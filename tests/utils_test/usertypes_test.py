import unittest
from stig.utils.usertypes import (ValueBase, StringValue, IntegerValue, FloatValue,
                                  BooleanValue, PathValue, ListValue, OptionValue,
                                  MultiValue, TRUE, FALSE)


class TestValueBase(unittest.TestCase):
    def setUp(self):
        class TestValue(ValueBase):
            pass
        self.cls = TestValue
        self.val = self.cls(name='foo', default=(1, 2, 3))

    def test_string_from_current_value(self):
        self.val.set('hello')
        self.assertEqual(self.val.string(), 'hello')

    def test_string_from_default_value(self):
        self.val.set('hello')
        self.assertEqual(self.val.string(default=True), '(1, 2, 3)')

    def test_string_from_specific_value(self):
        self.val.set('hello')
        self.assertEqual(self.val.string(['x', 'y', 'z']), "['x', 'y', 'z']")

    def test_value_is_converted_to_correct_type(self):
        for basetype,testval1,testval2 in ((str, (1, 2, 3), []),
                                           (int, 1.234, -3.21),
                                           (float, 5, 17),
                                           (bool, 1, 0)):
            class TestValue(ValueBase):
                type = basetype

            val = TestValue('test', default=testval1)
            self.assertIsInstance(val.get(), basetype)
            val.set(testval2)
            self.assertIsInstance(val.get(), basetype)


class TestBooleanValue(unittest.TestCase):
    def test_valid_values(self):
        val = BooleanValue(name='foo')
        for x in TRUE:
            val.set(x)
            self.assertEqual(val.get(), True)
        for x in FALSE:
            val.set(x)
            self.assertEqual(val.get(), False)

        for x in (True, 1):
            val.set(x)
            self.assertEqual(val.get(), True)
        for x in (False, 0):
            val.set(x)
            self.assertEqual(val.get(), False)

    def test_invalid_values(self):
        val = BooleanValue(name='foo')
        for v in (2, -1, [1, 2, 3]):
            with self.assertRaises(ValueError) as cm:
                val.set(v)
            self.assertIn('Not a boolean', str(cm.exception))

    def test_string_from_current_value(self):
        val = BooleanValue(name='foo', default=True)
        self.assertEqual(val.string(), 'enabled')

    def test_string_from_default_value(self):
        val = BooleanValue(name='foo', default='no')
        val.set('yes')
        self.assertEqual(val.string(default=True), 'disabled')

    def test_string_from_specific_valid_value(self):
        val = BooleanValue(name='foo', default='off')
        self.assertEqual(val.string(value='on'), 'enabled')


