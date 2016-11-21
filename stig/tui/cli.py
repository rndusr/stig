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
import re
import operator
import os


class CLIEditWidget(urwid.Edit):
    """Edit widget with readline keybindings callbacks and a history"""

    def __init__(self, *args, on_change=None, on_accept=None, on_cancel=None,
                 history_file=None, **kwargs):
        kwargs['align'] = kwargs['align'] if 'align' in kwargs else 'left'
        kwargs['wrap'] = kwargs['wrap'] if 'wrap' in kwargs else 'clip'
        self._on_change = on_change
        self._on_accept = on_accept
        self._on_cancel = on_cancel
        self._edit_text_cache = ''
        self._history = []
        self._history_pos = -1
        self.history_file = history_file
        return super().__init__(*args, **kwargs)

    def keypress(self, size, key):
        size = (size[0],)
        text_before = self.get_edit_text()
        if key in ('ctrl a',):
            return super().keypress(size, 'home')
        elif key in ('ctrl e',):
            return super().keypress(size, 'end')
        elif key in ('ctrl f',):
            return super().keypress(size, 'right')
        elif key in ('ctrl b',):
            return super().keypress(size, 'left')

        elif key in ('ctrl p','up'):
            self._set_history_prev()
            key = None
        elif key in ('ctrl n','down'):
            self._set_history_next()
            key = None
        elif key in ('ctrl k',):
            self.edit_text = self.edit_text[:self.edit_pos]
            key = None
        elif key in ('ctrl u',):
            self.set_edit_text('')
            key = None
        elif key in ('ctrl d',):
            return super().keypress(size, 'delete')
        elif key in ('meta f', 'shift right'):
            self.move_to_next_word(forward=True)
            key = None
        elif key in ('meta b', 'shift left'):
            self.move_to_next_word(forward=False)
            key = None
        elif key in ('meta d',):
            start_pos = self.edit_pos
            end_pos = self.move_to_next_word(forward=True)
            if end_pos != None:
                self.set_edit_text(self.edit_text[:start_pos] + self.edit_text[end_pos:])
            self.edit_pos = start_pos
            key = None
        elif key in ('meta delete', 'meta backspace', 'ctrl w'):
            end_pos = self.edit_pos
            start_pos = self.move_to_next_word(forward=False)
            if start_pos != None:
                self.set_edit_text(self.edit_text[:start_pos] + self.edit_text[end_pos:])
            key = None
        elif self._on_accept is not None and key in ('enter',):
            self._append_to_history(self.edit_text)
            self._on_accept(self)
            self._reset()
            key = None
        elif self._on_cancel is not None and key in ('esc','ctrl g'):
            self._on_cancel(self)
            self._reset()
            key = None
        else:
            key = super().keypress(size, key)
        text_after = self.get_edit_text()
        if self._on_change is not None and text_before != text_after:
            self._on_change(self)
        return key

    def move_to_next_word(self, forward=True):
        if forward:
            match_iterator  = re.finditer(r'(\b\W+|$)', self.edit_text,
                                          flags=re.UNICODE)
            match_positions = [m.start() for m in match_iterator]
            op = operator.gt
        else:
            match_iterator  = re.finditer(r'(\w+\b|^)', self.edit_text,
                                          flags=re.UNICODE)
            match_positions = reversed([m.start() for m in match_iterator])
            op = operator.lt
        for pos in match_positions:
            if op(pos, self.edit_pos):
                self.set_edit_pos(pos)
                return pos

    def _reset(self):
        self._history_pos = -1

    def _set_history_prev(self):
        # Remember whatever is currently in line when user starts exploring history
        if self._history_pos == -1:
            self._edit_text_cache = self.edit_text
        if self._history_pos+1 < len(self._history):
            self._history_pos += 1
            self.edit_text = self._history[self._history_pos]

    def _set_history_next(self):
        # The most recent history entry is at index 0; -1 is the current line
        # that is not yet in history.
        if self._history_pos > -1:
            self._history_pos -= 1
        if self._history_pos == -1:
            self.edit_text = self._edit_text_cache  # Restore current line
        else:
            self.edit_text = self._history[self._history_pos]

    def _read_history(self):
        if self._history_file:
            self._history = _read_lines(self._history_file)

    def _append_to_history(self, line):
        # Don't add the same line twice in a row
        if self._history and self._history[0] == line:
            return
        self._history.insert(0, line)
        if self._history_file is not None:
            _append_line(self._history_file, line)

    @property
    def history_file(self):
        return self._history_file

    @history_file.setter
    def history_file(self, path):
        if path is None:
            self._history_file = None
        else:
            if _mkdir(os.path.dirname(path)) and _testwrite(path):
                self._history_file = os.path.abspath(os.path.expanduser(path))
                self._read_history()


def _read_lines(filepath):
    if  os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return [line.strip() for line in reversed(f.readlines())]
        except OSError as e:
            log.error("Can't read history file {}: {}"
                      .format(filepath, e.strerror))
    return []

def _mkdir(path):
    try:
        if path and not os.path.exists(path):
            os.makedirs(path)
    except OSError as e:
        log.error("Can't create directory {}: {}".format(path, e.strerror))
    else:
        return True

def _testwrite(path):
    try:
        open(path, 'a')
    except OSError as e:
        log.error("Can't append to history file {}: {}".format(path, e.strerror))
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
