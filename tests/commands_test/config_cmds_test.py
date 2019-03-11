from resources_cmd import CommandTestCase

from unittest.mock import call, patch, MagicMock
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
            mock_candidates.fs_path.return_value = ('foo', 'bar', 'baz')
            self.assertEqual(RcCmd.completion_candidates(['rc', 'hey', 'ho'], 1), ('foo', 'bar', 'baz'))
            mock_candidates.fs_path.assert_called_once_with('hey', base=os.path.dirname(self.mock_default_rcfile))
            self.assertEqual(RcCmd.completion_candidates(['rc', 'hey', 'ho'], 2), None)

    def test_completion_candidates_on_any_other_argument(self):
        with patch('stig.commands.base.config.candidates') as mock_candidates:
            mock_candidates.fs_path.return_value = ('foo', 'bar', 'baz')
            self.assertEqual(RcCmd.completion_candidates(['rc', 'hey', 'ho'], 2), None)
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
            mock_candidates.setting_names.return_value = ('foo', 'bar', 'baz')
            self.assertEqual(ResetCmd.completion_candidates(['reset', 'hey', 'ho'], 2), ('foo', 'bar', 'baz'))
            mock_candidates.setting_names.assert_called_once_with()
