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

import functools
import os
import shlex
from functools import partial

from . import _mixin as mixin
from .. import CmdError, CommandMeta, utils
from ... import client, objects
from ...completion import candidates
from ._common import make_tab_title_widget

from ...logging import make_logger  # isort:skip
log = make_logger(__name__)


# Import tui.main module only on demand
def _get_keymap_contexts():
    from ...tui.tuiobjects import keymap
    return tuple(keymap.contexts)


class BindCmd(metaclass=CommandMeta):
    name = 'bind'
    provides = {'tui'}
    category = 'tui'
    description = 'Bind keys to commands or other keys'
    usage = ('bind [<OPTIONS>] <KEY> <ACTION>',)
    examples = ('bind ctrl-a tab ls active',
                'bind --context tabs alt-[ tab --focus left',
                'bind --context tabs alt-] tab --focus right',
                'bind --context torrent alt-! start --force',
                "bind --context torrent 'd .' rm",
                "bind --context torrent 'd+!' rm --delete-files",
                'bind u <up>',
                'bind d <down>')
    argspecs = (
        {'names': ('--context','-c'),
         'description': 'Where KEY is grabbed (see CONTEXTS section)'},
        {'names': ('--description','-d'),
         'description': 'Explanation of what ACTION does'},
        {'names': ('KEY',),
         'description': 'One or more keys or key combinations (see KEYS section)'},
        {'names': ('ACTION',), 'nargs': 'REMAINDER',
         'description': ("Any command or '<KEY>' (including the brackets) "
                         'to translate one key to another')},
    )

    def __create_CONTEXTS_section():
        lines = [
            ('The same key can be bound multiple times in different contexts.  '
             'With no context given, the default context is used.  The default '
             "context gets the key if it isn't mapped in any other relevant context."),
            '',
            'Available contexts are: ' + ', '.join(str(c) for c in _get_keymap_contexts()),
            '',
            'EXAMPLE',
            '\tbind --context torrent ctrl-t start',
            '\tbind --context tabs ctrl-t tab',
            '\tbind ctrl-t <left>',
            '',
            ('\tWhen focusing a torrent, <ctrl-t> starts the focused torrent.  '
             'If focus is not on a torrent but still on a tab (e.g. in an empty '
             'torrent list or when reading this text) a new tab is opened.  '
             'Otherwise (e.g. focus is on the command prompt), <ctrl-t> does the '
             'same as <left>.'),
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
             "given as one argument per chain."),
        )
    }

    def run(self, context, description, KEY, ACTION):
        from ...tui.tuiobjects import keymap
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
            keymap.bind(key, action, context=context, description=description)
        except ValueError as e:
            raise CmdError(e)

    _own_options = {('--context', '-c'): 1,
                    ('--description', '-d'): 1}

    @classmethod
    def completion_candidates_posargs(cls, args):
        """Complete positional arguments"""
        posargs = args.posargs(cls._own_options)
        if posargs.curarg_index == 2:
            # First positional argument is the key, second is the command's name
            return candidates.commands()
        else:
            # Any other positional arguments will be passed to subcmd
            subcmd = cls._get_subcmd(args)
            if subcmd:
                return candidates.for_args(subcmd)

    @classmethod
    def completion_candidates_opts(cls, args):
        """Return candidates for arguments that start with '-'"""
        subcmd = cls._get_subcmd(args)
        if subcmd:
            # Get completion candidates from subcmd's class
            return candidates.for_args(subcmd)
        else:
            # Parent class generates candidates for our own options
            return super().completion_candidates_opts(args)

    @classmethod
    def completion_candidates_params(cls, option, args):
        """Complete parameters (e.g. --option parameter1,parameter2)"""
        if option == '--context':
            return candidates.keybinding_contexts()

    @classmethod
    def _get_subcmd(cls, args):
        # posarg[0] is 'bind', posarg[1] is the key
        subcmd_start = args.nth_posarg_index(3, cls._own_options)
        # Subcmd is only relevant if the cursor is somewhere on it.
        # Otherwise, we're on our own arguments.
        if subcmd_start is not None and subcmd_start < args.curarg_index:
            return args[subcmd_start:]


