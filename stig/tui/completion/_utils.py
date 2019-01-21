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

DEFAULT_DELIMS = (' ',)
DEFAULT_ESCAPES = ('\\',)
DEFAULT_QUOTES = ('"', "'")


def get_current_cmd(tokens, curtok_index, ops):
    """
    Extract tokens before and after the currently focused token up to any
    operators or the start/end

    Return slice of those tokens and the index of the currently focused token in
    that slice
    """
    def is_op(token):
        return any(token == op for op in ops)

    if is_op(tokens[curtok_index]):
        # Cursor is on operator, so no command to return
        return (None, None)
    else:
        first_tok = 0
        last_tok = len(tokens) - 1

        # Find operator before focused token
        for i in range(curtok_index-1, 0, -1):
            token = tokens[i]
            if is_op(token):
                first_tok = i + 1
                break

        # Find operator after focused token
        for i,token in enumerate(tokens[curtok_index:-1]):
            if is_op(token):
                last_tok = curtok_index + i - 1
                break

    sub_curtok_index = curtok_index - first_tok
    return (tokens[first_tok:last_tok+1], sub_curtok_index)


class Char(str):
    """Single character with parser-provided attributes"""

    def __new__(cls, char, *, string='', delim='', escape='', quote='',
                is_special=False, is_escaped=False, is_quoted=False):
        obj = super().__new__(cls, char)
        obj._string = string
        obj._delim = delim
        obj._escape = escape
        obj._quote = quote
        obj._is_special = bool(is_special)
        obj._is_escaped = bool(is_escaped)
        obj._is_quoted = bool(is_quoted)
        return obj

    @property
    def string(self):
        """
        Special delimiting/escaping/quoting string this character is a part of or
        empty string
        """
        return self._string

    @property
    def delim(self):
        """Delimiter string this character is a part of or empty string"""
        return self._delim

    @property
    def escape(self):
        """Escape string this character is a part of or is escaped with or empty string"""
        return self._escape

    @property
    def quote(self):
        """Quote string this character is a part of or quoted with or empty string"""
        return self._quote

    @property
    def is_special(self):
        """
        Whether this character is part of a special string and interpreted as such
        (i.e. not escaped or quoted)
        """
        return self._is_special

    @property
    def is_delim(self):
        """Whether this character is a delimiter"""
        return bool(self._delim)

    @property
    def is_escaped(self):
        """Whether this character is escaped (False for escapes)"""
        return self._is_escaped

    @property
    def is_quoted(self):
        """Whether this character comes after an opening quote (False for quotes)"""
        return self._is_quoted

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return (str(self) == str(other) and
                    self._string == other._string and
                    self._delim == other._delim and
                    self._escape == other._escape and
                    self._quote == other._quote and
                    self._is_special == other._is_special and
                    self._is_escaped == other._is_escaped and
                    self._is_quoted == other._is_quoted)
        else:
            return NotImplemented

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        kwargs = {}
        if self._string: kwargs['string'] = self._string
        if self._delim: kwargs['delim'] = self._delim
        if self._escape: kwargs['escape'] = self._escape
        if self._quote: kwargs['quote'] = self._quote
        if self._is_special: kwargs['is_special'] = self._is_special
        if self._is_escaped: kwargs['is_escaped'] = self._is_escaped
        if self._is_quoted: kwargs['is_quoted'] = self._is_quoted
        if kwargs:
            return '%s(%r, %s)' % (type(self).__name__, str(self),
                                   ', '.join('%s=%r' % (k,v) for k,v in kwargs.items()))
        else:
            return '%s(%r)' % (type(self).__name__, str(self))


