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
from collections import abc

from .. import (InitCommand, ExpectedResource)
from . import mixin


class AddTorrentsCmdbase(metaclass=InitCommand):
    name = 'add'
    aliases = ('download','get')
    provides = set()
    category = 'torrent'
    description = 'Download torrents'
    usage = ('add [<OPTIONS>] <TORRENT> <TORRENT> <TORRENT> ...',)
    examples = ('add 72d7a3179da3de7a76b98f3782c31843e3f818ee',
                'add --stopped http://example.org/something.torrent')
    argspecs = (
        { 'names': ('TORRENT',), 'nargs': '+',
          'description': 'Link or path to torrent file, magnet link or hash' },

        { 'names': ('--stopped','-s'), 'action': 'store_true',
          'description': 'Do not start downloading the added torrent(s)' },

        { 'names': ('--path','-p'),
          'description': 'Custom download directory for added torrent(s)' },
    )

    srvapi = ExpectedResource

    async def run(self, TORRENT, stopped, path):
        success = True
        force_torrentlist_update = False
        for source in TORRENT:
            response = await self.make_request(self.srvapi.torrent.add(source, stopped=stopped, path=path))
            success = success and response.success
            force_torrentlist_update = force_torrentlist_update or success

        # Update torrentlist AFTER all 'add' requests
        if force_torrentlist_update and hasattr(self, 'polling_frenzy'):
            self.polling_frenzy()
        return success


