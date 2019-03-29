from resources_cmd import CommandTestCase
from stig.utils.cliparser import Args
from stig.completion import Candidates

from asynctest.mock import call, patch
import os


from stig.commands.cli import RcCmd
class TestRcCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.patch('stig.objects',
                   cmdmgr=self.cmdmgr)
        self.mock_path_exists = self.patch('os.path.exists')
        self.mock_rcfile = self.patch('stig.commands.base.config.rcfile')
        self.mock_rcfile.RcFileError = Exception
        self.mock_default_rcfile ='/home/mock/config/default_rcfile'
        self.patch('stig.settings.defaults',
                   DEFAULT_RCFILE=self.mock_default_rcfile)

    async def check_nonexisting_path(self, path, exp_path=None):
        if exp_path is None:
            exp_path = path
        error = 'no such path: %r' % (path,)
        self.mock_rcfile.read.side_effect = self.mock_rcfile.RcFileError(error)
        process = await self.execute(RcCmd, path)
        self.mock_rcfile.read.assert_called_with(exp_path)
        self.assertEqual(process.success, False)
        self.assert_stdout()
        self.assert_stderr('Loading rc file failed: %s' % (error,))

    async def check_existing_path(self, path, exp_path=None):
        if exp_path is None:
            exp_path = path
        self.mock_rcfile.read.return_value = ('mock command 1', 'mock command 2')
        process = await self.execute(RcCmd, path)
        self.mock_rcfile.read.assert_called_with(exp_path)
        self.assertEqual(process.success, True)
        self.assert_stdout()
        self.assert_stderr()
        self.assertEqual(self.cmdmgr.run_async.mock_calls, [call('mock command 1'),
                                                            call('mock command 2')])

    async def test_nonexisting_absolute_path(self):
        await self.check_nonexisting_path('/some/absolute/path')

    async def test_nonexisting_home_path(self):
        await self.check_nonexisting_path('~/absolute/path',
                                          exp_path=os.path.expanduser('~/absolute/path'))

    async def test_nonexisting_local_path(self):
        await self.check_nonexisting_path('./absolute/path')

    async def test_existing_absolute_path(self):
        await self.check_existing_path('/some/absolute/path')

    async def test_existing_home_path(self):
        await self.check_existing_path('~/absolute/path',
                                       exp_path=os.path.expanduser('~/absolute/path'))

    async def test_existing_local_path(self):
        await self.check_existing_path('./absolute/path')

    async def test_existing_relative_path(self):
        self.mock_path_exists.return_value = True
        await self.check_existing_path('relative/path')

    async def test_nonexisting_relative_path(self):
        self.mock_path_exists.return_value = False
        exp_path = os.path.join(os.path.dirname(self.mock_default_rcfile),
                                'relative/path')
        await self.check_existing_path('relative/path', exp_path=exp_path)

    @patch('stig.commands.base.config.candidates')
    async def test_completion_candidates_on_first_argument(self, mock_candidates):
        mock_candidates.fs_path.return_value = Candidates(('a', 'b', 'c'))
        await self.assert_completion_candidates(RcCmd, Args(('rc', 'hey', 'ho'), curarg_index=1),
                                                exp_cands=('a', 'b', 'c'))
        mock_candidates.fs_path.assert_called_once_with('hey', base=os.path.dirname(self.mock_default_rcfile))
        await self.assert_completion_candidates(RcCmd, Args(('rc', 'hey', 'ho'), curarg_index=2),
                                                exp_cands=None)

    @patch('stig.commands.base.config.candidates')
    async def test_completion_candidates_on_any_other_argument(self, mock_candidates):
        mock_candidates.fs_path.return_value = Candidates(('foo', 'bar', 'baz'))
        await self.assert_completion_candidates(RcCmd, Args(('rc', 'hey', 'ho'), curarg_index=2),
                                                exp_cands=None)
        mock_candidates.fs_path.assert_not_called()


