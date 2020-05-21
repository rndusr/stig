import unittest

from stig.commands import utils


class Test_listify_args(unittest.TestCase):
    def test_list(self):
        self.assertEqual(utils.listify_args(['1', '2', '3']),
                         ['1', '2', '3'])

    def test_string(self):
        self.assertEqual(utils.listify_args('1, 2,3'),
                         ['1', '2', '3'])

    def test_mixed(self):
        self.assertEqual(utils.listify_args(('1, 2', ',3,,  ,')),
                         ['1', '2', '3'])
