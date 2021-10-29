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

from .. import __appname__, __version__, objects
from pathlib import Path
from bidict import bidict, ValueDuplicationError

from ..logging import make_logger  # isort:skip

log = make_logger(__name__)


class PathTranslator:
    def __init__(self):
        # links: a dict of (remote_root, local_root) pairs
        self.links = bidict()

    def link(self, remote, local, force=False):
        remote = Path(remote)
        local =  Path(local)
        if not local.exists():
            raise ValueError("Local path %s does not exist." % local)
        if not local.is_absolute():
            raise ValueError("Local path %s must be absolute." % local)
        if not remote.is_absolute():
            raise ValueError("Local path %s must be absolute." % remote)
        if force:
            self.links.forceput(remote, local)
        if remote in self.links.keys():
            raise ValueError(
                "Remote path %s is already linked to local path %s."
                % (remote, self.links[remote])
            )
        try:
            self.links[remote] = local
        except ValueDuplicationError:
            raise ValueError(
                "Local path %s is already linked to remote path %s."
                % (local, self.links[remote])
            )
        log.debug("Linked remote path %s to local path %s" % (remote, local))

    def _translate_path(self, path, links):
        for roots in links.items():
            try:
                return roots[1] / path.relative_to(roots[0])
            except ValueError:
                pass
        return path

    def to_local(self, p_rem):
        return self._translate_path(p_rem, self.links)

    def to_remote(self, p_loc):
        return self._translate_path(p_loc, self.links.inv)
