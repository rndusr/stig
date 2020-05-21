import unittest

from stig.utils import cliparser


class Test_on_any_substr(unittest.TestCase):
    def test_multiple_substrings(self):
        self.assertEqual(cliparser._on_any_substr('=foo!=bar>=baz<', 0, ('=','!=', '>=', '<')), (True, '=', 0, 0))
        self.assertEqual(cliparser._on_any_substr('=foo!=bar>=baz<', 1, ('=','!=', '>=', '<')), (False, '', None, None))
        self.assertEqual(cliparser._on_any_substr('=foo!=bar>=baz<', 2, ('=','!=', '>=', '<')), (False, '', None, None))
        self.assertEqual(cliparser._on_any_substr('=foo!=bar>=baz<', 3, ('=','!=', '>=', '<')), (False, '', None, None))
        self.assertEqual(cliparser._on_any_substr('=foo!=bar>=baz<', 4, ('=','!=', '>=', '<')), (True, '!=', 4, 0))
        self.assertEqual(cliparser._on_any_substr('=foo!=bar>=baz<', 5, ('=','!=', '>=', '<')), (True, '!=', 4, 1))
        self.assertEqual(cliparser._on_any_substr('=foo!=bar>=baz<', 6, ('=','!=', '>=', '<')), (False, '', None, None))
        self.assertEqual(cliparser._on_any_substr('=foo!=bar>=baz<', 7, ('=','!=', '>=', '<')), (False, '', None, None))
        self.assertEqual(cliparser._on_any_substr('=foo!=bar>=baz<', 8, ('=','!=', '>=', '<')), (False, '', None, None))
        self.assertEqual(cliparser._on_any_substr('=foo!=bar>=baz<', 9, ('=','!=', '>=', '<')), (True, '>=', 9, 0))
        self.assertEqual(cliparser._on_any_substr('=foo!=bar>=baz<', 10, ('=','!=', '>=', '<')), (True, '>=', 9, 1))
        self.assertEqual(cliparser._on_any_substr('=foo!=bar>=baz<', 11, ('=','!=', '>=', '<')), (False, '', None, None))
        self.assertEqual(cliparser._on_any_substr('=foo!=bar>=baz<', 12, ('=','!=', '>=', '<')), (False, '', None, None))
        self.assertEqual(cliparser._on_any_substr('=foo!=bar>=baz<', 13, ('=','!=', '>=', '<')), (False, '', None, None))
        self.assertEqual(cliparser._on_any_substr('=foo!=bar>=baz<', 14, ('=','!=', '>=', '<')), (True, '<', 14, 0))

    def test_leading_substrings(self):
        self.assertEqual(cliparser._on_any_substr('=foo', 0, ('=','!=')), (True, '=', 0, 0))
        self.assertEqual(cliparser._on_any_substr('=foo', 1, ('=','!=')), (False, '', None, None))

        self.assertEqual(cliparser._on_any_substr('!=foo', 0, ('=','!=')), (True, '!=', 0, 0))
        self.assertEqual(cliparser._on_any_substr('!=foo', 1, ('=','!=')), (True, '!=', 0, 1))
        self.assertEqual(cliparser._on_any_substr('!=foo', 2, ('=','!=')), (False, '', None, None))

    def test_trailing_substrings(self):
        self.assertEqual(cliparser._on_any_substr('foo=', 2, ('=','!=')), (False, '', None, None))
        self.assertEqual(cliparser._on_any_substr('foo=', 3, ('=','!=')), (True, '=', 3, 0))

        self.assertEqual(cliparser._on_any_substr('foo!=', 2, ('=','!=')), (False, '', None, None))
        self.assertEqual(cliparser._on_any_substr('foo!=', 3, ('=','!=')), (True, '!=', 3, 0))
        self.assertEqual(cliparser._on_any_substr('foo!=', 4, ('=','!=')), (True, '!=', 3, 1))

    def test_consecutive_substrings(self):
        self.assertEqual(cliparser._on_any_substr('==', 0, ('=','!=')), (True, '=', 0, 0))
        self.assertEqual(cliparser._on_any_substr('==', 1, ('=','!=')), (True, '=', 1, 0))

        self.assertEqual(cliparser._on_any_substr('!=..', 0, ('..','!=')), (True, '!=', 0, 0))
        self.assertEqual(cliparser._on_any_substr('!=..', 1, ('..','!=')), (True, '!=', 0, 1))
        self.assertEqual(cliparser._on_any_substr('!=..', 2, ('..','!=')), (True, '..', 2, 0))
        self.assertEqual(cliparser._on_any_substr('!=..', 3, ('..','!=')), (True, '..', 2, 1))

    def test_incomplete_multichar_substrings(self):
        self.assertEqual(cliparser._on_any_substr('foo!>bar', 3, ('!>=','!=')), (False, '', None, None))
        self.assertEqual(cliparser._on_any_substr('foo!>bar', 4, ('!>=','!=')), (False, '', None, None))
        self.assertEqual(cliparser._on_any_substr('foo!>=bar', 5, ('!>=','!=')), (True, '!>=', 3, 2))
        self.assertEqual(cliparser._on_any_substr('foo!>=bar', 4, ('!>=','!=')), (True, '!>=', 3, 1))
        self.assertEqual(cliparser._on_any_substr('foo!>=bar', 3, ('!>=','!=')), (True, '!>=', 3, 0))

        self.assertEqual(cliparser._on_any_substr('foo!bar', 3, ('!>=','!=')), (False, '', None, None))
        self.assertEqual(cliparser._on_any_substr('foo!=bar', 3, ('!>=','!=')), (True, '!=', 3, 0))
        self.assertEqual(cliparser._on_any_substr('foo!=bar', 4, ('!>=','!=')), (True, '!=', 3, 1))

    def test_consecutive_multichar_substrings_with_single_character(self):
        self.assertEqual(cliparser._on_any_substr('foo!!!!!!bar', 2, ('!!',)), (False, '', None, None))
        self.assertEqual(cliparser._on_any_substr('foo!!!!!!bar', 3, ('!!',)), (True, '!!', 3, 0))
        self.assertEqual(cliparser._on_any_substr('foo!!!!!!bar', 4, ('!!',)), (True, '!!', 3, 1))
        self.assertEqual(cliparser._on_any_substr('foo!!!!!!bar', 5, ('!!',)), (True, '!!', 5, 0))
        self.assertEqual(cliparser._on_any_substr('foo!!!!!!bar', 6, ('!!',)), (True, '!!', 5, 1))
        self.assertEqual(cliparser._on_any_substr('foo!!!!!!bar', 7, ('!!',)), (True, '!!', 7, 0))
        self.assertEqual(cliparser._on_any_substr('foo!!!!!!bar', 8, ('!!',)), (True, '!!', 7, 1))
        self.assertEqual(cliparser._on_any_substr('foo!!!!!!bar', 9, ('!!',)), (False, '', None, None))

    def test_consecutive_multichar_substrings_with_single_character_and_mismatch_at_the_end(self):
        self.assertEqual(cliparser._on_any_substr('foo!!!bar', 2, ('!!',)), (False, '', None, None))
        self.assertEqual(cliparser._on_any_substr('foo!!!bar', 3, ('!!',)), (True, '!!', 3, 0))
        self.assertEqual(cliparser._on_any_substr('foo!!!bar', 4, ('!!',)), (True, '!!', 3, 1))
        self.assertEqual(cliparser._on_any_substr('foo!!!bar', 5, ('!!',)), (False, '', None, None))

    def test_consecutive_multichar_substrings_with_single_character_at_start(self):
        self.assertEqual(cliparser._on_any_substr('!!!!!!!', 0, ('!!!',)), (True, '!!!', 0, 0))
        self.assertEqual(cliparser._on_any_substr('!!!!!!!', 1, ('!!!',)), (True, '!!!', 0, 1))
        self.assertEqual(cliparser._on_any_substr('!!!!!!!', 2, ('!!!',)), (True, '!!!', 0, 2))
        self.assertEqual(cliparser._on_any_substr('!!!!!!!', 3, ('!!!',)), (True, '!!!', 3, 0))
        self.assertEqual(cliparser._on_any_substr('!!!!!!!', 4, ('!!!',)), (True, '!!!', 3, 1))
        self.assertEqual(cliparser._on_any_substr('!!!!!!!', 5, ('!!!',)), (True, '!!!', 3, 2))
        self.assertEqual(cliparser._on_any_substr('!!!!!!!', 6, ('!!!',)), (False, '', None, None))


class Test_parse(unittest.TestCase):
    def do(self, string, *, exp, **kwargs):
        self.maxDiff = None
        chars = tuple(cliparser._parse(string, **kwargs))
        self.assertEqual(chars, tuple(exp))

    def test_defaults__space(self):
        self.do(r'a b',
                exp=(cliparser.Char('a'),
                     cliparser.Char(' ', string=' ', delim=' ', is_special=True),
                     cliparser.Char('b')))

    def test_defaults__escaped_space(self):
        self.do(r'a\ b',
                exp=(cliparser.Char('a'),
                     cliparser.Char('\\', string='\\', escape='\\', is_special=True),
                     cliparser.Char(' ', string=' ', delim=' ', is_escaped=True, escape='\\'),
                     cliparser.Char('b')))

    def test_defaults__backslash_before_regular_character_is_not_escaped(self):
        self.do(r'\a',
                exp=(cliparser.Char('\\', string='\\', escape='\\', is_special=True),
                     cliparser.Char('a')))

    def test_defaults__doublequoted_space(self):
        self.do(r'"a b"',
                exp=(cliparser.Char('"', string='"', quote='"', is_special=True),
                     cliparser.Char('a', quote='"', is_quoted=True),
                     cliparser.Char(' ', string=' ', quote='"', is_quoted=True, delim=' '),
                     cliparser.Char('b', quote='"', is_quoted=True),
                     cliparser.Char('"', string='"', quote='"', is_special=True)))

    def test_defaults__singlequoted_space(self):
        self.do(r"'a b'",
                exp=(cliparser.Char("'", string="'", quote="'", is_special=True),
                     cliparser.Char('a', quote="'", is_quoted=True),
                     cliparser.Char(' ', string=' ', quote="'", is_quoted=True, delim=' '),
                     cliparser.Char('b', quote="'", is_quoted=True),
                     cliparser.Char("'", string="'", quote="'", is_special=True)))

    def test_defaults__escaped_singlequote_between_singlequotes(self):
        self.do(r"'a\'b'",
                exp=(cliparser.Char("'", string="'", quote="'", is_special=True),
                     cliparser.Char('a', quote="'", is_quoted=True),
                     cliparser.Char('\\', string='\\', quote="'", is_quoted=True, escape='\\', is_special=True),
                     cliparser.Char("'", string="'", quote="'", is_quoted=True, is_escaped=True, escape='\\'),
                     cliparser.Char('b', quote="'", is_quoted=True),
                     cliparser.Char("'", string="'", quote="'", is_special=True)))

    def test_defaults__escaped_doublequote_between_singlequotes(self):
        self.do(r'"a\"b"',
                exp=(cliparser.Char('"', string='"', quote='"', is_special=True),
                     cliparser.Char('a', quote='"', is_quoted=True),
                     cliparser.Char('\\', string='\\', quote='"', is_quoted=True, escape='\\', is_special=True),
                     cliparser.Char('"', string='"', quote='"', is_quoted=True, is_escaped=True, escape='\\'),
                     cliparser.Char('b', quote='"', is_quoted=True),
                     cliparser.Char('"', string='"', quote='"', is_special=True)))

    def test_defaults__backslash_between_quotes_is_regular_character(self):
        self.do(r'"a\b"',
                exp=(cliparser.Char('"', string='"', quote='"', is_special=True),
                     cliparser.Char('a', quote='"', is_quoted=True),
                     cliparser.Char('\\', string='\\', quote='"', is_quoted=True, escape='\\'),
                     cliparser.Char('b', quote='"', is_quoted=True),
                     cliparser.Char('"', string='"', quote='"', is_special=True)))

    def test_defaults__backslash_before_closing_quote_must_be_escaped(self):
        self.do(r'"a\\"',
                exp=(cliparser.Char('"', string='"', quote='"', is_special=True),
                     cliparser.Char('a', quote='"', is_quoted=True),
                     cliparser.Char('\\', string='\\', quote='"', is_quoted=True, escape='\\', is_special=True),
                     cliparser.Char('\\', string='\\', quote='"', is_quoted=True, escape='\\', is_escaped=True),
                     cliparser.Char('"', string='"', quote='"', is_special=True)))

    def test_multichar_delim(self):
        self.do(r'a //b%ac', delims=('//', '%a'),
                exp=(cliparser.Char('a'),
                     cliparser.Char(' '),
                     cliparser.Char('/', string='//', delim='//', is_special=True),
                     cliparser.Char('/', string='//', delim='//', is_special=True),
                     cliparser.Char('b'),
                     cliparser.Char('%', string='%a', delim='%a', is_special=True),
                     cliparser.Char('a', string='%a', delim='%a', is_special=True),
                     cliparser.Char('c')))

    def test_incomplete_multichar_delim_at_end(self):
        self.do(r'a12', delims=('123',),
                exp=(cliparser.Char('a'),
                     cliparser.Char('1'),
                     cliparser.Char('2')))

    def test_incomplete_multichar_delim_at_start(self):
        self.do(r'12a', delims=('123',),
                exp=(cliparser.Char('1'),
                     cliparser.Char('2'),
                     cliparser.Char('a')))

    def test_multichar_escape(self):
        self.do(r':..:. :.', escapes=('.:.',),
                exp=(cliparser.Char(':'),
                     cliparser.Char('.'),
                     cliparser.Char('.', string='.:.', escape='.:.', is_special=True),
                     cliparser.Char(':', string='.:.', escape='.:.', is_special=True),
                     cliparser.Char('.', string='.:.', escape='.:.', is_special=True),
                     cliparser.Char(' ', string=' ', delim=' ', is_escaped=True, escape='.:.'),
                     cliparser.Char(':'),
                     cliparser.Char('.')))

    def test_multichar_quote(self):
        self.do(r'::a :: |::||::', quotes=('::', '||'),
                exp=(cliparser.Char(':', string='::', quote='::', is_special=True),
                     cliparser.Char(':', string='::', quote='::', is_special=True),
                     cliparser.Char('a', quote='::', is_quoted=True),
                     cliparser.Char(' ', string=' ', quote='::', is_quoted=True, delim=' '),
                     cliparser.Char(':', string='::', quote='::', is_special=True),
                     cliparser.Char(':', string='::', quote='::', is_special=True),
                     cliparser.Char(' ', string=' ', delim=' ', is_special=True),
                     cliparser.Char('|'),
                     cliparser.Char(':', string='::', quote='::', is_special=True),
                     cliparser.Char(':', string='::', quote='::', is_special=True),
                     cliparser.Char('|', string='||', quote='::', is_quoted=True),
                     cliparser.Char('|', string='||', quote='::', is_quoted=True),
                     cliparser.Char(':', quote='::', string='::', is_special=True),
                     cliparser.Char(':', quote='::', string='::', is_special=True)))

    def test_escaped_multichar_quote(self):
        self.do(r'\::a b\::', quotes=('::',),
                exp=(cliparser.Char('\\', string='\\', escape='\\', is_special=True),
                     cliparser.Char(':', string='::', quote='::', escape='\\', is_escaped=True),
                     cliparser.Char(':', string='::', quote='::', escape='\\', is_escaped=True),
                     cliparser.Char('a'),
                     cliparser.Char(' ', string=' ', delim=' ', is_special=True),
                     cliparser.Char('b'),
                     cliparser.Char('\\', string='\\', escape='\\', is_special=True),
                     cliparser.Char(':', string='::', quote='::', escape='\\', is_escaped=True),
                     cliparser.Char(':', string='::', quote='::', escape='\\', is_escaped=True)))

    def test_escaped_multichar_escapes(self):
        self.do(r'a!!!! b', escapes=('!!',),
                exp=(
                    cliparser.Char('a'),
                    cliparser.Char('!', string='!!', escape='!!', is_special=True),
                    cliparser.Char('!', string='!!', escape='!!', is_special=True),
                    cliparser.Char('!', string='!!', escape='!!', is_escaped=True),
                    cliparser.Char('!', string='!!', escape='!!', is_escaped=True),
                    cliparser.Char(' ', string=' ', delim=' ', is_special=True),
                    cliparser.Char('b')))


