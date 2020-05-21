import asyncio

import asynctest
from asynctest.mock import call

from resources_cmd import Callback, make_cmdcls
from stig.commands import CmdError, CommandManager, _CommandBase

#import unittest
# from unittest.mock import call


class TestCommandManagerManagement(asynctest.TestCase):
    def setUp(self):
        self.cmdmgr = CommandManager()
        self.cmd_foo = make_cmdcls(name='foo', provides=('cli',))
        self.cmd_bar = make_cmdcls(name='bar', provides=('tui',))
        self.cmd_baz = make_cmdcls(name='baz', provides=('cli', 'tui'))
        for c in (self.cmd_foo, self.cmd_bar, self.cmd_baz):
            self.cmdmgr.register(c)

    def test_metaclass_check(self):
        class InvalidCommandClass():
            pass
        with self.assertRaises(RuntimeError) as cm:
            self.cmdmgr.register(InvalidCommandClass)
        self.assertIn('metaclass', str(cm.exception))
        self.assertIn('CommandMeta', str(cm.exception))

    def test_active_interface(self):
        self.assertEqual(self.cmdmgr.active_interface, None)
        self.cmdmgr.active_interface = 'tui'
        self.assertEqual(self.cmdmgr.active_interface, 'tui')
        self.cmdmgr.active_interface = 'cli'
        self.assertEqual(self.cmdmgr.active_interface, 'cli')
        with self.assertRaises(ValueError) as cm:
            self.cmdmgr.active_interface = 'fooi'
        self.assertIn('fooi', str(cm.exception))
        self.cmdmgr.active_interface = None
        self.assertEqual(self.cmdmgr.active_interface, None)

    def test_temporary_active_interface(self):
        self.assertEqual(self.cmdmgr.active_interface, None)
        with self.cmdmgr.temporary_active_interface('cli'):
            self.assertEqual(self.cmdmgr.active_interface, 'cli')
        self.assertEqual(self.cmdmgr.active_interface, None)

        self.cmdmgr.active_interface = 'tui'
        with self.cmdmgr.temporary_active_interface('cli'):
            self.assertEqual(self.cmdmgr.active_interface, 'cli')
        self.assertEqual(self.cmdmgr.active_interface, 'tui')

    def test_all_commands(self):
        self.assertEqual(set(self.cmdmgr.all_commands),
                         set((self.cmd_foo, self.cmd_bar, self.cmd_baz)))

    def test_active_commands(self):
        self.cmdmgr.active_interface = 'cli'
        self.assertEqual(set(self.cmdmgr.active_commands), set((self.cmd_foo, self.cmd_baz)))
        self.cmdmgr.active_interface = 'tui'
        self.assertEqual(set(self.cmdmgr.active_commands), set((self.cmd_bar, self.cmd_baz)))

    def test_get_cmdcls(self):
        self.cmdmgr.active_interface = 'cli'
        self.assertEqual(self.cmdmgr.get_cmdcls('bar', interface='ACTIVE', exclusive=False),
                         None)  # bar is 'tui' command
        self.assertEqual(self.cmdmgr.get_cmdcls('bar', interface='ANY', exclusive=False),
                         self.cmd_bar)
        self.assertEqual(self.cmdmgr.get_cmdcls('baz', interface='cli', exclusive=True),
                         None)  # baz supports cli but not exclusively

        # Add another 'foo' command for 'tui' (the first one for 'cli' is added in setUp)
        cmd_foo_tui = make_cmdcls(name='foo', provides=('tui',))
        self.cmdmgr.register(cmd_foo_tui)
        self.assertEqual(self.cmdmgr.get_cmdcls('foo', interface='ACTIVE', exclusive=False),
                         self.cmd_foo)
        self.cmdmgr.active_interface = 'tui'
        self.assertEqual(self.cmdmgr.get_cmdcls('foo', interface='ACTIVE', exclusive=False),
                         cmd_foo_tui)

        # Both commands support their interfaces exclusively
        self.assertEqual(self.cmdmgr.get_cmdcls('foo', interface='cli', exclusive=True),
                         self.cmd_foo)
        self.assertEqual(self.cmdmgr.get_cmdcls('foo', interface='tui', exclusive=True),
                         cmd_foo_tui)

        with self.assertRaises(ValueError) as cm:
            self.cmdmgr.get_cmdcls('foo', interface='brain')
        self.assertIn('brain', str(cm.exception))
        self.assertIn('interface', str(cm.exception).lower())


