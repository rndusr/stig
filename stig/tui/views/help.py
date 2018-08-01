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

import urwid
from ...utils.string import strwidth


class HelpText(urwid.WidgetWrap):
    def __init__(self, lines):
        self._lines = lines
        self._pile = urwid.Pile([
            urwid.Text(line) for line in lines
        ])
        super().__init__(self._pile)

    @property
    def secondary_filter(self):
        return getattr(self, '_secondary_filter', None)

    @secondary_filter.setter
    def secondary_filter(self, term):
        prev_secondary_filter = getattr(self, '_secondary_filter', None)
        if (term is None or not str(term)) and prev_secondary_filter:
            self._clear_matches()
        elif term != prev_secondary_filter:
            self._highlight_matches(term)

    def _clear_matches(self):
        self._secondary_filter = None
        self._w = urwid.Pile([urwid.Text(line) for line in self._lines])

    def _highlight_matches(self, term):
        self._secondary_filter = term = str(term)

        term_cf = term.casefold()
        case_sensitive = term != term_cf
        def match_boundaries(line):
            """Yield (start, stop) tuple for each occurence of `term` in `line`"""
            start = stop = -1
            if not term:
                yield (start, stop)

            def positions_of(term, line):
                start = line.find(term)
                while start > -1:
                    stop = start + strwidth(term)
                    yield (start, stop)

                    # Find next start
                    offset = line[stop:].find(term)
                    if offset > -1:
                        start = stop + offset
                    else:
                        start = -1

            if case_sensitive:
                yield from positions_of(term, line)
            else:
                yield from positions_of(term_cf, line.casefold())

        texts = []
        for line in self._lines:
            line_parts = []

            # Highlight all matches in the line
            prev_hl_stop = 0
            for hl_start,hl_stop in match_boundaries(line):
                before_hl = line[prev_hl_stop:hl_start]
                hl = line[hl_start:hl_stop]
                if before_hl: line_parts.append(before_hl)
                if hl: line_parts.append(('prompt', hl))
                prev_hl_stop = hl_stop

            # Append everything after the final match in the line
            line_parts.append(line[prev_hl_stop:])
            texts.append(urwid.Text(line_parts))

        # This calls _invalidate()
        self._w = urwid.Pile(texts)
