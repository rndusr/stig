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
        # preserve order and the dict is for access via __getitem__, etc.
        self._values = []
        self._values_dict = {}
        self._on_change = Signal()
        self.load(*values)

    def add(self, value):
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
    """Name:value pair with validation, default value and description"""

    def __init__(self, name, default, description='No description available'):
        """Create new value"""
        self.__name = name
        self.__value = self.__default = self.convert(default)
        self.__description = description
        self.__on_change = Signal()

    # Must be set by derived classes
    type = NotImplemented
    typename = '<NOT IMPLEMENTED>'

    @property
    def value(self): return self.__value

    @property
    def name(self): return self.__name

    @property
    def default(self): return self.__default

    @property
    def description(self): return self.__description

    def on_change(self, callback, autoremove=True):
        """Pass this object to `callback` every time its value changes

        `callback` may raise ValueError to revert the change (see `set`).

        If `autoremove` is True, stop calling callback once it is garbage
        collected.
        """
        self.__on_change.connect(callback, weak=autoremove)

    def set(self, value):
        """Change value if valid, reset to default if None

        Callbacks connected to `on_change` are passed this object every time a
        value is changed.  If a callback raises ValueError, the change is
        reverted and a ValueError is raised.
        """
        if value is None:
            value = self.__default
        try:
            new_value = self.convert(value)
            self.validate(new_value)
        except ValueError as e:
            raise ValueError('{} = {}: {}'.format(self.name, self.str(value), e))
        else:
            prev_value = self.__value
            self.__value = new_value
            # Callbacks can revert the change by raising ValueError
            try:
                self.__on_change.send(self)
            except ValueError as e:
                self.__value = prev_value
                raise ValueError('{} = {}: {}'.format(self.name, self.str(value), e))

    def get(self):
        """Return current value"""
        return self.value

    def validate(self, value):
        """Raise ValueError if value is not valid"""
        if not isinstance(value, self.type):
            raise ValueError('Not a {}'.format(self.typename))

    def convert(self, value):
        """Try to convert value to correct type before validation (e.g. str->int)

        Raise ValueError if impossible"""
        if isinstance(value, self.type):
            return value
        try:
            if isinstance(value, abc.Iterable):
                return self.type(''.join(value))
            else:
                return self.type(value)
        except Exception:
            raise ValueError('Not a {}'.format(self.typename))

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.value == other.value
        else:
            return self.value == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def str(self, value=None, default=False):
        """Return prettily stringified value

        value: None to return current value, or specific value
        default: Whether to return current or default value
        """
        if default:
            text = str(self.default)
        elif value is not None:
            text = str(value)
        else:
            text = str(self.value)

        if text and (text[0] == ' ' or text[-1] == ' '):
            return repr(text)
        else:
            return text

    def __str__(self):
        return self.str()

    def __repr__(self):
        return '{}={!r}'.format(self.name, self.value)


class StringValue(ValueBase):
    type = str
    @property
    def typename(self):
        text = 'string'
        if ((self._minlen == 1 or self._minlen == None) and
            (self._maxlen == 1 or self._maxlen == None)):
            chrstr = 'character'
        else:
            chrstr = 'characters'
        if self._minlen is not None and self._maxlen is not None:
            if self._minlen == self._maxlen:
                text += ' of {} {}'.format(self._minlen, chrstr)
            else:
                text += ' of {} to {} {}'.format(self._minlen, self._maxlen, chrstr)
        elif self._minlen is not None:
            text += ' of at least {} {}'.format(self._minlen, chrstr)
        elif self._maxlen is not None:
            text += ' of at most {} {}'.format(self._maxlen, chrstr)
        return text

    def __init__(self, *args, minlen=None, maxlen=None, **kwargs):
        if minlen is not None and maxlen is not None:
            assert minlen <= maxlen, 'minimum string length must be <= maximum'
        assert minlen is None or minlen >= 0, 'minimum string length must be >= 0'
        assert maxlen is None or maxlen >= 0, 'maximum string length must be >= 0'
        self._minlen = minlen
        self._maxlen = maxlen
        super().__init__(*args, **kwargs)

    def validate(self, string):
        if self._maxlen is not None and len(string) > self._maxlen:
            raise ValueError('Too long (maximum length is {})'.format(self._maxlen))
        if self._minlen is not None and len(string) < self._minlen:
            raise ValueError('Too short (minimum length is {})'.format(self._minlen))


