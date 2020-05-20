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

import itertools
import operator
import re
from collections import abc

from ...utils import cliparser

from ...logging import make_logger  # isort:skip
log = make_logger(__name__)


BOOLEAN = 'boolean'
COMPARATIVE = 'comparative'


class BoolFilterSpec():
    """Boolean filter specification"""

    type = BOOLEAN

    def __init__(self, func, *, needed_keys=(), aliases=(), description='No description'):
        if not func:
            self.filter_function = None
            needed_keys = ()
        else:
            self.filter_function = func
        self.needed_keys = needed_keys
        self.aliases = aliases
        self.description = description


class CmpFilterSpec():
    """Comparative filter specification"""

    type = COMPARATIVE

    def __init__(self, *, value_type, value_getter=None, value_matcher=None,
                 value_convert=None, as_bool=None, needed_keys=(), aliases=(),
                 description='No description'):
        """
        value_type    : Subclass of `type` (i.e. something that returns an instance when
                        called and can be passed to `isinstance` as the second argument
        value_getter  : Callable that takes an item and returns one or more
                        values to match against the user-provided value;
                        Multiple values must be given as an iterator (list,
                        tuple, generator, etc), and the item matches if any
                        match
        value_convert : Callable that takes a value and converts it to something
                        comparable (e.g. "42" (str) -> 42 (int))
        value_matcher : Callable that takes (item, operator, value) and returns True/False
        as_bool       : Callable that takes an item and returns True/False
        needed_keys   : Needed keys for this filter
        aliases       : Alternative names of this filter
        """
        self.value_type = value_type
        self.needed_keys = needed_keys
        self.aliases = aliases
        self.description = description
        self.value_convert = value_convert if value_convert is not None else value_type

        if value_getter is not None:
            self.value_getter = value_getter
        elif len(self.needed_keys) == 1:
            self.value_getter = lambda dct, k=needed_keys[0]: dct[k]
        else:
            raise TypeError('Missing argument with needed_keys=%r: value_getter', self.needed_keys)

        if value_matcher is None:
            def value_matcher(item, op, user_value, vg=self.value_getter):
                item_value = vg(item)
                if isinstance(item_value, abc.Iterator):
                    return any(op(ival, user_value) for ival in item_value)
                else:
                    return op(item_value, user_value)
        self.value_matcher = value_matcher

        if as_bool is None:
            def as_bool(item, vg=self.value_getter):
                item_value = vg(item)
                if isinstance(item_value, abc.Iterator):
                    return any(item_value)
                else:
                    return bool(item_value)
        self.as_bool = as_bool

    def make_filter(self, operator, user_value, invert):
        if operator is None and user_value is None:
            # Abuse comparative filter as boolean filter
            # (e.g. 'peers-connected' matches torrents with peers-connected!=0)
            return (self.as_bool, self.needed_keys, invert)
        elif user_value is None:
            # Operator with no value matches everything
            return (None, (), False)
        else:
            def f(obj, vm=self.value_matcher, op=operator, val=user_value):
                return vm(obj, op, val)
            return (f, self.needed_keys, invert)


class FilterSpecDict(abc.Mapping):
    """TODO"""
    _NOT_FOUND = object()

    def __init__(self, dct):
        self._dct = dct

    def __getitem__(self, key):
        value = self._dct.get(key, self._NOT_FOUND)
        if value is not self._NOT_FOUND:
            return value
        for value in self._dct.values():
            if key in value.aliases:
                return value
        raise KeyError(key)

    def __iter__(self):
        return iter(self._dct)

    def __len__(self):
        return len(self._dct)

    def __repr__(self):
        return '%s(%r)' % (type(self).__name__, self._dct)


