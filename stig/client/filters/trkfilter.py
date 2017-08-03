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

"""Filtering TrackerList items by various values"""

from ..ttypes import TorrentTracker
from . import (BoolFilterSpec, CmpFilterSpec, Filter, FilterChain)


class SingleTrackerFilter(Filter):
    DEFAULT_FILTER = 'domain'

    # Filters without arguments
    BOOLEAN_FILTERS = {
        'all': BoolFilterSpec(
            lambda trk: True,
            aliases=('*',),
            description='All trackers'),
        'alive': BoolFilterSpec(
            lambda trk: trk['error'] == '' or trk['state'] == 'inactive',
            description='Trackers we are trying to connect to'),
    }

    COMPARATIVE_FILTERS = {
        'tier': CmpFilterSpec(
            lambda trk, op, v: op(trk['tier'], v),
            description='Match VALUE against torrent tier',
            value_type=TorrentTracker.TYPES['tier']),
        'domain': CmpFilterSpec(
            lambda trk, op, v: op(trk['domain'], v),
            description='Match VALUE against domain from announce URL',
            aliases=('host',),
            value_type=TorrentTracker.TYPES['domain']),
        'url-announce': CmpFilterSpec(
            lambda trk, op, v: op(trk['url-announce'], v),
            description='Match VALUE against announce URL',
            value_type=TorrentTracker.TYPES['url-announce']),
        'url-scrape': CmpFilterSpec(
            lambda trk, op, v: op(trk['url-scrape'], v),
            description='Match VALUE against scrape URL',
            value_type=TorrentTracker.TYPES['url-scrape']),
        'state': CmpFilterSpec(
            lambda trk, op, v: op(trk['state'], v),
            description="Match VALUE against tracker state (inactive, waiting, queued, announcing, scraping)",
            value_type=TorrentTracker.TYPES['error']),
        'error': CmpFilterSpec(
            lambda trk, op, v: op(trk['error'], v),
            description='Match VALUE against error message from tracker',
            value_type=TorrentTracker.TYPES['error']),
    }


class TorrentTrackerFilter(FilterChain):
    """One or more filters combined with & and | operators"""
    filterclass = SingleTrackerFilter
