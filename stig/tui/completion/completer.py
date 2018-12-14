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

from ...logging import make_logger
log = make_logger(__name__)

import re
from collections import abc

from . import _utils
from ...completion import (Candidates, Candidate)


class Completer():
    """
    Parse command line and provide completion candidates and methods
    """
    def get_candidates(self, args, curarg_index):
        """
        Return completion candidates for given arguments and optionally a separator
        for the currently focused argument (e.g. "/" to split paths).
        Completion candidates can be `None` or any iteratable of strings.
        """
        raise NotImplementedError()

    def _get_candidates_wrapper(self, *args, **kwargs):
        result = self.get_candidates(*args, **kwargs)
        if result is None:
            return Candidates(), None
        elif not isinstance(result, abc.Sequence):
            try:
                result = tuple(result)
            except Exception:
                raise RuntimeError('Not an iterable: %r', result)

        if len(result) == 2:
            if isinstance(result[0], str):
                # result is the candidates
                cands = result
                arg_sep = None
            else:
                # result[0] is the candidates, result[1] is the argument separator
                cands, arg_sep = result
        else:
            cands, arg_sep = result, None

        if cands is None:
            cands = Candidates()
        elif not isinstance(cands, Candidates):
            cands = Candidates(*cands)
        return cands, arg_sep

    def __init__(self, operators=()):
        self.operators = operators
        self.reset()

    def reset(self):
        self._tokens = ()
        self._candidates = Candidates()
        self._curpos = 0
        self._curtok_index = None
        self._curtok_curpos = None

    def update(self, cmdline, curpos):
        log.debug('Parsing: %r', cmdline[:curpos] + '|' + cmdline[curpos:])
        tokens, curtok_index, curtok_curpos = _utils.get_position(_utils.tokenize(cmdline), curpos)
        log.debug('Tokens: %r', tokens)
        curcmd_tokens, curcmd_curtok_index = _utils.get_current_cmd(tokens, curtok_index, self._operators)
        log.debug('Current command tokens: %r', curcmd_tokens)
        log.debug('Focused token: %r', curcmd_curtok_index)
        if curcmd_tokens is None:
            log.debug('No current command - no candidates')
            self.reset()
            return

        # The candidate getter gets unescaped/unquoted tokens with delimiting
        # spaces removed (i.e. "arguments" or what would appear in sys.argv).
        # The cursor position and the index of the current argument may also
        # need to be adjusted for that.
        curcmd_args, curcmd_curarg_index, curarg_curpos = \
            _utils.as_args(curcmd_tokens, curcmd_curtok_index, curtok_curpos)
        curarg = curcmd_args[curcmd_curarg_index]

        # Get all possible completion candidates
        all_cands, arg_sep = self._get_candidates_wrapper(curcmd_args, curcmd_curarg_index)
        if arg_sep is not None:
            curarg.sep = arg_sep
        log.debug('All Candidates: %r', all_cands)

        # The candidate getter may have split the current argument, e.g. at each
        # "/" to complete individual parts of a path.  The Arg instance
        # remembers that and we can easily get common_prefix for that particular
        # part of the current argument.  If the argument wasn't split, curarg's
        # attributes refer to the whole argument and we can use the same method.
        log.debug('Current argument part: %r', curarg.curpart)
        common_prefix = curarg.curpart[:curarg.curpart_curpos]
        log.debug('Common prefix: %r', common_prefix)

        # Filter out any candidates that don't match the current argument up to
        # the cursor
        matching_cands = all_cands.reduce(common_prefix=common_prefix)

        # If there are any matching candidates, include the current argument as
        # a candidate so the user can cycle to their original input when
        # selecting candidates.
        if matching_cands and curarg not in matching_cands:
            curarg_cand = Candidate(curarg.curpart, curpos=curarg_curpos)
            cands_with_current_user_input = (curarg_cand,) + matching_cands.sorted()
            self._candidates = matching_cands.copy(*cands_with_current_user_input,
                                                   current_index=0)
        else:
            self._candidates = matching_cands.sorted(preserve_current=False)
        log.debug('Candidates: %r', self._candidates)

        # Finally, we also split the current token like the candidate getter
        # previously told us to so we can insert candidates in
        # complete_next/prev() without replacing the whole argument.
        curtok_delims = (curarg.sep,)
        curtok_parts, curpart_index, curpart_curpos = \
            _utils.get_position(_utils.tokenize(tokens[curtok_index], curtok_delims),
                                curtok_curpos, curtok_delims)
        log.debug('Separated current token: %r', curtok_parts)
        tokens[curtok_index:curtok_index+1] = curtok_parts
        curtok_index += curpart_index
        curtok_curpos = curpart_curpos
        log.debug('Tokens with separated argument: %r', tokens)
        log.debug('New current token: %r: %r', curtok_index, tokens[curtok_index])
        log.debug('New current token cursor position: %r', curtok_curpos)

        # Preserve stuff we need for re-assembling the command line
        self._curpos = curpos
        self._tokens = tokens
        self._curtok_index = curtok_index
        self._curtok_curpos = curtok_curpos
        self._arg_sep = curarg.sep

    def complete_next(self):
        """
        Fill in next completion candidate

        Return new command line and cursor position
        """
        self._candidates.next()
        log.debug('Selected next candidate: %r', self._candidates.current)
        return self._assemble_cmdline()

    def complete_prev(self):
        """
        Select previous completion candidate

        Return new command line and cursor position
        """
        self._candidates.prev()
        log.debug('Selected previous candidate: %r', self._candidates.current)
        return self._assemble_cmdline()

    def _assemble_cmdline(self):
        """
        Apply currently selected candidte to command line

        Return new command line string and adjusted cursor position
        """
        log.debug('Assembling %r', self._tokens)
        if self._candidates.current is None:
            # Return original, unmodified command line
            return ''.join(self._tokens), self._curpos
        else:
            # Insert current candidate into tokens
            tokens = list(self._tokens)
            curtok_index = self._curtok_index
            curtok = tokens[curtok_index]
            cand = self._candidates.current
            if _utils.is_escaped(curtok):
                cand_clisafe, cand_curpos = _utils.escape(cand, curpos=cand.curpos)
            else:
                cand_clisafe, cand_curpos = _utils.quote(cand, curpos=cand.curpos)
            new_curpos = self._curpos - self._curtok_curpos + cand_curpos

            # # If the cursor is on a delimiter, we can't just replace the current
            # # candidate with the current token or we're concatenating arguments
            # # by removing whitspace.
            # if curtok.isspace():
            #     spaces_before_cursor = curtok[:self._curtok_curpos]
            #     spaces_after_cursor = curtok[self._curtok_curpos:]
            #     log.debug('Replacing %r with %r', tokens[curtok_index],
            #               (spaces_before_cursor, cand_clisafe, spaces_after_cursor))
            #     tokens[curtok_index:curtok_index+1] = (spaces_before_cursor, cand_clisafe, spaces_after_cursor)
            #     new_curpos += len(spaces_before_cursor)
            # else:
            #     log.debug('Replacing %r with %r', tokens[curtok_index], cand_clisafe)
            #     tokens[curtok_index] = cand_clisafe
            log.debug('Replacing %r with %r', tokens[curtok_index], cand_clisafe)
            tokens[curtok_index] = cand_clisafe

            log.debug('Assembled: %r', ''.join(tokens[:new_curpos]) + '|' + ''.join(tokens[new_curpos:]))
            return ''.join(tokens), new_curpos

    @property
    def candidates(self):
        """Sequence of strings that are valid for the current argument"""
        return self._candidates

    @property
    def operators(self):
        """Sequence of strings that functions as delimiters between commands"""
        return self._operators
    @operators.setter
    def operators(self, operators):
        self._operators = tuple(operators)
