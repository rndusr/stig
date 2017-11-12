from resources_cmd import (CommandTestCase, MockTorrent, mock_select_torrents,
                           mock_get_torrent_sorter)

from stig.client.utils import Response
from stig.client.errors import ClientError


from stig.commands.cli import AddTorrentsCmd
class TestAddTorrentsCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        AddTorrentsCmd.srvapi = self.api

    async def test_success(self):
        self.api.torrent.response = Response(
            success=True,
            msgs=['Added Some Torrent'],
            torrent=MockTorrent(id=1, name='Some Torrent'))
        process = AddTorrentsCmd(['some.torrent'], loop=self.loop)
        with self.assertLogs(level='INFO') as logged:
            await self.finish(process)
        self.api.torrent.assert_called(1, 'add', ('some.torrent',), {'stopped': False, 'path': None})
        self.assertEqual(process.success, True)
        self.assert_logged(logged, ('INFO', '^Added Some Torrent$'))

    async def test_failure(self):
        self.api.torrent.response = Response(
            success=False,
            msgs=[ClientError('Bogus torrent')],
            torrent=None)
        process = AddTorrentsCmd(['some.torrent'], loop=self.loop)
        with self.assertLogs(level='ERROR') as logged:
            await self.finish(process)
        self.api.torrent.assert_called(1, 'add', ('some.torrent',), {'stopped': False, 'path': None})
        self.assertEqual(process.success, False)
        self.assert_logged(logged, ('ERROR', '^Bogus torrent$'))

    async def test_multiple_torrents(self):
        self.api.torrent.response = [
            Response(success=True,
                     msgs=['Added Some Torrent'],
                     torrent=MockTorrent(id=1, name='Some Torrent')),
            Response(success=False,
                     msgs=[ClientError('Something went wrong')],
                     torrent=None),
        ]
        process = AddTorrentsCmd(['some.torrent', 'another.torrent'], loop=self.loop)
        with self.assertLogs(level='INFO') as logged:
            await self.finish(process)
        self.api.torrent.assert_called(2, 'add',
                                       ('some.torrent',), {'stopped': False, 'path': None},
                                       ('another.torrent',), {'stopped': False, 'path': None})
        self.assertEqual(process.success, False)
        self.assert_logged(logged,
                           ('INFO', '^Added Some Torrent$'),
                           ('ERROR', '^Something went wrong$'))

    async def test_option_stopped(self):
        self.api.torrent.response = Response(
            success=True,
            msgs=['Added Some Torrent'],
            torrent=MockTorrent(id=1, name='Some Torrent'))
        process = AddTorrentsCmd(['some.torrent', '--stopped'], loop=self.loop)
        with self.assertLogs(level='INFO') as logged:
            await self.finish(process)
        self.api.torrent.assert_called(1, 'add', ('some.torrent',), {'stopped': True, 'path': None})
        self.assertEqual(process.success, True)
        self.assert_logged(logged, ('INFO', '^Added Some Torrent$'))


