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

import urwid
import collections

from ..table import ColumnHeaderWidget
from ..main import bottombar


class Style():
    """Map standard attributes to those defined in a urwid palette

    prefix: common prefix of all attributes
    extras: additional attributes (e.g. 'header')
    modes: additional subsections with 'focused' and 'unfocused' attributes
           (e.g. 'highlighted')
    focusable: True if 'focused' attributes should be mapped, False otherwise
    """

    def __init__(self, prefix, modes=(), extras=(), focusable=True):
        self._attribs = {
            'unfocused': self.dotify(prefix, 'unfocused')
        }
        for extra in extras:
            self._attribs[extra] = self.dotify(prefix, extra)

        if focusable:
            self._attribs['focused'] = self.dotify(prefix, 'focused')

        for mode in modes:
            self._attribs[mode+'.focused'] = self.dotify(prefix, mode, 'focused')
            self._attribs[mode+'.unfocused'] = self.dotify(prefix, mode, 'unfocused')

    def attrs(self, mode=None, focused=False):
        """Get attributes as specified in the urwid palette

        mode: one of the modes specified during initialization
        focused: If True the '...focused' attributes are returned,
                 '...unfocused otherwise
        """
        mode = '' if not mode else mode
        name = self.dotify(mode, 'focused' if focused else 'unfocused')
        if name in self._attribs:
            return self._attribs[name]
        else:
            return self._attribs[mode]

    @property
    def focus_map(self):
        """Map of all '...unfocused' -> '...focused' attributes"""
        focus_map = {}
        attribs = self._attribs
        for name in attribs:
            if name.endswith('unfocused'):
                name_focused = name[:-9] + 'focused'
                focus_map[attribs[name]] = attribs[name_focused]
        return focus_map

    @staticmethod
    def dotify(*strings):
        """Join non-empty strings with a '.'"""
        return '.'.join(x for x in (strings) if x)


class CellWidgetBase(urwid.WidgetWrap):
    """Base class for cells in items in Torrent/File/Peer/... lists"""

    style = collections.defaultdict(lambda: 'default')
    header = urwid.AttrMap(ColumnHeaderWidget(left='', right=''), 'header')
    width = ('weight', 100)
    align = 'right'

    def __init__(self):
        self.value = None
        self.text = urwid.Text('', wrap=self.wrap, align=self.align)
        self.attrmap = urwid.AttrMap(self.text, self.style.attrs('unfocused'))
        return super().__init__(self.attrmap)

    def update(self, data):
        self.data = data
        new_value = self.get_value()
        if self.value != new_value:
            self.value = new_value
            self.text.set_text(str(new_value))
            attr = self.style.attrs(self.get_mode(), focused=False)
            self.attrmap.set_attr_map({None: attr})

    def get_mode(self):
        return None

    @classmethod
    def set_header(cls, left=None, right=None):
        if left is not None:
            cls.header.base_widget.left = str(left)
        if right is not None:
            cls.header.base_widget.right = str(right)


class ItemWidgetBase(urwid.WidgetWrap):
    """Base class for items in Torrent/File/Peer/... lists"""

    # Derived classes must set these class attributes; lists with unfocusable
    # items (e.g. peer lists) don't have to set palette_focused and
    # columns_focus_map.
    columns_focus_map = NotImplemented
    palette_unfocused = NotImplemented
    palette_focused   = NotImplemented

    def __init__(self, data, cells):
        self._data = data    # Info of torrent/tracker/file/peer/... as mapping
        self._cells = cells  # Group instance that combines widgets horizontally

        # Create focusable or unfocusable item widget
        if self.columns_focus_map is not NotImplemented:
            item_widget = urwid.AttrMap(
                urwid.AttrMap(cells, attr_map=None, focus_map=self.columns_focus_map),
                self.palette_unfocused, self.palette_focused
            )
        else:
            item_widget = urwid.AttrMap(cells, self.palette_unfocused)
        urwid.WidgetWrap.__init__(self, item_widget)

        # Initialize cell widgets
        self.update(data)

    def update(self, data):
        for widget in self._cells.widgets:
            if hasattr(widget, 'update'):
                widget.update(data)
        self._data = data

    @property
    def id(self):
        """Unique, hashable ID of the displayed item"""
        raise NotImplementedError()

    @property
    def data(self):
        """Displayed data in dictionary form"""
        return self._data

    @property
    def is_marked(self):
        """Whether this item has been marked by the user"""
        if self._cells.exists('marked'):
            return self._cells.marked.is_marked
        else:
            return False

    @is_marked.setter
    def is_marked(self, is_marked):
        if self._cells.exists('marked'):
            self._cells.marked.is_marked = bool(is_marked)



