from stig.client.usertypes import (BandwidthValue, RateLimitValue)

from stig.client import convert
from stig.client import constants as const

import unittest


class BandwidthValueTest(unittest.TestCase):
    def setUp(self):
        self._orig_bandwidth_unit = convert.bandwidth.unit
        self._orig_bandwidth_prefix = convert.bandwidth.prefix

    def tearDown(self):
        convert.bandwidth.unit = self._orig_bandwidth_unit
        convert.bandwidth.prefix = self._orig_bandwidth_prefix

    def test_valuesyntax(self):
        self.assertEqual(BandwidthValue.valuesyntax,
                         '[+=|-=]<NUMBER>[Ti|T|Gi|G|Mi|M|Ki|k][b|B]')

    def test_unit_and_prefix_are_preserved(self):
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

    def test_adjusting_current_value(self):
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


class TestRateLimitValue(unittest.TestCase):
    def setUp(self):
        self.val = RateLimitValue('test')
        self._orig_bandwidth_unit = convert.bandwidth.unit
        self._orig_bandwidth_prefix = convert.bandwidth.prefix

    def tearDown(self):
        convert.bandwidth.unit = self._orig_bandwidth_unit
        convert.bandwidth.prefix = self._orig_bandwidth_prefix

    def test_typename(self):
        self.assertEqual(self.val.typename, 'boolean or rational number')

    def test_valuesyntax(self):
        self.assertEqual(self.val.valuesyntax,
                         ('[enabled/disabled|yes/no|on/off|true/false|1/0] or '
                          '[+=|-=]<NUMBER>[Ti|T|Gi|G|Mi|M|Ki|k][b|B]'))

    def test_valid_values_bytes_metric(self):
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

    def test_valid_values_bytes_binary(self):
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

    def test_valid_values_bits_metric(self):
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

    def test_valid_values_bits_binary(self):
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

    def test_invalid_values(self):
        for v,num_err in (('*500k', 'Not a rational number'),
                          ('10km', "Unit must be 'b' (bit) or 'B' (byte), not 'm'"),
                          ('=3', 'Not a rational number'),
                          ('zilch', 'Not a rational number'),
                          ([1, 2, 3], 'Not a number')):
            with self.assertRaises(ValueError) as cm:
                self.val.set(v)
            self.assertIn('Not a boolean', str(cm.exception))
            self.assertIn(num_err, str(cm.exception))
