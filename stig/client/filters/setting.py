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
from .common import (BoolFilterSpec, CmpFilterSpec, Filter, FilterChain)


class _SingleFilter(Filter):
    DEFAULT_FILTER = 'name'

    BOOLEAN_FILTERS = {
        'all'     : BoolFilterSpec(None,
                                   aliases=('*',),
                                   description='All settings'),
        'changed' : BoolFilterSpec(lambda s: s['default'] != s['value'],
                                   aliases=('ch',),
                                   description='Settings with customized values'),
    }

    COMPARATIVE_FILTERS = {
        'name'        : CmpFilterSpec(value_getter=lambda s: s['id'],
                                      value_type=SmartCmpStr,
                                      aliases=('n',),
                                      description='Match VALUE against setting name'),
        'value'       : CmpFilterSpec(value_getter=lambda s: s['value'],
                                      value_type=SmartCmpStr,
                                      aliases=('v',),
                                      description='Match VALUE against current value'),
        'default'     : CmpFilterSpec(value_getter=lambda s: s['default'],
                                      value_type=SmartCmpStr,
                                      aliases=('def',),
                                      description='Match VALUE against default value'),
        'description' : CmpFilterSpec(value_getter=lambda s: s['description'],
                                      value_type=SmartCmpStr,
                                      aliases=('desc',),
                                      description='Match VALUE against description'),
    }


class SettingFilter(FilterChain):
    """One or more filters combined with & and | operators"""
    filterclass = _SingleFilter
