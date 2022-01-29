# -*- coding: utf-8 -*-

import datetime
import json
import operator
import os
from decimal import Decimal

import pytest

from pyrql import Query
from pyrql.query import And
from pyrql.query import Filter
from pyrql.query import Or


@pytest.fixture(scope="session")
def data():
    with open(os.path.join(os.path.dirname(__file__), "testdata.json")) as f:
        data_ = json.load(f)

    for row in data_:
        # add decimal field for aggregation testing
        row["balance"] = Decimal(row["balance"][1:].replace(",", ""))
        # add datetime fields
        row["registered"] = datetime.datetime.strptime(
            row["registered"][::-1].replace(":", "", 1)[::-1], "%Y-%m-%dT%H:%M:%S %z"
        )
        row["birthdate"] = datetime.datetime.strptime(
            row["birthdate"], "%Y-%m-%d"
        ).date()

        # convert coordinates to a nested dict, for nested attribute operations
        row['position'] = {"latitude": row.pop("latitude"), "longitude": row.pop("longitude")}

    return data_


class TestBase:
    @pytest.mark.parametrize(
        "op,tv,fv",
        [
            ("eq", 10, 9),
            ("ne", 9, 10),
            ("lt", 9, 11),
            ("le", 10, 11),
            ("gt", 11, 10),
            ("ge", 10, 9),
        ],
    )
    def test_filter_operators(self, op, tv, fv):
        f = Filter(op, "id", 10)

        assert f({"id": tv})
        assert not f({"id": fv})

    def test_and_operator(self):
        a = Filter("eq", "a", 10)
        b = Filter("eq", "b", "xyz")

        f = And(a, b)

        assert f({"a": 10, "b": "xyz"})
        assert not f({"a": 11, "b": "xyz"})
        assert not f({"a": 10, "b": None})

    def test_or_operator(self):
        a = Filter("eq", "a", 10)
        b = Filter("eq", "b", "xyz")

        f = Or(a, b)

        assert f({"a": 10, "b": "x"})
        assert f({"a": 0, "b": "xyz"})

        assert not f({"a": 0, "b": "x"})

    def test_nested_operators(self):
        a = Filter("eq", "a", 10)
        b = Filter("eq", "b", "xyz")
        c = Filter("eq", "c", 10)

        f = Or(And(a, b), c)

        assert f({"a": 10, "b": "xyz", "c": 0})
        assert f({"a": 0, "b": "x", "c": 10})

        assert not f({"a": 11, "b": "x", "c": 0})


