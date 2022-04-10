import unittest

from resources_cmd import make_cmdcls

from stig.commands import CommandManager
from stig.commands.guess_ui import UIGuessError, guess_ui


class Test_guess_ui(unittest.TestCase):
    def setUp(self):
        self.cmdmgr = CommandManager()
        self.cmdmgr.register(make_cmdcls(name='dotui', provides=('tui',)))
        self.cmdmgr.register(make_cmdcls(name='docli', provides=('cli',)))
        self.cmdmgr.register(make_cmdcls(name='doboth', provides=('cli', 'tui')))
        self.cmdmgr.register(make_cmdcls(name='dotorrent', provides=('cli', 'tui'), category='torrent'))

    def guess_ui(self, cmds):
        return guess_ui(cmds, self.cmdmgr)

    def test_guess_no_commands(self):
        self.assertEqual(self.guess_ui([]), 'tui')

    def test_guess_exclusive_tui_command(self):
        self.assertEqual(self.guess_ui([['dotui']]), 'tui')

    def test_guess_exclusive_cli_command(self):
        self.assertEqual(self.guess_ui([['docli']]), 'cli')

    def test_guess_universal_command(self):
        self.assertEqual(self.guess_ui([['doboth']]), 'cli')

    def test_guess_cli_and_tui_command(self):
        with self.assertRaises(UIGuessError):
            self.guess_ui([['dotui'], ['docli']])

    def test_guess_torrent_command(self):
        self.assertEqual(self.guess_ui([['dotorrent']]), 'cli')
        self.assertEqual(self.guess_ui([['dotui'], ['dotorrent']]), 'tui')
        self.assertEqual(self.guess_ui([['docli'], ['dotorrent']]), 'cli')
