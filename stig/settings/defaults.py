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

import os
from xdg.BaseDirectory import xdg_config_home as XDG_CONFIG_HOME
from xdg.BaseDirectory import xdg_cache_home  as XDG_CACHE_HOME
from xdg.BaseDirectory import xdg_data_home  as XDG_DATA_HOME

from .. import __appname__
from ..views import (torrent, file, peer, tracker, setting)
from ..client.sorters.torrent import TorrentSorter
from ..client.sorters.peer import TorrentPeerSorter
from ..client.sorters.tracker import TorrentTrackerSorter
from ..client.sorters.setting import SettingSorter

DEFAULT_RCFILE      = os.path.join(XDG_CONFIG_HOME, __appname__, 'rc')
DEFAULT_HISTORY_DIR = os.path.join(XDG_DATA_HOME, __appname__, 'histories')
DEFAULT_GEOIP_DIR   = os.path.join(XDG_CACHE_HOME, __appname__)
DEFAULT_THEME_FILE  = os.path.join(os.path.dirname(__file__), 'default.theme')


def init_defaults(localcfg):
    from ..utils.usertypes import (String, Int, Float, Bool, Path, Tuple, Option)

    class SortOrder(str):
        """String that is equal to the same string with '!' or '.' prepended"""
        _invert_chars = ''.join(TorrentSorter.INVERT_CHARS)
        def __eq__(self, other):
            return self.lstrip(self._invert_chars) == other.lstrip(self._invert_chars)

        # An overloaded __eq__() obligates an overloaded __hash__(), or
        # instances won't be hashable.
        def __hash__(self):
            return super().__hash__()


    def partial_sort_order(sortercls):
        options = tuple(SortOrder(opt) for opt in sortercls.SORTSPECS)
        return Tuple.partial(options=options, dedup=True)

    localcfg.add('connect.host',
                 constructor=String.partial(),
                 default='localhost',
                 description='Hostname or IP of Transmission RPC interface')
    localcfg.add('connect.port',
                 Int.partial(min=1, max=65535, prefix='none'),
                 default=9091,
                 description='Port of Transmission RPC interface')
    localcfg.add('connect.path',
                 String.partial(),
                 default='/transmission/rpc',
                 description='Path of Transmission RPC interface')
    localcfg.add('connect.user',
                 String.partial(),
                 default='',
                 description='Username to use for authentication with Transmission RPC interface')
    localcfg.add('connect.password',
                 String.partial(),
                 default='',
                 description='Password to use for authentication with Transmission RPC interface')
    localcfg.add('connect.timeout',
                 Float.partial(min=0),
                 default=10,
                 description='Number of seconds before connecting to Transmission RPC interface fails')
    localcfg.add('connect.tls',
                 Bool.partial(),
                 default='off',
                 description='Whether to connect via HTTPS to the Transmission RPC interface')

    localcfg.add('columns.torrents',
                 Tuple.partial(options=torrent.COLUMNS, aliases=torrent.ALIASES),
                 default=('marked', 'size', 'downloaded', 'uploaded', 'ratio',
                          'seeds', 'peers', 'status', 'eta', '%downloaded',
                          'rate-down', 'rate-up', 'name'),
                 description='Default columns in torrent lists')
    localcfg.add('columns.peers',
                 Tuple.partial(options=peer.COLUMNS, aliases=peer.ALIASES),
                 default=('host', 'client', 'country', '%downloaded', 'rate-down',
                          'rate-up', 'rate-est', 'eta'),
                 description='Default columns in peer lists')
    localcfg.add('columns.files',
                 Tuple.partial(options=file.COLUMNS, aliases=file.ALIASES),
                 default=('marked', 'priority', '%downloaded', 'downloaded', 'size', 'name'),
                 description='Default columns in file lists')
    localcfg.add('columns.trackers',
                 Tuple.partial(options=tracker.COLUMNS, aliases=tracker.ALIASES),
                 default=('tier', 'domain', 'error', 'last-announce', 'next-announce',
                          'leeches', 'seeds', 'downloads'),
                 description='Default columns in tracker lists')
    localcfg.add('columns.settings',
                 Tuple.partial(options=setting.COLUMNS, aliases=setting.ALIASES),
                 default=('name', 'value', 'default', 'description'),
                 description='Default columns in setting lists')

    localcfg.add('geoip',
                 Bool.partial(),
                 default=True,
                 description='Whether to lookup peers\' country codes')
    localcfg.add('geoip.dir',
                 Path.partial(),
                 default=DEFAULT_GEOIP_DIR,
                 description='Where to cache the downloaded geolocation database')

    localcfg.add('remove.max-hits',
                 Int.partial(),
                 default=10,
                 description=('Maximum number of torrents to remove without extra confirmation'
                              '; negative numbers mean "unlimited"'))

    localcfg.add('reverse-dns',
                 Bool.partial(),
                 default=True,
                 description=('Whether to lookup peers\' host names'))

    localcfg.add('sort.torrents',
                 partial_sort_order(TorrentSorter),
                 default=TorrentSorter.DEFAULT_SORT,
                 description='List of sort orders in torrent lists')
    localcfg.add('sort.peers',
                 partial_sort_order(TorrentPeerSorter),
                 default=TorrentPeerSorter.DEFAULT_SORT,
                 description='List of sort orders in peer lists')
    localcfg.add('sort.trackers',
                 partial_sort_order(TorrentTrackerSorter),
                 default=TorrentTrackerSorter.DEFAULT_SORT,
                 description='List of sort orders in tracker lists')
    localcfg.add('sort.settings',
                 partial_sort_order(SettingSorter),
                 default=SettingSorter.DEFAULT_SORT,
                 description='List of sort orders in setting lists')

    localcfg.add('tui.theme',
                 Path.partial(),
                 default=DEFAULT_THEME_FILE,
                 description='Path to theme file'),
    localcfg.add('tui.log.height',
                 Int.partial(min=1),
                 default=10,
                 description='Maximum height of the log section')
    localcfg.add('tui.log.autohide',
                 Float.partial(min=0),
                 default=10,
                 description=('If the log is hidden, show it for this many seconds '
                              'for new log entries before hiding it again'))
    localcfg.add('tui.cli.history-dir',
                 Path.partial(),
                 default=DEFAULT_HISTORY_DIR,
                 description='Directory where histories of user input are stored')
    localcfg.add('tui.cli.history-size',
                 Int.partial(min=0),
                 default=10000,
                 description='Maximum number of lines to keep in history files')
    localcfg.add('tui.poll',
                 Float.partial(min=0.1),
                 default=5,
                 description='Interval in seconds between TUI updates')

    localcfg.add('unit.bandwidth',
                 Option.partial(options=('bit', 'byte')),
                 default='byte',
                 description="Unit for bandwidth rates ('bit' or 'byte')")
    localcfg.add('unitprefix.bandwidth',
                 Option.partial(options=('metric', 'binary')),
                 default='metric',
                 description=("Unit prefix for bandwidth rates ('metric' or 'binary')"))

    localcfg.add('unit.size',
                 Option.partial(options=('bit', 'byte')),
                 default='byte',
                 description="Unit for file sizes ('bit' or 'byte')")
    localcfg.add('unitprefix.size',
                 Option.partial(options=('metric', 'binary')),
                 default='binary',
                 description=("Unit prefix for file sizes ('metric' or 'binary')"))

    localcfg.add('tui.marked.on',
                 String.partial(minlen=1, maxlen=1),
                 default='●',
                 description=("Character displayed in 'marked' column for marked "
                              "list items (see 'mark' command)"))
    localcfg.add('tui.marked.off',
                 String.partial(minlen=1, maxlen=1),
                 default=' ',
                 description=("Character displayed in 'marked' column for unmarked "
                              "list items (see 'mark' command)"))



