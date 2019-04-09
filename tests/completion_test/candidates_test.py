from stig.completion import (candidates, Candidates)
from stig.utils.cliparser import (Args, Arg)
from stig.utils import usertypes

import unittest
import asynctest
from unittest.mock import patch, MagicMock, call
from types import SimpleNamespace


class Test_setting_names(unittest.TestCase):
    def setUp(self):
        # Because setting_names is an lru_cache
        candidates.setting_names.cache_clear()

    @patch('stig.objects.localcfg')
    @patch('stig.objects.remotecfg')
    def test_remote_and_local_settings_are_combined(self, mock_rcfg, mock_lcfg):
        mock_lcfg.__iter__.return_value = ('foo', 'bar', 'baz')
        mock_rcfg.__iter__.return_value = ('Foo', 'Bar', 'Baz')
        cands = candidates.setting_names()
        self.assertEqual(tuple(cands), ('bar', 'baz', 'foo', 'srv.Bar', 'srv.Baz', 'srv.Foo'))
        self.assertEqual(cands.label, 'Settings')

    @patch('stig.objects.localcfg')
    @patch('stig.objects.remotecfg')
    def test_description(self, mock_rcfg, mock_lcfg):
        mock_lcfg.__iter__.return_value = ('foo', 'bar')
        mock_rcfg.__iter__.return_value = ('Foo', 'Bar')
        mock_lcfg.description.side_effect = lambda name: 'mock description for local setting %s' % name
        mock_rcfg.description.side_effect = lambda name: 'mock description for remote setting %s' % name
        settings = candidates.setting_names()
        self.assertEqual(settings[0].description, 'mock description for local setting bar')
        self.assertEqual(settings[1].description, 'mock description for local setting foo')
        self.assertEqual(settings[2].description, 'mock description for remote setting Bar')
        self.assertEqual(settings[3].description, 'mock description for remote setting Foo')

    @patch('stig.objects.localcfg')
    @patch('stig.objects.remotecfg')
    def test_default(self, mock_rcfg, mock_lcfg):
        mock_lcfg.__iter__.return_value = ('foo', 'bar')
        mock_rcfg.__iter__.return_value = ('Foo', 'Bar')
        mock_lcfg.default.side_effect = lambda name: list(name)
        mock_rcfg.default.side_effect = lambda name: (name,) * 2
        cands = candidates.setting_names()
        self.assertEqual(cands[0].default, "['b', 'a', 'r']")
        self.assertEqual(cands[1].default, "['f', 'o', 'o']")
        self.assertEqual(cands[2].default, "('Bar', 'Bar')")
        self.assertEqual(cands[3].default, "('Foo', 'Foo')")


