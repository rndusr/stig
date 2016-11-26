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

from ..logging import make_logger
log = make_logger(__name__)

import urwid
from . import urwidpatches

from ..main import (aioloop, cfg, cmdmgr, srvapi, helpmgr)
from ..settings.defaults import DEFAULT_KEYMAP


from .keymap import KeyMap
keymap = KeyMap(callback=lambda cmd,widget: cmdmgr(cmd, on_error=log.error))
for args in DEFAULT_KEYMAP:
    if args['action'][0] == '<' and args['action'][-1] == '>':
        args['action'] = keymap.key(args['action'])
    keymap.bind(**args)
helpmgr.keymap = keymap


from .group import Group
from .tabs import Tabs
from .cli import CLIEditWidget
from .logger import LogWidget
from .infobar import (QuickHelpWidget, ConnectionStatusWidget,
                      BandwidthStatusWidget, TorrentCountersWidget)


def _create_cli_widget():
    def on_cancel(widget):
        widget.set_edit_text('')
        widgets.hide('cli')

    def on_accept(widget):
        cmd = widget.get_edit_text()
        on_cancel(widget)
        cmdmgr(cmd, on_error=log.error)

    return CLIEditWidget(':',
                         on_accept=on_accept, on_cancel=on_cancel,
                         history_file=cfg['tui.cli.history'].value)

def _greedy_spacer():
    return urwid.Padding(urwid.Text(''))

topbar = Group(cls=urwid.Columns)
topbar.add(name='host',   widget=ConnectionStatusWidget(), options='pack')
topbar.add(name='spacer', widget=urwid.AttrMap(_greedy_spacer(), 'topbar'))
topbar.add(name='help',   widget=QuickHelpWidget(), options='pack')

tabs = keymap.wrap(Tabs, context='tabs')(
    tabbar=urwid.AttrMap(urwid.Columns([], dividechars=2), 'tabs.unfocused')
)

bottombar = Group(cls=urwid.Columns)
bottombar.add(name='counters', widget=TorrentCountersWidget(), options='pack')
bottombar.add(name='spacer', widget=urwid.AttrMap(_greedy_spacer(), 'bottombar'))
bottombar.add(name='bandwidth', widget=BandwidthStatusWidget(), options='pack')

cli = urwid.AttrMap(_create_cli_widget(), 'cli')

logwidget = LogWidget(maxrows=cfg['tui.log.height'].value,
                      autohide_delay=cfg['tui.log.autohide'].value)

widgets = keymap.wrap(Group, context='main')(cls=urwid.Pile)
widgets.add(name='topbar', widget=topbar, options='pack')
widgets.add(name='main', widget=tabs)
widgets.add(name='log', widget=logwidget, options='pack')
widgets.add(name='cli', widget=cli, options='pack', visible=False)
widgets.add(name='bottombar', widget=bottombar, options='pack')


def unhandled_input(key):
    key = keymap.evaluate(key)
    if key is not None:
        log.debug('Unhandled key: %s', key)

urwidscreen = urwid.raw_display.Screen()
urwidloop = urwid.MainLoop(widgets,
                           screen=urwidscreen,
                           event_loop=urwid.AsyncioEventLoop(loop=aioloop),
                           unhandled_input=unhandled_input,
                           handle_mouse=False)


def run(cmds):
    """Run commands and start TUI

    Return False if any of the commands failed, True otherwise.
    """
    # Load tui-specific hooks before commands run (commands may trigger hooks)
    from . import hooks

    for cmd in cmds:
        try:
            if not cmdmgr(cmd, block=True, on_error=log.error):
                return False
        # Make 'quit' behave as expected
        except urwid.ExitMainLoop:
            return True

    # Don't catch theme.ParserError.  Default theme should throw exceptions to
    # stdout.
    from . import theme
    theme.init(cfg['tui.theme'].value, urwidscreen)

    # Enable logging to tui widget instead of stdout/stderr
    logwidget.enable()

    # If no tabs have been opened by cli or rc file, open default tab
    if len(tabs) <= 0:
        cmdmgr('ls', on_error=log.error)

    try:
        # Start polling torrent lists, counters, bandwidth usage, etc.
        aioloop.run_until_complete(srvapi.start_polling())
        urwidloop.run()
    finally:
        logwidget.disable()
        aioloop.run_until_complete(srvapi.stop_polling())

    return True
