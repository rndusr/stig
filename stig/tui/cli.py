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

import asyncio
import os

import blinker
import urwid

from .group import Group
from .scroll import ScrollBar

from ..logging import make_logger  # isort:skip
log = make_logger(__name__)


class CLIEditWidget(urwid.WidgetWrap):
    """Readline Edit widget with history and completion"""

    def __init__(self, prompt='', on_change=None, on_move=None, on_accept=None, on_cancel=None,
                 on_complete_next=None, on_complete_prev=None, completer=None,
                 history_file=None, history_size=1000, **kwargs):
        # Widgets
        self._editw = urwid.Edit(prompt, wrap='clip')
        self._candsw = CompletionCandidatesWidget(completer)
        self._groupw = Group(cls=urwid.Pile)
        self._groupw.add(name='candidates', widget=self._candsw, visible=False, options=10)
        self._groupw.add(name='cmdline', widget=self._editw, visible=True, options='pack')
        super().__init__(self._groupw)

        # Callbacks
        self._on_change = blinker.Signal()
        self._on_move = blinker.Signal()
        self._on_accept = blinker.Signal()
        self._on_cancel = blinker.Signal()
        self._on_complete_next = blinker.Signal()
        self._on_complete_prev = blinker.Signal()

        # Completion
        self._completer = completer
        self._on_complete_next.connect(self._cb_complete_next)
        self._on_complete_prev.connect(self._cb_complete_prev)
        self._on_change.connect(self._cb_change)
        self._on_move.connect(self._cb_move)
        self._user_input = None

        # History
        self._history = []
        self._history_size = history_size
        self._history_pos = -1
        self.history_file = history_file
        self._current_edit_text = ''

        # Internal callbacks
        self.on_cancel(lambda _: self.reset(), autoremove=False)

        # User callbacks
        if on_change is not None: self.on_change(on_change, autoremove=False)
        if on_move is not None: self.on_move(on_move, autoremove=False)
        if on_accept is not None: self.on_accept(on_accept, autoremove=False)
        if on_cancel is not None: self.on_cancel(on_cancel, autoremove=False)
        if on_complete_next is not None: self.on_complete_next(on_complete_next, autoremove=False)
        if on_complete_prev is not None: self.on_complete_prev(on_complete_prev, autoremove=False)

    def on_accept(self, callback, autoremove=True):
        self._on_accept.connect(callback, weak=autoremove)

    def on_cancel(self, callback, autoremove=True):
        self._on_cancel.connect(callback, weak=autoremove)

    def on_change(self, callback, autoremove=True):
        self._on_change.connect(callback, weak=autoremove)

    def on_move(self, callback, autoremove=True):
        self._on_move.connect(callback, weak=autoremove)

    def on_complete_next(self, callback, autoremove=True):
        self._on_complete_next.connect(callback, weak=autoremove)

    def on_complete_prev(self, callback, autoremove=True):
        self._on_complete_prev.connect(callback, weak=autoremove)

    def keypress(self, size, key):
        text_before = self._editw.edit_text
        curpos_before = self._editw.edit_pos

        callbacks = []
        cmd = self._editw._command_map[key]
        if cmd is urwid.CURSOR_UP:
            self._set_history_prev()
            key = None
        elif cmd is urwid.CURSOR_DOWN:
            self._set_history_next()
            key = None
        elif cmd is urwid.ACTIVATE:
            self.append_to_history()
            callbacks.append(self._on_accept)
            self._history_pos = -1
            key = None
        elif cmd is urwid.CANCEL:
            callbacks.append(self._on_cancel)
            self._history_pos = -1
            key = None
        elif cmd is urwid.COMPLETE_NEXT:
            callbacks.append(self._on_complete_next)
            key = None
        elif cmd is urwid.COMPLETE_PREV:
            callbacks.append(self._on_complete_prev)
            key = None
        elif key == 'space':
            key = super().keypress(size, ' ')
        else:
            key = super().keypress(size, key)

        if text_before != self._editw.edit_text:
            callbacks.append(self._on_change)
        elif curpos_before != self._editw.edit_pos:
            callbacks.append(self._on_move)

        for cb in callbacks:
            if cb is not None:
                cb.send(self)

        return key

    def reset(self):
        """Clear the command line and reset internal states"""
        self._editw.edit_text = ''
        self._groupw.hide('candidates')
        if self._completer is not None:
            self._completer.reset()
            self._candsw.reset()

    @property
    def edit_text(self):
        """Current editable text"""
        return self._editw.edit_text

    @edit_text.setter
    def edit_text(self, cmd):
        self._editw.edit_text = str(cmd)

    @property
    def edit_pos(self):
        """Current cursor position in the editable text"""
        return self._editw.edit_pos

    @edit_pos.setter
    def edit_pos(self, pos):
        self._editw.edit_pos = int(pos)

    # Completion

    def _cb_complete_next(self, _):
        self._complete('next')

    def _cb_complete_prev(self, _):
        self._complete('prev')

    def _complete(self, direction):
        compl = self._completer
        if compl is not None:
            if direction == 'next':
                self._editw.edit_text, self._editw.edit_pos = compl.complete_next()
            elif direction == 'prev':
                self._editw.edit_text, self._editw.edit_pos = compl.complete_prev()
            else:
                raise ValueError('direction must be "next" or "prev"')
            log.debug('Completed: %r, %r', self._editw.edit_text, self._editw.edit_pos)
            self._candsw.update_candidates()

    def _cb_change(self, _):
        # Update candidate list whenever edit text is changed
        self._update_completion_candidates()

    def _cb_move(self, _):
        # Candidates are based on where the cursor is in the command line
        self._update_completion_candidates()

    def _update_completion_candidates(self):
        if self._completer is not None:
            # If the previously scheduled call isn't finished yet, abort it
            # because it's results will be out of date.
            old_task = getattr(self, '_completion_update_task', None)
            if old_task is not None and not old_task.done():
                old_task.cancel()

            def callback(task):
                try:
                    task.result()
                except asyncio.CancelledError:
                    pass
                else:
                    self._candsw.update_candidates()
                    self._maybe_hide_or_show_menu()

            coro = self._completer.update(self._editw.edit_text, self._editw.edit_pos)
            self._completion_update_task = asyncio.ensure_future(coro)
            self._completion_update_task.add_done_callback(callback)

    def _maybe_hide_or_show_menu(self):
        if self._completer is not None:
            candsw_visible = self._groupw.visible('candidates')
            any_matches = len(self._completer.categories) > 1  # First is current user input
            if any_matches and not candsw_visible:
                log.debug('Showing completion menu')
                self._groupw.show('candidates')
            elif not any_matches and candsw_visible:
                log.debug('Hiding completion menu')
                self._groupw.hide('candidates')

    # History

    # The most recent history entry is at index 0; -1 used to represent the current line
    # that is not yet in history and stored outside of self._history.

    def _set_history_prev(self):
        if self._history_pos == -1:
            self._current_edit_text = self._editw.edit_text
        if self._history_pos + 1 < len(self._history):
            self._history_pos += 1
            self._editw.edit_text = self._history[self._history_pos]
            self._editw.set_edit_pos(len(self._editw.edit_text))

    def _set_history_next(self):
        if self._history_pos > -1:
            self._history_pos -= 1
            if self._history_pos == -1:
                self._editw.edit_text = self._current_edit_text
            else:
                self._editw.edit_text = self._history[self._history_pos]
            self._editw.set_edit_pos(len(self._editw.edit_text))

    def _read_history(self):
        if self._history_file:
            self._history = list(reversed(_read_lines(self._history_file)))

    def append_to_history(self):
        """Add current `edit_text` to history"""
        # Don't add the same line twice in a row
        new_line = self._editw.edit_text
        if self._history and self._history[0] == new_line:
            return
        self._history.insert(0, new_line)
        if self._history_file is not None:
            _append_line(self._history_file, new_line)
        self._trim_history()

    def _trim_history(self):
        max_size = self._history_size
        if len(self._history) > max_size:
            # Trim history in memory
            self._history[:] = self._history[:max_size]

        if len(self._history) > 0 and self._history_file:
            # Trim history on disk
            flines = _read_lines(self._history_file)
            if len(flines) > max_size:
                # Trim more than necessary to reduce number of writes
                overtrim = max(0, min(int(self._history_size / 2), 10))
                flines = flines[overtrim:]
                _write_lines(self._history_file, flines)

    @property
    def history_file(self):
        return self._history_file

    @history_file.setter
    def history_file(self, path):
        if path is None:
            self._history_file = None
        else:
            if _mkdir(os.path.dirname(path)) and _test_access(path):
                self._history_file = os.path.abspath(os.path.expanduser(path))
                log.debug('Setting history_file=%r', self._history_file)
                self._read_history()

    @property
    def history_size(self):
        """Maximum number of lines kept in history"""
        return self._history_size

    @history_size.setter
    def history_size(self, size):
        self._history_size = int(size)
        self._trim_history()


