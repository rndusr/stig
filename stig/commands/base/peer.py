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

from .. import (InitCommand, CmdError, ExpectedResource)
from . import _mixin as mixin
from ._common import (make_X_FILTER_spec, make_COLUMNS_doc,
                      make_SORT_ORDERS_doc, make_SCRIPTING_doc)

import asyncio
from collections import abc


class ListPeersCmdbase(mixin.get_peer_sorter, mixin.get_peer_columns,
                       mixin.get_peer_filter, metaclass=InitCommand):
    name = 'peerlist'
    aliases = ('pls', 'lsp')
    provides = set()
    category = 'peer'
    description = 'List connected peers of torrent(s)'
    usage = ('peerlist [<OPTIONS>]',
             'peerlist [<OPTIONS>] <TORRENT FILTER>',
             'peerlist [<OPTIONS>] <TORRENT FILTER> <PEER FILTER>')
    examples = ('peerlist',
                'peerlist downloading',
                'peerlist some_torrent host=127.0.0.1')
    argspecs = (
        make_X_FILTER_spec('TORRENT', or_focused=True, nargs='?'),
        make_X_FILTER_spec('PEER', nargs='?'),

        { 'names': ('--sort', '-s'),
          'default_description': "current value of 'sort.peers' setting",
          'description': ('Comma-separated list of sort orders '
                          "(see SORT ORDERS section)") },

        { 'names': ('--columns', '-c'),
          'default_description': "current value of 'columns.peers' setting",
          'description': ('Comma-separated list of column names '
                          "(see COLUMNS section)") },
    )

    from ...views.peer import COLUMNS
    from ...client.sorters.peer import TorrentPeerSorter
    more_sections = {
        'COLUMNS': make_COLUMNS_doc(COLUMNS, '--columns', 'columns.peers', append=(
            '',
            'The "torrent" column is added automatically if multiple '
            'torrents could be listed potentially.')),
        'SORT ORDERS': make_SORT_ORDERS_doc(TorrentPeerSorter, '--sort', 'sort.peers'),
        'SCRIPTING': make_SCRIPTING_doc(name),
    }

    cfg = ExpectedResource

    async def run(self, TORRENT_FILTER, PEER_FILTER, sort, columns):
        columns = self.cfg['columns.peers'] if columns is None else columns
        sort = self.cfg['sort.peers'] if sort is None else sort
        try:
            tfilter = self.select_torrents(TORRENT_FILTER,
                                           allow_no_filter=True,
                                           discover_torrent=True)
            pfilter = self.get_peer_filter(PEER_FILTER)
            sort    = self.get_peer_sorter(sort)
            columns = self.get_peer_columns(columns)
        except ValueError as e:
            raise CmdError(e)

        # Unless we're listing peers of exactly one torrent, specified by its
        # ID, automatically add the 'torrent' column.
        if 'torrent' not in columns and \
           (not isinstance(tfilter, abc.Sequence) or len(tfilter) != 1):
            columns += ('torrent',)

        log.debug('Listing %s peers of %s torrents', pfilter, tfilter)

        if asyncio.iscoroutinefunction(self.make_peer_list):
            await self.make_peer_list(tfilter, pfilter, sort, columns)
        else:
            self.make_peer_list(tfilter, pfilter, sort, columns)
