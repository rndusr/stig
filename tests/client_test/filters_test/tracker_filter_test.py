from stig.client.filters.tracker import _SingleFilter as TrackerFilter

import unittest
from helpers import HelpersMixin


class TestTrackerFilter(unittest.TestCase, HelpersMixin):
    def test_default_filter(self):
        self.assertEqual(TrackerFilter.DEFAULT_FILTER, 'domain')

    def test_all(self):
        self.check_bool_filter(TrackerFilter,
                               filter_names=('all', '*'),
                               items=({'id': 1}, {'id': 2}, {'id': 3}),
                               test_cases=(('{name}', (1, 2, 3)),
                                           ('!{name}', ())))

    def test_alive(self):
        self.check_bool_filter(TrackerFilter,
                               filter_names=('alive',),
                               items=({'id': 1, 'error': '', 'status': 'idle'},
                                      {'id': 2, 'error': 'Go away', 'status': 'stopped'},
                                      {'id': 3, 'error': '', 'status': 'announcing'}),
                               test_cases=(('{name}', (1, 3)),
                                           ('!{name}', (2,))))

    def test_tier(self):
        self.check_filter(TrackerFilter,
                          filter_names=('tier',),
                          items=({'id': 1, 'tier': 0},
                                 {'id': 2, 'tier': 1},
                                 {'id': 3, 'tier': 1}),
                          test_cases=(('{name}', (1, 2, 3)),
                                      ('!{name}', ()),
                                      ('{name}>0', (2, 3)),
                                      ('{name}>=0', (1, 2, 3)),
                                      ('{name}<0', ()),
                                      ('{name}<=0', (1,))))
        with self.assertRaises(ValueError) as cm:
            TrackerFilter('tier~5')
        self.assertEqual(str(cm.exception), "Invalid operator for filter 'tier': ~")

    def test_domain(self):
        self.check_filter(TrackerFilter,
                          filter_names=('domain', 'dom'),
                          items=({'id': 1, 'domain': 'abc.example.com'},
                                 {'id': 2, 'domain': 'abc.example.com'},
                                 {'id': 3, 'domain': 'def.example.com'}),
                          test_cases=(('{name}', (1, 2, 3)),
                                      ('!{name}', ()),
                                      ('{name}=def.example.com', (3,)),
                                      ('{name}~abc', (1, 2))))

    def test_url_announce(self):
        from stig.client.utils import URL
        self.check_filter(TrackerFilter,
                          filter_names=('url-announce', 'an'),
                          items=({'id': 1, 'url-announce': URL('http://abc.example.com:1234/foo/announce')},
                                 {'id': 2, 'url-announce': URL('http://abc.example.com:1234/bar/announce')},
                                 {'id': 3, 'url-announce': URL('http://def.example.com:4321/announce')}),
                          test_cases=(('{name}', (1, 2, 3)),
                                      ('!{name}', ()),
                                      ('{name}=http://abc.example.com:1234/bar/announce', (2,)),
                                      ('{name}~abc', (1, 2))))

    def test_url_scrape(self):
        from stig.client.utils import URL
        self.check_filter(TrackerFilter,
                          filter_names=('url-scrape', 'sc'),
                          items=({'id': 1, 'url-scrape': URL('http://abc.example.com:1234/foo/scrape')},
                                 {'id': 2, 'url-scrape': URL('http://abc.example.com:1234/bar/scrape')},
                                 {'id': 3, 'url-scrape': URL('http://def.example.com:4321/scrape')}),
                          test_cases=(('{name}', (1, 2, 3)),
                                      ('!{name}', ()),
                                      ('{name}=http://abc.example.com:1234/bar/scrape', (2,)),
                                      ('{name}~abc', (1, 2))))

    def test_status(self):
        self.check_filter(TrackerFilter,
                          filter_names=('status', 'st'),
                          items=({'id': 1, 'status': 'stopped'},
                                 {'id': 2, 'status': 'idle'},
                                 {'id': 3, 'status': 'queued'},
                                 {'id': 4, 'status': 'announcing'},
                                 {'id': 5, 'status': 'scraping'}),
                          test_cases=(('{name}', (1, 2, 3, 4, 5)),
                                      ('!{name}', ()),
                                      ('{name}=queued', (3,))))
        with self.assertRaises(ValueError) as cm:
            TrackerFilter('status=foo')
        self.assertEqual(str(cm.exception), "Invalid value for filter 'status': 'foo'")

    def test_error(self):
        self.check_str_filter(TrackerFilter,
                              filter_names=('error', 'err'),
                              key='error')

    def test_downloads(self):
        self.check_int_filter(TrackerFilter,
                              filter_names=('downloads', 'dns'),
                              key='count-downloads')

    def test_leeches(self):
        self.check_int_filter(TrackerFilter,
                              filter_names=('leeches', 'lcs'),
                              key='count-leeches')

    def test_seeds(self):
        self.check_int_filter(TrackerFilter,
                              filter_names=('seeds', 'sds'),
                              key='count-seeds')

    def test_last_announce(self):
        self.check_timestamp_filter(TrackerFilter, default_sign=-1,
                                    filter_names=('last-announce', 'lan'),
                                    key='time-last-announce')

    def test_next_announce(self):
        self.check_timestamp_filter(TrackerFilter, default_sign=1,
                                    filter_names=('next-announce', 'nan'),
                                    key='time-next-announce')

    def test_last_scrape(self):
        self.check_timestamp_filter(TrackerFilter, default_sign=-1,
                                    filter_names=('last-scrape', 'lsc'),
                                    key='time-last-scrape')

    def test_next_scrape(self):
        self.check_timestamp_filter(TrackerFilter, default_sign=1,
                                    filter_names=('next-scrape', 'nsc'),
                                    key='time-next-scrape')