class UnbindCmd(metaclass=CommandMeta):
    name = 'unbind'
    provides = {'tui'}
    category = 'tui'
    description = 'Unbind keys so pressing them has no effect'
    usage = ('unbind [<OPTIONS>] <KEY> <KEY> ...',)
    examples = ('unbind --context main ctrl-l',
                'unbind q')
    argspecs = (
        {'names': ('--context','-c'),
         'description': 'Where KEY is grabbed (see "bind" command)'},
        {'names': ('--all','-a'), 'action': 'store_true',
         'description': 'Remove all keybindings or only those in given context'},
        {'names': ('KEY',), 'nargs': 'REMAINDER',
         'description': 'Keys or key combinations (see "bind" command)'},
    )

    more_sections = {
        'COMPLETE UNBINDING': (
            ('For this command there is a special context called \'all\' that '
            'unbinds the key for every context.'),
            '',
            'Note that \'unbind --all\' is very different from \'unbind --context all\''
        )
    }

    def run(self, context, all, KEY):
        from ...tui.tuiobjects import keymap

        if context is not None and context not in _get_keymap_contexts():
            raise CmdError('Invalid context: %r' % (context,))

        if KEY:
            if context:
                success = self._unbind_keys(keys=KEY, context=context)
            elif all:
                success = self._unbind_keys(keys=KEY, context=keymap.ALL_CONTEXTS)
            else:
                success = self._unbind_keys(keys=KEY, context=keymap.DEFAULT_CONTEXT)
        else:
            success = self._unbind_all_keys(context=context)

        if not success:
            raise CmdError()

    def _unbind_keys(self, keys, context):
        from ...tui.tuiobjects import keymap
        success = True
        for key in keys:
            try:
                keymap.unbind(key, context=context)
            except ValueError as e:
                self.error(e)
                success = False
        return success

    def _unbind_all_keys(self, context):
        from ...tui.tuiobjects import keymap
        if context is None:
            keymap.clear()
        else:
            keymap.clear(context=context)
        return True

    @classmethod
    def completion_candidates_posargs(cls, args):
        """Complete positional arguments"""
        return candidates.keybinding_keys(args)

    @classmethod
    def completion_candidates_params(cls, option, args):
        """Complete parameters (e.g. --option parameter1,parameter2)"""
        if option == '--context':
            return candidates.keybinding_contexts()


class SetCommandCmd(mixin.placeholders, metaclass=CommandMeta):
    name = 'setcommand'
    aliases = ('setcmd',)
    provides = {'tui'}
    category = 'tui'
    description = 'Open the command line and insert a command'
    usage = ('setcommand [--trailing-space] <COMMAND> <ARGUMENT> <ARGUMENT> ...',)
    examples = (
        'setcommand --trailing-space tab ls',
        '\tAsk the user for a filter before opening a new torrent list.',
        '',
        'setcommand move {{location}}/',
        ('\tMove the focused torrent, using the path of the currently focused '
         'list item as a starting point.'),
        '',
        'setcommand move id={{id}} {{location}}/',
        ('\tSame as above, but make sure to move the correct torrent in case '
         'it is removed from the list while typing in the new path, e.g. if '
         'we\'re listing active torrents and the focused torrent stops being active.'),
    )
    argspecs = (
        {'names': ('COMMAND',), 'nargs': 'REMAINDER',
         'description': 'Command the can user edit before executing it (see PLACEHOLDERS)'},
        {'names': ('--trailing-space', '-s'), 'action': 'store_true',
         'description': 'Append a space at the end of COMMAND'},
    )
    more_sections = {
        'PLACEHOLDERS': mixin.placeholders.HELP,
    }

    async def run(self, COMMAND, trailing_space):
        log.debug('Unresolved command: %r', COMMAND)
        args = await self.parse_placeholders(*COMMAND)
        log.debug('Command with resolved placeholders: %r', args)

        if args:
            cmdstr = ' '.join(shlex.quote(str(arg)) for arg in args)
            if trailing_space:
                cmdstr += ' '
            from ...tui.tuiobjects import widgets
            widgets.show('cli')
            widgets.cli.base_widget.edit_text = cmdstr
            widgets.cli.base_widget.edit_pos = len(cmdstr)

    @classmethod
    def completion_candidates_posargs(cls, args):
        """Complete positional arguments"""
        posargs = args.posargs()
        if posargs.curarg_index == 1:
            # First positional argument is the subcmd's name
            return candidates.commands()
        else:
            # Any other positional arguments are part of subcmd
            subcmd = cls._get_subcmd(args)
            if subcmd:
                return candidates.for_args(subcmd)

    @classmethod
    def completion_candidates_opts(cls, args):
        """Return candidates for arguments that start with '-'"""
        subcmd = cls._get_subcmd(args)
        if subcmd:
            # Get completion candidates for subcmd
            return candidates.for_args(subcmd)
        else:
            # Parent class generates candidates for our own options
            return super().completion_candidates_opts(args)

    @staticmethod
    def _get_subcmd(args):
        # First posarg is 'setcommand'
        subcmd_start = args.nth_posarg_index(2)
        # Subcmd is only relevant if the cursor is somewhere on it.
        # Otherwise, we're on our own arguments.
        if subcmd_start is not None and subcmd_start < args.curarg_index:
            return args[subcmd_start:]


