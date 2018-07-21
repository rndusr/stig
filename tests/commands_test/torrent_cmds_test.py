from resources_cmd import (CommandTestCase, MockTorrent, mock_select_torrents,
                           mock_get_torrent_sorter)

from stig.client.utils import Response
from stig.client.errors import ClientError

from asynctest import CoroutineMock


from stig.commands.cli import AddTorrentsCmd
class TestAddTorrentsCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.patch('stig.commands.cli.AddTorrentsCmd',
                   srvapi=self.api)

    async def test_success(self):
        self.api.torrent.response = Response(
            success=True,
            msgs=('Added Some Torrent',),
            torrent=MockTorrent(id=1, name='Some Torrent'))
        process = await self.execute(AddTorrentsCmd, 'some.torrent')
        self.api.torrent.assert_called(1, 'add', ('some.torrent',), {'stopped': False, 'path': None})
        self.assertEqual(process.success, True)
        self.assert_stdout('add: Added Some Torrent')
        self.assert_stderr()

    async def test_failure(self):
        self.api.torrent.response = Response(
            success=False,
            errors=('Bogus torrent',),
            torrent=None)
        process = await self.execute(AddTorrentsCmd, 'some.torrent')
        self.api.torrent.assert_called(1, 'add', ('some.torrent',), {'stopped': False, 'path': None})
        self.assertEqual(process.success, False)
        self.assert_stdout()
        self.assert_stderr('add: Bogus torrent')

    async def test_multiple_torrents(self):
        self.api.torrent.response = [
            Response(success=True,
                     msgs=['Added Some Torrent'],
                     torrent=MockTorrent(id=1, name='Some Torrent')),
            Response(success=False,
                     errors=('Something went wrong',),
                     torrent=None),
        ]
        process = await self.execute(AddTorrentsCmd, 'some.torrent', 'another.torrent')
        self.api.torrent.assert_called(2, 'add',
                                       ('some.torrent',), {'stopped': False, 'path': None},
                                       ('another.torrent',), {'stopped': False, 'path': None})
        self.assertEqual(process.success, False)
        self.assert_stdout('add: Added Some Torrent')
        self.assert_stderr('add: Something went wrong')

    async def test_option_stopped(self):
        self.api.torrent.response = Response(
            success=True,
            msgs=('Added Some Torrent',),
            torrent=MockTorrent(id=1, name='Some Torrent'))
        process = await self.execute(AddTorrentsCmd, 'some.torrent', '--stopped')
        self.api.torrent.assert_called(1, 'add', ('some.torrent',), {'stopped': True, 'path': None})
        self.assertEqual(process.success, True)
        self.assert_stdout('add: Added Some Torrent')
        self.assert_stderr()


from stig.commands.cli import ListTorrentsCmd
class TestListTorrentsCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.patch('stig.commands.cli.ListTorrentsCmd',
                   srvapi=self.api,
                   cfg=self.cfg,
                   select_torrents=mock_select_torrents,
                   get_torrent_sorter=mock_get_torrent_sorter,
                   get_torrent_columns=lambda self, columns, interface=None: ('name',)
        )

        from types import SimpleNamespace
        from stig.commands.cli import torrent
        torrent.TERMSIZE = SimpleNamespace(columns=None, lines=None)

    async def do(self, args, errors):
        tlist = (
            MockTorrent(id=1, name='Some Torrent'),
            MockTorrent(id=2, name='Another Torrent')
        )
        self.api.torrent.response = Response(success=bool(errors), errors=(), msgs=(), torrents=tlist)
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
        await self.do(['foo'], errors=('%s: Nope!' % ListTorrentsCmd.name,))

    async def test_invalid_sort(self):
        def bad_get_torrent_sorter(self, *args, **kwargs):
            raise ValueError('Nope!')
        ListTorrentsCmd.get_torrent_sorter = bad_get_torrent_sorter
        await self.do(['-s', 'foo'], errors=('%s: Nope!' % ListTorrentsCmd.name,))


