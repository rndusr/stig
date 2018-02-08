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

from ...logging import make_logger
log = make_logger(__name__)

from .. import (InitCommand, ExpectedResource, utils)
from ._common import make_X_FILTER_spec

import asyncio
import subprocess


class RcCmdbase(metaclass=InitCommand):
    name = 'rc'
    aliases = ('source',)
    category = 'configuration'
    provides = set()
    description = 'Run commands in rc file'
    usage = ('rc <FILE>',)
    examples = ('rc rc.example   # Load $XDG_CONFIG_HOME/.config/{__appname__}/rc.example',)
    argspecs = (
        {'names': ('FILE',),
         'description': ('Path to rc file; if FILE does not start with '
                         "'.', '~' or '/', $XDG_CONFIG_HOME/.config/{__appname__}/ "
                         'is prepended')},
    )
    cmdmgr = ExpectedResource

    async def run(self, FILE):
        from ...settings import rcfile
        from ...settings.defaults import DEFAULT_RCFILE
        import os

        if FILE[0] not in (os.sep, '.', '~'):
            default_dir = os.path.dirname(DEFAULT_RCFILE)
            FILE = os.path.join(default_dir, FILE)

        try:
            lines = rcfile.read(FILE)
        except rcfile.RcFileError as e:
            log.error('Loading rc file failed: {}'.format(e))
            return False
        else:
            log.debug('Running commands from rc file: %r', FILE)
            for cmdline in lines:
                success = await self.cmdmgr.run_async(cmdline, on_error=log.error)
                if success is False:
                    return False
            return True


class ResetCmdbase(metaclass=InitCommand):
    name = 'reset'
    category = 'configuration'
    provides = set()
    description = 'Reset settings to their default values'
    usage = ('reset <NAME> <NAME> <NAME> ...',)
    examples = ('reset connect.port',)
    argspecs = (
        {'names': ('NAME',), 'nargs': '+',
         'description': 'Name of setting'},
    )
    more_sections = {
        'SEE ALSO': ('Run `help settings` for a list of all available settings.',
                     'Note that remote settings (srv.*) cannot be reset.'),
    }
    cfg = ExpectedResource

    def run(self, NAME):
        success = True
        for name in NAME:
            if name not in self.cfg:
                log.error('Unknown setting: {}'.format(name))
                success = False
            elif name.startswith('srv.'):
                log.error('Remote settings cannot be reset: {}'.format(name))
                success = False
            else:
                self.cfg[name].reset()
        return success


class SetCmdbase(metaclass=InitCommand):
    name = 'set'
    category = 'configuration'
    provides = set()
    description = 'Change {__appname__} settings'
    usage = ('set <NAME>[:eval] <VALUE>',)
    examples = ('set connect.host my.server.example.org',
                'set connect.user jonny_sixpack',
                'set connect.password:eval getpw --id transmission')
    argspecs = (
        {'names': ('NAME',),
         'description': "Name of setting; append ':eval' to turn VALUE into a shell command"},
        {'names': ('VALUE',), 'nargs': 'REMAINDER',
         'description': 'New value or shell command that prints the new value to stdout'},
    )
    more_sections = {
        'SEE ALSO': (('Run `help settings` for a list of all available '
                      'local and remote settings.'),),
    }
    cfg = ExpectedResource

    async def run(self, NAME, VALUE):
        # Get setting by name from local or remote settings
        try:
            setting = self._get_setting(NAME)
        except ValueError as e:
            log.error(e)
            return False

        # Normalized value
        try:
            value = self._get_value(VALUE, setting.typename,
                                    is_cmd=NAME.endswith(':eval'))
        except ValueError as e:
            log.error(e)
            return False

        # Update setting's value
        try:
            if asyncio.iscoroutinefunction(setting.set):
                log.debug('Setting remote setting %s to %r', setting.name, value)
                await setting.set(value)
            else:
                log.debug('Setting local setting %s to %r', setting.name, value)
                setting.set(value)
        except ValueError as e:
            log.error('%s = %s: %s', setting.name, setting.string(value), e)
            return False
        else:
            return True

    def _get_setting(self, name):
        if name.endswith(':eval'):
            name = name[:-5]

        try:
            return self.cfg[name]
        except KeyError:
            raise ValueError('Unknown setting: %s' % name)

    def _get_value(self, value, typename, is_cmd=False):
        if is_cmd:
            value = [self._eval_cmd(value)]

        # Make sure lists are lists and everything else is a string
        if typename in ('list', 'set'):
            return utils.listify_args(value)
        else:
            return ' '.join(value)

    @staticmethod
    def _eval_cmd(cmd):
        if not isinstance(cmd, str):
            cmd = ' '.join(cmd)
        log.debug('Running shell command: %r', cmd)
        proc = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout = proc.stdout.decode('utf-8').strip('\n')
        stderr = proc.stderr.decode('utf-8').strip('\n')
        if stderr:
            raise ValueError('%s: %s' % (cmd, stderr))
        else:
            return stdout


