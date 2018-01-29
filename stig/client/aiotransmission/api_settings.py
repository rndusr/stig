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

from ...logging import make_logger
log = make_logger(__name__)

import blinker
from collections import abc
import os
from functools import wraps

from ..poll import RequestPoller
from .. import convert
from .. import constants as const
from ...values import (BooleanValue, IntegerValue, ListValue, FloatValue,
                       OptionValue, PathValue, SetValue, StringValue, ValueBase,
                       MultiValue)


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

BooleanOrPathValue   = MultiValue(BooleanValue, PathValue)
RandomOrIntegerValue = MultiValue(RandomValue, IntegerValue)

class BandwidthValue(FloatValue):
    """FloatValue that passes values through `client.convert.bandwidth`"""

    valuesyntax = '%s[b|B]' % FloatValue.valuesyntax

    def convert(self, value):
        if isinstance(value, str):
            # It's important that both numbers have the same unit when adjusting
            # the current value
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


_EMPTY_CACHE = {}  # SettingsAPI._cache with default values
def setting(value_cls, **kwargs):
    """Decorator for SettingsAPI properties"""
    def wrap(method):
        setting_name = method.__name__.replace('_', '-')
        kwargs['default'] = None
        _EMPTY_CACHE[setting_name] = value_cls(setting_name, **kwargs)
        @wraps(method)
        def wrapped(self):
            if self._raw is None:
                return const.DISCONNECTED
            else:
                return method(self)
        return property(wrapped)
    return wrap


