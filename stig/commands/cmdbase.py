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

import argparse
import asyncio
import sys
from collections import abc

from ..completion import Candidate, Candidates
from ..utils import cliparser
from .cmderror import CmdArgError, CmdError

from ..logging import make_logger  # isort:skip
log = make_logger(__name__)


class StayAliveArgParser(argparse.ArgumentParser):
    """Capture errors instead of printing them on stderr and exiting"""
    def exit(self, status=0, message=None):
        if message is not None:
            self.error(message)

    def error(self, message):
        raise CmdArgError(message[0].upper() + message[1:])


_MANDATORY_CMD_ATTRS = ('name', 'category', 'provides', 'description', 'run')
_OPTIONAL_CMD_ATTRS = {
    'aliases': (), 'usage': (), 'examples': (), 'argspecs': (), 'more_sections': {}
}
def CommandMeta(clsname, bases, attrs):
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

    # 'names' attribute
    attrs['names'] = list(attrs['aliases'])
    attrs['names'].insert(0, attrs['name'])

    # Options are arguments that start with '-'
    # Map '--option' to ('-o', '-p', '-t')
    attrs['long_options'] = {name:argspec['names'][1:]
                             for argspec in attrs['argspecs']
                             for name in argspec['names']
                             if name.startswith('--')}
    # Map '-o' to '--option'
    attrs['short_options'] = {name:argspec['names'][0]
                              for argspec in attrs['argspecs']
                              for name in argspec['names']
                              if name.startswith('-') and not name[1:].startswith('-')}

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
        bases = (_CommandBase, _CompletionCandidatesMixin) + bases

    cls = type(clsname, bases, attrs)
    return cls


class _CommandBase():
    """
    Base for all command classes

    args: Any arguments for this command
    argv: Command line as given by user, including command name, as sequence
    info_handler: Function that is called with info messages via the info() method
    error_handler: Function that is called with error messages via the error() method

    Any remaining keyword arguments are made available as instance attributes.
    """
    def __init__(self, args=(), argv=(), info_handler=None, error_handler=None, **kwargs):
        # Store the command that invoked this instance
        self._command = ' '.join((cliparser.quote(arg) for arg in argv))
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
                self._task = asyncio.ensure_future(self.run(**kwargs))
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
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError('AsyncIO loop is closed - cannot wait for {!r}'.format(self))
            elif loop.is_running():
                raise RuntimeError('AsyncIO loop is running - cannot wait for {!r}'.format(self))
            else:
                log.debug('Waiting until finished: %r', self)
                self._catch_exceptions(loop.run_until_complete, self._task)

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

    @property
    def command(self):
        """Invoking command as string"""
        return self._command

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


class _CompletionCandidatesMixin():
    """
    Mixin class that provides class methods for generating tab completion
    candidates
    """

    @classmethod
    def _is_option(cls, arg):
        return arg in cls.long_options or arg in cls.short_options

    @classmethod
    def _get_argspec(cls, name):
        for argspec in cls.argspecs:
            if any(name == n for n in argspec['names']):
                return argspec

    @classmethod
    def _option_wants_arg(cls, option, roffset):
        argspec = cls._get_argspec(option)
        nargs = argspec.get('nargs', 1)
        if nargs in ('+', '*', 'REMAINDER'):
            return True
        elif nargs == '?':
            nargs = 1
        if roffset < nargs:
            return True
        return False

    @classmethod
    def completion_candidates_opts(cls, args):
        """
        Return candidates for arguments that start with "-"

        The default implementation should work for all commands and it shouldn't
        be necessary for subclasses to override this method.
        """
        # '--' turns all arguments to the right into positional arguments
        if '--' not in args.before_curarg:
            if args.curarg.startswith('-'):
                log.debug('Completing long options: %r', cls.long_options)
                # Remove any options from candidates that are already in `args`
                options = tuple(opt for opt in cls.long_options if opt not in args)
                if options:
                    cands = (Candidate(cand,
                                       in_parens=', '.join(cls.long_options[cand]),
                                       description=cls._get_argspec(cand)['description'])
                             for cand in options)
                    return Candidates(cands, label='%s option' % cls.name)

            # Check if any argument left of the current argument is an option that
            # wants another parameter
            for i,arg in enumerate(reversed(args.before_curarg)):
                if cls._is_option(arg) and cls._option_wants_arg(option=arg, roffset=i):
                    option_name = cls.short_options.get(arg, arg)
                    log.debug('Completing parameters for %r', option_name)
                    return cls.completion_candidates_params(option_name, args)

    @classmethod
    def completion_candidates_params(cls, option_name, args):
        """
        Return candidates for arguments to an option (e.g. --option parameter)

        The default implementation returns None.
        """
        pass

    @classmethod
    def completion_candidates_posargs(cls, args):
        """
        Return candidates that are not options and not parameters

        The default implementation returns None.
        """
        pass

    @classmethod
    def completion_candidates(cls, args):
        """
        Return appropriate completion candidates

        The default implementation calls the methods described above and returns
        the first return value that evaluates to True (i.e. non-empty and
        non-None).
        """
        # completion_candidates_params() is called by completion_candidates_opts
        # if appropriate.
        cands = cls.completion_candidates_opts(args)
        log.debug('Completion candidates for options: %r', cands)
        if cands:
            return cands
        cands = cls.completion_candidates_posargs(args)
        log.debug('Completion candidates for positional arguments: %r', cands)
        return cands
