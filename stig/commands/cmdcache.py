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


class CommandCache():
    """Store rc/CLI commands"""

    def __init__(self, cmdmgr):
        self._cmdmgr = cmdmgr
        self.rccmds = []
        self.clicmds = []

    def add_rccmds(self, *cmds):
        self.rccmds.extend(*cmds)
        log.debug('Cached rc commands: %r', self.rccmds)

    def add_clicmds(self, *cmds):
        self.clicmds.extend(*cmds)
        log.debug('Cached CLI commands: %r', self.clicmds)

    def select(self, source='ANY', interface='ANY'):
        """Return commands from `source` that provide `interface`

        source: 'cli' (command line) or 'rc' (rc file)
        interface: Provided interface ('cli' or 'tui')
        """
        if source == 'cli':
            cmdlines = self.clicmds
        elif source == 'rc':
            cmdlines = self.rccmds
        elif source == 'ANY':
            cmdlines = self.clicmds + self.rccmds
        else:
            raise ValueError('Invalid source: {!r}'.format(source))

        result = []
        for cmdline in cmdlines:
            cmdname = cmdline[0]
            cmdcls = self._cmdmgr.get_cmdcls(cmdname, interface=interface)
            if cmdcls is not None:
                result.append(cmdline)

        log.debug('Selected %s commands for %s interface: %s',
                  source, interface, result)
        return result

    def guess_ui(self, cmds):
        """Guess user interface (TUI or CLI) based on CLI commands"""
        if not cmds:
            return 'tui'

        log.debug('Guessing if the TUI is wanted:')
        guess = 'tui'
        for cmdline in cmds:
            cmdname = cmdline[0]
            debugmsg = '  %s: ' % cmdname

            tuicmd = self._cmdmgr.get_cmdcls(cmdname, interface='tui')
            clicmd = self._cmdmgr.get_cmdcls(cmdname, interface='cli')
            if tuicmd is None is clicmd:
                # Unknown command - maybe command is not loaded yet?
                debugmsg += 'unknown command - no guess'
                continue

            # Does command provides only one interface?
            elif tuicmd is None:
                debugmsg += 'no support for TUI - guessing CLI'
                guess = 'cli'   # Command NEEDS CLI
            elif clicmd is None:
                debugmsg += 'no support for CLI - guessing TUI'
                guess = 'tui'   # Command NEEDS TUI

            elif tuicmd.category == clicmd.category == 'torrent':
                # Torrent commands (start, stop, list, ...) inhibit the TUI
                debugmsg += 'torrent command - guessing CLI'
                guess = 'cli'

            # Some 'set' commands should enforce the tui or cli, other 'set'
            # commands shouldn't care.
            elif cmdline[0] == 'set' and len(cmdline) >= 3 or \
                 cmdline[0] == 'reset' and len(cmdline) >= 2:
                setting = cmdline[1]
                if setting.startswith('tui.'):
                    debugmsg += '{!r} starts with \'tui.\' - guessing TUI'.format(setting)
                    guess = 'tui'
                elif is_server_setting(setting):
                    debugmsg += 'is_server_setting({!r}) == True - guessing CLI'.format(setting)
                    guess = 'cli'

            elif clicmd is not None:
                debugmsg += 'CLI supported - guessing CLI'
                guess = 'cli'

            else:
                debugmsg += 'no guess'

        log.debug(debugmsg)
        log.debug('Guessed wanted UI: %s', guess)
        return guess
