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
from appdirs import (user_cache_dir, user_config_dir)

from .. import APPNAME
from ..views.tlist import COLUMNS as TCOLUMNS
from ..views.flist import COLUMNS as FCOLUMNS
from ..views.plist import COLUMNS as PCOLUMNS
from ..client.sorters.tsorter import TorrentSorter
from ..client.sorters.psorter import TorrentPeerSorter

DEFAULT_RCFILE        = user_config_dir(APPNAME) + '/rc'
DEFAULT_HISTORY_FILE  = user_cache_dir(APPNAME)+'/history'
DEFAULT_THEME_FILE    = os.path.join(os.path.dirname(__file__), 'default.theme')

DEFAULT_TLIST_SORT    = ('name',)
DEFAULT_PLIST_SORT    = ('torrent',)
DEFAULT_TLIST_COLUMNS = ('marked', 'size', 'downloaded', 'uploaded', 'ratio',
                         'seeds', 'connections', 'status', 'eta', 'progress',
                         'rate-down', 'rate-up', 'name')
DEFAULT_FLIST_COLUMNS = ('marked', 'priority', 'progress', 'downloaded', 'size', 'name')

from ..client.geoip import GEOIP_AVAILABLE
if GEOIP_AVAILABLE:
    DEFAULT_PLIST_COLUMNS = ('progress', 'rate-down', 'rate-up', 'rate-est',
                             'eta', 'ip', 'country', 'client')
else:
    DEFAULT_PLIST_COLUMNS = ('progress', 'rate-down', 'rate-up', 'rate-est',
                             'eta', 'ip', 'client')


from .settings import (StringValue, IntegerValue, NumberValue, BooleanValue,
                       PathValue, ListValue, SetValue, OptionValue)

