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

import os

from xdg.BaseDirectory import xdg_config_home as XDG_CONFIG_HOME
from xdg.BaseDirectory import xdg_data_home as XDG_DATA_HOME

from .. import __appname__
from ..client.sorters import PeerSorter, SettingSorter, TorrentSorter, TrackerSorter
from ..utils import convert
from ..utils.usertypes import Bool, Float, Int, Option, Path, String, Tuple
from ..views import file, peer, setting, torrent, tracker

from ..logging import make_logger  # isort:skip
log = make_logger(__name__)


DEFAULT_RCFILE      = os.path.join(XDG_CONFIG_HOME, __appname__, 'rc')
DEFAULT_HISTORY_DIR = os.path.join(XDG_DATA_HOME, __appname__, 'histories')
DEFAULT_THEME_FILE  = os.path.join(os.path.dirname(__file__), 'default.theme')

DEFAULT_TAB_COMMANDS = (
    'tab ls active|!complete',
    'tab ls -c status,seeds,ratio,size,uploaded,path,name',
    'tab ls downloading -c size,downloaded,%downloaded,%available,rate-down,completed,eta,path,name',
    'tab ls uploading -c size,ratio,uploaded,rate-up,peers,seeds,tracker,path,name',
    'tab -t peers lsp -s torrent',
    'tab ls stopped -s ratio,path -c size,%downloaded,seeds,ratio,activity,completed,path,name',
    'tab ls isolated -c error,tracker,path,name -s tracker',
    'tab --focus 1',
)


def partial_sort_order(sortercls):
    # Because sort orders have aliases and can be inverted by prepending "!", we have to
    # smarten up.

    # The SortOrder class makes sort orders compare equal to their aliases with or without
    # any of the inverter chars prepended, e.g. "name" == "!n".
    class SortOrder(str):
        _invert_chars = ''.join(TorrentSorter.INVERT_CHARS)

        def __new__(cls, name, aliases):
            self = super().__new__(cls, name)
            self._aliases = tuple(aliases)
            self._hash = hash((name,) + self._aliases)
            return self

        def __eq__(self, other):
            other_ = other.lstrip(self._invert_chars)
            return (self.lstrip(self._invert_chars) == other_ or
                    any(a.lstrip(self._invert_chars) == other_ for a in self._aliases))

        # An overloaded __eq__() obligates an overloaded __hash__(), or instances won't be
        # hashable.
        def __hash__(self):
            return self._hash

        def __repr__(self):
            return '%s(%r, aliases=%r)' % (type(self).__name__, str(self), self._aliases)

    # Wrap available sort orders in a Tuple, which also must know the aliases for each
    # sort order so it can generate the syntax string for the help output.
    sort_orders = []
    aliases = {}  # Mapping (alias -> realname)
    for name,spec in sortercls.SORTSPECS.items():
        sort_orders.append(SortOrder(name, spec.aliases))
        for alias in spec.aliases:
            aliases[alias] = name
    return Tuple.partial(options=sort_orders, aliases=aliases, dedup=True)


class Bytes(Int):
    def __new__(cls, num, unit='B', **kwargs):
        return convert.size(super().__new__(cls, num, unit=unit, **kwargs), unit='byte')


