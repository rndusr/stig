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


_commands = tuple(cmdcls.name for cmdcls in cmdmgr.active_commands)
def commands():
    """Names of commands"""
    return _commands


_settings = tuple(itertools.chain(localcfg, ('srv.' + name for name in remotecfg)))
def settings():
    """Names of settings"""
    return _settings


def values(setting, args, curarg_index):
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


def fs_path(path, base, include_hidden=True, directories_only=False):
    """File system path entries"""
    log.debug('Getting path candidates for %r', path)
    if path.startswith('~') and os.sep not in path:
        # Complete home dirs in "~<user>" style
        import pwd
        users = pwd.getpwall()
        cands = ('~%s' % (user.pw_name,) for user in users)
    else:
        path = os.path.expanduser(path)
        if not os.path.isabs(path):
            path = os.path.join(base, path)
        path = os.path.dirname(path)

        try:
            itr = os.scandir(path)
        except (FileNotFoundError, NotADirectoryError, PermissionError):
            cands = ()
        else:
            cands = (entry.name for entry in itr
                     if ((include_hidden or not entry.name.startswith('.')) and
                         (not directories_only or entry.is_dir())))

    return cands, ('/',)
