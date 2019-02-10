from stig.client import ttypes

import unittest
from unittest.mock import patch
import time
from datetime import datetime


def mock_time(year=0, month=1, day=1, hour=0, minute=0, second=0):
    dt = datetime(year, month, day, hour, minute, second)
    print(f'mocking time: {dt.timestamp()} {dt}')
    def mock_time():
        return dt.timestamp()
    def mock_localtime(secs=None):
        if secs:
            return datetime.fromtimestamp(secs).timetuple()
        else:
            return dt.timetuple()
    return patch.multiple('time', time=mock_time, localtime=mock_localtime)


def mock_datetime(year=0, month=1, day=1, hour=0, minute=0, second=0):
    dt = datetime(year, month, day, hour, minute, second)
    print(f'mocking time: {dt.timestamp()} {dt}')
    class mock_datetime_datetime(datetime):
        def now(*args, **kwargs):
            return dt
    return patch('datetime.datetime', mock_datetime_datetime)


class TestTypes(unittest.TestCase):
    def test_Torrent_types(self):
        for t in ttypes.TYPES.values():
            self.assertTrue(isinstance(t, type) or t is None)

    def test_TorrentPeer_types(self):
        for t in ttypes.TorrentPeer.TYPES.values():
            self.assertTrue(isinstance(t, type) or t is None)

    def test_TorrentFile_types(self):
        for t in ttypes.TorrentFile.TYPES.values():
            self.assertTrue(isinstance(t, type) or t is None)

    def test_TorrentTracker_types(self):
        for t in ttypes.TorrentTracker.TYPES.values():
            self.assertTrue(isinstance(t, type) or t is None)


class TestSmartCmpStr(unittest.TestCase):
    def test_eq_ne(self):
        self.assertTrue(ttypes.SmartCmpStr('foo') == 'foo')
        self.assertTrue(ttypes.SmartCmpStr('Foo') == 'foo')
        self.assertTrue(ttypes.SmartCmpStr('foo') != 'Foo')

    def test_lt(self):
        self.assertFalse(ttypes.SmartCmpStr('foo') < 'foo')
        self.assertFalse(ttypes.SmartCmpStr('Foo') < 'foo')
        self.assertFalse(ttypes.SmartCmpStr('foo') < 'Foo')

    def test_le(self):
        self.assertTrue(ttypes.SmartCmpStr('foo') <= 'foo')
        self.assertTrue(ttypes.SmartCmpStr('Foo') <= 'foo')
        self.assertFalse(ttypes.SmartCmpStr('foo') <= 'Foo')

    def test_gt(self):
        self.assertFalse(ttypes.SmartCmpStr('foo') > 'foo')
        self.assertFalse(ttypes.SmartCmpStr('Foo') > 'foo')
        self.assertTrue(ttypes.SmartCmpStr('foo') > 'Foo')

    def test_ge(self):
        self.assertTrue(ttypes.SmartCmpStr('foo') >= 'foo')
        self.assertTrue(ttypes.SmartCmpStr('Foo') >= 'foo')
        self.assertTrue(ttypes.SmartCmpStr('foo') >= 'Foo')

    def test_contains(self):
        self.assertTrue('foo' in ttypes.SmartCmpStr('foo'))
        self.assertTrue('foo' in ttypes.SmartCmpStr('Foo'))
        self.assertFalse('Foo' in ttypes.SmartCmpStr('foo'))


class TestPath(unittest.TestCase):
    def test_eq_ne(self):
        self.assertTrue(ttypes.Path('/foo/bar/') == ttypes.Path('/foo/bar'))
        self.assertTrue(ttypes.Path('/foo/bar/./../bar/') == ttypes.Path('/foo/bar'))
        self.assertTrue(ttypes.Path('foo/bar') != ttypes.Path('/foo/bar'))


class TestRatio(unittest.TestCase):
    def test_string(self):
        self.assertEqual(ttypes.Ratio(0), 0)
        self.assertEqual(str(ttypes.Ratio(-1)), '')
        self.assertEqual(str(ttypes.Ratio(float('inf'))), '∞')
        self.assertEqual(str(ttypes.Ratio(0.0003)), '0')
        self.assertEqual(str(ttypes.Ratio(5.389)), '5.39')
        self.assertEqual(str(ttypes.Ratio(10.0234)), '10')
        self.assertEqual(str(ttypes.Ratio(47.86123)), '47.9')
        self.assertEqual(str(ttypes.Ratio(100.5)), '100')


