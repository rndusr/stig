import asyncio

import asynctest
from aiohttp import web

import resources_aiotransmission as rsrc
from stig.client import AuthError, ConnectionError, RPCError, TimeoutError
from stig.client.aiotransmission.rpc import TransmissionRPC


class TestTransmissionRPC(asynctest.ClockedTestCase):
    async def setUp(self):
        self.daemon = rsrc.FakeTransmissionDaemon()
        self.daemon.response = rsrc.SESSION_GET_RESPONSE   # Default response
        await self.daemon.start()
        self.client = TransmissionRPC(self.daemon.host, self.daemon.port)

        self.cb_connected = rsrc.FakeCallback('cb_connected')
        self.cb_disconnected = rsrc.FakeCallback('cb_disconnected')
        self.cb_error = rsrc.FakeCallback('cb_error')
        self.client.on('connected', self.cb_connected)
        self.client.on('disconnected', self.cb_disconnected)
        self.client.on('error', self.cb_error)

    async def tearDown(self):
        await self.client.disconnect()
        await self.daemon.stop()

    def assert_not_connected_to(self, host, port):
        self.assertEqual(self.client.host, host)
        self.assertEqual(self.client.port, port)
        self.assertEqual(self.client.connected, False)
        self.assertEqual(self.client.version, None)
        self.assertEqual(self.client.rpcversion, None)
        self.assertEqual(self.client.rpcversionmin, None)

    def assert_connected_to(self, host, port):
        self.assertEqual(self.client.host, host)
        self.assertEqual(self.client.port, port)
        self.assertEqual(self.client.connected, True)
        self.assertNotEqual(self.client.version, None)
        self.assertNotEqual(self.client.rpcversion, None)
        self.assertNotEqual(self.client.rpcversionmin, None)

    def assert_cb_connected_called(self, calls=None, args=None, kwargs=None):
        if  calls is not None: self.assertEqual(self.cb_connected.calls, calls)
        if   args is not None: self.assertEqual(self.cb_connected.args, list(args))
        if kwargs is not None: self.assertEqual(self.cb_connected.kwargs, list(kwargs))

    def assert_cb_disconnected_called(self, calls, args=None, kwargs=None):
        if  calls is not None: self.assertEqual(self.cb_disconnected.calls, calls)
        if   args is not None: self.assertEqual(self.cb_disconnected.args, list(args))
        if kwargs is not None: self.assertEqual(self.cb_disconnected.kwargs, list(kwargs))

    def assert_cb_error_called(self, calls, args=None, kwargs=None):
        if  calls is not None: self.assertEqual(self.cb_error.calls, calls)
        if   args is not None: self.assertEqual(self.cb_error.args, list(args))
        if kwargs is not None:
            for kw_cb, kw_exp in zip(self.cb_error.kwargs, kwargs):
                self.assertEqual(set(kw_cb), set(kw_exp))
                for k,v in kw_cb.items():
                    self.assertEqual(v, kw_exp[k])

    def test_setting_connection_credentials_to_None(self):
        self.client.url = 'https://foo:bar@foo:123/path'
        self.client.host = None
        self.assertEqual(self.client.url, 'https://localhost:123/path')
        self.assertEqual((self.client.user, self.client.password), ('foo', 'bar'))
        self.client.port = None
        self.assertEqual(self.client.url, 'https://localhost:9091/path')
        self.assertEqual((self.client.user, self.client.password), ('foo', 'bar'))
        self.client.path = None
        self.assertEqual(self.client.url, 'https://localhost:9091/transmission/rpc')
        self.assertEqual((self.client.user, self.client.password), ('foo', 'bar'))
        self.client.tls = None
        self.assertEqual(self.client.url, 'http://localhost:9091/transmission/rpc')
        self.assertEqual((self.client.user, self.client.password), ('foo', 'bar'))
        self.client.user = None
        self.assertEqual(self.client.url, 'http://localhost:9091/transmission/rpc')
        self.assertEqual((self.client.user, self.client.password), ('', 'bar'))
        self.client.password = None
        self.assertEqual(self.client.url, 'http://localhost:9091/transmission/rpc')
        self.assertEqual((self.client.user, self.client.password), ('', ''))

    def test_getting_url_property(self):
        self.client.host = 'foo'
        self.client.port = 123
        self.client.tls = True
        self.assertEqual(self.client.url, 'https://foo:123/transmission/rpc')
        self.client.tls = False
        self.assertEqual(self.client.url, 'http://foo:123/transmission/rpc')
        self.client.host = 'fuu'
        self.assertEqual(self.client.url, 'http://fuu:123/transmission/rpc')
        self.client.port = '1724'
        self.assertEqual(self.client.url, 'http://fuu:1724/transmission/rpc')
        self.client.path = 'user/transmission/rpc'
        self.assertEqual(self.client.url, 'http://fuu:1724/user/transmission/rpc')

    def test_setting_url_property(self):
        self.client.url = 'some.host'
        self.assertEqual(self.client.url, 'http://some.host:9091/transmission/rpc')
        self.client.url = 'some.host:1234'
        self.assertEqual(self.client.url, 'http://some.host:1234/transmission/rpc')
        self.client.url = 'some.host/other/path'
        self.assertEqual(self.client.url, 'http://some.host:9091/other/path')
        self.client.url = 'https://some.host'
        self.assertEqual(self.client.url, 'https://some.host:9091/transmission/rpc')
        self.client.url = 'foo:bar@some.host'
        self.assertEqual(self.client.url, 'http://some.host:9091/transmission/rpc')
        self.assertEqual(self.client.user, 'foo')
        self.assertEqual(self.client.password, 'bar')
        self.client.url = 'foo@some.host:555'
        self.assertEqual(self.client.url, 'http://some.host:555/transmission/rpc')
        self.assertEqual(self.client.user, 'foo')
        self.assertEqual(self.client.password, '')
        self.client.url = 'https://:bar@some.host'
        self.assertEqual(self.client.url, 'https://some.host:9091/transmission/rpc')
        self.assertEqual(self.client.user, '')
        self.assertEqual(self.client.password, 'bar')
        self.client.url = None
        self.assertEqual(self.client.url, 'http://localhost:9091/transmission/rpc')
        self.assertEqual(self.client.user, '')
        self.assertEqual(self.client.password, '')

    def test_url_unsafe_property(self):
        self.client.url = 'some.host'
        self.assertEqual(self.client.url_unsafe, self.client.url)
        self.client.user = 'foo'
        self.assertEqual(self.client.url_unsafe, 'http://foo:@some.host:9091/transmission/rpc')
        self.client.password = 'bar'
        self.assertEqual(self.client.url_unsafe, 'http://foo:bar@some.host:9091/transmission/rpc')
        self.client.user = None
        self.assertEqual(self.client.url_unsafe, 'http://:bar@some.host:9091/transmission/rpc')
        with self.assertRaises(AttributeError):
            self.client.url_unsafe = 'something'

    async def test_connect_to_good_url(self):
        # TransmissionRPC requests 'session-get' to test the connection and
        # set version properties.
        self.daemon.response = rsrc.SESSION_GET_RESPONSE

        self.assert_not_connected_to(self.daemon.host, self.daemon.port)
        await self.client.connect()
        self.assert_connected_to(self.daemon.host, self.daemon.port)
        self.assert_cb_connected_called(calls=1, args=[(self.client,)])
        self.assert_cb_disconnected_called(calls=0)
        self.assert_cb_error_called(calls=0)

        await self.client.disconnect()
        self.assert_not_connected_to(self.daemon.host, self.daemon.port)
        self.assert_cb_connected_called(calls=1, args=[(self.client,)])
        self.assert_cb_disconnected_called(calls=1, args=[(self.client,)])
        self.assert_cb_error_called(calls=0)

    async def test_authentication_with_good_url(self):
        self.client.user = 'foo'
        self.client.password = 'bar'

        # TransmissionRPC requests 'session-get' to test the connection and
        # set version properties.
        self.daemon.response = rsrc.SESSION_GET_RESPONSE
        self.daemon.auth = {'user': 'foo', 'password': 'bar'}

        self.assert_not_connected_to(self.daemon.host, self.daemon.port)
        await self.client.connect()
        self.assert_connected_to(self.daemon.host, self.daemon.port)
        self.assert_cb_connected_called(calls=1, args=[(self.client,)])
        self.assert_cb_disconnected_called(calls=0)
        self.assert_cb_error_called(calls=0)

        await self.client.disconnect()
        self.assert_not_connected_to(self.daemon.host, self.daemon.port)
        self.assert_cb_connected_called(calls=1, args=[(self.client,)])
        self.assert_cb_disconnected_called(calls=1, args=[(self.client,)])
        self.assert_cb_error_called(calls=0)

    async def test_authentication_with_good_url_empty_username(self):
        self.client.user = ''
        self.client.password = 'bar'

        # TransmissionRPC requests 'session-get' to test the connection and
        # set version properties.
        self.daemon.response = rsrc.SESSION_GET_RESPONSE
        self.daemon.auth = {'user': '', 'password': 'bar'}

        self.assert_not_connected_to(self.daemon.host, self.daemon.port)
        await self.client.connect()
        self.assert_connected_to(self.daemon.host, self.daemon.port)
        self.assert_cb_connected_called(calls=1, args=[(self.client,)])
        self.assert_cb_disconnected_called(calls=0)
        self.assert_cb_error_called(calls=0)

        await self.client.disconnect()
        self.assert_not_connected_to(self.daemon.host, self.daemon.port)
        self.assert_cb_connected_called(calls=1, args=[(self.client,)])
        self.assert_cb_disconnected_called(calls=1, args=[(self.client,)])
        self.assert_cb_error_called(calls=0)

    async def test_authentication_with_good_url_empty_password(self):
        self.client.user = 'foo'
        self.client.password = ''

        # TransmissionRPC requests 'session-get' to test the connection and
        # set version properties.
        self.daemon.response = rsrc.SESSION_GET_RESPONSE
        self.daemon.auth = {'user': 'foo', 'password': ''}

        self.assert_not_connected_to(self.daemon.host, self.daemon.port)
        await self.client.connect()
        self.assert_connected_to(self.daemon.host, self.daemon.port)
        self.assert_cb_connected_called(calls=1, args=[(self.client,)])
        self.assert_cb_disconnected_called(calls=0)
        self.assert_cb_error_called(calls=0)

        await self.client.disconnect()
        self.assert_not_connected_to(self.daemon.host, self.daemon.port)
        self.assert_cb_connected_called(calls=1, args=[(self.client,)])
        self.assert_cb_disconnected_called(calls=1, args=[(self.client,)])
        self.assert_cb_error_called(calls=0)

    async def test_connect_to_bad_url(self):
        self.assert_not_connected_to(self.daemon.host, self.daemon.port)

        self.client.port = rsrc.unused_port()
        with self.assertRaises(ConnectionError) as cm:
            await self.client.connect()
        self.assertEqual(str(cm.exception), 'Failed to connect: %s' % self.client.url)
        self.assert_cb_connected_called(calls=0)
        self.assert_cb_disconnected_called(calls=0)
        self.assert_cb_error_called(calls=1,
                                    args=[(self.client,)],
                                    kwargs=[{'error': cm.exception}])

    async def test_reconnect_to_same_url(self):
        self.assert_not_connected_to(self.daemon.host, self.daemon.port)

        await self.client.connect()
        session1 = self.client._session
        self.assert_connected_to(self.daemon.host, self.daemon.port)
        self.assert_cb_connected_called(calls=1, args=[(self.client,)])
        self.assert_cb_disconnected_called(calls=0)
        self.assert_cb_error_called(calls=0)

        await self.client.connect()
        session2 = self.client._session
        self.assertIsNot(session1, session2)
        self.assert_connected_to(self.daemon.host, self.daemon.port)
        self.assert_cb_connected_called(calls=2, args=[(self.client,), (self.client,)])
        self.assert_cb_disconnected_called(calls=1, args=[(self.client,)])
        self.assert_cb_error_called(calls=0)

    async def test_reconnect_to_bad_url(self):
        self.assert_not_connected_to(self.daemon.host, self.daemon.port)

        await self.client.connect()
        self.assert_connected_to(self.daemon.host, self.daemon.port)
        self.assert_cb_connected_called(calls=1, args=[(self.client,)])
        self.assert_cb_disconnected_called(calls=0)
        self.assert_cb_error_called(calls=0)

        self.client.host = 'badhostname'
        with self.assertRaises(ConnectionError) as cm:
            await self.client.connect()
        self.assertEqual(str(cm.exception), 'Failed to connect: %s' % self.client.url)
        self.assert_not_connected_to('badhostname', self.daemon.port)
        self.assert_cb_connected_called(calls=1, args=[(self.client,)])
        self.assert_cb_disconnected_called(calls=1, args=[(self.client,)])
        self.assert_cb_error_called(calls=1,
                                    args=[(self.client,)],
                                    kwargs=[{'error': cm.exception}])

    async def test_RpcError_during_connect(self):
        self.daemon.response = {'result': 'Error from daemon'}
        with self.assertRaises(RPCError) as cm:
            await self.client.connect()

        self.assertEqual(str(cm.exception), 'Invalid RPC response: Error from daemon')
        self.assert_not_connected_to(self.daemon.host, self.daemon.port)
        self.assert_cb_connected_called(calls=0)
        self.assert_cb_disconnected_called(calls=0)
        self.assert_cb_error_called(calls=1,
                                    args=[(self.client,)],
                                    kwargs=[{'error': cm.exception}])

    async def test_RpcError_when_connected(self):
        await self.client.connect()
        self.assertEqual(self.client.connected, True)
        self.assert_cb_connected_called(calls=1, args=[(self.client,)])

        msg = "I don't like the jib of your request"
        self.daemon.response = {'result': msg}
        with self.assertRaises(RPCError) as cm:
            await self.client.invalid_rpc_method()
        self.assertEqual(str(cm.exception), 'Invalid RPC response: ' + msg)
        self.assertEqual(self.client.connected, True)

        self.assert_cb_disconnected_called(calls=0)
        self.assert_cb_error_called(calls=1,
                                    args=[(self.client,)],
                                    kwargs=[{'error': cm.exception}])

    async def test_ConnectionError_during_connect(self):
        self.assert_not_connected_to(self.daemon.host, self.daemon.port)

        await self.daemon.stop()
        with self.assertRaises(ConnectionError) as cm:
            await self.client.connect()
        self.assertEqual(str(cm.exception), 'Failed to connect: ' + self.client.url)
        self.assertEqual(self.client.connected, False)
        self.assert_cb_connected_called(calls=0)
        self.assert_cb_disconnected_called(calls=0)
        self.assert_cb_error_called(calls=1,
                                    args=[(self.client,)],
                                    kwargs=[{'error': cm.exception}])

    async def test_ConnectionError_when_connected(self):
        await self.client.connect()
        self.assert_connected_to(self.daemon.host, self.daemon.port)

        await self.daemon.stop()
        with self.assertRaises(ConnectionError) as cm:
            await self.client.torrent_get()
        self.assertEqual(str(cm.exception), 'Failed to connect: ' + self.client.url)
        self.assert_not_connected_to(self.daemon.host, self.daemon.port)
        self.assert_cb_disconnected_called(calls=1, args=[(self.client,)])
        self.assert_cb_error_called(calls=1,
                                    args=[(self.client,)],
                                    kwargs=[{'error': cm.exception}])

    async def test_AuthError_during_connect(self):
        self.daemon.response = web.Response(status=rsrc.AUTH_ERROR_CODE)
        with self.assertRaises(AuthError) as cm:
            await self.client.connect()
        self.assertEqual(str(cm.exception), 'Authentication failed: ' + self.client.url)
        self.assert_not_connected_to(self.daemon.host, self.daemon.port)
        self.assert_cb_connected_called(calls=0)
        self.assert_cb_disconnected_called(calls=0)
        self.assert_cb_error_called(calls=1,
                                    args=[(self.client,)],
                                    kwargs=[{'error': cm.exception}])

    async def test_AuthError_when_connected(self):
        await self.client.connect()
        self.assert_connected_to(self.daemon.host, self.daemon.port)

        self.daemon.response = web.Response(status=rsrc.AUTH_ERROR_CODE)
        with self.assertRaises(AuthError) as cm:
            await self.client.any_method()
        self.assertEqual(str(cm.exception), 'Authentication failed: ' + self.client.url)
        self.assert_not_connected_to(self.daemon.host, self.daemon.port)
        self.assert_cb_connected_called(calls=1, args=[(self.client,)])
        self.assert_cb_disconnected_called(calls=1, args=[(self.client,)])
        self.assert_cb_error_called(calls=1,
                                    args=[(self.client,)],
                                    kwargs=[{'error': cm.exception}])

    async def test_timeout_minus_one(self):
        delay = self.client.timeout - 1
        await asyncio.gather(self.advance(delay),
                             self.client.connect())
        await self.client.disconnect()
        self.assert_cb_connected_called(calls=1, args=[(self.client,)])
        self.assert_cb_disconnected_called(calls=1, args=[(self.client,)])
        self.assert_cb_error_called(calls=0)

    async def test_timeout_plus_one(self):
        delay = self.client.timeout + 1

        # NOTE: This function is only called sometimes, probably depending on
        # which task finishes first, advance() or client.connect().
        async def delayed_response(request):
            await asyncio.sleep(delay)
            return web.Response(json=rsrc.SESSION_GET_RESPONSE)
        self.daemon.response = delayed_response

        with self.assertRaises(TimeoutError) as cm:
            await asyncio.gather(self.advance(delay),
                                 self.client.connect())
        self.assertEqual(str(cm.exception),
                         'Timeout after %ds: %s' % (self.client.timeout, self.client.url))
        self.assert_cb_connected_called(calls=0)
        self.assert_cb_disconnected_called(calls=0)
        self.assert_cb_error_called(calls=1,
                                    args=[(self.client,)],
                                    kwargs=[{'error': cm.exception}])
