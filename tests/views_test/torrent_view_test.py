import unittest

from stig.views.details import SECTIONS
from stig.views.torrent import ALIASES, COLUMNS


def _item(label):
    for section in SECTIONS:
        for item in section['items']:
            if item.label == label:
                return item
    raise LookupError(label)


class TestSequentialDetailsItem(unittest.TestCase):
    def setUp(self):
        self.item = _item('Mode')

    def test_needed_keys(self):
        self.assertEqual(self.item.needed_keys, ('sequential', 'sequential-from-piece'))

    def test_non_sequential(self):
        t = {'sequential': False, 'sequential-from-piece': 0}
        self.assertEqual(self.item.human_readable(t), 'non-sequential')
        self.assertEqual(self.item.machine_readable(t), 'non-sequential\t0')

    def test_sequential_from_first_piece(self):
        t = {'sequential': True, 'sequential-from-piece': 0}
        self.assertEqual(self.item.human_readable(t), 'sequential from piece #0')
        self.assertEqual(self.item.machine_readable(t), 'sequential\t0')

    def test_sequential_from_other_piece(self):
        t = {'sequential': True, 'sequential-from-piece': 1200}
        self.assertEqual(self.item.human_readable(t), 'sequential from piece #1200')
        self.assertEqual(self.item.machine_readable(t), 'sequential\t1200')


class TestSequentialColumn(unittest.TestCase):
    def value(self, sequential, from_piece):
        column = COLUMNS['sequential']({'sequential': sequential,
                                        'sequential-from-piece': from_piece})
        return column.get_value()

    def test_alias(self):
        self.assertEqual(ALIASES['seq'], 'sequential')

    def test_non_sequential(self):
        self.assertEqual(self.value(False, 0), 'no')
        # The daemon remembers the starting piece while sequential is off
        self.assertEqual(self.value(False, 1200), 'no')

    def test_sequential_from_first_piece(self):
        self.assertEqual(self.value(True, 0), 'yes')

    def test_sequential_from_other_piece(self):
        self.assertEqual(self.value(True, 1200), '#1200')

    def test_value_fits_in_column(self):
        for value in (self.value(False, 0), self.value(True, 0), self.value(True, 999)):
            self.assertLessEqual(len(value), COLUMNS['sequential'].width)
