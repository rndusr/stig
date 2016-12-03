import asynctest

from stig.client.utils import Response
from stig.client.base import TorrentBase


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
                raise self.raises
            elif isinstance(self.response, Response):
                return self.response
            elif isinstance(self.response, list):
                return self.response.pop(0)
        return mock_method

    def assert_called(self, calls_exp, methodname, *args_exp):
        assert methodname in self._methods, '{!r} method was not called'.format(methodname)
        calls = self._methods[methodname]['calls']
        assert calls == calls_exp, '{!r} method was called {} times, not {}'.format(methodname, calls, calls_exp)
        posargs = self._methods[methodname]['posargs']
        kwargs = self._methods[methodname]['kwargs']
        posargs_exp = list(arg for arg in args_exp if isinstance(arg, tuple))
        kwargs_exp = list(arg for arg in args_exp if isinstance(arg, dict))
        assert posargs == posargs_exp, '\n{} !=\n{}'.format(posargs, posargs_exp)
        assert kwargs == kwargs_exp, '\n{} !=\n{}'.format(kwargs, kwargs_exp)


class MockTorrent(TorrentBase):
    def __init__(self, **kwargs):
        self._d = kwargs

    def __getitem__(self, item):
        return self._d[item]


class MockTorrentFilter():
    def __init__(self, *args, **kwargs):
        pass
    needed_keys = ('name', 'id')

class MockTorrentSorter(MockTorrentFilter):
    def apply(self, torrents):
        if hasattr(self, 'raises'):
            raise self.raises
        self.applied = torrents
        return torrents


class MockUtils():
    def __init__(self):
        self.logged = []

    def parseargs_tfilter(self, args):
        self.filterobj = MockTorrentFilter(args)
        return self.filterobj

    def parseargs_sort(self, args):
        self.sortobj = MockTorrentSorter(args)
        return self.sortobj

    torrent_columns = ['name']
    def parseargs_torrent_columns(self, args):
        return self.torrent_columns

    def listify_args(self, lst):
        return lst

    def log_msgs(self, *args, **kwargs):
        # Don't mock logging so we can check what is actually logged on the
        # different levels level.
        from stig.commands.utils import log_msgs
        return log_msgs(*args, **kwargs)


class MockHelpManager():
    @property
    def overview(self):
        return ['Mock overview']

    def find(self, topic):
        if topic == 'unknown':
            raise ValueError('Unknown topic: unknown')
        else:
            return ['Mock help for {}'.format(topic)]


from types import SimpleNamespace
def MockSettings():
    cfg = {'srv.url': SimpleNamespace(value='http://localhost:9091',
                                      typename='string'),
           'tlist.sort': SimpleNamespace(value=['name'],
                                         typename='list'),
           'tlist.columns': SimpleNamespace(value=['name', 'rate-down', 'rate-up'],
                                            typename='list'),
           'some.string': SimpleNamespace(value='foo',
                                          typename='string'),
           'some.integer': SimpleNamespace(value=10,
                                           typename='integer'),
           'some.number': SimpleNamespace(value=3.7,
                                          typename='number'),
           'some.list': SimpleNamespace(value=('bob', 'alice'),
                                        typename='list'),
           'some.boolean': SimpleNamespace(value=True,
                                           typename='boolean'),
           'some.option': SimpleNamespace(value='blue', options=('red', 'green', 'blue'),
                                          typename='option: red, green, blue'),
    }

    for ns in cfg.values():
        def setfunc(value, ns=ns):
            print('Fakesetting {}.value = {!r}'.format(ns, value))
            ns.value = value
        ns.set = setfunc
    return cfg



import re
class CommandTestCase(asynctest.TestCase):
    def setUp(self):
        self.api = SimpleNamespace(torrent=MockAPI(),
                                   rpc=MockAPI())
        self.cmdutils = MockUtils()
        self.cfg = MockSettings()
        self.helpmgr = MockHelpManager()

    def assert_logged(self, logged, *msgs):
        # msgs is a sequence of two-tuples: The first item is the level name, the
        # second item is a regular expression that matches the message string.
        for record,msg in zip(logged.records, msgs):
            self.assertEqual(record.levelname.lower(), msg[0].lower())
            self.assertRegex(record.message, msg[1])

    async def finish(self, process):
        if process.task is not None:
            await process.task
        self.assertEqual(process.finished, True)