class SettingsAPI(abc.Mapping, RequestPoller):
    """Transmission daemon settings

    get_* methods are coroutine functions and fetch values from the server.

    Cached values that are updated every `interval` seconds are available as
    properties with 'get_' removed from the equivalent method name.  For
    example, `get_path_incomplete` is an asyncronous method, `path_incomplete`
    is a syncronous property.

    Cached values are also available as items, e.g. settings['path-incomplete'].
    (Remove 'get_' from the method name and replace '_' with '-'.)

    To update cached values, use `update` (async) or `poll` (sync).
    """

    # Mapping methods
    def __getitem__(self, key):
        try:
            item = getattr(self, key.replace('-', '_'))
        except AttributeError as e:
            raise KeyError(key)
        else:
            return item

    def __contains__(self, key):
        return key in self._cache

    def __iter__(self):
        return iter(self._cache)

    def __len__(self):
        return len(self._cache)


    def __init__(self, srvapi, interval=1):
        self._raw = None            # Raw dict from 'session-get' or None if not connected
        self._cache = _EMPTY_CACHE  # Cached values with proper types
        self._srvapi = srvapi
        self._get_timestamp = 0
        self._on_update = blinker.Signal()

        super().__init__(self._srvapi.rpc.session_get, interval=interval, loop=srvapi.loop)
        self.on_response(self._handle_session_get)
        self.on_error(lambda error: self.clearcache(), autoremove=False)

    def clearcache(self):
        """Clear cached settings"""
        self._raw = None
        for value in self._cache.values():
            value.reset()

    def on_update(self, callback, autoremove=True):
        """
        Register `callback` to be called when settings have changed

        `callback` gets the instance of this class.

        If `autoremove` is True, `callback` is removed automatically when it is
        deleted.
        """
        log.debug('Registering %r to receive settings updates', callback)
        self._on_update.connect(callback, weak=autoremove)

    def _handle_session_get(self, response):
        """Request update from server"""
        log.debug('Handling settings update')
        self.clearcache()
        self._raw = response
        self._on_update.send(self)

    async def update(self):
        """Request update from server"""
        log.debug('Requesting immediate settings update')
        self._handle_session_get(await self.request())

    async def _set(self, request):
        """Send 'session-set' request with dictionary `request` and call `update`"""
        log.debug('Sending session-set request: %r', request)
        await self._srvapi.rpc.session_set(request)
        await self.update()


    # Rate limits

    def _rate_limit_fields(self, direction, alt):
        if alt:
            field_value = 'alt-speed-'+direction
            field_enabled = 'alt-speed-enabled'
        else:
            field_value = 'speed-limit-'+direction
            field_enabled = 'speed-limit-'+direction+'-enabled'
        return (field_value, field_enabled)

    def _get_rate_limit(self, direction, alt=False):
        key = 'rate-limit-' + direction
        setting = self._cache[key]
        if setting.value is None:
            field_value, field_enabled = self._rate_limit_fields(direction, alt)
            if self._raw[field_enabled]:
                # Transmission reports kilobytes
                value = convert.bandwidth(self._raw[field_value]*1000, unit='byte')
                setting.set(value)
            else:
                setting.set(const.UNLIMITED)
        return setting

    async def _set_rate_limit(self, limit, direction, alt=False):
        field_value, field_enabled = self._rate_limit_fields(direction, alt)
        if limit is True:
            await self._set({field_enabled: True})
        elif limit in (const.UNLIMITED, False) or \
             isinstance(limit, (int, float)) and limit < 0:
            await self._set({field_enabled: False})
        else:
            l = convert.bandwidth(limit)
            if l.unit == 'b':
                l /= 8  # Convert bits to bytes
            await self._set({field_enabled: True,
                             field_value: int(l/1000)})  # Convert to kilobytes


    @setting(BandwidthValue)
    def rate_limit_up(self):
        """
        Cached upload rate limit

        Returns a NumberFloat object created by the `bandwidth` converter in the
        `convert` module or one of the constants: UNLIMITED, DISCONNECTED
        """
        return self._get_rate_limit('up', alt=False)

    async def get_rate_limit_up(self):
        """Refresh cache and return `rate_limit_up`"""
        await self.update()
        return self.rate_limit_up

    async def set_rate_limit_up(self, limit):
        """
        Set upload rate limit to `limit`

        The `bandwidth` converter in the `convert` module is used to determine
        the unit (bits or bytes) of `limit`.

        An existing limit is disabled if `limit` is False, the constant
        UNLIMITED, or a number < 0.

        An existing limit is enabled if `limit` is True.
        """
        await self._set_rate_limit(limit, 'up', alt=False)


    @setting(BandwidthValue)
    def rate_limit_down(self):
        """Cached download rate limit (see `rate_limit_up`)"""
        return self._get_rate_limit('down', alt=False)

    async def get_rate_limit_down(self):
        """Refresh cache and return `rate_limit_down`"""
        await self.update()
        return self.rate_limit_down

    async def set_rate_limit_down(self, limit):
        """Set upload rate limit to `limit` (see `set_rate_limit_up`)"""
        await self._set_rate_limit(limit, 'down', alt=False)


    @setting(BandwidthValue)
    def alt_rate_limit_up(self):
        """Cached alternative upload rate limit (see `rate_limit_up`)"""
        return self._get_rate_limit('up', alt=True)

    async def get_alt_rate_limit_up(self):
        """Refresh cache and return `alt_rate_limit_up`"""
        await self.update()
        return self.alt_rate_limit_up

    async def set_alt_rate_limit_up(self, limit):
        """Set alternative upload rate limit to `limit` (see `set_rate_limit_up`)"""
        await self._set_rate_limit(limit, 'up', alt=True)


    @setting(BandwidthValue)
    def alt_rate_limit_down(self):
        """Cached alternative download rate limit (see `rate_limit_up`)"""
        return self._get_rate_limit('down', alt=True)

    async def get_alt_rate_limit_down(self):
        """Refresh cache and return `alt_rate_limit_down`"""
        await self.update()
        return self.alt_rate_limit_down

    async def set_alt_rate_limit_down(self, limit):
        """Set alternative upload rate limit to `limit` (see `set_rate_limit_up`)"""
        await self._set_rate_limit(limit, 'down', alt=True)



    # Paths

    def _absolute_path(self, path, basedir):
        return os.path.normpath(os.path.join(basedir, path))


    @setting(PathValue)
    def path_complete(self):
        """Path to directory where torrent files are put"""
        setting = self._cache['path-complete']
        if setting.value is None:
            setting.set(self._raw['download-dir'])
        return setting

    async def get_path_complete(self):
        """Get path to directory where torrent files are put"""
        await self.update()
        return self.path_complete

    async def set_path_complete(self, path):
        """
        Set path to directory where torrent files are put

        If path is relative (i.e. doesn't start with '/'), it is relative to
        `get_path_complete`.
        """
        base_path = (await self.get_path_complete()).value
        abs_path = self._absolute_path(path, base_path)
        self._cache['path-complete'].set(abs_path)
        await self._set({'download-dir': self._cache['path-complete'].value})


    @setting(BooleanOrPathValue)
    def path_incomplete(self):
        """
        Path to directory where incomplete torrent files are put or `False` if they
        are put in `path_complete`
        """
        setting = self._cache['path-incomplete']
        if setting.value is None:
            if self._raw['incomplete-dir-enabled']:
                setting.set(self._raw['incomplete-dir'])
            else:
                setting.set(False)
        print(f'path_incomplete: {setting!r}')
        return setting

    async def get_path_incomplete(self):
        """Refresh cache and return `path_incomplete`"""
        await self.update()
        return self.path_incomplete

    async def set_path_incomplete(self, path):
        """
        Set path to directory where incomplete torrent files are put

        If `path` is not a `str` instance, it is evaluated as a bool and this
        feature is enabled or disabled accordingly without changing the path.
        """
        setting = self._cache['path-incomplete']
        print(f'path: {path!r}')
        setting.set(path)
        path = setting.value
        if isinstance(path, str):
            base_path = (await self.get_path_complete()).value
            abs_path = self._absolute_path(path, base_path)
            setting.set(abs_path)
            request = {'incomplete-dir': abs_path,
                       'incomplete-dir-enabled': True}
        else:
            request = {'incomplete-dir-enabled': bool(path)}
        await self._set(request)


    @setting(BooleanValue)
    def part_files(self):
        """Whether ".part" is appended to incomplete file names"""
        setting = self._cache['part-files']
        if setting.value is None:
            setting.set(self._raw['rename-partial-files'])
        return setting

    async def get_part_files(self):
        """Refresh cache and return `part_files`"""
        await self.update()
        return self.part_files

    async def set_part_files(self, enabled):
        """See `part_files`"""
        self._cache['part-files'].set(enabled)
        await self._set({'rename-partial-files': self._cache['part-files'].value})



    # Network settings

    @setting(RandomOrIntegerValue)
    def port(self):
        """Port used to communicate with peers or 'random' to pick a random port"""
        setting = self._cache['port']
        if setting.value is None:
            if self._raw['peer-port-random-on-start']:
                raw_value = const.RANDOM
            else:
                raw_value = self._raw['peer-port']
            setting.set(raw_value)
        return setting

    async def get_port(self):
        """Refresh cache and return `port`"""
        await self.update()
        return self.port

    async def set_port(self, port):
        """See `port`"""
        setting = self._cache['port']
        setting.set(port)
        request = {'peer-port-random-on-start': setting.value is const.RANDOM}
        if setting.value is not const.RANDOM:
            request['peer-port'] = setting.value
        await self._set(request)


    @setting(BooleanValue)
    def port_forwarding(self):
        """Whether UPnP/NAT-PMP is enabled"""
        setting = self._cache['port-forwarding']
        if setting.value is None:
            setting.set(self._raw['port-forwarding-enabled'])
        return setting

    async def get_port_forwarding(self):
        """Refresh cache and return `port_forwarding`"""
        await self.update()
        return self.port_forwarding

    async def set_port_forwarding(self, enabled):
        """See `port_forwarding`"""
        self._cache['port-forwarding'].set(enabled)
        await self._set({'port-forwarding-enabled': self._cache['port-forwarding'].value})


    @setting(BooleanValue)
    def utp(self):
        """Whether UTP is used to discover peers"""
        setting = self._cache['utp']
        if setting.value is None:
            setting.set(self._raw['utp-enabled'])
        return setting

    async def get_utp(self):
        """Refresh cache and return `utp`"""
        await self.update()
        return self.utp

    async def set_utp(self, enabled):
        """See `utp`"""
        self._cache['utp'].set(enabled)
        await self._set({'utp-enabled': self._cache['utp'].value})


    @setting(BooleanValue)
    def dht(self):
        """Whether DHT is used to discover peers"""
        setting = self._cache['dht']
        if setting.value is None:
            setting.set(self._raw['dht-enabled'])
        return setting

    async def get_dht(self):
        """Refresh cache and return `dht`"""
        await self.update()
        return self.dht

    async def set_dht(self, enabled):
        """See `dht`"""
        self._cache['dht'].set(enabled)
        await self._set({'dht-enabled': self._cache['dht'].value})


    @setting(BooleanValue)
    def pex(self):
        """Whether Peer Exchange is used to discover peers"""
        setting = self._cache['pex']
        if setting.value is None:
            setting.set(self._raw['pex-enabled'])
        return setting

    async def get_pex(self):
        """Refresh cache and return `pex`"""
        await self.update()
        return self.pex

    async def set_pex(self, enabled):
        """See `pex`"""
        self._cache['pex'].set(enabled)
        await self._set({'pex-enabled': self._cache['pex'].value})


    @setting(BooleanValue)
    def lpd(self):
        """Whether Local Peer Discovery is used to discover peers"""
        setting = self._cache['lpd']
        if setting.value is None:
            setting.set(self._raw['lpd-enabled'])
        return setting

    async def get_lpd(self):
        """Refresh cache and return `lpd`"""
        await self.update()
        return self.lpd

    async def set_lpd(self, enabled):
        """See `lpd`"""
        self._cache['lpd'].set(enabled)
        await self._set({'lpd-enabled': self._cache['lpd'].value})


    @setting(IntegerValue, min=1, max=65535)
    def peer_limit_global(self):
        """Maximum number connections for all torrents combined"""
        setting = self._cache['peer-limit-global']
        if setting.value is None:
            setting.set(self._raw['peer-limit-global'])
        return setting

    async def get_peer_limit_global(self):
        """Refresh cache and return `peer_limit_global`"""
        await self.update()
        return self.peer_limit_global

    async def set_peer_limit_global(self, limit):
        """See `peer_limit_global`"""
        self._cache['peer-limit-global'].set(limit)
        await self._set({'peer-limit-global': self._cache['peer-limit-global'].value})


    @setting(IntegerValue, min=1, max=65535)
    def peer_limit_torrent(self):
        """Maximum number connections per torrent"""
        setting = self._cache['peer-limit-torrent']
        if setting.value is None:
            setting.set(self._raw['peer-limit-per-torrent'])
        return setting

    async def get_peer_limit_torrent(self):
        """Refresh cache and return `peer_limit_torrent`"""
        await self.update()
        return self.peer_limit_torrent

    async def set_peer_limit_torrent(self, limit):
        """See `peer_limit_torrent`"""
        self._cache['peer-limit-torrent'].set(limit)
        await self._set({'peer-limit-per-torrent': self._cache['peer-limit-torrent'].value})


    # Other settings

    @setting(OptionValue, options=('required', 'preferred', 'tolerated'))
    def encryption(self):
        """
        Whether protocol encryption is used to mask BitTorrent traffic

        One of the strings 'required', 'preferred' or 'tolerated'.
        """
        setting = self._cache['encryption']
        if setting.value is None:
            setting.set(self._raw['encryption'])
        return setting

    async def get_encryption(self):
        """Refresh cache and return `encryption`"""
        await self.update()
        return self.encryption

    async def set_encryption(self, encryption):
        """See `encryption`"""
        self._cache['encryption'].set(encryption)
        await self._set({'encryption': self._cache['encryption'].value})


    @setting(BooleanValue)
    def autostart_torrents(self):
        """Whether added torrents should be started automatically"""
        setting = self._cache['autostart-torrents']
        if setting.value is None:
            setting.set(self._raw['start-added-torrents'])
        return setting

    async def get_autostart_torrents(self):
        """Refresh cache and return `autostart_torrents`"""
        await self.update()
        return self.autostart_torrents

    async def set_autostart_torrents(self, enabled):
        """See `autostart_torrents`"""
        self._cache['autostart-torrents'].set(enabled)
        await self._set({'start-added-torrents': self._cache['autostart-torrents'].value})
