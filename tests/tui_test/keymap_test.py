import unittest
from stig.tui.keymap import (Key, KeyMap)
from urwid import Text

import logging
log = logging.getLogger(__name__)


def test_key_creation():
    for key,exp in (('alt-l', 'meta l'),
                    ('<ctrl-e>', 'ctrl e'),
                    ('<CTRL-e>', 'ctrl e'),
                    ('<CTRL-E>', 'ctrl E'),
                    ('<ctrl-E>', 'ctrl E'),
                    ('del', 'delete'),
                    ('esc', 'esc'),
                    ('ins', 'insert'),
                    ('return', 'enter'),
                    ('space', ' '),
                    ('shift-delete', 'shift delete'),
                    ('-', '-')):
        k = Key(key)
        assert k == exp, print('%r != %r' % (k, exp))

def test_key_string():
    for key,exp in ((Key('meta l'), 'alt-l'),
                    (Key('delete'), 'delete'),
                    (Key('esc'), 'escape'),
                    (Key('ins'), 'insert'),
                    (Key('return'), 'enter'),
                    (Key(' '), 'space'),
                    (Key('-'), '-')):
        assert key.pretty == exp, print('%r != %r' % (key.pretty, exp))


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
