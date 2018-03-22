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

"""Low-level communication with the Transmission daemon"""

from ...logging import make_logger
log = make_logger(__name__)

import asyncio
import json
import textwrap
from blinker import Signal
import warnings
import async_timeout

from ..errors import (ConnectionError, TimeoutError, RPCError, AuthError, ClientError)


AUTH_ERROR_CODE = 401
CSRF_ERROR_CODE = 409
CSRF_HEADER = 'X-Transmission-Session-Id'
TIMEOUT = 10


class TransmissionRPC():
    """
    Low-level AsyncIO Transmission RPC communication

    This class handles connecting to a Transmission daemon via the RPC
    interface.  It does not implement the RPC protocol, only basic things like
    authentication, sending requests and receiving responses.  High-level RPCs
    are done in the *API classes.
    """

    def __init__(self, host='localhost', port=9091, *, tls=False, user='',
                 password='', path='/transmission/rpc', enabled=True, loop=None):
        self.loop = loop if loop is not None else asyncio.get_event_loop()
        self._host = host
        self._port = port
        self._path = path
        self._tls = tls
        self._user = user
        self._password = password
        self._headers = {'content-type': 'application/json'}
        self._session = None
        self._enabled_event = asyncio.Event(loop=loop)
        self.enabled = enabled
        self._request_lock = asyncio.Lock(loop=loop)
        self._connecting_lock = asyncio.Lock(loop=loop)
        self._connection_tested = False
        self._connection_exception = None
        self._timeout = TIMEOUT
        self._version = None
        self._rpcversion = None
        self._rpcversionmin = None
        self._on_connecting = Signal()
        self._on_connected = Signal()
        self._on_disconnected = Signal()
        self._on_error = Signal()

    def __del__(self, _warnings=warnings):
        if self._session is not None and not self._session.closed:
            _warnings.warn('disconnect() wasn\'t called', ResourceWarning)
            asyncio.ensure_future(self._session.close())

    def on(self, signal, callback, autoremove=True):
        """
        Register `callback` for `signal`

        signal: 'connecting', 'connected', 'disconnected' or 'error'
        callback: a callable that receives this instance as a positional
                  argument and, in case of the 'error' signal, the exception as
                  a keyword argument with the name 'error'

        Callbacks are automatically unsubscribed when they are
        garbage-collected.
        """
        try:
            sig = getattr(self, '_on_' + signal)
        except AttributeError:
            raise ValueError('Unknown signal: {!r}'.format(signal))
        else:
            if not isinstance(sig, Signal):
                raise ValueError('Unknown signal: {!r}'.format(signal))
            else:
                log.debug('Registering %r for %r event', callback, signal)
                sig.connect(callback, weak=autoremove)

    @property
    def version(self):
        """Version of the Transmission daemon or None if not connected"""
        return self._version

    @property
    def rpcversion(self):
        """RPC version of the Transmission daemon or None if not connected"""
        return self._rpcversion

    @property
    def rpcversionmin(self):
        """Oldest RPC version supported by Transmission daemon or None if not connected"""
        return self._rpcversionmin

    @property
    def host(self):
        """
        Hostname or IP of the Transmission RPC interface

        Setting this property calls disconnect().
        """
        return self._host
    @host.setter
    def host(self, host):
        self._host = str(host)
        asyncio.ensure_future(self.disconnect('Changing host: %r' % self._host))

    @property
    def path(self):
        """
        Path of the Transmission RPC interface

        Setting this property calls disconnect().
        """
        return self._path
    @path.setter
    def path(self, path):
        if not path or path[0] != '/':
            path = '/' + path
        self._path = path
        asyncio.ensure_future(self.disconnect('Changing path: %r' % self._path))

    @property
    def port(self):
        """
        Port of the Transmission RPC interface

        Setting this property calls disconnect().
        """
        return self._port
    @port.setter
    def port(self, port):
        self._port = int(port)
        asyncio.ensure_future(self.disconnect('Changing port: %r' % self._port))

    @property
    def user(self):
        """
        Username for authenticating to the Transmission RPC interface or empty string

        Setting this property calls disconnect().
        """
        return self._user
    @user.setter
    def user(self, user):
        self._user = str(user)
        asyncio.ensure_future(self.disconnect('Changing user: %r' % self._user))

    @property
    def password(self):
        """
        Password for authenticating to the Transmission RPC interface or empty string

        Setting this property calls disconnect().
        """
        return self._password
    @password.setter
    def password(self, password):
        self._password = str(password)
        asyncio.ensure_future(self.disconnect('Changing password: %r' % self._password))

    @property
    def tls(self):
        """
        Whether to use HTTPS for connecting to the Transmission RPC interface

        Setting this property calls disconnect().
        """
        return self._tls
    @tls.setter
    def tls(self, tls):
        self._tls = bool(tls)
        asyncio.ensure_future(self.disconnect('Changing tls: %r' % self._tls))

    @property
    def url(self):
        """Schema, host, port, and path combined as a string"""
        return '%s://%s:%d%s' % (
            'https' if self.tls else 'http', self.host, self.port, self.path)

    @property
    def timeout(self):
        """Number of seconds to try to connect before giving up"""
        return self._timeout
    @timeout.setter
    def timeout(self, timeout):
        self._timeout = float(timeout)

    @property
    def enabled(self):
        """
        Whether requests should connect

        If this is set to False, requests will wait for it to be set to True.
        This allows you to block any connection attempts until the connection
        parameters (host, user, password, etc) are specified to prevent any
        unwarranted error messages.
        """
        return self._enabled_event.is_set()
    @enabled.setter
    def enabled(self, enabled):
        if enabled and not self.enabled:
            log.debug('Enabling %r', self)
            self._enabled_event.set()
        elif not enabled and self.enabled:
            log.debug('Disabling %r', self)
            self._enabled_event.clear()
            if self.connected:
                asyncio.ensure_future(self.disconnect())

    @property
    def connected(self):
        """Return True if connected, False otherwise"""
        return (self._session is not None
                and not self._session.closed
                and self._connection_tested)

    async def connect(self):
        """
        Connect to running daemon

        If the `enabled` property is set to False, this method blocks until
        `enabled` is set to True.

        Raises RPCError, ConnectionError or AuthError.
        """
        log.debug('Connecting to %s (timeout=%ss)', self.url, self.timeout)
        self._on_connecting.send(self)

        if self._connecting_lock.locked():
            if self._connection_exception is not None:
                # The other connect() call failed
                log.debug('Found connection error: %r', self._connection_exception)
                raise self._connection_exception

            log.debug('Connection is already being established - Waiting ...')
            try:
                async with async_timeout.timeout(self.timeout):
                    await self._enabled_event.wait()
            except asyncio.TimeoutError:
                raise TimeoutError(self.timeout, self.url)
            else:
                if self.connected:
                    log.debug('Connection is up: %r', self.url)
                    return

        async with self._connecting_lock:
            log.debug('Acquired connect() lock')

            if self.connected:
                await self.disconnect('Reconnecting')

            # Block until we're enabled
            await self._enabled_event.wait()

            import aiohttp
            session_args = {'loop': self.loop}
            if self.user and self.password:
                session_args['auth'] = aiohttp.BasicAuth(self.user, self.password,
                                                         encoding='utf-8')
            self._session = aiohttp.ClientSession(**session_args)

            # Check if connection works
            log.debug('Testing connection to %s', self.url)
            try:
                test_request = json.dumps({'method':'session-get'})
                info = await self._send_request(test_request)
            except ClientError as e:
                self._connection_exception = e
                log.debug('Caught during connection test: %r', e)
                await self._reset()
                self._on_error.send(self, error=e)
                raise
            else:
                self._version = info['version']
                self._rpcversion = info['rpc-version']
                self._rpcversionmin = info['rpc-version-minimum']
                self._connection_tested = True
                self._connection_exception = None
                log.debug('Connection established: %s', self.url)
                self._on_connected.send(self)

            log.debug('Releasing connect() lock')

    async def disconnect(self, reason=None):
        """
        Disconnect if connected

        reason: Why are we disconnecting? Only used in a debugging message.
        """
        if self.connected:
            await self._reset()
            log.debug('Disconnecting from %s (%s)', self.url,
                      reason if reason is not None else 'for no reason')
            self._on_disconnected.send(self)

    async def _reset(self):
        if self._session is not None:
            await self._session.close()
        self._session = None
        self._version = None
        self._rpcversion = None
        self._rpcversionmin = None
        self._connection_tested = False

    async def _post(self, data):
        async with async_timeout.timeout(self.timeout):
            response = await self._session.post(self.url, data=data, headers=self._headers)

            if response.status == CSRF_ERROR_CODE:
                # Send request again with CSRF header
                self._headers[CSRF_HEADER] = response.headers[CSRF_HEADER]
                log.debug('Setting CSRF header: %s = %s',
                          CSRF_HEADER, response.headers[CSRF_HEADER])
                await response.release()
                return await self._post(data)

            elif response.status == AUTH_ERROR_CODE:
                await response.release()
                log.debug('Authentication failed: %s: user=%r, password=%r',
                          self.url, self.user, self.password)
                raise AuthError(self.url)

            else:
                import aiohttp
                try:
                    answer = await response.json()
                except aiohttp.ClientResponseError:
                    raise RPCError('Server sent malformed JSON: %s' % await response.text())
                else:
                    return answer

    async def _send_request(self, post_data):
        """
        Send RPC POST request to daemon

        post_data: Any valid RPC request as JSON string

        If applicable, returns response['arguments']['torrents'] or
        response['arguments'], otherwise response.

        Raises ClientError.
        """
        import aiohttp
        try:
            answer = await self._post(post_data)

        # CancelledError is raised when we're writing on a "closing
        # transport". Not sure if this happens in the real world, but it happens
        # in the tests for some reason.
        except (aiohttp.ClientError, asyncio.CancelledError) as e:
            log.debug('Caught during POST request: %r', e)
            raise ConnectionError(self.url)

        except asyncio.TimeoutError as e:
            raise TimeoutError(self.timeout, self.url)

        else:
            if answer['result'] != 'success':
                raise RPCError(answer['result'].capitalize())
            else:
                if 'arguments' in answer:
                    if 'torrents' in answer['arguments']:
                        return answer['arguments']['torrents']
                    else:
                        return answer['arguments']
                return answer

    def __getattr__(self, method):
        """
        Return asyncio coroutine that sends RPC request and returns response

        method: Any method from the RPC specs with every '-' replaced with '_'.
                For arguments see the RPC specs.

        Example:
        >>> stats = await client.session_stats()
        >>> torrents = await client.torrent_get(ids=(1,2,3), fields=('status','name'))

        Raises RPCError, ConnectionError, AuthError
        """
        async def request(arguments=None, **kwargs):
            arguments = arguments or {}

            async with self._request_lock:
                if not self.connected:
                    log.debug('Autoconnecting for %r', method)
                    await self.connect()

                arguments.update(**kwargs)
                rpc_request = json.dumps({'method'    : method.replace('_', '-'),
                                          'arguments' : arguments})

                try:
                    return await self._send_request(rpc_request)
                except ClientError as e:
                    log.debug('Caught ClientError in %r request: %r', method, e)

                    # RPCError does not mean host is unreachable, there was just a
                    # misunderstanding, so we're still connected.
                    if not isinstance(e, RPCError) and self.connected:
                        await self.disconnect(str(e))

                    self._on_error.send(self, error=e)
                    raise

        request.__name__ = method
        request.__qualname__ = method
        return request
