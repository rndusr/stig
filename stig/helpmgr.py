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

from .logging import make_logger
log = make_logger(__name__)

from collections import abc
import re

from . import (__appname__, __version__)
from .utils import expandtabs
from .utils.string import striplines
from .cliopts import DESCRIPTIONS as CLI_DESCRIPTIONS

MAIN_TOPICS = ('commands', 'settings', 'keymap', 'filters', 'rcfile')

ALIASES = {
    'cmds': 'commands',
    'config': 'settings', 'cfg': 'settings',
    'keys': 'keymap', 'keybindings': 'keymap',
    'filtering': 'filters',
    'rcfiles': 'rcfile',
}


import string
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
    def find(self, topic=None):
        """Find help topic and return lines"""
        if topic in ALIASES:
            topic = ALIASES[topic]

        if topic is None:
            return self.overview
        elif topic in MAIN_TOPICS:
            return getattr(self, topic)
        elif topic in self.cmdmgr:
            return self.command(topic)
        elif topic in self.localcfg or topic[4:] in self.remotecfg:
            return self.setting(topic)

        raise ValueError('Unknown help topic: %r' % topic)

    @property
    def overview(self):
        lines = [
            '{} {}'.format(__appname__, __version__),
            '',
            'SYNTAX',
            '\t{__appname__} [<OPTIONS>] [<COMMAND> ; <COMMAND> ; <COMMAND>...]',
            '',
        ]

        for section,opts in CLI_DESCRIPTIONS.items():
            lines.append('%s' % section.upper())
            for opts,desc in opts.items():
                lines.append('\t%s  \t%s' % (opts, desc))
            lines.append('')

        lines.append('For more information run:')
        for topic in MAIN_TOPICS:
            lines.append('\thelp %s' % topic)
        return finalize_lines(lines)

    @property
    def settings(self):
        """Return help text for all settings"""
        localcfg = self.localcfg
        remotecfg = self.remotecfg

        lines = [
            'SETTINGS',
            "\tSettings can be changed with the commands 'set' and 'reset'.",
            '',
            "\tUse an rc file (see 'help rcfile') to specify your custom defaults.",
            '',
        ]

        lines.append('\tLOCAL SETTINGS')
        for name in sorted(localcfg):
            lines.append('\t\t' + name + '  \t' + localcfg.description(name))

        lines += ['']

        lines.append('\tREMOTE SETTINGS')
        for name in sorted(remotecfg):
            lines.append('\t\tsrv.' + name + '  \t' + remotecfg.description(name))
        return finalize_lines(lines)

    def setting(self, name):
        """Return help text for setting"""
        if name in self.localcfg:
            cfg = self.localcfg
            key = name
        elif name[4:] in self.remotecfg:
            cfg = self.remotecfg
            key = name[4:]
        else:
            raise ValueError('Unknown help topic: %r' % name)
        value = cfg[key]

        def maybe_quote(value):
            if isinstance(value, str) and re.match(r'^\s+$', value):
                return repr(value)
            else:
                return str(value)

        lines = ['%s - \t%s' % (name, cfg.description(key)),
                 '\tValue: \t' + maybe_quote(cfg[key]),
                 '\tDefault: \t' + maybe_quote(cfg.default(key))]

        if hasattr(value, 'options'):
            opt_strs = []
            for opt in sorted(value.options):
                opt_strs.append(str(opt))
                aliases = [alias for alias,option in value.aliases.items()
                           if option == opt]
                if aliases:
                    opt_strs[-1] += ' (%s)' % (', '.join(aliases))
            lines.append('\tOptions: \t' + ', '.join(opt_strs))

        lines.append('\tSyntax: \t' + cfg.syntax(key))

        return finalize_lines(lines)

    @property
    def commands(self):
        """Must be set to a CommandManager object; provides a help text"""
        from .commands import (OPS_AND, OPS_OR, OPS_SEQ)
        lines = [
            'COMMANDS',
            '\tCommands can be called ',
            '\t\t- \tby providing them as command line arguments,',
            "\t\t- \tvia the internal command line (hit ':' to open it),",
            "\t\t- \tby binding them to keys (see 'help bind'),",
            ("\t\t- \tby listing them in an rc file (see 'help rcfile') "
             "and loading it with the '--rcfile' option or the 'rc' command."),
            '',
            '\tCHAINING COMMANDS',
            ("\t\tCombining commands with operators makes it possible to run "
             "a command based on the previous command's success."),
            "",
            "\t\tAvailable command operators are: ",
            "\t\t\t%s \t- \tRun the next command if the previous command succeeded." % '/'.join(OPS_AND),
            "\t\t\t%s \t- \tRun the next command if the previous command failed." % '/'.join(OPS_OR),
            "\t\t\t%s \t- \tRun the next command in any case." % '/'.join(OPS_SEQ),
            "",
            "\t\tCommand operators must be enclosed by spaces.",
            "",
            ("\t\tFor example, 'ls foo & ls bar' would list all 'foo' torrents and, "
             "if any where found, continue to list all 'bar' torrents.  "
             "However, 'ls foo | ls bar' would list 'bar' torrents only if there "
             "are no 'foo' torrents."),
            '',
            '\tGUESSING THE USER INTERFACE (CLI/TUI)',
            ("\t\tIf commands are given as command line arguments and neither "
             "'--tui' nor '--notui' are provided, {__appname__} tries to guess "
             "whether it makes sense to start the TUI or just run the commands "
             "and exit.  For example, if you run '{__appname__} stop foo', "
             "it is reasonable to assume that you want to run 'stop foo' and "
             "get your shell prompt back.  But if you run "
             "'{__appname__} set connect.host foo.bar', "
             "you probably expect the TUI to pop up."),
            '',
            "\t\tThis is how this works basically:",
            ("\t\t\t- \tWithout CLI commands, the TUI is loaded."),
            ("\t\t\t- \tCommands in the TORRENT category (see below) prevent the TUI."),
            ("\t\t\t- \tChanging TUI settings ('(re)set tui.*') enforces the TUI."),
            ("\t\t\t- \tChanging remote settings ('set srv.*') prevents the TUI."),
            ("\t\t\t- \tCommands that are exclusive to TUI or CLI "
             "(e.g. 'tab') enforce their interface.  Providing both TUI- "
             "and CLI-only commands produces an error."),
            '',
        ]

        cmdmgr = self.cmdmgr
        for category in cmdmgr.categories:
            lines.append('\t{} COMMANDS'.format(category.upper()))

            # To deduplicate commands with the same name that provide
            # different interfaces (but should have the same docs), map
            # command names to commands.
            cmds = {}
            for cmd in cmdmgr.all_commands:
                if category == cmd.category:
                    cmds[cmd.name] = cmd

            for cmdname,cmd in sorted(cmds.items()):
                lines.append('\t\t{}  \t{}'.format(', '.join((cmd.name,)+cmd.aliases),
                                                   cmd.description))
            lines.append('')
        return finalize_lines(lines)

    def command(self, name):
        """Return help text for command"""
        cmd = self.cmdmgr[name]

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
    def keymap(self):
        """Must be set to a KeyMap object; provides a help text"""

        from .tui import main as tui
        km = tui.keymap
        lines = []

        def stringify(s):
            return ' '.join(s) if not isinstance(s, str) else s

        for context in sorted(km.contexts, key=lambda c: '' if c is None else c):
            if context is None:
                lines.append('GENERAL KEYBINDINGS')
            else:
                lines.append('{} KEYBINDINGS'.format(context.upper()))

            keymap = ((key, stringify(action)) for key,action in km.map(context))

            # Sort by command
            from natsort import (natsort_keygen, natsorted, ns)
            get_cmd = natsort_keygen(key=lambda pair: pair[1], alg=ns.IGNORECASE)
            for key,action in natsorted(keymap, key=get_cmd):
                if len(action) < 40:
                    lines.append('\t%s  \t%s  \t%s' % (key, action, km.get_description(key, context)))
                else:
                    lines.append('\t%s  \t%s' % (key, action))
                    lines.append('\t  \t%s' % (km.get_description(key, context),))
            lines.append('')
        return finalize_lines(lines)

    @property
    def filters(self):
        """Provide help text for arguments to TorrentFilter"""
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
            ('\tBesides the usual operators (=, !=, >, <, >=, <=), "~" matches '
             'if the item\'s value contains VALUE.'),
            '\tExample: "name~foo" matches all torrents with "foo" in their name.',
            '',
            ('\tIf FILTER NAME is omitted, it defaults to "name" for torrents and '
             'files and "domain" for trackers.  Peers don\'t have a default filter.  '
             'If OPERATOR is omitted, it defaults to "~".'),
            '\tExample: "foo" is the same as "~foo" is the same as "name~foo".',
            '',
            ('\tSpaces at the start and the end of VALUE are always removed.  '
             'If the result is enclosed by matching single or double quotes, they '
             'are removed.  Any other quotes are not interpreted, i.e. they must '
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
            '\tExamples: \t"added=2015-05" matches torrents that were added in May 2015.',
            '\t\t"completed>=01" matches torrents that finished downloading earlier this month.',
            ('\t\t"activity<10-17 18:45" matches torrents that were last active before '
             '18:45 (6:45 pm) on the 17th of October of this year.'),
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
            '\tExample: "name=foo\&bar" matches torrents with the name "foo&bar".',
        ]

        from .client.filters.torrent import SingleTorrentFilter
        from .client.filters.file import SingleTorrentFileFilter
        from .client.filters.peer import SingleTorrentPeerFilter
        from .client.filters.tracker import SingleTrackerFilter

        for caption,filt in (('TORRENT FILTERS', SingleTorrentFilter),
                             ('FILE FILTERS', SingleTorrentFileFilter),
                             ('PEER FILTERS', SingleTorrentPeerFilter),
                             ('TRACKER FILTERS', SingleTrackerFilter)):
            lines += ['', '\t%s' % caption]
            lines.append('\t\tBOOLEAN FILTERS')
            for fname,f in sorted(filt.BOOLEAN_FILTERS.items()):
                lines.append('\t\t\t{} \t{}'.format(', '.join((fname,)+f.aliases), f.description))
            lines += ['', '\t\tCOMPARATIVE FILTERS']
            for fname,f in sorted(filt.COMPARATIVE_FILTERS.items()):
                lines.append('\t\t\t{} \t{}'.format(', '.join((fname,)+f.aliases), f.description))

        return finalize_lines(lines)

    @property
    def rcfile(self):
        """Provide help text for rc file"""
        lines = [
            'RC FILES',
            ('\tAn rc file is a script that contains a list of arbitrary commands.  '
             'Commands can span multiple lines by escaping linebreaks with "\\".  '
             'Lines starting with "#" (optionally preceded by spaces) are ignored.'),
            '',
            ('\tThe default rc file path is "$XDG_CONFIG_HOME/{__appname__}/rc", '
             'where XDG_CONFIG_HOME defaults to "~/.config" if it is not set.'),
            '',
            ('\tA different path can be provided with the "--rcfile" option.  '
             'An existing rc file at the default path can be ignored with the '
             '"--norcfile" option.'),
            '',
            '\tTo permanently change the default config file, create an alias:',
            '',
            '\t\t$ alias stig="command stig --rcfile ~/.stigrc"',
            '',
            ('\tTo load an additional rc file after the default one, use the '
             '"rc" command.  (Note that this will prevent the TUI from being '
             'loaded unless you provide the "--tui" option.  See the GUESSING '
             'THE USER INTERFACE section in the "commands" help for more information.)'),
            '',
            ('\tCommands in an rc file are called during startup before the '
             'commands given on the command line.'),
            '',
            ('\tTUI commands (e.g. "tab" or "bind") in an rc file are ignored '
             'in CLI mode.'),
        ]
        return finalize_lines(lines)
