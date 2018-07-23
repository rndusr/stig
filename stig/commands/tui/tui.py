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

"""Commands that work exclusively in the TUI"""

from ...logging import make_logger
log = make_logger(__name__)

from .. import (InitCommand, CmdError, ExpectedResource)
from . import _mixin as mixin
from ._common import make_tab_title_widget

import shlex
from functools import partial


# Import tui.main module only on demand
def _get_keymap_contexts():
    from ...tui.main import keymap
    return tuple(keymap.contexts)


class BindCmd(metaclass=InitCommand):
    name = 'bind'
    provides = {'tui'}
    category = 'tui'
    description = 'Bind keys to commands or other keys'
    usage = ('bind [<OPTIONS>] <KEY> <ACTION>',)
    examples = ('bind --context tabs alt-[ tab --focus left',
                'bind --context tabs alt-] tab --focus right',
                'bind --context torrent alt-! start --force',
                'bind ctrl-a tab ls active',
                "bind 'd .' delete",
                "bind 'd+!' delete --delete-files",
                'bind u <up>',
                'bind d <down>')
    argspecs = (
        { 'names': ('--context','-c'),
          'description': 'Where KEY is grabbed (see CONTEXTS section)' },
        { 'names': ('KEY',),
          'description': 'One or more keys or key combinations (see KEYS section)' },
        { 'names': ('ACTION',), 'nargs': 'REMAINDER',
          'description': ("Any command or '<KEY>' (including the brackets) "
                          'to translate one key to another') },
    )

    def __create_CONTEXTS_section():
        lines = [
            ('Keys are mapped in contexts.  With no context given, the default '
             'context is used.  The default context only gets the key if no '
             'other context wants it.  The same key can be mapped to different '
             'actions in different contexts.'),
            '',
            'Available contexts are: ' +
              ', '.join('%s' % context for context in _get_keymap_contexts()),
            '',
            'EXAMPLE',
            '\tbind --context torrent ctrl-t start',
            '\tbind --context tabs ctrl-t tab',
            '\tbind ctrl-t <left>',
            '',
            ('\tWhen focusing a torrent, <ctrl-t> starts the focused torrent.  '
             'If focus is not on a torrent but still on a tab (e.g. when reading '
             'documentation) a new tab is opened.  Otherwise (e.g. focus is on the '
             'command prompt), <ctrl-t> does the same as <left>.'),
        ]
        return lines

    more_sections = {
        'CONTEXTS': __create_CONTEXTS_section,
        'KEYS': (
            'Single-character keys are specified as themselves (e.g. h, X, 5, !, þ, ¥, etc).',
            '',
            ('Special key names are enter, space, tab, backspace, insert, delete, home, end, '
             'up, down, left, right, pgup, pgdn and f1-12.'),
            '',
            ("The modifiers 'ctrl', 'alt' and 'shift' are separated with '-' from the key "
             "(e.g. alt-i, shift-delete, ctrl-a).  shift-x is identical to X."),
            '',
            ("Chained keys are sparated by single spaces (' ') or pluses ('+') and must be "
             "given as a single argument."),
        )
    }

    tui = ExpectedResource

    def run(self, context, KEY, ACTION):
        keymap = self.tui.keymap

        key = KEY
        if len(ACTION) == 1 and ACTION[0][0] == '<' and ACTION[0][-1] == '>':
            # ACTION is another key (e.g. 'j' -> 'down')
            action = keymap.mkkey(ACTION[0])
        else:
            action = ' '.join(shlex.quote(x) for x in ACTION)

        if context is None:
            context = keymap.DEFAULT_CONTEXT
        elif context not in _get_keymap_contexts():
            raise CmdError('Invalid context: %r' % (context,))

        try:
            keymap.bind(key, action, context=context)
        except ValueError as e:
            raise CmdError(e)


class UnbindCmd(metaclass=InitCommand):
    name = 'unbind'
    provides = {'tui'}
    category = 'tui'
    description = 'Unbind keys so pressing them has no effect'
    usage = ('unbind [<OPTIONS>] <KEY> <KEY> ...',)
    examples = ('unbind --context main ctrl-l',
                'unbind q')
    argspecs = (
        { 'names': ('--context','-c'),
          'description': 'Where KEY is grabbed (see "bind" command)' },
        { 'names': ('--all','-a'), 'action': 'store_true',
          'description': 'Remove all existing keybindings, including defaults' },
        { 'names': ('KEY',), 'nargs': 'REMAINDER',
          'description': 'Keys or key combinations (see "bind" command)' },
    )

    tui = ExpectedResource

    def run(self, context, all, KEY):
        keymap = self.tui.keymap

        if all:
            keymap.clear()

        if context is None:
            context = keymap.DEFAULT_CONTEXT
        elif context not in _get_keymap_contexts():
            raise CmdError('Invalid context: %r' % (context,))

        success = True
        for key in KEY:
            try:
                keymap.unbind(key, context=context)
            except ValueError as e:
                self.error(e)
                success = False
            else:
                success = success and True
        if not success:
            raise CmdError()


