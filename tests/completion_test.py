from stig import completion
from stig.completion.candidates import Candidates

import unittest
from unittest.mock import patch


class Test_finalize_completion(unittest.TestCase):
    def do(self, args, output, **kwargs):
        self.assertEqual(completion.completer._finalize_completion(*args, **kwargs), output)

    def test_tail_before_cursor(self):
        self.do(('foo,bar,baz', 8), ('foo,bar,baz', 8), tail=',')

    def test_no_tail_before_cursor(self):
        self.do(('foo,barbaz', 7), ('foo,bar,baz', 8), tail=',')

    def test_tail_under_cursor(self):
        self.do(('foo,bar,baz', 7), ('foo,bar,baz', 8), tail=',')

    def test_cursor_at_end(self):
        self.do(('foo,bar', 7), ('foo,bar,', 8), tail=',')


class Test_find_common_prefix(unittest.TestCase):
    def do(self, input, output):
        self.assertEqual(completion.completer._find_common_prefix(*input), output)

    def test_no_prefix(self):
        self.do((('foo', 'bar', 'baz'), ''), '')

    def test_no_match(self):
        self.do((('foo', 'bar', 'baz'), 'x'), 'x')

    def test_completion(self):
        self.do((('foo', 'foobar', 'foobaz'), 'f'), 'foo')
        self.do((('foobar', 'foobaz'), 'f'), 'fooba')


class Test_tokenize(unittest.TestCase):
    def do(self, input, output):
        self.assertEqual(completion.completer._tokenize(*input), output)

    def test_empty_string(self):
        self.do(('', 1), ([''], 0))

    def test_focused_argument(self):
        self.do(('foo bar baz', 0), (['foo', 'bar', 'baz'], 0))
        self.do(('foo bar baz', 3), (['foo', 'bar', 'baz'], 0))
        self.do(('foo bar baz', 4), (['foo', 'bar', 'baz'], 1))
        self.do(('foo bar baz', 7), (['foo', 'bar', 'baz'], 1))
        self.do(('foo bar baz', 8), (['foo', 'bar', 'baz'], 2))
        self.do(('foo bar baz', 11), (['foo', 'bar', 'baz'], 2))

    def test_trailing_space_at_the_end(self):
        self.do(('foo ', 4), (['foo', ''], 1))
        self.do(('foo  ', 5), (['foo', ''], 1))
        self.do(('foo   ', 6), (['foo', ''], 1))

    def test_trailing_space_in_the_middle(self):
        self.do(('foo -x', 4), (['foo', '-x'], 1))
        self.do(('foo  -x', 4), (['foo', '', '-x'], 1))
        self.do(('foo  -x', 5), (['foo', '', '-x'], 2))
        self.do(('foo   -x', 5), (['foo', '', '-x'], 1))
        self.do(('foo   -x', 6), (['foo', '', '-x'], 2))
        self.do(('foo   -x', 5), (['foo', '', '-x'], 1))
        self.do(('foo   -x', 6), (['foo', '', '-x'], 2))

    def test_escaped_space(self):
        self.do((r'foo\ bar -x baz', 15), (['foo bar', '-x', 'baz'], 2))
        self.do((r'foo bar\ -x baz', 15), (['foo', 'bar -x', 'baz'], 2))
        self.do((r'foo bar\ -x\ baz', 15), (['foo', 'bar -x baz'], 1))

    def test_escaped_backslash(self):
        self.do((r'foo bar\\ -x baz', 16), (['foo', 'bar\\', '-x', 'baz'], 3))
        self.do((r'foo bar\\\ -x baz', 17), (['foo', 'bar\\ -x', 'baz'], 2))
        self.do((r'foo bar\\\\ -x baz', 18), (['foo', 'bar\\\\', '-x', 'baz'], 3))
        self.do((r'foo bar\\\\\ -x baz', 19), (['foo', 'bar\\\\ -x', 'baz'], 2))
        self.do((r'foo bar\\\\\\ -x baz', 20), (['foo', 'bar\\\\\\', '-x', 'baz'], 3))

    def test_single_quotes(self):
        self.do((r"foo 'bar baz' -x", 16), (['foo', 'bar baz', '-x'], 2))

    def test_double_quotes(self):
        self.do((r'foo "bar baz" -x', 16), (['foo', 'bar baz', '-x'], 2))

    def test_escaped_single_quotes(self):
        self.do((r"foo \'bar baz\' -x", 18), (['foo', "'bar", "baz'", '-x'], 3))

    def test_escaped_double_quotes(self):
        self.do((r'foo \"bar baz\" -x', 18), (['foo', '"bar', 'baz"', '-x'], 3))

    def test_unbalanced_single_quotes(self):
        self.do((r"foo 'bar baz -x", 16), (['foo', 'bar baz -x'], 1))

    def test_unbalanced_double_quotes(self):
        self.do((r'foo "bar baz -x', 16), (['foo', 'bar baz -x'], 1))

    def test_double_quotes_in_single_quotes(self):
        self.do((r'''foo '"bar" baz' -x''', 18), (['foo', '"bar" baz', '-x'], 2))

    def test_single_quotes_in_double_quotes(self):
        self.do((r"""foo "'bar' baz" -x""", 18), (['foo', "'bar' baz", '-x'], 2))


