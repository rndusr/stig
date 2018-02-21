from stig.utils._converter import DataCountConverter
from stig.utils.stringables import Float

import unittest

class TestDataCountConverter(unittest.TestCase):
    def setUp(self):
        self.conv = DataCountConverter()
        self.orig_unit = self.conv.unit
        self.orig_prefix = self.conv.prefix

    def tearDown(self):
        self.conv.unit = self.orig_unit
        self.conv.prefix = self.orig_prefix

    def test_string_parse_unit(self):
        self.conv.unit = 'B'
        n = self.conv('10kB')
        self.assertEqual(str(n), '10kB')
        n = self.conv('80kb')
        self.assertEqual(str(n), '10kB')
        n = self.conv('10k')
        self.assertEqual(str(n), '10kB')

        self.conv.unit = 'b'
        n = self.conv('10kb')
        self.assertEqual(str(n), '10kb')
        n = self.conv('10kB')
        self.assertEqual(str(n), '80kb')
        n = self.conv('10k')
        self.assertEqual(str(n), '10kb')

    def test_string_default_unit(self):
        self.conv.unit = 'B'
        n = self.conv('10k')
        self.assertEqual(n, 10e3)
        self.assertEqual(str(n), '10kB')

        self.conv.unit = 'b'
        n = self.conv('10k')
        self.assertEqual(n, 10e3)
        self.assertEqual(str(n), '10kb')

    def test_string_pass_unit_as_argument(self):
        self.conv.unit = 'B'
        n = self.conv('100k', unit='b')
        self.assertEqual(str(n), '12.5kB')
        n = self.conv('100k', unit='B')
        self.assertEqual(str(n), '100kB')

        self.conv.unit = 'b'
        n = self.conv('100k', unit='b')
        self.assertEqual(str(n), '100kb')
        n = self.conv('100k', unit='B')
        self.assertEqual(str(n), '800kb')

    def test_unit_as_argument(self):
        self.conv.unit = 'B'
        n = self.conv(100e3, unit='b')
        self.assertEqual(str(n), '12.5kB')
        n = self.conv(100e3, unit='B')
        self.assertEqual(str(n), '100kB')

        self.conv.unit = 'b'
        n = self.conv(100e3, unit='b')
        self.assertEqual(str(n), '100kb')
        n = self.conv(100e3, unit='B')
        self.assertEqual(str(n), '800kb')

    def test_default_unit(self):
        self.conv.unit = 'B'
        self.assertEqual(self.conv(10e6).with_unit, '10MB')
        self.conv.unit = 'b'
        self.assertEqual(self.conv(10e6).with_unit, '10Mb')

    def test_unit_conversion(self):
        self.conv.unit = 'B'
        self.conv.prefix = 'metric'
        self.assertEqual(self.conv(Float('100kB')).with_unit, '100kB')
        self.assertEqual(self.conv(Float('100kb')).with_unit, '12.5kB')
        self.assertEqual(self.conv(Float('100KiB')).with_unit, '102kB')
        self.assertEqual(self.conv(Float('100Kib')).with_unit, '12.8kB')

        self.conv.unit = 'b'
        self.conv.prefix = 'metric'
        self.assertEqual(self.conv(Float('100kB')).with_unit, '800kb')
        self.assertEqual(self.conv(Float('100kb')).with_unit, '100kb')
        self.assertEqual(self.conv(Float('100KiB')).with_unit, '819kb')
        self.assertEqual(self.conv(Float('100Kib')).with_unit, '102kb')

        self.conv.unit = 'B'
        self.conv.prefix = 'binary'
        self.assertEqual(self.conv(Float('100kB')).with_unit, '97.7KiB')
        self.assertEqual(self.conv(Float('100kb')).with_unit, '12.2KiB')
        self.assertEqual(self.conv(Float('100KiB')).with_unit, '100KiB')
        self.assertEqual(self.conv(Float('100Kib')).with_unit, '12.5KiB')

        self.conv.unit = 'b'
        self.conv.prefix = 'binary'
        self.assertEqual(self.conv(Float('100kB')).with_unit, '781Kib')
        self.assertEqual(self.conv(Float('100kb')).with_unit, '97.7Kib')
        self.assertEqual(self.conv(Float('100KiB')).with_unit, '800Kib')
        self.assertEqual(self.conv(Float('100Kib')).with_unit, '100Kib')

    def test_invalid_unit(self):
        self.conv.unit = 'B'
        with self.assertRaises(ValueError) as cm:
            self.conv('10km')
        self.assertEqual('Cannot convert m to B', str(cm.exception))

    def test_prefix_property(self):
        self.conv.unit = 'B'
        self.conv.prefix = 'metric'
        self.assertEqual(self.conv(10*1000).with_unit, '10kB')
        self.conv.prefix = 'binary'
        self.assertEqual(self.conv(10*1024).with_unit, '10KiB')

        self.conv.unit = 'b'
        self.conv.prefix = 'metric'
        self.assertEqual(self.conv(10*1000).with_unit, '10kb')
        self.conv.prefix = 'binary'
        self.assertEqual(self.conv(10*1024).with_unit, '10Kib')

    def test_chained_calls(self):
        self.conv.unit = 'B'
        x = self.conv(10e3)
        for _ in range(5):
            x = self.conv(x)
            self.assertEqual(x.with_unit, '10kB')

        self.conv.unit = 'b'
        x = self.conv(10e3)
        for _ in range(5):
            x = self.conv(x)
            self.assertEqual(x.with_unit, '10kb')
