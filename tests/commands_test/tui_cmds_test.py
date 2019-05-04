from resources_cmd import CommandTestCase
from stig.utils.cliparser import Args
from stig.completion import Candidates

from asynctest.mock import patch


from stig.commands.tui import TabCmd
class TestTabCmd(CommandTestCase):
    @patch('stig.completion.candidates.for_args')
    @patch('stig.completion.candidates.commands')
    async def test_completion_candidates__subcmd_name(self, mock_commands, mock_for_args):
        mock_commands.return_value = Candidates(('foo', 'bar', 'baz'))
        args = Args(('tab', '--bar', 'a', '-b', 'c'), curarg_index=2, curarg_curpos=0)
        await self.assert_completion_candidates(TabCmd, args, exp_cands=('foo', 'bar', 'baz'))
        mock_commands.assert_called_once_with()
        mock_for_args.assert_not_called()

    @patch('stig.completion.candidates.for_args')
    @patch('stig.commands._CompletionCandidatesMixin.completion_candidates_opts')
    async def test_completion_candidates__own_options(self, mock_completion_candidates_opts, mock_for_args):
        mock_completion_candidates_opts.return_value = Candidates(('--foo', '--bar', '--baz'))
        args = Args(('tab', '--bar', 'a', '-b', 'c'), curarg_index=1, curarg_curpos=1)
        await self.assert_completion_candidates(TabCmd, args, exp_cands=('--foo', '--bar', '--baz'))
        mock_completion_candidates_opts.assert_called_once_with(args)
        mock_for_args.assert_not_called()

    @patch('stig.completion.candidates.for_args')
    @patch('stig.commands._CompletionCandidatesMixin.completion_candidates_opts')
    async def test_completion_candidates__subcmd_options(self, mock_completion_candidates_opts, mock_for_args):
        mock_for_args.return_value = Candidates(('--foo', '--bar', '--baz'))
        args = Args(('tab', '--bar', 'a', '-b', 'c'), curarg_index=3, curarg_curpos=1)
        await self.assert_completion_candidates(TabCmd, args, exp_cands=('--foo', '--bar', '--baz'))
        mock_completion_candidates_opts.assert_not_called()
        mock_for_args.assert_called_once_with(Args(('a', '-b', 'c'), curarg_index=1, curarg_curpos=1))

    @patch('stig.completion.candidates.for_args')
    @patch('stig.commands._CompletionCandidatesMixin.completion_candidates_opts')
    async def test_completion_candidates__own_parameters(self, mock_completion_candidates_opts, mock_for_args):
        mock_completion_candidates_opts.return_value = Candidates(('foo', 'bar', 'baz'))
        args = Args(('tab', '-c', 'asdf', 'a', '-b', 'c'), curarg_index=2, curarg_curpos=0)
        await self.assert_completion_candidates(TabCmd, args, exp_cands=('foo', 'bar', 'baz'))
        mock_for_args.assert_not_called()
        mock_completion_candidates_opts.assert_called_once_with(args)

    @patch('stig.completion.candidates.for_args')
    @patch('stig.completion.candidates.commands')
    async def test_completion_candidates__subcmd_parameters(self, mock_commands, mock_for_args):
        mock_for_args.return_value = Candidates(('foo', 'bar', 'baz'))
        args = Args(('tab', '--bar', 'a', '-b', 'c'), curarg_index=4, curarg_curpos=0)
        await self.assert_completion_candidates(TabCmd, args, exp_cands=('foo', 'bar', 'baz'))
        mock_commands.assert_not_called()
        mock_for_args.assert_called_once_with(Args(('a', '-b', 'c'), curarg_index=2, curarg_curpos=0))