class Test_get_current_cmd(unittest.TestCase):
    def do(self, input, output):
        self.assertEqual(completion.Completer._get_current_cmd(*input), output)

    def test_empty_cmdline(self):
        self.do(('', 0), ('', 0))

    def test_single_command(self):
        self.do(('foo', 0), ('foo', 0))
        self.do(('foo', 1), ('foo', 1))
        self.do(('foo', 2), ('foo', 2))
        self.do(('foo', 3), ('foo', 3))

    def test_symbol_ops__cursor_on_leftmost_command(self):
        self.do(('foo -x ; bar --why & baz -z ed', 0), ('foo -x', 0))
        self.do(('foo -x & bar --why | baz -z ed', 1), ('foo -x', 1))
        self.do(('foo -x | bar --why ; baz -z ed', 6), ('foo -x', 6))
        self.do(('foo -x ; bar --why & baz -z ed', 7), ('foo -x ', 7))
        self.do(('foo -x & bar --why | baz -z ed', 8), ('foo -x & bar --why', 8))

    def test_symbol_ops__cursor_on_middle_command(self):
        self.do(('foo -x | bar --why ; baz -z ed', 9), ('bar --why', 0))
        self.do(('foo -x ; bar --why & baz -z ed', 10), ('bar --why', 1))
        self.do(('foo -x & bar --why | baz -z ed', 18), ('bar --why', 9))
        self.do(('foo -x | bar --why ; baz -z ed', 19), ('bar --why ', 10))
        self.do(('foo -x ; bar --why | baz -z ed', 20), ('bar --why | baz -z ed', 11))

    def test_symbol_ops__cursor_on_rightmost_command(self):
        self.do(('foo -x & bar --why | baz -z ed', 21), ('baz -z ed', 0))
        self.do(('foo -x | bar --why ; baz -z ed', 22), ('baz -z ed', 1))
        self.do(('foo -x ; bar --why & baz -z ed', 29), ('baz -z ed', 8))
        self.do(('foo -x & bar --why | baz -z ed', 30), ('baz -z ed', 9))

    def test_word_ops__cursor_on_leftmost_command(self):
        self.do(('foo -x or bar --why and baz -z ed', 0), ('foo -x', 0))
        self.do(('foo -x or bar --why and baz -z ed', 7), ('foo -x ', 7))
        self.do(('foo -x or bar --why and baz -z ed', 8), ('foo -x or bar --why', 8))
        self.do(('foo -x or bar --why and baz -z ed', 9), ('foo -x or bar --why', 9))

    def test_word_ops__cursor_on_middle_command(self):
        self.do(('foo -x and bar --why or baz -z ed', 11), ('bar --why', 0))
        self.do(('foo -x and bar --why or baz -z ed', 21), ('bar --why ', 10))
        self.do(('foo -x and bar --why or baz -z ed', 22), ('bar --why or baz -z ed', 11))
        self.do(('foo -x and bar --why or baz -z ed', 23), ('bar --why or baz -z ed', 12))

    def test_word_ops__cursor_on_rightmost_command(self):
        self.do(('foo -x also bar --why or baz -z ed', 25), ('baz -z ed', 0))
        self.do(('foo -x also bar --why or baz -z ed', 33), ('baz -z ed', 8))
        self.do(('foo -x also bar --why or baz -z ed', 34), ('baz -z ed', 9))


