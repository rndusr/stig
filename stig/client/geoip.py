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

    @property
    def cachedir(self):
        """Where to cache the downloaded database"""
        return getattr(self, '_cachedir', None)
    @cachedir.setter
    def cachedir(self, cachedir):
        self._cachedir = str(cachedir)

    @property
    def enabled(self):
        """Whether lookup functions always return None"""
        return getattr(self, '_enabled', False)
    @enabled.setter
    def enabled(self, enabled):
        self._enabled = bool(enabled)

    async def load(self, *args, **kwargs):
        pass

    def country_code(self, addr):
        return None


try:
    import maxminddb
except ImportError:
    class GeoIP(GeoIPBase):
        available = False
else:
    import os
    import time
    import asyncio

    class GeoIP(GeoIPBase):
        available = True
        max_age = 60*60*24*30
        timeout = 5
        url = 'https://geolite.maxmind.com/download/geoip/database/GeoLite2-Country.mmdb.gz'

        def __init__(self):
            super().__init__()
            self.filename = self.url.split('/')[-1]
            if self.filename[-3:] == '.gz':
                self.filename = self.filename[:-3]
            self._lookup_cache = {}

        @property
        def cachefile(self):
            return os.path.join(self.cachedir, self.filename)

        async def load(self, force_update=False, loop=None):
            if loop is None:
                loop = asyncio.get_event_loop()

            # Maybe get fresh database from URL
            if force_update:
                log.debug('Forcing database update')
                await self._update_dbfile(loop)
            else:
                cachefile = self.cachefile
                if os.path.exists(cachefile):
                    age = time.time() - os.path.getmtime(cachefile)
                    if age > self.max_age:
                        log.debug('Cached database is older than %r seconds', self.max_age)
                        await self._update_dbfile(loop)
                else:
                    log.debug('No database found: %r', self.cachefile)
                    await self._update_dbfile(loop)

            # Read database
            try:
                self._db = maxminddb.open_database(cachefile)
            except maxminddb.InvalidDatabaseError as e:
                raise GeoIPError('Unable to read geolocation database %s: Invalid format'
                                 % (cachefile,))
            except FileNotFoundError as e:
                raise GeoIPError('Unable to read geolocation database %s'
                                 % (cachefile,))

        async def _update_dbfile(self, loop):
            import aiohttp
            import gzip

            log.debug('Fetching fresh geolocation database from %s', self.url)

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(self.url, timeout=self.timeout) as resp:
                        data = await resp.content.read()
                except aiohttp.ClientError as e:
                    raise GeoIPError('Failed to download geolocation database %s: %s'
                                     % (self.url, os.strerror(e.errno)))

            try:
                data = gzip.decompress(data)
            except OSError:
                pass   # Maybe downloaded data isn't gzipped

            cachedir = self.cachedir
            cachefile = self.cachefile
            try:
                if not os.path.exists(cachedir):
                    os.makedirs(cachedir)
                with open(cachefile, 'wb') as f:
                    f.write(data)
            except OSError as e:
                if os.path.exists(cachefile):
                    os.remove(cachefile)
                raise GeoIPError('Unable to write geolocation database %s: %s'
                                 % (cachefile, os.strerror(e.errno)))

            log.debug('Wrote new geoip database: %s', self.cachefile)

        def country_code(self, addr):
            if not self.enabled:
                return None

            cache = self._lookup_cache
            country, timestamp = cache.get(addr, (None, 0))
            now = time.time()
            if country is not None and now - timestamp < self.max_age:
                return country

            db = getattr(self, '_db', None)
            if db is not None:
                try:
                    info = db.get(addr)
                except maxminddb.InvalidDatabaseError:
                    pass
                else:
                    if isinstance(info, dict):
                        country = info.get('country')
                        if isinstance(country, dict):
                            iso_code = country.get('iso_code')
                            cache[addr] = (iso_code, now)
                            return iso_code
