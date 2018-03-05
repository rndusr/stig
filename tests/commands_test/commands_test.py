import unittest
import asynctest
import asyncio

from stig.commands import (CommandManager, _CommandBase, ExpectedResource,
                           CmdError, CmdArgError, CmdNotFoundError)
from resources_cmd import (make_cmdcls, assertIsException, Callback)


class TestCommand(asynctest.TestCase):
    def setUp(self):
        def run_sync(self_, A, B):
            assert isinstance(self_, _CommandBase)
            self.div_result = A / B
            return True

        async def run_async(self_, A, B):
            assert isinstance(self_, _CommandBase)
            await asyncio.sleep(0, loop=self_.loop)
            self.div_result = A / B
            return True

        argspecs = ({'names': ('A',), 'type': int, 'description': 'First number'},
                    {'names': ('B',), 'type': int, 'description': 'Second number'})

        self.div_sync = make_cmdcls(name='div', run=run_sync, argspecs=argspecs, provides=('sync',))
        self.div_async = make_cmdcls(name='div', run=run_async, argspecs=argspecs, provides=('async',))
        self.div_result = None
        self.cb_success = Callback()
        self.cb_error = Callback()

    @asynctest.ignore_loop
    def test_mandatory_properties(self):
        attrs = {'name': 'foo',
                 'run': lambda self: None,
                 'category': 'catfoo',
                 'provides': ('tui', 'cli'),
                 'description': 'This command is the foo!'}

        for missing_attr in ('name', 'category', 'provides', 'description', 'run'):
            this_attrs = attrs.copy()
            del this_attrs[missing_attr]
            with self.assertRaises(RuntimeError) as cm:
                make_cmdcls(**this_attrs, defaults=False)
            self.assertIn(missing_attr, str(cm.exception))
            self.assertIn('attribute', str(cm.exception).lower())
        # assertRaisesNot
        make_cmdcls(**attrs, defaults=False)

    @asynctest.ignore_loop
    def test_kwargs_become_instance_attributes(self):
        cmdcls = make_cmdcls()
        cmdinst = cmdcls(foo='bar', one=1)
        self.assertEqual(cmdinst.foo, 'bar')
        self.assertEqual(cmdinst.one, 1)

    @asynctest.ignore_loop
    def test_argparser(self):
        argspecs = ({'names': ('ARG1',), 'description': 'First arg'},
                    {'names': ('ARG2',), 'description': 'Second arg'})
        cmdcls = make_cmdcls(argspecs=argspecs)
        self.assertTrue(hasattr(cmdcls, '_argparser'))
        kwargs = vars(cmdcls._argparser.parse_args(['foo', 'bar']))
        self.assertEqual(kwargs, {'ARG1': 'foo', 'ARG2': 'bar'})

        with self.assertRaises(CmdArgError):
            cmdcls._argparser.parse_args(['foo', 'bar', 'baz'])

    @asynctest.ignore_loop
    def test_expected_resource_available_in_run_method(self):
        argspecs = ({'names': ('A',), 'description': 'First number'},
                    {'names': ('B',), 'description': 'Second number'})
        result = None
        def run(self, A, B):
            nonlocal result
            result = self.template.format(number=int(int(A)/int(B)))
            return True
        cmdcls = make_cmdcls(run=run, argspecs=argspecs,
                             template=ExpectedResource)
        cmdcls.template = 'Result: {number}'
        process = cmdcls(['100', '50'])
        self.assertEqual(process.success, True)
        self.assertEqual(result, 'Result: 2')

    @asynctest.ignore_loop
    def test_missing_expected_resource_error(self):
        cmdcls = make_cmdcls(api=ExpectedResource)
        with self.assertRaises(AttributeError) as cm:
            cmdcls().api
        self.assertIn('api', str(cm.exception))
        self.assertIn('resource', str(cm.exception).lower())

    @asynctest.ignore_loop
    def test_names_and_aliases(self):
        cmdcls = make_cmdcls(name='foo', aliases=('bar', 'baz'))
        self.assertEqual(cmdcls.names, ['foo', 'bar', 'baz'])
        cmdcls = make_cmdcls(name='foo')
        self.assertEqual(cmdcls.names, ['foo'])

    @asynctest.ignore_loop
    def test_argparser_error(self):
        process = self.div_sync(['10', '2', '--frobnicate'], loop=None,
                                on_success=self.cb_success, on_error=self.cb_error)

        self.assertEqual(process.finished, True)
        self.assertEqual(process.success, False)
        assertIsException(process.exception, CmdArgError, '--frobnicate')

        self.assertEqual(self.cb_success.calls, 0)
        self.assertEqual(self.cb_error.calls, 1)
        assert self.cb_error.args[0][0] is process.exception, \
            '{!r} is not {!r}'.format(self.cb_error.args[0][0], process.exception)


    ### Test running commands with stopped asyncio loop

    def check(self, process, result, calls_success=0, calls_error=0, exccls=None):
        self.assertEqual(process.finished, True)
        self.assertEqual(process.success, calls_success >= 1)
        if exccls is None:
            self.assertEqual(process.exception, None)
        else:
            self.assertIsInstance(process.exception, exccls)

        self.assertEqual(self.cb_success.calls, calls_success)
        self.assertEqual(self.cb_error.calls, calls_error)
        if calls_success >= 1:
            assert self.cb_success.args[-1][0] is process

        self.assertEqual(self.div_result, result)

    @asynctest.ignore_loop
    def test_run_does_not_raise_exception_with_stopped_loop(self):
        process = self.div_sync(['10', '2'], loop=None,
                                on_success=self.cb_success, on_error=self.cb_error)
        self.check(process, result=5, calls_success=1)

        process = self.div_async(['10', '2'], loop=self.loop,
                                 on_success=self.cb_success, on_error=self.cb_error)
        process.wait_sync()
        self.check(process, result=5, calls_success=2)

    @asynctest.ignore_loop
    def test_run_raises_exception_with_stopped_loop(self):
        process = self.div_sync(['10', '0'], loop=None,
                                on_success=self.cb_success, on_error=self.cb_error)
        self.check(process, result=None, calls_error=1, exccls=ZeroDivisionError)

        process = self.div_async(['10', '0'], loop=self.loop,
                                 on_success=self.cb_success, on_error=self.cb_error)
        process.wait_sync()
        self.check(process, result=None, calls_error=2, exccls=ZeroDivisionError)


    ### Test running commands with running asyncio loop

    async def test_run_does_not_raise_exception_with_running_loop(self):

        process = self.div_sync(['10', '2'], loop=None,
                                on_success=self.cb_success, on_error=self.cb_error)
        self.check(process, result=5, calls_success=1)

        process = self.div_async(['10', '2'], loop=self.loop,
                                 on_success=self.cb_success, on_error=self.cb_error)
        await process.wait_async()
        self.check(process, result=5, calls_success=2)

    @asynctest.ignore_loop
    async def test_run_raises_exception(self):
        process = self.div_sync(['10', '0'], loop=None,
                                on_success=self.cb_success, on_error=self.cb_error)
        self.check(process, result=None, calls_error=1, exccls=ZeroDivisionError)

        process = self.div_async(['10', '0'], loop=self.loop,
                                 on_success=self.cb_success, on_error=self.cb_error)
        await process.wait_async()
        self.check(process, result=None, calls_error=2, exccls=ZeroDivisionError)



