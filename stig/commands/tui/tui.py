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


from .. import (InitCommand, ExpectedResource)


from ...tui import KEYMAP_CONTEXTS
import shlex
class BindCmd(metaclass=InitCommand):
    name = 'bind'
    provides = {'tui'}
    category = 'tui'
    description = 'Bind keys to commands or other keys'
    usage = ('bind [--context <CONTEXT>] <KEY> <ACTION>',)
    examples = ('bind --context tabs alt-[ tab --focus left',
                'bind --context tabs alt-] tab --focus right',
                'bind --context torrent alt-! start --force',
                'bind ctrl-a tab ls active',
                "bind 'd .' delete",
                "bind 'd !' delete --delete-files",
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
            'Available contexts are: ' + \
              ', '.join('"%s"' % context for context in KEYMAP_CONTEXTS),
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

        if context is not None and context not in KEYMAP_CONTEXTS:
            log.error('Invalid context: {!r}'.format(context))
            return False
        try:
            keymap.bind(key, action, context=context)
        except ValueError as e:
            log.error(e)
            return False
        else:
            return True


class ClearLogCmd(metaclass=InitCommand):
    name = 'clearlog'
    provides = {'tui'}
    category = 'tui'
    description = 'Clear all logged messages'

    tui = ExpectedResource

    def run(self):
        logwidget = self.tui.logwidget
        if len(tuple(logwidget.entries)) > 0:
            logwidget.clear()
            return True
        else:
            return False


class QuitCmd(metaclass=InitCommand):
    name = 'quit'
    provides = {'tui'}
    category = 'tui'
    description = 'Terminate the TUI'

    def run(self):
        import urwid
        raise urwid.ExitMainLoop()


class RcCmd(metaclass=InitCommand):
    name = 'rc'
    aliases = ('source',)
    category = 'misc'
    provides = {'tui'}
    description = 'Run commands in rc file'
    usage = ('rc <FILE>',)
    examples = ('rc rc.example.org   # Load $XDG_CONFIG_HOME/.config/{APPNAME}/rc.example.org',)
    argspecs = (
        {'names': ('FILE',),
         'description': ('Path to rc file; if FILE does not start with '
                         "'.', '~' or '/', $XDG_CONFIG_HOME/.config/{APPNAME}/ "
                         'is prepended')},
    )
    cmdmgr = ExpectedResource

    def run(self, FILE):
        from ...settings import rcfile
        from ...settings.defaults import DEFAULT_RCFILE
        import os

        if FILE[0] not in (os.sep, '.', '~'):
            FILE = '{}{}{}'.format(os.path.dirname(DEFAULT_RCFILE),
                                   os.sep,
                                   FILE)

        try:
            lines = rcfile.read(FILE)
        except rcfile.RcFileError as e:
            log.error('Loading rc file failed: {}'.format(e))
            return False
        else:
            log.debug('Reading commands from rc file: %r', FILE)
            log.debug(lines)
            for cmdline in lines:
                self.cmdmgr(cmdline)
            return True


class TabCmd(metaclass=InitCommand):
    name = 'tab'
    provides = {'tui'}
    category = 'tui'
    description = 'Open, close and focus tabs'
    usage = ('tab [--close] [--focus <TITLE OR INDEX>] [<COMMAND>]',)
    examples = ('tab',
                'tab ls active',
                'tab -f active',
                'tab -f 3 ls active',
                'tab -c')
    argspecs = (
        { 'names': ('--close', '-c'), 'nargs': '?', 'const': None, 'default': False,
          'description': 'Close tab at index CLOSE or with partial tital CLOSE' },
        { 'names': ('--focus', '-f'),
          'description': ('Focus tab; FOCUS can be an index (first tab is 1), '
                          "part of a tab title, 'left'/'-' or 'right'/'+'") },
        { 'names': ('COMMAND',), 'nargs': 'REMAINDER',
          'description': ('Command to run in new tab') },
    )

    tui = ExpectedResource
    cmdmgr = ExpectedResource

    async def run(self, close, focus, COMMAND):
        # Get indexes before adding/removing tabs, which changes indexes on
        # subsequent operations
        if focus is not None:
            i_focus = self.get_tab_index(focus)
            log.debug('Focusing tab %r at index %r', focus, i_focus)
            if i_focus is None:
                return False
        if close is not False:
            i_close = self.get_tab_index(close)
            log.debug('Closing tab %r at index %r', close, i_close)
            if i_close is None:
                return False

        tabs = self.tui.tabs

        # Apply close/focus operations
        if focus is not None:
            tabs.focus_position = i_focus
        if close is not False:
            tabs.remove(i_close)

        # Remember which torrent is focused in current tab so we can provide
        # it to the command running in a new tab.
        cmdargs = {}
        try:
            cmdargs['focused_torrent'] = tabs.focus.focused_torrent.torrent
        except AttributeError:
            pass

        if close is False and focus is None:
            import urwid
            titlew = urwid.AttrMap(urwid.Text('Empty tab'), 'tabs.unfocused', 'tabs.focused')
            tabs.insert(titlew, position='right')
            log.debug('Inserted new tab at position %d', tabs.focus_position)

        if COMMAND:
            log.debug('Running command in tab %d with args %s: %r',
                      tabs.focus_position,
                      ', '.join('%s=%r' % (k,v) for k,v in cmdargs.items()),
                      COMMAND)

            process = self.cmdmgr.run(COMMAND, **cmdargs)
            # Sync processes are always finished at this point.
            # Async processes must finish before we can report our own success.
            if not process.finished:
                await process.task
            return process.success
        else:
            return True

    def get_tab_index(self, pos):
        tabs = self.tui.tabs

        if pos is None:
            return tabs.focus_position

        def find_index(i):
            try:
                return tabs.get_index(i-1)
            except IndexError as e:
                log.error('No tab at position: {}'.format(e.value+1))

        def find_title(string):
            for i,title in enumerate(tabs.titles):
                if string in title.original_widget.text:
                    return i
            log.error('No tab found: {!r}'.format(string))

        tabcount = len(tabs)
        curpos = tabs.focus_position
        curpos = 1 if curpos is None else curpos

        if pos.isdigit():
            return find_index(int(pos))
        elif pos in ('left', '-'):
            if tabcount > 1:
                return tabs.get_index(max(0, curpos-1))
        elif pos in ('right', '+'):
            if tabcount > 1:
                return tabs.get_index(min(tabcount-1, curpos+1))
        else:
            return find_title(pos)


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
        { 'names': ('ELEMENTS',), 'nargs': '+',
          'description': ('Name(s) of TUI elements; '
                          'see ELEMENT NAMES section for a list') },
    )

    # Lazily load the element names from tui (HelpManager supports sequences
    # of lines or a callable that returns them)
    def __create_element_names():
        from ...tui.main import widgets
        return ('Available TUI element names are: ' + \
                ', '.join(str(e) for e in sorted(widgets.names_recursive)),)
    more_sections = { 'ELEMENT NAMES': __create_element_names }

    tui = ExpectedResource

    def run(self, ACTION, ELEMENTS):
        widgets = self.tui.widgets
        widget = None
        success = False
        for element in ELEMENTS:
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
                log.error('Unknown TUI element: %r', '.'.join(current_path))

        if widget is not None:
            action = getattr(widget, ACTION)
            log.debug('%sing %s in %s', ACTION.capitalize(), target_name, widget)
            try:
                action(target_name)
                success = True
            except ValueError as e:
                log.error(e)
        return success
