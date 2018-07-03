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
from . import (BoolFilterSpec, Filter, FilterChain, make_cmp_filter, CmpFilterSpec)
from . import (timestamp_or_timedelta, time_filter)


def _make_cmp_filter(*args, **kwargs):
    return make_cmp_filter(TorrentTracker.TYPES, *args, **kwargs)


class SingleTrackerFilter(Filter):
    DEFAULT_FILTER = 'domain'

    # Filters without arguments
    BOOLEAN_FILTERS = {
        'all': BoolFilterSpec(
            lambda trk: True,
            aliases=('*',),
            description='All trackers'),
        'alive': BoolFilterSpec(
            lambda trk: trk['error'] == '' or trk['status'] == 'inactive',
            description='Trackers we are trying to connect to'),
    }

    COMPARATIVE_FILTERS = {
        'tier'           : _make_cmp_filter('tier',
                                            description='Match VALUE against torrent tier'),
        'domain'         : _make_cmp_filter('domain',
                                            aliases=('dom',),
                                            description='Match VALUE against domain from announce URL'),
        'url-announce'   : _make_cmp_filter('url-announce',
                                            aliases=('an',),
                                            description='Match VALUE against announce URL'),
        'url-scrape'     : _make_cmp_filter('url-scrape',
                                            aliases=('sc',),
                                            description='Match VALUE against scrape URL'),
        'status'         : _make_cmp_filter('status',
                                            aliases=('st',),
                                            description=('Match VALUE against tracker status '
                                                         '(stopped, idle, queued, announcing, scraping)')),
        'error'          : _make_cmp_filter('error',
                                            aliases=('err',),
                                            description='Match VALUE against error message from tracker'),
        'downloads'      : _make_cmp_filter('count-downloads',
                                            aliases=('dns',),
                                            description='Match VALUE against number of known downloads'),
        'leeches'        : _make_cmp_filter('count-leeches',
                                            aliases=('lcs',),
                                            description='Match VALUE against number of known downloading peers'),
        'seeds'          : _make_cmp_filter('count-seeds',
                                            aliases=('sds',),
                                            description='Match VALUE against number of known seeding peers'),
        'last-announce': CmpFilterSpec(
            lambda t, op, v: time_filter(t['time-last-announce'], op, v),
            aliases=('lan',),
            description='Match VALUE against time of last announce',
            needed_keys=('time-last-announce',),
            value_type=TorrentTracker.TYPES['time-last-announce'],
            value_convert=lambda v: timestamp_or_timedelta(v, default_sign=-1),
        ),
        'next-announce': CmpFilterSpec(
            lambda t, op, v: time_filter(t['time-next-announce'], op, v),
            aliases=('nan',),
            description='Match VALUE against time of next announce',
            needed_keys=('time-next-announce',),
            value_type=TorrentTracker.TYPES['time-next-announce'],
            value_convert=lambda v: timestamp_or_timedelta(v, default_sign=1),
        ),
        'last-scrape': CmpFilterSpec(
            lambda t, op, v: time_filter(t['time-last-scrape'], op, v),
            aliases=('lsc',),
            description='Match VALUE against time of last scrape',
            needed_keys=('time-last-scrape',),
            value_type=TorrentTracker.TYPES['time-last-scrape'],
            value_convert=lambda v: timestamp_or_timedelta(v, default_sign=-1),
        ),
        'next-scrape': CmpFilterSpec(
            lambda t, op, v: time_filter(t['time-next-scrape'], op, v),
            aliases=('nsc',),
            description='Match VALUE against time of next scrape',
            needed_keys=('time-next-scrape',),
            value_type=TorrentTracker.TYPES['time-next-scrape'],
            value_convert=lambda v: timestamp_or_timedelta(v, default_sign=1),
        ),
    }


class TorrentTrackerFilter(FilterChain):
    """One or more filters combined with & and | operators"""
    filterclass = SingleTrackerFilter
