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
CommandMeta.

>>> class MyCommand(metaclass=CommandMeta):
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
second torrent does not exist, third torrent was paused -> return False because
of second torrent).

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
"""

# flake8: noqa

OPS_AND = ('&', 'and')
OPS_OR  = ('|', 'or')
OPS_SEQ = (';', 'also')
OPS = OPS_AND + OPS_OR + OPS_SEQ

from .cmdbase import CommandMeta, _CommandBase
from .cmderror import *
from .cmdmanager import CommandManager
from .utils import is_cmdcls, is_op
