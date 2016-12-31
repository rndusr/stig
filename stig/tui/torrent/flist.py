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
from collections import abc

from .. import main as tui
from ..table import Table
from .flist_columns import TUICOLUMNS
from ...columns.flist import (create_directory_data, create_directory_name)

COLUMNS_FOCUS_MAP = {}
for col in TUICOLUMNS.values():
    COLUMNS_FOCUS_MAP.update(col.style.focus_map)



class FileWidget(urwid.WidgetWrap):
    def __init__(self, tfile, row):
        self._widgets = row.widgets
        super().__init__(urwid.AttrMap(row, 'filelist', 'filelist.focused'))
        self.update(tfile)

    def update(self, tfile):
        for widget in self._widgets:
            widget.update(tfile)
        self._tfile = tfile

    @property
    def torrent_id(self):
        return self._tfile['tid']

    @property
    def file_id(self):
        return self._tfile['id']


from urwidtrees.decoration import ArrowTree
class FileTreeDecorator(ArrowTree):
    """urwidtrees decorator for TorrentFiles and TorrentFileTrees"""

    def __init__(self, torrents, keymap, table, ffilter):
        self._filewidgetcls = keymap.wrap(FileWidget, context='file')
        self._table = table
        self._ffilter = ffilter
        self._widgets = {}
        self._filtered_counts = {}
        forest = self._create_file_forest(torrents)
        super().__init__(forest, indent=2)

    def _file_is_filtered(self, tfile):
        if self._ffilter is None:
            return False  # No filter specified
        elif isinstance(self._ffilter, (abc.Sequence, abc.Set)):
            # ffilter is a collection of file IDs
            return not tfile['id'] in self._ffilter
        else:
            # ffilter is a TorrentFileFilter instance
            return not self._ffilter.match(tfile)

    def _create_file_forest(self, torrents):
        # Create a list of nested trees in SimpleTree format.  But the leaves
        # are mappings instead of widgets.  Each mapping contains the
        # information that the `decorate` method needs to create a widget.

        ffilter = self._ffilter
        def create_tree(node, content):
            if content.nodetype == 'leaf':
                # Torrent has a single file and no directories
                if not self._file_is_filtered(content):
                    return (content, None)
                else:
                    return None

            elif content.nodetype == 'parent':
                # Torrent has at least one directory
                tree = []
                filtered_count = 0
                for k,v in sorted(content.items(), key=lambda pair: pair[0].lower()):
                    if v.nodetype == 'leaf':
                        if not self._file_is_filtered(v):
                            tree.append((v, None))
                        else:
                            filtered_count += 1
                    elif v.nodetype == 'parent':
                        dirnode = create_directory_data(name=k, tree=v)
                        tree.append(create_tree(dirnode, v))

                node_id = (node['tid'], node['id'])
                self._filtered_counts[node_id] = filtered_count
                node['name'] = create_directory_name(node['name'], filtered_count)
                return (node, tree or None)

        forest = []  # Multiple trees as siblings
        for t in sorted(torrents, key=lambda t: t['name'].lower()):
            filetree = t['files']
            # This works because t['files'] always has 1 item: the torrent's name
            rootnodename = next(iter(filetree.keys()))
            rootnode = create_directory_data(rootnodename, tree=filetree)
            tree = create_tree(rootnode, filetree[rootnodename])
            if tree is not None:
                forest.append(tree)
        return forest

    def decorate(self, pos, data, is_first=True):
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
        node_id = (data['tid'], data['id'])
        self._widgets[node_id] = file_widget
        return urwid.AttrMap(file_widget, attr_map=None, focus_map=COLUMNS_FOCUS_MAP)

    def update(self, torrents):
        widgets = self._widgets
        for t in torrents:
            tid = t['id']

            # Update file nodes
            for f in t['files'].files:
                fid = f['id']
                node_id = (tid, fid)
                if node_id in widgets:
                    widgets[node_id].update(f)

            # Update directory nodes
            for name,content in t['files'].folders:
                fids = frozenset(f['id'] for f in content.files)
                node_id = (tid, fids)
                if node_id in widgets:
                    filtered_count = self._filtered_counts[node_id]
                    data = create_directory_data(name, tree=content,
                                                 filtered_count=filtered_count)
                    widgets[node_id].update(data)


class FileListWidget(urwid.WidgetWrap):
    def __init__(self, srvapi, tfilter, ffilter, columns):
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

        self._poller = srvapi.create_poller(
            srvapi.torrent.torrents, tfilter, keys=('files', 'name'))
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
        focus = self._listbox.focus
        if focus is not None:
            return focus.original_widget.torrent_id

    @property
    def focused_file_ids(self):
        """File IDs of the focused files in a tuple"""
        focus = self._listbox.focus
        if focus is not None:
            # The focused widget in the list can be a file or a directory.  If
            # it's a directory, the 'file_id' property returns the IDs of all
            # the contained files recursively.
            fid = focus.original_widget.file_id
            return tuple(fid) if isinstance(fid, (abc.Sequence, abc.Set)) else (fid,)
