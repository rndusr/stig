from stig.client.aiotransmission.api_settings import (SettingsAPI, convert, const)
from stig.client.aiotransmission.api_settings import (BandwidthValue, RateLimitValue)
from stig.client import (ClientError, DISCONNECTED)
import resources_aiotransmission as rsrc

import asynctest
from types import SimpleNamespace
from copy import deepcopy


class BandwidthValueTest(asynctest.TestCase):
    def setUp(self):
        self._orig_bandwidth_unit = convert.bandwidth.unit
        self._orig_bandwidth_prefix = convert.bandwidth.prefix

    def tearDown(self):
        convert.bandwidth.unit = self._orig_bandwidth_unit
        convert.bandwidth.prefix = self._orig_bandwidth_prefix

    async def test_valuesyntax(self):
        self.assertEqual(BandwidthValue.valuesyntax,
                         '[+=|-=]<NUMBER>[Ti|T|Gi|G|Mi|M|Ki|k][b|B]')

    async def test_unit_and_prefix_are_preserved(self):
        convert.bandwidth.unit = 'b'
        convert.bandwidth.prefix = 'binary'
        v = BandwidthValue('test', default='102400')
        self.assertEqual(v.value, 102400)
        self.assertEqual(str(v), '100Kib')
        v.set('1MB')
        self.assertEqual(v.value, 8e6)
        self.assertEqual(str(v), '7.63Mib')

        convert.bandwidth.unit = 'B'
        convert.bandwidth.prefix = 'metric'
        v = BandwidthValue('test', default='100k')
        self.assertEqual(v.value, 100000)
        self.assertEqual(str(v), '100kB')
        v.set('1Mib')
        self.assertEqual(v.value, (1024*1024)/8)
        self.assertEqual(str(v), '131kB')

    async def test_adjusting_current_value(self):
        convert.bandwidth.unit = 'b'
        convert.bandwidth.prefix = 'metric'
        v = BandwidthValue('test', default=1e6)
        self.assertEqual(v.value, 1000000)
        self.assertEqual(str(v.value), '1Mb')
        v.set('+=1MB')
        self.assertEqual(v.value, 9e6)
        self.assertEqual(str(v), '9Mb')

        convert.bandwidth.unit = 'B'
        convert.bandwidth.prefix = 'metric'
        v = BandwidthValue('test2', default='100k')
        self.assertEqual(v.value, 100e3)
        self.assertEqual(str(v), '100kB')
        v.set('-=80Kib')
        self.assertEqual(v.value, 100e3 - (80*1024/8))
        self.assertEqual(str(v), '89.8kB')


