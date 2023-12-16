# -*- coding: utf-8 -*-

import datetime

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pyrql import parser as pm

from . import helpers as hp


class TestTokens:
    @pytest.mark.parametrize("expr, rep", [("%20", " ")])
    def test_PCT_ENCODED(self, expr, rep):
        pd = pm.PCT_ENCODED.parseString(expr)
        assert pd[0] == rep

    # there are probably more categories that should be included
    @given(st.characters(whitelist_categories=("Ll", "Lu", "Nd")))
    def test_NCHAR(self, char):
        pd = pm.NCHAR.parseString(char)
        assert pd[0] == char

    @given(hp.rql_names)
    def test_NAME(self, name):
        pd = pm.NAME.parseString(name)
        assert pd[0] == name

    @given(hp.py_numbers)
    def test_TYPED_NUMBER(self, value):
        pd = pm.TYPED_NUMBER.parseString(f"number:{value}")
        assert pd[0] == value

    @given(hp.py_dates)
    def test_TYPED_DATE(self, value):
        pd = pm.TYPED_DATE.parseString(f"date:{value.isoformat()}")
        assert pd[0] == value

    @given(hp.py_naive_datetimes)
    def test_naive_TYPED_DATETIME(self, value):
        pd = pm.TYPED_DATETIME.parseString(f"datetime:{value.isoformat()}")
        assert pd[0] == value

    # reject tz-aware datetimes that have a timezone offset with more than 5
    # digits (not ISO 8601 compliant)
    @given(hp.py_datetimes)
    def test_TYPED_DATETIME(self, value):
        pd = pm.TYPED_DATETIME.parseString(f"datetime:{value.isoformat()}")
        assert pd[0] == value

    @given(hp.py_booleans)
    def test_TYPED_BOOL(self, value):
        pd = pm.TYPED_BOOL.parseString(f"boolean:{str(value).lower()}")
        assert pd[0] == value

    @given(hp.py_datetimes)
    def test_TYPED_EPOCH(self, v):
        # remove microseconds that are not supported by epoch
        v_utc = v.replace(microsecond=0).astimezone(datetime.timezone.utc)
        # convert to timestamp
        ts = v_utc.timestamp()

        pd = pm.TYPED_EPOCH.parseString(f"epoch:{ts}")
        assert pd[0] == v_utc

    @given(hp.py_uuids)
    def test_TYPED_UUID(self, value):
        pd = pm.TYPED_UUID.parseString("uuid:%s" % value.hex)
        assert pd[0] == value

    @given(hp.py_decimals)
    def test_TYPED_DECIMAL(self, value):
        pd = pm.TYPED_DECIMAL.parseString("decimal:%s" % value)
        assert pd[0] == value

    @given(hp.rql_typed_strings)
    def test_TYPED_STRING(self, value):
        pd = pm.TYPED_STRING.parseString(value)
        assert pd[0] == value.split(":", 1)[1]

    @given(hp.value_pairs)
    def test_VALUE(self, pair):
        pyv, rqlv = pair
        pd = pm.VALUE.parseString(rqlv)
        assert pd[0] == pyv

    @given(hp.array_pairs)
    def test_ARRAY(self, pair):
        pyv, rqlv = pair
        pd = pm.ARRAY.parseString(rqlv)
        assert pd[0] == pyv

    @given(hp.rql_names)
    def test_OPERATOR_no_args(self, name):
        expr = f"{name}()"
        pd = pm.OPERATOR.parseString(expr)
        assert pd[0] == {"name": name, "args": []}

    @given(hp.rql_names, hp.value_pairs)
    def test_OPERATOR_single_arg(self, name, pair):
        pyv, rqlv = pair
        expr = f"{name}({rqlv})"
        pd = pm.OPERATOR.parseString(expr)
        assert pd[0] == {"name": name, "args": [pyv]}

    @given(hp.rql_names, hp.array_pairs)
    def test_OPERATOR_multiple_args(self, name, pair):
        pyv, rqlv = pair
        expr = f"{name}{rqlv}"
        pd = pm.OPERATOR.parseString(expr)
        assert pd[0] == {"name": name, "args": list(pyv)}

    @given(hp.rql_names, hp.value_pairs, hp.rql_names, hp.value_pairs)
    def test_nested_OPERATOR(self, name1, pair1, name2, pair2):
        pyv1, rqlv1 = pair1
        pyv2, rqlv2 = pair2

        expr = f"{name1}({rqlv1},{name2}({rqlv2}))"

        pd = pm.OPERATOR.parseString(expr)
        assert pd[0] == {"name": name1, "args": [pyv1, {"name": name2, "args": [pyv2]}]}

    @given(hp.rql_names, hp.value_pairs)
    def test_OPERATOR_with_literal_comparison(self, name, pair):
        pyv, rqlv = pair
        pd = pm.OPERATOR.parseString(f"{name}={rqlv}")
        assert pd[0] == {"name": "eq", "args": [name, pyv]}

    @given(hp.rql_names, hp.value_pairs, hp.rql_cmp_ops)
    def test_OPERATOR_with_fiql_comparison(self, name, pair, op):
        pyv, rqlv = pair
        pd = pm.OPERATOR.parseString(f"{name}={op}={rqlv}")
        assert pd[0] == {"name": op, "args": [name, pyv]}

    @given(hp.rql_names, hp.value_pairs, hp.rql_names, hp.value_pairs)
    def test_AND_expression(self, name1, pair1, name2, pair2):
        pyv1, rqlv1 = pair1
        pyv2, rqlv2 = pair2
        expr = f"{name1}({rqlv1})&{name2}({rqlv2})"

        pd = pm.AND.parseString(expr)
        assert pd[0] == {
            "name": "and",
            "args": [{"name": name1, "args": [pyv1]}, {"name": name2, "args": [pyv2]}],
        }

    @given(hp.rql_names, hp.value_pairs, hp.rql_names, hp.value_pairs)
    def test_OR_expression(self, name1, pair1, name2, pair2):
        pyv1, rqlv1 = pair1
        pyv2, rqlv2 = pair2
        expr = f"{name1}({rqlv1})|{name2}({rqlv2})"

        pd = pm.OR.parseString(expr)
        assert pd[0] == {
            "name": "or",
            "args": [{"name": name1, "args": [pyv1]}, {"name": name2, "args": [pyv2]}],
        }
