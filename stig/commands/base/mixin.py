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

"""Mixin classes that are common between TUI and CLI commands"""

from ...logging import make_logger
log = make_logger(__name__)


from .. import utils


class get_torrent_sorter():
    def get_torrent_sorter(self, args):
        """Return TorrentSorter instance or None

        If `args` evaluates to True, it is passed to TorrentSorter and the
        result is returned.

        If `args` evaluates to False, None is returned.
        """
        if args:
            from ...client import TorrentSorter
            return TorrentSorter(utils.listify_args(args))


class get_tlist_columns():
    def get_tlist_columns(self, args):
        """Check if each item in iterable `args` is a valid torrent list column

        Raise ValueError or return the same iterable.
        """
        from ...columns.tlist import COLUMNS
        args = utils.listify_args(args)
        for arg in args:
            if arg not in COLUMNS:
                raise ValueError('Unknown column name: {}'.format(arg))
        return args


class get_flist_columns():
    def get_flist_columns(self, args):
        """Check if each item in iterable `args` is a valid file list column

        Raise ValueError or return the same iterable.
        """
        from ...columns.flist import COLUMNS
        args = utils.listify_args(args)
        for arg in args:
            if arg not in COLUMNS:
                raise ValueError('Unknown column name: {}'.format(arg))
        return args
