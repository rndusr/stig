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

from ..logging import make_logger
log = make_logger(__name__)

from functools import partial


class _Sorter():
    def __init__(self, *keyfuncs, needed_keys, description, aliases=()):
        self._keyfuncs = keyfuncs
        self.needed_keys = needed_keys
        self.description = 'Sort torrents by ' + description
        self.aliases = aliases

    def __call__(self, items, reverse=False, inplace=False, torrent_getter=lambda item: item):
        if not items:
            return items

        for keyfunc in self._keyfuncs:
            def key_getter(item):
                return keyfunc(torrent_getter(item))

            if inplace:
                items[:] = sorted(items, key=key_getter, reverse=reverse)
            else:
                items = sorted(items, key=key_getter, reverse=reverse)

        return items


SORTERS = {
    'name':         _Sorter(lambda t: t['name'].lower(),
                            needed_keys=('name',),
                            description='name'),
    'path':         _Sorter(lambda t: t['path'],
                            aliases=('dir',),
                            needed_keys=('path',),
                            description='download location'),
    'status':       _Sorter(lambda t: t['status'],
                            needed_keys=('status',),
                            description='status (downloading, seeding, verifying, etc.)'),
    'size':         _Sorter(lambda t: t['size-final'],
                            needed_keys=('size-final',),
                            description='size'),
    'peers':        _Sorter(lambda t: t['peers-connected'],
                            needed_keys=('peers-connected',),
                            description='connected peers'),
    'seeds':        _Sorter(lambda t: t['peers-seeding'],
                            needed_keys=('peers-seeding',),
                            description='domain of first tracker'),
    'ratio':        _Sorter(lambda t: t['ratio'],
                            needed_keys=('ratio',),
                            description='ratio'),
    'rate-down':    _Sorter(lambda t: t['rate-down'],
                            needed_keys=('rate-down',),
                            description='download rate'),
    'rate-up':      _Sorter(lambda t: t['rate-up'],
                            needed_keys=('rate-up',),
                            description='upload rate'),
    'rate':         _Sorter(lambda t: t['rate-up'] + t['rate-down'],
                            needed_keys=('rate-up', 'rate-down'),
                            description='combined download and upload rate'),
    'uploaded':     _Sorter(lambda t: t['size-uploaded'],
                            needed_keys=('size-uploaded',),
                            description='number of uploaded bytes'),
    'downloaded':   _Sorter(lambda t: t['size-downloaded'],
                            needed_keys=('size-downloaded',),
                            description='number of downloaded bytes'),
    'progress':     _Sorter(lambda t: t['%downloaded'],
                            lambda t: t['%metadata'],
                            lambda t: t['%verified'],
                            needed_keys=('%downloaded', '%metadata', '%verified'),
                            description='downloading or verifying progress'),
    'tracker':      _Sorter(lambda t: t['trackers'][0]['url-announce'].domain if t['trackers'] else '',
                            needed_keys=('trackers',),
                            description='domain of first tracker'),
}

# Map aliases to their original name
_ALIASES = {alias: sname
            for sname,s in SORTERS.items()
            for alias in s.aliases}


class TorrentSorter():
    def __init__(self, sortstrings=()):
        sorters = []         # List of (<_Sorter instance>, <reverse=True/False>) tuples
        needed_keys = set()  # Torrent keys needed by all sorters
        strings = []         # String reprs of sorters
        for sortstring in sortstrings:
            if sortstring.startswith('!'):
                sortername, reverse = sortstring[1:], True
            else:
                sortername, reverse = sortstring, False

            # Resolve alias
            if sortername in _ALIASES:
                sortername = _ALIASES[sortername]

            if sortername not in SORTERS:
                raise ValueError('Unknown sort order: {}'.format(sortername))
            else:
                sorter = SORTERS[sortername]
                sorters.append(partial(sorter, reverse=reverse))
                strings.append(('!' if reverse else '') + sortername)
                needed_keys.update(sorter.needed_keys)

        # Insert alphabetical sorter unless one already exists (reverse or not)
        if 'name' not in sortstrings:
            namesorter = SORTERS['name']
            sorters.insert(0, namesorter)
            needed_keys.update(namesorter.needed_keys)

        self._sorters = tuple(sorters)
        self._str = ','.join(strings)
        self._needed_keys = tuple(needed_keys)

    def apply(self, items, inplace=False, torrent_getter=lambda item: item):
        """Sort sequence `items` in-place or return new list of items

        torrent_getter: Callable that gets an item of `items` and returns a
                        Torrent object (e.g. to sort lists of torrent widgets
                        in-place)
        inplace: Modify `items` if True, otherwise return a new list
        """
        import time
        start_time = time.time()

        for sorter in self._sorters:
            items = sorter(items, inplace=inplace, torrent_getter=torrent_getter)

        log.debug('-> Sorted %d items by %s in %.3fms',
                  len(items), self, (time.time()-start_time)*1e3)

        if not inplace:
            return items

    @property
    def needed_keys(self):
        return self._needed_keys

    def __str__(self):
        return self._str

    def __repr__(self):
        return '<{} {}>'.format(type(self).__name__, str(self))
