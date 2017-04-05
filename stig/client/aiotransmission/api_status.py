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

from ...logging import make_logger
log = make_logger(__name__)

import blinker
from types import SimpleNamespace

from ..poll import RequestPoller
from .. import convert
from .. import constants as const


class StatusAPI():
    """Transmission daemon status information"""

    # Pass poller methods through to our pollers
    async def start(self, *args, **kwargs):
        await self._poller_stats.start(*args, **kwargs)
        await self._poller_tcount.start(*args, **kwargs)

    async def stop(self, *args, **kwargs):
        await self._poller_stats.stop(*args, **kwargs)
        await self._poller_tcount.stop(*args, **kwargs)

    def poll(self, *args, **kwargs):
        self._poller_stats.poll(*args, **kwargs)
        self._poller_tcount.poll(*args, **kwargs)

    @property
    def running(self):
        return self._poller_stats.running

    @property
    def interval(self):
        return self._poller_stats.interval

    @interval.setter
    def interval(self, interval):
        self._poller_stats.interval = interval
        self._poller_tcount.interval = interval


    def __init__(self, srvapi, interval=1):
        self._session_stats_updated = False
        self._tcounts_updated = False
        self._reset_session_stats()
        self._reset_tcounts()
        self._on_update = blinker.Signal()

        self._poller_stats = RequestPoller(srvapi.rpc.session_stats,
                                           autoconnect=False,
                                           interval=interval,
                                           loop=srvapi.loop)
        self._poller_stats.on_response(self._handle_session_stats)
        self._poller_stats.on_error(lambda e: log.debug('Ignoring exception: %r', e),
                                    autoremove=False)

        # 'session-stats' provides some counters, but not enough, so we
        # request a minimalistic torrent list.
        self._poller_tcount = RequestPoller(srvapi.torrent.torrents,
                                            keys=('rate-down', 'rate-up', 'status'),
                                            autoconnect=False,
                                            interval=interval,
                                            loop=srvapi.loop)
        self._poller_tcount.on_response(self._handle_tlist)

    def _reset_session_stats(self):
        self._session_stats = {}

    def _reset_tcounts(self):
        self._tcounts = SimpleNamespace(
            active=const.DISCONNECTED, downloading=const.DISCONNECTED, isolated=const.DISCONNECTED,
            stopped=const.DISCONNECTED, total=const.DISCONNECTED, uploading=const.DISCONNECTED)

    def _handle_session_stats(self, stats):
        if stats is None:
            self._reset_session_stats()
        else:
            self._session_stats = stats
            self._tcounts.total = stats['torrentCount']
            self._tcounts.stopped = stats['pausedTorrentCount']
            self._tcounts.active = stats['activeTorrentCount']
        self._session_stats_updated = True
        self._maybe_run_callbacks()

    def _handle_tlist(self, response):
        if response is None:
            self._reset_tcounts()
        else:
            tlist = response.torrents
            self._tcounts.isolated = len(tuple(filter(
                lambda t: t['status'].ISOLATED in t['status'],
                tlist)))
            self._tcounts.downloading = len(tuple(filter(
                lambda t: t['rate-down'] > 0,
                tlist)))
            self._tcounts.uploading = len(tuple(filter(
                lambda t: t['rate-up'] > 0,
                tlist)))
        self._tcounts_updated = True
        self._maybe_run_callbacks()

    def _maybe_run_callbacks(self):
        # We have two pollers, but we want to call callbacks once when both
        # have an update to report.
        if self._tcounts_updated and self._session_stats_updated:
            self._on_update.send(self)
            self._tcounts_updated = False
            self._session_stats_updated = False

    def on_update(self, callback, autoremove=True):
        """Register `callback` to be called at intervals

        `callback` is passed the instance of this class.  If `autoremove` is
        True, `callback` is stored as a weakref and removed automatically when
        it is deleted.
        """
        log.debug('Registering %r to receive status updates', callback)
        self._on_update.connect(callback, weak=autoremove)

    @property
    def count(self):
        """Torrent counts by category"""
        return self._tcounts

    @property
    def rate_down(self):
        """Total download rate or `constants.DISCONNECTED`"""
        if 'downloadSpeed' in self._session_stats:
            return convert.bandwidth(self._session_stats['downloadSpeed'])
        else:
            return const.DISCONNECTED

    @property
    def rate_up(self):
        """Total upload rate or `constants.DISCONNECTED`"""
        if 'downloadSpeed' in self._session_stats:
            return convert.bandwidth(self._session_stats['uploadSpeed'])
        else:
            return const.DISCONNECTED
