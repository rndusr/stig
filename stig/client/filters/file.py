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

from ..ttypes import TorrentFile
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
            lambda f: f['%downloaded'] >= 100,
            aliases=('comp',),
            description='Fully downloaded files'),
    }

    COMPARATIVE_FILTERS = {
        'name'        : _make_cmp_filter('name',
                                         'Match VALUE against file name',
                                         aliases=('n',)),
        'path'        : _make_cmp_filter('path-absolute',
                                         'Match VALUE against full file path',
                                         aliases=('dir',)),
        'size'        : _make_cmp_filter('size-total',
                                         'Match VALUE against file size',
                                         aliases=('sz',)),
        'downloaded'  : _make_cmp_filter('size-downloaded',
                                         'Match VALUE against number of downloaded bytes',
                                         aliases=('dn',)),
        '%downloaded' : _make_cmp_filter('%downloaded',
                                         'Match VALUE against percentage of downloaded bytes',
                                         aliases=('%dn',)),
        'priority'    : _make_cmp_filter('priority',
                                         'Match VALUE against download priority (off, low, normal, high)',
                                         aliases=('prio',)),
    }


class TorrentFileFilter(FilterChain):
    """One or more filters combined with & and | operators"""
    filterclass = SingleTorrentFileFilter
