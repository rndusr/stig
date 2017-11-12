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

"""Mixin classes for TUI commands"""

from ...logging import make_logger
log = make_logger(__name__)

from .. import ExpectedResource
from .. import utils
from ._common import make_tab_title_widget


class make_request():
    async def make_request(self, request_coro, polling_frenzy=False, quiet=False):
        """Awaits request coroutine and logs messages; returns response"""
        response = await request_coro
        utils.log_msgs(log, response.msgs, quiet)
        if response.success and polling_frenzy:
            self.polling_frenzy()
        return response


class user_confirmation():
    tui     = ExpectedResource
    aioloop = ExpectedResource

    ANSWERS = {'y': True, 'n': False,
               'Y': True, 'N': False}

    async def ask_yes_no(self, question, yes=None, no=None, after=None):
        """Ask user a yes/no question

        The `yes` and `no` arguments are callbacks (or None) that are called
        depending on the user's answer. `after` is called after the user
        answered and after `yes` or `no` has been called.

        Callbacks may be normal functions, coroutine functions or
        coroutines. They don't get any arguments and their return value is
        ignored.
        """
        tui = self.tui

        import asyncio
        def run_func_or_coro(func_or_coro):
            if asyncio.iscoroutinefunction(func_or_coro):
                self.aioloop.create_task(func_or_coro())
            elif asyncio.iscoroutine(func_or_coro):
                self.aioloop.create_task(func_or_coro)
            elif func_or_coro is not None:
                func_or_coro()

        class YesNoEditWidget(tui.urwid.Edit):
            def keypress(slf, size, key):
                answer = self.ANSWERS.get(key, None)
                if answer is not None:
                    tui.widgets.remove('yesnoprompt')
                    tui.widgets.focus_name = focus_name
                    if answer:
                        run_func_or_coro(yes)
                    else:
                        run_func_or_coro(no)
                    run_func_or_coro(after)
                return None

        # Remember focused widget
        focus_name = tui.widgets.focus_name

        widget = tui.urwid.AttrMap(YesNoEditWidget(question + ' [y|n] '), 'prompt')
        pos = tui.widgets.get_position('main') + 1
        tui.widgets.add(widget=widget, name='yesnoprompt', removable=True,
                        options='pack', position=pos)


class select_torrents():
    tui = ExpectedResource

    def select_torrents(self, FILTER, allow_no_filter=True, discover_torrent=True):
        """Get TorrentFilter instance or focused/marked torrent IDs

        If `FILTER` evaluates to True, it is passed to TorrentFilter and the
        resulting object is returned.

        If `FILTER` evaluates to False, the result of `discover_torrent_ids` is
        returned if `discover_torrent` evaluates to True. Otherwise, None is
        returned if `allow_no_filter` evaluates to True, else a ValueError is
        raised.
        """
        if FILTER:
            from ...client import TorrentFilter
            return TorrentFilter(FILTER)
        else:
            if discover_torrent:
                tids = self.discover_torrent_ids()
                if tids is not None:
                    return tids

            if allow_no_filter:
                return None

            else:
                raise ValueError('No torrent specified')

    def discover_torrent_ids(self):
        """Auto-detect which torrents are currently selected by the user

        Try `get_marked_torrent_ids` first, then `get_focused_torrent_id`.

        If any torrents are found, return a tuple of torrent IDs, otherwise
        None.
        """
        tids = self.get_marked_torrent_ids()
        if tids:
            return tids
        tid = self.get_focused_torrent_id()
        if tid:
            return (tid,)

    def get_marked_torrent_ids(self):
        """Return IDs of marked items in the current or previous tab

        This relies on the widget having a `marked` attribute.
        """
        widget = self._get_current_or_previous_tab()
        if hasattr(widget, 'marked'):
            tids = tuple(twidget.id for twidget in widget.marked)
            if tids:
                return tids

    def get_focused_torrent_id(self):
        """Return torrent ID of focused item in the current or previous tab

        This relies on the widget having a `focused_torrent_id` attribute.
        """
        widget = self._get_current_or_previous_tab()
        if hasattr(widget, 'focused_torrent_id'):
            tid = widget.focused_torrent_id
            if tid is not None:
                return tid

    def _get_current_or_previous_tab(self):
        """Return currently focused tab content if not empty, or the previous one"""
        widget = self.tui.tabs.focus
        if widget is not None:
            return widget

        if hasattr(self, 'previous_tab_id'):
            try:
                widget = self.tui.tabs.get_content(self.previous_tab_id)
            except IndexError:
                pass
            else:
                return widget


