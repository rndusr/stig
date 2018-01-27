from stig.utils import (DataCountConverter, NumberFloat, NumberInt)

import unittest

import logging
log = logging.getLogger(__name__)


class TestNumberFloat(unittest.TestCase):
    def test_prefix(self):
        for value,str_metric,str_binary in ((pow(1000, 1), '1k',    '1000'),
                                            (pow(1024, 1), '1.02k', '1Ki'),
                                            (pow(1000, 2), '1M',    '977Ki'),
                                            (pow(1024, 2), '1.05M', '1Mi'),
                                            (pow(1000, 3), '1G',    '954Mi'),
                                            (pow(1024, 3), '1.07G', '1Gi'),
                                            (pow(1000, 4), '1T',    '931Gi'),
                                            (pow(1024, 4), '1.10T', '1Ti')):
            for prefix in ('metric', 'binary'):
                n = NumberFloat(value, prefix=prefix)
                n_neg = NumberFloat(-value, prefix=prefix)
                self.assertEqual(n, value)
                self.assertEqual(n_neg, -value)
                self.assertEqual(n.prefix, prefix)
                n.prefix = 'metric'
                n_neg.prefix = 'metric'
                self.assertEqual(n.prefix, 'metric')
                self.assertEqual(n_neg.prefix, 'metric')
                self.assertEqual(n.without_unit, str_metric)
                self.assertEqual(n_neg.without_unit, '-'+str_metric)
                n.prefix = 'binary'
                n_neg.prefix = 'binary'
                self.assertEqual(n.prefix, 'binary')
                self.assertEqual(n_neg.prefix, 'binary')
                self.assertEqual(n.without_unit, str_binary)
                self.assertEqual(n_neg.without_unit, '-'+str_binary)

        with self.assertRaises(ValueError) as cm:
            n.prefix = 'foo'
        self.assertIn('binary', str(cm.exception))
        self.assertIn('metric', str(cm.exception))

    def test_unit(self):
        n = NumberFloat(1e6, unit='A', prefix='metric')
        self.assertEqual(n, 1e6)
        self.assertEqual(n.with_unit, '1MA')
        self.assertEqual(n.without_unit, '1M')
        n.unit = 'B'
        self.assertEqual(n.with_unit, '1MB')
        self.assertEqual(n.without_unit, '1M')
        n.unit = None
        self.assertEqual(n.with_unit, '1M')
        self.assertEqual(n.without_unit, '1M')

    def test_string_has_reasonable_number_of_decimal_points(self):
        self.assertEqual(NumberFloat(float('inf')).without_unit, '∞')
        self.assertEqual(NumberFloat(0).without_unit, '0')
        self.assertEqual(NumberFloat(0.009).without_unit, '0.01')
        self.assertEqual(NumberFloat(0.09).without_unit, '0.09')
        self.assertEqual(NumberFloat(9.09).without_unit, '9.09')
        self.assertEqual(NumberFloat(10.09).without_unit, '10.1')
        self.assertEqual(NumberFloat(99.09).without_unit, '99.1')
        self.assertEqual(NumberFloat(99.95).without_unit, '100')

    def test_parsing_without_unit(self):
        for string,num,prefix in ( ('23', 23, 'metric'),
                                   ('23.1', 23.1, 'metric'),
                                   ('23.2k',  23.2*pow(1000, 1), 'metric'),
                                   ('23.3Mi', 23.3*pow(1024, 2), 'binary'),
                                   ('23.4G',  23.4*pow(1000, 3), 'metric'),
                                   ('23.5Ti', 23.5*pow(1024, 4), 'binary') ):
            n = NumberFloat(string)
            self.assertEqual(n, num)
            self.assertEqual(str(n), string)
            self.assertEqual(n.prefix, prefix)

    def test_parsing_with_unit(self):
        for string,num,prefix in ( ('23X',     23,                'metric'),
                                   ('23.1X',   23.1,              'metric'),
                                   ('23.2kX',  23.2*pow(1000, 1), 'metric'),
                                   ('23.3MiX', 23.3*pow(1024, 2), 'binary'),
                                   ('23.4GX',  23.4*pow(1000, 3), 'metric'),
                                   ('23.5TiX', 23.5*pow(1024, 4), 'binary') ):
            n = NumberFloat(string)
            self.assertEqual(n, num)
            self.assertEqual(n.unit, 'X')
            self.assertEqual(n.prefix, prefix)
            self.assertEqual(n.with_unit, string)
            self.assertEqual(n.without_unit, string[:-1])

    def test_parsing_conflicting_units(self):
        n = NumberFloat('123kF', unit='B')
        self.assertEqual(n, 123000)
        self.assertEqual(n.unit, 'F')

    def test_parsing_signs(self):
        self.assertEqual(NumberFloat('-10'), -10)
        self.assertEqual(NumberFloat('+10'), 10)
        self.assertEqual(NumberFloat('-10k'), -10000)
        self.assertEqual(NumberFloat('+10M'), 10e6)
        n = NumberFloat('-10GX')
        self.assertEqual(n, -10e9)
        self.assertEqual(n.unit, 'X')
        n = NumberFloat('-10Ty')
        self.assertEqual(n, -10e12)
        self.assertEqual(n.unit, 'y')

    def test_passing_NumberFloat_instance_copies_properties(self):
        for orig_prefix in ('binary', 'metric'):
            for orig_unit in ('A', 'B'):
                for orig_str_includes_unit in (True, False):
                    orig = NumberFloat(1e3, prefix=orig_prefix, unit=orig_unit, str_includes_unit=orig_str_includes_unit)
                    copy = NumberFloat(orig)
                    self.assertEqual(copy, 1e3)
                    self.assertEqual(copy.unit, orig.unit)
                    self.assertEqual(copy.prefix, orig.prefix)
                    self.assertEqual(copy.str_includes_unit, orig.str_includes_unit)

                    # Override prefix
                    for new_prefix in ('metric', 'binary'):
                        copy = NumberFloat(orig, prefix=new_prefix)
                        self.assertEqual(copy, 1e3)
                        self.assertEqual(copy.unit, orig.unit)
                        self.assertEqual(copy.prefix, new_prefix)
                        self.assertEqual(copy.str_includes_unit, orig.str_includes_unit)

                    # Override unit
                    copy = NumberFloat(orig, unit='Z')
                    self.assertEqual(copy, 1e3)
                    self.assertEqual(copy.unit, 'Z')
                    self.assertEqual(copy.prefix, orig.prefix)
                    self.assertEqual(copy.str_includes_unit, orig.str_includes_unit)

                    # Override str_includes_unit
                    for new_str_includes_unit in (True, False):
                        copy = NumberFloat(orig, str_includes_unit=new_str_includes_unit)
                        self.assertEqual(copy, 1e3)
                        self.assertEqual(copy.unit, orig.unit)
                        self.assertEqual(copy.prefix, orig.prefix)
                        self.assertEqual(copy.str_includes_unit, new_str_includes_unit)

    def test_not_a_number(self):
        for value in ('foo', [1, 2, 3], print):
            with self.assertRaises(ValueError) as cm:
                NumberFloat(value)
            self.assertIn('Not a number', str(cm.exception))
            self.assertIn(str(value), str(cm.exception))

    def test_equality(self):
        self.assertEqual(NumberFloat(0), 0)
        self.assertEqual(NumberFloat(0), NumberFloat(0))
        self.assertEqual(NumberFloat(1024), 1024)
        self.assertEqual(NumberFloat(1024), NumberFloat(1024))
        self.assertNotEqual(NumberFloat(1000), 1000.0001)
        self.assertNotEqual(NumberFloat(1024), NumberFloat(1023))

    def test_arithmetic_operation_returns_correct_type(self):
        n = NumberFloat(5) / 2
        self.assertIsInstance(n, NumberFloat)
        n = NumberFloat(5) * 2
        self.assertIsInstance(n, NumberInt)
        n = NumberInt(5) + NumberFloat(4.3)
        self.assertIsInstance(n, NumberFloat)

    def test_arithmetic_operation_copies_unit(self):
        n = NumberFloat(5, unit='X') / 100
        self.assertEqual(n, 0.05)
        self.assertEqual(n.unit, 'X')

    def test_arithmetic_operation_copies_prefix(self):
        for prfx in ('metric', 'binary'):
            n = NumberFloat(5, prefix=prfx) * 100
            self.assertEqual(n, 500)
            self.assertEqual(n.prefix, prfx)

    def test_arithmetic_operation_copies_str_includes_unit(self):
        for str_includes_unit in (True, False):
            n = NumberFloat(5, str_includes_unit=str_includes_unit) * 100
            self.assertEqual(n, 500)
            self.assertEqual(n.str_includes_unit, str_includes_unit)

    def test_arithmetic_operation_copies_from_first_value(self):
        for prfx in ('metric', 'binary'):
            n = NumberFloat(  5, unit='X', prefix=prfx, str_includes_unit=False) \
              + NumberFloat(100, unit='z', prefix='metric', str_includes_unit=True)
            self.assertEqual(n, 105)
            self.assertEqual(n.unit, 'X')
            self.assertEqual(n.prefix, prfx)
            self.assertEqual(n.str_includes_unit, False)

    def test_str_includes_unit_argument(self):
        string = '1MA'
        n = NumberFloat(1e6, unit='A', prefix='metric', str_includes_unit=True)
        self.assertEqual(str(n), string)
        n.str_includes_unit = False
        self.assertEqual(str(n), string[:-1])

        n = NumberFloat(1e6, unit='A', prefix='metric', str_includes_unit=False)
        self.assertEqual(str(n), string[:-1])
        n.str_includes_unit = True
        self.assertEqual(str(n), string)

    def test_convert_to_argument(self):
        n = NumberFloat(1000, unit='B', convert_to='b')
        self.assertEqual(n.unit, 'b')
        self.assertEqual(n, 8000)
        n = NumberFloat('1000b')
        self.assertEqual(n.unit, 'b')
        self.assertEqual(n, 1000)

        n = NumberFloat(NumberFloat.from_string('1kb', convert_to='B'))
        self.assertEqual(n.unit, 'B')
        self.assertEqual(n, 125)
        n = NumberFloat(1000, unit='B')
        self.assertEqual(n.unit, 'B')
        self.assertEqual(n, 1000)