class InteractiveCmd(metaclass=InitCommand):
    name = 'interactive'
    provides = {'tui'}
    category = 'tui'
    description = 'Complete partial command with user input from a dialog'
    usage = ('interactive [<OPTIONS>] <COMMAND>',)
    examples = ('tab ls & interactive -c "tab --close --focus left" search %s',
                'tab ls & interactive -a "mark --all & start" -x "tab --close --focus left" search "%s & stopped"',)
    argspecs = (
        { 'names': ('--on-cancel', '-c'), 'metavar': 'CANCEL COMMAND',
          'description': 'Command to run when the dialog is aborted with escape' },
        { 'names': ('--on-accept', '-a'), 'metavar': 'ACCEPT COMMAND',
          'description': 'Command to run when the dialog is accepted with enter' },
        { 'names': ('--on-close', '-x'), 'metavar': 'CLOSE COMMAND',
          'description': 'Command to run after the dialog is closed either way' },
        { 'names': ('COMMAND',), 'nargs': '+',
          'description': ('The command to run when the user types something.  The first occurence '
                          'of "%s" in COMMAND is replaced with the user input.  If "%s" doesn\'t occur, '
                          'user input is appended to COMMAND.') },
    )
    tui = ExpectedResource
    cmdmgr = ExpectedResource

    _EDIT_WIDGET_NAME = 'interactive_prompt'
    _PLACEHOLDER = '%s'

    def run(self, on_cancel, on_accept, on_close, COMMAND):
        from ...tui.cli import CLIEditWidget
        import urwid

        command_skeleton = ' '.join(shlex.quote(arg) for arg in COMMAND)
        self._cancel_cmd = on_cancel
        self._accept_cmd = on_accept
        self._close_cmd = on_close

        log.debug('cmd: %r', command_skeleton)
        log.debug('cancel_cmd: %r', self._cancel_cmd)
        log.debug('accept_cmd: %r', self._accept_cmd)
        log.debug('close_cmd: %r', self._close_cmd)

        if self._PLACEHOLDER in command_skeleton:
            self._before_edit, _, self._after_edit = command_skeleton.partition(self._PLACEHOLDER)
        else:
            self._before_edit = command_skeleton + ' '
            self._after_edit = ''

        self._before_edit_widget = urwid.Text(self._before_edit)
        self._edit_widget = CLIEditWidget(on_change=self._change_callback,
                                          on_accept=self._accept_callback,
                                          on_cancel=self._cancel_callback)
        self._after_edit_widget = urwid.Text(self._after_edit)

        self._columns = urwid.Columns([('pack', self._before_edit_widget),
                                       (25, urwid.AttrMap(self._edit_widget, 'prompt')),
                                       ('pack', self._after_edit_widget)])
        self.tui.widgets.add(name=self._EDIT_WIDGET_NAME,
                             widget=urwid.AttrMap(self._columns, 'cli'),
                             position=self.tui.widgets.get_position('cli'),
                             removable=True,
                             options='pack')

    def _change_callback(self, widget):
        cmd = ''.join((self._before_edit, widget.edit_text, self._after_edit))
        self.cmdmgr.run_task(cmd)

    def _accept_callback(self, widget):
        if self._accept_cmd is not None:
            self.cmdmgr.run_task(self._accept_cmd)
        self._close()

    def _cancel_callback(self, widget):
        if self._cancel_cmd is not None:
            self.cmdmgr.run_task(self._cancel_cmd)
        self._close()

    def _close(self):
        self.tui.widgets.remove(self._EDIT_WIDGET_NAME)
        self.tui.widgets.focus_name = 'main'
        if self._close_cmd is not None:
            self.cmdmgr.run_task(self._close_cmd)


