import unittest
from stig.settings.settings import (Settings, ValueBase, StringValue,
                                    IntegerValue, NumberValue, BooleanValue,
                                    TRUE, FALSE, PathValue, ListValue,
                                    OptionValue)


class TestValueBase(unittest.TestCase):
    def setUp(self):
        class TestValue(ValueBase):
            pass
        self.cls = TestValue
        self.val = self.cls(name='foo', default=(1, 2, 3))
        self.val.set('hello')

    def test_str_from_current_value(self):
        self.assertEqual(self.val.string(), 'hello')

    def test_str_from_default_value(self):
        self.assertEqual(self.val.string(default=True), '(1, 2, 3)')

    def test_str_from_specific_value(self):
        self.assertEqual(self.val.string(['x', 'y', 'z']), "['x', 'y', 'z']")


class TestBooleanValue(unittest.TestCase):
    def test_valid_values(self):
        val = BooleanValue(name='foo')
        for x in TRUE:
            val.set(x)
            self.assertEqual(val.value, True)
        for x in FALSE:
            val.set(x)
            self.assertEqual(val.value, False)

        for x in (True, 1):
            val.set(x)
            self.assertEqual(val.value, True)
        for x in (False, 0):
            val.set(x)
            self.assertEqual(val.value, False)

    def test_invalid_values(self):
        val = BooleanValue(name='foo')
        with self.assertRaises(ValueError) as cm:
            val.set([1, 2, 3])
        self.assertIn('Not a boolean', str(cm.exception))
        self.assertIn('[1, 2, 3]', str(cm.exception))

    def test_str_from_current_value(self):
        val = BooleanValue(name='foo', default=True)
        self.assertEqual(val.string(), 'enabled')

    def test_str_from_default_value(self):
        val = BooleanValue(name='foo', default='no')
        val.set('yes')
        self.assertEqual(val.string(default=True), 'disabled')

    def test_str_from_specific_valid_value(self):
        val = BooleanValue(name='foo', default='off')
        self.assertEqual(val.string(value='on'), 'enabled')


class TestNumberValue(unittest.TestCase):
    def test_valid_values(self):
        val = NumberValue(name='foo', default=10)
        self.assertEqual(val.value, 10)
        for newval,exp in ((0, 0), (0.0, 0), ('0', 0), ('0.0', 0),
                           (0.123456789, 0.123456789), (-1e3, -1000),
                           ('+=7', -993), ('-= 3', -996)):
            val.set(newval)
            self.assertEqual(val.value, exp)

    def test_invalid_values(self):
        val = NumberValue(name='foo')
        with self.assertRaises(ValueError) as cm:
            val.set([123])
        self.assertIn('Not a %s' % val.typename, str(cm.exception))
        self.assertIn('[123]', str(cm.exception))

    def test_str_from_current_value(self):
        val = NumberValue(name='foo', default=42.3456)
        self.assertEqual(val.string(), '42.3456')

    def test_str_from_default_value(self):
        val = NumberValue(name='foo', default=42.3456)
        val.set(-0.00005)
        self.assertEqual(val.string(default=True), '42.3456')

    def test_str_from_specific_value(self):
        val = NumberValue(name='foo', default=42.3456)
        self.assertEqual(val.string(value=-0.123), '-0.123')

    def test_typename(self):
        self.assertEqual(NumberValue(name='foo').typename,
                         'rational number')
        self.assertEqual(NumberValue(name='foo', min=5).typename,
                         'rational number >= 5')
        self.assertEqual(NumberValue(name='foo', max=5).typename,
                         'rational number <= 5')
        self.assertEqual(NumberValue(name='foo', min=-5, max=5).typename,
                         'rational number -5 - 5')

    def test_min(self):
        val = NumberValue(name='foo', min=10)
        with self.assertRaises(ValueError) as cm:
            val.set(9)
        self.assertIn('Too small', str(cm.exception))
        self.assertIn('minimum is 10', str(cm.exception))

        val = NumberValue(name='foo', default=100)
        val.min = 150
        self.assertEqual(val.min, 150)
        self.assertEqual(val.value, 150)
        self.assertEqual(val.default, 150)
        with self.assertRaises(ValueError) as cm:
            val.set(149)
        self.assertIn('Too small', str(cm.exception))
        self.assertIn('minimum is 150', str(cm.exception))

    def test_max(self):
        val = NumberValue(name='foo', max=100)
        with self.assertRaises(ValueError) as cm:
            val.set(100.001)
        self.assertIn('Too big', str(cm.exception))
        self.assertIn('maximum is 100', str(cm.exception))

        val = NumberValue(name='foo', default=100)
        val.max = 50
        self.assertEqual(val.max, 50)
        self.assertEqual(val.value, 50)
        self.assertEqual(val.default, 50)
        with self.assertRaises(ValueError) as cm:
            val.set(51)
        self.assertIn('Too big', str(cm.exception))
        self.assertIn('maximum is 50', str(cm.exception))

    def test_min_bigger_than_max(self):
        with self.assertRaises(ValueError) as cm:
            NumberValue(name='foo', min=100, max=99)
        self.assertIn('minimum must be smaller than or equal to maximum', str(cm.exception))

        val = NumberValue(name='foo')
        val.min = 50
        with self.assertRaises(ValueError) as cm:
            val.max = 49
        self.assertIn('minimum must be smaller than or equal to maximum', str(cm.exception))


