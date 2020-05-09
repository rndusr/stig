from stig.tui.group import Group

import unittest
import urwid

from .resources_tui import get_canvas_text


class TestGroup(unittest.TestCase):
    def setUp(self):
        items = [{'name': 'one', 'widget': urwid.Text('Widget one')},
                 {'name': 'two', 'widget': urwid.Text('Widget two')},]
        self.grp = Group(*items, cls=urwid.Pile)

    def assert_render_text(self, *texts):
        size = (20,)
        exp_lines = [text.ljust(size[0]) for text in texts]

        canv = self.grp.render(size)
        lines = [get_canvas_text(row) for row in canv.content()]
        self.assertEqual(lines, exp_lines)

    def test_get_item_by_name(self):
        self.assertEqual(self.grp._get_item_by_name('one')['name'], 'one')
        self.assertEqual(self.grp._get_item_by_name('two')['name'], 'two')

        with self.assertRaises(ValueError):
            self.grp._get_item_by_name('three')
        self.grp.add(name='three', widget=urwid.Text('Widget three'),
                     removable=True)
        self.assertEqual(self.grp._get_item_by_name('three')['name'], 'three')

        self.grp.remove(name='three')
        with self.assertRaises(ValueError):
            self.grp._get_item_by_name('three')

    def test_get_item_by_name_only_visible(self):
        self.assertEqual(self.grp._get_item_by_name('one')['name'], 'one')
        self.assertEqual(self.grp._get_item_by_name('one', visible=True)['name'], 'one')
        self.assertEqual(self.grp._get_item_by_name('two', visible=True)['name'], 'two')

        self.grp.hide('one')
        self.assertEqual(self.grp._get_item_by_name('one')['name'], 'one')
        self.assertEqual(self.grp._get_item_by_name('one', visible=True), None)
        self.assertEqual(self.grp._get_item_by_name('two', visible=True)['name'], 'two')

        self.grp.show('one')
        self.assertEqual(self.grp._get_item_by_name('one')['name'], 'one')
        self.assertEqual(self.grp._get_item_by_name('one', visible=True)['name'], 'one')
        self.assertEqual(self.grp._get_item_by_name('two', visible=True)['name'], 'two')

    def test_get_item_by_position(self):
        self.assertEqual(self.grp._get_item_by_position(position=0)['name'], 'one')
        self.assertEqual(self.grp._get_item_by_position(position=1)['name'], 'two')

        with self.assertRaises(ValueError):
            self.grp._get_item_by_position(position=2)
        self.grp.add(name='three', widget=urwid.Text('Widget three'),
                     removable=True)
        self.assertEqual(self.grp._get_item_by_position(position=2)['name'], 'three')

        self.grp.remove('three')
        with self.assertRaises(ValueError):
            self.grp._get_item_by_position(position=2)

    def test_get_item_by_position_only_visible(self):
        self.assertEqual(self.grp._get_item_by_position(position=0)['name'], 'one')
        self.assertEqual(self.grp._get_item_by_position(position=0, visible=True)['name'], 'one')
        self.assertEqual(self.grp._get_item_by_position(position=1, visible=True)['name'], 'two')

        self.grp.hide('one')
        self.assertEqual(self.grp._get_item_by_position(position=0)['name'], 'one')
        self.assertEqual(self.grp._get_item_by_position(position=0, visible=True), None)
        self.assertEqual(self.grp._get_item_by_position(position=1, visible=True)['name'], 'two')

        self.grp.show('one')
        self.assertEqual(self.grp._get_item_by_position(position=0)['name'], 'one')
        self.assertEqual(self.grp._get_item_by_position(position=0, visible=True)['name'], 'one')
        self.assertEqual(self.grp._get_item_by_position(position=1, visible=True)['name'], 'two')

    def test_get_position(self):
        self.assertEqual(self.grp.get_position('one'), 0)
        self.assertEqual(self.grp.get_position('two'), 1)
        with self.assertRaises(ValueError):
            self.grp.get_position('three')

    def test_get_position_only_visible(self):
        self.assertEqual(self.grp.get_position('one', visible=True), 0)
        self.assertEqual(self.grp.get_position('two', visible=True), 1)

        self.grp.hide('two')
        self.assertEqual(self.grp.get_position('one', visible=True), 0)
        self.assertEqual(self.grp.get_position('two', visible=True), None)
        self.assertEqual(self.grp.get_position('two', visible=False), 1)

        self.grp.show('two')
        self.assertEqual(self.grp.get_position('one', visible=True), 0)
        self.assertEqual(self.grp.get_position('two', visible=True), 1)

    def test_names_attribute(self):
        self.assertEqual(self.grp.names, ['one', 'two'])

    def test_widget_as_attributes(self):
        self.assertEqual(self.grp.one.text, 'Widget one')
        self.assertEqual(self.grp.two.text, 'Widget two')

    def test_add(self):
        self.grp.add(name='three', widget=urwid.Text('Widget three'))
        self.assertEqual(self.grp.names, ['one', 'two', 'three'])
        self.assert_render_text('Widget one', 'Widget two', 'Widget three')

    def test_add_end(self):
        self.grp.add(name='three', widget=urwid.Text('Widget three'),
                     position='end')
        self.assertEqual(self.grp.names, ['one', 'two', 'three'])
        self.assert_render_text('Widget one', 'Widget two', 'Widget three')

    def test_add_start(self):
        self.grp.add(name='zero', widget=urwid.Text('Widget zero'),
                     position='start')
        self.assertEqual(self.grp.names, ['zero', 'one', 'two'])
        self.assert_render_text('Widget zero', 'Widget one', 'Widget two')

    def test_add_at_position(self):
        self.grp.add(name='x', widget=urwid.Text('Widget x'),
                     position=1)
        self.assertEqual(self.grp.names, ['one', 'x', 'two'])
        self.assert_render_text('Widget one', 'Widget x', 'Widget two')

        self.grp.add(name='zero', position=0, widget=urwid.Text('Widget zero'))
        self.assertEqual(self.grp.names, ['zero', 'one', 'x', 'two'])
        self.assert_render_text('Widget zero', 'Widget one', 'Widget x', 'Widget two')

        self.grp.add(name='three', position=4, widget=urwid.Text('Widget three'))
        self.assertEqual(self.grp.names, ['zero', 'one', 'x', 'two', 'three'])
        self.assert_render_text('Widget zero', 'Widget one', 'Widget x', 'Widget two', 'Widget three')

    def test_add_hidden(self):
        self.grp.add(name='x', widget=urwid.Text('Widget x'),
                     visible=False)
        self.assertEqual(self.grp.names, ['one', 'two', 'x'])
        self.assertEqual(self.grp.visible('x'), False)
        self.assert_render_text('Widget one', 'Widget two')

    def test_hide_show(self):
        self.grp.hide('one')
        self.assertEqual(self.grp.visible('one'), False)
        self.assert_render_text('Widget two')

        self.grp.hide('two')
        self.assertEqual(self.grp.visible('two'), False)
        self.assert_render_text()

        self.grp.show('one')
        self.assertEqual(self.grp.visible('one'), True)
        self.assert_render_text('Widget one')

        self.grp.show('two')
        self.assertEqual(self.grp.visible('two'), True)
        self.assert_render_text('Widget one', 'Widget two')

    def test_remove(self):
        self.grp.add(name='x', widget=urwid.Text('Widget x'),
                     removable=True)
        self.assertEqual(self.grp.names, ['one', 'two', 'x'])
        self.assert_render_text('Widget one', 'Widget two', 'Widget x')

        self.grp.remove('x')
        self.assertEqual(self.grp.names, ['one', 'two'])
        self.assert_render_text('Widget one', 'Widget two')

    def test_replace(self):
        self.grp.replace('one', urwid.Text('1'))
        self.assertEqual(self.grp.names, ['one', 'two'])
        self.assert_render_text('1', 'Widget two')

    def test_replace_hidden(self):
        self.grp.hide('two')
        self.grp.replace('two', urwid.Text('2'))
        self.assertEqual(self.grp.names, ['one', 'two'])
        self.assert_render_text('Widget one')

        self.grp.show('two')
        self.assert_render_text('Widget one', '2')
