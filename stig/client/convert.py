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

from . import NumberFloat


class _DataCountConverter():
    """Convert bits or bytes with metric or binary unit prefix to NumberFloat"""

    def __init__(self):
        self.prefix = 'metric'
        self.unit = 'byte'

    # Units (Long2Short and Short2Long)
    UNITS_L2S = {'bit': 'b', 'byte': 'B', 'b': 'b', 'B': 'B'}
    UNITS_S2L = {'b': 'bit', 'B': 'byte', 'bit': 'bit', 'byte': 'byte'}

    def from_string(self, string, *, unit=None):
        """Parse number of bytes/bits from `string`

        All arguments are passed to `NumberFloat.from_string`.  `unit` defaults
        to the `unit` property of this object.
        """
        num = NumberFloat.from_string(string, prefix=self._prefix,
                                      unit=unit or self.unit_short)
        num = self._ensure_unit_and_prefix(num)
        return num

    def __call__(self, num, unit=None):
        """Make NumberFloat from `num`

        The returned NumberFloat is converted to bits or bytes depending on what
        the `unit` property is set to.

        If no unit is given by passing a NumberFloat object with a specified
        `unit` property or by passing the `unit` argument, it is assumed to be
        in what the `unit` property of this object is set to.
        """
        if not isinstance(num, NumberFloat):
            unit = unit or self.unit_short
            num = NumberFloat(num, prefix=self._prefix, unit=unit)
        return self._ensure_unit_and_prefix(num)

    def _ensure_unit_and_prefix(self, num):
        unit_given = num.unit or self._unit
        if unit_given not in self.UNITS_L2S:
            raise ValueError("Unit must be 'b' (bit) or 'B' (byte), not {!r}".format(unit_given))
        else:
            unit_given = self.UNITS_L2S[unit_given]
            unit_wanted = self.unit_short
            if unit_given != unit_wanted:
                if unit_wanted == 'b':
                    num = NumberFloat(num*8, prefix=self._prefix, unit='b')
                elif unit_wanted == 'B':
                    num = NumberFloat(num/8, prefix=self._prefix, unit='B')
                else:
                    raise RuntimeError('This should never have happened!')
            else:
                # Make sure unit is in short form ('B', not 'byte')
                num.unit = unit_wanted

            num.prefix = self._prefix
            return num

    @property
    def unit(self):
        """'bit' or 'byte'"""
        return self._unit

    @unit.setter
    def unit(self, unit):
        if unit not in self.UNITS_S2L:
            raise ValueError("unit must be 'bit' or 'byte'")
        else:
            self._unit = self.UNITS_S2L[unit]

    @property
    def unit_short(self):
        return self.UNITS_L2S[self._unit]

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
