from stig.client.aiotransmission.api_torrent import TorrentAPI
from stig.client.aiotransmission.rpc import TransmissionRPC
from stig.client.aiotransmission.torrent import Torrent
from stig.client import errors
from stig.client.filters.torrent import TorrentFilter

import resources_aiotransmission as rsrc

import asynctest
import os.path
assert os.path.exists(rsrc.TORRENTFILE)
assert not os.path.exists(rsrc.TORRENTFILE_NOEXIST)


class TorrentAPITestCase(asynctest.TestCase):
    async def setUp(self):
        self.daemon = rsrc.FakeTransmissionDaemon()
        await self.daemon.start()
        self.rpc = TransmissionRPC(self.daemon.host, self.daemon.port)
        self.api = TorrentAPI(self.rpc)
        await self.rpc.connect()
        assert self.rpc.connected is True

    async def tearDown(self):
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
            {'torrent-added': { 'id': 1,
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

    async def test_add_torrent_by_hash(self):
        self.daemon.response = rsrc.response_success(
            {'torrent-added': { 'id': 1,
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
