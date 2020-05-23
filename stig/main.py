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
import os
import sys

from . import cliopts, logging, objects, settings
from .objects import cmdmgr, log, srvapi

# Remove python from process name when running inside tmux
if 'TMUX' in os.environ:
    try:
        from setproctitle import setproctitle
    except ImportError:
        pass
    else:
        from . import __appname__
        setproctitle(__appname__)

cliargs, clicmds = cliopts.parse()
objects.main_rcfile = cliargs['rcfile'] or settings.defaults.DEFAULT_RCFILE

logging.setup(debugmods=cliargs['debug'], filepath=cliargs['debug_file'])
logging.redirect_level('INFO', sys.stdout)


def run():
    cmdmgr.load_cmds_from_module('stig.commands.cli', 'stig.commands.tui')

    from .commands.guess_ui import guess_ui, UIGuessError
    from .commands import CmdError
    from . import hooks  # noqa: F401

    # Read commands from rc file
    rclines = ()
    if not cliargs['norcfile']:
        from .settings import rcfile
        try:
            rclines = rcfile.read(objects.main_rcfile)
        except rcfile.RcFileError as e:
            log.error('Loading rc file failed: {}'.format(e))
            sys.exit(1)

    # Decide if we run as a TUI or CLI
    if cliargs['tui']:
        cmdmgr.active_interface = 'tui'
    elif cliargs['notui']:
        cmdmgr.active_interface = 'cli'
    else:
        try:
            cmdmgr.active_interface = guess_ui(clicmds, cmdmgr)
        except UIGuessError:
            log.error('Unable to guess user interface')
            log.error('Provide one of these options: --tui/-t or --no-tui/-T')
            sys.exit(1)
        except CmdError as e:
            log.error(e)
            sys.exit(1)

    def run_commands():
        for cmdline in rclines:
            success = cmdmgr.run_sync(cmdline)
            # Ignored commands return None, which we consider a success here
            # because TUI commands like 'tab' in the rc file should have no
            # effect at all when in CLI mode.
            if success is False:
                return False

        # Exit if CLI commands fail
        if clicmds:
            success = cmdmgr.run_sync(clicmds)
            if not success:
                return False

        return True

    exit_code = 0

    # Run commands either in CLI or TUI mode
    if cmdmgr.active_interface == 'cli':
        # Exit when pipe is closed (e.g. `stig help | head -1`)
        import signal
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

        try:
            if not run_commands():
                exit_code = 1
        except KeyboardInterrupt:
            log.debug('Caught SIGINT')

    elif cmdmgr.active_interface == 'tui':
        from .tui import main as tui
        if not tui.run(run_commands):
            exit_code = 1

    asyncio.get_event_loop().run_until_complete(srvapi.rpc.disconnect('Quit'))

    # We're not closing the AsyncIO event loop here because it sometimes
    # complains about unfinished tasks and not calling it seems to work fine.
    sys.exit(exit_code)
