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


class TabID(int):
    def __repr__(self):
        return '<TabID %d>' % self


def _find_unused_id(existing_ids):
    """Find lowest unused ID in `existing_ids`"""
    if not existing_ids:
        return TabID(0)
    else:
        for id_candidate in range(0, max(existing_ids)+2):
            if id_candidate not in existing_ids:
                return TabID(id_candidate)
    raise RuntimeError('How did you get here?')


class Tabs(urwid.Widget):
    """Organize multiple widgets in tabs"""

    _sizing = frozenset([urwid.FLOW, urwid.BOX])

    def __init__(self, *contents, tabbar=None):
        """Create new Tabs widget

        contents: Iterable of dictionaries or iterables that match the
                  arguments of the `insert` method
        tabbar: Columns object that is used to display tab titles or any
                object with an 'original_widget' attribute (e.g. AttrMap) that
                returns a Columns object
        """
        if tabbar is None:
            self._tabbar = urwid.Columns([], dividechars=1)
            self._tabbar_render = self._tabbar.render
        elif hasattr(tabbar, 'original_widget'):
            self._tabbar = tabbar.original_widget
            self._tabbar_render = tabbar.render
        elif isinstance(tabbar, urwid.Columns):
            self._tabbar = tabbar
            self._tabbar_render = self._tabbar.render
        else:
            raise ValueError('tabbar must be Columns, not {}: {!r}'
                             .format(type(tabbar).__name__, tabbar))

        self._ids = []
        self._contents = urwid.MonitoredFocusList()
        for content in contents:
            if not isinstance(content, collections.Mapping):
                content = dict(zip(('title', 'widget', 'position', 'focus'),
                                   content))
            self.insert(**content)

    def render(self, size, focus=False):
        if len(size) < 2:
            cols, rows = (size[0], None)
        else:
            cols, rows = size

        if len(self._contents) < 1:
            # No contents - return empty canvas
            return urwid.SolidCanvas(' ', cols, rows)

        combinelist = []
        position = self._contents.focus

        # Render tab bar and add it to combinelist.  The tab bar is always
        # rendered as focused to highlight the focused tab.
        canvas = self._tabbar_render((cols,), True)
        combinelist.append((canvas, position, True))
        if rows is not None:
            rows -= 1  # Account for title bar

        # Render and add content of currently selected tab
        current_widget = self._contents[position]
        if current_widget is None:
            canvas = urwid.SolidCanvas(' ', cols, rows)
        else:
            if rows is not None:
                canvas = current_widget.render((cols,rows), focus)
            else:
                canvas = current_widget.render((cols,), focus)
        combinelist.append((canvas, position, focus))
        return urwid.CanvasCombine(combinelist)

    def get_index(self, position=None):
        """Return tab index at `position` or None if there are no tabs

        position: Index (int), ID (TabID) or None (focused tab)

        Raises IndexError if tab can't be found.
        """
        if position is None:
            return self.focus_position
        elif isinstance(position, TabID):
            if position in self._ids:
                return self._ids.index(position)
            else:
                e = IndexError('No tab with ID: {}'.format(position))
                e.value = position
                raise e
        else:
            i = self.focus_position if position is None else position
            if i is not None and not 0 <= i < len(self._contents):
                e = IndexError('No tab at position: {}'.format(position))
                e.value = position
                raise e
        return i

    def get_id(self, position=None):
        """Return unique TabID of tab at `position` or None if there are no tabs

        position: Index (int), ID (TabID) or None (focused tab)

        Raises IndexError if tab can't be found.
        """
        i = self.get_index(position)
        return self._ids[i] if i is not None else None

    def load(self, title, widget=None, position=None, focus=True):
        """Set content at `position`, in focused tab or in new tab

        If `position` is not None, is forwarded to `set_title`/`set_content`
        together with `title`/`widget`.

        If no tabs exist, a new tab is created with `title` and `widget`.  If
        `widget` is None, a blank widget is used.

        Otherwise, the focused tab's title and content is replaced with
        `set_title` and `set_content`.

        Set `focus` to False to load content in background.
        """
        if position is not None:
            # Overload content in specified tab
            self.set_content(widget, position=position)
            self.set_title(title, position=position)
            if focus:
                if isinstance(position, TabID):
                    self.focus_id = position
                else:
                    self.focus_position = position
        elif self.focus_position is None:
            # No tabs exist - create new tab
            self.insert(title, widget, focus=focus)
        else:
            # Overload content in focused tab
            self.set_content(widget)
            self.set_title(title)

    def insert(self, title, widget=None, position=-1, focus=True):
        """Insert new tab

        title: Any flow or fixed widget to use as the tab's title
        widget: Widget to show when this tab is selected or None
        position: Where to insert the new tab; int for list-like index or
                  'right'/'left' to insert next to focused tab
        focus: True to focus the new tab, False otherwise
        """
        curpos = self.focus_position
        if position == 'right':
            newpos = (curpos+1) if curpos is not None else 0
        elif position == 'left':
            newpos = max(curpos, 0) if curpos is not None else 0
        elif isinstance(position, int):
            if position < 0:
                newpos = position + len(self._contents) + 1
            else:
                newpos = position
        else:
            raise ValueError('Invalid position: {!r}'.format(position))

        # Insert new tab ID
        self._ids.insert(newpos, _find_unused_id(self._ids))

        # Insert title
        options = self._tabbar.options('pack')
        self._tabbar.contents.insert(newpos, (title, options))

        # Insert content
        self._contents.insert(newpos, widget)

        # Adjust focus
        if focus:
            self.focus_position = newpos

    def remove(self, position=None):
        """Remove tab `position`

        position: Index (int), ID (TabID) or None (focused tab)

        Raises IndexError if tab can't be found.
        """
        i = self.get_index(position)
        del self._ids[i]
        del self._tabbar.contents[i]
        del self._contents[i]

    def clear(self):
        """Remove all tabs"""
        while len(self._ids):
            self.remove(0)  # Remove tab at index 0

    def get_title(self, position=None):
        """Return tab title widget at `position`

        position: Index (int), ID (TabID) or None (focused tab)

        Raises IndexError if tab can't be found.
        """
        i = self.get_index(position)
        return self._tabbar.contents[i][0]

    def set_title(self, title, position=None):
        """Change the title widget of a tab

        title: New title widget
        position: Index (int), ID (TabID) or None (focused tab)

        Raises IndexError if tab can't be found.
        """
        i = self.get_index(position)
        self._tabbar.contents[i] = (title, self._tabbar.options('pack'))

    def get_content(self, position=None):
        """Return tab content widget at `position`

        position: Index (int), ID (TabID) or None (focused tab)

        Raises IndexError if tab can't be found.
        """
        i = self.get_index(position)
        return self._contents[i]

    def set_content(self, widget=None, position=None):
        """Set content of tab at `position` to `widget`

        position: Index (int), ID (TabID) or None (focused tab)

        Raises IndexError if tab can't be found.
        """
        i = self.get_index(position)
        self._contents[i] = widget

    @property
    def focus(self):
        """Content widget of currently focused tab or None if no tabs exist"""
        position = self._contents.focus
        if position is not None:
            return self._contents[position]
        return None

    @property
    def focus_position(self):
        """Index (starting from 0) of currently focused tab or None if no tabs exist"""
        return self._contents.focus

    @focus_position.setter
    def focus_position(self, position):
        if 0 <= position < len(self._contents):
            self._tabbar.contents.focus = position
            self._contents.focus = position
        else:
            raise IndexError('No tab at position: {!r}'.format(position))

    @property
    def focus_id(self):
        """TabID of currently focused tab or None if no tabs exist"""
        i = self.focus_position
        if i is not None:
            return self._ids[i]

    @focus_id.setter
    def focus_id(self, tabid):
        i = self.get_index(tabid)
        if 0 <= i < len(self._contents):
            self._tabbar.contents.focus = i
            self._contents.focus = i
        else:
            raise IndexError('No tab with ID: {}'.format(tabid))

    @property
    def contents(self):
        """Yields all content widgets"""
        for w in self._contents:
            yield w

    @property
    def titles(self):
        """Yields all tab title widgets"""
        for w in self._tabbar.contents:
            yield w[0]

    def __len__(self):
        return len(self._contents)

    def __iter__(self):
        return iter(self._contents)

    def selectable(self):
        return True

    def keypress(self, size, key):
        focus_widget = self.focus

        if focus_widget is not None:
            if len(size) > 1:
                #       maxcol   maxrow (-1 for the tab bar)
                size = (size[0], size[1]-1)
            else:
                size = (size[0],)

            if focus_widget.selectable():
                key = focus_widget.keypress(size, key)

        if key is not None:
            focus_pos = self.focus_position
            if key == 'left' and focus_pos > 0:
                self.focus_position -= 1
                key = None
            elif key == 'right' and focus_pos < len(self._contents)-1:
                self.focus_position += 1
                key = None
        return key