def _on_any_substr(string, pos, substrs):
    """
    Whether the character at `string[pos]` is on a aubstring that exists in
    `substrs`

    Return the following tuple:
        (<bool: whether substring was found>,
         <str: the found substring or ''>,
         <int or None: position in `string` where substring was found or None>)
         <int or None: position in substring or None>)
    """
    if pos >= len(string):
        return False, '', None, None

    # Match the longest substrings before the shorter ones
    for substr in sorted(substrs, key=len, reverse=True):
        # Move position backwards until we find `substr`
        len_substr = len(substr)
        substr_pos = pos
        found_substr = ''
        for _ in range(len_substr):
            maybe_substr = string[substr_pos:substr_pos+len_substr]
            if maybe_substr == substr:
                found_substr = maybe_substr
                break
            else:
                substr_pos -= 1
        if not found_substr:
            continue

        # Find non-overlapping start position in case there are multiple
        # consecutive substrings of the same character, e.g. string="!!!!",
        # substr="!!", pos=1 would find the substring at 1, but it actually
        # starts at 0.
        first_substr_pos = substr_pos
        while first_substr_pos > 0:
            first_substr_pos -= 1
            if string[first_substr_pos:first_substr_pos+len_substr] != found_substr:
                first_substr_pos += 1
                break

        # From the first occurence of `substr`, move as many `substr` lengths
        # forward as do fully fit into the difference between the position where
        # we found `substr` and its first occurence.
        diff = pos - first_substr_pos
        len_found_substr = len(found_substr)
        substr_pos = first_substr_pos + (int(diff / len_found_substr) * len_found_substr)
        if string[substr_pos:substr_pos+len_found_substr] == found_substr:
            return True, found_substr, substr_pos, diff % len_found_substr

    return False, '', None, None


def _parse(string, delims=DEFAULT_DELIMS, escapes=DEFAULT_ESCAPES, quotes=DEFAULT_QUOTES):
    """
    Yield `Char` instances

    `delims` is a sequence of strings that act as delimiters between arguments.

    `escapes` is a sequence of strings that remove the special meaning of the
    next character.

    `quotes` is a sequences of strings that (mostly) remove the special meaning
    of the characters between two identical quotes. Special cases are:

        1. Any `escape` in front of a normally closing quote is still a special
           character and removes its quoting power.

        2. As a result, any literal `escape` right before a closing quote must
           be escaped so the closing quote can do its job.
    """
    # log.debug('Parsing %r', string)
    state = {'escape': '', 'quote': '', 'closing_quote_end_index': -1}
    i_max = len(string) - 1
    for i,char in enumerate(string):
        # log.debug('<%s>', string[:i] + '[' + string[i] + ']' + string[i+1:])
        is_delim, delim, delim_index, delim_offset = _on_any_substr(string, i, delims)
        # if is_delim: log.debug('    Delimiter at %r: %r', delim_index, delim)
        is_quote, quote, quote_index, quote_offset = _on_any_substr(string, i, quotes)
        # if is_quote: log.debug('    Quote at %r: %r', quote_index, quote)
        is_escape, escape, escape_index, escape_offset = _on_any_substr(string, i, escapes)
        # if is_escape: log.debug('    Escape at %r: %r', escape_index, escape)

        if not state['escape']:
            next_is_quote, next_quote, next_quote_index, next_quote_offset = _on_any_substr(string, i+1, quotes)
            next_is_escape, next_escape, next_escape_index, next_escape_offset = _on_any_substr(string, i+1, escapes)

            # Backslash is plain text between quotes except when it escapes the
            # enclosing quote (e.g. "foo \" bar" -> [foo " bar])
            if is_escape and (not state['quote'] or next_quote == state['quote'] or next_is_escape):
                yield Char(char, string=escape,
                           is_special=True, is_escaped=state['escape'], is_quoted=state['quote'],
                           escape=escape, quote=state['quote'])
                # Enable escaping state if this is the last character of the
                # escape string (escape characters are not marked as escaped)
                if i >= escape_index + len(escape)-1:
                    # Only mark escape characters that nned it
                    next_is_delim, _, _, _ = _on_any_substr(string, i+1, delims)
                    if next_is_delim or next_is_quote or next_is_escape:
                        # log.debug('    Enabling escape state')
                        state['escape'] = escape
                    else:
                        log.debug('    No need to escape escape next character')
                # else:
                #     log.debug('    Waiting for escape string to finish')
                continue

            elif is_quote:
                if state['quote'] == quote:
                    # Closing quote
                    # log.debug('    Found closing quote: %r', quote)
                    state['quote'] = ''
                    yield Char(char, string=quote,
                               is_special=True, is_escaped=state['escape'], is_quoted=state['quote'],
                               quote=quote, escape=state['escape'])
                    # The next character might still be part of the closing quote
                    state['closing_quote_end_index'] = i + len(quote)-1
                    continue

                elif not state['quote']:
                    # Opening quote
                    yield Char(char, string=quote,
                               is_special=True, is_escaped=state['escape'], is_quoted=state['quote'],
                               quote=quote, escape=state['escape'])

                    # Enable quoting state if this is the last character of the
                    # quote string (quote characters are not marked as quoted)
                    # and if we are not on a closing quote
                    if i >= quote_index + len(quote) - 1 and i > state['closing_quote_end_index']:
                        # log.debug('    Found opening quote: %r', quote)
                        state['quote'] = quote
                    continue

        if is_delim:
            # log.debug('    %r is part of delimiter: %r', char, delim)
            special_string = delim
            special_string_offset = delim_offset
        elif is_escape:
            # log.debug('    %r is part of escape: %r', char, escape)
            special_string = escape
            special_string_offset = escape_offset
        elif is_quote:
            # log.debug('    %r is part of quote: %r', char, quote)
            special_string = quote
            special_string_offset = quote_offset
        else:
            # log.debug('    %r is not part of a special string', char)
            special_string = ''
            special_string_offset = 0

        is_special = is_delim and not state['escape'] and not state['quote']
        yield Char(char, string=special_string,
                   is_special=is_special, is_escaped=state['escape'], is_quoted=state['quote'],
                   delim=delim, escape=state['escape'] or escape, quote=state['quote'] or quote)

        if state['escape'] and special_string and special_string_offset >= len(special_string) - 1:
            # After the first character of a multichar special string is
            # processed, we must keep the escape state alive until all
            # characters of that special string are processed.
            # log.debug('        Disabling escape state')
            state['escape'] = ''


