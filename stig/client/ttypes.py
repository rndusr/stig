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

"""Value types used in Torrent classes"""

# The TYPES dictionary at the end of this file maps Torrent key names to
# types.  Every Torrent key must have a type, even if it's just a no-op
# (`lambda obj: obj`).
#
# A type is any callable that converts a single value to the appropriate object.
#
# Types are used to convert values from the server by instantiating them
# normally (e.g. `NumberFloat(1234567)`) and from the user by using the class
# method `from_string` (e.g. `NumberFloat.from_string('1.3GB')`). Not all types
# must provide a `from_string` class method (e.g. 'files').


from ..logging import make_logger
log = make_logger(__name__)

from collections import abc
import os
import re
import time

from . import (NumberFloat, NumberInt)
from . import constants as const
from . import convert
from . import utils


def _rate_limit(limit):
    return const.UNLIMITED if limit is None else convert.bandwidth(limit, unit='byte')


def _calc_percent(a, b):
    try:
        return a / b * 100
    except ZeroDivisionError:
        return 0


class Percent(NumberFloat):
    def __new__(cls, *args, **kwargs):
        kwargs['unit'] = '%'
        return super().__new__(cls, *args, **kwargs)


class Ratio(NumberFloat):
    """A Torrent's upload/download ratio as a float"""
    INFINITE = float('inf')
    NOT_APPLICABLE = -1
    def __str__(self):
        if self == self.INFINITE:
            return '∞'
        elif self == self.NOT_APPLICABLE:
            return ''
        else:
            return super().without_unit


class Count(NumberInt):
    UNKNOWN = -1
    def __str__(self):
        return '?' if self < 0 else super().__str__()


class Status(tuple):
    """A Torrent's status as string"""

    IDLE      = 'idle'
    DOWNLOAD  = 'downloading'
    UPLOAD    = 'uploading'
    CONNECTED = 'connected'
    SEED      = 'seeding'
    STOPPED   = 'stopped'
    QUEUED    = 'queued'
    ISOLATED  = 'isolated'
    VERIFY    = 'verifying'
    INIT      = 'discovering'
    ORDER = (VERIFY, DOWNLOAD, UPLOAD, INIT, CONNECTED,
             ISOLATED, QUEUED, IDLE, STOPPED, SEED)

    def __lt__(self, other):
        return self.ORDER.index(self[0]) < self.ORDER.index(other[0])

    def __le__(self, other):
        return self.ORDER.index(self[0]) <= self.ORDER.index(other[0])

    def __gt__(self, other):
        return self.ORDER.index(self[0]) > self.ORDER.index(other[0])

    def __ge__(self, other):
        return self.ORDER.index(self[0]) >= self.ORDER.index(other[0])



import operator
import unicodedata
class SmartCmpStr(str):
    """String with smart comparison capabilities

    Adds the <, >, <=, >= operators that compare length of strings and makes
    comparison case-insensitive if the other string consists solely of
    lower-case characters.
    """

    def __new__(cls, string):
        # Combine characters with diacritical marks ("a˚" -> "å") so len()
        # reports the correct length.
        # http://www.unicode.org/faq/char_combmark.html
        return super().__new__(cls, unicodedata.normalize('NFC', string))

    def __cmp(self, op, other):
        if not isinstance(other, str):
            return NotImplemented

        # Do case-insensitive comparison?
        # Make copies to avoid infinite recursion.
        o = str(other)
        if o == o.lower():
            s = str(self.lower())
        else:
            s = str(self)

        if op in (operator.__eq__, operator.__ne__, operator.__contains__):
            return op(s, o)
        elif self.isdigit():
            return op(int(s), len(o))
        elif other.isdigit():
            return op(len(s), int(o))
        else:
            return op(s, o)

    def __lt__(self, other): return self.__cmp(operator.lt, other)
    def __le__(self, other): return self.__cmp(operator.le, other)
    def __eq__(self, other): return self.__cmp(operator.eq, other)
    def __ne__(self, other): return self.__cmp(operator.ne, other)
    def __gt__(self, other): return self.__cmp(operator.gt, other)
    def __ge__(self, other): return self.__cmp(operator.ge, other)
    def __contains__(self, other): return self.__cmp(operator.contains, other)

    def __hash__(self):
        return super().__hash__()


class Path(SmartCmpStr):
    def __new__(cls, path):
        return super().__new__(cls, os.path.normpath(path))

    def __repr__(self):
        return '<{} {!r}>'.format(type(self).__name__, str(self))

    def __hash__(self):
        return super().__hash__()



