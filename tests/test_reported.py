# -*- coding: utf-8 -*-

import pytest

from pyrql import RQLSyntaxError
from pyrql import parse
from pyrql import unparse

CMP_OPS = ["eq", "lt", "le", "gt", "ge", "ne"]


class TestReportedErrors:
    def test_like_with_string_parameter(self):
        expr = "like(name,*new jack city*)"
        rep = {"name": "like", "args": ["name", "*new jack city*"]}

        pd = parse(expr)
        assert pd == rep

    def test_like_with_string_encoded_parameter(self):
        expr = "like(name,*new%20jack%20city*)"
        rep = {"name": "like", "args": ["name", "*new jack city*"]}

        pd = parse(expr)
        assert pd == rep

    def test_string_starting_with_number(self):
        expr = "uuid=27f1db1c029e4a428961b85433de25fd"
        rep = {"name": "eq", "args": ["uuid", "27f1db1c029e4a428961b85433de25fd"]}

        pd = parse(expr)
        assert pd == rep

    def test_unparser_error_1(self):
        expr = r"eq(accountId,(123456789))&eq(yyyy,(2020))&eq(mm,(10))"
        rep = {
            "name": "and",
            "args": [
                {"name": "eq", "args": ["accountId", (123456789,)]},
                {"name": "eq", "args": ["yyyy", (2020,)]},
                {"name": "eq", "args": ["mm", (10,)]},
            ],
        }

        pd = parse(expr)
        upd = parse(unparse(pd))

        assert pd == rep
        assert upd == pd

    def test_unparser_error_4(self):
        expr = r"and(eq(accountId,(123456789)), eq(yyyy,(2020)), eq(mm,(10)))"
        rep = {
            "name": "and",
            "args": [
                {"name": "eq", "args": ["accountId", (123456789,)]},
                {"name": "eq", "args": ["yyyy", (2020,)]},
                {"name": "eq", "args": ["mm", (10,)]},
            ],
        }

        pd = parse(expr)
        upd = parse(unparse(pd))

        assert pd == rep
        assert upd == pd

    def test_unbalanced_parenthesis_11(self):
        parsed = parse(r"in(foo,(foo,bar))&sort(+foo)&eq(userid,user)")
        assert parsed == {'name': 'and', 'args': [
            {'name': 'in', 'args': ['foo', ('foo', 'bar')]},
            {'name': 'sort', 'args': [('+', 'foo')]},
            {'name': 'eq', 'args': ['userid', 'user']}
        ]}

        with pytest.raises(RQLSyntaxError) as exc:
            parse(r"in(foo,(foo,bar))&sort(+foo))&eq(userid,user)")

        assert exc.value.args[2] == "Expected end of text"
