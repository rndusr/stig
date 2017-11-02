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

"""Display specifications for tables and such"""

from ..logging import make_logger
log = make_logger(__name__)

from ..utils import stralign
from collections import defaultdict
from time import time


class ColumnBase():
    header = {'left': '', 'right': ''}
    width = None
    min_width = 1
    align = 'right'
    interfaces = ('cli', 'tui')
    may_have_wide_chars = False

    def __init__(self, data=None):
        self.data = data if data is not None else {}
        super().__init__()

    _cache = defaultdict(lambda: {'value': None, 'last_hit': time(), 'hits': 0})
    _last_cache_prune = 0
    def _from_cache(self, create_value, *args):
        cache_id = (create_value, args)
        if cache_id not in self._cache:
            # log.debug('Calling %r with %r', create_value.__qualname__, args)
            value = self._cache[cache_id]['value'] = create_value(*args)
        else:
            cache_item = self._cache[cache_id]
            value = cache_item['value']
            cache_item['last_hit'] = time()

            # Remove any cached items that haven't been used recently
            now = time()
            if now-ColumnBase._last_cache_prune > 60:
                ColumnBase._last_cache_prune = now

                prune_counter = 0
                for cid,citem in tuple(self._cache.items()):
                    if now-citem['last_hit'] > 600:
                        del self._cache[cid]
                        prune_counter += 1

                # # Debugging stuff
                # items_without_hits = tuple(citem for citem in self._cache.values()
                #                            if citem['hits'] < 1)

                # log.debug('Cell cache: %r values pruned, %r remaining, '
                #           '%r with no hits, %r hits combined',
                #           prune_counter, len(self._cache), len(items_without_hits),
                #           sum((citem['hits'] for citem in self._cache.values())))


                # items_with_hits = tuple(citem for citem in self._cache.values()
                #                         if citem['hits'] > 0)
                # from time import (strftime, localtime)
                # for citem in items_with_hits:
                #     log.debug('  %5d hits, last hit: %s: %s',
                #               citem['hits'],
                #               strftime('%H:%M:%S', localtime(citem['last_hit'])),
                #               citem['value'])
        return value

    def get_value(self):
        raise NotImplementedError()

    def get_raw(self):
        return self.get_value()

    def get_string(self):
        """Return `get_value` as spaced and aligned string

        If the `width` attribute is not set to None, expand or shrink and
        align the returned string (`align` attribute must be 'left' or
        'right').
        """
        def crop_and_align(string, width, align):
            if isinstance(width, int):
                # Cropping and justifying is more expensive when there are wide
                # characters involved
                if self.may_have_wide_chars:
                    string = stralign(string, width, align)
                else:
                    err = TypeError("'align' attribute must be 'left' or 'right', not %r}" % align)
                    string_len = len(string)
                    if string_len > width:
                        if align == 'right':
                            string = string[string_len-width:]
                        elif align == 'left':
                            string = string[:width]
                        else:
                            raise err
                    else:
                        if align == 'right':
                            string = string.rjust(width)
                        elif align == 'left':
                            string = string.ljust(width)
                        else:
                            raise err
            return string

        return self._from_cache(crop_and_align, str(self.get_value()),
                                self.width, self.align)

    def __repr__(self):
        if self.data:
            return '<{} {}>'.format(type(self).__name__, self.get_value())
        else:
            return '<{} <UNINITIALIZED>>'.format(type(self).__name__)


def _ensure_string_without_unit(value):
    # We don't want to display the unit (e.g. 'B' or 'b' for file size or
    # transfer rate) in each cell; it's already displayed in the column header.
    if hasattr(value, 'str_includes_unit'):
        return type(value)(value, str_includes_unit=False)
    else:
        return value
