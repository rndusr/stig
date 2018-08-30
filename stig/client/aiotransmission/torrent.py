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

"""Torrent class and value modifiers for compatibility with ttypes"""

from ...logging import make_logger
log = make_logger(__name__)

from .. import ttypes
from ..utils import LazyDict
from .. import base


# Some values need to be modified to comply with our internal standards

def _modify_ratio(t):
    #define TR_RATIO_NA  -1
    #define TR_RATIO_INF -2
    ratio = t['uploadRatio']
    if ratio == -1:
        return ttypes.Ratio.NOT_APPLICABLE
    elif ratio == -2:
        return ttypes.Ratio.INFINITE
    else:
        return ratio


def _modify_eta(t):
    #define TR_ETA_NOT_AVAIL -1
    #define TR_ETA_UNKNOWN -2
    seconds = t['eta']
    if seconds == -1:
        return ttypes.Timedelta.NOT_APPLICABLE
    elif seconds == -2:
        return ttypes.Timedelta.UNKNOWN
    else:
        return seconds


def _modify_timestamp(t, key, zero_means=ttypes.Timestamp.UNKNOWN):
    # I couldn't find any documentation on this, but 0 seems to mean "not applicable"?
    seconds = t[key]
    if seconds == 0:
        return zero_means
    else:
        return seconds


import time
def _modify_timestamp_completed(t):
    if t['percentDone'] >= 1:
        doneDate = t['doneDate']
        if doneDate == 0:
            return t['addedDate']            # We are the original uploader
        else:
            return doneDate                  # Torrent has been completed in the past
    elif t['eta'] <= 0:
        return ttypes.Timestamp.UNKNOWN      # Torrent is incomplete + paused
    else:
        return time.time() + t['eta']        # Torrent is downloading


def _count_seeds(t):
    trackerStats = t['trackerStats']
    if trackerStats:
        return max(t['seederCount'] for t in trackerStats)
    else:
        return ttypes.Count.UNKNOWN


def _bytes_available(t):
    return t['desiredAvailable'] + t['haveValid'] + t['haveUnchecked']


def _percent_available(t):
    try:
        return _bytes_available(t) / t['sizeWhenDone'] * 100
    except ZeroDivisionError:
        return 0


def _percent_uploaded(t):
    try:
        return t['uploadedEver'] / t['totalSize'] * 100
    except ZeroDivisionError:
        return 0


def _is_isolated(t):
    """Return whether this torrent can find any peers via trackers or DHT"""
    if not t['isPrivate']:
        return False  # DHT is used

    # Torrent has trackers?
    trackerStats = t['trackerStats']
    if trackerStats:
        # Did we try to connect to a tracker?
        if any(tracker['hasAnnounced'] for tracker in trackerStats):
            # Did at least one tracker respond?
            if any(tracker['lastAnnounceSucceeded'] for tracker in trackerStats):
                return False
        # We didn't try yet; assume non-isolation
        else:
            return False
    return True  # No way to find any peers


def _find_error(t):
    error = t['error']
    if error == 1:
        return 'Tracker warning: %s' % t['errorString']
    elif error == 2:
        return 'Tracker error: %s' % t['errorString']
    elif error == 3:
        return t['errorString']

    # The fields 'error' and 'errorString' are not necessarily set when
    # _is_isolated returns True. (Not sure why that happens. Reproduce by
    # setting a tracker domain to 127.0.0.1 in /etc/hosts to provoke an error.)
    trackerStats = t['trackerStats']
    for tracker in trackerStats:
        msg = tracker['lastAnnounceResult']
        if msg != 'Success':
            return msg

    return ''


