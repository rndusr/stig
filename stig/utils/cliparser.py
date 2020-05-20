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

# TODO: Make all functions that take a cursor position return a tuple if the cursor
#       position is given, or just a single argument otherwise.

# TODO: To comply with bash, a backslash shouldn't have special meaning unless it's in
#       front of a special character, e.g. "\1" should be a backslash and 1.

# TODO: To comply with bash, backslashes shouldn't have special meaning inside single
#       quotes, e.g. '\' should be a single backslash while "\" would be a double quote
#       with the closing quote missing.


from collections import abc

from ..logging import make_logger  # isort:skip
log = make_logger(__name__)


DEFAULT_DELIMS = (' ',)
DEFAULT_ESCAPES = ('\\',)
DEFAULT_QUOTES = ('"', "'")


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
            maybe_substr = string[substr_pos : substr_pos + len_substr]
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
            if string[first_substr_pos : first_substr_pos + len_substr] != found_substr:
                first_substr_pos += 1
                break

        # From the first occurrence of `substr`, move as many `substr` lengths
        # forward as do fully fit into the difference between the position where
        # we found `substr` and its first occurrence.
        diff = pos - first_substr_pos
        len_found_substr = len(found_substr)
        substr_pos = first_substr_pos + (int(diff / len_found_substr) * len_found_substr)
        if string[substr_pos : substr_pos + len_found_substr] == found_substr:
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
    for i,char in enumerate(string):
        # log.debug('<%s>', string[:i] + '[' + string[i] + ']' + string[i+1:])
        is_delim, delim, delim_index, delim_offset = _on_any_substr(string, i, delims)
        # if is_delim: log.debug('    Delimiter at %r: %r', delim_index, delim)
        is_quote, quote, quote_index, quote_offset = _on_any_substr(string, i, quotes)
        # if is_quote: log.debug('    Quote at %r: %r', quote_index, quote)
        is_escape, escape, escape_index, escape_offset = _on_any_substr(string, i, escapes)
        # if is_escape: log.debug('    Escape at %r: %r', escape_index, escape)

        if not state['escape']:
            next_is_quote, next_quote, next_quote_index, next_quote_offset = _on_any_substr(string, i + 1, quotes)
            next_is_escape, next_escape, next_escape_index, next_escape_offset = _on_any_substr(string, i + 1, escapes)

            # Backslash is plain text between quotes except when it escapes the
            # enclosing quote (e.g. "foo \" bar" -> [foo " bar])
            if is_escape and (not state['quote'] or next_quote == state['quote'] or next_is_escape):
                yield Char(char, string=escape,
                           is_special=True, is_escaped=state['escape'], is_quoted=state['quote'],
                           escape=escape, quote=state['quote'])
                # Enable escaping state if this is the last character of the
                # escape string (escape characters are not marked as escaped)
                if i >= escape_index + len(escape) - 1:
                    # Only mark escape characters that nned it
                    next_is_delim, _, _, _ = _on_any_substr(string, i + 1, delims)
                    if next_is_delim or next_is_quote or next_is_escape:
                        # log.debug('    Enabling escape state')
                        state['escape'] = escape
                #     else:
                #         log.debug('    No need to escape escape next character')
                # else:
                #     log.debug('    Waiting for escape string to end')
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
                    state['closing_quote_end_index'] = i + len(quote) - 1
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
            # log.debug('    Disabling escape state')
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
            if quote not in string:
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

    All special characters are retained:

    >>> ''.join(tokenize(cmdline)) == cmdline

    Delimiters are included as separate tokens.
    """
    tokens = []
    token = []
    chars = tuple(_parse(cmdline, delims=delims, escapes=escapes, quotes=quotes))
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
            prev_char = chars[i - 1] if i > 0 else Char('')

            if not prev_char.is_delim or not prev_char.is_special:
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
                # log.debug('  Delimiter already started: %r (prev.is_delim=%r, prev.is_special=%r)',
                #           prev_char.delim, prev_char.is_delim, prev_char.is_special)
                token.append(char)

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
        # log.debug('Added last token: %r', tokens[-1])

    # log.debug('Tokenized: %r', tokens)
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


def remove_delims(tokens, curtok_index, curtok_curpos, delims=DEFAULT_DELIMS):
    """
    Remove any delimiters from `tokens` and adjust `curtok_index` and
    `curtok_curpos` accordingly

    `curtok_index` is adjusted so that the cursor stays on the same argument.

    `curtok_curpos` is adjusted only if the cursor is on a delimiter, in which
    case it is moved to the next token if it's behind the last character of the
    delimiter and the next token is not a delimiter or the previous token
    otherwise.

    Return new `tokens`, `curtok_index` and `curtok_curpos`
    """
    # log.debug('  Input: %r, %r, %r', tokens, curtok_index, curtok_curpos)
    new_tokens = []
    new_curtok_index = curtok_index
    new_curtok_curpos = curtok_curpos
    for i,token in enumerate(tokens):
        if token not in delims:
            # log.debug('    Token %r: %r: Not a delimiter', i, token)
            new_tokens.append(token)

        elif i < curtok_index:
            # If token is a delimiter, reduce `new_curtok_index` as long as we
            # haven't passed the `curtok_index` yet
            new_curtok_index -= 1
            # log.debug('    Token %r: %r: Reduced new_curtok_index by 1: %r', i, token, new_curtok_index)

        elif i == curtok_index:
            # Cursor is on a delimiter
            next_token = tokens[i + 1] if i + 1 < len(tokens) else None
            cursor_after_last_char = curtok_curpos >= len(tokens[curtok_index])
            if next_token is not None and next_token not in delims and cursor_after_last_char:
                # Move to to first character of next token
                new_curtok_curpos = 0
                # log.debug('    Token %r: %r: Moved cursor to next token: %r', i, token, next_token)
            else:
                # Move to to last character of previous token
                if new_tokens:
                    new_curtok_index = max(0, new_curtok_index - 1)
                    new_curtok_curpos = len(new_tokens[new_curtok_index])
                    # log.debug('    Token %r: %r: Moved cursor to previous token: %r', i, token, new_tokens[new_curtok_index])
                else:
                    new_curtok_index = new_curtok_curpos = 0

    # log.debug('  Output: %r, %r, %r', new_tokens, new_curtok_index, new_curtok_curpos)
    return new_tokens, new_curtok_index, new_curtok_curpos


def avoid_delims(tokens, curtok_index, curtok_curpos, delims=DEFAULT_DELIMS):
    """
    If the cursor is on the first character of a delimiter, move it behind the
    last character of any previous non-delimiter token.  If the cursor is on any
    other character of a delimiter, move it on the first character of the next
    non-delimiter token.

    If no previous non-delimiter token exists, move on the first character of
    the next non-delimiter token.  And vice-versa, if no next non-delimiter
    token exists, move behind the last character of the previous non-delimiter
    token. If `tokens` contains only delimiters, keep the cursor position as it
    is.

    Return new `tokens`, `curtok_index` and `curtok_curpos`
    """
    curtok = tokens[curtok_index]
    if curtok not in delims:
        return tokens, curtok_index, curtok_curpos
    else:
        class ImpossibleMove(Exception): pass

        def forward():
            # log.debug('      Finding first non-delimiter token in %r', tokens[curtok_index+1:])
            for i,tok in enumerate(tokens[curtok_index + 1:], start=1):
                if tok not in delims:
                    # log.debug('      Avoiding delimiter - moving %d tokens forward', i)
                    return curtok_index + i, 0
            raise ImpossibleMove()

        def backward():
            # log.debug('      Finding last non-delimiter token in %r', tokens[:curtok_index])
            for i,tok in enumerate(reversed(tokens[:curtok_index]), start=1):
                if tok not in delims:
                    # log.debug('      Avoiding delimiter - moving %d tokens backward', i)
                    return curtok_index - i, len(tokens[curtok_index - i])
            raise ImpossibleMove()

        def move(*movements):
            for func in movements:
                # log.debug('    Trying to move %s', func.__name__)
                try:
                    return func()
                except ImpossibleMove:
                    # log.debug('      No dice')
                    pass
            return curtok_index, curtok_curpos

        prev_token = tokens[curtok_index - 1] if curtok_index > 0 else None
        # log.debug('  Input: %r, %r, %r', tokens, curtok_index, curtok_curpos)

        # Move to previous token if we're on the first character of a delimiter
        # and the previous token is a non-delimiter
        # ['ls', '| ', 'foo'] -> ['ls|', ' ', 'foo']
        if curtok_curpos <= 0 and prev_token is not None and prev_token not in delims:
            curtok_index, curtok_curpos = move(backward, forward)

        # Move to next token if we're on the last character of a delimiter
        # ['ls', ' |', 'foo'] -> ['ls', ' ', '|foo']
        else:
            curtok_index, curtok_curpos = move(forward, backward)

    # log.debug('  Output: %r, %r, %r', tokens, curtok_index, curtok_curpos)
    return tokens, curtok_index, curtok_curpos


def maybe_insert_empty_token(tokens, curtok_index, curtok_curpos, delims=DEFAULT_DELIMS):
    """
    If the cursor is on a delimiter at the beginning or end of the command line,
    an empty token is inserted there.

    If the cursor is on the first character of a delimiter and the previous
    token is also a delimiter, an empty token is inserted at `curtok_index`.

    If the cursor is on the last character of a delimiter and the next token is
    also a delimiter, an empty token is inserted at `curtok_index+1`.

    If the cursor is on any but the first or last character of a multi-character
    delimiter, the delimiter is split at `curtok_curpos` and an empty token is
    inserted there.

    If an empty token is inserted, the cursor is always placed on it.

    Return new `tokens`, `curtok_index` and `curtok_curpos`
    """
    # log.debug('  Input: %r, %r, %r', tokens, curtok_index, curtok_curpos)
    curtok = tokens[curtok_index]
    curtok_index_max = len(tokens) - 1
    curtok_curpos_max = len(curtok)

    if curtok in delims:
        on_first_char = curtok_curpos == 0
        on_last_char = curtok_curpos == curtok_curpos_max
        prevtok = tokens[curtok_index - 1] if curtok_index >= 1 else None
        nexttok = tokens[curtok_index + 1] if curtok_index < curtok_index_max else None

        if curtok_index == 0:
            # log.debug('    Inserting empty token before the first')
            tokens = ['', *tokens]
            curtok_curpos = 0

        elif curtok_index == curtok_index_max:
            # log.debug('    Inserting empty token after the last')
            tokens = [*tokens, '']
            curtok_index = curtok_index_max + 1
            curtok_curpos = 0

        elif on_first_char and prevtok in delims:
            # ['foo', '/', '|/', 'bar'] -> ['foo', '/', '|', '/', 'bar']
            # log.debug('    Inserting empty token before the current')
            tokens = [*tokens[:curtok_index], '', *tokens[curtok_index:]]
            curtok_curpos = 0

        elif on_last_char and nexttok in delims:
            # ['foo', '/|', '/', 'bar'] -> ['foo', '/', '|', '/', 'bar']
            # log.debug('    Inserting empty token after the current')
            curtok_index += 1
            tokens = [*tokens[:curtok_index], '', *tokens[curtok_index:]]
            curtok_curpos = 0

        elif not on_first_char and not on_last_char:
            # ['foo', '!|=', 'bar'] -> ['foo', '!', '|', '=', 'bar']
            # log.debug('    Inserting empty token in multi-char delimiter')
            subtoks = (curtok[:curtok_curpos], '', curtok[curtok_curpos:])
            # log.debug('    Replacing %r with %r', curtok, subtoks)
            tokens = [*tokens[:curtok_index], *subtoks, *tokens[curtok_index + 1:]]
            curtok_index += 1
            curtok_curpos = 0
    #     else:
    #         log.debug('    No need for empty token after %r: %r', curtok, tokens)
    # else:
    #     log.debug('    Not a delimiter: %r', curtok)

    # log.debug('  Output: %r, %r, %r', tokens, curtok_index, curtok_curpos)
    return tokens, curtok_index, curtok_curpos


def _get_paramspec(options, arg):
    for key,spec in options.items():
        if arg in key:
            return spec


def remove_options(args, curarg_index, curarg_curpos, options={}):
    """
    Remove options and parameters from `args` and adjust `curarg_index` and
    `curarg_curpos` if necessary

    `options` is a mapping that maps tuples of option names (e.g. `('--output',
    '-o')`) to one of these values:

        <int> - Remove <int> arguments after these options
        "*"   - Remove all arguments after these options until an argument
                that starts with "-" is encountered

    (Parameters are defined as arguments to an option, e.g. "--option parameter".)

    Return new arguments, index of current argument and cursor position in
    current argument
    """
    # Reduce index of current argument if we remove options to the left of it
    new_curarg_index = curarg_index
    new_curarg_curpos = curarg_curpos
    cur_spec, params_found = None, 0
    args_wo_opts = []

    for i,arg in enumerate(args):
        append_arg = True
        is_option = arg.startswith('-')
        if is_option:
            append_arg = False
            cur_spec, params_found = _get_paramspec(options, arg), 0
        elif cur_spec is not None:
            # Find out whether this argument is a parameter for an option we
            # encountered earlier
            params_found += 1
            if isinstance(cur_spec, int):
                if params_found <= cur_spec:
                    append_arg = False
            elif cur_spec == '*':
                if not is_option:
                    append_arg = False
            else:
                raise ValueError('Invalid parameter spec: %r' % (cur_spec,))

        if append_arg:
            args_wo_opts.append(arg)
        elif curarg_index is not None and curarg_curpos is not None:
            if i < curarg_index:
                # Removing an argument before the current one
                new_curarg_index -= 1
            elif i == curarg_index:
                # Removing the current argument
                new_curarg_curpos = 0

    # Ensure at least one empty argument
    if not args_wo_opts:
        args_wo_opts = ['']
        new_curarg_index = new_curarg_curpos = 0

    # Ensure index and curpos are not out of bounds
    elif curarg_index is not None and curarg_curpos is not None:
        new_curarg_index_max = len(args_wo_opts) - 1
        new_curarg_curpos_max = len(args_wo_opts[-1])
        if new_curarg_index > new_curarg_index_max:
            new_curarg_index = new_curarg_index_max
            new_curarg_curpos = new_curarg_curpos_max
        elif new_curarg_curpos > new_curarg_curpos_max:
            new_curarg_curpos = new_curarg_curpos_max

    return args_wo_opts, new_curarg_index, new_curarg_curpos


def get_nth_posarg_index(n, args, options={}):
    """
    Return index in `args` of the `n`th positional argument.  Positional
    arguments don't start with "-" and are not parameters for options.

    Return None if there are no positional arguments in `args`.

    See `remove_options` for documentation about `options`.
    """
    posargs_found = -1
    cur_spec, params_found = None, 0
    for i,arg in enumerate(args):
        is_option = arg.startswith('-')
        is_posarg = False

        if is_option:
            cur_spec, params_found = _get_paramspec(options, arg), 0
        elif cur_spec is not None:
            # Find out whether this argument is a parameter for an option
            params_found += 1

            if isinstance(cur_spec, int):
                if params_found > cur_spec:
                    is_posarg = True
                    posargs_found += 1
            elif cur_spec == '*':
                if not is_option:
                    is_posarg = True
                    posargs_found += 1
            else:
                raise ValueError('Invalid parameter spec: %r' % (cur_spec,))

        else:
            # Option is not specified in `options` but it's still an option
            is_posarg = True
            posargs_found += 1

        if is_posarg and posargs_found == n - 1:
            return i
    return None


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
        for i in range(curtok_index - 1, 0, -1):
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
    return (tokens[first_tok : last_tok + 1], sub_curtok_index)


class Arg(str):
    """Single argument"""

    def __new__(cls, arg, curpos=None):
        obj = super().__new__(cls, arg)
        obj._curpos = curpos
        return obj

    @property
    def before_cursor(self):
        """Return the part before the cursor or the whole argument if `curpos` is None"""
        if self.curpos is not None:
            return Arg(self[:self.curpos], curpos=self.curpos)
        else:
            return self

    @property
    def curpos(self):
        """Cursor position in argument"""
        return self._curpos

    @curpos.setter
    def curpos(self, curpos):
        self._curpos = int(curpos)

    def separate(self, seps, maxseps=None, include_seps=True):
        """
        Split argument at any occurrence of any string in `seps`

        maxseps: Maximum number of separations or None
        include_seps: Whether to include separators in the new list

        Return an `Args` object
        """
        seps = tuple(seps)
        # log.debug('Splitting %r at separators: %r', str(self), seps)
        parts = tokenize(self, delims=seps, maxdelims=maxseps)

        if self.curpos is not None:
            curpart_index, curpart_curpos = get_position(parts, self.curpos)
        else:
            curpart_index, curpart_curpos = 0, 0

        parts, curpart_index, curpart_curpos = maybe_insert_empty_token(parts, curpart_index, curpart_curpos, seps)
        # log.debug('Maybe inserted empty token: %r, %r, %r', parts, curpart_index, curpart_curpos)

        if include_seps:
            if self.curpos is not None:
                parts, curpart_index, curpart_curpos = avoid_delims(parts, curpart_index, curpart_curpos, seps)
                # log.debug('Moved away from separators: %r, %r, %r', parts, curpart_index, curpart_curpos)
        else:
            parts, curpart_index, curpart_curpos = remove_delims(parts, curpart_index, curpart_curpos, seps)
            # log.debug('Removed separators: %r, %r, %r', parts, curpart_index, curpart_curpos)

        if self.curpos is not None:
            return Args(parts, curpart_index, curpart_curpos)
        else:
            return Args(parts)

    def __getitem__(self, item):
        if isinstance(item, slice):
            subarg = super().__getitem__(item)
            if item.step is not None:
                raise RuntimeError('Slicing with steps is not implemented yet')
            elif self.curpos is None:
                return Arg(subarg)
            elif ((item.start is None or item.start <= self.curpos) and
                  (item.stop is None or item.stop > self.curpos)):
                curpos = self.curpos - (item.start or 0)
            else:
                curpos = None
            return Arg(subarg, curpos=curpos)
        else:
            curpos = 0 if item == self.curpos else None
            return Arg(super().__getitem__(item), curpos=curpos)

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return super().__eq__(other) and self.curpos == other.curpos

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return super().__hash__()

    def __repr__(self):
        string = '%s(%r' % (type(self).__name__, str(self),)
        if self.curpos is not None:
            string += ', curpos=%d' % (self.curpos,)
        return string + ')'


class Args(tuple):
    """
    Tuple of arguments (tokens without delimiters) with cursor position and
    some convenience properties
    """
    @classmethod
    def from_tokens(cls, tokens, curtok_index, curtok_curpos, delims=DEFAULT_DELIMS):
        # log.debug('Creating Args from tokens: %r, %r, %r', tokens, curtok_index, curtok_curpos)

        # Ensure at least one empty string
        if not tokens:
            tokens = ('',)

        tokens, curtok_index, curtok_curpos = maybe_insert_empty_token(tokens, curtok_index, curtok_curpos, delims)
        # log.debug('Maybe inserted empty token: %r, %r, %r', tokens, curtok_index, curtok_curpos)

        tokens, curtok_index, curtok_curpos = remove_delims(tokens, curtok_index, curtok_curpos, delims)
        # log.debug('Removed separators: %r, %r, %r', tokens, curtok_index, curtok_curpos)

        # Convert everything to plaintext (e.g. remove backslashes from escaped characters)
        for i in range(len(tokens)):
            if i == curtok_index:
                tokens[i], curtok_curpos = plaintext(tokens[i], curtok_curpos)
            else:
                tokens[i] = plaintext(tokens[i])

        return cls(tokens, curtok_index, curtok_curpos)

    def __new__(cls, args, curarg_index=None, curarg_curpos=None):
        def gen():
            for i,arg in enumerate(args):
                if i == curarg_index:
                    yield Arg(arg, curpos=curarg_curpos)
                else:
                    yield Arg(arg)
        obj = super().__new__(cls, gen())
        obj._curarg_index = curarg_index
        if curarg_index is not None and obj.curarg_curpos is None:
            obj.curarg_curpos = 0
        return obj

    @property
    def curarg(self):
        """Currently focused argument"""
        curarg_index = self._curarg_index
        if curarg_index is not None:
            return self[curarg_index]

    @property
    def before_curarg(self):
        """All arguments up to current argument"""
        if self._curarg_index is None:
            return self
        else:
            return self[:self._curarg_index]

    @property
    def curarg_index(self):
        """Index of currently focused argument"""
        return self._curarg_index

    @curarg_index.setter
    def curarg_index(self, index):
        self._curarg_index = index

    @property
    def curarg_curpos(self):
        """Cursor position in currently focused argument"""
        curarg = self.curarg
        if curarg is not None:
            return curarg.curpos

    @curarg_curpos.setter
    def curarg_curpos(self, curpos):
        curarg = self.curarg
        if curarg is not None:
            curarg.curpos = curpos

    def posargs(self, options={}):
        """
        Return copy without options and parameters for options

        `options` is a mapping that maps tuples of option names
        (e.g. `('--output', '-o')`) to one of these values:

            <int> - Remove <int> arguments after these options
            "*"   - Remove all arguments after these options until an argument
                    that starts with "-" is encountered
        """
        return Args(*remove_options(self, self.curarg_index, self.curarg_curpos, options))

    def params(self, option, maxparams=None):
        """
        Return list of parameters for `option`

        `option` is either the name of an option (e.g. "-h" or "--help") or an
        iterable of names.

        `max` is the maximum number of parameters to return.
        """
        # Find index of option
        option_index = None
        if isinstance(option, str):
            for i,arg in enumerate(self):
                if arg == option:
                    option_index = i
                    break
        elif isinstance(option, abc.Iterable):
            opts = tuple(option)
            for i,arg in enumerate(self):
                if any(arg == o for o in opts):
                    option_index = i
                    break
        # Get parameters that follow option
        params = []
        curarg_index = None
        curarg_curpos = None
        if option_index is not None:
            stop = option_index + maxparams + 1 if maxparams is not None else len(self)
            for i in range(option_index + 1, stop):
                try:
                    arg = self[i]
                except IndexError:
                    break
                if arg and arg[0] == '-':
                    break
                params.append(arg)
                if arg.curpos is not None:
                    curarg_curpos = arg.curpos
                    curarg_index = i - option_index - 1
        return Args(params, curarg_index, curarg_curpos)

    def nth_posarg_index(self, n, options={}):
        """
        Return index of `n`th positional argument (any argument that isn't an option
        or a parameter for an option)

        Return None if there are no positional arguments.

        See `posargs` for documentation on the `options` argument.
        """
        return get_nth_posarg_index(n, self, options)

    def remove_empty(self):
        """Return new Args object with any empty ("") arguments removed"""
        new_args = []
        new_curarg_index = self.curarg_index
        new_curarg_curpos = self.curarg_curpos
        for i,arg in enumerate(self):
            if len(arg) >= 1:
                new_args.append(arg)
            elif self.curarg_index > i:
                new_curarg_index -= 1
        return Args(new_args,
                    curarg_index=min(new_curarg_index, len(new_args) - 1),
                    curarg_curpos=new_curarg_curpos)

    def __getitem__(self, item):
        if isinstance(item, slice):
            subargs = super().__getitem__(item)
            if not subargs:
                # Args are never really empty
                subargs = ('',)
                curarg_index = curarg_curpos = None
            elif item.step is not None:
                raise RuntimeError('Slicing with steps is not implemented yet')
            elif self.curarg_index is None or self.curarg_curpos is None:
                # No cursor position specifed
                curarg_index = curarg_curpos = None
            else:
                start = item.start if item.start is not None else 0
                stop  = item.stop  if item.stop  is not None else len(self)
                if ((item.start is None or item.start <= self.curarg_index) and
                    (item.stop is None or item.stop > self.curarg_index)):
                    # Cursor is between `start` and `stop` or on `start`
                    curarg_index = self.curarg_index - start
                    curarg_curpos = self.curarg_curpos
                elif self.curarg_index == start - 1 and self.curarg_curpos == len(self.curarg):
                    # Cursor is after the last character of the argument before
                    # `start`, i.e. just before our slice.  This is essentially
                    # the same position as on the first character of the
                    # argument at `start`.
                    # Example: ['a|', 'b', 'c'][1:]  ->  ['|b', 'c']
                    curarg_index = self.curarg_index - start + 1
                    curarg_curpos = 0
                elif self.curarg_index == stop and self.curarg_curpos == 0:
                    # Cursor is on the first character of the argument at
                    # `stop`, i.e. just after our slice.  This is essentially
                    # the same position as after the last character of the
                    # argument at `stop`.
                    # Example: ['a', 'b', '|c'][:2]  ->  ['a', 'b|']
                    curarg_index = self.curarg_index - start - 1
                    curarg_curpos = len(subargs[-1])
                    curarg_curpos = len(subargs[-1])
                else:
                    curarg_index = curarg_curpos = None
            return Args(subargs, curarg_index=curarg_index, curarg_curpos=curarg_curpos)
        else:
            return super().__getitem__(item)

    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return NotImplemented
        return (super().__eq__(other) and
                self.curarg_index == other.curarg_index and
                self.curarg_curpos == other.curarg_curpos)

    def __hash__(self):
        return super().__hash__()

    def __repr__(self):
        string = '%s(%s' % (type(self).__name__, tuple(str(arg) for arg in self))
        if self.curarg_index is not None:
            string += ', curarg_index=%d' % (self.curarg_index,)
        if self.curarg_curpos is not None:
            string += ', curarg_curpos=%d' % (self.curarg_curpos,)
        return string + ')'
