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

"""Getters for tab completion candidates"""

from ..logging import make_logger
log = make_logger(__name__)


from .. import objects
from ..utils import usertypes
from ..completion import (Candidates, Candidate)
from . import _utils

import itertools
import os
import re
import functools
from collections import abc


def for_args(args):
    """Get completion candidates for command line `args`"""
    cmdcls = objects.cmdmgr.get_cmdcls(args[0])
    if cmdcls is not None:
        log.debug('Getting candidates for args: %r', args)
        return cmdcls.completion_candidates(args)


@functools.lru_cache(maxsize=None)
def commands():
    """Names of commands"""
    cands = (Candidate(cmdcls.name,
                       in_parens='%s' % (', '.join(cmdcls.aliases),),
                       Description=cmdcls.description)
             for cmdcls in objects.cmdmgr.active_commands)
    return Candidates(cands, label='Commands')


@functools.lru_cache(maxsize=None)
def help_topics():
    """All known help topics"""
    cats = []
    cats.append(Candidates(
        (Candidate(topic, Description=objects.helpmgr.MAIN_TOPICS[topic])
         for topic in objects.helpmgr.MAIN_TOPICS),
        label='Main Topics'))
    cats.append(commands())
    cats.append(Candidates(
        (Candidate(topic, Description=objects.localcfg.description(topic))
         for topic in objects.localcfg),
        label='Local Settings'))
    cats.append(Candidates(
        (Candidate('srv.' + topic, Description=objects.remotecfg.description(topic))
         for topic in objects.remotecfg),
        label='Remote Settings'))
    return cats


@functools.lru_cache(maxsize=None)
def setting_names():
    """Names of settings"""
    local_cands = (Candidate(name,
                             Description=objects.localcfg.description(name),
                             Default=str(objects.localcfg.default(name)))
                   for name in objects.localcfg)
    remote_cands = (Candidate('srv.' + name,
                              Description=objects.remotecfg.description(name),
                              Default=str(objects.remotecfg.default(name)))
                    for name in objects.remotecfg)
    return Candidates(itertools.chain(local_cands, remote_cands),
                      label='Settings')


def setting_values(args):
    """
    Values of settings

    `args` must be a `stig.utils.cliparser.Args` instance in which the first
    argument is the name of a setting.
    """
    setting = args[0]

    if setting in objects.localcfg:
        value = objects.localcfg[setting]
    elif setting.startswith('srv.') and setting[4:] in objects.remotecfg:
        value = objects.remotecfg[setting[4:]]
    else:
        return

    # Some settings accept multiple values, others only one
    focus_on_first_value = args.curarg_index == 1

    log.debug('Setting %r is a %s: %r', setting, type(value).__name__, value)
    # Get candidates depending on what kind of setting it is (bool, option, etc)
    if isinstance(value, usertypes.Option) and focus_on_first_value:
        aliases = value.aliases_inverse
        cands = (Candidate(opt, in_parens=', '.join(aliases.get(opt, '')))
                 for opt in value.options)
        return Candidates(cands, label='%s options' % (setting,))
    elif isinstance(value, usertypes.Tuple):
        aliases = value.aliases_inverse
        cands = (Candidate(opt, in_parens=', '.join(aliases.get(opt, '')))
                 for opt in value.options)
        return Candidates(cands, label='%s options' % (setting,),
                          curarg_seps=(value.sep.strip(),))
    elif isinstance(value, usertypes.Bool) and focus_on_first_value:
        options = (val
                   for vals in zip(value.truths, value.falsities)
                   for val in vals)
        return Candidates(options, label='%s options' % (setting,))
    elif isinstance(value, usertypes.Path):
        return fs_path(args.curarg.before_cursor,
                       base=value.base_path,
                       directories_only=os.path.isdir(value))


def sort_orders(clsname):
    """
    Names of sort orders

    `clsname` must be the name of a SorterBase derivative.
    """
    cls = _utils.get_sorter_cls(clsname)
    cands = (Candidate(name,
                       in_parens=', '.join(spec.aliases),
                       Description=spec.description)
             for name,spec in cls.SORTSPECS.items())
    return Candidates(cands,
                      curarg_seps=(objects.localcfg['sort.torrents'].sep.strip(),),
                      label=_utils.sorters_labels[clsname])


def column_names(list_type):
    """
    Columns names for a certain type of list

    When `list_type` is appended to "columns.", it must resolve to a proper
    setting.
    """
    setting = objects.localcfg['columns.%s' % list_type]
    cands = (Candidate(colname,
                       in_parens=', '.join(setting.aliases_inverse.get(colname, '')))
             for colname in setting.options)
    return Candidates(cands,
                      curarg_seps=(setting.sep.strip(),),
                      label=_utils.columns_labels[list_type])


