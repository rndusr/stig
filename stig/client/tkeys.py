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

"""Value types for Torrent classes"""

# The TYPES dictionary at the end of this file maps Torrent key names to
# types.  Every Torrent key must have a type, even if it's just a no-op
# (`lambda obj: obj`).
#
# A type is any callable that converts a single value to the appropriate class
# instance.
#
# Types are used to convert values from the server (e.g. large integers) and
# from the user (e.g. number strings like '3.5G').  Not all types must accept
# user-given values (e.g. 'files').


from ..logging import make_logger
log = make_logger(__name__)

from collections import abc
from .utils import pretty_float
import os

from . import constants as const


from itertools import chain
import re
class Number(float):
    """float with a nice string representation; also parses strings like '123K' or '123Mi'"""

    _PREFIXES_BINARY = (('Ti', 1024**4), ('Gi', 1024**3), ('Mi', 1024**2), ('Ki', 1024))
    _PREFIXES_METRIC = (('T', 1000**4), ('G', 1000**3), ('M', 1000**2), ('k', 1000))
    _ALL_PREFIXES = tuple((prefix.lower(), size)
                          for prefix,size in chain.from_iterable(zip(_PREFIXES_BINARY,
                                                                     _PREFIXES_METRIC)))
    _ALL_PREFIXES_DCT = dict(_ALL_PREFIXES)
    _REGEX = re.compile('^([-+]?(?:\d+\.\d+|\d+|\.\d+)) ?(' +\
                        '|'.join(p[0] for p in _ALL_PREFIXES) + \
                        '|)(.*?)$',
                        flags=re.IGNORECASE)

    @classmethod
    def from_string(cls, string, prefix='metric', unit=None):
        match = cls._REGEX.match(string)
        if match is None:
            raise ValueError('Not a number: {!r}'.format(string))
        else:
            num = float(match.group(1))
            unit = match.group(3) or unit
            prfx = match.group(2)
            if prfx:
                all_prfxs = cls._ALL_PREFIXES_DCT
                prfx_lower = prfx.lower()
                if prfx_lower in all_prfxs:
                    num *= all_prfxs[prfx_lower]

            prfx_len = len(prfx)
            if prfx_len == 2:
                prefix = 'binary'
            elif prfx_len == 1:
                prefix = 'metric'

            return cls(num, prefix, unit)

    def __new__(cls, num, prefix='metric', unit=None):
        if isinstance(num, cls):
            return cls(float(num), prefix or num.prefix, unit or num.unit)

        obj = super().__new__(cls, num)
        if prefix == 'binary':
            obj._prefixes = cls._PREFIXES_BINARY
        elif prefix == 'metric':
            obj._prefixes = cls._PREFIXES_METRIC
        else:
            raise ValueError("prefix must be 'binary' or 'metric', not {!r}".format(prefix))
        obj.unit = unit
        obj.prefix = prefix
        return obj

    @property
    def with_unit(self):
        s = self.without_unit
        if self.unit is not None:
            s += self.unit
        return s

    @property
    def without_unit(self):
        for prefix,size in self._prefixes:
            if self >= size:
                return pretty_float(self/size) + prefix
        return pretty_float(self)

    def __str__(self):
        return self.without_unit

    def __repr__(self):
        return '<{} {}, prefix={!r}, unit={!r}>'.format(type(self).__name__, float(self),
                                                        self.prefix, self.unit)

    # Arithmetic operations return Number instances with unit and prefix preserved
    def __add__(self, other):
        return type(self)(super().__add__(other), unit=self.unit, prefix=self.prefix)
    def __sub__(self, other):
        return type(self)(super().__sub__(other), unit=self.unit, prefix=self.prefix)
    def __mul__(self, other):
        return type(self)(super().__mul__(other), unit=self.unit, prefix=self.prefix)
    def __div__(self, other):
        return type(self)(super().__div__(other), unit=self.unit, prefix=self.prefix)
    def __truediv__(self, other):
        return type(self)(super().__truediv__(other), unit=self.unit, prefix=self.prefix)
    def __floordiv__(self, other):
        return type(self)(super().__floordiv__(other), unit=self.unit, prefix=self.prefix)
    def __mod__(self, other):
        return type(self)(super().__mod__(other), unit=self.unit, prefix=self.prefix)
    def __divmod__(self, other):
        return type(self)(super().__divmod__(other), unit=self.unit, prefix=self.prefix)
    def __pow__(self, other):
        return type(self)(super().__pow__(other), unit=self.unit, prefix=self.prefix)

