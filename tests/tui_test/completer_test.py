from stig.tui.completer import Completer
from stig.completion import Categories, Candidates, SingleCandidate

import asynctest
import unittest
from unittest.mock import MagicMock, call


def tupleize(categories):
    return tuple(tuple(sorted(cands)) for cands in categories)


class TestCompleter_get_candidates_wrapper(asynctest.TestCase):
    async def do(self, get_cands, exp_cats):
        completer = Completer(get_cands)
        result = await completer._get_candidates_wrapper(('',))
        self.assertIsInstance(result, Categories)
        for c in result:
            self.assertIsInstance(c, Candidates)
        self.assertIsInstance(result[0], SingleCandidate)
        self.assertEqual(tupleize(result[1:]), tupleize(exp_cats))

    async def test_get_candidates_returns_None(self):
        def get_cands(args): pass
        await self.do(get_cands, ())

        async def get_cands(args): pass
        await self.do(get_cands, ())

    async def test_get_candidates_returns_single_Candidates(self):
        test_value = Candidates(('fooo', 'barrr', 'bazzz'))
        def get_cands(args):
            return test_value
        await self.do(get_cands, (test_value,))

        async def get_cands(args):
            return test_value
        await self.do(get_cands, (test_value,))

    async def test_get_candidates_returns_multiple_Candidates(self):
        test_value = (Candidates(('fooo', 'barrr', 'bazzz')),
                      Candidates(('a', 'b', 'c')))
        def get_cands(args):
            return test_value
        await self.do(get_cands, test_value)

        async def get_cands(args):
            return test_value
        await self.do(get_cands, test_value)

    async def test_get_candidates_returns_nested_iterables_and_iterators_of_Candidates(self):
        cands = Candidates(('a', 'b', 'c'))
        cands_iter = iter((cands, Candidates(('d', 'e', 'f'))))
        def get_cands(args):
            yield from (cands_iter, Candidates(('g', 'h', 'i')))
        await self.do(get_cands, (('a', 'b', 'c'), ('d', 'e', 'f'), ('g', 'h', 'i')))

    async def test_get_candidates_returns_iterator_that_contains_None(self):
        def get_cands(args):
            for cands in (Candidates(('foo', 'bar', 'baz')),
                          None,
                          Candidates(('a', 'b', 'c'))):
                yield cands
        await self.do(get_cands, (('bar', 'baz', 'foo'),
                                  ('a', 'b', 'c')))


class TestCompleter_current_user_input(asynctest.TestCase):
    async def do(self, categories, cmdline, curpos, exp_cur_user_input):
        completer = Completer(lambda *args, **kwargs: categories)
        await completer.update(cmdline, curpos)
        self.assertEqual(completer.current_user_input, exp_cur_user_input)

    async def test_no_candidates(self):
        await self.do((), 'abc', 1, 'a')
        await self.do((), 'abc', 2, 'ab')
        await self.do((), 'abc', 3, 'abc')

    async def test_no_matching_candidates(self):
        cats = (Candidates(('foo', 'bar', 'baz')),)
        await self.do(cats, 'abc', 1, 'a')
        await self.do(cats, 'abc', 2, 'ab')
        await self.do(cats, 'abc', 3, 'abc')

    async def test_curpos_args_with_single_category(self):
        cats = (Candidates(('foo', 'bar', 'baz'), curarg_seps=('/',)),)
        await self.do(cats, 'foo/bar/', 3, 'foo')
        await self.do(cats, 'foo/bar/', 4, '')
        await self.do(cats, 'foo/bar/', 5, 'b')
        await self.do(cats, 'foo/bar/', 6, 'ba')
        await self.do(cats, 'foo/bar/', 7, 'bar')
        await self.do(cats, 'foo/bar/abc', 11, 'foo/bar/abc')

    async def test_curpos_args_with_multiple_categories_with_same_curarg_seps(self):
        cats = (Candidates(('foo', 'bar'), curarg_seps=('/',)),
                Candidates(('foo', 'bang'), curarg_seps=('/',)))
        await self.do(cats, 'foo/bar', 3, 'foo')
        await self.do(cats, 'foo/bar', 4, '')
        await self.do(cats, 'foo/bar', 5, 'b')
        await self.do(cats, 'foo/bar', 6, 'ba')
        await self.do(cats, 'foo/bar', 7, 'bar')
        await self.do(cats, 'foo/ban', 7, 'ban')
        await self.do(cats, 'foo/bang/abc', 12, 'foo/bang/abc')

    async def test_curpos_args_with_multiple_categories_with_different_curarg_seps(self):
        cats = (Candidates(('foo', 'bar'), curarg_seps=('/',)),
                Candidates(('foo', 'bang'), curarg_seps=('.',)))
        await self.do(cats, 'foo/ba', 3, 'foo')
        await self.do(cats, 'foo/ba', 4, '')
        await self.do(cats, 'foo/ba', 5, 'b')
        await self.do(cats, 'foo/ba', 6, 'ba')
        await self.do(cats, 'foo/bang', 8, 'foo/bang')
        await self.do(cats, 'foo.bang', 8, 'bang')


