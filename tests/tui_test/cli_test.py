from stig.tui.cli import CLIEditWidget

import unittest
from unittest.mock import MagicMock, patch
import tempfile
import os
import asynctest
import asyncio

from . _handle_urwidpatches import (setUpModule, tearDownModule)


class TestCLIEditWidget(asynctest.TestCase):
    def setUp(self):
        def on_accept(w):
            w.reset()
            self.accepted_line = w.edit_text
        self.w = CLIEditWidget(on_accept=on_accept)
        fd, self.history_filepath = tempfile.mkstemp()

    def tearDown(self):
        os.remove(self.history_filepath)

    def enter_line(self, line, press_return=True):
        for char in str(line):
            self.w.keypress((80,), char)
        if press_return:
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
        self.w.edit_text = 'asdf'
        self.w.keypress((80,), 'tab')
        self.assertEqual(self.w.edit_text, 'asdf')

    async def test_completer(self):
        class MockCompleter():
            update = asynctest.CoroutineMock()
            complete_next = MagicMock()
            categories = ()
        self.w._completer = self.w._candsw._completer = MockCompleter()

        self.enter_line('foo', press_return=False)
        self.assertEqual(self.w.edit_text, 'foo')
        self.w._completer.complete_next.return_value = ('foobar', 3)
        await asyncio.wait_for(self.w._completion_update_task, timeout=10)
        self.w.keypress((80,), 'tab')
        self.assertEqual(self.w.edit_text, 'foobar')
        self.assertEqual(self.w.edit_pos, 3)
