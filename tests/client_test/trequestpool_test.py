from tctrl.client.trequestpool import TorrentRequestPool
from tctrl.client.aiotransmission.torrent import Torrent
from tctrl.client.tfilter import TorrentFilter
from tctrl.client.utils import Response

import asynctest
import asyncio
from types import SimpleNamespace

import logging
log = logging.getLogger(__name__)



FAKE_TORRENTS = (
    Torrent({'id': 1, 'name': 'foo', 'status': 3, 'isStalled': False,
             'rateDownload': 50, 'rateUpload': 100, 'totalSize': 10e3}),
    Torrent({'id': 2, 'name': 'bar', 'status': 0, 'isStalled': True,
             'rateDownload': 0, 'rateUpload': 0, 'totalSize': 10e6}),
    Torrent({'id': 3, 'name': 'baz', 'status': 6, 'isStalled': True,
             'rateDownload': 0, 'rateUpload': 0, 'totalSize': 10e9})
)


class FakeTorrentAPI():
    def __init__(self):
        self.calls = 0
        self.arg_torrents = None
        self.arg_keys = None
        self.exc = None
        self.tlist = FAKE_TORRENTS
        self.delay = 0

    async def torrents(self, torrents=None, keys='ALL', autoconnect=True):
        if self.delay:
            await asyncio.sleep(self.delay, loop=asyncio.get_event_loop())
        self.calls += 1
        self.arg_torrents = torrents
        self.arg_keys = keys
        if self.exc is None:
            return Response(torrents=self.tlist)
        else:
            raise self.exc


class FakeCallback():
    def __init__(self):
        self.calls = 0
        self.args = None

    def __call__(self, torrents):
        self.calls += 1
        self.args = torrents


class Subscriber():
    def __init__(self, filters, *keys):
        self.keys = keys
        if isinstance(filters, str):
            self.filters = TorrentFilter(filters)
            self.keys_needed = tuple(set(self.keys + self.filters.needed_keys))
        else:
            self.filters = filters
            self.keys_needed = self.keys
        self.callback = FakeCallback()

    def __add__(self, other):
        if other.filters is not None:
            filters = str(self.filters + other.filters)
        else:
            filters = str(self.filters)
        s = Subscriber(filters, *(self.keys + other.keys))
        s.keys_needed = tuple(set(self.keys_needed + other.keys_needed))
        return s


