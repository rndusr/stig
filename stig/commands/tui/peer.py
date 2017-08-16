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

from ..base import peer as base
from . import _mixin as mixin
from .. import (ExpectedResource, InitCommand)
from ._common import make_tab_title_widget

from functools import partial


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

        from ...tui.views.peerlist import PeerListWidget
        plistw = PeerListWidget(self.srvapi, self.tui.keymap,
                                tfilter=tfilter, pfilter=pfilter,
                                sort=sort, columns=columns, title=title_str)
        tabid = self.tui.tabs.load(make_titlew(plistw.title), plistw)

        def set_tab_title(text, count):
            self.tui.tabs.set_title(make_titlew(text, count), position=tabid)
        plistw.title_updater = set_tab_title

        return True
