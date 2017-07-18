import asynctest
from stig.settings.types_srv import (const, converter, RateLimitValue,
                                     RateLimitSrvValue, BooleanSrvValue,
                                     PortSrvValue, IntegerSrvValue,
                                     PathIncompleteSrvValue)
from stig.types import (TRUE, FALSE)


class FakeServer():
    def __init__(self, initial_value):
        self.current = initial_value
        self.connected = False

    def getter(self):
        if self.connected:
            return self.current
        else:
            return const.DISCONNECTED

    async def setter(self, value):
        if self.connected:
            self.current = value
        else:
            raise ValueError("Can't change server setting")


class assert_attrs_mixin():
    def assert_attrs(self, v, **kwargs):
        for attr,val in kwargs.items():
            self.assertEqual(getattr(v, attr), val)


class TestBooleanSrvValue(asynctest.TestCase, assert_attrs_mixin):
    def setUp(self):
        self.initial_value = True
        self.srv = FakeServer(self.initial_value)
        self.val = BooleanSrvValue('test', getter=self.srv.getter, setter=self.srv.setter)

    async def test_typename(self):
        self.assertEqual(self.val.typename, 'boolean')

    async def test_valuesyntax(self):
        self.assertEqual(self.val.valuesyntax,
                         '[' + '|'.join('%s/%s' % (t,f) for t,f in zip(TRUE, FALSE)) + ']')

    async def test_disconnected(self):
        self.srv.connected = False
        self.assert_attrs(self.val, default=const.DISCONNECTED, value=const.DISCONNECTED)

    async def test_initial_value(self):
        self.srv.connected = True
        self.assertEqual(self.val.get(), self.initial_value)

    async def test_valid_values(self):
        self.srv.connected = True
        for v in ('enabled', 'yes', '1', 'on', 'true'):
            await self.val.set(v)
            self.assertEqual(self.val.get(), True)
            self.assertEqual(self.val.string(), 'enabled')
            self.assertEqual(self.srv.current, True)

        for v in ('disabled', 'no', '0', 'off', 'false'):
            await self.val.set(v)
            self.assertEqual(self.val.get(), False)
            self.assertEqual(self.val.string(), 'disabled')
            self.assertEqual(self.srv.current, False)

    async def test_invalid_values(self):
        self.srv.connected = True
        for v in ('hypertrue', (1, 2, 3)):
            with self.assertRaises(ValueError) as cm:
                await self.val.set(v)
            self.assertIn('Not a %s' % self.val.typename, str(cm.exception))

    async def test_change_setting_when_disconnected(self):
        self.srv.connected = False
        with self.assertRaises(ValueError) as cm:
            await self.val.set('true')
        self.assertIn("Can't change server setting", str(cm.exception))


class TestIntegerSrvValue(asynctest.TestCase, assert_attrs_mixin):
    def setUp(self):
        self.initial_value = 42
        self.srv = FakeServer(initial_value=self.initial_value)
        self.val = IntegerSrvValue('test', getter=self.srv.getter, setter=self.srv.setter)

    async def test_typename(self):
        self.assertEqual(self.val.typename, 'integer number')

    async def test_valuesyntax(self):
        self.assertEqual(self.val.valuesyntax, '[+=|-=]<NUMBER>[Ti|T|Gi|G|Mi|M|Ki|k]')

    async def test_disconnected(self):
        self.srv.connected = False
        self.assert_attrs(self.val, default=const.DISCONNECTED, value=const.DISCONNECTED)

    async def test_initial_value(self):
        self.srv.connected = True
        self.assertEqual(self.val.get(), self.initial_value)

    async def test_valid_values(self):
        self.srv.connected = True
        for v,exp in ((24, 24), ('-24', -24)):
            await self.val.set(v)
            self.assertEqual(self.val.get(), exp)
            self.assertEqual(self.srv.current, exp)

    async def test_invalid_values(self):
        self.srv.connected = True
        for v in ('true', (1, 2, 3)):
            with self.assertRaises(ValueError) as cm:
                await self.val.set(v)
            self.assertIn('Not a %s' % self.val.typename, str(cm.exception))


class TestPathIncompleteSrvValue(asynctest.TestCase, assert_attrs_mixin):
    def setUp(self):
        self.initial_value = '/foo/bar/baz'
        self.srv = FakeServer(self.initial_value)
        self.val = PathIncompleteSrvValue('test', getter=self.srv.getter, setter=self.srv.setter)

    async def test_typename(self):
        self.assertEqual(self.val.typename, 'boolean or path')

    async def test_valuesyntax(self):
        self.assertEqual(self.val.valuesyntax,
                         '[enabled/disabled|yes/no|on/off|true/false|1/0] or path')

    async def test_disconnected(self):
        self.srv.connected = False
        self.assert_attrs(self.val, default=const.DISCONNECTED, value=const.DISCONNECTED)

    async def test_initial_value(self):
        self.srv.connected = True
        self.assertEqual(self.val.get(), self.initial_value)

    async def test_valid_values(self):
        self.srv.connected = True
        for v,exp in (('this/path', 'this/path'), ('/that/other/path/../cool///path', '/that/other/cool/path'),
                      ('yes', True), ('enabled', True), ('on', True), ('1', True),
                      ('no', False), ('disabled', False), ('off', False), ('0', False)):
            await self.val.set(v)
            self.assertEqual(self.val.get(), exp)

    async def test_invalid_values(self):
        self.srv.connected = True
        val = PathIncompleteSrvValue('test', getter=self.srv.getter, setter=self.srv.setter,
                                     mustexist=True)
        invalid_path = 'this/path/does/not/exist/or/otherwise/this/test/fails'
        with self.assertRaises(ValueError) as cm:
            await val.set(invalid_path)
        self.assertEqual('Not a boolean; No such file or directory', str(cm.exception))


