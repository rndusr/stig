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
Create and manage commands

Commands can be created anywhere by defining a class with metaclass set to
InitCommand.

>>> class MyCommand(metaclass=InitCommand):
>>>     ...

Every command class must have a 'run' method, which is called when the command
is executed. It can be a coroutine function or a normal, synchronous function.
The command's arguments are passed to 'run' as keywords.

The return value of the 'run' method is ignored.  It must raise CmdError on
failure.  The argument to CmdError is used as the error message.  It may also
print errors via its 'error' method or informational messages via its 'info'
method.

If a command executes multiple actions (e.g. pausing two torrents) and any of
those actions fails, it should be a failure (e.g. first torrent was paused,
second torrent does not exist -> return False).

Every command class must have the following class attributes:

    run (callable):            Method that is called when the command runs
    name (string):             Name of the command
    category (string):         Name of the command category (used by `help commands`)
    provides (set of strings): Supported interfaces ('cli' and/or 'tui')
    description (string):      One-line description for command

These class attributes are optional:

    aliases (sequence of strings):   Alternative command names
    argspecs (sequence of mappings): argparse specs for arguments
    usage (sequence of strings):     Syntax string of any arguments (in man pages
                                     this is called SYNOPSIS)
    examples (sequence of strings):  Typical invocations
    more_sections (dict):            Maps additional section names to list of strings or
                                     callables that return lists of strings

Arguments
---------

Each command class gets its own argparser.ArgumentParser instance.  Command
arguments are specified by setting the 'argspecs' class attribute to a
sequence of mappings.  The mappings are then used to create arguments for
ArgumentParser.add_argument.  Most items are passed on unmodified, but there
are exceptions:

- 'names' must be set to a string or a sequence of strings that is passed on
  as the positional arguments to add_argument.  The first string is used as
  the keyword when providing the argument to the run method.

- 'description' must be set to a string that describes what the argument does.

- 'nargs' can be the string 'REMAINDER', which is replaced with the value of
  argparse.REMAINDER.

Resources
---------

Resources are objects that are provided to the CommandManager instance as
key-value pairs which sets them as attributes for command classes that want
them.  For example, the global client API instance 'srvapi' is a resource.

