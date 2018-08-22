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

from functools import partial
from itertools import chain
import re
from collections.abc import Iterable
import os

_INFINITY = float('inf')


def _resolve_alias(value, aliases):
    # Only hashable values can be aliases
    try:
        hash(value)
    except Exception:
        return value
    else:
        # Return original value if it doesn't have an alias
        return aliases.get(value, value)


def _pretty_float(n):
    n_abs = abs(n)
    if n_abs >= _INFINITY:
        return ('-' if n < 0 else '') + '∞'
    elif n_abs == 0:
        return '0'
    n_abs_r2 = round(n_abs, 2)
    if n_abs_r2 == int(n_abs):
        return '%.0f' % n
    elif n_abs_r2 < 10:
        return ('%.2f' % n).rstrip('0').rstrip('.')
    elif round(n_abs, 1) < 100:
        return ('%.1f' % n).rstrip('0').rstrip('.')
    else:
        return '%.0f' % n


class _PartialConstructor(partial):
    def __init__(self, cls, **kwargs):
        repr = cls.__name__ + '('
        if kwargs:
            repr += ', '.join('%s=%r' % (k,v) for k,v in kwargs.items())
        self.__repr = repr + ')'
        self.__name__ = cls.__name__

    @property
    def syntax(self):
        return self.func._get_syntax(**self.keywords)

    @property
    def typename(self):
        return self.func.typename

    def __repr__(self):
        return self.__repr


class StringableMixin():
    @classmethod
    def partial(cls, **kwargs):
        return _PartialConstructor(cls, **kwargs)

    def __init__(self, *value, **kwargs):
        self._config = {**self.defaults, **kwargs}

    def copy(self, *value, **kwargs):
        new_kwargs = {**self._config, **kwargs}
        new_posargs = value if len(value) > 0 else self
        if not isinstance(new_posargs, Iterable):
            new_posargs = (new_posargs,)
        return type(self)(*new_posargs, **new_kwargs)

    @property
    def syntax(self):
        return self._get_syntax(**self._config)


# https://stackoverflow.com/a/5192374
class classproperty():
    def __init__(self, f):
        self.f = f

    def __get__(self, obj, owner):
        return self.f(owner)


def multitype(*constructors):
    class MultitypeMeta(type):
        def __new__(mcls, name, bases, clsattrs):
            cls = type.__new__(mcls, name, bases, clsattrs)
            cls.__name__ = 'Or'.join(subcls.__name__ for subcls in cls._subclses)
            mcls._subclses = (cls,) + cls._subclses
            return cls

        @classmethod
        def __instancecheck__(mcls, inst):
            for subtype in mcls._subclses:
                log.debug('Checking whether %r,%r is a %r', inst, type(inst), subtype)
                if type(inst) is subtype:
                    return True
            return False

        @classmethod
        def __subclasscheck__(mcls, cls):
            return cls in mcls._subclses[1:]


    class Multitype(StringableMixin, metaclass=MultitypeMeta):
        # Get constructors (e.g. Int.partial(...)) for making new values
        _constructors = tuple(c if isinstance(c, _PartialConstructor) else c.partial()
                              for c in constructors)

        # Get classes for instance checking (see MultitypeMeta)
        _subclses = tuple(c.func for c in _constructors)

        def __new__(cls, *value, **kwargs):
            self = cls._get_instance(*value, **kwargs)
            # Overload syntax string
            self._get_syntax = lambda cls=cls, **_: cls.syntax
            self.typename = cls.typename
            return self

        @classmethod
        def _get_instance(cls, *value, **kwargs):
            errors = []
            for const in cls._constructors:
                try:
                    return const(*value)
                except ValueError as e:
                    errors.append(str(e))
                except TypeError as e:
                    errors.append('Not a %s' % const.typename)
            raise ValueError('; '.join(errors))

        @classproperty
        def typename(cls):
            return ' or '.join((s.typename for s in cls._subclses if s.typename))

        @classproperty
        def syntax(cls):
            return ' or '.join((c.syntax for c in cls._constructors))

        @classmethod
        def _get_syntax(cls, **_):
            return cls.syntax

    return Multitype


