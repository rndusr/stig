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

from ...main import cfg
from .tlist_columns import TUICOLUMNS as TCOLUMNS
from .flist_columns import TUICOLUMNS as FCOLUMNS
from .plist_columns import TUICOLUMNS as PCOLUMNS


def _set_bandwidth_unit(unit):
    u = {'bit': 'b', 'byte': 'B'}[unit.value]
    TCOLUMNS['rate-up'].set_unit(u)
    TCOLUMNS['rate-down'].set_unit(u)
    TCOLUMNS['rate-limit-up'].set_unit(u)
    TCOLUMNS['rate-limit-down'].set_unit(u)

    PCOLUMNS['rate-up'].set_unit(u)
    PCOLUMNS['rate-down'].set_unit(u)
    PCOLUMNS['rate-est'].set_unit(u)
cfg['unit.bandwidth'].on_change(_set_bandwidth_unit)


def _set_size_unit(unit):
    u = {'bit': 'b', 'byte': 'B'}[unit.value]
    TCOLUMNS['size'].set_unit(u)
    TCOLUMNS['downloaded'].set_unit(u)
    TCOLUMNS['uploaded'].set_unit(u)
    TCOLUMNS['available'].set_unit(u)

    FCOLUMNS['size'].set_unit(u)
    FCOLUMNS['downloaded'].set_unit(u)
cfg['unit.size'].on_change(_set_size_unit)
