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

from .errors import *
from .constants import *

from .utils import Response

from .tfilter import TorrentFilter
from .tsort import TorrentSorter

from .poll import RequestPoller
from .trequestpool import TorrentRequestPool

from .aiotransmission.rpc import TransmissionRPC
from .aiotransmission.api_status import StatusAPI
from .aiotransmission.api_settings import SettingsAPI
from .aiotransmission.api_torrent import TorrentAPI


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
        return value


from . import convert

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

    POLLERS = ('status', 'settings', 'treqpool')
    @property
    def _existing_pollers(self):
        for pname in self.POLLERS:
            if self.created(pname):
                yield getattr(self, pname)

    @property
    def interval(self):
        """Delay between polls of all pollers"""
        return self._interval

    @interval.setter
    def interval(self, interval):
        self._interval = interval
        for poller in self._existing_pollers:
            poller.interval = interval

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

    async def stop_polling(self):
        """Stop all created pollers"""
        for poller in self._existing_pollers:
            if poller.running:
                await poller.stop()
