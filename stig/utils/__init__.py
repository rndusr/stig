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

import unicodedata
from itertools import chain
import re


class Number(float):
    """float with a string representation that can be parsed"""

    _PREFIXES_BINARY = (('Ti', 1024**4), ('Gi', 1024**3), ('Mi', 1024**2), ('Ki', 1024))
    _PREFIXES_METRIC = (('T', 1000**4), ('G', 1000**3), ('M', 1000**2), ('k', 1000))
    _ALL_PREFIXES = tuple((prefix.lower(), size)
                          for prefix,size in chain.from_iterable(zip(_PREFIXES_BINARY,
                                                                     _PREFIXES_METRIC)))
    _ALL_PREFIXES_DCT = dict(_ALL_PREFIXES)
    _REGEX = re.compile('^([-+]?(?:\d+\.\d+|\d+|\.\d+)) ?(' +\
                        '|'.join(p[0] for p in _ALL_PREFIXES) + \
                        '|)(.*?)$',
                        flags=re.IGNORECASE)

    @classmethod
    def from_string(cls, string, prefix='metric', unit=None):
        match = cls._REGEX.match(string)
        if match is None:
            raise ValueError('Not a number: {!r}'.format(string))
        else:
            num = float(match.group(1))
            unit = match.group(3) or unit
            prfx = match.group(2)
            if prfx:
                all_prfxs = cls._ALL_PREFIXES_DCT
                prfx_lower = prfx.lower()
                if prfx_lower in all_prfxs:
                    num *= all_prfxs[prfx_lower]

            prfx_len = len(prfx)
            if prfx_len == 2:
                prefix = 'binary'
            elif prfx_len == 1:
                prefix = 'metric'

            return cls(num, prefix, unit)

    def __new__(cls, num, prefix='metric', unit=None):
        if isinstance(num, cls):
            return cls(float(num), prefix or num.prefix, unit or num.unit)

        obj = super().__new__(cls, num)
        if prefix == 'binary':
            obj._prefixes = cls._PREFIXES_BINARY
        elif prefix == 'metric':
            obj._prefixes = cls._PREFIXES_METRIC
        else:
            raise ValueError("prefix must be 'binary' or 'metric', not {!r}".format(prefix))
        obj.unit = unit
        obj.prefix = prefix
        return obj

    @property
    def with_unit(self):
        s = self.without_unit
        if self.unit is not None:
            s += self.unit
        return s

    @property
    def without_unit(self):
        for prefix,size in self._prefixes:
            if self >= size:
                return pretty_float(self/size) + prefix
        return pretty_float(self)

    def __str__(self):
        return self.without_unit

    def __repr__(self):
        return '<{} {}, prefix={!r}, unit={!r}>'.format(type(self).__name__, float(self),
                                                        self.prefix, self.unit)

    # Arithmetic operations return Number instances with unit and prefix preserved
    def __add__(self, other):
        return type(self)(super().__add__(other), unit=self.unit, prefix=self.prefix)
    def __sub__(self, other):
        return type(self)(super().__sub__(other), unit=self.unit, prefix=self.prefix)
    def __mul__(self, other):
        return type(self)(super().__mul__(other), unit=self.unit, prefix=self.prefix)
    def __div__(self, other):
        return type(self)(super().__div__(other), unit=self.unit, prefix=self.prefix)
    def __truediv__(self, other):
        return type(self)(super().__truediv__(other), unit=self.unit, prefix=self.prefix)
    def __floordiv__(self, other):
        return type(self)(super().__floordiv__(other), unit=self.unit, prefix=self.prefix)
    def __mod__(self, other):
        return type(self)(super().__mod__(other), unit=self.unit, prefix=self.prefix)
    def __divmod__(self, other):
        return type(self)(super().__divmod__(other), unit=self.unit, prefix=self.prefix)
    def __pow__(self, other):
        return type(self)(super().__pow__(other), unit=self.unit, prefix=self.prefix)


def pretty_float(n):
    """Format float with a reasonable amount of decimal places"""
    n_abs = round(abs(n), 2)
    n_abs_int = int(n_abs)
    if n_abs == 0:
        return '0'
    elif n_abs == n_abs_int:
        return '%.0f' % n
    elif n_abs < 10:
        return '%.2f' % n
    elif n_abs < 100:
        return '%.1f' % n
    else:
        return '%.0f' % n


def striplines(lines):
    """Remove empty strings from start and end of `lines` using `pop`"""
    lines = list(lines)
    while lines and lines[0] == '':
        lines.pop(0)
    while lines and lines[-1] == '':
        lines.pop(-1)
    yield from lines


def strwidth(string):
    """Return displayed width of `string`, considering wide characters"""
    return len(string) + sum(1 for char in string
                             if unicodedata.east_asian_width(char) in 'FW')


def strcrop(string, width, tail=None):
    """Return `string` cropped to `width`, considering wide characters

    If `tail` is not None, it must be a string that is appended to the cropped
    string.
    """
    def widechar_indexes(s):
        for i,c in enumerate(s):
            if unicodedata.east_asian_width(c) in 'FW':
                yield i

    if strwidth(string) <= width:
        return string  # string is already short enough

    if tail is not None:
        width -= strwidth(tail)  # Account for tail in final width

    indexes = list(widechar_indexes(string)) + [len(string)]
    if not indexes:
        return string[:width]  # No wide chars, regular cropping is ok

    parts = []
    start = 0
    end = 0
    currwidth = strwidth(''.join(parts))

    while indexes and currwidth < width and end < len(string):
        end = indexes.pop(0)
        if end > 0:
            parts.append(string[start:end])
            currwidth = strwidth(''.join(parts))
            start = end

    if currwidth > width:
        excess = currwidth - width
        parts[-1] = parts[-1][:-excess]

    if tail is not None:
        parts.append(tail)

    return ''.join(parts)


def stralign(string, width, side='left'):
    """Return `string` aligned to `side`, considering wide characters

    The returned string is filled up with spaces to take `width` single-spaced
    characters and cropped with `strcrop` if necessary.
    """
    fill = width - strwidth(string)
    if fill < 0:
        string = strcrop(string, width)

    fill = width - strwidth(string)
    if fill > 0:
        if side == 'left':
            string = string + ' '*fill
        elif side == 'right':
            string = ' '*fill + string
        else:
            raise TypeError("side argument must be 'left' or 'right', not {!r}".format(side))
    return string
