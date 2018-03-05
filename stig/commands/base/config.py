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
from ...utils.stringables import Float

import subprocess
import operator


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
                self.cfg.reset(name)
        return success


from ...client import ClientError
class SetCmdbase(metaclass=InitCommand):
    name = 'set'
    category = 'configuration'
    provides = set()
    description = 'Change {__appname__} settings'
    usage = ('set <NAME>[:eval] <VALUE>',)
    examples = ('set connect.host my.server.example.org',
                'set connect.user jonny_sixpack',
                'set connect.password:eval getpw --id transmission',
                'set tui.log.height +=10')
    argspecs = (
        {'names': ('NAME',),
         'description': "Name of setting; append ':eval' to turn VALUE into a shell command"},
        {'names': ('VALUE',), 'nargs': 'REMAINDER',
         'description': ('New value or shell command that prints the new value to stdout; '
                         "numerical values can be adjusted by prepending '+=' or '-='")},
    )
    more_sections = {
        'SEE ALSO': (('Run `help settings` for a list of all available '
                      'local and remote settings.'),),
    }
    cfg = ExpectedResource
    srvcfg = ExpectedResource

    async def run(self, NAME, VALUE):
        # NAME might have ':eval' attached if VALUE is shell command
        try:
            name, key, is_local_setting = self._parse_name(NAME)
        except ValueError as e:
            log.error(e)
            return False

        cfg = self.cfg if is_local_setting else self.srvcfg

        # Get current value in case we want to adjust it
        if not is_local_setting:
            try:
                await cfg.update()
            except ClientError as e:
                log.error('%s', e)
                return False

        # VALUE might be shell command or have '+='/'-=' prepended
        try:
            value = self._parse_value(VALUE,
                                      listify=isinstance(cfg[key], tuple),
                                      is_cmd=NAME.endswith(':eval'))
        except ValueError as e:
            log.error('%s: %s' % (name, e))
            return False

        # Separate '+=' or '-=' from value
        try:
            op, value = self._get_operator(value)
        except ValueError as e:
            log.error('%s = %s: %s' % (name, value, e))
            return False

        # Value may have an operator (e.g. '+=' or '-=') to adjust the current value
        if op is not None:
            try:
                value = self._adjust_value(cfg[key], op, value)
            except ValueError as e:
                opfunc = getattr(operator, op)
                unbound = cfg[key].copy(min=-float('inf'), max=float('inf'))
                invalid = opfunc(unbound, value)
                log.error('%s = %s: %s' % (name, invalid, e))
                return False

        # Update setting's value
        try:
            if is_local_setting:
                log.debug('Local setting: %r = %r', name, value)
                cfg[key] = value
            else:
                log.debug('Remote setting: %r = %r', name, value)
                await cfg.set(key, value)
        except ValueError as e:
            log.error('%s = %s: %s', name, value, e)
            return False
        except ClientError as e:
            log.error('%s', e)
            return False
        else:
            return True

    def _parse_name(self, name):
        if name.endswith(':eval'):
            name = name[:-5]
        if name in self.cfg:
            return name, name, True
        elif name.startswith('srv.') and name[4:] in self.srvcfg:
            return name, name[4:], False
        else:
            raise ValueError('Unknown setting: %s' % name)

    def _parse_value(self, value, listify=False, is_cmd=False):
        if is_cmd:
            value = [self._eval_cmd(value)]
        if listify:
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
            raise ValueError(stderr)
        else:
            return stdout

    @staticmethod
    def _get_operator(value):
        if isinstance(value, str):
            value = value.strip()
            if len(value) >= 3:
                def to_num(string):
                    try:
                        return Float(string)
                    except ValueError as e:
                        raise ValueError('%s: %r' % (e, string))
                if value[:2] == '+=':
                    return '__add__', to_num(value[2:])
                elif value[:2] == '-=':
                    return '__sub__', to_num(value[2:])
        return None, value

    @staticmethod
    def _adjust_value(current, op, value):
        if isinstance(current, (float, int)):
            if current >= float('inf'):
                current = Float(0)
            func = getattr(operator, op)
            value = func(current, value)
        return value


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
                log.error('%s: Invalid direction: %r', self.name, d)
                return False

        # Do we adjust current limits or set absolute limits?
        limit = LIMIT.strip()
        if limit[:2] == '+=' or limit[:2] == '-=':
            method_start = 'adjust_limit_rate_'
            limit = limit[0] + limit[2:]  # Remove '=' so it can be parsed as a number
        else:
            method_start = 'set_limit_rate_'

        # _set_limits() is defined in cli.config and tui.config and behaves slightly differently
        return await self._set_limits(TORRENT_FILTER, directions, limit, method_start)

    async def _set_global_limit(self, directions, limit, method_start):
        for d in directions:
            log.debug('Setting global %s rate limit: %r', d, limit)
            method = getattr(self.srvapi.settings, method_start + d)
            try:
                await method(limit)
            except ValueError as e:
                log.error('%s: %r', e, limit)
                return False
            except ClientError as e:
                log.error('%s', e)
                return False
        return True

    async def _set_individual_limit(self, TORRENT_FILTER, directions, limit, method_start):
        try:
            tfilter = self.select_torrents(TORRENT_FILTER,
                                           allow_no_filter=False,
                                           discover_torrent=True)
        except ValueError as e:
            log.error(e)
            return False

        log.debug('Setting %sload rate limit for %s torrents: %r',
                  '+'.join(directions), tfilter, limit)

        for d in directions:
            method = getattr(self.srvapi.torrent, method_start + d)
            response = await self.make_request(method(tfilter, limit),
                                               polling_frenzy=True)
            if not response.success:
                return False
