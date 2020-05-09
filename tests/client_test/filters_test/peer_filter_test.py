from stig.client.filters.peer import _SingleFilter as PeerFilter

import unittest
from filter_helpers import HelpersMixin


class TestPeerFilter(unittest.TestCase, HelpersMixin):
    def test_needed_keys(self):
        self.assertEqual(PeerFilter('foo').needed_keys, ('peers',))

    def test_default_filter(self):
        self.assertEqual(PeerFilter.DEFAULT_FILTER, 'host')

    def test_getting_spec_by_alias(self):
        self.check_getting_spec_by_alias(PeerFilter)

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
                          items=({'id': 1, 'downloaded': 0},
                                 {'id': 2, 'downloaded': 1000},
                                 {'id': 3, 'downloaded': 10000},
                                 {'id': 4, 'downloaded': 15999}),
                          test_cases=(('{name}', (2, 3, 4)),
                                      ('!{name}', (1,)),
                                      ('{name}=1000', (2,)),
                                      ('{name}!=1k', (1, 3, 4)),
                                      ('{name}<1000', (1,)),
                                      ('{name}<=1k', (1, 2)),
                                      ('{name}>1k', (3, 4)),
                                      ('{name}>=1000', (2, 3, 4))))

    def test_percent_downloaded(self):
        self.check_int_filter(PeerFilter,
                              filter_names=('%downloaded', '%dn'),
                              key='%downloaded')

    def test_client(self):
        self.check_str_filter(PeerFilter,
                              filter_names=('client', 'cl'),
                              key='client')

    @unittest.mock.patch('stig.client.rdns.gethostbyaddr_from_cache')
    def test_host(self, mock_gethost):
        mock_gethost.side_effect = lambda ip: 'hostname of %s' % (ip,) if ip[0] == '1' else ip
        self.check_filter(PeerFilter,
                          filter_names=('host',),
                          items=({'id': 1, 'ip': '123.4.5.6'},
                                 {'id': 2, 'ip': '123.6.5.4'},
                                 {'id': 3, 'ip': '23.4.5.6'},
                                 {'id': 4, 'ip': '3.4.5.6'}),
                          test_cases=(('{name}', (1, 2, 3, 4)),
                                      ('!{name}', ()),
                                      ('{name}=hostname of 123.6.5.4', (2,)),
                                      ('{name}!=hostname of 123.6.5.4', (1, 3, 4)),
                                      ('{name}~123', (1, 2)),
                                      ('{name}!~123', (3, 4))))

    def test_port(self):
        self.check_int_filter(PeerFilter,
                              filter_names=('port',),
                              key='port')
