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

"""General hooks that are always needed regardless of the interface"""

from .logging import make_logger
log = make_logger(__name__)

from .main import (cfg, srvapi)
from .utils import convert
from .views.torrentlist import COLUMNS as TORRENT_COLUMNS
from .views.filelist import COLUMNS as FILE_COLUMNS
from .views.peerlist import COLUMNS as PEER_COLUMNS


def _make_connection_callback(name):
    def on_set(setting):
        log.debug('Setting rpc.%s=%r', name, setting.value)
        setattr(srvapi.rpc, name, setting.value)
    return on_set
cfg['connect.host'].on_change(_make_connection_callback('host'), autoremove=False)
cfg['connect.port'].on_change(_make_connection_callback('port'), autoremove=False)
cfg['connect.path'].on_change(_make_connection_callback('path'), autoremove=False)
cfg['connect.user'].on_change(_make_connection_callback('user'), autoremove=False)
cfg['connect.password'].on_change(_make_connection_callback('password'), autoremove=False)
cfg['connect.tls'].on_change(_make_connection_callback('tls'), autoremove=False)
cfg['connect.timeout'].on_change(_make_connection_callback('timeout'), autoremove=False)


def _set_bandwidth_unit(unit):
    convert.bandwidth.unit = unit.value

    TORRENT_COLUMNS['rate-up'].set_unit(convert.bandwidth.unit)
    TORRENT_COLUMNS['rate-down'].set_unit(convert.bandwidth.unit)
    TORRENT_COLUMNS['rate-limit-up'].set_unit(convert.bandwidth.unit)
    TORRENT_COLUMNS['rate-limit-down'].set_unit(convert.bandwidth.unit)

    PEER_COLUMNS['rate-up'].set_unit(convert.bandwidth.unit)
    PEER_COLUMNS['rate-down'].set_unit(convert.bandwidth.unit)
    PEER_COLUMNS['rate-est'].set_unit(convert.bandwidth.unit)

    srvapi.torrent.clearcache()
cfg['unit.bandwidth'].on_change(_set_bandwidth_unit)
_set_bandwidth_unit(cfg['unit.bandwidth'])  # Initially call TORRENT_COLUMNS[...].set_unit()

def _set_bandwidth_prefix(prefix):
    convert.bandwidth.prefix = prefix.value
    srvapi.torrent.clearcache()
cfg['unitprefix.bandwidth'].on_change(_set_bandwidth_prefix)


def _set_size_unit(unit):
    convert.size.unit = unit.value

    TORRENT_COLUMNS['size'].set_unit(convert.size.unit)
    TORRENT_COLUMNS['downloaded'].set_unit(convert.size.unit)
    TORRENT_COLUMNS['uploaded'].set_unit(convert.size.unit)
    TORRENT_COLUMNS['available'].set_unit(convert.size.unit)

    FILE_COLUMNS['size'].set_unit(convert.size.unit)
    FILE_COLUMNS['downloaded'].set_unit(convert.size.unit)

    srvapi.torrent.clearcache()
cfg['unit.size'].on_change(_set_size_unit)
_set_size_unit(cfg['unit.size'])  # Initially call TORRENT_COLUMNS[...].set_unit()

def _set_size_prefix(prefix):
    convert.size.prefix = prefix.value
    srvapi.torrent.clearcache()
cfg['unitprefix.size'].on_change(_set_size_prefix)
