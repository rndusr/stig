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

"""Documentation commands"""

from ...logging import make_logger
log = make_logger(__name__)


from ..base import help as base
from .. import ExpectedResource
from .utils import make_tab_title_widget


class HelpCmd(base.HelpCmdbase):
    provides = {'tui'}
    tui = ExpectedResource

    def display_help(self, topics, lines):
        import urwid
        from ...tui.scroll import (Scrollable, ScrollBar)

        if hasattr(self, 'title'):
            titlew = make_tab_title_widget(str(self.title),
                                           attr_unfocused='tabs.help.unfocused',
                                           attr_focused='tabs.help.focused')
        else:
            titlew = make_tab_title_widget(','.join(topics),
                                           attr_unfocused='tabs.help.unfocused',
                                           attr_focused='tabs.help.focused')

        textw = urwid.AttrMap(Scrollable(urwid.Text('\n'.join(lines))), 'helptext')
        contentw = urwid.AttrMap(ScrollBar(textw), 'scrollbar')
        self.tui.tabs.load(titlew, contentw)


class VersionCmd(base.VersionCmdbase):
    provides = {'tui'}
