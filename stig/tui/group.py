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


class _Fill(urwid.SolidFill):
    def render(self, size, focus=False):
        size_len = len(size)
        if size_len == 0:
            size = (0, 0)
        elif size_len == 1:
            size = (size[0], 0)
        return super().render(size, focus=False)

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
        self._items_list = []
        self._items_dict = {}
        # Add initial widgets
        for widget in widgets:
            self.add(**widget)
        super().__init__(self._main)

    def _get_item_by_name(self, name, visible=False):
        """Return item dict identified by `name`

        visible: If True, return None if widget is hidden

        Raises ValueError if specified item doesn't exist.
        """
        try:
            item = self._items_dict[name]
        except KeyError:
            raise ValueError('Unknown name: %s' % name)
        else:
            if not visible or self.visible(item['name']):
                return item
            else:
                return None

    def _get_item_by_position(self, position, visible=False):
        """Return item dict identified by `position`

        visible: If True, return None if widget is hidden

        Raises ValueError if specified item doesn't exist.
        """
        try:
            item = self._items_list[position]
        except IndexError:
            raise ValueError('No item at position: %s' % position)
        else:
            if not visible or self.visible(item['name']):
                return item
            else:
                return None

    def get_position(self, name, visible=False):
        """Return position of item

        visible: If True, return None if widget is hidden

        Raises ValueError if no widget with `name` exists.
        """
        try:
            item = self._get_item_by_name(name)
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
                return self._items_list.index(item)

    def _parse_options(self, options):
        """Convert sizing options from a simpler format to urwid format

        See set_size method.
        """
        if type(options) is tuple:
            # Assume tuple is following urwid's format
            return self._main.options(*options)
        elif type(options) is str and options.isdigit():
            return self._main.options('weight', int(options))
        elif options == 'pack':
            return self._main.options('pack', None)
        elif type(options) is int:
            return self._main.options('given', options)
        else:
            raise ValueError('Invalid options: %s' % options)

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
        if self.exists(name):
            raise ValueError('Already added: {!r}'.format(name))
        else:
            options = self._parse_options(options)
            item = dict(
                name = name,            # Descriptive, unique handle
                widget = widget,        # Bare widget
                options = options,      # urwid options tuple, e.g. ('given',10) or ('weight',50)
                removable = removable,  # Wether this item can be deleted
            )

            if position == 'start':
                position = 0
            elif position == 'end':
                position = len(self._items_list)

            self._items_list.insert(position, item)
            self._items_dict[item['name']] = item

            # Insert dummy widget
            content = (_Fill(), self._parse_options(0))
            self._main.contents.insert(position, content)

            if visible:
                self.show(name)

    def remove(self, name):
        """Remove widget from group"""
        if self.exists(name):
            position = self.get_position(name)
            item = self._get_item_by_name(name)
            if not item['removable']:
                raise ValueError('Item is not removable: {}'.format(name))

            self._main.contents.pop(position)
            self._items_list.remove(item)
            del self._items_dict[item['name']]
        else:
            raise ValueError('Unknown item name: {}'.format(name))

    def clear(self):
        """Remove all removable items"""
        for item in tuple(self._items_list):
            if item['removable']:
                self.remove(item['name'])

    def replace(self, name, widget):
        """Replace `name`'s widget with `widget`

        Raises ValueError if `name` doesn't exist.
        """
        if not self.exists(name):
            raise ValueError('Unknown item name: {}'.format(name))
        else:
            # Remember if widget is currently visible or not
            visible = self.visible(name)

            # Replace item's widget
            item = self._get_item_by_name(name)
            item['widget'] = widget

            self.hide(name)
            if visible:
                self.show(name)

    def set_size(self, name, opts):
        """Change size options for widget

        opts: Must be one of the following:
                - An integer is translated to ('given', int[, False]).
                - A string that consists solely of numbers is translated to
                  ('weight', int).
                - The string 'pack' is translated to ('pack', None).
                - Any tuple Pile/Columns accepts as 'options' when adding to
                  the contents attribute.
        """
        item = self._get_item_by_name(name=name)
        item['options'] = self._parse_options(opts)
        self.hide(name)  # Refresh content in self._main
        self.show(name)

    def show(self, name):
        """Show widget specified by `name` and focus it if selectable"""
        if not self.exists(name):
            raise ValueError('Unknown item name: {}'.format(name))
        elif not self.visible(name):
            item = self._get_item_by_name(name)
            position = self.get_position(name)
            content = (item['widget'], item['options'])
            contents = self._main.contents
            if position >= len(contents):
                contents.append(content)
            else:
                contents[position] = content

            if item['widget'].selectable():
                self.focus_name = item['name']

    def hide(self, name, free_space=True):
        """
        Hide widget specified by `name` and focus next selectable widget

        If `free_space` is False, the widget's space is still occupied but
        empty.  This only works for widgets with a relative size.
        """
        if not self.exists(name):
            raise ValueError('Unknown item name: {!r}'.format(name))
        elif self.visible(name):
            position = self.get_position(name)
            item = self._get_item_by_name(name)
            opts = item['options']

            if not free_space and opts[0] == 'weight':
                placeholder_size = str(opts[1])
            else:
                placeholder_size = 0

            if len(self._items_list) == 1:
                content = (_Fill(), self._parse_options('100'))
            else:
                content = (_Fill(), self._parse_options(placeholder_size))
            self._main.contents[position] = content

            # Try to focus next selectable item
            self.focus_selectable(forward=False)
            self.focus_selectable(forward=True)

    def toggle(self, name, free_space=True):
        """Show widget if it's hidden and vice versa (see also `hide`)"""
        if self.exists(name):
            self.hide(name, free_space=free_space) if self.visible(name) else self.show(name)
        else:
            raise ValueError('Unknown item name: {!r}'.format(name))

    def visible(self, name):
        """Whether widget is hidden or not"""
        item = self._get_item_by_name(name)
        content = (item['widget'], item['options'])
        return content in self._main.contents

    def exists(self, name):
        """Whether widget exists or not"""
        return name in self._items_dict

    def __getattr__(self, name):
        """Return widget by name"""
        try:
            return self._get_item_by_name(name)['widget']
        except ValueError as e:
            raise AttributeError(e)

    @property
    def names(self):
        """Return list of known widget names"""
        return [item['name'] for item in self._items_list]

    @property
    def names_recursive(self):
        """Return list of known widget names recursively

        This dives into Group instances and adds their names, prepending the
        parent's name with '.' as a separator.
        """
        names = []
        for item in self._items_list:
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
        return [item['widget'] for item in self._items_list]

    @property
    def focus(self):
        """Focused widget or None"""
        try:
            item = self._get_item_by_position(self._main.focus_position)
            return item['widget']
        except ValueError:
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
            item = self._get_item_by_position(self._main.focus_position)
            return item['name']
        except ValueError:
            return None

    @focus_name.setter
    def focus_name(self, name):
        if self.exists(name):
            position = self.get_position(name, visible=True)
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
        max_pos = len(self._main.contents)-1
        new_pos = None
        pos = self.focus_position
        while 0 < pos < max_pos:
            pos = op(pos, 1)
            item = self._get_item_by_position(pos, visible=True)
            if item is not None and item['widget'].selectable():
                new_pos = pos
                break

        if new_pos is not None:
            self.focus_position = new_pos
            return True
        return False
