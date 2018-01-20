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
import re
import warnings

from ..errors import (ConnectionError, RPCError, AuthError, ClientError)


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

    def __init__(self, host='localhost', port=9091, *, tls=False, user=None, password=None, loop=None):
        self.loop = loop if loop is not None else asyncio.get_event_loop()
        self._host = host
        self._port = port
        self._tls = tls
        self._user = user
        self._password = password
        self._headers = {'content-type': 'application/json'}
        self._session = None
        self._connection_lock = asyncio.Lock(loop=loop)
        self._request_lock = asyncio.Lock(loop=loop)
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
            self._session.close()

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
        self.disconnect('Changing host: %r' % self._host)

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
        self.disconnect('Changing port: %r' % self._port)

    @property
    def user(self):
        """
        Username for authenticating to the Transmission RPC interface or None

        Setting this property calls disconnect().
        """
        return self._user
    @user.setter
    def user(self, user):
        self._user = str(user)
        self.disconnect('Changing user: %r' % self._user)

    @property
    def password(self):
        """
        Password for authenticating to the Transmission RPC interface or None

        Setting this property calls disconnect().
        """
        return self._password
    @password.setter
    def password(self, password):
        self._password = str(password)
        self.disconnect('Changing password: %r' % self._password)

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
        self.disconnect('Changing tls: %r' % self._tls)

    @property
    def _url(self):
        """Host, port, user and password combined as a string (not a valid URL)"""
        return '%s://%s:%d' % (
            'https' if self.tls else 'http', self.host, self.port)

    @property
    def timeout(self):
        """Number of seconds to try to connect before giving up"""
        return self._timeout
    @timeout.setter
    def timeout(self, timeout):
        self._timeout = float(timeout)

    @property
    def connected(self):
        """Return True if connected, False otherwise"""
        return (self._session is not None
                and not self._session.closed
                and self._connection_tested)

    async def connect(self):
        """
        Connect to running daemon

        This does nothing if only one of `user` and `password` are specified.

        Raises RPCError, ConnectionError or AuthError.
        """
        if bool(self.user) != bool(self.password):
            # If user or password is set, but not both, we're likely facing a
            # race condition. By refusing to connect until both are set, we're
            # avoiding unwarranted error messages.
            log.debug('Refusing to connect with incomplete auth data: user=%r, password=%r',
                      self.user, self.password)
            return

        if self._connection_lock.locked():
            log.debug('Connection is already being established')
            while True:
                log.debug('Waiting for connection to come up ...')
                await asyncio.sleep(0.1, loop=self.loop)

                if self.connected:
                    log.debug('Connection is up: %r', self._url)
                    return

                elif self._connection_exception is not None:
                    # The other connect() call failed
                    log.debug('Found connection error: %r', self._connection_exception)
                    raise self._connection_exception

        async with self._connection_lock:
            import aiohttp
            log.debug('Acquired connect() lock')

            if self.connected:
                self.disconnect('Reconnecting')

            log.debug('Connecting to %s (timeout=%ss)', self._url, self.timeout)
            self._on_connecting.send(self)

            session_args = {'loop': self.loop}
            if self.user and self.password:
                session_args['auth'] = aiohttp.BasicAuth(self.user, self.password,
                                                         encoding='utf-8')
            self._session = aiohttp.ClientSession(**session_args)

            # Check if connection works
            log.debug('Testing connection to %s', self._url)
            try:
                test_request = json.dumps({'method':'session-get'})
                info = await self._send_request(test_request)
            except ClientError as e:
                self._connection_exception = e
                log.debug('Caught during connection test: %r', e)
                self._reset()
                self._on_error.send(self, error=e)
                raise
            else:
                self._version = info['version']
                self._rpcversion = info['rpc-version']
                self._rpcversionmin = info['rpc-version-minimum']
                self._connection_tested = True
                self._connection_exception = None
                log.debug('Connection established: %s', self._url)
                self._on_connected.send(self)

            log.debug('Releasing connect() lock')

    def disconnect(self, reason=None):
        """
        Disconnect if connected

        reason: Why are we disconnecting? Only used in a debugging message.
        """
        if self.connected:
            self._reset()
            log.debug('Disconnecting from %s (%s)', self._url,
                      reason if reason is not None else 'for no reason')
            log.debug('Calling "disconnected" callbacks for %s', self._url)
            self._on_disconnected.send(self)

    def _reset(self):
        if self._session is not None:
            self._session.close()
        self._session = None
        self._version = None
        self._rpcversion = None
        self._rpcversionmin = None
        self._connection_tested = False

    _RPC_PATH = '/transmission/rpc'
    async def _post(self, data):
        import aiohttp
        with aiohttp.Timeout(self.timeout, loop=self.loop):
            try:
                response = await self._session.post(self._url + self._RPC_PATH,
                                                    data=data,
                                                    headers=self._headers)
            except aiohttp.ClientError as e:
                log.debug('Caught during POST request: %r', e)
                raise ConnectionError(self._url)
            else:
                if response.status == CSRF_ERROR_CODE:
                    # Send request again with CSRF header
                    self._headers[CSRF_HEADER] = response.headers[CSRF_HEADER]
                    log.debug('Setting CSRF header: %s = %s',
                              CSRF_HEADER, response.headers[CSRF_HEADER])
                    await response.release()
                    return await self._post(data)

                elif response.status == AUTH_ERROR_CODE:
                    await response.release()
                    log.debug('Authentication failed: %s: user=%r, password=%r' % (
                        self._url, self.user, self.password))
                    raise AuthError(self._url)

                else:
                    try:
                        answer = await response.json()
                    except aiohttp.ClientResponseError as e:
                        text = textwrap.shorten(await response.text(),
                                                50, placeholder='...')
                        raise RPCError('Server sent malformed JSON: %s' % text)
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
        try:
            answer = await self._post(post_data)
        except OSError as e:
            log.debug('Caught OSError: %r', e)
            raise ConnectionError(self._url)
        except asyncio.TimeoutError as e:
            log.debug('Caught TimeoutError: %r', e)
            raise ConnectionError('Timeout after %ds: %s' % (self.timeout, self._url))
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
        async def request(arguments={}, **kwargs):
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
                        self.disconnect(str(e))

                    self._on_error.send(self, error=e)
                    raise

        request.__name__ = method
        request.__qualname__ = method
        return request