class TestIntegerValue(unittest.TestCase):
    def test_valid_values(self):
        val = IntegerValue(name='foo', default=10)
        self.assertEqual(val.value, 10)
        for newval,exp in ((0.3, 0), ('0.2', 0), ('-500', -500)):
            val.set(newval)
            self.assertEqual(val.value, exp)

    def test_invalid_values(self):
        for x in ('x2', range(100)):
            with self.assertRaises(ValueError) as cm:
                IntegerValue(name='foo', default=x)
            self.assertIn('Not a integer number', str(cm.exception))

            val = IntegerValue(name='foo')
            with self.assertRaises(ValueError) as cm:
                val.set(x)
                self.assertIn('Not a %s' % val.typename, str(cm.exception))
                self.assertIn(str(x), str(cm.exception))

    def test_typename(self):
        self.assertEqual(IntegerValue(name='foo').typename,
                         'integer number')
        self.assertEqual(IntegerValue(name='foo', min=5).typename,
                         'integer number >= 5')
        self.assertEqual(IntegerValue(name='foo', max=5).typename,
                         'integer number <= 5')
        self.assertEqual(IntegerValue(name='foo', min=-5, max=5).typename,
                         'integer number -5 - 5')


class TestStringValue(unittest.TestCase):
    def test_typename(self):
        self.assertEqual(StringValue(name='foo').typename,
                         'string')
        self.assertEqual(StringValue(name='foo', minlen=1).typename,
                         'string of at least 1 character')
        self.assertEqual(StringValue(name='foo', maxlen=2).typename,
                         'string of at most 2 characters')
        self.assertEqual(StringValue(name='foo', minlen=5, maxlen=20).typename,
                         'string of 5 to 20 characters')

    def test_valid_values(self):
        val = StringValue(name='foo', default='hello', minlen=3, maxlen=6)
        self.assertEqual(val.value, 'hello')
        for newval in ('hel', 'hell', 'hello', 'helloo'):
            val.set(newval)
            self.assertEqual(val.value, newval)

    def test_invalid_values(self):
        for x in ('he', 'hellooo'):
            def assert_exceptions(string_was_too_short, cm):
                if string_was_too_short:
                    self.assertIn('Too short', str(cm.exception))
                    self.assertIn('minimum length is 3', str(cm.exception))
                else:
                    self.assertIn('Too long', str(cm.exception))
                    self.assertIn('maximum length is 6', str(cm.exception))

            with self.assertRaises(ValueError) as cm:
                StringValue(name='foo', default=x, minlen=3, maxlen=6)
            assert_exceptions(len(x) < 3, cm)

            val = StringValue(name='foo', minlen=3, maxlen=6)
            with self.assertRaises(ValueError) as cm:
                val.set(x)
            assert_exceptions(len(x) < 3, cm)

    def test_minlen_adjusts_value_and_default(self):
        val = StringValue(name='foo', default='1234', minlen=3, maxlen=6)
        val.minlen = 5
        self.assertEqual(val.default, '1234 ')
        self.assertEqual(val.value, '1234 ')

    def test_maxlen_adjusts_value_and_default(self):
        val = StringValue(name='foo', default='123456', minlen=3, maxlen=6)
        val.maxlen = 5
        self.assertEqual(val.default, '12345')
        self.assertEqual(val.value, '12345')


