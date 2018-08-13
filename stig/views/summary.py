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

"""TUI and CLI specs for torrent summary sections"""

from ..logging import make_logger
log = make_logger(__name__)

from functools import partial


def _size_hr(t):
    if t['size-total'] == t['size-final']:
        return '%s' % t['size-total'].with_unit
    else:
        return '%s (%s wanted)' % (t['size-total'].with_unit, t['size-final'].with_unit)

def _size_mr(t):
    return '%d\t%d' % (t['size-total'], t['size-final'])


def _limit_rate_hr(direction, t):
    return str(t['limit-rate-' + direction])

def _limit_rate_mr(direction, t):
    limit = t['limit-rate-' + direction]
    return int(limit) if limit < float('inf') else str(limit)


def _file_counts(t):
    files = tuple(t['files'].files)
    all_files = len(files)
    wanted_files = sum(1 for f in files if f['is-wanted'])
    return (all_files, wanted_files)

def _files_hr(t):
    return '%d (%d wanted)' % _file_counts(t)

def _files_mr(t):
    return '%d\t%d' % _file_counts(t)


def _pieces_hr(t):
    return '%d * %s' % (t['count-pieces'], t['size-piece'].with_unit)

def _pieces_mr(t):
    return '%d\t%d' % (t['count-pieces'], t['size-piece'])


def _private_hr(t):
    return ('yes (decentralized peer discovery is disabled for this torrent)'
            if t['private'] else
            'no (decentralized peer discovery allowed if enabled globally)')

def _private_mr(t):
    return 'yes' if t['private'] else 'no'


def _status_hr(t):
    return ', '.join(t['status'])

def _status_mr(t):
    return ','.join(t['status'])


def _uploaded_hr(t):
    return '%s (%.2f %%)' % (t['size-uploaded'].with_unit, t['%uploaded'])

def _uploaded_mr(t):
    return '%d\t%f' % (t['size-uploaded'], t['%uploaded'] / 100)


def _downloaded_hr(t):
    info = ['%.2f %%' % t['%downloaded']]
    if t['%downloaded'] < 100:
        if t['timespan-eta']:
            info.append('%s / %s left' % (t['size-left'].with_unit, t['timespan-eta']))
        else:
            info.append('%s left' % t['size-left'].with_unit)
    return '%s (%s)' % (t['size-downloaded'].with_unit, ', '.join(info))

def _downloaded_mr(t):
    return '%d\t%f\t%d\t%d' % (t['size-downloaded'],
                               t['%downloaded'] / 100, t['size-left'],
                               t['timespan-eta'])


def _ratio_hr(t):
    ratio = t['ratio']
    if ratio == ratio.INFINITE:
        return 'infinite'
    elif ratio == ratio.NOT_APPLICABLE:
        return 'not applicable'
    else:
        return '%g' % ratio
_ratio_mr = _ratio_hr


def _available_hr(t):
    return '%s (%.2f %%)' % (t['size-available'].with_unit, t['%available'])

def _available_mr(t):
    return '%d\t%f' % (t['size-available'], t['%available'])


def _isolated_hr(t):
    status = t['status']
    return ('yes (torrent can\'t discover new peers)'
            if status.ISOLATED in status else
            'no (torrent can discover new peers)')

def _isolated_mr(t):
    status = t['status']
    return 'yes' if status.ISOLATED in status else 'no'


def _date_hr(key, t):
    date = t[key]
    if date.is_known:
        delta = date.timedelta
        if abs(delta) < 5:
            return 'now'
        else:
            return '%s (%s)' % (date.full, delta.with_preposition)
    else:
        return date.full

def _date_mr(key, t):
    date = t[key]
    return '%d\t%d' % (date, date.timedelta)


def _timespan_hr(key, t):
    timespan = t[key]
    return str(timespan) if timespan != 0 else '0'

