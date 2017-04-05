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

"""Converters for units"""

from ..logging import make_logger
log = make_logger(__name__)

from .tkeys import Number


class _DataCountConverter():
    """Convert bits or bytes with metric or binary unit prefix to Number"""

    def __init__(self):
        self.prefix = 'metric'
        self.unit = 'byte'

    # Units (Long2Short and Short2Long)
    UNITS_L2S = {'bit': 'b', 'byte': 'B', 'b': 'b', 'B': 'B'}
    UNITS_S2L = {'b': 'bit', 'B': 'byte', 'bit': 'bit', 'byte': 'byte'}

    def from_string(self, string):
        """Parse number of bytes/bits from `string`

        `string` must be of the format "NUMBER[UNIT PREFIX][UNIT]".  UNIT PREFIX
        is something like 'M' (mega) or 'Mi' (mebi). UNIT must be 'b' (bits) or
        'B' (bytes). If UNIT is not given, NUMBER is assumed to be in whatever
        the `unit` property is set to.

        Raises ValueError if unit is invalid.
        """
        num = Number.from_string(string)
        unit = num.unit
        if unit is None:
            # Default to value of `unit` property
            unit = self.unit
            num.unit = self.UNITS_L2S[unit]
        elif unit not in self.UNITS_S2L:
            raise ValueError("Unit must be 'b' (bit) or 'B' (byte), not {!r}".format(unit))

        return self._ensure_unit(num)

    def __call__(self, bytes):
        """Make Number from `bytes`

        The returned Number object is converted to bits if the `unit` property
        is set to 'bits'.

        If `bytes` is a Number object, it's `unit` property is evaluated to
        ensure the correct unit of the returned Number.
        """
        if isinstance(bytes, Number):
            return self._ensure_unit(bytes)
        elif self._unit == 'bit':
            return Number(bytes*8, prefix=self._prefix, unit='b')
        else:
            return Number(bytes, prefix=self._prefix, unit='B')

    def _ensure_unit(self, num):
        # Make sure the unit of the returned Number is what the `unit` property is set to
        unit_wanted = self._unit
        unit_given = self.UNITS_S2L[num.unit]
        if unit_wanted == unit_given:
            return num
        elif unit_given == 'bit':
            return Number(num/8, prefix=self._prefix, unit='B')
        elif unit_given == 'byte':
            return Number(num*8, prefix=self._prefix, unit='b')

    @property
    def unit(self):
        """'bit' or 'byte'"""
        return self._unit

    @unit.setter
    def unit(self, unit):
        if unit not in ('bit', 'byte'):
            raise ValueError("unit must be 'bit' or 'byte'")
        self._unit = unit

    @property
    def prefix(self):
        """'binary' or 'metric'"""
        return self._prefix

    @prefix.setter
    def prefix(self, prefix):
        if prefix not in ('binary', 'metric'):
            raise ValueError("unit must be 'binary' or 'metric'")
        else:
            self._prefix = prefix


bandwidth = _DataCountConverter()

class bandwidth_mixin():
    @property
    def bandwidth_unit(self):
        """Bandwidth numbers are displayed in 'bit' or 'byte'"""
        return bandwidth.unit

    @bandwidth_unit.setter
    def bandwidth_unit(self, unit):
        bandwidth.unit = unit

    @property
    def bandwidth_prefix(self):
        """Bandwidth numbers are displayed with 'binary' or 'metric' unit prefixes"""
        return bandwidth.prefix

    @bandwidth_prefix.setter
    def bandwidth_prefix(self, prefix):
        bandwidth.prefix = prefix


size = _DataCountConverter()

class size_mixin():
    @property
    def size_unit(self):
        """Size numbers are displayed in 'bit' or 'byte'"""
        return size.unit

    @size_unit.setter
    def size_unit(self, unit):
        size.unit = unit

    @property
    def size_prefix(self):
        """Size numbers are displayed with 'binary' or 'metric' unit prefixes"""
        return size.prefix

    @size_prefix.setter
    def size_prefix(self, prefix):
        size.prefix = prefix