class TestStatus(unittest.TestCase):
    def test_string(self):
        for s in (ttypes.Status.VERIFY, ttypes.Status.DOWNLOAD,
                  ttypes.Status.UPLOAD, ttypes.Status.INIT, ttypes.Status.CONNECTED,
                  ttypes.Status.QUEUED, ttypes.Status.SEED, ttypes.Status.IDLE,
                  ttypes.Status.STOPPED):
            self.assertEqual(ttypes.Status((s,)), (s,))

    def test_sort(self):
        statuses = [ttypes.Status.UPLOAD, ttypes.Status.CONNECTED,
                    ttypes.Status.SEED, ttypes.Status.INIT, ttypes.Status.VERIFY,
                    ttypes.Status.DOWNLOAD, ttypes.Status.STOPPED,
                    ttypes.Status.IDLE, ttypes.Status.QUEUED]
        sort = sorted([ttypes.Status((s,)) for s in statuses])
        exp = [(ttypes.Status.VERIFY,), (ttypes.Status.DOWNLOAD,),
               (ttypes.Status.UPLOAD,), (ttypes.Status.INIT,),
               (ttypes.Status.CONNECTED,), (ttypes.Status.QUEUED,),
               (ttypes.Status.IDLE,), (ttypes.Status.STOPPED,),
               (ttypes.Status.SEED,)]
        self.assertEqual(sort, exp)


MIN = 60
HOUR = 60*MIN
DAY = 24*HOUR
YEAR = 365.25*DAY
MONTH = YEAR / 12

