from stig.client.aiotransmission.api_settings import SettingsAPI

from stig.client import convert
from stig.client import constants as const
from stig.client import ClientError

import resources_aiotransmission as rsrc

import asynctest
from types import SimpleNamespace
from copy import deepcopy


class FakeTransmissionRPC():
    connected = True

    def __init__(self, *args, **kwargs):
        self.fake_settings = deepcopy(rsrc.SESSION_GET_RESPONSE['arguments'])

    async def session_get(self):
        return self.fake_settings

    async def session_set(self, settings):
        self.fake_settings.update(settings)


class TestSettingsAPI(asynctest.TestCase):
    async def setUp(self):
        self.rpc = FakeTransmissionRPC()
        srvapi = SimpleNamespace(rpc=self.rpc, loop=self.loop)
        self.api = SettingsAPI(srvapi)


    async def test_attrs_have_corresponding_methods(self):
        for attr in self.api:
            method = 'get_' + attr.replace('.', '_')
            self.assertTrue(hasattr(self.api, method))

    async def test_properties_with_setters(self):
        for name in ('dht', 'path.complete', 'autostart'):
            setting = self.api[name]
            for prop in ('name', 'description'):
                self.assertNotEqual(getattr(setting, prop), 'foo')
                setattr(self.api[name], prop, 'foo')
                self.assertEqual(getattr(setting, prop), 'foo')

    async def test_rpc_unreachable(self):
        class UnreachableRPC(FakeTransmissionRPC):
            async def session_get(self):
                raise ClientError('Something went wrong.')
            async def session_set(self, settings):
                raise ClientError('Nah.')
        self.rpc = UnreachableRPC()
        self.api = SettingsAPI(SimpleNamespace(rpc=self.rpc, loop=self.loop))
        self.rpc.fake_settings = {}
        self.rpc.fake_settings['foo'] = 'bar'

        self.assertIs(self.api.pex.value, const.DISCONNECTED)
        with self.assertRaises(ClientError):
            await self.api.get_pex()
        with self.assertRaises(ClientError):
            await self.api['pex'].get()

        with self.assertRaises(ClientError):
            await self.api.set_pex(True)
        with self.assertRaises(ValueError):
            await self.api['pex'].set(False)

    async def test_value_property(self):
        setting = self.api['dht']
        self.api.clearcache()
        self.assertIs(setting.value, const.DISCONNECTED)
        await self.api.update()
        self.assertIn(setting.value, (True, False))

    async def test_string_method(self):
        from logging import getLogger
        log = getLogger(__name__)
        setting = self.api['dht']
        log.debug('setting: %r, %r', setting, type(setting))
        log.debug('string method: %r', setting.string)
        self.api.clearcache()
        self.assertIs(setting.string(), str(const.DISCONNECTED))
        await self.api.update()
        self.assertIn(setting.string(), ('enabled', 'disabled'))


    async def test_get_limit_rate_up(self):
        convert.bandwidth.unit = 'byte'
        self.rpc.fake_settings['speed-limit-up'] = 100
        self.rpc.fake_settings['speed-limit-up-enabled'] = False
        self.assertEqual((await self.api.get_limit_rate_up()).value, const.UNLIMITED)

        self.rpc.fake_settings['speed-limit-up-enabled'] = True
        self.assertEqual(await self.api['limit.rate.up'].get(), 100e3)

        convert.bandwidth.unit = 'bit'
        self.assertEqual((await self.api.get_limit_rate_up()).value, 800e3)

    async def test_get_limit_rate_down(self):
        convert.bandwidth.unit = 'bit'
        self.rpc.fake_settings['speed-limit-down'] = 1e3
        self.rpc.fake_settings['speed-limit-down-enabled'] = True
        self.assertEqual(await self.api['limit.rate.down'].get(), 8e6)

        self.rpc.fake_settings['speed-limit-down-enabled'] = False
        self.assertEqual((await self.api.get_limit_rate_down()).value, const.UNLIMITED)

        self.rpc.fake_settings['speed-limit-down-enabled'] = True
        convert.bandwidth.unit = 'byte'
        self.assertEqual((await self.api.get_limit_rate_down()).value, 1e6)


    async def test_set_limit_rate_up(self):
        self.rpc.fake_settings['speed-limit-up'] = 12345
        self.rpc.fake_settings['speed-limit-up-enabled'] = False
        convert.bandwidth.unit = 'byte'

        await self.api.set_limit_rate_up('50k')
        self.assertEqual(self.rpc.fake_settings['speed-limit-up'], 50)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up-enabled'], True)

        await self.api.set_limit_rate_up(False)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up-enabled'], False)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up'], 50)

        await self.api.set_limit_rate_up(True)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up-enabled'], True)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up'], 50)

        await self.api['limit.rate.up'].set(const.UNLIMITED)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up-enabled'], False)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up'], 50)

        await self.api.set_limit_rate_up('+=1Mb')
        self.assertEqual(self.rpc.fake_settings['speed-limit-up-enabled'], True)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up'], 125)

        await self.api['limit.rate.up'].set(False)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up-enabled'], False)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up'], 125)

    async def test_set_limit_rate_down(self):
        self.rpc.fake_settings['speed-limit-down'] = 100
        self.rpc.fake_settings['speed-limit-down-enabled'] = True
        convert.bandwidth.unit = 'bit'

        await self.api['limit.rate.down'].set('+=80k')
        self.assertEqual(self.rpc.fake_settings['speed-limit-down'], 110)
        self.assertEqual(self.rpc.fake_settings['speed-limit-down-enabled'], True)

        await self.api.set_limit_rate_down(False)
        self.assertEqual(self.rpc.fake_settings['speed-limit-down-enabled'], False)
        self.assertEqual(self.rpc.fake_settings['speed-limit-down'], 110)

        await self.api['limit.rate.down'].set(True)
        self.assertEqual(self.rpc.fake_settings['speed-limit-down-enabled'], True)
        self.assertEqual(self.rpc.fake_settings['speed-limit-down'], 110)

        convert.bandwidth.unit = 'byte'
        await self.api.set_limit_rate_down('+=1M')
        self.assertEqual(self.rpc.fake_settings['speed-limit-down-enabled'], True)
        self.assertEqual(self.rpc.fake_settings['speed-limit-down'], 1110)

        await self.api['limit.rate.down'].set(const.UNLIMITED)
        self.assertEqual(self.rpc.fake_settings['speed-limit-down-enabled'], False)
        self.assertEqual(self.rpc.fake_settings['speed-limit-down'], 1110)


    async def test_get_limits_rate_alt(self):
        convert.bandwidth.unit = 'byte'
        self.rpc.fake_settings['alt-speed-up'] = 200
        self.rpc.fake_settings['alt-speed-down'] = 20
        self.rpc.fake_settings['alt-speed-enabled'] = False
        self.assertEqual((await self.api.get_limit_rate_up_alt()).value, const.UNLIMITED)
        self.assertEqual(await self.api['limit.rate.down.alt'].get(), const.UNLIMITED)

        self.rpc.fake_settings['alt-speed-enabled'] = True
        self.assertEqual(await self.api['limit.rate.up.alt'].get(), 200e3)
        self.assertEqual((await self.api.get_limit_rate_down_alt()).value, 20e3)

    async def test_set_limits_rate_alt(self):
        convert.bandwidth.unit = 'bit'
        self.rpc.fake_settings['alt-speed-up'] = 1000
        self.rpc.fake_settings['alt-speed-down'] = 1000
        self.rpc.fake_settings['alt-speed-enabled'] = True

        await self.api.set_limit_rate_up_alt('+=1000k')
        await self.api.set_limit_rate_up_alt('+=1000k')
        await self.api['limit.rate.down.alt'].set('-=1000k')
        self.assertEqual(self.rpc.fake_settings['alt-speed-up'], 1250)
        self.assertEqual(self.rpc.fake_settings['alt-speed-down'], 875)
        self.assertEqual(self.rpc.fake_settings['alt-speed-enabled'], True)

        await self.api.set_limit_rate_down_alt(const.UNLIMITED)
        self.assertEqual(self.rpc.fake_settings['alt-speed-up'], 1250)
        self.assertEqual(self.rpc.fake_settings['alt-speed-down'], 875)
        self.assertEqual(self.rpc.fake_settings['alt-speed-enabled'], False)

        await self.api['limit.rate.up.alt'].set(True)
        self.assertEqual(self.rpc.fake_settings['alt-speed-up'], 1250)
        self.assertEqual(self.rpc.fake_settings['alt-speed-down'], 875)
        self.assertEqual(self.rpc.fake_settings['alt-speed-enabled'], True)


    async def test_get_path_complete(self):
        self.rpc.fake_settings['download-dir'] = '/foo/bar'
        self.assertEqual((await self.api.get_path_complete()).value, '/foo/bar')
        self.assertEqual(await self.api['path_complete'].get(), '/foo/bar')

    async def test_set_path_complete(self):
        self.rpc.fake_settings['download-dir'] = '/foo/bar'
        await self.api.set_path_complete('/bar/baz')
        self.assertEqual(self.rpc.fake_settings['download-dir'], '/bar/baz')

        await self.api['path.complete'].set('blam')
        self.assertEqual(self.rpc.fake_settings['download-dir'], '/bar/baz/blam')

        await self.api['path.complete'].set('////bli/bloop///di/blop//')
        self.assertEqual(self.rpc.fake_settings['download-dir'], '/bli/bloop/di/blop')


    async def test_get_path_incomplete(self):
        self.rpc.fake_settings['incomplete-dir-enabled'] = True
        self.rpc.fake_settings['incomplete-dir'] = '/fim/fam'
        self.assertEqual(await self.api['path_incomplete'].get(), '/fim/fam')
        self.rpc.fake_settings['incomplete-dir-enabled'] = False
        self.assertIs((await self.api.get_path_incomplete()).value, False)

    async def test_set_path_incomplete(self):
        self.rpc.fake_settings['incomplete-dir-enabled'] = True
        self.rpc.fake_settings['incomplete-dir'] = '/boo/baa'
        await self.api.set_path_incomplete('/baa/boo')
        self.rpc.fake_settings['incomplete-dir-enabled'] = True
        self.rpc.fake_settings['incomplete-dir'] = '/baa/boo'

        await self.api.set_path_incomplete(False)
        self.rpc.fake_settings['incomplete-dir-enabled'] = False
        self.rpc.fake_settings['incomplete-dir'] = '/baa/boo'
        await self.api['path.incomplete'].set(True)
        self.rpc.fake_settings['incomplete-dir-enabled'] = True
        self.rpc.fake_settings['incomplete-dir'] = '/baa/boo'

        await self.api['path.incomplete'].set('/absolute/path')
        self.rpc.fake_settings['incomplete-dir-enabled'] = True
        self.rpc.fake_settings['incomplete-dir'] = '/absolute/path'

        await self.api.set_path_incomplete(False)
        await self.api['path.incomplete'].set('relative/path')
        self.rpc.fake_settings['incomplete-dir-enabled'] = True
        self.rpc.fake_settings['incomplete-dir'] = '/absolute/path/relative/path'
        await self.api.set_path_incomplete('..')
        self.rpc.fake_settings['incomplete-dir-enabled'] = True
        self.rpc.fake_settings['incomplete-dir'] = '/absolute/path/relative'


    async def test_get_part_files(self):
        self.rpc.fake_settings['rename-partial-files'] = False
        self.assertIs(await self.api['part.files'].get(), False)
        self.rpc.fake_settings['rename-partial-files'] = True
        self.assertIs((await self.api.get_part_files()).value, True)

    async def test_set_part_files_incomplete(self):
        self.rpc.fake_settings['rename-partial-files'] = False
        await self.api.set_part_files(True)
        self.assertEqual(self.rpc.fake_settings['rename-partial-files'], True)

        await self.api['part.files'].set(False)
        self.assertEqual(self.rpc.fake_settings['rename-partial-files'], False)

        with self.assertRaises(ValueError):
            await self.api.set_part_files('foo')


    async def test_get_port(self):
        self.rpc.fake_settings['peer-port-random-on-start'] = False
        self.rpc.fake_settings['peer-port'] = 123
        self.assertEqual((await self.api.get_port()).value, 123)
        self.rpc.fake_settings['peer-port-random-on-start'] = True
        self.assertIs(await self.api['port'].get(), const.RANDOM)

    async def test_set_port(self):
        self.rpc.fake_settings['peer-port-random-on-start'] = False
        self.rpc.fake_settings['peer-port'] = 123
        await self.api['port'].set(456)
        self.assertEqual(self.rpc.fake_settings['peer-port-random-on-start'], False)
        self.assertEqual(self.rpc.fake_settings['peer-port'], 456)

        await self.api.set_port(const.RANDOM)
        self.assertEqual(self.rpc.fake_settings['peer-port-random-on-start'], True)
        self.assertEqual(self.rpc.fake_settings['peer-port'], 456)

        await self.api['port'].set(234)
        self.assertEqual(self.rpc.fake_settings['peer-port-random-on-start'], False)
        self.assertEqual(self.rpc.fake_settings['peer-port'], 234)

        await self.api.set_port('random')
        self.assertEqual(self.rpc.fake_settings['peer-port-random-on-start'], True)
        self.assertEqual(self.rpc.fake_settings['peer-port'], 234)

        with self.assertRaises(ValueError):
            await self.api.set_port('Pick one!')


    async def test_get_port_forwarding(self):
        self.rpc.fake_settings['port-forwarding-enabled'] = False
        self.assertEqual((await self.api.get_port_forwarding()).value, False)
        self.rpc.fake_settings['port-forwarding-enabled'] = True
        self.assertEqual((await self.api.get_port_forwarding()).value, True)

    async def test_set_port_forwarding(self):
        self.rpc.fake_settings['port-forwarding-enabled'] = False
        await self.api.set_port_forwarding('on')
        self.assertEqual(self.rpc.fake_settings['port-forwarding-enabled'], True)
        await self.api['port.forwarding'].set('no')
        self.assertEqual(self.rpc.fake_settings['port-forwarding-enabled'], False)
        with self.assertRaises(ValueError):
            await self.api.set_port_forwarding('over my dead body')


    async def test_get_utp(self):
        self.rpc.fake_settings['utp-enabled'] = True
        self.assertEqual((await self.api.get_utp()).value, True)
        self.rpc.fake_settings['utp-enabled'] = False
        self.assertEqual(await self.api['utp'].get(), False)

    async def test_set_utp(self):
        await self.api.set_utp(True)
        self.assertEqual(self.rpc.fake_settings['utp-enabled'], True)
        await self.api.set_utp(False)
        self.assertEqual(self.rpc.fake_settings['utp-enabled'], False)
        with self.assertRaises(ValueError):
            await self.api.set_utp('a fishy value')


    async def test_get_dht(self):
        self.rpc.fake_settings['dht-enabled'] = True
        self.assertEqual(await self.api['dht'].get(), True)
        self.rpc.fake_settings['dht-enabled'] = False
        self.assertEqual((await self.api.get_dht()).value, False)

    async def test_set_dht(self):
        await self.api.set_dht(True)
        self.assertEqual(self.rpc.fake_settings['dht-enabled'], True)
        await self.api.set_dht(False)
        self.assertEqual(self.rpc.fake_settings['dht-enabled'], False)
        with self.assertRaises(ValueError):
            await self.api.set_dht('not a boolean')


    async def test_get_pex(self):
        self.rpc.fake_settings['pex-enabled'] = True
        self.assertEqual((await self.api.get_pex()).value, True)
        self.rpc.fake_settings['pex-enabled'] = False
        self.assertEqual(await self.api['pex'].get(), False)

    async def test_set_pex(self):
        await self.api.set_pex(True)
        self.assertEqual(self.rpc.fake_settings['pex-enabled'], True)
        await self.api['pex'].set(False)
        self.assertEqual(self.rpc.fake_settings['pex-enabled'], False)
        with self.assertRaises(ValueError):
            await self.api.set_pex('not a boolean')


    async def test_get_lpd(self):
        self.rpc.fake_settings['lpd-enabled'] = True
        self.assertEqual((await self.api.get_lpd()).value, True)
        self.rpc.fake_settings['lpd-enabled'] = False
        self.assertEqual(await self.api['lpd'].get(), False)

    async def test_set_lpd(self):
        await self.api.set_lpd(True)
        self.assertEqual(self.rpc.fake_settings['lpd-enabled'], True)
        await self.api.set_lpd(False)
        self.assertEqual(self.rpc.fake_settings['lpd-enabled'], False)
        with self.assertRaises(ValueError):
            await self.api.set_lpd('One ValueError, please.')


    async def test_get_peer_limit_global(self):
        self.assertIs(self.api['peer.limit.global'].value, const.DISCONNECTED)
        self.rpc.fake_settings['peer-limit-global'] = 17
        self.assertEqual((await self.api.get_peer_limit_global()).value, 17)
        self.rpc.fake_settings['peer-limit-global'] = 17000
        self.assertEqual((await self.api.get_peer_limit_global()).value, 17000)

    async def test_set_peer_limit_global(self):
        self.assertIs(self.api['peer.limit.global'].value, const.DISCONNECTED)
        self.assertNotEqual(self.rpc.fake_settings['peer-limit-global'], 583)
        await self.api['peer.limit.global'].set(583)
        self.assertEqual(self.rpc.fake_settings['peer-limit-global'], 583)
        await self.api.set_peer_limit_global(123)
        self.assertEqual(self.rpc.fake_settings['peer-limit-global'], 123)
        with self.assertRaises(ValueError):
            await self.api.set_peer_limit_global('all of them')


    async def test_get_peer_limit_torrent(self):
        self.assertIs(self.api['peer.limit.torrent'].value, const.DISCONNECTED)
        self.rpc.fake_settings['peer-limit-per-torrent'] = 17
        self.assertEqual((await self.api.get_peer_limit_torrent()).value, 17)
        self.rpc.fake_settings['peer-limit-per-torrent'] = 17000
        self.assertEqual((await self.api.get_peer_limit_torrent()).value, 17000)

    async def test_set_peer_limit_torrent(self):
        self.assertIs(self.api['peer.limit.torrent'].value, const.DISCONNECTED)
        self.rpc.fake_settings['peer-limit-per-torrent'] = 2
        await self.api.set_peer_limit_torrent(583)
        self.assertEqual(self.rpc.fake_settings['peer-limit-per-torrent'], 583)
        await self.api['peer.limit.torrent'].set(28)
        self.assertEqual(self.rpc.fake_settings['peer-limit-per-torrent'], 28)
        with self.assertRaises(ValueError):
            await self.api.set_peer_limit_torrent('all of them')


    async def test_get_encryption(self):
        self.rpc.fake_settings['encryption'] = 'tolerated'
        self.assertEqual((await self.api.get_encryption()).value, 'tolerated')
        self.rpc.fake_settings['encryption'] = 'preferred'
        self.assertEqual(await self.api['encryption'].get(), 'preferred')
        self.rpc.fake_settings['encryption'] = 'required'
        self.assertEqual((await self.api.get_encryption()).value, 'required')

    async def test_set_encryption(self):
        self.rpc.fake_settings['encryption'] = 'required'
        await self.api.set_encryption('preferred')
        self.assertEqual(self.rpc.fake_settings['encryption'], 'preferred')
        await self.api.set_encryption('tolerated')
        self.assertEqual(self.rpc.fake_settings['encryption'], 'tolerated')
        await self.api.set_encryption('required')
        self.assertEqual(self.rpc.fake_settings['encryption'], 'required')
        with self.assertRaises(ValueError):
            await self.api.set_encryption('AES256')


    async def test_get_autostart(self):
        self.rpc.fake_settings['start-added-torrents'] = True
        self.assertEqual((await self.api.get_autostart()).value, True)
        self.rpc.fake_settings['start-added-torrents'] = False
        self.assertEqual(await self.api['autostart'].get(), False)

    async def test_set_autostart(self):
        await self.api.set_autostart(True)
        self.assertEqual(self.rpc.fake_settings['start-added-torrents'], True)
        await self.api.set_autostart(False)
        self.assertEqual(self.rpc.fake_settings['start-added-torrents'], False)
        with self.assertRaises(ValueError):
            await self.api.set_autostart('hello?')
