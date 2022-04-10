from sorter_helpers import TestSorterBase

from stig.client.sorters import TrackerSorter


class TestTrackerSorter(TestSorterBase):
    sorter_cls = TrackerSorter

    def test_default_sorter(self):
        self.assertEqual(TrackerSorter.DEFAULT_SORT, 'domain')

    def test_torrent(self):
        items = [{'id': 1, 'domain': 'example.org', 'tname': 'Foo'},
                 {'id': 2, 'domain': 'example.org', 'tname': 'bar'},
                 {'id': 3, 'domain': 'example.org', 'tname': 'Baz'}]
        self.assert_sorted_ids('torrent', items, (2, 3, 1))

    def test_tier(self):
        items = [{'id': 1, 'domain': 'example.org', 'tier': 0},
                 {'id': 2, 'domain': 'example.org', 'tier': 2},
                 {'id': 3, 'domain': 'example.org', 'tier': 1}]
        self.assert_sorted_ids('tier', items, (1, 3, 2))

    def test_domain(self):
        items = [{'id': 1, 'domain': 'foo.example.org'},
                 {'id': 2, 'domain': 'bar.example.org'},
                 {'id': 3, 'domain': 'baz.example.org'}]
        self.assert_sorted_ids('domain', items, (2, 3, 1))

    def test_status(self):
        items = [{'id': 1, 'domain': 'example.org', 'status': 'idle'},
                 {'id': 2, 'domain': 'example.org', 'status': 'announcing'},
                 {'id': 3, 'domain': 'example.org', 'status': 'scraping'}]
        self.assert_sorted_ids('status', items, (2, 1, 3))

    def test_error(self):
        items = [{'id': 1, 'domain': 'example.org', 'error': 'no'},
                 {'id': 2, 'domain': 'example.org', 'error': 'Nu-uh!'},
                 {'id': 3, 'domain': 'example.org', 'error': 'go away'}]
        self.assert_sorted_ids('error', items, (3, 1, 2))

    def test_downloads(self):
        items = [{'id': 1, 'domain': 'example.org', 'count-downloads': 0},
                 {'id': 2, 'domain': 'example.org', 'count-downloads': 15},
                 {'id': 3, 'domain': 'example.org', 'count-downloads': 4}]
        self.assert_sorted_ids('downloads', items, (1, 3, 2))

    def test_leeches(self):
        items = [{'id': 1, 'domain': 'example.org', 'count-leeches': 58},
                 {'id': 2, 'domain': 'example.org', 'count-leeches': 21},
                 {'id': 3, 'domain': 'example.org', 'count-leeches': 0}]
        self.assert_sorted_ids('leeches', items, (3, 2, 1))

    def test_seeds(self):
        items = [{'id': 1, 'domain': 'example.org', 'count-seeds': 58},
                 {'id': 2, 'domain': 'example.org', 'count-seeds': 2},
                 {'id': 3, 'domain': 'example.org', 'count-seeds': 991}]
        self.assert_sorted_ids('seeds', items, (2, 1, 3))

    def test_last_announce(self):
        items = [{'id': 1, 'domain': 'example.org', 'time-last-announce': 92},
                 {'id': 2, 'domain': 'example.org', 'time-last-announce': 1000},
                 {'id': 3, 'domain': 'example.org', 'time-last-announce': 4}]
        self.assert_sorted_ids('last-announce', items, (3, 1, 2))

    def test_next_announce(self):
        items = [{'id': 1, 'domain': 'example.org', 'time-next-announce': 84},
                 {'id': 2, 'domain': 'example.org', 'time-next-announce': 399},
                 {'id': 3, 'domain': 'example.org', 'time-next-announce': 994}]
        self.assert_sorted_ids('next-announce', items, (1, 2, 3))

    def test_last_scrape(self):
        items = [{'id': 1, 'domain': 'example.org', 'time-last-scrape': 92},
                 {'id': 2, 'domain': 'example.org', 'time-last-scrape': 1000},
                 {'id': 3, 'domain': 'example.org', 'time-last-scrape': 4}]
        self.assert_sorted_ids('last-scrape', items, (3, 1, 2))

    def test_next_scrape(self):
        items = [{'id': 1, 'domain': 'example.org', 'time-next-scrape': 84},
                 {'id': 2, 'domain': 'example.org', 'time-next-scrape': 399},
                 {'id': 3, 'domain': 'example.org', 'time-next-scrape': 994}]
        self.assert_sorted_ids('next-scrape', items, (1, 2, 3))
