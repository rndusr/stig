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

from ..singletons import (localcfg, remotecfg)
from ..singletons import cmdmgr
from ..utils import usertypes

from itertools import chain


class Candidates(tuple):
    """
    Iterable of candidates

    All functions in this module should return an instance of this.
    """
    def __new__(cls, *candidates, tail=' '):
        obj = super().__new__(cls, candidates)
        obj.tail = tail
        return obj

    def __repr__(self):
        return 'Canididates(%s, tail=%r)' % (
            ', '.join(repr(c) for c in self),
            self.tail)


def commands():
    return Candidates(*(cmdcls.name for cmdcls in cmdmgr.active_commands))


def settings():
    return Candidates(*(chain(
        localcfg,
        ('srv.' + name for name in remotecfg)
    )))


def values(setting, args, focus):
    log.debug('Getting value candidates for %r with args: %r', setting, args)
    # Get setting from localcfg or remotecfg
    if setting in localcfg:
        setting = localcfg[setting]
    elif setting.startswith('srv.') and setting[4:] in remotecfg:
        setting = remotecfg[setting[4:]]
    else:
        log.debug('No such setting: %r', setting)
        return Candidates()

    # Some settings accept multiple values, others only one
    focus_on_first_value = focus == 2

    log.debug('Setting is a %s: %r', type(setting).__name__, setting)
    # Get candidates depending on what kind of setting it is (bool, option, etc)
    if isinstance(setting, usertypes.Option) and focus_on_first_value:
        return Candidates(*setting.options)
    elif isinstance(setting, usertypes.Tuple):
        return Candidates(*setting.options)
    elif isinstance(setting, usertypes.Bool) and focus_on_first_value:
        return Candidates(*(
            value
            for values in zip(usertypes.Bool.defaults['true'],
                              usertypes.Bool.defaults['false'])
            for value in values))

    return Candidates()
