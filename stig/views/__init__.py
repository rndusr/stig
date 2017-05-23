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

"""Display specifications for tables and such"""

from ..logging import make_logger
log = make_logger(__name__)

from ..utils import stralign


class ColumnBase():
    header = {'left': '', 'right': ''}
    width = None
    align = 'right'
    interfaces = ('cli', 'tui')
    may_have_wide_chars = False

    def __init__(self, data=None):
        self.data = data if data is not None else {}
        super().__init__()

    def get_value(self):
        raise NotImplementedError()

    def get_raw(self):
        return self.get_value()

    def get_string(self):
        """Return `get_value` as spaced and aligned string

        If the `width` attribute is not set to None, expand or shrink and
        align the returned string (`align` attribute must be 'left' or
        'right').
        """
        width = self.width
        align = self.align
        string = str(self.get_value())
        if not isinstance(width, int):
            return string
        else:
            # Crop string or fill it with spaces and align to left/right
            if self.may_have_wide_chars:
                return stralign(string, width, align)

            if len(string) > width:
                string = string[:width]

            if align == 'right':
                return string.rjust(width)
            elif align == 'left':
                return string.ljust(width)
            else:
                raise TypeError("'align' attribute must be 'left' or 'right', not {!r}".format(align))

    def __repr__(self):
        if self.data:
            return '<{} {}>'.format(type(self).__name__, self.get_value())
        else:
            return '<{} <UNINITIALIZED>>'.format(type(self).__name__)
