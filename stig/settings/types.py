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

import os
from collections import abc
from blinker import Signal
import inspect

from ..utils import (NumberFloat, NumberInt)

UNSPECIFIED = '<unspecified>'


class ValueBase():
    """Base class for *Value classes"""

    type = None             # Something like int, str or tuple
    typename = 'anything'   # User-readable explanation

    def __init__(self, name, *, default=None, description=None):
        self._name = str(name)
        self._description = str(description) or 'No description available'
        self._on_change = Signal()
        self._default = self._value = self._prev_value = None
        if default is not None:
            initial_value = self.convert(default)
            self.validate(initial_value)
            self._value = initial_value
            self._default = self._value
        log.debug('Initialized ValueBase: %s=%r', self._name, self._value)

    @property
    def name(self): return self._name
    @name.setter
    def name(self, name): self._name = str(name)

    @property
    def description(self): return self._description
    @description.setter
    def description(self, description): self._description = str(description)

    @property
    def value(self):
        """Convenience property for `get` method"""
        return self.get()
    @value.setter
    def value(self, value): self.set(value)

    @property
    def default(self):
        """Convenience property for `get_default` method"""
        return self.get_default()
    @default.setter
    def default(self, default): self.set_default(default)

    def get(self):
        """Return current value"""
        return self._value

    def set(self, value):
        """Set current value

        When setting this property, callbacks connected to `on_change` get the
        current value (after validation) every time it is changed.  If one of
        the callbacks raises ValueError, the change is reverted and ValueError
        is raised.
        """
        # convert() and validate() may raise ValueError
        new_value = self.convert(value)
        self.validate(new_value)

        # Set new value
        prev_value = self._value
        self._value = new_value

        # Callbacks can revert the change by raising ValueError
        try:
            self._on_change.send(self)
        except ValueError:
            self._value = prev_value
            raise
        else:
            self._prev_value = prev_value

    def get_default(self):
        """Return default value or `None` if no default is specified"""
        return self._default

    def set_default(self, default):
        """Change default value

        Raise ValueError if `default` doesn't pass through `convert` and
        `validate` methods.
        """
        try:
            new_default = self.convert(default)
            self.validate(new_default)
        except ValueError as e:
            raise ValueError('{} = {}: {}'.format(self.name, self.string(default), e))
        else:
            self._default = new_default

    def prev_value(self):
        return self._prev_value

    def reset(self):
        """Reset current value back to default"""
        self.value = self.default

    def validate(self, value):
        """Raise ValueError if `value` is not valid

        The default implementation checks if `value` is of the type specified in
        the class attribute `type`.  If `type` is None (the default), all values
        valid.

        Additionally, subclasses may check for things like max/min length/number
        (see `StringValue` and `NumberValue` for examples).
        """
        if self.type is not None and not isinstance(value, self.type):
            raise ValueError('Not a {}'.format(self.typename))

    def convert(self, value, *args, **kwargs):
        """Try to convert value to correct type before validation (e.g. str->int)

        Raise ValueError if impossible
        """
        if self.type is None or isinstance(value, self.type):
            return value
        try:
            return self.type(value, *args, **kwargs)
        except Exception:
            raise ValueError('Not a {}'.format(self.typename))

    def string(self, value=None, default=False):
        """Return prettily stringified value

        value: The value to stringify or `None` to use `value` property
        default: Whether to stringify current or default value (setting this to
                 True ignores the value argument)

        If possible, use `convert` to parse `value` before stringifying it.

        If `value` is invalid, `str(value)` or something similar should be
        returned so we can provide pretty error messages.  This method must not
        raise any exceptions.
        """
        if default:
            value = self.default
        elif value is not None:
            try:
                value = self.convert(value)
            except ValueError as e:
                value = value
        else:
            value = self.value

        # Display `None` as something more user-readable
        text = UNSPECIFIED if value is None else str(value)

        if not text or (text[0] == ' ' or text[-1] == ' '):
            return repr(text)
        else:
            return text

    def __str__(self):
        return self.string()

    def __repr__(self):
        v = self.value
        return '%s=%s' % (self.name, UNSPECIFIED if v is None else repr(v))

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.value == other.value
        else:
            return self.value == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        if isinstance(other, type(self)):
            return self.value > other.value
        try:
            return self.value > other
        except TypeError:
            return NotImplemented

    def __lt__(self, other):
        if isinstance(other, type(self)):
            return self.value < other.value
        try:
            return self.value < other
        except TypeError:
            return NotImplemented

    def __ge__(self, other):
        if isinstance(other, type(self)):
            return self.value >= other.value
        try:
            return self.value >= other
        except TypeError:
            return NotImplemented

    def __le__(self, other):
        if isinstance(other, type(self)):
            return self.value <= other.value
        try:
            return self.value <= other
        except TypeError:
            return NotImplemented

    def on_change(self, callback, autoremove=True):
        """Pass this object to `callback` every time its value changes

        `callback` may raise ValueError to revert the change (see `set`).

        If `autoremove` is True, stop calling callback once it is garbage
        collected.
        """
        self._on_change.connect(callback, weak=autoremove)


