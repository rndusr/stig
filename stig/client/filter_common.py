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

"""Common stuff for Torrent and TorrentFile filters"""

from ..logging import make_logger
log = make_logger(__name__)

import operator
import re


class BoolFilterSpec():
    """Boolean filter specification"""

    def __init__(self, func, needed_keys=(), aliases=(), description='No description'):
        self.filter_function = func
        self.needed_keys = needed_keys
        self.aliases = aliases

        if description.startswith('...'):
            self.description = 'Torrents that are ' + description[3:].strip()
        elif description.startswith(':::'):
            self.description = 'Match VALUE against the ' + description[3:].strip()
        else:
            self.description = description


class CmpFilterSpec(BoolFilterSpec):
    """Comparative filter specification"""

    def __init__(self, *args, value_type, **kwargs):
        super().__init__(*args, **kwargs)
        self.value_type = value_type

    def make_filter_func(self, operator, value):
        func = self.filter_function
        return lambda obj: func(obj, operator, value)


class Filter():
    """Match sequences of objects against a single filter"""

    _OPERATORS = {
        '=': operator.__eq__, '~': operator.__contains__,
        '>': operator.__gt__, '<': operator.__lt__,
        '>=': operator.__ge__, '<=': operator.__le__,
    }
    _OP_CHARS = ''.join(_OPERATORS)
    _OP_LIST = '(?:' + '|'.join(sorted(_OPERATORS, key=lambda op: len(op), reverse=True)) + ')'
    _INVERT_CHAR = '!'
    _FILTER_REGEX = re.compile(r'^'
                               r'(?P<invert1>' + _INVERT_CHAR + '?)'
                               r'(?P<name>[^' + _OP_CHARS+_INVERT_CHAR + ']*)'
                               r'(?P<invert2>' + _INVERT_CHAR + '?)'
                               r'(?P<op>' + _OP_LIST + '|)'
                               r'(?P<value>.*)$')

    DEFAULT_FILTER = None

    BOOLEAN_FILTERS = {}
    COMPARATIVE_FILTERS = {}

    @classmethod
    def _check_value(cls, name, value, op):
        """Convert `value` to correct type for comparative filter `name`

        Also ensure operator `op` is compatible with `value`.

        Raises ValueError
        """
        if name not in cls.COMPARATIVE_FILTERS:
            return value

        # Convert value to proper type
        target_type = cls.COMPARATIVE_FILTERS[name].value_type
        if type(value) is not target_type:
            try:
                value = target_type(value)
            except ValueError:
                raise ValueError('Invalid value for filter {!r}: {!r}'.format(name, value))

        # Make sure value and operator are compatible
        if op == '~' and not isinstance(value, str):
            raise ValueError('Invalid operator for filter {!r}: {}'.format(name, op))

        return value

    @classmethod
    def _resolve_alias(cls, name):
        if not hasattr(cls, '_aliases'):
            aliases = {}
            for fseq in (cls.BOOLEAN_FILTERS, cls.COMPARATIVE_FILTERS):
                for fname,f in fseq.items():
                    for a in f.aliases:
                        aliases[a] = fname
            cls._aliases = aliases
        return cls._aliases.get(name, name)

    def __init__(self, filter_str=''):
        # name: Name of filter (user-readable string)
        # invert: Whether to invert filter (bool)
        # op: Comparison operator as string (see _OPERATORS)
        # value: User-given value as string (will be converted to proper type)
        name, invert, op, value = (None, False, None, None)
        if filter_str != '':
            match = self._FILTER_REGEX.fullmatch(filter_str)
            if match is None:
                raise ValueError('Invalid filter: {!r}'.format(filter_str))
            else:
                name = match.group('name')
                op = match.group('op') or None
                invert = bool(match.group('invert1')) ^ bool(match.group('invert2'))
                value = match.group('value')
                value = None if value.strip() == '' else value

        # No operator but a value doesn't make any sense
        if op is None and value is not None:
            raise ValueError('Malformed filter expression: {!r}'.format(filter_str))

        # Handle spaces around operator: If there's a space before the
        # operator, strip value.  Otherwise, preserve them.  In any case,
        # strip name.
        if op is not None:
            if name.endswith(' '):
                value = value.strip(' ')
        if name is not None:
            name = name.strip()

        if name is None:
            # No filter_str provided
            name = 'all'
        elif name is '':
            # No filter name is given, but a value and maybe an operator.
            name = self.DEFAULT_FILTER
        else:
            name = self._resolve_alias(name)

        # Make sure value has the correct type and operator is compatible
        if value is not None:
            value = self._check_value(name, value, op)

        log.debug('Parsed filter %r: name=%r, invert=%r, op=%r, value=%r',
                  filter_str, name, invert, op, value)

        # Filter that doesn't use value argument
        if name in self.BOOLEAN_FILTERS:
            f = self.BOOLEAN_FILTERS[name]
            self._filter_func = f.filter_function
            self._needed_keys = f.needed_keys

        # Filter that needs an argument
        elif name in self.COMPARATIVE_FILTERS:
            f = self.COMPARATIVE_FILTERS[name]
            self._needed_keys = f.needed_keys
            if op is None and value is None:
                # Abuse comparative filter as boolean filter
                # (e.g. 'peers-connected' matches torrents with peers-connected!=0)
                self._filter_func = lambda obj, keys=f.needed_keys: all(bool(obj[key]) for key in keys)
            elif op is None:
                ops = '[' + '|'.join(sorted(self._OPERATORS)) + ']'
                raise ValueError('Missing operator and value: {} {} ...'.format(name, ops))
            elif value is None:
                raise ValueError('Missing value: {} ...'.format(filter_str))
            else:
                self._filter_func = f.make_filter_func(self._OPERATORS[op], value)

        elif value is op is None:
            # `name` is no known filter - default to DEFAULT_FILTER with operator '~'.
            value = name
            op = '~'
            name = self.DEFAULT_FILTER
            if name in self.BOOLEAN_FILTERS:
                f = self.BOOLEAN_FILTERS[name]
                self._filter_func = f.filter_function
            elif name in self.COMPARATIVE_FILTERS:
                f = self.COMPARATIVE_FILTERS[name]
                self._filter_func = f.make_filter_func(self._OPERATORS[op], value)
            else:
                raise RuntimeError('Default filter {!r} does not exist: {!r}'
                                   .format(name, ', '.join(tuple(self.BOOLEAN_FILTERS) +
                                                           tuple(self.COMPARATIVE_FILTERS))))
            self._needed_keys = f.needed_keys

        else:
            raise ValueError('Invalid filter name: {!r}'.format(name))

        self._name, self._invert, self._op, self._value = name, invert, op, value
        self._hash = hash((name, invert, op, value))

    def apply(self, objs, invert=False, key=None):
        """Yield matching objects or `key` of each matching object"""
        invert = self._invert ^ bool(invert)  # xor
        wanted = self._filter_func
        for i in objs:
            if wanted(i) ^ invert:
                yield i if key is None else i[key]

    def match(self, obj):
        """Return True if `obj` matches, False otherwise"""
        return self._filter_func(obj) ^ self._invert

    def __str__(self):
        if self._name is None:
            return 'all'
        elif self._value is None:
            return ('!' if self._invert else '') + self._name
        else:
            name = self._name if self._name != self.DEFAULT_FILTER else ''
            op = ('!' if self._invert else '') + self._op
            val = str(self._value)
            return name + op + val

    @property
    def needed_keys(self):
        return self._needed_keys

    def __eq__(self, other):
        if isinstance(other, type(self)):
            for attr in ('_name', '_value', '_invert', '_op'):
                if getattr(self, attr) != getattr(other, attr):
                    return False
            return True
        else:
            return NotImplemented

    def __repr__(self):
        return '<{} {}>'.format(type(self).__name__, str(self))

    def __hash__(self):
        return self._hash
