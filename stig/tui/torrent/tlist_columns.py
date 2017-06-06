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

"""Column classes that display information in torrent lists

Adding a new cell type adds a new optional column to torrent lists.  To do
this, write a new class that derives from CellWidgetBase and register it in
the COLUMNS dictionary to make it available.
"""

from ...logging import make_logger
log = make_logger(__name__)

import urwid

from ..table import ColumnHeaderWidget
from . import (Style, CellWidgetBase)
from ...views.tlist import COLUMNS as _COLUMNS
from ...client import tkeys


TUICOLUMNS = {}


from .common_columns import MarkedBase
class Marked(MarkedBase):
    style = Style(prefix='torrentlist.marked', focusable=True, extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(), style.attrs('header'))

TUICOLUMNS['marked'] = Marked


class Path(_COLUMNS['path'], CellWidgetBase):
    width = 20
    style = Style(prefix='torrentlist.path', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['path'].header),
                           style.attrs('header'))

TUICOLUMNS['path'] = Path


class Connections(_COLUMNS['connections'], CellWidgetBase):
    style = Style(prefix='torrentlist.connections', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['connections'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value > 0 else ''

TUICOLUMNS['connections'] = Connections


class Seeds(_COLUMNS['seeds'], CellWidgetBase):
    style = Style(prefix='torrentlist.seeds', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['seeds'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value < 5 else ''

TUICOLUMNS['seeds'] = Seeds


class Progress(_COLUMNS['progress'], CellWidgetBase):
    style = Style(prefix='torrentlist.progress', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['progress'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value < 100 else ''

TUICOLUMNS['progress'] = Progress


class PercentAvailable(_COLUMNS['%available'], CellWidgetBase):
    style = Style(prefix='torrentlist.%available', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['%available'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value < 100 else ''

TUICOLUMNS['%available'] = PercentAvailable


class Ratio(_COLUMNS['ratio'], CellWidgetBase):
    style = Style(prefix='torrentlist.ratio', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['ratio'].header),
                           style.attrs('header'))

    def get_mode(self):
        if 0 <= self.value < 1:
            return 'highlighted'

TUICOLUMNS['ratio'] = Ratio


class Size(_COLUMNS['size'], CellWidgetBase):
    style = Style(prefix='torrentlist.size', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['size'].header),
                           style.attrs('header'))

    @classmethod
    def set_unit(cls, unit):
        cls.header.original_widget.right = _COLUMNS['size'].header['right']

TUICOLUMNS['size'] = Size


class Downloaded(_COLUMNS['downloaded'], CellWidgetBase):
    style = Style(prefix='torrentlist.downloaded', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['downloaded'].header),
                           style.attrs('header'))

    def get_mode(self):
        t = self.data
        if t['%downloaded'] < 100 and 0 < t['size-downloaded'] < t['size-final']:
            return 'highlighted'

    @classmethod
    def set_unit(cls, unit):
        cls.header.original_widget.right = _COLUMNS['downloaded'].header['right']

TUICOLUMNS['downloaded'] = Downloaded


class Uploaded(_COLUMNS['uploaded'], CellWidgetBase):
    style = Style(prefix='torrentlist.uploaded', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['uploaded'].header),
                           style.attrs('header'))

    def get_mode(self):
        if self.data['size-uploaded'] < self.data['size-downloaded']:
            return 'highlighted'

    @classmethod
    def set_unit(cls, unit):
        cls.header.original_widget.right = _COLUMNS['uploaded'].header['right']

TUICOLUMNS['uploaded'] = Uploaded


class BytesAvailable(_COLUMNS['available'], CellWidgetBase):
    style = Style(prefix='torrentlist.available', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['available'].header),
                           style.attrs('header'))

    def get_mode(self):
        if self.value < self.data['size-final']:
            return 'highlighted'

    @classmethod
    def set_unit(cls, unit):
        cls.header.original_widget.right = _COLUMNS['available'].header['right']

TUICOLUMNS['available'] = BytesAvailable


class RateDown(_COLUMNS['rate-down'], CellWidgetBase):
    style = Style(prefix='torrentlist.rate-down', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['rate-down'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value > 0 else ''

    @classmethod
    def set_unit(cls, unit):
        cls.header.original_widget.right = _COLUMNS['rate-down'].header['right']

TUICOLUMNS['rate-down'] = RateDown


class RateUp(_COLUMNS['rate-up'], CellWidgetBase):
    style = Style(prefix='torrentlist.rate-up', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['rate-up'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value > 0 else ''

    @classmethod
    def set_unit(cls, unit):
        cls.header.original_widget.right = _COLUMNS['rate-up'].header['right']

TUICOLUMNS['rate-up'] = RateUp



class RateLimitDown(_COLUMNS['rate-limit-down'], CellWidgetBase):
    style = Style(prefix='torrentlist.rate-limit-down', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['rate-limit-down'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value < float('inf') else ''

    @classmethod
    def set_unit(cls, unit):
        cls.header.original_widget.right = _COLUMNS['rate-limit-down'].header['right']

TUICOLUMNS['rate-limit-down'] = RateLimitDown


class RateLimitUp(_COLUMNS['rate-limit-up'], CellWidgetBase):
    style = Style(prefix='torrentlist.rate-limit-up', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['rate-limit-up'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value < float('inf') else ''

    @classmethod
    def set_unit(cls, unit):
        cls.header.original_widget.right = _COLUMNS['rate-limit-up'].header['right']

TUICOLUMNS['rate-limit-up'] = RateLimitUp


class EtaComplete(_COLUMNS['eta'], CellWidgetBase):
    style = Style(prefix='torrentlist.eta', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['eta'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if bool(self.value) else ''

TUICOLUMNS['eta'] = EtaComplete


class TimeCreated(_COLUMNS['created'], CellWidgetBase):
    style = Style(prefix='torrentlist.created', focusable=True, extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['created'].header),
                           style.attrs('header'))

TUICOLUMNS['created'] = TimeCreated

class TimeAdded(_COLUMNS['added'], CellWidgetBase):
    style = Style(prefix='torrentlist.added', focusable=True, extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['added'].header),
                           style.attrs('header'))

TUICOLUMNS['added'] = TimeAdded

class TimeStarted(_COLUMNS['started'], CellWidgetBase):
    style = Style(prefix='torrentlist.started', focusable=True, extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['started'].header),
                           style.attrs('header'))

TUICOLUMNS['started'] = TimeStarted

class TimeActive(_COLUMNS['activity'], CellWidgetBase):
    style = Style(prefix='torrentlist.activity', focusable=True, extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['activity'].header),
                           style.attrs('header'))

TUICOLUMNS['activity'] = TimeActive

class TimeCompleted(_COLUMNS['completed'], CellWidgetBase):
    style = Style(prefix='torrentlist.completed', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['completed'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value.in_future else ''

TUICOLUMNS['completed'] = TimeCompleted


class Tracker(_COLUMNS['tracker'], CellWidgetBase):
    style = Style(prefix='torrentlist.tracker', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['tracker'].header),
                           style.attrs('header'))

TUICOLUMNS['tracker'] = Tracker


class Error(_COLUMNS['error'], CellWidgetBase):
    style = Style(prefix='torrentlist.error', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['error'].header),
                           style.attrs('header'))

TUICOLUMNS['error'] = Error


class Status(_COLUMNS['status'], CellWidgetBase):
    style = Style(prefix='torrentlist.status', focusable=True,
                  extras=('header',),
                  modes=('idle', 'downloading', 'uploading', 'connected', 'seeding',
                         'stopped', 'queued', 'isolated', 'verifying', 'discovering'))

    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['status'].header),
                           style.attrs('header'))

    MODE_MAP = {
        tkeys.Status.IDLE      : 'idle',
        tkeys.Status.DOWNLOAD  : 'downloading',
        tkeys.Status.UPLOAD    : 'uploading',
        tkeys.Status.CONNECTED : 'connected',
        tkeys.Status.SEED      : 'seeding',
        tkeys.Status.STOPPED   : 'stopped',
        tkeys.Status.QUEUED    : 'queued',
        tkeys.Status.ISOLATED  : 'isolated',
        tkeys.Status.VERIFY    : 'verifying',
        tkeys.Status.INIT      : 'discovering',
    }
    def get_mode(self):
        return self.MODE_MAP[self.value]

TUICOLUMNS['status'] = Status


class TorrentName(_COLUMNS['name'], CellWidgetBase):
    width = ('weight', 100)
    style = Style(prefix='torrentlist.name', focusable=True, extras=('header',),
                  modes=('idle.progress1', 'idle.progress2', 'idle.complete',
                         'stopped.progress1', 'stopped.progress2', 'stopped.complete',
                         'isolated.progress1', 'isolated.progress2', 'isolated.complete',
                         'discovering.progress1', 'discovering.progress2', 'discovering.complete',
                         'verifying.progress1', 'verifying.progress2', 'verifying.complete',
                         'downloading.progress1', 'downloading.progress2', 'downloading.complete',
                         'uploading.progress1', 'uploading.progress2', 'uploading.complete',
                         'queued.progress1', 'queued.progress2', 'queued.complete',
                         'connected.progress1', 'connected.progress2', 'connected.complete'))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['name'].header),
                           style.attrs('header'))
    needed_keys = ('name', 'status', '%downloaded', '%verified', '%metadata',
                   'rate-up', 'rate-down', 'peers-connected')

    def __init__(self, *args, **kwargs):
        self.status = ('', 'idle', 0)
        super().__init__(*args, **kwargs)

    def update(self, torrent):
        new_status = self.make_status(torrent)
        if new_status != self.status:
            self.status = new_status
            self._invalidate()

    def render(self, size, focus=False):
        (maxcol,) = size
        name, mode, progress = self.status
        name = name[:maxcol].ljust(maxcol, ' ')  # Expand/Shrink name to full width
        if progress == 100:
            attrs = self.style.attrs(mode+'.complete', focused=focus)
            self.text.set_text((attrs, name))
        else:
            completed_col = int(maxcol * progress / 100)  # Width of first part of progress bar
            name1 = name[:completed_col]
            name2 = name[completed_col:]
            attrs1 = self.style.attrs(mode+'.progress1', focused=focus)
            attrs2 = self.style.attrs(mode+'.progress2', focused=focus)
            self.text.set_text([(attrs1, name1),
                                (attrs2, name2)])
        return super().render(size, focus)

    def get_mode(self):
        return self.status[1]

    @staticmethod
    def make_status(t):
        progress = t['%downloaded']
        Status = type(t['status'])
        if Status.STOPPED in t['status']:
            mode = 'stopped'
        elif Status.ISOLATED in t['status']:
            mode = 'isolated'
        elif Status.INIT in t['status']:
            mode = 'discovering'
            progress = t['%metadata']
        elif Status.VERIFY in t['status']:
            mode = 'verifying'
            progress = t['%verified']
        elif Status.DOWNLOAD in t['status']:
            mode = 'downloading'
        elif Status.UPLOAD in t['status']:
            mode = 'uploading'
        elif Status.QUEUED in t['status']:
            mode = 'queued'
        elif Status.CONNECTED in t['status']:
            mode = 'connected'
        else:
            mode = 'idle'
        return (t['name'], mode, progress)



TUICOLUMNS['name'] = TorrentName
