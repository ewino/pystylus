import re

from .tokens import *
from utils import chunks
from css_consts import units

__all__ = ['StylusLexer']

Match = type(re.match('', ''))

operator_aliases = {
    'and': '&&',
    'or': '||',
    'is': '==',
    'isnt': '!=',
    'is not': '!=',
    ':=': '?='
}


def lex(regex, token_func, with_spaces=False):
    """ Tries to match the regex from the beginning of the buffer.
    If it matches, consume all of it (via _skip()) and call token_func with the
    match
    :param str regex: The regular expression for the token
    :param (Match)->Token token_func: Function to call with the match to return
        a token
    :param with_spaces: Whether to add [ \t]+ to the end of the regex
    :return: The token from token_func or None
    """
    def lex_func(self):
        """
        :type self: StylusLexer
        """
        match = self._match(regex, with_spaces=with_spaces)
        if match:
            self._skip(match)
            return token_func(match)
    return lex_func


class StylusLexer(object):
    def __init__(self, input_buffer):
        super(StylusLexer, self).__init__()
        self.line_num = 1
        self.column = 1

        # Remove BOM
        if input_buffer.startswith(u'\ufeff'):
            input_buffer = self.buf[1:]

        # Normalize EOF
        input_buffer = re.sub(r'\s+$', '\n', input_buffer)
        # Normalize line breaks
        input_buffer = re.sub(r'\r\n?', '\n', input_buffer, flags=re.MULTILINE)
        # Backslash at line end means to continue at the next line
        input_buffer = re.sub(r'\\ *\n', '\r', input_buffer, flags=re.MULTILINE)

        self.stash = []  # where we store peeked tokens
        self.indents = []
        self.prev = None
        self.indentation_type = None

        # state
        self.is_in_url = False

        # TODO: integrate this after understanding why it's here
        # .replace(/([,(:](?!\/\/[^ ])) *(?:\/\/[^\n]*)?\n\s*/g, comment)
        # .replace(/\s*\n[ \t]*([,)])/g, comment);
        self.buf = self.original_buffer = input_buffer

    def _skip(self, amount):
        """
        Consumes the amount of characters from the beginning of the buffer
        :param (int|Match) amount: The amount of characters to consume
        """
        match = None
        has_linebreak = False
        if isinstance(amount, Match):
            match = amount.group()
            has_linebreak = '\n' in match
            amount = len(match)
        self.buf = self.buf[amount:]
        if has_linebreak:
            self.line_num += match.count('\n')
            self.column = len(match) - match.rindex('\n')
        else:
            self.column += amount

    def lookahead(self, skip=1):
        """
        Return the token `skip` tokens from the current position
        :param int skip: The number of tokens to 'advance'. 1 or more.
        :return: The token `skip` amount of tokens ahead.
        """
        for _ in xrange(skip - len(self.stash)):
            self.stash.append(self._lex_next())
        return self.stash[skip - 1]

    def next(self):
        """
        Returns the next token. From either cache or the input buffer
        :return: a token, if exists
        :rtype: Token
        """
        token = self.stash.pop(0) if self.stash else self._lex_next()
        self.prev = token
        return token

    def __repr__(self):
        orig_buf = self.buf
        tokens = []
        token = self.next()
        while not isinstance(token, EOFToken):
            tokens.append(token)
            token = self.next()
        self.buf = orig_buf
        return repr(tokens)

    def push_token(self, token):
        """
        Pushes a token to the start of the stash (it will be the
        next one polled)
        :param Token token: The token to add
        """
        self.stash.insert(0, token)

    def _match(self, pattern, flags=0, with_spaces=False):
        """
        Performs a match from the start of the buffer
        :param str pattern: The pattern to match
        :param int flags: Flags to use while matching
        :param bool with_spaces: Whether to capture optional spaces and tabs
            at the end of the match
        :return: The Match object if found. None otherwise
        :rtype: Match
        """
        if with_spaces:
            pattern += r'[ \t]*'
        return re.match(pattern, self.buf, flags)

    def _lex_next(self):
        """
        Consume the next token from the buffer and returns it
        :return: The next token (EOF is used for the end of the buffer)
        :rtype: Token
        """
        line_num = self.line_num
        col = self.column
        token = (
            self._l_eof()
            or self._l_null()
            or self._l_statement_sep()
            or self._l_keyword()
            or self._l_urlchars()
            or self._l_comment()
            or self._l_newline_and_indents()
            or self._l_escaped_char()
            or self._l_important()
            or self._l_literal_css()
            or self._l_anon_func()
            or self._l_atrule()
            or self._l_function_start()
            or self._l_brace()
            or self._l_paren()
            or self._l_color()
            or self._l_string_val()
            or self._l_number()
            or self._l_textual_operator()
            or self._l_bool()
            or self._l_unicode()
            or self._l_identifier()
            or self._l_operator()
            or self._l_eol()
            or self._l_space()
            or self._l_selector()
        )
        token.line_num = line_num
        token.column = col
        return token

    def _l_eof(self):
        """ Try to match the end of the input, and simulates outdents in the
        end of the input if necessary
        """
        if self.buf:
            return
        if self.indents:
            self.indents.pop()
            return OutdentToken()
        return EOFToken()

    def _l_null(self):
        """ Try to match null tokens """
        match = self._match(r'(null)\b', with_spaces=True)
        if match:
            self._skip(match)
            # TODO: implement this once I figure out how is_in_selector
            # TODO: magically works (ewino@2014-12-26)
            # if self.is_in_selector:
            #     return EntityToken(match.group(1))
            return NullToken()

    _l_statement_sep = lex(';', lambda m: SemicolonToken(), with_spaces=True)
    """ Try to match a semicolon """

    def _l_keyword(self):
        """ Try to match the keywords: if, else, unless, return, for, in """
        match = self._match(r'(return|if|else|unless|for|in)\b',
                            with_spaces=True)
        if match:
            self._skip(match)
            # TODO: implement this once I figure out how is_in_selector
            # TODO: magically works (ewino@2014-12-26)
            # if self.is_in_selector:
            #     return EntityToken(match.group(0))
            return KeywordToken(match.group(1))

    def _l_urlchars(self):
        """ Try to match misc chars inside of url() parens """
        if not self.is_in_url:
            return
        match = self._match(r'[/:@.;?&=*!,<>#%0-9]+')
        if match:
            self._skip(match)
            return LiteralToken(match.string.group())

    def _l_comment(self):
        """ Try to match a CSS multi-line comment or stylus' single-line
        comment
        """
        return self._l_stylus_comment() or self._l_css_comment()

    def _l_stylus_comment(self):
        """ Try to match stylus' single-line comment.
        It's ignored by the parser/lexer
        """
        if self.buf.startswith('//'):
            comment_end = self.buf.find('\n')
            if comment_end == -1:
                comment_end = len(self.buf)
            self._skip(comment_end)
            return self._lex_next()

    def _l_css_comment(self):
        """ Try to match a CSS multi-line comment """
        if self.buf.startswith('/*'):
            comment_end = self.buf.find('*/') + 2  # len of '*/'
            if comment_end == 1:  # not found + len of '*/'
                comment_end = len(self.buf)
            content = self.buf[:comment_end]

            self.line_num += content.count('\n')
            self._skip(comment_end)

            # TODO: Find out what this means (ewino@2014-12-27)
            is_suppress = (content[3] != '!')  # /*!
            if not is_suppress:
                # timed to be faster than replace('*!', '*', 1)
                content = content[:2] + content[3:]
            # TODO: Shouldn't this be decided by the parser?
            # TODO: (also considering line breaks) (ewino@2014-12-27)
            is_inline = self.prev and isinstance(self.prev, SemicolonToken)
            return CommentToken(content, is_suppress, is_inline)

    def _l_newline_and_indents(self):
        """ Tries to match a new line and a subsequent indent or outdent """
        match = self._match(r'\n([\t ]*)')
        if match:
            self._skip(match)
            indent = match.group(1)

            # blank line
            if self.buf.startswith('\n'):
                return self._lex_next()

            # Outdent
            prev_indent = self.indents[-1] if self.indents else ''
            if self.indents and self.indents[-1].startswith(indent):
                # NOTE: the JS version only checks the length of the indent
                # NOTE: ('  ' == '\t '). we compare the indentation exactly.
                # NOTE: Now let's see if we pass the tests...
                print 'outing! new indent is %r' % indent
                while self.indents and self.indents[-1].startswith(indent) \
                        and self.indents[-1] != indent:
                    self.stash.append(OutdentToken())
                    self.indents.pop()
                return self.stash.pop()
            # Indent
            elif indent and (not prev_indent or indent.startswith(prev_indent)):
                self.indents.append(indent)
                return IndentToken()
            # New line
            elif indent == prev_indent:
                return NewLineToken()
            # Indentation doesn't match with previous one (neither starts
            # with the other)
            else:
                indent = indent.replace(' ', '<space>').replace('\t', '<tab>')
                prev_indent = self.indents[-1].replace(' ', '<space>')\
                                              .replace('\t', '<tab>')
                raise SyntaxError("Invalid indentation. %r doesn't match with "
                                  "previous indent: %r" % (indent, prev_indent))

    _l_escaped_char = lex(r'\\(.)', lambda m: IdentifierToken(m.group(1)),
                          with_spaces=True)
    """ Try to match an escaped char """

    _l_important = lex('!important', lambda m: IdentifierToken('!important'),
                       with_spaces=True)
    """ Try to match the "!important" keyword """

    def _l_literal_css(self):
        """ Try to match a literal CSS block @css { (...) }
        Try to find it's end when the braces close
        """
        match = self._match(r'@css[ \t]*\{')
        if match:
            self._skip(match)
            braces = 1
            css_buf = ''
            while self.buf and braces > 0:
                c = self.buf[0]
                if c == '{':
                    braces += 1
                elif c == '}':
                    braces -= 1
                elif c == '\n':
                    self.line_num += 1
                css_buf += c
            css_buf = re.sub(r'\s*}$', '', css_buf)
            return LiteralCSSToken(css_buf)

    _l_anon_func = lex('@\(', lambda m: AnonymousFunctionToken())
    """ Try to match an anonymous function start (starts with '@(') """

    def _l_atrule(self):
        """ Try to match keywords starting with an at sign (@) """
        match = self._match(r'@(?:-(\w+)-)?([\w-]+)', with_spaces=True)
        if match:
            vendor_prefix = match.group(1)
            rule = match.group(2)
            if rule in ('require', 'import', 'charset', 'namespace', 'media',
                        'scope', 'supports'):
                return AtRuleToken(rule)
            if rule == 'document':
                return AtRuleToken('-moz-document')
            if rule == 'block':
                return AtRuleToken('atblock')
            if rule in ('extend', 'extends'):
                return AtRuleToken('extend')
            if rule == 'keyframes':
                return KeyframesToken(vendor_prefix)
            return AtRuleToken(rule if not vendor_prefix
                               else '-%s-%s' % (vendor_prefix, rule))

    def _l_function_start(self):
        """ Try to match a function name (ending with an opening paren) """
        match = self._match(r'(-*[_a-zA-Z$][-\w$]*)\(([ \t]*)')
        if match:
            self._skip(match)
            func_name = match.group(1)
            if func_name == 'url':
                self.is_in_url = True
            return FunctionToken(func_name, match.group(2))

    _l_brace = lex('[{}]', lambda m: OpeningBraceToken() if m.group() == '{'
                                     else ClosingBraceToken())
    """ Try to match opening or closing braces '{' or '}' """

    def _l_paren(self):
        """ Try to match opening or closing parens '(' or ')' """
        match = self._match(r'([()])', with_spaces=True)
        if match:
            self._skip(match)
            is_closing = match.group(1) == ')'
            if is_closing:
                self.is_in_url = False
            return ParenToken(not is_closing)

    def _l_color(self):
        """
        Try to match any type of hexadecimal color: #n, #nn, #rgb, #rgba,
        #rrggbb, #rrggbbaa
        """
        if not self.buf.startswith('#'):
            return

        # n(1), nn(2), rgb(3), rgba(4), rrggbb(6), rrggbbaa(8)
        choices = ['[a-fA-F0-9]{%d}' % length for length in (1, 2, 3, 4, 6, 8)]
        match = self._match('#(%s)' % ('|'.join(choices)), with_spaces=True)
        if match:
            self._skip(match)
            hex_num = match.group(1)
            if len(hex_num) in (2, 6, 8):
                parts = map(''.join, chunks(hex_num, 2))  # divide to parts
            else:
                parts = map(lambda c: c * 2, hex_num)  # double each char
            values = tuple(map(lambda c: int(c, 16), parts))  # unhex

            a = 255
            if len(values) == 1:
                r, g, b = values[0] * 3
            elif len(values) == 3:
                r, g, b = values
            else:
                r, g, b, a = values
            return ColorToken(r, g, b, a / 255.0)

    def _l_string_val(self):
        """  Try to match a string, starting and ending with quote marks """
        match = self._match(r'''("[^"]*"|'[^']*')''', with_spaces=True)
        if match:
            self._skip(match)
            val = match.group(1)[1:-1].replace('\\n', '\n')
            quote_type = match.group(1)[0]
            return StringToken(val, quote_type)

    def _l_number(self):
        """ Try to match a number with an optional unit """
        match = self._match(r'^(-?\d+\.\d+|-?\d+|-?\.\d+)(%s)?[ \t]*'
                            % '|'.join(units))
        if match:
            self._skip(match)
            raw = match.group()
            return NumberToken(float(match.group(1)), raw, match.group(2))

    def _l_textual_operator(self):
        """ Try to match the operators: not, and, or, is, is not, isnt,
        is a, is defined
        """
        match = self._match(r'(not|and|or|is a|is defined|'
                            r'isnt|is not|is)(?!-)\b([ \t]*)')
        if match:
            self._skip(match)
            # if self.is_in_selector:
            #     return EntityToken(match.group(0))
            op = match.group(1)
            return OperatorToken(operator_aliases.get(op, op),
                                 spaces=match.group(2))

    _l_bool = lex(r'(true|false)\b([ \t]*)',
                  lambda m: BooleanValueToken(m.group(1) == 'true', m.group(2)))
    """ Try to match a true/false value """

    _l_unicode = lex(r'u\+[0-9a-f?]{1,6}(?:-[0-9a-f]{1,6})?',
                     lambda m: LiteralToken(m.group()))
    """ Unicode escape characters """

    _l_identifier = lex(r'-*[A-Za-z_$][\w$-]*',
                        lambda m: IdentifierToken(m.group()))
    """ Try to match any sort of word that could be an identifier """

    def _l_operator(self):
        """ Try to match the operators: ',', +, +=, -, -=, *, *=, /, /=, %, %=,
        **, !, &, &&, ||, >, >=, <, <=, =, ==, !=, !, ~, ?=, :=, ?, :, [, ], .,
        .., ...,
        """
        match = self._match(r'(\.{1,3}|&&|\|\||[!<>=?:]=|\*\*|[-+*/%]=?|'
                            r'[,=?:!~<>&\[\]])([ \t]*)')
        if match:
            self._skip(match)
            self.is_in_url = False
            op = match.group(1)
            return OperatorToken(operator_aliases.get(op, op),
                                 spaces=match.group(2))

    def _l_eol(self):
        """ Try to find a soft line end (breaking a line with a trailing
        backslash to continue it at the next one), advance the line num,
        then fetch the actual next token
        """
        if self.buf[0] == '\r':
            self._skip(1)
            self.line_num += 1
            return self._lex_next()

    def _l_space(self):
        """ Try to match a space """
        match = self._match('', with_spaces=True)
        if match:
            self._skip(match)
            return SpaceToken()

    _l_selector = lex(r'.*?(?=//(?![^\[]*\])|[,\n{])',
                      lambda m: SelectorToken(m.group()))
    """ Anything that afterwards has a comma, a line break, an opening brace
    or a single-line comment (//) (we also check that the // sign is not inside
    of an attribute selector like "a[href=//]")
    """