class Test_escape(unittest.TestCase):
    def test_spaces(self):
        self.assertEqual(cliparser.escape('foo bar baz'), r'foo\ bar\ baz')
        self.assertEqual(cliparser.escape('foo bar baz', curpos=3), (r'foo\ bar\ baz', 3))
        self.assertEqual(cliparser.escape('foo bar baz', curpos=4), (r'foo\ bar\ baz', 5))
        self.assertEqual(cliparser.escape('foo bar baz', curpos=5), (r'foo\ bar\ baz', 6))
        self.assertEqual(cliparser.escape('foo bar baz', curpos=7), (r'foo\ bar\ baz', 8))
        self.assertEqual(cliparser.escape('foo bar baz', curpos=8), (r'foo\ bar\ baz', 10))
        self.assertEqual(cliparser.escape('foo bar baz', curpos=9), (r'foo\ bar\ baz', 11))

    def test_single_quotes(self):
        self.assertEqual(cliparser.escape('''foo's'''), r'''foo\'s''')
        self.assertEqual(cliparser.escape('''foo's''', curpos=3), (r'''foo\'s''', 3))
        self.assertEqual(cliparser.escape('''foo's''', curpos=4), (r'''foo\'s''', 5))
        self.assertEqual(cliparser.escape('''foo's''', curpos=5), (r'''foo\'s''', 6))

    def test_escaped_single_quotes(self):
        self.assertEqual(cliparser.escape(r'''foo\'s'''), r'''foo\\\'s''')
        self.assertEqual(cliparser.escape(r'''foo\'s''', curpos=3), (r'''foo\\\'s''', 3))
        self.assertEqual(cliparser.escape(r'''foo\'s''', curpos=4), (r'''foo\\\'s''', 5))
        self.assertEqual(cliparser.escape(r'''foo\'s''', curpos=5), (r'''foo\\\'s''', 7))
        self.assertEqual(cliparser.escape(r'''foo\'s''', curpos=6), (r'''foo\\\'s''', 8))

    def test_double_quotes(self):
        self.assertEqual(cliparser.escape('''"foo"'''), r'''\"foo\"''')
        self.assertEqual(cliparser.escape('''"foo"''', curpos=0), (r'''\"foo\"''', 0))
        self.assertEqual(cliparser.escape('''"foo"''', curpos=1), (r'''\"foo\"''', 2))
        self.assertEqual(cliparser.escape('''"foo"''', curpos=2), (r'''\"foo\"''', 3))
        self.assertEqual(cliparser.escape('''"foo"''', curpos=3), (r'''\"foo\"''', 4))
        self.assertEqual(cliparser.escape('''"foo"''', curpos=4), (r'''\"foo\"''', 5))
        self.assertEqual(cliparser.escape('''"foo"''', curpos=5), (r'''\"foo\"''', 7))

    def test_escaped_double_quotes(self):
        self.assertEqual(cliparser.escape(r'''\"foo\"'''), r'''\\\"foo\\\"''')
        self.assertEqual(cliparser.escape(r'''\"foo\"''', curpos=0), (r'''\\\"foo\\\"''', 0))
        self.assertEqual(cliparser.escape(r'''\"foo\"''', curpos=1), (r'''\\\"foo\\\"''', 2))
        self.assertEqual(cliparser.escape(r'''\"foo\"''', curpos=2), (r'''\\\"foo\\\"''', 4))
        self.assertEqual(cliparser.escape(r'''\"foo\"''', curpos=3), (r'''\\\"foo\\\"''', 5))
        self.assertEqual(cliparser.escape(r'''\"foo\"''', curpos=4), (r'''\\\"foo\\\"''', 6))
        self.assertEqual(cliparser.escape(r'''\"foo\"''', curpos=5), (r'''\\\"foo\\\"''', 7))
        self.assertEqual(cliparser.escape(r'''\"foo\"''', curpos=6), (r'''\\\"foo\\\"''', 9))
        self.assertEqual(cliparser.escape(r'''\"foo\"''', curpos=7), (r'''\\\"foo\\\"''', 11))

    def test_backslashes(self):
        self.assertEqual(cliparser.escape(r'foo \bar'), r'foo\ \\bar')
        self.assertEqual(cliparser.escape(r'foo \\bar'), r'foo\ \\\\bar')
        self.assertEqual(cliparser.escape(r'foo \\\bar'), r'foo\ \\\\\\bar')
        self.assertEqual(cliparser.escape(r'foo \\bar', curpos=3), (r'foo\ \\\\bar', 3))
        self.assertEqual(cliparser.escape(r'foo \\bar', curpos=4), (r'foo\ \\\\bar', 5))
        self.assertEqual(cliparser.escape(r'foo \\bar', curpos=5), (r'foo\ \\\\bar', 7))
        self.assertEqual(cliparser.escape(r'foo \\bar', curpos=6), (r'foo\ \\\\bar', 9))
        self.assertEqual(cliparser.escape(r'foo \\bar', curpos=7), (r'foo\ \\\\bar', 10))

    def test_multichar_delims(self):
        self.assertEqual(cliparser.escape(r'foo.bar-.baz', delims=('.', '-.')), r'foo\.bar\-\.baz')
        self.assertEqual(cliparser.escape(r'foo.bar-.baz', delims=('.', '-.'), curpos=3), (r'foo\.bar\-\.baz', 3))
        self.assertEqual(cliparser.escape(r'foo.bar-.baz', delims=('.', '-.'), curpos=4), (r'foo\.bar\-\.baz', 5))
        self.assertEqual(cliparser.escape(r'foo.bar-.baz', delims=('.', '-.'), curpos=5), (r'foo\.bar\-\.baz', 6))
        self.assertEqual(cliparser.escape(r'foo.bar-.baz', delims=('.', '-.'), curpos=7), (r'foo\.bar\-\.baz', 8))
        self.assertEqual(cliparser.escape(r'foo.bar--baz', delims=('.', '--'), curpos=8), (r'foo\.bar\-\-baz', 10))
        self.assertEqual(cliparser.escape(r'foo.bar--baz', delims=('.', '--'), curpos=9), (r'foo\.bar\-\-baz', 12))
        self.assertEqual(cliparser.escape(r'foo.bar--baz', delims=('.', '--'), curpos=10), (r'foo\.bar\-\-baz', 13))

    def test_multichar_escapes(self):
        self.assertEqual(cliparser.escape('foo?!?bar$baz', escapes=('$', '!?')), 'foo?$!$?bar$$baz')
        self.assertEqual(cliparser.escape('foo!?bar$baz', escapes=('$', '!?'), curpos=3), ('foo$!$?bar$$baz', 3))
        self.assertEqual(cliparser.escape('foo!?bar$baz', escapes=('$', '!?'), curpos=4), ('foo$!$?bar$$baz', 5))
        self.assertEqual(cliparser.escape('foo!?bar$baz', escapes=('$', '!?'), curpos=5), ('foo$!$?bar$$baz', 7))
        self.assertEqual(cliparser.escape('foo!?bar$baz', escapes=('$', '!?'), curpos=6), ('foo$!$?bar$$baz', 8))
        self.assertEqual(cliparser.escape('foo!?bar$baz', escapes=('$', '!?'), curpos=8), ('foo$!$?bar$$baz', 10))
        self.assertEqual(cliparser.escape('foo!?bar$baz', escapes=('$', '!?'), curpos=9), ('foo$!$?bar$$baz', 12))
        self.assertEqual(cliparser.escape('foo!?bar$baz', escapes=('$', '!?'), curpos=10), ('foo$!$?bar$$baz', 13))

    def test_multichar_quotes(self):
        self.assertEqual(cliparser.escape('|::foo bar::: baz|', quotes=('|', '::')), r'\|::foo bar::: baz\|')
        self.assertEqual(cliparser.escape('::foo: |bar baz|::', quotes=('|', '::')), r'\:\:foo: |bar baz|\:\:')
        self.assertEqual(cliparser.escape('::foo: |bar baz|::', quotes=('|', '::'), curpos=0), (r'\:\:foo: |bar baz|\:\:', 0))
        self.assertEqual(cliparser.escape('::foo: |bar baz|::', quotes=('|', '::'), curpos=1), (r'\:\:foo: |bar baz|\:\:', 2))
        self.assertEqual(cliparser.escape('::foo: |bar baz|::', quotes=('|', '::'), curpos=2), (r'\:\:foo: |bar baz|\:\:', 4))
        self.assertEqual(cliparser.escape('::foo: |bar baz|::', quotes=('|', '::'), curpos=3), (r'\:\:foo: |bar baz|\:\:', 5))
        self.assertEqual(cliparser.escape('::foo: |bar baz|::', quotes=('|', '::'), curpos=4), (r'\:\:foo: |bar baz|\:\:', 6))
        self.assertEqual(cliparser.escape('::foo: |bar baz|::', quotes=('|', '::'), curpos=5), (r'\:\:foo: |bar baz|\:\:', 7))
        self.assertEqual(cliparser.escape('::foo: |bar baz|::', quotes=('|', '::'), curpos=6), (r'\:\:foo: |bar baz|\:\:', 8))
        self.assertEqual(cliparser.escape('::foo: |bar baz|::', quotes=('|', '::'), curpos=7), (r'\:\:foo: |bar baz|\:\:', 9))
        self.assertEqual(cliparser.escape('::foo: |bar baz|::', quotes=('|', '::'), curpos=8), (r'\:\:foo: |bar baz|\:\:', 10))
        self.assertEqual(cliparser.escape('::foo: |bar baz|::', quotes=('|', '::'), curpos=9), (r'\:\:foo: |bar baz|\:\:', 11))
        self.assertEqual(cliparser.escape(':!foo: |bar baz|:!', quotes=('|', ':!'), curpos=10), (r'\:\!foo: |bar baz|\:\!', 12))
        self.assertEqual(cliparser.escape(':!foo: |bar baz|:!', quotes=('|', ':!'), curpos=11), (r'\:\!foo: |bar baz|\:\!', 13))
        self.assertEqual(cliparser.escape(':!foo: |bar baz|:!', quotes=('|', ':!'), curpos=12), (r'\:\!foo: |bar baz|\:\!', 14))
        self.assertEqual(cliparser.escape(':!foo: |bar baz|:!', quotes=('|', ':!'), curpos=13), (r'\:\!foo: |bar baz|\:\!', 15))
        self.assertEqual(cliparser.escape(':!foo: |bar baz|:!', quotes=('|', ':!'), curpos=14), (r'\:\!foo: |bar baz|\:\!', 16))
        self.assertEqual(cliparser.escape(':!foo: |bar baz|:!', quotes=('|', ':!'), curpos=15), (r'\:\!foo: |bar baz|\:\!', 17))
        self.assertEqual(cliparser.escape(':!foo: |bar baz|:!', quotes=('|', ':!'), curpos=16), (r'\:\!foo: |bar baz|\:\!', 18))
        self.assertEqual(cliparser.escape(':!foo: |bar baz|:!', quotes=('|', ':!'), curpos=17), (r'\:\!foo: |bar baz|\:\!', 20))
        self.assertEqual(cliparser.escape(':!foo: |bar baz|:!', quotes=('|', ':!'), curpos=18), (r'\:\!foo: |bar baz|\:\!', 22))


class Test_quote(unittest.TestCase):
    def test_no_quoting_needed(self):
        self.assertEqual(cliparser.quote('foo'), 'foo')
        self.assertEqual(cliparser.quote('foo', curpos=0), ('foo', 0))
        self.assertEqual(cliparser.quote('foo', curpos=1), ('foo', 1))
        self.assertEqual(cliparser.quote('foo', curpos=2), ('foo', 2))
        self.assertEqual(cliparser.quote('foo', curpos=3), ('foo', 3))

    def test_space(self):
        self.assertEqual(cliparser.quote('foo bar baz'), '"foo bar baz"')
        for i in range(11):
            self.assertEqual(cliparser.quote('foo bar baz', curpos=i), ('"foo bar baz"', i + 1))
        self.assertEqual(cliparser.quote('foo bar baz', curpos=11), ('"foo bar baz"', 13))

    def test_backslash(self):
        self.assertEqual(cliparser.quote(r'foo\bar\baz'), r'"foo\bar\baz"')
        for i in range(11):
            self.assertEqual(cliparser.quote(r'foo\bar\baz', curpos=i), (r'"foo\bar\baz"', i + 1))
        self.assertEqual(cliparser.quote(r'foo\bar\baz', curpos=11), (r'"foo\bar\baz"', 13))

    def test_single_quote(self):
        self.assertEqual(cliparser.quote("foo'bar'baz"), '''"foo'bar'baz"''')
        for i in range(11):
            self.assertEqual(cliparser.quote("foo'bar'baz", curpos=i), ('''"foo'bar'baz"''', i + 1))
        self.assertEqual(cliparser.quote("foo'bar'baz", curpos=11), ('''"foo'bar'baz"''', 13))

    def test_double_quote(self):
        self.assertEqual(cliparser.quote('''foo"bar"baz'''), """'foo"bar"baz'""")
        for i in range(11):
            self.assertEqual(cliparser.quote('''foo"bar"baz''', curpos=i), ("""'foo"bar"baz'""", i + 1))
        self.assertEqual(cliparser.quote('''foo"bar"baz''', curpos=11), ("""'foo"bar"baz'""", 13))

    def test_mixed_quotes(self):
        self.assertEqual(cliparser.quote('''foo 'bar' "baz"'''), r'''"foo 'bar' \"baz\""''')
        self.assertEqual(cliparser.quote('''foo 'bar' "baz"''', curpos=0), (r'''"foo 'bar' \"baz\""''', 1))
        self.assertEqual(cliparser.quote('''foo 'bar' "baz"''', curpos=1), (r'''"foo 'bar' \"baz\""''', 2))
        self.assertEqual(cliparser.quote('''foo 'bar' "baz"''', curpos=2), (r'''"foo 'bar' \"baz\""''', 3))
        self.assertEqual(cliparser.quote('''foo 'bar' "baz"''', curpos=3), (r'''"foo 'bar' \"baz\""''', 4))
        self.assertEqual(cliparser.quote('''foo 'bar' "baz"''', curpos=4), (r'''"foo 'bar' \"baz\""''', 5))
        self.assertEqual(cliparser.quote('''foo 'bar' "baz"''', curpos=5), (r'''"foo 'bar' \"baz\""''', 6))
        self.assertEqual(cliparser.quote('''foo 'bar' "baz"''', curpos=6), (r'''"foo 'bar' \"baz\""''', 7))
        self.assertEqual(cliparser.quote('''foo 'bar' "baz"''', curpos=7), (r'''"foo 'bar' \"baz\""''', 8))
        self.assertEqual(cliparser.quote('''foo 'bar' "baz"''', curpos=8), (r'''"foo 'bar' \"baz\""''', 9))
        self.assertEqual(cliparser.quote('''foo 'bar' "baz"''', curpos=9), (r'''"foo 'bar' \"baz\""''', 10))
        self.assertEqual(cliparser.quote('''foo 'bar' "baz"''', curpos=10), (r'''"foo 'bar' \"baz\""''', 11))
        self.assertEqual(cliparser.quote('''foo 'bar' "baz"''', curpos=11), (r'''"foo 'bar' \"baz\""''', 13))
        self.assertEqual(cliparser.quote('''foo 'bar' "baz"''', curpos=12), (r'''"foo 'bar' \"baz\""''', 14))
        self.assertEqual(cliparser.quote('''foo 'bar' "baz"''', curpos=13), (r'''"foo 'bar' \"baz\""''', 15))
        self.assertEqual(cliparser.quote('''foo 'bar' "baz"''', curpos=14), (r'''"foo 'bar' \"baz\""''', 16))
        self.assertEqual(cliparser.quote('''foo 'bar' "baz"''', curpos=15), (r'''"foo 'bar' \"baz\""''', 19))

    def test_multichar_delims(self):
        self.assertEqual(cliparser.quote('''fooSTOPbarSTOPbaz'''), r'''fooSTOPbarSTOPbaz''')
        self.assertEqual(cliparser.quote('''fooSTOPbarSTOPbaz''', delims=('STOP',)), r'''"fooSTOPbarSTOPbaz"''')

    def test_multichar_escapes(self):
        self.assertEqual(cliparser.quote('''fooNObarNObaz'''), r'''fooNObarNObaz''')
        self.assertEqual(cliparser.quote('''fooNObarNObaz''', escapes=('NO',)), r'''"fooNObarNObaz"''')

    def test_multichar_quotes(self):
        self.assertEqual(cliparser.quote('''foo bar baz''', quotes=(':::',)), r''':::foo bar baz:::''')


class Test_is_escaped(unittest.TestCase):
    def test_no_special_characters(self):
        self.assertFalse(cliparser.is_escaped(r'foo'))

    def test_escaped(self):
        self.assertTrue(cliparser.is_escaped(r'foo\ bar'))
        self.assertTrue(cliparser.is_escaped(r'foo\'s\ bar'))
        self.assertTrue(cliparser.is_escaped(r'foo\'s\ \"bar\"'))
        self.assertTrue(cliparser.is_escaped(r'foo\'s\ \"bar\" \\o/'))

    def test_quoted(self):
        self.assertFalse(cliparser.is_escaped('"foo bar"'))
        self.assertFalse(cliparser.is_escaped("foo' 'bar"))
        self.assertFalse(cliparser.is_escaped('fo"o b"ar'))
        self.assertFalse(cliparser.is_escaped('foo "\bar"'))
        self.assertFalse(cliparser.is_escaped('foo "bar\"'))
        self.assertFalse(cliparser.is_escaped('foo "bar\\"'))

    def test_multichar_escapes(self):
        self.assertTrue(cliparser.is_escaped('fooXXX bar', escapes=('XXX',)))
        self.assertFalse(cliparser.is_escaped('fooXX bar', escapes=('XXX',)))
        self.assertTrue(cliparser.is_escaped('fooXYZ bar', escapes=('XYZ',)))


