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

"""Mixin classes for TUI commands"""

from ...logging import make_logger
log = make_logger(__name__)


class update_torrentlist():
    def update_torrentlist(self):
        """Reduce polling interval for a few seconds"""
        short_interval = 0.5
        srvapi = self.srvapi
        if srvapi.interval > 1:
            import asyncio
            async def coro():
                log.debug('Setting interval to 0.5 for 2 seconds')
                orig_interval = srvapi.interval
                srvapi.interval = short_interval
                await asyncio.sleep(2, loop=self.aioloop)
                srvapi.interval = orig_interval
                log.debug('Interval restored')
            self.aioloop.create_task(coro())


class make_request():
    async def make_request(self, request_coro, update_torrentlist=False, quiet=False):
        """Awaits request coroutine and logs messages; returns response"""
        response = await request_coro
        self.cmdutils.log_msgs(log, response.msgs, quiet)
        if response.success and update_torrentlist and hasattr(self, 'update_torrentlist'):
            self.update_torrentlist()
        return response


class select_torrents():
    def select_torrents(self, FILTER):
        """Get TorrentFilter instance or torrent IDs from FILTER or focused torrent"""
        tabs = self.tui.tabs
        try:
            filters = self.cmdutils.parseargs_tfilter(FILTER)
        except ValueError as e:
            log.error(e)
        else:
            if filters is None:
                # Try to find focused torrent in focused tab
                if hasattr(self, 'focused_torrent'):
                    return (self.focused_torrent['id'],)
                elif hasattr(tabs.focus, 'focused_torrent') and \
                   tabs.focus.focused_torrent is not None:
                    return (tabs.focus.focused_torrent.tid,)
                else:
                    log.error('No torrent selected')
            else:
                return filters

