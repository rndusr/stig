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
from .base import BoolFilterSpec, CmpFilterSpec, Filter, FilterChain, FilterSpecDict


class _BoolFilterSpec(BoolFilterSpec):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, needed_keys=('files',), **kwargs)

class _CmpFilterSpec(CmpFilterSpec):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, needed_keys=('files',), **kwargs)

class _SingleFilter(Filter):
    DEFAULT_FILTER = 'name'

    BOOLEAN_FILTERS = FilterSpecDict({
        'all'      : _BoolFilterSpec(None,
                                     aliases=('*',),
                                     description='All files'),
        'wanted'   : _BoolFilterSpec(lambda f: f['is-wanted'],
                                     description='Wanted files'),
        'complete' : _BoolFilterSpec(lambda f: f['%downloaded'] >= 100,
                                     aliases=('cmp',),
                                     description='Fully downloaded files'),
    })

    COMPARATIVE_FILTERS = FilterSpecDict({
        'name'        : _CmpFilterSpec(value_getter=lambda f: f['name'],
                                       value_type=TorrentFile.TYPES['name'],
                                       aliases=('n',),
                                       description='Match VALUE against file name'),
        'path'        : _CmpFilterSpec(value_getter=lambda f: f['path-absolute'],
                                       value_type=TorrentFile.TYPES['path-absolute'],
                                       aliases=('dir',),
                                       description='Match VALUE against file path'),
        'size'        : _CmpFilterSpec(value_getter=lambda f: f['size-total'],
                                       value_type=TorrentFile.TYPES['size-total'],
                                       aliases=('sz',),
                                       description='Match VALUE against file size'),
        'downloaded'  : _CmpFilterSpec(value_getter=lambda f: f['size-downloaded'],
                                       value_type=TorrentFile.TYPES['size-downloaded'],
                                       as_bool=lambda f: f['%downloaded'] >= 100,
                                       aliases=('dn',),
                                       description='Match VALUE against downloaded bytes'),
        '%downloaded' : _CmpFilterSpec(value_getter=lambda f: f['%downloaded'],
                                       value_type=TorrentFile.TYPES['%downloaded'],
                                       as_bool=lambda f: f['%downloaded'] >= 100,
                                       aliases=('%dn',),
                                       description='Match VALUE against percentage of downloaded bytes'),
        'priority'    : _CmpFilterSpec(value_getter=lambda f: f['priority'],
                                       value_type=TorrentFile.TYPES['priority'],
                                       as_bool=lambda f: f['priority'] != 0,  # Any non-normal priority
                                       aliases=('prio',),
                                       description='Match VALUE against download priority (off, low, normal, high)'),
    })


class FileFilter(FilterChain):
    """One or more filters combined with & and | operators"""
    filterclass = _SingleFilter
