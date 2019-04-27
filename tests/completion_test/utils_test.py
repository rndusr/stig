from stig.completion import _utils as utils

import unittest


class MockTree(dict):
    nodetype = 'parent'

class MockLeaf(str):
    nodetype = 'leaf'

class Test_find_subtree(unittest.TestCase):
    def test_single_file_torrent(self):
        torrent = {'name': 'foo',
                   'files': MockTree(foo=MockLeaf('bar'))}
        self.assertEqual(utils.find_subtree(torrent, ('foo',)), None)
        self.assertEqual(utils.find_subtree(torrent, ('bar',)), None)

    def setUp(self):
        self.torrent = {'name': 'foo',
                        'files': MockTree(foo=MockTree(bar1=MockTree(baz1=MockTree(bat1=MockTree(bam1=MockLeaf('bam1'),
                                                                                                 bam2=MockLeaf('bam2')),
                                                                                   bat2=MockTree(mab1=MockLeaf('mab1'),
                                                                                                 mab2=MockLeaf('mab2'))),
                                                                     baz2=MockTree(bat1=MockTree(bax1=MockLeaf('bax1'),
                                                                                                 bax2=MockLeaf('bax2')),
                                                                                   bat2=MockTree(xab1=MockLeaf('xab1'),
                                                                                                 xab2=MockLeaf('xab2')))),
                                                       bar2=MockTree(zap1=MockLeaf('zap1'),
                                                                     zap2=MockLeaf('zap2'))))}

    def test_path_points_to_directory(self):
        self.assertEqual(utils.find_subtree(self.torrent, ('bar2',)),
                         MockTree(zap1=MockLeaf('zap1'),
                                  zap2=MockLeaf('zap2')))
        self.assertEqual(utils.find_subtree(self.torrent, ('bar1', 'baz1', 'bat1')),
                         MockTree(bam1=MockLeaf('bam1'),
                                  bam2=MockLeaf('bam2')))
        self.assertEqual(utils.find_subtree(self.torrent, ('bar1', 'baz1', 'bat2')),
                         MockTree(mab1=MockLeaf('mab1'),
                                  mab2=MockLeaf('mab2')))
        self.assertEqual(utils.find_subtree(self.torrent, ('bar1', 'baz2', 'bat1')),
                         MockTree(bax1=MockLeaf('bax1'),
                                  bax2=MockLeaf('bax2')))
        self.assertEqual(utils.find_subtree(self.torrent, ('bar1', 'baz2', 'bat2')),
                         MockTree(xab1=MockLeaf('xab1'),
                                  xab2=MockLeaf('xab2')))

    def test_path_points_to_file(self):
        self.assertEqual(utils.find_subtree(self.torrent, ('bar2', 'zap1')), MockLeaf('zap1'))
        self.assertEqual(utils.find_subtree(self.torrent, ('bar2', 'zap2')), MockLeaf('zap2'))
        self.assertEqual(utils.find_subtree(self.torrent, ('bar1', 'baz1', 'bat1', 'bam1')), MockLeaf('bam1'))
        self.assertEqual(utils.find_subtree(self.torrent, ('bar1', 'baz1', 'bat1', 'bam2')), MockLeaf('bam2'))

    def test_last_part_of_path_does_not_exist(self):
        self.assertEqual(utils.find_subtree(self.torrent, ('xxx',)),
                         self.torrent['files']['foo'])
        self.assertEqual(utils.find_subtree(self.torrent, ('bar1', 'xxx',)),
                         self.torrent['files']['foo']['bar1'])
        self.assertEqual(utils.find_subtree(self.torrent, ('bar2', 'xxx',)),
                         self.torrent['files']['foo']['bar2'])
        self.assertEqual(utils.find_subtree(self.torrent, ('bar1', 'baz1', 'xxx',)),
                         self.torrent['files']['foo']['bar1']['baz1'])
        self.assertEqual(utils.find_subtree(self.torrent, ('bar1', 'baz2', 'xxx',)),
                         self.torrent['files']['foo']['bar1']['baz2'])
        self.assertEqual(utils.find_subtree(self.torrent, ('bar1', 'baz2', 'bat2', 'xxx',)),
                         self.torrent['files']['foo']['bar1']['baz2']['bat2'])

    def test_nonlast_part_of_path_does_not_exist(self):
        self.assertEqual(utils.find_subtree(self.torrent, ('xxx', 'foo')), None)
        self.assertEqual(utils.find_subtree(self.torrent, ('xxx', 'bar1')), None)
        self.assertEqual(utils.find_subtree(self.torrent, ('bar1', 'xxx', 'baz1')), None)
        self.assertEqual(utils.find_subtree(self.torrent, ('bar1', 'baz1', 'bat1', 'xxx', 'bam1')), None)
        self.assertEqual(utils.find_subtree(self.torrent, ('bar1', 'baz1', 'xxx', 'bat2', 'mab2')), None)
        self.assertEqual(utils.find_subtree(self.torrent, ('bar2', 'xxx', 'zap2')), None)

    def test_leaf_at_nonlast_part_in_path(self):
        self.assertEqual(utils.find_subtree(self.torrent, ('bar2', 'zap1', 'xxx')), None)
        self.assertEqual(utils.find_subtree(self.torrent, ('bar2', 'zap2', 'xxx')), None)
        self.assertEqual(utils.find_subtree(self.torrent, ('bar2', 'zap2', 'xxx', 'yyy', 'zzz')), None)
        self.assertEqual(utils.find_subtree(self.torrent, ('bar1', 'baz2', 'bat1', 'bax1', 'xxx')), None)
