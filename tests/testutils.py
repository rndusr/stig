"""Helpers for asynchronous tests"""

import asyncio
import unittest

# How often to give the event loop a chance to run callbacks that became due
# after advancing the clock.  Callbacks that wake up other callbacks need one
# iteration each.
_ADVANCE_ITERATIONS = 10

# Safety net against callbacks that keep rescheduling themselves for the same
# moment, which would make advance() step through time without ever moving on.
_MAX_ADVANCE_STEPS = 1000


class ClockedTestCase(unittest.IsolatedAsyncioTestCase):
    """
    IsolatedAsyncioTestCase with a clock that can be fast-forwarded

    `await self.advance(seconds)` moves the event loop's clock forward so that
    callbacks scheduled up to `seconds` in the future (e.g. by asyncio.sleep())
    are due immediately instead of after `seconds` real seconds.

    This replaces asynctest.ClockedTestCase.  The clock starts at 0 and only
    moves when advance() says so, so tests never wait for real time to pass.
    """

    _clock_offset = 0

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self._patch_clock()

    def _patch_clock(self):
        # Patching also happens on first use because subclasses define their own
        # asyncSetUp() without calling super().
        loop = asyncio.get_running_loop()
        if not getattr(loop, '_clock_is_patched', False):
            # The event loop looks up time() on the instance, so shadowing the
            # method is enough to move all scheduled callbacks closer to their
            # due time.  Like asynctest's clock, this one starts at 0 and only
            # moves when advance() says so.
            loop.time = lambda: self._clock_offset
            loop._clock_is_patched = True

    @staticmethod
    def _next_callback_time(loop):
        """When the next scheduled callback is due or None if there is none"""
        # asyncio has no public API for looking at scheduled callbacks, but
        # _scheduled has been part of BaseEventLoop since asyncio was added.
        # Complain instead of quietly skipping callbacks if it ever goes away:
        # advance() would still return, but nothing scheduled would ever run.
        try:
            scheduled = loop._scheduled
        except AttributeError:
            raise RuntimeError(f'{loop} has no _scheduled attribute - advance() needs another '
                               'way to find the next scheduled callback') from None
        return min((handle.when() for handle in scheduled if not handle.cancelled()),
                   default=None)

    async def _run_due_callbacks(self):
        for _ in range(_ADVANCE_ITERATIONS):
            await asyncio.sleep(0)

    async def advance(self, seconds):
        """Pretend `seconds` have passed and run any callbacks that are due"""
        if seconds < 0:
            raise ValueError('Cannot go back in time: {seconds}')
        self._patch_clock()
        loop = asyncio.get_running_loop()
        target = loop.time() + seconds

        # Move to each scheduled callback in turn instead of jumping straight to
        # `target`.  A callback that reschedules itself (e.g. a poller sleeping
        # between requests) must run once per interval, not once in total.
        for _ in range(_MAX_ADVANCE_STEPS):
            await self._run_due_callbacks()
            when = self._next_callback_time(loop)
            if when is None or when > target:
                break
            self._clock_offset += max(0, when - loop.time())

        self._clock_offset += max(0, target - loop.time())
        await self._run_due_callbacks()
