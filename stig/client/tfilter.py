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

import re
import operator
from itertools import zip_longest
from collections import abc

from .tkeys import TYPES as VALUETYPES


class _Filter():
    """A filter specification"""

    def __init__(self, checkfunc, needed_keys, description, aliases=(), value_type=None):
        self.checkfunc = checkfunc
        self.needed_keys = needed_keys
        self.value_type = value_type
        self.aliases = aliases
        if description.startswith('...'):
            self.description = 'Torrents that are ' + description[3:].strip()
        elif description.startswith(':::'):
            self.description = 'Match VALUE against the ' + description[3:].strip()
        else:
            self.description = description

    def __call__(self, *args, **kwargs):
        return self.checkfunc(*args, **kwargs)


# Filters without arguments
BOOLEAN_FILTERS = {
    # '...' is replaced with 'Torrents that are'
    'all':               _Filter(lambda t: True,
                                 aliases=('*',),
                                 needed_keys=(),
                                 description='All torrents'),
    'verifying':         _Filter(lambda t: t['status'] == 'verifying',
                                 aliases=('checking',),
                                 needed_keys=('status',),
                                 description='... being verified or queued for verification'),
    'stopped':           _Filter(lambda t: t['status'] == 'stopped',
                                 aliases=('paused',),
                                 needed_keys=('status',),
                                 description='... not allowed to up- or download'),
    'seeding':           _Filter(lambda t: t['status'] == 'seeding',
                                 needed_keys=('status',),
                                 description='... complete and offered for download'),
    'leeching':          _Filter(lambda t: t['status'] == 'leeching',
                                 needed_keys=('status',),
                                 description='... downloading or waiting for seeds'),
    'complete':          _Filter(lambda t: t['%downloaded'] >= 100,
                                 needed_keys=('%downloaded',),
                                 description='Torrents with all wanted files complete'),
    'active':            _Filter(lambda t: t['peers-connected'] > 0 or t['status'] == 'verifying',
                                 needed_keys=('peers-connected', 'status'),
                                 description='... connected to peers or being verified'),
    'downloading':       _Filter(lambda t: t['rate-down'] > 0,
                                 needed_keys=('rate-down',),
                                 description='... using download bandwidth'),
    'uploading':         _Filter(lambda t: t['rate-up'] > 0,
                                 needed_keys=('rate-up',),
                                 description='... using upload bandwidth'),
    'idle':              _Filter(lambda t: t['stalled'],
                                 needed_keys=('stalled',),
                                 description='... not down- or uploading but not stopped'),
    'private':           _Filter(lambda t: t['private'],
                                 needed_keys=('private',),
                                 description='... only connectable through trackers'),
    'public':            _Filter(lambda t: not t['private'],
                                 needed_keys=('private',),
                                 description='... connectable through DHT and/or PEX'),
    'isolated':          _Filter(lambda t: t['isolated'],
                                 needed_keys=('isolated',),
                                 description='... cannot discover new peers in any way'),
}


# Filters with arguments
COMPARATIVE_FILTERS = {}

# Most comparative filters are almost identical
for name,aliases,key,desc in (
        # ':::' is replaced with 'Matches VALUE against the'
        ('connections', ('conn',), 'peers-connected', '::: number of connected peers'),
        ('%downloaded', ('%done', '%complete'), '%downloaded', '::: percentage of downloaded bytes'),
        ('downloaded', ('down',), 'size-downloaded', '::: number of downloaded bytes'),
        ('id', (), 'id', '::: ID'),
        ('path', ('dir',), 'path', '::: full path to download directory'),
        ('name', ('title',), 'name', '::: name'),
        ('ratio', (), 'ratio', '::: uploadded/downloaded ratio'),
        ('rate-down', ('rdown',), 'rate-down', '::: download rate'),
        ('rate-up', ('rup',), 'rate-up', '::: upload rate'),
        ('seeds', (), 'peers-seeding', '::: largest number of seeds reported by any tracker'),
        ('size', (), 'size-final', '::: combined size of all wanted files'),
        ('uploaded', ('up',), 'size-uploaded', '::: number of uploaded bytes'),
    ):
    # key=key is needed to make the key variable local inside the lambda.
    # Without it, it is always be set to the last key in the looped-over tuple
    # above when filterfunc is called.
    filterfunc = lambda t, op, v, key=key: op(t[key], v)
    COMPARATIVE_FILTERS[name] = _Filter(filterfunc,
                                        aliases=aliases,
                                        needed_keys=(key,),
                                        value_type=VALUETYPES[key],
                                        description=desc)

