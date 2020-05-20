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

"""Base classes for documentation commands"""

from .. import CmdError, CommandMeta
from ... import __appname__, __version__, objects
from ...completion import candidates
from ...logging import make_logger

log = make_logger(__name__)



class HelpCmdbase(metaclass=CommandMeta):
    name = 'help'
    aliases = ('man',)
    category = 'miscellaneous'
    provides = set()
    description = 'List or explain commands and settings'
    usage = ('help',
             'help <TOPIC> <TOPIC> ...')
    examples = ('help',
                'help help')
    argspecs = (
        {'names': ('TOPIC',), 'nargs': '*',
         'description': 'Name of command, setting or category'},
    )

    TOPIC_DELIMITER = ('', '-  ' * 20, '')

    def run(self, TOPIC):
        topics = TOPIC
        lines = []
        success = True
        existing_topics = []

        if len(topics) < 1:
            lines = objects.helpmgr.find('overview')
        else:
            for topic in topics:
                try:
                    line = objects.helpmgr.find(topic)
                except ValueError as e:
                    self.error(e)
                    success = False
                else:
                    lines.extend(line)
                    lines.extend(self.TOPIC_DELIMITER)
                    existing_topics.append(topic)

            if lines:
                # Remove last TOPIC_DELIMITER
                for _ in range(len(self.TOPIC_DELIMITER)):
                    lines.pop(-1)

        if not existing_topics:
            existing_topics.append(__appname__)

        self.display_help(existing_topics, lines)
        if not success:
            raise CmdError()

    @classmethod
    def completion_candidates_posargs(cls, args):
        """Complete positional arguments"""
        return candidates.help_topics()


class VersionCmdbase(metaclass=CommandMeta):
    name = 'version'
    category = 'miscellaneous'
    provides = set()
    description = 'Show {} version'.format(__appname__)

    def run(self):
        log.info('%s version %s' % (__appname__, __version__))


class LogCmdbase(metaclass=CommandMeta):
    name = 'log'
    provides = set()
    category = 'miscellaneous'
    description = 'Clear, add or scroll through log messages'
    usage = ('log <ACTION> [<PARAMETER> <PARAMETER> ...]',)
    examples = ('log clear',
                'log scroll up',
                'log scroll page down',
                'log error Holy crap, Batman!')
    argspecs = (
        {'names': ('ACTION',), 'nargs': 'REMAINDER',
         'description': ('"clear", "scroll", "info" or "error" '
                         '(see the sections below for more information)')},
    )

    more_sections = {'clear': ('Remove all previously logged messages in the TUI.  '
                               'This action ignores all PARAMETERs.',),
                     'scroll': ('Scroll the log messages up or down in the TUI.  '
                                'Valid PARAMETERs are "up", "down", "page up", "page down", '
                                '"top" and "bottom".',),
                     'info': ('Join all PARAMETERs and display them as a normal message.',),
                     'error': ('Join all PARAMETERs and display them as an error message.',)}

    def run(self, ACTION):
        if len(ACTION) < 1:
            raise CmdError('Missing at least one argument')
        elif ACTION[0] == 'clear':
            return self._do('clear', *ACTION[1:])
        elif ACTION[0] == 'scroll':
            return self._do('scroll', *ACTION[1:])
        elif ACTION[0] == 'error':
            self.error(' '.join(ACTION[1:]))
        elif ACTION[0] == 'info':
            self.info(' '.join(ACTION[1:]))
        else:
            self.info(' '.join(ACTION))

    @classmethod
    def completion_candidates_posargs(cls, args):
        """Complete positional arguments"""
        if args.curarg_index == 1:
            return candidates.Candidates(
                (candidates.Candidate(topic, Description=''.join(cls.more_sections[topic]).split('.')[0])
                 for topic in cls.more_sections),
                label='Action')
        elif args.curarg_index == 2 and args[1] == 'scroll':
            return candidates.Candidates(
                (candidates.Candidate('up', Description='Scroll log messages up one line'),
                 candidates.Candidate('down', Description='Scroll log messages down one line'),
                 candidates.Candidate('page up', Description='Scroll log messages up one page'),
                 candidates.Candidate('page down', Description='Scroll log messages down one page'),
                 candidates.Candidate('top', Description='Scroll to top of log messages'),
                 candidates.Candidate('bottom', Description='Scroll to bottom of log messages')),
                label='Action')