class TestRateLimitValue(asynctest.TestCase):
    def setUp(self):
        self.val = RateLimitValue('test')
        self._orig_bandwidth_unit = convert.bandwidth.unit
        self._orig_bandwidth_prefix = convert.bandwidth.prefix

    def tearDown(self):
        convert.bandwidth.unit = self._orig_bandwidth_unit
        convert.bandwidth.prefix = self._orig_bandwidth_prefix

    async def test_typename(self):
        self.assertEqual(self.val.typename, 'boolean or rational number')

    async def test_valuesyntax(self):
        self.assertEqual(self.val.valuesyntax,
                         ('[enabled/disabled|yes/no|on/off|true/false|1/0] or '
                          '[+=|-=]<NUMBER>[Ti|T|Gi|G|Mi|M|Ki|k][b|B]'))

    async def test_valid_values_bytes_metric(self):
        convert.bandwidth.prefix = 'metric'
        convert.bandwidth.unit = 'B'
        self.val.default = '123000000'
        for v,exp_get,exp_str in (
                ('off', const.UNLIMITED, 'unlimited'),
                (1e6, 1e6, '1MB'),
                (const.UNLIMITED, const.UNLIMITED, 'unlimited'),
                ('2340000', 2340000, '2.34MB'),
                ('enabled', 2340000, '2.34MB'),
                ('disabled', const.UNLIMITED, 'unlimited'),
                ('5670000000', 5.67e9, '5.67GB'),
                ('+=1G', 6.67e9, '6.67GB'),
                ('false', const.UNLIMITED, 'unlimited'),
                ('+=2Gi', 2*(2**30), '2.15GB'),
                ('-=100GB', const.UNLIMITED, 'unlimited'),
                ('0B', 0, '0B'),
        ):
            self.val.set(v)
            self.assertEqual(self.val.get(), exp_get)
            self.assertEqual(self.val.string(), exp_str)
            self.assertEqual(self.val.string(default=True), '123MB')
            self.assertEqual(self.val.string(value=456000), '456kB')

    async def test_valid_values_bytes_binary(self):
        convert.bandwidth.prefix = 'binary'
        convert.bandwidth.unit = 'B'
        self.val.set_default(123*1024*1024)
        for v,exp_get,exp_str in (
                ('off', const.UNLIMITED, 'unlimited'),
                (2**20, 2**20, '1MiB'),
                ('1024', 1024, '1KiB'),
                ('no', const.UNLIMITED, 'unlimited'),
                ('enabled', 1024, '1KiB'),
                ('disabled', const.UNLIMITED, 'unlimited'),
                ('1MB', 1e6, '977KiB'),
                ('+=8Mb', 2e6, '1.91MiB'),
                ('false', const.UNLIMITED, 'unlimited'),
                ('+=4Mb', 4e6/8, '488KiB'),
                ('-=100Gb', const.UNLIMITED, 'unlimited'),
                ('0b', 0, '0B'),
        ):
            self.val.set(v)
            self.assertEqual(self.val.get(), exp_get)
            self.assertEqual(self.val.string(), exp_str)
            self.assertEqual(self.val.string(default=True), '123MiB')
            self.assertEqual(self.val.string(value=456*1024), '456KiB')

    async def test_valid_values_bits_metric(self):
        convert.bandwidth.prefix = 'metric'
        convert.bandwidth.unit = 'b'
        self.val.set_default('123000kb')
        for v,exp_get,exp_str in (
                ('off', const.UNLIMITED, 'unlimited'),
                (1e6, 1e6, '1Mb'),
                ('1000', 1000, '1kb'),
                ('no', const.UNLIMITED, 'unlimited'),
                ('enabled', 1000, '1kb'),
                ('disabled', const.UNLIMITED, 'unlimited'),
                ('1MiB', 1048576*8, '8.39Mb'),
                ('-=500k', (1048576*8)-500e3, '7.89Mb'),
                ('false', const.UNLIMITED, 'unlimited'),
                ('+=500k', 500e3, '500kb'),
                ('-=100T', const.UNLIMITED, 'unlimited'),
                ('0KiB', 0, '0b'),
        ):
            self.val.set(v)
            self.assertEqual(self.val.get(), exp_get)
            self.assertEqual(self.val.string(), exp_str)
            self.assertEqual(self.val.string(default=True), '123Mb')
            self.assertEqual(self.val.string(value='100kB'), '800kb')

    async def test_valid_values_bits_binary(self):
        convert.bandwidth.prefix = 'binary'
        convert.bandwidth.unit = 'b'
        self.val.set_default(str(123*1024*1024/1000/1000/1000/8) + 'GB')
        for v,exp_get,exp_str in (
                ('off', const.UNLIMITED, 'unlimited'),
                (2**20, 2**20, '1Mib'),
                ('1024', 1024, '1Kib'),
                ('no', const.UNLIMITED, 'unlimited'),
                ('enabled', 1024, '1Kib'),
                ('disabled', const.UNLIMITED, 'unlimited'),
                ('1MiB', 1048576*8, '8Mib'),
                ('+=1000k', (1048576*8) + 1e6, '8.95Mib'),
                ('false', const.UNLIMITED, 'unlimited'),
                ('+=100kB', 800e3, '781Kib'),
                ('-=100TB', const.UNLIMITED, 'unlimited'),
                ('0kb', 0, '0b'),
        ):
            self.val.set(v)
            self.assertEqual(self.val.get(), exp_get)
            self.assertEqual(self.val.string(), exp_str)
            self.assertEqual(self.val.string(default=True), '123Mib')
            self.assertEqual(self.val.string(value='0.5MiB'), '4Mib')

    async def test_invalid_values(self):
        for v,num_err in (('*500k', 'Not a rational number'),
                          ('10km', "Unit must be 'b' (bit) or 'B' (byte), not 'm'"),
                          ('=3', 'Not a rational number'),
                          ('zilch', 'Not a rational number'),
                          ([1, 2, 3], 'Not a number')):
            with self.assertRaises(ValueError) as cm:
                self.val.set(v)
            self.assertIn('Not a boolean', str(cm.exception))
            self.assertIn(num_err, str(cm.exception))


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
            method = 'get_' + attr.replace('-', '_')
            self.assertTrue(hasattr(self.api, method))

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

        self.assertIs(self.api.pex.value, DISCONNECTED)
        with self.assertRaises(ClientError):
            await self.api.get_pex()
        with self.assertRaises(ClientError):
            await self.api['pex'].get()

        with self.assertRaises(ClientError):
            await self.api.set_pex(True)
        with self.assertRaises(ValueError):
            await self.api['pex'].set(False)


    async def test_get_rate_limit_up(self):
        convert.bandwidth.unit = 'byte'
        self.rpc.fake_settings['speed-limit-up'] = 100
        self.rpc.fake_settings['speed-limit-up-enabled'] = False
        self.assertEqual((await self.api.get_rate_limit_up()).value, const.UNLIMITED)

        self.rpc.fake_settings['speed-limit-up-enabled'] = True
        self.assertEqual(await self.api['rate_limit_up'].get(), 100e3)

        convert.bandwidth.unit = 'bit'
        self.assertEqual((await self.api.get_rate_limit_up()).value, 800e3)

    async def test_get_rate_limit_down(self):
        convert.bandwidth.unit = 'bit'
        self.rpc.fake_settings['speed-limit-down'] = 1e3
        self.rpc.fake_settings['speed-limit-down-enabled'] = True
        self.assertEqual(await self.api['rate-limit-down'].get(), 8e6)

        self.rpc.fake_settings['speed-limit-down-enabled'] = False
        self.assertEqual((await self.api.get_rate_limit_down()).value, const.UNLIMITED)

        self.rpc.fake_settings['speed-limit-down-enabled'] = True
        convert.bandwidth.unit = 'byte'
        self.assertEqual((await self.api.get_rate_limit_down()).value, 1e6)


    async def test_set_rate_limit_up(self):
        self.rpc.fake_settings['speed-limit-up'] = 12345
        self.rpc.fake_settings['speed-limit-up-enabled'] = False
        convert.bandwidth.unit = 'byte'

        await self.api.set_rate_limit_up('50k')
        self.assertEqual(self.rpc.fake_settings['speed-limit-up'], 50)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up-enabled'], True)

        await self.api.set_rate_limit_up(False)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up-enabled'], False)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up'], 50)

        await self.api.set_rate_limit_up(True)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up-enabled'], True)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up'], 50)

        await self.api['rate_limit_up'].set(const.UNLIMITED)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up-enabled'], False)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up'], 50)

        await self.api.set_rate_limit_up('+=1Mb')
        self.assertEqual(self.rpc.fake_settings['speed-limit-up-enabled'], True)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up'], 125)

        await self.api['rate_limit_up'].set(False)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up-enabled'], False)
        self.assertEqual(self.rpc.fake_settings['speed-limit-up'], 125)

    async def test_set_rate_limit_down(self):
        self.rpc.fake_settings['speed-limit-down'] = 100
        self.rpc.fake_settings['speed-limit-down-enabled'] = True
        convert.bandwidth.unit = 'bit'

        await self.api['rate_limit_down'].set('+=80k')
        self.assertEqual(self.rpc.fake_settings['speed-limit-down'], 110)
        self.assertEqual(self.rpc.fake_settings['speed-limit-down-enabled'], True)

        await self.api.set_rate_limit_down(False)
        self.assertEqual(self.rpc.fake_settings['speed-limit-down-enabled'], False)
        self.assertEqual(self.rpc.fake_settings['speed-limit-down'], 110)

        await self.api['rate_limit_down'].set(True)
        self.assertEqual(self.rpc.fake_settings['speed-limit-down-enabled'], True)
        self.assertEqual(self.rpc.fake_settings['speed-limit-down'], 110)

        convert.bandwidth.unit = 'byte'
        await self.api.set_rate_limit_down('+=1M')
        self.assertEqual(self.rpc.fake_settings['speed-limit-down-enabled'], True)
        self.assertEqual(self.rpc.fake_settings['speed-limit-down'], 1110)

        await self.api['rate_limit_down'].set(const.UNLIMITED)
        self.assertEqual(self.rpc.fake_settings['speed-limit-down-enabled'], False)
        self.assertEqual(self.rpc.fake_settings['speed-limit-down'], 1110)


    async def test_description_rate_limit_up(self):
        self.assertEqual(type(self.api).rate_limit_up.__doc__, self.api['rate-limit-up'].description)

    async def test_description_rate_limit_down(self):
        self.assertEqual(type(self.api).rate_limit_down.__doc__, self.api['rate-limit-down'].description)


    async def test_get_alt_rate_limits(self):
        convert.bandwidth.unit = 'byte'
        self.rpc.fake_settings['alt-speed-up'] = 200
        self.rpc.fake_settings['alt-speed-down'] = 20
        self.rpc.fake_settings['alt-speed-enabled'] = False
        self.assertEqual((await self.api.get_alt_rate_limit_up()).value, const.UNLIMITED)
        self.assertEqual(await self.api['alt-rate-limit-down'].get(), const.UNLIMITED)

        self.rpc.fake_settings['alt-speed-enabled'] = True
        self.assertEqual(await self.api['alt_rate_limit_up'].get(), 200e3)
        self.assertEqual((await self.api.get_alt_rate_limit_down()).value, 20e3)

    async def test_set_alt_rate_limits(self):
        convert.bandwidth.unit = 'bit'
        self.rpc.fake_settings['alt-speed-up'] = 1000
        self.rpc.fake_settings['alt-speed-down'] = 1000
        self.rpc.fake_settings['alt-speed-enabled'] = True

        await self.api.set_alt_rate_limit_up('+=1000k')
        await self.api.set_alt_rate_limit_up('+=1000k')
        await self.api['alt-rate-limit-down'].set('-=1000k')
        self.assertEqual(self.rpc.fake_settings['alt-speed-up'], 1250)
        self.assertEqual(self.rpc.fake_settings['alt-speed-down'], 875)
        self.assertEqual(self.rpc.fake_settings['alt-speed-enabled'], True)

        await self.api.set_alt_rate_limit_down(const.UNLIMITED)
        self.assertEqual(self.rpc.fake_settings['alt-speed-up'], 1250)
        self.assertEqual(self.rpc.fake_settings['alt-speed-down'], 875)
        self.assertEqual(self.rpc.fake_settings['alt-speed-enabled'], False)

        await self.api['alt-rate-limit-up'].set(True)
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

        await self.api['path-complete'].set('blam')
        self.assertEqual(self.rpc.fake_settings['download-dir'], '/bar/baz/blam')

        await self.api['path-complete'].set('////bli/bloop///di/blop//')
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
        await self.api['path-incomplete'].set(True)
        self.rpc.fake_settings['incomplete-dir-enabled'] = True
        self.rpc.fake_settings['incomplete-dir'] = '/baa/boo'

        await self.api['path-incomplete'].set('/absolute/path')
        self.rpc.fake_settings['incomplete-dir-enabled'] = True
        self.rpc.fake_settings['incomplete-dir'] = '/absolute/path'

        await self.api.set_path_incomplete(False)
        await self.api['path-incomplete'].set('relative/path')
        self.rpc.fake_settings['incomplete-dir-enabled'] = True
        self.rpc.fake_settings['incomplete-dir'] = '/absolute/path/relative/path'
        await self.api.set_path_incomplete('..')
        self.rpc.fake_settings['incomplete-dir-enabled'] = True
        self.rpc.fake_settings['incomplete-dir'] = '/absolute/path/relative'


    async def test_get_part_files(self):
        self.rpc.fake_settings['rename-partial-files'] = False
        self.assertIs(await self.api['part-files'].get(), False)
        self.rpc.fake_settings['rename-partial-files'] = True
        self.assertIs((await self.api.get_part_files()).value, True)

    async def test_set_part_files_incomplete(self):
        self.rpc.fake_settings['rename-partial-files'] = False
        await self.api.set_part_files(True)
        self.assertEqual(self.rpc.fake_settings['rename-partial-files'], True)

        await self.api['part-files'].set(False)
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
        await self.api['port-forwarding'].set('no')
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

    async def test_description_pex(self):
        self.assertEqual(type(self.api).pex.__doc__, self.api['pex'].description)


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
        self.assertIs(self.api['peer-limit-global'].value, DISCONNECTED)
        self.rpc.fake_settings['peer-limit-global'] = 17
        self.assertEqual((await self.api.get_peer_limit_global()).value, 17)
        self.rpc.fake_settings['peer-limit-global'] = 17000
        self.assertEqual((await self.api.get_peer_limit_global()).value, 17000)

    async def test_set_peer_limit_global(self):
        self.assertIs(self.api['peer-limit-global'].value, DISCONNECTED)
        self.assertNotEqual(self.rpc.fake_settings['peer-limit-global'], 583)
        await self.api['peer-limit-global'].set(583)
        self.assertEqual(self.rpc.fake_settings['peer-limit-global'], 583)
        await self.api.set_peer_limit_global(123)
        self.assertEqual(self.rpc.fake_settings['peer-limit-global'], 123)
        with self.assertRaises(ValueError):
            await self.api.set_peer_limit_global('all of them')


    async def test_get_peer_limit_torrent(self):
        self.assertIs(self.api['peer-limit-torrent'].value, DISCONNECTED)
        self.rpc.fake_settings['peer-limit-per-torrent'] = 17
        self.assertEqual((await self.api.get_peer_limit_torrent()).value, 17)
        self.rpc.fake_settings['peer-limit-per-torrent'] = 17000
        self.assertEqual((await self.api.get_peer_limit_torrent()).value, 17000)

    async def test_set_peer_limit_torrent(self):
        self.assertIs(self.api['peer-limit-torrent'].value, DISCONNECTED)
        self.rpc.fake_settings['peer-limit-per-torrent'] = 2
        await self.api.set_peer_limit_torrent(583)
        self.assertEqual(self.rpc.fake_settings['peer-limit-per-torrent'], 583)
        await self.api['peer-limit-torrent'].set(28)
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


    async def test_get_autostart_torrents(self):
        self.rpc.fake_settings['start-added-torrents'] = True
        self.assertEqual((await self.api.get_autostart_torrents()).value, True)
        self.rpc.fake_settings['start-added-torrents'] = False
        self.assertEqual(await self.api['autostart-torrents'].get(), False)

    async def test_set_autostart_torrents(self):
        await self.api.set_autostart_torrents(True)
        self.assertEqual(self.rpc.fake_settings['start-added-torrents'], True)
        await self.api.set_autostart_torrents(False)
        self.assertEqual(self.rpc.fake_settings['start-added-torrents'], False)
        with self.assertRaises(ValueError):
            await self.api.set_autostart_torrents('hello?')