class TestCompleter_update(asynctest.TestCase):
    def init(self, get_cands):
        self.mock_get_cands = MagicMock(side_effect=get_cands)
        def get_cands(args):
            return self.mock_get_cands(args)
        self.completer = Completer(get_cands, operators=('&', 'and', '|', 'or'))

    async def update(self, cmdline, curpos, exp_get_cands_args,
                     exp_curarg_index, exp_curarg_curpos, exp_cands, exp_curcand):
        should_be_None = await self.completer.update(cmdline, curpos)
        self.assertTrue(should_be_None is None)

        if exp_get_cands_args is None:
            self.assertEqual(self.mock_get_cands.called, False)
        else:
            self.assertEqual(self.mock_get_cands.call_args, exp_get_cands_args)
            args = self.mock_get_cands.call_args[0][0]
            self.assertEqual(args.curarg_index, exp_curarg_index)
            self.assertEqual(args.curarg_curpos, exp_curarg_curpos)
            self.assertEqual(args.curarg.curpos, exp_curarg_curpos)

        self.mock_get_cands.reset_mock()
        self.assertEqual(tupleize(self.completer.categories), tupleize(exp_cands))
        if exp_curcand is None:
            self.assertEqual(self.completer.categories.current_index, None)
            self.assertEqual(self.completer.categories.current, None)
        else:
            self.assertEqual(self.completer.categories.current_index, exp_curcand)

    async def test_empty_command_line(self):
        def get_cands(args):
            return Candidates(('foo', 'bar', 'baz'))
        self.init(get_cands)
        await self.update('', 0, call(('',)), 0, 0, (('',), ('bar', 'baz', 'foo')), 0)

    async def test_no_candidates(self):
        def get_cands(args):
            return ()
        self.init(get_cands)
        await self.update('something', 9, call(('something',)), 0, 9, (('something',),), 0)
        await self.update('anything', 5, call(('anything',)), 0, 5, (('anyth',),), 0)
        await self.update('', 0, call(('',)), 0, 0, (('',),), 0)

    async def test_no_matches(self):
        def get_cands(args):
            return Candidates(('foo', 'bar', 'baz'))
        self.init(get_cands)
        await self.update('xxxx', 1, call(('xxxx',)), 0, 1, (('x',),), 0)
        await self.update('xxxx', 2, call(('xxxx',)), 0, 2, (('xx',),), 0)
        await self.update('xxxx', 3, call(('xxxx',)), 0, 3, (('xxx',),), 0)
        await self.update('xxxx', 4, call(('xxxx',)), 0, 4, (('xxxx',),), 0)

    async def test_only_characters_before_cursor_are_relevant(self):
        def get_cands(args):
            if args.curarg_index == 0: return Candidates(('foo', 'bar', 'baz'))
            elif args[0] == 'foo': return Candidates(('-10', '-11', '-110'))
            elif args[0] == 'bar': return Candidates(('-20', '-21', '-210'))
            elif args[0] == 'baz': return Candidates(('-30', '-31', '-310'))
            else: return Candidates(())
        self.init(get_cands)
        await self.update('foo -1', 0, call(('foo', '-1',)), 0, 0, (('',), ('bar', 'baz', 'foo')), 0)
        await self.update('foo -1', 1, call(('foo', '-1',)), 0, 1, (('f',), ('foo',)), 0)
        await self.update('boo -1', 1, call(('boo', '-1',)), 0, 1, (('b',), ('bar', 'baz')), 0)
        await self.update('foo -1', 6, call(('foo', '-1',)), 1, 2, (('-1',), ('-10', '-11', '-110')), 0)
        await self.update('foo -11', 7, call(('foo', '-11',)), 1, 3, (('-11',), ('-11', '-110')), 0)
        await self.update('foo -21', 7, call(('foo', '-21',)), 1, 3, (('-21',),), 0)

    async def test_multiple_commands(self):
        def get_cands(args):
            if args.curarg_index == 0: return Candidates(('foo', 'bar', 'baz'))
            elif args[0] == 'foo': return Candidates(('-10', '-11', '-110'))
            elif args[0] == 'bar': return Candidates(('-20', '-21', '-210'))
            elif args[0] == 'baz': return Candidates(('-30', '-31', '-310'))
            else: return Candidates()
        cmdline = 'foo -10 & bar - | baz -31'
        self.init(get_cands)
        await self.update(cmdline,  6, call(('foo', '-10',)), 1, 2, (('-1',), ('-10', '-11', '-110')), 0)
        await self.update(cmdline,  7, call(('foo', '-10',)), 1, 3, (('-10',), ('-10',)), 0)
        await self.update(cmdline,  8, None, None, None, (), None)
        await self.update(cmdline,  9, None, None, None, (), None)
        await self.update(cmdline, 10, call(('bar', '-',)), 0, 0, (('',), ('bar', 'baz', 'foo')), 0)
        await self.update(cmdline, 11, call(('bar', '-',)), 0, 1, (('b',), ('bar', 'baz')), 0)
        await self.update(cmdline, 12, call(('bar', '-',)), 0, 2, (('ba',), ('bar', 'baz')), 0)
        await self.update(cmdline, 13, call(('bar', '-',)), 0, 3, (('bar',), ('bar',)), 0)
        await self.update(cmdline, 14, call(('bar', '-',)), 1, 0, (('',), ('-20', '-21', '-210')), 0)
        await self.update(cmdline, 15, call(('bar', '-',)), 1, 1, (('-',), ('-20', '-21', '-210')), 0)
        await self.update(cmdline, 16, None, None, None, (), None)
        await self.update(cmdline, 17, None, None, None, (), None)
        await self.update(cmdline, 18, call(('baz', '-31',)), 0, 0, (('',), ('bar', 'baz', 'foo')), 0)
        await self.update(cmdline, 19, call(('baz', '-31',)), 0, 1, (('b',), ('bar', 'baz')), 0)
        await self.update(cmdline, 20, call(('baz', '-31',)), 0, 2, (('ba',), ('bar', 'baz')), 0)
        await self.update(cmdline, 21, call(('baz', '-31',)), 0, 3, (('baz',), ('baz',)), 0)
        await self.update(cmdline, 22, call(('baz', '-31',)), 1, 0, (('',), ('-30', '-31', '-310')), 0)
        await self.update(cmdline, 23, call(('baz', '-31',)), 1, 1, (('-',), ('-30', '-31', '-310')), 0)
        await self.update(cmdline, 24, call(('baz', '-31',)), 1, 2, (('-3',), ('-30', '-31', '-310')), 0)
        await self.update(cmdline, 25, call(('baz', '-31',)), 1, 3, (('-31',), ('-31', '-310')), 0)

    async def test_argument_without_closing_quote(self):
        def get_cands(args):
            return Candidates(('a \\', 'a string', 'another string'))
        self.init(get_cands)
        await self.update('foo "', 5, call(('foo', '',)), 1, 0, (('',), ('a \\', 'a string', 'another string')), 0)
        await self.update('foo "a', 6, call(('foo', 'a',)), 1, 1, (('a',), ('a \\', 'a string', 'another string')), 0)
        await self.update('foo "a ', 7, call(('foo', 'a ',)), 1, 2, (('a ',), ('a \\', 'a string')), 0)
        await self.update('foo "an', 7, call(('foo', 'an',)), 1, 2, (('an',), ('another string',)), 0)
        await self.update(r"""foo "a \\" 'a s""", 15, call(('foo', 'a \\', 'a s',)), 2, 3, (('a s',), ('a string',)), 0)


