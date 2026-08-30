import asyncio
import logging
import os.path
from base64 import b64decode

from aiohttp import web
from aiohttp.test_utils import unused_port

from stig.client.aiotransmission.rpc import AUTH_ERROR_CODE, CSRF_ERROR_CODE, CSRF_HEADER

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


# Transmission >=4.1.0 uses snake_case for all RPC strings.  This is only a
# representative excerpt of what 'session_get' returns - enough to connect.
SESSION_GET_RESPONSE_JSONRPC = {
    "jsonrpc": "2.0",
    "result": {
        "alt_speed_down": 100,
        "alt_speed_enabled": False,
        "download_dir": "/srv/torrents/inbox/",
        "peer_limit_global": 300,
        "rpc_version": 18,
        "rpc_version_minimum": 1,
        "rpc_version_semver": "6.0.0",
        "seed_ratio_limit": 5,
        "seed_ratio_limited": False,
        "speed_limit_down": 7000,
        "speed_limit_down_enabled": True,
        "units": {
            "memory_bytes": 1024,
            "memory_units": ["KiB", "MiB", "GiB", "TiB"],
            "size_bytes": 1000,
            "size_units": ["kB", "MB", "GB", "TB"],
            "speed_bytes": 1000,
            "speed_units": ["kB/s", "MB/s", "GB/s", "TB/s"]
        },
        "version": "4.1.0 (1234567890)"
    },
    "id": 1
}


def response_success(args):
    return {'result': 'success', 'arguments': args}

def response_success_jsonrpc(result):
    return {'jsonrpc': '2.0', 'result': result}

def response_failure_jsonrpc(code, message, error_string=None):
    error = {'code': code, 'message': message}
    if error_string is not None:
        error['data'] = {'error_string': error_string}
    return {'jsonrpc': '2.0', 'error': error}

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

def response_torrents_jsonrpc(*torrents):
    return {'jsonrpc': '2.0',
            'result': response_torrents(*torrents)['arguments']}


class FakeTransmissionDaemon:
    def __init__(self, jsonrpc=False):
        # Whether this daemon understands JSON-RPC 2.0 (Transmission >=4.1.0)
        self.jsonrpc = jsonrpc
        self.host = 'localhost'
        self.port = unused_port()
        self.app = web.Application()
        self.app.router.add_route(method='POST',
                                  path='/{path:.*}',
                                  handler=self.handle_POST)
        self.handler = None
        self.server = None
        self.response = None
        self.requests = []
        self.auth = None

    async def handle_POST(self, request):
        def valid_auth():
            def extract_credentials(basic_auth_str):
                try:
                    creds_b64 = basic_auth_str.split(' ')[1]
                    creds_str = b64decode(creds_b64).decode()
                    user, password = creds_str.split(':')
                    return user, password
                except Exception:
                    raise ValueError("Wrong 'Authorization' header format: %s" % (basic_auth_str,))

            if not self.auth:
                return True
            elif 'Authorization' not in request.headers:
                return False
            else:
                auth_header = request.headers['Authorization']
                user, password = extract_credentials(auth_header)
                return user == self.auth['user'] and password == self.auth['password']

        self.requests.append(await request.json())

        if CSRF_HEADER not in request.headers:
            resp = web.Response(headers={CSRF_HEADER: SESSION_ID},
                                status=CSRF_ERROR_CODE)
        elif request.headers[CSRF_HEADER] != SESSION_ID:
            raise RuntimeError('Attempt to connect with wrong session id: {}'
                               .format(request.headers[CSRF_HEADER]))
        elif isinstance(self.response, web.Response):
            resp = self.response
        elif not valid_auth():
            resp = web.Response(status=AUTH_ERROR_CODE)
        else:
            resp = await self._make_response(request, self.response)
        return resp

    async def _make_response(self, request, response):
        rqdata = await request.json()
        is_jsonrpc = 'jsonrpc' in rqdata

        if is_jsonrpc and not self.jsonrpc:
            # Daemons older than 4.1.0 don't know the snake_case method names
            return web.json_response({'result': 'method name not recognized'})

        if callable(response):
            if asyncio.iscoroutinefunction(response):
                return await response(request)
            else:
                return response(request)
        elif isinstance(response, dict):
            if is_jsonrpc and 'id' not in response:
                response = dict(response, id=rqdata.get('id'))
            return web.json_response(response)

        if rqdata.get('method') in ('session-get', 'session_get'):
            return web.json_response(SESSION_GET_RESPONSE_JSONRPC if is_jsonrpc
                                     else SESSION_GET_RESPONSE)
        elif response is None:
            raise RuntimeError('Set the response property before making a request!')
        else:
            return web.Response(text=response)

    async def start(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, self.host, self.port)
        await site.start()

    async def stop(self):
        await self.runner.cleanup()


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
