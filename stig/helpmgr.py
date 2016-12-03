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
from . import (APPNAME, __version__)
from .utils import (natsortkey, striplines, expandtabs)

from .cliopts import descriptions

MAIN_TOPICS = ('commands', 'settings', 'keymap', 'filter', 'sort', 'rcfile')

ALIASES = {
    'command': 'commands', 'cmds': 'commands', 'cmd': 'commands',
    'setting': 'settings', 'config': 'settings', 'cfg': 'settings',
    'keys': 'keymap', 'keybindings': 'keymap',
    'filters': 'filter', 'filtering': 'filter',
    'sorting': 'sort',
}


def finalize_lines(lines):
    return tuple(
        striplines(line.format(APPNAME=APPNAME)
                   for line in expandtabs.expand(lines))
    )


class HelpManager():
    """Provide help texts for CommandManager, Settings and KeyMap objects"""
    def __init__(self):
        self._cmdmgr = None
        self._settings = None
        self._keymap = None

    def find(self, topic=None):
        """Find help topic and return lines"""
        if topic in ALIASES:
            topic = ALIASES[topic]

        if topic is None:
            return self.overview
        elif topic in MAIN_TOPICS:
            return getattr(self, topic)
        elif topic in self._cmdmgr:
            return self.command(topic)
        elif topic in self._settings:
            return self.setting(topic)
        else:
            raise ValueError('Unknown help topic: {!r}'.format(topic))

    @property
    def overview(self):
        lines = [
            '{} {}'.format(APPNAME, __version__),
            '',
            'SYNTAX',
            '\t{APPNAME} [<OPTIONS>] [<COMMAND> ; <COMMAND> ; <COMMAND>...]',
            '',
        ]

        for section,opts in descriptions.items():
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
        """Must be set to a Settings object; provides a help text"""
        cfg = self._settings

        lines = [
            'SETTINGS',
            "\tSettings can be changed with the commands 'set' and 'reset'.",
            '',
            "\tUse an rc file (see 'help rcfile') to specify your custom defaults.",
            '',
        ]

        if cfg is None:
            lines.append('\tSettings have not been loaded.')
        else:
            lines.append('\tAVAILABLE SETTINGS')
            for name in sorted(cfg.names):
                lines.append('\t\t' + name + '  \t' + cfg[name].description)
        return finalize_lines(lines)

    @settings.setter
    def settings(self, settings):
        self._settings = settings

    def setting(self, name):
        """Return help text for setting"""
        v = self._settings[name]
        lines = ['{} [{}]'.format(v.name, v.typename),
                 '\t' + v.description,
                 '\tValue: \t' + v.str(default=False),
                 '\tDefault: \t' + v.str(default=True)]
        if hasattr(v, 'options'):
            lines.append('\tOptions: \t' + \
                         ', '.join(str(o) for o in sorted(v.options)))
        if hasattr(v, 'valuesyntax'):
            lines.append('\tSyntax: \t{}'.format(v.valuesyntax))
        return finalize_lines(lines)

    @property
    def commands(self):
        """Must be set to a CommandManager object; provides a help text"""
        lines = [
            'COMMANDS',
            '\tCommands can be called ',
            '\t\t- \tby providing them as command line arguments,',
            "\t\t- \tvia the internal command line (hit ':' to open it),",
            "\t\t- \tby binding them to keys (see 'help bind'),",
            ("\t\t- \tby listing them in an rc file (see 'help rcfile') "
             "and loading it with the '--rcfile' option or the 'rc' command."),
            '',

            '\tGUESSING CLI/TUI',
            ("\t\tIf commands are given as command line arguments and neither "
             "'--tui' nor '--notui' are provided, {APPNAME} tries to guess "
             "whether it makes sense to start the TUI or just run the commands "
             "and exit.  For example, if you run '{APPNAME} stop foo', "
             "it is reasonable to assume that you want to run 'stop foo' and "
             "get your shell prompt back as soon as possible.  But if you run "
             "'{APPNAME} set srv.url foo.bar', it is very likely that you "
             "expect the TUI to pop up."),
             '',
             "\t\tHere is how it works:",
             ("\t\t\t- \tBy default, the TUI is loaded."),
             ("\t\t\t- \tCommands in the TORRENT category (see below) "
              "inhibit the TUI."),
             ("\t\t\t- \tCommands that are exclusive to TUI or CLI "
              "(e.g. 'tab') enforce their interface."),
             ("\t\t\t- \tAny command that starts with 'set tui.' enforces the TUI."),
             ("\t\t\t- \tIf applying the above rules is inconclusive, the last "
              "command wins.  For example '{APPNAME} tab ls idle \; help' does not "
              "load the TUI, but '{APPNAME} help \; tab ls idle' does."),
            '',
        ]

        cmdmgr = self._cmdmgr
        if cmdmgr is None:
            lines.append('\tCommands have not been loaded.')
        else:
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

    @commands.setter
    def commands(self, cmdmgr):
        self._cmdmgr = cmdmgr

    def command(self, name):
        """Return help text for command"""
        cmd = self._cmdmgr[name]

        def takes_value(argspec):
            if 'nargs' in argspec:
                nargs = argspec['nargs']
                if nargs in ('+', '*', '?'):
                    return True
                elif isinstance(nargs, int) and nargs > 0:
                    return True
            return False

        def arg_dest(argspec):
            if 'metavar' in argspec:
                return argspec['metavar'].upper()
            elif 'dest' in argspec:
                return argspec['dest'].upper()
            elif argspec['names'][0][0] == '-':
                return argspec['names'][0].lstrip('-').upper()

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
                argline = '\t' + ','.join(argspec['names'])
                if takes_value(argspec):
                    dest = arg_dest(argspec)
                    if dest is not None:
                        argline += ' <' + dest + '>'

                argline += '  \t' + argspec['description']

                def stringify_default(default):
                    dflt = default() if callable(default) else default

                    if not isinstance(dflt, str) and isinstance(dflt, abc.Sequence):
                        return ' '.join(dflt)
                    else:
                        return str(dflt)

                if 'default_description' in argspec:
                    argline += ' (default: {})'.format(
                        stringify_default(argspec['default_description'])
                    )
                elif 'default' in argspec:
                    argline += ' (default: {})'.format(
                        stringify_default(argspec['default'])
                    )

                lines_args.append(argline)
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

        # Make sure the TUI (and ergo the keymap) is loaded
        from .tui import main

        km = self._keymap
        lines = []

        if km is None:
            lines.append('Keybindings have not been loaded.')
        else:
            def stringify(s):
                return ' '.join(s) if not isinstance(s, str) else s

            for context in sorted(km.contexts, key=lambda c: '' if c is None else c):
                if context is None:
                    lines.append('GENERAL KEYBINDINGS')
                else:
                    lines.append('{} KEYBINDINGS'.format(context.upper()))

                keymap = ((key, stringify(action)) for key,action in km.map(context))
                for key, action in sorted(keymap, key=lambda pair: natsortkey(pair[1])):
                    lines.append('\t{}  \t{}'.format(action, key))
                lines.append('')
        return finalize_lines(lines)

    @keymap.setter
    def keymap(self, keymap):
        self._keymap = keymap

    @property
    def filter(self):
        """Provide help text for arguments to TorrentFilter"""
        lines = [
            'FILTERING TORRENTS AND FILES',
            ('\tCommands that accept FILTER arguments for torrents or files '
             'are applied to torrents or files that match these arguments.'),
            '',
            '\tThere are two kinds of filters:',
            "\t\t- \tBoolean filters stand on their own (e.g. 'downloading')",
            "\t\t- \tComparative filters match against values (e.g. 'seeds>20').",
            '',
            '\tThe syntax of comparative filters is: [[<FILTER NAME>] <OPERATOR>] <VALUE>',
            '',
            ("\tBesides the standard operators (=, !=, >, <, >=, <=), '~' matches "
             "if the torrent's value contains VALUE."),
            "\tExample: 'name~foo' matches all torrents with 'foo' in their name.",
            '',
            ("\tIf FILTER NAME is omitted, it defaults to 'name'.  If OPERATOR is "
             "omitted, it defaults to '~'."),
            "\tExample: 'foo' is the same as '~foo' is the same as 'name~foo'.",
            '',
            ('\tSpaces before the filter name are ignored.  If there is a space '
             'between the filter name and the operator, all spaces at the '
             'start and end of VALUE are removed, otherwise they are preserved.  '),
            "\tExample: 'name = foo  ' matches 'foo'; 'name= foo  ' matches ' foo  '.",
            '',
            "\tAll filters can be inverted by prepending '!'.",
            ("\tExample: 'name!=foo' is the same as '!name=foo'; "
             "'!name!=foo' is the same as 'name=foo'."),
            '',
            ('\tWhen matching strings, matches are case-sensitive if VALUE includes '
             'upper-case characters, otherwise it is case-insensitive.'),
            '',
            ("\tWhen matching numbers, the unit prefixes 'k', 'M', 'G', 'T' and "
             "their binary counterparts 'Ki', 'Mi', 'Gi', 'Ti' are supported.  "
             "The case of unit prefixes is ignored."),
            ("\tExample: 'size>1mi' is the same as 'size>1048576' (1 Mebibyte); "
             "'size>1m' is the same as 'size>1000000' (1 Megabyte)"),
            '',
            ("\tFilters can be combined with the operators '&' (logical AND) "
             "and '|' (logical OR).  Multiple FILTER arguments are combined with '|'."),
            "\tExample: 'name=foo paused' is the same as 'name=foo|paused'.",
        ]

        from .client.filters.tfilter import SingleTorrentFilter
        lines += ['', '\tTORRENT FILTERS']
        lines.append('\t\tBOOLEAN FILTERS')
        for fname,f in sorted(SingleTorrentFilter.BOOLEAN_FILTERS.items()):
            lines.append('\t\t\t{} \t{}'.format(', '.join((fname,)+f.aliases), f.description))
        lines += ['', '\t\tCOMPARATIVE FILTERS']
        for fname,f in sorted(SingleTorrentFilter.COMPARATIVE_FILTERS.items()):
            lines.append('\t\t\t{} \t{}'.format(', '.join((fname,)+f.aliases), f.description))

        from .client.filters.ffilter import SingleTorrentFileFilter
        lines += ['', '\tTORRENT FILE FILTERS']
        lines.append('\t\tBOOLEAN FILTERS')
        for fname,f in sorted(SingleTorrentFileFilter.BOOLEAN_FILTERS.items()):
            lines.append('\t\t\t{} \t{}'.format(', '.join((fname,)+f.aliases), f.description))
        lines += ['', '\t\tCOMPARATIVE FILTERS']
        for fname,f in sorted(SingleTorrentFileFilter.COMPARATIVE_FILTERS.items()):
            lines.append('\t\t\t{} \t{}'.format(', '.join((fname,)+f.aliases), f.description))

        return finalize_lines(lines)

    @property
    def sort(self):
        """Provide help text for arguments to TorrentSorter"""
        from .client.tsort import SORTERS
        lines = [
            'SORTING TORRENTS',
            ('\tCommands with a SORT argument accept one of the sort orders '
             'listed below to sort torrents.'),
            '',
            '\tMultiple sort orders are separated with "," (e.g. "name,tracker").',
            '',
            ('\tSorting is reversed (descending instead of ascending) by '
             'prepending "!" (e.g. "!rate").'),
            '',
            ('\tTorrents are sorted alphabetically first before any other '
             'sort orders are applied.'),
        ]
        lines += ['', '\tSORT ORDERS']
        for sname,s in sorted(SORTERS.items()):
            snames = ', '.join((sname,) + s.aliases)
            lines.append('\t\t{} \t{}'.format(snames, s.description))
        return finalize_lines(lines)

    @property
    def rcfile(self):
        """Provide help text for rc file"""
        lines = [
            'RC FILES',
            ("\tAn rc file contains a list of arbitrary commands.  Lines starting "
             "with '#' (or more precisely '\s*#') are ignored."),
            '',
            ("\tThe default rc file path is '$XDG_CONFIG_HOME/{APPNAME}/rc'.  "
             "XDG_CONFIG_HOME defaults to '~/.config'.  A different path can be "
             "provided with the '--rcfile' option.  An existing rc file at the "
             "default path can be ignored with the '--norcfile' option."),
            '',
            ('\tCommands in an rc file are called during startup before the '
             'commands given on the command line.'),
            '',
            ("\tTUI commands (e.g. 'tab' or 'bind') in an rc file are ignored "
             "in CLI mode."),
        ]
        return finalize_lines(lines)
