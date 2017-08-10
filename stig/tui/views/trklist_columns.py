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
from ...views.trackerlist import COLUMNS as _COLUMNS


TUICOLUMNS = {}

class TorrentName(_COLUMNS['torrent'], CellWidgetBase):
    width = ('weight', 50)
    style = Style(prefix='trackerlist.torrent', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['torrent'].header),
                           style.attrs('header'))

TUICOLUMNS['torrent'] = TorrentName


class Tier(_COLUMNS['tier'], CellWidgetBase):
    style = Style(prefix='trackerlist.tier', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['tier'].header),
                           style.attrs('header'))

TUICOLUMNS['tier'] = Tier


class Domain(_COLUMNS['domain'], CellWidgetBase):
    width = ('weight', 20)
    style = Style(prefix='trackerlist.domain', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['domain'].header),
                           style.attrs('header'))

TUICOLUMNS['domain'] = Domain


class AnnounceURL(_COLUMNS['announce'], CellWidgetBase):
    width = ('weight', 100)
    style = Style(prefix='trackerlist.announce', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['announce'].header),
                           style.attrs('header'))

TUICOLUMNS['announce'] = AnnounceURL


class ScrapeURL(_COLUMNS['scrape'], CellWidgetBase):
    width = ('weight', 100)
    style = Style(prefix='trackerlist.scrape', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['scrape'].header),
                           style.attrs('header'))

TUICOLUMNS['scrape'] = ScrapeURL


class State(_COLUMNS['state'], CellWidgetBase):
    style = Style(prefix='trackerlist.state', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['state'].header),
                           style.attrs('header'))

TUICOLUMNS['state'] = State


class Error(_COLUMNS['error'], CellWidgetBase):
    width = ('weight', 100)
    style = Style(prefix='trackerlist.error', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['error'].header),
                           style.attrs('header'))

TUICOLUMNS['error'] = Error
