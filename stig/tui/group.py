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
import operator


class _FlowFill(urwid.SolidFill):
    def rows(self, size, focus=False):
        return 0


class Group(urwid.WidgetWrap):
    """Wrapper aroung Pile or Columns widget

    The purpose of this class it o make adding/removing, hiding/showing and
    accessing widgets simpler.
    """

    def __init__(self, *widgets, cls=urwid.Columns, **kwargs):
        """Create new Group widget

        Widgets can be added by providing mappings as positional arguments.
        Each mapping is then provided to the `add` method as keyword
        arguments.

        cls: `Columns` or `Pile` (or derivatives of either)

        All other keyword arguments are forwarded to `cls` on instantiation.
        """
        self._main = cls([], **kwargs)
        self._items = []
        # Add initial widgets
        for widget in widgets:
            self.add(**widget)
        super().__init__(self._main)

    def _get_item(self, name=None, position=None, visible=False):
        """Return item dict identified by `name` or `position`

        visible: If True, return None instead of widget if widget is hidden

        Raises ValueError in case of invalid name or IndexError in case of
        invalid position.
        """
        if name is not None:
            for item in self._items:
                if item['name'] == name:
                    if not visible or self.visible(item['name']):
                        return item
                    else:
                        return None
            raise ValueError('Unknown name: {}'.format(name))

        elif position is not None:
            try:
                item = self._items[position]
            except IndexError:
                raise IndexError('No item at position: {}'.format(position))
            else:
                if not visible or self.visible(item['name']):
                    return item
                else:
                    return None
        else:
            raise TypeError('Neither name nor position specified')

    def _get_position(self, name, visible=False):
        """Return position of item

        visible: If True, return None instead of widget if widget is hidden

        Raises ValueError if no widget with `name` exists.
        """
        try:
            item = self._get_item(name)
        except ValueError:
            raise ValueError('Unknown name: {}'.format(name))
        else:
            if visible:
                content = (item['widget'], item['options'])
                try:
                    return self._main.contents.index(content)
                except ValueError:
                    return None
            else:
                return self._items.index(item)

    def _parse_options(self, opts):
        """Convert sizing options from a simpler format to urwid format

        See set_size method.
        """
        if type(opts) is tuple:
            # Assume tuple is following urwid's format
            return self._main.options(*opts)
        elif type(opts) is str and opts.isdigit():
            return self._main.options('weight', int(opts))
        elif opts == 'pack':
            return self._main.options('pack', None)
        elif type(opts) is int:
            return self._main.options('given', opts)
        else:
            raise ValueError('Invalid options: {}'.format(opts))

    def add(self, name, widget, options=('weight', 100),
            position='end', visible=True, removable=False):
        """Insert new widget

        name: A string ([a-zA-Z0-9_]+) to get the widget via an attribute

        widget: Any widget that can live in a Columns/Pile
        options: See `set_size` method
        position: Insert position (integer, 'start' or 'end')
        visible: True to immediately show widget, False otherwise
        removable: True to allow complete removal of widget, False otherwise

        Raises ValueError if `name` already exists.
        """
        options = self._parse_options(options)
        item = dict(
            name = name,           # String handle
            widget = widget,       # Bare widget
            options = options,     # urwid options tuple, e.g. ('given',10) or ('weight',50)
            removable = removable, # Wether this item can be deleted
        )

        if self.exists(name):
            raise ValueError('Already added: {!r}'.format(name))
        else:
            if position == 'start':
                position = 0
            elif position == 'end':
                position = len(self._items)

            self._items.insert(position, item)
            self.show(name)
            if not visible:
                self.hide(name)

    def remove(self, name):
        """Remove widget from group"""
        if self.exists(name):
            position = self._get_position(name)
            item = self._get_item(name)
            if not item['removable']:
                raise ValueError('Item is not removable: {}'.format(name))
            self._main.contents.pop(position)
            self._items.remove(item)
        else:
            raise ValueError('Unknown item name: {}'.format(name))

    def clear(self):
        """Remove all removable items"""
        for item in tuple(self._items):
            if item['removable']:
                self.remove(item['name'])

    def replace(self, name, widget):
        """Remove `name` if it exists and add new item with the same name"""
        if not self.exists(name):
            raise ValueError('Unknown item name: {}'.format(name))
        else:
            visible = self.visible(name)
            item = self._get_item(name=name)
            item['widget'] = widget
            self.hide(name)
            if visible:
                self.show(name)

    def set_size(self, name, opts):
        """Change size options for widget

        opts: Must be one of the following:
                - An integer is translated to ('given', int).
                - A string that consists solely of numbers is translated to
                  ('weight', int).
                - The string 'pack' is translated to ('pack', None).
                - Any tuple Pile/Columns accepts as 'options' when adding to
                  the contents attribute.
        """
        item = self._get_item(name=name)
        item['options'] = self._parse_options(opts)
        self.hide(name)  # Refresh content in self._main
        self.show(name)

    def show(self, name):
        """Show widget with specific name and focus it if selectable"""
        if not self.exists(name):
            raise ValueError('Unknown item name: {}'.format(name))
        elif not self.visible(name):
            item = self._get_item(name)
            position = self._get_position(name)
            content = (item['widget'], item['options'])
            if position >= len(self._main.contents):
                self._main.contents.append(content)
            else:
                self._main.contents[position] = content

            if item['widget'].selectable():
                self.focus_name = item['name']

    def hide(self, name):
        """Hide widget with specific name and focus the next selectable widget"""
        if not self.exists(name):
            raise ValueError('Unknown item name: {!r}'.format(name))
        elif self.visible(name):
            position = self._get_position(name)
            opts = self._get_item(name)['options']

            if opts[0] == 'weight':
                self._main.contents[position] = (_FlowFill(),
                                                 self._main.options('weight', opts[1]))
            else:
                self._main.contents[position] = (_FlowFill(),
                                                 self._main.options('given', 0))
            # Try to focus next selectable item
            self.focus_selectable(forward=False)
            self.focus_selectable(forward=True)

    def toggle(self, name):
        """Show widget if it's hidden and vice versa"""
        if self.exists(name):
            self.hide(name) if self.visible(name) else self.show(name)
        else:
            raise ValueError('Unknown item name: {!r}'.format(name))

    def visible(self, name):
        """Whether widget is hidden or not"""
        item = self._get_item(name)
        content = (item['widget'], item['options'])
        return content in self._main.contents

    def exists(self, name):
        """Whether widget exists or not"""
        return any(item['name'] == name for item in self._items)

    def __getattr__(self, name):
        """Return widget"""
        try:
            return self._get_item(name)['widget']
        except ValueError as e:
            raise AttributeError(e)

    @property
    def names(self):
        """Return list of known widget names"""
        return [item['name'] for item in self._items]

    @property
    def names_recursive(self):
        """Return list of known widget names recursively

        This dives into Group instances and adds their names, prepending the
        parent's name with '.' as a separator.
        """
        names = []
        for item in self._items:
            if isinstance(item['widget'], Group):
                names.append(item['name'])
                names.extend('{}.{}'.format(item['name'], subname)
                             for subname in item['widget'].names_recursive)
            else:
                names.append(item['name'])
        return names

    @property
    def widgets(self):
        """Return list of all widgets (hidden or visible)"""
        return [item['widget'] for item in self._items]

    @property
    def focus(self):
        """Focused widget or None"""
        try:
            item = self._get_item(position=self._main.focus_position)
            return item['widget']
        except IndexError:
            return None

    @property
    def focus_position(self):
        """Position of currently focused widget or None"""
        return self._main.focus_position

    @focus_position.setter
    def focus_position(self, position):
        self._main.focus_position = position

    @property
    def focus_name(self):
        """Name of currently focused widget or None"""
        try:
            item = self._get_item(position=self._main.focus_position)
            return item['name']
        except IndexError as e:
            return None

    @focus_name.setter
    def focus_name(self, name):
        if self.exists(name):
            position = self._get_position(name, visible=True)
            if position is not None:
                self._main.focus_position = position
        else:
            raise ValueError('Unknown item name: {}'.format(name))

    def focus_selectable(self, forward=True):
        """Change focus to next selectable widget

        forward: True to select next widget, False to select previous widget

        Returns True if focus was changed, False otherwise.
        """
        op = operator.add if forward else operator.sub

        new_pos = op(self.focus_position, 1)
        try:
            while True:
                item = self._get_item(position=new_pos, visible=True)
                if item is not None and item['widget'].selectable():
                    break
                else:
                    new_pos = op(new_pos, 1)
            self.focus_position = new_pos
        except IndexError:
            return False
        else:
            return True

    def keypress(self, size, key):
        if self.focus is None:
            return key

        if self.focus.selectable():
            key = self.focus.keypress(size, key)

        if key is not None:
            # Child widgets don't want key.
            # Move focus to next/previous selectable widget.
            if isinstance(self._main, urwid.Columns) and key == 'left' or \
               isinstance(self._main, urwid.Pile)    and key == 'up':
                if self.focus_selectable(forward=False):
                    key = None
            elif isinstance(self._main, urwid.Columns) and key == 'right' or \
                 isinstance(self._main, urwid.Pile)    and key == 'down':
                if self.focus_selectable(forward=True):
                    key = None

        return key

    def selectable(self):
        for item in self._items:
            if item['widget'].selectable() and self.visible(item['name']):
                return True
        return False