class Test_plaintext(unittest.TestCase):
    def test_backslash_escapes_space(self):
        self.assertEqual(cliparser.plaintext(r'foo\ bar\ baz'), 'foo bar baz')
        self.assertEqual(cliparser.plaintext(r'foo\ bar\ baz', curpos=0), ('foo bar baz', 0))
        self.assertEqual(cliparser.plaintext(r'foo\ bar\ baz', curpos=1), ('foo bar baz', 1))
        self.assertEqual(cliparser.plaintext(r'foo\ bar\ baz', curpos=2), ('foo bar baz', 2))
        self.assertEqual(cliparser.plaintext(r'foo\ bar\ baz', curpos=3), ('foo bar baz', 3))
        self.assertEqual(cliparser.plaintext(r'foo\ bar\ baz', curpos=4), ('foo bar baz', 3))
        self.assertEqual(cliparser.plaintext(r'foo\ bar\ baz', curpos=5), ('foo bar baz', 4))
        self.assertEqual(cliparser.plaintext(r'foo\ bar\ baz', curpos=6), ('foo bar baz', 5))
        self.assertEqual(cliparser.plaintext(r'foo\ bar\ baz', curpos=7), ('foo bar baz', 6))
        self.assertEqual(cliparser.plaintext(r'foo\ bar\ baz', curpos=8), ('foo bar baz', 7))
        self.assertEqual(cliparser.plaintext(r'foo\ bar\ baz', curpos=9), ('foo bar baz', 7))
        self.assertEqual(cliparser.plaintext(r'foo\ bar\ baz', curpos=10), ('foo bar baz', 8))
        self.assertEqual(cliparser.plaintext(r'foo\ bar\ baz', curpos=11), ('foo bar baz', 9))
        self.assertEqual(cliparser.plaintext(r'foo\ bar\ baz', curpos=12), ('foo bar baz', 10))
        self.assertEqual(cliparser.plaintext(r'foo\ bar\ baz', curpos=13), ('foo bar baz', 11))

    def test_backslash_escapes_backslash(self):
        self.assertEqual(cliparser.plaintext(r'foo\\ bar\\\\ baz'), r'foo\ bar\\ baz')
        self.assertEqual(cliparser.plaintext(r'foo\\ bar\\\\ baz', curpos=0), (r'foo\ bar\\ baz', 0))
        self.assertEqual(cliparser.plaintext(r'foo\\ bar\\\\ baz', curpos=1), (r'foo\ bar\\ baz', 1))
        self.assertEqual(cliparser.plaintext(r'foo\\ bar\\\\ baz', curpos=2), (r'foo\ bar\\ baz', 2))
        self.assertEqual(cliparser.plaintext(r'foo\\ bar\\\\ baz', curpos=3), (r'foo\ bar\\ baz', 3))
        self.assertEqual(cliparser.plaintext(r'foo\\ bar\\\\ baz', curpos=4), (r'foo\ bar\\ baz', 3))
        self.assertEqual(cliparser.plaintext(r'foo\\ bar\\\\ baz', curpos=5), (r'foo\ bar\\ baz', 4))
        self.assertEqual(cliparser.plaintext(r'foo\\ bar\\\\ baz', curpos=6), (r'foo\ bar\\ baz', 5))
        self.assertEqual(cliparser.plaintext(r'foo\\ bar\\\\ baz', curpos=7), (r'foo\ bar\\ baz', 6))
        self.assertEqual(cliparser.plaintext(r'foo\\ bar\\\\ baz', curpos=8), (r'foo\ bar\\ baz', 7))
        self.assertEqual(cliparser.plaintext(r'foo\\ bar\\\\ baz', curpos=9), (r'foo\ bar\\ baz', 8))
        self.assertEqual(cliparser.plaintext(r'foo\\ bar\\\\ baz', curpos=10), (r'foo\ bar\\ baz', 8))
        self.assertEqual(cliparser.plaintext(r'foo\\ bar\\\\ baz', curpos=11), (r'foo\ bar\\ baz', 9))
        self.assertEqual(cliparser.plaintext(r'foo\\ bar\\\\ baz', curpos=12), (r'foo\ bar\\ baz', 9))
        self.assertEqual(cliparser.plaintext(r'foo\\ bar\\\\ baz', curpos=13), (r'foo\ bar\\ baz', 10))
        self.assertEqual(cliparser.plaintext(r'foo\\ bar\\\\ baz', curpos=14), (r'foo\ bar\\ baz', 11))
        self.assertEqual(cliparser.plaintext(r'foo\\ bar\\\\ baz', curpos=15), (r'foo\ bar\\ baz', 12))
        self.assertEqual(cliparser.plaintext(r'foo\\ bar\\\\ baz', curpos=16), (r'foo\ bar\\ baz', 13))
        self.assertEqual(cliparser.plaintext(r'foo\\ bar\\\\ baz', curpos=17), (r'foo\ bar\\ baz', 14))

    def test_blackslash_escapes_space_after_escaped_backslash(self):
        self.assertEqual(cliparser.plaintext(r'foo\\\ bar\\\\\ baz'), r'foo\ bar\\ baz')
        self.assertEqual(cliparser.plaintext(r'foo\\\ bar\\\\\ baz', curpos=0), (r'foo\ bar\\ baz', 0))
        self.assertEqual(cliparser.plaintext(r'foo\\\ bar\\\\\ baz', curpos=1), (r'foo\ bar\\ baz', 1))
        self.assertEqual(cliparser.plaintext(r'foo\\\ bar\\\\\ baz', curpos=2), (r'foo\ bar\\ baz', 2))
        self.assertEqual(cliparser.plaintext(r'foo\\\ bar\\\\\ baz', curpos=3), (r'foo\ bar\\ baz', 3))
        self.assertEqual(cliparser.plaintext(r'foo\\\ bar\\\\\ baz', curpos=4), (r'foo\ bar\\ baz', 3))
        self.assertEqual(cliparser.plaintext(r'foo\\\ bar\\\\\ baz', curpos=5), (r'foo\ bar\\ baz', 4))
        self.assertEqual(cliparser.plaintext(r'foo\\\ bar\\\\\ baz', curpos=6), (r'foo\ bar\\ baz', 4))
        self.assertEqual(cliparser.plaintext(r'foo\\\ bar\\\\\ baz', curpos=7), (r'foo\ bar\\ baz', 5))
        self.assertEqual(cliparser.plaintext(r'foo\\\ bar\\\\\ baz', curpos=8), (r'foo\ bar\\ baz', 6))
        self.assertEqual(cliparser.plaintext(r'foo\\\ bar\\\\\ baz', curpos=9), (r'foo\ bar\\ baz', 7))
        self.assertEqual(cliparser.plaintext(r'foo\\\ bar\\\\\ baz', curpos=10), (r'foo\ bar\\ baz', 8))
        self.assertEqual(cliparser.plaintext(r'foo\\\ bar\\\\\ baz', curpos=11), (r'foo\ bar\\ baz', 8))
        self.assertEqual(cliparser.plaintext(r'foo\\\ bar\\\\\ baz', curpos=12), (r'foo\ bar\\ baz', 9))
        self.assertEqual(cliparser.plaintext(r'foo\\\ bar\\\\\ baz', curpos=13), (r'foo\ bar\\ baz', 9))
        self.assertEqual(cliparser.plaintext(r'foo\\\ bar\\\\\ baz', curpos=14), (r'foo\ bar\\ baz', 10))
        self.assertEqual(cliparser.plaintext(r'foo\\\ bar\\\\\ baz', curpos=15), (r'foo\ bar\\ baz', 10))
        self.assertEqual(cliparser.plaintext(r'foo\\\ bar\\\\\ baz', curpos=16), (r'foo\ bar\\ baz', 11))
        self.assertEqual(cliparser.plaintext(r'foo\\\ bar\\\\\ baz', curpos=17), (r'foo\ bar\\ baz', 12))
        self.assertEqual(cliparser.plaintext(r'foo\\\ bar\\\\\ baz', curpos=18), (r'foo\ bar\\ baz', 13))

    def test_last_character_is_backslash(self):
        self.assertEqual(cliparser.plaintext('foo\\'), 'foo')
        self.assertEqual(cliparser.plaintext('foo\\', curpos=0), ('foo', 0))
        self.assertEqual(cliparser.plaintext('foo\\', curpos=1), ('foo', 1))
        self.assertEqual(cliparser.plaintext('foo\\', curpos=2), ('foo', 2))
        self.assertEqual(cliparser.plaintext('foo\\', curpos=3), ('foo', 3))
        self.assertEqual(cliparser.plaintext('foo\\', curpos=4), ('foo', 3))
        self.assertEqual(cliparser.plaintext('foo\\', curpos=5), ('foo', 3))

    def test_last_character_is_escaped_space(self):
        self.assertEqual(cliparser.plaintext(r'foo\ '), 'foo ')
        self.assertEqual(cliparser.plaintext(r'foo\  '), 'foo ')
        self.assertEqual(cliparser.plaintext(r'foo\   '), 'foo ')
        self.assertEqual(cliparser.plaintext(r'foo\   ', curpos=0), ('foo ', 0))
        self.assertEqual(cliparser.plaintext(r'foo\   ', curpos=1), ('foo ', 1))
        self.assertEqual(cliparser.plaintext(r'foo\   ', curpos=2), ('foo ', 2))
        self.assertEqual(cliparser.plaintext(r'foo\   ', curpos=3), ('foo ', 3))
        self.assertEqual(cliparser.plaintext(r'foo\   ', curpos=4), ('foo ', 3))
        self.assertEqual(cliparser.plaintext(r'foo\   ', curpos=5), ('foo ', 4))
        self.assertEqual(cliparser.plaintext(r'foo\   ', curpos=6), ('foo ', 4))
        self.assertEqual(cliparser.plaintext(r'foo\   ', curpos=7), ('foo ', 4))

    def test_single_quotes(self):
        self.assertEqual(cliparser.plaintext("'foo' 'b'ar b'az'"), 'foo bar baz')
        self.assertEqual(cliparser.plaintext("'foo' 'b'ar b'az'", curpos=0), ('foo bar baz', 0))
        self.assertEqual(cliparser.plaintext("'foo' 'b'ar b'az'", curpos=1), ('foo bar baz', 0))
        self.assertEqual(cliparser.plaintext("'foo' 'b'ar b'az'", curpos=2), ('foo bar baz', 1))
        self.assertEqual(cliparser.plaintext("'foo' 'b'ar b'az'", curpos=3), ('foo bar baz', 2))
        self.assertEqual(cliparser.plaintext("'foo' 'b'ar b'az'", curpos=4), ('foo bar baz', 3))
        self.assertEqual(cliparser.plaintext("'foo' 'b'ar b'az'", curpos=5), ('foo bar baz', 3))
        self.assertEqual(cliparser.plaintext("'foo' 'b'ar b'az'", curpos=6), ('foo bar baz', 4))
        self.assertEqual(cliparser.plaintext("'foo' 'b'ar b'az'", curpos=7), ('foo bar baz', 4))
        self.assertEqual(cliparser.plaintext("'foo' 'b'ar b'az'", curpos=8), ('foo bar baz', 5))
        self.assertEqual(cliparser.plaintext("'foo' 'b'ar b'az'", curpos=9), ('foo bar baz', 5))
        self.assertEqual(cliparser.plaintext("'foo' 'b'ar b'az'", curpos=10), ('foo bar baz', 6))
        self.assertEqual(cliparser.plaintext("'foo' 'b'ar b'az'", curpos=11), ('foo bar baz', 7))
        self.assertEqual(cliparser.plaintext("'foo' 'b'ar b'az'", curpos=12), ('foo bar baz', 8))
        self.assertEqual(cliparser.plaintext("'foo' 'b'ar b'az'", curpos=13), ('foo bar baz', 9))
        self.assertEqual(cliparser.plaintext("'foo' 'b'ar b'az'", curpos=14), ('foo bar baz', 9))
        self.assertEqual(cliparser.plaintext("'foo' 'b'ar b'az'", curpos=15), ('foo bar baz', 10))
        self.assertEqual(cliparser.plaintext("'foo' 'b'ar b'az'", curpos=16), ('foo bar baz', 11))
        self.assertEqual(cliparser.plaintext("'foo' 'b'ar b'az'", curpos=17), ('foo bar baz', 11))

    def test_double_quotes(self):
        self.assertEqual(cliparser.plaintext('"foo" "b"ar b"az"'), "foo bar baz")
        self.assertEqual(cliparser.plaintext('"foo" "b"ar b"az"', curpos=0), ("foo bar baz", 0))
        self.assertEqual(cliparser.plaintext('"foo" "b"ar b"az"', curpos=1), ("foo bar baz", 0))
        self.assertEqual(cliparser.plaintext('"foo" "b"ar b"az"', curpos=2), ("foo bar baz", 1))
        self.assertEqual(cliparser.plaintext('"foo" "b"ar b"az"', curpos=3), ("foo bar baz", 2))
        self.assertEqual(cliparser.plaintext('"foo" "b"ar b"az"', curpos=4), ("foo bar baz", 3))
        self.assertEqual(cliparser.plaintext('"foo" "b"ar b"az"', curpos=5), ("foo bar baz", 3))
        self.assertEqual(cliparser.plaintext('"foo" "b"ar b"az"', curpos=6), ("foo bar baz", 4))
        self.assertEqual(cliparser.plaintext('"foo" "b"ar b"az"', curpos=7), ("foo bar baz", 4))
        self.assertEqual(cliparser.plaintext('"foo" "b"ar b"az"', curpos=8), ("foo bar baz", 5))
        self.assertEqual(cliparser.plaintext('"foo" "b"ar b"az"', curpos=9), ("foo bar baz", 5))
        self.assertEqual(cliparser.plaintext('"foo" "b"ar b"az"', curpos=10), ("foo bar baz", 6))
        self.assertEqual(cliparser.plaintext('"foo" "b"ar b"az"', curpos=11), ("foo bar baz", 7))
        self.assertEqual(cliparser.plaintext('"foo" "b"ar b"az"', curpos=12), ("foo bar baz", 8))
        self.assertEqual(cliparser.plaintext('"foo" "b"ar b"az"', curpos=13), ("foo bar baz", 9))
        self.assertEqual(cliparser.plaintext('"foo" "b"ar b"az"', curpos=14), ("foo bar baz", 9))
        self.assertEqual(cliparser.plaintext('"foo" "b"ar b"az"', curpos=15), ("foo bar baz", 10))
        self.assertEqual(cliparser.plaintext('"foo" "b"ar b"az"', curpos=16), ("foo bar baz", 11))
        self.assertEqual(cliparser.plaintext('"foo" "b"ar b"az"', curpos=17), ("foo bar baz", 11))

    def test_double_quotes_in_single_quotes(self):
        self.assertEqual(cliparser.plaintext("""'"foo" "bar" "baz"'"""), '"foo" "bar" "baz"')
        self.assertEqual(cliparser.plaintext("""'"foo" "bar" "baz"'""", curpos=0), ('"foo" "bar" "baz"', 0))
        for i in range(1, 19):
            self.assertEqual(cliparser.plaintext("""'"foo" "bar" "baz"'""", curpos=i), ('"foo" "bar" "baz"', i - 1))
        self.assertEqual(cliparser.plaintext("""'"foo" "bar" "baz"'""", curpos=19), ('"foo" "bar" "baz"', 17))

    def test_single_quotes_in_double_quotes(self):
        self.assertEqual(cliparser.plaintext('''"'foo' 'bar' 'baz'"'''), "'foo' 'bar' 'baz'")
        self.assertEqual(cliparser.plaintext('''"'foo' 'bar' 'baz'"''', curpos=0), ("'foo' 'bar' 'baz'", 0))
        for i in range(1, 19):
            self.assertEqual(cliparser.plaintext('''"'foo' 'bar' 'baz'"''', curpos=i), ("'foo' 'bar' 'baz'", i - 1))
        self.assertEqual(cliparser.plaintext('''"'foo' 'bar' 'baz'"''', curpos=19), ("'foo' 'bar' 'baz'", 17))

    def test_mixed_quotes(self):
        self.assertEqual(cliparser.plaintext(r"""'\'foo\' "bar" \'baz\''"""), """'foo' "bar" 'baz'""")
        self.assertEqual(cliparser.plaintext(r'''"'foo' \"bar\" 'baz'"'''), """'foo' "bar" 'baz'""")
        self.assertEqual(cliparser.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=0), ("""'foo' "bar" 'baz'""", 0))
        self.assertEqual(cliparser.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=1), ("""'foo' "bar" 'baz'""", 0))
        self.assertEqual(cliparser.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=2), ("""'foo' "bar" 'baz'""", 1))
        self.assertEqual(cliparser.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=3), ("""'foo' "bar" 'baz'""", 2))
        self.assertEqual(cliparser.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=4), ("""'foo' "bar" 'baz'""", 3))
        self.assertEqual(cliparser.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=5), ("""'foo' "bar" 'baz'""", 4))
        self.assertEqual(cliparser.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=6), ("""'foo' "bar" 'baz'""", 5))
        self.assertEqual(cliparser.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=7), ("""'foo' "bar" 'baz'""", 6))
        self.assertEqual(cliparser.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=8), ("""'foo' "bar" 'baz'""", 6))
        self.assertEqual(cliparser.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=9), ("""'foo' "bar" 'baz'""", 7))
        self.assertEqual(cliparser.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=10), ("""'foo' "bar" 'baz'""", 8))
        self.assertEqual(cliparser.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=11), ("""'foo' "bar" 'baz'""", 9))
        self.assertEqual(cliparser.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=12), ("""'foo' "bar" 'baz'""", 10))
        self.assertEqual(cliparser.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=13), ("""'foo' "bar" 'baz'""", 10))
        self.assertEqual(cliparser.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=14), ("""'foo' "bar" 'baz'""", 11))
        self.assertEqual(cliparser.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=15), ("""'foo' "bar" 'baz'""", 12))
        self.assertEqual(cliparser.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=16), ("""'foo' "bar" 'baz'""", 13))
        self.assertEqual(cliparser.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=17), ("""'foo' "bar" 'baz'""", 14))
        self.assertEqual(cliparser.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=18), ("""'foo' "bar" 'baz'""", 15))
        self.assertEqual(cliparser.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=19), ("""'foo' "bar" 'baz'""", 16))
        self.assertEqual(cliparser.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=20), ("""'foo' "bar" 'baz'""", 17))
        self.assertEqual(cliparser.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=21), ("""'foo' "bar" 'baz'""", 17))

    def test_backslash_in_single_quotes_before_nonquotes(self):
        self.assertEqual(cliparser.plaintext(r"""'f\oo' bar"""), r"""f\oo bar""")
        self.assertEqual(cliparser.plaintext(r"""'f\oo' bar""", curpos=0), (r"""f\oo bar""", 0))
        self.assertEqual(cliparser.plaintext(r"""'f\oo' bar""", curpos=1), (r"""f\oo bar""", 0))
        self.assertEqual(cliparser.plaintext(r"""'f\oo' bar""", curpos=2), (r"""f\oo bar""", 1))
        self.assertEqual(cliparser.plaintext(r"""'f\oo' bar""", curpos=3), (r"""f\oo bar""", 2))
        self.assertEqual(cliparser.plaintext(r"""'f\oo' bar""", curpos=4), (r"""f\oo bar""", 3))
        self.assertEqual(cliparser.plaintext(r"""'f\oo' bar""", curpos=5), (r"""f\oo bar""", 4))
        self.assertEqual(cliparser.plaintext(r"""'f\oo' bar""", curpos=6), (r"""f\oo bar""", 4))
        self.assertEqual(cliparser.plaintext(r"""'f\oo' bar""", curpos=7), (r"""f\oo bar""", 5))

    def test_backslash_in_double_quotes_before_nonquotes(self):
        self.assertEqual(cliparser.plaintext(r'''foo "b\r"'''), r'''foo b\r''')
        self.assertEqual(cliparser.plaintext(r'''foo "b\r"''', curpos=4), (r'''foo b\r''', 4))
        self.assertEqual(cliparser.plaintext(r'''foo "b\r"''', curpos=5), (r'''foo b\r''', 4))
        self.assertEqual(cliparser.plaintext(r'''foo "b\r"''', curpos=6), (r'''foo b\r''', 5))
        self.assertEqual(cliparser.plaintext(r'''foo "b\r"''', curpos=7), (r'''foo b\r''', 6))
        self.assertEqual(cliparser.plaintext(r'''foo "b\r"''', curpos=8), (r'''foo b\r''', 7))
        self.assertEqual(cliparser.plaintext(r'''foo "b\r"''', curpos=9), (r'''foo b\r''', 7))

    def test_backslash_before_single_quote_in_double_quotes(self):
        self.assertEqual(cliparser.plaintext(r'''"foo\'"'''), r"foo\'")
        self.assertEqual(cliparser.plaintext(r'''"foo\'"''', curpos=0), (r"foo\'", 0))
        self.assertEqual(cliparser.plaintext(r'''"foo\'"''', curpos=1), (r"foo\'", 0))
        self.assertEqual(cliparser.plaintext(r'''"foo\'"''', curpos=2), (r"foo\'", 1))
        self.assertEqual(cliparser.plaintext(r'''"foo\'"''', curpos=3), (r"foo\'", 2))
        self.assertEqual(cliparser.plaintext(r'''"foo\'"''', curpos=4), (r"foo\'", 3))
        self.assertEqual(cliparser.plaintext(r'''"foo\'"''', curpos=5), (r"foo\'", 4))
        self.assertEqual(cliparser.plaintext(r'''"foo\'"''', curpos=6), (r"foo\'", 5))
        self.assertEqual(cliparser.plaintext(r'''"foo\'"''', curpos=7), (r"foo\'", 5))

    def test_backslash_before_double_quote_in_single_quotes(self):
        self.assertEqual(cliparser.plaintext(r"""'foo\"'"""), r'foo\"')
        self.assertEqual(cliparser.plaintext(r"""'foo\"'""", curpos=0), (r'foo\"', 0))
        self.assertEqual(cliparser.plaintext(r"""'foo\"'""", curpos=1), (r'foo\"', 0))
        self.assertEqual(cliparser.plaintext(r"""'foo\"'""", curpos=2), (r'foo\"', 1))
        self.assertEqual(cliparser.plaintext(r"""'foo\"'""", curpos=3), (r'foo\"', 2))
        self.assertEqual(cliparser.plaintext(r"""'foo\"'""", curpos=4), (r'foo\"', 3))
        self.assertEqual(cliparser.plaintext(r"""'foo\"'""", curpos=5), (r'foo\"', 4))
        self.assertEqual(cliparser.plaintext(r"""'foo\"'""", curpos=6), (r'foo\"', 5))
        self.assertEqual(cliparser.plaintext(r"""'foo\"'""", curpos=7), (r'foo\"', 5))

    def test_escaped_backslash_before_closing_quote(self):
        self.assertEqual(cliparser.plaintext(r"'foo \\' bar"), r'foo \ bar')
        self.assertEqual(cliparser.plaintext(r"'foo \\' bar", curpos=4), (r'foo \ bar', 3))
        self.assertEqual(cliparser.plaintext(r"'foo \\' bar", curpos=5), (r'foo \ bar', 4))
        self.assertEqual(cliparser.plaintext(r"'foo \\' bar", curpos=6), (r'foo \ bar', 4))
        self.assertEqual(cliparser.plaintext(r"'foo \\' bar", curpos=7), (r'foo \ bar', 5))
        self.assertEqual(cliparser.plaintext(r"'foo \\' bar", curpos=8), (r'foo \ bar', 5))
        self.assertEqual(cliparser.plaintext(r"'foo \\' bar", curpos=9), (r'foo \ bar', 6))
        self.assertEqual(cliparser.plaintext(r"'foo \\' bar", curpos=10), (r'foo \ bar', 7))

    def test_unbalanced_single_quote(self):
        self.assertEqual(cliparser.plaintext("'foo  "), 'foo  ')
        self.assertEqual(cliparser.plaintext("'foo  ", curpos=0), ('foo  ', 0))
        self.assertEqual(cliparser.plaintext("'foo  ", curpos=1), ('foo  ', 0))
        self.assertEqual(cliparser.plaintext("'foo  ", curpos=2), ('foo  ', 1))
        self.assertEqual(cliparser.plaintext("'foo  ", curpos=3), ('foo  ', 2))
        self.assertEqual(cliparser.plaintext("'foo  ", curpos=4), ('foo  ', 3))
        self.assertEqual(cliparser.plaintext("'foo  ", curpos=5), ('foo  ', 4))
        self.assertEqual(cliparser.plaintext("'foo  ", curpos=6), ('foo  ', 5))

    def test_unbalanced_double_quote(self):
        self.assertEqual(cliparser.plaintext('"foo   '), "foo   ")
        self.assertEqual(cliparser.plaintext('"foo   ', curpos=0), ("foo   ", 0))
        self.assertEqual(cliparser.plaintext('"foo   ', curpos=1), ("foo   ", 0))
        self.assertEqual(cliparser.plaintext('"foo   ', curpos=2), ("foo   ", 1))
        self.assertEqual(cliparser.plaintext('"foo   ', curpos=3), ("foo   ", 2))
        self.assertEqual(cliparser.plaintext('"foo   ', curpos=4), ("foo   ", 3))
        self.assertEqual(cliparser.plaintext('"foo   ', curpos=5), ("foo   ", 4))
        self.assertEqual(cliparser.plaintext('"foo   ', curpos=6), ("foo   ", 5))
        self.assertEqual(cliparser.plaintext('"foo   ', curpos=7), ("foo   ", 6))

    def test_double_quotes_in_unbalanced_single_quotes(self):
        self.assertEqual(cliparser.plaintext(r''''foo\'s "bar"'''), '''foo's "bar"''')
        self.assertEqual(cliparser.plaintext(r''''foo\'s "bar"''', curpos=0), ('''foo's "bar"''', 0))
        self.assertEqual(cliparser.plaintext(r''''foo\'s "bar"''', curpos=1), ('''foo's "bar"''', 0))
        self.assertEqual(cliparser.plaintext(r''''foo\'s "bar"''', curpos=2), ('''foo's "bar"''', 1))
        self.assertEqual(cliparser.plaintext(r''''foo\'s "bar"''', curpos=3), ('''foo's "bar"''', 2))
        self.assertEqual(cliparser.plaintext(r''''foo\'s "bar"''', curpos=4), ('''foo's "bar"''', 3))
        self.assertEqual(cliparser.plaintext(r''''foo\'s "bar"''', curpos=5), ('''foo's "bar"''', 3))
        self.assertEqual(cliparser.plaintext(r''''foo\'s "bar"''', curpos=6), ('''foo's "bar"''', 4))
        self.assertEqual(cliparser.plaintext(r''''foo\'s "bar"''', curpos=7), ('''foo's "bar"''', 5))
        self.assertEqual(cliparser.plaintext(r''''foo\'s "bar"''', curpos=8), ('''foo's "bar"''', 6))
        self.assertEqual(cliparser.plaintext(r''''foo\'s "bar"''', curpos=9), ('''foo's "bar"''', 7))
        self.assertEqual(cliparser.plaintext(r''''foo\'s "bar"''', curpos=10), ('''foo's "bar"''', 8))
        self.assertEqual(cliparser.plaintext(r''''foo\'s "bar"''', curpos=11), ('''foo's "bar"''', 9))
        self.assertEqual(cliparser.plaintext(r''''foo\'s "bar"''', curpos=12), ('''foo's "bar"''', 10))

    def test_single_quotes_in_unbalanced_double_quotes(self):
        self.assertEqual(cliparser.plaintext(r'''"foo bar's'''), '''foo bar's''')
        self.assertEqual(cliparser.plaintext(r'''"foo bar's''', curpos=7), ('''foo bar's''', 6))
        self.assertEqual(cliparser.plaintext(r'''"foo bar's''', curpos=8), ('''foo bar's''', 7))
        self.assertEqual(cliparser.plaintext(r'''"foo bar's''', curpos=9), ('''foo bar's''', 8))
        self.assertEqual(cliparser.plaintext(r'''"foo bar's''', curpos=10), ('''foo bar's''', 9))

    def test_mixed_quotes_in_unbalanced_single_quotes(self):
        self.assertEqual(cliparser.plaintext(r'''f'oo\'s "bar"'''), '''foo's "bar"''')
        self.assertEqual(cliparser.plaintext(r'''f'oo\'s "bar"''', curpos=0), ('''foo's "bar"''', 0))
        self.assertEqual(cliparser.plaintext(r'''f'oo\'s "bar"''', curpos=1), ('''foo's "bar"''', 1))
        self.assertEqual(cliparser.plaintext(r'''f'oo\'s "bar"''', curpos=2), ('''foo's "bar"''', 1))
        self.assertEqual(cliparser.plaintext(r'''f'oo\'s "bar"''', curpos=3), ('''foo's "bar"''', 2))
        self.assertEqual(cliparser.plaintext(r'''f'oo\'s "bar"''', curpos=4), ('''foo's "bar"''', 3))
        self.assertEqual(cliparser.plaintext(r'''f'oo\'s "bar"''', curpos=5), ('''foo's "bar"''', 3))
        self.assertEqual(cliparser.plaintext(r'''f'oo\'s "bar"''', curpos=6), ('''foo's "bar"''', 4))
        self.assertEqual(cliparser.plaintext(r'''f'oo\'s "bar"''', curpos=7), ('''foo's "bar"''', 5))
        self.assertEqual(cliparser.plaintext(r'''f'oo\'s "bar"''', curpos=8), ('''foo's "bar"''', 6))
        self.assertEqual(cliparser.plaintext(r'''f'oo\'s "bar"''', curpos=9), ('''foo's "bar"''', 7))
        self.assertEqual(cliparser.plaintext(r'''f'oo\'s "bar"''', curpos=10), ('''foo's "bar"''', 8))
        self.assertEqual(cliparser.plaintext(r'''f'oo\'s "bar"''', curpos=11), ('''foo's "bar"''', 9))
        self.assertEqual(cliparser.plaintext(r'''f'oo\'s "bar"''', curpos=12), ('''foo's "bar"''', 10))
        self.assertEqual(cliparser.plaintext(r'''f'oo\'s "bar"''', curpos=13), ('''foo's "bar"''', 11))

    def test_mixed_quotes_in_unbalanced_double_quotes(self):
        self.assertEqual(cliparser.plaintext(r'''"foo 'b\"ar'''), '''foo 'b"ar''')
        self.assertEqual(cliparser.plaintext(r'''"foo 'b\"ar''', curpos=5), ('''foo 'b"ar''', 4))
        self.assertEqual(cliparser.plaintext(r'''"foo 'b\"ar''', curpos=6), ('''foo 'b"ar''', 5))
        self.assertEqual(cliparser.plaintext(r'''"foo 'b\"ar''', curpos=7), ('''foo 'b"ar''', 6))
        self.assertEqual(cliparser.plaintext(r'''"foo 'b\"ar''', curpos=8), ('''foo 'b"ar''', 6))
        self.assertEqual(cliparser.plaintext(r'''"foo 'b\"ar''', curpos=9), ('''foo 'b"ar''', 7))
        self.assertEqual(cliparser.plaintext(r'''"foo 'b\"ar''', curpos=10), ('''foo 'b"ar''', 8))
        self.assertEqual(cliparser.plaintext(r'''"foo 'b\"ar''', curpos=11), ('''foo 'b"ar''', 9))

    def test_unbalanced_quotes_with_trailing_spaces(self):
        self.assertEqual(cliparser.plaintext("'foo "), 'foo ')
        self.assertEqual(cliparser.plaintext('"bar  '), 'bar  ')

    def test_unbalanced_quotes_with_leading_spaces(self):
        self.assertEqual(cliparser.plaintext("' "), ' ')
        self.assertEqual(cliparser.plaintext('"  '), '  ')
        self.assertEqual(cliparser.plaintext("'   "), '   ')
        self.assertEqual(cliparser.plaintext('"    '), '    ')

    def test_unbalanced_quotes_without_actual_text(self):
        self.assertEqual(cliparser.plaintext("'"), '')
        self.assertEqual(cliparser.plaintext('"'), '')

    def test_single_quotes_with_surrounding_spaces(self):
        self.assertEqual(cliparser.plaintext(" 'foo bar' "), 'foo bar')
        self.assertEqual(cliparser.plaintext(" 'foo bar' ", curpos=0), ('foo bar', 0))
        self.assertEqual(cliparser.plaintext(" 'foo bar' ", curpos=1), ('foo bar', 0))
        self.assertEqual(cliparser.plaintext(" 'foo bar' ", curpos=2), ('foo bar', 0))
        self.assertEqual(cliparser.plaintext(" 'foo bar' ", curpos=3), ('foo bar', 1))
        self.assertEqual(cliparser.plaintext(" 'foo bar' ", curpos=4), ('foo bar', 2))
        self.assertEqual(cliparser.plaintext(" 'foo bar' ", curpos=5), ('foo bar', 3))
        self.assertEqual(cliparser.plaintext(" 'foo bar' ", curpos=6), ('foo bar', 4))
        self.assertEqual(cliparser.plaintext(" 'foo bar' ", curpos=7), ('foo bar', 5))
        self.assertEqual(cliparser.plaintext(" 'foo bar' ", curpos=8), ('foo bar', 6))
        self.assertEqual(cliparser.plaintext(" 'foo bar' ", curpos=9), ('foo bar', 7))
        self.assertEqual(cliparser.plaintext(" 'foo bar' ", curpos=10), ('foo bar', 7))
        self.assertEqual(cliparser.plaintext(" 'foo bar' ", curpos=11), ('foo bar', 7))

    def test_double_quotes_with_surrounding_spaces(self):
        self.assertEqual(cliparser.plaintext('  " foo bar "  '), ' foo bar ')
        self.assertEqual(cliparser.plaintext('  " foo bar "  ', curpos=0), (' foo bar ', 0))
        self.assertEqual(cliparser.plaintext('  " foo bar "  ', curpos=1), (' foo bar ', 0))
        self.assertEqual(cliparser.plaintext('  " foo bar "  ', curpos=2), (' foo bar ', 0))
        self.assertEqual(cliparser.plaintext('  " foo bar "  ', curpos=3), (' foo bar ', 0))
        self.assertEqual(cliparser.plaintext('  " foo bar "  ', curpos=4), (' foo bar ', 1))
        self.assertEqual(cliparser.plaintext('  " foo bar "  ', curpos=5), (' foo bar ', 2))
        self.assertEqual(cliparser.plaintext('  " foo bar "  ', curpos=6), (' foo bar ', 3))
        self.assertEqual(cliparser.plaintext('  " foo bar "  ', curpos=7), (' foo bar ', 4))
        self.assertEqual(cliparser.plaintext('  " foo bar "  ', curpos=8), (' foo bar ', 5))
        self.assertEqual(cliparser.plaintext('  " foo bar "  ', curpos=9), (' foo bar ', 6))
        self.assertEqual(cliparser.plaintext('  " foo bar "  ', curpos=10), (' foo bar ', 7))
        self.assertEqual(cliparser.plaintext('  " foo bar "  ', curpos=11), (' foo bar ', 8))
        self.assertEqual(cliparser.plaintext('  " foo bar "  ', curpos=12), (' foo bar ', 9))
        self.assertEqual(cliparser.plaintext('  " foo bar "  ', curpos=13), (' foo bar ', 9))
        self.assertEqual(cliparser.plaintext('  " foo bar "  ', curpos=14), (' foo bar ', 9))
        self.assertEqual(cliparser.plaintext('  " foo bar "  ', curpos=15), (' foo bar ', 9))


