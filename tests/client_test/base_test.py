from types import SimpleNamespace

import asynctest
from asynctest import CoroutineMock, Mock, call

from stig.client.base import FreeSpaceAPIBase
from stig.client.errors import ClientError
from stig.utils.usertypes import Int


class TestFreeSpaceAPI(asynctest.ClockedTestCase):
    async def setUp(self):
        self.get_free_space = CoroutineMock()

        class FreeSpaceAPI(FreeSpaceAPIBase):
            get_free_space = self.get_free_space

        self.path_getters = (Mock(return_value='/foo', name='Mock for /foo'),
                             Mock(return_value='/bar', name='Mock for /bar'))
        rpc = None  # Should not be used in these tests
        self.mock_settings = Mock()
        self.freespace = FreeSpaceAPI(self.path_getters, rpc, self.mock_settings)
        # We need a spec from a callable because blinker does some weird stuff and we get
        # an AttributeError for '__self__' without the spec.  Also, RequestPoller
        # prettifies function calls in the logs, so we need the __qualname__.
        self.update_cb = Mock(spec=lambda self: None, __qualname__='mock_callback')
        self.freespace.on_update(self.update_cb)

    async def test_hooks_into_settings_updates(self):
        self.assertEqual(self.mock_settings.on_update.call_args_list,
                         [call(self.freespace._gather_info_wrapper)])

    async def test_info_is_updated(self):
        self.get_free_space.side_effect = (123, 456)
        await self.freespace._gather_info_wrapper_coro()
        self.assertEqual(self.freespace.info, {
            '/foo': SimpleNamespace(path='/foo', free=123, error=None),
            '/bar': SimpleNamespace(path='/bar', free=456, error=None)
        })
        self.assertEqual(self.update_cb.call_args_list, [call(self.freespace)])

    async def test_free_is_correct_type(self):
        self.get_free_space.side_effect = (123, 456)
        await self.freespace._gather_info_wrapper_coro()
        self.assertIsInstance(self.freespace.info['/foo'].free, Int)
        self.assertIsInstance(self.freespace.info['/bar'].free, Int)

    async def test_update_callback_is_only_called_when_space_changes(self):
        self.get_free_space.side_effect = [123, 456] * 2 + [123000, 456]
        for i in range(2):
            await self.freespace._gather_info_wrapper_coro()
            self.assertEqual(self.freespace.info, {
                '/foo': SimpleNamespace(path='/foo', free=123, error=None),
                '/bar': SimpleNamespace(path='/bar', free=456, error=None)
            })
            self.assertEqual(self.update_cb.call_args_list, [call(self.freespace)])

        await self.freespace._gather_info_wrapper_coro()
        self.assertEqual(self.update_cb.call_args_list, [call(self.freespace), call(self.freespace)])
        self.assertEqual(self.freespace.info, {
            '/foo': SimpleNamespace(path='/foo', free=123000, error=None),
            '/bar': SimpleNamespace(path='/bar', free=456, error=None)
        })

    async def test_path_getter_raises_expected_error(self):
        self.get_free_space.side_effect = (456,)
        self.path_getters[0].side_effect = ClientError('Nah')
        await self.freespace._gather_info_wrapper_coro()
        self.assertEqual(self.freespace.info, {
            '/bar': SimpleNamespace(path='/bar', free=456, error=None)
        })
        self.assertEqual(self.update_cb.call_args_list, [call(self.freespace)])

    async def test_path_getter_raises_unexpected_error(self):
        self.get_free_space.side_effect = (123, 456)
        self.path_getters[1].side_effect = RuntimeError('Argh!')
        with self.assertRaises(RuntimeError):
            await self.freespace._gather_info_wrapper_coro()
        self.assertEqual(self.freespace.info, {})
        self.assertEqual(self.update_cb.call_args_list, [])

    async def test_get_free_space_raises_expected_error(self):
        self.get_free_space.side_effect = (123, ClientError('Nah'))
        await self.freespace._gather_info_wrapper_coro()
        self.assertEqual(self.freespace.info['/foo'], SimpleNamespace(path='/foo', free=123, error=None))
        self.assertEqual(self.freespace.info['/bar'].path, '/bar')
        self.assertIs(self.freespace.info['/bar'].free, None)
        self.assertEqual(str(self.freespace.info['/bar'].error), 'Nah')
        self.assertEqual(self.update_cb.call_args_list, [call(self.freespace)])

        self.get_free_space.side_effect = (ClientError('Nah'), 456)
        await self.freespace._gather_info_wrapper_coro()
        self.assertEqual(self.freespace.info['/foo'].path, '/foo')
        self.assertIs(self.freespace.info['/foo'].free, None)
        self.assertEqual(str(self.freespace.info['/foo'].error), 'Nah')
        self.assertEqual(self.freespace.info['/bar'], SimpleNamespace(path='/bar', free=456, error=None))
        self.assertEqual(self.update_cb.call_args_list, [call(self.freespace), call(self.freespace)])

    async def test_get_free_space_raises_unexpected_error(self):
        self.get_free_space.side_effect = (123, RuntimeError('Nah'))
        with self.assertRaises(RuntimeError):
            await self.freespace._gather_info_wrapper_coro()
        self.assertEqual(self.freespace.info, {})
        self.assertEqual(self.update_cb.call_args_list, [])

        self.get_free_space.side_effect = (RuntimeError('Nah'), 456)
        with self.assertRaises(RuntimeError):
            await self.freespace._gather_info_wrapper_coro()
        self.assertEqual(self.freespace.info, {})
        self.assertEqual(self.update_cb.call_args_list, [])
