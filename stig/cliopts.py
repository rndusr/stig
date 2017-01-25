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
from collections import OrderedDict


_parser = argparse.ArgumentParser(add_help=False)
DESCRIPTIONS = OrderedDict()
def _add_arg(*args, section='OPTIONS', description=None, varname=None, **kwargs):
    if description is not None:
        optstr = ','.join(args)
        if varname is not None:
            optstr += ' %s' % varname

        if section not in DESCRIPTIONS:
            DESCRIPTIONS[section] = OrderedDict()
        DESCRIPTIONS[section][optstr] = description
    _parser.add_argument(*args, **kwargs)


_add_arg('--help','-h', nargs='*', default=None,
         section='OPTIONS',
         description="Display help about TOPIC",
         varname='[TOPIC]')

_add_arg('--version','-v', action='store_true',
         section='OPTIONS',
         description="Display version number and exit")


_add_arg('--tui', '-t', action='store_true',
         section='OPTIONS',
         description='Enforce the TUI')
_add_arg('--notui', '--no-tui', '-T', action='store_true',
         section='OPTIONS',
         description='Inhibit the TUI')


_add_arg('--rcfile', '--rc-file', '-c',
         section='OPTIONS',
         description='Run commands from FILE upon startup',
         varname='FILE')
_add_arg('--norcfile', '--no-rc-file', '-C', action='store_true',
         section='OPTIONS',
         description='Do not run commands from any rc file')


_add_arg('--debug', type=lambda mods: mods.split(','), default=[],
         section='DEVELOPER OPTIONS',
         description=('Log debug messages from comma-separated list of MODULES'
                      ' (e.g. "client,commands.tui")'),
         varname='MODULES')
_add_arg('--debug-file', default=None,
         section='DEVELOPER OPTIONS',
         description='Log debug messages to FILE',
         varname='FILE')
_add_arg('--profile-file', default=None,
         section='DEVELOPER OPTIONS',
         description='Write cProfile statistics to FILE',
         varname='FILE')

# Anything not specified above is a subcommand or a subcommand option.
_parser.add_argument('subcmds', nargs=argparse.REMAINDER)
ARGS = vars(_parser.parse_args())
_subcmds = ARGS.pop('subcmds')

# Convert -h option to 'help' command
if ARGS['help'] is not None:
    _subcmds.append('help')
    _subcmds.extend(ARGS['help'])

# Convert -v option to 'version' command
if ARGS['version']:
    _subcmds.append('version')


# Assemble commands into a single string.  Arguments must be properly
# escaped/quoted, except for command operators (&, |, ;), which are
# interpreted by CommandManager.
from .commands import (OPS_AND, OPS_OR, OPS_SEQ)
_CMD_SEPARATORS = set().union(OPS_AND, OPS_OR, OPS_SEQ)

import shlex
subcmds = ' '.join(arg if arg in _CMD_SEPARATORS else shlex.quote(arg)
                   for arg in _subcmds)