class Test_tokenize(unittest.TestCase):
    def do(self, input, output, **kwargs):
        self.assertEqual(cliparser.tokenize(input, **kwargs), output)

    def test_empty_cmdline(self):
        self.do('', [''])

    def test_consecutive_singlechar_delimiters(self):
        self.do(' ', [' '])
        self.do('  ', [' ', ' '])
        self.do('   ', [' ', ' ', ' '])

    def test_maxdelims(self):
        self.do('a:b:c:d:e', ['a:b:c:d:e'], maxdelims=0, delims=(':',))
        self.do('a:b:c:d:e', ['a', ':', 'b:c:d:e'], maxdelims=1, delims=(':',))
        self.do('a:b:c:d:e', ['a', ':', 'b', ':', 'c:d:e'], maxdelims=2, delims=(':',))
        self.do('a:b:c:d:e', ['a', ':', 'b', ':', 'c', ':', 'd:e'], maxdelims=3, delims=(':',))
        self.do('a:b:c:d:e', ['a', ':', 'b', ':', 'c', ':', 'd', ':', 'e'], maxdelims=4, delims=(':',))

    def test_consecutive_multichar_delimiters(self):
        self.do('abc', ['abc'], delims=('abc',))
        self.do('abcabc', ['abc', 'abc'], delims=('abc',))
        self.do('abcabcabc', ['abc', 'abc', 'abc'], delims=('abc',))

    def test_consecutive_incomplete_multichar_delimiters(self):
        self.do('ab', ['ab'], delims=('abc',))
        self.do('abab', ['abab'], delims=('abc',))
        self.do('ababab', ['ababab'], delims=('abc',))

    def test_leading_singlechar_delimiters(self):
        self.do('.foo', ['.', 'foo'], delims=('.',))
        self.do('..foo', ['.', '.', 'foo'], delims=('.',))
        self.do('...foo', ['.', '.', '.', 'foo'], delims=('.',))

    def test_leading_multichar_delimiters(self):
        self.do('.:foo', ['.:', 'foo'], delims=('.:', '.:!'))
        self.do('.:.:!foo', ['.:', '.:!', 'foo'], delims=('.:', '.:!'))
        self.do('.:.:!.:foo', ['.:', '.:!', '.:', 'foo'], delims=('.:', '.:!'))

    def test_trailing_singlechar_delimiters(self):
        self.do('foo.', ['foo', '.'], delims=('.',))
        self.do('foo..', ['foo', '.', '.'], delims=('.',))
        self.do('foo...', ['foo', '.', '.', '.'], delims=('.',))

    def test_trailing_multichar_delimiters(self):
        self.do('foo.:!', ['foo', '.:!'], delims=('.:', '.:!'))
        self.do('foo.:!.:', ['foo', '.:!', '.:'], delims=('.:', '.:!'))
        self.do('foo.:!.:.:!', ['foo', '.:!', '.:', '.:!'], delims=('.:', '.:!'))

    def test_spaces_between_nonspace_singlechar_delimiters(self):
        self.do('. ,', ['.', ' ', ','], delims=('.', ','))
        self.do(' . , ', [' ', '.', ' ', ',', ' '], delims=('.', ','))
        self.do('  .  ,  ', ['  ', '.', '  ', ',', '  '], delims=('.', ','))
        self.do('  ..  ,,  ', ['  ', '.', '.', '  ', ',', ',', '  '], delims=('.', ','))

    def test_spaces_between_nonspace_multichar_delimiters(self):
        self.do(':: ;;', ['::', ' ', ';;'], delims=('::', ';;'))
        self.do(' :: ;; ', [' ', '::', ' ', ';;', ' '], delims=('::', ';;'))
        self.do('  ::  ;;  ', ['  ', '::', '  ', ';;', '  '], delims=('::', ';;'))
        self.do('  :::  ;;;  ', ['  ', '::', ':  ', ';;', ';  '], delims=('::', ';;'))
        self.do('  ::::  ;;;;  ', ['  ', '::', '::', '  ', ';;', ';;', '  '], delims=('::', ';;'))

    def test_incomplete_multichar_delimiter_after_complete_multichar_delimiters(self):
        self.do('foo....bar', ['foo', '...', '.bar'], delims=('...',))
        self.do('foo.....bar', ['foo', '...', '..bar'], delims=('...',))
        self.do('..foo.....bar', ['..foo', '...', '..bar'], delims=('...',))
        self.do('...foo......bar..', ['...', 'foo', '...', '...', 'bar..'], delims=('...',))
        self.do('...foo......bar...', ['...', 'foo', '...', '...', 'bar', '...'], delims=('...',))

    def test_unescaped_singlechar_delimiter_after_escaped_singlechar_delimiter(self):
        self.do('foo!,,bar', ['foo!,', ',', 'bar'], delims=(',',), escapes=('!',))

    def test_escaping_singlechar_delimiters(self):
        self.do(r'foo!,bar', [r'foo!,bar'], delims=(',',), escapes=('!',))
        self.do(r'!,foo', [r'!,foo'], delims=(',',), escapes=('!',))
        self.do(r'foo!,', [r'foo!,'], delims=(',',), escapes=('!',))

    def test_escaping_multichar_delimiters(self):
        self.do('foo!:::bar', ['foo!:::bar'], delims=(':::',), escapes=('!',))
        self.do('foo:!::bar', ['foo:!::bar'], delims=(':::',), escapes=('!',))
        self.do('foo::!:bar', ['foo::!:bar'], delims=(':::',), escapes=('!',))
        self.do('foo:::!bar', ['foo', ':::', '!bar'], delims=(':::',), escapes=('!',))

        self.do('!:::foo', ['!:::foo'], delims=(':::',), escapes=('!',))
        self.do(':!::foo', [':!::foo'], delims=(':::',), escapes=('!',))
        self.do('::!:foo', ['::!:foo'], delims=(':::',), escapes=('!',))
        self.do(':::!foo', [':::', '!foo'], delims=(':::',), escapes=('!',))

        self.do('foo!:::', ['foo!:::'], delims=(':::',), escapes=('!',))
        self.do('foo:!::', ['foo:!::'], delims=(':::',), escapes=('!',))
        self.do('foo::!:', ['foo::!:'], delims=(':::',), escapes=('!',))

    def test_escaping_singlechar_escapes(self):
        self.do('foo!!,bar', ['foo!!', ',', 'bar'], delims=(',',), escapes=('!',))
        self.do('foo!!!,bar', ['foo!!!,bar'], delims=(',',), escapes=('!',))
        self.do('foo!!!!,bar', ['foo!!!!', ',', 'bar'], delims=(',',), escapes=('!',))
        self.do('!!,foo', ['!!', ',', 'foo'], delims=(',',), escapes=('!',))
        self.do('foo!!,', ['foo!!', ','], delims=(',',), escapes=('!',))

    def test_escaping_multichar_escapes(self):
        self.do('foo!!!!:::bar', ['foo!!!!', ':::', 'bar'], delims=(':::',), escapes=('!!',))
        self.do('foo:!!!!::bar', ['foo:!!!!::bar'], delims=(':::',), escapes=('!!',))

        self.do('!!!!:::foo', ['!!!!', ':::', 'foo'], delims=(':::',), escapes=('!!',))
        self.do(':!!!!::foo', [':!!!!::foo'], delims=(':::',), escapes=('!!',))

        self.do('foo!!!!:::', ['foo!!!!', ':::'], delims=(':::',), escapes=('!!',))
        self.do('foo:::!!!!', ['foo', ':::', '!!!!'], delims=(':::',), escapes=('!!',))

    def test_singlechar_quotes(self):
        self.do(r':foo bar: baz', [r':foo bar:', ' ', 'baz'], quotes=(':',))
        self.do(r'f:oo ba:r baz', [r'f:oo ba:r', ' ', 'baz'], quotes=(':',))
        self.do(r'foo :bar baz:', [r'foo', ' ', ':bar baz:'], quotes=(':',))
        self.do(r'foo b:ar ba:z', [r'foo', ' ', 'b:ar ba:z'], quotes=(':',))

    def test_multichar_quotes(self):
        self.do(r'::foo bar:: baz', [r'::foo bar::', ' ', 'baz'], quotes=('::',))
        self.do(r'foo:: ::bar baz', [r'foo:: ::bar', ' ', 'baz'], quotes=('::',))
        self.do(r'foo ::bar baz::', [r'foo', ' ', '::bar baz::'], quotes=('::',))
        self.do(r'foo ba::r b::az', [r'foo', ' ', 'ba::r b::az'], quotes=('::',))

    def test_escaping_singlechar_quotes(self):
        self.do(r'!:foo bar!: baz', [r'!:foo', ' ', 'bar!:', ' ', 'baz'], quotes=(':',), escapes=('!',))
        self.do(r'f!:oo ba!:r baz', [r'f!:oo', ' ', 'ba!:r', ' ', 'baz'], quotes=(':',), escapes=('!',))
        self.do(r'foo !:bar baz!:', [r'foo', ' ', '!:bar', ' ', 'baz!:'], quotes=(':',), escapes=('!',))
        self.do(r'foo b!:ar b!:az', [r'foo', ' ', 'b!:ar', ' ', 'b!:az'], quotes=(':',), escapes=('!',))
        self.do(r'foo b!:ar b:az', [r'foo', ' ', 'b!:ar', ' ', 'b:az'], quotes=(':',), escapes=('!',))

    def test_escaping_multichar_quotes(self):
        self.do(r'!!::foo bar!!:: baz', [r'!!::foo', ' ', 'bar!!::', ' ', 'baz'], quotes=('::',), escapes=('!!',))
        self.do(r'foo !!::bar baz!!::', [r'foo', ' ', '!!::bar', ' ', 'baz!!::'], quotes=('::',), escapes=('!!',))
        self.do(r'foo !!::bar baz::', [r'foo', ' ', '!!::bar', ' ', 'baz::'], quotes=('::',), escapes=('!!',))

    def test_unbalanced_singlechar_quotes(self):
        self.do(r':foo bar baz', [r':foo bar baz'], quotes=(':',))
        self.do(r'foo: bar baz', [r'foo: bar baz'], quotes=(':',))
        self.do(r'foo :bar baz', [r'foo', ' ', ':bar baz'], quotes=(':',))

    def test_unbalanced_multichar_quotes(self):
        self.do(r'::foo bar baz', [r'::foo bar baz'], quotes=('::',))
        self.do(r'fo::o bar baz', [r'fo::o bar baz'], quotes=('::',))
        self.do(r'foo ba::r baz', [r'foo', ' ', 'ba::r baz'], quotes=('::',))

    def test_quoting_singlechar_quotes_with_other_singlechar_quotes(self):
        self.do(r':foo ;bar; : baz', [r':foo ;bar; :', ' ', 'baz'], quotes=(':', ';'))
        self.do(r'fo;o: b;ar baz', [r'fo;o: b;ar', ' ', 'baz'], quotes=(':', ';'))
        self.do(r'foo ;:;: bar baz', [r'foo', ' ', ';:;: bar baz'], quotes=(':', ';'))

    def test_quoting_singlechar_quotes_with_multichar_quotes(self):
        self.do(r'foo ::;:: bar', [r'foo', ' ', '::;::', ' ', 'bar'], quotes=('::', ';'))
        self.do(r'foo::; bar:: baz', [r'foo::; bar::', ' ', 'baz'], quotes=('::', ';'))

    def test_quoting_multichar_quotes_with_other_multichar_quotes(self):
        self.do(r'foo ::;;bar;;:: baz', [r'foo', ' ', '::;;bar;;::', ' ', 'baz'], quotes=('::', ';;'))
        self.do(r'::;;foo bar:: ;; baz', [r'::;;foo bar::', ' ', ';; baz'], quotes=('::', ';;'))

    def test_quoting_multichar_quotes_with_singlechar_quotes(self):
        self.do(r'foo :;;bar;; baz:', [r'foo', ' ', ':;;bar;; baz:'], quotes=(':', ';;'))
        self.do(r':foo ;;: bar:;;: baz', [r':foo ;;:', ' ', 'bar:;;:', ' ', 'baz'], quotes=(':', ';;'))

    def test_escapes_between_singlechar_quotes(self):
        self.do(r':f!oo! !bar: baz', [r':f!oo! !bar:', ' ', 'baz'], quotes=(':',), escapes=('!',))

    def test_escapes_before_singlechar_opening_quote(self):
        self.do(r':foo bar: baz', [r':foo bar:', ' ', 'baz'], quotes=(':',), escapes=('!',))
        self.do(r'!:foo bar: baz', [r'!:foo', ' ', 'bar: baz'], quotes=(':',), escapes=('!',))
        self.do(r'!!:foo bar: baz', [r'!!:foo bar:', ' ', 'baz'], quotes=(':',), escapes=('!',))

    def test_escapes_before_singlechar_closing_quote(self):
        self.do(r':foo bar: baz', [r':foo bar:', ' ', 'baz'], quotes=(':',), escapes=('!',))
        self.do(r':foo bar!: baz', [r':foo bar!: baz'], quotes=(':',), escapes=('!',))
        self.do(r':foo bar!!: baz', [r':foo bar!!:', ' ', 'baz'], quotes=(':',), escapes=('!',))

    def test_escapes_before_multichar_opening_quote(self):
        self.do(r'::foo bar:: baz', [r'::foo bar::', ' ', 'baz'], quotes=('::',), escapes=('!!',))
        self.do(r'!::foo bar:: baz', [r'!::foo bar::', ' ', 'baz'], quotes=('::',), escapes=('!!',))
        self.do(r'!!::foo bar:: baz', [r'!!::foo', ' ', 'bar:: baz'], quotes=('::',), escapes=('!!',))
        self.do(r'!!!::foo bar:: baz', [r'!!!::foo bar::', ' ', 'baz'], quotes=('::',), escapes=('!!',))
        self.do(r'!!!!::foo bar:: baz', [r'!!!!::foo bar::', ' ', 'baz'], quotes=('::',), escapes=('!!',))

    def test_escapes_before_multichar_closing_quote(self):
        self.do(r'::foo bar:: baz', [r'::foo bar::', ' ', 'baz'], quotes=('::',), escapes=('!!',))
        self.do(r'::foo bar!:: baz', [r'::foo bar!::', ' ', 'baz'], quotes=('::',), escapes=('!!',))
        self.do(r'::foo bar!!:: baz', [r'::foo bar!!:: baz'], quotes=('::',), escapes=('!!',))
        self.do(r'::foo bar!!!:: baz', [r'::foo bar!!!::', ' ', 'baz'], quotes=('::',), escapes=('!!',))
        self.do(r'::foo bar!!!!:: baz', [r'::foo bar!!!!::', ' ', 'baz'], quotes=('::',), escapes=('!!',))


