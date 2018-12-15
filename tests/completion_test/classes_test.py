from stig.completion import Candidates, Candidate

import unittest


class TestCandidates(unittest.TestCase):
    def test_all_candidates_are_Candidate_objects(self):
        cands = Candidates('foo', 'bar', 'baz')
        self.assertTrue(all(isinstance(cand, Candidate) for cand in cands))

    def test_current_index(self):
        self.assertEqual(Candidates().current, None)
        self.assertEqual(Candidates().current_index, None)
        with self.assertRaises(IndexError):
            Candidates('foo', 'bar', 'baz', current_index=-1)
        self.assertEqual(Candidates('foo', 'bar', 'baz', current_index=0).current, 'foo')
        self.assertEqual(Candidates('foo', 'bar', 'baz', current_index=1).current, 'bar')
        self.assertEqual(Candidates('foo', 'bar', 'baz', current_index=2).current, 'baz')
        with self.assertRaises(IndexError):
            Candidates('foo', 'bar', 'baz', current_index=3)

    def test_next(self):
        cands = Candidates('foo', 'bar', 'baz')
        self.assertEqual(cands.current, 'foo')
        self.assertEqual(cands.current_index, 0)
        self.assertEqual(cands.next(), 1)
        self.assertEqual(cands.current, 'bar')
        self.assertEqual(cands.current_index, 1)
        self.assertEqual(cands.next(), 2)
        self.assertEqual(cands.current, 'baz')
        self.assertEqual(cands.current_index, 2)
        self.assertEqual(cands.next(), 0)
        self.assertEqual(cands.current, 'foo')
        self.assertEqual(cands.current_index, 0)

    def test_prev(self):
        cands = Candidates('foo', 'bar', 'baz')
        self.assertEqual(cands.current, 'foo')
        self.assertEqual(cands.current_index, 0)
        self.assertEqual(cands.prev(), 2)
        self.assertEqual(cands.current, 'baz')
        self.assertEqual(cands.current_index, 2)
        self.assertEqual(cands.prev(), 1)
        self.assertEqual(cands.current, 'bar')
        self.assertEqual(cands.current_index, 1)
        self.assertEqual(cands.prev(), 0)
        self.assertEqual(cands.current, 'foo')
        self.assertEqual(cands.current_index, 0)
        self.assertEqual(cands.prev(), 2)
        self.assertEqual(cands.current, 'baz')
        self.assertEqual(cands.current_index, 2)

    def test_reduce(self):
        cands = Candidates('foo', 'bar', 'baz')
        self.assertEqual(cands.reduce('f'), Candidates('foo',))
        self.assertEqual(cands.reduce('b'), Candidates('bar', 'baz'))

    def test_reduce_preserves_separator(self):
        cands = Candidates('foo', 'bar', 'baz', separators=(':',))
        self.assertEqual(cands.reduce('f').separators, (':',))
        cands.separators = ('/',)
        self.assertEqual(cands.reduce('f').separators, ('/',))

    def test_reduce_preserves_current_index_if_possible(self):
        cands = Candidates('foo', 'bar', 'baz', 'far', separators=(':',))
        def do(prefix, old_index, old_current, exp_index, exp_current):
            cands.current_index = old_index
            self.assertEqual((cands.current_index, cands.current), (old_index, Candidate(old_current)))
            self.assertEqual(cands.reduce(prefix).current_index, exp_index)
            self.assertEqual(cands.reduce(prefix).current, Candidate(exp_current))
        do('f', 0, 'foo', 0, 'foo')
        do('f', 1, 'bar', 0, 'foo')
        do('f', 2, 'baz', 0, 'foo')
        do('f', 3, 'far', 1, 'far')
        do('b', 0, 'foo', 0, 'bar')
        do('b', 1, 'bar', 0, 'bar')
        do('b', 2, 'baz', 1, 'baz')
        do('b', 3, 'far', 0, 'bar')

    def test_reduce_case_sensitive(self):
        cands = Candidates('Foo', 'bar', 'Baz')
        self.assertEqual(cands.reduce('f', case_sensitive=True), Candidates())
        self.assertEqual(cands.reduce('f', case_sensitive=False), Candidates('Foo'))
        self.assertEqual(cands.reduce('B', case_sensitive=True), Candidates('Baz'))
        self.assertEqual(cands.reduce('B', case_sensitive=False), Candidates('bar', 'Baz'))

    def test_copy_everything(self):
        cands = Candidates('foo', 'bar', 'baz', separators=('.',), current_index=1)
        cp = cands.copy()
        self.assertEqual(cp, ('foo', 'bar', 'baz'))
        self.assertEqual(cp.separators, ('.',))
        self.assertEqual(cp.current_index, 1)

    def test_copy_with_updated_items_set_to_empty_sequence(self):
        cands = Candidates('foo', 'bar', 'baz', separators=('.',), current_index=1)
        cp = cands.copy(())
        self.assertEqual(cp, ())
        self.assertEqual(cp.separators, ('.',))
        self.assertEqual(cp.current_index, None)

    def test_copy_with_updated_items_set_to_sequence_without_current_item(self):
        cands = Candidates('foo', 'bar', 'baz', separators=('.',), current_index=1)
        cp = cands.copy('boo', 'far', 'faz')
        self.assertEqual(cp, ('boo', 'far', 'faz'))
        self.assertEqual(cp.separators, ('.',))
        self.assertEqual(cp.current_index, 0)

    def test_copy_with_updated_items_set_to_sequence_with_current_item(self):
        cands = Candidates('foo', 'bar', 'baz', separators=('.',), current_index=1)
        cp = cands.copy('baz', 'foo', 'bar')
        self.assertEqual(cp, ('baz', 'foo', 'bar'))
        self.assertEqual(cp.separators, ('.',))
        self.assertEqual(cp.current_index, 2)

    def test_copy_with_updated_separator(self):
        cands = Candidates('foo', 'bar', 'baz', separators=('.',), current_index=1)
        cp = cands.copy(separators=(':',))
        self.assertEqual(cp, ('foo', 'bar', 'baz'))
        self.assertEqual(cp.separators, (':',))
        self.assertEqual(cp.current_index, 1)

    def test_copy_with_updated_current_index(self):
        cands = Candidates('foo', 'bar', 'baz', separators=('.',), current_index=1)
        cp = cands.copy(current_index=2)
        self.assertEqual(cp, ('foo', 'bar', 'baz'))
        self.assertEqual(cp.separators, ('.',))
        self.assertEqual(cp.current_index, 2)

    def test_sorted(self):
        self.assertEqual(Candidates('Fo', 'bar', 'Bazz').sorted(),
                         ('Bazz', 'Fo', 'bar'))
        self.assertEqual(Candidates('Fo', 'bar', 'Bazz').sorted(key=str.casefold),
                         ('bar', 'Bazz', 'Fo'))
        self.assertEqual(Candidates('Fo', 'bar', 'Bazz').sorted(key=len),
                         ('Fo', 'bar', 'Bazz'))

    def test_sorted_preserve_current_candidate(self):
        orig = Candidates('Fo', 'bar', 'Bazz', current_index=2)
        cp = orig.sorted(key=str.casefold, preserve_current=True)
        self.assertEqual(cp.current_index, 1)
        cp = orig.sorted(key=str.casefold, preserve_current=False)
        self.assertEqual(cp.current_index, 0)
