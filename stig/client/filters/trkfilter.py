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
VALUETYPES = TorrentTracker.TYPES
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
            needed_keys=('tier',),
            value_type=VALUETYPES['tier']),
        'domain': CmpFilterSpec(
            lambda trk, op, v: op(trk['domain'], v),
            description='Match VALUE against domain from announce URL',
            aliases=('host',),
            needed_keys=('domain',),
            value_type=VALUETYPES['domain']),
        'url-announce': CmpFilterSpec(
            lambda trk, op, v: op(trk['url-announce'], v),
            description='Match VALUE against announce URL',
            needed_keys=('url-announce',),
            value_type=VALUETYPES['url-announce']),
        'url-scrape': CmpFilterSpec(
            lambda trk, op, v: op(trk['url-scrape'], v),
            description='Match VALUE against scrape URL',
            needed_keys=('url-scrape',),
            value_type=VALUETYPES['url-scrape']),
        'state': CmpFilterSpec(
            lambda trk, op, v: op(trk['state'], v),
            description="Match VALUE against tracker state (inactive, waiting, queued, announcing, scraping)",
            needed_keys=('state',),
            value_type=VALUETYPES['error']),
        'error': CmpFilterSpec(
            lambda trk, op, v: op(trk['error'], v),
            description='Match VALUE against error message from tracker',
            needed_keys=('error',),
            value_type=VALUETYPES['error']),
        'downloads': CmpFilterSpec(
            lambda trk, op, v: op(trk['count-downloads'], v),
            description='Match VALUE against number of known downloads',
            needed_keys=('count-downloads',),
            value_type=VALUETYPES['count-downloads']),
        'leeches': CmpFilterSpec(
            lambda trk, op, v: op(trk['count-leeches'], v),
            description='Match VALUE against number of known downloading peers',
            needed_keys=('count-leeches',),
            value_type=VALUETYPES['count-leeches']),
        'seeds': CmpFilterSpec(
            lambda trk, op, v: op(trk['count-seeds'], v),
            description='Match VALUE against number of known seeding peers',
            needed_keys=('count-seeds',),
            value_type=VALUETYPES['count-seeds']),
        'last-announce': CmpFilterSpec(
            lambda trk, op, v: op(trk['time-last-announce'], v),
            description='Match VALUE against last time of a successful announce',
            value_type=VALUETYPES['time-last-announce'],
            needed_keys=('time-last-announce',),
            value_convert=VALUETYPES['time-last-announce'].from_string),
        'next-announce': CmpFilterSpec(
            lambda trk, op, v: op(trk['time-next-announce'], v),
            description='Match VALUE against next time of a successful announce',
            value_type=VALUETYPES['time-next-announce'],
            needed_keys=('time-next-announce',),
            value_convert=VALUETYPES['time-next-announce'].from_string),
        'last-scrape': CmpFilterSpec(
            lambda trk, op, v: op(trk['time-last-scrape'], v),
            description='Match VALUE against last time of a successful scrape',
            value_type=VALUETYPES['time-last-scrape'],
            needed_keys=('time-last-scrape',),
            value_convert=VALUETYPES['time-last-scrape'].from_string),
        'next-scrape': CmpFilterSpec(
            lambda trk, op, v: op(trk['time-next-scrape'], v),
            description='Match VALUE against next time of a successful scrape',
            value_type=VALUETYPES['time-next-scrape'],
            needed_keys=('time-next-scrape',),
            value_convert=VALUETYPES['time-next-scrape'].from_string),
    }


class TorrentTrackerFilter(FilterChain):
    """One or more filters combined with & and | operators"""
    filterclass = SingleTrackerFilter
