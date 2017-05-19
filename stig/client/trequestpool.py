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
from collections import abc

from .poll import RequestPoller
from .filters.tfilter import TorrentFilter


class TorrentRequestPool():
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
        self._poller = RequestPoller(request=self._api.torrents,
                                     autoconnect=False,
                                     interval=interval,
                                     loop=srvapi.loop)
        self._poller.on_response(self._handle_tlist)

    def register(self, sid, callback, keys=(), tfilter=None):
        """Add new request to request pool

        sid: Subscriber ID (any hashable)
        callback: Callable that receives a tuple of Torrents on updates
        keys: Wanted Torrent keys
        tfilter: None for all torrents or TorrentFilter instance
        """
        if isinstance(tfilter, abc.Sequence):
            tfilter = TorrentFilter('|'.join('id=%s' % tid for tid in tfilter))

        log.debug('Registering subscriber: %s', sid)
        event = blinker.signal(sid)
        event.connect(callback)
        self._keys[event] = tuple(keys)
        self._tfilters[event] = tfilter

        # It's possible that a currently ongoing request doesn't collect the
        # keys this new callback needs.  In that case, the request is finished
        # AFTER we added the callback, and the callback would be called with
        # lacking keys, resuling in a KeyError.
        # Therefore we ask the poller to dump the result of a currently
        # ongoing request to prevent this.
        if self._poller.running:
            self._poller.skip_ongoing_request()

        self._combine_requests()

    def _combine_requests(self):
        """Create single request that combines keys and filters of all subscribers"""
        if not self.has_subscribers:
            # Don't request anything
            log.debug('No subscribers - setting request to None')
            self._poller.set_request(None)
        else:
            kwargs = {}

            all_filters = tuple(self._tfilters.values())
            if not all_filters or None in all_filters:
                # No subscribers or at least one subscriber wants all torrents
                kwargs['torrents'] = None
            else:
                kwargs['torrents'] = reduce(operator.__add__, all_filters)

            kwargs['keys'] = reduce(operator.__add__, self._keys.values())
            # Filters also need certain keys
            for f in all_filters:
                if f is not None:
                    kwargs['keys'] += f.needed_keys

            kwargs['keys'] = tuple(set(kwargs['keys']))
            log.debug('Combined filters: %s', kwargs['torrents'])
            log.debug('Combined keys: %s', kwargs['keys'])
            self._poller.set_request(self._api.torrents, **kwargs)

    def _handle_tlist(self, response):
        # If the request failed, response is None and tlist is empty.
        tlist = response.torrents if response is not None else ()

        dead_subscribers = []
        def has_subscribers(event):
            if not bool(event.receivers):
                dead_subscribers.append(event.name)
                return False
            else:
                return True

        log.debug('Processing %d torrents for %d subscribers',
                  len(tlist), len(self._tfilters))
        if len(self._tfilters) == 1:
            # If there's only one subscriber, there's no need to filter the
            # torrents again.
            event = next(iter(self._tfilters))
            if has_subscribers(event):
                log.debug('Running callback: %r', event.name)
                event.send(tlist)
        else:
            # More than 1 subscriber means we have to filter the torrents
            # again for each one.
            for event,filter in self._tfilters.items():
                if has_subscribers(event):
                    log.debug('Running callback: %r', event.name)
                    if filter is None:
                        # Subscriber wants all torrents
                        this_tlist = tlist
                    else:
                        # Subscriber wants filtered torrents
                        this_tlist = filter.apply(tlist)
                    event.send(this_tlist)

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

    def __getattr__(self, attr):
        if attr in ('start', 'stop', 'poll', 'running'):
            return getattr(self._poller, attr)
        raise AttributeError('{!r} object has no attribute {!r}'
                             .format(type(self).__name__, attr))

    @property
    def interval(self):
        return self._poller.interval

    @interval.setter
    def interval(self, interval):
        self._poller.interval = interval
