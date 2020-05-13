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

# The TYPES dictionary at the end of this file maps Torrent key names to types.
# Types must derive from `type` or be None.  Every Torrent key must have a type.
#
# Types are used to convert values from the server (e.g. `Float(1234567)`) and
# for some types from the user as strings (e.g. `Float('1.3GB')`).

import calendar
import datetime
import operator
import os
import re
import time
from collections import abc, defaultdict, deque

from .utils import (URL, Float, Int, Percent, String, cached_property, const, convert,
                    multitype)

from ..logging import make_logger  # isort:skip
log = make_logger(__name__)


class SHA1(String):
    def __new__(cls, value, regex=r'^[0-9a-fA-F]{,40}$'):
        return super().__new__(cls, value, regex=regex)

class SizeInBytes(Int):
    def __new__(cls, value, **kwargs):
        return convert.size(value, unit='byte')

class BandwidthInBytes(Int):
    def __new__(cls, value, **kwargs):
        return convert.bandwidth(value, unit='byte')

class BandwidthInBytesOrNone(BandwidthInBytes):
    def __new__(cls, value, **kwargs):
        if value is None:
            return const.UNLIMITED
        else:
            return super().__new__(cls, value, **kwargs)

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

class SmartCmpStr(str):
    """
    String that compares case-insensitively if the other string consists solely
    of lower case characters.
    """

    def __cmp(self, op, other):
        if not isinstance(other, str):
            return NotImplemented
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
    def __hash__(self):
        return super().__hash__()

