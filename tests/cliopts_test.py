import unittest

import sys
import importlib


class Test_get_cmds(unittest.TestCase):
    def mock_args(self, args):
        sys.argv = [sys.argv[0]] + args
        global cliopts
        from stig import cliopts
        importlib.reload(cliopts)

    def test_no_commands(self):
        self.mock_args([])
        self.assertEqual(cliopts.get_cmds(), ())

    def test_single_command(self):
        self.mock_args(['hello', 'world'])
        self.assertEqual(cliopts.get_cmds(), (('hello', 'world'),))

    def test_multiple_commands(self):
        self.mock_args(['hello', 'world', ';',
                        'hello', 'universe', 'and', 'subuniverses', ';',
                        'hello', 'hello', ';',
                        ';', ';',
                        'hello', 'goodbye'])
        self.assertEqual(cliopts.get_cmds(), (('hello', 'world'),
                                              ('hello', 'universe', 'and', 'subuniverses'),
                                              ('hello', 'hello'),
                                              ('hello', 'goodbye')))
