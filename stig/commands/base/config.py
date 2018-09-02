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

from .. import (InitCommand, CmdError, ExpectedResource, utils)
from ._common import (make_X_FILTER_spec, make_COLUMNS_doc,
                      make_SORT_ORDERS_doc, make_SCRIPTING_doc)
from ...utils.usertypes import Float
from . import _mixin as mixin

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

        if not os.path.isabs(FILE) and not os.path.exists(FILE):
            default_dir = os.path.dirname(DEFAULT_RCFILE)
            FILE = os.path.join(default_dir, FILE)

        try:
            lines = rcfile.read(FILE)
        except rcfile.RcFileError as e:
            raise CmdError('Loading rc file failed: %s' % e)
        else:
            log.debug('Running commands from rc file: %r', FILE)
            for cmdline in lines:
                success = await self.cmdmgr.run_async(cmdline)
                # False means failure, None means the command didn't run because
                # the active interface doesn't support it
                if success is False:
                    raise CmdError()


class ResetCmdbase(metaclass=InitCommand):
    name = 'reset'
    category = 'configuration'
    provides = set()
    description = 'Reset settings to their default values'
    usage = ('reset <NAME> <NAME> <NAME> ...',)
    examples = ('reset connect.port',)
    argspecs = (
        {'names': ('NAME',), 'nargs': '*',
         'description': 'Name of setting'},
    )
    more_sections = {
        'SEE ALSO': ('Run `help settings` for a list of all available settings.',
                     'Note that remote settings (srv.*) cannot be reset.'),
    }
    cfg = ExpectedResource
    srvcfg = ExpectedResource

    def run(self, NAME):
        if not NAME:
            raise CmdError('Missing NAME argument')

        success = True
        for name in NAME:
            if name.startswith('srv.') and name[4:] in self.srvcfg:
                self.error('Remote settings cannot be reset: %s' % name)
                success = False
            elif name not in self.cfg:
                self.error('Unknown setting: %s' % name)
                success = False
            else:
                self.cfg.reset(name)
        if not success:
            raise CmdError()


from ...client import ClientError
class SetCmdbase(mixin.get_setting_sorter, mixin.get_setting_columns,
                 metaclass=InitCommand):
    name = 'set'
    category = 'configuration'
    provides = set()
    description = 'Change {__appname__} settings'
    usage = ('set [<NAME>[:eval]] [<VALUE>]',)
    examples = ('set connect.host my.server.example.org',
                'set connect.user jonny_sixpack',
                'set connect.password:eval getpw --id transmission',
                'set tui.log.height +=10')
    argspecs = (
        {'names': ('NAME',), 'nargs': '?',
         'description': "Name of setting; append ':eval' to turn VALUE into a shell command"},

        {'names': ('VALUE',), 'nargs': 'REMAINDER',
         'description': ('New value or shell command that prints the new value to stdout; '
                         "numerical values can be adjusted by prepending '+=' or '-='")},

        { 'names': ('--sort', '-s'),
          'description': 'Comma-separated list of sort orders (see SORT ORDERS section)' },

        { 'names': ('--columns', '-c'),
          'default_description': "current value of 'columns.settings' setting",
          'description': 'Comma-separated list of column names (see COLUMNS section)' },
    )
    from ...views.setting import COLUMNS
    from ...client.sorters.setting import SettingSorter
    more_sections = {
        'COLUMNS': make_COLUMNS_doc(COLUMNS, '--columns', 'columns.settings'),
        'SORT ORDERS': make_SORT_ORDERS_doc(SettingSorter, '--sort', 'sort.settings'),
        'SCRIPTING': make_SCRIPTING_doc(name),
        'SEE ALSO': (('Run `help settings` or run `set` without commands '
                      'for a list of available local and remote settings.'),),
    }
    cfg = ExpectedResource
    srvcfg = ExpectedResource

    async def run(self, NAME, VALUE, sort, columns):
        if not NAME and not VALUE:
            # Get remote setting values
            try:
                await self.srvcfg.update()
            except ClientError as e:
                error = e
            else:
                error = None

            # Show list of settings
            sort = self.cfg['sort.settings'] if sort is None else sort
            columns = self.cfg['columns.settings'] if columns is None else columns
            try:
                sort = self.get_setting_sorter(sort)
                columns = self.get_setting_columns(columns)
            except ValueError as e:
                raise CmdError(e)
            else:
                self.make_setting_list(sort, columns)
                if error:
                    raise CmdError(error)
            return

        # NAME might have ':eval' attached if VALUE is shell command
        # `name` is the user-facing name of the variable.
        # `key` is the lookup key in the config mapping.
        try:
            name, key, is_local_setting = self._parse_name(NAME)
        except ValueError as e:
            raise CmdError(e)

        cfg = self.cfg if is_local_setting else self.srvcfg

        # Get current value in case we want to adjust it
        if not is_local_setting:
            try:
                await cfg.update()
            except ClientError as e:
                raise CmdError(e)

        # VALUE might be shell command or have '+='/'-=' prepended
        try:
            value = self._parse_value(VALUE,
                                      listify=isinstance(cfg[key], tuple),
                                      is_cmd=NAME.endswith(':eval'))
        except ValueError as e:
            # Report potential stderr output if VALUE is a command
            raise CmdError('%s: %s' % (name, e))

        # Separate '+=' or '-=' from value
        try:
            op, value = self._get_operator(value)
        except ValueError as e:
            # Report invalid value after operator (e.g. nan)
            raise CmdError('%s = %s: %s' % (name, self._stringify(value), e))

        # Value may have an operator (e.g. '+=' or '-=') to adjust the current value
        if op is not None:
            try:
                value = self._adjust_value(cfg[key], op, value)
            except ValueError as e:
                # Report out-of-bounds value
                opfunc = getattr(operator, op)
                unbound = cfg[key].copy(min=-float('inf'), max=float('inf'))
                invalid = opfunc(unbound, value)
                raise CmdError('%s = %s: %s' % (name, self._stringify(invalid), e))

        # Update setting's value
        try:
            if is_local_setting:
                log.debug('Local setting: %r = %r', name, value)
                cfg[key] = value
            else:
                log.debug('Remote setting: %r = %r', name, value)
                await cfg.set(key, value)
        except ValueError as e:
            raise CmdError('%s = %s: %s' % (name, self._stringify(value), e))
        except ClientError as e:
            raise CmdError(e)

    def _parse_name(self, name):
        # Return (name, key, is_local_setting)
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

    @staticmethod
    def _stringify(value):
        from collections.abc import Iterable
        if not isinstance(value, str) and isinstance(value, Iterable):
            return ', '.join(str(item) for item in value)
        else:
            return str(value)