def _make_status(t):
    Status = ttypes.Status
    statuses = []

    # RPC values for 'status' field:
    # TR_STATUS_STOPPED        = 0, /* Torrent is stopped */
    # TR_STATUS_CHECK_WAIT     = 1, /* Queued to check files */
    # TR_STATUS_CHECK          = 2, /* Checking files */
    # TR_STATUS_DOWNLOAD_WAIT  = 3, /* Queued to download */
    # TR_STATUS_DOWNLOAD       = 4, /* Downloading */
    # TR_STATUS_SEED_WAIT      = 5, /* Queued to seed */
    # TR_STATUS_SEED           = 6  /* Seeding */
    t_status = t['status']
    if t_status == 0:
        statuses.append(Status.STOPPED)
    elif t_status in (1, 2):
        statuses.append(Status.VERIFY)
    if t_status in (1, 3, 5):
        statuses.append(Status.QUEUED)

    if Status.STOPPED not in statuses:
        if _is_isolated(t):
            statuses.append(Status.ISOLATED)
        if t['metadataPercentComplete'] < 1:
            statuses.append(Status.INIT)

        if Status.QUEUED not in statuses:
            if t['peersConnected'] > 0:
                if t['rateDownload'] > 0:
                    statuses.append(Status.DOWNLOAD)
                if t['rateUpload'] > 0:
                    statuses.append(Status.UPLOAD)
                statuses.append(Status.CONNECTED)

            if t['percentDone'] >= 1:
                statuses.append(Status.SEED)

    if all(x not in statuses for x in (Status.UPLOAD,
                                       Status.DOWNLOAD,
                                       Status.VERIFY)):
        statuses.append(Status.IDLE)

    return statuses


class TorrentFileID(tuple):
    def __new__(cls, torrent_id, file_id):
        return super().__new__(cls, (torrent_id, file_id))

    @property
    def torrent_id(self):
        return self[0]

    @property
    def file_id(self):
        return self[1]

    def __repr__(self):
        return 'TorrentFileID(torrent_id=%d, file_id=%d)' % self

import os
class TorrentFileTree(base.TorrentFileTreeBase):
    @classmethod
    def create(cls, raw_torrent):
        fileStats = raw_torrent['fileStats']
        if len(fileStats) < 1:
            # filelist is empty if torrent was added by hash and metadata isn't
            # downloaded yet.
            filelist = [{'tid': -1, 'id': TorrentFileID(-1, -1), 'name': raw_torrent['name'],
                         'priority': 0, 'length': 0, 'wanted': True, 'bytesCompleted': 0}]
        else:
            # Combine 'files' and 'fileStats' fields and add the 'id' key to each
            # file, which is a (torrent ID, file list index) tuple
            tid = raw_torrent['id']
            filelist = ({'id': TorrentFileID(tid, i), **f, **fS}
                        for i,(f,fS) in enumerate(zip(raw_torrent['files'], fileStats)))
        return cls(raw_torrent['id'], raw_torrent['downloadDir'], filelist, path=())

    def __init__(self, torrent_id, torrent_location, filelist, path):
        log.debug('Creating new TorrentFileTree for torrent %r: %r', torrent_id, path)
        path_str = os.sep.join(path)
        super().__init__(torrent_location, path_str)

        items = {}
        subdirs = {}
        for entry in filelist:
            parts = entry['name'].split(os.sep, 1)
            if len(parts) == 1:
                filename = parts[0]
                items[filename] = ttypes.TorrentFile(
                    tid=torrent_id, id=entry['id'],
                    name=entry['name'], path=path_str, location=torrent_location,
                    size_total=entry['length'],
                    size_downloaded=entry['bytesCompleted'],
                    is_wanted=entry['wanted'],
                    priority=entry['priority'])

            elif len(parts) == 2:
                subdir, subpath = parts
                if subdir not in subdirs:
                    subdirs[subdir] = []
                entry['name'] = subpath
                subdirs[subdir].append(entry)
            else:
                raise RuntimeError(parts)

        for subdir,filelist in subdirs.items():
            items[subdir] = TorrentFileTree(torrent_id, torrent_location,
                                            filelist, path=path+(subdir,))
        self._items = items

    def update(self, raw_torrent):
        def update_files(ftree, fileStats):
            if not fileStats:
                # We don't have any metadata yet, so there is nothing to update
                return

            for entry in ftree.values():
                if isinstance(entry, ttypes.TorrentFile):
                    # File ID is its index in the list provided by
                    # Transmission (see _create_TorrentFileTree)
                    index = entry['id'].file_id
                    fstats = fileStats[index]
                    entry.update({'size-downloaded': fstats['bytesCompleted'],
                                  'is-wanted': fstats['wanted'],
                                  'priority': fstats['priority'],
                                  'location': raw_torrent['downloadDir']})
                else:
                    update_files(entry, fileStats)

        update_files(self._items, raw_torrent['fileStats'])



