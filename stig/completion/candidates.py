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
from ..client import filters as filter_clses

import itertools
import os
import re
import functools
from collections import abc

_commands = tuple(cmdcls.name for cmdcls in objects.cmdmgr.active_commands)
def commands():
    """Names of commands"""
    return _commands


@functools.lru_cache(maxsize=None)
def setting_names():
    """Names of settings"""
    local_cands = (Candidate(name,
                             description=objects.localcfg.description(name),
                             default=str(objects.localcfg.default(name)))
                   for name in objects.localcfg)
    remote_cands = (Candidate('srv.' + name,
                              description=objects.remotecfg.description(name),
                              default=str(objects.remotecfg.default(name)))
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
        cands = (Candidate(opt, in_parens=aliases.get(opt, ''))
                 for opt in value.options)
        return Candidates(cands, label='%s options' % (setting,))
    elif isinstance(value, usertypes.Tuple):
        aliases = value.aliases_inverse
        cands = (Candidate(opt, in_parens=aliases.get(opt, ''))
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


def fs_path(path, base=os.path.expanduser('~'), directories_only=False, glob=None, regex=None):
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


# All filters use the same operators
_filter_combine_ops = ('&', '|')
_filter_compare_ops = filter_clses.TorrentFilter.POSSIBLE_OPERATORS
_filter_labels = {'TorrentFilter' : 'Torrent Filters',
                  'FileFilter'    : 'File Filters',
                  'PeerFilter'    : 'Peer Filters',
                  'TrackerFilter' : 'Tracker Filters',
                  'SettingFilter' : 'Setting Filters'}

async def torrent_filter(curarg):
    """
    Torrent filter names and maybe values for default filter

    The return value is a tuple with 0, 1 or 2 items.
    """
    filter_cls = _get_filter_cls('TorrentFilter')
    if curarg.startswith(filter_cls.INVERT_CHAR):
        curarg = curarg[1:]

    # Separate individual filters, e.g. 'seeding|comment=foo'
    filter_strings = curarg.separate(_filter_combine_ops, include_seps=True)
    # Separate filter name from filter value
    parts = filter_strings.curarg.separate(_filter_compare_ops, include_seps=True)
    if parts.curarg_index == 0:
        # If focus is on filter name, complete filter names and torrent names
        # (default torrent filter is 'name')
        log.debug('Completing torrent filter names and torrent names: %r', parts[0])
        return (_filter_names('TorrentFilter'),
                await _torrent_filter_values(filter_cls.DEFAULT_FILTER))
    elif parts.curarg_index == 2:
        # parts is something like ('comment', '!=', 'foo')
        log.debug('Completing %r torrent filter values', parts[0])
        return (await _torrent_filter_values(parts[0].strip()),)
    else:
        return ()

@functools.lru_cache(maxsize=None)
def _filter_names(filter_cls_name):
    """Filter names as Candidate instances with description and aliases"""
    def get_names(filter_cls):
        for name in _get_filter_names(filter_cls):
            filter_spec = _get_filter_spec(filter_cls, name)
            desc = filter_spec.description
            alias_str = ','.join(filter_spec.aliases)
            yield Candidate(name, description=desc, in_parens=alias_str)

    filter_cls = _get_filter_cls(filter_cls_name)
    curarg_seps = itertools.chain(_filter_compare_ops, _filter_combine_ops, (filter_cls.INVERT_CHAR,))
    return Candidates(get_names(filter_cls),
                      curarg_seps=curarg_seps,
                      label=_filter_labels[filter_cls_name])

async def _torrent_filter_values(filter_name):
    filter_cls = _get_filter_cls('TorrentFilter')
    cands = ()
    if _filter_takes_completable_values(filter_cls, filter_name):
        keys = filter_cls(filter_name).needed_keys
        response = await objects.srvapi.torrent.torrents(keys=keys, from_cache=True)
        if response.success:
            value_getter = _get_filter_spec(filter_cls, filter_name).value_getter
            cands = []
            for t in response.torrents:
                value = value_getter(t)
                if not isinstance(value, str) and isinstance(value, (abc.Iterable, abc.Iterator)):
                    cands.extend(value)
                else:
                    cands.append(value)
    curarg_seps = itertools.chain(_filter_compare_ops, _filter_combine_ops)
    return Candidates(cands,
                      label='Torrent Filter Values: %s' % (filter_name,),
                      curarg_seps=curarg_seps)

@functools.lru_cache(maxsize=None)
def _get_filter_cls(name):
    try:
        return getattr(filter_clses, name)
    except AttributeError:
        raise ValueError('Not a filter class: %r' % name)

@functools.lru_cache(maxsize=None)
def _get_filter_names(filter_cls):
    return itertools.chain(filter_cls.BOOLEAN_FILTERS,
                           filter_cls.COMPARATIVE_FILTERS)

@functools.lru_cache(maxsize=None)
def _get_filter_spec(filter_cls, name):
    try:
        return filter_cls.BOOLEAN_FILTERS[name]
    except KeyError:
        try:
            return filter_cls.COMPARATIVE_FILTERS[name]
        except KeyError:
            raise ValueError('No such filter: %r' % (name,))

@functools.lru_cache(maxsize=None)
def _filter_takes_completable_values(filter_cls, name):
    try:
        filter_spec = _get_filter_spec(filter_cls, name)
    except ValueError:
        return False
    else:
        return (name in filter_cls.COMPARATIVE_FILTERS and
                filter_spec is not None and
                issubclass(filter_spec.value_type, str))
