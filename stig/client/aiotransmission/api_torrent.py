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

from string import hexdigits as HEXDIGITS
from collections import abc
import os
import base64

from ..utils import (Response, URL)
from .torrent import (TorrentFields, Torrent)
from .. import ClientError
from ..filters.torrent import TorrentFilter
from ..filters.file import TorrentFileFilter
from ..utils import (Bool, Bandwidth, BoolOrBandwidth)
from ..ttypes import Path


class _TorrentCache():
    def __init__(self, raw_torrents=()):
        self._tdict = {}  # Map torrent IDs to Torrent objects

    def update(self, raw_torrents):
        # import time ; start = time.time()
        tdict = self._tdict
        for rt in raw_torrents:
            tid = rt['id']
            if tid in tdict:
                # Update existing torrent
                # log.debug('Updating torrent #%d, %d keys: %s', tid, len(rt), tuple(rt))
                tdict[tid].update(rt)
            else:
                # Add new torrent
                # log.debug('Adding torrent #%d, %d keys: %s', tid, len(rt), tuple(rt))
                tdict[tid] = Torrent(rt)
        # log.debug('Updated %d cached with %d new torrents in %.3fms',
        #           len(tdict), len(raw_torrents), (time.time()-start)*1000)

    def purge(self, existing_tids):
        """Remove torrents with IDs that are not in `existing_ids`"""
        tdict = self._tdict
        known_tids = set(tdict)
        removed_tids = known_tids.difference(existing_tids)
        if removed_tids:
            log.debug('Clearing cached torrents: %r', removed_tids)
        for tid in removed_tids:
            del tdict[tid]

    def get(self, *ids):
        """Return tuple of Torrent objects"""
        if ids:
            return tuple(t for tid,t in self._tdict.items() if tid in ids)
        else:
            return tuple(self._tdict.values())

    def __len__(self):
        return len(self._tdict)

    def __repr__(self):
        tlist = ', '.join('#'+str(tid) for tid in self._tdict)
        return '<{cls} {tlist}>'.format(cls=type(self).__name__,
                                        tlist=tlist or '(empty)')