class Test_get_position(unittest.TestCase):
    def do(self, input, output):
        self.assertEqual(cliparser.get_position(*input), output)

    def test_everything(self):
        self.do((['foo', '|', 'bar', '|', 'baz'],  0), (0, 0))
        self.do((['foo', '|', 'bar', '|', 'baz'],  1), (0, 1))
        self.do((['foo', '|', 'bar', '|', 'baz'],  2), (0, 2))
        self.do((['foo', '|', 'bar', '|', 'baz'],  3), (0, 3))
        self.do((['foo', '|', 'bar', '|', 'baz'],  4), (1, 1))
        self.do((['foo', '|', 'bar', '|', 'baz'],  5), (2, 1))
        self.do((['foo', '|', 'bar', '|', 'baz'],  6), (2, 2))
        self.do((['foo', '|', 'bar', '|', 'baz'],  7), (2, 3))
        self.do((['foo', '|', 'bar', '|', 'baz'],  8), (3, 1))
        self.do((['foo', '|', 'bar', '|', 'baz'],  9), (4, 1))
        self.do((['foo', '|', 'bar', '|', 'baz'], 10), (4, 2))
        self.do((['foo', '|', 'bar', '|', 'baz'], 11), (4, 3))


class Test_remove_delims(unittest.TestCase):
    def do(self, input, output):
        self.assertEqual(cliparser.remove_delims(*input), output)

    def test_cursor_on_nondelimiter(self):
        for curpos in (0, 1, 2, 3):
            self.do((['foo', ':', '!', 'bar', '!', 'baz'], 0, curpos, (':', '!')), ((['foo', 'bar', 'baz'], 0, curpos)))
            self.do((['foo', ':', 'bar', '!', '!', 'baz'], 0, curpos, (':', '!')), ((['foo', 'bar', 'baz'], 0, curpos)))
            self.do((['foo', ':', 'bar', '!', 'baz', '!'], 0, curpos, (':', '!')), ((['foo', 'bar', 'baz'], 0, curpos)))
            self.do(([':', 'foo', ':', '!', 'bar', '!', 'baz'], 1, curpos, (':', '!')), ((['foo', 'bar', 'baz'], 0, curpos)))
        for curpos in (0, 1, 2, 3):
            self.do((['foo', '!', ':', 'bar', ':', 'baz'], 3, curpos, (':', '!')), ((['foo', 'bar', 'baz'], 1, curpos)))
            self.do((['foo', ':', 'bar', '!', ':', 'baz'], 2, curpos, (':', '!')), ((['foo', 'bar', 'baz'], 1, curpos)))
            self.do((['foo', ':', 'bar', '!', 'baz', ':'], 2, curpos, (':', '!')), ((['foo', 'bar', 'baz'], 1, curpos)))
            self.do((['!', 'foo', ':', 'bar', ':', 'baz'], 3, curpos, (':', '!')), ((['foo', 'bar', 'baz'], 1, curpos)))
        for curpos in (0, 1, 2, 3):
            self.do((['foo', ':', 'bar', '!', 'baz'], 4, curpos, (':', '!')), ((['foo', 'bar', 'baz'], 2, curpos)))
            self.do((['foo', ':', '!', 'bar', '!', 'baz'], 5, curpos, (':', '!')), ((['foo', 'bar', 'baz'], 2, curpos)))
            self.do((['foo', ':', 'bar', '!', ':', 'baz'], 5, curpos, (':', '!')), ((['foo', 'bar', 'baz'], 2, curpos)))
            self.do((['!', 'foo', ':', 'bar', '!', 'baz'], 5, curpos, (':', '!')), ((['foo', 'bar', 'baz'], 2, curpos)))

    def test_cursor_on_delimiter(self):
        self.do((['foo', ':', '!', 'bar', '!', 'baz'], 1, 0, (':', '!')), ((['foo', 'bar', 'baz'], 0, 3)))
        self.do((['foo', ':', '!', 'bar', '!', 'baz'], 1, 1, (':', '!')), ((['foo', 'bar', 'baz'], 0, 3)))
        self.do((['foo', ':', '!', 'bar', '!', 'baz'], 2, 0, (':', '!')), ((['foo', 'bar', 'baz'], 0, 3)))
        self.do((['foo', ':', '!', 'bar', '!', 'baz'], 2, 1, (':', '!')), ((['foo', 'bar', 'baz'], 1, 0)))
        self.do((['foo', ':', '!', 'bar', '!', 'baz'], 4, 0, (':', '!')), ((['foo', 'bar', 'baz'], 1, 3)))
        self.do((['foo', ':', '!', 'bar', '!', 'baz'], 4, 1, (':', '!')), ((['foo', 'bar', 'baz'], 2, 0)))

    def test_cursor_on_delimiter_and_last_token(self):
        for curpos in (0, 1):
            self.do((['foo', ':', 'bar', '!', 'baz', '!'], 5, curpos, (':', '!')), ((['foo', 'bar', 'baz'], 2, 3)))
            self.do((['foo', ':', 'bar', '!', 'baz', '!', ':'], 6, curpos, (':', '!')), ((['foo', 'bar', 'baz'], 2, 3)))
            self.do((['foo', ':', 'bar', '!', 'baz', '!', ':', '!'], 7, curpos, (':', '!')), ((['foo', 'bar', 'baz'], 2, 3)))

    def test_cursor_on_delimiter_and_first_token(self):
        for curpos in (0, 1):
            self.do(([':', 'foo', ':', 'bar', '!', 'baz'], 0, curpos, (':', '!')), ((['foo', 'bar', 'baz'], 0, 0)))
            for index in (0, 1):
                self.do(([':', '!', 'foo', ':', 'bar', '!', 'baz'], index, curpos, (':', '!')), ((['foo', 'bar', 'baz'], 0, 0)))
            for index in (0, 1, 2):
                self.do(([':', '!', '!', 'foo', ':', 'bar', '!', 'baz'], index, curpos, (':', '!')), ((['foo', 'bar', 'baz'], 0, 0)))


