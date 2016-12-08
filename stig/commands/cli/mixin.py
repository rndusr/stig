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

from .. import ExpectedResource
from .. import utils


class make_request():
    async def make_request(self, request_coro, polling_frenzy=False, quiet=False):
        """Awaits request coroutine and logs messages; returns response"""
        response = await request_coro
        utils.log_msgs(log, response.msgs, quiet)
        return response


class select_torrents():
    def select_torrents(self, FILTER, allow_no_filter=True, discover_torrent=None):
        """Get TorrentFilter instance or None

        If `FILTER` evaluates to True, it is passed to TorrentFilter and the
        resulting object is returned.

        If `FILTER` evaluates to False, None is returned if allow_no_filter
        evaluates to True, otherwise a ValueError is raised.

        `discover_torrent` is ignored and only used in the TUI version of this
        method (see ..tui.mixin.select_torrent).
        """
        if FILTER:
            from ...client import TorrentFilter
            return TorrentFilter(FILTER)
        else:
            if allow_no_filter:
                return None
            else:
                raise ValueError('No torrent specified')


class select_files():
    def select_files(self, FILTER, allow_no_filter=True, discover_file=None):
        """Get TorrentFileFilter instance or None

        If `FILTER` evaluates to True, it is passed to TorrentFileFilter and
        the resulting object is returned.

        If `FILTER` evaluates to False, None is returned if allow_no_filter
        evaluates to True, otherwise a ValueError is raised.

        `discover_file` is ignored and only used in the TUI version of this
        method (see ..tui.mixin.select_file).
        """
        if FILTER:
            from ...client import TorrentFileFilter
            return TorrentFileFilter(FILTER)
        else:
            if allow_no_filter:
                return None
            else:
                raise ValueError('No torrent specified')
