from stig.client import tkeys as tkeys

import unittest
import time


class TestNumber(unittest.TestCase):
    def test_unit_and_prefix(self):
        n = tkeys.Number(1024, prefix='binary', unit='Potatoe')
        self.assertEqual(n, 1024)
        self.assertEqual(n.unit, 'Potatoe')
        self.assertEqual(n.with_unit, '1KiPotatoe')
        self.assertEqual(n.without_unit, '1Ki')

        n = tkeys.Number(1024, prefix='metric', unit='Potatoe')
        self.assertEqual(n, 1024)
        self.assertEqual(n.unit, 'Potatoe')
        self.assertEqual(n.with_unit, '1.02kPotatoe')
        self.assertEqual(n.without_unit, '1.02k')

        n = tkeys.Number(1000**3, prefix='metric', unit='foo')
        self.assertEqual(n, 1000**3)
        self.assertEqual(n.unit, 'foo')
        self.assertEqual(n.with_unit, '1Gfoo')
        self.assertEqual(n.without_unit, '1G')

        n = tkeys.Number(1000**3, prefix='binary', unit='foo')
        self.assertEqual(n, 1000**3)
        self.assertEqual(n.unit, 'foo')
        self.assertEqual(n.with_unit, '954Mifoo')
        self.assertEqual(n.without_unit, '954Mi')

    def test_no_unit(self):
        n = tkeys.Number(1000**3, prefix='binary')
        self.assertEqual(n, 1000**3)
        self.assertEqual(n.unit, None)
        self.assertEqual(str(n), '954Mi')

    def test_string_repr(self):
        for (num,str_metric,str_binary) in (
                (pow(1000, 1), '1k', '1000'),  (pow(1024, 1), '1.02k', '1Ki'),
                (pow(1000, 2), '1M', '977Ki'), (pow(1024, 2), '1.05M', '1Mi'),
                (pow(1000, 3), '1G', '954Mi'), (pow(1024, 3), '1.07G', '1Gi'),
                (pow(1000, 4), '1T', '931Gi'), (pow(1024, 4), '1.10T', '1Ti') ):

            num_metric = tkeys.Number(num, prefix='metric')
            self.assertEqual(num_metric, num)
            self.assertEqual(str(num_metric), str_metric)

            num_binary = tkeys.Number(num, prefix='binary')
            self.assertEqual(num_binary, num)
            self.assertEqual(str(num_binary), str_binary)

    def test_string_with_out_unit(self):
        n = tkeys.Number(1000, prefix='metric', unit='Balls')
        self.assertEqual(n.with_unit, '1kBalls')
        self.assertEqual(n.without_unit, '1k')

    def test_parsing_without_unit(self):
        for (string,num) in ( ('23', 23), ('23.1', 23.1),
                              ('23.2k',  23.2*pow(1000, 1)),
                              ('23.3Mi', 23.3*pow(1024, 2)),
                              ('23.4G',  23.4*pow(1000, 3)),
                              ('23.5Ti', 23.5*pow(1024, 4)) ):
            n = tkeys.Number(string)
            self.assertEqual(n, num)
            self.assertEqual(str(n), string)

    def test_parsing_with_unit(self):
        for (string,num) in ( ('23X', 23),
                              ('23.1X', 23.1),
                              ('23.2kX',  23.2*pow(1000, 1)),
                              ('23.3MiX', 23.3*pow(1024, 2)),
                              ('23.4GX',  23.4*pow(1000, 3)),
                              ('23.5TiX', 23.5*pow(1024, 4)) ):
            n = tkeys.Number(string)
            self.assertEqual(n, num)
            self.assertEqual(n.unit, 'X')
            self.assertEqual(n.with_unit, string)
            self.assertEqual(n.without_unit, string[:-1])

    def test_parsing_conflicting_units(self):
        n = tkeys.Number('123kF', unit='B')
        self.assertEqual(n, 123000)
        self.assertEqual(n.unit, 'F')

    def test_parsing_Number_instance(self):
        for prefix in ('binary', 'metric'):
            orig = tkeys.Number('1MB', prefix=prefix)

            n = tkeys.Number(orig)
            self.assertEqual(n, 1e6)
            self.assertEqual(n.unit, orig.unit)
            self.assertEqual(n.prefix, orig.prefix)

            for new_prefix in ('metric', 'binary'):
                n1 = tkeys.Number(orig, prefix=new_prefix)
                self.assertEqual(n1, 1e6)
                self.assertEqual(n1.unit, orig.unit)
                self.assertEqual(n1.prefix, new_prefix)

                n2 = tkeys.Number(orig, unit='b')
                self.assertEqual(n2, 1e6)
                self.assertEqual(n2.unit, 'b')
                self.assertEqual(n2.prefix, orig.prefix)

    def test_not_a_number(self):
        with self.assertRaises(ValueError):
            tkeys.Number('foo')

    def test_signs(self):
        self.assertEqual(tkeys.Number('-10'), -10)
        self.assertEqual(tkeys.Number('+10'), 10)
        self.assertEqual(tkeys.Number('-10k'), -10000)
        self.assertEqual(tkeys.Number('+10M'), 10e6)
        n = tkeys.Number('-10GX')
        self.assertEqual(n, -10e9)
        self.assertEqual(n.unit, 'X')
        n = tkeys.Number('-10Ty')
        self.assertEqual(n, -10e12)
        self.assertEqual(n.unit, 'y')

    def test_equality(self):
        self.assertEqual(tkeys.Number(0), 0)
        self.assertEqual(tkeys.Number(0), tkeys.Number(0))
        self.assertEqual(tkeys.Number(1024), 1024)
        self.assertEqual(tkeys.Number(1024), tkeys.Number(1024))
        self.assertNotEqual(tkeys.Number(1000), 1000.0001)
        self.assertNotEqual(tkeys.Number(1024), tkeys.Number(1023))

    def test_arithmetic_operation_returns_Number_instance(self):
        n = tkeys.Number(5) * 3000
        self.assertIsInstance(n, tkeys.Number)

    def test_arithmetic_operation_copies_unit(self):
        n = tkeys.Number(5, unit='X') / 3000
        self.assertEqual(n.unit, 'X')

    def test_arithmetic_operation_copies_prefix(self):
        for prfx in ('metric', 'binary'):
            n = tkeys.Number(5, prefix=prfx) - 3000
            self.assertEqual(n.prefix, prfx)

    def test_arithmetic_operation_copies_from_first_value(self):
        for prfx in ('metric', 'binary'):
            n = tkeys.Number(5,    unit='X', prefix=prfx) \
              * tkeys.Number(3000, unit='z', prefix='metric')
            self.assertEqual(n.unit, 'X')
            self.assertEqual(n.prefix, prfx)


