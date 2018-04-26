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

from collections import defaultdict
from time import time


class ColumnBase():
    header = {'left': '', 'right': ''}
    width = None
    min_width = 1
    align = 'right'
    wrap = 'clip'
    interfaces = ('cli', 'tui')
    may_have_wide_chars = False

    def __init__(self, data=None):
        self.data = data if data is not None else {}
        super().__init__()

    # _cache = defaultdict(lambda: {'value': None, 'last_hit': time(), 'hits': 0})
    _cache = defaultdict(lambda: {'value': None, 'last_hit': time()})
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
            # cache_item['hits'] += 1

            # Remove any cached items that haven't been used recently
            now = time()
            if now-ColumnBase._last_cache_prune > 60:
                ColumnBase._last_cache_prune = now

                # prune_counter = 0
                for cid,citem in tuple(self._cache.items()):
                    if now-citem['last_hit'] > 600:
                        del self._cache[cid]
                        # prune_counter += 1

                # # Debugging stuff; also uncomment the lines containing
                # # 'prune_counter' and 'hits'
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

    @classmethod
    def clearcache(cls):
        cls._cache.clear()

    def get_value(self):
        raise NotImplementedError()

    def get_cli_value(self):
        return self.get_value()

    def get_tui_value(self):
        return self.get_value()

    def get_raw_value(self):
        value = self.get_value()
        if isinstance(value, (int, float)) and value < float('inf'):
            return repr(value)
        else:
            return value

    def __repr__(self):
        if getattr(self, 'data', None):
            return '<{} {}>'.format(type(self).__name__, self.get_value())
        else:
            return '<{} <UNINITIALIZED>>'.format(type(self).__name__)

def _ensure_hide_unit(value):
    return type(value)(value, hide_unit=True)