class Path(SmartCmpStr):
    def __new__(cls, path):
        return super().__new__(cls, os.path.normpath(path))

    def __repr__(self):
        return '%s(%r)' % (type(self).__name__, str(self))



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
    CONSTANTS = (UNKNOWN, NOT_APPLICABLE)
    _CONSTANTS_MAP_STRINGS = {'unknown': UNKNOWN, 'na': NOT_APPLICABLE,
                              'n/a': NOT_APPLICABLE, 'not applicable': NOT_APPLICABLE}

    _FULL_REGEX = re.compile((r'^(in |-|\+|)(\S+)( ago|)$'), flags=re.IGNORECASE)
    _SPLIT_REGEX = re.compile((r'((?:\d+\.\d+|\d+|\.\d+)[' +
                               r''.join(unit for unit,secs in SECONDS) +
                               r']?)'))

    @classmethod
    def from_string(cls, string):
        const_value = cls._CONSTANTS_MAP_STRINGS.get(string, None)
        if const_value is not None:
            return cls(const_value)

        match = cls._FULL_REGEX.match(string)
        if not match:
            raise ValueError('Invalid %s: %r' % (cls.__name__, string))

        sign_start = match.group(1).lower().strip()
        timespan = match.group(2)
        sign_end = match.group(3).lower().strip()
        sign = 1  # 1/-1 to represent +/-

        if sign_start == '-' or sign_end == 'ago':
            if sign_start == '+':
                raise ValueError('Invalid %s: %r' % (cls.__name__, string))
            sign = -1
        if any(sign_start == x for x in ('+', 'in')):
            if sign_end == 'ago':
                raise ValueError('Invalid %s: %r' % (cls.__name__, string))

        secs_total = 0
        kwargs = {}
        for part in cls._SPLIT_REGEX.split(timespan):
            if len(part) < 1:
                continue
            elif not cls._SPLIT_REGEX.match(part):
                raise ValueError('Invalid %s: %r' % (cls.__name__, string))
            elif part[-1].isdigit():
                # No unit specified - assume seconds
                secs_total += float(part)
            else:
                num, unit = part[:-1], part[-1]
                for unit_,secs in SECONDS:
                    if unit == unit_:
                        secs_total += float(num) * secs
                        if unit == 'y':
                            kwargs['_real_years'] = float(num) * sign
                        elif unit == 'M':
                            kwargs['_real_months'] = float(num) * sign
                        break

        return cls(secs_total * sign, **kwargs)

    def __new__(cls, seconds, _real_years=None, _real_months=None):
        obj = super().__new__(cls, seconds)
        obj._real_years = _real_years
        obj._real_months = _real_months
        return obj

    @cached_property
    def inverse(self):
        """Return the same object with the sign switched"""
        real_years, real_months = self._real_years, self._real_months
        return type(self)(-int(self),
                          _real_years=-real_years if real_years is not None else None,
                          _real_months=-real_months if real_months is not None else None)

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

    @cached_property
    def with_preposition(self):
        if self > 0:
            return 'in %s' % self
        elif self < 0:
            return ('%s ago' % self)[1:]  # Remove the first char ('-')
        else:
            return 'now'

    def __bool__(self):
        """Whether delta is known"""
        return self not in self.CONSTANTS

    @cached_property
    def is_known(self):
        return bool(self)

    @property
    def timestamp(self):
        if self == self.UNKNOWN:
            return Timestamp(Timestamp.UNKNOWN)
        elif self == self.NOT_APPLICABLE:
            return Timestamp(Timestamp.NOT_APPLICABLE)
        else:
            ts = None
            real_years, real_months = self._real_years, self._real_months
            if real_years or real_months:
                # Because we can't know the exact number of seconds in a
                # year/month, we take the number of years/months provided by the
                # parser and use datetime and timedelta to calculate the
                # timestamp.
                secs = int(self)
                dt = datetime.datetime.now()
                # datetime will throw OverflowError if numbers are too large
                try:
                    if real_years is not None:
                        dt = dt.replace(year=int(dt.year + real_years))
                        # Subtract the approximate number seconds in the number of years
                        secs = secs % (real_years * SECONDS[0][1])

                    if real_months is not None:
                        # When adding/subtracting months, we may have to keep the
                        # month between 1-12. We also may have to adjust the year
                        # and/or day.
                        # https://stackoverflow.com/a/4131114
                        month = int(dt.month - 1 + real_months)
                        year = int(dt.year + month // 12)  # Integer division
                        month = int(month % 12 + 1)
                        day = min(dt.day, calendar.monthrange(year, month)[1])  # Avoid day 30 in February
                        dt = dt.replace(year=year, month=month, day=day)
                        # Subtract the approximate number seconds in the number of months
                        secs = secs % (real_months * SECONDS[1][1])
                except (OverflowError, ValueError):
                    pass
                else:
                    dt = dt + datetime.timedelta(seconds=secs)
                    ts = Timestamp(dt.timestamp())

            if ts is None:
                # Without years or months given, we can simply add our delta to time.time()
                ts = Timestamp(time.time() + self)
            return ts

    def __repr__(self):
        return '<%s %s / %s>' % (type(self).__name__, str(int(self)), self.__str__())


class Timestamp(float):
    # These constants get "random" fractions added to make it less likely that
    # any real-world value equals them.
    NOW            = -2 + 0.123456789
    SOON           = -1 + 0.123456789
    UNKNOWN        = 1e10 + 0.123456789
    NOT_APPLICABLE = 1e11 + 0.123456789
    NEVER          = 1e12 + 0.123456789
    CONSTANTS = (NOW, SOON, UNKNOWN, NOT_APPLICABLE, NEVER)
    _CONSTANTS_MAP_STRINGS = {'now': NOW, 'soon': SOON, 'unknown': UNKNOWN,
                              'na': NOT_APPLICABLE, 'n/a': NOT_APPLICABLE, 'not applicable': NOT_APPLICABLE,
                              'never': NEVER}

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
        now = datetime.datetime.now()
        value = cls._CONSTANTS_MAP_STRINGS.get(string.lower(), None)
        if value is not None:
            return cls(value, _timerange=(value, value))

        dt_now = now.replace(second=0, microsecond=0)
        dt_default = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

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
                    # Example: User gave month and day: Get year from dt_now.
                    #          Get hours, minutes and seconds from dt_default.
                    if most_significant_given > names.index(name):
                        new_args[name] = getattr(dt_now, name)
                    else:
                        new_args[name] = getattr(dt_default, name)
            return datetime.datetime(**new_args)

        def get_timerange(dt, given):
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
                return cls(dt.timestamp(), _timerange=get_timerange(dt, given))

        raise ValueError('Invalid format: %r' % string)

    def __new__(cls, seconds, _timerange=None):
        obj = super().__new__(cls, seconds)
        obj._timerange = _timerange if _timerange is not None else (seconds, seconds)
        return obj

    def __eq__(self, other):
        return self._timerange[0] <= other <= self._timerange[1]

    def __hash__(self):  # Needed to stay hashable with __eq__()
        return super().__hash__()

    def __gt__(self, other):
        return self._timerange[0] > other

    def __ge__(self, other):
        return self._timerange[1] >= other

    def __lt__(self, other):
        return self._timerange[1] < other

    def __le__(self, other):
        return self._timerange[0] <= other

    _SHORT_STR_MAP = {NOW: 'now', SOON: 'soon', UNKNOWN: '?',
                      NOT_APPLICABLE: '', NEVER: 'never'}
    def __str__(self):
        const_str = self._SHORT_STR_MAP.get(self, None)
        if const_str is not None:
            return const_str
        else:
            # The format is based on the delta of seconds compared to the
            # current time
            abs_delta = abs(self - time.time())
            if abs_delta < 120:
                frmt = '%H:%M:%S'
            elif abs_delta < 86400:
                frmt = '%H:%M'
            else:
                frmt = '%Y-%m-%d'
            return time.strftime(frmt, time.localtime(self))

    _LONG_STR_MAP = {NOW: 'now', SOON: 'soon', UNKNOWN: 'unknown',
                     NOT_APPLICABLE: 'not applicable', NEVER: 'never'}
    @cached_property
    def full(self):
        const_str = self._LONG_STR_MAP.get(self, None)
        if const_str is not None:
            return const_str
        else:
            return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self))

    @cached_property
    def date(self):
        if self in self.CONSTANTS:
            return self.full
        else:
            return time.strftime('%Y-%m-%d', time.localtime(self))

    @cached_property
    def time(self):
        if self in self.CONSTANTS:
            return self.full
        else:
            return time.strftime('%H:%M:%S', time.localtime(self))

    def __bool__(self):
        return self not in (self.UNKNOWN, self.NOT_APPLICABLE, self.NEVER)

    @cached_property
    def is_known(self):
        return self not in self.CONSTANTS

    _DELTA_MAP = {NOW: Timedelta(0), SOON: Timedelta(0),
                  UNKNOWN: Timedelta(Timedelta.UNKNOWN),
                  NOT_APPLICABLE: Timedelta(Timedelta.NOT_APPLICABLE),
                  NEVER: Timedelta(Timedelta.NOT_APPLICABLE)}
    @property
    def timedelta(self):
        delta = self._DELTA_MAP.get(self, None)
        if delta is not None:
            return delta
        else:
            return Timedelta(self - time.time())

    @property
    def in_future(self):
        return bool(self) and self > time.time()

    def __repr__(self):
        return '<%s %s / %s>' % (type(self).__name__, str(int(self)), self.full)



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

    def __ne__(self, other): return not self.__eq__(other)
    def __lt__(self, other): return self.as_int < int(other)
    def __gt__(self, other): return self.as_int > int(other)
    def __le__(self, other): return self.as_int <= int(other)
    def __ge__(self, other): return self.as_int >= int(other)
    def __int__(self): return self.as_int
    def __repr__(self): return '%s(%r)' % (type(self).__name__, str(self))
    def __hash__(self): return super().__hash__()

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
        'name'            : SmartCmpStr,
        'path-absolute'   : Path,
        'path-relative'   : Path,
        'location'        : Path,
        'size-total'      : SizeInBytes,
        'size-downloaded' : SizeInBytes,
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