class TestCommandManagerCallsBase(asynctest.ClockedTestCase):
    def setUp(self):
        self.info_handler = Callback()
        self.error_handler = Callback()
        self.cmdmgr = CommandManager(info_handler=self.info_handler,
                                     error_handler=self.error_handler)

        def run_sync(self_, A, B):
            assert isinstance(self_, _CommandBase)
            self_.info(round(int(A) / int(B)))

        async def run_async(self_, A, B):
            assert isinstance(self_, _CommandBase)
            await asyncio.sleep(0)
            self_.info(round(int(A) / int(B)))

        argspecs = ({'names': ('A',), 'type': int, 'description': 'First number'},
                    {'names': ('B',), 'type': int, 'description': 'Second number'})
        self.cmdmgr.register(
            make_cmdcls(name='div', run=run_sync, argspecs=argspecs, provides=('sync',))
        )
        self.cmdmgr.register(
            make_cmdcls(name='div', run=run_async, argspecs=argspecs, provides=('async',))
        )


        def run_sync_CmdError(self_, msg):
            raise CmdError(msg)

        async def run_async_CmdError(self_, msg):
            await asyncio.sleep(0)
            raise CmdError(msg)

        argspecs = ({'names': ('msg',), 'description': 'Error message'},)
        self.cmdmgr.register(
            make_cmdcls(name='error', run=run_sync_CmdError, argspecs=argspecs, provides=('sync',))
        )
        self.cmdmgr.register(
            make_cmdcls(name='error', run=run_async_CmdError, argspecs=argspecs, provides=('async',))
        )


        def run_sync_Exception(self_):
            1/0
        async def run_async_Exception(self_):
            await asyncio.sleep(0)
            1/0
        self.cmdmgr.register(
            make_cmdcls(name='raise', run=run_sync_Exception, argspecs=(), provides=('sync',))
        )
        self.cmdmgr.register(
            make_cmdcls(name='raise', run=run_async_Exception, argspecs=(), provides=('async',))
        )

    async def check(self, result, success, infos=(), errors=()):
        self.assertEqual(result, success)
        self.assertEqual(tuple(self.info_handler.args), infos)
        self.assertEqual(tuple(self.error_handler.args), errors)


class TestCommandManagerCalls_NoException(TestCommandManagerCallsBase):
    def test_run_sync_command_in_sync_context(self):
        self.cmdmgr.active_interface = 'sync'
        success = self.cmdmgr.run_sync('div 20 4')
        self.assertEqual(success, True)
        self.assertEqual(self.info_handler.args, [('div: 5',)])
        self.assertEqual(self.error_handler.args, [])

    def test_run_async_command_in_sync_context(self):
        self.cmdmgr.active_interface = 'async'
        success = self.cmdmgr.run_sync('div 24 4')
        self.assertEqual(success, True)
        self.assertEqual(self.info_handler.args, [('div: 6',)])
        self.assertEqual(self.error_handler.args, [])

    async def test_run_sync_command_in_async_context(self):
        self.cmdmgr.active_interface = 'sync'
        success = await self.cmdmgr.run_async('div 28 4')
        self.assertEqual(success, True)
        self.assertEqual(self.info_handler.args, [('div: 7',)])
        self.assertEqual(self.error_handler.args, [])

    async def test_run_async_command_in_async_context(self):
        self.cmdmgr.active_interface = 'async'
        success = await self.cmdmgr.run_async('div 32 4')
        self.assertEqual(success, True)
        self.assertEqual(self.info_handler.args, [('div: 8',)])
        self.assertEqual(self.error_handler.args, [])


