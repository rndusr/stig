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
        for args in (Args(('tab', 'a', '-b', 'c'), curarg_index=1),
                     Args(('tab', '-c', 'foo', 'a', '-b', 'c'), curarg_index=3),
                     Args(('tab', '-c', 'foo', '-t', 'bar', 'a', '-b', 'c'), curarg_index=5),):
            await self.assert_completion_candidates(TabCmd, args, exp_cands=('foo', 'bar', 'baz'))
            mock_commands.assert_called_with()
            mock_for_args.assert_not_called()

    @patch('stig.completion.candidates.for_args')
    @patch('stig.completion.candidates.commands')
    @patch('stig.commands.cmdbase._CompletionCandidatesMixin.completion_candidates_opts')
    async def test_completion_candidates__own_options(self, mock_completion_candidates_opts, mock_commands, mock_for_args):
        mock_completion_candidates_opts.return_value = Candidates(('--foo', '--bar', '--baz'))
        for args in (Args(('tab', '-', 'a', '-b', 'c'), curarg_index=1, curarg_curpos=1),
                     Args(('tab', '-c', 'foo', '-t', 'bar', 'a', '-b', 'c'), curarg_index=3)):
            await self.assert_completion_candidates(TabCmd, args, exp_cands=('--foo', '--bar', '--baz'))
            mock_completion_candidates_opts.assert_called_with(args)
            mock_for_args.assert_not_called()
            mock_commands.assert_not_called()

    @patch('stig.completion.candidates.for_args')
    @patch('stig.completion.candidates.commands')
    @patch('stig.commands.cmdbase._CompletionCandidatesMixin.completion_candidates_opts')
    async def test_completion_candidates__subcmd_options(self, mock_completion_candidates_opts, mock_commands, mock_for_args):
        mock_for_args.return_value = Candidates(('--foo', '--bar', '--baz'))
        args = Args(('tab', '--bar', 'a', '-b', 'c'), curarg_index=3, curarg_curpos=1)
        await self.assert_completion_candidates(TabCmd, args, exp_cands=('--foo', '--bar', '--baz'))
        mock_completion_candidates_opts.assert_not_called()
        mock_for_args.assert_called_once_with(Args(('a', '-b', 'c'), curarg_index=1, curarg_curpos=1))
        mock_commands.assert_not_called()

    @patch('stig.completion.candidates.for_args')
    @patch('stig.completion.candidates.commands')
    @patch('stig.commands.cmdbase._CompletionCandidatesMixin.completion_candidates_opts')
    async def test_completion_candidates__own_parameters(self, mock_completion_candidates_opts, mock_commands, mock_for_args):
        mock_completion_candidates_opts.return_value = Candidates(('foo', 'bar', 'baz'))
        for args in (Args(('tab', '-c', 'foo', '-t', '', 'a', '-b', 'c'), curarg_index=4),
                     Args(('tab', '-c', 'foo', '-t', 'bar', 'a', '-b', 'c'), curarg_index=2, curarg_curpos=2)):
            await self.assert_completion_candidates(TabCmd, args, exp_cands=('foo', 'bar', 'baz'))
            mock_completion_candidates_opts.assert_called_with(args)
            mock_for_args.assert_not_called()
            mock_commands.assert_not_called()

    @patch('stig.completion.candidates.for_args')
    @patch('stig.completion.candidates.commands')
    async def test_completion_candidates__subcmd_parameters(self, mock_commands, mock_for_args):
        mock_for_args.return_value = Candidates(('foo', 'bar', 'baz'))
        args = Args(('tab', '--bar', 'a', '-b', 'c'), curarg_index=4)
        await self.assert_completion_candidates(TabCmd, args, exp_cands=('foo', 'bar', 'baz'))
        mock_for_args.assert_called_once_with(Args(('a', '-b', 'c'), curarg_index=2, curarg_curpos=0))
        mock_commands.assert_not_called()


