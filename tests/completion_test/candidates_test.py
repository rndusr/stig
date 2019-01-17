from stig.completion import candidates

import unittest
from unittest.mock import patch, call

from types import SimpleNamespace


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
