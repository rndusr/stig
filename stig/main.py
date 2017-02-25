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

import sys
import asyncio
aioloop = asyncio.get_event_loop()


from . import cliopts
from . import logging
cliargs, clicmds = cliopts.parse()
if cliargs['profile_file'] is not None:
    logging.enable_profiling(cliargs['profile_file'])
logging.setup(debugmods=cliargs['debug'], filepath=cliargs['debug_file'])
logging.redirect_level('INFO', sys.stdout)
log = logging.make_logger()


from . import settings
cfg = settings.Settings()
settings.init_defaults(cfg)

def _log_cfg_change(setting):
    msg = '{} = {!s}'.format(setting.name, setting)
    if setting.value == setting.default:
        msg += ' (default)'
    log.debug(msg)
cfg.on_change(_log_cfg_change)


from .helpmgr import HelpManager
helpmgr = HelpManager()
helpmgr.settings = cfg


from .client import API
srvapi = API(url=cfg['srv.url'].value,
             interval=cfg['tui.poll'].value,
             loop=aioloop)
srvapi.bandwidth_unit = cfg['unit.bandwidth'].value
srvapi.bandwidth_prefix = cfg['unitprefix.bandwidth'].value
srvapi.size_unit = cfg['unit.size'].value
srvapi.size_prefix = cfg['unitprefix.size'].value

settings.init_server_defaults(cfg, srvapi.settings)


from .commands import CommandManager
cmdmgr = CommandManager(loop=aioloop)
cmdmgr.resources.update(aioloop=aioloop,
                        srvapi=srvapi,
                        cfg=cfg,
                        helpmgr=helpmgr)
helpmgr.commands = cmdmgr
cmdmgr.load_cmds_from_module(
    'stig.commands.cli', 'stig.commands.tui',
)


def run():
    from .commands.guess_ui import (guess_ui, UIGuessError)
    from . import hooks

    # Read commands from rc file
    rclines = ()
    if not cliargs['norcfile']:
        from .settings import rcfile
        from .settings.defaults import DEFAULT_RCFILE
        try:
            rclines = rcfile.read(cliargs['rcfile'] or DEFAULT_RCFILE)
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
        except UIGuessError as e:
            log.error('Unable to guess user interface')
            log.error('Provide one of these options: --tui/-t or --no-tui/-T')
            sys.exit(1)

    def run_commands():
        for cmdline in rclines:
            success = cmdmgr.run_sync(cmdline, on_error=log.error)
            # Ignored commands return None, which we consider a success here
            # because TUI commands like 'tab' in the rc file should have no
            # effect at all when in CLI mode.
            if success is False:
                return False

        # Exit if CLI commands fail
        if clicmds:
            success = cmdmgr.run_sync(clicmds, on_error=log.error)
            if not success:
                return False
        return True

    # Run commands either in CLI or TUI mode
    if cmdmgr.active_interface == 'cli':
        if not run_commands():
            sys.exit(1)
    elif cmdmgr.active_interface == 'tui':
        from .tui import main as tui
        cmdmgr.resources.update(tui=tui)
        if not tui.run(run_commands):
            sys.exit(1)

    # Terminate any remaining tasks
    tasks = tuple(task for task in asyncio.Task.all_tasks() if not task.done())
    if tasks:
        log.debug('Not all tasks have been properly canceled.')
        for task in tasks:
            log.debug('Terminating leftover task: %r', task)
            task.cancel()
            try:
                aioloop.run_until_complete(asyncio.wait_for(task, timeout=None))
                task.result()
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

    aioloop.run_until_complete(srvapi.rpc.disconnect('Quit'))
    aioloop.close()
