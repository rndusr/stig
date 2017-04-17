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

"""Filtering PeerList items by various values"""

from ..tkeys import TorrentPeer
from . import (BoolFilterSpec, CmpFilterSpec, Filter, FilterChain)


class SingleTorrentPeerFilter(Filter):
    DEFAULT_FILTER = None

    # Filters without arguments
    BOOLEAN_FILTERS = {
        'all': BoolFilterSpec(
            lambda p: True,
            aliases=('*',),
            description='All peers'),
        'uploading': BoolFilterSpec(
            lambda p: p['rate-up'] > 0,
            aliases=('ul',),
            description='Peers we are uploading to'),
        'downloading': BoolFilterSpec(
            lambda p: p['rate-down'] > 0,
            aliases=('dl',),
            description='Peers we are downloading from'),
        'seeding': BoolFilterSpec(
            lambda p: p['progress'] >= 100,
            aliases=('done',),
            description='Peers that have downloaded all data'),
    }

    COMPARATIVE_FILTERS = {
        'client': CmpFilterSpec(
            lambda p, op, v: op(p['client'], v),
            description='Match VALUE against peer client',
            value_type=TorrentPeer.TYPES['client']),
        'country': CmpFilterSpec(
            lambda p, op, v: op(p['country'], v),
            description='Match VALUE against peer country',
            value_type=TorrentPeer.TYPES['country']),
        'ip': CmpFilterSpec(
            lambda p, op, v: op(p['ip'], v),
            description='Match VALUE against peer IP address',
            value_type=TorrentPeer.TYPES['ip']),
        'port': CmpFilterSpec(
            lambda p, op, v: op(p['port'], v),
            description='Match VALUE against peer port',
            value_type=TorrentPeer.TYPES['port']),
        'downloaded': CmpFilterSpec(
            lambda p, op, v: op(p['tsize'] * (p['progress']/100), v),
            aliases=('down',),
            description='Match VALUE against number of bytes peer has downloaded',
            value_type=TorrentPeer.TYPES['tsize']),
        '%downloaded': CmpFilterSpec(
            lambda p, op, v: op(p['progress'], v),
            aliases=('%down',),
            description='Match VALUE against percentage of bytes peer has downloaded',
            value_type=TorrentPeer.TYPES['progress']),
    }


class TorrentPeerFilter(FilterChain):
    """One or more filters combined with & and | operators"""
    filterclass = SingleTorrentPeerFilter