class TestCommandManagerCalls_RaisingCmdError(TestCommandManagerCallsBase):
    def test_run_sync_command_in_sync_context(self):
        self.cmdmgr.active_interface = 'sync'
        success = self.cmdmgr.run_sync('div 1 foo')
        self.assertEqual(success, False)
        self.assertEqual(self.info_handler.args, [])
        self.assertEqual(self.error_handler.args, [("div: Argument B: invalid int value: 'foo'",)])

    def test_run_async_command_in_sync_context(self):
        self.cmdmgr.active_interface = 'async'
        success = self.cmdmgr.run_sync('div 1 foo')
        self.assertEqual(success, False)
        self.assertEqual(self.info_handler.args, [])
        self.assertEqual(self.error_handler.args, [("div: Argument B: invalid int value: 'foo'",)])

    async def test_run_sync_command_in_async_context(self):
        self.cmdmgr.active_interface = 'sync'
        success = self.cmdmgr.run_sync('div 1 foo')
        self.assertEqual(success, False)
        self.assertEqual(self.info_handler.args, [])
        self.assertEqual(self.error_handler.args, [("div: Argument B: invalid int value: 'foo'",)])

    async def test_run_async_command_in_async_context(self):
        self.cmdmgr.active_interface = 'async'
        success = await self.cmdmgr.run_async('div 1 foo')
        self.assertEqual(success, False)
        self.assertEqual(self.info_handler.args, [])
        self.assertEqual(self.error_handler.args, [("div: Argument B: invalid int value: 'foo'",)])


class TestCommandManagerCalls_RaisingException(TestCommandManagerCallsBase):
    def test_run_sync_command_in_sync_context(self):
        self.cmdmgr.active_interface = 'sync'
        with self.assertRaises(ZeroDivisionError):
            self.cmdmgr.run_sync('div 1 0')
        self.assertEqual(self.info_handler.calls, 0)
        self.assertEqual(self.error_handler.calls, 0)

    def test_run_async_command_in_sync_context(self):
        self.cmdmgr.active_interface = 'async'
        with self.assertRaises(ZeroDivisionError):
            self.cmdmgr.run_sync('div 1 0')
        self.assertEqual(self.info_handler.calls, 0)
        self.assertEqual(self.error_handler.calls, 0)

    async def test_run_sync_command_in_async_context(self):
        self.cmdmgr.active_interface = 'sync'
        with self.assertRaises(ZeroDivisionError):
            await self.cmdmgr.run_async('div 1 0')
        self.assertEqual(self.info_handler.calls, 0)
        self.assertEqual(self.error_handler.calls, 0)

    async def test_run_async_command_in_async_context(self):
        self.cmdmgr.active_interface = 'async'
        with self.assertRaises(ZeroDivisionError):
            await self.cmdmgr.run_async('div 1 0')
        self.assertEqual(self.info_handler.calls, 0)
        self.assertEqual(self.error_handler.calls, 0)


class TestCommandManagerCalls_UnknownCommand(TestCommandManagerCallsBase):
    def test_in_sync_context(self):
        success = self.cmdmgr.run_sync('foo 1 0')
        self.assertEqual(success, False)
        self.assertEqual(self.info_handler.args, [])
        self.assertEqual(self.error_handler.args, [('foo: Unknown command',)])

    async def test_in_async_context(self):
        success = await self.cmdmgr.run_async('foo 1 0')
        self.assertEqual(success, False)
        self.assertEqual(self.info_handler.args, [])
        self.assertEqual(self.error_handler.args, [('foo: Unknown command',)])


class TestCommandManagerCalls_OtherTests(TestCommandManagerCallsBase):
    def test_kwargs_are_forwarded_to_cmd_instance(self):
        kwargs = {'foo': 'bar', 'one': 1}
        def run(self_cmd):
            for k,v in kwargs.items():
                self.assertEqual(getattr(self_cmd, k), v)

        cmdcls = make_cmdcls(name='kwargs-test', run=run, provides=('sync',))
        self.cmdmgr.register(cmdcls)

        self.cmdmgr.active_interface = 'sync'
        success = self.cmdmgr.run_sync('kwargs-test', **kwargs)
        self.assertEqual(success, True)

    def test_unbalanced_quotes_in_command_line(self):
        success = self.cmdmgr.run_sync('div 12 4 & div 24 "3 | foo')
        self.assertEqual(success, False)
        self.assertEqual(self.info_handler.args, [])
        self.assertEqual(self.error_handler.args, [('No closing quotation',)])