class MarkCmd(metaclass=InitCommand):
    name = 'mark'
    provides = {'tui'}
    category = 'tui'
    description = 'Select torrents or files for an action'
    usage = ('mark [<OPTIONS>]',)
    argspecs = (
        { 'names': ('--focus-next','-n'), 'action': 'store_true',
          'description': 'Move focus forward after marking or toggling' },
        { 'names': ('--toggle','-t'), 'action': 'store_true',
          'description': 'Mark if unmarked, unmark if marked' },
        { 'names': ('--all','-a'), 'action': 'store_true',
          'description': 'Mark or toggle all items' },
    )
    more_sections = {
        'NOTES': (('The column "marked" must be in the "columns.*" settings. Otherwise '
                   'marked list items are indistinguishable from unmarked ones.'),
                  '',
                  ('The character that is displayed in the "marked" column is '
                   'specified by the settings "tui.marked.on" and "tui.marked.off".')),
    }

    tui = ExpectedResource

    def run(self, focus_next, toggle, all):
        widget = self.tui.tabs.focus
        if not widget.has_marked_column:
            raise CmdError('Nothing to mark here.')
        else:
            widget.mark(toggle=toggle, all=all)
            if focus_next:
                widget.focus_position += 1


class UnmarkCmd(metaclass=InitCommand):
    name = 'unmark'
    provides = {'tui'}
    category = 'tui'
    description = 'Deselect torrents or files for an action'
    usage = ('unmark [<OPTIONS>]',)
    argspecs = (
        { 'names': ('--focus-next','-n'), 'action': 'store_true',
          'description': 'Move focus forward after unmarking or toggling' },
        { 'names': ('--toggle','-t'), 'action': 'store_true',
          'description': 'Mark if unmarked, unmark if marked' },
        { 'names': ('--all','-a'), 'action': 'store_true',
          'description': 'Unmark or toggle all items' },
    )
    more_sections = MarkCmd.more_sections

    tui = ExpectedResource

    def run(self, focus_next, toggle, all):
        widget = self.tui.tabs.focus
        if not widget.has_marked_column:
            raise CmdError('Nothing to unmark here.')
        else:
            widget.unmark(toggle=toggle, all=all)
            if focus_next:
                widget.focus_position += 1


class QuitCmd(metaclass=InitCommand):
    name = 'quit'
    provides = {'tui'}
    category = 'tui'
    description = 'Terminate the TUI'

    def run(self):
        import urwid
        raise urwid.ExitMainLoop()


class SearchCmd(metaclass=InitCommand):
    name = 'search'
    provides = {'tui'}
    category = 'tui'
    description = 'Search the content of the focused tab'
    usage = ('search [<OPTIONS>] <FILTER>',)
    argspecs = (
        { 'names': ('--clear','-c'), 'action': 'store_true',
          'description': 'Remove previously applied filter' },
        { 'names': ('FILTER',), 'nargs': '?',
          'description': 'Filter expression (see `help filter`)' },
    )
    tui = ExpectedResource

    def run(self, clear, FILTER):
        content = self.tui.tabs.focus
        if not hasattr(content, 'secondary_filter'):
            raise CmdError('Current tab does not support searching.')
        else:
            if clear:
                content.secondary_filter = None
                return True
            else:
                try:
                    content.secondary_filter = FILTER
                except ValueError as e:
                    raise CmdError(e)


class SortCmd(metaclass=InitCommand):
    name = 'sort'
    aliases = ()
    provides = {'tui'}
    category = 'tui'
    description = "Sort lists of torrents/peers/trackers/etc"
    usage = ('sort [<OPTIONS>] [<ORDER> <ORDER> <ORDER> ...]',)
    examples = ('sort tracker status !rate-down',
                'sort --add eta')
    argspecs = (
        {'names': ('ORDER',), 'nargs': '*',
         'description': 'How to sort list items (see SORT ORDERS section)'},

        {'names': ('--add', '-a'), 'action': 'store_true',
         'description': 'Append ORDERs to current list of sort orders instead of replacing it'},

        {'names': ('--reset', '-r'), 'action': 'store_true',
         'description': 'Go back to sort order that was used when list was created'},

        {'names': ('--none', '-n'), 'action': 'store_true',
         'description': 'Remove all sort orders from the list'},
    )

    def _list_sort_orders(title, sortercls):
        return (title,) + \
            tuple('\t{}\t - \t{}'.format(', '.join((sname,) + s.aliases), s.description)
                  for sname,s in sorted(sortercls.SORTSPECS.items()))

    from ...client import (TorrentSorter, TorrentPeerSorter,
                           TorrentTrackerSorter, SettingSorter)
    more_sections = {
        'SORT ORDERS': _list_sort_orders('TORRENT LISTS', TorrentSorter) +
                       ('',) +
                       _list_sort_orders('PEER LISTS', TorrentPeerSorter) +
                       ('',) +
                       _list_sort_orders('TRACKER LISTS', TorrentTrackerSorter)
    }

    tui = ExpectedResource

    async def run(self, add, reset, none, ORDER):
        current_tab = self.tui.tabs.focus

        if reset:
            current_tab.sort = 'RESET'

        if none:
            current_tab.sort = None

        if ORDER:
            # Find appropriate sorter class for focused list
            from ...tui.views.torrent_list import TorrentListWidget
            from ...tui.views.peer_list import PeerListWidget
            from ...tui.views.tracker_list import TrackerListWidget
            from ...tui.views.setting_list import SettingListWidget
            if isinstance(current_tab, TorrentListWidget):
                sortcls = self.TorrentSorter
            elif isinstance(current_tab, PeerListWidget):
                sortcls = self.TorrentPeerSorter
            elif isinstance(current_tab, TrackerListWidget):
                sortcls = self.TorrentTrackerSorter
            elif isinstance(current_tab, SettingListWidget):
                sortcls = self.SettingSorter
            else:
                raise CmdError('Current tab is not sortable.')

            try:
                new_sort = sortcls(ORDER)
            except ValueError as e:
                raise CmdError(e)

            if add and current_tab.sort is not None:
                current_tab.sort += new_sort
            else:
                current_tab.sort = new_sort


