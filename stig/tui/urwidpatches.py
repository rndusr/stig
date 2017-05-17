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

"""Monkey patches that should be removed when they are resolved upstream"""

import urwid

# Add more actions for key bindings
urwid.CURSOR_WORD_LEFT = 'cursor word left'
urwid.CURSOR_WORD_RIGHT = 'cursor word right'
urwid.DELETE_TO_EOL = 'delete to end of line'
urwid.DELETE_LINE = 'delete line'
urwid.DELETE_CHAR_UNDER_CURSOR = 'delete char under cursor'
urwid.DELETE_WORD_LEFT = 'delete word left'
urwid.DELETE_WORD_RIGHT = 'delete word right'
urwid.CANCEL = 'cancel'


# Limit the impact of the high CPU load bug
# https://github.com/urwid/urwid/pull/86
# https://github.com/urwid/urwid/issues/90
from distutils.version import LooseVersion
if LooseVersion(urwid.__version__) <= LooseVersion('1.3.1'):
    urwid.AsyncioEventLoop._idle_emulation_delay = 1/25


# Raise UnicodeDecodeError properly
# https://github.com/urwid/urwid/pull/92
# https://github.com/urwid/urwid/pull/196
class AsyncioEventLoop_patched(urwid.AsyncioEventLoop):
    def _exception_handler(self, loop, context):
        exc = context.get('exception')
        if exc:
            loop.stop()
            if not isinstance(exc, urwid.ExitMainLoop):
                self._exc_info = exc
        else:
            loop.default_exception_handler(context)

    def run(self):
        """
        Start the event loop.  Exit the loop when any callback raises
        an exception.  If ExitMainLoop is raised, exit cleanly.
        """
        self._loop.set_exception_handler(self._exception_handler)
        self._loop.run_forever()
        if self._exc_info:
            raise self._exc_info

urwid.AsyncioEventLoop = AsyncioEventLoop_patched


class ListBox_patched(urwid.ListBox):
    def keypress(self, size, key):
        # Offer key to focused widget first
        # https://github.com/urwid/urwid/pull/233
        focused_widget = self.focus
        if focused_widget is not None and focused_widget.selectable() and \
           focused_widget.keypress((size[0],), key) is None:
            return None

        # Add support for home/end keys
        # https://github.com/urwid/urwid/pull/229
        key = super().keypress(size, key)
        if self.focus is not None:
            if key == 'home':
                self.focus_position = next(iter(self.body.positions()))
                self.set_focus_valign('top')
                self._invalidate()
                return None
            elif key == 'end':
                self.focus_position = next(iter(self.body.positions(reverse=True)))
                self.set_focus_valign('bottom')
                self._invalidate()
                return None
        return key


    # Add support for ScrollBar class (see stig.tui.scroll)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rows_max = None

    def _invalidate(self):
        super()._invalidate()
        self._rows_max = None

    def get_scrollpos(self, size, focus=False):
        """Current scrolling position

        Lower limit is 0, upper limit is the highest index of `body`.
        """
        middle, top, bottom = self.calculate_visible(size, focus)
        if middle is None:
            return 0
        else:
            offset_rows, _, focus_pos, _, _ = middle
            maxcol, maxrow = size
            flow_size = (maxcol,)

            body = self.body
            if hasattr(body, 'positions'):
                # For body[pos], pos can be anything, not just an int.  In that
                # case, the positions() method returns an interable of valid
                # positions.
                positions = tuple(self.body.positions())
                focus_index = positions.index(focus_pos)
                widgets_above_focus = (body[pos] for pos in positions[:focus_index])
            else:
                # Treat body like a normal list
                widgets_above_focus = (w for w in body[:focus_pos])

            rows_above_focus = sum(w.rows(flow_size) for w in widgets_above_focus)
            rows_above_top = rows_above_focus - offset_rows
            return rows_above_top

    def rows_max(self, size, focus=False):
        if self._rows_max is None:
            flow_size = (size[0],)
            body = self.body
            if hasattr(body, 'positions'):
                self._rows_max = sum(body[pos].rows(flow_size) for pos in body.positions())
            else:
                self._rows_max = sum(w.rows(flow_size) for w in self.body)
        return self._rows_max

urwid.ListBox = ListBox_patched