class CompletionCandidatesWidget(urwid.WidgetWrap):
    def selectable(self):
        return False

    def __init__(self, completer):
        self._completer = completer
        self._listbox = urwid.ListBox(urwid.SimpleFocusListWalker([]))
        super().__init__(
            urwid.AttrMap(ScrollBar(
                urwid.AttrMap(self._listbox, 'completion')
            ), 'completion.scrollbar')
        )

    def reset(self):
        self._listbox.body[:] = ()

    def render(self, size, focus=False):
        # Always render as focused to highlight the focused candidate
        return super().render(size, focus=True)

    def update_candidates(self):
        if not self._completer.categories:
            self.reset()
        else:
            cats = self._completer.categories

            def cat_widget_cols(cands):
                column_titles = []
                column_titles.append(cands.label)
                for cand in cands:
                    for title in cand.info:
                        if title not in column_titles:
                            column_titles.append(title)
                column_titles = tuple(urwid.Text(title) for title in column_titles)
                return urwid.Columns(column_titles)

            def cat_widget(cands):
                return urwid.AttrMap(urwid.Padding(cat_widget_cols(cands)), 'completion.category', 'default')

            def cand_widget(cand):
                if cand.in_parens:
                    cols = [urwid.Text('%s (%s)' % (cand, cand.in_parens))]
                else:
                    cols = [urwid.Text(cand)]
                for column_text in cand.info.values():
                    cols.append(urwid.Text(column_text))
                return urwid.AttrMap(urwid.Padding(urwid.Columns(cols)),
                                     'completion.item', 'completion.item.focused')

            widgets = []
            for cands in cats:
                if cands.label:
                    widgets.append(cat_widget(cands))
                for cand in cands:
                    widgets.append(cand_widget(cand))
            self._listbox.body[:] = widgets

            # Change focus position
            # Candidates are rendered as a flat list, which means we have to
            # calculate the focus_position, skipping category headers. Having
            # each category in a separate ListBox would be nicer, but nested
            # ListBoxes don't seem to work correctly: If the focused item is
            # moved out of view, the view doesn't scroll to follow it.
            cats = self._completer.categories
            if cats.current:
                pos = 0
                if cats.current_index > 0:
                    for cands in cats[:cats.current_index]:
                        if cands.label:
                            pos += 1
                        pos += len(cands)
                if cats.current.label:
                    pos += 1
                pos += cats.current.current_index
                self._listbox.focus_position = pos


def _mkdir(path):
    try:
        if path and not os.path.exists(path):
            os.makedirs(path)
    except OSError as e:
        log.error("Can't create directory {}: {}".format(path, e.strerror))
    else:
        return True


def _test_access(path):
    if path.startswith('/dev/null'):
        return True
    try:
        with open(path, 'a'): pass
    except OSError as e:
        log.error("Can't read/write history file {}: {}".format(path, e.strerror))
    else:
        return True


def _read_lines(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return [line.strip() for line in f.readlines()]
        except OSError as e:
            log.error("Can't read history file {}: {}"
                      .format(filepath, e.strerror))
    return []


def _write_lines(filepath, lines):
    try:
        with open(filepath, 'w') as f:
            for line in lines:
                f.write(line.strip('\n') + '\n')
    except OSError as e:
        log.error("Can't write history file {}: {}".format(filepath, e.strerror))
    else:
        return True


def _append_line(filepath, line):
    try:
        with open(filepath, 'a') as f:
            f.write(line.strip() + '\n')
    except OSError as e:
        log.error("Can't append to history file {}: {}".format(filepath, e.strerror))
    else:
        return True