class Test_setting_values(unittest.TestCase):
    @patch('stig.objects.localcfg')
    @patch('stig.objects.remotecfg')
    def test_unknown_setting(self, mock_rcfg, mock_lcfg):
        mock_lcfg.__iter__.return_value = ('foo', 'bar', 'baz')
        mock_rcfg.__iter__.return_value = ('Foo', 'Bar', 'Baz')
        for args in (('foo', 'bar', 'baz'),
                     ('foo', 'bar', 'baz'),
                     ('foo', 'bar', 'baz')):
            for curarg_index in (0, 1, 2):
                for curarg_curpos in (0, 1, 2, 3):
                    cmdline = Args(args, curarg_index=curarg_index, curarg_curpos=curarg_curpos)
                    self.assertFalse(candidates.setting_values(cmdline))

    @patch('stig.objects.localcfg')
    @patch('stig.objects.remotecfg')
    def test_setting_is_an_Option(self, mock_rcfg, mock_lcfg):
        for mock_cfg,setting_name in ((mock_lcfg, 'foo'),
                                      (mock_rcfg, 'srv.foo')):
            mock_cfg.__iter__.return_value = (setting_name,)
            mock_cfg.__contains__.return_value = True
            mock_cfg.__getitem__.return_value = usertypes.Option('b', options=('a', 'b', 'c'))
            cmdline = Args((setting_name, '_', '_'), curarg_index=1, curarg_curpos=0)
            self.assertEqual(candidates.setting_values(cmdline), Candidates(('a', 'b', 'c'),
                                                                            label='%s options' % setting_name))
            cmdline = Args((setting_name, '_', '_'), curarg_index=2, curarg_curpos=0)
            self.assertFalse(candidates.setting_values(cmdline))

    @patch('stig.objects.localcfg')
    @patch('stig.objects.remotecfg')
    def test_setting_is_a_Tuple(self, mock_rcfg, mock_lcfg):
        for mock_cfg,setting_name in ((mock_lcfg, 'foo'),
                                      (mock_rcfg, 'srv.foo')):
            mock_cfg.__iter__.return_value = (setting_name,)
            mock_cfg.__contains__.return_value = True
            mock_cfg.__getitem__.return_value = usertypes.Tuple('a', 'b', options=('a', 'b', 'c'))
            for i in (1, 2, 3):
                cmdline = Args((setting_name, '_', '_', '_'), curarg_index=i, curarg_curpos=0)
                cands = candidates.setting_values(cmdline)
                exp_cands = Candidates(('a', 'b', 'c'), label='%s options' % setting_name, curarg_seps=(',',))
                self.assertEqual(cands, exp_cands)

    @patch('stig.objects.localcfg')
    @patch('stig.objects.remotecfg')
    def test_setting_is_a_Bool(self, mock_rcfg, mock_lcfg):
        for mock_cfg,setting_name in ((mock_lcfg, 'foo'),
                                      (mock_rcfg, 'srv.foo')):
            mock_cfg.__iter__.return_value = (setting_name,)
            mock_cfg.__contains__.return_value = True
            mock_cfg.__getitem__.return_value = usertypes.Bool('1', true=('1',), false=('0',))
            cmdline = Args((setting_name, '_', '_'), curarg_index=1, curarg_curpos=0)
            cands = candidates.setting_values(cmdline)
            exp_cands = Candidates(('1', '0'), label='%s options' % setting_name)
            self.assertEqual(cands, exp_cands)
            cmdline = Args((setting_name, '_', '_'), curarg_index=2, curarg_curpos=0)
            self.assertFalse(candidates.setting_values(cmdline))

    @patch('stig.objects.localcfg')
    @patch('stig.objects.remotecfg')
    @patch('os.path.isdir')
    @patch('stig.completion.candidates.fs_path')
    def test_setting_is_a_Path(self, mock_fs_path, mock_isdir, mock_rcfg, mock_lcfg):
        for mock_cfg,setting_name in ((mock_lcfg, 'foo'),
                                      (mock_rcfg, 'srv.foo')):
            for mocking_directory in (True, False):
                mock_isdir.return_value = mocking_directory
                mock_cfg.__iter__.return_value = (setting_name,)
                mock_cfg.__contains__.return_value = True
                mock_cfg.__getitem__.return_value = usertypes.Path('mock/path', base='/mockbase/')
                cmdline = Args((setting_name, 'abcdef'), curarg_index=1, curarg_curpos=3)
                candidates.setting_values(cmdline)
                mock_isdir.assert_called_with('mock/path')
                mock_fs_path.assert_called_with('abc', base='/mockbase/',
                                                directories_only=mocking_directory)


