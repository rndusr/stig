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
from types import SimpleNamespace
import os

from ..poll import RequestPoller
from ..utils import (convert, const, Bool, Option, Int, Path, BoolOrPath, BoolOrBandwidth)


# Transform key (as in `settings[key]`) to property name and vice versa
def _key2property(key):
    return key.replace('.', '_')
def _property2key(property_name):
    return property_name.replace('_', '.')


_SETTINGS = {}
def _setting(value_cls, **kwargs):
    """Decorator for SettingsAPI properties"""
    def wrap(method):
        property_name = method.__name__
        setting_name = _property2key(property_name)
        description = kwargs.pop('description') if 'description' in kwargs else None
        converter = value_cls.partial(**kwargs)

        def get_typespec(api):
            return SimpleNamespace(
                converter=converter,
                description=description or getattr(type(api), property_name).__doc__)
        _SETTINGS[setting_name] = get_typespec

        return property(method)
    return wrap


class SettingsAPI(abc.Mapping, RequestPoller):
    """
    Transmission daemon settings

    `set_*` methods are coroutine functions that request value changes from the
    server.

    `get_*` methods are coroutine functions that fetch values from the server.

    Cached values, which are updated every `interval` seconds, are available as
    properties with 'get_' removed from the equivalent method name
    (e.g. api.get_port() -> api.port).

    Use `on_change` to set a callback for interval updates.

    Cached values are also available as mapping items with '.' instead of '_',
    e.g.  `settings['path.incomplete']`.

    To update cached values, use `update` (async) or `poll` (sync).
    """

    # Mapping methods
    def __getitem__(self, key):
        try:
            item = getattr(self, _key2property(key))
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
        self._cache = {}
        self._descriptions = {}
        self._converters = {}
        for setting,get_typespec in _SETTINGS.items():
            typespec = get_typespec(self)
            self._cache[setting] = None
            self._converters[setting] = typespec.converter
            self._descriptions[setting] = typespec.description

        self._raw = None    # Raw dict from 'session-get' or None if not connected
        self._srvapi = srvapi
        self._on_update = blinker.Signal()

        super().__init__(self._srvapi.rpc.session_get, interval=interval, loop=srvapi.loop)
        self.on_response(self._handle_session_get)
        self.on_error(self._handle_error)

    def description(self, name):
        """Return setting's description"""
        return self._descriptions[name]

    def syntax(self, name):
        """Return setting's value syntax"""
        return self._converters[name].syntax

    def default(self, name):
        # Maintain consistency with local Settings class
        return const.DISCONNECTED

    async def update(self):
        """Request update from server"""
        log.debug('Requesting immediate settings update')
        self._handle_session_get(await self.request())

    def _handle_session_get(self, response):
        """Request update from server"""
        log.debug('Handling settings update')
        self.clearcache(run_callbacks=False)
        self._raw = response
        self._on_update.send(self)

    def _handle_error(self, error):
        self.clearcache(run_callbacks=True)

    def clearcache(self, run_callbacks=True):
        """
        Clear cached settings

        update: Whether to run `on_update` callbacks
        """
        log.debug('Clearing %s cache', type(self).__name__)
        self._raw = None
        for setting in self._cache:
            self._cache[setting] = None
        if run_callbacks:
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

    async def get(self, key):
        """Same as __getitem__ but refresh cache first"""
        if key not in self:
            raise ValueError(key)
        else:
            method = getattr(self, 'get_' + _key2property(key))
            return await method()

    async def set(self, key, value):
        """Asynchronous replacement for __setitem__"""
        if key not in self:
            raise ValueError(key)
        else:
            method = getattr(self, 'set_' + _key2property(key))
            await method(value)

    def _get(self, key, field_or_callable):
        """Get setting from cache if possible"""
        if self._cache[key] is None:
            if self._raw is None:
                self._cache[key] = const.DISCONNECTED
            elif callable(field_or_callable):
                self._cache[key] = self._converters[key](field_or_callable())
            else:
                self._cache[key] = self._converters[key](self._raw[field_or_callable])
        return self._cache[key]

    async def _set(self, request):
        """Send 'session-set' request with dictionary `request` and call `update`"""
        log.debug('Sending session-set request: %r', request)
        await self._srvapi.rpc.session_set(request)
        await self.update()


    @_setting(Bool)
    def autostart(self):
        """Whether added torrents are started automatically"""
        return self._get('autostart', 'start-added-torrents')

    async def get_autostart(self):
        """Refresh cache and return `autostart`"""
        await self.update()
        return self.autostart

    async def set_autostart(self, enabled):
        """See `autostart`"""
        value = self._converters['autostart'](enabled)
        await self._set({'start-added-torrents': bool(value)})


    # Network settings

    @_setting(Int, min=0, max=65535, prefix='none')
    def port(self):
        """Port used to communicate with peers"""
        return self._get('port', 'peer-port')

    async def get_port(self):
        """Refresh cache and return `port`"""
        await self.update()
        return self.port

    async def set_port(self, port):
        """See `port`"""
        value = self._converters['port'](port)
        await self._set({'peer-port': value,
                         'peer-port-random-on-start': False})


    @_setting(Bool)
    def port_random(self):
        """Whether to pick a random port when the daemon starts"""
        return self._get('port.random', 'peer-port-random-on-start')

    async def get_port_random(self):
        """Refresh cache and return `port_random`"""
        await self.update()
        return self.port_random

    async def set_port_random(self, port_random):
        """See `port_random`"""
        value = self._converters['port.random'](port_random)
        await self._set({'peer-port-random-on-start': bool(value)})


    @_setting(Bool)
    def port_forwarding(self):
        """Whether to autoconfigure port-forwarding via UPnP/NAT-PMP"""
        return self._get('port.forwarding', 'port-forwarding-enabled')

    async def get_port_forwarding(self):
        """Refresh cache and return `port_forwarding`"""
        await self.update()
        return self.port_forwarding

    async def set_port_forwarding(self, enabled):
        """See `port_forwarding`"""
        value = self._converters['port.forwarding'](enabled)
        await self._set({'port-forwarding-enabled': bool(value)})


    @_setting(Int, min=1, max=65535)
    def limit_peers_global(self):
        """Maximum number of connections for all torrents combined"""
        return self._get('limit.peers.global', 'peer-limit-global')

    async def get_limit_peers_global(self):
        """Refresh cache and return `limit_peers_global`"""
        await self.update()
        return self.limit_peers_global

    async def set_limit_peers_global(self, limit):
        """See `limit_peers_global`"""
        value = self._converters['limit.peers.global'](limit)
        await self._set({'peer-limit-global': value})


    @_setting(Int, min=1, max=65535)
    def limit_peers_torrent(self):
        """Maximum number of connections per torrent"""
        return self._get('limit.peers.torrent', 'peer-limit-per-torrent')

    async def get_limit_peers_torrent(self):
        """Refresh cache and return `limit_peers_torrent`"""
        await self.update()
        return self.limit_peers_torrent

    async def set_limit_peers_torrent(self, limit):
        """See `limit_peers_torrent`"""
        value = self._converters['limit.peers.torrent'](limit)
        await self._set({'peer-limit-per-torrent': value})


    @_setting(Option, options=('required', 'preferred', 'tolerated'),
              description='Protocol encryption policy; "required", "preferred" or "tolerated"')
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
        value = self._converters['encryption'](encryption)
        await self._set({'encryption': value})


    @_setting(Bool)
    def utp(self):
        """Whether to use µTP to mitigate latency issues"""
        return self._get('utp', 'utp-enabled')

    async def get_utp(self):
        """Refresh cache and return `utp`"""
        await self.update()
        return self.utp

    async def set_utp(self, enabled):
        """See `utp`"""
        value = self._converters['utp'](enabled)
        await self._set({'utp-enabled': bool(value)})


    @_setting(Bool)
    def dht(self):
        """Whether to use DHT to discover peers for public torrents"""
        return self._get('dht', 'dht-enabled')

    async def get_dht(self):
        """Refresh cache and return `dht`"""
        await self.update()
        return self.dht

    async def set_dht(self, enabled):
        """See `dht`"""
        value = self._converters['dht'](enabled)
        await self._set({'dht-enabled': bool(value)})


    @_setting(Bool)
    def pex(self):
        """Whether to use PEX to discover peers for public torrents"""
        return self._get('pex', 'pex-enabled')

    async def get_pex(self):
        """Refresh cache and return `pex`"""
        await self.update()
        return self.pex

    async def set_pex(self, enabled):
        """See `pex`"""
        value = self._converters['pex'](enabled)
        await self._set({'pex-enabled': bool(value)})


    @_setting(Bool)
    def lpd(self):
        """Whether to use LPD to discover peers for public torrents"""
        return self._get('lpd', 'lpd-enabled')

    async def get_lpd(self):
        """Refresh cache and return `lpd`"""
        await self.update()
        return self.lpd

    async def set_lpd(self, enabled):
        """See `lpd`"""
        value = self._converters['lpd'](enabled)
        await self._set({'lpd-enabled': bool(value)})


    # Local Filesystem settings

    @_setting(Path)
    def path_complete(self):
        """Where to put downloaded files"""
        return self._get('path.complete', 'download-dir')

    async def get_path_complete(self):
        """Refresh cache and return `path_complete`"""
        await self.update()
        return self.path_complete

    async def set_path_complete(self, path):
        """
        Set download directory files

        If path is relative (i.e. doesn't start with a path separator
        (e.g. '/')), it is relative to what `get_path_complete` returns.
        """
        value = self._converters['path.complete'](path)
        if not value.startswith(os.sep):
            current_path = await self.get_path_complete()
            value = os.path.join(current_path, value)
        await self._set({'download-dir': value})


    @_setting(BoolOrPath,
              description='Where to put partially downloaded files')
    def path_incomplete(self):
        """
        Path to incomplete files or Bool(<False>) to put them in `path_complete`
        """
        def get_raw_value():
            if self._raw['incomplete-dir-enabled']:
                return self._raw['incomplete-dir']
            else:
                return False
        return self._get('path.incomplete', get_raw_value)

    async def get_path_incomplete(self):
        """Refresh cache and return `path_incomplete`"""
        await self.update()
        return self.path_incomplete

    async def set_path_incomplete(self, path):
        """
        Set path to incomplete files or Bool(<False>)

        If `path` is not a `str` instance, it is evaluated as a bool and this
        feature is enabled or disabled accordingly without changing the path.

        If path is relative (i.e. doesn't start with a path separator
        (e.g. '/')), it is relative to what `get_path_incomplete` returns.
        """
        value = self._converters['path.incomplete'](path)
        request = {'incomplete-dir-enabled': bool(value)}
        if isinstance(value, Path):
            if not value.startswith(os.sep):
                current_path = await self.get_path_incomplete()
                value = os.path.join(current_path, value)
            request['incomplete-dir'] = str(value)
        await self._set(request)


    @_setting(Bool)
    def files_part(self):
        """Whether ".part" is appended to incomplete files"""
        return self._get('files.part', 'rename-partial-files')

    async def get_files_part(self):
        """Refresh cache and return `files_part`"""
        await self.update()
        return self.files_part

    async def set_files_part(self, enabled):
        """See `files_part`"""
        value = self._converters['files.part'](enabled)
        await self._set({'rename-partial-files': bool(value)})


    # Rate limits

    @staticmethod
    def _limit_rate_fields(direction, alt):
        if alt:
            field_value = 'alt-speed-'+direction
            field_enabled = 'alt-speed-enabled'
        else:
            field_value = 'speed-limit-'+direction
            field_enabled = 'speed-limit-'+direction+'-enabled'
        return (field_value, field_enabled)

    @staticmethod
    def _limit_rate_key(direction, alt):
        if alt:
            return 'limit.rate.alt.%s' % direction
        else:
            return 'limit.rate.%s' % direction

    def _get_limit_rate(self, direction, alt=False):
        key = self._limit_rate_key(direction, alt)
        if self._cache[key] is None:
            field_value, field_enabled = self._limit_rate_fields(direction, alt)
            if self._raw is None:
                self._cache[key] = const.DISCONNECTED
            elif self._raw[field_enabled]:
                # Transmission reports kilobytes
                self._cache[key] = self._converters[key](
                    convert.bandwidth(self._raw[field_value]*1000, unit='B'))
            else:
                self._cache[key] = const.UNLIMITED
        return self._cache[key]

    async def _set_limit_rate(self, limit, direction, alt=False):
        key = self._limit_rate_key(direction, alt)
        field_value, field_enabled = self._limit_rate_fields(direction, alt)
        limit = self._converters[key](limit)
        if isinstance(limit, Bool):
            await self._set({field_enabled: bool(limit)})
        elif 0 <= limit < float('inf'):
            raw_limit = round(round(limit.copy(convert_to='B')) / 1000)
            await self._set({field_enabled: True,
                             field_value: raw_limit})
        else:
            await self._set({field_enabled: False})

    async def _adjust_limit_rate(self, adjustment, direction, alt=False):
        key = self._limit_rate_key(direction, alt)
        field_value, field_enabled = self._limit_rate_fields(direction, alt)
        prop_name = _key2property(key)

        current_limit = getattr(self, prop_name)
        if current_limit is const.DISCONNECTED:
            current_limit = await getattr(self, 'get_' + prop_name)()
        adjustment = self._converters[key](adjustment)
        new_limit = BoolOrBandwidth.adjust(current_limit, adjustment)
        await self._set_limit_rate(new_limit, direction, alt=alt)

    @_setting(BoolOrBandwidth,
              description='Global upload rate limit')
    def limit_rate_up(self):
        """
        Upload rate limit

        This uses the application-wide `stig.utils.convert` module to get
        consistent units and unit prefixes.
        """
        return self._get_limit_rate('up', alt=False)

    async def get_limit_rate_up(self):
        """Refresh cache and return `limit_rate_up`"""
        await self.update()
        return self.limit_rate_up

    async def set_limit_rate_up(self, limit):
        """
        Set upload rate limit to `limit` (see also `limit_rate_up`)

        An existing limit is disabled if `limit` is False, the constant
        UNLIMITED, or a number < 0.

        A previously set and then disabled limit is enabled if `limit` is True.
        """
        await self._set_limit_rate(limit, 'up', alt=False)

    async def adjust_limit_rate_up(self, limit):
        """Adjust current upload rate limit by `limit` (positive or negative number)"""
        await self._adjust_limit_rate(limit, 'up', alt=False)


    @_setting(BoolOrBandwidth,
              description='Global download rate limit')
    def limit_rate_down(self):
        """Download rate limit (see `limit_rate_up`)"""
        return self._get_limit_rate('down', alt=False)

    async def get_limit_rate_down(self):
        """Refresh cache and return `limit_rate_down`"""
        await self.update()
        return self.limit_rate_down

    async def set_limit_rate_down(self, limit):
        """Set download rate limit to `limit` (see `set_limit_rate_up`)"""
        await self._set_limit_rate(limit, 'down', alt=False)

    async def adjust_limit_rate_down(self, limit):
        """Adjust current download rate limit by `limit` (positive or negative number)"""
        await self._adjust_limit_rate(limit, 'down', alt=False)


    @_setting(BoolOrBandwidth,
              description='Alternative global upload rate limit')
    def limit_rate_alt_up(self):
        """Alternative upload rate limit (see `limit_rate_up`)"""
        return self._get_limit_rate('up', alt=True)

    async def get_limit_rate_alt_up(self):
        """Refresh cache and return `limit_rate_alt_up`"""
        await self.update()
        return self.limit_rate_alt_up

    async def set_limit_rate_alt_up(self, limit):
        """Set alternative upload rate limit to `limit` (see `set_limit_rate_up`)"""
        await self._set_limit_rate(limit, 'up', alt=True)

    async def adjust_limit_rate_alt_up(self, limit):
        """Adjust current alternative upload rate limit by `limit`"""
        await self._adjust_limit_rate(limit, 'up', alt=True)


    @_setting(BoolOrBandwidth,
              description='Alternative global download rate limit')
    def limit_rate_alt_down(self):
        """Alternative download rate limit (see `limit_rate_up`)"""
        return self._get_limit_rate('down', alt=True)

    async def get_limit_rate_alt_down(self):
        """Refresh cache and return `limit_rate_alt_down`"""
        await self.update()
        return self.limit_rate_alt_down

    async def set_limit_rate_alt_down(self, limit):
        """Set alternative upload rate limit to `limit` (see `set_limit_rate_up`)"""
        await self._set_limit_rate(limit, 'down', alt=True)

    async def adjust_limit_rate_alt_down(self, limit):
        """Adjust current alternative download rate limit by `limit`"""
        await self._adjust_limit_rate(limit, 'down', alt=True)
