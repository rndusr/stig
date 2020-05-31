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

import asyncio
from collections import abc, defaultdict
from types import SimpleNamespace
from urllib.parse import quote_plus as urlquote

import blinker

from . import ClientError, utils

from ..logging import make_logger  # isort:skip
log = make_logger(__name__)


class TorrentBase(abc.Mapping):
    """Information about a torrent as a mapping

    This is the base class that all API implementations should use.

    Derivatives of this base class must add the methods 'update',
    '__getitem__' and '__iter__'.
    """

    TYPES = {
        'id'                           : int,
        'hash'                         : utils.SHA1,
        'name'                         : utils.SmartCmpStr,
        'ratio'                        : utils.Ratio,
        'status'                       : utils.Status,
        'path'                         : utils.SmartCmpPath,
        'private'                      : bool,
        'comment'                      : utils.SmartCmpStr,
        'creator'                      : utils.SmartCmpStr,
        'magnetlink'                   : str,
        'count-pieces'                 : utils.Int,

        '%downloaded'                  : utils.Percent,
        '%uploaded'                    : utils.Percent,
        '%metadata'                    : utils.Percent,
        '%verified'                    : utils.Percent,
        '%available'                   : utils.Percent,

        'peers-connected'              : utils.Int,
        'peers-uploading'              : utils.Int,
        'peers-downloading'            : utils.Int,
        'peers-seeding'                : utils.Count,

        'timespan-eta'                 : utils.Timedelta,
        'timespan-seeding'             : utils.Timedelta,
        'timespan-downloading'         : utils.Timedelta,
        'time-created'                 : utils.Timestamp,
        'time-added'                   : utils.Timestamp,
        'time-started'                 : utils.Timestamp,
        'time-activity'                : utils.Timestamp,
        'time-completed'               : utils.Timestamp,
        'time-manual-announce-allowed' : utils.Timestamp,

        'rate-down'                    : utils.BandwidthInBytes,
        'rate-up'                      : utils.BandwidthInBytes,
        'limit-rate-down'              : utils.BandwidthInBytesOrNone,
        'limit-rate-up'                : utils.BandwidthInBytesOrNone,
        'size-final'                   : utils.SizeInBytes,
        'size-total'                   : utils.SizeInBytes,
        'size-downloaded'              : utils.SizeInBytes,
        'size-uploaded'                : utils.SizeInBytes,
        'size-available'               : utils.SizeInBytes,
        'size-left'                    : utils.SizeInBytes,
        'size-corrupt'                 : utils.SizeInBytes,
        'size-piece'                   : utils.SizeInBytes,

        'error'                        : str,
        'trackers'                     : tuple,
        'peers'                        : tuple,
        'files'                        : None,
    }

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


class FreeSpaceAPIBase():
    """
    Gather available storage space for multiple directories

    path_getters: Iterable of callables that must return a path (str) or None
    rpc: Object that can be used by the implementation of get_free_space()
    settings: Object with an on_update() method that allows us to register a callback for
              path changes
    """
    def __init__(self, path_getters, rpc, settings):
        self._path_getters = tuple(path_getters)
        self._rpc = rpc
        self._on_update = blinker.Signal()
        self._info = defaultdict(lambda: SimpleNamespace(path=None, free=None, error=None))
        settings.on_update(self._gather_info_wrapper)

    def _gather_info_wrapper(self, settings):
        asyncio.ensure_future(self._gather_info_wrapper_coro())

    async def _gather_info_wrapper_coro(self):
        infos = {}
        for path_getter in self._path_getters:
            try:
                path = path_getter()
            except ClientError as e:
                log.debug('Exception from %r: %r', path_getter, e)
            else:
                if not path:
                    log.debug('Ignoring false path: %r: %r', path, bool(path))
                elif not isinstance(path, str):
                    log.debug('Ignoring invalid path: %r: %r', type(path), path)
                else:
                    try:
                        free = await self.get_free_space(path)
                    except ClientError as e:
                        infos[path] = SimpleNamespace(path=path, free=None, error=e)
                    else:
                        infos[path] = SimpleNamespace(path=path,
                                                      free=utils.convert.size(free, unit='byte'),
                                                      error=None)
        if self._info != infos:
            self._info = infos
            self._on_update.send(self)

    @property
    def info(self):
        """
        Dictionary that maps paths to namespaces

        Each namespace has these attributes:

          path:  Directory returned by one of the path_getters or None if the path_getter
                 failed
          free:  Available space in path or None if get_free_space() or the path_getter
                 failed
          error: Exception object raised by the path_getter or get_free_space()
        """
        return self._info

    async def get_free_space(self, path):
        """
        Return the available space in directory `path` in bytes
        """
        raise NotImplementedError()

    def on_update(self, callback, autoremove=True):
        """
        Register `callback` to be called when free space has changed

        `callback` gets the instance of this class.

        If `autoremove` is True, `callback` is removed automatically when it is deleted.
        """
        log.debug('Registering %r to receive free space updates', callback)
        self._on_update.connect(callback, weak=autoremove)
