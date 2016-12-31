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

"""Base classes for torrent commands"""

from ...logging import make_logger
log = make_logger(__name__)

import asyncio

from .. import (InitCommand, ExpectedResource)
from . import mixin


class AddTorrentsCmdbase(metaclass=InitCommand):
    name = 'add'
    aliases = ('download','get')
    provides = set()
    category = 'torrent'
    description = 'Download torrents'
    usage = ('add <TORRENT> <TORRENT> <TORRENT> ... [<OPTIONS>]',)
    examples = ('add 72d7a3179da3de7a76b98f3782c31843e3f818ee',
                'add --stopped http://example.org/something.torrent')
    argspecs = (
        { 'names': ('TORRENT',), 'nargs': '+',
          'description': 'Link or path to torrent file, magnet link or hash' },
        { 'names': ('--stopped','-s'), 'action': 'store_true',
          'description': 'Do not start downloading the added torrent' },
    )

    srvapi = ExpectedResource

    async def run(self, TORRENT, stopped):
        success = True
        force_torrentlist_update = False
        for source in TORRENT:
            response = await self.make_request(self.srvapi.torrent.add(source, stopped=stopped))
            success = success and response.success
            force_torrentlist_update = force_torrentlist_update or success

        # Update torrentlist AFTER all 'add' requests
        if force_torrentlist_update and hasattr(self, 'polling_frenzy'):
            self.polling_frenzy()
        return success


class ListTorrentsCmdbase(mixin.get_torrent_sorter, mixin.get_tlist_columns,
                          metaclass=InitCommand):
    name = 'list'
    aliases = ('ls',)
    provides = set()
    category = 'torrent'
    description = 'List torrents'
    usage = ('list [<OPTIONS>]',
             'list [<OPTIONS>] [<TORRENT FILTER> <TORRENT FILTER> ...]')
    examples = ('ls active',
                'ls !active',
                'ls seeds<10',
                'ls active&tracker~example.org',
                'ls active|idle&tracker~example')
    argspecs = (
        {'names': ('TORRENT FILTER',), 'nargs': '*',
         'description': 'Filter expression (see `help filter`)'},

        { 'names': ('--sort', '-s'),
          'default_description': "current value of 'tlist.sort' setting",
          'description': ('Comma-separated list of sort orders '
                          "(see 'sort' command for available sort orders)") },

        { 'names': ('--columns', '-c'),
          'default_description': "current value of 'tlist.columns' setting",
          'description': ('Comma-separated list of column names '
                          "(see 'help tlist.columns' for available columns)") },
    )
    more_sections = {
        'SCRIPTING': (
            ("If invoked as a command line argument and the output does not "
             "go to a TTY (i.e. the terminal size can't be determined), "
             "the output is optimized for scripting.  Numbers are "
             "unformatted, columns are separated by '|' and headers are "
             "not printed."),
            "",
            ("To enforce human-readable, formatted output, set the environment"
             "variables COLUMNS and LINES."),
            "",
            "\t$ \tCOLUMNS=80 LINES=24 {APPNAME} ls | less -R"
        ),
    }

    cfg = ExpectedResource

    async def run(self, TORRENT_FILTER, sort, columns):
        sort = self.cfg['tlist.sort'].value if sort is None else sort
        columns = self.cfg['tlist.columns'].value if columns is None else columns
        try:
            tfilter = self.select_torrents(TORRENT_FILTER,
                                           allow_no_filter=True,
                                           discover_torrent=False)
            sort = self.get_torrent_sorter(sort)
            columns = self.get_tlist_columns(columns)
        except ValueError as e:
            log.error(e)
            return False
        else:
            log.debug('Listing %s torrents sorted by %s', tfilter, sort)
            if asyncio.iscoroutinefunction(self.make_tlist):
                return await self.make_tlist(tfilter, sort, columns)
            else:
                return self.make_tlist(tfilter, sort, columns)


