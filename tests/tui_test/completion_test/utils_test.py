from stig.tui.completion import _utils as utils

import unittest


class Test_escape(unittest.TestCase):
    def test_spaces(self):
        self.assertEqual(utils.escape('foo bar baz'), r'foo\ bar\ baz')
        self.assertEqual(utils.escape('foo bar baz', curpos=3), (r'foo\ bar\ baz', 3))
        self.assertEqual(utils.escape('foo bar baz', curpos=4), (r'foo\ bar\ baz', 5))
        self.assertEqual(utils.escape('foo bar baz', curpos=5), (r'foo\ bar\ baz', 6))
        self.assertEqual(utils.escape('foo bar baz', curpos=7), (r'foo\ bar\ baz', 8))
        self.assertEqual(utils.escape('foo bar baz', curpos=8), (r'foo\ bar\ baz', 10))
        self.assertEqual(utils.escape('foo bar baz', curpos=9), (r'foo\ bar\ baz', 11))

    def test_single_quotes(self):
        self.assertEqual(utils.escape('''foo's'''), r'''foo\'s''')
        self.assertEqual(utils.escape('''foo's''', curpos=3), (r'''foo\'s''', 3))
        self.assertEqual(utils.escape('''foo's''', curpos=4), (r'''foo\'s''', 5))
        self.assertEqual(utils.escape('''foo's''', curpos=5), (r'''foo\'s''', 6))

    def test_double_quotes(self):
        self.assertEqual(utils.escape('''"foo"'''), r'''\"foo\"''')
        self.assertEqual(utils.escape('''"foo"''', curpos=0), (r'''\"foo\"''', 0))
        self.assertEqual(utils.escape('''"foo"''', curpos=1), (r'''\"foo\"''', 2))
        self.assertEqual(utils.escape('''"foo"''', curpos=2), (r'''\"foo\"''', 3))
        self.assertEqual(utils.escape('''"foo"''', curpos=3), (r'''\"foo\"''', 4))
        self.assertEqual(utils.escape('''"foo"''', curpos=4), (r'''\"foo\"''', 5))
        self.assertEqual(utils.escape('''"foo"''', curpos=5), (r'''\"foo\"''', 7))

    def test_backslashes(self):
        self.assertEqual(utils.escape(r'foo \bar'), r'foo\ \\bar')
        self.assertEqual(utils.escape(r'foo \\bar'), r'foo\ \\\\bar')
        self.assertEqual(utils.escape(r'foo \\\bar'), r'foo\ \\\\\\bar')
        self.assertEqual(utils.escape(r'foo \\bar', curpos=3), (r'foo\ \\\\bar', 3))
        self.assertEqual(utils.escape(r'foo \\bar', curpos=4), (r'foo\ \\\\bar', 5))
        self.assertEqual(utils.escape(r'foo \\bar', curpos=5), (r'foo\ \\\\bar', 7))
        self.assertEqual(utils.escape(r'foo \\bar', curpos=6), (r'foo\ \\\\bar', 9))
        self.assertEqual(utils.escape(r'foo \\bar', curpos=7), (r'foo\ \\\\bar', 10))


class Test_quote(unittest.TestCase):
    def test_no_quoting_needed(self):
        self.assertEqual(utils.quote('foo'), 'foo')
        self.assertEqual(utils.quote('foo', curpos=0), ('foo', 0))
        self.assertEqual(utils.quote('foo', curpos=1), ('foo', 1))
        self.assertEqual(utils.quote('foo', curpos=2), ('foo', 2))
        self.assertEqual(utils.quote('foo', curpos=3), ('foo', 3))

    def test_space(self):
        self.assertEqual(utils.quote('foo bar baz'), "'foo bar baz'")
        for i in range(11):
            self.assertEqual(utils.quote('foo bar baz', curpos=i),  ("'foo bar baz'", i+1))
        self.assertEqual(utils.quote('foo bar baz', curpos=11), ("'foo bar baz'", 13))

    def test_backslash(self):
        self.assertEqual(utils.quote(r'foo\bar\baz'), r"'foo\bar\baz'")
        for i in range(11):
            self.assertEqual(utils.quote(r'foo\bar\baz', curpos=i), (r"'foo\bar\baz'", i+1))
        self.assertEqual(utils.quote(r'foo\bar\baz', curpos=11), (r"'foo\bar\baz'", 13))

    def test_single_quote(self):
        self.assertEqual(utils.quote("foo'bar'baz"), '''"foo'bar'baz"''')
        for i in range(11):
            self.assertEqual(utils.quote("foo'bar'baz", curpos=i), ('''"foo'bar'baz"''', i+1))
        self.assertEqual(utils.quote("foo'bar'baz", curpos=11), ('''"foo'bar'baz"''', 13))

    def test_double_quote(self):
        self.assertEqual(utils.quote('''foo"bar"baz'''), """'foo"bar"baz'""")
        for i in range(11):
            self.assertEqual(utils.quote('''foo"bar"baz''', curpos=i), ("""'foo"bar"baz'""", i+1))
        self.assertEqual(utils.quote('''foo"bar"baz''', curpos=11), ("""'foo"bar"baz'""", 13))

    def test_mixed_quotes(self):
        self.assertEqual(utils.quote('''foo 'bar' "baz"'''), r"""'foo \'bar\' "baz"'""")
        self.assertEqual(utils.quote('''foo 'bar' "baz"''', curpos=0), (r"""'foo \'bar\' "baz"'""", 1))
        self.assertEqual(utils.quote('''foo 'bar' "baz"''', curpos=1), (r"""'foo \'bar\' "baz"'""", 2))
        self.assertEqual(utils.quote('''foo 'bar' "baz"''', curpos=2), (r"""'foo \'bar\' "baz"'""", 3))
        self.assertEqual(utils.quote('''foo 'bar' "baz"''', curpos=3), (r"""'foo \'bar\' "baz"'""", 4))
        self.assertEqual(utils.quote('''foo 'bar' "baz"''', curpos=4), (r"""'foo \'bar\' "baz"'""", 6))
        self.assertEqual(utils.quote('''foo 'bar' "baz"''', curpos=5), (r"""'foo \'bar\' "baz"'""", 7))
        self.assertEqual(utils.quote('''foo 'bar' "baz"''', curpos=6), (r"""'foo \'bar\' "baz"'""", 8))
        self.assertEqual(utils.quote('''foo 'bar' "baz"''', curpos=7), (r"""'foo \'bar\' "baz"'""", 9))
        self.assertEqual(utils.quote('''foo 'bar' "baz"''', curpos=8), (r"""'foo \'bar\' "baz"'""", 11))
        self.assertEqual(utils.quote('''foo 'bar' "baz"''', curpos=9), (r"""'foo \'bar\' "baz"'""", 12))
        self.assertEqual(utils.quote('''foo 'bar' "baz"''', curpos=10), (r"""'foo \'bar\' "baz"'""", 13))
        self.assertEqual(utils.quote('''foo 'bar' "baz"''', curpos=11), (r"""'foo \'bar\' "baz"'""", 14))
        self.assertEqual(utils.quote('''foo 'bar' "baz"''', curpos=12), (r"""'foo \'bar\' "baz"'""", 15))
        self.assertEqual(utils.quote('''foo 'bar' "baz"''', curpos=13), (r"""'foo \'bar\' "baz"'""", 16))
        self.assertEqual(utils.quote('''foo 'bar' "baz"''', curpos=14), (r"""'foo \'bar\' "baz"'""", 17))
        self.assertEqual(utils.quote('''foo 'bar' "baz"''', curpos=15), (r"""'foo \'bar\' "baz"'""", 19))


class Test_is_escaped(unittest.TestCase):
    def test_escaped(self):
        self.assertTrue(utils.is_escaped(r'foo\ bar'))
        self.assertTrue(utils.is_escaped(r'foo\'s\ bar'))
        self.assertTrue(utils.is_escaped(r'foo\'s\ \"bar\"'))
        self.assertTrue(utils.is_escaped(r'foo\'s\ \"bar\" \\o/'))

    def test_quoted(self):
        self.assertFalse(utils.is_escaped('"foo bar"'))
        self.assertFalse(utils.is_escaped("foo' 'bar"))
        self.assertFalse(utils.is_escaped('fo"o b"ar'))
        self.assertFalse(utils.is_escaped('foo "\bar"'))
        self.assertFalse(utils.is_escaped('foo "bar\"'))
        self.assertFalse(utils.is_escaped('foo "bar\\"'))


