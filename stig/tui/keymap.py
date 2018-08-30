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
        (re.compile(r'^<(.+)>$'),                            r'\1'),
        (re.compile(r'^(.*) $'),                             r'\1space'),
        (re.compile(r'^meta', flags=re.I),                   r'alt'),
        (re.compile(r'\besc$', flags=re.I),                  r'escape'),
        (re.compile(r'\bpos1$', flags=re.I),                 r'home'),
        (re.compile(r'\bdel$', flags=re.I),                  r'delete'),
        (re.compile(r'\bins$', flags=re.I),                  r'insert'),
        (re.compile(r'(\b|\W*)(?:return|\n)$', flags=re.I),  r'\1enter'),
        (re.compile(r'\bpage up$', flags=re.I),              r'pgup'),
        (re.compile(r'\bpage down$', flags=re.I),            r'pgdn'),
        (re.compile(r'\bpage dn$', flags=re.I),              r'pgdn'),
        (re.compile(r' '),                                   r'-'),
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
        elif not isinstance(key, str):
            raise TypeError('Not a string: %r' % key)
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
                raise ValueError('Unknown key: %r' % key)

        if mods:
            keystr = '%s-%s' % ('-'.join(sorted(mods)), key)
        else:
            keystr = key

        if len(key) < 1:
            raise ValueError('No key specified')

        obj = super().__new__(cls, keystr)
        cls._cache[orig_key] = obj
        return obj

    def __eq__(self, other):
        if not isinstance(other, Key):
            try:
                other = Key(other)
            except (ValueError, TypeError):
                return False
        return super().__eq__(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return super().__hash__()

    def __str__(self):
        return '<%s>' % super().__str__()

    def __repr__(self):
        return '<Key %s>' % super().__str__()


class KeyChain(tuple):
    ADVANCE = '<ADVANCE>'
    REDUCE  = '<REDUCE>'
    REJECT  = '<REJECT>'
    ABORT   = '<ABORT>'

    def __new__(cls, *keys):
        obj = super().__new__(cls, (Key(k) for k in keys))
        if len(keys) < 2:
            raise ValueError('Not enough keys to make a chain: %s' % str(obj))
        return obj

    def startswith(self, keys):
        """Whether this key chain starts with `keys` (sequence of Key instances)"""
        keys_ = tuple(keys)
        len_keys_ = len(keys_)
        return len_keys_ <= len(self) and self[:len_keys_] == keys_

    def __eq__(self, other):
        return super().__eq__(tuple(other))

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return super().__hash__()

    def __str__(self):
        return ' '.join(str(k) for k in self)

    def __repr__(self):
        return '<KeyChain %s>' % str(self)


class Keymapped():
    """Mixin class that provides a keypress method"""

    def keypress(self, size, key_orig):
        keymap   = self.__keymap
        context  = self.__context
        callback = self.__callback
        key_eval = Key(key_orig)

        def try_parent_class(key, sup=super()):
            if sup.selectable():
                # mro = sup.__self_class__.mro()
                # super_cls = mro[mro.index(sup.__thisclass__) + 1]
                # log.debug('%s: Offering %r to %s.keypress()', context, key, super_cls.__name__)
                key = sup.keypress(size, key)
                # log.debug('%s: %s.keypress() returned %r', context, super_cls.__name__, key)
            return key

        log.debug('%s: %r / %r pressed', context, key_orig, key_eval)

        # Any started keychains have the highest priority
        if keymap.any_keychain_started:
            log.debug('%s: Advancing started keychain(s)', context)
            key_ = keymap.evaluate(key_eval, context=context, callback=callback, widget=self)
            if key_ is None:
                log.debug('%s: Started keychain(s) used %r', context, key_eval)
                return None

        # Offer original key to original keypress() for built-in keys like up/down
        key_ = try_parent_class(key_orig)
        if key_ is None:
            return None

        # Offer our own key format to original keypress() in case there are any
        # Key instances in urwid.command_map
        if str(key_orig) != str(key_eval):
            key_ = try_parent_class(key_eval)
            if key_ is None:
                return None
        else:
            log.debug('%s: Not feeding %r to parent again (%r == %r)', context, key_eval, key_orig, key_eval)

        # Offer key to KeyMap
        key_ = keymap.evaluate(key_eval, context=context, callback=callback, widget=self)
        if key_ is None:
            # Key was evaluated() to some action
            return None
        elif key_ != key_eval:
            # key_eval was translated to another key (e.g. 'j' -> 'down'), so we
            # check if original keypress() likes that better
            if try_parent_class(key_) is None:
                # Original keypress() used translated key
                return None

        log.debug('%s: Returning %r', context, key_eval)
        return key_eval

    def selectable(self):
        return True


class KeyMap():
    """
    Bind keys to actions in different contexts

    To bind keys to widgets, a new class is created that accepts user input by
    adding the methods `keypress` and `selectable` to the original class:

    >>> keymap = KeyMap()
    >>> keymap.bind(key='meta g',
                    action=lambda widget: widget.set_edit_text('abcfoo'),
                    context='pwentry')
    >>> Password = keymap.wrap(urwid.Edit, context='pwentry')
    >>> Password
    urwid.Edit_Keymapped

    Now you can use Password like any regular Edit widget:

    >>> pw = Password('', 'Enter password or <Alt-g> to generate one')
    """

    NO_CONTEXT      = object()
    ALL_CONTEXTS    = object()
    DEFAULT_CONTEXT = 'default'

    def __init__(self, callback=None):
        self._default_callback = callback
        self._actions = {self.DEFAULT_CONTEXT: {}}
        self._descriptions = {}

        self._bindunbind_callbacks = blinker.Signal()
        self._keychain_callbacks = blinker.Signal()
        self._keychain_partial = []
        self._keychain_context = self.NO_CONTEXT

    def clear(self):
        """Remove all keybindings"""
        contexts = self._actions
        for context in contexts:
            log.debug('%s: Removing all keybindings', context)
            contexts[context] = {}
        self._bindunbind_callbacks.send(self)

    def _unbind_from_urwid_command_map(self, key):
        """Remove key from urwid's internal command map if possible"""
        import urwid
        if isinstance(key, KeyChain):
            key = key[0]
        try:
            del urwid.command_map[key]
        except KeyError as e:
            return False
        else:
            return True

    def bind(self, key, action, context=DEFAULT_CONTEXT, description=None):
        """
        Bind `key` to `action` in `context`

        key: a key string that is converted to Key or KeyChain with `mkkey`
        context: a descriptive string (or any other hashable object)
        action: What to do when `key` is pressed in `context`; may be:
                - a callable that accepts the widget that received `key`,
                - a Key object (so you can bind <j> to <down> for example),
                - any other object that is passed to the `callback` specified
                  in calls to `wrap` or when the KeyMap was instantiated.
        description: a descriptive string
        """
        key = self.mkkey(key)
        if isinstance(action, Key) and key == action:
            raise ValueError('Circular key mapping: %s -> %s' % (key, action))

        if context not in self._actions:
            self._actions[context] = {}
        self._actions[context][key] = action
        self._descriptions[(context, key)] = description or ''
        log.debug('%s: Mapped %r -> %r', context, key, action)
        self._bindunbind_callbacks.send(self)

    def unbind(self, key, context=DEFAULT_CONTEXT):
        """
        Unbind `key` in `context`

        Key chains starting with `key` are also removed.
        """
        key = self.mkkey(key)
        if context not in self._actions:
            raise ValueError('Unknown context: {!r}'.format(context))
        elif key in self._actions[context]:
            del self._actions[context][key]
            log.debug('%s: Unmapped %r', context, key)
        else:
            if context == self.DEFAULT_CONTEXT:
                key_removed = self._unbind_from_urwid_command_map(key)
            else:
                key_removed = False

            for k in tuple(self._actions[context]):
                if isinstance(k, KeyChain) and k.startswith(key):
                    del self._actions[context][k]
                    log.debug('%s: Unmapped %r', context, k)
                    key_removed = True
            if not key_removed:
                raise ValueError('Key not mapped in context %r: %s' % (context, key))
        self._bindunbind_callbacks.send(self)

    def get_description(self, key, context=DEFAULT_CONTEXT):
        return self._descriptions.get((context, key), '')

    def evaluate(self, key, context=DEFAULT_CONTEXT, callback=None, widget=None):
        """
        Run action that is mapped to `key` in `context`

        key: the pressed key
        context: the context `key` was pressed in
        callback: None or any callable
        widget: the widget that received `key`
        """
        if context not in self._actions:
            raise ValueError('Unknown context: {}'.format(context))

        key = Key(key)
        action = None

        # Unless we've are already started a key chain, try to find a single-key mapping
        if not self.any_keychain_started:
            log.debug('%s: Evaluating %r as single key for widget %r', context, key, widget)
            action = self._get_single_key_action(key, context)

        # Try to advance keychains only if no keychain was started previously or
        # if that previously started keychain was in the same context as we're
        # in now.
        if action is None and (self._keychain_context == self.NO_CONTEXT or
                               self._keychain_context == context):
            log.debug('%s: Evaluating %r as chain key for widget %r', context, key, widget)
            action = self._get_keychain_action(key, context)
            if action is KeyChain.ADVANCE:
                log.debug('%s:   %r was used to advance a keychain; locking context', context, key)
                self._keychain_context = context
                self._keychain_partial.append(key)
                self._run_keychain_callbacks()
                return None
            elif action is KeyChain.REDUCE:
                log.debug('%s:   %r was used to reduce a keychain', context, key)
                self._keychain_partial.pop()
                if not self.any_keychain_started:
                    self._reset_keychains()
                else:
                    self._run_keychain_callbacks()
                return None
            elif action is KeyChain.ABORT:
                log.debug('%s:   %r was used to abort a keychain', context, key)
                self._reset_keychains()
                return None
            elif action is KeyChain.REJECT:
                log.debug('%s:   %r was rejected by all keychains', context, key)
                action = None
            elif isinstance(action, Key):
                log.debug('%s:   %r was resolved to a single key: %r', context, key, action)
                self._reset_keychains(context)
            else:
                log.debug('%s:   %r was used to complete a keychain', context, key)
                self._reset_keychains(context)

        # Handle the action we found
        if action is None:
            log.debug('%s:   %r is not mapped', context, key)
            return key
        elif isinstance(action, Key):
            return self.evaluate(action, context, callback, widget)
        elif isinstance(action, KeyChain):
            raise RuntimeError('Mapping to keychains is not supported.')
        elif callable(action):
            # action itself is the callback
            log.debug('%s:   Calling action directly: %r', context, action)
            action(widget)
        elif callback is not None:
            # Individual callback for this widget
            log.debug('%s:  Calling widget class callback %r(%r, %r)', context, callback, action, widget)
            callback(action, widget)
        elif self._default_callback is not None:
            # General callback for all widgets
            log.debug('%s:   Calling default callback %r(%r, %r)', context, self._default_callback, action, widget)
            self._default_callback(action, widget)
        else:
            raise RuntimeError('No callback given - unable to handle {!r}'.format(action))

    def _get_single_key_action(self, key, context=DEFAULT_CONTEXT):
        actions = self._actions[context]
        if key in actions:
            return actions[key]

        if context is not self.DEFAULT_CONTEXT:
            actions = self._actions[self.DEFAULT_CONTEXT]
            if key in actions:
                return actions[key]

    def _get_keychain_action(self, key, context):
        partial = self._keychain_partial
        candidate = tuple(partial) + (key,)
        log.debug('%s: Getting keychain action for %s + %s:',
                  context, '+'.join(partial) or "<>", key)
        action = KeyChain.ABORT if partial else KeyChain.REJECT
        for kc,act in self._started_keychains(context):
            if kc == candidate:
                log.debug('%s:   Resolved keychain %r to action %r', context, kc, act)
                return act
            elif kc.startswith(candidate):
                log.debug('%s:   Advancing keychain %r: %r', context, kc, '+'.join(candidate))
                action = KeyChain.ADVANCE
            elif key == 'backspace' and len(partial) > 0:
                log.debug('%s:   Reducing keychain %r: %r', context, kc, candidate[:-2])
                action = KeyChain.REDUCE
        return action

    def _keychains(self, context=ALL_CONTEXTS):
        def keychains_from(cntxt):
            for kc,action in self._actions[cntxt].items():
                if isinstance(kc, KeyChain):
                    yield (kc, action)

        if context is self.ALL_CONTEXTS:
            for cntxt in self.contexts:
                yield from keychains_from(cntxt)
        else:
            yield from keychains_from(context)

    def _started_keychains(self, context=ALL_CONTEXTS):
        keychain_partial = self._keychain_partial
        for kc,action in self._keychains(context):
            if kc.startswith(keychain_partial):
                yield (kc, action)

    def _reset_keychains(self, context=ALL_CONTEXTS):
        log.debug('%s: Resetting keychains', context)
        self._keychain_partial.clear()
        self._keychain_context = self.NO_CONTEXT
        self._run_keychain_callbacks()

    @property
    def any_keychain_started(self):
        """Whether any keychain was started"""
        return bool(self._keychain_partial)

    @property
    def current_keychain(self):
        """Tuple of currently collected keychain keys"""
        return tuple(self._keychain_partial)

    def _run_keychain_callbacks(self):
        context = self._keychain_context
        if context is self.NO_CONTEXT:
            self._keychain_callbacks.send(self, context=self.NO_CONTEXT, active_keychains=(), keys_given=())
        else:
            self._keychain_callbacks.send(self,
                                          context=context,
                                          active_keychains=self._started_keychains(context),
                                          keys_given=self.current_keychain)

    def on_keychain(self, callback):
        """
        Register callback for keychain changes

        `callback` is called when a keychain is advanced, finished or aborted
        with this KeyMap instances as a positional argument and the keyword
        arguments "active_keychains" and "keys_given".
        """
        self._keychain_callbacks.connect(callback, weak=True)

    def on_bind_unbind(self, callback):
        """
        Register callback for bind/unbind events

        `callback` is called when a key mapped or unmapped with this KeyMap
        instances as a positional argument.
        """
        self._bindunbind_callbacks.connect(callback, weak=True)

    def wrap(self, cls, callback=None, context=DEFAULT_CONTEXT):
        """
        Return widget class that passes keypress()es through `evaluate`

        callback: Custom callable for this widget class; will be called with
                  the action mapped to the key and the widget instance.
        context: A descriptive string (or any other hashable object)
        """
        if context not in self._actions:
            self._actions[context] = {}
        clsname = cls.__name__ + '_Keymapped'
        return type(clsname,
                    (Keymapped, cls),
                    {'_Keymapped__keymap': self,
                     '_Keymapped__context': context,
                     '_Keymapped__callback': staticmethod(callback)})

    _KEY_SPLIT_SPACE = re.compile(r' +')
    def mkkey(self, string):
        """
        Create Key or KeyChain instance from `string`

        Valid values for `string`:
          - A Key or KeyChain instance, which is simply returned.
          - A string that contains spaces is split at those spaces and all
            non-empty items of the resulting list are passed to KeyChain.
          - A string with '+' in it is split at those '+' and the resulting list
            is passed to KeyChain.
          - Any other string is passed to Key.
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
        """
        Yield all keys where `match_func(key, action)` evaluates to True

        If `context` is not None, yield only keys mapped in that context.
        """
        def is_match(key, action):
            return match_func is None or match_func(key, action)

        if context is not None:
            for k,a in self._actions[context].items():
                if is_match(k, a):
                    yield k
        else:
            for context in self.contexts:
                for k,a in self._actions[context].items():
                    if is_match(k, a):
                        yield k

    def map(self, context=DEFAULT_CONTEXT):
        """Yield (key, action) tuples for keys mapped in `context`"""
        yield from self._actions[context].items()

    @property
    def contexts(self):
        """Yield existing contexts"""
        yield from self._actions
