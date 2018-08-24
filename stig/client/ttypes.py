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
# Types are used to convert values from the server (e.g. `Float(1234567)`) and
# for some types from the user as strings (e.g. `Float('1.3GB')`).

from ..logging import make_logger
log = make_logger(__name__)

from collections import abc
import os
import re
import time
import datetime

from .utils import (URL, Float, Int, convert, const)


Percent = Float.partial(unit='%')


class Ratio(Float):
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


class Count(Int):
    UNKNOWN = -1
    def __str__(self):
        return '?' if self == self.UNKNOWN else super().without_unit


class Status(tuple):
    """A Torrent's status as a tuple of strings"""

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
class SmartCmpStr(str):
    """
    String that compares case-insensitively if the other string consists solely
    of lower case characters.
    """

    def __cmp(self, op, other):
        if not isinstance(other, str):
            return NotImplemented

        # Do case-insensitive comparison if `other` consists solely of
        # lower-case characters
        o = str(other)
        if o == o.casefold():
            s = self.casefold()
        else:
            s = str(self)
        return op(s, o)

    def __lt__(self, other): return self.__cmp(operator.lt, other)
    def __le__(self, other): return self.__cmp(operator.le, other)
    def __eq__(self, other): return self.__cmp(operator.eq, other)
    def __ne__(self, other): return self.__cmp(operator.ne, other)
    def __gt__(self, other): return self.__cmp(operator.gt, other)
    def __ge__(self, other): return self.__cmp(operator.ge, other)
    def __contains__(self, other): return self.__cmp(operator.contains, other)

    # Defining __eq__ mandates defining __hash__ to make instances hashable
    def __hash__(self): return super().__hash__()


class Path(SmartCmpStr):
    def __new__(cls, path):
        return super().__new__(cls, os.path.normpath(path))

    def __repr__(self):
        return '<{} {!r}>'.format(type(self).__name__, str(self))

    def __hash__(self):
        return super().__hash__()