class Test_avoid_delims(unittest.TestCase):
    def do(self, input, output):
        self.assertEqual(cliparser.avoid_delims(*input), output)

    def test_no_nondelimiters(self):
        for curpos in (0, 1):
            self.do(([':'], 0, curpos, (':', '!')), ([':'], 0, curpos))
            for tokpos in (0, 1):
                self.do(([':', '!'], tokpos, curpos, (':', '!')), ([':', '!'], tokpos, curpos))
            for tokpos in (0, 1, 2):
                self.do(([':', '!', ':'], tokpos, curpos, (':', '!')), ([':', '!', ':'], tokpos, curpos))
        for curpos in (0, 1, 2):
            self.do((['::'], 0, curpos, ('::', '.:')), (['::'], 0, curpos))
            for tokpos in (0, 1):
                self.do((['::', '.:'], tokpos, curpos, (':', '!')), (['::', '.:'], tokpos, curpos))
            for tokpos in (0, 1, 2):
                self.do((['::', '.:', '.:'], tokpos, curpos, (':', '!')), (['::', '.:', '.:'], tokpos, curpos))

    def test_cursor_on_leading_delimiter(self):
        for curpos in (0, 1):
            self.do(([':', 'foo'], 0, curpos, (':',)), ([':', 'foo'], 1, 0))
            self.do(([':', ':', 'foo'], 0, curpos, (':',)), ([':', ':', 'foo'], 2, 0))
        for curpos in (0, 1, 2):
            self.do((['::', 'foo'], 0, curpos, ('::', '.:!')), (['::', 'foo'], 1, 0))
            self.do((['::', '.:!', 'foo'], 0, curpos, ('::', '.:!')), (['::', '.:!', 'foo'], 2, 0))
        for curpos in (0, 1, 2, 3):
            self.do((['.:!', 'foo'], 0, curpos, (':', '.:!')), (['.:!', 'foo'], 1, 0))
            self.do((['.:!', ':', 'foo'], 0, curpos, (':', '.:!')), (['.:!', ':', 'foo'], 2, 0))
            self.do((['.:!', '.:!', 'foo'], 0, curpos, (':', '.:!')), (['.:!', '.:!', 'foo'], 2, 0))

    def test_cursor_on_trailing_delimiter(self):
        for curpos in (0, 1):
            self.do((['foo', ':'], 1, curpos, (':',)), (['foo', ':'], 0, 3))
            self.do((['foo', ':', ':'], 2, curpos, (':',)), (['foo', ':', ':'], 0, 3))
        for curpos in (0, 1, 2):
            self.do((['foo', '::'], 1, curpos, ('::', '.:!')), (['foo', '::'], 0, 3))
            self.do((['foo', '.:!', '::'], 2, curpos, ('::', '.:!')), (['foo', '.:!', '::'], 0, 3))
        for curpos in (0, 1, 2, 3):
            self.do((['foo', '.:!'], 1, curpos, ('::', '.:!')), (['foo', '.:!'], 0, 3))
            self.do((['foo', '::', '.:!'], 2, curpos, ('::', '.:!')), (['foo', '::', '.:!'], 0, 3))

    def test_cursor_on_delimiting_delimiter(self):
        self.do((['foo', ':', 'bar'], 1, 0, (':',)), (['foo', ':', 'bar'], 0, 3))
        self.do((['foo', ':', 'bar'], 1, 1, (':',)), (['foo', ':', 'bar'], 2, 0))

        self.do((['foo', ':', '!', 'bar'], 1, 0, (':', '!')), (['foo', ':', '!', 'bar'], 0, 3))
        self.do((['foo', ':', '!', 'bar'], 1, 1, (':', '!')), (['foo', ':', '!', 'bar'], 3, 0))
        self.do((['foo', ':', '!', 'bar'], 2, 0, (':', '!')), (['foo', ':', '!', 'bar'], 3, 0))
        self.do((['foo', ':', '!', 'bar'], 2, 1, (':', '!')), (['foo', ':', '!', 'bar'], 3, 0))

        self.do((['foo', '::', 'bar'], 1, 0, ('::', '.:!')), (['foo', '::', 'bar'], 0, 3))
        self.do((['foo', '::', 'bar'], 1, 1, ('::', '.:!')), (['foo', '::', 'bar'], 2, 0))
        self.do((['foo', '::', 'bar'], 1, 2, ('::', '.:!')), (['foo', '::', 'bar'], 2, 0))
        self.do((['foo', '.:!', '::', 'bar'], 1, 0, ('::', '.:!')), (['foo', '.:!', '::', 'bar'], 0, 3))
        self.do((['foo', '.:!', '::', 'bar'], 1, 1, ('::', '.:!')), (['foo', '.:!', '::', 'bar'], 3, 0))
        self.do((['foo', '.:!', '::', 'bar'], 1, 2, ('::', '.:!')), (['foo', '.:!', '::', 'bar'], 3, 0))
        self.do((['foo', '.:!', '::', 'bar'], 1, 3, ('::', '.:!')), (['foo', '.:!', '::', 'bar'], 3, 0))
        self.do((['foo', '.:!', '::', 'bar'], 2, 0, ('::', '.:!')), (['foo', '.:!', '::', 'bar'], 3, 0))
        self.do((['foo', '.:!', '::', 'bar'], 2, 1, ('::', '.:!')), (['foo', '.:!', '::', 'bar'], 3, 0))
        self.do((['foo', '.:!', '::', 'bar'], 2, 2, ('::', '.:!')), (['foo', '.:!', '::', 'bar'], 3, 0))


class Test_maybe_insert_empty_token(unittest.TestCase):
    def do(self, input, output):
        self.assertEqual(cliparser.maybe_insert_empty_token(*input), output)

    def test_cursor_on_first_char_of_first_arg(self):
        self.do((['foo', ':', 'bar'], 0, 0, (':', '!')), (['foo', ':', 'bar'], 0, 0))
        for curpos in (0, 1):
            self.do((['!', 'foo', ':', 'bar'], 0, curpos, (':', '!')), (['', '!', 'foo', ':', 'bar'], 0, 0))

    def test_cursor_on_last_char_of_last_arg(self):
        self.do((['foo', ':', 'bar'], 2, 3, (':', '!')), (['foo', ':', 'bar'], 2, 3))
        for curpos in (0, 1):
            self.do((['foo', ':', 'bar', '!'], 3, curpos, (':', '!')), (['foo', ':', 'bar', '!', ''], 4, 0))

    def test_cursor_on_first_char_of_delimiter_with_delimiter_before(self):
        self.do((['foo', '!', ':', 'bar'], 2, 0, (':', '!')), (['foo', '!', '', ':', 'bar'], 2, 0))
        self.do((['foo', '::', '.:!', 'bar'], 2, 0, ('::', '.:!')), (['foo', '::', '', '.:!', 'bar'], 2, 0))

    def test_cursor_on_last_char_of_delimiter_with_delimiter_after(self):
        self.do((['foo', ':', '!', 'bar'], 1, 1, (':', '!')), (['foo', ':', '', '!', 'bar'], 2, 0))
        self.do((['foo', '::', '.:!', 'bar'], 1, 2, ('::', '.:!')), (['foo', '::', '', '.:!', 'bar'], 2, 0))
        self.do((['foo', '.:!', '::', 'bar'], 1, 3, ('::', '.:!')), (['foo', '.:!', '', '::', 'bar'], 2, 0))



    def test_cursor_on_last_arg_which_is_delimiter(self):
        self.do((['foo', ' '], 1, 1, (' ',)), (['foo', ' ', ''], 2, 0))



    def test_cursor_in_middle_of_multichar_delimiter(self):
        self.do((['foo', '::', '.:!', 'bar'], 1, 1, ('::', '.:!')), (['foo', ':', '', ':', '.:!', 'bar'], 2, 0))
        self.do((['foo', '::', '.:!', 'bar'], 2, 1, ('::', '.:!')), (['foo', '::', '.', '', ':!', 'bar'], 3, 0))
        self.do((['foo', '::', '.:!', 'bar'], 2, 2, ('::', '.:!')), (['foo', '::', '.:', '', '!', 'bar'], 3, 0))


class Test_remove_options(unittest.TestCase):
    def do(self, input, output):
        self.assertEqual(cliparser.remove_options(*input), output)

    def test_no_cursor_position(self):
        self.do((['foo', '--bar', 'baz'], None, None), (['foo', 'baz'], None, None))
        self.do((['foo', 'baz', '--bar'], None, None), (['foo', 'baz'], None, None))
        self.do((['foo', 'baz', '--bar', 'bam'], None, None), (['foo', 'baz', 'bam'], None, None))
        self.do((['foo', 'baz', '--bar', '-bam'], None, None), (['foo', 'baz'], None, None))

    def test_cursor_to_the_left_of_an_option(self):
        self.do((['foo', 'baz', '--bar'], 1, 0), (['foo', 'baz'], 1, 0))
        self.do((['foo', 'baz', '--bar'], 1, 1), (['foo', 'baz'], 1, 1))
        self.do((['foo', 'baz', '--bar'], 1, 2), (['foo', 'baz'], 1, 2))
        self.do((['foo', 'baz', '--bar'], 1, 3), (['foo', 'baz'], 1, 3))

    def test_cursor_to_the_right_of_an_option(self):
        self.do((['foo', '--bar', 'baz'], 2, 0), (['foo', 'baz'], 1, 0))
        self.do((['foo', '--bar', 'baz'], 2, 1), (['foo', 'baz'], 1, 1))
        self.do((['foo', '--bar', 'baz'], 2, 2), (['foo', 'baz'], 1, 2))
        self.do((['foo', '--bar', 'baz'], 2, 3), (['foo', 'baz'], 1, 3))

    def test_cursor_on_an_option(self):
        self.do((['foo', '--bar', 'baz'], 1, 0), (['foo', 'baz'], 1, 0))
        self.do((['foo', '--bar', 'baz'], 1, 1), (['foo', 'baz'], 1, 0))
        self.do((['foo', '--bar', 'baz'], 1, 2), (['foo', 'baz'], 1, 0))
        self.do((['foo', '--bar', 'baz'], 1, 3), (['foo', 'baz'], 1, 0))
        self.do((['foo', '--bar', 'baz'], 1, 4), (['foo', 'baz'], 1, 0))
        self.do((['foo', '--bar', 'baz'], 1, 5), (['foo', 'baz'], 1, 0))

    def test_cursor_on_a_parameter_with_options(self):
        opts = {('--foo', '-f'): 0, ('--bar', '-b'): 1, ('--baz', '-z'): 2}

        for opt in ('--foo', '-f'):
            self.do((['foo', opt, '1', '2', '3', '-x', 'end'], 2, 0, opts), (['foo', '1', '2', '3', 'end'], 1, 0))
            self.do((['foo', opt, '1', '2', '3', '-x', 'end'], 2, 1, opts), (['foo', '1', '2', '3', 'end'], 1, 1))
            self.do((['foo', opt, '-x'], 2, 0, opts), (['foo'], 0, 3))
            self.do((['foo', opt, '-x'], 2, 1, opts), (['foo'], 0, 3))

        for opt in ('--bar', '-b'):
            self.do((['foo', opt, '1', '2', '3', '-x', 'end'], 2, 0, opts), (['foo', '2', '3', 'end'], 1, 0))
            self.do((['foo', opt, '1', '2', '3', '-x', 'end'], 2, 1, opts), (['foo', '2', '3', 'end'], 1, 0))
            self.do((['foo', opt, '1', '-x'], 2, 0, opts), (['foo'], 0, 3))
            self.do((['foo', opt, '1', '-x'], 2, 1, opts), (['foo'], 0, 3))

        for opt in ('--baz', '-z'):
            self.do((['foo', opt, '1', '2', '3', '-x', 'end'], 3, 0, opts), (['foo', '3', 'end'], 1, 0))
            self.do((['foo', opt, '1', '2', '3', '-x', 'end'], 3, 1, opts), (['foo', '3', 'end'], 1, 0))
            self.do((['foo', opt, '1', '2', '-x'], 2, 0, opts), (['foo'], 0, 3))
            self.do((['foo', opt, '1', '2', '-x'], 2, 1, opts), (['foo'], 0, 3))

    def test_cursor_on_a_parameter_with_greedy_option(self):
        opts = {('--greedy', '-g',): '*'}
        for opt in ('--greedy', '-g'):
            self.do((['foo', opt, '1', '2', '3', '-x', 'end'], 2, 0, opts), (['foo', 'end'], 1, 0))
            self.do((['foo', opt, '1', '2', '3', '-x', 'end'], 2, 1, opts), (['foo', 'end'], 1, 0))
            self.do((['foo', opt, '-x'], 2, 0, opts), (['foo'], 0, 3))
            self.do((['foo', opt, '-x'], 2, 1, opts), (['foo'], 0, 3))

    def test_multiple_options_that_take_parameters(self):
        opts = {('-a'): 1, ('-b'): 1, ('-c'): 2}
        self.do((['foo', '-a', '1', '-b', '2', '-c', '3', '4', '-x', 'end'], 0, 0, opts),
                (['foo', 'end'], 0, 0))
        self.do((['foo', '-a', '1', 'a', '-b', '2', 'b', '-c', '3', '4', 'c', '-x', 'end'], 0, 0, opts),
                (['foo', 'a', 'b', 'c', 'end'], 0, 0))

    def test_invalid_option_spec(self):
        opts = {('-x',): 'x'}
        with self.assertRaises(ValueError):
            self.do((['foo', '-x', '1', '2', '3', '-x', 'end'], 2, 0, opts), ([], 0, 0))


class Test_get_nth_posarg_index(unittest.TestCase):
    def do(self, input, output):
        self.assertEqual(cliparser.get_nth_posarg_index(*input), output)

    def test_no_args(self):
        self.do((1, []), None)

    def test_no_posargs(self):
        self.do((1, ['-a', '-b', '-c']), None)
        self.do((1, ['-a', 'b'], {('-a',): 1}), None)
        self.do((1, ['-a', 'b', 'c'], {('-a',): 2}), None)
        self.do((1, ['-a', 'b', 'c', 'd'], {('-a',): 3}), None)
        self.do((1, ['-a', 'b', '-c', 'd'], {('-a',): 1, ('-c',): 1}), None)

    def test_only_posargs(self):
        self.do((1, ['a', 'b', 'c', 'd']), 0)
        self.do((2, ['a', 'b', 'c', 'd']), 1)
        self.do((3, ['a', 'b', 'c', 'd']), 2)
        self.do((4, ['a', 'b', 'c', 'd']), 3)
        self.do((5, ['a', 'b', 'c', 'd']), None)

    def test_options_without_parameters(self):
        self.do((1, ['-a', 'b', 'c']), 1)
        self.do((2, ['-a', 'b', 'c']), 2)
        self.do((3, ['-a', 'b', 'c']), None)
        self.do((1, ['a', '-b', 'c']), 0)
        self.do((2, ['a', '-b', 'c']), 2)
        self.do((3, ['a', '-b', 'c']), None)
        self.do((1, ['a', 'b', '-c']), 0)
        self.do((2, ['a', 'b', '-c']), 1)
        self.do((3, ['a', 'b', '-c']), None)
        self.do((1, ['-a', 'b', '-c']), 1)
        self.do((2, ['-a', 'b', '-c']), None)
        self.do((1, ['-a', '-b', '-c']), None)

    def test_options_with_parameters(self):
        options = {('-one',): 1, ('-two',): 2}
        self.do((1, ['-one', 'a', 'b', 'c'], options), 2)
        self.do((2, ['-one', 'a', 'b', 'c'], options), 3)
        self.do((3, ['-one', 'a', 'b', 'c'], options), None)
        self.do((1, ['a', '-one', 'b', 'c'], options), 0)
        self.do((2, ['a', '-one', 'b', 'c'], options), 3)
        self.do((3, ['a', '-one', 'b', 'c'], options), None)
        self.do((1, ['a', 'b', '-one', 'c'], options), 0)
        self.do((2, ['a', 'b', '-one', 'c'], options), 1)
        self.do((3, ['a', 'b', '-one', 'c'], options), None)


