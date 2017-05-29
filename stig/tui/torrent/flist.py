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
import builtins

from .. import main as tui
from ..scroll import ScrollBar
from ..table import Table
from .flist_columns import TUICOLUMNS
from ...views.flist import (create_directory_data, create_directory_name)

COLUMNS_FOCUS_MAP = {}
for col in TUICOLUMNS.values():
    COLUMNS_FOCUS_MAP.update(col.style.focus_map)


class FileWidget(urwid.WidgetWrap):
    def __init__(self, tfile, row):
        self._cells = row
        super().__init__(urwid.AttrMap(row, 'filelist', 'filelist.focused'))
        self.update(tfile)

    def update(self, tfile):
        for widget in self._cells.widgets:
            widget.update(tfile)
        self._tfile = tfile

    @property
    def torrent_id(self):
        return self._tfile['tid']

    @property
    def file_id(self):
        return self._tfile['id']

    @property
    def is_marked(self):
        return self._cells.marked.is_marked

    @is_marked.setter
    def is_marked(self, is_marked):
        self._cells.marked.is_marked = bool(is_marked)

    @property
    def nodetype(self):
        """'parent' or 'leaf'"""
        return self._tfile.nodetype

    def __repr__(self):
        return '<{} {!r}>'.format(type(self).__name__, self._tfile['name'])


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
                            nonlocal fcount
                            fcount += 1
                        else:
                            filtered_count += 1
                    elif v.nodetype == 'parent':
                        dirnode = create_directory_data(name=k, tree=v)
                        tree.append(create_tree(dirnode, v))

                node_id = (node['tid'], node['id'])
                self._filtered_counts[node_id] = filtered_count
                node['name'] = create_directory_name(node['name'], filtered_count)
                return (node, tree or None)

        fcount = 0
        forest = []  # Multiple trees as siblings
        for t in sorted(torrents, key=lambda t: t['name'].lower()):
            filetree = t['files']
            # This works because t['files'] always has 1 item: the torrent's name
            rootnodename = next(iter(filetree.keys()))
            rootnode = create_directory_data(rootnodename, tree=filetree)
            tree = create_tree(rootnode, filetree[rootnodename])
            if tree is not None:
                forest.append(tree)
        self.filecount = fcount
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

    @property
    def widgets(self):
        """Yield all file and directory widgets in this tree"""
        yield from self._widgets.values()


