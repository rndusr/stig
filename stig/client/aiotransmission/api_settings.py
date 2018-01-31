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
from .. import errors
from ...utils.usertypes import (BooleanValue, IntegerValue, ListValue,
                                FloatValue, OptionValue, PathValue, SetValue,
                                StringValue, ValueBase, MultiValue)


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

    def __init__(self, *args, getter, setter, **kwargs):
        self._getter = getter
        self._setter = setter
        self._value = cls(*args, **kwargs)
    clsattrs['__init__'] = __init__

    def _set_local(self, raw_value):
        """Update internal value without setting remote value"""
        self._value.set(raw_value)
    clsattrs['_set_local'] = _set_local

    def reset(self):
        self._value.reset()
    clsattrs['reset'] = reset

    async def set_(self, value):
        # Make sure we have an actual value.  This is important when adjusting
        # numbers relatively (e.g. '+=100kB').
        if self._value.value is const.DISCONNECTED:
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

    async def get(self):
        value = (await self._getter()).value
        self._value.set(value)
        return value
    clsattrs['get'] = get

    for attr in ('name', 'value', 'description'):
        clsattrs[attr] = property(lambda self, attr=attr: getattr(self._value, attr))

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
        if self.value is None:
            await self.get()
        basedir = self.value
        await super().set(os.path.join(basedir, path))

class PathIncompleteRemoteValue(RemoteValue(BooleanValue, PathValue)):
    """Same as PathCompleteRemoteValue but also accepts booleans"""
    async def set(self, path):
        # Fetch current path if necessary before setting new path
        if self.value is None:
            await self.get()
        if self.value not in (True, False):
            basedir = self.value
            await super().set(os.path.join(basedir, path))
        else:
            await super().set(path)


# Transform key (as in `settings[key]`) to property name and vice versa
def _property_to_key(property_name):
    return property_name.replace('_', '-').replace('.', '-')
def _key_to_property(key):
    return key.replace('.', '-').replace('-', '_')

# Map names of settings to callables that return a new *RemoteValue instance
_TYPES = {}
def setting(value_cls, **kwargs):
    """Decorator for SettingsAPI properties"""
    def wrap(method):
        property_name = method.__name__
        setting_name = _property_to_key(property_name)
        def mk_value_inst(api):
            if 'description' not in kwargs:
                kwargs['description'] = getattr(SettingsAPI, property_name).__doc__
            getter = getattr(api, 'get_' + property_name)
            setter = getattr(api, 'set_' + property_name)
            return value_cls(setting_name, getter=getter, setter=setter, **kwargs)
        _TYPES[setting_name] = mk_value_inst
        return property(method)
    return wrap

