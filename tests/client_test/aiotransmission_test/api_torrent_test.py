import os.path
import unittest
from unittest.mock import patch

import resources_aiotransmission as rsrc

from stig.client import MAX_TORRENT_FILE_SIZE
from stig.client.aiotransmission.api_torrent import TorrentAPI
from stig.client.aiotransmission.rpc import TransmissionRPC
from stig.client.aiotransmission.torrent import Torrent
from stig.client.filters.torrent import TorrentFilter

assert os.path.exists(rsrc.TORRENTFILE)
assert not os.path.exists(rsrc.TORRENTFILE_NOEXIST)


class TorrentAPITestCase(unittest.IsolatedAsyncioTestCase):
    # Whether the fake daemon speaks JSON-RPC 2.0 (i.e. is Transmission >=4.1.0)
    jsonrpc = False

    async def asyncSetUp(self):
        self.daemon = rsrc.FakeTransmissionDaemon(jsonrpc=self.jsonrpc)
        await self.daemon.start()
        self.rpc = TransmissionRPC(self.daemon.host, self.daemon.port)
        self.api = TorrentAPI(self.rpc)
        await self.rpc.connect()
        assert self.rpc.connected is True

    async def asyncTearDown(self):
        await self.rpc.disconnect()
        await self.daemon.stop()


class TestConnection(TorrentAPITestCase):
    async def test_send_request_with_lost_connection(self):
        assert self.rpc.connected is True
        await self.daemon.stop()
        response = await self.api.torrents()
        self.assertEqual(response.success, False)
        self.assertEqual(response.torrents, ())
        self.assertEqual(response.msgs, ())
        self.assertTrue('Failed to connect: ' in response.errors[0])


class TestAddingTorrents(TorrentAPITestCase):
    async def test_add_torrent_by_local_file(self):
        self.daemon.response = rsrc.response_success(
            {'torrent-added': {'id': 1,
                               'name': 'Test Torrent',
                               'hashString': rsrc.TORRENTHASH}}
        )
        response = await self.api.add(rsrc.TORRENTFILE)
        self.assertEqual(response.success, True)
        self.assertEqual(response.torrent, Torrent({'id': 1, 'name': 'Test Torrent'}))
        self.assertEqual(response.msgs, ('Added Test Torrent',))
        self.assertEqual(response.errors, ())

    async def test_add_torrent_by_nonexisting_file(self):
        self.daemon.response = rsrc.response_failure(
            'invalid or corrupt torrent file'
        )
        response = await self.api.add(rsrc.TORRENTFILE_NOEXIST)
        self.assertEqual(response.success, False)
        self.assertEqual(response.torrent, None)
        self.assertEqual(response.msgs, ())
        self.assertEqual(response.errors,
                         ('Torrent file is corrupt or doesn\'t exist: %r' % rsrc.TORRENTFILE_NOEXIST,))

    @patch('os.path.exists', return_value=True)
    @patch('os.path.getsize', return_value=int(MAX_TORRENT_FILE_SIZE) + 1)
    async def test_add_torrent_by_giant_file(self, _, __):
        response = await self.api.add('some.torrent')
        self.assertEqual(response.success, False)
        self.assertEqual(response.torrent, None)
        self.assertEqual(response.msgs, ())
        e = 'some.torrent is bigger than %s: %s (%s bytes)' % (
            MAX_TORRENT_FILE_SIZE, MAX_TORRENT_FILE_SIZE + 1, int(MAX_TORRENT_FILE_SIZE) + 1)
        self.assertEqual(response.errors, (e,))

    async def test_add_torrent_by_hash(self):
        self.daemon.response = rsrc.response_success(
            {'torrent-added': {'id': 1,
                               'name': rsrc.TORRENTHASH,
                               'hashString': rsrc.TORRENTHASH}}
        )
        response = await self.api.add(rsrc.TORRENTHASH)
        self.assertEqual(response.success, True)
        self.assertEqual(response.torrent, Torrent({'id': 1, 'name': rsrc.TORRENTHASH}))
        self.assertEqual(response.msgs, ('Added %s' % rsrc.TORRENTHASH,))
        self.assertEqual(response.errors, ())


