import contextlib
import random
import time
import unittest
from datetime import datetime
from unittest.mock import patch

from stig.client import utils


class TestPath(unittest.TestCase):
    def test_eq_ne(self):
        self.assertTrue(utils.Path('/foo/bar/') == utils.Path('/foo/bar'))
        self.assertTrue(utils.Path('/foo/bar/./../bar/') == utils.Path('/foo/bar'))
        self.assertTrue(utils.Path('foo/bar') != utils.Path('/foo/bar'))


class TestRatio(unittest.TestCase):
    def test_string(self):
        self.assertEqual(utils.Ratio(0), 0)
        self.assertEqual(str(utils.Ratio(-1)), '')
        self.assertEqual(str(utils.Ratio(float('inf'))), '∞')
        self.assertEqual(str(utils.Ratio(0.0003)), '0')
        self.assertEqual(str(utils.Ratio(5.389)), '5.39')
        self.assertEqual(str(utils.Ratio(10.0234)), '10')
        self.assertEqual(str(utils.Ratio(47.86123)), '47.9')
        self.assertEqual(str(utils.Ratio(100.5)), '100')


class TestStatus(unittest.TestCase):
    def test_string(self):
        for s in (utils.Status.VERIFY, utils.Status.DOWNLOAD,
                  utils.Status.UPLOAD, utils.Status.INIT, utils.Status.CONNECTED,
                  utils.Status.QUEUED, utils.Status.SEED, utils.Status.IDLE,
                  utils.Status.STOPPED):
            self.assertEqual(utils.Status((s,)), (s,))

    def test_sort(self):
        statuses = [utils.Status.UPLOAD, utils.Status.CONNECTED,
                    utils.Status.SEED, utils.Status.INIT, utils.Status.VERIFY,
                    utils.Status.DOWNLOAD, utils.Status.STOPPED,
                    utils.Status.IDLE, utils.Status.QUEUED]
        sort = sorted([utils.Status((s,)) for s in statuses])
        exp = [(utils.Status.VERIFY,), (utils.Status.DOWNLOAD,),
               (utils.Status.UPLOAD,), (utils.Status.INIT,),
               (utils.Status.CONNECTED,), (utils.Status.QUEUED,),
               (utils.Status.IDLE,), (utils.Status.STOPPED,),
               (utils.Status.SEED,)]
        self.assertEqual(sort, exp)


class TestSmartCmpStr(unittest.TestCase):
    def test_eq_ne(self):
        self.assertTrue(utils.SmartCmpStr('foo') == 'foo')
        self.assertTrue(utils.SmartCmpStr('Foo') == 'foo')
        self.assertTrue(utils.SmartCmpStr('foo') != 'Foo')

    def test_lt(self):
        self.assertFalse(utils.SmartCmpStr('foo') < 'foo')
        self.assertFalse(utils.SmartCmpStr('Foo') < 'foo')
        self.assertFalse(utils.SmartCmpStr('foo') < 'Foo')

    def test_le(self):
        self.assertTrue(utils.SmartCmpStr('foo') <= 'foo')
        self.assertTrue(utils.SmartCmpStr('Foo') <= 'foo')
        self.assertFalse(utils.SmartCmpStr('foo') <= 'Foo')

    def test_gt(self):
        self.assertFalse(utils.SmartCmpStr('foo') > 'foo')
        self.assertFalse(utils.SmartCmpStr('Foo') > 'foo')
        self.assertTrue(utils.SmartCmpStr('foo') > 'Foo')

    def test_ge(self):
        self.assertTrue(utils.SmartCmpStr('foo') >= 'foo')
        self.assertTrue(utils.SmartCmpStr('Foo') >= 'foo')
        self.assertTrue(utils.SmartCmpStr('foo') >= 'Foo')

    def test_contains(self):
        self.assertTrue('foo' in utils.SmartCmpStr('foo'))
        self.assertTrue('foo' in utils.SmartCmpStr('Foo'))
        self.assertFalse('Foo' in utils.SmartCmpStr('foo'))


