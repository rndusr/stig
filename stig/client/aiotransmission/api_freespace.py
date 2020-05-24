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

from types import SimpleNamespace

import blinker

from stig.utils import convert

from ..errors import TimeoutError
from ..poll import RequestPoller

from ...logging import make_logger  # isort:skip
log = make_logger(__name__)


class DirectorySpaceWatcher():
    """
    Directory space watcher on a directory defined in the Transmission settings
    """

    async def start(self, *args, **kwargs):
        await self._poller_dirname.start(*args, **kwargs)
        await self._poller_size.start(*args, **kwargs)

    async def stop(self, *args, **kwargs):
        await self._poller_dirname.stop(*args, **kwargs)
        await self._poller_size.stop(*args, **kwargs)

    def poll(self, *args, **kwargs):
        self._poller_dirname.poll(*args, **kwargs)
        self._poller_size.poll(*args, **kwargs)

    @property
    def running(self):
        return self._poller_size.running

    @property
    def interval(self):
        return self._poller_size.interval

    @interval.setter
    def interval(self, interval):
        self._poller_dirname.interval = interval
        self._poller_size.interval = interval

    def __init__(self, srvapi, setting_poller, interval=1):
        self._srvapi = srvapi
        self._on_update = blinker.Signal()

        self._poller_dirname = RequestPoller(setting_poller,
                                             interval=interval)
        self._poller_dirname.on_response(self._handle_dirname)
        self._poller_dirname.on_error(self._handle_dirname_error,
                                      autoremove=False)

        self._poller_size = RequestPoller(srvapi.rpc.free_space,
                                          path="",
                                          interval=interval)
        self._poller_size.on_response(self._handle_size)
        self._poller_size.on_error(self._handle_size_error,
                                   autoremove=False)

        self.space_info = SimpleNamespace(path=None,
                                          size=None)

    def _handle_dirname(self, path):
        if path is not None and path != "disabled":
            self.space_info.path = path
            self._poller_size.skip_ongoing_request()
            self._poller_size.set_request(self._srvapi.rpc.free_space,
                                          path=path)

    def _handle_dirname_error(self, error):
        log.debug('Ignoring exception: %r', error)

    def _handle_size(self, response):
        if response is not None \
           and self.space_info.path == response['path']:
            self.space_info.size = convert.size(response['size-bytes'], unit='byte')
            self._on_update.send(self.space_info)

    def _handle_size_error(self, error):
        if not self.space_info.path \
           or isinstance(error, TimeoutError):
            log.debug('Ignoring exception: %r', error)
        else:
            raise error

    def on_update(self, callback, autoremove=True):
        """
        Register `callback` to be called when free space has changed

        `callback` gets the instance of this class.

        If `autoremove` is True, `callback` is removed automatically when it is
        deleted.
        """
        log.debug('Registering %r to receive updates about free space', callback)
        self._on_update.connect(callback, weak=autoremove)


class FreeSpaceAPI():
    """
    Transmission daemon free space method handler
    """

    async def start(self, *args, **kwargs):
        await self._watcher_complete.start(*args, **kwargs)
        await self._watcher_incomplete.start(*args, **kwargs)

    async def stop(self, *args, **kwargs):
        await self._watcher_complete.stop(*args, **kwargs)
        await self._watcher_incomplete.stop(*args, **kwargs)

    def poll(self, *args, **kwargs):
        self._watcher_complete.poll(*args, **kwargs)
        self._watcher_incomplete.poll(*args, **kwargs)

    @property
    def running(self):
        return self._watcher_incomplete.running \
               and self._watcher_incomplete.running

    @property
    def interval(self):
        return self._watcher_complete.interval

    @interval.setter
    def interval(self, interval):
        self._watcher_complete.interval = interval
        self._watcher_incomplete.interval = interval

    @property
    def complete_info(self):
        return self._watcher_complete.space_info

    @property
    def incomplete_info(self):
        return self._watcher_incomplete.space_info

    def __init__(self, srvapi, interval=1):
        self._on_update = blinker.Signal()

        self._watcher_complete = DirectorySpaceWatcher(srvapi,
                                                       srvapi.settings.get_path_complete,
                                                       interval)
        self._watcher_complete.on_update(self._send_update)

        self._watcher_incomplete = DirectorySpaceWatcher(srvapi,
                                                         srvapi.settings.get_path_incomplete,
                                                         interval)
        self._watcher_incomplete.on_update(self._send_update)

    def _send_update(self, *args):
        log.debug('Free space: %r / %r',
                  self.complete_info, self.incomplete_info)
        self._on_update.send(self)

    def on_update(self, callback, autoremove=True):
        """
        Register `callback` to be called when free space has changed

        `callback` gets the instance of this class.

        If `autoremove` is True, `callback` is removed automatically when it is
        deleted.
        """
        log.debug('Registering %r to receive updates about free space', callback)
        self._on_update.connect(callback, weak=autoremove)
