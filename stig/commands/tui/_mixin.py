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

import asyncio
import functools
import os

from .. import CmdError, utils
from ... import client, objects
from ._common import make_tab_title_widget

from ...logging import make_logger  # isort:skip
log = make_logger(__name__)


def _deep_getattr(obj, *attrs):
    for attr in attrs:
        obj = getattr(obj, attr, None)
        if obj is None:
            break
    return obj


class make_request():
    async def make_request(self, request_coro, polling_frenzy=False, quiet=False):
        """
        Awaits `request_coro` and optionally logs messages to `process`

        If `polling_frenzy` evaluates to True and the request succeeded, the
        `polling_frenzy` method is called.

        Return the response object returned by `request_coro`.
        """
        response = await request_coro
        utils.log_msgs(self, response, quiet)
        if response.success and polling_frenzy:
            self.polling_frenzy()
        return response


class ask_yes_no():
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
        from ...tui import tuiobjects

        def run_func_or_coro(func_or_coro):
            if asyncio.iscoroutinefunction(func_or_coro):
                asyncio.ensure_future(func_or_coro())
            elif asyncio.iscoroutine(func_or_coro):
                asyncio.ensure_future(func_or_coro)
            elif func_or_coro is not None:
                func_or_coro()

        class YesNoEditWidget(tuiobjects.urwid.Edit):
            def keypress(slf, size, key):
                answer = self.ANSWERS.get(key, None)
                if answer is not None:
                    tuiobjects.widgets.remove('yesnoprompt')
                    tuiobjects.widgets.focus_name = focus_name
                    if answer:
                        run_func_or_coro(yes)
                    else:
                        run_func_or_coro(no)
                    run_func_or_coro(after)
                return None

        # Remember focused widget
        focus_name = tuiobjects.widgets.focus_name

        widget = tuiobjects.urwid.AttrMap(YesNoEditWidget(question + ' [y|n] '), 'prompt')
        pos = tuiobjects.widgets.get_position('main') + 1
        tuiobjects.widgets.add(widget=widget, name='yesnoprompt', removable=True,
                               options='pack', position=pos)


class select_torrents():
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
            return client.TorrentFilter(FILTER)
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

    @classmethod
    def get_focused_torrent_id(cls):
        """
        Return torrent ID of focused item in the current or previous tab

        This relies on the current widget having a `focused_torrent_id`
        attribute.
        """
        widget = cls._get_current_or_previous_tab()
        if hasattr(widget, 'focused_torrent_id'):
            tid = widget.focused_torrent_id
            if tid is not None:
                return tid


    @classmethod
    def get_focused_item_data(cls):
        """
        Return 'torrent', 'file' or 'directory' depending on what is currently
        focused
        """
        from ...tui.tuiobjects import tabs
        return _deep_getattr(tabs, 'focus', 'focused_widget', 'data')

    @classmethod
    def get_focused_item_type(cls):
        """
        Return 'torrent', 'file' or 'directory' depending on what is currently
        focused
        """
        from ...tui.tuiobjects import tabs
        focused_widget = _deep_getattr(tabs, 'focus', 'focused_widget')
        focused_data = _deep_getattr(focused_widget, 'data')

        if isinstance(focused_data, client.Torrent):
            return 'torrent'
        from ...views.file import TorrentFileDirectory
        if isinstance(focused_data, TorrentFileDirectory):
            return 'directory'
        if isinstance(focused_data, client.TorrentFile):
            return 'file'
        from ...tui.views import SettingItemWidget
        if isinstance(focused_widget, SettingItemWidget):
            return 'setting'

    @classmethod
    def _get_current_or_previous_tab(cls):
        """Return currently focused tab content if not empty, the previous one or None"""
        from ...tui.tuiobjects import tabs
        widget = tabs.focus
        if widget is not None:
            return widget
        else:
            return tabs.prev_focus

    @staticmethod
    def ids2tfilter(ids):
        """Turn an iterable of ids into a TorrentFilter instance"""
        if all(isinstance(x, int) for x in ids):
            return client.TorrentFilter('|'.join(('id=%d' % id for id in ids)))
        else:
            raise RuntimeError('Not a list of IDs: %r' % (ids,))


