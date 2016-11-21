from stig.client.aiotransmission.api_settings import (SettingsAPI, convert, const)
import resources_aiotransmission as rsrc

import asynctest
from types import SimpleNamespace
from copy import deepcopy


import logging
log = logging.getLogger(__name__)


class FakeTransmissionRPC():
    connected = True

    def __init__(self, *args, **kwargs):
        self.fake_settings = deepcopy(rsrc.SESSION_GET_RESPONSE['arguments'])

    async def session_get(self, autoconnect=True):
        return self.fake_settings

    async def session_set(self, settings):
        self.fake_settings.update(settings)


class TestSettingsAPI(asynctest.TestCase):
    async def setUp(self):
        self.rpc = FakeTransmissionRPC()
        srvapi = SimpleNamespace(rpc=self.rpc,
                                 loop=self.loop)
        self.api = SettingsAPI(srvapi)

    async def test___getitem__(self):
        for attr in ('rate-limit-down', 'rate-limit-up',
                     'alt-rate-limit-down', 'alt-rate-limit-up', 'dht', 'lpd'):
            self.assertIn(attr, tuple(self.api))

        attr_num = len(tuple(self.api))
        get_method_num = len(tuple(attr for attr in dir(self.api)
                                   if attr.startswith('get_')))
        self.assertEqual(attr_num, get_method_num)


    async def test_get_rate_limit(self):
        self.rpc.fake_settings['speed-limit-up'] = 100
        self.rpc.fake_settings['speed-limit-down'] = 10
        self.rpc.fake_settings['speed-limit-up-enabled'] = False
        self.rpc.fake_settings['speed-limit-down-enabled'] = False
        self.assertEqual((await self.api.get_rate_limit_up()), const.UNLIMITED)
        self.assertEqual((await self.api.get_rate_limit_down()), const.UNLIMITED)

        self.rpc.fake_settings['speed-limit-up-enabled'] = True
        self.rpc.fake_settings['speed-limit-down-enabled'] = True
        convert.bandwidth.unit = 'byte'
        self.assertEqual((await self.api.get_rate_limit_up()), 100e3)
        self.assertEqual((await self.api.get_rate_limit_down()), 10e3)

        convert.bandwidth.unit = 'bit'
        self.assertEqual((await self.api.get_rate_limit_up()), 800e3)
        self.assertEqual((await self.api.get_rate_limit_down()), 80e3)

    async def test_set_rate_limit(self):
        convert.bandwidth.unit = 'byte'
        self.rpc.fake_settings['speed-limit-up'] = 0
        self.rpc.fake_settings['speed-limit-up-enabled'] = False
        self.rpc.fake_settings['speed-limit-down'] = 0
        self.rpc.fake_settings['speed-limit-down-enabled'] = False

        await self.api.set_rate_limit_up(50e6)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up'], 50e3)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up-enabled'], True)
        await self.api.set_rate_limit_down(100e6)
        self.assertEqual(self.rpc.fake_settings['speed-limit-down'], 100e3)
        self.assertEqual(self.rpc.fake_settings['speed-limit-down-enabled'], True)

        await self.api.set_rate_limit_up(const.ENABLED)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up-enabled'], True)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up'], 50e3)
        await self.api.set_rate_limit_down(const.ENABLED)
        self.assertEqual(self.rpc.fake_settings['speed-limit-down-enabled'], True)
        self.assertEqual(self.rpc.fake_settings['speed-limit-down'], 100e3)

        await self.api.set_rate_limit_up(const.DISABLED)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up-enabled'], False)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up'], 50e3)
        await self.api.set_rate_limit_down(const.DISABLED)
        self.assertEqual(self.rpc.fake_settings['speed-limit-down-enabled'], False)
        self.assertEqual(self.rpc.fake_settings['speed-limit-down'], 100e3)

        await self.api.set_rate_limit_up(True)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up-enabled'], True)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up'], 50e3)
        await self.api.set_rate_limit_down(True)
        self.assertEqual(self.rpc.fake_settings['speed-limit-down-enabled'], True)
        self.assertEqual(self.rpc.fake_settings['speed-limit-down'], 100e3)

        await self.api.set_rate_limit_up(const.UNLIMITED)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up-enabled'], False)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up'], 50e3)
        await self.api.set_rate_limit_down(const.UNLIMITED)
        self.assertEqual(self.rpc.fake_settings['speed-limit-down-enabled'], False)
        self.assertEqual(self.rpc.fake_settings['speed-limit-down'], 100e3)

        await self.api.set_rate_limit_up(False)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up-enabled'], False)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up'], 50e3)
        await self.api.set_rate_limit_down(False)
        self.assertEqual(self.rpc.fake_settings['speed-limit-down-enabled'], False)
        self.assertEqual(self.rpc.fake_settings['speed-limit-down'], 100e3)

    async def test_get_alt_rate_limits(self):
        convert.bandwidth.unit = 'byte'
        self.rpc.fake_settings['alt-speed-up'] = 200
        self.rpc.fake_settings['alt-speed-down'] = 20
        self.rpc.fake_settings['alt-speed-enabled'] = False
        self.assertEqual((await self.api.get_alt_rate_limit_up()), const.UNLIMITED)
        self.assertEqual((await self.api.get_alt_rate_limit_down()), const.UNLIMITED)

        self.rpc.fake_settings['alt-speed-enabled'] = True
        self.assertEqual((await self.api.get_alt_rate_limit_up()), 200e3)
        self.assertEqual((await self.api.get_alt_rate_limit_down()), 20e3)

    async def test_set_alt_rate_limits(self):
        self.rpc.fake_settings['alt-speed-up'] = 0
        self.rpc.fake_settings['alt-speed-down'] = 0
        self.rpc.fake_settings['alt-speed-enabled'] = False
        convert.bandwidth.unit = 'byte'

        await self.api.set_alt_rate_limit_up(50e6)
        self.assertEqual(self.rpc.fake_settings['alt-speed-up'], 50e3)
        self.assertEqual(self.rpc.fake_settings['alt-speed-down'], 0)
        self.assertEqual(self.rpc.fake_settings['alt-speed-enabled'], True)

        await self.api.set_alt_rate_limit_down(500e6)
        self.assertEqual(self.rpc.fake_settings['alt-speed-up'], 50e3)
        self.assertEqual(self.rpc.fake_settings['alt-speed-down'], 500e3)
        self.assertEqual(self.rpc.fake_settings['alt-speed-enabled'], True)

        await self.api.set_alt_rate_limit_down(const.DISABLED)
        self.assertEqual(self.rpc.fake_settings['alt-speed-up'], 50e3)
        self.assertEqual(self.rpc.fake_settings['alt-speed-down'], 500e3)
        self.assertEqual(self.rpc.fake_settings['alt-speed-enabled'], False)

        await self.api.set_alt_rate_limit_up(const.ENABLED)
        self.assertEqual(self.rpc.fake_settings['alt-speed-up'], 50e3)
        self.assertEqual(self.rpc.fake_settings['alt-speed-down'], 500e3)
        self.assertEqual(self.rpc.fake_settings['alt-speed-enabled'], True)


    async def test_get_path_complete(self):
        self.rpc.fake_settings['download-dir'] = '/foo/bar'
        self.assertEqual((await self.api.get_path_complete()), '/foo/bar')

    async def test_set_path_complete(self):
        self.rpc.fake_settings['download-dir'] = '/foo/bar'
        await self.api.set_path_complete('/foo/baz')
        self.assertEqual(self.rpc.fake_settings['download-dir'], '/foo/baz')

        await self.api.set_path_complete('things/stuff')
        self.assertEqual(self.rpc.fake_settings['download-dir'], '/foo/baz/things/stuff')


    async def test_get_path_incomplete(self):
        self.rpc.fake_settings['incomplete-dir-enabled'] = True
        self.rpc.fake_settings['incomplete-dir'] = '/fim/fam'
        self.assertEqual((await self.api.get_path_incomplete()), '/fim/fam')
        self.rpc.fake_settings['incomplete-dir-enabled'] = False
        self.assertEqual((await self.api.get_path_incomplete()), const.DISABLED)

    async def test_set_path_incomplete(self):
        self.rpc.fake_settings['incomplete-dir-enabled'] = True
        self.rpc.fake_settings['incomplete-dir'] = '/boo/baa'
        await self.api.set_path_incomplete('/baa/boo')
        self.rpc.fake_settings['incomplete-dir-enabled'] = True
        self.rpc.fake_settings['incomplete-dir'] = '/baa/boo'
        await self.api.set_path_incomplete(False)
        self.rpc.fake_settings['incomplete-dir-enabled'] = False
        self.rpc.fake_settings['incomplete-dir'] = '/baa/boo'
        await self.api.set_path_incomplete('/123')
        self.rpc.fake_settings['incomplete-dir-enabled'] = True
        self.rpc.fake_settings['incomplete-dir'] = '/123'
        await self.api.set_path_incomplete('relative/path')
        self.rpc.fake_settings['incomplete-dir-enabled'] = True
        self.rpc.fake_settings['incomplete-dir'] = '/123/relative/path'
        await self.api.set_path_incomplete('..')
        self.rpc.fake_settings['incomplete-dir-enabled'] = True
        self.rpc.fake_settings['incomplete-dir'] = '/123/relative'


    async def test_get_dht(self):
        self.rpc.fake_settings['dht-enabled'] = True
        self.assertEqual((await self.api.get_dht()), const.ENABLED)
        self.rpc.fake_settings['dht-enabled'] = False
        self.assertEqual((await self.api.get_dht()), const.DISABLED)

    async def test_set_dht(self):
        await self.api.set_dht(True)
        self.assertEqual(self.rpc.fake_settings['dht-enabled'], True)
        await self.api.set_dht(False)
        self.assertEqual(self.rpc.fake_settings['dht-enabled'], False)
        await self.api.set_dht(const.ENABLED)
        self.assertEqual(self.rpc.fake_settings['dht-enabled'], True)
        await self.api.set_dht(const.DISABLED)
        self.assertEqual(self.rpc.fake_settings['dht-enabled'], False)


    async def test_get_lpd(self):
        self.rpc.fake_settings['lpd-enabled'] = True
        self.assertEqual((await self.api.get_lpd()), const.ENABLED)
        self.rpc.fake_settings['lpd-enabled'] = False
        self.assertEqual((await self.api.get_lpd()), const.DISABLED)

    async def test_set_lpd(self):
        await self.api.set_lpd(True)
        self.assertEqual(self.rpc.fake_settings['lpd-enabled'], True)
        await self.api.set_lpd(False)
        self.assertEqual(self.rpc.fake_settings['lpd-enabled'], False)
        await self.api.set_lpd(const.ENABLED)
        self.assertEqual(self.rpc.fake_settings['lpd-enabled'], True)
        await self.api.set_lpd(const.DISABLED)
        self.assertEqual(self.rpc.fake_settings['lpd-enabled'], False)


    async def test_get_encryption(self):
        self.rpc.fake_settings['encryption'] = 'required'
        self.assertEqual((await self.api.get_encryption()), 'required')
        self.rpc.fake_settings['encryption'] = 'preferred'
        self.assertEqual((await self.api.get_encryption()), 'preferred')
        self.rpc.fake_settings['encryption'] = 'tolerated'
        self.assertEqual((await self.api.get_encryption()), 'tolerated')

    async def test_set_encryption(self):
        await self.api.set_encryption('required')
        self.assertEqual(self.rpc.fake_settings['encryption'], 'required')
        await self.api.set_encryption('preferred')
        self.assertEqual(self.rpc.fake_settings['encryption'], 'preferred')
        await self.api.set_encryption('tolerated')
        self.assertEqual(self.rpc.fake_settings['encryption'], 'tolerated')
        with self.assertRaises(ValueError):
            await self.api.set_encryption('foo')
