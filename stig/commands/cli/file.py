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

from ..base import file as base
from . import _mixin as mixin
from .. import (CmdError, ExpectedResource)
from ._table import (print_table, TERMSIZE)

import os


class ListFilesCmd(base.ListFilesCmdbase,
                   mixin.make_request, mixin.select_torrents, mixin.select_files,
                   mixin.only_supported_columns):
    provides = {'cli'}
    srvapi = ExpectedResource

    async def make_file_list(self, tfilter, ffilter, columns):
        response = await self.make_request(
            self.srvapi.torrent.torrents(tfilter, keys=('name', 'files')),
            quiet=True)
        torrents = response.torrents

        if len(torrents) < 1:
            raise CmdError()

        filelist = []
        for torrent in sorted(torrents, key=lambda t: t['name'].lower()):
            files, filtered_count = self._flatten_tree(torrent['files'], ffilter)
            filelist.extend(files)

        if filelist:
            from ...views.file import COLUMNS as FILE_COLUMNS
            # Remove columns that aren't supported by CLI interface (e.g. 'marked')
            columns = self.only_supported_columns(columns, FILE_COLUMNS)
            print_table(filelist, columns, FILE_COLUMNS)
        else:
            if str(tfilter) != 'all':
                raise CmdError('No matching files in %s torrents: %s' % (tfilter, ffilter))
            else:
                raise CmdError('No matching files: %s' % (ffilter))

    def _flatten_tree(self, files, ffilter=None, _indent_level=0):
        """
        Return list of rows for `print_table`

        `files` must be a nested mapping tree (i.e. TorrentFileTree).
        `ffilter` must be a TorrentFileFilter instance or None.
        """
        if TERMSIZE.columns is None:
            def indent(node):
                node['name'] = node['path-absolute']
        else:
            def indent(node):
                node['name'] = '%s%s' % ('  '*(_indent_level), node['name'])

        from ...views.file import TorrentFileDirectory
        flist = []
        filtered_count = 0
        for key,value in sorted(files.items(), key=lambda pair: pair[0].lower()):
            if value.nodetype == 'leaf':
                if ffilter is None or ffilter.match(value):
                    filenode = dict(value)  # Copy original TorrentFile
                    indent(filenode)
                    flist.append(filenode)
                else:
                    filtered_count += 1

            elif value.nodetype == 'parent':
                sub_flist, sub_filtered_count = self._flatten_tree(value, ffilter, _indent_level+1)
                if TERMSIZE.columns is not None:
                    dirnode = TorrentFileDirectory(key, value, sub_filtered_count)
                    indent(dirnode)
                    flist.append(dirnode)
                flist.extend(sub_flist)

        return flist, filtered_count


class PriorityCmd(base.PriorityCmdbase,
                  mixin.make_request, mixin.select_torrents, mixin.select_files):
    provides = {'cli'}
