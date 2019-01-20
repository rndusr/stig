from stig.completion import Categories, Candidates, SingleCandidate

import unittest

class TestCandidates(unittest.TestCase):
    def assert_focus(self, cands, exp_current_index, exp_current):
        self.assertEqual(cands.current_index, exp_current_index)
        self.assertEqual(cands.current, exp_current)

    def test_all_candidates_are_strings(self):
        cands = Candidates(('foo', 5, (1, 2, 'three')))
        self.assertTrue(all(isinstance(cand, str) for cand in cands))

    def test_candidates_are_sorted_case_insensitively(self):
        self.assertEqual(tuple(Candidates(('B', 'a'))), ('a', 'B'))

    def test_candidates_are_deduplicated(self):
        self.assertEqual(tuple(Candidates(('a', 'a', 'b'))), ('a', 'b'))

    def test_no_candidates(self):
        self.assertEqual(Candidates(()).current_index, None)
        cands = Candidates(('a', 'b', 'c'))
        cands.reduce('x')
        self.assert_focus(cands, None, None)

    def test_current_and_current_index(self):
        self.assert_focus(Candidates(), None, None)
        cands = Candidates(('bar', 'baz', 'foo'))
        cands.current_index = -1
        self.assert_focus(cands, 0, 'bar')
        cands.current_index = 0
        self.assert_focus(cands, 0, 'bar')
        cands.current_index = 1
        self.assert_focus(cands, 1, 'baz')
        cands.current_index = 2
        self.assert_focus(cands, 2, 'foo')
        cands.current_index = 3
        self.assert_focus(cands, 2, 'foo')

    def test_current_and_current_index_when_reduced(self):
        self.assert_focus(Candidates(), None, None)
        cands = Candidates(('bar', 'baz', 'foo'))
        cands.reduce(r'^f')
        cands.current_index = -1
        self.assert_focus(cands, 0, 'foo')
        cands.current_index = 0
        self.assert_focus(cands, 0, 'foo')
        cands.current_index = 1
        self.assert_focus(cands, 0, 'foo')

    def test_if_possible_keep_selected_candidate_when_reduced(self):
        cands = Candidates(('abc', 'cde', 'efg'))
        cands.current_index = 1
        self.assert_focus(cands, 1, 'cde')
        cands.reduce(r'e')
        self.assert_focus(cands, 0, 'cde')
        cands.reduce(r'f')
        self.assert_focus(cands, 0, 'efg')

    def test_next(self):
        cands = Candidates(('bar', 'baz', 'foo'))
        for _ in range(3):
            self.assert_focus(cands, 0, 'bar')
            cands.next()
            self.assert_focus(cands, 1, 'baz')
            cands.next()
            self.assert_focus(cands, 2, 'foo')
            cands.next()
            self.assert_focus(cands, 0, 'bar')

    def test_prev(self):
        cands = Candidates(('bar', 'baz', 'foo'))
        for _ in range(3):
            self.assert_focus(cands, 0, 'bar')
            cands.prev()
            self.assert_focus(cands, 2, 'foo')
            cands.prev()
            self.assert_focus(cands, 1, 'baz')
            cands.prev()
            self.assert_focus(cands, 0, 'bar')

    def test_reduce(self):
        cands = Candidates(('bar', 'baz', 'foo'))
        self.assert_focus(cands, 0, 'bar')
        cands.reduce(r'^b')
        self.assertEqual(tuple(cands), ('bar', 'baz'))
        self.assert_focus(cands, 0, 'bar')
        cands.next()
        self.assert_focus(cands, 1, 'baz')
        cands.next()
        self.assert_focus(cands, 0, 'bar')


class TestSingleCandidate(unittest.TestCase):
    def test_empty_string_is_included(self):
        self.assertEqual(tuple(SingleCandidate('')), ('',))


class TestCategories(unittest.TestCase):
    def assert_focus(self, cats, current_index, cand):
        self.assertEqual(cats.current_index, current_index)
        self.assertEqual(cats.current.current, cand)

    def assert_rotation(self, cats, move, *states):
        move_method = getattr(cats, move)
        for _ in range(3):
            for state in states:
                self.assert_focus(*state)
                move_method()

    def reduce(self, cats, pattern):
        for cands in cats.all:
            cands.reduce(pattern)

    def test_len_with_some_empty_candidate_lists(self):
        cats = Categories(Candidates(()),
                          Candidates(('bar', 'baz')),
                          Candidates(('foo',)),
                          Candidates(()))
        self.assertEqual(len(cats), 2)

    def test_len_with_some_reduced_candidate_lists(self):
        cats = Categories(Candidates(('boo', 'foo')),
                          Candidates(('bar', 'far')),
                          Candidates(('faz', 'naz')))
        self.assertEqual(len(cats), 3)
        self.reduce(cats, '^x')
        self.assertEqual(len(cats), 0)
        self.reduce(cats, '^f')
        self.assertEqual(len(cats), 3)
        self.reduce(cats, '^b')
        self.assertEqual(len(cats), 2)

    def test_next_with_some_empty_candidate_lists(self):
        cats = Categories(Candidates(()),
                          Candidates(('bar', 'baz')),
                          Candidates(('foo',)),
                          Candidates(()))
        self.assertEqual(len(cats), 2)
        self.assert_rotation(cats, 'next',
                             (cats, 0, 'bar'),
                             (cats, 0, 'baz'),
                             (cats, 1, 'foo'))

    def test_prev_with_some_empty_candidate_lists(self):
        cats = Categories(Candidates(('bar', 'baz')),
                          Candidates(()),
                          Candidates(()),
                          Candidates(('foo',)))
        self.assertEqual(len(cats), 2)
        self.assert_rotation(cats, 'prev',
                             (cats, 0, 'bar'),
                             (cats, 1, 'foo'),
                             (cats, 0, 'baz'))

    def test_next_with_some_lists_reduced_to_nothing(self):
        cats = Categories(Candidates(('boo', 'foo')),
                          Candidates(('bar', 'far')),
                          Candidates(('faz', 'naz')))

        self.reduce(cats, '^b')
        self.assert_rotation(cats, 'next',
                             (cats, 0, 'boo'),
                             (cats, 1, 'bar'))

    def test_prev_with_some_lists_reduced_to_nothing(self):
        cats = Categories(Candidates(('boo', 'foo')),
                          Candidates(('bar', 'far')),
                          Candidates(('faz', 'naz')))
        self.reduce(cats, 'a')
        self.assert_rotation(cats, 'prev',
                             (cats, 0, 'bar'),
                             (cats, 1, 'naz'),
                             (cats, 1, 'faz'),
                             (cats, 0, 'far'))

    def test_no_lists(self):
        cats = Categories()
        self.reduce(cats, 'x')
        def assert_state():
            self.assertEqual(len(cats), 0)
            self.assertEqual(cats.current_index, None)
            self.assertEqual(cats.current, None)
        cats.next()
        assert_state()
        cats.prev()
        assert_state()

    def test_all_lists_are_reduced_to_nothing(self):
        cats = Categories(Candidates(('boo', 'foo')),
                          Candidates(('bar', 'far')),
                          Candidates(('faz', 'naz')))
        self.reduce(cats, 'x')
        def assert_state():
            self.assertEqual(len(cats), 0)
            self.assertEqual(cats.current_index, None)
            self.assertEqual(cats.current, None)
        cats.next()
        assert_state()
        cats.prev()
        assert_state()
