__author__ = 'Ehud'


class Token(object):
    def __init__(self):
        super(Token, self).__init__()
        self.line_num = 0
        self.column = 0

    def __repr__(self):
        return '<%s at %d:%d>' % (type(self).__name__, self.line_num, self.column)


class ValuableToken(Token):
    """ A token with a value """

    def __init__(self, val):
        super(ValuableToken, self).__init__()
        self.val = val

    def __str__(self):
        return self.val

    def __repr__(self):
        return '<%s (%r) at %d:%d>' % (type(self).__name__, self.val, self.line_num, self.column)