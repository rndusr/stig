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

from collections import abc

from .. import utils


class get_torrent_id():
    async def get_torrent_id(self, tfilter):
        request = self.srvapi.torrent.torrents(tfilter, keys=('name', 'id'))
        response = await self.make_request(request, polling_frenzy=False, quiet=True)
        if response.success:
            from ...client import TorrentSorter
            torrents = TorrentSorter(('name',)).apply(response.torrents)
            return torrents[0]['id']


class get_torrent_sorter():
    def get_torrent_sorter(self, args):
        """Return TorrentSorter instance or None

        If `args` evaluates to True, it is passed to TorrentSorter and the
        result is returned.

        If `args` evaluates to False, None is returned.
        """
        if args:
            from ...client import TorrentSorter
            return TorrentSorter(utils.listify_args(args))


class get_peer_sorter():
    def get_peer_sorter(self, args):
        """Return TorrentPeerSorter instance or None

        If `args` evaluates to True, it is passed to TorrentPeerSorter and the
        result is returned.

        If `args` evaluates to False, None is returned.
        """
        if args:
            from ...client import TorrentPeerSorter
            return TorrentPeerSorter(utils.listify_args(args))


class get_peer_filter():
    def get_peer_filter(self, FILTER):
        """Return TorrentPeerFilter instance or None

        If `FILTER` evaluates to True, it is passed to TorrentPeerFilter and
        the resulting object is returned.

        If `FILTER` evaluates to False, None is returned.
        """
        if FILTER:
            from ...client import TorrentPeerFilter
            return TorrentPeerFilter(FILTER)


class get_tlist_columns():
    def get_tlist_columns(self, columns, interface=None):
        """Check if each item in iterable `columns` is a valid torrent list column name

        If `interface` is not None, also remove all columns that don't have
        `interface` in their `interfaces` attribute.

        Raise ValueError or return a new list of `columns`.
        """
        from ...views.tlist import COLUMNS
        cols = utils.listify_args(columns)
        for col in tuple(cols):
            if col not in COLUMNS:
                raise ValueError('Unknown column name: {}'.format(col))
            elif interface is not None and interface not in COLUMNS[col].interfaces:
                log.debug('Removing column %r because it does not support %r',
                          col, interface)
                cols.remove(col)
        return cols


class get_flist_columns():
    def get_flist_columns(self, columns):
        """Check if each item in iterable `columns` is a valid file list column name

        Raise ValueError or return a new list of `columns`.
        """
        from ...views.flist import COLUMNS
        cols = utils.listify_args(columns)
        for col in cols:
            if col not in COLUMNS:
                raise ValueError('Unknown column name: {}'.format(col))
        return cols


class get_plist_columns():
    def get_plist_columns(self, columns):
        """Check if each item in iterable `columns` is a valid peer list column name

        Raise ValueError or return a new list of `columns`.
        """
        from ...views.plist import COLUMNS
        cols = utils.listify_args(columns)
        for col in cols:
            if col not in COLUMNS:
                raise ValueError('Unknown column name: {}'.format(col))
        return cols
