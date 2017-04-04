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

from .settings import (ValueBase, StringValue, IntegerValue, NumberValue,
                       BooleanValue, PathValue, ListValue, SetValue,
                       OptionValue)
from ..client.errors import ClientError
from ..client import constants as const
from ..client import convert


class SrvValueBase(ValueBase):
    def __init__(self, name, getter, setter, description='No description available'):
        super().__init__(name, default=const.DISCONNECTED, description=description)
        self._getter = getter
        self._setter = setter

    @property
    def value(self):
        return self._getter()

    async def set(self, value):
        log.debug('Setting server value %r: %r', self.name, value)
        try:
            value = self.convert(value)
            self.validate(value)
            await self._setter(value)
        except ClientError as e:
            raise ValueError("Can't change server setting {}: {}".format(self.name, e))
        except ValueError as e:
            log.debug('%s while setting %s to %r: %s', type(e).__name__, self.name, value, e)
            raise ValueError('{} = {}: {}'.format(self.name, self.str(value), e))
        else:
            log.debug('Successfully set %s to %r', self.name, value)

    def convert(self, value):
        log.debug('SrvValueBase: converting %r', value)
        if value is const.DISCONNECTED:
            return value
        else:
            log.debug('consulting super().convert for %r', value)
            value = super().convert(value)
            log.debug('got back: %r', value)
            return value

    def validate(self, value):
        log.debug('SrvValueBase: validating %r', value)
        if value is not const.DISCONNECTED:
            log.debug('consulting super().validate for %r', value)
            super().validate(value)
            log.debug('Valid value: %r', value)


class RateLimitSrvValue(SrvValueBase, NumberValue):
    typename = 'number or bool'
    valuesyntax = ('[+=|-=]<NUMBER>[k|M|G|T|Ki|Mi|Gi|Ti][b|B] or '
                   '%s (case is ignored)' % BooleanValue.valuesyntax)

    def convert(self, value):
        def convert_bandwidth(value):
            try:
                return convert.bandwidth.from_string(value)
            except ValueError as e:
                raise ValueError('Not a {}: {!r}'.format(self.typename, value))

        try:
            # value may be something like 'on' or 'off'
            return BooleanValue.convert(self, value)
        except ValueError:
            # Parse relative values
            if isinstance(value, str) and len(value) >= 3 and value[:2] in ('+=', '-='):
                op = value[:2]
                num = convert_bandwidth(value[2:].strip())

                # Pretend current value is 0 if user wants to adjust UNLIMITED.
                if self.value is const.UNLIMITED and op == '+=':
                    return num

                return super().convert(op + str(float(num)))

            # Parse other strings or numbers
            elif not const.is_constant(value):
                return convert_bandwidth(value)

            # Let parent provide the error message
            return super().convert(value)

    def validate(self, value):
        if isinstance(value, bool) or value in (const.ENABLED, const.DISABLED):
            pass
        else:
            super().validate(value)  # May raise ValueError


class PathSrvValue(SrvValueBase, PathValue):
    pass

class PathIncompleteSrvValue(PathSrvValue):
    typename = 'path or bool'
    def convert(self, value):
        try:
            # value may be something like 'on' or 'off'
            return BooleanValue.convert(self, value)
        except ValueError:
            return super().convert(value)


def is_server_setting(name):
    """Whether setting `name` is managed by the server"""
    if isinstance(name, ValueBase):
        name = name.name
    else:
        name = str(name)

    if name.startswith('srv.') and \
       not name.startswith('srv.timeout') and \
       not name.startswith('srv.url'):
        return True
    else:
        return False