from stig.commands.cli import ResetCmd
class TestResetCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.patch('stig.objects',
                   localcfg=self.localcfg,
                   remotecfg=self.remotecfg)

    async def test_unknown_setting(self):
        process = await self.execute(ResetCmd, 'some.string', 'foo.bar')
        self.assertEqual(process.success, False)
        self.assert_stdout()
        self.assert_stderr('reset: Unknown setting: some.string',
                           'reset: Unknown setting: foo.bar')

    async def test_remote_setting(self):
        self.remotecfg['some.string'] = 'foo'
        self.remotecfg['some.number'] = 12
        process = await self.execute(ResetCmd, 'srv.some.string', 'srv.some.number')
        self.assertEqual(process.success, False)
        self.assert_stdout()
        self.assert_stderr('reset: Remote settings cannot be reset: srv.some.string',
                           'reset: Remote settings cannot be reset: srv.some.number')

    async def test_space_separated_arguments(self):
        self.localcfg['some.string'] = 'foo'
        self.localcfg['some.number'] = 12
        process = await self.execute(ResetCmd, 'some.string', 'some.number')
        self.assertEqual(process.success, True)
        self.assertEqual(self.localcfg.reset.mock_calls, [call('some.string'),
                                                     call('some.number')])
        self.assert_stdout()
        self.assert_stderr()

    async def test_comma_separated_arguments(self):
        self.localcfg['some.string'] = 'foo'
        self.localcfg['some.number'] = 12
        process = await self.execute(ResetCmd, 'some.string,some.number')
        self.assertEqual(process.success, True)
        self.assertEqual(self.localcfg.reset.mock_calls, [call('some.string'),
                                                     call('some.number')])
        self.assert_stdout()
        self.assert_stderr()

    @patch('stig.commands.base.config.candidates')
    async def test_completion_candidates(self, mock_candidates):
        mock_candidates.setting_names.return_value = Candidates(('a', 'b', 'c'))
        await self.assert_completion_candidates(ResetCmd, Args(('reset', 'hey', 'ho'), curarg_index=2),
                                                exp_cands=('a', 'b', 'c'))
        mock_candidates.setting_names.assert_called_once_with()