class TestCommandManagerManagement(unittest.TestCase):
    def setUp(self):
        # It's ok to use the default loop here because we're not using it in
        # this test class.
        self.cmdmgr = CommandManager(loop=asyncio.get_event_loop())
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
        self.assertIn('InitCommand', str(cm.exception))

    def test_active_interface(self):
        self.assertEqual(self.cmdmgr.active_interface, None)
        self.cmdmgr.active_interface = 'tui'
        self.assertEqual(self.cmdmgr.active_interface, 'tui')
        self.cmdmgr.active_interface = 'cli'
        self.assertEqual(self.cmdmgr.active_interface, 'cli')
        with self.assertRaises(ValueError) as cm:
            self.cmdmgr.active_interface = 'fooi'
        self.assertIn('fooi', str(cm.exception))

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
        self.cmdmgr = CommandManager(loop=self.loop)

        def sync_run(self_, A, B):
            assert isinstance(self_, _CommandBase)
            self.div_result = A / B
            return True

        async def async_run(self_, A, B):
            assert isinstance(self_, _CommandBase)
            await asyncio.sleep(0, loop=self_.loop)
            self.div_result = A / B
            return True

        argspecs = ({'names': ('A',), 'type': int, 'description': 'First number'},
                    {'names': ('B',), 'type': int, 'description': 'Second number'})
        self.cmdmgr.register(
            make_cmdcls(name='div', run=sync_run, argspecs=argspecs, provides=('sync',))
        )
        self.cmdmgr.register(
            make_cmdcls(name='div', run=async_run, argspecs=argspecs, provides=('async',))
        )


        async def async_run_CmdError(self_, msg):
            await asyncio.sleep(0, loop=self_.loop)
            raise CmdError(msg)

        def sync_run_CmdError(self_, msg):
            raise CmdError(msg)

        argspecs = ({'names': ('msg',), 'type': str, 'description': 'Error message'},)
        self.cmdmgr.register(
            make_cmdcls(name='error', run=async_run_CmdError, argspecs=argspecs, provides=('async',))
        )
        self.cmdmgr.register(
            make_cmdcls(name='error', run=sync_run_CmdError, argspecs=argspecs, provides=('sync',))
        )


        async def async_run_Exception(self_):
            await asyncio.sleep(0, loop=self_.loop)
            1/0
        def sync_run_Exception(self_):
            1/0
        self.cmdmgr.register(
            make_cmdcls(name='raise', run=async_run_Exception, argspecs=(), provides=('async',))
        )
        self.cmdmgr.register(
            make_cmdcls(name='raise', run=sync_run_Exception, argspecs=(), provides=('sync',))
        )

        self.cb_error = Callback()
        self.cb_success = Callback()