class TestURL(unittest.TestCase):
    def test_empty_string(self):
        url = utils.URL('')
        self.assertEqual(url.scheme, None)
        self.assertEqual(url.host, None)
        self.assertEqual(url.port, None)
        self.assertEqual(str(url), '')

    def test_attributes(self):
        url = utils.URL('http://user:pw@localhost:123/foo')
        self.assertEqual(url.scheme, 'http')
        self.assertEqual(url.user, 'user')
        self.assertEqual(url.password, 'pw')
        self.assertEqual(url.host, 'localhost')
        self.assertEqual(url.port, 123)
        self.assertEqual(url.path, '/foo')

    def test_no_scheme(self):
        url = utils.URL('localhost/foo')
        self.assertEqual(url.scheme, 'http')
        self.assertEqual(url.host, 'localhost')
        self.assertEqual(url.port, None)
        self.assertEqual(url.path, '/foo')

    def test_authentication(self):
        url = utils.URL('https://foo:bar@localhost:123')
        self.assertEqual(url.scheme, 'https')
        self.assertEqual(url.host, 'localhost')
        self.assertEqual(url.port, 123)
        self.assertEqual(url.user, 'foo')
        self.assertEqual(url.password, 'bar')

    def test_authentication_empty_password(self):
        url = utils.URL('foo:@localhost')
        self.assertEqual(url.user, 'foo')
        self.assertEqual(url.password, None)
        self.assertEqual(url.host, 'localhost')

    def test_authentication_no_password(self):
        url = utils.URL('foo@localhost')
        self.assertEqual(url.user, 'foo')
        self.assertEqual(url.password, None)
        self.assertEqual(url.host, 'localhost')

    def test_authentication_empty_user(self):
        url = utils.URL(':bar@localhost')
        self.assertEqual(url.user, None)
        self.assertEqual(url.password, 'bar')
        self.assertEqual(url.host, 'localhost')

    def test_authentication_empty_user_and_password(self):
        url = utils.URL(':@localhost')
        self.assertEqual(url.user, None)
        self.assertEqual(url.password, None)
        self.assertEqual(url.host, 'localhost')

    def test_invalid_port(self):
        url = utils.URL('foohost:70123')
        self.assertEqual(url.scheme, 'http')
        self.assertEqual(url.host, 'foohost')
        self.assertEqual(url.port, 70123)

    def test_no_scheme_with_port(self):
        url = utils.URL('foohost:9999')
        self.assertEqual(url.scheme, 'http')
        self.assertEqual(url.host, 'foohost')
        self.assertEqual(url.port, 9999)

    def test_no_scheme_user_and_pw(self):
        url = utils.URL('foo:bar@foohost:9999')
        self.assertEqual(url.scheme, 'http')
        self.assertEqual(url.host, 'foohost')
        self.assertEqual(url.port, 9999)
        self.assertEqual(url.user, 'foo')
        self.assertEqual(url.password, 'bar')

    def test_str(self):
        url = utils.URL('https://foo:bar@localhost:123')
        self.assertEqual(str(url), 'https://foo:bar@localhost:123')
        url = utils.URL('localhost')
        self.assertEqual(str(url), 'http://localhost')

    def test_repr(self):
        url = utils.URL('https://foo:bar@localhost:123/foo/bar/baz')
        self.assertEqual(repr(url), "URL('https://foo:bar@localhost:123/foo/bar/baz')")

    def test_mutability_and_cache(self):
        url = utils.URL('https://foo.example.com:123/foo')
        url.port = 321
        url.host = 'bar.example.com'
        url.scheme = 'http'
        self.assertEqual(str(url), 'http://bar.example.com:321/foo')

        self.assertEqual(url.domain, 'example.com')
        url.host = 'foo.bar.com'
        self.assertEqual(url.domain, 'bar.com')
        self.assertEqual(str(url), 'http://foo.bar.com:321/foo')


MIN = utils.SECONDS[5][1]
HOUR = utils.SECONDS[4][1]
DAY = utils.SECONDS[3][1]
WEEK = utils.SECONDS[2][1]
MONTH = utils.SECONDS[1][1]
YEAR = utils.SECONDS[0][1]
TIMEUNITS = tuple(x[0] for x in utils.SECONDS)

def mktime(string):
    tstruct = time.strptime(string, '%Y-%m-%d %H:%M:%S')
    return time.mktime(tstruct)

@contextlib.contextmanager
def mock_time(year=0, month=0, day=0, hour=0, minute=0, second=0):
    dt = datetime(year, month, day, hour, minute, second)

    class Mock_datetime(datetime):
        @classmethod
        def now(cls, *args, **kwargs):
            return dt

    patchers = (patch('time.time', lambda *args, **kwargs: dt.timestamp()),
                patch('time.localtime', lambda s: datetime.fromtimestamp(s).timetuple() if s else dt.timestamp()),
                patch('datetime.datetime', Mock_datetime))
    for p in patchers: p.start()
    try:
        yield
    finally:
        for p in patchers: p.stop()


