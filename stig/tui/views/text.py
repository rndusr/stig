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
        self._match_indexes = None
        self._render_action = None
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
        phrase = str(phrase)
        prev_search_phrase = self._search_phrase
        self._match_indexes = None
        if not phrase and prev_search_phrase:
            self._search_phrase = None
            self._case_sensitive = None
            self._clear_matches()
        elif phrase != prev_search_phrase:
            # Case-insensitive matching if phrase is equal to casefolded phrase
            phrase_cf = phrase.casefold()
            case_sensitive = phrase != phrase_cf
            if not case_sensitive:
                # Do case-insensitive matching
                phrase = phrase_cf
            self._search_phrase = phrase
            self._case_sensitive = case_sensitive
            self._highlight_matches()

    def _clear_matches(self):
        scrollpos = self._w.get_scrollpos()
        self._w = self._make_content([urwid.Text(line) for line in self._lines])
        self._w.set_scrollpos(scrollpos)

    def _highlight_matches(self):
        scrollpos = self._w.get_scrollpos()
        phrase = self._search_phrase
        case_sensitive = self._case_sensitive

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
                yield from positions_of(phrase, line.casefold())

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

        # Restore scrolling position which was lost when content changed
        self._w.set_scrollpos(scrollpos)

    _JUMP_TO_NEXT_MATCH = object()
    _JUMP_TO_PREV_MATCH = object()
    _MAYBE_JUMP_TO_NEXT_MATCH = object()
    _MAYBE_JUMP_TO_PREV_MATCH = object()

    def _assert_search_phrase_not_None(self):
        if self._search_phrase is None:
            raise RuntimeError("Can't jump to next match with search_phrase set to None")

    def jump_to_next_match(self):
        self._assert_search_phrase_not_None()
        self._render_action = self._JUMP_TO_NEXT_MATCH
        self._invalidate()

    def jump_to_prev_match(self):
        self._assert_search_phrase_not_None()
        self._render_action = self._JUMP_TO_PREV_MATCH
        self._invalidate()

    def maybe_jump_to_next_match(self):
        """Jump to next match if nothing matches on the current page"""
        if self._search_phrase:
            self._assert_search_phrase_not_None()
            self._render_action = self._MAYBE_JUMP_TO_NEXT_MATCH
            self._invalidate()

    def maybe_jump_to_prev_match(self):
        """Jump to previous match if nothing matches on the current page"""
        if self._search_phrase:
            self._assert_search_phrase_not_None()
            self._render_action = self._MAYBE_JUMP_TO_PREV_MATCH
            self._invalidate()

    def render(self, size, focus=False):
        ra = self._render_action
        if self._search_phrase is not None and ra is not None:
            # Calculate indexes of matching rows on the canvas
            if self._match_indexes is None:
                self._find_match_indexes(size)

            # Move next/previous match to the top of the canvas
            if ra is self._JUMP_TO_NEXT_MATCH:
                self._jump_to_next_match(size)
            elif ra is self._JUMP_TO_PREV_MATCH:
                self._jump_to_prev_match(size)

            # Same as above, but only if there are no matches visible
            elif ra is self._MAYBE_JUMP_TO_NEXT_MATCH:
                if not self._any_matches_on_current_page(size):
                    self._jump_to_next_match(size)
            elif ra is self._MAYBE_JUMP_TO_PREV_MATCH:
                if not self._any_matches_on_current_page(size):
                    self._jump_to_prev_match(size)

            self._render_action = None
        return super().render(size, focus)

    def _jump_to_next_match(self, size):
        scrollpos = self._w.get_scrollpos()
        for i in self._match_indexes:
            if i > scrollpos:
                self._w.set_scrollpos(i)
                break

    def _jump_to_prev_match(self, size):
        scrollpos = self._w.get_scrollpos()
        for i in reversed(self._match_indexes):
            if i < scrollpos:
                self._w.set_scrollpos(i)
                break

    def _any_matches_on_current_page(self, size):
        viewport_min = self._w.get_scrollpos()
        viewport_max = viewport_min + size[1] - 1
        for i in self._match_indexes:
            if viewport_min <= i <= viewport_max:
                return True
        return False

    def _find_match_indexes(self, size):
        phrase = self._search_phrase
        case_sensitive = self._case_sensitive

        def row_matches(row):
            for _,_,text in row:
                text_dec = text.decode()
                if case_sensitive and phrase in text_dec:
                    return True
                elif not case_sensitive and phrase in text_dec.casefold():
                    return True
            return False

        # Render the full Pile canvas because long lines can cause line breaks
        # and so we can't just get indexes from self._lines.
        full_canv = self._w.base_widget.render((size[0],), False)
        indexes = []
        for i,row in enumerate(full_canv.content()):
            text = ''.join(p[2].decode() for p in row).strip()
            if row_matches(row):
                indexes.append(i)
        self._match_indexes = indexes
