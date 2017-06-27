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


class Settings():
    """Dict of ordered Value objects"""

    def __init__(self, *values):
        # _values and _values_dict hold the same instances; the list is to
        # preserve order and the dict is for fast access via __getitem__
        self._values = []
        self._values_dict = {}
        self._on_change = Signal()
        self.load(*values)

    def add(self, value):
        assert isinstance(value, ValueBase), 'not a ValueBase: %r' % value
        self._values.append(value)
        self._values_dict[value.name] = value

    def load(self, *values):
        for v in values:
            self.add(v)

    @property
    def names(self):
        yield from self._values_dict.keys()

    @property
    def values(self):
        yield from self._values

    def on_change(self, callback, autoremove=True):
        """Run `callback` every time a value changes with the value

        If `autoremove` is True, stop calling callback once it is garbage
        collected.
        """
        self._on_change.connect(callback, weak=autoremove)

    def __getitem__(self, name):
        return self._values_dict[name]

    def __setitem__(self, name, value):
        self._values_dict[name].set(value)
        self._on_change.send(self._values_dict[name])

    def __contains__(self, name):
        return name in self._values_dict


class ValueBase():
    """Base class for *Value types"""

    _type = NotImplemented  # Something like int, str or tuple
    typename = 'anything'   # User-readable explanation

    def __init__(self, name, *, default=None, description=None):
        """Create new value"""
        self._name = name
        if default is None:
            self._value = self._default = None
        else:
            self._value = self._default = self.convert(default)
            self.validate(self._default)
        self._description = description or 'No description available'
        self._on_change = Signal()

    @property
    def value(self): return self._value
    @value.setter
    def value(self, value): self.set(value)

    @property
    def name(self): return self._name
    @name.setter
    def name(self, name): self._name = str(name)

    @property
    def default(self): return self._default
    @default.setter
    def default(self, default):
        self.validate(default)
        self._default = default

    @property
    def description(self): return self._description
    @description.setter
    def description(self, description): self._description = str(description)

    def set(self, value):
        """Change value if valid, reset to default if None

        Callbacks connected to `on_change` get this object every time a value is
        changed.  If one of the callbacks raises ValueError, the change is
        reverted and a ValueError is raised.
        """
        if value is None:
            value = self.default
        try:
            new_value = self.convert(value)
            self.validate(new_value)
        except ValueError as e:
            raise ValueError('{} = {}: {}'.format(self.name, self.string(value), e))
        else:
            prev_value = self.value
            self._value = new_value
            # Callbacks can revert the change by raising ValueError
            try:
                self._on_change.send(self)
            except ValueError as e:
                self._value = prev_value
                raise ValueError('{} = {}: {}'.format(self.name, self.string(value), e))

    def get(self):
        """Return current value

        This method is usefull for retrieving values asynchronously as there are
        no asynchronous properties.
        """
        return self.value

    def validate(self, value):
        """Raise ValueError if value is not valid

        The default implementation checks if `value` is of the type specified in
        the class attribute `_type`, if it is specified (i.e. not
        `NotImplemented`).

        Additionally, subclasses may check for things like max/min length/number
        (see `StringValue` and `NumberValue` for examples).
        """
        if self._type is not NotImplemented and not isinstance(value, self._type):
            raise ValueError('Not a {}'.format(self.typename))

    def convert(self, value):
        """Try to convert value to correct type before validation (e.g. str->int)

        Raise ValueError if impossible
        """
        if self._type is NotImplemented or isinstance(value, self._type):
            return value
        try:
            return self._type(value)
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
            text = str(self.default)
        elif value is not None:
            try:
                text = str(self.convert(value))
            except ValueError:
                text = str(value)
        else:
            text = str(self.value)

        if not text or (text[0] == ' ' or text[-1] == ' '):
            return repr(text)
        else:
            return text

    def __str__(self):
        return self.string()

    def __repr__(self):
        v = self.value
        return '%s=%s' % (self.name, '<unspecified>' if v is None else repr(v))

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.value == other.value
        else:
            return self.value == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def on_change(self, callback, autoremove=True):
        """Pass this object to `callback` every time its value changes

        `callback` may raise ValueError to revert the change (see `set`).

        If `autoremove` is True, stop calling callback once it is garbage
        collected.
        """
        self._on_change.connect(callback, weak=autoremove)