COMPARATIVE_FILTERS['tracker'] = _Filter(
    lambda t, op, v: any(op(tracker['url-announce'].domain, v)
                       for tracker in t['trackers']),
    needed_keys=('trackers',),
    value_type=str,
    description='::: domain of the announce URL of trackers'
)
# TODO: Add more filters 'time-created', 'time-added', 'time-started',
# 'time-finished', 'time-active'


_NEEDED_KEYS = {}
_ALIASES = {}
for filters in (BOOLEAN_FILTERS, COMPARATIVE_FILTERS):
    for fname,f in filters.items():
        _NEEDED_KEYS[fname] = f.needed_keys
        for alias in f.aliases:
            if alias in _ALIASES:
                raise RuntimeError('Filter alias {!r} exists twice!'.format(alias))
            _ALIASES[alias] = fname


def _check_value(name, value, op):
    """Convert `value` to correct type for filter `name`, ensure op is compatible

    Raises ValueError on failure.
    """
    if name not in COMPARATIVE_FILTERS:
        return value

    # Convert value to proper type
    target_type = COMPARATIVE_FILTERS[name].value_type
    if type(value) is not target_type:
        try:
            value = target_type(value)
        except ValueError:
            raise ValueError('Invalid value for filter {!r}: {!r}'.format(name, value))

    # Make sure value and operator are compatible
    if op == '~' and not isinstance(value, str):
        raise ValueError('Invalid operator for filter {!r}: {}'.format(name, op))

    return value


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


class _TorrentFilter():
    """A single filter, e.g. idle"""

    def __init__(self, filter_str=''):
        # name: Name of filter (user-readable string)
        # invert: Whether to invert filter (bool)
        # op: Comparison operator as string (see _OPERATORS)
        # value: User-given value as string (will be converted to proper type)
        name, invert, op, value = (None, False, None, None)
        if filter_str != '':
            match = _FILTER_REGEX.fullmatch(filter_str)
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
            name = 'name'
        elif name in _ALIASES:
            name = _ALIASES[name]

        # Make sure value has the correct type and operator is compatible
        if value is not None:
            value = _check_value(name, value, op)

        log.debug('Parsed filter %r: name=%r, invert=%r, op=%r, value=%r',
                  filter_str, name, invert, op, value)

        # Filter that doesn't use value argument
        if name in BOOLEAN_FILTERS:
            self._check_func = BOOLEAN_FILTERS[name]
            self.needed_keys = _NEEDED_KEYS[name]

        # Filter that needs an argument
        elif name in COMPARATIVE_FILTERS:
            f = COMPARATIVE_FILTERS[name]
            if op is None and value is None:
                # Abuse comparative filter as boolean filter
                # (e.g. 'peers-connected' matches torrents with peers-connect!=0)
                keys = f.needed_keys
                self._check_func = lambda t, keys=keys: all(bool(t[key]) for key in keys)
                self.needed_keys = _NEEDED_KEYS[name]

            elif op is None:
                ops = '[' + '|'.join(sorted(_OPERATORS)) + ']'
                raise ValueError('Missing operator and value: {} {} ...'.format(name, ops))
            elif value is None:
                raise ValueError('Missing value: {} ...'.format(filter_str))
            else:
                self._check_func = lambda t, f=f, v=value, op=_OPERATORS[op]: f(t, op, v)
                self.needed_keys = _NEEDED_KEYS[name]

        elif value is op is None:
            # `name` is no known filter - default to filter 'name' and
            # operator '~'.
            value = name
            name = 'name'
            op = '~'
            key = 'name'
            self.needed_keys = (key,)
            self._check_func = lambda t, key=key, op=_OPERATORS[op], v=value: op(t[key], v)
        else:
            raise ValueError('Invalid filter name: {!r}'.format(name))

        self._name, self._invert, self._op, self._value = name, invert, op, value
        self._hash = hash((name, invert, op, value))

    def apply(self, torrents, invert=False, ids=False):
        """Yield torrents or torrent IDs that match"""
        invert = self._invert ^ bool(invert)  # xor
        wanted = self._check_func
        for t in torrents:
            if wanted(t) ^ invert:
                yield t['id'] if ids else t

    def match(self, torrent):
        """Return True if `torrent` matches filter, False otherwise"""
        return self._check_func(torrent) ^ self._invert

    def __eq__(self, other):
        if isinstance(other, type(self)):
            for attr in ('_name', '_value', '_invert', '_op'):
                if getattr(self, attr) != getattr(other, attr):
                    return False
            return True
        else:
            return NotImplemented

    def __str__(self):
        if self._name is None:
            return 'all'
        elif self._value is None:
            return ('!' if self._invert else '') + self._name
        else:
            name = self._name if self._name != 'name' else ''
            op = ('!' if self._invert else '') + self._op
            val = str(self._value)
            return name + op + val

    def __repr__(self):
        return '<{} {}>'.format(type(self).__name__, str(self))

    def __hash__(self):
        return self._hash


