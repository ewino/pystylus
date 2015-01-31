
class SyntaxError(Exception):
    pass


class ParseError(Exception):
    def __init__(self, parser, message):
        """
        :param StylusParser parser: the parser that raised the error.
        :param str message: The error text. '{peek}' will be replaced by the
            next token in the parser
        :return:
        """
        super(ParseError, self).__init__(message.format(peek=parser.peek()))
