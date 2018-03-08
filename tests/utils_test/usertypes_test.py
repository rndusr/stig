import unittest
from stig.utils.usertypes import (String, Bool, Path, Tuple, Option, Float,
                                  Int, StringableMixin, multitype)


from contextlib import contextmanager
class _TestBase(unittest.TestCase):
    @contextmanager
    def assert_raises(self, exccls, msg=None):
        with self.assertRaises(exccls) as cm:
            yield
        if msg is not None:
            self.assertEqual(str(cm.exception), msg)


class TestStringableMixin(_TestBase):
    def test_partial(self):
        class X(int, StringableMixin):
            defaults = {'min': 0, 'max': 10}
            def __new__(cls, i, min=defaults['min'], max=defaults['max']):
                self = super().__new__(cls, i)
                self.min = min
                self.max = max
                return self

        for opts,exp in (({}, {'min': 0, 'max': 10}),
                         ({'min': 5}, {'min': 5, 'max': 10}),
                         ({'max': 5}, {'min': 0, 'max': 5}),
                         ({'min': -10, 'max': 0}, {'min': -10, 'max': 0})):
            p = X.partial(**opts)
            x = p(0)
            self.assertIsInstance(x, X)
            self.assertEqual(x, 0)
            self.assertEqual(x.min, exp['min'])
            self.assertEqual(x.max, exp['max'])

    def test_partial_syntax(self):
        class X(int, StringableMixin):
            defaults = {'min': 0, 'max': 10}
            def __new__(cls, i, min=defaults['min'], max=defaults['max']):
                return super().__new__(cls, i)

            @staticmethod
            def _get_syntax(min=defaults['min'], max=defaults['max']):
                return 'min=%r, max=%r' % (min, max)

        for kwargs in ({}, {'min': 4}, {'max': 6}, {'min': 4, 'max': 6}):
            self.assertEqual(X(5, **kwargs).syntax,
                             X.partial(**kwargs).syntax)

    def test_copy(self):
        class X(int, StringableMixin):
            defaults = {'a': 1, 'b': 2, 'c': 3}
            def __new__(cls, i, a=defaults['a'], b=defaults['b'], c=defaults['c']):
                inst = super().__new__(cls, i)
                inst.a = a
                inst.b = b
                inst.c = c
                return inst

        x = X(5, a=10, b=20)
        self.assertEqual(x, 5)
        self.assertEqual((x.a, x.b, x.c), (10, 20, 3))

        y = x.copy(a=100)
        self.assertEqual(y, 5)
        self.assertEqual((y.a, y.b, y.c), (100, 20, 3))

        z = y.copy(5000, b=2000, c=3000)
        self.assertEqual(z, 5000)
        self.assertEqual((z.a, z.b, z.c), (100, 2000, 3000))


class Test_multitype(_TestBase):
    def test_classname(self):
        mt = multitype(Bool, Float, String)
        self.assertEqual(mt.__name__, 'BoolOrFloatOrString')

    def test_valid_value_behaves_like_subclass_instance(self):
        mt = multitype(Float.partial(min=10), String)
        x = mt(15)
        self.assertEqual(x, 15.0)
        self.assertEqual(x+5, 20.0)
        with self.assert_raises(TypeError):
            x+'!'

        x = mt('hello')
        self.assertEqual(x, 'hello')
        self.assertEqual(x+'!', 'hello!')
        with self.assert_raises(TypeError):
            x+5

    def test_test_invalid_value(self):
        mt = multitype(Bool.partial(true=('yes',), false=('no',)),
                       Float,
                       Tuple.partial(options=('a', 'b', 'c')))
        with self.assert_raises(ValueError, 'Not a boolean; Not a number; Invalid option: hi'):
            mt('hi')
        with self.assert_raises(ValueError, 'Not a boolean; Not a number; Invalid option: d'):
            mt('a', 'b', 'd')

    def test_isinstance(self):
        mt = multitype(Int,
                       Tuple.partial(options=('foo', 'bar', 'baz')),
                       String.partial(minlen=1))

        x = mt(49)
        self.assertTrue(isinstance(x, mt))
        self.assertTrue(isinstance(x, Int))
        self.assertFalse(isinstance(x, String))
        self.assertFalse(isinstance(x, Tuple))

        x = mt('asdf')
        self.assertTrue(isinstance(x, mt))
        self.assertFalse(isinstance(x, Int))
        self.assertTrue(isinstance(x, String))
        self.assertFalse(isinstance(x, Tuple))

        for value in (('foo',), ('bar', 'baz')):
            x = mt(*value)
            self.assertTrue(isinstance(x, mt))
            self.assertFalse(isinstance(x, Int))
            self.assertFalse(isinstance(x, String))
            self.assertTrue(isinstance(x, Tuple))

    def test_issubclass(self):
        mt = multitype(Float,
                       Option.partial(options=('foo', 'bar', 'baz')),
                       Tuple.partial(sep=' / ', dedup=True))

        for subcls in (Float, Option, Tuple):
            self.assertTrue(issubclass(subcls, mt))

        for subcls in (String, Int, Path):
            self.assertFalse(issubclass(subcls, mt))

    def test_syntax(self):
        constructors = (Int.partial(min=-1, max=100),
                        Option.partial(options=('foo', 'bar')),
                        String)
        exp_syntax = ' or '.join((Int.partial(min=-1, max=100).syntax,
                                  Option.partial(options=('foo', 'bar')).syntax,
                                  String.partial().syntax))
        mt = multitype(*constructors)
        self.assertEqual(mt.syntax, exp_syntax)
        inst = mt('hello')
        self.assertEqual(inst.syntax, exp_syntax)

    def test_typename(self):
        constructors = (Int.partial(min=-1, max=100),
                        Option.partial(options=('foo', 'bar')),
                        String)
        exp_typename = ' or '.join((Int.partial(min=-1, max=100).typename,
                                    Option.partial(options=('foo', 'bar')).typename,
                                    String.partial().typename))
        mt = multitype(*constructors)
        self.assertEqual(mt.typename, exp_typename)
        inst = mt('hello')
        self.assertEqual(inst.typename, exp_typename)


