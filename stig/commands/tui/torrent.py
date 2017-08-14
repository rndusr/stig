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

"""Torrent commands for the TUI"""

from ...logging import make_logger
log = make_logger(__name__)

from collections import abc
from functools import partial

from ..base import torrent as base
from . import mixin
from .. import (ExpectedResource, InitCommand)
from .utils import make_tab_title_widget


class AddTorrentsCmd(base.AddTorrentsCmdbase,
                     mixin.polling_frenzy, mixin.make_request):
    provides = {'tui'}


class AnnounceTorrentsCmd(base.AnnounceTorrentsCmdbase,
                          mixin.make_request, mixin.select_torrents):
    provides = {'tui'}


class ListTorrentsCmd(base.ListTorrentsCmdbase,
                      mixin.select_torrents, mixin.generate_tab_title):
    provides = {'tui'}
    tui = ExpectedResource
    srvapi = ExpectedResource

    async def make_tlist(self, tfilter, sort, columns):
        if 'marked' not in columns:
            columns.insert(0, 'marked')

        make_titlew = partial(make_tab_title_widget,
                              attr_unfocused='tabs.torrentlist.unfocused',
                              attr_focused='tabs.torrentlist.focused')

        title_str = await self.generate_tab_title(tfilter)

        from ...tui.views.torrentlist import TorrentListWidget
        tlistw = TorrentListWidget(self.srvapi, self.tui.keymap, tfilter=tfilter,
                                   sort=sort, columns=columns, title=title_str)
        tabid = self.tui.tabs.load(make_titlew(tlistw.title), tlistw)

        def set_tab_title(text, count):
            self.tui.tabs.set_title(make_titlew(text, count), position=tabid)
        tlistw.title_updater = set_tab_title

        return True


class ListFilesCmd(base.ListFilesCmdbase,
                   mixin.make_request, mixin.select_torrents, mixin.select_files,
                   mixin.generate_tab_title):
    provides = {'tui'}
    tui = ExpectedResource
    srvapi = ExpectedResource

    async def make_flist(self, tfilter, ffilter, columns):
        if 'marked' not in columns:
            columns.insert(0, 'marked')

        make_titlew = partial(make_tab_title_widget,
                              attr_unfocused='tabs.filelist.unfocused',
                              attr_focused='tabs.filelist.focused')

        title_str = await self.generate_tab_title(tfilter)

        from ...tui.views.filelist import FileListWidget
        flistw = FileListWidget(self.srvapi, self.tui.keymap,
                                tfilter=tfilter, ffilter=ffilter,
                                columns=columns, title=title_str)
        tabid = self.tui.tabs.load(make_titlew(flistw.title), flistw)

        def set_tab_title(text, count):
            self.tui.tabs.set_title(make_titlew(text, count), position=tabid)
        flistw.title_updater = set_tab_title

        return True


class ListPeersCmd(base.ListPeersCmdbase,
                   mixin.make_request, mixin.select_torrents, mixin.generate_tab_title):
    provides = {'tui'}
    tui = ExpectedResource
    srvapi = ExpectedResource

    async def make_plist(self, tfilter, pfilter, sort, columns):
        make_titlew = partial(make_tab_title_widget,
                              attr_unfocused='tabs.peerlist.unfocused',
                              attr_focused='tabs.peerlist.focused')

        title_str = await self.generate_tab_title(tfilter)

        from ...tui.views.peerlist import PeerListWidget
        plistw = PeerListWidget(self.srvapi, self.tui.keymap,
                                tfilter=tfilter, pfilter=pfilter,
                                sort=sort, columns=columns, title=title_str)
        tabid = self.tui.tabs.load(make_titlew(plistw.title), plistw)

        def set_tab_title(text, count):
            self.tui.tabs.set_title(make_titlew(text, count), position=tabid)
        plistw.title_updater = set_tab_title

        return True


class ListTrackersCmd(base.ListTrackersCmdbase,
                      mixin.make_request, mixin.select_torrents, mixin.generate_tab_title):
    provides = {'tui'}
    tui = ExpectedResource
    srvapi = ExpectedResource

    async def make_trklist(self, torfilter, trkfilter, sort, columns):
        make_titlew = partial(make_tab_title_widget,
                              attr_unfocused='tabs.trackerlist.unfocused',
                              attr_focused='tabs.trackerlist.focused')

        title_str = await self.generate_tab_title(torfilter)

        from ...tui.views.trackerlist import TrackerListWidget
        trklistw = TrackerListWidget(self.srvapi, self.tui.keymap,
                                     torfilter=torfilter, trkfilter=trkfilter,
                                     sort=sort, columns=columns, title=title_str)
        tabid = self.tui.tabs.load(make_titlew(trklistw.title), trklistw)

        def set_tab_title(text, count):
            self.tui.tabs.set_title(make_titlew(text, count), position=tabid)
        trklistw.title_updater = set_tab_title

        return True


