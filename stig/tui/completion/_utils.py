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


def _parse(string):
    """
    Yield (<char>, <special>, <escaped>, <quoted>) tuples

    <char> is the current character

    <special> is True if <char> is backslash, space or quote and interpreted as
    such (i.e. not escaped or quoted), False otherwise

    <escaped> is True if the previous character was an interpreted backslash,
    False otherwise

    <quoted> is the closing quote character we're looking for, otherwise it's an
    empty string (it's empty for the opening and closing quotes)

    <nextchar> is the character after <char> or None if <char> is the last
    character
    """
    escaped = False
    quoted = ''
    i_max = len(string) - 1
    special_chars = (' ', '\\', '"', "'")
    for i,char in enumerate(string):
        nextchar = string[i+1] if i < i_max else None
        if not escaped:
            # Backslash is plain text between quotes except when it escapes the
            # enclosing quote (e.g. "foo \" bar" -> <foo " bar>)
            if char == '\\' and (not quoted or nextchar == quoted or nextchar == '\\'):
                log.debug('    char=%r, special=%r, escaped=%r, quoted=%r, next=%r',
                          char, True, escaped, quoted, nextchar)
                yield (char, True, escaped, quoted, nextchar)
                escaped = True
                continue
            elif (char == '"' or char == "'"):
                if quoted == char and not escaped:
                    quoted = ''
                    log.debug('    char=%r, special=%r, escaped=%r, quoted=%r, next=%r',
                              char, True, escaped, quoted, nextchar)
                    yield (char, True, escaped, quoted, nextchar)
                    continue
                elif not quoted:
                    log.debug('    char=%r, special=%r, escaped=%r, quoted=%r, next=%r',
                              char, True, escaped, quoted, nextchar)
                    yield (char, True, escaped, quoted, nextchar)
                    quoted = char
                    continue

        special = char.isspace() and not escaped and not quoted
        log.debug('    char=%r, special=%r, escaped=%r, quoted=%r, next=%r',
                  char, special, escaped, quoted, nextchar)
        yield (char, special, escaped, quoted, nextchar)
        escaped = False


_special_chars = ('\\', ' ', "'", '"')

def escape(string, curpos=None):
    """
    Prepend a backslash to special characters: backslash, space, single quote,
    double quote

    If `curpos` is not None, it is the position of the cursor in `string`, and
    the return value is a 2-tuple of (<escaped string>, <new cursor position>).
    """
    string_escaped = []
    curpos_diff = 0
    for i,(char,special,escaped,quoted,nextchar) in enumerate(_parse(string)):
        if char in _special_chars:
            string_escaped.append('\\')
            if curpos is not None and i < curpos:
                curpos_diff += 1
        string_escaped.append(char)

    if curpos is None:
        return ''.join(string_escaped)
    else:
        return ''.join(string_escaped), curpos + curpos_diff


def quote(string, curpos=None):
    """
    Quote `string` if it contains special characters: backslash, space, single
    quote, double quote

    If `curpos` is not None, it is the position of the cursor in `string`, and
    the return value is a 2-tuple of (<quoted string>, <new cursor position>).
    """
    if all(special_char not in string for special_char in _special_chars):
        new_string = string
    elif "'" not in string:
        new_string = "'%s'" % (string,)
    elif '"' not in string:
        new_string = '"%s"' % (string,)
    else:
        new_string = "'%s'" % (string.replace("'", r"\'"),)

    if curpos is None:
        return new_string
    else:
        if len(new_string) == len(string):
            # No quotes were added
            return new_string, curpos
        else:
            new_curpos = curpos + 1  # Opening quote
            # If double and single quotes are in string, add the number of
            # escaped quotes up to cursor position
            quote = new_string[0]
            escaped_quotes = string[:new_curpos].count(quote)
            new_curpos += escaped_quotes
            if curpos >= len(string):
                new_curpos = new_curpos + 1  # Closing quote
            return new_string, new_curpos


def is_escaped(string):
    """
    Return whether `string` uses backslashes to escape special characters
    """
    for char,special,escaped,quoted,nextchar in _parse(string):
        if special:
            if char == '\\': return True
            if char in ('"', "'"): return False
    return False


_trailing_whitespace_regex = re.compile(r'(\s*)$')
def _get_trailing_whitespace(string):
    match = _trailing_whitespace_regex.search(string)
    if match:
        return match.group(1)
    else:
        return ''


