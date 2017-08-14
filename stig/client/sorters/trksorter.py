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

from . import (SortSpecBase, SorterBase)

class _SortSpec(SortSpecBase):
    def __init__(self, *args, description='', **kwargs):
        description = 'Sort tracker by %s' % description
        super().__init__(*args, description=description, **kwargs)


class TorrentTrackerSorter(SorterBase):
    SORTSPECS = {
        'torrent':    _SortSpec(lambda t: t['tname'].lower(),
                                description='torrent name'),
        'tier':       _SortSpec(lambda t: t['tier'],
                                description='tier number'),
        'domain':     _SortSpec(lambda t: t['domain'],
                                description='domain from announce URL',
                                aliases=('host',)),
        'state':      _SortSpec(lambda t: t['state'],
                                description='tracker state'),
        'error':      _SortSpec(lambda t: t['error'],
                                description='error message'),
    }
    DEFAULT_SORT = 'torrent'
