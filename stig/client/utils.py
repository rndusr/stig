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

import asyncio
import calendar
import datetime
import operator
import os
import re
import time
from types import SimpleNamespace

from async_timeout import timeout as async_timeout

from . import constants as const
from ..utils import cached_property, convert  # noqa: F401
from ..utils.usertypes import (Bool, Float, Int, Option, Path, Percent,  # noqa: F401
                               String, multitype)


class SHA1(String):
    def __new__(cls, value, regex=r'^[0-9a-fA-F]{,40}$'):
        return super().__new__(cls, value, regex=regex)


class SizeInBytes(Int):
    def __new__(cls, value, **kwargs):
        return convert.size(value, unit='byte')


class Bandwidth(Int):
    typename = 'bandwidth'

    def __new__(cls, value, **kwargs):
        value = convert.bandwidth(value)
        kwargs.update(unit=convert.bandwidth.unit,
                      prefix=convert.bandwidth.prefix)
        return super().__new__(cls, value, **kwargs)

    @classmethod
    def _get_syntax(cls, **kwargs):
        return '%s[b|B]' % super()._get_syntax(**kwargs)


class BandwidthInBytes(Bandwidth):
    def __new__(cls, value, **kwargs):
        return convert.bandwidth(value, unit='byte')


class BandwidthInBytesOrNone(BandwidthInBytes):
    def __new__(cls, value, **kwargs):
        if value is None:
            return const.UNLIMITED
        else:
            return super().__new__(cls, value, **kwargs)


class BoolOrBandwidth(multitype(Bool.partial(true=('limited', 'enabled', 'yes', 'on', 'true'),
                                             false=('unlimited', 'disabled', 'no', 'off', 'false')),
                                Bandwidth)):
    @staticmethod
    def adjust(current, adjustment):
        """Adjust `current` by `adjustment`"""
        if isinstance(current, Bool) or current >= float('inf'):
            # If current number is infinity, adjust from 0
            current = 0
        new = current + adjustment
        if new < 0:
            # Drop to 0 if current is greater than zero.
            # If current already is zero, drop to infinity.
            if current > 0:
                new = 0
            else:
                new = const.UNLIMITED
        return new

    def __new__(cls, value, **kwargs):
        if isinstance(value, (float, int)) and value >= float('inf'):
            return super().__new__(cls, 'unlimited')
        else:
            return super().__new__(cls, value, **kwargs)


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


class SmartCmpPath(SmartCmpStr):
    def __new__(cls, path):
        return super().__new__(cls, os.path.normpath(path))


BoolOrPath = multitype(Bool, Path)