class Test_plaintext(unittest.TestCase):
    def test_backslash_escapes_space(self):
        self.assertEqual(utils.plaintext(r'foo\ bar\ baz'), 'foo bar baz')
        self.assertEqual(utils.plaintext(r'foo\ bar\ baz', curpos=0), ('foo bar baz', 0))
        self.assertEqual(utils.plaintext(r'foo\ bar\ baz', curpos=1), ('foo bar baz', 1))
        self.assertEqual(utils.plaintext(r'foo\ bar\ baz', curpos=2), ('foo bar baz', 2))
        self.assertEqual(utils.plaintext(r'foo\ bar\ baz', curpos=3), ('foo bar baz', 3))
        self.assertEqual(utils.plaintext(r'foo\ bar\ baz', curpos=4), ('foo bar baz', 3))
        self.assertEqual(utils.plaintext(r'foo\ bar\ baz', curpos=5), ('foo bar baz', 4))
        self.assertEqual(utils.plaintext(r'foo\ bar\ baz', curpos=6), ('foo bar baz', 5))
        self.assertEqual(utils.plaintext(r'foo\ bar\ baz', curpos=7), ('foo bar baz', 6))
        self.assertEqual(utils.plaintext(r'foo\ bar\ baz', curpos=8), ('foo bar baz', 7))
        self.assertEqual(utils.plaintext(r'foo\ bar\ baz', curpos=9), ('foo bar baz', 7))
        self.assertEqual(utils.plaintext(r'foo\ bar\ baz', curpos=10), ('foo bar baz', 8))
        self.assertEqual(utils.plaintext(r'foo\ bar\ baz', curpos=11), ('foo bar baz', 9))
        self.assertEqual(utils.plaintext(r'foo\ bar\ baz', curpos=12), ('foo bar baz', 10))
        self.assertEqual(utils.plaintext(r'foo\ bar\ baz', curpos=13), ('foo bar baz', 11))

    def test_backslash_escapes_backslash(self):
        self.assertEqual(utils.plaintext(r'foo\\ bar\\\\ baz'), r'foo\ bar\\ baz')
        self.assertEqual(utils.plaintext(r'foo\\ bar\\\\ baz', curpos=0), (r'foo\ bar\\ baz', 0))
        self.assertEqual(utils.plaintext(r'foo\\ bar\\\\ baz', curpos=1), (r'foo\ bar\\ baz', 1))
        self.assertEqual(utils.plaintext(r'foo\\ bar\\\\ baz', curpos=2), (r'foo\ bar\\ baz', 2))
        self.assertEqual(utils.plaintext(r'foo\\ bar\\\\ baz', curpos=3), (r'foo\ bar\\ baz', 3))
        self.assertEqual(utils.plaintext(r'foo\\ bar\\\\ baz', curpos=4), (r'foo\ bar\\ baz', 3))
        self.assertEqual(utils.plaintext(r'foo\\ bar\\\\ baz', curpos=5), (r'foo\ bar\\ baz', 4))
        self.assertEqual(utils.plaintext(r'foo\\ bar\\\\ baz', curpos=6), (r'foo\ bar\\ baz', 5))
        self.assertEqual(utils.plaintext(r'foo\\ bar\\\\ baz', curpos=7), (r'foo\ bar\\ baz', 6))
        self.assertEqual(utils.plaintext(r'foo\\ bar\\\\ baz', curpos=8), (r'foo\ bar\\ baz', 7))
        self.assertEqual(utils.plaintext(r'foo\\ bar\\\\ baz', curpos=9), (r'foo\ bar\\ baz', 8))
        self.assertEqual(utils.plaintext(r'foo\\ bar\\\\ baz', curpos=10), (r'foo\ bar\\ baz', 8))
        self.assertEqual(utils.plaintext(r'foo\\ bar\\\\ baz', curpos=11), (r'foo\ bar\\ baz', 9))
        self.assertEqual(utils.plaintext(r'foo\\ bar\\\\ baz', curpos=12), (r'foo\ bar\\ baz', 9))
        self.assertEqual(utils.plaintext(r'foo\\ bar\\\\ baz', curpos=13), (r'foo\ bar\\ baz', 10))
        self.assertEqual(utils.plaintext(r'foo\\ bar\\\\ baz', curpos=14), (r'foo\ bar\\ baz', 11))
        self.assertEqual(utils.plaintext(r'foo\\ bar\\\\ baz', curpos=15), (r'foo\ bar\\ baz', 12))
        self.assertEqual(utils.plaintext(r'foo\\ bar\\\\ baz', curpos=16), (r'foo\ bar\\ baz', 13))
        self.assertEqual(utils.plaintext(r'foo\\ bar\\\\ baz', curpos=17), (r'foo\ bar\\ baz', 14))

    def test_blackslash_escapes_space_after_escaped_backslash(self):
        self.assertEqual(utils.plaintext(r'foo\\\ bar\\\\\ baz'), r'foo\ bar\\ baz')
        self.assertEqual(utils.plaintext(r'foo\\\ bar\\\\\ baz', curpos=0), (r'foo\ bar\\ baz', 0))
        self.assertEqual(utils.plaintext(r'foo\\\ bar\\\\\ baz', curpos=1), (r'foo\ bar\\ baz', 1))
        self.assertEqual(utils.plaintext(r'foo\\\ bar\\\\\ baz', curpos=2), (r'foo\ bar\\ baz', 2))
        self.assertEqual(utils.plaintext(r'foo\\\ bar\\\\\ baz', curpos=3), (r'foo\ bar\\ baz', 3))
        self.assertEqual(utils.plaintext(r'foo\\\ bar\\\\\ baz', curpos=4), (r'foo\ bar\\ baz', 3))
        self.assertEqual(utils.plaintext(r'foo\\\ bar\\\\\ baz', curpos=5), (r'foo\ bar\\ baz', 4))
        self.assertEqual(utils.plaintext(r'foo\\\ bar\\\\\ baz', curpos=6), (r'foo\ bar\\ baz', 4))
        self.assertEqual(utils.plaintext(r'foo\\\ bar\\\\\ baz', curpos=7), (r'foo\ bar\\ baz', 5))
        self.assertEqual(utils.plaintext(r'foo\\\ bar\\\\\ baz', curpos=8), (r'foo\ bar\\ baz', 6))
        self.assertEqual(utils.plaintext(r'foo\\\ bar\\\\\ baz', curpos=9), (r'foo\ bar\\ baz', 7))
        self.assertEqual(utils.plaintext(r'foo\\\ bar\\\\\ baz', curpos=10), (r'foo\ bar\\ baz', 8))
        self.assertEqual(utils.plaintext(r'foo\\\ bar\\\\\ baz', curpos=11), (r'foo\ bar\\ baz', 8))
        self.assertEqual(utils.plaintext(r'foo\\\ bar\\\\\ baz', curpos=12), (r'foo\ bar\\ baz', 9))
        self.assertEqual(utils.plaintext(r'foo\\\ bar\\\\\ baz', curpos=13), (r'foo\ bar\\ baz', 9))
        self.assertEqual(utils.plaintext(r'foo\\\ bar\\\\\ baz', curpos=14), (r'foo\ bar\\ baz', 10))
        self.assertEqual(utils.plaintext(r'foo\\\ bar\\\\\ baz', curpos=15), (r'foo\ bar\\ baz', 10))
        self.assertEqual(utils.plaintext(r'foo\\\ bar\\\\\ baz', curpos=16), (r'foo\ bar\\ baz', 11))
        self.assertEqual(utils.plaintext(r'foo\\\ bar\\\\\ baz', curpos=17), (r'foo\ bar\\ baz', 12))
        self.assertEqual(utils.plaintext(r'foo\\\ bar\\\\\ baz', curpos=18), (r'foo\ bar\\ baz', 13))

    def test_last_character_is_backslash(self):
        self.assertEqual(utils.plaintext('foo\\'), 'foo')
        self.assertEqual(utils.plaintext('foo\\', curpos=0), ('foo', 0))
        self.assertEqual(utils.plaintext('foo\\', curpos=1), ('foo', 1))
        self.assertEqual(utils.plaintext('foo\\', curpos=2), ('foo', 2))
        self.assertEqual(utils.plaintext('foo\\', curpos=3), ('foo', 3))
        self.assertEqual(utils.plaintext('foo\\', curpos=4), ('foo', 3))
        self.assertEqual(utils.plaintext('foo\\', curpos=5), ('foo', 3))

    def test_last_character_is_escaped_space(self):
        self.assertEqual(utils.plaintext(r'foo\ '), 'foo ')
        self.assertEqual(utils.plaintext(r'foo\  '), 'foo ')
        self.assertEqual(utils.plaintext(r'foo\   '), 'foo ')
        self.assertEqual(utils.plaintext(r'foo\   ', curpos=0), ('foo ', 0))
        self.assertEqual(utils.plaintext(r'foo\   ', curpos=1), ('foo ', 1))
        self.assertEqual(utils.plaintext(r'foo\   ', curpos=2), ('foo ', 2))
        self.assertEqual(utils.plaintext(r'foo\   ', curpos=3), ('foo ', 3))
        self.assertEqual(utils.plaintext(r'foo\   ', curpos=4), ('foo ', 3))
        self.assertEqual(utils.plaintext(r'foo\   ', curpos=5), ('foo ', 4))
        self.assertEqual(utils.plaintext(r'foo\   ', curpos=6), ('foo ', 4))
        self.assertEqual(utils.plaintext(r'foo\   ', curpos=7), ('foo ', 4))

    def test_single_quotes(self):
        self.assertEqual(utils.plaintext("'foo' 'b'ar b'az'"), 'foo bar baz')
        self.assertEqual(utils.plaintext("'foo' 'b'ar b'az'", curpos=0), ('foo bar baz', 0))
        self.assertEqual(utils.plaintext("'foo' 'b'ar b'az'", curpos=1), ('foo bar baz', 0))
        self.assertEqual(utils.plaintext("'foo' 'b'ar b'az'", curpos=2), ('foo bar baz', 1))
        self.assertEqual(utils.plaintext("'foo' 'b'ar b'az'", curpos=3), ('foo bar baz', 2))
        self.assertEqual(utils.plaintext("'foo' 'b'ar b'az'", curpos=4), ('foo bar baz', 3))
        self.assertEqual(utils.plaintext("'foo' 'b'ar b'az'", curpos=5), ('foo bar baz', 3))
        self.assertEqual(utils.plaintext("'foo' 'b'ar b'az'", curpos=6), ('foo bar baz', 4))
        self.assertEqual(utils.plaintext("'foo' 'b'ar b'az'", curpos=7), ('foo bar baz', 4))
        self.assertEqual(utils.plaintext("'foo' 'b'ar b'az'", curpos=8), ('foo bar baz', 5))
        self.assertEqual(utils.plaintext("'foo' 'b'ar b'az'", curpos=9), ('foo bar baz', 5))
        self.assertEqual(utils.plaintext("'foo' 'b'ar b'az'", curpos=10), ('foo bar baz', 6))
        self.assertEqual(utils.plaintext("'foo' 'b'ar b'az'", curpos=11), ('foo bar baz', 7))
        self.assertEqual(utils.plaintext("'foo' 'b'ar b'az'", curpos=12), ('foo bar baz', 8))
        self.assertEqual(utils.plaintext("'foo' 'b'ar b'az'", curpos=13), ('foo bar baz', 9))
        self.assertEqual(utils.plaintext("'foo' 'b'ar b'az'", curpos=14), ('foo bar baz', 9))
        self.assertEqual(utils.plaintext("'foo' 'b'ar b'az'", curpos=15), ('foo bar baz', 10))
        self.assertEqual(utils.plaintext("'foo' 'b'ar b'az'", curpos=16), ('foo bar baz', 11))
        self.assertEqual(utils.plaintext("'foo' 'b'ar b'az'", curpos=17), ('foo bar baz', 11))

    def test_double_quotes(self):
        self.assertEqual(utils.plaintext('"foo" "b"ar b"az"'), "foo bar baz")
        self.assertEqual(utils.plaintext('"foo" "b"ar b"az"', curpos=0), ("foo bar baz", 0))
        self.assertEqual(utils.plaintext('"foo" "b"ar b"az"', curpos=1), ("foo bar baz", 0))
        self.assertEqual(utils.plaintext('"foo" "b"ar b"az"', curpos=2), ("foo bar baz", 1))
        self.assertEqual(utils.plaintext('"foo" "b"ar b"az"', curpos=3), ("foo bar baz", 2))
        self.assertEqual(utils.plaintext('"foo" "b"ar b"az"', curpos=4), ("foo bar baz", 3))
        self.assertEqual(utils.plaintext('"foo" "b"ar b"az"', curpos=5), ("foo bar baz", 3))
        self.assertEqual(utils.plaintext('"foo" "b"ar b"az"', curpos=6), ("foo bar baz", 4))
        self.assertEqual(utils.plaintext('"foo" "b"ar b"az"', curpos=7), ("foo bar baz", 4))
        self.assertEqual(utils.plaintext('"foo" "b"ar b"az"', curpos=8), ("foo bar baz", 5))
        self.assertEqual(utils.plaintext('"foo" "b"ar b"az"', curpos=9), ("foo bar baz", 5))
        self.assertEqual(utils.plaintext('"foo" "b"ar b"az"', curpos=10), ("foo bar baz", 6))
        self.assertEqual(utils.plaintext('"foo" "b"ar b"az"', curpos=11), ("foo bar baz", 7))
        self.assertEqual(utils.plaintext('"foo" "b"ar b"az"', curpos=12), ("foo bar baz", 8))
        self.assertEqual(utils.plaintext('"foo" "b"ar b"az"', curpos=13), ("foo bar baz", 9))
        self.assertEqual(utils.plaintext('"foo" "b"ar b"az"', curpos=14), ("foo bar baz", 9))
        self.assertEqual(utils.plaintext('"foo" "b"ar b"az"', curpos=15), ("foo bar baz", 10))
        self.assertEqual(utils.plaintext('"foo" "b"ar b"az"', curpos=16), ("foo bar baz", 11))
        self.assertEqual(utils.plaintext('"foo" "b"ar b"az"', curpos=17), ("foo bar baz", 11))

    def test_double_quotes_in_single_quotes(self):
        self.assertEqual(utils.plaintext("""'"foo" "bar" "baz"'"""), '"foo" "bar" "baz"')
        self.assertEqual(utils.plaintext("""'"foo" "bar" "baz"'""", curpos=0), ('"foo" "bar" "baz"', 0))
        for i in range(1, 19):
            self.assertEqual(utils.plaintext("""'"foo" "bar" "baz"'""", curpos=i), ('"foo" "bar" "baz"', i-1))
        self.assertEqual(utils.plaintext("""'"foo" "bar" "baz"'""", curpos=19), ('"foo" "bar" "baz"', 17))

    def test_single_quotes_in_double_quotes(self):
        self.assertEqual(utils.plaintext('''"'foo' 'bar' 'baz'"'''), "'foo' 'bar' 'baz'")
        self.assertEqual(utils.plaintext('''"'foo' 'bar' 'baz'"''', curpos=0), ("'foo' 'bar' 'baz'", 0))
        for i in range(1, 19):
            self.assertEqual(utils.plaintext('''"'foo' 'bar' 'baz'"''', curpos=i), ("'foo' 'bar' 'baz'", i-1))
        self.assertEqual(utils.plaintext('''"'foo' 'bar' 'baz'"''', curpos=19), ("'foo' 'bar' 'baz'", 17))

    def test_mixed_quotes(self):
        self.assertEqual(utils.plaintext(r'''"'foo' \"bar\" 'baz'"'''), """'foo' "bar" 'baz'""")
        self.assertEqual(utils.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=0), ("""'foo' "bar" 'baz'""", 0))
        self.assertEqual(utils.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=1), ("""'foo' "bar" 'baz'""", 0))
        self.assertEqual(utils.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=2), ("""'foo' "bar" 'baz'""", 1))
        self.assertEqual(utils.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=3), ("""'foo' "bar" 'baz'""", 2))
        self.assertEqual(utils.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=4), ("""'foo' "bar" 'baz'""", 3))
        self.assertEqual(utils.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=5), ("""'foo' "bar" 'baz'""", 4))
        self.assertEqual(utils.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=6), ("""'foo' "bar" 'baz'""", 5))
        self.assertEqual(utils.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=7), ("""'foo' "bar" 'baz'""", 6))
        self.assertEqual(utils.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=8), ("""'foo' "bar" 'baz'""", 6))
        self.assertEqual(utils.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=9), ("""'foo' "bar" 'baz'""", 7))
        self.assertEqual(utils.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=10), ("""'foo' "bar" 'baz'""", 8))
        self.assertEqual(utils.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=11), ("""'foo' "bar" 'baz'""", 9))
        self.assertEqual(utils.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=12), ("""'foo' "bar" 'baz'""", 10))
        self.assertEqual(utils.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=13), ("""'foo' "bar" 'baz'""", 10))
        self.assertEqual(utils.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=14), ("""'foo' "bar" 'baz'""", 11))
        self.assertEqual(utils.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=15), ("""'foo' "bar" 'baz'""", 12))
        self.assertEqual(utils.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=16), ("""'foo' "bar" 'baz'""", 13))
        self.assertEqual(utils.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=17), ("""'foo' "bar" 'baz'""", 14))
        self.assertEqual(utils.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=18), ("""'foo' "bar" 'baz'""", 15))
        self.assertEqual(utils.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=19), ("""'foo' "bar" 'baz'""", 16))
        self.assertEqual(utils.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=20), ("""'foo' "bar" 'baz'""", 17))
        self.assertEqual(utils.plaintext(r'''"'foo' \"bar\" 'baz'"''', curpos=21), ("""'foo' "bar" 'baz'""", 17))

    def test_backslash_in_single_quotes_before_nonquotes(self):
        self.assertEqual(utils.plaintext(r"""'f\oo' bar"""), r"""f\oo bar""")
        self.assertEqual(utils.plaintext(r"""'f\oo' bar""", curpos=0), (r"""f\oo bar""", 0))
        self.assertEqual(utils.plaintext(r"""'f\oo' bar""", curpos=1), (r"""f\oo bar""", 0))
        self.assertEqual(utils.plaintext(r"""'f\oo' bar""", curpos=2), (r"""f\oo bar""", 1))
        self.assertEqual(utils.plaintext(r"""'f\oo' bar""", curpos=3), (r"""f\oo bar""", 2))
        self.assertEqual(utils.plaintext(r"""'f\oo' bar""", curpos=4), (r"""f\oo bar""", 3))
        self.assertEqual(utils.plaintext(r"""'f\oo' bar""", curpos=5), (r"""f\oo bar""", 4))
        self.assertEqual(utils.plaintext(r"""'f\oo' bar""", curpos=6), (r"""f\oo bar""", 4))
        self.assertEqual(utils.plaintext(r"""'f\oo' bar""", curpos=7), (r"""f\oo bar""", 5))

    def test_backslash_in_double_quotes_before_nonquotes(self):
        self.assertEqual(utils.plaintext(r'''foo "b\r"'''), r'''foo b\r''')
        self.assertEqual(utils.plaintext(r'''foo "b\r"''', curpos=4), (r'''foo b\r''', 4))
        self.assertEqual(utils.plaintext(r'''foo "b\r"''', curpos=5), (r'''foo b\r''', 4))
        self.assertEqual(utils.plaintext(r'''foo "b\r"''', curpos=6), (r'''foo b\r''', 5))
        self.assertEqual(utils.plaintext(r'''foo "b\r"''', curpos=7), (r'''foo b\r''', 6))
        self.assertEqual(utils.plaintext(r'''foo "b\r"''', curpos=8), (r'''foo b\r''', 7))
        self.assertEqual(utils.plaintext(r'''foo "b\r"''', curpos=9), (r'''foo b\r''', 7))

    def test_backslash_before_single_quote_in_double_quotes(self):
        self.assertEqual(utils.plaintext(r'''"foo\'"'''), r"foo\'")
        self.assertEqual(utils.plaintext(r'''"foo\'"''', curpos=0), (r"foo\'", 0))
        self.assertEqual(utils.plaintext(r'''"foo\'"''', curpos=1), (r"foo\'", 0))
        self.assertEqual(utils.plaintext(r'''"foo\'"''', curpos=2), (r"foo\'", 1))
        self.assertEqual(utils.plaintext(r'''"foo\'"''', curpos=3), (r"foo\'", 2))
        self.assertEqual(utils.plaintext(r'''"foo\'"''', curpos=4), (r"foo\'", 3))
        self.assertEqual(utils.plaintext(r'''"foo\'"''', curpos=5), (r"foo\'", 4))
        self.assertEqual(utils.plaintext(r'''"foo\'"''', curpos=6), (r"foo\'", 5))
        self.assertEqual(utils.plaintext(r'''"foo\'"''', curpos=7), (r"foo\'", 5))

    def test_backslash_before_double_quote_in_single_quotes(self):
        self.assertEqual(utils.plaintext(r"""'foo\"'"""), r'foo\"')
        self.assertEqual(utils.plaintext(r"""'foo\"'""", curpos=0), (r'foo\"', 0))
        self.assertEqual(utils.plaintext(r"""'foo\"'""", curpos=1), (r'foo\"', 0))
        self.assertEqual(utils.plaintext(r"""'foo\"'""", curpos=2), (r'foo\"', 1))
        self.assertEqual(utils.plaintext(r"""'foo\"'""", curpos=3), (r'foo\"', 2))
        self.assertEqual(utils.plaintext(r"""'foo\"'""", curpos=4), (r'foo\"', 3))
        self.assertEqual(utils.plaintext(r"""'foo\"'""", curpos=5), (r'foo\"', 4))
        self.assertEqual(utils.plaintext(r"""'foo\"'""", curpos=6), (r'foo\"', 5))
        self.assertEqual(utils.plaintext(r"""'foo\"'""", curpos=7), (r'foo\"', 5))

    def test_escaped_backslash_before_closing_quote(self):
        self.assertEqual(utils.plaintext(r"'foo \\' bar"), r'foo \ bar')
        self.assertEqual(utils.plaintext(r"'foo \\' bar", curpos=4), (r'foo \ bar', 3))
        self.assertEqual(utils.plaintext(r"'foo \\' bar", curpos=5), (r'foo \ bar', 4))
        self.assertEqual(utils.plaintext(r"'foo \\' bar", curpos=6), (r'foo \ bar', 4))
        self.assertEqual(utils.plaintext(r"'foo \\' bar", curpos=7), (r'foo \ bar', 5))
        self.assertEqual(utils.plaintext(r"'foo \\' bar", curpos=8), (r'foo \ bar', 5))
        self.assertEqual(utils.plaintext(r"'foo \\' bar", curpos=9), (r'foo \ bar', 6))
        self.assertEqual(utils.plaintext(r"'foo \\' bar", curpos=10), (r'foo \ bar', 7))

    def test_unbalanced_single_quote(self):
        self.assertEqual(utils.plaintext("'foo  "), 'foo  ')
        self.assertEqual(utils.plaintext("'foo  ", curpos=0), ('foo  ', 0))
        self.assertEqual(utils.plaintext("'foo  ", curpos=1), ('foo  ', 0))
        self.assertEqual(utils.plaintext("'foo  ", curpos=2), ('foo  ', 1))
        self.assertEqual(utils.plaintext("'foo  ", curpos=3), ('foo  ', 2))
        self.assertEqual(utils.plaintext("'foo  ", curpos=4), ('foo  ', 3))
        self.assertEqual(utils.plaintext("'foo  ", curpos=5), ('foo  ', 4))
        self.assertEqual(utils.plaintext("'foo  ", curpos=6), ('foo  ', 5))

    def test_unbalanced_double_quote(self):
        self.assertEqual(utils.plaintext('"foo   '), "foo   ")
        self.assertEqual(utils.plaintext('"foo   ', curpos=0), ("foo   ", 0))
        self.assertEqual(utils.plaintext('"foo   ', curpos=1), ("foo   ", 0))
        self.assertEqual(utils.plaintext('"foo   ', curpos=2), ("foo   ", 1))
        self.assertEqual(utils.plaintext('"foo   ', curpos=3), ("foo   ", 2))
        self.assertEqual(utils.plaintext('"foo   ', curpos=4), ("foo   ", 3))
        self.assertEqual(utils.plaintext('"foo   ', curpos=5), ("foo   ", 4))
        self.assertEqual(utils.plaintext('"foo   ', curpos=6), ("foo   ", 5))
        self.assertEqual(utils.plaintext('"foo   ', curpos=7), ("foo   ", 6))

    def test_double_quotes_in_unbalanced_single_quotes(self):
        self.assertEqual(utils.plaintext(r''''foo\'s "bar"'''), '''foo's "bar"''')
        self.assertEqual(utils.plaintext(r''''foo\'s "bar"''', curpos=0), ('''foo's "bar"''', 0))
        self.assertEqual(utils.plaintext(r''''foo\'s "bar"''', curpos=1), ('''foo's "bar"''', 0))
        self.assertEqual(utils.plaintext(r''''foo\'s "bar"''', curpos=2), ('''foo's "bar"''', 1))
        self.assertEqual(utils.plaintext(r''''foo\'s "bar"''', curpos=3), ('''foo's "bar"''', 2))
        self.assertEqual(utils.plaintext(r''''foo\'s "bar"''', curpos=4), ('''foo's "bar"''', 3))
        self.assertEqual(utils.plaintext(r''''foo\'s "bar"''', curpos=5), ('''foo's "bar"''', 3))
        self.assertEqual(utils.plaintext(r''''foo\'s "bar"''', curpos=6), ('''foo's "bar"''', 4))
        self.assertEqual(utils.plaintext(r''''foo\'s "bar"''', curpos=7), ('''foo's "bar"''', 5))
        self.assertEqual(utils.plaintext(r''''foo\'s "bar"''', curpos=8), ('''foo's "bar"''', 6))
        self.assertEqual(utils.plaintext(r''''foo\'s "bar"''', curpos=9), ('''foo's "bar"''', 7))
        self.assertEqual(utils.plaintext(r''''foo\'s "bar"''', curpos=10), ('''foo's "bar"''', 8))
        self.assertEqual(utils.plaintext(r''''foo\'s "bar"''', curpos=11), ('''foo's "bar"''', 9))
        self.assertEqual(utils.plaintext(r''''foo\'s "bar"''', curpos=12), ('''foo's "bar"''', 10))

    def test_single_quotes_in_unbalanced_double_quotes(self):
        self.assertEqual(utils.plaintext(r'''"foo bar's'''), '''foo bar's''')
        self.assertEqual(utils.plaintext(r'''"foo bar's''', curpos=7), ('''foo bar's''', 6))
        self.assertEqual(utils.plaintext(r'''"foo bar's''', curpos=8), ('''foo bar's''', 7))
        self.assertEqual(utils.plaintext(r'''"foo bar's''', curpos=9), ('''foo bar's''', 8))
        self.assertEqual(utils.plaintext(r'''"foo bar's''', curpos=10), ('''foo bar's''', 9))

    def test_mixed_quotes_in_unbalanced_single_quotes(self):
        self.assertEqual(utils.plaintext(r'''f'oo\'s "bar"'''), '''foo's "bar"''')
        self.assertEqual(utils.plaintext(r'''f'oo\'s "bar"''', curpos=0), ('''foo's "bar"''', 0))
        self.assertEqual(utils.plaintext(r'''f'oo\'s "bar"''', curpos=1), ('''foo's "bar"''', 1))
        self.assertEqual(utils.plaintext(r'''f'oo\'s "bar"''', curpos=2), ('''foo's "bar"''', 1))
        self.assertEqual(utils.plaintext(r'''f'oo\'s "bar"''', curpos=3), ('''foo's "bar"''', 2))
        self.assertEqual(utils.plaintext(r'''f'oo\'s "bar"''', curpos=4), ('''foo's "bar"''', 3))
        self.assertEqual(utils.plaintext(r'''f'oo\'s "bar"''', curpos=5), ('''foo's "bar"''', 3))
        self.assertEqual(utils.plaintext(r'''f'oo\'s "bar"''', curpos=6), ('''foo's "bar"''', 4))
        self.assertEqual(utils.plaintext(r'''f'oo\'s "bar"''', curpos=7), ('''foo's "bar"''', 5))
        self.assertEqual(utils.plaintext(r'''f'oo\'s "bar"''', curpos=8), ('''foo's "bar"''', 6))
        self.assertEqual(utils.plaintext(r'''f'oo\'s "bar"''', curpos=9), ('''foo's "bar"''', 7))
        self.assertEqual(utils.plaintext(r'''f'oo\'s "bar"''', curpos=10), ('''foo's "bar"''', 8))
        self.assertEqual(utils.plaintext(r'''f'oo\'s "bar"''', curpos=11), ('''foo's "bar"''', 9))
        self.assertEqual(utils.plaintext(r'''f'oo\'s "bar"''', curpos=12), ('''foo's "bar"''', 10))
        self.assertEqual(utils.plaintext(r'''f'oo\'s "bar"''', curpos=13), ('''foo's "bar"''', 11))

    def test_mixed_quotes_in_unbalanced_double_quotes(self):
        self.assertEqual(utils.plaintext(r'''"foo 'b\"ar'''), '''foo 'b"ar''')
        self.assertEqual(utils.plaintext(r'''"foo 'b\"ar''', curpos=5), ('''foo 'b"ar''', 4))
        self.assertEqual(utils.plaintext(r'''"foo 'b\"ar''', curpos=6), ('''foo 'b"ar''', 5))
        self.assertEqual(utils.plaintext(r'''"foo 'b\"ar''', curpos=7), ('''foo 'b"ar''', 6))
        self.assertEqual(utils.plaintext(r'''"foo 'b\"ar''', curpos=8), ('''foo 'b"ar''', 6))
        self.assertEqual(utils.plaintext(r'''"foo 'b\"ar''', curpos=9), ('''foo 'b"ar''', 7))
        self.assertEqual(utils.plaintext(r'''"foo 'b\"ar''', curpos=10), ('''foo 'b"ar''', 8))
        self.assertEqual(utils.plaintext(r'''"foo 'b\"ar''', curpos=11), ('''foo 'b"ar''', 9))

    def test_unbalanced_quotes_with_trailing_spaces(self):
        self.assertEqual(utils.plaintext("'foo "), 'foo ')
        self.assertEqual(utils.plaintext('"bar  '), 'bar  ')

    def test_unbalanced_quotes_with_leading_spaces(self):
        self.assertEqual(utils.plaintext("' "), ' ')
        self.assertEqual(utils.plaintext('"  '), '  ')
        self.assertEqual(utils.plaintext("'   "), '   ')
        self.assertEqual(utils.plaintext('"    '), '    ')

    def test_unbalanced_quotes_without_actual_text(self):
        self.assertEqual(utils.plaintext("'"), '')
        self.assertEqual(utils.plaintext('"'), '')

    def test_single_quotes_with_surrounding_spaces(self):
        self.assertEqual(utils.plaintext(" 'foo bar' "), 'foo bar')
        self.assertEqual(utils.plaintext(" 'foo bar' ", curpos=0), ('foo bar', 0))
        self.assertEqual(utils.plaintext(" 'foo bar' ", curpos=1), ('foo bar', 0))
        self.assertEqual(utils.plaintext(" 'foo bar' ", curpos=2), ('foo bar', 0))
        self.assertEqual(utils.plaintext(" 'foo bar' ", curpos=3), ('foo bar', 1))
        self.assertEqual(utils.plaintext(" 'foo bar' ", curpos=4), ('foo bar', 2))
        self.assertEqual(utils.plaintext(" 'foo bar' ", curpos=5), ('foo bar', 3))
        self.assertEqual(utils.plaintext(" 'foo bar' ", curpos=6), ('foo bar', 4))
        self.assertEqual(utils.plaintext(" 'foo bar' ", curpos=7), ('foo bar', 5))
        self.assertEqual(utils.plaintext(" 'foo bar' ", curpos=8), ('foo bar', 6))
        self.assertEqual(utils.plaintext(" 'foo bar' ", curpos=9), ('foo bar', 7))
        self.assertEqual(utils.plaintext(" 'foo bar' ", curpos=10), ('foo bar', 7))
        self.assertEqual(utils.plaintext(" 'foo bar' ", curpos=11), ('foo bar', 7))

    def test_double_quotes_with_surrounding_spaces(self):
        self.assertEqual(utils.plaintext('  " foo bar "  '), ' foo bar ')
        self.assertEqual(utils.plaintext('  " foo bar "  ', curpos=0), (' foo bar ', 0))
        self.assertEqual(utils.plaintext('  " foo bar "  ', curpos=1), (' foo bar ', 0))
        self.assertEqual(utils.plaintext('  " foo bar "  ', curpos=2), (' foo bar ', 0))
        self.assertEqual(utils.plaintext('  " foo bar "  ', curpos=3), (' foo bar ', 0))
        self.assertEqual(utils.plaintext('  " foo bar "  ', curpos=4), (' foo bar ', 1))
        self.assertEqual(utils.plaintext('  " foo bar "  ', curpos=5), (' foo bar ', 2))
        self.assertEqual(utils.plaintext('  " foo bar "  ', curpos=6), (' foo bar ', 3))
        self.assertEqual(utils.plaintext('  " foo bar "  ', curpos=7), (' foo bar ', 4))
        self.assertEqual(utils.plaintext('  " foo bar "  ', curpos=8), (' foo bar ', 5))
        self.assertEqual(utils.plaintext('  " foo bar "  ', curpos=9), (' foo bar ', 6))
        self.assertEqual(utils.plaintext('  " foo bar "  ', curpos=10), (' foo bar ', 7))
        self.assertEqual(utils.plaintext('  " foo bar "  ', curpos=11), (' foo bar ', 8))
        self.assertEqual(utils.plaintext('  " foo bar "  ', curpos=12), (' foo bar ', 9))
        self.assertEqual(utils.plaintext('  " foo bar "  ', curpos=13), (' foo bar ', 9))
        self.assertEqual(utils.plaintext('  " foo bar "  ', curpos=14), (' foo bar ', 9))
        self.assertEqual(utils.plaintext('  " foo bar "  ', curpos=15), (' foo bar ', 9))