class InteractiveCmd(mixin.placeholders, metaclass=CommandMeta):
    name = 'interactive'
    provides = {'tui'}
    category = 'tui'
    description = 'Complete partial command with user input from a dialog'
    usage = ('interactive <COMMAND> [<OPTIONS>]',)
    examples = (
        'interactive "move \'[{location}/]\'"',
        '\tAsk for the destination directory when moving torrents.',
        '',
        'tab ls & interactive "limit \'[]\'" --per-change --on-cancel "tab --close --focus left"',
        ('\tOpen a new tab with all torrents and filter them as you type.  '
         'Keep the tab open if the user input field is accepted with <enter> '
         'or close the tab and focus the previous one if the dialog is aborted '
         'with <escape>.'),
        '',
        'tab ls stopped & interactive \'limit "[]"\' -p -a "mark --all & start" -x "tab --close --focus left"',
        ('\tSearch for stopped torrents only.  When accepted, the matching torrents '
         'are started.  The new tab is always closed, whether the dialog is '
         'accepted or not.'),
    )
    argspecs = (
        {'names': ('COMMAND',),
         'description': ('Any command with "[PREFILLED TEXT]" as marker for '
                         'user input field (see USER INPUT FIELDS) and '
                         '"{{NAM}}" as placeholder for values of the currently '
                         'focused list item (see PLACEHOLDERS)')},
        {'names': ('--per-change', '-p'), 'action': 'store_true',
         'description': 'Whether to run COMMAND every time the input is changed'},
        {'names': ('--on-accept', '-a'), 'metavar': 'ACCEPT COMMAND',
         'description': 'Command to run when the dialog is accepted (with <enter>)'},
        {'names': ('--on-cancel', '-c'), 'metavar': 'CANCEL COMMAND',
         'description': 'Command to run when the dialog is aborted (with <escape>)'},
        {'names': ('--on-close', '-x'), 'metavar': 'CLOSE COMMAND',
         'description': 'Command to run after the dialog is closed either way'},
        {'names': ('--ignore-errors', '-i'), 'action': 'store_true',
         'description': 'Whether to ignore errors from COMMAND'},
    )
    more_sections = {
        'COMMANDS': (('For each occurrence of "[]" in any command, the user is '
                      'prompted for input to insert at that point.  Any text between '
                      '"[" and "]" is used as the initial user input.  "[" can be '
                      'escaped with "\\" in which case the corresponding "]" is also '
                      'interpreted literally.'),
                     '',
                     ('COMMAND is called if the user presses <enter> or, if --per-change '
                      'is given, after any user input field is changed.'),
                     '',
                     ('COMMAND must contain at least one user input field.  Any of the '
                      'commands described below are called without user interaction if '
                      'they don\'t contain any user input fields.'),
                     '',
                     ('ACCEPT COMMAND is called after COMMAND if the user accepts the '
                      'dialog by pressing <enter>.'),
                     '',
                     'CANCEL COMMAND is called if the user aborts the COMMAND dialog.',
                     '',
                     ('CLOSE COMMAND is always called when the dialog is closed either '
                      'by accepting or by cancelling it.')),
        'PLACEHOLDERS': mixin.placeholders.HELP,
    }

    import re
    _input_regex = re.compile(r'(?<!\\)(\[.*?\])')

    async def run(self, COMMAND, per_change, on_accept, on_cancel, on_close, ignore_errors):
        cmd = await self._parse_cmd(COMMAND)
        accept_cmd = await self._parse_cmd(on_accept) if on_accept else None
        cancel_cmd = await self._parse_cmd(on_cancel) if on_cancel else None
        close_cmd = await self._parse_cmd(on_close) if on_close else None
        self._ignore_errors = ignore_errors

        if len(cmd) == 1:
            # There are no user input markers
            raise CmdError('No user input fields ("[]"): %s' % COMMAND)

        def close_cb():
            self._run_cmd_or_open_dialog(close_cmd)

        if per_change:
            def accept_cb():
                self._run_cmd_from_dialog()
                self._run_cmd_or_open_dialog(accept_cmd)

            def cancel_cb():
                self._run_cmd_or_open_dialog(cancel_cmd)

            self._open_dialog(cmd,
                              on_change=self._run_cmd_from_dialog,
                              on_accept=accept_cb,
                              on_cancel=cancel_cb,
                              on_close=close_cb)
        else:
            def accept_cb():
                self._run_cmd_from_dialog()
                self._run_cmd_or_open_dialog(accept_cmd)

            def cancel_cb():
                self._run_cmd_or_open_dialog(cancel_cmd)

            self._open_dialog(cmd,
                              on_accept=accept_cb,
                              on_cancel=cancel_cb,
                              on_close=close_cb)

    _WIDGET_NAME = 'interactive_prompt'
    _MIN_EDIT_WIDTH = 25
    _MAX_EDIT_WIDTH = 50

    def _open_dialog(self, cmd, on_change=None, on_accept=None, on_cancel=None, on_close=None):
        import urwid
        from ...tui.cli import CLIEditWidget

        def accept_cb(widget):
            # CLIEditWidget only automatically appends to history when it gets
            # an <enter> key, but only one gets it if there are multiple user
            # input fields.
            for part in self._edit_widgets:
                part.append_to_history()
            self._close_dialog()
            if on_accept: on_accept()
            if on_close: on_close()

        def cancel_cb(widget):
            self._close_dialog()
            if on_cancel: on_cancel()
            if on_close: on_close()

        def change_cb(widget):
            if on_change: on_change()

        # Derive history file name from command
        import re
        filename = re.sub('[/\n]', '__', ''.join(cmd))
        history_file_base = os.path.join(objects.localcfg['tui.cli.history-dir'].full_path, filename)

        columns_args = [('pack', urwid.Text(':'))]
        self._cmd_parts = []
        self._edit_widgets = []
        edit_index = 0
        for part in cmd:
            if part[0] == '[' and part[-1] == ']':
                edit_index += 1
                history_file = history_file_base + '.input%d' % edit_index
                log.debug('History file for edit #%d: %r', edit_index, history_file)
                edit_widget = CLIEditWidget(on_change=change_cb,
                                            on_accept=accept_cb,
                                            on_cancel=cancel_cb,
                                            history_file=history_file)
                edit_widget.edit_text = part[1:-1]
                edit_widget.edit_pos = len(edit_widget.edit_text)
                columns_args.append(urwid.AttrMap(edit_widget, 'prompt'))
                self._cmd_parts.append(edit_widget)
                self._edit_widgets.append(edit_widget)
            else:
                columns_args.append(('pack', urwid.Text(part)))
                self._cmd_parts.append(part)

        class MyColumns(urwid.Columns):
            """Use <tab> and <shift-tab> to move focus between input fields"""
            def keypress(self, size, key):

                def move_right():
                    if self.focus_position < len(self.contents) - 1:
                        self.focus_position += 1
                    else:
                        self.focus_position = 0

                def move_left():
                    if self.focus_position > 0:
                        self.focus_position -= 1
                    else:
                        self.focus_position = len(self.contents) - 1

                if key == 'tab':
                    move_right()
                    while not isinstance(self.focus.base_widget, urwid.Edit):
                        move_right()
                elif key == 'shift-tab':
                    move_left()
                    while not isinstance(self.focus.base_widget, urwid.Edit):
                        move_left()
                else:
                    log.debug('focus pos: %r', self.focus_position)
                    return super().keypress(size, key)

        columns_widget = MyColumns(columns_args)

        # Close any previously opened dialog
        from ...tui.tuiobjects import widgets
        if widgets.exists(self._WIDGET_NAME):
            self._close_dialog()

        # Focus the first empty input widget if there are any
        for i,(w,_) in enumerate(columns_widget.contents):
            w = w.base_widget
            log.debug('%02d: %r', i, w)
            if hasattr(w, 'edit_text') and w.edit_text == '':
                columns_widget.focus_position = i
                break

        widgets.add(name=self._WIDGET_NAME,
                    widget=urwid.AttrMap(columns_widget, 'cli'),
                    position=widgets.get_position('cli'),
                    removable=True,
                    options='pack')

    def _close_dialog(self):
        from ...tui.tuiobjects import widgets
        widgets.remove(self._WIDGET_NAME)
        widgets.focus_name = 'main'

    def _run_cmd_or_open_dialog(self, cmd):
        if not cmd:
            return
        elif len(cmd) == 1:
            log.debug('Running command without dialog: %r', cmd)
            self._run_cmd(cmd[0])
        else:
            log.debug('Running command in dialog: %r', cmd)
            self._open_dialog(cmd, on_accept=self._run_cmd_from_dialog)

    def _run_cmd_from_dialog(self):
        cmd = []
        for part in self._cmd_parts:
            if hasattr(part, 'edit_text'):
                cmd.append(part.edit_text)
            else:
                cmd.append(part)
        cmd = ''.join(cmd)
        log.debug('Got command from current dialog: %r', cmd)
        self._run_cmd(cmd)

    def _run_cmd(self, cmd):
        log.debug('Running cmd: %r', cmd)
        if self._ignore_errors:
            # Overload the error() method on the command's instance
            objects.cmdmgr.run_task(cmd, error=lambda msg: None)
        else:
            objects.cmdmgr.run_task(cmd)

    async def _parse_cmd(self, cmd):
        assert isinstance(cmd, str)
        args = await self.parse_placeholders(cmd)
        return self._split_cmd_at_inputs(args[0])

    def _split_cmd_at_inputs(self, cmd):
        """
        Split `cmd` so that each input marker ("[...]") is a single item

        Example result:
            ['somecmd --an-argument ', '[user input goes here]', ' some more arguments']
        """

        log.debug('Splitting %r', cmd)
        parts = [part for part in self._input_regex.split(cmd) if part]
        log.debug('Split: %r', parts)

        for i in range(len(parts)):
            parts[i] = parts[i].replace('\\[', '[')
        log.debug('Unescaped: %r', parts)

        return parts


