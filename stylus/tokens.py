from ast.values import Color


__all__ = ['OutdentToken', 'IndentToken', 'EOFToken', 'NullToken', 'LiteralToken',
           'SelectorToken', 'LiteralCSSToken', 'SemicolonToken', 'SpaceToken',
           'IdentifierToken', 'OpeningBraceToken', 'ClosingBraceToken', 'ParenToken',
           'KeywordToken', 'OperatorToken', 'FunctionToken', 'AnonymousFunctionToken',
           'AtRuleToken', 'KeyframesToken', 'CommentToken', 'BooleanValueToken',
           'NewLineToken', 'NumberToken', 'StringToken', 'ColorToken']


class Token(object):
    """ A generic token """
    def __init__(self):
        super(Token, self).__init__()
        self.line_num = 0
        self.column = 0

    def __repr__(self):
        return '<%s at %d:%d>' % (type(self).__name__, self.line_num,
                                  self.column)


class ValuableToken(Token):
    """ A token with a value """

    def __init__(self, val):
        super(ValuableToken, self).__init__()
        self.val = val

    def __str__(self):
        return self.val

    def __repr__(self):
        return '<%s (%r) at %d:%d>' % (type(self).__name__, self.val,
                                       self.line_num, self.column)


class OutdentToken(Token):
    """  indentation is lesser than previous line """
    pass


class IndentToken(Token):
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


class IdentifierToken(ValuableToken):
    pass


class OpeningBraceToken(Token):
    """ An opening brace ('{') """


class ClosingBraceToken(Token):
    """ A closing brace ('}') """


class ParenToken(ValuableToken):
    def __init__(self, is_opening):
        """
        :param bool is_opening: Whether this is an opening paren '('.
            False for closing one ')'
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


class FunctionToken(IdentifierToken):
    def __init__(self, name, space=''):
        super(FunctionToken, self).__init__(name)
        self.space = space


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
        # TODO: Is this needed? (or can we drop the token) (ewino@2014-12-27)
        self.is_suppress = is_suppress
        self.is_inline = is_inline


class BooleanValueToken(ValuableToken):
    def __init__(self, val, space):
        """ A boolean value: True or False
        :param space: The spaces after the value
        :type val: bool
        """
        super(BooleanValueToken, self).__init__(val)
        self.spaces = space


class NewLineToken(Token):
    pass


class NumberToken(ValuableToken):
    """ A number with an optional unit (2, -5.2, 16px, 80.3%) """
    def __init__(self, val, raw, unit=None):
        super(NumberToken, self).__init__(val)
        self.raw = raw
        self.unit = unit


class StringToken(ValuableToken):
    """ A string value (containing the type of the surrounding quotes) """
    def __init__(self, val, quote):
        super(StringToken, self).__init__(val)
        self.quote = quote


class ColorToken(ValuableToken):
    """ A color value """
    def __init__(self, r, g, b, a):
        super(ColorToken, self).__init__(Color(r, g, b, a))


class SelectorToken(ValuableToken):
    """ A part of a selector """
    pass