class TestCompleter_complete_next_prev(asynctest.TestCase):
    async def init(self, cmdline, curpos, get_cands):
        self.completer = Completer(get_cands, operators=('&', 'and', '|', 'or'))
        await self.completer.update(cmdline, curpos)

    def do_next(self, exp_cmdline, exp_curpos):
        self.assertEqual(self.completer.complete_next(), (exp_cmdline, exp_curpos))

    def do_prev(self, exp_cmdline, exp_curpos):
        self.assertEqual(self.completer.complete_prev(), (exp_cmdline, exp_curpos))

    async def test_empty_command_line(self):
        def get_cands(args):
            return Candidates(('foo', 'ba', 'bazz'))
        await self.init('', 0, get_cands)
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

    async def test_complete_at_end_of_command_line(self):
        def get_cands(args):
            return Candidates(('-a', '-be', '-cee'))
        await self.init('foo ', 4, get_cands)
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

    async def test_complete_in_middle_of_command_line(self):
        def get_cands(args):
            return Candidates(('-a', '-be', '-cee'))
        await self.init('foo     &  bar', 5, get_cands)
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

    async def test_complete_at_beginning_of_command_line(self):
        def get_cands(args):
            return Candidates(('foo', 'ba', 'bazz'))
        await self.init('  -a', 0, get_cands)
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

    async def test_complete_at_beginning_of_command_line_with_leading_space(self):
        def get_cands(args):
            return Candidates(('foo', 'ba', 'bazz'))
        await self.init('    -a', 2, get_cands)
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

    async def test_follow_user_style_with_special_characters(self):
        def get_cands(args):
            return Candidates(('foo or bar ',))
        await self.init("'foo ", 5, get_cands)
        self.do_next('"foo or bar "', 13)
        await self.init(r'foo\ ', 5, get_cands)
        self.do_next(r'foo\ or\ bar\ ', 14)

    async def test_non_space_delimiter(self):
        def get_cands(args):
            return Candidates(('b ', r'b\r', 'f"oo'), curarg_seps=('/',))
        await self.init(r'ls "path to"/f\" -x', 16, get_cands)
        self.do_next(r'ls "path to"/f\"oo -x', 18)
        await self.init(r'ls "path to"/b -x', 14, get_cands)
        self.do_next(r'ls "path to"/"b " -x', 17)
        self.do_next(r'ls "path to"/"b\r" -x', 18)

    async def test_non_space_delimiter_with_no_common_prefix(self):
        def get_cands(args):
            return Candidates(('b ', r'b\r', 'f"oo'), curarg_seps=('/',))
        await self.init(r'ls "path to"/ -x', 13, get_cands)
        self.do_next(r'ls "path to"/"b " -x', 17)

    async def test_non_space_delimiter_with_cursor_on_previous_candidate(self):
        def get_cands(args):
            return Candidates(('b ', r'b\r', 'f"oo'), curarg_seps=('/',))
        await self.init(r'''ls "path to"/f/abc -x''', 14, get_cands)
        self.do_next(r'''ls "path to"/'f"oo'/abc -x''', 19)
        await self.init(r'''ls "path to"/f/abc/def/ -x''', 14, get_cands)
        self.do_next(r'''ls "path to"/'f"oo'/abc/def/ -x''', 19)

    async def test_non_space_delimiter_with_cursor_on_first_part(self):
        def get_cands(args):
            return Candidates(('b ', r'b\r', 'f"oo'), curarg_seps=('/',))
        await self.init(r'''ls abc/def/ghi -x''', 3, get_cands)
        self.do_next(r'''ls "b "/def/ghi -x''', 7)
        self.do_next(r'''ls "b\r"/def/ghi -x''', 8)
        self.do_next(r'''ls 'f"oo'/def/ghi -x''', 9)
