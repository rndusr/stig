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

import asyncio
import os

from . import _mixin as mixin
from .. import CmdError, CommandMeta
from ... import objects
from ...completion import candidates
from ...utils.cliparser import Arg
from ._common import (make_COLUMNS_doc, make_SCRIPTING_doc, make_SORT_ORDERS_doc,
                      make_X_FILTER_spec)

from ...logging import make_logger  # isort:skip
log = make_logger(__name__)


class AddTorrentsCmdbase(metaclass=CommandMeta):
    name = 'add'
    aliases = ('download','get')
    provides = set()
    category = 'torrent'
    description = 'Download torrents'
    usage = ('add [<OPTIONS>] <TORRENT> <TORRENT> <TORRENT> ...',)
    examples = ('add 72d7a3179da3de7a76b98f3782c31843e3f818ee',
                'add --stopped http://example.org/something.torrent')
    argspecs = (
        {'names': ('TORRENT',), 'nargs': '+',
         'description': 'Link or path to torrent file, magnet link or info hash'},

        {'names': ('--stopped','-s'), 'action': 'store_true',
         'description': 'Do not start downloading the added torrent(s)'},

        {'names': ('--path','-p'),
         'description': ('Custom download directory for added torrent(s) '
                         'relative to "srv.path.complete" setting')},
    )

    async def run(self, TORRENT, stopped, path):
        success = True
        force_torrentlist_update = False
        for source in TORRENT:
            source_abs_path = self.make_path_absolute(source)
            response = await self.make_request(objects.srvapi.torrent.add(source_abs_path,
                                                                          stopped=stopped,
                                                                          path=path))
            success = success and response.success
            force_torrentlist_update = force_torrentlist_update or success

        # Update torrentlist AFTER all 'add' requests
        if force_torrentlist_update and hasattr(self, 'polling_frenzy'):
            self.polling_frenzy()

        if not success:
            raise CmdError()

    @staticmethod
    def make_path_absolute(path):
        abspath = os.path.abspath(os.path.expanduser(path))
        if os.path.exists(abspath):
            return abspath
        else:
            return path

    @classmethod
    def completion_candidates_params(cls, option, args):
        """Complete parameters (e.g. --option parameter1,parameter2)"""
        if option == '--path':
            return candidates.fs_path(args.curarg.before_cursor,
                                      base=objects.cfg['srv.path.complete'],
                                      directories_only=True)


class TorrentDetailsCmdbase(mixin.get_single_torrent, metaclass=CommandMeta):
    name = 'details'
    aliases = ('info',)
    provides = set()
    category = 'torrent'
    description = 'Display detailed torrent information'
    usage = ('details',
             'details <TORRENT FILTER>')
    examples = ('details id=71',)
    argspecs = (
        make_X_FILTER_spec('TORRENT', or_focused=True, nargs='?'),
    )

    async def run(self, TORRENT_FILTER):
        try:
            tfilter = self.select_torrents(TORRENT_FILTER,
                                           allow_no_filter=False,
                                           discover_torrent=True,
                                           prefer_focused=True)
        except ValueError as e:
            raise CmdError(e)
        else:
            torrent = await self.get_single_torrent(tfilter, keys=('id', 'name'))
            if not torrent:
                raise CmdError()
            else:
                log.debug('Showing details of torrent %r: %r', tfilter, torrent)
                if asyncio.iscoroutinefunction(self.display_details):
                    await self.display_details(torrent['id'])
                else:
                    self.display_details(torrent['id'])

    @classmethod
    def completion_candidates_posargs(cls, args):
        """Complete positional arguments"""
        if args.curarg_index == 1:
            return candidates.torrent_filter(args.curarg)


