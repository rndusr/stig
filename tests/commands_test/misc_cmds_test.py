from resources_cmd import CommandTestCase

from stig.client.errors import ClientError


from stig.commands.cli import HelpCmd
class TestHelpCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        HelpCmd.helpmgr = self.helpmgr
        HelpCmd.cfg = self.cfg

    async def test_no_topic(self):
        process = HelpCmd([], loop=self.loop)
        with self.assertLogs(level='INFO') as logged:
            await self.finish(process)
        self.assertEqual(process.success, True)
        self.assert_logged(logged, ('INFO', '^Mock overview'))

    async def test_one_topic(self):
        process = HelpCmd(['foo'], loop=self.loop)
        with self.assertLogs(level='INFO') as logged:
            await self.finish(process)
        self.assertEqual(process.success, True)
        self.assert_logged(logged, ('INFO', '^Mock help for foo'))

    async def test_multiple_topics(self):
        process = HelpCmd(['foo', 'bar'], loop=self.loop)
        with self.assertLogs(level='INFO') as logged:
            await self.finish(process)
        self.assertEqual(process.success, True)
        self.assert_logged(logged,
                           ('INFO', '^Mock help for foo'),
                           ('INFO', ' *'),  # Topic delimiter
                           ('INFO', '-+'),  # Topic delimiter
                           ('INFO', ' *'),  # Topic delimiter
                           ('INFO', '^Mock help for bar'))

    async def test_unknown_topic(self):
        process = HelpCmd(['unknown'], loop=self.loop)
        with self.assertLogs(level='ERROR') as logged:
            await self.finish(process)
        self.assertEqual(process.success, False)
        self.assert_logged(logged, ('ERROR', '^Unknown topic: unknown'))

    async def test_known_and_unknown_topic(self):
        process = HelpCmd(['foo', 'unknown'], loop=self.loop)
        with self.assertLogs(level='ERROR') as logged:
            await self.finish(process)
        self.assertEqual(process.success, False)
        self.assert_logged(logged,
                           ('ERROR', '^Unknown topic: unknown'),
                           ('INFO', '^Mock help for foo'))


from stig.commands.cli import ResetCmd
class TestResetCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        ResetCmd.cfg = self.cfg

    async def test_space_separated_arguments(self):
        process = ResetCmd(['some.string', 'some.number'])
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.string'], None)
        self.assertEqual(self.cfg['some.number'], None)

    async def test_unknown_setting(self):
        with self.assertLogs(level='ERROR') as logged:
            process = ResetCmd(['some.string', 'foo.bar'])
        self.assertEqual(process.success, False)
        self.assertEqual(self.cfg['some.string'], None)
        self.assert_logged(logged, ('ERROR', '^Unknown setting: foo.bar'))


from stig.commands.cli import SetCmd
class TestSetCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        SetCmd.cfg = self.cfg

    async def test_unknown_setting(self):
        process = SetCmd(['foo.bar', '27'], loop=self.loop)
        with self.assertLogs(level='ERROR') as logged:
            await self.finish(process)
        self.assertEqual(process.success, False)
        self.assert_logged(logged, ('ERROR', '^Unknown setting: foo.bar'))

    async def test_setting_string(self):
        process = SetCmd(['some.string', 'bar', 'foo'], loop=self.loop)
        await self.finish(process)
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.string'], 'bar foo')

    async def test_setting_integer(self):
        process = SetCmd(['some.integer', '39'], loop=self.loop)
        await self.finish(process)
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.integer'], '39')

    async def test_setting_number(self):
        process = SetCmd(['some.number', '39.2'], loop=self.loop)
        await self.finish(process)
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.number'], '39.2')

    async def test_adjusting_number(self):
        self.cfg['some.number'] = 20
        process = SetCmd(['some.number', '+=15'], loop=self.loop)
        await self.finish(process)
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.number'], 35)

        process = SetCmd(['some.number', '-=45'], loop=self.loop)
        await self.finish(process)
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.number'], -10)

    async def test_setting_bool(self):
        process = SetCmd(['some.boolean', 'yes'], loop=self.loop)
        await self.finish(process)
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.boolean'], 'yes')

    async def test_setting_option(self):
        process = SetCmd(['some.option', 'red', 'with', 'a', 'hint', 'of', 'yellow'], loop=self.loop)
        await self.finish(process)
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.option'], 'red with a hint of yellow')

    async def test_setting_comma_separated_list(self):
        process = SetCmd(['some.list', 'alice,bob,bert'], loop=self.loop)
        await self.finish(process)
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.list'], ['alice', 'bob', 'bert'])

    async def test_setting_space_separated_list(self):
        process = SetCmd(['some.list', 'alice', 'bert'], loop=self.loop)
        await self.finish(process)
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.list'], ['alice', 'bert'])

    async def test_setting_with_eval(self):
        process = SetCmd(['some.boolean:eval', 'echo', 'true'], loop=self.loop)
        await self.finish(process)
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.boolean'], 'true')

        process = SetCmd(['some.boolean:eval', 'echo false'], loop=self.loop)
        await self.finish(process)
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.boolean'], 'false')

    async def test_setting_raises_error(self):
        class AngryDict(dict):
            def __contains__(self, name):
                return True
            def __getitem__(self, name):
                return 'Some bullshit value'
            def __setitem__(self, name, value):
                raise ValueError('I hate your values!')
        SetCmd.cfg = AngryDict()

        process = SetCmd(['some.string', 'bar'], loop=self.loop)
        with self.assertLogs(level='ERROR') as logged:
            await self.finish(process)
        self.assert_logged(logged, ('ERROR', r"^some.string = bar: I hate your values!$"))


from stig.commands.cli import RateLimitCmd
class TestRateLimitCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        RateLimitCmd.srvapi = self.api

    async def test_setting_global_limits(self):
        for direction in ('up', 'dn', 'down'):
            set_name = 'set_limit_rate_' + {'dn':'down'}.get(direction, direction)
            adjust_name = 'adjust_limit_rate_' + {'dn':'down'}.get(direction, direction)

            self.api.settings.forget_calls()
            process = RateLimitCmd([direction, '1Mb', 'global'], loop=self.loop)
            await self.finish(process)
            self.assertEqual(process.success, True)
            self.api.settings.assert_called(1, set_name, ('1Mb',), {})

            self.api.settings.forget_calls()
            process = RateLimitCmd([direction, '+=2MB', 'global'], loop=self.loop)
            await self.finish(process)
            self.assertEqual(process.success, True)
            self.api.settings.assert_called(1, adjust_name, ('+2MB',), {})

            self.api.settings.forget_calls()
            process = RateLimitCmd([direction, '--', '-=10Mb', 'global'], loop=self.loop)
            await self.finish(process)
            self.assertEqual(process.success, True)
            self.api.settings.assert_called(1, adjust_name, ('-10Mb',), {})

            self.api.settings.forget_calls()
            self.api.settings.raises = ValueError('bad value')
            process = RateLimitCmd([direction, 'fooo', 'global'], loop=self.loop)
            with self.assertLogs(level='ERROR') as logged:
                await self.finish(process)
            self.assertEqual(process.success, False)
            self.assert_logged(logged, ('ERROR', "^bad value: 'fooo'$"))