class MarkCmd(metaclass=CommandMeta):
    name = 'mark'
    provides = {'tui'}
    category = 'tui'
    description = 'Select torrents or files for an action'
    usage = ('mark [<OPTIONS>]',)
    argspecs = (
        {'names': ('--focus-next','-n'), 'action': 'store_true',
         'description': 'Move focus forward after marking or toggling'},
        {'names': ('--toggle','-t'), 'action': 'store_true',
         'description': 'Mark if unmarked, unmark if marked'},
        {'names': ('--all','-a'), 'action': 'store_true',
         'description': 'Mark or toggle all items'},
    )
    more_sections = {
        'NOTES': (('The column "marked" must be in the "columns.*" settings. Otherwise '
                   'marked list items are indistinguishable from unmarked ones.'),
                  '',
                  ('The character that is displayed in the "marked" column is '
                   'specified by the settings "tui.marked.on" and "tui.marked.off".')),
    }

    def run(self, focus_next, toggle, all):
        from ...tui.tuiobjects import tabs
        widget = tabs.focus
        if not widget.has_marked_column:
            raise CmdError('Nothing to mark here.')
        else:
            widget.mark(toggle=toggle, all=all)
            if focus_next:
                widget.focus_position += 1


class UnmarkCmd(metaclass=CommandMeta):
    name = 'unmark'
    provides = {'tui'}
    category = 'tui'
    description = 'Deselect torrents or files for an action'
    usage = ('unmark [<OPTIONS>]',)
    argspecs = (
        {'names': ('--focus-next','-n'), 'action': 'store_true',
         'description': 'Move focus forward after unmarking or toggling'},
        {'names': ('--toggle','-t'), 'action': 'store_true',
         'description': 'Mark if unmarked, unmark if marked'},
        {'names': ('--all','-a'), 'action': 'store_true',
         'description': 'Unmark or toggle all items'},
    )
    more_sections = MarkCmd.more_sections

    def run(self, focus_next, toggle, all):
        from ...tui.tuiobjects import tabs
        widget = tabs.focus
        if not widget.has_marked_column:
            raise CmdError('Nothing to unmark here.')
        else:
            widget.unmark(toggle=toggle, all=all)
            if focus_next:
                widget.focus_position += 1


