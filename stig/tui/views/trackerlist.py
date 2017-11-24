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

import urwid

from ..scroll import ScrollBar
from .trklist_columns import TUICOLUMNS
from . import (ItemWidgetBase, ListWidgetBase, stringify_torrent_filter)


class TrackerItemWidget(ItemWidgetBase):
    palette_unfocused = 'trackerlist'
    palette_focused   ='trackerlist.focused'
    columns_focus_map = {}
    for col in TUICOLUMNS.values():
        columns_focus_map.update(col.style.focus_map)


class TrackerListWidget(ListWidgetBase):
    tuicolumns      = TUICOLUMNS
    ListItemClass   = TrackerItemWidget
    keymap_context  = 'tracker'
    palette_name    = 'trackerlist'
    focusable_items = True

    def __init__(self, srvapi, keymap, torfilter, trkfilter, columns=None, sort=None, title=None):
        super().__init__(srvapi, keymap, columns=columns, sort=sort, title=title)
        self._torfilter = torfilter
        self._trkfilter = trkfilter

        # Create tracker filter generator
        if trkfilter is not None:
            def filter_trackers(trackers):
                yield from trkfilter.apply(trackers)
        else:
            def filter_trackers(trackers):
                yield from trackers
        self._maybe_filter_trackers = filter_trackers

        self._poller = self._srvapi.create_poller(
            self._srvapi.torrent.torrents, torfilter, keys=('trackers', 'name', 'id'),
            autoconnect=False
        )
        self._poller.on_response(self._handle_trackers)

    def _handle_trackers(self, response):
        if response is None or not response.torrents:
            self.clear()
        else:
            # Auto-generate title from our filters if not set
            if self._title_name is None:
                self._title_name = stringify_torrent_filter(self._torfilter, response.torrents)
                if self._trkfilter:
                    self._title_name += ' %s' % self._trkfilter

            # Create list items our base widget can handle
            def trackers_combined(torrents):
                for t in torrents:
                    yield from self._maybe_filter_trackers(t['trackers'])
            self._items = {trk['id']:trk for trk in trackers_combined(response.torrents)}
        self._invalidate()

    def refresh(self):
        self._poller.poll()

    @property
    def sort(self):
        return self._sort

    @sort.setter
    def sort(self, sort):
        ListWidgetBase.sort.fset(self, sort)
        self._poller.poll()