class Test_DataCountConverter(unittest.TestCase):
    def setUp(self):
        self.conv = DataCountConverter()

    def test_from_string_parse_unit(self):
        self.conv.unit = 'B'
        n = self.conv.from_string('10kB')
        self.assertEqual((n, n.unit), (10e3, 'B'))
        n = self.conv.from_string('80kb')
        self.assertEqual((n, n.unit), (10e3, 'B'))
        n = self.conv.from_string('10k')
        self.assertEqual((n, n.unit), (10e3, 'B'))

        self.conv.unit = 'b'
        n = self.conv.from_string('10kb')
        self.assertEqual((n, n.unit), (10e3, 'b'))
        n = self.conv.from_string('10kB')
        self.assertEqual((n, n.unit), (80e3, 'b'))
        n = self.conv.from_string('10k')
        self.assertEqual((n, n.unit), (10e3, 'b'))

    def test_from_string_default_unit(self):
        self.conv.unit = 'B'
        n = self.conv.from_string('10k')
        self.assertEqual(n, 10e3)
        self.assertEqual(n.unit, 'B')

        self.conv.unit = 'b'
        n = self.conv.from_string('10k')
        self.assertEqual(n, 10e3)
        self.assertEqual(n.unit, 'b')

    def test_from_string_pass_unit_as_argument(self):
        self.conv.unit = 'B'
        n = self.conv.from_string('100k', unit='b')
        self.assertEqual(str(n), '12.5kB')
        n = self.conv.from_string('100k', unit='B')
        self.assertEqual(str(n), '100kB')

        self.conv.unit = 'b'
        n = self.conv.from_string('100k', unit='b')
        self.assertEqual(str(n), '100kb')
        n = self.conv.from_string('100k', unit='B')
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
        self.assertEqual(self.conv(NumberFloat('100kB')).with_unit, '100kB')
        self.assertEqual(self.conv(NumberFloat('100kb')).with_unit, '12.5kB')
        self.assertEqual(self.conv(NumberFloat('100KiB')).with_unit, '102kB')
        self.assertEqual(self.conv(NumberFloat('100Kib')).with_unit, '12.8kB')

        self.conv.unit = 'b'
        self.conv.prefix = 'metric'
        self.assertEqual(self.conv(NumberFloat('100kB')).with_unit, '800kb')
        self.assertEqual(self.conv(NumberFloat('100kb')).with_unit, '100kb')
        self.assertEqual(self.conv(NumberFloat('100KiB')).with_unit, '819kb')
        self.assertEqual(self.conv(NumberFloat('100Kib')).with_unit, '102kb')

        self.conv.unit = 'B'
        self.conv.prefix = 'binary'
        self.assertEqual(self.conv(NumberFloat('100kB')).with_unit, '97.7KiB')
        self.assertEqual(self.conv(NumberFloat('100kb')).with_unit, '12.2KiB')
        self.assertEqual(self.conv(NumberFloat('100KiB')).with_unit, '100KiB')
        self.assertEqual(self.conv(NumberFloat('100Kib')).with_unit, '12.5KiB')

        self.conv.unit = 'b'
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