class QuitCmd(metaclass=CommandMeta):
    name = 'quit'
    provides = {'tui'}
    category = 'tui'
    description = 'Terminate the TUI'

    def run(self):
        import urwid
        raise urwid.ExitMainLoop()


class FindCmd(metaclass=CommandMeta):
    name = 'find'
    provides = {'tui'}
    category = 'tui'
    description = 'Find text in the content of the focused tab'
    usage = ('find [<OPTIONS>] [<PHRASE>]',)
    argspecs = (
        {'names': ('--clear','-c'), 'action': 'store_true',
         'description': ('Remove previously applied filter; this is '
                         'the default if no PHRASE arguments are provided')},
        {'names': ('--next','-n'), 'action': 'store_true',
         'description': 'Jump to next match (call `find <PHRASE>` first)'},
        {'names': ('--previous','-p'), 'action': 'store_true',
         'description': 'Jump to previous match (call `find <PHRASE>` first)'},
        {'names': ('PHRASE',), 'nargs': '*',
         'description': 'Search phrase'},
    )

    def run(self, clear, next, previous, PHRASE):
        from ...tui.tuiobjects import tabs
        content = tabs.focus.base_widget
        if not hasattr(content, 'search_phrase'):
            raise CmdError('This tab does not support finding.')
        elif next and previous:
            raise CmdError('The options --next and --previous contradict each other.')
        elif next:
            if content.search_phrase is None:
                raise CmdError('Set a search phrase first with `find <PHRASE>`.')
            else:
                content.jump_to_next_match()
        elif previous:
            if content.search_phrase is None:
                raise CmdError('Set a search phrase first with `find <PHRASE>`.')
            else:
                content.jump_to_prev_match()
        elif clear:
            content.search_phrase = None
        else:
            try:
                content.search_phrase = ' '.join(PHRASE)
                content.maybe_jump_to_next_match()
            except ValueError as e:
                raise CmdError(e)