def escape(string, curpos=None, delims=DEFAULT_DELIMS, escapes=DEFAULT_ESCAPES, quotes=DEFAULT_QUOTES):
    """
    Prepend a backslash to special characters: backslash, space, single quote,
    double quote

    If `curpos` is not None, it is the position of the cursor in `string`, and
    the return value is a 2-tuple of (<escaped string>, <new cursor position>).
    """
    string_escaped = []
    curpos_diff = 0
    for i,char in enumerate(_parse(string, delims=delims, escapes=escapes, quotes=quotes)):
        # Escape special or escaped characters
        # The fact that a character is escaped means it is special by nature
        # (non-special characters never have `is_escaped` set to True)
        if char.is_special or char.is_escaped:
            string_escaped.append(escapes[0])
            if curpos is not None and i < curpos:
                curpos_diff += 1
        string_escaped.append(char)

    if curpos is None:
        return ''.join(string_escaped)
    else:
        return ''.join(string_escaped), curpos + curpos_diff


def quote(string, curpos=None, delims=DEFAULT_DELIMS, escapes=DEFAULT_ESCAPES, quotes=DEFAULT_QUOTES):
    """
    Quote `string` if it contains special characters: backslash, space, single
    quote, double quote

    If `curpos` is not None, it is the position of the cursor in `string`, and
    the return value is a 2-tuple of (<quoted string>, <new cursor position>).
    """
    def quote_string():
        # No special strings means no quoting needed
        if all(special_string not in string
               for special_strings in (delims, escapes, quotes)
               for special_string in special_strings):
            return string, '', ''

        # Use the first quote that doesn't exist in `string`
        for quote in quotes:
            if not quote in string:
                return ''.join((quote, string, quote)), quote, ''

        # All quotes exist somewhere in `string` - use the first quoting style
        # and escape all its occurrences
        quote = quotes[0]
        return ''.join((quote,
                        string.replace(quote, escapes[0] + quote),
                        quote)), quote, escapes[0]

    new_string, quote, escape = quote_string()
    # log.debug('Quoted <%s> with <%s>: <%s>', string, quote, new_string)

    if curpos is None:
        return new_string
    else:
        if len(new_string) == len(string):
            # No quotes were added
            return new_string, curpos
        elif curpos <= 0:
            # If cursor was on the first character, put it after the opening quote
            return new_string, len(quote)
        elif curpos >= len(string):
            # If cursor was right of the last character, put it after the closing quote
            return new_string, len(new_string)
        else:
            # Parse `string` up to its cursor position.  Every `quote` we find
            # must be escaped, so we can just add `escape`'s length for each
            # `quote` we find.
            # log.debug('Original string up to %r: %r', curpos, string[:curpos])
            new_curpos = curpos + len(quote)  # Move cursor inside the quotes
            len_escape = len(escape)
            for char in _parse(string[:curpos], delims=delims, escapes=escapes, quotes=quotes):
                if char.string == quote:
                    # log.debug('  Adding len(%r) to cursor position %r: %r', escape, new_curpos, new_curpos+len_escape)
                    new_curpos += len_escape
            # log.debug('New cursor position: %r', new_string[:new_curpos] + '|' + new_string[new_curpos:])
            return new_string, new_curpos


