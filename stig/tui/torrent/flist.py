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

from ...logging import make_logger
log = make_logger(__name__)

import urwid

from .. import main as tui

from ..table import Table
from .flist_columns import TUICOLUMNS

COLUMNS_FOCUS_MAP = {}
for col in TUICOLUMNS.values():
    COLUMNS_FOCUS_MAP.update(col.style.focus_map)


class FileWidget(urwid.WidgetWrap):
    def __init__(self, tfile, cells):
        self._tfile = tfile
        self._cells = cells
        super().__init__(urwid.AttrMap(cells, 'filelist', 'filelist.focused'))
        self.update(tfile)

    def update(self, tfile):
        for widget in self._cells.original_widget.widgets:
            widget.update(tfile)
        self._tfile = tfile


class FileListWidget(urwid.WidgetWrap):
    def __init__(self, srvapi, tfilters, ffilters, columns):
        self._srvapi = srvapi
        self._tfilters = tfilters
        self._ffilters = ffilters

        self._table = Table(**TUICOLUMNS)
        self._table.columns = columns

        self._torrents = ()
        self._walker = urwid.SimpleFocusListWalker([])
        self._listbox = urwid.ListBox(self._walker)

        pile = urwid.Pile([
            ('pack', urwid.AttrMap(self._table.headers, 'filelist.header')),
            self._listbox
        ])
        super().__init__(urwid.AttrMap(pile, 'filelist'))

        self._create_poller()

    def _create_poller(self):
        self._poller = self._srvapi.create_poller(
            self._srvapi.torrent.torrents, self._tfilters, keys=('files', 'name'))
        self._poller.on_response(self._handle_response)

    def _handle_response(self, response):
        if response is None or not response.torrents:
            self.clear()
        else:
            self._torrents = response.torrents
        self._invalidate()

    def render(self, size, focus=False):
        if self._torrents is not None:
            if len(self._walker) > 0:
                self._update_listitems()
            else:
                self._init_listitems()
            self._torrents = None
        return super().render(size, focus)

    def _init_listitems(self):
        keymap = tui.keymap

        self._table.clear()
        table = self._table

        self._walker[:] = ()
        walker = self._walker
        fws = self._filewidgets = {}

        for t in sorted(self._torrents, key=lambda t: t['name'].lower()):
            for f in self._maybe_filter(t['files']):
                fid = (t['id'], f['id'])
                fwcls = keymap.wrap(FileWidget, context='file')
                table.register(fid)
                row = urwid.AttrMap(table.get_row(fid),
                                    attr_map=None, focus_map=COLUMNS_FOCUS_MAP)
                fws[fid] = fwcls(f, row)
                walker.append(fws[fid])

    def _update_listitems(self):
        fws = self._filewidgets
        for t in self._torrents:
            for f in self._maybe_filter(t['files']):
                fid = (t['id'], f['id'])
                fws[fid].update(f)

    def _maybe_filter(self, files):
        return files if self._ffilters is None else \
            self._ffilters.apply(files)

    def clear(self):
        """Remove all list items"""
        self._filewidgets = {}
        self._table.clear()
        self._walker[:] = []

    @property
    def focused_torrent_id(self):
        """Torrent ID of the focused file's torrent"""
        focused_fw = self._listbox.focus
        if focused_fw is not None:
            for (tid,fid),fw in self._filewidgets.items():
                if focused_fw is fw:
                    return tid

    @property
    def focused_file_id(self):
        """File ID/index of the focused file"""
        focused_fw = self._listbox.focus
        if focused_fw is not None:
            for (tid,fid),fw in self._filewidgets.items():
                if focused_fw is fw:
                    return fid
