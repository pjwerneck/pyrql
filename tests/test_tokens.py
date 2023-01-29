# -*- coding: utf-8 -*-

import datetime

import pytest

from pyrql import parser as pm

CMP_OPS = ["eq", "lt", "le", "gt", "ge", "ne"]


class TestTokens:
    @pytest.mark.parametrize("expr, rep", [("%20", " ")])
    def test_PCT_ENCODED(self, expr, rep):
        pd = pm.PCT_ENCODED.parseString(expr)
        assert pd[0] == rep

    @pytest.mark.parametrize("expr, rep", [("%20", " "), ("a", "a"), ("1", "1")])
    def test_NCHAR(self, expr, rep):
        pd = pm.NCHAR.parseString(expr)
        assert pd[0] == rep

    @pytest.mark.parametrize("expr, rep", [("ab", "ab"), ("abc", "abc")])
    def test_NAME(self, expr, rep):
        pd = pm.NAME.parseString(expr)
        assert pd[0] == rep

    @pytest.mark.parametrize(
        "expr, rep",
        [
            ("123", 123),
            ("abc", "abc"),
            ("3.14", 3.14),
            ("true", True),
            ("false", False),
            ("null", None),
        ],
    )
    def test_VALUE(self, expr, rep):
        pd = pm.VALUE.parseString(expr)
        assert pd[0] == rep

    @pytest.mark.parametrize(
        "expr, rep",
        [
            ("string:3", "3"),
            ("number:3", 3),
            ("date:2017-01-01", datetime.date(2017, 1, 1)),
            ("datetime:2017-01-01T22:04:23", datetime.datetime(2017, 1, 1, 22, 4, 23)),
            ("boolean:true", True),
            ("boolean:false", False),
            ("epoch:1346201641.0", datetime.datetime(2012, 8, 29, 0, 54, 1)),
        ],
    )
    def test_TYPED_VALUE(self, expr, rep):
        pd = pm.TYPED_VALUE.parseString(expr)
        assert pd[0] == rep

    @pytest.mark.parametrize(
        "expr, rep",
        [
            (
                "(123,string:123,date:2017-01-01)",
                (123, "123", datetime.date(2017, 1, 1)),
            ),
            ("(1,(2, 3, (4, 5)))", (1, (2, 3, (4, 5)))),
        ],
    )
    def test_ARRAY(self, expr, rep):
        pd = pm.ARRAY.parseString(expr)
        assert pd[0] == rep

    @pytest.mark.parametrize(
        "pair",
        [
            ("a()", []),
            ("a(1)", [1]),
            ("a(x,(y,z))", ["x", ("y", "z")]),
            ("a(number:1,string:2)", [1, "2"]),
            ("a(date:2017-01-01)", [datetime.date(2017, 1, 1)]),
        ],
    )
    def test_CALL_OPERATOR(self, pair):
        expr, args = pair

        pd = pm.CALL_OPERATOR.parseString(expr)
        assert pd[0] == {"name": "a", "args": args}

    def test_nested_CALL_OPERATOR(self):
        expr = "a(1,b(2),3)"

        pd = pm.CALL_OPERATOR.parseString(expr)
        assert pd[0] == {"name": "a", "args": [1, {"name": "b", "args": [2]}, 3]}

    @pytest.mark.parametrize(
        "pair",
        [
            ("a=1", ["a", 1]),
            ("a=xyz", ["a", "xyz"]),
            ("a=string:1", ["a", "1"]),
            ("a=date:2017-01-01", ["a", datetime.date(2017, 1, 1)]),
        ],
    )
    def test_call_eq_expressions(self, pair):
        expr, args = pair

        pd = pm.COMPARISON.parseString(expr)
        assert pd[0] == {"name": "eq", "args": args}

    @pytest.mark.parametrize("op", CMP_OPS)
    @pytest.mark.parametrize(
        "pair",
        [
            ("a=%s=1", ["a", 1]),
            ("a=%s=xyz", ["a", "xyz"]),
            ("a=%s=string:1", ["a", "1"]),
            ("a=%s=date:2017-01-01", ["a", datetime.date(2017, 1, 1)]),
        ],
    )
    def test_call_fiql_expression(self, op, pair):
        expr, args = pair

        pd = pm.COMPARISON.parseString(expr % op)
        assert pd[0] == {"name": op, "args": args}

    @pytest.mark.parametrize(
        "pair",
        [
            ("a()", []),
            ("a(1)", [1]),
            ("a(x,(y,z))", ["x", ("y", "z")]),
            ("a(number:1,string:2)", [1, "2"]),
            ("a(date:2017-01-01)", [datetime.date(2017, 1, 1)]),
        ],
    )
    def test_OPERATOR_call(self, pair):
        expr, args = pair

        pd = pm.OPERATOR.parseString(expr)
        assert pd[0] == {"name": "a", "args": args}

    @pytest.mark.parametrize(
        "pair",
        [
            ("a=1", ["a", 1]),
            ("a=xyz", ["a", "xyz"]),
            ("a=string:1", ["a", "1"]),
            ("a=date:2017-01-01", ["a", datetime.date(2017, 1, 1)]),
        ],
    )
    def test_OPERATOR_eq_expressions(self, pair):
        expr, args = pair

        pd = pm.OPERATOR.parseString(expr)
        assert pd[0] == {"name": "eq", "args": args}

    @pytest.mark.parametrize("op", CMP_OPS)
    @pytest.mark.parametrize(
        "expr, args",
        [
            ("a=%s=1", ["a", 1]),
            ("a=%s=xyz", ["a", "xyz"]),
            ("a=%s=string:1", ["a", "1"]),
            ("a=%s=date:2017-01-01", ["a", datetime.date(2017, 1, 1)]),
        ],
    )
    def test_OPERATOR_fiql_expression(self, op, expr, args):
        pd = pm.OPERATOR.parseString(expr % op)
        assert pd[0] == {"name": op, "args": args}

    def test_AND(self):
        expr = "a(1)&b(2)"

        pd = pm.AND.parseString(expr)
        assert pd[0] == {
            "name": "and",
            "args": [{"name": "a", "args": [1]}, {"name": "b", "args": [2]}],
        }

    def test_OR(self):
        expr = "a(1)|b(2)"

        pd = pm.OR.parseString(expr)
        assert pd[0] == {
            "name": "or",
            "args": [{"name": "a", "args": [1]}, {"name": "b", "args": [2]}],
        }
