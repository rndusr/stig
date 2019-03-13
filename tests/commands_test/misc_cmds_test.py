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