class ListFilesCmdbase(mixin.get_flist_columns, metaclass=InitCommand):
    name = 'filelist'
    aliases = ('fls', 'lsf')
    provides = set()
    category = 'torrent'
    description = 'List torrent files'
    usage = ('filelist [<OPTIONS>]',
             'filelist [<OPTIONS>] [<TORRENT FILTER>] [<FILE FILTER>]')
    examples = ('filelist',
                "filelist A.Torrent.with.Files",
                "filelist A.Torrent.with.Files priority=low")
    argspecs = (
        {'names': ('TORRENT FILTER',), 'nargs': '?',
         'description': 'Filter expression (see `help filter`) or focused torrent in the TUI'},

        { 'names': ('FILE FILTER',), 'nargs': '?',
          'description': 'Filter expression (see `help filter`)' },

        { 'names': ('--columns', '-c'),
          'default_description': "current value of 'flist.columns' setting",
          'description': ('Comma-separated list of column names '
                          "(see 'help flist.columns' for available columns)") },
    )
    more_sections = {'SCRIPTING': ListTorrentsCmdbase.more_sections['SCRIPTING']}

    cfg = ExpectedResource

    async def run(self, TORRENT_FILTER, FILE_FILTER, columns):
        columns = self.cfg['flist.columns'].value if columns is None else columns
        try:
            columns = self.get_flist_columns(columns)
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
    category = 'torrent'
    description = 'Change download priority of files'
    usage = ('priority <PRIORITY>',
             'priority <PRIORITY> [<TORRENT FILTER>] [<FILE FILTER>]')
    examples = ('priority low',
                'priority high "some torrent" size>12M')
    argspecs = (
        { 'names': ('PRIORITY',),
          'description': ("File priority; must be low/normal/high/shun, "
                          "l/n/h/s or -/./+/0")},
        {'names': ('TORRENT FILTER',), 'nargs': '?',
         'description': 'Filter expression (see `help filter`) or focused torrent in the TUI'},
        { 'names': ('FILE FILTER',), 'nargs': '?',
         'description': 'Filter expression (see `help filter`) or focused file in the TUI'},
    )

    srvapi = ExpectedResource

    _PRIORITY = {'l': 'low',    '-': 'low',    'low': 'low',
                 'n': 'normal', '.': 'normal', 'normal': 'normal',
                 'h': 'high',   '+': 'high'  , 'high': 'high',
                 's': 'shun',   '0': 'shun',   'shun': 'shun'}

    async def run(self, PRIORITY, TORRENT_FILTER, FILE_FILTER):
        try:
            priority = self._PRIORITY[PRIORITY.lower()]
        except KeyError:
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

        log.debug('Setting file download priority to %s for %s files of %s torrents',
                  priority, ffilter, tfilter)

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

        response = await self.make_request(
            self.srvapi.torrent.file_priority(priority, tfilter, ffilter),
            polling_frenzy=True, quiet=quiet)
        return response.success


class RemoveTorrentsCmdbase(metaclass=InitCommand):
    name = 'remove'
    aliases = ('rm', 'delete')
    provides = set()
    category = 'torrent'
    description = 'Remove torrents'
    usage = ('remove [<OPTIONS>]',
             'remove [<OPTIONS>] [<TORRENT FILTER> <TORRENT FILTER> ...]')
    examples = ('remove',
                'remove "some torrent" another\ torrent and_this_torrent',
                'remove -d "unwanted torrent"')
    argspecs = (
        {'names': ('TORRENT FILTER',), 'nargs': '*',
         'description': 'Filter expression (see `help filter`) or focused torrent in the TUI'},

        { 'names': ('--delete-files','-d'), 'action': 'store_true',
          'description': 'Delete any downloaded files' },
    )

    srvapi = ExpectedResource

    async def run(self, TORRENT_FILTER, delete_files):
        try:
            tfilter = self.select_torrents(TORRENT_FILTER,
                                           allow_no_filter=False,
                                           discover_torrent=True)
        except ValueError as e:
            log.error(e)
            return False
        else:
            response = await self.make_request(
                self.srvapi.torrent.remove(tfilter, delete=delete_files),
                polling_frenzy=True)
            return response.success