def is_escaped(string, delims=DEFAULT_DELIMS, escapes=DEFAULT_ESCAPES, quotes=DEFAULT_QUOTES):
    """
    Return whether `string` uses backslashes to escape special characters
    """
    for char in _parse(string, delims=delims, escapes=escapes, quotes=quotes):
        if char.is_special:
            if char.string in escapes: return True
            if char.string in quotes: return False
    return False


def plaintext(string, curpos=None, delims=DEFAULT_DELIMS, escapes=DEFAULT_ESCAPES, quotes=DEFAULT_QUOTES):
    """
    Remove any quotes or backslashes from `string` unless they are escaped or
    quoted

    If `curpos` is not None, it is the position of the cursor in `string`, and
    the return value is a 2-tuple of (<plaintext string>, <new cursor position>).
    """
    string_lstripped = string.lstrip()
    if curpos is not None:
        # Adjust cursor position to account for removed leading whitespace
        curpos = max(0, curpos - (len(string) - len(string_lstripped)))

    # Find index of first character of trailing whitespace
    trailing_spaces = len(string_lstripped) - len(string_lstripped.rstrip())
    trailing_spaces_pos = len(string_lstripped) - (trailing_spaces)

    literal = []
    new_curpos = curpos
    for i,char in enumerate(_parse(string_lstripped, delims=delims, escapes=escapes, quotes=quotes)):
        if not char.is_special:
            literal.append(char)
        elif char.is_delim and i < trailing_spaces_pos:
            # Only append non-trailing spaces, i.e. spaces between
            # characters. (Leading spaces have already been stripped.)
            literal.append(char)
        elif char.is_escaped:
            literal.append(char)
        elif new_curpos is not None and new_curpos > 0 and i < curpos:
            new_curpos -= 1

    if new_curpos is None:
        return ''.join(literal)
    else:
        return ''.join(literal), min(new_curpos, len(literal))


