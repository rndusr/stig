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

"""Column classes that display information in peer lists"""

import urwid

from ..table import ColumnHeaderWidget
from . import (Style, CellWidgetBase)
from ...views.peer import COLUMNS as _COLUMNS


TUICOLUMNS = {}

class Torrent(_COLUMNS['torrent'], CellWidgetBase):
    width = ('weight', 100)
    style = Style(prefix='peerlist.torrent', focusable=False,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['torrent'].header),
                           style.attrs('header'))

TUICOLUMNS['torrent'] = Torrent


class Client(_COLUMNS['client'], CellWidgetBase):
    width = 30
    style = Style(prefix='peerlist.client', focusable=False,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['client'].header),
                           style.attrs('header'))

TUICOLUMNS['client'] = Client


class Country(_COLUMNS['country'], CellWidgetBase):
    width = 7
    style = Style(prefix='peerlist.country', focusable=False,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['country'].header),
                           style.attrs('header'))

TUICOLUMNS['country'] = Country


class Host(_COLUMNS['host'], CellWidgetBase):
    width = ('weight', 50)
    style = Style(prefix='peerlist.host', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['host'].header),
                           style.attrs('header'))

    def update(self, data):
        # Set IP address initially
        super().update(data)

        # Lookup hostname once per instance
        from ...main import localcfg
        if localcfg['reverse-dns']:
            def set_hostname(hostname):
                if self.text.text != hostname:
                    self.text.set_text(hostname)
            from ...client import rdns
            rdns.query(data['ip'], callback=set_hostname)

TUICOLUMNS['host'] = Host


class Port(_COLUMNS['port'], CellWidgetBase):
    style = Style(prefix='peerlist.port', focusable=False,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['port'].header),
                           style.attrs('header'))

TUICOLUMNS['port'] = Port


class PercentDownloaded(_COLUMNS['%downloaded'], CellWidgetBase):
    style = Style(prefix='peerlist.%downloaded', focusable=False,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['%downloaded'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value < 100 else None

TUICOLUMNS['%downloaded'] = PercentDownloaded


class RateUp(_COLUMNS['rate-up'], CellWidgetBase):
    style = Style(prefix='peerlist.rate-up', focusable=False,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['rate-up'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value > 0 else None

TUICOLUMNS['rate-up'] = RateUp


class RateDown(_COLUMNS['rate-down'], CellWidgetBase):
    style = Style(prefix='peerlist.rate-down', focusable=False,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['rate-down'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value > 0 else None

TUICOLUMNS['rate-down'] = RateDown


class ETA(_COLUMNS['eta'], CellWidgetBase):
    style = Style(prefix='peerlist.eta', focusable=False,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['eta'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if bool(self.value) else None

TUICOLUMNS['eta'] = ETA


class RateEst(_COLUMNS['rate-est'], CellWidgetBase):
    style = Style(prefix='peerlist.rate-est', focusable=False,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['rate-est'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value > 0 else None

TUICOLUMNS['rate-est'] = RateEst
