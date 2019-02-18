from stig.client.filters.peer import _SingleFilter as PeerFilter

import unittest
from helpers import HelpersMixin


class TestPeerFilter(unittest.TestCase, HelpersMixin):
    def test_default_filter(self):
        self.assertEqual(PeerFilter.DEFAULT_FILTER, 'host')

    def test_all(self):
        self.check_bool_filter(PeerFilter,
                               filter_names=('all', '*'),
                               items=({'id': 1}, {'id': 2}, {'id': 3}),
                               test_cases=(('{name}', (1, 2, 3)),
                                           ('!{name}', ())))

    def test_uploading(self):
        self.check_bool_filter(PeerFilter,
                               filter_names=('uploading', 'upg'),
                               items=({'id': 1, 'rate-up': 1000},
                                      {'id': 2, 'rate-up': 2000},
                                      {'id': 3, 'rate-up': 0}),
                               test_cases=(('{name}', (1, 2)),
                                           ('!{name}', (3,))))

    def test_downloading(self):
        self.check_bool_filter(PeerFilter,
                               filter_names=('downloading', 'dng'),
                               items=({'id': 1, 'rate-down': 1000},
                                      {'id': 2, 'rate-down': 2000},
                                      {'id': 3, 'rate-down': 0}),
                               test_cases=(('{name}', (1, 2)),
                                           ('!{name}', (3,))))

    def test_seeding(self):
        self.check_bool_filter(PeerFilter,
                               filter_names=('seeding', 'sdg'),
                               items=({'id': 1, '%downloaded': 0},
                                      {'id': 2, '%downloaded': 99.9},
                                      {'id': 3, '%downloaded': 100}),
                               test_cases=(('{name}', (3,)),
                                           ('!{name}', (1, 2))))

    def test_downloaded(self):
        self.check_filter(PeerFilter,
                          filter_names=('downloaded', 'dn'),
                          items=({'id': 1, 'tsize': 5000, '%downloaded': 0},
                                 {'id': 2, 'tsize': 2000, '%downloaded': 50},
                                 {'id': 3, 'tsize': 4000, '%downloaded': 75},
                                 {'id': 4, 'tsize': 3000, '%downloaded': 100}),
                          test_cases=(('{name}', (4,)),
                                      ('!{name}', (1, 2, 3)),
                                      ('{name}=1000', (2,)),
                                      ('{name}!=1000', (1, 3, 4)),
                                      ('{name}<1000', (1,)),
                                      ('{name}<=1000', (1, 2)),
                                      ('{name}>1000', (3, 4)),
                                      ('{name}>=1000', (2, 3, 4))))

    def test_percent_downloaded(self):
        self.check_int_filter(PeerFilter,
                              filter_names=('%downloaded', '%dn'),
                              key='%downloaded')

    def test_client(self):
        self.check_str_filter(PeerFilter,
                              filter_names=('client', 'cl'),
                              key='client')

    def test_country(self):
        self.check_str_filter(PeerFilter,
                              filter_names=('country', 'cn'),
                              key='country')

    def test_host(self):
        self.check_str_filter(PeerFilter,
                              filter_names=('country', 'cn'),
                              key='country')

    def test_port(self):
        self.check_int_filter(PeerFilter,
                              filter_names=('port',),
                              key='port')