SECONDS = (('y', 31557600),  # 365.25 days
           ('M',  2629800),  # 1 year / 12
           ('w',   605800),  # 7 days
           ('d',    86400),
           ('h',     3600),
           ('m',       60),
           ('s',        1))

class Timedelta(int):
    # To sort unknown and not applicable Timedeltas below the rest, these
    # constants have large values that are very likely never encountered as
    # actual values.
    UNKNOWN        = 1e10
    NOT_APPLICABLE = 1e11

    _FROM_STRING_REGEX = re.compile((r'(\d+(?:\.\d+|)[' +
                                     r''.join(unit for unit,secs in SECONDS) +
                                     r']?)'), flags=re.IGNORECASE)
    @classmethod
    def from_string(cls, string):
        string = string.replace(' ', '')
        if len(string) < 1:
            raise ValueError('Invalid {} value: {!r}'.format(cls.__name__, string))

        secs_total = 0
        for s in cls._FROM_STRING_REGEX.split(string):
            if len(s) < 1:
                continue
            elif not cls._FROM_STRING_REGEX.match(s):
                raise ValueError('Invalid {} value: {!r}'.format(cls.__name__, s))
            elif s[-1].isdigit():
                # No unit specified
                secs_total += float(s)
            else:
                unit, num = s[-1], s[:-1]
                for unit_,secs in SECONDS:
                    if unit == unit_:
                        secs_total += float(num) * secs
                        break

        return cls(secs_total)

    def __str__(self):
        if self == self.UNKNOWN:
            return '?'
        elif self == self.NOT_APPLICABLE:
            return ''
        elif self == 0:
            return 'now'

        abs_secs = abs(self)
        for i,(unit,amount) in enumerate(SECONDS):
            if abs_secs >= amount:
                num = self/amount

                # Small numbers get a sub-unit, for example '1d15h'
                if 1 <= abs_secs/amount < 10 and i < len(SECONDS)-1:
                    subunit, subamount = SECONDS[i+1]
                    if num >= 0:
                        subnum = abs( ((num%1) * amount) / subamount )
                    else:
                        subnum = abs( ((num%-1) * amount) / subamount )

                    if subnum >= 1:
                        return '%d%s%d%s' % (int(num), unit, int(subnum), subunit)

                return '%d%s' % (int(num), unit)

    @property
    def with_preposition(self):
        if self > 0:
            return 'in %s' % self
        elif self < 0:
            return ('%s ago' % self)[1:]  # Remove the first char ('-')
        else:
            return 'now'

    def __bool__(self):
        """Whether delta is known"""
        return self not in (self.UNKNOWN, self.NOT_APPLICABLE)

    @property
    def is_known(self):
        return bool(self)


