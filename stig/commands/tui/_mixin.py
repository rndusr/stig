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

from .. import (ExpectedResource, CmdError)
from .. import utils
from ._common import make_tab_title_widget


class make_request():
    async def make_request(self, request_coro, polling_frenzy=False, quiet=False):
        """Awaits request coroutine and logs messages; returns response"""
        response = await request_coro
        utils.log_msgs(self, response, quiet)
        if response.success and polling_frenzy:
            self.polling_frenzy()
        return response


class ask_yes_no():
    tui     = ExpectedResource
    aioloop = ExpectedResource

    ANSWERS = {'y': True, 'n': False,
               'Y': True, 'N': False}

    async def ask_yes_no(self, question, yes=None, no=None, after=None):
        """
        Ask user a yes/no question

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

    def select_torrents(self, FILTER, allow_no_filter=True, discover_torrent=True, prefer_focused=False):
        """
        Get TorrentFilter instance or None

        If `FILTER` evaluates to True, it is passed to TorrentFilter and the
        resulting object is returned.

        If `FILTER` evaluates to False, the result of `discover_torrent_ids` is
        returned if `discover_torrent` evaluates to True.  `prefer_focused` is
        forwarded to `discover_torrent_ids`.  If `discover_torrent` evaluates to
        False, None is returned if `allow_no_filter` evaluates to True,
        otherwise a ValueError is raised.
        """
        if FILTER:
            from ...client import TorrentFilter
            return TorrentFilter(FILTER)
        else:
            if discover_torrent:
                tids = self.discover_torrent_ids(prefer_focused=prefer_focused)
                if tids is not None:
                    return self.ids2tfilter(tids)

            if allow_no_filter:
                return None

            else:
                raise ValueError('No torrent specified')

    def discover_torrent_ids(self, prefer_focused=False):
        """
        Auto-detect which torrents are currently selected by the user

        Torrents are selected by marking them or by focusing them.  If
        `prefer_focused` evaluates to True, the focused torrent ID is returned,
        if possible, before looking for marks.  Otherwise, the focused torrent
        ID is only returned if there are no marked torrents.

        If any torrents are found, return a tuple of torrent IDs, otherwise
        None.
        """
        def get_marked():
            tids = self.get_marked_torrent_ids()
            if tids:
                log.debug('Found marked torrents: %r', tids)
                return tids

        def get_focused():
            tid = self.get_focused_torrent_id()
            if tid:
                log.debug('Found focused torrent: %r', tid)
                return (tid,)

        if prefer_focused:
            return get_focused() or get_marked()
        else:
            return get_marked() or get_focused()

    def get_marked_torrent_ids(self):
        """
        Return IDs of marked items in the current or previous tab

        This relies on the widget having a `marked` attribute.
        """
        widget = self._get_current_or_previous_tab()
        if hasattr(widget, 'marked'):
            tids = tuple(twidget.torrent_id for twidget in widget.marked)
            if tids:
                return set(tids)

    def get_focused_torrent_id(self):
        """
        Return torrent ID of focused item in the current or previous tab

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

    @staticmethod
    def ids2tfilter(ids):
        """Turn an iterable of ids into a TorrentFilter instance"""
        if all(isinstance(x, int) for x in ids):
            from ...client import TorrentFilter
            return TorrentFilter('|'.join(('id=%d' % id for id in ids)))
        else:
            raise RuntimeError('Not a list of IDs: %r' % (ids,))


class select_files():
    tui = ExpectedResource

    def get_focused_path_in_torrent(self):
        """Return relative path of focused file or directory in file lists"""
        focused_widget = self.tui.tabs.focus
        if hasattr(focused_widget, 'focused_file_ids'):
            widget = focused_widget.focused_widget
            return widget.data['path-relative']

    def select_files(self, FILTER, allow_no_filter=True, discover_file=True):
        """
        Get TorrentFileFilter instance, focused/marked file IDs or None

        If `FILTER` evaluates to True, it is passed to TorrentFileFilter and the
        resulting object is returned.

        If `FILTER` evaluates to False and `discover_file` evaluates to True,
        a tuple of (<torrent ID>, <file ID>) tuples is returned.  If
        `discover_file` evaluates to False, None is returned if
        `allow_no_filter` evaluates to True, else a ValueError is raised.

        Files are discovered by getting the `focused_file_ids` of the focused
        tab's widget.
        """
        if FILTER:
            from ...client import TorrentFileFilter
            return TorrentFileFilter(FILTER)
        else:
            if discover_file:
                fids = self._find_file_ids()
                if fids:
                    log.debug('Found file IDs: %r', fids)
                    return fids
            if allow_no_filter:
                return None
            else:
                raise ValueError('No torrent file specified')

    def _find_file_ids(self):
        focused_widget = self.tui.tabs.focus
        # Get marked file IDs
        if hasattr(focused_widget, 'marked'):
            fids = tuple(fwidget.id for fwidget in focused_widget.marked)
            if fids:
                log.debug('Found marked files: %r', fids)
                return fids

        # Get focused file IDs (if directory is focused, include all files in it)
        if hasattr(focused_widget, 'focused_file_ids'):
            fids = tuple(focused_widget.focused_file_ids)
            if fids:
                log.debug('Found focused files: %r', fids)
                return fids

        return ()


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


