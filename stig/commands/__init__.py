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

"""Create and manage commands

Commands can be created anywhere by defining a class with metaclass set to
InitCommand.

>>> class MyCommand(metaclass=InitComand):
>>>     ...

Every command class must have a 'run' method, which is called when the command
is executed. It can be a coroutine function or a normal, synchronous function.
The command's arguments are passed to 'run' as keywords.

The 'run' method should return True on success and False on failure.  It may
also raise CmdError.  If False is returned, it is assumed that any errors have
already been reported (i.e. logged to the ERROR level).

If a command executes multiple actions (e.g. pausing two torrents) and any of
those actions fails, it should be a failure (e.g. first torrent was paused,
second torrent does not exist -> return False).

Every command class must have the following class attributes:

    run (callable):            Method that is called when the command runs
    name (string):             Name of the command
    category (string):         Name of the category (used only for `help commands`)
    provides (set of strings): Supported interfaces ('cli' and/or 'tui')
    description (string):      One-line description for command

These class attributes are optional:

    aliases (sequence of strings):   Alternative names
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

- 'description' must be set to a string that describes what the command does.

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


def ExpectedResource(name):
    def _raise(self):
        raise AttributeError('{} misses expected resource: {}'.format(type(self).__name__, name))
    return property(fget=_raise)


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
    """Class factory that inits all commands

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
    argp = StayAliveArgParser()
    for argspec in attrs['argspecs']:
        # Check if all mandatory keys are in the spec
        for mandatory_key in ('names', 'description'):
            if mandatory_key not in argspec:
                raise RuntimeError('Missing key {!r} in argument spec: {}'
                                   .format(mandatory_key, argspec))

        # Create a copy of the spec for this arg and remove all items that
        # ArgParser doesn't understand
        argspec = argspec.copy()
        argspec.pop('description')
        if 'default_description' in argspec:
            argspec.pop('default_description')

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
    """Base for all commands classes"""
    def __init__(self, args=(), on_success=None, on_error=None, loop=None, **kwargs):
        for k,v in kwargs.items():
            setattr(self, k, v)
        self._loop = loop
        self._args = args
        self.on_success = on_success
        self.on_error = on_error
        self._task = None
        self._success = None
        self._exc = None
        self._exc_fetched = False

        try:
            args_parsed = self._argparser.parse_args(args)
        except CmdArgError as e:
            self._finish(success=False,
                         exception=CmdArgError('{}: {}'.format(self.name, e)))
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
                self._task = self.loop.create_task(self.run(**kwargs))
                self._task.add_done_callback(lambda task: self._catch_exceptions(task.result))
            else:
                log.debug('Running sync command: %r', self)
                self._catch_exceptions(self.run, **kwargs)

    def _catch_exceptions(self, callabee, *args, **kwargs):
        try:
            success = callabee(*args, **kwargs)
        except Exception as e:
            success = False
            exc = e
        else:
            exc = None

        if success:
            self._finish(success=True)
        else:
            if exc is None:
                exc = CmdError()
            self._finish(success=False, exception=exc)

    def _finish(self, success, exception=None):
        if self.finished:
            return  # _finish() was already called

        self._success = success
        self._exc = exception

        if success:
            log.debug('%r succeeded', self)
            if self.on_success is not None:
                log.debug('Calling success callback: %r', self.on_success)
                self.on_success(self)
        else:
            log.debug('%r failed: exception=%r', self, exception)
            if self.on_error is not None:
                log.debug('Calling error callback: %r', self.on_error)
                self.on_error(self.exception)

    def wait(self):
        """Wait synchronously until asynchronous command has finished

        Raises RuntimeError if loop is closed or running.
        """
        if not self.finished:
            if self.loop.is_closed():
                raise RuntimeError('AsyncIO loop is closed - cannot wait for {!r}'.format(self))
            elif self.loop.is_running():
                raise RuntimeError('AsyncIO loop is running - cannot wait for {!r}'.format(self))
            else:
                log.debug('Waiting until finished: %r', self)
                self._catch_exceptions(self.loop.run_until_complete, self._task)

    def __del__(self):
        """Raise stored, unraised exception"""
        exc = self.exception
        if exc and not self._exc_fetched:
            raise exc

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
    def exception(self):
        """Exception if command raised one, None otherwise"""
        # If this class is called with wrong arguments, __del__ is called
        # befire _exc exists.
        if hasattr(self, '_exc'):
            self._exc_fetched = True
            return self._exc

    @property
    def finished(self):
        """Whether command has finished"""
        return self._success is not None

    @property
    def task(self):
        """The Task instance of a running async command (run method is async)"""
        return self._task

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
    def __init__(self, loop=None):
        self.loop = loop if loop is not None else asyncio.get_event_loop()
        self._cmds = {}
        self._active_interface = None
        self._resources = CallbackDict(callback=self._update_resources)
        from . import utils
        self._resources.update(cmdmgr=self)

    def load_cmds_from_module(self, *modules):
        """Import modules and look for command classes

        Command classes must have set metaclass=InitCommand.
        """
        for modname in modules:
            log.debug('Looking for commands in %s', modname)
            mod = import_module(modname)
            for member in getmembers(mod):
                cmdcls = member[1]
                # We're interested in classes that inherit from _CommandBase
                # but are not _CommandBase.
                if iscmdcls(cmdcls):
                    self.register(cmdcls)

    def register(self, cmdcls):
        """Add new command

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
        """Resolve command name `cmdname` to command class

        If `interface` is 'ACTIVE', return command class from
        `active_commands`.

        If `interface` is 'ANY', return command class from `all_commands`.

        If `interface` is anything else, it must be an existing interface and
        only a command that supports it is returned.

        If `exclusive` evaluates to True, the returned command class does not
        support any other interfaces.

        Returns None if not matching command class is registered.
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

    # TODO: With command chains, 'command' argument should be 'cmdchain' and
    # be a string or a list of arguments.
    def __call__(self, command, block=False, on_error=None, **kwargs):
        """Run `command`, return its return value

        command: Command name and any arguments as a sequence or string
        block: Whether to return immediately or wait for command to finish; if
               enabled, the asyncio event loop must be stopped and not closed
        on_error: Callable that gets any CmdErrors

        Any other keyword arguments are forwarded to the command instance
        which makes them available as attributes so the 'run' method can
        access them via 'self'.

        Any exceptions from the command are re-raised, except CmdErrors if
        `on_error` is not None.

        Returns True if the command succeeded, False if it failed, and None if
        it is async and `block` is False.
        """
        def handle_exc(exc):
            if on_error is not None and isinstance(exc, CmdError):
                if exc.args:
                    # exc.args is () if cmd didn't raise any exception but
                    # returned False.  In that case, we assume the error(s)
                    # were already reported by the cmd itself.
                    log.debug('Calling %r with %r', on_error, exc)
                    on_error(exc)
            else:
                log.debug('Re-raising %r', exc)
                raise exc

        process = self.run(command, on_error=handle_exc, **kwargs)
        if process is None:
            return False  # CmdNotFoundError was handled by handle_exc()
        else:
            if block:
                process.wait()
                if process.exception is not None and on_error is None:
                    raise process.exception
            return process.success

    def run(self, command, on_success=None, on_error=None, **kwargs):
        """Run `command`, return its instance"""
        # TODO: Once command chaining is implemented:
        #       - _split_cmds() method takes flat sequence and returns tuple
        #         of command tuples with [;|&] between.
        #       - New method _run_cmd_chain() takes return value of
        #         _split_cmds() and walks through the commands with
        #         _run_single_cmd().
        return self._run_single_cmd(command, on_success=on_success,
                                    on_error=on_error, **kwargs)

    def _run_single_cmd(self, command, on_success=None, on_error=None, **kwargs):
        """Call one command and return its instance or None if command not found"""
        try:
            cmd, cmdargs = self._split_cmd(command)
        except CmdError as e:
            # 'Unknown command' or 'No support for ... interface'
            if on_error is not None:
                on_error(e)
            else:
                raise
        else:
            return cmd(cmdargs, loop=self.loop, on_success=on_success, on_error=on_error, **kwargs)

    def _split_cmd(self, command):
        if isinstance(command, str):
            command = shlex.split(command)
        elif not isinstance(command, abc.Sequence):
            raise TypeError('comand must be string or sequence, not {}: {!r}'
                            .format(type(command).__name__, command))
        cmdname = command[0]
        cmdargs = command[1:]
        cmd = self.get_cmdcls(cmdname, interface='ACTIVE')
        if cmd is None:
            raise CmdNotFoundError('Unknown command: {}'.format(cmdname))
        elif cmd not in self.active_commands:
            raise CmdError('{}: No support for {} interface'
                           .format(cmdname, self._active_interface))
        else:
            return cmd, cmdargs
