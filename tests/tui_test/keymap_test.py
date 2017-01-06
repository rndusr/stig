import unittest
from stig.tui.keymap import (Key, KeyMap)
from urwid import Text

import logging
log = logging.getLogger(__name__)


class TestKey(unittest.TestCase):
    def test_compare_Key_with_Key(self):
        self.assertEqual(Key('alt-l'), Key('Alt-l'))
        self.assertEqual(Key('alt-l'), Key('meta-l'))
        self.assertEqual(Key('alt-l'), Key('Meta-l'))
        self.assertEqual(Key('alt-l'), Key('<alt-l>'))
        self.assertNotEqual(Key('alt-l'), Key('alt-L'))

        self.assertEqual(Key('ctrl-e'), Key('Ctrl-e'))
        self.assertEqual(Key('ctrl-e'), Key('<ctrl-e>'))
        self.assertEqual(Key('ctrl-e'), Key('CTRL-e'))
        self.assertNotEqual(Key('ctrl-e'), Key('ctrl-E'))

        self.assertEqual(Key('space'), Key(' '))
        self.assertEqual(Key('escape'), Key('esc'))
        self.assertEqual(Key('home'), Key('pos1'))
        self.assertEqual(Key('delete'), Key('del'))
        self.assertEqual(Key('enter'), Key('return'))
        self.assertEqual(Key('insert'), Key('ins'))

    def test_compare_Key_with_urwid_key(self):
        self.assertEqual(Key('alt-l'), 'meta l')
        self.assertEqual(Key('space'), ' ')
        self.assertEqual(Key('escape'), 'esc')
        self.assertEqual(Key('pgup'), 'page up')
        self.assertEqual(Key('pgdn'), 'page down')
        self.assertEqual(Key('shift-delete'), 'shift delete')
        self.assertEqual(Key('-'), '-')

    def test_convert_shift_modifier(self):
        self.assertEqual(Key('shift-E'), Key('E'))
        self.assertEqual(Key('shift-e'), Key('E'))
        self.assertEqual(Key('shift-ö'), Key('Ö'))
        self.assertNotEqual(Key('shift-ö'), Key('O'))

    def test_invalid_modifier(self):
        with self.assertRaises(ValueError) as cm:
            Key('shit-e')
        self.assertIn('Invalid modifier', str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            Key('alt-')
        self.assertIn('Missing character', str(cm.exception))


class TestKeyMap(unittest.TestCase):
    def test_no_callback(self):
        km = KeyMap()
        km.bind(key='ctrl a',
                action=lambda widget: widget.set_text('foo was called'))
        widget = km.wrap(Text)('Test Text')
        widget.keypress((80,), 'ctrl a')
        self.assertEqual(widget.text, 'foo was called')

    def test_global_callback(self):
        called = None
        def cb(action, widget):
            nonlocal called
            called = action

        km = KeyMap(callback=cb)
        km.bind(key='ctrl a', action='foo')
        widget = km.wrap(Text)('Test Text')
        widget.keypress((80,), 'ctrl a')
        self.assertEqual(called, 'foo')

    def test_individual_callback(self):
        called = None
        def cb(action, widget):
            nonlocal called
            called = action

        km = KeyMap()
        km.bind(key='ctrl a', action='foo')
        widget = km.wrap(Text, callback=cb)('Test Text')
        widget.keypress((80,), 'ctrl a')
        self.assertEqual(called, 'foo')

    def test_key_translation(self):
        km = KeyMap()
        km.bind(key='a',
                action=lambda widget: widget.set_text('Key pressed: a'))
        km.bind(key='b', action=Key('a'))
        widget = km.wrap(Text)('Test Text')
        widget.keypress((80,), 'b')
        self.assertEqual(widget.text, 'Key pressed: a')