class Test_tokenize(unittest.TestCase):
    def do(self, input, output, delims=None):
        if delims is not None:
            self.assertEqual(utils.tokenize(input, delims=delims), output)
        else:
            self.assertEqual(utils.tokenize(input), output)

    def test_empty_cmdline(self):
        self.do('', [''])
        self.do(' ', [' '])
        self.do('  ', [' ', ' '])
        self.do('   ', [' ', ' ', ' '])

    def test_custom_delimiters(self):
        self.do('foo.bar:baz', ['foo', '.', 'bar', ':', 'baz'], delims=('.',':'))
        self.do(' foo .  bar  :   baz   ', [' foo ', '.', '  bar  ', ':', '   baz   '], delims=('.',':',))
        self.do(r'foo \. bar : baz', [r'foo \. bar ', ':', ' baz'], delims=('.',':',))
        self.do(r'foo.:bar":b"az', [r'foo', '.', ':', 'bar":b"az'], delims=('.',':',))

    def test_delimiters_are_tokens(self):
        self.do('foo bar baz', ['foo', ' ', 'bar', ' ', 'baz'])
        self.do('foo  bar baz', ['foo', ' ', ' ', 'bar', ' ', 'baz'])
        self.do('foo bar  baz', ['foo', ' ', 'bar', ' ', ' ', 'baz'])
        self.do(' foo bar baz', [' ', 'foo', ' ', 'bar', ' ', 'baz'])
        self.do('  foo bar baz ', [' ', ' ', 'foo', ' ', 'bar', ' ', 'baz', ' '])
        self.do('foo bar  baz   ', ['foo', ' ', 'bar', ' ', ' ', 'baz', ' ', ' ', ' '])

    def test_escaped_spaces(self):
        self.do(r'foo\ bar baz', [r'foo\ bar', ' ', 'baz'])
        self.do(r'foo bar\ baz', ['foo', ' ', r'bar\ baz'])

    def test_escaped_backslash(self):
        self.do(r'foo bar\\ baz', ['foo', ' ', r"""bar\\""", ' ', 'baz'])
        self.do(r'foo bar\\\ baz', ['foo', ' ', r"""bar\\\ baz"""])
        self.do(r'foo bar\\\\ baz', ['foo', ' ', r"""bar\\\\""", ' ', 'baz'])
        self.do(r'foo bar\\\\\ baz', ['foo', ' ', r"""bar\\\\\ baz"""])
        self.do(r'foo bar\\\\\\ baz', ['foo', ' ', r"""bar\\\\\\""", ' ', 'baz'])

    def test_double_quotes(self):
        self.do('"foo bar" baz', ['"foo bar"', ' ', 'baz'])
        self.do('foo "bar baz"', ['foo', ' ', '"bar baz"'])
        self.do('"f"oo "b"ar "b"az', ['"f"oo', ' ', '"b"ar', ' ', '"b"az'])
        self.do('f"o"o b"a"r b"a"z', ['f"o"o', ' ', 'b"a"r', ' ', 'b"a"z'])
        self.do('fo"o" ba"r" ba"z"', ['fo"o"', ' ', 'ba"r"', ' ', 'ba"z"'])
        self.do('" foo " bar b" a "z', ['" foo "', ' ', 'bar', ' ', 'b" a "z'])
        self.do('fo" o " " bar " baz', ['fo" o "', ' ', '" bar "', ' ', 'baz'])
        self.do('" foo  bar " " baz "', ['" foo  bar "', ' ', '" baz "'])

    def test_single_quotes(self):
        self.do("'foo bar' baz", ["'foo bar'", " ", "baz"])
        self.do("foo 'bar baz'", ["foo", " ", "'bar baz'"])
        self.do("'f'oo 'b'ar 'b'az", ["'f'oo", " ", "'b'ar", " ", "'b'az"])
        self.do("f'o'o b'a'r b'a'z", ["f'o'o", " ", "b'a'r", " ", "b'a'z"])
        self.do("fo'o' ba'r' ba'z'", ["fo'o'", " ", "ba'r'", " ", "ba'z'"])
        self.do("' foo ' bar b' a 'z", ["' foo '", " ", "bar", " ", "b' a 'z"])
        self.do("fo' o ' ' bar ' baz", ["fo' o '", " ", "' bar '", " ", "baz"])
        self.do("' foo  bar ' ' baz '", ["' foo  bar '", " ", "' baz '"])

    def test_escaped_double_quotes(self):
        self.do(r'\"foo\" bar baz\"', [r'\"foo\"', ' ', 'bar', ' ', r'baz\"'])
        self.do(r'foo\" ba\"r baz', [r'foo\"', ' ', r'ba\"r', ' ', 'baz'])
        self.do(r'foo ba\"r \"baz', ['foo', ' ', r'ba\"r', ' ', r'\"baz'])

    def test_escaped_single_quotes(self):
        self.do(r"\'foo\' bar baz", [r"\'foo\'", ' ', "bar", ' ', "baz"])
        self.do(r"foo\' ba\'r baz", [r"foo\'", ' ', r"ba\'r", ' ', "baz"])
        self.do(r"foo ba\'r \'baz", ["foo", ' ', r"ba\'r", ' ', r"\'baz"])
        self.do(r"'foo\'s bar' baz", [r"'foo\'s bar'", ' ', "baz"])

    def test_escaped_backslash_in_double_quotes(self):
        self.do(r'foo "\\bar " baz', ['foo', ' ', r'"\\bar "', ' ', 'baz'])
        self.do(r'foo "bar \\" baz', ['foo', ' ', r'"bar \\"', ' ', 'baz'])

    def test_escaped_backslash_in_single_quotes(self):
        self.do(r"foo '\\bar ' baz", ["foo", " ", r"'\\bar '", " ", "baz"])
        self.do(r"foo 'bar \\' baz", ["foo", " ", r"'bar \\'", " ", "baz"])

    def test_unbalanced_single_quotes(self):
        self.do("'foo bar baz", ["'foo bar baz"])
        self.do("fo'o bar baz", ["fo'o bar baz"])
        self.do("foo 'bar baz", ['foo', ' ', "'bar baz"])
        self.do("foo bar' baz", ['foo', ' ', "bar' baz"])
        self.do("foo bar baz'", ['foo', ' ', 'bar', ' ', "baz'"])

    def test_unbalanced_double_quotes(self):
        self.do('"foo bar baz', ['"foo bar baz'])
        self.do('fo"o bar baz', ['fo"o bar baz'])
        self.do('foo "bar baz', ["foo", ' ', '"bar baz'])
        self.do('foo bar" baz', ["foo", ' ', 'bar" baz'])
        self.do('foo bar baz"', ["foo", ' ', "bar", ' ', 'baz"'])

    def test_double_quotes_in_single_quotes(self):
        self.do("""'fo"o b"ar ' baz""", ["""'fo"o b"ar '""", ' ', 'baz'])

    def test_single_quotes_in_double_quotes(self):
        self.do('''"fo'o b'ar " baz''', ['''"fo'o b'ar "''', ' ', "baz"])


