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

"""Mixin classes for CLI commands"""

from ...logging import make_logger
log = make_logger(__name__)


class make_request():
    async def make_request(self, request_coro, update_torrentlist=False, quiet=False):
        """Awaits request coroutine and logs messages; returns response"""
        response = await request_coro
        self.cmdutils.log_msgs(log, response.msgs, quiet)
        return response


class make_selection():
    def make_selection(self, FILTER):
        """Get TorrentFilter instance or IDs from arguments"""
        try:
            filters = self.cmdutils.parseargs_filter(FILTER)
        except ValueError as e:
            log.error(e)
        else:
            if filters is None:
                log.error('No torrent specified')
            else:
                return filters