class TestFloatValue(unittest.TestCase):
    def test_valid_values(self):
        val = FloatValue(name='foo', default=10)
        self.assertEqual(val.get(), 10)
        for newval,exp in ((0, 0), (0.0, 0), ('0', 0), ('0.0', 0),
                           (0.123456789, 0.123456789), (-1e3, -1000),
                           ('100k', 100e3), ('-100k', -100e3),
                           ('+=7k', -93e3), ('-= 1', -93001)):
            val.set(newval)
            self.assertEqual(val.get(), exp)

    def test_invalid_values(self):
        val = FloatValue(name='foo')
        for v in (True, False, [1, 2, 3]):
            with self.assertRaises(ValueError) as cm:
                val.set(v)
            self.assertIn('Not a %s' % val.typename, str(cm.exception))

    def test_adjusting_current_value(self):
        val = FloatValue(name='foo', default=10)
        val.set('+=23')
        self.assertEqual(val.get(), 33)
        val.set('-=3')
        self.assertEqual(val.get(), 30)
        val.set('+=-10')
        self.assertEqual(val.get(), 20)

    def test_adjusting_current_value_without_default_value(self):
        val = FloatValue(name='foo')
        val.set('+=23')
        self.assertEqual(val.get(), 23)

    def test_string_from_current_value(self):
        val = FloatValue(name='foo', default=42)
        self.assertEqual(val.string(), '42')

    def test_string_from_default_value(self):
        val = FloatValue(name='foo', default=42.0)
        val.set(-5)
        self.assertEqual(val.string(), '-5')
        self.assertEqual(val.string(default=True), '42')

    def test_string_from_specific_value(self):
        val = FloatValue(name='foo', default=42.3)
        self.assertEqual(val.string(value=-0.12), '-0.12')
        self.assertEqual(val.string(default=True), '42.3')

    def test___repr__(self):
        val = FloatValue(name='foo', default=42e3)
        self.assertEqual(repr(val), 'foo=42k')
        val.set(1024)
        self.assertEqual(repr(val), 'foo=1.02k')

    def test_typename(self):
        self.assertEqual(FloatValue(name='foo').typename,
                         'rational number')
        self.assertEqual(FloatValue(name='foo', min=5).typename,
                         'rational number (>= 5)')
        self.assertEqual(FloatValue(name='foo', max=5).typename,
                         'rational number (<= 5)')
        self.assertEqual(FloatValue(name='foo', min=-5, max=5).typename,
                         'rational number (-5 - 5)')

    def test_min(self):
        val = FloatValue(name='foo', min=10)
        with self.assertRaises(ValueError) as cm:
            val.set(9)
        self.assertIn('Too small', str(cm.exception))
        self.assertIn('minimum is 10', str(cm.exception))

        val = FloatValue(name='foo', default=100)
        val.min = '150k'
        self.assertEqual(val.min, 150e3)
        self.assertEqual(val.get(), 150e3)
        self.assertEqual(val.get_default(), 150e3)
        with self.assertRaises(ValueError) as cm:
            val.set(149999)
        self.assertIn('Too small', str(cm.exception))
        self.assertIn('minimum is 150k', str(cm.exception))

    def test_max(self):
        val = FloatValue(name='foo', max=100)
        with self.assertRaises(ValueError) as cm:
            val.set(100.001)
        self.assertIn('Too large', str(cm.exception))
        self.assertIn('maximum is 100', str(cm.exception))

        val = FloatValue(name='foo', default=100)
        val.max = 50
        self.assertEqual(val.max, 50)
        self.assertEqual(val.get(), 50)
        self.assertEqual(val.get_default(), 50)
        with self.assertRaises(ValueError) as cm:
            val.set(51)
        self.assertIn('Too large', str(cm.exception))
        self.assertIn('maximum is 50', str(cm.exception))

    def test_min_larger_than_max(self):
        with self.assertRaises(ValueError) as cm:
            FloatValue(name='foo', min=100, max=99)
        self.assertIn('minimum must be smaller than or equal to maximum', str(cm.exception))

        val = FloatValue(name='foo')
        val.min = 50
        with self.assertRaises(ValueError) as cm:
            val.max = 49
        self.assertIn('minimum must be smaller than or equal to maximum', str(cm.exception))

    def test_comparison_with_normal_floats(self):
        i = IntegerValue(name='foo', default=10)
        self.assertTrue(100 > i)
        self.assertTrue(100 >= i)
        self.assertTrue(10 >= i)
        self.assertTrue(i < 100)
        self.assertTrue(i <= 100)
        self.assertTrue(i <= 10)

    def test_pretty_argument(self):
        val = FloatValue(name='foo', default='17000km', pretty=True)
        val.set('10.571111km')
        self.assertEqual(val.string(default=True), '17Mm')
        self.assertEqual(val.string(default=False), '10.6km')
        self.assertEqual(val.string(default=True, unit=False), '17M')
        self.assertEqual(val.string(default=False, unit=False), '10.6k')

        val = FloatValue(name='foo', default='17000km', pretty=False)
        val.set('10.571111km')
        self.assertEqual(val.string(default=True), '17000000.0m')
        self.assertEqual(val.string(default=False), '10571.111m')
        self.assertEqual(val.string(default=True, unit=False), '17000000.0')
        self.assertEqual(val.string(default=False, unit=False), '10571.111')


class TestIntegerValue(unittest.TestCase):
    def test_valid_values(self):
        val = IntegerValue(name='foo', default=10)
        self.assertEqual(val.get(), 10)
        for newval,exp in ((0.3, 0), ('-23.4', -23), (123.5, 124), ('-500.6', -501),
                           ('1234', 1234), ('1234.56789', 1235)):
            val.set(newval)
            self.assertEqual(val.get(), exp)

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
                         'integer number (>= 5)')
        self.assertEqual(IntegerValue(name='foo', max=5).typename,
                         'integer number (<= 5)')
        self.assertEqual(IntegerValue(name='foo', min=-5, max=5).typename,
                         'integer number (-5 - 5)')


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
        self.assertEqual(val.get(), 'hello')
        for newval in ('hel', 'hell', 'hello', 'helloo'):
            val.set(newval)
            self.assertEqual(val.get(), newval)

    def test_invalid_values(self):
        def assert_exceptions(string_was_too_short, cm):
            if string_was_too_short:
                self.assertIn('Too short', str(cm.exception))
                self.assertIn('minimum length is 3', str(cm.exception))
            else:
                self.assertIn('Too long', str(cm.exception))
                self.assertIn('maximum length is 6', str(cm.exception))

        for x in ('he', 'hellooo'):
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
        self.assertEqual(val.get_default(), '1234 ')
        self.assertEqual(val.get(), '1234 ')

    def test_maxlen_adjusts_value_and_default(self):
        val = StringValue(name='foo', default='123456', minlen=3, maxlen=6)
        val.maxlen = 5
        self.assertEqual(val.get_default(), '12345')
        self.assertEqual(val.get(), '12345')


