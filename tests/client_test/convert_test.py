from stig.client.convert import _DataCountConverter

import unittest

import logging
log = logging.getLogger(__name__)


class Test_DataCountConverter(unittest.TestCase):
    def setUp(self):
        self.conv = _DataCountConverter()

    def test_parse_unit_with_from_string(self):
        self.conv.unit = 'byte'
        n = self.conv.from_string('10kB')
        self.assertEqual((n, n.unit), (10e3, 'B'))
        n = self.conv.from_string('10kb')
        self.assertEqual((n, n.unit), (1.25e3, 'B'))
        n = self.conv.from_string('10k')
        self.assertEqual((n, n.unit), (10e3, 'B'))

        self.conv.unit = 'bit'
        n = self.conv.from_string('10kb')
        self.assertEqual((n, n.unit), (10e3, 'b'))
        n = self.conv.from_string('10kB')
        self.assertEqual((n, n.unit), (80e3, 'b'))
        n = self.conv.from_string('10k')
        self.assertEqual((n, n.unit), (10e3, 'b'))

    def test_no_unit_with_from_string(self):
        self.conv.unit = 'byte'
        n = self.conv.from_string('10k')
        self.assertEqual(n, 10e3)
        self.assertEqual(n.unit, 'B')

        self.conv.unit = 'bit'
        n = self.conv.from_string('10k')
        self.assertEqual(n, 10e3)
        self.assertEqual(n.unit, 'b')

    def test_default_unit(self):
        self.conv.unit = 'byte'
        self.assertEqual(self.conv(10e6).with_unit, '10MB')
        self.conv.unit = 'bit'
        self.assertEqual(self.conv(10e6).with_unit, '80Mb')

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
        self.assertEqual(self.conv(10*1000).with_unit, '80kb')
        self.conv.prefix = 'binary'
        self.assertEqual(self.conv(10*1024).with_unit, '80Kib')

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
            self.assertEqual(x.with_unit, '80kb')
