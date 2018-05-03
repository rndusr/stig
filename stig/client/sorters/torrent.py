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

from ...logging import make_logger
log = make_logger(__name__)

from . import (SortSpecBase, SorterBase)

class _SortSpec(SortSpecBase):
    def __init__(self, *args, description='', needed_keys=(), **kwargs):
        description = 'Sort torrents by %s' % description
        super().__init__(*args, description=description, **kwargs)
        self.needed_keys = needed_keys


class TorrentSorter(SorterBase):
    SORTSPECS = {
        'id':                _SortSpec(lambda t: t['id'],
                                       needed_keys=('id',),
                                       description='ID'),
        'name':              _SortSpec(lambda t: t['name'].lower(),
                                       aliases=('n',),
                                       needed_keys=('name',),
                                       description='name'),
        'path':              _SortSpec(lambda t: t['path'],
                                       aliases=('dir',),
                                       needed_keys=('path',),
                                       description='download location'),
        'status':            _SortSpec(lambda t: t['status'],
                                       aliases=('st',),
                                       needed_keys=('status',),
                                       description='current status (idle, uploading, verifying, etc.)'),
        'error':             _SortSpec(lambda t: t['error'],
                                       aliases=('err',),
                                       needed_keys=('error',),
                                       description='error message'),
        'uploaded':          _SortSpec(lambda t: t['size-uploaded'],
                                       aliases=('up',),
                                       needed_keys=('size-uploaded',),
                                       description='number of uploaded bytes'),
        'downloaded':        _SortSpec(lambda t: t['size-downloaded'],
                                       aliases=('dn',),
                                       needed_keys=('size-downloaded',),
                                       description='number of downloaded bytes'),
        '%downloaded':       _SortSpec(lambda t: t['%downloaded'],
                                       lambda t: t['%metadata'],
                                       lambda t: t['%verified'],
                                       aliases=('%dn',),
                                       needed_keys=('%downloaded', '%metadata', '%verified'),
                                       description='downloading or verifying progress'),
        'size':              _SortSpec(lambda t: t['size-final'],
                                       aliases=('sz',),
                                       needed_keys=('size-final',),
                                       description='number of bytes of all wanted files'),
        'peers':             _SortSpec(lambda t: t['peers-connected'],
                                       aliases=('prs',),
                                       needed_keys=('peers-connected',),
                                       description='connected peers'),
        'seeds':             _SortSpec(lambda t: t['peers-seeding'],
                                       aliases=('sds',),
                                       needed_keys=('peers-seeding',),
                                       description='highest number of seeds reported by any tracker'),
        'ratio':             _SortSpec(lambda t: t['ratio'],
                                       aliases=('rto',),
                                       needed_keys=('ratio',),
                                       description='upload/download ratio'),
        'rate-up':           _SortSpec(lambda t: t['rate-up'],
                                       aliases=('rup',),
                                       needed_keys=('rate-up',),
                                       description='upload rate'),
        'rate-down':         _SortSpec(lambda t: t['rate-down'],
                                       aliases=('rdn',),
                                       needed_keys=('rate-down',),
                                       description='download rate'),
        'rate':              _SortSpec(lambda t: t['rate-up'] + t['rate-down'],
                                       aliases=('r',),
                                       needed_keys=('rate-up', 'rate-down'),
                                       description='combined download and upload rate'),
        'limit-rate-up':     _SortSpec(lambda t: t['limit-rate-up'],
                                       aliases=('lrup',),
                                       needed_keys=('limit-rate-up',),
                                       description='upload rate limit'),
        'limit-rate-down':   _SortSpec(lambda t: t['limit-rate-down'],
                                       aliases=('lrdn',),
                                       needed_keys=('limit-rate-down',),
                                       description='download rate limit'),
        'limit-rate':        _SortSpec(lambda t: t['limit-rate-up'] + t['limit-rate-down'],
                                       aliases=('lr',),
                                       needed_keys=('limit-rate-up', 'limit-rate-down'),
                                       description='combined download and upload rate limit'),
        'tracker':           _SortSpec(lambda t: t['trackers'][0]['url-announce'].domain if t['trackers'] else '',
                                       aliases=('trk',),
                                       needed_keys=('trackers',),
                                       description='domain of first tracker'),
        'eta':               _SortSpec(lambda t: t['timespan-eta'],
                                       needed_keys=('timespan-eta',),
                                       description='estimated time to finish downloading'),
        'created':           _SortSpec(lambda t: t['time-created'],
                                       aliases=('tcrt',),
                                       needed_keys=('time-created',),
                                       description='creation time'),
        'added':             _SortSpec(lambda t: t['time-added'],
                                       aliases=('tadd',),
                                       needed_keys=('time-added',),
                                       description='time of addition'),
        'started':           _SortSpec(lambda t: t['time-started'],
                                       aliases=('tsta',),
                                       needed_keys=('time-started',),
                                       description='start time'),
        'activity':          _SortSpec(lambda t: t['time-activity'],
                                       aliases=('tact',),
                                       needed_keys=('time-activity',),
                                       description='time of latest upload/download activity'),
        'completed':         _SortSpec(lambda t: t['time-completed'],
                                       aliases=('tcmp',),
                                       needed_keys=('time-completed',),
                                       description='time of completion'),
    }
    DEFAULT_SORT = 'name'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Torrent keys we need for all sortspecs
        self._needed_keys = tuple(set().union(
            *(sortspec.needed_keys
              for sortspec in self._sortspecs)
        ))

    @property
    def needed_keys(self):
        return self._needed_keys
