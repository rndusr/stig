from stig.client.geoip import (GeoIPBase, GeoIP, GeoIPError)

import asynctest
from unittest import mock

import os
import time
import maxminddb


def test_maxminddb_installed():
    import sys
    assert 'maxminddb' in sys.modules


class TestGeoIPBase(asynctest.TestCase):
    def setUp(self):
        class GeoIP(GeoIPBase):
            pass
        self.geoip = GeoIP()

    def test_cachedir(self):
        self.assertEqual(self.geoip.cachedir, '')
        self.geoip.cachedir = '/foo/bar/baz/'
        self.assertEqual(self.geoip.cachedir, '/foo/bar/baz/')

    def test_enabled(self):
        self.assertEqual(self.geoip.enabled, False)
        self.geoip.enabled = 'yes'
        self.assertEqual(self.geoip.enabled, True)

    async def test_load(self):
        self.assertEqual(await self.geoip.load(), None)

    def test_country_code(self):
        self.assertEqual(self.geoip.country_code('1.2.3.4'), None)


class TestGeoIP_properties(asynctest.TestCase):
    def setUp(self):
        self.geoip = GeoIP()

    def test_cachefile(self):
        exp_filename = os.path.basename(self.geoip.url)[:-3]  # Remove .gz extension
        self.assertEqual(self.geoip.cachefile, exp_filename)
        self.geoip.cachedir = '/foo/bar'
        self.assertEqual(self.geoip.cachefile, os.path.join('/foo/bar', exp_filename))
        self.geoip.cachedir = 'baz/'
        self.assertEqual(self.geoip.cachefile, os.path.join('baz', exp_filename))

    @mock.patch('time.time')
    @mock.patch('os.path.getmtime')
    @mock.patch('os.path.exists')
    def test_cachefile_age(self, mock_exists, mock_getmtime, mock_time):
        mock_exists.return_value = True
        mock_getmtime.return_value = 300
        mock_time.return_value = 1000
        self.assertEqual(self.geoip.cachefile_age, 700)
        mock_exists.return_value = False
        self.assertEqual(self.geoip.cachefile_age, None)


class TestGeoIP_downloading(asynctest.TestCase):
    def setUp(self):
        self.geoip = GeoIP()

        self.mock_response = asynctest.MagicMock()
        self.mock_response.content.read = asynctest.CoroutineMock()
        self.mock_get = asynctest.patch('aiohttp.ClientSession.get').start()
        self.mock_get.return_value.__aenter__.return_value= self.mock_response

        self.mock_exists = mock.patch('os.path.exists').start()
        self.mock_getmtime = mock.patch('os.path.getmtime').start()
        self.mock_time = mock.patch('time.time').start()

        self.mock_maybe_replace_db = mock.patch(__name__ + '.GeoIP._maybe_replace_db').start()

    def tearDown(self):
        mock.patch.stopall()

    async def assert_cachefile_is_updated(self, force):
        self.mock_response.content.read.return_value = 'mock geoip data'
        await self.geoip._download_db(force=force)
        self.mock_get.assert_called_once_with(self.geoip.url, timeout=self.geoip.timeout)
        self.mock_maybe_replace_db.assert_called_once_with('mock geoip data')

    async def assert_cachefile_is_not_updated(self, force):
        self.mock_response.content.read.return_value = 'mock geoip data'
        await self.geoip._download_db(force=force)
        self.mock_get.assert_not_called()
        self.mock_maybe_replace_db.assert_not_called()

    @asynctest.patch(__name__ + '.GeoIP.cachefile_age', mock.PropertyMock(return_value=None))
    async def test_cachefile_doesnt_exist(self):
        self.mock_time.return_value = 0
        self.geoip._download_attempt_delay = 0
        await self.assert_cachefile_is_updated(force=False)
        await self.assert_cachefile_is_updated(force=True)

    @asynctest.patch(__name__ + '.GeoIP.cachefile_age', mock.PropertyMock(return_value=1001))
    async def test_cachefile_has_expired(self):
        self.geoip.max_cache_age = 1000
        self.mock_time.return_value = 0
        self.geoip._download_attempt_delay = 0
        await self.assert_cachefile_is_updated(force=False)
        await self.assert_cachefile_is_updated(force=True)

    @asynctest.patch(__name__ + '.GeoIP.cachefile_age', mock.PropertyMock(return_value=999))
    async def test_cachefile_is_up_to_date(self):
        self.geoip.max_cache_age = 1000
        await self.assert_cachefile_is_not_updated(force=False)

        self.mock_time.return_value = 0
        self.geoip._download_attempt_delay = 0
        await self.assert_cachefile_is_updated(force=True)

    @asynctest.patch(__name__ + '.GeoIP.cachefile_age', mock.PropertyMock(return_value=None))
    async def test_delay_between_download_attempts(self):
        self.geoip._download_attempt_delay = 10
        self.mock_time.return_value = 1e6

        self.geoip._last_download_attempt = 1e6 - 9
        await self.assert_cachefile_is_not_updated(force=False)
        await self.assert_cachefile_is_not_updated(force=True)

        self.geoip._last_download_attempt = 1e6 - 10
        await self.assert_cachefile_is_updated(force=False)
        await self.assert_cachefile_is_updated(force=True)

    @asynctest.patch(__name__ + '.GeoIP.cachefile_age', mock.PropertyMock(return_value=None))
    async def test_download_lock(self):
        self.mock_time.return_value = 0
        self.geoip._last_download_attempt = 0
        await self.geoip._download_lock.acquire()
        await self.assert_cachefile_is_not_updated(force=False)
        await self.assert_cachefile_is_not_updated(force=True)


