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

from ..logging import make_logger
log = make_logger(__name__)


class CallbackDict(dict):
    """Mapping that runs a callback on every change"""
    # https://stackoverflow.com/a/5186698

    __slots__ = ["callback"]

    def __init__(self, callback, *args, **kwargs):
        self.callback = callback
        dict.__init__(self, *args, **kwargs)

    def _wrap(method):
        def wrapper(self, *args, **kwargs):
            result = method(self, *args, **kwargs)
            self.callback()
            return result
        return wrapper

    __delitem__ = _wrap(dict.__delitem__)
    __setitem__ = _wrap(dict.__setitem__)
    clear = _wrap(dict.clear)
    pop = _wrap(dict.pop)
    popitem = _wrap(dict.popitem)
    setdefault = _wrap(dict.setdefault)
    update =  _wrap(dict.update)


from collections import abc

def listify_args(args):
    """Make list from `args`

    If `args` is a string, use split(',') on it.  If `args` is any other
    iterable, recurse on each item and add the return values to the result.
    Otherwise make `args` a single item.

    All items are turned into strings and strip()ed.

    Despite the name, return a tuple.
    """
    if args is None:
        return []

    if isinstance(args, str):
        # args is a string of comma-separated list items
        args = tuple(str(arg).strip() for arg in args.split(','))
    elif isinstance(args, abc.Iterable):
        # args is an iterable of list items; each item may be a string of
        # comma-separated items
        args = tuple(a
                     for arg in args
                     for a in listify_args(arg))
    else:
        # args is something else
        args = tuple(str(args).strip())
    return tuple(arg for arg in args if arg)


def parseargs_tfilter(args):
    """Return TorrentFilter instance or None if `args` evaluates to False"""
    if args:
        from ..client import TorrentFilter
        return TorrentFilter(args)

def parseargs_sort(args):
    """Return TorrentSorter instance"""
    from ..client import TorrentSorter
    return TorrentSorter(listify_args(args))

def parseargs_tcolumns(args):
    """Return valid torrent list columns"""
    from ..columns.tlist import COLUMNS
    args = listify_args(args)
    for arg in args:
        if arg not in COLUMNS:
            raise ValueError('Unknown column: {}'.format(arg))
    return args

def parseargs_file_columns(args):
    from ..columns.flist import COLUMNS
    args = listify_args(args)
    for arg in args:
        if arg not in COLUMNS:
            raise ValueError('Unknown column: {}'.format(arg))
    return args


def log_msgs(logger, msgs, quiet=False):
    for msg in msgs:
        if isinstance(msg, str):
            if not quiet:
                logger.info(msg)
        elif isinstance(msg, Exception):
            logger.error(msg)
        else:
            raise RuntimeError('Invalid log message type ({}): {!r}'
                               .format(type(msg).__name__, msg))
