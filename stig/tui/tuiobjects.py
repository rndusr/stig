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

from ..logging import make_logger
log = make_logger(__name__)

from .. import objects


# Keybindings
from .keymap import KeyMap
from ..settings.defaults import DEFAULT_KEYMAP
keymap = KeyMap(callback=lambda cmd,widget: objects.cmdmgr.run_task(cmd, on_error=log.error))
for args in DEFAULT_KEYMAP:
    if args['action'][0] == '<' and args['action'][-1] == '>':
        args['action'] = keymap.mkkey(args['action'])
    keymap.bind(**args)


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
        except objects.geoip.GeoIPError as e:
            log.error(e)
    task = objects.aioloop.create_task(objects.geoip.load())
    task.add_done_callback(_handle_geoip_load_result)


# Widgets
import urwid
from . import urwidpatches
from . import theme

MAX_TAB_TITLE_WIDTH = 50

def _create_cli_widget():
    def reset_cli(cli):
        cli.reset()
        widgets.hide('cli')

    def run_cmd(cli):
        objects.cmdmgr.run_task(cli.edit_text, on_error=log.error)
        reset_cli(cli)

    from ..completion import (Candidates, Candidate)
    from .completer import Completer
    def get_candidates(args):
        log.debug('Getting candidates for %r', args)
        if args.curarg_index == 0:
            log.debug('Completing command: %r', args[0])
            cands = (Candidate(cmdcls.name,
                               description=cmdcls.description,
                               in_parens='%s' % (', '.join(cmdcls.aliases),))
                     for cmdcls in objects.cmdmgr.active_commands)
            return Candidates(cands, label='Commands')
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

from .group import Group
from .miscwidgets import (ConnectionStatusWidget, QuickHelpWidget)

topbar = Group(cls=urwid.Columns)
topbar.add(name='host',   widget=ConnectionStatusWidget(), options='pack')
topbar.add(name='spacer', widget=urwid.AttrMap(_greedy_spacer(), 'topbar'))
topbar.add(name='help',   widget=QuickHelpWidget(), options='pack')

from .tabs import (Tabs, TabBar)
tabs = keymap.wrap(Tabs, context='tabs')(
    tabbar=urwid.AttrMap(TabBar(), 'tabs.unfocused')
)

from .miscwidgets import (TorrentCountersWidget, MarkedItemsWidget, BandwidthStatusWidget)
bottombar = Group(cls=urwid.Columns)
bottombar.add(name='counters', widget=TorrentCountersWidget(), options='pack')
bottombar.add(name='spacer1', widget=urwid.AttrMap(_greedy_spacer(), 'bottombar'))
bottombar.add(name='marked', widget=MarkedItemsWidget(), options='pack')
bottombar.add(name='spacer2', widget=urwid.AttrMap(_greedy_spacer(), 'bottombar'))
bottombar.add(name='bandwidth', widget=BandwidthStatusWidget(), options='pack')

cli = urwid.AttrMap(_create_cli_widget(), 'cli')

from .logger import LogWidget
logwidget = LogWidget(height=int(objects.localcfg['tui.log.height']),
                      autohide_delay=objects.localcfg['tui.log.autohide'])

from .miscwidgets import KeyChainsWidget
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
                           event_loop=urwid.AsyncioEventLoop(loop=objects.aioloop),
                           unhandled_input=unhandled_input,
                           handle_mouse=False)
