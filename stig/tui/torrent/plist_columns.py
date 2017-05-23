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
from ...views.plist import COLUMNS as _COLUMNS


TUICOLUMNS = {}

class TorrentName(_COLUMNS['name'], CellWidgetBase):
    width = ('weight', 100)
    style = Style(prefix='peerlist.name', focusable=False,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['name'].header),
                           style.attrs('header'))

TUICOLUMNS['name'] = TorrentName


class Client(_COLUMNS['client'], CellWidgetBase):
    width = ('weight', 100)
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


class IPAddress(_COLUMNS['ip'], CellWidgetBase):
    style = Style(prefix='peerlist.ip', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['ip'].header),
                           style.attrs('header'))

TUICOLUMNS['ip'] = IPAddress


class Port(_COLUMNS['port'], CellWidgetBase):
    style = Style(prefix='peerlist.port', focusable=False,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['port'].header),
                           style.attrs('header'))

TUICOLUMNS['port'] = Port


class Progress(_COLUMNS['progress'], CellWidgetBase):
    style = Style(prefix='peerlist.progress', focusable=False,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['progress'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value < 100 else None

TUICOLUMNS['progress'] = Progress


class RateDown(_COLUMNS['rate-down'], CellWidgetBase):
    style = Style(prefix='peerlist.rate-down', focusable=False,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['rate-down'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value > 0 else None

    @classmethod
    def set_unit(cls, unit):
        cls.header.original_widget.right = _COLUMNS['rate-down'].header['right']

TUICOLUMNS['rate-down'] = RateDown


class RateUp(_COLUMNS['rate-up'], CellWidgetBase):
    style = Style(prefix='peerlist.rate-up', focusable=False,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['rate-up'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value > 0 else None

    @classmethod
    def set_unit(cls, unit):
        cls.header.original_widget.right = _COLUMNS['rate-up'].header['right']

TUICOLUMNS['rate-up'] = RateUp


class ETA(_COLUMNS['eta'], CellWidgetBase):
    style = Style(prefix='peerlist.eta', focusable=False,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['eta'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if bool(self.value) else None

TUICOLUMNS['eta'] = ETA


class EstimatedPeerRate(_COLUMNS['rate-est'], CellWidgetBase):
    style = Style(prefix='peerlist.rate-est', focusable=False,
                  extras=('header',), modes=('highlighted',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['rate-est'].header),
                           style.attrs('header'))

    def get_mode(self):
        return 'highlighted' if self.value > 0 else None

    @classmethod
    def set_unit(cls, unit):
        cls.header.original_widget.right = _COLUMNS['rate-est'].header['right']

TUICOLUMNS['rate-est'] = EstimatedPeerRate
