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


class ConstantBase():
    pass

def is_constant(obj):
    return isinstance(obj, ConstantBase)

_constants_cache = {}
def get_constant(string, repr_str=None, bases=(), value=None, attrs={}):
    """Get constant/singleton defined by `string`

    repr_str: Same as `string.upper()` if not specified
    bases: tuple of base classes; will be prepended to (ConstantBase, str)
    value: What the constant class is passed to upon creation
    attrs: Additional attributes of the constant class
    """
    if string not in _constants_cache:
        repr_str = (string if repr_str is None else repr_str).upper()

        def __str__(self): return self.string
        def __repr__(self): return '<Constant: {}>'.format(self.repr_str.upper())

        cls_attrs = {'__str__': __str__,
                     '__repr__': __repr__,
                     'string': string,
                     'repr_str': repr_str,
                     'value': value}
        cls_attrs.update(attrs)

        cls = type('Constant', bases + (ConstantBase,), cls_attrs)

        if value is not None:
            _constants_cache[string] = cls(value)
        else:
            _constants_cache[string] = cls()
    return _constants_cache[string]


DISCONNECTED = get_constant('disconnected')
UNLIMITED = get_constant('unlimited', bases=(float,), value='inf')
DISABLED = get_constant('disabled', attrs={'__bool__': lambda self: False})
ENABLED = get_constant('enabled', attrs={'__bool__': lambda self: True})
