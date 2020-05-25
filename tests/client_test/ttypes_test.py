import random
import unittest

from stig.client import ttypes


class TestValueTypes(unittest.TestCase):
    def test_Torrent_types(self):
        for t in ttypes.TYPES.values():
            self.assertTrue(isinstance(t, type) or t is None)

    def test_TorrentPeer_types(self):
        for t in ttypes.TorrentPeer.TYPES.values():
            self.assertTrue(isinstance(t, type) or t is None)

    def test_TorrentFile_types(self):
        for t in ttypes.TorrentFile.TYPES.values():
            self.assertTrue(isinstance(t, type) or t is None)

    def test_TorrentTracker_types(self):
        for t in ttypes.TorrentTracker.TYPES.values():
            self.assertTrue(isinstance(t, type) or t is None)


class TestTorrentFilePriority(unittest.TestCase):
    def test_int_values(self):
        for i in range(-2, 2):
            ttypes.TorrentFilePriority(i)
        for i in (-3, 2):
            with self.assertRaises(ValueError):
                ttypes.TorrentFilePriority(-3)

    def test_str_values(self):
        for s in ('off', 'low', 'normal', 'high'):
            ttypes.TorrentFilePriority(s)
        for s in ('offf', 'norm', 'adsf'):
            with self.assertRaises(ValueError):
                ttypes.TorrentFilePriority(s)

    def test_equality(self):
        for i,s in ((-2, 'off'), (-1, 'low'), (0, 'normal'), (1, 'high')):
            self.assertEqual(ttypes.TorrentFilePriority(i), s)
            self.assertEqual(ttypes.TorrentFilePriority(s), i)
            self.assertEqual(ttypes.TorrentFilePriority(i), ttypes.TorrentFilePriority(s))
            self.assertEqual(ttypes.TorrentFilePriority(s), ttypes.TorrentFilePriority(i))
            self.assertNotEqual(ttypes.TorrentFilePriority(s), 'foo')
            self.assertNotEqual(ttypes.TorrentFilePriority(s), None)
            self.assertNotEqual(ttypes.TorrentFilePriority(s), NotImplemented)

    def test_sort_order(self):
        prios = [
            ttypes.TorrentFilePriority(-2),
            ttypes.TorrentFilePriority(-1),
            ttypes.TorrentFilePriority(0),
            ttypes.TorrentFilePriority(1),
        ]

        def shuffle(l):
            return random.sample(l, k=len(l))

        for _ in range(10):
            self.assertEqual(sorted(shuffle(prios)), prios)
