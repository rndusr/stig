import unittest
from contextlib import asynccontextmanager

import resources_aiotransmission as rsrc

from stig.client import RPCError
from stig.client.aiotransmission import apicompat
from stig.client.aiotransmission.rpc import SemVer, TransmissionRPC


@asynccontextmanager
async def fake_daemon(jsonrpc):
    daemon = rsrc.FakeTransmissionDaemon(jsonrpc=jsonrpc)
    await daemon.start()
    client = TransmissionRPC(daemon.host, daemon.port)
    try:
        yield daemon, client
    finally:
        await client.disconnect()
        await daemon.stop()


def requests_for(daemon, method):
    return [rq for rq in daemon.requests if rq.get('method') == method]


class TestProtocolNegotiation(unittest.IsolatedAsyncioTestCase):
    async def test_jsonrpc_is_preferred(self):
        async with fake_daemon(jsonrpc=True) as (daemon, client):
            await client.connect()
            self.assertEqual(client.protocol, 'JSON-RPC 2.0')
            self.assertEqual(client.version, '4.1.0 (1234567890)')
            self.assertEqual(client.rpcversion, 18)
            self.assertEqual(client.rpcversionmin, 1)
            self.assertEqual(client.rpcversion_semver, (6, 0, 0))
            # The old protocol was never tried
            self.assertEqual(requests_for(daemon, 'session-get'), [])

    async def test_fall_back_to_legacy_protocol(self):
        async with fake_daemon(jsonrpc=False) as (daemon, client):
            await client.connect()
            self.assertEqual(client.protocol, 'RPC')
            self.assertEqual(client.version, '2.84 (14307)')
            self.assertEqual(client.rpcversion, 15)
            self.assertEqual(client.rpcversionmin, 1)
            # Daemons older than 5.3.0 don't report 'rpc-version-semver'
            self.assertIs(client.rpcversion_semver, None)
            # JSON-RPC 2.0 was tried first and refused
            self.assertNotEqual(requests_for(daemon, 'session_get'), [])

    async def test_deprecated_rpc_version_is_optional(self):
        # 'rpc-version' is deprecated in favour of 'rpc-version-semver' and may
        # be gone from future daemons
        async with fake_daemon(jsonrpc=True) as (daemon, client):
            session = {key: value
                       for key, value in rsrc.SESSION_GET_RESPONSE_JSONRPC['result'].items()
                       if key not in ('rpc_version', 'rpc_version_minimum')}
            daemon.response = rsrc.response_success_jsonrpc(session)
            await client.connect()
            self.assertIs(client.connected, True)
            self.assertIs(client.rpcversion, None)
            self.assertIs(client.rpcversionmin, None)
            self.assertEqual(client.rpcversion_semver, (6, 0, 0))

    async def test_rpc_version_semver_is_forgotten_on_disconnect(self):
        async with fake_daemon(jsonrpc=True) as (daemon, client):
            await client.connect()
            self.assertEqual(client.rpcversion_semver, (6, 0, 0))
            await client.disconnect()
            self.assertIs(client.rpcversion_semver, None)

    async def test_protocol_is_forgotten_on_disconnect(self):
        async with fake_daemon(jsonrpc=True) as (daemon, client):
            await client.connect()
            self.assertEqual(client.protocol, 'JSON-RPC 2.0')
            await client.disconnect()
            self.assertIs(client.protocol, None)

    async def test_unknown_protocol(self):
        async with fake_daemon(jsonrpc=True) as (daemon, client):
            daemon.response = {'something': 'else'}
            with self.assertRaises(RPCError) as cm:
                await client.connect()
            self.assertEqual(str(cm.exception),
                             f'Invalid RPC response: Not a Transmission daemon: {client.url}')
            self.assertIs(client.connected, False)


