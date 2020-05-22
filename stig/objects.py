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

"""
Application-wide instances that are always needed, regardless of interface
or features
"""

from . import logging, settings
from .client import API
from .commands import CommandManager
from .helpmgr import HelpManager

log = logging.make_logger()

# Set by main.run()
main_rcfile = None

localcfg = settings.Settings()
settings.init_defaults(localcfg)

srvapi = API(interval=localcfg['tui.poll'])

remotecfg = settings.RemoteSettings(srvapi.settings)

cfg = settings.CombinedSettings(localcfg, remotecfg)

helpmgr = HelpManager()

cmdmgr = CommandManager(info_handler=lambda msg: log.info(msg),
                        error_handler=lambda msg: log.error(msg))
