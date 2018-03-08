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


def make_tab_title_widget(text_cropable, text_fixed='', attr_unfocused='', attr_focused=''):
    import urwid
    from ...utils.string import strcrop
    from ...tui.main import MAX_TAB_TITLE_WIDTH
    max_width = max(1, MAX_TAB_TITLE_WIDTH-len(text_fixed))
    text_cropped = strcrop(text_cropable, max_width, tail='…')
    return urwid.AttrMap(urwid.Text(''.join((text_cropped, text_fixed))),
                         attr_unfocused, attr_focused)
