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

from .peer import TUICOLUMNS
from . import (ItemWidgetBase, ListWidgetBase, stringify_torrent_filter)
from ...client import TorrentPeerFilter


class PeerItemWidget(ItemWidgetBase):
    palette_unfocused = 'peerlist'

    @property
    def id(self):
        return self.data['id']

    @property
    def torrent_id(self):
        return self.data['tid']


class PeerListWidget(ListWidgetBase):
    tuicolumns      = TUICOLUMNS
    ListItemClass   = PeerItemWidget
    keymap_context  = 'peer'
    palette_name    = 'peerlist'
    focusable_items = False

    def __init__(self, srvapi, keymap, tfilter=None, pfilter=None, columns=None, sort=None, title=None):
        super().__init__(srvapi, keymap, columns=columns, sort=sort, title=title)
        self._tfilter = tfilter
        self._pfilter = pfilter
        self._secondary_filter = None

        # Create peer filter generator
        if pfilter is not None:
            def filter_peers(peers):
                yield from pfilter.apply(peers)
        else:
            def filter_peers(peers):
                yield from peers
        self._maybe_filter_peers = filter_peers

        self._poller = self._srvapi.create_poller(
            self._srvapi.torrent.torrents, tfilter, keys=('peers', 'name', 'id')
        )
        self._poller.on_response(self._handle_peers)

    def _handle_peers(self, response):
        if response is None or not response.torrents:
            self.clear()
        else:
            # Auto-generate title from our filters if not set
            if self._title_name is None:
                self._title_name = stringify_torrent_filter(self._tfilter, response.torrents)
                if self._pfilter:
                    self._title_name += ' %s' % self._pfilter

            # Create list items our base widget can handle
            def peers_combined(torrents):
                for t in torrents:
                    yield from self._maybe_filter_peers(t['peers'])
            self._data_dict = {p['id']:p for p in peers_combined(response.torrents)}
        self._invalidate()

    def clear(self):
        for w in self._listbox.body:
            w.data.clearcache()
        super().clear()

    def refresh(self):
        self._poller.poll()

    @property
    def sort(self):
        return self._sort

    @sort.setter
    def sort(self, sort):
        ListWidgetBase.sort.fset(self, sort)
        self._poller.poll()

    @property
    def secondary_filter(self):
        return self._secondary_filter

    @secondary_filter.setter
    def secondary_filter(self, peer_filter):
        if peer_filter is None:
            self._secondary_filter = None
        else:
            self._secondary_filter = TorrentPeerFilter(peer_filter)
        self._invalidate()

    def _limit_items(self, peer_widgets):
        # Combine primary and secondary peer filters
        pfilter = self._pfilter
        spfilter = self._secondary_filter
        if pfilter is None:
            pfilter = spfilter
        elif spfilter is not None:
            pfilter = pfilter & spfilter

        if pfilter is not None:
            for pw in peer_widgets:
                if not pfilter.match(pw.data):
                    yield pw