def tokenize(cmdline, maxdelims=None, delims=DEFAULT_DELIMS, escapes=DEFAULT_ESCAPES, quotes=DEFAULT_QUOTES):
    """
    Split `cmdline` into list of tokens

    All special characters are included: ''.join(tokenize(cmd)) == string

    Delimiters are separate tokens.
    """
    tokens = []
    token = []
    chars = tuple(_parse(cmdline, delims=delims, escapes=escapes, quotes=quotes))
    i_max = len(chars) - 1
    maxdelims = float('inf') if maxdelims is None else maxdelims

    def get_token_and_delim_from_end(token_and_delim, delim):
        len_delim = len(delim)
        token = ''.join(token_and_delim[:-len_delim])
        delim = ''.join(token_and_delim[-len_delim:])
        return token, delim

    # log.debug('Tokenizing: %r', cmdline)
    for i,char in enumerate(chars):
        # log.debug('Char: %r', char)

        curdelims = int(len(tokens) / 2)
        if char.is_delim and char.is_special and curdelims < maxdelims:
            # Character is part of a delimiter string that is not escaped or quoted
            prev_char = chars[i-1] if i > 0 else Char('')
            next_char = chars[i+1] if i < i_max else Char('')

            if not prev_char.is_delim:
                # This is the first character of a delimiter.  Append the
                # current (non-delimiter) token first before starting a new
                # delimiter token with this character.
                # log.debug('  Delimiter starts at %r: %r: %r', i, char, cmdline[i:])
                if token:
                    tokens.append(''.join(token))
                    # log.debug('    Added %r: %r', tokens[-1], tokens)
                token.clear()
                token[:] = char
            else:
                # This is not the first character of a delimiter, i.e. the
                # current token is a multi-character delimiter.
                token.append(char)

            # log.debug('    len(%r) >= len(%r)', len(token), len(char.delim))
            if ''.join(token) == char.delim:
                # This is the last character of a delimiter.  Append the current
                # token (a delimiter) before starting a new empty token.
                # log.debug('  Delimiter ends at %r: %r: %r', i, char, cmdline[i:])
                if token:
                    tokens.append(''.join(token))
                    # log.debug('    Added %r: %r', tokens[-1], tokens)
                    token.clear()

            # log.debug('    New token: %r', ''.join(token))
            continue

        token.append(char)
        # log.debug('New token: %r', ''.join(token))

    if token or not tokens:
        tokens.append(''.join(token))
    #     log.debug('Added last token: %r', tokens[-1])

    log.debug('Tokenized: %r', tokens)
    return tokens


def get_position(tokens, curpos):
    """
    Find focused index in `tokens`

    `tokens` is a list of tokens as returned by `tokenize`.

    `curpos` is the cursor position in the string of concatenated `tokens`.

    Return the index of the focused token in `tokens` and the cursor position
    within that token
    """
    # Default cursor position is after the last character of the last argument
    curtok_index = len(tokens) - 1
    curtok_curpos = len(tokens[curtok_index])
    for i,token in enumerate(tokens):
        token_len = len(token)
        curpos -= token_len
        if curpos <= 0:
            curtok_index = i
            curtok_curpos = token_len + curpos
            break
    return curtok_index, curtok_curpos