class TestPortSrvValue(asynctest.TestCase, assert_attrs_mixin):
    def setUp(self):
        self.initial_value = 12345
        self.srv = FakeServer(self.initial_value)
        self.val = PortSrvValue('test', getter=self.srv.getter, setter=self.srv.setter,
                                min=1, max=65535)

    async def test_typename(self):
        self.assertEqual(self.val.typename, 'integer number (1 - 65535) or random')

    async def test_valuesyntax(self):
        self.assertEqual(self.val.valuesyntax,
                         "[+=|-=]<NUMBER>[Ti|T|Gi|G|Mi|M|Ki|k] or 'random'")

    async def test_disconnected(self):
        self.srv.connected = False
        self.assert_attrs(self.val, default=const.DISCONNECTED, value=const.DISCONNECTED)

    async def test_initial_value(self):
        self.srv.connected = True
        self.assertEqual(self.val.get(), self.initial_value)

    async def test_valid_values(self):
        self.srv.connected = True
        for v,exp in ((1234, 1234), ('1234', 1234), ('random', const.RANDOM)):
            await self.val.set(v)
            self.assertEqual(self.val.get(), exp)

    async def test_invalid_values(self):
        self.srv.connected = True
        for v,errmsg in ((0, 'Too small'), ('65536', 'Too large'), ('randoom', "Not 'random'")):
            with self.assertRaises(ValueError) as cm:
                await self.val.set(v)
            self.assertIn(errmsg, str(cm.exception))


class TestRateLimitValue(asynctest.TestCase):
    def setUp(self):
        self.val = RateLimitValue('test')

    async def test_typename(self):
        self.assertEqual(self.val.typename, 'boolean or rational number (>= 0)')

    async def test_valuesyntax(self):
        self.assertEqual(self.val.valuesyntax,
                         ('[enabled/disabled|yes/no|on/off|true/false|1/0] or '
                          '[+=|-=]<NUMBER>[Ti|T|Gi|G|Mi|M|Ki|k][b|B]'))

    async def test_valid_values_bytes_metric(self):
        converter.bandwidth.prefix = 'metric'
        converter.bandwidth.unit = 'byte'
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
        ):
            self.val.set(v)
            self.assertEqual(self.val.get(), exp_get)
            self.assertEqual(self.val.string(), exp_str)
            self.assertEqual(self.val.string(default=True), '123MB')
            self.assertEqual(self.val.string(value=456000), '456kB')

    async def test_valid_values_bytes_binary(self):
        converter.bandwidth.prefix = 'binary'
        converter.bandwidth.unit = 'byte'
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
        ):
            self.val.set(v)
            self.assertEqual(self.val.get(), exp_get)
            self.assertEqual(self.val.string(), exp_str)
            self.assertEqual(self.val.string(default=True), '123MiB')
            self.assertEqual(self.val.string(value=456*1024), '456KiB')

    async def test_valid_values_bits_metric(self):
        converter.bandwidth.prefix = 'metric'
        converter.bandwidth.unit = 'bit'
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
        ):
            self.val.set(v)
            self.assertEqual(self.val.get(), exp_get)
            self.assertEqual(self.val.string(), exp_str)
            self.assertEqual(self.val.string(default=True), '123Mb')
            self.assertEqual(self.val.string(value='100kB'), '800kb')

    async def test_valid_values_bits_binary(self):
        converter.bandwidth.prefix = 'binary'
        converter.bandwidth.unit = 'bit'
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
                          (-1, 'Too small'),
                          ([1, 2, 3], 'Not a rational number')):
            with self.assertRaises(ValueError) as cm:
                self.val.set(v)
            self.assertIn('Not a boolean', str(cm.exception))
            self.assertIn(num_err, str(cm.exception))


class TestRateLimitSrvValue(asynctest.TestCase, assert_attrs_mixin):
    def setUp(self):
        self.initial_value = 1e6
        self.srv = FakeServer(self.initial_value)
        self.val = RateLimitSrvValue('test', getter=self.srv.getter, setter=self.srv.setter)

    async def test_disconnected(self):
        self.assert_attrs(self.val, default=const.DISCONNECTED, value=const.DISCONNECTED)

    async def test_initial_value(self):
        self.srv.connected = True
        self.assertEqual(self.val.get(), self.initial_value)

    async def test_limit_adjustment_from_initial_value(self):
        self.srv.connected = True
        await self.val.set('+=5M')
        self.assertEqual(self.val.get(), 6e6)

    async def test_limit_adjustment_from_boolean(self):
        self.srv.connected = True
        for num in ('1Ki', '2M', '3Gi'):
            await self.val.set('off')
            await self.val.set('+=' + num)
            self.assertEqual(self.val.string(), self.val.string(num))

    async def test_enable_previously_set_limit(self):
        self.srv.connected = True
        await self.val.set('1M')
        self.assertEqual(self.val.get(), 1e6)
        await self.val.set('disabled')
        self.assertEqual(self.val.get(), const.UNLIMITED)
        await self.val.set('enabled')
        self.assertEqual(self.val.get(), 1e6)