import os
import collections
class placeholders(make_request):
    srvapi = ExpectedResource
    tui = ExpectedResource

    class _Placeholder():
        def __init__(self, name, needed_keys, description, modifier=None):
            self.name = name
            self.needed_keys = needed_keys
            self.description = description
            self.modifier = modifier

        def evaluate(self, data):
            if self.modifier:
                return str(self.modifier(data))
            else:
                # assert len(self.needed_keys) == 1
                return str(data[self.needed_keys[0]])

    _placeholder_specs = {
        # {location}/{name} is absolute path to torrent file/directory
        'torrent': (_Placeholder('id', needed_keys=('id',),
                                 description='Torrent ID'),
                    _Placeholder('name', needed_keys=('name', 'comment'),
                                 description='Torrent name'),
                    _Placeholder('location', needed_keys=('path',),
                                 description='Download path (absolute)')),

        # {location}/{torrentname}/{path} is absolute path to file/directory
        # inside a torrent
        'file': (_Placeholder('id', needed_keys=('tid',),
                              description='Torrent ID'),
                 _Placeholder('name', needed_keys=('name',),
                              description='File or directory name without path'),
                 _Placeholder('location', needed_keys=('location',),
                              description='Torrent\'s absolute download path'),
                 _Placeholder('torrentname', needed_keys=('path-relative',),
                              description='Torrent name',
                              modifier=lambda data: data['path-relative'].split('/', maxsplit=1)[0]),
                 _Placeholder('path', needed_keys=('path-relative',),
                              description='Relative path within the torrent, including name',
                              modifier=lambda data: os.sep.join(data['path-relative'].split('/')[1:])))
    }

    HELP = (('Placeholders are evaluated to values of the focused list item.  '
             'Their format is "{{NAME}}" where valid values for NAME are as follows:'),
            '',
            '\tIn torrent lists:') \
            + tuple('\t\t%s \t- %s' % (ph.name, ph.description) for ph in _placeholder_specs['torrent']) \
            + ('',
             '\tIn file lists:') \
            + tuple('\t\t%s \t- %s' % (ph.name, ph.description) for ph in _placeholder_specs['file']) \
            + ('',
               'To get a literal "{{", escape it with "\\".  "}}" doesn\'t need '
               'to be escaped.  Note that you must escape the "\\" itself unless '
               'it is quoted because it escapes arbitrary characters.')

    _NOT_SUPPORTED_ERROR = 'Placeholders are not supported in the current tab'
    _RESOLVE_ERROR = 'Unable to resolve placeholders: %s'

    import re
    _placeholder_split_regex = re.compile(r'(?<!\\)(\{.+?\})')
    async def parse_placeholders(self, *args):
        parsed_args = []
        for i,arg in enumerate(args):
            next_arg = []
            for part in self._placeholder_split_regex.split(arg):
                log.debug('part: %r', part)
                if not part:
                    continue
                elif part.endswith('}'):
                    if part.startswith('{'):
                        next_arg.append(await self._resolve_placeholder(part[1:-1]))
                    else:
                        next_arg.append(part)
                else:
                    next_arg.append(part)

                # Unescape escaped curly brackets
                next_arg[-1] = next_arg[-1].replace('\\{', '{').replace('\\}', '}')

            parsed_args.append(''.join(next_arg))
        return parsed_args

    async def _resolve_placeholder(self, key):
        placeholders = await self._get_placeholder_map()
        try:
            return placeholders[key]
        except KeyError:
            raise CmdError('Unknown placeholder: %r' % key)

    async def _get_placeholder_map(self):
        if not hasattr(self, '_placeholders'):
            from ...tui.views.torrent_list import TorrentListWidget
            from ...tui.views.file_list import FileListWidget

            focused_list = self.tui.tabs.focus
            if focused_list is None:
                raise CmdError(self._RESOLVE_ERROR % 'No tab opened')
            elif not isinstance(focused_list, (TorrentListWidget, FileListWidget)):
                raise CmdError(self._NOT_SUPPORTED_ERROR)
            elif focused_list.focused_widget is None:
                raise CmdError(self._RESOLVE_ERROR % 'Current tab is empty')
            else:
                focused_item = focused_list.focused_widget.base_widget
                torrent_id = focused_item.torrent_id

                if isinstance(focused_list, TorrentListWidget):
                    phspecs = self._placeholder_specs['torrent']
                    needed_keys = sum((phspec.needed_keys for phspec in phspecs), ())
                    if all(key in focused_item.data for key in needed_keys):
                        # Cached Torrent object has everything we need
                        data = focused_item.data
                    else:
                        # Fetch data we need for placeholders
                        data = await self._fetch_torrent_data(torrent_id, needed_keys)
                elif isinstance(focused_list, FileListWidget):
                    phspecs = self._placeholder_specs['file']
                    # We don't need to fetch data because the file list item
                    # already has everything
                    data = focused_item.data

                else:
                    raise CmdError(self._NOT_SUPPORTED_ERROR)

                self._placeholders = {phspec.name:phspec.evaluate(data)
                                      for phspec in phspecs}
                log.debug('Placeholders: %r', self._placeholders)
        return self._placeholders

    async def _fetch_torrent_data(self, torrent_id, keys):
        log.debug('Fetching fresh Torrent #%d with keys: %r', torrent_id, keys)
        # Request new torrent because we can't be sure the wanted key
        # exists in widget.data
        request = self.srvapi.torrent.torrents((torrent_id,), keys=keys)
        response = await self.make_request(request, quiet=True)
        if not response.success:
            raise CmdError()
        else:
            return response.torrents[0]
