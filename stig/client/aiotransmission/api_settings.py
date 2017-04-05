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

from ..poll import RequestPoller
from .. import convert
from .. import constants as const
from functools import wraps


def setting(method):
    """Decorator for SettingsAPI properties"""
    @wraps(method)
    def wrapped(self):
        if self._raw is None:
            return const.DISCONNECTED
        else:
            return method(self)
    return property(wrapped)


class SettingsAPI(abc.Mapping):
    """Transmission daemon settings

    get_* methods are coroutine functions and fetch values from the server.

    Cached values that are updated every `interval` seconds are available as
    properties with 'get_' removed from the equivalent method name.  For
    example, `get_path_incomplete` as an asyncronous method, `path_incomplete`
    is a syncronous property.

    Cached values are also available as items, e.g. settings['path-incomplete'].
    (Remove 'get_' from the method name and replace '_' with '-'.)

    To update cached values, use `update` (async) or `poll` (sync).
    """

    # Forward some methods and properties to the internal poller
    def __getattr__(self, attr):
        if attr in ('start', 'stop', 'poll', 'running'):
            return getattr(self._poller, attr)
        raise AttributeError('{!r} object has no attribute {!r}'
                             .format(type(self).__name__, attr))

    @property
    def interval(self):
        return self._poller.interval

    @interval.setter
    def interval(self, interval):
        self._poller.interval = interval


    # Mandatory abc.Mapping methods
    def __iter__(self):
        for attr in dir(self):
            if attr.startswith('get_'):
                yield attr[4:].replace('_', '-')

    def __len__(self):
        return len(tuple(iter(self)))


    def __init__(self, srvapi, interval=1):
        self._raw = None      # Raw dict from 'session-get' or None if not connected
        self._cache = {}      # Cached values convert by _AFTER_GET
        self._srvapi = srvapi
        self._get_timestamp = 0
        self._on_update = blinker.Signal()

        # autoconnect must be True so the CLI 'help' command can display
        # current values (e.g. 'help srv.limit.rate.down').
        self._poller = RequestPoller(self._srvapi.rpc.session_get,
                                     autoconnect=True,
                                     interval=interval,
                                     loop=srvapi.loop)
        self._poller.on_response(self._handle_session_get)
        self._poller.on_error(self._handle_error)

    def _handle_error(self, e):
        log.debug('Ignoring {!r}'.format(e))

    def clearcache(self):
        """Clear cached settings"""
        self._raw = None
        self._cache = {}

    def on_update(self, callback, autoremove=True):
        """Register `callback` to be called when settings have changed

        `callback` gets the instance of this class.

        If `autoremove` is True, `callback` is removed automatically when it
        is deleted.
        """
        log.debug('Registering %r to receive settings updates', callback)
        self._on_update.connect(callback, weak=autoremove)

    def _handle_session_get(self, response):
        """Request update from server"""
        log.debug('Handling periodic settings update')
        self._raw = response
        self._cache = {}
        self._on_update.send(self)

    async def update(self):
        """Request update from server"""
        log.debug('Requesting settings update')
        self._handle_session_get(await self._poller.request())

    def __getitem__(self, key):
        return getattr(self, key.replace('-', '_'))

    async def _set(self, dct):
        """Set dictionary `settings` with the 'session-set' RPC method"""
        log.debug('Setting %s', dct)
        await self._srvapi.rpc.session_set(dct)
        await self.update()


    # Rate limits

    def _rate_limit_keys(self, direction, alt):
        if alt:
            key_value = 'alt-speed-'+direction
            key_enabled = 'alt-speed-enabled'
        else:
            key_value = 'speed-limit-'+direction
            key_enabled = 'speed-limit-'+direction+'-enabled'
        return (key_value, key_enabled)

    def _get_rate_limit(self, direction, alt=False):
        key_value, key_enabled = self._rate_limit_keys(direction, alt)
        if self._raw[key_enabled]:
            # Transmission reports kilobytes
            return convert.bandwidth(self._raw[key_value]*1000)
        else:
            return const.UNLIMITED

    def _set_rate_limit(self, limit, direction, alt=False):
        key_value, key_enabled = self._rate_limit_keys(direction, alt)
        if limit in (const.ENABLED, True):
            return {key_enabled: True}
        elif limit in (const.UNLIMITED, const.DISABLED, False) or \
             isinstance(limit, (int, float)) and limit < 0:
            return {key_enabled: False}
        else:
            l = convert.bandwidth(limit)
            if l.unit == 'b':
                l /= 8  # Convert to bytes
            return {key_value: int(l/1000), key_enabled: True}


    @setting
    def rate_limit_up(self):
        """Cached upload rate limit

        Returns a Number object created by the `bandwidth` converter in the
        `convert` module or one of the constants: UNLIMITED, DISCONNECTED
        """
        if 'rate_limit_up' not in self._cache:
            self._cache['rate_limit_up'] = self._get_rate_limit('up', alt=False)
        return self._cache['rate_limit_up']

    async def get_rate_limit_up(self):
        """Refresh cache and return `rate_limit_up`"""
        await self.update()
        return self.rate_limit_up

    async def set_rate_limit_up(self, limit):
        """Set upload rate limit to `limit`

        The `bandwidth` converter in the `convert` module is used to determine
        the unit (bits or bytes) of `limit`.

        An existing limit is disabled if `limit` is False, one of the
        constants UNLIMITED or DISABLED, or a number < 0.

        An existing limit is enabled if `limit` is True or the constant
        ENABLED.
        """
        await self._set(self._set_rate_limit(limit, 'up', alt=False))


    @setting
    def rate_limit_down(self):
        """Cached download rate limit (see `rate_limit_up`)"""
        if 'rate_limit_down' not in self._cache:
            self._cache['rate_limit_down'] = self._get_rate_limit('down', alt=False)
        return self._cache['rate_limit_down']

    async def get_rate_limit_down(self):
        """Refresh cache and return `rate_limit_down`"""
        await self.update()
        return self.rate_limit_down

    async def set_rate_limit_down(self, limit):
        """Set upload rate limit to `limit` (see `set_rate_limit_up`)"""
        await self._set(self._set_rate_limit(limit, 'down', alt=False))


    @setting
    def alt_rate_limit_up(self):
        """Cached alternative upload rate limit (see `rate_limit_up`)"""
        if 'rate_limit_up' not in self._cache:
            self._cache['rate_limit_up'] = self._get_rate_limit('up', alt=True)
        return self._cache['rate_limit_up']

    async def get_alt_rate_limit_up(self):
        """Refresh cache and return `alt_rate_limit_up`"""
        await self.update()
        return self.alt_rate_limit_up

    async def set_alt_rate_limit_up(self, limit):
        """Set alternative upload rate limit to `limit` (see `set_rate_limit_up`)"""
        await self._set(self._set_rate_limit(limit, 'up', alt=True))


    @setting
    def alt_rate_limit_down(self):
        """Cached alternative download rate limit (see `rate_limit_up`)"""
        if 'rate_limit_down' not in self._cache:
            self._cache['rate_limit_down'] = self._get_rate_limit('down', alt=True)
        return self._cache['rate_limit_down']

    async def get_alt_rate_limit_down(self):
        """Refresh cache and return `alt_rate_limit_down`"""
        await self.update()
        return self.alt_rate_limit_down

    async def set_alt_rate_limit_down(self, limit):
        """Set alternative upload rate limit to `limit` (see `set_rate_limit_up`)"""
        await self._set(self._set_rate_limit(limit, 'down', alt=True))


    # Paths

    def _absolute_path(self, path, cwd):
        return os.path.normpath(os.path.join(cwd, path))

    @setting
    def path_complete(self):
        """Path to directory where torrent files are put"""
        return os.path.normpath(self._raw['download-dir'])

    async def get_path_complete(self):
        """Get path to directory where torrent files are put"""
        await self.update()
        return self.path_complete

    async def set_path_complete(self, path):
        """Set path to directory where torrent files are put

        If path is relative (i.e. doesn't start with '/'), it is relative to
        `get_path_complete`.
        """
        path = self._absolute_path(path, await self.get_path_complete())
        await self._set({'download-dir': path})

    @setting
    def path_incomplete(self):
        """Path to directory where incomplete torrent files are put"""
        if not self._raw['incomplete-dir-enabled']:
            return const.DISABLED
        else:
            return os.path.normpath(self._raw['incomplete-dir'])

    async def get_path_incomplete(self):
        """Get path to directory where incomplete torrent files are put

        Returns `constants.DISABLED` if incomplete files are stored together
        with complete ones.
        """
        await self.update()
        return self.path_incomplete

    async def set_path_incomplete(self, path):
        """Set path to directory where torrent files are put before they are complete

        If `path` is not a `str` instance, it is evaluated as a bool and this
        feature is enabled or disabled without changing the path.
        """
        if isinstance(path, str):
            await self.update()
            current_path = self._raw['incomplete-dir']
            await self._set({'incomplete-dir': self._absolute_path(path, current_path),
                             'incomplete-dir-enabled': True})
        else:
            await self._set({'incomplete-dir-enabled': bool(path)})


    # Other settings

    @setting
    def dht(self):
        """Whether DHT is used to discover peers"""
        return const.ENABLED if self._raw['dht-enabled'] else const.DISABLED

    async def get_dht(self):
        """Refresh cache and return `dht`"""
        await self.update()
        return self.dht

    async def set_dht(self, enabled):
        """Whether DHT should be used to disover peers"""
        await self._set({'dht-enabled': bool(enabled)})


    @setting
    def lpd(self):
        """Whether Local Peer Discovery is used to discover peers"""
        return const.ENABLED if self._raw['lpd-enabled'] else const.DISABLED

    async def get_lpd(self):
        """Refresh cache and return `lpd`"""
        await self.update()
        return self.lpd

    async def set_lpd(self, enabled):
        """Whether Local Peer Discovery should be used to disover peers"""
        await self._set({'lpd-enabled': bool(enabled)})


    @setting
    def encryption(self):
        """Whether protocol encryption is used to mask BitTorrent traffic

        One of the strings 'required', 'preferred' or 'tolerated'.
        """
        return self._raw['encryption']

    async def get_encryption(self):
        """Refresh cache and return `encryption`"""
        await self.update()
        return self.encryption

    async def set_encryption(self, encryption):
        """Whether encryption is 'required', 'preferred' or 'tolerated'"""
        if encryption in ('required', 'preferred', 'tolerated'):
            await self._set({'encryption': encryption})
        else:
            raise ValueError("Must be one of 'required', 'preferred', 'tolerated', not {!r}"
                             .format(encryption))
