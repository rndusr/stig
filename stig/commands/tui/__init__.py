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

"""Commands for the TUI"""

def make_tab_title(text, attr_unfocused, attr_focused):
    import urwid
    return urwid.AttrMap(urwid.Text(text), attr_unfocused, attr_focused)

from .config import *
from .help import *
from .torrent import *
from .tui import *
