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

from collections import abc
from functools import partial


class make_request():
    async def make_request(self, request_coro, polling_frenzy=False, quiet=False):
        """Awaits request coroutine and logs messages; returns response"""
        response = await request_coro
        utils.log_msgs(log, response.msgs, quiet)
        if response.success and polling_frenzy:
            self.polling_frenzy()
        return response


class select_torrents():
    tui = ExpectedResource

    def select_torrents(self, FILTER, allow_no_filter=True, discover_torrent=True):
        """Get TorrentFilter instance, focused torrent ID in a tuple or None

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

    def discover_torrent_ids(self, widget=None):
        """Return IDs of selected torrents

        Return tuple of torrent IDs that are either focused, marked or otherwise
        selected by the user.

        Return None if no torrents are selected.

        widget: Widget that is used to discover torrent IDs or None to use
                widget in focused tab

        Torrents are discovered by getting the:
            - `selected_torrent_ids` attribute in this command's object
              (e.g. set by the 'tab' command),
            - `marked` attribute of the focused tab's widget
              (e.g. TorrentListWidget), which must be an iterable of objects
              with an `id` attribute that returns a torrent ID
            - `focused_torrent_id` attribute of the focused tab's widget
              (e.g. FileListWidget).

        """
        # Get torrent IDs from attribute set by 'tab' command (this happens when
        # you run 'tab filelist' while a torrent is focused)
        if hasattr(self, 'selected_torrent_ids') and len(self.selected_torrent_ids) > 0:
            log.debug('Found torrents specified by tab command: %r', self.selected_torrent_ids)
            return self.selected_torrent_ids

        focused_widget = widget if widget is not None else self.tui.tabs.focus
        log.debug('Finding torrent in focused tab: %r', focused_widget)

        # Get torrent IDs from marked items
        if hasattr(focused_widget, 'marked'):
            tids = tuple(twidget.id for twidget in focused_widget.marked)
            if tids:
                log.debug('Found marked torrents: %r', tids)
                return tids

        # Get torrent ID from widget in focused tab (e.g. FileListWidget)
        if hasattr(focused_widget, 'focused_torrent_id'):
            tid = focused_widget.focused_torrent_id
            if tid is not None:
                log.debug('Found focused torrent: %r', tid)
                return (tid,)


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


class generate_tab_title():
    srvapi = ExpectedResource

    async def generate_tab_title(self, tfilter):
        if hasattr(self, 'title'):
            # Title is preset - we are not allowed to generate one
            return self.title
        elif isinstance(tfilter, abc.Sequence) and len(tfilter) == 1:
            # tfilter is a torrent ID - resolve it to a name for the title
            response = await self.srvapi.torrent.torrents(tfilter, keys=('name',))
            if response.success:
                return response.torrents[0]['name']
            else:
                return 'Could not find torrent with ID %s' % tfilter[0]
        else:
            return None


class create_list_widget():
    tui    = ExpectedResource
    srvapi = ExpectedResource

    def create_list_widget(self, list_cls, *args, theme_name, markable_items=False, **kwargs):
        # Helper function that creates a tab title widget
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