class TabCmd(mixin.select_torrents, metaclass=InitCommand):
    name = 'tab'
    provides = {'tui'}
    category = 'tui'
    description = 'Open, close and focus tabs'
    usage = ('tab [<OPTIONS>]',
             'tab [<OPTIONS>] <COMMAND>')
    examples = ('tab',
                'tab -c',
                'tab -c active',
                'tab ls active',
                'tab -b ls active',
                'tab -f active',
                'tab -f 3 ls active',
                'tab -b -f -1 ls active')
    argspecs = (
        { 'names': ('--background', '-b'), 'action': 'store_true',
          'description': 'Do not focus new tab' },
        { 'names': ('--close-all', '-C'), 'action': 'store_true',
          'description': 'Close all tabs' },
        { 'names': ('--close', '-c'), 'nargs': '?', 'default': False, 'document_default': False,
          'description': 'Close focused or specified tab (see TAB IDENTIFIERS SECTION)' },
        { 'names': ('--focus', '-f'),
          'description': 'Focus specified tab (see TAB IDENTIFIERS SECTION)' },
        { 'names': ('--title', '-t'),
          'description': 'Manually set tab title instead of generating one' },
        { 'names': ('COMMAND',), 'nargs': 'REMAINDER',
          'description': ('Command to run in new tab') },
    )
    more_sections = {
        'TAB IDENTIFIERS': (
            'There are three ways to specify a tab (e.g. to close it):',
            ('  - \tIntegers specify the position of the tab.  Positive numbers '
             'start from the left and negative numbers start from the right '
             '(1 (and 0) is the leftmost tab and -1 is the rightmost tab).'),
            ('  - \t"left" and "right" specify the tabs right and left to the '
             'currently focused tab.'),
            ('  - \tAnything else is assumed to be a part of a tab title.  If there '
             'are multiple matches, the first match from the left wins.'),
        ),
    }

    tui = ExpectedResource
    cmdmgr = ExpectedResource

    async def run(self, close, close_all, focus, background, title, COMMAND):
        tabs = self.tui.tabs

        # Find relevant tab IDs and fail immediately if unsuccessful
        tabid_old = tabs.get_id()
        if focus is not None:
            tabid_focus = self._get_tab_id(focus)
            if tabid_focus is None:
                raise CmdError('No such tab: %r' % (focus,))
        if close is not False:
            tabid_close = self._get_tab_id(close)
            if tabid_close is None:
                raise CmdError('No such tab: %r' % (close,))

        # COMMAND may get additional hidden arguments as instance attributes
        cmd_attrs = {}

        # The command we're running might be interested in the items the user
        # had selected in the previously focused tab, e.g. if the user selects
        # multiple torrents and runs "tab filelist", the new tab should list the
        # files of the selected torrnets.  So we provide the ID of the
        # previously focused tab as a command attribute.  The command can then
        # use that to look up the relevant torrents (usually via the
        # select_torrents() mixin class).
        if tabid_old is not None:
            cmd_attrs['previous_tab_id'] = tabid_old

        # Apply close/focus operations
        if focus is not None:
            log.debug('Focusing tab %r', tabid_focus)
            tabs.focus_id = tabid_focus
        if close_all is not False:
            log.debug('Closing all tabs')
            tabs.clear()
        elif close is not False:
            log.debug('Closing tab %r', tabid_close)
            tabs.remove(tabid_close)

        # If no tabs were closed or focused, open a new one
        if close is False and close_all is False and focus is None:
            titlew = make_tab_title_widget(title or 'Empty tab',
                                           attr_unfocused='tabs.unfocused',
                                           attr_focused='tabs.focused')
            tabs.insert(titlew, position='right')
            log.debug('Inserted new tab at position %d: %r', tabs.focus_position, titlew.base_widget.text)

        # Maybe provide a user-specified tab title to the new command
        if title:
            cmd_attrs['title'] = title

        if COMMAND:
            # Execute command
            cmd_str = ' '.join(shlex.quote(arg) for arg in COMMAND)
            log.debug('Running command in tab %s with args %s: %r',
                      tabs.focus_position,
                      ', '.join('%s=%r' % (k,v) for k,v in cmd_attrs.items()),
                      cmd_str)

            success = await self.cmdmgr.run_async(cmd_str, **cmd_attrs)
        else:
            success = True

        if background:
            tabs.focus_id = tabid_old

        return success

    def _get_tab_id(self, pos):
        tabs = self.tui.tabs
        if len(tabs) == 0:
            return None

        if pos is None:
            return tabs.focus_id

        def find_id_by_index(index):
            try:
                index = int(index)
            except ValueError:
                pass
            else:
                index_max = len(tabs) - 1
                # Internally, first tab is at index 0, but for users it's 1, unless
                # they gave us 0, in which case we assume they mean 1.
                index = index-1 if index > 0 else index

                # Limit index to index_max, considering negative values when
                # indexing from the right.
                if index < 0:
                    index = max(index, -index_max-1)
                else:
                    index = min(index, index_max)
                return tabs.get_id(index)

        def find_right_left_id(right_or_left):
            tabcount = len(tabs)
            if tabcount > 1:
                cur_index = tabs.focus_position
                cur_index = 1 if cur_index is None else cur_index
                if right_or_left == 'left':
                    return tabs.get_id(max(0, cur_index-1))
                elif right_or_left == 'right':
                    return tabs.get_id(min(tabcount-1, cur_index+1))

        def find_id_by_title(string):
            for index,title in enumerate(tabs.titles):
                if string in title.original_widget.text:
                    return tabs.get_id(index)

        # Try to use pos as an index
        tabid = find_id_by_index(pos)
        if tabid is not None:
            log.debug('Found tab ID by index: %r -> %r', pos, tabid)
            return tabid

        pos_str = str(pos)

        # Move to left/right tab
        tabid = find_right_left_id(pos_str)
        if tabid is not None:
            log.debug('Found tab ID by direction: %r -> %r', pos, tabid)
            return tabid

        # Try to find tab title
        tabid = find_id_by_title(pos_str)
        if tabid is not None:
            log.debug('Found tab ID by title: %r -> %r', pos, tabid)
            return tabid