from stig.commands.cli import SetCmd
class TestSetCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.patch('stig.objects',
                   localcfg=self.localcfg,
                   remotecfg=self.remotecfg)

    async def test_unknown_setting(self):
        process = await self.execute(SetCmd, 'foo.bar', '27')
        self.assertEqual(process.success, False)
        self.assert_stdout()
        self.assert_stderr('set: Unknown setting: foo.bar')

    async def test_setting_string(self):
        self.localcfg['some.string'] = 'asdf'
        process = await self.execute(SetCmd, 'some.string', 'bar', 'foo')
        self.assertEqual(process.success, True)
        self.assertEqual(self.localcfg['some.string'], 'bar foo')
        self.assert_stdout()
        self.assert_stderr()

    async def test_setting_integer(self):
        self.localcfg['some.integer'] = 42
        process = await self.execute(SetCmd, 'some.integer', '39')
        self.assertEqual(process.success, True)
        self.assertEqual(self.localcfg['some.integer'], '39')
        self.assert_stdout()
        self.assert_stderr()

    async def test_setting_float(self):
        self.localcfg['some.number'] = 3.7
        process = await self.execute(SetCmd, 'some.number', '39.2')
        self.assertEqual(process.success, True)
        self.assertEqual(self.localcfg['some.number'], '39.2')
        self.assert_stdout()
        self.assert_stderr()

    async def test_adjusting_number(self):
        self.localcfg['some.number'] = 20
        process = await self.execute(SetCmd, 'some.number', '+=15')
        self.assertEqual(process.success, True)
        self.assertEqual(self.localcfg['some.number'], 35)
        self.assert_stdout()
        self.assert_stderr()

        process = await self.execute(SetCmd, 'some.number', '-=45')
        self.assertEqual(process.success, True)
        self.assertEqual(self.localcfg['some.number'], -10)
        self.assert_stdout()
        self.assert_stderr()

    async def test_setting_bool(self):
        self.localcfg['some.boolean'] = 'no'
        process = await self.execute(SetCmd, 'some.boolean', 'yes')
        self.assertEqual(process.success, True)
        self.assertEqual(self.localcfg['some.boolean'], 'yes')
        self.assert_stdout()
        self.assert_stderr()

    async def test_setting_option(self):
        self.localcfg['some.option'] = 'foo bar'
        process = await self.execute(SetCmd, 'some.option', 'red', 'with', 'a', 'hint', 'of', 'yellow')
        self.assertEqual(process.success, True)
        self.assertEqual(self.localcfg['some.option'], 'red with a hint of yellow')
        self.assert_stdout()
        self.assert_stderr()

    async def test_setting_comma_separated_list(self):
        self.localcfg['some.list'] = ('foo', 'bar', 'baz')
        process = await self.execute(SetCmd, 'some.list', 'alice,bob,bert')
        self.assertEqual(process.success, True)
        self.assertEqual(self.localcfg['some.list'], ['alice', 'bob', 'bert'])
        self.assert_stdout()
        self.assert_stderr()

    async def test_setting_space_separated_list(self):
        self.localcfg['some.list'] = ('foo', 'bar', 'baz')
        process = await self.execute(SetCmd, 'some.list', 'alice', 'bert')
        self.assertEqual(process.success, True)
        self.assertEqual(self.localcfg['some.list'], ['alice', 'bert'])
        self.assert_stdout()
        self.assert_stderr()

    async def test_setting_with_eval(self):
        self.localcfg['some.boolean'] = 'false'
        process = await self.execute(SetCmd, 'some.boolean:eval', 'echo', 'true')
        self.assertEqual(process.success, True)
        self.assertEqual(self.localcfg['some.boolean'], 'true')
        self.assert_stdout()
        self.assert_stderr()

        process = await self.execute(SetCmd, 'some.boolean:eval', 'echo false')
        self.assertEqual(process.success, True)
        self.assertEqual(self.localcfg['some.boolean'], 'false')
        self.assert_stdout()
        self.assert_stderr()

    async def test_remote_setting(self):
        self.localcfg['something'] = 'foo'
        self.remotecfg['something'] = 'bar'
        process = await self.execute(SetCmd, 'srv.something', 'baz')
        self.assertEqual(process.success, True)
        self.assertEqual(self.localcfg['something'], 'foo')
        self.remotecfg.update.assert_called_once_with()
        self.remotecfg.set.assert_called_once_with('something', 'baz')
        self.assert_stdout()
        self.assert_stderr()

    async def test_setting_raises_error(self):
        class AngryDict(dict):
            def __contains__(self, name):
                return True
            def __getitem__(self, name):
                return 'Some bullshit value'
            def __setitem__(self, name, value):
                raise ValueError('I hate your values!')
        with patch('stig.objects.localcfg', AngryDict()):
            process = await self.execute(SetCmd, 'some.string', 'bar')
            self.assert_stderr('set: some.string = bar: I hate your values!')

    async def test_no_completion_candidates_if_sort_or_columns_options_given(self):
        for opt in ('--columns', '--sort'):
            await self.assert_completion_candidates(SetCmd, Args(('set', opt, 'name', '_', '_'), curarg_index=3), exp_cands=None)
            await self.assert_completion_candidates(SetCmd, Args(('set', opt, 'name', '_', '_'), curarg_index=4), exp_cands=None)
            await self.assert_completion_candidates(SetCmd, Args(('set', '_', opt, 'name', '_'), curarg_index=1), exp_cands=None)
            await self.assert_completion_candidates(SetCmd, Args(('set', '_', opt, 'name', '_'), curarg_index=4), exp_cands=None)
            await self.assert_completion_candidates(SetCmd, Args(('set', '_', '_', opt, 'name'), curarg_index=1), exp_cands=None)
            await self.assert_completion_candidates(SetCmd, Args(('set', '_', '_', opt, 'name'), curarg_index=2), exp_cands=None)

    @patch('stig.commands.base.config.candidates')
    async def test_completion_candidates_when_completing_setting_names(self, mock_candidates):
        mock_candidates.setting_names.return_value = Candidates(('a', 'b', 'c'))
        await self.assert_completion_candidates(SetCmd, Args(('set', '_'), curarg_index=1), exp_cands=('a', 'b', 'c'))
        await self.assert_completion_candidates(SetCmd, Args(('set', '_', '_'), curarg_index=1), exp_cands=('a', 'b', 'c'))
        await self.assert_completion_candidates(SetCmd, Args(('set', '_', '_', 'z'), curarg_index=1), exp_cands=('a', 'b', 'c'))
        await self.assert_completion_candidates(SetCmd, Args(('set', '_', '_', 'z'), curarg_index=2), exp_cands=None)

    @patch('stig.commands.base.config.candidates')
    async def test_completion_candidates_when_completing_values(self, mock_candidates):
        mock_candidates.setting_names.return_value = Candidates(('foo', 'bar'))
        mock_candidates.setting_values.return_value = Candidates(('a', 'b', 'c'))
        await self.assert_completion_candidates(SetCmd, Args(('set', 'foo', '_'), curarg_index=2), exp_cands=('a', 'b', 'c'))
        await self.assert_completion_candidates(SetCmd, Args(('set', 'bar', '_'), curarg_index=2), exp_cands=('a', 'b', 'c'))

    @patch('stig.commands.base.config.candidates')
    async def test_completion_candidates_when_completing_list_values(self, mock_candidates):
        mock_candidates.setting_names.return_value = Candidates(('foo', 'bar'))
        mock_candidates.setting_values.return_value = Candidates(('a', 'b', 'c'))
        await self.assert_completion_candidates(SetCmd, Args(('set', 'foo', '_', '_', '_'), curarg_index=2), exp_cands=('a', 'b', 'c'))
        await self.assert_completion_candidates(SetCmd, Args(('set', 'bar', '_', '_', '_'), curarg_index=3), exp_cands=('a', 'b', 'c'))


