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

from ..ttypes import TorrentPeer
from . import (BoolFilterSpec, CmpFilterSpec, Filter, FilterChain)


from .. import rdns
def _cmp_host_or_ip(p, op, v):
    hostname = rdns.gethostbyaddr_from_cache(p['ip'])
    if hostname is None:
        return op(p['ip'], v)
    else:
        return op(hostname, v)


class SingleTorrentPeerFilter(Filter):
    DEFAULT_FILTER = 'host'

    # Filters without arguments
    BOOLEAN_FILTERS = {
        'all': BoolFilterSpec(
            lambda p: True,
            aliases=('*',),
            description='All peers'),
        'uploading': BoolFilterSpec(
            lambda p: p['rate-up'] > 0,
            aliases=('upg',),
            description='Peers we are uploading to'),
        'downloading': BoolFilterSpec(
            lambda p: p['rate-down'] > 0,
            aliases=('dng',),
            description='Peers we are downloading from'),
        'seeding': BoolFilterSpec(
            lambda p: p['%downloaded'] >= 100,
            aliases=('sdg',),
            description='Peers that have downloaded all data'),
    }

    COMPARATIVE_FILTERS = {
        'downloaded': CmpFilterSpec(
            lambda p, op, v: op(p['tsize'] * (p['%downloaded']/100), v),
            aliases=('dn',),
            description='Match VALUE against number of bytes peer has downloaded',
            value_type=TorrentPeer.TYPES['tsize']),
        '%downloaded': CmpFilterSpec(
            lambda p, op, v: op(p['%downloaded'], v),
            aliases=('%dn',),
            description='Match VALUE against percentage of bytes peer has downloaded',
            value_type=TorrentPeer.TYPES['%downloaded']),
        'client': CmpFilterSpec(
            lambda p, op, v: op(p['client'], v),
            aliases=('cl',),
            description='Match VALUE against peer client',
            value_type=TorrentPeer.TYPES['client']),
        'country': CmpFilterSpec(
            lambda p, op, v: op(p['country'], v),
            aliases=('cn',),
            description='Match VALUE against peer country',
            value_type=TorrentPeer.TYPES['country']),
        'host': CmpFilterSpec(
            _cmp_host_or_ip,
            description='Match VALUE against peer IP address',
            value_type=TorrentPeer.TYPES['ip']),
        'port': CmpFilterSpec(
            lambda p, op, v: op(p['port'], v),
            description='Match VALUE against peer port',
            value_type=TorrentPeer.TYPES['port']),
    }


class TorrentPeerFilter(FilterChain):
    """One or more filters combined with & and | operators"""
    filterclass = SingleTorrentPeerFilter
