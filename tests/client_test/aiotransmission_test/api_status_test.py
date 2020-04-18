from stig.client.aiotransmission.api_status import StatusAPI
from stig.client.utils import (convert, const)
from stig.client.ttypes import Status

import resources_aiotransmission as rsrc

import asynctest
from types import SimpleNamespace

import logging
log = logging.getLogger(__name__)


class FakeTransmissionRPC():
    connected = True
    fake_stats = None
    async def session_stats(self):
        return self.fake_stats


class FakeRequestPoller():
    def __init__(self, request, interval, *args, **kwargs):
        self.request = request
        self.interval = interval

    def on_response(self, callback, autoremove=True):
        self.cb_response = callback

    def on_error(self, callback, autoremove=True):
        self.cb_error = callback

    async def fake_response(self):
        self.cb_response(await self.request())

    async def start(self):
        pass

    async def stop(self):
        pass

from stig.client.aiotransmission import api_status
api_status.RequestPoller = FakeRequestPoller

class FakeTorrentAPI():
    fake_tlist = ()
    async def torrents(self, *args, **kwargs):
        return self.fake_tlist


class TestStatusAPI(asynctest.TestCase):
    async def setUp(self):
        self.rpc = FakeTransmissionRPC()
        self.torrent = FakeTorrentAPI()
        srvapi = SimpleNamespace(rpc=self.rpc,
                                 torrent=self.torrent)
        self.api = StatusAPI(srvapi, interval=1)

        self.rpc.fake_stats = {
            'downloadSpeed': 789,
            'uploadSpeed': 0,
            'activeTorrentCount': 1,
            'pausedTorrentCount': 2,
            'torrentCount': 3,
        }

        self.torrent.fake_tlist = SimpleNamespace(
            torrents=({'status': Status((Status.ISOLATED,)), 'rate-up': 0, 'rate-down': 0},
                      {'status': Status((Status.DOWNLOAD,)), 'rate-up': 0, 'rate-down': 456},
                      {'status': Status((Status.DOWNLOAD, Status.UPLOAD)), 'rate-up': 123, 'rate-down': 456}),
        )

    async def test_attributes(self):
        convert.bandwidth.unit = 'byte'
        convert.bandwidth.prefix = 'metric'

        await self.api._poller_stats.fake_response()
        await self.api._poller_tcount.fake_response()

        self.assertEqual(self.api.rate_down, 789)
        self.assertEqual(self.api.rate_up, 0)
        self.assertEqual(self.api.count.active, 1)
        self.assertEqual(self.api.count.stopped, 2)
        self.assertEqual(self.api.count.total, 3)
        self.assertEqual(self.api.count.uploading, 1)
        self.assertEqual(self.api.count.downloading, 2)
        self.assertEqual(self.api.count.isolated, 1)

        self.rpc.fake_stats = None
        self.torrent.fake_tlist = None
        await self.api._poller_stats.fake_response()
        await self.api._poller_tcount.fake_response()

        self.assertEqual(self.api.rate_down, const.DISCONNECTED)
        self.assertEqual(self.api.rate_up, const.DISCONNECTED)
        self.assertEqual(self.api.count.active, const.DISCONNECTED)
        self.assertEqual(self.api.count.stopped, const.DISCONNECTED)
        self.assertEqual(self.api.count.total, const.DISCONNECTED)
        self.assertEqual(self.api.count.uploading, const.DISCONNECTED)
        self.assertEqual(self.api.count.downloading, const.DISCONNECTED)
        self.assertEqual(self.api.count.isolated, const.DISCONNECTED)

    async def test_on_update_callback(self):
        convert.bandwidth.unit = 'byte'
        convert.bandwidth.prefix = 'metric'

        cb = rsrc.FakeCallback('handle_info')
        self.api.on_update(cb)
        self.assertEqual(cb.calls, 0)

        await self.api._poller_stats.fake_response()
        await self.api._poller_tcount.fake_response()
        self.assertEqual(cb.calls, 1)
        status = cb.args[0][0]
        self.assertEqual(status.rate_down, 789)
        self.assertEqual(status.rate_up, 0)
        self.assertEqual(status.count.active, 1)
        self.assertEqual(status.count.stopped, 2)
        self.assertEqual(status.count.total, 3)
        self.assertEqual(status.count.uploading, 1)
        self.assertEqual(status.count.downloading, 2)
        self.assertEqual(status.count.isolated, 1)

        self.rpc.fake_stats = None
        self.torrent.fake_tlist = None
        await self.api._poller_stats.fake_response()
        await self.api._poller_tcount.fake_response()

        self.assertEqual(cb.calls, 2)
        status = cb.args[0][0]
        self.assertEqual(status.rate_down, const.DISCONNECTED)
        self.assertEqual(status.rate_up, const.DISCONNECTED)
        self.assertEqual(status.count.active, const.DISCONNECTED)
        self.assertEqual(status.count.stopped, const.DISCONNECTED)
        self.assertEqual(status.count.total, const.DISCONNECTED)
        self.assertEqual(status.count.uploading, const.DISCONNECTED)
        self.assertEqual(status.count.downloading, const.DISCONNECTED)
        self.assertEqual(status.count.isolated, const.DISCONNECTED)
