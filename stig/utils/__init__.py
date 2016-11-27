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

import unicodedata
import re


def natsortkey(key):
    """Provide this as the 'key' argument to `list.sort`, `sorted`, etc.

    Pilfered from
    <https://blog.codinghorror.com/sorting-for-humans-natural-sort-order/>
    and adapted.
    """
    convert = lambda text: int(text) if isinstance(text, str) and text.isdigit() else text
    return [convert(c) for c in re.split('([0-9]+)', key)]


def striplines(lines):
    """Remove empty strings from start and end of `lines` using `pop`"""
    lines = list(lines)
    while lines and lines[0] == '':
        lines.pop(0)
    while lines and lines[-1] == '':
        lines.pop(-1)
    yield from lines


def strwidth(string):
    """Return displayed width of `string`, considering wide characters"""
    return len(string) + sum(1 for char in string
                             if unicodedata.east_asian_width(char) in 'FW')


def strcrop(string, width, tail=None):
    """Return `string` cropped to `width`, considering wide characters

    If `tail` is not None, it must be a string that is appended to the cropped
    string.
    """
    def widechar_indexes(s):
        for i,c in enumerate(s):
            if unicodedata.east_asian_width(c) in 'FW':
                yield i

    if strwidth(string) <= width:
        return string  # string is already short enough

    if tail is not None:
        width -= strwidth(tail)  # Account for tail in final width

    indexes = list(widechar_indexes(string)) + [len(string)]
    if not indexes:
        return string[:width]  # No wide chars, regular cropping is ok

    parts = []
    start = 0
    end = 0
    currwidth = strwidth(''.join(parts))

    while indexes and currwidth < width and end < len(string):
        end = indexes.pop(0)
        if end > 0:
            parts.append(string[start:end])
            currwidth = strwidth(''.join(parts))
            start = end

    if currwidth > width:
        excess = currwidth - width
        parts[-1] = parts[-1][:-excess]

    if tail is not None:
        parts.append(tail)

    return ''.join(parts)


def stralign(string, width, side='left'):
    """Return `string` aligned to `side`, considering wide characters

    The returned string is filled up with spaces to take `width` single-spaced
    characters and cropped with `strcrop` if necessary.
    """
    fill = width - strwidth(string)
    if fill < 0:
        string = strcrop(string, width)

    fill = width - strwidth(string)
    if fill > 0:
        if side == 'left':
            string = string + ' '*fill
        elif side == 'right':
            string = ' '*fill + string
        else:
            raise TypeError("side argument must be 'left' or 'right', not {!r}".format(side))
    return string
