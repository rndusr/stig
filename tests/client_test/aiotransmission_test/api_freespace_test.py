import asynctest
from asynctest import CoroutineMock, Mock, call
from types import SimpleNamespace

from stig.client.aiotransmission.api_freespace import FreeSpaceAPI


class TestFreeSpaceAPI(asynctest.ClockedTestCase):
    async def setUp(self):
        self.rpc = SimpleNamespace(free_space=CoroutineMock())
        self.freespace = FreeSpaceAPI((), self.rpc, Mock())

    async def test_expected_path_matches(self):
        self.rpc.free_space.return_value = {'path': '/some/path', 'size-bytes': 123}
        self.assertEqual(await self.freespace.get_free_space('/some/path'), 123)
        self.assertEqual(self.rpc.free_space.call_args_list, [call(path='/some/path')])

    async def test_expected_path_mismatches(self):
        self.rpc.free_space.return_value = {'path': '/different/path', 'size-bytes': 123}
        with self.assertRaises(RuntimeError) as cm:
            await self.freespace.get_free_space('/some/path')
        self.assertEqual(str(cm.exception), "Expected path '/some/path', got '/different/path'")
        self.assertEqual(self.rpc.free_space.call_args_list, [call(path='/some/path')])
