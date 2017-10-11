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

from ..base import config as base
from . import _mixin as mixin

class RcCmd(base.RcCmdbase):
    provides = {'cli'}

class ResetCmd(base.ResetCmdbase):
    provides = {'cli'}

class SetCmd(base.SetCmdbase):
    provides = {'cli'}

class RateLimitCmd(base.RateLimitCmdbase,
                   mixin.make_request, mixin.select_torrents):
    provides = {'cli'}

    async def _set_limits(self, TORRENT_FILTER, directions, LIMIT):
        if len(TORRENT_FILTER) == 0 or TORRENT_FILTER == ['global']:
            return await self._set_global_limit(directions, LIMIT)
        else:
            return await self._set_individual_limit(TORRENT_FILTER, directions, LIMIT)
