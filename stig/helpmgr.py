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

"""Anything related to the help system that is common between interfaces"""

import re
import string
from collections import abc

from . import __appname__, __version__, objects
from .cliopts import DESCRIPTIONS as CLI_DESCRIPTIONS
from .utils import expandtabs
from .utils.string import striplines
from .utils.usertypes import Float, Int

from .logging import make_logger  # isort:skip
log = make_logger(__name__)


class ForgivingFormatter(string.Formatter):
    def get_value(self, key, args, kwargs):
        if isinstance(key, str):
            try:
                return kwargs[key]
            except KeyError:
                return '{%s}' % key
        else:
            return super().get_value(key, args, kwargs)

    def __call__(self, lines):
        return tuple(
            striplines(self.format(line, __appname__=__appname__)
                       for line in expandtabs.expand(lines, indent=2))
        )

finalize_lines = ForgivingFormatter()


class HelpManager():
    """Provide help texts for CommandManager, Settings and KeyMap objects"""

    MAIN_TOPICS = {
        'commandsmanual' : 'Describes how to call and chain commands',
        'commands'       : 'Lists commands',
        'filtersmanual'  : 'Describes how to define and combine filters',
        'filters'        : 'Lists filters for torrents, files, etc',
        'settingsmanual' : 'Describes how to change settings',
        'settings'       : 'Lists configuration settings',
        'keybindings'    : 'Lists TUI keybindings',
    }

    ALIASES = {
        'cmds'        : 'commands',
        'cmdsman'     : 'commandsmanual',
        'filtersman'  : 'filtersmanual',
        'config'      : 'settings',
        'cfg'         : 'settings',
        'configman'   : 'settingsmanual',
        'cfgman'      : 'settingsmanual',
        'keymap'      : 'keybindings',
        'keys'        : 'keybindings',
    }

    def find(self, topic=None):
        """Find help topic and return lines"""
        if topic in self.ALIASES:
            topic = self.ALIASES[topic]

        if topic is None:
            return self.topic_overview

        if hasattr(self, 'topic_' + topic):
            return getattr(self, 'topic_' + topic)
        elif topic in objects.cmdmgr:
            return self.command(topic)
        elif topic in objects.cfg:
            return self.setting(topic)

        raise ValueError('Unknown help topic: %r' % topic)

    @property
    def topic_overview(self):
        lines = [
            '{} {}'.format(__appname__, __version__),
            '',
            'SYNTAX',
            '\t{__appname__} [<OPTIONS>] [<COMMANDS>]',
            '',
        ]

        for section,opts in CLI_DESCRIPTIONS.items():
            lines.append('%s' % section.upper())
            for opts,desc in opts.items():
                lines.append('\t%s  \t%s' % (opts, desc))
            lines.append('')

        def topic_line(topic):
            names = (topic,) + tuple(alias for alias,topic_ in self.ALIASES.items()
                                     if topic_ == topic)
            return '\t\t%s \t- \t%s' % (', '.join(names), self.MAIN_TOPICS[topic])

        lines += ['HELP TOPICS',
                  ('\tAll commands and settings are valid help topics.  Read '
                   "them with '{__appname__} help <TOPIC>' or '{__appname__} -h <TOPIC>'.  "
                   'Additionally, the following topics are available:')]
        lines.extend(topic_line(topic) for topic in self.MAIN_TOPICS)

        return finalize_lines(lines)

    @property
    def topic_settingsmanual(self):
        lines = [
            'SETTINGS',
            ("\tSettings can be changed with the commands 'set' and 'reset' "
             "(see 'help set' and 'help reset')."),
            '',
            ('\tLocal settings change the behaviour of {__appname__} while '
             'remote settings change the behaviour of the connected daemon.  '
             'The names of remote settings start with "srv.".'),
            '',
            ('\tChanges made to local settings are not permanent.  All '
             'values are set back to their defaults once {__appname__} is '
             'restarted (see RC FILES).'),
            '',
            ('\tChanges made to remote settings, on the other hand, are '
             'permanent as the daemon has its own configuration system.'),
            '',
            ('\tIn the TUI, the "set" command with no arguments (bound to <alt-s> '
             'by default) lists all settings and lets you edit them with <enter>.  '
             'The "dump" command (bound to <alt-S> by default) makes your '
             'current settings, keybindings and tabs permanent.'),
            '',
            'RC FILES',
            ('\tAn rc file contains a list of arbitrary commands.  '
             r'Commands can span multiple lines by escaping line breaks with "\".  '
             'Lines starting with "#" (optionally preceded by spaces) are ignored.'),
            '',
            ('\tCommands in an rc file are called during startup before the '
             'commands given on the command line.'),
            '',
            ('\tThe default rc file path is "$XDG_CONFIG_HOME/{__appname__}/rc", '
             'where $XDG_CONFIG_HOME defaults to "~/.config" if it is not set.'),
            '',
            ('\tA different path can be provided with the "--rcfile" option.  '
             'An existing rc file at the default path can be ignored with the '
             '"--norcfile" option.'),
            '',
            '\tTo permanently change the default config file, create an alias:',
            '',
            '\t\t$ alias {__appname__}="command {__appname__} --rcfile ~/.{__appname__}rc"',
            '',
            ('\tTo load any additional rc files after the default one use the '
             '"rc" command.  (Note that this will prevent the TUI from being '
             'loaded unless you provide the "--tui" option.  See the GUESSING '
             'THE USER INTERFACE section in the "commandsmanual" help for '
             'more information).'),
            '',
            ('\tTUI commands (e.g. "tab" or "bind") in an rc file are ignored '
             'in CLI mode.'),
        ]

        return finalize_lines(lines)

    @property
    def topic_settings(self):
        """Return help text for all settings"""
        localcfg = objects.localcfg
        remotecfg = objects.remotecfg

        lines = []
        lines.append('LOCAL SETTINGS')
        for name in sorted(localcfg):
            lines.append('\t' + name + '  \t' + localcfg.description(name))

        lines += ['']

        lines.append('REMOTE SETTINGS')
        for name in sorted(remotecfg):
            lines.append('\t' + name + '  \t' + remotecfg.description(name))
        return finalize_lines(lines)

    def setting(self, name):
        """Return help text for setting"""
        cfg = objects.cfg
        if name not in objects.cfg:
            raise ValueError('Unknown help topic: %r' % name)
        value = cfg[name]

        def pretty_string(value):
            if isinstance(value, str) and re.match(r'^\s+$', value):
                return repr(value)
            elif isinstance(value, (Float, Int)):
                return value.with_unit
            else:
                return str(value)

        lines = ['%s - \t%s' % (name, cfg.description(name)),
                 '\tValue: \t' + pretty_string(cfg[name]),
                 '\tDefault: \t' + pretty_string(cfg.default(name))]

        if hasattr(value, 'options'):
            opt_strs = []
            for opt in sorted(value.options):
                opt_strs.append(str(opt))
                aliases = [alias for alias,option in value.aliases.items()
                           if option == opt]
                if aliases:
                    opt_strs[-1] += ' (%s)' % (', '.join(aliases))
            lines.append('\tOptions: \t' + ', '.join(opt_strs))

        lines.append('\tSyntax: \t' + cfg.syntax(name))

        return finalize_lines(lines)

    @property
    def topic_commandsmanual(self):
        from .commands import (OPS_AND, OPS_OR, OPS_SEQ)
        lines = [
            'COMMANDS',
            '\tCommands can be called:',
            '\t\t- \tby providing them as command line arguments,',
            "\t\t- \tvia the command line in the TUI (press ':' to open it),",
            "\t\t- \tby binding them to keys (see 'help bind'),",
            ("\t\t- \tby listing them in an rc file (see 'help cfgman') "
             "and loading it with the '--rcfile' option or the 'rc' command."),
            '',
            'CHAINING COMMANDS',
            ("\tCombining commands with operators makes it possible to run "
             "a command based on the previous command's success."),
            "",
            "\tAvailable command operators are: ",
            "\t\t%s \t- \tRun the next command if the previous command succeeded." % '/'.join(OPS_AND),
            "\t\t%s \t- \tRun the next command if the previous command failed." % '/'.join(OPS_OR),
            "\t\t%s \t- \tRun the next command in any case." % '/'.join(OPS_SEQ),
            "",
            "\tCommand operators must be enclosed by spaces.",
            "",
            ("\tFor example, 'ls foo & ls bar' would list all 'foo' torrents and, "
             "if any where found, continue to list all 'bar' torrents.  "
             "However, 'ls foo | ls bar' would list 'bar' torrents only if there "
             "are no 'foo' torrents."),
            '',
            'GUESSING THE USER INTERFACE (CLI/TUI)',
            ("\tIf commands are given as command line arguments and neither "
             "'--tui' nor '--notui' are provided, {__appname__} tries to guess "
             "whether it makes sense to start the TUI or just run the commands "
             "and exit.  For example, if you run '{__appname__} stop foo', "
             "it is reasonable to assume that you want to run 'stop foo' and "
             "get your shell prompt back.  But if you run "
             "'{__appname__} set connect.host foo.bar', "
             "you probably expect the TUI to pop up."),
            '',
            "\tThis is how this works basically:",
            ("\t\t- \tWithout CLI commands, the TUI is loaded and vice versa."),
            ("\t\t- \tCommands in the torrent category (see 'help commands') prevent the TUI."),
            ("\t\t- \tChanging TUI settings ('(re)set tui.*') enforces the TUI."),
            ("\t\t- \tChanging remote settings ('set srv.*') prevents the TUI."),
            ("\t\t- \tCommands that are exclusive to TUI or CLI (e.g. 'tab') enforce their "
             "interface.  Providing both TUI- and CLI-only commands produces an error.  "
             "Provide --tui or --notui in that case."),
        ]
        return finalize_lines(lines)

    @property
    def topic_commands(self):
        """Must be set to a CommandManager object; provides a help text"""
        lines = []
        for category in objects.cmdmgr.categories:
            lines.append('{} COMMANDS'.format(category.upper()))

            # To deduplicate commands with the same name that provide
            # different interfaces (but should have the same docs), map
            # command names to commands.
            cmds = {}
            for cmd in objects.cmdmgr.all_commands:
                if category == cmd.category:
                    cmds[cmd.name] = cmd

            for cmdname,cmd in sorted(cmds.items()):
                lines.append('\t{}  \t{}'.format(', '.join((cmd.name,) + cmd.aliases),
                                                 cmd.description))
            lines.append('')
        return finalize_lines(lines)

    def command(self, name):
        """Return help text for command"""
        cmd = objects.cmdmgr[name]

        def takes_value(argspec):
            if argspec.get('action') in ('store_true', 'store_false', 'store_const'):
                return False  # Boolean option
            if 'nargs' not in argspec:
                return True
            nargs = argspec['nargs']
            return not isinstance(nargs, int) or nargs > 0

        def arg_dest(argspec):
            if 'metavar' in argspec:
                dest = argspec['metavar'].upper()
            elif 'dest' in argspec:
                dest = argspec['dest'].upper()
            elif argspec['names'][0][0] == '-':
                dest = argspec['names'][0].lstrip('-').upper()
            else:
                return None

            if 'nargs' in argspec and argspec['nargs'] in ('*', '?'):
                return '[<%s>]' % dest
            else:
                return '<%s>' % dest

        lines = [cmd.name.upper()]

        log.debug('Generating help text for %s', cmd.name)
        names = ', '.join((cmd.name,) + cmd.aliases)
        lines = [names + ' - \t' + cmd.description]
        lines.append('')

        if cmd.usage:
            lines.append('USAGE')
            lines += ['\t' + u for u in cmd.usage]
            lines.append('')

        if cmd.argspecs:
            lines.append('ARGUMENTS')
            lines_args = []
            for argspec in cmd.argspecs:
                if 'description' not in argspec:
                    # Argument has no description
                    continue

                arglines = ['\t' + ', '.join(argspec['names'])]
                if takes_value(argspec):
                    dest = arg_dest(argspec)
                    if dest is not None:
                        arglines[0] += ' %s' % dest

                if isinstance(argspec['description'], str):
                    arglines[0] += '  \t' + argspec['description']
                else:  # Assume description is a sequence
                    arglines[0] += '  \t' + argspec['description'][0]
                    for paragraph in argspec['description'][1:]:
                        arglines.append('\t  \t' + paragraph)

                if 'document_default' not in argspec or argspec['document_default']:
                    # Argument takes a value that may default to another value
                    # if ommitted and we want to document that default value
                    def stringify_default(default):
                        dflt = default() if callable(default) else default

                        if not isinstance(dflt, str) and isinstance(dflt, abc.Sequence):
                            return ' '.join(dflt)
                        else:
                            return str(dflt)

                    if 'default_description' in argspec:
                        arglines.append('\t  \tDefault: %s' % stringify_default(argspec['default_description']))
                    elif 'default' in argspec:
                        arglines.append('\t  \tDefault: %s' % stringify_default(argspec['default']))

                lines_args.extend(arglines)
            lines += lines_args
            lines.append('')

        if cmd.examples:
            lines.append('EXAMPLES')
            lines += ['\t' + e for e in cmd.examples]
            lines.append('')

        for name,text in sorted(cmd.more_sections.items()):
            lines.append(name.upper())
            if callable(text):
                text = text()
            lines += ['\t' + line for line in text]
            lines.append('')

        return finalize_lines(lines)

    @property
    def topic_keybindings(self):
        """Must be set to a KeyMap object; provides a help text"""
        from .tui.tuiobjects import keymap

        def stringify(s):
            return ' '.join(s) if not isinstance(s, str) else s

        lines = []
        for context in sorted(keymap.contexts, key=lambda c: '' if c is None else c):
            if context is None:
                lines.append('GENERAL KEYBINDINGS')
            else:
                lines.append('{} KEYBINDINGS'.format(context.upper()))

            km = ((key, stringify(action)) for key,action in keymap.map(context))

            # Sort by command
            from natsort import natsorted, ns
            for key,action in natsorted(km, key=lambda pair: pair[1], alg=ns.IGNORECASE):
                if len(action) < 40:
                    lines.append('\t%s  \t%s  \t%s' % (key, action, keymap.get_description(key, context)))
                else:
                    lines.append('\t%s  \t%s' % (key, action))
                    lines.append('\t  \t%s' % (keymap.get_description(key, context),))
            lines.append('')
        return finalize_lines(lines)

    @property
    def topic_filtersmanual(self):
        lines = [
            'FILTERING TORRENTS, FILES, PEERS, ETC',
            ('\tCommands that accept FILTER arguments are applied to items '
             'that match these filters.'),
            '',
            '\tThere are two kinds of filters:',
            '\t\t- \tBoolean filters stand on their own (e.g. "downloading")',
            '\t\t- \tComparative filters need a value (e.g. "seeds>20")',
            '',
            '\tThe syntax of comparative filters is: [[<FILTER NAME>]<OPERATOR>]<VALUE>',
            '',
            ('\tBesides the usual operators (=, !=, >, <, >=, <=), "~" matches if the '
             'item\'s value contains the literal string VALUE and "=~" matches if the '
             'item\'s value matches against the Perl-style regular expression VALUE.'),
            '\tExample: "name~foo" matches all torrents with "foo" in their name.',
            '',
            ('\tIf FILTER NAME is omitted, it defaults to a comparative filter that '
             "makes sense, e.g. \"name\" for torrents (see 'help filters').  "
             'If OPERATOR is omitted, it defaults to "~".'),
            '\tExample: "foo" is the same as "~foo" is the same as "name~foo".',
            '',
            ('\tSpaces at the start and the end of VALUE are always removed.  '
             'If the result starts and ends with matching single or double quotes, the '
             'quotes are removed.  Any other quotes are not interpreted, i.e. they must '
             'not be escaped.'),
            '\tExample: "name = foo " matches "foo"; "name = \' foo \' " matches " foo "',
            '',
            '\tAll filters can be inverted by prepending "!" to the filter name.',
            ('\tExample: "name!=foo" is the same as "!name=foo"; '
             '"!name!=foo" is the same as "name=foo".'),
            '',
            ('\tMatching strings is case-insensitive if VALUE does not contain any '
             'upper-case characters, otherwise it is case-sensitive.'),
            '',
            ('\tWhen matching numbers, the unit prefixes "k", "M", "G", "T" and '
             'their binary counterparts "Ki", "Mi", "Gi", "Ti" are supported.  '
             'The case of unit prefixes is ignored.'),
            ('\tExample: "size>1mi" is the same as "size>1048576" (1 Mebibyte); '
             '"size>1m" is the same as "size>1000000" (1 Megabyte)'),
            '',
            ('\tFor time-based filters, VALUE is either an absolute time stamp '
             'or a relative time delta based on the current time.'),
            '',
            ('\tTime stamps support a date in the format [[YYYY-]MM-]DD or YYYY[-MM] '
             'and a time in the format HH:MM[:SS].  Date and time can be combined by '
             'separating them with a space.'),
            '\tExamples: \t"added=2015-05" \tmatches torrents that were added in May 2015.',
            ('\t\t"completed>=01" \tmatches torrents that finished downloading earlier this month '
             '("01" being the first day of the current month).'),
            ('\t\t"activity<10-17 18:45" \tmatches torrents that were last active before '
             '18:45 (6:45 p.m.) on the 17th of October of this year.'),
            '',
            ('\tTime deltas use the format [in |+|-]AMOUNT[s|m|h|d|w|M|y][ ago].  '
             'The words "in" and "ago" are aliases for "+" and "-".  Negative time '
             'deltas match time stamps in the past and positive time deltas '
             'match time stamps in the future.  Filters have individual defaults for '
             'the sign; e.g. "eta > 1h" is the same as "eta > in 1h" while '
             '"completed > 1h" is the same as "completed > 1h ago".'),
            '',
            ('\tFilters can be combined with the operators "&" (logical AND) '
             'and "|" (logical OR).  Multiple FILTER arguments are implicitly '
             'combined with "|".'),
            '\tExample: "name=foo paused" is the same as "name=foo|paused".',
            '',
            ('\tOperators can be escaped with a preceding "\\" to remove their meaning.'),
            '\tExample: "name=foo\\&bar" matches torrents with the name "foo&bar".',
        ]
        return finalize_lines(lines)

    @property
    def topic_filters(self):
        """Provide help text for arguments to TorrentFilter"""
        from .client import (TorrentFilter, FileFilter,
                             PeerFilter, TrackerFilter,
                             SettingFilter)
        lines = []
        for caption,filt in (('TORRENT FILTERS', TorrentFilter),
                             ('FILE FILTERS', FileFilter),
                             ('PEER FILTERS', PeerFilter),
                             ('TRACKER FILTERS', TrackerFilter),
                             ('SETTING FILTERS', SettingFilter)):
            lines += ['',
                      '%s' % caption,
                      '\tDEFAULT FILTER: %s' % filt.DEFAULT_FILTER,
                      '']

            lines.append('\tBOOLEAN FILTERS')
            for fname,f in sorted(filt.BOOLEAN_FILTERS.items()):
                lines.append('\t\t{} \t{}'.format(', '.join((fname,) + f.aliases), f.description))

            lines += ['', '\tCOMPARATIVE FILTERS']
            for fname,f in sorted(filt.COMPARATIVE_FILTERS.items()):
                if fname == filt.DEFAULT_FILTER:
                    lines.append('\t\t{} \t{} (default)'.format(', '.join((fname,) + f.aliases), f.description))
                else:
                    lines.append('\t\t{} \t{}'.format(', '.join((fname,) + f.aliases), f.description))

        return finalize_lines(lines)