class StringValue(ValueBase):
    """String value

    Specify `minlen` and/or `maxlen` to limit the length of the string.
    """
    type = str

    @property
    def typename(self):
        text = 'string'
        if ((self.minlen == 1 or self.minlen == None) and
            (self.maxlen == 1 or self.maxlen == None)):
            chrstr = 'character'
        else:
            chrstr = 'characters'
        if self.minlen is not None and self.maxlen is not None:
            if self.minlen == self.maxlen:
                text += ' of {} {}'.format(self.minlen, chrstr)
            else:
                text += ' of {} to {} {}'.format(self.minlen, self.maxlen, chrstr)
        elif self.minlen is not None:
            text += ' of at least {} {}'.format(self.minlen, chrstr)
        elif self.maxlen is not None:
            text += ' of at most {} {}'.format(self.maxlen, chrstr)
        return text

    def __init__(self, *args, minlen=None, maxlen=None, **kwargs):
        self._check_minlen_maxlen(minlen, maxlen)
        self._minlen = minlen
        self._maxlen = maxlen
        ValueBase.__init__(self, *args, **kwargs)

    @staticmethod
    def _check_minlen_maxlen(minlen, maxlen):
        if minlen is not None and maxlen is not None:
            if minlen > maxlen:
                raise ValueError('minlen must be smaller than or equal to maxlen: minlen=%r, maxlen=%r' % (minlen, maxlen))
        if minlen is not None and minlen <= 0:
            raise ValueError('minlen must be > 0 or None')
        if maxlen is not None and maxlen <= 0:
            raise ValueError('maxlen must be > 0 or None')

    def validate(self, value):
        string = self.convert(value)
        if self.maxlen is not None and len(string) > self.maxlen:
            raise ValueError('Too long (maximum length is {})'.format(self.maxlen))
        if self.minlen is not None and len(string) < self.minlen:
            raise ValueError('Too short (minimum length is {})'.format(self.minlen))

    @property
    def minlen(self):
        return self._minlen

    @minlen.setter
    def minlen(self, minlen):
        self._check_minlen_maxlen(minlen, self.maxlen)
        self._minlen = minlen
        if minlen is not None:
            for name in ('_default', '_value'):
                value = getattr(self, name)
                if value is not None and len(value) < minlen:
                    setattr(self, name, value.ljust(minlen))

    @property
    def maxlen(self):
        return self._maxlen

    @maxlen.setter
    def maxlen(self, maxlen):
        self._check_minlen_maxlen(self.minlen, maxlen)
        self._maxlen = maxlen
        if maxlen is not None:
            for name in ('_default', '_value'):
                value = getattr(self, name)
                if value is not None and len(value) > maxlen:
                    setattr(self, name, value[:maxlen])


class PathValue(StringValue):
    """File system path

    If `mustexist` evaluates to True, the path must exist on the local file
    system.
    """
    typename = 'path'

    def __init__(self, *args, mustexist=False, **kwargs):
        self._mustexist = mustexist
        StringValue.__init__(self, *args, **kwargs)

    def validate(self, value):
        path = self.convert(value)
        if self.mustexist and not os.path.exists(path):
            raise ValueError('No such file or directory')

    def convert(self, value):
        path = StringValue.convert(self, value)
        return os.path.expanduser(os.path.normpath(path))

    def string(self, *args, **kwargs):
        """Replace user home directory with '~'"""
        path = StringValue.string(self, *args, **kwargs)
        if path.startswith(os.environ['HOME']):
            path = '~' + path[len(os.environ['HOME']):]
        return path

    @property
    def mustexist(self):
        """Whether the path must exist on the local file system."""
        return self._mustexist

    @mustexist.setter
    def mustexist(self, mustexist):
        self._mustexist = bool(mustexist)


