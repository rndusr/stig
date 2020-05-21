import unittest

from stig.client.filters.base import BoolFilterSpec, CmpFilterSpec, Filter, FilterChain


class TestFilterParser(unittest.TestCase):
    def setUp(self):
        class FooFilter(Filter):
            BOOLEAN_FILTERS = {'b1': BoolFilterSpec(lambda i: bool(i), aliases=('b1a', 'b1A')),
                               'b2': BoolFilterSpec(lambda i: bool(i), aliases=('b2a', 'b2A'))}
            COMPARATIVE_FILTERS = {'c1': CmpFilterSpec(value_type=str, value_getter=NotImplemented, aliases=('c1a', 'c1A')),
                                   'c2': CmpFilterSpec(value_type=str, value_getter=NotImplemented, aliases=('c2a', 'c2A'))}
            DEFAULT_FILTER = 'c1'
        self.f = FooFilter

    def test_no_argument_with_no_default_filter(self):
        class FooFilter(Filter):
            pass
        with self.assertRaises(ValueError) as cm:
            FooFilter()
        self.assertEqual(str(cm.exception), 'No filter expression given')

    def test_no_argument_with_default_filter(self):
        self.f.DEFAULT_FILTER = 'b2'
        self.assertEqual(str(self.f()), 'b2')
        self.assertEqual(str(self.f('')), 'b2')
        self.assertEqual(str(self.f(' ')), 'b2')
        self.f.DEFAULT_FILTER = 'c1'
        self.assertEqual(str(self.f()), 'c1')
        self.assertEqual(str(self.f('')), 'c1')
        self.assertEqual(str(self.f(' ')), 'c1')

    def test_only_operator_given(self):
        self.assertEqual(str(self.f('=')), '=')
        self.assertEqual(str(self.f('~')), '~')
        self.assertEqual(str(self.f('!>=')), '>=')

    def test_filter_and_operator_given(self):
        self.assertEqual(str(self.f('c1=')), '=')
        self.assertEqual(str(self.f('c2>=')), 'c2>=')
        self.assertEqual(str(self.f('c2!>=')), 'c2>=')
        self.assertEqual(str(self.f('!c2>=')), 'c2>=')
        self.assertEqual(str(self.f('!c2!>=')), 'c2>=')

    def test_comparative_filter_as_boolean(self):
        self.assertEqual(str(self.f('c1')), 'c1')
        self.assertEqual(str(self.f('c2')), 'c2')

    def test_aliases(self):
        class FooFilter(Filter):
            BOOLEAN_FILTERS = {'b': BoolFilterSpec(lambda i: bool(i),
                                                   aliases=('foo',))}
            COMPARATIVE_FILTERS = {'c': CmpFilterSpec(value_type=str, value_getter=NotImplemented,
                                                      aliases=('bar', 'baz'))}

        self.assertEqual(str(FooFilter('foo')), 'b')
        self.assertEqual(str(FooFilter('bar')), 'c')
        self.assertEqual(str(FooFilter('bar~x')), 'c~x')
        self.assertEqual(str(FooFilter('baz')), 'c')
        self.assertEqual(str(FooFilter('baz<42')), 'c<42')

    def test_alias_collision(self):
        class FooFilter(Filter):
            BOOLEAN_FILTERS = {'b': BoolFilterSpec(lambda i: bool(i),
                                                   aliases=('foo',))}
            COMPARATIVE_FILTERS = {'c': CmpFilterSpec(value_type=str, value_getter=NotImplemented,
                                                      aliases=('bar', 'foo'))}
        with self.assertRaises(RuntimeError) as cm:
            FooFilter('anything')
        self.assertEqual(str(cm.exception), "Multiple aliases: 'foo'")

    def test_operator_given_to_boolean_filter(self):
        with self.assertRaises(ValueError) as cm:
            self.f('b1=')
        self.assertEqual(str(cm.exception), "Boolean filter does not take an operator: b1")

    def test_value_given_to_boolean_filter(self):
        with self.assertRaises(ValueError) as cm:
            self.f('b2=foo')
        self.assertEqual(str(cm.exception), "Boolean filter does not take a value: b2")

    def test_invert_whole_expression(self):
        self.assertEqual(str(self.f('!b2')), '!b2')
        self.assertEqual(str(self.f('!c1~x')), '!~x')
        self.assertEqual(str(self.f('!c2<5')), 'c2!<5')
        self.assertEqual(str(self.f('!c2!<52')), 'c2<52')

    def test_invert_operator(self):
        self.assertEqual(str(self.f('c1!=x')), '!=x')
        self.assertEqual(str(self.f('c2!>=y')), 'c2!>=y')

    def test_invert_default_filter_value(self):
        self.assertEqual(str(self.f('!value')), '!~value')
        self.assertEqual(str(self.f('!<42')), '!<42')

    def test_irrelevant_spaces(self):
        self.assertEqual(str(self.f('  !b1 ')), '!b1')
        self.assertEqual(str(self.f(' !foo')), '!~foo')
        self.assertEqual(str(self.f(' foo ')), '~foo')
        self.assertEqual(str(self.f('~ foo')), '~foo')
        self.assertEqual(str(self.f('=foo ')), '=foo')
        self.assertEqual(str(self.f(' != foo')), '!=foo')
        self.assertEqual(str(self.f('c1= foo')), "=foo")
        self.assertEqual(str(self.f('c2= foo')), "c2=foo")
        self.assertEqual(str(self.f(' c1 !=foo ')), "!=foo")
        self.assertEqual(str(self.f(' c2 !=foo ')), "c2!=foo")

    def test_escaped_inverter(self):
        self.assertEqual(str(self.f('\\!b1')), "~!b1")

    def test_escaped_spaces(self):
        self.assertEqual(str(self.f('c1=a\\ ')), "='a '")
        self.assertEqual(str(self.f('c2~\\ b')), "c2~' b'")
        self.assertEqual(str(self.f('\\ foo\\ ')), "~' foo '")
        self.assertEqual(str(self.f('\\ \\ " foo " ')), "~'   foo '")
        self.assertEqual(str(self.f('c2 ~ \\ foo\\ ')), "c2~' foo '")

    def test_quoted_spaces(self):
        self.assertEqual(str(self.f("c1='a b'")), "='a b'")
        self.assertEqual(str(self.f('c2="a b"')), "c2='a b'")
        self.assertEqual(str(self.f('" foo "')), "~' foo '")
        self.assertEqual(str(self.f('  " foo " ')), "~' foo '")
        self.assertEqual(str(self.f('~ " foo  " ')), "~' foo  '")
        self.assertEqual(str(self.f('  c2  ~  " foo "  ')), "c2~' foo '")

    def test_escaped_quotes(self):
        self.assertEqual(str(self.f('\\"foo')), """~'"foo'""")
        self.assertEqual(str(self.f('foo\\"')), """~'foo"'""")
        self.assertEqual(str(self.f("~foo\\'s")), '''~"foo's"''')
        self.assertEqual(str(self.f("~foo\\'")), '''~"foo'"''')

    def test_quoted_quotes(self):
        self.assertEqual(str(self.f("""'"f"oo'""")), """~'"f"oo'""")
        self.assertEqual(str(self.f('''c2~"foo's"''')), '''c2~"foo's"''')

    def test_quoted_comparative_operators(self):
        for op1 in self.f.OPERATORS:
            self.assertEqual(str(self.f('"%s"' % (op1,))), '~%s' % (op1,))
            self.assertEqual(str(self.f("'%s'" % (op1,))), '~%s' % (op1,))

            self.assertEqual(str(self.f('!"%s"' % (op1,))), '!~%s' % (op1,))
            self.assertEqual(str(self.f("!'%s'" % (op1,))), '!~%s' % (op1,))

            self.assertEqual(str(self.f("' %s'" % (op1,))), "~' %s'" % (op1,))
            self.assertEqual(str(self.f("'%s '" % (op1,))), "~'%s '" % (op1,))
            self.assertEqual(str(self.f("' %s '" % (op1,))), "~' %s '" % (op1,))

            for op2 in self.f.OPERATORS:
                self.assertEqual(str(self.f("%s' %s'" % (op1, op2,))), "%s' %s'" % (op1, op2,))
                self.assertEqual(str(self.f("!%s' %s'" % (op1, op2,))), "!%s' %s'" % (op1, op2,))
                self.assertEqual(str(self.f("c2!%s' %s'" % (op1, op2,))), "c2!%s' %s'" % (op1, op2,))

    def test_escaped_comparative_operators(self):
        for op1 in self.f.OPERATORS:
            self.assertEqual(str(self.f('\\%s' % (op1,))), '~%s' % (op1,))
            self.assertEqual(str(self.f('!\\%s' % (op1,))), '!~%s' % (op1,))
            self.assertEqual(str(self.f(" \\%s" % (op1,))), "~%s" % (op1,))
            self.assertEqual(str(self.f("' \\%s'" % (op1,))), "~' \\%s'" % (op1,))
            self.assertEqual(str(self.f("!' \\%s'" % (op1,))), "!~' \\%s'" % (op1,))

    def test_auto_quoting(self):
        self.assertEqual(str(self.f('=f o o')), "='f o o'")

    def test_unknown_filter(self):
        with self.assertRaises(ValueError) as cm:
            self.f('foo=bar')
        self.assertEqual(str(cm.exception), "Invalid filter name: 'foo'")

    def test_equality(self):
        self.assertEqual(self.f('c1=foo'), self.f('=foo'))
        self.assertEqual(self.f('c1a=foo'), self.f('=foo'))
        self.assertEqual(self.f('c1A=foo'), self.f('=foo'))

        self.assertEqual(self.f('!c1=foo'), self.f('!=foo'))
        self.assertEqual(self.f('!c1a=foo'), self.f('!=foo'))
        self.assertEqual(self.f('c1A!=foo'), self.f('!=foo'))
        self.assertEqual(self.f('!c2=foo'), self.f('c2!=foo'))
        self.assertEqual(self.f('!c2a=foo'), self.f('!c2=foo'))
        self.assertEqual(self.f('!c2A!=foo'), self.f('c2=foo'))

        self.assertEqual(self.f('b1'), self.f('b1'))
        self.assertEqual(self.f('b1'), self.f('b1a'))
        self.assertEqual(self.f('b1'), self.f('b1A'))

        self.assertEqual(self.f('b2'), self.f('b2'))
        self.assertEqual(self.f('b2'), self.f('b2a'))
        self.assertEqual(self.f('b2'), self.f('b2A'))

        self.assertEqual(self.f('!b1'), self.f('!b1'))
        self.assertEqual(self.f('!b1'), self.f('!b1a'))
        self.assertEqual(self.f('!b1'), self.f('!b1A'))

        self.assertEqual(self.f('!b2'), self.f('!b2'))
        self.assertEqual(self.f('!b2'), self.f('!b2a'))
        self.assertEqual(self.f('!b2'), self.f('!b2A'))

        self.assertNotEqual(self.f('c1=foo'), self.f('c1=bar'))


