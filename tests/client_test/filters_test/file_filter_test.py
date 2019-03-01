from stig.client.filters.file import _SingleFilter as FileFilter

import unittest
from filter_helpers import HelpersMixin


class TestFileFilter(unittest.TestCase, HelpersMixin):
    def test_default_filter(self):
        self.assertEqual(FileFilter.DEFAULT_FILTER, 'name')

    def test_all(self):
        self.check_bool_filter(FileFilter,
                               filter_names=('all', '*'),
                               items=({'id': 1}, {'id': 2}, {'id': 3}),
                               test_cases=(('{name}', (1, 2, 3)),
                                           ('!{name}', ())))

    def test_wanted(self):
        self.check_bool_filter(FileFilter,
                               filter_names=('wanted',),
                               items=({'id': 1, 'is-wanted': True},
                                      {'id': 2, 'is-wanted': False},
                                      {'id': 3, 'is-wanted': True}),
                               test_cases=(('{name}', (1, 3)),
                                           ('!{name}', (2,))))

    def test_complete(self):
        self.check_bool_filter(FileFilter,
                               filter_names=('complete', 'cmp'),
                               items=({'id': 1, '%downloaded': 0},
                                      {'id': 2, '%downloaded': 99},
                                      {'id': 3, '%downloaded': 100}),
                               test_cases=(('{name}', (3,)),
                                           ('!{name}', (1, 2))))

    def test_name(self):
        self.check_str_filter(FileFilter,
                              filter_names=('name', 'n'),
                              key='name')

    def test_path(self):
        self.check_str_filter(FileFilter,
                          filter_names=('path', 'dir'),
                              key='path-absolute')

    def test_size(self):
        self.check_int_filter(FileFilter,
                              filter_names=('size', 'sz'),
                              key='size-total')

    def test_downloaded(self):
        self.check_filter(FileFilter,
                          filter_names=('downloaded', 'dn'),
                          items=({'id': 1, 'size-downloaded': 0, '%downloaded': 0},
                                 {'id': 2, 'size-downloaded': 100, '%downloaded': 42},
                                 {'id': 3, 'size-downloaded': 3000, '%downloaded': 100}),
                          test_cases=(('{name}', (3,)),
                                      ('!{name}', (1, 2)),
                                      ('{name}=100', (2,)),
                                      ('{name}<100', (1,)),
                                      ('{name}<=100', (1, 2)),
                                      ('{name}>100', (3,)),
                                      ('{name}>=100', (2, 3))))

    def test_percent_downloaded(self):
        self.check_filter(FileFilter,
                          filter_names=('%downloaded', '%dn'),
                          items=({'id': 1, '%downloaded': 0},
                                 {'id': 2, '%downloaded': 50},
                                 {'id': 3, '%downloaded': 100}),
                          test_cases=(('{name}', (3,)),
                                      ('!{name}', (1, 2)),
                                      ('{name}=100', (3,)),
                                      ('{name}<100', (1, 2)),
                                      ('{name}<=100', (1, 2, 3)),
                                      ('{name}>100', ()),
                                      ('{name}>=100', (3,))))

    def test_priority(self):
        from stig.client.ttypes import TorrentFilePriority
        self.check_filter(FileFilter,
                          filter_names=('priority', 'prio'),
                          items=({'id': 1, 'priority': TorrentFilePriority(-2)},  # off
                                 {'id': 2, 'priority': TorrentFilePriority(-1)},  # low
                                 {'id': 3, 'priority': TorrentFilePriority(0)},   # normal
                                 {'id': 4, 'priority': TorrentFilePriority(1)}),  # high
                          test_cases=(('{name}', (1, 2, 4)),
                                      ('!{name}', (3,)),
                                      ('{name}=low', (2,)),
                                      ('{name}<low', (1,)),
                                      ('{name}<=low', (1, 2)),
                                      ('{name}>low', (3, 4)),
                                      ('{name}>=low', (2, 3, 4))))