class SortOrderValue(SetValue):
    """SetValue that correctly validates inverted sort orders (e.g. '!name')"""
    def __init__(self, sortercls, *args, options=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.options = tuple(sortercls.SORTSPECS)

    def validate(self, names):
        super().validate(name.strip('!.') for name in names)


def init_defaults(cfg):
    cfg.load(
        StringValue('srv.url', default='localhost:9091',
                    description='URL of the Transmission RPC interface ([USER:PASSWORD@]HOST[:PORT])'),
        NumberValue('srv.timeout', default=10, min=0,
                    description=('Number of seconds before connecting '
                                 'to Transmission daemon fails')),

        SetValue('columns.torrents', default=DEFAULT_TLIST_COLUMNS,
                 options=tuple(TCOLUMNS),
                 description='List of columns in new torrent lists'),
        SetValue('columns.peers', default=DEFAULT_PLIST_COLUMNS,
                 options=tuple(PCOLUMNS),
                 description='List of columns in new peer lists'),
        SetValue('columns.files', default=DEFAULT_FLIST_COLUMNS,
                 options=tuple(FCOLUMNS),
                 description='List of columns in new torrent file lists'),

        SortOrderValue(TorrentSorter, 'sort.torrents', default=DEFAULT_TLIST_SORT,
                       description='List of torrent list sort orders'),
        SortOrderValue(TorrentPeerSorter, 'sort.peers', default=DEFAULT_PLIST_SORT,
                       description='List of peer list sort orders'),

        PathValue('tui.theme', default=DEFAULT_THEME_FILE,
                  description='Path to theme file'),
        IntegerValue('tui.log.height', default=10, min=1,
                     description='Maximum height of the log section'),
        NumberValue('tui.log.autohide', default=10, min=0,
                    description=('If the log is hidden, show it for this many seconds '
                                 'for new log entries before hiding it again')),
        PathValue('tui.cli.history', default=DEFAULT_HISTORY_FILE,
                  description='Path to TUI command line history file'),
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
    )


from .settings_server import (RateLimitSrvValue, PathSrvValue, PathIncompleteSrvValue)

def init_server_defaults(cfg, settingsapi):
    cfg.load(
        RateLimitSrvValue('srv.limit.rate.up',
                          description='Combined upload rate limit',
                          getter=lambda: settingsapi['rate-limit-up'],
                          setter=settingsapi.set_rate_limit_up),
        RateLimitSrvValue('srv.limit.rate.down',
                          description='Combined download rate limit',
                          getter=lambda: settingsapi['rate-limit-down'],
                          setter=settingsapi.set_rate_limit_down),

        PathSrvValue('srv.path.complete',
                     description='Where to put torrent files',
                     getter=lambda: settingsapi['path-complete'],
                     setter=settingsapi.set_path_complete),

        PathIncompleteSrvValue('srv.path.incomplete',
                     description='Where to put incomplete torrent files',
                     getter=lambda: settingsapi['path-incomplete'],
                     setter=settingsapi.set_path_incomplete),
    )


DEFAULT_KEYMAP = (
    # Use some vi and emacs keybindings
    {'context': None, 'key': 'h', 'action': '<left>'},
    {'context': None, 'key': 'j', 'action': '<down>'},
    {'context': None, 'key': 'k', 'action': '<up>'},
    {'context': None, 'key': 'l', 'action': '<right>'},
    {'context': None, 'key': 'g', 'action': '<home>'},
    {'context': None, 'key': 'G', 'action': '<end>'},
    {'context': None, 'key': 'ctrl-n', 'action': '<down>'},
    {'context': None, 'key': 'ctrl-p', 'action': '<up>'},
    {'context': None, 'key': 'ctrl-f', 'action': '<right>'},
    {'context': None, 'key': 'ctrl-b', 'action': '<left>'},

    # Global TUI keys
    {'context': 'main', 'key': 'q', 'action': 'quit'},
    {'context': 'main', 'key': ':', 'action': 'tui show cli'},

    {'context': 'main', 'key': 'F1+c', 'action': 'tab help commands'},
    {'context': 'main', 'key': 'F1+s', 'action': 'tab help settings'},
    {'context': 'main', 'key': 'F1+k', 'action': 'tab help keymap'},
    {'context': 'main', 'key': 'F1+f', 'action': 'tab help filtering'},
    {'context': 'main', 'key': 'F1+r', 'action': 'tab help rcfile'},
    {'context': 'main', 'key': '?',    'action': '<F1>'},

    {'context': 'main', 'key': 'ctrl-l', 'action': 'clearlog'},
    {'context': 'main', 'key': 'meta-L', 'action': 'tui toggle log'},
    {'context': 'main', 'key': 'meta-M', 'action': 'tui toggle main'},
    {'context': 'main', 'key': 'meta-T', 'action': 'tui toggle topbar'},
    {'context': 'main', 'key': 'meta-B', 'action': 'tui toggle bottombar'},

    # Bandwidth limits
    {'context': 'main', 'key': 'shift-up',    'action': 'set srv.limit.rate.down +=100kB'},
    {'context': 'main', 'key': 'shift-down',  'action': 'set srv.limit.rate.down -=100kB'},
    {'context': 'main', 'key': 'shift-right', 'action': 'set srv.limit.rate.up +=100kB'},
    {'context': 'main', 'key': 'shift-left',  'action': 'set srv.limit.rate.up -=100kB'},

    # Tab management
    {'context': 'tabs', 'key': 'n', 'action': 'tab'},
    {'context': 'tabs', 'key': 'd', 'action': 'tab --close'},
    {'context': 'tabs', 'key': 'D', 'action': 'tab --close --focus left'},
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
    {'context': 'torrent', 'key': 't v',       'action': 'verify'},
    {'context': 'torrent', 'key': 't p',       'action': 'pause --toggle'},
    {'context': 'torrent', 'key': 't P',       'action': 'start --toggle --force'},
    {'context': 'torrent', 'key': 't a',       'action': 'announce'},
    {'context': 'torrent', 'key': 't d',       'action': 'delete'},
    {'context': 'torrent', 'key': 't D',       'action': 'delete --delete-files'},
    {'context': 'torrent', 'key': 'enter',     'action': 'tab details'},
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

    # Torrent file actions
    {'context': 'file', 'key': '+',         'action': 'priority high'},
    {'context': 'file', 'key': '=',         'action': 'priority normal'},
    {'context': 'file', 'key': '-',         'action': 'priority low'},
    {'context': 'file', 'key': '0',         'action': 'priority shun'},
    {'context': 'file', 'key': 'space',     'action': 'mark --toggle --focus-next'},
    {'context': 'file', 'key': 'alt-space', 'action': 'mark --toggle --all'},
)
