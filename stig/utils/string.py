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


from unicodedata import normalize as _normalize_unicode
def normalize_unicode(string):
    """
    Convert combining character sequences into graphemes (e.g. "a˚" -> "å") so
    that len() reports the correct length.
    http://www.unicode.org/faq/char_combmark.html
    """
    return _normalize_unicode('NFC', string)


def striplines(lines):
    """Remove empty strings from start and end of `lines` using `pop`"""
    lines = list(lines)
    while lines and lines[0] == '':
        lines.pop(0)
    while lines and lines[-1] == '':
        lines.pop(-1)
    yield from lines


from unicodedata import east_asian_width as _east_asian_width
def strwidth(string):
    """Return displayed width of `string`, considering wide characters"""
    return len(string) + sum(1 for char in string
                             if _east_asian_width(char) in 'FW')


def strcrop(string, width, tail=None):
    """Return `string` cropped to `width`, considering wide characters

    If `tail` is not None, it must be a string that is appended to the cropped
    string.
    """
    def widechar_indexes(s):
        for i,c in enumerate(s):
            if _east_asian_width(c) in 'FW':
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


def crop_and_align(string, width, align, has_wide_chars=True):
    """Make `string` exactly `width` spaces long and align it

    If `has_wide_chars` evaluates to True, the more expensive `stralign`
    function is used, which considers wide characters.

    `align` must be 'left' or 'right'.
    """
    if has_wide_chars:
        string = stralign(string, width, align)
    else:
        err = TypeError("'align' attribute must be 'left' or 'right', not %r}" % align)
        string_len = len(string)
        if string_len > width:
            if align == 'right':
                string = string[string_len-width:]
            elif align == 'left':
                string = string[:width]
            else:
                raise err
        else:
            if align == 'right':
                string = string.rjust(width)
            elif align == 'left':
                string = string.ljust(width)
            else:
                raise err
    return string
