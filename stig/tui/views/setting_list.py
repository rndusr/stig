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
from ...utils.usertypes import (Bool, Option)
from ...client import SettingFilter


def _change_setting(name, new_value, on_success=None):
    remote_name = name[4:]  # Remove 'srv.'

    if name in localcfg:
        try:
            localcfg[name] = new_value
        except ValueError as e:
            log.error('Cannot set %s = %r: %s', name, new_value, e)
        else:
            if on_success is not None:
                on_success()

    elif remote_name in remotecfg:
        async def setter():
            try:
                await remotecfg.set(remote_name, new_value)
            except (ValueError, srvapi.ClientError) as e:
                log.error('Cannot set %s = %r: %s', name, new_value, e)
            else:
                if on_success is not None:
                    on_success()
        aioloop.create_task(setter())

    else:
        raise RuntimeError('Not a setting name: %r' % name)


class SettingItemWidget(ItemWidgetBase):
    palette_unfocused = 'settinglist'
    palette_focused   = 'settinglist.focused'
    columns_focus_map = {}
    for col in TUICOLUMNS.values():
        columns_focus_map.update(col.style.focus_map)

    @property
    def id(self):
        return self.data['id']

    def selectable(self):
        return True

    @property
    def name(self):
        if self._cells.exists('name'):
            return self._cells.name.text.text

    @property
    def value_widget(self):
        if self._cells.exists('value'):
            return self._cells.value.base_widget

    @property
    def current_value(self):
        if self._cells.exists('value'):
            value_widget = self.value_widget
            if isinstance(value_widget, urwid.Edit):
                return value_widget.edit_text
            elif hasattr(value_widget, 'get_tui_value'):
                return value_widget.get_tui_value()

    @property
    def edit_mode(self):
        if self._cells.exists('value'):
            return isinstance(self._cells.value.base_widget, urwid.Edit)
        return False

    def keypress(self, size, key):
        current_value = self.current_value
        if current_value is None:
            return key
        elif isinstance(current_value, Bool):
            return self._keypress_bool(size, key)
        elif isinstance(current_value, Option):
            return self._keypress_option(size, key)
        else:
            return self._keypress_string(size, key)

    def _keypress_bool(self, size, key):
        cmd = self._command_map[key]
        if cmd is urwid.ACTIVATE:
            new_value = not self.current_value
            _change_setting(self.name, new_value)
        else:
            return key

    def _keypress_option(self, size, key):
        cmd = self._command_map[key]
        if cmd is urwid.ACTIVATE:
            current_value = self.current_value
            options = current_value.options
            index = options.index(current_value)
            if index < len(options)-1:
                index += 1
            else:
                index = 0
            new_value = options[index]
            _change_setting(self.name, new_value)
        else:
            return key

    def _keypress_string(self, size, key):
        cells = self._cells
        cmd = self._command_map[key]
        current_value = self.current_value
        value_widget = self.value_widget

        def edit():
            attrmap = self._cells.value.attrmap
            edit_widget = urwid.AttrMap(urwid.Edit(edit_text=str(current_value)),
                                        attr_map=attrmap.attr_map,
                                        focus_map=attrmap.focus_map)
            cells.replace('value', edit_widget)
            self._value_widget_temp = value_widget

        def unedit():
            cells.replace('value', self._value_widget_temp)
            delattr(self, '_value_widget_temp')

        if cmd is urwid.ACTIVATE:
            if not self.edit_mode:
                edit()
            else:
                new_value = value_widget.edit_text
                _change_setting(self.name, new_value, on_success=unedit)
        elif cmd is urwid.CANCEL:
            if self.edit_mode:
                unedit()
        elif self.edit_mode:
            key = super().keypress(size, key)
            cmd = self._command_map[key]
            # Don't allow user to focus next/previous setting when editing
            if cmd not in (urwid.CURSOR_DOWN, urwid.CURSOR_UP):
                return key
        else:
            return key


class SettingListWidget(ListWidgetBase):
    tuicolumns      = TUICOLUMNS
    ListItemClass   = SettingItemWidget
    keymap_context  = 'setting'
    palette_name    = 'settinglist'
    focusable_items = True

    def __init__(self, srvapi, keymap, sort=None, columns=None, title='Settings'):
        super().__init__(srvapi, keymap, columns=columns, sort=sort, title=title)
        self._sort = sort
        self._secondary_filter = None
        localcfg.on_change(self._handle_update)
        remotecfg.on_update(self._handle_update)
        self.refresh()

    def _handle_update(self, *_, **__):
        self._data_dict = {
            **{k: {'id': k,
                   'value': v,
                   'default': localcfg.default(k),
                   'description': localcfg.description(k)}
               for k,v in localcfg.items()},
            **{'srv.'+k: {'id': 'srv.'+k,
                          'value': v,
                          'default': '',
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

    @property
    def secondary_filter(self):
        return self._secondary_filter

    @secondary_filter.setter
    def secondary_filter(self, setting_filter):
        if setting_filter is None:
            self._secondary_filter = None
        else:
            self._secondary_filter = SettingFilter(setting_filter)
        self._invalidate()

    def _limit_items(self, setting_widgets):
        sfilter = self._secondary_filter
        if sfilter is not None:
            for sw in setting_widgets:
                if not sfilter.match(sw.data):
                    yield sw

