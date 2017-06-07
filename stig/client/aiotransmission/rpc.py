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


AUTH_ERROR_CODE = 401
CSRF_ERROR_CODE = 409
CSRF_HEADER = 'X-Transmission-Session-Id'
TIMEOUT = 10


class TransmissionURL():
    _DEFAULT = urlsplit('http://localhost:9091/transmission/rpc')
    _ATTRS = ('scheme', 'netloc', 'path', 'query', 'fragment', 'username',
              'password', 'hostname', 'port')

    _SCHEME_REGEX = re.compile('^\w+://')

    def __init__(self, url='http://localhost:9091/transmission/rpc'):
        url = str(url)
        # Insert default scheme before parsing the URL. Otherwise, urlsplit
        # is confused.
        if not self._SCHEME_REGEX.match(url):
            url = self._DEFAULT.scheme + '://' + url

        # urlsplit doesn't seem to raise meaningful errors,
        # e.g. 'localhost:123:456' raises:
        # ValueError: invalid literal for int() with base 10: '123:456'
        try:
            parsed_url = urlsplit(url, allow_fragments=False)
            urldict = {}
            for attr in self._ATTRS:
                urldict[attr] = getattr(parsed_url, attr)
        except Exception:
            raise URLParserError(url)

        if urldict['username'] is not None and urldict['password'] is None:
            raise URLParserError('Missing password: %s' % url)

        # Some more defaults
        if urldict['port'] is None:
            urldict['port'] = self._DEFAULT.port
        if urldict['path'] in ('/', ''):
            urldict['path'] = self._DEFAULT.path
        self.url = urldict

    @property
    def has_auth(self):
        return bool(self.url['username'] and self.url['password'])

    def str(self, path=False, scheme=False, port=False, password=False):
        urlfmt = ''
        if self.url['username'] is not None:
            urlfmt += '{username}'
            if password and self.url['password'] is not None:
                urlfmt += ':{password}'
            urlfmt += '@'
        urlfmt += '{hostname}'
        if scheme:
            urlfmt = '{scheme}://' + urlfmt
        if port:
            urlfmt = urlfmt + ':{port}'
        if path:
            urlfmt = urlfmt + '{path}'
        return urlfmt.format(**self.url)

    def __repr__(self):
        return self.str(path=True, scheme=True, port=True, password=True)

    def __str__(self):
        scheme = self.url['scheme'] != self._DEFAULT.scheme
        path   = self.url['path']   != self._DEFAULT.path
        port   = self.url['port']   != self._DEFAULT.port
        return self.str(path=path, scheme=scheme, port=port, password=False)

    def __getattr__(self, attr):
        try:
            return self.url[attr]
        except KeyError:
            raise AttributeError(attr)

    def __eq__(self, other):
        return str(self) == str(other)

    def __ne__(self, other):
        return not self.__eq__(other)


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
        self.__connecting_lock = asyncio.Lock(loop=loop)
        self.__connection_tested = False
        self.__timeout = TIMEOUT
        self.__on_connected = Signal()
        self.__on_disconnected = Signal()
        self.__on_error = Signal()
        self.__version = None
        self.__rpcversion = None
        self.__rpcversionmin = None

    def __del__(self, _warnings=warnings):
        if self.__session is not None and not self.__session.closed:
            _warnings.warn('disconnect() wasn\'t called', ResourceWarning)
            self.__session.close()

    def on(self, signal, callback, autoremove=True):
        """Register `callback` for `signal`

        signal: 'connected', 'disconnected' or 'error'
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
        if self.__connecting_lock.locked():
            # Someone else is currently connecting.  Wait for them to finish.
            log.debug('Waiting for other connection to establish')
            await self.__connecting_lock.acquire()
            log.debug('Other connect() call finished')
            self.__connecting_lock.release()

            # Check if connection has the url we want
            if url is not None and self.url != TransmissionURL(url):
                log.debug('Reconnecting because %s != %s', self.__url, url)
                await self.connect(url=url, timeout=timeout)

            # The other connect() call croaked for some reason, and our caller
            # expects the same exception.  Calling connect() again should
            # raise the same error, but that's too much recursion for my tiny,
            # little mind.
            elif self.__connect_exception is not None:
                raise self.__connect_exception

            # Looks like we're connected.  Our intended timeout may differ
            # from what the previous call set, but there's no need to
            # re-connect.
            elif timeout is not None and self.timeout != timeout:
                self.timeout = timeout

        else:
            async with self.__connecting_lock:
                log.debug('Acquired connect() lock')
                if timeout is not None:
                    self.timeout = timeout

                # Reconnect if URL is specified
                if url is not None:
                    if self.connected:
                        log.debug('Reconnecting to %s', url)
                        await self.disconnect('reconnecting to %s' % url)
                    self.__url = TransmissionURL(url)

                # If we're not connected (because new URL or we weren't
                # connected in the first place), create new session.
                if not self.connected:
                    log.debug('Connecting to %s (timeout=%ss)', self.url, self.timeout)
                    session_args = {'loop': self.loop}
                    # TODO: Remove this check when aiohttp2 is common.
                    if aiohttp.__version__[0] == '2':
                        session_args['connector'] = aiohttp.TCPConnector(limit_per_host=1)
                    if self.__url.has_auth:
                        session_args['auth'] = aiohttp.BasicAuth(self.__url.username,
                                                                 self.__url.password)
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
                    await self.disconnect('Connection failed during initialization')
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
        await self.__reset()
        log.debug('Disconnecting from %s (%s)',
                  self.url, reason if reason is not None else 'for no reason')
        self.__on_disconnected.send(self.__url)

    async def __reset(self):
        if self.__session is not None:
            await self.__session.close()
        self.__session = None
        self.__version = None
        self.__rpcversion = None
        self.__rpcversionmin = None
        self.__connection_tested = False

    async def __post(self, data):
        with aiohttp.Timeout(self.timeout, loop=self.loop):
            try:
                response = await self.__session.post(repr(self.__url), data=data, headers=self.__headers)
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
        realmethod = method.replace('_', '-')

        async def request(arguments={}, autoconnect=True, **kwargs):
            if not self.connected:
                if autoconnect:
                    log.debug('Autoconnecting for %r', method)
                    await self.connect()
                else:
                    log.debug('Not connected and autoconnect=%r - %r returns None',
                              autoconnect, method)
                    return None

            arguments.update(**kwargs)
            rpc_request = json.dumps( {'method':realmethod, 'arguments':arguments} )
            try:
                return await self.__send_request(rpc_request)
            except ClientError as e:
                log.debug('Caught ClientError in %r request: %r', method, e)

                # RPCError does not mean host is unreachable, there was just a
                # misunderstanding, so we're still connected.
                if not isinstance(e, RPCError):
                    await self.disconnect(str(e))

                self.__on_error.send(self.__url, error=e)
                raise

        request.__name__ = method
        request.__qualname__ = method
        return request