class TestTimedelta(unittest.TestCase):
    def test_from_string__no_unit(self):
        self.assertEqual(ttypes.Timedelta.from_string('0'), 0)
        self.assertEqual(ttypes.Timedelta.from_string('60'), MIN)
        self.assertEqual(ttypes.Timedelta.from_string('600'), 10*MIN)

    def test_from_string__single_unit(self):
        self.assertEqual(ttypes.Timedelta.from_string('0s'), 0)
        self.assertEqual(ttypes.Timedelta.from_string('1s'), 1)
        self.assertEqual(ttypes.Timedelta.from_string('2m'), 2*MIN)
        self.assertEqual(ttypes.Timedelta.from_string('3h'), 3*HOUR)
        self.assertEqual(ttypes.Timedelta.from_string('4d'), 4*DAY)
        self.assertEqual(ttypes.Timedelta.from_string('2w'), 2*7*DAY)
        self.assertEqual(ttypes.Timedelta.from_string('6M'), 6*MONTH)
        self.assertEqual(ttypes.Timedelta.from_string('7y'), 7*YEAR)

    def test_from_string__multiple_units(self):
        self.assertEqual(ttypes.Timedelta.from_string('1d2h3m4s'), DAY + (2*HOUR) + (3*MIN) + 4)
        self.assertEqual(ttypes.Timedelta.from_string('4s1d2h3m'), DAY + (2*HOUR) + (3*MIN) + 4)

    def test_from_string__fractions(self):
        self.assertEqual(ttypes.Timedelta.from_string('2.5h.2m'), (2*HOUR) + (30*MIN) + 12)

    def test_from_string__too_large_numbers(self):
        self.assertEqual(ttypes.Timedelta.from_string('600'), 10*MIN)
        self.assertEqual(ttypes.Timedelta.from_string('600m'), 10*HOUR)
        self.assertEqual(ttypes.Timedelta.from_string('30h'), DAY + (6*HOUR))

    def test_from_string__signs(self):
        self.assertEqual(ttypes.Timedelta.from_string('-3h'), -3*HOUR)
        self.assertEqual(ttypes.Timedelta.from_string('+3h'), 3*HOUR)
        self.assertEqual(ttypes.Timedelta.from_string('-3h5s'), (-3*HOUR) - 5)
        self.assertEqual(ttypes.Timedelta.from_string('+3h5s'), (3*HOUR) + 5)

    def test_from_string__in_ago_notation(self):
        self.assertEqual(ttypes.Timedelta.from_string('in 1h30m20s'),  HOUR + (30*MIN) + 20)
        self.assertEqual(ttypes.Timedelta.from_string('-1.5h20s ago'), -HOUR - (30*MIN) - 20)

    def test_from_string__contradicting_signs(self):
        for string in ('in -1h', 'in 1h ago'):
            with self.assertRaises(ValueError) as exc:
                ttypes.Timedelta.from_string(string)

    def test_special_values(self):
        self.assertEqual(str(ttypes.Timedelta(0)), '0s')
        self.assertEqual(str(ttypes.Timedelta(0.4)), '0s')
        self.assertEqual(str(ttypes.Timedelta(-0.4)), '0s')
        self.assertEqual(str(ttypes.Timedelta(ttypes.Timedelta.NOT_APPLICABLE)), '')
        self.assertEqual(str(ttypes.Timedelta(ttypes.Timedelta.UNKNOWN)), '?')

    def test_added_subunits_for_small_numbers(self):
        self.assertEqual(str(ttypes.Timedelta(9*HOUR + 59*MIN + 59)), '9h59m')
        self.assertEqual(str(ttypes.Timedelta(10*HOUR + 59*MIN + 59)), '10h')

    def test_negative_delta(self):
        self.assertEqual(str(ttypes.Timedelta(-10)), '-10s')
        self.assertEqual(str(ttypes.Timedelta(-1*60 - 45)), '-1m45s')
        self.assertEqual(str(ttypes.Timedelta(-3*DAY - 2*HOUR)), '-3d2h')

    def test_preposition_string(self):
        self.assertEqual(ttypes.Timedelta(6 * DAY).with_preposition, 'in 6d')
        self.assertEqual(ttypes.Timedelta(-6 * DAY).with_preposition, '6d ago')
        self.assertEqual(ttypes.Timedelta(0.3).with_preposition, 'now')
        self.assertEqual(ttypes.Timedelta(-0.3).with_preposition, 'now')

    def test_sorting(self):
        lst = [ttypes.Timedelta(-2 * HOUR),
               ttypes.Timedelta(2 * MIN),
               ttypes.Timedelta(3 * MIN),
               ttypes.Timedelta(1 * DAY),
               ttypes.Timedelta(2.5 * YEAR),
               ttypes.Timedelta(ttypes.Timedelta.UNKNOWN),
               ttypes.Timedelta(ttypes.Timedelta.NOT_APPLICABLE)]

        import random
        def shuffle(l):
            return random.sample(l, k=len(l))

        for _ in range(10):
            self.assertEqual(sorted(shuffle(lst)), lst)

    def test_bool(self):
        import random
        for td in (ttypes.Timedelta(random.randint(-1e10, 1e10) * MIN),
                   ttypes.Timedelta(random.randint(-1e10, 1e10) * HOUR),
                   ttypes.Timedelta(random.randint(-1e10, 1e10) * DAY)):
            self.assertEqual(bool(td), True)

        for td in (ttypes.Timedelta(ttypes.Timedelta.UNKNOWN),
                   ttypes.Timedelta(ttypes.Timedelta.NOT_APPLICABLE)):
            self.assertEqual(bool(td), False)


