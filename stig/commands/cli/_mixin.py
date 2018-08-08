# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details
# http://www.gnu.org/licenses/gpl-3.0.txt

"""Mixin classes for CLI commands"""

from ...logging import make_logger
log = make_logger(__name__)

from .. import ExpectedResource
from .. import utils
from ._common import clear_line


class make_request():
    async def make_request(self, request_coro, polling_frenzy=False, quiet=False):
        """Awaits request coroutine and logs messages; returns response"""
        response = await request_coro
        utils.log_msgs(self, response, quiet)
        return response


class ask_yes_no():
    aioloop = ExpectedResource

    ANSWERS = {'y': True, 'n': False,
               'Y': True, 'N': False,
               '\x03': False,  # ctrl-c
               '\x07': False,  # ctrl-g
               '\x1b': False}  # escape

    async def ask_yes_no(self, question, yes=None, no=None, after=None):
        """
        Ask user a yes/no question and return True/False

        The `yes` and `no` arguments are callbacks (or None) that are called
        depending on the user's answer. `after` is called after the user
        answered and after `yes` or `no` has been called.

        Callbacks may be normal functions, coroutine functions or
        coroutines. They don't get any arguments and their return value is
        ignored.
        """
        answer = await self._get_answer(question)
        if answer:
            await self._run_func_or_coro(yes)
        else:
            await self._run_func_or_coro(no)
        await self._run_func_or_coro(after)
        return answer

    async def _run_func_or_coro(self, func_or_coro):
        import asyncio
        if asyncio.iscoroutinefunction(func_or_coro):
            await func_or_coro()
        elif asyncio.iscoroutine(func_or_coro):
            await func_or_coro
        elif func_or_coro is not None:
            func_or_coro()

    async def _get_answer(self, question):
        import sys, tty, termios

        if not sys.stdout.isatty():
            # We can't ask the user - default to None (which evaluates to False)
            return None

        async def aiogetch(loop):
            # Disable printing of typed characters
            old_settings = termios.tcgetattr(sys.stdin.fileno())
            tty.setraw(sys.stdin.fileno())

            # Read exactly one character
            key = await loop.run_in_executor(None, sys.stdin.read, 1)

            # Restore terminal settings
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_settings)

            return key

        # Get answer from user
        answer = None
        while answer is None:
            print(question, end=' [y|n] ', flush=True)
            key = await aiogetch(self.aioloop)
            clear_line()
            answer = self.ANSWERS.get(key, None)
        return answer


class select_torrents():
    def select_torrents(self, FILTER, allow_no_filter=True, discover_torrent=None, prefer_focused=None):
        """
        Get TorrentFilter instance or None

        If `FILTER` evaluates to True, it is passed to TorrentFilter and the
        resulting object is returned.

        If `FILTER` evaluates to False, None is returned if allow_no_filter
        evaluates to True, otherwise a ValueError is raised.

        `discover_torrent` and `prefer_focused` are ignored and only used in the
        TUI version of this method.
        """
        if FILTER:
            from ...client import TorrentFilter
            return TorrentFilter(FILTER)
        else:
            if allow_no_filter:
                return None
            else:
                raise ValueError('No torrent specified')


class select_files():
    def get_focused_path_in_torrent(self):
        """Return relative path in torrent of focused file or directory"""
        pass

    def select_files(self, FILTER, allow_no_filter=True, discover_file=None):
        """
        Get TorrentFileFilter instance or None

        If `FILTER` evaluates to True, it is passed to TorrentFileFilter and the
        resulting object is returned.

        If `FILTER` evaluates to False, None is returned if allow_no_filter
        evaluates to True, otherwise a ValueError is raised.

        `discover_file` is ignored and only used in the TUI version of this
        method (see ..tui.mixin.select_file).
        """
        if FILTER:
            from ...client import TorrentFileFilter
            return TorrentFileFilter(FILTER)
        else:
            if allow_no_filter:
                return None
            else:
                raise ValueError('No torrent specified')


class only_supported_columns():
    def only_supported_columns(self, columns, specs):
        """Remove columns from list `columns` that don't support the CLI"""
        return [col for col in columns
                if 'cli' in specs[col].interfaces]
