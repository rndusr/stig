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

    This class prettifies urwid key codes and accepts some alternatives, for
    example Key('del') creates Key('delete'), Key('escape') -> Key('esc'),
    etc.
    """

    _PARSE_MAP = (
        (re.compile(r'^<(.+)>$'),                 r'\1'),
        (re.compile(r'(.+)-(.+)'),                r'\1 \2'),
        (re.compile(r'^alt', flags=re.I),         r'meta'),
        (re.compile(r'^space$', flags=re.I),      r' '),
        (re.compile(r'^return$', flags=re.I),     r'enter'),
        (re.compile(r'^escape$', flags=re.I),     r'esc'),
        (re.compile(r'^pgup$', flags=re.I),       r'page up'),
        (re.compile(r'^pgdn$', flags=re.I),       r'page down'),
        (re.compile(r'^pos1$', flags=re.I),       r'home'),
        (re.compile(r'^ins$', flags=re.I),        r'insert'),
        (re.compile(r'^del$', flags=re.I),        r'delete'),
        (re.compile(r'^(\w+) (\S+)$'),
         lambda m: m.group(1).lower()+' '+m.group(2)),
    )

    def __new__(cls, key):
        # Conform to urwid conventions
        for regex,repl in cls._PARSE_MAP:
            key = regex.sub(repl, key)
        return super().__new__(cls, key)

    _PRETTIFY_MAP = (
        (re.compile(r'^esc$'), r'escape'),
        (re.compile(r'^ $'),   r'space'),
        (re.compile(r'^meta'), r'alt'),
        (re.compile(r' '),     r'-'),
    )

    @property
    def pretty(self):
        """Pretty string representation"""
        key = self
        for regex,repl in self._PRETTIFY_MAP:
            key = regex.sub(repl, key)
        return key

    def __repr__(self):
        return '<'+str(self)+'>'


class KeyMapped():
    """Mixin class that provides a keypress method"""
    def keypress(self, size, key):
        sup = super()
        def try_super(key):
            if sup.selectable():
                key = sup.keypress(size, key)
            return key

        # Offer key to parent's keypress()
        key = try_super(key)

        # If parent doesn't want key, check if it is mapped
        if key is not None:
            key = self.keymap.evaluate(key,
                                       context=self.context,
                                       callback=self.callback,
                                       widget=self)

            # evaluate() may have resolved key to another key
            # (e.g. 'j' -> 'down')
            if key is not None:
                key = try_super(key)

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
        key = Key(key)
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