class TestGettingTorrents(TorrentAPITestCase):
    async def test_get_all_torrents(self):
        self.daemon.response = rsrc.response_torrents(
            {'id': 1, 'name': 'Torrent1'},
            {'id': 2, 'name': 'Torrent2'},
        )
        response = await self.api.torrents()
        self.assertEqual(response.success, True)
        self.assertEqual(response.torrents,
                         (Torrent({'id': 1, 'name': 'Torrent1'}),
                          Torrent({'id': 2, 'name': 'Torrent2'})))
        self.assertEqual(response.msgs, ())
        self.assertEqual(response.errors, ())

    async def test_get_torrents_by_ids(self):
        self.daemon.response = rsrc.response_torrents(
            {'id': 1, 'name': 'Torrent1'},
            {'id': 2, 'name': 'Torrent2'},
            {'id': 3, 'name': 'Torrent3'},
        )
        response = await self.api.torrents(torrents=(1, 3))
        self.assertEqual(response.success, True)
        self.assertEqual(response.torrents,
                         (Torrent({'id': 1, 'name': 'Torrent1'}),
                          Torrent({'id': 3, 'name': 'Torrent3'})))
        self.assertEqual(response.msgs, ())
        self.assertEqual(response.errors, ())

        response = await self.api.torrents(torrents=(2,))
        self.assertEqual(response.success, True)
        self.assertEqual(response.torrents,
                         (Torrent({'id': 2, 'name': 'Torrent2'}),))
        self.assertEqual(response.msgs, ())
        self.assertEqual(response.errors, ())

        response = await self.api.torrents(torrents=())
        self.assertEqual(response.success, True)
        self.assertEqual(response.torrents, ())
        self.assertEqual(response.msgs, ())
        self.assertEqual(response.errors, ())

        response = await self.api.torrents(torrents=(4, 5))
        self.assertEqual(response.success, False)
        self.assertEqual(response.torrents, ())
        self.assertEqual(response.msgs, ())
        self.assertEqual(response.errors, ('No torrent with ID: 4', 'No torrent with ID: 5'))

    async def test_get_torrents_by_filter(self):
        self.daemon.response = rsrc.response_torrents(
            {'id': 1, 'name': 'Foo'},
            {'id': 2, 'name': 'Bar'},
            {'id': 3, 'name': 'Boo'},
        )
        response = await self.api.torrents(torrents=TorrentFilter('name=Foo'))
        self.assertEqual(response.success, True)
        self.assertEqual(response.torrents,
                         (Torrent({'id': 1, 'name': 'Foo'}),))
        self.assertEqual(response.msgs, ('Found 1 =Foo torrent',))
        self.assertEqual(response.errors, ())

        response = await self.api.torrents(torrents=TorrentFilter('name~oo'))
        self.assertEqual(response.success, True)
        self.assertEqual(response.torrents,
                         (Torrent({'id': 1, 'name': 'Foo'}),
                          Torrent({'id': 3, 'name': 'Boo'})))
        self.assertEqual(response.msgs, ('Found 2 ~oo torrents',))
        self.assertEqual(response.errors, ())

        response = await self.api.torrents(torrents=TorrentFilter('name=Nope'))
        self.assertEqual(response.success, False)
        self.assertEqual(response.torrents, ())
        self.assertEqual(response.msgs, ())
        self.assertEqual(response.errors, ('No matching torrents: =Nope',))


