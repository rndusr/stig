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

"""TUI and CLI specs for torrent list columns"""

from . import ColumnBase
from ..utils import stralign


COLUMNS = {}

class Filename(ColumnBase):
    header = {'left': 'Filename'}
    align = 'left'
    width = None

    def get_value(self):
        return self.data['name']

    def _crop_and_align(self, name, width, side):
        return stralign(name, width, side)

COLUMNS['name'] = Filename


class Size(ColumnBase):
    header = {'left': 'Size', 'right': '?'}
    width = 6

    def get_value(self):
        return self.data['size-total']

    def get_raw(self):
        return int(self.get_value())

    @classmethod
    def set_unit(cls, unit):
        cls.header['right'] = unit

COLUMNS['size'] = Size


class Downloaded(ColumnBase):
    header = {'left': 'Dn', 'right': '?'}
    width = 6

    def get_value(self):
        return self.data['size-downloaded']

    def get_raw(self):
        return int(self.get_value())

    @classmethod
    def set_unit(cls, unit):
        cls.header['right'] = unit

COLUMNS['downloaded'] = Downloaded


class Progress(ColumnBase):
    header = {'right': '%'}
    width = 4

    def get_value(self):
        return self.data['progress']

    def get_raw(self):
        return int(self.get_value())

COLUMNS['progress'] = Progress


class Priority(ColumnBase):
    header = {'left': 'Priority'}
    width = 4
    align = 'left'

    def get_value(self):
        val = self.get_raw()
        return '' if val == 'normal' else val

    def get_raw(self):
        return 'shun' if self.data['is-wanted'] is False else self.data['priority']

COLUMNS['priority'] = Priority




class TorrentFileDirectory(dict):
    def __hash__(self):
        return hash(self['path'])

    def __repr__(self):
        return '<{} {!r}>'.format(type(self).__name__, self['path'])

def create_directory_data(name, tree, filtered_count=0):
    # Create a mapping that has the same keys as a TorrentFile instance.
    # Each value recursively summarizes the values of all the TorrentFiles
    # in `tree`.

    tfiles = tuple(tree.files)

    def sum_size(tfiles, key):
        sizes = tuple(tfile[key] for tfile in tfiles)
        # Preserve the original type (Number)
        first_size = sizes[0]
        start_value = type(first_size)(0, unit=first_size.unit, prefix=first_size.prefix)
        return sum(sizes, start_value)

    def sum_priority(tfiles):
        if len(set(tfile['priority'] for tfile in tfiles)) == 1:
            return tfiles[0]['priority']
        else:
            return ''

    data = {'size-downloaded': sum_size(tfiles, 'size-downloaded'),
            'size-total': sum_size(tfiles, 'size-total'),
            'priority': sum_priority(tfiles),
            'is-wanted': True}

    data['name'] = create_directory_name(name, filtered_count)

    progress_cls = type(tfiles[0]['progress'])
    data['progress'] = progress_cls(data['size-downloaded'] / data['size-total'] * 100)
    data['tid'] = tfiles[0]['tid']
    data['path'] = tree.path
    data['id'] = frozenset(tf['id'] for tf in tfiles)
    return TorrentFileDirectory(data)


def create_directory_name(name, filtered_count):
    if filtered_count > 0:
        return '%s (%d file%s filtered)' % (name, filtered_count,
                                            '' if filtered_count == 1 else 's')
    else:
        return str(name)
