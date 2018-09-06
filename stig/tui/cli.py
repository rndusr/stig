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


class CLIEditWidget(urwid.Edit):
    """Edit widget with readline keybindings callbacks and a history"""

    def __init__(self, *args, on_change=None, on_accept=None, on_cancel=None,
                 history_file=None, history_size=1000, **kwargs):
        kwargs['align'] = kwargs['align'] if 'align' in kwargs else 'left'
        kwargs['wrap'] = kwargs['wrap'] if 'wrap' in kwargs else 'clip'
        self._on_change = on_change
        self._on_accept = on_accept
        self._on_cancel = on_cancel
        self._edit_text_cache = ''
        self._history = []
        self._history_size = history_size
        self._history_pos = -1
        self.history_file = history_file
        return super().__init__(*args, **kwargs)

    def keypress(self, size, key):
        text_before = self.get_edit_text()
        cmd = self._command_map[key]
        if cmd is urwid.CURSOR_UP:
            self._set_history_prev()
            key = None
        elif cmd is urwid.CURSOR_DOWN:
            self._set_history_next()
            key = None
        elif cmd is urwid.ACTIVATE:
            self.append_to_history()
            if self._on_accept is not None:
                self._on_accept(self)
            self._history_pos = -1
            key = None
        elif cmd is urwid.CANCEL:
            if self._on_cancel is not None:
                self._on_cancel(self)
            self._history_pos = -1
            key = None
        elif key == 'space':
            return super().keypress(size, ' ')
        else:
            key = super().keypress(size, key)

        text_after = self.get_edit_text()
        if self._on_change is not None and text_before != text_after:
            self._on_change(self)
        return key

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
            self._history = list(reversed(_read_lines(self._history_file)))

    def append_to_history(self):
        """Add current `edit_text` to history"""
        # Don't add the same line twice in a row
        new_line = self.edit_text
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
