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

"""TUI and CLI specs for torrent list columns"""

from . import ColumnBase

COLUMNS = {}

import os
PATHSEP = os.sep
class Path(ColumnBase):
    header = {'left': 'Path'}
    width = None
    align = 'left'
    needed_keys = ('path',)

    def get_value(self):
        path = self.data['path'].rstrip(PATHSEP)
        if self.width is None:
            return path

        # Remove characters from the end of the most toplevel directory
        # until there's only one left. Then do the same with the next
        # level.
        # /the/path/to/your/torrents
        # -> /th/path/to/your/torrents
        # -> /t/path/to/your/torrents
        # -> /t/pat/to/your/torrents
        while len(path) > self.width:
            dirs = [d for d in path.split(PATHSEP) if d]
            for i,d in enumerate(dirs):
                if len(d) > 1:
                    dirs[i] = d[:-1]
                    break
            path = PATHSEP + PATHSEP.join(dirs)
            if len(path) <= len(dirs)*2:
                break  # Each dir is now exactly one character long.

        # If "/t/p/t/y/t" is still too long, simply remove enough characters
        # from the front.
        if len(path) > self.width:
            excess = len(path) - self.width + 1
            path = '…' + path[excess:]

        return path

COLUMNS['path'] = Path


class PeersConnected(ColumnBase):
    header = {'left': 'Conn'}
    width = 5
    needed_keys = ('peers-connected',)

    def get_value(self):
        return self.data['peers-connected']

    def get_raw(self):
        return int(self.get_value())

COLUMNS['peers-connected'] = PeersConnected


class PeersSeeding(ColumnBase):
    header = {'left': 'Seeds'}
    width = 5
    needed_keys = ('peers-seeding',)

    def get_value(self):
        return self.data['peers-seeding']

    def get_raw(self):
        return int(self.get_value())

COLUMNS['peers-seeding'] = PeersSeeding


class Progress(ColumnBase):
    header = {'right': '%'}
    width = 4
    needed_keys = ('%verified', '%downloaded', '%metadata')

    def get_value(self):
        t = self.data
        v, d, m = (t['%verified'], t['%downloaded'], t['%metadata'])
        if 0 < v < 100:
            return v
        elif 0 < m < 100:
            return m
        else:
            return d

    def get_raw(self):
        return float(self.get_value()) / 100

COLUMNS['progress'] = Progress


class Ratio(ColumnBase):
    header = {'left': 'Ratio'}
    width = 5
    needed_keys = ('ratio',)

    def get_value(self):
        return self.data['ratio']

    def get_raw(self):
        return float(self.get_value())

COLUMNS['ratio'] = Ratio


class Size(ColumnBase):
    header = {'left': 'Size', 'right': '?'}
    width = 6
    needed_keys = ('size-final',)

    def get_value(self):
        return self.data['size-final']

    def get_raw(self):
        return int(self.get_value())

    @classmethod
    def set_unit(cls, unit):
        cls.header['right'] = unit

COLUMNS['size'] = Size


class Downloaded(ColumnBase):
    header = {'left': 'Dn', 'right': '?'}
    width = 6
    needed_keys = ('size-downloaded', 'size-final')

    def get_value(self):
        return self.data['size-downloaded']

    def get_raw(self):
        return int(self.get_value())

    @classmethod
    def set_unit(cls, unit):
        cls.header['right'] = unit

COLUMNS['downloaded'] = Downloaded


class Uploaded(ColumnBase):
    header = {'left': 'Up', 'right': '?'}
    width = 6
    needed_keys = ('size-uploaded', 'size-downloaded')

    def get_value(self):
        return self.data['size-uploaded']

    def get_raw(self):
        return int(self.get_value())

    @classmethod
    def set_unit(cls, unit):
        cls.header['right'] = unit

COLUMNS['uploaded'] = Uploaded


class RateDown(ColumnBase):
    header = {'left': 'Dn', 'right': '?/s'}
    width = 6
    needed_keys = ('rate-down',)

    def get_value(self):
        return self.data['rate-down']

    def get_raw(self):
        return int(self.get_value())

    @classmethod
    def set_unit(cls, unit):
        cls.header['right'] = '%s/s' % unit

COLUMNS['rate-down'] = RateDown


class RateUp(ColumnBase):
    header = {'left': 'Up', 'right': '?/s'}
    width = 6
    needed_keys = ('rate-up',)

    def get_value(self):
        return self.data['rate-up']

    def get_raw(self):
        return int(self.get_value())

    @classmethod
    def set_unit(cls, unit):
        cls.header['right'] = '%s/s' % unit

COLUMNS['rate-up'] = RateUp


class EtaComplete(ColumnBase):
    header = {'left': 'ETA'}
    width = 3
    needed_keys = ('timespan-eta',)

    def get_value(self):
        return self.data['timespan-eta']

    def get_raw(self):
        return int(self.get_value())

COLUMNS['eta'] = EtaComplete


class TorrentName(ColumnBase):
    header = {'left': 'Name'}
    width = None
    needed_keys = ('name',)
    align = 'left'

    def get_value(self):
        return self.data['name']

COLUMNS['name'] = TorrentName
