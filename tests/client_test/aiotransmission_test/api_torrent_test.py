from stig.client.aiotransmission.api_torrent import TorrentAPI
from stig.client.aiotransmission.rpc import TransmissionRPC
from stig.client.aiotransmission.torrent import Torrent
from stig.client import errors
from stig.client.filters.tfilter import TorrentFilter

import resources_aiotransmission as rsrc

import asynctest
import os.path
assert os.path.exists(rsrc.TORRENTFILE)
assert not os.path.exists(rsrc.TORRENTFILE_NOEXIST)


class TorrentAPITestCase(asynctest.TestCase):
    async def setUp(self):
        self.daemon = rsrc.FakeTransmissionDaemon(loop=self.loop)
        await self.daemon.start()
        self.rpc = TransmissionRPC(self.daemon.host, self.daemon.port, loop=self.loop)
        self.api = TorrentAPI(self.rpc)
        await self.rpc.connect()
        assert self.rpc.connected == True

    async def tearDown(self):
        await self.rpc.disconnect()
        await self.daemon.stop()

    def assert_torrentkeys_equal(self, key, tlist, *exp):
        self.assertEqual(tuple(t[key] for t in tlist), exp)


class TestConnection(TorrentAPITestCase):
    async def test_send_request_with_lost_connection(self):
        assert self.rpc.connected == True
        await self.daemon.stop()
        response = await self.api.torrents()
        self.assertEqual(response.success, False)
        self.assertEqual(response.torrents, ())


class TestAddingTorrents(TorrentAPITestCase):
    async def test_add_torrent_by_local_file(self):
        self.daemon.response = rsrc.response_success(
            {'torrent-added': { 'id': 1,
                                'name': 'Test Torrent',
                                'hashString': rsrc.TORRENTHASH}}
        )
        response = await self.api.add(rsrc.TORRENTFILE)
        self.assertEqual(response.success, True)
        self.assertEqual(response.torrent, Torrent({'id': 1, 'name': 'Test Torrent'}))

    async def test_add_torrent_by_nonexisting_file(self):
        self.daemon.response = rsrc.response_failure(
            'File does not exist or something'
        )
        response = await self.api.add(rsrc.TORRENTFILE_NOEXIST)
        self.assertEqual(response.success, False)
        self.assertEqual(response.torrent, None)
        self.assertEqual(len(response.msgs), 1)
        self.assertIsInstance(response.msgs[0], errors.ClientError)
        self.assertIn('File does not exist or something', str(response.msgs[0]))

    async def test_add_torrent_by_hash(self):
        self.daemon.response = rsrc.response_success(
            {'torrent-added': { 'id': 1,
                                'name': rsrc.TORRENTHASH,
                                'hashString': rsrc.TORRENTHASH}}
        )
        response = await self.api.add(rsrc.TORRENTHASH)
        self.assertEqual(response.success, True)
        self.assertEqual(response.torrent, Torrent({'id': 1, 'name': rsrc.TORRENTHASH}))


class TestGettingTorrents(TorrentAPITestCase):
    async def test_get_all_torrents(self):
        self.daemon.response = rsrc.response_torrents(
            {'id': 1, 'name': 'Torrent1'},
            {'id': 2, 'name': 'Torrent2'},
        )
        torrents = (await self.api.torrents()).torrents
        self.assert_torrentkeys_equal('id', torrents, 1, 2)
        self.assert_torrentkeys_equal('name', torrents, 'Torrent1', 'Torrent2')

    async def test_get_torrents_by_ids(self):
        self.daemon.response = rsrc.response_torrents(
            {'id': 1, 'name': 'Torrent1'},
            {'id': 2, 'name': 'Torrent2'},
            {'id': 3, 'name': 'Torrent3'},
        )
        response = await self.api.torrents(torrents=(1, 3))
        self.assertEqual(response.success, True)
        self.assert_torrentkeys_equal('id', response.torrents, 1, 3)
        self.assert_torrentkeys_equal('name', response.torrents, 'Torrent1', 'Torrent3')

        response = await self.api.torrents(torrents=(2,))
        self.assertEqual(response.success, True)
        self.assert_torrentkeys_equal('id', response.torrents, 2)
        self.assert_torrentkeys_equal('name', response.torrents, 'Torrent2')

        response = await self.api.torrents(torrents=())
        self.assertEqual(response.success, True)
        self.assertEqual(response.torrents, ())

        response = await self.api.torrents(torrents=(42, 23))
        self.assertEqual(response.success, False)
        self.assertEqual(response.torrents, ())
        self.assertIn('42', str(response.msgs[0]))
        self.assertIn('23', str(response.msgs[1]))

    async def test_get_torrents_by_filter(self):
        self.daemon.response = rsrc.response_torrents(
            {'id': 1, 'name': 'Foo'},
            {'id': 2, 'name': 'Bar'},
            {'id': 3, 'name': 'Boo'},
        )
        response = await self.api.torrents(torrents=TorrentFilter('name=Foo'))
        self.assertEqual(response.success, True)
        self.assert_torrentkeys_equal('id', response.torrents, 1)
        self.assert_torrentkeys_equal('name', response.torrents, 'Foo')

        response = await self.api.torrents(torrents=TorrentFilter('name~oo'))
        self.assertEqual(response.success, True)
        self.assert_torrentkeys_equal('id', response.torrents, 1, 3)
        self.assert_torrentkeys_equal('name', response.torrents, 'Foo', 'Boo')

        response = await self.api.torrents(torrents=TorrentFilter('name=Nope'))
        self.assertEqual(response.success, False)
        self.assertEqual(response.torrents, ())
        self.assertIn('Nope', str(response.msgs[0]))


