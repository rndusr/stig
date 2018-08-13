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
from collections import namedtuple

from ..poll import RequestPoller
from ..utils import (convert, const)


TorrentCount = namedtuple('TorrentCount', ('active', 'downloading', 'isolated',
                                           'stopped', 'total', 'uploading'))


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
                                           interval=interval,
                                           loop=srvapi.loop)
        self._poller_stats.on_response(self._handle_session_stats)
        self._poller_stats.on_error(lambda e: log.debug('Ignoring exception: %r', e),
                                    autoremove=False)

        # 'session-stats' provides some counters, but not enough, so we
        # request a minimalistic torrent list.
        self._poller_tcount = RequestPoller(srvapi.torrent.torrents,
                                            keys=('rate-down', 'rate-up', 'status'),
                                            interval=interval,
                                            loop=srvapi.loop)
        self._poller_tcount.on_response(self._handle_torrent_list)

    def _reset_session_stats(self):
        self._session_stats = None

    def _reset_tcounts(self):
        self._torrent_list = None

    def _handle_session_stats(self, stats):
        if stats is None:
            self._reset_session_stats()
        else:
            self._session_stats = stats
        self._session_stats_updated = True
        self._maybe_run_callbacks()

    def _handle_torrent_list(self, response):
        if response is None:
            self._reset_tcounts()
        else:
            self._torrent_list = response.torrents
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
        """
        Register `callback` to be called at intervals

        `callback` is passed the instance of this class.  If `autoremove` is
        True, `callback` is stored as a weakref and removed automatically when
        it is deleted.
        """
        log.debug('Registering %r to receive status updates', callback)
        self._on_update.connect(callback, weak=autoremove)

    @property
    def count(self):
        """Torrent counts by category"""
        stats = self._session_stats
        tlist = self._torrent_list
        tc_args = {field:const.DISCONNECTED for field in TorrentCount._fields}
        if stats is not None:
            tc_args.update(
                total=stats['torrentCount'],
                stopped=stats['pausedTorrentCount'],
                active=stats['activeTorrentCount']
            )
        if tlist is not None:
            from ..ttypes import Status
            ISOLATED = Status.ISOLATED
            tc_args.update(
                isolated=len(tuple(filter(lambda t: ISOLATED in t['status'], tlist))),
                downloading=len(tuple(filter(lambda t: t['rate-down'] > 0, tlist))),
                uploading=len(tuple(filter(lambda t: t['rate-up'] > 0, tlist)))
            )
        return TorrentCount(**tc_args)

    def _get_transfer_rate(self, direction):
        stats = self._session_stats
        if stats is None:
            return const.DISCONNECTED
        else:
            return convert.bandwidth(self._session_stats[direction + 'loadSpeed'], unit='B')

    @property
    def rate_down(self):
        """Total download rate or `constants.DISCONNECTED`"""
        return self._get_transfer_rate('down')

    @property
    def rate_up(self):
        """Total upload rate or `constants.DISCONNECTED`"""
        return self._get_transfer_rate('up')
