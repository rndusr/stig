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
import aiohttp
import json
import textwrap
from blinker import Signal
from urllib.parse import urlsplit
import re
import warnings

from ..errors import (URLParserError, ConnectionError, RPCError, AuthError, ClientError)
from ..utils import URL


AUTH_ERROR_CODE = 401
CSRF_ERROR_CODE = 409
CSRF_HEADER = 'X-Transmission-Session-Id'
TIMEOUT = 10


class TransmissionURL(URL):
    DEFAULT = URL('http://localhost:9091/transmission/rpc')

    def __new__(cls, url=str(DEFAULT)):
        obj = super().__new__(cls, url)

        # Fill in defaults
        for attr in ('scheme', 'host', 'port', 'path'):
            if getattr(obj, attr) is None:
                setattr(obj, attr, getattr(cls.DEFAULT, attr))

        return obj


class TransmissionRPC():
    """Low-level AsyncIO Transmission RPC communication

    This class handles connecting to a Transmission daemon via the RPC
    interface.  It does not implement the RPC protocol, only basic things like
    authentication, sending requests and receiving responses.  High-level RPC
    are done in the *API classes.
    """

    def __init__(self, url='localhost:9091', loop=None):
        # Use double underscores because TransmissionAPI inherits from this
        # class; this way, we don't have to worry about name collisions.
        self.loop = loop if loop is not None else asyncio.get_event_loop()
        self.__url = TransmissionURL(url)
        self.__headers = {'content-type': 'application/json'}
        self.__session = None
        self.__connect_exception = None
        self.__connection_lock = asyncio.Lock(loop=loop)
        self.__request_lock = asyncio.Lock(loop=loop)
        self.__connection_tested = False
        self.__timeout = TIMEOUT
        self.__version = None
        self.__rpcversion = None
        self.__rpcversionmin = None
        self.__on_connecting = Signal()
        self.__on_connected = Signal()
        self.__on_disconnected = Signal()
        self.__on_error = Signal()

    def __del__(self, _warnings=warnings):
        if self.__session is not None and not self.__session.closed:
            _warnings.warn('disconnect() wasn\'t called', ResourceWarning)
            self.__session.close()

    def on(self, signal, callback, autoremove=True):
        """Register `callback` for `signal`

        signal: 'connecting', 'connected', 'disconnected' or 'error'
        callback: a callable that receives the RPC URL and, for 'error', the
                  exception

        Callbacks are automatically unsubscribed when they are
        garbage-collected.
        """
        try:
            # Attributes with '__' become '_Classname__attribute'
            sig = getattr(self, '_TransmissionRPC__on_' + signal)
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
        return self.__version

    @property
    def rpcversion(self):
        """RPC version of the Transmission daemon or None if not connected"""
        return self.__rpcversion

    @property
    def rpcversionmin(self):
        """Oldest RPC version supported by Transmission daemon or None if not connected"""
        return self.__rpcversionmin

    @property
    def url(self):
        """Transmission's RPC URL without the path"""
        return self.__url

    @url.setter
    def url(self, url):
        self.__url = TransmissionURL(url)

    @property
    def timeout(self):
        """Number of seconds to try to connect before giving up"""
        return self.__timeout

    @timeout.setter
    def timeout(self, timeout):
        self.__timeout = timeout

    @property
    def connected(self):
        """Return True if connected, False otherwise"""
        return self.__session is not None and not self.__session.closed \
            and self.__connection_tested

    async def connect(self, url=None, timeout=None):
        """Connect to running daemon

        url: URL to the Transmission RPC interface or None for default
             (see TransmissionURL)
        timeout: Maximum number of seconds before attempt to connect fails

        Raises RPCError, ConnectionError or AuthError.
        """
        if self.__connection_lock.locked():
            # Someone else is currently connecting.  Wait for them to finish.
            log.debug('Waiting for other connection to establish')
            await self.__connection_lock.acquire()
            log.debug('Other connect() call finished')
            self.__connection_lock.release()

            # Check if connection has the url we want
            if url is not None and self.url != TransmissionURL(url):
                log.debug('Reconnecting because %s != %s', self.__url, url)
                await self.connect(url=url, timeout=timeout)

            # The other connect() call croaked for some reason, and our caller
            # expects the same exception.  Calling connect() again should
            # raise the same error, but that's too much recursion for my tiny,
            # little mind.
            elif self.__connect_exception is not None:
                log.debug('Raising exception of other connect() call: %r', self.__connect_exception)
                raise self.__connect_exception

            # Looks like we're connected.  Our intended timeout may differ
            # from what the previous call set, but there's no need to
            # re-connect.
            elif timeout is not None and self.timeout != timeout:
                self.timeout = timeout

        else:
            async with self.__connection_lock:
                log.debug('Acquired connect() lock')
                if timeout is not None:
                    self.timeout = timeout

                # Reconnect if URL is specified
                if url is not None:
                    if self.connected:
                        await self.disconnect('reconnecting to %s' % url)
                    self.__url = TransmissionURL(url)
                self.__on_connecting.send(self.url)

                # If we're not connected (because new URL or we weren't
                # connected in the first place), create new session.
                if not self.connected:
                    log.debug('Connecting to %s (timeout=%ss)', self.url, self.timeout)
                    session_args = {'loop': self.loop}
                    # TODO: Remove this check when aiohttp2 is common.
                    if aiohttp.__version__[0] == '2':
                        session_args['connector'] = aiohttp.TCPConnector(limit_per_host=1)
                    if self.__url.has_auth:
                        session_args['auth'] = aiohttp.BasicAuth(self.__url.user,
                                                                 self.__url.password)

                    # It is possible that the connection test below was
                    # interrupted, which leaves us with self.connected returning
                    # False (self.__connection_tested is still False), but an
                    # unclosed ClientSession in self.__session.  We must close
                    # it before consigning it to the garbage collector so it
                    # doesn't throw warnings around.
                    if self.__session is not None and not self.__session.closed:
                        log.debug('Closing leftover ClientSession before creating a new one: %r', self.__session)
                        self.__session.close()
                    self.__session = aiohttp.ClientSession(**session_args)
                    skip_connected_callback = False
                else:
                    log.debug('Already connected to %s', self.url)
                    skip_connected_callback = True

                # Check if connection works.  If we were already connected, we
                # still want to check if the old connection still works, but
                # we don't want to report the working connection again to
                # callbacks (skip_connected_callback).
                log.debug('Initializing new connection to %s', self.url)
                try:
                    test_request = json.dumps({'method':'session-get'})
                    info = await self.__send_request(test_request)
                except ClientError as e:
                    log.debug('Caught during initialization: %r', e)
                    self.__connect_exception = e
                    await self.__reset()
                    self.__on_error.send(self.__url, error=e)
                    raise
                else:
                    self.__version = info['version']
                    self.__rpcversion = info['rpc-version']
                    self.__rpcversionmin = info['rpc-version-minimum']
                    self.__connection_tested = True
                    self.__connect_exception = None
                    log.debug('Connection established: %s', self.url)
                    if not skip_connected_callback:
                        self.__on_connected.send(self.__url)

                log.debug('Releasing connect() lock')

    async def disconnect(self, reason=None):
        """Disconnect if connected

        reason: Why are we disconnecting? Only used in a debugging message.
        """
        if self.connected:
            await self.__reset()
            log.debug('Disconnecting from %s (%s)',
                      self.url, reason if reason is not None else 'for no reason')
            log.debug('Calling "disconnected" callbacks for %s', self.url)
            self.__on_disconnected.send(self.__url)

    async def __reset(self):
        if self.__session is not None:
            self.__session.close()
        self.__session = None
        self.__version = None
        self.__rpcversion = None
        self.__rpcversionmin = None
        self.__connection_tested = False

    async def __post(self, data):
        with aiohttp.Timeout(self.timeout, loop=self.loop):
            try:
                response = await self.__session.post(str(self.__url), data=data, headers=self.__headers)
            except aiohttp.ClientError as e:
                log.debug('Caught during POST request: %r', e)
                raise ConnectionError(str(self.url))
            else:
                if response.status == CSRF_ERROR_CODE:
                    # Send request again with CSRF header
                    self.__headers[CSRF_HEADER] = response.headers[CSRF_HEADER]
                    log.debug('Setting CSRF header: %s = %s',
                              CSRF_HEADER, response.headers[CSRF_HEADER])
                    await response.release()
                    return await self.__post(data)

                elif response.status == AUTH_ERROR_CODE:
                    await response.release()
                    log.debug('Authentication failed')
                    raise AuthError(str(self.url))

                else:
                    try:
                        answer = await response.json()
                    except aiohttp.ClientResponseError as e:
                        text = textwrap.shorten(await response.text(),
                                                50, placeholder='...')
                        raise RPCError('Server sent malformed JSON: {}'.format(text))
                    else:
                        return answer

    async def __send_request(self, post_data):
        """Send RPC POST request to daemon

        post_data: Any valid RPC request as JSON string

        If applicable, returns response['arguments']['torrents'] or
        response['arguments'], otherwise response.

        Raises ClientError.
        """
        try:
            answer = await self.__post(post_data)
        except OSError as e:
            log.debug('Caught OSError: %r', e)
            raise ConnectionError(str(self.url))
        except asyncio.TimeoutError as e:
            log.debug('Caught TimeoutError: %r', e)
            raise ConnectionError('Timeout after {}s: {}'.format(self.timeout, self.url))
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
        """Return asyncio coroutine that sends RPC request and returns response

        method: Any method from the RPC specs with every '-' replaced with '_'.
                For arguments see the RPC specs.

        Example:
        >>> stats = await client.session_stats()
        >>> torrents = await client.torrent_get(ids=(1,2,3), fields=('status','name'))

        Raises RPCError, ConnectionError, AuthError
        """
        async def request(arguments={}, autoconnect=True, **kwargs):
            async with self.__request_lock:
                if not self.connected:
                    if autoconnect:
                        log.debug('Autoconnecting for %r', method)
                        await self.connect()
                    else:
                        log.debug('Not connected and autoconnect=%r - %r returns None',
                                  autoconnect, method)
                        return None

                arguments.update(**kwargs)
                rpc_request = json.dumps({'method'    : method.replace('_', '-'),
                                          'arguments' : arguments})

                try:
                    return await self.__send_request(rpc_request)
                except ClientError as e:
                    log.debug('Caught ClientError in %r request: %r', method, e)

                    # RPCError does not mean host is unreachable, there was just a
                    # misunderstanding, so we're still connected.
                    if not isinstance(e, RPCError) and self.connected:
                        await self.disconnect(str(e))

                    self.__on_error.send(self.__url, error=e)
                    raise

        request.__name__ = method
        request.__qualname__ = method
        return request
