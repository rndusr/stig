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

"""
Translation between the RPC strings of Transmission <4.1.0 and >=4.1.0

Transmission 4.1.0 didn't only add the JSON-RPC 2.0 protocol, it also renamed
every RPC string from the old mix of kebab-case and camelCase to snake_case.
The old strings are only understood by the old bespoke protocol, so JSON-RPC 2.0
requests must use the new strings and their responses contain the new strings.

The rest of stig speaks the old strings, so requests are translated on their way
out and responses on their way back in.  This mirrors what the daemon does for
old-protocol requests in libtransmission/api-compat.cc.
"""


# (current name, legacy name) pairs, taken from the RpcKeys table in
# libtransmission/api-compat.cc
_RPC_KEYS = (
    ('active_torrent_count',                 'activeTorrentCount'),
    ('activity_date',                        'activityDate'),
    ('added_date',                           'addedDate'),
    ('alt_speed_down',                       'alt-speed-down'),
    ('alt_speed_enabled',                    'alt-speed-enabled'),
    ('alt_speed_time_begin',                 'alt-speed-time-begin'),
    ('alt_speed_time_day',                   'alt-speed-time-day'),
    ('alt_speed_time_enabled',               'alt-speed-time-enabled'),
    ('alt_speed_time_end',                   'alt-speed-time-end'),
    ('alt_speed_up',                         'alt-speed-up'),
    ('announce_state',                       'announceState'),
    ('anti_brute_force_enabled',             'anti-brute-force-enabled'),
    ('anti_brute_force_threshold',           'anti-brute-force-threshold'),
    ('bandwidth_priority',                   'bandwidthPriority'),
    ('blocklist_enabled',                    'blocklist-enabled'),
    ('blocklist_size',                       'blocklist-size'),
    ('blocklist_update',                     'blocklist-update'),
    ('blocklist_url',                        'blocklist-url'),
    ('bytes_completed',                      'bytesCompleted'),
    ('cache_size_mib',                       'cache-size-mb'),
    ('client_is_choked',                     'clientIsChoked'),
    ('client_is_interested',                 'clientIsInterested'),
    ('client_name',                          'clientName'),
    ('config_dir',                           'config-dir'),
    ('corrupt_ever',                         'corruptEver'),
    ('cumulative_stats',                     'cumulative-stats'),
    ('current_stats',                        'current-stats'),
    ('date_created',                         'dateCreated'),
    ('default_trackers',                     'default-trackers'),
    ('delete_local_data',                    'delete-local-data'),
    ('desired_available',                    'desiredAvailable'),
    ('dht_enabled',                          'dht-enabled'),
    ('done_date',                            'doneDate'),
    ('download_count',                       'downloadCount'),
    ('download_dir',                         'download-dir'),
    ('download_dir_free_space',              'download-dir-free-space'),
    ('download_limit',                       'downloadLimit'),
    ('download_limited',                     'downloadLimited'),
    ('download_queue_enabled',               'download-queue-enabled'),
    ('download_queue_size',                  'download-queue-size'),
    ('download_speed',                       'downloadSpeed'),
    ('downloaded_bytes',                     'downloadedBytes'),
    ('downloaded_ever',                      'downloadedEver'),
    ('edit_date',                            'editDate'),
    ('error_string',                         'errorString'),
    ('eta_idle',                             'etaIdle'),
    ('file_count',                           'file-count'),
    ('file_stats',                           'fileStats'),
    ('files_added',                          'filesAdded'),
    ('files_unwanted',                       'files-unwanted'),
    ('files_wanted',                         'files-wanted'),
    ('flag_str',                             'flagStr'),
    ('free_space',                           'free-space'),
    ('from_cache',                           'fromCache'),
    ('from_dht',                             'fromDht'),
    ('from_incoming',                        'fromIncoming'),
    ('from_lpd',                             'fromLpd'),
    ('from_ltep',                            'fromLtep'),
    ('from_pex',                             'fromPex'),
    ('from_tracker',                         'fromTracker'),
    ('group_get',                            'group-get'),
    ('group_set',                            'group-set'),
    ('has_announced',                        'hasAnnounced'),
    ('has_scraped',                          'hasScraped'),
    ('hash_string',                          'hashString'),
    ('have_unchecked',                       'haveUnchecked'),
    ('have_valid',                           'haveValid'),
    ('honors_session_limits',                'honorsSessionLimits'),
    ('idle_seeding_limit',                   'idle-seeding-limit'),
    ('idle_seeding_limit_enabled',           'idle-seeding-limit-enabled'),
    ('incomplete_dir',                       'incomplete-dir'),
    ('incomplete_dir_enabled',               'incomplete-dir-enabled'),
    ('is_backup',                            'isBackup'),
    ('is_downloading_from',                  'isDownloadingFrom'),
    ('is_encrypted',                         'isEncrypted'),
    ('is_finished',                          'isFinished'),
    ('is_incoming',                          'isIncoming'),
    ('is_private',                           'isPrivate'),
    ('is_stalled',                           'isStalled'),
    ('is_uploading_to',                      'isUploadingTo'),
    ('is_utp',                               'isUTP'),
    ('last_announce_peer_count',             'lastAnnouncePeerCount'),
    ('last_announce_result',                 'lastAnnounceResult'),
    ('last_announce_start_time',             'lastAnnounceStartTime'),
    ('last_announce_succeeded',              'lastAnnounceSucceeded'),
    ('last_announce_time',                   'lastAnnounceTime'),
    ('last_announce_timed_out',              'lastAnnounceTimedOut'),
    ('last_scrape_result',                   'lastScrapeResult'),
    ('last_scrape_start_time',               'lastScrapeStartTime'),
    ('last_scrape_succeeded',                'lastScrapeSucceeded'),
    ('last_scrape_time',                     'lastScrapeTime'),
    ('last_scrape_timed_out',                'lastScrapeTimedOut'),
    ('leecher_count',                        'leecherCount'),
    ('left_until_done',                      'leftUntilDone'),
    ('lpd_enabled',                          'lpd-enabled'),
    ('magnet_link',                          'magnetLink'),
    ('manual_announce_time',                 'manualAnnounceTime'),
    ('max_connected_peers',                  'maxConnectedPeers'),
    ('memory_bytes',                         'memory-bytes'),
    ('memory_units',                         'memory-units'),
    ('metadata_percent_complete',            'metadataPercentComplete'),
    ('next_announce_time',                   'nextAnnounceTime'),
    ('next_scrape_time',                     'nextScrapeTime'),
    ('paused_torrent_count',                 'pausedTorrentCount'),
    ('peer_is_choked',                       'peerIsChoked'),
    ('peer_is_interested',                   'peerIsInterested'),
    ('peer_limit',                           'peer-limit'),
    ('peer_limit_global',                    'peer-limit-global'),
    ('peer_limit_per_torrent',               'peer-limit-per-torrent'),
    ('peer_port',                            'peer-port'),
    ('peer_port_random_on_start',            'peer-port-random-on-start'),
    ('peers_connected',                      'peersConnected'),
    ('peers_from',                           'peersFrom'),
    ('peers_getting_from_us',                'peersGettingFromUs'),
    ('peers_sending_to_us',                  'peersSendingToUs'),
    ('percent_complete',                     'percentComplete'),
    ('percent_done',                         'percentDone'),
    ('pex_enabled',                          'pex-enabled'),
    ('piece_count',                          'pieceCount'),
    ('piece_size',                           'pieceSize'),
    ('port_forwarding_enabled',              'port-forwarding-enabled'),
    ('port_is_open',                         'port-is-open'),
    ('port_test',                            'port-test'),
    ('primary_mime_type',                    'primary-mime-type'),
    ('priority_high',                        'priority-high'),
    ('priority_low',                         'priority-low'),
    ('priority_normal',                      'priority-normal'),
    ('queue_move_bottom',                    'queue-move-bottom'),
    ('queue_move_down',                      'queue-move-down'),
    ('queue_move_top',                       'queue-move-top'),
    ('queue_move_up',                        'queue-move-up'),
    ('queue_position',                       'queuePosition'),
    ('queue_stalled_enabled',                'queue-stalled-enabled'),
    ('queue_stalled_minutes',                'queue-stalled-minutes'),
    ('rate_download',                        'rateDownload'),
    ('rate_to_client',                       'rateToClient'),
    ('rate_to_peer',                         'rateToPeer'),
    ('rate_upload',                          'rateUpload'),
    ('recently_active',                      'recently-active'),
    ('recheck_progress',                     'recheckProgress'),
    ('rename_partial_files',                 'rename-partial-files'),
    ('rpc_host_whitelist',                   'rpc-host-whitelist'),
    ('rpc_host_whitelist_enabled',           'rpc-host-whitelist-enabled'),
    ('rpc_version',                          'rpc-version'),
    ('rpc_version_minimum',                  'rpc-version-minimum'),
    ('rpc_version_semver',                   'rpc-version-semver'),
    ('scrape_state',                         'scrapeState'),
    ('script_torrent_added_enabled',         'script-torrent-added-enabled'),
    ('script_torrent_added_filename',        'script-torrent-added-filename'),
    ('script_torrent_done_enabled',          'script-torrent-done-enabled'),
    ('script_torrent_done_filename',         'script-torrent-done-filename'),
    ('script_torrent_done_seeding_enabled',  'script-torrent-done-seeding-enabled'),
    ('script_torrent_done_seeding_filename', 'script-torrent-done-seeding-filename'),
    ('seconds_active',                       'secondsActive'),
    ('seconds_downloading',                  'secondsDownloading'),
    ('seconds_seeding',                      'secondsSeeding'),
    ('seed_idle_limit',                      'seedIdleLimit'),
    ('seed_idle_mode',                       'seedIdleMode'),
    ('seed_queue_enabled',                   'seed-queue-enabled'),
    ('seed_queue_size',                      'seed-queue-size'),
    ('seed_ratio_limit',                     'seedRatioLimit'),
    ('seed_ratio_limited',                   'seedRatioLimited'),
    ('seed_ratio_mode',                      'seedRatioMode'),
    ('seeder_count',                         'seederCount'),
    ('session_close',                        'session-close'),
    ('session_count',                        'sessionCount'),
    ('session_get',                          'session-get'),
    ('session_id',                           'session-id'),
    ('session_set',                          'session-set'),
    ('session_stats',                        'session-stats'),
    ('size_bytes',                           'size-bytes'),
    ('size_units',                           'size-units'),
    ('size_when_done',                       'sizeWhenDone'),
    ('speed_bytes',                          'speed-bytes'),
    ('speed_limit_down',                     'speed-limit-down'),
    ('speed_limit_down_enabled',             'speed-limit-down-enabled'),
    ('speed_limit_up',                       'speed-limit-up'),
    ('speed_limit_up_enabled',               'speed-limit-up-enabled'),
    ('speed_units',                          'speed-units'),
    ('start_added_torrents',                 'start-added-torrents'),
    ('start_date',                           'startDate'),
    ('tcp_enabled',                          'tcp-enabled'),
    ('torrent_add',                          'torrent-add'),
    ('torrent_added',                        'torrent-added'),
    ('torrent_count',                        'torrentCount'),
    ('torrent_duplicate',                    'torrent-duplicate'),
    ('torrent_file',                         'torrentFile'),
    ('torrent_get',                          'torrent-get'),
    ('torrent_reannounce',                   'torrent-reannounce'),
    ('torrent_remove',                       'torrent-remove'),
    ('torrent_rename_path',                  'torrent-rename-path'),
    ('torrent_set',                          'torrent-set'),
    ('torrent_set_location',                 'torrent-set-location'),
    ('torrent_start',                        'torrent-start'),
    ('torrent_start_now',                    'torrent-start-now'),
    ('torrent_stop',                         'torrent-stop'),
    ('torrent_verify',                       'torrent-verify'),
    ('total_size',                           'totalSize'),
    ('tracker_add',                          'trackerAdd'),
    ('tracker_list',                         'trackerList'),
    ('tracker_remove',                       'trackerRemove'),
    ('tracker_replace',                      'trackerReplace'),
    ('tracker_stats',                        'trackerStats'),
    ('trash_original_torrent_files',         'trash-original-torrent-files'),
    ('upload_limit',                         'uploadLimit'),
    ('upload_limited',                       'uploadLimited'),
    ('upload_ratio',                         'uploadRatio'),
    ('upload_speed',                         'uploadSpeed'),
    ('uploaded_bytes',                       'uploadedBytes'),
    ('uploaded_ever',                        'uploadedEver'),
    ('utp_enabled',                          'utp-enabled'),
    ('webseeds_sending_to_us',               'webseedsSendingToUs'),
)

