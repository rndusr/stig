from stig.tui.cli import CLIEditWidget

import unittest
import tempfile
import os

from . _handle_urwidpatches import (setUpModule, tearDownModule)


class TestCLIEditWidget(unittest.TestCase):
    def setUp(self):
        def on_cancel(w):
            w.set_edit_text('')
        def on_accept(w):
            on_cancel(w)
            self.accepted_line = w.edit_text
        self.w = CLIEditWidget(on_cancel=on_cancel, on_accept=on_accept)
        fd, self.history_filepath = tempfile.mkstemp()

    def tearDown(self):
        os.remove(self.history_filepath)

    def enter_line(self, line):
        for char in str(line):
            self.w.keypress((80,), char)
        self.w.keypress((80,), 'enter')

    def get_history_on_disk(self):
        with open(self.history_filepath, 'r') as f:
            return [line.strip('\n') for line in f.readlines()]

    def assert_history_on_disk(self, exp_history):
        self.assertEqual(self.get_history_on_disk(), list(exp_history))

    def assert_history_in_memory(self, exp_history):
        # Internally, history is stored reversed
        self.assertEqual(self.w._history, list(reversed(exp_history)))

    def test_history(self):
        exp_history = []
        for line in ('foo', 'bar', 'baz'):
            self.assert_history_in_memory(exp_history)
            self.enter_line(line)
            exp_history.append(line)
            self.assert_history_in_memory(exp_history)

    def test_history_in_memory_max_size(self):
        self.w.history_size = 3
        for text in ('one', 'two', 'three'):
            self.enter_line(text)
        self.assert_history_in_memory(['one', 'two', 'three'])
        self.enter_line('four')
        self.assert_history_in_memory(['two', 'three', 'four'])

        self.w.history_size = 4
        self.enter_line('five')
        self.assert_history_in_memory(['two', 'three', 'four', 'five'])
        self.enter_line('six')
        self.assert_history_in_memory(['three', 'four', 'five', 'six'])

        self.w.history_size = 3
        self.assert_history_in_memory(['four', 'five', 'six'])

    def test_history_file_disabled(self):
        self.w.history_file = None
        lines = ['foo', 'bar', 'baz']
        for line in lines:
            self.enter_line(line)
        self.assert_history_in_memory(lines)
        self.assert_history_on_disk([])

    def test_history_file_enabled(self):
        self.w.history_file = self.history_filepath
        lines = ['foo', 'bar', 'baz']
        for i,line in enumerate(lines, start=1):
            self.enter_line(line)
        self.assert_history_in_memory(lines)
        self.assert_history_on_disk(lines)

    def test_history_file_overtrim(self):
        self.w.history_file = self.history_filepath
        self.w.history_size = 30

        lines = [str(i) for i in range(1, 101)]
        hist_disk_must_be_smaller_than_hist_mem = False
        for i,line in enumerate(lines, start=1):
            self.enter_line(line)

            hist_mem_start = max(0, i - self.w.history_size)
            hist_mem_stop  = i
            hist_mem = lines[hist_mem_start:hist_mem_stop]
            self.assert_history_in_memory(hist_mem)

            # Every time the on-disk history reaches the same size as the
            # in-memory history, it should trim off a bit more than necessary.
            hist_disk = self.get_history_on_disk()
            if hist_disk_must_be_smaller_than_hist_mem:
                self.assertTrue(len(hist_disk) < len(hist_mem))
            else:
                self.assertTrue(len(hist_disk) <= len(hist_mem))

            if len(hist_mem) == self.w.history_size and \
               len(hist_disk) == len(hist_mem):
                hist_disk_must_be_smaller_than_hist_mem = True
            else:
                hist_disk_must_be_smaller_than_hist_mem = False

    def test_no_completer(self):
        edit_text = self.w.edit_text
        self.w.keypress((80,), 'tab')
        self.assertEqual(self.w.edit_text, edit_text)

    def test_completer(self):
        def completer(line, curpos):
            return 'foo', 1
        self.w.completer = completer

        self.assertNotEqual(self.w.edit_text, 'foo')
        self.assertNotEqual(self.w.edit_pos, 1)
        self.w.keypress((80,), 'tab')
        self.assertEqual(self.w.edit_text, 'foo')
        self.assertEqual(self.w.edit_pos, 1)