from stig.commands.cli import RemoveTorrentsCmd
class TestRemoveTorrentsCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.patch('stig.commands.cli.RemoveTorrentsCmd',
                   srvapi=self.api,
                   cfg=self.cfg,
                   select_torrents=mock_select_torrents,
        )

    async def do(self, args, tlist, success_exp, msgs=(), errors=(), delete=False, remove_called=True):
        self.api.torrent.response = Response(success=success_exp, torrents=tlist, msgs=msgs, errors=errors)

        process = await self.execute(RemoveTorrentsCmd, *args)
        self.assertEqual(process.success, success_exp)

        msgs_exp = tuple('^%s: %s$' % (RemoveTorrentsCmd.name, msg) for msg in msgs)
        errors_exp = tuple('^%s: %s$' % (RemoveTorrentsCmd.name, err) for err in errors)
        self.assert_stdout(*msgs_exp)
        self.assert_stderr(*errors_exp)

        if remove_called:
            self.api.torrent.assert_called(1, 'remove', (process.mock_tfilter,), {'delete': delete})
        else:
            self.api.torrent.assert_called(0, 'remove')

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
        RemoveTorrentsCmd.cfg['remove.max-hits'] = 2

        RemoveTorrentsCmd.show_list_of_hits = CoroutineMock()

        async def mock_ask_yes_no(self_, *args, yes, no, **kwargs):
            await yes() ; return True
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
        RemoveTorrentsCmd.cfg['remove.max-hits'] = 2

        RemoveTorrentsCmd.show_list_of_hits = CoroutineMock()

        async def mock_ask_yes_no(self_, *args, yes, no, **kwargs):
            await no() ; return False
        RemoveTorrentsCmd.ask_yes_no = mock_ask_yes_no

        await self.do(['seeds>50'], tlist=tlist, remove_called=False, success_exp=False,
                      errors=('Keeping .*? torrents: Too many hits .*',))
        self.assertTrue(RemoveTorrentsCmd.show_list_of_hits.called)

    async def test_max_hits_negative(self):
        tlist = (MockTorrent(id=1, name='Torrent1', seeds='51'),
                 MockTorrent(id=2, name='Torrent2', seeds='52'),
                 MockTorrent(id=3, name='Torrent3', seeds='53'))

        RemoveTorrentsCmd.show_list_of_hits = CoroutineMock()
        RemoveTorrentsCmd.cfg['remove.max-hits'] = -1
        await self.do(['all'], tlist=tlist, remove_called=True, success_exp=True,
                      msgs=('Removed Torrent1', 'Removed Torrent2', 'Removed Torrent3'))
        self.assertFalse(RemoveTorrentsCmd.show_list_of_hits.called)

    async def test_force_option(self):
        tlist = (MockTorrent(id=1, name='Torrent1', seeds='51'),
                 MockTorrent(id=2, name='Torrent2', seeds='52'),
                 MockTorrent(id=3, name='Torrent3', seeds='53'))
        RemoveTorrentsCmd.cfg['remove.max-hits'] = 2

        RemoveTorrentsCmd.show_list_of_hits = CoroutineMock()
        RemoveTorrentsCmd.ask_yes_no = CoroutineMock()

        await self.do(['all', '--force'], tlist=tlist, remove_called=True, success_exp=True,
                      msgs=('Removed Torrent1', 'Removed Torrent2', 'Removed Torrent3'))
        self.assertFalse(RemoveTorrentsCmd.show_list_of_hits.called)
        self.assertFalse(RemoveTorrentsCmd.ask_yes_no.called)


from stig.commands.cli import StartTorrentsCmd
class TestStartTorrentsCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.patch('stig.commands.cli.StartTorrentsCmd',
                   srvapi=self.api,
                   select_torrents=mock_select_torrents,
        )

    async def do(self, args, success_exp, msgs=(), errors=(), force=False, toggle=False):
        self.api.torrent.response = Response(success=success_exp, msgs=msgs, errors=errors)

        process = await self.execute(StartTorrentsCmd, *args)
        self.assertEqual(process.success, success_exp)

        msgs_exp = tuple('^%s: %s$' % (StartTorrentsCmd.name, msg) for msg in msgs)
        errors_exp = tuple('^%s: %s$' % (StartTorrentsCmd.name, err) for err in errors)
        self.assert_stdout(*msgs_exp)
        self.assert_stderr(*errors_exp)

        if toggle:
            self.api.torrent.assert_called(1, 'toggle_stopped', (process.mock_tfilter,), {'force': force})
        else:
            self.api.torrent.assert_called(1, 'start', (process.mock_tfilter,), {'force': force})

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


from stig.commands.cli import StopTorrentsCmd
class TestStopTorrentsCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.patch('stig.commands.cli.StopTorrentsCmd',
                   srvapi=self.api,
                   select_torrents=mock_select_torrents,
        )

    async def do(self, args, success_exp, msgs=(), errors=(), toggle=False):
        self.api.torrent.response = Response(success=success_exp, msgs=msgs, errors=errors)


        process = await self.execute(StopTorrentsCmd, *args)
        self.assertEqual(process.success, success_exp)

        msgs_exp = tuple('^%s: %s$' % (StopTorrentsCmd.name, msg) for msg in msgs)
        errors_exp = tuple('^%s: %s$' % (StopTorrentsCmd.name, err) for err in errors)
        self.assert_stdout(*msgs_exp)
        self.assert_stderr(*errors_exp)

        if toggle:
            self.api.torrent.assert_called(1, 'toggle_stopped', (process.mock_tfilter,), {})
        else:
            self.api.torrent.assert_called(1, 'stop', (process.mock_tfilter,), {})

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


from stig.commands.cli import VerifyTorrentsCmd
class TestVerifyTorrentsCmd(CommandTestCase):
    def setUp(self):
        super().setUp()

        self.patch('stig.commands.cli.VerifyTorrentsCmd',
                   srvapi=self.api,
                   select_torrents=mock_select_torrents,
        )

    async def do(self, args, success_exp, msgs=(), errors=()):
        self.api.torrent.response = Response(success=success_exp, msgs=msgs, errors=errors)

        process = await self.execute(VerifyTorrentsCmd, *args)
        self.assertEqual(process.success, success_exp)

        msgs_exp = tuple('^%s: %s$' % (VerifyTorrentsCmd.name, msg) for msg in msgs)
        errors_exp = tuple('^%s: %s$' % (VerifyTorrentsCmd.name, err) for err in errors)
        self.assert_stdout(*msgs_exp)
        self.assert_stderr(*errors_exp)

        self.api.torrent.assert_called(1, 'verify', (process.mock_tfilter,), {})

    async def test_verify(self):
        await self.do(['idle'], success_exp=False,
                      msgs=('Verifying torrent A',),
                      errors=('Already verifying torrent B',))

    async def test_no_torrents_found(self):
        await self.do(['idle'], success_exp=True,
                      errors=('no torrents found',))