from stig.commands.cli import ListTorrentsCmd
class TestListTorrentsCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        ListTorrentsCmd.srvapi = self.api
        ListTorrentsCmd.cfg = self.cfg
        ListTorrentsCmd.select_torrents = mock_select_torrents
        ListTorrentsCmd.get_torrent_sorter = mock_get_torrent_sorter
        ListTorrentsCmd.get_torrent_columns = lambda self, columns, interface=None: ('name',)

        from types import SimpleNamespace
        from stig.commands.cli import torrent
        torrent.TERMSIZE = SimpleNamespace(columns=None, lines=None)

    async def do(self, args, errors):
        tlist = (
            MockTorrent(id=1, name='Some Torrent'),
            MockTorrent(id=2, name='Another Torrent')
        )
        self.api.torrent.response = Response(errors=(), msgs=[], torrents=tlist)
        with self.assertLogs(level='INFO') as logged:
            process = ListTorrentsCmd(args, loop=self.loop)
            await self.finish(process)
        expected_success = not errors
        self.assertEqual(process.success, expected_success)
        if errors:
            expected_msgs = tuple(('ERROR', regex) for regex in errors)
            self.assert_logged(logged, *expected_msgs)
        else:
            self.assert_logged(logged,
                               ('INFO', 'Some Torrent'),
                               ('INFO', 'Another Torrent'))
            keys_exp = set(process.mock_tsorter.needed_keys + \
                           process.mock_tfilter.needed_keys + \
                           ('name',))  # columns
            self.api.torrent.assert_called(1, 'torrents', (process.mock_tfilter,),
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
        await self.do(['foo'], errors=('Nope!',))

    async def test_invalid_sort(self):
        def bad_get_torrent_sorter(self, *args, **kwargs):
            raise ValueError('Nope!')
        ListTorrentsCmd.get_torrent_sorter = bad_get_torrent_sorter
        await self.do(['-s', 'foo'], errors=('Nope!',))


from stig.commands.cli import RemoveTorrentsCmd
class TestRemoveTorrentsCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        RemoveTorrentsCmd.srvapi = self.api
        RemoveTorrentsCmd.select_torrents = mock_select_torrents
        RemoveTorrentsCmd.cfg = self.cfg

    async def do(self, args, msgs, tlist, delete=False):
        success_exp = all(isinstance(msg, str) for msg in msgs)
        self.api.torrent.response = Response(success=success_exp, msgs=msgs, torrents=tlist)
        process = RemoveTorrentsCmd(args, loop=self.loop)
        with self.assertLogs(level='INFO') as logged:
            await self.finish(process)
        self.api.torrent.assert_called(1, 'remove', (process.mock_tfilter,), {'delete': delete})
        self.assertEqual(process.success, success_exp)
        exp_msgs = tuple( (('INFO' if isinstance(msg, str) else 'ERROR'), str(msg))
                          for msg in msgs )
        self.assert_logged(logged, *exp_msgs)

    async def test_remove(self):
        tlist = (MockTorrent(id=1, name='Some Torrent', seeds='51'),)
        await self.do(['seeds>50'], tlist=tlist, delete=False,
                      msgs=('Removed Some Torrent',))

    async def test_delete_files(self):
        tlist = (MockTorrent(id=1, name='Some Torrent', seeds='51'),)
        await self.do(['--delete-files', 'seeds>50'], tlist=tlist, delete=True,
                      msgs=('Removed Some Torrent',))

    async def test_delete_files_short(self):
        tlist = (MockTorrent(id=1, name='Some Torrent', seeds='51'),)
        await self.do(['-d', 'seeds>50'], tlist=tlist, delete=True,
                      msgs=('Removed Some Torrent',))

    async def test_no_torrents_found(self):
        await self.do(['seeds>5000'], delete=False, tlist=(),
                      msgs=(ClientError('no torrents found'),))


from stig.commands.cli import StartTorrentsCmd
class TestStartTorrentsCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        StartTorrentsCmd.srvapi = self.api
        StartTorrentsCmd.select_torrents = mock_select_torrents

    async def do(self, args, msgs=(), force=False, toggle=False):
        success_exp = all(isinstance(msg, str) for msg in msgs)
        self.api.torrent.response = Response(success=success_exp, msgs=msgs)
        process = StartTorrentsCmd(args, loop=self.loop)
        with self.assertLogs(level='INFO') as logged:
            await self.finish(process)
        if toggle:
            self.api.torrent.assert_called(1, 'toggle_stopped', (process.mock_tfilter,), {'force': force})
        else:
            self.api.torrent.assert_called(1, 'start', (process.mock_tfilter,), {'force': force})
        self.assertEqual(process.success, success_exp)
        exp_msgs = tuple( (('INFO' if isinstance(msg, str) else 'ERROR'), str(msg))
                          for msg in msgs )
        self.assert_logged(logged, *exp_msgs)

    async def test_start(self):
        await self.do(['paused'], force=False,
                      msgs=('Started torrent A',
                            'Started torrent B'))

    async def test_no_torrents_found(self):
        await self.do(['paused'], force=False,
                      msgs=(ClientError('no torrents found'),))

    async def test_force(self):
        await self.do(['paused', '--force'], force=True,
                      msgs=('Started torrent 1',
                            'Started torrent 2'))

    async def test_force_short(self):
        await self.do(['paused', '-f'], force=True,
                      msgs=('Started torrent 1',
                            'Started torrent 2'))

    async def test_toggle(self):
        await self.do(['paused', '--toggle'], force=False, toggle=True,
                      msgs=('Started torrent 1',
                            'Stopped torrent 2'))

    async def test_toggle_short(self):
        await self.do(['paused', '-t'], force=False, toggle=True,
                      msgs=('Stopped torrent 1',
                            'Started torrent 2'))


from stig.commands.cli import StopTorrentsCmd
class TestStopTorrentsCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        StopTorrentsCmd.srvapi = self.api
        StopTorrentsCmd.select_torrents = mock_select_torrents

    async def do(self, args, msgs=(), toggle=False):
        success_exp = all(isinstance(msg, str) for msg in msgs)
        self.api.torrent.response = Response(success=success_exp, msgs=msgs)
        process = StopTorrentsCmd(args, loop=self.loop)
        with self.assertLogs(level='INFO') as logged:
            await self.finish(process)
        if toggle:
            self.api.torrent.assert_called(1, 'toggle_stopped', (process.mock_tfilter,), {})
        else:
            self.api.torrent.assert_called(1, 'stop', (process.mock_tfilter,), {})
        self.assertEqual(process.success, success_exp)
        exp_msgs = tuple( (('INFO' if isinstance(msg, str) else 'ERROR'), str(msg))
                          for msg in msgs )
        self.assert_logged(logged, *exp_msgs)

    async def test_stop(self):
        await self.do(['uploading'], msgs=('Stopped torrent A',
                                           'Stopped torrent B'))

    async def test_no_torrents_found(self):
        await self.do(['uploading'],
                      msgs=(ClientError('no torrents found'),))

    async def test_toggle(self):
        await self.do(['uploading', '--toggle'], toggle=True,
                      msgs=('Stopped torrent 1',
                            'Stopped torrent 2'))

    async def test_toggle_short(self):
        await self.do(['uploading', '-t'], toggle=True,
                      msgs=('Started torrent 1',
                            'Started torrent 2'))


from stig.commands.cli import VerifyTorrentsCmd
class TestVerifyTorrentsCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        VerifyTorrentsCmd.srvapi = self.api
        VerifyTorrentsCmd.select_torrents = mock_select_torrents

    async def do(self, args, msgs=()):
        success_exp = all(isinstance(msg, str) for msg in msgs)
        self.api.torrent.response = Response(success=success_exp, msgs=msgs)
        process = VerifyTorrentsCmd(args, loop=self.loop)
        with self.assertLogs(level='INFO') as logged:
            await self.finish(process)
        self.api.torrent.assert_called(1, 'verify', (process.mock_tfilter,), {})
        self.assertEqual(process.success, success_exp)
        exp_msgs = tuple( (('INFO' if isinstance(msg, str) else 'ERROR'), str(msg))
                          for msg in msgs )
        self.assert_logged(logged, *exp_msgs)

    async def test_verify(self):
        await self.do(['idle'], msgs=('Verifying torrent A',
                                      ClientError('Already verifying torrent B')))

    async def test_no_torrents_found(self):
        await self.do(['idle'],
                      msgs=(ClientError('no torrents found'),))
