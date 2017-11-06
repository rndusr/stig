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

from ..logging import make_logger
log = make_logger(__name__)

import weakref

from . import convert
from .utils import SleepUneasy

from .aiotransmission.rpc import TransmissionRPC
from .aiotransmission.api_status import StatusAPI
from .aiotransmission.api_settings import SettingsAPI
from .aiotransmission.api_torrent import TorrentAPI

from .poll import RequestPoller
from .trequestpool import TorrentRequestPool
from .errors import *
from .utils import lazy_property


class API(convert.bandwidth_mixin, convert.size_mixin):
    """Provide and manage *API classes as singletons

    A convenience class that creates instances of TransmissionRPC, TorrentAPI,
    StatusAPI, TorrentRequestPool and TorrentCounters in a lazy manner on
    demand.
    """

    # Make errors available without having to import them everywhere
    ClientError     = ClientError
    ConnectionError = ConnectionError
    RPCError        = RPCError
    AuthError       = AuthError
    URLParserError  = URLParserError

    def __init__(self, url, interval=1, loop=None):
        if loop is None:
            raise TypeError('Missing argument: loop')
        self.loop = loop
        self._url = url
        self._interval = interval
        self._pollers = []
        self._manage_pollers_interval = SleepUneasy(loop=self.loop)

    @property
    def url(self):
        """URL to API interface"""
        if self.created('rpc'):
            return self.rpc.url
        return self._url

    @url.setter
    def url(self, url):
        self._url = url
        if self.created('rpc'):
            self.rpc.url = url

    @property
    def interval(self):
        """Delay between polls of all pollers"""
        return self._interval

    @interval.setter
    def interval(self, interval):
        self._interval = interval
        for poller in self._existing_pollers:
            poller.interval = interval


    def created(self, prop):
        """Whether property `prop` was created"""
        return hasattr(self, prop+'_created')

    @lazy_property(after_creation=lambda self: setattr(self, 'rpc_created', True))
    def rpc(self):
        """TransmissionRPC singleton"""
        log.debug('Creating RPC singleton')
        return TransmissionRPC(self._url, loop=self.loop)

    @lazy_property(after_creation=lambda self: setattr(self, 'torrent_created', True))
    def torrent(self):
        """TorrentAPI singleton"""
        log.debug('Creating TorrentAPI singleton')
        return TorrentAPI(self.rpc)

    @lazy_property(after_creation=lambda self: setattr(self, 'status_created', True))
    def status(self):
        """StatusAPI singleton"""
        log.debug('Creating StatusAPI singleton')
        return StatusAPI(self, interval=self._interval, autoconnect=True)

    @lazy_property(after_creation=lambda self: setattr(self, 'settings_created', True))
    def settings(self):
        """SettingsAPI singleton"""
        log.debug('Creating SettingsAPI singleton')
        return SettingsAPI(self, interval=self._interval, autoconnect=True)

    @lazy_property(after_creation=lambda self: setattr(self, 'treqpool_created', True))
    def treqpool(self):
        """TorrentRequestPool singleton"""
        log.debug('Creating TorrentRequestPool singleton')
        return TorrentRequestPool(self, interval=self._interval, autoconnect=True)


    def create_poller(self, *args, interval=None, loop=None, **kwargs):
        """Create, start and return custom RequestPoller instance

        All arguments are used to create the poller, except for `interval` and
        `loop`, which are ignored and replaced with this object's `interval`
        and `loop` attributes so all pollers have the same interval.

        The RequestPoller instance is treated like all other pollers, i.e. it
        is polled when `poll` is called, its interval is changed when
        `interval` is set, etc.
        """
        poller = RequestPoller(*args, interval=self.interval, loop=self.loop, **kwargs)
        self._pollers.append(poller)
        self.manage_pollers_now()
        return poller

    async def _manage_pollers(self):
        def is_needed(poller):
            # Whether anyone is still interested in the poller
            try:
                return poller.has_callbacks
            except AttributeError:
                try:
                    return poller.has_subscribers
                except AttributeError:
                    return True

        async def manage():
            for poller in self._existing_pollers:
                if is_needed(poller):
                    if not poller.running:
                        log.debug('  Starting because not running and has callbacks: %r', poller)
                        await poller.start()
                else:
                    if poller.running:
                        log.debug('  Stopping because running and no callbacks: %r', poller)
                        await poller.stop()
                    if poller in self._pollers:
                        self._pollers.remove(poller)

        # To estimate peer download rates, we have to keep track of all the
        # peers' progresses, and we need to prune that data from time to
        # time. It's a bit dirty to put this here, but managing another task
        # just for this isn't much better.
        from .ttypes import gc_peer_progress_data
        while True:
            gc_peer_progress_data()

            log.debug('Managing pollers:')
            await manage()

            # If a poller was added while we were managing the existing
            # pollers, it won't get started until the next interval.  This
            # also solves a weird bug that accumulates unused pollers when
            # rapidly opening and closing file lists.
            while any(not poller.running for poller in self._pollers):
                log.debug('Managing pollers again:')
                await manage()

            await self._manage_pollers_interval.sleep(10)

    def manage_pollers_now(self):
        self._manage_pollers_interval.interrupt()

    # Standard pollers accessible through properties
    _STD_POLLERS = ('status', 'settings', 'treqpool')
    @property
    def _existing_pollers(self):
        for pname in self._STD_POLLERS:
            if self.created(pname):
                yield getattr(self, pname)
        yield from self._pollers

    @property
    def pollers_running(self):
        """Whether pollers are running or not"""
        pollers = tuple(self._existing_pollers)
        if not pollers:
            return False
        return pollers[0].running

    def poll(self):
        """Poll all created and running pollers immediately

        This also resets the interval - the next polls are made `interval`
        seconds later.
        """
        for poller in self._existing_pollers:
            if poller.running:
                poller.poll()

    async def start_polling(self):
        """Start all created pollers"""
        for poller in self._existing_pollers:
            if not poller.running:
                await poller.start()
        self._manage_pollers_task = self.loop.create_task(self._manage_pollers())
        self._manage_pollers_task.add_done_callback(lambda task: task.result())

    async def stop_polling(self):
        """Stop all created pollers"""
        for poller in self._existing_pollers:
            if poller.running:
                await poller.stop()
        self._manage_pollers_task.cancel()
