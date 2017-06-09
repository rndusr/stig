# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details
# http://www.gnu.org/licenses/gpl-3.0.txt

from ..logging import make_logger
log = make_logger(__name__)

import re
import blinker


class Key(str):
    """Key or key combination as string"""

    # Convert some urwid key names and some other stuff
    _INIT = (
        (re.compile(r'^<(.+)>$'),                    r'\1'),
        (re.compile(r'^(.*) $'),                     r'\1space'),
        (re.compile(r'^meta', flags=re.I),           r'alt'),
        (re.compile(r'\besc$', flags=re.I),       r'escape'),
        (re.compile(r'\bpos1$', flags=re.I),      r'home'),
        (re.compile(r'\bdel$', flags=re.I),       r'delete'),
        (re.compile(r'\bins$', flags=re.I),       r'insert'),
        (re.compile(r'\breturn$', flags=re.I),    r'enter'),
        (re.compile(r'\bpage up$', flags=re.I),   r'pgup'),
        (re.compile(r'\bpage down$', flags=re.I), r'pgdn'),
        (re.compile(r'\bpage dn$', flags=re.I),   r'pgdn'),
        (re.compile(r' '),                           r'-'),
        # The first part in key combos must always be the same, but the part
        # after must be preserved. <alt-l> is not the same as <alt-L>.
        (re.compile(r'^(\w+)-(\S+)$'),
         lambda m: m.group(1).lower()+'-'+m.group(2)),
    )

    _MODS = ('shift', 'alt', 'ctrl')
    _FKEYS = ('F1', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F8', 'F9', 'F10', 'F11', 'F12',
              'F13', 'F14', 'F15', 'F16', 'F17', 'F18', 'F19', 'F20')
    _KEYNAMES = ('escape', 'space', 'home', 'end', 'tab', 'delete', 'backspace', 'insert',
                 'enter', 'pgup', 'pgdn', 'left', 'right', 'up', 'down') + _FKEYS
    _cache = {}

    def __new__(cls, key):
        if isinstance(key, Key):
            return key
        elif key in cls._cache:
            return cls._cache[key]
        else:
            orig_key = key

        # Remove brackets (<>) around key, some renaming, etc.
        for regex,repl in cls._INIT:
            key = regex.sub(repl, key)

        # Split modifiers and key
        if '-' in key and len(key) > 1:
            _parts = key.split('-')
            key = _parts.pop(-1)
            mods = set(p.lower() for p in _parts)
            for mod in mods:
                if mod not in cls._MODS:
                    raise ValueError('Invalid modifier in <%s>: <%s>' % (orig_key, mod))

            if len(key) == 0:
                raise ValueError('Missing key after modifier: <%s>' % orig_key)

            # Convert <shift-x> to <X>
            elif len(key) == 1 and 'shift' in mods:
                key = key.upper()
                mods.remove('shift')

            # 'shift-/ctrl-E' is the same as 'shift-/ctrl-e'
            elif 'alt' not in mods:
                key = key.lower()
        else:
            mods = set()

        # Validate named keys ('enter', 'delete', etc)
        if len(key) > 1:
            # F* key names are upper case, all others lower case
            key_upper = key.upper()
            key = key_upper if key_upper in cls._FKEYS else key.lower()
            if key not in cls._KEYNAMES:
                raise ValueError('Unknown key name: %r' % key)

        if mods:
            keystr = '%s-%s' % ('-'.join(sorted(mods)), key)
        else:
            keystr = key

        if len(key) < 1:
            raise ValueError('No key specified')

        obj = super().__new__(cls, keystr)
        cls._cache[orig_key] = obj
        return obj

    def __str__(self):
        return '<%s>' % super().__str__()

    def __repr__(self):
        return '<Key %s>' % self


