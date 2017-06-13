import unittest
from stig.settings.settings import (Settings, ValueBase, StringValue,
                                    IntegerValue, NumberValue, BooleanValue,
                                    PathValue, ListValue, OptionValue)


class TestValueBase(unittest.TestCase):
    def setUp(self):
        class TestValue(ValueBase):
            pass
        self.cls = TestValue
        self.val = self.cls(name='foo', default=(1, 2, 3))
        self.val.set('hello')

    def test_str_from_current_value(self):
        self.assertEqual(self.val.str(), 'hello')

    def test_str_from_default_value(self):
        self.assertEqual(self.val.str(default=True), '(1, 2, 3)')

    def test_str_from_specific_value(self):
        self.assertEqual(self.val.str(['x', 'y', 'z']), "['x', 'y', 'z']")


class TestBooleanValue(unittest.TestCase):
    def setUp(self):
        self.val = BooleanValue(name='foo', default=0)
        self.val.set('true')

    def test_str_from_current_value(self):
        self.assertEqual(self.val.str(), 'enabled')

    def test_str_from_default_value(self):
        self.assertEqual(self.val.str(default=True), 'disabled')

    def test_str_from_specific_valid_value(self):
        self.assertEqual(self.val.str(value='on'), 'enabled')

    def test_str_from_specific_invalid_value(self):
        self.assertEqual(self.val.str(value=('jibber', 'jabber')),
                         "('jibber', 'jabber')")


class TestNumberValue(unittest.TestCase):
    def test_conversion(self):
        for x in (0, 0.0, '0.0', '0', ['0']):
            t = NumberValue(name='test', default=x)
            self.assertIs(type(t.value), type(0.0))
            self.assertEqual(t.value, 0.0)

    def test_relative_change(self):
        t = NumberValue(name='test', default=20)
        t.set('+=1')
        self.assertEqual(t.value, 21)
        t.set('-=20')
        self.assertEqual(t.value, 1)
        t.set('-=20')
        self.assertEqual(t.value, -19)


class TestOptionValue(unittest.TestCase):
    def test_values(self):
        opts = ['apple', 'orange', 'cherry']
        v = OptionValue(name='test', options=opts, default=opts[0])

        for x in ('apple', 'orange', 'cherry'):
            v.set(x)
            self.assertEqual(v.value, x)
            self.assertEqual(v.default, opts[0])

        for x in ('tree', 'car', 'one of us'):
            with self.assertRaises(ValueError) as cm:
                v.set(x)
            self.assertEqual(str(cm.exception),
                             ("test = {}: Must be one of: {}"
                              .format(x,
                                      ', '.join(sorted(opts)))))


class TestListValue(unittest.TestCase):
    def test_sequence_value(self):
        for seq in ([1, 2, 3], (1, 2, 3), {1, 2, 3}):
            v = ListValue(name='test', default=seq)
            self.assertEqual(v.default, [1, 2, 3])

        v.set([1, 2, 3, 4])
        self.assertEqual(v.default, [1, 2, 3])
        self.assertEqual(v.value, [1, 2, 3, 4])

    def test_string_value(self):
        v = ListValue(name='test', default='1, 2, 3')
        self.assertEqual(v.default, ['1', '2', '3'])
        v.set('1, 2, 3, 4')
        self.assertEqual(v.default, ['1', '2', '3'])
        self.assertEqual(v.value, ['1', '2', '3', '4'])

    def test_options(self):
        v = ListValue(name='test', default=[1, 2, 3], options=range(1, 11))
        v.set([4, 5, 6, 1])
        self.assertEqual(v.default, [1, 2, 3])
        self.assertEqual(v.value, [4, 5, 6, 1])

        with self.assertRaises(ValueError) as cm:
            v.set([4, 5, 6, 0])
        self.assertIn('0', str(cm.exception))
        self.assertIn('test', str(cm.exception))
        self.assertIn('invalid', str(cm.exception).lower())

        with self.assertRaises(ValueError) as cm:
            v.set([4, 12, 5, 6, 0])
        self.assertIn('0', str(cm.exception))
        self.assertIn('12', str(cm.exception))
        self.assertIn('test', str(cm.exception))
        self.assertIn('invalid', str(cm.exception).lower())

    def test_str(self):
        v = ListValue(name='test', default=[1, 2, 3], options=range(1, 11))
        self.assertEqual(v.str('foo'), 'foo')
        self.assertEqual(v.str(range(4)), '0, 1, 2, 3')
        self.assertEqual(v.str(['foo', 'bar', 3]), 'foo, bar, 3')