class select_files():
    tui = ExpectedResource

    def select_files(self, FILTER, allow_no_filter=True, discover_file=True):
        """Get TorrentFileFilter instance, focused file ID or None

        If `FILTER` evaluates to True, it is passed to TorrentFileFilter and
        the resulting object is returned.

        If `FILTER` evaluates to False and `discover_file` evaluates to True,
        the file ID (or IDs) are returned in a tuple if possible. Otherwise,
        None is returned if `allow_no_filter` evaluates to True, else a
        ValueError is raised.

        File are discovered by getting the `focused_file_id` of the focused
        tab's widget.
        """
        if FILTER:
            from ...client import TorrentFileFilter
            return TorrentFileFilter(FILTER)
        else:
            if discover_file:
                fids = self._find_file_ids()
                if fids is not None:
                    return fids
            if allow_no_filter:
                return None
            else:
                raise ValueError('No torrent file specified')

    def _find_file_ids(self):
        focused_widget = self.tui.tabs.focus

        if hasattr(focused_widget, 'marked'):
            tfids = tuple((fwidget.torrent_id, fwidget.file_id)
                          for fwidget in focused_widget.marked
                          if isinstance(fwidget.file_id, int))
            if tfids:
                return tfids

        # Get torrent ID from widget in focused tab
        if hasattr(focused_widget, 'focused_file_ids') and \
           focused_widget.focused_file_ids is not None:
            return tuple((focused_widget.focused_torrent_id, fid)
                         for fid in focused_widget.focused_file_ids)


class create_list_widget():
    tui    = ExpectedResource
    srvapi = ExpectedResource

    def create_list_widget(self, list_cls, *args, theme_name, markable_items=False, **kwargs):
        # Helper function that creates a tab title widget
        from functools import partial
        make_titlew = partial(make_tab_title_widget,
                              attr_unfocused='tabs.%s.unfocused' % theme_name,
                              attr_focused='tabs.%s.focused' % theme_name)

        # If tab is specified by the user, pass it on to the list widget
        if hasattr(self, 'title'):
            kwargs['title'] = self.title

        # Create list widget
        log.debug('Creating %s(%s, %s)', list_cls.__name__, args, kwargs)
        listw = list_cls(self.srvapi, self.tui.keymap, *args, **kwargs)

        # Add list to tabs
        tabid = self.tui.tabs.load(make_titlew(listw.title), listw)

        # If list items are markable, automatically add the 'marked' column
        if markable_items:
            columns = listw.columns
            if 'marked' not in columns:
                listw.columns = ('marked',) + columns

        # Tell list widget how to change the tab title
        def set_tab_title(text, count):
            # There is a race condition that can result in the list widget
            # setting a new title for a tab that has already been removed, which
            # raises an IndexError here.
            try:
                self.tui.tabs.set_title(make_titlew(text, count), position=tabid)
            except IndexError:
                pass
        listw.title_updater = set_tab_title

        # Set a temporary title until the tab has finished loading its content
        # and the title_updater is called with the actual title
        self.tui.tabs.set_title(make_titlew('Loading...', ''), position=tabid)


class polling_frenzy():
    aioloop = ExpectedResource
    srvapi  = ExpectedResource

    def polling_frenzy(self, duration=2, short_interval=0.5):
        """Reduce polling interval to `short_interval` for `duration` seconds"""
        srvapi = self.srvapi
        if srvapi.interval > 1:
            import asyncio
            async def coro():
                log.debug('Setting poll interval to %s for %s seconds', short_interval, duration)
                orig_interval = srvapi.interval
                srvapi.interval = short_interval
                await asyncio.sleep(duration, loop=self.aioloop)
                srvapi.interval = orig_interval
                log.debug('Interval restored to %s', srvapi.interval)
            self.aioloop.create_task(coro())