class PeerList(tuple):
    def __new__(cls, t):
        TorrentPeer = ttypes.TorrentPeer
        return super().__new__(cls,
            (TorrentPeer(tid=t['id'], tname=t['name'], tsize=t['totalSize'],
                         ip=p['address'], port=p['port'], client=p['clientName'],
                         pdownloaded=p['progress']*100,
                         rate_up=p['rateToPeer'], rate_down=p['rateToClient'])
             for p in t['peers'])
        )



class TrackerList(tuple):
    _STATES_ANNOUNCE = {
        # From libtransmission/transmission.h:
        # /* we won't (announce,scrape) this torrent to this tracker because
        #  * the torrent is stopped, or because of an error, or whatever */
        0: 'stopped',
        # /* we will (announce,scrape) this torrent to this tracker, and are
        #  * waiting for enough time to pass to satisfy the tracker's interval */
        1: 'idle',
        # /* it's time to (announce,scrape) this torrent, and we're waiting on a
        #  * a free slot to open up in the announce manager */
        2: 'queued',
        # /* we're (announcing,scraping) this torrent right now */
        3: 'announcing',
    }
    _STATES_SCRAPE = {0: 'stopped', 1: 'idle', 2: 'queued', 3: 'scraping'}

    @staticmethod
    def _error_announce(tracker):
        msg = tracker['lastAnnounceResult'] if tracker['hasAnnounced'] else ''
        return '' if msg == 'Success' else msg

    @staticmethod
    def _error_scrape(tracker):
        msg = tracker['lastScrapeResult'] if tracker['hasScraped'] else ''
        return '' if msg == 'Success' else msg

    @staticmethod
    def _next_time(tracker, which):
        """
        Handle next(Announce|Scrape)Time RPC key

        `which` must be 'Scrape' or 'Announce'.

        transmission.h says:
            /* when the next periodic (announce|scrape) message will be sent out.
               if (announce|scrape)State isn't TR_TRACKER_WAITING, this field is undefined */
        """
        state = tracker['%sState' % which.lower()]
        if state == 1:    # TR_TRACKER_WAITING = 1
            return tracker['next%sTime' % which]
        elif state == 0:  # Torrent is paused
            return ttypes.Timestamp.NOT_APPLICABLE
        elif state == 2:  # Announce/scrape is queued
            return ttypes.Timestamp.SOON
        else:
            return ttypes.Timestamp.NOW

    @staticmethod
    def _last_time(tracker, which):
        """
        Handle last(Announce|Scrape)Time RPC key

        `which` must be 'Scrape' or 'Announce'.

        transmission.h says:
            /* when the last (announce|scrape) was completed.
               if "has(Announced|Scraped)" is false, this field is undefined */
        """
        if tracker['has%sd' % which]:
            return tracker['last%sTime' % which]
        else:
            return ttypes.Timestamp.NEVER

    def __new__(cls, raw_torrent):
        return super().__new__(cls,
            (ttypes.TorrentTracker(
                (LazyDict({
                    'id'                 : (raw_torrent['id'], raw_tracker['id']),
                    'tid'                : raw_torrent['id'],
                    'tname'              : raw_torrent['name'],
                    'tier'               : raw_tracker['tier'],

                    'url-announce'       : raw_tracker['announce'],
                    'url-scrape'         : raw_tracker['scrape'],

                    'status-announce'    : cls._STATES_ANNOUNCE[raw_tracker['announceState']],
                    'status-scrape'      : cls._STATES_SCRAPE[raw_tracker['scrapeState']],

                    'error-announce'     : lambda: cls._error_announce(raw_tracker),
                    'error-scrape'       : lambda: cls._error_scrape(raw_tracker),

                    'count-downloads'    : raw_tracker['downloadCount'],
                    'count-leeches'      : raw_tracker['leecherCount'],
                    'count-seeds'        : raw_tracker['seederCount'],

                    'time-last-announce' : lambda: cls._last_time(raw_tracker, 'Announce'),
                    'time-last-scrape'   : lambda: cls._last_time(raw_tracker, 'Scrape'),
                    'time-next-announce' : lambda: cls._next_time(raw_tracker, 'Announce'),
                    'time-next-scrape'   : lambda: cls._next_time(raw_tracker, 'Scrape'),
                }))) for raw_tracker in raw_torrent['trackerStats'])
        )



