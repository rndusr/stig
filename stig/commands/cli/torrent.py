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

from . import _mixin as mixin
from .. import CmdError
from ... import objects
from ...completion import candidates
from ..base import torrent as base
from ._table import TERMSIZE, print_table

from ...logging import make_logger  # isort:skip
log = make_logger(__name__)


class AddTorrentsCmd(base.AddTorrentsCmdbase,
                     mixin.make_request):
    provides = {'cli'}

    @classmethod
    def completion_candidates_posargs(cls, args):
        """Complete positional arguments"""
        # Use current working directory as base
        return candidates.fs_path(args.curarg.before_cursor,
                                  base='.',
                                  glob=r'*.torrent')


class TorrentDetailsCmd(base.TorrentDetailsCmdbase,
                        mixin.make_request, mixin.select_torrents):
    provides = {'cli'}

    async def display_details(self, torrent_id):
        from ...views.details import SECTIONS
        needed_keys = set(('name',))
        for _section in SECTIONS:
            for _item in _section['items']:
                needed_keys.update(_item.needed_keys)

        response = await self.make_request(
            objects.srvapi.torrent.torrents((torrent_id,), keys=needed_keys),
            quiet=True)
        if not response.torrents:
            raise CmdError()
        else:
            torrent = response.torrents[0]

        if TERMSIZE.columns is None:
            self._machine_readable(torrent)
        else:
            self._human_readable(torrent)

    def _human_readable(self, torrent):
        from ...views.details import SECTIONS

        label_width = max(len(item.label)
                          for section in SECTIONS
                          for item in section['items'])

        for i,section in enumerate(SECTIONS):
            if i != 0:
                print()  # Newline between sections
            print('\033[1m' + section['title'].upper() + '\033[0m')
            for item in section['items']:
                print('  %s: %s' % (item.label.rjust(label_width), item.human_readable(torrent)))

    def _machine_readable(self, torrent):
        from ...views.details import SECTIONS
        for section in SECTIONS:
            for item in section['items']:
                print('%s\t%s' % (item.label.lower(), item.machine_readable(torrent)))


class ListTorrentsCmd(base.ListTorrentsCmdbase,
                      mixin.make_request, mixin.select_torrents,
                      mixin.only_supported_columns):
    provides = {'cli'}

    async def make_torrent_list(self, tfilter, sort, columns):
        from ...views.torrent import COLUMNS as TORRENT_COLUMNS

        # Remove columns that aren't supported by CLI interface (e.g. 'marked')
        columns = self.only_supported_columns(columns, TORRENT_COLUMNS)

        # Get needed keys
        if tfilter is None:
            keys = set(sort.needed_keys)
        else:
            keys = set(sort.needed_keys + tfilter.needed_keys)

        # Get wanted torrents and sort them
        for colname in columns:
            keys.update(TORRENT_COLUMNS[colname].needed_keys)
        response = await self.make_request(
            objects.srvapi.torrent.torrents(tfilter, keys=keys),
            quiet=True)
        torrents = sort.apply(response.torrents)

        # Show table of found torrents
        if torrents:
            print_table(torrents, columns, TORRENT_COLUMNS)
        else:
            raise CmdError()


class TorrentMagnetURICmd(base.TorrentMagnetURICmdbase,
                          mixin.select_torrents):
    provides = {'cli'}

    def display_uris(self, uris):
        for uri in uris:
            print(uri)


class MoveTorrentsCmd(base.MoveTorrentsCmdbase,
                      mixin.make_request, mixin.select_torrents):
    provides = {'cli'}

    @classmethod
    async def completion_candidates_posargs(cls, args):
        """Complete positional arguments"""
        if args.curarg_index == 1:
            log.debug('Getting torrent filter candidates from %r', candidates.torrent_filter)
            return await candidates.torrent_filter(args.curarg)
        elif args.curarg_index == 2:
            return candidates.fs_path(args.curarg.before_cursor,
                                      base=objects.cfg['srv.path.complete'],
                                      directories_only=True)


class RemoveTorrentsCmd(base.RemoveTorrentsCmdbase,
                        mixin.make_request, mixin.select_torrents, mixin.ask_yes_no):
    provides = {'cli'}

    async def show_list_of_hits(self, tfilter):
        import sys
        if sys.stdout.isatty():
            cmd = 'ls --sort name %s' % tfilter
            await objects.cmdmgr.run_async(cmd)

    def remove_list_of_hits(self):
        pass


class RenameCmd(base.RenameCmdbase,
                mixin.make_request, mixin.select_torrents, mixin.select_files):
    provides = {'cli'}


class StartTorrentsCmd(base.StartTorrentsCmdbase,
                       mixin.make_request, mixin.select_torrents):
    provides = {'cli'}


class StopTorrentsCmd(base.StopTorrentsCmdbase,
                      mixin.make_request, mixin.select_torrents):
    provides = {'cli'}


class VerifyTorrentsCmd(base.VerifyTorrentsCmdbase,
                        mixin.make_request, mixin.select_torrents):
    provides = {'cli'}
