import unittest
from stig.utils.stringables import (String, Bool, Path, Tuple, Option, Float,
                                    Int, StringableMixin)


from contextlib import contextmanager
class _TestBase(unittest.TestCase):
    @contextmanager
    def assert_raises(self, exccls, msg):
        with self.assertRaises(exccls) as cm:
            yield
        self.assertEqual(str(cm.exception), msg)


class TestStringableMixin(_TestBase):
    def test_partial(self):
        class X(int, StringableMixin):
            def __new__(cls, i, min=0, max=10):
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
        self.assertFalse(Bool('o', true=('x',), false=('o',)))
        with self.assert_raises(ValueError, "Not a boolean value: '0'"):
            Bool('0', true=('x',), false=('o',))

    def test_string(self):
        for value in ('x', 'y', 'z'):
            b = Bool(value, true=('x','y','z'), false=(1, 2, 3))
            self.assertEqual(str(b), 'x')
        for value in (1, 2, 3):
            b = Bool(value, true=('x','y','z'), false=(1, 2, 3))
            self.assertEqual(str(b), '1')


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

        import os
        existing_path = __file__
        p = Path(__file__, mustexist=True)
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


class TestFloat(_TestBase):
    def test_syntax(self):
        self.assertEqual(Float('1').syntax,
                         '[+|-]<NUMBER>[Ti|Gi|Mi|Ki|T|G|M|k]')

    def test_not_a_number(self):
        for value in ('foo', '25xx02', [1, 2, 3], print):
            with self.assert_raises(ValueError, 'Not a number: %r' % value):
                Float(value)

    def test_argument_unit(self):
        n = Float(100, unit='A')
        self.assertEqual(n.string(unit=True), '100A')
        self.assertEqual(n.string(unit=False), '100')
        n = Float(100)
        self.assertEqual(n.string(unit=True), '100')
        self.assertEqual(n.string(unit=False), '100')

    def test_argument_prefix(self):
        n = Float(1e6, prefix='metric')
        self.assertEqual(str(n), '1M')
        n = Float(2**20, prefix='binary')
        self.assertEqual(str(n), '1Mi')

    def test_argument_hide_unit(self):
        n = Float(1e6, unit='f', hide_unit=True)
        self.assertEqual(str(n), '1M')
        self.assertEqual(n.string(unit=False), '1M')
        self.assertEqual(n.string(unit=True), '1Mf')

        n = Float(1e6, unit='f', hide_unit=False)
        self.assertEqual(str(n), '1Mf')
        self.assertEqual(n.string(unit=False), '1M')
        self.assertEqual(n.string(unit=True), '1Mf')

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

    def test_argument_precise(self):
        self.assertEqual(str(Float(100.123, precise=True)), '100.123')
        self.assertEqual(str(Float(100.123, precise=False)), '100')
        self.assertEqual(str(Float(1000003, precise=True)), '1000003')
        self.assertEqual(str(Float(1000003, precise=False)), '1M')
        self.assertEqual(str(Int('1.23456789k', precise=True)), '1235')

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
        self.assertEqual(Float(0).string(unit=False), '0')
        self.assertEqual(Float(0.009).string(unit=False), '0.01')
        self.assertEqual(Float(0.09123).string(unit=False), '0.09')
        self.assertEqual(Float(5.001).string(unit=False), '5')
        self.assertEqual(Float(9.09123).string(unit=False), '9.09')
        self.assertEqual(Float(10.09123).string(unit=False), '10.1')
        self.assertEqual(Float(99.09123).string(unit=False), '99.1')
        self.assertEqual(Float(99.95).string(unit=False), '100')

    def test_infinity_has_correct_sign(self):
        self.assertEqual(Float(float('inf')).string(unit=False), '∞')
        self.assertEqual(Float(-float('inf')).string(unit=False), '-∞')

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
        for prfx,exp_string in (('metric', '1.25Mx'),
                                ('binary', '1.19Mix')):
            n = Float(1e6, unit='x', prefix=prfx, hide_unit=False) \
              + Float(250e3, unit='z', prefix='metric', hide_unit=True)
            self.assertEqual(n, 1.25e6)
            self.assertEqual(str(n), exp_string)


class TestInt(_TestBase):
    def test_rounding(self):
        self.assertEqual(Int(1.4), 1)
        self.assertEqual(Int(1.5), 2)
        self.assertEqual(Int('1.4'), 1)
        self.assertEqual(Int('1.5'), 2)