# Map our keys to tuples of needed RPC field names for those keys
DEPENDENCIES = {
    'id'                           : ('id',),
    'hash'                         : ('hashString',),
    'name'                         : ('name',),
    'ratio'                        : ('uploadRatio',),
    'status'                       : ('status', 'percentDone', 'metadataPercentComplete', 'rateDownload',
                                      'rateUpload', 'peersConnected', 'trackerStats', 'isPrivate'),
    'path'                         : ('downloadDir',),
    'private'                      : ('isPrivate',),
    'comment'                      : ('comment',),
    'creator'                      : ('creator',),
    'magnetlink'                   : ('magnetLink',),
    'count-pieces'                 : ('pieceCount',),

    '%downloaded'                  : ('percentDone',),
    '%uploaded'                    : ('totalSize', 'uploadedEver'),
    '%metadata'                    : ('metadataPercentComplete',),
    '%verified'                    : ('recheckProgress',),
    '%available'                   : ('haveValid', 'haveUnchecked', 'desiredAvailable', 'sizeWhenDone'),

    'peers-connected'              : ('peersConnected',),
    'peers-uploading'              : ('peersSendingToUs',),
    'peers-downloading'            : ('peersGettingFromUs',),
    'peers-seeding'                : ('trackerStats',),

    'timespan-eta'                 : ('eta',),
    'timespan-seeding'             : ('secondsSeeding',),
    'timespan-downloading'         : ('secondsDownloading',),
    'time-created'                 : ('dateCreated',),
    'time-added'                   : ('addedDate',),
    'time-started'                 : ('startDate',),
    'time-activity'                : ('activityDate',),
    'time-completed'               : ('doneDate', 'addedDate', 'percentDone', 'eta'),
    'time-manual-announce-allowed' : ('manualAnnounceTime',),

    'rate-down'                    : ('rateDownload',),
    'rate-up'                      : ('rateUpload',),
    'limit-rate-down'              : ('downloadLimited', 'downloadLimit'),
    'limit-rate-up'                : ('uploadLimited', 'uploadLimit'),

    'size-final'                   : ('sizeWhenDone',),
    'size-total'                   : ('totalSize',),
    'size-downloaded'              : ('downloadedEver',),
    'size-uploaded'                : ('uploadedEver',),
    'size-available'               : ('leftUntilDone', 'desiredAvailable', 'haveValid', 'haveUnchecked'),
    'size-left'                    : ('leftUntilDone',),
    'size-corrupt'                 : ('corruptEver',),
    'size-piece'                   : ('pieceSize',),

    'error'                        : ('errorString', 'error', 'trackerStats'),
    'trackers'                     : ('trackerStats', 'name', 'id'),
    'peers'                        : ('peers', 'totalSize', 'name'),
    'files'                        : ('files', 'fileStats', 'downloadDir'),
}

