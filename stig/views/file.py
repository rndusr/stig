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

"""TUI and CLI specs for file list columns"""

from ..logging import make_logger
log = make_logger(__name__)

from . import (ColumnBase, _ensure_hide_unit)


COLUMNS = {}
ALIASES = { 'n'    : 'name', 'filename': 'name',
            'sz'   : 'size',
            'dn'   : 'downloaded',
            '%dn'  : '%downloaded',
            'prio' : 'priority',
            'mark' : 'marked' }


class Filename(ColumnBase):
    header = {'left': 'Filename'}
    align = 'left'
    width = None
    min_width = 10
    may_have_wide_chars = True

    def get_value(self):
        return self.data['name']

COLUMNS['name'] = Filename


class Size(ColumnBase):
    header = {'left': 'Size', 'right': '?'}
    width = 6
    min_width = 6

    def get_value(self):
        return self._from_cache(_ensure_hide_unit, self.data['size-total'])

    @classmethod
    def set_unit(cls, unit):
        cls.header['right'] = unit

COLUMNS['size'] = Size


class Downloaded(ColumnBase):
    header = {'left': 'Dn', 'right': '?'}
    width = 6
    min_width = 6

    def get_value(self):
        return self._from_cache(_ensure_hide_unit, self.data['size-downloaded'])

    @classmethod
    def set_unit(cls, unit):
        cls.header['right'] = unit

COLUMNS['downloaded'] = Downloaded


class PercentDownloaded(ColumnBase):
    header = {'right': '%'}
    width = 4
    min_width = 4

    def get_value(self):
        return self._from_cache(_ensure_hide_unit, self.data['%downloaded'])

COLUMNS['%downloaded'] = PercentDownloaded


class Priority(ColumnBase):
    header = {'left': 'Priority'}
    width = 4
    min_width = 4
    align = 'left'

    def get_value(self):
        val = self.get_raw_value()
        return '' if val == 'normal' else val

    def get_raw_value(self):
        return 'off' if self.data['is-wanted'] is False else self.data['priority']

COLUMNS['priority'] = Priority


class Marked(ColumnBase):
    interfaces = ('tui',)

COLUMNS['marked'] = Marked


import os
class TorrentFileDirectory(dict):
    """
    A mapping with the same keys as a TorrentFile instance but represents a directory

    Values recursively summarize the values of all the TorrentFiles in the subtree.
    """
    nodetype = 'parent'

    def __init__(self, name, tree, filtered_count=0):
        tfiles = tuple(tree.files)
        self.update({
            'id'              : tree.id,
            'tid'             : tfiles[0]['tid'],
            'name'            : self.create_directory_name(name, filtered_count),
            'path-absolute'   : os.path.join(tree.location, tree.path),
            'path-relative'   : tree.path,
            'location'        : tree.location,
            'size-total'      : self._sum_size(tfiles, 'size-total'),
            'size-downloaded' : self._sum_size(tfiles, 'size-downloaded'),
            'is-wanted'       : True,
            'priority'        : self._sum_priority(tfiles),
        })
        perc_dl_cls = type(tfiles[0]['%downloaded'])
        try:
            self['%downloaded'] = perc_dl_cls(self['size-downloaded'] / self['size-total'] * 100)
        except ZeroDivisionError:
            self['%downloaded'] = perc_dl_cls(0)

    @staticmethod
    def _sum_size(tfiles, key):
        sizes = tuple(tfile[key] for tfile in tfiles)
        # Preserve the original type (Float)
        first_size = sizes[0]
        start_value = type(first_size)(0, unit=first_size.unit, prefix=first_size.prefix)
        return sum(sizes, start_value)

    @staticmethod
    def _sum_priority(tfiles):
        if len(set(tfile['priority'] for tfile in tfiles)) == 1:
            return tfiles[0]['priority']
        else:
            return ''

    @staticmethod
    def create_directory_name(name, filtered_count):
        if filtered_count > 0:
            return '%s (%d file%s filtered)' % (name, filtered_count,
                                                '' if filtered_count == 1 else 's')
        else:
            return str(name)

    def __hash__(self):
        return hash(self['path'])

    def __repr__(self):
        return '<%s %s>' % (type(self).__name__, self['path-absolute'])
