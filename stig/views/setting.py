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

"""TUI and CLI specs for setting list columns"""

from . import ColumnBase


COLUMNS = {}
ALIASES = {}


class Name(ColumnBase):
    header = {'left': 'Name'}
    align = 'left'
    width = 25

    def get_value(self):
        return self.data['id']

COLUMNS['name'] = Name


class Value(ColumnBase):
    header = {'left': 'Value'}
    align = 'left'
    width = None
    wrap = 'space'

    def get_raw_value(self):
        return self.data['value']

    def get_value(self):
        value = self.data['value']
        if hasattr(value, 'prettified'):
            return value.prettified
        else:
            return value

COLUMNS['value'] = Value


class Default(ColumnBase):
    header = {'left': 'Default'}
    align = 'left'
    width = None
    wrap = 'space'

    def get_raw_value(self):
        return self.data['default']

    def get_value(self):
        value = self.data['default']
        # Paths are prettified by replacing '~' with $HOME
        if hasattr(value, 'prettified'):
            return value.prettified
        else:
            return value

COLUMNS['default'] = Default


class Description(ColumnBase):
    header = {'left': 'Description'}
    align = 'left'
    width = None
    wrap = 'space'

    def get_value(self):
        return self.data['description']

COLUMNS['description'] = Description
