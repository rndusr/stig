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


# Only needed until asyncio gets a timeout again.
# https://github.com/python/asyncio/commit/e39449787dedd839e31946915fa933a08955b667
from aiohttp import Timeout as AsyncIOTimeout
import asyncio
class SleepUneasy():
    """Asynchronous sleep() that can be aborted"""

    def __init__(self, loop):
        self.loop = loop
        self._interrupt = asyncio.Event(loop=self.loop)

    async def sleep(self, seconds=None):
        """Sleep for `seconds` or until `interrupt` is called"""
        self._interrupt.clear()
        try:
            with AsyncIOTimeout(seconds, loop=self.loop):
                await self._interrupt.wait()
        except asyncio.TimeoutError:
            pass  # Interval passed without interrupt
        finally:
            self._interrupt.clear()

    def interrupt(self):
        """Stop sleeping"""
        self._interrupt.set()


class PerfectInterval():
    """Remove processing time from intervals"""

    def __init__(self, loop):
        self._loop = loop

    def __call__(self, seconds):
        now = self._loop.time()
        stop_at = int(now) + seconds
        diff = stop_at - now
        return diff


from types import SimpleNamespace
class Response(SimpleNamespace):
    """Response to an API call

    All API implementations should use this class to provide return values to
    API calls.

    success: Whether the call was a success
    msgs: Sequence of messages; either strings or ClientError exceptions

    Any other keyword arguments are made available as attributes.
    """
    def __init__(self, success=False, msgs=(), **kwargs):
        super().__init__(success=bool(success), msgs=tuple(msgs), **kwargs)


class LazyDict(dict):
    """Dictionary with callables as values that return the actual value on demand"""
    def __getitem__(self, key):
        value = dict.__getitem__(self, key)
        if callable(value):
            value = value()
            dict.__setitem__(self, key, value)
        return value


from urllib.parse import (urlsplit, urlunsplit)
class URL(str):
    """Provide the same attributes as `urllib.parse.urlsplit` plus 'domain'"""
    def __init__(self, url):
        # If no scheme is given, urlsplit() thinks the whole string is the path
        if '://' not in url:
            url = 'http://' + url
        self._split_url = split_url = urlsplit(url)

        # Find domain name
        if split_url.hostname.count('.') <= 1:
            self.__domain = split_url.hostname
        else:
            parts = split_url.hostname.split('.')
            self.__domain = '.'.join(parts[-2:])

    def __getattr__(self, name):
        if name == 'domain':
            return self.__domain
        else:
            return getattr(self._split_url, name)

    def __str__(self):
        return urlunsplit(self._split_url)

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self._split_url == other._split_url
        else:
            return NotImplemented

    def __hash__(self):
        return hash(self._split_url)

    def __repr__(self):
        return '<URL %s>' % self
