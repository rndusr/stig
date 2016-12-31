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
    _REGEX = re.compile('^([-+]?\d+(?:\.\d+|)) ?(' +\
                        '|'.join(p[0] for p in _ALL_PREFIXES) + \
                        '|)(.*?)$',
                        flags=re.IGNORECASE)

    def __new__(cls, num, prefix='metric', unit=None):
        if isinstance(num, cls):
            return num
        elif isinstance(num, str):
            match = cls._REGEX.match(num)
            if match is None:
                raise ValueError('Not a number: {!r}'.format(num))
            else:
                num_str = match.group(1)
                unit = match.group(3) or unit
                prfx = match.group(2)
                num = float(num_str)
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
        s = None
        for prefix,size in self._prefixes:
            if self >= size:
                s = '%s%s' % (pretty_float(self/size), prefix)
                break
        if s is None:
            s = pretty_float(self)
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

    def __add__(self, other): return type(self)(super().__add__(other))
    def __sub__(self, other): return type(self)(super().__sub__(other))
    def __mul__(self, other): return type(self)(super().__mul__(other))
    def __div__(self, other): return type(self)(super().__div__(other))
    def __truediv__(self, other): return type(self)(super().__truediv__(other))
    def __floordiv__(self, other): return type(self)(super().__floordiv__(other))
    def __mod__(self, other): return type(self)(super().__mod__(other))
    def __divmod__(self, other): return type(self)(super().__divmod__(other))
    def __pow__(self, other): return type(self)(super().__pow__(other))


class Percent(float):
    """Float with a pretty string representation"""
    def __str__(self):
        return pretty_float(self)


class Ratio(Number):
    """A Torrent's upload/download ratio as a float"""
    UNKNOWN = -1
    def __str__(self):
        if self == self.UNKNOWN:
            return '?'
        else:
            return pretty_float(self)


class SeedCount(Number):
    UNKNOWN = -1
    def __str__(self):
        return '?' if self == self.UNKNOWN else super().__str__()


class Status(str):
    """A Torrent's status as string"""
    VERIFY   = 'verifying'
    VERIFY_Q = 'verifying pending'
    LEECH    = 'leeching'
    LEECH_Q  = 'leeching pending'
    SEED     = 'seeding'
    SEED_Q   = 'seeding pending'
    STOPPED  = 'stopped'
    ORDER = (VERIFY, VERIFY_Q, LEECH, LEECH_Q, SEED, SEED_Q, STOPPED)

    def __new__(cls, status):
        if status not in cls.ORDER:
            raise ValueError('Invalid status string: {!r}'.format(status))
        else:
            obj = super().__new__(cls, status)
            obj._index = cls.ORDER.index(status)
            return obj

    def __lt__(self, other): return self._index < other._index
    def __le__(self, other): return self._index <= other._index
    def __gt__(self, other): return self._index > other._index
    def __ge__(self, other): return self._index >= other._index


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

    def __cmp(self, other, op):
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

    def __lt__(self, other): return self.__cmp(other, operator.lt)
    def __le__(self, other): return self.__cmp(other, operator.le)
    def __eq__(self, other): return self.__cmp(other, operator.eq)
    def __ne__(self, other): return self.__cmp(other, operator.ne)
    def __gt__(self, other): return self.__cmp(other, operator.gt)
    def __ge__(self, other): return self.__cmp(other, operator.ge)
    def __contains__(self, other): return self.__cmp(other, operator.contains)

    def __hash__(self):
        return super().__hash__()



TIMEDELTA_NOW = 5
SECONDS = (('y', 31557600),
           ('M',  2592000),
           ('d',    86400),
           ('h',     3600),
           ('m',       60),
           ('s',        1))

class Timedelta(int):
    NOT_APPLICABLE = -1
    UNKNOWN = -2

    def __str__(self):
        if self == self.UNKNOWN:
            return '?'
        elif self == self.NOT_APPLICABLE:
            return ''
        else:
            abs_secs = abs(self)
            if abs_secs < TIMEDELTA_NOW:
                return 'now'
            else:
                for unit,amount in SECONDS:
                    if abs_secs >= amount:
                        return str(int(self/amount)) + unit

    def __bool__(self):
        """Whether delta is known"""
        return self >= 0

