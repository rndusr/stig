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

import urwid

from ..table import ColumnHeaderWidget
from . import (Style, CellWidgetBase)
from ...views.setting import COLUMNS as _COLUMNS


TUICOLUMNS = {}

class Name(_COLUMNS['name'], CellWidgetBase):
    style = Style(prefix='settinglist.name', focusable=True, extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['name'].header),
                           style.attrs('header'))

TUICOLUMNS['name'] = Name


class Value(_COLUMNS['value'], CellWidgetBase):
    width = ('weight', 100)
    style = Style(prefix='settinglist.value', focusable=True, extras=('header',),
                  modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['value'].header),
                           style.attrs('header'))

    def get_mode(self):
        default = self.data['default']
        value = self.data['value']
        if not self.data['id'].startswith('srv.') and value != default:
            return 'highlighted'

TUICOLUMNS['value'] = Value


class Default(_COLUMNS['default'], CellWidgetBase):
    width = ('weight', 100)
    style = Style(prefix='settinglist.default', focusable=True, extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['default'].header),
                           style.attrs('header'))

TUICOLUMNS['default'] = Default


class Description(_COLUMNS['description'], CellWidgetBase):
    width = ('weight', 100)
    style = Style(prefix='settinglist.description', focusable=True, extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['description'].header),
                           style.attrs('header'))

TUICOLUMNS['description'] = Description
