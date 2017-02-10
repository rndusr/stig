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


# https://stackoverflow.com/a/6849299
class _lazy_property():
    """Property that replaces itself with the requested object"""

    def __init__(self, fget):
        self.fget = fget
        self.func_name = fget.__name__

    def __get__(self, obj, cls):
        if obj is None:
            return None
        value = self.fget(obj)
        setattr(obj, self.func_name, value)
        setattr(obj, self.func_name + '_created', True)
        obj.manage_pollers_now()
        return value


class API(convert.bandwidth_mixin, convert.size_mixin):
    """Provide and manage *API classes as singletons

    A convenience class that creates instances of TransmissionRPC, TorrentAPI,
    StatusAPI, TorrentRequestPool and TorrentCounters in a lazy manner on
    demand.
    """
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

    def created(self, prop):
        """Whether property `prop` was created"""
        return hasattr(self, prop+'_created')

    @_lazy_property
    def rpc(self):
        """TransmissionRPC singleton"""
        log.debug('Creating RPC singleton')
        return TransmissionRPC(self._url, loop=self.loop)

    @_lazy_property
    def torrent(self):
        """TorrentAPI singleton"""
        log.debug('Creating TorrentAPI singleton')
        return TorrentAPI(self.rpc)

    @_lazy_property
    def status(self):
        """StatusAPI singleton"""
        log.debug('Creating StatusAPI singleton')
        return StatusAPI(self, interval=self._interval)

    @_lazy_property
    def settings(self):
        """SettingsAPI singleton"""
        log.debug('Creating SettingsAPI singleton')
        return SettingsAPI(self, interval=self._interval)

    @_lazy_property
    def treqpool(self):
        """TorrentRequestPool singleton"""
        log.debug('Creating TorrentRequestPool singleton')
        return TorrentRequestPool(self, interval=self._interval)

    def create_poller(self, *args, interval=None, loop=None, **kwargs):
        """Create, start and return new RequestPoller instance

        All arguments are used to create the poller, except for `interval` and
        `loop`, which are ignored and replaced with this object's `interval`
        and `loop` attributes.

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
                running = poller.running
                needed = is_needed(poller)

                if not running and needed:
                    log.debug('Starting because not running and has callbacks: %r', poller)
                    await poller.start()
                elif running and not needed:
                    log.debug('Stopping because running and no callbacks: %r', poller)
                    await poller.stop()
                    if poller in self._pollers:
                        self._pollers.remove(poller)

        # To estimate peer download rates, we have to keep track of all the
        # peers' progresses, and we need to prune that data from time to
        # time. It's a bit dirty to put this here, but managing another task
        # just for this isn't much better.
        from .tkeys import gc_peer_progress_data
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
    def interval(self):
        """Delay between polls of all pollers"""
        return self._interval

    @interval.setter
    def interval(self, interval):
        self._interval = interval
        for poller in self._existing_pollers:
            poller.interval = interval

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