def avoid_delims(tokens, curtok_index, curtok_curpos, delims=(' ',)):
    """
    If the cursor is on the first character of a delimiter, move behind the last
    character of the previous token.  If the cursor is after the last character
    of a delimiter, move on the first character of the next token.  This moves
    the cursor to the closest point of interest without actually changing its
    position (cursor position is still the same when the tokens are
    concatenated).

    If the cursor is at the beginning or end of the command line or if there's a
    delimiter both before and under the cursor, an empty token is inserted at
    that point and the cursor is placed on it.  If the cursor is in the middle
    of a multi-character delimiter, the delimiter is split in two and the empty
    token is inserted between the two parts.

    Return new `tokens`, `curtok_index` and `curtok_curpos`
    """
    curtok = tokens[curtok_index]
    if curtok not in delims:
        return tokens, curtok_index, curtok_curpos
    else:
        curtok_index_max = len(tokens) - 1
        curtok_curpos_max = len(curtok)
        prev_token = tokens[curtok_index-1] if curtok_index > 0 else None
        next_token = tokens[curtok_index+1] if curtok_index < curtok_index_max else None
        log.debug('  Previous token: %r  Next token: %r', prev_token, next_token)

        # Move to previous token if we're on the first character of a delimiter
        # ['ls', '| ', 'foo'] -> ['ls|', ' ', 'foo']
        if curtok_curpos <= 0 and prev_token is not None:
            log.debug('  Avoiding delimiter - moving to previous token')
            curtok_index -= 1
            curtok_curpos = len(prev_token)

        # Move to next token if we're on the last character of a delimiter
        # ['ls', ' |', 'foo'] -> ['ls', ' ', '|foo']
        elif curtok_curpos >= curtok_curpos_max and next_token is not None:
            log.debug('  Avoiding delimiter - moving to next token')
            curtok_index += 1
            curtok_curpos = 0

    log.debug('  After moving away from delimiter: Current token: %r, Cursor position: %r',
              curtok_index, curtok_curpos)

    # If we still focus a delimiter, we are either at the beginning or end of
    # the command line or there are consecutive delimiters.  We insert an empty
    # token and move the cursor on it.  This doesn't change the command line and
    # completion candidates can replace the empty token without changing the
    # other tokens.
    curtok = tokens[curtok_index]
    curtok_curpos_max = len(curtok)
    if curtok in delims:
        # If the cursor is on the first character of the token, insert an empty
        # token before the current one
        if curtok_curpos <= 0:
            log.debug('  Inserting empty token before the current')
            tokens.insert(curtok_index, '')
            curtok_curpos = 0

        # If the cursor is after the last character of the token, insert an
        # empty token after the current one
        elif curtok_curpos >= curtok_curpos_max:
            log.debug('  Inserting empty token after the current')
            curtok_index += 1
            tokens.insert(curtok_index, '')
            curtok_curpos = 0

        # If the cursor is somewhere else than the beginning/end of the token,
        # split the token at the cursor position, insert the empty token between
        # the parts and replace the current token with these three tokens.
        else:
            log.debug('  Inserting empty token in the middle of the current')
            subtoks = (curtok[:curtok_curpos], '', curtok[curtok_curpos:])
            log.debug('  Replacing %r with %r', curtok, subtoks)
            tokens[curtok_index:curtok_index+1] = subtoks
            curtok_index += 1
            curtok_curpos = 0

    log.debug('  Final: Current token: %r, Cursor position: %r', curtok_index, curtok_curpos)
    log.debug('  Tokens: %r', tokens)
    return tokens, curtok_index, curtok_curpos


class Parts(tuple):
    def __new__(cls, parts, curpart_index=None, curpart_curpos=None):
        # Make sure all parts are Arg instances
        def gen():
            for i,part in enumerate(parts):
                if not isinstance(part, Arg):
                    if i == curpart_index:
                        yield Arg(part, curpos=curpart_curpos)
                    else:
                        yield Arg(part)
                else:
                    yield part
        obj = super().__new__(cls, gen())
        obj.curpart = obj[curpart_index] if curpart_index is not None else None
        obj.curpart_index = curpart_index
        obj.curpart_curpos = curpart_curpos
        return obj

    @property
    def curpart_before_cursor(self):
        if self.curpart_curpos is not None:
            return self.curpart[:self.curpart_curpos]
        else:
            return str(self.curpart)

    def __repr__(self):
        return '%s(%r, curpart=%r, curpart_index=%r, curpart_curpos=%r)' % (
            type(self).__name__,
            tuple(self), self.curpart, self.curpart_index, self.curpart_curpos)


class Arg(str):
    def __new__(cls, arg, curpos=None):
        obj = super().__new__(cls, arg)
        obj._curpos = curpos
        return obj

    @property
    def before_cursor(self):
        """Return the part before the cursor or the whole argument if `curpos` is None"""
        if self.curpos is not None:
            return self[:self.curpos]
        else:
            return str(self)

    @property
    def curpos(self):
        """Cursor position in argument"""
        return self._curpos

    def separate(self, seps, maxseps=None, include_seps=True):
        """
        Split argument at any occurence of any string in `seps`

        maxseps: Maximum number of separations or None
        include_seps: Whether to include separators in the new list

        Return a `Parts` object
        """
        seps = tuple(seps)
        log.debug('Splitting %r at separators: %r', str(self), seps)
        parts = tokenize(self, delims=seps, maxdelims=maxseps)

        if self.curpos is not None:
            curpart_index, curpart_curpos = get_position(parts, self.curpos)
        else:
            curpart_index, curpart_curpos = 0, 0

        if include_seps:
            if self.curpos is not None:
                log.debug('Moving away from separators')
                parts, curpart_index, curpart_curpos = avoid_delims(parts, curpart_index, curpart_curpos, seps)
        else:
            log.debug('Removing separators')
            parts, curpart_index, curpart_curpos = as_args(parts, curpart_index, curpart_curpos, seps)

        if self.curpos is not None:
            return Parts(parts, curpart_index, curpart_curpos)
        else:
            return Parts(parts)

    def __repr__(self):
        string = '%s(%r' % (type(self).__name__, str(self),)
        if self.curpos is not None:
            string += ', curpos=%d' % (self.curpos,)
        return string + ')'


