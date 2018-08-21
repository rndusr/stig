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
from ._table import print_table

from itertools import chain


class RcCmd(base.RcCmdbase):
    provides = {'cli'}

class ResetCmd(base.ResetCmdbase):
    provides = {'cli'}


class SetCmd(base.SetCmdbase,
             mixin.only_supported_columns):
    provides = {'cli'}

    def make_setting_list(self, sort, columns):
        from ...views.setting import COLUMNS as SETTING_COLUMNS
        from ...main import (localcfg, remotecfg)

        # Remove columns that aren't supported by CLI interface (e.g. 'marked')
        columns = self.only_supported_columns(columns, SETTING_COLUMNS)

        settings = sort.apply(
            chain(({'id': k,
                    'value': v,
                    'default': localcfg.default(k),
                    'description': localcfg.description(k)}
                   for k,v in localcfg.items()),
                  ({'id': 'srv.'+k,
                    'value': v,
                    'default': '',
                    'description': remotecfg.description(k)}
                   for k,v in remotecfg.items()))
        )

        print_table(settings, columns, SETTING_COLUMNS)


class RateLimitCmd(base.RateLimitCmdbase,
                   mixin.make_request, mixin.select_torrents):
    provides = {'cli'}

    async def _set_limits(self, TORRENT_FILTER, directions, limit, adjust=False, quiet=False):
        if len(TORRENT_FILTER) == 0 or TORRENT_FILTER == ['global']:
            await self._set_global_limits(directions, limit,
                                          adjust=adjust, quiet=quiet)
        else:
            await self._set_individual_limits(TORRENT_FILTER, directions, limit,
                                              adjust=adjust, quiet=quiet)

    async def _show_limits(self, TORRENT_FILTER, directions):
        if not TORRENT_FILTER or TORRENT_FILTER == ['global']:
            await self._show_global_limits(directions)
        else:
            await self._show_individual_limits(TORRENT_FILTER, directions)

    def _output(self, msg):
        print(msg)
