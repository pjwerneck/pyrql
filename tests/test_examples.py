# -*- coding: utf-8 -*-

from uuid import uuid4

import pytest

from pyrql import RQLSyntaxError
from pyrql import parse

CMP_OPS = ["eq", "lt", "le", "gt", "ge", "ne"]


class TestExamples:
    def test_rfc_abstract_example(self):
        expr = "category=dates&sort(+price)"
        rep = {
            "name": "and",
            "args": [
                {"name": "eq", "args": ["category", "dates"]},
                {"name": "sort", "args": [("+", "price")]},
            ],
        }

        pd = parse(expr)
        assert pd == rep

    def test_rfc_arrays_example(self):
        expr = "in(category,(toy,food))"
        rep = {"name": "in", "args": ["category", ("toy", "food")]}

        pd = parse(expr)
        assert pd == rep

    def test_rfc_nested_operators_example(self):
        expr = "or(eq(category,toy),eq(category,food))"
        rep = {
            "name": "or",
            "args": [
                {"name": "eq", "args": ["category", "toy"]},
                {"name": "eq", "args": ["category", "food"]},
            ],
        }

        pd = parse(expr)
        assert pd == rep

    @pytest.mark.parametrize(
        "exre",
        [
            ("sort(+foo)", [("+", "foo")]),
            ("sort(+price,-rating)", [("+", "price"), ("-", "rating")]),
        ],
    )
    def test_rfc_sort_examples(self, exre):
        expr, args = exre

        pd = parse(expr)
        assert pd == {"name": "sort", "args": args}

    def test_rfc_aggregate_example(self):
        expr = "aggregate(departmentId,sum(sales))"
        rep = {
            "name": "aggregate",
            "args": ["departmentId", {"name": "sum", "args": ["sales"]}],
        }

        pd = parse(expr)
        assert pd == rep

    def test_rfc_comparison_example(self):
        expr = "foo=3&(bar=text|bar=string)"
        rep = {
            "name": "and",
            "args": [
                {"name": "eq", "args": ["foo", 3]},
                {
                    "name": "or",
                    "args": [
                        {"name": "eq", "args": ["bar", "text"]},
                        {"name": "eq", "args": ["bar", "string"]},
                    ],
                },
            ],
        }

        pd = parse(expr)
        assert pd == rep

    def test_rfc_typed_value_example(self):
        expr = "foo=number:4"
        rep = {"name": "eq", "args": ["foo", 4]}

        pd = parse(expr)
        assert pd == rep

    def test_syntax_error(self):
        expr = "lero===lero"
        with pytest.raises(RQLSyntaxError):
            parse(expr)


class TestJSExamples:
    # Testing the examples given in the JS library

    @pytest.mark.parametrize("expr", ["lt(price,10)", "price=lt=10"])
    def test_fiql_compatibility(self, expr):
        rep = {"name": "lt", "args": ["price", 10]}

        assert parse(expr) == rep

    @pytest.mark.parametrize(
        "expr",
        ["foo=3&price=lt=10", "eq(foo,3)&lt(price,10)", "and(eq(foo,3),lt(price,10))"],
    )
    def test_and_operator(self, expr):
        rep = {
            "name": "and",
            "args": [
                {"name": "eq", "args": ["foo", 3]},
                {"name": "lt", "args": ["price", 10]},
            ],
        }

        assert parse(expr) == rep

    @pytest.mark.parametrize(
        "expr",
        ["(foo=3|foo=bar)&price=lt=10", "and(or(eq(foo,3),eq(foo,bar)),lt(price,10))"],
    )
    def test_or_operator(self, expr):
        rep = {
            "name": "and",
            "args": [
                {
                    "name": "or",
                    "args": [
                        {"name": "eq", "args": ["foo", 3]},
                        {"name": "eq", "args": ["foo", "bar"]},
                    ],
                },
                {"name": "lt", "args": ["price", 10]},
            ],
        }

        assert parse(expr) == rep

    @pytest.mark.parametrize("expr", ["eq((foo,bar),3)", "(foo,bar)=3"])
    def test_name_array(self, expr):
        rep = {"name": "eq", "args": [("foo", "bar"), 3]}

        assert parse(expr) == rep

    @pytest.mark.parametrize("expr", ["sort(+price,-rating)"])
    def test_multiple_sort(self, expr):
        rep = {"name": "sort", "args": [("+", "price"), ("-", "rating")]}
        assert parse(expr) == rep


class TestUUID:
    @pytest.mark.parametrize("uuid", [uuid4().hex for x in range(100)])
    def test_uuid_query(self, uuid):
        expr = "uuid={}".format(uuid)
        rep = {"name": "eq", "args": ["uuid", uuid]}

        assert parse(expr) == rep
