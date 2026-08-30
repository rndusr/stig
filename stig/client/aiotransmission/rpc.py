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

import asyncio
import json
import re

import async_timeout
from blinker import Signal

from ..errors import AuthError, ClientError, ConnectionError, RPCError, TimeoutError
from ..utils import URL
from . import apicompat

from ...logging import make_logger  # isort:skip

log = make_logger(__name__)


AUTH_ERROR_CODE = 401
CSRF_ERROR_CODE = 409
CSRF_HEADER = 'X-Transmission-Session-Id'
TIMEOUT = 10


class SemVer(tuple):
    """
    Semantic version number that compares like a tuple of integers

    Pre-release and build metadata are ignored, i.e. "1.2.3-rc1" and "1.2.3"
    are the same version.
    """

    @classmethod
    def parse(cls, string):
        """Return SemVer or None if `string` is None or malformed"""
        if string is None:
            return None
        core = re.split(r'[-+]', str(string), maxsplit=1)[0]
        try:
            return cls(int(part) for part in core.split('.'))
        except ValueError:
            log.debug('Malformed semantic version: %r', string)
            return None

    def __str__(self):
        return '.'.join(str(part) for part in self)

    def __repr__(self):
        return f'{type(self).__name__}({str(self)!r})'


class RPCProtocol:
    """
    One of the two RPC protocols spoken by the Transmission daemon

    Subclasses translate method calls into requests, unpack responses and turn
    errors reported by the daemon into RPCError exceptions.
    """

    name = NotImplemented

    def encode(self, method, arguments):
        """
        Return request for `method`

        method: Any method from the RPC specs with every '-' replaced with '_'
        arguments: Dictionary of arguments for `method`
        """
        raise NotImplementedError()

    def recognizes(self, answer):
        """Whether `answer` is a response of this protocol"""
        raise NotImplementedError()

    def decode(self, method, answer):
        """
        Return the interesting part of `answer`

        If applicable, this is the list of torrents or the arguments of the
        response, otherwise the whole response.

        Raises RPCError if the daemon reported an error.
        """
        raise NotImplementedError()

    def __repr__(self):
        t = type(self).__name__
        return f'<{t} {self.name}>'


class LegacyRPC(RPCProtocol):
    """
    Transmission's bespoke RPC protocol

    This is the only protocol spoken by daemons older than 4.1.0, where it is
    deprecated in favour of JSON-RPC 2.0.
    """

    name = 'RPC'

    def encode(self, method, arguments):
        return {'method': method.replace('_', '-'), 'arguments': arguments}

    def recognizes(self, answer):
        return isinstance(answer, dict) and 'result' in answer

    def decode(self, method, answer):
        if answer['result'] != 'success':
            raise RPCError(answer['result'].capitalize())
        elif 'arguments' in answer:
            arguments = answer['arguments']
            if 'torrents' in arguments:
                return arguments['torrents']
            else:
                return arguments
        else:
            return answer


class JSONRPC(RPCProtocol):
    """
    JSON-RPC 2.0 protocol

    This protocol is only spoken by daemons since 4.1.0, which also renamed all
    RPC strings to snake_case.  Requests and responses are translated by the
    apicompat module so the rest of stig can keep using the old strings.
    """

    name = 'JSON-RPC 2.0'
    version = '2.0'

    def __init__(self):
        self._prev_id = 0

    def encode(self, method, arguments):
        # Requests are sent one at a time (see TransmissionRPC._request_lock),
        # so a simple counter is enough to match responses to requests.
        self._prev_id += 1
        return {
            'jsonrpc': self.version,
            'method': method,
            'params': apicompat.request_to_current(method, arguments),
            'id': self._prev_id,
        }

    def recognizes(self, answer):
        return isinstance(answer, dict) and answer.get('jsonrpc') == self.version

    def decode(self, method, answer):
        if 'error' in answer:
            raise RPCError(self._error_message(answer['error']))
        else:
            result = apicompat.response_to_legacy(method, answer.get('result', {}))
            if isinstance(result, dict) and 'torrents' in result:
                return result['torrents']
            else:
                return result

    @staticmethod
    def _error_message(error):
        if not isinstance(error, dict):
            return str(error)
        message = str(error.get('message', 'Unknown error'))
        data = error.get('data')
        # The daemon may explain itself in more detail than the generic message
        # of the error code does.
        details = data.get('error_string') if isinstance(data, dict) else None
        if details:
            return f'{message}: {details}'
        else:
            return message


# Preferred protocol first
PROTOCOLS = (JSONRPC, LegacyRPC)


