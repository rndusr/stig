import unittest

import urwid

from stig.tui.keymap import Key, KeyChain, KeyMap

from .resources_tui import get_canvas_text


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
        self.assertEqual(Key('insert'), Key('ins'))

        self.assertEqual(Key('enter'), Key('return'))
        self.assertEqual(Key('enter'), Key('\n'))
        self.assertEqual(Key('alt-enter'), Key('meta-\n'))

        self.assertEqual(Key('alt-insert'), Key('meta ins'))
        self.assertEqual(Key('alt-del'), Key('meta delete'))
        self.assertEqual(Key('shift-ctrl-enter'), Key('shift-Ctrl-RETURN'))
        self.assertEqual(Key('alt-space'), Key('meta  '))
        self.assertEqual(Key('alt-pgup'), Key('meta page up'))

    def test_compare_Key_with_str(self):
        self.assertEqual(Key('enter'), '\n')
        self.assertEqual(Key('enter'), 'return')
        self.assertEqual(Key('pgdn'), 'page down')
        self.assertEqual(Key('pgup'), 'page up')
        self.assertEqual(Key('space'), ' ')
        self.assertEqual(Key('ins'), 'insert')
        self.assertEqual(Key('insert'), 'ins')

    def test_compare_Key_with_invalid_value(self):
        self.assertNotEqual(Key('space'), 'foo')
        self.assertNotEqual(Key('space'), range(10))

    def test_convert_shift_modifier(self):
        self.assertEqual(Key('shift-E'), Key('E'))
        self.assertEqual(Key('shift-e'), Key('E'))
        self.assertEqual(Key('shift-ö'), Key('Ö'))
        self.assertEqual(Key('shift-alt-ö'), Key('alt-Ö'))
        self.assertEqual(Key('ctrl-shift-alt-ö'), Key('ctrl-alt-Ö'))

    def test_convert_multiple_modifiers(self):
        self.assertEqual(Key('shift meta right'), Key('shift-alt-right'))
        self.assertEqual(Key('meta shift right'), Key('shift-alt-right'))
        self.assertEqual(Key('meta ctrl x'), Key('ctrl-alt-x'))
        self.assertEqual(Key('ctrl meta shift u'), Key('ctrl-meta-U'))

    def test_invalid_modifier(self):
        with self.assertRaises(ValueError) as cm:
            Key('shit-e')
        self.assertIn('Invalid modifier', str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            Key('alt-')
        self.assertIn('Missing key', str(cm.exception))

    def test_invalid_key(self):
        with self.assertRaises(ValueError) as cm:
            Key('hello')
        self.assertIn('Unknown key', str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            Key('alt-hello')
        self.assertIn('Unknown key', str(cm.exception))

        with self.assertRaises(ValueError) as cm:
            Key('')
        self.assertIn('No key', str(cm.exception))

        with self.assertRaises(TypeError) as cm:
            Key(object())
        self.assertIn('Not a string', str(cm.exception))


class TestKeyChain(unittest.TestCase):
    def test_minimum_number_of_keys(self):
        with self.assertRaises(ValueError) as cm:
            KeyChain('a')
        self.assertIn('Not enough keys', str(cm.exception))

    def test_equality(self):
        kc = KeyChain('F1', 'space', 'page down')
        self.assertEqual(kc, ('F1', 'space', 'page down'))
        self.assertEqual(kc, ['F1', ' ', 'pgdn'])
        self.assertEqual(kc, (k for k in ('F1', ' ', 'page down')))
        self.assertNotEqual(kc, ('F1', 'space', 'page down', 'X'))
        self.assertNotEqual(kc, ('F1', 'space'))
        self.assertNotEqual(kc, ('F1', 'space', 'X'))
        self.assertNotEqual(kc, ())

    def test_startswith(self):
        kc = KeyChain('a', 'b', 'c')
        self.assertTrue(kc.startswith(()))
        self.assertTrue(kc.startswith(('a',)))
        self.assertTrue(kc.startswith(('a', 'b')))
        self.assertTrue(kc.startswith(('a', 'b', 'c')))
        self.assertFalse(kc.startswith(('a', 'b', 'c', 'd')))
        self.assertFalse(kc.startswith(('a', 'b', 'X')))
        self.assertFalse(kc.startswith(('a', 'X')))
        self.assertFalse(kc.startswith(('X')))


class FakeAction():
    def __init__(self, action=None):
        self.callnum = 0
        self.action = action
        self.args = ()
        self.kwargs = {}

    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.callnum += 1
        if self.action is not None:
            return self.action()

class TestKeyMapped(unittest.TestCase):
    def setUp(self):
        self.keymap = KeyMap()

    def mk_widget(self, subcls, *args, context=None, callback=None, **kwargs):
        cls = self.keymap.wrap(subcls, context=context, callback=callback)
        return cls(*args, **kwargs)

    def assert_lines(self, widget, size, exp_lines, exp_focus_pos=None):
        canv = widget.render(size, focus=True)
        content = tuple(get_canvas_text(row) for row in canv.content())
        self.assertEqual(content, tuple(exp_lines))
        if exp_focus_pos is not None:
            self.assertEqual(widget.focus_position, exp_focus_pos)

    def test_hardcoded_keys_keep_working(self):
        list_contents = [urwid.Text(str(i)) for i in range(1, 10)]
        widget = self.mk_widget(urwid.ListBox, urwid.SimpleFocusListWalker(list_contents),
                                context='list')
        size = (3, 3)
        self.assert_lines(widget, size, exp_lines=('1  ', '2  ', '3  '))
        widget.keypress(size, 'down')
        self.assert_lines(widget, size, exp_lines=('2  ', '3  ', '4  '))
        widget.keypress(size, 'page down')
        self.assert_lines(widget, size, exp_lines=('5  ', '6  ', '7  '))
        widget.keypress(size, 'up')
        self.assert_lines(widget, size, exp_lines=('4  ', '5  ', '6  '))
        widget.keypress(size, 'page up')
        self.assert_lines(widget, size, exp_lines=('1  ', '2  ', '3  '))

    def test_non_hardcoded_keys_are_evaluated(self):
        list_contents = [urwid.Text(str(i)) for i in range(1, 10)]
        widget = self.mk_widget(urwid.ListBox, urwid.SimpleFocusListWalker(list_contents),
                                context='list')
        action = FakeAction()
        self.keymap.bind('a', context='list', action=action)
        size = (3, 3)
        self.assert_lines(widget, size, exp_lines=('1  ', '2  ', '3  '))
        widget.keypress(size, 'a')
        self.assert_lines(widget, size, exp_lines=('1  ', '2  ', '3  '))
        self.assertEqual(action.callnum, 1)
        self.assertEqual(action.args, (widget,))

    def test_evaluated_keys_are_offered_to_parent_again(self):
        list_contents = [urwid.Text(str(i)) for i in range(1, 10)]
        action = FakeAction()
        widget = self.mk_widget(urwid.ListBox, urwid.SimpleFocusListWalker(list_contents),
                                context='list', callback=action)
        self.keymap.bind('j', context='list', action=Key('down'))
        size = (3, 3)
        self.assert_lines(widget, size, exp_lines=('1  ', '2  ', '3  '))
        widget.keypress(size, 'j')
        self.assertEqual(action.callnum, 0)
        self.assert_lines(widget, size, exp_lines=('2  ', '3  ', '4  '))

    def test_evaluated_key_does_not_replace_original_key(self):
        # Create a list of widgets that translate 'j' to 'down' in their
        # keypress() methods.
        lst_contents = [self.mk_widget(urwid.Text, str(i), context='item')
                        for i in range(1, 10)]
        self.keymap.bind('j', context='item', action=Key('down'))

        # Create ListBox with separate key context.  If the ListBox gets to
        # handle 'j', it just checks a mark we can look for.
        lst_widget = self.mk_widget(urwid.ListBox, urwid.SimpleFocusListWalker(lst_contents), context='list')
        lst_got_j = FakeAction()
        self.keymap.bind('j', context='list', action=lst_got_j)

        # Make sure everything works regularly
        size = (3, 3)
        self.assert_lines(lst_widget, size, exp_lines=('1  ', '2  ', '3  '), exp_focus_pos=0)
        lst_widget.keypress(size, 'down')
        self.assert_lines(lst_widget, size, exp_lines=('1  ', '2  ', '3  '), exp_focus_pos=1)

        # Do the actual test: Pressing 'j' should pass 'j' to the focused item,
        # which evaluates it to 'down'.  But the list widget must get 'j'.
        lst_widget.keypress(size, 'j')
        self.assert_lines(lst_widget, size, exp_lines=('1  ', '2  ', '3  '), exp_focus_pos=1)
        self.assertEqual(lst_got_j.callnum, 1)


class TestKeyMap(unittest.TestCase):
    def setUp(self):
        self.km = KeyMap()

    def test_clear_all_contexts(self):
        self.km.bind(key='a', action='1', context='x')
        self.km.bind(key='b', action='2', context='y')
        self.km.bind(key='c', action='3', context='z')
        import sys
        if sys.hexversion < 0x03060000:
            # Python <= 3.6 dicts are not ordered yet
            self.assertEqual(set(self.km.keys()), {'a', 'b', 'c'})
        else:
            self.assertEqual(tuple(self.km.keys()), ('a', 'b', 'c'))
        self.km.clear()
        self.assertEqual(tuple(self.km.keys()), ())

    def test_clear_context(self):
        self.km.bind(key='a', action='1', context='x')
        self.km.bind(key='b', action='2', context='y')
        self.km.bind(key='c', action='3', context='z')
        import sys
        if sys.hexversion < 0x03060000:
            # Python <= 3.6 dicts are not ordered yet
            self.assertEqual(set(self.km.keys()), {'a', 'b', 'c'})
        else:
            self.assertEqual(tuple(self.km.keys()), ('a', 'b', 'c'))
        self.km.clear(context='x')
        if sys.hexversion < 0x03060000:
            # Python <= 3.6 dicts are not ordered yet
            self.assertEqual(set(self.km.keys()), {'b', 'c'})
        else:
            self.assertEqual(tuple(self.km.keys()), ('b', 'c'))
        self.km.clear(context='y')
        self.assertEqual(tuple(self.km.keys()), ('c',))
        self.km.clear(context='z')
        self.assertEqual(tuple(self.km.keys()), ())


class TestKeyMap_with_single_keys(unittest.TestCase):
    def setUp(self):
        self.km = KeyMap()

    def test_unbind(self):
        self.km.bind(key='a', action='foo')
        self.assertIn(Key('a'), self.km.keys())
        self.km.unbind(key='a')
        self.assertNotIn(Key('a'), self.km.keys())

        self.km.bind(key='b', action='foo')
        with self.assertRaises(ValueError) as cm:
            self.km.unbind(key='c')
        self.assertIn("Key not mapped in context 'default'", str(cm.exception))
        self.assertIn(str(Key('c')), str(cm.exception))

        self.km.bind(key='d', action='foo')
        with self.assertRaises(ValueError) as cm:
            self.km.unbind(key='d', context='bar')
        self.assertIn("Unknown context: 'bar'", str(cm.exception))

        self.km.bind(key='e', action='foo', context='kablam')
        with self.assertRaises(ValueError) as cm:
            self.km.unbind(key='e')
        self.assertIn("Key not mapped in context 'default'", str(cm.exception))
        self.assertIn(str(Key('e')), str(cm.exception))

    def test_mkkey(self):
        self.assertEqual(self.km.mkkey(Key('x')), Key('x'))
        self.assertEqual(self.km.mkkey(KeyChain('1', '2', '3')),
                         KeyChain('1', '2', '3'))

        self.assertEqual(self.km.mkkey('x'), Key('x'))
        self.assertEqual(self.km.mkkey('x y z'), KeyChain('x', 'y', 'z'))
        self.assertEqual(self.km.mkkey('x+y+z'), KeyChain('x', 'y', 'z'))
        self.assertEqual(self.km.mkkey('x +'), KeyChain('x', '+'))
        self.assertEqual(self.km.mkkey('+ x'), KeyChain('+', 'x'))
        self.assertEqual(self.km.mkkey('x y +'), KeyChain('x', 'y', '+'))
        self.assertEqual(self.km.mkkey('+ y z'), KeyChain('+', 'y', 'z'))
        self.assertEqual(self.km.mkkey('+ + +'), KeyChain('+', '+', '+'))

    def test_circular_bind_detection(self):
        with self.assertRaises(ValueError) as cm:
            self.km.bind(key='a', action=self.km.mkkey('a'))
        self.assertIn('Circular', str(cm.exception))
        self.assertIn('<a>', str(cm.exception))

    def test_key_translation(self):
        widget = self.km.wrap(urwid.Text)('Test Text')
        self.km.bind(key='a',
                     action=lambda widget: widget.set_text('Key pressed: a'))
        self.km.bind(key='b', action=Key('a'))
        widget.keypress((80,), 'b')
        self.assertEqual(widget.text, 'Key pressed: a')

    def test_key_translation_to_builtin_key(self):
        class SelectableText(urwid.Text):
            def selectable(self): return True
            def keypress(self, size, key): return key
        list_contents = [SelectableText(str(i)) for i in range(1, 10)]
        listw = self.km.wrap(urwid.ListBox, context='list')(urwid.SimpleFocusListWalker(list_contents))
        self.km.bind(key='j', action=Key('down'))
        self.assertEqual(listw.focus_position, 0)
        listw.keypress((3, 3), 'j')
        self.assertEqual(listw.focus_position, 1)

    def test_action_is_callback(self):
        self.km.bind(key='a',
                     action=lambda widget: widget.set_text('foo'))
        widget = self.km.wrap(urwid.Text)('Test Text')
        widget.keypress((80,), 'a')
        self.assertEqual(widget.text, 'foo')

    def test_widget_callback(self):
        def cb(action, widget):
            widget.set_text(action)

        self.km.bind(key='a', action='foo')
        widget = self.km.wrap(urwid.Text, callback=cb)('Test Text')
        widget.keypress((80,), 'a')
        self.assertEqual(widget.text, 'foo')

    def test_default_callback(self):
        def cb(action, widget):
            widget.set_text(action)

        self.km = KeyMap(callback=cb)
        self.km.bind(key='a', action='foo')
        widget = self.km.wrap(urwid.Text)('Test Text')
        widget.keypress((80,), 'a')
        self.assertEqual(widget.text, 'foo')

    def test_widget_callback_overrides_default_callback(self):
        def default_cb(action, widget):
            widget.set_text(action)

        def widget_cb(action, widget):
            widget.set_text(action.upper())

        self.km = KeyMap(callback=default_cb)
        self.km.bind(key='a', action='foo')
        widget = self.km.wrap(urwid.Text, callback=widget_cb)('Test Text')
        widget.keypress((80,), 'a')
        self.assertEqual(widget.text, 'FOO')


class TestKeyMap_with_keychains(unittest.TestCase):
    def setUp(self):
        self.km = KeyMap(callback=self.handle_action)
        self.widget = self.km.wrap(urwid.Edit)('', 'Original Text')
        self.km.on_keychain(self.handle_keychain_changed)
        self._action_counter = 0

    def handle_action(self, action, widget):
        self._action_counter += 1
        widget.set_edit_text('%s%d' % (str(action), self._action_counter))

    def handle_keychain_changed(self, keymap, context, active_keychains, keys_given):
        self.active_keychains = set(active_keychains)

    def assert_status(self, active_keychains=(), keys_given=(), widget_text=None):
        self.assertEqual(self.active_keychains, set(active_keychains))
        self.assertEqual(self.km.current_keychain, tuple(keys_given))
        self.assertEqual(self.widget.text, widget_text)


    def test_any_keychain_started(self):
        def cb(*args, **kwargs): pass
        self.km.bind(key='a+b+c', action='foo')
        self.assertFalse(self.km.any_keychain_started)
        self.km.evaluate('a', callback=cb)
        self.assertTrue(self.km.any_keychain_started)
        self.km.evaluate('b', callback=cb)
        self.assertTrue(self.km.any_keychain_started)
        self.km.evaluate('c', callback=cb)
        self.assertFalse(self.km.any_keychain_started)

    def test_unbind(self):
        kc = '1 2 3'
        for keys in ('1', '1 2', '1 2 3'):
            self.km.bind(kc, 'foo')
            self.assertIn(KeyChain('1', '2', '3'), self.km.keys())
            self.km.unbind(keys)
            self.assertNotIn(KeyChain('1', '2', '3'), self.km.keys())

        for keys in ('1 3', '1 2 4', '1 2 3 4', '2', '3', '2 1', '3 2 1'):
            self.km.bind(kc, 'foo')
            self.assertIn(KeyChain('1', '2', '3'), self.km.keys())
            with self.assertRaises(ValueError) as cm:
                self.km.unbind(keys)
            self.assertIn('Key not mapped in context', str(cm.exception))
            self.assertIn(str(self.km.mkkey(keys)), str(cm.exception))

    def test_complete_chain(self):
        self.km.bind('alt-1 alt-2 alt-3', 'foo')

        self.widget.keypress((80,), 'alt-1')
        self.assert_status(keys_given=('alt-1',),
                           widget_text='Original Text',
                           active_keychains=((('alt-1', 'alt-2', 'alt-3'), 'foo'),))

        self.widget.keypress((80,), 'alt-2')
        self.assert_status(keys_given=('alt-1', 'alt-2'),
                           widget_text='Original Text',
                           active_keychains=((('alt-1', 'alt-2', 'alt-3'), 'foo'),))

        self.widget.keypress((80,), 'alt-3')
        self.assert_status(keys_given=(),
                           widget_text='foo1',
                           active_keychains=())

    def test_reverse_chain_with_backspace(self):
        self.km.bind('alt-1 alt-f alt-x', 'foo')
        self.km.bind('alt-1 alt-b alt-x', 'bar')

        self.widget.keypress((80,), 'alt-1')
        self.assert_status(keys_given=('alt-1',),
                           widget_text='Original Text',
                           active_keychains=((('alt-1', 'alt-f', 'alt-x'), 'foo'),
                                             (('alt-1', 'alt-b', 'alt-x'), 'bar')))

        self.widget.keypress((80,), 'alt-f')
        self.assert_status(keys_given=('alt-1', 'alt-f'),
                           widget_text='Original Text',
                           active_keychains=((('alt-1', 'alt-f', 'alt-x'), 'foo'),))

        self.widget.keypress((80,), 'backspace')
        self.assert_status(keys_given=('alt-1',),
                           widget_text='Original Text',
                           active_keychains=((('alt-1', 'alt-f', 'alt-x'), 'foo'),
                                             (('alt-1', 'alt-b', 'alt-x'), 'bar')))

        self.widget.keypress((80,), 'alt-b')
        self.assert_status(keys_given=('alt-1', 'alt-b'),
                           widget_text='Original Text',
                           active_keychains=((('alt-1', 'alt-b', 'alt-x'), 'bar'),))

        self.widget.keypress((80,), 'alt-x')
        self.assert_status(keys_given=(),
                           widget_text='bar1',
                           active_keychains=())

    def test_binding_backspace(self):
        self.km.bind('alt-1 backspace', 'foo')

        self.widget.keypress((80,), 'alt-1')
        self.assert_status(keys_given=('alt-1',),
                           widget_text='Original Text',
                           active_keychains=((('alt-1', 'backspace'), 'foo'),))

        self.widget.keypress((80,), 'backspace')
        self.assert_status(keys_given=(),
                           widget_text='foo1',
                           active_keychains=())

    def test_abort_chain_with_unmapped_key(self):
        self.km.bind('alt-1 alt-2 alt-3', 'foo')

        self.widget.keypress((80,), 'alt-1')
        self.assert_status(keys_given=('alt-1',),
                           widget_text='Original Text',
                           active_keychains=((('alt-1', 'alt-2', 'alt-3'), 'foo'),))

        self.widget.keypress((80,), 'alt-x')
        self.assert_status(keys_given=(),
                           widget_text='Original Text',
                           active_keychains=())

    def test_abort_chain_with_mapped_key(self):
        self.km.bind('alt-1 alt-2 alt-3', 'foo')
        self.km.bind('alt-x', 'bar')

        self.widget.keypress((80,), 'alt-1')
        self.assert_status(keys_given=('alt-1',),
                           widget_text='Original Text',
                           active_keychains=((('alt-1', 'alt-2', 'alt-3'), 'foo'),))

        # Abort the started chain
        self.widget.keypress((80,), 'alt-x')
        self.assert_status(keys_given=(),
                           widget_text='Original Text',
                           active_keychains=())

        # Mapped single-key evaluation works again
        self.widget.keypress((80,), 'alt-x')
        self.assert_status(keys_given=(),
                           widget_text='bar1',
                           active_keychains=())

    def test_abort_chain_with_builtin_key(self):
        self.km.bind('alt-1 alt-2 alt-3', 'foo')

        self.widget.keypress((80,), 'alt-1')
        self.assert_status(keys_given=('alt-1',),
                           widget_text='Original Text',
                           active_keychains=((('alt-1', 'alt-2', 'alt-3'), 'foo'),))

        # This would usually append 'x' to the Edit widget text, but we want it
        # to abort the started chain instead.
        self.widget.keypress((80,), 'x')
        self.assert_status(keys_given=(),
                           widget_text='Original Text',
                           active_keychains=())

        # Now we can change the text again
        self.widget.keypress((80,), 'x')
        self.assert_status(keys_given=(),
                           widget_text='Original Textx',
                           active_keychains=())

    def test_competing_chains(self):
        self.km.bind('alt-1 alt-2 alt-a', 'foo')
        self.km.bind('alt-1 alt-2 alt-b', 'bar')

        self.widget.keypress((80,), 'alt-1')
        self.assert_status(keys_given=('alt-1',),
                           widget_text='Original Text',
                           active_keychains=((('alt-1', 'alt-2', 'alt-a'), 'foo'),
                                             (('alt-1', 'alt-2', 'alt-b'), 'bar')))

        self.widget.keypress((80,), 'alt-2')
        self.assert_status(keys_given=('alt-1', 'alt-2'),
                           widget_text='Original Text',
                           active_keychains=((('alt-1', 'alt-2', 'alt-a'), 'foo'),
                                             (('alt-1', 'alt-2', 'alt-b'), 'bar')))

        self.widget.keypress((80,), 'alt-a')
        self.assert_status(keys_given=(),
                           widget_text='foo1',
                           active_keychains=())

        self.widget.keypress((80,), 'alt-1')
        self.assert_status(keys_given=('alt-1',),
                           widget_text='foo1',
                           active_keychains=((('alt-1', 'alt-2', 'alt-a'), 'foo'),
                                             (('alt-1', 'alt-2', 'alt-b'), 'bar')))

        self.widget.keypress((80,), 'alt-2')
        self.assert_status(keys_given=('alt-1', 'alt-2'),
                           widget_text='foo1',
                           active_keychains=((('alt-1', 'alt-2', 'alt-a'), 'foo'),
                                             (('alt-1', 'alt-2', 'alt-b'), 'bar')))

        self.widget.keypress((80,), 'alt-b')
        self.assert_status(keys_given=(),
                           widget_text='bar2',
                           active_keychains=())


class TestKeyMap_with_nested_widgets(unittest.TestCase):
    def setUp(self):
        self.km = KeyMap(callback=self.handle_action)
        self.km.on_keychain(self.handle_keychain_changed)
        self.last_action = None
        self.action_widget = None
        self.action_counter = 0
        self.active_keychains = set()

        # Create a Pile of two ListBoxes with some Text items
        def mk_item(widgetcls, i, context):
            return self.km.wrap(widgetcls, context=context)('%s: %s' % (context, i))
        self.listw1 = self.km.wrap(urwid.ListBox, context='list1')(
            urwid.SimpleFocusListWalker([mk_item(urwid.Text, i, context='item1')
                                         for i in range(1, 10)])
        )
        self.listw2 = self.km.wrap(urwid.ListBox, context='list2')(
            urwid.SimpleFocusListWalker([mk_item(urwid.Edit, i, context='item2')
                                         for i in range(100, 1000, 100)])
        )
        self.mainw = self.km.wrap(urwid.Pile, context='main')([self.listw1, self.listw2])

        self.km.bind('A',     'A in main',   context='main')
        self.km.bind('B',     'B in main',   context='main')
        self.km.bind('1 2 A', '12A in main', context='main')
        self.km.bind('1 2 B', '12B in main', context='main')

        self.km.bind('C',     'C in list1',   context='list1')
        self.km.bind('D',     'D in list1',   context='list1')
        self.km.bind('2 3 A', '23A in list1', context='list1')
        self.km.bind('2 3 B', '23B in list1', context='list1')

        self.km.bind('C',     'C in list2',   context='list2')
        self.km.bind('D',     'D in list2',   context='list2')
        self.km.bind('2 3 A', '23A in list2', context='list2')
        self.km.bind('2 3 B', '23B in list2', context='list2')

        self.km.bind('E',     'E in item1',   context='item1')
        self.km.bind('F',     'F in item1',   context='item1')
        self.km.bind('3 4 A', '34A in item1', context='item1')
        self.km.bind('3 4 B', '34B in item1', context='item1')

        self.km.bind('E',     'E in item2',   context='item2')
        self.km.bind('F',     'F in item2',   context='item2')
        self.km.bind('3 4 A', '34A in item2', context='item2')
        self.km.bind('3 4 B', '34B in item2', context='item2')


    def handle_action(self, action, widget):
        self.last_action = action
        self.action_counter += 1
        self.action_widget = widget

    def handle_keychain_changed(self, keymap, context, active_keychains, keys_given):
        self.active_keychains = set(active_keychains)

    def press_key(self, key):
        self.mainw.keypress((80, 25), key)


    def assert_active_keychains(self, *active_keychains):
        self.assertEqual(self.active_keychains, set(active_keychains))

    def assert_current_keychain(self, *keys):
        # If there are no active keychains, we don't want this test to pass if
        # given keys are expected.
        ak = tuple(self.active_keychains)
        if len(keys) < 1:
            self.assertEqual(ak, ())
        else:
            self.assertEqual(self.km.current_keychain, keys)

    def assert_action(self, exp_action=None, exp_count=0, exp_widget=None):
        self.assertEqual(self.last_action, exp_action)
        self.assertEqual(self.action_counter, exp_count)
        self.assertEqual(self.action_widget, exp_widget)


    def test_mapped_singlekeys_in_main_context(self):
        self.press_key('A')
        self.assert_current_keychain()
        self.assert_action(exp_action='A in main', exp_count=1, exp_widget=self.mainw)
        self.assert_active_keychains()

        self.press_key('B')
        self.assert_current_keychain()
        self.assert_action(exp_action='B in main', exp_count=2, exp_widget=self.mainw)
        self.assert_active_keychains()


    def test_mapped_singlekeys_in_list_with_Text_widgets(self):
        self.mainw.focus_position = 0

        self.press_key('C')
        self.assert_current_keychain()
        self.assert_action(exp_action='C in list1', exp_count=1, exp_widget=self.listw1)
        self.assert_active_keychains()

        self.press_key('D')
        self.assert_current_keychain()
        self.assert_action(exp_action='D in list1', exp_count=2, exp_widget=self.listw1)
        self.assert_active_keychains()

    def test_mapped_singlekeys_in_list_with_Edit_widgets(self):
        self.mainw.focus_position = 1

        self.press_key('C')
        self.assertEqual(self.mainw.focus.focus.edit_text, 'C')
        self.assert_current_keychain()
        self.assert_action(exp_action=None, exp_count=0, exp_widget=None)
        self.assert_active_keychains()

        self.press_key('D')
        self.assertEqual(self.mainw.focus.focus.edit_text, 'CD')
        self.assert_current_keychain()
        self.assert_action(exp_action=None, exp_count=0, exp_widget=None)
        self.assert_active_keychains()


    def test_mapped_singlekeys_in_Text_widget(self):
        self.mainw.focus_position = 0
        self.press_key('E')
        self.assert_current_keychain()
        self.assert_action(exp_action='E in item1', exp_count=1, exp_widget=self.listw1.focus)
        self.assert_active_keychains()

        self.press_key('F')
        self.assert_current_keychain()
        self.assert_action(exp_action='F in item1', exp_count=2, exp_widget=self.listw1.focus)
        self.assert_active_keychains()

    def test_mapped_singlekeys_in_Edit_widget(self):
        self.mainw.focus_position = 1

        self.press_key('E')
        self.assertEqual(self.mainw.focus.focus.edit_text, 'E')
        self.assert_current_keychain()
        self.assert_action(exp_action=None, exp_count=0, exp_widget=None)
        self.assert_active_keychains()

        self.press_key('F')
        self.assertEqual(self.mainw.focus.focus.edit_text, 'EF')
        self.assert_current_keychain()
        self.assert_action(exp_action=None, exp_count=0, exp_widget=None)
        self.assert_active_keychains()


    def test_unmapped_singlekeys(self):
        self.press_key('Z')
        self.assert_current_keychain()
        self.assert_action(exp_action=None, exp_count=0, exp_widget=None)
        self.assert_active_keychains()


    def test_keychain_in_main_context(self):
        def start_keychain(exp_action, exp_count, exp_widget):
            self.press_key('1')
            self.assert_current_keychain('1')
            self.assert_action(exp_action=exp_action, exp_count=exp_count, exp_widget=exp_widget)
            self.assert_active_keychains((('1', '2', 'A'), '12A in main'),
                                         (('1', '2', 'B'), '12B in main'))
            self.press_key('2')
            self.assert_current_keychain('1', '2')
            self.assert_action(exp_action=exp_action, exp_count=exp_count, exp_widget=exp_widget)
            self.assert_active_keychains((('1', '2', 'A'), '12A in main'),
                                         (('1', '2', 'B'), '12B in main'))

        start_keychain(exp_action=None, exp_count=0, exp_widget=None)
        self.press_key('A')
        self.assert_action(exp_action='12A in main', exp_count=1, exp_widget=self.mainw)
        self.assert_current_keychain()
        self.assert_active_keychains()

        start_keychain(exp_action='12A in main', exp_count=1, exp_widget=self.mainw)
        self.press_key('B')
        self.assert_action(exp_action='12B in main', exp_count=2, exp_widget=self.mainw)
        self.assert_current_keychain()
        self.assert_active_keychains()


    def test_keychain_in_list1_context(self):
        self.mainw.focus_position = 0

        def start_keychain(exp_action, exp_count, exp_widget):
            self.press_key('2')
            self.assert_current_keychain('2')
            self.assert_action(exp_action=exp_action, exp_count=exp_count, exp_widget=exp_widget)
            self.assert_active_keychains((('2', '3', 'A'), '23A in list1'),
                                         (('2', '3', 'B'), '23B in list1'))
            self.press_key('3')
            self.assert_current_keychain('2', '3')
            self.assert_action(exp_action=exp_action, exp_count=exp_count, exp_widget=exp_widget)
            self.assert_active_keychains((('2', '3', 'A'), '23A in list1'),
                                         (('2', '3', 'B'), '23B in list1'))

        start_keychain(exp_action=None, exp_count=0, exp_widget=None)
        self.press_key('A')
        self.assert_action(exp_action='23A in list1', exp_count=1, exp_widget=self.listw1)
        self.assert_current_keychain()
        self.assert_active_keychains()

        start_keychain(exp_action='23A in list1', exp_count=1, exp_widget=self.listw1)
        self.press_key('B')
        self.assert_action(exp_action='23B in list1', exp_count=2, exp_widget=self.listw1)
        self.assert_current_keychain()
        self.assert_active_keychains()

    def test_keychain_in_item1_context(self):
        self.mainw.focus_position = 0

        def start_keychain(exp_action, exp_count, exp_widget):
            self.press_key('3')
            self.assert_current_keychain('3')
            self.assert_action(exp_action=exp_action, exp_count=exp_count, exp_widget=exp_widget)
            self.assert_active_keychains((('3', '4', 'A'), '34A in item1'),
                                         (('3', '4', 'B'), '34B in item1'))
            self.press_key('4')
            self.assert_current_keychain('3', '4')
            self.assert_action(exp_action=exp_action, exp_count=exp_count, exp_widget=exp_widget)
            self.assert_active_keychains((('3', '4', 'A'), '34A in item1'),
                                         (('3', '4', 'B'), '34B in item1'))

        start_keychain(exp_action=None, exp_count=0, exp_widget=None)
        self.press_key('A')
        self.assert_action(exp_action='34A in item1', exp_count=1, exp_widget=self.listw1.focus)
        self.assert_current_keychain()
        self.assert_active_keychains()

        start_keychain(exp_action='34A in item1', exp_count=1, exp_widget=self.listw1.focus)
        self.press_key('B')
        self.assert_action(exp_action='34B in item1', exp_count=2, exp_widget=self.listw1.focus)
        self.assert_current_keychain()
        self.assert_active_keychains()


    def test_keychain_in_list2_context(self):
        self.mainw.focus_position = 1

        text = ''

        def press_key(key):
            nonlocal text
            text += key
            self.press_key(key)

        def start_keychain():
            for key in ('2', '3'):
                press_key(key)
                self.assertEqual(self.listw2.focus.edit_text, text)
                self.assert_current_keychain()
                self.assert_action(exp_action=None, exp_count=0, exp_widget=None)
                self.assert_active_keychains()

        for key in ('A', 'B'):
            start_keychain()
            press_key(key)
            self.assertEqual(self.listw2.focus.edit_text, text)
            self.assert_current_keychain()
            self.assert_action(exp_action=None, exp_count=0, exp_widget=None)
            self.assert_active_keychains()

    def test_keychain_in_item2_context(self):
        self.mainw.focus_position = 1

        text = ''
        def press_key(key):  # noqa: E306
            nonlocal text
            text += key
            self.press_key(key)

        def start_keychain():
            for key in ('3', '4'):
                press_key(key)
                self.assertEqual(self.listw2.focus.edit_text, text)
                self.assert_current_keychain()
                self.assert_action(exp_action=None, exp_count=0, exp_widget=None)
                self.assert_active_keychains()

        for key in ('A', 'B'):
            start_keychain()
            press_key(key)
            self.assertEqual(self.listw2.focus.edit_text, text)
            self.assert_current_keychain()
            self.assert_action(exp_action=None, exp_count=0, exp_widget=None)
            self.assert_active_keychains()


    def test_abort_chain_with_builtin_key(self):
        def start_keychain(exp_action, exp_count, exp_widget):
            self.press_key('1')
            self.assert_current_keychain('1')
            self.assert_action(exp_action=exp_action, exp_count=exp_count, exp_widget=exp_widget)
            self.assert_active_keychains((('1', '2', 'A'), '12A in main'),
                                         (('1', '2', 'B'), '12B in main'))
            self.press_key('2')
            self.assert_current_keychain('1', '2')
            self.assert_action(exp_action=exp_action, exp_count=exp_count, exp_widget=exp_widget)
            self.assert_active_keychains((('1', '2', 'A'), '12A in main'),
                                         (('1', '2', 'B'), '12B in main'))

        start_keychain(exp_action=None, exp_count=0, exp_widget=None)
        self.press_key('down')
        self.assert_action(exp_action=None, exp_count=0, exp_widget=None)
        self.assert_current_keychain()
        self.assert_active_keychains()

    def test_abort_chain_with_mapped_key(self):
        self.km.bind('x', 'x in main', context='main')

        def start_keychain(exp_action, exp_count, exp_widget):
            self.press_key('1')
            self.assert_current_keychain('1')
            self.assert_action(exp_action=exp_action, exp_count=exp_count, exp_widget=exp_widget)
            self.assert_active_keychains((('1', '2', 'A'), '12A in main'),
                                         (('1', '2', 'B'), '12B in main'))
            self.press_key('2')
            self.assert_current_keychain('1', '2')
            self.assert_action(exp_action=exp_action, exp_count=exp_count, exp_widget=exp_widget)
            self.assert_active_keychains((('1', '2', 'A'), '12A in main'),
                                         (('1', '2', 'B'), '12B in main'))

        start_keychain(exp_action=None, exp_count=0, exp_widget=None)
        self.press_key('x')
        self.assert_action(exp_action=None, exp_count=0, exp_widget=None)
        self.assert_current_keychain()
        self.assert_active_keychains()

    def test_abort_chain_with_unmapped_key(self):
        def start_keychain(exp_action, exp_count, exp_widget):
            self.press_key('1')
            self.assert_current_keychain('1')
            self.assert_action(exp_action=exp_action, exp_count=exp_count, exp_widget=exp_widget)
            self.assert_active_keychains((('1', '2', 'A'), '12A in main'),
                                         (('1', '2', 'B'), '12B in main'))
            self.press_key('2')
            self.assert_current_keychain('1', '2')
            self.assert_action(exp_action=exp_action, exp_count=exp_count, exp_widget=exp_widget)
            self.assert_active_keychains((('1', '2', 'A'), '12A in main'),
                                         (('1', '2', 'B'), '12B in main'))

        start_keychain(exp_action=None, exp_count=0, exp_widget=None)
        self.press_key('x')
        self.assert_action(exp_action=None, exp_count=0, exp_widget=None)
        self.assert_current_keychain()
        self.assert_active_keychains()


    def test_builtin_keys_have_precedence_over_keychain_if_no_keychain_started(self):
        self.km.bind('z', 'impossible action', context='list2')  # This should go to an Edit widget
        self.mainw.focus_position = 1  # Focus list2
        self.press_key('z')
        self.assert_current_keychain()
        self.assert_action(exp_action=None, exp_count=0, exp_widget=None)
        self.assert_active_keychains()
        self.assertEqual(self.listw2.focus.edit_text, 'z')

    def test_chain_with_builtin_key_if_parent_needs_it(self):
        self.km.bind('up down', 'jump', context='list1')

        # Make sure parent uses 'up' key to move focus up
        self.listw1.focus_position = 1

        self.press_key('up')
        self.assertEqual(self.listw1.focus_position, 0)
        self.assert_current_keychain()
        self.assert_action(exp_action=None, exp_count=0, exp_widget=None)
        self.assert_active_keychains()

    def test_chain_with_builtin_key_if_parent_doesnt_need_it(self):
        self.km.bind('up down', 'jump', context='list1')

        # Make sure parent doesn't need 'up' key
        self.listw1.focus_position = 0

        self.press_key('up')
        self.assert_current_keychain('up')
        self.assert_action(exp_action=None, exp_count=0, exp_widget=None)
        self.assert_active_keychains((('up', 'down'), 'jump'))
        self.press_key('down')
        self.assert_current_keychain()
        self.assert_action(exp_action='jump', exp_count=1, exp_widget=self.listw1)
        self.assert_active_keychains()