class TestFilter_apply(unittest.TestCase):
    def test_key_argument(self):
        class FooFilter(Filter):
            BOOLEAN_FILTERS = {'all': BoolFilterSpec(None)}
            COMPARATIVE_FILTERS = {'dec': CmpFilterSpec(value_type=str, value_getter=lambda x: x['dec']),
                                   'oct': CmpFilterSpec(value_type=str, value_getter=lambda x: x['oct']),
                                   'hex': CmpFilterSpec(value_type=str, value_getter=lambda x: x['hex'])}
        items = ({'dec': '42', 'oct': '0o52', 'hex': '0x2a'},
                 {'dec': '23', 'oct': '0o27', 'hex': '0x17'},
                 {'dec': '51', 'oct': '0o63', 'hex': '0x33'})

        self.assertEqual(tuple(FooFilter('all').apply(items, key='dec')), ('42', '23', '51'))
        self.assertEqual(tuple(FooFilter('all').apply(items, key='oct')), ('0o52', '0o27', '0o63'))
        self.assertEqual(tuple(FooFilter('all').apply(items, key='hex')), ('0x2a', '0x17', '0x33'))

        self.assertEqual(tuple(FooFilter('dec~2').apply(items, key='dec')), ('42', '23'))
        self.assertEqual(tuple(FooFilter('oct~7').apply(items, key='dec')), ('23',))
        self.assertEqual(tuple(FooFilter('hex~2').apply(items, key='dec')), ('42',))

        self.assertEqual(tuple(FooFilter('dec~5').apply(items, key='oct')), ('0o63',))
        self.assertEqual(tuple(FooFilter('oct~5').apply(items, key='oct')), ('0o52',))
        self.assertEqual(tuple(FooFilter('hex~3').apply(items, key='oct')), ('0o63',))

        self.assertEqual(tuple(FooFilter('dec~4').apply(items, key='hex')), ('0x2a',))
        self.assertEqual(tuple(FooFilter('oct~3').apply(items, key='hex')), ('0x33',))
        self.assertEqual(tuple(FooFilter('hex~7').apply(items, key='hex')), ('0x17',))

    def test_invert_argument(self):
        class FooFilter(Filter):
            BOOLEAN_FILTERS = {'all': BoolFilterSpec(None)}
            COMPARATIVE_FILTERS = {'dec': CmpFilterSpec(value_type=str, value_getter=lambda x: x['dec']),
                                   'oct': CmpFilterSpec(value_type=str, value_getter=lambda x: x['oct']),
                                   'hex': CmpFilterSpec(value_type=str, value_getter=lambda x: x['hex'])}
        items = ({'dec': '42', 'oct': '0o52', 'hex': '0x2a'},
                 {'dec': '23', 'oct': '0o27', 'hex': '0x17'},
                 {'dec': '51', 'oct': '0o63', 'hex': '0x33'})

        self.assertEqual(tuple(FooFilter('all').apply(items, invert=True)), ())
        self.assertEqual(tuple(FooFilter('!all').apply(items, invert=True)), items)
        self.assertEqual(tuple(FooFilter('all').apply(items, invert=True, key='oct')), ())
        self.assertEqual(tuple(FooFilter('!all').apply(items, invert=True, key='oct')), ('0o52', '0o27', '0o63'))

        self.assertEqual(tuple(FooFilter('dec~2').apply(items, invert=True)), (items[2],))
        self.assertEqual(tuple(FooFilter('dec!~2').apply(items, invert=True)), (items[0], items[1]))
        self.assertEqual(tuple(FooFilter('dec~2').apply(items, invert=True, key='hex')), ('0x33',))
        self.assertEqual(tuple(FooFilter('dec!~2').apply(items, invert=True, key='hex')), ('0x2a', '0x17'))
        self.assertEqual(tuple(FooFilter('!dec!~2').apply(items, invert=True, key='hex')), ('0x33',))

    def test_invalid_operator(self):
        class FooFilter(Filter):
            COMPARATIVE_FILTERS = {'n': CmpFilterSpec(value_type=int, value_getter=NotImplemented)}
        items = ({'n': 42},)
        with self.assertRaises(ValueError) as cm:
            FooFilter('n~4').apply(items)
        self.assertEqual(str(cm.exception), "Invalid operator for filter 'n': ~")

    def test_invalid_value(self):
        class FooFilter(Filter):
            COMPARATIVE_FILTERS = {'n': CmpFilterSpec(value_type=int, value_getter=NotImplemented)}
        items = ({'n': 42},)
        with self.assertRaises(ValueError) as cm:
            FooFilter('n>foo').apply(items)
        self.assertEqual(str(cm.exception), "Invalid value for filter 'n': 'foo'")

    def test_boolean_filters(self):
        class FooFilter(Filter):
            BOOLEAN_FILTERS = {'b1': BoolFilterSpec(lambda i: i['v']),
                               'b2': BoolFilterSpec(lambda i: i['v'] >= 0)}
        items = ({'v': 0}, {'v': 1}, {'v': -1})
        self.assertEqual(tuple(FooFilter('b1').apply(items, key='v')), (1, -1))
        self.assertEqual(tuple(FooFilter('!b1').apply(items, key='v')), (0,))
        self.assertEqual(tuple(FooFilter('b2').apply(items, key='v')), (0, 1))
        self.assertEqual(tuple(FooFilter('!b2').apply(items, key='v')), (-1,))

    def test_catch_all_filter(self):
        class FooFilter(Filter):
            BOOLEAN_FILTERS = {'all': BoolFilterSpec(None)}
        items = ({'v': 0}, {'v': 1}, {'v': -1})
        self.assertEqual(tuple(FooFilter('all').apply(items, key='v')), (0, 1, -1))
        self.assertEqual(tuple(FooFilter('!all').apply(items, key='v')), ())

    def test_equals_operator(self):
        class FooFilter(Filter):
            COMPARATIVE_FILTERS = {'c': CmpFilterSpec(value_type=str, value_getter=lambda i: i['v'])}
        items = ({'v': 'foo'}, {'v': 'bar'}, {'v': 'baz'})
        self.assertEqual(tuple(FooFilter('c=foo').apply(items, key='v')), ('foo',))
        self.assertEqual(tuple(FooFilter('c!=foo').apply(items, key='v')), ('bar', 'baz'))
        self.assertEqual(tuple(FooFilter('!c=foo').apply(items, key='v')), ('bar', 'baz'))

    def test_contains_operator(self):
        class FooFilter(Filter):
            COMPARATIVE_FILTERS = {'c': CmpFilterSpec(value_type=str, value_getter=lambda i: i['v'])}
        items = ({'v': 'foo'}, {'v': 'bar'}, {'v': 'baz'})
        self.assertEqual(tuple(FooFilter('c~b').apply(items, key='v')), ('bar', 'baz'))
        self.assertEqual(tuple(FooFilter('c!~b').apply(items, key='v')), ('foo',))
        self.assertEqual(tuple(FooFilter('!c~b').apply(items, key='v')), ('foo',))

    def test_gt_operator(self):
        class FooFilter(Filter):
            COMPARATIVE_FILTERS = {'c': CmpFilterSpec(value_type=int, value_getter=lambda i: i['v'])}
        items = ({'v': 10}, {'v': 20}, {'v': 30})
        self.assertEqual(tuple(FooFilter('c>20').apply(items, key='v')), (30,))
        self.assertEqual(tuple(FooFilter('c!>20').apply(items, key='v')), (10, 20))
        self.assertEqual(tuple(FooFilter('!c>20').apply(items, key='v')), (10, 20))

    def test_lt_operator(self):
        class FooFilter(Filter):
            COMPARATIVE_FILTERS = {'c': CmpFilterSpec(value_type=int, value_getter=lambda i: i['v'])}
        items = ({'v': 10}, {'v': 20}, {'v': 30})
        self.assertEqual(tuple(FooFilter('c<20').apply(items, key='v')), (10,))
        self.assertEqual(tuple(FooFilter('c!<20').apply(items, key='v')), (20, 30))
        self.assertEqual(tuple(FooFilter('!c<20').apply(items, key='v')), (20, 30))

    def test_ge_operator(self):
        class FooFilter(Filter):
            COMPARATIVE_FILTERS = {'c': CmpFilterSpec(value_type=int, value_getter=lambda i: i['v'])}
        items = ({'v': 10}, {'v': 20}, {'v': 30})
        self.assertEqual(tuple(FooFilter('c>=20').apply(items, key='v')), (20, 30))
        self.assertEqual(tuple(FooFilter('c!>=20').apply(items, key='v')), (10,))
        self.assertEqual(tuple(FooFilter('!c>=20').apply(items, key='v')), (10,))

    def test_le_operator(self):
        class FooFilter(Filter):
            COMPARATIVE_FILTERS = {'c': CmpFilterSpec(value_type=int, value_getter=lambda i: i['v'])}
        items = ({'v': 10}, {'v': 20}, {'v': 30})
        self.assertEqual(tuple(FooFilter('c<=20').apply(items, key='v')), (10, 20))
        self.assertEqual(tuple(FooFilter('c!<=20').apply(items, key='v')), (30,))
        self.assertEqual(tuple(FooFilter('!c<=20').apply(items, key='v')), (30,))

    def test_matching_any_value(self):
        class FooFilter(Filter):
            COMPARATIVE_FILTERS = {'c': CmpFilterSpec(value_type=str, value_getter=lambda i: i['v'])}
        items = ({'v': ''}, {'v': 'foo'}, {'v': 'bar'})
        self.assertEqual(tuple(FooFilter('c=').apply(items, key='v')), ('', 'foo', 'bar'))
        self.assertEqual(tuple(FooFilter('c~').apply(items, key='v')), ('', 'foo', 'bar'))
        self.assertEqual(tuple(FooFilter('!c~').apply(items, key='v')), ('', 'foo', 'bar'))
        self.assertEqual(tuple(FooFilter('c!~').apply(items, key='v')), ('', 'foo', 'bar'))

    def test_matching_empty_string(self):
        class FooFilter(Filter):
            COMPARATIVE_FILTERS = {'c': CmpFilterSpec(value_type=str, value_getter=lambda i: i['v'])}
        items = ({'v': ''}, {'v': 'foo'}, {'v': 'bar'})
        self.assertEqual(tuple(FooFilter('c=""').apply(items, key='v')), ('',))
        self.assertEqual(tuple(FooFilter("c=''").apply(items, key='v')), ('',))
        self.assertEqual(tuple(FooFilter('!c=""').apply(items, key='v')), ('foo', 'bar'))
        self.assertEqual(tuple(FooFilter("c!=''").apply(items, key='v')), ('foo', 'bar'))

    def test_comparative_filter_as_boolean(self):
        class FooFilter(Filter):
            COMPARATIVE_FILTERS = {'c': CmpFilterSpec(value_type=str, value_getter=lambda i: i['v'])}
        items = ({'v': ''}, {'v': 'foo'}, {'v': 'bar'})
        self.assertEqual(tuple(FooFilter('c').apply(items, key='v')), ('foo', 'bar'))
        self.assertEqual(tuple(FooFilter('!c').apply(items, key='v')), ('',))

    def test_match_everything(self):
        class FooFilter(Filter):
            BOOLEAN_FILTERS = {'everything': BoolFilterSpec(None, aliases=('all',))}
        items = ({'v': ''}, {'v': 'foo'}, {'v': 'bar'})
        self.assertEqual(tuple(FooFilter('everything').apply(items, key='v')), ('', 'foo', 'bar'))
        self.assertEqual(tuple(FooFilter('all').apply(items, key='v')), ('', 'foo', 'bar'))

    def test_match(self):
        class FooFilter(Filter):
            BOOLEAN_FILTERS = {'everything': BoolFilterSpec(None)}
            COMPARATIVE_FILTERS = {'v': CmpFilterSpec(value_type=str, value_getter=lambda i: i['v'])}
        items = ({'v': 'foo'}, {'v': 'bar'}, {'v': 'baz'})
        for item in items:
            self.assertTrue(FooFilter('everything').match(item))
        for filter_str,results in (('v~f', (True, False, False)),
                                   ('v~ba', (False, True, True)),
                                   ('v!~f', (False, True, True)),
                                   ('!v~ba', (True, False, False))):
            for item,result in zip(items, results):
                self.assertEqual(FooFilter(filter_str).match(item), result)


