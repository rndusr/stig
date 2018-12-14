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

from ..logging import make_logger
log = make_logger(__name__)

import urwid
import os
import blinker

from .group import Group
from .scroll import ScrollBar


class CLIEditWidget(urwid.WidgetWrap):
    """Readline Edit widget with history and completion"""

    def __init__(self, prompt='', on_change=None, on_move=None, on_accept=None, on_cancel=None,
                 on_complete_next=None, on_complete_prev=None, completer=None,
                 history_file=None, history_size=1000, **kwargs):
        # Widgets
        self._editw = urwid.Edit(prompt, wrap='clip')
        self._candsw = CompletionCandidatesWidget()
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
        self._prev_key_was_tab = False

        # History
        self._history = []
        self._history_size = history_size
        self._history_pos = -1
        self.history_file = history_file
        self._edit_text_cache = ''

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
        if self._completer is not None:
            if direction == 'next':
                self._editw.edit_text, self._editw.edit_pos = self._completer.complete_next()
            elif direction == 'prev':
                self._editw.edit_text, self._editw.edit_pos = self._completer.complete_prev()
            else:
                raise ValueError('direction must be "next" or "prev"')

            log.debug('Completed: %r, %r', self._editw.edit_text, self._editw.edit_pos)
            if self._completer.candidates.current_index is not None:
                log.debug('Setting candidates focus: %r', self._completer.candidates.current_index)
                self._candsw.focus_position = self._completer.candidates.current_index

    def _cb_change(self, _):
        # Update candidate list whenever edit text is changed
        self._prev_key_was_tab = False
        self._update_completion_candidates()

    def _cb_move(self, _):
        # Candidates are based on where the cursor is in the command line
        self._prev_key_was_tab = False
        self._update_completion_candidates()

    def _update_completion_candidates(self):
        if self._completer is not None:
            log.debug('Updating completer: %r, %r', self._editw.edit_text, self._editw.edit_pos)
            self._completer.update(self._editw.edit_text, self._editw.edit_pos)
            # log.debug('New candidates: %r', self._completer.candidates)
            self._candsw.update(self._completer.candidates)
            self._maybe_hide_or_show_menu()

    def _maybe_hide_or_show_menu(self):
        if self._completer is not None:
            # log.debug('%d candidates: %r', len(self._completer.candidates), self._completer.candidates)
            candsw_visible = self._groupw.visible('candidates')
            if self._completer.candidates and not candsw_visible:
                log.debug('Showing completion menu')
                self._groupw.show('candidates')
            elif not self._completer.candidates and candsw_visible:
                log.debug('Hiding completion menu')
                self._groupw.hide('candidates')


    # History

    def _set_history_prev(self):
        # Remember whatever is currently in line when user starts exploring history
        if self._history_pos == -1:
            self._edit_text_cache = self._editw.edit_text
        if self._history_pos+1 < len(self._history):
            self._history_pos += 1
            self._editw.edit_text = self._history[self._history_pos]

    def _set_history_next(self):
        # The most recent history entry is at index 0; -1 is the current line
        # that is not yet in history.
        if self._history_pos > -1:
            self._history_pos -= 1
        if self._history_pos == -1:
            self._editw.edit_text = self._edit_text_cache  # Restore current line
        else:
            self._editw.edit_text = self._history[self._history_pos]

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
                overtrim = max(0, min(int(self._history_size/2), 10))
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

    def __init__(self):
        self._listbox = urwid.ListBox(urwid.SimpleFocusListWalker([]))
        super().__init__(
            urwid.AttrMap(ScrollBar(
                urwid.AttrMap(self._listbox, 'completion')
            ), 'completion.scrollbar')
        )

    def reset(self):
        self.update(())

    def update(self, cands):
        # log.debug('CompletionCandidatesWidget: Updating displayed candidates: %r', cands)
        self._listbox.body[:] = tuple(self._mk_widget(cand) for cand in cands)
        if self._listbox.body:
            self._listbox.focus_position = cands.current_index
            log.debug('CompletionCandidatesWidget: Focusing %r: %r', cands.current_index, cands.current)

    @staticmethod
    def _mk_widget(cand):
        return urwid.AttrMap(urwid.Padding(urwid.Text(cand)),
                             'completion.item', 'completion.item.focused')
    @property
    def focus_position(self):
        return self._listbox.focus_position
    @focus_position.setter
    def focus_position(self, pos):
        self._listbox.focus_position = pos

    def render(self, size, focus=False):
        # Always render as focused to highlight the focused candidate
        return super().render(size, focus=True)


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
