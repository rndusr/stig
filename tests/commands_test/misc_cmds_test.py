from resources_cmd import CommandTestCase

from stig.commands.cli import HelpCmd


class TestHelpCmd(CommandTestCase):
    def setUp(self):
        super().setUp()
        self.patch('stig.objects',
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
