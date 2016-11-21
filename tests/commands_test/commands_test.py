import unittest
import asynctest
import asyncio

from stig.commands import (CommandManager, InitCommand, _CommandBase,
                            ExpectedResource, CmdError, CmdArgError,
                            CmdNotFoundError)


import logging
log = logging.getLogger(__name__)


def make_cmdcls(defaults=True, **clsattrs):
    assert isinstance(defaults, bool)
    if defaults:
        for k,v in dict(name='foo', category='catfoo',
                        provides=('tui', 'cli'),
                        description='bla').items():
            if k not in clsattrs:
                clsattrs[k] = v

        if 'run' not in clsattrs:
            clsattrs['retval'] = True
            clsattrs['run'] = lambda self: self.retval

    if 'name' in clsattrs:
        clsname = clsattrs['name'].capitalize()+'Command'
    else:
        clsname = 'MockCommand'

    cmdcls = InitCommand(clsname, (), clsattrs)
    assert issubclass(cmdcls, _CommandBase)
    return cmdcls


class Callback():
    def __init__(self):
        self.calls = 0
        self.args = None
        self.kwargs = None

    def __call__(self, *args, **kwargs):
        self.calls += 1
        self.args = args
        self.kwargs = kwargs


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
                cmdcls = make_cmdcls(**this_attrs, defaults=False)
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
    def test_names(self):
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
        self.assertTrue(isinstance(process.exception, CmdArgError))
        self.assertIn('--frobnicate', str(process.exception))

        self.assertEqual(self.cb_success.calls, 0)
        self.assertEqual(self.cb_error.calls, 1)
        assert self.cb_error.args[0] is process.exception

    @asynctest.ignore_loop
    def test_run_does_not_raise_exception(self):
        def check(process, calls_success):
            self.assertEqual(process.finished, True)
            self.assertEqual(process.success, True)
            self.assertEqual(process.exception, None)

            self.assertEqual(self.cb_success.calls, calls_success)
            self.assertEqual(self.cb_error.calls, 0)
            assert self.cb_success.args[0] is process

            self.assertEqual(self.div_result, 5)

        process = self.div_sync(['10', '2'], loop=None,
                                on_success=self.cb_success, on_error=self.cb_error)
        check(process, calls_success=1)

        process = self.div_async(['10', '2'], loop=self.loop,
                                 on_success=self.cb_success, on_error=self.cb_error)
        process.wait()
        check(process, calls_success=2)

    @asynctest.ignore_loop
    def test_run_raises_exception(self):
        def check(process, calls_error):
            self.assertEqual(process.finished, True)
            self.assertEqual(process.success, False)
            self.assertTrue(isinstance(process.exception, ZeroDivisionError))

            self.assertEqual(self.cb_success.calls, 0)
            self.assertEqual(self.cb_error.calls, calls_error)
            assert self.cb_error.args[0] is process.exception

        process = self.div_sync(['10', '0'], loop=None,
                                on_success=self.cb_success, on_error=self.cb_error)
        check(process, calls_error=1)

        process = self.div_async(['10', '0'], loop=self.loop,
                                 on_success=self.cb_success, on_error=self.cb_error)
        process.wait()
        check(process, calls_error=2)

    @asynctest.ignore_loop
    def test_async_catch_exception_with_run_until_complete(self):
        process = self.div_async(['10', '0'], loop=self.loop,
                                 on_success=self.cb_success, on_error=self.cb_error)

        with self.assertRaises(ZeroDivisionError) as cm:
            self.loop.run_until_complete(process.task)

        self.assertEqual(process.finished, True)
        self.assertEqual(process.success, False)
        self.assertTrue(isinstance(process.exception, ZeroDivisionError))

        self.assertEqual(self.cb_success.calls, 0)
        self.assertEqual(self.cb_error.calls, 1)
        assert self.cb_error.args[0] is process.exception


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


        async def async_run_error(self_, msg):
            await asyncio.sleep(0, loop=self_.loop)
            raise CmdError(msg)
        def sync_run_error(self_, msg):
            raise CmdError(msg)
        argspecs = ({'names': ('msg',), 'type': str, 'description': 'Error message'},)
        self.cmdmgr.register(
            make_cmdcls(name='error', run=async_run_error, argspecs=argspecs, provides=('async',))
        )
        self.cmdmgr.register(
            make_cmdcls(name='error', run=sync_run_error, argspecs=argspecs, provides=('sync',))
        )


        async def async_run_exc(self_):
            await asyncio.sleep(0, loop=self_.loop)
            1/0
        def sync_run_exc(self_):
            1/0
        self.cmdmgr.register(
            make_cmdcls(name='raise', run=async_run_exc, argspecs=(), provides=('async',))
        )
        self.cmdmgr.register(
            make_cmdcls(name='raise', run=sync_run_exc, argspecs=(), provides=('sync',))
        )

        self.cb_error = Callback()
        self.cb_success = Callback()


