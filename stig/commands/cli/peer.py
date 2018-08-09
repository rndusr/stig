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

from ..base import peer as base
from . import _mixin as mixin
from .. import (ExpectedResource, CmdError)
from ._table import print_table


class ListPeersCmd(base.ListPeersCmdbase,
                   mixin.make_request, mixin.select_torrents):
    provides = {'cli'}
    srvapi = ExpectedResource

    async def make_peer_list(self, tfilter, pfilter, sort, columns):
        response = await self.make_request(
            self.srvapi.torrent.torrents(tfilter, keys=('name', 'peers')),
            quiet=True)
        torrents = response.torrents

        if len(torrents) < 1:
            raise CmdError()

        if pfilter is None:
            filter_peers = lambda peers: peers
        else:
            filter_peers = lambda peers: pfilter.apply(peers)

        peerlist = []
        for torrent in sorted(torrents, key=lambda t: t['name'].lower()):
            peerlist.extend(filter_peers(torrent['peers']))

        # Pre-lookup peers' IPs
        from ...main import localcfg
        if 'host' in columns and localcfg['reverse-dns']:
            from ...client import rdns
            rdns.query(*(p['ip'] for p in peerlist))

        sort.apply(peerlist, inplace=True)

        if peerlist:
            from ...views.peer import COLUMNS as PEER_COLUMNS
            print_table(peerlist, columns, PEER_COLUMNS)
        else:
            filter_is_relevant = lambda f: f and str(f) != 'all'

            if filter_is_relevant(pfilter):
                errmsg = 'No matching peers'
            else:
                errmsg = 'No peers'

            if filter_is_relevant(tfilter):
                errmsg += ' in {} torrents'.format(tfilter)

            if filter_is_relevant(pfilter):
                errmsg += ': {}'.format(pfilter)

            raise CmdError(errmsg)
