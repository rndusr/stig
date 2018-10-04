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

from ..singletons import cmdmgr
from ..commands import OPS
from . import candidates


class Completer():
    """
    Parse command line and provide a tab completion interface

    cmdline: Full command line
    curpos: Current cursor position in cmdline
    """
    def __init__(self, cmdline, curpos):
        log.debug('Parsing: %r', cmdline[:curpos] + '|' + cmdline[curpos:])

        # Extract current command from command chain (e.g. "foo -x & bar ; baz -a")
        # and also the cursor position within that command
        subcmd, subcurpos = self._get_current_cmd(cmdline, curpos)
        log.debug('Partial subcmd: %r', subcmd[:subcurpos] + '|' + subcmd[subcurpos:])
        args, subcmd_focus = _tokenize(subcmd, subcurpos)
        log.debug('Tokenized: %r, focused=%r', args, subcmd_focus)
        cmdname = args[0] if args else ''
        log.debug('Command name: %r', cmdname)
        cmdcls = cmdmgr.get_cmdcls(cmdname)
        log.debug('Command class: %r', cmdcls)
        curarg = args[subcmd_focus] if subcmd_focus is not None else ''
        log.debug('Current argument: %r', curarg)

        # Command completion command is not "finalized" by a trailing space
        if ' ' not in subcmd[:subcurpos].lstrip():
            log.debug('Completing command: %r', cmdname)
            cands = candidates.commands()
        elif cmdcls is not None:
            log.debug('Completing argument for %r', cmdcls.name)
            cands = cmdcls.completion_candidates(args, subcmd_focus)
        else:
            cands = candidates.Candidates()

        delim = getattr(cands, 'delimiter', ' ')
        if delim != ' ':
            # Parameters for options may be separated by non-space characters, e.g. ','
            log.debug('Splitting current argument at custom delimiter: %r', delim)
            curarg = curarg.split(delim)[-1]
            log.debug('New current argument: %r', curarg)

        self._candidates = _reduce_candidates(cands, curarg)
        self._cmdline = cmdline
        self._curpos = curpos
        self._current_argument = curarg
        self._delim = delim
        log.debug('Candidates for %r: %r', curarg, self._candidates)

    def complete(self):
        """
        Return new command line and new cursor position

        `update` must be called first.
        """
        cmdline = self._cmdline
        curpos = self._curpos
        if any(x is None for x in (cmdline, curpos)):
            raise RuntimeError('You must call update() first')
        elif self._candidates:
            log.debug('Completing %r', cmdline[:curpos] + '|' + cmdline[curpos:])
            curarg = self._current_argument
            cands = self._candidates

            # Get the longest common string all candidates start with
            common_prefix = _find_common_prefix(cands, curarg)
            log.debug('Common prefix: %r', common_prefix)
            len_diff = len(common_prefix) - len(curarg)

            # If cursor is inside a word, move it to end of current completion:
            # tra|ckerlist -> trackerlist|
            while (not cmdline[curpos:].startswith(common_prefix)
                   and _char_at(curpos, cmdline) != ' '
                   and curpos < len(cmdline)):
                curpos += 1

            # Insert any remaining characters at cursor position
            len_curarg = len(curarg)
            missing_part = common_prefix[len_curarg:]
            log.debug('%r: Inserting %r at %r', cmdline, missing_part, curpos)
            cmdline = ''.join((cmdline[:curpos], missing_part, cmdline[curpos:]))
            curpos += len_diff

            # If there's only one candidate, finalize the completion (usually by
            # adding a space after the completed string)
            if len(cands) <= 1:
                cmdline, curpos = _finalize_completion(cmdline, curpos, tail=self._delim)

        return cmdline, curpos

    @property
    def candidates(self):
        """Sequence of strings that could complete the current argument"""
        return self._candidates

    _cmd_ops_regex = re.compile(r'(?:^|\s)(?:' + r'|'.join(re.escape(op) for op in OPS) + r')\s')
    @classmethod
    def _get_current_cmd(cls, cmdline, curpos):
        """Split `cmdline` at operators and return the command the cursor is in"""
        log.debug('Splitting %r at %r (%r)', cmdline, curpos, cmdline[curpos] if curpos < len(cmdline) else '')

        start = _rfind(cls._cmd_ops_regex, cmdline[:curpos]) or 0
        end = _lfind(cls._cmd_ops_regex, cmdline[curpos:])
        end = len(cmdline) if end is None else curpos + end

        cmd = cmdline[start:end]
        curpos = curpos - start
        log.debug('Current command: %r', cmd)
        log.debug('Cursor position in current command: %r', curpos)
        return (cmd, curpos)



