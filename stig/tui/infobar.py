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

import urwid

from ..main import srvapi
from ..main import cfg
from . import main as tui
from ..client import constants as const


class KeyChainsWidget(urwid.WidgetWrap):
    def __init__(self):
        self._pile = urwid.Pile([])
        super().__init__(urwid.AttrMap(self._pile, 'keychains'))

    def update(self, keychains):
        self._pile.contents[:] = []
        if not keychains:
            return

        lines = []
        keys_col_width = 0
        for kc,action in sorted(keychains, key=lambda x: str(x[0]).lower()):
            given = ' '.join(kc.given)
            current = kc.next_key
            rest = ' '.join(kc[len(kc.given)+1:])
            keys_col_width = max(len(' '.join((given, current, rest))), keys_col_width)
            lines.append((given, current, rest, str(action)))

        for given,current,rest,action in lines:
            keys_widget = urwid.Text([('keychains.keys', given), ' ',
                                      ('keychains.keys.next', current), ' ',
                                      ('keychains.keys', rest)])
            action_widget = urwid.Text(('keychains.action', action))
            line_widget = urwid.Columns([(keys_col_width, keys_widget),
                                         ('pack', urwid.Text('  -  ')),
                                         action_widget])
            self._pile.contents.append((line_widget, self._pile.options('pack')))

    def rows(self, size, focus=False):
        return len(self._pile.contents)

    _selectable = False
    _sizing = ['flow']


class QuickHelpWidget(urwid.Text):
    def __init__(self):
        super().__init__('')

    def update(self):
        def get_key(cmd, contexts):
            """Return shortest key sequence that executes `cmd`"""
            for context in contexts:
                keys = tuple(tui.keymap.keys(lambda key,action: action.startswith(cmd), context))
                if keys:
                    return sorted(keys, key=lambda k: len(k))[0]

        def get_first_key(cmd, contexts):
            """Same as `get_key`, but return only first key if key sequence"""
            key = get_key(cmd, contexts)
            if isinstance(key, tuple):  # key is a key sequence
                return key[0]
            else:
                return key

        def maybe_add_entry(items, label, key):
            if key is not None:
                items.append([('topbar.help.space',  '   '),
                              ('topbar.help.key',    str(key)),
                              ('topbar.help.equals', ' '),
                              ('topbar.help.label',  label)])

        items = []
        maybe_add_entry(items, 'Prompt', get_key('tui show cli', contexts=('main', None)))
        maybe_add_entry(items, 'Quit', get_key('quit', contexts=('main', None)))
        maybe_add_entry(items, 'Help', get_first_key('tab help', contexts=('main', None)))
        self.set_text(items) if items else self.set_text('')


class ConnectionStatusWidget(urwid.WidgetWrap):
    def __init__(self):
        self._text = urwid.Text('Not connected')
        self._attrmap = urwid.AttrMap(self._text, 'topbar.host.disconnected')
        super().__init__(self._attrmap)
        srvapi.rpc.on('connected', self._handle_connected)
        srvapi.rpc.on('disconnected', self._handle_disconnected)
        srvapi.rpc.on('error', self._handle_error)

    def _handle_connected(self, url):
        self._text.set_text('{}:{} Transmission {}'.format(url.hostname, url.port, srvapi.rpc.version))
        self._attrmap.set_attr_map({None: 'topbar.host.connected'})

    def _handle_disconnected(self, url):
        self._text.set_text(str(url))
        self._attrmap.set_attr_map({None: 'topbar.host.disconnected'})

    def _handle_error(self, url, error):
        self._text.set_text(str(error))  # error should also contain url
        self._attrmap.set_attr_map({None: 'topbar.host.disconnected'})


