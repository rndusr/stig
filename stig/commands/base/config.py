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

"""Base classes for configuration commands"""

from ...logging import make_logger
log = make_logger(__name__)

from .. import (InitCommand, ExpectedResource, utils)
from asyncio import iscoroutinefunction


class ResetCmdbase(metaclass=InitCommand):
    name = 'reset'
    category = 'misc'
    provides = set()
    description = 'Reset settings to their default values'
    usage = ('reset <NAME> <NAME> <NAME> ...',)
    examples = ('reset srv.url',)
    argspecs = (
        {'names': ('NAME',), 'nargs': '+',
         'description': 'Name of setting'},
    )
    cfg = ExpectedResource

    def run(self, NAME):
        from ...settings import is_server_setting
        success = True
        for name in NAME:
            if name not in self.cfg:
                log.error('Unknown setting: {}'.format(name))
                success = False
            elif is_server_setting(name):
                log.error('Server settings cannot be reset: {}'.format(name))
                success = False
            else:
                self.cfg[name] = None
        return success


class SetCmdbase(metaclass=InitCommand):
    name = 'set'
    category = 'misc'
    provides = set()
    description = 'Change values of settings'
    usage = ('set <NAME> <VALUE>',)
    examples = ('set srv.url my.server.example.org:12345',)
    argspecs = (
        {'names': ('NAME',),
         'description': 'Name of setting'},
        {'names': ('VALUE',), 'nargs': 'REMAINDER',
         'description': 'New value'},
    )
    cfg = ExpectedResource
    srvapi = ExpectedResource

    async def run(self, NAME, VALUE):
        if NAME not in self.cfg:
            log.error('Unknown setting: {}'.format(NAME))
        else:
            setting = self.cfg[NAME]

            # Make sure strings are strings and lists are lists
            if setting.typename in ('list', 'set'):
                val = utils.listify_args(VALUE)
            else:
                val = ' '.join(VALUE)

            from ...settings import is_server_setting
            if is_server_setting(setting):
                from ...client import ClientError
                try:
                    await self.srvapi.settings.update()
                except ClientError as e:
                    log.error(str(e))
                    return False

            try:
                # Server settings' set() methods are async (maybe others too)
                if iscoroutinefunction(setting.set):
                    await setting.set(val)
                else:
                    setting.set(val)
            except ValueError as e:
                log.error(e)
            else:
                return True

        return False
