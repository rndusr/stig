from stig.client import ttypes

import unittest
import time


class TestPercent(unittest.TestCase):
    def test_string(self):
        self.assertEqual(str(ttypes.Percent(0)), '0%')
        self.assertEqual(str(ttypes.Percent(0.129)), '0.13%')
        self.assertEqual(str(ttypes.Percent(1)), '1%')
        self.assertEqual(str(ttypes.Percent(9.3456)), '9.35%')
        self.assertEqual(str(ttypes.Percent(10.6543)), '10.7%')
        self.assertEqual(str(ttypes.Percent(100)), '100%')
        self.assertEqual(str(ttypes.Percent(100.6)), '101%')


class TestSmartCmpStr(unittest.TestCase):
    def test_eq_ne(self):
        self.assertTrue(ttypes.SmartCmpStr('foo') == 'foo')
        self.assertTrue(ttypes.SmartCmpStr('foo') != 'bar')
        self.assertTrue(ttypes.SmartCmpStr('foo') != '3')

    def test_lt(self):
        self.assertTrue(ttypes.SmartCmpStr('foo') < '4')
        self.assertTrue(ttypes.SmartCmpStr('aaa') < 'bbb')
        self.assertFalse(ttypes.SmartCmpStr('foo') < '3')
        self.assertFalse(ttypes.SmartCmpStr('def') < 'abc')

    def test_gt(self):
        self.assertTrue(ttypes.SmartCmpStr('foo') > '2')
        self.assertTrue(ttypes.SmartCmpStr('bbb') > 'aaa')
        self.assertFalse(ttypes.SmartCmpStr('foo') > '3')
        self.assertFalse(ttypes.SmartCmpStr('abc') > 'def')

    def test_le(self):
        self.assertTrue(ttypes.SmartCmpStr('foo') <= '3')
        self.assertTrue(ttypes.SmartCmpStr('foo') <= '4')
        self.assertTrue(ttypes.SmartCmpStr('abc') <= 'def')
        self.assertTrue(ttypes.SmartCmpStr('abc') <= 'zoo')

        self.assertFalse(ttypes.SmartCmpStr('foo') <= '2')
        self.assertFalse(ttypes.SmartCmpStr('zoo') <= 'aaa')

    def test_ge(self):
        self.assertTrue(ttypes.SmartCmpStr('foo') >= '3')
        self.assertTrue(ttypes.SmartCmpStr('foo') >= '2')
        self.assertTrue(ttypes.SmartCmpStr('zoo') >= 'zoo')
        self.assertTrue(ttypes.SmartCmpStr('zoo') >= 'abc')

        self.assertFalse(ttypes.SmartCmpStr('foo') >= '4')
        self.assertFalse(ttypes.SmartCmpStr('foo') >= 'zoo')

    def test_contains(self):
        # Case-insensitive
        self.assertTrue('oo' in ttypes.SmartCmpStr('foo'))
        self.assertTrue('oo' in ttypes.SmartCmpStr('FOO'))

        # Case-sensitive
        self.assertFalse('OO' in ttypes.SmartCmpStr('foo'))
        self.assertTrue('OO' in ttypes.SmartCmpStr('FOO'))


class TestPath(unittest.TestCase):
    def test_eq_ne(self):
        self.assertTrue(ttypes.Path('/foo/bar/') == ttypes.Path('/foo/bar'))
        self.assertTrue(ttypes.Path('/foo/bar/./../bar/') == ttypes.Path('/foo/bar'))
        self.assertTrue(ttypes.Path('foo/bar') != ttypes.Path('/foo/bar'))


