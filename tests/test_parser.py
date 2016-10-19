# -*- coding: utf-8 -*-

from pyrql.parser import parser

import pytest


@pytest.mark.parametrize('func', ['eq', 'lt', 'le', 'gt', 'ge', 'ne'])
def test_cmp_functions(func):
    parsed = parser.parse('%s(a, 1)' % func)
    assert parsed == {'name': func, 'args': ['a', 1]}

    parsed = parser.parse('%s((a,b,c), 1)' % func)
    assert parsed == {'name': func, 'args': [('a', 'b', 'c'), 1]}


@pytest.mark.parametrize('func', ['eq', 'lt', 'le', 'gt', 'ge', 'ne'])
def test_cmp_ops_functions(func):
    parsed = parser.parse('a=%s=1' % func)
    assert parsed == {'name': func, 'args': ['a', 1]}

    parsed = parser.parse('%s((a,b,c), 1)' % func)
    assert parsed == {'name': func, 'args': [('a', 'b', 'c'), 1]}


def test_equality_operator():
    p1 = parser.parse('lero=0')
    p2 = parser.parse('eq(lero, 0)')

    assert p1 == p2


def test_and_operator():
    p1 = parser.parse('eq(a,0)&eq(b,1)')
    p2 = parser.parse('and(eq(a, 0), eq(b, 1))')
    assert p1 == p2


def test_or_operator():
    p1 = parser.parse('eq(a,0)|eq(b,1)')
    p2 = parser.parse('or(eq(a, 0), eq(b, 1))')
    assert p1 == p2


@pytest.mark.parametrize('func', ['in', 'out', 'contains', 'excludes'])
def test_member_functions(func):
    parsed = parser.parse('%s(name, (a,b))' % func)
    assert parsed == {'name': func, 'args': ['name', ('a', 'b')]}


@pytest.mark.skip()
def test_rel_function():
    # how is this one supposed to work?
    pass


@pytest.mark.parametrize('func', ['and', 'or'])
def test_bool_functions(func):
    parsed = parser.parse('%s(a, b)' % func)
    assert parsed == {'name': func, 'args': ['a', 'b']}

    parsed = parser.parse('%s(a, b, c)' % func)
    assert parsed == {'name': func, 'args': ['a', 'b', 'c']}


def test_sort_function():
    parsed = parser.parse('sort(+lero)')
    assert parsed == {'name': 'sort', 'args': [('+', 'lero')]}

    parsed = parser.parse('sort(+foo, -bar)')
    assert parsed == {'name': 'sort', 'args': [('+', 'foo'), ('-', 'bar')]}

    parsed = parser.parse('sort(+(foo,bar), -lero)')
    assert parsed == {'name': 'sort', 'args': [('+', ('foo', 'bar')), ('-', 'lero')]}


@pytest.mark.parametrize('func', ['select', 'values'])
def test_query_functions(func):
    parsed = parser.parse('%s(username, password, (address, city))' % func)
    assert parsed == {'name': func, 'args': ['username', 'password', ('address', 'city')]}


@pytest.mark.parametrize('func', ['sum', 'mean', 'max', 'min', 'count'])
def test_aggregate_functions(func):
    parsed = parser.parse('%s((a, b, c))' % func)
    assert parsed == {'name': func, 'args': [('a', 'b', 'c')]}


@pytest.mark.parametrize('func', ['distinct', 'first', 'one'])
def test_result_functions(func):
    parsed = parser.parse('%s()' % func)
    assert parsed == {'name': func, 'args': []}


def test_limit_function():
    parsed = parser.parse('limit(10, 0)')
    assert parsed == {'name': 'limit', 'args': [10, 0]}


def test_recurse_function():
    parsed = parser.parse('recurse(lero)')
    assert parsed == {'name': 'recurse', 'args': ['lero']}


@pytest.mark.parametrize('expr', ['foo=3&price=lt=10',
                                  'eq(foo,3)&lt(price,10)',
                                  'and(eq(foo,3),lt(price,10))',
                                  ])
def test_equivalent_expressions(expr):
    parsed = parser.parse(expr)

    assert parsed == {'name': 'and', 'args': [{'name': 'eq', 'args': ['foo', 3]},
                                              {'name': 'lt', 'args': ['price', 10]}]}


def test_toplevel_and():
    parsed = parser.parse('eq(a, 1),eq(b, 2),eq(c, 3)')

    assert parsed == {'name': 'and', 'args': [{'name': 'eq', 'args': ['a', 1]},
                                              {'name': 'eq', 'args': ['b', 2]},
                                              {'name': 'eq', 'args': ['c', 3]},
                                              ]}


def test_parenthesis():
    parsed = parser.parse('(state=Florida|state=Alabama)&gender=female')

    assert parsed == {'name': 'and',
                      'args': [{'name': 'or',
                                'args': [{'name': 'eq', 'args': ['state', 'Florida']},
                                         {'name': 'eq', 'args': ['state', 'Alabama']},
                                         ],
                                },
                               {'name': 'eq', 'args': ['gender', 'female']}]}
