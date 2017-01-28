import unittest
from unittest.mock import (patch, mock_open)

from stig.settings import rcfile

_MOCK_CFG = """
# this is a comment
foo bar baz

foo

# this isn't really a command
faboobarbaz

# the end
"""

class TestRcfile(unittest.TestCase):
    def test_ignoring_comments_and_empty_lines(self):
        with patch('builtins.open', mock_open(read_data=_MOCK_CFG)):
            cmds = rcfile.read()
        self.assertEqual(tuple(cmds), ('foo bar baz',
                                       'foo',
                                       'faboobarbaz'))

    def test_FileNotFoundError_with_default_path(self):
        with patch('builtins.open', mock_open(read_data=_MOCK_CFG)) as m:
            m.side_effect = FileNotFoundError
            cmds = rcfile.read()
        self.assertEqual(cmds, ())

    def test_FileNotFoundError_with_user_specified_path(self):
        with patch('builtins.open', mock_open(read_data=_MOCK_CFG)) as m:
            m.side_effect = FileNotFoundError
            with self.assertRaises(rcfile.RcFileError) as cm:
                cmds = rcfile.read('/path/to/nondefault/rc')
            self.assertIn('/path/to/nondefault/rc', str(cm.exception).lower())
            self.assertIn('not found', str(cm.exception).lower())

    def test_PermissionError_with_default_path(self):
        with patch('builtins.open', mock_open(read_data=_MOCK_CFG)) as m:
            m.side_effect = PermissionError
            with self.assertRaises(rcfile.RcFileError) as cm:
                cmds = rcfile.read()
            self.assertIn('read', str(cm.exception).lower())
            self.assertIn('permission', str(cm.exception).lower())

    def test_PermissionError_with_user_specified_path(self):
        with patch('builtins.open', mock_open(read_data=_MOCK_CFG)) as m:
            m.side_effect = PermissionError
            with self.assertRaises(rcfile.RcFileError) as cm:
                cmds = rcfile.read('/path/to/nondefault/rc')
            self.assertIn('read', str(cm.exception).lower())
            self.assertIn('permission', str(cm.exception).lower())