class TestJSONRPCRequests(unittest.IsolatedAsyncioTestCase):
    async def test_request_format(self):
        async with fake_daemon(jsonrpc=True) as (daemon, client):
            await client.connect()
            daemon.response = rsrc.response_success_jsonrpc({'torrents': []})
            await client.torrent_get(fields=('id', 'downloadDir', 'uploadRatio'), ids=(1, 2))
            request = requests_for(daemon, 'torrent_get')[-1]
            self.assertEqual(request['jsonrpc'], '2.0')
            self.assertEqual(request['params'], {'fields': ['id', 'download_dir', 'upload_ratio'],
                                                 'ids': [1, 2]})
            self.assertIsInstance(request['id'], int)

    async def test_request_ids_are_unique(self):
        async with fake_daemon(jsonrpc=True) as (daemon, client):
            await client.connect()
            daemon.response = rsrc.response_success_jsonrpc({})
            await client.torrent_start(ids=(1,))
            await client.torrent_stop(ids=(1,))
            # A request that is resent because of a CSRF error keeps its id, so
            # only compare the ids of different requests.
            self.assertNotEqual(requests_for(daemon, 'torrent_start')[-1]['id'],
                                requests_for(daemon, 'torrent_stop')[-1]['id'])

    async def test_torrents_are_unpacked_and_translated(self):
        async with fake_daemon(jsonrpc=True) as (daemon, client):
            await client.connect()
            daemon.response = rsrc.response_success_jsonrpc({
                'torrents': [{'id': 1,
                              'name': 'Foo',
                              'download_dir': '/tmp',
                              'upload_ratio': 1.5,
                              'wanted': [True, False],
                              'tracker_stats': [{'seeder_count': 5,
                                                 'last_announce_result': 'Success'}]}]
            })
            torrents = await client.torrent_get(fields=('id',))
            self.assertEqual(torrents, [{'id': 1,
                                         'name': 'Foo',
                                         'downloadDir': '/tmp',
                                         'uploadRatio': 1.5,
                                         'wanted': [1, 0],
                                         'trackerStats': [{'seederCount': 5,
                                                           'lastAnnounceResult': 'Success'}]}])

    async def test_arguments_are_translated(self):
        async with fake_daemon(jsonrpc=True) as (daemon, client):
            await client.connect()
            daemon.response = rsrc.response_success_jsonrpc({})
            await client.session_set({'alt-speed-down': 100, 'download-dir': '/tmp'})
            request = requests_for(daemon, 'session_set')[-1]
            self.assertEqual(request['params'], {'alt_speed_down': 100, 'download_dir': '/tmp'})

    async def test_response_without_torrents(self):
        async with fake_daemon(jsonrpc=True) as (daemon, client):
            await client.connect()
            daemon.response = rsrc.response_success_jsonrpc({'path': '/tmp',
                                                             'size_bytes': 123,
                                                             'total_size': 456})
            response = await client.free_space(path='/tmp')
            self.assertEqual(response, {'path': '/tmp', 'size-bytes': 123, 'total_size': 456})


class TestJSONRPCErrors(unittest.IsolatedAsyncioTestCase):
    async def test_error_message(self):
        async with fake_daemon(jsonrpc=True) as (daemon, client):
            await client.connect()
            daemon.response = rsrc.response_failure_jsonrpc(-32601, 'Method not found')
            with self.assertRaises(RPCError) as cm:
                await client.no_such_method()
            self.assertEqual(str(cm.exception), 'Invalid RPC response: Method not found')
            # An RPCError means we're still connected
            self.assertIs(client.connected, True)

    async def test_error_message_with_details(self):
        async with fake_daemon(jsonrpc=True) as (daemon, client):
            await client.connect()
            daemon.response = rsrc.response_failure_jsonrpc(
                7, 'HTTP error from backend service', "Couldn't test port: No Response (0)")
            with self.assertRaises(RPCError) as cm:
                await client.port_test()
            self.assertEqual(str(cm.exception),
                             'Invalid RPC response: HTTP error from backend service: '
                             "Couldn't test port: No Response (0)")

    async def test_error_during_connect(self):
        async with fake_daemon(jsonrpc=True) as (daemon, client):
            daemon.response = rsrc.response_failure_jsonrpc(-32603, 'Internal error')
            with self.assertRaises(RPCError) as cm:
                await client.connect()
            self.assertEqual(str(cm.exception), 'Invalid RPC response: Internal error')
            self.assertIs(client.connected, False)


class TestLegacyProtocol(unittest.IsolatedAsyncioTestCase):
    async def test_request_format_is_unchanged(self):
        async with fake_daemon(jsonrpc=False) as (daemon, client):
            await client.connect()
            daemon.response = rsrc.response_torrents({'id': 1, 'name': 'Foo'})
            torrents = await client.torrent_get(fields=('id', 'downloadDir'))
            request = requests_for(daemon, 'torrent-get')[-1]
            self.assertNotIn('jsonrpc', request)
            self.assertEqual(request['arguments'], {'fields': ['id', 'downloadDir']})
            self.assertEqual(torrents, [{'id': 1, 'name': 'Foo'}])

    async def test_error_message(self):
        async with fake_daemon(jsonrpc=False) as (daemon, client):
            await client.connect()
            daemon.response = rsrc.response_failure('something went wrong')
            with self.assertRaises(RPCError) as cm:
                await client.torrent_get()
            self.assertEqual(str(cm.exception), 'Invalid RPC response: Something went wrong')


