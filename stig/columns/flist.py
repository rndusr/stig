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

from ..logging import make_logger
log = make_logger(__name__)

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