class StringValue(ValueBase):
    """Simple string

    Specify `minlen` and/or `maxlen` to limit the length of the string.
    """
    _type = str

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
        super().__init__(*args, **kwargs)

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
            for name in ('default', 'value'):
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
            for name in ('default', 'value'):
                value = getattr(self, name)
                if value is not None and len(value) > maxlen:
                    setattr(self, name, value[:maxlen])


class PathValue(StringValue):
    """File system path

    If `mustexist` evaluates to True, the path must exist on the local file system.
    """
    typename = 'path'

    def __init__(self, *args, mustexist=False, **kwargs):
        self._mustexist = mustexist
        super().__init__(*args, **kwargs)

    def validate(self, value):
        path = self.convert(value)
        if self.mustexist and not os.path.exists(path):
            raise ValueError('No such file or directory')

    def convert(self, value):
        return os.path.expanduser(super().convert(value))

    def string(self, value=None, default=False):
        """Replace user home directory with '~'"""
        path = super().string(value=value, default=default)
        if path.startswith(os.environ['HOME']):
            path = '~' + path[len(os.environ['HOME']):]
        return path

    @property
    def mustexist(self):
        return self._mustexist

    @mustexist.setter
    def mustexist(self, mustexist):
        self._mustexist = bool(mustexist)


class NumberValue(ValueBase):
    _type = float
    _numbertype = 'rational'
    valuesyntax = '[+=|-=]<NUMBER>'

    @property
    def typename(self):
        text = '{} number'.format(self._numbertype)
        if self.min is not None and self.max is not None:
            text += ' {} - {}'.format(self.min, self.max)
        elif self.min is not None:
            text += ' >= {}'.format(self.min)
        elif self.max is not None:
            text += ' <= {}'.format(self.max)
        return text

    def __init__(self, *args, min=None, max=None, **kwargs):
        self._check_min_max(min, max)
        self._min = min
        self._max = max
        super().__init__(*args, **kwargs)

    @staticmethod
    def _check_min_max(min, max):
        if min is not None and max is not None:
            if min > max:
                raise ValueError('minimum must be smaller than or equal to maximum: min=%r, max=%r' % (min, max))

    def validate(self, value):
        num = self.convert(value)
        if self.min is not None and num < self.min:
            raise ValueError('Too small (minimum is {})'.format(self.min))
        elif self.max is not None and num > self.max:
            raise ValueError('Too big (maximum is {})'.format(self.max))

    def convert(self, value):
        if isinstance(value, str) and len(value) >= 3:
            if value[0:2] == '+=':
                return self.value + super().convert(value[2:].strip())
            elif value[0:2] == '-=':
                return self.value - super().convert(value[2:].strip())
        return super().convert(value)

    @property
    def min(self):
        return self._min

    @min.setter
    def min(self, min):
        self._check_min_max(min, self.max)
        self._min = min
        if min is not None:
            if self.default is not None and self.default < min: self.default = min
            if self.value is not None and self.value < min: self.value = min

    @property
    def max(self):
        return self._max

    @max.setter
    def max(self, max):
        self._check_min_max(self.min, max)
        self._max = max
        if max is not None:
            if self.default is not None and self.default > max: self.default = max
            if self.value is not None and self.value > max: self.value = max


