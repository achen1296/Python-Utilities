
import itertools
from abc import ABC, abstractmethod
from typing import Iterable, Literal


class BooleanExpressionException(Exception):
    pass


class BooleanExpression(ABC):
    @abstractmethod
    def match(self, vars: Iterable[str]) -> bool:
        """ vars is an iterable of variables that are true, the rest are false implicitly """
        return False

    @staticmethod
    def tokenize(expression: str,

                 group_pairs: dict[str, str] = {"[": "]"},

                 not_chars: str = "!",

                 and_chars: str = "&",
                 or_chars: str = "|",
                 ):

        all_operators = list(itertools.chain(
            group_pairs.keys(), group_pairs.values(), not_chars, and_chars, or_chars))

        tokens: list[str] = []
        t = ""
        for i in range(0, len(expression)):
            c = expression[i]
            if c in all_operators:
                tokens.append(t)
                t = ""
                tokens.append(c)
            elif c.isspace():
                tokens.append(t)
                t = ""
            else:
                t += c
        tokens.append(t)
        # print(tokens)
        return [t for t in tokens if t != ""]

    @staticmethod
    def compile(expression: str | list[str],

                group_pairs: dict[str, str] = {"[": "]"},

                not_chars: str = "!",

                and_chars: str = "&",
                or_chars: str = "|",

                implicit_binary: Literal['or'] | Literal['and'] | None = "or",
                ):
        """ Group chars should be a dictionary of start chars mapping to end chars. All others should be strings (treated as lists of single chars).

        Implicit binary operator is used when variables are separated only by whitespace and grouping characters or not operators. If None, then explicit binary operators are required.

        Precedence highest to lowest:
        - not
        - implicit binary
        - explicit and/or (left to right)

        This means that either and or or can be made higher priority all the time by only ever using one of them explicitly.
        """

        all_operators = list(itertools.chain(
            group_pairs.keys(), group_pairs.values(), not_chars, and_chars, or_chars))
        binary_operators = and_chars + or_chars

        implicit_operator_cls = BooleanExpressionOr if implicit_binary == "or" else BooleanExpressionAnd

        if isinstance(expression, str):
            tokens = BooleanExpression.tokenize(
                expression, group_pairs, not_chars, and_chars, or_chars)
        else:
            tokens = expression

        # get an arbitrary grouping character
        for end_char in group_pairs.values():
            break
        else:
            raise BooleanExpressionException("No grouping pairs specified")

        # logically surround entire expression with a group to simplify the code, which may now assume it is always inside a group
        # not actually necessary to prepend a starter
        tokens += [end_char]

        def _compile(i: int, group_end: str) -> tuple[BooleanExpression, int]:
            if tokens[i] in binary_operators:
                raise BooleanExpressionException(
                    "Binary operator without left operand")
            left, i = _consume_implicit(i, group_end)
            while i < len(tokens):
                t = tokens[i]
                if t == group_end:
                    return left, i + 1
                if t in or_chars:
                    right, i = _consume_implicit(i+1, group_end)
                    operator = BooleanExpressionOr
                elif t in and_chars:
                    right, i = _consume_implicit(i+1, group_end)
                    operator = BooleanExpressionAnd
                else:
                    raise BooleanExpressionException(
                        "Default operator is None but was required")
                left = operator.create(left, right)
            raise BooleanExpressionException(
                "Mismatched grouping characters")

        def _consume_implicit(i: int, group_end: str):
            if implicit_binary is None:
                return _compile_unary(i)
            else:
                # process as many implicit operators as possible first, resulting in its promised higher precedence
                vars = []
                while i < len(tokens):
                    t = tokens[i]
                    if t == group_end or t in binary_operators:
                        return implicit_operator_cls.create(*vars), i
                    else:
                        e, i = _compile_unary(i)
                        vars.append(e)
                assert False

        def _compile_unary(i: int) -> tuple[BooleanExpression, int]:
            t = tokens[i]
            if t in not_chars:
                e, i = _compile_unary(i + 1)
                return BooleanExpressionNot(e), i
            elif t in group_pairs:
                return _compile(i+1, group_pairs[t])
            else:
                assert t not in all_operators, t
                return BooleanVar(t), i+1

        e, i = _compile(0, end_char)
        if i < len(tokens):
            raise BooleanExpressionException(
                "Mismatched grouping characters")
        return e


