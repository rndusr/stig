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

from . import (BoolFilterSpec, CmpFilterSpec, make_cmp_filter,
               Filter, FilterChain)

from ..tkeys import TYPES as VALUETYPES
def _make_cmp_filter(*args, **kwargs):
    return make_cmp_filter(VALUETYPES, *args, **kwargs)

def _desc(text):
    if text.startswith('...'):
        text = 'Match VALUE against ' + text[4:]
    return text


from ..tkeys import Status
_STATUS_VERIFY    = Status.VERIFY
_STATUS_DOWNLOAD  = Status.DOWNLOAD
_STATUS_UPLOAD    = Status.UPLOAD
_STATUS_INIT      = Status.INIT
_STATUS_CONNECTED = Status.CONNECTED
_STATUS_ISOLATED  = Status.ISOLATED
_STATUS_QUEUED    = Status.QUEUED
_STATUS_SEED      = Status.SEED
_STATUS_IDLE      = Status.IDLE
_STATUS_STOPPED   = Status.STOPPED

class SingleTorrentFilter(Filter):
    DEFAULT_FILTER = 'name'

    # Filters without arguments
    BOOLEAN_FILTERS = {
        'all': BoolFilterSpec(
            lambda t: True,
            description='All torrents',
            needed_keys=(),
            aliases=('*',)),

        'leeching': BoolFilterSpec(
            lambda t: t['%downloaded'] < 100 and _STATUS_STOPPED not in t['status'],
            description='unstopped Torrents downloading or waiting for seeds',
            needed_keys=('%downloaded', 'status')),
        'seeding': BoolFilterSpec(
            lambda t: t['%downloaded'] >= 100 and _STATUS_STOPPED not in t['status'],
            description='unstopped Torrents with all wanted files downloaded',
            needed_keys=('%downloaded', 'status')),
        'complete': BoolFilterSpec(
            lambda t: t['%downloaded'] >= 100,
            description='Torrents with all wanted files downloaded',
            needed_keys=('%downloaded',)),
        'incomplete': BoolFilterSpec(
            lambda t: t['%downloaded'] < 100,
            description='Torrents with some wanted files not fully downloaded',
            needed_keys=('%downloaded',)),
        'stopped': BoolFilterSpec(
            lambda t: _STATUS_STOPPED in t['status'],
            description='Torrents not allowed to up- or download',
            needed_keys=('status',),
            aliases=('paused',)),

        'active': BoolFilterSpec(
            lambda t: t['peers-connected'] > 0 or _STATUS_VERIFY in t['status'],
            description='Torrents connected to peers or being verified',
            needed_keys=('peers-connected', 'status')),
        'downloading': BoolFilterSpec(
            lambda t: t['rate-down'] > 0,
            description='Torrents using download bandwidth',
            needed_keys=('rate-down',)),
        'uploading': BoolFilterSpec(
            lambda t: t['rate-up'] > 0,
            description='Torrents using upload bandwidth',
            needed_keys=('rate-up',)),
        'verifying': BoolFilterSpec(
            lambda t: _STATUS_VERIFY in t['status'],
            description='Torrents being verified or queued for verification',
            needed_keys=('status',),
            aliases=('checking',)),
        'idle': BoolFilterSpec(
            lambda t: (_STATUS_IDLE in t['status'] and
                       _STATUS_STOPPED not in t['status']),
            description='unstopped Torrents not using any bandwidth',
            needed_keys=('status',)),
        'isolated': BoolFilterSpec(
            lambda t: _STATUS_ISOLATED in t['status'],
            description='Torrents that cannot discover new peers in any way',
            needed_keys=('status',)),

        'private': BoolFilterSpec(
            lambda t: t['private'],
            description='Torrents connectable through trackers only',
            needed_keys=('private',)),
        'public': BoolFilterSpec(
            lambda t: not t['private'],
            description='Torrents connectable through DHT and/or PEX',
            needed_keys=('private',)),
    }


    # Filters with arguments
    COMPARATIVE_FILTERS = {
        'connections': _make_cmp_filter('peers-connected', _desc('... number of connected peers'),
                                        aliases=('conn',)),
        '%downloaded': _make_cmp_filter('%downloaded', _desc('... percentage of downloaded bytes'),
                                        aliases=('%down',)),
        'downloaded': _make_cmp_filter('size-downloaded', _desc('... number of downloaded bytes'),
                                       aliases=('down',)),
        'id':        _make_cmp_filter('id', _desc('... ID')),
        'name':      _make_cmp_filter('name', _desc('... name'),
                                      aliases=('title',)),
        'path':      _make_cmp_filter('path', _desc('... full path to download directory'),
                                      aliases=('dir',)),
        'ratio':     _make_cmp_filter('ratio', _desc('... uploaded/downloaded ratio')),
        'rate-down': _make_cmp_filter('rate-down', _desc('... download rate'),
                                      aliases=('rdown',)),
        'rate-up':   _make_cmp_filter('rate-up', _desc('... upload rate'),
                                      aliases=('rup',)),
        'seeds':     _make_cmp_filter('peers-seeding',
                                      _desc('... largest number of seeds reported by any tracker')),
        'size':      _make_cmp_filter('size-final', _desc('... combined size of all wanted files')),
        'uploaded':  _make_cmp_filter('size-uploaded',
                                      _desc('... number of uploaded bytes')),

        'tracker': CmpFilterSpec(
            lambda t, op, v: any(op(tracker['url-announce'].domain, v)
                                 for tracker in t['trackers']),
            description=_desc('... domain of the announce URL of trackers'),
            needed_keys=('trackers',),
            value_type=str,
        ),

        'eta': CmpFilterSpec(
            lambda t, op, v: t['timespan-eta'].is_known and op(t['timespan-eta'], v),
            description=_desc('... estimated time for torrent to finish'),
            needed_keys=('timespan-eta',),
            value_type=VALUETYPES['timespan-eta'],
            value_convert=VALUETYPES['timespan-eta'].from_string,
        ),
        'created': CmpFilterSpec(
            lambda t, op, v: t['time-created'].is_known and op(t['time-created'], v),
            description=_desc('... time torrent was created'),
            needed_keys=('time-created',),
            value_type=VALUETYPES['time-created'],
            value_convert=VALUETYPES['time-created'].from_string,
        ),
        'added': CmpFilterSpec(
            lambda t, op, v: t['time-added'].is_known and op(t['time-added'], v),
            description=_desc('... time torrent was added'),
            needed_keys=('time-added',),
            value_type=VALUETYPES['time-added'],
            value_convert=VALUETYPES['time-added'].from_string,
        ),
        'started': CmpFilterSpec(
            lambda t, op, v: t['time-started'].is_known and op(t['time-started'], v),
            description=_desc('... last time torrent was started'),
            needed_keys=('time-started',),
            value_type=VALUETYPES['time-started'],
            value_convert=VALUETYPES['time-started'].from_string,
        ),
        'activity': CmpFilterSpec(
            lambda t, op, v: t['time-activity'].is_known and op(t['time-activity'], v),
            description=_desc('... last time torrent was active'),
            needed_keys=('time-activity',),
            value_type=VALUETYPES['time-activity'],
            value_convert=VALUETYPES['time-activity'].from_string,
        ),
        'completed': CmpFilterSpec(
            lambda t, op, v: t['time-completed'].is_known and op(t['time-completed'], v),
            description=_desc('... time all wanted files where downloaded'),
            needed_keys=('time-completed',),
            value_type=VALUETYPES['time-completed'],
            value_convert=VALUETYPES['time-completed'].from_string,
        ),
    }



class TorrentFilter(FilterChain):
    """One or more filters combined with & and | operators"""
    filterclass = SingleTorrentFilter
