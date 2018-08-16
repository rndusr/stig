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
from ..scroll import Scrollable


class SearchableText(urwid.WidgetWrap):
    palette_name = 'find.highlight'

    def __init__(self, lines):
        self._lines = lines
        self._search_phrase = None
        self._match_indexes = []
        super().__init__(self._make_content([urwid.Text(line) for line in lines]))

    def _make_content(self, text_widgets):
         return Scrollable(urwid.Pile(text_widgets))

    @property
    def original_widget(self):
        # original_widget is only needed for ScrollBar
        return self._w

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
        curpos = self._w.get_scrollpos()
        self._search_phrase = None
        self._w = self._make_content([urwid.Text(line) for line in self._lines])
        self._w.set_scrollpos(curpos)

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
        palette_name = self.palette_name
        for line_index,line in enumerate(self._lines):
            line_parts = []

            # Highlight all matches in the line
            prev_hl_stop = 0
            for hl_start,hl_stop in match_boundaries(line):
                before_hl = line[prev_hl_stop:hl_start]
                hl = line[hl_start:hl_stop]
                if before_hl: line_parts.append(before_hl)
                if hl: line_parts.append((palette_name, hl))
                prev_hl_stop = hl_stop

            # Append everything after the final match in the line
            line_parts.append(line[prev_hl_stop:])
            texts.append(urwid.Text(line_parts))

        # This calls _invalidate()
        self._w = self._make_content(texts)

    def render(self, size, focus=False):
        phrase = self._search_phrase
        indexes = self._match_indexes
        indexes.clear()

        if phrase is not None:
            # Case-insensitive matching if phrase is equal to casefolded phrase
            phrase_cf = phrase.casefold()
            case_sensitive = phrase == phrase_cf
            if case_sensitive:
                phrase = phrase_cf

            # Render the full Pile of rows because extra long lines cause line
            # breaks and so we can't just get indexes from self._lines.
            pile = self._w.base_widget
            full_canv = pile.render((size[0],), focus)

            # Find indexes of matching rows in full Pile of rows
            for i,row in enumerate(full_canv.content()):
                for attr,cs,text in row:
                    text_dec = text.decode()
                    if (case_sensitive and phrase in text_dec or
                        phrase_cf in text_dec.casefold()):
                        indexes.append(i)
                        break

        # Now we can render the actual canvas and throw away the full canvas
        return super().render(size, focus)

    def jump_to_next_match(self):
        self._assert_search_phrase_not_None()
        curpos = self._w.get_scrollpos()
        for i in self._match_indexes:
            if i > curpos:
                self._w.set_scrollpos(i)
                break

    def jump_to_prev_match(self):
        self._assert_search_phrase_not_None()
        curpos = self._w.get_scrollpos()
        for i in reversed(self._match_indexes):
            if i < curpos:
                self._w.set_scrollpos(i)
                break

    def _assert_search_phrase_not_None(self):
        if self._search_phrase is None:
            raise RuntimeError("Can't jump to next match with search_phrase set to None")