# Map our keys to callables that adjust the raw RPC values or create new
# values from existing RPC values.
_MODIFY = {
    '%downloaded'                  : lambda raw: raw['percentDone'] * 100,
    '%uploaded'                    : _percent_uploaded,
    '%metadata'                    : lambda raw: raw['metadataPercentComplete'] * 100,
    '%verified'                    : lambda raw: raw['recheckProgress'] * 100,
    '%available'                   : _percent_available,
    'status'                       : _make_status,
    'peers-seeding'                : _count_seeds,
    'ratio'                        : _modify_ratio,
    'size-available'               : _bytes_available,

    # Transmission provides rate limits in kilobytes - we want bytes
    'limit-rate-down'              : lambda raw: None if not raw['downloadLimited'] else raw['downloadLimit'] * 1000,
    'limit-rate-up'                : lambda raw: None if not raw['uploadLimited']   else raw['uploadLimit']   * 1000,

    'timespan-eta'                 : _modify_eta,
    'time-created'                 : lambda raw: _modify_timestamp(raw, 'dateCreated',
                                                                   zero_means=ttypes.Timestamp.UNKNOWN),
    'time-added'                   : lambda raw: _modify_timestamp(raw, 'addedDate',
                                                                   zero_means=ttypes.Timestamp.UNKNOWN),
    'time-started'                 : lambda raw: _modify_timestamp(raw, 'startDate',
                                                                   zero_means=ttypes.Timestamp.NOT_APPLICABLE),
    'time-activity'                : lambda raw: _modify_timestamp(raw, 'activityDate',
                                                                   zero_means=ttypes.Timestamp.NEVER),
    'time-completed'               : lambda raw: _modify_timestamp_completed(raw),
    'time-manual-announce-allowed' : lambda raw: _modify_timestamp(raw, 'manualAnnounceTime',
                                                                   zero_means=ttypes.Timestamp.NEVER),

    'error'                        : _find_error,
    'trackers'                     : TrackerList,
    'peers'                        : PeerList,
    'files'                        : TorrentFileTree.create,
}

class Torrent(base.TorrentBase):
    """
    Information about a torrent as a mapping

    The available keys are specified in DEPENDENCIES and ttypes.TYPES.
    """

    def __init__(self, raw_torrent):
        self._raw = raw_torrent
        self._cache = {}

    def update(self, raw_torrent):
        cache = self._cache
        raw_old = self._raw

        # Remove cached values if their original/raw value(s) differ
        for k in tuple(cache):
            # Each key depends on one or more RPC field
            fields = DEPENDENCIES[k]
            for field in fields:
                new_value = raw_torrent.get(field)
                old_value = raw_old.get(field)
                if new_value is not None and new_value != old_value:
                    # log.debug('Invalidating cached %s/%s: %r -> %r', k, field, old_value, new_value)
                    # New and previous value differ - if we are dealing with
                    # more complex data structures (e.g. a file tree), use the
                    # update() method to update the object in cache instead of
                    # removing it from the cache.
                    value = cache[k]
                    if hasattr(value, 'update') and all(field in raw_torrent for field in fields):
                        value.update(raw_torrent)
                    del cache[k]
                    break

        # Now we can forget the old values
        raw_old.update(raw_torrent)

    def __getitem__(self, key):
        cache = self._cache
        if key not in cache:
            raw = self._raw
            if key in _MODIFY:
                # Modifier gets the whole raw torrent
                value = _MODIFY[key](raw)
            else:
                # Copy raw value unmodified
                fields = DEPENDENCIES[key]
                value = raw[fields[0]]
            cache[key] = ttypes.TYPES[key](value)
        return cache[key]

    def __contains__(self, key):
        deps = DEPENDENCIES
        raw = self._raw
        # Check if key is known
        if key not in deps:
            return False
        else:
            # Check if we have all dependencies for key
            for dep in deps[key]:
                if dep not in raw:
                    return False
        return True

    def __iter__(self):
        for key in DEPENDENCIES:
            if key in self:
                yield key

    def __eq__(self, other):
        if hasattr(other, '_raw'):
            return self._raw['id'] == other._raw['id']
        else:
            return NotImplemented

    def __lt__(self, other):
        if hasattr(other, '_raw'):
            return self._raw['id'] > other._raw['id']
        else:
            return NotImplemented

    def __hash__(self):
        return hash(self._raw['id'])

    def clearcache(self):
        self._cache = {}


