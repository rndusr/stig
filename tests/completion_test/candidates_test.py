from stig.completion import (candidates, Candidates)
from stig.utils.cliparser import Args

import unittest
from unittest.mock import patch, call

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
                    self.assertEqual(candidates.setting_values(cmdline), None)


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
