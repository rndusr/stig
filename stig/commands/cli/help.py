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

from ..base import help as base


class HelpCmd(base.HelpCmdbase):
    provides = {'cli'}

    async def run(self, TOPIC):
        from ...settings import is_server_setting
        for topic in TOPIC:
            if is_server_setting(topic):
                from ...main import srvapi
                from ...client import ClientError
                try:
                    await srvapi.settings.update()
                except ClientError as e:
                    log.error(str(e))
                finally:
                    break
        return super().run(TOPIC)

    def display_help(self, topics, lines):
        for line in lines:
            log.info(line)


class VersionCmd(base.VersionCmdbase):
    provides = {'cli'}