class Test_fs_path(unittest.TestCase):
    def do(self, *args, exp_cands, **kwargs):
        cands = candidates.fs_path(*args, **kwargs)
        self.assertEqual(tuple(cands), tuple(sorted(exp_cands)))
        self.assertEqual(cands.curarg_seps, ('/',))

    @patch('os.scandir')
    @patch('os.path.expanduser')
    def test_base_path(self, expanduser, scandir):
        expanduser.side_effect = lambda path: path.replace('~', '/home/')
        candidates.fs_path('abc', '/asdf')
        self.assertEqual(scandir.call_args, call('/asdf'))
        candidates.fs_path('abc/def', '/asdf')
        self.assertEqual(scandir.call_args, call('/asdf/abc'))
        candidates.fs_path('abc/def/', '/asdf')
        self.assertEqual(scandir.call_args, call('/asdf/abc/def'))

    @patch('pwd.getpwall')
    def test_tilde_without_path(self, getpwall):
        getpwall.return_value = [SimpleNamespace(pw_name='foo'),
                                 SimpleNamespace(pw_name='bar'),
                                 SimpleNamespace(pw_name='baz')]
        self.do('~', base='/', exp_cands=('~foo', '~bar', '~baz'))
        self.do('~x', base='/', exp_cands=('~foo', '~bar', '~baz'))
        self.do('~xx', base='/', exp_cands=('~foo', '~bar', '~baz'))

    @patch('os.scandir')
    @patch('os.path.expanduser')
    def test_tilde_with_path(self, expanduser, scandir):
        expanduser.side_effect = lambda path: path.replace('~', '/home/')
        scandir.return_value = [
            SimpleNamespace(name='foo', is_dir=lambda *a, **k: True),
            SimpleNamespace(name='bar', is_dir=lambda *a, **k: False),
            SimpleNamespace(name='baz', is_dir=lambda *a, **k: False)
        ]
        self.do('~x/', base='/', exp_cands=('foo', 'bar', 'baz'))
        self.do('~x/x', base='/', exp_cands=('foo', 'bar', 'baz'))
        self.do('~x/xx', base='/', exp_cands=('foo', 'bar', 'baz'))

    @patch('os.scandir')
    @patch('os.path.expanduser')
    def test_directories_only(self, expanduser, scandir):
        expanduser.side_effect = lambda path: path.replace('~', '/home/')
        scandir.return_value = [
            SimpleNamespace(name='foo', is_dir=lambda *a, **k: True),
            SimpleNamespace(name='bar', is_dir=lambda *a, **k: False),
            SimpleNamespace(name='baz', is_dir=lambda *a, **k: False)
        ]
        self.do('~x/', base='/', directories_only=True, exp_cands=('foo',))
        self.do('~x/x', base='/', directories_only=True, exp_cands=('foo',))
        self.do('~x/xx', base='/', directories_only=False, exp_cands=('foo', 'bar', 'baz'))

    @patch('os.scandir')
    @patch('os.path.expanduser')
    def test_complete_hidden_files(self, expanduser, scandir):
        expanduser.side_effect = lambda path: path.replace('~', '/home/')
        scandir.return_value = [
            SimpleNamespace(name='.foo', is_dir=lambda *a, **k: True),
            SimpleNamespace(name='bar', is_dir=lambda *a, **k: False),
            SimpleNamespace(name='.baz', is_dir=lambda *a, **k: False)
        ]
        self.do('x', base='/', exp_cands=('bar',))
        self.do('.', base='/', exp_cands=('.foo', 'bar', '.baz'))
        self.do('./', base='/', exp_cands=('bar',))
        self.do('./.', base='/', exp_cands=('.foo', 'bar', '.baz'))
        self.do('/a/b/c/', base='/', exp_cands=('bar',))
        self.do('/a/b/c/.', base='/', exp_cands=('.foo', 'bar', '.baz'))
        self.do('/a/b/c/.def', base='/', exp_cands=('.foo', 'bar', '.baz'))
        self.do('/a/b/c/def', base='/', exp_cands=('bar',))
        self.do('~abc/', base='/', exp_cands=('bar',))
        self.do('~abc/.', base='/', exp_cands=('.foo', 'bar', '.baz'))
        self.do('~abc/.def', base='/', exp_cands=('.foo', 'bar', '.baz'))
        self.do('~abc/def', base='/', exp_cands=('bar',))

    @patch('os.scandir')
    def test_regex(self, scandir):
        scandir.return_value = [
            SimpleNamespace(name='foo', is_dir=lambda *a, **k: False),
            SimpleNamespace(name='bar', is_dir=lambda *a, **k: False),
            SimpleNamespace(name='baz', is_dir=lambda *a, **k: True)
        ]
        self.do('x', base='/', regex=r'b', exp_cands=('bar', 'baz'))
        self.do('x', base='/', regex=r'oo$', exp_cands=('foo', 'baz'))
        self.do('x', base='/', regex=r'asdf', exp_cands=('baz',))

    @patch('os.scandir')
    def test_glob(self, scandir):
        scandir.return_value = [
            SimpleNamespace(name='foo', is_dir=lambda *a, **k: False),
            SimpleNamespace(name='bar', is_dir=lambda *a, **k: False),
            SimpleNamespace(name='baz', is_dir=lambda *a, **k: True)
        ]
        self.do('x', base='/', glob=r'f*', exp_cands=('foo', 'baz'))
        self.do('x', base='/', glob=r'*r', exp_cands=('bar', 'baz'))


