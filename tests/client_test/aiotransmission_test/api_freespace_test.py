import asynctest
from asynctest import CoroutineMock, Mock, call

from stig.client.aiotransmission.api_freespace import FreeSpaceAPI


class TestFreeSpaceAPI(asynctest.ClockedTestCase):
    async def setUp(self):
        self.space_getter = CoroutineMock()
        self.freespace = FreeSpaceAPI((), self.space_getter, Mock())

    async def test_expected_path_matches(self):
        self.space_getter.return_value = {'path': '/some/path', 'size-bytes': 123}
        self.assertEqual(await self.freespace._get_free_space('/some/path'), 123)
        self.assertEqual(self.space_getter.call_args_list, [call(path='/some/path')])

    async def test_expected_path_mismatches(self):
        self.space_getter.return_value = {'path': '/different/path', 'size-bytes': 123}
        with self.assertRaises(RuntimeError) as cm:
            await self.freespace._get_free_space('/some/path')
        self.assertEqual(str(cm.exception), "Expected path '/some/path', got '/different/path'")
        self.assertEqual(self.space_getter.call_args_list, [call(path='/some/path')])
