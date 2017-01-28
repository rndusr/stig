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

from ..logging import make_logger
log = make_logger(__name__)

import os

from .defaults import DEFAULT_RCFILE


def _tildify(p):
    if p.startswith(os.environ['HOME']):
        return '~' + p[len(os.environ['HOME']):]
    return p


class RcFileError(Exception):
    pass


def read(filepath=DEFAULT_RCFILE):
    """Read list of commands from file"""
    filepath = os.path.expanduser(filepath)
    log.debug('Reading rc file: %r', filepath)
    try:
        with open(filepath, 'r') as f:
            cmdstrs = (line
                       for line in (line.strip() for line in f.readlines())
                       if line and not line.startswith('#'))

    except FileNotFoundError:
        if _tildify(filepath) == _tildify(DEFAULT_RCFILE):
            return ()  # Missing default rc file is not an error
        else:
            raise RcFileError('File not found: {}'.format(_tildify(filepath)))

    except PermissionError as e:
        raise RcFileError('No read permission for rc file: {}'.format(_tildify(filepath)))

    return cmdstrs
