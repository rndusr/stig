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


parser = argparse.ArgumentParser(add_help=False)
descriptions = OrderedDict()
def add_arg(*args, section='OPTIONS', description=None, varname=None, **kwargs):
    if description is not None:
        optstr = ','.join(args)
        if varname is not None:
            optstr += ' %s' % varname

        if section not in descriptions:
            descriptions[section] = OrderedDict()
        descriptions[section][optstr] = description
    parser.add_argument(*args, **kwargs)


add_arg('--help','-h', nargs='*', default=None,
        section='OPTIONS',
        description="Display help about TOPIC",
        varname='[TOPIC]')

add_arg('--version','-v', action='store_true',
        section='OPTIONS',
        description="Display version number and exit")

add_arg('--tui', '-t', action='store_true',
        section='OPTIONS',
        description='Enforce the TUI')
add_arg('--notui', '--no-tui', '-T', action='store_true',
        section='OPTIONS',
        description='Inhibit the TUI')

add_arg('--rcfile', '--rc-file', '-c',
        section='OPTIONS',
        description='Run commands from FILE upon startup',
        varname='FILE')
add_arg('--norcfile', '--no-rc-file', '-C', action='store_true',
        section='OPTIONS',
        description='Do not run commands from any rc file')

add_arg('--debug', type=lambda mods: mods.split(','), default=[],
        section='DEVELOPER OPTIONS',
        description=('Log debug messages from comma-separated list of MODULES'
                     ' (e.g. "client,commands.tui")'),
        varname='MODULES')
add_arg('--debug-file', default=None,
        section='DEVELOPER OPTIONS',
        description='Log debug messages to FILE',
        varname='FILE')
add_arg('--profile-file', default=None,
        section='DEVELOPER OPTIONS',
        description='Write cProfile statistics to FILE',
        varname='FILE')

# Anything not specified above is a subcommand or a subcommand option.
parser.add_argument('subcmds', nargs=argparse.REMAINDER)
ARGS = vars(parser.parse_args())
_SUBCMDS = ARGS.pop('subcmds')

# Convert -h option to 'help' command
if ARGS['help'] is not None:
    _SUBCMDS.append('help')
    _SUBCMDS.extend(ARGS['help'])

# Convert -v option to 'version' command
if ARGS['version']:
    _SUBCMDS.append('version')


_CMD_SEPARATORS = (';',)

def get_cmds():
    """Return tuple of commands, each command being a tuple of arguments"""
    cmds = [[]]
    for arg in _SUBCMDS:
        if arg in _CMD_SEPARATORS:
            cmds.append([])       # Start new command
        else:
            cmds[-1].append(arg)  # Append arg to current command
    return tuple(tuple(cmd) for cmd in cmds if cmd)
