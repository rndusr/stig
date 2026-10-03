from unittest.mock import AsyncMock, MagicMock

from resources_cmd import CommandTestCase

from stig.client.utils import Response
from stig.commands.cli import TrackerCmd as CLITrackerCmd
from stig.commands.tui import TrackerCmd as TUITrackerCmd
from stig.utils.cliparser import Args


class TestTrackerCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.mock_select_torrents = MagicMock()
        self.mock_srvapi = MagicMock()
        self.mock_srvapi.torrent.tracker_add = AsyncMock()
        self.mock_srvapi.torrent.tracker_remove = AsyncMock()
        self.mock_srvapi.torrent.tracker_replace = AsyncMock()
        self.mock_srvapi.interval = 10
        self.patch('stig.objects', srvapi=self.mock_srvapi)
        self.patch('stig.commands.cli.TrackerCmd',
                   select_torrents=self.mock_select_torrents)
        self.patch('stig.commands.tui.TrackerCmd',
                   select_torrents=self.mock_select_torrents)

    async def test_tracker_replace_with_filter(self):
        self.mock_select_torrents.return_value = 'mock filter'
        mock_resp = Response(success=True, torrents=(), msgs=('Replaced tracker',), errors=())
        self.mock_srvapi.torrent.tracker_replace.return_value = mock_resp

        process = await self.execute(CLITrackerCmd, 'replace', 'url-announce~old', 'http://old/announce', 'https://new/announce')
        self.mock_select_torrents.assert_called_once_with('url-announce~old', allow_no_filter=False, discover_torrent=True)
        self.mock_srvapi.torrent.tracker_replace.assert_called_once_with('mock filter', 'http://old/announce', 'https://new/announce')
        self.assertTrue(process.success)

    async def test_tracker_replace_without_filter(self):
        self.mock_select_torrents.return_value = 'discovered filter'
        mock_resp = Response(success=True, torrents=(), msgs=('Replaced tracker',), errors=())
        self.mock_srvapi.torrent.tracker_replace.return_value = mock_resp

        process = await self.execute(TUITrackerCmd, 'replace', 'http://old/announce', 'https://new/announce')
        self.mock_select_torrents.assert_called_once_with(None, allow_no_filter=False, discover_torrent=True)
        self.mock_srvapi.torrent.tracker_replace.assert_called_once_with('discovered filter', 'http://old/announce', 'https://new/announce')
        self.assertTrue(process.success)

    async def test_tracker_replace_invalid_args(self):
        process = await self.execute(CLITrackerCmd, 'replace', 'only_one_arg')
        self.assertFalse(process.success)
        self.assert_stderr(r'.*Usage: tracker replace.*')

    async def test_tracker_add(self):
        self.mock_select_torrents.return_value = 'mock filter'
        mock_resp = Response(success=True, torrents=(), msgs=('Added tracker',), errors=())
        self.mock_srvapi.torrent.tracker_add.return_value = mock_resp

        process = await self.execute(CLITrackerCmd, 'add', 'all', 'http://new/announce')
        self.mock_select_torrents.assert_called_once_with('all', allow_no_filter=False, discover_torrent=True)
        self.mock_srvapi.torrent.tracker_add.assert_called_once_with('mock filter', ('http://new/announce',))
        self.assertTrue(process.success)

    async def test_tracker_remove(self):
        self.mock_select_torrents.return_value = 'mock filter'
        mock_resp = Response(success=True, torrents=(), msgs=('Removed tracker',), errors=())
        self.mock_srvapi.torrent.tracker_remove.return_value = mock_resp

        process = await self.execute(CLITrackerCmd, 'remove', 'all', 'http://old/announce')
        self.mock_select_torrents.assert_called_once_with('all', allow_no_filter=False, discover_torrent=True)
        self.mock_srvapi.torrent.tracker_remove.assert_called_once_with('mock filter', ('http://old/announce',), partial_match=True)
        self.assertTrue(process.success)

    async def test_completion_candidates(self):
        await self.assert_completion_candidates(CLITrackerCmd, Args(('tracker', 'rep'), curarg_index=1),
                                                exp_cands=('add', 'remove', 'replace'))
