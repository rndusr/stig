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

"""Load urwid palette from file

This module handles loading urwid palettes from files or lists of strings and
applying them to a Screen object (see `ScreenBase.register_palette`).

First, load the default palette you ship with your application.

>>> init('path/to/default.palette', screen)

Now users can load their own palettes that overload default attributes.

>>> load('path/to/user.palette', screen)

Instead of a file you can also provide an iterable of strings or any object
with a 'readlines' method that returns such an iterable.

Use `reset` to go back to the defaults.

>>> reset(screen)


FILE FORMAT
===========

The palette format is very simple. Each line is either a palette entry or a
variable declaration.

Palette entries look like this:

    <ATTRIBUTE NAME> <FOREGROUND> on <BACKGROUND>

ATTRIBUTE NAME is a string without spaces. FOREGROUND and BACKGROUND are
16-color and 256-color attributes as specified in the urwid manual.

Variables are declared like that:

    $<NAME> = <VALUE>

Variables can be used as FOREGROUND or BACKGROUND attributes.

    $bg = dark gray
    this-attribute yellow     on $bg
    that-attribute light blue on $bg

"""

from collections import abc
import re
from urwid import (AttrSpec, AttrSpecError)


class ThemeError(Exception): pass
class ParseError(ThemeError): pass
class ValidationError(ThemeError): pass


def init(palette, screen):
    """Read `palette`, set it as default and apply it to `screen`

    palette: Where to get the palette from:
             - any object with a `readlines` method (e.g. a file handle),
             - a file name,
             - an iterable of lines.
    screen: A urwid screen instance (e.g. `raw_display.Screen`)

    The palette is passed to `set_default` before `register`ing it.
    """
    lines = read(palette)
    palette = Palette(lines)
    set_default(palette)
    register(screen, palette)


def load(palette, screen):
    """Same as `init`, but with validation

    The palette is passed to `validate` before `register`ing it.
    """
    lines = read(palette)
    palette = Palette(lines)
    validate(palette)
    register(screen, palette)


def read(source):
    """Read palette from `source`

    source: file handle, file name or iterable of strings

    Returns list of string lines.
    Raises TypeError or OSError.
    """
    if hasattr(source, 'readlines') and callable(source.readlines):
        lines = source.readlines()
    elif isinstance(source, str):
        try:
            with open(source, mode='r') as f:
                lines = f.readlines()
        except OSError as e:
            raise ThemeError('Unable to read {!r}: {}'.format(source, e.strerror))
    elif isinstance(source, abc.Iterable):
        lines = source
    else:
        raise TypeError('Invalid source: {!r}'.format(source))
    return [l.rstrip('\n') for l in lines]


def register(screen, palette):
    """Register palette with screen"""
    screen.set_terminal_properties(colors=palette.colors,
                                   bright_is_bold=palette.light_is_bold)
    screen.register_palette(palette)
    screen.clear()


DEFAULT_PALETTE = None
def set_default(palette):
    """Store copy of palette in global variable `DEFAULT_PALETTE`"""
    if not isinstance(palette, Palette):
        raise TypeError('Not a Palette: {!r}'.format(palette))
    global DEFAULT_PALETTE
    DEFAULT_PALETTE = palette.copy()


def validate(palette):
    """Validate palette (`set_default` must be called before)

    Raise ValidationError if any attribute name in `palette` is not in
    `DEFAULT_NAMES`.
    """
    if DEFAULT_PALETTE is None:
        raise RuntimeError('No defaults have been specified with set_default()')
    else:
        for entry in palette:
            name = entry[0]
            if name not in DEFAULT_PALETTE.names:
                raise ValidationError('Invalid attribute name: {!r}'.format(name))

def reset(screen):
    """`register` palette previously given to `set_default`"""
    if DEFAULT_PALETTE is None:
        raise RuntimeError('No defaults have been specified with set_default()')
    else:
        register(screen, DEFAULT_PALETTE)


class Palette(abc.Sequence):
    """Read urwid palette as a list of strings

    Raises ParseError on errors during parsing (duh).
    """

    VAR_REGEX = re.compile(r'^\$(?P<var>\S+) *= *(?P<val>.*?) *$')
    ATTR_REGEX = re.compile(r'^(?P<name>\S+) *(?P<fg>.*?) +on +(?P<bg>.*) *$')

    def __init__(self, lines):
        def apply_variables(string, variables):
            for name,value in sorted(variables.items(), key=lambda k: len(k[0]), reverse=True):
                while value[0] == '$':
                    value = variables[value[1:]]
                string = string.replace('$'+name, value)
            return string

        def check_color(string):
            try:
                attrspec = AttrSpec(string, 'default')
            except AttrSpecError:
                raise ValueError(string)
            else:
                return max(16, attrspec.colors)

        def make_entry(name, fg, bg, colors):
            if colors == 256:
                return (name, 'default', 'default', 'default', fg, bg)
            elif colors == 16:
                return (name, fg, bg)
            else:
                raise RuntimeError('Unsupported number of colors: {}'.format(colors))

        self._light_is_bold = False
        palette = []
        variables = {}
        max_colors = 1
        for linenum,line in enumerate(lines, start=1):
            line = line.strip()
            if len(line) < 1 or line[0] == '#':
                # Ignore comments and empty lines
                continue

            if line == 'light_is_bold':
                self.light_is_bold = True
                continue

            # Read variable declaration
            match = self.VAR_REGEX.match(line)
            if match is not None:
                name, value = match.group('var', 'val')
                variables[name] = value
                continue

            # Read palette entry
            match = self.ATTR_REGEX.match(line)
            if match is not None:
                name, fg, bg = match.group('name', 'fg', 'bg')
                fg = apply_variables(fg, variables)
                bg = apply_variables(bg, variables)
                try:
                    this_colors = max(check_color(fg), check_color(bg))
                except ValueError as e:
                    raise ParseError('Invalid color in line {}: {!r}'.format(linenum, str(e)))
                else:
                    max_colors = max(max_colors, this_colors)
                    palette.append(make_entry(name, fg, bg, this_colors))
                    continue

            raise ParseError('Invalid line #{}: {!r}'.format(linenum, line))

        self._palette = palette
        self._colors = max_colors
        self._names = tuple(entry[0] for entry in palette)

    @property
    def light_is_bold(self):
        """Whether light colors are automatically bold"""
        return self._light_is_bold

    @light_is_bold.setter
    def light_is_bold(self, light_is_bold):
        self._light_is_bold = light_is_bold

    @property
    def colors(self):
        """Number of colors needed"""
        return self._colors

    @property
    def names(self):
        """Yield attribute names"""
        for name in self._names:
            yield name

    def copy(self):
        palette = Palette([])
        palette._palette = self._palette
        palette._colors = self._colors
        palette._names = self._names
        return palette

    def __eq__(self, other):
        return tuple(self) == tuple(other)

    def __ne__(self, other):
        return tuple(self) != tuple(other)

    def __repr__(self):
        return repr(self._palette)

    def __getitem__(self, item):
        return self._palette[item]

    def __iter__(self):
        return iter(self._palette)

    def __len__(self):
        return len(self._palette)
