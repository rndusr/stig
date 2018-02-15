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

from .scroll import (Scrollable, ScrollBar)


class UILogRecordHandler(logging.Handler):
    """Feed LogRecords to a LogWidget"""

    def __init__(self, logwidget):
        super().__init__()
        self._logwidget = logwidget

    def emit(self, record):
        self._logwidget.add(record)


class LogWidget(urwid.WidgetWrap):
    """Present LogRecords from logging module in a ListBox Widget"""

    def __init__(self, height=10, autohide_delay=0, loop=None):
        self._height = height
        self._autohide_delay = autohide_delay
        self._autohide_handle = None
        self._loop = loop if loop is not None else asyncio.get_event_loop()
        self._pile = urwid.Pile([])
        self._pile_options = self._pile.options('pack', None)
        self._scrollable = Scrollable(self._pile)
        pile_sb = urwid.AttrMap(
            ScrollBar(urwid.AttrMap(self._scrollable, 'log')),
            'scrollbar'
        )
        super().__init__(pile_sb)

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
        entries = tuple(widget for widget,options in self._pile.contents)
        if len(entries) > 0 and entries[-1].text == msg:
            entries[-1].dupes += 1
        else:
            # Keep scrolling down if we are currently at the bottom; otherwise
            # the user has scrolled up manually.
            curpos = self._scrollable.get_scrollpos()
            maxpos = self._scrollable.rows_max()
            scroll_to_bottom = curpos+self._height >= maxpos
            new_content = (LogEntry(msg, style), self._pile_options)
            self._pile.contents.append(new_content)
            if scroll_to_bottom:
                self.scroll_to('bottom')
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
        if not hasattr(self, '_rows'):
            self._rows = min(self._pile.rows(size, focus),
                             self._height)
        return self._rows

    def _invalidate_rows(self):
        try:
            delattr(self, '_rows')
        except AttributeError:
            pass

    def render(self, size, focus=False):
        return super().render((size[0], self.rows(size, focus)), focus)

    def clear(self):
        self._pile.contents.clear()
        self._invalidate_rows()

    def scroll_relative(self, direction, lines):
        scrl = self._scrollable
        pos = scrl.get_scrollpos()
        if direction == 'up':
            pos = max(0, pos - lines)
        elif direction == 'down':
            pos += lines
        scrl.set_scrollpos(pos)

    _WHERE = {'top': 0, 'bottom': -1}
    def scroll_to(self, where):
        """Scroll to top or bottom of log

        where: "top" or "bottom"
        """
        try:
            self._scrollable.set_scrollpos(self._WHERE[where])
        except KeyError:
            raise ValueError('where argument must be "top" or "bottom", not %r' % where)

    @property
    def entries(self):
        for widget,options in self._pile.contents:
            yield widget

    @property
    def autohide_delay(self):
        return self._autohide_delay

    @autohide_delay.setter
    def autohide_delay(self, seconds):
        self._autohide_delay = seconds

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, rows):
        self._height = int(rows)
        self._invalidate_rows()
        self._invalidate()

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
            urwid.AttrMap(self._widgets['message'], 'log.'+style),
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
