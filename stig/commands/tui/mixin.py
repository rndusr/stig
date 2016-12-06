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


from .. import ExpectedResource

class polling_frenzy():
    aioloop = ExpectedResource
    def polling_frenzy(self, duration=2, short_interval=0.5):
        """Reduce polling interval for a few seconds

        This affects TorrentListWidgets and FileListWidgets.
        """
        srvapi = self.srvapi
        if srvapi.interval > 1:
            import asyncio
            async def coro():
                log.debug('Setting poll interval to %s for %s seconds', short_interval, duration)
                orig_interval = srvapi.interval
                srvapi.interval = short_interval
                await asyncio.sleep(duration, loop=self.aioloop)
                srvapi.interval = orig_interval
                log.debug('Interval restored to %s', srvapi.interval)
            self.aioloop.create_task(coro())


class make_request():
    async def make_request(self, request_coro, polling_frenzy=False, quiet=False):
        """Awaits request coroutine and logs messages; returns response"""
        response = await request_coro
        self.cmdutils.log_msgs(log, response.msgs, quiet)
        if response.success and polling_frenzy and hasattr(self, 'polling_frenzy'):
            self.polling_frenzy()
        return response


class select_torrents():
    def select_torrents(self, FILTER):
        """Get TorrentFilter instance, focused torrent ID in a tuple or None

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
                tabs = self.tui.tabs

                # Get Torrent object from attribute set by 'tab' command (this
                # happens if for example when you run 'tab filelist' while a
                # torrent is focused)
                if hasattr(self, 'focused_torrent'):
                    return (self.focused_torrent['id'],)

                # Get Torrent object from widget in focused tab
                elif hasattr(tabs.focus, 'focused_torrent') and \
                   tabs.focus.focused_torrent is not None:
                    return (tabs.focus.focused_torrent.tid,)

                # Get torrent ID from widget in focused tab
                elif hasattr(tabs.focus, 'focused_torrent_id') and \
                   tabs.focus.focused_torrent_id is not None:
                    return (tabs.focus.focused_torrent_id,)

                else:
                    log.error('No torrent selected')
            else:
                return filters


class select_files():
    def select_files(self, FILTER, default_to_focused=False):
        """Get TorrentFileFilter instance, focused file ID or None"""
        try:
            filters = self.cmdutils.parseargs_ffilter(FILTER)
        except ValueError as e:
            log.error(e)
        else:
            if filters is not None:
                return filters
            elif default_to_focused:
                tabs = self.tui.tabs

                # Get torrent ID from widget in focused tab
                if hasattr(tabs.focus, 'focused_file_id') and \
                   tabs.focus.focused_file_id is not None:
                    return (tabs.focus.focused_file_id,)
