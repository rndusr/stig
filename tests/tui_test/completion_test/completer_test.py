from stig.tui import completion

import unittest
from unittest.mock import MagicMock, call


class TestCompleter_update(unittest.TestCase):
    def init(self, get_candidates):
        self.mock_get_candidates = MagicMock(side_effect=get_candidates)
        class MyCompleter(completion.Completer):
            def get_candidates(self_, *args, **kwargs):
                return self.mock_get_candidates(*args, **kwargs)
        self.completer = MyCompleter(operators=('&', 'and', '|', 'or'))

    def update(self, cmdline, curpos, get_candidates_args, exp_candidates, exp_curcand):
        self.completer.update(cmdline, curpos)
        if get_candidates_args is None:
            self.assertEqual(self.mock_get_candidates.called, False)
        else:
            self.assertEqual(self.mock_get_candidates.call_args, get_candidates_args)
        self.mock_get_candidates.reset_mock()

        print(self.completer.candidates)
        print(exp_candidates)
        self.assertEqual(self.completer.candidates, exp_candidates)
        self.assertEqual(self.completer.candidates.current_index, exp_curcand)

    def test_empty_command_line(self):
        def get_candidates(argv, focused, curpos):
            return ('foo', 'bar', 'baz')
        self.init(get_candidates)
        self.update('', 0, call([''], 0, 0), ('', 'bar', 'baz', 'foo'), 0)

    def test_no_candidates(self):
        def get_candidates(argv, focused, curpos):
            return ()
        self.init(get_candidates)
        self.update('something', 9, call(['something'], 0, 9), (), None)
        self.update('anything', 5, call(['anything'], 0, 5), (), None)
        self.update('', 0, call([''], 0, 0), (), None)

    def test_no_matches(self):
        def get_candidates(argv, focused, curpos):
            return ('foo', 'bar', 'baz')
        self.init(get_candidates)
        self.update('afoo', 1, call(['afoo'], 0, 1), (), None)
        self.update('abar', 2, call(['abar'], 0, 2), (), None)
        self.update('abaz', 3, call(['abaz'], 0, 3), (), None)
        self.update('abaz', 4, call(['abaz'], 0, 4), (), None)

    def test_only_characters_before_cursor_are_relevant(self):
        def get_candidates(argv, focused, curpos):
            if focused == 0:       return ('foo', 'bar', 'baz')
            elif argv[0] == 'foo': return ('-10', '-11', '-110')
            elif argv[0] == 'bar': return ('-20', '-21', '-210')
            elif argv[0] == 'baz': return ('-30', '-31', '-310')
            else:                  return ()
        self.init(get_candidates)
        self.update('foo -1', 0, call(['foo', '-1'], 0, 0), ('bar', 'baz', 'foo'), 0)
        self.update('foo -1', 1, call(['foo', '-1'], 0, 1), ('foo',), 0)
        self.update('boo -1', 1, call(['boo', '-1'], 0, 1), ('boo', 'bar', 'baz'), 0)
        self.update('foo -1', 6, call(['foo', '-1'], 1, 2), ('-1', '-10', '-11', '-110'), 0)
        self.update('foo -11', 7, call(['foo', '-11'], 1, 3), ('-11', '-110'), 0)
        self.update('foo -21', 7, call(['foo', '-21'], 1, 3), (), None)

    def test_multiple_commands(self):
        def get_candidates(argv, focused, curpos):
            if focused == 0:       return ('foo', 'bar', 'baz')
            elif argv[0] == 'foo': return ('-10', '-11', '-110')
            elif argv[0] == 'bar': return ('-20', '-21', '-210')
            elif argv[0] == 'baz': return ('-30', '-31', '-310')
            else:                  return ()
        cmdline = 'foo -10 & bar - | baz -31'
        self.init(get_candidates)
        self.update(cmdline,  6, call(['foo', '-10'], 1, 2), ('-10', '-11', '-110'), 0)
        self.update(cmdline,  7, call(['foo', '-10'], 1, 3), ('-10',), 0)
        self.update(cmdline,  8, None, (), None)
        self.update(cmdline,  9, None, (), None)
        self.update(cmdline, 10, call(['bar', '-'], 0, 0), ('bar', 'baz', 'foo'), 0)
        self.update(cmdline, 11, call(['bar', '-'], 0, 1), ('bar', 'baz'), 0)
        self.update(cmdline, 12, call(['bar', '-'], 0, 2), ('bar', 'baz'), 0)
        self.update(cmdline, 13, call(['bar', '-'], 0, 3), ('bar',), 0)
        self.update(cmdline, 14, call(['bar', '-'], 1, 0), ('-', '-20', '-21', '-210'), 0)
        self.update(cmdline, 15, call(['bar', '-'], 1, 1), ('-', '-20', '-21', '-210'), 0)
        self.update(cmdline, 16, None, (), None)
        self.update(cmdline, 17, None, (), None)
        self.update(cmdline, 18, call(['baz', '-31'], 0, 0), ('bar', 'baz', 'foo'), 0)
        self.update(cmdline, 19, call(['baz', '-31'], 0, 1), ('bar', 'baz'), 0)
        self.update(cmdline, 20, call(['baz', '-31'], 0, 2), ('bar', 'baz'), 0)
        self.update(cmdline, 21, call(['baz', '-31'], 0, 3), ('baz',), 0)
        self.update(cmdline, 22, call(['baz', '-31'], 1, 0), ('-30', '-31', '-310'), 0)
        self.update(cmdline, 23, call(['baz', '-31'], 1, 1), ('-30', '-31', '-310'), 0)
        self.update(cmdline, 24, call(['baz', '-31'], 1, 2), ('-30', '-31', '-310'), 0)
        self.update(cmdline, 25, call(['baz', '-31'], 1, 3), ('-31', '-310'), 0)

    def test_argument_without_closing_quote(self):
        def get_candidates(argv, focused, curpos):
            return ('a \\', 'a string', 'another string')
        self.init(get_candidates)
        self.update('foo "', 5, call(['foo', ''], 1, 0), ('', 'a \\', 'a string', 'another string'), 0)
        self.update('foo "a', 6, call(['foo', 'a'], 1, 1), ('a', 'a \\', 'a string', 'another string'), 0)
        self.update('foo "a ', 7, call(['foo', 'a '], 1, 2), ('a ', 'a \\', 'a string'), 0)
        self.update('foo "an', 7, call(['foo', 'an'], 1, 2), ('an', 'another string',), 0)
        self.update(r"""foo "a \\" 'a s""", 15, call(['foo', 'a \\', 'a s'], 2, 3), ('a s', 'a string',), 0)


