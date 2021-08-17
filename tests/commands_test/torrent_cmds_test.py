import os
from types import SimpleNamespace

import asynctest
from asynctest import CoroutineMock
from asynctest.mock import MagicMock, call, patch

from resources_cmd import (CommandTestCase, MockTorrent, mock_get_torrent_sorter,
                           mock_select_torrents)
from stig.client.utils import Response
from stig.commands.cli import (ListTorrentsCmd, RemoveTorrentsCmd, StartTorrentsCmd,
                               StopTorrentsCmd, TorrentDetailsCmd, VerifyTorrentsCmd)
from stig.completion import Candidates
from stig.utils.cliparser import Arg, Args


class TestAddTorrentsCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.patch('stig.objects',
                   srvapi=self.srvapi,
                   cfg=self.cfg)

    @patch.dict(os.environ, HOME='/mock/home/dir')
    async def test_CLI_make_path_absolute(self):
        from stig.commands.cli import AddTorrentsCmd
        with patch('os.path.exists', side_effect=lambda path: True):
            abspath = '/path/to/file.torrent'
            self.assertEqual(AddTorrentsCmd.make_path_absolute(abspath), '/path/to/file.torrent')
            cwdpath = './path/to/file.torrent'
            self.assertEqual(AddTorrentsCmd.make_path_absolute(cwdpath), os.path.join(os.getcwd(), 'path/to/file.torrent'))
            relpath = 'path/to/file.torrent'
            self.assertEqual(AddTorrentsCmd.make_path_absolute(relpath), os.path.join(os.getcwd(), 'path/to/file.torrent'))
            homepath = '~/path/to/file.torrent'
            self.assertEqual(AddTorrentsCmd.make_path_absolute(homepath), os.path.join(os.environ['HOME'], 'path/to/file.torrent'))
            uri = 'magnet:?xt=urn:btih:e186f17ea5b29a694f7e4b89865baa65e9e51083'
            self.assertEqual(AddTorrentsCmd.make_path_absolute(uri), os.path.join(os.getcwd(), uri))
            url = 'http://some/url.torrent'
            self.assertEqual(AddTorrentsCmd.make_path_absolute(url), os.path.join(os.getcwd(), 'http:/some/url.torrent'))
        with patch('os.path.exists', side_effect=lambda path: False):
            abspath = '/path/to/file.torrent'
            self.assertEqual(AddTorrentsCmd.make_path_absolute(abspath), '/path/to/file.torrent')
            cwdpath = './path/to/file.torrent'
            self.assertEqual(AddTorrentsCmd.make_path_absolute(cwdpath), './path/to/file.torrent')
            relpath = 'path/to/file.torrent'
            self.assertEqual(AddTorrentsCmd.make_path_absolute(relpath), 'path/to/file.torrent')
            homepath = '~/path/to/file.torrent'
            self.assertEqual(AddTorrentsCmd.make_path_absolute(homepath), '~/path/to/file.torrent')
            uri = 'magnet:?xt=urn:btih:e186f17ea5b29a694f7e4b89865baa65e9e51083'
            self.assertEqual(AddTorrentsCmd.make_path_absolute(uri), uri)
            url = 'http://some/url.torrent'
            self.assertEqual(AddTorrentsCmd.make_path_absolute(url), url)

    @patch.dict(os.environ, HOME='/mock/home/dir')
    async def test_TUI_make_path_absolute(self):
        from stig.commands.tui import AddTorrentsCmd
        with patch('os.path.exists', side_effect=lambda path: True):
            abspath = '/path/to/file.torrent'
            self.assertEqual(AddTorrentsCmd.make_path_absolute(abspath), '/path/to/file.torrent')
            cwdpath = './path/to/file.torrent'
            self.assertEqual(AddTorrentsCmd.make_path_absolute(cwdpath), os.path.join(os.environ['HOME'], 'path/to/file.torrent'))
            relpath = 'path/to/file.torrent'
            self.assertEqual(AddTorrentsCmd.make_path_absolute(relpath), os.path.join(os.environ['HOME'], 'path/to/file.torrent'))
            with patch.dict(os.environ):
                del os.environ['HOME']
                for path in (cwdpath, relpath):
                    self.assertEqual(AddTorrentsCmd.make_path_absolute(path), './path/to/file.torrent')
            homepath = '~/path/to/file.torrent'
            self.assertEqual(AddTorrentsCmd.make_path_absolute(homepath), os.path.join(os.environ['HOME'], 'path/to/file.torrent'))
            uri = 'magnet:?xt=urn:btih:e186f17ea5b29a694f7e4b89865baa65e9e51083'
            self.assertEqual(AddTorrentsCmd.make_path_absolute(uri), os.path.join(os.environ['HOME'], uri))
            url = 'http://some/url.torrent'
            self.assertEqual(AddTorrentsCmd.make_path_absolute(url), os.path.join(os.environ['HOME'], 'http:/some/url.torrent'))
        with patch('os.path.exists', side_effect=lambda path: False):
            abspath = '/path/to/file.torrent'
            self.assertEqual(AddTorrentsCmd.make_path_absolute(abspath), abspath)
            cwdpath = './path/to/file.torrent'
            self.assertEqual(AddTorrentsCmd.make_path_absolute(cwdpath), cwdpath)
            relpath = 'path/to/file.torrent'
            self.assertEqual(AddTorrentsCmd.make_path_absolute(relpath), relpath)
            with patch.dict(os.environ):
                del os.environ['HOME']
                for path in (cwdpath, relpath):
                    self.assertEqual(AddTorrentsCmd.make_path_absolute(path), path)
            homepath = '~/path/to/file.torrent'
            self.assertEqual(AddTorrentsCmd.make_path_absolute(homepath), homepath)
            uri = 'magnet:?xt=urn:btih:e186f17ea5b29a694f7e4b89865baa65e9e51083'
            self.assertEqual(AddTorrentsCmd.make_path_absolute(uri), uri)
            url = 'http://some/url.torrent'
            self.assertEqual(AddTorrentsCmd.make_path_absolute(url), url)

    @patch('stig.commands.cli.AddTorrentsCmd.make_path_absolute', side_effect=lambda path: path)
    async def test_success(self, mock_make_path_absolute):
        from stig.commands.cli import AddTorrentsCmd
        self.srvapi.torrent.response = Response(
            success=True,
            msgs=('Added Some Torrent',),
            torrent=MockTorrent(id=1, name='Some Torrent'))
        process = await self.execute(AddTorrentsCmd, 'some.torrent')
        self.srvapi.torrent.assert_called(1, 'add', ('some.torrent',), {'stopped': False, 'path': None})
        self.assertEqual(process.success, True)
        self.assert_stdout('add: Added Some Torrent')
        self.assert_stderr()

    @patch('stig.commands.cli.AddTorrentsCmd.make_path_absolute', side_effect=lambda path: path)
    async def test_failure(self, mock_make_path_absolute):
        from stig.commands.cli import AddTorrentsCmd
        self.srvapi.torrent.response = Response(
            success=False,
            errors=('Bogus torrent',),
            torrent=None)
        process = await self.execute(AddTorrentsCmd, 'some.torrent')
        self.srvapi.torrent.assert_called(1, 'add', ('some.torrent',), {'stopped': False, 'path': None})
        self.assertEqual(process.success, False)
        self.assert_stdout()
        self.assert_stderr('add: Bogus torrent')

    @patch('stig.commands.cli.AddTorrentsCmd.make_path_absolute', side_effect=lambda path: path)
    async def test_multiple_torrents(self, mock_make_path_absolute):
        from stig.commands.cli import AddTorrentsCmd
        self.srvapi.torrent.response = [
            Response(success=True,
                     msgs=['Added Some Torrent'],
                     torrent=MockTorrent(id=1, name='Some Torrent')),
            Response(success=False,
                     errors=('Something went wrong',),
                     torrent=None),
        ]
        process = await self.execute(AddTorrentsCmd, 'some.torrent', 'another.torrent')
        self.srvapi.torrent.assert_called(2, 'add',
                                          ('some.torrent',), {'stopped': False, 'path': None},
                                          ('another.torrent',), {'stopped': False, 'path': None})
        self.assertEqual(process.success, False)
        self.assert_stdout('add: Added Some Torrent')
        self.assert_stderr('add: Something went wrong')

    @patch('stig.commands.cli.AddTorrentsCmd.make_path_absolute', side_effect=lambda path: path)
    async def test_option_stopped(self, mock_make_path_absolute):
        from stig.commands.cli import AddTorrentsCmd
        self.srvapi.torrent.response = Response(
            success=True,
            msgs=('Added Some Torrent',),
            torrent=MockTorrent(id=1, name='Some Torrent'))
        process = await self.execute(AddTorrentsCmd, 'some.torrent', '--stopped')
        self.srvapi.torrent.assert_called(1, 'add', ('some.torrent',), {'stopped': True, 'path': None})
        self.assertEqual(process.success, True)
        self.assert_stdout('add: Added Some Torrent')
        self.assert_stderr()

    @patch('stig.completion.candidates.fs_path')
    async def test_CLI_completion_candidates_for_posargs(self, mock_fs_path):
        from stig.commands.cli import AddTorrentsCmd
        mock_fs_path.return_value = Candidates(('a', 'b', 'c'))
        await self.assert_completion_candidates(AddTorrentsCmd, Args(('add', 'foo'),
                                                                     curarg_index=1, curarg_curpos=3),
                                                exp_cands=('a', 'b', 'c'))
        mock_fs_path.assert_called_once_with('foo', glob='*.torrent', base='.')
        mock_fs_path.reset_mock()
        await self.assert_completion_candidates(AddTorrentsCmd, Args(('add', 'foo', 'bar'),
                                                                     curarg_index=2, curarg_curpos=3),
                                                exp_cands=('a', 'b', 'c'))
        mock_fs_path.assert_called_once_with('bar', glob='*.torrent', base='.')

    @patch('stig.completion.candidates.fs_path')
    @patch.dict(os.environ, HOME='/mock/home/dir')
    @asynctest.skip('https://github.com/Martiusweb/asynctest/issues/149')
    async def test_TUI_completion_candidates_for_posargs(self, mock_fs_path):
        from stig.commands.tui import AddTorrentsCmd
        mock_fs_path.return_value = Candidates(('a', 'b', 'c'))
        await self.assert_completion_candidates(AddTorrentsCmd, Args(('add', 'foo'),
                                                                     curarg_index=1, curarg_curpos=3),
                                                exp_cands=('a', 'b', 'c'))
        mock_fs_path.assert_called_once_with('foo', glob='*.torrent', base='/mock/home/dir')
        mock_fs_path.reset_mock()
        await self.assert_completion_candidates(AddTorrentsCmd, Args(('add', 'foo', 'bar'),
                                                                     curarg_index=2, curarg_curpos=3),
                                                exp_cands=('a', 'b', 'c'))
        mock_fs_path.assert_called_once_with('bar', glob='*.torrent', base='/mock/home/dir')

    @patch('stig.completion.candidates.fs_path')
    async def test_completion_candidates_for_path_option(self, mock_fs_path):
        from stig.commands.cli import AddTorrentsCmd
        mock_fs_path.return_value = Candidates(('a', 'b', 'c'))
        self.cfg['srv.path.complete'] = '/bar/baz'
        await self.assert_completion_candidates(AddTorrentsCmd, Args(('add', '--path', 'foo', 'x.torrent'),
                                                                     curarg_index=2, curarg_curpos=3),
                                                exp_cands=('a', 'b', 'c'))
        mock_fs_path.assert_called_once_with('foo', base='/bar/baz', directories_only=True)
        mock_fs_path.reset_mock()
        await self.assert_completion_candidates(AddTorrentsCmd, Args(('add', 'x.torrent', '--path', 'foo'),
                                                                     curarg_index=3, curarg_curpos=3),
                                                exp_cands=('a', 'b', 'c'))
        mock_fs_path.assert_called_once_with('foo', base='/bar/baz', directories_only=True)
        mock_fs_path.reset_mock()
        await self.assert_completion_candidates(AddTorrentsCmd, Args(('add', 'x.torrent', 'y.torrent', '--path', 'foo'),
                                                                     curarg_index=4, curarg_curpos=3),
                                                exp_cands=('a', 'b', 'c'))
        mock_fs_path.assert_called_once_with('foo', base='/bar/baz', directories_only=True)


class TestTorrentDetailsCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.patch('stig.objects',
                   srvapi=self.srvapi)
        self.mock_display_details = MagicMock()
        self.patch('stig.commands.cli.TorrentDetailsCmd',
                   select_torrents=mock_select_torrents,
                   display_details=self.mock_display_details)

    async def do(self, args, tlist, success_exp, msgs=(), errors=()):
        self.srvapi.torrent.response = Response(success=success_exp, torrents=tlist, errors=errors)

        process = await self.execute(TorrentDetailsCmd, *args)
        self.assertEqual(process.success, success_exp)

        self.assert_stdout()
        self.assert_stderr(*tuple('^%s: %s$' % (TorrentDetailsCmd.name, err) for err in errors))

        self.srvapi.torrent.assert_called(1, 'torrents', (process.mock_tfilter,), {'keys': ('id', 'name')})

    async def test_no_match(self):
        tlist = ()
        await self.do(['mock filter'], tlist=tlist, success_exp=False, errors=('Mock error',))
        self.mock_display_details.assert_not_called()

    async def test_single_match(self):
        tlist = (MockTorrent(id=1, name='Torrent A', seeds='50'),)
        await self.do(['mock filter'], tlist=tlist, success_exp=True, errors=())
        self.mock_display_details.assert_called_once_with(1)

    async def test_multiple_matches_are_sorted_by_name(self):
        tlist = (MockTorrent(id=1, name='Torrent B', seeds='51'),
                 MockTorrent(id=2, name='Torrent A', seeds='50'))
        await self.do(['mock filter'], tlist=tlist, success_exp=True, errors=())
        self.mock_display_details.assert_called_once_with(2)

    @patch('stig.completion.candidates.torrent_filter')
    async def test_completion_candidates_for_posargs(self, mock_torrent_filter):
        mock_torrent_filter.return_value = Candidates(('a', 'b', 'c'))
        await self.assert_completion_candidates(TorrentDetailsCmd, Args(('details', 'foo'), curarg_index=1),
                                                exp_cands=('a', 'b', 'c'))
        mock_torrent_filter.assert_called_once_with('foo')
        mock_torrent_filter.reset_mock()
        await self.assert_completion_candidates(TorrentDetailsCmd, Args(('details', 'foo', 'bar'), curarg_index=2),
                                                exp_cands=None)
        mock_torrent_filter.assert_not_called()


class TestListTorrentsCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.patch('stig.objects',
                   srvapi=self.srvapi,
                   cfg=self.cfg)
        self.cfg['sort.torrents'] = ('name',)
        self.cfg['columns.torrents'] = ('name',)

        self.patch('stig.commands.cli.ListTorrentsCmd',
                   select_torrents=mock_select_torrents,
                   get_torrent_sorter=mock_get_torrent_sorter,
                   get_torrent_columns=lambda self, columns, interface=None: ('name',))

        from stig.commands.cli import torrent
        torrent.TERMSIZE = SimpleNamespace(columns=None, lines=None)

    async def do(self, args, errors):
        tlist = (
            MockTorrent(id=1, name='Some Torrent'),
            MockTorrent(id=2, name='Another Torrent')
        )
        self.srvapi.torrent.response = Response(success=bool(errors), errors=(), msgs=(), torrents=tlist)

        process = await self.execute(ListTorrentsCmd, *args)
        expected_success = not errors
        self.assertEqual(process.success, expected_success)
        if errors:
            self.assert_stdout()
            self.assert_stderr(*errors)
        else:
            self.assert_stdout('Some Torrent',
                               'Another Torrent')
            self.assert_stderr()
            keys_exp = set(process.mock_tsorter.needed_keys +
                           process.mock_tfilter.needed_keys +
                           ('name',))  # columns
            self.srvapi.torrent.assert_called(1, 'torrents', (process.mock_tfilter,),
                                              {'keys': keys_exp})
            self.assertEqual(process.mock_tsorter.applied, tlist)

    async def test_filter(self):
        await self.do(['active'], errors=())

    async def test_multiple_filters(self):
        await self.do(['active', 'downloading'], errors=())

    async def test_sorts(self):
        await self.do(['--sort', 'name,size'], errors=())

    async def test_sort_short(self):
        await self.do(['-s', 'name,size'], errors=())

    async def test_sort_and_filter(self):
        await self.do(['-s', 'name,size', 'downloading', 'uploading'], errors=())

    async def test_invalid_filter(self):
        def bad_select_torrents(self, *args, **kwargs):
            raise ValueError('Nope!')
        ListTorrentsCmd.select_torrents = bad_select_torrents
        await self.do(['foo'], errors=('%s: Nope!' % ListTorrentsCmd.name,))

    async def test_invalid_sort(self):
        def bad_get_torrent_sorter(self, *args, **kwargs):
            raise ValueError('Nope!')
        ListTorrentsCmd.get_torrent_sorter = bad_get_torrent_sorter
        await self.do(['-s', 'foo'], errors=('%s: Nope!' % ListTorrentsCmd.name,))

    @patch('stig.completion.candidates.torrent_filter')
    async def test_completion_candidates_for_posargs(self, mock_torrent_filter):
        mock_torrent_filter.return_value = Candidates(('a', 'b', 'c'))
        await self.assert_completion_candidates(ListTorrentsCmd, Args(('ls', 'foo'), curarg_index=1),
                                                exp_cands=('a', 'b', 'c'))
        mock_torrent_filter.assert_called_once_with('foo')
        mock_torrent_filter.reset_mock()
        await self.assert_completion_candidates(ListTorrentsCmd, Args(('ls', 'foo', 'bar'), curarg_index=2),
                                                exp_cands=('a', 'b', 'c'))
        mock_torrent_filter.assert_called_once_with('bar')

    @patch('stig.completion.candidates.sort_orders')
    async def test_completion_candidates_for_sort_option(self, mock_sort_orders):
        mock_sort_orders.return_value = Candidates(('a', 'b', 'c'), curarg_seps=(',',))
        await self.assert_completion_candidates(ListTorrentsCmd, Args(('ls', '--sort', 'foo'), curarg_index=2),
                                                exp_cands=('a', 'b', 'c'), exp_curarg_seps=(',',))
        await self.assert_completion_candidates(ListTorrentsCmd, Args(('ls', '--sort', 'foo', 'bar'), curarg_index=2),
                                                exp_cands=('a', 'b', 'c'), exp_curarg_seps=(',',))
        await self.assert_completion_candidates(ListTorrentsCmd, Args(('ls', 'bar', '--sort', 'foo'), curarg_index=3),
                                                exp_cands=('a', 'b', 'c'), exp_curarg_seps=(',',))
        self.assertEqual(mock_sort_orders.call_args_list, [call('TorrentSorter'),
                                                           call('TorrentSorter'),
                                                           call('TorrentSorter')])

    async def test_completion_candidates_for_columns_option(self):
        self.cfg['columns.torrents'] = SimpleNamespace(options=('a', 'b', 'c'), sep=' , ', aliases_inverse={})
        await self.assert_completion_candidates(ListTorrentsCmd, Args(('ls', '--columns', 'foo'), curarg_index=2),
                                                exp_cands=('a', 'b', 'c'), exp_curarg_seps=(',',))
        await self.assert_completion_candidates(ListTorrentsCmd, Args(('ls', '--columns', 'foo', 'bar'), curarg_index=2),
                                                exp_cands=('a', 'b', 'c'), exp_curarg_seps=(',',))
        await self.assert_completion_candidates(ListTorrentsCmd, Args(('ls', 'bar', '--columns', 'foo'), curarg_index=3),
                                                exp_cands=('a', 'b', 'c'), exp_curarg_seps=(',',))


class TestTorrentMagnetURICmd(CommandTestCase):
    @patch('stig.completion.candidates.torrent_filter')
    async def test_completion_candidates_for_posargs(self, mock_torrent_filter):
        from stig.commands.cli import TorrentMagnetURICmd
        mock_torrent_filter.return_value = Candidates(('a', 'b', 'c'))
        await self.assert_completion_candidates(TorrentMagnetURICmd, Args(('magnet', 'foo'), curarg_index=1),
                                                exp_cands=('a', 'b', 'c'))
        await self.assert_completion_candidates(TorrentMagnetURICmd, Args(('magnet', 'foo', 'bar'), curarg_index=2),
                                                exp_cands=None)


class TestMoveTorrentsCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.patch('stig.objects',
                   cfg=self.cfg)

    @patch('stig.completion.candidates.torrent_filter')
    @patch('stig.completion.candidates.fs_path')
    async def test_CLI_completion_candidates_for_posargs_with_first_arg(self, mock_fs_path, mock_torrent_filter):
        from stig.commands.cli import MoveTorrentsCmd
        mock_torrent_filter.return_value = (Candidates(('a', 'b', 'c')),)

        cands = await MoveTorrentsCmd.completion_candidates(Args(('move', 'foo', 'bar'), curarg_index=1))
        mock_torrent_filter.assert_called_once_with('foo')
        mock_fs_path.assert_not_called()
        self.assertEqual(cands, (Candidates(('a', 'b', 'c')),))

    @patch('stig.completion.candidates.torrent_filter')
    @patch('stig.completion.candidates.fs_path')
    async def test_CLI_completion_candidates_for_posargs_with_second_arg(self, mock_fs_path, mock_torrent_filter):
        from stig.commands.cli import MoveTorrentsCmd
        mock_torrent_filter.return_value = (Candidates(('a', 'b', 'c')),)
        mock_fs_path.return_value = Candidates(('d', 'e', 'f'))
        self.cfg['srv.path.complete'] = '/some/path/'

        cands = await MoveTorrentsCmd.completion_candidates(Args(('move', 'foo', 'bar'), curarg_index=2, curarg_curpos=3))
        mock_torrent_filter.assert_not_called()
        mock_fs_path.assert_called_once_with('bar', base=self.cfg['srv.path.complete'], directories_only=True)
        self.assertEqual(cands, Candidates(('d', 'e', 'f')))

    @patch('stig.completion.candidates.torrent_filter')
    @patch('stig.completion.candidates.fs_path')
    async def test_TUI_completion_candidates_for_posargs_with_one_arg(self, mock_fs_path, mock_torrent_filter):
        from stig.commands.tui import MoveTorrentsCmd
        mock_torrent_filter.return_value = (Candidates(('a', 'b', 'c')),)
        mock_fs_path.return_value = Candidates(('d', 'e', 'f'))
        self.cfg['srv.path.complete'] = '/some/path/'

        cands = await MoveTorrentsCmd.completion_candidates(Args(('move', 'foo'), curarg_index=1, curarg_curpos=3))
        mock_torrent_filter.assert_called_once_with('foo')
        mock_fs_path.assert_called_once_with('foo', base=self.cfg['srv.path.complete'],
                                             directories_only=True, expand_home_directory=False)
        self.assertEqual(cands, (Candidates(('d', 'e', 'f')),
                                 Candidates(('a', 'b', 'c'))))

    @patch('stig.completion.candidates.torrent_filter')
    @patch('stig.completion.candidates.fs_path')
    async def test_TUI_completion_candidates_for_posargs_with_two_args_on_first_arg(self, mock_fs_path, mock_torrent_filter):
        from stig.commands.tui import MoveTorrentsCmd
        mock_torrent_filter.return_value = (Candidates(('a', 'b', 'c')),)

        cands = await MoveTorrentsCmd.completion_candidates(Args(('move', 'foo', 'bar'), curarg_index=1))
        mock_torrent_filter.assert_called_once_with('foo')
        mock_fs_path.assert_not_called()
        self.assertEqual(cands, (Candidates(('a', 'b', 'c')),))

    @patch('stig.completion.candidates.torrent_filter')
    @patch('stig.completion.candidates.fs_path')
    async def test_TUI_completion_candidates_for_posargs_with_two_args_on_second_arg(self, mock_fs_path, mock_torrent_filter):
        from stig.commands.tui import MoveTorrentsCmd
        mock_fs_path.return_value = Candidates(('d', 'e', 'f'))
        self.cfg['srv.path.complete'] = '/some/path/'

        cands = await MoveTorrentsCmd.completion_candidates(Args(('move', 'foo', 'bar'), curarg_index=2, curarg_curpos=3))
        mock_torrent_filter.assert_not_called()
        mock_fs_path.assert_called_once_with('bar', base=self.cfg['srv.path.complete'],
                                             directories_only=True, expand_home_directory=False)

        self.assertEqual(cands, Candidates(('d', 'e', 'f')))


class TestRemoveTorrentsCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.patch('stig.objects',
                   srvapi=self.srvapi,
                   cfg=self.cfg)
        self.cfg['remove.max-hits'] = 10
        self.patch('stig.commands.cli.RemoveTorrentsCmd',
                   select_torrents=mock_select_torrents)

    async def do(self, args, tlist, success_exp, msgs=(), errors=(), delete=False, remove_called=True):
        self.srvapi.torrent.response = Response(success=success_exp, torrents=tlist, msgs=msgs, errors=errors)

        process = await self.execute(RemoveTorrentsCmd, *args)
        self.assertEqual(process.success, success_exp)

        msgs_exp = tuple('^%s: %s$' % (RemoveTorrentsCmd.name, msg) for msg in msgs)
        errors_exp = tuple('^%s: %s$' % (RemoveTorrentsCmd.name, err) for err in errors)
        self.assert_stdout(*msgs_exp)
        self.assert_stderr(*errors_exp)

        if remove_called:
            self.srvapi.torrent.assert_called(1, 'remove', (process.mock_tfilter,), {'delete': delete})
        else:
            self.srvapi.torrent.assert_called(0, 'remove')

    async def test_remove(self):
        tlist = (MockTorrent(id=1, name='Some Torrent', seeds='51'),)
        await self.do(['seeds>50'], tlist=tlist, delete=False, success_exp=True,
                      msgs=('Removed Some Torrent',))

    async def test_delete_files(self):
        tlist = (MockTorrent(id=1, name='Some Torrent', seeds='51'),)
        await self.do(['--delete-files', 'seeds>50'], tlist=tlist, delete=True, success_exp=True,
                      msgs=('Removed Some Torrent',))

    async def test_delete_files_short(self):
        tlist = (MockTorrent(id=1, name='Some Torrent', seeds='51'),)
        await self.do(['-d', 'seeds>50'], tlist=tlist, delete=True, success_exp=True,
                      msgs=('Removed Some Torrent',))

    async def test_no_torrents_found(self):
        await self.do(['seeds>5000'], delete=False, tlist=(), success_exp=True,
                      errors=('remove: No matching torrents: seeds>5k',))

    async def test_max_hits_exceeded_and_user_says_yes(self):
        tlist = (MockTorrent(id=1, name='Torrent1', seeds='51'),
                 MockTorrent(id=2, name='Torrent2', seeds='52'),
                 MockTorrent(id=3, name='Torrent3', seeds='53'))
        from stig import objects
        objects.cfg['remove.max-hits'] = 2
        RemoveTorrentsCmd.show_list_of_hits = CoroutineMock()

        async def mock_ask_yes_no(self_, *args, yes, no, **kwargs):
            await yes() ; return True  # noqa: E702

        RemoveTorrentsCmd.ask_yes_no = mock_ask_yes_no

        await self.do(['all'], tlist=tlist, remove_called=True, success_exp=True,
                      msgs=('Removed Torrent1',
                            'Removed Torrent2',
                            'Removed Torrent3'))
        self.assertTrue(RemoveTorrentsCmd.show_list_of_hits.called)

    async def test_max_hits_exceeded_and_user_says_no(self):
        tlist = (MockTorrent(id=1, name='Torrent1', seeds='51'),
                 MockTorrent(id=2, name='Torrent2', seeds='52'),
                 MockTorrent(id=3, name='Torrent3', seeds='53'))
        self.cfg['remove.max-hits'] = 2
        RemoveTorrentsCmd.show_list_of_hits = CoroutineMock()

        async def mock_ask_yes_no(self_, *args, yes, no, **kwargs):
            await no() ; return False  # noqa: E702

        RemoveTorrentsCmd.ask_yes_no = mock_ask_yes_no

        await self.do(['seeds>50'], tlist=tlist, remove_called=False, success_exp=False,
                      errors=('Keeping .*? torrents: Too many hits .*',))
        self.assertTrue(RemoveTorrentsCmd.show_list_of_hits.called)

    async def test_max_hits_negative(self):
        tlist = (MockTorrent(id=1, name='Torrent1', seeds='51'),
                 MockTorrent(id=2, name='Torrent2', seeds='52'),
                 MockTorrent(id=3, name='Torrent3', seeds='53'))
        self.cfg['remove.max-hits'] = -1
        RemoveTorrentsCmd.show_list_of_hits = CoroutineMock()
        await self.do(['all'], tlist=tlist, remove_called=True, success_exp=True,
                      msgs=('Removed Torrent1', 'Removed Torrent2', 'Removed Torrent3'))
        self.assertFalse(RemoveTorrentsCmd.show_list_of_hits.called)

    async def test_force_option(self):
        tlist = (MockTorrent(id=1, name='Torrent1', seeds='51'),
                 MockTorrent(id=2, name='Torrent2', seeds='52'),
                 MockTorrent(id=3, name='Torrent3', seeds='53'))
        self.cfg['remove.max-hits'] = 2
        RemoveTorrentsCmd.show_list_of_hits = CoroutineMock()
        RemoveTorrentsCmd.ask_yes_no = CoroutineMock()
        await self.do(['all', '--force'], tlist=tlist, remove_called=True, success_exp=True,
                      msgs=('Removed Torrent1', 'Removed Torrent2', 'Removed Torrent3'))
        self.assertFalse(RemoveTorrentsCmd.show_list_of_hits.called)
        self.assertFalse(RemoveTorrentsCmd.ask_yes_no.called)

    @patch('stig.completion.candidates.torrent_filter')
    @patch('stig.completion.candidates.fs_path')
    async def test_completion_candidates_for_posargs(self, mock_fs_path, mock_torrent_filter):
        mock_torrent_filter.return_value = Candidates(('a', 'b', 'c'))
        cands = await RemoveTorrentsCmd.completion_candidates(Args(('remove', 'foo'), curarg_index=1))
        mock_torrent_filter.assert_called_once_with('foo')
        self.assertEqual(cands, Candidates(('a', 'b', 'c')))

        mock_torrent_filter.reset_mock()
        mock_torrent_filter.return_value = Candidates(('a', 'b', 'c'))
        cands = await RemoveTorrentsCmd.completion_candidates(Args(('remove', 'foo', 'bar'), curarg_index=2))
        mock_torrent_filter.assert_called_once_with('bar')
        self.assertEqual(cands, Candidates(('a', 'b', 'c')))


class TestRenameCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.mock_get_relative_path_from_focused = MagicMock()
        self.mock_select_torrents = MagicMock()
        self.mock_srvapi = MagicMock()
        self.mock_srvapi.torrent.torrents = CoroutineMock()
        self.mock_srvapi.torrent.rename = CoroutineMock()
        self.mock_srvapi.interval = 10
        self.patch('stig.objects',
                   srvapi=self.mock_srvapi)
        self.patch('stig.commands.cli.RenameCmd',
                   select_torrents=self.mock_select_torrents,
                   get_relative_path_from_focused=self.mock_get_relative_path_from_focused)
        self.patch('stig.commands.tui.RenameCmd',
                   select_torrents=self.mock_select_torrents,
                   get_relative_path_from_focused=self.mock_get_relative_path_from_focused)

    async def test_discovering_focused_torrent(self):
        from stig.commands.cli import RenameCmd
        self.mock_get_relative_path_from_focused.return_value = None
        self.mock_select_torrents.return_value = 'mock filter'
        self.mock_srvapi.torrent.torrents.return_value = Response(
            success=True,
            torrents=(MockTorrent(id=1234, name='Some Torrent'),))

        info_cb, err_cb = MagicMock(), MagicMock()
        process = RenameCmd(['New Name'], info_handler=info_cb, error_handler=err_cb)
        await process.wait_async()
        self.assertEqual(process.success, True)
        info_cb.assert_not_called()
        err_cb.assert_not_called()

        self.mock_get_relative_path_from_focused.assert_called_once_with(unique=False)
        self.mock_select_torrents.assert_called_once_with(None, allow_no_filter=False, discover_torrent=True)
        self.mock_srvapi.torrent.torrents.assert_called_once_with('mock filter', keys=('id',))
        self.mock_srvapi.torrent.rename.assert_called_once_with(1234, path=None, new_name='New Name')

    async def test_discovering_focused_file(self):
        from stig.commands.cli import RenameCmd
        self.mock_get_relative_path_from_focused.return_value = 'id=1234/mock/path/to/file'
        self.mock_select_torrents.return_value = 'mock filter'
        self.mock_srvapi.torrent.torrents.return_value = Response(
            success=True,
            torrents=(MockTorrent(id=1234, name='Some Torrent'),))

        info_cb, err_cb = MagicMock(), MagicMock()
        process = RenameCmd(['file2'], info_handler=info_cb, error_handler=err_cb)
        await process.wait_async()
        self.assertEqual(process.success, True)
        info_cb.assert_not_called()
        err_cb.assert_not_called()

        self.mock_get_relative_path_from_focused.assert_called_once_with(unique=False)
        self.mock_select_torrents.assert_called_once_with('id=1234', allow_no_filter=False, discover_torrent=True)
        self.mock_srvapi.torrent.torrents.assert_called_once_with('mock filter', keys=('id',))
        self.mock_srvapi.torrent.rename.assert_called_once_with(1234, path='mock/path/to/file', new_name='file2')

    async def test_specifying_torrent(self):
        from stig.commands.cli import RenameCmd
        self.mock_select_torrents.return_value = 'mock filter'
        self.mock_srvapi.torrent.torrents.return_value = Response(
            success=True,
            torrents=(MockTorrent(id=1234, name='Some Torrent'),))

        info_cb, err_cb = MagicMock(), MagicMock()
        process = RenameCmd(['id=1234', 'Renamed Torrent'], info_handler=info_cb, error_handler=err_cb)
        await process.wait_async()
        self.assertEqual(process.success, True)
        info_cb.assert_not_called()
        err_cb.assert_not_called()

        self.mock_get_relative_path_from_focused.assert_not_called()
        self.mock_select_torrents.assert_called_once_with('id=1234', allow_no_filter=False, discover_torrent=True)
        self.mock_srvapi.torrent.torrents.assert_called_once_with('mock filter', keys=('id',))
        self.mock_srvapi.torrent.rename.assert_called_once_with(1234, path=None, new_name='Renamed Torrent')

    async def test_specifying_file(self):
        from stig.commands.cli import RenameCmd
        self.mock_select_torrents.return_value = 'mock filter'
        self.mock_srvapi.torrent.torrents.return_value = Response(
            success=True,
            torrents=(MockTorrent(id=1234, name='Some Torrent'),))

        info_cb, err_cb = MagicMock(), MagicMock()
        process = RenameCmd(['id=1234/mock/path/to/file', 'file2'], info_handler=info_cb, error_handler=err_cb)
        await process.wait_async()
        self.assertEqual(process.success, True)
        info_cb.assert_not_called()
        err_cb.assert_not_called()

        self.mock_get_relative_path_from_focused.assert_not_called()
        self.mock_select_torrents.assert_called_once_with('id=1234', allow_no_filter=False, discover_torrent=True)
        self.mock_srvapi.torrent.torrents.assert_called_once_with('mock filter', keys=('id',))
        self.mock_srvapi.torrent.rename.assert_called_once_with(1234, path='mock/path/to/file', new_name='file2')

    async def test_torrent_filter_must_match_one_torrent_when_renaming_torrents(self):
        from stig.commands.cli import RenameCmd
        self.mock_select_torrents.return_value = 'mock filter'
        self.mock_srvapi.torrent.torrents.return_value = Response(
            success=True,
            torrents=(MockTorrent(id=1234, name='Some Torrent'),
                      MockTorrent(id=1235, name='Some Torrent')))

        info_cb, err_cb = MagicMock(), MagicMock()
        process = RenameCmd(['Some Torrent', 'Renamed Torrent'], info_handler=info_cb, error_handler=err_cb)
        await process.wait_async()
        self.assertEqual(process.success, False)
        info_cb.assert_not_called()
        err_cb.assert_called_once_with('rename: mock filter matches more than one torrent')

        self.mock_get_relative_path_from_focused.assert_not_called()
        self.mock_select_torrents.assert_called_once_with('Some Torrent', allow_no_filter=False, discover_torrent=True)
        self.mock_srvapi.torrent.torrents.assert_called_once_with('mock filter', keys=('id',))
        self.mock_srvapi.torrent.rename.assert_not_called()

    async def test_renaming_files_of_multiple_torrents_succeeds(self):
        from stig.commands.cli import RenameCmd
        self.mock_select_torrents.return_value = 'mock filter'
        self.mock_srvapi.torrent.torrents.return_value = Response(
            success=True,
            torrents=(MockTorrent(id=1234, name='Some Torrent'),
                      MockTorrent(id=1235, name='Some Torrent')))

        info_cb, err_cb = MagicMock(), MagicMock()
        process = RenameCmd(['Some Torrent/mock/path/to/file', 'file2'], info_handler=info_cb, error_handler=err_cb)
        await process.wait_async()
        self.assertEqual(process.success, True)
        info_cb.assert_not_called()
        err_cb.assert_not_called()

        self.mock_get_relative_path_from_focused.assert_not_called()
        self.mock_select_torrents.assert_called_once_with('Some Torrent', allow_no_filter=False, discover_torrent=True)
        self.mock_srvapi.torrent.torrents.assert_called_once_with('mock filter', keys=('id',))
        self.assertEqual(self.mock_srvapi.torrent.rename.call_args_list,
                         [call(1234, path='mock/path/to/file', new_name='file2'),
                          call(1235, path='mock/path/to/file', new_name='file2')])

    async def test_using_unique_option_in_TUI_with_single_match(self):
        from stig.commands.tui import RenameCmd
        self.mock_get_relative_path_from_focused.return_value = 'id=1235/focused/file'
        self.mock_select_torrents.return_value = 'mock filter'
        self.mock_srvapi.torrent.torrents.return_value = Response(
            success=True,
            torrents=(MockTorrent(id=1235, name='Some Torrent'),))

        info_cb, err_cb = MagicMock(), MagicMock()
        process = RenameCmd(['--unique', 'file2'],
                            info_handler=info_cb, error_handler=err_cb)
        await process.wait_async()
        self.assertEqual(process.success, True)
        info_cb.assert_not_called()
        err_cb.assert_not_called()

        self.mock_get_relative_path_from_focused.assert_called_once_with(unique=True)
        self.mock_select_torrents.assert_called_once_with('id=1235', allow_no_filter=False, discover_torrent=True)
        self.mock_srvapi.torrent.torrents.assert_called_once_with('mock filter', keys=('id',))
        self.assertEqual(self.mock_srvapi.torrent.rename.call_args_list,
                         [call(1235, path='focused/file', new_name='file2')])

    async def test_using_unique_option_in_TUI_with_multiple_matches(self):
        from stig.commands.tui import RenameCmd
        self.mock_get_relative_path_from_focused.return_value = 'Some Torrent/focused/file'
        self.mock_select_torrents.return_value = 'mock filter'
        self.mock_srvapi.torrent.torrents.return_value = Response(
            success=True,
            torrents=(MockTorrent(id=1234, name='Some Torrent'),
                      MockTorrent(id=1235, name='Some Torrent')))

        info_cb, err_cb = MagicMock(), MagicMock()
        process = RenameCmd(['--unique', 'file2'],
                            info_handler=info_cb, error_handler=err_cb)
        await process.wait_async()
        self.assertEqual(process.success, False)
        info_cb.assert_not_called()
        err_cb.assert_called_once_with('rename: mock filter matches more than one torrent')

        self.mock_get_relative_path_from_focused.assert_called_once_with(unique=True)
        self.mock_select_torrents.assert_called_once_with('Some Torrent', allow_no_filter=False, discover_torrent=True)
        self.mock_srvapi.torrent.torrents.assert_called_once_with('mock filter', keys=('id',))
        self.assertEqual(self.mock_srvapi.torrent.rename.call_args_list, [])

    async def test_using_unique_option_in_CLI_with_single_match(self):
        from stig.commands.cli import RenameCmd
        self.mock_select_torrents.return_value = 'mock filter'
        self.mock_srvapi.torrent.torrents.return_value = Response(
            success=True,
            torrents=(MockTorrent(id=1235, name='Some Torrent'),))

        info_cb, err_cb = MagicMock(), MagicMock()
        process = RenameCmd(['--unique', 'id=1235/path/to/file', 'file2'],
                            info_handler=info_cb, error_handler=err_cb)
        await process.wait_async()
        self.assertEqual(process.success, True)
        info_cb.assert_not_called()
        err_cb.assert_not_called()

        self.mock_get_relative_path_from_focused.assert_not_called()
        self.mock_select_torrents.assert_called_once_with('id=1235', allow_no_filter=False, discover_torrent=True)
        self.mock_srvapi.torrent.torrents.assert_called_once_with('mock filter', keys=('id',))
        self.assertEqual(self.mock_srvapi.torrent.rename.call_args_list,
                         [call(1235, path='path/to/file', new_name='file2')])

    async def test_using_unique_option_in_CLI_with_multiple_matches(self):
        from stig.commands.cli import RenameCmd
        self.mock_select_torrents.return_value = 'mock filter'
        self.mock_srvapi.torrent.torrents.return_value = Response(
            success=True,
            torrents=(MockTorrent(id=1234, name='Some Torrent'),
                      MockTorrent(id=1235, name='Some Torrent')))

        info_cb, err_cb = MagicMock(), MagicMock()
        process = RenameCmd(['--unique', 'Some Torrent/path/to/file', 'file2'],
                            info_handler=info_cb, error_handler=err_cb)
        await process.wait_async()
        self.assertEqual(process.success, False)
        info_cb.assert_not_called()
        err_cb.assert_called_once_with('rename: mock filter matches more than one torrent')

        self.mock_get_relative_path_from_focused.assert_not_called()
        self.mock_select_torrents.assert_called_once_with('Some Torrent', allow_no_filter=False, discover_torrent=True)
        self.mock_srvapi.torrent.torrents.assert_called_once_with('mock filter', keys=('id',))
        self.assertEqual(self.mock_srvapi.torrent.rename.call_args_list, [])

    async def test_autodiscovery_of_TORRENT_argument_fails(self):
        from stig.commands.cli import RenameCmd
        self.mock_get_relative_path_from_focused.return_value = None
        self.mock_select_torrents.side_effect = ValueError('No torrent given')

        info_cb, err_cb = MagicMock(), MagicMock()
        process = RenameCmd(['New Name'], info_handler=info_cb, error_handler=err_cb)
        await process.wait_async()
        self.assertEqual(process.success, False)
        info_cb.assert_not_called()
        err_cb.assert_called_once_with('rename: No torrent given')

        self.mock_get_relative_path_from_focused.assert_called_once_with(unique=False)
        self.mock_select_torrents.assert_called_once_with(None, allow_no_filter=False, discover_torrent=True)
        self.mock_srvapi.torrent.torrents.assert_not_called()
        self.mock_srvapi.torrent.rename.assert_not_called()

    @patch('stig.completion.candidates.torrent_path')
    async def test_CLI_completion_candidates__options_are_ignored(self, mock_torrent_path):
        from stig.commands.cli import RenameCmd
        mock_torrent_path.return_value = 'mock candidates'
        for args in (Args(('rename', '-a', 'foo'), curarg_index=2, curarg_curpos=0),
                     Args(('rename', '-a', '-b', 'foo'), curarg_index=3, curarg_curpos=0),
                     Args(('rename', '-a', '-b', '--cee', 'foo'), curarg_index=4, curarg_curpos=0)):
            cands = await RenameCmd.completion_candidates(args)
            mock_torrent_path.assert_called_once_with('foo', only='any')
            self.assertEqual(cands, 'mock candidates')
            mock_torrent_path.reset_mock()

    @patch('stig.completion.candidates.torrent_path')
    async def test_CLI_completion_candidates__first_arg(self, mock_torrent_path):
        from stig.commands.cli import RenameCmd
        mock_torrent_path.return_value = 'mock candidates'
        cands = await RenameCmd.completion_candidates(Args(('rename', 'foo', 'bar', 'baz'), curarg_index=1))
        mock_torrent_path.assert_called_once_with('foo', only='any')
        self.assertEqual(cands, 'mock candidates')

    @patch('stig.completion.candidates.torrent_path')
    @patch('stig.completion.candidates.torrent_filter')
    async def test_CLI_completion_candidates__second_arg__first_arg_does_not_contain_path_separator(
            self, mock_torrent_filter, mock_torrent_path):
        from stig.commands.cli import RenameCmd
        mock_torrent_filter.return_value = 'mock torrent_filter() candidates'
        cands = await RenameCmd.completion_candidates(Args(('rename', 'foo', 'bar', 'baz'), curarg_index=2))
        mock_torrent_path.assert_not_called()
        mock_torrent_filter.assert_called_once_with('bar', filter_names=False)
        self.assertEqual(cands, 'mock torrent_filter() candidates')

    @patch('stig.completion.candidates.torrent_path')
    @patch('stig.completion.candidates.torrent_filter')
    async def test_CLI_completion_candidates__second_arg__first_arg_contains_path_separator(
            self, mock_torrent_filter, mock_torrent_path):
        from stig.commands.cli import RenameCmd
        mock_torrent_path.return_value = 'mock torrent_path() candidates'
        cands = await RenameCmd.completion_candidates(Args(('rename', 'foo/some/path', 'bar', 'baz'), curarg_index=2))
        mock_torrent_path.assert_called_once_with('foo/some/path', only='auto')
        mock_torrent_filter.assert_not_called()
        self.assertEqual(cands, 'mock torrent_path() candidates')

    @patch('stig.completion.candidates.torrent_path')
    @patch('stig.completion.candidates.torrent_filter')
    async def test_CLI_completion_candidates__third_arg(
            self, mock_torrent_filter, mock_torrent_path):
        from stig.commands.cli import RenameCmd
        cands = await RenameCmd.completion_candidates(Args(('rename', 'foo/some/path', 'bar', 'baz'), curarg_index=3))
        mock_torrent_path.assert_not_called()
        mock_torrent_filter.assert_not_called()
        self.assertFalse(cands)

    @patch('stig.completion.candidates.torrent_path')
    @patch('stig.commands.tui.torrent.RenameCmd._get_focused_item_source')
    async def test_TUI_completion_candidates__options_are_ignored(
            self, mock_get_focused_item_source, mock_torrent_path):
        from stig.commands.tui import RenameCmd
        mock_torrent_path.return_value = 'mock candidates'
        mock_get_focused_item_source.return_value = None
        for args in (Args(('rename', '-a', 'foo'), curarg_index=2, curarg_curpos=0),
                     Args(('rename', '-a', '-b', 'foo'), curarg_index=3, curarg_curpos=0),
                     Args(('rename', '-a', '-b', '--cee', 'foo'), curarg_index=4, curarg_curpos=0)):
            cands = await RenameCmd.completion_candidates(args)
            from logging import getLogger
            log = getLogger()
            log.debug(mock_torrent_path.call_args_list)
            mock_torrent_path.assert_called_once_with('foo', only='any')
            mock_get_focused_item_source.assert_called_once_with()
            self.assertEqual(cands, 'mock candidates')
            mock_torrent_path.reset_mock()
            mock_get_focused_item_source.reset_mock()

    @patch('stig.completion.candidates.torrent_path')
    @patch('stig.commands.tui.torrent.RenameCmd._get_focused_item_source')
    async def test_TUI_completion_candidates__first_arg__getting_source_from_focused_item(
            self, mock_get_focused_item_source, mock_torrent_path):
        from stig.commands.tui import RenameCmd
        mock_get_focused_item_source.return_value = 'mock torrent source'
        mock_torrent_path.side_effect = lambda arg, **_: 'mock torrent_path(%r) candidates' % (str(arg),)
        cands = await RenameCmd.completion_candidates(Args(('rename', 'foo'), curarg_index=1, curarg_curpos=2))
        mock_get_focused_item_source.assert_called_once_with()
        self.assertEqual(mock_torrent_path.call_args_list, [call(Arg('mock torrent source', curpos=19), only='auto'),
                                                            call(Arg('foo', curpos=2), only='any')])
        self.assertEqual(cands, ("mock torrent_path('mock torrent source') candidates",
                                 "mock torrent_path('foo') candidates"))

    @patch('stig.completion.candidates.torrent_path')
    @patch('stig.commands.tui.torrent.RenameCmd._get_focused_item_source')
    async def test_TUI_completion_candidates__first_arg__unable_to_get_source_from_focused_item(
            self, mock_get_focused_item_source, mock_torrent_path):
        from stig.commands.tui import RenameCmd
        mock_get_focused_item_source.return_value = None
        mock_torrent_path.side_effect = lambda arg, **_: 'mock torrent_path(%r) candidates' % (str(arg),)
        cands = await RenameCmd.completion_candidates(Args(('rename', 'foo'), curarg_index=1, curarg_curpos=2))
        mock_get_focused_item_source.assert_called_once_with()
        self.assertEqual(mock_torrent_path.call_args_list, [call(Arg('foo', curpos=2), only='any')])
        self.assertEqual(cands, "mock torrent_path('foo') candidates")


class TestStartTorrentsCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.patch('stig.objects',
                   srvapi=self.srvapi)
        self.patch('stig.commands.cli.StartTorrentsCmd',
                   select_torrents=mock_select_torrents)

    async def do(self, args, success_exp, msgs=(), errors=(), force=False, toggle=False):
        self.srvapi.torrent.response = Response(success=success_exp, msgs=msgs, errors=errors)

        process = await self.execute(StartTorrentsCmd, *args)
        self.assertEqual(process.success, success_exp)

        msgs_exp = tuple('^%s: %s$' % (StartTorrentsCmd.name, msg) for msg in msgs)
        errors_exp = tuple('^%s: %s$' % (StartTorrentsCmd.name, err) for err in errors)
        self.assert_stdout(*msgs_exp)
        self.assert_stderr(*errors_exp)

        if toggle:
            self.srvapi.torrent.assert_called(1, 'toggle_stopped', (process.mock_tfilter,), {'force': force})
        else:
            self.srvapi.torrent.assert_called(1, 'start', (process.mock_tfilter,), {'force': force})

    async def test_start(self):
        await self.do(['paused'], force=False, success_exp=True,
                      msgs=('Started torrent A',
                            'Started torrent B'))

    async def test_no_torrents_found(self):
        await self.do(['paused'], force=False, success_exp=False,
                      errors=('no torrents found',))

    async def test_force(self):
        await self.do(['paused', '--force'], force=True, success_exp=False,
                      msgs=('Started torrent 1',
                            'Started torrent 2'))

    async def test_force_short(self):
        await self.do(['paused', '-f'], force=True, success_exp=False,
                      msgs=('Started torrent 1',
                            'Started torrent 2'))

    async def test_toggle(self):
        await self.do(['paused', '--toggle'], force=False, toggle=True, success_exp=False,
                      msgs=('Started torrent 1',
                            'Stopped torrent 2'))

    async def test_toggle_short(self):
        await self.do(['paused', '-t'], force=False, toggle=True, success_exp=False,
                      msgs=('Stopped torrent 1',
                            'Started torrent 2'))

    @patch('stig.completion.candidates.torrent_filter')
    async def test_completion_candidates_for_posargs(self, mock_torrent_filter):
        mock_torrent_filter.return_value = Candidates(('a', 'b', 'c'))
        await self.assert_completion_candidates(StartTorrentsCmd, Args(('start', 'foo'), curarg_index=1),
                                                exp_cands=('a', 'b', 'c'))
        await self.assert_completion_candidates(StartTorrentsCmd, Args(('start', 'foo', 'bar'), curarg_index=2),
                                                exp_cands=('a', 'b', 'c'))


class TestStopTorrentsCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.patch('stig.objects',
                   srvapi=self.srvapi)
        self.patch('stig.commands.cli.StopTorrentsCmd',
                   select_torrents=mock_select_torrents)

    async def do(self, args, success_exp, msgs=(), errors=(), toggle=False):
        self.srvapi.torrent.response = Response(success=success_exp, msgs=msgs, errors=errors)


        process = await self.execute(StopTorrentsCmd, *args)
        self.assertEqual(process.success, success_exp)

        msgs_exp = tuple('^%s: %s$' % (StopTorrentsCmd.name, msg) for msg in msgs)
        errors_exp = tuple('^%s: %s$' % (StopTorrentsCmd.name, err) for err in errors)
        self.assert_stdout(*msgs_exp)
        self.assert_stderr(*errors_exp)

        if toggle:
            self.srvapi.torrent.assert_called(1, 'toggle_stopped', (process.mock_tfilter,), {})
        else:
            self.srvapi.torrent.assert_called(1, 'stop', (process.mock_tfilter,), {})

    async def test_stop(self):
        await self.do(['uploading'], success_exp=True,
                      msgs=('Stopped torrent A',
                            'Stopped torrent B'))

    async def test_no_torrents_found(self):
        await self.do(['uploading'], success_exp=False,
                      errors=('no torrents found',))

    async def test_toggle(self):
        await self.do(['uploading', '--toggle'], toggle=True, success_exp=False,
                      msgs=('Stopped torrent 1',
                            'Stopped torrent 2'))

    async def test_toggle_short(self):
        await self.do(['uploading', '-t'], toggle=True, success_exp=False,
                      msgs=('Started torrent 1',
                            'Started torrent 2'))

    @patch('stig.completion.candidates.torrent_filter')
    async def test_completion_candidates_for_posargs(self, mock_torrent_filter):
        mock_torrent_filter.return_value = Candidates(('a', 'b', 'c'))
        await self.assert_completion_candidates(StopTorrentsCmd, Args(('stop', 'foo'), curarg_index=1),
                                                exp_cands=('a', 'b', 'c'))
        await self.assert_completion_candidates(StopTorrentsCmd, Args(('stop', 'foo', 'bar'), curarg_index=2),
                                                exp_cands=('a', 'b', 'c'))


class TestVerifyTorrentsCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.patch('stig.objects',
                   srvapi=self.srvapi)
        self.patch('stig.commands.cli.VerifyTorrentsCmd',
                   select_torrents=mock_select_torrents)

    async def do(self, args, success_exp, msgs=(), errors=()):
        self.srvapi.torrent.response = Response(success=success_exp, msgs=msgs, errors=errors)

        process = await self.execute(VerifyTorrentsCmd, *args)
        self.assertEqual(process.success, success_exp)

        msgs_exp = tuple('^%s: %s$' % (VerifyTorrentsCmd.name, msg) for msg in msgs)
        errors_exp = tuple('^%s: %s$' % (VerifyTorrentsCmd.name, err) for err in errors)
        self.assert_stdout(*msgs_exp)
        self.assert_stderr(*errors_exp)

        self.srvapi.torrent.assert_called(1, 'verify', (process.mock_tfilter,), {})

    async def test_verify(self):
        await self.do(['idle'], success_exp=False,
                      msgs=('Verifying torrent A',),
                      errors=('Already verifying torrent B',))

    async def test_no_torrents_found(self):
        await self.do(['idle'], success_exp=True,
                      errors=('no torrents found',))

    @patch('stig.completion.candidates.torrent_filter')
    async def test_completion_candidates_for_posargs(self, mock_torrent_filter):
        mock_torrent_filter.return_value = Candidates(('a', 'b', 'c'))
        await self.assert_completion_candidates(VerifyTorrentsCmd, Args(('verify', 'foo'), curarg_index=1),
                                                exp_cands=('a', 'b', 'c'))
        await self.assert_completion_candidates(VerifyTorrentsCmd, Args(('verify', 'foo', 'bar'), curarg_index=2),
                                                exp_cands=('a', 'b', 'c'))
