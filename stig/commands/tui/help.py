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
from . import make_tab_title


class HelpCmd(base.HelpCmdbase):
    provides = {'tui'}
    tui = ExpectedResource

    def display_help(self, topics, lines):
        import urwid
        titlew = make_tab_title(','.join(topics), 'tabs.help.unfocused', 'tabs.help.focused')
        lines = [urwid.Text(l) for l in lines]
        helpw = urwid.ListBox(urwid.SimpleListWalker(lines))
        self.tui.tabs.load(titlew, helpw)


class VersionCmd(base.VersionCmdbase):
    provides = {'tui'}
