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

from functools import partial
import os

from ..main import (localcfg, srvapi, aioloop)
from . import main as tui

from .views.torrent_list import TorrentListWidget
from .views.file_list import FileListWidget
from .views.peer_list import PeerListWidget

from .views.torrent import TUICOLUMNS as TORRENT_COLUMNS
from .views.file import TUICOLUMNS as FILE_COLUMNS


def _reconnect(settings, name, value):
    # See also ..hooks
    log.debug('Reconnecting because %s changed to %r', name, value)
    srvapi.poll()
localcfg.on_change(_reconnect, name='connect.host')
localcfg.on_change(_reconnect, name='connect.port')
localcfg.on_change(_reconnect, name='connect.path')
localcfg.on_change(_reconnect, name='connect.user')
localcfg.on_change(_reconnect, name='connect.password')
localcfg.on_change(_reconnect, name='connect.tls')


def _update_pollers(rpc):
    tui.srvapi.poll()
srvapi.rpc.on('connected', _update_pollers)
srvapi.rpc.on('disconnected', _update_pollers)


def _refresh_lists(settings, name, value):
    for widget in tui.tabs:
        if isinstance(widget, (TorrentListWidget, FileListWidget, PeerListWidget)):
            widget.clear()
            widget.refresh()
localcfg.on_change(_refresh_lists, name='unit.bandwidth')
localcfg.on_change(_refresh_lists, name='unit.size')
localcfg.on_change(_refresh_lists, name='unitprefix.bandwidth')
localcfg.on_change(_refresh_lists, name='unitprefix.size')
localcfg.on_change(_refresh_lists, name='reverse-dns')
localcfg.on_change(_refresh_lists, name='geoip')


def _set_poll_interval(settings, name, value):
    tui.srvapi.interval = value
localcfg.on_change(_set_poll_interval, name='tui.poll')


def _set_cli_history_dir(settings, name, value):
    tui.cli.original_widget.history_file = os.path.join(value, 'commands')
localcfg.on_change(_set_cli_history_dir, name='tui.cli.history-dir')

def _set_cli_history_size(settings, name, value):
    tui.cli.original_widget.history_size = value
localcfg.on_change(_set_cli_history_size, name='tui.cli.history-size')


def _set_autohide_delay(settings, name, value):
    tui.logwidget.autohide_delay = value
localcfg.on_change(_set_autohide_delay, name='tui.log.autohide')


def _set_log_height(settings, name, value):
    tui.logwidget.height = int(value)
localcfg.on_change(_set_log_height, name='tui.log.height')


def _set_theme(settings, name, value):
    try:
        tui.load_theme(value)
    except tui.theme.ThemeError as e:
        raise ValueError(e)
localcfg.on_change(_set_theme, name='tui.theme')


def _set_tui_marked_char(methodname, settings, name, value):
    getattr(TORRENT_COLUMNS['marked'], methodname)(value)
    getattr(FILE_COLUMNS['marked'], methodname)(value)
    for widget in tui.tabs:
        if isinstance(widget, (TorrentListWidget, FileListWidget)):
            widget.refresh_marks()
localcfg.on_change(partial(_set_tui_marked_char, 'set_marked_char'), name='tui.marked.on', autoremove=False)
localcfg.on_change(partial(_set_tui_marked_char, 'set_unmarked_char'), name='tui.marked.off', autoremove=False)
_set_tui_marked_char('set_marked_char', localcfg, name='tui.marked.on', value=localcfg['tui.marked.on'])
_set_tui_marked_char('set_unmarked_char', localcfg, name='tui.marked.off', value=localcfg['tui.marked.off'])


def _update_quickhelp(keymap):
    tui.topbar.help.update()
tui.keymap.on_bind_unbind(_update_quickhelp)


def _set_geoip(settings, name, value):
    if value:
        tui.load_geoip_db()
localcfg.on_change(_set_geoip, name='geoip')