# The daemon uses different legacy names for the same value depending on the
# context, so these can't be part of the lookup tables below.
_DOWNLOAD_DIR_LEGACY_TORRENT   = 'downloadDir'   # torrent-get/torrent-set
_DOWNLOAD_DIR_LEGACY_SESSION   = 'download-dir'  # session-get/session-set/torrent-add
_TOTAL_SIZE_LEGACY_TORRENT     = 'totalSize'     # torrent-get
_TOTAL_SIZE_LEGACY_FREE_SPACE  = 'total_size'    # free-space

TO_CURRENT = {legacy: current for current,legacy in _RPC_KEYS}
TO_CURRENT[_DOWNLOAD_DIR_LEGACY_TORRENT] = 'download_dir'
TO_CURRENT[_TOTAL_SIZE_LEGACY_FREE_SPACE] = 'total_size'

TO_LEGACY = {current: legacy for current,legacy in _RPC_KEYS}

# Methods whose arguments and response use the torrent flavour of the ambiguous
# legacy names above
_TORRENT_METHODS = ('torrent_get', 'torrent_set')

# Values of these keys are RPC strings themselves and must be translated, too
_KEYS_WITH_RPC_STRINGS = ('fields', 'ids', 'method', 'torrents')


def _convert_key(name, names, is_torrent):
    if names is TO_LEGACY:
        if name == 'download_dir':
            return _DOWNLOAD_DIR_LEGACY_TORRENT if is_torrent else _DOWNLOAD_DIR_LEGACY_SESSION
        elif name == 'total_size':
            return _TOTAL_SIZE_LEGACY_TORRENT if is_torrent else _TOTAL_SIZE_LEGACY_FREE_SPACE
    return names.get(name, name)


