import urwid
import unittest

from . _handle_urwidpatches import (setUpModule, tearDownModule)


class TestListBox_scrolling_API(unittest.TestCase):
    def mk_test_subjects(self, *listbox_items):
        listbox = urwid.ListBox(
            urwid.SimpleListWalker(list(listbox_items))
        )
        return listbox

    def test_rows_max(self):
        size = (10, 5)

        listbox = self.mk_test_subjects()
        self.assertEqual(listbox.rows_max(size), 0)

        listbox = self.mk_test_subjects(urwid.Text('1'),
                                        urwid.Text('2'),
                                        urwid.Text('3'))
        self.assertEqual(listbox.rows_max(size), 3)

        listbox = self.mk_test_subjects(urwid.Text('1'),
                                        urwid.Text('2\n3'),
                                        urwid.Text('4\n5\n6'))
        self.assertEqual(listbox.rows_max(size), 6)

    def test_get_scrollpos(self):
        # 7 lines total
        listbox = self.mk_test_subjects(urwid.Text('a1'),
                                        urwid.Text('a2'),
                                        urwid.Text('a3'),
                                        urwid.Text('b4\nb5'),
                                        urwid.Text('c6\nc7'))
        size = (10, 5)

        # Go 3 lines down to reach the bottom
        for i in range(3):
            self.assertEqual(listbox.get_scrollpos(size), i)
            listbox.keypress(size, 'down')

        # Hitting 'down' again doesn't do anything
        bottom_pos = i
        for i in range(3):
            self.assertEqual(listbox.get_scrollpos(size), bottom_pos)
            listbox.keypress(size, 'down')

        # Go 3 lines up to reach the top
        for i in reversed(range(3)):
            self.assertEqual(listbox.get_scrollpos(size), i)
            listbox.keypress(size, 'up')

        # Hitting 'up' again doesn't do anything
        top_pos = i
        for i in range(3):
            self.assertEqual(listbox.get_scrollpos(size), top_pos)
            listbox.keypress(size, 'top')
