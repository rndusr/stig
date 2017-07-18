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
from types import MethodType
import re


class Number(float):
    """float with a string representation that can be parsed"""

    _PREFIXES_BINARY = (('Ti', 1024**4), ('Gi', 1024**3), ('Mi', 1024**2), ('Ki', 1024))
    _PREFIXES_METRIC = (('T', 1000**4), ('G', 1000**3), ('M', 1000**2), ('k', 1000))
    _PREFIXES = tuple((prefix.lower(), size)
                          for prefix,size in chain.from_iterable(zip(_PREFIXES_BINARY,
                                                                     _PREFIXES_METRIC)))
    _PREFIXES_DCT = dict(_PREFIXES)
    _REGEX = re.compile('^([-+]?(?:\d+\.\d+|\d+|\.\d+)) ?(' +\
                        '|'.join(p[0] for p in _PREFIXES) + \
                        '|)(.*?)$',
                        flags=re.IGNORECASE)

    PREFIXES = tuple(prefix for prefix,size in chain.from_iterable(zip(_PREFIXES_BINARY,
                                                                       _PREFIXES_METRIC)))

    @classmethod
    def from_string(cls, string, *, prefix='metric', unit=None, str_with_unit=True):
        match = cls._REGEX.match(str(string))
        if match is None:
            raise ValueError('Not a number: {!r}'.format(string))
        else:
            num = float(match.group(1))
            unit = match.group(3) or unit
            prfx = match.group(2)
            if prfx:
                all_prfxs = cls._PREFIXES_DCT
                prfx_lower = prfx.lower()
                if prfx_lower in all_prfxs:
                    num *= all_prfxs[prfx_lower]

            prfx_len = len(prfx)
            if prfx_len == 2:
                prefix = 'binary'
            elif prfx_len == 1:
                prefix = 'metric'

            return cls(num, prefix, unit, str_with_unit)

    def __new__(cls, num, prefix='metric', unit=None, str_with_unit=True):
        if isinstance(num, cls):
            return cls(float(num), prefix=prefix or num.prefix, unit=unit or num.unit)
        elif isinstance(num, str):
            return cls.from_string(num, prefix=prefix, unit=unit)

        obj = super().__new__(cls, num)
        obj.unit = unit
        obj.prefix = prefix
        obj.str_with_unit = str_with_unit
        return obj

    def __str__(self):
        return self.__str()

    def __repr__(self):
        return '<{} {}, prefix={!r}, unit={!r}>'.format(type(self).__name__, float(self),
                                                        self._prefix, self._unit)

    @property
    def with_unit(self):
        s = self.without_unit
        if self.unit is not None:
            s += self.unit
        return s

    @property
    def without_unit(self):
        if self >= float('inf'):
            return pretty_float(self)

        for prefix,size in self._prefixes:
            if self >= size:
                return pretty_float(self/size) + prefix
        return pretty_float(self)

    @property
    def str_with_unit(self):
        return self._str_with_unit

    @str_with_unit.setter
    def str_with_unit(self, str_with_unit):
        if str_with_unit:
            self.__str = MethodType(lambda self: self.with_unit, self)
        else:
            self.__str = MethodType(lambda self: self.without_unit, self)
        self._str_with_unit = bool(str_with_unit)

    @property
    def unit(self): return self._unit
    @unit.setter
    def unit(self, unit): self._unit = str(unit) if unit is not None else None

    @property
    def prefix(self):
        return self._prefix
    @prefix.setter
    def prefix(self, prefix):
        if prefix == 'binary':
            self._prefixes = self._PREFIXES_BINARY
        elif prefix == 'metric':
            self._prefixes = self._PREFIXES_METRIC
        else:
            raise ValueError("prefix must be 'binary' or 'metric', not {!r}".format(prefix))
        self._prefix = prefix

    # Arithmetic operations return Number instances with unit, prefix, etc preserved
    def _get_kwargs(self):
        return {'unit': self.unit, 'prefix': self.prefix, 'str_with_unit': self._str_with_unit}

    def __add__(self, other):
        return type(self)(super().__add__(other), **self._get_kwargs())
    def __sub__(self, other):
        return type(self)(super().__sub__(other), **self._get_kwargs())
    def __mul__(self, other):
        return type(self)(super().__mul__(other), **self._get_kwargs())
    def __div__(self, other):
        return type(self)(super().__div__(other), **self._get_kwargs())
    def __truediv__(self, other):
        return type(self)(super().__truediv__(other), **self._get_kwargs())
    def __floordiv__(self, other):
        return type(self)(super().__floordiv__(other), **self._get_kwargs())
    def __mod__(self, other):
        return type(self)(super().__mod__(other), **self._get_kwargs())
    def __divmod__(self, other):
        return type(self)(super().__divmod__(other), **self._get_kwargs())
    def __pow__(self, other):
        return type(self)(super().__pow__(other), **self._get_kwargs())
    def __round__(self, *args, **kwargs):
        return type(self)(super().__round__(*args, **kwargs), **self._get_kwargs())
    def __floor__(self):
        return type(self)(super().__floor__(), **self._get_kwargs())
    def __ceil__(self):
        return type(self)(super().__ceil__(), **self._get_kwargs())


def pretty_float(n):
    """Format float with a reasonable amount of decimal places"""
    if n == float('inf'):
        return '∞'
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