from ..table import Table
from ..scroll import ScrollBar
class ListWidgetBase(urwid.WidgetWrap):
    """Base class for Torrent/File/Peer/... lists"""

    # Derived classes must set these class attributes
    tuicolumns      = NotImplemented
    ListItemClass   = NotImplemented
    keymap_context  = NotImplemented
    palette_name    = NotImplemented
    focusable_items = False

    def __init__(self, srvapi, keymap, columns=None, sort=None, title=None):
        self._srvapi = srvapi
        self._keymap = keymap

        if self.focusable_items:
            self._ListItemClass = keymap.wrap(self.ListItemClass, context=self.keymap_context)
        else:
            self._ListItemClass = self.ListItemClass

        self._data_dict = None
        self._marked = set()

        self._existing_widgets = set()
        self._hidden_widgets = set()

        self._sort = sort
        self._sort_orig = sort

        self._title_name = title
        self.title_updater = None

        self._table = Table(**self.tuicolumns)
        self._table.columns = columns or ()

        if self.focusable_items:
            walker = urwid.SimpleFocusListWalker([])
        else:
            walker = urwid.SimpleListWalker([])
        self._listbox = keymap.wrap(urwid.ListBox, context=self.keymap_context + 'list')(walker)

        listbox_sb = urwid.AttrMap(
            ScrollBar(urwid.AttrMap(self._listbox, self.palette_name)),
            'scrollbar'
        )
        pile = urwid.Pile([
            ('pack', urwid.AttrMap(self._table.headers, self.palette_name + '.header')),
            listbox_sb
        ])
        super().__init__(pile)

    def __repr__(self):
        return '<%s %s, #%s>' % (type(self).__name__, self.title, id(self))

    def _invalidate(self):
        if self.title_updater is not None:
            # First argument can be cropped if too long, second argument is fixed
            self.title_updater(self.title, ' [%d]' % self.count)
        super()._invalidate()

    def render(self, size, focus=False):
        # Remember focused item widget in case items get added or removed
        focusedw = self.focused_widget

        if self._data_dict is not None:
            self._update_existing_widgets(self._data_dict)
            self._data_dict = None

        self._hide_or_unhide_widgets()
        self._sort_widgets()

        # Ensure focus doesn't change when items get added or removed
        if focusedw is not None and self.focused_widget is not None and \
           focusedw.id != self.focused_widget.id:
            focused_id = focusedw.id
            for i,w in enumerate(self._listbox.body):
                if w.id == focused_id:
                    self._listbox.focus_position = i
                    break

        # Update number of marked items in this list
        bottombar.marked.update(len(self._marked))

        # focus=True because we always want to highlight the focused item, for
        # example when the CLI is open
        return super().render(size, focus=True)

    def _update_existing_widgets(self, data_dict):
        existing_widgets = self._existing_widgets
        dead_widgets = []

        for w in existing_widgets:  # w = *ItemWidget instance
            id = w.id
            try:
                # Update existing *ItemWidget instances with new data
                w.update(data_dict[id])
                del data_dict[id]
            except KeyError:
                # Item no longer exists in data_dict anymore
                dead_widgets.append(w)

        # Remove dead *ItemWidget instances
        walker = self._listbox.body
        marked = self._marked
        for w in dead_widgets:
            if w in walker:
                walker.remove(w)
            existing_widgets.remove(w)
            marked.discard(w)  # self._marked may have a reference too

        # Any items that haven't been used to update an existing *ItemWidget instance are new
        if data_dict:
            table = self._table
            ListItemClass = self._ListItemClass
            for data_id,data in data_dict.items():
                table.register(data_id)
                row = table.get_row(data_id)
                existing_widgets.add(ListItemClass(data, row))

    def _sort_widgets(self):
        walker = self._listbox.body
        if self._sort is not None:
            self._sort.apply(walker,
                             item_getter=lambda w: w.data,
                             inplace=True)

    def _hide_or_unhide_widgets(self):
        walker = self._listbox.body
        existing_widgets = self._existing_widgets
        hidden_widgets = self._hidden_widgets
        hidden_ids = tuple(w.id for w in self._limit_items(existing_widgets))
        for w in existing_widgets:
            widget_is_visible = w in walker
            hide_widget = w.id in hidden_ids
            if hide_widget and widget_is_visible:
                walker.remove(w)
                self._hidden_widgets.add(w)
            elif not hide_widget and not widget_is_visible:
                walker.append(w)

        if self.title_updater is not None:
            self.title_updater(self.title, ' [%d]' % self.count)

    def _limit_items(self, existing_widgets):
        """Iterate over filtered widgets"""
        return ()

    def clear(self):
        """Remove all list items"""
        self._table.clear()
        self._listbox.body[:] = ()
        self._listbox._invalidate()
        self._marked.clear()

    def refresh(self):
        """Update list items"""
        raise NotImplementedError


    @property
    def columns(self):
        return self._table.columns

    @columns.setter
    def columns(self, columns):
        self._table.columns = columns

    @property
    def sort(self):
        """*Sorter object or `None` to keep list items unsorted"""
        return self._sort

    @sort.setter
    def sort(self, sort):
        if sort == 'RESET':
            self._sort = self._sort_orig
        else:
            self._sort = sort

    @property
    def count(self):
        """Number of listed items"""
        # If this method was called before rendering, the contents of the
        # listbox widget are inaccurate and we have to use self._data_dict.  But
        # if we're called after rendering, self._data_dict is reset to None and
        # we have to count items in the listbox.
        if self._data_dict is not None:
            return len(self._data_dict)
        else:
            return len(self._listbox.body)

    @property
    def title_name(self):
        """The base name of the title"""
        return str(self._title_name or 'No title')

    @property
    def title_sort_order(self):
        """The sort order part of the title"""
        if self._sort is not None:
            sortstr = str(self._sort)
            if sortstr is not self._sort.DEFAULT_SORT:
                return '{%s}' % sortstr
        return ''

    @property
    def title(self):
        """Combined `title_name` and `title_sort_order`"""
        parts = [self.title_name]
        sort = self.title_sort_order
        if sort:
            parts.append(sort)
        return ' '.join(parts)


    @property
    def has_marked_column(self):
        return 'marked' in self._table.columns

    def mark(self, toggle=False, all=False):
        """Mark the currently focused item or all items"""
        self._set_mark(True, toggle=toggle, all=all)

    def unmark(self, toggle=False, all=False):
        """Unmark the currently focused item or all items"""
        self._set_mark(False, toggle=toggle, all=all)

    @property
    def marked(self):
        """Generator that yields ItemWidgetBase descendants"""
        yield from self._marked

    def _set_mark(self, mark, toggle=False, all=False):
        if toggle and self.focused_widget is not None:
            mark = not self.focused_widget.is_marked

        for widget in self._select_items_for_marking(all):
            widget.is_marked = mark
            if mark:
                self._marked.add(widget)
            else:
                self._marked.discard(widget)

    def _select_items_for_marking(self, all):
        if self.focused_widget is not None:
            if all:
                yield from self._listbox.body
            else:
                yield self.focused_widget

    def refresh_marks(self):
        """Redraw the "marked" column in all items widgets

        This shouldn't be needed unless the marked character was changed.
        """
        for widget in self._listbox.body:
            widget.is_marked = widget.is_marked


    @property
    def focused_widget(self):
        """Currently focused widget in list"""
        if self.focusable_items:
            return self._listbox.focus

    @property
    def focused_id(self):
        """ID of the currently focused list item or `None`"""
        focused_widget = self._listbox.focus
        if focused_widget is not None:
            return focused_widget.id

    @property
    def focus_position(self):
        """Focus position (first item is 0; `None` if list is empty)"""
        return self._listbox.focus_position

    @focus_position.setter
    def focus_position(self, focus_position):
        self._listbox.focus_position = min(focus_position, len(self._listbox.body)-1)


def stringify_torrent_filter(tfilter, torrents):
    if tfilter is None:
        return 'all'
    else:
        return str(tfilter)


from . import hooks