class TestString(_TestBase):
    def test_syntax(self):
        self.assertEqual(String('foo').syntax, 'string')
        self.assertEqual(String('foo', minlen=1).syntax, 'string (at least 1 character)')
        self.assertEqual(String('foo', minlen=2).syntax, 'string (at least 2 characters)')
        self.assertEqual(String('f',   maxlen=1).syntax, 'string (at most 1 character)')
        self.assertEqual(String('f',   maxlen=2).syntax, 'string (at most 2 characters)')
        self.assertEqual(String('f',   minlen=1, maxlen=2).syntax, 'string (1-2 characters)')
        self.assertEqual(String('fo',  minlen=2, maxlen=2).syntax, 'string (2 characters)')

    def test_minlen(self):
        for value in ('foo', True, 123):
            with self.assert_raises(ValueError, 'Too short (minimum length is 5)'):
                String(value, minlen=5)

            s = String(value, minlen=1)
            self.assertEqual(s, str(value))

    def test_maxlen(self):
        for value in ('foo', True, 123):
            with self.assert_raises(ValueError, 'Too long (maximum length is 2)'):
                String(value, maxlen=2)

            s = String(value, maxlen=99)
            self.assertEqual(s, str(value))


class TestBool(_TestBase):
    def test_syntax(self):
        self.assertEqual(Bool('1', true=('1',1,'on'), false=('0',0,'off')).syntax,
                         '1/0|on/off')

    def test_valid_values(self):
        self.assertTrue(Bool('x', true=('x',), false=('o',)))
        self.assertFalse(Bool('O', true=('x',), false=('o',)))
        with self.assert_raises(ValueError, 'Not a boolean'):
            Bool('0', true=('x',), false=('o',))

    def test_string(self):
        for value in ('x', 'Y', 'z'):
            b = Bool(value, true=('x','y','z'), false=(1, 2, 3))
            self.assertEqual(str(b), str(value))
        for value in (1, 2, 3):
            b = Bool(value, true=('x','y','z'), false=(1, 2, 3))
            self.assertEqual(str(b), str(value))

    def test_equality(self):
        B = Bool.partial(true=('x','y','z'), false=(1, 2, 3))
        self.assertEqual(B('x'), B('y'))
        self.assertEqual(B('y'), B('z'))
        self.assertEqual(B('z'), True)

        self.assertEqual(B(1), B(2))
        self.assertEqual(B(2), B(3))
        self.assertEqual(B(3), False)


