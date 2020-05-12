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

from .. import rdns
from ..ttypes import TorrentPeer
from .base import BoolFilterSpec, CmpFilterSpec, Filter, FilterChain, FilterSpecDict


def _cmp_host_or_ip(p, op, v):
    hostname = rdns.gethostbyaddr_from_cache(p['ip'])
    if hostname is None:
        return op(p['ip'], v)
    else:
        return op(hostname, v)

class _BoolFilterSpec(BoolFilterSpec):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, needed_keys=('peers',), **kwargs)

class _CmpFilterSpec(CmpFilterSpec):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, needed_keys=('peers',), **kwargs)

class _SingleFilter(Filter):
    DEFAULT_FILTER = 'host'

    BOOLEAN_FILTERS = FilterSpecDict({
        'all'         : _BoolFilterSpec(None,
                                        aliases=('*',),
                                        description='All peers'),
        'uploading'   : _BoolFilterSpec(lambda p: p['rate-up'] > 0,
                                        aliases=('upg',),
                                        description='Peers we are uploading to'),
        'downloading' : _BoolFilterSpec(lambda p: p['rate-down'] > 0,
                                        aliases=('dng',),
                                        description='Peers we are downloading from'),
        'seeding'     : _BoolFilterSpec(lambda p: p['%downloaded'] >= 100,
                                        aliases=('sdg',),
                                        description='Peers that have downloaded all data'),
    })

    COMPARATIVE_FILTERS = FilterSpecDict({
        'downloaded'  : _CmpFilterSpec(value_getter=lambda p: p['downloaded'],
                                       value_type=TorrentPeer.TYPES['downloaded'],
                                       as_bool=lambda p: p['downloaded'] > 0,
                                       aliases=('dn',),
                                       description='Match VALUE against number of bytes peer has downloaded'),
        '%downloaded' : _CmpFilterSpec(value_getter=lambda p: p['%downloaded'],
                                       value_type=TorrentPeer.TYPES['%downloaded'],
                                       aliases=('%dn',),
                                       description='Match VALUE against percentage of bytes peer has downloaded'),
        'client'      : _CmpFilterSpec(value_getter=lambda p: p['client'],
                                       value_type=TorrentPeer.TYPES['client'],
                                       aliases=('cl',),
                                       description='Match VALUE against peer client'),
        'host'        : _CmpFilterSpec(value_getter=lambda p: rdns.gethostbyaddr_from_cache(p['ip']) or p['ip'],
                                       value_type=TorrentPeer.TYPES['ip'],
                                       description='Match VALUE against peer host name or IP address'),
        'port'        : _CmpFilterSpec(value_getter=lambda p: p['port'],
                                       value_type=TorrentPeer.TYPES['port'],
                                       description='Match VALUE against peer port'),
    })


class PeerFilter(FilterChain):
    """One or more filters combined with & and | operators"""
    filterclass = _SingleFilter
