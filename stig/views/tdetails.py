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


def _torrent_size_hr(t):
    if t['size-total'] == t['size-final']:
        return '%s' % t['size-total']
    else:
        return '%s (%s wanted)' % (t['size-total'], t['size-final'])

def _torrent_size_mr(t):
    return '%d\t%d' % (t['size-total'], t['size-final'])


def _torrent_files_hr(t):
    return '%d (%d wanted)' % (t['count-files'], t['count-files-wanted'])

def _torrent_files_mr(t):
    return '%d\t%d' % (t['count-files'], t['count-files-wanted'])


def _torrent_pieces_hr(t):
    return '%d * %s' % (t['count-pieces'], t['size-piece'].with_unit)

def _torrent_pieces_mr(t):
    return '%d\t%d' % (t['count-pieces'], t['size-piece'])


def _torrent_private_hr(t):
    return ('yes (decentralized peer discovery is disabled for this torrent)'
            if t['private'] else
            'no (decentralized peer discovery allowed if enabled globally)')

def _torrent_private_mr(t):
    return 'yes' if t['private'] else 'no'


def _status_uploaded_hr(t):
    return '%s (%.2f %%)' % (t['size-uploaded'].with_unit, t['%uploaded'])

def _status_uploaded_mr(t):
    return '%d\t%f' % (t['size-uploaded'], t['%uploaded'] / 100)


def _status_downloaded_hr(t):
    info = ['%.2f %%' % t['%downloaded']]
    if t['%downloaded'] < 100:
        if t['timespan-eta']:
            info.append('%s / %s left' % (t['size-left'].with_unit, t['timespan-eta']))
        else:
            info.append('%s left' % t['size-left'].with_unit)
    return '%s (%s)' % (t['size-downloaded'].with_unit, ', '.join(info))

def _status_downloaded_mr(t):
    return '%d\t%f\t%d\t%d' % (t['size-downloaded'],
                               t['%downloaded'] / 100, t['size-left'],
                               t['timespan-eta'])


def _status_available_hr(t):
    return '%s (%.2f %%)' % (t['size-available'].with_unit, t['%available'])

def _status_available_mr(t):
    return '%d\t%f' % (t['size-available'], t['%available'])


def _status_completed_hr(t):
    if t['time-completed'].in_future:
        return '%s (in %s)' % (t['time-completed'].full, t['time-completed'].delta)
    else:
        return '%s' % t['time-completed'].full

def _status_completed_mr(t):
    return '%d' % t['time-completed']


def _status_isolated_hr(t):
    status = t['status']
    return ('yes (torrent can\'t discover new peers)'
            if status.ISOLATED in status else
            'no (torrent can discover new peers)')

def _status_isolated_mr(t):
    status = t['status']
    return 'yes' if status.ISOLATED in status else 'no'


class Item():
    def __init__(self, label, needed_keys, human_readable=None, machine_readable=None):
        self.label = label
        self.needed_keys = needed_keys
        if human_readable is None:
            self.human_readable = lambda torrent, key=needed_keys[0]: str(torrent[key])
        else:
            self.human_readable = human_readable
        if machine_readable is None:
            self.machine_readable = self.human_readable
        else:
            self.machine_readable = machine_readable

SECTIONS = (
    {'title': 'Torrent', 'width': 60, 'items': (
        Item('Name',       ('name',)),
        Item('ID',         ('id',)),
        Item('Hash',       ('hash',)),
        Item('Size',       ('size-total', 'size-final'), _torrent_size_hr, _torrent_size_mr),
        Item('Files',      ('count-files', 'count-files-wanted'), _torrent_files_hr, _torrent_files_mr),
        Item('Pieces',     ('count-pieces', 'size-piece'), _torrent_pieces_hr, _torrent_pieces_mr),
        Item('Private',    ('private',), _torrent_private_hr, _torrent_private_mr),
        Item('Comment',    ('comment',)),
        Item('Creator',    ('creator',)),
        Item('Created',    ('time-created',),   lambda t: t['time-created'].full,  lambda t: int(t['time-created'])),
        Item('Added',      ('time-added',),     lambda t: t['time-added'].full,    lambda t: int(t['time-added'])),
        Item('Started',    ('time-started',),   lambda t: t['time-started'].full,  lambda t: int(t['time-started'])),
        Item('Completed',  ('time-completed',), _status_completed_hr, _status_completed_mr),
        Item('Active',     ('time-activity',),  lambda t: t['time-activity'].full, lambda t: int(t['time-activity'])),
    )},

    {'title': 'Status', 'width': 60, 'items': (
        Item('Downloaded', ('size-downloaded', 'size-left', '%downloaded', 'timespan-eta'),
          _status_downloaded_hr, _status_downloaded_mr),
        Item('Uploaded', ('size-uploaded', 'size-total', '%uploaded'),
             _status_uploaded_hr, _status_uploaded_mr),
        Item('Availability', ('%available', 'size-available'),
             _status_available_hr, _status_available_mr),

        Item('Isolated',          ('status',), _status_isolated_hr, _status_isolated_mr),
        Item('Seeding peers',     ('peers-seeding',)),
        Item('Connected peers',   ('peers-connected',)),
        Item('Uploading peers',   ('peers-uploading',)),
        Item('Downloading peers', ('peers-downloading',)),
    )},
)
