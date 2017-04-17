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

"""Torrent commands for the TUI"""

from ...logging import make_logger
log = make_logger(__name__)

from collections import abc
from functools import partial

from ..base import torrent as base
from . import mixin
from .. import ExpectedResource
from . import make_tab_title_widget


class AddTorrentsCmd(base.AddTorrentsCmdbase,
                     mixin.polling_frenzy, mixin.make_request):
    provides = {'tui'}


class AnnounceTorrentsCmd(base.AnnounceTorrentsCmdbase,
                          mixin.make_request, mixin.select_torrents):
    provides = {'tui'}


class ListTorrentsCmd(base.ListTorrentsCmdbase,
                      mixin.select_torrents, mixin.generate_tab_title):
    provides = {'tui'}
    tui = ExpectedResource

    async def make_tlist(self, tfilter, sort, columns):
        if 'marked' not in columns:
            columns.insert(0, 'marked')

        make_titlew = partial(make_tab_title_widget,
                              attr_unfocused='tabs.torrentlist.unfocused',
                              attr_focused='tabs.torrentlist.focused')

        title_str = await self.generate_tab_title(tfilter)

        from ...tui.torrent.tlist import TorrentListWidget
        tlistw = TorrentListWidget(tfilter=tfilter, sort=sort, columns=columns,
                                   title=title_str)
        tabid = self.tui.tabs.load(make_titlew(tlistw.title), tlistw)

        def set_tab_title(text):
            self.tui.tabs.set_title(make_titlew(text), position=tabid)
        tlistw.title_updater = set_tab_title

        return True


class ListFilesCmd(base.ListFilesCmdbase,
                   mixin.make_request, mixin.select_torrents, mixin.select_files,
                   mixin.generate_tab_title):
    provides = {'tui'}
    tui = ExpectedResource
    srvapi = ExpectedResource

    async def make_flist(self, tfilter, ffilter, columns):
        if 'marked' not in columns:
            columns.insert(0, 'marked')

        make_titlew = partial(make_tab_title_widget,
                              attr_unfocused='tabs.filelist.unfocused',
                              attr_focused='tabs.filelist.focused')

        title_str = await self.generate_tab_title(tfilter)

        from ...tui.torrent.flist import FileListWidget
        flistw = FileListWidget(self.srvapi, tfilter, ffilter, columns,
                                title=title_str)
        tabid = self.tui.tabs.load(make_titlew(flistw.title), flistw)

        def set_tab_title(text):
            self.tui.tabs.set_title(make_titlew(text), position=tabid)
        flistw.title_updater = set_tab_title

        return True


class ListPeersCmd(base.ListPeersCmdbase,
                   mixin.make_request, mixin.select_torrents, mixin.generate_tab_title):
    provides = {'tui'}
    tui = ExpectedResource
    srvapi = ExpectedResource

    async def make_plist(self, tfilter, pfilter, sort, columns):
        make_titlew = partial(make_tab_title_widget,
                              attr_unfocused='tabs.peerlist.unfocused',
                              attr_focused='tabs.peerlist.focused')

        title_str = await self.generate_tab_title(tfilter)

        from ...tui.torrent.plist import PeerListWidget
        plistw = PeerListWidget(self.srvapi, tfilter=tfilter, pfilter=pfilter,
                                sort=sort, columns=columns, title=title_str)
        tabid = self.tui.tabs.load(make_titlew(plistw.title), plistw)

        def set_tab_title(text):
            self.tui.tabs.set_title(make_titlew(text), position=tabid)
        plistw.title_updater = set_tab_title

        return True


class MoveTorrentsCmd(base.MoveTorrentsCmdbase,
                      mixin.polling_frenzy, mixin.make_request, mixin.select_torrents):
    provides = {'tui'}


class PriorityCmd(base.PriorityCmdbase,
                  mixin.polling_frenzy, mixin.make_request, mixin.select_torrents, mixin.select_files):
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