class TorrentSummaryCmd(base.TorrentSummaryCmdbase,
                        mixin.select_torrents, mixin.make_request, mixin.generate_tab_title):
    provides = {'tui'}
    tui = ExpectedResource

    async def display_summary(self, tfilter):
        tid = await self.get_torrent_id(tfilter)
        if tid is None:
            return False

        make_titlew = partial(make_tab_title_widget,
                              attr_unfocused='tabs.torrentsummary.unfocused',
                              attr_focused='tabs.torrentsummary.focused')

        title_str = await self.generate_tab_title(tfilter)
        from ...tui.views.summary import TorrentSummaryWidget
        TorrentSummaryWidget_keymapped = self.tui.keymap.wrap(TorrentSummaryWidget,
                                                              context='torrent')
        summaryw = TorrentSummaryWidget_keymapped(self.srvapi, tid, title=title_str)
        tabid = self.tui.tabs.load(make_titlew(summaryw.title), summaryw)

        def set_tab_title(text):
            self.tui.tabs.set_title(make_titlew(text), position=tabid)
        summaryw.title_updater = set_tab_title

        return True


class SortCmd(metaclass=InitCommand):
    name = 'sort'
    aliases = ()
    provides = {'tui'}
    category = 'torrent'
    description = "Sort lists of torrents/peers/trackers/etc"
    usage = ('sort [<OPTIONS>] [<ORDER> <ORDER> <ORDER> ...]',)
    examples = ('sort tracker status !rate-down',
                'sort --add eta')
    argspecs = (
        {'names': ('ORDER',), 'nargs': '*',
         'description': 'How to sort list items (see SORT ORDERS section)'},

        {'names': ('--add', '-a'), 'action': 'store_true',
         'description': 'Append ORDERs to current list of sort orders instead of replacing it'},

        {'names': ('--reset', '-r'), 'action': 'store_true',
         'description': 'Go back to sort order that was used when list was created'},

        {'names': ('--none', '-n'), 'action': 'store_true',
         'description': 'Remove all sort orders from the list'},
    )

    def _list_sort_orders(title, sortercls):
        return (title,) + \
            tuple('\t{}\t - \t{}'.format(', '.join((sname,) + s.aliases), s.description)
                  for sname,s in sorted(sortercls.SORTSPECS.items()))

    from ...client.sorters.tsorter import TorrentSorter
    from ...client.sorters.psorter import TorrentPeerSorter
    from ...client.sorters.trksorter import TorrentTrackerSorter
    more_sections = {
        'SORT ORDERS': _list_sort_orders('TORRENT LISTS', TorrentSorter) + \
                       ('',) + \
                       _list_sort_orders('PEER LISTS', TorrentPeerSorter) + \
                       ('',) + \
                       _list_sort_orders('TRACKER LISTS', TorrentTrackerSorter)
    }

    tui = ExpectedResource

    async def run(self, add, reset, none, ORDER):
        current_tab = self.tui.tabs.focus

        if reset:
            current_tab.sort = 'RESET'

        if none:
            current_tab.sort = None

        if ORDER:
            # Find appropriate sorter class for focused list
            from ...tui.views.torrentlist import TorrentListWidget
            from ...tui.views.peerlist import PeerListWidget
            from ...tui.views.trackerlist import TrackerListWidget
            if isinstance(current_tab, TorrentListWidget):
                sortcls = self.TorrentSorter
            elif isinstance(current_tab, PeerListWidget):
                sortcls = self.TorrentPeerSorter
            elif isinstance(current_tab, TrackerListWidget):
                sortcls = self.TorrentTrackerSorter
            else:
                log.error('Current tab does not contain a torrent, peer or tracker list.')
                return False

            try:
                new_sort = sortcls(ORDER)
            except ValueError as e:
                log.error(e)
                return False

            if add and current_tab.sort is not None:
                current_tab.sort += new_sort
            else:
                current_tab.sort = new_sort
            return True


class MoveTorrentsCmd(base.MoveTorrentsCmdbase,
                      mixin.polling_frenzy, mixin.make_request, mixin.select_torrents):
    provides = {'tui'}


class PriorityCmd(base.PriorityCmdbase,
                  mixin.polling_frenzy, mixin.make_request, mixin.select_torrents, mixin.select_files):
    provides = {'tui'}


class RateLimitCmd(base.RateLimitCmdbase,
                   mixin.make_request, mixin.select_torrents, mixin.polling_frenzy):
    provides = {'tui'}


class RemoveTorrentsCmd(base.RemoveTorrentsCmdbase,
                        mixin.polling_frenzy, mixin.make_request, mixin.select_torrents):
    provides = {'tui'}


class StartTorrentsCmd(base.StartTorrentsCmdbase,
                       mixin.polling_frenzy, mixin.make_request, mixin.select_torrents):
    provides = {'tui'}


class StopTorrentsCmd(base.StopTorrentsCmdbase,
                      mixin.polling_frenzy, mixin.make_request, mixin.select_torrents):
    provides = {'tui'}


class VerifyTorrentsCmd(base.VerifyTorrentsCmdbase,
                        mixin.make_request, mixin.select_torrents):
    provides = {'tui'}
