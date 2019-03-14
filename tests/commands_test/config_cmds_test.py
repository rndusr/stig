from resources_cmd import CommandTestCase

from unittest.mock import call, patch
import os


from stig.commands.cli import RcCmd
class TestRcCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.patch('stig.commands.cli.RcCmd',
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

    def test_completion_candidates_on_first_argument(self):
        with patch('stig.commands.base.config.candidates') as mock_candidates:
            mock_candidates.fs_path.return_value = ('a', 'b', 'c')
            self.assert_completion_candidates(RcCmd, ['rc', 'hey', 'ho'], 1, ('a', 'b', 'c'))
            mock_candidates.fs_path.assert_called_once_with('hey', base=os.path.dirname(self.mock_default_rcfile))
            self.assert_completion_candidates(RcCmd, ['rc', 'hey', 'ho'], 2, None)

    def test_completion_candidates_on_any_other_argument(self):
        with patch('stig.commands.base.config.candidates') as mock_candidates:
            mock_candidates.fs_path.return_value = ('foo', 'bar', 'baz')
            self.assert_completion_candidates(RcCmd, ['rc', 'hey', 'ho'], 2, None)
            mock_candidates.fs_path.assert_not_called()


from stig.commands.cli import ResetCmd
class TestResetCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.patch('stig.commands.cli.ResetCmd',
                   cfg=self.cfg,
                   srvcfg=self.srvcfg)

    async def test_unknown_setting(self):
        process = await self.execute(ResetCmd, 'some.string', 'foo.bar')
        self.assertEqual(process.success, False)
        self.assert_stdout()
        self.assert_stderr('reset: Unknown setting: some.string',
                           'reset: Unknown setting: foo.bar')

    async def test_remote_setting(self):
        self.srvcfg['some.string'] = 'foo'
        self.srvcfg['some.number'] = 12
        process = await self.execute(ResetCmd, 'srv.some.string', 'srv.some.number')
        self.assertEqual(process.success, False)
        self.assert_stdout()
        self.assert_stderr('reset: Remote settings cannot be reset: srv.some.string',
                           'reset: Remote settings cannot be reset: srv.some.number')

    async def test_space_separated_arguments(self):
        self.cfg['some.string'] = 'foo'
        self.cfg['some.number'] = 12
        process = await self.execute(ResetCmd, 'some.string', 'some.number')
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg.reset.mock_calls, [call('some.string'),
                                                     call('some.number')])
        self.assert_stdout()
        self.assert_stderr()

    async def test_comma_separated_arguments(self):
        self.cfg['some.string'] = 'foo'
        self.cfg['some.number'] = 12
        process = await self.execute(ResetCmd, 'some.string,some.number')
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg.reset.mock_calls, [call('some.string'),
                                                     call('some.number')])
        self.assert_stdout()
        self.assert_stderr()

    def test_completion_candidates(self):
        with patch('stig.commands.base.config.candidates') as mock_candidates:
            mock_candidates.setting_names.return_value = ('a', 'b', 'c')
            self.assert_completion_candidates(ResetCmd, ['reset', 'hey', 'ho'], 2, ('a', 'b', 'c'))
            mock_candidates.setting_names.assert_called_once_with()


