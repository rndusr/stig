from stig.client.aiotransmission import torrent

import unittest


def test_all_dependencies_are_standard_keys():
    from stig.client.tkeys import TYPES
    assert set(torrent.DEPENDENCIES) == set(TYPES)


class Test_is_isolated(unittest.TestCase):
    def test_no_trackers_and_public(self):
        tc = torrent._is_isolated({'isPrivate': False, 'trackerStats': []})
        self.assertEqual(tc, False)

    def test_no_trackers_and_private(self):
        tc = torrent._is_isolated({'isPrivate': True, 'trackerStats': []})
        self.assertEqual(tc, True)

    def test_trackers_and_private(self):
        tc = torrent._is_isolated(
            {'isPrivate': True,
             'trackerStats': [{'lastAnnounceSucceeded': False, 'hasAnnounced': False},
                              {'lastAnnounceSucceeded': False, 'hasAnnounced': True}]}
        )
        self.assertEqual(tc, True)
        tc = torrent._is_isolated(
            {'isPrivate': True,
             'trackerStats': [{'lastAnnounceSucceeded': False, 'hasAnnounced': False},
                              {'lastAnnounceSucceeded': True, 'hasAnnounced': True}]}
        )
        self.assertEqual(tc, False)


class TestTorrentFields(unittest.TestCase):
    def test_handpicked_fields(self):
        testcase = ('id', 'hash', 'name', 'status', 'id', 'id', 'id')
        expect = ('id', 'hashString', 'name', 'status',
                  'metadataPercentComplete', 'rateDownload', 'rateUpload',
                  'peersConnected', 'trackerStats', 'isPrivate')
        self.assertEqual(sorted(torrent.TorrentFields(*testcase)),
                         sorted(expect))

    def test_preset_all(self):
        self.assertEqual(sorted(torrent.TorrentFields('all')),
                         sorted(torrent.TorrentFields._ALL_FIELDS))

    def test_equality(self):
        fields = torrent.TorrentFields._ALL_FIELDS
        from random import shuffle
        for _ in range(10):
            f1 = list(fields) ; shuffle(f1)
            f2 = list(fields) ; shuffle(f2)
            self.assertEqual(torrent.TorrentFields(*f1),
                             torrent.TorrentFields(*f2))

    def test_adding(self):
        f1 = torrent.TorrentFields('name', 'stalled')
        f2 = torrent.TorrentFields('name', 'ratio')
        f3 = torrent.TorrentFields('hash', 'status')
        self.assertEqual(f1+f2, torrent.TorrentFields('name', 'stalled', 'ratio'))
        self.assertEqual(f1+f3, torrent.TorrentFields('name', 'stalled', 'hash', 'status'))
        self.assertEqual(f2+f3, torrent.TorrentFields('name', 'ratio', 'hash', 'status'))
        self.assertEqual(f1+f2+f3, torrent.TorrentFields('name', 'stalled', 'ratio', 'hash', 'status'))


class TestTorrent(unittest.TestCase):
    def test_contains(self):
        raw = {'id': 123, 'name': 'Fake torrent',
               'rateDownload': 10000, 'hashString': 'foobar',
               'doneDate': 18902394873, 'recheckProgress': 0.4832}
        t = torrent.Torrent(raw)
        self.assertEqual(set(t), {'id', 'name', 'rate-down', 'hash',
                                  'timestamp-done', '%verified'})