class TestCommandManagerCalls(TestCommandManagerCallsBase):
    @asynctest.ignore_loop
    def test_run_sync(self):
        for iface in ('sync', 'async'):
            self.cmdmgr.active_interface = iface
            success = self.cmdmgr.run_sync('div 20 4',
                                           on_success=self.cb_success, on_error=self.cb_error)
            self.assertEqual(success, True)
            self.assertEqual(self.cb_success.calls, 1)
            self.assertIsInstance(self.cb_success.args[-1][0], _CommandBase)
            self.assertEqual(self.cb_error.calls, 0)
            self.assertEqual(self.div_result, 5)

            self.cb_success.reset()
            self.cb_error.reset()

    async def test_run_async(self):
        for iface in ('sync', 'async'):
            self.cmdmgr.active_interface = iface
            success = await self.cmdmgr.run_async('div 20 4',
                                                  on_success=self.cb_success, on_error=self.cb_error)
            self.assertEqual(success, True)
            self.assertEqual(self.cb_success.calls, 1)
            self.assertIsInstance(self.cb_success.args[-1][0], _CommandBase)
            self.assertEqual(self.cb_error.calls, 0)
            self.assertEqual(self.div_result, 5)

            self.cb_success.reset()
            self.cb_error.reset()

    @asynctest.ignore_loop
    def test_kwargs_are_forwarded_to_cmd_instance(self):
        kwargs = {'foo': 'bar', 'one': 1}
        def run(self_cmd):
            for k,v in kwargs.items():
                self.assertEqual(getattr(self_cmd, k), v)
            return True

        cmdcls = make_cmdcls(name='kwargs-test', run=run, provides=('sync',))
        self.cmdmgr.register(cmdcls)

        self.cmdmgr.active_interface = 'sync'
        success = self.cmdmgr.run_sync('kwargs-test', **kwargs)
        self.assertEqual(success, True)


    @asynctest.ignore_loop
    def test_sync_command_raises_unexpected_exception(self):
        for iface in ('sync', 'async'):
            self.cmdmgr.active_interface = iface

            # Without error handler
            with self.assertRaises(ZeroDivisionError):
                self.cmdmgr.run_sync('div 1 0')
            self.assertEqual(self.cb_success.calls, 0)
            self.assertEqual(self.cb_error.calls, 0)

            # With error handler (non-CmdErrors are always raised)
            with self.assertRaises(ZeroDivisionError):
                self.cmdmgr.run_sync('div 1 0',
                                     on_success=self.cb_success, on_error=self.cb_error)
            self.assertEqual(self.cb_success.calls, 0)
            self.assertEqual(self.cb_error.calls, 0)

    async def test_async_command_raises_unexpected_exception(self):
        for iface in ('sync', 'async'):
            self.cmdmgr.active_interface = iface

            # Without error handler
            with self.assertRaises(ZeroDivisionError):
                await self.cmdmgr.run_async('div 1 0')
            self.assertEqual(self.cb_success.calls, 0)
            self.assertEqual(self.cb_error.calls, 0)

            # With error handler (non-CmdErrors are always raised)
            with self.assertRaises(ZeroDivisionError):
                await self.cmdmgr.run_async('div 1 0',
                                            on_success=self.cb_success, on_error=self.cb_error)
            self.assertEqual(self.cb_success.calls, 0)
            self.assertEqual(self.cb_error.calls, 0)


    @asynctest.ignore_loop
    def test_sync_command_raises_CmdError(self):
        for iface in ('sync', 'async'):
            self.cmdmgr.active_interface = iface

            # Without error handler
            with self.assertRaises(CmdError) as cm:
                self.cmdmgr.run_sync('error "Oops"')
            self.assertEqual(self.cb_success.calls, 0)
            self.assertEqual(self.cb_error.calls, 0)
            self.assertIn('Oops', str(cm.exception))

            # With error handler
            success = self.cmdmgr.run_sync('error "No!"',
                                           on_success=self.cb_success, on_error=self.cb_error)
            self.assertEqual(success, False)
            self.assertEqual(self.cb_success.calls, 0)
            self.assertEqual(self.cb_error.calls, 1)
            exc = self.cb_error.args[0][0]
            assertIsException(exc, CmdError, 'No!')

            self.cb_success.reset()
            self.cb_error.reset()

    async def test_async_command_raises_CmdError(self):
        for iface in ('sync', 'async'):
            self.cmdmgr.active_interface = iface

            # Without error handler
            with self.assertRaises(CmdError) as cm:
                await self.cmdmgr.run_async('error "Oops"')
            self.assertEqual(self.cb_success.calls, 0)
            self.assertEqual(self.cb_error.calls, 0)
            self.assertIn('Oops', str(cm.exception))

            # With error handler
            success = await self.cmdmgr.run_async('error "No!"',
                                                  on_success=self.cb_success, on_error=self.cb_error)
            self.assertEqual(success, False)
            self.assertEqual(self.cb_success.calls, 0)
            self.assertEqual(self.cb_error.calls, 1)
            exc = self.cb_error.args[0][0]
            assertIsException(exc, CmdError, 'No!')

            self.cb_success.reset()
            self.cb_error.reset()


    @asynctest.ignore_loop
    def test_sync_unknown_command_without_error_handler(self):
        for iface in ('sync', 'async'):
            self.cmdmgr.active_interface = iface
            with self.assertRaises(CmdNotFoundError) as cm:
                self.cmdmgr.run_sync('foo bar baz')
            self.assertEqual(self.cb_success.calls, 0)
            self.assertEqual(self.cb_error.calls, 0)
            assertIsException(cm.exception, CmdError, 'foo')

    async def test_async_unknown_command_without_error_handler(self):
        for iface in ('sync', 'async'):
            self.cmdmgr.active_interface = iface
            with self.assertRaises(CmdNotFoundError) as cm:
                await self.cmdmgr.run_async('foo bar baz')
            self.assertEqual(self.cb_success.calls, 0)
            self.assertEqual(self.cb_error.calls, 0)
            assertIsException(cm.exception, CmdError, 'foo')

    @asynctest.ignore_loop
    def test_sync_unknown_command_with_error_handler(self):
        for iface in ('sync', 'async'):
            self.cmdmgr.active_interface = iface
            success = self.cmdmgr.run_sync('foo',
                                           on_success=self.cb_success, on_error=self.cb_error)
            self.assertEqual(success, False)
            self.assertEqual(self.cb_success.calls, 0)
            self.assertEqual(self.cb_error.calls, 1)
            exc = self.cb_error.args[0][0]
            assertIsException(exc, CmdError, 'foo')

            self.cb_success.reset()
            self.cb_error.reset()

    async def test_async_unknown_command_with_error_handler(self):
        for iface in ('sync', 'async'):
            self.cmdmgr.active_interface = iface
            success = await self.cmdmgr.run_async('foo',
                                                  on_success=self.cb_success, on_error=self.cb_error)
            self.assertEqual(success, False)
            self.assertEqual(self.cb_success.calls, 0)
            self.assertEqual(self.cb_error.calls, 1)
            exc = self.cb_error.args[0][0]
            assertIsException(exc, CmdError, 'foo')

            self.cb_success.reset()
            self.cb_error.reset()


