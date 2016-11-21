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


from types import SimpleNamespace
class Response(SimpleNamespace):
    """Response to an API call

    All API implementations should use this class to provide return values to
    API calls.

    success: Whether the call was a success
    msgs: Sequence of messages; either strings or ClientError exceptions

    Any other keyword arguments are made available as attributes.
    """
    def __init__(self, success=False, msgs=(), **kwargs):
        super().__init__(success=bool(success), msgs=tuple(msgs), **kwargs)


from urllib.parse import urlsplit
class split_url():
    """Works like `urllib.parse.urlsplit` but with a 'domain' attribute"""
    def __new__(cls, url):
        obj = super().__new__(cls)

        # Use urlsplit to get most fields
        url = urlsplit(url)
        for attr in dir(url):
            if not attr.startswith('_'):
                setattr(obj, attr, getattr(url, attr))

        # Find domain
        if url.hostname.count('.') <= 1:
            obj.domain = url.hostname
        else:
            parts = url.hostname.split('.')
            obj.domain = '.'.join(parts[-2:])
        return obj


def pretty_float(n):
    """Format number with a reasonable amount of decimal places"""
    n_abs = round(abs(n), 2)
    n_abs_int = int(n_abs)
    if n_abs == 0:
        return '0'
    elif n_abs == n_abs_int:
        return '%.0f' % n
    elif n_abs < 10:
        return '%.2f' % n
    elif n_abs < 100:
        return '%.1f' % n
    else:
        return '%.0f' % n


def pluralize(word, n):
    """Return `word`+'s' if n != 1, `word` otherwise"""
    return word+'s' if abs(n) != 1 else word
