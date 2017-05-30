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
from collections import abc

from .. import main as tui

from ..scroll import ScrollBar
from ..table import Table
from .tlist_columns import TUICOLUMNS

COLUMNS_FOCUS_MAP = {}
for col in TUICOLUMNS.values():
    COLUMNS_FOCUS_MAP.update(col.style.focus_map)


class TorrentListItemWidget(urwid.WidgetWrap):
    def __init__(self, torrent, cells):
        self._torrent = torrent
        self._tid = torrent['id']
        self._cells = cells
        self.update(torrent)
        row = urwid.AttrMap(urwid.AttrMap(cells, attr_map=None, focus_map=COLUMNS_FOCUS_MAP),
                            'torrentlist', 'torrentlist.focused')
        super().__init__(row)

    def update(self, torrent):
        for widget in self._cells.widgets:
            widget.update(torrent)
        self._torrent = torrent

    @property
    def torrent_id(self):
        return self._tid

    @property
    def torrent(self):
        return self._torrent

    @property
    def is_marked(self):
        return self._cells.marked.is_marked

    @is_marked.setter
    def is_marked(self, is_marked):
        self._cells.marked.is_marked = bool(is_marked)


class TorrentListWidget(urwid.WidgetWrap):
    def __init__(self, sort=None, tfilter=None, columns=[], title=None):
        self._sort = sort
        self._sort_orig = sort
        self._tfilter = tfilter
        self._columns = columns
        self._title_base = title
        self.title_updater = None

        self._table = Table(**TUICOLUMNS)
        self._table.columns = columns

        self._torrents = ()
        self._walker = urwid.SimpleFocusListWalker([])
        self._listbox = tui.keymap.wrap(urwid.ListBox, context='torrentlist')(self._walker)
        self._marked = set()

        listbox_sb = urwid.AttrMap(
            ScrollBar(urwid.AttrMap(self._listbox, 'torrentlist')),
            'scrollbar'
        )
        pile = urwid.Pile([
            ('pack', urwid.AttrMap(self._table.headers, 'torrentlist.header')),
            listbox_sb
        ])
        super().__init__(pile)

        self._register_request()

    def _register_request(self):
        # Get keys needed for sort order, tfilter and columns
        keys = []
        if self._sort is not None:
            keys.extend(self._sort.needed_keys)
        if hasattr(self._tfilter, 'needed_keys'):
            keys.extend(self._tfilter.needed_keys)
        for colname in self._columns:
            keys.extend(TUICOLUMNS[colname].needed_keys)

        # Register new request in request pool
        log.debug('Registering keys for %s: %s', self.id, keys)
        tui.srvapi.treqpool.register(self.id, self._handle_tlist,
                                     keys=keys,
                                     tfilter=self._tfilter)
        tui.srvapi.treqpool.poll()

    def _handle_tlist(self, torrents):
        self._torrents = tuple(torrents)
        if self.title_updater is not None:
            # First argument can be cropped if too long, second argument is fixed
            self.title_updater(self.title, ' [%d]' % self.count)
        self._invalidate()

    def render(self, size, focus=False):
        if self._torrents is not None:
            self._update_listitems()
            self._torrents = None
        return super().render(size, focus)

    def _update_listitems(self):
        # Remember focused torrent
        focused_tw = self.focused_torrent_widget

        walker = self._walker
        tdict = {t['id']:t for t in self._torrents}
        dead_tws = []
        for tw in walker:  # tw = TorrentListItemWidget
            tid = tw.torrent_id
            try:
                # Update existing torrent widget with new data
                tw.update(tdict[tid])
                del tdict[tid]
            except KeyError:
                # Torrent has been removed
                dead_tws.append(tw)

        # Remove list items that don't exist in self._torrents anymore
        marked = self._marked
        for tw in dead_tws:
            walker.remove(tw)
            marked.discard(tw)  # List items are also stored in self._marked

        # Any torrents that haven't been used to update an existing torrent are new
        if tdict:
            widgetcls = tui.keymap.wrap(TorrentListItemWidget, context='torrent')
            for tid in tdict:
                self._table.register(tid)
                row = self._table.get_row(tid)
                walker.append(widgetcls(tdict[tid], row))

        # Sort torrents
        if self._sort is not None:
            self._sort.apply(walker,
                            item_getter=lambda tw: tw.torrent,
                            inplace=True)

        # If necessary, re-focus previously focused torrent
        if focused_tw is not None and self.focused_torrent_widget is not None and \
           focused_tw.torrent_id != self.focused_torrent_widget.torrent_id:
            focused_tid = focused_tw.torrent_id
            for i,tw in enumerate(walker):
                if tw.torrent_id == focused_tid:
                    self._listbox.focus_position = i
                    break

    def clear(self):
        """Remove all list items"""
        for tw in tuple(self._walker):
            tw.torrent.clearcache()
            self._walker.remove(tw)
        tui.srvapi.treqpool.poll()

    def update(self):
        """Call `clear` and then poll immediately"""
        self.clear()
        tui.srvapi.treqpool.poll()

    @property
    def sort(self):
        return self._sort

    @sort.setter
    def sort(self, sort):
        tui.srvapi.treqpool.remove(self.id)
        if sort == 'RESET':
            self._sort = self._sort_orig
        else:
            self._sort = sort
        self._register_request()

    @property
    def title(self):
        if self._title_base is None:
            if self._tfilter is None:
                title = ['<all>']
            elif isinstance(self._tfilter, abc.Sequence):
                title = ['<handpicked>']
            else:
                title = [str(self._tfilter)]
        else:
            title = [self._title_base]

        if self._sort is not None:
            sortstr = str(self._sort)
            if sortstr is not self._sort.DEFAULT_SORT:
                title.append('{%s}' % sortstr)

        return ' '.join(title)

    @property
    def count(self):
        """Number of listed torrents"""
        # If this method was called before rendering, the contents of the
        # listbox widget are inaccurate and we have to use self._torrents.
        # But if we're called after rendering, self._torrents is reset to
        # None.
        if self._torrents is not None:
            return len(self._torrents)
        else:
            return len(self._listbox.body)

    @property
    def id(self):
        return 'tlist%s:%s' % (id(self), self.title)

    @property
    def focused_torrent_widget(self):
        return self._listbox.focus

    @property
    def focused_torrent_id(self):
        return self._listbox.focus.torrent['id']

    @property
    def focus_position(self):
        return self._listbox.focus_position

    @focus_position.setter
    def focus_position(self, focus_position):
        self._listbox.focus_position = min(focus_position, len(self._listbox.body)-1)

    def mark(self, toggle=False, all=False):
        """Mark the currently focused item or all items"""
        self._set_mark(True, toggle=toggle, all=all)

    def unmark(self, toggle=False, all=False):
        """Unmark the currently focused item or all items"""
        self._set_mark(False, toggle=toggle, all=all)

    @property
    def marked(self):
        """Generator that yields TorrentListItemWidgets"""
        yield from self._marked

    def _set_mark(self, mark, toggle=False, all=False):
        if toggle and self.focused_torrent_widget is not None:
            mark = not self.focused_torrent_widget.is_marked

        for widget in self._select_items_for_marking(all):
            widget.is_marked = mark
            if mark:
                self._marked.add(widget)
            else:
                self._marked.discard(widget)

    def _select_items_for_marking(self, all):
        if self.focused_torrent_widget is not None:
            if all:
                yield from self._listbox.body
            else:
                yield self.focused_torrent_widget

    def refresh_marks(self):
        """Redraw the "marked" column in all rows"""
        for widget in self._listbox.body:
            widget.is_marked = widget.is_marked