class TestRatio(unittest.TestCase):
    def test_string(self):
        self.assertEqual(ttypes.Ratio(0), 0)
        self.assertEqual(str(ttypes.Ratio(-1)), '?')
        self.assertEqual(str(ttypes.Ratio(0.0003)), '0')
        self.assertEqual(str(ttypes.Ratio(5.389)), '5.39')
        self.assertEqual(str(ttypes.Ratio(10.0234)), '10.0')
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
class TestTimedelta(unittest.TestCase):
    def test_from_string(self):
        for s, i, s_exp in (('0', 0, 'now'),
                            ('0d', 0, 'now'),
                            ('600', 600, '10m'),
                            ('1m270s', 330, '5m30s'),
                            ('1m270', 330, '5m30s'),
                            ('600m', 36000, '10h'),
                            ('1h10m', 4200, '1h10m'),
                            ('1h10m2d', 4200+(2*24*3600), '2d1h'),
                            ('24.5h', 3600*24.5, '1d'),
                            ('1y370d', YEAR+(DAY*370), '2y')):
            t = ttypes.Timedelta.from_string(s)
            self.assertEqual(t, i)
            self.assertEqual(str(t), s_exp)

        for string in ('', 'x', '?m', '1.2.3', '5g10s', '1y2x10d'):
            with self.assertRaises(ValueError) as cm:
                ttypes.Timedelta.from_string(string)

    def test_special_values(self):
        self.assertEqual(str(ttypes.Timedelta(0)), 'now')
        self.assertEqual(str(ttypes.Timedelta(ttypes.Timedelta.NOT_APPLICABLE)), '')
        self.assertEqual(str(ttypes.Timedelta(ttypes.Timedelta.UNKNOWN)), '?')

    def test_even_units(self):
        for unit,char in ((1, 's'), (MIN, 'm'), (HOUR, 'h'), (DAY, 'd'), (YEAR, 'y')):
            for i in range(11, 20):
                self.assertEqual(str(ttypes.Timedelta(i * unit)), '%d%s' % (i, char))

    def test_subunits_with_small_numbers(self):
        self.assertEqual(str(ttypes.Timedelta(1*DAY + 0*HOUR + 59*MIN + 59)), '1d')
        self.assertEqual(str(ttypes.Timedelta(1*DAY + 23*HOUR + 59*MIN + 59)), '1d23h')

        self.assertEqual(str(ttypes.Timedelta(9*DAY + 0*HOUR + 59*MIN + 59)), '9d')
        self.assertEqual(str(ttypes.Timedelta(9*DAY + 23*HOUR + 59*MIN + 59)), '9d23h')

        self.assertEqual(str(ttypes.Timedelta(10*DAY + 23*HOUR + 59*MIN + 59)), '10d')

    def test_negative_delta(self):
        self.assertEqual(str(ttypes.Timedelta(-10)), '-10s')
        self.assertEqual(str(ttypes.Timedelta(-1*60 - 45)), '-1m45s')
        self.assertEqual(str(ttypes.Timedelta(-3*DAY - 2*HOUR)), '-3d2h')

    def test_preposition_string(self):
        self.assertEqual(ttypes.Timedelta(7 * DAY).with_preposition, 'in 7d')
        self.assertEqual(ttypes.Timedelta(-7 * DAY).with_preposition, '7d ago')

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
    def strftime(self, format, timestamp):
        return time.strftime(format, time.localtime(timestamp))

    def strptime(self, string):
        tstruct = time.strptime(string, '%Y-%m-%d %H:%M:%S')
        return time.mktime(tstruct)

    now = time.time()
    year = time.localtime(now).tm_year
    month = time.localtime(now).tm_mon
    day = time.localtime(now).tm_mday

    def test_from_string(self):
        for s,s_exp in (('      2015', '2015-01-01 00:00:00'),
                        ('   2105-02', '2105-02-01 00:00:00'),
                        ('2051-03-10', '2051-03-10 00:00:00'),
                        ('     04-11', '%04d-04-11 00:00:00' % self.year),
                        ('        17', '%04d-%02d-17 00:00:00' % (self.year, self.month)),
                        ('           05:30', '%04d-%02d-%02d 05:30:00' % (self.year, self.month, self.day)),
                        ('        09 06:12', '%04d-%02d-09 06:12:00' % (self.year, self.month)),
                        ('     06-16 06:40', '%04d-06-16 06:40:00' % (self.year)),
                        ('2021-12-31 23:59', '2021-12-31 23:59:00'),
                        ('2001-10    19:04', '2001-10-01 19:04:00'),
                        ('2014       07:43', '2014-01-01 07:43:00')):
            t = ttypes.Timestamp.from_string(s)
            t_exp = self.strptime(s_exp)
            self.assertEqual(t, t_exp)

        with self.assertRaises(ValueError) as cm:
            ttypes.Timestamp.from_string('foo')
        self.assertIn('Invalid format', str(cm.exception))
        self.assertIn('foo', str(cm.exception))

    def test_string(self):
        self.assertEqual(str(ttypes.Timestamp(self.now)), self.strftime('%H:%M', self.now))
        later_today = self.now + 20*60*60
        self.assertEqual(str(ttypes.Timestamp(later_today)),
                         self.strftime('%H:%M', later_today))
        next_week = self.now + 7*24*60*60
        self.assertEqual(str(ttypes.Timestamp(next_week)),
                         self.strftime('%Y-%m-%d', next_week))

    def test_bool(self):
        import random
        for td in (ttypes.Timestamp(random.randint(-1e10, 1e10) * MIN),
                   ttypes.Timestamp(random.randint(-1e10, 1e10) * HOUR),
                   ttypes.Timestamp(random.randint(-1e10, 1e10) * DAY)):
            self.assertEqual(bool(td), True)

        for td in (ttypes.Timestamp(ttypes.Timestamp.UNKNOWN),
                   ttypes.Timestamp(ttypes.Timestamp.NOT_APPLICABLE)):
            self.assertEqual(bool(td), False)

    def test_sorting(self):
        lst = [ttypes.Timestamp(ttypes.Timestamp.NOT_APPLICABLE),
               ttypes.Timestamp(ttypes.Timestamp.UNKNOWN),
               ttypes.Timestamp(self.now + (-2 * HOUR)),
               ttypes.Timestamp(self.now + (2 * MIN)),
               ttypes.Timestamp(self.now + (3 * MIN)),
               ttypes.Timestamp(self.now + (1 * DAY)),
               ttypes.Timestamp(self.now + (2.5 * YEAR))]

        import random
        def shuffle(l):
            return random.sample(l, k=len(l))

        for _ in range(10):
            self.assertEqual(sorted(shuffle(lst)), lst)