class KeyChain(tuple):
    class COMPLETED(): pass
    class ADVANCED(): pass
    class ABORTED(): pass
    class REFUSED(): pass

    def __new__(cls, *keys):
        obj = super().__new__(cls, (Key(k) for k in keys))
        if len(keys) < 2:
            raise ValueError('Not enough keys to make a chain: %s' % str(obj))
        return obj

    def __init__(self, *keys):
        self._pos = -1

    def feed(self, key):
        """Process `key`

        If `key` is expected, `advance` is called.  If that completes the
        chain, `reset` is called.

        If `key` is not expected, `reset` called.

        Return one of the constants:
          - COMPLETED: chain was completed with `key`
          - ADVANCED: chain was advanced with `key` but is not complete yet
          - REFUSED: `key` != `next_key` and `given` is empty
          - ABORTED: `key` != `next_key` and `given` is not empty
        """
        if self.next_key == key:
            log.debug('Advancing %r with %r', self, key)
            self.advance()
            if self.is_complete:
                self.reset()
                return self.COMPLETED
            else:
                return self.ADVANCED
        elif self._pos == -1:
            return self.REFUSED
        else:
            # log.debug('Expected %r, got %r', self.next_key, key)
            self.reset()
            return self.ABORTED

    def advance(self):
        """Look for next key in chain or call `reset` if complete"""
        if self.is_complete:
            log.debug('Completed %r', self)
            self.reset()
        else:
            self._pos += 1

    def reset(self):
        """Start looking for first key in chain"""
        self._pos = -1

    @property
    def next_key(self):
        """Next missing key or None if chain is already complete"""
        return None if self.is_complete else self[self._pos+1]

    def startswith(self, keys):
        """Whether this key chain starts with `keys` (sequence of Key instances)"""
        return self[:len(keys)] == tuple(keys)

    @property
    def given(self):
        """Tuple of keys we have so far"""
        return tuple(self) if self.is_complete else self[:self._pos+1]

    @property
    def is_complete(self):
        """Wether there are keys missing to complete the chain"""
        return self._pos >= len(self)-1

    @property
    def is_started(self):
        """Wether the first character has been supplied"""
        return self._pos > -1

    def __str__(self):
        return ' '.join(str(k) for k in self)

    def __repr__(self):
        text = ['<KeyChain %s' % str(self)]
        if self._pos > -1:
            text.append(' given=[')
            text.append(' '.join(str(k) for k in self.given))
            text.append(']')
        text.append('>')
        return ''.join(text)



class KeyMapped():
    """Mixin class that provides a keypress method"""
    def keypress(self, size, key):
        key = Key(key)

        sup = super()
        def try_super(key):
            if sup.selectable():
                key = sup.keypress(size, key)
            return key

        # Offer key to parent's keypress() for built-in keys like up/down
        key = try_super(key)

        # If parent doesn't want key, check if it is mapped
        if key is not None:
            key_eval = self.keymap.evaluate(key,
                                            context=self.context,
                                            callback=self.callback,
                                            widget=self)
            if key_eval is None:
                return None
            elif key_eval != key:
                # evaluate() may have resolved key to another key
                # (e.g. 'j' -> 'down')
                key = try_super(key_eval)

        return key

    def selectable(self):
        return True


NOCONTEXT = object()  # Another None value

