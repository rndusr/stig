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

# Remove python from process name when running inside tmux
import os
if 'TMUX' in os.environ:
    try:
        from setproctitle import setproctitle
    except ImportError:
        pass
    else:
        from . import __appname__
        setproctitle(__appname__)


import sys
import asyncio
aioloop = asyncio.get_event_loop()


from . import cliopts
cliargs, clicmds = cliopts.parse()


from . import logging
logging.setup(debugmods=cliargs['debug'], filepath=cliargs['debug_file'])
logging.redirect_level('INFO', sys.stdout)
log = logging.make_logger(__name__)


from . import settings
localcfg = settings.Settings()
settings.init_defaults(localcfg)


from .helpmgr import HelpManager
helpmgr = HelpManager()
helpmgr.localcfg = localcfg


from .client import API
srvapi = API(host=localcfg['connect.host'],
             port=localcfg['connect.port'],
             path=localcfg['connect.path'],
             user=localcfg['connect.user'],
             password=localcfg['connect.password'],
             tls=localcfg['connect.tls'],
             interval=localcfg['tui.poll'],
             loop=aioloop)
remotecfg = srvapi.settings
helpmgr.remotecfg = remotecfg


from .client import geoip
if geoip.available:
    geoip.cachedir = localcfg['geoip.dir']
else:
    localcfg['geoip'] = False
geoip.enabled = localcfg['geoip']


from .commands import CommandManager
cmdmgr = CommandManager(loop=aioloop,
                        info_handler=lambda msg: log.info(msg),
                        error_handler=lambda msg: log.error(msg))
cmdmgr.resources.update(aioloop=aioloop,
                        srvapi=srvapi,
                        cfg=localcfg,
                        srvcfg=srvapi.settings,
                        helpmgr=helpmgr)
cmdmgr.load_cmds_from_module(
    'stig.commands.cli', 'stig.commands.tui',
)
helpmgr.cmdmgr = cmdmgr


def _pre_run_hook(cmdline):
    # Change command before it is executed

    # If there is '-h' or '--help' in the arguments, replace it with 'help
    # <cmd>'.  This is dirty but easier than forcing argparse to ignore all
    # other arguments without calling sys.exit().
    if '-h' in cmdline or '--help' in cmdline:
        cmdcls = cmdmgr.get_cmdcls(cmdline[0], interface='ANY')
        if cmdcls is not None:
            if cmdcls.name != 'tab':
                return ['help', cmdcls.name]
            else:
                # 'tab ls -h' is a little trickier because both 'tab' and 'ls'
                # can have arbitrary additional arguments which we must remove.
                #
                # Find first argument to 'tab' that is also a valid command
                # name.  Preserve all arguments before that.
                tab_args = []
                for arg in cmdline[1:]:
                    if cmdmgr.get_cmdcls(arg, interface='ANY') is not None:
                        return ['tab'] + tab_args + ['help', arg]
                    else:
                        tab_args.append(arg)
                return ['help', 'tab']
    return cmdline
cmdmgr.pre_run_hook = _pre_run_hook



def run():
    from .commands.guess_ui import (guess_ui, UIGuessError)
    from .commands import CmdError
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

        # Load geoip database
        if localcfg['geoip']:
            try:
                aioloop.run_until_complete(geoip.load(loop=aioloop))
            except geoip.GeoIPError as e:
                log.error(e)
                exit_code = 1

        try:
            if not run_commands():
                exit_code = 1
        except KeyboardInterrupt:
            log.debug('Caught SIGINT')

    elif cmdmgr.active_interface == 'tui':
        from .tui import main as tui
        cmdmgr.resources.update(tui=tui)
        if not tui.run(run_commands):
            exit_code = 1

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

    _cancel_unfinished_tasks()
    aioloop.run_until_complete(srvapi.rpc.disconnect('Quit'))
    # # Closing the event loop raises "RuntimeError: Event loop is closed" (not
    # # always) when a `run_in_executor` command (i.e. a thread) is cancelled.
    # # https://github.com/python/asyncio/issues/258
    # aioloop.close()
    sys.exit(exit_code)


def _cancel_unfinished_tasks():
    pending = (task for task in asyncio.Task.all_tasks() if not task.done())
    for task in pending:
        log.debug('Cancelling pending task: %r', task)
        task.cancel()
        try:
            log.debug('Finishing pending task: %r', task)
            aioloop.run_until_complete(task)
        except asyncio.CancelledError:
            pass