class TestTimestamp(unittest.TestCase):
    def epoch(self, string):
        tstruct = time.strptime(string, '%Y-%m-%d %H:%M:%S')
        return time.mktime(tstruct)

    def test_string__year(self):
        ts = ttypes.Timestamp.from_string('2000')
        self.assertEqual(int(ts), self.epoch('2000-01-01 00:00:00'))
        ts = ttypes.Timestamp.from_string('2001')
        self.assertEqual(int(ts), self.epoch('2001-01-01 00:00:00'))

    def test_string__year_month(self):
        ts = ttypes.Timestamp.from_string('2000-01')
        self.assertEqual(int(ts), self.epoch('2000-01-01 00:00:00'))
        ts = ttypes.Timestamp.from_string('2000-12')
        self.assertEqual(int(ts), self.epoch('2000-12-01 00:00:00'))

    def test_string__year_month_day(self):
        ts = ttypes.Timestamp.from_string('2000-01-01')
        self.assertEqual(int(ts), self.epoch('2000-01-01 00:00:00'))
        ts = ttypes.Timestamp.from_string('2000-12-31')
        self.assertEqual(int(ts), self.epoch('2000-12-31 00:00:00'))

    def test_string__year_month_day_hour_minute(self):
        ts = ttypes.Timestamp.from_string('2000-01-01 12:03')
        self.assertEqual(int(ts), self.epoch('2000-01-01 12:03:00'))
        ts = ttypes.Timestamp.from_string('1999-12-31 23:59')
        self.assertEqual(int(ts), self.epoch('1999-12-31 23:59:00'))

    def test_string__year_month_day_hour_minute_second(self):
        ts = ttypes.Timestamp.from_string('1999-12-31 23:59:59')
        self.assertEqual(int(ts), self.epoch('1999-12-31 23:59:59'))
        ts = ttypes.Timestamp.from_string('2000-01-01 23:59:59')
        self.assertEqual(int(ts), self.epoch('2000-01-01 23:59:59'))

    def test_string__month_day(self):
        with mock_datetime(2000, 10, 15, 12, 30, 45):
            ts = ttypes.Timestamp.from_string('12-31')
            self.assertEqual(int(ts), self.epoch('2000-12-31 00:00:00'))
        with mock_datetime(2033, 5, 3, 3, 45, 12):
            ts = ttypes.Timestamp.from_string('01-31')
            self.assertEqual(int(ts), self.epoch('2033-01-31 00:00:00'))

    def test_string__month_day_hour_minute(self):
        with mock_datetime(1973, 10, 15, 12, 30, 45):
            ts = ttypes.Timestamp.from_string('03-15 17:39')
            self.assertEqual(int(ts), self.epoch('1973-03-15 17:39:00'))
        with mock_datetime(1904, 5, 3, 3, 45, 12):
            ts = ttypes.Timestamp.from_string('09-21 06:45')
            self.assertEqual(int(ts), self.epoch('1904-09-21 06:45:00'))

    def test_string__month_day_hour_minute_second(self):
        with mock_datetime(1845, 5, 17, 3, 29, 4):
            ts = ttypes.Timestamp.from_string('08-07 09:28:07')
            self.assertEqual(int(ts), self.epoch('1845-08-07 09:28:07'))
        with mock_datetime(2010, 4, 24, 18, 17, 57):
            ts = ttypes.Timestamp.from_string('10-20 05:03:14')
            self.assertEqual(int(ts), self.epoch('2010-10-20 05:03:14'))

    def test_string__hour_minute(self):
        with mock_datetime(2034, 11, 30, 11, 31, 22):
            ts = ttypes.Timestamp.from_string('12:32:23')
            self.assertEqual(int(ts), self.epoch('2034-11-30 12:32:23'))

    def test_string__hour_minute(self):
        with mock_datetime(1987, 6, 27, 22, 19, 13):
            ts = ttypes.Timestamp.from_string('19:33')
            self.assertEqual(int(ts), self.epoch('1987-06-27 19:33:00'))

    def test_string__year_hour_minute(self):
        with mock_datetime(2538, 1, 5, 7, 33, 11):
            ts = ttypes.Timestamp.from_string('2000 17:07')
            self.assertEqual(int(ts), self.epoch('2000-01-01 17:07:00'))

    def test_string_representation(self):
        with mock_time(1993, 2, 14, 5, 38, 12):
            self.assertEqual(str(ttypes.Timestamp(time.time())), '05:38:12')
            self.assertEqual(str(ttypes.Timestamp(time.time() - 60)), '05:37:12')
            self.assertEqual(str(ttypes.Timestamp(time.time() + 60)), '05:39:12')
            self.assertEqual(str(ttypes.Timestamp(time.time() - 3*60*60)), '02:38')
            self.assertEqual(str(ttypes.Timestamp(time.time() + 3*60*60)), '08:38')
            self.assertEqual(str(ttypes.Timestamp(time.time() - 7*24*60*60)), '1993-02-07')
            self.assertEqual(str(ttypes.Timestamp(time.time() + 7*24*60*60)), '1993-02-21')

    def test_accuracy__year_eq(self):
        ts = ttypes.Timestamp.from_string('2005')
        self.assertTrue(ts != self.epoch('2004-12-31 23:59:59'))
        self.assertTrue(ts == self.epoch('2005-01-01 00:00:00'))
        self.assertTrue(ts == self.epoch('2005-06-15 12:30:15'))
        self.assertTrue(ts == self.epoch('2005-12-31 23:59:59'))
        self.assertTrue(ts != self.epoch('2006-01-01 00:00:00'))

    def test_accuracy__year_gt(self):
        ts = ttypes.Timestamp.from_string('2005')
        self.assertTrue(ts > self.epoch('2004-12-31 23:59:59'))
        self.assertFalse(ts > self.epoch('2005-01-01 00:00:00'))
        self.assertFalse(ts > self.epoch('2005-06-15 12:30:15'))
        self.assertFalse(ts > self.epoch('2005-12-31 23:59:59'))
        self.assertFalse(ts > self.epoch('2006-01-01 00:00:00'))

    def test_accuracy__year_ge(self):
        ts = ttypes.Timestamp.from_string('2005')
        self.assertTrue(ts >= self.epoch('2004-12-31 23:59:59'))
        self.assertTrue(ts >= self.epoch('2005-01-01 00:00:00'))
        self.assertTrue(ts >= self.epoch('2005-06-15 12:30:15'))
        self.assertTrue(ts >= self.epoch('2005-12-31 23:59:59'))
        self.assertFalse(ts >= self.epoch('2006-01-01 00:00:00'))

    def test_accuracy__year_lt(self):
        ts = ttypes.Timestamp.from_string('2005')
        self.assertFalse(ts < self.epoch('2004-12-31 23:59:59'))
        self.assertFalse(ts < self.epoch('2005-01-01 00:00:00'))
        self.assertFalse(ts < self.epoch('2005-06-15 12:30:15'))
        self.assertFalse(ts < self.epoch('2005-12-31 23:59:59'))
        self.assertTrue(ts < self.epoch('2006-01-01 00:00:00'))

    def test_accuracy__year_le(self):
        ts = ttypes.Timestamp.from_string('2005')
        self.assertFalse(ts <= self.epoch('2004-12-31 23:59:59'))
        self.assertTrue(ts <= self.epoch('2005-01-01 00:00:00'))
        self.assertTrue(ts <= self.epoch('2005-06-15 12:30:15'))
        self.assertTrue(ts <= self.epoch('2005-12-31 23:59:59'))
        self.assertTrue(ts <= self.epoch('2006-01-01 00:00:00'))

    def test_accuracy__year_month_eq(self):
        ts = ttypes.Timestamp.from_string('2005-06')
        self.assertTrue(ts != self.epoch('2005-05-31 23:59:59'))
        self.assertTrue(ts == self.epoch('2005-06-01 00:00:00'))
        self.assertTrue(ts == self.epoch('2005-06-15 12:30:15'))
        self.assertTrue(ts == self.epoch('2005-06-30 23:59:59'))
        self.assertTrue(ts != self.epoch('2005-07-01 00:00:00'))

    def test_accuracy__year_month_gt(self):
        ts = ttypes.Timestamp.from_string('2005-06')
        self.assertTrue(ts > self.epoch('2005-05-31 23:59:59'))
        self.assertFalse(ts > self.epoch('2005-06-01 00:00:00'))
        self.assertFalse(ts > self.epoch('2005-06-15 12:30:15'))
        self.assertFalse(ts > self.epoch('2005-06-30 23:59:59'))
        self.assertFalse(ts > self.epoch('2005-07-01 00:00:00'))

    def test_accuracy__year_month_ge(self):
        ts = ttypes.Timestamp.from_string('2005-06')
        self.assertTrue(ts >= self.epoch('2005-05-31 23:59:59'))
        self.assertTrue(ts >= self.epoch('2005-06-01 00:00:00'))
        self.assertTrue(ts >= self.epoch('2005-06-15 12:30:15'))
        self.assertTrue(ts >= self.epoch('2005-06-30 23:59:59'))
        self.assertFalse(ts >= self.epoch('2005-07-01 00:00:00'))

    def test_accuracy__year_month_lt(self):
        ts = ttypes.Timestamp.from_string('2005-06')
        self.assertFalse(ts < self.epoch('2005-05-31 23:59:59'))
        self.assertFalse(ts < self.epoch('2005-06-01 00:00:00'))
        self.assertFalse(ts < self.epoch('2005-06-15 12:30:15'))
        self.assertFalse(ts < self.epoch('2005-06-30 23:59:59'))
        self.assertTrue(ts < self.epoch('2005-07-01 00:00:00'))

    def test_accuracy__year_month_le(self):
        ts = ttypes.Timestamp.from_string('2005-06')
        self.assertFalse(ts <= self.epoch('2005-05-31 23:59:59'))
        self.assertTrue(ts <= self.epoch('2005-06-01 00:00:00'))
        self.assertTrue(ts <= self.epoch('2005-06-15 12:30:15'))
        self.assertTrue(ts <= self.epoch('2005-06-30 23:59:59'))
        self.assertTrue(ts <= self.epoch('2005-07-01 00:00:00'))

    def test_accuracy__year_month_day_eq(self):
        ts = ttypes.Timestamp.from_string('2005-06-15')
        self.assertTrue(ts != self.epoch('2005-06-14 23:59:59'))
        self.assertTrue(ts == self.epoch('2005-06-15 00:00:00'))
        self.assertTrue(ts == self.epoch('2005-06-15 12:30:15'))
        self.assertTrue(ts == self.epoch('2005-06-15 23:59:59'))
        self.assertTrue(ts != self.epoch('2005-06-16 00:00:00'))

    def test_accuracy__year_month_day_gt(self):
        ts = ttypes.Timestamp.from_string('2005-06-15')
        self.assertTrue(ts > self.epoch('2005-06-14 23:59:59'))
        self.assertFalse(ts > self.epoch('2005-06-15 00:00:00'))
        self.assertFalse(ts > self.epoch('2005-06-15 12:30:15'))
        self.assertFalse(ts > self.epoch('2005-06-15 23:59:59'))
        self.assertFalse(ts > self.epoch('2005-06-16 00:00:00'))

    def test_accuracy__year_month_day_ge(self):
        ts = ttypes.Timestamp.from_string('2005-06-15')
        self.assertTrue(ts >= self.epoch('2005-06-14 23:59:59'))
        self.assertTrue(ts >= self.epoch('2005-06-15 00:00:00'))
        self.assertTrue(ts >= self.epoch('2005-06-15 12:30:15'))
        self.assertTrue(ts >= self.epoch('2005-06-15 23:59:59'))
        self.assertFalse(ts >= self.epoch('2005-06-16 00:00:00'))

    def test_accuracy__year_month_day_lt(self):
        ts = ttypes.Timestamp.from_string('2005-06-15')
        self.assertFalse(ts < self.epoch('2005-06-14 23:59:59'))
        self.assertFalse(ts < self.epoch('2005-06-15 00:00:00'))
        self.assertFalse(ts < self.epoch('2005-06-15 12:30:15'))
        self.assertFalse(ts < self.epoch('2005-06-15 23:59:59'))
        self.assertTrue(ts < self.epoch('2005-06-16 00:00:00'))

    def test_accuracy__year_month_day_le(self):
        ts = ttypes.Timestamp.from_string('2005-06-15')
        self.assertFalse(ts <= self.epoch('2005-06-14 23:59:59'))
        self.assertTrue(ts <= self.epoch('2005-06-15 00:00:00'))
        self.assertTrue(ts <= self.epoch('2005-06-15 12:30:15'))
        self.assertTrue(ts <= self.epoch('2005-06-15 23:59:59'))
        self.assertTrue(ts <= self.epoch('2005-06-16 00:00:00'))

    def test_accuracy__year_month_day_hour_minute_eq(self):
        ts = ttypes.Timestamp.from_string('2005-06-15 12:30')
        self.assertTrue(ts != self.epoch('2005-06-15 12:29:59'))
        self.assertTrue(ts == self.epoch('2005-06-15 12:30:00'))
        self.assertTrue(ts == self.epoch('2005-06-15 12:30:59'))
        self.assertTrue(ts != self.epoch('2005-06-15 12:31:00'))

    def test_accuracy__year_month_day_hour_minute_gt(self):
        ts = ttypes.Timestamp.from_string('2005-06-15 12:30')
        self.assertTrue(ts > self.epoch('2005-06-15 12:29:59'))
        self.assertFalse(ts > self.epoch('2005-06-15 12:30:00'))
        self.assertFalse(ts > self.epoch('2005-06-15 12:30:59'))
        self.assertFalse(ts > self.epoch('2005-06-15 12:31:00'))

    def test_accuracy__year_month_day_hour_minute_ge(self):
        ts = ttypes.Timestamp.from_string('2005-06-15 12:30')
        self.assertTrue(ts >= self.epoch('2005-06-15 12:29:59'))
        self.assertTrue(ts >= self.epoch('2005-06-15 12:30:00'))
        self.assertTrue(ts >= self.epoch('2005-06-15 12:30:59'))
        self.assertFalse(ts >= self.epoch('2005-06-15 12:31:00'))

    def test_accuracy__year_month_day_hour_minute_lt(self):
        ts = ttypes.Timestamp.from_string('2005-06-15 12:30')
        self.assertTrue(ts > self.epoch('2005-06-15 12:29:59'))
        self.assertFalse(ts > self.epoch('2005-06-15 12:30:00'))
        self.assertFalse(ts > self.epoch('2005-06-15 12:30:59'))
        self.assertFalse(ts > self.epoch('2005-06-15 12:31:00'))

    def test_accuracy__year_month_day_hour_minute_le(self):
        ts = ttypes.Timestamp.from_string('2005-06-15 12:30')
        self.assertTrue(ts >= self.epoch('2005-06-15 12:29:59'))
        self.assertTrue(ts >= self.epoch('2005-06-15 12:30:00'))
        self.assertTrue(ts >= self.epoch('2005-06-15 12:30:59'))
        self.assertFalse(ts >= self.epoch('2005-06-15 12:31:00'))

    def test_bool(self):
        import random
        for td in (ttypes.Timestamp(random.randint(-1000, 1000) * MIN),
                   ttypes.Timestamp(random.randint(-1000, 1000) * HOUR),
                   ttypes.Timestamp(random.randint(-1000, 1000) * DAY),
                   ttypes.Timestamp(random.randint(-1000, 1000) * MONTH),
                   ttypes.Timestamp(random.randint(-1000, 1000) * YEAR)):
            self.assertIs(bool(td), True)

        for td in (ttypes.Timestamp(ttypes.Timestamp.UNKNOWN),
                   ttypes.Timestamp(ttypes.Timestamp.NOT_APPLICABLE),
                   ttypes.Timestamp(ttypes.Timestamp.NEVER)):
            self.assertIs(bool(td), False)

        for td in (ttypes.Timestamp(ttypes.Timestamp.NOW),
                   ttypes.Timestamp(ttypes.Timestamp.SOON)):
            self.assertIs(bool(td), True)

    def test_sorting(self):
        now = 1e6
        lst = [ttypes.Timestamp(ttypes.Timestamp.NOW),
               ttypes.Timestamp(ttypes.Timestamp.SOON),
               ttypes.Timestamp(now + (-2 * HOUR)),
               ttypes.Timestamp(now + (2 * MIN)),
               ttypes.Timestamp(now + (3 * MIN)),
               ttypes.Timestamp(now + (1 * DAY)),
               ttypes.Timestamp(now + (2.5 * YEAR)),
               ttypes.Timestamp(ttypes.Timestamp.UNKNOWN),
               ttypes.Timestamp(ttypes.Timestamp.NOT_APPLICABLE)]

        import random
        def shuffle(l):
            return random.sample(l, k=len(l))

        for _ in range(10):
            self.assertEqual(sorted(shuffle(lst)), lst)