def tab_titles():
    """Titles (strings) of TUI tabs"""
    from ..tui.tuiobjects import tabs
    return Candidates((widget.original_widget.text
                       for widget in tabs.titles), label='Tab Titles')


def keybinding_contexts():
    """Arguments for the '--context' option of the 'bind' command"""
    from ..tui.tuiobjects import keymap
    return Candidates(keymap.contexts, label='Keybinding Contexts')


def fs_path(path, base='.', directories_only=False, glob=None, regex=None):
    """
    File system path entries

    path: Path to get entries from
    base: Absolute path that is prepended to `path` if `path` is not absolute
    directories_only: Whether to include only directories
    glob: Unix shell pattern
    regex: Regular expression that is matched against each name in `path`
    """
    log.debug('Getting path candidates for %r', path)
    if path.startswith('~') and os.sep not in path:
        # Complete home dirs in "~<user>" style
        import pwd
        users = pwd.getpwall()
        cands = ('~%s' % (user.pw_name,) for user in users)
        label = 'Home directories'
    else:
        include_hidden = os.path.basename(path).startswith('.')
        dirpath = os.path.expanduser(path)
        if not os.path.isabs(dirpath):
            dirpath = os.path.join(base, dirpath)
        dirpath = os.path.dirname(dirpath)
        try:
            itr = os.scandir(dirpath)
        except (FileNotFoundError, NotADirectoryError, PermissionError):
            cands = ()
            label = 'No matches'
        else:
            from fnmatch import fnmatch
            cands = (entry.name for entry in itr
                     if ((include_hidden or not entry.name.startswith('.')) and
                         (not directories_only or entry.is_dir()) and
                         (regex is None or entry.is_dir() or re.search(regex, entry.name)) and
                         (glob is None or entry.is_dir() or fnmatch(entry.name, glob))))
            if directories_only:
                label = 'Directories in %s' % (dirpath,)
            else:
                label = '%s' % (dirpath,)
            if glob:
                label += '/%s' % (glob,)
    return Candidates(cands, label=label, curarg_seps=('/',))


async def torrent_path(curarg, only='auto'):
    """
    If `curarg` is a path to a file or directory in a torrent ("<TORRENT
    FILTER>/<PATH>"), return one `Candidates` object for each matching torrent
    that has a matching path.  Otherwise, simply pass `curarg` to
    `torrent_filter` and return the result.

    `only` must be "files", "directories", "any" or "auto".  If `only` is
    "auto", candidates are taken from the parent directory; if `curarg` points
    to a file, only files are returned, if `curarg` points to a directory, only
    directories are returned.
    """
    parts = curarg.before_cursor.separate(('/',), include_seps=False)
    if len(parts) < 2:
        # User is still writing the torrent filter part
        log.debug('Passing %r to torrent_filter()', parts[0])
        # If the command line looks like 'ls comment=|/some/path' ('|' is the
        # cursor), '/' must be an argument separator to inform the completer
        # that '/some/path' is not the part we are completing.
        cats = await torrent_filter(parts[0])
        for cands in cats:
            cands.curarg_seps += ('/',)
        return cats

    def level_up(path):
        # Remove all empty parts from the right
        while len(path) > 1 and path[-1] == '':
            path = path[:-1]
        # Remove last part from the right
        return path[:-1] if path else path

    def get_cands(torrent, path, only):
        subtree = _utils.find_subtree(torrent, path)

        if subtree is not None:
            path_points_to_file = subtree.nodetype == 'leaf'
            if path_points_to_file:
                subtree = _utils.find_subtree(torrent, level_up(path))

            if only == 'files':
                cands = _utils.find_files(subtree)
                return Candidates(cands, curarg_seps=('/',), label='Files in %s' % (subtree.path,))

            elif only == 'directories':
                cands = _utils.find_dirs(subtree)
                return Candidates(cands, curarg_seps=('/',), label='Directories in %s' % (subtree.path,))

            elif only == 'any':
                return Candidates(subtree, curarg_seps=('/',), label=subtree.path)

            elif only == 'auto':
                if path_points_to_file:
                    return get_cands(torrent, level_up(path), 'files')
                else:
                    return get_cands(torrent, level_up(path), 'directories')

            else:
                raise TypeError('Invalid value for argument "only": %r' % (only,))

    tfilter = parts[0]
    path = parts[1:]
    log.debug('Completing files or directories in %r torrents: %r', tfilter, path)
    response = await objects.srvapi.torrent.torrents(tfilter, keys=('files',), from_cache=True)
    if response.success:
        return (get_cands(torrent, path, only)
                for torrent in response.torrents)


async def torrent_filter(curarg, filter_names=True):
    """
    Values and/or names for torrent filters

    If `filter_names` evaluates to False, filter names are not included in the
    returned list, only torrent names.

    The return value is either an empty tuple, a 1-tuple (filter values) or a
    2-tuple (filter names and filter values).
    """
    return await _filter(curarg, 'TorrentFilter',
                         torrent_filter=None,
                         filter_names=filter_names,
                         items_getter=None)