class Timestamp(int):
    NOW            = -2
    SOON           = -1
    UNKNOWN        = 1e10
    NOT_APPLICABLE = 1e11
    NEVER          = 1e12

    _FORMATS_DATE = (('%Y',       ('tm_year',)),
                     ('%Y-%m',    ('tm_year', 'tm_mon')),
                     ('%Y-%m-%d', ('tm_year', 'tm_mon', 'tm_mday')),
                     ('%d',       ('tm_mday',)),
                     ('%m-%d',    ('tm_mon', 'tm_mday')))
    _FORMATS_TIME = (('%H:%M', ('tm_hour', 'tm_min')),
                     ('%H:%M:%S', ('tm_hour', 'tm_min', 'tm_sec')))

    # Create all combinations of date, time and date+time formats, keeping track
    # of the values they specify
    _FORMATS = []
    for date_frmt,date_given in _FORMATS_DATE:
        _FORMATS.append((date_frmt, date_given))
        for time_frmt,time_given in _FORMATS_TIME:
            _FORMATS.append((time_frmt, time_given))
            given = date_given + time_given
            _FORMATS.append(('%s %s' % (date_frmt, time_frmt), given))
            _FORMATS.append(('%s %s' % (time_frmt, date_frmt), given))

    @classmethod
    def from_string(cls, string):
        string = string.strip().replace('  ', ' ')

        def fill_in_missing_values(t, given):
            # Today with seconds set to 0
            t_now = time.localtime()
            t_now = time.struct_time((t_now.tm_year, t_now.tm_mon, t_now.tm_mday,
                                      t_now.tm_hour, t_now.tm_min, 0,
                                      t_now.tm_wday, t_now.tm_yday, -1))

            # THISYEAR-01-01 00:00:00
            t_default = time.struct_time((t_now.tm_year, 1, 1, 0, 0, 0, 0, 1, -1))

            names = ('tm_year', 'tm_mon', 'tm_mday', 'tm_hour', 'tm_min',
                     'tm_sec', 'tm_wday', 'tm_yday', 'tm_isdst')
            args = []

            # Copy values from `t` if they are in `given`, otherwise from
            # `t_now` or `t_default`.
            for name in names:
                if name in given:
                    args.append(getattr(t, name))
                else:
                    if names.index(given[0]) > names.index(name):
                        args.append(getattr(t_now, name))
                    else:
                        args.append(getattr(t_default, name))
            return time.struct_time(args)

        t = None
        for frmt, given in cls._FORMATS:
            try:
                t = time.strptime(string, frmt)
            except ValueError:
                pass
            else:
                t = fill_in_missing_values(t, given)
                break

        if t is None:
            raise ValueError('Invalid format: %r' % string)
        else:
            return cls(time.mktime(t))

    def __str__(self):
        if self == self.UNKNOWN:
            return '?'
        elif self == self.NOT_APPLICABLE:
            return ''
        elif self == self.NOW:
            return 'now'
        elif self == self.SOON:
            return 'soon'
        elif self == self.NEVER:
            return 'never'

        abs_delta = abs(self - time.time())
        if abs_delta < 120:     # <= 2 minutes
            frmt = '%H:%M:%S'
        elif abs_delta < 86400: # <= 1 day
            frmt = '%H:%M'
        else:
            frmt = '%Y-%m-%d'
        return time.strftime(frmt, time.localtime(self))

    @property
    def full(self):
        if self == self.UNKNOWN:
            return 'unknown'
        elif self == self.NOT_APPLICABLE:
            return 'not applicable'
        elif self == self.NOW:
            return 'now'
        elif self == self.SOON:
            return 'soon'
        elif self == self.NEVER:
            return 'never'
        else:
            return time.strftime('%Y-%m-%d %H:%M', time.localtime(self))

    def __bool__(self):
        """Whether timestamp known"""
        return self != self.UNKNOWN and self != self.NOT_APPLICABLE and \
               self != self.NOW and self != self.SOON and self != self.NEVER

    @property
    def is_known(self):
        return bool(self)

    @property
    def delta(self):
        if self == self.UNKNOWN:
            return Timedelta(Timedelta.UNKNOWN)
        elif self == self.NOT_APPLICABLE:
            return Timedelta(Timedelta.NOT_APPLICABLE)
        elif self == self.NOW:
            return Timedelta(0)
        elif self == self.SOON:
            return Timedelta(0)
        elif self == self.NEVER:
            return Timedelta(Timedelta.NOT_APPLICABLE)
        else:
            return Timedelta(self - time.time())

    @property
    def in_future(self):
        return bool(self) and self > time.time()



class TorrentFilePriority(str):
    INT2STR = {-2:'off', -1:'low', 0:'normal', 1:'high'}
    STR2INT = {'off':-2, 'low':-1, 'normal':0, 'high':1}

    def __new__(cls, prio):
        if isinstance(prio, int):
            if prio not in cls.INT2STR:
                raise ValueError('Invalid {} value: {!r}'.format(cls.__name__, prio))
            obj = super().__new__(cls, cls.INT2STR[prio])
        else:
            if prio not in cls.STR2INT:
                raise ValueError('Invalid {} value: {!r}'.format(cls.__name__, prio))
            obj = super().__new__(cls, prio)
        return obj

    def __lt__(self, other): return int(self) < int(other)
    def __gt__(self, other): return int(self) > int(other)
    def __le__(self, other): return int(self) <= int(other)
    def __ge__(self, other): return int(self) >= int(other)
    def __int__(self): return self.STR2INT[self]
    def __repr__(self): return '<%s %r>' % (type(self).__name__, str(self))

