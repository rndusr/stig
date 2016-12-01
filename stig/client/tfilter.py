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

"""Filtering Torrents by their values"""

from ..logging import make_logger
log = make_logger(__name__)

import re
from itertools import zip_longest
from collections import abc

from .filter_common import (BoolFilterSpec, CmpFilterSpec, Filter)

from .tkeys import TYPES as VALUETYPES
def _make_cmp_filter(key, aliases, description):
    filterfunc = lambda t, op, v, key=key: op(t[key], v)
    return CmpFilterSpec(filterfunc, description=description,
                         needed_keys=(key,), aliases=aliases,
                         value_type=VALUETYPES[key])


class _TorrentFilter(Filter):
    DEFAULT_FILTER = 'name'

    # Filters without arguments
    BOOLEAN_FILTERS = {
        # '...' is replaced with 'Torrents that are'
        'active': BoolFilterSpec(
            lambda t: t['peers-connected'] > 0 or t['status'] == 'verifying',
            description='... connected to peers or being verified',
            needed_keys=('peers-connected', 'status')),
        'all': BoolFilterSpec(
            lambda t: True,
            description='All torrents',
            needed_keys=(),
            aliases=('*',)),
        'complete': BoolFilterSpec(
            lambda t: t['%downloaded'] >= 100,
            description='Torrents with all wanted files complete',
            needed_keys=('%downloaded',)),
        'downloading': BoolFilterSpec(
            lambda t: t['rate-down'] > 0,
            description='... using download bandwidth',
            needed_keys=('rate-down',)),
        'idle': BoolFilterSpec(
            lambda t: t['stalled'],
            description='... not down- or uploading but not stopped',
            needed_keys=('stalled',)),
        'isolated': BoolFilterSpec(
            lambda t: t['isolated'],
            description='... cannot discover new peers in any way',
            needed_keys=('isolated',)),
        'leeching': BoolFilterSpec(
            lambda t: t['status'] == 'leeching',
            description='... downloading or waiting for seeds',
            needed_keys=('status',)),
        'private': BoolFilterSpec(
            lambda t: t['private'],
            description='... only connectable through trackers',
            needed_keys=('private',)),
        'public': BoolFilterSpec(
            lambda t: not t['private'],
            description='... connectable through DHT and/or PEX',
            needed_keys=('private',)),
        'seeding': BoolFilterSpec(
            lambda t: t['status'] == 'seeding',
            description='... complete and offered for download',
            needed_keys=('status',)),
        'stopped': BoolFilterSpec(
            lambda t: t['status'] == 'stopped',
            description='... not allowed to up- or download',
            needed_keys=('status',),
            aliases=('paused',)),
        'uploading': BoolFilterSpec(
            lambda t: t['rate-up'] > 0,
            description='... using upload bandwidth',
            needed_keys=('rate-up',)),
        'verifying': BoolFilterSpec(
            lambda t: t['status'] == 'verifying',
            description='... being verified or queued for verification',
            needed_keys=('status',),
            aliases=('checking',)),
    }


    # Filters with arguments
    COMPARATIVE_FILTERS = {
        'connections': _make_cmp_filter('peers-connected', ('conn',),
                                        '::: number of connected peers'),
        '%downloaded': _make_cmp_filter('%downloaded', ('%done', '%complete'),
                                        '::: percentage of downloaded bytes'),
        'downloaded': _make_cmp_filter('size-downloaded', ('down',),
                                       '::: number of downloaded bytes'),
        'id':        _make_cmp_filter('id', (), '::: ID'),
        'name':      _make_cmp_filter('name', ('title',), '::: name'),
        'path':      _make_cmp_filter('path', ('dir',), '::: full path to download directory'),
        'ratio':     _make_cmp_filter('ratio', (), '::: uploaded/downloaded ratio'),
        'rate-down': _make_cmp_filter('rate-down', ('rdown',), '::: download rate'),
        'rate-up':   _make_cmp_filter('rate-up', ('rup',), '::: upload rate'),
        'seeds':     _make_cmp_filter('peers-seeding', (),
                                      '::: largest number of seeds reported by any tracker'),
        'size':      _make_cmp_filter('size-final', (),
                                      '::: combined size of all wanted files'),
        'uploaded':  _make_cmp_filter('size-uploaded', (),
                                      '::: number of uploaded bytes'),

        'tracker': CmpFilterSpec(
            lambda t, op, v: any(op(tracker['url-announce'].domain, v)
                                 for tracker in t['trackers']),
            description='::: domain of the announce URL of trackers',
            needed_keys=('trackers',),
            value_type=str,
        ),
    }



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
                        if f == _TorrentFilter('all'):
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