class Test_get_current_cmd(unittest.TestCase):
    ops = ('&', 'and', '|', 'or')

    def do(self, input, output):
        input += (self.ops,)
        self.assertEqual(cliparser.get_current_cmd(*input), output)

    def test_empty_string(self):
        self.do(([''], 0), ([''], 0))

    def test_no_operators(self):
        self.do((['foo', ' ' , 'bar', ' ', 'baz'], 0), (['foo', ' ', 'bar', ' ', 'baz'], 0))
        self.do((['foo', ' ', 'bar', ' ', 'baz'], 1), (['foo', ' ', 'bar', ' ', 'baz'], 1))
        self.do((['foo', ' ', 'bar', ' ', 'baz'], 2), (['foo', ' ', 'bar', ' ', 'baz'], 2))
        self.do((['foo', ' ', 'bar', ' ', 'baz'], 3), (['foo', ' ', 'bar', ' ', 'baz'], 3))
        self.do((['foo', ' ', 'bar', ' ', 'baz'], 4), (['foo', ' ', 'bar', ' ', 'baz'], 4))

    def test_single_char_operators(self):
        tokens = ['foo', ' ', '&', ' ', 'bar', ' ', 'baz', ' ', '|', ' ', 'bang', ' ', '-a']
        self.do((tokens, 0), (['foo', ' '], 0))
        self.do((tokens, 1), (['foo', ' '], 1))
        self.do((tokens, 2), (None, None))
        self.do((tokens, 3), ([' ', 'bar', ' ', 'baz', ' '], 0))
        self.do((tokens, 4), ([' ', 'bar', ' ', 'baz', ' '], 1))
        self.do((tokens, 5), ([' ', 'bar', ' ', 'baz', ' '], 2))
        self.do((tokens, 6), ([' ', 'bar', ' ', 'baz', ' '], 3))
        self.do((tokens, 7), ([' ', 'bar', ' ', 'baz', ' '], 4))
        self.do((tokens, 8), (None, None))
        self.do((tokens, 9), ([' ', 'bang', ' ', '-a'], 0))
        self.do((tokens, 10), ([' ', 'bang', ' ', '-a'], 1))
        self.do((tokens, 11), ([' ', 'bang', ' ', '-a'], 2))
        self.do((tokens, 12), ([' ', 'bang', ' ', '-a'], 3))

    def test_multi_char_operators(self):
        tokens = ['foo', ' ', 'and', ' ', 'bar', ' ', 'baz', ' ', 'or', ' ', 'bang', ' ', '-a']
        self.do((tokens, 0), (['foo', ' '], 0))
        self.do((tokens, 1), (['foo', ' '], 1))
        self.do((tokens, 2), (None, None))
        self.do((tokens, 3), ([' ', 'bar', ' ', 'baz', ' '], 0))
        self.do((tokens, 4), ([' ', 'bar', ' ', 'baz', ' '], 1))
        self.do((tokens, 5), ([' ', 'bar', ' ', 'baz', ' '], 2))
        self.do((tokens, 6), ([' ', 'bar', ' ', 'baz', ' '], 3))
        self.do((tokens, 7), ([' ', 'bar', ' ', 'baz', ' '], 4))
        self.do((tokens, 8), (None, None))
        self.do((tokens, 9), ([' ', 'bang', ' ', '-a'], 0))
        self.do((tokens, 10), ([' ', 'bang', ' ', '-a'], 1))
        self.do((tokens, 11), ([' ', 'bang', ' ', '-a'], 2))
        self.do((tokens, 12), ([' ', 'bang', ' ', '-a'], 3))


class TestArg(unittest.TestCase):
    def test_equality(self):
        self.assertEqual(cliparser.Arg('foo', curpos=0), cliparser.Arg('foo', curpos=0))
        self.assertNotEqual(cliparser.Arg('foo', curpos=0), cliparser.Arg('fo', curpos=0))
        self.assertNotEqual(cliparser.Arg('foo', curpos=0), cliparser.Arg('foo', curpos=1))

    def test_getitem_with_index(self):
        arg = cliparser.Arg('bar', curpos=0)
        self.assertEqual(arg[0], cliparser.Arg('b', curpos=0))
        self.assertEqual(arg[1], cliparser.Arg('a'))
        self.assertEqual(arg[2], cliparser.Arg('r'))
        arg = cliparser.Arg('bar', curpos=1)
        self.assertEqual(arg[0], cliparser.Arg('b'))
        self.assertEqual(arg[1], cliparser.Arg('a', curpos=0))
        self.assertEqual(arg[2], cliparser.Arg('r'))
        arg = cliparser.Arg('bar', curpos=2)
        self.assertEqual(arg[0], cliparser.Arg('b'))
        self.assertEqual(arg[1], cliparser.Arg('a'))
        self.assertEqual(arg[2], cliparser.Arg('r', curpos=0))
        with self.assertRaises(IndexError):
            arg[3]

    def test_getitem_with_slice(self):
        arg = cliparser.Arg('bar', curpos=0)
        self.assertEqual(arg[0:], cliparser.Arg('bar', curpos=0))
        self.assertEqual(arg[1:], cliparser.Arg('ar'))
        self.assertEqual(arg[2:], cliparser.Arg('r'))
        arg = cliparser.Arg('bar', curpos=1)
        self.assertEqual(arg[0:], cliparser.Arg('bar', curpos=1))
        self.assertEqual(arg[1:], cliparser.Arg('ar', curpos=0))
        self.assertEqual(arg[2:], cliparser.Arg('r'))
        arg = cliparser.Arg('bar', curpos=2)
        self.assertEqual(arg[0:], cliparser.Arg('bar', curpos=2))
        self.assertEqual(arg[1:], cliparser.Arg('ar', curpos=1))
        self.assertEqual(arg[2:], cliparser.Arg('r', curpos=0))

        arg = cliparser.Arg('bar', curpos=0)
        self.assertEqual(arg[:1], cliparser.Arg('b', curpos=0))
        self.assertEqual(arg[:2], cliparser.Arg('ba', curpos=0))
        self.assertEqual(arg[:3], cliparser.Arg('bar', curpos=0))
        arg = cliparser.Arg('bar', curpos=1)
        self.assertEqual(arg[:1], cliparser.Arg('b'))
        self.assertEqual(arg[:2], cliparser.Arg('ba', curpos=1))
        self.assertEqual(arg[:3], cliparser.Arg('bar', curpos=1))
        arg = cliparser.Arg('bar', curpos=2)
        self.assertEqual(arg[:1], cliparser.Arg('b'))
        self.assertEqual(arg[:2], cliparser.Arg('ba'))
        self.assertEqual(arg[:3], cliparser.Arg('bar', curpos=2))

    def test_before_cursor(self):
        self.assertEqual(cliparser.Arg('foo', curpos=0).before_cursor, '')
        self.assertEqual(cliparser.Arg('foo', curpos=1).before_cursor, 'f')
        self.assertEqual(cliparser.Arg('foo', curpos=2).before_cursor, 'fo')
        self.assertEqual(cliparser.Arg('foo', curpos=3).before_cursor, 'foo')
        self.assertIsInstance(cliparser.Arg('foo', curpos=2).before_cursor, cliparser.Arg)
        self.assertEqual(cliparser.Arg('foo', curpos=2).before_cursor.curpos, 2)

    def do(self, arg, curpos, seps, maxseps, include_seps, exp_parts, exp_curpart, exp_curpart_index, exp_curpart_curpos):
        arg = cliparser.Arg(arg, curpos)
        self.assertEqual(arg.curpos, curpos)
        parts = arg.separate(seps, maxseps=maxseps, include_seps=include_seps)
        self.assertEqual(parts, exp_parts)
        self.assertEqual(parts.curarg, exp_curpart)
        self.assertEqual(parts.curarg_index, exp_curpart_index)
        self.assertEqual(parts.curarg_curpos, exp_curpart_curpos)
        self.assertTrue(all(type(part) is cliparser.Arg for part in parts))
        self.assertTrue(type(parts.curarg) is cliparser.Arg or parts.curarg is None)

    def test_no_curpos_with_seps_included(self):
        self.do('foo/bar/baz', None, ('/',), None, True, ('foo', '/', 'bar', '/', 'baz'), None, None, None)

    def test_no_curpos_with_seps_not_included(self):
        self.do('foo/bar/baz', None, ('/',), None, False, ('foo', 'bar', 'baz'), None, None, None)

    def test_separate_at_singlechar_separator_including_separators(self):
        self.do('foo/bar/baz',  0, ('/',), None, True, ('foo', '/', 'bar', '/', 'baz'), 'foo', 0, 0)
        self.do('foo/bar/baz',  1, ('/',), None, True, ('foo', '/', 'bar', '/', 'baz'), 'foo', 0, 1)
        self.do('foo/bar/baz',  2, ('/',), None, True, ('foo', '/', 'bar', '/', 'baz'), 'foo', 0, 2)
        self.do('foo/bar/baz',  3, ('/',), None, True, ('foo', '/', 'bar', '/', 'baz'), 'foo', 0, 3)
        self.do('foo/bar/baz',  4, ('/',), None, True, ('foo', '/', 'bar', '/', 'baz'), 'bar', 2, 0)
        self.do('foo/bar/baz',  5, ('/',), None, True, ('foo', '/', 'bar', '/', 'baz'), 'bar', 2, 1)
        self.do('foo/bar/baz',  6, ('/',), None, True, ('foo', '/', 'bar', '/', 'baz'), 'bar', 2, 2)
        self.do('foo/bar/baz',  7, ('/',), None, True, ('foo', '/', 'bar', '/', 'baz'), 'bar', 2, 3)
        self.do('foo/bar/baz',  8, ('/',), None, True, ('foo', '/', 'bar', '/', 'baz'), 'baz', 4, 0)
        self.do('foo/bar/baz',  9, ('/',), None, True, ('foo', '/', 'bar', '/', 'baz'), 'baz', 4, 1)
        self.do('foo/bar/baz', 10, ('/',), None, True, ('foo', '/', 'bar', '/', 'baz'), 'baz', 4, 2)
        self.do('foo/bar/baz', 11, ('/',), None, True, ('foo', '/', 'bar', '/', 'baz'), 'baz', 4, 3)

    def test_separate_at_multichar_separator_including_separators(self):
        self.do('foo//bar/.baz',  0, ('//', './', '/.'), None, True, ('foo', '//', 'bar', '/.', 'baz'), 'foo', 0, 0)
        self.do('foo./bar//baz',  1, ('//', './', '/.'), None, True, ('foo', './', 'bar', '//', 'baz'), 'foo', 0, 1)
        self.do('foo/.bar./baz',  2, ('//', './', '/.'), None, True, ('foo', '/.', 'bar', './', 'baz'), 'foo', 0, 2)
        self.do('foo//bar/.baz',  3, ('//', './', '/.'), None, True, ('foo', '//', 'bar', '/.', 'baz'), 'foo', 0, 3)
        self.do('foo./bar//baz',  4, ('//', './', '/.'), None, True, ('foo', '.', '', '/', 'bar', '//', 'baz'), '', 2, 0)
        self.do('foo/.bar./baz',  5, ('//', './', '/.'), None, True, ('foo', '/.', 'bar', './', 'baz'), 'bar', 2, 0)
        self.do('foo//bar/.baz',  6, ('//', './', '/.'), None, True, ('foo', '//', 'bar', '/.', 'baz'), 'bar', 2, 1)
        self.do('foo./bar//baz',  7, ('//', './', '/.'), None, True, ('foo', './', 'bar', '//', 'baz'), 'bar', 2, 2)
        self.do('foo/.bar./baz',  8, ('//', './', '/.'), None, True, ('foo', '/.', 'bar', './', 'baz'), 'bar', 2, 3)
        self.do('foo//bar/.baz',  9, ('//', './', '/.'), None, True, ('foo', '//', 'bar', '/', '', '.', 'baz'), '', 4, 0)
        self.do('foo./bar//baz', 10, ('//', './', '/.'), None, True, ('foo', './', 'bar', '//', 'baz'), 'baz', 4, 0)
        self.do('foo/.bar./baz', 11, ('//', './', '/.'), None, True, ('foo', '/.', 'bar', './', 'baz'), 'baz', 4, 1)
        self.do('foo/.bar./baz', 12, ('//', './', '/.'), None, True, ('foo', '/.', 'bar', './', 'baz'), 'baz', 4, 2)
        self.do('foo/.bar./baz', 13, ('//', './', '/.'), None, True, ('foo', '/.', 'bar', './', 'baz'), 'baz', 4, 3)

    def test_separate_at_singlechar_separator_removing_separators(self):
        self.do('foo/bar/baz',  0, ('/',), None, False, ('foo', 'bar', 'baz'), 'foo', 0, 0)
        self.do('foo/bar/baz',  1, ('/',), None, False, ('foo', 'bar', 'baz'), 'foo', 0, 1)
        self.do('foo/bar/baz',  2, ('/',), None, False, ('foo', 'bar', 'baz'), 'foo', 0, 2)
        self.do('foo/bar/baz',  3, ('/',), None, False, ('foo', 'bar', 'baz'), 'foo', 0, 3)
        self.do('foo/bar/baz',  4, ('/',), None, False, ('foo', 'bar', 'baz'), 'bar', 1, 0)
        self.do('foo/bar/baz',  5, ('/',), None, False, ('foo', 'bar', 'baz'), 'bar', 1, 1)
        self.do('foo/bar/baz',  6, ('/',), None, False, ('foo', 'bar', 'baz'), 'bar', 1, 2)
        self.do('foo/bar/baz',  7, ('/',), None, False, ('foo', 'bar', 'baz'), 'bar', 1, 3)
        self.do('foo/bar/baz',  8, ('/',), None, False, ('foo', 'bar', 'baz'), 'baz', 2, 0)
        self.do('foo/bar/baz',  9, ('/',), None, False, ('foo', 'bar', 'baz'), 'baz', 2, 1)
        self.do('foo/bar/baz', 10, ('/',), None, False, ('foo', 'bar', 'baz'), 'baz', 2, 2)
        self.do('foo/bar/baz', 11, ('/',), None, False, ('foo', 'bar', 'baz'), 'baz', 2, 3)

    def test_separate_at_multichar_separator_removing_separators(self):
        self.do('foo//bar/.baz',  0, ('//', './', '/.'), None, False, ('foo', 'bar', 'baz'), 'foo', 0, 0)
        self.do('foo./bar//baz',  1, ('//', './', '/.'), None, False, ('foo', 'bar', 'baz'), 'foo', 0, 1)
        self.do('foo/.bar./baz',  2, ('//', './', '/.'), None, False, ('foo', 'bar', 'baz'), 'foo', 0, 2)
        self.do('foo//bar/.baz',  3, ('//', './', '/.'), None, False, ('foo', 'bar', 'baz'), 'foo', 0, 3)
        self.do('foo./bar//baz',  4, ('//', './', '/.'), None, False, ('foo', '.', '', '/', 'bar', 'baz'), '', 2, 0)
        self.do('foo/.bar./baz',  5, ('//', './', '/.'), None, False, ('foo', 'bar', 'baz'), 'bar', 1, 0)
        self.do('foo//bar/.baz',  6, ('//', './', '/.'), None, False, ('foo', 'bar', 'baz'), 'bar', 1, 1)
        self.do('foo./bar//baz',  7, ('//', './', '/.'), None, False, ('foo', 'bar', 'baz'), 'bar', 1, 2)
        self.do('foo/.bar./baz',  8, ('//', './', '/.'), None, False, ('foo', 'bar', 'baz'), 'bar', 1, 3)
        self.do('foo//bar/.baz',  9, ('//', './', '/.'), None, False, ('foo', 'bar', '/', '', '.', 'baz'), '', 3, 0)
        self.do('foo./bar//baz', 10, ('//', './', '/.'), None, False, ('foo', 'bar', 'baz'), 'baz', 2, 0)
        self.do('foo/.bar./baz', 11, ('//', './', '/.'), None, False, ('foo', 'bar', 'baz'), 'baz', 2, 1)
        self.do('foo//bar/.baz', 12, ('//', './', '/.'), None, False, ('foo', 'bar', 'baz'), 'baz', 2, 2)
        self.do('foo./bar//baz', 13, ('//', './', '/.'), None, False, ('foo', 'bar', 'baz'), 'baz', 2, 3)

    def test_maxseps_zero(self):
        self.do('foo/bar/baz',  0, ('/',), 0, False, ('foo/bar/baz',), 'foo/bar/baz', 0,  0)
        self.do('foo/bar/baz',  1, ('/',), 0, False, ('foo/bar/baz',), 'foo/bar/baz', 0,  1)
        self.do('foo/bar/baz',  2, ('/',), 0, False, ('foo/bar/baz',), 'foo/bar/baz', 0,  2)
        self.do('foo/bar/baz',  3, ('/',), 0, False, ('foo/bar/baz',), 'foo/bar/baz', 0,  3)
        self.do('foo/bar/baz',  4, ('/',), 0, False, ('foo/bar/baz',), 'foo/bar/baz', 0,  4)
        self.do('foo/bar/baz',  5, ('/',), 0, False, ('foo/bar/baz',), 'foo/bar/baz', 0,  5)
        self.do('foo/bar/baz',  6, ('/',), 0, False, ('foo/bar/baz',), 'foo/bar/baz', 0,  6)
        self.do('foo/bar/baz',  7, ('/',), 0, False, ('foo/bar/baz',), 'foo/bar/baz', 0,  7)
        self.do('foo/bar/baz',  8, ('/',), 0, False, ('foo/bar/baz',), 'foo/bar/baz', 0,  8)
        self.do('foo/bar/baz',  9, ('/',), 0, False, ('foo/bar/baz',), 'foo/bar/baz', 0,  9)
        self.do('foo/bar/baz', 10, ('/',), 0, False, ('foo/bar/baz',), 'foo/bar/baz', 0, 10)
        self.do('foo/bar/baz', 11, ('/',), 0, False, ('foo/bar/baz',), 'foo/bar/baz', 0, 11)

    def test_maxseps_one(self):
        self.do('foo/bar/baz',  0, ('/',), 1, False, ('foo', 'bar/baz'), 'foo', 0,  0)
        self.do('foo/bar/baz',  1, ('/',), 1, False, ('foo', 'bar/baz'), 'foo', 0,  1)
        self.do('foo/bar/baz',  2, ('/',), 1, False, ('foo', 'bar/baz'), 'foo', 0,  2)
        self.do('foo/bar/baz',  3, ('/',), 1, False, ('foo', 'bar/baz'), 'foo', 0,  3)
        self.do('foo/bar/baz',  4, ('/',), 1, False, ('foo', 'bar/baz'), 'bar/baz', 1, 0)
        self.do('foo/bar/baz',  5, ('/',), 1, False, ('foo', 'bar/baz'), 'bar/baz', 1, 1)
        self.do('foo/bar/baz',  6, ('/',), 1, False, ('foo', 'bar/baz'), 'bar/baz', 1, 2)
        self.do('foo/bar/baz',  7, ('/',), 1, False, ('foo', 'bar/baz'), 'bar/baz', 1, 3)
        self.do('foo/bar/baz',  8, ('/',), 1, False, ('foo', 'bar/baz'), 'bar/baz', 1, 4)
        self.do('foo/bar/baz',  9, ('/',), 1, False, ('foo', 'bar/baz'), 'bar/baz', 1, 5)
        self.do('foo/bar/baz', 10, ('/',), 1, False, ('foo', 'bar/baz'), 'bar/baz', 1, 6)
        self.do('foo/bar/baz', 11, ('/',), 1, False, ('foo', 'bar/baz'), 'bar/baz', 1, 7)

    def test_maxseps_two(self):
        self.do('foo/bar/baz/bax',  0, ('/',), 2, False, ('foo', 'bar', 'baz/bax'), 'foo', 0,  0)
        self.do('foo/bar/baz/bax',  1, ('/',), 2, False, ('foo', 'bar', 'baz/bax'), 'foo', 0,  1)
        self.do('foo/bar/baz/bax',  2, ('/',), 2, False, ('foo', 'bar', 'baz/bax'), 'foo', 0,  2)
        self.do('foo/bar/baz/bax',  3, ('/',), 2, False, ('foo', 'bar', 'baz/bax'), 'foo', 0,  3)
        self.do('foo/bar/baz/bax',  4, ('/',), 2, False, ('foo', 'bar', 'baz/bax'), 'bar', 1, 0)
        self.do('foo/bar/baz/bax',  5, ('/',), 2, False, ('foo', 'bar', 'baz/bax'), 'bar', 1, 1)
        self.do('foo/bar/baz/bax',  6, ('/',), 2, False, ('foo', 'bar', 'baz/bax'), 'bar', 1, 2)
        self.do('foo/bar/baz/bax',  7, ('/',), 2, False, ('foo', 'bar', 'baz/bax'), 'bar', 1, 3)
        self.do('foo/bar/baz/bax',  8, ('/',), 2, False, ('foo', 'bar', 'baz/bax'), 'baz/bax', 2, 0)
        self.do('foo/bar/baz/bax',  9, ('/',), 2, False, ('foo', 'bar', 'baz/bax'), 'baz/bax', 2, 1)
        self.do('foo/bar/baz/bax', 10, ('/',), 2, False, ('foo', 'bar', 'baz/bax'), 'baz/bax', 2, 2)
        self.do('foo/bar/baz/bax', 11, ('/',), 2, False, ('foo', 'bar', 'baz/bax'), 'baz/bax', 2, 3)
        self.do('foo/bar/baz/bax', 12, ('/',), 2, False, ('foo', 'bar', 'baz/bax'), 'baz/bax', 2, 4)
        self.do('foo/bar/baz/bax', 13, ('/',), 2, False, ('foo', 'bar', 'baz/bax'), 'baz/bax', 2, 5)
        self.do('foo/bar/baz/bax', 14, ('/',), 2, False, ('foo', 'bar', 'baz/bax'), 'baz/bax', 2, 6)
        self.do('foo/bar/baz/bax', 15, ('/',), 2, False, ('foo', 'bar', 'baz/bax'), 'baz/bax', 2, 7)