class LimitCmd(metaclass=CommandMeta):
    name = 'limit'
    provides = {'tui'}
    category = 'tui'
    description = 'Limit contents of the focused tab by applying more filters'
    usage = ('limit [<OPTIONS>] [<FILTER> <FILTER> ...]',)
    argspecs = (
        {'names': ('--clear','-c'), 'action': 'store_true',
         'description': ('Remove previously applied filter; this is '
                         'the default if no FILTER arguments are provided')},
        {'names': ('FILTER',), 'nargs': '*',
         'description': 'Filter expression (see `help filters`)'},
    )

    def run(self, clear, FILTER):
        from ...tui.tuiobjects import tabs
        content = tabs.focus.base_widget
        if not hasattr(content, 'secondary_filter'):
            raise CmdError('This tab does not support limiting.')
        else:
            if clear or not FILTER:
                content.secondary_filter = None
            else:
                try:
                    content.secondary_filter = FILTER
                except ValueError as e:
                    raise CmdError(e)

    @classmethod
    def completion_candidates_posargs(cls, args):
        """Complete positional arguments"""
        from ...tui.tuiobjects import tabs
        from ...tui.views import (TorrentListWidget, FileListWidget,
                                  PeerListWidget, TrackerListWidget,
                                  SettingListWidget)
        widget = tabs.focus.base_widget
        if hasattr(widget, 'secondary_filter'):
            if isinstance(widget, TorrentListWidget):
                return candidates.torrent_filter(args.curarg)
            elif isinstance(widget, FileListWidget):
                torrent_filter = 'id=%s' % (widget.focused_torrent_id,)
                return candidates.file_filter(args.curarg, torrent_filter)
            elif isinstance(widget, PeerListWidget):
                return candidates.peer_filter(args.curarg, None)
            elif isinstance(widget, TrackerListWidget):
                torrent_filter = '|'.join('id=%s' % (itemw.torrent_id,)
                                          for itemw in widget.items)
                return candidates.tracker_filter(args.curarg, torrent_filter)
            elif isinstance(widget, SettingListWidget):
                return candidates.setting_filter(args.curarg)


class SortCmd(metaclass=CommandMeta):
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

        {'names': ('--delete', '-d'), 'action': 'store_true',
         'description': 'Delete ORDERs from current list of sort orders instead of replacing it'},

        {'names': ('--reset', '-r'), 'action': 'store_true',
         'description': 'Go back to sort order that was used when the list was created'},

        {'names': ('--none', '-n'), 'action': 'store_true',
         'description': 'Remove all sort orders from the list'},
    )

    def _list_sort_orders(title, sortcls):
        return (title,) + \
            tuple('\t{}\t - \t{}'.format(', '.join((sname,) + s.aliases), s.description)
                  for sname,s in sorted(sortcls.SORTSPECS.items()))

    more_sections = {
        'SORT ORDERS': (_list_sort_orders('TORRENT LISTS', client.TorrentSorter) +
                        ('',) +
                        _list_sort_orders('PEER LISTS', client.PeerSorter) +
                        ('',) +
                        _list_sort_orders('TRACKER LISTS', client.TrackerSorter))
    }

    async def run(self, add, delete, reset, none, ORDER):
        from ...tui.tuiobjects import tabs
        current_tab = tabs.focus.base_widget

        if reset:
            current_tab.sort = 'RESET'

        if none:
            current_tab.sort = None

        if ORDER:
            # # Find appropriate sorter class for focused list
            sortcls = self._widget2sortcls(current_tab)
            if sortcls is None:
                raise CmdError('Current tab is not sortable.')
            try:
                new_sort = sortcls(utils.listify_args(ORDER))
            except ValueError as e:
                raise CmdError(e)

            if add and current_tab.sort is not None:
                current_tab.sort += new_sort
            elif delete and current_tab.sort is not None:
                current_tab.sort -= new_sort
            else:
                current_tab.sort = new_sort

    @staticmethod
    def _widget2sortcls(list_widget):
        from ...tui.views import (TorrentListWidget, PeerListWidget,
                                  TrackerListWidget, SettingListWidget)
        if isinstance(list_widget, TorrentListWidget):
            return client.TorrentSorter
        elif isinstance(list_widget, PeerListWidget):
            return client.PeerSorter
        elif isinstance(list_widget, TrackerListWidget):
            return client.TrackerSorter
        elif isinstance(list_widget, SettingListWidget):
            return client.SettingSorter

    @classmethod
    def completion_candidates_posargs(cls, args):
        """Complete positional arguments"""
        from ...tui.tuiobjects import tabs
        sortcls = cls._widget2sortcls(tabs.focus.base_widget)
        if sortcls is not None:
            return candidates.sort_orders(sortcls.__name__)


