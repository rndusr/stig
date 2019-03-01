from stig.client.filters.setting import _SingleFilter as SettingFilter

import unittest
from filter_helpers import HelpersMixin


class TestSettingFilter(unittest.TestCase, HelpersMixin):
    def test_default_filter(self):
        self.assertEqual(SettingFilter.DEFAULT_FILTER, 'name')

    def test_all(self):
        self.check_bool_filter(SettingFilter,
                               filter_names=('all', '*'),
                               items=({'id': 'foo'}, {'id': 'bar'}, {'id': 'baz'}),
                               test_cases=(('{name}', ('foo', 'bar', 'baz')),
                                           ('!{name}', ())))

    def test_changed(self):
        self.check_bool_filter(SettingFilter,
                               filter_names=('changed', 'ch'),
                               items=({'id': 'foo', 'default': 1000, 'value': 100},
                                      {'id': 'bar', 'default': 'hello', 'value': 'goodbye'},
                                      {'id': 'baz', 'default': (1, 2, 3), 'value': (1, 2, 3)}),
                               test_cases=(('{name}', ('foo', 'bar')),
                                           ('!{name}', ('baz',))))

    def test_name(self):
        self.check_filter(filter_cls=SettingFilter,
                          filter_names=('name', 'n'),
                          items=({'id': 'foo'},
                                 {'id': 'bar'},
                                 {'id': 'baz'}),
                          test_cases=(('{name}', ('foo', 'bar', 'baz')),
                                      ('!{name}', ()),
                                      ('{name}=foo', ('foo',)),
                                      ('{name}!=foo', ('bar', 'baz')),
                                      ('{name}~ba', ('bar', 'baz')),
                                      ('{name}!~ba', ('foo',))))

    def test_value(self):
        self.check_str_filter(SettingFilter,
                              filter_names=('value', 'v'),
                              key='value')

    def test_default(self):
        self.check_str_filter(SettingFilter,
                              filter_names=('default', 'def'),
                              key='default')

    def test_description(self):
        self.check_str_filter(SettingFilter,
                              filter_names=('description', 'desc'),
                              key='description')
