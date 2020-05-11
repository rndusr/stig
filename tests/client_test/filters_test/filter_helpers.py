from datetime import datetime
from unittest.mock import patch

import contextlib

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


class HelpersMixin():
    def check_getting_spec_by_alias(self, filter_cls):
        for specdict in (filter_cls.BOOLEAN_FILTERS, filter_cls.COMPARATIVE_FILTERS):
            for name,spec in specdict.items():
                for alias in spec.aliases:
                    self.assertEqual(specdict[alias], specdict[name])

    def check_filter(self, filter_cls, items, filter_names, test_cases):
        assert all('id' in item for item in items), "All items must have an 'id' field: %r" % (items,)
        for fn in filter_names:
            # filter_string must contain '{name}' as a placeholder for the
            # filter name or one of its aliases
            for filter_string, exp_ids in test_cases:
                f = filter_string.format(name=fn)
                # TODO: Don't rely on "id" (or any other) key (see
                # settings.Settings.as_dict and
                # client.aiotransmission.api_torrent.SettingsAPI.as_dict)
                self.assertEqual(tuple(filter_cls(f).apply(items, key='id')), exp_ids)

    def check_int_filter(self, filter_cls, filter_names, key):
        self.check_filter(filter_cls=filter_cls,
                          filter_names=filter_names,
                          items=({'id': 1, key: 0},
                                 {'id': 2, key: 17},
                                 {'id': 3, key: 42e23}),
                          test_cases=(('{name}', (2, 3)),
                                      ('!{name}', (1,)),
                                      ('{name}=17', (2,)),
                                      ('{name}!=17', (1, 3)),
                                      ('{name}>17', (3,)),
                                      ('{name}<17', (1,)),
                                      ('{name}>=17', (2, 3)),
                                      ('{name}<=17', (1, 2))))
        for fn in filter_names:
            with self.assertRaises(ValueError) as cm:
                filter_cls('%s~1' % (fn,))
            self.assertEqual(str(cm.exception), "Invalid operator for filter '%s': ~" % (filter_names[0],))

    def check_float_filter(self, filter_cls, filter_names, key):
        self.check_filter(filter_cls=filter_cls,
                          filter_names=filter_names,
                          items=({'id': 1, key: 0},
                                 {'id': 2, key: 17.5},
                                 {'id': 3, key: 42.123}),
                          test_cases=(('{name}', (2, 3)),
                                      ('!{name}', (1,)),
                                      ('{name}=17.5', (2,)),
                                      ('{name}!=17.5', (1, 3)),
                                      ('{name}>17.5', (3,)),
                                      ('{name}<17.5', (1,)),
                                      ('{name}>=17.5', (2, 3)),
                                      ('{name}<=17.5', (1, 2))))
        for fn in filter_names:
            with self.assertRaises(ValueError) as cm:
                filter_cls('%s~1.05' % (fn,))
            self.assertEqual(str(cm.exception), "Invalid operator for filter '%s': ~" % (filter_names[0],))

    def check_str_filter(self, filter_cls, filter_names, key):
        self.check_filter(filter_cls=filter_cls,
                          filter_names=filter_names,
                          items=({'id': 1, key: 'foo'},
                                 {'id': 2, key: 'bar'},
                                 {'id': 3, key: 'baz'},
                                 {'id': 4, key: ''}),
                          test_cases=(('{name}', (1, 2, 3)),
                                      ('!{name}', (4,)),
                                      ('{name}=foo', (1,)),
                                      ('{name}!=foo', (2, 3, 4)),
                                      ('{name}~ba', (2, 3)),
                                      ('{name}!~ba', (1, 4)),
                                      ('{name}=~b+', (2,3)),
                                      ('{name}!=~^r', (1, 2, 3, 4))))
        for fn in filter_names:
            with self.assertRaises(ValueError) as cm:
                filter_cls('{name}=~['.format(name=fn))
            assert str(cm.exception) == "Invalid regular expression: Unterminated character set at position 0: ["

    def check_bool_filter(self, filter_cls, filter_names, **kwargs):
        self.check_filter(filter_cls=filter_cls, filter_names=filter_names, **kwargs)

        for fn in filter_names:
            for op in filter_cls.OPERATORS:
                with self.assertRaises(ValueError) as cm:
                    filter_cls('%s%s' % (fn, op))
                self.assertEqual(str(cm.exception), "Boolean filter does not take an operator: %s" % (filter_names[0],))

                with self.assertRaises(ValueError) as cm:
                    filter_cls('%s%sfoo' % (fn, op))
                self.assertEqual(str(cm.exception), "Boolean filter does not take a value: %s" % (filter_names[0],))

                with self.assertRaises(ValueError) as cm:
                    filter_cls('%s%s0' % (fn, op))
                self.assertEqual(str(cm.exception), "Boolean filter does not take a value: %s" % (filter_names[0],))


    def check_limit_rate_filter(self, filter_cls, filter_names, key):
        from stig.client.utils import BoolOrBandwidth
        from stig.client.constants import UNLIMITED
        self.check_filter(filter_cls,
                          filter_names=filter_names,
                          items=({'id': 1, key: BoolOrBandwidth(1000)},
                                 {'id': 2, key: BoolOrBandwidth(2048)},
                                 {'id': 3, key: UNLIMITED}),
                          test_cases=(('{name}', (1, 2)),
                                      ('!{name}', (3,)),

                                      ('{name}=2048', (2,)),
                                      ('{name}!=2048', (1, 3)),
                                      ('{name}<2048', (1,)),
                                      ('{name}>2048', (3,)),
                                      ('{name}<=2048', (1, 2)),
                                      ('{name}>=2048', (2, 3)),

                                      ('{name}=1k', (1,)),
                                      ('{name}=2k', ()),
                                      ('{name}=1Ki', ()),
                                      ('{name}=2Ki', (2,)),

                                      ('{name}=limited', (1, 2)),
                                      ('{name}!=limited', (3,)),
                                      ('{name}<limited', ()),
                                      ('{name}>limited', (3,)),
                                      ('{name}<=limited', (1, 2)),
                                      ('{name}>=limited', (3,)),

                                      ('{name}=unlimited', (3,)),
                                      ('{name}!=unlimited', (1, 2)),
                                      ('{name}<unlimited', (1, 2)),
                                      ('{name}>unlimited', ()),
                                      ('{name}<=unlimited', (1, 2, 3)),
                                      ('{name}>=unlimited', (3,))))

    def check_timestamp_filter(self, filter_cls, filter_names, key, default_sign):
        from stig.client.ttypes import Timestamp
        items = ({'id': 1, key: Timestamp.from_string('2001-01-01')},
                 {'id': 2, key: Timestamp.from_string('2002-01-01')},
                 {'id': 3, key: Timestamp.from_string('2003-01-01')},
                 {'id': 4, key: Timestamp(Timestamp.NOW)},
                 {'id': 5, key: Timestamp(Timestamp.SOON)},
                 {'id': 6, key: Timestamp(Timestamp.UNKNOWN)},
                 {'id': 7, key: Timestamp(Timestamp.NOT_APPLICABLE)},
                 {'id': 8, key: Timestamp(Timestamp.NEVER)})

        for fn in filter_names:
            self._check_timestamp_as_bool(filter_cls, fn, key, items)
            self._check_timestamp_with_absolute_times(filter_cls, fn, key, items)
            self._check_timestamp_with_relative_times(filter_cls, fn, key, items)
            self._check_timestamp_with_constants(filter_cls, fn, key, items)
            if default_sign == 1:
                self._check_timestamp_with_positive_default_sign(filter_cls, fn, key, items)
            elif default_sign == -1:
                self._check_timestamp_with_negative_default_sign(filter_cls, fn, key, items)
            else:
                raise RuntimeError('Invalid default_sign: %r' % (default_sign,))

    def _check_timestamp_as_bool(self, filter_cls, filter_name, key, items):
        self.assertEqual(tuple(filter_cls('%s' % filter_name).apply(items, key='id')), (1, 2, 3, 4, 5))
        self.assertEqual(tuple(filter_cls('!%s' % filter_name).apply(items, key='id')), (6, 7, 8))

    def _check_timestamp_with_absolute_times(self, filter_cls, filter_name, key, items):
        self.assertEqual(tuple(filter_cls('%s=2000' % filter_name).apply(items, key='id')), ())
        self.assertEqual(tuple(filter_cls('%s=2001' % filter_name).apply(items, key='id')), (1,))
        self.assertEqual(tuple(filter_cls('%s=2002' % filter_name).apply(items, key='id')), (2,))
        self.assertEqual(tuple(filter_cls('%s=2003' % filter_name).apply(items, key='id')), (3,))
        self.assertEqual(tuple(filter_cls('%s=2004' % filter_name).apply(items, key='id')), ())

        self.assertEqual(tuple(filter_cls('%s<2001' % filter_name).apply(items, key='id')), (4, 5))
        self.assertEqual(tuple(filter_cls('%s<2002' % filter_name).apply(items, key='id')), (1, 4, 5))
        self.assertEqual(tuple(filter_cls('%s<2003' % filter_name).apply(items, key='id')), (1, 2, 4, 5))
        self.assertEqual(tuple(filter_cls('%s<2004' % filter_name).apply(items, key='id')), (1, 2, 3, 4, 5))

        self.assertEqual(tuple(filter_cls('%s<=2000' % filter_name).apply(items, key='id')), (4, 5))
        self.assertEqual(tuple(filter_cls('%s<=2001' % filter_name).apply(items, key='id')), (1, 4, 5))
        self.assertEqual(tuple(filter_cls('%s<=2002' % filter_name).apply(items, key='id')), (1, 2, 4, 5))
        self.assertEqual(tuple(filter_cls('%s<=2003' % filter_name).apply(items, key='id')), (1, 2, 3, 4, 5))

        self.assertEqual(tuple(filter_cls('%s>2000' % filter_name).apply(items, key='id')), (1, 2, 3, 6, 7, 8))
        self.assertEqual(tuple(filter_cls('%s>2001' % filter_name).apply(items, key='id')), (2, 3, 6, 7, 8))
        self.assertEqual(tuple(filter_cls('%s>2002' % filter_name).apply(items, key='id')), (3, 6, 7, 8))
        self.assertEqual(tuple(filter_cls('%s>2003' % filter_name).apply(items, key='id')), (6, 7, 8))

        self.assertEqual(tuple(filter_cls('%s>=2001' % filter_name).apply(items, key='id')), (1, 2, 3, 6, 7, 8))
        self.assertEqual(tuple(filter_cls('%s>=2002' % filter_name).apply(items, key='id')), (2, 3, 6, 7, 8))
        self.assertEqual(tuple(filter_cls('%s>=2003' % filter_name).apply(items, key='id')), (3, 6, 7, 8))
        self.assertEqual(tuple(filter_cls('%s>=2004' % filter_name).apply(items, key='id')), (6, 7, 8))

    def _check_timestamp_with_relative_times(self, filter_cls, filter_name, key, items):
        with mock_time(year=2000, month=1, day=1, hour=0, minute=0, second=0):
            self.assertEqual(tuple(filter_cls('%s=in 1y' % filter_name).apply(items, key='id')), (1,))
            self.assertEqual(tuple(filter_cls('%s>in 1y' % filter_name).apply(items, key='id')), (2, 3))
            self.assertEqual(tuple(filter_cls('%s>=in 1y' % filter_name).apply(items, key='id')), (1, 2, 3))
            self.assertEqual(tuple(filter_cls('%s<in 1y' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s<=in 1y' % filter_name).apply(items, key='id')), (1,))

            self.assertEqual(tuple(filter_cls('%s=1y ago' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s>1y ago' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s>=1y ago' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s<1y ago ' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s<=1y ago' % filter_name).apply(items, key='id')), ())

        with mock_time(year=2001, month=1, day=1, hour=0, minute=0, second=0):
            self.assertEqual(tuple(filter_cls('%s=in 1y' % filter_name).apply(items, key='id')), (2,))
            self.assertEqual(tuple(filter_cls('%s>in 1y' % filter_name).apply(items, key='id')), (3,))
            self.assertEqual(tuple(filter_cls('%s>=in 1y' % filter_name).apply(items, key='id')), (2, 3))
            self.assertEqual(tuple(filter_cls('%s<in 1y' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s<=in 1y' % filter_name).apply(items, key='id')), (2,))

            self.assertEqual(tuple(filter_cls('%s=1y ago' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s>1y ago' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s>=1y ago' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s<1y ago ' % filter_name).apply(items, key='id')), (1,))
            self.assertEqual(tuple(filter_cls('%s<=1y ago' % filter_name).apply(items, key='id')), (1,))

        with mock_time(year=2002, month=1, day=1, hour=0, minute=0, second=0):
            self.assertEqual(tuple(filter_cls('%s=in 1y' % filter_name).apply(items, key='id')), (3,))
            self.assertEqual(tuple(filter_cls('%s>in 1y' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s>=in 1y' % filter_name).apply(items, key='id')), (3,))
            self.assertEqual(tuple(filter_cls('%s<in 1y' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s<=in 1y' % filter_name).apply(items, key='id')), (3,))

            self.assertEqual(tuple(filter_cls('%s=1y ago' % filter_name).apply(items, key='id')), (1,))
            self.assertEqual(tuple(filter_cls('%s>1y ago' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s>=1y ago' % filter_name).apply(items, key='id')), (1,))
            self.assertEqual(tuple(filter_cls('%s<1y ago ' % filter_name).apply(items, key='id')), (2,))
            self.assertEqual(tuple(filter_cls('%s<=1y ago' % filter_name).apply(items, key='id')), (1, 2,))

        with mock_time(year=2003, month=1, day=1, hour=0, minute=0, second=0):
            self.assertEqual(tuple(filter_cls('%s=in 1y' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s>in 1y' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s>=in 1y' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s<in 1y' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s<=in 1y' % filter_name).apply(items, key='id')), ())

            self.assertEqual(tuple(filter_cls('%s=1y ago' % filter_name).apply(items, key='id')), (2,))
            self.assertEqual(tuple(filter_cls('%s>1y ago' % filter_name).apply(items, key='id')), (1,))
            self.assertEqual(tuple(filter_cls('%s>=1y ago' % filter_name).apply(items, key='id')), (1, 2))
            self.assertEqual(tuple(filter_cls('%s<1y ago ' % filter_name).apply(items, key='id')), (3,))
            self.assertEqual(tuple(filter_cls('%s<=1y ago' % filter_name).apply(items, key='id')), (2, 3))

    def _check_timestamp_with_positive_default_sign(self, filter_cls, filter_name, key, items):
        # '1y' should be the same as 'in 1y'
        with mock_time(year=2002, month=1, day=1, hour=0, minute=0, second=0):
            self.assertEqual(tuple(filter_cls('%s=1y' % filter_name).apply(items, key='id')), (3,))
            self.assertEqual(tuple(filter_cls('%s>1y' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s>=1y' % filter_name).apply(items, key='id')), (3,))
            self.assertEqual(tuple(filter_cls('%s<1y' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s<=1y' % filter_name).apply(items, key='id')), (3,))

    def _check_timestamp_with_negative_default_sign(self, filter_cls, filter_name, key, items):
        # '1y' should be the same as '1y ago'
        with mock_time(year=2002, month=1, day=1, hour=0, minute=0, second=0):
            self.assertEqual(tuple(filter_cls('%s=1y' % filter_name).apply(items, key='id')), (1,))
            self.assertEqual(tuple(filter_cls('%s>1y' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s>=1y' % filter_name).apply(items, key='id')), (1,))
            self.assertEqual(tuple(filter_cls('%s<1y' % filter_name).apply(items, key='id')), (2,))
            self.assertEqual(tuple(filter_cls('%s<=1y' % filter_name).apply(items, key='id')), (1, 2))

    def _check_timestamp_with_constants(self, filter_cls, filter_name, key, items):
        self.assertEqual(tuple(filter_cls('%s=now' % (filter_name,)).apply(items, key='id')), (4,))
        self.assertEqual(tuple(filter_cls('%s!=now' % (filter_name,)).apply(items, key='id')), (1, 2, 3, 5, 6, 7, 8))
        self.assertEqual(tuple(filter_cls('%s<now' % (filter_name,)).apply(items, key='id')), ())
        self.assertEqual(tuple(filter_cls('%s>now' % (filter_name,)).apply(items, key='id')), (1, 2, 3, 5, 6, 7, 8))
        self.assertEqual(tuple(filter_cls('%s<=now' % (filter_name,)).apply(items, key='id')), (4,))
        self.assertEqual(tuple(filter_cls('%s>=now' % (filter_name,)).apply(items, key='id')), (1, 2, 3, 4, 5, 6, 7, 8))

        self.assertEqual(tuple(filter_cls('%s=soon' % (filter_name,)).apply(items, key='id')), (5,))
        self.assertEqual(tuple(filter_cls('%s!=soon' % (filter_name,)).apply(items, key='id')), (1, 2, 3, 4, 6, 7, 8))
        self.assertEqual(tuple(filter_cls('%s<soon' % (filter_name,)).apply(items, key='id')), (4,))
        self.assertEqual(tuple(filter_cls('%s>soon' % (filter_name,)).apply(items, key='id')), (1, 2, 3, 6, 7, 8))
        self.assertEqual(tuple(filter_cls('%s<=soon' % (filter_name,)).apply(items, key='id')), (4, 5))
        self.assertEqual(tuple(filter_cls('%s>=soon' % (filter_name,)).apply(items, key='id')), (1, 2, 3, 5, 6, 7, 8))

        self.assertEqual(tuple(filter_cls('%s=unknown' % (filter_name,)).apply(items, key='id')), (6,))
        self.assertEqual(tuple(filter_cls('%s!=unknown' % (filter_name,)).apply(items, key='id')), (1, 2, 3, 4, 5, 7, 8))
        self.assertEqual(tuple(filter_cls('%s<unknown' % (filter_name,)).apply(items, key='id')), (1, 2, 3, 4, 5))
        self.assertEqual(tuple(filter_cls('%s>unknown' % (filter_name,)).apply(items, key='id')), (7, 8))
        self.assertEqual(tuple(filter_cls('%s<=unknown' % (filter_name,)).apply(items, key='id')), (1, 2, 3, 4, 5, 6))
        self.assertEqual(tuple(filter_cls('%s>=unknown' % (filter_name,)).apply(items, key='id')), (6, 7, 8))

        self.assertEqual(tuple(filter_cls('%s=na' % (filter_name,)).apply(items, key='id')), (7,))
        self.assertEqual(tuple(filter_cls('%s!=na' % (filter_name,)).apply(items, key='id')), (1, 2, 3, 4, 5, 6, 8))
        self.assertEqual(tuple(filter_cls('%s<na' % (filter_name,)).apply(items, key='id')), (1, 2, 3, 4, 5, 6))
        self.assertEqual(tuple(filter_cls('%s>na' % (filter_name,)).apply(items, key='id')), (8,))
        self.assertEqual(tuple(filter_cls('%s<=na' % (filter_name,)).apply(items, key='id')), (1, 2, 3, 4, 5, 6, 7))
        self.assertEqual(tuple(filter_cls('%s>=na' % (filter_name,)).apply(items, key='id')), (7, 8))

        self.assertEqual(tuple(filter_cls('%s=never' % (filter_name,)).apply(items, key='id')), (8,))
        self.assertEqual(tuple(filter_cls('%s!=never' % (filter_name,)).apply(items, key='id')), (1, 2, 3, 4, 5, 6, 7))
        self.assertEqual(tuple(filter_cls('%s<never' % (filter_name,)).apply(items, key='id')), (1, 2, 3, 4, 5, 6, 7))
        self.assertEqual(tuple(filter_cls('%s>never' % (filter_name,)).apply(items, key='id')), ())
        self.assertEqual(tuple(filter_cls('%s<=never' % (filter_name,)).apply(items, key='id')), (1, 2, 3, 4, 5, 6, 7, 8))
        self.assertEqual(tuple(filter_cls('%s>=never' % (filter_name,)).apply(items, key='id')), (8,))


    def check_timedelta_filter(self, filter_cls, filter_names, key, default_sign):
        from stig.client.ttypes import Timedelta
        items = ({'id': 1, key: Timedelta.from_string('1h ago')},
                 {'id': 2, key: Timedelta.from_string('0s')},
                 {'id': 3, key: Timedelta.from_string('in 1h')},
                 {'id': 4, key: Timedelta(Timedelta.UNKNOWN)},
                 {'id': 5, key: Timedelta(Timedelta.NOT_APPLICABLE)})

        for fn in filter_names:
            self._check_timedelta_as_bool(filter_cls, fn, key, items)
            self._check_timedelta_with_absolute_times(filter_cls, fn, key, items)
            self._check_timedelta_with_relative_times(filter_cls, fn, key, items)
            self._check_timedelta_with_constants(filter_cls, fn, key, items)
            if default_sign == 1:
                self._check_timedelta_with_positive_default_sign(filter_cls, fn, key, items)
            elif default_sign == -1:
                self._check_timedelta_with_negative_default_sign(filter_cls, fn, key, items)
            else:
                raise RuntimeError('Invalid default_sign: %r' % (default_sign,))

    def _check_timedelta_as_bool(self, filter_cls, filter_name, key, items):
        self.assertEqual(tuple(filter_cls('%s' % filter_name).apply(items, key='id')), (1, 2, 3))
        self.assertEqual(tuple(filter_cls('!%s' % filter_name).apply(items, key='id')), (4, 5))

    def _check_timedelta_with_absolute_times(self, filter_cls, filter_name, key, items):
        with mock_time(year=2001, month=1, day=1, hour=0, minute=0, second=0):
            self.assertEqual(tuple(filter_cls('%s=2000-12-31 22:59:59' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s=2000-12-31 23:00:00' % filter_name).apply(items, key='id')), (1,))
            self.assertEqual(tuple(filter_cls('%s=2001-01-01 23:00:01' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s=2000-12-31 23:59:59' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s=2001-01-01 00:00:00' % filter_name).apply(items, key='id')), (2,))
            self.assertEqual(tuple(filter_cls('%s=2001-01-01 00:00:01' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s=2001-01-01 00:59:59' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s=2001-01-01 01:00:00' % filter_name).apply(items, key='id')), (3,))
            self.assertEqual(tuple(filter_cls('%s=2001-01-01 01:00:01' % filter_name).apply(items, key='id')), ())

            self.assertEqual(tuple(filter_cls('%s<2000-12-31 23:00:00' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s<2000-12-31 23:00:01' % filter_name).apply(items, key='id')), (1,))
            self.assertEqual(tuple(filter_cls('%s<2001-01-01 00:00:00' % filter_name).apply(items, key='id')), (1,))
            self.assertEqual(tuple(filter_cls('%s<2001-01-01 00:00:01' % filter_name).apply(items, key='id')), (1, 2))
            self.assertEqual(tuple(filter_cls('%s<2001-01-01 01:00:00' % filter_name).apply(items, key='id')), (1, 2))
            self.assertEqual(tuple(filter_cls('%s<2001-01-01 01:00:01' % filter_name).apply(items, key='id')), (1, 2, 3))

            self.assertEqual(tuple(filter_cls('%s<=2000-12-31 22:59:59' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s<=2000-12-31 23:00:00' % filter_name).apply(items, key='id')), (1,))
            self.assertEqual(tuple(filter_cls('%s<=2000-12-31 23:00:01' % filter_name).apply(items, key='id')), (1,))
            self.assertEqual(tuple(filter_cls('%s<=2000-12-31 23:59:59' % filter_name).apply(items, key='id')), (1,))
            self.assertEqual(tuple(filter_cls('%s<=2001-01-01 00:00:00' % filter_name).apply(items, key='id')), (1, 2))
            self.assertEqual(tuple(filter_cls('%s<=2001-01-01 00:00:01' % filter_name).apply(items, key='id')), (1, 2,))
            self.assertEqual(tuple(filter_cls('%s<=2001-01-01 00:59:59' % filter_name).apply(items, key='id')), (1, 2,))
            self.assertEqual(tuple(filter_cls('%s<=2001-01-01 01:00:00' % filter_name).apply(items, key='id')), (1, 2, 3))
            self.assertEqual(tuple(filter_cls('%s<=2001-01-01 01:00:01' % filter_name).apply(items, key='id')), (1, 2, 3))

            self.assertEqual(tuple(filter_cls('%s>2000-12-31 22:59:59' % filter_name).apply(items, key='id')), (1, 2, 3))
            self.assertEqual(tuple(filter_cls('%s>2000-12-31 23:00:00' % filter_name).apply(items, key='id')), (2, 3))
            self.assertEqual(tuple(filter_cls('%s>2000-12-31 23:59:59' % filter_name).apply(items, key='id')), (2, 3))
            self.assertEqual(tuple(filter_cls('%s>2001-01-01 00:00:00' % filter_name).apply(items, key='id')), (3,))
            self.assertEqual(tuple(filter_cls('%s>2001-01-01 00:59:59' % filter_name).apply(items, key='id')), (3,))
            self.assertEqual(tuple(filter_cls('%s>2001-01-01 01:00:00' % filter_name).apply(items, key='id')), ())

            self.assertEqual(tuple(filter_cls('%s>=2000-12-31 22:59:59' % filter_name).apply(items, key='id')), (1, 2, 3))
            self.assertEqual(tuple(filter_cls('%s>=2000-12-31 23:00:00' % filter_name).apply(items, key='id')), (1, 2, 3))
            self.assertEqual(tuple(filter_cls('%s>=2000-12-31 23:00:01' % filter_name).apply(items, key='id')), (2, 3))
            self.assertEqual(tuple(filter_cls('%s>=2000-12-31 23:59:59' % filter_name).apply(items, key='id')), (2, 3))
            self.assertEqual(tuple(filter_cls('%s>=2001-01-01 00:00:00' % filter_name).apply(items, key='id')), (2, 3))
            self.assertEqual(tuple(filter_cls('%s>=2001-01-01 00:00:01' % filter_name).apply(items, key='id')), (3,))
            self.assertEqual(tuple(filter_cls('%s>=2001-01-01 00:59:59' % filter_name).apply(items, key='id')), (3,))
            self.assertEqual(tuple(filter_cls('%s>=2001-01-01 01:00:00' % filter_name).apply(items, key='id')), (3,))
            self.assertEqual(tuple(filter_cls('%s>=2001-01-01 01:00:01' % filter_name).apply(items, key='id')), ())

    def _check_timedelta_with_relative_times(self, filter_cls, filter_name, key, items):
        with mock_time(year=2001, month=1, day=1, hour=1, minute=0, second=0):
            self.assertEqual(tuple(filter_cls('%s=1h1s ago' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s=1h ago' % filter_name).apply(items, key='id')), (1,))
            self.assertEqual(tuple(filter_cls('%s=59m59s ago' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s=1s ago' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s=0s' % filter_name).apply(items, key='id')), (2,))
            self.assertEqual(tuple(filter_cls('%s=in 1s' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s=in 59m59s' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s=in 1h' % filter_name).apply(items, key='id')), (3,))
            self.assertEqual(tuple(filter_cls('%s=in 1h1s' % filter_name).apply(items, key='id')), ())

            self.assertEqual(tuple(filter_cls('%s<1h1s ago' % filter_name).apply(items, key='id')), (1, 2))
            self.assertEqual(tuple(filter_cls('%s<1h ago' % filter_name).apply(items, key='id')), (2,))
            self.assertEqual(tuple(filter_cls('%s<in 1h' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s<in 1h1s' % filter_name).apply(items, key='id')), (3,))

            self.assertEqual(tuple(filter_cls('%s<=1h ago' % filter_name).apply(items, key='id')), (1, 2))
            self.assertEqual(tuple(filter_cls('%s<=59m59s ago' % filter_name).apply(items, key='id')), (2,))
            self.assertEqual(tuple(filter_cls('%s<=in 59m59s' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s<=in 1h' % filter_name).apply(items, key='id')), (3,))

            self.assertEqual(tuple(filter_cls('%s>1h ago' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s>59m59s ago' % filter_name).apply(items, key='id')), (1,))
            self.assertEqual(tuple(filter_cls('%s>in 59m59s' % filter_name).apply(items, key='id')), (3,))
            self.assertEqual(tuple(filter_cls('%s>in 1h' % filter_name).apply(items, key='id')), ())

            self.assertEqual(tuple(filter_cls('%s>=1h1s ago' % filter_name).apply(items, key='id')), ())
            self.assertEqual(tuple(filter_cls('%s>=1h ago' % filter_name).apply(items, key='id')), (1,))
            self.assertEqual(tuple(filter_cls('%s>=in 1h' % filter_name).apply(items, key='id')), (3,))
            self.assertEqual(tuple(filter_cls('%s>=in 1h1s' % filter_name).apply(items, key='id')), ())

    def _check_timedelta_with_positive_default_sign(self, filter_cls, filter_name, key, items):
        # '1h' should be the same as 'in 1h'
        self.assertEqual(tuple(filter_cls('%s=1h' % filter_name).apply(items, key='id')), (3,))
        self.assertEqual(tuple(filter_cls('%s>1h' % filter_name).apply(items, key='id')), ())
        self.assertEqual(tuple(filter_cls('%s>=1h' % filter_name).apply(items, key='id')), (3,))
        self.assertEqual(tuple(filter_cls('%s<1h' % filter_name).apply(items, key='id')), ())
        self.assertEqual(tuple(filter_cls('%s<=1h' % filter_name).apply(items, key='id')), (3,))

    # No filter currently has a negative default sign
    def _check_timedelta_with_negative_default_sign(self, filter_cls, filter_name, key, items):
        # '1h' should be the same as '1h ago'
        raise NotImplementedError('Please implement _check_timedelta_with_negative_default_sign()')

    def _check_timedelta_with_constants(self, filter_cls, filter_name, key, items):
        self.assertEqual(tuple(filter_cls('%s=unknown' % filter_name).apply(items, key='id')), (4,))
        self.assertEqual(tuple(filter_cls('%s!=unknown' % filter_name).apply(items, key='id')), (1, 2, 3, 5))
        self.assertEqual(tuple(filter_cls('%s<unknown' % filter_name).apply(items, key='id')), (1, 2, 3))
        self.assertEqual(tuple(filter_cls('%s>unknown' % filter_name).apply(items, key='id')), ())
        self.assertEqual(tuple(filter_cls('%s<=unknown' % filter_name).apply(items, key='id')), (1, 2, 3))
        self.assertEqual(tuple(filter_cls('%s>=unknown' % filter_name).apply(items, key='id')), ())

        self.assertEqual(tuple(filter_cls('%s=na' % filter_name).apply(items, key='id')), (5,))
        self.assertEqual(tuple(filter_cls('%s!=na' % filter_name).apply(items, key='id')), (1, 2, 3, 4))
        self.assertEqual(tuple(filter_cls('%s<na' % filter_name).apply(items, key='id')), (1, 2, 3))
        self.assertEqual(tuple(filter_cls('%s>na' % filter_name).apply(items, key='id')), ())
        self.assertEqual(tuple(filter_cls('%s<=na' % filter_name).apply(items, key='id')), (1, 2, 3))
        self.assertEqual(tuple(filter_cls('%s>=na' % filter_name).apply(items, key='id')), ())
