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

"""TUI and CLI specs for tracker list columns"""

from ..logging import make_logger
log = make_logger(__name__)

from . import (ColumnBase, _ensure_string_without_unit)


COLUMNS = {}


class TorrentName(ColumnBase):
    header = {'left': 'Torrent'}
    align = 'left'
    width = None
    may_have_wide_chars = True

    def get_value(self):
        return self.data['tname']

COLUMNS['torrent'] = TorrentName


class Tier(ColumnBase):
    header = {'left': 'Tier'}
    align = 'right'
    width = 4

    def get_value(self):
        return self.data['tier']

COLUMNS['tier'] = Tier


class Domain(ColumnBase):
    header = {'left': 'Domain'}
    align = 'left'
    width = None

    def get_value(self):
        return self.data['domain']

COLUMNS['domain'] = Domain


class AnnounceURL(ColumnBase):
    header = {'left': 'Announce'}
    align = 'left'
    width = None

    def get_value(self):
        return self.data['url-announce']

COLUMNS['announce'] = AnnounceURL


class ScrapeURL(ColumnBase):
    header = {'left': 'Scrape'}
    align = 'left'
    width = None

    def get_value(self):
        return self.data['url-scrape']

COLUMNS['scrape'] = ScrapeURL


class State(ColumnBase):
    header = {'left': 'State'}
    align = 'left'
    width = None

    def get_value(self):
        return self.data['state']

COLUMNS['state'] = State


class Error(ColumnBase):
    header = {'left': 'Error'}
    align = 'left'
    width = None

    def get_value(self):
        return self.data['error']

COLUMNS['error'] = Error
