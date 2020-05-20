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
from .base import BoolFilterSpec, CmpFilterSpec, Filter, FilterChain, FilterSpecDict
from .utils import cmp_timestamp_or_timdelta, timestamp_or_timedelta


class _BoolFilterSpec(BoolFilterSpec):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, needed_keys=('trackers',), **kwargs)

class _CmpFilterSpec(CmpFilterSpec):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, needed_keys=('trackers',), **kwargs)

class _SingleFilter(Filter):
    DEFAULT_FILTER = 'domain'

    BOOLEAN_FILTERS = FilterSpecDict({
        'all'   : _BoolFilterSpec(None,
                                  aliases=('*',),
                                  description='All trackers'),
        'alive' : _BoolFilterSpec(lambda trk: trk['status'] != 'stopped',
                                  description='Trackers we are trying to connect to'),
    })

    COMPARATIVE_FILTERS = FilterSpecDict({
        'tier'           : _CmpFilterSpec(value_getter=lambda trk: trk['tier'],
                                         value_type=TorrentTracker.TYPES['tier'],
                                         as_bool=lambda trk: True,
                                         description='Match VALUE against tracker tier'),
        'domain'         : _CmpFilterSpec(value_getter=lambda trk: trk['domain'],
                                         value_type=TorrentTracker.TYPES['domain'],
                                         aliases=('dom', 'tracker'),
                                         description='Match VALUE against domain of announce URL'),
        'url-announce'   : _CmpFilterSpec(value_getter=lambda trk: trk['url-announce'],
                                         value_type=TorrentTracker.TYPES['url-announce'],
                                         aliases=('an',),
                                         description='Match VALUE against announce URL'),
        'url-scrape'     : _CmpFilterSpec(value_getter=lambda trk: trk['url-scrape'],
                                         value_type=TorrentTracker.TYPES['url-scrape'],
                                         aliases=('sc',),
                                         description='Match VALUE against scrape URL'),
        'status'         : _CmpFilterSpec(value_getter=lambda trk: trk['status'],
                                         value_type=TorrentTracker.TYPES['status'],
                                         aliases=('st',),
                                         description=('Match VALUE against tracker status '
                                                      '(stopped, idle, queued, announcing, scraping)')),
        'error'          : _CmpFilterSpec(value_getter=lambda trk: trk['error'],
                                         value_type=TorrentTracker.TYPES['error'],
                                         aliases=('err',),
                                         description='Match VALUE against error message from tracker'),
        'downloads'      : _CmpFilterSpec(value_getter=lambda trk: trk['count-downloads'],
                                         value_type=TorrentTracker.TYPES['count-downloads'],
                                         aliases=('dns',),
                                         description='Match VALUE against number of known downloads'),
        'leeches'        : _CmpFilterSpec(value_getter=lambda trk: trk['count-leeches'],
                                         value_type=TorrentTracker.TYPES['count-leeches'],
                                         aliases=('lcs',),
                                         description='Match VALUE against number of known downloads'),
        'seeds'          : _CmpFilterSpec(value_getter=lambda trk: trk['count-seeds'],
                                         value_type=TorrentTracker.TYPES['count-seeds'],
                                         aliases=('sds',),
                                         description='Match VALUE against number of known seeding peers'),
        'last-announce'  : _CmpFilterSpec(value_getter=lambda trk: trk['time-last-announce'],
                                         value_matcher=lambda trk, op, v: cmp_timestamp_or_timdelta(trk['time-last-announce'], op, v),
                                         value_type=TorrentTracker.TYPES['time-last-announce'],
                                         value_convert=lambda v: timestamp_or_timedelta(v, default_sign=-1),
                                         aliases=('lan',),
                                         description='Match VALUE against time of last announce'),
        'next-announce'  : _CmpFilterSpec(value_getter=lambda trk: trk['time-next-announce'],
                                         value_matcher=lambda trk, op, v: cmp_timestamp_or_timdelta(trk['time-next-announce'], op, v),
                                         value_type=TorrentTracker.TYPES['time-next-announce'],
                                         value_convert=lambda v: timestamp_or_timedelta(v, default_sign=1),
                                         aliases=('nan',),
                                         description='Match VALUE against time of next announce'),
        'last-scrape'    : _CmpFilterSpec(value_getter=lambda trk: trk['time-last-scrape'],
                                         value_matcher=lambda trk, op, v: cmp_timestamp_or_timdelta(trk['time-last-scrape'], op, v),
                                         value_type=TorrentTracker.TYPES['time-last-scrape'],
                                         value_convert=lambda v: timestamp_or_timedelta(v, default_sign=-1),
                                         aliases=('lsc',),
                                         description='Match VALUE against time of last scrape'),
        'next-scrape'    : _CmpFilterSpec(value_getter=lambda trk: trk['time-next-scrape'],
                                         value_matcher=lambda trk, op, v: cmp_timestamp_or_timdelta(trk['time-next-scrape'], op, v),
                                         value_type=TorrentTracker.TYPES['time-next-scrape'],
                                         value_convert=lambda v: timestamp_or_timedelta(v, default_sign=1),
                                         aliases=('nsc',),
                                         description='Match VALUE against time of next scrape'),
    })


class TrackerFilter(FilterChain):
    """One or more filters combined with & and | operators"""
    filterclass = _SingleFilter
