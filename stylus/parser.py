from contextlib import contextmanager
from ast import Root, FunctionCall, Expression, Conditional, LoopBlock, Block
from ..exceptions import ParseError
from .lexer import StylusLexer
from stylus.tokens import *


class StylusParser(object):
    def __init__(self, input_str, parent_node=None):
        """
        :type parent_node: ast.Block
        """
        super(StylusParser, self).__init__()
        self.lexer = StylusLexer(input_str)
        self.states = []
        self.tok_stash = []  # some states change the tokens because of
        self.parent_node = parent_node or Root()
        self.current_block = self.parent_node
        self.accept = TokenMatcher(self, False)
        self.expect = TokenMatcher(self, True)
        self.matches = TokenMatcher(self, False, consumes=False)
        # context

    def peek(self):
        return self.lookahead(0)

    def lookahead(self, amount):
        if amount < len(self.tok_stash):
            return self.tok_stash[amount]
        return self.lexer.lookahead(amount - len(self.tok_stash) + 1)

    def next(self):
        return self.tok_stash.pop(0) if self.tok_stash else self.lexer.next()

    @contextmanager
    def push_state(self, state):
        self.states.append(state)
        yield
        popped_state = self.states.pop()
        if popped_state != state:
            raise ParseError(self, 'Entered state {0} was never finished'
                                   .format(popped_state))

    @contextmanager
    def push_block(self, block):
        """
        Push the block as the current parent. Restores the parent when we're done
        with the block
        :param Block block: The block to push
        """
        grandparent = self.current_block
        grandparent.statements.push(block)
        self.parent_node = block
        yield
        self.parent_node = grandparent

    def skip_tokens(self, token_type_or_types, token_matcher=None):
        while self.accept(token_type_or_types, token_matcher) is not None:
            self.next()

    def skip_whitespaces(self):
        self.skip_tokens((SpaceToken, IndentToken, OutdentToken, NewLineToken))

    def skip_spaces(self):
        self.skip_tokens(SpaceToken)

    def skip_spaces_and_comments(self):
        self.skip_tokens((SpaceToken, CommentToken))

    def parse(self):
        block = self.parent_node
        with self.push_state('root'):
            self.skip_whitespaces()
            while not isinstance(self.peek(), EOFToken):
                stmt = self._p_statement()
                if not stmt:
                    raise ParseError(self, 'Unexpected token {peek}, '
                                           'not allowed at root level')
                self.accept(SemicolonToken)
                block.statements.append(stmt)
        return block

    def _p_statement(self):
        """
        Matches a statement (as in _p_inner_stmt) with an optional postfix
        """
        stmt = self._p_inner_stmt()
        if isinstance(stmt, postfix_allowed_nodes)\
                and not isinstance(stmt, (Conditional, LoopBlock)):
            pf_token = self.accept.keywords('if', 'unless', 'for')
            while pf_token:
                if pf_token.val in ('if', 'unless'):
                    stmt = Conditional(self._p_expression(), stmt, is_postfix=True,
                                       negate=pf_token.val == 'unless')
                    self.accept(SemicolonToken)
                elif pf_token.val == 'for':
                    val_name = self._p_id_name()
                    key_name = self._p_id_name() if self.accept.operators(',') else None
                    self.expect.keywords('in')
                    loop = LoopBlock(val_name=val_name, key_name=key_name,
                                     loop_expr=self._p_expression(),
                                     parent=self.parent_node)
                    loop.statements.append(stmt)
                    stmt = loop
                pf_token = self.accept.keywords('if', 'unless', 'for')
        return stmt

    def _p_inner_stmt(self):
        if self.matches(KeyframesToken):
            return self._p_keyframes()
        elif self.matches.atrules('-moz-document'):
            return self._p_mozdocument()
        elif self.matches(CommentToken):
            return self._p_comment()
        elif self.matches(SelectorToken):
            return self._p_selector()
        elif self.matches(LiteralToken):
            return self._p_literal()
        elif self.matches.atrules('charset', 'namespace', 'import', 'require', 'extend',
                                  'media', 'scope', 'supports'):
            return getattr(self, '_p_' + self.peek().val)()
        elif self.matches(AtRuleToken):
            return self._p_atrule()
        elif self.matches(IdentifierToken):
            return self._p_identifier()
        elif self.matches.keywords('unless'):
            return self._p_unless()
        elif self.matches.keywords('for'):
            return self._p_for()
        elif self.matches.keywords('if'):
            return self._p_conditional()
        elif self.matches.keywords('return'):
            return self._p_return()
        elif self.matches(OpeningBraceToken):
            return self._p_property()
        elif self.states[-1] in selector_allowed_states:
            if self.matches.operators('~', '>', '<', ':', '&', '[', '.', '/') or \
                    self.matches(ColorToken):  # A selector's id might look like a color
                return self._p_selector()
            elif self.matches.operators('+'):
                if isinstance(self.lookahead(1), FunctionToken):
                    return self._p_functionCall()
                else:
                    return self._p_selector()
            elif self.matches.operators('*'):
                return self._p_property()  # TODO: why is that? (ewino@2015-01-31)
            elif self.matches(NumberToken) and self.looks_like_keyframe():
                return self._p_selector()  # TODO: why is that? (ewino@2015-01-31)
            elif self.matches.operators('-') and isinstance(self.lookahead(1),
                                                            OpeningBraceToken):
                return self._p_property()

        expr = self._p_expression()
        if expr is not None:
            return expr
        raise ParseError(self, 'Unexpected {peek}')

    def _p_expression(self):
        raise NotImplementedError()

    def _p_keyframes(self):
        raise NotImplementedError()

    def _p_mozdocument(self):
        raise NotImplementedError()

    def _p_id_name(self):
        """ Returns the name of an identifier """
        token = self.expect(IdentifierToken)
        self.skip_spaces()
        return token.val

    def _p_comment(self):
        raise NotImplementedError()

    def _p_selector(self):
        raise NotImplementedError()

    def _p_literal(self):
        raise NotImplementedError()

    def _p_charset(self):
        raise NotImplementedError()

    def _p_namespace(self):
        raise NotImplementedError()

    def _p_import(self):
        raise NotImplementedError()

    def _p_require(self):
        raise NotImplementedError()

    def _p_extend(self):
        raise NotImplementedError()

    def _p_media(self):
        raise NotImplementedError()

    def _p_scope(self):
        raise NotImplementedError()

    def _p_supports(self):
        raise NotImplementedError()

    def _p_atrule(self):
        raise NotImplementedError()

    def _p_identifier(self):
        raise NotImplementedError()

    def _p_unless(self):
        raise NotImplementedError()

    def _p_for(self):
        raise NotImplementedError()

    def _p_conditional(self):
        raise NotImplementedError()

    def _p_return(self):
        raise NotImplementedError()

    def _p_property(self):
        raise NotImplementedError()

    def _p_functionCall(self):
        raise NotImplementedError()

    def looks_like_keyframe(self):
        raise NotImplementedError()


