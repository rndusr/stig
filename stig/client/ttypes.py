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

"""More complex types for torrent data, e.g. lists of peers or a file tree"""

import os
import time
from collections import abc, defaultdict, deque

from . import utils
from .base import TorrentBase  # noqa: F401

from ..logging import make_logger  # isort:skip
log = make_logger(__name__)


class TorrentFilePriority(str):
    _MAP = {-2: (-2, 'off'), -1: (-1, 'low'), 0: (0, 'normal'), 1: (1, 'high'),
            'off': (-2, 'off'), 'low': (-1, 'low'), 'normal': (0, 'normal'), 'high': (1, 'high')}
    valid_values = ('off', 'low', 'normal', 'high')

    def __new__(cls, prio):
        try:
            number, string = cls._MAP[prio]
        except KeyError:
            raise ValueError('Invalid %s value: %r' % (cls.__name__, prio))
        else:
            obj = super().__new__(cls, string)
            obj.as_int = number
            return obj

    def __eq__(self, other):
        o_int, o_str = self._MAP.get(other, (None, None))
        if isinstance(other, int) and o_int == self.as_int:
            return True
        elif isinstance(other, str) and o_str == str(self):
            return True
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        return self.as_int < int(other)

    def __gt__(self, other):
        return self.as_int > int(other)

    def __le__(self, other):
        return self.as_int <= int(other)

    def __ge__(self, other):
        return self.as_int >= int(other)

    def __int__(self):
        return self.as_int

    def __repr__(self):
        return '%s(%r)' % (type(self).__name__, str(self))

    def __hash__(self):
        return super().__hash__()

def _calc_percent(a, b):
    try:
        return a / b * 100
    except ZeroDivisionError:
        return 0

class TorrentFile(abc.Mapping):
    """Mapping that holds the values of a single file in a torrent"""

    # Distinguish subtrees from files without comparing classes everywhere
    nodetype = 'leaf'

    TYPES = {
        'id'              : None,
        'tid'             : None,
        'name'            : utils.SmartCmpStr,
        'path-absolute'   : utils.SmartCmpPath,
        'path-relative'   : utils.SmartCmpPath,
        'location'        : utils.SmartCmpPath,
        'size-total'      : utils.SizeInBytes,
        'size-downloaded' : utils.SizeInBytes,
        'is-wanted'       : bool,
        'priority'        : TorrentFilePriority,
        '%downloaded'     : utils.Percent,
    }

    _MODIFIERS = {
        'id'              : lambda raw: raw['id'],
        'tid'             : lambda raw: raw['tid'],
        'name'            : lambda raw: raw['name'],
        'path-absolute'   : lambda raw: os.path.join(raw['location'], raw['path'], raw['name']),
        'path-relative'   : lambda raw: os.path.join(raw['path'], raw['name']),
        'location'        : lambda raw: raw['location'],
        'size-total'      : lambda raw: raw['size-total'],
        'size-downloaded' : lambda raw: raw['size-downloaded'],
        'is-wanted'       : lambda raw: raw['is-wanted'],
        'priority'        : lambda raw: 'off' if not raw['is-wanted'] else raw['priority'],
        '%downloaded'     : lambda raw: _calc_percent(raw['size-downloaded'], raw['size-total']),
    }

    def __init__(self, tid, id, name, path, location, size_total, size_downloaded, is_wanted, priority):
        self._raw = {'tid': tid, 'id': id, 'name': name, 'path': path, 'location': location,
                     'is-wanted': is_wanted, 'priority': priority,
                     'size-total': size_total, 'size-downloaded': size_downloaded}
        self._cache = {}

    def __getitem__(self, key):
        if key not in self._cache:
            val = self._MODIFIERS[key](self._raw)
            typ = self.TYPES.get(key)
            if typ is not None:
                self._cache[key] = typ(val)
            else:
                self._cache[key] = val
        return self._cache[key]

    def update(self, raw):
        self._raw.update(raw)
        cache = self._cache
        for key,new_value in raw.items():
            cached_value = cache.get(key)
            if cached_value is not None and cached_value != new_value:
                del cache[key]

        # %downloaded is never in raw because it is calculated from
        # size-downloaded and size-total
        if 'size-downloaded' in raw:
            try:
                del cache['%downloaded']
            except KeyError:
                pass

    def __repr__(self):
        return '<{} {!r}>'.format(type(self).__name__, self['name'])

    def __iter__(self):
        return iter(self.TYPES)

    def __len__(self):
        return len(self.TYPES)


