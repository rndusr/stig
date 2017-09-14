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


def _connect_to_new_url(url):
    # See also ..hooks
    async def coro():
        try:
            await srvapi.rpc.connect(url.value)
        except srvapi.ClientError as e:
            log.error(str(e))
    aioloop.create_task(coro())
cfg['srv.url'].on_change(_connect_to_new_url)


def _update_pollers(url):
    tui.srvapi.poll()
srvapi.rpc.on('connected', _update_pollers)
srvapi.rpc.on('disconnected', _update_pollers)


def _refresh_lists(value):
    for widget in tui.tabs:
        if isinstance(widget, (TorrentListWidget, FileListWidget, PeerListWidget)):
            widget.clear()
            widget.refresh()
cfg['unit.bandwidth'].on_change(_refresh_lists)
cfg['unit.size'].on_change(_refresh_lists)
cfg['unitprefix.bandwidth'].on_change(_refresh_lists)
cfg['unitprefix.size'].on_change(_refresh_lists)


def _set_poll_interval(seconds):
    tui.srvapi.interval = seconds.value
cfg['tui.poll'].on_change(_set_poll_interval)


def _set_cli_history_file(histfile):
    tui.cli.original_widget.history_file = histfile.value
cfg['tui.cli.history-file'].on_change(_set_cli_history_file)


def _set_cli_history_size(histsize):
    tui.cli.original_widget.history_size = histsize.value
cfg['tui.cli.history-size'].on_change(_set_cli_history_size)


def _set_autohide_delay(seconds):
    tui.logwidget.autohide_delay = seconds.value
cfg['tui.log.autohide'].on_change(_set_autohide_delay)


def _set_log_height(rows):
    tui.logwidget.height = rows.value
cfg['tui.log.height'].on_change(_set_log_height)


def _set_theme(themefile):
    try:
        tui.load_theme(themefile.value)
    except tui.theme.ThemeError as e:
        raise ValueError(e)
cfg['tui.theme'].on_change(_set_theme)


def _set_tui_marked_char(methodname, setting):
    getattr(TORRENT_COLUMNS['marked'], methodname)(setting.value)
    getattr(FILE_COLUMNS['marked'], methodname)(setting.value)

    for widget in tui.tabs:
        if isinstance(widget, (TorrentListWidget, FileListWidget)):
            widget.refresh_marks()
cfg['tui.marked.on'].on_change(partial(_set_tui_marked_char, 'set_marked_char'), autoremove=False)
cfg['tui.marked.off'].on_change(partial(_set_tui_marked_char, 'set_unmarked_char'), autoremove=False)
_set_tui_marked_char('set_marked_char', cfg['tui.marked.on'])
_set_tui_marked_char('set_unmarked_char', cfg['tui.marked.off'])


def _update_quickhelp(keymap):
    tui.topbar.help.update()
tui.keymap.on_bind_unbind(_update_quickhelp)