class SettingsAPI(abc.Mapping, RequestPoller):
    """
    Transmission daemon settings

    `set_*` methods are coroutine functions that request value changes from the
    server.

    `get_*` methods are coroutine functions that fetch values from the server.

    Cached values that are updated every `interval` seconds are available as
    properties with 'get_' removed from the equivalent method name.  Use
    `on_change` to set a callback for interval updates.

    Values are also available as mapping items with '-' instead of '_', e.g.
    `settings['port-forwarding']`.  These values have the coroutines `set` and
    `get` methods that are identical to the `set_*` and `get_*` methods
    described above, aswell as a `value` property for synchronous access.

    To update cached values, use `update` (async) or `poll` (sync).
    """

    # Mapping methods
    def __getitem__(self, key):
        try:
            item = getattr(self, _key_to_property(key))
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
        # Generate a *RemoteValue instance for each setting
        self._cache = {
            setting_name:mk_value_inst(self)
            for setting_name,mk_value_inst in _TYPES.items()
        }
        self._raw = None    # Raw dict from 'session-get' or None if not connected
        self._srvapi = srvapi
        self._on_update = blinker.Signal()

        super().__init__(self._srvapi.rpc.session_get, interval=interval, loop=srvapi.loop)
        self.on_response(self._handle_session_get)
        self.on_error(lambda error: self.clearcache(), autoremove=False)

    def clearcache(self):
        """Clear cached settings"""
        log.debug('Clearing %s cache', type(self).__name__)
        self._raw = None
        for value in self._cache.values():
            value.reset()
        self._on_update.send(self)

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

    def _get(self, key, field_or_callable):
        """Get setting from cache if possible"""
        setting = self._cache[key]
        if setting.value is None:
            if self._raw is None:
                raw_value = const.DISCONNECTED
            elif callable(field_or_callable):
                raw_value = field_or_callable()
            else:
                raw_value = self._raw[field_or_callable]
            setting._set_local(raw_value)
        return setting


    # Rate limits

    def _rate_limit_fields(self, direction, alt):
        if alt:
            field_value = 'alt-speed-'+direction
            field_enabled = 'alt-speed-enabled'
        else:
            field_value = 'speed-limit-'+direction
            field_enabled = 'speed-limit-'+direction+'-enabled'
        return (field_value, field_enabled)

    def _rate_limit_key(self, direction, alt):
        return '%srate-limit-%s' % ('alt-' if alt else '', direction)

    def _get_rate_limit(self, direction, alt=False):
        key = self._rate_limit_key(direction, alt)
        setting = self._cache[key]
        if setting.value is None:
            field_value, field_enabled = self._rate_limit_fields(direction, alt)
            if self._raw is None:
                setting._set_local(const.DISCONNECTED)
            elif self._raw[field_enabled]:
                # Transmission reports kilobytes
                value = convert.bandwidth(self._raw[field_value]*1000, unit='byte')
                setting._set_local(value)
            else:
                setting._set_local(False)
        return setting

    async def _set_rate_limit(self, limit, direction, alt=False):
        # Make sure we have the current value in case `limit` is an adjustment
        # (e.g. '+=100kB'), which wouldn't work if `setting.value` would return
        # None.
        if self._raw is None:
            await self.update()
        self._get_rate_limit(direction, alt=alt)

        key = self._rate_limit_key(direction, alt)
        setting = self._cache[key]
        setting._set_local(limit)
        limit = setting.value

        field_value, field_enabled = self._rate_limit_fields(direction, alt)
        if limit is True:
            await self._set({field_enabled: True})
        elif limit in (const.UNLIMITED, False) or limit < 0:
            await self._set({field_enabled: False})
        else:
            raw_limit = int(int(limit.convert_to('B')) / 1000)  # Transmission expects kilobytes
            await self._set({field_enabled: True,
                             field_value: raw_limit})


    @setting(RateLimitRemoteValue)
    def rate_limit_up(self):
        """
        Upload rate limit

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

        A previously set and then disabled limit is enabled if `limit` is True.
        """
        await self._set_rate_limit(limit, 'up', alt=False)


    @setting(RateLimitRemoteValue)
    def rate_limit_down(self):
        """Download rate limit (see `rate_limit_up`)"""
        return self._get_rate_limit('down', alt=False)

    async def get_rate_limit_down(self):
        """Refresh cache and return `rate_limit_down`"""
        await self.update()
        return self.rate_limit_down

    async def set_rate_limit_down(self, limit):
        """Set download rate limit to `limit` (see `set_rate_limit_up`)"""
        await self._set_rate_limit(limit, 'down', alt=False)


    @setting(RateLimitRemoteValue)
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


    @setting(RateLimitRemoteValue)
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

    @setting(PathCompleteRemoteValue)
    def path_complete(self):
        """Where to put downloaded files"""
        return self._get('path-complete', 'download-dir')

    async def get_path_complete(self):
        """Refresh cache and return `path_complete`"""
        await self.update()
        return self.path_complete

    async def set_path_complete(self, path):
        """
        Set path to directory where downloaded files are put

        If path is relative (i.e. doesn't start with a path separator
        (e.g. '/')), it is relative to what `get_path_complete` returns.
        """
        setting = self._cache['path-complete']
        setting._set_local(path)
        await self._set({'download-dir': setting.value})


    @setting(PathIncompleteRemoteValue)
    def path_incomplete(self):
        """
        Path to directory where incomplete torrent files are put or `False` if they
        are put in `path_complete`
        """
        def get_raw_value():
            if self._raw['incomplete-dir-enabled']:
                return self._raw['incomplete-dir']
            else:
                return False
        return self._get('path-incomplete', get_raw_value)

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
        setting._set_local(path)
        request = {'incomplete-dir-enabled': setting.value is not False}
        if setting.value:
            request['incomplete-dir'] = setting.value
        await self._set(request)


    @setting(BooleanRemoteValue)
    def part_files(self):
        """Whether '.part' is appended to incomplete file names"""
        return self._get('part-files', 'rename-partial-files')

    async def get_part_files(self):
        """Refresh cache and return `part_files`"""
        await self.update()
        return self.part_files

    async def set_part_files(self, enabled):
        """See `part_files`"""
        setting = self._cache['part-files']
        setting._set_local(enabled)
        await self._set({'rename-partial-files': setting.value})


    # Network settings

    @setting(PortRemoteValue)
    def port(self):
        """Port used to communicate with peers or 'random' to pick a random port"""
        def get_raw_value():
            if self._raw['peer-port-random-on-start']:
                return const.RANDOM
            else:
                return self._raw['peer-port']
        return self._get('port', get_raw_value)

    async def get_port(self):
        """Refresh cache and return `port`"""
        await self.update()
        return self.port

    async def set_port(self, port):
        """See `port`"""
        setting = self._cache['port']
        setting._set_local(port)
        request = {'peer-port-random-on-start': setting.value is const.RANDOM}
        if setting.value is not const.RANDOM:
            request['peer-port'] = setting.value
        await self._set(request)


    @setting(BooleanRemoteValue)
    def port_forwarding(self):
        """Whether UPnP/NAT-PMP is enabled"""
        return self._get('port-forwarding', 'port-forwarding-enabled')

    async def get_port_forwarding(self):
        """Refresh cache and return `port_forwarding`"""
        await self.update()
        return self.port_forwarding

    async def set_port_forwarding(self, enabled):
        """See `port_forwarding`"""
        setting = self._cache['port-forwarding']
        setting._set_local(enabled)
        await self._set({'port-forwarding-enabled': setting.value})


    @setting(BooleanRemoteValue)
    def utp(self):
        """Whether UTP is used to discover peers"""
        return self._get('utp', 'utp-enabled')

    async def get_utp(self):
        """Refresh cache and return `utp`"""
        await self.update()
        return self.utp

    async def set_utp(self, enabled):
        """See `utp`"""
        setting = self._cache['utp']
        setting._set_local(enabled)
        await self._set({'utp-enabled': setting.value})


    @setting(BooleanRemoteValue)
    def dht(self):
        """Whether DHT is used to discover peers"""
        return self._get('dht', 'dht-enabled')

    async def get_dht(self):
        """Refresh cache and return `dht`"""
        await self.update()
        return self.dht

    async def set_dht(self, enabled):
        """See `dht`"""
        setting = self._cache['dht']
        setting._set_local(enabled)
        await self._set({'dht-enabled': setting.value})


    @setting(BooleanRemoteValue)
    def pex(self):
        """Whether PEX is used to discover peers"""
        return self._get('pex', 'pex-enabled')

    async def get_pex(self):
        """Refresh cache and return `pex`"""
        await self.update()
        return self.pex

    async def set_pex(self, enabled):
        """See `pex`"""
        setting = self._cache['pex']
        setting._set_local(enabled)
        await self._set({'pex-enabled': setting.value})


    @setting(BooleanRemoteValue)
    def lpd(self):
        """Whether Local Peer Discovery is used to discover peers"""
        return self._get('lpd', 'lpd-enabled')

    async def get_lpd(self):
        """Refresh cache and return `lpd`"""
        await self.update()
        return self.lpd

    async def set_lpd(self, enabled):
        """See `lpd`"""
        setting = self._cache['lpd']
        setting._set_local(enabled)
        await self._set({'lpd-enabled': setting.value})


    @setting(IntegerRemoteValue, min=1, max=65535)
    def peer_limit_global(self):
        """Maximum number connections for all torrents combined"""
        return self._get('peer-limit-global', 'peer-limit-global')

    async def get_peer_limit_global(self):
        """Refresh cache and return `peer_limit_global`"""
        await self.update()
        return self.peer_limit_global

    async def set_peer_limit_global(self, limit):
        """See `peer_limit_global`"""
        setting = self._cache['peer-limit-global']
        setting._set_local(limit)
        await self._set({'peer-limit-global': setting.value})


    @setting(IntegerRemoteValue, min=1, max=65535)
    def peer_limit_torrent(self):
        """Maximum number connections per torrent"""
        return self._get('peer-limit-torrent', 'peer-limit-per-torrent')

    async def get_peer_limit_torrent(self):
        """Refresh cache and return `peer_limit_torrent`"""
        await self.update()
        return self.peer_limit_torrent

    async def set_peer_limit_torrent(self, limit):
        """See `peer_limit_torrent`"""
        setting = self._cache['peer-limit-torrent']
        setting._set_local(limit)
        await self._set({'peer-limit-per-torrent': setting.value})


    # Other settings

    @setting(OptionRemoteValue, options=('required', 'preferred', 'tolerated'))
    def encryption(self):
        """
        Whether protocol encryption is used to mask BitTorrent traffic

        One of the strings 'required', 'preferred' or 'tolerated'.
        """
        return self._get('encryption', 'encryption')

    async def get_encryption(self):
        """Refresh cache and return `encryption`"""
        await self.update()
        return self.encryption

    async def set_encryption(self, encryption):
        """See `encryption`"""
        setting = self._cache['encryption']
        setting._set_local(encryption)
        await self._set({'encryption': setting.value})


    @setting(BooleanRemoteValue)
    def autostart_torrents(self):
        """Whether added torrents should be started automatically"""
        return self._get('autostart-torrents', 'start-added-torrents')

    async def get_autostart_torrents(self):
        """Refresh cache and return `autostart_torrents`"""
        await self.update()
        return self.autostart_torrents

    async def set_autostart_torrents(self, enabled):
        """See `autostart_torrents`"""
        setting = self._cache['autostart-torrents']
        setting._set_local(enabled)
        await self._set({'start-added-torrents': setting.value})
