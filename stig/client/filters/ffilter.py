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
from . import (BoolFilterSpec, CmpFilterSpec, Filter, FilterChain)


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
    }

    COMPARATIVE_FILTERS = {
        'name': CmpFilterSpec(
            lambda f, op, v: op(f['name'], v),
            description='Match VALUE against file name',
            value_type=TorrentFile.TYPES['name']),
        'size': CmpFilterSpec(
            lambda f, op, v: op(f['size-total'], v),
            aliases=(),
            description='Match VALUE against file size',
            value_type=TorrentFile.TYPES['size-total']),
        'downloaded': CmpFilterSpec(
            lambda f, op, v: op(f['size-downloaded'], v),
            aliases=('down',),
            description='Match VALUE against downloaded bytes',
            value_type=TorrentFile.TYPES['size-downloaded']),
        'priority': CmpFilterSpec(
            lambda f, op, v: op(f['priority'], v),
            aliases=('prio',),
            description='Match VALUE against file download priority (low, normal or high)',
            value_type=TorrentFile.TYPES['priority']),
        'progress': CmpFilterSpec(
            lambda f, op, v: op(f['progress'], v),
            aliases=('percent',),
            description='Match VALUE against percent downloaded',
            value_type=TorrentFile.TYPES['progress']),
    }


class TorrentFileFilter(FilterChain):
    """One or more filters combined with & and | operators"""
    filterclass = SingleTorrentFileFilter
