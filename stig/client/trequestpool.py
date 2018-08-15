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

import blinker
import operator
from functools import reduce

from .poll import RequestPoller


class TorrentRequestPool(RequestPoller):
    """Combine multiple `TorrentAPI.torrents` requests into one

    The wanted Torrent keys from all subscribers are combined and added to the
    needed keys for TorrentFilter from all subscribers.

    After the combined torrents have arrived, split it back up by using each
    subscriber's filter and provide it to its callbacks as tuples.
    """
    def __init__(self, srvapi, interval=1):
        self._api = srvapi.torrent
        self._tfilters = {}
        self._keys = {}
        super().__init__(request=None, interval=interval, loop=srvapi.loop)
        self.on_response(self._handle_torrent_list)

    def register(self, sid, callback, keys=(), tfilter=None):
        """Add new request to request pool

        sid: Subscriber ID (any hashable)
        callback: Callable that receives a tuple of Torrents on updates
        keys: Wanted Torrent keys
        tfilter: None for all torrents or TorrentFilter instance
        """
        log.debug('Registering subscriber: %s', sid)
        event = blinker.signal(sid)
        event.connect(callback)
        self._keys[event] = set(keys)
        self._tfilters[event] = tfilter

        # It's possible that a currently ongoing request doesn't collect the
        # keys this new callback needs.  In that case, the request is finished
        # AFTER we added the callback, and the callback would be called with
        # lacking keys, resuling in a KeyError.
        # Therefore we ask the poller to dump the result of a currently
        # ongoing request to prevent this.
        if self.running:
            self.skip_ongoing_request()

        self._combine_requests()

    def _combine_requests(self):
        """Create single request that combines keys and filters of all subscribers"""
        if not self.has_subscribers:
            # Don't request anything
            log.debug('No subscribers - setting request to None')
            self.set_request(None)
        else:
            kwargs = {}

            all_filters = tuple(self._tfilters.values())
            if not all_filters or None in all_filters:
                # No subscribers or at least one subscriber wants all torrents
                kwargs['torrents'] = None
            else:
                kwargs['torrents'] = reduce(operator.__or__, all_filters)

            # Combine keys of all requests
            kwargs['keys'] = reduce(lambda a,b: {*a,*b}, self._keys.values())

            # Filters also need certain keys
            for f in all_filters:
                if f is not None:
                    kwargs['keys'].update(f.needed_keys)

            log.debug('Combined filters: %s', kwargs['torrents'])
            log.debug('Combined keys: %s', kwargs['keys'])
            self.set_request(self._api.torrents, **kwargs)

    def _handle_torrent_list(self, response):
        # If the request failed, response is None and tlist is empty.
        tlist = response.torrents if response is not None else ()

        dead_subscribers = []
        def send(event, tlist):
            if not bool(event.receivers):
                dead_subscribers.append(event.name)
            else:
                log.debug('Running callback: %r', event.name)
                event.send(tlist)

        log.debug('Processing %d torrents for %d subscribers',
                  len(tlist), len(self._tfilters))
        if len(self._tfilters) == 1:
            # If there's only one subscriber, there's no need to filter the
            # torrents again.
            event = next(iter(self._tfilters))
            send(event, tlist)
        else:
            # More than 1 subscriber means we have to filter the torrents
            # again for each one.
            for event,filter in self._tfilters.items():
                if filter is None:
                    # Subscriber wants all torrents
                    this_tlist = tlist
                else:
                    # Subscriber wants filtered torrents
                    this_tlist = filter.apply(tlist)
                send(event, this_tlist)

        # Remove dead subscribers
        for eventname in dead_subscribers:
            self.remove(eventname)

    def remove(self, sid):
        """Unsubscribe previously registered subscriber"""
        log.debug('Removing subscriber: %s', sid)
        event = blinker.signal(sid)
        del self._keys[event]
        del self._tfilters[event]
        self._combine_requests()

    @property
    def has_subscribers(self):
        """Whether any subscribers are registered"""
        return bool(self._tfilters)

    def requested_keys(self, sid):
        """Return keys requested by subscriber"""
        event = blinker.signal(sid)
        try:
            return self._keys[event]
        except KeyError:
            return ()