class Count(Int):
    UNKNOWN = -1

    def __str__(self):
        return '?' if self == self.UNKNOWN else super().without_unit


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
                num = self / amount

                # Small numbers get a sub-unit, for example '1d15h'
                if 1 <= abs_secs / amount < 10 and i < len(SECONDS) - 1:
                    subunit, subamount = SECONDS[i + 1]
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
                ts_max = datetime.datetime(year=dt.year + 1, month=1, day=1) - datetime.timedelta(seconds=1)
            elif least_significant_given == 'month':
                ts_min = datetime.datetime(year=dt.year, month=dt.month, day=1)
                if dt.month < 12:
                    ts_max = (datetime.datetime(year=dt.year, month=dt.month + 1, day=1)
                              - datetime.timedelta(seconds=1))
                else:
                    ts_max = (datetime.datetime(year=dt.year + 1, month=1, day=1)
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

    _DELTA_MAP = {NOW: Timedelta(0),
                  SOON: Timedelta(0),
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


class PerfectInterval():
    """Remove processing time from intervals"""

    def __init__(self):
        self._last_timestamp = 0

    def __call__(self, seconds):
        now = asyncio.get_event_loop().time()
        if self._last_timestamp <= 0:
            self._last_timestamp = int(now)
            return seconds
        else:
            expected = self._last_timestamp + seconds
            diff = now - expected
            interval = max(seconds - diff, 0)
            self._last_timestamp = expected
            return interval


class SleepUneasy():
    """Asynchronous sleep() that can be aborted"""

    def __init__(self):
        self._interrupt = asyncio.Event()
        self._perfint = PerfectInterval()

    async def sleep(self, seconds):
        """Sleep for `seconds` or until `interrupt` is called"""
        self._interrupt.clear()
        # Remove processing time from seconds
        seconds = self._perfint(seconds)
        try:
            async with async_timeout(seconds):
                await self._interrupt.wait()
        except asyncio.TimeoutError:
            pass  # Interval passed without interrupt
        finally:
            self._interrupt.clear()

    def interrupt(self):
        """Stop sleeping"""
        self._interrupt.set()


class Response(SimpleNamespace):
    """
    Response to an API call

    All API implementations should use this class to provide return values to
    API calls.

    success: Whether the call was a success
    msgs: Sequence of messages; either strings or ClientError exceptions

    Any other keyword arguments are made available as attributes.
    """
    def __init__(self, success, msgs=(), errors=(), **kwargs):
        super().__init__(success=bool(success),
                         msgs=tuple(msgs), errors=tuple(errors),
                         **kwargs)


class LazyDict(dict):
    """Dictionary with callables as values that return the actual value on demand"""
    def __getitem__(self, key):
        value = dict.__getitem__(self, key)
        if callable(value):
            value = value()
            dict.__setitem__(self, key, value)
        return value


class URL():
    """Parse URL as lenient as possible (no validation)"""

    # Pilfered from yurl: https://github.com/homm/yurl
    # This is not validating regexp.
    # It splits url to unambiguous parts according RFC.
    _split_re = re.compile(r'''
        (?:([^:/?#]+):)?            # scheme
        (?://                       # authority
            (?:([^/?\#@]*)@)?       # userinfo
            ([^/?\#]*)              # host:port
        )?
        ([^?\#]*)                   # path
        \??([^\#]*)                 # query
        \#?(.*)                     # fragment
        ''', re.VERBOSE | re.DOTALL).match

    @classmethod
    def _parse_url(cls, url):
        # Default to http scheme so 'host:123' is not interpreted as 'host://123/'
        if len(url) > 0 and '://' not in str(url):
            url = 'http://' + str(url)

        groups = cls._split_re(url).groups('')
        # Order: scheme, user+password, host+port, path, query, fragment
        dct = {}
        dct['scheme']   = groups[0] or None
        dct['path']     = groups[3] or None
        dct['query']    = groups[4] or None
        dct['fragment'] = groups[5] or None

        auth = groups[1]
        user, pw = None, None
        if auth:
            # Password in authentication is optional
            if ':' in auth:
                user, pw = auth.split(':')
            else:
                user, pw = auth, None
        dct['user'] = user or None
        dct['password'] = pw or None

        # Split port from host only if it consists of digits.
        host = groups[2]
        port = None
        port_idx = host.rfind(':')
        if port_idx >= 0:
            port_str = host[port_idx + 1:]
            if port_str.isdigit():
                host = host[:port_idx]
                port = int(port_str)
        dct['host'] = host or None
        dct['port'] = port or None

        return dct

    _obj_cache = {}

    def __new__(cls, url):
        if isinstance(url, cls):
            return url

        cache_id = url
        cache = cls._obj_cache
        url_dict = cache.get(cache_id)
        if url_dict is None:
            url_dict = cache[cache_id] = cls._parse_url(url)

        obj = super().__new__(cls)
        for attr in ('scheme', 'host', 'port', 'path', 'user', 'password'):
            setattr(obj, attr, url_dict[attr])
        return obj

    @property
    def has_auth(self):
        """Whether user and password properties are set"""
        return self.user is not None and self.password is not None

    @property
    def domain(self):
        domain = getattr(self, '_domain_cached', None)
        if domain is None:
            host = self.host
            if not host:
                self._domain_cached = None
            else:
                if host.count('.') <= 1:
                    domain = self._domain_cached = host
                else:
                    parts = host.rsplit('.', maxsplit=2)
                    domain = self._domain_cached = '.'.join(parts[-2:])
        return domain

    def __str__(self):
        string = getattr(self, '_cached_string', None)
        if string is None:
            parts = []
            if self.scheme:
                parts.append('%s://' % self.scheme)
            if self.user:
                parts.append('%s' % self.user)
                if self.password:
                    parts.append(':%s' % self.password)
                parts.append('@')
            if self.host:
                parts.append(self.host)
            if self.port:
                parts.append(':%s' % self.port)
            if self.path:
                parts.append('%s' % self.path)
            string = self._cached_string = ''.join(parts)
        return string

    def __setattr__(self, name, value):
        super().__setattr__(name, value)
        if name[0] != '_':
            # Clear caches
            if hasattr(self, '_cached_string'):
                del self._cached_string
            if name == 'host' and hasattr(self, '_domain_cached'):
                del self._domain_cached

    def __repr__(self):
        return '%s(%r)' % (type(self).__name__, str(self))

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        return str(self) == str(other)

    def __lt__(self, other):
        return str(self) < str(other)

    def __le__(self, other):
        return str(self) <= str(other)

    def __gt__(self, other):
        return str(self) > str(other)

    def __ge__(self, other):
        return str(self) >= str(other)

    def __contains__(self, other):
        return str(other) in str(self)
