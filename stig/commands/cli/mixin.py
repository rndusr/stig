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
    async def make_request(self, request_coro, polling_frenzy=False, quiet=False):
        """Awaits request coroutine and logs messages; returns response"""
        response = await request_coro
        self.cmdutils.log_msgs(log, response.msgs, quiet)
        return response


class select_torrents():
    def select_torrents(self, FILTER):
        """Get TorrentFilter instance or None

        `FILTER` is an argument for TorrentFilter.

        Returns a TorrentFilter instance or None if `FILTER` evaluates to
        False.
        """
        try:
            filters = self.cmdutils.parseargs_tfilter(FILTER)
        except ValueError as e:
            log.error(e)
        else:
            if filters is None:
                log.error('No torrent specified')
            else:
                return filters


class select_files():
    def select_files(self, FILTER, default_to_focused=False):
        """Get TorrentFileFilter instance or None"""
        try:
            return self.cmdutils.parseargs_ffilter(FILTER)
        except ValueError as e:
            log.error(e)
        else:
            return None
