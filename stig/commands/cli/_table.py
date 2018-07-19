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

from ...logging import make_logger
log = make_logger(__name__)

from ...utils.string import (strwidth, stralign, crop_and_align, normalize_unicode)

import re
import textwrap
from types import SimpleNamespace
from shutil import get_terminal_size
TERMSIZE = get_terminal_size(fallback=(None, None))


_whitespace_regex = re.compile(r'^\s*$')
def _wrapped(line, width):
    # Prevent textwrap.wrap() from filtering out empty lines
    if _whitespace_regex.match(line):
        yield line
    else:
        yield from textwrap.wrap(line, width=width, break_on_hyphens=False)

def _get_cell_lines(cell):
    # Return string of single cell correctly cropped/padded and aligned
    line = normalize_unicode(str(cell.get_cli_value()))
    width = cell.width
    if isinstance(width, int):
        if cell.wrap == 'clip':
            return (crop_and_align(line, width, cell.align,
                                   has_wide_chars=cell.may_have_wide_chars),)
        else:
            return tuple(stralign(line, width=width)
                         for line in _wrapped(line, width))
    else:
        return (line,)

def _assemble_row(table, line_index, pretty=True):
    # Concatenate all cells in a row with delimiters
    # Return a list of lines (cells may have multiple lines)
    row = []
    for cell in table.rows[line_index]:
        if pretty:
            row.append(_get_cell_lines(cell))
        else:
            row.append((str(cell.get_raw_value()),))

    lines_count = max(len(cell) for cell in row)
    lines = []
    delimiter = table.delimiter
    for i in range(lines_count):
        # `row` is a list of cells; each `cell` is a list of lines in an
        # individual cell.
        line = []
        for cell in row:
            cell_lines = len(cell)
            empty_space = ' ' * len(cell[0])
            line.append(cell[i] if i < cell_lines else empty_space)
        line = table.delimiter.join(line)
        lines.append(line)
    return lines

def _assemble_headers(table):
    # Concatenate all column headers with delimiters
    # This must be called after shrink_and_expand_to_fit() so we can
    # grab the final column widths from the first row.
    headers = []
    for colname in table.colorder:
        width = table.colwidths[colname]
        header_items = table.colspecs[colname].header
        left  = header_items.get('left', '')
        right = header_items.get('right', '')
        space = ' '*(width - len(left) - len(right))
        header = ''.join((left, space, right))[:width]
        headers.append(header)
    return table.delimiter.join(headers)

def _get_header_width(table, colname):
    header = table.colspecs[colname].header
    return strwidth(' '.join((header.get('left', ''),
                              header.get('right', ''))).strip())

def _get_colwidth(table, colindex):
    # Return width of widest cell in column
    rows = (normalize_unicode(str(row[colindex].get_cli_value()))
            for row in table.rows)
    return max(strwidth(row) for row in rows)

def _column_has_variable_width(table, colname):
    # Whether column has fixed or variable width
    return not isinstance(table.colspecs[colname].width, int)

def _column_could_use_more_width(table, colname):
    # Whether any cell in a column is cropped
    return table.colwidths[colname] < table.maxcolwidths[colname]

def _column_is_shrinkable(table, colname):
    # Whether the current width of column is larger than its minimum width
    return table.colwidths[colname] > table.colspecs[colname].min_width

def _set_colwidth(table, colindex, width):
    # Set width of all cells in a column
    colname = table.colorder[colindex]
    table.colwidths[colname] = width
    for row in table.rows:
        row[colindex].width = width

def _set_maxcolwidth(table, colindex, maxwidth):
    # Set maximum width a column can make use of (no cell needs more horizontal
    # space than `maxwidth`)
    colname = table.colorder[colindex]
    table.maxcolwidths[colname] = maxwidth

def _get_excess_width(table):
    # Return width by which table must be narrowed to fit in max_width
    first_line = _assemble_row(table, 0)[0]
    return strwidth(first_line) - table.max_width

def _remove_column(table, colindex):
    # Delete column from internal structures
    del table.colwidths[table.colorder[colindex]]
    del table.colorder[colindex]
    for row in table.rows:
        del row[colindex]

def _shrink_to_widest_value(table):
    # Reduce width of columns where header and all values are narrower than the
    # current width
    for colindex,colname in enumerate(table.colorder):
        max_value_width = max(_get_header_width(table, colname),
                              _get_colwidth(table, colindex))
        _set_colwidth(table, colindex, max_value_width)
        _set_maxcolwidth(table, colindex, max_value_width)