class TabCmd(mixin.select_torrents, metaclass=CommandMeta):
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
        {'names': ('--background', '-b'), 'action': 'store_true',
         'description': 'Do not focus new tab'},
        {'names': ('--close-all', '-C'), 'action': 'store_true',
         'description': 'Close all tabs'},
        {'names': ('--close', '-c'), 'nargs': '?', 'default': False, 'document_default': False,
         'description': 'Close focused or specified tab (see TAB IDENTIFIERS SECTION)'},
        {'names': ('--focus', '-f'),
         'description': 'Focus specified tab (see TAB IDENTIFIERS SECTION)'},
        {'names': ('--move', '-m'),
         'description': 'Move focused tab left, right or to absolute position'},
        {'names': ('--title', '-t'),
         'description': 'Manually set tab title instead of generating one'},
        {'names': ('COMMAND',), 'nargs': 'REMAINDER',
         'description': ('Command to run in tab')},
    )
    more_sections = {
        'TAB IDENTIFIERS': (
            'There are three ways to specify a tab (e.g. to close it):',
            ('  - \tIntegers specify the position of the tab.  Positive numbers '
             'start from the left and negative numbers start from the right '
             '(1 (and 0) is the leftmost tab and -1 is the rightmost tab).'),
            ('  - \t"left" and "right" specify the tabs next to the '
             'currently focused tab.'),
            ('  - \tAnything else is assumed to be a part of a tab title.  If there '
             'are multiple matches, the first match from the left wins.'),
        ),
    }

    async def run(self, background, close_all, close, focus, move, title, COMMAND):
        from ...tui.tuiobjects import tabs
        tabid_old = tabs.get_id()

        # Find relevant tab IDs and fail immediately if unsuccessful
        if focus is not None:
            tabid_focus = self._get_tab_id(focus)
            if tabid_focus is None:
                raise CmdError('No such tab: %r' % (focus,))
        if close is not False:
            tabid_close = self._get_tab_id(close)
            if tabid_close is None:
                if close is None:
                    raise CmdError('No tab is open')
                else:
                    raise CmdError('No such tab: %r' % (close,))

        # COMMAND may get additional hidden arguments as instance attributes
        cmd_attrs = {}

        # Apply close/focus/move operations
        if focus is not None:
            log.debug('Focusing tab %r', tabid_focus)
            tabs.focus_id = tabid_focus
        if close_all is not False:
            log.debug('Closing all tabs')
            tabs.clear()
        elif close is not False:
            log.debug('Closing tab %r', tabid_close)
            tabs.remove(tabid_close)
        elif move and tabs.focus:
            self._move_tab(tabs, move)

        # If no tabs were closed, focused or moved, open a new one
        if close is False and close_all is False and focus is None and not move:
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

            success = await objects.cmdmgr.run_async(cmd_str, **cmd_attrs)
        else:
            success = True

        if background:
            tabs.focus_id = tabid_old
        else:
            content = tabs.focus
            if content is not None and hasattr(content, 'marked_count'):
                from ...tui.tuiobjects import bottombar
                bottombar.marked.update(content.marked_count)

        return success

    def _get_tab_id(self, pos):
        from ...tui.tuiobjects import tabs
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
                index = index - 1 if index > 0 else index

                # Limit index to index_max, considering negative values when
                # indexing from the right.
                if index < 0:
                    index = max(index, -index_max - 1)
                else:
                    index = min(index, index_max)
                return tabs.get_id(index)

        def find_right_left_id(right_or_left):
            tabcount = len(tabs)
            if tabcount > 1:
                cur_index = tabs.focus_position
                cur_index = 1 if cur_index is None else cur_index
                if right_or_left == 'left':
                    return tabs.get_id(max(0, cur_index - 1))
                elif right_or_left == 'right':
                    return tabs.get_id(min(tabcount - 1, cur_index + 1))

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

    def _move_tab(self, tabs, move):
        if move == 'left':
            tabs.move(tabs.get_id(), 'left')
        elif move == 'right':
            tabs.move(tabs.get_id(), 'right')
        else:
            try:
                index = int(move)
            except (ValueError, TypeError):
                raise CmdError('--move argument must be "left", "right" or tab index: %r' % (move,))
            else:
                # Positive tab index starts at 0, negative at -1
                if index > 0:
                    index -= 1
                tabs.move(tabs.get_id(), index)

    _own_options = {('--close', '-c'): 1,
                    ('--focus', '-f'): 1,
                    ('--title', '-t'): 1}

    @classmethod
    def completion_candidates_posargs(cls, args):
        """Complete positional arguments"""
        posargs = args.posargs(cls._own_options)
        if posargs.curarg_index == 1:
            # First positional argument is the subcmd's name
            return candidates.commands()
        else:
            # Any other positional arguments will be passed to subcmd
            subcmd = cls._get_subcmd(args)
            if subcmd:
                return candidates.for_args(subcmd)

    @classmethod
    def completion_candidates_opts(cls, args):
        """Return candidates for arguments that start with '-'"""
        subcmd = cls._get_subcmd(args)
        if subcmd:
            # Get completion candidates for subcmd
            return candidates.for_args(subcmd)
        else:
            # Parent class generates candidates for our own options
            return super().completion_candidates_opts(args)

    @classmethod
    def completion_candidates_params(cls, option, args):
        """Complete parameters (e.g. --option parameter1,parameter2)"""
        if option in ('--close', '--focus'):
            return candidates.tab_titles()

    @classmethod
    def _get_subcmd(cls, args):
        # First posarg is 'tab'
        subcmd_start = args.nth_posarg_index(2, cls._own_options)
        # Subcmd is only relevant if the cursor is somewhere on it.
        # Otherwise, we're on our own arguments.
        if subcmd_start is not None and subcmd_start < args.curarg_index:
            return args[subcmd_start:]


