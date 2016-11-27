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

from .group import Group


class Table():
    """Manage rows, columns and headers as in a table

    `columns`: Dictionary that maps column IDs to column classes

    A column class is any class that creates a cell widget when called without
    arguments and has the attributes 'header' and 'width'.

        - 'header' is a cell widget that is displayed at the top of the
          column.

        - 'width' is passed on to the 'options' argument of Group.add()

    By setting the `columns` property to column IDs, columns are displayed or
    hidden in each existing or newly added row.
    """
    def __init__(self, **columns):
        self._colspecs = columns
        self._enabled_columns = []
        self._headers = Group(cls=urwid.Columns, dividechars=1)
        self._members = {}
        self.columns = columns

    def register(self, member_id):
        """Add a new row

        Create a new Group(cls=Columns) object and fill it with enabled column
        cells which can then be retrieved with `get_row(member_id)`.
        """
        member = Group(cls=urwid.Columns, dividechars=1)
        for colname in self._enabled_columns:
            cellcls = self._colspecs[colname]
            cellwidget = cellcls()
            member.add(colname, cellwidget, options=cellcls.width, removable=True)
        self._members[member_id] = member

    def get_row(self, member_id):
        """Return a row, i.e. a Group(cls=Columns) object created by register()"""
        return self._members[member_id]

    @property
    def headers(self):
        """Header row (a Group(cls=Columns) object)"""
        return self._headers

    @property
    def columns(self):
        """Currently enabled/displayed column IDs"""
        return self._enabled_columns

    @columns.setter
    def columns(self, columns):
        for col in columns:
            if col not in self._colspecs:
                raise ValueError('Unknown column name: {!r}'.format(col))

        # Remove all columns
        self._headers.clear()
        for member in self._members.values():
            member.clear()
        self._enabled_columns = []

        # Add wanted columns
        for colname in columns:
            # Add header
            cellcls = self._colspecs[colname]
            self._headers.add(colname, cellcls.header, options=cellcls.width, removable=True)
            self._enabled_columns.append(colname)

            # Add new column to all members
            for member in self._members.values():
                cellwidget = cellcls()
                member.add(colname, cellwidget, options=cellcls.width, removable=True)

    def clear(self):
        """Remove all registered rows"""
        self._members = {}


class ColumnHeaderWidget(urwid.WidgetWrap):
    """Column widget with left and right text"""

    def __init__(self, left='', right=''):
        self._left = urwid.Text(left, wrap='clip')
        self._right = urwid.Text(right, wrap='clip')
        widget = urwid.Columns([self._left, ('pack', self._right)],
                               dividechars=0)
        super().__init__(widget)

    @property
    def left(self):
        """String on the left side"""
        return self._left.text

    @left.setter
    def left(self, string):
        self._left.set_text(string)

    @property
    def right(self):
        """String on the right side"""
        return self._right.text

    @right.setter
    def right(self, string):
        self._right.set_text(string)