class RateLimitCmdbase(metaclass=InitCommand):
    name = 'ratelimit'
    aliases = ('rate', 'rl')
    provides = set()
    category = 'configuration'
    description = 'Limit transfer rates per torrent or globally'
    usage = ('ratelimit',
             'ratelimit <DIRECTION>',
             'ratelimit <DIRECTION> <LIMIT>',
             'ratelimit <DIRECTION> <LIMIT> <TORRENT FILTER> <TORRENT FILTER> ...')
    examples = ('ratelimit up 5Mb',
                'ratelimit down,up 1M global',
                'ratelimit up,dn off "This torrent" size<100MB')
    argspecs = (
        {'names': ('DIRECTION',), 'nargs': '?', 'default': 'up,down',
         'description': 'Any combination of "up", "down" or "dn" separated by a comma'},

        {'names': ('LIMIT',), 'nargs': '?',
         'description': ('Maximum allowed transfer rate (see `help srv.limit.rate.up` '
                         'for the syntax) or "show" to display the current limit')},

        make_X_FILTER_spec('TORRENT', or_focused=True, nargs='*',
                           more_text=('"global" to set global limit (same as setting '
                                      "srv.limit.rate.<DIRECTION>); may be omitted in CLI mode "
                                      'for the same effect as specifying "global"')),

        { 'names': ('--quiet','-q'), 'action': 'store_true',
          'description': 'Do not show new bandwidth rate(s)' },
    )
    srvapi = ExpectedResource

    async def run(self, DIRECTION, LIMIT, TORRENT_FILTER, quiet):
        directions = tuple('down' if d == 'dn' else d
                           for d in map(str.lower, DIRECTION.split(',')))
        for d in directions:
            if d not in ('up', 'down'):
                raise CmdError('Invalid direction: %r' % (d,))

        # _show_limits() and _set_limits() are defined in cli.config and
        # tui.config because the TUI can use the focused torrent while the CLI
        # can't.
        if not LIMIT or LIMIT == 'show':
            await self._show_limits(TORRENT_FILTER, directions)
        else:
            # Do we adjust current limits or set absolute limits?
            limit = LIMIT.strip()
            if limit[:2] == '+=' or limit[:2] == '-=':
                adjust = True
                limit = limit[0] + limit[2:]  # Remove '=' so it can be parsed as a number
            else:
                adjust = False

            await self._set_limits(TORRENT_FILTER, directions, limit,
                                   adjust=adjust, quiet=quiet)

    async def _show_global_limits(self, directions):
        for d in directions:
            get_method = getattr(self.srvapi.settings, 'get_limit_rate_' + d)
            limit = await get_method()
            self._output('Global %sload rate limit: %s' % (d, limit))

    async def _show_individual_limits(self, TORRENT_FILTER, directions):
        try:
            tfilter = self.select_torrents(TORRENT_FILTER,
                                           allow_no_filter=False,
                                           discover_torrent=True)
        except ValueError as e:
            raise CmdError(e)
        request = self.srvapi.torrent.torrents(
            tfilter, keys=('name', 'limit-rate-up', 'limit-rate-down'))
        response = await self.make_request(request, polling_frenzy=True, quiet=True)
        if response.success:
            for t in response.torrents:
                for d in directions:
                    self._output('%s %sload rate limit: %s' %
                                 (t['name'], d, t['limit-rate-%s' % d]))

    async def _set_global_limits(self, directions, limit, quiet=False, adjust=False):
        for d in directions:
            log.debug('Setting global %s rate limit: %r', d, limit)
            set_method = getattr(self.srvapi.settings,
                                 ('adjust' if adjust else 'set') + '_limit_rate_' + d)
            get_method = getattr(self.srvapi.settings, 'get_limit_rate_' + d)
            try:
                try:
                    await set_method(limit)
                except ValueError as e:
                    raise CmdError('%s: %r' % (e, limit))
                if not quiet:
                    limit = await get_method()
                    self.info('Global %sload rate limit: %s' % (d, limit))
            except ClientError as e:
                raise CmdError(e)

    async def _set_individual_limits(self, TORRENT_FILTER, directions, limit, quiet=False, adjust=False):
        try:
            tfilter = self.select_torrents(TORRENT_FILTER,
                                           allow_no_filter=False,
                                           discover_torrent=True)
        except ValueError as e:
            raise CmdError(e)

        log.debug('Setting %sload rate limit for %s torrents: %r',
                  '+'.join(directions), tfilter, limit)

        success = True
        for d in directions:
            method = getattr(self.srvapi.torrent,
                             ('adjust' if adjust else 'set') + '_limit_rate_' + d)
            response = await self.make_request(method(tfilter, limit),
                                               polling_frenzy=True, quiet=quiet)
            success = success and response.success
        if not success:
            raise CmdError()