import time
class Timestamp(float):
    def __str__(self):
        abs_delta = abs(self - time.time())
        if abs_delta <= SECONDS[2][1]:      # 1 day: locale's time
            frmt = '%X'
        elif abs_delta <= SECONDS[2][1]*2:  # 2 days: locale's date and time
            frmt = '%x %X'
        else:                               # locale's date
            frmt = '%x'
        return time.strftime(frmt, time.localtime(self))

    def __bool__(self):
        """Whether timestamp is just a few seconds in the past/future"""
        return abs(self - time.time()) < TIMEDELTA_NOW



from functools import total_ordering
@total_ordering
class TorrentFilePriority(str):
    _INT2STR = {-1:'low', 0:'normal', 1:'high', -2:'shun'}
    _STR2INT = {'low':-1, 'normal':0, 'high':1, 'shun':-2}

    def __new__(cls, prio):
        if isinstance(prio, int):
            if prio not in cls._INT2STR:
                raise ValueError('Invalid {} value: {!r}'.format(cls.__name__, prio))
            obj = super().__new__(cls, cls._INT2STR[prio])
        else:
            if prio not in cls._STR2INT:
                raise ValueError('Invalid {} value: {!r}'.format(cls.__name__, prio))
            obj = super().__new__(cls, prio)
        return obj

    def __int__(self): return self._STR2INT[self]
    def __lt__(self, other): return int(self) < int(other)
    def __repr__(self): return '<%s %r>' % (type(self).__name__, str(self))


import os
class TorrentFile(abc.Mapping):
    """Mapping that holds the values of a single file in a torrent"""

    # Distinguish subtrees from files without comparing classes everywhere
    nodetype = 'leaf'

    TYPES = {
        'tid'             : lambda val: int(val),
        'id'              : lambda val: int(val),
        'name'            : lambda val: SmartCmpStr(val),
        'path'            : lambda val: SmartCmpStr(val),
        'size-total'      : lambda val: convert.size(val, unit='byte'),
        'size-downloaded' : lambda val: convert.size(val, unit='byte'),
        'is-wanted'       : lambda val: bool(val),
        'priority'        : lambda val: TorrentFilePriority(val),
        'progress'        : lambda val: Percent(val),
    }

    _VALUES = {
        'tid'             : lambda raw: raw['tid'],
        'id'              : lambda raw: raw['id'],
        'name'            : lambda raw: raw['name'],
        'path'            : lambda raw: os.sep.join(raw['path']),
        'size-total'      : lambda raw: raw['size-total'],
        'size-downloaded' : lambda raw: raw['size-downloaded'],
        'is-wanted'       : lambda raw: raw['is-wanted'],
        'priority'        : lambda raw: -2 if not raw['is-wanted'] else raw['priority'],
        'progress'        : lambda raw: raw['size-downloaded'] / raw['size-total'] * 100,
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


# Because 'convert' needs Number, which is specified in this file, it must be
# imported AFTER Number exists to avoid a circular import.
from . import convert

from . import base
def _ensure_TorrentFileTree(obj):
    if isinstance(obj, base.TorrentFileTreeBase):
        return obj
    else:
        raise RuntimeError('Not a TorrentFileTreeBase instance: {!r}'.format(obj))

TYPES = {
    'id'                : int,
    'hash'              : str,
    'name'              : SmartCmpStr,
    'status'            : Status,
    'path'              : SmartCmpStr,
    'ratio'             : Ratio,

    'private'           : bool,
    'stalled'           : bool,
    'isolated'          : bool,

    '%downloaded'       : Percent,
    '%metadata'         : Percent,
    '%verified'         : Percent,

    'peers-connected'   : Number,
    'peers-uploading'   : Number,
    'peers-downloading' : Number,
    'peers-seeding'     : SeedCount,

    'timestamp-created' : Timestamp,
    'timestamp-added'   : Timestamp,
    'timestamp-started' : Timestamp,
    'timestamp-active'  : Timestamp,
    'timestamp-done'    : Timestamp,
    'timespan-eta'      : Timedelta,

    'rate-down'         : lambda v: convert.bandwidth(v, unit='byte'),
    'rate-up'           : lambda v: convert.bandwidth(v, unit='byte'),

    'size-final'        : lambda v: convert.size(v, unit='byte'),
    'size-total'        : lambda v: convert.size(v, unit='byte'),
    'size-downloaded'   : lambda v: convert.size(v, unit='byte'),
    'size-uploaded'     : lambda v: convert.size(v, unit='byte'),
    'size-available'    : lambda v: convert.size(v, unit='byte'),
    'size-corrupt'      : lambda v: convert.size(v, unit='byte'),

    'trackers'          : tuple,
    'files'             : _ensure_TorrentFileTree,
}
