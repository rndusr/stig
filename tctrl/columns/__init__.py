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


class ColumnBase():
    header = {'left': '', 'right': ''}
    width = None
    align = 'right'

    def __init__(self, data=None):
        self.data = data
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
        text = str(self.get_value())
        if self.width is None:
            return text
        else:
            text = self._crop(text)

        if self.align == 'right':
            return text.rjust(self.width)
        elif self.align == 'left':
            return text.ljust(self.width)
        else:
            raise RuntimeError("Not 'left' or 'right': {!r}".format(self.align))

    def _crop(self, string):
        return string[:self.width]

    def __repr__(self):
        return '<{} {}>'.format(type(self).__name__, self.get_value())