class TestManipulatingTorrents(TorrentAPITestCase):
    async def setUp(self):
        await super().setUp()
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
        # None of the RPC methods for torrents have return values

    async def test_no_torrents_found(self):
        response = await self.api._torrent_action(
            torrents=TorrentFilter('id=4'),
            method=self.mock_method,
        )
        self.assertEqual(self.mock_method_args, None)
        self.assertEqual(self.mock_method_kwargs, None)
        self.assertEqual(response.success, False)
        self.assertEqual(response.torrents, ())
        self.assertIn('id', str(response.msgs[0]))
        self.assertIn('4', str(response.msgs[0]))

    async def test_rpc_method_without_kwargs(self):
        response = await self.api._torrent_action(
            torrents=TorrentFilter('id=4|id=3'),
            method=self.mock_method,
        )
        self.assertEqual(self.mock_method_args, (3,))
        self.assertEqual(self.mock_method_kwargs, {})
        self.assertEqual(response.success, True)
        self.assert_torrentkeys_equal('id', response.torrents, 3)
        self.assert_torrentkeys_equal('name', response.torrents, 'Boo')

    async def test_rpc_method_with_kwargs(self):
        response = await self.api._torrent_action(
            torrents=TorrentFilter('name~B'),
            method=self.mock_method, method_args={'foo': 'bar'},
        )
        self.assertEqual(self.mock_method_args, (2,3))
        self.assertEqual(self.mock_method_kwargs, {'foo': 'bar'})
        self.assertEqual(response.success, True)
        self.assert_torrentkeys_equal('id', response.torrents, 2, 3)
        self.assert_torrentkeys_equal('name', response.torrents, 'Bar', 'Boo')

    async def test_rpc_method_without_filter(self):
        response = await self.api._torrent_action(
            method=self.mock_method,
        )
        self.assertEqual(self.mock_method_args, (1, 2, 3))  # All torrents
        self.assertEqual(self.mock_method_kwargs, {})
        self.assertEqual(response.success, True)
        self.assert_torrentkeys_equal('id', response.torrents, 1, 2, 3)
        self.assert_torrentkeys_equal('name', response.torrents, 'Foo', 'Bar', 'Boo')

    async def test_check_function(self):
        wanted_keys = ('id', 'name')
        def check_func(torrent):
            self.assertEqual(set(torrent), set(wanted_keys))

            if 'oo' in torrent['name']:
                return (True, 'hit: #{}, {}'.format(torrent['id'], torrent['name']))
            else:
                return (False, 'miss: #{}, {}'.format(torrent['id'], torrent['name']))

        response = await self.api._torrent_action(
            method=self.mock_method,
            check=check_func, keys_check=wanted_keys,
        )
        self.assertEqual(self.mock_method_args, (1, 3))
        self.assertEqual(self.mock_method_kwargs, {})
        self.assertEqual(response.success, True)
        self.assert_torrentkeys_equal('id', response.torrents, 1, 3)
        self.assert_torrentkeys_equal('name', response.torrents, 'Foo', 'Boo')
        self.assertEqual(response.msgs, (
            'hit: #1, Foo',
            errors.ClientError('miss: #2, Bar'),
            'hit: #3, Boo',
        ))


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


    async def test_enable_rate_limit(self):
        self.daemon.response = rsrc.response_torrents(
            {'id': 1, 'name': 'Foo', 'uploadLimit': 100, 'uploadLimited': False},
            {'id': 2, 'name': 'Bar', 'uploadLimit': 200, 'uploadLimited': False},
        )
        response = await self.api.set_rate_limit_up(TorrentFilter('id=1|id=2'), True)
        self.assert_request({'method': 'torrent-set',
                            'arguments': {'ids': [1, 2], 'uploadLimited': True}})

    async def test_disable_rate_limit(self):
        self.daemon.response = rsrc.response_torrents(
            {'id': 1, 'name': 'Foo', 'uploadLimit': 100, 'uploadLimited': True},
            {'id': 2, 'name': 'Bar', 'uploadLimit': 200, 'uploadLimited': True},
        )
        response = await self.api.set_rate_limit_up(TorrentFilter('id=1|id=2'), False)
        self.assert_request({'method': 'torrent-set',
                            'arguments': {'ids': [1, 2], 'uploadLimited': False}})

    async def test_set_absolute_rate_limit(self):
        self.daemon.response = rsrc.response_torrents(
            {'id': 1, 'name': 'Foo', 'uploadLimit': 100, 'uploadLimited': False},
            {'id': 2, 'name': 'Bar', 'uploadLimit': 200, 'uploadLimited': True},
        )
        response = await self.api.set_rate_limit_up(TorrentFilter('id=1|id=2'), 1e6)
        self.assert_request({'method': 'torrent-set',
                            'arguments': {'ids': [1, 2], 'uploadLimited': True,
                                          'uploadLimit': 1000}})

    async def test_set_relative_rate_limit_when_enabled(self):
        self.daemon.response = rsrc.response_torrents(
            {'id': 1, 'name': 'Foo', 'uploadLimit': 100, 'uploadLimited': True},
            {'id': 2, 'name': 'Bar', 'uploadLimit': 200, 'uploadLimited': True},
        )
        response = await self.api.adjust_rate_limit_up(TorrentFilter('id=1|id=2'), -50e3)
        self.assert_request({'method': 'torrent-set',
                            'arguments': {'ids': [1], 'uploadLimited': True,
                                          'uploadLimit': 50}})
        self.assert_request({'method': 'torrent-set',
                            'arguments': {'ids': [2], 'uploadLimited': True,
                                          'uploadLimit': 150}})
