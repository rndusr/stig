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

"""TUI and CLI specs for torrent details sections"""

from ..logging import make_logger
log = make_logger(__name__)


def _torrent_size(size_total, size_final):
    if size_total == size_final:
        return '%s' % size_total
    else:
        return '%s (%s wanted)' % (size_total, size_final)

def _torrent_files(count_files, count_files_wanted):
    return '%d (%d wanted)' % (count_files, count_files_wanted)

def _torrent_pieces(count_pieces, size_pieces):
    return '%d * %s' % (count_pieces, size_pieces.with_unit)

def _status_uploaded(size_uploaded, size_total):
    return '%s (%d %%)' % (size_uploaded.with_unit, size_uploaded / size_total * 100)

def _status_downloaded(size_downloaded, size_final, size_left, percent_downloaded, eta):
    info = ['%s %%' % percent_downloaded]
    if percent_downloaded < 100:
        if eta:
            info.append('%s / %s left' % (size_left.with_unit, eta))
        else:
            info.append('%s left' % size_left.with_unit)
    return '%s (%s)' % (size_downloaded.with_unit, ', '.join(info))

def _status_completed(time_completed):
    if time_completed.in_future:
        return '%s (in %s)' % (time_completed, time_completed.delta)
    else:
        return '%s' % time_completed


SECTIONS = {
    'torrent':
    {'title': 'Torrent', 'width': 60, 'items': (
        {'label': 'Name',       'keys': ('name',)},
        {'label': 'ID',         'keys': ('id',)},
        {'label': 'Hash',       'keys': ('hash',)},
        {'label': 'Size',       'keys': ('size-total', 'size-final'), 'func': _torrent_size},
        {'label': 'Files',      'keys': ('count-files', 'count-files-wanted'), 'func': _torrent_files},
        {'label': 'Pieces',     'keys': ('count-pieces', 'size-piece'), 'func': _torrent_pieces},
        {'label': 'Private',    'keys': ('private',),
         'func': lambda private: ('yes (decentralized peer discovery is disabled for this torrent)'
                                  if private else
                                  'no (decentralized peer discovery allowed if enabled globally)')},
        {'label': 'Comment',    'keys': ('comment',)},
        {'label': 'Creator',    'keys': ('creator',)},
        {'label': 'Created',    'keys': ('time-created',)},
        {'label': 'Added',      'keys': ('time-added',)},
        {'label': 'Started',    'keys': ('time-started',)},
        {'label': 'Completed',  'keys': ('time-completed',), 'func': _status_completed},
        {'label': 'Active',     'keys': ('time-activity',)},
    )},

    'status':
    {'title': 'Status', 'width': 60, 'items': (
        {'label': 'Downloaded', 'func': _status_downloaded,
         'keys': ('size-downloaded', 'size-final', 'size-left', '%downloaded', 'timespan-eta')},
        {'label': 'Uploaded', 'func': _status_uploaded,
         'keys': ('size-uploaded', 'size-total')},
        # {'label': 'Available', 'func': _status_available,
        # 'keys': ('size-downloaded', 'size-final', 'size-left', '%downloaded', 'timespan-eta')},

        {'label': 'Seeding peers',     'keys': ('peers-seeding',)},
        {'label': 'Connected peers',   'keys': ('peers-connected',)},
        {'label': 'Uploading peers',   'keys': ('peers-uploading',)},
        {'label': 'Downloading peers', 'keys': ('peers-downloading',)},
    )},
}