class TestTimedelta(unittest.TestCase):
    def test_from_string__constants(self):
        self.assertEqual(utils.Timedelta.from_string('unknown'), utils.Timedelta.UNKNOWN)
        self.assertEqual(utils.Timedelta.from_string('na'), utils.Timedelta.NOT_APPLICABLE)
        self.assertEqual(utils.Timedelta.from_string('n/a'), utils.Timedelta.NOT_APPLICABLE)
        self.assertEqual(utils.Timedelta.from_string('not applicable'), utils.Timedelta.NOT_APPLICABLE)

    def test_from_string__no_unit(self):
        self.assertEqual(utils.Timedelta.from_string('0'), 0)
        self.assertEqual(utils.Timedelta.from_string('60'), MIN)
        self.assertEqual(utils.Timedelta.from_string('600'), 10 * MIN)

    def test_from_string__single_unit(self):
        self.assertEqual(utils.Timedelta.from_string('0s'), 0)
        self.assertEqual(utils.Timedelta.from_string('1s'), 1)
        self.assertEqual(utils.Timedelta.from_string('2m'), 2 * MIN)
        self.assertEqual(utils.Timedelta.from_string('3h'), 3 * HOUR)
        self.assertEqual(utils.Timedelta.from_string('4d'), 4 * DAY)
        self.assertEqual(utils.Timedelta.from_string('2w'), 2 * 7 * DAY)
        self.assertEqual(utils.Timedelta.from_string('6M'), 6 * MONTH)
        self.assertEqual(utils.Timedelta.from_string('7y'), 7 * YEAR)

    def test_from_string__multiple_units(self):
        self.assertEqual(utils.Timedelta.from_string('1d2h3m4s'), DAY + (2 * HOUR) + (3 * MIN) + 4)
        self.assertEqual(utils.Timedelta.from_string('4s1d2h3m'), DAY + (2 * HOUR) + (3 * MIN) + 4)

    def test_from_string__fractions(self):
        self.assertEqual(utils.Timedelta.from_string('2.5h.2m'), (2 * HOUR) + (30 * MIN) + 12)

    def test_from_string__too_large_numbers(self):
        self.assertEqual(utils.Timedelta.from_string('600'), 10 * MIN)
        self.assertEqual(utils.Timedelta.from_string('600m'), 10 * HOUR)
        self.assertEqual(utils.Timedelta.from_string('30h'), DAY + (6 * HOUR))

    def test_from_string__signs(self):
        self.assertEqual(utils.Timedelta.from_string('-3h'), -3 * HOUR)
        self.assertEqual(utils.Timedelta.from_string('+3h'), 3 * HOUR)
        self.assertEqual(utils.Timedelta.from_string('-3h5s'), (-3 * HOUR) - 5)
        self.assertEqual(utils.Timedelta.from_string('+3h5s'), (3 * HOUR) + 5)

    def test_from_string__in_ago_notation(self):
        self.assertEqual(utils.Timedelta.from_string('in 1h30m20s'),  HOUR + (30 * MIN) + 20)
        self.assertEqual(utils.Timedelta.from_string('-1.5h20s ago'), -HOUR - (30 * MIN) - 20)

    def test_from_string__contradicting_signs(self):
        for string in ('in -1h', 'in 1h ago'):
            with self.assertRaises(ValueError):
                utils.Timedelta.from_string(string)

    def test_special_values(self):
        self.assertEqual(str(utils.Timedelta(0)), '0s')
        self.assertEqual(str(utils.Timedelta(0.4)), '0s')
        self.assertEqual(str(utils.Timedelta(-0.4)), '0s')
        self.assertEqual(str(utils.Timedelta(utils.Timedelta.NOT_APPLICABLE)), '')
        self.assertEqual(str(utils.Timedelta(utils.Timedelta.UNKNOWN)), '?')

    def test_added_subunits_for_small_numbers(self):
        self.assertEqual(str(utils.Timedelta(9 * HOUR + 59 * MIN + 59)), '9h59m')
        self.assertEqual(str(utils.Timedelta(10 * HOUR + 59 * MIN + 59)), '10h')

    def test_negative_delta(self):
        self.assertEqual(str(utils.Timedelta(-10)), '-10s')
        self.assertEqual(str(utils.Timedelta(-1 * 60 - 45)), '-1m45s')
        self.assertEqual(str(utils.Timedelta(-3 * DAY - 2 * HOUR)), '-3d2h')

    def test_preposition_string(self):
        self.assertEqual(utils.Timedelta(6 * DAY).with_preposition, 'in 6d')
        self.assertEqual(utils.Timedelta(-6 * DAY).with_preposition, '6d ago')
        self.assertEqual(utils.Timedelta(0.3).with_preposition, 'now')
        self.assertEqual(utils.Timedelta(-0.3).with_preposition, 'now')

    def test_sorting(self):
        lst = [utils.Timedelta(-2 * HOUR),
               utils.Timedelta(2 * MIN),
               utils.Timedelta(3 * MIN),
               utils.Timedelta(1 * DAY),
               utils.Timedelta(2.5 * YEAR),
               utils.Timedelta(utils.Timedelta.UNKNOWN),
               utils.Timedelta(utils.Timedelta.NOT_APPLICABLE)]

        def shuffle(l):
            return random.sample(l, k=len(l))

        for _ in range(10):
            self.assertEqual(sorted(shuffle(lst)), lst)

    def test_bool(self):
        for td in (utils.Timedelta(random.randint(-1e5, 1e5) * MIN),
                   utils.Timedelta(random.randint(-1e5, 1e5) * HOUR),
                   utils.Timedelta(random.randint(-1e5, 1e5) * DAY)):
            self.assertEqual(bool(td), True)

        for td in (utils.Timedelta(utils.Timedelta.UNKNOWN),
                   utils.Timedelta(utils.Timedelta.NOT_APPLICABLE)):
            self.assertEqual(bool(td), False)

    def test_inverse(self):
        pos = utils.Timedelta.from_string('5y4M3d2h1m10s')
        neg = utils.Timedelta.from_string('-5y4M3d2h1m10s')
        self.assertEqual(pos.inverse, neg)
        self.assertEqual(neg.inverse, pos)
        self.assertTrue(neg.inverse._real_years > 0)
        self.assertTrue(neg.inverse._real_months > 0)
        self.assertTrue(pos.inverse._real_years < 0)
        self.assertTrue(pos.inverse._real_months < 0)

    def test_timestamp_conversion_with_years_and_months(self):
        with mock_time(year=2001, month=1, day=1, hour=1, minute=1, second=1):
            self.assertEqual(utils.Timedelta.from_string('5y4M3d2h1m10s').timestamp,
                             utils.Timestamp.from_string('2006-05-04 03:02:11'))
            self.assertEqual(utils.Timedelta.from_string('-10y7M5d3h1m10s').timestamp,
                             utils.Timestamp.from_string('1990-05-26 21:59:51'))

        with mock_time(year=2001, month=1, day=31, hour=10, minute=15, second=20):
            self.assertEqual(utils.Timedelta.from_string('1M5h5m10s').timestamp,
                             utils.Timestamp.from_string('2001-02-28 15:20:30'))
            self.assertEqual(utils.Timedelta.from_string('1M1d5h5m10s').timestamp,
                             utils.Timestamp.from_string('2001-03-01 15:20:30'))

            self.assertEqual(utils.Timedelta.from_string('-2M5h5m10s').timestamp,
                             utils.Timestamp.from_string('2000-11-30 05:10:10'))
            self.assertEqual(utils.Timedelta.from_string('-2M40d5h5m10s').timestamp,
                             utils.Timestamp.from_string('2000-10-21 05:10:10'))

            self.assertEqual(utils.Timedelta.from_string('24M5h5m10s').timestamp,
                             utils.Timestamp.from_string('2003-01-31 15:20:30'))
            self.assertEqual(utils.Timedelta.from_string('24M59d5h5m10s').timestamp,
                             utils.Timestamp.from_string('2003-03-31 15:20:30'))

            self.assertEqual(utils.Timedelta.from_string('-24M5h5m10s').timestamp,
                             utils.Timestamp.from_string('1999-01-31 05:10:10'))
            self.assertEqual(utils.Timedelta.from_string('-24M62d5h5m10s').timestamp,
                             utils.Timestamp.from_string('1998-11-30 05:10:10'))

        # datetime can't handle large integers so we default to inaccurately
        # adding seconds, but we have to make sure we don't get any exceptions.
        utils.Timedelta.from_string('1000000000y').timestamp
        utils.Timedelta.from_string('1000000000M').timestamp


