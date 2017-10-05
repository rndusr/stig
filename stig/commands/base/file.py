# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details
# http://www.gnu.org/licenses/gpl-3.0.txt

from ...logging import make_logger
log = make_logger(__name__)

from .. import (InitCommand, ExpectedResource)
from . import _mixin as mixin
from ._common import (make_X_FILTER_spec, make_COLUMNS_doc, make_SCRIPTING_doc)

import asyncio


class ListFilesCmdbase(mixin.get_file_columns, metaclass=InitCommand):
    name = 'filelist'
    aliases = ('fls', 'lsf')
    provides = set()
    category = 'file'
    description = 'List files of torrent(s)'
    usage = ('filelist [<OPTIONS>]',
             'filelist [<OPTIONS>] <TORRENT FILTER>',
             'filelist [<OPTIONS>] <TORRENT FILTER> <FILE FILTER>')
    examples = ('filelist',
                'filelist size<100MB',
                'filelist A.Torrent.with.Files priority=low')
    argspecs = (
        make_X_FILTER_spec('TORRENT', or_focused=True, nargs='?'),
        make_X_FILTER_spec('FILE', or_focused=False, nargs='?'),
        { 'names': ('--columns', '-c'),
          'default_description': "current value of 'columns.files' setting",
          'description': ('Comma-separated list of column names '
                          "(see COLUMNS section)") },
    )

    from ...views.filelist import COLUMNS
    more_sections = {
        'COLUMNS': make_COLUMNS_doc(COLUMNS, '--columns', 'columns.files'),
        'SCRIPTING': make_SCRIPTING_doc(name),
    }

    cfg = ExpectedResource

    async def run(self, TORRENT_FILTER, FILE_FILTER, columns):
        columns = self.cfg['columns.files'].value if columns is None else columns
        try:
            columns = self.get_file_columns(columns)
            tfilter = self.select_torrents(TORRENT_FILTER,
                                           allow_no_filter=False,
                                           discover_torrent=True)
            ffilter = self.select_files(FILE_FILTER,
                                        allow_no_filter=True,
                                        discover_file=False)
        except ValueError as e:
            log.error(e)
            return False

        log.debug('Listing %s files of %s torrents', ffilter, tfilter)

        if asyncio.iscoroutinefunction(self.make_flist):
            return await self.make_flist(tfilter, ffilter, columns)
        else:
            return self.make_flist(tfilter, ffilter, columns)


class PriorityCmdbase(metaclass=InitCommand):
    name = 'priority'
    aliases = ('prio',)
    provides = set()
    category = 'file'
    description = 'Change download priority of files'
    usage = ('priority <PRIORITY>',
             'priority <PRIORITY> <TORRENT FILTER>',
             'priority <PRIORITY> <TORRENT FILTER> <FILE FILTER>')
    examples = ('priority low',
                'priority high "that torrent" size>12M')
    _PRIORITY = {'off'    : ('o', '0', 'off'),
                 'low'    : ('l', '-', 'low'),
                 'normal' : ('n', '=', 'normal'),
                 'high'   : ('h', '+', 'high')}
    argspecs = (
        { 'names': ('PRIORITY',),
          'description': 'File priority; must be %s, %s or %s' % (
              '/'.join(p[2] for p in _PRIORITY.values()),
              '/'.join(p[0] for p in _PRIORITY.values()),
              '/'.join(p[1] for p in _PRIORITY.values()),
          )},
        make_X_FILTER_spec('TORRENT', or_focused=True, nargs='?'),
        make_X_FILTER_spec('FILE', or_focused=True, nargs='?'),
    )
    srvapi = ExpectedResource

    async def run(self, PRIORITY, TORRENT_FILTER, FILE_FILTER):
        priority = None
        for p,names in self._PRIORITY.items():
            if PRIORITY in names:
                priority = p
                break
        if priority is None:
            log.error('Invalid priority: {!r}'.format(PRIORITY))
            return False

        try:
            tfilter = self.select_torrents(TORRENT_FILTER,
                                           allow_no_filter=False,
                                           discover_torrent=True)
            ffilter = self.select_files(FILE_FILTER,
                                        allow_no_filter=True,
                                        discover_file=True)
        except ValueError as e:
            log.error(e)
            return False

        if not isinstance(tfilter, tuple):
            # tfilter must be TorrentFilter instance, which means the user
            # specified a filter and will be informed about the matches.
            if isinstance(ffilter, tuple):
                # The user did specify a torrent filter but not a file filter,
                # so select_files() may have returned a focused file.  But we
                # assume that the user meant all files of the matching
                # torrents, otherwise they wouldn't have given a torrent
                # filter.
                ffilter = None

            msg = 'New download priority of %s files in %s torrents: %s' % (
                'all' if ffilter is None else ffilter, tfilter, priority)
            log.info(msg)
            quiet = False
        else:
            # We're operating on the focused file and success is indiciated by
            # the updated file list, so no info message necessary.
            quiet = True

        # If ffilter is a tuple, it is a tuple of (torrent_id, file_id) tuples.
        # In that case, we overload tfilter with the torrent_ids from ffilter.
        if isinstance(ffilter, tuple):
            tfilter = tuple(set(ids[0] for ids in ffilter))
        log.debug('Setting file download priority to %s for %s files of %s torrents',
                  priority, ffilter, tfilter)

        response = await self.make_request(
            self.srvapi.torrent.file_priority(tfilter, ffilter, priority),
            polling_frenzy=True, quiet=quiet)
        return response.success
