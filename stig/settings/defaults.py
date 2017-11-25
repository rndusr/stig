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

from .. import APPNAME
from ..views import (torrentlist, filelist, peerlist, trackerlist)
from ..client.sorters.tsorter import TorrentSorter
from ..client.sorters.psorter import TorrentPeerSorter
from ..client.sorters.trksorter import TorrentTrackerSorter

DEFAULT_RCFILE        = os.path.join(XDG_CONFIG_HOME, APPNAME, 'rc')
DEFAULT_HISTORY_FILE  = os.path.join(XDG_CACHE_HOME, APPNAME, 'history')
DEFAULT_THEME_FILE    = os.path.join(os.path.dirname(__file__), 'default.theme')

DEFAULT_TORRENT_SORT = ('name',)
DEFAULT_PEER_SORT    = ('torrent',)
DEFAULT_TRACKER_SORT = ('domain',)

DEFAULT_TORRENT_COLUMNS = ('marked', 'size', 'downloaded', 'uploaded', 'ratio',
                           'seeds', 'connections', 'status', 'eta', 'progress',
                           'rate-down', 'rate-up', 'name')
DEFAULT_FILE_COLUMNS    = ('marked', 'priority', 'progress', 'downloaded', 'size', 'name')
DEFAULT_TRACKER_COLUMNS = ('tier', 'domain', 'state', 'error',
                           'leeches', 'seeds', 'downloads',
                           'last-announce', 'next-announce')

from ..client.geoip import GEOIP_AVAILABLE
if GEOIP_AVAILABLE:
    DEFAULT_PEER_COLUMNS = ('client', 'country', 'ip', 'progress', 'rate-down',
                            'rate-up', 'rate-est', 'eta')
else:
    DEFAULT_PEER_COLUMNS = ('client', 'ip', 'progress', 'rate-down', 'rate-up',
                            'rate-est', 'eta', )


def init_defaults(cfg):
    from .types import (StringValue, IntegerValue, NumberValue, BooleanValue,
                        PathValue, ListValue, SetValue, OptionValue)

    class SortOrderValue(SetValue):
        """SetValue that correctly validates inverted sort orders (e.g. '!name')"""
        def __init__(self, sortercls, *args, **kwargs):
            super().__init__(*args, options=tuple(sortercls.SORTSPECS), **kwargs)

        def validate(self, names):
            super().validate(name.strip('!.') for name in names)

    cfg.load(
        StringValue('srv.url', default='localhost:9091',
                    description='URL of the Transmission RPC interface ([USER:PASSWORD@]HOST[:PORT])'),
        NumberValue('srv.timeout', default=10, min=0,
                    description=('Number of seconds before connecting '
                                 'to Transmission daemon fails')),

        SetValue('columns.torrents', default=DEFAULT_TORRENT_COLUMNS,
                 options=torrentlist.COLUMNS,
                 aliases=torrentlist.ALIASES,
                 description='List of columns in new torrent lists'),
        SetValue('columns.peers', default=DEFAULT_PEER_COLUMNS,
                 options=peerlist.COLUMNS,
                 aliases=peerlist.ALIASES,
                 description='List of columns in new peer lists'),
        SetValue('columns.files', default=DEFAULT_FILE_COLUMNS,
                 options=filelist.COLUMNS,
                 aliases=filelist.ALIASES,
                 description='List of columns in new torrent file lists'),
        SetValue('columns.trackers', default=DEFAULT_TRACKER_COLUMNS,
                 options=trackerlist.COLUMNS,
                 aliases=trackerlist.ALIASES,
                 description='List of columns in new tracker lists'),

        SortOrderValue(TorrentSorter, 'sort.torrents', default=DEFAULT_TORRENT_SORT,
                       description='List of torrent list sort orders'),
        SortOrderValue(TorrentPeerSorter, 'sort.peers', default=DEFAULT_PEER_SORT,
                       description='List of peer list sort orders'),
        SortOrderValue(TorrentTrackerSorter, 'sort.trackers', default=DEFAULT_TRACKER_SORT,
                       description='List of tracker list sort orders'),

        PathValue('tui.theme', default=DEFAULT_THEME_FILE,
                  description='Path to theme file'),
        IntegerValue('tui.log.height', default=10, min=1,
                     description='Maximum height of the log section'),
        NumberValue('tui.log.autohide', default=10, min=0,
                    description=('If the log is hidden, show it for this many seconds '
                                 'for new log entries before hiding it again')),
        PathValue('tui.cli.history-file', default=DEFAULT_HISTORY_FILE,
                  description='Path to TUI command line history file'),
        PathValue('tui.cli.history-size', default=10000,
                  description='Maximum number of lines in history file'),
        NumberValue('tui.poll', default=5, min=0.1,
                    description='Interval in seconds between TUI updates'),

        OptionValue('unit.bandwidth', default='byte', options=('bit', 'byte'),
                    description="Unit for bandwidth rates ('bit' or 'byte')"),
        OptionValue('unitprefix.bandwidth', default='metric', options=('metric', 'binary'),
                    description=("Unit prefix for bandwidth rates ('metric' or 'binary')")),

        OptionValue('unit.size', default='byte', options=('bit', 'byte'),
                    description="Unit for sizes ('bit' or 'byte')"),
        OptionValue('unitprefix.size', default='binary', options=('metric', 'binary'),
                    description=("Unit prefix for sizes ('metric' or 'binary')")),

        StringValue('tui.marked.on', default='✔', minlen=1, maxlen=1,
                    description=('Character displayed in "marked" column for marked '
                                 'list items (see "mark" command)')),
        StringValue('tui.marked.off', default=' ', minlen=1, maxlen=1,
                    description=('Character displayed in "marked" column for unmarked '
                                 'list items (see "mark" command)')),

        IntegerValue('remove.max-hits', default=10, min=0,
                     description=('Maximum number of torrents to remove without '
                                  'getting extra user confirmation')),
    )