class TorrentPeer(abc.Mapping):
    TYPES = {
        'id'          : None,
        'tid'         : None,
        'tname'       : SmartCmpStr,
        'tsize'       : SizeInBytes,
        'ip'          : str,
        'port'        : int,
        'client'      : SmartCmpStr,
        'downloaded'  : SizeInBytes,
        '%downloaded' : Percent,
        'rate-up'     : BandwidthInBytes,
        'rate-down'   : BandwidthInBytes,
        'eta'         : Timedelta,
        'rate-est'    : BandwidthInBytes,
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
            eta = Timedelta.NOT_APPLICABLE
        else:
            eta = Timedelta.UNKNOWN
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

    def __repr__(self): return '<{} #{}, {}>'.format(type(self).__name__, self['tid'], self['ip'])
    def __iter__(self): return iter(self.TYPES)
    def __len__(self): return len(self.TYPES)



class TrackerStatus(SmartCmpStr):
    def __new__(cls, status):
        if status not in ('stopped', 'idle', 'queued', 'announcing', 'scraping'):
            raise ValueError('Invalid tracker status: %r' % status)
        else:
            return super().__new__(cls, status)

class TorrentTracker(abc.Mapping):
    TYPES = {
        'id'                 : None,
        'tid'                : int,
        'tname'              : SmartCmpStr,
        'tier'               : int,

        'url-announce'       : URL,
        'url-scrape'         : URL,
        'domain'             : SmartCmpStr,

        'status-announce'    : TrackerStatus,
        'status-scrape'      : TrackerStatus,
        'status'             : TrackerStatus,

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

    def __repr__(self): return '<%s %s>' % (type(self).__name__, self['url-announce'])
    def __iter__(self): return iter(self.TYPES)
    def __len__(self): return len(self.TYPES)


TYPES = {
    'id'                           : int,
    'hash'                         : SHA1,
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

    'rate-down'                    : BandwidthInBytes,
    'rate-up'                      : BandwidthInBytes,
    'limit-rate-down'              : BandwidthInBytesOrNone,
    'limit-rate-up'                : BandwidthInBytesOrNone,
    'size-final'                   : SizeInBytes,
    'size-total'                   : SizeInBytes,
    'size-downloaded'              : SizeInBytes,
    'size-uploaded'                : SizeInBytes,
    'size-available'               : SizeInBytes,
    'size-left'                    : SizeInBytes,
    'size-corrupt'                 : SizeInBytes,
    'size-piece'                   : SizeInBytes,

    'error'                        : str,
    'trackers'                     : tuple,
    'peers'                        : tuple,
    'files'                        : None,
}