SECONDS = (('y', 31557600),  # 365.25 days
           ('M',  2629800),  # 1 year / 12
           ('w',   604800),  # 7 days
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

    _FULL_REGEX = re.compile((r'^(in |-|\+|)(\S+)( ago|)$'), flags=re.IGNORECASE)
    _SPLIT_REGEX = re.compile((r'((?:\d+\.\d+|\d+|\.\d+)[' +
                               r''.join(unit for unit,secs in SECONDS) +
                               r']?)'))

    @classmethod
    def from_string(cls, string):
        exc = ValueError('Invalid %s: %r' % (cls.__name__, string))

        match = cls._FULL_REGEX.match(string)
        if not match:
            raise exc

        sign_start = match.group(1).lower().strip()
        timespan = match.group(2)
        sign_end = match.group(3).lower().strip()
        sign = 1  # 1/-1 to represent +/-

        if sign_start == '-' or sign_end == 'ago':
            if sign_start == '+':
                raise exc
            sign = -1
        if any(sign_start == x for x in ('+', 'in')):
            if sign_end == 'ago':
                raise exc

        secs_total = 0
        for s in cls._SPLIT_REGEX.split(timespan):
            if len(s) < 1:
                continue
            elif not cls._SPLIT_REGEX.match(s):
                raise exc
            elif s[-1].isdigit():
                # No unit specified - assume seconds
                secs_total += float(s)
            else:
                num, unit = s[:-1], s[-1]
                for unit_,secs in SECONDS:
                    if unit == unit_:
                        secs_total += float(num) * secs
                        break

        return cls(secs_total * sign)

    def __str__(self):
        if self == self.UNKNOWN:
            return '?'
        elif self == self.NOT_APPLICABLE:
            return ''
        elif self == 0:
            return '0s'

        abs_secs = abs(self)
        for i,(unit,amount) in enumerate(SECONDS):
            if abs_secs >= amount:
                num = self/amount

                # Small numbers get a sub-unit, for example '1d15h'
                if 1 <= abs_secs/amount < 10 and i < len(SECONDS)-1:
                    subunit, subamount = SECONDS[i+1]
                    if num >= 0:
                        subnum = abs(((num % 1) * amount) / subamount)
                    else:
                        subnum = abs(((num % -1) * amount) / subamount)

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

    @property
    def timestamp(self):
        if self == self.UNKNOWN:
            return Timestamp(Timestamp.UNKNOWN)
        elif self == self.NOT_APPLICABLE:
            return Timestamp(Timestamp.NOT_APPLICABLE)
        else:
            return Timestamp(self + time.time())

    def __repr__(self):
        return '<%s %s / %s>' % (type(self).__name__, super().__str__(), self.__str__())


class Timestamp(float):
    # These constants get "random" fractions added to make it less likely that
    # any real-world value equals them.
    NOW            = -2 + 0.123456789
    SOON           = -1 + 0.123456789
    UNKNOWN        = 1e10 + 0.123456789
    NOT_APPLICABLE = 1e11 + 0.123456789
    NEVER          = 1e12 + 0.123456789

    _FORMATS_DATE = (('%Y',       ('year',)),
                     ('%Y-%m',    ('year', 'month')),
                     ('%Y-%m-%d', ('year', 'month', 'day')),
                     ('%d',       ('day',)),
                     ('%m-%d',    ('month', 'day')))
    _FORMATS_TIME = (('%H:%M',    ('hour', 'minute')),
                     ('%H:%M:%S', ('hour', 'minute', 'second')))

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
        dt_now = datetime.datetime.now().replace(second=0, microsecond=0)
        dt_default = datetime.datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

        def fill_in_missing_values(dt, given):
            names = ('year', 'month', 'day', 'hour', 'minute', 'second')
            most_significant_given = names.index(given[0])
            new_args = {}
            for name in names:
                if name in given:
                    new_args[name] = getattr(dt, name)
                else:
                    # If `name` is less significant than the most significant
                    # user-given value, fill in value from current time,
                    # otherwise fill in the lowest possible value from default.
                    # Example: User gave month and day: Get year from t_now.
                    #          Get hours, minutes and seconds from t_default.
                    if most_significant_given > names.index(name):
                        new_args[name] = getattr(dt_now, name)
                    else:
                        new_args[name] = getattr(dt_default, name)
            return datetime.datetime(**new_args)

        def get_timespan(dt, given):
            # Return min/max timestamp based on the least significant value.
            # Example: Use gave '2012-08' (year and month): Return timestamp for
            #          '2012-08-01 00:00:00' and '2012-08-31 23:59:59'.
            least_significant_given = given[-1]
            if least_significant_given == 'year':
                ts_min = datetime.datetime(year=dt.year, month=1, day=1)
                ts_max = datetime.datetime(year=dt.year+1, month=1, day=1) - datetime.timedelta(seconds=1)
            elif least_significant_given == 'month':
                ts_min = datetime.datetime(year=dt.year, month=dt.month, day=1)
                if dt.month < 12:
                    ts_max = (datetime.datetime(year=dt.year, month=dt.month+1, day=1)
                              - datetime.timedelta(seconds=1))
                else:
                    ts_max = (datetime.datetime(year=dt.year+1, month=1, day=1)
                              - datetime.timedelta(seconds=1))
            elif least_significant_given == 'day':
                ts_min = datetime.datetime(year=dt.year, month=dt.month, day=dt.day)
                ts_max = ts_min + datetime.timedelta(hours=23, minutes=59, seconds=59)
            elif least_significant_given == 'hour':
                ts_min = datetime.datetime(year=dt.year, month=dt.month, day=dt.day, hour=dt.hour)
                ts_max = ts_min + datetime.timedelta(minutes=59, seconds=59)
            elif least_significant_given == 'minute':
                ts_min = datetime.datetime(year=dt.year, month=dt.month, day=dt.day, hour=dt.hour, minute=dt.minute)
                ts_max = ts_min + datetime.timedelta(seconds=59)
            else:
                ts_min, ts_max = dt, dt
            return (int(ts_min.timestamp()), int(ts_max.timestamp()))

        for frmt,given in cls._FORMATS:
            try:
                dt = datetime.datetime.strptime(string, frmt)
            except ValueError:
                continue
            else:
                dt = fill_in_missing_values(dt, given)
                return cls(dt.timestamp(), _timespan=get_timespan(dt, given))

        raise ValueError('Invalid format: %r' % string)

    def __new__(cls, seconds, _timespan=None):
        obj = super().__new__(cls, seconds)
        obj._timespan = _timespan if _timespan is not None else (seconds, seconds)
        return obj

    def __eq__(self, other):
        return self._timespan[0] <= other <= self._timespan[1]

    def __hash__(self):  # Needed to stay hashable with __eq__()
        return super().__hash__()

    def __gt__(self, other):
        return self._timespan[0] > other

    def __ge__(self, other):
        return self._timespan[1] >= other

    def __lt__(self, other):
        return self._timespan[1] < other

    def __le__(self, other):
        return self._timespan[0] <= other

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

        # The format is based on the delta of seconds compared to the current time
        abs_delta = abs(self - time.time())
        if abs_delta < 120:
            frmt = '%H:%M:%S'
        elif abs_delta < 86400:
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
        return self not in (self.UNKNOWN, self.NOT_APPLICABLE, self.NEVER)

    @property
    def is_known(self):
        return self not in (self.NOW, self.SOON, self.UNKNOWN, self.NOT_APPLICABLE, self.NEVER)

    @property
    def timedelta(self):
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

    def __repr__(self):
        return '<%s %s / %s>' % (type(self).__name__, super().__str__(), self.__str__())



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

    def __eq__(self, other):
        if isinstance(other, int):
            return super().__eq__(self.INT2STR.get(other))
        return super().__eq__(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return super().__hash__()


class TorrentFile(abc.Mapping):
    """Mapping that holds the values of a single file in a torrent"""

    # Distinguish subtrees from files without comparing classes everywhere
    nodetype = 'leaf'

    TYPES = {
        'id'              : lambda val: val,
        'tid'             : lambda val: val,
        'name'            : SmartCmpStr,
        'path-absolute'   : Path,
        'path-relative'   : Path,
        'location'        : Path,
        'size-total'      : lambda size: convert.size(size, unit='byte'),
        'size-downloaded' : lambda size: convert.size(size, unit='byte'),
        'is-wanted'       : bool,
        'priority'        : TorrentFilePriority,
        '%downloaded'     : Percent,
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
        'id'          : lambda val: val,
        'tid'         : lambda val: val,
        'tname'       : SmartCmpStr,
        'tsize'       : lambda size: convert.size(size, unit='byte'),
        'ip'          : str,
        'port'        : int,
        'client'      : SmartCmpStr,
        'country'     : SmartCmpStr,
        '%downloaded' : Percent,
        'rate-up'     : lambda rate: convert.bandwidth(rate, unit='byte'),
        'rate-down'   : lambda rate: convert.bandwidth(rate, unit='byte'),
        'eta'         : Timedelta,
        'rate-est'    : lambda rate: convert.bandwidth(rate, unit='byte'),
    }

    _MODIFIERS = {
        'id'      : lambda p: (p['tid'], p['ip'], p['port']),
        'country' : lambda p: geoip.country_code(p['ip']) or '?',
    }

    def __init__(self, tid, tname, tsize, ip, port, client, pdownloaded, rate_up, rate_down):
        self._dct = {'tid': tid, 'tname': tname, 'tsize': tsize,
                     'ip': ip, 'port': port, 'client': client, '%downloaded': pdownloaded,
                     'rate-up': rate_up, 'rate-down': rate_down}
        self._cache = {}

    def __getitem__(self, key):
        if key not in self._cache:
            if key in ('eta', 'rate-est'):
                rate, eta = _guess_peer_rate_and_eta(self['id'], self['%downloaded'] / 100, self['tsize'])
                self._cache['rate-est'] = self.TYPES['rate-est'](rate)
                self._cache['eta'] = self.TYPES['eta'](eta)

            else:
                if key in self._MODIFIERS:
                    val = self._MODIFIERS[key](self._dct)
                else:
                    val = self._dct[key]
                self._cache[key] = self.TYPES[key](val)
        return self._cache[key]

    def clearcache(self):
        self._cache.clear()

    def __repr__(self): return '<{} #{}, {}>'.format(type(self).__name__, self['tid'], self['ip'])
    def __iter__(self): return iter(self.TYPES)
    def __len__(self): return len(self.TYPES)



class TorrentTracker(abc.Mapping):
    def _validate_tracker_status(string):
        if string not in ('stopped', 'idle', 'queued', 'announcing', 'scraping'):
            raise ValueError('Invalid tracker status: %r' % string)
        else:
            return SmartCmpStr(string)

    TYPES = {
        'id'                 : lambda val: val,
        'tid'                : int,
        'tname'              : SmartCmpStr,
        'tier'               : int,

        'url-announce'       : URL,
        'url-scrape'         : URL,
        'domain'             : SmartCmpStr,

        'status-announce'    : _validate_tracker_status,
        'status-scrape'      : _validate_tracker_status,
        'status'             : _validate_tracker_status,

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
        if key not in self._cache:
            modifier = self._MODIFIERS.get(key)
            if modifier is not None:
                val = modifier(self)
            else:
                val = self._dct[key]
            cache[key] = self.TYPES[key](val)

        return cache[key]

    def __repr__(self): return '<%s %s>' % (type(self).__name__, self['url-announce'])
    def __iter__(self): return iter(self.TYPES)
    def __len__(self): return len(self.TYPES)



def _rate(rate):
    return convert.bandwidth(rate, unit='byte')


def _rate_limit(limit):
    return const.UNLIMITED if limit is None else convert.bandwidth(limit, unit='byte')


def _data_size(size):
    return convert.size(size, unit='byte')


def _calc_percent(a, b):
    try:
        return a / b * 100
    except ZeroDivisionError:
        return 0


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
    'count-pieces'                 : Int,

    '%downloaded'                  : Percent,
    '%uploaded'                    : Percent,
    '%metadata'                    : Percent,
    '%verified'                    : Percent,
    '%available'                   : Percent,

    'peers-connected'              : Int,
    'peers-uploading'              : Int,
    'peers-downloading'            : Int,
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

    'rate-down'                    : _rate,
    'rate-up'                      : _rate,

    'limit-rate-down'              : _rate_limit,
    'limit-rate-up'                : _rate_limit,

    'size-final'                   : _data_size,
    'size-total'                   : _data_size,
    'size-downloaded'              : _data_size,
    'size-uploaded'                : _data_size,
    'size-available'               : _data_size,
    'size-left'                    : _data_size,
    'size-corrupt'                 : _data_size,
    'size-piece'                   : _data_size,

    'error'                        : str,
    'trackers'                     : tuple,
    'peers'                        : tuple,
    'files'                        : _ensure_TorrentFileTree,
}
