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

from ..main import (cfg, srvapi, aioloop)
from . import main as tui

from .views.torrentlist import TorrentListWidget
from .views.filelist import FileListWidget
from .views.peerlist import PeerListWidget

from .views.tlist_columns import TUICOLUMNS as TORRENT_COLUMNS
from .views.flist_columns import TUICOLUMNS as FILE_COLUMNS


def _reconnect(settings, name, value):
    # See also ..hooks
    async def coro():
        log.debug('Reconnecting because %s changed to %r', name, value)
        try:
            await srvapi.rpc.connect()
        except srvapi.ClientError as e:
            log.error(str(e))
    aioloop.create_task(coro())
cfg.on_change(_reconnect, name='connect.host')
cfg.on_change(_reconnect, name='connect.port')
cfg.on_change(_reconnect, name='connect.path')
cfg.on_change(_reconnect, name='connect.user')
cfg.on_change(_reconnect, name='connect.password')
cfg.on_change(_reconnect, name='connect.tls')


def _update_pollers(rpc):
    tui.srvapi.poll()
srvapi.rpc.on('connected', _update_pollers)
srvapi.rpc.on('disconnected', _update_pollers)


def _refresh_lists(settings, name, value):
    for widget in tui.tabs:
        if isinstance(widget, (TorrentListWidget, FileListWidget, PeerListWidget)):
            widget.clear()
            widget.refresh()
cfg.on_change(_refresh_lists, name='unit.bandwidth')
cfg.on_change(_refresh_lists, name='unit.size')
cfg.on_change(_refresh_lists, name='unitprefix.bandwidth')
cfg.on_change(_refresh_lists, name='unitprefix.size')


def _set_poll_interval(settings, name, value):
    tui.srvapi.interval = value
cfg.on_change(_set_poll_interval, name='tui.poll')


def _set_cli_history_file(settings, name, value):
    tui.cli.original_widget.history_file = value
cfg.on_change(_set_cli_history_file, name='tui.cli.history-file')


def _set_cli_history_size(settings, name, value):
    tui.cli.original_widget.history_size = value
cfg.on_change(_set_cli_history_size, name='tui.cli.history-size')


def _set_autohide_delay(settings, name, value):
    tui.logwidget.autohide_delay = value
cfg.on_change(_set_autohide_delay, name='tui.log.autohide')


def _set_log_height(settings, name, value):
    tui.logwidget.height = int(value)
cfg.on_change(_set_log_height, name='tui.log.height')


def _set_theme(settings, name, value):
    try:
        tui.load_theme(value)
    except tui.theme.ThemeError as e:
        raise ValueError(e)
cfg.on_change(_set_theme, name='tui.theme')


def _set_tui_marked_char(methodname, settings, name, value):
    getattr(TORRENT_COLUMNS['marked'], methodname)(value)
    getattr(FILE_COLUMNS['marked'], methodname)(value)
    for widget in tui.tabs:
        if isinstance(widget, (TorrentListWidget, FileListWidget)):
            widget.refresh_marks()
cfg.on_change(partial(_set_tui_marked_char, 'set_marked_char'), name='tui.marked.on', autoremove=False)
cfg.on_change(partial(_set_tui_marked_char, 'set_unmarked_char'), name='tui.marked.off', autoremove=False)
_set_tui_marked_char('set_marked_char', cfg, name='tui.marked.on', value=cfg['tui.marked.on'])
_set_tui_marked_char('set_unmarked_char', cfg, name='tui.marked.off', value=cfg['tui.marked.off'])


def _update_quickhelp(keymap):
    tui.topbar.help.update()
tui.keymap.on_bind_unbind(_update_quickhelp)