class ListTorrentsCmdbase(mixin.get_torrent_sorter, mixin.get_torrent_columns,
                          metaclass=CommandMeta):
    name = 'list'
    aliases = ('ls',)
    provides = set()
    category = 'torrent'
    description = 'List torrents'
    usage = ('list [<OPTIONS>]',
             'list [<OPTIONS>] <TORRENT FILTER> <TORRENT FILTER> ...')
    examples = ('ls active',
                'ls !active',
                'ls seeds<10',
                'ls active&tracker~example.org',
                'ls active|idle&tracker~example')
    argspecs = (
        make_X_FILTER_spec('TORRENT', or_focused=False, nargs='*'),

        {'names': ('--sort', '-s'),
         'default_description': "current value of 'sort.torrents' setting",
         'description': ('Comma-separated list of sort orders '
                         "(see SORT ORDERS section)")},

        {'names': ('--columns', '-c'),
         'default_description': "current value of 'columns.torrents' setting",
         'description': ('Comma-separated list of column names '
                         "(see COLUMNS section)")},
    )

    from ...views.torrent import COLUMNS
    from ...client.sorters import TorrentSorter
    more_sections = {
        'COLUMNS': make_COLUMNS_doc(COLUMNS, '--columns', 'columns.torrents'),
        'SORT ORDERS': make_SORT_ORDERS_doc(TorrentSorter, '--sort', 'sort.torrents'),
        'SCRIPTING': make_SCRIPTING_doc(name),
    }

    async def run(self, TORRENT_FILTER, sort, columns):
        sort = objects.localcfg['sort.torrents'] if sort is None else sort
        columns = objects.localcfg['columns.torrents'] if columns is None else columns
        try:
            columns = self.get_torrent_columns(columns)
            tfilter = self.select_torrents(TORRENT_FILTER,
                                           allow_no_filter=True,
                                           discover_torrent=False)
            sort = self.get_torrent_sorter(sort)
        except ValueError as e:
            raise CmdError(e)
        else:
            log.debug('Listing %s torrents sorted by %s', tfilter, sort)
            if asyncio.iscoroutinefunction(self.make_torrent_list):
                await self.make_torrent_list(tfilter, sort, columns)
            else:
                self.make_torrent_list(tfilter, sort, columns)

    @classmethod
    def completion_candidates_posargs(cls, args):
        """Complete positional arguments"""
        return candidates.torrent_filter(args.curarg)

    @classmethod
    def completion_candidates_params(cls, option, args):
        """Complete parameters (e.g. --option parameter1,parameter2)"""
        if option == '--sort':
            return candidates.sort_orders('TorrentSorter')
        elif option == '--columns':
            return candidates.column_names('torrents')


class TorrentMagnetURICmdbase(metaclass=CommandMeta):
    name = 'magnet'
    aliases = ('uri',)
    provides = set()
    category = 'torrent'
    description = 'Display torrent(s) magnet URI'
    usage = ('magnet',
             'magnet <TORRENT FILTER>')
    examples = ('magnet name~ubuntu',)
    argspecs = (
        make_X_FILTER_spec('TORRENT', or_focused=True, nargs='?'),
    )

    async def run(self, TORRENT_FILTER):
        try:
            tfilter = self.select_torrents(TORRENT_FILTER,
                                           allow_no_filter=False,
                                           discover_torrent=True,
                                           prefer_focused=False)
        except ValueError as e:
            raise CmdError(e)
        else:
            try:
                uris = await objects.srvapi.torrent.get_magnet_uris(tfilter)
            except objects.srvapi.ClientError as e:
                raise CmdError(e)
            else:
                self.display_uris(uris)

    @classmethod
    def completion_candidates_posargs(cls, args):
        """Complete positional arguments"""
        if args.curarg_index == 1:
            return candidates.torrent_filter(args.curarg)


class MoveTorrentsCmdbase(metaclass=CommandMeta):
    name = 'move'
    aliases = ('mv',)
    provides = set()
    category = 'torrent'
    description = "Change torrents' location"
    usage = ('move <PATH>',
             'move <TORRENT FILTER> <PATH>')
    examples = ('move ./new/path',
                'move size>50G /path/to/lots/of/storage')
    argspecs = (
        make_X_FILTER_spec('TORRENT', or_focused=True, nargs='?'),

        {'names': ('PATH',),
         'description': ('Move the specified torrent(s) to this directory.  If PATH is relative '
                         '(i.e. does not start with "/"), it is relative to the value of the '
                         'setting "srv.path.complete".  That means "." is the download path.')},
    )

    async def run(self, TORRENT_FILTER, PATH):
        try:
            tfilter = self.select_torrents(TORRENT_FILTER,
                                           allow_no_filter=False,
                                           discover_torrent=True)
        except ValueError as e:
            raise CmdError(e)
        else:
            response = await self.make_request(objects.srvapi.torrent.move(tfilter, PATH),
                                               polling_frenzy=True)
            if not response.success:
                raise CmdError()