def _convert(obj, names, is_torrent, key=None):
    if isinstance(obj, dict):
        converted = {}
        for k,v in obj.items():
            new_key = _convert_key(k, names, is_torrent)
            converted[new_key] = _convert(v, names, is_torrent, new_key)
        return converted
    elif isinstance(obj, (list, tuple)):
        return [_convert(item, names, is_torrent, key) for item in obj]
    elif isinstance(obj, str) and key in _KEYS_WITH_RPC_STRINGS:
        return _convert_key(obj, names, is_torrent)
    else:
        return obj


def _wanted_to_legacy(result):
    """Transmission >=4.1.0 reports 'wanted' as booleans, older versions as 0/1"""
    if isinstance(result, dict):
        for torrent in result.get('torrents', ()):
            if isinstance(torrent, dict):
                wanted = torrent.get('wanted')
                if isinstance(wanted, list) and all(isinstance(w, bool) for w in wanted):
                    torrent['wanted'] = [int(w) for w in wanted]


def request_to_current(method, arguments):
    """Return copy of `arguments` with legacy RPC strings replaced by current ones"""
    return _convert(arguments, TO_CURRENT, method in _TORRENT_METHODS)


def response_to_legacy(method, result):
    """Return copy of `result` with current RPC strings replaced by legacy ones"""
    is_torrent = (method in _TORRENT_METHODS
                  or (isinstance(result, dict) and 'torrents' in result))
    converted = _convert(result, TO_LEGACY, is_torrent)
    _wanted_to_legacy(converted)
    return converted