class select_files():
    def get_relative_path_from_focused(self, unique=False):
        """
        When viewing a file list, return '<TORRENT NAME>/<RELATIVE PATH>' of the
        focused file or directory, or None when viewing anything else

        If `unique` evaluates to True, '<TORRENT NAME>' is replaced with
        'id=<TORRENT ID>' to make this path unique to this torrent even if there
        are multiple torrents with the same name.
        """
        from ...tui.tuiobjects import tabs
        focused_widget = tabs.focus
        if hasattr(focused_widget, 'focused_file_ids'):
            data = focused_widget.focused_widget.data
            path = data['path-relative']
            if unique:
                # Remove torrent name from path
                first_slash = path.find('/')
                if first_slash > -1:
                    # Multi-file torrent
                    return 'id=%d/%s' % (data['tid'], path[first_slash:].strip('/'))
                else:
                    # Single-file torrent
                    return 'id=%d' % (data['tid'],)
            else:
                return path

    def select_files(self, FILTER, allow_no_filter=True, discover_file=True):
        """
        Get FileFilter instance, focused/marked file IDs or None

        If `FILTER` evaluates to True, it is passed to FileFilter and the
        resulting object is returned.

        If `FILTER` evaluates to False and `discover_file` evaluates to True,
        a tuple of (<torrent ID>, <file ID>) tuples is returned.  If
        `discover_file` evaluates to False, None is returned if
        `allow_no_filter` evaluates to True, else a ValueError is raised.

        Files are discovered by getting the `focused_file_ids` of the focused
        tab's widget.
        """
        if FILTER:
            return client.FileFilter(FILTER)
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
        from ...tui.tuiobjects import tabs
        focused_widget = tabs.focus
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
    def create_list_widget(self, list_cls, *args, theme_name, markable_items=False, **kwargs):
        # Helper function that creates a tab title widget
        make_titlew = functools.partial(
            make_tab_title_widget,
            attr_unfocused='tabs.%s.unfocused' % theme_name,
            attr_focused='tabs.%s.focused' % theme_name)

        # If tab is specified by the user, pass it on to the list widget
        if hasattr(self, 'title'):
            kwargs['title'] = self.title

        # Create list widget
        log.debug('Creating %s(%s, %s)', list_cls.__name__, args, kwargs)
        from ...tui.tuiobjects import keymap
        listw = list_cls(objects.srvapi, keymap, *args, **kwargs)

        # Add list to tabs
        from ...tui.tuiobjects import tabs
        tabid = tabs.load(make_titlew(listw.title), listw)
        tabs.set_info(command=self.command)

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
                tabs.set_title(make_titlew(text, count), position=tabid)
            except IndexError:
                pass
        listw.title_updater = set_tab_title

        # Set a temporary title until the tab has finished loading its content
        # and the title_updater is called with the actual title
        tabs.set_title(make_titlew('Loading...', ''), position=tabid)


# TODO: Take a callable that return True to stop and False to keep polling rapidly.
#       `duration` should be a timeout to prevent polling rapidly forever.
class polling_frenzy():
    @classmethod
    def polling_frenzy(cls, duration=2, short_interval=0.5):
        """Reduce polling interval to `short_interval` for `duration` seconds"""
        if objects.srvapi.interval > 1:
            async def coro():
                log.debug('Setting poll interval to %s for %s seconds', short_interval, duration)
                orig_interval = objects.srvapi.interval
                objects.srvapi.interval = short_interval
                await asyncio.sleep(duration)
                objects.srvapi.interval = orig_interval
                log.debug('Interval restored to %s', objects.srvapi.interval)
            asyncio.ensure_future(coro())


class placeholders(make_request):
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
                              description='Name of the torrent',
                              modifier=lambda data: data['path-relative'].split('/', maxsplit=1)[0]),
                 _Placeholder('path', needed_keys=('path-relative',),
                              description='Relative path within the torrent, including name',
                              modifier=lambda data: os.sep.join(data['path-relative'].split('/')[1:])))
    }

    HELP = ((('Placeholders are evaluated to values of the focused list item.  '
              'Their format is "{{NAME}}" where valid values for NAME are as follows:'),
             '',
             '\tIn torrent lists:')
            + tuple('\t\t%s \t- %s' % (ph.name, ph.description) for ph in _placeholder_specs['torrent'])
            + ('', '\tIn file lists:')
            + tuple('\t\t%s \t- %s' % (ph.name, ph.description) for ph in _placeholder_specs['file'])
            + ('',
               'To get a literal "{{", escape it with "\\".  "}}" doesn\'t need '
               'to be escaped.  Note that you must escape the "\\" itself unless '
               'it is quoted because it escapes arbitrary characters.'))

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
            from ...tui.views import TorrentListWidget, FileListWidget
            from ...tui.tuiobjects import tabs
            focused_list = tabs.focus
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
        request = objects.srvapi.torrent.torrents((torrent_id,), keys=keys)
        response = await self.make_request(request, quiet=True)
        if not response.success:
            raise CmdError()
        else:
            return response.torrents[0]
