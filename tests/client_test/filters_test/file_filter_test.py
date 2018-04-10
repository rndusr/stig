from stig.client.filters.file import (TorrentFileFilter)
from stig.client.ttypes import TorrentFile

import unittest


flist = (
    TorrentFile(tid=1, path='', id=1, name='Foo',  is_wanted=True,  priority='normal',
                location='/download/path', size_total=10e3, size_downloaded=10e3),
    TorrentFile(tid=1, path='', id=2, name='Bar',  is_wanted=False, priority='normal',
                location='/download/path', size_total=20e3, size_downloaded=10e3),
    TorrentFile(tid=1, path='', id=3, name='Baz',  is_wanted=True,  priority='low',
                location='/download/path', size_total=20e3, size_downloaded=20e3),
    TorrentFile(tid=1, path='', id=4, name='Bang', is_wanted=True,  priority='high',
                location='/download/path', size_total=30e3, size_downloaded=20e3),
    TorrentFile(tid=1, path='', id=5, name='Flup', is_wanted=False, priority='high',
                location='/download/path', size_total=30e3, size_downloaded=30e3),
)


def f(filter_str):
    return tuple(TorrentFileFilter(filter_str).apply(flist))


class Test_FileFilter(unittest.TestCase):
    def test_name_filter(self):
        self.assertEqual(f('name=Foo'), (flist[0],))
        self.assertEqual(f('name~F'), (flist[0], flist[4]))
        self.assertEqual(f('name~Ba'), (flist[1], flist[2], flist[3]))

    def test_wanted_filter(self):
        self.assertEqual(f('wanted'), (flist[0], flist[2], flist[3]))
        self.assertEqual(f('!wanted'), (flist[1], flist[4]))

    def test_priority_filter(self):
        self.assertEqual(f('priority=low'), (flist[2],))
        self.assertEqual(f('priority=normal'), (flist[0],))
        self.assertEqual(f('priority=high'), (flist[3],))
        self.assertEqual(f('priority=off'), (flist[1], flist[4]))

        with self.assertRaises(ValueError) as cm:
            f('priority=foo')
        self.assertIn('foo', str(cm.exception))
