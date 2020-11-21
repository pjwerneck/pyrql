# -*- coding: utf-8 -*-

from datetime import date
from datetime import datetime
from datetime import timezone
from decimal import Decimal
from uuid import UUID

import pytest

from pyrql import parse
from pyrql import unparse

IMPLICIT_TYPES = [
    ("123abc", "123abc"),
    (123, "123"),
    (123.456, "123.456"),
    (True, "true"),
    (None, "null"),
]

EXPLICIT_TYPES = [
    (Decimal("0.1"), "decimal:0.1"),
    (
        UUID("12345678-1234-1234-1234-123456789abc"),
        "uuid:12345678123412341234123456789abc",
    ),
    (date(2020, 11, 21), "date:2020-11-21"),
    (datetime(2020, 11, 21, 10, 0, 0), "datetime:2020-11-21T10:00:00"),
    (
        datetime(2020, 11, 21, 10, 0, 0, tzinfo=timezone.utc),
        "datetime:2020-11-21T10:00:00+00:00",
    ),
]


@pytest.mark.parametrize("func", ["eq", "lt", "le", "gt", "ge", "ne"])
def test_cmp_functions(func):
    parsed = {"name": func, "args": ["a", 1]}
    assert unparse(parsed) == "%s(a,1)" % func

    parsed = {"name": func, "args": [("a", "b", "c"), 1]}
    assert unparse(parsed) == "%s((a,b,c),1)" % func


def test_array_arg():
    parsed = {"name": "eq", "args": ["a", (1,)]}
    assert unparse(parsed) == "eq(a,(1))"

    parsed = {"name": "eq", "args": [("a", "b", "c"), (1, 2, 3)]}
    assert unparse(parsed) == "eq((a,b,c),(1,2,3))"


@pytest.mark.parametrize("in_,out", IMPLICIT_TYPES)
def test_implicit_types(in_, out):
    parsed = {"name": "eq", "args": ["a", in_]}
    assert unparse(parsed) == "eq(a,%s)" % out


@pytest.mark.parametrize("in_,out", IMPLICIT_TYPES)
def test_implicit_types_symmetry(in_, out):
    parsed = {"name": "eq", "args": ["a", in_]}
    upd = unparse(parsed)
    pd = parse(upd)

    assert pd == parsed
    assert upd == "eq(a,%s)" % out


@pytest.mark.parametrize("in_,out", EXPLICIT_TYPES)
def test_explicit_types(in_, out):
    parsed = {"name": "eq", "args": ["a", in_]}
    assert unparse(parsed) == "eq(a,%s)" % out


@pytest.mark.parametrize("in_,out", EXPLICIT_TYPES)
def test_explicit_types_symmetry(in_, out):
    parsed = {"name": "eq", "args": ["a", in_]}
    upd = unparse(parsed)
    pd = parse(upd)

    assert pd == parsed
    assert upd == "eq(a,%s)" % out
