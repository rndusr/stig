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

from ..base import TorrentBase
from ..utils import Bandwidth, BoolOrBandwidth, Status, convert
from .base import BoolFilterSpec, CmpFilterSpec, Filter, FilterChain, FilterSpecDict
from .utils import cmp_timestamp_or_timdelta, limit_rate_filter, timestamp_or_timedelta


def _desc(text):
    if text.startswith('...'):
        text = 'Match VALUE against ' + text[4:]
    return text


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


class _SingleFilter(Filter):
    DEFAULT_FILTER = 'name'

    BOOLEAN_FILTERS = FilterSpecDict({
        'all'         : BoolFilterSpec(None,
                                       aliases=('*',),
                                       description='All torrents'),
        'complete'    : BoolFilterSpec(lambda t: t['%downloaded'] >= 100,
                                       needed_keys=('%downloaded',),
                                       aliases=('cmp',),
                                       description='Torrents with all wanted files downloaded'),
        'stopped'     : BoolFilterSpec(lambda t: _STATUS_STOPPED in t['status'],
                                       needed_keys=('status',),
                                       aliases=('stp', 'paused'),
                                       description='Torrents that are not allowed to up- or download'),
        'active'      : BoolFilterSpec(lambda t: _STATUS_CONNECTED in t['status'] or _STATUS_VERIFY in t['status'],
                                       needed_keys=('peers-connected', 'status'),
                                       aliases=('act',),
                                       description='Torrents connected to peers or being verified'),
        'uploading'   : BoolFilterSpec(lambda t: t['rate-up'] > 0,
                                       needed_keys=('rate-up',),
                                       aliases=('upg',),
                                       description='Torrents using upload bandwidth'),
        'downloading' : BoolFilterSpec(lambda t: t['rate-down'] > 0,
                                       needed_keys=('rate-down',),
                                       aliases=('dng',),
                                       description='Torrents using download bandwidth'),
        'leeching'    : BoolFilterSpec(lambda t: t['%downloaded'] < 100 and _STATUS_STOPPED not in t['status'],
                                       needed_keys=('%downloaded', 'status'),
                                       aliases=('lcg',),
                                       description='Unstopped torrents downloading or waiting for seeds'),
        'seeding'     : BoolFilterSpec(lambda t: t['%downloaded'] >= 100 and _STATUS_STOPPED not in t['status'],
                                       needed_keys=('%downloaded', 'status'),
                                       aliases=('sdg',),
                                       description='Unstopped torrents with all wanted files downloaded'),
        'verifying'   : BoolFilterSpec(lambda t: _STATUS_VERIFY in t['status'],
                                       needed_keys=('status',),
                                       aliases=('vfg',),
                                       description='Torrents being verified or queued for verification'),
        'idle'        : BoolFilterSpec(lambda t: (_STATUS_IDLE in t['status'] and
                                                  _STATUS_STOPPED not in t['status']),
                                       needed_keys=('status',),
                                       description="Unstopped torrents that don't do anything"),
        'isolated'    : BoolFilterSpec(lambda t: _STATUS_ISOLATED in t['status'],
                                       needed_keys=('status',),
                                       aliases=('isl',),
                                       description='Torrents that cannot discover new peers in any way'),
        'private'     : BoolFilterSpec(lambda t: t['private'],
                                       needed_keys=('private',),
                                       aliases=('prv',),
                                       description='Torrents connectable through trackers only (no DHT/PEX)'),
    })

    COMPARATIVE_FILTERS = FilterSpecDict({
        'id'              : CmpFilterSpec(value_getter=lambda t: t['id'],
                                          value_type=TorrentBase.TYPES['id'],
                                          needed_keys=('id',),
                                          description=_desc('... torrent ID')),

        'hash'            : CmpFilterSpec(value_getter=lambda t: t['hash'],
                                          value_type=TorrentBase.TYPES['hash'],
                                          needed_keys=('hash',),
                                          description=_desc('... torrent SHA1 hash')),

        'name'            : CmpFilterSpec(value_getter=lambda t: t['name'],
                                          value_type=TorrentBase.TYPES['name'],
                                          needed_keys=('name',),
                                          aliases=('n',),
                                          description=_desc('... name')),

        'comment'         : CmpFilterSpec(value_getter=lambda t: t['comment'],
                                          value_type=TorrentBase.TYPES['comment'],
                                          needed_keys=('comment',),
                                          aliases=('cmnt',),
                                          description=_desc('... comment')),

        'path'            : CmpFilterSpec(value_getter=lambda t: t['path'],
                                          value_type=TorrentBase.TYPES['path'],
                                          needed_keys=('path',),
                                          description=_desc('... absolute path to download directory')),

        'error'           : CmpFilterSpec(value_getter=lambda t: t['error'],
                                          value_type=TorrentBase.TYPES['error'],
                                          needed_keys=('error',),
                                          aliases=('err',),
                                          description=_desc('... error message')),

        'uploaded'        : CmpFilterSpec(value_getter=lambda t: t['size-uploaded'],
                                          value_type=TorrentBase.TYPES['size-uploaded'],
                                          needed_keys=('size-uploaded',),
                                          aliases=('up',),
                                          description=_desc('... number of uploaded bytes')),

        'downloaded'      : CmpFilterSpec(value_getter=lambda t: t['size-downloaded'],
                                          value_type=TorrentBase.TYPES['size-downloaded'],
                                          needed_keys=('size-downloaded',),
                                          aliases=('dn',),
                                          description=_desc('... number of downloaded bytes')),

        '%downloaded'     : CmpFilterSpec(value_getter=lambda t: t['%downloaded'],
                                          value_type=TorrentBase.TYPES['%downloaded'],
                                          needed_keys=('%downloaded',),
                                          aliases=('%dn',),
                                          description=_desc('... percentage of downloaded bytes')),

        'size'            : CmpFilterSpec(value_getter=lambda t: t['size-final'],
                                          value_type=TorrentBase.TYPES['size-final'],
                                          value_convert=convert.size,
                                          needed_keys=('size-final',),
                                          aliases=('sz',),
                                          description=_desc('... combined size of all wanted files')),

        'peers'           : CmpFilterSpec(value_getter=lambda t: t['peers-connected'],
                                          value_type=TorrentBase.TYPES['peers-connected'],
                                          needed_keys=('peers-connected',),
                                          aliases=('prs',),
                                          description=_desc('... number of connected peers')),

        'seeds'           : CmpFilterSpec(value_getter=lambda t: t['peers-seeding'],
                                          value_type=TorrentBase.TYPES['peers-seeding'],
                                          needed_keys=('peers-seeding',),
                                          aliases=('sds',),
                                          description=_desc('... largest number of seeds reported by any tracker')),

        'ratio'           : CmpFilterSpec(value_getter=lambda t: t['ratio'],
                                          value_type=TorrentBase.TYPES['ratio'],
                                          needed_keys=('ratio',),
                                          aliases=('rto',),
                                          description=_desc('... uploaded/downloaded ratio')),

        'rate-up'         : CmpFilterSpec(value_getter=lambda t: t['rate-up'],
                                          value_type=TorrentBase.TYPES['rate-up'],
                                          value_convert=Bandwidth,
                                          needed_keys=('rate-up',),
                                          aliases=('rup',),
                                          description=_desc('... upload rate')),

        'rate-down'       : CmpFilterSpec(value_getter=lambda t: t['rate-down'],
                                          value_type=TorrentBase.TYPES['rate-down'],
                                          value_convert=Bandwidth,
                                          needed_keys=('rate-down',),
                                          aliases=('rdn',),
                                          description=_desc('... download rate')),

        'limit-rate-up'   : CmpFilterSpec(value_getter=lambda t: t['limit-rate-up'],
                                          value_matcher=lambda t, op, v: limit_rate_filter(t['limit-rate-up'], op, v),
                                          value_type=BoolOrBandwidth,
                                          as_bool=lambda t: t['limit-rate-up'] < float('inf'),
                                          needed_keys=('limit-rate-up',),
                                          aliases=('lrup',),
                                          description=_desc('... upload rate limit')),

        'limit-rate-down' : CmpFilterSpec(value_getter=lambda t: t['limit-rate-down'],
                                          value_matcher=lambda t, op, v: limit_rate_filter(t['limit-rate-down'], op, v),
                                          value_type=BoolOrBandwidth,
                                          as_bool=lambda t: t['limit-rate-down'] < float('inf'),
                                          needed_keys=('limit-rate-down',),
                                          aliases=('lrdn',),
                                          description=_desc('... download rate limit')),

        'tracker'         : CmpFilterSpec(value_getter=lambda t: (tracker['url-announce'].domain for tracker in t['trackers']),
                                          value_matcher=lambda t, op, v: any(op(tracker['url-announce'].domain, v)
                                                                             for tracker in t['trackers']),
                                          value_type=str,
                                          needed_keys=('trackers',),
                                          aliases=('trk',),
                                          description=_desc('... domain of the announce URL of trackers')),

        'eta'             : CmpFilterSpec(value_getter=lambda t: t['timespan-eta'],
                                          value_matcher=lambda t, op, v: cmp_timestamp_or_timdelta(t['timespan-eta'], op, v),
                                          value_type=TorrentBase.TYPES['timespan-eta'],
                                          value_convert=timestamp_or_timedelta,
                                          needed_keys=('timespan-eta',),
                                          description=_desc('... estimated time to finish downloading')),

        'created'         : CmpFilterSpec(value_getter=lambda t: t['time-created'],
                                          value_matcher=lambda t, op, v: cmp_timestamp_or_timdelta(t['time-created'], op, v),
                                          value_type=TorrentBase.TYPES['time-created'],
                                          value_convert=lambda v: timestamp_or_timedelta(v, default_sign=-1),
                                          needed_keys=('time-created',),
                                          aliases=('tcrt',),
                                          description=_desc('... torrent creation time')),

        'added'           : CmpFilterSpec(value_getter=lambda t: t['time-added'],
                                          value_matcher=lambda t, op, v: cmp_timestamp_or_timdelta(t['time-added'], op, v),
                                          value_type=TorrentBase.TYPES['time-added'],
                                          value_convert=lambda v: timestamp_or_timedelta(v, default_sign=-1),
                                          needed_keys=('time-added',),
                                          aliases=('tadd',),
                                          description=_desc('... time torrent was added')),

        'started'         : CmpFilterSpec(value_getter=lambda t: t['time-started'],
                                          value_matcher=lambda t, op, v: cmp_timestamp_or_timdelta(t['time-started'], op, v),
                                          value_type=TorrentBase.TYPES['time-started'],
                                          value_convert=lambda v: timestamp_or_timedelta(v, default_sign=-1),
                                          needed_keys=('time-started',),
                                          aliases=('tsta',),
                                          description=_desc('... last time torrent was started')),

        'activity'        : CmpFilterSpec(value_getter=lambda t: t['time-activity'],
                                          value_matcher=lambda t, op, v: cmp_timestamp_or_timdelta(t['time-activity'], op, v),
                                          value_type=TorrentBase.TYPES['time-activity'],
                                          value_convert=lambda v: timestamp_or_timedelta(v, default_sign=-1),
                                          needed_keys=('time-activity',),
                                          aliases=('tact',),
                                          description=_desc('... time torrent was active')),

        'completed'       : CmpFilterSpec(value_getter=lambda t: t['time-completed'],
                                          value_matcher=lambda t, op, v: cmp_timestamp_or_timdelta(t['time-completed'], op, v),
                                          value_type=TorrentBase.TYPES['time-completed'],
                                          value_convert=lambda v: timestamp_or_timedelta(v, default_sign=-1),
                                          needed_keys=('time-completed',),
                                          aliases=('tcmp',),
                                          description=_desc('... time all wanted files where/will be downloaded')),
    })


class TorrentFilter(FilterChain):
    """One or more filters combined with & and | operators"""
    filterclass = _SingleFilter