class TestCompleter(unittest.TestCase):
    def do(self, input, output):
        c = completion.Completer(*input)
        self.assertEqual(c.complete(), output)

    def test_no_candidates(self):
        with patch('stig.completion.completer.candidates') as cands:
            cands.commands = lambda: Candidates('foo', 'bar', 'baz')
            self.do(('x', 1), ('x', 1))

    def test_partial_match(self):
        with patch('stig.completion.completer.candidates') as cands:
            cands.commands = lambda: Candidates('foo', 'bar', 'baz')
            self.do(('b', 1), ('ba', 2))

    def test_single_match(self):
        with patch('stig.completion.completer.candidates') as cands:
            cands.commands = lambda: Candidates('foo', 'bar', 'baz')
            self.do(('f', 1), ('foo ', 4))

    def test_operators(self):
        with patch('stig.completion.completer.candidates') as cands:
            cands.commands = lambda: Candidates('foo', 'bar', 'baz')
            self.do(('foo ; b', 7), ('foo ; ba', 8))
            self.do(('bar ; f', 7), ('bar ; foo ', 10))

    def test_complete_in_command_chain(self):
        with patch('stig.completion.completer.candidates') as cands:
            cands.commands = lambda: Candidates('foo', 'bar', 'baz')
            self.do(('foo ; b & baz', 7), ('foo ; ba & baz', 8))
            self.do(('bar ; f & baz', 7), ('bar ; foo & baz', 10))

    def test_single_match_in_middle_of_command(self):
        with patch('stig.completion.completer.candidates') as cands:
            cands.commands = lambda: Candidates('foo', 'bar', 'baz')
            self.do(('foo asdf -b c', 1), ('foo asdf -b c', 4))
            self.do(('foo asdf -b c', 2), ('foo asdf -b c', 4))
            self.do(('bar asdf -b c', 1), ('bar asdf -b c', 4))
            self.do(('bar asdf -b c', 2), ('bar asdf -b c', 4))

    def test_partial_match_in_middle_of_command(self):
        with patch('stig.completion.completer.candidates') as cands:
            cands.commands = lambda: Candidates('marmelade', 'bar', 'baz')
            self.do(('marm asdf -b c', 1), ('marmelade asdf -b c', 10))

    def test_no_match_in_middle_of_command(self):
        with patch('stig.completion.completer.candidates') as cands:
            cands.commands = lambda: Candidates('foo', 'bar', 'baz')
            self.do(('xyz asdf -b c', 1), ('xyz asdf -b c', 1))
            self.do(('xyz asdf -b c', 2), ('xyz asdf -b c', 2))
            self.do(('xyz asdf -b c', 3), ('xyz asdf -b c', 3))

    def test_finalize_already_complete_command(self):
        with patch('stig.completion.completer.candidates') as cands:
            cands.commands = lambda: Candidates('foo', 'bar', 'baz')
            self.do(('foo', 3), ('foo ', 4))

    def test_custom_delimiter(self):
        with patch('stig.completion.completer.candidates') as cands:
            cands.commands = lambda: Candidates('foo', 'bar', 'baz', delimiter='/')
            self.do(('foo', 3), ('foo/', 4))
            self.do(('foo/bar', 7), ('foo/bar/', 8))
            self.do(('foo/bar/b', 7), ('foo/bar/ba', 10))


# TODO:
# class Test_complete_arguments(CompletionTestBase):