class String(str, StringableMixin):
    """
    String

    Options:
      minlen: Minimum length of the string
      maxlen: Maximum length of the string
    """
    typename = 'string'
    defaults = {'minlen': 0,
                'maxlen': _INFINITY}

    def __new__(cls, value, *, minlen=defaults['minlen'], maxlen=defaults['maxlen']):
        # Convert
        self = super().__new__(cls, value)

        # Validate
        self_len = len(self)
        if maxlen is not None and self_len > maxlen:
            raise ValueError('Too long (maximum length is %s)' % maxlen)
        if minlen is not None and self_len < minlen:
            raise ValueError('Too short (minimum length is %s)' % minlen)
        return self

    @staticmethod
    def _get_syntax(minlen=defaults['minlen'], maxlen=defaults['maxlen']):
        text = 'string'
        if ((minlen == 1 or minlen <= 0) and
            (maxlen == 1 or maxlen >= _INFINITY)):
            chrstr = 'character'
        else:
            chrstr = 'characters'
        if minlen > 0 and maxlen < _INFINITY:
            if minlen == maxlen:
                text += ' (%s %s)' % (minlen, chrstr)
            else:
                text += ' (%s-%s %s)' % (minlen, maxlen, chrstr)
        elif minlen > 0:
            text += ' (at least %s %s)' % (minlen, chrstr)
        elif maxlen < _INFINITY:
            text += ' (at most %s %s)' % (maxlen, chrstr)
        return text


class Bool(str, StringableMixin):
    """
    Boolean

    Options:
    TODO: ...
    """
    typename = 'boolean'
    defaults = {'true'  : ('enabled', 'yes', 'on', 'true', '1'),
                'false' : ('disabled', 'no', 'off', 'false', '0')}

    def __new__(cls, value, *, true=defaults['true'], false=defaults['false']):
        if isinstance(value, str):
            _value = value.casefold()
        else:
            _value = value

        # Validate
        if _value in true:
            is_true = True
        elif _value in false:
            is_true = False
        elif isinstance(_value, bool):
            is_true = _value
            if is_true:
                value = true[0]
            else:
                value = false[0]
        else:
            raise ValueError('Not a %s' % cls.typename)

        self = super().__new__(cls, value)
        self._is_true = is_true
        return self

    @staticmethod
    def _get_syntax(true=defaults['true'], false=defaults['false']):
        pairs = []
        for pair in zip(true, false):
            pair = tuple(str(val) for val in pair)
            if pair not in pairs:
                pairs.append(pair)
        return '%s' % '|'.join('/'.join((t,f)) for t,f in pairs)

    def __bool__(self):
        return self._is_true

    def __eq__(self, other):
        if isinstance(other, bool):
            return other == self._is_true
        elif isinstance(other, type(self)):
            return other._is_true == self._is_true
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self._is_true)


class Path(str, StringableMixin):
    """
    File system path

    Options:
      mustexist: Whether the path must exist on the local file system
    """
    typename = 'path'
    defaults = {'mustexist': False}

    def __new__(cls, value, *, mustexist=defaults['mustexist']):
        # Convert
        value = os.path.expanduser(os.path.normpath(value))
        self = super().__new__(cls, value)

        # Validate
        if mustexist and not os.path.exists(self):
            raise ValueError('No such file or directory')

        return self

    @staticmethod
    def _get_syntax(mustexist=defaults['mustexist']):
        return 'file system path'

    @property
    def prettified(self):
        home = os.environ['HOME']
        if self.startswith(home):
            return '~' + self[len(home):]
        else:
            return str(self)


class Tuple(tuple, StringableMixin):
    """
    Immutable list

    Options:
      sep:     Separator between list items when parsing string
      options: Iterable of valid values; any other values raise ValueError
      aliases: <alias> -> <value> mapping: any occurence of <alias> is replaced
               with <value>
      dedup:   Whether to remove duplicate items
    """
    typename = 'list'
    defaults = {'sep'     : ', ',
                'options' : None,
                'aliases' : {},
                'dedup'   : False}

    def __new__(cls, *value, sep=defaults['sep'], options=defaults['options'],
                aliases=defaults['options'], dedup=defaults['dedup']):
        def normalize(val):
            if isinstance(val, str):
                for item in val.split(sep.strip()):
                    yield item.strip()
            else:
                yield val

        # Convert
        value = (chain.from_iterable((normalize(item) for item in value)))
        if aliases:
            value = (_resolve_alias(item, aliases) for item in value)
        if dedup:
            _seen = set()
            value = (item for item in value if not (item in _seen or _seen.add(item)))
        self = super().__new__(cls, value)

        if options is not None:
            # A single '*' replaces it with all available options
            if len(self) == 1 and self[0] == '*':
                self = super().__new__(cls, options)

            # Validate
            invalid_items = tuple(str(item) for item in self if item not in options)
            if invalid_items:
                raise ValueError('Invalid option%s: %s' % (
                    's' if len(invalid_items) != 1 else '',
                    sep.join(invalid_items)))

        return self

    @staticmethod
    def _get_syntax(sep=defaults['sep'], **_):
        sep = sep.strip()
        return '<OPTION>%s<OPTION>%s...' % (sep, sep)

    def __str__(self):
        return self._config['sep'].join(str(item) for item in self)

    @property
    def sep(self):
        return self._config['sep']

    @property
    def options(self):
        return self._config['options']

    @property
    def aliases(self):
        return self._config['aliases']