class NumberValue(ValueBase):
    """Float or integer value

    Specify `min` and/or `max` to limit the range of valid numbers.
    """
    type = NumberFloat
    _numbertype = 'rational'
    valuesyntax = '[+=|-=]<NUMBER>[%s]' % '|'.join(NumberFloat.UNIT_PREFIXES)

    @property
    def typename(self):
        text = '{} number'.format(self._numbertype)
        if self.min is not None and self.max is not None:
            text += ' ({} - {})'.format(self.min, self.max)
        elif self.min is not None:
            text += ' (>= {})'.format(self.min)
        elif self.max is not None:
            text += ' (<= {})'.format(self.max)
        return text

    def __init__(self, *args, min=None, max=None, prefix='metric', unit=None, **kwargs):
        self._check_min_max(min, max)
        self._min = min
        self._max = max
        ValueBase.__init__(self, *args, **kwargs)
        self.prefix = prefix
        self.unit = unit

    @staticmethod
    def _check_min_max(min, max):
        if min is not None and max is not None:
            if min > max:
                raise ValueError('minimum must be smaller than or equal to maximum: min=%r, max=%r' % (min, max))

    def validate(self, value):
        num = self.convert(value)
        # bools are integers but not invalid in this case
        if isinstance(value, bool):
            raise ValueError('Not a %s' % self.typename)
        elif self.min is not None and num < self.min:
            raise ValueError('Too small (minimum is {})'.format(self.min))
        elif self.max is not None and num > self.max:
            raise ValueError('Too large (maximum is {})'.format(self.max))

    def convert(self, value):
        # True and False are technically integers
        if isinstance(value, bool):
            raise ValueError('Not a %s' % self.typename)

        # Allow adjusting value relative to current value
        elif isinstance(value, str) and len(value) >= 3:
            current_value = 0 if self.value is None else self.value
            value_str = value
            if value[0:2] == '+=':
                value = current_value + self.type(value[2:].strip())
            elif value[0:2] == '-=':
                value = current_value - self.type(value[2:].strip())

        if not isinstance(value, self.type):
            try:
                value = self.type(value, prefix=self.prefix, unit=self.unit)
            except (ValueError, TypeError) as e:
                raise ValueError('Not a %s' % self.typename)

        if hasattr(self, '_set_unit_when_possible'):
            value.unit = self._set_unit_when_possible
            delattr(self, '_set_unit_when_possible')
        if hasattr(self, '_set_prefix_when_possible'):
            value.prefix = self._set_prefix_when_possible
            delattr(self, '_set_prefix_when_possible')

        return value

    @property
    def min(self):
        """The smallest valid number"""
        return self._min

    @min.setter
    def min(self, min):
        self._check_min_max(min, self.max)
        self._min = min
        if min is not None:
            default = self.default
            if default is not None and default < min:
                self.default = self.type(min, prefix=self.prefix, unit=self.unit)
            value = self.value
            if value is not None and value < min:
                self.value = self.type(min, prefix=self.prefix, unit=self.unit)

    @property
    def max(self):
        """The largest valid number"""
        return self._max

    @max.setter
    def max(self, max):
        self._check_min_max(self.min, max)
        self._max = max
        if max is not None:
            default = self.default
            if default is not None and default > max:
                self.default = self.type(max, prefix=self.prefix, unit=self.unit)
            value = self.value
            if value is not None and value > max:
                self.value = self.type(max, prefix=self.prefix, unit=self.unit)

    @property
    def unit(self):
        """Any string or `None` for no unit"""
        value = self.value
        if value is not None:
            return value.unit
        elif hasattr(self, '_set_unit_when_possible'):
            return self._set_unit_when_possible
    @unit.setter
    def unit(self, unit):
        value = self.value
        if value is not None:
            value.unit = unit
        else:
            self._set_unit_when_possible = unit

    @property
    def prefix(self):
        """Unit prefix; 'binary' or 'metric'"""
        value = self.value
        if value is not None:
            return value.prefix
        elif hasattr(self, '_set_prefix_when_possible'):
            return self._set_prefix_when_possible
        else:
            return 'metric'
    @prefix.setter
    def prefix(self, prefix):
        value = self.value
        if value is None and prefix is not None:
            self._set_prefix_when_possible = prefix
        else:
            value.prefix = prefix

    def string(self, value=None, default=False, with_unit=True):
        if default:
            num = self.default
        elif value is not None:
            try:
                num = self.convert(value)
            except ValueError:
                return str(value)
        else:
            num = self.value

        if num is None:
            return UNSPECIFIED
        else:
            return num.with_unit if with_unit is True else num.without_unit

    def __repr__(self):
        v = self.value
        return '%s=%s' % (self.name, UNSPECIFIED if v is None else str(v))