class TorrentFields(tuple):
    """
    Convert Torrent keys to those specified in rpc-spec.txt

    The resulting tuple has no duplicates and the keys 'id' and 'name' are
    always included.
    """
    _RPC_FIELDS = ('activityDate', 'addedDate', 'announceResponse', 'announceURL',
                   'bandwidthPriority', 'comment', 'corruptEver', 'creator',
                   'dateCreated', 'desiredAvailable', 'doneDate', 'downloadDir',
                   'downloadedEver', 'downloadLimit', 'downloadLimited',
                   'downloadLimitMode', 'error', 'errorString', 'eta', 'etaIdle',
                   'hashString', 'haveUnchecked', 'haveValid', 'honorsSessionLimits',
                   'id', 'isFinished', 'isPrivate', 'isStalled', 'lastAnnounceTime',
                   'lastScrapeTime', 'leftUntilDone', 'magnetLink',
                   'manualAnnounceTime', 'maxConnectedPeers',
                   'metadataPercentComplete', 'name', 'nextAnnounceTime',
                   'nextScrapeTime', 'peer-limit', 'peersConnected',
                   'peersGettingFromUs', 'peersSendingToUs', 'percentDone',
                   'pieceCount', 'pieceSize', 'queuePosition', 'rateDownload',
                   'rateUpload', 'recheckProgress', 'secondsDownloading',
                   'secondsSeeding', 'scrapeResponse', 'scrapeURL', 'seedIdleLimit',
                   'seedIdleMode', 'seedRatioLimit', 'seedRatioMode', 'sizeWhenDone',
                   'startDate', 'status', 'totalSize', 'torrentFile', 'uploadedEver',
                   'uploadLimit', 'uploadLimitMode', 'uploadLimited', 'uploadRatio',
                   'webseedsSendingToUs',

                   # Lists ('files' is handled internally in api_torrent -
                   # request 'fileStats' instead)
                   'fileStats', 'peers', 'peersFrom', 'pieces', 'priorities',
                   'trackers', 'trackerStats', 'wanted', 'webseeds')

    _ALL_FIELDS = tuple(set(field
                            for fields in DEPENDENCIES.values()
                            for field in fields))
    _cache = {}

    def __new__(cls, *keys):
        if keys not in cls._cache:
            cls._cache[keys] = super().__new__(cls, cls._get_fields(*keys))
        return cls._cache[keys]

    @classmethod
    def _get_fields(cls, *keys):
        collected_fields = set(('id',))
        for key in keys:
            if key.lower() == 'all':
                return cls._ALL_FIELDS
            elif key in DEPENDENCIES:
                # key is one of Torrent's keys that needs one or more RPC fields
                collected_fields.update(DEPENDENCIES[key])
            elif key in cls._RPC_FIELDS:
                # key is a valid Transmission RPC field
                collected_fields.add(key)
            else:
                raise ValueError('Unknown torrent key: {!r}'.format(key))
        return collected_fields

    def __add__(self, other):
        if isinstance(other, (type(self), set, list, tuple)):
            fields = set(self)  # Make a copy
            fields.update(other)
            return type(self)(*fields)
        else:
            return NotImplemented

    def __eq__(self, other):
        return set(self) == set(other)

    def __ne__(self, other):
        return not self.__eq__(other)