class Test_get_position(unittest.TestCase):
    def do(self, input, output, delims=None):
        if delims is not None:
            self.assertEqual(utils.get_position(*input, delims=delims), output)
        else:
            self.assertEqual(utils.get_position(*input), output)

    def test_single_delimiters(self):
        self.do((['foo', ' ', 'bar', ' ', 'baz'],   0), (['foo', ' ', 'bar', ' ', 'baz'], 0, 0))
        self.do((['foo', ' ', 'bar', ' ', 'baz'],   1), (['foo', ' ', 'bar', ' ', 'baz'], 0, 1))
        self.do((['foo', ' ', 'bar', ' ', 'baz'],   2), (['foo', ' ', 'bar', ' ', 'baz'], 0, 2))
        self.do((['foo', ' ', 'bar', ' ', 'baz'],   3), (['foo', ' ', 'bar', ' ', 'baz'], 0, 3))
        self.do((['foo', ' ', 'bar', ' ', 'baz'],   4), (['foo', ' ', 'bar', ' ', 'baz'], 2, 0))
        self.do((['foo', ' ', 'bar', ' ', 'baz'],   5), (['foo', ' ', 'bar', ' ', 'baz'], 2, 1))
        self.do((['foo', ' ', 'bar', ' ', 'baz'],   6), (['foo', ' ', 'bar', ' ', 'baz'], 2, 2))
        self.do((['foo', ' ', 'bar', ' ', 'baz'],   7), (['foo', ' ', 'bar', ' ', 'baz'], 2, 3))
        self.do((['foo', ' ', 'bar', ' ', 'baz'],   8), (['foo', ' ', 'bar', ' ', 'baz'], 4, 0))
        self.do((['foo', ' ', 'bar', ' ', 'baz'],   9), (['foo', ' ', 'bar', ' ', 'baz'], 4, 1))
        self.do((['foo', ' ', 'bar', ' ', 'baz'],  10), (['foo', ' ', 'bar', ' ', 'baz'], 4, 2))
        self.do((['foo', ' ', 'bar', ' ', 'baz'],  11), (['foo', ' ', 'bar', ' ', 'baz'], 4, 3))

    def test_mutliple_delimiters(self):
        self.do((['foo', ' ', ' ', 'bar'], 3), (['foo', ' ', ' ', 'bar'], 0, 3))
        self.do((['foo', ' ', ' ', 'bar'], 4), (['foo', ' ', '', ' ', 'bar'], 2, 0))
        self.do((['foo', ' ', ' ', 'bar'], 5), (['foo', ' ', ' ', 'bar'], 3, 0))
        self.do((['foo', ' ', ' ', 'bar'], 6), (['foo', ' ', ' ', 'bar'], 3, 1))

        self.do((['foo', ' ', ' ', ' ', 'bar'], 3), (['foo', ' ', ' ', ' ', 'bar'], 0, 3))
        self.do((['foo', ' ', ' ', ' ', 'bar'], 4), (['foo', ' ', '', ' ', ' ', 'bar'], 2, 0))
        self.do((['foo', ' ', ' ', ' ', 'bar'], 5), (['foo', ' ', ' ', '', ' ', 'bar'], 3, 0))
        self.do((['foo', ' ', ' ', ' ', 'bar'], 6), (['foo', ' ', ' ', ' ', 'bar'], 4, 0))
        self.do((['foo', ' ', ' ', ' ', 'bar'], 7), (['foo', ' ', ' ', ' ', 'bar'], 4, 1))

    def test_leading_delimiters(self):
        self.do(([' ', 'foo'], 0), (['', ' ', 'foo'], 0, 0))
        self.do(([' ', 'foo'], 1), ([' ', 'foo'], 1, 0))
        self.do(([' ', 'foo'], 2), ([' ', 'foo'], 1, 1))
        self.do(([' ', 'foo'], 3), ([' ', 'foo'], 1, 2))
        self.do(([' ', 'foo'], 4), ([' ', 'foo'], 1, 3))

        self.do(([' ', ' ', 'foo'], 0), (['', ' ', ' ', 'foo'], 0, 0))
        self.do(([' ', ' ', 'foo'], 1), ([' ', '', ' ', 'foo'], 1, 0))
        self.do(([' ', ' ', 'foo'], 2), ([' ', ' ', 'foo'], 2, 0))
        self.do(([' ', ' ', 'foo'], 3), ([' ', ' ', 'foo'], 2, 1))
        self.do(([' ', ' ', 'foo'], 4), ([' ', ' ', 'foo'], 2, 2))
        self.do(([' ', ' ', 'foo'], 5), ([' ', ' ', 'foo'], 2, 3))

    def test_trailing_delimiters(self):
        self.do((['foo', ' '], 3), (['foo', ' '], 0, 3))
        self.do((['foo', ' '], 4), (['foo', ' ', ''], 2, 0))
        self.do((['foo', ' ', ' '], 5), (['foo', ' ', ' ', ''], 3, 0))
        self.do((['foo', ' ', ' ', ' '], 6), (['foo', ' ', ' ', ' ', ''], 4, 0))