def plaintext(string, curpos=None):
    """
    Remove any quotes or backslashes from `string` unless they are escaped or
    quoted

    If `curpos` is not None, it is the position of the cursor in `string`, and
    the return value is a 2-tuple of (<plaintext string>, <new cursor position>).
    """
    if curpos is not None:
        log.debug('  Converting to plain text: %r', string[:curpos] + '|' + string[curpos:])

    literal = []
    # trailing_whitespace = tuple(_get_trailing_whitespace(string))

    # Remove leading whitespace
    string_lstripped = string.lstrip()
    if curpos is not None:
        # Adjust cursor position to account for rmeoved leading whitespace
        curpos = new_curpos = max(0, curpos - (len(string) - len(string_lstripped)))
    else:
        new_curpos = None

    # Find index of first character of trailing whitespace
    trailing_spaces = len(string_lstripped) - len(string_lstripped.rstrip())
    log.debug('Found %r trailing whitespaces', trailing_spaces)
    trailing_spaces_pos = len(string_lstripped) - (trailing_spaces)
    log.debug('First trailing whitespace: %r', trailing_spaces_pos)

    for i,(char,special,escaped,quoted,nextchar) in enumerate(_parse(string_lstripped)):
        if not special:
            log.debug('      Appending %r because not special', char)
            literal.append(char)
        elif char == ' ' and i < trailing_spaces_pos:
            log.debug('      Appending %r because space before trailing whitespace (%r < %r)',
                      char, i, trailing_spaces_pos)
            literal.append(char)
        elif escaped or (quoted and nextchar != quoted and nextchar != '\\'):
            log.debug('      Appending %r because escaped (%r) or quoted (%r)', char, escaped, quoted)
            literal.append(char)

        elif new_curpos is not None and new_curpos > 0 and i < curpos:
            log.debug('      Reducing %r by 1 because of %r', new_curpos, char)
            new_curpos -= 1

    if new_curpos is None:
        return ''.join(literal)
    else:
        log.debug('  Plain text: %r', ''.join(literal[:new_curpos]) + '|' + ''.join(literal[new_curpos:]))
        return ''.join(literal), min(new_curpos, len(literal))


def tokenize(cmdline, delims=(' ',)):
    """
    Split `cmdline` into list of tokens
    """
    log.debug('Tokenizing %r', cmdline)
    tokens = []
    token = []
    prev_char, prev_escaped, prev_quoted = '', False, False
    for i_char,(char,special,escaped,quoted,nextchar) in enumerate(_parse(cmdline)):
        if char in delims and not escaped and not quoted:
            if token:
                tokens.append(''.join(token))
                log.debug('      Appended token: %r', tokens[-1])
                token.clear()
            tokens.append(char)
            log.debug('      Appended delimiter: %r', char)

        elif prev_char in delims and not prev_escaped and not prev_quoted:
            if token:
                tokens.append(''.join(token))
                log.debug('      Appended token: %r', tokens[-1])
                token.clear()
            token.append(char)
        else:
            token.append(char)
            log.debug('      Added %r to %r', char, ''.join(token))
        prev_char, prev_escaped, prev_quoted = char, escaped, quoted

    # Append final token if it's not empty or if cmdline is an empty string so
    # don't return an empty list
    if token or not tokens:
        tokens.append(''.join(token))
    log.debug('Tokenized: %r', tokens)
    return tokens


def get_position(tokens, curpos, delims=(' ',)):
    """
    Find focused index in `tokens`

    `tokens` is a list of tokens as returned by `tokenize`.

    `curpos` is the cursor position in the concatenated `tokens`.

    If the cursor is at the beginning or end of the command line or if there's a
    delimiter both before and under the cursor, an empty token is inserted at
    that point and the cursor is placed on it.

    Return `(tokens, curtok_index, curtok_curpos)`
    """
    # Default cursor position is after the last character of the last argument
    curtok_index = len(tokens) - 1
    curtok_curpos = len(tokens[curtok_index])

    log.debug('Finding cursor position %r in %r', curpos, tokens)
    for i,token in enumerate(tokens):
        token_len = len(token)
        log.debug('  Token: %r: %r', token_len, token)
        curpos -= token_len
        log.debug('    New cursor position: %r', curpos)
        if curpos <= 0:
            curtok_index = i
            curtok_curpos = token_len + curpos
            break
    log.debug('  Initial: Current token: %r, Cursor position: %r', curtok_index, curtok_curpos)

    # Make sure we don't focus a delimiter
    curtok = tokens[curtok_index]
    curtok_index_max = len(tokens) - 1
    curtok_curpos_max = len(curtok)
    if curtok in delims:
        prev_token = tokens[curtok_index-1] if curtok_index > 0 else None
        next_token = tokens[curtok_index+1] if curtok_index < curtok_index_max else None
        log.debug('  Previous token: %r', prev_token)
        log.debug('  Next token: %r', next_token)

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
    # the command line or there are multiple tokens.  We insert an empty token
    # and move the cursor on it.  This doesn't change the command line and
    # completion candidates can replace the empty token without changing the
    # other tokens.
    curtok = tokens[curtok_index]
    curtok_index_max = len(tokens) - 1
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

        # If the cursor is somewhere not at the beginning/end of the token,
        # split the token at the cursor position, insert the empty token between
        # them and replace the current token with these three tokens.
        else:
            log.debug('  Inserting empty token in the middle of the current')
            subtoks = (token[curtok_curpos:], '', token[curtok_curpos:])
            log.debug('  Replacing %r with %r', curtok, subtoks)
            tokens[curtok_index:curtok_index+1] = subtoks
            curtok_index += 1
            curtok_curpos = 0

    log.debug('  Final: Current token: %r, Cursor position: %r', curtok_index, curtok_curpos)
    log.debug('  Tokens: %r', tokens)
    return tokens, curtok_index, curtok_curpos