class TestManipulatingTorrents(TorrentAPITestCase):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.mock_method_args = None
        self.mock_method_kwargs = None
        self.daemon.response = rsrc.response_torrents(
            {'id': 1, 'name': 'Foo'},
            {'id': 2, 'name': 'Bar'},
            {'id': 3, 'name': 'Boo'},
        )

    async def mock_method(self, ids, **kwargs):
        self.mock_method_args = ids
        self.mock_method_kwargs = kwargs
        # None of the RPC methods for torrents have return values,
        # so we return nothing

    async def test_no_torrents_found(self):
        response = await self.api._torrent_action(
            torrents=TorrentFilter('id=4'),
            method=self.mock_method,
        )
        self.assertEqual(self.mock_method_args, None)
        self.assertEqual(self.mock_method_kwargs, None)
        self.assertEqual(response.success, False)
        self.assertEqual(response.torrents, ())
        self.assertEqual(response.msgs, ())
        self.assertEqual(response.errors, ('No matching torrents: id=4',))

    async def test_rpc_method_without_kwargs(self):
        response = await self.api._torrent_action(
            torrents=TorrentFilter('id=4|id=3'),
            method=self.mock_method,
        )
        self.assertEqual(self.mock_method_args, (3,))
        self.assertEqual(self.mock_method_kwargs, {})
        self.assertEqual(response.success, True)
        self.assertEqual(response.torrents,
                         (Torrent({'id': 3, 'name': 'Boo'}),))
        self.assertEqual(response.msgs, ('Found 1 id=4|id=3 torrent',))
        self.assertEqual(response.errors, ())

    async def test_rpc_method_with_kwargs(self):
        response = await self.api._torrent_action(
            torrents=TorrentFilter('name~B'),
            method=self.mock_method, method_args={'foo': 'bar'},
        )
        self.assertEqual(self.mock_method_args, (2,3))
        self.assertEqual(self.mock_method_kwargs, {'foo': 'bar'})
        self.assertEqual(response.success, True)
        self.assertEqual(response.torrents,
                         (Torrent({'id': 2, 'name': 'Bar'}),
                          Torrent({'id': 3, 'name': 'Boo'}),))
        self.assertEqual(response.msgs, ('Found 2 ~B torrents',))
        self.assertEqual(response.errors, ())

    async def test_rpc_method_without_filter(self):
        response = await self.api._torrent_action(
            method=self.mock_method,
        )
        self.assertEqual(self.mock_method_args, (1, 2, 3))  # All torrents
        self.assertEqual(self.mock_method_kwargs, {})
        self.assertEqual(response.success, True)
        self.assertEqual(response.torrents,
                         (Torrent({'id': 1, 'name': 'Foo'}),
                          Torrent({'id': 2, 'name': 'Bar'}),
                          Torrent({'id': 3, 'name': 'Boo'}),))
        self.assertEqual(response.msgs, ())
        self.assertEqual(response.errors, ())

    async def test_check_function(self):
        wanted_keys = ('id', 'name')

        def check_func(torrent):
            self.assertEqual(set(torrent), set(wanted_keys))

            if 'oo' in torrent['name']:
                return (True, 'hit: #%d, %s' % (torrent['id'], torrent['name']))
            else:
                return (False, 'miss: #%d, %s' % (torrent['id'], torrent['name']))

        response = await self.api._torrent_action(
            method=self.mock_method,
            check=check_func, check_keys=wanted_keys,
        )
        self.assertEqual(self.mock_method_args, (1, 3))
        self.assertEqual(self.mock_method_kwargs, {})
        self.assertEqual(response.success, True)
        self.assertEqual(response.torrents,
                         (Torrent({'id': 1, 'name': 'Foo'}),
                          Torrent({'id': 3, 'name': 'Boo'}),))
        self.assertEqual(response.msgs, ('hit: #1, Foo', 'hit: #3, Boo'))
        self.assertEqual(response.errors, ('miss: #2, Bar',))


