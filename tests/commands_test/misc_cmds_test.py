from resources_cmd import CommandTestCase

from tctrl.client.errors import ClientError


from tctrl.commands.cli import HelpCmd
class TestHelpCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        HelpCmd.helpmgr = self.helpmgr

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
                           ('INFO', '=+'),  # Topic delimiter
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


from tctrl.commands.cli import ResetCmd
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


from tctrl.commands.cli import SetCmd
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
        self.assertEqual(self.cfg['some.string'].value, 'bar foo')

    async def test_setting_integer(self):
        process = SetCmd(['some.integer', '39'], loop=self.loop)
        await self.finish(process)
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.integer'].value, '39')

    async def test_setting_number(self):
        process = SetCmd(['some.number', '39.2'], loop=self.loop)
        await self.finish(process)
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.number'].value, '39.2')

    async def test_setting_bool(self):
        process = SetCmd(['some.boolean', 'yes'], loop=self.loop)
        await self.finish(process)
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.boolean'].value, 'yes')

    async def test_setting_option(self):
        process = SetCmd(['some.option', 'red', 'with', 'a', 'hint', 'of', 'yellow'], loop=self.loop)
        await self.finish(process)
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.option'].value, 'red with a hint of yellow')

    async def test_setting_comma_separated_list(self):
        process = SetCmd(['some.list', 'alice,bob,bert'], loop=self.loop)
        await self.finish(process)
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.list'].value, ('alice', 'bob', 'bert'))

    async def test_setting_space_separated_list(self):
        process = SetCmd(['some.list', 'alice', 'bert'], loop=self.loop)
        await self.finish(process)
        self.assertEqual(process.success, True)
        self.assertEqual(self.cfg['some.list'].value, ('alice', 'bert'))

    async def test_setting_raises_error(self):
        def sabotaged_set_func(value):
            raise ValueError('value no good: {}'.format(value))
        SetCmd.cfg['some.string'].set = sabotaged_set_func

        process = SetCmd(['some.string', 'bar'], loop=self.loop)
        with self.assertLogs(level='ERROR') as logged:
            await self.finish(process)
        self.assert_logged(logged, ('ERROR', '^value no good: bar$'))
