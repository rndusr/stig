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


# Abuse some *Value classes from the settings to allow the same user-input for
# individual torrents as we do for the global settings srv.limit.rate.*.
from ...settings.types_srv import (MultiValue, BooleanValue, UnlimitedValue, BandwidthValue)
class TorrentRateLimitValue(MultiValue(UnlimitedValue, BandwidthValue, BooleanValue)):
    pass

class RateLimitCmdbase(metaclass=InitCommand):
    name = 'ratelimit'
    aliases = ('rate',)
    provides = set()
    category = 'configuration'
    description = "Limit up-/download rate per torrent or globally"
    usage = ('rate <DIRECTION> <LIMIT>',
             'rate <DIRECTION> <LIMIT> <TORRENT FILTER> <TORRENT FILTER> ...')
    examples = ('rate up 5Mb',
                'rate down,up 1MB global',
                'rate up,dn off "This torrent" size<100MB')
    argspecs = (
        {'names': ('DIRECTION',),
         'description': 'Any combination of "up", "down" or "dn" separated by a comma'},
        {'names': ('LIMIT',),
         'description': ('Maximum allowed transfer rate; see `help srv.limit.rate.up` for the syntax')},
        make_X_FILTER_spec('TORRENT', or_focused=True, nargs='*',
                           more_text=('"global" to set global limit (same as setting '
                                      "srv.limit.rate.<DIRECTION>'); may be omitted in CLI mode "
                                      'for the same effect as specifying "global"')),
    )
    srvapi = ExpectedResource
    cmdmgr = ExpectedResource

    async def run(self, DIRECTION, LIMIT, TORRENT_FILTER):
        directions = tuple('down' if d == 'dn' else d
                           for d in map(str.lower, DIRECTION.split(',')))
        for d in directions:
            if d not in ('up', 'down'):
                log.error('%s: Invalid item in argument DIRECTION: %r', self.name, d)
                return False

        return await self._set_limits(TORRENT_FILTER, directions, LIMIT)

    async def _set_global_limit(self, directions, LIMIT):
        # Change the srv.limit.rate.* setting for each direction
        log.debug('Setting global %s rate limit: %r', '/'.join(directions), LIMIT)
        for d in directions:
            success = await self.cmdmgr.run_async('set srv.limit.rate.%s %s' % (d, LIMIT),
                                                  block=True)
            if not success:
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

        # Do we adjust current limits or set absolute limits?
        if LIMIT[:2] == '+=' or LIMIT[:2] == '-=':
            method_start = 'adjust_rate_limit_'
            limit = LIMIT[0] + LIMIT[2:]  # Remove '=' so it can be parsed as a number
        else:
            method_start = 'set_rate_limit_'
            limit = LIMIT

        try:
            new_limit = TorrentRateLimitValue('_new_limit', default=limit).get()
        except ValueError as e:
            log.error('%s: %r', e, limit)
            return False

        log.debug('Setting %s rate limit for %s torrents: %r',
                  '+'.join(directions), tfilter, new_limit)

        for d in directions:
            method = getattr(self.srvapi.torrent, method_start + d)
            response = await self.make_request(method(tfilter, new_limit),
                                               polling_frenzy=True)
            if not response.success:
                return False
        return True
