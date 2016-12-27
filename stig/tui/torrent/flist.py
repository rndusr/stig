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
import urwidtrees

from .. import main as tui
from ..table import Table
from .flist_columns import TUICOLUMNS

COLUMNS_FOCUS_MAP = {}
for col in TUICOLUMNS.values():
    COLUMNS_FOCUS_MAP.update(col.style.focus_map)


from collections import Mapping
class TorrentFileDirectory(dict):
    def __hash__(self):
        return hash(self['id'])

    def __repr__(self):
        return '<{} {!r}>'.format(type(self).__name__, self['id'])


class FileWidget(urwid.WidgetWrap):
    def __init__(self, tfile, row):
        self._widgets = row.widgets
        super().__init__(urwid.AttrMap(row, 'filelist', 'filelist.focused'))
        self.update(tfile)

    def update(self, tfile):
        for widget in self._widgets:
            widget.update(tfile)
        self._tfile = tfile


from urwidtrees.decoration import ArrowTree
class FileTreeDecorator(ArrowTree):
    """urwidtrees decorator for TorrentFiles and TorrentFileTrees"""

    def __init__(self, torrents, keymap, table, ffilter):
        self._filewidgetcls = keymap.wrap(FileWidget, context='file')
        self._table = table
        self._ffilter = ffilter
        self._widgets = {}
        forest = self._create_file_forest(torrents)
        super().__init__(forest, indent=2)

    def _create_file_forest(self, torrents):
        # Create a list of nested trees in SimpleTree format.  But the leaves
        # are mappings instead of widgets.  Each mapping contains the
        # information that the `decorate` method needs to create a widget.

        def create_tree(nodename, content):
            if content.nodetype == 'leaf':
                # Torrent has a single file and no directories
                if self._ffilter is None or self._ffilter.match(content):
                    return (content, None)
                else:
                    return None

            elif content.nodetype == 'parent':
                # Torrent has at least one directory
                tree = []
                for k,v in sorted(content.items(), key=lambda pair: pair[0].lower()):
                    if v.nodetype == 'leaf':
                        if self._ffilter is None or self._ffilter.match(v):
                            tree.append((v, None))
                    elif v.nodetype == 'parent':
                        dirnode = self._create_directory_data(name=k, tree=v)
                        tree.append(create_tree(dirnode, v))
                return (nodename, tree or None)

        forest = []  # Multiple trees as siblings
        for t in sorted(torrents, key=lambda t: t['name'].lower()):
            filetree = t['files']
            rootnodename = next(iter(filetree.keys()))
            rootnode = self._create_directory_data(rootnodename, tree=filetree)
            tree = create_tree(rootnode, filetree[rootnodename])
            if tree is not None:
                forest.append(tree)
        return forest

    def _create_directory_data(self, name, tree):
        # Create a mapping that has the same keys as a TorrentFile instance.
        # Each value recursively summarizes the values of all the TorrentFiles
        # in `tree`.

        tfiles = tuple(tree.files)

        def sum_size(tree, key):
            sizes = tuple(tfile[key] for tfile in tfiles)
            # Preserve the original type (Number)
            first_size = sizes[0]
            start_value = type(first_size)(0, unit=first_size.unit, prefix=first_size.prefix)
            return sum(sizes, start_value)

        def sum_priority(tfiles):
            if len(set(tfile['priority'] for tfile in tfiles)) == 1:
                return tfiles[0]['priority']
            else:
                return ''

        data = {'name': str(name),
                'size-downloaded': sum_size(tfiles, 'size-downloaded'),
                'size-total': sum_size(tfiles, 'size-total'),
                'priority': sum_priority(tfiles),
                'is-wanted': True}
        progress_cls = type(tfiles[0]['progress'])
        data['progress'] = progress_cls(data['size-downloaded'] / data['size-total'] * 100)
        data['tid'] = tfiles[0]['tid']
        data['id'] = tree.path
        return TorrentFileDirectory(data)

    def decorate(self, pos, data, is_first=True):
        node_id = (data['tid'], data['id'])

        # We can use the tree position as table ID
        self._table.register(pos)
        row = self._table.get_row(pos)

        # We use parent's decorate() method to give the name column a tree
        # structure.  But we also need the original update() method so we can
        # apply new data to the widget.  This is dirty but it works.
        update_method = row.name.update
        decowidget = super().decorate(pos, row.name, is_first=is_first)
        decowidget.update = update_method
        row.replace('name', decowidget)

        # Wrap the whole row in a FileWidget with keymapping.  This also
        # applies all the other values besides the name (size, progress, etc).
        file_widget = self._filewidgetcls(data, row)
        self._widgets[node_id] = file_widget
        return urwid.AttrMap(file_widget, attr_map=None, focus_map=COLUMNS_FOCUS_MAP)

    def update(self, torrents):
        widgets = self._widgets
        for t in torrents:
            tid = t['id']

            # Update file nodes
            for f in t['files'].files:
                fid = f['id']
                widget_id = (tid, fid)
                if widget_id in widgets:
                    widgets[widget_id].update(f)

            # Update directory nodes
            for name,content in t['files'].folders:
                path = content.path
                widget_id = (tid, path)
                if widget_id in widgets:
                    data = self._create_directory_data(name, tree=content)
                    widgets[widget_id].update(data)



class FileListWidget(urwid.WidgetWrap):
    def __init__(self, srvapi, tfilter, ffilter, columns):
        self._srvapi = srvapi
        self._tfilter = tfilter
        self._ffilter = ffilter
        self._torrents = ()
        self._initialized = False

        self._table = Table(**TUICOLUMNS)
        self._table.columns = columns

        self._listbox = urwid.ListBox(urwid.SimpleListWalker([]))
        pile = urwid.Pile([
            ('pack', urwid.AttrMap(self._table.headers, 'filelist.header')),
            self._listbox
        ])
        super().__init__(urwid.AttrMap(pile, 'filelist'))

        self._create_poller()

    def _create_poller(self):
        self._poller = self._srvapi.create_poller(
            self._srvapi.torrent.torrents, self._tfilter, keys=('files', 'name'))
        self._poller.on_response(self._handle_response)

    def _handle_response(self, response):
        if response is None or not response.torrents:
            self.clear()
        else:
            self._torrents = response.torrents
        self._invalidate()

    def render(self, size, focus=False):
        if self._torrents is not None:
            if self._initialized:
                self._update_listitems()
            else:
                self._init_listitems()
            self._torrents = None
        return super().render(size, focus)

    def _init_listitems(self):
        self.clear()
        if self._torrents:
            self._filetree = FileTreeDecorator(self._torrents, tui.keymap,
                                               self._table, self._ffilter)
            self._listbox.body = urwidtrees.widgets.TreeListWalker(self._filetree)
            self._listbox._invalidate()
            self._initialized = True

    def _update_listitems(self):
        if self._torrents:
            self._filetree.update(self._torrents)

    def clear(self):
        """Remove all list items"""
        self._table.clear()
        self._listbox.body = urwid.SimpleListWalker([])
        self._listbox._invalidate()
        self._initialized = False

    def update(self):
        """Call `clear` and then poll immediately"""
        self.clear()
        self._poller.poll()

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