class TestPercent(unittest.TestCase):
    def test_string(self):
        self.assertEqual(str(tkeys.Percent(0)), '0')
        self.assertEqual(str(tkeys.Percent(0.129)), '0.13')
        self.assertEqual(str(tkeys.Percent(1)), '1')
        self.assertEqual(str(tkeys.Percent(9.3456)), '9.35')
        self.assertEqual(str(tkeys.Percent(10.6543)), '10.7')
        self.assertEqual(str(tkeys.Percent(100)), '100')
        self.assertEqual(str(tkeys.Percent(100.6)), '101')


class TestSmartCmpStr(unittest.TestCase):
    def test_eq_ne(self):
        self.assertTrue(tkeys.SmartCmpStr('foo') == 'foo')
        self.assertTrue(tkeys.SmartCmpStr('foo') != 'bar')
        self.assertTrue(tkeys.SmartCmpStr('foo') != '3')

    def test_lt(self):
        self.assertTrue(tkeys.SmartCmpStr('foo') < '4')
        self.assertTrue(tkeys.SmartCmpStr('aaa') < 'bbb')
        self.assertFalse(tkeys.SmartCmpStr('foo') < '3')
        self.assertFalse(tkeys.SmartCmpStr('def') < 'abc')

    def test_gt(self):
        self.assertTrue(tkeys.SmartCmpStr('foo') > '2')
        self.assertTrue(tkeys.SmartCmpStr('bbb') > 'aaa')
        self.assertFalse(tkeys.SmartCmpStr('foo') > '3')
        self.assertFalse(tkeys.SmartCmpStr('abc') > 'def')

    def test_le(self):
        self.assertTrue(tkeys.SmartCmpStr('foo') <= '3')
        self.assertTrue(tkeys.SmartCmpStr('foo') <= '4')
        self.assertTrue(tkeys.SmartCmpStr('abc') <= 'def')
        self.assertTrue(tkeys.SmartCmpStr('abc') <= 'zoo')

        self.assertFalse(tkeys.SmartCmpStr('foo') <= '2')
        self.assertFalse(tkeys.SmartCmpStr('zoo') <= 'aaa')

    def test_ge(self):
        self.assertTrue(tkeys.SmartCmpStr('foo') >= '3')
        self.assertTrue(tkeys.SmartCmpStr('foo') >= '2')
        self.assertTrue(tkeys.SmartCmpStr('zoo') >= 'zoo')
        self.assertTrue(tkeys.SmartCmpStr('zoo') >= 'abc')

        self.assertFalse(tkeys.SmartCmpStr('foo') >= '4')
        self.assertFalse(tkeys.SmartCmpStr('foo') >= 'zoo')

    def test_contains(self):
        # Case-insensitive
        self.assertTrue('oo' in tkeys.SmartCmpStr('foo'))
        self.assertTrue('oo' in tkeys.SmartCmpStr('FOO'))

        # Case-sensitive
        self.assertFalse('OO' in tkeys.SmartCmpStr('foo'))
        self.assertTrue('OO' in tkeys.SmartCmpStr('FOO'))


