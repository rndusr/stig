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

from . import (SortSpecBase, SorterBase)

class _SortSpec(SortSpecBase):
    def __init__(self, *args, description='', **kwargs):
        description = 'Sort peers by %s' % description
        super().__init__(*args, description=description, **kwargs)


from .. import rdns
def _get_hostname_or_ip(torrent):
    ip = torrent['ip']
    hostname = rdns.gethostbyaddr_from_cache(ip)
    return ip if hostname is None else hostname


class TorrentPeerSorter(SorterBase):
    SORTSPECS = {
        'torrent'     : _SortSpec(lambda t: t['tname'].lower(),
                                  description='torrent name'),
        '%downloaded' : _SortSpec(lambda t: t['%downloaded'],
                                  aliases=('%dn',),
                                  description="peer's download progress"),
        'rate-up'     : _SortSpec(lambda t: t['rate-up'],
                                  aliases=('rup',),
                                  description='upload rate (from our perspective)'),
        'rate-down'   : _SortSpec(lambda t: t['rate-down'],
                                  aliases=('rdn',),
                                  description='download rate (from our perspective)'),
        'rate-est'    : _SortSpec(lambda t: t['rate-est'],
                                  aliases=('re',),
                                  description="peer's estimated overall download rate"),
        'rate'        : _SortSpec(lambda t: t['rate-up'] + t['rate-down'],
                                  aliases=('r',),
                                  description='combined download and upload rate'),
        'eta'         : _SortSpec(lambda t: t['eta'],
                                  description="peer's estimated remaining download time"),
        'client'      : _SortSpec(lambda t: t['client'].lower(),
                                  aliases=('cl',),
                                  description="peer's client name"),
        'country'     : _SortSpec(lambda t: t['country'].lower(),
                                  aliases=('cn',),
                                  description="peer's country"),
        'host'        : _SortSpec(_get_hostname_or_ip,
                                  description="peer's IP address or hostname"),
        'port'        : _SortSpec(lambda t: t['port'],
                                  description="peer's port number"),
    }
    DEFAULT_SORT = 'torrent'