class TestTorrentFilePriority(unittest.TestCase):
    def test_int_values(self):
        for i in range(-2, 2):
            ttypes.TorrentFilePriority(i)
        for i in (-3, 2):
            with self.assertRaises(ValueError):
                ttypes.TorrentFilePriority(-3)

    def test_str_values(self):
        for s in ('off', 'low', 'normal', 'high'):
            ttypes.TorrentFilePriority(s)
        for s in ('offf', 'norm', 'adsf'):
            with self.assertRaises(ValueError):
                ttypes.TorrentFilePriority(s)

    def test_equality(self):
        for i,s in ((-2, 'off'), (-1, 'low'), (0, 'normal'), (1, 'high')):
            self.assertEqual(ttypes.TorrentFilePriority(i), s)
            self.assertEqual(ttypes.TorrentFilePriority(s), i)
            self.assertEqual(ttypes.TorrentFilePriority(i), ttypes.TorrentFilePriority(s))
            self.assertEqual(ttypes.TorrentFilePriority(s), ttypes.TorrentFilePriority(i))
            self.assertNotEqual(ttypes.TorrentFilePriority(s), 'foo')
            self.assertNotEqual(ttypes.TorrentFilePriority(s), None)
            self.assertNotEqual(ttypes.TorrentFilePriority(s), NotImplemented)

    def test_sort_order(self):
        prios = [
            ttypes.TorrentFilePriority(-2),
            ttypes.TorrentFilePriority(-1),
            ttypes.TorrentFilePriority(0),
            ttypes.TorrentFilePriority(1),
        ]

        import random
        def shuffle(l):
            return random.sample(l, k=len(l))

        for _ in range(10):
            self.assertEqual(sorted(shuffle(prios)), prios)