class TestTorrentRequestPool(asynctest.ClockedTestCase):
    async def setUp(self):
        self.api = FakeTorrentAPI()
        srvapi = SimpleNamespace(torrent=self.api,
                                 loop=self.loop)
        self.rp = TorrentRequestPool(srvapi)
        self.assertEqual(self.rp.running, False)

    def assert_api_request(self, calls=None, filters=None, keys=None):
        if calls is not None:
            self.assertEqual(self.api.calls, calls)
        if filters is not None:
            self.assertEqual(self.api.arg_torrents, filters)
        if keys is not None:
            self.assertEqual(set(self.api.arg_keys), set(keys))

    async def test_combining_requests(self):
        await self.rp.start()
        self.assertEqual(self.rp.running, True)
        await self.advance(0)
        self.assert_api_request(calls=1,
                                filters=None,
                                keys='ALL')

        foo = Subscriber('name~foo', 'name', 'rate-down')
        self.rp.register('foo', foo.callback, keys=foo.keys, filters=foo.filters)
        await self.advance(self.rp.interval)
        self.assert_api_request(calls=2,
                                filters=foo.filters,
                                keys=foo.keys_needed)

        bar = Subscriber('name~bar', 'name', 'rate-up')
        self.rp.register('bar', bar.callback, keys=bar.keys, filters=bar.filters)
        await self.advance(self.rp.interval)
        self.assert_api_request(calls=3,
                                filters=(foo+bar).filters,
                                keys=(foo+bar).keys_needed)

        baz = Subscriber('idle', 'id', 'status', 'size-total')
        self.rp.register('baz', baz.callback, keys=baz.keys, filters=baz.filters)
        await self.advance(self.rp.interval)
        self.assert_api_request(calls=4,
                                filters=(foo+bar+baz).filters,
                                keys=(foo+bar+baz).keys_needed)

        # no filter
        for f in (None, TorrentFilter('all')):
            thelot = Subscriber(f, 'name', 'rate-up')
            self.rp.register('all', thelot.callback, keys=thelot.keys, filters=thelot.filters)
            await self.advance(self.rp.interval)
            self.assert_api_request(filters=None,
                                    keys=(foo+bar+baz+thelot).keys_needed)
            self.rp.remove('all')
            await self.advance(self.rp.interval)
            self.assert_api_request(filters=(foo+bar+baz).filters,
                                    keys=(foo+bar+baz).keys_needed)

        await self.rp.stop()

    async def test_autoremoving_requests(self):
        await self.rp.start()
        self.assertEqual(self.rp.running, True)
        await self.advance(0)

        foo = Subscriber('name~foo', 'name', 'rate-down')
        bar = Subscriber('name~bar', 'name', 'rate-up')
        baz = Subscriber('idle', 'id', 'status', 'size-total')
        self.rp.register('foo', foo.callback, keys=foo.keys, filters=foo.filters)
        self.rp.register('bar', bar.callback, keys=bar.keys, filters=bar.filters)
        self.rp.register('baz', baz.callback, keys=baz.keys, filters=baz.filters)
        await self.advance(self.rp.interval)
        self.assert_api_request(filters=(foo+bar+baz).filters,
                                keys=(foo+bar+baz).keys_needed)
        del foo
        # Wait one interval to detect `del foo`, and another interval for the
        # new request to happen.
        await self.advance(self.rp.interval*2)
        self.assert_api_request(filters=(bar+baz).filters,
                                keys=(bar+baz).keys_needed)
        del bar
        await self.advance(self.rp.interval*2)
        self.assert_api_request(filters=baz.filters,
                                keys=baz.keys_needed)
        del baz
        await self.advance(self.rp.interval*2)
        # No subscribers left
        self.assertEqual(self.rp._filters, {})
        self.assertEqual(self.rp._keys, {})

        await self.rp.stop()

    async def test_callbacks_get_correct_torrents(self):
        await self.rp.start()
        self.assertEqual(self.rp.running, True)

        foo = Subscriber('name~foo', 'name', 'rate-down')
        bar = Subscriber('name~bar', 'name', 'rate-up')
        baz = Subscriber('idle', 'id', 'status', 'size-total')
        self.rp.register('foo', foo.callback, keys=foo.keys, filters=foo.filters)
        self.rp.register('bar', bar.callback, keys=bar.keys, filters=bar.filters)
        self.rp.register('baz', baz.callback, keys=baz.keys, filters=baz.filters)
        await self.advance(0)

        self.assertEqual(foo.callback.calls, 1)
        self.assertEqual(bar.callback.calls, 1)
        self.assertEqual(baz.callback.calls, 1)

        self.assertEqual(tuple(foo.callback.args), (FAKE_TORRENTS[0],))
        self.assertEqual(tuple(bar.callback.args), (FAKE_TORRENTS[1],))
        self.assertEqual(tuple(baz.callback.args), (FAKE_TORRENTS[1], FAKE_TORRENTS[2]))

        await self.rp.stop()

    async def test_raising_fatal_exception(self):
        self.api.exc = ValueError('Something is wrong!')
        await self.rp.start()
        self.assertEqual(self.rp.running, True)
        await self.advance(0)
        with self.assertRaises(ValueError) as cm:
            await self.rp.stop()
        self.assertEqual(str(cm.exception), 'Something is wrong!')

    async def test_skip_ongoing_request(self):
        self.assertEqual(self.api.calls, 0)
        self.api.delay = 5
        await self.rp.start()

        # Add 3 callbacks at once
        cb1, cb2, cb3 = FakeCallback(), FakeCallback(), FakeCallback()
        self.rp.register('cb1', cb1)
        await self.advance(0)  # Poller starts a new request here
        self.rp.register('cb2', cb2)
        await self.advance(0)  # Poller should abort previous request and start a new one
        self.rp.register('cb3', cb3)
        await self.advance(0)  # Poller should abort previous request and start a new one

        # Autostart should've kicked in
        self.assertEqual(self.rp.running, True)

        # Wait for api call to return
        await self.advance(self.api.delay)
        self.assertEqual(cb1.calls, 1)
        self.assertEqual(cb1.args, FAKE_TORRENTS)
        self.assertEqual(cb2.calls, 1)
        self.assertEqual(cb2.args, FAKE_TORRENTS)
        self.assertEqual(cb3.calls, 1)
        self.assertEqual(cb3.args, FAKE_TORRENTS)

        await self.advance(self.rp.interval)
        await self.advance(self.api.delay)
        self.assertEqual(cb1.calls, 2)
        self.assertEqual(cb1.args, FAKE_TORRENTS)
        self.assertEqual(cb2.calls, 2)
        self.assertEqual(cb2.args, FAKE_TORRENTS)
        self.assertEqual(cb3.calls, 2)
        self.assertEqual(cb3.args, FAKE_TORRENTS)

        # Remove all callbacks at once
        del cb1 ; del cb2 ; del cb3
        apicalls = self.api.calls
        await self.advance(self.api.delay+20)

        # One extra apicall was made before the poller detected the dead callbacks
        self.assertEqual(self.api.calls, apicalls+1)

        await self.rp.stop()
