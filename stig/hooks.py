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


_BANDWIDTH_COLUMNS = (TORRENT_COLUMNS['rate-up'], TORRENT_COLUMNS['rate-down'],
                      TORRENT_COLUMNS['rate-limit-up'], TORRENT_COLUMNS['rate-limit-down'],
                      PEER_COLUMNS['rate-up'], PEER_COLUMNS['rate-down'], PEER_COLUMNS['rate-est'])
def _set_bandwidth_unit(unit):
    convert.bandwidth.unit = unit.value
    unit_short = convert.bandwidth.unit
    for column in _BANDWIDTH_COLUMNS:
        column.set_unit(unit_short)
        column.clearcache()
    srvapi.torrent.clearcache()
    srvapi.poll()
cfg['unit.bandwidth'].on_change(_set_bandwidth_unit)
_set_bandwidth_unit(cfg['unit.bandwidth'])  # Init columns' units

def _set_bandwidth_prefix(prefix):
    convert.bandwidth.prefix = prefix.value
    for column in _BANDWIDTH_COLUMNS:
        column.clearcache()
    srvapi.torrent.clearcache()
    srvapi.poll()
cfg['unitprefix.bandwidth'].on_change(_set_bandwidth_prefix)


_SIZE_COLUMNS = (TORRENT_COLUMNS['size'], TORRENT_COLUMNS['downloaded'],
                 TORRENT_COLUMNS['uploaded'], TORRENT_COLUMNS['available'],
                 FILE_COLUMNS['size'], FILE_COLUMNS['downloaded'])
def _set_size_unit(unit):
    convert.size.unit = unit.value
    unit_short = convert.size.unit
    for column in _SIZE_COLUMNS:
        column.set_unit(unit_short)
        column.clearcache()
    srvapi.torrent.clearcache()
    srvapi.poll()
cfg['unit.size'].on_change(_set_size_unit)
_set_size_unit(cfg['unit.size'])  # Init columns' units

def _set_size_prefix(prefix):
    convert.size.prefix = prefix.value
    for column in _SIZE_COLUMNS:
        column.clearcache()
    srvapi.torrent.clearcache()
    srvapi.poll()
cfg['unitprefix.size'].on_change(_set_size_prefix)
