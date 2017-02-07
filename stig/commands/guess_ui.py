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

from ..settings import is_server_setting
from ..commands import is_op as is_cmd_op


class UIGuessError(Exception):
    pass

def guess_ui(clicmds, cmdmgr):
    """Guess desired user interface based on CLI commands

    Return 'tui' or 'cli'
    """
    if not clicmds:
        return 'tui'

    log.debug('Guessing whether TUI or CLI is wanted:')
    tui_needed = False
    cli_needed = False
    guess = 'cli'
    for cmdline in cmdmgr.split_cmdchain(clicmds):
        if is_cmd_op(cmdline):
            continue

        cmdname = cmdline[0]
        debugmsg = '  %s: ' % cmdname

        tuicmd = cmdmgr.get_cmdcls(cmdname, interface='tui')
        clicmd = cmdmgr.get_cmdcls(cmdname, interface='cli')
        if tuicmd is None is clicmd:
            debugmsg += 'unknown command - not guessing'

        # Does command provide only one interface?
        elif tuicmd is None:
            debugmsg += 'no support for TUI - demanding CLI'
            cli_needed = True
        elif clicmd is None:
            debugmsg += 'no support for CLI - demanding TUI'
            tui_needed = True

        elif tuicmd.category == clicmd.category == 'torrent':
            # Torrent commands (start, stop, list, ...) inhibit the TUI
            debugmsg += 'torrent command - guessing CLI'
            guess = 'cli'

        # Some 'set' commands should enforce the tui or cli, other 'set'
        # commands shouldn't care.
        elif cmdline[0] == 'set' and len(cmdline) >= 2 or \
             cmdline[0] == 'reset' and len(cmdline) >= 2:
            setting = cmdline[1]
            if setting.startswith('tui.'):
                debugmsg += 'TUI setting: %r - guessing TUI' % setting
                guess = 'tui'
            elif is_server_setting(setting):
                debugmsg += 'server setting: %r - guessing CLI' % setting
                guess = 'cli'
            else:
                debugmsg += 'other setting: %r - guessing TUI' % setting
                guess = 'tui'

        elif clicmd is not None:
            debugmsg += 'CLI supported - guessing CLI'
            guess = 'cli'

        else:
            debugmsg += 'no guess'
        log.debug(debugmsg)

    if cli_needed and tui_needed:
        raise UIGuessError('Unable to guess user interface')
    elif tui_needed:
        ui = 'tui'
    elif cli_needed:
        ui = 'cli'
    else:
        ui = guess

    log.debug('Guessed wanted UI: %s', ui)
    return ui