class TestCommandManagerCalls_RunIgnoredCalls(TestCommandManagerCallsBase):
    def setUp(self):
        super().setUp()

        self.mock_gui = asynctest.mock.MagicMock()
        argspecs = ({'names': ('A',), 'type': int, 'description': 'First number'},
                    {'names': ('B',), 'type': int, 'description': 'Second number'})

        def run_add(self_, A, B, _gui=self.mock_gui):
            print('add called with %r, %r' % (A, B))
            _gui.display('Result: %d' % (int(A) + int(B),))
        self.cmdmgr.register(make_cmdcls(name='add', run=run_add, argspecs=argspecs, provides=('gui',)))

        async def run_sub(self_, A, B, _gui=self.mock_gui):
            print('sub called with %r, %r' % (A, B))
            _gui.display('Result: %d' % (int(A) - int(B),))
            await asyncio.sleep(0)
        self.cmdmgr.register(make_cmdcls(name='sub', run=run_sub, argspecs=argspecs, provides=('tui',)))

    def test_run_ignored_sync_calls_sync(self):
        self.cmdmgr.active_interface = 'tui'
        # Make call for active interface
        success = self.cmdmgr.run_sync('sub 12 4')
        self.assertEqual(success, True)
        self.assertEqual(self.mock_gui.display.call_args_list, [call('Result: 8')])
        # Make call for inactive interface
        success = self.cmdmgr.run_sync('add 12 4')
        self.assertEqual(success, True)
        self.assertEqual(self.mock_gui.display.call_args_list, [call('Result: 8')])
        # Run call for inactive interface
        with self.cmdmgr.temporary_active_interface('gui'):
            success = self.cmdmgr.run_ignored_calls_sync('add')
            self.assertEqual(success, True)
        self.assertEqual(self.mock_gui.display.call_args_list, [call('Result: 8'), call('Result: 16')])
        # Call for inactive interface was consumed
        with self.cmdmgr.temporary_active_interface('gui'):
            success = self.cmdmgr.run_ignored_calls_sync('add')
            self.assertEqual(success, False)
        self.assertEqual(self.mock_gui.display.call_args_list, [call('Result: 8'), call('Result: 16')])
        # Unknown commands are ignored
        success = self.cmdmgr.run_ignored_calls_sync('foo')
        self.assertEqual(success, False)

    async def test_run_ignored_sync_calls_async(self):
        self.cmdmgr.active_interface = 'gui'
        # Make call for active interface
        success = await self.cmdmgr.run_async('add 12 4')
        self.assertEqual(success, True)
        self.assertEqual(self.mock_gui.display.call_args_list, [call('Result: 16')])
        # Make call for inactive interface
        success = await self.cmdmgr.run_async('sub 12 4')
        self.assertEqual(success, True)
        self.assertEqual(self.mock_gui.display.call_args_list, [call('Result: 16')])
        # Run call for inactive interface
        with self.cmdmgr.temporary_active_interface('tui'):
            success = await self.cmdmgr.run_ignored_calls_async('sub')
            self.assertEqual(success, True)
        self.assertEqual(self.mock_gui.display.call_args_list, [call('Result: 16'), call('Result: 8')])
        # Call for inactive interface was consumed
        with self.cmdmgr.temporary_active_interface('tui'):
            success = self.cmdmgr.run_ignored_calls_sync('sub')
            self.assertEqual(success, False)
        self.assertEqual(self.mock_gui.display.call_args_list, [call('Result: 16'), call('Result: 8')])
        # Unknown commands are ignored
        success = self.cmdmgr.run_ignored_calls_sync('foo')
        self.assertEqual(success, False)


