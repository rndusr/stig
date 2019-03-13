import asynctest

from stig.client.utils import Response
from stig.client.base import TorrentBase
from stig.commands import (InitCommand, _CommandBase, CmdError)


def make_cmdcls(defaults=True, **clsattrs):
    assert isinstance(defaults, bool)
    if defaults:
        for k,v in dict(name='foo', category='catfoo',
                        provides=('tui', 'cli'),
                        description='bla').items():
            if k not in clsattrs:
                clsattrs[k] = v

        if 'run' not in clsattrs:
            clsattrs['retval'] = True
            clsattrs['run'] = lambda self: self.retval

    if 'name' in clsattrs:
        clsname = clsattrs['name'].capitalize()+'Command'
    else:
        clsname = 'MockCommand'

    cmdcls = InitCommand(clsname, (), clsattrs)
    assert issubclass(cmdcls, _CommandBase)
    return cmdcls


class Callback():
    def __init__(self):
        self.reset()

    def reset(self):
        self.calls = 0
        self.args = []
        self.kwargs = []

    def __call__(self, *args, **kwargs):
        self.calls += 1
        self.args.append(args)
        self.kwargs.append(kwargs)


def assertIsException(obj, exccls, text):
    assert isinstance(obj, exccls), 'Not a {!r}: {!r}'.format(exccls.__name__, obj)
    assert text in str(obj), 'Not in {!r}: {!r}'.format(obj, text)
    return True


class MockAPI():
    def __init__(self, *args, **kwargs):
        self.init_args = args
        self.init_kwargs = kwargs
        self._methods = {}
        self.response = None
        self.raises = None

    def __getattr__(self, methodname):
        async def mock_method(*posargs, **kwargs):
            if methodname not in self._methods:
                self._methods[methodname] = {'posargs': [], 'kwargs': [], 'calls': 0}
            self._methods[methodname]['posargs'].append(posargs)
            self._methods[methodname]['kwargs'].append(kwargs)
            self._methods[methodname]['calls'] += 1
            if self.raises is not None:
                exc = self.raises
                self.raises = None
                raise exc
            elif isinstance(self.response, Response):
                return self.response
            elif isinstance(self.response, list) and self.response:
                return self.response.pop(0)
        return mock_method

    def assert_called(self, calls_exp, methodname, *args_exp):
        if calls_exp == 0:
            assert methodname not in self._methods, '{!r} method was called'.format(methodname)
        else:
            assert methodname in self._methods, '{!r} method was not called'.format(methodname)
            calls = self._methods[methodname]['calls']
            assert calls == calls_exp, '{!r} method was called {} times, not {}'.format(methodname, calls, calls_exp)
            posargs = self._methods[methodname]['posargs']
            kwargs = self._methods[methodname]['kwargs']
            posargs_exp = list(arg for arg in args_exp if isinstance(arg, tuple))
            kwargs_exp = list(arg for arg in args_exp if isinstance(arg, dict))
            assert posargs == posargs_exp, '\n{} !=\n{}'.format(posargs, posargs_exp)
            assert kwargs == kwargs_exp, '\n{} !=\n{}'.format(kwargs, kwargs_exp)

    def forget_calls(self):
        self._methods.clear()


class MockTorrent(TorrentBase):
    def __init__(self, **kwargs):
        self._d = kwargs

    def __getitem__(self, item):
        return self._d[item]


class MockTorrentFilter():
    def __init__(self, *args, **kwargs):
        pass
    needed_keys = ('name', 'id')

def mock_select_torrents(self, *args, **kwargs):
    self.mock_tfilter = MockTorrentFilter(*args, **kwargs)
    return self.mock_tfilter


class MockTorrentSorter(MockTorrentFilter):
    def apply(self, torrents):
        if hasattr(self, 'raises'):
            raise self.raises
        self.applied = torrents
        return torrents

def mock_get_torrent_sorter(self, *args, **kwargs):
    self.mock_tsorter = MockTorrentSorter(*args, **kwargs)
    return self.mock_tsorter


class MockHelpManager():
    def find(self, topic):
        if topic == 'unknown':
            raise ValueError('Unknown topic: unknown')
        else:
            return ['Mock help for {}'.format(topic)]


class MockSettings(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reset = MagicMock()

class MockRemoteSettings(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set = CoroutineMock()
        self.update = CoroutineMock()


from types import SimpleNamespace
import sys, io
from unittest.mock import (patch, MagicMock)
from asynctest import CoroutineMock
class CommandTestCase(asynctest.TestCase):
    def setUp(self):
        self.api = SimpleNamespace(torrent=MockAPI(),
                                   rpc=MockAPI(),
                                   settings=MockAPI())
        self.cfg = MockSettings()
        self.srvcfg = MockRemoteSettings()
        self.helpmgr = MockHelpManager()
        self.cmdmgr = MagicMock()
        self.cmdmgr.run_async = CoroutineMock()

        self.stdout = sys.stdout = io.StringIO()
        def reset_stdout(): sys.stdout = sys.__stdout__
        self.addCleanup(reset_stdout)

        self.stderr = sys.stderr = io.StringIO()
        def reset_stderr(): sys.stderr = sys.__stderr__
        self.addCleanup(reset_stderr)

    def patch(self, *args, **kwargs):
        if kwargs:
            patcher = patch.multiple(*args, **kwargs)
        else:
            patcher = patch(*args)
        mock_obj = patcher.start()
        self.addCleanup(patcher.stop)
        return mock_obj

    async def execute(self, cmdcls, *params):
        process = cmdcls(params,
                         error_handler=lambda msg: print(msg, file=self.stderr),
                         loop=self.loop)
        if not process.finished:
            await process.wait_async()
        self.assertTrue(process.finished)
        return process

    def assert_stdout(self, *lines_exp):
        self.stdout.seek(0)
        self._compare_lines(self.stdout.readlines(), lines_exp)

    def assert_stderr(self, *lines_exp):
        self.stderr.seek(0)
        self._compare_lines(self.stderr.readlines(), lines_exp)

    def assert_completion_candidates(self, cmdcls, args, curarg_index, exp_cands):
        from stig.utils.cliparser import Args
        args = Args(args, curarg_index)
        self.assertEqual(cmdcls.completion_candidates(args), exp_cands)

    def _compare_lines(self, lines, lines_exp):
        from itertools import zip_longest
        for line,line_exp in zip_longest(lines, lines_exp, fillvalue='<NO MESSAGE>'):
            line = line.rstrip('\n')
            self.assertRegex(line, line_exp)

    def clear_stdout(self):
        self.stdout = sys.stdout = io.StringIO()

    def clear_stderr(self):
        self.stderr = sys.stderr = io.StringIO()
