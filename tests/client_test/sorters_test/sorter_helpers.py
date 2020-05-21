import random
import unittest


class TestSorterBase(unittest.TestCase):
    sorter_cls = None

    def assert_sorted_ids(self, sorter_name, items, exp_ids):
        random.shuffle(items)
        sorter_names = (sorter_name,) + tuple(self.sorter_cls.SORTSPECS[sorter_name].aliases)
        for sort_str in sorter_names:
            sorter = self.sorter_cls((sort_str,))
            self.assertEqual(tuple(item['id'] for item in sorter.apply(items)), exp_ids)
