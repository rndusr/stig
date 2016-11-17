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

from ..logging import make_logger
log = make_logger(__name__)


class _ColumnBase():
    header = {'left': '', 'right': ''}
    width = None
    align = 'right'
    needed_keys = ()

    def __init__(self, torrent=None):
        self.torrent = torrent
        super().__init__()

    def get_value(self):
        raise NotImplementedError()

    def get_raw(self):
        return self.get_value()

    def get_string(self):
        """Return `get_value` as spaced and aligned string

        If the `width` attribute is not set to None, expand or shrink and
        align the returned string (`align` attribute must be 'left' or
        'right').
        """
        text = str(self.get_value())
        if self.width is None:
            return text
        else:
            text = self._crop(text)

        if self.align == 'right':
            return text.rjust(self.width)
        elif self.align == 'left':
            return text.ljust(self.width)
        else:
            raise RuntimeError("Not 'left' or 'right': {!r}".format(self.align))

    def _crop(self, string):
        return string[:self.width]

    def __repr__(self):
        return '<{} {}>'.format(type(self).__name__, self.get_value())


COLUMNS = {}

import os
PATHSEP = os.sep
class Path(_ColumnBase):
    header = {'left': 'Path'}
    width = None
    align = 'left'
    needed_keys = ('path',)

    def get_value(self):
        path = self.torrent['path'].rstrip(PATHSEP)
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
        return path

COLUMNS['path'] = Path


class PeersConnected(_ColumnBase):
    header = {'left': 'Conn'}
    width = 5
    needed_keys = ('peers-connected',)

    def get_value(self):
        return self.torrent['peers-connected']

    def get_raw(self):
        return int(self.get_value())

COLUMNS['peers-connected'] = PeersConnected


class PeersSeeding(_ColumnBase):
    header = {'left': 'Seeds'}
    width = 5
    needed_keys = ('peers-seeding',)

    def get_value(self):
        return self.torrent['peers-seeding']

    def get_raw(self):
        return int(self.get_value())

COLUMNS['peers-seeding'] = PeersSeeding


class Progress(_ColumnBase):
    header = {'right': '%'}
    width = 5
    needed_keys = ('%verified', '%downloaded', '%metadata')

    def get_value(self):
        t = self.torrent
        v, c, m = (t['%verified'], t['%downloaded'], t['%metadata'])
        if 0 < v < 100:
            return v
        elif 0 < m < 100:
            return m
        else:
            return c

    def get_raw(self):
        return float(self.get_value()) / 100

COLUMNS['progress'] = Progress


class Ratio(_ColumnBase):
    header = {'left': 'Ratio'}
    width = 5
    needed_keys = ('ratio',)

    def get_value(self):
        return self.torrent['ratio']

    def get_raw(self):
        return float(self.get_value())

COLUMNS['ratio'] = Ratio


class Size(_ColumnBase):
    header = {'left': 'Size', 'right': '?'}
    width = 6
    needed_keys = ('size-final',)

    def get_value(self):
        return self.torrent['size-final']

    def get_raw(self):
        return int(self.get_value())

    @classmethod
    def set_unit(cls, unit):
        cls.header['right'] = unit

COLUMNS['size'] = Size


class Downloaded(_ColumnBase):
    header = {'left': 'Dn', 'right': '?'}
    width = 6
    needed_keys = ('size-downloaded', 'size-final')

    def get_value(self):
        return self.torrent['size-downloaded']

    def get_raw(self):
        return int(self.get_value())

    @classmethod
    def set_unit(cls, unit):
        cls.header['right'] = unit

COLUMNS['downloaded'] = Downloaded


class Uploaded(_ColumnBase):
    header = {'left': 'Up', 'right': '?'}
    width = 6
    needed_keys = ('size-uploaded', 'size-downloaded')

    def get_value(self):
        return self.torrent['size-uploaded']

    def get_raw(self):
        return int(self.get_value())

    @classmethod
    def set_unit(cls, unit):
        cls.header['right'] = unit

COLUMNS['uploaded'] = Uploaded


class RateDown(_ColumnBase):
    header = {'left': 'Dn', 'right': '?/s'}
    width = 6
    needed_keys = ('rate-down',)

    def get_value(self):
        return self.torrent['rate-down']

    def get_raw(self):
        return int(self.get_value())

    @classmethod
    def set_unit(cls, unit):
        cls.header['right'] = '%s/s' % unit

COLUMNS['rate-down'] = RateDown


class RateUp(_ColumnBase):
    header = {'left': 'Up', 'right': '?/s'}
    width = 6
    needed_keys = ('rate-up',)

    def get_value(self):
        return self.torrent['rate-up']

    def get_raw(self):
        return int(self.get_value())

    @classmethod
    def set_unit(cls, unit):
        cls.header['right'] = '%s/s' % unit

COLUMNS['rate-up'] = RateUp


class EtaComplete(_ColumnBase):
    header = {'left': 'ETA'}
    width = 3
    needed_keys = ('timespan-eta',)

    def get_value(self):
        return self.torrent['timespan-eta']

    def get_raw(self):
        return int(self.get_value())

COLUMNS['eta'] = EtaComplete


class TorrentName(_ColumnBase):
    header = {'left': 'Name'}
    width = None
    needed_keys = ('name',)
    align = 'left'

    def get_value(self):
        return self.torrent['name']

COLUMNS['name'] = TorrentName