class TorrentAPI():
    """High-level abstraction of the Transmission RPC protocol"""

    def __init__(self, rpc):
        self.rpc = rpc
        self._tcache = _TorrentCache()

    def clearcache(self):
        """Remove all torrents from cache"""
        self._tcache.purge(existing_tids=())

    @staticmethod
    async def _request(method, *args, **kwargs):
        try:
            result = await method(*args, **kwargs)
        except ClientError as e:
            return Response(success=False, result=None, errors=(str(e),))
        else:
            return Response(success=True, result=result)

    async def _map_tid_to_torrent_values(self, torrents, keys):
        """
        Map torrent ID to Torrent value(s)

        If `keys` lists only one key, the returned map maps each torrent's ID to
        its value of that key.

        If `keys` lists two or more keys, the returned map maps torrent IDs to a
        dict that maps keys to each torrent's value for that key.

        The result is returned attached to a Response instance via the attribute
        'torrent_values'.
        """
        response = await self.torrents(torrents, keys=('id',) + tuple(keys))
        if not response.success:
            return Response(success=False, torrent_values={}, errors=response.errors)
        else:
            if len(keys) == 1:
                key = keys[0]
                torrent_values = {t['id']:t[key] for t in response.torrents}
            else:
                torrent_values = {t['id']:{key:t[key] for key in keys}
                                  for t in response.torrents}
            return Response(success=True, torrent_values=torrent_values)

    async def _abs_download_path(self, path):
        """Turn relative `path` into absolute path based on default download path"""
        if not os.path.isabs(path):
            response = await self._request(self.rpc.session_get)
            if not response.success:
                return Response(success=False, path=None, errors=response.errors)
            else:
                download_dir = response.result['download-dir']
                abs_path = os.path.normpath(os.path.join(download_dir, path))
                return Response(success=True, path=Path(abs_path))
        return Response(success=True, path=Path(path))

    async def add(self, torrent, stopped=False, path=None):
        """
        Add torrent from file, URL or hash

        torrent: Path to local file, web/magnet link or hash
        stopped: False to start downloading immediately, True otherwise
        path:    Download directory or `None` for default directory

        Return Response with the following properties:
            torrent: Torrent object with the keys 'id' and 'name' if the
                     torrent could be added or if it already exists, otherwise
                     None
            success: False if torrent could not be added or already exists,
                     True otherwise
            msgs:    List of info messages
            errors:  List of error messages
        """
        torrent_str = torrent
        args = {'paused': bool(stopped)}

        if path is not None:
            response = await self._abs_download_path(path)
            if not response.success:
                return Response(success=False, torrent=None, errors=response.errors)
            else:
                args['download-dir'] = response.path

        # Check if torrent_str is path to local torrent file
        torrent_str_path = os.path.expanduser(torrent_str)
        if os.path.exists(torrent_str_path):
            torrent_str = torrent_str_path
            del torrent_str_path

            # Read local file
            try:
                with open(torrent_str, 'rb') as f:
                    args['metainfo'] = str(base64.b64encode(f.read()),
                                           encoding='ascii')
            except OSError as e:
                return Response(success=False, torrent=None,
                                errors=('%s: %s' % (e.strerror, torrent_str),))
        elif len(torrent_str) == 40 and all(c in HEXDIGITS for c in torrent_str):
            # Convert hash to magnet link
            args['filename'] = 'magnet:?xt=urn:btih:' + torrent_str
        else:
            # It's either a link or a torrent file on the server - let the
            # daemon figure it out
            args['filename'] = torrent_str

        response = await self._request(self.rpc.torrent_add, **args)
        if not response.success:
            errors = []
            for error in response.errors:
                if 'Invalid or corrupt' in error:
                    errors.append('Torrent file is corrupt or doesn\'t exist: %r' % torrent_str)
                else:
                    errors.append(error)
            return Response(success=False, torrent=None, msgs=response.msgs, errors=errors)
        else:
            result = response.result
            errors = ()
            msgs = ()
            if 'torrent-duplicate' in result:
                info = result['torrent-duplicate']
                errors = ('Torrent already exists: ' + info['name'],)
                success = False
            elif 'torrent-added' in result:
                info = result['torrent-added']
                msgs = ('Added %s' % info['name'],)
                success = True
            else:
                raise RuntimeError('Malformed response: %r' % (result,))
            torrent = Torrent({'id': info['id'], 'name': info['name']})
            return Response(success=success, torrent=torrent, msgs=msgs, errors=errors)


    async def _request_torrents(self, fields, ids=None):
        """
        Make 'torrent-get' RPC request

        Return a Response object with 'raw_torrents' set to a tuple of torrents
        according to the RPC spec.
        """
        if 'id' not in fields:
            fields = ('id',) + tuple(fields)
        try:
            if ids is None:
                # Request all IDs
                raw_tlist = await self.rpc.torrent_get(fields=fields)
            else:
                if len(ids) > 0:
                    # Request given IDs
                    raw_tlist = await self.rpc.torrent_get(fields=fields, ids=ids)
                else:
                    # No IDs (i.e. empty torrent list) requested
                    raw_tlist = []
        except ClientError as e:
            return Response(success=False, raw_torrents=(), errors=(str(e),))
        else:
            self._tcache.update(raw_tlist)

            # If we just got a list of all torrents, we can check for torrents
            # that we still have cached but don't exist anymore and purge them.
            if ids is None:
                tids = tuple(t['id'] for t in raw_tlist)
                self._tcache.purge(existing_tids=tids)

            return Response(success=True, raw_torrents=raw_tlist)

    async def _get_torrents_by_ids(self, keys, ids=None):
        """
        Return a Response object with 'torrents' set to a tuple of Torrents

        keys: 'ALL' for all supported Torrent keys or a sequence of key
              strings (see client.ttypes.TYPES for available keys)
        ids:  None for all torrents or a sequence of wanted IDs
        """
        if keys == 'ALL':
            fields = TorrentFields(keys)
        else:
            fields = TorrentFields(*keys)

        response = await self._request_torrents(fields, ids)
        if not response.success:
            return Response(success=False, torrents=(), errors=response.errors)
        else:
            from time import time
            start = time()

            errors = []

            # Get torrents from cache
            if ids is None:
                tlist = self._tcache.get()  # All torrents
            elif not ids:
                tlist = ()  # No torrents requested
            else:
                tlist = self._tcache.get(*ids)

                # Provide error for requested IDs that don't exist
                existing_ids = tuple(t['id'] for t in tlist)
                for tid in ids:
                    # Torrent objects are equal to an integer of the torrent's ID
                    if tid not in existing_ids:
                        errors.append('No torrent with ID: %d' % tid)

            success = len(tlist) > 0 or not ids
            log.debug('Found %d torrents in %.3fms', len(tlist), (time()-start)*1e3)
        return Response(success=success, torrents=tlist, errors=errors)

    async def _get_torrents_by_filter(self, keys, tfilter=None):
        """
        Return a Response object with 'torrents' set to a tuple of Torrents

        keys:    See _get_torrents_by_ids
        tfilter: A TorrentFilter instance or None to get all torrents
        """
        if tfilter is None:
            log.debug('Looking for all torrents with keys: %s', keys)
            # No filter specified - just return all torrents with the specified keys
            return await self._get_torrents_by_ids(keys=keys)
        else:
            log.debug('Looking for %s torrents with keys: %s', tfilter, keys)
            if isinstance(tfilter, str):
                tfilter = TorrentFilter(tfilter)

            tlist = ()

            # Request all torrents with the keys needed to filter them
            log.debug('Requesting full list with filter keys: %s', tfilter.needed_keys)
            response = await self._get_torrents_by_ids(keys=tfilter.needed_keys)
            if not response.success:
                return Response(success=False, torrents=(), errors=response.errors)
            else:
                # Find IDs of torrents that match tfilter
                wanted_ids = tuple(t['id'] for t in tfilter.apply(response.torrents))
                log.debug('Wanted IDs: %s', wanted_ids)
                if len(wanted_ids) > 0:
                    # Get only wanted torrents with all wanted keys
                    response = await self._get_torrents_by_ids(keys, wanted_ids)
                    if not response.success:
                        return Response(success=False, torrents=(), errors=response.errors)
                    else:
                        tlist = tuple(response.torrents)

            success = len(tlist) > 0
            msgs = errors = ()
            if not success:
                errors = ('No matching torrents: %s' % (tfilter,),)
            else:
                msgs = ('Found %d %s torrent%s' %
                        (len(tlist), tfilter, '' if len(tlist) == 1 else 's'),)
            return Response(success=success, torrents=tlist, msgs=msgs, errors=errors)

    async def torrents(self, torrents=None, keys='ALL'):
        """
        Get torrents

        torrents: Iterator of torrent IDs, TorrentFilter object (or its string
                  representation) or None for all torrents
        keys: tuple of Torrent keys to fetch or 'ALL' for all torrents

        Return Response with the following properties:
            torrents: Tuple of Torrent objects with requested torrents
            success:  False if no torrents were found, True otherwise
            msgs:     List of info messages
            errors:   List of error messages
        """
        if torrents is None:
            return await self._get_torrents_by_ids(keys)
        elif isinstance(torrents, (str, TorrentFilter)):
            return await self._get_torrents_by_filter(keys, tfilter=torrents)
        elif isinstance(torrents, abc.Sequence) and \
             all(isinstance(id, int) for id in torrents):
            return await self._get_torrents_by_ids(keys, ids=torrents)
        else:
            raise ValueError("Invalid 'torrents' argument: %r" % (torrents,))


    async def _torrent_action(self, method, torrents=None, method_args={},
                              check=None, check_keys=()):
        """
        Helper method that operates on torrents (start, stop, remove, etc)

        method:      Any method from TransmissionRPC that accepts torrent ids
        torrents:    See `torrents` method
        method_args: Dictionary with keyword arguments for method (except 'ids')
        check:       None or callable that is called with every torrent; must
                     return a 2-tuple of (SUCCESS, MESSAGE) where SUCCESS is
                     evaluated as bool and MESSAGE a string or None.  If SUCCESS
                     evaluates to True, `method` is applied to the torrent,
                     otherwise not.
        check_keys:  List of Torrent keys the check function needs ('id' and
                     'name' are always included)

        Return Response with the following properties:
            torrents: Tuple of Torrents that `method` was applied to with the
                      keys 'id' and 'name'
            success:  True if `method` was successfully applied to at least one
                      torrent, False otherwise
            msgs:     List of info messages
            errors:   List of error messages
        """
        # Always provide some basic keys
        check_keys = set(tuple(check_keys) + ('id', 'name'))

        msgs = []
        errors = []
        response = await self.torrents(torrents, keys=check_keys)
        if not response.success:
            return Response(success=False, torrents=(), errors=response.errors)
        else:
            msgs.extend(response.msgs)
            errors.extend(response.errors)

        if check is None:
            tlist = response.torrents
        else:
            # Filter torrents through check function
            tlist = []
            for t in response.torrents:
                passed, msg = check(t)
                if passed:
                    tlist.append(t)
                    if msg is not None:
                        msgs.append(msg)
                else:
                    if msg is not None:
                        errors.append(str(msg))

        # Apply method to torrents that passed the check function
        if len(tlist) <= 0:
            return Response(success=False, torrents=(), msgs=msgs, errors=errors)
        else:
            try:
                # Ignore response because it is always {}, except for
                # 'torrent-get' requests, which this method is not meant for.
                ids = tuple(t['id'] for t in tlist)
                # log.debug('Sending %s(%s) for IDs: %s', method.__qualname__,
                #           ', '.join(('%s=%r' % (k,v) for k,v in method_args.items())),
                #           ids)
                await method(ids=ids, **method_args)
            except ClientError as e:
                errors.append(str(e))
                return Response(success=False, torrents=(), msgs=msgs, errors=errors)
            else:
                return Response(success=True, torrents=tuple(tlist), msgs=msgs, errors=errors)

    async def stop(self, torrents):
        """
        Stop down-/uploading torrents

        torrents: See `torrents` method

        Return Response with the following properties:
            torrents: Tuple of stopped Torrents with the keys 'id' and 'name'
            success:  True if any torrents were stopped, False otherwise
            msgs:     List of info messages
            errors:   List of error messages
        """
        def check(t):
            if t['status'].STOPPED in t['status']:
                return (False, 'Already stopped: ' + t['name'])
            else:
                return (True, 'Stopping ' + t['name'])

        return await self._torrent_action(self.rpc.torrent_stop, torrents,
                                          check=check, check_keys=('status',))

    async def start(self, torrents, force=False):
        """
        Start down-/uploading torrents

        torrents: See `torrents` method
        force:    Start downloading even if download queue is active and full

        Return Response with the following properties:
            torrents: Tuple of started Torrents with the keys 'id' and 'name'
            success:  True if any torrents were started, False otherwise
            msgs:     List of info messages
            errors:   List of error messages
        """
        def check(t):
            if t['status'].STOPPED in t['status']:
                return (True, 'Starting ' + t['name'])
            else:
                return (False, 'Already started: ' + t['name'])

        if force:
            method = self.rpc.torrent_start_now
        else:
            method = self.rpc.torrent_start

        return await self._torrent_action(method, torrents,
                                          check=check, check_keys=('status',),
                                          method_args={'force':force})

    async def toggle_stopped(self, torrents, force=False):
        """
        Toggle down-/uploading torrents

        torrents: See `torrents` method
        force:    See `start` method

        Return Response with the following properties:
            torrents: Tuple of toggled Torrents with the keys 'id' and 'name'
            success:  True if any torrents were toggled, False otherwise
            msgs:     List of info messages
            errors:   List of error messages
        """
        response = await self.torrents(torrents, keys=('status',))
        if not response.success:
            return Response(success=False, torrents=(), errors=response.errors)

        stopped, running = [], []
        for t in response.torrents:
            if t['status'].STOPPED in t['status']:
                stopped.append(t)
            else:
                running.append(t)

        torrents = []
        msgs = []
        errors = []
        if len(running) > 0:
            response = await self.stop(tuple(t['id'] for t in running))
            torrents.extend(response.torrents)
            msgs.extend(response.msgs)
            errors.extend(response.errors)
        if len(stopped) > 0:
            r = await self.start(tuple(t['id'] for t in stopped), force=force)
            torrents.extend(response.torrents)
            msgs.extend(response.msgs)
            errors.extend(response.errors)

        return Response(success=len(torrents) > 0, torrents=torrents,
                        msgs=msgs, errors=errors)

    async def verify(self, torrents):
        """
        Verify torrents' downloaded data

        torrents: See `torrents` method

        Return Response with the following properties:
            torrents: tuple of to be verified Torrents with the keys 'id' and 'name'
            success:  True if any torrents are going to be verified, False otherwise
            msgs:     List of info messages
            errors:   List of error messages
        """
        def check(t):
            if t['status'].VERIFY in t['status']:
                if t['status'].QUEUED in t['status']:
                    return (False, 'Already queued for verification: ' + t['name'])
                else:
                    return (False, 'Already verifying: ' + t['name'])
            else:
                return (True, 'Verifying ' + t['name'])

        return await self._torrent_action(self.rpc.torrent_verify, torrents,
                                          check=check, check_keys=('status',))

    async def remove(self, torrents, delete=False):
        """
        Remove torrents

        torrents: See `torrents` method
        delete:   True to deleted downloaded files

        Return Response with the following properties:
            torrents: Tuple of removed Torrents with the keys 'id' and 'name'
            success:  True if any torrents were removed, False otherwise
            msgs:     List of info messages
            errors:   List of error messages
        """
        if delete:
            msg = 'Deleting %s (including files)'
        else:
            msg = 'Removing %s (keeping files)'

        def create_info_msg(t):
            return (True, msg % t['name'])

        return await self._torrent_action(self.rpc.torrent_remove, torrents,
                                          check=create_info_msg,
                                          method_args={'delete-local-data': delete})


    async def move(self, torrents, destination):
        """
        Change torrents' file system location

        torrents:    See `torrents` method
        destination: New path (relative paths are relative to the default
                     download path

        Return Response with the following properties:
            torrents: Tuple of moved Torrents with the keys 'id' and 'name'
            success:  True if any torrents were moved, False otherwise
            msgs:     List of info messages
            errors:   List of error messages
        """
        # Transmission wants an absolute path
        response = await self._abs_download_path(destination)
        if not response.success:
            return Response(success=False, torrents=(), errors=response.errors)
        else:
            destination = response.path

        def create_info_msg(t):
            if t['path'] != destination:
                return (True, 'Moving to %s: %s' % (destination, t['name']))
            else:
                return (False, 'Already in %s: %s' % (destination, t['name']))

        return await self._torrent_action(self.rpc.torrent_set_location, torrents,
                                          check=create_info_msg, check_keys=('path',),
                                          method_args={'move': True, 'location': destination})

    async def rename(self, tid, path, new_name):
        """
        Change the name of a torrent or one of its files or directories

        tid:      Torrent ID
        path:     Relative path in the torrent without the torrent's name or
                  anything that evaluates to False to rename the torrent itself
        new_name: New file or directory name; must not contain any directory
                  separators (usually "/") or be "." or ".."

        Return Response with the following properties:
            torrent: Torrent object with the keys 'id', 'name' and 'files' or
                     None in case of failure
            success: True if the torrent was renamed, False otherwise
            msgs:    List of info messages
            errors:  List of error messages
        """
        # Validate new_name
        if '/' in new_name:
            return Response(success=False, torrent=None,
                            errors=('New name must not contain "/": %s' % new_name,))
        for forbidden in ('.', '..'):
            if new_name == forbidden:
                return Response(success=False, torrent=None,
                                errors=('Illegal name: %s' % new_name,))

        # Fetch torrent
        response = await self._get_torrents_by_ids(ids=(tid,),
                                                   keys=('name', 'id', 'files', 'path'))
        if not response.success:
            return Response(success=False, torrent=None, errors=response.errors)
        else:
            torrent = response.torrents[0]

        # If no path given, rename the torrent itself
        if not path:
            path = torrent['name']

            # Check if new_name already exists at torrent's path
            download_path = torrent['path']
            response = await self.torrents('path=%s' % download_path, keys=('name',))
            if not response.success:
                return Response(success=False, torrent=None, errors=response.errors)
            else:
                for t in response.torrents:
                    if t['name'] == new_name:
                        return Response(success=False, torrent=None,
                                        errors=('Torrent already exists in %s: %s' %
                                                (download_path, new_name),))

        # Rename a file or directory in the torrent
        else:
            # Prepend torrent name to path
            path = os.path.join(torrent['name'], os.path.normpath(path))

            # Create list of existing files and directories; make sure to
            # include directories that contain no files (that means we can't use
            # os.path.dirname(filepath))
            existing_paths = set()
            for file in torrent['files'].files:
                filepath = str(file['path-relative'])
                existing_paths.add(filepath)
                dirs = filepath.split(os.sep)
                for i in range(1, len(dirs)):
                    dirpath = os.path.join(*dirs[:i])
                    existing_paths.add(dirpath)

            # Check if old path exists in torrent's files
            if path not in existing_paths:
                return Response(success=False, torrent=None,
                                errors=('No such path: %s' % path,))

            # Check if path is already named new_name
            if os.path.basename(path) == new_name:
                return Response(success=False, torrent=None,
                                errors=('Already named %s: %s' % (new_name, path),))

            # Check if new_name would overwrite a file or directory
            new_filepath = os.path.join(os.path.dirname(path), new_name)
            if new_filepath in existing_paths:
                return Response(success=False, torrent=None,
                                errors=('Path already exists: %s' % new_filepath,))

        # Send the rename RPC call
        def create_info_msg(t):
            return (True, 'Renaming %s to %s' % (path, new_name))
        response = await self._torrent_action(self.rpc.torrent_rename_path, (torrent['id'],),
                                              check=create_info_msg, check_keys=('name',),
                                              method_args={'path': path, 'name': new_name})
        if not response.success:
            return Response(success=False, torrent=None, errors=response.errors)
        else:
            # Preserve info messages for final response
            msgs = response.msgs

        # Fetch new torrent data and return final response
        response = await self._get_torrents_by_ids(ids=(tid,),
                                                   keys=('name', 'id', 'files'))
        if not response.success:
            return Response(success=False, torrent=None, errors=response.errors)
        else:
            torrent = response.torrents[0]
            return Response(success=True, torrent=torrent, msgs=msgs)

    async def file_priority(self, torrents, files, priority):
        """
        Change download priority of individual torrent files

        torrents: See `torrents` method
        files:    TorrentFileFilter object (or its string representation), sequence
                  of (torrent ID, file ID) tuples or None for all files
        priority: One of the strings 'off', 'low', 'normal' or 'high'

        Return Response with the following properties:
            torrents: Tuple of matching Torrents with matching files with the
                      keys 'id', 'name' and 'files'
            success:  True if any file priorities were changed, False otherwise
            msgs:     List of info messages
            errors:   List of error messages
        """
        response = await self.torrents(torrents, keys=('name', 'files'))
        if not response.success:
            return Response(success=False, torrents=(), errors=response.errors)
        else:
            if isinstance(files, str):
                files = TorrentFileFilter(files)

            # Set filter_files to a lambda that takes a TorrentFileTree and
            # returns a list of TorrentFiles.
            if files is None:
                filter_files = lambda ftree: tuple(ftree.files)
            elif isinstance(files, TorrentFileFilter):
                filter_files = lambda ftree: tuple(files.apply(ftree.files))
            elif isinstance(files, abc.Sequence):
                filter_files = lambda ftree: tuple(f for f in ftree.files
                                                   if f['id'] in files)
            else:
                raise ValueError("Invalid 'files' argument: %r" % (files,))

            torrent_ids = []
            msgs = []
            errors = []
            for t in sorted(response.torrents, key=lambda t: t['name'].lower()):
                # Filter torrent's files
                flist = filter_files(t['files'])
                if files is None:
                    msgs.append('%d file%s: %s' %
                                (len(flist), '' if len(flist) == 1 else 's', t['name']))
                else:
                    if not flist:
                        errors.append('No matching files: %s' % (t['name'],))
                    else:
                        msgs.append('%d matching file%s: %s' %
                                    (len(flist), '' if len(flist) == 1 else 's', t['name']))
                success = len(flist) > 0

                # Transmission wants a list of file indexes.  For
                # aiotransmission, the 'id' field of a TorrentFile is a tuple:
                #     (<torrent ID>, <file index>)
                # (See aiotransmission.torrent._create_TorrentFileTree())
                findexes = tuple(f['id'][1] for f in flist)
                if findexes:
                    response = await self._set_files_priority(priority, t['id'], findexes)
                    if response.success:
                        torrent_ids.append(t['id'])
                    msgs.extend(response.msgs)
                    errors.extend(response.errors)

        if torrent_ids:
            response = await self.torrents(torrent_ids, keys=('id', 'name', 'files'))
            if not response.success:
                return Response(success=False, torrents=(), errors=response.errors)
            else:
                torrents = response.torrents
        return Response(success=success, torrents=torrents, msgs=msgs, errors=errors)

    async def _set_files_priority(self, priority, torrent_id, file_indexes):
        fi = tuple(file_indexes)
        log.debug('Setting priority of torrent #%d: %r: %s', torrent_id, priority, file_indexes)
        if priority in ('high', 'normal', 'low'):
            return await self._torrent_action(
                self.rpc.torrent_set, (torrent_id,),
                method_args={'priority-%s' % priority: fi, 'files-wanted': fi})
        elif priority == 'off':
            return await self._torrent_action(
                self.rpc.torrent_set, (torrent_id,),
                method_args={'files-unwanted': fi})
        else:
            raise ValueError('Invalid priority: {!r}'.format(priority))


    async def _limit_rate_absolute(self, torrents, direction, limit):
        if isinstance(limit, str):
            try:
                limit = BoolOrBandwidth(limit)
            except ValueError as e:
                return Response(success=False, torrents=(), errors=('%s: %r' % (e, limit),))
        if isinstance(limit, (float, int)):
            limit = BoolOrBandwidth(False) if limit < 0 or limit >= float('inf') else limit

        log.debug('Setting new %sload limit for torrents %s: %s', direction, torrents, limit)
        return await self._limit_rate(torrents, direction, get_new_limit=lambda _: limit)

    async def _limit_rate_relative(self, torrents, direction, adjustment):
        if isinstance(adjustment, str):
            try:
                adjustment = Bandwidth(adjustment)
            except ValueError as e:
                return Response(success=False, torrents=(), errors=('%s: %r' % (e, adjustment),))

        def add_to_current_limit(current_limit):
            log.debug('Adjusting %sload limit %r by %r', direction, current_limit, adjustment)
            return BoolOrBandwidth.adjust(current_limit, adjustment)

        return await self._limit_rate(torrents, direction, get_new_limit=add_to_current_limit)

    async def _limit_rate(self, torrents, direction, get_new_limit):
        response = await self._map_tid_to_torrent_values(torrents, keys=('limit-rate-'+direction,))
        if not response.success:
            return Response(success=False, torrent_set_args={}, errors=response.errors)
        else:
            current_limits = response.torrent_values
            log.debug('Current %sload rate limits: %r', direction, current_limits)

        # Generate 'torrent-set' arguments for each torrent ID.  To de-duplicate
        # requests (same args for multiple torrents), we map the args to a list
        # of torrent IDs, so we just append another ID for existing args.
        torrent_set_args = {}
        errors = {}
        for tid,cur_limit in current_limits.items():
            cur_limit = BoolOrBandwidth(cur_limit)
            new_limit = BoolOrBandwidth(get_new_limit(cur_limit))

            if new_limit == cur_limit:
                log.debug('Nothing to set: new:%r == cur:%r', new_limit, cur_limit)
                errors[tid] = 'Already %s' % cur_limit
                continue
            elif isinstance(new_limit, Bool):
                if new_limit and isinstance(cur_limit, (float, int)) and cur_limit < float('inf'):
                    errors[tid] = 'Already limited'
                    continue
                else:
                    log.debug('%sabling limit', 'En' if new_limit else 'Dis')
                    args = (('%sloadLimited' % direction, bool(new_limit)),)
            else:
                log.debug('Setting new limit: %r', new_limit)
                if new_limit >= float('inf'):
                    args = (('%sloadLimited' % direction, False),)
                else:
                    raw_limit = round(int(new_limit.copy(convert_to='B'))/1000)  # Transmission expects kilobytes
                    args = (('%sloadLimited' % direction, True),
                            ('%sloadLimit' % direction, raw_limit))

            if args in torrent_set_args:
                torrent_set_args[args].append(tid)
            else:
                torrent_set_args[args] = [tid]

        # Send one 'torrent-set' request for each list of torrent IDs
        for args,tids in torrent_set_args.items():
            response = await self._torrent_action(self.rpc.torrent_set, tids,
                                                  method_args=dict(args))
            if not response.success:
                return Response(success=False, torrents=(), errors=response.errors)

        # Fetch torrents again and return Response with new rate limit messages
        all_tids = sum(torrent_set_args.values(), []) + list(errors)
        response = await self.torrents(all_tids, keys=('name', 'id', 'limit-rate-'+direction))
        if not response.success:
            return Response(success=False, torrents=(), errors=response.errors)
        msgs = []
        errormsgs = []
        success = False
        for t in response.torrents:
            if t['id'] in errors:
                errormsgs.append('%s %sload rate limit: %s' % (t['name'], direction, errors[t['id']]))
            else:
                success = True
                msgs.append('%s %sload rate limit: %s' % (t['name'], direction, t['limit-rate-'+direction]))
        return Response(success=success, torrents=response.torrents, msgs=msgs, errors=errormsgs)

    async def set_limit_rate_up(self, torrents, limit):
        """
        Limit upload rate for individual torrent(s)

        torrents: See `torrents` method
        limit:    Passed to `client.utils.BoolOrBandwidth`

        Return Response with the following properties:
            torrents: Tuple of Torrents with the keys 'id', 'name' and 'limit-rate-up'
            success:  True if any upload rate limits were changed, False otherwise
            msgs:     List of info messages
            errors:   List of error messages
        """
        return await self._limit_rate_absolute(torrents, 'up', limit)

    async def set_limit_rate_down(self, torrents, limit):
        """See `set_limit_rate_up`"""
        return await self._limit_rate_absolute(torrents, 'down', limit)

    async def adjust_limit_rate_up(self, torrents, adjustment):
        """
        Same as `set_limit_rate_up` but set new limit relative to current limit

        adjustment: Negative or positive number to add to the current limit of
                    each matching torrent (this is passed to
                    `client.utils.Bandwidth`)
        """
        return await self._limit_rate_relative(torrents, 'up', adjustment)

    async def adjust_limit_rate_down(self, torrents, adjustment):
        """See `adjust_limit_rate_up`"""
        return await self._limit_rate_relative(torrents, 'down', adjustment)


    async def tracker_add(self, torrents, urls):
        """
        Add tracker(s) to torrents

        torrents: See `torrents` method
        urls:     Iterable of announce URLs

        Return Response with the following properties:
            torrents: Tuple of Torrents with the keys 'id', 'name' and 'trackers'
            success:  True if any trackers were added, False otherwise
            msgs:     List of info messages
            errors:   List of error messages
        """
        if not urls:
            return Response(success=False, torrents=(), errors=('No URLs given',))

        # Transmission returns 'Invalid argument' if we try to add an existing
        # tracker, so first we check if any of our URLs already exist.
        response = await self.torrents(torrents, keys=('id', 'name', 'trackers',))
        if not response.success:
            return Response(success=False, torrents=(), errors=response.errors)
        else:
            tordict = {tor['id']:tor for tor in response.torrents}

        # Map torrent IDs to currently used URLs by that torrent
        old_url_dict = {torid:tuple(trk['url-announce'] for trk in torrent['trackers'])
                        for torid,torrent in tordict.items()}

        # Make sure URLs are comparable
        new_urls = [URL(url) for url in urls]

        # For each torrent, report any supplied URLs that are already used
        msgs = []
        errors = []
        for torid,old_urls in old_url_dict.items():
            for old_url in old_urls:
                if old_url in new_urls:
                    errors.append('%s: Tracker already exists: %s' % (tordict[torid]['name'], old_url))
                    new_urls.remove(old_url)

        # No URLs left to add?
        if not new_urls:
            return Response(success=False, torrents=(), errors=errors)

        for new_url in new_urls:
            msgs.append('%s: Adding tracker: %s' % (tordict[torid]['name'], new_url))

        # Add trackers
        args = {'trackerAdd': [str(url) for url in new_urls]}
        response = await self._torrent_action(self.rpc.torrent_set, torrents,
                                              method_args=args)
        if not response.success:
            errors.extend(response.errors)
            return Response(success=False, torrents=(), msgs=msgs, errors=errors)
        else:
            return Response(success=True, torrents=response.torrents, msgs=msgs, errors=errors)

    async def tracker_remove(self, torrents, urls, partial_match=False):
        """
        Remove tracker(s) from torrents

        torrents:      See `torrents` method
        urls:          Iterable of announce URLs
        partial_match: True if given URLs match existing URLs partially
                       (e.g. 'example.org' matches 'http://tracker.example.org/')

        Return Response with the following properties:
            torrents: Tuple of Torrents with the keys 'id', 'name' and 'trackers'
            success:  True if any trackers were removed, False otherwise
            msgs:     List of info messages
            errors:   List of error messages
        """
        if not urls:
            return Response(success=False, torrents=(), errors=('No URLs given',))

        # Get wanted torrent IDs
        response = await self.torrents(torrents, keys=('id',))
        if not response.success:
            return Response(success=False, torrents=(), errors=response.errors)
        else:
            torids = tuple(t['id'] for t in response.torrents)

        # Get raw tracker lists for the unaltered tracker IDs.  We need them
        # later to specify which trackers to remove.
        response = await self._request(self.rpc.torrent_get, ids=torids,
                                       fields=('id', 'name', 'trackers'))
        if not response.success or len(response.result) <= 0:
            return Response(success=False, torrents=(), errors=response.errors)
        else:
            raw_tor_dict = {raw_tor['id']:raw_tor for raw_tor in response.result}

        # Map torrent IDs to lists of IDs of matching trackers
        msgs = []
        errors = []
        remove_urls = urls
        matching_urls = []
        remove_ids = {}
        for torid,raw_tor in raw_tor_dict.items():
            remove_ids[torid] = []
            for raw_trk in raw_tor['trackers']:
                existing_url = raw_trk['announce']
                for remove_url in remove_urls:
                    if remove_url == existing_url or partial_match and remove_url in existing_url:
                        remove_ids[torid].append(raw_trk['id'])
                        matching_urls.append(remove_url)
                        msgs.append('%s: Removing tracker: %s' % (raw_tor['name'], existing_url))

            if len(remove_ids[torid]) <= 0:
                # No matching trackers for this torrent
                del remove_ids[torid]

        # Report error if no matching trackers were found for a given URL
        for mismatch in set(remove_urls).difference(matching_urls):
            errors.append('No matching trackers found: %r' % mismatch)

        # Finally remove trackers from torrents
        if remove_ids:
            for torid,trkids in remove_ids.items():
                response = await self._torrent_action(self.rpc.torrent_set, (torid,),
                                                      method_args={'trackerRemove': trkids})
                if not response.success:
                    return Response(success=False, torrents=(), errors=response.errors)

        # Get new torrent list with newly added trackers
        response = await self.torrents(tuple(remove_ids), keys=('id', 'name', 'trackers'))
        if not response.success:
            errors.extend(response.errors)
            return Response(success=False, torrents=(), msgs=msgs, errors=errors)
        else:
            return Response(success=True, torrents=response.torrents, msgs=msgs, errors=errors)

    async def announce(self, torrents):
        """
        Announce torrents to their tracker(s)

        torrents: See `torrents` method

        Return Response with the following properties:
            torrents: Tuple of Torrents with the keys 'id' and 'name'
            success:  True if any torrents were found, False otherwise
            msgs:     List of info messages
            errors:   List of error messages
        """
        import time
        def check(t):
            if len(t['trackers']) < 1:
                return (False, 'Torrent has no trackers: %s' % t['name'])
            elif t['status'].STOPPED in t['status']:
                return (False, 'Not announcing inactive torrent: %s' % t['name'])
            elif t['time-manual-announce-allowed'] == 0:
                return (False, 'Manual announce not allowed')
            elif t['time-manual-announce-allowed'] > time.time():
                return (False, ('Manual announce not allowed until %s (in %s): %r' %
                                (t['time-manual-announce-allowed'],
                                 t['time-manual-announce-allowed'].timedelta, t['name'])))
            else:
                return (True, 'Announcing: %s' % t['name'])

        return await self._torrent_action(self.rpc.torrent_reannounce, torrents,
                                          check=check, check_keys=('status', 'trackers',
                                                                   'time-manual-announce-allowed'))
