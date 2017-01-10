import unittest
from stig.tui.keymap import (Key, KeyChain, KeyMap)
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
        self.assertEqual(Key('ctrl-e'), Key('ctrl-E'))

        self.assertEqual(Key('space'), Key(' '))
        self.assertEqual(Key('escape'), Key('esc'))
        self.assertEqual(Key('home'), Key('pos1'))
        self.assertEqual(Key('delete'), Key('del'))
        self.assertEqual(Key('enter'), Key('return'))
        self.assertEqual(Key('insert'), Key('ins'))

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

    def test_invalid_modifier(self):
        with self.assertRaises(ValueError) as cm:
            Key('shit-e')
        self.assertIn('Invalid modifier', str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            Key('alt-')
        self.assertIn('Missing character', str(cm.exception))


class TestKeyChain(unittest.TestCase):
    def test_advance(self):
        kc = KeyChain('a', 'b', 'c')
        for _ in range(10):
            self.assertEqual(kc.given, ())
            kc.advance()
            self.assertEqual(kc.given, ('a',))
            kc.advance()
            self.assertEqual(kc.given, ('a', 'b'))
            kc.advance()
            self.assertEqual(kc.given, ('a', 'b', 'c'))
            kc.advance()

    def test_reset(self):
        kc = KeyChain('a', 'b', 'c')
        for i in range(10):
            for _ in range(i): kc.advance()
            kc.reset()
            self.assertEqual(kc.given, ())

    def test_next_key(self):
        kc = KeyChain('a', 'b', 'c')
        for i in range(10):
            self.assertEqual(kc.next_key, 'a')
            kc.advance()
            self.assertEqual(kc.next_key, 'b')
            kc.advance()
            self.assertEqual(kc.next_key, 'c')
            kc.advance()
            self.assertEqual(kc.next_key, None)  # chain is complete
            kc.advance()  # same as reset() if complete

    def test_is_complete(self):
        kc = KeyChain('a', 'b', 'c')
        for i in range(10):
            self.assertEqual(kc.is_complete, False)
            kc.advance()
            self.assertEqual(kc.is_complete, False)
            kc.advance()
            self.assertEqual(kc.is_complete, False)
            kc.advance()
            self.assertEqual(kc.is_complete, True)
            kc.advance()

    def test_feed_with_correct_chain(self):
        kc = KeyChain('a', 'b', 'c')
        self.assertEqual(kc.feed('a'), KeyChain.ADVANCED)
        self.assertEqual(kc.feed('b'), KeyChain.ADVANCED)
        self.assertEqual(kc.feed('c'), KeyChain.COMPLETED)

    def test_feed_with_wrong_chain(self):
        kc = KeyChain('a', 'b', 'c')
        self.assertEqual(kc.feed('x'), KeyChain.REFUSED)

        self.assertEqual(kc.feed('a'), KeyChain.ADVANCED)
        self.assertEqual(kc.feed('x'), KeyChain.ABORTED)

        self.assertEqual(kc.feed('a'), KeyChain.ADVANCED)
        self.assertEqual(kc.feed('b'), KeyChain.ADVANCED)
        self.assertEqual(kc.feed('x'), KeyChain.ABORTED)


class TestKeyMap(unittest.TestCase):
    def test_action_is_callback(self):
        km = KeyMap()
        km.bind(key='a',
                action=lambda widget: widget.set_text('foo'))
        widget = km.wrap(Text)('Test Text')
        widget.keypress((80,), 'a')
        self.assertEqual(widget.text, 'foo')

    def test_widget_callback(self):
        def cb(action, widget):
            widget.set_text(action)

        km = KeyMap()
        km.bind(key='a', action='foo')
        widget = km.wrap(Text, callback=cb)('Test Text')
        widget.keypress((80,), 'a')
        self.assertEqual(widget.text, 'foo')

    def test_default_callback(self):
        def cb(action, widget):
            widget.set_text(action)

        km = KeyMap(callback=cb)
        km.bind(key='a', action='foo')
        widget = km.wrap(Text)('Test Text')
        widget.keypress((80,), 'a')
        self.assertEqual(widget.text, 'foo')

    def test_widget_callback_overrides_default_callback(self):
        def default_cb(action, widget):
            widget.set_text(action)

        def widget_cb(action, widget):
            widget.set_text(action.upper())

        km = KeyMap(callback=default_cb)
        km.bind(key='a', action='foo')
        widget = km.wrap(Text, callback=widget_cb)('Test Text')
        widget.keypress((80,), 'a')
        self.assertEqual(widget.text, 'FOO')

    def test_key_translation(self):
        km = KeyMap()
        km.bind(key='a',
                action=lambda widget: widget.set_text('Key pressed: a'))
        km.bind(key='b', action=Key('a'))
        widget = km.wrap(Text)('Test Text')
        widget.keypress((80,), 'b')
        self.assertEqual(widget.text, 'Key pressed: a')


class TestKeyMap_with_key_chains(unittest.TestCase):
    def setUp(self):
        self.km = KeyMap(callback=self.handle_action)
        self.widget = self.km.wrap(Text)('Test Text')

    def handle_action(self, action, widget):
        widget.set_text(str(action))

    def test_correct_chain(self):
        self.km.bind('1 2 3', 'foo')
        self.widget.keypress((80,), '1')
        self.assertEqual(self.widget.text, 'Test Text')
        self.widget.keypress((80,), '2')
        self.assertEqual(self.widget.text, 'Test Text')
        self.widget.keypress((80,), '3')
        self.assertEqual(self.widget.text, 'foo')

    def test_incorrect_chain_then_correct_chain(self):
        self.km.bind('1 2 3', 'foo')
        self.widget.keypress((80,), '1')
        self.assertEqual(self.widget.text, 'Test Text')
        self.widget.keypress((80,), '2')
        self.assertEqual(self.widget.text, 'Test Text')
        self.widget.keypress((80,), 'x')
        self.assertEqual(self.widget.text, 'Test Text')
        self.widget.keypress((80,), '3')
        self.assertEqual(self.widget.text, 'Test Text')
        self.widget.keypress((80,), '1')
        self.widget.keypress((80,), '2')
        self.widget.keypress((80,), '3')
        self.assertEqual(self.widget.text, 'foo')

    def test_competing_chains(self):
        self.km.bind('1 2 3', 'foo')
        self.km.bind('1 2 0', 'bar')
        self.widget.keypress((80,), '1')
        self.widget.keypress((80,), '2')
        self.widget.keypress((80,), '3')
        self.assertEqual(self.widget.text, 'foo')
        self.widget.keypress((80,), '1')
        self.widget.keypress((80,), '2')
        self.widget.keypress((80,), '0')
        self.assertEqual(self.widget.text, 'bar')

    def test_competing_chains_with_different_lengths(self):
        self.km.bind('1 2 3', 'foo')
        self.km.bind('1 2 3 4', 'bar')
        self.widget.keypress((80,), '1')
        self.widget.keypress((80,), '2')
        self.widget.keypress((80,), '3')
        self.assertEqual(self.widget.text, 'foo')
        self.widget.keypress((80,), '1')
        self.widget.keypress((80,), '2')
        self.widget.keypress((80,), '3')
        self.widget.keypress((80,), '4')
        self.assertEqual(self.widget.text, 'foo')

    def test_abort_with_bound_key_has_no_action(self):
        self.km.bind('1 2 3', 'foo')
        self.km.bind('x', 'bar')
        self.widget.keypress((80,), '1')
        self.widget.keypress((80,), '2')
        self.widget.keypress((80,), 'x')
        self.widget.keypress((80,), '3')
        self.assertEqual(self.widget.text, 'Test Text')
        self.widget.keypress((80,), 'x')
        self.assertEqual(self.widget.text, 'bar')
