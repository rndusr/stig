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

"""Monkey patches that should be removed when they are resolved upstream"""

import urwid

# Workaround until this bug is resolved:
# https://github.com/urwid/urwid/pull/86
# https://github.com/urwid/urwid/issues/90
from distutils.version import LooseVersion
if LooseVersion(urwid.__version__) <= LooseVersion('1.3.1'):
    urwid.AsyncioEventLoop._idle_emulation_delay = 1/25


# Raise UnicodeDecodeError properly.
# https://github.com/urwid/urwid/pull/92
# https://github.com/urwid/urwid/pull/196
class AsyncioEventLoop_withfixedraise(urwid.AsyncioEventLoop):
    def _exception_handler(self, loop, context):
        exc = context.get('exception')
        if exc:
            loop.stop()
            if not isinstance(exc, urwid.ExitMainLoop):
                self._exc_info = exc
        else:
            loop.default_exception_handler(context)

    def run(self):
        """
        Start the event loop.  Exit the loop when any callback raises
        an exception.  If ExitMainLoop is raised, exit cleanly.
        """
        self._loop.set_exception_handler(self._exception_handler)
        self._loop.run_forever()
        if self._exc_info:
            raise self._exc_info

urwid.AsyncioEventLoop = AsyncioEventLoop_withfixedraise


# Tell ListBox to move to first/last item on 'home'/'end' keys.
class ListBox_with_home_end(urwid.ListBox):
    def keypress(self, size, key):
        key = super().keypress(size, key)
        if self.focus is not None:
            if key == 'home':
                self.focus_position = next(self.body.positions())
                self._invalidate()  # Don't know why this is needed?
                key = None
            elif key == 'end':
                self.focus_position = next(self.body.positions(reverse=True))
                self._invalidate()  # Don't know why this is needed?
                key = None
        return key

urwid.ListBox = ListBox_with_home_end