class TestPath(unittest.TestCase):
    def test_eq_ne(self):
        self.assertTrue(tkeys.Path('/foo/bar/') == tkeys.Path('/foo/bar'))
        self.assertTrue(tkeys.Path('/foo/bar/./../bar/') == tkeys.Path('/foo/bar'))
        self.assertTrue(tkeys.Path('foo/bar') != tkeys.Path('/foo/bar'))


class TestRatio(unittest.TestCase):
    def test_string(self):
        self.assertEqual(tkeys.Ratio(0), 0)
        self.assertEqual(str(tkeys.Ratio(-1)), '?')
        self.assertEqual(str(tkeys.Ratio(0.0003)), '0')
        self.assertEqual(str(tkeys.Ratio(5.389)), '5.39')
        self.assertEqual(str(tkeys.Ratio(10.0234)), '10.0')
        self.assertEqual(str(tkeys.Ratio(47.86123)), '47.9')
        self.assertEqual(str(tkeys.Ratio(100.5)), '100')


class TestStatus(unittest.TestCase):
    def test_string(self):
        for s in (tkeys.Status.VERIFY, tkeys.Status.DOWNLOAD,
                  tkeys.Status.UPLOAD, tkeys.Status.INIT, tkeys.Status.CONNECTED,
                  tkeys.Status.QUEUED, tkeys.Status.SEED, tkeys.Status.IDLE,
                  tkeys.Status.STOPPED):
            self.assertEqual(tkeys.Status((s,)), (s,))

    def test_sort(self):
        statuses = [tkeys.Status.UPLOAD, tkeys.Status.CONNECTED,
                    tkeys.Status.SEED, tkeys.Status.INIT, tkeys.Status.VERIFY,
                    tkeys.Status.DOWNLOAD, tkeys.Status.STOPPED,
                    tkeys.Status.IDLE, tkeys.Status.QUEUED]
        sort = sorted([tkeys.Status((s,)) for s in statuses])
        exp = [(tkeys.Status.VERIFY,), (tkeys.Status.DOWNLOAD,),
               (tkeys.Status.UPLOAD,), (tkeys.Status.INIT,),
               (tkeys.Status.CONNECTED,), (tkeys.Status.QUEUED,),
               (tkeys.Status.IDLE,), (tkeys.Status.STOPPED,),
               (tkeys.Status.SEED,)]
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
                            ('600m', 36000, '10h'),
                            ('1h', 3600, '1h'),
                            ('24.5h', 3600*24.5, '1d'),
                            ('370d', 3600*24*370, '1y')):
            t = tkeys.Timedelta.from_string(s)
            self.assertEqual(t, i)
            self.assertEqual(str(t), s_exp)

        with self.assertRaises(ValueError) as cm:
            tkeys.Timedelta.from_string('')
        with self.assertRaises(ValueError) as cm:
            tkeys.Timedelta.from_string('x')
        with self.assertRaises(ValueError) as cm:
            tkeys.Timedelta.from_string('1.2.3')

    def test_special_values(self):
        self.assertEqual(str(tkeys.Timedelta(0)), 'now')
        self.assertEqual(str(tkeys.Timedelta(tkeys.Timedelta.NOT_APPLICABLE)), '')
        self.assertEqual(str(tkeys.Timedelta(tkeys.Timedelta.UNKNOWN)), '?')

    def test_even_units(self):
        for unit,char in ((1, 's'), (MIN, 'm'), (HOUR, 'h'), (DAY, 'd'), (YEAR, 'y')):
            for i in range(11, 20):
                self.assertEqual(str(tkeys.Timedelta(i * unit)), '%d%s' % (i, char))

    def test_subunits_with_small_numbers(self):
        self.assertEqual(str(tkeys.Timedelta(1*DAY + 0*HOUR + 59*MIN + 59)), '1d')
        self.assertEqual(str(tkeys.Timedelta(1*DAY + 23*HOUR + 59*MIN + 59)), '1d23h')

        self.assertEqual(str(tkeys.Timedelta(9*DAY + 0*HOUR + 59*MIN + 59)), '9d')
        self.assertEqual(str(tkeys.Timedelta(9*DAY + 23*HOUR + 59*MIN + 59)), '9d23h')

        self.assertEqual(str(tkeys.Timedelta(10*DAY + 23*HOUR + 59*MIN + 59)), '10d')

    def test_negative_delta(self):
        self.assertEqual(str(tkeys.Timedelta(-10)), '-10s')
        self.assertEqual(str(tkeys.Timedelta(-1*60 - 45)), '-1m45s')
        self.assertEqual(str(tkeys.Timedelta(-3*DAY - 2*HOUR)), '-3d2h')

    def test_preposition_string(self):
        self.assertEqual(tkeys.Timedelta(7 * DAY).with_preposition, 'in 7d')
        self.assertEqual(tkeys.Timedelta(-7 * DAY).with_preposition, '7d ago')

    def test_sorting(self):
        lst = [tkeys.Timedelta(-2 * HOUR),
               tkeys.Timedelta(2 * MIN),
               tkeys.Timedelta(3 * MIN),
               tkeys.Timedelta(1 * DAY),
               tkeys.Timedelta(2.5 * YEAR),
               tkeys.Timedelta(tkeys.Timedelta.UNKNOWN),
               tkeys.Timedelta(tkeys.Timedelta.NOT_APPLICABLE)]

        import random
        def shuffle(l):
            return random.sample(l, k=len(l))

        for _ in range(10):
            self.assertEqual(sorted(shuffle(lst)), lst)

    def test_bool(self):
        import random
        for td in (tkeys.Timedelta(random.randint(-1e10, 1e10) * MIN),
                   tkeys.Timedelta(random.randint(-1e10, 1e10) * HOUR),
                   tkeys.Timedelta(random.randint(-1e10, 1e10) * DAY)):
            self.assertEqual(bool(td), True)

        for td in (tkeys.Timedelta(tkeys.Timedelta.UNKNOWN),
                   tkeys.Timedelta(tkeys.Timedelta.NOT_APPLICABLE)):
            self.assertEqual(bool(td), False)



