import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from stig.completion import _utils as utils
from stig.completion import candidates


class Test_filter_helper_functions(unittest.TestCase):
    @patch('stig.completion.candidates._utils.filter_clses')
    def test_get_filter_cls(self, mock_filter_clses):
        mock_filter_clses.mock_add_spec(('FooFilter',), spec_set=True)
        mock_filter_clses.FooFilter = 'mock filter'
        self.assertEqual(candidates._utils.get_filter_cls('FooFilter'), 'mock filter')
        with self.assertRaises(ValueError):
            candidates._utils.get_filter_cls('BarFilter')

    def test_get_filter_names(self):
        mock_filter_cls = MagicMock()
        mock_filter_cls.BOOLEAN_FILTERS = {'foo': None, 'bar': None}
        mock_filter_cls.COMPARATIVE_FILTERS = {'baz': None}
        import sys
        if sys.hexversion < 0x03060000:
            # Python <= 3.6 dicts are not ordered yet
            self.assertEqual(set(candidates._utils.get_filter_names(mock_filter_cls)),
                             {'foo', 'bar', 'baz'})
        else:
            self.assertEqual(tuple(candidates._utils.get_filter_names(mock_filter_cls)),
                             ('foo', 'bar', 'baz'))

    def test_get_filter_spec(self):
        mock_filter_cls = MagicMock()
        mock_filter_cls.BOOLEAN_FILTERS = {'foo': 'mock foo spec', 'bar': 'mock bar spec'}
        mock_filter_cls.COMPARATIVE_FILTERS = {'baz': 'mock baz spec'}
        self.assertEqual(candidates._utils.get_filter_spec(mock_filter_cls, 'foo'), 'mock foo spec')
        self.assertEqual(candidates._utils.get_filter_spec(mock_filter_cls, 'bar'), 'mock bar spec')
        self.assertEqual(candidates._utils.get_filter_spec(mock_filter_cls, 'baz'), 'mock baz spec')

    def test_filter_takes_completable_values(self):
        mock_filter_cls = MagicMock()
        mock_filter_cls.BOOLEAN_FILTERS = {'foo': None}
        mock_filter_cls.COMPARATIVE_FILTERS = {'bar': SimpleNamespace(value_type=str),
                                               'baz': SimpleNamespace(value_type=int)}
        self.assertEqual(candidates._utils.filter_takes_completable_values(mock_filter_cls, 'bar'), True)
        self.assertEqual(candidates._utils.filter_takes_completable_values(mock_filter_cls, 'baz'), False)
        self.assertEqual(candidates._utils.filter_takes_completable_values(mock_filter_cls, 'foo'), False)
        self.assertEqual(candidates._utils.filter_takes_completable_values(mock_filter_cls, 'asdf'), False)



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
