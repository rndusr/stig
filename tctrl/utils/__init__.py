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


import re
def natsortkey(key):
    """Provide this as the 'key' argument to `list.sort`, `sorted`, etc.

    Pilfered from
    <https://blog.codinghorror.com/sorting-for-humans-natural-sort-order/>
    and adapted.
    """
    convert = lambda text: int(text) if isinstance(text, str) and text.isdigit() else text
    return [convert(c) for c in re.split('([0-9]+)', key)]


def striplines(lines):
    """Remove empty strings from start and end of `lines` using `pop`"""
    lines = list(lines)
    while lines and lines[0] == '':
        lines.pop(0)
    while lines and lines[-1] == '':
        lines.pop(-1)
    yield from lines