class TestPath(_TestBase):
    def test_syntax(self):
        self.assertEqual(Path('/foo/bar/baz').syntax, 'file system path')

    def test_parsing_tilde(self):
        import os
        homedir = os.environ['HOME']
        self.assertEqual(Path('~/foo/bar'), os.path.join(homedir, 'foo/bar'))

    def test_string(self):
        import os
        homedir = os.environ['HOME']
        p = Path(os.path.join(homedir, 'foo/bar'))
        self.assertEqual(str(p), '~/foo/bar')

    def test_mustexist(self):
        with self.assert_raises(ValueError, 'No such file or directory'):
            Path('/foo/bar/baz', mustexist=True)

        existing_path = __file__
        p = Path(existing_path, mustexist=True)
        self.assertEqual(repr(p), repr(__file__))


class TestTuple(_TestBase):
    def test_syntax(self):
        self.assertEqual(Tuple('foo,bar,baz').syntax, '<OPTION>,<OPTION>,...')
        self.assertEqual(Tuple('foo|bar|baz', sep='|').syntax, '<OPTION>|<OPTION>|...')

    def test_separator(self):
        for sep,string,string_exp in ((', ', '1, 2 ,3 , 4', ('1, 2, 3, 4')),
                                      ('/', '1/2 / 3 /4', '1/2/3/4'),
                                      (' : ', '1:2 : 3: 4', '1 : 2 : 3 : 4')):
            t = Tuple(string, sep=sep)
            self.assertEqual(t, ('1', '2', '3', '4'))
            self.assertEqual(str(t), string_exp)

    def test_options(self):
        with self.assert_raises(ValueError, 'Invalid options: x, baz'):
            Tuple('x, foo, bar, baz', options=('foo', 'bar'))

        with self.assert_raises(ValueError, 'Invalid option: baz'):
            Tuple('foo', 'bar', 'baz', options=('foo', 'bar'))

        self.assertEqual(Tuple('foo, bar'), ('foo', 'bar'))
        self.assertEqual(Tuple('bar', 'foo'), ('bar', 'foo'))
        self.assertEqual(Tuple('foo'), ('foo',))
        self.assertEqual(Tuple('bar'), ('bar',))

    def test_options_property(self):
        t = Tuple(3, 2, options=(1, 2, 3))
        self.assertEqual(t.options, (1, 2, 3))

    def test_aliases(self):
        aliases = {1: 'one', 2: 'two'}
        t = Tuple(1, 2, 'three', aliases=aliases)
        self.assertEqual(t, ('one', 'two', 'three'))

    def test_dedup(self):
        self.assertEqual(Tuple('foo', 'bar', 'bar', 'baz', 'foo', dedup=False),
                         ('foo', 'bar', 'bar', 'baz', 'foo'))
        self.assertEqual(Tuple('foo, bar, bar, baz, foo', dedup=True),
                         ('foo', 'bar', 'baz'))

    def test_mixed_values(self):
        t = Tuple(1, 2, '3, 4', 5, '6, 7')
        self.assertEqual(t, (1, 2, '3', '4', 5, '6', '7'))


class TestOption(_TestBase):
    def test_syntax(self):
        self.assertEqual(Option('1', options=('1', '2', '3')).syntax, '1|2|3')

    def test_aliases(self):
        options = ('foo', 'bar')
        aliases = {'f': 'foo'}
        self.assertEqual(Option('f', options=options, aliases=aliases), 'foo')
        self.assertEqual(Option('foo', options=options, aliases=aliases), 'foo')
        self.assertEqual(Option('bar', options=options, aliases=aliases), 'bar')
        with self.assert_raises(ValueError, 'Not one of: foo, bar'):
            Option('fo', options=options, aliases=aliases)

    def test_options_property(self):
        o = Option('1', options=('1', '2', '3'))
        self.assertEqual(o.options, ('1', '2', '3'))

    def test_aliases_property(self):
        o = Option('1', options=('1', '2', '3'), aliases={'one': '1'})
        self.assertEqual(o.aliases, {'one': '1'})
        o = Option('1', options=('1', '2', '3'))
        self.assertEqual(o.aliases, {})

    def test_errors(self):
        with self.assert_raises(RuntimeError, 'No options provided'):
            Option('fooo', options=())
        with self.assert_raises(ValueError, 'Not foo'):
            Option('fooo', options=('foo',))
        with self.assert_raises(ValueError, 'Not one of: foo, bar'):
            Option('fooo', options=('foo', 'bar'))


