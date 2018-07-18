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


class ListPeersCmd(base.ListPeersCmdbase,
                   mixin.make_request,
                   mixin.select_torrents,
                   mixin.create_list_widget):
    provides = {'tui'}

    def make_peer_list(self, tfilter, pfilter, sort, columns):
        from ...tui.views.peer_list import PeerListWidget
        self.create_list_widget(PeerListWidget, theme_name='peerlist',
                                tfilter=tfilter, pfilter=pfilter,
                                sort=sort, columns=columns,
                                markable_items=False)
