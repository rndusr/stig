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

from . import _mixin as mixin
from ..base import file as base


class ListFilesCmd(base.ListFilesCmdbase,
                   mixin.make_request,
                   mixin.select_torrents, mixin.select_files,
                   mixin.create_list_widget):
    provides = {'tui'}

    def make_file_list(self, tfilter, ffilter, columns):
        from ...tui.views import FileListWidget
        self.create_list_widget(FileListWidget, theme_name='filelist',
                                tfilter=tfilter, ffilter=ffilter,
                                columns=columns,
                                markable_items=True)


class PriorityCmd(base.PriorityCmdbase,
                  mixin.polling_frenzy, mixin.make_request, mixin.select_torrents, mixin.select_files):
    provides = {'tui'}

class FOpenCmd(base.FOpenCmdbase, mixin.make_request, mixin.select_torrents, mixin.select_files):
    provides = {'tui'}
    # When files are selected in the tui, the two first arguments, the torrent
    # and the file(s) need to be filled in.  That is, `fopen mpv` should mean
    # `fopen torrent file mpv`

    async def run(self, quiet, COMMAND, TORRENT_FILTER, FILE_FILTER, OPTS):
        await base.FOpenCmdbase.run(self, quiet, TORRENT_FILTER=COMMAND, FILE_FILTER=FILE_FILTER, COMMAND=TORRENT_FILTER, OPTS=OPTS)
