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
import os
from . import urwidpatches
from ..singletons import (aioloop, localcfg, cmdmgr, srvapi, geoip)


# Keybindings
from ..settings.defaults import DEFAULT_KEYMAP
from .keymap import KeyMap
keymap = KeyMap(callback=lambda cmd,widget: cmdmgr.run_task(cmd, on_error=log.error))
for args in DEFAULT_KEYMAP:
    if args['action'][0] == '<' and args['action'][-1] == '>':
        args['action'] = keymap.mkkey(args['action'])
    keymap.bind(**args)


# Widgets
MAX_TAB_TITLE_WIDTH = 50

from .group import Group
from .tabs import (Tabs, TabBar)
from .cli import CLIEditWidget
from .logger import LogWidget
from .miscwidgets import (KeyChainsWidget, QuickHelpWidget, ConnectionStatusWidget,
                          BandwidthStatusWidget, TorrentCountersWidget, MarkedItemsWidget)
from . import theme

def load_theme(themeobj):
    """
    Load theme from `themeobj`

    themeobj: See `theme.load`

    If `themeobj` is a string, does not have a path and does not exist in the
    current working directory, try to load it from the same path as the rc file.
    """
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



def load_geoip_db():
    """
    Load geolocation database in a background task
    """
    def _handle_geoip_load_result(task):
        import asyncio
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except geoip.GeoIPError as e:
            log.error(e)
    task = aioloop.create_task(geoip.load(loop=aioloop))
    task.add_done_callback(_handle_geoip_load_result)



def _create_cli_widget():
    # TODO: If it's 2019, remove the following block.
    #
    # DEFAULT_HISTORY_FILE was deprecated in v0.10.0 to allow multiple history
    # files.  Silently move the old history file to its new destination.
    from xdg.BaseDirectory import xdg_data_home  as XDG_DATA_HOME
    from ..settings.defaults import DEFAULT_HISTORY_DIR
    from .. import __appname__
    old_history_file = os.path.join(XDG_DATA_HOME, __appname__, 'history')
    if os.path.exists(old_history_file):
        if not os.path.exists(DEFAULT_HISTORY_DIR):
            os.makedirs(DEFAULT_HISTORY_DIR)
        os.rename(old_history_file, os.path.join(DEFAULT_HISTORY_DIR, 'commands'))

    def reset_cli(cli):
        cli.reset()
        widgets.hide('cli')

    def run_cmd(cli):
        cmdmgr.run_task(cli.edit_text, on_error=log.error)
        reset_cli(cli)

    from .completion import Completer
    from ..completion import candidates
    class MyCompleter(Completer):
        def get_candidates(self, args, curarg_index, curarg_curpos):
            log.debug('Getting candidates for %r, %r, %r', args, curarg_index, curarg_curpos)
            if curarg_index == 0:
                log.debug('Completing command: %r', args[0])
                return (cmdcls.name for cmdcls in cmdmgr.active_commands)
            else:
                cmdcls = cmdmgr.get_cmdcls(args[0])
                if cmdcls is not None:
                    log.debug('  Completing argument for %r', cmdcls.__name__)
                    return cmdcls.completion_candidates(args, curarg_index, curarg_curpos)

    history_file = os.path.join(localcfg['tui.cli.history-dir'], 'commands')
    from ..commands import OPS
    return CLIEditWidget(prompt=':',
                         history_file=history_file,
                         on_cancel=reset_cli,
                         on_accept=run_cmd,
                         completer=MyCompleter(operators=OPS))



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
bottombar.add(name='spacer1', widget=urwid.AttrMap(_greedy_spacer(), 'bottombar'))
bottombar.add(name='marked', widget=MarkedItemsWidget(), options='pack')
bottombar.add(name='spacer2', widget=urwid.AttrMap(_greedy_spacer(), 'bottombar'))
bottombar.add(name='bandwidth', widget=BandwidthStatusWidget(), options='pack')

cli = urwid.AttrMap(_create_cli_widget(), 'cli')

logwidget = LogWidget(height=int(localcfg['tui.log.height']),
                      autohide_delay=localcfg['tui.log.autohide'])

keychains = KeyChainsWidget()
keymap.on_keychain(keychains.update)

widgets = keymap.wrap(Group, context='main')(cls=urwid.Pile)
widgets.add(name='topbar', widget=topbar, options='pack')
widgets.add(name='main', widget=tabs)
widgets.add(name='log', widget=logwidget, options='pack', visible=False)
widgets.add(name='cli', widget=cli, options='pack', visible=False)
widgets.add(name='keychains', widget=keychains, options='pack')
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


def run(command_runner):
    """
    Run commands and start TUI

    Return False if any of the commands failed, True otherwise.
    """
    # Don't catch theme.ParserError - a broken default theme should make us
    # croak obviously and horribly
    theme.init(localcfg.default('tui.theme'), urwidscreen)

    # Load tui-specific hooks before commands run (commands may trigger hooks)
    from . import hooks

    try:
        if not command_runner():
            return False
    # Make 'quit' behave as expected
    except urwid.ExitMainLoop:
        return True

    # Load/Download GeoIP database
    if geoip.available and localcfg['geoip']:
        load_geoip_db()

    # Start logging to TUI widget instead of stdout/stderr
    logwidget.enable()

    topbar.help.update()

    # If no tab has been opened by cli or rc file, open default tabs
    if len(tabs) <= 0:
        for cmd in ('tab ls -c seeds,status,ratio,path,name,tracker',
                    'tab ls active|incomplete',
                    'tab ls downloading -c size,downloaded,%downloaded,rate-down,completed,eta,path,name',
                    'tab ls uploading -c size,ratio,uploaded,rate-up,peers,seeds,tracker,path,name',
                    'tab -t peers lsp -s torrent',
                    'tab ls stopped -s ratio,path -c size,%downloaded,seeds,ratio,activity,path,name',
                    'tab ls isolated -c error,tracker,path,name -s tracker'):
            cmdmgr.run_sync(cmd, on_error=log.error)
        tabs.focus_position = 1

    try:
        # Start polling torrent lists, counters, bandwidth usage, etc.
        aioloop.run_until_complete(srvapi.start_polling())
        old = urwidscreen.tty_signal_keys('undefined','undefined',
                                          'undefined','undefined','undefined')
        urwidloop.run()
    finally:
        urwidscreen.tty_signal_keys(*old)
        logwidget.disable()
        aioloop.run_until_complete(srvapi.stop_polling())

    return True
