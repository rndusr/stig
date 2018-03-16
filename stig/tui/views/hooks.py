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

from ...main import localcfg
from .torrent import TUICOLUMNS as TCOLUMNS
from .file import TUICOLUMNS as FCOLUMNS
from .peer import TUICOLUMNS as PCOLUMNS


_BANDWIDTH_COLUMNS = (TCOLUMNS['rate-up'], TCOLUMNS['rate-down'],
                      TCOLUMNS['limit-rate-up'], TCOLUMNS['limit-rate-down'],
                      PCOLUMNS['rate-up'], PCOLUMNS['rate-down'], PCOLUMNS['rate-est'])
def _set_bandwidth_unit(settings, name, value):
    unit_short = {'bit': 'b', 'byte': 'B'}.get(value, value)
    unit_short += '/s'
    for column in _BANDWIDTH_COLUMNS:
        column.set_header(right=unit_short)
localcfg.on_change(_set_bandwidth_unit, name='unit.bandwidth')


_SIZE_COLUMNS = (TCOLUMNS['size'], TCOLUMNS['downloaded'],
                 TCOLUMNS['uploaded'], TCOLUMNS['available'],
                 FCOLUMNS['size'], FCOLUMNS['downloaded'])
def _set_size_unit(settings, name, value):
    unit_short = {'bit': 'b', 'byte': 'B'}.get(value, value)
    for column in _SIZE_COLUMNS:
        column.set_header(right=unit_short)
localcfg.on_change(_set_size_unit, name='unit.size')