# Abuse some *Value classes from the settings to allow the same user-input for
# individual torrents as we do for the global settings srv.limit.rate.*.
from ...client.usertypes import (MultiValue, BooleanValue, UnlimitedValue, BandwidthValue)
class TorrentRateLimitValue(MultiValue(UnlimitedValue, BandwidthValue, BooleanValue)):
    pass

class RateLimitCmdbase(metaclass=InitCommand):
    name = 'ratelimit'
    aliases = ('rate',)
    provides = set()
    category = 'configuration'
    description = "Limit up-/download rate per torrent or globally"
    usage = ('ratelimit <DIRECTION> <LIMIT>',
             'ratelimit <DIRECTION> <LIMIT> <TORRENT FILTER> <TORRENT FILTER> ...')
    examples = ('ratelimit up 5Mb',
                'ratelimit down,up 1M global',
                'ratelimit up,dn off "This torrent" size<100MB')
    argspecs = (
        {'names': ('DIRECTION',),
         'description': 'Any combination of "up", "down" or "dn" separated by a comma'},
        {'names': ('LIMIT',),
         'description': ('Maximum allowed transfer rate; see `help srv.limit.rate.up` for the syntax')},
        make_X_FILTER_spec('TORRENT', or_focused=True, nargs='*',
                           more_text=('"global" to set global limit (same as setting '
                                      "srv.limit.rate.<DIRECTION>); may be omitted in CLI mode "
                                      'for the same effect as specifying "global"')),
    )
    srvapi = ExpectedResource

    async def run(self, DIRECTION, LIMIT, TORRENT_FILTER):
        directions = set('down' if d == 'dn' else d
                         for d in map(str.lower, DIRECTION.split(',')))
        for d in directions:
            if d not in ('up', 'down'):
                log.error('%s: Invalid item in argument DIRECTION: %r', self.name, d)
                return False

        # _set_limits() is defined in cli.config and tui.config and behaves
        # slightly differently.
        return await self._set_limits(TORRENT_FILTER, directions, LIMIT)

    async def _set_global_limit(self, directions, LIMIT):
        # Change the srv.limit.rate.* setting for each direction
        for d in directions:
            print('Setting global %s rate limit: %r' % (d, LIMIT))
            log.debug('Setting global %s rate limit: %r', d, LIMIT)
            try:
                await self.srvapi.settings['rate.limit.'+d].set(LIMIT)
            except ValueError as e:
                log.error(e)
                return False
        return True

    async def _set_individual_limit(self, TORRENT_FILTER, directions, LIMIT):
        try:
            tfilter = self.select_torrents(TORRENT_FILTER,
                                           allow_no_filter=False,
                                           discover_torrent=True)
        except ValueError as e:
            log.error(e)
            return False

        log.debug('Setting %sload rate limit for %s torrents: %r',
                  '+'.join(directions), tfilter, LIMIT)

        # Do we adjust current limits or set absolute limits?
        limit = LIMIT.strip()
        if limit[:2] == '+=' or limit[:2] == '-=':
            method_start = 'adjust_rate_limit_'
            limit = limit[0] + limit[2:]  # Remove '=' so it can be parsed as a number
        else:
            method_start = 'set_rate_limit_'

        try:
            new_limit = TorrentRateLimitValue('_new_limit', default=limit).get()
        except ValueError as e:
            log.error('%s: %r', e, limit)
            return False

        log.debug('Setting %sload rate limit for %s torrents: %r',
                  '+'.join(directions), tfilter, new_limit)

        for d in directions:
            method = getattr(self.srvapi.torrent, method_start + d)
            response = await self.make_request(method(tfilter, new_limit),
                                               polling_frenzy=True)
            if not response.success:
                return False
