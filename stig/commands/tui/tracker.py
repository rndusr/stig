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


class ListTrackersCmd(base.ListTrackersCmdbase,
                      mixin.make_request,
                      mixin.select_torrents,
                      mixin.create_list_widget):
    provides = {'tui'}

    def make_tracker_list(self, torfilter, trkfilter, sort, columns):
        from ...tui.views.tracker_list import TrackerListWidget
        self.create_list_widget(TrackerListWidget, theme_name='trackerlist',
                                torfilter=torfilter, trkfilter=trkfilter,
                                sort=sort, columns=columns,
                                markable_items=False)


class AnnounceCmd(base.AnnounceCmdbase,
                  mixin.make_request, mixin.select_torrents):
    provides = {'tui'}


class TrackerCmd(base.TrackerCmdbase,
                 mixin.make_request, mixin.polling_frenzy, mixin.select_torrents):
    provides = {'tui'}