class TestTimestamp(unittest.TestCase):
    def strftime(self, format, timestamp):
        return time.strftime(format, time.localtime(timestamp))

    def test_string(self):
        now = time.time()
        self.assertEqual(str(tkeys.Timestamp(now)), self.strftime('%H:%M', now))
        later_today = now + 20*60*60
        self.assertEqual(str(tkeys.Timestamp(later_today)),
                         self.strftime('%H:%M', later_today))
        next_week = now + 7*24*60*60
        self.assertEqual(str(tkeys.Timestamp(next_week)),
                         self.strftime('%Y-%m-%d', next_week))

    def test_bool(self):
        import random
        for td in (tkeys.Timestamp(random.randint(-1e10, 1e10) * MIN),
                   tkeys.Timestamp(random.randint(-1e10, 1e10) * HOUR),
                   tkeys.Timestamp(random.randint(-1e10, 1e10) * DAY)):
            self.assertEqual(bool(td), True)

        for td in (tkeys.Timestamp(tkeys.Timestamp.UNKNOWN),
                   tkeys.Timestamp(tkeys.Timestamp.NOT_APPLICABLE)):
            self.assertEqual(bool(td), False)

    def test_sorting(self):
        now = time.time()
        lst = [tkeys.Timestamp(tkeys.Timestamp.NOT_APPLICABLE),
               tkeys.Timestamp(tkeys.Timestamp.UNKNOWN),
               tkeys.Timestamp(now + (-2 * HOUR)),
               tkeys.Timestamp(now + (2 * MIN)),
               tkeys.Timestamp(now + (3 * MIN)),
               tkeys.Timestamp(now + (1 * DAY)),
               tkeys.Timestamp(now + (2.5 * YEAR))]

        import random
        def shuffle(l):
            return random.sample(l, k=len(l))

        for _ in range(10):
            self.assertEqual(sorted(shuffle(lst)), lst)