class Test_filter_helper_functions(unittest.TestCase):
    @patch('stig.completion.candidates.filter_clses')
    def test_get_filter_cls(self, mock_filter_clses):
        mock_filter_clses.mock_add_spec(('FooFilter',), spec_set=True)
        mock_filter_clses.FooFilter = 'mock filter'
        self.assertEqual(candidates._get_filter_cls('FooFilter'), 'mock filter')
        with self.assertRaises(ValueError):
            candidates._get_filter_cls('BarFilter')

    def test_get_filter_names(self):
        mock_filter_cls = MagicMock()
        mock_filter_cls.BOOLEAN_FILTERS = {'foo': None, 'bar': None}
        mock_filter_cls.COMPARATIVE_FILTERS = {'baz': None}
        self.assertEqual(tuple(candidates._get_filter_names(mock_filter_cls)),
                         ('foo', 'bar', 'baz'))

    def test_get_filter_spec(self):
        mock_filter_cls = MagicMock()
        mock_filter_cls.BOOLEAN_FILTERS = {'foo': 'mock foo spec', 'bar': 'mock bar spec'}
        mock_filter_cls.COMPARATIVE_FILTERS = {'baz': 'mock baz spec'}
        self.assertEqual(candidates._get_filter_spec(mock_filter_cls, 'foo'), 'mock foo spec')
        self.assertEqual(candidates._get_filter_spec(mock_filter_cls, 'bar'), 'mock bar spec')
        self.assertEqual(candidates._get_filter_spec(mock_filter_cls, 'baz'), 'mock baz spec')

    def test_filter_takes_completable_values(self):
        mock_filter_cls = MagicMock()
        mock_filter_cls.BOOLEAN_FILTERS = {'foo': None}
        mock_filter_cls.COMPARATIVE_FILTERS = {'bar': SimpleNamespace(value_type=str),
                                               'baz': SimpleNamespace(value_type=int)}
        self.assertEqual(candidates._filter_takes_completable_values(mock_filter_cls, 'bar'), True)
        self.assertEqual(candidates._filter_takes_completable_values(mock_filter_cls, 'baz'), False)
        self.assertEqual(candidates._filter_takes_completable_values(mock_filter_cls, 'foo'), False)
        self.assertEqual(candidates._filter_takes_completable_values(mock_filter_cls, 'asdf'), False)


