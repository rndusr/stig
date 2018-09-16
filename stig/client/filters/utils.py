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

from ..ttypes import (Timedelta, Timestamp)
from ..utils import const


def timestamp_or_timedelta(string, default_sign=1):
    try:
        return Timestamp.from_string(string)
    except ValueError:
        delta = Timedelta.from_string(string)
        # Apply default_sign if no sign was given explicitly
        string = string.strip()
        if (not string.startswith('in') and
            not string.endswith('ago') and
            string[0] not in ('+', '-')):
            delta = Timedelta(delta * default_sign)
        return delta

def time_filter(torrent_value, op, user_value):
    if not torrent_value.is_known:
        return False

    type_torrent_value = type(torrent_value)
    type_user_value = type(user_value)

    if type_torrent_value is Timestamp:
        if type_user_value is Timestamp:
            return op(torrent_value, user_value)
        elif type_user_value is Timedelta:
            return _compare_timedelta(torrent_value.timedelta, op,  user_value)

    elif type_torrent_value is Timedelta:
        if type_user_value is Timedelta:
            return _compare_timedelta(torrent_value, op, user_value)
        elif type_user_value is Timestamp:
            return _compare_timedelta(torrent_value, op, user_value.timedelta)

    raise RuntimeError('cannot compare {torrent_value!r} with {user_value!}')

def _compare_timedelta(delta_torrent, op, delta_user):
    if delta_user <= 0:
        # User's time delta is in the past - ignore future times
        if delta_torrent > 0:
            return False
    elif delta_user > 0:
        # User's time delta is in the future - ignore past times
        if delta_torrent <= 0:
            return False
    return op(abs(delta_torrent), abs(delta_user))


def limit_rate_filter(limit, op, user_value):
    # `limit` may be a number or const.UNLIMITED.
    # `user_value` may be a number or a Bool (which is not a derivative of the
    # built-in `bool`).
    # If `user_value` is a Bool, True means 'limited' and False means
    # 'unlimited'.

    if isinstance(user_value, (int, float)):
        # This works because const.UNLIMITED behaves like `float('inf')`.
        return op(limit, user_value)
    else:
        if not user_value:
            return op(limit, const.UNLIMITED)

        # `user_value` is 'limited'.
        elif op.__name__ in ('gt', 'ge'):
            # 'greater than limited' -> 'equal to unlimited'
            return limit == const.UNLIMITED
        elif op.__name__ in ('eq', 'ne'):
            # 'equal/unequal to limited' -> 'not equal/unequal to unlimited'
            return not op(limit, const.UNLIMITED)
        elif op.__name__ == 'lt':
            # 'lower than limited' -> No idea what to do here.
            return False
        elif op.__name__ == 'le':
            # Ignore the 'lower' in 'lower or equal';
            # 'equal to limited' -> ' unequal to unlimited'
            return limit != const.UNLIMITED
        else:
            # That should be all possible operators, but to avoid any
            # tracebacks, whatever is left gets regular treatment
            return op(limit, user_value)
