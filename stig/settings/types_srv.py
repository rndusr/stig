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

from .types import (BooleanValue, IntegerValue, ListValue, NumberValue,
                    OptionValue, PathValue, SetValue, StringValue, ValueBase,
                    MultiValue)
from ..client.errors import ClientError
from ..client import constants as const
from ..client import convert as converter


def is_srv_setting(setting, settings=None):
    """Whether `ValueBase` instance `setting` is managed by the server

    If `settings` is not None, it must be a `Settings` instance and `setting` is
    looked up as a name.
    """
    if settings is not None:
        try:
            setting = settings[setting]
        except KeyError:
            return False
    return isinstance(setting, ValueBase) and type(setting).__name__.endswith('SrvValue')


def _mk_constantValue(constant, typename=None, valuesyntax=None):
    """Create proper Value from constant"""
    clsname = constant.name.capitalize() + 'Value'
    clsattrs = {
        '__constant': constant,
        'typename': typename,
        'valuesyntax': valuesyntax,
    }

    def validate(self, value):
        if value is not self.__constant and value != self.__constant.name:
            raise ValueError('Not %r: %r' % (self.__constant, value))
    clsattrs['validate'] = validate

    def convert(self, value):
        self.validate(value)
        return self.__constant
    clsattrs['convert'] = convert

    return type(clsname, (ValueBase,), clsattrs)

DisconnectedValue = _mk_constantValue(const.DISCONNECTED)
UnlimitedValue    = _mk_constantValue(const.UNLIMITED)
RandomValue       = _mk_constantValue(const.RANDOM, typename='random', valuesyntax="'random'")


class BandwidthValue(NumberValue):
    """NumberValue that passes values through `client.convert.bandwidth`"""

    valuesyntax = '%s[b|B]' % NumberValue.valuesyntax

    def convert(self, value):
        # Make sure that both numbers are in the same unit when adjusting current value
        if isinstance(value, str) and len(value) >= 3 and value[:2] in ('+=', '-='):
            operator = value[:2]
            value = converter.bandwidth.from_string(value[2:])
            value = operator + str(float(value))

        # Convert to NumberFloat and ensure it has a unit
        return converter.bandwidth(super().convert(value))

    def validate(self, value):
        super().validate(value)
        self.convert(value)


class RateLimitValue(MultiValue(BooleanValue, UnlimitedValue, BandwidthValue)):
    """Special type that accepts boolean and bandwidth limits

    It runs numbers through `client.convert.bandwidth` to give them the correct
    unit and unit prefix.

    If set to `True`, it returns the most recent number it was set to.
    """

    def __init__(self, *args, **kwargs):
        object.__setattr__(self, '_previous_number', converter.bandwidth(0))
        super().__init__(*args, **kwargs)

    def set(self, value):
        super().set(value)

        # Remember this number so we can go back to it if we're set to True
        if isinstance(self.get(), BandwidthValue.type):
            self._previous_number = self.get()

        # If limit was just disabled, set internal number to 0 so that if the
        # next value is an adjustment (e.g '+=1Mb'), we start from 0 instead of
        # the previously set number, which may be confusing to the user.
        if self.get() is const.UNLIMITED:
            self.instances[BandwidthValue].set(0)

    def convert(self, value):
        value = super().convert(value)
        if value is True:
            return self._previous_number    # Re-enable previously set limit
        elif value is False or value < 0:
            return const.UNLIMITED          # No limit
        else:
            return value                    # Must be a BandwidthValue object


def SrvValue(*value_clses):
    """Create new class for server value"""
    cls = MultiValue(DisconnectedValue, *value_clses)
    clsname = cls.__name__[:-5] + 'SrvValue'  # Replace 'Value' at the end with 'SrvValue'
    clsattrs = { '__supercls': cls }

    def __init__(self, *args, getter, setter, **kwargs):
        object.__setattr__(self, '__getter', getter)
        object.__setattr__(self, '__setter', setter)
        kwargs['default'] = const.DISCONNECTED
        self.__supercls.__init__(self, *args, **kwargs)
    clsattrs['__init__'] = __init__

    async def set_(self, value):
        # Make sure we have the most recent value.  This is important when
        # adjusting numbers relatively (e.g. '+=100').
        self.get()

        # Raise any validation/conversion errors
        self.__supercls.set(self, value)
        try:
            await self.__setter(self.__supercls.get(self))
        except ClientError as e:
            raise ValueError("Can't change server setting {}: {}".format(self.name, e))
        else:
            log.debug('SrvValue: Successfully set %s to %r', self.name, self.get())
    clsattrs['set'] = set_

    def get(self):
        current_value = self.__getter()
        self.__supercls.set(self, current_value)
        return self.__supercls.get(self)
    clsattrs['get'] = get

    return type(clsname, (cls,), clsattrs)


# Create *SrvValue class for each *Value class
BooleanSrvValue = SrvValue(BooleanValue)
IntegerSrvValue = SrvValue(IntegerValue)
ListSrvValue    = SrvValue(ListValue)
NumberSrvValue  = SrvValue(NumberValue)
OptionSrvValue  = SrvValue(OptionValue)
PathSrvValue    = SrvValue(PathValue)
SetSrvValue     = SrvValue(SetValue)
StringSrvValue  = SrvValue(StringValue)

# Some settings need special values
PathIncompleteSrvValue = SrvValue(BooleanValue, PathValue)
PortSrvValue           = SrvValue(IntegerValue, RandomValue)
RateLimitSrvValue      = SrvValue(RateLimitValue)
