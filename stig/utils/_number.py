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


from itertools import chain
from types import MethodType
import re


def pretty_float(n):
    """Format float with a reasonable amount of decimal places"""
    if n >= float('inf'):
        return '∞'
    n_abs = abs(n)
    n_abs_r2 = round(n_abs, 2)
    if n_abs == 0:
        return '0'
    elif n_abs_r2 == int(n_abs):
        return '%.0f' % n
    elif n_abs_r2 < 10:
        return '%.2f' % n
    elif round(n_abs, 1) < 100:
        return '%.1f' % n
    else:
        return '%.0f' % n


class _NumberBase():
    _PREFIXES_BINARY = (('Ti', 1024**4), ('Gi', 1024**3), ('Mi', 1024**2), ('Ki', 1024))
    _PREFIXES_METRIC = (('T', 1000**4), ('G', 1000**3), ('M', 1000**2), ('k', 1000))
    _PREFIXES = tuple((prefix.lower(), size)
                      for prefix,size in chain.from_iterable(zip(_PREFIXES_BINARY,
                                                                 _PREFIXES_METRIC)))
    _PREFIXES_DCT = dict(_PREFIXES)

    _REGEX = re.compile('^([-+]?(?:\d+\.\d+|\d+|\.\d+)) ?(' +\
                        '|'.join(p[0] for p in _PREFIXES) + \
                        '|)(\S*?)$',
                        flags=re.IGNORECASE)

    # Public tuple of all supported unit prefixes
    UNIT_PREFIXES = tuple(prefix for prefix,size in chain.from_iterable(zip(_PREFIXES_BINARY,
                                                                            _PREFIXES_METRIC)))

    @classmethod
    def from_string(cls, string, *, prefix=None, unit=None, str_includes_unit=None):
        match = cls._REGEX.match(str(string))
        if match is None:
            raise ValueError('Not a number: %r' % string)
        else:
            # Convert to float first, because a) int('1.2') is not allowed and
            # b) so '1.2k' (which is a integer) is not parsed to 1000
            num = float(match.group(1))
            unit = match.group(3) or unit
            prfx = match.group(2)
            if prfx:
                all_prfxs = cls._PREFIXES_DCT
                prfx_lower = prfx.lower()
                # _REGEX matches, so we can be sure that prfx_lower is in all_prfxs
                num *= all_prfxs[prfx_lower]
            num = cls._numtype(num)

            prfx_len = len(prfx)
            if prfx_len == 2:
                prefix = 'binary'
            elif prfx_len == 1:
                prefix = 'metric'

            return cls(num, prefix=prefix, unit=unit, str_includes_unit=str_includes_unit)

    def __new__(cls, num, *, prefix=None, unit=None, str_includes_unit=None):
        if isinstance(num, _NumberBase):
            # Copy properties from existing Number instance unless they are
            # overridden by arguments.
            prefix = num.prefix if prefix is None else prefix
            unit = num.unit if unit is None else unit
            str_includes_unit = num.str_includes_unit if str_includes_unit is None else str_includes_unit
            # return cls(float(num), prefix=prefix, unit=unit, str_includes_unit=str_includes_unit)
            return cls(cls._numtype(num), prefix=prefix, unit=unit, str_includes_unit=str_includes_unit)

        # We can't specify defaults in the arguments because then we don't know
        # which arguments are passed and which are default.
        prefix = 'metric' if prefix is None else prefix
        str_includes_unit = True if str_includes_unit is None else str_includes_unit

        if isinstance(num, str):
            return cls.from_string(num, prefix=prefix, unit=unit, str_includes_unit=str_includes_unit)
        elif isinstance(num, (int, float)):
            obj = super().__new__(cls, num)
            obj.unit = unit
            obj.prefix = prefix
            obj.str_includes_unit = str_includes_unit
            return obj
        else:
            raise ValueError('Not a number: %r' % num)

    def __str__(self):
        return self.__str()

    @property
    def str_includes_unit(self):
        return self._str_includes_unit
    @str_includes_unit.setter
    def str_includes_unit(self, str_includes_unit):
        if str_includes_unit:
            self.__str = MethodType(lambda self: self.with_unit, self)
        else:
            self.__str = MethodType(lambda self: self.without_unit, self)
        self._str_includes_unit = bool(str_includes_unit)

    def __repr__(self):
        return '<{} {}, prefix={!r}, unit={!r}>'.format(type(self).__name__, self._numtype(self),
                                                        self._prefix, self._unit)

    @property
    def with_unit(self):
        s = self.without_unit
        if self.unit is not None:
            s += self.unit
        return s

    @property
    def without_unit(self):
        absolute = abs(self)
        if self == 0:
            # This should increase efficiency since 0 is a common value
            return '0'
        elif absolute >= float('inf'):
            return pretty_float(self)
        else:
            for prefix,size in self._prefixes:
                if absolute >= size:
                    return pretty_float(self/size) + prefix
            return pretty_float(self)

    @property
    def unit(self):
        return self._unit
    @unit.setter
    def unit(self, unit):
        self._unit = str(unit) if unit is not None else None

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

    def _do_math(self, method, *args, **kwargs):
        # Get the new value as int or float
        if self == float('inf'):
            # No need to do any calculations with infinity, especially because
            # of round() throwing an OverflowError because `int` has no infinity
            # value implemented.
            new_value = float('inf')
        else:
            new_value = getattr(self._numtype, method)(self, *args, **kwargs)

        if new_value is NotImplemented:
            # This may have happened because `self._numtype` is `int` and it got
            # a `float` to handle.  To make this work, we must flip `self` and
            # `other`, getting the method from `other` and passing it `self`:
            #
            #     int.__add__(<int>, <float>)  ->  float.__add__(<float>, <int>)
            #
            # If we get the parent method from the instance instead of its type,
            # we don't have to pass two values and it's a little bit faster.
            parent_method = getattr(args[0], method)
            new_value = parent_method(self, **kwargs)
            if new_value is NotImplemented:
                return NotImplemented

        # Determine the appropriate class (1.0 should return a NumberInt)
        if isinstance(new_value, int) or (new_value < float('inf') and
                                          isinstance(new_value, float) and
                                          int(new_value) == new_value):
            new_cls = NumberInt
        else:
            new_cls = NumberFloat

        # Copy all properties to new instance
        return new_cls(new_value, unit=self.unit, prefix=self.prefix,
                       str_includes_unit=self._str_includes_unit)

    def __add__(self, other):             return self._do_math('__add__', other)
    def __sub__(self, other):             return self._do_math('__sub__', other)
    def __mul__(self, other):             return self._do_math('__mul__', other)
    def __div__(self, other):             return self._do_math('__div__', other)
    def __truediv__(self, other):         return self._do_math('__truediv__', other)
    def __floordiv__(self, other):        return self._do_math('__floordiv__', other)
    def __mod__(self, other):             return self._do_math('__mod__', other)
    def __divmod__(self, other):          return self._do_math('__divmod__', other)
    def __pow__(self, other):             return self._do_math('__pow__', other)
    def __floor__(self):                  return self._do_math('__floor__')
    def __ceil__(self):                   return self._do_math('__ceil__')
    def __round__(self, *args, **kwargs): return self._do_math('__round__', *args, **kwargs)


class NumberFloat(_NumberBase, float):
    _numtype = float

class NumberInt(_NumberBase, int):
    _numtype = int
