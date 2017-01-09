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


class Key(str):
    """Key code as string

    Do some validation and translation from urwid format to a format better
    suited for chained keys.

    """

    _INIT = (
        (re.compile(r'^<(.+)>$'),                r'\1'),
        (re.compile(r'^esc$', flags=re.I),       r'escape'),
        (re.compile(r'^ $'),                     r'space'),
        (re.compile(r'^meta', flags=re.I),       r'alt'),
        (re.compile(r'^pos1$', flags=re.I),      r'home'),
        (re.compile(r'^del$', flags=re.I),       r'delete'),
        (re.compile(r'^ins$', flags=re.I),       r'insert'),
        (re.compile(r'^return$', flags=re.I),    r'enter'),
        (re.compile(r'^page up$', flags=re.I),   r'pgup'),
        (re.compile(r'^page down$', flags=re.I), r'pgdn'),
        (re.compile(r'^page dn$', flags=re.I),   r'pgdn'),
        (re.compile(r' '),                       r'-'),
        # The first part in key combos must always be the same, but the part
        # after must be preserved. <alt-l> is not the same as <alt-L>.
        (re.compile(r'^(\w+)-(\S+)$'),
         lambda m: m.group(1).lower()+'-'+m.group(2)),
    )

    _MODS = ('shift', 'alt', 'ctrl')
    _cache = {}

    def __new__(cls, key):
        if key in cls._cache:
            return cls._cache[key]
        else:
            orig_key = key

        # Remove brackets (<>) around key, some renaming, etc.
        for regex,repl in cls._INIT:
            key = regex.sub(repl, key)

        # Convert 'X' to 'shift-x'
        if len(key) == 1 and key.isupper():
            key = 'shift-%s' % key.lower()

        # Validate modifier
        if '-' in key:
            mod, char = key.split('-', 1)
            # If the modifier is '', '-' is the actual key
            if len(mod) > 0:
                if len(char) == 0:
                    raise ValueError('Missing character after modifier: <%s>' % key)
                if mod not in cls._MODS:
                    raise ValueError('Invalid modifier: <%s>' % key)
                if mod == 'shift':
                    # 'shift-E' is the same as 'shift-e'
                    key = key.lower()

        obj = super().__new__(cls, key)
        cls._cache[orig_key] = obj
        return obj

    def __repr__(self):
        return '<%s>' % self


class KeyChain(tuple):
    class COMPLETED(): pass
    class ADVANCED(): pass
    class ABORTED(): pass
    class REFUSED(): pass

    def __new__(cls, *keys):
        log.debug('Making KeyChain from %r', keys)
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

    @property
    def given(self):
        """Tuple of keys we have so far"""
        return tuple(self) if self.is_complete else self[:self._pos+1]

    @property
    def is_complete(self):
        """Wether there are keys missing to complete the chain"""
        return self._pos >= len(self)-1

    def __str__(self):
        return ' '.join(repr(k) for k in self)

    def __repr__(self):
        text = ['<KeyChain %s' % str(self)]
        if self._pos > -1:
            text.append(' given=[')
            text.append(' '.join(repr(k) for k in self.given))
            text.append(']')
        text.append('>')
        return ''.join(text)



class KeyMapped():
    """Mixin class that provides a keypress method"""
    def keypress(self, size, key):
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
            elif key_eval != Key(key):
                # evaluate() may have resolved key to another key
                # (e.g. 'j' -> 'down')
                key = try_super(key_eval)

        return key

    def selectable(self):
        return True


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
        self._callback = callback
        self._contexts = {None: {}}
        self._clscache = {}

    def bind(self, key, action, context=None):
        """Bind `key` to `action` in `context`

        key: an urwid key string
        context: a descriptive string (or any other hashable object)
        action: What to do when `key` is pressed in `context`; may be:
                - a callable that accepts the widget that received `key`,
                - a Key object (so you can bind <ctrl a> to whatever <ctrl b>
                  is bound to,
                - any other object that is passed to the `callback` specified
                  in calls to `wrap` or when the KeyMap was instantiated.
        """
        key = Key(key)
        if isinstance(action, Key) and key == action:
            raise ValueError('Mapping {!r} to {!r} is silly'.format(key, action))

        if context not in self._contexts:
            self._contexts[context] = {}
        self._contexts[context][key] = action
        log.debug('%s: Mapped %r -> %r', context, key, action)

    def unbind(self, key, context=None):
        """Unbind `key` in `context`"""
        key = Key(key)
        if context not in self._contexts:
            raise ValueError('Unknown context: {!r}'.format(context))
        elif key not in self._contexts[context]:
            raise ValueError('Key not mapped in context {!r}: {!r}'.format(context, key))
        else:
            del self._contexts[context][key]
            log.debug('Unmapped %r [%s]', key, context)

    def evaluate(self, key, context=None, callback=None, widget=None):
        """Run action that is bound to `key` in `context`

        key: the pressed key
        context: the context `key` was pressed in
        callback: None or any callable
        widget: the widget that received `key`
        """
        if context not in self._contexts:
            raise ValueError('Unknown context: {}'.format(context))

        # Find the action that is bound to key in context
        if key in self._contexts[context]:
            action = self._contexts[context][key]
            log.debug('Evaluated %r in context %r: %r', key, context, action)
        elif key in self._contexts[None]:
            action = self._contexts[None][key]
            log.debug('Evaluated %r in default context: %r', key, action)
        else:
            log.debug('%r is not mapped in context %r', key, context)
            return key

        # Run the action
        if isinstance(action, Key):
            log.debug('Evaluating %r', action)
            return self.evaluate(action, context, callback, widget)
        elif callable(action):
            # action itself is the callback
            log.debug('Calling action: %r', action)
            action(widget)
        elif callback is not None:
            # Individual callback for this widget
            log.debug('Calling callback %r with widget %r', callback, widget)
            callback(action, widget)
        elif self._callback is not None:
            # General callback for all widgets
            log.debug('Calling callback %r with widget %r', self._callback, widget)
            self._callback(action, widget)
        else:
            raise TypeError('No callback given - unable to handle {!r}'.format(action))

    def wrap(self, cls, callback=None, context=None):
        """Return widget class that passes keypress()es through evaluate()"""
        clsid = id(cls)
        if clsid in self._clscache:
            cls_km = self._clscache[clsid]
        else:
            if context not in self._contexts:
                self._contexts[context] = {}

            log.debug('Wrapping %r in %r', cls, KeyMapped)
            clsname = cls.__name__ + '_KeyMapped'
            cls_km = type(clsname,
                          (KeyMapped, cls),
                          {'keymap': self,
                           'context': context,
                           'callback': staticmethod(callback)})
            self._clscache[clsid] = cls_km
        return cls_km

    def key(self, string):
        """Convenience method to make Key object from string"""
        return Key(string)

    def keys(self, action, context=None):
        """Yield keys that are mapped to actions that start with `action`

        If `context` is not None, yield only keys mapped in that context.
        """
        if context is not None:
            for k,a in self._contexts[context].items():
                if a.startswith(action):
                    yield k
        else:
            for context in self.contexts:
                for k,a in self._contexts[context].items():
                    if a.startswith(action):
                        yield k

    def map(self, context=None):
        """Yield (key, action) tuples for keys mapped in `context`"""
        yield from self._contexts[context].items()

    @property
    def contexts(self):
        """Yield existing contexts"""
        yield from self._contexts
