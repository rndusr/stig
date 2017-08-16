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


class RateLimitCmdbase(metaclass=InitCommand):
    name = 'rate'
    aliases = ()
    provides = set()
    category = 'configuration'
    description = "Limit up-/download rate per torrent or globally"
    usage = ('rate <DIRECTION> <LIMIT>',
             'rate <DIRECTION> <LIMIT> [<TORRENT FILTER> <TORRENT FILTER> ...]')
    examples = ('rate up 5Mb',
                'rate up,down - "This torrent" size<100MB',
                'rate down,up 1MB global')
    argspecs = (
        {'names': ('DIRECTION',),
         'description': '"up", "down" or both separated by a comma'},

        {'names': ('LIMIT',),
         'description': ('Maximum allowed rate limit; metric (k, M, G, etc) and binary (Ki, Mi, Gi, etc) '
                         'unit prefixes are supported (case is ignored); append "b" for bits, "B" for bytes '
                         'or nothing for whatever \'unit.bandwidth\' is set to; "none", "-" and '
                         'negative numbers disable the limit; if TORRENT FILTER is "global", any valid '
                         '\'srv.limit.rate.up/down\' setting is accepted (see `help srv.limit.rate.up`)')},

        {'names': ('TORRENT FILTER',), 'nargs': '*',
         'description': ('Filter expression (see `help filter`), "global" to set '
                         '\'srv.limit.rate.<DIRECTION>\' or focused torrent in the TUI')},
    )
    srvapi = ExpectedResource
    cmdmgr = ExpectedResource

    async def run(self, DIRECTION, LIMIT, TORRENT_FILTER):
        direction = tuple(map(str.lower, DIRECTION.split(',')))
        for d in direction:
            if d not in ('up', 'down'):
                log.error('%s: Invalid item in argument DIRECTION: %r', self.name, d)
                return False

        if TORRENT_FILTER == ['global']:
            if LIMIT in ('none', '-'):
                LIMIT = 'disable'
            for d in direction:
                success = await self.cmdmgr.run_async('set srv.limit.rate.%s %s' % (d, LIMIT),
                                                      block=True)
                if not success:
                    return False
            return True

        try:
            tfilter = self.select_torrents(TORRENT_FILTER,
                                           allow_no_filter=False,
                                           discover_torrent=True)
        except ValueError as e:
            log.error(e)
            return False
        else:
            if LIMIT in ('none', '-'):
                LIMIT = None

            for d in direction:
                method = getattr(self.srvapi.torrent, 'limit_rate_'+d)
                try:
                    response = await self.make_request(method(tfilter, LIMIT),
                                                       polling_frenzy=True)
                except ValueError as e:
                    log.error(e)
                    return False
                if not response.success:
                    return False
            return True
