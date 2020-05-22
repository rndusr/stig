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

from functools import partial

from ...logging import make_logger  # isort:skip
log = make_logger(__name__)


class SortSpec():
    def __init__(self, *keyfuncs, description, aliases=()):
        self._keyfuncs = keyfuncs
        self.description = description
        self.aliases = aliases

    def __call__(self, items, reverse=False, inplace=False, item_getter=lambda item: item):
        if not items:
            return items

        for keyfunc in self._keyfuncs:
            def key_getter(item):
                return keyfunc(item_getter(item))

            if inplace:
                items[:] = sorted(items, key=key_getter, reverse=reverse)
            else:
                items = sorted(items, key=key_getter, reverse=reverse)

        return items


class _SorterBaseMeta(type):
    def __init__(cls, clsname, bases, attrs):
        sortspecs = getattr(cls, 'SORTSPECS', None)
        if sortspecs is None:
            raise RuntimeError('%s: Missing SORTSPECS attribute' % (clsname,))
        elif sortspecs is NotImplemented:
            # No aliases for base class
            cls._aliases = {}
        else:
            # Get list of aliases from sort specs and map each one to the real
            # sorter name
            cls._aliases = {alias:sorter_name
                            for sorter_name,sortspec in sortspecs.items()
                            for alias in sortspec.aliases}


class SorterBase(metaclass=_SorterBaseMeta):
    INVERT_CHARS = ('!', '.')
    SORTSPECS = NotImplemented
    DEFAULT_SORT = None

    def __init__(self, sortstrings=()):
        sortspecs = []
        sortfuncs = []
        strings = []   # String representations of sortspecs

        # Go through items in reverse because we want to deduplicate sort orders
        # while keeping the most recent one.
        for sortstring in reversed(sortstrings):
            if sortstring[0] in self.INVERT_CHARS:
                sortspecname, reverse = sortstring[1:], True
            else:
                sortspecname, reverse = sortstring, False

            # Resolve alias
            if sortspecname in self._aliases:
                sortspecname = self._aliases[sortspecname]

            if sortspecname not in self.SORTSPECS:
                raise ValueError('Unknown sort order: {!r}'.format(sortspecname))
            else:
                sortspec = self.SORTSPECS[sortspecname]
                if sortspec not in sortspecs:
                    sortfunc = partial(sortspec, reverse=reverse)
                    sortspecs.insert(0, sortspec)
                    sortfuncs.insert(0, sortfunc)
                    strings.insert(0, (self.INVERT_CHARS[0] if reverse else '') + sortspecname)
        self._strings = tuple(strings)

        # Unless we already sort by DEFAULT_SORT, insert it as the first one.
        if self.DEFAULT_SORT is not None:
            default_sortspec = self.SORTSPECS[self.DEFAULT_SORT]
            if default_sortspec not in sortspecs:
                sortfuncs.insert(0, default_sortspec)
                sortspecs.insert(0, default_sortspec)

        self._sortspecs = sortspecs
        self._sortfuncs = sortfuncs

    def apply(self, items, inplace=False, item_getter=lambda item: item):
        """
        Sort sequence `items`

        item_getter: Callable that gets an item of `items` and returns an
                     object that can be sorted with any of the sorters
                     specified in the SORTSPECS variable. (This allows for
                     sorting of widgets as long as they can provide a sortable
                     object.)
        inplace: Modify `items` if True, otherwise return a new, sorted list
        """
        import time
        start_time = time.monotonic()

        for sorter in self._sortfuncs:
            items = sorter(items, inplace=inplace, item_getter=item_getter)

        log.debug('-> Sorted %d items by %s in %.3fms',
                  len(items), self, (time.monotonic() - start_time) * 1e3)

        if not inplace:
            return items

    def __add__(self, other):
        cls = type(self)
        if not isinstance(other, cls):
            return NotImplemented
        else:
            return cls(self._strings + other._strings)

    def __sub__(self, other):
        cls = type(self)
        if not isinstance(other, cls):
            return NotImplemented
        else:
            invchars = ''.join(self.INVERT_CHARS)
            other_strings = tuple(s.lstrip(invchars) for s in other._strings)
            return cls(tuple(s for s in self._strings
                             if s.lstrip(invchars) not in other_strings))

    def __str__(self):
        return ','.join(self._strings)

    def __repr__(self):
        return '%s(%r)' % (type(self).__name__, self._strings)
