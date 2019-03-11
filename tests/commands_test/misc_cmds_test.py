from resources_cmd import CommandTestCase


from stig.commands.cli import HelpCmd
class TestHelpCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.patch('stig.commands.cli.HelpCmd',
                   helpmgr=self.helpmgr)

    async def test_no_topic(self):
        process = await self.execute(HelpCmd)
        self.assertEqual(process.success, True)
        self.assert_stdout('Mock help for overview')
        self.assert_stderr()

    async def test_one_topic(self):
        process = await self.execute(HelpCmd, 'foo')
        self.assertEqual(process.success, True)
        self.assert_stdout('Mock help for foo')
        self.assert_stderr()

    async def test_multiple_topics(self):
        process = await self.execute(HelpCmd, 'foo', 'bar')
        self.assertEqual(process.success, True)
        self.assert_stdout('^Mock help for foo$',
                           *(line or '^$' for line in HelpCmd.TOPIC_DELIMITER),
                           '^Mock help for bar$')
        self.assert_stderr()

    async def test_unknown_topic(self):
        process = await self.execute(HelpCmd, 'unknown')
        self.assertEqual(process.success, False)
        self.assert_stdout()
        self.assert_stderr('help: Unknown topic: unknown')

    async def test_known_and_unknown_topic(self):
        process = await self.execute(HelpCmd, 'foo', 'unknown')
        self.assertEqual(process.success, False)
        self.assert_stdout('Mock help for foo')
        self.assert_stderr('help: Unknown topic: unknown')


from stig.commands.cli import SetCmd
class TestSetCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.patch('stig.commands.cli.SetCmd',
                   cfg=self.cfg)

    async def test_unknown_setting(self):
        process = await self.execute(SetCmd, 'foo.bar', '27')
        self.assertEqual(process.success, False)
        self.assert_stdout()
        self.assert_stderr('set: Unknown setting: foo.bar')

    async def test_setting_string(self):
        process = await self.execute(SetCmd, 'some.string', 'bar', 'foo')
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.string'], 'bar foo')
        self.assert_stdout()
        self.assert_stderr()

    async def test_setting_integer(self):
        process = await self.execute(SetCmd, 'some.integer', '39')
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.integer'], '39')
        self.assert_stdout()
        self.assert_stderr()

    async def test_setting_float(self):
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
        process = await self.execute(SetCmd, 'some.boolean', 'yes')
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.boolean'], 'yes')
        self.assert_stdout()
        self.assert_stderr()

    async def test_setting_option(self):
        process = await self.execute(SetCmd, 'some.option', 'red', 'with', 'a', 'hint', 'of', 'yellow')
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.option'], 'red with a hint of yellow')
        self.assert_stdout()
        self.assert_stderr()

    async def test_setting_comma_separated_list(self):
        process = await self.execute(SetCmd, 'some.list', 'alice,bob,bert')
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.list'], ['alice', 'bob', 'bert'])
        self.assert_stdout()
        self.assert_stderr()

    async def test_setting_space_separated_list(self):
        process = await self.execute(SetCmd, 'some.list', 'alice', 'bert')
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.list'], ['alice', 'bert'])
        self.assert_stdout()
        self.assert_stderr()

    async def test_setting_with_eval(self):
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


from stig.commands.cli import RateLimitCmd
from asynctest import CoroutineMock
class TestRateLimitCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.patch('stig.commands.cli.RateLimitCmd',
                   srvapi=self.api)

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

            self.api.settings.forget_calls()
            process = await self.execute(RateLimitCmd, direction, '1Mb', 'global')
            self.assertEqual(process.success, True)
            self.api.settings.assert_called(1, set_method, ('1Mb',), {})
            self.assert_stdout('ratelimit: Global %sload rate limit: None' % real_dir)
            self.assert_stderr()
            self.clear_stdout(); self.clear_stderr()

            self.api.settings.forget_calls()
            process = await self.execute(RateLimitCmd, direction, '+=2MB', 'global')
            self.assertEqual(process.success, True)
            self.api.settings.assert_called(1, adjust_method, ('+2MB',), {})
            self.assert_stdout('ratelimit: Global %sload rate limit: None' % real_dir)
            self.assert_stderr()
            self.clear_stdout(); self.clear_stderr()

            self.api.settings.forget_calls()
            process = await self.execute(RateLimitCmd, direction, '--', '-=10Mb', 'global')
            self.assertEqual(process.success, True)
            self.api.settings.assert_called(1, adjust_method, ('-10Mb',), {})
            self.assert_stdout('ratelimit: Global %sload rate limit: None' % real_dir)
            self.assert_stderr()
            self.clear_stdout(); self.clear_stderr()

            self.api.settings.forget_calls()
            self.api.settings.raises = ValueError('bad value')
            process = await self.execute(RateLimitCmd, direction, 'fooo', 'global')
            self.assertEqual(process.success, False)
            self.assert_stdout()
            self.assert_stderr("ratelimit: bad value: 'fooo'")
            self.clear_stdout(); self.clear_stderr()
