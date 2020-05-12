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

from .. import rdns
from .base import SorterBase, SortSpec


class _SortSpec(SortSpec):
    def __init__(self, *args, description='', **kwargs):
        description = 'Sort peers by %s' % description
        super().__init__(*args, description=description, **kwargs)


def _get_hostname_or_ip(torrent):
    ip = torrent['ip']
    hostname = rdns.gethostbyaddr_from_cache(ip)
    return ip if hostname is None else hostname


class PeerSorter(SorterBase):
    DEFAULT_SORT = 'torrent'
    SORTSPECS = {
        'torrent'     : _SortSpec(lambda t: t['tname'].casefold(),
                                  description='torrent name'),
        '%downloaded' : _SortSpec(lambda t: t['%downloaded'],
                                  aliases=('%dn',),
                                  description='download progress'),
        'rate-up'     : _SortSpec(lambda t: t['rate-up'],
                                  aliases=('rup',),
                                  description='upload rate (from our perspective)'),
        'rate-down'   : _SortSpec(lambda t: t['rate-down'],
                                  aliases=('rdn',),
                                  description='download rate (from our perspective)'),
        'rate-est'    : _SortSpec(lambda t: t['rate-est'],
                                  aliases=('re',),
                                  description='estimated overall download rate'),
        'rate'        : _SortSpec(lambda t: t['rate-up'] + t['rate-down'],
                                  aliases=('r',),
                                  description='combined download and upload rate'),
        'eta'         : _SortSpec(lambda t: t['eta'],
                                  description='estimated remaining download time'),
        'client'      : _SortSpec(lambda t: t['client'].casefold(),
                                  aliases=('cl',),
                                  description='client name'),
        'host'        : _SortSpec(_get_hostname_or_ip,
                                  description='IP address or hostname'),
        'port'        : _SortSpec(lambda t: t['port'],
                                  description='port number'),
    }
