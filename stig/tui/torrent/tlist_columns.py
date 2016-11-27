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

import urwid

from ..table import ColumnHeaderWidget
from . import (Style, CellWidgetBase)
from ...columns.tlist import COLUMNS as _COLUMNS


TUICOLUMNS = {}

import os
PATHSEP = os.sep
class Path(_COLUMNS['path'], CellWidgetBase):
    width = 20
    style = Style(prefix='torrentlist.tpath', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['path'].header),
                           style.attrs('header'))

TUICOLUMNS['path'] = Path


class PeersConnected(_COLUMNS['peers-connected'], CellWidgetBase):
    style = Style(prefix='torrentlist.peers-connected', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['peers-connected'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value > 0 else ''

TUICOLUMNS['peers-connected'] = PeersConnected


class PeersSeeding(_COLUMNS['peers-seeding'], CellWidgetBase):
    style = Style(prefix='torrentlist.peers-seeding', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['peers-seeding'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value < 5 else ''

TUICOLUMNS['peers-seeding'] = PeersSeeding


class Progress(_COLUMNS['progress'], CellWidgetBase):
    style = Style(prefix='torrentlist.progress', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['progress'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value < 100 else ''

TUICOLUMNS['progress'] = Progress


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


class EtaComplete(_COLUMNS['eta'], CellWidgetBase):
    style = Style(prefix='torrentlist.eta', focusable=True,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['eta'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value > 0 else ''

TUICOLUMNS['eta'] = EtaComplete


class TorrentName(_COLUMNS['name'], CellWidgetBase):
    width = ('weight', 100)
    style = Style(prefix='torrentlist.name', focusable=True, extras=('header',),
                  modes=('idle.progress1', 'idle.progress2', 'idle.complete',
                         'stopped.progress1', 'stopped.progress2', 'stopped.complete',
                         'isolated.progress1', 'isolated.progress2', 'isolated.complete',
                         'initializing.progress1', 'initializing.progress2', 'initializing.complete',
                         'verifying.progress1', 'verifying.progress2', 'verifying.complete',
                         'downloading.progress1', 'downloading.progress2', 'downloading.complete',
                         'uploading.progress1', 'uploading.progress2', 'uploading.complete',
                         'queued.progress1', 'queued.progress2', 'queued.complete',
                         'connected.progress1', 'connected.progress2', 'connected.complete'))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['name'].header),
                           style.attrs('header'))
    needed_keys = ('name', 'status', '%downloaded', '%verified', '%metadata',
                   'isolated', 'rate-up', 'rate-down', 'peers-connected')

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
        if t['status'] == 'stopped':
            mode = 'stopped'
        elif t['isolated']:
            mode = 'isolated'
        elif t['%metadata'] < 1:
            mode = 'initializing'
            progress = t['%metadata']
        elif 'verify' in t['status']:
            mode = 'verifying'
            progress = t['%verified']
        elif t['rate-down'] > 0 and t['status'] == 'leeching':
            mode = 'downloading'
        elif t['status'] == 'leeching pending':
            mode = 'queued'
        elif t['rate-up'] > 0:
            mode = 'uploading'
        elif t['peers-connected'] > 0:
            mode = 'connected'
        else:
            mode = 'idle'
        return (t['name'], mode, progress)

TUICOLUMNS['name'] = TorrentName
