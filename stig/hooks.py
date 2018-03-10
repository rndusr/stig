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
from .views.torrent import COLUMNS as TORRENT_COLUMNS
from .views.file import COLUMNS as FILE_COLUMNS
from .views.peer import COLUMNS as PEER_COLUMNS


def _make_connection_callback(attr):
    def on_set(settings, name, value):
        log.debug('Setting rpc.%s=%r', attr, value)
        setattr(srvapi.rpc, attr, value)
    return on_set
cfg.on_change(_make_connection_callback('host'),     name='connect.host',     autoremove=False)
cfg.on_change(_make_connection_callback('port'),     name='connect.port',     autoremove=False)
cfg.on_change(_make_connection_callback('path'),     name='connect.path',     autoremove=False)
cfg.on_change(_make_connection_callback('user'),     name='connect.user',     autoremove=False)
cfg.on_change(_make_connection_callback('password'), name='connect.password', autoremove=False)
cfg.on_change(_make_connection_callback('tls'),      name='connect.tls',      autoremove=False)
cfg.on_change(_make_connection_callback('timeout'),  name='connect.timeout',  autoremove=False)


_BANDWIDTH_COLUMNS = (TORRENT_COLUMNS['rate-up'], TORRENT_COLUMNS['rate-down'],
                      TORRENT_COLUMNS['limit-rate-up'], TORRENT_COLUMNS['limit-rate-down'],
                      PEER_COLUMNS['rate-up'], PEER_COLUMNS['rate-down'], PEER_COLUMNS['rate-est'])
def _set_bandwidth_unit(settings, name, value):
    convert.bandwidth.unit = value
    unit_short = convert.bandwidth.unit
    for column in _BANDWIDTH_COLUMNS:
        column.set_unit(unit_short)
        column.clearcache()
    srvapi.torrent.clearcache()
    srvapi.poll()
cfg.on_change(_set_bandwidth_unit, name='unit.bandwidth')
_set_bandwidth_unit(cfg, name='unit.bandwidth', value=cfg['unit.bandwidth'])  # Init columns' units

def _set_bandwidth_prefix(settings, name, value):
    convert.bandwidth.prefix = value
    for column in _BANDWIDTH_COLUMNS:
        column.clearcache()
    srvapi.torrent.clearcache()
    srvapi.poll()
cfg.on_change(_set_bandwidth_prefix, name='unitprefix.bandwidth')


_SIZE_COLUMNS = (TORRENT_COLUMNS['size'], TORRENT_COLUMNS['downloaded'],
                 TORRENT_COLUMNS['uploaded'], TORRENT_COLUMNS['available'],
                 FILE_COLUMNS['size'], FILE_COLUMNS['downloaded'])
def _set_size_unit(settings, name, value):
    convert.size.unit = value
    unit_short = convert.size.unit
    for column in _SIZE_COLUMNS:
        column.set_unit(unit_short)
        column.clearcache()
    srvapi.torrent.clearcache()
    srvapi.poll()
cfg.on_change(_set_size_unit, name='unit.size')
_set_size_unit(cfg, name='unit.size', value=cfg['unit.size'])  # Init columns' units

def _set_size_prefix(settings, name, value):
    convert.size.prefix = value
    for column in _SIZE_COLUMNS:
        column.clearcache()
    srvapi.torrent.clearcache()
    srvapi.poll()
cfg.on_change(_set_size_prefix, name='unitprefix.size')