class IntegerValue(NumberValue):
    """NumberValue that automatically converts values to `int`"""
    _type = int
    _numbertype = 'integer'

    def convert(self, value):
        try:
            # Try to convert float or str to int
            return super().convert(value)
        except ValueError as error:
            # int cannot handle floats in string form (e.g. '10.3'), so we try
            # do convert them to float first.  If that also doesn't work, raise
            # *previous* exception.
            try:
                return super().convert(float(value))
            except (ValueError, TypeError) as _:
                raise error from None


TRUE = ('enabled', 'yes', 'on', 'true', '1')
FALSE = ('disabled', 'no', 'off', 'false', '0')
class BooleanValue(ValueBase):
    """Boolean value

    Supported strings are specified in the module-level variables `TRUE` and
    `FALSE`.  Valid values are also the numbers 1/0 and `True`/`False`.  All
    other values are invalid.
    """
    _type = bool
    typename = 'boolean'
    valuesyntax = '[%s]' % '|'.join('/'.join((t,f)) for t,f in zip(TRUE, FALSE))

    def validate(self, value):
        super().validate(self.convert(value))

    def convert(self, value):
        if isinstance(value, bool):
            return value
        elif isinstance(value, int):
            if value in (0, 1): return bool(value)
        elif isinstance(value, str):
            if value.lower() in FALSE:  return False
            elif value.lower() in TRUE: return True
        raise ValueError('Not a {}'.format(self.typename))

    def string(self, value=None, default=False):
        v = super().string(value, default)
        if v == 'True':    return TRUE[0]
        elif v == 'False': return FALSE[0]
        else:              return v


class OptionValue(ValueBase):
    """Single value that can only be one of a predefined set of values"""

    @property
    def _type(self):
        if self.options:
            return type(self.options[0])
        else:
            raise RuntimeError('Cannot guess value type: {!r}'.format(self))

    @property
    def typename(self):
        optvals = (str(o) for o in self.options)
        return 'option: ' + ', '.join(optvals)

    def __init__(self, *args, options=(), **kwargs):
        self._options = tuple(options)
        super().__init__(*args, **kwargs)

    def validate(self, value):
        value = self.convert(value)
        if value not in self.options:
            optvals = (str(o) for o in self.options)
            raise ValueError('Not one of: {}'.format(', '.join(optvals)))

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
            for name in ('default', 'value'):
                if getattr(self, name) not in self.options:
                    setattr(self, name, self.options[0])


class ListValue(ValueBase):
    """A sequence of values

    Set `options` to any iterable to limit the items allowed in the list.
    """
    _type = list
    typename = 'list'

    def __init__(self, *args, options=None, **kwargs):
        self._options = options
        super().__init__(*args, **kwargs)

    def validate(self, value):
        lst = self.convert(value)
        super().validate(lst)

        if self.options is not None:
            # Only items in self.options are allowed
            invalid_items = []
            for item in lst:
                if item not in self.options:
                    invalid_items.append(item)

            if invalid_items:
                raise ValueError('Invalid value{}: {}'.format(
                    's' if len(invalid_items) != 1 else '',
                    self.string(invalid_items)))

    def convert(self, value):
        if isinstance(value, str):
            return self._type(value.strip() for value in value.split(','))
        elif isinstance(value, abc.Iterable):
            return self._type(value)
        else:
            raise ValueError('Not a {}'.format(self.typename))

    def string(self, value=None, default=False):
        if default:
            lst = self.default
        elif value is not None:
            try:
                lst = self.convert(value)
            except ValueError:
                lst = str(value)
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
            for name in ('default', 'value'):
                lst = getattr(self, name)
                invalid_items = set(lst).difference(self.options)
                for item in invalid_items:
                    while item in lst:
                        lst.remove(item)
        else:
            raise TypeError('options must be sequence or None, not %s: %r' % (type(options).__name__, options))


class SetValue(ListValue):
    """ListValue with unique elements (order is preserved)"""
    _type = list
    typename = 'set'

    def convert(self, value):
        lst = super().convert(value)
        # Make list items unique while preserving order
        seen = set()
        return [x for x in lst if not (x in seen or seen.add(x))]