class TestFilterChain_parser(unittest.TestCase):
    def setUp(self):
        class FooFilter(Filter):
            BOOLEAN_FILTERS = {'b1': BoolFilterSpec(lambda i: i['v'], needed_keys=('a', 'b')),
                               'b2': BoolFilterSpec(lambda i: len(i['v']) > 3, needed_keys=('c', 'b')),
                               'everything': BoolFilterSpec(None, aliases=('all',))}
            COMPARATIVE_FILTERS = {'c': CmpFilterSpec(value_type=str, value_getter=lambda i: i['v'],
                                                      needed_keys=('c', 'a')),
                                   'ci': CmpFilterSpec(value_type=str, value_getter=lambda i: i['v'].casefold(),
                                                       needed_keys=('b', 'd'))}
            DEFAULT_FILTER = 'c'

        class FooFilterChain(FilterChain):
            filterclass = FooFilter

        self.f = FooFilterChain

    def test_no_filterclass_attribute_set_by_child_class(self):
        class FooFilterChain(FilterChain):
            pass
        with self.assertRaises(RuntimeError) as cm:
            FooFilterChain()
        self.assertEqual(str(cm.exception), 'Attribute "filterclass" must be set to a Filter subclass')

    def test_passing_FilterChain_instance(self):
        self.assertEqual(str(self.f(self.f('ci=x'))), 'ci=x')

    def test_invalid_argument_type(self):
        with self.assertRaises(ValueError) as cm:
            self.f(123)
        self.assertEqual(str(cm.exception), 'Filters must be string or sequence of strings, not int: 123')

    def test_filter_is_sequence_of_strings(self):
        self.assertEqual(str(self.f(('foo', 'ci~bar', 'b2'))), '~foo|ci~bar|b2')

    def test_any_blank_filter_ignores_all_other_filters(self):
        self.assertEqual(str(self.f('everything')), 'everything')
        self.assertEqual(str(self.f('c~foo|everything&b2')), 'everything')
        self.assertEqual(str(self.f('c~foo|all&b2')), 'everything')

    def test_filter_with_boolean_operators(self):
        self.assertEqual(str(self.f('b1 | b2 & c~x | ci < 5')), 'b1|b2&~x|ci<5')

    def test_filter_starts_with_boolean_operator(self):
        for op in ('&', '|'):
            with self.assertRaises(ValueError) as cm:
                self.f(op + 'b2')
            self.assertEqual(str(cm.exception), "Filter can't start with operator: '%s'" % (op,))

    def test_filter_ends_with_boolean_operator(self):
        for op in ('&', '|'):
            with self.assertRaises(ValueError) as cm:
                self.f('b1' + op)
            self.assertEqual(str(cm.exception), "Filter can't end with operator: '%s'" % (op,))

    def test_consecutive_boolean_operators(self):
        for string,wrong_part in (('b1||b2&foo', 'b1||b2'),
                                  ('b2|c=foo&&ci=bar', 'c=foo&&ci=bar'),
                                  ('b2&|b1&ci', 'b2&|b1'),
                                  ('ci|ci~foo|&c', 'ci~foo|&c'),
                                  ('foo||b2&c~foo|~bar', 'foo||b2'),
                                  ('ci~foo|c=bar&b1|&!b2|~baz', 'b1|&!b2')):
            with self.assertRaises(ValueError) as cm:
                self.f(string)
            self.assertEqual(str(cm.exception), 'Consecutive operators: %r' % wrong_part)

    def test_chaining_default_filters(self):
        self.assertEqual(str(self.f('foo|bar')), '~foo|~bar')
        self.assertEqual(str(self.f('bar&foo')), '~bar&~foo')
        self.assertEqual(str(self.f('bar&!foo')), '~bar&!~foo')
        self.assertEqual(str(self.f('!bar|!foo')), '!~bar|!~foo')

    def test_catch_all_filter(self):
        self.assertEqual(str(self.f('b1|everything|c~foo')), 'everything')
        self.assertEqual(str(self.f('b1|c~foo&all')), 'everything')
        self.assertEqual(str(self.f('b1|!all&c~foo')), '!everything')

    def test_quoting_boolean_operators(self):
        for op in ('&', '|'):
            self.assertEqual(str(self.f('ci="%s"' % (op,))), "ci=\\%s" % (op,))
            self.assertEqual(str(self.f('ci="%sa"' % (op,))), "ci='%sa'" % (op,))
            self.assertEqual(str(self.f('ci="a%s"' % (op,))), "ci='a%s'" % (op,))
            self.assertEqual(str(self.f("ci='a%sb'" % (op,))), "ci='a%sb'" % (op,))

    def test_escaping_boolean_operators(self):
        for op in ('&', '|'):
            self.assertEqual(str(self.f('ci=\\%s' % (op,))), "ci=\\%s" % (op,))
            self.assertEqual(str(self.f('ci=\\%sa' % (op,))), "ci='%sa'" % (op,))
            self.assertEqual(str(self.f('ci=a\\%s' % (op,))), "ci='a%s'" % (op,))
            self.assertEqual(str(self.f("ci=a\\%sb" % (op,))), "ci='a%sb'" % (op,))

    def test_equality(self):
        self.assertEqual(self.f('b1&b2'), self.f('b1&b2'))
        self.assertEqual(self.f('b1&b2'), self.f('b2&b1'))
        self.assertEqual(self.f('b1|b2'), self.f('b2|b1'))
        self.assertNotEqual(self.f('b1|b2'), self.f('b1&b2'))
        self.assertEqual(self.f('b1|b2&c~foo'), self.f('c~foo&b2|b1'))
        self.assertNotEqual(self.f('b1|b2&c~foo'), self.f('b2|b1&c~foo'))
        self.assertEqual(self.f('b1|b2&c~foo|ci~bar'), self.f('c~foo&b2|ci~bar|b1'))
        self.assertNotEqual(self.f('b1|b2&c~foo|ci~bar'), self.f('c~foo&b2|b1'))

    def test_combined_needed_keys(self):
        f1 = self.f('b1')
        f2 = self.f('b2')
        self.assertEqual(set(f1.needed_keys), {'a', 'b'})
        self.assertEqual(set(f2.needed_keys), {'b', 'c'})
        self.assertEqual(set((f1 | f2).needed_keys), {'a', 'b', 'c'})
        self.assertEqual(set((f1 & f2).needed_keys), {'a', 'b', 'c'})

    def test_combining_filters_with_or_operator(self):
        f1 = self.f('b1') | self.f('c~foo')
        self.assertEqual(f1, self.f('b1|c~foo'))
        f2 = f1 | self.f('c!~bar&!b1')
        self.assertEqual(f2, self.f('b1|c~foo|c!~bar&!b1'))

        f1 = self.f('b1&b2')
        f2 = self.f('b2&b1')
        for a,b in ((f1, f2), (f2, f1)):
            self.assertEqual(a | b, f1)
            self.assertEqual(a | b, f2)

        f3 = self.f('c~foo')
        self.assertEqual(f1 | f2 | f3, self.f('b1&b2|c~foo'))
        self.assertEqual(f3 | f1 | f2, self.f('c~foo|b1&b2'))
        self.assertEqual(f2 | f3 | f1, self.f('b1&b2|c~foo'))

    def test_combining_filters_with_and_operator(self):
        f1 = self.f('b1') & self.f('c~foo')
        self.assertEqual(f1, self.f('b1&c~foo'))
        f2 = self.f('b2|ci~bar')
        self.assertEqual(f1 & f2, self.f('b1&c~foo&b2|ci~bar'))
        self.assertEqual(f1 & f2, self.f('ci~bar|b2&b1&c~foo'))

    def test_combining_catch_all_filter(self):
        self.assertEqual(self.f('b2') & self.f('c~foo') | self.f('everything'), self.f('everything'))
        self.assertEqual(self.f('b2') & self.f('everything') | self.f('c~foo'), self.f('everything'))
        self.assertEqual(self.f('b2') | self.f('everything') & self.f('c~foo'), self.f('everything'))