class TestPathValue(unittest.TestCase):
    def test_mustexist(self):
        import tempfile
        with tempfile.TemporaryDirectory() as existing_path:
            val = PathValue('foo', default=existing_path, mustexist=True)
            self.assertEqual(val.get(), existing_path)

            nonexisting_path = 'this/path/does/not/exist'
            with self.assertRaises(ValueError) as cm:
                val.set(nonexisting_path)
            self.assertIn('No such file or directory', str(cm.exception))

            val.mustexist = False
            val.set(nonexisting_path)
            self.assertEqual(val.get(), nonexisting_path)


class TestOptionValue(unittest.TestCase):
    def test_valid_values(self):
        opts = [1, 2, 3, 'apple', 'orange', 'cherry']
        val = OptionValue(name='test', options=opts, default=opts[0])

        for x in (1, 2, 3, 'apple', 'orange', 'cherry'):
            val.set(x)
            self.assertEqual(val.get(), x)
            self.assertEqual(val.get_default(), opts[0])

    def test_invalid_values(self):
        opts = [1, 2, 3, 'apple', 'orange', 'cherry']
        val = OptionValue(name='test', options=opts)

        for x in (0, -1, 4, 'tree', 'car', 'one of us'):
            with self.assertRaises(ValueError) as cm:
                val.set(x)
            self.assertIn('Not one of', str(cm.exception))
            self.assertIn(', '.join(str(o) for o in opts), str(cm.exception))

    def test_options_property(self):
        opts = [1, 2, 3, 'apple', 'orange', 'cherry']
        new_opts = (0, -1, 4, 'tree', 'car', 'one of us')
        val = OptionValue(name='test', options=opts, default=opts[2])
        val.options = new_opts

        for x in opts:
            with self.assertRaises(ValueError) as cm:
                val.set(x)
            self.assertIn('Not one of', str(cm.exception))
            self.assertIn(', '.join(str(no) for no in new_opts), str(cm.exception))

        for x in val.options:
            val.set(x)
            self.assertEqual(val.get(), x)
            self.assertEqual(val.get_default(), new_opts[0])

    def test_aliases(self):
        val = OptionValue(name='test',
                          options=[1, 2, 3, 'apple', 'orange', 'cherry'],
                          aliases={'one': 1, 'two': 2, 'three': 3})

        for alias in val.aliases:
            val.set(alias)
            self.assertEqual(val.value, val.aliases[alias])


