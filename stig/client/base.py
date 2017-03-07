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

from collections import abc


class TorrentBase(abc.Mapping):
    """Information about a torrent as a mapping

    This is the base class that all API implementations should use.

    Derivatives of this base class must add the methods 'update',
    '__getitem__' and '__iter__'.
    """

    def update(self, raw_torrent):
        raise NotImplementedError()

    def __getitem__(self, key):
        raise NotImplementedError()

    def __iter__(self):
        raise NotImplementedError()

    def __repr__(self):
        r = '<{} #{}'.format(type(self).__name__, self['id'])
        if 'name' in self:
            r += ' ' + repr(self['name'])
        return r + '>'

    def __eq__(self, other):
        if isinstance(other, int):
            return self['id'] == other
        elif isinstance(other, TorrentBase):
            return self['id'] == other['id']
        else:
            return NotImplemented

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        return self['id'] > other['id']

    def __len__(self):
        return len(tuple(iter(self)))

    def __hash__(self):
        return hash(self['id'])


from collections import abc
from . import tkeys
class TorrentFileTreeBase(abc.Mapping):
    """Nested mapping of a Torrent's files"""

    # Distinguish subtrees from files without comparing classes everywhere
    # ("parent" or "leaf")
    nodetype = 'parent'

    def __init__(self, *args, **kwargs):
        raise NotImplementedError()

    @property
    def files(self):
        """Yield all TorrentFiles recursively"""
        for entry in self._items.values():
            if entry.nodetype == 'leaf':
                yield entry
            else:
                yield from entry.files

    @property
    def folders(self):
        """Yield (name, TorrentFileTree) tuples recursively"""
        for name,entry in self._items.items():
            if entry.nodetype == 'parent':
                yield (name, entry)
                yield from entry.folders

    @property
    def path(self):
        return self._path

    def __repr__(self):
        return '<%s %r>' % (type(self).__name__, self._items)

    def __getitem__(self, key):
        return self._items[key]

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)