class TestFilterChain_apply(unittest.TestCase):
    def setUp(self):
        class FooFilter(Filter):
            BOOLEAN_FILTERS = {'positive': BoolFilterSpec(lambda i: i['v'] >= 0),
                               'mod2': BoolFilterSpec(lambda i: i['v'] % 2 == 0),
                               'mod3': BoolFilterSpec(lambda i: i['v'] % 3 == 0),
                               'mod4': BoolFilterSpec(lambda i: i['v'] % 4 == 0),
                               'mod5': BoolFilterSpec(lambda i: i['v'] % 5 == 0),
                               'mod10': BoolFilterSpec(lambda i: i['v'] % 10 == 0),
                               'all': BoolFilterSpec(None, aliases=('*',))}
            COMPARATIVE_FILTERS = {'n': CmpFilterSpec(value_type=float, value_getter=lambda i: i['v']),
                                   'n_int': CmpFilterSpec(value_type=int, value_getter=lambda i: int(i['v'])),
                                   'n_abs': CmpFilterSpec(value_type=int, value_getter=lambda i: abs(i['v']))}
            DEFAULT_FILTER = 'c'

        class FooFilterChain(FilterChain):
            filterclass = FooFilter

        self.f = FooFilterChain
        # range() only supports integers
        self.items = tuple({'v': i / 10} for i in range(-100, 105, 5))

    def do(self, filter_str, exp_values):
        self.assertEqual(tuple(item['v'] for item in self.f(filter_str).apply(self.items)),
                         exp_values)

    def test_no_filter_given(self):
        self.assertEqual(tuple(self.f().apply(self.items)), self.items)
        self.assertEqual(tuple(self.f('').apply(self.items)), self.items)

    def test_catch_all_filter(self):
        self.assertEqual(tuple(self.f('all').apply(self.items)), self.items)

    def test_OR_operator(self):
        self.do('mod3|mod5', (-10, -9, -6, -5, -3, 0, 3, 5, 6, 9, 10))
        self.do('mod5|mod3', (-10, -9, -6, -5, -3, 0, 3, 5, 6, 9, 10))
        self.do('mod5|n_abs=7', (-10, -7, -5, 0, 5, 7, 10))
        self.do('n=7|mod3', (-9, -6, -3, 0, 3, 6, 7, 9))
        self.do('mod5|mod3|n_int=7', (-10, -9, -6, -5, -3, 0, 3, 5, 6, 7, 7.5, 9, 10))
        self.do('n=-4.5|mod5|mod3|n_int=7', (-10, -9, -6, -5, -4.5, -3, 0, 3, 5, 6, 7, 7.5, 9, 10))

    def test_AND_operator(self):
        self.do('mod3&positive', (0, 3, 6, 9))
        self.do('mod3&n_abs=3', (-3, 3))
        self.do('mod3&n_abs=3&positive', (3,))
        self.do('mod3&mod2', (-6, 0, 6))
        self.do('mod3&mod2&n!=0', (-6, 6))
        self.do('mod3&mod2&n>=0', (0, 6))

    def test_combined_OR_and_AND_operators(self):
        self.do('mod3&mod2|positive&n_int>7', (-6, 0, 6, 8, 8.5, 9, 9.5, 10))
        self.do('positive&n_int>7|mod3&mod2', (-6, 0, 6, 8, 8.5, 9, 9.5, 10))
        self.do('!positive&mod2&n_abs<=4|positive&mod3&n_abs<=6', (-4, -2, 0, 3, 6))

    def test_match(self):
        for item in self.items:
            self.assertEqual(self.f('mod2').match(item), item['v'] % 2 == 0)
            self.assertEqual(self.f('!mod2').match(item), item['v'] % 2 != 0)
            self.assertEqual(self.f('mod3').match(item), item['v'] % 3 == 0)
            self.assertEqual(self.f('!mod3').match(item), item['v'] % 3 != 0)
            self.assertEqual(self.f('n_abs>0').match(item), abs(item['v']) > 0)
            self.assertEqual(self.f('n_abs!>0').match(item), abs(item['v']) <= 0)