class TorrentPeer(abc.Mapping):
    TYPES = {
        'id'          : None,
        'tid'         : None,
        'tname'       : utils.SmartCmpStr,
        'tsize'       : utils.SizeInBytes,
        'ip'          : str,
        'port'        : int,
        'client'      : utils.SmartCmpStr,
        'downloaded'  : utils.SizeInBytes,
        '%downloaded' : utils.Percent,
        'rate-up'     : utils.BandwidthInBytes,
        'rate-down'   : utils.BandwidthInBytes,
        'eta'         : utils.Timedelta,
        'rate-est'    : utils.BandwidthInBytes,
    }

    _MODIFIERS = {
        'id'      : lambda p: (p['tid'], p['ip'], p['port']),
    }

    _MAX_PEER_PROGRESS_SAMPLE_AGE = 1800  # 30 minutes
    _PEER_PROGRESS_DATA = defaultdict(lambda: deque(maxlen=10))

    @classmethod
    def gc_peer_progress_data(cls):
        log.debug('Pruning peer progress data:')
        for peer_id,samples in tuple(cls._PEER_PROGRESS_DATA.items()):
            # Remove samples that are too old
            while samples and (samples[0][0] + cls._MAX_PEER_PROGRESS_SAMPLE_AGE) < time.monotonic():
                log.debug('Sample from %s is too old: %r', peer_id, samples[0])
                samples.popleft()

            # Remove samples where progress is 0.0.  A lot of the cache entries just have
            # a single sample from peers connecting for some reason but not downloading.
            if samples and samples[0][1] in (0.0, 1.0):
                samples.popleft()

            # Remove deque if there are no samples left
            if not samples:
                del cls._PEER_PROGRESS_DATA[peer_id]

        log.debug('Pruned peer progress data:')
        for peer_id,samples in tuple(cls._PEER_PROGRESS_DATA.items()):
            log.debug('%s: %s', peer_id, samples)

    @classmethod
    def _guess_peer_rate_and_eta(cls, peer_id, peer_progress, torrent_size):
        rate = 0
        if peer_progress >= 1:
            # Peer has already downloaded everything
            eta = utils.Timedelta.NOT_APPLICABLE
        else:
            eta = utils.Timedelta.UNKNOWN
            samples = cls._PEER_PROGRESS_DATA[peer_id]

            # Don't add the same progress twice
            if not samples or peer_progress != samples[-1][1]:
                samples.append((time.monotonic(), peer_progress))

            # We need at least 3 samples
            if len(samples) >= 3:
                # Use second and last sample to calculate rate.  The first sample is
                # ignored because its timestamp may be inaccurate: When we add the
                # first sample, the peer's progress is not current but the latest we
                # received, which happened likely tens of seconds ago.
                t_first, p_first = samples[1]
                t_last, p_last = samples[-1]
                p_diff = p_last - p_first
                t_diff = t_last - t_first

                # It's possible progress goes down, e.g. if a peer deletes a file
                if p_diff > 0:
                    torrent_size = int(torrent_size)  # Don't copy unit + unit prefix from torrent_size
                    size_diff = torrent_size * p_diff
                    rate = size_diff / t_diff
                    size_remaining = torrent_size - (torrent_size * peer_progress)
                    eta = size_remaining / rate

        return rate, eta

    def __init__(self, tid, tname, tsize, ip, port, client, downloaded, pdownloaded, rate_up, rate_down):
        self._cache = {}
        self._dct = {'tid': tid, 'tname': tname, 'tsize': tsize,
                     'ip': ip, 'port': port, 'client': client,
                     'downloaded': downloaded, '%downloaded': pdownloaded,
                     'rate-up': rate_up, 'rate-down': rate_down}
        self._dct['rate-est'], self._dct['eta'] = \
            self._guess_peer_rate_and_eta(self['id'], pdownloaded / 100, tsize)

    def __getitem__(self, key):
        cache = self._cache
        value = cache.get(key)
        if value is None:
            modifier = self._MODIFIERS.get(key)
            if modifier is not None:
                val = modifier(self._dct)
            else:
                val = self._dct[key]
            typ = self.TYPES.get(key)
            if typ is not None:
                cache[key] = typ(val)
            else:
                cache[key] = val
        return cache[key]

    def clearcache(self):
        self._cache.clear()

    def __repr__(self):
        return '<{} #{}, {}>'.format(type(self).__name__, self['tid'], self['ip'])

    def __iter__(self):
        return iter(self.TYPES)

    def __len__(self):
        return len(self.TYPES)


class TrackerStatus(utils.SmartCmpStr):
    def __new__(cls, status):
        if status not in ('stopped', 'idle', 'queued', 'announcing', 'scraping'):
            raise ValueError('Invalid tracker status: %r' % status)
        else:
            return super().__new__(cls, status)

class TorrentTracker(abc.Mapping):
    TYPES = {
        'id'                 : None,
        'tid'                : int,
        'tname'              : utils.SmartCmpStr,
        'tier'               : int,

        'url-announce'       : utils.URL,
        'url-scrape'         : utils.URL,
        'domain'             : utils.SmartCmpStr,

        'status-announce'    : TrackerStatus,
        'status-scrape'      : TrackerStatus,
        'status'             : TrackerStatus,

        'error-announce'     : utils.SmartCmpStr,
        'error-scrape'       : utils.SmartCmpStr,
        'error'              : utils.SmartCmpStr,

        'count-downloads'    : utils.Count,
        'count-leeches'      : utils.Count,
        'count-seeds'        : utils.Count,

        'time-last-announce' : utils.Timestamp,
        'time-next-announce' : utils.Timestamp,
        'time-last-scrape'   : utils.Timestamp,
        'time-next-scrape'   : utils.Timestamp,
    }

    _MODIFIERS = {
        'id'     : lambda self: hash((self['tid'], self['url-announce'])),
        'domain' : lambda self: self['url-announce'].domain,
        'status' : lambda self: (self['status-scrape'] if self['status-announce'] == 'idle'
                                 else self['status-announce']),
        'error'  : lambda self: ('Announce error: %s' % self['error-announce']
                                 if self['error-announce'] else
                                 'Scrape error: %s' % self['error-scrape']
                                 if self['error-scrape'] else '')
    }

    def __init__(self, trkdict):
        self._dct = trkdict
        self._cache = {}

    def __getitem__(self, key):
        cache = self._cache
        value = cache.get(key)
        if value is None:
            modifier = self._MODIFIERS.get(key)
            if modifier is not None:
                val = modifier(self)
            else:
                val = self._dct[key]
            typ = self.TYPES.get(key)
            if typ is not None:
                cache[key] = typ(val)
            else:
                cache[key] = val
        return cache[key]

    def __repr__(self):
        return '<%s %s>' % (type(self).__name__, self['url-announce'])

    def __iter__(self):
        return iter(self.TYPES)

    def __len__(self):
        return len(self.TYPES)