class TransmissionRPC:
    """
    Low-level AsyncIO Transmission RPC communication

    This class handles connecting to a Transmission daemon via the RPC
    interface.  It does not implement the RPC protocol, only basic things like
    authentication, sending requests and receiving responses.  High-level RPCs
    are done in the *API classes.
    """

    def __init__(self, host='localhost', port=9091, *, tls=False, user='',
                 password='', proxy='', path='/transmission/rpc', enabled=True):
        self.host = host
        self.port = port
        self.path = path
        self.tls = tls
        self.user = user
        self.password = password
        self.proxy = proxy
        self._headers = {'content-type': 'application/json'}
        self._session = None
        self._enabled_event = asyncio.Event()
        self.enabled = enabled
        self._request_lock = asyncio.Lock()
        self._connecting_lock = asyncio.Lock()
        self._connection_tested = False
        self._connection_exception = None
        self._timeout = TIMEOUT
        self._protocol = None
        self._version = None
        self._rpcversion = None
        self._rpcversionmin = None
        self._rpcversion_semver = None
        self._on_connecting = Signal()
        self._on_connected = Signal()
        self._on_disconnected = Signal()
        self._on_error = Signal()

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
    def protocol(self):
        """Name of the RPC protocol we're talking to the daemon or None if not connected"""
        return self._protocol.name if self._protocol is not None else None

    @property
    def version(self):
        """Version of the Transmission daemon or None if not connected"""
        return self._version

    @property
    def rpcversion(self):
        """
        Deprecated RPC version of the Transmission daemon

        None if not connected or if the daemon doesn't report it anymore.  Use
        `rpcversion_semver` instead.
        """
        return self._rpcversion

    @property
    def rpcversionmin(self):
        """
        Oldest RPC version supported by Transmission daemon

        None if not connected or if the daemon doesn't report it.
        """
        return self._rpcversionmin

    @property
    def rpcversion_semver(self):
        """
        RPC version of the Transmission daemon as a SemVer

        None if not connected or if the daemon doesn't report it, which means
        it is older than 5.3.0, the version that introduced it.
        """
        return self._rpcversion_semver

    @property
    def host(self):
        """
        Hostname or IP of the Transmission RPC interface

        Setting this property calls disconnect().
        """
        return self._host

    @host.setter
    def host(self, host):
        self._host = str(host) if host is not None else 'localhost'
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
        if path is None:
            path = '/transmission/rpc'
        elif not path or path[0] != '/':
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
        self._port = int(port) if port is not None else 9091
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
        self._user = str(user) if user is not None else ''
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
        self._password = str(password) if password is not None else ''
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
        self._tls = bool(tls) if tls is not None else False
        asyncio.ensure_future(self.disconnect('Changing tls: %r' % self._tls))

    @property
    def url(self):
        """
        URL of the Transmission RPC interface

        Setting or getting this property sets or gets the following properties: tls, user,
        password, host, port, path

        Missing parts are filled in with defaults, e.g. "example.org:1234" results in
        "http://example.org:1234/transmission/rpc".

        While user and password are supported when setting ("user:password@localhost"),
        they are not included in the return value for security reasons.  See the
        url_unsafe property.
        """
        return '%s://%s:%d%s' % ('https' if self.tls else 'http',
                                 self.host, self.port, self.path)

    @url.setter
    def url(self, url):
        if url is None:
            url = URL('http://localhost:9091/transmission/rpc')
        else:
            url = URL(url)
        self._user = url.user or ''
        self._password = url.password or ''
        if url.scheme == 'https':
            self._tls = True
        elif url.scheme == 'http':
            self._tls = False
        else:
            raise ValueError('Invalid scheme: %r' % (url.scheme,))
        self._host = url.host
        self._port = int(url.port) if url.port is not None else 9091
        self._path = url.path if url.path is not None else '/transmission/rpc'
        asyncio.ensure_future(self.disconnect('Changing url: %r' % self._url))

    @property
    def url_unsafe(self):
        """URL of the Transmission RPC interface with user and password if given"""
        if self.user or self.password:
            return '%s://%s:%s@%s:%d%s' % ('https' if self.tls else 'http', self.user,
                                           self.password, self.host, self.port, self.path)
        else:
            return self.url

    @property
    def proxy(self):
        """URL of a SOCKS5, SOCKS4 or HTTP proxy"""
        return self._proxy

    @proxy.setter
    def proxy(self, proxy):
        if proxy:
            try:
                import aiohttp_socks
            except ImportError:
                raise ValueError('Missing extra: proxy (aiohttp_socks)')
            self._connector = aiohttp_socks.ProxyConnector.from_url(proxy)
            self._proxy = URL(proxy)
        else:
            self._connector = None
            self._proxy = URL('')
        asyncio.ensure_future(self.disconnect('Changing proxy: %r' % self._proxy))

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

            session_args = {}
            if self.user or self.password:
                session_args['auth'] = aiohttp.BasicAuth(self.user, self.password,
                                                         encoding='utf-8')
            if self._connector is not None:
                session_args['connector'] = self._connector
                session_args['connector_owner'] = False
            self._session = aiohttp.ClientSession(**session_args)

            # Check if connection works and find out which protocol to speak
            log.debug('Testing connection to %s', self.url)
            try:
                protocol, info = await self._negotiate_protocol()
            except ClientError as e:
                self._connection_exception = e
                log.debug('Caught during connection test: %r', e)
                await self._reset()
                self._on_error.send(self, error=e)
                raise
            else:
                self._protocol = protocol
                self._version = info['version']
                self._rpcversion = info.get('rpc-version')
                self._rpcversionmin = info.get('rpc-version-minimum')
                self._rpcversion_semver = SemVer.parse(info.get('rpc-version-semver'))
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
                reason if reason is not None else 'for no reason',)
            self._on_disconnected.send(self)

    async def _negotiate_protocol(self):
        """
        Find out which RPC protocol the daemon speaks

        Return (protocol, session info) for the most modern protocol the daemon
        understands.

        Raises ClientError.
        """
        for cls in PROTOCOLS:
            protocol = cls()
            answer = await self._post_request(protocol, 'session_get', {})
            if protocol.recognizes(answer):
                log.debug('Daemon at %s speaks %s', self.url, protocol.name)
                return protocol, protocol.decode('session_get', answer)
            else:
                log.debug(
                    'Daemon at %s does not speak %s: %r',
                    self.url,
                    protocol.name,
                    answer,
                )
        raise RPCError(f'Not a Transmission daemon: {self.url}')

    async def _reset(self):
        if self._session is not None:
            await self._session.close()
        self._session = None
        self._protocol = None
        self._version = None
        self._rpcversion = None
        self._rpcversionmin = None
        self._rpcversion_semver = None
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
                try:
                    answer = await response.json()
                except json.JSONDecodeError as e:
                    raise RPCError('Server sent malformed JSON: %s: %s' % (e, await response.text()))
                except UnicodeDecodeError as e:
                    raise RPCError('Server sent malformed UTF-8: %s' % e)
                else:
                    return answer

    async def _post_request(self, protocol, method, arguments):
        """
        Send `method` as an RPC POST request and return the raw response

        protocol: RPCProtocol instance that encodes the request
        method: Any method from the RPC specs with every '-' replaced with '_'
        arguments: Dictionary of arguments for `method`

        Raises ClientError.
        """
        request = protocol.encode(method, arguments)
        try:
            post_data = json.dumps(request)
        except Exception as e:
            raise RuntimeError(f'Invalid JSON data: {e}: {request:r}') from None
        # NOTE #163: Letting asyncio.CancelledError bubble up seems to fix the issue that
        #            causes empty torrent lists in new tabs until the next poll iteration.
        #            But I've seen this error pop up in the TUI log: "Unclosed client
        #            session client_session: <aiohttp.client.ClientSession object at
        #            0x7f35d98d1be0>" This may or may not be related.
        import aiohttp

        try:
            from aiohttp_socks import  ProxyConnectionError, ProxyError, ProxyTimeoutError
        except ImportError:
            class ProxyError(Exception): pass
            class ProxyConnectionError(Exception): pass
            class ProxyTimeoutError(Exception): pass

        try:
            answer = await self._post(post_data)
        except aiohttp.ClientError as e:
            log.debug('Caught during POST request: %r', e)
            raise ConnectionError(self.url)

        except (ProxyError, ProxyConnectionError) as e:
            log.debug('Caught during POST request: %r', e)
            raise ConnectionError(self.proxy)

        except asyncio.TimeoutError as e:
            log.debug('Caught during POST request: %r', e)
            raise TimeoutError(self.timeout, self.url)

        except ProxyTimeoutError as e:
            log.debug('Caught during POST request: %r', e)
            raise TimeoutError(self.timeout, self.proxy)

        else:
            return answer

    async def _send_request(self, method, arguments):
        """
        Send `method` as an RPC POST request and unpack the response

        method: Any method from the RPC specs with every '-' replaced with '_'
        arguments: Dictionary of arguments for `method`

        If applicable, returns the list of torrents or the arguments of the
        response, otherwise the whole response.

        Raises ClientError.
        """
        protocol = self._protocol
        if protocol is None:
            raise ConnectionError(self.url)
        answer = await self._post_request(protocol, method, arguments)
        return protocol.decode(method, answer)

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
                try:
                    return await self._send_request(method, arguments)
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