class Arg(str):
    def __new__(cls, arg, curpos=None):
        obj = super().__new__(cls, arg)
        obj._curpos = curpos
        obj._parts = (str(obj),)
        obj._curpart = obj._parts[0]
        obj._curpart_index = 0
        obj._curpart_curpos = curpos
        obj._separators = ()
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

    @property
    def separators(self):
        """
        Sequence of separator strings that split argument into multiple parts

        Setting this also changes `curpart` and `curpart_curpos`.
        """
        return self._separators
    @separators.setter
    def separators(self, separators):
        if not separators:
            self._parts = (str(self),)
            self._curpart = self._parts[0]
            self._curpart_index = 0
            self._curpart_curpos = self.curpos
        else:
            split_regex = r'(?:' + '|'.join(re.escape(str(sep)) for sep in separators) + ')'
            self._parts = tuple(re.split(split_regex, self))
            curpart_curpos = self.curpos
            for i,part in enumerate(self._parts):
                len_part = len(part)
                len_sep = len(separators)
                if curpart_curpos > len_part:
                    curpart_curpos -= len_part + len_sep
                else:
                    self._curpart = part
                    self._curpart_index = i
                    break
            self._curpart_curpos = curpart_curpos
        self._separators = separators

    @property
    def parts(self):
        return self._parts

    @property
    def curpart(self):
        return self._curpart

    @property
    def curpart_index(self):
        return self._curpart_index

    @property
    def curpart_curpos(self):
        return self._curpart_curpos

    def __repr__(self):
        string = '%s(%r' % (type(self).__name__, str(self),)
        if self.curpos is not None:
            string += ', curpos=%d' % (self.curpos,)
        return string + ')'


def as_args(tokens, curtok_index, curtok_curpos, delims=(' ',)):
    """
    Remove delimiters and interpreted special characters from `tokens` and
    adjust `curtok_index` and `curtok_curpos` accordingly
    """
    log.debug('  Converting to arguments: %r', tokens)
    log.debug('    curtok_index=%r, curtok_curpos=%r', curtok_index, curtok_curpos)

    def is_delim(token):
        return bool(token) and all(char in delims for char in token)

    args = []
    curarg_index = curtok_index
    curarg_curpos = curtok_curpos
    curtok_index_max = len(tokens) - 1
    for i,token in enumerate(tokens):
        log.debug('Token %s: %r', i, token)
        # Append non-delimiter tokens
        if not is_delim(token):
            log.debug('Not a delimiter: %r', token)
            if i == curtok_index:
                arg, curarg_curpos = plaintext(token, curtok_curpos)
                args.append(Arg(arg, curpos=curarg_curpos))
                log.debug('    Token %r: %r: Added current argument: %r',
                          i, token, arg[:curarg_curpos] + '|' + arg[curarg_curpos:])
            else:
                args.append(Arg(plaintext(token)))
                log.debug('    Token %r: %r: Added argument: %r', i, token, args[-1])

        # Adjust current argument index as long as we haven't passed the current
        # token yet
        elif i < curtok_index:
            log.debug('A delimiter left of cursor (%s < %s): %r', i, curtok_index, token)
            curarg_index -= 1
            log.debug('    Token %r: %r: Reduced curarg_index by %r: %r', i, token, len(token), curarg_index)
        else:
            log.debug('A delimiter not left of cursor (%s >= %s): %r', i, curtok_index, token)

    # Ensure args has at least one empty string to avoid catching IndexErrors
    if not args:
        args.append(Arg('', curpos=0))
        curarg_index = curarg_curpos = 0

    log.debug('  Args:%r, curarg_index:%r, curarg_curpos:%r', args, curarg_index, curarg_curpos)
    return args, curarg_index, curarg_curpos


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
