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

"""TUI and CLI specs for peer list columns"""

from ..logging import make_logger
log = make_logger(__name__)

from . import (ColumnBase, _ensure_string_without_unit)


COLUMNS = {}
ALIASES = { '%'    : 'progress',
            'rdn'  : 'rate-down',
            'rup'  : 'rate-up',
            'rest' : 'rate-est',
            'name' : 'torrent' }


class TorrentName(ColumnBase):
    header = {'left': 'Torrent'}
    align = 'left'
    width = None
    min_width = 7
    may_have_wide_chars = True

    def get_value(self):
        return self.data['tname']

COLUMNS['torrent'] = TorrentName


class Client(ColumnBase):
    header = {'left': 'Client'}
    align = 'left'
    width = None
    min_width = 6

    def get_value(self):
        return self.data['client']

COLUMNS['client'] = Client


class Country(ColumnBase):
    header = {'left': 'Country'}
    align = 'right'
    width = 7
    min_width = 7

    def get_value(self):
        return self.data['country']

COLUMNS['country'] = Country


class IPAddress(ColumnBase):
    header = {'left': 'IP'}
    align = 'right'
    width = 15
    min_width = 15

    def get_value(self):
        return self.data['ip']

COLUMNS['ip'] = IPAddress


class Port(ColumnBase):
    header = {'left': 'Port'}
    align = 'right'
    width = 5
    min_width = 5

    def get_value(self):
        return self.data['port']

COLUMNS['port'] = Port


class Progress(ColumnBase):
    header = {'right': '%'}
    width = 4
    min_width = 4

    def get_value(self):
        return self._from_cache(_ensure_string_without_unit, self.data['progress'])

COLUMNS['progress'] = Progress


class RateDown(ColumnBase):
    header = {'left': 'Dn', 'right': '?/s'}
    width = 6
    min_width = 6

    def get_value(self):
        return self._from_cache(_ensure_string_without_unit, self.data['rate-down'])

    def get_raw(self):
        return int(self.get_value())

    @classmethod
    def set_unit(cls, unit):
        cls.header['right'] = '%s/s' % unit

COLUMNS['rate-down'] = RateDown


class RateUp(ColumnBase):
    header = {'left': 'Up', 'right': '?/s'}
    width = 6
    min_width = 6

    def get_value(self):
        return self._from_cache(_ensure_string_without_unit, self.data['rate-up'])

    def get_raw(self):
        return int(self.get_value())

    @classmethod
    def set_unit(cls, unit):
        cls.header['right'] = '%s/s' % unit

COLUMNS['rate-up'] = RateUp


class ETA(ColumnBase):
    header = {'left': 'ETA'}
    width = 5
    min_width = 3

    def get_value(self):
        return self.data['eta']

    def get_raw(self):
        return int(self.get_value())

COLUMNS['eta'] = ETA


class EstimatedPeerRate(ColumnBase):
    header = {'left': 'Est', 'right': '?/s'}
    width = 7
    min_width = 7

    def get_value(self):
        return self._from_cache(_ensure_string_without_unit, self.data['rate-est'])

    def get_raw(self):
        return int(self.get_value())

    @classmethod
    def set_unit(cls, unit):
        cls.header['right'] = '%s/s' % unit

COLUMNS['rate-est'] = EstimatedPeerRate
