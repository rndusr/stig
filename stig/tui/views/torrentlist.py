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

import urwid

from ..scroll import ScrollBar
from ..table import Table
from .tlist_columns import TUICOLUMNS
from . import (ItemWidgetBase, ListWidgetBase, stringify_torrent_filter)


class TorrentItemWidget(ItemWidgetBase):
    palette_unfocused = 'torrentlist'
    palette_focused   = 'torrentlist.focused'
    columns_focus_map = {}
    for col in TUICOLUMNS.values():
        columns_focus_map.update(col.style.focus_map)


class TorrentListWidget(ListWidgetBase):
    tuicolumns      = TUICOLUMNS
    ListItemClass   = TorrentItemWidget
    keymap_context  = 'torrent'
    palette_name    = 'torrentlist'
    focusable_items = True

    def __init__(self, srvapi, keymap, tfilter=None, sort=None, columns=None, title=None):
        super().__init__(srvapi, keymap, columns=columns, sort=sort, title=title)
        self._tfilter = tfilter
        self._register_request()

    @property
    def id(self):
        """Hashable object that is unique among all torrent lists"""
        return repr(self)

    def _register_request(self):
        # Get keys needed for sort order, tfilter and columns
        keys = []
        if self._sort is not None:
            keys.extend(self._sort.needed_keys)
        if hasattr(self._tfilter, 'needed_keys'):
            keys.extend(self._tfilter.needed_keys)
        for colname in self._columns:
            keys.extend(self.tuicolumns[colname].needed_keys)

        # Register new request in request pool
        log.debug('Registering keys for %r: %s', self, keys)
        self._srvapi.treqpool.register(self.id,
                                       self._handle_torrents,
                                       keys=keys, tfilter=self._tfilter)
        self._srvapi.treqpool.poll()

    def _handle_torrents(self, torrents):
        self._items = {t['id']:t for t in torrents}
        super()._invalidate()

    def clear(self):
        """Remove all list items"""
        for w in self._listbox.body:
            w.item.clearcache()
        super().clear()
        self._srvapi.treqpool.poll()

    @property
    def sort(self):
        """TorrentSorter object (set to `None` to restore original sort order)"""
        return self._sort

    @sort.setter
    def sort(self, sort):
        self._srvapi.treqpool.remove(self.id)
        ListWidgetBase.sort.fset(self, sort)
        self._register_request()

    @property
    def title_name(self):
        if self._title is None:
            return stringify_torrent_filter(self._tfilter)
        else:
            return ListWidgetBase.title_name.fget(self)
