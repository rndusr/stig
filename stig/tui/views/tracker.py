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
from ...views.tracker import COLUMNS as _COLUMNS


TUICOLUMNS = {}

class Torrent(_COLUMNS['torrent'], CellWidgetBase):
    width = ('weight', 50)
    style = Style(prefix='trackerlist.torrent', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['torrent'].header),
                           style.attrs('header'))

TUICOLUMNS['torrent'] = Torrent


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


class AnnounceURL(_COLUMNS['url-announce'], CellWidgetBase):
    width = ('weight', 100)
    style = Style(prefix='trackerlist.url-announce', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['url-announce'].header),
                           style.attrs('header'))

TUICOLUMNS['url-announce'] = AnnounceURL


class ScrapeURL(_COLUMNS['url-scrape'], CellWidgetBase):
    width = ('weight', 100)
    style = Style(prefix='trackerlist.url-scrape', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['url-scrape'].header),
                           style.attrs('header'))

TUICOLUMNS['url-scrape'] = ScrapeURL


class Status(_COLUMNS['status'], CellWidgetBase):
    style = Style(prefix='trackerlist.status', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['status'].header),
                           style.attrs('header'))

TUICOLUMNS['status'] = Status


class Error(_COLUMNS['error'], CellWidgetBase):
    width = ('weight', 100)
    style = Style(prefix='trackerlist.error', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['error'].header),
                           style.attrs('header'))

TUICOLUMNS['error'] = Error


class ErrorAnnounce(_COLUMNS['error-announce'], CellWidgetBase):
    width = ('weight', 100)
    style = Style(prefix='trackerlist.error-announce', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['error-announce'].header),
                           style.attrs('header'))

TUICOLUMNS['error-announce'] = ErrorAnnounce


class ErrorScrape(_COLUMNS['error-scrape'], CellWidgetBase):
    width = ('weight', 100)
    style = Style(prefix='trackerlist.error-scrape', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['error-scrape'].header),
                           style.attrs('header'))

TUICOLUMNS['error-scrape'] = ErrorScrape


class Downloads(_COLUMNS['downloads'], CellWidgetBase):
    style = Style(prefix='trackerlist.downloads', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['downloads'].header),
                           style.attrs('header'))

TUICOLUMNS['downloads'] = Downloads


class Leeches(_COLUMNS['leeches'], CellWidgetBase):
    style = Style(prefix='trackerlist.leeches', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['leeches'].header),
                           style.attrs('header'))

TUICOLUMNS['leeches'] = Leeches


class Seeds(_COLUMNS['seeds'], CellWidgetBase):
    style = Style(prefix='trackerlist.seeds', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['seeds'].header),
                           style.attrs('header'))

TUICOLUMNS['seeds'] = Seeds


class LastAnnounce(_COLUMNS['last-announce'], CellWidgetBase):
    style = Style(prefix='trackerlist.last-announce', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['last-announce'].header),
                           style.attrs('header'))

TUICOLUMNS['last-announce'] = LastAnnounce


class NextAnnounce(_COLUMNS['next-announce'], CellWidgetBase):
    style = Style(prefix='trackerlist.next-announce', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['next-announce'].header),
                           style.attrs('header'))

TUICOLUMNS['next-announce'] = NextAnnounce


class LastScrape(_COLUMNS['last-scrape'], CellWidgetBase):
    style = Style(prefix='trackerlist.last-scrape', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['last-scrape'].header),
                           style.attrs('header'))

TUICOLUMNS['last-scrape'] = LastScrape


class NextScrape(_COLUMNS['next-scrape'], CellWidgetBase):
    style = Style(prefix='trackerlist.next-scrape', focusable=True,
                  extras=('header',))
    header = urwid.AttrMap(ColumnHeaderWidget(**_COLUMNS['next-scrape'].header),
                           style.attrs('header'))

TUICOLUMNS['next-scrape'] = NextScrape