class PathValue(StringValue):
    typename = 'path'

    def __init__(self, *args, mustexist=False, **kwargs):
        self.mustexist = mustexist
        super().__init__(*args, **kwargs)

    def convert(self, path):
        return os.path.expanduser(path)

    def validate(self, path):
        if self.mustexist and not os.path.exists(path):
            raise ValueError('No such file or directory')

    def str(self, value=None, default=False):
        """Tildify string"""
        path = super().str(value=value, default=default)
        if path.startswith(os.environ['HOME']):
            path = '~' + path[len(os.environ['HOME']):]
        return path


class NumberValue(ValueBase):
    type = float
    _numbertype = 'rational'
    valuesyntax = '[+=|-=]<NUMBER>'

    def __init__(self, *args, min=None, max=None, **kwargs):
        if min is not None and max is not None:
            assert min <= max, 'minimum must be smaller or equal than maximum'
        self._min = min
        self._max = max
        super().__init__(*args, **kwargs)

    @property
    def typename(self):
        text = '{} number'.format(self._numbertype)
        if self._min is not None and self._max is not None:
            text += ' {}-{}'.format(self._min, self._max)
        elif self._min is not None:
            text += ' >= {}'.format(self._min)
        elif self._max is not None:
            text += ' <= {}'.format(self._max)
        return text

    def convert(self, value):
        if isinstance(value, str) and len(value) >= 3:
            if value[0:2] == '+=':
                return self.value + super().convert(value[2:].strip())
            elif value[0:2] == '-=':
                return self.value - super().convert(value[2:].strip())
        return super().convert(value)

    def validate(self, value):
        super().validate(value)
        if self._min is not None and value < self._min:
            raise ValueError('Too small (minimum is {})'.format(self._min))
        elif self._max is not None and value > self._max:
            raise ValueError('Too big (maximum is {})'.format(self._max))

class IntegerValue(NumberValue):
    type = int
    _numbertype = 'integer'


TRUE = ('enable', 'yes', 'on', 'true', '1')
FALSE = ('disable', 'no', 'off', 'false', '0')
class BooleanValue(ValueBase):
    type = bool
    typename = 'boolean'
    valuesyntax = '[%s]' % '|'.join('/'.join((t,f)) for t,f in zip(TRUE, FALSE))

    def convert(self, value):
        if isinstance(value, bool):
            return value
        elif isinstance(value, int):
            if value in (0, 1):
                return bool(value)
        elif isinstance(value, str):
            if value.lower() in FALSE:
                return False
            elif value.lower() in TRUE:
                return True
        raise ValueError('Not a {}'.format(self.typename))

    def validate(self, value):
        self.convert(value)


class ListValue(ValueBase):
    type = list
    typename = 'list'

    def __init__(self, *args, options=None, **kwargs):
        self._options = options
        super().__init__(*args, **kwargs)

    @property
    def options(self):
        """tuple of allowed values or None to allow all values

        Calling `set` with a sequence that contains items not in `options`
        will raise a ValueError.
        """
        return self._options

    @options.setter
    def options(self, options):
        if isinstance(options, abc.Iterable):
            self._options = tuple(options)
        else:
            raise TypeError('options must be sequence, not {}: {!r}'
                            .format(type(options).__name__, options))

    def convert(self, value):
        if isinstance(value, str):
            return self.type(value.strip() for value in value.split(','))
        elif isinstance(value, abc.Iterable):
            return self.type(value)
        else:
            raise ValueError('Not a {}'.format(self.typename))

    def validate(self, lst):
        if self.options is not None:
            # Only items in self.options are allowed
            invalid_items = []
            for item in lst:
                if item not in self.options:
                    invalid_items.append(item)

            if invalid_items:
                raise ValueError('Invalid value{}: {}'.format(
                    's' if len(invalid_items) != 1 else '',
                    self.str(invalid_items)))

    def str(self, value=None, default=False):
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


class SetValue(ListValue):
    """ListValue with unique elements (order is preserved)"""
    type = list
    typename = 'set'

    def convert(self, value):
        lst = super().convert(value)
        # Make list items unique while preserving order
        seen = set()
        return [x for x in lst if not (x in seen or seen.add(x))]


class OptionValue(ValueBase):
    def __init__(self, *args, options=(), **kwargs):
        self._options = tuple(options)
        super().__init__(*args, **kwargs)

    @property
    def type(self):
        if self._options:
            return type(self._options[0])
        else:
            raise RuntimeError('Cannot guess value type: {!r}'.format(self))

    @property
    def typename(self):
        optvals = sorted(str(o) for o in self._options)
        return 'option: ' + ', '.join(optvals)

    def validate(self, value):
        if value not in self._options:
            optvals = sorted(str(o) for o in self._options)
            raise ValueError('Must be one of: {}'.format(', '.join(optvals)))

    def convert(self, value):
        self.validate(value)
        return value