# Argument definitions that are shared between commands
ARGSPEC_TOGGLE = {
    'names': ('--toggle','-t'), 'action': 'store_true',
    'description': ('Start TORRENT if stopped and vice versa')
}

class StartTorrentsCmdbase(metaclass=InitCommand):
    name = 'start'
    aliases = ()
    provides = set()
    category = 'torrent'
    description = 'Start downloading torrents'
    usage = ('start [<OPTIONS>]',
             'start [<OPTIONS>] [<TORRENT FILTER> <TORRENT FILTER> ...]')
    examples = ('start',
                "start 'night of the living dead' Metropolis",
                'start ubuntu --force')
    argspecs = (
        {'names': ('TORRENT FILTER',), 'nargs': '*',
         'description': 'Filter expression (see `help filter`) or focused torrent in the TUI'},
        { 'names': ('--force','-f'), 'action': 'store_true',
          'description': 'Ignore download queue' },
        ARGSPEC_TOGGLE,
    )

    srvapi = ExpectedResource

    async def run(self, TORRENT_FILTER, toggle, force):
        try:
            tfilter = self.select_torrents(TORRENT_FILTER,
                                           allow_no_filter=False,
                                           discover_torrent=True)
        except ValueError as e:
            log.error(e)
            return False
        else:
            if toggle:
                response = await self.make_request(
                    self.srvapi.torrent.toggle_stopped(tfilter, force=force),
                    polling_frenzy=True)
            else:
                response = await self.make_request(
                    self.srvapi.torrent.start(tfilter, force=force),
                    polling_frenzy=True)
            return response.success


class StopTorrentsCmdbase(metaclass=InitCommand):
    name = 'stop'
    aliases = ('pause',)
    provides = set()
    category = 'torrent'
    description = 'Stop downloading torrents'
    usage = ('stop [<OPTIONS>]',
             'stop [<OPTIONS>] [<TORRENT FILTER> <TORRENT FILTER> ...]')
    examples = ('stop',
                'stop "night of the living dead" idle',
                'stop --toggle ubuntu')
    argspecs = (
        {'names': ('TORRENT FILTER',), 'nargs': '*',
         'description': 'Filter expression (see `help filter`) or focused torrent in the TUI'},
        ARGSPEC_TOGGLE,
    )

    srvapi = ExpectedResource

    async def run(self, TORRENT_FILTER, toggle):
        try:
            tfilter = self.select_torrents(TORRENT_FILTER,
                                           allow_no_filter=False,
                                           discover_torrent=True)
        except ValueError as e:
            log.error(e)
            return False
        else:
            if toggle:
                response = await self.make_request(
                    self.srvapi.torrent.toggle_stopped(tfilter),
                    polling_frenzy=True)
            else:
                response = await self.make_request(
                    self.srvapi.torrent.stop(tfilter),
                    polling_frenzy=True)
            return response.success


class VerifyTorrentsCmdbase(metaclass=InitCommand):
    name = 'verify'
    aliases = ('check',)
    provides = set()
    category = 'torrent'
    description = 'Verify downloaded torrent data'
    usage = ('verify [<OPTIONS>]',
             'verify [<OPTIONS>] [<TORRENT FILTER> <TORRENT FILTER> ...]')
    examples = ('verify',
                'verify debian')
    argspecs = (
        {'names': ('TORRENT FILTER',), 'nargs': '*',
         'description': 'Filter expression (see `help filter`) or focused torrent in the TUI'},
    )

    srvapi = ExpectedResource

    async def run(self, TORRENT_FILTER):
        try:
            tfilter = self.select_torrents(TORRENT_FILTER,
                                           allow_no_filter=False,
                                           discover_torrent=True)
        except ValueError as e:
            log.error(e)
            return False
        else:
            response = await self.make_request(self.srvapi.torrent.verify(tfilter),
                                               polling_frenzy=False)
            return response.success