# Because 'convert' needs Number, which is specified in this file, it must be
# imported AFTER Number exists to avoid a circular import.
from . import convert


def _rate_limit(limit):
    return const.UNLIMITED if limit is None else convert.bandwidth(limit)


class Percent(float):
    """Float with a pretty string representation"""
    def __str__(self):
        return pretty_float(self)

def _calc_percent(a, b):
    try:
        return a / b * 100
    except ZeroDivisionError:
        return 0


class Ratio(Number):
    """A Torrent's upload/download ratio as a float"""
    UNKNOWN = -1
    NOT_APPLICABLE = -2
    def __str__(self):
        if self == self.UNKNOWN:
            return '?'
        elif self == self.NOT_APPLICABLE:
            return ''
        else:
            return pretty_float(self)


class SeedCount(Number):
    UNKNOWN = -1
    def __str__(self):
        return '?' if self == self.UNKNOWN else super().__str__()


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
           ('M',  2629800),  # 1y / 12
           ('d',    86400),
           ('h',     3600),
           ('m',       60),
           ('s',        1))

class Timedelta(int):
    # To sort unknown and not applicable Timedeltas below the rest, these
    # constants have large values that are very likely never encountered as
    # actual values.
    UNKNOWN        = 1e10    # ~3.1k years
    NOT_APPLICABLE = 1e10+1  # ~31k years

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


import time
class Timestamp(int):
    UNKNOWN        = -1
    NOT_APPLICABLE = -2

    _FORMATS_DATE = (('%Y',       ('tm_year',)),
                     ('%Y-%m',    ('tm_year', 'tm_mon')),
                     ('%Y-%m-%d', ('tm_year', 'tm_mon', 'tm_mday')),
                     ('%d',       ('tm_mday',)),
                     ('%m-%d',    ('tm_mon', 'tm_mday')))
    _FORMATS_TIME = (('%H:%M', ('tm_hour', 'tm_min')),)

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

        abs_delta = abs(self - time.time())
        if abs_delta <= SECONDS[2][1]:  # <= 1 day
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
        else:
            return time.strftime('%Y-%m-%d %H:%M', time.localtime(self))

    def __bool__(self):
        """Whether timestamp known"""
        return self != self.UNKNOWN and self != self.NOT_APPLICABLE

    @property
    def is_known(self):
        return bool(self)

    @property
    def delta(self):
        if self == self.UNKNOWN:
            return Timedelta(Timedelta.UNKNOWN)
        elif self == self.NOT_APPLICABLE:
            return Timedelta(Timedelta.NOT_APPLICABLE)
        else:
            return Timedelta(self - time.time())

    @property
    def in_future(self):
        return bool(self) and self > time.time()



from functools import total_ordering
@total_ordering
class TorrentFilePriority(str):
    INT2STR = {-1:'low', 0:'normal', 1:'high', -2:'shun'}
    STR2INT = {'low':-1, 'normal':0, 'high':1, 'shun':-2}

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

    def __int__(self): return self.STR2INT[self]
    def __lt__(self, other): return int(self) < int(other)
    def __repr__(self): return '<%s %r>' % (type(self).__name__, str(self))