DEFAULT_KEYMAP = (
    # Some vi and emacs key translations
    {'key': 'h',      'action': '<left>'},
    {'key': 'j',      'action': '<down>'},
    {'key': 'k',      'action': '<up>'},
    {'key': 'l',      'action': '<right>'},
    {'key': 'g',      'action': '<home>'},
    {'key': 'G',      'action': '<end>'},
    {'key': 'ctrl-n', 'action': '<down>'},
    {'key': 'ctrl-p', 'action': '<up>'},
    {'key': 'ctrl-f', 'action': '<right>'},
    {'key': 'ctrl-b', 'action': '<left>'},

    # Global TUI keys
    {'context': 'main', 'key': 'q',     'action': 'quit',
     'description': 'Exit'},
    {'context': 'main', 'key': ':',     'action': 'tui show cli',
     'description': 'Open command line interface'},
    {'context': 'main', 'key': 'alt-s', 'action': 'tab set',
     'description': 'Open settings in a new tab'},

    # Help
    {'context': 'main', 'key': 'F1+c', 'action': 'tab help commands',
     'description': 'Open help for commands in a new tab'},
    {'context': 'main', 'key': 'F1+s', 'action': 'tab help settings',
     'description': 'Open help for settings in a new tab'},
    {'context': 'main', 'key': 'F1+k', 'action': 'tab help keymap',
     'description': 'Open help for keybindings in a new tab'},
    {'context': 'main', 'key': 'F1+f', 'action': 'tab help filters',
     'description': 'Open help for filters in a new tab'},
    {'context': 'main', 'key': 'F1+r', 'action': 'tab help rcfile',
     'description': 'Open help for rc files in a new tab'},
    {'context': 'main', 'key': '?',    'action': '<F1>'},

    # Hide/Show TUI elements
    {'context': 'main', 'key': 'alt-m', 'action': 'tui toggle main',
     'description': 'Show or hide main area'},
    {'context': 'main', 'key': 'alt-t', 'action': 'tui toggle topbar',
     'description': 'Show or hide top bar'},
    {'context': 'main', 'key': 'alt-b', 'action': 'tui toggle bottombar',
     'description': 'Show or hide bottom bar'},
    {'context': 'main', 'key': 'alt-l', 'action': 'tui toggle log',
     'description': 'Show or hide log messages'},

    # Log messages
    {'context': 'main', 'key': 'ctrl-l',   'action': 'log clear',
     'description': 'Remove all log messages'},
    {'context': 'main', 'key': 'alt-pgup', 'action': 'log scroll page up',
     'description': 'Scroll log messages one page up'},
    {'context': 'main', 'key': 'alt-pgdn', 'action': 'log scroll page down',
     'description': 'Scroll log messages one page down'},
    {'context': 'main', 'key': 'alt-home', 'action': 'log scroll top',
     'description': 'Scroll to top of log messages'},
    {'context': 'main', 'key': 'alt-end',  'action': 'log scroll bottom',
     'description': 'Scroll to bottom of log messages'},

    # Global bandwidth limits
    {'context': 'main', 'key': 'shift-up',    'action': 'rate --quiet dn -- +=100kB global',
     'description': 'Increase global download rate limit by 100 kilobytes'},
    {'context': 'main', 'key': 'shift-down',  'action': 'rate --quiet dn -- -=100kB global',
     'description': 'Decrease global download rate limit by 100 kilobytes'},
    {'context': 'main', 'key': 'shift-right', 'action': 'rate --quiet up -- +=100kB global',
     'description': 'Increase global upload rate limit by 100 kilobytes'},
    {'context': 'main', 'key': 'shift-left',  'action': 'rate --quiet up -- -=100kB global',
     'description': 'Decrease global upload rate limit by 100 kilobytes'},

    # Tab management
    {'context': 'tabs', 'key': 'n',     'action': 'tab',
     'description': 'Open a new empty tab'},
    {'context': 'tabs', 'key': 'd',     'action': 'tab --close',
     'description': 'Remove current tab and focus tab on the right'},
    {'context': 'tabs', 'key': 'D',     'action': 'tab --close --focus left',
     'description': 'Remove current tab and focus tab on the left'},
    {'context': 'tabs', 'key': 'alt-1', 'action': 'tab --focus 1',
     'description': 'Focus first tab'},
    {'context': 'tabs', 'key': 'alt-2', 'action': 'tab --focus 2',
     'description': 'Focus second tab'},
    {'context': 'tabs', 'key': 'alt-3', 'action': 'tab --focus 3',
     'description': 'Focus third tab'},
    {'context': 'tabs', 'key': 'alt-4', 'action': 'tab --focus 4',
     'description': 'Focus fourth tab'},
    {'context': 'tabs', 'key': 'alt-5', 'action': 'tab --focus 5',
     'description': 'Focus fifth tab'},
    {'context': 'tabs', 'key': 'alt-6', 'action': 'tab --focus 6',
     'description': 'Focus sixth tab'},
    {'context': 'tabs', 'key': 'alt-7', 'action': 'tab --focus 7',
     'description': 'Focus seventh tab'},
    {'context': 'tabs', 'key': 'alt-8', 'action': 'tab --focus 8',
     'description': 'Focus eighth tab'},
    {'context': 'tabs', 'key': 'alt-9', 'action': 'tab --focus 9',
     'description': 'Focus ninth tab'},
    {'context': 'tabs', 'key': 'alt-0', 'action': 'tab --focus 10',
     'description': 'Focus tenth tab'},

    # List torrents with different filters
    {'context': 'tabs', 'key': 'f a', 'action': 'tab ls active',
     'description': 'List active torrents in a new tab'},
    {'context': 'tabs', 'key': 'f A', 'action': 'tab ls !active',
     'description': 'List inactive torrents in a new tab'},
    {'context': 'tabs', 'key': 'f i', 'action': 'tab ls isolated --columns name,tracker,error',
     'description': 'List isolated torrents in a new tab'},
    {'context': 'tabs', 'key': 'f p', 'action': 'tab ls paused',
     'description': 'List paused torrents in a new tab'},
    {'context': 'tabs', 'key': 'f P', 'action': 'tab ls !paused',
     'description': 'List unpaused torrents in a new tab'},
    {'context': 'tabs', 'key': 'f c', 'action': 'tab ls complete',
     'description': 'List complete torrents in a new tab'},
    {'context': 'tabs', 'key': 'f C', 'action': 'tab ls !complete',
     'description': 'List incomplete torrents in a new tab'},
    {'context': 'tabs', 'key': 'f u', 'action': 'tab ls uploading',
     'description': 'List uploading torrents in a new tab'},
    {'context': 'tabs', 'key': 'f d', 'action': 'tab ls downloading',
     'description': 'List downloading torrents in a new tab'},
    {'context': 'tabs', 'key': 'f s', 'action': 'tab ls seeding',
     'description': 'List seeding torrents in a new tab'},
    {'context': 'tabs', 'key': 'f l', 'action': 'tab ls leeching',
     'description': 'List leeching torrents in a new tab'},
    {'context': 'tabs', 'key': 'f .', 'action': 'tab ls',
     'description': 'List all torrents in a new tab'},

    # Torrent list actions
    {'context': 'torrentlist', 'key': 's d', 'action': 'sort --add dir',
     'description': 'Sort torrents by download directory'},
    {'context': 'torrentlist', 'key': 's D', 'action': 'sort --add !dir',
     'description': 'Sort torrents by download directory in reverse'},
    {'context': 'torrentlist', 'key': 's e', 'action': 'sort --add eta',
     'description': 'Sort torrents by estimated remaining download time'},
    {'context': 'torrentlist', 'key': 's E', 'action': 'sort --add !eta',
     'description': 'Sort torrents by estimated remaining download time in reverse'},
    {'context': 'torrentlist', 'key': 's n', 'action': 'sort --add name',
     'description': 'Sort torrents by name'},
    {'context': 'torrentlist', 'key': 's N', 'action': 'sort --add !name',
     'description': 'Sort torrents by name in reverse'},
    {'context': 'torrentlist', 'key': 's o', 'action': 'sort --add ratio',
     'description': 'Sort torrents by upload/download ratio'},
    {'context': 'torrentlist', 'key': 's O', 'action': 'sort --add !ratio',
     'description': 'Sort torrents by upload/download ratio in reverse'},
    {'context': 'torrentlist', 'key': 's p', 'action': 'sort --add %downloaded',
     'description': 'Sort torrents by download progress'},
    {'context': 'torrentlist', 'key': 's P', 'action': 'sort --add !%downloaded',
     'description': 'Sort torrents by download progress in reverse'},
    {'context': 'torrentlist', 'key': 's r', 'action': 'sort --add rate',
     'description': 'Sort torrents by combined upload and download rate'},
    {'context': 'torrentlist', 'key': 's R', 'action': 'sort --add !rate',
     'description': 'Sort torrents by combined upload and download rate in reverse'},
    {'context': 'torrentlist', 'key': 's s', 'action': 'sort --add seeds',
     'description': 'Sort torrents by number of seeds'},
    {'context': 'torrentlist', 'key': 's S', 'action': 'sort --add !seeds',
     'description': 'Sort torrents by number of seeds in reverse'},
    {'context': 'torrentlist', 'key': 's t', 'action': 'sort --add tracker',
     'description': 'Sort torrents by first tracker domain'},
    {'context': 'torrentlist', 'key': 's T', 'action': 'sort --add !tracker',
     'description': 'Sort torrents by first tracker domain in reverse'},
    {'context': 'torrentlist', 'key': 's z', 'action': 'sort --add size',
     'description': 'Sort torrents by size of combined wanted files'},
    {'context': 'torrentlist', 'key': 's Z', 'action': 'sort --add !size',
     'description': 'Sort torrents by size of combined wanted files in reverse'},
    {'context': 'torrentlist', 'key': 's ,', 'action': 'sort --reset',
     'description': 'Reset to initial sort orders'},
    {'context': 'torrentlist', 'key': 's .', 'action': 'sort --none',
     'description': 'Remove all sort orders'},
    {'context': 'torrentlist', 'key': '/',   'action': ("interactive 'limit \"[]\"' --per-change "
                                                        "--on-cancel 'limit --clear' --ignore-errors"),
     'description': 'Reduce listed torrents by applying more filters'},

    # Torrent actions
    {'context': 'torrent', 'key': 't a',       'action': 'announce',
     'description': 'Announce torrent to its tracker(s)'},
    {'context': 'torrent', 'key': 't d',       'action': 'delete',
     'description': 'Remove torrent and keep any downloaded files'},
    {'context': 'torrent', 'key': 't D',       'action': 'delete --delete-files',
     'description': 'Remove torrent and all downloaded files'},
    {'context': 'torrent', 'key': 't m',       'action': 'setcommand move {location}/',
     'description': 'Move torrent'},
    {'context': 'torrent', 'key': 't n',       'action': 'setcommand rename id={id} {name}',
     'description': 'Rename torrent'},
    {'context': 'torrent', 'key': 't p',       'action': 'tab peerlist',
     'description': 'List selected or focused torrents\' peers in a new tab'},
    {'context': 'torrent', 'key': 't t',       'action': 'tab trackerlist',
     'description': 'List selected or focused torrents\' trackers in a new tab'},
    {'context': 'torrent', 'key': 't s',       'action': 'start --toggle',
     'description': 'Start or stop selected or focused torrents'},
    # Disabled until we have download queues implemented
    # {'context': 'torrent', 'key': 't S',       'action': 'start --toggle --force',
    #  'description': ''},
    {'context': 'torrent', 'key': 't v',       'action': 'verify',
     'description': 'Verify selected or focused torrents\' downloaded files'},
    {'context': 'torrent', 'key': 'enter',     'action': 'tab summary',
     'description': 'Show details about focused torrent in a new tab'},
    {'context': 'torrent', 'key': 'alt-enter', 'action': 'tab filelist',
     'description': 'List selected or focused torrents\' files in a new tab'},
    {'context': 'torrent', 'key': 'space',     'action': 'mark --toggle --focus-next',
     'description': 'Mark or unmark focused torrent'},
    {'context': 'torrent', 'key': 'alt-space', 'action': 'mark --toggle --all',
     'description': 'Mark or unmark all torrents'},

    # Peer list actions
    {'context': 'peerlist', 'key': 's c', 'action': 'sort --add country',
     'description': 'Sort peers by country'},
    {'context': 'peerlist', 'key': 's C', 'action': 'sort --add !country',
     'description': 'Sort peers by country in reverse'},
    {'context': 'peerlist', 'key': 's d', 'action': 'sort --add rate-down',
     'description': 'Sort peers by download rate'},
    {'context': 'peerlist', 'key': 's D', 'action': 'sort --add !rate-down',
     'description': 'Sort peers by download rate in reverse'},
    {'context': 'peerlist', 'key': 's e', 'action': 'sort --add eta',
     'description': 'Sort peers by estimated time of download completion'},
    {'context': 'peerlist', 'key': 's E', 'action': 'sort --add !eta',
     'description': 'Sort peers by estimated time of download completion in reverse'},
    {'context': 'peerlist', 'key': 's l', 'action': 'sort --add client',
     'description': 'Sort peers by client'},
    {'context': 'peerlist', 'key': 's L', 'action': 'sort --add !client',
     'description': 'Sort peers by client in reverse'},
    {'context': 'peerlist', 'key': 's p', 'action': 'sort --add %downloaded',
     'description': 'Sort peers by download progress'},
    {'context': 'peerlist', 'key': 's P', 'action': 'sort --add !%downloaded',
     'description': 'Sort peers by download progress in reverse'},
    {'context': 'peerlist', 'key': 's u', 'action': 'sort --add rate-up',
     'description': 'Sort peers by upload rate'},
    {'context': 'peerlist', 'key': 's U', 'action': 'sort --add !rate-up',
     'description': 'Sort peers by upload rate in reverse'},
    {'context': 'peerlist', 'key': 's s', 'action': 'sort --add rate-est',
     'description': 'Sort peers by estimated download rate'},
    {'context': 'peerlist', 'key': 's S', 'action': 'sort --add !rate-est',
     'description': 'Sort peers by estimated download rate in reverse'},
    {'context': 'peerlist', 'key': 's r', 'action': 'sort --add rate',
     'description': 'Sort peers by combined upload and download rate'},
    {'context': 'peerlist', 'key': 's R', 'action': 'sort --add !rate',
     'description': 'Sort peers by combined upload and download rate in reverse'},
    {'context': 'peerlist', 'key': 's t', 'action': 'sort --add torrent',
     'description': 'Sort peers by torrent name'},
    {'context': 'peerlist', 'key': 's T', 'action': 'sort --add !torrent',
     'description': 'Sort peers by torrent name in reverse'},
    {'context': 'peerlist', 'key': 's ,', 'action': 'sort --reset',
     'description': 'Reset to initial sort orders'},
    {'context': 'peerlist', 'key': 's .', 'action': 'sort --none',
     'description': 'Remove all sort orders'},
    {'context': 'peerlist', 'key': '/',   'action': ("interactive 'limit \"[]\"' --per-change "
                                                     "--on-cancel 'limit --clear' --ignore-errors"),
     'description': 'Reduce listed peers by applying more filters'},

    # File list actions
    {'context': 'filelist', 'key': '/', 'action': ("interactive 'limit \"[]\"' --per-change "
                                                   "--on-cancel 'limit --clear' --ignore-errors"),
     'description': 'Reduce listed files by applying more filters'},

    # File actions
    {'context': 'file', 'key': 'f n',       'action': 'setcommand rename {name}',
     'description': 'Rename file or directory'},
    {'context': 'file', 'key': 'f +',       'action': 'priority high',
     'description': 'Set selected or focused file\'s download priority to "high"'},
    {'context': 'file', 'key': 'f =',       'action': 'priority normal',
     'description': 'Set selected or focused file\'s download priority to "normal"'},
    {'context': 'file', 'key': 'f -',       'action': 'priority low',
     'description': 'Set selected or focused file\'s download priority to "low"'},
    {'context': 'file', 'key': 'f 0',       'action': 'priority off',
     'description': 'Don\'t download selected or focused file(s)'},
    {'context': 'file', 'key': 'space',     'action': 'mark --toggle --focus-next',
     'description': 'Mark or unmark focused file or directory'},
    {'context': 'file', 'key': 'alt-space', 'action': 'mark --toggle --all',
     'description': 'Mark or unmark all files'},

    # Tracker list actions
    {'context': 'trackerlist', 'key': 's n a', 'action': 'sort --add next-announce',
     'description': 'Sort trackers by next announce time'},
    {'context': 'trackerlist', 'key': 's n A', 'action': 'sort --add !next-announce',
     'description': 'Sort trackers by next announce time in reverse'},
    {'context': 'trackerlist', 'key': 's l a', 'action': 'sort --add last-announce',
     'description': 'Sort trackers by last announce time'},
    {'context': 'trackerlist', 'key': 's l A', 'action': 'sort --add !last-announce',
     'description': 'Sort trackers by last announce time in reverse'},
    {'context': 'trackerlist', 'key': 's d',   'action': 'sort --add downloads',
     'description': 'Sort trackers by number of downloads'},
    {'context': 'trackerlist', 'key': 's D',   'action': 'sort --add !downloads',
     'description': 'Sort trackers by number of downloads in reverse'},
    {'context': 'trackerlist', 'key': 's c',   'action': 'sort --add leeches',
     'description': 'Sort trackers by number of downloading peers'},
    {'context': 'trackerlist', 'key': 's C',   'action': 'sort --add !leeches',
     'description': 'Sort trackers by number of downloading peers in reverse'},
    {'context': 'trackerlist', 'key': 's s',   'action': 'sort --add seeds',
     'description': 'Sort trackers by number of seeding peers'},
    {'context': 'trackerlist', 'key': 's S',   'action': 'sort --add !seeds',
     'description': 'Sort trackers by number of seeding peers in reverse'},
    {'context': 'trackerlist', 'key': 's o',   'action': 'sort --add domain',
     'description': 'Sort trackers by tracker\'s domain'},
    {'context': 'trackerlist', 'key': 's O',   'action': 'sort --add !domain',
     'description': 'Sort trackers by tracker\'s domain in reverse'},
    {'context': 'trackerlist', 'key': 's t',   'action': 'sort --add torrent',
     'description': 'Sort trackers by torrent name'},
    {'context': 'trackerlist', 'key': 's T',   'action': 'sort --add !torrent',
     'description': 'Sort trackers by torrent name in reverse'},
    {'context': 'trackerlist', 'key': 's e',   'action': 'sort --add error',
     'description': 'Sort trackers by error message'},
    {'context': 'trackerlist', 'key': 's E',   'action': 'sort --add !error',
     'description': 'Sort trackers by error message in reverse'},
    {'context': 'trackerlist', 'key': 's a',   'action': 'sort --add status',
     'description': 'Sort trackers by current status'},
    {'context': 'trackerlist', 'key': 's A',   'action': 'sort --add !status',
     'description': 'Sort trackers by current status in reverse'},
    {'context': 'trackerlist', 'key': 's ,',   'action': 'sort --reset',
     'description': 'Reset to initial sort orders'},
    {'context': 'trackerlist', 'key': 's .',   'action': 'sort --none',
     'description': 'Remove all sort orders'},
    {'context': 'trackerlist', 'key': '/',     'action': ("interactive 'limit \"[]\"' --per-change "
                                                          "--on-cancel 'limit --clear' --ignore-errors"),
     'description': 'Reduce listed trackers by applying more filters'},

    # Tracker actions
    {'context': 'torrent', 'key': 'enter', 'action': 'tab summary',
     'description': 'Show details about torrent of focused tracker in new tab'},
    {'context': 'torrent', 'key': 'alt-enter', 'action': 'tab filelist',
     'description': 'List files of torrent of focused tracker in a new tab'},

    # Setting list actions
    {'context': 'settinglist', 'key': 's n', 'action': 'sort --add name',
     'description': 'Sort settings by name'},
    {'context': 'settinglist', 'key': 's N', 'action': 'sort --add !name',
     'description': 'Sort settings by name in reverse'},
    {'context': 'settinglist', 'key': 's v', 'action': 'sort --add value',
     'description': 'Sort settings by value'},
    {'context': 'settinglist', 'key': 's V', 'action': 'sort --add !value',
     'description': 'Sort settings by value in reverse'},
    {'context': 'settinglist', 'key': 's d', 'action': 'sort --add default',
     'description': 'Sort settings by default value'},
    {'context': 'settinglist', 'key': 's D', 'action': 'sort --add !default',
     'description': 'Sort settings by default value in reverse'},
    {'context': 'settinglist', 'key': 's c', 'action': 'sort --add description',
     'description': 'Sort settings by description'},
    {'context': 'settinglist', 'key': 's C', 'action': 'sort --add !description',
     'description': 'Sort settings by description in reverse'},
    {'context': 'settinglist', 'key': 's ,', 'action': 'sort --reset',
     'description': 'Reset to initial sort orders'},
    {'context': 'settinglist', 'key': 's .', 'action': 'sort --none',
     'description': 'Remove all sort orders'},
    {'context': 'settinglist', 'key': '/',   'action': ("interactive 'limit \"[]\"' --per-change "
                                                        "--on-cancel 'limit --clear' --ignore-errors"),
     'description': 'Reduce listed settings by applying more filters'},

    # Setting actions
    {'context': 'setting', 'key': 'ctrl-r', 'action': 'reset',
     'description': 'Reset setting to its default value'},

    # Help actions
    {'context': 'helptext', 'key': '/',      'action': ("interactive 'find \"[]\"' --per-change "
                                                        "--on-cancel 'find --clear' --ignore-errors"),
     'description': 'Search for string'},
    {'context': 'helptext', 'key': 'n',      'action': 'find --next',
     'description': 'Find next occurence of search string'},
    {'context': 'helptext', 'key': 'ctrl-n', 'action': 'find --next',
     'description': 'Find next occurence of search string'},
    {'context': 'helptext', 'key': 'N',      'action': 'find --previous',
     'description': 'Find previous occurence of search string'},
    {'context': 'helptext', 'key': 'ctrl-p', 'action': 'find --previous',
     'description': 'Find previous occurence of search string'},
)