def _tokenize(cmdline, curpos):
    """
    Split `cmdline` into arguments, considering (escaped) quotes and escaped
    spaces

    Return list of tokens and the index of the token the cursor is on
    """
    tokens = []
    escaped = False
    quoted = ''
    curtoken = []
    focused_token = None
    for i_char,char in enumerate(cmdline):
        if not escaped:
            if char == '\\':
                log.debug('%s: Escaping next character', char)
                escaped = True
                continue

            elif char == '"' or char == "'":
                if quoted == char:
                    log.debug('%s: Closing quote', char)
                    quoted = ''
                    continue
                elif not quoted:
                    log.debug('%s: Opening quote', char)
                    quoted = char
                    continue

        if char == ' ' and not escaped and not quoted:
            if curtoken:
                token = ''.join(curtoken)
                curtoken = []
                log.debug('Appending new token: %r', token)
                tokens.append(token)
            else:
                log.debug('Skipping empty token')
        else:
            log.debug('%s: Adding non-space or escaped character', char)
            curtoken.append(char)
            if focused_token is None and i_char == curpos-1:
                log.debug('Character #%d is on token #%d', i_char, len(tokens))
                focused_token = len(tokens)

        escaped = False

    token = ''.join(curtoken)
    log.debug('Appending final token: %r', token)
    tokens.append(token)
    if focused_token is None:
        focused_token = len(tokens) - 1

    return tokens, focused_token


def _find_common_prefix(candidates, prefix=''):
    """
    Return longest string that all the strings in `candidates` start with,
    starting with `prefix`
    """
    if len(candidates) == 1:
        return candidates[0]
    else:
        shortest_cand = sorted(candidates, key=len)[0]
        for i in range(len(prefix), len(shortest_cand)):
            test_char = shortest_cand[i]
            test_prefix = prefix + test_char
            if all(cand[:len(test_prefix)] == test_prefix for cand in candidates):
                prefix += test_char
            else:
                break
        return prefix


def _reduce_candidates(cands, common_prefix):
    """Return tuple of candidates that start with `common_prefix`"""
    return tuple(cand for cand in cands
                 if cand.startswith(common_prefix))


def _finalize_completion(cmdline, curpos, tail=' '):
    """Ensure `tail` exists at `curpos` and cursor is positioned after it"""
    # Examples: ('|' is the cursor)
    # 'ls|...'  -> 'ls |...'
    # 'ls| ...' -> 'ls |...'
    # 'ls |...' -> 'ls |...'
    i = curpos - 1
    if cmdline[i] != tail and (len(cmdline)-1 < curpos or cmdline[curpos] != tail):
        cmdline = ''.join((cmdline[:curpos], tail, cmdline[curpos:]))
    if cmdline[i] != tail:
        curpos += 1
    return cmdline, curpos


def _char_at(curpos, cmdline):
    return cmdline[curpos] if curpos < len(cmdline) else ''


def _rfind(regex, string):
    match = None
    for match in regex.finditer(string): pass
    return None if match is None else match.end()


def _lfind(regex, string):
    try:
        match = next(regex.finditer(string))
    except StopIteration:
        return None
    else:
        return match.start()
