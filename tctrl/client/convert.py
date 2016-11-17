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

    def __call__(self, num, unit=None):
        """Make Number from `num`

        `num` can be a number (int, float) or a string.  If it's a string, it
        can specify the unit ('b' for bits, 'B' for bytes), in which case the
        `unit` argument is ignored.

        If `unit` is not specified, it defaults to whatever the `unit`
        property is currently set to.
        """
        n = Number(num, prefix=self._prefix, unit=self.UNITS_L2S.get(unit, None))
        unit = n.unit
        if unit is None:
            unit = self.unit
            n.unit = self.UNITS_L2S[unit]
        elif unit not in self.UNITS_S2L:
            raise ValueError("Unit must be 'b' (bit) or 'B' (byte), not {!r}".format(unit))

        # Maybe we need to convert from bits to bytes or vice versa
        if self.UNITS_S2L[unit] == self._unit:
            return n
        else:
            return Number(self._convert(n), prefix=self._prefix,
                          unit=self.UNITS_L2S[self._unit])

    @property
    def unit(self):
        """'bit' or 'byte'"""
        return self._unit

    @unit.setter
    def unit(self, unit):
        if unit == 'bit':
            # How to get bits if we got bytes
            self._convert = lambda num: num*8
        elif unit == 'byte':
            # How to get bytes if we got bits
            self._convert = lambda num: num/8
        else:
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
