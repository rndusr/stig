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
        description = 'Sort trackers by %s' % description
        super().__init__(*args, description=description, **kwargs)


class TorrentTrackerSorter(SorterBase):
    SORTSPECS = {
        'torrent':         _SortSpec(lambda t: t['tname'].lower(),
                                     description='torrent name'),
        'tier':            _SortSpec(lambda t: t['tier'],
                                     description='tier number'),
        'domain':          _SortSpec(lambda t: t['domain'],
                                     description='domain from announce URL',
                                     aliases=('host',)),
        'state':           _SortSpec(lambda t: t['state'],
                                     description='tracker state'),
        'error':           _SortSpec(lambda t: t['error'],
                                     description='error message'),
        'downloads':       _SortSpec(lambda t: t['count-downloads'],
                                     description='number of known downloads'),
        'leeches':         _SortSpec(lambda t: t['count-leeches'],
                                     description='number of known downloading peers'),
        'seeds':           _SortSpec(lambda t: t['count-seeds'],
                                     description='number of known seeding peers'),
        'last-announce':   _SortSpec(lambda t: t['time-last-announce'],
                                     aliases=('l-an',),
                                     description='last time the torrent was successfully announce'),
        'next-announce':   _SortSpec(lambda t: t['time-next-announce'],
                                     aliases=('n-an',),
                                     description='next time the torrent is announced'),
        'last-scrape':     _SortSpec(lambda t: t['time-last-scrape'],
                                     aliases=('l-sc',),
                                     description='last time the torrent was successfully scrape'),
        'next-scrape':     _SortSpec(lambda t: t['time-next-scrape'],
                                     aliases=('n-sc',),
                                     description='next time the torrent is scraped'),
    }
    DEFAULT_SORT = 'torrent'
