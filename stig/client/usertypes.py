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

from ..logging import make_logger
log = make_logger(__name__)

import os

from ..utils.usertypes import (BooleanValue, IntegerValue, FloatValue,
                               OptionValue, PathValue, ValueBase, MultiValue)
from . import constants as const
from . import errors
from . import convert


def _mk_constantValue(constant, typename=None, valuesyntax=None):
    """Create proper Value class from constant"""
    clsname = constant.name.capitalize() + 'Value'
    clsattrs = {
        '__constant': constant,
        'typename': typename,
        'valuesyntax': valuesyntax,
    }

    def validate(self, value):
        if value is not self.__constant and value != self.__constant.name:
            raise ValueError('Not %r' % self.__constant)
    clsattrs['validate'] = validate

    def convert(self, value):
        self.validate(value)
        return self.__constant
    clsattrs['convert'] = convert

    return type(clsname, (ValueBase,), clsattrs)

DisconnectedValue = _mk_constantValue(const.DISCONNECTED)
UnlimitedValue    = _mk_constantValue(const.UNLIMITED)
RandomValue       = _mk_constantValue(const.RANDOM, typename='random', valuesyntax="'random'")


class BandwidthValue(FloatValue):
    """FloatValue that passes values through `client.convert.bandwidth`"""

    valuesyntax = '%s[b|B]' % FloatValue.valuesyntax

    def convert(self, value):
        if isinstance(value, str):
            # It's important that both numbers have the same unit when adjusting
            # the current value
            value = value.strip()
            if len(value) >= 3 and value[:2] in ('+=', '-='):
                operator = value[:2]
                value = convert.bandwidth.from_string(value[2:])
                value = operator + str(float(value))
            value = super().convert(value)

        # Convert to NumberFloat and ensure it has a unit
        return convert.bandwidth(value)


class RateLimitValue(MultiValue(BooleanValue, UnlimitedValue, BandwidthValue)):
    """Rate limits can be boolean, unlimited or a number"""

    def __init__(self, *args, **kwargs):
        object.__setattr__(self, '_current_bandwidth', convert.bandwidth(0))
        super().__init__(*args, **kwargs)

    def set(self, value):
        super().set(value)
        value = self.get()

        # If limit was just disabled, set internal bandwidth value to 0 so that
        # if the next value is an adjustment (e.g '+=1Mb'), we start from 0
        # instead of some previously set bandwidth that is long forgotten.
        if value is const.UNLIMITED:
            self.instances[BandwidthValue].set(0)

        # Remember this number so we can go back to it if we're set to True
        elif isinstance(value, BandwidthValue.type):
            self._current_bandwidth = value

    def convert(self, value):
        value = super().convert(value)
        if value is True:
            return self._current_bandwidth  # Re-enable previously set limit
        elif value is False or value < 0:
            return const.UNLIMITED          # No limit
        else:
            return value                    # Must be a BandwidthValue object


def RemoteValue(*value_clses):
    """Create new class for remote value"""
    cls = MultiValue(DisconnectedValue, *value_clses)
    clsname = cls.__name__[:-5] + 'RemoteValue'  # Replace 'Value' at the end with 'RemoteValue'
    clsattrs = {}

    def __init__(self, *args, upgrade, remote_getter, setter, **kwargs):
        #       upgrade : The property decorated by @setting (used as a
        #                function). It should convert the raw value (e.g. 'true'
        #                -> True) and pass the result to _set_local().

        # remote_getter : The corresponding get_* coroutine
        #        setter : The corresponding set_* coroutine
        self._upgrade = upgrade
        self._remote_getter = remote_getter
        self._setter = setter
        kwargs['default'] = const.DISCONNECTED
        self._value = cls(*args, **kwargs)
    clsattrs['__init__'] = __init__

    # Local values (use _upgrade to get the intended value)
    clsattrs['_get_local'] = lambda self: self._value.get()
    clsattrs['_set_local'] = lambda self, raw_value: self._value.set(raw_value)
    clsattrs['value'] = property(fget=lambda self: self._upgrade()._get_local(),
                                  doc=lambda self: type(self._value).value.__doc__)
    clsattrs['string'] = lambda self, *a, **kw: self._upgrade()._value.string(*a, **kw)


    # set() method changes value remotely (and locally)
    async def set_(self, value):
        # Make sure we have an actual value.  This is important when adjusting
        # numbers relatively (e.g. '+=100kB').
        if self._value.get() is const.DISCONNECTED:
            try:
                await self.get()
            except errors.ClientError as e:
                raise ValueError("Can't change setting %s: %s" % (self.name, e))

        # Parse value and raise any validation/conversion errors
        self._value.set(value)
        value = self._value.get()

        # Push new value to server
        try:
            log.debug('Calling %s(%r)', self._setter.__qualname__, value)
            await self._setter(value)
        except errors.ClientError as e:
            raise ValueError("Can't change setting %s: %s" % (self.name, e))
    clsattrs['set'] = set_

    # get() method uses SettingsAPI.get_* method to get fresh value
    async def get(self):
        log.debug('Calling %r()', self._remote_getter.__qualname__)
        value = (await self._remote_getter()).value
        self._value.set(value)
        return value
    clsattrs['get'] = get

    # Mutable properties
    for propname in ('name', 'description'):
        clsattrs[propname] = property(fget=lambda self, pn=propname: getattr(self._value, pn),
                                      fset=lambda self, new, pn=propname: setattr(self._value, pn, new),
                                      doc=lambda self, pn=propname: getattr(self._value, pn).__doc__)

    # Immutable properties
    for propname in ('typename', 'reset', '__repr__', '__str__'):
        clsattrs[propname] = property(fget=lambda self, pn=propname: getattr(self._value, pn),
                                      doc=lambda self, pn=propname: getattr(self._value, pn).__doc__)

    return type(clsname, (), clsattrs)


# Settings are cached as descendants of RemoteValue instances
BooleanRemoteValue   = RemoteValue(BooleanValue)
IntegerRemoteValue   = RemoteValue(IntegerValue)
OptionRemoteValue    = RemoteValue(OptionValue)
RateLimitRemoteValue = RemoteValue(RateLimitValue)
PortRemoteValue      = RemoteValue(IntegerValue, RandomValue)

class PathCompleteRemoteValue(RemoteValue(PathValue)):
    """Make new path absolute relative to current path if not already absolute"""
    async def set(self, path):
        # Fetch current path if necessary before setting new path
        if self._get_local() is None:
            await self.get()
        basedir = self.value
        await super().set(os.path.join(basedir, path))

class PathIncompleteRemoteValue(RemoteValue(BooleanValue, PathValue)):
    """Same as PathCompleteRemoteValue but also accepts booleans"""
    async def set(self, path):
        # Fetch current path if necessary before setting new path
        if self._get_local() is None:
            await self.get()
        if self.value not in (True, False):
            basedir = self.value
            await super().set(os.path.join(basedir, path))
        else:
            await super().set(path)
