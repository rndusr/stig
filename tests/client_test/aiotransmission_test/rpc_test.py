from stig.client.aiotransmission.rpc import (TransmissionRPC, TransmissionURL)
from stig.client import (ClientError, ConnectionError, RPCError, AuthError)

import resources_aiotransmission as rsrc

import asynctest
import asyncio
from aiohttp import web
from aiohttp.test_utils import unused_port

import logging
log = logging.getLogger(__name__)


import unittest
class TestTransmissionURL(unittest.TestCase):
    def test_default_url(self):
        url = TransmissionURL()
        self.assertEqual(url.scheme, 'http')
        self.assertEqual(url.host, 'localhost')
        self.assertEqual(url.port, 9091)

    def test_default_scheme(self):
        url = TransmissionURL('localhost')
        self.assertEqual(url.scheme, 'http')

    def test_default_port(self):
        url = TransmissionURL('localhost')
        self.assertEqual(url.port, 9091)

    def test_default_path(self):
        url = TransmissionURL('localhost')
        self.assertEqual(url.path, '/transmission/rpc')


class TestTransmissionRPC(asynctest.ClockedTestCase):
    async def setUp(self):
        self.daemon = rsrc.FakeTransmissionDaemon(loop=self.loop)
        self.daemon.response = rsrc.SESSION_GET_RESPONSE   # Default response
        self.url = self.daemon.url
        await self.daemon.start()
        self.client = TransmissionRPC(self.url, loop=self.loop)

        self.cb_connected = rsrc.FakeCallback('cb_connected')
        self.cb_disconnected = rsrc.FakeCallback('cb_disconnected')
        self.cb_error = rsrc.FakeCallback('cb_error')
        self.client.on('connected', self.cb_connected)
        self.client.on('disconnected', self.cb_disconnected)
        self.client.on('error', self.cb_error)

    async def tearDown(self):
        await self.client.disconnect()
        await self.daemon.stop()

    def assert_not_connected_to(self, url):
        self.assertEqual(self.client.url, url)
        self.assertEqual(self.client.connected, False)
        self.assertEqual(self.client.version, None)
        self.assertEqual(self.client.rpcversion, None)
        self.assertEqual(self.client.rpcversionmin, None)

    def assert_connected_to(self, url):
        self.assertEqual(self.client.url, url)
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
                    self.assertRegex(str(v), str(kw_exp[k]))

    async def test_connect_to_good_url(self):
        # TransmissionRPC requests 'session-get' to test the connection and
        # set version properties.
        self.daemon.response = rsrc.SESSION_GET_RESPONSE

        self.assert_not_connected_to(self.url)
        await self.client.connect(self.url)
        self.assert_connected_to(self.url)
        self.assert_cb_connected_called(calls=1, args=[(self.url,)])
        self.assert_cb_disconnected_called(calls=0)
        self.assert_cb_error_called(calls=0)

        await self.client.disconnect()
        self.assert_not_connected_to(self.url)
        self.assert_cb_connected_called(calls=1, args=[(self.url,)])
        self.assert_cb_disconnected_called(calls=1, args=[(self.url,)])
        self.assert_cb_error_called(calls=0)

    async def test_authentication_with_good_url(self):
        self.client.url.user = 'foo'
        self.client.url.password = 'bar'

        self.assertEqual(str(self.client.url),
                         '%s://foo:bar@%s:%s%s' % (self.client.url.scheme,
                                                   self.client.url.host,
                                                   self.client.url.port,
                                                   self.client.url.path))
        # TransmissionRPC requests 'session-get' to test the connection and
        # set version properties.
        self.daemon.response = rsrc.SESSION_GET_RESPONSE

        self.assert_not_connected_to(self.url)
        await self.client.connect(self.url)

        self.assert_connected_to(self.url)
        self.assert_cb_connected_called(calls=1, args=[(self.url,)])
        self.assert_cb_disconnected_called(calls=0)
        self.assert_cb_error_called(calls=0)

        await self.client.disconnect()
        self.assert_not_connected_to(self.url)
        self.assert_cb_connected_called(calls=1, args=[(self.url,)])
        self.assert_cb_disconnected_called(calls=1, args=[(self.url,)])
        self.assert_cb_error_called(calls=0)

    async def test_connect_to_bad_url(self):
        bad_url = rsrc.make_url()
        with self.assertRaises(ConnectionError) as cm:
            await self.client.connect(bad_url)
        self.assertIn(str(bad_url), str(cm.exception))
        self.assert_cb_connected_called(calls=0)
        self.assert_cb_disconnected_called(calls=0)
        self.assert_cb_error_called(calls=1,
                                    args=[(bad_url,)],
                                    kwargs=[{'error': r'Connection failed.*'+str(bad_url)}])

    async def test_reconnect_to_same_url(self):
        self.assert_not_connected_to(self.url)

        await self.client.connect(self.url)
        url_id1 = id(self.client.url)
        self.assert_connected_to(self.url)
        self.assert_cb_connected_called(calls=1, args=[(self.url,)])
        self.assert_cb_disconnected_called(calls=0)
        self.assert_cb_error_called(calls=0)

        await self.client.connect()
        url_id2 = id(self.client.url)
        self.assertEqual(url_id1, url_id2)
        self.assert_connected_to(self.url)
        self.assert_cb_connected_called(calls=1, args=[(self.url,)])
        self.assert_cb_disconnected_called(calls=0)
        self.assert_cb_error_called(calls=0)

    async def test_reconnect_to_bad_url(self):
        self.assert_not_connected_to(self.url)

        await self.client.connect(self.url)
        self.assert_connected_to(self.url)
        self.assert_cb_connected_called(calls=1, args=[(self.url,)])
        self.assert_cb_disconnected_called(calls=0)
        self.assert_cb_error_called(calls=0)
        url_id1 = id(self.client.url)

        other_url = rsrc.make_url()
        with self.assertRaises(ConnectionError):
            await self.client.connect(other_url)
        url_id2 = id(self.client.other_url)
        self.assertNotEqual(url_id1, url_id2)

        self.assert_cb_connected_called(calls=1, args=[(self.url,)])
        self.assert_cb_disconnected_called(calls=1, args=[(self.url,)])
        self.assert_cb_error_called(calls=1,
                                    args=[(other_url,)],
                                    kwargs=[{'error': r'Connection failed.*'+str(other_url)}])

    async def test_RpcError_during_connect(self):
        self.assertEqual(self.client.connected, False)
        self.daemon.response = {'result': 'Error from daemon'}
        with self.assertRaises(RPCError) as cm:
            await self.client.connect()
        self.assertIn('Error from daemon', str(cm.exception))
        self.assertEqual(self.client.connected, False)

        self.assert_cb_connected_called(calls=0)
        self.assert_cb_disconnected_called(calls=0)
        self.assert_cb_error_called(calls=1,
                                    args=[(self.url,)],
                                    kwargs=[{'error': r'Error from daemon'}])

    async def test_RpcError_when_connected(self):
        msg = "I don't like the jib of your request"
        await self.client.connect()
        self.assertEqual(self.client.connected, True)
        self.assert_cb_connected_called(calls=1, args=[(self.url,)])

        self.daemon.response = {'result': msg}
        with self.assertRaises(RPCError) as cm:
            await self.client.invalid_rpc_method()
        self.assertIn(msg, str(cm.exception))
        self.assertEqual(self.client.connected, True)

        self.assert_cb_disconnected_called(calls=0)
        self.assert_cb_error_called(calls=1,
                                    args=[(self.url,)],
                                    kwargs=[{'error': msg}])

    async def test_ConnectionError_during_connect(self):
        await self.daemon.stop()
        with self.assertRaises(ConnectionError) as cm:
            await self.client.connect()
        self.assertIn(str(self.url), str(cm.exception))
        self.assertEqual(self.client.connected, False)

        self.assert_cb_connected_called(calls=0)
        self.assert_cb_disconnected_called(calls=0)
        self.assert_cb_error_called(calls=1,
                                    args=[(self.url,)],
                                    kwargs=[{'error': r'Connection failed.*'+str(self.url)}])

    async def test_ConnectionError_when_connected(self):
        await self.client.connect()
        self.assertEqual(self.client.connected, True)
        self.assert_cb_connected_called(calls=1, args=[(self.url,)])

        await self.daemon.stop()
        with self.assertRaises(ConnectionError) as cm:
            await self.client.torrent_get()
        self.assertIn(str(self.url), str(cm.exception))
        self.assertEqual(self.client.connected, False)

        self.assert_cb_disconnected_called(calls=1, args=[(self.url,)])
        self.assert_cb_error_called(calls=1,
                                    args=[(self.url,)],
                                    kwargs=[{'error': r'Connection failed.*'+str(self.url)}])

    async def test_AuthError_during_connect(self):
        self.daemon.response = web.Response(status=rsrc.AUTH_ERROR_CODE)
        with self.assertRaises(AuthError) as cm:
            await self.client.connect()
        self.assertIn('Authentication failed', str(cm.exception))
        self.assertIn(str(self.url), str(cm.exception))
        self.assertEqual(self.client.connected, False)

        self.assert_cb_connected_called(calls=0)
        self.assert_cb_disconnected_called(calls=0)
        self.assert_cb_error_called(calls=1,
                                    args=[(self.url,)],
                                    kwargs=[{'error': r'Authentication failed.*'+str(self.url)}])

    async def test_AuthError_when_connected(self):
        await self.client.connect()
        self.assertEqual(self.client.connected, True)
        self.daemon.response = web.Response(status=rsrc.AUTH_ERROR_CODE)
        with self.assertRaises(AuthError) as cm:
            await self.client.any_method()
        self.assertIn('Authentication failed', str(cm.exception))
        self.assertIn(str(self.url), str(cm.exception))
        self.assertEqual(self.client.connected, False)

        self.assert_cb_connected_called(calls=1, args=[(self.url,)])
        self.assert_cb_disconnected_called(calls=1, args=[(self.url,)])
        self.assert_cb_error_called(calls=1,
                                    args=[(self.url,)],
                                    kwargs=[{'error': r'Authentication failed.*'+str(self.url)}])

    async def test_malformed_json(self):
        # The daemon redirects some requests to the web interface in some
        # error cases like 404.
        self.daemon.response = '<html><body>Fake Web Interface</body></html>'

        wrong_path_url = TransmissionURL('{}/wrong_path'.format(self.url, self.client.url.path))
        with self.assertRaises(RPCError) as cm:
            await self.client.connect(wrong_path_url)
        self.assertIn('malformed JSON', str(cm.exception))
        self.assertEqual(self.client.connected, False)

        self.assert_cb_connected_called(calls=0)
        self.assert_cb_disconnected_called(calls=0)
        self.assert_cb_error_called(calls=1,
                                    args=[(wrong_path_url,)],
                                    kwargs=[{'error': r'malformed JSON'}])

    async def test_timeout_minus_one(self):
        delay = self.client.timeout-1
        await asyncio.gather(self.advance(delay),
                             self.client.connect(),
                             loop=self.loop)
        await self.client.disconnect()

        self.assert_cb_connected_called(calls=1, args=[(self.url,)])
        self.assert_cb_disconnected_called(calls=1, args=[(self.url,)])
        self.assert_cb_error_called(calls=0)

    async def test_timeout_plus_one(self):
        delay = self.client.timeout+1

        # NOTE: This function is only called sometimes, probably depending on
        # which task finishes first, advance() or client.connect().
        async def delay_response(request):
            await asyncio.sleep(delay, loop=self.loop)
            return web.json_response(rsrc.SESSION_GET_RESPONSE)
        self.daemon.response = delay_response

        with self.assertRaises(ConnectionError) as cm:
            await asyncio.gather(self.advance(delay),
                                 self.client.connect(),
                                 loop=self.loop)
        self.assertIn('timeout', str(cm.exception).lower())
        self.assertIn(str(self.client.timeout), str(cm.exception))
        self.assertIn(str(self.url), str(cm.exception))

        self.assert_cb_connected_called(calls=0)
        self.assert_cb_disconnected_called(calls=0)
        self.assert_cb_error_called(calls=1,
                                    args=[(self.url,)],
                                    kwargs=[{'error': r'{}.*{}'.format(self.client.timeout,
                                                                       self.url)}])