from stig.commands.tui import BindCmd
class TestBindCmd(CommandTestCase):
    @patch('stig.completion.candidates.for_args')
    @patch('stig.completion.candidates.commands')
    async def test_completion_candidates__subcmd_name(self, mock_commands, mock_for_args):
        mock_commands.return_value = Candidates(('foo', 'bar', 'baz'))
        for args in (Args(('bind', 'alt-x', 'a', '-b', 'c'), curarg_index=2),
                     Args(('bind', '-c', 'foo', 'alt-x', 'a', '-b', 'c'), curarg_index=4),
                     Args(('bind', '-c', 'foo', '-d', 'bar', 'alt-x', 'a', '-b', 'c'), curarg_index=6),
                     Args(('bind', '-c', 'foo', 'alt-x', '-d', 'bar', 'a', '-b', 'c'), curarg_index=6),):
            await self.assert_completion_candidates(BindCmd, args, exp_cands=('foo', 'bar', 'baz'))
            mock_commands.assert_called_once_with()
            mock_for_args.assert_not_called()
            mock_commands.reset_mock()
            mock_for_args.reset_mock()

    @patch('stig.completion.candidates.for_args')
    @patch('stig.completion.candidates.commands')
    @patch('stig.commands.cmdbase._CompletionCandidatesMixin.completion_candidates_opts')
    async def test_completion_candidates__own_options(self, mock_completion_candidates_opts, mock_commands, mock_for_args):
        mock_completion_candidates_opts.return_value = Candidates(('--context', '--description'))
        for args in (Args(('bind', '-c', 'foo', 'alt-x', 'a', '-b', 'c'), curarg_index=1),
                     Args(('bind', '-d', 'bar', 'alt-x', 'a', '-b', 'c'), curarg_index=1),
                     Args(('bind', '-c', 'foo', '-d', 'bar', 'alt-x', 'a', '-b', 'c'), curarg_index=3),
                     Args(('bind', '-c', 'foo', 'alt-x', '-d', 'bar', 'a', '-b', 'c'), curarg_index=4)):
            await self.assert_completion_candidates(BindCmd, args, exp_cands=('--context', '--description'))
            mock_completion_candidates_opts.assert_called_with(args)
            mock_for_args.assert_not_called()
            mock_commands.assert_not_called()

    @patch('stig.completion.candidates.for_args')
    @patch('stig.completion.candidates.commands')
    async def test_completion_candidates__subcmd_options(self, mock_commands, mock_for_args):
        mock_for_args.return_value = Candidates(('--foo', '--bar', '--baz'))
        for args,i1,i2 in ((('bind', 'alt-x', 'a', '-b', 'c'), 3, 1),
                           (('bind', 'alt-x', 'a', '-b', 'c'), 4, 2),
                           (('bind', '-c', 'foo', 'alt-x', 'a', '-b', 'c'), 5, 1),
                           (('bind', '-d', 'bar', 'alt-x', 'a', '-b', 'c'), 6, 2),
                           (('bind', '-c', 'foo', '-d', 'bar', 'alt-x', 'a', '-b', 'c'), 7, 1),
                           (('bind', '-c', 'foo', '-d', 'bar', 'alt-x', 'a', '-b', 'c'), 8, 2)):
            await self.assert_completion_candidates(BindCmd, Args(args, curarg_index=i1),
                                                    exp_cands=('--foo', '--bar', '--baz'))
            mock_for_args.assert_called_with(Args(('a', '-b', 'c'), curarg_index=i2, curarg_curpos=0))
            mock_commands.assert_not_called()

    @patch('stig.completion.candidates.for_args')
    @patch('stig.completion.candidates.commands')
    @patch('stig.commands.cmdbase._CompletionCandidatesMixin.completion_candidates_opts')
    async def test_completion_candidates__own_parameters(self, mock_completion_candidates_opts, mock_commands, mock_for_args):
        mock_completion_candidates_opts.return_value = Candidates(('foo', 'bar', 'baz'))
        for args in (Args(('bind', '-c', 'foo', 'alt-x', 'a', '-b', 'c'), curarg_index=2),
                     Args(('bind', '-d', 'bar', 'alt-x', 'a', '-b', 'c'), curarg_index=2),
                     Args(('bind', '-c', 'foo', '-d', 'bar', 'alt-x', 'a', '-b', 'c'), curarg_index=2),
                     Args(('bind', '-c', 'foo', '-d', 'bar', 'alt-x', 'a', '-b', 'c'), curarg_index=4)):
            await self.assert_completion_candidates(BindCmd, args, exp_cands=('foo', 'bar', 'baz'))
            mock_completion_candidates_opts.assert_called_with(args)
            mock_for_args.assert_not_called()
            mock_commands.assert_not_called()

    @patch('stig.completion.candidates.for_args')
    @patch('stig.completion.candidates.commands')
    async def test_completion_candidates__subcmd_parameters(self, mock_commands, mock_for_args):
        mock_for_args.return_value = Candidates(('foo', 'bar', 'baz'))
        for args in (Args(('bind', 'alt-x', 'a', '-b', 'c'), curarg_index=4),
                     Args(('bind', '-d', 'bar', 'alt-x', 'a', '-b', 'c'), curarg_index=6),
                     Args(('bind', '-c', 'foo', '-d', 'bar', 'alt-x', 'a', '-b', 'c'), curarg_index=8)):
            await self.assert_completion_candidates(BindCmd, args, exp_cands=('foo', 'bar', 'baz'))
            mock_for_args.assert_called_once_with(Args(('a', '-b', 'c'), curarg_index=2))
            mock_for_args.reset_mock()
            mock_commands.assert_not_called()

    @patch('stig.completion.candidates.for_args')
    @patch('stig.completion.candidates.commands')
    @patch('stig.commands.cmdbase._CompletionCandidatesMixin.completion_candidates_opts')
    async def test_completion_candidates__no_subcmd(self, mock_completion_candidates_opts, mock_commands, mock_for_args):
        mock_completion_candidates_opts.return_value = Candidates(('foo', 'bar', 'baz'))
        for args in (Args(('bind',), curarg_index=0),
                     Args(('bind', '-d', 'bar'), curarg_index=1),
                     Args(('bind', '-d', 'bar'), curarg_index=2),
                     Args(('bind', '-c', 'foo', '-d', 'bar'), curarg_index=3),
                     Args(('bind', '-c', 'foo', '-d', 'bar'), curarg_index=4)):
            await self.assert_completion_candidates(BindCmd, args, exp_cands=('foo', 'bar', 'baz'))
            mock_completion_candidates_opts.assert_called_with(args)
            mock_for_args.assert_not_called()
            mock_commands.assert_not_called()
