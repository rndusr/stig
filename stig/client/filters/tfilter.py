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

from ...logging import make_logger
log = make_logger(__name__)

import re

from . import (BoolFilterSpec, CmpFilterSpec, Filter, FilterChain)

from ..tkeys import TYPES as VALUETYPES
def _make_cmp_filter(key, aliases, description):
    filterfunc = lambda t, op, v, key=key: op(t[key], v)
    return CmpFilterSpec(filterfunc,
                         description=_make_filter_desc(description),
                         needed_keys=(key,), aliases=aliases,
                         value_type=VALUETYPES[key])

def _make_filter_desc(text):
    if text.startswith('...'):
        text = 'Match VALUE against ' + text[4:]
    return text



class SingleTorrentFilter(Filter):
    DEFAULT_FILTER = 'name'

    # Filters without arguments
    BOOLEAN_FILTERS = {
        # '...' is replaced with 'Torrents that are'
        'active': BoolFilterSpec(
            lambda t: t['peers-connected'] > 0 or t['status'] == 'verifying',
            description='Torrents connected to peers or being verified',
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
            description='Torrents using download bandwidth',
            needed_keys=('rate-down',)),
        'idle': BoolFilterSpec(
            lambda t: t['stalled'],
            description='Torrents not down- or uploading but not stopped',
            needed_keys=('stalled',)),
        'isolated': BoolFilterSpec(
            lambda t: t['isolated'],
            description='Torrents that cannot discover new peers in any way',
            needed_keys=('isolated',)),
        'leeching': BoolFilterSpec(
            lambda t: t['status'] == 'leeching',
            description='Torrents downloading or waiting for seeds',
            needed_keys=('status',)),
        'private': BoolFilterSpec(
            lambda t: t['private'],
            description='Torrents that are only connectable through trackers',
            needed_keys=('private',)),
        'public': BoolFilterSpec(
            lambda t: not t['private'],
            description='Torrents connectable through DHT and/or PEX',
            needed_keys=('private',)),
        'seeding': BoolFilterSpec(
            lambda t: t['status'] == 'seeding',
            description='Torrents that are complete and shared on request',
            needed_keys=('status',)),
        'stopped': BoolFilterSpec(
            lambda t: t['status'] == 'stopped',
            description='Torrents not allowed to up- or download',
            needed_keys=('status',),
            aliases=('paused',)),
        'uploading': BoolFilterSpec(
            lambda t: t['rate-up'] > 0,
            description='Torrents using upload bandwidth',
            needed_keys=('rate-up',)),
        'verifying': BoolFilterSpec(
            lambda t: t['status'] == 'verifying',
            description='Torrents being verified or queued for verification',
            needed_keys=('status',),
            aliases=('checking',)),
    }


    # Filters with arguments
    COMPARATIVE_FILTERS = {
        'connections': _make_cmp_filter('peers-connected', ('conn',),
                                        '... number of connected peers'),
        '%downloaded': _make_cmp_filter('%downloaded', ('%down',),
                                        '... percentage of downloaded bytes'),
        'downloaded': _make_cmp_filter('size-downloaded', ('down',),
                                       '... number of downloaded bytes'),
        'id':        _make_cmp_filter('id', (), '... ID'),
        'name':      _make_cmp_filter('name', ('title',), '... name'),
        'path':      _make_cmp_filter('path', ('dir',), '... full path to download directory'),
        'ratio':     _make_cmp_filter('ratio', (), '... uploaded/downloaded ratio'),
        'rate-down': _make_cmp_filter('rate-down', ('rdown',), '... download rate'),
        'rate-up':   _make_cmp_filter('rate-up', ('rup',), '... upload rate'),
        'seeds':     _make_cmp_filter('peers-seeding', (),
                                      '... largest number of seeds reported by any tracker'),
        'size':      _make_cmp_filter('size-final', (),
                                      '... combined size of all wanted files'),
        'uploaded':  _make_cmp_filter('size-uploaded', (),
                                      '... number of uploaded bytes'),

        'tracker': CmpFilterSpec(
            lambda t, op, v: any(op(tracker['url-announce'].domain, v)
                                 for tracker in t['trackers']),
            description=_make_filter_desc('... domain of the announce URL of trackers'),
            needed_keys=('trackers',),
            value_type=str,
        ),
    }



class TorrentFilter(FilterChain):
    """One or more filters combined with & and | operators"""
    filterclass = SingleTorrentFilter
