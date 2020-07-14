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
from functools import partial

from . import tuiobjects
from ..objects import localcfg, srvapi
from .views.file import TUICOLUMNS as FILE_COLUMNS
from .views.file_list import FileListWidget
from .views.peer_list import PeerListWidget
from .views.torrent import TUICOLUMNS as TORRENT_COLUMNS
from .views.torrent_list import TorrentListWidget

from ..logging import make_logger  # isort:skip
log = make_logger(__name__)


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
localcfg.on_change(_reconnect, name='connect.url')
localcfg.on_change(_reconnect, name='connect.proxy')


# TODO: These are probably not needed?
# def _update_pollers(rpc):
#     srvapi.poll()
# srvapi.rpc.on('connected', _update_pollers)
# srvapi.rpc.on('disconnected', _update_pollers)


def _refresh_diskspace(settings, name, value):
    tuiobjects.bottombar.diskspace.refresh()
localcfg.on_change(_refresh_diskspace, name='tui.free-space.low')


def _refresh_lists(settings, name, value):
    for widget in tuiobjects.tabs:
        if isinstance(widget, (TorrentListWidget, FileListWidget, PeerListWidget)):
            widget.clear()
            widget.refresh()
localcfg.on_change(_refresh_lists, name='unit.bandwidth')
localcfg.on_change(_refresh_lists, name='unit.size')
localcfg.on_change(_refresh_lists, name='unitprefix.bandwidth')
localcfg.on_change(_refresh_lists, name='unitprefix.size')
localcfg.on_change(_refresh_lists, name='reverse-dns')


def _set_poll_interval(settings, name, value):
    srvapi.interval = value
localcfg.on_change(_set_poll_interval, name='tui.poll')


def _set_cli_history_dir(settings, name, value):
    tuiobjects.cli.original_widget.history_file = os.path.join(value.full_path, 'commands')
localcfg.on_change(_set_cli_history_dir, name='tui.cli.history-dir')

def _set_cli_history_size(settings, name, value):
    tuiobjects.cli.original_widget.history_size = value
localcfg.on_change(_set_cli_history_size, name='tui.cli.history-size')


def _set_autohide_delay(settings, name, value):
    tuiobjects.logwidget.autohide_delay = value
localcfg.on_change(_set_autohide_delay, name='tui.log.autohide')


def _set_log_height(settings, name, value):
    tuiobjects.logwidget.height = int(value)
localcfg.on_change(_set_log_height, name='tui.log.height')


def _set_theme(settings, name, value):
    try:
        tuiobjects.theme.load(value.full_path, tuiobjects.urwidscreen)
    except tuiobjects.theme.ThemeError as e:
        raise ValueError(e)
localcfg.on_change(_set_theme, name='tui.theme')


def _set_tui_marked_char(methodname, settings, name, value):
    getattr(TORRENT_COLUMNS['marked'], methodname)(value)
    getattr(FILE_COLUMNS['marked'], methodname)(value)
    for widget in tuiobjects.tabs:
        if isinstance(widget, (TorrentListWidget, FileListWidget)):
            widget.refresh_marks()
localcfg.on_change(partial(_set_tui_marked_char, 'set_marked_char'), name='tui.marked.on', autoremove=False)
localcfg.on_change(partial(_set_tui_marked_char, 'set_unmarked_char'), name='tui.marked.off', autoremove=False)
_set_tui_marked_char('set_marked_char', localcfg, name='tui.marked.on', value=localcfg['tui.marked.on'])
_set_tui_marked_char('set_unmarked_char', localcfg, name='tui.marked.off', value=localcfg['tui.marked.off'])


def _update_quickhelp(keymap):
    tuiobjects.topbar.help.update()
tuiobjects.keymap.on_bind_unbind(_update_quickhelp)