from stig.commands.cli import SetCmd
class TestSetCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.patch('stig.commands.cli.SetCmd',
                   cfg=self.cfg,
                   srvcfg=self.srvcfg)

    async def test_unknown_setting(self):
        process = await self.execute(SetCmd, 'foo.bar', '27')
        self.assertEqual(process.success, False)
        self.assert_stdout()
        self.assert_stderr('set: Unknown setting: foo.bar')

    async def test_setting_string(self):
        self.cfg['some.string'] = 'asdf'
        process = await self.execute(SetCmd, 'some.string', 'bar', 'foo')
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.string'], 'bar foo')
        self.assert_stdout()
        self.assert_stderr()

    async def test_setting_integer(self):
        self.cfg['some.integer'] = 42
        process = await self.execute(SetCmd, 'some.integer', '39')
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.integer'], '39')
        self.assert_stdout()
        self.assert_stderr()

    async def test_setting_float(self):
        self.cfg['some.number'] = 3.7
        process = await self.execute(SetCmd, 'some.number', '39.2')
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.number'], '39.2')
        self.assert_stdout()
        self.assert_stderr()

    async def test_adjusting_number(self):
        self.cfg['some.number'] = 20
        process = await self.execute(SetCmd, 'some.number', '+=15')
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.number'], 35)
        self.assert_stdout()
        self.assert_stderr()

        process = await self.execute(SetCmd, 'some.number', '-=45')
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.number'], -10)
        self.assert_stdout()
        self.assert_stderr()

    async def test_setting_bool(self):
        self.cfg['some.boolean'] = 'no'
        process = await self.execute(SetCmd, 'some.boolean', 'yes')
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.boolean'], 'yes')
        self.assert_stdout()
        self.assert_stderr()

    async def test_setting_option(self):
        self.cfg['some.option'] = 'foo bar'
        process = await self.execute(SetCmd, 'some.option', 'red', 'with', 'a', 'hint', 'of', 'yellow')
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.option'], 'red with a hint of yellow')
        self.assert_stdout()
        self.assert_stderr()

    async def test_setting_comma_separated_list(self):
        self.cfg['some.list'] = ('foo', 'bar', 'baz')
        process = await self.execute(SetCmd, 'some.list', 'alice,bob,bert')
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.list'], ['alice', 'bob', 'bert'])
        self.assert_stdout()
        self.assert_stderr()

    async def test_setting_space_separated_list(self):
        self.cfg['some.list'] = ('foo', 'bar', 'baz')
        process = await self.execute(SetCmd, 'some.list', 'alice', 'bert')
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.list'], ['alice', 'bert'])
        self.assert_stdout()
        self.assert_stderr()

    async def test_setting_with_eval(self):
        self.cfg['some.boolean'] = 'false'
        process = await self.execute(SetCmd, 'some.boolean:eval', 'echo', 'true')
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.boolean'], 'true')
        self.assert_stdout()
        self.assert_stderr()

        process = await self.execute(SetCmd, 'some.boolean:eval', 'echo false')
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.boolean'], 'false')
        self.assert_stdout()
        self.assert_stderr()

    async def test_remote_setting(self):
        self.cfg['something'] = 'foo'
        self.srvcfg['something'] = 'bar'
        process = await self.execute(SetCmd, 'srv.something', 'baz')
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['something'], 'foo')
        self.srvcfg.update.assert_called_once_with()
        self.srvcfg.set.assert_called_once_with('something', 'baz')
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
        SetCmd.cfg = AngryDict()
        process = await self.execute(SetCmd, 'some.string', 'bar')
        self.assert_stderr('set: some.string = bar: I hate your values!')

    def test_no_completion_candidates_if_sort_or_columns_options_given(self):
        for opt in ('--columns', '--sort'):
            self.assert_completion_candidates(SetCmd, ['set', opt, 'name', '_', '_'], 3, None)
            self.assert_completion_candidates(SetCmd, ['set', opt, 'name', '_', '_'], 4, None)
            self.assert_completion_candidates(SetCmd, ['set', '_', opt, 'name', '_'], 1, None)
            self.assert_completion_candidates(SetCmd, ['set', '_', opt, 'name', '_'], 4, None)
            self.assert_completion_candidates(SetCmd, ['set', '_', '_', opt, 'name'], 1, None)
            self.assert_completion_candidates(SetCmd, ['set', '_', '_', opt, 'name'], 2, None)

    @patch('stig.commands.base.config.candidates')
    def test_completion_candidates_when_completing_setting_names(self, mock_candidates):
        mock_candidates.setting_names.return_value = ('a', 'b', 'c')
        self.assert_completion_candidates(SetCmd, ['set', '_'], 1, ('a', 'b', 'c'))
        self.assert_completion_candidates(SetCmd, ['set', '_', '_'], 1, ('a', 'b', 'c'))
        self.assert_completion_candidates(SetCmd, ['set', '_', '_', 'z'], 1, ('a', 'b', 'c'))

    @patch('stig.commands.base.config.candidates')
    def test_completion_candidates_when_completing_values(self, mock_candidates):
        mock_candidates.setting_names.return_value = ('foo', 'bar', 'baz')
        mock_candidates.setting_values.return_value = ('a', 'b', 'c')
        self.assert_completion_candidates(SetCmd, ['set', 'foo', '_'], 2, ('a', 'b', 'c'))
        self.assert_completion_candidates(SetCmd, ['set', 'bar', '_'], 2, ('a', 'b', 'c'))
        self.assert_completion_candidates(SetCmd, ['set', 'baz', '_'], 2, ('a', 'b', 'c'))

    @patch('stig.commands.base.config.candidates')
    def test_completion_candidates_when_completing_list_values(self, mock_candidates):
        mock_candidates.setting_names.return_value = ('foo', 'bar', 'baz')
        mock_candidates.setting_values.return_value = ('a', 'b', 'c')
        self.assert_completion_candidates(SetCmd, ['set', 'foo', '_', '_', '_'], 2, ('a', 'b', 'c'))
        self.assert_completion_candidates(SetCmd, ['set', 'bar', '_', '_', '_'], 3, ('a', 'b', 'c'))
        self.assert_completion_candidates(SetCmd, ['set', 'baz', '_', '_', '_'], 4, ('a', 'b', 'c'))