Command classes can request resources by setting a class attribute to
ExpectedResource.  If the CommandManager instance has a resource by this name,
it will be replaced by InitCommand and commands can use it like any regular
class attribute.  If the resource does not exist, accessing it raises an
AttributeError.
"""

from ..logging import make_logger
log = make_logger(__name__)

import asyncio
import argparse
import shlex
from inspect import getmembers
from importlib import import_module
from collections import abc
from .utils import CallbackDict
import sys


def ExpectedResource(name):
    def _raise(self):
        raise AttributeError('{} misses expected resource: {}'.format(type(self).__name__, name))
    return property(fget=_raise)


OPS_AND = ('&', 'and')
OPS_OR  = ('|', 'or')
OPS_SEQ = (';', 'also')

def is_op(string):
    return any(string in ops for ops in (OPS_SEQ, OPS_AND, OPS_OR))


class CmdError(Exception): pass
class CmdArgError(CmdError): pass
class CmdNotFoundError(CmdError): pass


class StayAliveArgParser(argparse.ArgumentParser):
    """Capture errors instead of printing them on stderr and exiting"""
    def exit(self, status=0, message=None):
        if message is not None:
            self.error(message)

    def error(self, message):
        raise CmdArgError(message[0].upper() + message[1:])


def iscmdcls(obj):
    """Whether `obj` is a command class"""
    return isinstance(obj, type) and \
        obj is not _CommandBase and \
        issubclass(obj, _CommandBase)


_MANDATORY_CMD_ATTRS = ('name', 'category', 'provides', 'description', 'run')
_OPTIONAL_CMD_ATTRS = {
    'aliases': (), 'usage': (), 'examples': (), 'argspecs': (), 'more_sections': {}
}
def InitCommand(clsname, bases, attrs):
    """
    Class factory that inits all commands

    This takes care of inheritance, complains about missing mandatory class
    attributes, adds defaults for optional class attributes, etc.
    """
    # Make sure all mandatory attributes are there
    for attr in _MANDATORY_CMD_ATTRS:
        if attr not in attrs:
            raise RuntimeError('{} misses mandatory attribute: {!r}'
                               .format(clsname, attr))

    # Add defaults for optional attributes
    for k,v in _OPTIONAL_CMD_ATTRS.items():
        if k not in attrs:
            attrs[k] = v

    # Turn ExpectedResource into a property that raises an exception if not
    # provided by CommandManager
    for k,v in attrs.items():
        if v is ExpectedResource:
            attrs[k] = ExpectedResource(k)

    # 'names' attribute
    attrs['names'] = list(attrs['aliases'])
    attrs['names'].insert(0, attrs['name'])

    # Create argument parser
    argp = StayAliveArgParser(prog=attrs['name'], add_help=False)
    for argspec in attrs['argspecs']:
        # Check if all mandatory keys are in the spec
        for mandatory_key in ('names',):
            if mandatory_key not in argspec:
                raise RuntimeError('Missing key {!r} in argument spec: {}'
                                   .format(mandatory_key, argspec))

        # Create a copy of argspec so we don't alter the original class
        # attribute and remove all items that ArgParser doesn't understand
        argspec = argspec.copy()
        if 'description' in argspec:
            argspec.pop('description')
        if 'default_description' in argspec:
            argspec.pop('default_description')
        if 'document_default' in argspec:
            argspec.pop('document_default')

        # Assemble arg names
        argnames = argspec.pop('names', None)
        if not isinstance(argnames, abc.Sequence):
            argnames = (argnames,)

        # Translate string to argparse constant
        if 'nargs' in argspec and argspec['nargs'] == 'REMAINDER':
            argspec['nargs'] = argparse.REMAINDER

        # Create new argparser
        argp.add_argument(*argnames, **argspec)
    attrs['_argparser'] = argp

    # Command class must inherit from _CommandBase
    if _CommandBase not in bases:
        bases = (_CommandBase,) + bases

    cls = type(clsname, bases, attrs)
    return cls


class _CommandBase():
    """Base for all command classes"""
    def __init__(self, args=(), info_handler=None, error_handler=None, loop=None, **kwargs):
        self._loop = loop
        self._args = args
        for k,v in kwargs.items():
            setattr(self, k, v)
        self._info_handler = info_handler or (lambda msg: print(msg, file=sys.stdout))
        self._error_handler = error_handler or (lambda msg: print(msg, file=sys.stderr))
        self._task = None
        self._success = None
        self._is_async = False

        try:
            args_parsed = self._argparser.parse_args(args)
        except CmdArgError as e:
            self._finish(exception=e)
        else:
            # Create keyword args for run() method
            kwargs = {}
            for argspec in self.argspecs:
                # First name is the kwarg for run()
                key = argspec['names'][0].lstrip('-').replace('-', '_')
                value = getattr(args_parsed, key)
                kwargs[key.replace(' ', '_')] = value
            self._args = kwargs

            if asyncio.iscoroutinefunction(self.run):
                log.debug('Running async command: %r', self)
                self._is_async = True
                self._task = self.loop.create_task(self.run(**kwargs))
                self._task.add_done_callback(lambda task: self._catch_exceptions(task.result))
            else:
                log.debug('Running sync command: %r', self)
                self._is_async = False
                self._catch_exceptions(self.run, **kwargs)

    def _catch_exceptions(self, callabee, *args, **kwargs):
        try:
            callabee(*args, **kwargs)
        except Exception as e:
            self._finish(exception=e)
        else:
            self._finish()

    def _finish(self, exception=None):
        if not self.finished:
            log.debug('Finishing %s', self)
            self._success = not bool(exception)
            if isinstance(exception, CmdError):
                exc_str = str(exception)
                if exc_str:
                    self.error(exc_str)

        if exception and not isinstance(exception, CmdError):
            raise exception

    def wait_sync(self):
        """
        Wait synchronously until this command has finished

        This uses the run_until_complete() method, so the loop must not be
        running or closed.
        """
        if not self.finished:
            if self.loop.is_closed():
                raise RuntimeError('AsyncIO loop is closed - cannot wait for {!r}'.format(self))
            elif self.loop.is_running():
                raise RuntimeError('AsyncIO loop is running - cannot wait for {!r}'.format(self))
            else:
                log.debug('Waiting until finished: %r', self)
                self._catch_exceptions(self.loop.run_until_complete, self._task)

    async def wait_async(self):
        """Wait asynchronously until this command has finished"""
        if not self.finished:
            log.debug('Waiting until finished: %r', self)
            try:
                await self._task
            except Exception as e:
                self._finish(exception=e)
            else:
                self._finish()

    def info(self, msg):
        """Show info message (use this as your stdout)"""
        self._info_handler('%s: %s' % (self.name, msg))

    def error(self, msg):
        """Show error message (use this as your stderr)"""
        self._error_handler('%s: %s' % (self.name, msg))

    @property
    def loop(self):
        """AsyncIO loop"""
        if self._loop is None:
            raise RuntimeError('Called with missing asyncio loop: {!r}'.format(self))
        else:
            return self._loop

    @property
    def success(self):
        """True/False if command has finished, None otherwise"""
        return self._success

    @property
    def finished(self):
        """Whether command has finished"""
        return self._success is not None

    @property
    def is_async(self):
        """Whether this command runs asynchronously"""
        return self._is_async

    def __repr__(self):
        if isinstance(self._args, abc.Sequence):
            argstr = ', '.join(repr(arg) for arg in self._args)
        elif isinstance(self._args, abc.Mapping):
            argstr = ', '.join('%s=%r' % (k,v)
                                for k,v in self._args.items())
        provides = '/'.join(interface for interface in self.provides)
        string = '<Command [{}] {}({})'.format(provides, self.name, argstr)
        if self.finished:
            string += ' success={}'.format(self.success)
        else:
            string += ' running'
        return string + '>'


class CommandManager():
    def __init__(self, loop=None, pre_run_hook=None, info_handler=None, error_handler=None):
        self.loop = loop if loop is not None else asyncio.get_event_loop()
        self._info_handler = info_handler
        self._error_handler = error_handler
        self.pre_run_hook = pre_run_hook
        self._cmds = {}
        self._active_interface = None
        self._resources = CallbackDict(callback=self._update_resources)
        self._resources.update(cmdmgr=self)

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

        Command classes must have set metaclass=InitCommand.
        """
        for modname in modules:
            log.debug('Looking for commands in %s', modname)
            mod = import_module(modname)
            for member in getmembers(mod):
                cmdcls = member[1]
                if iscmdcls(cmdcls):
                    self.register(cmdcls)

    def register(self, cmdcls):
        """
        Add new command

        cmdcls: command class (must have InitCommand as metaclass)
        """
        if not issubclass(cmdcls, _CommandBase):
            raise RuntimeError("{} must have InitCommand as metaclass".format(cmdcls))
        elif not cmdcls.provides:
            raise RuntimeError('{} does not provide any interfaces'.format(cmdcls))

        self._provide_resources_to_cmdcls(cmdcls)

        # Store cmdcls for each of its supported interfaces
        for interface in cmdcls.provides:
            if interface not in self._cmds:
                self._cmds[interface] = {}
            log.debug('Registered %s command %s (%s)',
                      interface, cmdcls.name, type(cmdcls).__name__)
            self._cmds[interface][cmdcls.name] = cmdcls

    @property
    def resources(self):
        return self._resources

    def _update_resources(self):
        for cmdcls in self.all_commands:
            self._provide_resources_to_cmdcls(cmdcls)

    def _provide_resources_to_cmdcls(self, cmdcls):
        for name,obj in self._resources.items():
            if hasattr(cmdcls, name):
                setattr(cmdcls, name, obj)

    @property
    def active_interface(self):
        return self._active_interface

    @active_interface.setter
    def active_interface(self, interface):
        if interface in self._cmds:
            self._active_interface = interface
        else:
            raise ValueError('No commands for interface {!r} registered'.format(interface))

    @property
    def active_commands(self):
        """Tuple of commands for the active interface or all commands with no active interface"""
        if self._active_interface is None:
            return self.all_commands
        else:
            return tuple(self._cmds[self._active_interface].values())

    @property
    def all_commands(self):
        """Tuple of all commands for all interfaces"""
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

    def run_task(self, commands, **kwargs):
        """Return Task that runs `run_async`"""
        log.debug('Creating command chain task: %r', commands)
        return self.loop.create_task(self.run_async(commands, **kwargs))

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
                elif is_op(item):
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
            cmdchain = [str(item) if is_op(item) else list(item)
                        for item in commands]
            log.debug('turned %r into %r', commands, cmdchain)

        for item in cmdchain:
            self._validate_cmdchain_item(item)

        if cmdchain and is_op(cmdchain[-1]):
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
            cmdname = cmdline.pop(0)
        except IndexError:
            # cmdline is empty
            return self._dummy_process(cmdname=None)
        cmdargs = cmdline
        cmdcls = self.get_cmdcls(cmdname, interface='ACTIVE')
        if cmdcls is None:
            if self.get_cmdcls(cmdname, interface='ANY') is not None:
                # Command exists but not in active interface - we ignore it
                log.debug('Ignoring inactive command: %s', cmdname)
                process = self._dummy_process(cmdname)
            else:
                exc = CmdNotFoundError('Unknown command')
                process = self._dummy_process(cmdname, exception=exc)
        elif cmdcls not in self.active_commands:
            exc = CmdError('%s: No support for %s interface' % (cmdname, self._active_interface))
            process = self._dummy_process(cmdname, exception=exc)
        else:
            process = cmdcls(cmdargs, loop=self.loop,
                             info_handler=self._info_handler,
                             error_handler=self._error_handler,
                             **kwargs)
        return process

    def _validate_cmdchain_item(self, item):
        # item must be operator or a command line in list form
        if not (is_op(item) or (isinstance(item, abc.Sequence) and not isinstance(item, str) and
                                all(isinstance(arg, str) for arg in item))):
            raise RuntimeError('Invalid type for command chain item: %r' % (item,))

        # Test if item is an operator after another operator
        try:
            prev_item = self._prev_validation_item
        except AttributeError:
            prev_item = None
        self._prev_validation_item = item
        if is_op(prev_item) and is_op(item):
            raise ValueError('Consecutive operators: %s %s' % (prev_item, item))

    def _dummy_process(self, cmdname, exception=None, info=None):
        """
        Create new _CommandBase-derived class and return an instance of it

        This is useful, for example, for unknown commands, which can still be
        used in chains as a dummy process, e.g. "invalidcommand | validcommand"
        runs "validcommand" because "invalidcommand" fails.
        """
        class DummyCommand(metaclass=InitCommand):
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

        return DummyCommand((), loop=self.loop,
                            info_handler=self._info_handler,
                            error_handler=self._error_handler)