class TestTorrentBandwidthLimit(TorrentAPITestCase):
    def assert_request(self, expected_request):
        # Because order doesn't matter, replace lists with sets to make requests comparable
        def comparable_request(request):
            cmp_req = {}
            for k,v in request.items():
                if isinstance(v, (str, int, float)):
                    cmp_req[k] = v
                elif isinstance(v, list):
                    cmp_req[k] = set(v)
                else:
                    cmp_req[k] = comparable_request(v)
            return cmp_req

        existing_reqs = tuple(map(comparable_request, self.daemon.requests))
        expected_req = comparable_request(expected_request)
        self.assertIn(expected_req, existing_reqs)


    async def test_disable_rate_limit(self):
        self.daemon.response = rsrc.response_torrents(
            {'id': 1, 'name': 'Foo', 'uploadLimit': 100, 'uploadLimited': True},
            {'id': 2, 'name': 'Bar', 'uploadLimit': 200, 'uploadLimited': True},
        )
        response = await self.api.set_limit_rate_up(TorrentFilter('id=1|id=2'), False)
        self.assert_request({'method': 'torrent-set',
                             'arguments': {'ids': [1, 2], 'uploadLimited': False}})
        self.assertEqual(response.success, True)

    async def test_enable_rate_limit(self):
        self.daemon.response = rsrc.response_torrents(
            {'id': 1, 'name': 'Foo', 'uploadLimit': 100, 'uploadLimited': False},
            {'id': 2, 'name': 'Bar', 'uploadLimit': 200, 'uploadLimited': False},
        )
        response = await self.api.set_limit_rate_up(TorrentFilter('id=1|id=2'), True)
        self.assert_request({'method': 'torrent-set',
                             'arguments': {'ids': [1, 2], 'uploadLimited': True}})
        self.assertEqual(response.success, True)

    async def test_set_absolute_rate_limit(self):
        self.daemon.response = rsrc.response_torrents(
            {'id': 1, 'name': 'Foo', 'uploadLimit': 100, 'uploadLimited': False},
            {'id': 2, 'name': 'Bar', 'uploadLimit': 200, 'uploadLimited': True},
        )
        await self.api.set_limit_rate_up(TorrentFilter('id=1|id=2'), 1e6)
        self.assert_request({'method': 'torrent-set',
                             'arguments': {'ids': [1, 2], 'uploadLimited': True,
                                           'uploadLimit': 1000}})

    async def test_add_to_current_limit_when_enabled(self):
        self.daemon.response = rsrc.response_torrents(
            {'id': 1, 'name': 'Foo', 'uploadLimit': 100, 'uploadLimited': True},
            {'id': 2, 'name': 'Bar', 'uploadLimit': 200, 'uploadLimited': True},
        )
        await self.api.adjust_limit_rate_up(TorrentFilter('id=1|id=2'), 50e3)
        self.assert_request({'method': 'torrent-set',
                             'arguments': {'ids': [1], 'uploadLimited': True,
                                           'uploadLimit': 150}})
        self.assert_request({'method': 'torrent-set',
                             'arguments': {'ids': [2], 'uploadLimited': True,
                                           'uploadLimit': 250}})

    async def test_subtract_from_current_limit_when_enabled(self):
        self.daemon.response = rsrc.response_torrents(
            {'id': 1, 'name': 'Foo', 'uploadLimit': 100, 'uploadLimited': True},
            {'id': 2, 'name': 'Bar', 'uploadLimit': 200, 'uploadLimited': True},
        )
        await self.api.adjust_limit_rate_up(TorrentFilter('id=1|id=2'), -50e3)
        self.assert_request({'method': 'torrent-set',
                             'arguments': {'ids': [1], 'uploadLimited': True,
                                           'uploadLimit': 50}})
        self.assert_request({'method': 'torrent-set',
                             'arguments': {'ids': [2], 'uploadLimited': True,
                                           'uploadLimit': 150}})

    async def test_add_to_current_limit_when_disabled(self):
        self.daemon.response = rsrc.response_torrents(
            {'id': 1, 'name': 'Foo', 'uploadLimit': 100, 'uploadLimited': False},
            {'id': 2, 'name': 'Bar', 'uploadLimit': 200, 'uploadLimited': False},
        )
        await self.api.adjust_limit_rate_up(TorrentFilter('id=1|id=2'), 50e3)
        self.assert_request({'method': 'torrent-set',
                             'arguments': {'ids': [1,2], 'uploadLimited': True,
                                           'uploadLimit': 50}})

    async def test_subtract_from_current_limit_when_disabled(self):
        self.daemon.response = rsrc.response_torrents(
            {'id': 1, 'name': 'Foo', 'uploadLimit': 100, 'uploadLimited': False},
            {'id': 2, 'name': 'Bar', 'uploadLimit': 200, 'uploadLimited': False},
        )
        await self.api.adjust_limit_rate_up(TorrentFilter('id=1|id=2'), -50e3)
        self.daemon.requests == ()  # Assert no requests were sent