class IntegerValue(NumberValue):
    """NumberValue that rounds numbers off to an integer"""
    type = NumberInt
    _numbertype = 'integer'

    def convert(self, value):
        return round(NumberValue.convert(self, value))


TRUE = ('enabled', 'yes', 'on', 'true', '1')
FALSE = ('disabled', 'no', 'off', 'false', '0')
class BooleanValue(ValueBase):
    """Boolean value

    Supported strings are specified in the module variables `TRUE` and `FALSE`.
    Valid values are also the numbers 1/0 and `True`/`False`.  All other values
    are invalid.
    """
    type = bool
    typename = 'boolean'
    valuesyntax = '[%s]' % '|'.join('/'.join((t,f)) for t,f in zip(TRUE, FALSE))

    def validate(self, value):
        ValueBase.validate(self, self.convert(value))

    def convert(self, value):
        if isinstance(value, bool):
            return value
        elif isinstance(value, int):
            if value in (0, 1): return bool(value)
        elif isinstance(value, str):
            if value.lower() in FALSE:  return False
            elif value.lower() in TRUE: return True
        raise ValueError('Not a {}'.format(self.typename))

    def string(self, *args, **kwargs):
        """Return the first value specified in the module variables `TRUE` or `FALSE`"""
        v = ValueBase.string(self, *args, **kwargs)
        if v == 'True':    return TRUE[0]
        elif v == 'False': return FALSE[0]
        else:              return v


class _AliasCapabilities():
    _aliases = {}

    @property
    def aliases(self):
        return self._aliases

    @aliases.setter
    def aliases(self, aliases):
        self._aliases = aliases

    def resolve_alias(self, value):
        # Return `value` if it can't be used as a dict key
        try:
            hash(value)
        except Exception:
            return value
        else:
            # Return `value` if it's not in our alias dictionary, otherwise return
            # what is mapped to `value`.
            return self._aliases.get(value, value)


class OptionValue(_AliasCapabilities, ValueBase):
    """Single value that can only be one of a predefined set of values"""

    @property
    def typename(self):
        optvals = (str(o) for o in self.options)
        return 'option: ' + ', '.join(optvals)

    def __init__(self, *args, options=(), aliases={}, **kwargs):
        self._options = tuple(options)
        self.aliases = aliases
        ValueBase.__init__(self, *args, **kwargs)

    def validate(self, value):
        value = self.resolve_alias(value)
        value = self.convert(value)
        if value not in self.options:
            optvals = (str(o) for o in self.options)
            raise ValueError('Not one of: {}'.format(', '.join(optvals)))

    def convert(self, value):
        return ValueBase.convert(self, self.resolve_alias(value))

    @property
    def options(self):
        """Iterable of all valid values"""
        return self._options

    @options.setter
    def options(self, options):
        if not isinstance(options, abc.Iterable):
            raise ValueError('Not an iterable: %r', options)
        else:
            self._options = tuple(options)
            for name in ('_default', '_value'):
                if getattr(self, name) not in self.options:
                    setattr(self, name, self.options[0])