class Filter():
    """Match sequences of objects against a single filter"""

    OPERATORS = {
        '='  : operator.__eq__, '~'  : operator.__contains__,
        '>'  : operator.__gt__, '<'  : operator.__lt__,
        '>=' : operator.__ge__, '<=' : operator.__le__,
        '=~' : lambda a, b: re.search(b, a),
    }
    INVERT_CHAR = '!'
    POSSIBLE_OPERATORS = tuple(itertools.chain.from_iterable((op, '!' + op)
                                                             for op in OPERATORS))
    DEFAULT_FILTER = None
    DEFAULT_OPERATOR = '~'
    BOOLEAN_FILTERS = {}
    COMPARATIVE_FILTERS = {}

    @classmethod
    def _resolve_alias(cls, name):
        """
        Return real filter name or `name` if it does not resolve
        """
        if not hasattr(cls, '_aliases'):
            aliases = {}
            for fspecs in (cls.BOOLEAN_FILTERS, cls.COMPARATIVE_FILTERS):
                for fname,f in fspecs.items():
                    for a in f.aliases:
                        if a in aliases:
                            raise RuntimeError('Multiple aliases: %r' % (a,))
                        else:
                            aliases[a] = fname
            cls._aliases = aliases
        if name is None:
            name = ''
        return cls._aliases.get(name.strip(), name)

    @classmethod
    def _get_filter_spec(cls, name):
        """
        Get filter spec by `name`

        Raise ValueError on error
        """
        fspec = cls.BOOLEAN_FILTERS.get(name)
        if fspec is not None:
            return fspec
        fspec = cls.COMPARATIVE_FILTERS.get(name)
        if fspec is not None:
            return fspec
        if name:
            raise ValueError('Invalid filter name: %r' % (name,))
        else:
            raise ValueError('No filter expression given')

    @classmethod
    def _make_filter(cls, name, op, user_value, invert):
        """
        Return filter function, needed keys and invert

        Filter function takes a value and returns whether it matches
        `user_value`.

        Filter function and needed keys are both `None` if everything is
        matched.

        Raise ValueError on error
        """
        # Ensure value is wanted by filter, compatible to operator and of proper type
        user_value = cls._validate_user_value(name, op, user_value)
        log.debug('  Validated user_value: %r', user_value)

        fspec = cls._get_filter_spec(name)
        if fspec.type is BOOLEAN:
            return (fspec.filter_function, fspec.needed_keys, invert)
        elif fspec.type is COMPARATIVE:
            return fspec.make_filter(cls.OPERATORS.get(op), user_value, invert)

    @classmethod
    def _validate_user_value(cls, name, op, user_value):
        """
        Ensure that the `name`, `op`, and `user_value` make sense in conjunction

        Return user value as correct type (e.g. `int`) for filter `name`

        Raise ValueError if anything smells funky
        """
        log.debug('  Validating user value: name=%r, op=%r, user_value=%r',
                  name, op, user_value)

        if name in cls.BOOLEAN_FILTERS:
            # log.debug('%r is a valid boolean filter: %r', name, cls.BOOLEAN_FILTERS[name])
            if user_value:
                raise ValueError('Boolean filter does not take a value: %s' % (name,))
            elif op:
                raise ValueError('Boolean filter does not take an operator: %s' % (name,))

        if op is None or user_value is None:
            # Filter `name` could still be (ab)used as boolean filter
            return None

        fspec = cls.COMPARATIVE_FILTERS.get(name)
        if fspec is None:
            if name:
                raise ValueError('Invalid filter name: %r' % (name,))
            else:
                raise ValueError('No filter expression given')

        # Convert user_value to proper type
        if type(user_value) is not fspec.value_type:
            log.debug('  Converting %r to %r', user_value, fspec.value_type)
            try:
                user_value = fspec.value_convert(user_value)
            except ValueError:
                raise ValueError('Invalid value for filter %r: %r' % (name, user_value))

        # In case of regex operator, compile user_value
        if op == '=~':
            try:
                user_value = re.compile(user_value)
            except re.error as e:
                raise ValueError('Invalid regular expression: %s: %s' % (str(e).capitalize(), user_value))
        else:
            # Test if target_type supports operator
            try:
                log.debug('Trying %r(%r [%r], %r [%r])',
                          cls.OPERATORS[op], user_value, type(user_value), user_value, type(user_value))
                cls.OPERATORS[op](user_value, user_value)
            except TypeError:
                raise ValueError('Invalid operator for filter %r: %s' % (name, op))

        return user_value

    @classmethod
    def _parse_inverter(cls, string, invert):
        if not string:
            return string, invert

        # Find INVERT_CHAR at start or end of string
        parts = cliparser.tokenize(string.strip(), delims=(cls.INVERT_CHAR,), escapes=('\\',), quotes=())
        if cls.INVERT_CHAR in parts:
            if parts and parts[0] == cls.INVERT_CHAR:
                parts.pop(0)
                invert = not invert
            if parts and parts[-1] == cls.INVERT_CHAR:
                parts.pop(-1)
                invert = not invert
            return ''.join(parts), invert
        else:
            # Return string unchanged
            return string, invert

    def __init__(self, filter_str=''):
        # name: Name of filter (user-readable string)
        # invert: Whether to invert filter (bool)
        # op: Comparison operator as string (see OPERATORS)
        # user_value: User-given value that is matched against items
        # The *_raw variables contain original quotes and backslashes.
        name_raw, op_raw, user_value_raw, invert = (None, None, None, False)

        log.debug('Parsing %r', filter_str)
        parts = cliparser.tokenize(filter_str, maxdelims=1, delims=self.OPERATORS, escapes=('\\',))
        log.debug('Parts: %r', parts)
        if len(parts) == 3:
            name_raw, op_raw, user_value_raw = parts
        elif len(parts) == 2:
            if parts[0] in self.OPERATORS:
                op_raw, user_value_raw = parts
                name_raw = self.DEFAULT_FILTER
            elif parts[1] in self.OPERATORS:
                name_raw, op_raw = parts
            else:
                raise ValueError('Malformed filter expression: %r' % (filter_str,))
        elif len(parts) == 1:
            if parts[0] in self.OPERATORS:
                op_raw = parts[0]
            else:
                name_raw = parts[0]
        else:
            raise ValueError('Malformed filter expression: %r' % (filter_str,))
        name_raw, invert = self._parse_inverter(name_raw, invert)
        log.debug('Parsed %r into raw: name=%r, invert=%r, op=%r, user_value=%r',
                  filter_str, name_raw, invert, op_raw, user_value_raw)

        # Remove all special characters (backslashes, quotes)
        name, op, user_value = map(lambda x: None if x is None else cliparser.plaintext(x),
                                   (name_raw, op_raw, user_value_raw))
        log.debug('  Plaintext: name=%r, invert=%r, op=%r, user_value=%r',
                  name, invert, op, user_value)

        name = self._resolve_alias(name)
        log.debug('  Resolved alias: name=%r, op=%r, user_value=%r', name, op, user_value)

        if not name:
            name = self.DEFAULT_FILTER
            log.debug('  Falling back to default filter: %r', name)

        try:
            log.debug('  Getting filter spec: name=%r, op=%r, user_value=%r', name, op, user_value)
            # Get filter spec by `name`
            filter_func, needed_keys, invert = self._make_filter(name, op, user_value, invert)
        except ValueError:
            # Filter spec lookup failed
            if self.DEFAULT_FILTER and user_value is op is None:
                # No `user_value` or `op` given - use the first part of the
                # filter expression (normally the filter name) as `user_value`
                # for DEFAULT_FILTER.
                name, op, user_value = self.DEFAULT_FILTER, self.DEFAULT_OPERATOR, name
                log.debug('  Using name as value for default filter: name=%r, op=%r, user_value=%r',
                          name, op, user_value)
                filter_func, needed_keys, invert = self._make_filter(name, op, user_value, invert)
            else:
                # No DEFAULT_FILTER is set, so we can't default to it
                raise

        log.debug('  Final filter: name=%r, invert=%r, op=%r, user_value=%r',
                  name, invert, op, user_value)
        self._filter_func = filter_func
        self._needed_keys = needed_keys
        self._name, self._invert, self._op, self._user_value = name, invert, op, user_value
        self._hash = hash((name, invert, op, user_value))

    def apply(self, objs, invert=False, key=None):
        """Yield matching objects or `key` of each matching object"""
        invert = self._invert ^ bool(invert)  # xor
        is_wanted = self._filter_func
        if is_wanted is None:
            if invert:
                # This filter matches nothing
                yield from ()
            else:
                # This filter matches everything
                if key is None:
                    yield from objs
                else:
                    for obj in objs:
                        yield obj[key]
        else:
            if key is None:
                for obj in objs:
                    if bool(is_wanted(obj)) ^ invert:
                        yield obj
            else:
                for obj in objs:
                    if bool(is_wanted(obj)) ^ invert:
                        yield obj[key]

    def match(self, obj):
        """Return True if `obj` matches, False otherwise"""
        is_wanted = self._filter_func
        if is_wanted is None:
            # This filter matches everything/nothing
            return not self._invert
        else:
            return bool(is_wanted(obj)) ^ self._invert

    def __str__(self):
        if self._name is None:
            return self.DEFAULT_FILTER or ''
        elif self._op is None:
            return ('!' if self._invert else '') + self._name
        else:
            name = self._name if self._name != self.DEFAULT_FILTER else ''
            op = ('!' if self._invert else '') + self._op
            user_value = self._user_value
            if user_value is None:
                return name + op
            else:
                val = str(user_value)
                if val == '':
                    val = "''"
                elif len(val) == 1:
                    val = cliparser.escape(val, delims=(' ', '&', '|'), quotes=("'", '"'))
                else:
                    val = cliparser.quote(val, delims=(' ', '&', '|'), quotes=("'", '"'))
                return name + op + val

    @property
    def needed_keys(self):
        return self._needed_keys

    @property
    def match_everything(self):
        return not self._filter_func

    @property
    def inverted(self):
        return self._invert

    def __eq__(self, other):
        if isinstance(other, type(self)):
            for attr in ('_name', '_user_value', '_invert', '_op'):
                if getattr(self, attr) != getattr(other, attr):
                    return False
            return True
        else:
            return NotImplemented

    def __repr__(self):
        return '%s(%r)' % (type(self).__name__, str(self))

    def __hash__(self):
        return self._hash