class KeyMap():
    """Bind keys to actions in different contexts

    To bind keys to widgets, a new class is created that accepts user input by
    adding the methods `keypress` and `selectable` to the original class:

    >>> keymap = KeyMap()
    >>> keymap.bind(key='meta g',
                    action=lambda widget: widget.set_edit_text('abcfoo'),
                    context='pwentry')
    >>> Password = keymap.wrap(urwid.Edit, context='pwentry')
    >>> Password
    urwid.Edit_KeyMapped

    Now you can use Password like any regular Edit widget:

    >>> pw = Password('', 'Enter password or <Alt-g> to generate one')
    """

    def __init__(self, callback=None):
        self._default_callback = callback
        self._contexts = {None: {}}

        self._bindunbind_callbacks = blinker.Signal()
        self._keychain_callbacks = blinker.Signal()
        self._keychain_partial = []
        self._keychain_context = NOCONTEXT

    def clear(self):
        """Remove all keybindings"""
        contexts = self._contexts
        for context in contexts:
            log.debug('Removing all keybindings in context: %r', context)
            contexts[context] = {}
        self._bindunbind_callbacks.send(self)

    def bind(self, key, action, context=None):
        """Bind `key` to `action` in `context`

        key: a key string that is converted to Key or KeyChain with `mkkey`
        context: a descriptive string (or any other hashable object)
        action: What to do when `key` is pressed in `context`; may be:
                - a callable that accepts the widget that received `key`,
                - a Key object (so you can bind <j> to <down> for example),
                - any other object that is passed to the `callback` specified
                  in calls to `wrap` or when the KeyMap was instantiated.
        """
        key = self.mkkey(key)
        if isinstance(action, Key) and key == action:
            raise ValueError('Mapping {} to {} is silly'.format(key, action))

        if context not in self._contexts:
            self._contexts[context] = {}
        self._contexts[context][key] = action
        log.debug('%s: Mapped %r -> %r', context, key, action)
        self._bindunbind_callbacks.send(self)

    def unbind(self, key, context=None):
        """Unbind `key` in `context`

        Key chains starting with `key` are also removed.
        """
        key = self.mkkey(key)
        if context not in self._contexts:
            raise ValueError('Unknown context: {!r}'.format(context))
        elif key in self._contexts[context]:
            del self._contexts[context][key]
            log.debug('Unmapped %r [%s]', key, context)
        else:
            key_removed = False
            for k in tuple(self._contexts[context]):
                if isinstance(k, KeyChain) and k.startswith(key):
                    del self._contexts[context][k]
                    log.debug('Unmapped %r [%s]', k, context)
                    key_removed = True
            if not key_removed:
                msg = ('Key not mapped ',
                       ('in context %r' % context if context is not None else 'in default context'),
                       ': ', str(key))
                raise ValueError(''.join(msg))
        self._bindunbind_callbacks.send(self)

    def evaluate(self, key, context=None, callback=None, widget=None):
        """Run action that is bound to `key` in `context`

        key: the pressed key
        context: the context `key` was pressed in
        callback: None or any callable
        widget: the widget that received `key`
        """
        if context not in self._contexts:
            raise ValueError('Unknown context: {}'.format(context))

        key = Key(key)
        action = None
        log.debug('Evaluating %r in context %r for widget %r', key, context, widget)

        # Unless we've are already started a key chain, try to find a single-key mapping
        if not self._keychain_partial:
            action = self._get_single_key_action(key, context)
        else:
            log.debug('Not doing single-key lookup because we\'re '
                      'trying to complete a key chain')

        # Try to advance keychains only if no keychain was started previously
        # or if that previously started keychain was in the same context as
        # we're in now.
        if action is None and (self._keychain_context == NOCONTEXT or
                               self._keychain_context == context):
            action = self._get_keychain_action(key, context, self._keychain_partial)
            if action is KeyChain.ADVANCED:
                self._keychain_context = context    # Lock context
                self._keychain_partial.append(key)
                log.debug('%r was used to advance a keychain (status: %r)', key, self._keychain_partial)
                self._run_callbacks(tuple(self._active_keychains(context, self._keychain_partial)))
                return None
            elif action is KeyChain.ABORTED:
                log.debug('%r was used to abort a keychain', key)
                self._reset_keychains(context, self._keychain_partial)
                self._keychain_context = NOCONTEXT
                self._keychain_partial.clear()
                self._run_callbacks(tuple())
                return None
            elif action is KeyChain.REFUSED:
                log.debug('%r was refused by all keychains', key)
                self._keychain_context = NOCONTEXT
                self._keychain_partial.clear()
                action = None
            elif isinstance(action, Key):
                log.debug('%r was resolved to a single key: %r', key)
                self._keychain_context = NOCONTEXT
                self._keychain_partial.clear()
                self._run_callbacks(tuple())
            else:
                log.debug('%r was used to complete a keychain', key)
                self._keychain_context = NOCONTEXT
                self._keychain_partial.clear()
                self._run_callbacks(tuple())

        # Handle the action we found
        log.debug('Evaluated %r to action: %r', key, action)
        if action is None:
            log.debug('%r is not mapped in context %r', key, context)
            return key
        elif isinstance(action, Key):
            log.debug('Evaluating %r', action)
            return self.evaluate(action, context, callback, widget)
        elif isinstance(action, KeyChain):
            log.error('Mapping to key chains is not supported.')
            return None
        elif callable(action):
            # action itself is the callback
            log.debug('Calling action: %r', action)
            action(widget)
        elif callback is not None:
            # Individual callback for this widget
            log.debug('Calling widget callback %r with widget %r', callback, widget)
            callback(action, widget)
        elif self._default_callback is not None:
            # General callback for all widgets
            log.debug('Calling default callback %r with widget %r', self._default_callback, widget)
            self._default_callback(action, widget)
        else:
            raise TypeError('No callback given - unable to handle {!r}'.format(action))

    def _get_single_key_action(self, key, context):
        for keymap in (self._contexts[context], self._contexts[None]):
            if key in keymap:
                return keymap[key]

    def _get_keychain_action(self, key, context, partial_keys):
        # Go through all actions in this context and feed them the new key.
        action = KeyChain.ABORTED if partial_keys else KeyChain.REFUSED
        for kc,act in self._keychains(context, partial_keys):
            log.debug('   Feeding %r to %r', key, kc)
            result = kc.feed(key)

            # The first completed chain wins, we return its action and reset
            # all other chains.
            if result is KeyChain.COMPLETED:
                log.debug('%r completed %r', key, kc)
                self._reset_keychains(context, partial_keys)
                return act

            # At least this key chain was advanced.
            elif result is KeyChain.ADVANCED:
                log.debug('%r advanced %r', key, kc)
                action = KeyChain.ADVANCED

        if action is KeyChain.ADVANCED:
            log.debug('At least one key chain was advanced, returning %r', action)
        elif action is KeyChain.ABORTED:
            log.debug('No key chain was advanced or completed, returning %r', action)
        elif action is KeyChain.REFUSED:
            log.debug('%r did not start or advance a keychain, returning %r', key, action)
        else:
            log.debug('There should be no keychains in context %r: %r', context, tuple(self._keychains(context)))

        return action

    def _reset_keychains(self, context, partial_keys):
        for kc,action in self._keychains(context, partial_keys):
            kc.reset()

    def _keychains(self, context, partial_keys):
        for kc,action in self._contexts[context].items():
            if isinstance(kc, KeyChain) and kc.startswith(partial_keys):
                yield (kc, action)

    def _active_keychains(self, context, partial_keys):
        for kc,action in self._keychains(context, partial_keys):
            if kc.is_started:
                yield (kc, action)

    def _run_callbacks(self, active_keychains):
        log.debug('Running callbacks with %r', active_keychains)
        self._keychain_callbacks.send(active_keychains)

    def on_keychain(self, callback):
        self._keychain_callbacks.connect(callback, weak=True)

    def on_bind_unbind(self, callback):
        self._bindunbind_callbacks.connect(callback, weak=True)

    def wrap(self, cls, callback=None, context=None):
        """Return widget class that passes keypress()es through `evaluate`

        callback: Custom callable for this widget class; will be called with
                  the action bound to the key and the widget instance.
        context: A descriptive string (or any other hashable object)
        """
        if context not in self._contexts:
            self._contexts[context] = {}

        log.debug('Wrapping %r in %r with context %r', cls, KeyMapped, context)
        clsname = cls.__name__ + '_KeyMapped'
        return type(clsname,
                    (KeyMapped, cls),
                    {'keymap': self,
                     'context': context,
                     'callback': staticmethod(callback)})

    _KEY_SPLIT_SPACE = re.compile(r' +')
    def mkkey(self, string):
        """Create Key or KeyChain instance from `string`

        TODO: describe format
        """
        if isinstance(string, (Key, KeyChain)):
            return string
        elif ' ' in string:
            keys = (key for key in self._KEY_SPLIT_SPACE.split(string) if key)
            return KeyChain(*keys)
        elif '+' in string and len(string) >= 3:
            return KeyChain(*string.strip().split('+'))
        else:
            return Key(string)

    def keys(self, match_func=None, context=None):
        """Yield all keys where `match_func(key, action)` evaluates to True

        If `context` is not None, yield only keys mapped in that context.
        """
        def is_match(key, action):
            return match_func is None or match_func(key, action)

        if context is not None:
            for k,a in self._contexts[context].items():
                if is_match(k, a):
                    yield k
        else:
            for context in self.contexts:
                for k,a in self._contexts[context].items():
                    if is_match(k, a):
                        yield k

    def map(self, context=None):
        """Yield (key, action) tuples for keys mapped in `context`"""
        yield from self._contexts[context].items()

    @property
    def contexts(self):
        """Yield existing contexts"""
        yield from self._contexts
