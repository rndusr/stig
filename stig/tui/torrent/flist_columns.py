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

"""Column classes that display information in torrent file lists"""

import urwid

from ..table import ColumnHeaderWidget
from . import (Style, CellWidgetBase)
from ...columns.flist import COLUMNS as _COLUMNS


TUICOLUMNS = {}

class Filename(_COLUMNS['name'], CellWidgetBase):
    width = ('weight', 100)
    style = Style(prefix='filelist.name', focusable=True,
                  extras=('header',), modes=('file', 'folder', 'filtered'))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['name'].header),
                           style.attrs('header'))

    def get_mode(self):
        if isinstance(self.data['id'], int):
            return 'file'
        else:
            return 'folder'

TUICOLUMNS['name'] = Filename


class Size(_COLUMNS['size'], CellWidgetBase):
    style = Style(prefix='filelist.size', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['size'].header),
                           style.attrs('header'))

    @classmethod
    def set_unit(cls, unit):
        cls.header.original_widget.right = _COLUMNS['size'].header['right']

TUICOLUMNS['size'] = Size


class Downloaded(_COLUMNS['downloaded'], CellWidgetBase):
    style = Style(prefix='filelist.downloaded', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['downloaded'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.data['progress'] < 100 else None

    @classmethod
    def set_unit(cls, unit):
        cls.header.original_widget.right = _COLUMNS['downloaded'].header['right']

TUICOLUMNS['downloaded'] = Downloaded


class Progress(_COLUMNS['progress'], CellWidgetBase):
    style = Style(prefix='filelist.progress', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['progress'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value < 100 else ''

TUICOLUMNS['progress'] = Progress


class Priority(_COLUMNS['priority'], CellWidgetBase):
    style = Style(prefix='filelist.priority', focusable=True,
                  extras=('header',), modes=('low', 'high', 'shun'))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['priority'].header),
                           style.attrs('header'))

    def get_mode(self):
        val = self.value
        return val if val in ('low', 'high', 'shun') else None

TUICOLUMNS['priority'] = Priority
