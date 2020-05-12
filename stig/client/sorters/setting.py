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

from .base import SorterBase, SortSpec


class _SortSpec(SortSpec):
    def __init__(self, *args, description='', **kwargs):
        description = 'Sort settings by %s' % description
        super().__init__(*args, description=description, **kwargs)


class SettingSorter(SorterBase):
    DEFAULT_SORT = 'name'
    SORTSPECS = {
        'name'        : _SortSpec(lambda s: s['id'],
                                  description='name'),
        # repr() because values have incompatible types
        'value'       : _SortSpec(lambda s: repr(s['value']).casefold(),
                                  description='value'),
        'default'     : _SortSpec(lambda s: repr(s['default']).casefold(),
                                  description='default'),
        'description' : _SortSpec(lambda s: s['description'],
                                  description='description'),
    }