import os
class TorrentFile(abc.Mapping):
    """Mapping that holds the values of a single file in a torrent"""

    # Distinguish subtrees from files without comparing classes everywhere
    nodetype = 'leaf'

    TYPES = {
        'tid'             : int,
        'id'              : int,
        'name'            : SmartCmpStr,
        'path'            : Path,
        'size-total'      : convert.size,
        'size-downloaded' : convert.size,
        'is-wanted'       : bool,
        'priority'        : TorrentFilePriority,
        'progress'        : Percent,
    }

    _VALUES = {
        'tid'             : lambda raw: raw['tid'],
        'id'              : lambda raw: raw['id'],
        'name'            : lambda raw: raw['name'],
        'path'            : lambda raw: os.sep.join(raw['path']),
        'size-total'      : lambda raw: raw['size-total'],
        'size-downloaded' : lambda raw: raw['size-downloaded'],
        'is-wanted'       : lambda raw: raw['is-wanted'],
        'priority'        : lambda raw: (TorrentFilePriority.STR2INT['shun']
                                         if not raw['is-wanted'] else raw['priority']),
        'progress'        : lambda raw: _calc_percent(raw['size-downloaded'], raw['size-total']),
    }

    def __init__(self, tid, id, name, path, size_total, size_downloaded, is_wanted, priority):
        self._raw = {'tid': tid, 'id': id, 'name': name, 'path': path,
                     'is-wanted': is_wanted, 'priority': priority,
                     'size-total': size_total, 'size-downloaded': size_downloaded}
        self._cache = {}

    def __getitem__(self, key):
        if key not in self._cache:
            self._cache[key] = self.TYPES[key](
                self._VALUES[key](self._raw)
            )
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
        raise RuntimeError('Not a TorrentFileTreeBase instance: {!r}'.format(obj))




import time
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
        'tsize'     : convert.size,
        'ip'        : str,
        'port'      : int,
        'client'    : SmartCmpStr,
        'country'   : SmartCmpStr,
        'progress'  : Percent,
        'rate-up'   : convert.bandwidth,
        'rate-down' : convert.bandwidth,
        'eta'       : Timedelta,
        'rate-est'  : convert.bandwidth,
    }

    _VALUES = {
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
                rate, eta = _guess_peer_rate_and_eta(self['id'], self['progress']/100, self['tsize'])
                self._cache['rate-est'] = self.TYPES['rate-est'](rate)
                self._cache['eta'] = self.TYPES['eta'](eta)

            else:
                if key in self._VALUES:
                    val = self._VALUES[key](self._dct)
                else:
                    val = self._dct[key]
                self._cache[key] = self.TYPES[key](val)
        return self._cache[key]

    def __repr__(self): return '<{} {}@{}>'.format(type(self).__name__, self['ip'], self['progress'])
    def __iter__(self): return iter(self.TYPES)
    def __len__(self): return len(self.TYPES)



TYPES = {
    'id'                : int,
    'hash'              : str,
    'name'              : SmartCmpStr,
    'ratio'             : Ratio,
    'status'            : Status,
    'path'              : Path,
    'private'           : bool,
    'comment'           : SmartCmpStr,
    'creator'           : SmartCmpStr,
    'magnetlink'        : str,
    'count-pieces'      : Number,

    '%downloaded'       : Percent,
    '%uploaded'         : Percent,
    '%metadata'         : Percent,
    '%verified'         : Percent,
    '%available'        : Percent,

    'peers-connected'   : Number,
    'peers-uploading'   : Number,
    'peers-downloading' : Number,
    'peers-seeding'     : SeedCount,

    'timespan-eta'      : Timedelta,
    'time-created'      : Timestamp,
    'time-added'        : Timestamp,
    'time-started'      : Timestamp,
    'time-activity'     : Timestamp,
    'time-completed'    : Timestamp,
    'time-manual-announce-allowed': Timestamp,

    'rate-down'         : convert.bandwidth,
    'rate-up'           : convert.bandwidth,

    'rate-limit-down'   : _rate_limit,
    'rate-limit-up'     : _rate_limit,

    'size-final'        : convert.size,
    'size-total'        : convert.size,
    'size-downloaded'   : convert.size,
    'size-uploaded'     : convert.size,
    'size-available'    : convert.size,
    'size-left'         : convert.size,
    'size-corrupt'      : convert.size,
    'size-piece'        : convert.size,

    'trackers'          : tuple,
    'error'             : str,
    'peers'             : tuple,
    'files'             : _ensure_TorrentFileTree,
}
