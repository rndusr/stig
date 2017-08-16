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

from ..base import torrent as base
from . import _mixin as mixin
from .. import (ExpectedResource, InitCommand)
from ._common import make_tab_title_widget

from functools import partial


class ListTorrentsCmd(base.ListTorrentsCmdbase,
                      mixin.select_torrents, mixin.generate_tab_title):
    provides = {'tui'}
    tui = ExpectedResource
    srvapi = ExpectedResource

    async def make_tlist(self, tfilter, sort, columns):
        if 'marked' not in columns:
            columns.insert(0, 'marked')

        make_titlew = partial(make_tab_title_widget,
                              attr_unfocused='tabs.torrentlist.unfocused',
                              attr_focused='tabs.torrentlist.focused')

        title_str = await self.generate_tab_title(tfilter)

        from ...tui.views.torrentlist import TorrentListWidget
        tlistw = TorrentListWidget(self.srvapi, self.tui.keymap, tfilter=tfilter,
                                   sort=sort, columns=columns, title=title_str)
        tabid = self.tui.tabs.load(make_titlew(tlistw.title), tlistw)

        def set_tab_title(text, count):
            self.tui.tabs.set_title(make_titlew(text, count), position=tabid)
        tlistw.title_updater = set_tab_title

        return True


class TorrentSummaryCmd(base.TorrentSummaryCmdbase,
                        mixin.select_torrents, mixin.make_request, mixin.generate_tab_title):
    provides = {'tui'}
    tui = ExpectedResource

    async def display_summary(self, tfilter):
        tid = await self.get_torrent_id(tfilter)
        if tid is None:
            return False

        make_titlew = partial(make_tab_title_widget,
                              attr_unfocused='tabs.torrentsummary.unfocused',
                              attr_focused='tabs.torrentsummary.focused')

        title_str = await self.generate_tab_title(tfilter)
        from ...tui.views.summary import TorrentSummaryWidget
        TorrentSummaryWidget_keymapped = self.tui.keymap.wrap(TorrentSummaryWidget,
                                                              context='torrent')
        summaryw = TorrentSummaryWidget_keymapped(self.srvapi, tid, title=title_str)
        tabid = self.tui.tabs.load(make_titlew(summaryw.title), summaryw)

        def set_tab_title(text):
            self.tui.tabs.set_title(make_titlew(text), position=tabid)
        summaryw.title_updater = set_tab_title

        return True


class AddTorrentsCmd(base.AddTorrentsCmdbase,
                     mixin.polling_frenzy, mixin.make_request):
    provides = {'tui'}


class MoveTorrentsCmd(base.MoveTorrentsCmdbase,
                      mixin.polling_frenzy, mixin.make_request, mixin.select_torrents):
    provides = {'tui'}


class RemoveTorrentsCmd(base.RemoveTorrentsCmdbase,
                        mixin.polling_frenzy, mixin.make_request, mixin.select_torrents):
    provides = {'tui'}


class StartTorrentsCmd(base.StartTorrentsCmdbase,
                       mixin.polling_frenzy, mixin.make_request, mixin.select_torrents):
    provides = {'tui'}


class StopTorrentsCmd(base.StopTorrentsCmdbase,
                      mixin.polling_frenzy, mixin.make_request, mixin.select_torrents):
    provides = {'tui'}


class VerifyTorrentsCmd(base.VerifyTorrentsCmdbase,
                        mixin.make_request, mixin.select_torrents):
    provides = {'tui'}
