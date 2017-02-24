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

from .. import (InitCommand, ExpectedResource)
from ... import (APPNAME, __version__)

TOPIC_DELIMITER = ['', '='*50, '']

class HelpCmdbase(metaclass=InitCommand):
    name = 'help'
    aliases = ('man',)
    category = 'misc'
    provides = set()
    description = 'List or explain commands and settings'
    usage = ('help [<TOPIC> <TOPIC> <TOPIC> ...]',)
    examples = ('help',
                'help help')
    argspecs = (
        { 'names': ('TOPIC',), 'nargs': '*',
          'description': 'Name of command, setting or category' },
    )
    helpmgr = ExpectedResource

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
                    log.error(e)
                    success = False
                else:
                    lines.extend(l)
                    lines.extend(TOPIC_DELIMITER)
                    existing_topics.append(topic)

            if lines:
                # Remove last TOPIC_DELIMITER
                for _ in range(len(TOPIC_DELIMITER)):
                    lines.pop(-1)

        if not existing_topics:
            existing_topics.append(APPNAME)

        self.display_help(existing_topics, lines)
        return success


class VersionCmdbase(metaclass=InitCommand):
    name = 'version'
    category = 'misc'
    provides = set()
    description = 'Show {} version'.format(APPNAME)

    def run(self):
        log.info('{} version {}'.format(APPNAME, __version__))
        return True
