from stig.client.sorters.base import SorterBase, SortSpec

import unittest
import random


class TestSorterBase(unittest.TestCase):
    def setUp(self):
        class TestSorter(SorterBase):
            SORTSPECS = {'foo' : SortSpec(lambda item: item['foo'],
                                          aliases=('f', 'F'),
                                          description='Some description'),
                         'bar' : SortSpec(lambda item: item['bar'],
                                          aliases=('b', 'B'),
                                          description='Some other description')}
        self.sortercls = TestSorter

    def assert_sorted(self, items, sortstrings=None, exp_id_order=None):
        items = sorted(items, key=lambda _: random.random())
        if sortstrings:
            items_sorted = self.sortercls(sortstrings).apply(items)
        else:
            items_sorted = self.sortercls().apply(items)
        if exp_id_order:
            self.assertEqual(tuple(i['id'] for i in items_sorted), exp_id_order)
        else:
            self.assertEqual(set(i['id'] for i in items),
                             set(i['id'] for i in items_sorted))

    def test_no_sorter(self):
        items = [{'id': 1, 'foo': 'a', 'bar': 'z'},
                 {'id': 2, 'foo': 'b', 'bar': 'y'},
                 {'id': 3, 'foo': 'c', 'bar': 'x'}]
        self.assert_sorted(items)
        self.assert_sorted(items)

    def test_single_sorter(self):
        items = [{'id': 1, 'foo': 'a', 'bar': 'z'},
                 {'id': 2, 'foo': 'b', 'bar': 'y'},
                 {'id': 3, 'foo': 'c', 'bar': 'x'}]
        self.assert_sorted(items, ('foo',), (1, 2, 3))
        self.assert_sorted(items, ('bar',), (3, 2, 1))

    def test_invert_sorter(self):
        items = [{'id': 1, 'foo': 'a', 'bar': 'z'},
                 {'id': 2, 'foo': 'b', 'bar': 'y'},
                 {'id': 3, 'foo': 'c', 'bar': 'x'}]
        self.assert_sorted(items, ('!foo',), (3, 2, 1))
        self.assert_sorted(items, ('!bar',), (1, 2, 3))

    def test_multiple_sorters(self):
        items = [{'id': 1, 'foo': 'a', 'bar': 'c'},
                 {'id': 2, 'foo': 'a', 'bar': 'b'},
                 {'id': 3, 'foo': 'b', 'bar': 'a'},
                 {'id': 4, 'foo': 'b', 'bar': 'c'},
                 {'id': 5, 'foo': 'c', 'bar': 'b'},
                 {'id': 6, 'foo': 'c', 'bar': 'a'}]
        self.assert_sorted(items, ('foo', 'bar'), (3, 6, 2, 5, 1, 4))
        self.assert_sorted(items, ('bar', 'foo'), (2, 1, 3, 4, 6, 5))

    def test_multiple_sorters_with_some_inverted(self):
        items = [{'id': 1, 'foo': 'a', 'bar': 'c'},
                 {'id': 2, 'foo': 'a', 'bar': 'b'},
                 {'id': 3, 'foo': 'b', 'bar': 'a'},
                 {'id': 4, 'foo': 'b', 'bar': 'c'},
                 {'id': 5, 'foo': 'c', 'bar': 'b'},
                 {'id': 6, 'foo': 'c', 'bar': 'a'}]
        self.assert_sorted(items, ('!foo', 'bar'), (6, 3, 5, 2, 4, 1))
        self.assert_sorted(items, ('foo', '!bar'), (1, 4, 2, 5, 3, 6))
        self.assert_sorted(items, ('!bar', 'foo'), (1, 2, 4, 3, 5, 6))
        self.assert_sorted(items, ('bar', '!foo'), (6, 5, 3, 4, 2, 1))

    def test_aliases(self):
        items = [{'id': 1, 'foo': 'a', 'bar': 'z'},
                 {'id': 2, 'foo': 'b', 'bar': 'y'},
                 {'id': 3, 'foo': 'c', 'bar': 'x'}]
        self.assert_sorted(items, ('f',), (1, 2, 3))
        self.assert_sorted(items, ('F',), (1, 2, 3))
        self.assert_sorted(items, ('b',), (3, 2, 1))
        self.assert_sorted(items, ('B',), (3, 2, 1))

    def test_inverted_aliases(self):
        items = [{'id': 1, 'foo': 'a', 'bar': 'z'},
                 {'id': 2, 'foo': 'b', 'bar': 'y'},
                 {'id': 3, 'foo': 'c', 'bar': 'x'}]
        self.assert_sorted(items, ('!f',), (3, 2, 1))
        self.assert_sorted(items, ('!F',), (3, 2, 1))
        self.assert_sorted(items, ('!b',), (1, 2, 3))
        self.assert_sorted(items, ('!B',), (1, 2, 3))

    def test___str__(self):
        items = [{'id': 1, 'foo': 'a', 'bar': 'z'},
                 {'id': 2, 'foo': 'b', 'bar': 'y'},
                 {'id': 3, 'foo': 'c', 'bar': 'x'}]
        self.assertEqual(str(self.sortercls(('foo', 'bar'))), 'foo,bar')
        self.assertEqual(str(self.sortercls(('bar', 'foo'))), 'bar,foo')
        self.assertEqual(str(self.sortercls(('!foo', 'bar'))), '!foo,bar')
        self.assertEqual(str(self.sortercls(('bar', '!foo'))), 'bar,!foo')
        self.assertEqual(str(self.sortercls(('!foo', 'b'))), '!foo,bar')
        self.assertEqual(str(self.sortercls(('B', '!F'))), 'bar,!foo')
        self.assertEqual(str(self.sortercls(('!b', 'f'))), '!bar,foo')

    def test_adding_sorters(self):
        foo = self.sortercls(('foo',))
        bar = self.sortercls(('bar',))
        self.assertEqual(str(foo + bar), 'foo,bar')
        self.assertEqual(str(bar + foo), 'bar,foo')
        Foo = self.sortercls(('!foo',))
        Bar = self.sortercls(('!bar',))
        self.assertEqual(str(foo + Bar), 'foo,!bar')
        self.assertEqual(str(bar + Foo), 'bar,!foo')

    def test_sorters_are_deduplicated(self):
        for fstr in ('foo', 'f', 'F'):
            self.assertEqual(str(self.sortercls((fstr, fstr))), 'foo')
            self.assertEqual(str(self.sortercls((fstr, 'bar', fstr))), 'bar,foo')
            self.assertEqual(str(self.sortercls((fstr, 'f'))), 'foo')
            self.assertEqual(str(self.sortercls((fstr, 'F'))), 'foo')
            self.assertEqual(str(self.sortercls((fstr, 'bar', 'f'))), 'bar,foo')
            self.assertEqual(str(self.sortercls((fstr, 'bar', 'F'))), 'bar,foo')
            self.assertEqual(str(self.sortercls(('f', fstr))), 'foo')
            self.assertEqual(str(self.sortercls(('F', fstr))), 'foo')
            self.assertEqual(str(self.sortercls(('f', 'bar', fstr))), 'bar,foo')
            self.assertEqual(str(self.sortercls(('F', 'bar', fstr))), 'bar,foo')
            self.assertEqual(str(self.sortercls(('!'+fstr, fstr))), 'foo')
            self.assertEqual(str(self.sortercls((fstr, '!'+fstr))), '!foo')
            self.assertEqual(str(self.sortercls(('!'+fstr, 'bar', fstr))), 'bar,foo')
            self.assertEqual(str(self.sortercls((fstr, 'bar', '!'+fstr))), 'bar,!foo')

    def test_apply_inplace(self):
        items = [{'id': 1, 'foo': 'a', 'bar': 'z'},
                 {'id': 2, 'foo': 'b', 'bar': 'y'},
                 {'id': 3, 'foo': 'c', 'bar': 'x'}]
        random.shuffle(items)
        self.sortercls(('foo',)).apply(items, inplace=True)
        self.assertEqual(tuple(item['id'] for item in items), (1, 2, 3))
        self.sortercls(('!foo',)).apply(items, inplace=True)
        self.assertEqual(tuple(item['id'] for item in items), (3, 2, 1))
        self.sortercls(('bar',)).apply(items, inplace=True)
        self.assertEqual(tuple(item['id'] for item in items), (3, 2, 1))
        self.sortercls(('!bar',)).apply(items, inplace=True)
        self.assertEqual(tuple(item['id'] for item in items), (1, 2, 3))

    def test_apply_item_getter(self):
        from types import SimpleNamespace
        items = [SimpleNamespace(id=1, values={'foo': 'a', 'bar': 'z'}),
                 SimpleNamespace(id=2, values={'foo': 'b', 'bar': 'y'}),
                 SimpleNamespace(id=3, values={'foo': 'c', 'bar': 'x'})]

        def item_getter(obj):
            print('getting item for %r' % (obj,))
            return obj.values

        srted = self.sortercls(('foo',)).apply(items, item_getter=item_getter)
        self.assertEqual(tuple(obj.id for obj in srted), (1, 2, 3))

        srted = self.sortercls(('!foo',)).apply(items, item_getter=item_getter)
        self.assertEqual(tuple(obj.id for obj in srted), (3, 2, 1))

        srted = self.sortercls(('bar',)).apply(items, item_getter=item_getter)
        self.assertEqual(tuple(obj.id for obj in srted), (3, 2, 1))

        srted = self.sortercls(('!bar',)).apply(items, item_getter=item_getter)
        self.assertEqual(tuple(obj.id for obj in srted), (1, 2, 3))
