"""
In this package there will be types used to construct the AST of the stylus
language. It will be convertible to stylus or css tokens and strings
"""


class ASTNode(object):
    postfix_allowed = False
    pass


class Statement(ASTNode):
    pass


class Block(ASTNode):
    def __init__(self, parent):
        """
        :param Block|None parent: Parent block
        """
        super(Block, self).__init__()
        self.parent = parent
        self.statements = []
        """ type: list[Statement] """


class Root(Block):
    """
    This represents the root node of the AST, one with no parents
    """
    def __init__(self):
        super(Root, self).__init__(parent=None)


class Expression(ASTNode):
    @property
    def value(self):
        raise NotImplementedError()


class FunctionCall(Expression):
    pass


class Identifier(Expression):
    """ A named identifier and a value assigned to it"""

    def __init__(self, name, value=None, is_mixin=False):
        # TODO: What's the deal with the mixin parameter? (ewino@2015-01-23)
        self.name = name
        self._value = value

    def value(self):
        return self._value


class Conditional(Expression):
    """
    A conditional expression with a condition, and values (or statements) for
    when it is true or false
    """
    # TODO: Implement this (value should return after evaluating the
    # condition expression as boolean and deciding (ewino@2015-01-23)

    def __init__(self, condition, true_block=None, negate=False,
                 is_postfix=False):
        self.condition = condition
        # TODO: replace negate with unary not operator (ewino@2015-01-23)
        self.negate = bool(negate)
        self.block = true_block
        self.else_block = None
        self.is_postfix = is_postfix


class LoopBlock(Block):
    def __init__(self, parent, val_name, loop_expr, key_name=None):
        super(LoopBlock, self).__init__(parent)
        self.val_name = val_name
        self.key_name = key_name
        self.loop_expr = loop_expr


class SelectorBlock(Block):
    def __init__(self, selectors):
        super(SelectorBlock, self).__init__(parent=None)
        self.selectors = []
        if selectors:
            if isinstance(selectors, basestring):
                selectors = [selectors]
            if isinstance(selectors, list):
                self.selectors += selectors
