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

from . import (ColumnBase, _ensure_hide_unit)

COLUMNS = {}
ALIASES = { 'mark'     : 'marked',
            'n'        : 'name',
            'dir'      : 'path',
            'st'       : 'status',
            'err'      : 'error',
            'up'       : 'uploaded',
            'dn'       : 'downloaded',
            '%dn'      : '%downloaded',
            'av'       : 'available',
            '%av'      : '%available',
            'sz'       : 'size',
            'prs'      : 'peers',
            'sds'      : 'seeds',
            'rto'      : 'ratio',
            'rup'      : 'rate-up',
            'rdn'      : 'rate-down',
            'lrup'     : 'limit-rate-up',
            'lrdn'     : 'limit-rate-down',
            'trk'      : 'tracker',
            'tcrt'     : 'created',
            'tadd'     : 'added',
            'tsta'     : 'started',
            'tact'     : 'activity',
            'tcmp'     : 'completed' }


class Marked(ColumnBase):
    interfaces = ('tui',)

COLUMNS['marked'] = Marked


class Id(ColumnBase):
    header = {'left': 'ID'}
    width = 4
    needed_keys = ('id',)
    align = 'right'

    def get_value(self):
        return self.data['id']

COLUMNS['id'] = Id


class Name(ColumnBase):
    header = {'left': 'Name'}
    width = None
    min_width = 5
    needed_keys = ('name',)
    align = 'left'
    may_have_wide_chars = True

    def get_value(self):
        return self.data['name']

COLUMNS['name'] = Name


import os
PATHSEP = os.sep
class Path(ColumnBase):
    header = {'left': 'Path'}
    width = None
    min_width = 10
    align = 'left'
    needed_keys = ('path',)
    may_have_wide_chars = True

    @staticmethod
    def _shorten_path(path, width):
        if width is None:
            return path
        elif width == 1:
            return '…'
        elif width <= 0:
            return ''

        # Remove characters from the end of the most toplevel directory until
        # there's only one left. Then do the same with the next level.
        #    /the/path/to/your/torrents
        #    /th/path/to/your/torrents
        #    /t/path/to/your/torrents
        #    /t/pat/to/your/torrents

        dirs = [d for d in path.split(PATHSEP) if d]
        calc_cur_len = lambda dirs: (sum(map(len, dirs)) +  # combined dir names
                                     len(dirs))             # path separators

        cur_len = calc_cur_len(dirs)
        while cur_len > width:
            for i,d in enumerate(dirs):
                if len(d) > 1:
                    dirs[i] = d[:-1]
                    break

            # Stop when every dir is one character long
            if cur_len <= len(dirs)*2:
                break

            cur_len = calc_cur_len(dirs)

        # Re-assemble shortened path
        path = PATHSEP + PATHSEP.join(dirs)

        # If "/t/p/t/y/t" is still too long, simply remove enough
        # characters from the front.
        if len(path) > width:
            excess = len(path) - width + 1
            path = '…' + path[excess:]

        return path

    def get_value(self):
        return self._from_cache(self._shorten_path,
                                self.data['path'].rstrip(PATHSEP),
                                self.width)

COLUMNS['path'] = Path


class Status(ColumnBase):
    header = {'left': 'Status'}
    width = 11
    min_width = 11
    needed_keys = ('status',)

    def get_value(self):
        return self.data['status'][0]

COLUMNS['status'] = Status


class Error(ColumnBase):
    header = {'left': 'Error'}
    width = ('weight', 300)
    min_width = 10
    needed_keys = ('error',)
    align = 'left'

    def get_value(self):
        return self.data['error']

COLUMNS['error'] = Error


class Uploaded(ColumnBase):
    header = {'left': 'Up', 'right': '?'}
    width = 6
    min_width = 6
    needed_keys = ('size-uploaded', 'size-downloaded')

    def get_value(self):
        return self._from_cache(_ensure_hide_unit, self.data['size-uploaded'])

    @classmethod
    def set_unit(cls, unit):
        cls.header['right'] = unit

COLUMNS['uploaded'] = Uploaded


class Downloaded(ColumnBase):
    header = {'left': 'Dn', 'right': '?'}
    width = 6
    min_width = 6
    needed_keys = ('size-downloaded', 'size-final')

    def get_value(self):
        return self._from_cache(_ensure_hide_unit, self.data['size-downloaded'])

    @classmethod
    def set_unit(cls, unit):
        cls.header['right'] = unit

COLUMNS['downloaded'] = Downloaded


class PercentDownloaded(ColumnBase):
    header = {'right': '%'}
    width = 4
    min_width = 4
    needed_keys = ('%verified', '%downloaded', '%metadata')

    @staticmethod
    def _get_value(verified, downloaded, metadata):
        if 0 < verified < 100:
            value = verified
        elif 0 < metadata < 100:
            value = metadata
        else:
            value = downloaded
        return _ensure_hide_unit(value)

    def get_value(self):
        t = self.data
        return self._from_cache(self._get_value, t['%verified'], t['%downloaded'], t['%metadata'])

COLUMNS['%downloaded'] = PercentDownloaded


