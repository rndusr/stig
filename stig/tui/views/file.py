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
from ...views.file import COLUMNS as _COLUMNS


TUICOLUMNS = {}


from .common_columns import MarkedBase
class Marked(MarkedBase):
    style = Style(prefix='filelist.marked', focusable=True, extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(), style.attrs('header'))

TUICOLUMNS['marked'] = Marked


from ...utils.string import normalize_unicode
class Filename(_COLUMNS['name'], CellWidgetBase):
    width = ('weight', 100)
    style = Style(prefix='filelist.name', focusable=True,
                  extras=('header',), modes=('file', 'folder', 'filtered'))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['name'].header),
                           style.attrs('header'))

    def get_mode(self):
        if self.data.nodetype == 'leaf':
            return 'file'
        else:
            return 'folder'

    def get_tui_value(self):
        return normalize_unicode(super().get_tui_value())

TUICOLUMNS['name'] = Filename


class Size(_COLUMNS['size'], CellWidgetBase):
    style = Style(prefix='filelist.size', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['size'].header),
                           style.attrs('header'))

TUICOLUMNS['size'] = Size


class Downloaded(_COLUMNS['downloaded'], CellWidgetBase):
    style = Style(prefix='filelist.downloaded', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['downloaded'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.data['%downloaded'] < 100 else None

TUICOLUMNS['downloaded'] = Downloaded


class PercentDownloaded(_COLUMNS['%downloaded'], CellWidgetBase):
    style = Style(prefix='filelist.%downloaded', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['%downloaded'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value < 100 else ''

TUICOLUMNS['%downloaded'] = PercentDownloaded


class Priority(_COLUMNS['priority'], CellWidgetBase):
    style = Style(prefix='filelist.priority', focusable=True,
                  extras=('header',), modes=('off', 'low', 'high'))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['priority'].header),
                           style.attrs('header'))

    def get_mode(self):
        val = self.value
        return val if val in ('off', 'low', 'high') else None

TUICOLUMNS['priority'] = Priority
