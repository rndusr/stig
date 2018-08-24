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

from . import (BoolFilterSpec, CmpFilterSpec, make_cmp_filter, Filter, FilterChain)
from . import (timestamp_or_timedelta, time_filter, limit_rate_filter)
from ..utils import (Bandwidth, BoolOrBandwidth, convert)


from ..ttypes import TYPES as VALUETYPES
def _make_cmp_filter(*args, **kwargs):
    return make_cmp_filter(VALUETYPES, *args, **kwargs)

def _desc(text):
    if text.startswith('...'):
        text = 'Match VALUE against ' + text[4:]
    return text


from ..ttypes import Status
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
            aliases=('*',),
            description='All torrents',
            needed_keys=()),
        'complete': BoolFilterSpec(
            lambda t: t['%downloaded'] >= 100,
            aliases=('cmp',),
            description='Torrents with all wanted files downloaded',
            needed_keys=('%downloaded',)),
        'incomplete': BoolFilterSpec(
            lambda t: t['%downloaded'] < 100,
            aliases=('inc',),
            description='Torrents with some wanted files not fully downloaded',
            needed_keys=('%downloaded',)),
        'stopped': BoolFilterSpec(
            lambda t: _STATUS_STOPPED in t['status'],
            aliases=('stp',),
            description='Torrents not allowed to up- or download',
            needed_keys=('status',)),
        'active': BoolFilterSpec(
            lambda t: t['peers-connected'] > 0 or _STATUS_VERIFY in t['status'],
            description='Torrents connected to peers or being verified',
            needed_keys=('peers-connected', 'status')),
        'uploading': BoolFilterSpec(
            lambda t: t['rate-up'] > 0,
            aliases=('upg',),
            description='Torrents using upload bandwidth',
            needed_keys=('rate-up',)),
        'downloading': BoolFilterSpec(
            lambda t: t['rate-down'] > 0,
            aliases=('dng',),
            description='Torrents using download bandwidth',
            needed_keys=('rate-down',)),
        'verifying': BoolFilterSpec(
            lambda t: _STATUS_VERIFY in t['status'],
            aliases=('vfg',),
            description='Torrents being verified or queued for verification',
            needed_keys=('status',)),
        'leeching': BoolFilterSpec(
            lambda t: t['%downloaded'] < 100 and _STATUS_STOPPED not in t['status'],
            aliases=('lcg',),
            description='Unstopped torrents downloading or waiting for seeds',
            needed_keys=('%downloaded', 'status')),
        'seeding': BoolFilterSpec(
            lambda t: t['%downloaded'] >= 100 and _STATUS_STOPPED not in t['status'],
            aliases=('sdg',),
            description='Unstopped torrents with all wanted files downloaded',
            needed_keys=('%downloaded', 'status')),
        'idle': BoolFilterSpec(
            lambda t: (_STATUS_IDLE in t['status'] and
                       _STATUS_STOPPED not in t['status']),
            description='Unstopped torrents not using any bandwidth',
            needed_keys=('status',)),
        'isolated': BoolFilterSpec(
            lambda t: _STATUS_ISOLATED in t['status'],
            aliases=('isl',),
            description='Torrents that cannot discover new peers in any way',
            needed_keys=('status',)),
        'private': BoolFilterSpec(
            lambda t: t['private'],
            aliases=('prv',),
            description='Torrents connectable through trackers only',
            needed_keys=('private',)),
        'public': BoolFilterSpec(
            lambda t: not t['private'],
            aliases=('pbl',),
            description='Torrents connectable through DHT and/or PEX',
            needed_keys=('private',)),
    }

    # Filters with arguments
    COMPARATIVE_FILTERS = {
        'id'              : _make_cmp_filter('id',
                                             _desc('... ID')),
        'name'            : _make_cmp_filter('name',
                                             _desc('... name'),
                                             aliases=('n',)),
        'comment'         : _make_cmp_filter('comment',
                                             _desc('... comment'),
                                             aliases=('cmnt',)),
        'path'            : _make_cmp_filter('path',
                                             _desc('... full path to download directory'),
                                             aliases=('dir',)),
        'error'           : _make_cmp_filter('error',
                                             _desc('... error message'),
                                             aliases=('err',)),
        'uploaded'        : _make_cmp_filter('size-uploaded',
                                             _desc('... number of uploaded bytes'),
                                             aliases=('up',)),
        'downloaded'      : _make_cmp_filter('size-downloaded',
                                             _desc('... number of downloaded bytes'),
                                             aliases=('dn',)),
        '%downloaded'     : _make_cmp_filter('%downloaded',
                                             _desc('... percentage of downloaded bytes'),
                                             aliases=('%dn',)),
        'size'            : _make_cmp_filter('size-final',
                                             _desc('... combined size of all wanted files'),
                                             aliases=('sz',),
                                             value_convert=convert.size),
        'peers'           : _make_cmp_filter('peers-connected',
                                             _desc('... number of connected peers'),
                                             aliases=('prs',)),
        'seeds'           : _make_cmp_filter('peers-seeding',
                                             _desc('... largest number of seeds reported by any tracker'),
                                             aliases=('sds',)),
        'ratio'           : _make_cmp_filter('ratio',
                                             _desc('... uploaded/downloaded ratio'),
                                             aliases=('rto',)),
        'rate-up'         : _make_cmp_filter('rate-up',
                                             _desc('... upload rate'),
                                             aliases=('rup',),
                                             value_convert=Bandwidth),
        'rate-down'       : _make_cmp_filter('rate-down',
                                             _desc('... download rate'),
                                             aliases=('rdn',),
                                             value_convert=Bandwidth),

        'limit-rate-up': CmpFilterSpec(
            lambda t, op, v: limit_rate_filter(t['limit-rate-up'], op, v),
            aliases=('lrup',),
            description=_desc('... upload rate limit'),
            needed_keys=('limit-rate-up',),
            value_type=BoolOrBandwidth,
        ),

        'limit-rate-down': CmpFilterSpec(
            lambda t, op, v: limit_rate_filter(t['limit-rate-down'], op, v),
            aliases=('lrdn',),
            description=_desc('... download rate limit'),
            needed_keys=('limit-rate-down',),
            value_type=BoolOrBandwidth,
        ),

        'tracker': CmpFilterSpec(
            lambda t, op, v: any(op(tracker['url-announce'].domain, v)
                                 for tracker in t['trackers']),
            aliases=('trk',),
            description=_desc('... domain of the announce URL of trackers'),
            needed_keys=('trackers',),
            value_type=str,
        ),

        'eta': CmpFilterSpec(
            lambda t, op, v: time_filter(t['timespan-eta'], op, v),
            description=_desc('... estimated time for torrent to finish'),
            needed_keys=('timespan-eta',),
            value_type=VALUETYPES['timespan-eta'],
            value_convert=timestamp_or_timedelta,
        ),

        'created': CmpFilterSpec(
            lambda t, op, v: time_filter(t['time-created'], op, v),
            aliases=('tcrt',),
            description=_desc('... time torrent was created'),
            needed_keys=('time-created',),
            value_type=VALUETYPES['time-created'],
            value_convert=lambda v: timestamp_or_timedelta(v, default_sign=-1),
        ),
        'added': CmpFilterSpec(
            lambda t, op, v: time_filter(t['time-added'], op, v),
            aliases=('tadd',),
            description=_desc('... time torrent was added'),
            needed_keys=('time-added',),
            value_type=VALUETYPES['time-added'],
            value_convert=lambda v: timestamp_or_timedelta(v, default_sign=-1),
        ),
        'started': CmpFilterSpec(
            lambda t, op, v: time_filter(t['time-started'], op, v),
            aliases=('tsta',),
            description=_desc('... last time torrent was started'),
            needed_keys=('time-started',),
            value_type=VALUETYPES['time-started'],
            value_convert=lambda v: timestamp_or_timedelta(v, default_sign=-1),
        ),
        'activity': CmpFilterSpec(
            lambda t, op, v: time_filter(t['time-activity'], op, v),
            aliases=('tact',),
            description=_desc('... last time torrent was active'),
            needed_keys=('time-activity',),
            value_type=VALUETYPES['time-activity'],
            value_convert=lambda v: timestamp_or_timedelta(v, default_sign=-1),
        ),
        'completed': CmpFilterSpec(
            lambda t, op, v: time_filter(t['time-completed'], op, v),
            aliases=('tcmp',),
            description=_desc('... time all wanted files where downloaded'),
            needed_keys=('time-completed',),
            value_type=VALUETYPES['time-completed'],
            value_convert=lambda v: timestamp_or_timedelta(v, default_sign=-1),
        ),
    }


class TorrentFilter(FilterChain):
    """One or more filters combined with & and | operators"""
    filterclass = SingleTorrentFilter