class TUICmd(metaclass=CommandMeta):
    name = 'tui'
    provides = {'tui'}
    category = 'tui'
    description = 'Show or hide parts of the text user interface'
    usage = ('tui <ACTION> <ELEMENT> <ELEMENT> ...',)
    examples = ('tui toggle log',
                'tui hide topbar.help')
    argspecs = (
        {'names': ('ACTION',), 'choices': ('show', 'hide', 'toggle'),
         'description': '"show", "hide" or "toggle"'},
        {'names': ('ELEMENT',), 'nargs': '+',
         'description': ('Name of TUI elements; '
                         'see ELEMENT NAMES section for a list')},
    )
    # HelpManager supports sequences of lines or a callable that returns them
    more_sections = {'ELEMENT NAMES': lambda: ('Available TUI element names are: ' +
                                               ', '.join(_tui_element_names()),)}

    def run(self, ACTION, ELEMENT):
        from ...tui.tuiobjects import widgets
        widget = None
        success = True
        for element in utils.listify_args(ELEMENT):
            # Resolve path
            path = element.split('.')
            target_name = path.pop(-1)
            current_path = []
            widget = widgets
            try:
                for widgetname in path:
                    current_path.append(widgetname)
                    widget = getattr(widget, widgetname)
            except AttributeError:
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

        if not success:
            raise CmdError()

    @classmethod
    def completion_candidates_posargs(cls, args):
        """Complete positional arguments"""
        posargs = args.posargs()
        if posargs.curarg_index == 1:
            for argspec in cls.argspecs:
                if 'ACTION' in argspec['names']:
                    return candidates.Candidates(argspec['choices'],
                                                 label='Action')
        else:
            return candidates.Candidates(_tui_element_names(),
                                         label='Element')

# Lazily load element names from tui module to avoid importing TUI stuff if possible
@functools.lru_cache()
def _tui_element_names():
    from ...tui import tuiobjects
    return tuple(str(name) for name in sorted(tuiobjects.widgets.names_recursive))
