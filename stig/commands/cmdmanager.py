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
import shlex
from collections import abc
from contextlib import contextmanager
from importlib import import_module
from inspect import getmembers

from . import OPS_AND, OPS_OR, OPS_SEQ, _CommandBase, utils
from .cmdbase import CommandMeta
from .cmderror import CmdError, CmdNotFoundError

from ..logging import make_logger  # isort:skip
log = make_logger(__name__)


class CommandManager():
    def __init__(self, pre_run_hook=None, info_handler=None, error_handler=None):
        self._info_handler = info_handler
        self._error_handler = error_handler
        self.pre_run_hook = pre_run_hook
        self._cmds = {}
        self._active_interface = None
        self._ignored_calls = []

    @property
    def info_handler(self):
        return self._info_handler

    @info_handler.setter
    def info_handler(self, callback):
        assert callback is None or callable(callback), 'Not a callable: %r' % callback
        self._info_handler = callback

    @property
    def error_handler(self):
        return self._error_handler

    @error_handler.setter
    def error_handler(self, callback):
        assert callback is None or callable(callback), 'Not a callable: %r' % callback
        self._error_handler = callback

    def load_cmds_from_module(self, *modules):
        """
        Import modules and look for command classes

        Command classes must have set metaclass=CommandMeta.
        """
        for modname in modules:
            log.debug('Looking for commands in %s', modname)
            mod = import_module(modname)
            for member in getmembers(mod):
                cmdcls = member[1]
                if utils.is_cmdcls(cmdcls):
                    self.register(cmdcls)

    def register(self, cmdcls):
        """
        Add new command

        cmdcls: command class (must have CommandMeta as metaclass)
        """
        if not issubclass(cmdcls, _CommandBase):
            raise RuntimeError("{} must have CommandMeta as metaclass".format(cmdcls))
        elif not cmdcls.provides:
            raise RuntimeError('{} does not provide any interfaces'.format(cmdcls))

        # Store cmdcls for each of its supported interfaces
        for interface in cmdcls.provides:
            if interface not in self._cmds:
                self._cmds[interface] = {}
            log.debug('Registered %s command %s (%s)',
                      interface, cmdcls.name, type(cmdcls).__name__)
            self._cmds[interface][cmdcls.name] = cmdcls

    @property
    def active_interface(self):
        return self._active_interface

    @active_interface.setter
    def active_interface(self, interface):
        if interface in self._cmds or interface is None:
            self._active_interface = interface
        else:
            raise ValueError('No commands for interface {!r} registered'.format(interface))

    @contextmanager
    def temporary_active_interface(self, interface):
        """Context manager that temporarily changes the active interface"""
        orig_interface = self.active_interface
        self.active_interface = interface
        log.debug('Activating temporary interface %r', interface)
        yield
        log.debug('Deactivating temporary interface %r', interface)
        self.active_interface = orig_interface

    @property
    def active_commands(self):
        """
        Tuple of command classes for the active interface or all commands if no
        active interface is specified
        """
        if self._active_interface is None:
            return self.all_commands
        else:
            return tuple(self._cmds[self._active_interface].values())

    @property
    def all_commands(self):
        """Tuple of all command classes for all interfaces"""
        cmds = set()
        for interface,cmdnames in self._cmds.items():
            for cmdname in cmdnames:
                cmds.add(self._cmds[interface][cmdname])
        return tuple(cmds)

    def get_cmdcls(self, cmdname, interface='ACTIVE', exclusive=False):
        """
        Resolve command name `cmdname` to command class

        If `interface` is 'ACTIVE', return command class from
        `active_commands`.

        If `interface` is 'ANY', return command class from `all_commands`.

        If `interface` is anything else, it must be an existing interface and
        only a command that supports it is returned.

        If `exclusive` evaluates to True, the returned command class does not
        support any other interfaces.

        Returns None if no matching command class is registered.
        """
        if interface == 'ACTIVE':
            cmdpool = self.active_commands
        elif interface == 'ANY':
            cmdpool = self.all_commands
        elif isinstance(interface, abc.Hashable):
            try:
                cmdpool = tuple(self._cmds[interface].values())
            except KeyError:
                raise ValueError('Unknown interface: {!r}'.format(interface))
        else:
            raise RuntimeError('Interface type must be hashable: {!r}'.format(interface))

        for cmd in cmdpool:
            if cmdname in cmd.names:
                if not exclusive:
                    return cmd
                elif cmd.provides == (interface,):
                    return cmd

    def __getitem__(self, cmdname):
        cmd = self.get_cmdcls(cmdname, interface='ANY')
        if cmd is not None:
            return cmd
        else:
            raise KeyError(cmdname)

    def __contains__(self, cmdname):
        return self.get_cmdcls(cmdname, interface='ANY') is not None

    @property
    def categories(self):
        """Tuple of command categories built from commands' `category` attributes"""
        categories = set()
        for cmd in self.all_commands:
            categories.add(cmd.category)
        return tuple(sorted(categories))

    def _handle_final_process(self, process):
        if process.success in (True, None):
            return True
        return False

    def run_sync(self, commands, **kwargs):
        """
        Run `commands`, return boolean result

        Use this method in non-async code. The asyncio loop must be not running
        and not closed.

        command: See `split_cmdchain`

        Any other keyword arguments are forwarded to the command instance which
        makes them available as attributes so the 'run' method can access them
        via its instance (self).

        Returns True if all `commands` ran successfully, False otherwise.
        """
        log.debug('Running command chain synchronously: %r', commands)
        if not commands:
            return True  # No commands - no error
        for process in self._yield_from_cmdchain(commands, **kwargs):
            if not process.finished:
                process.wait_sync()
        return self._handle_final_process(process)

    async def run_async(self, commands, **kwargs):
        """Same as `run_sync` but in asynchronous contexts"""
        log.debug('Running command chain asynchronously: %r', commands)
        if not commands:
            return True  # No commands - no error
        for process in self._yield_from_cmdchain(commands, **kwargs):
            if not process.finished:
                await process.wait_async()
        return self._handle_final_process(process)

    def run_ignored_calls_sync(self, cmdname=None):
        """
        Execute any calls that were previously ignored because their interface was not active

        cmdname: Only run calls for this command or all calls if None.

        See `temporary_active_interface` for changing the active interface while running
        ignored calls.
        """
        calls_made = False
        success = True
        for call in self._get_ignored_calls(cmdname):
            success = success and self.run_sync(call)
            calls_made = True
        return calls_made and success

    async def run_ignored_calls_async(self, cmdname=None):
        """Asynchronous version of `run_ignored_calls_sync`"""
        calls_made = False
        success = True
        for call in self._get_ignored_calls(cmdname):
            success = success and await self.run_async(call)
            calls_made = True
        return calls_made and success

    def _get_ignored_calls(self, cmdname):
        for call in tuple(self._ignored_calls):
            if cmdname is None or cmdname == call[0][0]:
                yield call
                self._ignored_calls.remove(call)

    def run_task(self, commands, **kwargs):
        """Return Task that runs `run_async`"""
        log.debug('Creating command chain task: %r', commands)
        return asyncio.ensure_future(self.run_async(commands, **kwargs))

    def _yield_from_cmdchain(self, commands, **kwargs):
        try:
            cmdchain = self.split_cmdchain(commands)
        except ValueError as e:
            yield self._dummy_process(cmdname=None, exception=CmdError(e))
        else:
            prev_process_success = True
            for item in cmdchain:
                if item in OPS_AND and not prev_process_success:
                    log.debug('Found operator %s and previous command failed (%r) - aborting', item, prev_process_success)
                    break
                elif item in OPS_OR and prev_process_success:
                    log.debug('Found operator %s and previous command succeeded (%r) - aborting', item, prev_process_success)
                    break
                elif utils.is_op(item):
                    continue
                else:
                    process = self._create_process(item, **kwargs)
                    yield process
                    assert process.finished, 'Not finished: %r' % process
                    prev_process_success = process.success

    def split_cmdchain(self, commands):
        """
        Parse and validate chained commands

        commands: Command line as string or a valid command chain

        A command chain is a sequence of sequences of commands with their
        arguments.  Sub-sequences must be separated by single operators.

        Command operators are characters specified by the variables OPS_AND,
        OPS_OR and OPS_SEQ.  In a string, they must be enclosed by spaces
        (e.g. " & ").

        Example:

        >>> list(cmdmgr.split_cmdchain('do that & act "like this"'))
        [ ['do', 'that'], '&', ['act', 'like this'] ]

        Raise ValueError if `commands` is not valid.
        """
        if not isinstance(commands, abc.Sequence):
            raise RuntimeError('Must be string or sequence, not %r: %r' %
                               (type(commands).__name__, commands))
        elif isinstance(commands, str):
            args = shlex.split(commands)
            cmdchain = []
            cmd = []
            while args:
                arg = args.pop(0)
                if arg in OPS_SEQ:
                    if cmd:
                        cmdchain.append(cmd)
                    cmdchain.append(OPS_SEQ[0])
                    cmd = []
                elif arg in OPS_OR:
                    if cmd:
                        cmdchain.append(cmd)
                    cmdchain.append(OPS_OR[0])
                    cmd = []
                elif arg in OPS_AND:
                    if cmd:
                        cmdchain.append(cmd)
                    cmdchain.append(OPS_AND[0])
                    cmd = []
                else:
                    cmd.append(arg)
            if cmd:
                cmdchain.append(cmd)
        else:
            cmdchain = [str(item) if utils.is_op(item) else list(item)
                        for item in commands]

        for item in cmdchain:
            self._validate_cmdchain_item(item)

        if cmdchain and utils.is_op(cmdchain[-1]):
            cmdchain.pop(-1)

        log.debug('Parsed command chain: %r', cmdchain)
        return cmdchain

    def _create_process(self, cmdline, **kwargs):
        """Call one command and return its instance or None on error"""
        # Make a copy so we can pop from it
        cmdline = list(cmdline)

        if self.pre_run_hook is not None:
            old_cmdline = cmdline.copy()
            cmdline = self.pre_run_hook(cmdline)
            if cmdline != old_cmdline:
                log.debug('Pre-run-hook %r converted %r to %r',
                          self.pre_run_hook.__name__, old_cmdline, cmdline)

        try:
            cmdname = cmdline[0]
        except IndexError:
            # cmdline is empty
            return self._dummy_process(cmdname=None)
        cmdargs = cmdline[1:]
        cmdcls = self.get_cmdcls(cmdname, interface='ACTIVE')
        if cmdcls is None:
            if self.get_cmdcls(cmdname, interface='ANY') is not None:
                # Command exists but not in active interface.  Store it in case we want to
                # run it later and run a fake command so command chains are still working.
                log.debug('Ignoring inactive command: %s', cmdname)
                self._ignored_calls.append(((cmdname,) + tuple(cmdargs),))
                process = self._dummy_process(cmdname)
            else:
                exc = CmdNotFoundError('Unknown command')
                process = self._dummy_process(cmdname, exception=exc)
        elif cmdcls not in self.active_commands:
            exc = CmdError('%s: No support for %s interface' % (cmdname, self._active_interface))
            process = self._dummy_process(cmdname, exception=exc)
        else:
            process = cmdcls(cmdargs,
                             argv=tuple(cmdline),
                             info_handler=self._info_handler,
                             error_handler=self._error_handler,
                             **kwargs)
        return process

    def _validate_cmdchain_item(self, item):
        # item must be operator or a command line in list form
        if not (utils.is_op(item) or (isinstance(item, abc.Sequence) and not isinstance(item, str) and
                                      all(isinstance(arg, str) for arg in item))):
            raise RuntimeError('Invalid type for command chain item: %r' % (item,))

        # Test if item is an operator after another operator
        try:
            prev_item = self._prev_validation_item
        except AttributeError:
            prev_item = None
        self._prev_validation_item = item
        if utils.is_op(prev_item) and utils.is_op(item):
            raise ValueError('Consecutive operators: %s %s' % (prev_item, item))

    def _dummy_process(self, cmdname, exception=None, info=None):
        """
        Create new _CommandBase-derived class and return an instance of it

        This is useful, for example, for unknown commands, which can still be
        used in chains as a dummy process, e.g. "invalidcommand | validcommand"
        runs "validcommand" because "invalidcommand" fails.
        """
        class DummyCommand(metaclass=CommandMeta):
            name = cmdname
            category = 'dummies'
            provides = set()
            description = 'Dummy command'

            def run(self):
                if info:
                    self.info(info)
                if exception:
                    raise exception

            def info(self, msg):
                if self.name is None:
                    self._info_handler(str(msg))
                else:
                    return super().info(msg)

            def error(self, msg):
                if self.name is None:
                    self._error_handler(str(msg))
                else:
                    return super().error(msg)

        return DummyCommand((),
                            info_handler=self._info_handler,
                            error_handler=self._error_handler)
