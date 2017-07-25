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


class RcCmdbase(metaclass=InitCommand):
    name = 'rc'
    aliases = ('source',)
    category = 'configuration'
    provides = set()
    description = 'Run commands in rc file'
    usage = ('rc <FILE>',)
    examples = ('rc rc.example   # Load $XDG_CONFIG_HOME/.config/{APPNAME}/rc.example',)
    argspecs = (
        {'names': ('FILE',),
         'description': ('Path to rc file; if FILE does not start with '
                         "'.', '~' or '/', $XDG_CONFIG_HOME/.config/{APPNAME}/ "
                         'is prepended')},
    )
    cmdmgr = ExpectedResource

    async def run(self, FILE):
        from ...settings import rcfile
        from ...settings.defaults import DEFAULT_RCFILE
        import os

        if FILE[0] not in (os.sep, '.', '~'):
            FILE = '{}{}{}'.format(os.path.dirname(DEFAULT_RCFILE),
                                   os.sep,
                                   FILE)

        try:
            lines = rcfile.read(FILE)
        except rcfile.RcFileError as e:
            log.error('Loading rc file failed: {}'.format(e))
            return False
        else:
            log.debug('Running commands from rc file: %r', FILE)
            for cmdline in lines:
                log.debug('  %r', cmdline)
                success = await self.cmdmgr.run_async(cmdline)
                if success is False:
                    return False
            return True


class ResetCmdbase(metaclass=InitCommand):
    name = 'reset'
    category = 'configuration'
    provides = set()
    description = 'Reset settings to their default values'
    usage = ('reset <NAME> <NAME> <NAME> ...',)
    examples = ('reset srv.url',)
    argspecs = (
        {'names': ('NAME',), 'nargs': '+',
         'description': 'Name of setting'},
    )
    more_sections = {
        'SEE ALSO': (('Run `help settings` for a list of all available settings.  Note that '
                      'server settings (srv.* except for srv.url and srv.timeout) cannot be reset.'),),
    }

    cfg = ExpectedResource

    def run(self, NAME):
        from ...settings import is_srv_setting
        success = True
        for name in NAME:
            if name not in self.cfg:
                log.error('Unknown setting: {}'.format(name))
                success = False
            elif is_srv_setting(self.cfg[name]):
                log.error('Server settings cannot be reset: {}'.format(name))
                success = False
            else:
                self.cfg[name].reset()
        return success


class SetCmdbase(metaclass=InitCommand):
    name = 'set'
    category = 'configuration'
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
    more_sections = {
        'SEE ALSO': (('Run `help settings` for a list of all available '
                      'client and server settings.'),),
    }

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

            from ...settings import is_srv_setting
            if is_srv_setting(setting):
                # Fetch current values from server first
                try:
                    await self.srvapi.settings.update()
                except self.srvapi.ClientError as e:
                    log.error(str(e))
                    return False
                else:
                    # Send new setting to server
                    try:
                        await setting.set(val)
                    except ValueError as e:
                        log.error('%s = %s: %s', setting.name, setting.string(val), e)
                    else:
                        return True

            else:
                # Client setting
                try:
                    setting.set(val)
                except ValueError as e:
                    log.error('%s = %s: %s', setting.name, setting.string(val), e)
                else:
                    return True

        return False
