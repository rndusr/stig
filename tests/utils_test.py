from stig.utils import (NumberFloat, NumberInt, strwidth, strcrop, stralign)

import unittest


class TestNumberFloat(unittest.TestCase):
    def test_prefix(self):
        for value,str_metric,str_binary in ((pow(1000, 1), '1k', '1000'),
                                            (pow(1024, 1), '1.02k', '1Ki'),
                                            (pow(1000, 2), '1M', '977Ki'),
                                            (pow(1024, 2), '1.05M', '1Mi'),
                                            (pow(1000, 3), '1G', '954Mi'),
                                            (pow(1024, 3), '1.07G', '1Gi'),
                                            (pow(1000, 4), '1T', '931Gi'),
                                            (pow(1024, 4), '1.10T', '1Ti')):
            for prefix in ('metric', 'binary'):
                n = NumberFloat(value, prefix=prefix)
                self.assertEqual(n, value)
                self.assertEqual(n.prefix, prefix)
                n.prefix = 'metric'
                self.assertEqual(n.prefix, 'metric')
                self.assertEqual(n.without_unit, str_metric)
                n.prefix = 'binary'
                self.assertEqual(n.prefix, 'binary')
                self.assertEqual(n.without_unit, str_binary)

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
        for string,num,prefix in ( ('23X', 23, 'metric'),
                                   ('23.1X', 23.1, 'metric'),
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

    def test_signs(self):
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


class Test_strwidth(unittest.TestCase):
    def test_empty_string(self):
        self.assertEqual(strwidth(''), 0)

    def test_ascii_string(self):
        self.assertEqual(strwidth('123'), 3)

    def test_double_wide_characters(self):
        self.assertEqual(strwidth('123／456'), 8)
        self.assertEqual(strwidth('ツ123／456'), 10)
        self.assertEqual(strwidth('ツ123／456ツ'), 12)
        self.assertEqual(strwidth('ツ／ツ'), 6)


class Test_strcrop(unittest.TestCase):
    def test_empty_string(self):
        self.assertEqual(strcrop('', 0), '')
        self.assertEqual(strcrop('', 100), '')

    def test_ascii_string(self):
        self.assertEqual(strcrop('123456', 100), '123456')
        self.assertEqual(strcrop('123456', 3), '123')
        self.assertEqual(strcrop('123456', 0), '')

    def test_one_double_wide_character(self):
        self.assertEqual(strcrop('123／456', 0), '')
        self.assertEqual(strcrop('123／456', 1), '1')
        self.assertEqual(strcrop('123／456', 2), '12')
        self.assertEqual(strcrop('123／456', 3), '123')
        self.assertEqual(strcrop('123／456', 4), '123')
        self.assertEqual(strcrop('123／456', 5), '123／')
        self.assertEqual(strcrop('123／456', 6), '123／4')
        self.assertEqual(strcrop('123／456', 7), '123／45')
        self.assertEqual(strcrop('123／456', 8), '123／456')
        self.assertEqual(strcrop('123／456', 9), '123／456')

    def test_multiple_double_wide_characters(self):
        self.assertEqual(strcrop('ツ123／456ツ', 100), 'ツ123／456ツ')
        self.assertEqual(strcrop('ツ123／456ツ', 1), '')
        self.assertEqual(strcrop('ツ123／456ツ', 2), 'ツ')
        self.assertEqual(strcrop('ツ123／456ツ', 3), 'ツ1')
        self.assertEqual(strcrop('ツ123／456ツ', 4), 'ツ12')
        self.assertEqual(strcrop('ツ123／456ツ', 5), 'ツ123')
        self.assertEqual(strcrop('ツ123／456ツ', 6), 'ツ123')
        self.assertEqual(strcrop('ツ123／456ツ', 7), 'ツ123／')
        self.assertEqual(strcrop('ツ123／456ツ', 8), 'ツ123／4')
        self.assertEqual(strcrop('ツ123／456ツ', 9), 'ツ123／45')
        self.assertEqual(strcrop('ツ123／456ツ', 10), 'ツ123／456')
        self.assertEqual(strcrop('ツ123／456ツ', 11), 'ツ123／456')
        self.assertEqual(strcrop('ツ123／456ツ', 12), 'ツ123／456ツ')
        self.assertEqual(strcrop('ツ123／456ツ', 13), 'ツ123／456ツ')


class Test_stralign(unittest.TestCase):
    def test_empty_string(self):
        self.assertEqual(stralign('', 0, 'left'), '')
        self.assertEqual(stralign('', 0, 'right'), '')
        self.assertEqual(stralign('', 10, 'left'), ' '*10)
        self.assertEqual(stralign('', 10, 'right'), ' '*10)

    def test_ascii_string(self):
        self.assertEqual(stralign('123', 1, 'left'), '1')
        self.assertEqual(stralign('123', 2, 'left'), '12')
        self.assertEqual(stralign('123', 3, 'left'), '123')
        self.assertEqual(stralign('123', 4, 'left'), '123 ')
        self.assertEqual(stralign('123', 5, 'left'), '123  ')
        self.assertEqual(stralign('123', 5, 'right'), '  123')
        self.assertEqual(stralign('123', 4, 'right'), ' 123')
        self.assertEqual(stralign('123', 3, 'right'), '123')

    def test_double_wide_characters(self):
        self.assertEqual(stralign('1／2／3', 0, 'left'), '')
        self.assertEqual(stralign('1／2／3', 1, 'left'), '1')
        self.assertEqual(stralign('1／2／3', 2, 'left'), '1 ')
        self.assertEqual(stralign('1／2／3', 3, 'left'), '1／')
        self.assertEqual(stralign('1／2／3', 4, 'left'), '1／2')
        self.assertEqual(stralign('1／2／3', 5, 'left'), '1／2 ')
        self.assertEqual(stralign('1／2／3', 6, 'left'), '1／2／')
        self.assertEqual(stralign('1／2／3', 7, 'left'), '1／2／3')
        self.assertEqual(stralign('1／2／3', 8, 'left'), '1／2／3 ')
        self.assertEqual(stralign('1／2／3', 9, 'left'), '1／2／3  ')
        self.assertEqual(stralign('1／2／3', 9, 'right'), '  1／2／3')
        self.assertEqual(stralign('1／2／3', 8, 'right'), ' 1／2／3')
        self.assertEqual(stralign('1／2／3', 7, 'right'), '1／2／3')