class TorrentFile(abc.Mapping):
    """Mapping that holds the values of a single file in a torrent"""

    # Distinguish subtrees from files without comparing classes everywhere
    nodetype = 'leaf'

    TYPES = {
        'tid'             : int,
        'id'              : int,
        'name'            : SmartCmpStr,
        'path'            : Path,
        'size-total'      : lambda size: convert.size(size, unit='byte'),
        'size-downloaded' : lambda size: convert.size(size, unit='byte'),
        'is-wanted'       : bool,
        'priority'        : TorrentFilePriority,
        'progress'        : Percent,
    }

    _MODIFIERS = {
        'tid'             : lambda raw: raw['tid'],
        'id'              : lambda raw: raw['id'],
        'name'            : lambda raw: raw['name'],
        'path'            : lambda raw: os.sep.join(raw['path']),
        'size-total'      : lambda raw: raw['size-total'],
        'size-downloaded' : lambda raw: raw['size-downloaded'],
        'is-wanted'       : lambda raw: raw['is-wanted'],
        'priority'        : lambda raw: 'off' if not raw['is-wanted'] else raw['priority'],
        'progress'        : lambda raw: _calc_percent(raw['size-downloaded'], raw['size-total']),
    }

    def __init__(self, tid, id, name, path, size_total, size_downloaded, is_wanted, priority):
        self._raw = {'tid': tid, 'id': id, 'name': name, 'path': path,
                     'is-wanted': is_wanted, 'priority': priority,
                     'size-total': size_total, 'size-downloaded': size_downloaded}
        self._cache = {}

    def __getitem__(self, key):
        if key not in self._cache:
            val = self._MODIFIERS[key](self._raw)
            self._cache[key] = self.TYPES[key](val)
        return self._cache[key]

    def update(self, raw):
        self._raw.update(raw)
        try:
            for k in raw:
                del self._cache[k]
            if 'size-downloaded' in raw:
                del self._cache['progress']
        except KeyError:
            pass

    def __repr__(self): return '<{} {!r}>'.format(type(self).__name__, self['name'])
    def __iter__(self): return iter(self.TYPES)
    def __len__(self): return len(self.TYPES)


from . import base
def _ensure_TorrentFileTree(obj):
    if isinstance(obj, base.TorrentFileTreeBase):
        return obj
    else:
        raise RuntimeError('Not a TorrentFileTreeBase: %r' % obj)




from collections import (defaultdict, deque)
MAX_SAMPLES = 10
MAX_SAMPLE_AGE = 5*3600
_PEER_PROGRESS_DATA = defaultdict(lambda: deque(maxlen=MAX_SAMPLES))

def gc_peer_progress_data():
    for peer_id,samples in tuple(_PEER_PROGRESS_DATA.items()):
        # Remove samples that are too old
        while samples and (samples[0][0] + MAX_SAMPLE_AGE) < time.monotonic():
            samples.popleft()

        # Remove deque if there are no samples left
        if not samples:
            del _PEER_PROGRESS_DATA[peer_id]

def _guess_peer_rate_and_eta(peer_id, peer_progress, torrent_size):
    rate = 0
    if peer_progress >= 1:
        # Peer has already downloaded everything
        eta = Timedelta.NOT_APPLICABLE
    else:
        eta = Timedelta.UNKNOWN
        samples = _PEER_PROGRESS_DATA[peer_id]

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

from . import geoip
class TorrentPeer(abc.Mapping):
    TYPES = {
        'id'        : lambda val: val,
        'tid'       : lambda val: val,
        'tname'     : SmartCmpStr,
        'tsize'     : lambda size: convert.size(size, unit='byte'),
        'ip'        : str,
        'port'      : int,
        'client'    : SmartCmpStr,
        'country'   : SmartCmpStr,
        'progress'  : Percent,
        'rate-up'   : lambda rate: convert.bandwidth(rate, unit='byte'),
        'rate-down' : lambda rate: convert.bandwidth(rate, unit='byte'),
        'eta'       : Timedelta,
        'rate-est'  : lambda rate: convert.bandwidth(rate, unit='byte'),
    }

    _MODIFIERS = {
        'id'      : lambda p: hash((p['tid'], p['ip'], p['port'])),
        'country' : lambda p: geoip.country_code(p['ip']) or '?',
    }

    def __init__(self, tid, tname, tsize, ip, port, client, progress, rate_up, rate_down):
        self._dct = {'tid': tid, 'tname': tname, 'tsize': tsize,
                     'ip': ip, 'port': port, 'client': client, 'progress': progress,
                     'rate-up': rate_up, 'rate-down': rate_down}
        self._cache = {}

    def __getitem__(self, key):
        if key not in self._cache:
            if key in ('eta', 'rate-est'):
                rate, eta = _guess_peer_rate_and_eta(self['id'], self['progress'] / 100, self['tsize'])
                self._cache['rate-est'] = self.TYPES['rate-est'](rate)
                self._cache['eta'] = self.TYPES['eta'](eta)

            else:
                if key in self._MODIFIERS:
                    val = self._MODIFIERS[key](self._dct)
                else:
                    val = self._dct[key]
                self._cache[key] = self.TYPES[key](val)
        return self._cache[key]

    def __repr__(self): return '<{} #{}, {}>'.format(type(self).__name__, self['tid'], self['ip'])
    def __iter__(self): return iter(self.TYPES)
    def __len__(self): return len(self.TYPES)



