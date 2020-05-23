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

import re
from collections import abc
from typing import Pattern

from natsort import humansorted


class Categories(abc.Sequence):
    """Iterable over non-empty Candidates objects with selection tracking"""

    def __init__(self, *categories):
        self._categories = categories
        self._current_index = 0 if categories else None

    def __getitem__(self, key):
        return tuple(self)[key]

    def __iter__(self):
        for cat in self._categories:
            if len(cat) > 0:
                yield cat

    def __len__(self):
        return len(tuple(iter(self)))

    def next(self):
        """
        Select next candidate in current Candidates or first candidate in next
        Candidates or first candidate in first Candidates
        """
        cats = tuple(self)
        if not cats:
            self.current_index = None
        else:
            if self.current and self.current.current_index < len(self.current) - 1:
                # Move to next candidate in current list
                self.current.next()
            elif self.current_index < len(cats) - 1:
                # Move to first candidate in next list
                self.current_index += 1
                self.current.current_index = 0
            else:
                # Wrap to first candidate in first list
                self.current_index = self.current.current_index = 0

    def prev(self):
        """
        Select previous candidate in current Candidates or last candidate in
        previous Candidates or last candidate in last Candidates
        """
        cats = tuple(self)
        if not cats:
            self.current_index = None
        else:
            if self.current and self.current.current_index > 0:
                # Move to previous candidate in current list
                self.current.prev()
            elif self.current_index > 0:
                # Move to last candidate in previous list
                self.current_index -= 1
                self.current.current_index = len(self.current) - 1
            else:
                # Wrap to last candidate in last list
                self.current_index = len(cats)
                self.current.current_index = len(self.current) - 1

    @property
    def all(self):
        """All Candidates, including empty ones"""
        return self._categories

    @property
    def current_index(self):
        """Index of currently selected Candidates object or None"""
        # Make sure the current index is not pointing to an empty list
        self.current_index = self._current_index
        return self._current_index

    @current_index.setter
    def current_index(self, index):
        if not self:
            self._current_index = None
        elif index is None and self:
            self._current_index = 0
        else:
            self._current_index = max(0, min(index, len(self) - 1))

    @property
    def current(self):
        """Currently selected Candidates object or None"""
        i = self.current_index
        if i is not None:
            return tuple(self)[i]

    def __repr__(self):
        return '%s(%s)' % (type(self).__name__,
                           ', '.join(repr(cands) for cands in self._categories))


class Candidates(abc.Sequence):
    """Sequence of completion candidates"""

    def __init__(self, candidates=(), label='', curarg_seps=()):
        # Remove duplicates while preserving order:
        # https://www.peterbe.com/plog/fastest-way-to-uniquify-a-list-in-python-3.6
        cands_typed = (cand if isinstance(cand, Candidate) else Candidate(cand)
                       for cand in candidates)
        cands_deduped = (cand for cand in dict.fromkeys(cands_typed))
        cands_noempty = (cand for cand in cands_deduped if cand != '')
        cands_sorted = humansorted(cands_noempty)
        self._candidates = tuple(cands_sorted)
        self._matches = self._candidates
        self._curarg_seps = tuple(sorted(curarg_seps))
        self._label = str(label)
        self._current_index = 0 if self._candidates else None

    def __getitem__(self, key):
        return self._matches[key]

    def __len__(self):
        return len(self._matches)

    def next(self):
        """Select next candidate or first one if last is selected"""
        if not self:
            self._current_index = None
        elif self._current_index >= len(self) - 1:
            self._current_index = 0
        else:
            self._current_index += 1

    def prev(self):
        """Select previous candidate or last one if last is selected"""
        if not self:
            self._current_index = None
        elif self._current_index <= 0:
            self._current_index = len(self) - 1
        else:
            self._current_index -= 1

    @property
    def current_index(self):
        """Index of currently selected candidate or None"""
        return self._current_index

    @current_index.setter
    def current_index(self, index):
        if not self._matches:
            self._current_index = None
        elif index is None and self._matches:
            self._current_index = 0
        else:
            self._current_index = max(0, min(index, len(self._matches) - 1))

    @property
    def current(self):
        """Currently selected candidate or None"""
        if self._current_index is not None:
            return self[self._current_index]

    def reduce(self, regex):
        """Reduce the candidates to the ones that match `pattern`"""
        if not isinstance(regex, Pattern):
            regex = re.compile(regex)
        # Remember current candidate so we can keep it selected if possible
        curcand = self.current
        self._matches = tuple(cand for cand in self._candidates
                              if re.search(regex, cand))
        if curcand in self._matches:
            self.current_index = self._matches.index(curcand)
        elif self._matches:
            self.current_index = 0
        else:
            self.current_index = None

    @property
    def curarg_seps(self):
        """
        List of strings at which the current argument should be split before
        applying a candidate from this list
        """
        return self._curarg_seps

    @curarg_seps.setter
    def curarg_seps(self, seps):
        self._curarg_seps = seps

    @property
    def label(self):
        """Category or short description"""
        return self._label

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return (self._candidates == other._candidates and
                self._label == other._label and
                self._curarg_seps == other._curarg_seps)

    def __hash__(self):
        return hash(self._candidates)

    def __repr__(self):
        kwargs = {}
        if self.curarg_seps: kwargs['curarg_seps'] = self.curarg_seps
        if self.label: kwargs['label'] = self.label
        if kwargs:
            return '%s(%r, %s)' % (
                type(self).__name__, self._candidates,
                ', '.join('%s=%r' % (k,v) for k,v in kwargs.items())
            )
        else:
            return '%s(%r)' % (type(self).__name__, self._candidates)


class Candidate(str):
    """A string with some attributes"""

    def __new__(cls, string, **kwargs):
        return super().__new__(cls, string)

    def __init__(self, string, in_parens='', **info):
        # `in_parens` is displayed in parentheses after `string`.
        # `info` is a mapping with extra information, e.g. `Description='This
        # value does that'` or 'Default='<default value>'`.
        self.info = {}
        for title,text in info.items():
            self.info[str(title)] = str(text)
        self.in_parens = str(in_parens)

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return super().__eq__(other)

    def __hash__(self):
        return hash(str(self))

    def __repr__(self):
        kwargs = {}
        if self.in_parens: kwargs['in_parens'] = self.in_parens
        for title,text in self.info.items():
            kwargs[title] = text
        if kwargs:
            return '%s(%r, %s)' % (
                type(self).__name__, str(self),
                ', '.join('%s=%r' % (k,v) for k,v in kwargs.items())
            )
        else:
            return '%s(%r)' % (type(self).__name__, str(self))


class SingleCandidate(Candidates):
    """
    Dummy Candidates that contains only one replacable candidate

    This is used to include current user input in its own category.
    """

    def __init__(self, string, curarg_seps=()):
        super().__init__((string,), curarg_seps=curarg_seps)
        if not self._candidates:
            self._candidates = self._matches = (Candidate(''),)
            self._current_index = 0

    def set(self, string):
        self._candidates = self._matches = \
            (Candidate(string) if not isinstance(string, Candidate) else string,)

    def reduce(self, *args, **kwargs):
        pass

    def __hash__(self):
        return hash(id(self))
