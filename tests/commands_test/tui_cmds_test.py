from resources_cmd import CommandTestCase
from stig.utils.cliparser import Args
from stig.completion import Candidates

from asynctest.mock import patch


from stig.commands.tui import TabCmd
class TestTabCmd(CommandTestCase):
    @patch('stig.commands.tui.TabCmd.completion_candidates_opts')
    async def test_completion_candidates__options(self, mock_completion_candidates_opts):
        mock_completion_candidates_opts.return_value = Candidates(('--foo', '--bar', '--baz'))
        await self.assert_completion_candidates(TabCmd, Args(('tab', '--bar', 'asdf'), curarg_index=1),
                                                exp_cands=('--foo', '--bar', '--baz'))

    @patch('stig.commands.tui.candidates.commands')
    async def test_completion_candidates__command_names(self, mock_commands):
        mock_commands.return_value = Candidates(('foo', 'bar', 'baz'))
        await self.assert_completion_candidates(TabCmd, Args(('tab', 'foo', '--bar', 'baz'), curarg_index=1),
                                                exp_cands=('foo', 'bar', 'baz'))
        await self.assert_completion_candidates(TabCmd, Args(('tab', '-b', 'foo', '--bar', 'baz'), curarg_index=2),
                                                exp_cands=('foo', 'bar', 'baz'))
        await self.assert_completion_candidates(TabCmd, Args(('tab', '-b', '--close', 'foo', '--bar', 'baz'), curarg_index=3),
                                                exp_cands=('foo', 'bar', 'baz'))

    @patch('stig.commands.tui.objects.cmdmgr')
    async def test_completion_candidates__subcommand_arguments(self, mock_cmdmgr):
        mock_cmdmgr.get_cmdcls().completion_candidates.return_value = Candidates(('a', 'b', 'c'))
        await self.assert_completion_candidates(TabCmd, Args(('tab', '-b', 'foo', '--bar', 'baz'), curarg_index=3, curarg_curpos=0),
                                                exp_cands=('a', 'b', 'c'))
        mock_cmdmgr.get_cmdcls.assert_called_with('foo')
        mock_cmdmgr.get_cmdcls().completion_candidates.assert_called_with(Args(('foo', '--bar', 'baz'),
                                                                               curarg_index=1, curarg_curpos=0))
