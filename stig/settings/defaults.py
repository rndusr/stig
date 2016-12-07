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
from ..columns.tlist import COLUMNS as TCOLUMNS
from ..columns.flist import COLUMNS as FCOLUMNS
from ..client.tsort import SORTERS

DEFAULT_RCFILE        = user_config_dir(APPNAME) + '/rc'
DEFAULT_HISTORY_FILE  = user_cache_dir(APPNAME)+'/history'
DEFAULT_THEME_FILE    = os.path.dirname(__file__) + os.sep + 'default.theme'

DEFAULT_TLIST_SORT    = ('name',)
DEFAULT_TLIST_COLUMNS = ('name', 'ratio', 'size', 'downloaded', 'uploaded',
                         'eta', 'peers-connected', 'peers-seeding', 'rate-down',
                         'rate-up')
DEFAULT_FLIST_COLUMNS = ('priority', 'name', 'progress', 'downloaded', 'size')


from .settings import (StringValue, IntegerValue, NumberValue, BooleanValue,
                       PathValue, ListValue, SetValue, OptionValue)

class TorrentSortValue(SetValue):
    """SetValue that correctly validates inverted sort orders (e.g. '!name')"""
    def __init__(self, *args, options=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.options = tuple(SORTERS)

    def validate(self, names):
        for name in names:
            if name[0] == '!':
                name = name[1:]
            if name not in SORTERS:
                raise ValueError('Invalid sort order: {!r}'.format(name))


def init_defaults(cfg):
    cfg.load(
        StringValue('srv.url', default='http://localhost:9091',
                    description='URL of the Transmission RPC interface'),
        NumberValue('srv.timeout', default=10, min=0,
                    description=('Number of seconds before connecting '
                                 'to Transmission daemon fails')),

        SetValue('tlist.columns', default=DEFAULT_TLIST_COLUMNS,
                 options=tuple(TCOLUMNS),
                 description='List of columns in new torrent lists'),
        TorrentSortValue('tlist.sort', default=DEFAULT_TLIST_SORT,
                 description='List of torrent sort orders'),

        SetValue('flist.columns', default=DEFAULT_FLIST_COLUMNS,
                 options=tuple(FCOLUMNS),
                 description='List of columns in new torrent file lists'),


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
        OptionValue('unitprefix.size', default='metric', options=('metric', 'binary'),
                    description=("Unit prefix for sizes ('metric' or 'binary')")),
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
    {'context': None, 'key': 'h', 'action': '<left>'},
    {'context': None, 'key': 'j', 'action': '<down>'},
    {'context': None, 'key': 'k', 'action': '<up>'},
    {'context': None, 'key': 'l', 'action': '<right>'},
    {'context': None, 'key': 'ctrl-n', 'action': '<down>'},
    {'context': None, 'key': 'ctrl-p', 'action': '<up>'},
    {'context': None, 'key': 'ctrl-f', 'action': '<pgdn>'},
    {'context': None, 'key': 'ctrl-b', 'action': '<pgup>'},

    {'context': 'main', 'key': 'q', 'action': 'quit'},
    {'context': 'main', 'key': '?', 'action': 'tab help keymap'},
    {'context': 'main', 'key': ':', 'action': 'tui show cli'},
    {'context': 'main', 'key': 'ctrl-l', 'action': 'clearlog'},
    {'context': 'main', 'key': 'meta-L', 'action': 'tui toggle log'},
    {'context': 'main', 'key': 'meta-M', 'action': 'tui toggle main'},
    {'context': 'main', 'key': 'meta-T', 'action': 'tui toggle topbar'},
    {'context': 'main', 'key': 'meta-B', 'action': 'tui toggle bottombar'},

    {'context': 'main', 'key': 'shift-up',    'action': 'set srv.limit.rate.down +=100kB'},
    {'context': 'main', 'key': 'shift-down',  'action': 'set srv.limit.rate.down -=100kB'},
    {'context': 'main', 'key': 'shift-right', 'action': 'set srv.limit.rate.up +=100kB'},
    {'context': 'main', 'key': 'shift-left',  'action': 'set srv.limit.rate.up -=100kB'},

    {'context': 'tabs', 'key': 't', 'action': 'tab'},
    {'context': 'tabs', 'key': 'd', 'action': 'tab --close'},
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

    {'context': 'tabs', 'key': 'a', 'action': 'ls active'},
    {'context': 'tabs', 'key': 'A', 'action': 'tab ls active'},
    {'context': 'tabs', 'key': 'i', 'action': 'ls isolated'},
    {'context': 'tabs', 'key': 'I', 'action': 'tab ls isolated'},
    {'context': 'tabs', 'key': 's', 'action': 'ls stopped'},
    {'context': 'tabs', 'key': 'S', 'action': 'tab ls stopped'},
    {'context': 'tabs', 'key': 'z', 'action': 'ls'},
    {'context': 'tabs', 'key': 'Z', 'action': 'tab ls'},

    {'context': 'torrent', 'key': 'v', 'action': 'verify'},
    {'context': 'torrent', 'key': 'p', 'action': 'stop --toggle'},
    {'context': 'torrent', 'key': 'P', 'action': 'start --toggle --force'},
    {'context': 'torrent', 'key': 'delete', 'action': 'remove'},
    {'context': 'torrent', 'key': 'shift-delete', 'action': 'remove --delete-files'},
    {'context': 'torrent', 'key': 'enter', 'action': 'tab filelist'},

    {'context': 'file', 'key': '+', 'action': 'priority high'},
    {'context': 'file', 'key': '=', 'action': 'priority normal'},
    {'context': 'file', 'key': '-', 'action': 'priority low'},
    {'context': 'file', 'key': '0', 'action': 'priority shun'},
)
