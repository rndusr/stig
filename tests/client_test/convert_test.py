from stig.client.convert import _DataCountConverter

import unittest

import logging
log = logging.getLogger(__name__)


class Test_DataCountConverter(unittest.TestCase):
    def setUp(self):
        self.conv = _DataCountConverter()

    def test_parsing_with_unit(self):
        self.conv.unit = 'bit'
        self.assertEqual(self.conv('10kb'), 10e3)
        self.assertEqual(self.conv('10kB'), 80e3)
        self.conv.unit = 'byte'
        self.assertEqual(self.conv('10kB'), 10e3)
        self.assertEqual(self.conv('10kb'), 1.25e3)

    def test_parsing_without_unit(self):
        self.conv.unit = 'bit'
        self.assertEqual(self.conv('10k', unit='b'), 10e3)
        self.conv.unit = 'byte'
        self.assertEqual(self.conv('10k', unit='B'), 10e3)

    def test_prefix_property(self):
        self.conv.unit = 'byte'
        self.conv.prefix = 'metric'
        self.assertEqual(str(self.conv(10*1000, unit='B')), '10k')
        self.conv.prefix = 'binary'
        self.assertEqual(str(self.conv(10*1024, unit='B')), '10Ki')

    def test_missing_unit_argument(self):
        self.conv.unit = 'byte'
        self.assertEqual(self.conv(10*1e6).with_unit, '10MB')
        self.conv.unit = 'bit'
        self.assertEqual(self.conv(10*1e6).with_unit, '10Mb')

    def test_unknown_unit_argument(self):
        with self.assertRaises(ValueError) as cm:
            self.conv('10km')
        self.assertIn('unit', str(cm.exception).lower())
        self.assertIn("'m'", str(cm.exception))