class TestAPICompat(unittest.TestCase):
    def test_all_names_are_translated_back_and_forth(self):
        for current, legacy in apicompat._RPC_KEYS:
            self.assertEqual(apicompat.TO_CURRENT[legacy], current)
            self.assertEqual(apicompat.TO_LEGACY[current], legacy)

    def test_unknown_names_are_left_alone(self):
        self.assertEqual(apicompat.request_to_current(
            'torrent_get', {'fields': ['announceURL'], 'ids': ['b0b1']}
        ), {'fields': ['announceURL'], 'ids': ['b0b1']})

    def test_download_dir_depends_on_context(self):
        self.assertEqual(apicompat.response_to_legacy(
            'torrent_get', {'torrents': [{'download_dir': '/tmp'}]}
        ), {'torrents': [{'downloadDir': '/tmp'}]})
        self.assertEqual(apicompat.response_to_legacy(
            'session_get', {'download_dir': '/tmp'}
        ), {'download-dir': '/tmp'})
        for legacy in ('downloadDir', 'download-dir'):
            self.assertEqual(apicompat.request_to_current(
                'torrent_add', {legacy: '/tmp'}
            ), {'download_dir': '/tmp'})

    def test_total_size_depends_on_context(self):
        self.assertEqual(apicompat.response_to_legacy(
            'torrent_get', {'torrents': [{'total_size': 5}]}
        ), {'torrents': [{'totalSize': 5}]})
        self.assertEqual(apicompat.response_to_legacy(
            'free_space', {'total_size': 5}
        ), {'total_size': 5})

    def test_nested_names_are_translated(self):
        self.assertEqual(apicompat.response_to_legacy(
            'session_get', {'units': {'speed_bytes': 1000, 'size_units': ['kB']}}
        ), {'units': {'speed-bytes': 1000, 'size-units': ['kB']}})


class TestTorrentAPIOverJSONRPC(unittest.IsolatedAsyncioTestCase):
    async def test_torrents(self):
        from stig.client.aiotransmission.api_torrent import TorrentAPI

        async with fake_daemon(jsonrpc=True) as (daemon, client):
            api = TorrentAPI(client)
            await client.connect()
            self.assertEqual(client.protocol, 'JSON-RPC 2.0')
            daemon.response = rsrc.response_success_jsonrpc({
                'torrents': [{'id': 1, 'name': 'Foo', 'upload_ratio': 2.5, 'download_dir': '/tmp'},
                             {'id': 2, 'name': 'Bar', 'upload_ratio': 0.5, 'download_dir': '/tmp'}]
            })
            response = await api.torrents(keys=('id', 'name', 'ratio', 'path'))
            self.assertIs(response.success, True)
            self.assertEqual([(t['id'], t['name'], t['ratio'], t['path'])
                              for t in response.torrents],
                             [(1, 'Foo', 2.5, '/tmp'), (2, 'Bar', 0.5, '/tmp')])
            # The daemon got snake_case field names
            request = requests_for(daemon, 'torrent_get')[-1]
            self.assertEqual(set(request['params']['fields']),
                             {'id', 'name', 'upload_ratio', 'download_dir'})


class TestSemVer(unittest.TestCase):
    def test_parsing(self):
        self.assertEqual(SemVer.parse('5.3.0'), (5, 3, 0))
        self.assertEqual(SemVer.parse('6.0.0-beta.1+42'), (6, 0, 0))
        self.assertEqual(SemVer.parse('6.0'), (6, 0))

    def test_parsing_garbage(self):
        for string in (None, '', 'foo', '1.x.3'):
            self.assertIs(SemVer.parse(string), None)

    def test_comparison(self):
        self.assertTrue(SemVer.parse('5.2.0') < (5, 3, 0))
        self.assertFalse(SemVer.parse('5.3.0') < (5, 3, 0))
        self.assertFalse(SemVer.parse('6.0.0') < (5, 3, 0))

    def test_string_representation(self):
        self.assertEqual(str(SemVer.parse('6.0.0')), '6.0.0')
        self.assertEqual(repr(SemVer.parse('6.0.0')), "SemVer('6.0.0')")
