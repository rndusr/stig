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

import asyncio

import urwid

from ..settings.defaults import DEFAULT_TAB_COMMANDS

from ..logging import make_logger  # isort:skip
log = make_logger(__name__)


def run(command_runner):
    """
    Run commands and start TUI

    Return False if any of the commands failed, True otherwise.
    """
    from .. import objects
    from .import tuiobjects

    # Don't catch theme.ParserError - a broken default theme should make us
    # croak obviously and horribly
    tuiobjects.theme.init(objects.localcfg.default('tui.theme'), tuiobjects.urwidscreen)

    # Load tui-specific hooks before commands run (commands may trigger hooks)
    from . import hooks  # noqa

    try:
        if not command_runner():
            return False
    # Make 'quit' behave as expected
    except urwid.ExitMainLoop:
        return True

    # Start logging to TUI widget instead of stdout/stderr
    tuiobjects.logwidget.enable()

    tuiobjects.topbar.help.update()

    # If no tab has been opened by cli or rc file, open default tabs
    if len(tuiobjects.tabs) <= 0:
        for cmd in DEFAULT_TAB_COMMANDS:
            objects.cmdmgr.run_sync(cmd, on_error=log.error)

    try:
        # Start polling torrent lists, counters, bandwidth usage, etc.
        asyncio.get_event_loop().run_until_complete(objects.srvapi.start_polling())
        old = tuiobjects.urwidscreen.tty_signal_keys('undefined','undefined',
                                                     'undefined','undefined','undefined')
        tuiobjects.urwidloop.run()
    finally:
        tuiobjects.urwidscreen.tty_signal_keys(*old)
        tuiobjects.logwidget.disable()

    return True
