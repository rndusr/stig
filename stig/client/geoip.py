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


class GeoIPError(Exception):
    pass


class GeoIPBase():
    GeoIPError = GeoIPError

    def __init__(self):
        self._filepath = None
        self._enabled = None

    @property
    def filepath(self):
        """Where to cache downloaded database"""
        return self._filepath
    @filepath.setter
    def filepath(self, filepath):
        self._filepath = filepath if filepath is None else str(filepath)

    @property
    def enabled(self):
        """Whether lookup functions always return None"""
        return self._enabled
    @enabled.setter
    def enabled(self, enabled):
        self._enabled = bool(enabled)

    def load(self):
        pass

    def country_code(self, addr):
        return None


try:
    import maxminddb
except ImportError:
    class GeoIP(GeoIPBase):
        pass

else:
    import os
    import time
    import asyncio

    class GeoIP(GeoIPBase):
        max_age = 60*24*7
        timeout = 5
        url = 'https://geolite.maxmind.com/download/geoip/database/GeoLite2-Country.mmdb.gz'

        def __init__(self):
            super().__init__()
            self._filepath = self.url.split('/')[-1][:-3]
            self._cache = {}
            self.enabled = True

        async def load(self, force_update=False, loop=None):
            if not self.enabled:
                return

            if loop is None:
                loop = asyncio.get_event_loop()

            if force_update:
                await self._update_dbfile(loop)
            else:
                filepath = self.filepath
                if os.path.exists(filepath):
                    age = time.time() - os.path.getmtime(filepath)
                    if age > self.max_age:
                        await self._update_dbfile(loop)
                else:
                    await self._update_dbfile(loop)

            self._db = self._read_dbfile()

        def _read_dbfile(self):
            try:
                return maxminddb.open_database(self.filepath)
            except maxminddb.InvalidDatabaseError as e:
                raise GeoIPError('Unable to read geolocation database %s: Invalid format' % (self.filepath,))

        async def _update_dbfile(self, loop):
            import aiohttp
            import gzip

            log.debug('Fetching fresh geolocation database from %s', self.url)

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(self.url, timeout=self.timeout) as resp:
                        data = await resp.content.read()
                except aiohttp.ClientError as e:
                    raise GeoIPError('Failed to download geolocation database %s: %s' % (self.url, os.strerror(e.errno)))

            try:
                data = gzip.decompress(data)
            except OSError:
                pass   # Maybe downloaded data isn't gzipped

            dirpath = os.path.dirname(self.filepath)
            try:
                if not os.path.exists(dirpath):
                    os.makedirs(dirpath)
                with open(self.filepath, 'wb') as f:
                    f.write(data)
            except OSError as e:
                if os.path.exists(self.filepath):
                    os.remove(self.filepath)
                raise GeoIPError('Unable to write geolocation database %s: %s' % (self.filepath, os.strerror(e.errno)))

            log.debug('Wrote new geoip cache: %s', self.filepath)

        def country_code(self, addr):
            if not self.enabled:
                return None

            cache = self._cache
            country, timestamp = cache.get(addr, (None, 0))
            now = time.time()
            if country is not None and now - timestamp < self.max_age:
                return country

            db = getattr(self, '_db', None)
            if db is not None:
                info = db.get(addr)
                if info is not None:
                    country = info['country']['iso_code']
                    cache[addr] = (country, now)
                    return country