class TestGeoIP_load(asynctest.TestCase):
    def setUp(self):
        self.geoip = GeoIP()
        self.geoip.enabled = True

        self.mock_open_database = mock.patch('maxminddb.open_database').start()
        self.mock_download_db = mock.patch(__name__ + '.GeoIP._download_db',
                                           asynctest.CoroutineMock()).start()

    def tearDown(self):
        mock.patch.stopall()

    async def test_force_update_option(self):
        await self.geoip.load()
        self.mock_download_db.assert_called_once_with(force=False)
        self.mock_download_db.reset_mock()
        await self.geoip.load(force_update=True)
        self.mock_download_db.assert_called_once_with(force=True)

    async def test_open_database_raises_InvalidDatabaseError(self):
        self.mock_open_database.side_effect = maxminddb.InvalidDatabaseError('nope')
        with self.assertRaises(GeoIPError) as cm:
            await self.geoip.load()
        self.assertEqual(str(cm.exception),
                         ('Unable to read geolocation database: %s: Invalid format'
                          % (self.geoip.cachefile,)))

    async def test_open_database_raises_other_error(self):
        import errno
        exception = FileNotFoundError(errno.ENOENT,
                                      os.strerror(errno.ENOENT),
                                      self.geoip.cachefile)
        self.mock_open_database.side_effect = exception
        with self.assertRaises(GeoIPError) as cm:
            await self.geoip.load()
        self.assertEqual(str(cm.exception),
                         ('Unable to read geolocation database: %s: %s'
                          % (self.geoip.cachefile, os.strerror(errno.ENOENT))))

    async def test_database_is_loaded_correctly(self):
        self.mock_open_database.return_value = 'mock database'
        await self.geoip.load()
        self.assertEqual(self.geoip._db, 'mock database')

    async def test_lookup_cache_is_emptied_if_load_succeeds(self):
        self.geoip._lookup_cache = {'1.2.3.4': ('AB', 123)}
        self.mock_open_database.return_value = 'mock database'
        await self.geoip.load()
        self.assertEqual(self.geoip._lookup_cache, {})

    async def test_lookup_cache_is_not_emptied_if_load_fails(self):
        self.geoip._lookup_cache = {'1.2.3.4': ('AB', 123)}
        self.mock_open_database.side_effect = maxminddb.InvalidDatabaseError()
        with self.assertRaises(GeoIPError) as cm:
            await self.geoip.load()
        self.assertEqual(self.geoip._lookup_cache, {'1.2.3.4': ('AB', 123)})


class TestGeoIP_prune_lookup_cache(asynctest.TestCase):
    def setUp(self):
        self.geoip = GeoIP()
        self.mock_time = mock.patch('time.time').start()

    def tearDown(self):
        mock.patch.stopall()

    def test_lookup_cache_is_pruned_correctly(self):
        import random
        self.geoip._lookup_cache = {
            '1.2.3.%d' % i : ('AB', i)
            for i in random.sample(range(10), 10)
        }
        self.geoip.max_cache_size = 6
        self.mock_time.return_value = 10
        self.geoip._prune_lookup_cache()
        self.assertEqual(self.geoip._lookup_cache,
                         {'1.2.3.7': ('AB', 7),
                          '1.2.3.8': ('AB', 8),
                          '1.2.3.9': ('AB', 9)})


class Test_country_code(asynctest.TestCase):
    def setUp(self):
        self.geoip = GeoIP()
        self.geoip.enabled = True

        self.mock_maxminddb = mock.patch.object(self.geoip, '_db').start()
        self.mock_download_db = mock.patch(__name__ + '.GeoIP._download_db',
                                           asynctest.CoroutineMock()).start()
        self.mock_load = mock.patch(__name__ + '.GeoIP.load',
                                    asynctest.CoroutineMock()).start()

    def tearDown(self):
        mock.patch.stopall()

    def test_not_enabled(self):
        self.geoip.enabled = False
        self.assertIs(self.geoip.country_code('asdf'), None)

    def test_cache(self):
        self.geoip._lookup_cache = {'1.2.3.4': ('AB', time.time())}
        self.assertEqual(self.geoip.country_code('1.2.3.4'), 'AB')
        self.mock_maxminddb.get.assert_not_called()
        self.mock_load.assert_not_called()

    def test_maxminddb_raises_InvalidDatabaseError(self):
        self.mock_maxminddb.get.side_effect = maxminddb.InvalidDatabaseError()
        self.assertEqual(self.geoip.country_code('1.2.3.4'), None)
        self.mock_maxminddb.get.assert_called_once_with('1.2.3.4')
        self.mock_load.assert_called_once_with(force_update=True, ignore_errors=True)

    def test_maxminddb_raises_UnicodeDecodeError(self):
        self.mock_maxminddb.get.side_effect = UnicodeDecodeError('mockcodec', b'', 0, 0, 'Oh no!')
        self.assertEqual(self.geoip.country_code('1.2.3.4'), None)
        self.mock_maxminddb.get.assert_called_once_with('1.2.3.4')
        self.mock_load.assert_called_once_with(force_update=True, ignore_errors=True)

    def test_maxminddb_returns_non_dictinary(self):
        self.mock_maxminddb.get.return_value = 'not a dict'
        self.assertEqual(self.geoip.country_code('1.2.3.4'), None)
        self.mock_maxminddb.get.assert_called_once_with('1.2.3.4')
        self.mock_load.assert_called_once_with(force_update=True, ignore_errors=True)

    def test_country_key_maps_to_non_dictionary(self):
        self.mock_maxminddb.get.return_value = {'country': 'not a dict'}
        self.assertEqual(self.geoip.country_code('1.2.3.4'), None)
        self.mock_maxminddb.get.assert_called_once_with('1.2.3.4')
        self.mock_load.assert_called_once_with(force_update=True, ignore_errors=True)