class TestArg(unittest.TestCase):
    def test_before_cursor(self):
        self.assertEqual(utils.Arg('foo', curpos=0).before_cursor, '')
        self.assertEqual(utils.Arg('foo', curpos=1).before_cursor, 'f')
        self.assertEqual(utils.Arg('foo', curpos=2).before_cursor, 'fo')
        self.assertEqual(utils.Arg('foo', curpos=3).before_cursor, 'foo')

    def test_splitting(self):
        def do(arg, curpos, seps, exp_parts, exp_curpart, exp_curpart_index, exp_curpart_curpos):
            arg = utils.Arg(arg, curpos)
            arg.separators = seps
            self.assertEqual(arg.parts, exp_parts)
            self.assertEqual(arg.curpart, exp_curpart)
            self.assertEqual(arg.curpart_index, exp_curpart_index)
            self.assertEqual(arg.curpart_curpos, exp_curpart_curpos)
            self.assertEqual(arg.separators, seps)
            self.assertEqual(arg.curpos, curpos)
        do('foo/bar/baz',  0, '/', ('foo', 'bar', 'baz'), 'foo', 0, 0)
        do('foo/bar/baz',  1, '/', ('foo', 'bar', 'baz'), 'foo', 0, 1)
        do('foo/bar/baz',  2, '/', ('foo', 'bar', 'baz'), 'foo', 0, 2)
        do('foo/bar/baz',  3, '/', ('foo', 'bar', 'baz'), 'foo', 0, 3)
        do('foo/bar/baz',  4, '/', ('foo', 'bar', 'baz'), 'bar', 1, 0)
        do('foo/bar/baz',  5, '/', ('foo', 'bar', 'baz'), 'bar', 1, 1)
        do('foo/bar/baz',  6, '/', ('foo', 'bar', 'baz'), 'bar', 1, 2)
        do('foo/bar/baz',  7, '/', ('foo', 'bar', 'baz'), 'bar', 1, 3)
        do('foo/bar/baz',  8, '/', ('foo', 'bar', 'baz'), 'baz', 2, 0)
        do('foo/bar/baz',  9, '/', ('foo', 'bar', 'baz'), 'baz', 2, 1)
        do('foo/bar/baz', 10, '/', ('foo', 'bar', 'baz'), 'baz', 2, 2)
        do('foo/bar/baz', 11, '/', ('foo', 'bar', 'baz'), 'baz', 2, 3)

    def test_unsplitting(self):
        arg = utils.Arg('foo,bar,baz', 0)
        arg.separators = (',',)
        self.assertEqual(arg.parts, ('foo', 'bar', 'baz'))
        arg.separators = ()
        self.assertEqual(arg.parts, ('foo,bar,baz',))

    def test_multiple_separators(self):
        arg = utils.Arg('foo.bar:.baz!', 0)
        arg.separators = ('.', ':', '!')
        self.assertEqual(arg.parts, ('foo', 'bar', '', 'baz', ''))

    def test_multichar_separators(self):
        arg = utils.Arg('foo...bar.:!baz!', 0)
        arg.separators = ('..', '.:!')
        self.assertEqual(arg.parts, ('foo', '.bar', 'baz!'))


