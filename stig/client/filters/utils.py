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

import operator

from ..utils import Timedelta, Timestamp, const

from ...logging import make_logger  # isort:skip
log = make_logger(__name__)


def timestamp_or_timedelta(string, default_sign=1):
    """
    Try to parse `string` as Timestamp or Timedelta

    If `string` is parsed as Timedelta and the string does not indicate whether
    the Timedelta should be positive (in the future) or negative (in the past),
    multiply it by `default_sign`, which should be either 1 (default) or -1.
    """
    try:
        return Timestamp.from_string(string)
    except ValueError:
        delta = Timedelta.from_string(string)
        # Apply default_sign if no sign was given explicitly
        string = string.strip()
        if (not string.startswith('in') and
            not string.endswith('ago') and
            string[0] not in ('+', '-')):
            delta = delta.inverse if default_sign < 0 else delta
        return delta


_lgfilters = (operator.__lt__, operator.__le__, operator.__gt__, operator.__ge__)
def cmp_timestamp_or_timdelta(item_value, op, user_value):
    """Compare any combination of Timestamp and Timedelta objects"""
    # Some filters don't make any sense
    if (item_value in Timestamp.CONSTANTS and
        isinstance(user_value, Timedelta) and
        op in _lgfilters):
        return False
    elif item_value in Timedelta.CONSTANTS and op in _lgfilters:
        return False

    type_item_value = type(item_value)
    type_user_value = type(user_value)

    if type_user_value is Timestamp:
        if type_item_value is Timestamp:
            # result = op(item_value, user_value)
            # log.debug('1: %r %s %r = %r', item_value, op.__name__, user_value, result)
            # return result
            return op(item_value, user_value)
        elif type_item_value is Timedelta:
            # result = op(item_value, user_value.timedelta)
            # log.debug('2: %r %s %r (%r) = %r',
            #           item_value, op.__name__, user_value, user_value.timedelta, result)
            # return result
            return op(item_value, user_value.timedelta)
    elif type_user_value is Timedelta:
        # If the filter is, e.g., 'less than 1y ago', future dates would match
        # (because "[any future date] > -[seconds in 1y]") but we interpret the
        # filter as 'less than 1y ago up till now'.  Same thing for 'in less
        # than 1y' - past dates technically match, but they shouldn't.
        if not _either_past_or_future(item_value, user_value):
            return False
        elif type_item_value is Timedelta:
            # result = op(abs(item_value), abs(user_value))
            # log.debug('3: %r %s %r = %r', item_value, op.__name__, user_value, result)
            # return result
            return op(abs(item_value), abs(user_value))
        elif type_item_value is Timestamp:
            user_value_timestamp = user_value.timestamp
            if user_value < 0:
                if item_value in (Timestamp.NOW, Timestamp.SOON):
                    return False
                # result = op(user_value_timestamp, item_value)
                # log.debug('4: %r (%r) %s %r = %r',
                #           user_value, user_value_timestamp, op.__name__, item_value, result)
                # return result
                return op(user_value_timestamp, item_value)
            else:
                # result = op(item_value, user_value_timestamp)
                # log.debug('5: %r %s %r (%r) = %r',
                #           item_value, op.__name__, user_value, user_value_timestamp, result)
                # return result
                return op(item_value, user_value_timestamp)

    raise RuntimeError('cannot compare %r with %r' % (item_value, user_value))

def _either_past_or_future(item_value, user_value):
    """
    Return True if `item_value` and `user_value` are equal, both in the past or
    both in the future, False otherwise
    """
    type_item_value = type(item_value)
    type_user_value = type(user_value)

    if type_user_value is Timestamp:
        user_value_in_future = user_value.in_future
    elif type_user_value is Timedelta:
        user_value_in_future = user_value > 0

    if type_item_value is Timestamp:
        item_value_in_future = item_value.in_future
    elif type_item_value is Timedelta:
        item_value_in_future = item_value > 0

    return item_value_in_future == user_value_in_future


# TODO: Add docstring
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
            # `user_value` is 'unlimited'/'off'/etc
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
