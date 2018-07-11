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

from ..ttypes import SmartCmpStr
from . import (BoolFilterSpec, CmpFilterSpec, Filter, FilterChain)


class SingleSettingFilter(Filter):
    DEFAULT_FILTER = 'name'

    # Filters without arguments
    BOOLEAN_FILTERS = {
        'all': BoolFilterSpec(
            lambda s: True,
            aliases=('*',),
            description='All settings'),
        'changed': BoolFilterSpec(
            lambda s: s['default'] != s['value'],
            aliases=('ch',),
            description='Settings with customized values'),
    }

    COMPARATIVE_FILTERS = {
        'name': CmpFilterSpec(
            lambda s, op, v: op(SmartCmpStr(s['id']), v),
            aliases=('n',),
            description='Match VALUE against name of setting',
            value_type=SmartCmpStr),
        'value': CmpFilterSpec(
            lambda s, op, v: op(SmartCmpStr(s['value']), v),
            aliases=('v',),
            description='Match VALUE against current value',
            value_type=SmartCmpStr),
        'default': CmpFilterSpec(
            lambda s, op, v: op(SmartCmpStr(s['default']), v),
            aliases=('def',),
            description='Match VALUE against default value',
            value_type=SmartCmpStr),
        'description': CmpFilterSpec(
            lambda s, op, v: op(SmartCmpStr(s['description']), v),
            aliases=('desc',),
            description='Match VALUE against description',
            value_type=SmartCmpStr),
    }


class SettingFilter(FilterChain):
    """One or more filters combined with & and | operators"""
    filterclass = SingleSettingFilter