class Test_torrent_filter_values(asynctest.TestCase):
    @asynctest.patch('stig.completion.candidates._filter_combine_ops', new=('|', '&'))
    @asynctest.patch('stig.completion.candidates._filter_compare_ops', new=('=', '!='))
    @asynctest.patch('stig.completion.candidates._get_filter_cls')
    @asynctest.patch('stig.completion.candidates._filter_takes_completable_values')
    @asynctest.patch('stig.completion.candidates.objects.srvapi.torrent.torrents')
    async def test_filter_takes_no_completable_values(self, mock_torrents,
                                                      mock_filter_takes_completable_values,
                                                      mock_get_filter_cls):
        mock_get_filter_cls.return_value = 'mock TorrentFilter class'
        mock_filter_takes_completable_values.return_value = False
        cands = await candidates._torrent_filter_values('mock filter name')
        mock_get_filter_cls.assert_called_once_with('TorrentFilter')
        mock_filter_takes_completable_values.assert_called_once_with('mock TorrentFilter class',
                                                                     'mock filter name')
        exp_cands = Candidates((), curarg_seps=('|', '&', '=', '!='),
                               label='Torrent Filter Values: mock filter name')
        self.assertEqual(cands, exp_cands)

    @asynctest.patch('stig.completion.candidates._filter_combine_ops', new=('|', '&'))
    @asynctest.patch('stig.completion.candidates._filter_compare_ops', new=('=', '!='))
    @asynctest.patch('stig.completion.candidates._get_filter_cls')
    @asynctest.patch('stig.completion.candidates._get_filter_spec')
    @asynctest.patch('stig.completion.candidates._filter_takes_completable_values')
    @asynctest.patch('stig.completion.candidates.objects.srvapi.torrent.torrents')
    async def test_server_request_failed(self, mock_torrents,
                                         mock_filter_takes_completable_values,
                                         mock_get_filter_spec,
                                         mock_get_filter_cls):
        mock_filter_takes_completable_values.return_value = True
        mock_get_filter_cls.return_value.return_value.needed_keys = ('mockkey1', 'mockkey2')
        mock_torrents.return_value.success = False
        cands = await candidates._torrent_filter_values('mockfilter')
        mock_torrents.assert_called_with(keys=('mockkey1', 'mockkey2'), from_cache=True)
        mock_get_filter_spec.assert_not_called()
        exp_cands = Candidates((), curarg_seps=('|', '&', '=', '!='),
                               label='Torrent Filter Values: mockfilter')
        self.assertEqual(cands, exp_cands)

    @asynctest.patch('stig.completion.candidates._filter_combine_ops', new=('|', '&'))
    @asynctest.patch('stig.completion.candidates._filter_compare_ops', new=('=', '!='))
    @asynctest.patch('stig.completion.candidates._get_filter_cls')
    @asynctest.patch('stig.completion.candidates._get_filter_spec')
    @asynctest.patch('stig.completion.candidates._filter_takes_completable_values')
    @asynctest.patch('stig.completion.candidates.objects.srvapi.torrent.torrents')
    async def test_torrent_value_is_string(self, mock_torrents,
                                             mock_filter_takes_completable_values,
                                             mock_get_filter_spec,
                                             mock_get_filter_cls):
        mock_filter_takes_completable_values.return_value = True
        mock_get_filter_cls.return_value.return_value.needed_keys = ('mockkey1', 'mockkey2')
        mock_torrents.return_value.success = True
        mock_torrents.return_value.torrents = ('mock torrent 1', 'mock torrent 2')
        mock_get_filter_spec.return_value.value_getter.side_effect = (
            'mock torrent 1 value', 'mock torrent 2 value')
        cands = await candidates._torrent_filter_values('mockfilter')
        mock_torrents.assert_called_once_with(keys=('mockkey1', 'mockkey2'), from_cache=True)
        mock_value_getter = mock_get_filter_spec.return_value.value_getter
        mock_value_getter.assert_any_call('mock torrent 1')
        mock_value_getter.assert_any_call('mock torrent 2')
        exp_cands = Candidates(('mock torrent 1 value', 'mock torrent 2 value'),
                               curarg_seps=('|', '&', '=', '!='),
                               label='Torrent Filter Values: mockfilter')
        self.assertEqual(cands, exp_cands)

    @asynctest.patch('stig.completion.candidates._filter_combine_ops', new=('|', '&'))
    @asynctest.patch('stig.completion.candidates._filter_compare_ops', new=('=', '!='))
    @asynctest.patch('stig.completion.candidates._get_filter_cls')
    @asynctest.patch('stig.completion.candidates._get_filter_spec')
    @asynctest.patch('stig.completion.candidates._filter_takes_completable_values')
    @asynctest.patch('stig.completion.candidates.objects.srvapi.torrent.torrents')
    async def test_torrent_value_is_iterable(self, mock_torrents,
                                             mock_filter_takes_completable_values,
                                             mock_get_filter_spec,
                                             mock_get_filter_cls):
        mock_filter_takes_completable_values.return_value = True
        mock_get_filter_cls.return_value.return_value.needed_keys = ('mockkey1', 'mockkey2')
        mock_torrents.return_value.success = True
        mock_torrents.return_value.torrents = ('mock torrent 1', 'mock torrent 2')
        mock_get_filter_spec.return_value.value_getter.side_effect = (
            ('mock torrent 1 value 1', 'mock torrent 1 value 2'),
            ('mock torrent 2 value 1', 'mock torrent 2 value 2'))
        cands = await candidates._torrent_filter_values('mockfilter')
        mock_torrents.assert_called_once_with(keys=('mockkey1', 'mockkey2'), from_cache=True)
        mock_value_getter = mock_get_filter_spec.return_value.value_getter
        mock_value_getter.assert_any_call('mock torrent 1')
        mock_value_getter.assert_any_call('mock torrent 2')
        exp_cands = Candidates(('mock torrent 1 value 1', 'mock torrent 1 value 2',
                                'mock torrent 2 value 1', 'mock torrent 2 value 2'),
                               curarg_seps=('|', '&', '=', '!='),
                               label='Torrent Filter Values: mockfilter')
        self.assertEqual(cands, exp_cands)


