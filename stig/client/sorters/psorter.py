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


class TorrentPeerSorter(SorterBase):
    SORTSPECS = {
        'ip':         _SortSpec(lambda t: t['ip'],
                                description='IP address (alphabetically)'),
        'port':       _SortSpec(lambda t: t['port'],
                                description='port number'),
        'client':     _SortSpec(lambda t: t['client'].lower(),
                                description='client name'),
        'country':     _SortSpec(lambda t: t['country'].lower(),
                                 description='country'),
        'progress':   _SortSpec(lambda t: t['progress'],
                                description='downloading progress'),
        'rate-up':    _SortSpec(lambda t: t['rate-up'],
                                description='upload rate (from your perspective)'),
        'rate-down':  _SortSpec(lambda t: t['rate-down'],
                                description='download rate (from your perspective)'),
        'rate':       _SortSpec(lambda t: t['rate-up'] + t['rate-down'],
                                description='combined download and upload rate'),
        'eta':        _SortSpec(lambda t: t['eta'],
                                description='estimated time they need to finish'),
        'rate-est':   _SortSpec(lambda t: t['rate-est'],
                                description='estimated overall download rate'),
        'torrent':    _SortSpec(lambda t: t['tname'].lower(),
                                description='torrent name'),
    }
    DEFAULT_SORT = 'torrent'