class TestCommandManagerNonblockingCalls(TestCommandManagerCallsBase):
    @asynctest.ignore_loop
    def test_string_args(self):
        self.cmdmgr.active_interface = 'sync'
        success = self.cmdmgr('div 20 4')
        self.assertEqual(success, True)
        self.assertEqual(self.div_result, 5)

    @asynctest.ignore_loop
    def test_sequence_args(self):
        self.cmdmgr.active_interface = 'sync'
        success = self.cmdmgr(['div', '20',  '4'])
        self.assertEqual(success, True)
        self.assertEqual(self.div_result, 5)

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
        success = self.cmdmgr(['kwargs-test'], **kwargs)
        self.assertEqual(success, True)

    @asynctest.ignore_loop
    def test_sync_error(self):
        self.cmdmgr.active_interface = 'sync'
        success = self.cmdmgr('error "Nay!"', on_error=self.cb_error)
        self.assertEqual(success, False)
        self.assertEqual(self.cb_error.calls, 1)
        exc = self.cb_error.args[0]
        self.assertIsInstance(exc, CmdError)
        self.assertEqual(str(exc), "Nay!")

    @asynctest.ignore_loop
    def test_sync_exception(self):
        self.cmdmgr.active_interface = 'sync'
        with self.assertRaises(ZeroDivisionError):
            # Only CommandErrors are passed to on_error
            self.cmdmgr('div 20 0', on_error=self.cb_error)
        self.assertEqual(self.cb_error.calls, 0)

    async def test_async_error(self):
        self.cmdmgr.active_interface = 'async'
        success = self.cmdmgr('error "Oh noes!"', on_error=self.cb_error)

        # Command is still running
        self.assertEqual(success, None)
        self.assertEqual(self.cb_error.calls, 0)

        # Wait for command to finish
        await self.advance(1)
        self.assertEqual(self.cb_error.calls, 1)
        exc = self.cb_error.args[0]
        self.assertIsInstance(exc, CmdError)
        self.assertEqual(str(exc), 'Oh noes!')

    @asynctest.ignore_loop
    def test_sync_unknown_command_without_error_handler(self):
        with self.assertRaises(CmdNotFoundError) as cm:
            self.cmdmgr('foo 20 2')
        self.assertIn('foo', str(cm.exception))

    @asynctest.ignore_loop
    def test_sync_unknown_command_with_error_handler(self):
        success = self.cmdmgr('foo 20 2', on_error=self.cb_error)
        self.assertEqual(success, False)
        self.assertEqual(self.cb_error.calls, 1)
        exc = self.cb_error.args[0]
        self.assertTrue(isinstance(exc, CmdNotFoundError))
        self.assertIn('foo', str(exc))


