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

from ..base import torrent as base
from . import _mixin as mixin
from ._common import clear_line
from .. import ExpectedResource
from ._table import (print_table, TERMSIZE)
from ...client import convert


class CreateTorrentCmd(base.CreateTorrentCmdbase,
                       mixin.user_confirmation):
    provides = {'cli'}

    def generate(self, torrent):
        import torf

        _display_torrent_info(torrent)
        canceled = True
        try:
            canceled = not torrent.generate(callback=self._progress_callback,
                                            interval=0.5)
        except torf.TorfError as e:
            clear_line()
            log.error(e)
            return False
        finally:
            clear_line()
            if canceled:
                return False
            else:
                _info_line('Info Hash', torrent.infohash)
                return True

    def write(self, torrent, torrent_filepath, create_magnet=False):
        if create_magnet:
            _info_line('Magnet URI', torrent.magnet())

        if torrent_filepath:
            import torf
            try:
                torrent.write(torrent_filepath, overwrite=True)
            except torf.TorfError as e:
                log.error(e)
                return False
            else:
                _info_line('Torrent File', torrent_filepath)
                return True

    def _progress_callback(self, filename, pieces_completed, pieces_total):
        progress = pieces_completed / pieces_total * 100
        if progress < 100:
            msg = '%s: Hashed %d of %d pieces (%.2f %%)' % \
                  ('Progress'.rjust(SHOW_TORRENT_LABEL_WIDTH), pieces_completed,
                   pieces_total, progress)
            clear_line()
            print(msg, end='', flush=True)


class ShowTorrentCmd(base.ShowTorrentCmdbase):
    provides = {'cli'}

    def show_torrent(self, torrent):
        _display_torrent_info(torrent)


SHOW_TORRENT_LABEL_WIDTH = 13
def _info_line(label, value):
    if label:
        log.info('%s: %s' % (label.rjust(SHOW_TORRENT_LABEL_WIDTH), value))
    else:
        log.info('%s  %s' % (label.rjust(SHOW_TORRENT_LABEL_WIDTH), value))

def _display_torrent_info(torrent):
    lines = []
    lines.append(('Name', torrent.name))
    lines.append(('Content Path', torrent.path))
    lines.append(('Size', convert.size(torrent.size)))
    if torrent.comment:
        lines.append(('Comment', torrent.comment))
    if torrent.creation_date:
        lines.append(('Creation Date', torrent.creation_date.isoformat(sep=' ', timespec='seconds')))
    else:
        lines.append(('Creation Date', 'Unknown'))
    if torrent.created_by:
        lines.append(('Created By', torrent.created_by))
    lines.append(('Private', 'yes' if torrent.private else 'no'))

    trackers = []  # List of lines
    if torrent.trackers:
        if all(len(tier) <= 1 for tier in torrent.trackers):
            # One tracker per tier - print tracker per line
            for tier in torrent.trackers:
                if tier:
                    trackers.append(tier[0])
        else:
            # At least one tier has multiple trackers
            for i,tier in enumerate(torrent.trackers, 1):
                if tier:
                    trackers.append('Tier #%d: %s' % (i, tier[0]))
                    for tracker in tier[1:]:
                        trackers.append(' '*9 + tracker)

    # Prepend 'Trackers' to first line and indent the remaining ones
    if trackers:
        label = 'Tracker' + ('s' if len(trackers) > 1 else '')
        lines.append((label, trackers[0]))
        for line in trackers[1:]:
            lines.append(('', line))

    if torrent.webseeds:
        label = 'Webseed' + ('s' if len(torrent.webseeds) > 1 else '')
        lines.append((label, torrent.webseeds[0]))
        for webseed in torrent.webseeds[1:]:
            lines.append(('', webseed))

    if torrent.httpseeds:
        label = 'HTTP Seed' + ('s' if len(torrent.httpseeds) > 1 else '')
        lines.append((label, torrent.httpseeds[0]))
        for httpseed in torrent.httpseeds[1:]:
            lines.append(('', httpseed))

    if isinstance(torrent.piece_size, int):
        lines.append(('Piece Size', convert.size(torrent.piece_size)))

    # Show non-standard values
    standard_keys = ('info', 'announce', 'announce-list', 'creation date',
                     'created by', 'comment', 'encoding', 'url-list', 'httpseeds')
    for key,value in torrent.metainfo.items():
        if key not in standard_keys:
            lines.append((key.capitalize(), value))

    # Print assembled lines
    for label,value in lines:
        _info_line(label, value)