class TUICmd(metaclass=InitCommand):
    name = 'tui'
    provides = {'tui'}
    category = 'tui'
    description = 'Show or hide parts of the text user interface'
    usage = ('tui <ACTION> <ELEMENT> <ELEMENT> ...',)
    examples = ('tui toggle log',
                'tui hide topbar.help')
    argspecs = (
        { 'names': ('ACTION',), 'choices': ('show', 'hide', 'toggle'),
          'description': '"show", "hide" or "toggle"' },
        { 'names': ('ELEMENT',), 'nargs': '+',
          'description': ('Name of TUI elements; '
                          'see ELEMENT NAMES section for a list') },
    )

    # Lazily load the element names from tui (HelpManager supports sequences
    # of lines or a callable that returns them)
    def __create_element_names():
        from ...tui.main import widgets
        return ('Available TUI element names are: ' +
                ', '.join(str(e) for e in sorted(widgets.names_recursive)),)
    more_sections = { 'ELEMENT NAMES': __create_element_names }

    tui = ExpectedResource

    def run(self, ACTION, ELEMENT):
        widgets = self.tui.widgets
        widget = None
        success = True
        for element in ELEMENT:
            # Resolve path
            path = element.split('.')
            target_name = path.pop(-1)
            current_path = []
            widget = widgets
            try:
                for widgetname in path:
                    current_path.append(widgetname)
                    widget = getattr(widget, widgetname)
            except AttributeError as e:
                self.error('Unknown TUI element: %r' % ('.'.join(current_path),))

            if widget is not None:
                action = getattr(widget, ACTION)
                if any(ACTION == x for x in ('hide', 'toggle')):
                    action = partial(action, free_space=False)

                log.debug('%sing %s in %s', ACTION.capitalize(), target_name, widget)
                try:
                    action(target_name)
                except ValueError as e:
                    success = False
                    self.error(e)
                else:
                    success = success and True
                log.debug('Success is now %r', success)

        if not success:
            raise CmdError()
