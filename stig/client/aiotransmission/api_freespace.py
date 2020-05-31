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

from ..base import FreeSpaceAPIBase

from ...logging import make_logger  # isort:skip
log = make_logger(__name__)


class FreeSpaceAPI(FreeSpaceAPIBase):
    async def get_free_space(self, path):
        """Return free space in directory `path` in bytes"""
        response = await self._rpc.free_space(path=path)
        log.debug('Free space in %r: %r', path, response)
        if path == response['path']:
            return response['size-bytes']
        else:
            raise RuntimeError('Expected path %r, got %r' % (path, response['path']))