class TestCommandManagerChainedCalls(TestCommandManagerCallsBase):
    def setUp(self):
        super().setUp()
        self.true_cb = Callback()
        self.false_cb = Callback()

        def true_run(self_, *args, **kwargs): self.true_cb(*args, **kwargs) ; return True
        def false_run(self_, *args, **kwargs): self.false_cb(*args, **kwargs) ; raise CmdError('Nope')

        args = ({'names': ('-a',), 'action': 'store_true', 'description': 'A args'},
                {'names': ('-b',), 'action': 'store_true', 'description': 'B args'},
                {'names': ('-c',), 'action': 'store_true', 'description': 'C args'})
        true_cmd = make_cmdcls(name='true', run=true_run, argspecs=args, provides=('T',))
        false_cmd = make_cmdcls(name='false', run=false_run, argspecs=args, provides=('F',))

        self.cmdmgr.register(true_cmd)
        self.cmdmgr.register(false_cmd)

    def assert_success(self, cmdchain):
        success = self.cmdmgr.run_sync(cmdchain, on_success=self.cb_success,
                                       on_error=self.cb_error)
        self.assertEqual(success, True)

    def assert_failure(self, cmdchain):
        success = self.cmdmgr.run_sync(cmdchain, on_success=self.cb_success,
                                       on_error=self.cb_error)
        self.assertEqual(success, False)

    @asynctest.ignore_loop
    def test_empty_cmdchain(self):
        self.assert_success([])
        self.assert_success('')

    @asynctest.ignore_loop
    def test_run_good_parsed_cmdchain(self):
        self.assert_success([['false'], ';', ('true',)])
        self.assert_success([['false'], ['true']])
        self.assert_success((('true',), '&', ['true']))
        self.assert_success(iter([['false'], '|', ['true']]))

        self.assert_failure([['true'], ';', ('false',)])
        self.assert_failure([['true'], ['false']])
        self.assert_failure((['true'], '&', ['false']))
        self.assert_failure((['false'], '|', ['false']))


    def assert_invalid_cmdchain_format(self, cmdchain):
        with self.assertRaises(RuntimeError):
            self.cmdmgr.run_sync(cmdchain)

    @asynctest.ignore_loop
    def test_run_bad_parsed_cmdchain(self):
        self.assert_invalid_cmdchain_format([['true'], ';', 'true'])
        self.assert_invalid_cmdchain_format((('true',), '&', iter(['true'])))
        self.assert_invalid_cmdchain_format((('true',), '&&&', ['true']))


    @asynctest.ignore_loop
    def test_consecutive_operators(self):
        def assert_consecutive_ops(cmdchain, op1, op2):
            with self.assertRaises(CmdError) as cm:
                self.cmdmgr.run_sync(cmdchain)
            self.assertIn('Consecutive operators', str(cm.exception))
            self.assertIn('%s %s' % (op1, op2), str(cm.exception))

        assert_consecutive_ops('true ; ; true', ';', ';')
        assert_consecutive_ops('true ; & true', ';', '&')
        assert_consecutive_ops('true &   | true', '&', '|')
        assert_consecutive_ops([['true'], '&', '|', ['true']], '&', '|')


    @asynctest.ignore_loop
    def test_nonexisting_cmd_in_cmdchain(self):
        def do_test(cmdchain, success, success_calls, error_calls, true_calls, false_calls,
                    true_args, false_args):
            succ = self.cmdmgr.run_sync(cmdchain, on_success=self.cb_success,
                                           on_error=self.cb_error)
            self.assertEqual(succ, success)
            self.assertEqual(self.cb_success.calls, success_calls)
            self.assertEqual(self.cb_error.calls, error_calls)
            self.assertEqual(self.true_cb.calls, true_calls)
            self.assertEqual(self.false_cb.calls, false_calls)
            self.assertEqual(self.true_cb.kwargs, true_args)
            self.assertEqual(self.false_cb.kwargs, false_args)

            self.cb_success.reset()
            self.cb_error.reset()
            self.true_cb.reset()
            self.false_cb.reset()

        do_test('true ; foo', False, 1, 1, 1, 0, [{'a': False, 'b': False, 'c': False}], [])
        do_test('false ; foo', False, 0, 2, 0, 1, [], [{'a': False, 'b': False, 'c': False}])
        do_test('false | foo', False, 0, 2, 0, 1, [], [{'a': False, 'b': False, 'c': False}])
        do_test('false & foo', False, 0, 1, 0, 1, [], [{'a': False, 'b': False, 'c': False}])
        do_test('true & foo', False, 1, 1, 1, 0, [{'a': False, 'b': False, 'c': False}], [])

        do_test('foo & true', False, 0, 1, 0, 0, [], [])
        do_test('foo | false', False, 0, 2, 0, 1, [], [{'a': False, 'b': False, 'c': False}])
        do_test('foo ; true', True, 1, 1, 1, 0, [{'a': False, 'b': False, 'c': False}], [])


    @asynctest.ignore_loop
    def test_only_cmds_from_active_interface_are_called(self):
        def do_test(cmdchain, success, success_calls, error_calls, true_calls, false_calls,
                    true_args, false_args):
            succ = self.cmdmgr.run_sync(cmdchain, on_success=self.cb_success,
                                        on_error=self.cb_error)
            self.assertEqual(succ, success)
            self.assertEqual(self.cb_success.calls, success_calls)
            self.assertEqual(self.cb_error.calls, error_calls)
            self.assertEqual(self.true_cb.calls, true_calls)
            self.assertEqual(self.false_cb.calls, false_calls)
            self.assertEqual(self.true_cb.kwargs, true_args)
            self.assertEqual(self.false_cb.kwargs, false_args)

            self.cb_success.reset()
            self.cb_error.reset()
            self.true_cb.reset()
            self.false_cb.reset()

        # Calls to 'false' are ignored and evaluate to None in the command chain
        self.cmdmgr.active_interface = 'T'
        do_test('true ; false', None, 1, 0, 1, 0, [{'a': False, 'b': False, 'c': False}], [])
        do_test('false ; true', True, 1, 0, 1, 0, [{'a': False, 'b': False, 'c': False}], [])
        do_test('true & false', None, 1, 0, 1, 0, [{'a': False, 'b': False, 'c': False}], [])
        do_test('false & true', None, 0, 0, 0, 0, [], [])
        do_test('true | false', True, 1, 0, 1, 0, [{'a': False, 'b': False, 'c': False}], [])
        do_test('false | true', True, 1, 0, 1, 0, [{'a': False, 'b': False, 'c': False}], [])

        # Calls to 'true' are ignored and evaluate to None in the command chain
        self.cmdmgr.active_interface = 'F'
        do_test('true ; false', False, 0, 1, 0, 1, [], [{'a': False, 'b': False, 'c': False}])
        do_test('false ; true', None, 0, 1, 0, 1, [], [{'a': False, 'b': False, 'c': False}])
        do_test('true & false', None, 0, 0, 0, 0, [], [])
        do_test('false & true', False, 0, 1, 0, 1, [], [{'a': False, 'b': False, 'c': False}])
        do_test('true | false', False, 0, 1, 0, 1, [], [{'a': False, 'b': False, 'c': False}])
        do_test('false | true', None, 0, 1, 0, 1, [], [{'a': False, 'b': False, 'c': False}])


    @asynctest.ignore_loop
    def test_final_process_determines_overall_success(self):
        def do_test(cmdchain, success):
            result = self.cmdmgr.run_sync(cmdchain, on_success=self.cb_success,
                                           on_error=self.cb_error)
            self.assertEqual(result, success)

        do_test([['true'], ';', ['true']], success=True)
        do_test([['false'], ';', ['true']], success=True)
        do_test([['true'], ';', ['false']], success=False)
        do_test([['false'], ';', ['false']], success=False)

        do_test([['true'], '&', ['true']], success=True)
        do_test([['false'], '&', ['true']], success=False)
        do_test([['true'], '&', ['false']], success=False)
        do_test([['false'], '&', ['false']], success=False)

        do_test([['true'], '|', ['true']], success=True)
        do_test([['false'], '|', ['true']], success=True)
        do_test([['true'], '|', ['false']], success=True)
        do_test([['false'], '|', ['false']], success=False)


    @asynctest.ignore_loop
    def test_sync_complete_chain_with_AND_operator(self):
        result = self.cmdmgr.run_sync('true -a  &  true -a -b  &  true -a -b -c',
                                      on_success=self.cb_success, on_error=self.cb_error)
        self.confirm_complete_chain_with_AND_operator(result)

    async def test_async_complete_chain_with_AND_operator(self):
        result = await self.cmdmgr.run_async('true -a  &  true -a -b  &  true -a -b -c',
                                             on_success=self.cb_success, on_error=self.cb_error)
        self.confirm_complete_chain_with_AND_operator(result)

    def confirm_complete_chain_with_AND_operator(self, result):
        self.assertEqual(result, True)
        self.assertEqual(self.cb_success.calls, 3)
        self.assertEqual(self.cb_error.calls, 0)
        self.assertEqual(self.true_cb.calls, 3)
        self.assertEqual(self.true_cb.kwargs, [{'a': True, 'b': False, 'c': False},
                                               {'a': True, 'b': True, 'c': False},
                                               {'a': True, 'b': True, 'c': True}])
        self.assertEqual(self.false_cb.calls, 0)


    @asynctest.ignore_loop
    def test_sync_broken_chain_with_AND_operator(self):
        result = self.cmdmgr.run_sync('true -a  &  false -a -b  &  true -a -b -c',
                                      on_success=self.cb_success, on_error=self.cb_error)
        self.confirm_broken_chain_with_AND_operator(result)

    async def test_async_broken_chain_with_AND_operator(self):
        result = await self.cmdmgr.run_async('true -a  &  false -a -b  &  true -a -b -c',
                                             on_success=self.cb_success, on_error=self.cb_error)
        self.confirm_broken_chain_with_AND_operator(result)

    def confirm_broken_chain_with_AND_operator(self, result):
        self.assertEqual(result, False)
        self.assertEqual(self.cb_success.calls, 1)
        self.assertEqual(self.cb_error.calls, 1)
        self.assertEqual(self.true_cb.calls, 1)
        self.assertEqual(self.true_cb.kwargs, [{'a': True, 'b': False, 'c': False}])
        self.assertEqual(self.false_cb.calls, 1)
        self.assertEqual(self.false_cb.kwargs, [{'a': True, 'b': True, 'c': False}])


    @asynctest.ignore_loop
    def test_sync_complete_chain_with_OR_operator(self):
        result = self.cmdmgr.run_sync('false -a  |  false -a -b  |  true -a -b -c',
                                      on_success=self.cb_success, on_error=self.cb_error)
        self.confirm_complete_chain_with_OR_operator(result)

    async def test_async_complete_chain_with_OR_operator(self):
        result = await self.cmdmgr.run_async('false -a  |  false -a -b  |  true -a -b -c',
                                             on_success=self.cb_success, on_error=self.cb_error)
        self.confirm_complete_chain_with_OR_operator(result)

    def confirm_complete_chain_with_OR_operator(self, result):
        self.assertEqual(result, True)
        self.assertEqual(self.cb_success.calls, 1)
        self.assertEqual(self.cb_error.calls, 2)
        self.assertEqual(self.false_cb.calls, 2)
        self.assertEqual(self.false_cb.kwargs, [{'a': True, 'b': False, 'c': False},
                                                {'a': True, 'b': True, 'c': False}])
        self.assertEqual(self.true_cb.calls, 1)
        self.assertEqual(self.true_cb.kwargs, [{'a': True, 'b': True, 'c': True}])


    @asynctest.ignore_loop
    def test_sync_broken_chain_with_OR_operator(self):
        result = self.cmdmgr.run_sync('false -a  |  true -a -b  |  false -a -b -c',
                                      on_success=self.cb_success, on_error=self.cb_error)
        self.confirm_broken_chain_with_OR_operator(result)

    async def test_async_broken_chain_with_OR_operator(self):
        result = await self.cmdmgr.run_async('false -a  |  true -a -b  |  false -a -b -c',
                                             on_success=self.cb_success, on_error=self.cb_error)
        self.confirm_broken_chain_with_OR_operator(result)

    def confirm_broken_chain_with_OR_operator(self, result):
        self.assertEqual(result, True)
        self.assertEqual(self.cb_success.calls, 1)
        self.assertEqual(self.cb_error.calls, 1)
        self.assertEqual(self.false_cb.calls, 1)
        self.assertEqual(self.false_cb.kwargs, [{'a': True, 'b': False, 'c': False}])
        self.assertEqual(self.true_cb.calls, 1)
        self.assertEqual(self.true_cb.kwargs, [{'a': True, 'b': True, 'c': False}])


