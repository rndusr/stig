from stig.client.filters.setting import _SingleFilter as SettingFilter

import unittest
from filter_helpers import HelpersMixin


class TestSettingFilter(unittest.TestCase, HelpersMixin):
    def test_default_filter(self):
        self.assertEqual(SettingFilter.DEFAULT_FILTER, 'name')

    def test_getting_spec_by_alias(self):
        self.check_getting_spec_by_alias(SettingFilter)

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

    def test_value_filter_with_strings(self):
        from stig.utils.usertypes import Bool, String, Float
        self.check_filter(filter_cls=SettingFilter,
                          filter_names=('value', 'v'),
                          items=({'id': 'a', 'value': 'asdfoo', 'validate': String},
                                 {'id': 'b', 'value': True, 'validate': Bool},
                                 {'id': 'c', 'value': ''},
                                 {'id': 'd', 'value': 0.5, 'validate': Float},
                                 {'id': 'e', 'value': ('foo', 'bar')}),
                          test_cases=(
                              ('{name}', ('a', 'b', 'd', 'e')),
                              ('!{name}', ('c',)),
                              ('{name}=asdfoo', ('a',)),
                              ('{name}!=asdfoo', ('b', 'c', 'd', 'e')),
                              ('{name}!=xxx', ('a', 'b', 'c', 'd', 'e')),
                              ('{name}~sd', ('a',)),
                              ('{name}~foo', ('a', 'e')),
                              ('{name}!~sd', ('b', 'c', 'd', 'e')),
                              ('{name}!~foo', ('b', 'c', 'd'))))

    def test_default_filter_with_strings(self):
        from stig.utils.usertypes import Bool, String, Float
        self.check_filter(filter_cls=SettingFilter,
                          filter_names=('default', 'def'),
                          items=({'id': 'a', 'default': 'asdfoo', 'validate': String},
                                 {'id': 'b', 'default': True, 'validate': Bool},
                                 {'id': 'c', 'default': ''},
                                 {'id': 'd', 'default': 0.5, 'validate': Float},
                                 {'id': 'e', 'default': ('foo', 'bar')}),
                          test_cases=(
                              ('{name}', ('a', 'b', 'd', 'e')),
                              ('!{name}', ('c',)),
                              ('{name}=asdfoo', ('a',)),
                              ('{name}!=asdfoo', ('b', 'c', 'd', 'e')),
                              ('{name}!=xxx', ('a', 'b', 'c', 'd', 'e')),
                              ('{name}~sd', ('a',)),
                              ('{name}~foo', ('a', 'e')),
                              ('{name}!~sd', ('b', 'c', 'd', 'e')),
                              ('{name}!~foo', ('b', 'c', 'd'))))

    def test_value_filter_with_numbers(self):
        from stig.utils.usertypes import Bool, Int, Float
        self.check_filter(filter_cls=SettingFilter,
                          filter_names=('value', 'v'),
                          items=({'id': 'a', 'value': 17, 'validate': Int},
                                 {'id': 'b', 'value': True, 'validate': Bool},
                                 {'id': 'c', 'value': ''},
                                 {'id': 'd', 'value': 0.5, 'validate': Float},
                                 {'id': 'e', 'value': ('foo', 'bar')}),
                          test_cases=(
                              ('{name}', ('a', 'b', 'd', 'e')),
                              ('!{name}', ('c',)),
                              ('{name}=17', ('a',)),
                              ('{name}!=17', ('b', 'c', 'd', 'e')),
                              ('{name}!=16', ('a', 'b', 'c', 'd', 'e')),
                              ('{name}=0', ()),
                              ('{name}=0.5', ('d',)),
                              ('{name}=0.6', ()),
                              ('{name}<0.6', ('c', 'd')),
                              ('{name}>0.6', ('a',)),
                              ('{name}>=0.5', ('a', 'd')),
                              ('{name}<=0.5', ('c', 'd')),
                              ('{name}<0.5', ('c',)),
                              ('{name}<0.5', ('c',)),
                              ('{name}~7', ()),
                              ('{name}!~foo', ('a', 'b', 'c', 'd'))))

    def test_default_filter_with_numbers(self):
        from stig.utils.usertypes import Bool, Int, Float
        self.check_filter(filter_cls=SettingFilter,
                          filter_names=('default', 'def'),
                          items=({'id': 'a', 'default': 17, 'validate': Int},
                                 {'id': 'b', 'default': True, 'validate': Bool},
                                 {'id': 'c', 'default': ''},
                                 {'id': 'd', 'default': 0.5, 'validate': Float},
                                 {'id': 'e', 'default': ('foo', 'bar')}),
                          test_cases=(
                              ('{name}', ('a', 'b', 'd', 'e')),
                              ('!{name}', ('c',)),
                              ('{name}=17', ('a',)),
                              ('{name}!=17', ('b', 'c', 'd', 'e')),
                              ('{name}!=16', ('a', 'b', 'c', 'd', 'e')),
                              ('{name}=0', ()),
                              ('{name}=0.5', ('d',)),
                              ('{name}=0.6', ()),
                              ('{name}<0.6', ('c', 'd')),
                              ('{name}>0.6', ('a',)),
                              ('{name}>=0.5', ('a', 'd')),
                              ('{name}<=0.5', ('c', 'd')),
                              ('{name}<0.5', ('c',)),
                              ('{name}<0.5', ('c',)),
                              ('{name}~7', ()),
                              ('{name}!~foo', ('a', 'b', 'c', 'd'))))

    def test_value_filter_with_iterables(self):
        from stig.utils.usertypes import Tuple, Bool
        self.check_filter(filter_cls=SettingFilter,
                          filter_names=('value', 'v'),
                          items=({'id': 'a',
                                  'value': Tuple('x', 'y', options=('x', 'y', 'z')),
                                  'validate': Tuple.partial(options=('x', 'y', 'z'))},
                                 {'id': 'b', 'value': True, 'validate': Bool},
                                 {'id': 'c', 'value': 'foo'},
                                 {'id': 'd', 'value': 0, 'validate': int},
                                 {'id': 'e',
                                  'value': Tuple('x', 'z', options=('x', 'y', 'z')),
                                  'validate': Tuple.partial(options=('x', 'y', 'z'))}),
                          test_cases=(('{name}', ('a', 'b', 'c', 'e')),
                                      ('!{name}', ('d',)),
                                      ('{name}=x,y', ('a',)),
                                      ('{name}!=x,y', ('b', 'c', 'd', 'e')),
                                      ('{name}=x', ()),
                                      ('{name}~x', ('a', 'e')),
                                      ('{name}~y', ('a',)),
                                      ('{name}~z', ('e',)),
                                      ('{name}!~z', ('a', 'b', 'c', 'd')),
                                      ('{name}~x,y', ('a',)),
                                      ('{name}~y,x', ('a',)),
                                      ('{name}!~y,x', ('b', 'c', 'd', 'e'))))

    def test_default_filter_with_iterables(self):
        from stig.utils.usertypes import Tuple, Bool
        self.check_filter(filter_cls=SettingFilter,
                          filter_names=('default', 'def'),
                          items=({'id': 'a',
                                  'default': Tuple('x', 'y', options=('x', 'y', 'z')),
                                  'validate': Tuple.partial(options=('x', 'y', 'z'))},
                                 {'id': 'b', 'default': True, 'validate': Bool},
                                 {'id': 'c', 'default': 'foo'},
                                 {'id': 'd', 'default': 0, 'validate': int},
                                 {'id': 'e',
                                  'default': Tuple('x', 'z', options=('x', 'y', 'z')),
                                  'validate': Tuple.partial(options=('x', 'y', 'z'))}),
                          test_cases=(('{name}', ('a', 'b', 'c', 'e')),
                                      ('!{name}', ('d',)),
                                      ('{name}=x,y', ('a',)),
                                      ('{name}!=x,y', ('b', 'c', 'd', 'e')),
                                      ('{name}=x', ()),
                                      ('{name}~x', ('a', 'e')),
                                      ('{name}~y', ('a',)),
                                      ('{name}~z', ('e',)),
                                      ('{name}!~z', ('a', 'b', 'c', 'd')),
                                      ('{name}~x,y', ('a',)),
                                      ('{name}~y,x', ('a',)),
                                      ('{name}!~y,x', ('b', 'c', 'd', 'e'))))

    def test_description(self):
        self.check_str_filter(SettingFilter,
                              filter_names=('description', 'desc'),
                              key='description')