class Test_torrent_filter(asynctest.TestCase):
    @asynctest.patch('stig.completion.candidates._filter_combine_ops', ('|', '&'))
    @asynctest.patch('stig.completion.candidates._filter_compare_ops', ('=', '!='))
    @asynctest.patch('stig.completion.candidates._torrent_filter_values')
    @asynctest.patch('stig.completion.candidates._get_filter_cls')
    @asynctest.patch('stig.completion.candidates._filter_names')
    async def test_focusing_filter_name(self, mock_filter_names, mock_get_filter_cls, mock_torrent_filter_values):
        mock_get_filter_cls.return_value.INVERT_CHAR = '!'
        mock_get_filter_cls.return_value.DEFAULT_FILTER = 'mock default filter'
        mock_filter_names.return_value = Candidates(('foo', 'bar', 'baz'),
                                                    curarg_seps=('.', ':'),
                                                    label='Mock Filter Names')
        mock_torrent_filter_values.return_value = 'mock torrent values'
        cands = await candidates.torrent_filter(Arg('bar=asdf', curpos=2))
        mock_torrent_filter_values.assert_called_once_with('mock default filter')
        exp_cands = (
            Candidates(('foo', 'bar', 'baz'), curarg_seps=('.', ':'), label='Mock Filter Names'),
            'mock torrent values'
        )
        self.assertEqual(cands, exp_cands)

    @asynctest.patch('stig.completion.candidates._filter_combine_ops', ('|', '&'))
    @asynctest.patch('stig.completion.candidates._filter_compare_ops', ('=', '!='))
    @asynctest.patch('stig.completion.candidates._torrent_filter_values')
    @asynctest.patch('stig.completion.candidates._get_filter_cls')
    async def test_focusing_filter_value(self, mock_get_filter_cls, mock_torrent_filter_values):
        mock_get_filter_cls.return_value.INVERT_CHAR = '!'
        mock_torrent_filter_values.return_value = 'mock torrent values'
        cands = await candidates.torrent_filter(Arg('bar=asdf', curpos=4))
        mock_torrent_filter_values.assert_called_once_with('bar')
        exp_cands = ('mock torrent values',)
        self.assertEqual(cands, exp_cands)

    @asynctest.patch('stig.completion.candidates._filter_combine_ops', ('|', '&'))
    @asynctest.patch('stig.completion.candidates._filter_compare_ops', ('=', '!='))
    @asynctest.patch('stig.completion.candidates._torrent_filter_values')
    @asynctest.patch('stig.completion.candidates._get_filter_cls')
    async def test_operator_given_without_filter_name(self, mock_get_filter_cls, mock_torrent_filter_values):
        mock_get_filter_cls.return_value.INVERT_CHAR = '!'
        mock_get_filter_cls.return_value.DEFAULT_FILTER = 'mock default'
        mock_torrent_filter_values.return_value = 'mock torrent values'
        cands = await candidates.torrent_filter(Arg('=asdf', curpos=4))
        mock_torrent_filter_values.assert_called_once_with('mock default')
        exp_cands = ('mock torrent values',)
        self.assertEqual(cands, exp_cands)

    @asynctest.patch('stig.completion.candidates._filter_combine_ops', ('|', '&'))
    @asynctest.patch('stig.completion.candidates._filter_compare_ops', ('=', '!='))
    @asynctest.patch('stig.completion.candidates._torrent_filter_values')
    @asynctest.patch('stig.completion.candidates._get_filter_cls')
    async def test_invert_char_is_first_char(self, mock_get_filter_cls, mock_torrent_filter_values):
        mock_get_filter_cls.return_value.INVERT_CHAR = '!'
        mock_torrent_filter_values.return_value = 'mock torrent values'
        cands = await candidates.torrent_filter(Arg('!bar=asdf', curpos=5))
        mock_torrent_filter_values.assert_called_once_with('bar')
        exp_cands = ('mock torrent values',)
        self.assertEqual(cands, exp_cands)

    @asynctest.patch('stig.completion.candidates._filter_combine_ops', ('|', '&'))
    @asynctest.patch('stig.completion.candidates._filter_compare_ops', ('=', '!='))
    @asynctest.patch('stig.completion.candidates._torrent_filter_values')
    @asynctest.patch('stig.completion.candidates._get_filter_cls')
    async def test_invert_char_in_operator(self, mock_get_filter_cls, mock_torrent_filter_values):
        mock_get_filter_cls.return_value.INVERT_CHAR = '!'
        mock_torrent_filter_values.return_value = 'mock torrent values'
        cands = await candidates.torrent_filter(Arg('bar!=asdf', curpos=5))
        mock_torrent_filter_values.assert_called_once_with('bar')
        exp_cands = ('mock torrent values',)
        self.assertEqual(cands, exp_cands)
