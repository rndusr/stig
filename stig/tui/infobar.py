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


class QuickHelpWidget(urwid.Text):
    ITEMS = (
        # Context, Command, Description
        ('main', 'tui show cli', 'Prompt'),
        ('main', 'tab help keymap',  'Keymap'),
        ('main', 'quit','Quit'),
    )

    def __init__(self):
        texts = []
        for context,cmd,label in self.ITEMS:
            keys = tuple(tui.keymap.keys(cmd, context))
            texts.extend([
                ('topbar.help.key',    str(keys[0])),
                ('topbar.help.equals', ' '),
                ('topbar.help.label',  label),
                ('topbar.help.space',  '   '),
            ])
        texts.pop(-1)  # Remove delimiter space from last item
        super().__init__(texts)


class ConnectionStatusWidget(urwid.WidgetWrap):
    def __init__(self):
        self._text = urwid.Text(' ')
        self._attrmap = urwid.AttrMap(self._text, 'topbar.host.disconnected')
        super().__init__(self._attrmap)
        srvapi.rpc.on('connected', self._handle_connected)
        srvapi.rpc.on('disconnected', self._handle_disconnected)

    def _handle_connected(self, url):
        self._text.set_text('{}:{} Transmission {}'.format(url.hostname, url.port, srvapi.rpc.version))
        self._attrmap.set_attr_map({None: 'topbar.host.connected'})

    def _handle_disconnected(self, url):
        self._text.set_text(str(url))
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
