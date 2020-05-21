import unittest
from unittest.mock import MagicMock

from stig import utils


class Test_cached_property(unittest.TestCase):
    def test_no_arguments(self):
        foo = MagicMock(return_value='bar')

        class X:
            @utils.cached_property
            def foo(self):
                return foo()
        x = X()
        for _ in range(5):
            self.assertEqual(x.foo, 'bar')
        foo.assert_called_once_with()

    def test_after_creation(self):
        foo = MagicMock(return_value='bar')
        callback = MagicMock()

        class X:
            @utils.cached_property(after_creation=callback)
            def foo(self):
                return foo()
        x = X()
        for _ in range(5):
            self.assertEqual(x.foo, 'bar')
        foo.assert_called_once_with()
        callback.assert_called_once_with(x)
