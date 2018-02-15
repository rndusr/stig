from stig.settings import Settings
from stig.utils.stringables import StringableMixin

import unittest
from unittest.mock import MagicMock, call


class TestSettings(unittest.TestCase):
    def setUp(self):
        self.s = Settings()
        def one(value): return str(value).upper()
        def two(value): return str(value).lower()
        def three(value): return '(%s)' % value
        self.s.add('one', MagicMock(side_effect=one), 'fOO')
        self.s.add('two', MagicMock(side_effect=two), 'Bar')
        self.s.add('three', MagicMock(side_effect=three), 'baz')

    def test_adding_settings(self):
        constructor = MagicMock(return_value='biz')
        self.s.add('four', constructor, 'biz')
        constructor.assert_called_once_with('biz')
        self.assertEqual(self.s['four'], 'biz')

    def test_renaming_settings(self):
        self.s.rename('two', 'twooo')
        self.assertNotIn('two', self.s)
        self.assertIn('twooo', self.s)
        self.assertEqual(self.s['twooo'], 'bar')

    def test_values_property(self):
        self.assertEqual(tuple(self.s.values), ('FOO', 'bar', '(baz)'))

    def test_names_property(self):
        self.assertEqual(tuple(self.s.names), ('one', 'two', 'three'))

    def test_getting_values(self):
        self.assertEqual(self.s['one'], 'FOO')
        self.assertEqual(self.s['two'], 'bar')
        self.assertEqual(self.s['three'], '(baz)')
        with self.assertRaises(KeyError):
            self.s['four']

    def test_setting_values(self):
        self.s['one'] = 'some'
        self.assertEqual(self.s['one'], 'SOME')
        self.assertEqual(self.s['two'], 'bar')
        self.assertEqual(self.s['three'], '(baz)')

        self.s['two'] = 'tHiNg'
        self.assertEqual(self.s['one'], 'SOME')
        self.assertEqual(self.s['two'], 'thing')
        self.assertEqual(self.s['three'], '(baz)')

        self.s['three'] = 'or maybe not'
        self.assertEqual(self.s['one'], 'SOME')
        self.assertEqual(self.s['two'], 'thing')
        self.assertEqual(self.s['three'], '(or maybe not)')

        with self.assertRaises(KeyError):
            self.s['four'] = 'gloop'

    def test_resetting_values(self):
        self.assertEqual(self.s['one'], 'FOO')
        self.s['one'] = 'x'
        self.assertEqual(self.s['one'], 'X')
        self.s.reset('one')
        self.assertEqual(self.s['one'], 'FOO')

    def test_on_change_global(self):
        # spec={} to work around issue with blinker
        # https://stackoverflow.com/questions/19569164/#41180322
        cb = MagicMock(spec={})
        self.s.on_change(cb)
        self.s['three'] = 'kazam'
        cb.assert_has_calls((call(self.s, name='three', value='(kazam)'),))
        self.s['two'] = 'kaZING'
        cb.assert_has_calls((call(self.s, name='three', value='(kazam)'),
                             call(self.s, name='two', value='kazing')))
        self.s['one'] = 'zup'
        cb.assert_has_calls((call(self.s, name='three', value='(kazam)'),
                             call(self.s, name='two', value='kazing'),
                             call(self.s, name='one', value='ZUP')))

    def test_on_change_per_setting(self):
        # spec={} to work around issue with blinker
        # https://stackoverflow.com/questions/19569164/#41180322
        cb = MagicMock(spec={})
        self.s.on_change(cb, name='three')
        self.s['three'] = 'kazam'
        cb.assert_has_calls((call(self.s, name='three', value='(kazam)'),))
        self.s['two'] = 'kaZING'
        cb.assert_has_calls((call(self.s, name='three', value='(kazam)'),))
        self.s['one'] = 'zup'
        cb.assert_has_calls((call(self.s, name='three', value='(kazam)'),))

    def test_on_change_autoremove(self):
        x = 0
        def cb(settings, name, value):
            nonlocal x
            x += 1
        self.s.on_change(cb, name='three', autoremove=True)
        self.s['three'] = 'foo'
        self.assertEqual(x, 1)
        del cb
        self.s['three'] = 'bar'
        self.assertEqual(x, 1)
