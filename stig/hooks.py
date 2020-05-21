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

"""General hooks that are always needed regardless of the interface"""

from .objects import cmdmgr, localcfg, srvapi
from .utils import convert
from .views.file import COLUMNS as FILE_COLUMNS
from .views.peer import COLUMNS as PEER_COLUMNS
from .views.torrent import COLUMNS as TORRENT_COLUMNS

from .logging import make_logger  # isort:skip
log = make_logger(__name__)


def _pre_run_hook(cmdline):
    # Dirty hack to make "ls -h" work
    # If there is '-h' or '--help' in the arguments, replace it with 'help
    # <cmd>'.  This is dirty but easier than forcing argparse to ignore all
    # other arguments without calling sys.exit().
    if '-h' in cmdline or '--help' in cmdline:
        cmdcls = cmdmgr.get_cmdcls(cmdline[0], interface='ANY')
        if cmdcls is not None:
            if cmdcls.name != 'tab':
                cmdline = ['help', cmdcls.name]
            else:
                # 'tab ls -h' is a little trickier because both 'tab' and 'ls'
                # can have arbitrary additional arguments which we must remove.
                #
                # Find first argument to 'tab' that is also a valid command
                # name.  Preserve all arguments before that.
                tab_args = []
                for arg in cmdline[1:]:
                    if cmdmgr.get_cmdcls(arg, interface='ANY') is not None:
                        return ['tab'] + tab_args + ['help', arg]
                    else:
                        tab_args.append(arg)
                cmdline = ['help', 'tab']
    return cmdline
cmdmgr.pre_run_hook = _pre_run_hook


_BANDWIDTH_COLUMNS = (TORRENT_COLUMNS['rate-up'], TORRENT_COLUMNS['rate-down'],
                      TORRENT_COLUMNS['limit-rate-up'], TORRENT_COLUMNS['limit-rate-down'],
                      PEER_COLUMNS['rate-up'], PEER_COLUMNS['rate-down'], PEER_COLUMNS['rate-est'])
def _set_bandwidth_unit(settings, name, value):
    convert.bandwidth.unit = value
    unit_short = convert.bandwidth.unit
    for column in _BANDWIDTH_COLUMNS:
        column.set_unit(unit_short)
        column.clearcache()
    srvapi.torrent.clearcache()
    srvapi.poll()
localcfg.on_change(_set_bandwidth_unit, name='unit.bandwidth')
_set_bandwidth_unit(localcfg, name='unit.bandwidth', value=localcfg['unit.bandwidth'])  # Init columns' units

def _set_bandwidth_prefix(settings, name, value):
    convert.bandwidth.prefix = value
    for column in _BANDWIDTH_COLUMNS:
        column.clearcache()
    srvapi.torrent.clearcache()
    srvapi.poll()
localcfg.on_change(_set_bandwidth_prefix, name='unitprefix.bandwidth')


_SIZE_COLUMNS = (TORRENT_COLUMNS['size'], TORRENT_COLUMNS['downloaded'],
                 TORRENT_COLUMNS['uploaded'], TORRENT_COLUMNS['available'],
                 FILE_COLUMNS['size'], FILE_COLUMNS['downloaded'])
def _set_size_unit(settings, name, value):
    convert.size.unit = value
    unit_short = convert.size.unit
    for column in _SIZE_COLUMNS:
        column.set_unit(unit_short)
        column.clearcache()
    srvapi.torrent.clearcache()
    srvapi.poll()
localcfg.on_change(_set_size_unit, name='unit.size')
_set_size_unit(localcfg, name='unit.size', value=localcfg['unit.size'])  # Init columns' units

def _set_size_prefix(settings, name, value):
    convert.size.prefix = value
    for column in _SIZE_COLUMNS:
        column.clearcache()
    srvapi.torrent.clearcache()
    srvapi.poll()
localcfg.on_change(_set_size_prefix, name='unitprefix.size')
