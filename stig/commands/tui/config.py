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

from ..base import config as base
from . import _mixin as mixin


class RcCmd(base.RcCmdbase):
    provides = {'tui'}

class ResetCmd(base.ResetCmdbase):
    provides = {'tui'}

    def run(self, NAME):
        if not NAME:
            # Get name from focused item in setting list
            from ...tui import main as tui
            from ...tui.views.setting_list import SettingListWidget
            widget = tui.tabs.focus
            if isinstance(widget, SettingListWidget):
                setting_name = widget.focused_widget.name
                return super().run((setting_name,))
        return super().run(NAME)


class SetCmd(base.SetCmdbase,
             mixin.create_list_widget):
    provides = {'tui'}

    def make_setting_list(self, sort, columns):
        from ...tui.views.setting_list import SettingListWidget
        self.create_list_widget(SettingListWidget, theme_name='settinglist',
                                sort=sort, columns=columns)


class RateLimitCmd(base.RateLimitCmdbase,
                   mixin.make_request, mixin.select_torrents, mixin.polling_frenzy):
    provides = {'tui'}

    async def _set_limits(self, TORRENT_FILTER, directions, limit, adjust=False, quiet=False):
        if TORRENT_FILTER == ['global']:
            return await self._set_global_limit(directions, limit,
                                                adjust=adjust, quiet=quiet)
        else:
            return await self._set_individual_limit(TORRENT_FILTER, directions, limit,
                                                    adjust=adjust, quiet=quiet)