class Option(str, StringableMixin):
    """
    Single string that can only be one of a given set of string

    Options:
      options: Iterable of valid values; any other values raise ValueError
      aliases: <alias> -> <value> mapping; any occurence of <alias> is replaced
               with <value>
    """
    typename = 'option'
    defaults = {'options': (),
                'aliases': {}}

    def __new__(cls, value, *, options=defaults['options'], aliases=defaults['aliases']):
        value = str(value)
        value = _resolve_alias(value, aliases)

        if not any(value == option for option in options):
            if len(options) == 0:
                raise RuntimeError('No options provided')
            elif len(options) == 1:
                raise ValueError('Not %s' % options[0])
            else:
                raise ValueError('Not one of: %s' % ', '.join((str(o) for o in options)))

        self = super().__new__(cls, value)
        return self

    @staticmethod
    def _get_syntax(options=defaults['options'], aliases=defaults['aliases']):
        return '|'.join(str(opt) for opt in options)

    @property
    def options(self):
        return self._config['options']

    @property
    def aliases(self):
        return self._config['aliases']


class _NumberBase(StringableMixin):
    _prefixes_binary = (('Ti', 1024**4), ('Gi', 1024**3), ('Mi', 1024**2), ('Ki', 1024))
    _prefixes_metric = (('T', 1000**4), ('G', 1000**3), ('M', 1000**2), ('k', 1000))
    _prefixes_dct = {prefix.lower():size
                     for prefix,size in chain.from_iterable(zip(_prefixes_binary,
                                                                _prefixes_metric))}
    _regex = re.compile('^\s*([-+]?(?:\d+\.\d+|\d+|\.\d+|inf)) ?(' +
                        '|'.join(p[0] for p in chain.from_iterable(zip(_prefixes_binary,
                                                                       _prefixes_metric))) +
                        '|)([^\s0-9]*?)\s*$',
                        flags=re.IGNORECASE)

    converters = {
        'B': {'b': lambda value: value * 8},  # bytes to bits
        'b': {'B': lambda value: value / 8},  # bits to bytes
    }
    typename = 'number'
    defaults = {'unit'       : None,
                'convert_to' : None,
                'prefix'     : None,
                'hide_unit'  : None,
                'min'        : None,
                'max'        : None,
                'autolimit'  : None}

    def __new__(cls, value, *, unit=defaults['unit'],
                convert_to=defaults['convert_to'], prefix=defaults['prefix'],
                hide_unit=defaults['hide_unit'], min=defaults['min'],
                max=defaults['max'], autolimit=defaults['autolimit']):
        if isinstance(value, cls):
            # Use value's arguments as defaults
            defaults = value._args
            unit = unit if unit is not None else defaults['unit']
            prefix = prefix if prefix is not None else defaults['prefix']
            hide_unit = hide_unit if hide_unit is not None else defaults['hide_unit']
            value = float(value)

        # Fill in hardcoded defaults
        prefix = 'metric' if prefix is None else prefix
        hide_unit = False if hide_unit is None else hide_unit

        # Parse strings
        if isinstance(value, str):
            string = str(value)
            match = cls._regex.match(string)
            if match is None:
                raise ValueError('Not a %s' % cls.typename)
            else:
                value = float(match.group(1))
                prfx = match.group(2)
                unit = match.group(3) or unit
                if prfx:
                    value *= cls._prefixes_dct[prfx.lower()]

                prfx_len = len(prfx)
                if prfx_len == 2:
                    prefix = 'binary'
                elif prfx_len == 1:
                    prefix = 'metric'

        # Scale number to different unit
        if convert_to is not None and unit != convert_to:
            if unit is None:
                # num has no unit - assume num is already in target unit
                unit = convert_to
            else:
                converters = cls.converters
                if unit in converters and convert_to in converters[unit]:
                    converter = converters[unit][convert_to]
                    value = converter(value)
                    unit = convert_to
                else:
                    raise ValueError('Cannot convert %s to %s' % (unit, convert_to))

        if issubclass(cls, int):
            try:
                value = round(value)
            except OverflowError:
                raise ValueError('Not a %s' % cls.typename)

        if min is not None and value < min:
            if autolimit:
                value = min
            else:
                raise ValueError('Too small (minimum is %s)' % min)
        elif max is not None and value > max:
            if autolimit:
                value = max
            else:
                raise ValueError('Too big (maximum is %s)' % max)

        try:
            self = super().__new__(cls, value)
        except TypeError:
            raise ValueError('Not a %s' % cls.typename)

        if hide_unit:
            self._str = lambda: self.without_unit
        else:
            self._str = lambda: self.with_unit

        if prefix == 'binary':
            self._prefixes = self._prefixes_binary
        elif prefix == 'metric':
            self._prefixes = self._prefixes_metric
        elif prefix == 'none':
            self._prefixes = ()
        else:
            raise ValueError("prefix must be 'binary' or 'metric'")

        # Remember arguments so we can copy them if this instance is passed to the same class
        self._args = {'unit': unit, 'prefix': prefix, 'hide_unit': hide_unit,
                      'min': min, 'max': max, 'autolimit': autolimit}
        return self

    @classmethod
    def _get_syntax(cls, **_):
        prefixes = (p[0] for p in chain(cls._prefixes_binary, cls._prefixes_metric))
        return '<NUMBER>[%s]' % '|'.join(prefixes)

    def __str__(self):
        return self._str()

    @property
    def with_unit(self):
        """String representation including unit"""
        s = self.without_unit
        unit = self._args['unit']
        if unit is not None:
            s += unit
        return s

    @property
    def without_unit(self):
        """String representation excluding unit"""
        absolute = abs(self)
        if self == 0:
            # This should increase efficiency since 0 is a common value
            return '0'
        elif absolute >= _INFINITY:
            return _pretty_float(self)
        else:
            for prefix,size in self._prefixes:
                if absolute >= size:
                    # Converting to float/int before doing the math is faster
                    # because we overload math operators.
                    return _pretty_float(float(self) / size) + prefix
            return _pretty_float(self)

    @property
    def unit(self):
        return self._args['unit']

    @property
    def hide_unit(self):
        return self._args['hide_unit']

    @property
    def prefix(self):
        return self._args['prefix']

    def _do_math(self, funcname, other=None, **kwargs):
        # If self and other have a unit specified, convert other if possible, or
        # raise an exception.
        if other is not None and isinstance(other, _NumberBase) and self.unit != other.unit:
            other = other.copy(other, convert_to=self.unit)

        # Get the new value as int or float
        if self >= _INFINITY:
            # No need to do anything with infinity because `int` has no infinity
            # value implemented.
            result = _INFINITY
        else:
            result = getattr(float(self), funcname)(other, **kwargs)

        if result is NotImplemented:
            return NotImplemented
        elif not hasattr(result, 'is_integer') or result.is_integer():
            result_cls = Int
        else:
            result_cls = Float

        # Create new instance with copied properties
        return result_cls(result, **self._args)

    def __add__(self, other):          return self._do_math('__add__', other)
    def __sub__(self, other):          return self._do_math('__sub__', other)
    def __mul__(self, other):          return self._do_math('__mul__', other)
    def __div__(self, other):          return self._do_math('__div__', other)
    def __truediv__(self, other):      return self._do_math('__truediv__', other)
    def __floordiv__(self, other):     return self._do_math('__floordiv__', other)
    def __mod__(self, other):          return self._do_math('__mod__', other)
    def __divmod__(self, other):       return self._do_math('__divmod__', other)
    def __pow__(self, other):          return self._do_math('__pow__', other)
    def __floor__(self):               return self._do_math('__floor__')
    def __ceil__(self):                return self._do_math('__ceil__')
    def __round__(self, ndigits=None): return self._do_math('__round__', ndigits)

class Float(_NumberBase, float):
    """
    Floating point number

    TODO: ...
    """

class Int(_NumberBase, int):
    """
    Integer number

    TODO: ...
    """
