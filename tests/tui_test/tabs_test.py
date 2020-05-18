import unittest

import urwid

from stig.tui import tabs
from stig.tui.tabs import TabID, Tabs, _find_unused_id


def test_find_unused_id():
    assert _find_unused_id([]) == 0
    assert _find_unused_id([0, 1, 2]) == 3
    assert _find_unused_id([1, 2]) == 0
    assert _find_unused_id([0, 1, 3]) == 2

# Normal TabIDs are lowest unused integers.  That means for these simple
# tests, TabIDs are mostly identical to tab indexes, which may have weird
# consequences.
def make_large_id(existing_ids):
    if not existing_ids:
        return TabID(999)
    else:
        return TabID(max(existing_ids) + 100)
tabs._find_unused_id = make_large_id


class SelectableText(urwid.Text):
    _selectable = True
    def keypress(self, size, key):
        return key


class TestTabs(unittest.TestCase):
    def setUp(self):
        self.tabs = Tabs((urwid.Text('Tab1'), urwid.Text('Tab one')),
                         (urwid.Text('Tab2'), urwid.Text('Tab two')))

    def test_get_index_focused(self):
        self.tabs.focus_position = 0
        self.assertEqual(self.tabs.get_index(), 0)

    def test_get_index_by_existing_index(self):
        self.assertEqual(self.tabs.get_index(1), 1)
        self.assertEqual(self.tabs.get_index(0), 0)
        self.assertEqual(self.tabs.get_index(-1), 1)
        self.assertEqual(self.tabs.get_index(-2), 0)

    def test_get_index_by_nonexisting_index(self):
        with self.assertRaises(IndexError) as cm:
            self.tabs.get_index(2)
        self.assertIn('position', str(cm.exception))
        self.assertIn('2', str(cm.exception))

        with self.assertRaises(IndexError) as cm:
            self.tabs.get_index(-3)
        self.assertIn('position', str(cm.exception))
        self.assertIn('-3', str(cm.exception))

    def test_get_index_by_existing_tabid(self):
        tabids = self.tabs.get_id(0), self.tabs.get_id(1)
        for index,tabid in enumerate(tabids):
            self.assertEqual(self.tabs.get_index(tabid), index)

    def test_get_index_by_nonexisting_tabid(self):
        with self.assertRaises(IndexError) as cm:
            self.tabs.get_index(TabID(-42))
        self.assertIn('ID', str(cm.exception))
        self.assertIn('-42', str(cm.exception))

    def test_get_index_when_no_tabs_exist(self):
        self.tabs = Tabs()
        self.assertEqual(self.tabs.get_index(), None)

    def test_get_id_focused(self):
        self.tabs.focus_position = 0
        self.assertEqual(self.tabs.get_id(), self.tabs.get_id(0))
        self.assertIsInstance(self.tabs.get_id(), TabID)

    def test_get_id_by_existing_index(self):
        self.assertIsInstance(self.tabs.get_id(0), TabID)
        self.assertIsInstance(self.tabs.get_id(1), TabID)

    def test_get_id_by_nonexisting_index(self):
        with self.assertRaises(IndexError) as cm:
            self.tabs.get_id(17)
        self.assertIn('position', str(cm.exception))
        self.assertIn('17', str(cm.exception))

    def test_get_id_by_existing_id(self):
        self.assertEqual(self.tabs.get_id(self.tabs.get_id(0)), self.tabs.get_id(0))
        self.assertEqual(self.tabs.get_id(self.tabs.get_id(1)), self.tabs.get_id(1))

    def test_get_id_by_nonexisting_id(self):
        with self.assertRaises(IndexError) as cm:
            self.tabs.get_id(TabID(-42))
        self.assertIn('ID', str(cm.exception))
        self.assertIn('-42', str(cm.exception))

    def test_get_id_when_no_tabs_exist(self):
        self.tabs = Tabs()
        self.assertEqual(self.tabs.get_id(), None)


    def test_get_set_info_focused(self):
        self.tabs.focus_position = 0
        self.assertEqual(self.tabs.get_info(), {})
        self.tabs.focus_position = 1
        self.assertEqual(self.tabs.get_info(), {})
        self.tabs.set_info(hey='you')
        self.assertEqual(self.tabs.get_info(), {'hey': 'you'})
        self.tabs.focus_position = 0
        self.tabs.set_info(out='there')
        self.assertEqual(self.tabs.get_info(), {'out': 'there'})

    def test_get_set_info_by_existing_index(self):
        self.assertEqual(self.tabs.get_info(0), {})
        self.assertEqual(self.tabs.get_info(1), {})
        self.tabs.set_info(0, hey='you')
        self.tabs.set_info(1, out='there')
        self.assertEqual(self.tabs.get_info(0), {'hey': 'you'})
        self.assertEqual(self.tabs.get_info(1), {'out': 'there'})

    def test_get_set_info_by_nonexisting_index(self):
        with self.assertRaises(IndexError) as cm:
            self.tabs.get_info(17)
        self.assertIn('position', str(cm.exception))
        self.assertIn('17', str(cm.exception))

    def test_get_set_info_by_existing_id(self):
        self.assertEqual(self.tabs.get_info(self.tabs.get_id(0)), {})
        self.assertEqual(self.tabs.get_info(self.tabs.get_id(1)), {})
        self.tabs.set_info(self.tabs.get_id(0), hey='you')
        self.tabs.set_info(self.tabs.get_id(1), out='there')
        self.assertEqual(self.tabs.get_info(self.tabs.get_id(0)), {'hey': 'you'})
        self.assertEqual(self.tabs.get_info(self.tabs.get_id(1)), {'out': 'there'})

    def test_get_set_info_by_nonexisting_id(self):
        with self.assertRaises(IndexError) as cm:
            self.tabs.get_info(TabID(1000000))
        self.assertIn('ID', str(cm.exception))
        self.assertIn('1000', str(cm.exception))

    def test_get_set_info_when_no_tabs_exist(self):
        with self.assertRaises(RuntimeError) as cm:
            Tabs().set_info(foo='bar')
        self.assertEqual(str(cm.exception), 'Tabs is empty')
        self.assertEqual(Tabs().get_info(), None)

    def test_tab_info_is_removed_when_tab_is_removed(self):
        self.tabs.set_info(self.tabs.get_id(TabID(999)), hey='you')
        self.tabs.set_info(self.tabs.get_id(TabID(1099)), out='there')
        self.tabs.remove(1)
        self.assertEqual(self.tabs._info, {TabID(999): {'hey': 'you'}})
        self.tabs.remove(0)
        self.assertEqual(self.tabs._info, {})

    def test_tab_ids_are_not_equal(self):
        id1 = self.tabs.get_id(0)
        id2 = self.tabs.get_id(1)
        self.assertNotEqual(id1, id2)

    def test_focus_position_property(self):
        self.tabs.focus_position = 0
        self.assertEqual(self.tabs.focus_position, 0)
        self.tabs.focus_position = 1
        self.assertEqual(self.tabs.focus_position, 1)

        with self.assertRaises(IndexError) as cm:
            self.tabs.focus_position = 2
        self.assertIn('position', str(cm.exception))
        self.assertIn('2', str(cm.exception))

        with self.assertRaises(IndexError) as cm:
            self.tabs.focus_position = -1
        self.assertIn('position', str(cm.exception))
        self.assertIn('-1', str(cm.exception))

    def test_focus_id_property(self):
        for i,tabid in enumerate([self.tabs.get_id(0), self.tabs.get_id(1)]):
            self.tabs.focus_id = self.tabs.get_id(tabid)
        self.assertEqual(self.tabs.focus_id, self.tabs.get_id(tabid))
        self.assertEqual(self.tabs.focus_position, i)

        with self.assertRaises(IndexError) as cm:
            self.tabs.focus_id = TabID(123)
        self.assertIn('ID', str(cm.exception))
        self.assertIn('123', str(cm.exception))

    def test_focus_property(self):
        self.tabs.focus_position = 0
        self.assertEqual(self.tabs.focus.text, 'Tab one')
        self.tabs.focus_position = 1
        self.assertEqual(self.tabs.focus.text, 'Tab two')

    def test_prev_focus_position_property(self):
        self.assertEqual(self.tabs.focus_position, 1)
        self.assertEqual(self.tabs.prev_focus_position, None)
        self.tabs.focus_position = 0
        self.assertEqual(self.tabs.prev_focus_position, 1)
        self.tabs.insert(urwid.Text('Tab 3'), urwid.Text('Tab three'))
        self.assertEqual(self.tabs.prev_focus_position, 0)
        self.tabs.focus_position = 1
        self.assertEqual(self.tabs.prev_focus_position, 2)
        self.tabs.remove(1)
        self.assertEqual(self.tabs.prev_focus_position, 0)

    def test_prev_focus_id_property(self):
        self.tabs.insert(urwid.Text('Tab 3'), urwid.Text('Tab three'))
        ids = (self.tabs.get_id(0), self.tabs.get_id(1), self.tabs.get_id(2))
        self.assertEqual(self.tabs.focus_id, ids[2])
        self.assertEqual(self.tabs.prev_focus_id, ids[1])
        self.tabs.focus_id = ids[0]
        self.assertEqual(self.tabs.prev_focus_id, ids[2])
        self.tabs.focus_id = ids[2]
        self.assertEqual(self.tabs.prev_focus_id, ids[0])
        self.tabs.remove(ids[2])
        self.assertEqual(self.tabs.prev_focus_id, ids[0])

    def test_prev_focus(self):
        self.tabs.insert(urwid.Text('Tab 3'), urwid.Text('Tab three'))
        self.assertEqual(self.tabs.focus.text, 'Tab three')
        self.assertEqual(self.tabs.prev_focus.text, 'Tab two')
        self.tabs.focus_position = 0
        self.assertEqual(self.tabs.prev_focus.text, 'Tab three')
        self.tabs.focus_position = 2
        self.assertEqual(self.tabs.prev_focus.text, 'Tab one')
        self.tabs.remove(1)
        self.assertEqual(self.tabs.prev_focus.text, 'Tab three')

    def test_contents_property(self):
        self.assertEqual(tuple(w.text for w in self.tabs.contents),
                         ('Tab one', 'Tab two'))

    def test_titles_property(self):
        self.assertEqual(tuple(t.text for t in self.tabs.titles),
                         ('Tab1', 'Tab2'))

    def test_get_title(self):
        self.tabs.focus_position = 0
        self.assertEqual(self.tabs.get_title().text, 'Tab1')
        self.assertEqual(self.tabs.get_title(0).text, 'Tab1')
        self.assertEqual(self.tabs.get_title(self.tabs.get_id(0)).text, 'Tab1')

        self.assertEqual(self.tabs.get_title(1).text, 'Tab2')
        self.assertEqual(self.tabs.get_title(self.tabs.get_id(1)).text, 'Tab2')

    def test_set_title(self):
        self.tabs.focus_position = 0
        self.tabs.set_title(urwid.Text('foo'))
        self.assertEqual(self.tabs.get_title(0).text, 'foo')

        self.tabs.set_title(urwid.Text('bar'), position=1)
        self.assertEqual(self.tabs.get_title(1).text, 'bar')

        self.tabs.set_title(urwid.Text('FOO'), position=self.tabs.get_id(0))
        self.assertEqual(self.tabs.get_title(0).text, 'FOO')

        self.tabs.set_title(urwid.Text('BAR'), position=self.tabs.get_id(1))
        self.assertEqual(self.tabs.get_title(1).text, 'BAR')

    def test_get_content(self):
        self.tabs.focus_position = 0
        self.assertEqual(self.tabs.get_content().text, 'Tab one')
        self.assertEqual(self.tabs.get_content(0).text, 'Tab one')
        self.assertEqual(self.tabs.get_content(self.tabs.get_id(0)).text, 'Tab one')

        self.assertEqual(self.tabs.get_content(1).text, 'Tab two')
        self.assertEqual(self.tabs.get_content(self.tabs.get_id(1)).text, 'Tab two')

    def test_set_content(self):
        self.tabs.focus_position = 0
        self.tabs.set_content(urwid.Text('foo'))
        self.assertEqual(self.tabs.get_content().text, 'foo')

        self.tabs.set_content(urwid.Text('bar'), position=1)
        self.assertEqual(self.tabs.get_content(1).text, 'bar')

        self.tabs.set_content(urwid.Text('FOO'), position=self.tabs.get_id(0))
        self.assertEqual(self.tabs.get_content(0).text, 'FOO')

        self.tabs.set_content(urwid.Text('BAR'), position=self.tabs.get_id(1))
        self.assertEqual(self.tabs.get_content(1).text, 'BAR')

    def test_remove(self):
        self.tabs.insert(urwid.Text('Tab3'), urwid.Text('Tab three'))
        self.assertEqual(tuple(t.text for t in self.tabs.titles),
                         ('Tab1', 'Tab2', 'Tab3'))
        self.assertEqual(tuple(t.text for t in self.tabs.contents),
                         ('Tab one', 'Tab two', 'Tab three'))

        self.tabs.remove(self.tabs.get_id(2))
        self.assertEqual(tuple(t.text for t in self.tabs.titles),
                         ('Tab1', 'Tab2'))
        self.assertEqual(tuple(t.text for t in self.tabs.contents),
                         ('Tab one', 'Tab two'))

        self.tabs.remove(1)
        self.assertEqual(tuple(t.text for t in self.tabs.titles),
                         ('Tab1',))
        self.assertEqual(tuple(t.text for t in self.tabs.contents),
                         ('Tab one',))

        self.tabs.remove()
        self.assertEqual(tuple(self.tabs.titles), ())
        self.assertEqual(tuple(self.tabs.contents), ())

        with self.assertRaises(IndexError):
            self.tabs.remove(0)

    def test_insert(self):
        self.tabs.focus_position = len(self.tabs) - 1
        self.tabs.insert(urwid.Text('Tab3'), urwid.Text('Tab three'))
        self.assertEqual(tuple(t.text for t in self.tabs.titles),
                         ('Tab1', 'Tab2', 'Tab3'))
        self.assertEqual(tuple(w.text for w in self.tabs.contents),
                         ('Tab one', 'Tab two', 'Tab three'))

        self.tabs.insert(urwid.Text('Tab0'), urwid.Text('Tab zero'), position=0)
        self.assertEqual(tuple(t.text for t in self.tabs.titles),
                         ('Tab0', 'Tab1', 'Tab2', 'Tab3'))
        self.assertEqual(tuple(w.text for w in self.tabs.contents),
                         ('Tab zero', 'Tab one', 'Tab two', 'Tab three'))

        self.tabs.insert(urwid.Text('Tab4'), urwid.Text('Tab four'), position=-1)
        self.assertEqual(tuple(t.text for t in self.tabs.titles),
                         ('Tab0', 'Tab1', 'Tab2', 'Tab3', 'Tab4'))
        self.assertEqual(tuple(w.text for w in self.tabs.contents),
                         ('Tab zero', 'Tab one', 'Tab two', 'Tab three', 'Tab four'))

        self.tabs.insert(urwid.Text('Tab2.5'), urwid.Text('Tab two point five'), position=3)
        self.assertEqual(tuple(t.text for t in self.tabs.titles),
                         ('Tab0', 'Tab1', 'Tab2', 'Tab2.5', 'Tab3', 'Tab4'))
        self.assertEqual(tuple(w.text for w in self.tabs.contents),
                         ('Tab zero', 'Tab one', 'Tab two',
                          'Tab two point five', 'Tab three', 'Tab four'))

        self.tabs.focus_position = 2
        self.tabs.insert(urwid.Text('Tab1.5'), urwid.Text('Tab one point five'), position='left')
        self.assertEqual(tuple(t.text for t in self.tabs.titles),
                         ('Tab0', 'Tab1', 'Tab1.5', 'Tab2', 'Tab2.5', 'Tab3', 'Tab4'))
        self.assertEqual(tuple(w.text for w in self.tabs.contents),
                         ('Tab zero', 'Tab one', 'Tab one point five', 'Tab two',
                          'Tab two point five', 'Tab three', 'Tab four'))

        self.tabs.focus_position = 6
        self.tabs.insert(urwid.Text('Tab4.5'), urwid.Text('Tab four point five'), position='right')
        self.assertEqual(tuple(t.text for t in self.tabs.titles),
                         ('Tab0', 'Tab1', 'Tab1.5', 'Tab2', 'Tab2.5', 'Tab3', 'Tab4', 'Tab4.5'))
        self.assertEqual(tuple(w.text for w in self.tabs.contents),
                         ('Tab zero', 'Tab one', 'Tab one point five', 'Tab two',
                          'Tab two point five', 'Tab three', 'Tab four', 'Tab four point five'))

    def test_load_content_with_no_existing_tabs(self):
        self.tabs.clear()
        self.assertEqual(tuple(self.tabs.titles), ())
        self.assertEqual(self.tabs.focus_position, None)

        self.tabs.load(title=urwid.Text('Foo'), widget=urwid.Text('Tab foo'))
        self.assertEqual(tuple(t.text for t in self.tabs.titles),
                         ('Foo',))
        self.assertEqual(self.tabs.focus_position, 0)

    def test_load_content_at_specific_position(self):
        self.tabs.load(title=urwid.Text('Foo'), widget=urwid.Text('Tab foo'), position=0)
        self.assertEqual(tuple(t.text for t in self.tabs.titles),
                         ('Foo', 'Tab2'))
        self.assertEqual(self.tabs.focus_position, 0)

    def test_load_content_at_focus(self):
        self.tabs.load(title=urwid.Text('Foo'), widget=urwid.Text('Tab foo'))
        self.assertEqual(tuple(t.text for t in self.tabs.titles),
                         ('Tab1', 'Foo'))
        self.assertEqual(self.tabs.focus_position, 1)

    def test_load_content_without_focusing_it(self):
        self.tabs.load(title=urwid.Text('Bar'), widget=urwid.Text('Tab bar'), position=0, focus=False)
        self.assertEqual(tuple(t.text for t in self.tabs.titles),
                         ('Bar', 'Tab2'))
        self.assertEqual(self.tabs.focus_position, 1)

    def test_move_tab_left_right(self):
        tabs = Tabs((urwid.Text('1'),), (urwid.Text('2'),), (urwid.Text('3'),))
        tabs.move(0, 'right')
        self.assertEqual(tuple(t.text for t in tabs.titles), ('2', '1', '3'))
        tabs.move(2, 'left')
        self.assertEqual(tuple(t.text for t in tabs.titles), ('2', '3', '1'))
        tabs.move(1, 'left')
        self.assertEqual(tuple(t.text for t in tabs.titles), ('3', '2', '1'))
        tabs.move(0, 'left')
        self.assertEqual(tuple(t.text for t in tabs.titles), ('3', '2', '1'))
        tabs.move(2, 'right')
        self.assertEqual(tuple(t.text for t in tabs.titles), ('3', '2', '1'))

    def test_move_tab_with_wrapping(self):
        tabs = Tabs((urwid.Text('1'),), (urwid.Text('2'),), (urwid.Text('3'),))
        tabs.move(0, 'left', wrap=True)
        self.assertEqual(tuple(t.text for t in tabs.titles), ('2', '3', '1'))
        tabs.move(2, 'right', wrap=True)
        self.assertEqual(tuple(t.text for t in tabs.titles), ('1', '2', '3'))

    def test_move_tab_to_index(self):
        tabs = Tabs((urwid.Text('1'),), (urwid.Text('2'),), (urwid.Text('3'),))
        tabs.move(0, 1)
        self.assertEqual(tuple(t.text for t in tabs.titles), ('2', '1', '3'))
        tabs.move(1, 2)
        self.assertEqual(tuple(t.text for t in tabs.titles), ('2', '3', '1'))
        tabs.move(2, 0)
        self.assertEqual(tuple(t.text for t in tabs.titles), ('1', '2', '3'))
        with self.assertRaises(IndexError) as cm:
            tabs.move(3, 'right')
        assert str(cm.exception) == 'No tab at position: 3'

    def test_move_tab_to_negative_index(self):
        tabs = Tabs((urwid.Text('1'),), (urwid.Text('2'),), (urwid.Text('3'),))
        tabs.move(-1, 0)
        self.assertEqual(tuple(t.text for t in tabs.titles), ('3', '1', '2'))
        tabs.move(-2, 0)
        self.assertEqual(tuple(t.text for t in tabs.titles), ('1', '3', '2'))
        tabs.move(-3, 2)
        self.assertEqual(tuple(t.text for t in tabs.titles), ('3', '2', '1',))
        with self.assertRaises(IndexError) as cm:
            tabs.move(-4, 0)
        assert str(cm.exception) == 'No tab at position: -4'


