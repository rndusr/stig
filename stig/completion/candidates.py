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
            return value.options
        elif isinstance(value, usertypes.Tuple):
            return value.options, (value.sep.strip(),)
        elif isinstance(value, usertypes.Bool) and focus_on_first_value:
            return (val
                    for vals in zip(usertypes.Bool.defaults['true'],
                                    usertypes.Bool.defaults['false'])
                    for val in vals)
        elif isinstance(value, usertypes.Path):
            return fs_path(curarg.before_cursor,
                           base=value.base_path,
                           directories_only=os.path.isdir(value))


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
