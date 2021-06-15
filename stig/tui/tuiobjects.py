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

"""
Application-wide instances for the TUI
"""

import asyncio

import urwid

from . import theme, urwidpatches  # noqa
from .. import objects
from ..settings.defaults import DEFAULT_KEYMAP
from .group import Group
from .keymap import KeyMap
from .logger import LogWidget
from .miscwidgets import (AvailableDiskSpaceWidget, BandwidthStatusWidget,
                          ConnectionStatusWidget, KeyChainsWidget, MarkedItemsWidget,
                          QuickHelpWidget, TorrentCountersWidget)
from .tabs import TabBar, Tabs

from ..logging import make_logger  # isort:skip
log = make_logger(__name__)


urwidpatches.apply_patches()


keymap = KeyMap(callback=lambda cmd,widget: objects.cmdmgr.run_task(cmd, on_error=log.error))
for args in DEFAULT_KEYMAP:
    if args['action'][0] == '<' and args['action'][-1] == '>':
        args['action'] = keymap.mkkey(args['action'])
    keymap.bind(**args)


MAX_TAB_TITLE_WIDTH = 50

def _create_cli_widget():
    def reset_cli(cli):
        cli.reset()
        widgets.hide('cli')

    def run_cmd(cli):
        objects.cmdmgr.run_task(cli.edit_text, on_error=log.error)
        reset_cli(cli)

    from .completer import Completer
    from ..completion import candidates

    def get_candidates(args):
        log.debug('Getting candidates for %r', args)
        if args.curarg_index == 0:
            log.debug('Completing command: %r', args[0])
            return candidates.commands()
        else:
            cmdcls = objects.cmdmgr.get_cmdcls(args[0])
            if cmdcls is not None:
                log.debug('  Completing argument for %r', cmdcls.__name__)
                return cmdcls.completion_candidates(args)

    import os
    history_file = os.path.join(objects.localcfg['tui.cli.history-dir'].full_path, 'commands')
    from ..commands import OPS
    from .cli import CLIEditWidget
    return CLIEditWidget(prompt=':',
                         history_file=history_file,
                         on_cancel=reset_cli,
                         on_accept=run_cmd,
                         completer=Completer(get_candidates, operators=OPS))

def _greedy_spacer():
    return urwid.Padding(urwid.Text(''))


# Widget names start with "_" if they are hidden, e.g. they aren't mentioned in
# the output of "help tui".

topbar = Group(cls=urwid.Columns)
topbar.add(name='host',   widget=ConnectionStatusWidget(), options='pack')
topbar.add(name='_spacer', widget=urwid.AttrMap(_greedy_spacer(), 'topbar'))
topbar.add(name='help',   widget=QuickHelpWidget(), options='pack')

tabs = keymap.wrap(Tabs, context='tabs')(
    tabbar=urwid.AttrMap(TabBar(), 'tabs.unfocused')
)

bottombar = Group(cls=urwid.Columns)
bottombar.add(name='counters', widget=TorrentCountersWidget(), options='pack')
bottombar.add(name='_spacer1', widget=urwid.AttrMap(_greedy_spacer(), 'bottombar'))
bottombar.add(name='diskspace', widget=AvailableDiskSpaceWidget(), options='pack')
bottombar.add(name='_spacer2', widget=urwid.AttrMap(_greedy_spacer(), 'bottombar'))
bottombar.add(name='marked', widget=MarkedItemsWidget(), options='pack')
bottombar.add(name='_spacer3', widget=urwid.AttrMap(_greedy_spacer(), 'bottombar'))
bottombar.add(name='bandwidth', widget=BandwidthStatusWidget(), options='pack')

cli = urwid.AttrMap(_create_cli_widget(), 'cli')

logwidget = LogWidget(height=int(objects.localcfg['tui.log.height']),
                      autohide_delay=objects.localcfg['tui.log.autohide'])

keychains = KeyChainsWidget()
keymap.on_keychain(keychains.update)

widgets = keymap.wrap(Group, context='main')(cls=urwid.Pile)
widgets.add(name='topbar', widget=topbar, options='pack')
widgets.add(name='main', widget=tabs)
widgets.add(name='log', widget=logwidget, options='pack', visible=False)
widgets.add(name='cli', widget=cli, options='pack', visible=False)
widgets.add(name='_keychains', widget=keychains, options='pack')
widgets.add(name='bottombar', widget=bottombar, options='pack')


def unhandled_input(key):
    key = keymap.evaluate(key)
    if key is not None:
        log.debug('Unhandled key: %s', key)

urwidscreen = urwid.raw_display.Screen()
urwidloop = urwid.MainLoop(widgets,
                           screen=urwidscreen,
                           event_loop=urwid.AsyncioEventLoop(loop=asyncio.get_event_loop()),
                           unhandled_input=unhandled_input,
                           handle_mouse=False)