class TestCompleter_complete_next_prev(unittest.TestCase):
    def init(self, cmdline, curpos, Completer):
        self.completer = Completer(operators=('&', 'and', '|', 'or'))
        self.completer.update(cmdline, curpos)

    def do_next(self, exp_cmdline, exp_curpos):
        self.assertEqual(self.completer.complete_next(), (exp_cmdline, exp_curpos))

    def do_prev(self, exp_cmdline, exp_curpos):
        self.assertEqual(self.completer.complete_prev(), (exp_cmdline, exp_curpos))

    def test_empty_command_line(self):
        class TestCompleter(completion.Completer):
            def get_candidates(self, argv, focused, curpos):
                return ('foo', 'ba', 'bazz')
        self.init('', 0, TestCompleter)
        for _ in range(3):
            self.do_next('ba', 2)
            self.do_next('bazz', 4)
            self.do_next('foo', 3)
            self.do_next('', 0)
        for _ in range(3):
            self.do_prev('foo', 3)
            self.do_prev('bazz', 4)
            self.do_prev('ba', 2)
            self.do_prev('', 0)

    def test_complete_at_end_of_command_line(self):
        class TestCompleter(completion.Completer):
            def get_candidates(self, argv, focused, curpos):
                return ('-a', '-be', '-cee')
        self.init('foo ', 4, TestCompleter)
        for _ in range(3):
            self.do_next('foo -a', 6)
            self.do_next('foo -be', 7)
            self.do_next('foo -cee', 8)
            self.do_next('foo ', 4)
        for _ in range(3):
            self.do_prev('foo -cee', 8)
            self.do_prev('foo -be', 7)
            self.do_prev('foo -a', 6)
            self.do_prev('foo ', 4)

    def test_complete_in_middle_of_command_line(self):
        class TestCompleter(completion.Completer):
            def get_candidates(self, argv, focused, curpos):
                return ('-a', '-be', '-cee')
        self.init('foo     &  bar', 5, TestCompleter)
        for _ in range(3):
            self.do_next('foo  -a   &  bar', 7)
            self.do_next('foo  -be   &  bar', 8)
            self.do_next('foo  -cee   &  bar', 9)
            self.do_next('foo     &  bar', 5)
        for _ in range(3):
            self.do_prev('foo  -cee   &  bar', 9)
            self.do_prev('foo  -be   &  bar', 8)
            self.do_prev('foo  -a   &  bar', 7)
            self.do_prev('foo     &  bar', 5)

    def test_complete_at_beginning_of_command_line(self):
        class TestCompleter(completion.Completer):
            def get_candidates(self, argv, focused, curpos):
                return ('foo', 'ba', 'bazz')
        self.init('  -a', 0, TestCompleter)
        for _ in range(3):
            self.do_next('ba  -a', 2)
            self.do_next('bazz  -a', 4)
            self.do_next('foo  -a', 3)
            self.do_next('  -a', 0)
        for _ in range(3):
            self.do_prev('foo  -a', 3)
            self.do_prev('bazz  -a', 4)
            self.do_prev('ba  -a', 2)
            self.do_prev('  -a', 0)

    def test_complete_at_beginning_of_command_line_with_leading_space(self):
        class TestCompleter(completion.Completer):
            def get_candidates(self, argv, focused, curpos):
                return ('foo', 'ba', 'bazz')
        self.init('    -a', 2, TestCompleter)
        for _ in range(3):
            self.do_next('  ba  -a', 4)
            self.do_next('  bazz  -a', 6)
            self.do_next('  foo  -a', 5)
            self.do_next('    -a', 2)
        for _ in range(3):
            self.do_prev('  foo  -a', 5)
            self.do_prev('  bazz  -a', 6)
            self.do_prev('  ba  -a', 4)
            self.do_prev('    -a', 2)

    def test_follow_user_style_with_special_characters(self):
        class TestCompleter(completion.Completer):
            def get_candidates(self, argv, focused, curpos):
                return ('foo or bar ',)
        self.init("'foo ", 5, TestCompleter)
        self.do_next("'foo or bar '", 13)
        self.init(r'foo\ ', 5, TestCompleter)
        self.do_next(r'foo\ or\ bar\ ', 14)

    def test_non_space_delimiter(self):
        class TestCompleter(completion.Completer):
            def get_candidates(self, argv, focused, curpos):
                return ('b ', r'b\r', "f'oo"), '/'
        self.init(r"ls 'path to'/f\' -x", 16, TestCompleter)
        self.do_next(r"ls 'path to'/f\'oo -x", 18)
        self.init(r"ls 'path to'/b -x", 14, TestCompleter)
        self.do_next(r"ls 'path to'/'b ' -x", 17)
        self.do_next(r"ls 'path to'/'b\r' -x", 18)

    def test_non_space_delimiter_with_no_common_prefix(self):
        class TestCompleter(completion.Completer):
            def get_candidates(self, argv, focused, curpos):
                return ('b ', r'b\r', "f'oo"), '/'
        self.init(r"ls 'path to'/ -x", 13, TestCompleter)
        self.do_next(r"ls 'path to'/'b ' -x", 17)

    def test_non_space_delimiter_with_cursor_on_previous_candidate(self):
        class TestCompleter(completion.Completer):
            def get_candidates(self, argv, focused, curpos):
                return ('b ', r'b\r', "f'oo"), '/'
        self.init(r'''ls 'path to'/f/abc -x''', 14, TestCompleter)
        self.do_next(r'''ls 'path to'/"f'oo"/abc -x''', 19)
        self.init(r'''ls 'path to'/f/abc/def/ -x''', 14, TestCompleter)
        self.do_next(r'''ls 'path to'/"f'oo"/abc/def/ -x''', 19)

    def test_non_space_delimiter_with_cursor_on_first_part(self):
        class TestCompleter(completion.Completer):
            def get_candidates(self, argv, focused, curpos):
                return ('b ', r'b\r', "f'oo"), '/'
        self.init(r'''ls abc/def/ghi -x''', 3, TestCompleter)
        self.do_next(r'''ls 'b '/def/ghi -x''', 7)
        self.do_next(r'''ls 'b\r'/def/ghi -x''', 8)
        self.do_next(r'''ls "f'oo"/def/ghi -x''', 9)
