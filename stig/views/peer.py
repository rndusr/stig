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

from . import (ColumnBase, _ensure_hide_unit)


COLUMNS = {}
ALIASES = { 'cl'   : 'client',
            'cn'   : 'country',
            '%dn'  : '%downloaded',
            'rup'  : 'rate-up',
            'rdn'  : 'rate-down',
            're'   : 'rate-est' }


class Torrent(ColumnBase):
    header = {'left': 'Torrent'}
    align = 'left'
    width = None
    min_width = 7
    may_have_wide_chars = True

    def get_value(self):
        return self.data['tname']

COLUMNS['torrent'] = Torrent


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


class Host(ColumnBase):
    header = {'left': 'Host'}
    align = 'right'
    width = None
    min_width = 4

    def get_value(self):
        return self.data['ip']

    def get_cli_value(self):
        from ..main import localcfg
        if localcfg['reverse-dns']:
            from ..client import rdns
            return rdns.gethostbyaddr(self.data['ip'])
        return self.data['ip']

COLUMNS['host'] = Host


class Port(ColumnBase):
    header = {'left': 'Port'}
    align = 'right'
    width = 5
    min_width = 5

    def get_value(self):
        return self.data['port']

COLUMNS['port'] = Port


class PercentDownloaded(ColumnBase):
    header = {'right': '%'}
    width = 4
    min_width = 4

    def get_value(self):
        return self._from_cache(_ensure_hide_unit, self.data['%downloaded'])

COLUMNS['%downloaded'] = PercentDownloaded


class RateUp(ColumnBase):
    header = {'left': 'Up', 'right': '?/s'}
    width = 6
    min_width = 6

    def get_value(self):
        return self._from_cache(_ensure_hide_unit, self.data['rate-up'])

    @classmethod
    def set_unit(cls, unit):
        cls.header['right'] = '%s/s' % unit

COLUMNS['rate-up'] = RateUp


class RateDown(ColumnBase):
    header = {'left': 'Dn', 'right': '?/s'}
    width = 6
    min_width = 6

    def get_value(self):
        return self._from_cache(_ensure_hide_unit, self.data['rate-down'])

    @classmethod
    def set_unit(cls, unit):
        cls.header['right'] = '%s/s' % unit

COLUMNS['rate-down'] = RateDown


class ETA(ColumnBase):
    header = {'left': 'ETA'}
    width = 5
    min_width = 3

    def get_value(self):
        return self.data['eta']

COLUMNS['eta'] = ETA


class RateEst(ColumnBase):
    header = {'left': 'Est', 'right': '?/s'}
    width = 7
    min_width = 7

    def get_value(self):
        return self._from_cache(_ensure_hide_unit, self.data['rate-est'])

    @classmethod
    def set_unit(cls, unit):
        cls.header['right'] = '%s/s' % unit

COLUMNS['rate-est'] = RateEst
