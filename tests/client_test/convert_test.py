from stig.client.convert import _DataCountConverter
from stig.utils import NumberFloat

import unittest

import logging
log = logging.getLogger(__name__)


class Test_DataCountConverter(unittest.TestCase):
    def setUp(self):
        self.conv = _DataCountConverter()

    def test_from_string_parse_unit(self):
        self.conv.unit = 'byte'
        n = self.conv.from_string('10kB')
        self.assertEqual((n, n.unit), (10e3, 'B'))
        n = self.conv.from_string('80kb')
        self.assertEqual((n, n.unit), (10e3, 'B'))
        n = self.conv.from_string('10k')
        self.assertEqual((n, n.unit), (10e3, 'B'))

        self.conv.unit = 'bit'
        n = self.conv.from_string('10kb')
        self.assertEqual((n, n.unit), (10e3, 'b'))
        n = self.conv.from_string('10kB')
        self.assertEqual((n, n.unit), (80e3, 'b'))
        n = self.conv.from_string('10k')
        self.assertEqual((n, n.unit), (10e3, 'b'))

    def test_from_string_default_unit(self):
        self.conv.unit = 'byte'
        n = self.conv.from_string('10k')
        self.assertEqual(n, 10e3)
        self.assertEqual(n.unit, 'B')

        self.conv.unit = 'bit'
        n = self.conv.from_string('10k')
        self.assertEqual(n, 10e3)
        self.assertEqual(n.unit, 'b')

    def test_from_string_pass_unit_as_argument(self):
        self.conv.unit = 'byte'
        n = self.conv.from_string('100k', unit='b')
        self.assertEqual(str(n), '12.5kB')
        n = self.conv.from_string('100k', unit='byte')
        self.assertEqual(str(n), '100kB')

        self.conv.unit = 'bit'
        n = self.conv.from_string('100k', unit='bit')
        self.assertEqual(str(n), '100kb')
        n = self.conv.from_string('100k', unit='B')
        self.assertEqual(str(n), '800kb')

    def test_unit_as_argument(self):
        self.conv.unit = 'byte'
        n = self.conv(100e3, unit='b')
        self.assertEqual(str(n), '12.5kB')
        n = self.conv(100e3, unit='byte')
        self.assertEqual(str(n), '100kB')

        self.conv.unit = 'bit'
        n = self.conv(100e3, unit='bit')
        self.assertEqual(str(n), '100kb')
        n = self.conv(100e3, unit='B')
        self.assertEqual(str(n), '800kb')

    def test_default_unit(self):
        self.conv.unit = 'byte'
        self.assertEqual(self.conv(10e6).with_unit, '10MB')
        self.conv.unit = 'bit'
        self.assertEqual(self.conv(10e6).with_unit, '10Mb')

    def test_unit_conversion(self):
        self.conv.unit = 'byte'
        self.conv.prefix = 'metric'
        self.assertEqual(self.conv(NumberFloat('100kB')).with_unit, '100kB')
        self.assertEqual(self.conv(NumberFloat('100kb')).with_unit, '12.5kB')
        self.assertEqual(self.conv(NumberFloat('100KiB')).with_unit, '102kB')
        self.assertEqual(self.conv(NumberFloat('100Kib')).with_unit, '12.8kB')

        self.conv.unit = 'bit'
        self.conv.prefix = 'metric'
        self.assertEqual(self.conv(NumberFloat('100kB')).with_unit, '800kb')
        self.assertEqual(self.conv(NumberFloat('100kb')).with_unit, '100kb')
        self.assertEqual(self.conv(NumberFloat('100KiB')).with_unit, '819kb')
        self.assertEqual(self.conv(NumberFloat('100Kib')).with_unit, '102kb')

        self.conv.unit = 'byte'
        self.conv.prefix = 'binary'
        self.assertEqual(self.conv(NumberFloat('100kB')).with_unit, '97.7KiB')
        self.assertEqual(self.conv(NumberFloat('100kb')).with_unit, '12.2KiB')
        self.assertEqual(self.conv(NumberFloat('100KiB')).with_unit, '100KiB')
        self.assertEqual(self.conv(NumberFloat('100Kib')).with_unit, '12.5KiB')

        self.conv.unit = 'bit'
        self.conv.prefix = 'binary'
        self.assertEqual(self.conv(NumberFloat('100kB')).with_unit, '781Kib')
        self.assertEqual(self.conv(NumberFloat('100kb')).with_unit, '97.7Kib')
        self.assertEqual(self.conv(NumberFloat('100KiB')).with_unit, '800Kib')
        self.assertEqual(self.conv(NumberFloat('100Kib')).with_unit, '100Kib')

    def test_invalid_unit(self):
        with self.assertRaises(ValueError) as cm:
            self.conv.from_string('10km')
        self.assertIn('Unit must be', str(cm.exception))
        self.assertIn("'m'", str(cm.exception))

    def test_prefix_property(self):
        self.conv.unit = 'byte'
        self.conv.prefix = 'metric'
        self.assertEqual(self.conv(10*1000).with_unit, '10kB')
        self.conv.prefix = 'binary'
        self.assertEqual(self.conv(10*1024).with_unit, '10KiB')

        self.conv.unit = 'bit'
        self.conv.prefix = 'metric'
        self.assertEqual(self.conv(10*1000).with_unit, '10kb')
        self.conv.prefix = 'binary'
        self.assertEqual(self.conv(10*1024).with_unit, '10Kib')

    def test_chained_calls(self):
        self.conv.unit = 'byte'
        x = self.conv(10e3)
        for _ in range(5):
            x = self.conv(x)
            self.assertEqual(x.with_unit, '10kB')

        self.conv.unit = 'bit'
        x = self.conv(10e3)
        for _ in range(5):
            x = self.conv(x)
            self.assertEqual(x.with_unit, '10kb')