class RemoveTorrentsCmdbase(metaclass=CommandMeta):
    name = 'remove'
    aliases = ('rm', 'delete')
    provides = set()
    category = 'torrent'
    description = 'Remove torrents'
    usage = ('remove [<OPTIONS>]',
             'remove [<OPTIONS>] <TORRENT FILTER> <TORRENT FILTER> ...')
    examples = ('remove',
                r'remove "stupid torrent" silly\ torrent and_this_torrent',
                'remove -d "unwanted torrent"')
    argspecs = (
        make_X_FILTER_spec('TORRENT', or_focused=True, nargs='*'),

        {'names': ('--delete-files','-d'), 'action': 'store_true',
         'description': 'Delete any downloaded files'},

        {'names': ('--force','-f'), 'action': 'store_true',
         'description': ('Ignore remove.max-hits setting: Remove all '
                         'matching torrents instead of asking for confirmation '
                         'if the number of matches exceeds remove.max-hits')},
    )

    async def run(self, TORRENT_FILTER, delete_files, force):
        try:
            tfilter = self.select_torrents(TORRENT_FILTER,
                                           allow_no_filter=False,
                                           discover_torrent=True)
        except ValueError as e:
            raise CmdError(e)
        else:
            async def do_remove(tfilter=tfilter, delete_files=delete_files):
                response = await self.make_request(
                    objects.srvapi.torrent.remove(tfilter, delete=delete_files),
                    polling_frenzy=True)
                if not response.success:
                    raise CmdError()

            async def do_keep(tfilter=tfilter):
                self.error(('Keeping %s torrents: Too many hits ' % tfilter) +
                           '(use --force or increase remove.max-hits setting)')

            response = await objects.srvapi.torrent.torrents(tfilter, keys=('id',))
            hits = len(response.torrents)
            success = hits > 0
            if force or objects.cfg['remove.max-hits'] < 0 or hits < objects.cfg['remove.max-hits']:
                return await do_remove()
            else:
                await self.show_list_of_hits(tfilter)
                if hits > 0:
                    question = 'Are you sure you want to remove %d torrent%s' % (
                        hits, '' if hits == 1 else 's')
                    if delete_files:
                        question += ' and their files'
                    question += '?'
                    success = await self.ask_yes_no(question, yes=do_remove, no=do_keep,
                                                    after=self.remove_list_of_hits)
                if not success:
                    raise CmdError()

    @classmethod
    def completion_candidates_posargs(cls, args):
        """Complete positional arguments"""
        return candidates.torrent_filter(args.curarg)


class RenameCmdbase(metaclass=CommandMeta):
    name = 'rename'
    aliases = ('rn',)
    provides = set()
    category = 'torrent'
    description = 'Rename a torrent or one of its files or directories'
    usage = ('rename <NEW>',
             'rename <TORRENT> <NEW>')
    examples = ('rename "A Better Name"',
                'rename id=123 Foo',
                'rename id=123/some/file new_file_name')
    argspecs = (
        {'names': ('TORRENT',), 'nargs': '?',
         'description': ('Torrent filter expression, optionally followed by a "/" and '
                         'the relative path to a file or directory in the torrent'),
         'default_description': 'Focused torrent, file or directory in the TUI'},

        {'names': ('NEW',),
         'description': ('New name of the torrent, file or directory specified by TORRENT '
                         '(must not contain "/" or be "." or "..")')},

        {'names': ('--unique', '-u'), 'action': 'store_true',
         'description': ('Ensure the torrent filter expression in TORRENT matches exactly '
                         'one torrent; if not given, all matching files in all matching '
                         'torrents are renamed'),
         'default_description': 'Enabled automatically when renaming torrents'},
    )

    async def run(self, TORRENT, NEW, unique):
        if not TORRENT:
            # Autodetect path
            path = self.get_relative_path_from_focused(unique=unique)
            if path:
                # path is "<TORRENT
                # IDENTIFIER>/relative/path/to/file/in/torrent" where <TORRENT
                # IDENTIFIER> is either the torrent's name or "id=<ID>" if
                # `unique` is True.
                TORRENT = path

        # Split torrent filter from relative path in torrent
        if TORRENT and '/' in TORRENT:
            FILTER, PATH = TORRENT.split('/', maxsplit=1)
            renaming_torrent = False
        else:
            FILTER, PATH = TORRENT, None
            renaming_torrent = True

        try:
            tfilter = self.select_torrents(FILTER,
                                           allow_no_filter=False,
                                           discover_torrent=True)
        except ValueError as e:
            raise CmdError(e)
        else:
            response = await self.make_request(
                objects.srvapi.torrent.torrents(tfilter, keys=('id',)),
                quiet=True)
            if not response.success:
                raise CmdError()
            elif (unique or renaming_torrent) and len(response.torrents) > 1:
                # When renaming a torrent or --unique is given, tfilter must
                # match exactly one torrent.  If it matches zero torrents,
                # make_request() below with produce the appropriate error
                # message.
                raise CmdError('%s matches more than one torrent' % tfilter)
            else:
                success = True
                for torrent in response.torrents:
                    tid = torrent['id']
                    response = await self.make_request(
                        objects.srvapi.torrent.rename(tid, path=PATH, new_name=NEW),
                        polling_frenzy=True)
                    if not response.success:
                        success = False
                if not success:
                    raise CmdError()

    @classmethod
    async def completion_candidates_posargs(cls, args):
        """Complete positional arguments"""
        # We don't care about options
        args = args.posargs()
        if args.curarg_index == 1:
            # Complete file and directory names from torrent(s)
            return await candidates.torrent_path(args.curarg, only='any')
        elif args.curarg_index == 2:
            first_arg_stripped = args[1].strip('/')
            if '/' in first_arg_stripped:
                # First argument contains a path separator, so destination is
                # the new file name.  The second argument can't contain a path
                # separator if it's a file or directory.
                if '/' not in args.curarg:
                    # To make it more convenient to adjust file/directory names,
                    # destination candidates are existing files or directories
                    # from the path specified in the first argument.  Files if
                    # the first argument points to a file, directories if the
                    # first argument points to a directory.
                    source = Arg(first_arg_stripped, curpos=len(first_arg_stripped))
                    log.debug('Using destination candidates from: %r', source)
                    return await candidates.torrent_path(source, only='auto')
            else:
                # Destination is the new torrent name
                log.debug('Using torrent names as destination candidates')
                return await candidates.torrent_filter(args.curarg, filter_names=False)