class FileListWidget(urwid.WidgetWrap):
    def __init__(self, srvapi, tfilter, ffilter, columns, title=None):
        self._ffilter = ffilter
        self._torrents = ()
        self._marked = set()
        self._initialized = False

        # Create the fixed part of the title (everything minus the number of files listed)
        # If title is not given, create one from filters
        if title is None:
            tfilter_str = str(tfilter or 'all')
            if ffilter is None:
                title = tfilter_str
            else:
                title = '%s files of %s torrents' % (ffilter, tfilter_str)
        self._title_base = title
        self.title_updater = None

        self._table = Table(**TUICOLUMNS)
        self._table.columns = columns

        self._listbox = tui.keymap.wrap(urwid.ListBox, context='filelist')(urwid.SimpleListWalker([]))

        listbox_sb = urwid.AttrMap(
            ScrollBar(urwid.AttrMap(self._listbox, 'filelist')),
            'scrollbar'
        )
        pile = urwid.Pile([
            ('pack', urwid.AttrMap(self._table.headers, 'filelist.header')),
            listbox_sb
        ])
        super().__init__(pile)

        self._poller = srvapi.create_poller(
            srvapi.torrent.torrents, tfilter, keys=('files', 'name'))
        self._poller.on_response(self._handle_response)

    def _handle_response(self, response):
        if response is None or not response.torrents:
            self.clear()
        else:
            if self._initialized:
                self._update_listitems(response.torrents)
            else:
                self._init_listitems(response.torrents)
        if self.title_updater is not None:
            # First argument can be cropped if too long, second argument is fixed
            self.title_updater(self.title, ' [%d]' % self.count)
        self._invalidate()

    def _init_listitems(self, torrents):
        self.clear()
        if torrents:
            self._filetree = FileTreeDecorator(torrents, tui.keymap,
                                               self._table, self._ffilter)
            self._listbox.body = urwidtrees.widgets.TreeListWalker(self._filetree)
            self._listbox._invalidate()
            self._initialized = True

    def _update_listitems(self, torrents):
        if torrents:
            self._filetree.update(torrents)

    def clear(self):
        """Remove all list items"""
        self._table.clear()
        self._listbox.body = urwid.SimpleListWalker([])
        self._listbox._invalidate()
        self._initialized = False

    @property
    def title(self):
        return self._title_base

    @property
    def count(self):
        """Number of listed peers"""
        return self._filetree.filecount if hasattr(self, '_filetree') else 0

    def update(self):
        """Call `clear` and then poll immediately"""
        self.clear()
        self._poller.poll()

    @property
    def focus_position(self):
        positions = tuple(self._filetree.positions())
        return positions.index(self._listbox.focus_position)

    @focus_position.setter
    def focus_position(self, focus_position):
        positions = tuple(self._filetree.positions())
        i = min(focus_position, len(positions)-1)
        try:
            self._listbox.focus_position = positions[i]
        except KeyError:
            pass

    @property
    def focused_file(self):
        """Focused FileWidget instance"""
        focused = self._listbox.focus
        if focused is not None:
            return focused.original_widget

    @property
    def focused_torrent_id(self):
        """Torrent ID of the focused file's torrent"""
        focused = self.focused_file
        if focused is not None:
            return focused.torrent_id

    @property
    def focused_file_ids(self):
        """File IDs of the focused files in a tuple"""
        focused = self.focused_file
        if focused is not None:
            # The focused widget in the list can be a file or a directory.  If
            # it's a directory, the 'file_id' property returns the IDs of all
            # the contained files recursively.
            fid = focused.file_id
            return tuple(fid) if isinstance(fid, (abc.Sequence, abc.Set)) else (fid,)

    def all_children(self, pos):
        """Yield (position, widget) tuples of all sub-nodes (leaves and parents)"""
        ft = self._filetree
        lb = self._listbox
        def recurse(subpos):
            widget = lb.body[subpos].original_widget
            if ft.is_leaf(subpos):
                yield (subpos, widget)
            else:
                # Yield sub-parent nodes, but not the starting node that was
                # passed to us
                if subpos != pos:
                    yield (subpos, widget)

                new_subpos = ft.first_child_position(subpos)
                while new_subpos is not None:
                    yield from recurse(new_subpos)
                    new_subpos = ft.next_sibling_position(new_subpos)

        yield from recurse(pos)

    def mark(self, toggle=False, all=False):
        """Mark the currently focused item or all items"""
        self._set_mark(True, toggle=toggle, all=all)

    def unmark(self, toggle=False, all=False):
        """Unmark the currently focused item or all items"""
        self._set_mark(False, toggle=toggle, all=all)

    @property
    def marked(self):
        """Generator that yields FileWidgets"""
        yield from self._marked

    def _set_mark(self, mark, toggle=False, all=False):
        if toggle:
            focused = self.focused_file
            if focused is not None:
                mark = not focused.is_marked

        def get_widget(pos):
            return self._listbox.body[pos].original_widget

        def mark_leaves(pos, mark):
            get_widget(pos).is_marked = mark

            for subpos,widget in self.all_children(pos):
                if widget.nodetype == 'leaf':
                    widget.is_marked = mark
                    if mark:
                        self._marked.add(widget)
                    else:
                        self._marked.discard(widget)

                elif widget.nodetype == 'parent':
                    mark_leaves(subpos, mark)

        if all:
            # Top ancestor node positions are (0,), (1,), (3,) etc
            for pos in self._filetree.positions():
                if len(pos) == 1:
                    mark_leaves(pos, mark)
        else:
            mark_leaves(self._listbox.focus_position, mark)
        assert builtins.all(m.nodetype == 'leaf' for m in self._marked)

        # A parent node is marked only if all its children are marked.  To check
        # that, we walk through every ancestor up to the top and check all its
        # children.  There is no need to check the children of other parent
        # nodes (uncles, great uncles, etc) because they should already be
        # marked properly from previous runs.

        def all_children_marked(pos):
            marked = True
            childpos = self._filetree.first_child_position(pos)
            while childpos is not None:
                marked = marked and get_widget(childpos).is_marked
                childpos = self._filetree.next_sibling_position(childpos)
            return marked

        parpos = self._filetree.parent_position(self._listbox.focus_position)
        while parpos is not None:
            parwidget = get_widget(parpos)
            parwidget.is_marked = all_children_marked(parpos)
            parpos = self._filetree.parent_position(parpos)

    def refresh_marks(self):
        """Redraw the "marked" column in all rows"""
        for widget in self._filetree.widgets:
            widget.is_marked = widget.is_marked