class TestCommandManagerBlockingCalls(TestCommandManagerCallsBase):
    @asynctest.ignore_loop
    def test_sync(self):
        self.cmdmgr.active_interface = 'sync'
        success = self.cmdmgr('div 20 5', block=True)
        self.assertEqual(success, True)
        self.assertEqual(self.div_result, 4)

    @asynctest.ignore_loop
    def test_sync_exception(self):
        self.cmdmgr.active_interface = 'sync'
        # Only CmdErrors are reported to error handler
        with self.assertRaises(ZeroDivisionError):
            self.cmdmgr('raise', block=True, on_error=self.cb_error)
        self.assertEqual(self.cb_error.calls, 0)

    @asynctest.ignore_loop
    def test_sync_error_with_error_handler(self):
        self.cmdmgr.active_interface = 'sync'
        success = self.cmdmgr('error "Oh noes!"', block=True, on_error=self.cb_error)
        self.assertEqual(success, False)
        self.assertEqual(self.cb_error.calls, 1)
        exc = self.cb_error.args[0]
        self.assertIsInstance(exc, CmdError)
        self.assertEqual(str(exc), 'Oh noes!')

    @asynctest.ignore_loop
    def test_sync_unknown_command_without_error_handler(self):
        self.cmdmgr.active_interface = 'sync'
        with self.assertRaises(CmdNotFoundError) as cm:
            self.cmdmgr('foo 20 10', block=True)
        self.assertEqual(self.cb_error.calls, 0)
        self.assertIn('foo', str(cm.exception))

    @asynctest.ignore_loop
    def test_sync_unknown_command_with_error_handler(self):
        self.cmdmgr.active_interface = 'sync'
        success = self.cmdmgr('foo 20 10', block=True, on_error=self.cb_error)
        self.assertEqual(success, False)
        self.assertEqual(self.cb_error.calls, 1)
        exc = self.cb_error.args[0]
        self.assertIsInstance(exc, CmdNotFoundError)
        self.assertIn('foo', str(exc))

    def test_async(self):
        assert self.loop.is_running() == False
        self.cmdmgr.active_interface = 'async'
        success = self.cmdmgr('div 20 5', block=True, on_error=self.cb_error)
        self.assertEqual(success, True)
        self.assertEqual(self.div_result, 4)
        self.assertEqual(self.cb_error.calls, 0)

    def test_async_exception(self):
        assert self.loop.is_running() == False
        self.cmdmgr.active_interface = 'async'
        with self.assertRaises(ZeroDivisionError):
            self.cmdmgr('div 20 0', block=True)
        self.assertEqual(self.cb_error.calls, 0)

    @asynctest.ignore_loop
    def test_async_error_without_error_handler(self):
        self.cmdmgr.active_interface = 'async'
        assert self.loop.is_running() == False
        with self.assertRaises(CmdError):
            self.cmdmgr('error "Oh noes!"', block=True)
        self.assertEqual(self.cb_error.calls, 0)
        # Exception is lost without handler

    def test_async_error_with_error_handler(self):
        assert self.loop.is_running() == False
        self.cmdmgr.active_interface = 'async'
        success = self.cmdmgr('error "Oh noes!"', block=True, on_error=self.cb_error)
        self.assertEqual(success, False)
        self.assertEqual(self.cb_error.calls, 1)
        exc = self.cb_error.args[0]
        self.assertIsInstance(exc, CmdError)
        self.assertEqual(str(exc), 'Oh noes!')

    @asynctest.ignore_loop
    def test_async_unknown_command_without_error_handler(self):
        assert self.loop.is_running() == False
        self.cmdmgr.active_interface = 'async'
        with self.assertRaises(CmdNotFoundError):
            self.cmdmgr('foo 20 10', block=True)

    @asynctest.ignore_loop
    def test_async_unknown_command_with_error_handler(self):
        assert self.loop.is_running() == False
        self.cmdmgr.active_interface = 'async'
        success = self.cmdmgr('foo 20 10', block=True, on_error=self.cb_error)
        self.assertEqual(success, False)
        self.assertEqual(self.cb_error.calls, 1)
        exc = self.cb_error.args[0]
        self.assertIsInstance(exc, CmdNotFoundError)
        self.assertIn('foo', str(exc))


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