class BandwidthStatusWidget(urwid.Widget):
    _RATE_WIDTH = 6
    _SPACER_WIDTH = 1
    _TAIL_WIDTH = 4

    def __init__(self):
        self._text_up = urwid.Text('', align='right')
        self._text_up_limit = urwid.Text('')
        self._text_dn = urwid.Text('', align='right')
        self._text_dn_limit = urwid.Text('')

        spacer = urwid.AttrMap(urwid.SolidFill(' '), 'bottombar')
        self._spacer_canvas = spacer.render((self._SPACER_WIDTH, 1))

        def mkattr(text, attrsname):
            return urwid.AttrMap(urwid.Padding(text), attrsname)

        self._attr_up = mkattr(self._text_up, 'bottombar.bandwidth.up')
        self._attr_up_limit = mkattr(self._text_up_limit, 'bottombar.bandwidth.up')
        self._attr_dn = mkattr(self._text_dn, 'bottombar.bandwidth.down')
        self._attr_dn_limit = mkattr(self._text_dn_limit, 'bottombar.bandwidth.down')

        self._up_limit_width = 0
        self._dn_limit_width = 0
        self._connected = False

        srvapi.status.on_update(self._update_current_rates)
        srvapi.settings.on_update(self._update_rate_limits)

    def _update_current_rates(self, status):
        highlight = lambda v: v > 0

        up = status.rate_up
        if up is not const.DISCONNECTED:
            up_attrs = 'bottombar.bandwidth.up.highlighted' if highlight(up) \
                       else 'bottombar.bandwidth.up'
            self._text_up.set_text((up_attrs, str(up)))

        dn = status.rate_down
        if dn is not const.DISCONNECTED:
            dn_attrs = 'bottombar.bandwidth.down.highlighted' if highlight(dn) \
                       else 'bottombar.bandwidth.down'
            self._text_dn.set_text((dn_attrs, str(dn)))
            self._connected = True
        else:
            self._connected = False
        self._invalidate()

    def _update_rate_limits(self, settings):
        up = settings['rate-limit-up']
        dn = settings['rate-limit-down']

        # Empty display if DISCONNECTED or UNLIMITED
        as_str = lambda v: '' if v in (const.DISCONNECTED, const.UNLIMITED) \
                           else '/%s' % str(v)
        self._text_up_limit.set_text(as_str(up))
        self._text_dn_limit.set_text(as_str(dn))

        self._up_limit_width = len(self._text_up_limit.text)
        self._dn_limit_width = len(self._text_dn_limit.text)
        self._invalidate()

    def _mk_tail_canv(self, direction, icon):
        unit = {'bit': 'b', 'byte': 'B'}[cfg['unit.bandwidth'].value]
        text = urwid.Text('%s/s%s' % (unit, icon))
        attr_text = urwid.AttrMap(text, 'bottombar.bandwidth.%s' % direction)
        return attr_text.render((self._TAIL_WIDTH,))

    def render(self, size, focus=False):
        if not self._connected:
            size = self.pack(size)
            return urwid.AttrMap(urwid.SolidFill(' '), 'bottombar').render(size)

        canv_up_tail = self._mk_tail_canv('up', '↑')
        canv_dn_tail = self._mk_tail_canv('down', '↓')

        # List of (canvas, position, focus) tuples
        combinelist = []

        # Download
        canv_dn = self._attr_dn.render((self._RATE_WIDTH,))
        combinelist.append((canv_dn, None, False, self._RATE_WIDTH))
        if self._dn_limit_width > 0:
            canv_dn_limit = self._attr_dn_limit.render((self._dn_limit_width,))
            combinelist.append((canv_dn_limit, None, False, self._dn_limit_width))
        combinelist.append((canv_dn_tail, None, False, self._TAIL_WIDTH))

        combinelist.append((self._spacer_canvas, None, False, self._SPACER_WIDTH))

        # Upload
        canv_up = self._attr_up.render((self._RATE_WIDTH,))
        combinelist.append((canv_up, None, False, self._RATE_WIDTH))
        if self._up_limit_width > 0:
            canv_up_limit = self._attr_up_limit.render((self._up_limit_width,))
            combinelist.append((canv_up_limit, None, False, self._up_limit_width))
        combinelist.append((canv_up_tail, None, False, self._TAIL_WIDTH))

        return urwid.CanvasJoin(combinelist)

    _sizing = ['fixed']

    def rows(self, size, focus=False):
        return 1

    def pack(self, size, focus=False):
        cols = (self._RATE_WIDTH*2) + (self._TAIL_WIDTH*2) + \
               self._dn_limit_width + self._up_limit_width + \
               self._SPACER_WIDTH
        return (cols, 1)


class TorrentCountersWidget(urwid.WidgetWrap):
    def __init__(self):
        self._text = urwid.Text(' ')
        super().__init__(urwid.AttrMap(self._text, 'bottombar'))
        tui.srvapi.status.on_update(self._update_counters)

    def _update_counters(self, status):
        counters = status.count
        if counters.total is const.DISCONNECTED:
            self._text.set_text('')
            return

        parts = []
        for name in ('downloading', 'uploading', 'stopped'):
            count = getattr(counters, name)
            if count > 0:
                parts.append('%d %s' % (count, name))

        text = ['{} torrents'.format(str(counters.total))]
        if parts:
            text[-1] += ': ' + ', '.join(parts)

        if counters.isolated > 0:
            text[-1] += ', '
            text.append(('bottombar.important', '%s isolated' % counters.isolated))
        self._text.set_text(text)