async def file_filter(curarg, torrent_filter, filter_names=True):
    """Values and/or names for file filters (see `torrent_filter`)"""
    # Get list of files from Torrent instance
    def items_getter(t):
        # Exclude single-file torrents (torrents that don't contain a
        # directory); file filters are irrelevant in that case.
        files = tuple(t['files'].files)
        if len(files) != 1 or t['name'] != files[0]['name']:
            return files
        else:
            return ()
    return await _filter(curarg, 'FileFilter',
                         torrent_filter=torrent_filter,
                         filter_names=filter_names,
                         items_getter=items_getter)

async def peer_filter(curarg, torrent_filter, filter_names=True):
    """Values and/or names for peer filters (see `torrent_filter`)"""
    return await _filter(curarg, 'PeerFilter',
                         torrent_filter=torrent_filter,
                         filter_names=filter_names,
                         # Get list of peers from Torrent instance
                         items_getter=lambda t: t['peers'])

async def _filter(curarg, filter_cls_name, torrent_filter, filter_names, items_getter):
    """
    Values and/or names for filters

    If `filter_names` evaluates to False, filter names are not included in the
    returned list, i.e. only values for the default filter (e.g. torrent name)
    are completed.

    The return value is either an empty tuple, a 1-tuple (filter values) or a
    2-tuple (filter names and filter values).
    """
    filter_cls = _utils.get_filter_cls(filter_cls_name)
    default_filter = filter_cls.DEFAULT_FILTER
    if curarg.startswith(filter_cls.INVERT_CHAR):
        curarg = curarg[1:]

    # Separate individual filters, e.g. 'seeding|comment=foo' -> ('seeding', 'comment=foo')
    filter_strings = curarg.separate(_utils.filter_combine_ops, include_seps=True)

    # Most arguments to _filter_values() are the same
    filter_values = functools.partial(_filter_values, filter_cls_name,
                                      torrent_filter=torrent_filter,
                                      items_getter=items_getter)

    # Separate filter name from filter value
    parts = filter_strings.curarg.separate(_utils.filter_compare_ops, include_seps=True)
    if parts.curarg_index == 0:
        # If focus is on filter name, complete filter names and values for the
        # default filter (usually "name")
        if filter_names:
            log.debug('Completing filter names and %r values: %r', default_filter, parts[0])
            return (_utils.filter_names(filter_cls_name),
                    await filter_values(default_filter))
        else:
            log.debug('Completing %r values (no filter names): %r', default_filter, parts[0])
            return (await filter_values(default_filter),)

    elif parts.curarg_index == 1 and parts[0] in _utils.filter_compare_ops:
        # User gave a comparison operator but not a filter name, e.g. ('=', 'foo')
        log.debug('Completing %r (default) values', default_filter)
        return (await filter_values(default_filter),)

    elif parts.curarg_index == 2:
        # User gave filter name, operator and value, e.g. ('comment', '!=', 'foo')
        filter_name = parts[0].strip()
        log.debug('Completing %r values', filter_name)
        return (await filter_values(filter_name),)
    else:
        return ()

async def _filter_values(filter_cls_name, filter_name, torrent_filter, items_getter):
    # Return list of possible values for filter (if filter is comparative)
    filter_cls = _utils.get_filter_cls(filter_cls_name)
    cands = ()
    if _utils.filter_takes_completable_values(filter_cls, filter_name):
        keys = filter_cls(filter_name).needed_keys
        response = await objects.srvapi.torrent.torrents(torrent_filter,
                                                         keys=keys,
                                                         from_cache=True)
        if response.success:
            # Get the same values that the filter would get
            value_getter = _utils.get_filter_spec(filter_cls, filter_name).value_getter

            cands = []
            def add_cands_for(item, _value_getter=value_getter, _cands=cands):
                # Get the same value from `item` that the filter would get
                value = _value_getter(item)
                # Some value_getters return multiple values, e.q. the torrent
                # filter "tracker", which matches against domain names of
                # announce URLs.
                if isinstance(value, (abc.Iterable, abc.Iterator)) and not isinstance(value, str):
                    value = tuple(value)
                    _cands.extend(value)
                else:
                    _cands.append(value)

            # File
            if items_getter is None:
                # Filtering Torrent instances
                for t in response.torrents:
                    add_cands_for(t)
            else:
                # Filtering items from torrent['files'] or torrent['peers']
                for t in response.torrents:
                    items = items_getter(t)
                    for i in items:
                        add_cands_for(i)

    curarg_seps = itertools.chain(_utils.filter_compare_ops, _utils.filter_combine_ops)
    label = '%s Filter: %s' % (filter_cls_name[:-6], filter_name)
    return Candidates(cands, label=label, curarg_seps=curarg_seps)
