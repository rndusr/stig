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

import logging
import urwid
import time
import asyncio


class UILogRecordHandler(logging.Handler):
    """Feed LogRecords to a LogWidget"""

    def __init__(self, logwidget):
        super().__init__()
        self._logwidget = logwidget

    def emit(self, record):
        self._logwidget.add(record)


class LogWidget(urwid.WidgetWrap):
    """Present LogRecords from logging module in a ListBox Widget"""

    def __init__(self, maxrows=10, autohide_delay=0, loop=None):
        self.maxrows = maxrows
        self.autohide_delay = autohide_delay
        self._autohide_handle = None
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._listbox = urwid.ListBox(urwid.SimpleListWalker([]))
        super().__init__(urwid.AttrMap(self._listbox, 'log'))

        self._root_logger = logging.getLogger()
        self._orig_handlers = []
        self._handler = UILogRecordHandler(self)

        # Copy formatter first handler (there should be only one formatter anyway)
        handlers = self._root_logger.handlers
        self._handler.setFormatter(handlers[0].formatter)

        # Don't log debugging messages if we're already logging to a file
        for h in handlers:
            if isinstance(h, logging.FileHandler):
                self._handler.setLevel(logging.INFO)

    def enable(self):
        # Store any stdout/stderr handlers
        for h in tuple(self._root_logger.handlers):
            if h.stream.name in ('<stderr>', '<stdout>'):
                self._orig_handlers.append(h)
                self._root_logger.removeHandler(h)
        self._root_logger.addHandler(self._handler)
        log.debug('Started logging to UI')

    def disable(self):
        # Restore any previously stored handlers
        for h in tuple(self._orig_handlers):
            self._root_logger.addHandler(h)
            self._orig_handlers.remove(h)

        try:
            self._root_logger.handlers.remove(self._handler)
        except ValueError:
            pass
        else:
            log.debug('Stopped logging to UI')

        if self._autohide_handle is not None:
            self._autohide_handle.cancel()

    def add(self, record):
        msg = ''
        if record.levelno >= logging.WARNING:
            style = 'error'
        elif record.levelno > logging.DEBUG:
            style = 'info'
        else:
            style = 'debug'
            msg = '[{}] '.format(record.name)
        msg += record.getMessage()

        # Indicate identical messages instead of spamming the log
        if len(self._listbox.body) > 0 and self._listbox.body[-1].text == msg:
            self._listbox.body[-1].dupes += 1
        else:
            self._listbox.body.append(LogEntry(msg, style))
            self._listbox.focus_position = len(self._listbox.body)-1  # Scroll to end of log
        self._invalidate_rows()
        self._maybe_show_temporarily()

    # TODO: The autohide functionality shouldn't be in this widget.
    def _maybe_show_temporarily(self):
        """Show log widget if hidden and hide it again after delay"""
        from .main import widgets
        if self.autohide_delay > 0 and \
           (not widgets.visible('log') or self._autohide_handle is not None):
            if self._autohide_handle is not None:
                self._autohide_handle.cancel()
            widgets.show('log')
            def hide():
                widgets.hide('log')
                self._autohide_handle = None
            self._autohide_handle = self._loop.call_later(self.autohide_delay, hide)

    def rows(self, size, focus=False):
        if hasattr(self, '_rows'):
            return self._rows
        else:
            (maxcols, maxrows) = (size[0], self.maxrows)
            walker = self._listbox.body
            rows = 0

            if len(walker) >= maxrows:
                rows = maxrows
            else:
                for widget in walker:
                    rows += widget.rows(size=(maxcols,))
                    if rows >= maxrows:
                        break
            self._rows = min(rows, maxrows)
            return self._rows

    def render(self, size, focus=False):
        size = (size[0], self.rows(size, focus))
        return super().render(size, focus)

    def _invalidate_rows(self):
        try:
            delattr(self, '_rows')
        except AttributeError:
            pass

    def clear(self):
        self._listbox.body[:] = []
        self._invalidate_rows()

    @property
    def entries(self):
        yield from self._listbox.body

    def selectable(self):
        return False


class LogEntry(urwid.WidgetWrap):
    @staticmethod
    def _make_timestamp():
        return time.strftime('%H:%M:%S')

    def __init__(self, message, style):
        self._dupes = 0
        self._widgets = {
            'timestamp':    urwid.Text(self._make_timestamp()),
            'dupes':        urwid.Text(''),
            'dupes_spacer': urwid.Text(''),
            'message':      urwid.Text(str(message)),
        }
        super().__init__(urwid.Columns([
            ('pack', urwid.AttrMap(self._widgets['timestamp'],    'log.timestamp')),
            ('pack', urwid.AttrMap(urwid.Text(' '),               'log')),
            ('pack', urwid.AttrMap(self._widgets['dupes'],        'log.dupecount')),
            ('pack', urwid.AttrMap(self._widgets['dupes_spacer'], 'log')),
            ('pack', urwid.AttrMap(self._widgets['message'],      'log.'+style)),
        ], dividechars=0))

    @property
    def text(self):
        return self._widgets['message'].text

    @property
    def dupes(self):
        return self._dupes

    @dupes.setter
    def dupes(self, dupes):
        self._dupes = dupes
        self._widgets['timestamp'].set_text(self._make_timestamp())
        if dupes > 0:
            self._widgets['dupes'].set_text('x' + str(dupes+1))
            self._widgets['dupes_spacer'].set_text(' ')
        else:
            self._widgets['dupes'].set_text('')
            self._widgets['dupes_spacer'].set_text('')

    def __repr__(self):
        return '<{} {!r}>'.format(type(self).__name__, self._widgets['message'].text)
