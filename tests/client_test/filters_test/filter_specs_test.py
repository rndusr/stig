import unittest

from stig.client import filters


class FilterSpecTests(unittest.TestCase):
    def filter_classes(self):
        for attr in dir(filters):
            if attr.endswith('Filter'):
                yield getattr(filters, attr)

    def test_boolean_filter_specs(self):
        for fcls in self.filter_classes():
            print(fcls)
            for fspec in fcls.BOOLEAN_FILTERS.values():
                self.assertTrue(callable(fspec.filter_function) or fspec.filter_function is None)
                self.assertTrue(isinstance(fspec.needed_keys, tuple))
                self.assertTrue(all(isinstance(key, str) for key in fspec.needed_keys))
                self.assertTrue(isinstance(fspec.aliases, tuple))
                self.assertTrue(all(isinstance(key, str) for key in fspec.aliases))
                self.assertTrue(isinstance(fspec.description, str))

    def test_comparative_filter_specs(self):
        for fcls in self.filter_classes():
            print(fcls)
            for fspec in fcls.COMPARATIVE_FILTERS.values():
                self.assertTrue(isinstance(fspec.needed_keys, tuple))
                self.assertTrue(all(isinstance(key, str) for key in fspec.needed_keys))
                self.assertTrue(isinstance(fspec.aliases, tuple))
                self.assertTrue(all(isinstance(key, str) for key in fspec.aliases))
                self.assertTrue(isinstance(fspec.description, str))

                self.assertTrue(callable(fspec.value_matcher))
                self.assertTrue(callable(fspec.value_getter))
                self.assertTrue(callable(fspec.value_convert) or isinstance(fspec.value_convert, type))
                self.assertTrue(isinstance(fspec.value_type, type))
