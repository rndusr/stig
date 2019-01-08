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


from ..singletons import (localcfg, remotecfg)
from ..singletons import cmdmgr
from ..utils import usertypes

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
    return _setting_names


def setting_values(setting, args, curarg_index):
    """Values of settings"""
    setting = _get_setting(setting)
    if setting is not None:
        # Some settings accept multiple values, others only one
        focus_on_first_value = curarg_index == 2

        log.debug('Setting is a %s: %r', type(setting).__name__, setting)
        # Get candidates depending on what kind of setting it is (bool, option, etc)
        if isinstance(setting, usertypes.Option) and focus_on_first_value:
            return setting.options
        elif isinstance(setting, usertypes.Tuple):
            return setting.options, (setting.sep.strip(),)
        elif isinstance(setting, usertypes.Bool) and focus_on_first_value:
            return (value
                    for values in zip(usertypes.Bool.defaults['true'],
                                      usertypes.Bool.defaults['false'])
                    for value in values)

def _get_setting(name):
    # Get setting from localcfg or remotecfg
    if name in localcfg:
        return localcfg[name]
    elif name.startswith('srv.') and name[4:] in remotecfg:
        return remotecfg[name[4:]]
    log.debug('No such setting: %r', name)


def fs_path(path, base=os.path.expanduser('~'), directories_only=False, regex=None):
    """
    File system path entries

    path: Path to get entries from
    base: Absolute path that is prepended to `path` if `path` is not absolute
    directories_only: Whether to include only directories
    regex: Regular expression that is matched against each name in `path`
    """
    log.debug('Getting path candidates for %r', path)
    if path.startswith('~') and os.sep not in path:
        # Complete home dirs in "~<user>" style
        import pwd
        users = pwd.getpwall()
        cands = ('~%s' % (user.pw_name,) for user in users)
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
        else:
            cands = (entry.name for entry in itr
                     if ((include_hidden or not entry.name.startswith('.')) and
                         (not directories_only or entry.is_dir()) and
                         (regex is None or entry.is_dir() or re.search(regex, entry.name))))
    return cands, ('/',)