def init_defaults(localcfg):
    from .. import objects

    localcfg.add('connect.host',
                 String.partial(),
                 getter=lambda: objects.srvapi.rpc.host,
                 setter=lambda v: setattr(objects.srvapi.rpc, 'host', v),
                 default='localhost',
                 description='Hostname or IP of Transmission RPC interface')
    localcfg.add('connect.port',
                 Int.partial(min=1, max=65535, prefix='none'),
                 getter=lambda: objects.srvapi.rpc.port,
                 setter=lambda v: setattr(objects.srvapi.rpc, 'port', v),
                 default=9091,
                 description='Port of Transmission RPC interface')
    localcfg.add('connect.path',
                 String.partial(),
                 getter=lambda: objects.srvapi.rpc.path,
                 setter=lambda v: setattr(objects.srvapi.rpc, 'path', v),
                 default='/transmission/rpc',
                 description='Path of Transmission RPC interface')
    localcfg.add('connect.user',
                 String.partial(),
                 getter=lambda: objects.srvapi.rpc.user,
                 setter=lambda v: setattr(objects.srvapi.rpc, 'user', v),
                 default='',
                 description='Username to use for authentication with Transmission RPC interface')
    localcfg.add('connect.password',
                 String.partial(),
                 getter=lambda: objects.srvapi.rpc.password,
                 setter=lambda v: setattr(objects.srvapi.rpc, 'password', v),
                 default='',
                 description='Password to use for authentication with Transmission RPC interface')
    localcfg.add('connect.timeout',
                 Float.partial(min=0),
                 getter=lambda: objects.srvapi.rpc.timeout,
                 setter=lambda v: setattr(objects.srvapi.rpc, 'timeout', v),
                 default=10,
                 description='Number of seconds before connecting to Transmission RPC interface fails')
    localcfg.add('connect.tls',
                 Bool.partial(),
                 getter=lambda: objects.srvapi.rpc.tls,
                 setter=lambda v: setattr(objects.srvapi.rpc, 'tls', v),
                 default='off',
                 description='Whether to connect via HTTPS to the Transmission RPC interface')
    localcfg.add('connect.url',
                 String.partial(),
                 getter=lambda: objects.srvapi.rpc.url_unsafe,
                 setter=lambda v: setattr(objects.srvapi.rpc, 'url', v),
                 default='http://localhost:9091/transmission/rpc',
                 description='URL of the Transmission RPC interface')
    localcfg.add('connect.proxy',
                 String.partial(),
                 getter=lambda: objects.srvapi.rpc.proxy,
                 setter=lambda v: setattr(objects.srvapi.rpc, 'proxy', v),
                 default='',
                 description='SOCKS5, SOCKS4 or HTTP proxy URL to tunnel RPC communication through')

    localcfg.add('columns.torrents',
                 Tuple.partial(options=torrent.COLUMNS, aliases=torrent.ALIASES),
                 default=('marked', 'size', 'downloaded', 'uploaded', 'ratio',
                          'seeds', 'peers', 'status', 'eta', '%downloaded',
                          'rate-down', 'rate-up', 'name'),
                 description='Default columns in torrent lists')
    localcfg.add('columns.peers',
                 Tuple.partial(options=peer.COLUMNS, aliases=peer.ALIASES),
                 default=('host', 'client', '%downloaded', 'rate-down',
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
                 partial_sort_order(PeerSorter),
                 default=PeerSorter.DEFAULT_SORT,
                 description='List of sort orders in peer lists')
    localcfg.add('sort.trackers',
                 partial_sort_order(TrackerSorter),
                 default=TrackerSorter.DEFAULT_SORT,
                 description='List of sort orders in tracker lists')
    localcfg.add('sort.settings',
                 partial_sort_order(SettingSorter),
                 default=SettingSorter.DEFAULT_SORT,
                 description='List of sort orders in setting lists')

    localcfg.add('tui.cli.history-dir',
                 Path.partial(base=os.path.expanduser('~')),
                 default=DEFAULT_HISTORY_DIR,
                 description='Directory where histories of user input are stored')
    localcfg.add('tui.cli.history-size',
                 Int.partial(min=0),
                 default=10000,
                 description='Maximum number of lines to keep in history files')
    localcfg.add('tui.free-space.low',
                 Bytes.partial(min=0),
                 default='10GB',
                 description='Minimum amount of free space before highlighting the display')
    localcfg.add('tui.log.height',
                 Int.partial(min=1),
                 default=10,
                 description='Maximum height of the log section')
    localcfg.add('tui.log.autohide',
                 Float.partial(min=0),
                 default=10,
                 description=('If the log is hidden, show it for this many seconds '
                              'for new log entries before hiding it again'))
    localcfg.add('tui.poll',
                 Float.partial(min=0.1),
                 default=5,
                 description='Interval in seconds between TUI updates')
    localcfg.add('tui.theme',
                 Path.partial(base=os.path.dirname(DEFAULT_RCFILE)),
                 default=DEFAULT_THEME_FILE,
                 description='Path to theme file'),

    localcfg.add('unit.bandwidth',
                 Option.partial(options=('bit', 'byte'), aliases={'b': 'bit', 'B': 'byte'}),
                 default='byte',
                 description="Unit for bandwidth rates ('bit' or 'byte')")
    localcfg.add('unitprefix.bandwidth',
                 Option.partial(options=('metric', 'binary'), aliases={'m': 'metric', 'b': 'binary'}),
                 default='metric',
                 description=("Unit prefix for bandwidth rates ('metric' or 'binary')"))

    localcfg.add('unit.size',
                 Option.partial(options=('bit', 'byte'), aliases={'b': 'bit', 'B': 'byte'}),
                 default='byte',
                 description="Unit for file sizes ('bit' or 'byte')")
    localcfg.add('unitprefix.size',
                 Option.partial(options=('metric', 'binary'), aliases={'m': 'metric', 'b': 'binary'}),
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
    {'context': 'main', 'key': 'alt-shift-s', 'action': 'dump',
     'description': 'Save current settings, keybindings and tabs in the default rc file'},
    {'context': 'main', 'key': 'shift-f', 'action': 'setcommand --trailing-space tab ls',
     'description': 'Find torrents in a new tab'},

    # Help
    {'context': 'main', 'key': 'F1 c', 'action': 'tab help commands',
     'description': 'Open help for commands in a new tab'},
    {'context': 'main', 'key': 'F1 s', 'action': 'tab help settings',
     'description': 'Open help for settings in a new tab'},
    {'context': 'main', 'key': 'F1 k', 'action': 'tab help keybindings',
     'description': 'Open help for keybindings in a new tab'},
    {'context': 'main', 'key': 'F1 f', 'action': 'tab help filters',
     'description': 'Open help for filters in a new tab'},
    {'context': 'main', 'key': 'F1 r', 'action': 'tab help cfgman',
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
    {'context': 'tabs', 'key': 'H',     'action': 'tab --move left',
     'description': 'Move current tab to the left'},
    {'context': 'tabs', 'key': 'L',     'action': 'tab --move right',
     'description': 'Move current tab to the right'},

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
    {'context': 'torrentlist', 'key': 's p', 'action': 'sort --add path',
     'description': TorrentSorter.SORTSPECS['path'].description},
    {'context': 'torrentlist', 'key': 's P', 'action': 'sort --add !path',
     'description': TorrentSorter.SORTSPECS['path'].description + ' (reverse)'},
    {'context': 'torrentlist', 'key': 's n', 'action': 'sort --add name',
     'description': TorrentSorter.SORTSPECS['name'].description},
    {'context': 'torrentlist', 'key': 's N', 'action': 'sort --add !name',
     'description': TorrentSorter.SORTSPECS['name'].description + ' (reverse)'},
    {'context': 'torrentlist', 'key': 's o', 'action': 'sort --add ratio',
     'description': TorrentSorter.SORTSPECS['ratio'].description},
    {'context': 'torrentlist', 'key': 's O', 'action': 'sort --add !ratio',
     'description': TorrentSorter.SORTSPECS['ratio'].description + ' (reverse)'},
    {'context': 'torrentlist', 'key': 's d', 'action': 'sort --add %downloaded',
     'description': TorrentSorter.SORTSPECS['%downloaded'].description},
    {'context': 'torrentlist', 'key': 's D', 'action': 'sort --add !%downloaded',
     'description': TorrentSorter.SORTSPECS['%downloaded'].description + ' (reverse)'},
    {'context': 'torrentlist', 'key': 's s', 'action': 'sort --add seeds',
     'description': TorrentSorter.SORTSPECS['seeds'].description},
    {'context': 'torrentlist', 'key': 's S', 'action': 'sort --add !seeds',
     'description': TorrentSorter.SORTSPECS['seeds'].description + ' (reverse)'},
    {'context': 'torrentlist', 'key': 's t', 'action': 'sort --add tracker',
     'description': TorrentSorter.SORTSPECS['tracker'].description},
    {'context': 'torrentlist', 'key': 's T', 'action': 'sort --add !tracker',
     'description': TorrentSorter.SORTSPECS['tracker'].description + ' (reverse)'},
    {'context': 'torrentlist', 'key': 's z', 'action': 'sort --add size',
     'description': TorrentSorter.SORTSPECS['size'].description},
    {'context': 'torrentlist', 'key': 's Z', 'action': 'sort --add !size',
     'description': TorrentSorter.SORTSPECS['size'].description + ' (reverse)'},

    {'context': 'torrentlist', 'key': 's m a', 'action': 'sort --add activity',
     'description': TorrentSorter.SORTSPECS['activity'].description},
    {'context': 'torrentlist', 'key': 's m A', 'action': 'sort --add !activity',
     'description': TorrentSorter.SORTSPECS['activity'].description + ' (reverse)'},
    {'context': 'torrentlist', 'key': 's m c', 'action': 'sort --add completed',
     'description': TorrentSorter.SORTSPECS['completed'].description},
    {'context': 'torrentlist', 'key': 's m C', 'action': 'sort --add !completed',
     'description': TorrentSorter.SORTSPECS['completed'].description + ' (reverse)'},
    {'context': 'torrentlist', 'key': 's m r', 'action': 'sort --add created',
     'description': TorrentSorter.SORTSPECS['created'].description},
    {'context': 'torrentlist', 'key': 's m R', 'action': 'sort --add !created',
     'description': TorrentSorter.SORTSPECS['created'].description + ' (reverse)'},
    {'context': 'torrentlist', 'key': 's m d', 'action': 'sort --add added',
     'description': TorrentSorter.SORTSPECS['added'].description},
    {'context': 'torrentlist', 'key': 's m D', 'action': 'sort --add !added',
     'description': TorrentSorter.SORTSPECS['added'].description + ' (reverse)'},
    {'context': 'torrentlist', 'key': 's m e', 'action': 'sort --add eta',
     'description': TorrentSorter.SORTSPECS['eta'].description},
    {'context': 'torrentlist', 'key': 's m E', 'action': 'sort --add !eta',
     'description': TorrentSorter.SORTSPECS['eta'].description + ' (reverse)'},
    {'context': 'torrentlist', 'key': 's m s', 'action': 'sort --add started',
     'description': TorrentSorter.SORTSPECS['started'].description},
    {'context': 'torrentlist', 'key': 's m S', 'action': 'sort --add !started',
     'description': TorrentSorter.SORTSPECS['started'].description + ' (reverse)'},

    {'context': 'torrentlist', 'key': 's r d', 'action': 'sort --add rate-down',
     'description': TorrentSorter.SORTSPECS['rate-down'].description},
    {'context': 'torrentlist', 'key': 's r D', 'action': 'sort --add !rate-down',
     'description': TorrentSorter.SORTSPECS['rate-down'].description + ' (reverse)'},
    {'context': 'torrentlist', 'key': 's r u', 'action': 'sort --add rate-up',
     'description': TorrentSorter.SORTSPECS['rate-up'].description},
    {'context': 'torrentlist', 'key': 's r U', 'action': 'sort --add !rate-up',
     'description': TorrentSorter.SORTSPECS['rate-up'].description + ' (reverse)'},
    {'context': 'torrentlist', 'key': 's r r', 'action': 'sort --add rate',
     'description': TorrentSorter.SORTSPECS['rate'].description},
    {'context': 'torrentlist', 'key': 's r R', 'action': 'sort --add !rate',
     'description': TorrentSorter.SORTSPECS['rate'].description + ' (reverse)'},

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
    {'context': 'torrent', 'key': 'enter',     'action': 'tab details',
     'description': 'Show details about focused torrent in a new tab'},
    {'context': 'torrent', 'key': 'alt-enter', 'action': 'tab filelist',
     'description': 'List selected or focused torrents\' files in a new tab'},
    {'context': 'torrent', 'key': 'space',     'action': 'mark --toggle --focus-next',
     'description': 'Mark or unmark focused torrent'},
    {'context': 'torrent', 'key': 'alt-space', 'action': 'mark --toggle --all',
     'description': 'Mark or unmark all torrents'},

    # Peer list actions
    {'context': 'peerlist', 'key': 's e', 'action': 'sort --add eta',
     'description': PeerSorter.SORTSPECS['eta'].description},
    {'context': 'peerlist', 'key': 's E', 'action': 'sort --add !eta',
     'description': PeerSorter.SORTSPECS['eta'].description + ' (reverse)'},
    {'context': 'peerlist', 'key': 's h', 'action': 'sort --add host',
     'description': PeerSorter.SORTSPECS['host'].description},
    {'context': 'peerlist', 'key': 's H', 'action': 'sort --add !host',
     'description': PeerSorter.SORTSPECS['host'].description + ' (reverse)'},
    {'context': 'peerlist', 'key': 's c', 'action': 'sort --add client',
     'description': PeerSorter.SORTSPECS['client'].description},
    {'context': 'peerlist', 'key': 's C', 'action': 'sort --add !client',
     'description': PeerSorter.SORTSPECS['client'].description + ' (reverse)'},
    {'context': 'peerlist', 'key': 's p', 'action': 'sort --add %downloaded',
     'description': PeerSorter.SORTSPECS['%downloaded'].description},
    {'context': 'peerlist', 'key': 's P', 'action': 'sort --add !%downloaded',
     'description': PeerSorter.SORTSPECS['%downloaded'].description + ' (reverse)'},

    {'context': 'peerlist', 'key': 's r u', 'action': 'sort --add rate-up',
     'description': PeerSorter.SORTSPECS['rate-up'].description},
    {'context': 'peerlist', 'key': 's r U', 'action': 'sort --add !rate-up',
     'description': PeerSorter.SORTSPECS['rate-up'].description + ' (reverse)'},
    {'context': 'peerlist', 'key': 's r d', 'action': 'sort --add rate-down',
     'description': PeerSorter.SORTSPECS['rate-down'].description},
    {'context': 'peerlist', 'key': 's r D', 'action': 'sort --add !rate-down',
     'description': PeerSorter.SORTSPECS['rate-down'].description + ' (reverse)'},
    {'context': 'peerlist', 'key': 's r r', 'action': 'sort --add rate',
     'description': PeerSorter.SORTSPECS['rate'].description},
    {'context': 'peerlist', 'key': 's r R', 'action': 'sort --add !rate',
     'description': PeerSorter.SORTSPECS['rate'].description + ' (reverse)'},
    {'context': 'peerlist', 'key': 's r e', 'action': 'sort --add rate-est',
     'description': PeerSorter.SORTSPECS['rate-est'].description},
    {'context': 'peerlist', 'key': 's r E', 'action': 'sort --add !rate-est',
     'description': PeerSorter.SORTSPECS['rate-est'].description + ' (reverse)'},

    {'context': 'peerlist', 'key': 's t', 'action': 'sort --add torrent',
     'description': PeerSorter.SORTSPECS['torrent'].description},
    {'context': 'peerlist', 'key': 's T', 'action': 'sort --add !torrent',
     'description': PeerSorter.SORTSPECS['torrent'].description + ' (reverse)'},
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
    {'context': 'trackerlist', 'key': 's e',   'action': 'sort --add error',
     'description': TrackerSorter.SORTSPECS['error'].description},
    {'context': 'trackerlist', 'key': 's E',   'action': 'sort --add !error',
     'description': TrackerSorter.SORTSPECS['error'].description + ' (reverse)'},
    {'context': 'trackerlist', 'key': 's s',   'action': 'sort --add status',
     'description': TrackerSorter.SORTSPECS['status'].description},
    {'context': 'trackerlist', 'key': 's S',   'action': 'sort --add !status',
     'description': TrackerSorter.SORTSPECS['status'].description + ' (reverse)'},
    {'context': 'trackerlist', 'key': 's d',   'action': 'sort --add domain',
     'description': TrackerSorter.SORTSPECS['domain'].description},
    {'context': 'trackerlist', 'key': 's D',   'action': 'sort --add !domain',
     'description': TrackerSorter.SORTSPECS['domain'].description + ' (reverse)'},
    {'context': 'trackerlist', 'key': 's t',   'action': 'sort --add torrent',
     'description': TrackerSorter.SORTSPECS['torrent'].description},
    {'context': 'trackerlist', 'key': 's T',   'action': 'sort --add !torrent',
     'description': TrackerSorter.SORTSPECS['torrent'].description + ' (reverse)'},

    {'context': 'trackerlist', 'key': 's n d',   'action': 'sort --add downloads',
     'description': TrackerSorter.SORTSPECS['downloads'].description},
    {'context': 'trackerlist', 'key': 's n D',   'action': 'sort --add !downloads',
     'description': TrackerSorter.SORTSPECS['downloads'].description + ' (reverse)'},
    {'context': 'trackerlist', 'key': 's n l',   'action': 'sort --add leeches',
     'description': TrackerSorter.SORTSPECS['leeches'].description},
    {'context': 'trackerlist', 'key': 's n L',   'action': 'sort --add !leeches',
     'description': TrackerSorter.SORTSPECS['leeches'].description + ' (reverse)'},
    {'context': 'trackerlist', 'key': 's n s',   'action': 'sort --add seeds',
     'description': TrackerSorter.SORTSPECS['seeds'].description},
    {'context': 'trackerlist', 'key': 's n S',   'action': 'sort --add !seeds',
     'description': TrackerSorter.SORTSPECS['seeds'].description + ' (reverse)'},

    {'context': 'trackerlist', 'key': 's a n', 'action': 'sort --add next-announce',
     'description': TrackerSorter.SORTSPECS['next-announce'].description},
    {'context': 'trackerlist', 'key': 's a N', 'action': 'sort --add !next-announce',
     'description': TrackerSorter.SORTSPECS['next-announce'].description + ' (reverse)'},
    {'context': 'trackerlist', 'key': 's a l', 'action': 'sort --add last-announce',
     'description': TrackerSorter.SORTSPECS['last-announce'].description},
    {'context': 'trackerlist', 'key': 's a L', 'action': 'sort --add !last-announce',
     'description': TrackerSorter.SORTSPECS['last-announce'].description + ' (reverse)'},

    {'context': 'trackerlist', 'key': 's ,',   'action': 'sort --reset',
     'description': 'Reset to initial sort orders'},
    {'context': 'trackerlist', 'key': 's .',   'action': 'sort --none',
     'description': 'Remove all sort orders'},
    {'context': 'trackerlist', 'key': '/',     'action': ("interactive 'limit \"[]\"' --per-change "
                                                          "--on-cancel 'limit --clear' --ignore-errors"),
     'description': 'Reduce listed trackers by applying more filters'},

    # Tracker actions
    {'context': 'torrent', 'key': 'enter', 'action': 'tab details',
     'description': 'Show details about torrent of focused tracker in new tab'},
    {'context': 'torrent', 'key': 'alt-enter', 'action': 'tab filelist',
     'description': 'List files of torrent of focused tracker in a new tab'},

    # Setting list actions
    {'context': 'settinglist', 'key': 's n', 'action': 'sort --add name',
     'description': SettingSorter.SORTSPECS['name'].description},
    {'context': 'settinglist', 'key': 's N', 'action': 'sort --add !name',
     'description': SettingSorter.SORTSPECS['name'].description + ' (reverse)'},
    {'context': 'settinglist', 'key': 's v', 'action': 'sort --add value',
     'description': SettingSorter.SORTSPECS['value'].description},
    {'context': 'settinglist', 'key': 's V', 'action': 'sort --add !value',
     'description': SettingSorter.SORTSPECS['value'].description + ' (reverse)'},
    {'context': 'settinglist', 'key': 's d', 'action': 'sort --add default',
     'description': SettingSorter.SORTSPECS['default'].description},
    {'context': 'settinglist', 'key': 's D', 'action': 'sort --add !default',
     'description': SettingSorter.SORTSPECS['default'].description + ' (reverse)'},
    {'context': 'settinglist', 'key': 's c', 'action': 'sort --add description',
     'description': SettingSorter.SORTSPECS['description'].description},
    {'context': 'settinglist', 'key': 's C', 'action': 'sort --add !description',
     'description': SettingSorter.SORTSPECS['description'].description + ' (reverse)'},
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
     'description': 'Find next occurrence of search string'},
    {'context': 'helptext', 'key': 'ctrl-n', 'action': 'find --next',
     'description': 'Find next occurrence of search string'},
    {'context': 'helptext', 'key': 'N',      'action': 'find --previous',
     'description': 'Find previous occurrence of search string'},
    {'context': 'helptext', 'key': 'ctrl-p', 'action': 'find --previous',
     'description': 'Find previous occurrence of search string'},
)