class TestOptionValue(unittest.TestCase):
    def test_valid_values(self):
        opts = ['apple', 'orange', 'cherry']
        val = OptionValue(name='test', options=opts, default=opts[0])

        for x in ('apple', 'orange', 'cherry'):
            val.set(x)
            self.assertEqual(val.value, x)
            self.assertEqual(val.default, opts[0])

    def test_invalid_values(self):
        opts = ['apple', 'orange', 'cherry']
        val = OptionValue(name='test', options=opts)

        for x in ('tree', 'car', 'one of us'):
            with self.assertRaises(ValueError) as cm:
                val.set(x)
            self.assertIn('Not one of', str(cm.exception))
            self.assertIn(', '.join(opts), str(cm.exception))

    def test_options_property(self):
        opts = ['apple', 'orange', 'cherry']
        new_opts = ('tree', 'car', 'one of us')
        val = OptionValue(name='test', options=opts, default=opts[2])
        val.options = new_opts

        for x in opts:
            with self.assertRaises(ValueError) as cm:
                val.set(x)
            self.assertIn('Not one of', str(cm.exception))
            self.assertIn(', '.join(new_opts), str(cm.exception))

        for x in new_opts:
            val.set(x)
            self.assertEqual(val.value, x)
            self.assertEqual(val.default, new_opts[0])


class TestListValue(unittest.TestCase):
    def test_valid_values(self):
        for seq in ([1, 2, 3], (1, 2, 3), {1, 2, 3}):
            v = ListValue(name='test', default=seq)
            self.assertEqual(v.default, [1, 2, 3])

        v.set([1, 2, 3, 4])
        self.assertEqual(v.default, [1, 2, 3])
        self.assertEqual(v.value, [1, 2, 3, 4])

    def test_invalid_values(self):
        for nonseq in (12, object(), print):
            with self.assertRaises(ValueError) as cm:
                ListValue(name='test', default=nonseq)
            self.assertIn('Not a list', str(cm.exception))

    def test_parsing_strings_with_commas(self):
        v = ListValue(name='test', default='1, 2, 3')
        self.assertEqual(v.default, ['1', '2', '3'])
        v.set('1, 2, 3, 4')
        self.assertEqual(v.default, ['1', '2', '3'])
        self.assertEqual(v.value, ['1', '2', '3', '4'])

    def test_string(self):
        v = ListValue(name='test', default=[1, 2, 3])
        self.assertEqual(v.string('foo'), 'foo')
        self.assertEqual(v.string(range(4)), '0, 1, 2, 3')
        self.assertEqual(v.string(['foo', 'bar', 3]), 'foo, bar, 3')

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

    def test_changing_options_adjusts_value_and_default(self):
        v = ListValue(name='test', default=[3, 2, 1, 2, 3, 2, 1, 2, 3], options=(1, 2, 3, 4))
        v.set([1, 1, 1])
        self.assertEqual(v.value, [1, 1, 1])
        self.assertEqual(v.default, [3, 2, 1, 2, 3, 2, 1, 2, 3])
        v.options = [1, 2]
        self.assertEqual(v.value, [1, 1, 1])
        self.assertEqual(v.default, [2, 1, 2, 2, 1, 2])
        v.options = [2, 3]
        self.assertEqual(v.value, [])
        self.assertEqual(v.default, [2, 2, 2, 2])
