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


class Candidate(str):
    """A string with a cursor position"""

    def __new__(cls, string, curpos=None):
        obj = super().__new__(cls, string)
        obj.curpos = curpos if curpos is not None else len(obj)
        return obj


class Candidates(tuple):
    """Iterable of candidates"""

    def __new__(cls, *candidates, sep=None, current_index=None):
        # Remove duplicates while preserving order:
        # https://www.peterbe.com/plog/fastest-way-to-uniquify-a-list-in-python-3.6
        obj = super().__new__(cls, (Candidate(c) for c in dict.fromkeys(candidates)))
        obj.sep = sep
        if current_index is not None:
            obj.current_index = current_index if len(obj) > 0 else None
        else:
            obj.current_index = 0 if len(obj) > 0 else None
        return obj

    def next(self):
        len_self = len(self)
        if len_self > 0:
            if self.current_index < len_self - 1:
                self.current_index += 1
            else:
                self.current_index = 0
        return self.current_index

    def prev(self):
        len_self = len(self)
        if len_self > 0:
            if self.current_index > 0:
                self.current_index -= 1
            else:
                self.current_index = len_self - 1
        return self.current_index

    @property
    def current_index(self):
        return self._current_index
    @current_index.setter
    def current_index(self, index):
        if len(self) == 0:
            assert index is None, 'current_index can only be None with no candidates'
            self._current_index = None
        elif len(self) > index >= 0:
            self._current_index = index
        else:
            raise IndexError('Invalid current_index: %r' % (index,))

    @property
    def current(self):
        if self.current_index is None:
            return None
        else:
            return self[self.current_index]

    def copy(self, *candidates, **kwargs):
        if not candidates:
            candidates = self
        elif len(candidates) == 1 and len(candidates[0]) == 0:
            candidates = ()

        kwargs.setdefault('sep', self.sep)
        try:
            kwargs.setdefault('current_index', candidates.index(self.current))
        except ValueError:
            pass
        return type(self)(*candidates, **kwargs)

    def reduce(self, common_prefix, case_sensitive=False):
        """Return copy that contains only candidates that start with `common_prefix`"""
        if case_sensitive:
            matches = tuple(cand for cand in self
                            if cand.startswith(common_prefix))
        else:
            matches = tuple(cand for cand in self
                            if cand.casefold().startswith(common_prefix.casefold()))

        if matches:
            return self.copy(*matches)
        else:
            return self.copy(())

    def sorted(self, key=None, preserve_current=True):
        if self:
            new_cands = sorted(self, key=key)
            if preserve_current:
                return self.copy(*new_cands)
            else:
                return self.copy(*new_cands, current_index=None)
        else:
            return self.copy()

    def __repr__(self):
        kwargs = {'current_index': self.current_index}
        if self.sep is not None:
            kwargs['sep'] = self.sep
        return '%s(%s, %s)' % (
            type(self).__name__,
            ', '.join(repr(c) for c in self) if self else (),
            ', '.join('%s=%r' % (k,v) for k,v in kwargs.items())
        )