class TestListValue(unittest.TestCase):
    def test_valid_values(self):
        for seq in ([1, 2, 3], (1, 2, 3), {1, 2, 3}):
            v = ListValue(name='test', default=seq)
            self.assertEqual(v.get_default(), [1, 2, 3])

        v.set([1, 2, 3, 4])
        self.assertEqual(v.get_default(), [1, 2, 3])
        self.assertEqual(v.get(), [1, 2, 3, 4])

    def test_invalid_values(self):
        for nonseq in (12, object(), print):
            with self.assertRaises(ValueError) as cm:
                ListValue(name='test', default=nonseq)
            self.assertIn('Not a list', str(cm.exception))

    def test_parsing_strings_with_commas(self):
        v = ListValue(name='test', default='1, 2, 3')
        self.assertEqual(v.get_default(), ['1', '2', '3'])
        v.set('1, 2, 3, 4')
        self.assertEqual(v.get_default(), ['1', '2', '3'])
        self.assertEqual(v.get(), ['1', '2', '3', '4'])

    def test_string(self):
        v = ListValue(name='test', default=[1, 2, 3])
        self.assertEqual(v.string(default=True), '1, 2, 3')
        self.assertEqual(v.string('foo'), 'foo')
        self.assertEqual(v.string(object), "<class 'object'>")
        self.assertEqual(v.string(range(4)), '0, 1, 2, 3')
        self.assertEqual(v.string(['foo', 'bar', 3]), 'foo, bar, 3')

    def test_options(self):
        v = ListValue(name='test', default=[1, 2, 3], options=range(1, 11))
        v.set([4, 5, 6, 1])
        self.assertEqual(v.get_default(), [1, 2, 3])
        self.assertEqual(v.get(), [4, 5, 6, 1])

        with self.assertRaises(ValueError) as cm:
            v.set([4, 5, 6, 0])
        self.assertIn('invalid option', str(cm.exception).lower())
        self.assertIn('0', str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            v.set([4, 12, 5, 6, 0])
        self.assertIn('invalid option', str(cm.exception).lower())
        self.assertIn('12', str(cm.exception))
        self.assertIn('0', str(cm.exception))

    def test_changing_options_adjusts_value_and_default(self):
        v = ListValue(name='test', default=[3, 2, 1, 2, 3, 2, 1, 2, 3], options=(1, 2, 3, 4))
        v.set([1, 1, 1])
        self.assertEqual(v.get(), [1, 1, 1])
        self.assertEqual(v.get_default(), [3, 2, 1, 2, 3, 2, 1, 2, 3])
        v.options = [1, 2]
        self.assertEqual(v.get(), [1, 1, 1])
        self.assertEqual(v.get_default(), [2, 1, 2, 2, 1, 2])
        v.options = [2, 3]
        self.assertEqual(v.get(), [])
        self.assertEqual(v.get_default(), [2, 2, 2, 2])

    def test_aliases(self):
        v = ListValue(name='test',
                      default=[1, 'foo', 'bar'],
                      options=[1, 2, 3, 'foo', 'bar', 'baz'],
                      aliases={'f': 'foo', 'b': 'bar'})

        v.set(['bar', 'b', 'f', 3, 'b', 'baz'])
        self.assertEqual(v.value, ['bar', 'bar', 'foo', 3, 'bar', 'baz'])


class TestMultiValue(unittest.TestCase):
    def setUp(self):
        self.IntOrOptOrBool = MultiValue(IntegerValue, OptionValue, BooleanValue)

    def assert_attrs(self, v, **kwargs):
        for kwarg in tuple(kwargs):
            if kwarg in ('__repr__'):
                method = getattr(v, kwarg)
                self.assertEqual(method(), kwargs[kwarg])
                kwargs.pop(kwarg)

        for attr,val in kwargs.items():
            self.assertEqual(getattr(v, attr), val)

    def test_invalid_init_arguments(self):
        with self.assertRaises(TypeError) as cm:
            self.IntOrOptOrBool('foo', min=1, max=2, options=(10, 11, 12),
                                foo='bar', baz='Karate!')
        self.assertEqual("TypeError: invalid keyword arguments: 'baz', 'foo'",
                         str(cm.exception))

    def test_initial_value(self):
        options = ('x', 'y', 'z')

        for v in (1, 2, 3) + options:
            val = self.IntOrOptOrBool('test', default=v, options=options)
            self.assert_attrs(val, value=v, default=v)

        for v in ([1, 2, 3], 'a', '', 'xx', ' z', range(10)):
            with self.assertRaises(ValueError) as cm:
                self.IntOrOptOrBool('test', default=v, options=options)
            errmsgs = ('Not a integer number',
                       'Not one of: %s' % ', '.join(options),
                       'Not a boolean')
            self.assertEqual('; '.join(errmsgs), str(cm.exception))

    def test___repr__(self):
        val = self.IntOrOptOrBool('test_value', options=('a', 'b', 'c'))
        self.assert_attrs(val, __repr__='test_value=<unspecified>')
        for v in (1, 17, 'a', 'b', 'c'):
            val.set(v)
            self.assert_attrs(val, __repr__='test_value=%r' % v)

    def test_set(self):
        options = ('x', 'y', 'z')
        val = self.IntOrOptOrBool('test', default=17, options=options)
        self.assert_attrs(val, value=17, default=17)

        # Test valid values
        for v in (1, 2, 3) + options:
            val.set(v)
            self.assert_attrs(val, value=v, default=17)

        # Test invalid values
        for v in ([1, 2, 3], 'a', '', 'xx', ' z', range(10)):
            with self.assertRaises(ValueError) as cm:
                val.set(v)
            self.assertIn('Not a integer number; Not one of: %s' % ', '.join(options),
                          str(cm.exception))

    def test_get(self):
        options = ('x', 'y', 'z')
        val = self.IntOrOptOrBool('test', default=17, options=options)
        self.assert_attrs(val, value=17, default=17)

        # Test valid values
        for v in (1, 2, 3) + options:
            val.set(v)
            self.assert_attrs(val, value=v, default=17)

        # Test invalid values
        for v in ([1, 2, 3], 'a', '', 'xx', ' z', range(10)):
            with self.assertRaises(ValueError) as cm:
                val.set(v)
            self.assertIn('Not a integer number; Not one of: %s' % ', '.join(options),
                          str(cm.exception))

    def test_get_set_default(self):
        options = ('x', 'y', 'z')
        val = self.IntOrOptOrBool('test', default=17, options=options)
        val.set(5)
        self.assert_attrs(val, value=5, default=17)

        # Test valid values
        for v in (1000, 2000, 3000) + options:
            val.set_default(v)
            self.assert_attrs(val, value=5, default=v)

        # Test invalid values
        for v in ([1, 2, 3], 'a', '', 'xx', ' z', range(10)):
            with self.assertRaises(ValueError) as cm:
                val.set_default(v)
            self.assertIn('Not a integer number; Not one of: %s' % ', '.join(options),
                          str(cm.exception))

    def test_name(self):
        val = self.IntOrOptOrBool('foo')
        self.assert_attrs(val, name='foo', __repr__='foo=<unspecified>')
        val.name = 'bar'
        self.assert_attrs(val, name='bar', __repr__='bar=<unspecified>')

    def test_description(self):
        val = self.IntOrOptOrBool('foo', description='Some explanation')
        self.assert_attrs(val, name='foo', description='Some explanation')
        val.description = 'Some other explanation'
        self.assert_attrs(val, name='foo', description='Some other explanation')

    def test_valuesyntax(self):
        options = ('this', 'that')
        val = self.IntOrOptOrBool('foo', options=options)
        valsyntaxes = ['[+=|-=]<NUMBER>[Ti|T|Gi|G|Mi|M|Ki|k]',
                       'option: %s' % ', '.join(options),
                       BooleanValue.valuesyntax]
        self.assert_attrs(val, valuesyntax=' or '.join(valsyntaxes))

        options = ('green', 'blue', 'yellow')
        val.options = options
        valsyntaxes[1] = 'option: %s' % ', '.join(options)
        self.assert_attrs(val, valuesyntax=' or '.join(valsyntaxes))

    def test_typename(self):
        options = ('this', 'that')
        val = self.IntOrOptOrBool('foo', options=options)
        self.assert_attrs(val, typename='integer number or option: %s or boolean' % ', '.join(options))

        options = ('green', 'blue', 'yellow')
        val.options = options
        self.assert_attrs(val, typename='integer number or option: %s or boolean' % ', '.join(options))

    def test_string_from_current_value(self):
        options = ('this', 'that')
        val = self.IntOrOptOrBool('foo', options=options)
        self.assertEqual(val.string(), '<unspecified>')
        for v,exp in ((54, '54'), ('this', 'this'), ('that', 'that'),
                      ('true', 'enabled'), ('yes', 'enabled'), ('on', 'enabled'),
                      ('false', 'disabled'), ('no', 'disabled'), ('off', 'disabled')):
            val.set(v)
            self.assertEqual(val.string(), exp)

    def test_string_from_default_value(self):
        options = ('this', 'that')
        val = self.IntOrOptOrBool('foo', default='this', options=options)
        val.set(5)
        self.assertEqual(val.string(), '5')
        self.assertEqual(val.string(default=True), 'this')
        val.set_default(True)
        self.assertEqual(val.string(), '5')
        self.assertEqual(val.string(default=True), 'enabled')
        val.set_default(29)
        self.assertEqual(val.string(), '5')
        self.assertEqual(val.string(default=True), '29')

    def test_string_from_specific_valid_value(self):
        options = ('this', 'that')
        val = self.IntOrOptOrBool('foo', default='this', min=0, options=options)
        val.set(1000)
        for v,exp in (('on', 'enabled'), ('false', 'disabled'), ('that', 'that'), (9, '9')):
            self.assertEqual(val.string(value=v), exp)

        # Invalid values should not raise an exception
        for v,exp in (('invalid value', 'invalid value'), (-1, '-1')):
            self.assertEqual(val.string(value=v), exp)

    def test_relative_number_adjustment(self):
        options = ('this', 'that')
        val = self.IntOrOptOrBool('foo', default='this', options=options)
        val.set(1000)
        self.assertEqual(val.get(), 1000)
        for v,exp in (('+=1', 1001), ('false', False), ('-=2000', -999)):
            val.set(v)
            self.assertEqual(val.get(), exp)

    def test_custom_attributes(self):
        def test_validity(val, valid_values, invalid_values):
            for i in valid_values:
                val.set(i)
                self.assert_attrs(val, value=i, default=None)

            for i in invalid_values:
                with self.assertRaisesRegex(ValueError, 'Too (small|large|short|long)'):
                    val.set(i)

        FloatOrPath = MultiValue(FloatValue, StringValue)
        val = FloatOrPath('test', min=-42, max=42, minlen=4)
        self.assert_attrs(val, min=-42, max=42, minlen=4, maxlen=None)
        with self.assertRaises(AttributeError):
            val.this_attribute_does_not_exist
        test_validity(val,
                      valid_values=(-42, 42, '1234', 'abcdefghijklmnopqrstuvwxyz'),
                      invalid_values=(-43, 43, '123', 'abc'))

        val.min = -100
        val.max = 100
        val.minlen = 5
        val.maxlen = 6
        self.assert_attrs(val, min=-100, max=100, minlen=5, maxlen=6)
        test_validity(val,
                      valid_values=(-100, 100, 'hello', 'hello!'),
                      invalid_values=(-101, 101, 'hell', 'Hello, World!'))

    def test_custom_validate_method(self):
        class CustomValidateValue(MultiValue(IntegerValue, BooleanValue)):
            def validate(self, value):
                if value is False:
                    raise ValueError('This boolean value accepts only the truth')
                super().validate(value)
        val = CustomValidateValue('test', default=52)
        self.assertEqual(val.get(), 52)

        # Test valid values
        for v,exp in (('-10', -10), ('true', True), ('yes', True), (True, True)):
            val.set(v)
            self.assertEqual(val.get(), exp)

        # Test invalid values
        for v in ('no', 'off', 'disabled', [1, 2, 3], 'foo'):
            with self.assertRaises(ValueError):
                val.set(v)

    def test_custom_convert_method(self):
        class CustomConvertValue(MultiValue(IntegerValue, StringValue)):
            def convert(self, value):
                v = super().convert(value)
                return v.upper() if isinstance(v, str) else v
        val = CustomConvertValue('test', default=52)
        self.assertEqual(val.get(), 52)

        for v,exp in (('-10', -10), ('Hello', 'HELLO'), (True, 'TRUE'),
                      (['One', 'two', 'three'], "['ONE', 'TWO', 'THREE']")):
            val.set(v)
            self.assertEqual(val.get(), exp)

    def test_custom_string_method(self):
        class CustomStringValue(MultiValue(BooleanValue, ListValue)):
            def string(self, *args, **kwargs):
                string = super().string(*args, **kwargs)
                return string.replace(', ', ' - ')

        val = CustomStringValue('test', default=True)
        self.assertEqual(val.get(), True)
        self.assertEqual(val.string(), 'enabled')
        val.set('foo, bar, baz')
        self.assertEqual(val.get(), ['foo', 'bar', 'baz'])
        self.assertEqual(val.string(), 'foo - bar - baz')

    def test_nested_MultiValues_with_custom_methods(self):
        class UpperStringValue(MultiValue(BooleanValue, StringValue)):
            def convert(self, value):
                v = super().convert(value)
                return v.upper() if isinstance(value, str) else v

        val = UpperStringValue('test', default='this')
        self.assertEqual(val.get(), 'THIS')
        self.assertEqual(val.string(), 'THIS')
        val.set('1')
        self.assertEqual(val.get(), True)
        self.assertEqual(val.string(), 'enabled')

        class SimonSaysValue(MultiValue(OptionValue, UpperStringValue)):
            def string(self, *args, **kwargs):
                return 'Simon says: ' + super().string(*args, **kwargs)

        val = SimonSaysValue('test', default='this', options=('this', 'that'))
        self.assertEqual(val.string(), 'Simon says: this')
        val.set('yes')
        self.assertEqual(val.get(), True)
        self.assertEqual(val.string(), 'Simon says: enabled')
        val.set('someTHING')
        self.assertEqual(val.get(), 'SOMETHING')
        self.assertEqual(val.string(), 'Simon says: SOMETHING')
        val.set('that')
        self.assertEqual(val.get(), 'that')
        self.assertEqual(val.string(), 'Simon says: that')