class ListValue(_AliasCapabilities, ValueBase):
    """A sequence of values

    Set `options` to any iterable to limit the items allowed in the list.
    """
    type = list
    typename = 'list'

    def __init__(self, *args, options=None, aliases={}, **kwargs):
        self._options = options
        self.aliases = aliases
        ValueBase.__init__(self, *args, **kwargs)

    def validate(self, value):
        lst = self.convert(value)
        ValueBase.validate(self, lst)

        if self.options is not None:
            # Only items in self.options are allowed
            invalid_items = []
            for item in lst:
                if item not in self.options:
                    invalid_items.append(item)

            if invalid_items:
                raise ValueError('Invalid option{}: {}'.format(
                    's' if len(invalid_items) != 1 else '',
                    self.string(invalid_items)))

    def convert(self, value):
        if isinstance(value, str):
            lst = self.type(value.strip() for value in value.split(','))
        elif isinstance(value, abc.Iterable):
            lst = self.type(value)
        else:
            raise ValueError('Not a {}'.format(self.typename))

        # Resolve aliases
        return [self.resolve_alias(item) for item in lst]

    def string(self, value=None, default=False):
        if default:
            lst = self.default
        elif value is not None:
            try:
                lst = self.convert(value)
            except ValueError:
                lst = (str(value),)
        else:
            lst = self.value
        return ', '.join(str(item) for item in lst)

    @property
    def options(self):
        """tuple of allowed values or None to allow all values

        Calling `set` with a sequence that contains items not in `options`
        will raise a ValueError.
        """
        return self._options

    @options.setter
    def options(self, options):
        if options is None:
            self._options = None
        elif isinstance(options, abc.Iterable):
            self._options = tuple(options)
            # Purge new invalid items
            for name in ('_default', '_value'):
                lst = getattr(self, name)
                invalid_items = set(lst).difference(self.options)
                for item in invalid_items:
                    while item in lst:
                        lst.remove(item)
        else:
            raise TypeError('options must be sequence or None, not %s: %r' % (type(options).__name__, options))


class SetValue(ListValue):
    """ListValue with unique elements (order is preserved)"""
    type = list
    typename = 'set'

    def convert(self, value):
        lst = ListValue.convert(self, value)
        # Make list items unique while preserving order
        seen = set()
        return [x for x in lst if not (x in seen or seen.add(x))]


def signature_without_unbound_args(func):
    sig = inspect.signature(func)
    params = [param for param in sig.parameters.values()
              if param.kind not in (inspect.Parameter.VAR_POSITIONAL,
                                    inspect.Parameter.VAR_KEYWORD)]
    return inspect.Signature(params)

