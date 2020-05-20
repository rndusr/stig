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

from types import SimpleNamespace

from ._converter import DataSizeConverter

convert = SimpleNamespace(bandwidth=DataSizeConverter(),
                          size=DataSizeConverter())


def cached_property(fget=None, *, after_creation=None):
    """
    Property that replaces itself with the requested value when accessed

    `after_creation` is called with the instance of the property when the
    property is accessed for the first time.
    """
    # https://stackoverflow.com/a/6849299
    class _cached_property():
        def __init__(self, fget):
            self._fget = fget
            self._property_name = fget.__name__
            self._after_creation = after_creation
            self._cache = {}

        def __get__(self, obj, cls):
            value = self._fget(obj)
            setattr(obj, self._property_name, value)
            if self._after_creation is not None:
                self._after_creation(obj)
            return value

    if fget is None:
        return _cached_property
    else:
        return _cached_property(fget)
