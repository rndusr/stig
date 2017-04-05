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

"""Filtering TorrentFiles by various values"""

from ..tkeys import (TorrentFile, TorrentFilePriority)
from . import (BoolFilterSpec, make_cmp_filter, Filter, FilterChain)

def _make_cmp_filter(*args, **kwargs):
    return make_cmp_filter(TorrentFile.TYPES, *args, **kwargs)


class SingleTorrentFileFilter(Filter):
    DEFAULT_FILTER = 'name'

    # Filters without arguments
    BOOLEAN_FILTERS = {
        'all': BoolFilterSpec(
            lambda f: True,
            aliases=('*',),
            description='All files'),
        'wanted': BoolFilterSpec(
            lambda f: f['is-wanted'],
            description='Wanted files'),
        'complete': BoolFilterSpec(
            lambda f: f['progress'] >= 100,
            description='Fully downloaded files'),
    }

    COMPARATIVE_FILTERS = {
        'name': _make_cmp_filter('name', 'Match VALUE against file name'),
        'path': _make_cmp_filter('path', 'Match VALUE against path in torrent'),
        'size': _make_cmp_filter('size-total', 'Match VALUE against file size'),
        'downloaded': _make_cmp_filter('size-downloaded',
                                       'Match VALUE against number of downloaded bytes',
                                       aliases=('down',)),
        '%downloaded': _make_cmp_filter('progress',
                                        'Match VALUE against percentage of downloaded bytes',
                                        aliases=('%down',)),
        'priority': _make_cmp_filter('priority',
                                     'Match VALUE against download priority (low, normal, high or shun)',
                                     aliases=('prio',)),
    }


class TorrentFileFilter(FilterChain):
    """One or more filters combined with & and | operators"""
    filterclass = SingleTorrentFileFilter
