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
from ...views.tlist import COLUMNS as _COLUMNS

TUICOLUMNS = {}

class MarkedBase(_COLUMNS['marked'], CellWidgetBase):
    width = 1
    needed_keys = ()
    _marked_char = '#'
    _unmarked_char = ' '

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text.set_text(self._unmarked_char)
        self._is_marked = False

    @classmethod
    def set_marked_char(cls, char):
        cls._marked_char = str(char)
        cls.header.original_widget.left = cls._marked_char

    @classmethod
    def set_unmarked_char(cls, char):
        cls._unmarked_char = str(char)

    @property
    def is_marked(self):
        return self._is_marked

    @is_marked.setter
    def is_marked(self, is_marked):
        if is_marked:
            self.text.set_text(self._marked_char)
        else:
            self.text.set_text(self._unmarked_char)
        self._is_marked = is_marked

    def update(self, data):
        pass  # Ignore update data

    def __repr__(self):
        return '<{} {}>'.format(type(self).__name__, 'on' if self._is_marked else 'off')
