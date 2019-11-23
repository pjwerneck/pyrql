# -*- coding: utf-8 -*-

import datetime

import pytest

from pyrql import parse
from pyrql import unparse


CMP_OPS = ["eq", "lt", "le", "gt", "ge", "ne"]


class TestParser:
    @pytest.mark.parametrize(
        "expr, args",
        [
            ("a(1)", [1]),
            ("a(3.14)", [3.14]),
            ("a(true)", [True]),
            ("a(false)", [False]),
            ("a(null)", [None]),
        ],
    )
    def test_autoconverted_values(self, expr, args):
        pd = parse(expr)
        assert pd == {"name": "a", "args": args}

    @pytest.mark.parametrize("op", CMP_OPS)
    @pytest.mark.parametrize(
        "expr, rep",
        [
            ("%s(a,1)", ["a", 1]),
            ("%s(a,xyz)", ["a", "xyz"]),
            ("%s(a,string:1)", ["a", "1"]),
            ("%s(a,date:2017-01-01)", ["a", datetime.date(2017, 1, 1)]),
        ],
    )
    def test_op_calls(self, op, expr, rep):
        pd = parse(expr % op)

        assert pd == {"name": op, "args": rep}

    @pytest.mark.parametrize(
        "name, arg",
        [("lero", "lero"), ("foo.bar", "foo.bar"), ("(foo,bar)", ("foo", "bar"))],
    )
    def test_equality_operator(self, name, arg):
        p1 = parse("%s=0" % name)
        p2 = parse("eq(%s, 0)" % name)
        assert p1 == p2
        assert p1 == {"name": "eq", "args": [arg, 0]}

    def test_and_operator_pair(self):
        p1 = parse("eq(a,0)&eq(b,1)")
        p2 = parse("and(eq(a, 0), eq(b, 1))")

        p3 = {
            "name": "and",
            "args": [
                {"name": "eq", "args": ["a", 0]},
                {"name": "eq", "args": ["b", 1]},
            ],
        }

        assert p1 == p2
        assert p1 == p3

    def test_and_operator_triple(self):
        p1 = parse("eq(a,0)&eq(b,1)&eq(c,2)")
        p2 = parse("and(eq(a, 0), eq(b, 1), eq(c, 2))")

        p3 = {
            "name": "and",
            "args": [
                {"name": "eq", "args": ["a", 0]},
                {"name": "eq", "args": ["b", 1]},
                {"name": "eq", "args": ["c", 2]},
            ],
        }

        assert p1 == p2
        assert p1 == p3

    def test_or_operator(self):
        p1 = parse("(f(1)|f(2))")
        p2 = parse("or(f(1),f(2))")

        p3 = {
            "name": "or",
            "args": [{"name": "f", "args": [1]}, {"name": "f", "args": [2]}],
        }

        assert p1 == p2
        assert p1 == p3

    @pytest.mark.parametrize("func", ["in", "out", "contains", "excludes"])
    def test_member_functions(self, func):
        expr = "%s(name,(a,b))" % func
        rep = {"name": func, "args": ["name", ("a", "b")]}

        pd = parse(expr)
        assert pd == rep
        assert unparse(pd) == expr

    @pytest.mark.parametrize("func", ["and", "or"])
    @pytest.mark.parametrize(
        "args", [["a", "b"], ["a", "b", "c"], ["a", "b", "c", "d"]]
    )
    def test_bool_functions(self, func, args):
        expr = "%s(%s)" % (func, ",".join(args))
        rep = {"name": func, "args": args}

        pd = parse(expr)
        assert rep == pd
        assert unparse(pd) == expr

    @pytest.mark.parametrize(
        "expr, args",
        [
            ("sort(+lero)", [("+", "lero")]),
            ("sort(+foo,-bar)", [("+", "foo"), ("-", "bar")]),
            ("sort(+(foo,bar),-lero)", [("+", ("foo", "bar")), ("-", "lero")]),
        ],
    )
    def test_sort_function(self, expr, args):
        rep = {"name": "sort", "args": args}

        pd = parse(expr)
        assert pd == rep

    @pytest.mark.parametrize("func", ["select", "values"])
    def test_query_functions(self, func):
        expr = "%s(username,password,(address,city))" % func
        rep = {"name": func, "args": ["username", "password", ("address", "city")]}

        pd = parse(expr)
        assert pd == rep
        assert unparse(pd) == expr

    @pytest.mark.parametrize("func", ["sum", "mean", "max", "min", "count"])
    def test_aggregate_functions(self, func):
        expr = "%s((a,b,c))" % func
        rep = {"name": func, "args": [("a", "b", "c")]}

        pd = parse(expr)
        assert pd == rep
        assert unparse(pd) == expr

    @pytest.mark.parametrize("func", ["distinct", "first", "one"])
    def test_result_functions(self, func):
        expr = "%s()" % func
        rep = {"name": func, "args": []}

        pd = parse(expr)
        assert pd == rep
        assert unparse(pd) == expr

    def test_limit_function(self):
        expr = "limit(10,0)"
        rep = {"name": "limit", "args": [10, 0]}

        pd = parse(expr)
        assert rep == pd
        assert unparse(pd) == expr

    def test_recurse_function(self):
        expr = "recurse(lero)"
        rep = {"name": "recurse", "args": ["lero"]}
        pd = parse(expr)

        assert rep == pd
        assert unparse(pd) == expr

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

    def test_toplevel_and(self):
        pd = parse("eq(a, 1),eq(b, 2),eq(c, 3)")
        rep = {
            "name": "and",
            "args": [
                {"name": "eq", "args": ["a", 1]},
                {"name": "eq", "args": ["b", 2]},
                {"name": "eq", "args": ["c", 3]},
            ],
        }
        assert pd == rep

    def test_parenthesis(self):
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
