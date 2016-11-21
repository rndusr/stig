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

from ...logging import make_logger
log = make_logger(__name__)

from ...main import cfg
from . import tlist_columns as columns


def _set_bandwidth_unit(unit):
    u = {'bit': 'b', 'byte': 'B'}[unit.value]
    columns.RateUp.set_unit(u)
    columns.RateDown.set_unit(u)
cfg['unit.bandwidth'].on_change(_set_bandwidth_unit)


def _set_size_unit(unit):
    u = {'bit': 'b', 'byte': 'B'}[unit.value]
    columns.Size.set_unit(u)
    columns.Downloaded.set_unit(u)
    columns.Uploaded.set_unit(u)
cfg['unit.size'].on_change(_set_size_unit)