class TestQuery:
    def test_simple_eq(self, data):
        rep = Query(data).query("eq(index,1)").all()

        assert len(rep) == 1
        assert rep[0]["index"] == 1

    @pytest.mark.parametrize("op", ["eq", "ne", "lt", "le", "gt", "ge"])
    @pytest.mark.parametrize("val", [1, 10, 50, 100])
    def test_simple_cmp(self, data, op, val):

        opc = getattr(operator, op)

        rep = Query(data).query("{}(index,{})".format(op, val)).all()

        exp = [row for row in data if opc(row["index"], val)]

        assert exp == rep

    @pytest.mark.parametrize("op1", ["ne", "lt", "gt"])
    @pytest.mark.parametrize("op2", ["ne", "lt", "gt"])
    @pytest.mark.parametrize("v1", [10, 50])
    @pytest.mark.parametrize("v2", [10, 50])
    def test_double_cmp_with_and(self, data, op1, op2, v1, v2):

        opc1 = getattr(operator, op1)
        opc2 = getattr(operator, op2)

        rep = (
            Query(data)
            .query("and({op1}(index,{v1}),{op2}(position.latitude,{v2}))".format(**locals()))
            .all()
        )

        exp = [
            row for row in data if opc1(row["index"], v1) and opc2(row["position"]["latitude"], v2)
        ]

        assert exp == rep

    @pytest.mark.parametrize("op1", ["ne", "lt", "gt"])
    @pytest.mark.parametrize("op2", ["ne", "lt", "gt"])
    @pytest.mark.parametrize("v1", [10, 50])
    @pytest.mark.parametrize("v2", [10, 50])
    def test_double_cmp_with_or(self, data, op1, op2, v1, v2):
        opc1 = getattr(operator, op1)
        opc2 = getattr(operator, op2)

        rep = (
            Query(data)
            .query("or({op1}(index,{v1}),{op2}(position.latitude,{v2}))".format(**locals()))
            .all()
        )

        exp = [
            row for row in data if opc1(row["index"], v1) or opc2(row["position"]["latitude"], v2)
        ]

        assert exp == rep

    @pytest.mark.parametrize("key", ["balance", "state"])
    def test_simple_sort(self, data, key):
        rep = Query(data).query("sort({})".format(key)).all()

        assert rep == sorted(data, key=operator.itemgetter(key))

    @pytest.mark.parametrize("key", ["balance", "state"])
    def test_reverse_sort(self, data, key):
        rep = Query(data).query("sort(-{})".format(key)).all()

        assert rep == sorted(data, key=operator.itemgetter(key), reverse=True)

    def test_complex_sort(self, data):
        rep = Query(data).query("sort(balance,registered,birthdate)").all()

        assert rep == sorted(
            data, key=lambda x: (x["balance"], x["registered"], x["birthdate"])
        )

    @pytest.mark.parametrize("limit", [10, 20, 30])
    def test_simple_limit(self, data, limit):
        rep = Query(data).query("limit({})".format(limit)).all()
        assert rep == data[:limit]

    @pytest.mark.parametrize("limit", [10, 20, 30])
    @pytest.mark.parametrize("offset", [20, 40, 60])
    def test_limit_offset(self, data, limit, offset):
        rep = Query(data).query("limit({},{})".format(limit, offset)).all()
        assert rep == data[offset:][:limit]

    def test_out(self, data):
        rep = Query(data).query("out(index,(11,12,13,14,15))").all()
        exp = [row for row in data if row["index"] not in (11, 12, 13, 14, 15)]
        assert rep == exp

    def test_distinct(self, data):
        rep = Query(data + data).query("distinct()").all()
        assert rep == data

    def test_first(self, data):
        rep = Query(data).query("first()").all()
        assert rep == [data[0]]

    def test_one(self, data):
        rep = Query(data).query("eq(index,11)&one()").all()
        assert rep == [data[11]]

    def test_min(self, data):
        rep = Query(data).query("min(balance)").all()
        assert rep == min(row["balance"] for row in data)

    def test_max(self, data):
        rep = Query(data).query("max(balance)").all()
        assert rep == max(row["balance"] for row in data)

    def test_mean(self, data):
        rep = Query(data).query("mean(balance)").all()
        assert rep == sum(row["balance"] for row in data) / len(data)

    def test_sum(self, data):
        rep = Query(data).query("sum(balance)").all()
        assert rep == sum(row["balance"] for row in data)

    def test_count1(self, data):
        rep = Query(data).query("count()").all()
        assert rep == len(data)

    def test_count2(self, data):
        rep = Query(data).query("gt(balance,2000)&count()").all()
        assert rep == len([row for row in data if row["balance"] > 2000])

    def test_in_operator(self, data):
        res = Query(data).query("in(state,(FL,TX))").all()
        exp = [row for row in data if row["state"] in {"FL", "TX"}]
        assert res
        assert res == exp

    def test_out_operator(self, data):
        res = Query(data).query("out(state,(FL,TX))").all()
        exp = [row for row in data if row["state"] not in {"FL", "TX"}]
        assert res
        assert res == exp

    def test_contains_string(self, data):
        res = Query(data).query("contains(email,besto.com)").all()
        exp = [row for row in data if "besto.com" in row["email"]]
        assert res
        assert res == exp

    def test_excludes_string(self, data):
        res = Query(data).query("excludes(email,besto.com)").all()
        exp = [row for row in data if "besto.com" not in row["email"]]
        assert res
        assert res == exp

    def test_contains_array(self, data):
        res = Query(data).query("contains(tags,aliqua)").all()
        exp = [row for row in data if "aliqua" in row["tags"]]
        assert res
        assert res == exp

    def test_excludes_array(self, data):
        res = Query(data).query("excludes(tags,aliqua)").all()
        exp = [row for row in data if "aliqua" not in row["tags"]]
        assert res
        assert res == exp

    def test_select(self, data):
        res = Query(data).query("select(index,state)").all()
        exp = [{"index": row["index"], "state": row["state"]} for row in data]
        assert res
        assert res == exp

    def test_values(self, data):
        res = Query(data).query("values(state)").all()
        exp = [row["state"] for row in data]
        assert res
        assert res == exp

    def test_aggregate(self, data):
        res = Query(data).query("aggregate(state,sum(balance))").all()

        states = []
        balances = []

        for row in data:
            if row["state"] not in states:
                states.append(row["state"])
                balances.append(row["balance"])

            else:
                i = states.index(row["state"])
                balances[i] += row["balance"]

        exp = [
            {"state": state, "balance": balance}
            for (state, balance) in zip(states, balances)
        ]

        assert res
        assert res == exp

    def test_aggregate_with_filter(self, data):
        res = Query(data).query("aggregate(state,sum(balance))&isActive=true").all()

        states = []
        balances = []

        for row in data:
            if not row["isActive"]:
                continue

            if row["state"] not in states:
                states.append(row["state"])
                balances.append(row["balance"])

            else:
                i = states.index(row["state"])
                balances[i] += row["balance"]

        exp = [
            {"state": state, "balance": balance}
            for (state, balance) in zip(states, balances)
        ]

        assert res
        assert res == exp

    def test_aggregate_with_filter_and_sort(self, data):
        res = (
            Query(data)
            .query("aggregate(state,sum(balance))&isActive=true&sort(balance)")
            .all()
        )

        states = []
        balances = []

        for row in data:
            if not row["isActive"]:
                continue

            if row["state"] not in states:
                states.append(row["state"])
                balances.append(row["balance"])

            else:
                i = states.index(row["state"])
                balances[i] += row["balance"]

        exp = [
            {"state": state, "balance": balance}
            for (state, balance) in zip(states, balances)
        ]
        exp.sort(key=operator.itemgetter("balance"))

        assert res
        assert res == exp

    def test_aggregate_multiple_with_filter_and_sort(self, data):
        res = (
            Query(data)
            .query(
                "aggregate(state,sum(balance),min(position.latitude),max(position.longitude),count())&"
                "isActive=true&sort(balance)",
            )
            .all()
        )

        states = []
        balances = []
        latitudes = []
        longitudes = []
        counts = []

        for row in data:
            if not row["isActive"]:
                continue

            if row["state"] not in states:
                states.append(row["state"])
                balances.append(row["balance"])
                latitudes.append(row["position"]["latitude"])
                longitudes.append(row["position"]["longitude"])
                counts.append(1)

            else:
                i = states.index(row["state"])
                balances[i] += row["balance"]
                latitudes[i] = min(latitudes[i], row["position"]["latitude"])
                longitudes[i] = max(longitudes[i], row["position"]["longitude"])
                counts[i] += 1

        exp = [
            {
                "state": state,
                "balance": balance,
                "position.latitude": latitude,
                "position.longitude": longitude,
                "count": count,
            }
            for (state, balance, latitude, longitude, count) in zip(
                states, balances, latitudes, longitudes, counts
            )
        ]
        exp.sort(key=operator.itemgetter("balance"))

        assert res
        assert res == exp
