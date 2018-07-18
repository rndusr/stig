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

from ...logging import make_logger
log = make_logger(__name__)

from .. import (InitCommand, CmdError, ExpectedResource)
from ... import (__appname__, __version__)


class HelpCmdbase(metaclass=InitCommand):
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
        { 'names': ('TOPIC',), 'nargs': '*',
          'description': 'Name of command, setting or category' },
    )
    helpmgr = ExpectedResource

    TOPIC_DELIMITER = ['', '-  '*20, '']

    def run(self, TOPIC):
        topics = TOPIC
        lines = []
        success = True
        existing_topics = []

        if len(topics) < 1:
            lines = self.helpmgr.overview
        else:
            for topic in topics:
                try:
                    l = self.helpmgr.find(topic)
                except ValueError as e:
                    self.error(e)
                    success = False
                else:
                    lines.extend(l)
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


class VersionCmdbase(metaclass=InitCommand):
    name = 'version'
    category = 'miscellaneous'
    provides = set()
    description = 'Show {} version'.format(__appname__)

    def run(self):
        print('%s ersion %s' % (__appname__, __version__))


class LogCmdbase(metaclass=InitCommand):
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
        { 'names': ('ACTION',), 'nargs': 'REMAINDER',
          'description': ('"clear", "scroll", "info" or "error" '
                          '(see the sections below for more information)') },
    )

    more_sections = { 'clear': ('Remove all previously logged messages in the TUI.  '
                                'This action ignores all PARAMETERs.',),
                      'scroll': ('Scroll the log messages up or down in the TUI.  '
                                 'Valid PARAMETERs are "up", "down", "page up", "page down", '
                                 '"top" and "bottom".',),
                      'info': ('Join all PARAMETERs and display them as a normal message.',),
                      'error': ('Join all PARAMETERs and display them as an error message.',) }

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
