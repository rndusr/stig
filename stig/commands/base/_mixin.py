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

"""Mixin classes that are common between TUI and CLI commands"""

from ...logging import make_logger
log = make_logger(__name__)


from .. import utils


def _get_columns(columns, setting, cfg):
    # Resolve aliases and complain about invalid values
    return cfg.validate(setting, columns)


class get_torrent():
    async def get_torrent(self, tfilter, keys=()):
        """
        Get a single torrent that matches TorrentFilter `tfilter`

        If there are multple matches, they are sorted by name and the first
        match is returned.

        Return None if no match is found.
        """
        request = self.srvapi.torrent.torrents(tfilter, keys=keys)
        response = await self.make_request(request, polling_frenzy=False, quiet=True)
        if response.success:
            from ...client import TorrentSorter
            torrents = TorrentSorter(('name',)).apply(response.torrents)
            return torrents[0]

class get_torrent_sorter():
    def get_torrent_sorter(self, args):
        """
        Return TorrentSorter instance or None

        If `args` evaluates to True, it is passed to TorrentSorter and the
        result is returned.

        If `args` evaluates to False, None is returned.
        """
        if args:
            from ...client import TorrentSorter
            return TorrentSorter(utils.listify_args(args))

class get_torrent_columns():
    def get_torrent_columns(self, columns):
        """
        Check if each item in iterable `columns` is a valid torrent list column name

        Raise ValueError or return a new list of `columns`.
        """
        return _get_columns(columns, 'columns.torrents', self.cfg)



class get_file_columns():
    def get_file_columns(self, columns):
        """
        Check if each item in iterable `columns` is a valid file list column name

        Raise ValueError or return a new list of `columns`.
        """
        return _get_columns(columns, 'columns.files', self.cfg)



class get_peer_sorter():
    def get_peer_sorter(self, args):
        """
        Return TorrentPeerSorter instance or None

        If `args` evaluates to True, it is passed to TorrentPeerSorter and the
        result is returned.

        If `args` evaluates to False, None is returned.
        """
        if args:
            from ...client import TorrentPeerSorter
            return TorrentPeerSorter(utils.listify_args(args))

class get_peer_filter():
    def get_peer_filter(self, FILTER):
        """
        Return TorrentPeerFilter instance or None

        If `FILTER` evaluates to True, it is passed to TorrentPeerFilter and the
        resulting object is returned.

        If `FILTER` evaluates to False, None is returned.
        """
        if FILTER:
            from ...client import TorrentPeerFilter
            return TorrentPeerFilter(FILTER)

class get_peer_columns():
    def get_peer_columns(self, columns):
        """
        Check if each item in iterable `columns` is a valid peer list column name

        Raise ValueError or return a new list of `columns`.
        """
        return _get_columns(columns, 'columns.peers', self.cfg)



class get_tracker_sorter():
    def get_tracker_sorter(self, args):
        """
        Return TorrentTrackerSorter instance or None

        If `args` evaluates to True, it is passed to TorrentTrackerSorter and
        the result is returned.

        If `args` evaluates to False, None is returned.
        """
        if args:
            from ...client import TorrentTrackerSorter
            return TorrentTrackerSorter(utils.listify_args(args))

class get_tracker_filter():
    def get_tracker_filter(self, FILTER):
        """
        Return TorrentTrackerFilter instance or None

        If `FILTER` evaluates to True, it is passed to TorrentTrackerFilter and
        the resulting object is returned.

        If `FILTER` evaluates to False, None is returned.
        """
        if FILTER:
            from ...client import TorrentTrackerFilter
            return TorrentTrackerFilter(FILTER)

class get_tracker_columns():
    def get_tracker_columns(self, columns):
        """
        Check if each item in iterable `columns` is a valid tracker list column name

        Raise ValueError or return a new list of `columns`.
        """
        return _get_columns(columns, 'columns.trackers', self.cfg)
