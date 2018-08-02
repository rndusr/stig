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
from ...tui.main import keymap


class HelpText(urwid.WidgetWrap):
    keymap_context = 'helptext'

    def __init__(self, lines):
        self._lines = lines
        self._search_phrase = None

        self._Pile_Keymapped = keymap.wrap(urwid.Pile, context=self.keymap_context)
        pile = self._Pile_Keymapped([urwid.Text(line) for line in lines])
        super().__init__(pile)

    @property
    def search_phrase(self):
        return self._search_phrase

    @search_phrase.setter
    def search_phrase(self, phrase):
        prev_search_phrase = self._search_phrase
        if (phrase is None or not str(phrase)) and prev_search_phrase:
            self._clear_matches()
        elif phrase != prev_search_phrase:
            self._highlight_matches(phrase)

    def _clear_matches(self):
        self._search_phrase = None
        self._w = self._Pile_Keymapped([urwid.Text(line) for line in self._lines])

    def _highlight_matches(self, phrase):
        self._search_phrase = phrase = str(phrase)

        phrase_cf = phrase.casefold()
        case_sensitive = phrase != phrase_cf
        def match_boundaries(line):
            """Yield (start, stop) tuple for each occurence of `phrase` in `line`"""
            start = stop = -1
            if not phrase:
                yield (start, stop)

            def positions_of(phrase, line):
                start = line.find(phrase)
                log.debug('%r in %r: %r', phrase, line, phrase in line)
                while start > -1:
                    stop = start + strwidth(phrase)
                    yield (start, stop)

                    # Find next start
                    offset = line[stop:].find(phrase)
                    if offset > -1:
                        start = stop + offset
                    else:
                        start = -1

            if case_sensitive:
                yield from positions_of(phrase, line)
            else:
                yield from positions_of(phrase_cf, line.casefold())

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
        self._w = self._Pile_Keymapped(texts)
