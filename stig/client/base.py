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

from collections import abc
from urllib.parse import quote_plus as urlquote

from . import ClientError

from ..logging import make_logger  # isort:skip
log = make_logger(__name__)


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
        if hasattr(other, 'get'):
            return self['id'] == other.get('id')
        return NotImplemented

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        if hasattr(other, 'get'):
            return self['id'] > other.get('id')
        return NotImplemented

    def __len__(self):
        return len(tuple(iter(self)))

    def __hash__(self):
        return hash(self['id'])


class TorrentAPIBase():
    async def get_magnet_uris(self, tfilter, tracker=False, trackers=True, name=True, size=True):
        response = await self.torrents(tfilter, keys=('hash', 'name', 'size-total', 'trackers'))
        if not response.success:
            raise ClientError(response.errors[0])
        else:
            torrents = response.torrents

        uris = []
        for t in torrents:
            parts = ['xt=urn:btih:%s' % t['hash']]
            if name and t['name'] != t['hash']:
                parts.append('dn=%s' % urlquote(t['name']))
            if size and t['size-total'] > 0:
                parts.append('xl=%r' % t['size-total'])
            if t['trackers']:
                if tracker:
                    # Including only one tracker
                    parts.append('tr=%s' % urlquote(str(t['trackers'][0]['url-announce'])))
                elif trackers:
                    # Including all trackers
                    for tracker in t['trackers']:
                        parts.append('tr=%s' % urlquote(str(tracker['url-announce'])))
            uris.append('magnet:?' + '&'.join(parts))
        return uris


class TorrentFileTreeBase(abc.Mapping):
    """Nested mapping of a Torrent's files"""

    # Distinguish subtrees from files without comparing classes everywhere
    # ("parent" or "leaf")
    nodetype = 'parent'

    def __init__(self, location, path, *args, **kwargs):
        self._location = location  # Absolute download location
        self._path = path          # Path relative to location
        self._items = NotImplemented

    @property
    def files(self):
        """Yield all TorrentFiles recursively"""
        for entry in self._items.values():
            if entry.nodetype == 'leaf':
                yield entry
            else:
                yield from entry.files

    @property
    def directories(self):
        """Yield (name, TorrentFileTree) tuples recursively"""
        for name,entry in self._items.items():
            if entry.nodetype == 'parent':
                yield (name, entry)
                yield from entry.directories

    @property
    def location(self):
        """Absolute path of the torrent; base directory"""
        return self._location

    @property
    def path(self):
        """Relative path in the torrent"""
        return self._path

    @property
    def id(self):
        return tuple(f['id'] for f in self.files)

    def __repr__(self):
        return '<%s path=%r: %r>' % (type(self).__name__, self._path, self._items)

    def __getitem__(self, key):
        return self._items[key]

    def __iter__(self):
        return iter(self._items)

    def __len__(self):
        return len(self._items)
