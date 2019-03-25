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
    available = False

    @property
    def cachedir(self):
        """Where to cache the downloaded database"""
        return getattr(self, '_cachedir', '')
    @cachedir.setter
    def cachedir(self, cachedir):
        self._cachedir = str(cachedir)

    @property
    def enabled(self):
        """Whether lookup functions always return None"""
        return getattr(self, '_enabled', self.available)
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
        pass
else:
    import os
    import time
    import asyncio

    class GeoIP(GeoIPBase):
        available = True
        max_cache_age = 60*60*24*30
        max_cache_size = 1000
        timeout = 10
        url = 'https://geolite.maxmind.com/download/geoip/database/GeoLite2-Country.mmdb.gz'

        def __init__(self):
            super().__init__()
            self._db = None
            self._download_lock = asyncio.Lock()
            self._last_download_attempt = 0
            self._download_attempt_delay = 1  # Will double on each failure
            self._lookup_cache = {}
            self.filename = self.url.split('/')[-1]
            if self.filename[-3:] == '.gz':
                self.filename = self.filename[:-3]

        @property
        def cachefile(self):
            """Path to local DB file"""
            return os.path.join(self.cachedir, self.filename)

        @property
        def cachefile_age(self):
            """Age of local DB file in seconds or None if it doesn't exist"""
            if os.path.exists(self.cachefile):
                return time.time() - os.path.getmtime(self.cachefile)

        async def _download_db(self, force=False):
            """
            Download DB from class attribute `url`

            This method does nothing ...
                1. if another download attempt is already being made.
                2. if force evaluates to False, `cachefile` already exists and
                   it hasn't expired yet according to class attribute
                   `max_cache_age`.
                3. if attempts are too rapid, starting at 10 seconds between two
                   attempts and doubling on each attempt made.

            Raise GeoIPError on failure
            """
            cachefile_age = self.cachefile_age
            log.debug('Cached database is %r seconds old', self.cachefile_age)
            if cachefile_age and not force and cachefile_age < self.max_cache_age:
                log.debug('Cached database is not expired yet')
            elif time.time() - self._last_download_attempt < self._download_attempt_delay:
                log.debug('%r more seconds before attempting to download again',
                          self._download_attempt_delay - (time.time() - self._last_download_attempt))
            elif self._download_lock.locked():
                log.debug('Already downloading new DB: %r', self._download_lock)
            else:
                async with self._download_lock:
                    self._last_download_attempt = time.time()
                    log.debug('Fetching fresh geolocation database from %s', self.url)
                    import aiohttp
                    import gzip
                    async with aiohttp.ClientSession() as session:
                        try:
                            async with session.get(self.url, timeout=self.timeout) as response:
                                data = await response.content.read()
                        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                            log.debug('Calculating minimum delay between downloads: min(%r * 2, 3600)', self._download_attempt_delay)
                            self._download_attempt_delay = min(self._download_attempt_delay * 2, 3600)
                            log.debug('New minimum delay between downloads: %r seconds', self._download_attempt_delay)
                            raise GeoIPError('Failed to download geolocation database %s: %s'
                                             % (self.url, os.strerror(e.errno)))
                        else:
                            log.debug('Resetting minimum delay between downloads to 1 second')
                            self._download_attempt_delay = 1

                    try:
                        data = gzip.decompress(data)
                    except (OSError, TypeError):
                        pass   # Downloaded data isn't gzipped
                    finally:
                        self._maybe_replace_db(data)

        def _maybe_replace_db(self, data):
            """Replace old DB if the new version seems to work (sometimes it doesn't)"""
            cachedir = self.cachedir
            cachefile = self.cachefile
            cachefile_old = self.cachefile + '.old'
            try:
                if not os.path.exists(cachedir):
                    log.debug('Creating cache directory: %r', cachedir)
                    os.makedirs(cachedir)
                if os.path.exists(cachefile):
                    log.debug('Temporarily renaming cache file: %r -> %r', cachefile, cachefile_old)
                    os.rename(cachefile, cachefile_old)
                with open(cachefile, 'wb') as f:
                    f.write(data)
            except OSError as e:
                for filepath in (cachefile, cachefile_old):
                    if os.path.exists(filepath):
                        log.debug('Removing %r', filepath)
                        os.remove(filepath)
                raise GeoIPError('Unable to write geolocation database %s: %s'
                                 % (cachefile, os.strerror(e.errno)))
            else:
                if not self._validate_cachefile(cachefile):
                    log.debug('New geoip database is broken - restoring previous version')
                    os.remove(cachefile)
                    os.rename(cachefile_old, cachefile)
                else:
                    log.debug('Wrote new geoip DB: %s', self.cachefile)
                    if os.path.exists(cachefile_old):
                        log.debug('Removing: %s', cachefile_old)
                        os.remove(cachefile_old)

        def _validate_cachefile(self, filepath):
            try:
                db = maxminddb.open_database(filepath)
            except Exception as e:
                log.debug('Exception raised when trying to open %r: %r', filepath, e)
                return False

            test_ip = '1.1.1.1'
            try:
                db.get(test_ip)
            except Exception as e:
                log.debug('Exception raised when looking up %r: %r', test_ip, e)
                return False
            else:
                return True

        async def load(self, force_update=False, ignore_errors=False):
            """
            Load DB from `cachefile` unless it is already loaded

            If `cachefile` doesn't exist or has expired, attempt to download it
            first.  If `force_update` evaluates to True, ignore `max_cache_age`.

            Raise GeoIPError on failure unless `ignore_errors` evaluates to
            True.
            """
            if self._db is None or force_update:
                try:
                    await self._download_db(force=force_update)
                except GeoIPError:
                    if not ignore_errors:
                        raise

                try:
                    self._db = maxminddb.open_database(self.cachefile)
                except maxminddb.InvalidDatabaseError as e:
                    if not ignore_errors:
                        raise GeoIPError('Unable to read geolocation database: %s: Invalid format'
                                         % (self.cachefile,))
                except OSError as e:
                    if not ignore_errors:
                        errmsg = 'Unable to read geolocation database: %s' % (self.cachefile,)
                        if e.errno is not None:
                            errmsg += ': %s' % (os.strerror(e.errno),)
                        raise GeoIPError(errmsg)
                else:
                    self._lookup_cache.clear()

        def country_code(self, addr):
            """
            Lookup two-letter country code (upper case) for IP address `addr`

            Always return None if `enabled` is set to False.
            """
            if not self.enabled:
                return None

            self._prune_lookup_cache()
            cache = self._lookup_cache
            country, timestamp = cache.get(addr, (None, 0))
            now = time.time()
            if country is not None and now - timestamp < self.max_cache_age:
                return country

            db = self._db
            if db is not None:
                try:
                    info = db.get(addr)
                except maxminddb.InvalidDatabaseError as e:
                    log.debug('Invalid database: %r', e)
                    asyncio.ensure_future(self.load(force_update=True, ignore_errors=True))
                except UnicodeDecodeError as e:
                    log.debug('Caught UnicodeDecodeError with address %r: %r', addr, e)
                    asyncio.ensure_future(self.load(force_update=True, ignore_errors=True))
                else:
                    if isinstance(info, dict):
                        country = info.get('country')
                        if isinstance(country, dict):
                            iso_code = country.get('iso_code')
                            cache[addr] = (iso_code, now)
                            return iso_code
                        else:
                            log.debug('"country" key maps to non-dict: %r', country)
                            asyncio.ensure_future(self.load(force_update=True, ignore_errors=True))
                    else:
                        log.debug('maxminddb.get(%r) returned non-dict: %r', addr, info)
                        asyncio.ensure_future(self.load(force_update=True, ignore_errors=True))
            else:
                log.debug('Database is not loaded')
                asyncio.ensure_future(self.load(ignore_errors=True))

        def _prune_lookup_cache(self):
            cache = self._lookup_cache
            max_cache_size = self.max_cache_size
            if len(cache) > max_cache_size:
                new_cache_size = int(self.max_cache_size * 0.5)
                start = time.time()

                # Sort by timestamp and remove items until cache is small enough
                for addr,(_,timestamp) in sorted(cache.items(), key=lambda kv: kv[1][1]):
                    len_cache = len(cache)
                    if len_cache <= new_cache_size:
                        break
                    else:
                        del cache[addr]

                log.debug('Pruned cache in %.3fµs', (time.time()-start) * 1e6)
