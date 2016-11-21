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

"""Indent and expand tabs and wrap lines"""

from textwrap import wrap
from shutil import get_terminal_size

def _explode(lines, indent):
    """Split each line in `lines` at tabstops

    Tabstops at the beginning of each line are expanded to 2 spaces.

    Return list of rows (a row being a list of strings, i.e. cells)
    """
    exploded = []
    for line in lines:
        indentions = 0
        while line.startswith('\t'):
            indentions += 1
            line = line[1:]
        splitline = line.split('\t')
        for i in range(indentions):
            splitline.insert(0, ' '*indent)
        exploded.append(splitline)
    return exploded

def _split_sections(lines):
    """Split `lines` into sections of lines that have the same amount of parts"""
    sections = []
    while lines:
        line = lines.pop(0)
        partnum = len(line)
        section = [line]
        while lines and len(lines[0]) == partnum:
            line = lines.pop(0)
            section.append(line)
        sections.append(section)
    return sections

def _col_widths(lines):
    """Return a list of maximum column widths"""
    widths = []
    for line in lines:
        for i,part in enumerate(line):
            while len(widths) <= i:
                widths.append(0)
            widths[i] = max(len(part), widths[i])
    return widths

def _join_line(parts, widths, maxwidth):
    """Expand and wrap all parts of `line`"""
    line = ''
    for colwidth,part in zip(widths, parts):
        part = part.ljust(colwidth)
        if len(line) + len(part) > maxwidth:
            line = _wrapindent(part, prefix=line, width=maxwidth)
        else:
            line += part
    return line

def _wrapindent(text, prefix, width):
    """Prepend `prefix` to text and wrap the result if longer than `width`"""
    indent = ' '*len(prefix)
    parts = wrap(prefix+text, width=width, subsequent_indent=indent)
    return '\n'.join(parts)

def expand(lines, indent=4, maxwidth=100):
    """Expand all tabstops (\t) in each line intelligently

    "Intelligently" means that consecutive lines with the same amount of '\t'
    characters are treated like a table, giving each column the same space.

    Return `lines` with all tabs expanded
    """
    width = min(get_terminal_size()[0], maxwidth)
    expanded = []
    for section in _split_sections(_explode(lines, indent)):
        widths = _col_widths(section)
        for line in section:
            expanded.append(_join_line(line, widths, width))
    return expanded