from stig.commands.cli import RateLimitCmd
from asynctest import CoroutineMock
class TestRateLimitCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.patch('stig.objects',
                   srvapi=self.srvapi)

    async def test_call_syntaxes(self):
        _set_limits = CoroutineMock()
        _show_limits = CoroutineMock()
        self.patch(RateLimitCmd, _set_limits=_set_limits, _show_limits=_show_limits)

        await self.execute(RateLimitCmd, 'up', '1Mb', 'limit-rate-up<1k')
        _set_limits.assert_awaited_once_with(['limit-rate-up<1k'], ('up',), '1Mb', adjust=False, quiet=False)
        _show_limits.assert_not_awaited()
        _set_limits.reset_mock() ; _show_limits.reset_mock()

        await self.execute(RateLimitCmd, 'up', '1Mb')
        _set_limits.assert_awaited_once_with([], ('up',), '1Mb', adjust=False, quiet=False)
        _show_limits.assert_not_awaited()
        _set_limits.reset_mock() ; _show_limits.reset_mock()

        await self.execute(RateLimitCmd, 'up')
        _set_limits.assert_not_awaited()
        _show_limits.assert_awaited_once_with([], ('up',))
        _set_limits.reset_mock() ; _show_limits.reset_mock()

        await self.execute(RateLimitCmd, 'up', 'show', 'limit-rate-up<1k')
        _set_limits.assert_not_awaited()
        _show_limits.assert_awaited_once_with(['limit-rate-up<1k'], ('up',))
        _set_limits.reset_mock() ; _show_limits.reset_mock()

    async def test_setting_global_limits(self):
        for direction in ('up', 'dn', 'down'):
            real_dir = {'dn':'down'}.get(direction, direction)
            set_method = 'set_limit_rate_' + real_dir
            adjust_method = 'adjust_limit_rate_' + real_dir

            self.srvapi.settings.forget_calls()
            process = await self.execute(RateLimitCmd, direction, '1Mb', 'global')
            self.assertEqual(process.success, True)
            self.srvapi.settings.assert_called(1, set_method, ('1Mb',), {})
            self.assert_stdout('ratelimit: Global %sload rate limit: None' % real_dir)
            self.assert_stderr()
            self.clear_stdout(); self.clear_stderr()

            self.srvapi.settings.forget_calls()
            process = await self.execute(RateLimitCmd, direction, '+=2MB', 'global')
            self.assertEqual(process.success, True)
            self.srvapi.settings.assert_called(1, adjust_method, ('+2MB',), {})
            self.assert_stdout('ratelimit: Global %sload rate limit: None' % real_dir)
            self.assert_stderr()
            self.clear_stdout(); self.clear_stderr()

            self.srvapi.settings.forget_calls()
            process = await self.execute(RateLimitCmd, direction, '--', '-=10Mb', 'global')
            self.assertEqual(process.success, True)
            self.srvapi.settings.assert_called(1, adjust_method, ('-10Mb',), {})
            self.assert_stdout('ratelimit: Global %sload rate limit: None' % real_dir)
            self.assert_stderr()
            self.clear_stdout(); self.clear_stderr()

            self.srvapi.settings.forget_calls()
            self.srvapi.settings.raises = ValueError('bad value')
            process = await self.execute(RateLimitCmd, direction, 'fooo', 'global')
            self.assertEqual(process.success, False)
            self.assert_stdout()
            self.assert_stderr("ratelimit: bad value: 'fooo'")
            self.clear_stdout(); self.clear_stderr()

    async def test_completion_candidates_directions(self):
        await self.assert_completion_candidates(RateLimitCmd, Args(('ratelimit', ''), curarg_index=1),
                                          exp_cands=('up', 'down'), exp_curarg_seps=(',',))
        await self.assert_completion_candidates(RateLimitCmd, Args(('ratelimit', 'up,'), curarg_index=1),
                                          exp_cands=('down',), exp_curarg_seps=(',',))
        await self.assert_completion_candidates(RateLimitCmd, Args(('ratelimit', 'down,'), curarg_index=1),
                                          exp_cands=('up',), exp_curarg_seps=(',',))
        await self.assert_completion_candidates(RateLimitCmd, Args(('ratelimit', 'dn,'), curarg_index=1),
                                          exp_cands=('up',), exp_curarg_seps=(',',))

        await self.assert_completion_candidates(RateLimitCmd, Args(('ratelimit', ''), curarg_index=1),
                                          exp_cands=('up', 'down'), exp_curarg_seps=(',',))
        await self.assert_completion_candidates(RateLimitCmd, Args(('ratelimit', '', '--quiet'), curarg_index=1),
                                          exp_cands=('up', 'down'), exp_curarg_seps=(',',))
        await self.assert_completion_candidates(RateLimitCmd, Args(('ratelimit', '--quiet', ''), curarg_index=2),
                                          exp_cands=('up', 'down'), exp_curarg_seps=(',',))

    @patch('stig.commands.base.config.candidates')
    async def test_completion_candidates_torrent_filter(self, mock_candidates):
        mock_candidates.torrent_filter.return_value = Candidates(('a', 'b', 'c'))
        await self.assert_completion_candidates(RateLimitCmd, Args(('ratelimit', 'up', '10MB', '_'), curarg_index=3),
                                          exp_cands=('a', 'b', 'c'))
        await self.assert_completion_candidates(RateLimitCmd, Args(('ratelimit', 'up', '10MB', '_', '_'), curarg_index=4),
                                          exp_cands=('a', 'b', 'c'))
        await self.assert_completion_candidates(RateLimitCmd, Args(('ratelimit', 'up', '10MB', '_', '_'), curarg_index=3),
                                          exp_cands=('a', 'b', 'c'))
        await self.assert_completion_candidates(RateLimitCmd, Args(('ratelimit', '-q', 'up', '10MB', '_', '_'), curarg_index=4),
                                          exp_cands=('a', 'b', 'c'))
        await self.assert_completion_candidates(RateLimitCmd, Args(('ratelimit', 'up', '-q', '10MB', '_', '_'), curarg_index=5),
                                          exp_cands=('a', 'b', 'c'))
        await self.assert_completion_candidates(RateLimitCmd, Args(('ratelimit', 'up', '10MB', '-q', '_', '_'), curarg_index=4),
                                          exp_cands=('a', 'b', 'c'))