# Argument definitions that are shared between commands
ARGSPEC_TOGGLE = {
    'names': ('--toggle','-t'), 'action': 'store_true',
    'description': ('Start TORRENT if stopped and vice versa')
}

class StartTorrentsCmdbase(metaclass=CommandMeta):
    name = 'start'
    aliases = ()
    provides = set()
    category = 'torrent'
    description = 'Start downloading torrents'
    usage = ('start [<OPTIONS>]',
             'start [<OPTIONS>] <TORRENT FILTER> <TORRENT FILTER> ...')
    examples = ('start',
                "start 'night of the living dead' Metropolis",
                'start ubuntu --force')
    argspecs = (
        make_X_FILTER_spec('TORRENT', or_focused=True, nargs='*'),

        {'names': ('--force','-f'), 'action': 'store_true',
         'description': 'Ignore download queue'},

        ARGSPEC_TOGGLE,
    )

    async def run(self, TORRENT_FILTER, toggle, force):
        try:
            tfilter = self.select_torrents(TORRENT_FILTER,
                                           allow_no_filter=False,
                                           discover_torrent=True)
        except ValueError as e:
            raise CmdError(e)
        else:
            if toggle:
                response = await self.make_request(
                    objects.srvapi.torrent.toggle_stopped(tfilter, force=force),
                    polling_frenzy=True)
            else:
                response = await self.make_request(
                    objects.srvapi.torrent.start(tfilter, force=force),
                    polling_frenzy=True)
            if not response.success:
                raise CmdError()

    @classmethod
    def completion_candidates_posargs(cls, args):
        """Complete positional arguments"""
        return candidates.torrent_filter(args.curarg)


class StopTorrentsCmdbase(metaclass=CommandMeta):
    name = 'stop'
    aliases = ('pause',)
    provides = set()
    category = 'torrent'
    description = 'Stop downloading torrents'
    usage = ('stop [<OPTIONS>]',
             'stop [<OPTIONS>] <TORRENT FILTER> <TORRENT FILTER> ...')
    examples = ('stop',
                'stop "night of the living dead" idle',
                'stop --toggle ubuntu')
    argspecs = (
        make_X_FILTER_spec('TORRENT', or_focused=True, nargs='*'),
        ARGSPEC_TOGGLE,
    )

    async def run(self, TORRENT_FILTER, toggle):
        try:
            tfilter = self.select_torrents(TORRENT_FILTER,
                                           allow_no_filter=False,
                                           discover_torrent=True)
        except ValueError as e:
            raise CmdError(e)
        else:
            if toggle:
                response = await self.make_request(
                    objects.srvapi.torrent.toggle_stopped(tfilter),
                    polling_frenzy=True)
            else:
                response = await self.make_request(
                    objects.srvapi.torrent.stop(tfilter),
                    polling_frenzy=True)
            if not response.success:
                raise CmdError()

    @classmethod
    def completion_candidates_posargs(cls, args):
        """Complete positional arguments"""
        return candidates.torrent_filter(args.curarg)


class VerifyTorrentsCmdbase(metaclass=CommandMeta):
    name = 'verify'
    aliases = ('check',)
    provides = set()
    category = 'torrent'
    description = 'Verify downloaded torrent data'
    usage = ('verify [<OPTIONS>]',
             'verify [<OPTIONS>] <TORRENT FILTER> <TORRENT FILTER> ...')
    examples = ('verify',
                'verify debian')
    argspecs = (
        make_X_FILTER_spec('TORRENT', or_focused=True, nargs='*'),
    )

    async def run(self, TORRENT_FILTER):
        try:
            tfilter = self.select_torrents(TORRENT_FILTER,
                                           allow_no_filter=False,
                                           discover_torrent=True)
        except ValueError as e:
            raise CmdError(e)
        else:
            response = await self.make_request(objects.srvapi.torrent.verify(tfilter),
                                               polling_frenzy=True)
            if not response.success:
                raise CmdError()

    @classmethod
    def completion_candidates_posargs(cls, args):
        """Complete positional arguments"""
        return candidates.torrent_filter(args.curarg)
