from stig.tui.group import Group

import unittest
import urwid


class TestGroup(unittest.TestCase):
    def setUp(self):
        self.grp = Group(
            {'name': 'one',
             'widget': urwid.Text('This is text one.')},
            {'name': 'two',
             'widget': urwid.Text('This is text two.')},
        )

    def test_widget_attributes(self):
        self.assertEqual(self.grp.names, ['one', 'two'])
        self.assertEqual(self.grp.one.text, 'This is text one.')
        self.assertEqual(self.grp.two.text, 'This is text two.')

    def test_add(self):
        self.grp.add(name='three', widget=urwid.Text('This is text three.'))
        self.assertEqual(self.grp.names, ['one', 'two', 'three'])
        self.assertEqual(self.grp.three.text, 'This is text three.')

    def test_add_end(self):
        self.grp.add(name='three', widget=urwid.Text('This is text three.'),
                     position='end')
        self.assertEqual(self.grp.names, ['one', 'two', 'three'])
        self.assertEqual(self.grp.three.text, 'This is text three.')

    def test_add_start(self):
        self.grp.add(name='zero', widget=urwid.Text('This is text zero.'),
                     position='start')
        self.assertEqual(self.grp.names, ['zero', 'one', 'two'])
        self.assertEqual(self.grp.zero.text, 'This is text zero.')

    def test_add_int(self):
        self.grp.add(name='x', widget=urwid.Text('This is text x.'),
                     position=1)
        self.assertEqual(self.grp.names, ['one', 'x', 'two'])
        self.assertEqual(self.grp.x.text, 'This is text x.')

    def test_add_hidden(self):
        self.grp.add(name='x', widget=urwid.Text('This is text x.'),
                     visible=False)
        self.assertEqual(self.grp.names, ['one', 'two', 'x'])
        self.assertEqual(self.grp.visible('x'), False)

    def test_hide(self):
        self.grp.hide('one')
        self.assertEqual(self.grp.visible('one'), False)

    def test_show(self):
        self.grp.hide('two')
        self.assertEqual(self.grp.visible('two'), False)
        self.grp.show('two')
        self.assertEqual(self.grp.visible('two'), True)

    def test_remove(self):
        self.grp.add(name='x', widget=urwid.Text('This is text x.'),
                     visible=False, removable=True)
        self.assertEqual(self.grp.names, ['one', 'two', 'x'])
        self.grp.remove('x')
        self.assertEqual(self.grp.names, ['one', 'two'])
