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


from ..singletons import (localcfg, remotecfg, cmdmgr, srvapi)
from ..utils import usertypes
from ..completion import Candidates

import itertools
import os
import re


_commands = tuple(cmdcls.name for cmdcls in cmdmgr.active_commands)
def commands():
    """Names of commands"""
    return _commands


_setting_names = tuple(itertools.chain(localcfg, ('srv.' + name for name in remotecfg)))
def setting_names():
    """Names of settings"""
    return Candidates(_setting_names, label='Settings')


def setting_values(setting, args, curarg_index):
    """Values of settings"""
    if setting in localcfg:
        value = localcfg[setting]
    elif setting.startswith('srv.') and setting[4:] in remotecfg:
        value = remotecfg[setting[4:]]
    else:
        return

    if value is not None:
        curarg = args[curarg_index]

        # Some settings accept multiple values, others only one
        focus_on_first_value = curarg_index == 2

        log.debug('Setting is a %s: %r', type(value).__name__, value)
        # Get candidates depending on what kind of setting it is (bool, option, etc)
        if isinstance(value, usertypes.Option) and focus_on_first_value:
            return Candidates(value.options, label='%s options' % (setting,))
        elif isinstance(value, usertypes.Tuple):
            return Candidates(value.options, label='%s options' % (setting,),
                              curarg_seps=(value.sep.strip(),))
        elif isinstance(value, usertypes.Bool) and focus_on_first_value:
            options = (val
                       for vals in zip(usertypes.Bool.defaults['true'],
                                       usertypes.Bool.defaults['false'])
                       for val in vals)
            return Candidates(options, label='%s options' % (setting,))
        elif isinstance(value, usertypes.Path):
            return fs_path(curarg.before_cursor,
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


async def torrent_filter(curarg):
    """Torrent filter names or values"""
    parts = curarg.separate(_possible_operators, include_seps=True)
    if parts.curpart_index == 0:
        log.debug('Completing torrent filtername of %r: %r', curarg, parts[0])
        return (
            Candidates(_filter_names['torrent'],
                       label='Torrent Filters',
                       curarg_seps=_possible_operators),
            Candidates(await _filter_values('torrent', 'name~'),
                       label='name~ torrents')
        )
    elif parts.curpart_index == 2 and parts[0] in _filter_names['torrent']:
        log.debug('Completing torrent filter value of %r: %r', curarg, parts.curpart)
        return (Candidates(await _filter_values('torrent', parts[0]),
                           label='%s torrents' % parts[0],
                           curarg_seps=_possible_operators),)

from ..client import (TorrentFilter, TorrentFileFilter, TorrentPeerFilter,
                      TorrentTrackerFilter, SettingFilter)

_filter_names = {}
for section,filter_class in (('torrent', TorrentFilter),
                             ('file', TorrentFileFilter),
                             ('peer', TorrentPeerFilter),
                             ('tracker', TorrentTrackerFilter),
                             ('setting', SettingFilter)):
    _filter_names[section] = tuple(itertools.chain(filter_class.BOOLEAN_FILTERS,
                                                   filter_class.COMPARATIVE_FILTERS))
_possible_operators = tuple(o
                            for op in TorrentFilter.OPERATORS
                            for o in (op, TorrentFilter.INVERT_CHAR+op))

async def _filter_values(section, filter_name):
    try:
        filter = TorrentFilter(filter_name)
    except ValueError as e:
        pass
    else:
        response = await srvapi.torrent.torrents(filter, from_cache=True)
        if response.success:
            key = filter.needed_keys[0]
            return tuple(t[key] for t in response.torrents)
    return ()
