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

from natsort import humansorted

from . import _mixin as mixin
from .. import CmdError
from ... import objects
from ..base import tracker as base
from ._table import print_table

from ...logging import make_logger  # isort:skip
log = make_logger(__name__)


class ListTrackersCmd(base.ListTrackersCmdbase,
                      mixin.make_request, mixin.select_torrents):
    provides = {'cli'}

    async def make_tracker_list(self, torfilter, trkfilter, sort, columns):
        response = await self.make_request(
            objects.srvapi.torrent.torrents(torfilter, keys=('name', 'trackers')),
            quiet=True)
        torrents = response.torrents

        if len(torrents) < 1:
            raise CmdError()

        if trkfilter is None:
            def filter_trackers(trackers):
                return trackers
        else:
            def filter_trackers(trackers):
                return trkfilter.apply(trackers)

        trklist = []
        for torrent in humansorted(torrents, key=lambda t: t['name']):
            trklist.extend(filter_trackers(torrent['trackers']))

        sort.apply(trklist, inplace=True)

        if trklist:
            from ...views.tracker import COLUMNS as TRACKER_COLUMNS
            print_table(trklist, columns, TRACKER_COLUMNS)
        else:
            def filter_is_relevant(f):
                return f and str(f) != 'all'

            if filter_is_relevant(trkfilter):
                errmsg = 'No matching trackers'
            else:
                errmsg = 'No trackers'

            if filter_is_relevant(torfilter):
                errmsg += ' in %s torrents' % torfilter

            if filter_is_relevant(trkfilter):
                errmsg += ': %s' % trkfilter

            raise CmdError(errmsg)


class AnnounceCmd(base.AnnounceCmdbase,
                  mixin.make_request, mixin.select_torrents):
    provides = {'cli'}


class TrackerCmd(base.TrackerCmdbase,
                 mixin.make_request, mixin.select_torrents):
    provides = {'cli'}
