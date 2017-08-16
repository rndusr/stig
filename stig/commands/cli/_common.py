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

from ...utils import strwidth
from shutil import get_terminal_size
TERMSIZE = get_terminal_size(fallback=(None, None))


def print_table(items, columns_wanted, COLUMN_SPECS):
    """Print table from a two-dimensional array of column objects

    `COLUMN_SPECS` maps column IDs to ColumnBase classes.  A column ID is any
    hashable object, but you probably want strings like 'name', 'id', 'date',
    etc.

    `columns_wanted` is a sequence of column IDs.

    `items` is a sequence of arbitrary objects that are used to create cell
    objects by passing them to the classes in `COLUMN_SPECS`.
    """

    # Create two-dimensional list to represent a table.  Each cell must be a
    # ColumnBase instance (see columns.tlist module).
    rows  = []
    for item in items:
        row = []
        for i,colname in enumerate(columns_wanted):
            cell = COLUMN_SPECS[colname](item)
            cell.index = i
            row.append(cell)
        rows.append(row)

    delimiter = '\t' if TERMSIZE.columns is None else '│'

    # Whether to print for a human or for a machine to read our output
    pretty_output = all(x is not None for x in (TERMSIZE.columns, TERMSIZE.lines))

    def assemble_line(row):
        line = []
        for cell in row:
            if pretty_output:
                line.append(cell.get_string())
            else:
                line.append(str(cell.get_raw()))
        return delimiter.join(line)

    def assemble_headers():
        # This must be called after shrink_and_expand_to_fit() so we can
        # grab the final column widths from the first row.
        widths = tuple(cell.width for cell in rows[0])
        headers = []
        for colname,width in zip(columns_wanted, widths):
            header_items = COLUMN_SPECS[colname].header
            left  = header_items.get('left', '')
            right = header_items.get('right', '')
            space = ' '*(width - len(left) - len(right))
            header = ''.join((left, space, right))[:width]
            headers.append(header)
        return delimiter.join(headers)

    def shrink_and_expand_to_fit():
        log.debug('TTY width is %dx%d', TERMSIZE.columns, TERMSIZE.lines)

        def get_max_colwidth(colindex):
            # Return width of widest cell in all rows
            colname = columns_wanted[colindex]
            header = COLUMN_SPECS[colname].header
            header_width = strwidth(''.join((header.get('left', ''), header.get('right', ''))))
            max_cell_width = max(strwidth(row[colindex].get_string()) for row in rows)
            return max(header_width, max_cell_width)

        def set_colwidth(colindex, width):
            # Set column width of all rows
            for row in rows:
                cell = row[colindex]
                cell.width = width

        def widest_columns():
            # List of columns sorted by width
            return sorted(range(len(columns_wanted)),
                          key=lambda colindex: get_max_colwidth(colindex),
                          reverse=True)

        # Expand column widths to make all cell values fit
        for colindex in range(len(columns_wanted)):
            colwidth = get_max_colwidth(colindex)
            set_colwidth(colindex, colwidth)

        # Rows should have identical column widths from now on, so we can
        # use the first row to check our progress.
        current_line = assemble_line(rows[0])
        current_width = strwidth(current_line)
        while current_width > TERMSIZE.columns:
            excess = current_width - TERMSIZE.columns
            widest = widest_columns()
            widest_0 = get_max_colwidth(widest[0])
            widest_1 = get_max_colwidth(widest[1])

            # Shorten widest column by difference to second widest column
            # (leaving them at the same width), but not by more than `excess`
            # characters and at least one character.

            # TODO: This is very slow when listing lots of rows in a small
            # terminal because the widest column is shrunk by only 1 character
            # before checking again.
            shorten_by = max(1, min(excess, widest_0 - widest_1))
            set_colwidth(widest[0], widest_0 - shorten_by)

            current_line = assemble_line(rows[0])
            current_width = strwidth(current_line)

    if rows:
        if not pretty_output:
            log.debug('Could not detect TTY size - assuming stdout is no TTY')
            headerstr = None
        elif TERMSIZE.columns < len(columns_wanted)*3:
            log.error('Terminal is too narrow for %d columns', len(columns_wanted))
            return False
        else:
            shrink_and_expand_to_fit()
            headerstr = '\033[1;4m' + assemble_headers() + '\033[0m'

        for linenum,row in enumerate(rows):
            if headerstr is not None and \
               linenum % (TERMSIZE.lines-1) == 0:
                log.info(headerstr)
            log.info(assemble_line(row))
