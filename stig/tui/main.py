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


#
# Keybindings
#

KEYMAP_CONTEXTS = ('main', 'tabs', 'torrentlist', 'torrent', 'filelist', 'file', 'peerlist')

# Remove urwid's defaults
for key in tuple(urwid.command_map._command):
    del urwid.command_map[key]

from .keymap import Key
urwid.command_map[Key('pgup')]   = urwid.CURSOR_PAGE_UP
urwid.command_map[Key('pgdn')]   = urwid.CURSOR_PAGE_DOWN
urwid.command_map[Key('ctrl-b')] = urwid.CURSOR_PAGE_UP
urwid.command_map[Key('ctrl-f')] = urwid.CURSOR_PAGE_DOWN
urwid.command_map[Key('b')]      = urwid.CURSOR_PAGE_UP
urwid.command_map[Key('space')]  = urwid.CURSOR_PAGE_DOWN

urwid.command_map[Key('up')]     = urwid.CURSOR_UP
urwid.command_map[Key('down')]   = urwid.CURSOR_DOWN
urwid.command_map[Key('left')]   = urwid.CURSOR_LEFT
urwid.command_map[Key('right')]  = urwid.CURSOR_RIGHT
urwid.command_map[Key('meta-b')] = urwid.CURSOR_WORD_LEFT
urwid.command_map[Key('meta-f')] = urwid.CURSOR_WORD_RIGHT

urwid.command_map[Key('home')]   = urwid.CURSOR_MAX_LEFT
urwid.command_map[Key('end')]    = urwid.CURSOR_MAX_RIGHT
urwid.command_map[Key('ctrl-a')] = urwid.CURSOR_MAX_LEFT
urwid.command_map[Key('ctrl-e')] = urwid.CURSOR_MAX_RIGHT

urwid.command_map[Key('ctrl-k')] = urwid.DELETE_TO_EOL
urwid.command_map[Key('ctrl-u')] = urwid.DELETE_LINE
urwid.command_map[Key('ctrl-d')] = urwid.DELETE_CHAR_UNDER_CURSOR
urwid.command_map[Key('meta-d')] = urwid.DELETE_WORD_LEFT
urwid.command_map[Key('meta-backspace')] = urwid.DELETE_WORD_RIGHT
urwid.command_map[Key('ctrl-w')] = urwid.DELETE_WORD_RIGHT

urwid.command_map[Key('enter')]  = urwid.ACTIVATE
urwid.command_map[Key('escape')] = urwid.CANCEL
urwid.command_map[Key('ctrl-g')] = urwid.CANCEL
urwid.command_map[Key('ctrl-l')] = urwid.REDRAW_SCREEN

from ..settings.defaults import DEFAULT_KEYMAP
from .keymap import KeyMap
keymap = KeyMap(callback=lambda cmd,widget: cmdmgr.run_task(cmd, on_error=log.error))
for args in DEFAULT_KEYMAP:
    if args['action'][0] == '<' and args['action'][-1] == '>':
        args['action'] = keymap.mkkey(args['action'])
    keymap.bind(**args)
helpmgr.keymap = keymap


#
# Widgets
#

MAX_TAB_TITLE_WIDTH = 50

from .group import Group
from .tabs import (Tabs, TabBar)
from .cli import CLIEditWidget
from .logger import LogWidget
from .infobar import (KeyChainsWidget, QuickHelpWidget, ConnectionStatusWidget,
                      BandwidthStatusWidget, TorrentCountersWidget)
from . import theme

def load_theme(themeobj):
    """Load theme from `themeobj`

    themeobj: See `theme.load`

    If `themeobj` is a string, does not have a path and does not exist in the
    current working directory, try to load it from the same path as the rc file.
    """
    import os
    if isinstance(themeobj, str) and \
       os.sep not in themeobj and not os.path.exists(themeobj):
        # Path is not given and file does not exist in working dir.
        from ..settings.defaults import DEFAULT_RCFILE
        from ..main import cliargs
        rcfilepath = cliargs['rcfile'] or DEFAULT_RCFILE
        themefilepath = os.path.join(os.path.dirname(rcfilepath), themeobj)
        if os.path.exists(themefilepath):
            theme.load(themefilepath, urwidscreen)
            return
    theme.load(themeobj, urwidscreen)


def _create_cli_widget():
    def on_cancel(widget):
        widget.set_edit_text('')
        widgets.hide('cli')

    def on_accept(widget):
        cmd = widget.get_edit_text()
        on_cancel(widget)
        cmdmgr.run_task(cmd, on_error=log.error)

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
    tabbar=urwid.AttrMap(TabBar(), 'tabs.unfocused')
)

bottombar = Group(cls=urwid.Columns)
bottombar.add(name='counters', widget=TorrentCountersWidget(), options='pack')
bottombar.add(name='spacer', widget=urwid.AttrMap(_greedy_spacer(), 'bottombar'))
bottombar.add(name='bandwidth', widget=BandwidthStatusWidget(), options='pack')

cli = urwid.AttrMap(_create_cli_widget(), 'cli')

logwidget = LogWidget(maxrows=cfg['tui.log.height'].value,
                      autohide_delay=cfg['tui.log.autohide'].value)

keychains = KeyChainsWidget()
keymap.on_keychain(keychains.update)

widgets = keymap.wrap(Group, context='main')(cls=urwid.Pile)
widgets.add(name='topbar', widget=topbar, options='pack')
widgets.add(name='main', widget=tabs)
widgets.add(name='log', widget=logwidget, options='pack', visible=False)
widgets.add(name='cli', widget=cli, options='pack', visible=False)
widgets.add(name='bottombar', widget=bottombar, options='pack')
widgets.add(name='keychains', widget=keychains, options='pack')


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


def run(command_runner):
    """Run commands and start TUI

    Return False if any of the commands failed, True otherwise.
    """
    # Don't catch theme.ParserError - a broken default theme should make us
    # croak obviously and horribly
    theme.init(cfg['tui.theme'].default, urwidscreen)

    # Load tui-specific hooks before commands run (commands may trigger hooks)
    from . import hooks

    try:
        if not command_runner():
            return False
    # Make 'quit' behave as expected
    except urwid.ExitMainLoop:
        return True

    # Start logging to TUI widget instead of stdout/stderr
    logwidget.enable()

    topbar.help.update()

    # If no tabs have been opened by cli or rc file, open default tab
    if len(tabs) <= 0:
        for cmd in ( 'tab ls -c size,ratio,seeds,status,tracker,path,name,activity',
                     'tab ls active|incomplete',
                    ('tab ls downloading -c size,downloaded,progress,'
                     'rate-down,completed,eta,path,name'),
                    ('tab ls uploading -c size,uploaded,ratio,'
                     'rate-up,connections,seeds,tracker,path,name -s ratio'),
                    'tab ls stopped -c size,progress,seeds,activity,path,name',
                    'tab ls isolated -c error,tracker,path,name -s tracker',
                    'tab -t peers lsp -s eta,torrent',):
            cmdmgr.run_sync(cmd, on_error=log.error)
        tabs.focus_position = 1

    try:
        # Start polling torrent lists, counters, bandwidth usage, etc.
        aioloop.run_until_complete(srvapi.start_polling())
        urwidloop.run()
    finally:
        logwidget.disable()
        aioloop.run_until_complete(srvapi.stop_polling())

    return True
