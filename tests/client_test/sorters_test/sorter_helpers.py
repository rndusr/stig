import unittest
import random


class TestSorterBase(unittest.TestCase):
    sorter_cls = None

    def assert_sorted_ids(self, sorter_name, items, exp_ids):
        random.shuffle(items)
        print(self.sorter_cls)
        sorter_names = (sorter_name,) + tuple(self.sorter_cls.SORTSPECS[sorter_name].aliases)
        print('sorter_names:', sorter_names)
        print('items:', items)
        for sort_str in sorter_names:
            print('sort_str:', sort_str)
            sorter = self.sorter_cls((sort_str,))
            print('sorter:', repr(sorter))
            self.assertEqual(tuple(item['id'] for item in sorter.apply(items)), exp_ids)
