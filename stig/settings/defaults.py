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

DEFAULT_RCFILE       = os.path.join(XDG_CONFIG_HOME, __appname__, 'rc')
DEFAULT_HISTORY_FILE = os.path.join(XDG_DATA_HOME, __appname__, 'history')
DEFAULT_GEOIP_DIR    = os.path.join(XDG_CACHE_HOME, __appname__)
DEFAULT_THEME_FILE   = os.path.join(os.path.dirname(__file__), 'default.theme')


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
                 default=('ip', 'client', 'country', '%downloaded', 'rate-down',
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
                 Int.partial(min=0),
                 default=10,
                 description=('Maximum number of torrents to remove without extra confirmation'))

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
    localcfg.add('tui.cli.history-file',
                 Path.partial(),
                 default=DEFAULT_HISTORY_FILE,
                 description='Path to TUI command line history file')
    localcfg.add('tui.cli.history-size',
                 Int.partial(min=0),
                 default=10000,
                 description='Maximum number of lines in history file')
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
    # Use some vi and emacs keybindings
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
    {'context': 'main', 'key': 'q',     'action': 'quit'},
    {'context': 'main', 'key': ':',     'action': 'tui show cli'},
    {'context': 'main', 'key': 'alt-s', 'action': 'tab set'},

    # Help
    {'context': 'main', 'key': 'F1+c', 'action': 'tab help commands'},
    {'context': 'main', 'key': 'F1+s', 'action': 'tab help settings'},
    {'context': 'main', 'key': 'F1+k', 'action': 'tab help keymap'},
    {'context': 'main', 'key': 'F1+f', 'action': 'tab help filtering'},
    {'context': 'main', 'key': 'F1+r', 'action': 'tab help rcfile'},
    {'context': 'main', 'key': '?',    'action': '<F1>'},

    # Hide/Show TUI elements
    {'context': 'main', 'key': 'alt-L', 'action': 'tui toggle log'},
    {'context': 'main', 'key': 'alt-M', 'action': 'tui toggle main'},
    {'context': 'main', 'key': 'alt-T', 'action': 'tui toggle topbar'},
    {'context': 'main', 'key': 'alt-B', 'action': 'tui toggle bottombar'},

    # Log messages
    {'context': 'main', 'key': 'ctrl-l',   'action': 'tui toggle log'},
    {'context': 'main', 'key': 'alt-l',    'action': 'log clear'},
    {'context': 'main', 'key': 'alt-pgup', 'action': 'log scroll page up'},
    {'context': 'main', 'key': 'alt-pgdn', 'action': 'log scroll page down'},
    {'context': 'main', 'key': 'alt-home', 'action': 'log scroll top'},
    {'context': 'main', 'key': 'alt-end',  'action': 'log scroll bottom'},

    # Global bandwidth limits
    {'context': 'main', 'key': 'shift-up',    'action': 'rate --quiet dn -- +=100kB global'},
    {'context': 'main', 'key': 'shift-down',  'action': 'rate --quiet dn -- -=100kB global'},
    {'context': 'main', 'key': 'shift-right', 'action': 'rate --quiet up -- +=100kB global'},
    {'context': 'main', 'key': 'shift-left',  'action': 'rate --quiet up -- -=100kB global'},

    # Tab management
    {'context': 'tabs', 'key': 'n',     'action': 'tab'},
    {'context': 'tabs', 'key': 'd',     'action': 'tab --close'},
    {'context': 'tabs', 'key': 'D',     'action': 'tab --close --focus left'},
    {'context': 'tabs', 'key': 'alt-1', 'action': 'tab --focus 1'},
    {'context': 'tabs', 'key': 'alt-2', 'action': 'tab --focus 2'},
    {'context': 'tabs', 'key': 'alt-3', 'action': 'tab --focus 3'},
    {'context': 'tabs', 'key': 'alt-4', 'action': 'tab --focus 4'},
    {'context': 'tabs', 'key': 'alt-5', 'action': 'tab --focus 5'},
    {'context': 'tabs', 'key': 'alt-6', 'action': 'tab --focus 6'},
    {'context': 'tabs', 'key': 'alt-7', 'action': 'tab --focus 7'},
    {'context': 'tabs', 'key': 'alt-8', 'action': 'tab --focus 8'},
    {'context': 'tabs', 'key': 'alt-9', 'action': 'tab --focus 9'},
    {'context': 'tabs', 'key': 'alt-0', 'action': 'tab --focus 10'},

    # List torrents with different filters
    {'context': 'tabs', 'key': 'f a', 'action': 'tab ls active'},
    {'context': 'tabs', 'key': 'f A', 'action': 'tab ls !active'},
    {'context': 'tabs', 'key': 'f i', 'action': 'tab ls isolated --columns name,tracker,error'},
    {'context': 'tabs', 'key': 'f p', 'action': 'tab ls paused'},
    {'context': 'tabs', 'key': 'f P', 'action': 'tab ls !paused'},
    {'context': 'tabs', 'key': 'f c', 'action': 'tab ls complete'},
    {'context': 'tabs', 'key': 'f C', 'action': 'tab ls !complete'},
    {'context': 'tabs', 'key': 'f u', 'action': 'tab ls uploading'},
    {'context': 'tabs', 'key': 'f d', 'action': 'tab ls downloading'},
    {'context': 'tabs', 'key': 'f s', 'action': 'tab ls seeding'},
    {'context': 'tabs', 'key': 'f l', 'action': 'tab ls leeching'},
    {'context': 'tabs', 'key': 'f .', 'action': 'tab ls'},

    # Torrent list actions
    {'context': 'torrentlist', 'key': 's d',       'action': 'sort --add dir'},
    {'context': 'torrentlist', 'key': 's D',       'action': 'sort --add !dir'},
    {'context': 'torrentlist', 'key': 's e',       'action': 'sort --add eta'},
    {'context': 'torrentlist', 'key': 's E',       'action': 'sort --add !eta'},
    {'context': 'torrentlist', 'key': 's n',       'action': 'sort --add name'},
    {'context': 'torrentlist', 'key': 's N',       'action': 'sort --add !name'},
    {'context': 'torrentlist', 'key': 's o',       'action': 'sort --add ratio'},
    {'context': 'torrentlist', 'key': 's O',       'action': 'sort --add !ratio'},
    {'context': 'torrentlist', 'key': 's p',       'action': 'sort --add %downloaded'},
    {'context': 'torrentlist', 'key': 's P',       'action': 'sort --add !%downloaded'},
    {'context': 'torrentlist', 'key': 's r',       'action': 'sort --add rate'},
    {'context': 'torrentlist', 'key': 's R',       'action': 'sort --add !rate'},
    {'context': 'torrentlist', 'key': 's s',       'action': 'sort --add seeds'},
    {'context': 'torrentlist', 'key': 's S',       'action': 'sort --add !seeds'},
    {'context': 'torrentlist', 'key': 's t',       'action': 'sort --add tracker'},
    {'context': 'torrentlist', 'key': 's T',       'action': 'sort --add !tracker'},
    {'context': 'torrentlist', 'key': 's z',       'action': 'sort --add size'},
    {'context': 'torrentlist', 'key': 's Z',       'action': 'sort --add !size'},
    {'context': 'torrentlist', 'key': 's ,',       'action': 'sort --reset'},
    {'context': 'torrentlist', 'key': 's .',       'action': 'sort --none'},

    # Torrent actions
    {'context': 'torrent', 'key': 't a',       'action': 'announce'},
    {'context': 'torrent', 'key': 't d',       'action': 'delete'},
    {'context': 'torrent', 'key': 't D',       'action': 'delete --delete-files'},
    {'context': 'torrent', 'key': 't p',       'action': 'tab peerlist'},
    {'context': 'torrent', 'key': 't t',       'action': 'tab trackerlist'},
    {'context': 'torrent', 'key': 't s',       'action': 'start --toggle'},
    {'context': 'torrent', 'key': 't S',       'action': 'start --toggle --force'},
    {'context': 'torrent', 'key': 't v',       'action': 'verify'},
    {'context': 'torrent', 'key': 'enter',     'action': 'tab summary'},
    {'context': 'torrent', 'key': 'alt-enter', 'action': 'tab filelist'},
    {'context': 'torrent', 'key': 'space',     'action': 'mark --toggle --focus-next'},
    {'context': 'torrent', 'key': 'alt-space', 'action': 'mark --toggle --all'},

    # Peer list actions
    {'context': 'peerlist', 'key': 's c',       'action': 'sort --add country'},
    {'context': 'peerlist', 'key': 's C',       'action': 'sort --add !country'},
    {'context': 'peerlist', 'key': 's d',       'action': 'sort --add rate-down'},
    {'context': 'peerlist', 'key': 's D',       'action': 'sort --add !rate-down'},
    {'context': 'peerlist', 'key': 's e',       'action': 'sort --add eta'},
    {'context': 'peerlist', 'key': 's E',       'action': 'sort --add !eta'},
    {'context': 'peerlist', 'key': 's l',       'action': 'sort --add client'},
    {'context': 'peerlist', 'key': 's L',       'action': 'sort --add !client'},
    {'context': 'peerlist', 'key': 's p',       'action': 'sort --add %downloaded'},
    {'context': 'peerlist', 'key': 's P',       'action': 'sort --add !%downloaded'},
    {'context': 'peerlist', 'key': 's u',       'action': 'sort --add rate-up'},
    {'context': 'peerlist', 'key': 's U',       'action': 'sort --add !rate-up'},
    {'context': 'peerlist', 'key': 's s',       'action': 'sort --add rate-est'},
    {'context': 'peerlist', 'key': 's S',       'action': 'sort --add !rate-est'},
    {'context': 'peerlist', 'key': 's r',       'action': 'sort --add rate'},
    {'context': 'peerlist', 'key': 's R',       'action': 'sort --add !rate'},
    {'context': 'peerlist', 'key': 's t',       'action': 'sort --add torrent'},
    {'context': 'peerlist', 'key': 's T',       'action': 'sort --add !torrent'},
    {'context': 'peerlist', 'key': 's ,',       'action': 'sort --reset'},
    {'context': 'peerlist', 'key': 's .',       'action': 'sort --none'},

    # File actions
    {'context': 'file', 'key': '+',         'action': 'priority high'},
    {'context': 'file', 'key': '=',         'action': 'priority normal'},
    {'context': 'file', 'key': '-',         'action': 'priority low'},
    {'context': 'file', 'key': '0',         'action': 'priority off'},
    {'context': 'file', 'key': 'space',     'action': 'mark --toggle --focus-next'},
    {'context': 'file', 'key': 'alt-space', 'action': 'mark --toggle --all'},

    # Tracker list actions
    {'context': 'trackerlist', 'key': 's n a',   'action': 'sort --add next-announce'},
    {'context': 'trackerlist', 'key': 's n A',   'action': 'sort --add !next-announce'},
    {'context': 'trackerlist', 'key': 's l a',   'action': 'sort --add last-announce'},
    {'context': 'trackerlist', 'key': 's l A',   'action': 'sort --add !last-announce'},

    {'context': 'trackerlist', 'key': 's n s',   'action': 'sort --add next-scrape'},
    {'context': 'trackerlist', 'key': 's n S',   'action': 'sort --add !next-scrape'},
    {'context': 'trackerlist', 'key': 's l s',   'action': 'sort --add last-scrape'},
    {'context': 'trackerlist', 'key': 's l S',   'action': 'sort --add !last-scrape'},

    {'context': 'trackerlist', 'key': 's D',     'action': 'sort --add !downloads'},
    {'context': 'trackerlist', 'key': 's d',     'action': 'sort --add downloads'},
    {'context': 'trackerlist', 'key': 's D',     'action': 'sort --add !downloads'},
    {'context': 'trackerlist', 'key': 's c',     'action': 'sort --add leeches'},
    {'context': 'trackerlist', 'key': 's C',     'action': 'sort --add !leeches'},
    {'context': 'trackerlist', 'key': 's s',     'action': 'sort --add seeds'},
    {'context': 'trackerlist', 'key': 's S',     'action': 'sort --add !seeds'},

    {'context': 'trackerlist', 'key': 's e',     'action': 'sort --add error'},
    {'context': 'trackerlist', 'key': 's E',     'action': 'sort --add !error'},
    {'context': 'trackerlist', 'key': 's t',     'action': 'sort --add status'},
    {'context': 'trackerlist', 'key': 's T',     'action': 'sort --add !status'},

    {'context': 'trackerlist', 'key': 's ,',     'action': 'sort --reset'},
    {'context': 'trackerlist', 'key': 's .',     'action': 'sort --none'},

    # Tracker actions
    {'context': 'tracker', 'key': 'enter',       'action': 'tab summary'},
    {'context': 'tracker', 'key': 'alt-enter',   'action': 'tab filelist'},

    # Setting list actions
    {'context': 'settinglist', 'key': 's n', 'action': 'sort --add name'},
    {'context': 'settinglist', 'key': 's N', 'action': 'sort --add !name'},
    {'context': 'settinglist', 'key': 's v', 'action': 'sort --add value'},
    {'context': 'settinglist', 'key': 's V', 'action': 'sort --add !value'},
    {'context': 'settinglist', 'key': 's d', 'action': 'sort --add default'},
    {'context': 'settinglist', 'key': 's D', 'action': 'sort --add !default'},
    {'context': 'settinglist', 'key': 's c', 'action': 'sort --add description'},
    {'context': 'settinglist', 'key': 's C', 'action': 'sort --add !description'},
    {'context': 'settinglist', 'key': 's ,', 'action': 'sort --reset'},
    {'context': 'settinglist', 'key': 's .', 'action': 'sort --none'},

    # Setting actions
    {'context': 'setting', 'key': 'ctrl-r', 'action': 'reset'},
)