postfix_allowed_nodes = (Expression,)  # tuple, not list (for isinstance)
selector_allowed_states = ('root', 'atblock', 'selector', 'conditional', 'function',
                           'atrule', 'for',)


class TokenMatcher(object):
    def __init__(self, parser, raise_if_missing=False, consumes=True):
        self.parser = parser
        self.raise_if_missing = raise_if_missing
        self.consumes = consumes

    def __call__(self, type_or_types, f=None):
        if self._is_match(self.parser.peek(), type_or_types, f):
            return self.parser.next() if self.consumes else self.parser.peek()

        if not self.raise_if_missing:
            return None

        msg = ''
        if type_or_types:
            if isinstance(type_or_types, tuple):
                msg += 'one of ' + ', '.join(t.__name__ for t in
                                             type_or_types)
            else:
                msg += type_or_types.__name__
        if f:
            msg += 'matching filter'
        raise ParseError(self, 'Expected {0}, but got {{peek}}'.format(msg))

    def operators(self, operator, *more_operators):
        keywords = [operator] + list(more_operators)
        return self(OperatorToken, lambda t: t.val in keywords)

    def keywords(self, keyword, *more_keywords):
        keywords = [keyword] + list(more_keywords)
        return self(KeywordToken, lambda t: t.val in keywords)

    def atrules(self, rule_name, *more_rule_names):
        rule_names = [rule_name] + list(more_rule_names)
        return self(AtRuleToken, lambda t: t.val in rule_names)

    @staticmethod
    def _is_match(token, type_or_types, match_func=None):
        if type_or_types and not isinstance(token, type_or_types):
            return False
        if match_func and not match_func(token):
            return False
        return True
"""
 Unordered notes from parser.js:

 - Cache parsing results (string buffer hash -> parsed whole root node)
 - Starting at Parser.parse()
  - state is a textual state (expression, assignment, etc)
 - id() expects an identifier (and ONLY an identifier, with a possible space)
 - ident() expects any kind of identifier, assignment, selector or anything
 that moves
 - we should have a contextmanager style state
"""