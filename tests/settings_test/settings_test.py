from stig.settings import LocalSettings, RemoteSettings, CombinedSettings

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


class TestCombinedSettings(asynctest.TestCase):
    def setUp(self):
        self.lcfg = MagicMock()
        self.rcfg = MagicMock()
        self.cfg = CombinedSettings(local=self.lcfg, remote=self.rcfg)

    def test_is_local_remote(self):
        self.assertTrue(self.cfg.is_local('foo'))
        self.assertFalse(self.cfg.is_local('srv.foo'))
        self.assertFalse(self.cfg.is_remote('foo'))
        self.assertTrue(self.cfg.is_remote('srv.foo'))

    async def test_update(self):
        self.rcfg.update = asynctest.CoroutineMock()
        await self.cfg.update()
        self.rcfg.update.assert_called_once_with()

    async def test_set(self):
        self.lcfg.__contains__.side_effect = lambda name: name == 'foo'
        self.rcfg.__contains__.side_effect = lambda name: name == 'srv.foo'
        self.rcfg.set = asynctest.CoroutineMock()
        await self.cfg.set('foo', 'bar')
        self.lcfg.__setitem__.assert_called_once_with('foo', 'bar')
        self.rcfg.set.assert_not_called()

        self.lcfg.reset_mock()
        await self.cfg.set('srv.foo', 'bar')
        self.lcfg.__setitem__.assert_not_called()
        self.rcfg.set.assert_called_once_with('srv.foo', 'bar')

        with self.assertRaises(KeyError):
            await self.cfg.set('bar', 'baz')
        with self.assertRaises(KeyError):
            await self.cfg.set('srv.bar', 'baz')

    def test_reset(self):
        self.lcfg.__contains__.side_effect = lambda name: name == 'foo'
        self.rcfg.__contains__.side_effect = lambda name: name == 'srv.foo'
        self.cfg.reset('foo')
        self.lcfg.reset.assert_called_once_with('foo')
        self.cfg.reset('srv.foo')
        self.rcfg.reset.assert_called_once_with('srv.foo')

    def test_default(self):
        self.lcfg.__contains__.side_effect = lambda name: name == 'foo'
        self.rcfg.__contains__.side_effect = lambda name: name == 'srv.foo'
        self.cfg.default('foo')
        self.lcfg.default.assert_called_once_with('foo')
        self.cfg.default('srv.foo')
        self.rcfg.default.assert_called_once_with('srv.foo')

    def test_description(self):
        self.lcfg.__contains__.side_effect = lambda name: name == 'foo'
        self.rcfg.__contains__.side_effect = lambda name: name == 'srv.foo'
        self.cfg.description('foo')
        self.lcfg.description.assert_called_once_with('foo')
        self.cfg.description('srv.foo')
        self.rcfg.description.assert_called_once_with('srv.foo')

    def test_syntax(self):
        self.lcfg.__contains__.side_effect = lambda name: name == 'foo'
        self.rcfg.__contains__.side_effect = lambda name: name == 'srv.foo'
        self.cfg.syntax('foo')
        self.lcfg.syntax.assert_called_once_with('foo')
        self.cfg.syntax('srv.foo')
        self.rcfg.syntax.assert_called_once_with('srv.foo')

    def test_validate(self):
        self.lcfg.__contains__.side_effect = lambda name: name == 'foo'
        self.rcfg.__contains__.side_effect = lambda name: name == 'srv.foo'
        self.cfg.validate('foo', 'bar')
        self.lcfg.validate.assert_called_once_with('foo', 'bar')
        self.cfg.validate('srv.foo', 'bar')
        self.rcfg.validate.assert_called_once_with('srv.foo', 'bar')

    def test_as_dict(self):
        self.lcfg.as_dict = {'foo': 1, 'bar': 'hello'}
        self.rcfg.as_dict = {'srv.asdf': 'something', 'srv.baz': 'something else'}
        self.assertEqual(self.cfg.as_dict, {'foo': 1, 'bar': 'hello',
                                            'srv.asdf': 'something', 'srv.baz': 'something else'})

    def test_getitem(self):
        self.lcfg.__contains__.side_effect = lambda name: name == 'foo'
        self.rcfg.__contains__.side_effect = lambda name: name == 'srv.foo'
        self.cfg['foo']
        self.lcfg.__getitem__.assert_called_once_with('foo')
        self.cfg['srv.foo']
        self.rcfg.__getitem__.assert_called_once_with('srv.foo')

    def test_setitem(self):
        self.lcfg.__contains__.side_effect = lambda name: name == 'foo'
        self.rcfg.__contains__.side_effect = lambda name: name == 'srv.foo'
        self.cfg['foo'] = 'bar'
        self.lcfg.__setitem__.assert_called_once_with('foo', 'bar')
        self.cfg['srv.foo'] = 'bar'
        self.rcfg.__setitem__.assert_called_once_with('srv.foo', 'bar')

    def test_contains(self):
        self.lcfg.__contains__.side_effect = lambda name: name == 'foo'
        self.rcfg.__contains__.side_effect = lambda name: name == 'srv.foo'
        self.assertIn('foo', self.cfg)
        self.assertIn('srv.foo', self.cfg)
        self.assertNotIn('bar', self.cfg)
        self.assertNotIn('srv.bar', self.cfg)

    def test_iter(self):
        self.lcfg.__iter__.return_value = ('foo', 'bar')
        self.rcfg.__iter__.return_value = ('srv.foo', 'srv.bar')
        self.assertEqual(tuple(self.cfg), ('foo', 'bar', 'srv.foo', 'srv.bar'))

    def test_len(self):
        self.lcfg.__len__.return_value = 2
        self.rcfg.__len__.return_value = 3
        self.assertEqual(len(self.cfg), 5)