def _shrink_variable_width_columns(table):
    # Reduce width of columns that haven't reached their min_size yet
    excess = _get_excess_width(table)
    while excess > 0:
        candidates = [(colname,table.colwidths[colname])
                      for colname in table.colorder
                      if _column_is_shrinkable(table, colname)]

        if len(candidates) >= 2:
            # Sort by width (first item is widest)
            candidates_sorted = sorted(candidates, key=lambda col: col[1], reverse=True)
            widest0_name, widest0_width = candidates_sorted[0]
            widest1_name, widest1_width = candidates_sorted[1]
            # Shrink widest column by difference to second widest column
            # (leaving them at the same width), but not by more than `excess`
            # characters.
            shrink_amount = max(1, min(excess, widest0_width - widest1_width))
        elif len(candidates) >= 1:
            # Only one column left to shrink
            widest0_name = candidates[0][0]
            shrink_amount = 1
        else:
            # No shrinkable columns
            break

        new_width = table.colwidths[widest0_name] - shrink_amount
        _set_colwidth(table, table.colorder.index(widest0_name), new_width)
        excess = _get_excess_width(table)

def _shrink_by_removing_columns(table):
    # Remove columns until table is no longer wider than terminal
    while _get_excess_width(table) > 0:
        _remove_column(table, 0)

    # We may have freed up space to give back to columns of variable width
    freed_width = -_get_excess_width(table)
    if freed_width > 0:
        while freed_width > 0:
            freed_width -= 1
            # Find non-fixed-width columns that could use more width
            candidates = [(colname,table.colwidths[colname])
                          for colname in table.colorder
                          if _column_has_variable_width(table, colname) and
                             _column_could_use_more_width(table, colname)]
            if not candidates:
                # We have space left, but no column wants it
                break
            candidates_sorted = sorted(candidates, key=lambda col: col[1])
            colname = candidates_sorted[0][0]
            new_width = table.colwidths[candidates_sorted[0][0]] + 1
            _set_colwidth(table, table.colorder.index(colname), new_width)

def _fit_table_into_terminal(table):
    # Expand all cells in each colum to the width of the widest cell
    # Keep track of each column width in table namespace
    for colindex,colname in enumerate(table.colorder):
        if _column_has_variable_width(table, colname):
            colwidth = _get_colwidth(table, colindex)
        else:
            colwidth = table.colspecs[colname].width
        _set_colwidth(table, colindex, colwidth)

    _shrink_to_widest_value(table)
    _shrink_variable_width_columns(table)
    _shrink_by_removing_columns(table)

def print_table(items, order, column_specs):
    """
    Print table from a two-dimensional array of column objects

    `column_specs` maps column IDs to ColumnBase classes.  A column ID is any
    hashable object, but you probably want strings like 'name', 'id', 'date',
    etc.

    `order` is a sequence of column IDs.

    `items` is a sequence of arbitrary objects that are used to create cell
    objects by passing them to the classes in `column_specs`.
    """
    # Whether to print for a human or for a machine to read our output
    pretty_output = all(x is not None for x in (TERMSIZE.columns, TERMSIZE.lines))

    table = SimpleNamespace(colspecs=column_specs,
                            colorder=order,
                            colwidths={}, maxcolwidths={},  # Calculated when needed
                            delimiter='\t' if TERMSIZE.columns is None else '│',
                            max_width=TERMSIZE.columns)

    # Create two-dimensional list of cells.  Each cell must behave like an
    # instance of a child class of ColumnBase (see stig.views.__init__.py).
    table.rows = []
    for item in items:
        row = []
        for i,colname in enumerate(table.colorder):
            row.append(table.colspecs[colname](item))
        table.rows.append(row)

    if len(table.rows) > 0:
        if pretty_output:
            _fit_table_into_terminal(table)
            headerstr = '\033[1;4m' + _assemble_headers(table) + '\033[0m'
        else:
            log.debug('Could not detect TTY size - assuming stdout is no TTY')

        for line_index in range(len(table.rows)):
            # Print column headers after every screen full
            if pretty_output and line_index % (TERMSIZE.lines-2) == 0:
                print(headerstr)
            for row in _assemble_row(table, line_index, pretty=pretty_output):
                print(row)