_NOFILTER = _TorrentFilter('all')

class TorrentFilter():
    """One or more filters combined with & and | operators"""

    _op_regex = re.compile(r'([&|])')

    def __init__(self, filters=''):
        if isinstance(filters, str):  # Because str is also instance of abc.Sequence
            pass
        elif isinstance(filters, abc.Sequence) and all(isinstance(f, str) for f in filters):
            filters = '|'.join(filters)
        elif not isinstance(filters, str):
            raise TypeError('filters must be string or sequence of strings, not {}: {!r}'
                            .format(type(filters).__name__, filters))

        parts = tuple(part for part in self._op_regex.split(filters) if part is not '')
        if len(parts) < 1:
            self._filterchains = ()
        else:
            if parts[0] in '&|':
                raise ValueError('Filter can\'t start with operator: {!r}'.format(parts[0]))
            elif parts[-1] in '&|':
                raise ValueError('Filter can\'t end with operator: {!r}'.format(parts[-1]))

            filters = []
            ops = []
            expect = 'filter'
            for i,part in enumerate(parts):
                if expect is 'filter':
                    if part not in '&|':
                        f = _TorrentFilter(part)
                        if f == _NOFILTER:
                            # part is 'all' or '*' - this disables all other filters
                            filters = []
                            ops = []
                            break
                        else:
                            filters.append(f)
                            expect = 'operator'
                            continue
                elif expect is 'operator':
                    if part in '&|':
                        ops.append(part)
                        expect = 'filter'
                        continue
                raise ValueError('Consecutive operators: {!r}'.format(''.join(parts[i-2:i+2])))

            if filters:
                fchain = [[]]
                for filter,op in zip_longest(filters, ops):
                    fchain[-1].append(filter)
                    if op is '|':
                        fchain.append([])
                self._filterchains = tuple(tuple(x) for x in fchain)
            else:
                self._filterchains = ()

    def apply(self, torrents):
        """Yield matching torrents from iterable `torrents`"""
        log.debug('Filtering %d torrents for %s', len(torrents), self)

        def torrent_is_a_hit(t):
            # All filters in an AND_chain must match for the AND_chain to
            # match.  At least one AND_chain must match.
            if any(all(f.match(t) for f in AND_chain)
                   for AND_chain in self._filterchains):
                return True
            else:
                return False

        if self._filterchains:
            yield from filter(torrent_is_a_hit, torrents)
        else:
            yield from torrents

    @property
    def needed_keys(self):
        """The Torrent keys needed for filtering"""
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
            return 'all'
        else:
            OR_chains = []
            for AND_chain in self._filterchains:
                OR_chains.append('&'.join(str(f) for f in AND_chain))
            return '|'.join(OR_chains)

    def __repr__(self):
        return '<{} {}>'.format(type(self).__name__, str(self))

    def __add__(self, other):
        cls = type(self)
        nofilter = cls()
        if not isinstance(other, cls):
            return NotImplemented
        elif other == nofilter or self == nofilter:
            return nofilter
        else:
            # Start with our own stuff
            new_fc = list(self._filterchains)

            # Because foo&bar is the same as bar&foo, comparing sets makes
            # everything much easier
            self_fc_sets = tuple(set(x) for x in self._filterchains)

            # Copy each AND_chain from other unless we already have it
            for AND_chain in other._filterchains:
                AND_chain_set = set(AND_chain)
                if AND_chain_set not in self_fc_sets:
                    new_fc.append(AND_chain)

            # Make string from new_fc
            OR_chains = []
            for AND_chain in new_fc:
                OR_chains.append('&'.join(str(f) for f in AND_chain))
            new_fc_str = '|'.join(OR_chains)

            return cls(new_fc_str)