def MultiValue(*clses):
    # Create class name from names of subclasses
    clsnames = []
    for cls in clses:
        if not issubclass(cls, ValueBase):
            raise RuntimeError('Not a ValueBase: %r', cls)
        clsnames.append(cls.__name__[:-5])  # Remove 'Value' from class name
    clsname = 'Or'.join(clsnames) + 'Value'

    clsattrs = {'_subclses': clses}

    def __init__(self, name, *, default=None, description=None, **kwargs):
        # Create instance of each subclass
        instances_list = []
        instances_dict = {}
        used_args = set()
        for cls in self._subclses:
            init_args = {'name': '%s[%s]' % (name, cls.__name__)}
            cls_sig = signature_without_unbound_args(cls.__init__)
            for param in cls_sig.parameters:
                if param in kwargs:
                    init_args[param] = kwargs[param]
                    used_args.add(param)
            instance = cls(**init_args)
            instances_dict[cls] = instance
            instances_list.append(instance)

        # Any arguments not used by any subclass raise a TypeError
        unused_args = set(kwargs).difference(used_args)
        if len(unused_args) > 0:
            raise TypeError("TypeError: invalid keyword arguments: %s" %
                            ', '.join(repr(arg) for arg in sorted(unused_args)))

        # These attributes don't exist yet, so we must avoid calling __getattr__
        for attrname in ('_name', '_default', '_value', '_description', '_on_change'):
            object.__setattr__(self, attrname, None)
        object.__setattr__(self, '_instances_list', instances_list)
        object.__setattr__(self, '_instances_dict', instances_dict)
        object.__setattr__(self, '_current_instance', self._get_valid_instance(default))

        # Fill _name, _default, etc with actual values
        ValueBase.__init__(self, name, default=default, description=description)
        log.debug('Initialized of MultiValue %s: %r', clsname, self)
    clsattrs['__init__'] = __init__

    clsattrs['instances'] = property(fget=lambda self: self._instances_dict,
                                     fset=None, fdel=None,
                                     doc='Dictionary of values with their class as key')

    def _get_valid_instance(self, value):
        """Return first instance that accepts `value`"""
        instances = self._instances_list
        if value is None:
            return instances[0]
        else:
            exceptions = []
            for inst in instances:
                try:
                    inst.validate(value)
                except ValueError as e:
                    if inst.typename is not None:
                        exceptions.append(e)
                else:
                    return inst
            raise ValueError('; '.join(str(e) for e in exceptions))
    clsattrs['_get_valid_instance'] = _get_valid_instance

    def set_(self, value):
        self._current_instance = self._get_valid_instance(value)
        self._current_instance.set(value)

        # Call custom validate()/convert() of child classes, set our own
        # internal _value attribute and handle callbacks.
        ValueBase.set(self, self._current_instance.value)

        # convert() of a child class may have changed the type of the value
        # (e.g. if we are a BooleanOrIntegerValue, convert() could return False
        # for values < 0), so we must check again which instance is valid for
        # the new value.
        self._current_instance = self._get_valid_instance(ValueBase.get(self))
    clsattrs['set'] = set_

    def validate(self, value):
        self._get_valid_instance(value)
    clsattrs['validate'] = validate

    def convert(self, value):
        inst = self._get_valid_instance(value)
        return inst.convert(value)
    clsattrs['convert'] = convert

    def string(self, value=None, default=False):
        if default or value is not None:
            if default:
                value = self.default
            try:
                inst = self._get_valid_instance(value)
            except ValueError:
                return str(value)
            else:
                return inst.string(value)
        else:
            return self._current_instance.string(self.value)
    clsattrs['string'] = string

    def typename(self):
        return ' or '.join(inst.typename for inst in self._instances_list
                           if inst.typename is not None)
    clsattrs['typename'] = property(typename)

    def valuesyntax(self):
        parts = []
        for inst in self._instances_list:
            for attrname in ('valuesyntax', 'typename'):
                if hasattr(inst, attrname):
                    attr = getattr(inst, attrname)
                    if attr is not None:
                        parts.append(attr)
                        break
        return ' or '.join(parts)
    clsattrs['valuesyntax'] = property(valuesyntax)

    def __repr__(self):
        # Use class of current value and supply it with self instance.  This
        # uses the proper __repr__ method while keeping the correct name without
        # the '[<type>]' affix.
        return type(self._current_instance).__repr__(self)
    clsattrs['__repr__'] = __repr__

    def __getattr__(self, name):
        # Find custom attribute (e.g. 'minlen' or 'options') in instances
        for inst in self._instances_list:
            if hasattr(inst, name):
                attr = getattr(inst, name)
                return attr
        raise AttributeError('%r object has no attribute %r' % (type(self).__name__, name))
    clsattrs['__getattr__'] = __getattr__

    def __setattr__(self, name, value):
        # Look for attribute on self only (avoid __getattr__)
        try:
            attr = object.__getattribute__(self, name)
        except AttributeError:
            pass
        else:
            object.__setattr__(self, name, value)
            return

        # Look for special attributes on the other instances (e.g. OptionValue's
        # "options" or NumberValue's "min/max")
        for inst in self._instances_list:
            if hasattr(inst, name):
                setattr(inst, name, value)
                return

        raise AttributeError('%r object has no attribute %r' % (type(self).__name__, name))
    clsattrs['__setattr__'] = __setattr__

    cls = type(clsname, (ValueBase,), clsattrs)
    return cls


class Settings():
    """Make multiple *Value instances accessible as a dict with their name as key"""

    def __init__(self, *values):
        # _values and _values_dict hold the same instances; the list is to
        # preserve order and the dict is for fast access via __getitem__
        self._values = []
        self._values_dict = {}
        self._on_change = Signal()
        self.load(*values)

    def add(self, value):
        """Add `value` to collection"""
        self._values.append(value)
        self._values_dict[value.name] = value

    def load(self, *values):
        """Add multiple `values` to collection"""
        for v in values:
            self.add(v)

    @property
    def values(self):
        """Iterate over collected values"""
        yield from self._values

    @property
    def names(self):
        """Iterate over values' `name` properties"""
        yield from self._values_dict.keys()

    def on_change(self, callback, autoremove=True):
        """Run `callback` every time a value changes

        `callback` gets the value instances as the only argument.

        If `autoremove` is True, stop calling `callback` once it is garbage
        collected.
        """
        self._on_change.connect(callback, weak=autoremove)

    def __getitem__(self, name):
        return self._values_dict[name]

    def __setitem__(self, name, value):
        self._values_dict[name].value = value
        self._on_change.send(self._values_dict[name])

    def __contains__(self, name):
        return name in self._values_dict
