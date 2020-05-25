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
from collections import abc

from .. import constants as const
from ..utils import SmartCmpStr
from .base import BoolFilterSpec, CmpFilterSpec, Filter, FilterChain, FilterSpecDict


def _is_sequence(obj):
    return isinstance(obj, abc.Sequence) and not isinstance(obj, str)

# Setting values have multiple incompatible types.  Try hard to compare them to
# the user-given value or fail silently.
def _match_coerced_value(setting, key, op, value):
    setting_value = setting[key]

    # Try to make `value` the same type as `setting['value']`
    validate = setting.get('validate', None)
    if validate is not None:
        try:
            value = validate(value)
        except ValueError:
            return False

    # Sequence matches if all its items are in `setting['value']`
    if _is_sequence(setting_value) and _is_sequence(value):
        if op is operator.__contains__:
            # Match if `settings['value'] contains all items of `value`, in any order
            for v in value:
                if v not in setting_value:
                    return False
            return True
        else:
            try:
                return op(setting_value, value)
            except TypeError:
                return False
    else:
        try:
            return op(setting_value, value)
        except TypeError:
            return False


class _SingleFilter(Filter):
    DEFAULT_FILTER = 'name'

    BOOLEAN_FILTERS = FilterSpecDict({
        'all'     : BoolFilterSpec(None,
                                   aliases=('*',),
                                   description='All settings'),
        'changed' : BoolFilterSpec(lambda s: s['value'] not in (s['default'], const.DISCONNECTED),
                                   aliases=('ch',),
                                   description='Settings with customized values'),
    })

    COMPARATIVE_FILTERS = FilterSpecDict({
        'name'        : CmpFilterSpec(value_getter=lambda s: s['id'],
                                      value_type=SmartCmpStr,
                                      aliases=('n',),
                                      description='Match VALUE against setting name'),
        'value'       : CmpFilterSpec(value_getter=lambda s: s['value'],
                                      value_matcher=lambda s, op, v: _match_coerced_value(s, 'value', op, v),
                                      value_type=SmartCmpStr,
                                      aliases=('v',),
                                      description='Match VALUE against current value'),
        'default'     : CmpFilterSpec(value_getter=lambda s: s['default'],
                                      value_matcher=lambda s, op, v: _match_coerced_value(s, 'default', op, v),
                                      value_type=SmartCmpStr,
                                      aliases=('def',),
                                      description='Match VALUE against default value'),
        'description' : CmpFilterSpec(value_getter=lambda s: s['description'],
                                      value_type=SmartCmpStr,
                                      aliases=('desc',),
                                      description='Match VALUE against description'),
    })


class SettingFilter(FilterChain):
    """One or more filters combined with & and | operators"""
    filterclass = _SingleFilter