class TestArgs(unittest.TestCase):
    def test_equality(self):
        self.assertEqual(cliparser.Args(('a', 'b', 'c')),
                         cliparser.Args(('a', 'b', 'c')))
        for curarg_index in (0, 1, 2):
            for curarg_curpos in (0, 1, 2, 3):
                self.assertEqual(cliparser.Args(('a', 'b', 'c'), curarg_index=curarg_index, curarg_curpos=curarg_curpos),
                                 cliparser.Args(('a', 'b', 'c'), curarg_index=curarg_index, curarg_curpos=curarg_curpos))

    def test_inequality(self):
        self.assertNotEqual(cliparser.Args(('a', 'b', 'c'), curarg_index=1, curarg_curpos=0),
                            cliparser.Args(('a', 'b', 'd'), curarg_index=1, curarg_curpos=0))
        self.assertNotEqual(cliparser.Args(('a', 'b', 'c'), curarg_index=1, curarg_curpos=0),
                            cliparser.Args(('a', 'b', 'c'), curarg_index=2, curarg_curpos=0))
        self.assertNotEqual(cliparser.Args(('a', 'b', 'c'), curarg_index=1, curarg_curpos=0),
                            cliparser.Args(('a', 'b', 'c'), curarg_index=1, curarg_curpos=1))

    def test_getitem_with_index(self):
        args = cliparser.Args(('a', 'b', 'c'), curarg_index=2, curarg_curpos=1)
        self.assertEqual(args[0], cliparser.Arg('a'))
        self.assertEqual(args[1], cliparser.Arg('b'))
        self.assertEqual(args[2], cliparser.Arg('c', curpos=1))
        with self.assertRaises(IndexError):
            args[3]

    def test_getitem_with_slice_without_cursor_position(self):
        args = cliparser.Args(('a', 'b', 'c'))
        self.assertEqual(args[0:], cliparser.Args(('a', 'b', 'c')))
        self.assertEqual(args[1:], cliparser.Args(('b', 'c')))
        self.assertEqual(args[2:], cliparser.Args(('c',)))
        self.assertEqual(args[3:], cliparser.Args(('',)))
        self.assertEqual(args[:0], cliparser.Args(('',)))
        self.assertEqual(args[:1], cliparser.Args(('a',)))
        self.assertEqual(args[:2], cliparser.Args(('a', 'b')))
        self.assertEqual(args[:3], cliparser.Args(('a', 'b', 'c')))

    def test_getitem_with_slice_with_cursor_position(self):
        args = cliparser.Args(('a', 'b', 'c'), curarg_index=0, curarg_curpos=0)
        self.assertEqual(args[0:], cliparser.Args(('a', 'b', 'c'), curarg_index=0, curarg_curpos=0))
        self.assertEqual(args[1:], cliparser.Args(('b', 'c')))
        self.assertEqual(args[2:], cliparser.Args(('c',)))
        self.assertEqual(args[3:], cliparser.Args(('',)))
        self.assertEqual(args[:0], cliparser.Args(('',)))
        self.assertEqual(args[:1], cliparser.Args(('a',), curarg_index=0, curarg_curpos=0))
        self.assertEqual(args[:2], cliparser.Args(('a', 'b'), curarg_index=0, curarg_curpos=0))
        self.assertEqual(args[:3], cliparser.Args(('a', 'b', 'c'), curarg_index=0, curarg_curpos=0))

        args = cliparser.Args(('a', 'b', 'c'), curarg_index=0, curarg_curpos=1)
        self.assertEqual(args[0:], cliparser.Args(('a', 'b', 'c'), curarg_index=0, curarg_curpos=1))
        self.assertEqual(args[1:], cliparser.Args(('b', 'c'), curarg_index=0, curarg_curpos=0))
        self.assertEqual(args[2:], cliparser.Args(('c',)))
        self.assertEqual(args[3:], cliparser.Args(('',)))
        self.assertEqual(args[:0], cliparser.Args(('',)))
        self.assertEqual(args[:1], cliparser.Args(('a',), curarg_index=0, curarg_curpos=1))
        self.assertEqual(args[:2], cliparser.Args(('a', 'b'), curarg_index=0, curarg_curpos=1))
        self.assertEqual(args[:3], cliparser.Args(('a', 'b', 'c'), curarg_index=0, curarg_curpos=1))

        args = cliparser.Args(('a', 'b', 'c'), curarg_index=1, curarg_curpos=0)
        self.assertEqual(args[0:], cliparser.Args(('a', 'b', 'c'), curarg_index=1, curarg_curpos=0))
        self.assertEqual(args[1:], cliparser.Args(('b', 'c'), curarg_index=0, curarg_curpos=0))
        self.assertEqual(args[2:], cliparser.Args(('c',)))
        self.assertEqual(args[3:], cliparser.Args(('',)))
        self.assertEqual(args[:0], cliparser.Args(('',)))
        self.assertEqual(args[:1], cliparser.Args(('a',), curarg_index=0, curarg_curpos=1))
        self.assertEqual(args[:2], cliparser.Args(('a', 'b'), curarg_index=1, curarg_curpos=0))
        self.assertEqual(args[:3], cliparser.Args(('a', 'b', 'c'), curarg_index=1, curarg_curpos=0))

        args = cliparser.Args(('a', 'b', 'c'), curarg_index=1, curarg_curpos=1)
        self.assertEqual(args[0:], cliparser.Args(('a', 'b', 'c'), curarg_index=1, curarg_curpos=1))
        self.assertEqual(args[1:], cliparser.Args(('b', 'c'), curarg_index=0, curarg_curpos=1))
        self.assertEqual(args[2:], cliparser.Args(('c',), curarg_index=0, curarg_curpos=0))
        self.assertEqual(args[3:], cliparser.Args(('',)))
        self.assertEqual(args[:0], cliparser.Args(('',)))
        self.assertEqual(args[:1], cliparser.Args(('a',)))
        self.assertEqual(args[:2], cliparser.Args(('a', 'b'), curarg_index=1, curarg_curpos=1))
        self.assertEqual(args[:3], cliparser.Args(('a', 'b', 'c'), curarg_index=1, curarg_curpos=1))

        args = cliparser.Args(('a', 'b', 'c'), curarg_index=2, curarg_curpos=0)
        self.assertEqual(args[0:], cliparser.Args(('a', 'b', 'c'), curarg_index=2, curarg_curpos=0))
        self.assertEqual(args[1:], cliparser.Args(('b', 'c'), curarg_index=1, curarg_curpos=0))
        self.assertEqual(args[2:], cliparser.Args(('c',), curarg_index=0, curarg_curpos=0))
        self.assertEqual(args[3:], cliparser.Args(('',)))
        self.assertEqual(args[:0], cliparser.Args(('',)))
        self.assertEqual(args[:1], cliparser.Args(('a',)))
        self.assertEqual(args[:2], cliparser.Args(('a', 'b'), curarg_index=1, curarg_curpos=1))
        self.assertEqual(args[:3], cliparser.Args(('a', 'b', 'c'), curarg_index=2, curarg_curpos=0))

        args = cliparser.Args(('a', 'b', 'c'), curarg_index=2, curarg_curpos=1)
        self.assertEqual(args[0:], cliparser.Args(('a', 'b', 'c'), curarg_index=2, curarg_curpos=1))
        self.assertEqual(args[1:], cliparser.Args(('b', 'c'), curarg_index=1, curarg_curpos=1))
        self.assertEqual(args[2:], cliparser.Args(('c',), curarg_index=0, curarg_curpos=1))
        self.assertEqual(args[3:], cliparser.Args(('',)))
        self.assertEqual(args[:0], cliparser.Args(('',)))
        self.assertEqual(args[:1], cliparser.Args(('a',)))
        self.assertEqual(args[:2], cliparser.Args(('a', 'b')))
        self.assertEqual(args[:3], cliparser.Args(('a', 'b', 'c'), curarg_index=2, curarg_curpos=1))

    def test_params(self):
        def do(*args, i=None, c=None, **kwargs):
            return cliparser.Args(args, curarg_index=i, curarg_curpos=c).params('--foo', **kwargs)
        self.assertEqual(do('a', 'b', 'c', 'd'), cliparser.Args(()))
        self.assertEqual(do('a', '--foo', 'b', 'c'), cliparser.Args(('b', 'c')))
        self.assertEqual(do('a', '--foo', 'b', 'c', maxparams=1), cliparser.Args(('b',)))
        self.assertEqual(do('a', '--foo', 'b', 'c', maxparams=2), cliparser.Args(('b', 'c')))
        self.assertEqual(do('a', 'b', '--foo', 'c', 'd'), cliparser.Args(('c', 'd')))
        self.assertEqual(do('a', 'b', '--foo', 'c', 'd', maxparams=1), cliparser.Args(('c',)))
        self.assertEqual(do('a', '--foo', 'b', '-c'), cliparser.Args(('b',)))
        self.assertEqual(do('a', '--foo', 'b', 'c', '-d', '-e'), cliparser.Args(('b', 'c')))

        self.assertEqual(do('a', 'b', 'c', i=2, c=1), cliparser.Args(()))
        self.assertEqual(do('a', '--foo', 'bar', 'baz', i=0, c=1),
                         cliparser.Args(('bar', 'baz')))
        self.assertEqual(do('a', '--foo', 'bar', 'baz', i=1, c=2),
                         cliparser.Args(('bar', 'baz')))
        self.assertEqual(do('a', '--foo', 'bar', 'baz', i=2, c=0),
                         cliparser.Args(('bar', 'baz'), curarg_index=0, curarg_curpos=0))
        self.assertEqual(do('a', '--foo', 'bar', 'baz', i=2, c=2),
                         cliparser.Args(('bar', 'baz'), curarg_index=0, curarg_curpos=2))
        self.assertEqual(do('a', '--foo', 'bar', 'baz', i=3, c=2),
                         cliparser.Args(('bar', 'baz'), curarg_index=1, curarg_curpos=2))
        self.assertEqual(do('a', '--foo', 'bar', 'baz', i=2, c=1, maxparams=1),
                         cliparser.Args(('bar',), curarg_index=0, curarg_curpos=1))
        self.assertEqual(do('a', '--foo', 'bar', 'baz', i=3, c=1, maxparams=1),
                         cliparser.Args(('bar',)))

    def test_remove_empty(self):
        def do(*args, i=None, c=None, **kwargs):
            return cliparser.Args(args, curarg_index=i, curarg_curpos=c).remove_empty()
        self.assertEqual(do('', 'b', 'c', 'd', i=0, c=1),
                         cliparser.Args(('b', 'c', 'd'), curarg_index=0, curarg_curpos=1))
        self.assertEqual(do('', 'b', 'c', 'd', i=1, c=1),
                         cliparser.Args(('b', 'c', 'd'), curarg_index=0, curarg_curpos=1))
        self.assertEqual(do('', 'b', 'c', 'd', i=2, c=1),
                         cliparser.Args(('b', 'c', 'd'), curarg_index=1, curarg_curpos=1))
        self.assertEqual(do('', 'b', 'c', 'd', i=3, c=1),
                         cliparser.Args(('b', 'c', 'd'), curarg_index=2, curarg_curpos=1))

        self.assertEqual(do('a', '', 'c', 'd', i=0, c=1),
                         cliparser.Args(('a', 'c', 'd'), curarg_index=0, curarg_curpos=1))
        self.assertEqual(do('a', '', 'c', 'd', i=1, c=1),
                         cliparser.Args(('a', 'c', 'd'), curarg_index=1, curarg_curpos=1))
        self.assertEqual(do('a', '', 'c', 'd', i=2, c=1),
                         cliparser.Args(('a', 'c', 'd'), curarg_index=1, curarg_curpos=1))
        self.assertEqual(do('a', '', 'c', 'd', i=3, c=1),
                         cliparser.Args(('a', 'c', 'd'), curarg_index=2, curarg_curpos=1))

        self.assertEqual(do('a', 'b', '', 'd', i=0, c=1),
                         cliparser.Args(('a', 'b', 'd'), curarg_index=0, curarg_curpos=1))
        self.assertEqual(do('a', 'b', '', 'd', i=1, c=1),
                         cliparser.Args(('a', 'b', 'd'), curarg_index=1, curarg_curpos=1))
        self.assertEqual(do('a', 'b', '', 'd', i=2, c=1),
                         cliparser.Args(('a', 'b', 'd'), curarg_index=2, curarg_curpos=1))
        self.assertEqual(do('a', 'b', '', 'd', i=3, c=1),
                         cliparser.Args(('a', 'b', 'd'), curarg_index=2, curarg_curpos=1))

        self.assertEqual(do('a', 'b', 'c', '', i=0, c=1),
                         cliparser.Args(('a', 'b', 'c'), curarg_index=0, curarg_curpos=1))
        self.assertEqual(do('a', 'b', 'c', '', i=1, c=1),
                         cliparser.Args(('a', 'b', 'c'), curarg_index=1, curarg_curpos=1))
        self.assertEqual(do('a', 'b', 'c', '', i=2, c=1),
                         cliparser.Args(('a', 'b', 'c'), curarg_index=2, curarg_curpos=1))
        self.assertEqual(do('a', 'b', 'c', '', i=3, c=1),
                         cliparser.Args(('a', 'b', 'c'), curarg_index=2, curarg_curpos=1))
