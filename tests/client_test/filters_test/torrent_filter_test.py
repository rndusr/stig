import unittest

from filter_helpers import HelpersMixin

from stig.client.filters.torrent import _SingleFilter as TorrentFilter
from stig.client.utils import Status


class TestTorrentFilter(unittest.TestCase, HelpersMixin):
    def test_default_filter(self):
        self.assertEqual(TorrentFilter.DEFAULT_FILTER, 'name')

    def test_getting_spec_by_alias(self):
        self.check_getting_spec_by_alias(TorrentFilter)

    def test_all(self):
        self.check_bool_filter(TorrentFilter,
                               filter_names=('all', '*'),
                               items=({'id': 1}, {'id': 2}, {'id': 3}),
                               test_cases=(('{name}', (1, 2, 3)),
                                           ('!{name}', ())))

    def test_complete(self):
        self.check_bool_filter(TorrentFilter,
                               filter_names=('complete', 'cmp'),
                               items=({'id': 1, '%downloaded': 0},
                                      {'id': 2, '%downloaded': 99},
                                      {'id': 3, '%downloaded': 100}),
                               test_cases=(('{name}', (3,)),
                                           ('!{name}', (1, 2))))

    def test_stopped(self):
        self.check_bool_filter(TorrentFilter,
                               filter_names=('stopped', 'stp'),
                               items=({'id': 1, 'status': (Status.STOPPED,)},
                                      {'id': 2, 'status': (Status.IDLE, Status.SEED)},
                                      {'id': 3, 'status': (Status.UPLOAD, Status.SEED)}),
                               test_cases=(('{name}', (1,)),
                                           ('!{name}', (2, 3))))

    def test_active(self):
        self.check_bool_filter(TorrentFilter,
                               filter_names=('active', 'act'),
                               items=({'id': 1, 'status': (Status.STOPPED,)},
                                      {'id': 2, 'status': (Status.CONNECTED, Status.IDLE, Status.SEED)},
                                      {'id': 3, 'status': (Status.VERIFY,)}),
                               test_cases=(('{name}', (2, 3)),
                                           ('!{name}', (1,))))

    def test_uploading(self):
        self.check_bool_filter(TorrentFilter,
                               filter_names=('uploading', 'upg'),
                               items=({'id': 1, 'rate-up': 0},
                                      {'id': 2, 'rate-up': 100},
                                      {'id': 3, 'rate-up': 2000}),
                               test_cases=(('{name}', (2, 3)),
                                           ('!{name}', (1,))))

    def test_downloading(self):
        self.check_bool_filter(TorrentFilter,
                               filter_names=('downloading', 'dng'),
                               items=({'id': 1, 'rate-down': 0},
                                      {'id': 2, 'rate-down': 100},
                                      {'id': 3, 'rate-down': 2000}),
                               test_cases=(('{name}', (2, 3)),
                                           ('!{name}', (1,))))

    def test_leeching(self):
        self.check_bool_filter(TorrentFilter,
                               filter_names=('leeching', 'lcg'),
                               items=({'id': 1, '%downloaded': 0, 'status': (Status.STOPPED,)},
                                      {'id': 2, '%downloaded': 50, 'status': (Status.IDLE,)},
                                      {'id': 3, '%downloaded': 50, 'status': (Status.CONNECTED, Status.DOWNLOAD)},
                                      {'id': 4, '%downloaded': 100, 'status': (Status.SEED, Status.IDLE)}),
                               test_cases=(('{name}', (2, 3)),
                                           ('!{name}', (1, 4))))

    def test_seeding(self):
        self.check_bool_filter(TorrentFilter,
                               filter_names=('seeding', 'sdg'),
                               items=({'id': 1, '%downloaded': 100, 'status': (Status.STOPPED,)},
                                      {'id': 2, '%downloaded': 50, 'status': (Status.IDLE,)},
                                      {'id': 3, '%downloaded': 50, 'status': (Status.CONNECTED, Status.DOWNLOAD)},
                                      {'id': 4, '%downloaded': 100, 'status': (Status.SEED, Status.IDLE)}),
                               test_cases=(('{name}', (4,)),
                                           ('!{name}', (1, 2, 3))))

    def test_verifying(self):
        self.check_bool_filter(TorrentFilter,
                               filter_names=('verifying', 'vfg'),
                               items=({'id': 1, 'status': (Status.STOPPED,)},
                                      {'id': 2, 'status': (Status.IDLE,)},
                                      {'id': 3, 'status': (Status.VERIFY)}),
                               test_cases=(('{name}', (3,)),
                                           ('!{name}', (1, 2))))

    def test_idle(self):
        self.check_bool_filter(TorrentFilter,
                               filter_names=('idle',),
                               items=({'id': 1, 'status': (Status.STOPPED,)},
                                      {'id': 2, 'status': (Status.IDLE,)},
                                      {'id': 3, 'status': (Status.VERIFY)},
                                      {'id': 4, 'status': (Status.DOWNLOAD)}),
                               test_cases=(('{name}', (2,)),
                                           ('!{name}', (1, 3, 4))))

    def test_isolated(self):
        self.check_bool_filter(TorrentFilter,
                               filter_names=('isolated', 'isl'),
                               items=({'id': 1, 'status': (Status.STOPPED, Status.SEED)},
                                      {'id': 2, 'status': (Status.VERIFY)},
                                      {'id': 3, 'status': (Status.IDLE, Status.ISOLATED)},
                                      {'id': 4, 'status': (Status.DOWNLOAD)}),
                               test_cases=(('{name}', (3,)),
                                           ('!{name}', (1, 2, 4))))

    def test_private(self):
        self.check_bool_filter(TorrentFilter,
                               filter_names=('private', 'prv'),
                               items=({'id': 1, 'private': True},
                                      {'id': 2, 'private': False}),
                               test_cases=(('{name}', (1,)),
                                           ('!{name}', (2,))))


    def test_id(self):
        self.check_filter(TorrentFilter,
                          filter_names=('id',),
                          items=({'id': 1},
                                 {'id': 2},
                                 {'id': 3}),
                          test_cases=(('{name}', (1, 2, 3)),
                                      ('!{name}', ()),
                                      ('{name}=2', (2,)),
                                      ('{name}!=3', (1, 2))))

    def test_hash(self):
        self.check_filter(TorrentFilter,
                          filter_names=('hash',),
                          items=({'id': 1, 'hash': 'f1d2d2f924e986ac86fdf7b36c94bcdf32beec15'},
                                 {'id': 2, 'hash': 'e242ed3bffccdf271b7fbaf34ed72d089537b42f'},
                                 {'id': 3, 'hash': '6eadeac2dade6347e87c0d24fd455feffa7069f0'}),
                          test_cases=(('{name}', (1, 2, 3)),
                                      ('!{name}', ()),
                                      ('{name}=e242ed3bffccdf271b7fbaf34ed72d089537b42f', (2,)),
                                      ('{name}!=e242ed3bffccdf271b7fbaf34ed72d089537b42f', (1, 3)),
                                      ('{name}~df', (1, 2)),
                                      ('{name}!~df', (3,))))

    def test_name(self):
        self.check_str_filter(TorrentFilter,
                              filter_names=('name', 'n'),
                              key='name')

    def test_comment(self):
        self.check_str_filter(TorrentFilter,
                              filter_names=('comment', 'cmnt'),
                              key='comment')

    def test_path(self):
        self.check_str_filter(TorrentFilter,
                              filter_names=('path',),
                              key='path')

    def test_error(self):
        self.check_str_filter(TorrentFilter,
                              filter_names=('error', 'err'),
                              key='error')

    def test_uploaded(self):
        self.check_int_filter(TorrentFilter,
                              filter_names=('uploaded', 'up'),
                              key='size-uploaded')

    def test_downloaded(self):
        self.check_int_filter(TorrentFilter,
                              filter_names=('downloaded', 'dn'),
                              key='size-downloaded')

    def test_percent_downloaded(self):
        self.check_int_filter(TorrentFilter,
                              filter_names=('%downloaded', '%dn'),
                              key='%downloaded')

    def test_size(self):
        self.check_int_filter(TorrentFilter,
                              filter_names=('size', 'sz'),
                              key='size-final')

    def test_peers(self):
        self.check_int_filter(TorrentFilter,
                              filter_names=('peers', 'prs'),
                              key='peers-connected')

    def test_seeds(self):
        self.check_int_filter(TorrentFilter,
                              filter_names=('seeds', 'sds'),
                              key='peers-seeding')

    def test_ratio(self):
        self.check_float_filter(TorrentFilter,
                                filter_names=('ratio', 'rto'),
                                key='ratio')

    def test_rate_up(self):
        self.check_int_filter(TorrentFilter,
                              filter_names=('rate-up', 'rup'),
                              key='rate-up')

    def test_rate_down(self):
        self.check_int_filter(TorrentFilter,
                              filter_names=('rate-down', 'rdn'),
                              key='rate-down')

    def test_limit_rate_up(self):
        self.check_limit_rate_filter(TorrentFilter,
                                     filter_names=('limit-rate-up', 'lrup'),
                                     key='limit-rate-up')

    def test_limit_rate_down(self):
        self.check_limit_rate_filter(TorrentFilter,
                                     filter_names=('limit-rate-down', 'lrdn'),
                                     key='limit-rate-down')

    def test_tracker(self):
        class MockURL(str):
            def __new__(cls, domain):
                # Only the domain is relevant for the tracker filter
                obj = super().__new__(cls, 'https://url.is.ignored.by.filter')
                obj.domain = domain
                return obj
        self.check_filter(TorrentFilter,
                          filter_names=('tracker', 'trk'),
                          items=({'id': 1, 'trackers': []},
                                 {'id': 2, 'trackers': [{'url-announce': MockURL('example.org')}]},
                                 {'id': 3, 'trackers': [{'url-announce': MockURL('example.net')},
                                                        {'url-announce': MockURL('example.org')}]}),
                          test_cases=(('{name}', (2, 3)),
                                      ('!{name}', (1,)),
                                      ('{name}=example.org', (2, 3)),
                                      ('{name}=example.net', (3,)),
                                      ('{name}!=example.org', (1,)),
                                      ('{name}!=example.net', (1, 2)),
                                      ('{name}~example', (2, 3)),
                                      ('{name}~net', (3,))))

    def test_eta(self):
        self.check_timedelta_filter(TorrentFilter, default_sign=1,
                                    filter_names=('eta',),
                                    key='timespan-eta')

    def test_created(self):
        self.check_timestamp_filter(TorrentFilter, default_sign=-1,
                                    filter_names=('created', 'tcrt'),
                                    key='time-created')

    def test_added(self):
        self.check_timestamp_filter(TorrentFilter, default_sign=-1,
                                    filter_names=('added', 'tadd'),
                                    key='time-added')

    def test_started(self):
        self.check_timestamp_filter(TorrentFilter, default_sign=-1,
                                    filter_names=('started', 'tsta'),
                                    key='time-started')

    def test_activity(self):
        self.check_timestamp_filter(TorrentFilter, default_sign=-1,
                                    filter_names=('activity', 'tact'),
                                    key='time-activity')

    def test_completed(self):
        self.check_timestamp_filter(TorrentFilter, default_sign=-1,
                                    filter_names=('completed', 'tcmp'),
                                    key='time-completed')
