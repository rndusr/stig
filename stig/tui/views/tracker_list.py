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

from .tracker import TUICOLUMNS
from . import (ItemWidgetBase, ListWidgetBase, stringify_torrent_filter)
from ...client import TorrentTrackerFilter

from ...logging import make_logger
log = make_logger(__name__)


class TrackerItemWidget(ItemWidgetBase):
    palette_unfocused = 'trackerlist'
    palette_focused   = 'trackerlist.focused'
    columns_focus_map = {}
    for col in TUICOLUMNS.values():
        columns_focus_map.update(col.style.focus_map)

    @property
    def id(self):
        return self.data['id']

    @property
    def torrent_id(self):
        return self.data['tid']


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
        self._secondary_filter = None

        # Create tracker filter generator
        if trkfilter is not None:
            def filter_trackers(trackers):
                yield from trkfilter.apply(trackers)
        else:
            def filter_trackers(trackers):
                yield from trackers
        self._maybe_filter_trackers = filter_trackers

        self._poller = self._srvapi.create_poller(
            self._srvapi.torrent.torrents, torfilter, keys=('trackers', 'name', 'id')
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
            self._data_dict = {trk['id']:trk for trk in trackers_combined(response.torrents)}
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

    @property
    def focused_torrent_id(self):
        """Torrent ID of the currently focused tracker or `None`"""
        focused_widget = self._listbox.focus
        if focused_widget is not None:
            return focused_widget.torrent_id


    @property
    def secondary_filter(self):
        return self._secondary_filter

    @secondary_filter.setter
    def secondary_filter(self, tracker_filter):
        if tracker_filter is None:
            self._secondary_filter = None
        else:
            self._secondary_filter = TorrentTrackerFilter(tracker_filter)
        self._invalidate()

    def _limit_items(self, tracker_widgets):
        # Combine primary and secondary tracker filters
        trkfilter = self._trkfilter
        strkfilter = self._secondary_filter
        if trkfilter is None:
            trkfilter = strkfilter
        elif strkfilter is not None:
            trkfilter = trkfilter & strkfilter

        if trkfilter is not None:
            for tw in tracker_widgets:
                if not trkfilter.match(tw.data):
                    log.debug('%r does not match %r', trkfilter, tw.data['domain'])
                    yield tw
                else:
                    log.debug('%r does match %r', trkfilter, tw.data['domain'])
