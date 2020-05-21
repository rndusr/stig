from sorter_helpers import TestSorterBase
from stig.client.sorters import SettingSorter


class TestSettingSorter(TestSorterBase):
    sorter_cls = SettingSorter

    def test_default_sorter(self):
        self.assertEqual(SettingSorter.DEFAULT_SORT, 'name')

    def test_name(self):
        # 'id' is the setting's name
        items = [{'id': 'foo'},
                 {'id': 'bar'},
                 {'id': 'baz'}]
        self.assert_sorted_ids('name', items, ('bar', 'baz', 'foo'))

    def test_value(self):
        items = [{'id': 1, 'value': 'five'},
                 {'id': 2, 'value': 5},
                 {'id': 3, 'value': 'IV'}]
        self.assert_sorted_ids('value', items, (1, 3, 2))

    def test_default(self):
        items = [{'id': 1, 'default': 5},
                 {'id': 2, 'default': 'IV'},
                 {'id': 3, 'default': 'five'}]
        self.assert_sorted_ids('default', items, (3, 2, 1))

    def test_description(self):
        items = [{'id': 1, 'description': 'This is a setting'},
                 {'id': 2, 'description': 'This is another setting'},
                 {'id': 3, 'description': 'Also a setting'}]
        self.assert_sorted_ids('description', items, (3, 1, 2))
