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

import os

from ..utils import string
from .defaults import DEFAULT_RCFILE

from ..logging import make_logger  # isort:skip
log = make_logger(__name__)


def _unescape_linebreaks(lines):
    unescaped = []
    append_next = False
    for line in lines:
        if append_next:
            unescaped[-1] += line
        else:
            unescaped.append(line)

        if unescaped[-1][-1] == '\\':
            unescaped[-1] = unescaped[-1][:-1]
            append_next = True
        else:
            append_next = False

    return unescaped


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
        if string.tildify(filepath) == string.tildify(DEFAULT_RCFILE):
            return ()  # Missing default rc file is not an error
        else:
            raise RcFileError('File not found: {}'.format(string.tildify(filepath)))

    except PermissionError:
        raise RcFileError('No read permission for rc file: {}'.format(string.tildify(filepath)))

    return _unescape_linebreaks(cmdstrs)
