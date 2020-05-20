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

import inspect
import re
from collections import abc

from ..completion import Candidates, Categories, SingleCandidate
from ..utils import cliparser

from ..logging import make_logger  # isort:skip
log = make_logger(__name__)


class Completer():
    """Parse command line and provide completion candidates and methods"""

    def __init__(self, get_candidates, operators=()):
        assert callable(get_candidates), 'Not callable: %r' % get_candidates
        self._get_candidates = get_candidates
        self._operators = operators
        self.reset()

    async def _get_candidates_wrapper(self, args):
        async def maybe_await(x):
            while inspect.isawaitable(x):
                x = await x
            return x

        cands = await maybe_await(self._get_candidates(args))
        if cands is None:
            cats = ()
        elif isinstance(cands, Candidates):
            cats = (cands,)
        elif isinstance(cands, (abc.Iterable, abc.Iterator)):
            def flatten(iters):
                # Only yield Candidates instances
                for item in iters:
                    if item is None:
                        pass
                    elif isinstance(item, Candidates):
                        yield item
                    elif isinstance(item, abc.Iterable) and not isinstance(item, str):
                        yield from flatten(item)
                    else:
                        raise RuntimeError('Not a Candidates object or iterable of Candidates objects: %r' % (item,))
            cats = tuple(flatten(cands))
        else:
            raise RuntimeError('Invalid candidates: %r' % (cands,))

        # Include current user input (this is filled in later when the current
        # command line is parsed)
        return Categories(SingleCandidate(''), *cats)

    def reset(self):
        self._tokens = ()
        self._categories = Categories()  # Tuple of Candidates objects
        self._curpos = 0
        self._curtok_index = None
        self._curtok_curpos = None

    async def update(self, cmdline, curpos):
        # log.debug('Parsing: %r', cmdline[:curpos] + '|' + cmdline[curpos:])
        tokens = cliparser.tokenize(cmdline)
        curtok_index, curtok_curpos = cliparser.get_position(tokens, curpos)
        tokens, curtok_index, curtok_curpos = cliparser.maybe_insert_empty_token(tokens, curtok_index, curtok_curpos)
        tokens, curtok_index, curtok_curpos = cliparser.avoid_delims(tokens, curtok_index, curtok_curpos)
        # log.debug('Tokens: %r', tokens)
        curcmd_tokens, curcmd_curtok_index = cliparser.get_current_cmd(tokens, curtok_index, self._operators)
        # log.debug('Current command tokens: %r', curcmd_tokens)
        # log.debug('Focused token: %r', curcmd_curtok_index)
        if curcmd_tokens is None:
            # log.debug('No current command - no candidates')
            self.reset()
        else:
            # The candidate getter gets unescaped/unquoted tokens with delimiting
            # spaces removed (i.e. "arguments" or what would appear in sys.argv).
            # The cursor position and the index of the current argument may need to
            # be adjusted.
            args = cliparser.Args.from_tokens(curcmd_tokens, curcmd_curtok_index, curtok_curpos)

            # Get all possible candidates and find matches
            self._categories = await self._get_candidates_wrapper(args)
            self._curarg_parts = {}
            for cands in self._categories.all:
                # The candidate getter may have specified custom separators for
                # the current argument to guide us when inserting a replacement,
                # e.g. paths are separated at "/" and we don't want to complete
                # the full path, just the part between two "/".
                if cands.curarg_seps:
                    # log.debug('  Separators for current argument: %r', cands.curarg_seps)
                    curarg_parts = args.curarg.separate(cands.curarg_seps, include_seps=True)
                    # log.debug('  Current argument parts: %r', curarg_parts)
                    common_prefix = curarg_parts.curarg.before_cursor
                else:
                    common_prefix = args.curarg.before_cursor
                self._curarg_parts[cands] = common_prefix

                # log.debug('Common prefix: %r', common_prefix)
                # Filter out any candidates that don't match the current argument
                cands.reduce(r'(?i)%s' % (re.escape(common_prefix),))

            # Include current user input as the first candidate so the user can
            # select it again after selecting other candidates
            self._update_current_user_input()

            # Preserve some stuff we need for re-assembling the command line
            self._tokens = tokens
            self._curpos = curpos
            self._curtok_index = curtok_index
            self._curtok_curpos = curtok_curpos

    def complete_next(self):
        """
        Fill in next completion candidate

        Return new command line and cursor position
        """
        self.categories.next()
        self._update_current_user_input()
        return self._assemble_cmdline()

    def complete_prev(self):
        """
        Select previous completion candidate

        Return new command line and cursor position
        """
        self.categories.prev()
        self._update_current_user_input()
        return self._assemble_cmdline()

    def _assemble_cmdline(self):
        """
        Apply currently selected candidate to command line

        Return new command line string and adjusted cursor position
        """
        # log.debug('Assembling %r', self._tokens)
        if not self.categories.current:
            # Return original, unmodified command line
            return ''.join(self._tokens), self._curpos
        else:
            # Split the current token as specified by the current Candidates
            # object so we can replace part of an argument, e.g. a directory in
            # a path.
            curtok = self._tokens[self._curtok_index]
            curarg_seps = self.categories.current.curarg_seps
            curtok_parts = cliparser.tokenize(curtok, delims=curarg_seps)
            curpart_index, curpart_curpos = cliparser.get_position(curtok_parts, self._curtok_curpos)
            curtok_parts, curpart_index, curpart_curpos = \
                cliparser.maybe_insert_empty_token(curtok_parts, curpart_index, curpart_curpos, curarg_seps)
            curtok_parts, curpart_index, curpart_curpos = \
                cliparser.avoid_delims(curtok_parts, curpart_index, curpart_curpos, curarg_seps)
            # log.debug('Separated current token: %r', curtok_parts)
            self._tokens[self._curtok_index : self._curtok_index + 1] = curtok_parts
            self._curtok_index += curpart_index
            self._curtok_curpos = curpart_curpos
            # log.debug('Tokens with separated argument: %r', self._tokens)
            # log.debug('New current token: %r: %r', self._curtok_index, self._tokens[self._curtok_index])
            # log.debug('New current token cursor position: %r', self._curtok_curpos)

            # Copy user-typed tokens and insert current candidate
            curcands = self.categories.current
            curcand = curcands.current
            tokens = list(self._tokens)
            curtok = self._tokens[self._curtok_index]

            if cliparser.is_escaped(curtok):
                curcand_token = cliparser.escape(curcand)
            else:
                curcand_token = cliparser.quote(curcand)
            new_curpos = self._curpos - self._curtok_curpos + len(curcand_token)
            # log.debug('Replacing %r with %r', tokens[self._curtok_index], curcand_token)
            tokens[self._curtok_index] = curcand_token
            # log.debug('New command line: %r',
            #           ''.join(tokens[:self._curtok_index]) +
            #           tokens[self._curtok_index][new_curpos:] + '|' + tokens[self._curtok_index][new_curpos:] +
            #           ''.join(tokens[self._curtok_index:]))
            return ''.join(tokens), new_curpos

    def _update_current_user_input(self):
        """ """
        if self._categories:
            user_input_cands = self._categories.all[0]
            user_input_cands.set(self.current_user_input)
            user_input_cands.curarg_seps = self._categories.current.curarg_seps
            # log.debug('Updated current user input candidate: %r', user_input_cands)

    @property
    def current_user_input(self):
        """Portion of user input that is replaced with completion candidates"""
        # First category is always current user input
        cats = self._categories[1:]
        len_cats = len(cats)
        if len_cats == 1:
            # There is only one other category of candidates besides the current
            # user input. Use the current argument separator of that other
            # category.
            # For example, if we are completing a path, the current user input
            # is only the part between two "/", the part which we are
            # completing, not the whole path.
            curcands = cats[0]

        elif len_cats > 1 and all(cats[0].curarg_seps == cat.curarg_seps for cat in cats):
            # There are multiple categories but their curarg_seps are all equal,
            # so we can use them like described above.
            curcands = cats[0]

        else:
            # Default to whatever the special current user input instance has
            # defined for curarg_seps (most likely an empty tuple).
            curcands = self._categories[0]

        return self._curarg_parts[curcands]

    @property
    def categories(self):
        """Tuple of Candidates objects for current command line"""
        return self._categories
