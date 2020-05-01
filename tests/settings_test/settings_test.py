from stig.settings import LocalSettings, RemoteSettings

import unittest
from unittest.mock import MagicMock, call
import asynctest


class TestLocalSettings(unittest.TestCase):
    def setUp(self):
        self.s = LocalSettings()
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


class TestRemoteSettings(asynctest.TestCase):
    def setUp(self):
        self.api = MagicMock()
        self.remotecfg = RemoteSettings(self.api)

    def test_reset(self):
        with self.assertRaises(KeyError):
            self.remotecfg.reset('foo')
        with self.assertRaises(NotImplementedError):
            self.remotecfg.reset('srv.foo')

    def test_default(self):
        with self.assertRaises(KeyError):
            self.remotecfg.default('foo')
        self.remotecfg.default('srv.foo')
        self.api.default.assert_called_once_with('foo')

    def test_description(self):
        with self.assertRaises(KeyError):
            self.remotecfg.description('foo')
        self.remotecfg.description('srv.foo')
        self.api.description.assert_called_once_with('foo')

    def test_syntax(self):
        with self.assertRaises(KeyError):
            self.remotecfg.syntax('foo')
        self.remotecfg.syntax('srv.foo')
        self.api.syntax.assert_called_once_with('foo')

    def test_validate(self):
        with self.assertRaises(KeyError):
            self.remotecfg.validate('foo', 'bar')
        self.remotecfg.validate('srv.foo', 'bar')
        self.api.validate.assert_called_once_with('foo', 'bar')

    def test_as_dict(self):
        self.api.as_dict = {'foo': {'id': 'foo', 'value': 1},
                                  'bar': {'id': 'bar', 'value': 'asdf'}}
        self.assertEqual(self.remotecfg.as_dict, {'srv.foo': {'id': 'srv.foo', 'value': 1},
                                            'srv.bar': {'id': 'srv.bar', 'value': 'asdf'}})

    def test_getitem(self):
        with self.assertRaises(KeyError):
            self.remotecfg['foo']
        def mock_getitem(name):
            if name == 'foo': return 1
            if name == 'bar': return 'asdf'
        self.api.__getitem__.side_effect = mock_getitem
        self.assertEqual(self.remotecfg['srv.foo'], 1)
        self.assertEqual(self.remotecfg['srv.bar'], 'asdf')

    def test_contains(self):
        self.assertNotIn('foo', self.remotecfg)
        def mock_contains(name):
            if name == 'foo': return True
            if name == 'bar': return False
        self.api.__contains__.side_effect = mock_contains
        self.assertTrue('srv.foo' in self.remotecfg)
        self.assertFalse('srv.bar' in self.remotecfg)

    def test_iter(self):
        self.api.__iter__.return_value = ('foo', 'bar')
        self.assertEqual(tuple(iter(self.remotecfg)), ('srv.foo', 'srv.bar'))

    def test_len(self):
        self.api.__len__.return_value = 123
        self.assertEqual(len(self.remotecfg), 123)

    def test_poll(self):
        self.remotecfg.poll()
        self.api.poll.assert_called_once_with()

    async def test_update(self):
        self.api.update = asynctest.CoroutineMock()
        await self.remotecfg.update()
        self.api.update.assert_called_once_with()

    async def test_set(self):
        with self.assertRaises(KeyError):
            await self.remotecfg.set('foo', 'bar')
        self.api.set = asynctest.CoroutineMock()
        await self.remotecfg.set('srv.foo', 'bar')
        self.api.set.assert_called_once_with('foo', 'bar')

    def test_on_update(self):
        cb = lambda: None
        self.remotecfg.on_update(cb, autoremove=False)
        self.api.on_update.assert_called_once_with(cb, autoremove=False)
