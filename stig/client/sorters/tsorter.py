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
        'name':         _SortSpec(lambda t: t['name'].lower(),
                                  needed_keys=('name',),
                                  description='name'),
        'path':         _SortSpec(lambda t: t['path'],
                                  aliases=('dir',),
                                  needed_keys=('path',),
                                  description='download location'),
        'status':       _SortSpec(lambda t: t['status'],
                                  needed_keys=('status',),
                                  description='status (downloading, seeding, verifying, etc.)'),
        'size':         _SortSpec(lambda t: t['size-final'],
                                  needed_keys=('size-final',),
                                  description='size when complete'),
        'peers':        _SortSpec(lambda t: t['peers-connected'],
                                  needed_keys=('peers-connected',),
                                  description='connected peers'),
        'seeds':        _SortSpec(lambda t: t['peers-seeding'],
                                  needed_keys=('peers-seeding',),
                                  description='highest number of seeds reported by any tracker'),
        'ratio':        _SortSpec(lambda t: t['ratio'],
                                  needed_keys=('ratio',),
                                  description='upload/download ratio'),
        'rate-down':    _SortSpec(lambda t: t['rate-down'],
                                  needed_keys=('rate-down',),
                                  description='download rate'),
        'rate-up':      _SortSpec(lambda t: t['rate-up'],
                                  needed_keys=('rate-up',),
                                  description='upload rate'),
        'rate':         _SortSpec(lambda t: t['rate-up'] + t['rate-down'],
                                  needed_keys=('rate-up', 'rate-down'),
                                  description='combined download and upload rate'),
        'uploaded':     _SortSpec(lambda t: t['size-uploaded'],
                                  needed_keys=('size-uploaded',),
                                  description='number of uploaded bytes'),
        'downloaded':   _SortSpec(lambda t: t['size-downloaded'],
                                  needed_keys=('size-downloaded',),
                                  description='number of downloaded bytes'),
        'progress':     _SortSpec(lambda t: t['%downloaded'],
                                  lambda t: t['%metadata'],
                                  lambda t: t['%verified'],
                                  needed_keys=('%downloaded', '%metadata', '%verified'),
                                  description='downloading or verifying progress'),
        'eta':          _SortSpec(lambda t: t['timespan-eta'],
                                  needed_keys=('timespan-eta',),
                                  description='estimated time to finish downloading'),
        'tracker':      _SortSpec(lambda t: t['trackers'][0]['url-announce'].domain if t['trackers'] else '',
                                  needed_keys=('trackers',),
                                  description='domain of first tracker'),
    }
    DEFAULT_SORTSPECNAME = 'name'

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