def as_args(tokens, curtok_index, curtok_curpos, delims=(' ',)):
    """
    Remove delimiters and interpreted special characters from `tokens` and
    adjust `curtok_index` and `curtok_curpos` accordingly

    If the cursor is on a delimiter, move the cursor to nearest left-hand token
    if possible, otherwise to the nearest right-hand token.

    The returned arguments always contain at least one empty argument.

    Return `(args, curarg_index, curarg_curpos)`
    """
    log.debug('  Converting to arguments: %r', tokens)
    log.debug('    curtok_index=%r, curtok_curpos=%r', curtok_index, curtok_curpos)

    curtok_index_max = len(tokens) - 1
    if tokens[curtok_index] in delims:
        # Move to token on the right if the next token is not a delimiter and if
        # the cursor is positioned after the last character (i.e. on the first
        # character of the next token)
        if (curtok_curpos == len(tokens[curtok_index]) and
            curtok_index < curtok_index_max and
            tokens[curtok_index+1] not in delims):
            curtok_index += 1
            curtok_curpos = 0

        # Try to move to the nearest left-hand non-delimiter
        elif any(tok not in delims for tok in tokens[:curtok_index]):
            curtok_index -= 1
            while tokens[curtok_index] in delims and curtok_index > 0:
                curtok_index -= 1
            curtok_curpos = len(tokens[curtok_index])

        # Try to move to the nearest right-hand non-delimiter
        elif any(tok not in delims for tok in tokens[curtok_index:]):
            # There are only delimiters on the left, but we can move to the right
            curtok_index += 1
            while tokens[curtok_index] in delims and curtok_index < curtok_index_max:
                curtok_index += 1
            curtok_curpos = 0

        # There are no non-delimiter tokens
        else:
            return [Arg('', curpos=0)], 0, 0

    log.debug('    Adjusted curtok_index=%r, curtok_curpos=%r', curtok_index, curtok_curpos)

    args = []
    curarg_index = curtok_index
    curarg_curpos = curtok_curpos
    for i,token in enumerate(tokens):
        log.debug('Token %s: %r', i, token)
        if token not in delims:
            # Append all non-delimiter tokens
            if i == curtok_index:
                arg, curarg_curpos = plaintext(token, curtok_curpos)
                args.append(Arg(arg, curpos=curarg_curpos))
                log.debug('    Token %r: %r: Added current argument: %r',
                          i, token, arg[:curarg_curpos] + '|' + arg[curarg_curpos:])
            else:
                args.append(Arg(plaintext(token)))
                log.debug('    Token %r: %r: Added argument: %r', i, token, args[-1])

        elif i < curtok_index:
            # Reduce current argument index as long as we haven't passed the
            # current token yet
            curarg_index -= 1
            log.debug('    Token %r: %r: Reduced curarg_index by %r: %r', i, token, len(token), curarg_index)

        elif i == curtok_index:
            # If cursor is on a delimiter, move it to the next token
            curtok_curpos = 0
            curtok_index = i+1  # Append next token in next iteration
            log.debug('    Token %r: %r: Moving cursor to next non-delimiter token', i, token)

        else:
            log.debug('A delimiter after cursor (%s >= %s): %r', i, curtok_index, token)

    # Ensure `args` has at least one empty string to avoid catching IndexErrors
    if not args:
        args.append(Arg('', curpos=0))
        curarg_index = curarg_curpos = 0

    log.debug('  Args:%r, curarg_index:%r, curarg_curpos:%r', args, curarg_index, curarg_curpos)
    return args, curarg_index, curarg_curpos
