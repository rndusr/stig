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

from ..logging import make_logger
log = make_logger(__name__)

from .usertypes import (Float, Int)


class DataSizeConverter():
    """
    Convert bits to bytes or vice versa, ensuring a Int instance with a unit
    prefix that is common throughout the application
    """
    __slots__ = ('_unit', '_prefix')

    _short = {'bit': 'b', 'byte': 'B'}

    def __init__(self):
        self.prefix = 'metric'
        self.unit = 'B'

    def __call__(self, num, unit=None):
        """
        Make Int from `num`

        The returned Int is converted to bits or bytes depending on what the
        `unit` property is set to.

        If no unit is given (by passing a Int/Float object with a specified
        `unit` property or by passing the `unit` argument), it is assumed to be
        what the `unit` property of this object is set to.
        """
        if not isinstance(num, (Int, Float)):
            # Parse unit; fall back to given or our own unit
            num = Int(num, unit=unit or self._unit, prefix=self._prefix)

        unit_given = self._short.get(num.unit, num.unit) or self._unit
        if unit_given not in ('b', 'B'):
            raise ValueError("Unit must be 'b' (bit) or 'B' (byte), not %r" % unit_given)
        else:
            return Int(num, unit=unit_given, convert_to=self._unit, prefix=self._prefix)

    @property
    def unit(self):
        """'b' (bits) or 'B' (bytes)"""
        return self._unit

    @unit.setter
    def unit(self, unit):
        if unit not in ('bit', 'byte', 'b', 'B'):
            raise ValueError("Unit must be 'bit or 'byte'")
        else:
            self._unit = self._short.get(unit, unit)

    @property
    def prefix(self):
        """'binary' or 'metric'"""
        return self._prefix

    @prefix.setter
    def prefix(self, prefix):
        if prefix not in ('binary', 'metric'):
            raise ValueError("Prefix must be 'binary' or 'metric'")
        else:
            self._prefix = prefix
