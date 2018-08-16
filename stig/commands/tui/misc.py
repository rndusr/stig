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


from ..base import misc as base
from .. import (ExpectedResource, CmdError)
from ._common import make_tab_title_widget


class HelpCmd(base.HelpCmdbase):
    provides = {'tui'}
    tui = ExpectedResource

    def display_help(self, topics, lines):
        import urwid
        from ...tui.scroll import ScrollBar
        from ...tui.views.text import SearchableText
        from ...tui.main import keymap

        if hasattr(self, 'title'):
            titlew = make_tab_title_widget(str(self.title),
                                           attr_unfocused='tabs.help.unfocused',
                                           attr_focused='tabs.help.focused')
        else:
            titlew = make_tab_title_widget(','.join(topics),
                                           attr_unfocused='tabs.help.unfocused',
                                           attr_focused='tabs.help.focused')

        helptext_widget_cls = keymap.wrap(SearchableText, context='helptext')
        helptext_widget = helptext_widget_cls(lines)
        textw = urwid.AttrMap(helptext_widget, 'helptext')
        contentw = urwid.AttrMap(ScrollBar(textw), 'scrollbar')
        self.tui.tabs.load(titlew, contentw)


class VersionCmd(base.VersionCmdbase):
    provides = {'tui'}


class LogCmd(base.LogCmdbase):
    provides = {'tui'}
    tui = ExpectedResource

    def _do(self, action, *args):
        logwidget = self.tui.logwidget
        if action == 'clear':
            if len(tuple(logwidget.entries)) < 1:
                raise CmdError()
            else:
                logwidget.clear()

        elif action == 'scroll':
            args = ' '.join(args)
            if args == 'up':
                logwidget.scroll_relative('up', 1)
            elif args == 'down':
                logwidget.scroll_relative('down', 1)
            elif args == 'page up':
                logwidget.scroll_relative('up', logwidget.height-1)
            elif args == 'page down':
                logwidget.scroll_relative('down', logwidget.height-1)
            elif args == 'top':
                logwidget.scroll_to('top')
            elif args == 'bottom':
                logwidget.scroll_to('bottom')
            else:
                raise CmdError('Invalid arguments for "scroll": %r' % (args,))

        else:
            cmd_str = '%s %s' % (action, ' '.join(args))
            raise CmdError('Unsupported command in TUI mode: %s' % cmd_str)