def init_server_defaults(cfg, settingsapi):
    from .types_srv import (BooleanSrvValue, IntegerSrvValue, OptionSrvValue,
                            PathSrvValue, PathIncompleteSrvValue,
                            RateLimitSrvValue, PortSrvValue)

    def mk(cls, name, setting, description, **kwargs):
        getter = lambda: settingsapi[setting]
        setter = getattr(settingsapi, 'set_'+setting)
        return cls(name, getter=getter, setter=setter, description=description, **kwargs)

    cfg.load(
        mk(BooleanSrvValue, 'srv.utp', 'utp',
           'Whether to use Micro Transport Protocol to mitigate latency issues'),
        mk(BooleanSrvValue, 'srv.dht', 'dht',
           'Whether to use Distributed Hash Tables to discover peers for public torrents'),
        mk(BooleanSrvValue, 'srv.lpd', 'lpd',
           'Whether to use Local Peer Discovery to discover peers for public torrents'),
        mk(BooleanSrvValue, 'srv.pex', 'pex',
           'Whether to use Peer Exchange to discover peers for public torrents'),

        mk(PortSrvValue, 'srv.port', 'port',
           'Port used to communicate with peers or "random" to use a random port',
           min=1, max=65535),
        mk(BooleanSrvValue, 'srv.port-forwarding', 'port_forwarding',
           'Whether to instruct your router to forward the peer port via UPnP or NAT-PMP'),

        mk(OptionSrvValue, 'srv.encryption', 'encryption',
           'Protocol encryption policy; "required", "preferred" or "tolerated"',
           options=('required', 'preferred', 'tolerated')),

        mk(IntegerSrvValue, 'srv.limit.peers.global', 'peer_limit_global',
           'Maximum number of connections for all torrents combined'),
        mk(IntegerSrvValue, 'srv.limit.peers.torrent', 'peer_limit_torrent',
           'Maximum number of connections for a single torrent'),

        mk(RateLimitSrvValue, 'srv.limit.rate.up', 'rate_limit_up',
           'Combined upload rate limit'),
        mk(RateLimitSrvValue, 'srv.limit.rate.down', 'rate_limit_down',
           'Combined download rate limit'),

        mk(BooleanSrvValue, 'srv.part-files', 'part_files',
           'Whether to append ".part" to incomplete file names'),
        mk(PathSrvValue, 'srv.path.complete', 'path_complete',
           'Where to put torrent files'),
        mk(PathIncompleteSrvValue, 'srv.path.incomplete', 'path_incomplete',
           'Where to put incomplete torrent files'),

        mk(BooleanSrvValue, 'srv.autostart-torrents', 'autostart_torrents',
           'Automatically start torrents when they are added'),
    )


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
    {'context': 'main', 'key': 'q', 'action': 'quit'},
    {'context': 'main', 'key': ':', 'action': 'tui show cli'},

    # Help
    {'context': 'main', 'key': 'F1+c', 'action': 'tab help commands'},
    {'context': 'main', 'key': 'F1+s', 'action': 'tab help settings'},
    {'context': 'main', 'key': 'F1+k', 'action': 'tab help keymap'},
    {'context': 'main', 'key': 'F1+f', 'action': 'tab help filtering'},
    {'context': 'main', 'key': 'F1+r', 'action': 'tab help rcfile'},
    {'context': 'main', 'key': '?',    'action': '<F1>'},

    # Hide/Show TUI elements
    {'context': 'main', 'key': 'meta-L', 'action': 'tui toggle log'},
    {'context': 'main', 'key': 'meta-M', 'action': 'tui toggle main'},
    {'context': 'main', 'key': 'meta-T', 'action': 'tui toggle topbar'},
    {'context': 'main', 'key': 'meta-B', 'action': 'tui toggle bottombar'},

    # Log messages
    {'context': 'main', 'key': 'ctrl-l',   'action': 'tui toggle log'},
    {'context': 'main', 'key': 'alt-l',    'action': 'log clear'},
    {'context': 'main', 'key': 'alt-pgup', 'action': 'log scroll page up'},
    {'context': 'main', 'key': 'alt-pgdn', 'action': 'log scroll page down'},
    {'context': 'main', 'key': 'alt-home', 'action': 'log scroll top'},
    {'context': 'main', 'key': 'alt-end',  'action': 'log scroll bottom'},

    # Bandwidth limits
    {'context': 'main', 'key': 'shift-up',    'action': 'set srv.limit.rate.down +=100kB'},
    {'context': 'main', 'key': 'shift-down',  'action': 'set srv.limit.rate.down -=100kB'},
    {'context': 'main', 'key': 'shift-right', 'action': 'set srv.limit.rate.up +=100kB'},
    {'context': 'main', 'key': 'shift-left',  'action': 'set srv.limit.rate.up -=100kB'},

    # Tab management
    {'context': 'tabs', 'key': 'n',      'action': 'tab'},
    {'context': 'tabs', 'key': 'd',      'action': 'tab --close'},
    {'context': 'tabs', 'key': 'D',      'action': 'tab --close --focus left'},
    {'context': 'tabs', 'key': 'meta-1', 'action': 'tab --focus 1'},
    {'context': 'tabs', 'key': 'meta-2', 'action': 'tab --focus 2'},
    {'context': 'tabs', 'key': 'meta-3', 'action': 'tab --focus 3'},
    {'context': 'tabs', 'key': 'meta-4', 'action': 'tab --focus 4'},
    {'context': 'tabs', 'key': 'meta-5', 'action': 'tab --focus 5'},
    {'context': 'tabs', 'key': 'meta-6', 'action': 'tab --focus 6'},
    {'context': 'tabs', 'key': 'meta-7', 'action': 'tab --focus 7'},
    {'context': 'tabs', 'key': 'meta-8', 'action': 'tab --focus 8'},
    {'context': 'tabs', 'key': 'meta-9', 'action': 'tab --focus 9'},
    {'context': 'tabs', 'key': 'meta-0', 'action': 'tab --focus 10'},

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
    {'context': 'torrentlist', 'key': 's p',       'action': 'sort --add progress'},
    {'context': 'torrentlist', 'key': 's P',       'action': 'sort --add !progress'},
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
    {'context': 'peerlist', 'key': 's i',       'action': 'sort --add ip'},
    {'context': 'peerlist', 'key': 's I',       'action': 'sort --add !ip'},
    {'context': 'peerlist', 'key': 's l',       'action': 'sort --add client'},
    {'context': 'peerlist', 'key': 's L',       'action': 'sort --add !client'},
    {'context': 'peerlist', 'key': 's p',       'action': 'sort --add progress'},
    {'context': 'peerlist', 'key': 's P',       'action': 'sort --add !progress'},
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
    {'context': 'trackerlist', 'key': 's t',     'action': 'sort --add state'},
    {'context': 'trackerlist', 'key': 's T',     'action': 'sort --add !state'},

    {'context': 'trackerlist', 'key': 's ,',     'action': 'sort --reset'},
    {'context': 'trackerlist', 'key': 's .',     'action': 'sort --none'},

    # Tracker actions
    {'context': 'tracker', 'key': 'enter',       'action': 'tab summary'},
    {'context': 'tracker', 'key': 'alt-enter',   'action': 'tab filelist'},
)
