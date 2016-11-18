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


from .. import tkeys as tkeys
from .. import utils
from ..base import TorrentBase


# Some values need to be modified to comply with our internal standards

def _modify_ratio(ratio):
    #define TR_RATIO_NA  -1
    #define TR_RATIO_INF -2
    return tkeys.Ratio.UNKNOWN if ratio in (-1, -2) else ratio

def _modify_eta(seconds):
    #define TR_ETA_NOT_AVAIL -1
    #define TR_ETA_UNKNOWN -2
    if seconds == -1:
        return tkeys.Timedelta.NOT_APPLICABLE
    elif seconds == -2:
        return tkeys.Timedelta.UNKNOWN
    return  seconds

def _count_seeds(trackerStats):
    if trackerStats:
        return max(t['seederCount'] for t in trackerStats)
    else:
        return tkeys.SeedCount.UNKNOWN

def _is_isolated(trackerStats, isPrivate):
    """Return whether this torrent can find any peers via trackers or DHT"""
    if not isPrivate:
        return False  # DHT is used

    # Torrent has trackers?
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

_STATUS_MAP = {
    0: tkeys.Status.STOPPED,
    1: tkeys.Status.VERIFY_Q,
    2: tkeys.Status.VERIFY,
    3: tkeys.Status.LEECH_Q,
    4: tkeys.Status.LEECH,
    5: tkeys.Status.SEED_Q,
    6: tkeys.Status.SEED,
}


class FileList(tuple):
    def __new__(cls, files, fileStats):
        return super().__new__(cls,
            (tkeys.TorrentFile(name=f['name'],
                               size_total=f['length'],
                               size_downloaded=f['bytesCompleted'],
                               is_wanted=fS['wanted'],
                               priority=fS['priority'])
             for f,fS in zip(files, fileStats))
        )


class TrackerList(tuple):
    def __new__(cls, trackers):
        return super().__new__(cls,
            ({'id': tracker['id'],
              'url-announce': utils.split_url(tracker['announce'])}
             for tracker in trackers)
        )


# Map our keys to tuples of needed RPC field names for those keys
DEPENDENCIES = {
    'id'                : ('id',),
    'hash'              : ('hashString',),
    'name'              : ('name',),
    'status'            : ('status',),
    'path'              : ('downloadDir',),

    'private'           : ('isPrivate',),
    'stalled'           : ('isStalled',),
    'isolated'          : ('trackerStats', 'isPrivate'),

    '%downloaded'       : ('percentDone',),
    '%metadata'         : ('metadataPercentComplete',),
    '%verified'         : ('recheckProgress',),

    'peers-connected'   : ('peersConnected',),
    'peers-uploading'   : ('peersSendingToUs',),
    'peers-downloading' : ('peersGettingFromUs',),
    'peers-seeding'     : ('trackerStats',),

    'timestamp-created' : ('dateCreated',),
    'timestamp-added'   : ('addedDate',),
    'timestamp-started' : ('startDate',),
    'timestamp-active'  : ('activityDate',),
    'timestamp-done'    : ('doneDate',),
    'timespan-eta'      : ('eta',),

    'ratio'             : ('uploadRatio',),
    'rate-down'         : ('rateDownload',),
    'rate-up'           : ('rateUpload',),

    'size-final'        : ('sizeWhenDone',),
    'size-total'        : ('totalSize',),
    'size-downloaded'   : ('downloadedEver',),
    'size-uploaded'     : ('uploadedEver',),
    'size-available'    : ('desiredAvailable',),
    'size-corrupt'      : ('corruptEver',),

    'trackers'          : ('trackers',),
    'files'             : ('files', 'fileStats'),
}

# Map our keys to callables that adjust the raw RPC values or create new
# values from existing RPC values (see 'isolated').
_MODIFY = {
    '%downloaded'     : lambda v: v*100,
    '%metadata'       : lambda v: v*100,
    '%verified'       : lambda v: v*100,
    'status'          : lambda v: _STATUS_MAP[v],
    'peers-seeding'   : _count_seeds,
    'isolated'        : _is_isolated,
    'ratio'           : _modify_ratio,
    'timespan-eta'    : _modify_eta,
    'trackers'        : TrackerList,
    'files'           : FileList,
}

class Torrent(TorrentBase):
    """Information about a torrent as a mapping

    The available keys are specified in DEPENDENCIES and tkeys.TYPES.
    """

    def __init__(self, raw_torrent):
        self._raw = raw_torrent
        self._cache = {}

    def update(self, raw_torrent):
        old = self._raw
        cache = self._cache
        for k,v in tuple(cache.items()):
            fields = DEPENDENCIES[k]
            for field in fields:
                if field in old and field in raw_torrent and \
                   old[field] != raw_torrent[field]:
                    del cache[k]
                    break
        old.update(raw_torrent)

    def __getitem__(self, key):
        if key not in self._cache:
            if key in _MODIFY:
                # Modifier gets all values specified in DEPENDENCIES
                args = tuple(self._raw[field] for field in DEPENDENCIES[key])
                value = _MODIFY[key](*args)
            else:
                fields = DEPENDENCIES[key]
                assert len(fields) == 1
                try:
                    value = self._raw[fields[0]]
                except KeyError:
                    log.debug('%r not in %s', fields[0], tuple(self._raw))
                    raise KeyError(key)
            self._cache[key] = tkeys.TYPES[key](value)
        return self._cache[key]

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
        if isinstance(other, int):
            return self._raw['id'] == other
        elif isinstance(other, Torrent):
            return self._raw['id'] == other._raw['id']
        else:
            return NotImplemented

    def __lt__(self, other):
        return self._raw['id'] > other._raw['id']

    def __hash__(self):
        return hash(self._raw['id'])

    def clearcache(self):
        self._cache = {}


class TorrentFields(tuple):
    """Convert Torrent keys to those specified in rpc-spec.txt

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

                   # Lists
                   'files', 'fileStats', 'peers', 'peersFrom', 'pieces', 'priorities',
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
