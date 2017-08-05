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


# TODO: It would be great if some columns (e.g. rate-up/down) would shrink to
#       the widest visible value (including its header).  Other columns would
#       share the remaining width using ('weight', x), giving some of them
#       (e.g. name) more space than others (e.g. path).
class CellWidgetBase(urwid.WidgetWrap):
    style = collections.defaultdict(lambda: 'default')
    header = urwid.Padding(urwid.Text('NO HEADER SPECIFIED'))
    width = ('weight', 100)
    align = 'right'

    def __init__(self):
        self.value = None
        self.text = urwid.Text('', wrap='clip', align=self.align)
        self.attrmap = urwid.AttrMap(self.text, self.style.attrs('unfocused'))
        return super().__init__(self.attrmap)

    def update(self, data):
        self.data.update(data)
        new_value = self.get_value()
        if self.value != new_value:
            self.value = new_value
            self.text.set_text(str(new_value))
            attr = self.style.attrs(self.get_mode(), focused=False)
            self.attrmap.set_attr_map({None: attr})

    def get_value(self):
        raise NotImplementedError()

    def get_mode(self):
        return None


def make_ItemWidget_class(item_name, tui_columns, unfocused, focused=None):
    """Return class to be used for rows in Torrent/File/Peer/... lists"""
    clsattrs = {'palette_unfocused': unfocused,
                'palette_focused': focused}

    if focused:
        # List items are focusable - create focus map that maps <unfocused> ->
        # <focused> that we can later use in __init__ for an AttrMap wrapper
        # around the whole row.
        COLUMNS_FOCUS_MAP = {}
        for col in tui_columns.values():
            COLUMNS_FOCUS_MAP.update(col.style.focus_map)
        clsattrs['COLUMNS_FOCUS_MAP'] = COLUMNS_FOCUS_MAP

    def __init__(self, item, cells):
        self._item = item    # Info of torrent/tracker/file/peer/...
        self._cells = cells  # Group instance that combines widgets horizontally

        if hasattr(self, 'COLUMNS_FOCUS_MAP'):
            # Item is focusable
            row = urwid.AttrMap(urwid.AttrMap(cells, attr_map=None, focus_map=self.COLUMNS_FOCUS_MAP),
                                self.palette_unfocused, self.palette_focused)
        else:
            # Item is not focusable
            row = urwid.AttrMap(cells, self.palette_unfocused)
        urwid.WidgetWrap.__init__(self, row)

        # Initialize cell widgets
        self.update(item)
    clsattrs['__init__'] = __init__

    def update(self, item):
        for widget in self._cells.widgets:
            widget.update(item)
        self._item = item
    clsattrs['update'] = update

    def id(self):
        return self._item['id']
    clsattrs['id'] = property(id)

    def item(self):
        return self._item
    clsattrs['item'] = property(item)

    def is_marked_getter(self):
        return self._cells.marked.is_marked
    def is_marked_setter(self, is_marked):
        self._cells.marked.is_marked = bool(is_marked)
    clsattrs['is_marked'] = property(fget=is_marked_getter, fset=is_marked_setter)

    return type(item_name+'ItemWidget', (urwid.WidgetWrap,), clsattrs)


from . import hooks
