import asyncio

import asynctest
from resources_cmd import Callback, make_cmdcls

from stig.commands import CmdArgError, _CommandBase


class TestCommandBase(asynctest.TestCase):
    def setUp(self):
        def run_sync(self_, A, B):
            assert isinstance(self_, _CommandBase)
            self_.info(round(int(A) / int(B)))

        async def run_async(self_, A, B):
            assert isinstance(self_, _CommandBase)
            await asyncio.sleep(0)
            self_.info(round(int(A) / int(B)))

        argspecs = ({'names': ('A',), 'type': int, 'description': 'First number'},
                    {'names': ('B',), 'type': int, 'description': 'Second number'})

        self.div_sync = make_cmdcls(name='div', run=run_sync, argspecs=argspecs, provides=('sync',))
        self.div_async = make_cmdcls(name='div', run=run_async, argspecs=argspecs, provides=('async',))
        self.info_handler = Callback()
        self.error_handler = Callback()

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

    def test_kwargs_become_instance_attributes(self):
        cmdcls = make_cmdcls()
        cmdinst = cmdcls(foo='bar', one=1)
        self.assertEqual(cmdinst.foo, 'bar')
        self.assertEqual(cmdinst.one, 1)

    def test_argparser(self):
        argspecs = ({'names': ('ARG1',), 'description': 'First arg'},
                    {'names': ('ARG2',), 'description': 'Second arg'})
        cmdcls = make_cmdcls(argspecs=argspecs)
        self.assertTrue(hasattr(cmdcls, '_argparser'))
        kwargs = vars(cmdcls._argparser.parse_args(['foo', 'bar']))
        self.assertEqual(kwargs, {'ARG1': 'foo', 'ARG2': 'bar'})

        with self.assertRaises(CmdArgError):
            cmdcls._argparser.parse_args(['foo', 'bar', 'baz'])

    def test_names_and_aliases(self):
        cmdcls = make_cmdcls(name='foo', aliases=('bar', 'baz'))
        self.assertEqual(cmdcls.names, ['foo', 'bar', 'baz'])
        cmdcls = make_cmdcls(name='foo')
        self.assertEqual(cmdcls.names, ['foo'])

    def test_argparser_error(self):
        process = self.div_sync(['10', '2', '--frobnicate'],
                                info_handler=self.info_handler,
                                error_handler=self.error_handler)

        self.assertEqual(process.finished, True)
        self.assertEqual(process.success, False)
        self.assertEqual(self.info_handler.calls, 0)
        self.assertEqual(self.error_handler.calls, 1)
        self.assertEqual(str(self.error_handler.args[0][0]),
                         'div: Unrecognized arguments: --frobnicate')


    def check(self, process, success, infos=(), errors=()):
        self.assertEqual(process.finished, True)
        self.assertEqual(process.success, success)
        self.assertEqual(self.error_handler.args, list(errors))
        self.assertEqual(self.info_handler.args, list(infos))

    # Test running commands with stopped asyncio loop

    def test_run_does_not_raise_exception_in_sync_context(self):
        process = self.div_sync(['10', '2'],
                                info_handler=self.info_handler,
                                error_handler=self.error_handler)
        self.check(process, success=True, infos=[('div: 5',)])

        self.info_handler.reset()
        self.error_handler.reset()

        process = self.div_async(['50', '2'],
                                 info_handler=self.info_handler,
                                 error_handler=self.error_handler)
        process.wait_sync()
        self.check(process, success=True, infos=[('div: 25',)])

    def test_run_raises_CmdError_in_sync_context(self):
        process = self.div_sync(['10', 'foo'],
                                info_handler=self.info_handler,
                                error_handler=self.error_handler)
        self.check(process, success=False, errors=[("div: Argument B: invalid int value: 'foo'",)])

        self.info_handler.reset()
        self.error_handler.reset()

        process = self.div_async(['1', 'bar'],
                                 info_handler=self.info_handler,
                                 error_handler=self.error_handler)
        process.wait_sync()
        self.check(process, success=False, errors=[("div: Argument B: invalid int value: 'bar'",)])

    def test_run_raises_Exception_in_sync_context(self):
        with self.assertRaises(ZeroDivisionError):
            self.div_sync(['10', '0'],
                          info_handler=self.info_handler,
                          error_handler=self.error_handler)
        self.assertEqual(self.info_handler.args, [])
        self.assertEqual(self.error_handler.args, [])

        self.info_handler.reset()
        self.error_handler.reset()

        process = self.div_async(['1', '0'],
                                 info_handler=self.info_handler,
                                 error_handler=self.error_handler)
        with self.assertRaises(ZeroDivisionError):
            process.wait_sync()
        self.assertEqual(self.info_handler.args, [])
        self.assertEqual(self.error_handler.args, [])

    # Test running commands with running asyncio loop

    async def test_run_does_not_raise_exception_in_async_context(self):
        process = self.div_sync(['10', '2'],
                                info_handler=self.info_handler,
                                error_handler=self.error_handler)
        self.check(process, success=True, infos=[('div: 5',)])

        self.info_handler.reset()
        self.error_handler.reset()

        process = self.div_async(['10', '5'],
                                 info_handler=self.info_handler,
                                 error_handler=self.error_handler)
        await process.wait_async()
        self.check(process, success=True, infos=[('div: 2',)])

    async def test_run_raises_CmdError_in_async_context(self):
        process = self.div_sync(['10', 'foo'],
                                info_handler=self.info_handler,
                                error_handler=self.error_handler)
        self.check(process, success=False, errors=[("div: Argument B: invalid int value: 'foo'",)])

        self.info_handler.reset()
        self.error_handler.reset()

        process = self.div_async(['100', 'bar'],
                                 info_handler=self.info_handler,
                                 error_handler=self.error_handler)
        await process.wait_async()
        self.check(process, success=False, errors=[("div: Argument B: invalid int value: 'bar'",)])

    async def test_run_raises_Exception_in_async_context(self):
        with self.assertRaises(ZeroDivisionError):
            self.div_sync(['10', '0'],
                          info_handler=self.info_handler,
                          error_handler=self.error_handler)
        self.assertEqual(self.info_handler.calls, 0)
        self.assertEqual(self.error_handler.calls, 0)
