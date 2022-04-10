import random
from types import SimpleNamespace

from sorter_helpers import TestSorterBase

from stig.client.sorters import TorrentSorter


class MockTracker(dict):
    def __init__(self, domain):
        self['url-announce'] = SimpleNamespace(domain=domain)


class LoggingDict(dict):
    def __new__(cls, *args, **kwargs):
        obj = super().__new__(cls, *args, **kwargs)
        obj.used_keys = set()
        return obj

    def __getitem__(self, key):
        getattr(self, 'used_keys', set()).add(key)
        return super().__getitem__(key)


class TestTorrentSorter(TestSorterBase):
    sorter_cls = TorrentSorter

    def assert_sorted_ids(self, sorter_name, items, exp_ids):
        random.shuffle(items)
        items = [LoggingDict(item) for item in items]
        sorter_names = (sorter_name,) + tuple(self.sorter_cls.SORTSPECS[sorter_name].aliases)
        for sort_str in sorter_names:
            sorter = self.sorter_cls((sort_str,))
            self.assertEqual(tuple(item['id'] for item in sorter.apply(items)), exp_ids)

            # Make sure all requested keys are given as needed_keys.  'id' is
            # always present and may or may not be given in needed_keys without
            # consequences.
            needed_keys = set(sorter.needed_keys)
            needed_keys.discard('id')
            for item in items:
                item.used_keys.discard('id')
                self.assertEqual(needed_keys, item.used_keys)

    def test_default_sorter(self):
        self.assertEqual(TorrentSorter.DEFAULT_SORT, 'name')

    def test_id(self):
        items = [{'id': 1, 'name': 'foo'},
                 {'id': 2, 'name': 'bar'},
                 {'id': 3, 'name': 'baz'}]
        self.assert_sorted_ids('id', items, (1, 2, 3))

    def test_name(self):
        items = [{'id': 1, 'name': 'foo'},
                 {'id': 2, 'name': 'bar'},
                 {'id': 3, 'name': 'baz'}]
        self.assert_sorted_ids('name', items, (2, 3, 1))

    def test_path(self):
        items = [{'id': 1, 'name': 'foo', 'path': '/foo/bar'},
                 {'id': 2, 'name': 'bar', 'path': '/foo/baz'},
                 {'id': 3, 'name': 'baz', 'path': '/bar'}]
        self.assert_sorted_ids('path', items, (3, 1, 2))

    def test_status(self):
        items = [{'id': 1, 'name': 'foo', 'status': 'a'},
                 {'id': 2, 'name': 'bar', 'status': 'c'},
                 {'id': 3, 'name': 'baz', 'status': 'b'}]
        self.assert_sorted_ids('status', items, (1, 3, 2))

    def test_error(self):
        items = [{'id': 1, 'name': 'foo', 'error': 'no'},
                 {'id': 2, 'name': 'bar', 'error': 'nah'},
                 {'id': 3, 'name': 'baz', 'error': 'nope'}]
        self.assert_sorted_ids('error', items, (2, 1, 3))

    def test_uploaded(self):
        items = [{'id': 1, 'name': 'foo', 'size-uploaded': 100},
                 {'id': 2, 'name': 'bar', 'size-uploaded': 200},
                 {'id': 3, 'name': 'baz', 'size-uploaded': 0}]
        self.assert_sorted_ids('uploaded', items, (3, 1, 2))

    def test_downloaded(self):
        items = [{'id': 1, 'name': 'foo', 'size-downloaded': 50},
                 {'id': 2, 'name': 'bar', 'size-downloaded': 60},
                 {'id': 3, 'name': 'baz', 'size-downloaded': 70}]
        self.assert_sorted_ids('downloaded', items, (1, 2, 3))

    def test_percent_downloaded(self):
        items = [{'id': 1, 'name': 'foo', '%downloaded':   0, '%verified':   0, '%metadata': 100},
                 {'id': 2, 'name': 'bar', '%downloaded': 100, '%verified':  30, '%metadata': 100},
                 {'id': 3, 'name': 'baz', '%downloaded':   0, '%verified':   0, '%metadata':  50}]
        self.assert_sorted_ids('%downloaded', items, (3, 1, 2))

    def test_size(self):
        items = [{'id': 1, 'name': 'foo', 'size-final': 500},
                 {'id': 2, 'name': 'bar', 'size-final': 6000},
                 {'id': 3, 'name': 'baz', 'size-final': 70}]
        self.assert_sorted_ids('size', items, (3, 1, 2))

    def test_peers(self):
        items = [{'id': 1, 'name': 'foo', 'peers-connected': 0},
                 {'id': 2, 'name': 'bar', 'peers-connected': 24},
                 {'id': 3, 'name': 'baz', 'peers-connected': 1}]
        self.assert_sorted_ids('peers', items, (1, 3, 2))

    def test_seeds(self):
        items = [{'id': 1, 'name': 'foo', 'peers-seeding': 20},
                 {'id': 2, 'name': 'bar', 'peers-seeding': 4},
                 {'id': 3, 'name': 'baz', 'peers-seeding': 0}]
        self.assert_sorted_ids('seeds', items, (3, 2, 1))

    def test_ratio(self):
        items = [{'id': 1, 'name': 'foo', 'ratio': 2},
                 {'id': 2, 'name': 'bar', 'ratio': 0},
                 {'id': 3, 'name': 'baz', 'ratio': 0.1}]
        self.assert_sorted_ids('ratio', items, (2, 3, 1))

    def test_rate_up(self):
        items = [{'id': 1, 'name': 'foo', 'rate-up': 500},
                 {'id': 2, 'name': 'bar', 'rate-up': 400},
                 {'id': 3, 'name': 'baz', 'rate-up': 0}]
        self.assert_sorted_ids('rate-up', items, (3, 2, 1))

    def test_rate_down(self):
        items = [{'id': 1, 'name': 'foo', 'rate-down': 3},
                 {'id': 2, 'name': 'bar', 'rate-down': 2},
                 {'id': 3, 'name': 'baz', 'rate-down': 5}]
        self.assert_sorted_ids('rate-down', items, (2, 1, 3))

    def test_rate(self):
        items = [{'id': 1, 'name': 'foo', 'rate-down': 3, 'rate-up': 7},
                 {'id': 2, 'name': 'bar', 'rate-down': 2, 'rate-up': 20},
                 {'id': 3, 'name': 'baz', 'rate-down': 21, 'rate-up': 0}]
        self.assert_sorted_ids('rate', items, (1, 3, 2))

    def test_limit_rate_up(self):
        items = [{'id': 1, 'name': 'foo', 'limit-rate-up': 0},
                 {'id': 2, 'name': 'bar', 'limit-rate-up': 20},
                 {'id': 3, 'name': 'baz', 'limit-rate-up': 15}]
        self.assert_sorted_ids('limit-rate-up', items, (1, 3, 2))

    def test_limit_rate_down(self):
        items = [{'id': 1, 'name': 'foo', 'limit-rate-down': 0},
                 {'id': 2, 'name': 'bar', 'limit-rate-down': 20},
                 {'id': 3, 'name': 'baz', 'limit-rate-down': 15}]
        self.assert_sorted_ids('limit-rate-down', items, (1, 3, 2))

    def test_limit_rate(self):
        items = [{'id': 1, 'name': 'foo', 'limit-rate-down': 0, 'limit-rate-up': 50},
                 {'id': 2, 'name': 'bar', 'limit-rate-down': 20, 'limit-rate-up': 10},
                 {'id': 3, 'name': 'baz', 'limit-rate-down': 15, 'limit-rate-up': 20}]
        self.assert_sorted_ids('limit-rate', items, (2, 3, 1))

    def test_tracker(self):
        items = [{'id': 1, 'name': 'foo', 'trackers': [MockTracker('foo.example.org')]},
                 {'id': 2, 'name': 'bar', 'trackers': [MockTracker('bar.example.org')]},
                 {'id': 3, 'name': 'baz', 'trackers': [MockTracker('baz.example.org')]}]
        self.assert_sorted_ids('tracker', items, (2, 3, 1))

    def test_eta(self):
        items = [{'id': 1, 'name': 'foo', 'timespan-eta': 500},
                 {'id': 2, 'name': 'bar', 'timespan-eta': 20},
                 {'id': 3, 'name': 'baz', 'timespan-eta': 1e5}]
        self.assert_sorted_ids('eta', items, (2, 1, 3))

    def test_created(self):
        items = [{'id': 1, 'name': 'foo', 'time-created': 5},
                 {'id': 2, 'name': 'bar', 'time-created': 7},
                 {'id': 3, 'name': 'baz', 'time-created': 6}]
        self.assert_sorted_ids('created', items, (1, 3, 2))

    def test_added(self):
        items = [{'id': 1, 'name': 'foo', 'time-added': 71},
                 {'id': 2, 'name': 'bar', 'time-added': 39},
                 {'id': 3, 'name': 'baz', 'time-added': 42}]
        self.assert_sorted_ids('added', items, (2, 3, 1))

    def test_started(self):
        items = [{'id': 1, 'name': 'foo', 'time-started': 84},
                 {'id': 2, 'name': 'bar', 'time-started': 91},
                 {'id': 3, 'name': 'baz', 'time-started': 48}]
        self.assert_sorted_ids('started', items, (3, 1, 2))

    def test_activity(self):
        items = [{'id': 1, 'name': 'foo', 'time-activity': 32},
                 {'id': 2, 'name': 'bar', 'time-activity': 92},
                 {'id': 3, 'name': 'baz', 'time-activity': 47}]
        self.assert_sorted_ids('activity', items, (1, 3, 2))

    def test_completed(self):
        items = [{'id': 1, 'name': 'foo', 'time-completed': 64},
                 {'id': 2, 'name': 'bar', 'time-completed': 28},
                 {'id': 3, 'name': 'baz', 'time-completed': 84}]
        self.assert_sorted_ids('completed', items, (2, 1, 3))
