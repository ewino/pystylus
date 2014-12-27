import re
from models import Token, ValuableToken

Match = type(re.match('', ''))

operator_aliases = {
    'and': '&&',
    'or': '||',
    'is': '==',
    'isnt': '!=',
    'is not': '!=',
    ':=': '?='
}


class StylusLexer(object):
    def __init__(self, input_buffer):
        super(StylusLexer, self).__init__()
        self.line_num = 1
        self.column = 1

        # Remove BOM
        if input_buffer.startswith(u'\ufeff'):
            input_buffer = self.buf[1:]

        input_buffer = re.sub(r'\s+$', '\n', input_buffer)  # Normalize EOF
        input_buffer = re.sub(r'\r\n?', '\n', input_buffer, flags=re.MULTILINE)  # Normalize line breaks
        input_buffer = re.sub(r'\\ *\n', '\r', input_buffer, flags=re.MULTILINE)  # Trailing backslashes at end of line

        self.peeked_tokens = []
        self.indents = []
        self.prev = None

        # helpers
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
        if isinstance(amount, Match):
            amount = amount.end() + 1  # end() is the position of the last letter
        self.buf = self.buf[amount:]
        self.column += amount

    def lookahead(self, skip=1):
        """
        Return the token `skip` tokens from the current position
        :param int skip: The number of tokens to 'advance'. 1 (for the next token) or more.
        :return:
        """
        for _ in xrange(skip - len(self.peeked_tokens)):
            self.peeked_tokens.append(self._lex_next())
        return self.peeked_tokens[skip - 1]

    def next(self):
        """
        Returns the next token. Either from cache or from consuming the input buffer
        :return: a token, if exists
        :rtype: Token
        """
        token = self.peeked_tokens.pop(0) if self.peeked_tokens else self._lex_next()
        self.prev = token
        return token

    def _match(self, pattern, flags=0, with_spaces=False):
        if with_spaces:
            pattern += r'[ \t]*'
        return re.match(pattern, self.buf, flags)

    def _lex_next(self):
        token = (
            self._l_eof()
            or self._l_null()
            or self._l_statement_sep()

            or self._l_urlchars()

            or self._l_escaped_char()

            or self._l_literal_css()

            or self._l_eol()
            or self._l_space()
        )
        token.line_num = self.line_num
        token.column = self.column
        return token

    def _l_eof(self):
        """ Try to match the end of the input, and simulates outdents in the end of the input if necessary """
        if self.buf:
            return
        if self.indents > 0:
            self.indents.pop()
            return OutdentToken()
        return EOFToken()

    def _l_null(self):
        """ Try to match null tokens """
        match = self._match(r'(null)\b', with_spaces=True)
        if match:
            self._skip(match)
            # TODO: implement this once I figure out how this magically works (ewino@2014-12-26)
            # if self.is_in_selector:
            #     return EntityToken(match.group(1))
            return NullToken()

    def _l_urlchars(self):
        """ Try to match misc chars inside of url() parens """
        if not self.is_in_url:
            return
        match = self._match(r'[/:@.;?&=*!,<>#%0-9]+')
        if match:
            self._skip(match)
            return LiteralToken(match.string.group())

    def _l_statement_sep(self):
        """ Try to match a semicolon """
        match = self._match(';', with_spaces=True)
        if match:
            self._skip(match)
            return SemicolonToken()

    def _l_eol(self):
        """ Try to find an end of line, advance the line num,
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

    def _l_escaped_char(self):
        """ Try to match an escaped char """
        match = self._match(r'\\(.)', with_spaces=True)
        if match:
            self._skip(match)
            return EntityToken(match.group(1))

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

    _l_important = lex('!important', lambda m: EntityToken('!important'), with_spaces=True)
    """ Try to match the "!important" keyword """

    _l_brace = lex('[{}]', lambda m: BraceToken(m.group() == '{'))
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

    def _l_keyword(self):
        """ Try to match the keywords: if, else, unless, return, for, in """
        match = self._match(r'(return|if|else|unless|for|in)\b', with_spaces=True)
        if match:
            self._skip(match)
            # TODO: implement this once I figure out how this magically works (ewino@2014-12-26)
            # if self.is_in_selector:
            #     return EntityToken(match.group(0))
            return KeywordToken(match.group(1))

    def _l_textual_operator(self):
        """ Try to match the operators: not, and, or, is, is not, isnt, is a, is defined """
        match = self._match(r'(not|and|or|is a|is defined|isnt|is not|is)(?!-)\b([ \t]*)')
        if match:
            self._skip(match)
            # if self.is_in_selector:
            #     return EntityToken(match.group(0))
            op = match.group(1)
            return OperatorToken(operator_aliases.get(op, op), spaces=match.group(2))

    def _l_operator(self):
        """ Try to match the operators: ',', +, +=, -, -=, *, *=, /, /=, %, %=, **, !, &, &&, ||, >, >=, <, <=, =,
        ==, !=, !, ~, ?=, :=, ?, :, [, ], ., .., ...,
        """
        match = self._match(r'(\.{1,3}|&&|\|\||[!<>=?:]=|\*\*|[-+*/%]=?|[,=?:!~<>&\[\]])([ \t]*)')
        if match:
            self._skip(match)
            self.is_in_url = False
            op = match.group(1)
            return OperatorToken(operator_aliases.get(op, op), spaces=match.group(2))

    _l_anon_func = lex('@(', lambda m: AnonymousFunctionToken())
    """ Try to match an anonymous function start (starts with '@(') """

    def _l_atrule(self):
        """ Try to match keywords starting with an at sign (@) """
        match = self._match(r'@(?:-(\w+)-)?([\w-]+)', with_spaces=True)
        if match:
            vendor_prefix = match.group(1)
            rule = match.group(2)
            if rule in ('require', 'import', 'charset', 'namespace', 'media', 'scope', 'supports'):
                return AtRuleToken(rule)
            if rule == 'document':
                return AtRuleToken('-moz-document')
            if rule == 'block':
                return AtRuleToken('atblock')
            if rule in ('extend', 'extends'):
                return AtRuleToken('extend')
            if rule == 'keyframes':
                return KeyframesToken(vendor_prefix)
            return AtRuleToken('-%s-%s' % (vendor_prefix, rule) if vendor_prefix else rule)

    def _l_comment(self):
        """ Try to match a CSS multi-line comment or stylus' single-line comment """
        return self._l_stylus_comment() or self._l_css_comment()

    def _l_stylus_comment(self):
        """ Try to match stylus' single-line comment. It's ignored by the parser/lexer """
        if self.buf.startswith('//'):
            comment_end = self.buf.find('\n')
            if comment_end == -1:
                comment_end = len(self.buf)
            self._skip(comment_end)
            return self._lex_next()

    def _l_css_comment(self):
        """ Try to match a CSS multi-line comment """
        if self.buf.startswith('/*'):
            comment_end = self.buf.find('*/') + 2  # len('*/')
            if comment_end == 1:  # not found + len('*/')
                comment_end = len(self.buf)
            content = self.buf[:comment_end]

            self.line_num += content.count('\n')
            self._skip(comment_end)

            # TODO: Find out what this means (ewino@2014-12-27)
            is_suppress = (content[3] != '!')  # /*!
            if not is_suppress:
                content = content[:2] + content[3:]  # timed to be faster than replace('*!', '*', 1)
            # TODO: Shouldn't this be decided by the parser? (also considering line breaks) (ewino@2014-12-27)
            is_inline = self.prev and isinstance(self.prev, SemicolonToken)
            return CommentToken(content, is_suppress, is_inline)

    _l_bool = lex(r'(true|false)\b([ \t]*)', lambda m: BooleanValueToken(m.group(1) == 'true', m.group(2)))
    """ Try to match a true/false value """

    _l_unicode = lex(r'u\+[0-9a-f?]{1,6}(?:-[0-9a-f]{1,6})?', lambda m: LiteralToken(m.group(0)))


