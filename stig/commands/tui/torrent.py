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

import functools
import os

from . import _mixin as mixin
from ... import objects
from ...completion import candidates
from ...utils.cliparser import Arg
from ..base import torrent as base
from ._common import make_tab_title_widget

from ...logging import make_logger  # isort:skip
log = make_logger(__name__)


class AddTorrentsCmd(base.AddTorrentsCmdbase,
                     mixin.polling_frenzy, mixin.make_request):
    provides = {'tui'}

    @staticmethod
    def make_path_absolute(path):
        # In the TUI, it makes more sense to use $HOME as the base directory for
        # relative paths instead of the current working directory.
        abspath = os.path.join(os.environ.get('HOME', '.'),
                               os.path.normpath(os.path.expanduser(path)))
        if os.path.exists(abspath):
            return abspath
        else:
            return path

    @classmethod
    def completion_candidates_posargs(cls, args):
        """Complete positional arguments"""
        return candidates.fs_path(args.curarg.before_cursor,
                                  base=os.environ.get('HOME', '.'),
                                  glob=r'*.torrent')


class TorrentDetailsCmd(base.TorrentDetailsCmdbase,
                        mixin.select_torrents, mixin.make_request):
    provides = {'tui'}

    async def display_details(self, torrent_id):
        make_titlew = functools.partial(make_tab_title_widget,
                                        attr_unfocused='tabs.torrentdetails.unfocused',
                                        attr_focused='tabs.torrentdetails.focused')

        from ...tui.views import TorrentDetailsWidget
        from ...tui.tuiobjects import keymap, tabs
        TorrentDetailsWidget_keymapped = keymap.wrap(TorrentDetailsWidget,
                                                     context='torrent')
        title_str = self.title if hasattr(self, 'title') else None
        detailsw = TorrentDetailsWidget_keymapped(torrent_id, title=title_str)
        tabid = tabs.load(make_titlew(detailsw.title), detailsw)
        tabs.set_info(command=self.command)

        def set_tab_title(text):
            # set_title() throws IndexError if the tab was removed, which may
            # have happened while TorrentDetailsWidget was waiting for a
            # response.
            try:
                tabs.set_title(make_titlew(text), position=tabid)
            except IndexError:
                pass
        detailsw.title_updater = set_tab_title


class ListTorrentsCmd(base.ListTorrentsCmdbase,
                      mixin.select_torrents,
                      mixin.create_list_widget):
    provides = {'tui'}

    def make_torrent_list(self, tfilter, sort, columns):
        from ...tui.views import TorrentListWidget
        self.create_list_widget(TorrentListWidget, theme_name='torrentlist',
                                tfilter=tfilter, sort=sort, columns=columns,
                                markable_items=True)


class TorrentMagnetURICmd(base.TorrentMagnetURICmdbase,
                          mixin.select_torrents):
    provides = {'tui'}

    def display_uris(self, uris):
        for uri in uris:
            self.info(uri)


class MoveTorrentsCmd(base.MoveTorrentsCmdbase,
                      mixin.polling_frenzy, mixin.make_request, mixin.select_torrents):
    provides = {'tui'}

    @classmethod
    async def completion_candidates_posargs(cls, args):
        """Complete positional arguments"""
        def dest_path_candidates(curarg):
            return candidates.fs_path(curarg.before_cursor,
                                      base=objects.cfg['srv.path.complete'],
                                      directories_only=True,
                                      expand_home_directory=False)

        curarg = args.curarg
        if len(args) >= 3:
            if args.curarg_index == 1:
                return await candidates.torrent_filter(curarg)
            elif args.curarg_index == 2:
                return dest_path_candidates(curarg)
        elif len(args) == 2:
            # Single argument may be a path or a filter
            filter_cands = await candidates.torrent_filter(curarg)
            path_cands = dest_path_candidates(curarg)
            return (path_cands,) + filter_cands


class RemoveTorrentsCmd(base.RemoveTorrentsCmdbase,
                        mixin.polling_frenzy, mixin.make_request, mixin.select_torrents,
                        mixin.ask_yes_no):
    provides = {'tui'}
    CONFIRMATION_TAB_TITLE = 'Removal Confirmation'

    async def show_list_of_hits(self, tfilter):
        cmd = 'tab --title %r ls --sort name %s' % (self.CONFIRMATION_TAB_TITLE, tfilter)
        await objects.cmdmgr.run_async(cmd)

    async def remove_list_of_hits(self):
        cmd = 'tab --close %r --focus left' % self.CONFIRMATION_TAB_TITLE
        await objects.cmdmgr.run_async(cmd)


class RenameCmd(base.RenameCmdbase,
                mixin.polling_frenzy, mixin.make_request, mixin.select_torrents, mixin.select_files):
    provides = {'tui'}

    @classmethod
    async def completion_candidates_posargs(cls, args):
        """Complete positional arguments"""
        # We don't care about options
        args = args.posargs()

        # If there is only one argument and it doesn't contain a path separator,
        # that means the user might want to rename the focused torrent, file or
        # directory.  In that case, the first argument is the destination and
        # the source is picked from the TUI.
        if len(args) == 2 and args.curarg_index == 1 and '/' not in args.curarg:
            source = cls._get_focused_item_source()
            if source is not None:
                log.debug('Getting destination candidates from TUI: %r', source)
                source_arg = Arg(source, curpos=len(source))
                tui_cands = await candidates.torrent_path(source_arg, only='auto')
                regular_cands = await candidates.torrent_path(args.curarg, only='any')
                return (tui_cands, regular_cands)

        # Any other arguments are handled identically in CLI and TUI
        log.debug('Not generating TUI-specific candidates')
        return await super().completion_candidates_posargs(args)

    @classmethod
    def _get_focused_item_source(cls):
        item_type = cls.get_focused_item_type()
        if item_type == 'torrent':
            data = cls.get_focused_item_data()
            source = 'id=%d' % (data['id'],)
            log.debug('  (focused torrent: %r)', source)
            return source

        elif item_type in ('file', 'directory'):
            data = cls.get_focused_item_data()
            # If there is no path separator in 'path-relative', that means focus
            # is on the torrent's name (or top-level directory)
            if '/' in data['path-relative']:
                focused_path = '/'.join(data['path-relative'].split('/')[1:])
                source = 'id=%d/%s' % (data['tid'], focused_path)
                log.debug('  (focused file/directory: %r)', source)
                return source


class StartTorrentsCmd(base.StartTorrentsCmdbase,
                       mixin.polling_frenzy, mixin.make_request, mixin.select_torrents):
    provides = {'tui'}


class StopTorrentsCmd(base.StopTorrentsCmdbase,
                      mixin.polling_frenzy, mixin.make_request, mixin.select_torrents):
    provides = {'tui'}


class VerifyTorrentsCmd(base.VerifyTorrentsCmdbase,
                        mixin.polling_frenzy, mixin.make_request, mixin.select_torrents):
    provides = {'tui'}
