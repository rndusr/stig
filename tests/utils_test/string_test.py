import unittest

from stig.utils.string import stralign, strcrop, strwidth


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