def lex(regex, token_func, with_spaces=False):
    """ Tries to match the regex from the beginning of the buffer.
    If it matches, consume all of it (via _skip()) and call token_func with the match
    :param str regex: The regular expression for the token
    :param (Match)->Token token_func: Function to call with the match to return a token
    :param with_spaces: Whether to add [ \t]+ to the end of the regex
    :return: The token from token_func or None
    """
    def lex_func(self):
        match = self._match(regex, with_spaces=with_spaces)
        if match:
            self._skip(match)
            return token_func(match)
    return lex_func


class OutdentToken(Token):
    """  indentation is lesser than previous line """
    pass


class EOFToken(Token):
    """ End of the input """
    pass


class NullToken(Token):
    """ The null keyword """
    pass


class LiteralToken(ValuableToken):
    """ No, this is not ~literally~ a token. It marks literal values. """
    pass


class LiteralCSSToken(LiteralToken):
    """ Literal CSS that should be copied directly to the output """
    pass


class SemicolonToken(Token):
    """ A semi-colon (;) """
    pass


class SpaceToken(Token):
    """ I'm in space! """
    pass


class EntityToken(ValuableToken):
    pass


class BraceToken(ValuableToken):
    def __init__(self, is_opening):
        """
        :param bool is_opening: Whether this is an opening brace '{'. False for closing one '}'
        """
        super(BraceToken, self).__init__('{' if is_opening else '}')
        self.is_opening = is_opening


class ParenToken(ValuableToken):
    def __init__(self, is_opening):
        """
        :param bool is_opening: Whether this is an opening paren '('. False for closing one ')'
        """
        super(ParenToken, self).__init__('(' if is_opening else ')')
        self.is_opening = is_opening


class KeywordToken(ValuableToken):
    pass


class OperatorToken(ValuableToken):
    def __init__(self, val, spaces):
        """ An operator (==, &&, ||, etc...)
        :param val: The operator
        :param spaces: The spaces after the operator
        """
        super(OperatorToken, self).__init__(val)
        # TODO: Find out why this is needed (ewino@2014-12-26)
        self.spaces = spaces


class FunctionToken(ValuableToken):
    pass


class AnonymousFunctionToken(FunctionToken):
    def __init__(self):
        super(AnonymousFunctionToken, self).__init__('anonymous')


class AtRuleToken(KeywordToken):
    def __init__(self, val):
        super(AtRuleToken, self).__init__(val)


class KeyframesToken(AtRuleToken):
    def __init__(self, vendor):
        super(KeyframesToken, self).__init__('keyframes')
        self.vendor = vendor


class CommentToken(ValuableToken):
    def __init__(self, content, is_suppress, is_inline):
        super(CommentToken, self).__init__(content)
        self.is_suppress = is_suppress  # TODO: Is this needed? (or we can just drop the token) (ewino@2014-12-27)
        self.is_inline = is_inline


class BooleanValueToken(ValuableToken):
    def __init__(self, val, space):
        """ A boolean value: True or False
        :param space: The spaces after the value
        :type val: bool
        """
        super(BooleanValueToken, self).__init__(val)
        self.spaces = space
