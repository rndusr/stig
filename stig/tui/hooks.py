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

from ..main import (cfg, srvapi, aioloop)
from . import main as tui
from ..client import ClientError


def _connect_to_new_url(url):
    # See also ..hooks
    async def coro():
        try:
            await srvapi.rpc.connect(url.value)
        except ClientError as e:
            pass
    aioloop.create_task(coro())
cfg['srv.url'].on_change(_connect_to_new_url)

def _update_pollers(seconds):
    tui.srvapi.poll()
srvapi.rpc.on('connected', _update_pollers)

def _clear_list_widgets(seconds):
    from .torrent.tlist import TorrentListWidget
    from .torrent.flist import FileListWidget
    for widget in tui.tabs.contents:
        if isinstance(widget, (TorrentListWidget, FileListWidget)):
            widget.clear()
srvapi.rpc.on('disconnected', _clear_list_widgets)

def _set_poll_interval(seconds):
    tui.srvapi.interval = seconds.value
cfg['tui.poll'].on_change(_set_poll_interval)

def _set_cli_history(histfile):
    tui.cli.original_widget.history_file = histfile.value
cfg['tui.cli.history'].on_change(_set_cli_history)

def _set_autohide_delay(seconds):
    tui.log.autohide_delay = seconds.value
cfg['tui.log.autohide'].on_change(_set_autohide_delay)

def _set_log_maxrows(rows):
    tui.log.maxrows = rows.value
cfg['tui.log.height'].on_change(_set_log_maxrows)

def _set_theme(themefile):
    try:
        tui.theme.load(cfg['tui.theme'].value, tui.urwidscreen)
    except tui.theme.ThemeError as e:
        raise ValueError(e)
cfg['tui.theme'].on_change(_set_theme)

def _refresh_tlists(value):
    from .torrent.tlist import TorrentListWidget
    from .torrent.flist import FileListWidget
    for widget in tui.tabs:
        if isinstance(widget, (TorrentListWidget, FileListWidget)):
            widget.clear()
    tui.srvapi.poll()
cfg['unit.bandwidth'].on_change(_refresh_tlists)
cfg['unit.size'].on_change(_refresh_tlists)
cfg['unitprefix.bandwidth'].on_change(_refresh_tlists)
cfg['unitprefix.size'].on_change(_refresh_tlists)