class ListTorrentsCmd(base.ListTorrentsCmdbase,
                      mixin.make_request, mixin.select_torrents,
                      mixin.only_supported_columns):
    provides = {'cli'}
    srvapi = ExpectedResource  # TUI version of 'list' doesn't need srvapi

    async def make_tlist(self, tfilter, sort, columns):
        from ...views.torrentlist import COLUMNS as TORRENT_COLUMNS

        # Remove columns that aren't supported by CLI interface (e.g. 'marked')
        columns = self.only_supported_columns(columns, TORRENT_COLUMNS)

        # Get wanted torrents and sort them
        if tfilter is None:
            keys = set(sort.needed_keys)
        else:
            keys = set(sort.needed_keys + tfilter.needed_keys)
        for colname in columns:
            keys.update(TORRENT_COLUMNS[colname].needed_keys)
        response = await self.make_request(
            self.srvapi.torrent.torrents(tfilter, keys=keys),
            quiet=True)
        torrents = sort.apply(response.torrents)

        if torrents:
            print_table(torrents, columns, TORRENT_COLUMNS)
        return len(torrents) > 0


class TorrentsSummaryCmd(base.TorrentSummaryCmdbase,
                         mixin.make_request, mixin.select_torrents):
    provides = {'cli'}

    async def display_summary(self, tfilter):
        torrent = await self.get_torrent(tfilter, keys=('id',))
        if torrent is None:
            return False
        tid = torrent['id']

        from ...views.summary import SECTIONS
        needed_keys = set(('name',))
        for _section in SECTIONS:
            for _item in _section['items']:
                needed_keys.update(_item.needed_keys)

        response = await self.make_request(
            self.srvapi.torrent.torrents((tid,), keys=needed_keys),
            quiet=True)
        if len(response.torrents) < 1:
            return False
        else:
            torrent = response.torrents[0]

        # Whether to print for a human or for a machine to read our output
        if TERMSIZE.columns is None:
            self._machine_readable(torrent)
        else:
            self._human_readable(torrent)
        return True

    def _human_readable(self, torrent):
        from ...views.summary import SECTIONS

        label_width = max(len(item.label)
                          for section in SECTIONS
                          for item in section['items'])

        for section in SECTIONS:
            log.info('\033[1m' + section['title'].upper() + '\033[0m')
            for item in section['items']:
                log.info('  %s: %s', item.label.rjust(label_width), item.human_readable(torrent))

    def _machine_readable(self, torrent):
        from ...views.summary import SECTIONS

        for section in SECTIONS:
            for item in section['items']:
                log.info('%s\t%s', item.label.lower(), item.machine_readable(torrent))


class AddTorrentsCmd(base.AddTorrentsCmdbase,
                     mixin.make_request):
    provides = {'cli'}


class MoveTorrentsCmd(base.MoveTorrentsCmdbase,
                      mixin.make_request, mixin.select_torrents):
    provides = {'cli'}


class RemoveTorrentsCmd(base.RemoveTorrentsCmdbase,
                        mixin.make_request, mixin.select_torrents, mixin.user_confirmation):
    provides = {'cli'}
    cmdmgr = ExpectedResource

    async def show_list_of_hits(self, tfilter):
        cmd = 'ls --sort name %s' % tfilter
        await self.cmdmgr.run_async(cmd)

    def remove_list_of_hits(self):
        pass


class StartTorrentsCmd(base.StartTorrentsCmdbase,
                       mixin.make_request, mixin.select_torrents):
    provides = {'cli'}


class StopTorrentsCmd(base.StopTorrentsCmdbase,
                      mixin.make_request, mixin.select_torrents):
    provides = {'cli'}


class VerifyTorrentsCmd(base.VerifyTorrentsCmdbase,
                        mixin.make_request, mixin.select_torrents):
    provides = {'cli'}
