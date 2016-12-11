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

import asyncio
import functools
import blinker

from . import errors
from .utils import (SleepUneasy, PerfectInterval)


def _funcname(func, *posargs, **kwargs):
    if hasattr(func, '__qualname__'):
        name = func.__qualname__
    elif hasattr(func, '__name__'):
        name = func.__name__
    else:
        name = repr(func)

    args = []
    if posargs:
        args.append(', '.join(repr(arg) for arg in posargs))
    if kwargs:
        args.append(', '.join('%s=%r' % (k,v) for k,v in kwargs.items()))

    name += '(' + ', '.join(args) + ')'
    return name


class RequestPoller():
    """Continuously send request and publish the response

    request: Coroutine that is called at intervals
    interval: Delay between calls
    loop: Asyncio loop

    Any other positional or keyword arguments are passed to `request`.
    """
    def __init__(self, request, *args, interval=1, loop=None, **kwargs):
        self.loop = loop if loop is not None else asyncio.get_event_loop()
        self._on_response = blinker.Signal()
        self._on_error = blinker.Signal()
        self._prev_error = None
        self._interval = interval
        self._poll_task = None
        self._poll_loop_task = None
        self._sleep = SleepUneasy(loop=loop)
        self._skip_ongoing_request = False
        self.set_request(request, *args, **kwargs)

    async def start(self):
        """Start polling"""
        if self.running:
            log.debug('Already polling: %s', self._request_str)
        else:
            log.debug('Starting polling: %s', self._request_str)
            self._poll_loop_task = self.loop.create_task(self._poll_loop())
            def reraise(task):
                log.debug('Polling loop is finished: %s', self._request_str)
                # Ignore if _poll_loop() was cancelled, raise all other exceptions
                try:
                    task.result()
                except asyncio.CancelledError:
                    pass
            self._poll_loop_task.add_done_callback(reraise)

    async def _poll_loop(self):
        self._prev_error = None
        while True:
            pinterval = PerfectInterval(self.loop)

            self._poll_task = self.loop.create_task(self._do_poll())
            try:
                await self._poll_task
            except asyncio.CancelledError:
                if self._skip_ongoing_request:
                    log.debug('Skipping polling result once: %s', self._request_str)
                    continue  # Skip the sleep() at the end of the loop
                else:
                    raise
            else:
                log.debug('Finished polling gracefully: %s', self._request_str)
            finally:
                self._poll_task = None
                self._skip_ongoing_request = False

            await self._sleep.sleep(pinterval(self._interval))

    async def _do_poll(self):
        """Send request and send response or error

        The return value from the request is passed to the 'response' event
        handlers.

        Exceptions raised by the request are passed to the 'error' handlers,
        and, except for `ConnectionError`, `stop` is called.
        """
        if self._request is None:
            log.debug('Request is set to None - not requesting anything')
        else:
            log.debug('Polling: %s', self._request_str)
            try:
                response = await self._request()
            except asyncio.CancelledError:
                # In _poll_loop(), abort waiting for poll_task.
                raise
            except errors.ClientError as e:
                # Report error but keep trying to connect
                self._run_callbacks(error=e)
            else:
                self._run_callbacks(response=response)

    def _run_callbacks(self, response=None, error=None):
        if self._skip_ongoing_request:
            log.debug('Not running callbacks for: %s', self._request_str)
            self._skip_ongoing_request = False
        else:
            log.debug('Running callbacks for: %s', self._request_str)
            self._on_response.send(response)
            # Ignore duplicate errors
            if error is not None and str(self._prev_error) != str(error):
                self._prev_error = error
                if self._on_error.receivers:
                    self._on_error.send(error)
                else:
                    log.debug('Uncaught exception in %r', self)
                    raise error

    def skip_ongoing_request(self):
        """Stop a currently ongoing request; do nothing if there is no ongoing request"""
        if self._poll_task is not None:
            log.debug('Skipping ongoing request: %s', self._request_str)
            self._skip_ongoing_request = True
            self._poll_task.cancel()

    async def stop(self):
        """Stop polling"""
        if not self.running:
            log.debug('Already stopped polling: %s', self._request_str)
        else:
            log.debug('Stopping polling %s', self._request_str)
            self._poll_loop_task.cancel()
            try:
                await asyncio.wait_for(self._poll_loop_task, timeout=0, loop=self.loop)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            finally:
                self._poll_loop_task = None
                self._run_callbacks()

    def __del__(self):
        if self._poll_loop_task is not None:
            raise RuntimeError('You forgot to call stop() on {!r}'.format(self))

    def poll(self):
        """Poll immediately instead of waiting for next interval

        This also resets the interval - the next request is made `interval`
        seconds after this method is called.

        Do nothing if this poller is not started.
        """
        if self.running:
            self._sleep.interrupt()

    @property
    def running(self):
        """Whether poller is polling"""
        return self._poll_loop_task is not None

    def set_request(self, request, *args, **kwargs):
        """Set request to coroutine `request`

        Any positional or keyword arguments are passed to `request` at each
        call.
        """
        self._request_str = _funcname(request, *args, **kwargs)
        log.debug('Setting new request: %s', self._request_str)
        if args or kwargs:
            self._request = functools.partial(request, *args, **kwargs)
        else:
            self._request = request

    @property
    def request(self):
        """The request coroutine sent every interval

        If any arguments were given, this is a partial object.
        """
        return self._request

    def on_response(self, callback, autoremove=True):
        """Register `callback` to receive responses

        callback: Any callable that gets the return value from the request
        autoremove: Store callback as weak reference and remove it
                    automatically once there are no other references to it
                    left

        If the request raises an exception, 'response' callbacks are called
        with `None` and 'error' callbacks are called with the exception.
        """
        log.debug('Registering %r to receive %s responses', _funcname(callback), self._request_str)
        self._on_response.connect(callback, weak=autoremove)

    def on_error(self, callback, autoremove=True):
        """Register `callback` to receive request exceptions (see `on_response`)"""
        log.debug('Registering %r to receive %s errors', _funcname(callback), self._request_str)
        self._on_error.connect(callback, weak=autoremove)

    @property
    def has_callbacks(self):
        """Whether anyone is interested in response to callback"""
        return bool(self._on_response.receivers) or \
               bool(self._on_error.receivers)

    @property
    def interval(self):
        """Seconds between polls"""
        return self._interval

    @interval.setter
    def interval(self, interval):
        self._interval = interval
        if self.running:
            self.poll()

    def __repr__(self):
        return '<{} {}>'.format(type(self).__name__, self._request_str)
