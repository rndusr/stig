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

from .utils import Float

class ConstantBase():
    pass

def is_constant(obj):
    return isinstance(obj, ConstantBase)

_constants_cache = {}
def get_constant(name, repr=None, bases=(), init_value=None, attrs={}):
    """Get constant/singleton defined by `name`

    repr: Same as `name.upper()` unless specified otherwise
    bases: tuple of base classes; will be prepended to (ConstantBase, str)
    init_value: Argument for the new constant class during creation
    attrs: Additional class attributes
    """
    if name not in _constants_cache:
        def __str__(self): return self.name
        def __repr__(self): return ('<Constant: %s>' % self.name.upper()) if self.repr is None else self.repr
        cls_attrs = {'__str__': __str__,
                     '__repr__': __repr__,
                     'name': name,
                     'repr': repr}
        cls_attrs.update(attrs)
        cls = type('Constant', bases + (ConstantBase,), cls_attrs)

        if init_value is not None:
            _constants_cache[name] = cls(init_value)
        else:
            _constants_cache[name] = cls()
    return _constants_cache[name]

DISCONNECTED = get_constant('disconnected', repr='<disconnected>')
UNLIMITED = get_constant('unlimited', bases=(Float,), init_value='inf')