class TestSequentialDownload(TorrentAPITestCase):
    jsonrpc = True

    def assert_request(self, method, params):
        """Assert that a request with `method` and exactly `params` was sent"""
        sent = tuple((rq.get('method'), rq.get('params')) for rq in self.daemon.requests)
        self.assertIn((method, params), sent)

    async def test_enable(self):
        self.daemon.response = rsrc.response_torrents_jsonrpc(
            {'id': 1, 'name': 'Foo'},
            {'id': 2, 'name': 'Bar'},
        )
        response = await self.api.set_sequential(TorrentFilter('id=1|id=2'), True)
        self.assert_request('torrent_set', {'ids': [1, 2],
                                            'sequential_download': True,
                                            'sequential_download_from_piece': 0})
        self.assertEqual(response.success, True)
        self.assertEqual(response.errors, ())
        self.assertIn('Foo: Sequential download from piece #0', response.msgs)
        self.assertIn('Bar: Sequential download from piece #0', response.msgs)

    async def test_enable_from_piece(self):
        self.daemon.response = rsrc.response_torrents_jsonrpc({'id': 1, 'name': 'Foo'})
        response = await self.api.set_sequential(TorrentFilter('id=1'), True, 1200)
        self.assert_request('torrent_set', {'ids': [1],
                                            'sequential_download': True,
                                            'sequential_download_from_piece': 1200})
        self.assertEqual(response.success, True)
        self.assertIn('Foo: Sequential download from piece #1200', response.msgs)

    async def test_disable_leaves_starting_piece_alone(self):
        self.daemon.response = rsrc.response_torrents_jsonrpc({'id': 1, 'name': 'Foo'})
        response = await self.api.set_sequential(TorrentFilter('id=1'), False, 1200)
        self.assert_request('torrent_set', {'ids': [1], 'sequential_download': False})
        self.assertEqual(response.success, True)
        self.assertIn('Foo: Non-sequential download', response.msgs)

    async def test_toggle_sends_one_request_per_mode(self):
        self.daemon.response = rsrc.response_torrents_jsonrpc(
            {'id': 1, 'name': 'Foo', 'sequential_download': True,
             'sequential_download_from_piece': 0},
            {'id': 2, 'name': 'Bar', 'sequential_download': False,
             'sequential_download_from_piece': 0},
            {'id': 3, 'name': 'Baz', 'sequential_download': True,
             'sequential_download_from_piece': 0},
        )
        response = await self.api.toggle_sequential(TorrentFilter('id=1|id=2|id=3'), 500)
        self.assert_request('torrent_set', {'ids': [2],
                                            'sequential_download': True,
                                            'sequential_download_from_piece': 500})
        self.assert_request('torrent_set', {'ids': [1, 3], 'sequential_download': False})
        self.assertEqual(response.success, True)

    async def test_torrent_get_asks_for_sequential_fields(self):
        self.daemon.response = rsrc.response_torrents_jsonrpc({'id': 1, 'name': 'Foo'})
        await self.api.torrents(TorrentFilter('id=1'),
                                keys=('sequential', 'sequential-from-piece'))
        fields = set()
        for rq in self.daemon.requests:
            if rq.get('method') == 'torrent_get':
                fields.update(rq['params']['fields'])
        self.assertIn('sequential_download', fields)
        self.assertIn('sequential_download_from_piece', fields)


class TestSequentialDownloadUnsupported(TorrentAPITestCase):
    # A daemon that only speaks the old protocol is older than 4.1.0
    jsonrpc = False

    async def test_set_sequential(self):
        response = await self.api.set_sequential(TorrentFilter('id=1'), True)
        self.assertEqual(response.success, False)
        self.assertEqual(response.torrents, ())
        self.assertEqual(response.errors, ('Daemon does not support sequential download (needs Transmission 4.1.0 or newer)',))
        # Only the requests that established the connection were sent
        self.assertNotIn('torrent-set',
                         tuple(rq.get('method') for rq in self.daemon.requests))

    async def test_toggle_sequential(self):
        response = await self.api.toggle_sequential(TorrentFilter('id=1'))
        self.assertEqual(response.success, False)
        self.assertEqual(response.errors, ('Daemon does not support sequential download (needs Transmission 4.1.0 or newer)',))
        # Only the requests that established the connection were sent
        self.assertNotIn('torrent-set',
                         tuple(rq.get('method') for rq in self.daemon.requests))