class TestCommandManagerChainedCalls(TestCommandManagerCallsBase):
    def setUp(self):
        super().setUp()
        self.true_cb = Callback()
        self.false_cb = Callback()

        def true_run(self_, *args, **kwargs):
            assert args is ()
            self.true_cb(**kwargs)

        def false_run(self_, *args, **kwargs):
            assert args is ()
            self.false_cb(**kwargs)
            raise CmdError()

        args = ({'names': ('-a',), 'action': 'store_true', 'description': 'A args'},
                {'names': ('-b',), 'action': 'store_true', 'description': 'B args'},
                {'names': ('-c',), 'action': 'store_true', 'description': 'C args'})
        true_cmd = make_cmdcls(name='true', run=true_run, argspecs=args, provides=('T',))
        false_cmd = make_cmdcls(name='false', run=false_run, argspecs=args, provides=('F',))
        self.cmdmgr.register(true_cmd)
        self.cmdmgr.register(false_cmd)

    async def assert_success(self, cmdchain):
        success = self.cmdmgr.run_sync(cmdchain)
        self.assertEqual(success, True)
        success = await self.cmdmgr.run_async(cmdchain)
        self.assertEqual(success, True)

    async def assert_failure(self, cmdchain, infos=(), errors=()):
        success = self.cmdmgr.run_sync(cmdchain)
        self.assertEqual(success, False)
        if infos: self.assertEqual(self.info_handler.args, list(infos))
        if errors: self.assertEqual(self.error_handler.args, list(errors))
        self.info_handler.reset()
        self.error_handler.reset()
        success = await self.cmdmgr.run_async(cmdchain)
        self.assertEqual(success, False)
        if infos: self.assertEqual(self.info_handler.args, list(infos))
        if errors: self.assertEqual(self.error_handler.args, list(errors))

    async def test_cmdchain_formats(self):
        await self.assert_success('true ; true')
        await self.assert_failure('true ; false')
        await self.assert_success([['true'], ';', ['true']])
        await self.assert_failure([['true'], ';', ['false']])

    async def test_empty_cmdchain(self):
        await self.assert_success('')
        await self.assert_success([])
        await self.assert_success([[], []])

    async def test_valid_cmdchain(self):
        await self.assert_success([['false'], ';', ['true']])
        await self.assert_success([['false'], ['true']])
        await self.assert_success((['true'], '&', ['true']))
        await self.assert_success([['false'], '|', ('true',)])

        await self.assert_failure([('true',), ';', ['false']])
        await self.assert_failure([('true',), ('false',)])
        await self.assert_failure((('true',), '&', ('false',)))
        await self.assert_failure([['false'], '|', ['false']])

    async def test_trailing_operator(self):
        await self.assert_failure('true ; false &')
        await self.assert_success([('false',), ';', ('true',), '|'])


    async def run_testcases(self, testcases, checkfunc):
        # Run each test in list format and in string format
        for cmdchain, kwargs in testcases:
            await checkfunc(cmdchain, **kwargs)
            cmdchain_str = ' '.join(cmd if isinstance(cmd, str) else ' '.join(cmd)
                                    for cmd in cmdchain)
            await checkfunc(cmdchain_str, **kwargs)

    async def test_consecutive_operators(self):
        async def assert_consecutive_ops(cmdchain, op1, op2):
            self.error_handler.reset()
            self.cmdmgr.run_sync(cmdchain)
            self.assertEqual(self.error_handler.args,
                             [('Consecutive operators: %s %s' % (op1, op2),)])
            self.error_handler.reset()
            await self.cmdmgr.run_async(cmdchain)
            self.assertEqual(self.error_handler.args,
                             [('Consecutive operators: %s %s' % (op1, op2),)])

        testcases = (
            ([['true'], ';', ';', ['false']], {'op1': ';', 'op2': ';'}),
            ([['true'], '&', '&', ['false']], {'op1': '&', 'op2': '&'}),
            ([['false'], '|', '|', ['true']], {'op1': '|', 'op2': '|'}),

            ([['true'], ';', '&', ['false']], {'op1': ';', 'op2': '&'}),
            ([['true'], '&', '|', ['false']], {'op1': '&', 'op2': '|'}),
            ([['false'], '|', ';', ['true']], {'op1': '|', 'op2': ';'}),
            ([['false'], ';', '|', ['false']], {'op1': ';', 'op2': '|'}),
        )
        await self.run_testcases(testcases, assert_consecutive_ops)

    async def test_final_process_determines_overall_success(self):
        async def do_test(cmdchain, success):
            result = self.cmdmgr.run_sync(cmdchain)
            self.assertEqual(result, success)
            result = await self.cmdmgr.run_async(cmdchain)
            self.assertEqual(result, success)

        testcases = (
            ([['true'], ';', ['true']], {'success': True}),
            ([['false'], ';', ['true']], {'success': True}),
            ([['true'], ';', ['false']], {'success': False}),
            ([['false'], ';', ['false']], {'success': False}),

            ([['true'], '&', ['true']], {'success': True}),
            ([['false'], '&', ['true']], {'success': False}),
            ([['true'], '&', ['false']], {'success': False}),
            ([['false'], '&', ['false']], {'success': False}),

            ([['true'], '|', ['true']], {'success': True}),
            ([['false'], '|', ['true']], {'success': True}),
            ([['true'], '|', ['false']], {'success': True}),
            ([['false'], '|', ['false']], {'success': False}),
        )
        await self.run_testcases(testcases, do_test)

    async def test_nonexisting_cmd_in_cmdchain(self):
        async def do_test(cmdchain, success, true_calls=0, false_calls=0, errors=()):
            self.error_handler.reset() ; self.true_cb.reset() ; self.false_cb.reset()
            result = self.cmdmgr.run_sync(cmdchain)
            self.assertEqual(result, success)
            self.assertEqual(self.true_cb.calls, true_calls)
            self.assertEqual(self.false_cb.calls, false_calls)
            self.assertEqual(self.error_handler.args, list(errors))

            self.error_handler.reset() ; self.true_cb.reset() ; self.false_cb.reset()
            result = await self.cmdmgr.run_async(cmdchain)
            self.assertEqual(result, success)
            self.assertEqual(self.true_cb.calls, true_calls)
            self.assertEqual(self.false_cb.calls, false_calls)
            self.assertEqual(self.error_handler.args, list(errors))

        testcases = (
            ([['true'], ';', ['foo'], ';', ['false']],
             {'success': False, 'true_calls': 1, 'false_calls': 1, 'errors': [('foo: Unknown command',)]}),
            ([['true'], '|', ['foo'], '|', ['false']],
             {'success': True, 'true_calls': 1, 'false_calls': 0}),
            ([['true'], '&', ['foo'], '&', ['false']],
             {'success': False, 'true_calls': 1, 'false_calls': 0, 'errors': [('foo: Unknown command',)]}),
            ([['true'], '&', ['foo'], '|', ['false']],
             {'success': False, 'true_calls': 1, 'false_calls': 1, 'errors': [('foo: Unknown command',)]}),
            ([['true'], '&', ['foo'], '|', ['true']],
             {'success': True, 'true_calls': 2, 'false_calls': 0, 'errors': [('foo: Unknown command',)]}),
            ([['false'], '|', ['foo'], '&', ['true']],
             {'success': False, 'true_calls': 0, 'false_calls': 1, 'errors': [('foo: Unknown command',)]}),
            ([['false'], '&', ['foo'], '&', ['true']],
             {'success': False, 'true_calls': 0, 'false_calls': 1}),
            ([['false'], '|', ['foo'], '|', ['true']],
             {'success': True, 'true_calls': 1, 'false_calls': 1, 'errors': [('foo: Unknown command',)]}),
        )
        await self.run_testcases(testcases, do_test)

    async def test_cmd_from_inactive_interface_in_cmdchain(self):
        async def do_test(cmdchain, success, true_calls=0, false_calls=0, errors=()):
            self.error_handler.reset() ; self.true_cb.reset() ; self.false_cb.reset()
            result = self.cmdmgr.run_sync(cmdchain)
            self.assertEqual(result, success)
            self.assertEqual(self.true_cb.calls, true_calls)
            self.assertEqual(self.false_cb.calls, false_calls)
            self.assertEqual(self.error_handler.args, list(errors))

            self.error_handler.reset() ; self.true_cb.reset() ; self.false_cb.reset()
            result = await self.cmdmgr.run_async(cmdchain)
            self.assertEqual(result, success)
            self.assertEqual(self.true_cb.calls, true_calls)
            self.assertEqual(self.false_cb.calls, false_calls)
            self.assertEqual(self.error_handler.args, list(errors))

        # Calls to 'false' are ignored and evaluate to True in the command chain
        self.cmdmgr.active_interface = 'T'
        testcases = (
            [[['true'], ';', ['false']], {'success': True, 'true_calls': 1, 'false_calls': 0}],
            [[['false'], ';', ['true']], {'success': True, 'true_calls': 1, 'false_calls': 0}],
            [[['true'], '&', ['false']], {'success': True, 'true_calls': 1, 'false_calls': 0}],
            [[['false'], '&', ['true']], {'success': True, 'true_calls': 1, 'false_calls': 0}],
            [[['true'], '|', ['false']], {'success': True, 'true_calls': 1, 'false_calls': 0}],
            [[['false'], '|', ['true']], {'success': True, 'true_calls': 0, 'false_calls': 0}],
        )
        await self.run_testcases(testcases, do_test)

        # Calls to 'false' are ignored and evaluate to True in the command chain
        self.cmdmgr.active_interface = 'F'
        testcases = (
            [[['true'], ';', ['false']], {'success': False, 'true_calls': 0, 'false_calls': 1}],
            [[['false'], ';', ['true']], {'success': True, 'true_calls': 0, 'false_calls': 1}],
            [[['true'], '&', ['false']], {'success': False, 'true_calls': 0, 'false_calls': 1}],
            [[['false'], '&', ['true']], {'success': False, 'true_calls': 0, 'false_calls': 1}],
            [[['true'], '|', ['false']], {'success': True, 'true_calls': 0, 'false_calls': 0}],
            [[['false'], '|', ['true']], {'success': True, 'true_calls': 0, 'false_calls': 1}],
        )
        await self.run_testcases(testcases, do_test)


    async def test_cmdchain_with_arguments(self):
        async def do_test(cmdchain, success, true_args=(), false_args=(), errors=()):
            self.error_handler.reset() ; self.true_cb.reset() ; self.false_cb.reset()
            result = self.cmdmgr.run_sync(cmdchain)
            self.assertEqual(result, success)
            self.assertEqual(self.true_cb.kwargs, list(true_args))
            self.assertEqual(self.false_cb.kwargs, list(false_args))
            self.assertEqual(self.error_handler.args, list(errors))

            self.error_handler.reset() ; self.true_cb.reset() ; self.false_cb.reset()
            result = await self.cmdmgr.run_async(cmdchain)
            self.assertEqual(result, success)
            self.assertEqual(self.true_cb.kwargs, list(true_args))
            self.assertEqual(self.false_cb.kwargs, list(false_args))
            self.assertEqual(self.error_handler.args, list(errors))

        testcases = (
            ([['true', '-a'], '&', ['true', '-a', '-b'], '&', ['true', '-a', '-b', '-c']],
             {'success': True,
              'true_args': [{'a': True, 'b': False, 'c': False},
                            {'a': True, 'b': True, 'c': False},
                            {'a': True, 'b': True, 'c': True}]}),
            ([['true', '-a'], '&', ['true', '-a', '-b'], '|', ['true', '-a', '-b', '-c']],
             {'success': True,
              'true_args': [{'a': True, 'b': False, 'c': False},
                            {'a': True, 'b': True, 'c': False}]}),
            ([['true', '-a'], '|', ['true', '-a', '-b'], '|', ['true', '-a', '-b', '-c']],
             {'success': True,
              'true_args': [{'a': True, 'b': False, 'c': False}]}),

            ([['false', '-a'], '|', ['false', '-a', '-b'], '|', ['false', '-a', '-b', '-c']],
             {'success': False,
              'false_args': [{'a': True, 'b': False, 'c': False},
                             {'a': True, 'b': True, 'c': False},
                             {'a': True, 'b': True, 'c': True}]}),
            ([['false', '-a'], '|', ['false', '-a', '-b'], '&', ['false', '-a', '-b', '-c']],
             {'success': False,
              'false_args': [{'a': True, 'b': False, 'c': False},
                             {'a': True, 'b': True, 'c': False}]}),
            ([['false', '-a'], '&', ['false', '-a', '-b'], '&', ['false', '-a', '-b', '-c']],
             {'success': False,
              'false_args': [{'a': True, 'b': False, 'c': False}]}),

            ([['false', '-a'], ';', ['true', '-a', '-b', '-x'], ';', ['true', '-a', '-b', '-c']],
             {'success': True,
              'false_args': [{'a': True, 'b': False, 'c': False}],
              'true_args': [{'a': True, 'b': True, 'c': True}],
              'errors': [('true: Unrecognized arguments: -x',)]}),
        )
        await self.run_testcases(testcases, do_test)