class TestTimestamp(unittest.TestCase):
    def test_string__constants(self):
        self.assertEqual(utils.Timestamp.from_string('now'), utils.Timestamp.NOW)
        self.assertEqual(utils.Timestamp.from_string('Now'), utils.Timestamp.NOW)
        self.assertEqual(utils.Timestamp.from_string('soon'), utils.Timestamp.SOON)
        self.assertEqual(utils.Timestamp.from_string('SOON'), utils.Timestamp.SOON)
        self.assertEqual(utils.Timestamp.from_string('unknown'), utils.Timestamp.UNKNOWN)
        self.assertEqual(utils.Timestamp.from_string('uNknoWn'), utils.Timestamp.UNKNOWN)
        self.assertEqual(utils.Timestamp.from_string('na'), utils.Timestamp.NOT_APPLICABLE)
        self.assertEqual(utils.Timestamp.from_string('NA'), utils.Timestamp.NOT_APPLICABLE)
        self.assertEqual(utils.Timestamp.from_string('N/A'), utils.Timestamp.NOT_APPLICABLE)
        self.assertEqual(utils.Timestamp.from_string('Not Applicable'), utils.Timestamp.NOT_APPLICABLE)
        self.assertEqual(utils.Timestamp.from_string('never'), utils.Timestamp.NEVER)
        self.assertEqual(utils.Timestamp.from_string('NeveR'), utils.Timestamp.NEVER)

    def test_string__year(self):
        ts = utils.Timestamp.from_string('2000')
        self.assertEqual(int(ts), mktime('2000-01-01 00:00:00'))
        ts = utils.Timestamp.from_string('2001')
        self.assertEqual(int(ts), mktime('2001-01-01 00:00:00'))

    def test_string__year_month(self):
        ts = utils.Timestamp.from_string('2000-01')
        self.assertEqual(int(ts), mktime('2000-01-01 00:00:00'))
        ts = utils.Timestamp.from_string('2000-12')
        self.assertEqual(int(ts), mktime('2000-12-01 00:00:00'))

    def test_string__year_month_day(self):
        ts = utils.Timestamp.from_string('2000-01-01')
        self.assertEqual(int(ts), mktime('2000-01-01 00:00:00'))
        ts = utils.Timestamp.from_string('2000-12-31')
        self.assertEqual(int(ts), mktime('2000-12-31 00:00:00'))

    def test_string__year_month_day_hour_minute(self):
        ts = utils.Timestamp.from_string('2000-01-01 12:03')
        self.assertEqual(int(ts), mktime('2000-01-01 12:03:00'))
        ts = utils.Timestamp.from_string('1999-12-31 23:59')
        self.assertEqual(int(ts), mktime('1999-12-31 23:59:00'))

    def test_string__year_month_day_hour_minute_second(self):
        ts = utils.Timestamp.from_string('1999-12-31 23:59:59')
        self.assertEqual(int(ts), mktime('1999-12-31 23:59:59'))
        ts = utils.Timestamp.from_string('2000-01-01 23:59:59')
        self.assertEqual(int(ts), mktime('2000-01-01 23:59:59'))

    def test_string__month_day(self):
        with mock_time(2000, 10, 15, 12, 30, 45):
            ts = utils.Timestamp.from_string('12-31')
            self.assertEqual(int(ts), mktime('2000-12-31 00:00:00'))
        with mock_time(2033, 5, 3, 3, 45, 12):
            ts = utils.Timestamp.from_string('01-31')
            self.assertEqual(int(ts), mktime('2033-01-31 00:00:00'))

    def test_string__month_day_hour_minute(self):
        with mock_time(1973, 10, 15, 12, 30, 45):
            ts = utils.Timestamp.from_string('03-15 17:39')
            self.assertEqual(int(ts), mktime('1973-03-15 17:39:00'))
        with mock_time(1904, 5, 3, 3, 45, 12):
            ts = utils.Timestamp.from_string('09-21 06:45')
            self.assertEqual(int(ts), mktime('1904-09-21 06:45:00'))

    def test_string__month_day_hour_minute_second(self):
        with mock_time(1945, 5, 17, 3, 29, 4):
            ts = utils.Timestamp.from_string('08-07 09:28:07')
            self.assertEqual(int(ts), mktime('1945-08-07 09:28:07'))
        with mock_time(2010, 4, 24, 18, 17, 57):
            ts = utils.Timestamp.from_string('10-20 05:03:14')
            self.assertEqual(int(ts), mktime('2010-10-20 05:03:14'))

    def test_string__hour_minute_second(self):
        with mock_time(2034, 11, 30, 11, 31, 22):
            ts = utils.Timestamp.from_string('12:32:23')
            self.assertEqual(int(ts), mktime('2034-11-30 12:32:23'))

    def test_string__hour_minute(self):
        with mock_time(1987, 6, 27, 22, 19, 13):
            ts = utils.Timestamp.from_string('19:33')
            self.assertEqual(int(ts), mktime('1987-06-27 19:33:00'))

    def test_string__year_hour_minute(self):
        with mock_time(2538, 1, 5, 7, 33, 11):
            ts = utils.Timestamp.from_string('2000 17:07')
            self.assertEqual(int(ts), mktime('2000-01-01 17:07:00'))

    def test_string_representation(self):
        with mock_time(1993, 2, 14, 5, 38, 12):
            self.assertEqual(str(utils.Timestamp(time.time())), '05:38:12')
            self.assertEqual(str(utils.Timestamp(time.time() - 60)), '05:37:12')
            self.assertEqual(str(utils.Timestamp(time.time() + 60)), '05:39:12')
            self.assertEqual(str(utils.Timestamp(time.time() - 3 * 60 * 60)), '02:38')
            self.assertEqual(str(utils.Timestamp(time.time() + 3 * 60 * 60)), '08:38')
            self.assertEqual(str(utils.Timestamp(time.time() - 7 * 24 * 60 * 60)), '1993-02-07')
            self.assertEqual(str(utils.Timestamp(time.time() + 7 * 24 * 60 * 60)), '1993-02-21')
        self.assertEqual(str(utils.Timestamp(utils.Timestamp.NOW)), 'now')
        self.assertEqual(str(utils.Timestamp(utils.Timestamp.SOON)), 'soon')
        self.assertEqual(str(utils.Timestamp(utils.Timestamp.UNKNOWN)), '?')
        self.assertEqual(str(utils.Timestamp(utils.Timestamp.NOT_APPLICABLE)), '')
        self.assertEqual(str(utils.Timestamp(utils.Timestamp.NEVER)), 'never')

    def test_full_property(self):
        with mock_time(1993, 2, 14, 5, 38, 12):
            self.assertEqual(utils.Timestamp(time.time()).full, '1993-02-14 05:38:12')
        self.assertEqual(utils.Timestamp(utils.Timestamp.NOW).full, 'now')
        self.assertEqual(utils.Timestamp(utils.Timestamp.SOON).full, 'soon')
        self.assertEqual(utils.Timestamp(utils.Timestamp.UNKNOWN).full, 'unknown')
        self.assertEqual(utils.Timestamp(utils.Timestamp.NOT_APPLICABLE).full, 'not applicable')
        self.assertEqual(utils.Timestamp(utils.Timestamp.NEVER).full, 'never')

    def test_time(self):
        self.assertEqual(utils.Timestamp.from_string('1954').time, '00:00:00')
        self.assertEqual(utils.Timestamp.from_string('1954-08').time, '00:00:00')
        self.assertEqual(utils.Timestamp.from_string('1954-08-09').time, '00:00:00')
        self.assertEqual(utils.Timestamp.from_string('1954-08-09 23:59:59').time, '23:59:59')
        self.assertEqual(utils.Timestamp.from_string('1954-08-10 11:12:13').time, '11:12:13')
        self.assertEqual(utils.Timestamp(utils.Timestamp.NOW).time, 'now')
        self.assertEqual(utils.Timestamp(utils.Timestamp.SOON).time, 'soon')
        self.assertEqual(utils.Timestamp(utils.Timestamp.UNKNOWN).time, 'unknown')
        self.assertEqual(utils.Timestamp(utils.Timestamp.NOT_APPLICABLE).time, 'not applicable')
        self.assertEqual(utils.Timestamp(utils.Timestamp.NEVER).time, 'never')

    def test_date(self):
        with mock_time(1954, 2, 3, 0, 0, 0):
            self.assertEqual(utils.Timestamp.from_string('00:00:00').date, '1954-02-03')
            self.assertEqual(utils.Timestamp.from_string('08:09:10').date, '1954-02-03')
            self.assertEqual(utils.Timestamp.from_string('23:59:59').date, '1954-02-03')
        self.assertEqual(utils.Timestamp.from_string('1954').date, '1954-01-01')
        self.assertEqual(utils.Timestamp.from_string('1954-08').date, '1954-08-01')
        self.assertEqual(utils.Timestamp.from_string('1954-08-09').date, '1954-08-09')
        self.assertEqual(utils.Timestamp.from_string('1954-08-09 23:59:59').date, '1954-08-09')
        self.assertEqual(utils.Timestamp.from_string('1954-08-10 00:00:00').date, '1954-08-10')
        self.assertEqual(utils.Timestamp.from_string('1954-08-10 11:12:13').date, '1954-08-10')
        self.assertEqual(utils.Timestamp(utils.Timestamp.NOW).date, 'now')
        self.assertEqual(utils.Timestamp(utils.Timestamp.SOON).date, 'soon')
        self.assertEqual(utils.Timestamp(utils.Timestamp.UNKNOWN).date, 'unknown')
        self.assertEqual(utils.Timestamp(utils.Timestamp.NOT_APPLICABLE).date, 'not applicable')
        self.assertEqual(utils.Timestamp(utils.Timestamp.NEVER).date, 'never')

    def test_timedelta(self):
        self.assertIsInstance(utils.Timestamp(1234).timedelta, utils.Timedelta)
        self.assertIsInstance(utils.Timestamp(utils.Timestamp.NOW).timedelta, utils.Timedelta)
        self.assertIsInstance(utils.Timestamp(utils.Timestamp.SOON).timedelta, utils.Timedelta)
        self.assertIsInstance(utils.Timestamp(utils.Timestamp.UNKNOWN).timedelta, utils.Timedelta)
        self.assertIsInstance(utils.Timestamp(utils.Timestamp.NOT_APPLICABLE).timedelta, utils.Timedelta)
        self.assertIsInstance(utils.Timestamp(utils.Timestamp.NEVER).timedelta, utils.Timedelta)
        with mock_time(2000, 1, 1, 0, 0, 0):
            self.assertEqual(utils.Timestamp.from_string('00:00:00').timedelta, utils.Timedelta(0))
            self.assertEqual(utils.Timestamp.from_string('00:00:01').timedelta, utils.Timedelta(1))
            self.assertEqual(utils.Timestamp.from_string('00:05:00').timedelta, utils.Timedelta(300))
            self.assertEqual(utils.Timestamp.from_string('01-02 00:00:00').timedelta, utils.Timedelta(3600 * 24))
            self.assertEqual(utils.Timestamp.from_string('02-01 00:00:00').timedelta, utils.Timedelta(3600 * 24 * 31))

    def test_accuracy__year_eq(self):
        ts = utils.Timestamp.from_string('2005')
        self.assertTrue(ts != mktime('2004-12-31 23:59:59'))
        self.assertTrue(ts == mktime('2005-01-01 00:00:00'))
        self.assertTrue(ts == mktime('2005-06-15 12:30:15'))
        self.assertTrue(ts == mktime('2005-12-31 23:59:59'))
        self.assertTrue(ts != mktime('2006-01-01 00:00:00'))

    def test_accuracy__year_gt(self):
        ts = utils.Timestamp.from_string('2005')
        self.assertTrue(ts > mktime('2004-12-31 23:59:59'))
        self.assertFalse(ts > mktime('2005-01-01 00:00:00'))
        self.assertFalse(ts > mktime('2005-06-15 12:30:15'))
        self.assertFalse(ts > mktime('2005-12-31 23:59:59'))
        self.assertFalse(ts > mktime('2006-01-01 00:00:00'))

    def test_accuracy__year_ge(self):
        ts = utils.Timestamp.from_string('2005')
        self.assertTrue(ts >= mktime('2004-12-31 23:59:59'))
        self.assertTrue(ts >= mktime('2005-01-01 00:00:00'))
        self.assertTrue(ts >= mktime('2005-06-15 12:30:15'))
        self.assertTrue(ts >= mktime('2005-12-31 23:59:59'))
        self.assertFalse(ts >= mktime('2006-01-01 00:00:00'))

    def test_accuracy__year_lt(self):
        ts = utils.Timestamp.from_string('2005')
        self.assertFalse(ts < mktime('2004-12-31 23:59:59'))
        self.assertFalse(ts < mktime('2005-01-01 00:00:00'))
        self.assertFalse(ts < mktime('2005-06-15 12:30:15'))
        self.assertFalse(ts < mktime('2005-12-31 23:59:59'))
        self.assertTrue(ts < mktime('2006-01-01 00:00:00'))

    def test_accuracy__year_le(self):
        ts = utils.Timestamp.from_string('2005')
        self.assertFalse(ts <= mktime('2004-12-31 23:59:59'))
        self.assertTrue(ts <= mktime('2005-01-01 00:00:00'))
        self.assertTrue(ts <= mktime('2005-06-15 12:30:15'))
        self.assertTrue(ts <= mktime('2005-12-31 23:59:59'))
        self.assertTrue(ts <= mktime('2006-01-01 00:00:00'))

    def test_accuracy__year_month_eq(self):
        ts = utils.Timestamp.from_string('2005-06')
        self.assertTrue(ts != mktime('2005-05-31 23:59:59'))
        self.assertTrue(ts == mktime('2005-06-01 00:00:00'))
        self.assertTrue(ts == mktime('2005-06-15 12:30:15'))
        self.assertTrue(ts == mktime('2005-06-30 23:59:59'))
        self.assertTrue(ts != mktime('2005-07-01 00:00:00'))

    def test_accuracy__year_month_gt(self):
        ts = utils.Timestamp.from_string('2005-06')
        self.assertTrue(ts > mktime('2005-05-31 23:59:59'))
        self.assertFalse(ts > mktime('2005-06-01 00:00:00'))
        self.assertFalse(ts > mktime('2005-06-15 12:30:15'))
        self.assertFalse(ts > mktime('2005-06-30 23:59:59'))
        self.assertFalse(ts > mktime('2005-07-01 00:00:00'))

    def test_accuracy__year_month_ge(self):
        ts = utils.Timestamp.from_string('2005-06')
        self.assertTrue(ts >= mktime('2005-05-31 23:59:59'))
        self.assertTrue(ts >= mktime('2005-06-01 00:00:00'))
        self.assertTrue(ts >= mktime('2005-06-15 12:30:15'))
        self.assertTrue(ts >= mktime('2005-06-30 23:59:59'))
        self.assertFalse(ts >= mktime('2005-07-01 00:00:00'))

    def test_accuracy__year_month_lt(self):
        ts = utils.Timestamp.from_string('2005-06')
        self.assertFalse(ts < mktime('2005-05-31 23:59:59'))
        self.assertFalse(ts < mktime('2005-06-01 00:00:00'))
        self.assertFalse(ts < mktime('2005-06-15 12:30:15'))
        self.assertFalse(ts < mktime('2005-06-30 23:59:59'))
        self.assertTrue(ts < mktime('2005-07-01 00:00:00'))

    def test_accuracy__year_month_le(self):
        ts = utils.Timestamp.from_string('2005-06')
        self.assertFalse(ts <= mktime('2005-05-31 23:59:59'))
        self.assertTrue(ts <= mktime('2005-06-01 00:00:00'))
        self.assertTrue(ts <= mktime('2005-06-15 12:30:15'))
        self.assertTrue(ts <= mktime('2005-06-30 23:59:59'))
        self.assertTrue(ts <= mktime('2005-07-01 00:00:00'))

    def test_accuracy__year_month_day_eq(self):
        ts = utils.Timestamp.from_string('2005-06-15')
        self.assertTrue(ts != mktime('2005-06-14 23:59:59'))
        self.assertTrue(ts == mktime('2005-06-15 00:00:00'))
        self.assertTrue(ts == mktime('2005-06-15 12:30:15'))
        self.assertTrue(ts == mktime('2005-06-15 23:59:59'))
        self.assertTrue(ts != mktime('2005-06-16 00:00:00'))

    def test_accuracy__year_month_day_gt(self):
        ts = utils.Timestamp.from_string('2005-06-15')
        self.assertTrue(ts > mktime('2005-06-14 23:59:59'))
        self.assertFalse(ts > mktime('2005-06-15 00:00:00'))
        self.assertFalse(ts > mktime('2005-06-15 12:30:15'))
        self.assertFalse(ts > mktime('2005-06-15 23:59:59'))
        self.assertFalse(ts > mktime('2005-06-16 00:00:00'))

    def test_accuracy__year_month_day_ge(self):
        ts = utils.Timestamp.from_string('2005-06-15')
        self.assertTrue(ts >= mktime('2005-06-14 23:59:59'))
        self.assertTrue(ts >= mktime('2005-06-15 00:00:00'))
        self.assertTrue(ts >= mktime('2005-06-15 12:30:15'))
        self.assertTrue(ts >= mktime('2005-06-15 23:59:59'))
        self.assertFalse(ts >= mktime('2005-06-16 00:00:00'))

    def test_accuracy__year_month_day_lt(self):
        ts = utils.Timestamp.from_string('2005-06-15')
        self.assertFalse(ts < mktime('2005-06-14 23:59:59'))
        self.assertFalse(ts < mktime('2005-06-15 00:00:00'))
        self.assertFalse(ts < mktime('2005-06-15 12:30:15'))
        self.assertFalse(ts < mktime('2005-06-15 23:59:59'))
        self.assertTrue(ts < mktime('2005-06-16 00:00:00'))

    def test_accuracy__year_month_day_le(self):
        ts = utils.Timestamp.from_string('2005-06-15')
        self.assertFalse(ts <= mktime('2005-06-14 23:59:59'))
        self.assertTrue(ts <= mktime('2005-06-15 00:00:00'))
        self.assertTrue(ts <= mktime('2005-06-15 12:30:15'))
        self.assertTrue(ts <= mktime('2005-06-15 23:59:59'))
        self.assertTrue(ts <= mktime('2005-06-16 00:00:00'))

    def test_accuracy__year_month_day_hour_minute_eq(self):
        ts = utils.Timestamp.from_string('2005-06-15 12:30')
        self.assertTrue(ts != mktime('2005-06-15 12:29:59'))
        self.assertTrue(ts == mktime('2005-06-15 12:30:00'))
        self.assertTrue(ts == mktime('2005-06-15 12:30:59'))
        self.assertTrue(ts != mktime('2005-06-15 12:31:00'))

    def test_accuracy__year_month_day_hour_minute_gt(self):
        ts = utils.Timestamp.from_string('2005-06-15 12:30')
        self.assertTrue(ts > mktime('2005-06-15 12:29:59'))
        self.assertFalse(ts > mktime('2005-06-15 12:30:00'))
        self.assertFalse(ts > mktime('2005-06-15 12:30:59'))
        self.assertFalse(ts > mktime('2005-06-15 12:31:00'))

    def test_accuracy__year_month_day_hour_minute_ge(self):
        ts = utils.Timestamp.from_string('2005-06-15 12:30')
        self.assertTrue(ts >= mktime('2005-06-15 12:29:59'))
        self.assertTrue(ts >= mktime('2005-06-15 12:30:00'))
        self.assertTrue(ts >= mktime('2005-06-15 12:30:59'))
        self.assertFalse(ts >= mktime('2005-06-15 12:31:00'))

    def test_accuracy__year_month_day_hour_minute_lt(self):
        ts = utils.Timestamp.from_string('2005-06-15 12:30')
        self.assertTrue(ts > mktime('2005-06-15 12:29:59'))
        self.assertFalse(ts > mktime('2005-06-15 12:30:00'))
        self.assertFalse(ts > mktime('2005-06-15 12:30:59'))
        self.assertFalse(ts > mktime('2005-06-15 12:31:00'))

    def test_accuracy__year_month_day_hour_minute_le(self):
        ts = utils.Timestamp.from_string('2005-06-15 12:30')
        self.assertTrue(ts >= mktime('2005-06-15 12:29:59'))
        self.assertTrue(ts >= mktime('2005-06-15 12:30:00'))
        self.assertTrue(ts >= mktime('2005-06-15 12:30:59'))
        self.assertFalse(ts >= mktime('2005-06-15 12:31:00'))

    def test_bool(self):
        for td in (utils.Timestamp(random.randint(-1000, 1000) * MIN),
                   utils.Timestamp(random.randint(-1000, 1000) * HOUR),
                   utils.Timestamp(random.randint(-1000, 1000) * DAY),
                   utils.Timestamp(random.randint(-1000, 1000) * MONTH),
                   utils.Timestamp(random.randint(-1000, 1000) * YEAR)):
            self.assertIs(bool(td), True)

        for td in (utils.Timestamp(utils.Timestamp.UNKNOWN),
                   utils.Timestamp(utils.Timestamp.NOT_APPLICABLE),
                   utils.Timestamp(utils.Timestamp.NEVER)):
            self.assertIs(bool(td), False)

        for td in (utils.Timestamp(utils.Timestamp.NOW),
                   utils.Timestamp(utils.Timestamp.SOON)):
            self.assertIs(bool(td), True)

    def test_sorting(self):
        now = 1e6
        lst = [utils.Timestamp(utils.Timestamp.NOW),
               utils.Timestamp(utils.Timestamp.SOON),
               utils.Timestamp(now + (-2 * HOUR)),
               utils.Timestamp(now + (2 * MIN)),
               utils.Timestamp(now + (3 * MIN)),
               utils.Timestamp(now + (1 * DAY)),
               utils.Timestamp(now + (2.5 * YEAR)),
               utils.Timestamp(utils.Timestamp.UNKNOWN),
               utils.Timestamp(utils.Timestamp.NOT_APPLICABLE)]

        def shuffle(l):
            return random.sample(l, k=len(l))

        for _ in range(10):
            self.assertEqual(sorted(shuffle(lst)), lst)