class AnnounceTorrentsCmdbase(metaclass=InitCommand):
    name = 'announce'
    aliases = ('an',)
    provides = set()
    category = 'torrent'
    description = 'Announce torrents to their trackers now if possible'
    usage = ('announce',
             'announce <TORRENT FILTER> <TORRENT FILTER> ...')
    examples = ('announce tracker~example.org',)
    argspecs = (
        { 'names': ('TORRENT FILTER',), 'nargs': '*',
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
            response = await self.make_request(
                self.srvapi.torrent.announce(tfilter),
                polling_frenzy=False)
            return response.success


def _make_SCRIPTING_doc(cmdname):
    return ( ("If invoked as a command line argument and the output does not "
              "go to a TTY (i.e. the terminal size can't be determined), "
              "the output is optimized for scripting.  Numbers are "
              "unformatted, columns are separated by a horizontal tab "
              "character ('\\t') and headers are not printed."),
             "",
             ("To enforce human-readable, formatted output, set the environment "
              "variables COLUMNS and LINES."),
             "",
             "\t$ \tCOLUMNS=80 LINES=24 {{APPNAME}} {CMDNAME} | less -R".format(CMDNAME=cmdname) )

def _make_SORT_ORDERS_doc(sortercls, option, setting, append=()):
    doc = [('The following sort orders can be specified with the {option} option '
            'or the "{setting}" setting:').format(option=option, setting=setting),
            '']

    for sname,s in sorted(sortercls.SORTSPECS.items()):
        snames = ', '.join((sname,) + s.aliases)
        doc.append('\t{}\t - \t{}'.format(snames, s.description))

    doc.extend(('',
                'Multiple sort orders are separated with "," without spaces.',
                '',
                'Sorting is reversed if the sort order is prepended by "!" or ".".',
                '',
                ('If "%s" is not given explicitly, it is always prepended to '
                 'the list of sort orders.') % sortercls.DEFAULT_SORT))
    if append:
        doc.extend(('',) + append)
    return tuple(doc)


def _make_COLUMNS_doc(columnspecs, option, setting, append=()):
    return (('The following columns can be specified with the {option} option '
             'or the "{setting}" setting:').format(option=option, setting=setting),
            '',
            '\t%s' % ', '.join(sorted(columnspecs)),
            '',
            'Columns are separated with "," without spaces.') \
            + append


class ListTorrentsCmdbase(mixin.get_torrent_sorter, mixin.get_tlist_columns,
                          metaclass=InitCommand):
    name = 'list'
    aliases = ('ls',)
    provides = set()
    category = 'torrent'
    description = 'List torrents'
    usage = ('list [<OPTIONS>] [<TORRENT FILTER> <TORRENT FILTER> ...]',)
    examples = ('ls active',
                'ls !active',
                'ls seeds<10',
                'ls active&tracker~example.org',
                'ls active|idle&tracker~example')

    argspecs = (
        {'names': ('TORRENT FILTER',), 'nargs': '*',
         'description': 'Filter expression (see `help filter`)'},

        { 'names': ('--sort', '-s'),
          'default_description': "current value of 'sort.torrents' setting",
          'description': ('Comma-separated list of sort orders '
                          "(see SORT ORDERS section)") },

        { 'names': ('--columns', '-c'),
          'default_description': "current value of 'columns.torrents' setting",
          'description': ('Comma-separated list of column names '
                          "(see COLUMNS section)") },
    )

    from ...views.tlist import COLUMNS
    from ...client.sorters.tsorter import TorrentSorter
    more_sections = {
        'COLUMNS': _make_COLUMNS_doc(COLUMNS, '--columns', 'columns.torrents'),
        'SORT ORDERS': _make_SORT_ORDERS_doc(TorrentSorter, '--sort', 'sort.torrents'),
        'SCRIPTING': _make_SCRIPTING_doc(name),
    }

    cfg = ExpectedResource

    async def run(self, TORRENT_FILTER, sort, columns):
        sort = self.cfg['sort.torrents'].value if sort is None else sort
        columns = self.cfg['columns.torrents'].value if columns is None else columns
        try:
            columns = self.get_tlist_columns(columns)
            tfilter = self.select_torrents(TORRENT_FILTER,
                                           allow_no_filter=True,
                                           discover_torrent=False)
            sort = self.get_torrent_sorter(sort)
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
    description = 'List files of torrent(s)'
    usage = ('filelist [<OPTIONS>]',
             'filelist [<OPTIONS>] [<TORRENT FILTER>] [<FILE FILTER>]')
    examples = ('filelist',
                'filelist size<100MB',
                'filelist A.Torrent.with.Files priority=low')
    argspecs = (
        {'names': ('TORRENT FILTER',), 'nargs': '?',
         'description': 'Filter expression (see `help filter`) or focused torrent in the TUI'},

        { 'names': ('FILE FILTER',), 'nargs': '?',
          'description': 'Filter expression (see `help filter`)' },

        { 'names': ('--columns', '-c'),
          'default_description': "current value of 'columns.files' setting",
          'description': ('Comma-separated list of column names '
                          "(see COLUMNS section)") },
    )

    from ...views.flist import COLUMNS
    more_sections = {
        'COLUMNS': _make_COLUMNS_doc(COLUMNS, '--columns', 'columns.files'),
        'SCRIPTING': _make_SCRIPTING_doc(name),
    }

    cfg = ExpectedResource

    async def run(self, TORRENT_FILTER, FILE_FILTER, columns):
        columns = self.cfg['columns.files'].value if columns is None else columns
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


class ListPeersCmdbase(mixin.get_peer_sorter, mixin.get_plist_columns,
                       mixin.get_peer_filter, metaclass=InitCommand):
    name = 'peerlist'
    aliases = ('pls', 'lsp')
    provides = set()
    category = 'torrent'
    description = 'List connected peers of torrent(s)'
    usage = ('peerlist [<OPTIONS>]',
             'peerlist [<OPTIONS>] [<TORRENT FILTER>] [<PEER FILTER>]')
    examples = ('peerlist',
                'peerlist downloading',
                'peerlist some_torrent ip=127.0.0.1')
    argspecs = (
        {'names': ('TORRENT FILTER',), 'nargs': '?',
         'description': 'Filter expression (see `help filter`) or focused torrent in the TUI'},

        { 'names': ('PEER FILTER',), 'nargs': '?',
          'description': 'Filter expression (see `help filter`)' },

        { 'names': ('--sort', '-s'),
          'default_description': "current value of 'sort.peers' setting",
          'description': ('Comma-separated list of sort orders '
                          "(see SORT ORDERS section)") },

        { 'names': ('--columns', '-c'),
          'default_description': "current value of 'columns.peers' setting",
          'description': ('Comma-separated list of column names '
                          "(see COLUMNS section)") },
    )

    from ...views.plist import COLUMNS
    from ...client.sorters.psorter import TorrentPeerSorter
    more_sections = {
        'COLUMNS': _make_COLUMNS_doc(COLUMNS, '--columns', 'columns.peers', append=(
            '',
            'The "name" column is added automatically if multiple '
            'torrents could be listed potentially.')),
        'SORT ORDERS': _make_SORT_ORDERS_doc(TorrentPeerSorter, '--sort', 'sort.peers'),
        'SCRIPTING': _make_SCRIPTING_doc(name),
    }

    cfg = ExpectedResource

    async def run(self, TORRENT_FILTER, PEER_FILTER, sort, columns):
        columns = self.cfg['columns.peers'].value if columns is None else columns
        sort = self.cfg['sort.peers'].value if sort is None else sort
        try:
            tfilter = self.select_torrents(TORRENT_FILTER,
                                           allow_no_filter=True,
                                           discover_torrent=True)
            pfilter = self.get_peer_filter(PEER_FILTER)
            sort    = self.get_peer_sorter(sort)
            columns = self.get_plist_columns(columns)
        except ValueError as e:
            log.error(e)
            return False

        # Unless we're listing peers of exactly one torrent, specified by its
        # ID, automatically add the 'name' column.
        if 'name' not in columns and \
           (not isinstance(tfilter, abc.Sequence) or len(tfilter) != 1):
            columns.insert(0, 'name')

        log.debug('Listing %s peers of %s torrents', pfilter, tfilter)

        if asyncio.iscoroutinefunction(self.make_plist):
            return await self.make_plist(tfilter, pfilter, sort, columns)
        else:
            return self.make_plist(tfilter, pfilter, sort, columns)


class TorrentDetailsCmdbase(mixin.get_torrent_id, metaclass=InitCommand):
    name = 'details'
    aliases = ('info',)
    provides = set()
    category = 'torrent'
    description = 'Display detailed torrent information'
    usage = ('details',)
    examples = ('details id=71',)
    argspecs = (
        { 'names': ('TORRENT FILTER',), 'nargs': '?',
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
            log.debug('Showing details of torrent %r', tfilter)
            if asyncio.iscoroutinefunction(self.show_details):
                return await self.show_details(tfilter)
            else:
                return self.show_details(tfilter)


class MoveTorrentsCmdbase(metaclass=InitCommand):
    name = 'move'
    aliases = ('mv',)
    provides = set()
    category = 'torrent'
    description = "Change torrents' location"
    usage = ('move [<TORRENT FILTER>] <PATH>',)
    examples = ('move new/path',
                'move size>50g path/to/lots/of/storage')
    argspecs = (
        {'names': ('TORRENT FILTER',), 'nargs': '?',
         'description': 'Filter expression (see `help filter`) or focused torrent in the TUI'},

        {'names': ('PATH',),
         'description': ('New location of the specified torrent(s).  If PATH is relative '
                         '(does not start with "/"), it is relative to the value of the '
                         'setting "srv.path.complete".')},
    )

    srvapi = ExpectedResource

    async def run(self, TORRENT_FILTER, PATH):
        try:
            tfilter = self.select_torrents(TORRENT_FILTER,
                                           allow_no_filter=False,
                                           discover_torrent=True)
        except ValueError as e:
            log.error(e)
            return False
        else:
            response = await self.make_request(self.srvapi.torrent.move(tfilter, PATH),
                                               polling_frenzy=True)
            return response.success


class PriorityCmdbase(metaclass=InitCommand):
    name = 'priority'
    aliases = ('prio',)
    provides = set()
    category = 'torrent'
    description = 'Change download priority of files'
    usage = ('priority <PRIORITY>',
             'priority <PRIORITY> [<TORRENT FILTER>] [<FILE FILTER>]')
    examples = ('priority low',
                'priority high "that torrent" size>12M')
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
            self.srvapi.torrent.file_priority(tfilter, priority, ffilter),
            polling_frenzy=True, quiet=quiet)
        return response.success


class RateLimitCmdbase(metaclass=InitCommand):
    name = 'rate'
    aliases = ()
    provides = set()
    category = 'torrent'
    description = "Limit up-/download rate per torrent or globally"
    usage = ('rate <DIRECTION> <LIMIT>',
             'rate <DIRECTION> <LIMIT> [<TORRENT FILTER> <TORRENT FILTER> ...]')
    examples = ('rate up 5Mb',
                'rate up,down - "This torrent" size<100MB',
                'rate down,up 1MB global')
    argspecs = (
        {'names': ('DIRECTION',),
         'description': '"up", "down" or both separated by a comma'},

        {'names': ('LIMIT',),
         'description': ('Maximum allowed rate limit; metric (k, M, G, etc) and binary (Ki, Mi, Gi, etc) '
                         'unit prefixes are supported (case is ignored); append "b" for bits, "B" for bytes '
                         'or nothing for whatever \'unit.bandwidth\' is set to; "none", "-" and '
                         'negative numbers disable the limit; if TORRENT FILTER is "global", any valid '
                         '\'srv.limit.rate.up/down\' setting is accepted (see `help srv.limit.rate.up`)')},

        {'names': ('TORRENT FILTER',), 'nargs': '*',
         'description': ('Filter expression (see `help filter`), "global" to set '
                         '\'srv.limit.rate.<DIRECTION>\' or focused torrent in the TUI')},
    )

    srvapi = ExpectedResource
    cmdmgr = ExpectedResource

    async def run(self, DIRECTION, LIMIT, TORRENT_FILTER):
        direction = tuple(map(str.lower, DIRECTION.split(',')))
        for d in direction:
            if d not in ('up', 'down'):
                log.error('%s: Invalid item in argument DIRECTION: %r', self.name, d)
                return False

        if TORRENT_FILTER == ['global']:
            if LIMIT in ('none', '-'):
                LIMIT = 'disable'
            for d in direction:
                success = await self.cmdmgr.run_async('set srv.limit.rate.%s %s' % (d, LIMIT),
                                                      block=True)
                if not success:
                    return False
            return True

        try:
            tfilter = self.select_torrents(TORRENT_FILTER,
                                           allow_no_filter=False,
                                           discover_torrent=True)
        except ValueError as e:
            log.error(e)
            return False
        else:
            if LIMIT in ('none', '-'):
                LIMIT = None

            for d in direction:
                method = getattr(self.srvapi.torrent, 'limit_rate_'+d)
                try:
                    response = await self.make_request(method(tfilter, LIMIT),
                                                       polling_frenzy=True)
                except ValueError as e:
                    log.error(e)
                    return False
                if not response.success:
                    return False
            return True


class RemoveTorrentsCmdbase(metaclass=InitCommand):
    name = 'remove'
    aliases = ('rm', 'delete')
    provides = set()
    category = 'torrent'
    description = 'Remove torrents'
    usage = ('remove [<OPTIONS>]',
             'remove [<OPTIONS>] [<TORRENT FILTER> <TORRENT FILTER> ...]')
    examples = ('remove',
                'remove "stupid torrent" silly\ torrent and_this_torrent',
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
