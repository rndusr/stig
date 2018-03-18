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

from .setting import TUICOLUMNS
from . import (ItemWidgetBase, ListWidgetBase)
from ...main import (localcfg, remotecfg, srvapi, aioloop)


def _change_setting(name, new_value, on_success):
    remote_name = name[4:]  # Remove 'srv.'

    if name in localcfg:
        try:
            localcfg[name] = new_value
        except ValueError as e:
            log.error('Cannot set %s = %r: %s', name, new_value, e)
        else:
            on_success()

    elif remote_name in remotecfg:
        async def setter():
            try:
                await remotecfg.set(remote_name, new_value)
            except (ValueError, srvapi.ClientError) as e:
                log.error('Cannot set %s = %r: %s', name, new_value, e)
            else:
                on_success()
        aioloop.create_task(setter())

    else:
        raise RuntimeError('Invalid setting: %r' % name)


class SettingItemWidget(ItemWidgetBase):
    palette_unfocused = 'settinglist'
    palette_focused   = 'settinglist.focused'
    columns_focus_map = {}
    for col in TUICOLUMNS.values():
        columns_focus_map.update(col.style.focus_map)

    def keypress(self, size, key):
        cells = self._cells

        def edit():
            # value column might be missing
            if cells.exists('value'):
                self._text_widget_temp = text_widget = cells.value
                attrmap = text_widget.attrmap
                current_value = text_widget.value
                edit_widget = urwid.AttrMap(urwid.Edit(edit_text=str(current_value)),
                                            attr_map=attrmap.attr_map, focus_map=attrmap.focus_map)
                cells.replace('value', edit_widget)

        def unedit():
            cells.replace('value', self._text_widget_temp)
            delattr(self, '_text_widget_temp')

        edit_mode = cells.exists('value') and hasattr(cells.value, 'keypress')

        cmd = self._command_map[key]
        if cmd is urwid.ACTIVATE:
            if not edit_mode:
                edit()
            else:
                new_value = cells.value.base_widget.edit_text
                _change_setting(cells.name.text.text, new_value, on_success=unedit)

        elif cmd is urwid.CANCEL:
            if edit_mode:
                unedit()

        elif edit_mode:
            key = super().keypress(size, key)
            cmd = self._command_map[key]
            # Don't allow user to focus next/previous setting when editing
            if cmd not in (urwid.CURSOR_DOWN, urwid.CURSOR_UP):
                return key

        else:
            return key

    def selectable(self):
        return True


class SettingListWidget(ListWidgetBase):
    tuicolumns      = TUICOLUMNS
    ListItemClass   = SettingItemWidget
    keymap_context  = 'setting'
    palette_name    = 'settinglist'
    focusable_items = True

    def __init__(self, srvapi, keymap, sort=None, columns=('name', 'value', 'description')):
        super().__init__(srvapi, keymap, title='Settings', columns=columns)
        self._sort = sort
        localcfg.on_change(self._handle_update)
        remotecfg.on_update(self._handle_update)
        self.refresh()

    def _handle_update(self, *_, **__):
        self._items = {
            **{k: {'id': k, 'value': v,
                   'description': localcfg.description(k)}
               for k,v in localcfg.items()},
            **{'srv.'+k: {'id': 'srv.'+k, 'value': v,
                          'description': remotecfg.description(k)}
               for k,v in remotecfg.items()},
        }
        self._invalidate()

    def refresh(self):
        remotecfg.poll()

    @property
    def sort(self):
        return self._sort

    @sort.setter
    def sort(self, sort):
        ListWidgetBase.sort.fset(self, sort)
        self.refresh()
