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

    def __init__(self, prompt='', on_change=None, on_move=None, on_accept=None,
                 on_cancel=None, on_complete=None, completer_class=None,
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
        self._on_complete = blinker.Signal()

        # Completion
        self.completer_class = completer_class
        self._completer = None
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
        if self._completer_class is not None:
            self.on_complete(self._cb_complete)
            self.on_change(self._cb_change)
            self.on_move(self._cb_move)

        # User callbacks
        if on_change is not None: self.on_change(on_change, autoremove=False)
        if on_move is not None: self.on_move(on_move, autoremove=False)
        if on_accept is not None: self.on_accept(on_accept, autoremove=False)
        if on_cancel is not None: self.on_cancel(on_cancel, autoremove=False)
        if on_complete is not None: self.on_complete(on_complete, autoremove=False)

    def on_accept(self, callback, autoremove=True):
        self._on_accept.connect(callback, weak=autoremove)

    def on_cancel(self, callback, autoremove=True):
        self._on_cancel.connect(callback, weak=autoremove)

    def on_complete(self, callback, autoremove=True):
        self._on_complete.connect(callback, weak=autoremove)

    def on_change(self, callback, autoremove=True):
        self._on_change.connect(callback, weak=autoremove)

    def on_move(self, callback, autoremove=True):
        self._on_move.connect(callback, weak=autoremove)

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
        elif cmd is urwid.COMPLETE and self._on_complete:
            callbacks.append(self._on_complete)
            key = None
        elif key == 'space':
            key = super().keypress(size, ' ')
        else:
            key = super().keypress(size, key)

        text_after = self._editw.edit_text
        curpos_after = self._editw.edit_pos
        if text_before != text_after:
            callbacks.append(self._on_change)
        elif curpos_before != curpos_after:
            callbacks.append(self._on_move)

        for cb in callbacks:
            if cb is not None:
                cb.send(self)

        return key

    def reset(self):
        """Clear the command line and reset internal states"""
        self._editw.edit_text = ''
        self._groupw.hide('candidates')
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
    @edit_text.setter
    def edit_pos(self, pos):
        self._editw.edit_pos = int(pos)


    # Completion

    @property
    def completer_class(self):
        return self._completer_class
    @completer_class.setter
    def completer_class(self, cls):
        self._completer_class = cls

        if cls is not None:
            # Make sure our internal callbacks are connected
            def ensure_cb(signal, cb):
                if cb not in (ref() for ref in self._on_complete.receivers.values()):
                    signal.connect(cb)
            ensure_cb(self._on_complete, self._cb_complete)
            ensure_cb(self._on_change, self._cb_change)
            ensure_cb(self._on_move, self._cb_move)
        else:
            # Make sure our internal callbacks are disconnected
            self._on_complete.disconnect(self._cb_complete)
            self._on_change.disconnect(self._cb_change)
            self._on_move.disconnect(self._cb_move)

    def _cb_complete(self, _):
        self._restore_cmdline()

        if self._completer is None:
            self._update_completion_candidates()

        if self._prev_key_was_tab:
            self._candsw.cycle('next')
            self._fill_in_focused_candidate()
        else:
            # Complete what the user typed
            self._complete_edit_text()
            completion_was_finalized = len(self._completer.candidates) == 1

            # Display what is left after (partial) completion
            self._update_completion_candidates()

            if completion_was_finalized:
                self._save_cmdline()
                self._prev_key_was_tab = False
            else:
                # Insert first candidate in command line
                self._fill_in_focused_candidate()
                self._prev_key_was_tab = True

            # Display candidates if there are any or hide the menu
            self._maybe_hide_or_show_menu()

    def _cb_change(self, _):
        # Update candidate list whenever edit text is changed
        self._update_completion_candidates()
        self._prev_key_was_tab = False
        self._save_cmdline()
        self._maybe_hide_or_show_menu()

    def _cb_move(self, _):
        # Candidates are based on where the cursor is in the command line
        self._prev_key_was_tab = False
        self._update_completion_candidates()
        self._maybe_hide_or_show_menu()

    def _update_completion_candidates(self):
        # Parse the current command line to get a list of candidates we can display
        self._completer = self._completer_class(self._editw.edit_text, self._editw.edit_pos)
        self._candsw.update(self._completer.candidates)



    def _fill_in_focused_candidate(self):
        # TODO: There must be a more efficient way to do this.
        candidate = self._candsw.focused_candidate
        if candidate is not None:
            log.debug('Selecting focused candidate: %r', candidate)
            cmdline = self._editw.edit_text
            curpos = self._editw.edit_pos
            before_cursor = cmdline[:curpos]
            for i in reversed(range(len(candidate)+1)):
                if before_cursor.endswith(candidate[:i]):
                    self._editw.edit_text = ''.join((
                        self._editw.edit_text[:self._editw.edit_pos],
                        candidate[i:],
                        self._editw.edit_text[self._editw.edit_pos:]
                    ))
                    self._editw.edit_pos += len(candidate[i:])
                    break






    def _maybe_hide_or_show_menu(self):
        log.debug('%d candidates: %r', len(self._completer.candidates), self._completer.candidates)
        candsw_visible = self._groupw.visible('candidates')
        if len(self._completer.candidates) > 0:
            self._candsw.update(self._completer.candidates)
            if not candsw_visible:
                log.debug('Showing completion menu')
                self._groupw.show('candidates')
        elif candsw_visible:
            log.debug('Hiding completion menu')
            self._groupw.hide('candidates')

    def _complete_edit_text(self):
        self._editw.edit_text, self._editw.edit_pos = self._completer.complete()
        log.debug('Completed edit text: %r, %r', self._editw.edit_text, self._editw.edit_pos)

    def _save_cmdline(self):
        self._user_input = (self._editw.edit_text, self._editw.edit_pos)
        log.debug('Saved command line: %r', self._user_input)

    def _restore_cmdline(self):
        if self._user_input is not None:
            self._editw.edit_text, self._editw.edit_pos = self._user_input
            log.debug('Restored command line: %r', (self._editw.edit_text, self._editw.edit_pos))


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
        self._walker = urwid.SimpleFocusListWalker([])
        self._listbox = urwid.ListBox(self._walker)
        super().__init__(
            urwid.AttrMap(ScrollBar(
                urwid.AttrMap(self._listbox, 'completion')
            ), 'completion.scrollbar')
        )

    def reset(self):
        self.update(())

    def update(self, cands):
        old_cands = tuple(widget.base_widget.text
                          for widget in self._walker)
        if old_cands != cands:
            self._walker[:] = ()
            for pos,cand in enumerate(sorted(cands, key=str.lower)):
                self._walker.append(
                    self._mk_widget(cand, selected=pos==0)
                )

    def _mk_widget(self, cand, selected=False):
        return urwid.AttrMap(urwid.Padding(urwid.Text(cand)),
                             'completion.item', 'completion.item.focused')

    def cycle(self, direction):
        if not self._walker:
            pass  # Empty list
        else:
            lb = self._listbox
            maxpos =  len(self._walker) - 1
            if direction == 'next':
                if lb.focus_position < maxpos:
                    lb.focus_position += 1
                else:
                    lb.focus_position = 0
                self._invalidate()
            elif direction == 'prev':
                if lb.focus_position > 0:
                    lb.focus_position -= 1
                else:
                    lb.focus_position = maxpos
                self._invalidate()
            else:
                raise RuntimeError('Invalid direction: %r', direction)

    @property
    def focused_candidate(self):
        if self._walker:
            return self._listbox.focus.base_widget.text
        else:
            return None

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
