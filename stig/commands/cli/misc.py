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

"""Documentation commands"""

from ...logging import make_logger
log = make_logger(__name__)

from ..base import misc as base
from .. import (ExpectedResource, CmdError)

class HelpCmd(base.HelpCmdbase):
    provides = {'cli'}
    srvapi = ExpectedResource

    async def run(self, TOPIC):
        # If TOPIC is a setting and it is managed by the server, we must fetch
        # config values from the server so we can display its current value.
        for topic in TOPIC:
            if topic.startswith('srv.'):
                try:
                    await self.srvapi.settings.update()
                except self.srvapi.ClientError as e:
                    self.error(e)
                finally:
                    break
        return super().run(TOPIC)

    def display_help(self, topics, lines):
        for line in lines:
            print(line)


class VersionCmd(base.VersionCmdbase):
    provides = {'cli'}


class LogCmd(base.LogCmdbase):
    provides = {'cli'}

    def _do(self, action, *args):
        cmd_str = '%s %s' % (action, ' '.join(args))
        raise CmdError('Unsupported command in CLI mode: %s' % cmd_str)
