from typing import NamedTuple

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pyrql import RQLSyntaxError
from pyrql import parse
from pyrql import unparse

from . import helpers as hp


class BinaryNode(NamedTuple):
    op: str
    attr: str
    pair: tuple

    def __str__(self):
        return f"{self.op}({self.attr[1]},{self.pair[1]})"

    @property
    def expected(self):
        return {"name": self.op, "args": [self.attr[0], self.pair[0]]}


class UnaryNode(NamedTuple):
    op: str
    attr: str

    def __str__(self):
        return f"{self.op}({self.attr[1]})"

    @property
    def expected(self):
        return {"name": self.op, "args": [self.attr[0]]}


def cmp_ops():
    return st.builds(BinaryNode, hp.rql_cmp_ops, hp.attribute_pairs, hp.value_pairs)


def member_ops():
    return st.builds(BinaryNode, hp.rql_member_ops, hp.attribute_pairs, hp.array_pairs)


def sort_ops():
    return st.builds(UnaryNode, st.just("sort"), hp.sort_attribute_pairs)


def query_ops(attribute_strategy):
    return st.builds(UnaryNode, attribute_strategy, hp.attribute_pairs)


def verify(expr, expected, rev=True):
    # verify both parser and unparser (reverse)
    parsed = parse(expr)
    assert parsed == expected
    if rev:
        assert unparse(parsed) == expr


class TestParser:
    @given(hp.rql_cmp_ops, hp.attribute_pairs, hp.value_pairs)
    def test_simple_comparison_expression(self, op, name, pair):
        pyv, rqlv = pair
        pyattr, rqlattr = name
        expr = f"{op}({rqlattr},{rqlv})"
        verify(expr, {"name": op, "args": [pyattr, pyv]})

    @given(cmp_ops())
    def test_binary_operator_with_single_attribute(self, v):
        verify(str(v), v.expected)

    @given(cmp_ops(), cmp_ops())
    def test_top_level_and_operator(self, a, b):
        verify(f"{a}&{b}", {"name": "and", "args": [a.expected, b.expected]}, rev=False)

    @given(cmp_ops(), cmp_ops(), cmp_ops())
    def test_top_level_and_operator_multiple(self, a, b, c):
        verify(
            f"{a}&{b}&{c}",
            {"name": "and", "args": [a.expected, b.expected, c.expected]},
            rev=False,
        )

    @given(cmp_ops(), cmp_ops())
    def test_literal_and_operator(self, a, b):
        verify(f"and({a},{b})", {"name": "and", "args": [a.expected, b.expected]})

    @given(cmp_ops(), cmp_ops(), cmp_ops())
    def test_literal_and_operator_multiple(self, a, b, c):
        verify(f"and({a},{b},{c})", {"name": "and", "args": [a.expected, b.expected, c.expected]})

    @given(cmp_ops(), cmp_ops())
    def test_literal_or_operator(self, a, b):
        verify(f"or({a},{b})", {"name": "or", "args": [a.expected, b.expected]})

    @given(cmp_ops(), cmp_ops(), cmp_ops(), cmp_ops())
    def test_nested_literal_and_or(self, a, b, c, d):
        verify(
            f"and({a},or({b},{c}),{d})",
            {
                "name": "and",
                "args": [a.expected, {"name": "or", "args": [b.expected, c.expected]}, d.expected],
            },
        )

    @given(member_ops())
    def test_membership_operators(self, v):
        verify(str(v), v.expected)

    @given(sort_ops())
    def test_sort(self, v):
        verify(str(v), v.expected, rev=False)

    @given(query_ops(st.one_of(st.just("select"), st.just("values"), st.just("recurse"))))
    def test_transform_ops(self, v):
        verify(str(v), v.expected)

    @given(query_ops(st.one_of(st.just("sum"), st.just("mean"), st.just("max"), st.just("min"))))
    def test_aggregate_ops(self, v):
        verify(str(v), v.expected)

    @pytest.mark.parametrize("func", ["distinct", "first", "one"])
    def test_result_functions(self, func):
        expr = f"{func}()"
        rep = {"name": func, "args": []}
        verify(expr, rep)

    @pytest.mark.parametrize(
        "expr",
        ["foo=3&price=lt=10", "eq(foo,3)&lt(price,10)", "and(eq(foo,3),lt(price,10))"],
    )
    def test_equivalent_expressions(self, expr):
        pd = parse(expr)
        rep = {
            "name": "and",
            "args": [
                {"name": "eq", "args": ["foo", 3]},
                {"name": "lt", "args": ["price", 10]},
            ],
        }
        assert pd == rep

    def test_parenthesis_grouping(self):
        pd = parse("(state=Florida|state=Alabama)&gender=female")
        rep = {
            "name": "and",
            "args": [
                {
                    "name": "or",
                    "args": [
                        {"name": "eq", "args": ["state", "Florida"]},
                        {"name": "eq", "args": ["state", "Alabama"]},
                    ],
                },
                {"name": "eq", "args": ["gender", "female"]},
            ],
        }

        assert pd == rep

    def test_unbalanced_opening_parenthesis(self):
        with pytest.raises(RQLSyntaxError) as exc:
            parse("((state=Florida|state=Alabama)&gender=female")
        assert exc.value.args[2] == "Expected ')'"

    @pytest.mark.parametrize(
        "expr,error",
        [
            ("(state=Florida|state=Alabama))&gender=female", "Expected end of text"),
            ("()state=Florida|state=Alabama)&gender=female", "Expected '('"),
            (")(state=Florida|state=Alabama)&gender=female", "Expected '('"),
        ],
    )
    def test_unbalanced_closing_parenthesis(self, expr, error):
        with pytest.raises(RQLSyntaxError) as exc:
            parse(expr)

        assert exc.value.args[2] == error

    def test_value_with_reserved_character(self):
        pd = parse("email=user@example.com")

        rep = {"name": "eq", "args": ["email", "user@example.com"]}

        assert pd == rep