# The filter specs are specified on the Filter subclasses in each module, but we
# only want to export the classes derived from FilterChain, so this metalcass
# grabs attributes that are missing from FilterChain from it's 'filterclass'
# attribute.
class _forward_attrs(type):
    def __getattr__(cls, name):
        attr = getattr(cls.filterclass, name)
        setattr(cls, name, attr)
        return attr


class FilterChain(metaclass=_forward_attrs):
    """One or more filters combined with AND and OR operators"""

    filterclass = NotImplemented

    def __init__(self, filters=''):
        if not isinstance(self.filterclass, type) or not issubclass(self.filterclass, Filter):
            raise RuntimeError('Attribute "filterclass" must be set to a Filter subclass')

        if isinstance(filters, str):  # Because str is also instance of abc.Sequence
            pass
        elif isinstance(filters, abc.Sequence) and all(isinstance(f, str) for f in filters):
            filters = '|'.join(filters)
        elif isinstance(filters, (type(self), self.filterclass)):
            filters = str(filters)
        elif not isinstance(filters, str):
            raise ValueError('Filters must be string or sequence of strings, not %s: %r'
                             % (type(filters).__name__, filters))

        self._filterchains = ()

        # Split `filters` at boolean operators
        parts = cliparser.tokenize(filters, delims=('&', '|'))
        if len(parts) > 0 and parts[0]:
            if parts[0] in ('&', '|'):
                raise ValueError("Filter can't start with operator: %r" % (parts[0],))
            elif parts[-1] in ('&', '|'):
                raise ValueError("Filter can't end with operator: %r" % (parts[-1],))

            # The filter chain is represented by a tuple of tuples.  Each inner
            # tuple combines filters with AND.  The outer tuple combines the
            # inner tuples with OR.
            filters = []
            ops = []
            expect = 'filter'
            for i,part in enumerate(parts):
                if expect == 'filter':
                    if part not in '&|':
                        f = self.filterclass(part)
                        if f.match_everything:
                            # One catch-all filter is the same as no filters
                            filters = [f]
                            ops.clear()
                            break
                        else:
                            filters.append(f)
                            expect = 'operator'
                            continue
                elif expect == 'operator' and part in '&|':
                    if part in '&|':
                        ops.append(part)
                        expect = 'filter'
                        continue
                raise ValueError('Consecutive operators: {!r}'.format(''.join(parts[i - 2 : i + 2])))

            fchain = [[]]
            for filter,op in itertools.zip_longest(filters, ops):
                fchain[-1].append(filter)
                if op == '|':
                    fchain.append([])
            log.debug('Chained %r and %r to %r', filters, ops, fchain)
            self._filterchains = tuple(tuple(x) for x in fchain)

    def apply(self, objects):
        """Yield matching objects from iterable `objects`"""
        chains = self._filterchains
        if chains:
            for obj in objects:
                if any(all(f.match(obj) for f in AND_chain)
                       for AND_chain in chains):
                    yield obj
        else:
            yield from objects

    def match(self, obj):
        """Whether `obj` matches this filter chain"""
        # All filters in an AND_chain must match for the AND_chain to
        # match.  At least one AND_chain must match.
        chains = self._filterchains
        if not chains:
            return True
        else:
            return any(all(f.match(obj) for f in AND_chain)
                       for AND_chain in chains)

    @property
    def needed_keys(self):
        """The object keys needed for filtering"""
        keys = set()
        for chain in self._filterchains:
            for filter in chain:
                keys.update(filter.needed_keys)
        return tuple(keys)

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        else:
            # Compare sets because order doesn't matter (foo&bar|baz is the
            # same as baz|bar&foo). Use frozensets because sets are not
            # hashable.
            self_fc_sets = set(frozenset(x) for x in self._filterchains)
            other_fc_sets = set(frozenset(x) for x in other._filterchains)
            return self_fc_sets == other_fc_sets

    def __str__(self):
        if len(self._filterchains) < 1:
            return ''
        else:
            OR_chains = []
            for AND_chain in self._filterchains:
                OR_chains.append('&'.join(str(f) for f in AND_chain))
            return '|'.join(OR_chains)

    def __repr__(self):
        return '%s(%r)' % (type(self).__name__, str(self))

    def __and__(self, other):
        cls = type(self)
        if not isinstance(other, cls):
            return NotImplemented
        else:
            return cls(str(self) + '&' + str(other))

    def __or__(self, other):
        cls = type(self)
        if not isinstance(other, cls):
            return NotImplemented
        else:
            return cls(str(self) + '|' + str(other))
