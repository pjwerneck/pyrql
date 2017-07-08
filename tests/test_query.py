# -*- coding: utf-8 -*-

import json
import operator
import os
import sys

import pytest

from pyrql import query
from pyrql.query import And
from pyrql.query import Filter
from pyrql.query import Or


@pytest.fixture(scope='session')
def data():
    with open(os.path.join(os.path.dirname(__file__), 'testdata.json')) as f:
        data_ = json.load(f)

    return data_


class TestBase:

    @pytest.mark.parametrize('op,tv,fv',
                             [('eq', 10, 9),
                              ('ne', 9, 10),
                              ('lt', 9, 11),
                              ('le', 10, 11),
                              ('gt', 11, 10),
                              ('ge', 10, 9),
                              ])
    def test_filter_operators(self, op, tv, fv):
        f = Filter(op, ['id', 10])

        assert f({'id': tv})
        assert not f({'id': fv})

    def test_and_operator(self):
        a = Filter('eq', ['a', 10])
        b = Filter('eq', ['b', 'xyz'])

        f = And(a, b)

        assert f({'a': 10, 'b': 'xyz'})
        assert not f({'a': 11, 'b': 'xyz'})
        assert not f({'a': 10, 'b': None})

    def test_or_operator(self):
        a = Filter('eq', ['a', 10])
        b = Filter('eq', ['b', 'xyz'])

        f = Or(a, b)

        assert f({'a': 10, 'b': 'x'})
        assert f({'a': 0, 'b': 'xyz'})

        assert not f({'a': 0, 'b': 'x'})

    def test_nested_operators(self):
        a = Filter('eq', ['a', 10])
        b = Filter('eq', ['b', 'xyz'])
        c = Filter('eq', ['c', 10])

        f = Or(And(a, b), c)

        assert f({'a': 10, 'b': 'xyz', 'c': 0})
        assert f({'a': 0, 'b': 'x', 'c': 10})

        assert not f({'a': 11, 'b': 'x', 'c': 0})


class TestQuery:

    def test_simple_eq(self, data):
        rep = query('eq(user_id,1)', data)

        assert len(rep) == 1
        assert rep[0]['user_id'] == 1

    @pytest.mark.parametrize('op', ['eq', 'ne', 'lt', 'le', 'gt', 'ge'])
    @pytest.mark.parametrize('val', [1, 10, 50, 100])
    def test_simple_cmp(self, data, op, val):

        opc = getattr(operator, op)

        rep = query('{}(user_id,{})'.format(op, val), data)

        exp = [row for row in data if opc(row['user_id'], val)]

        assert exp == rep

    @pytest.mark.parametrize('op1', ['ne', 'lt', 'gt'])
    @pytest.mark.parametrize('op2', ['ne', 'lt', 'gt'])
    @pytest.mark.parametrize('v1', [10, 50])
    @pytest.mark.parametrize('v2', [10, 50])
    def test_double_cmp_with_and(self, data, op1, op2, v1, v2):

        opc1 = getattr(operator, op1)
        opc2 = getattr(operator, op2)

        rep = query('and({op1}(user_id,{v1}),{op2}(distance,{v2}))'.format(**locals()), data)

        exp = [row for row in data if opc1(row['user_id'], v1) and opc2(row['distance'], v2)]

        assert exp == rep

    @pytest.mark.parametrize('op1', ['ne', 'lt', 'gt'])
    @pytest.mark.parametrize('op2', ['ne', 'lt', 'gt'])
    @pytest.mark.parametrize('v1', [10, 50])
    @pytest.mark.parametrize('v2', [10, 50])
    def test_double_cmp_with_or(self, data, op1, op2, v1, v2):
        opc1 = getattr(operator, op1)
        opc2 = getattr(operator, op2)

        rep = query('or({op1}(user_id,{v1}),{op2}(distance,{v2}))'.format(**locals()), data)

        exp = [row for row in data if opc1(row['user_id'], v1) or opc2(row['distance'], v2)]

        assert exp == rep

    @pytest.mark.parametrize('key', ['distance', 'state'])
    def test_simple_sort(self, data, key):
        rep = query('sort({})'.format(key), data)

        assert rep == sorted(data, key=operator.itemgetter(key))

    @pytest.mark.parametrize('key', ['distance', 'state'])
    def test_reverse_sort(self, data, key):
        rep = query('sort(-{})'.format(key), data)

        assert rep == sorted(data, key=operator.itemgetter(key), reverse=True)

    @pytest.mark.parametrize('limit', [10, 20, 30])
    def test_simple_limit(self, data, limit):
        rep = query('limit({})'.format(limit), data)

        assert rep == data[:limit]

    @pytest.mark.parametrize('limit', [10, 20, 30])
    @pytest.mark.parametrize('offset', [20, 40, 60])
    def test_limit_offset(self, data, limit, offset):
        rep = query('limit({},{})'.format(limit, offset), data)

        assert rep == data[offset:][:limit]

    def test_in(self, data):
        rep = query('in(user_id,(11,12,13,14,15))', data)

        exp = [row for row in data if row['user_id'] in (11, 12, 13, 14, 15)]

        assert rep == exp

    def test_out(self, data):
        rep = query('out(user_id,(11,12,13,14,15))', data)

        exp = [row for row in data if row['user_id'] not in (11, 12, 13, 14, 15)]

        assert rep == exp

    def test_distinct(self, data):
        rep = query('distinct()', data + data)

        assert rep == data

    def test_first(self, data):
        rep = query('first()', data)

        assert rep == [data[0]]

    def test_one(self, data):
        rep = query('first()', data[:1])

        assert rep == [data[0]]

    def test_count(self, data):
        rep = query('count()', data)

        assert rep == len(data)