class BooleanVar(BooleanExpression):
    def __init__(self, var: str):
        self.var = var

    def match(self, vars: Iterable[str]):
        return self.var in vars

    def __repr__(self):
        return "BooleanVar(\""+self.var+"\")"

    def __eq__(self, other):
        return isinstance(other, BooleanVar) and self.var == other.var


class BooleanExpressionNot(BooleanExpression):
    def __init__(self, sub_expression: BooleanExpression):
        self.sub_expression = sub_expression

    def match(self, vars: Iterable[str]):
        return not self.sub_expression.match(vars)

    def __repr__(self):
        return "BooleanExpressionNot("+repr(self.sub_expression)+")"

    def __eq__(self, other):
        return isinstance(other, BooleanExpressionNot) and self.sub_expression == other.sub_expression


class BooleanExpressionMulti(BooleanExpression):
    def __init__(self, *sub_expressions: BooleanExpression):
        self.sub_expressions = sub_expressions

    @classmethod
    def create(cls, *sub_expressions: BooleanExpression):
        # For and/or, it would be useless to wrap a single expression.
        # On the other hand, wrapping an empty list actually does something different -- for and, it will be always false, and for or, always true.
        if len(sub_expressions) == 1:
            return sub_expressions[0]
        if all(isinstance(sub, cls) for sub in sub_expressions):
            # flatten expressions of the same type, usually when chained
            return cls(*itertools.chain(*(sub.sub_expressions for sub in sub_expressions)))
        return cls(*sub_expressions)


class BooleanExpressionAnd(BooleanExpressionMulti):
    def match(self, vars: Iterable[str]):
        return all(sub.match(vars) for sub in self.sub_expressions)

    def __repr__(self):
        return "BooleanExpressionAnd("+", ".join((repr(sub) for sub in self.sub_expressions))+")"

    def __eq__(self, other):
        # not order independent
        try:
            return isinstance(other, BooleanExpressionAnd) and all(sub_self == sub_other for sub_self, sub_other in zip(self.sub_expressions, other.sub_expressions, strict=True))
        except ValueError:
            # from zip
            return False


class BooleanExpressionOr(BooleanExpressionMulti):

    def match(self, vars: Iterable[str]):
        return any(sub.match(vars) for sub in self.sub_expressions)

    def __repr__(self):
        return "BooleanExpressionOr("+", ".join((repr(sub) for sub in self.sub_expressions))+")"

    def __eq__(self, other):
        # not order independent
        try:
            return isinstance(other, BooleanExpressionOr) and all(sub_self == sub_other for sub_self, sub_other in zip(self.sub_expressions, other.sub_expressions, strict=True))
        except ValueError:
            # from zip
            return False


if __name__ == "__main__":
    result = BooleanExpression.compile("asdf")
    assert result == BooleanVar("asdf"), result
    result = BooleanExpression.compile("a b c d e")
    assert result == BooleanExpressionOr(BooleanVar(
        "a"), BooleanVar("b"), BooleanVar("c"), BooleanVar("d"), BooleanVar("e")), result
    result = BooleanExpression.compile("a b c&d e")
    assert result == BooleanExpressionAnd(
        BooleanExpressionOr(BooleanVar(
            "a"), BooleanVar("b"), BooleanVar("c")),
        BooleanExpressionOr(BooleanVar("d"),
                            BooleanVar("e"))
    ), result
    result = BooleanExpression.compile("a !b [!c&d] e")
    assert result == BooleanExpressionOr(
        BooleanVar("a"),
        BooleanExpressionNot(BooleanVar("b")),
        BooleanExpressionAnd(
            BooleanExpressionNot(BooleanVar("c")),
            BooleanVar("d")
        ),
        BooleanVar("e")
    ), result
    result = BooleanExpression.compile("a [!b ![!c&d] e]")
    assert result == BooleanExpressionOr(
        BooleanVar("a"),
        BooleanExpressionOr(
            BooleanExpressionNot(BooleanVar("b")),
            BooleanExpressionNot(
                BooleanExpressionAnd(
                    BooleanExpressionNot(BooleanVar("c")),
                    BooleanVar("d")
                )
            ),
            BooleanVar("e")
        )
    ), result
    assert result.match(["a"])
    assert result.match(["e"])
    assert not result.match(["b", "d"])
