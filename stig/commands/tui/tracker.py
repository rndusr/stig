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

from ..base import tracker as base
from . import _mixin as mixin
from .. import (ExpectedResource, InitCommand)
from ._common import make_tab_title_widget

from functools import partial


class ListTrackersCmd(base.ListTrackersCmdbase,
                      mixin.make_request, mixin.select_torrents, mixin.generate_tab_title):
    provides = {'tui'}
    tui = ExpectedResource
    srvapi = ExpectedResource

    async def make_trklist(self, torfilter, trkfilter, sort, columns):
        make_titlew = partial(make_tab_title_widget,
                              attr_unfocused='tabs.trackerlist.unfocused',
                              attr_focused='tabs.trackerlist.focused')

        title_str = await self.generate_tab_title(torfilter)

        from ...tui.views.trackerlist import TrackerListWidget
        trklistw = TrackerListWidget(self.srvapi, self.tui.keymap,
                                     torfilter=torfilter, trkfilter=trkfilter,
                                     sort=sort, columns=columns, title=title_str)
        tabid = self.tui.tabs.load(make_titlew(trklistw.title), trklistw)

        def set_tab_title(text, count):
            self.tui.tabs.set_title(make_titlew(text, count), position=tabid)
        trklistw.title_updater = set_tab_title

        return True


class AnnounceTorrentsCmd(base.AnnounceTorrentsCmdbase,
                          mixin.make_request, mixin.select_torrents):
    provides = {'tui'}