def _timespan_mr(key, t):
    timespan = t[key]
    return int(timespan)


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
        Item('Name',
             needed_keys=('name',)),
        Item('ID',
             needed_keys=('id',)),
        Item('Hash',
             needed_keys=('hash',)),
        Item('Size',
             needed_keys=('size-total', 'size-final'),
             human_readable=_size_hr,
             machine_readable=_size_mr),
        Item('Files',
             needed_keys=('files',),
             human_readable=_files_hr,
             machine_readable=_files_mr),
        Item('Pieces',
             needed_keys=('count-pieces', 'size-piece'),
             human_readable=_pieces_hr,
             machine_readable=_pieces_mr),
        Item('Private',
             needed_keys=('private',),
             human_readable=_private_hr,
             machine_readable=_private_mr),
        Item('Comment',
             needed_keys=('comment',)),
        Item('Creator',
             needed_keys=('creator',)),
    )},

    {'title': 'Status', 'width': 51, 'items': (
        Item('State',
             needed_keys=('status',),
             human_readable=_status_hr,
             machine_readable=_status_mr),
        Item('Location',
             needed_keys=('path',),),
        Item('Available',
             needed_keys=('%available', 'size-available'),
             human_readable=_available_hr,
             machine_readable=_available_mr),
        Item('Downloaded',
             needed_keys=('size-downloaded', 'size-left', '%downloaded', 'timespan-eta'),
             human_readable=_downloaded_hr,
             machine_readable=_downloaded_mr),
        Item('Uploaded',
             needed_keys=('size-uploaded', 'size-total', '%uploaded'),
             human_readable=_uploaded_hr,
             machine_readable=_uploaded_mr),
        Item('Ratio',
             needed_keys=('ratio',),
             human_readable=_ratio_hr,
             machine_readable=_ratio_mr),
        Item('Isolated',
             needed_keys=('status',),
             human_readable=_isolated_hr,
             machine_readable=_isolated_mr),
        Item('Error',
             needed_keys=('error',)),
    )},

    {'title': 'Limits', 'width': 24, 'items': (
        Item('Upload rate',
             needed_keys=('limit-rate-up',),
             human_readable=partial(_limit_rate_hr, 'up'),
             machine_readable=partial(_limit_rate_mr, 'up')),
        Item('Download rate',
             needed_keys=('limit-rate-down',),
             human_readable=partial(_limit_rate_hr, 'down'),
             machine_readable=partial(_limit_rate_mr, 'down')),
    )},

    {'title': 'Peers', 'width': 18, 'items': (
        Item('Seeding',
             needed_keys=('peers-seeding',)),
        Item('Connected',
             needed_keys=('peers-connected',)),
        Item('Uploading',
             needed_keys=('peers-uploading',)),
        Item('Downloading',
             needed_keys=('peers-downloading',)),
    )},

    {'title': 'Dates and Times', 'width': 41, 'items': (
        Item('Created',
             needed_keys=('time-created',),
             human_readable=partial(_date_hr, 'time-created'),
             machine_readable=partial(_date_mr, 'time-created')),
        Item('Added',
             needed_keys=('time-added',),
             human_readable=partial(_date_hr, 'time-added'),
             machine_readable=partial(_date_mr, 'time-added')),
        Item('Started',
             needed_keys=('time-started',),
             human_readable=partial(_date_hr, 'time-started'),
             machine_readable=partial(_date_mr, 'time-started')),
        Item('Completed',
             needed_keys=('time-completed',),
             human_readable=partial(_date_hr, 'time-completed'),
             machine_readable=partial(_date_mr, 'time-completed')),
        Item('Active',
             needed_keys=('time-activity',),
             human_readable=partial(_date_hr, 'time-activity'),
             machine_readable=partial(_date_mr, 'time-activity')),

        # Disabled because Transmission returns incorrect time span
        # Item('Seeding',
        #      needed_keys=('timespan-seeding',),
        #      human_readable=partial(_timespan_hr, 'timespan-seeding'),
        #      machine_readable=partial(_timespan_mr, 'timespan-seeding')),
        Item('Downloading',
             needed_keys=('timespan-downloading',),
             human_readable=partial(_timespan_hr, 'timespan-downloading'),
             machine_readable=partial(_timespan_mr, 'timespan-downloading')),
    )},
)
