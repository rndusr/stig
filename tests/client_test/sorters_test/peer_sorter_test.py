from unittest.mock import patch

from sorter_helpers import TestSorterBase
from stig.client.sorters import PeerSorter


class TestPeerSorter(TestSorterBase):
    sorter_cls = PeerSorter

    def test_default_sorter(self):
        self.assertEqual(PeerSorter.DEFAULT_SORT, 'torrent')

    def test_torrent(self):
        items = [{'id': 1, 'tname': 'foo'},
                 {'id': 2, 'tname': 'bar'},
                 {'id': 3, 'tname': 'baz'}]
        self.assert_sorted_ids('torrent', items, (2, 3, 1))

    def test_percent_downloaded(self):
        items = [{'id': 1, 'tname': 'foo', '%downloaded': 8},
                 {'id': 2, 'tname': 'bar', '%downloaded': 21},
                 {'id': 3, 'tname': 'baz', '%downloaded': 0}]
        self.assert_sorted_ids('%downloaded', items, (3, 1, 2))

    def test_rate_up(self):
        items = [{'id': 1, 'tname': 'foo', 'rate-up': 2000},
                 {'id': 2, 'tname': 'bar', 'rate-up': 4000},
                 {'id': 3, 'tname': 'baz', 'rate-up': 3000}]
        self.assert_sorted_ids('rate-up', items, (1, 3, 2))

    def test_rate_down(self):
        items = [{'id': 1, 'tname': 'foo', 'rate-down': 2000},
                 {'id': 2, 'tname': 'bar', 'rate-down': 4000},
                 {'id': 3, 'tname': 'baz', 'rate-down': 3000}]
        self.assert_sorted_ids('rate-down', items, (1, 3, 2))

    def test_rate_est(self):
        items = [{'id': 1, 'tname': 'foo', 'rate-est': 2000},
                 {'id': 2, 'tname': 'bar', 'rate-est': 4000},
                 {'id': 3, 'tname': 'baz', 'rate-est': 3000}]
        self.assert_sorted_ids('rate-est', items, (1, 3, 2))

    def test_rate(self):
        items = [{'id': 1, 'tname': 'foo', 'rate-up': 2000, 'rate-down': 5000},
                 {'id': 2, 'tname': 'bar', 'rate-up': 4000, 'rate-down': 0},
                 {'id': 3, 'tname': 'baz', 'rate-up': 3000, 'rate-down': 7000}]
        self.assert_sorted_ids('rate', items, (2, 1, 3))

    def test_eta(self):
        items = [{'id': 1, 'tname': 'foo', 'eta': 1000},
                 {'id': 2, 'tname': 'bar', 'eta': 2000},
                 {'id': 3, 'tname': 'baz', 'eta': 500}]
        self.assert_sorted_ids('eta', items, (3, 1, 2))

    def test_client(self):
        items = [{'id': 1, 'tname': 'foo', 'client': 'Transmission'},
                 {'id': 2, 'tname': 'bar', 'client': 'Deluge'},
                 {'id': 3, 'tname': 'baz', 'client': 'rtorrent'}]
        self.assert_sorted_ids('client', items, (2, 3, 1))

    @patch('stig.client.rdns.gethostbyaddr_from_cache')
    def test_host(self, mock_gethostbyaddr_from_cache):
        items = [{'id': 1, 'tname': 'foo', 'ip': '1.2.3.2'},
                 {'id': 2, 'tname': 'bar', 'ip': '3.4.5.1'},
                 {'id': 3, 'tname': 'baz', 'ip': '2.3.4.3'}]
        def mock_rdns(addr):
            return ''.join(reversed(addr))
        mock_gethostbyaddr_from_cache.side_effect = mock_rdns
        self.assert_sorted_ids('host', items, (2, 1, 3))

    def test_port(self):
        items = [{'id': 1, 'tname': 'foo', 'port': 6889},
                 {'id': 2, 'tname': 'bar', 'port': 6887},
                 {'id': 3, 'tname': 'baz', 'port': 6890}]
        self.assert_sorted_ids('port', items, (2, 1, 3))