class TestTabsKeyPress(unittest.TestCase):
    def setUp(self):
        self.size = (80, 20)
        self.content = [
            urwid.ListBox(urwid.SimpleFocusListWalker([
                urwid.Edit('Field 1'),
                urwid.Edit('Field 2'),
            ])),

            urwid.ListBox(urwid.SimpleFocusListWalker([
                SelectableText('Row 1'),
                urwid.Edit('', 'Edit field 2'),
                SelectableText('Row 3'),
            ]))
        ]
        self.editbox = self.content[1].body[1]
        self.editbox.edit_pos = 0
        self.tabs = Tabs((urwid.Text('Edit fields'), self.content[0]),
                         (urwid.Text('empty'),),
                         (urwid.Text('Text rows'), self.content[1]))

    def check(self, tab_pos, content_pos, edit_pos=None):
        self.assertEqual(self.tabs.focus_position, tab_pos)
        content = self.tabs.focus
        if content_pos is None:
            self.assertEqual(content, None)
        else:
            self.assertEqual(content.focus_position, content_pos)
        if edit_pos is not None:
            self.assertEqual(self.editbox.edit_pos, edit_pos)

    def test_move_up_down_left_right(self):
        self.tabs.focus_position = 0
        self.tabs.focus.focus_position = 0

        # Start at tab 0, row 0; move up and down
        self.check(tab_pos=0, content_pos=0, edit_pos=0)
        self.tabs.keypress(self.size, 'down')
        self.check(tab_pos=0, content_pos=1, edit_pos=0)
        self.tabs.keypress(self.size, 'down')
        self.check(tab_pos=0, content_pos=1, edit_pos=0)
        self.tabs.keypress(self.size, 'up')
        self.check(tab_pos=0, content_pos=0, edit_pos=0)
        self.tabs.keypress(self.size, 'up')
        self.check(tab_pos=0, content_pos=0, edit_pos=0)

        # Move to tab 2, start moving down
        self.tabs.keypress(self.size, 'right')
        self.check(tab_pos=1, content_pos=None, edit_pos=0)
        self.tabs.keypress(self.size, 'right')
        self.check(tab_pos=2, content_pos=0, edit_pos=0)
        self.tabs.keypress(self.size, 'right')
        self.check(tab_pos=2, content_pos=0, edit_pos=0)
        self.tabs.keypress(self.size, 'down')

        # We're now at editbox (tab 2, row 1), moving right should move the cursor
        self.check(tab_pos=2, content_pos=1, edit_pos=0)
        self.tabs.keypress(self.size, 'right')
        self.check(tab_pos=2, content_pos=1, edit_pos=1)
        self.tabs.keypress(self.size, 'right')
        self.check(tab_pos=2, content_pos=1, edit_pos=2)

        # Move cursor back left in edit field
        self.tabs.keypress(self.size, 'left')
        self.check(tab_pos=2, content_pos=1, edit_pos=1)
        self.tabs.keypress(self.size, 'left')
        self.check(tab_pos=2, content_pos=1, edit_pos=0)

        # Cursor is at position 0 in edit field, moving further should switch
        # to left tab (tab 0)
        self.tabs.keypress(self.size, 'left')
        self.check(tab_pos=1, content_pos=None, edit_pos=0)
        self.tabs.keypress(self.size, 'left')
        self.check(tab_pos=0, content_pos=0, edit_pos=0)