class TestCommandManagerResources(TestCommandManagerCallsBase):
    @asynctest.ignore_loop
    def test_adding_resources_to_registered_commands(self):
        self.cmdmgr.register(make_cmdcls(name='foo', numbers=ExpectedResource))
        resource = tuple(range(10))
        self.cmdmgr.resources['numbers'] = resource
        cmdcls = self.cmdmgr.get_cmdcls('foo', interface='ANY')
        self.assertEqual(cmdcls.numbers, resource)

    @asynctest.ignore_loop
    def test_adding_resources_to_new_commands(self):
        resource = tuple(range(10))
        self.cmdmgr.resources['numbers'] = resource
        self.cmdmgr.register(make_cmdcls(name='foo', numbers=ExpectedResource))
        foo = self.cmdmgr.get_cmdcls('foo', interface='ANY')
        self.assertEqual(foo.numbers, resource)

    @asynctest.ignore_loop
    def test_commands_get_only_expected_resources(self):
        resource = [50, 93, -11]
        self.cmdmgr.resources['numberwang'] = resource
        div_sync = self.cmdmgr.get_cmdcls('div', interface='sync')
        div_async = self.cmdmgr.get_cmdcls('div', interface='sync')
        self.assertFalse(hasattr(div_sync, 'numberwang'))
        self.assertFalse(hasattr(div_async, 'numberwang'))

        self.cmdmgr.register(make_cmdcls(name='foo', numberwang=ExpectedResource))
        foo = self.cmdmgr.get_cmdcls('foo', interface='ANY')
        self.assertTrue(hasattr(foo, 'numberwang'))
        self.assertEqual(foo().numberwang, resource)

    @asynctest.ignore_loop
    def test_command_requests_unknown_resource(self):
        resource = [50, 93, -11]
        self.cmdmgr.resources['numberwang'] = resource
        self.cmdmgr.register(make_cmdcls(name='foo', badgerwang=ExpectedResource))
        foo = self.cmdmgr.get_cmdcls('foo', interface='ANY')
        with self.assertRaises(AttributeError) as cm:
            foo().badgerwang
        self.assertIn('badgerwang', str(cm.exception))
        self.assertIn('resource', str(cm.exception).lower())