class Available(ColumnBase):
    header = {'left': 'Avail', 'right': '?'}
    width = 7
    min_width = 7
    needed_keys = ('size-available', 'size-final', 'peers-seeding')

    @staticmethod
    def _get_value(size_final, size_available, peers_seeding):
        if peers_seeding > 0:
            return _ensure_hide_unit(size_final)
        else:
            return _ensure_hide_unit(size_available)

    def get_value(self):
        t = self.data
        return self._from_cache(self._get_value, t['size-final'], t['size-available'], t['peers-seeding'])

    @classmethod
    def set_unit(cls, unit):
        cls.header['right'] = unit

COLUMNS['available'] = Available


class PercentAvailable(ColumnBase):
    header = {'left': 'Avail', 'right': '%'}
    width = 7
    min_width = 7
    needed_keys = ('%available', 'peers-seeding')

    @staticmethod
    def _get_value(perc_available, peers_seeding):
        if peers_seeding > 0:
            return type(perc_available)(100, unit='%', hide_unit=True)
        else:
            return _ensure_hide_unit(perc_available)

    def get_value(self):
        t = self.data
        return self._from_cache(self._get_value, t['%available'], t['peers-seeding'])

COLUMNS['%available'] = PercentAvailable


class Size(ColumnBase):
    header = {'left': 'Size', 'right': '?'}
    width = 6
    min_width = 6
    needed_keys = ('size-final',)

    def get_value(self):
        return self._from_cache(_ensure_hide_unit, self.data['size-final'])

    @classmethod
    def set_unit(cls, unit):
        cls.header['right'] = unit

COLUMNS['size'] = Size


class Peers(ColumnBase):
    header = {'left': 'Peers'}
    width = 5
    min_width = 5
    needed_keys = ('peers-connected',)

    def get_value(self):
        return self.data['peers-connected']

COLUMNS['peers'] = Peers


class Seeds(ColumnBase):
    header = {'left': 'Seeds'}
    width = 5
    min_width = 5
    needed_keys = ('peers-seeding',)

    def get_value(self):
        return self.data['peers-seeding']

COLUMNS['seeds'] = Seeds


class Ratio(ColumnBase):
    header = {'left': 'Ratio'}
    width = 5
    min_width = 5
    needed_keys = ('ratio',)

    def get_value(self):
        return self.data['ratio']

COLUMNS['ratio'] = Ratio


class RateUp(ColumnBase):
    header = {'left': 'Up', 'right': '?/s'}
    width = 6
    min_width = 6
    needed_keys = ('rate-up',)

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
    needed_keys = ('rate-down',)

    def get_value(self):
        return self._from_cache(_ensure_hide_unit, self.data['rate-down'])

    @classmethod
    def set_unit(cls, unit):
        cls.header['right'] = '%s/s' % unit

COLUMNS['rate-down'] = RateDown


class LimitRateUp(ColumnBase):
    header = {'left': 'LmtUp', 'right': '?/s'}
    width = 9
    min_width = 9
    needed_keys = ('limit-rate-up',)

    def get_value(self):
        return self._from_cache(_ensure_hide_unit, self.data['limit-rate-up'])

    @classmethod
    def set_unit(cls, unit):
        cls.header['right'] = '%s/s' % unit

COLUMNS['limit-rate-up'] = LimitRateUp


class LimitRateDown(ColumnBase):
    header = {'left': 'LmtDn', 'right': '?/s'}
    width = 9
    min_width = 9
    needed_keys = ('limit-rate-down',)

    def get_value(self):
        return self._from_cache(_ensure_hide_unit, self.data['limit-rate-down'])

    @classmethod
    def set_unit(cls, unit):
        cls.header['right'] = '%s/s' % unit

COLUMNS['limit-rate-down'] = LimitRateDown


class Eta(ColumnBase):
    header = {'left': 'ETA'}
    width = 5
    min_width = 9
    needed_keys = ('timespan-eta',)

    def get_value(self):
        return self.data['timespan-eta']

COLUMNS['eta'] = Eta


class Tracker(ColumnBase):
    header = {'left': 'Tracker'}
    width = 10
    min_width = 5
    needed_keys = ('trackers',)
    align = 'left'

    def get_value(self):
        if len(self.data['trackers']) > 0:
            return self.data['trackers'][0]['url-announce'].domain
        else:
            return ''

COLUMNS['tracker'] = Tracker


class _TimeBase(ColumnBase):
    width = 10
    min_width = 10

class Created(_TimeBase):
    header = {'left': 'Created'}
    needed_keys = ('time-created',)

    def get_value(self):
        return self.data['time-created']

COLUMNS['created'] = Created

class Added(_TimeBase):
    header = {'left': 'Added'}
    needed_keys = ('time-added',)

    def get_value(self):
        return self.data['time-added']

COLUMNS['added'] = Added

class Started(_TimeBase):
    header = {'left': 'Started'}
    needed_keys = ('time-started',)

    def get_value(self):
        return self.data['time-started']

COLUMNS['started'] = Started

class Activity(_TimeBase):
    header = {'left': 'Activity'}
    needed_keys = ('time-activity',)

    def get_value(self):
        return self.data['time-activity']

COLUMNS['activity'] = Activity

class Completed(_TimeBase):
    header = {'left': 'Completed'}
    needed_keys = ('time-completed',)

    def get_value(self):
        return self.data['time-completed']

COLUMNS['completed'] = Completed
