from stig.client.aiotransmission.rpc import (TransmissionURL,
                                              CSRF_ERROR_CODE, CSRF_HEADER,
                                              AUTH_ERROR_CODE)
from aiohttp import web
from aiohttp.test_utils import unused_port
import asyncio
import os.path

import logging
log = logging.getLogger(__name__)

TORRENTFILE = os.path.dirname(__file__) + '/test.torrent'
TORRENTFILE_NOEXIST = '/this/path/hopefully/does/not/exist'
TORRENTHASH = 'a41eec4208db5dc76f411dfe52605fd201149eff'  # Same as test.torrent
SESSION_ID = 'Ev0eQHlXX8073z6N0L1jr3FRlxjbRbTqK2RtgTnglWrMnWh0'
SESSION_GET_RESPONSE = {
    "arguments": {
        "alt-speed-down": 100,
        "alt-speed-enabled": False,
        "alt-speed-time-begin": 540,
        "alt-speed-time-day": 127,
        "alt-speed-time-enabled": False,
        "alt-speed-time-end": 1000,
        "alt-speed-up": 300,
        "blocklist-enabled": False,
        "blocklist-size": 0,
        "blocklist-url": "http://www.example.com/blocklist",
        "cache-size-mb": 10,
        "config-dir": "/config/path",
        "dht-enabled": True,
        "download-dir": "/srv/torrents/inbox/",
        "download-dir-free-space": 10000000000,
        "download-queue-enabled": False,
        "download-queue-size": 5,
        "encryption": "preferred",
        "idle-seeding-limit": 30,
        "idle-seeding-limit-enabled": False,
        "incomplete-dir": "/some/path",
        "incomplete-dir-enabled": False,
        "lpd-enabled": False,
        "peer-limit-global": 300,
        "peer-limit-per-torrent": 100,
        "peer-port": 123,
        "peer-port-random-on-start": False,
        "pex-enabled": True,
        "port-forwarding-enabled": False,
        "queue-stalled-enabled": True,
        "queue-stalled-minutes": 30,
        "rename-partial-files": True,
        "rpc-version": 15,
        "rpc-version-minimum": 1,
        "script-torrent-done-enabled": False,
        "script-torrent-done-filename": "",
        "seed-queue-enabled": False,
        "seed-queue-size": 20,
        "seedRatioLimit": 5,
        "seedRatioLimited": False,
        "speed-limit-down": 7000,
        "speed-limit-down-enabled": True,
        "speed-limit-up": 6500,
        "speed-limit-up-enabled": False,
        "start-added-torrents": True,
        "trash-original-torrent-files": False,
        "units": {
            "memory-bytes": 1024,
            "memory-units": [
                "KiB",
                "MiB",
                "GiB",
                "TiB"
            ],
            "size-bytes": 1000,
            "size-units": [
                "kB",
                "MB",
                "GB",
                "TB"
            ],
            "speed-bytes": 1000,
            "speed-units": [
                "kB/s",
                "MB/s",
                "GB/s",
                "TB/s"
            ]
        },
        "utp-enabled": True,
        "version": "2.84 (14307)"
    },
    "result": "success"
}


def response_success(args):
    return {'result': 'success', 'arguments': args}

def response_failure(msg):
    return {'result': msg}

def response_torrents(*torrents):
    tlist = []
    for torrent in torrents:
        t = {'id': 1, 'name': 'UNNAMED'}
        for k,v in torrent.items():
            t[k] = v
        tlist.append(t)
    return {'result': 'success',
            'arguments': {'torrents': tlist}}

def make_url():
    return TransmissionURL('localhost:' + str(unused_port()))


class FakeTransmissionDaemon:
    def __init__(self, loop):
        self.url = make_url()
        self.loop = loop
        self.app = web.Application(loop=loop)
        self.app.router.add_route(method='POST',
                                  path=self.url.path,
                                  handler=self.handle_POST)
        self.handler = None
        self.server = None
        self.response = None

    async def handle_POST(self, request):
        if CSRF_HEADER not in request.headers:
            resp = web.Response(headers={CSRF_HEADER: SESSION_ID},
                                status=CSRF_ERROR_CODE)
        elif request.headers[CSRF_HEADER] != SESSION_ID:
            raise RuntimeError('Attempt to connect with wrong session id: {}'
                               .format(request.headers[CSRF_HEADER]))
        elif isinstance(self.response, web.Response):
            resp = self.response
        else:
            resp = await self._make_response(request, self.response)
        return resp

    async def _make_response(self, request, response):
        if callable(response):
            if asyncio.iscoroutinefunction(response):
                return await response(request)
            else:
                return response(request)
        elif isinstance(response, dict):
            return web.json_response(response)

        rqdata = await request.json()
        if 'method' in rqdata and rqdata['method'] == 'session-get':
            return web.json_response(SESSION_GET_RESPONSE)
        elif response is None:
            raise RuntimeError('Set the response property before making a request!')
        else:
            return web.Response(text=response)

    async def start(self):
        self.handler = self.app.make_handler()
        self.server = await self.loop.create_server(
            self.handler, self.url.hostname, self.url.port)

    async def stop(self):
        self.server.close()
        await self.server.wait_closed()
        await self.app.shutdown()
        # TODO: aiohttp has changed behaviour again and this is the easiest
        # fix for now.  But this should be solved in the future.
        # (Haha! Fuck you, future me!)
        try:
            await self.handler.finish_connections()
        except AttributeError as e:
            pass
        await self.app.cleanup()


class FakeCallback():
    def __init__(self, name):
        self.name = name
        self.args = []
        self.kwargs = []
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        self.args.append(args)
        self.kwargs.append(kwargs)

    def __repr__(self):
        return '<{} {}>'.format(type(self).__name__, self.name)