class TestFloat(_TestBase):
    def test_syntax(self):
        self.assertEqual(Float('1').syntax,
                         '<NUMBER>[Ti|Gi|Mi|Ki|T|G|M|k]')

    def test_not_a_number(self):
        for value in ('foo', '25xx02', [1, 2, 3], print):
            with self.assert_raises(ValueError, 'Not a number'):
                Float(value)

    def test_argument_unit(self):
        n = Float(100, unit='A')
        self.assertEqual(n.with_unit, '100A')
        self.assertEqual(n.without_unit, '100')
        n = Float(100)
        self.assertEqual(n.with_unit, '100')
        self.assertEqual(n.without_unit, '100')

    def test_argument_prefix(self):
        n = Float(1e6, prefix='metric')
        self.assertEqual(str(n), '1M')
        n = Float(2**20, prefix='binary')
        self.assertEqual(str(n), '1Mi')
        n = Float(1e6, prefix='none')
        self.assertEqual(str(n), '1000000')

    def test_argument_hide_unit(self):
        n = Float(1e6, unit='f', hide_unit=True)
        self.assertEqual(str(n), '1M')
        self.assertEqual(n.without_unit, '1M')
        self.assertEqual(n.with_unit, '1Mf')

        n = Float(1e6, unit='f', hide_unit=False)
        self.assertEqual(str(n), '1Mf')
        self.assertEqual(n.without_unit, '1M')
        self.assertEqual(n.with_unit, '1Mf')

    def test_argument_convert_to(self):
        n = Float(1000, unit='B', convert_to='b')
        self.assertEqual(str(n), '8kb')
        n = Float('1000b', convert_to='b')
        self.assertEqual(str(n), '1kb')

        n = Float(1000, unit='b', convert_to='B')
        self.assertEqual(str(n), '125B')
        n = Float('1000B', convert_to='B')
        self.assertEqual(str(n), '1kB')

    def test_argument_min(self):
        Float(100, min=100)
        with self.assert_raises(ValueError, 'Too small (minimum is 100)'):
            Float(99.9, min=100)

    def test_argument_max(self):
        Float(100, max=100)
        with self.assert_raises(ValueError, 'Too big (maximum is 100)'):
            Float(100.1, max=100)

    def test_argument_autolimit(self):
        with self.assert_raises(ValueError, 'Too big (maximum is 10)'):
            Float(11, max=10, autolimit=False)
        self.assertEqual(Float(11, max=10, autolimit=True), 10)

        with self.assert_raises(ValueError, 'Too small (minimum is 10)'):
            Float(9, min=10, autolimit=False)
        self.assertEqual(Float(9, min=10, autolimit=True), 10)

    def test_parsing_strings(self):
        for string,exp_num in (
                ('1 Apple', 1),
                ('10.3x', 10.3),
                ('2kT', 2 * 1e3),
                ('3 KiB', 3 * (2**10)),
                ('4 MJ', 4 * 1e6),
                ('10.5Mib', 10.5 * 2**20),
                ('50Gp', 50 * 1e9),
                ('62.7Gi', 62.7 * 2**30),
                ('7.19TB', 7.19 * 1e12),
                ('8.9TiV', 8.9 * 2**40),
        ):
            n = Float(string)
            self.assertEqual(n, exp_num)
            self.assertEqual(str(n), string.replace(' ', ''))

    def test_parsing_with_conflicting_units(self):
        n = Float('123kF', unit='B')
        self.assertEqual(n, 123000)
        self.assertEqual(str(n), '123kF')

    def test_parsing_signs(self):
        for string,exp_num in (
                ('-10', -10),
                ('+10', 10),
                ('-10Ki', -10 * (2**10)),
                ('+10k', 10e3),
                ('-17Mx', -17e6),
                ('+99Tiy', 99 * (2**40)),
        ):
            n = Float(string)
            self.assertEqual(n, exp_num)
            self.assertEqual(str(n), string.lstrip('+'))

    def test_passing_other_Float_instance_copies_behaviour(self):
        for orig_prefix in ('binary', 'metric'):
            for orig_unit in ('A', 'B'):
                for orig_hide_unit in (True, False):
                    orig = Float(1e3, unit=orig_unit, prefix=orig_prefix, hide_unit=orig_hide_unit)
                    copy = Float(orig)
                    self.assertEqual(str(orig), str(copy))

                    # Override prefix
                    for new_prefix in ('metric', 'binary'):
                        copy = Float(orig, prefix=new_prefix)
                        self.assertEqual(copy, 1e3)
                        exp_string = '1k' if new_prefix == 'metric' else '1000'
                        exp_string += orig_unit if not orig_hide_unit else ''
                        self.assertEqual(str(copy), exp_string)

                    # Override unit
                    copy = Float(orig, unit='Z')
                    self.assertEqual(copy, 1e3)
                    exp_string = '1k' if orig_prefix == 'metric' else '1000'
                    exp_string += 'Z' if not orig_hide_unit else ''
                    self.assertEqual(str(copy), exp_string)

                    # Override hide_unit
                    for new_hide_unit in (True, False):
                        copy = Float(orig, hide_unit=new_hide_unit)
                        self.assertEqual(copy, 1e3)
                        exp_string = '1k' if orig_prefix == 'metric' else '1000'
                        exp_string += orig_unit if not new_hide_unit else ''
                        self.assertEqual(str(copy), exp_string)

    def test_string_has_reasonable_number_of_decimal_points(self):
        self.assertEqual(str(Float(0)), '0')
        self.assertEqual(str(Float(0.009)), '0.01')
        self.assertEqual(str(Float(0.09123)), '0.09')
        self.assertEqual(str(Float(5.001)), '5')
        self.assertEqual(str(Float(8.999)), '9')
        self.assertEqual(str(Float(9.09123)), '9.09')
        self.assertEqual(str(Float(10.09123)), '10.1')
        self.assertEqual(str(Float(79.999)), '80')
        self.assertEqual(str(Float(99.09123)), '99.1')
        self.assertEqual(str(Float(99.95)), '100')

    def test_infinity_has_correct_sign(self):
        self.assertEqual(str(Float(float('inf'))), '∞')
        self.assertEqual(str(Float(-float('inf'))), '-∞')

    def test_arithmetic_operation_returns_correct_type(self):
        self.assertIsInstance(Float(2.5) + 1.5, Int)
        self.assertIsInstance(Float(2.5) - 1.5, Int)
        self.assertIsInstance(Float(2.5) * 2, Int)
        self.assertIsInstance(Float(10) % 1, Int)
        self.assertIsInstance(Int(5) + 4.3, Float)
        self.assertIsInstance(Int(5) - 0.1, Float)
        self.assertIsInstance(Int(5) / 2, Float)
        self.assertIsInstance(Int(5) % 0.3, Float)
        self.assertIsInstance(round(Float(5.4)), Int)
        self.assertIsInstance(Float('inf') / 2, Float)

    def test_arithmetic_operation_copies_unit(self):
        n = Float(5, unit='X') / 100
        self.assertEqual(str(n), '0.05X')

    def test_arithmetic_operation_copies_prefix(self):
        for prfx,factor,exp_string in (('metric', 1e6, '5M'),
                                       ('binary', 2**20, '5Mi')):
            n = Float(5, prefix=prfx) * factor
            self.assertEqual(str(n), exp_string)

    def test_arithmetic_operation_copies_hide_unit(self):
        for hide_unit,exp_string in ((True, '500'),
                                     (False, '500u')):
            n = Float(5, unit='u', hide_unit=hide_unit) * 100
            self.assertEqual(str(n), exp_string)

    def test_arithmetic_operation_copies_from_first_value(self):
        for prfx,exp_string in (('metric', '1.25M'),
                                ('binary', '1.19Mi')):
            n = Float(1e6, prefix=prfx, hide_unit=False) \
              + Float(250e3, prefix='metric', hide_unit=True)
            self.assertEqual(n, 1.25e6)
            self.assertEqual(str(n), exp_string)

    def test_arithmetic_operation_with_base_types(self):
        x = Float('10k', unit='B', prefix='metric') + 2000
        self.assertEqual(str(x), '12kB')
        x = Float('10k', unit='B', prefix='metric') - 2000
        self.assertEqual(str(x), '8kB')
        x = Float('10k', unit='B', prefix='metric') / 2
        self.assertEqual(str(x), '5kB')
        x = Float('10k', unit='B', prefix='metric') * 2
        self.assertEqual(str(x), '20kB')

    def test_arithmetic_operation_ensures_common_unit(self):
        a = Float(10e3, unit='B', prefix='metric')
        b = Float(1024*10, unit='b', prefix='binary')
        c = a + b
        self.assertEqual(c, 10e3 + (10240/8))
        self.assertEqual(c.unit, 'B')
        self.assertEqual(c.prefix, 'metric')
        self.assertEqual(str(c), '11.3kB')

class TestInt(_TestBase):
    def test_rounding(self):
        self.assertEqual(Int(1.4), 1)
        self.assertEqual(Int(1.5), 2)
        self.assertEqual(Int('1.4'), 1)
        self.assertEqual(Int('1.5'), 2)
