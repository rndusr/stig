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

from .torrent import TUICOLUMNS
from . import (ItemWidgetBase, ListWidgetBase, stringify_torrent_filter)
from ...client import TorrentFilter


class TorrentItemWidget(ItemWidgetBase):
    palette_unfocused = 'torrentlist'
    palette_focused   = 'torrentlist.focused'
    columns_focus_map = {}
    for col in TUICOLUMNS.values():
        columns_focus_map.update(col.style.focus_map)

    @property
    def id(self):
        return self.data['id']

    @property
    def torrent_id(self):
        return self.data['id']


class TorrentListWidget(ListWidgetBase):
    tuicolumns      = TUICOLUMNS
    ListItemClass   = TorrentItemWidget
    keymap_context  = 'torrent'
    palette_name    = 'torrentlist'
    focusable_items = True

    def __init__(self, srvapi, keymap, tfilter=None, sort=None, columns=None, title=None):
        super().__init__(srvapi, keymap, columns=columns, sort=sort, title=title)
        self._tfilter = tfilter
        self._secondary_filter = None
        self._register_request()

    @property
    def id(self):
        """Hashable that is unique among all torrent lists"""
        return id(self)

    def _register_request(self):
        # Get keys needed for sort order, filters and columns
        keys = {'name'}
        if self._sort is not None:
            keys.update(self._sort.needed_keys)
        if hasattr(self._tfilter, 'needed_keys'):
            keys.update(self._tfilter.needed_keys)
        if self._secondary_filter is not None:
            keys.update(self._secondary_filter.needed_keys)
        for colname in self.columns:
            keys.update(self.tuicolumns[colname].needed_keys)

        # Register new request in request pool
        existing_keys = self._srvapi.treqpool.requested_keys(self.id)
        if keys != existing_keys:
            log.debug('Registering keys for %r: %s', self, keys)
            self._srvapi.treqpool.register(self.id,
                                           self._handle_torrents,
                                           keys=keys, tfilter=self._tfilter)
            self._srvapi.treqpool.poll()
        else:
            log.debug('No need to register a new request')
            self._invalidate()

    # # Enable this to measure rendering performance
    # def render(self, *args, **kwargs):
    #     import time
    #     start = time.time()
    #     canvas = super().render(*args, **kwargs)
    #     log.debug('Rendered torrent list in %.3fms', (time.time()-start)*1000)
    #     return canvas

    def _handle_torrents(self, torrents):
        # Auto-generate title from our filters if not set
        if self._title_name is None:
            self._title_name = stringify_torrent_filter(self._tfilter, torrents)
        self._data_dict = {t['id']:t for t in torrents}
        self._invalidate()

    def clear(self):
        for w in self._listbox.body:
            w.data.clearcache()
        super().clear()

    def refresh(self):
        self._srvapi.treqpool.poll()

    @property
    def sort(self):
        return self._sort

    @sort.setter
    def sort(self, sort):
        self._srvapi.treqpool.remove(self.id)
        ListWidgetBase.sort.fset(self, sort)
        self._register_request()

    @property
    def focused_torrent_id(self):
        """Torrent ID of the currently focused torrent or `None`"""
        focused_widget = self._listbox.focus
        if focused_widget is not None:
            return focused_widget.torrent_id

    @property
    def secondary_filter(self):
        return self._secondary_filter

    @secondary_filter.setter
    def secondary_filter(self, torrent_filter):
        if torrent_filter is None:
            self._secondary_filter = None
        else:
            self._secondary_filter = TorrentFilter(torrent_filter)
        log.debug('Filtering %r torrents', self._secondary_filter)
        self._register_request()

    def _limit_items(self, torrent_widgets):
        f = self._secondary_filter
        if f is not None:
            for tw in torrent_widgets:
                if not f.match(tw.data):
                    yield tw