class Test_as_args(unittest.TestCase):
    def do(self, tokens, curtok, tokcurpos, exp_args, exp_argindex, exp_argcurpos):
        args, argindex, argcurpos = utils.as_args(tokens, curtok, tokcurpos)
        self.assertEqual((args, argindex, argcurpos), (exp_args, exp_argindex, exp_argcurpos))
        for arg in args:
            self.assertTrue(isinstance(arg, utils.Arg))
        for i,arg in enumerate(args):
            if i == argindex:
                self.assertEqual(arg.curpos, exp_argcurpos)
            else:
                self.assertEqual(arg.curpos, None)

    def test_no_tokens(self):
        self.do(('',), 0, 0, [''], 0, 0)

    def test_single_delimiters(self):
        # As long as as_args() gets input via tokenize() and get_position(), the
        # cursor should never be on a delimiter.
        self.do(('foo', ' ', 'bar', ' ', 'baz'), 0, 0, ['foo', 'bar', 'baz'], 0, 0)
        self.do(('foo', ' ', 'bar', ' ', 'baz'), 0, 1, ['foo', 'bar', 'baz'], 0, 1)
        self.do(('foo', ' ', 'bar', ' ', 'baz'), 0, 2, ['foo', 'bar', 'baz'], 0, 2)
        self.do(('foo', ' ', 'bar', ' ', 'baz'), 0, 3, ['foo', 'bar', 'baz'], 0, 3)
        self.do(('foo', ' ', 'bar', ' ', 'baz'), 2, 0, ['foo', 'bar', 'baz'], 1, 0)
        self.do(('foo', ' ', 'bar', ' ', 'baz'), 2, 1, ['foo', 'bar', 'baz'], 1, 1)
        self.do(('foo', ' ', 'bar', ' ', 'baz'), 2, 2, ['foo', 'bar', 'baz'], 1, 2)
        self.do(('foo', ' ', 'bar', ' ', 'baz'), 2, 3, ['foo', 'bar', 'baz'], 1, 3)
        self.do(('foo', ' ', 'bar', ' ', 'baz'), 4, 0, ['foo', 'bar', 'baz'], 2, 0)
        self.do(('foo', ' ', 'bar', ' ', 'baz'), 4, 1, ['foo', 'bar', 'baz'], 2, 1)
        self.do(('foo', ' ', 'bar', ' ', 'baz'), 4, 2, ['foo', 'bar', 'baz'], 2, 2)
        self.do(('foo', ' ', 'bar', ' ', 'baz'), 4, 3, ['foo', 'bar', 'baz'], 2, 3)

    def test_multiple_delimiters(self):
        # Multiple consecutive delimiters insert an empty token for the cursor
        # to sit on
        self.do(('foo', ' ', '', ' ', 'bar'), 0, 3, ['foo', '', 'bar'], 0, 3)
        self.do(('foo', ' ', '', ' ', 'bar'), 2, 0, ['foo', '', 'bar'], 1, 0)
        self.do(('foo', ' ', ' ', '', ' ', 'bar'), 3, 0, ['foo', '', 'bar'], 1, 0)
        self.do(('foo', ' ', ' ', ' ', 'bar'), 4, 0, ['foo', 'bar'], 1, 0)

    def test_leading_delimiters(self):
        # Leading delimiters insert an empty token for the cursor to sit on
        self.do(('', ' ', 'foo'), 0, 0, ['', 'foo'], 0, 0)
        self.do((' ', 'foo'), 1, 0, ['foo'], 0, 0)
        self.do((' ', 'foo'), 1, 1, ['foo'], 0, 1)

        self.do(('', ' ', ' ', 'foo'), 0, 0, ['', 'foo'], 0, 0)
        self.do((' ', '', ' ', 'foo'), 1, 0, ['', 'foo'], 0, 0)
        self.do((' ', ' ', 'foo'), 2, 0, ['foo'], 0, 0)
        self.do((' ', ' ', 'foo'), 2, 1, ['foo'], 0, 1)

    def test_trailing_delimiters(self):
        # Trailing delimiters insert an empty token for the cursor to sit on
        self.do(('foo', ' '), 0, 3, ['foo'], 0, 3)
        self.do(('foo', ' ', ''), 2, 0, ['foo', ''], 1, 0)
        self.do(('foo', ' ', ' ', ''), 3, 0, ['foo', ''], 1, 0)
        self.do(('foo', ' ', ' ', ' ', ''), 4, 0, ['foo', ''], 1, 0)

    def test_special_characters(self):
        # First token is literally " foo \"
        tokens = ((r'\ foo\ ' '\\\\'), ' ', '''" bar's "''', ' ', r'b"a\"z"')
        exp_args = [' foo \\', ''' bar's ''', 'ba"z']
        self.do(tokens, 0, 1, exp_args, 0, 0)
        self.do(tokens, 0, 2, exp_args, 0, 1)
        self.do(tokens, 0, 3, exp_args, 0, 2)
        self.do(tokens, 0, 4, exp_args, 0, 3)
        self.do(tokens, 0, 5, exp_args, 0, 4)
        self.do(tokens, 0, 6, exp_args, 0, 4)
        self.do(tokens, 0, 7, exp_args, 0, 5)
        self.do(tokens, 0, 8, exp_args, 0, 5)
        self.do(tokens, 0, 9, exp_args, 0, 6)
        self.do(tokens, 2, 0, exp_args, 1, 0)
        self.do(tokens, 2, 1, exp_args, 1, 0)
        self.do(tokens, 2, 2, exp_args, 1, 1)
        self.do(tokens, 2, 3, exp_args, 1, 2)
        self.do(tokens, 2, 4, exp_args, 1, 3)
        self.do(tokens, 2, 5, exp_args, 1, 4)
        self.do(tokens, 2, 6, exp_args, 1, 5)
        self.do(tokens, 2, 7, exp_args, 1, 6)
        self.do(tokens, 2, 8, exp_args, 1, 7)
        self.do(tokens, 2, 9, exp_args, 1, 7)
        self.do(tokens, 4, 0, exp_args, 2, 0)
        self.do(tokens, 4, 1, exp_args, 2, 1)
        self.do(tokens, 4, 2, exp_args, 2, 1)
        self.do(tokens, 4, 3, exp_args, 2, 2)
        self.do(tokens, 4, 4, exp_args, 2, 2)


class Test_get_current_cmd(unittest.TestCase):
    ops = ('&', 'and', '|', 'or')

    def do(self, input, output):
        input += (self.ops,)
        self.assertEqual(utils.get_current_cmd(*input), output)

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