class TorrentTracker(abc.Mapping):
    def _validate_tracker_state(string):
        if string not in ('stopped', 'idle', 'queued', 'announcing', 'scraping'):
            raise TypeError('Invalid tracker state: %r' % string)
        else:
            return SmartCmpStr(string)

    TYPES = {
        'tid'                : int,
        'tname'              : SmartCmpStr,
        'id'                 : lambda val: val,
        'tier'               : int,

        'url-announce'       : utils.URL,
        'url-scrape'         : lambda url: utils.URL(url) if url else '',
        'domain'             : SmartCmpStr,

        'state-announce'     : _validate_tracker_state,
        'state-scrape'       : _validate_tracker_state,
        'state'              : _validate_tracker_state,

        'error-announce'     : SmartCmpStr,
        'error-scrape'       : SmartCmpStr,
        'error'              : SmartCmpStr,

        'count-downloads'    : Count,
        'count-leeches'      : Count,
        'count-seeds'        : Count,

        'time-last-announce' : Timestamp,
        'time-next-announce' : Timestamp,
        'time-last-scrape'   : Timestamp,
        'time-next-scrape'   : Timestamp,
    }

    _GENERATORS = {
        'id'     : lambda self: hash((self['tid'], self['url-announce'])),
        'domain' : lambda self: self['url-announce'].domain,
        'state'  : lambda self: (self['state-scrape'] if self['state-announce'] == 'idle'
                                 else self['state-announce']),
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
        if key not in self._cache:
            types = self.TYPES
            generators = self._GENERATORS

            if key in generators:
                val = generators[key](self)
            else:
                val = self._dct[key]
            cache[key] = types[key](val)

        return cache[key]

    def __repr__(self): return '<%s %s>' % (type(self).__name__, self['url-announce'])
    def __iter__(self): return iter(self.TYPES)
    def __len__(self): return len(self.TYPES)



TYPES = {
    'id'                           : int,
    'hash'                         : str,
    'name'                         : SmartCmpStr,
    'ratio'                        : Ratio,
    'status'                       : Status,
    'path'                         : Path,
    'private'                      : bool,
    'comment'                      : SmartCmpStr,
    'creator'                      : SmartCmpStr,
    'magnetlink'                   : str,
    'count-pieces'                 : NumberInt,

    '%downloaded'                  : Percent,
    '%uploaded'                    : Percent,
    '%metadata'                    : Percent,
    '%verified'                    : Percent,
    '%available'                   : Percent,

    'peers-connected'              : NumberInt,
    'peers-uploading'              : NumberInt,
    'peers-downloading'            : NumberInt,
    'peers-seeding'                : Count,

    'timespan-eta'                 : Timedelta,
    'timespan-seeding'             : Timedelta,
    'timespan-downloading'         : Timedelta,
    'time-created'                 : Timestamp,
    'time-added'                   : Timestamp,
    'time-started'                 : Timestamp,
    'time-activity'                : Timestamp,
    'time-completed'               : Timestamp,
    'time-manual-announce-allowed' : Timestamp,

    'rate-down'                    : lambda rate: convert.bandwidth(rate, unit='byte'),
    'rate-up'                      : lambda rate: convert.bandwidth(rate, unit='byte'),

    'rate-limit-down'              : _rate_limit,
    'rate-limit-up'                : _rate_limit,

    'size-final'                   : lambda size: convert.size(size, unit='byte'),
    'size-total'                   : lambda size: convert.size(size, unit='byte'),
    'size-downloaded'              : lambda size: convert.size(size, unit='byte'),
    'size-uploaded'                : lambda size: convert.size(size, unit='byte'),
    'size-available'               : lambda size: convert.size(size, unit='byte'),
    'size-left'                    : lambda size: convert.size(size, unit='byte'),
    'size-corrupt'                 : lambda size: convert.size(size, unit='byte'),
    'size-piece'                   : lambda size: convert.size(size, unit='byte'),

    'error'                        : str,
    'trackers'                     : tuple,
    'peers'                        : tuple,
    'files'                        : _ensure_TorrentFileTree,
}
