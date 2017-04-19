# -*- coding: utf-8 -*-

import datetime

import pytest

from pyrql import parser as pm
from pyrql.unparser import unparser


parser = pm.parser

CMP_OPS = ['eq', 'lt', 'le', 'gt', 'ge', 'ne']


class TestTokens:

    @pytest.mark.parametrize('expr', ['1', '2', '3'])
    def test_integer(self, expr):
        pd = pm.NUMBER.parseString(expr)
        assert pd[0] == int(expr)

    @pytest.mark.parametrize('expr', ['1.4', '2.1', '3.14', '4'])
    def test_float(self, expr):
        pd = pm.NUMBER.parseString(expr)
        assert pd[0] == float(expr)

    @pytest.mark.parametrize('expr', ['abc', 'DEF', 'F00'])
    def test_string(self, expr):
        pd = pm.STRING.parseString(expr)
        assert pd[0] == expr

    @pytest.mark.parametrize('pair', [('string:3', '3'),
                                      ('number:3', 3),
                                      ('date:2017-01-01', datetime.date(2017, 1, 1)),
                                      ])
    def test_conv(self, pair):
        expr, expected = pair

        pd = pm.CONV.parseString(expr)
        assert pd[0] == expected

    @pytest.mark.parametrize('expr', ['eq', 'sort', 'contains'])
    def test_ident(self, expr):
        pd = pm.IDENT.parseString(expr)
        assert pd[0] == expr

    @pytest.mark.parametrize(
        'pair',
        [('1', 1), ('3.14', 3.14), ('lero', 'lero'),
         ('true', True), ('false', False), ('null', None),
         ('string:123', '123'), ('number:123', 123),
         ('date:2017-01-01', datetime.date(2017, 1, 1)),
         ('(1,2,3,4)', (1, 2, 3, 4)),
         ])
    def test_value(self, pair):
        expr, expected = pair

        pd = pm.ARRAY.parseString(expr)
        assert pd[0] == expected

    @pytest.mark.parametrize(
        'pair',
        [('1', 1), ('3.14', 3.14), ('lero', 'lero'), ('true', True),
         ('false', False), ('null', None), ('(1, 2, 3)', (1, 2, 3))])
    def test_arg(self, pair):
        expr, expected = pair

        pd = pm.ARG.parseString(expr)
        assert pd[0] == expected

    @pytest.mark.parametrize(
        'pair',
        [('1', [1]),
         ('1,3.14,lero,true,false,null', [1, 3.14, 'lero', True, False, None])])
    def test_arglist(self, pair):
        expr, expected = pair

        pd = pm.ARGLIST.parseString(expr)
        assert list(pd) == expected

    @pytest.mark.parametrize(
        'pair',
        [('a()', []),
         ('a(1)', [1]),
         ('a(x,y,z)', ['x', 'y', 'z']),
         ('a(string:1,string:2)', ['1', '2']),
         ('a(date:2017-01-01)', [datetime.date(2017, 1, 1)])
         ])
    def test_simple_call(self, pair):
        expr, args = pair

        pd = pm.SIMPLE_CALL.parseString(expr)
        assert pd[0] == {'name': 'a', 'args': args}

    @pytest.mark.parametrize(
        'pair',
        [('a()', []),
         ('a(1)', [1]),
         ('a(x,y,z)', ['x', 'y', 'z']),
         ('a(string:1,number:2)', ['1', 2]),
         ('a(date:2017-01-01)', [datetime.date(2017, 1, 1)])
         ])
    def test_call(self, pair):
        expr, args = pair

        pd = pm.CALL.parseString(expr)
        assert pd[0] == {'name': 'a', 'args': args}

    @pytest.mark.parametrize(
        'pair',
        [('a=1', ['a', 1]), ('a=xyz', ['a', 'xyz']), ('a=string:1', ['a', '1']),
         ('a=date:2017-01-01', ['a', datetime.date(2017, 1, 1)])])
    def test_call_eq_expressions(self, pair):
        expr, args = pair

        pd = pm.CALL.parseString(expr)
        assert pd[0] == {'name': 'eq', 'args': args}

    @pytest.mark.parametrize('op', CMP_OPS)
    @pytest.mark.parametrize(
        'pair',
        [('a=%s=1', ['a', 1]), ('a=%s=xyz', ['a', 'xyz']), ('a=%s=string:1', ['a', '1']),
         ('a=%s=date:2017-01-01', ['a', datetime.date(2017, 1, 1)])])
    def test_call_fiql_expression(self, op, pair):
        expr, args = pair

        pd = pm.CALL.parseString(expr % op)
        assert pd[0] == {'name': op, 'args': args}

    def test_call_nested(self):
        expr = 'a(1,b(2),3)'

        pd = pm.CALL.parseString(expr)
        assert pd[0] == {'name': 'a', 'args': [1, {'name': 'b', 'args': [2]}, 3]}

    @pytest.mark.parametrize('op', CMP_OPS)
    @pytest.mark.parametrize(
        'pair',
        [('%s(a,1)', ['a', 1]), ('%s(a,xyz)', ['a', 'xyz']), ('%s(a,string:1)', ['a', '1']),
         ('%s(a,(1,2,3))', ['a', (1, 2, 3)]),
         ('%s(a,date:2017-01-01)', ['a', datetime.date(2017, 1, 1)])])
    def test_call_cmp_functions(self, op, pair):
        expr, args = pair

        pd = pm.CALL.parseString(expr % op)
        assert pd[0] == {'name': op, 'args': args}

    def test_and_operator(self):
        expr = 'a(1)&b(2)'

        pd = pm.OPCALL.parseString(expr)
        assert pd[0] == {'name': 'and', 'args': [{'name': 'a', 'args': [1]},
                                                 {'name': 'b', 'args': [2]}]}

    def test_or_operator(self):
        expr = 'a(1)|b(2)'

        pd = pm.OPCALL.parseString(expr)
        assert pd[0] == {'name': 'or', 'args': [{'name': 'a', 'args': [1]},
                                                 {'name': 'b', 'args': [2]}]}

    def test_call_parenthesis(self):
        expr = '(a(1))'

        pd = pm.ARG.parseString(expr)
        assert pd[0] == {'name': 'a', 'args': [1]}


class TestParser:
    def test_equality_operator(self):
        p1 = parser.parse('lero=0')
        p2 = parser.parse('eq(lero, 0)')

        assert p1 == p2

    def test_and_operator_pair(self):
        p1 = parser.parse('eq(a,0)&eq(b,1)')
        p2 = parser.parse('and(eq(a, 0), eq(b, 1))')

        p3 = {'name': 'and', 'args': [{'name': 'eq', 'args': ['a', 0]},
                                      {'name': 'eq', 'args': ['b', 1]}]}

        assert p1 == p2
        assert p1 == p3

    def test_and_operator_triple(self):
        p1 = parser.parse('eq(a,0)&eq(b,1)&eq(c,2)')
        p2 = parser.parse('and(eq(a, 0), eq(b, 1))')

        p3 = {'name': 'and', 'args': [{'name': 'eq', 'args': ['a', 0]},
                                      {'name': 'eq', 'args': ['b', 1]},
                                      {'name': 'eq', 'args': ['c', 2]}]}

        assert p1 == p2
        assert p1 == p3


    def test_or_operator(self):
        p1 = parser.parse('eq(a,0)|eq(b,1)')
        p2 = parser.parse('or(eq(a, 0), eq(b, 1))')

        p3 = {'name': 'or', 'args': [{'name': 'eq', 'args': ['a', 0]},
                                     {'name': 'eq', 'args': ['b', 1]}]}

        assert p1 == p2
        assert p1 == p3

    @pytest.mark.parametrize('func', ['in', 'out', 'contains', 'excludes'])
    def test_member_functions(self, func):
        expr = '%s(name,(a,b))' % func
        parsed = {'name': func, 'args': ['name', ('a', 'b')]}

        assert parser.parse(expr) == parsed
        assert unparser.unparse(parsed) == expr

    @pytest.mark.parametrize('func', ['and', 'or'])
    def test_bool_functions(self, func):
        expr = '%s(a,b)' % func
        parsed = {'name': func, 'args': ['a', 'b']}

        assert parser.parse(expr) == parsed
        assert unparser.unparse(parsed, level=1) == expr

        expr = '%s(a,b,c)' % func
        parsed = {'name': func, 'args': ['a', 'b', 'c']}

        assert parser.parse(expr) == parsed
        assert unparser.unparse(parsed, level=1) == expr

    def test_sort_function(self):
        expr = 'sort(+lero)'
        parsed = {'name': 'sort', 'args': [('+', 'lero')]}

        assert parser.parse(expr) == parsed
        assert unparser.unparse(parsed) == expr

        expr = 'sort(+foo,-bar)'
        parsed = {'name': 'sort', 'args': [('+', 'foo'), ('-', 'bar')]}

        assert parser.parse(expr) == parsed
        assert unparser.unparse(parsed) == expr

        expr = 'sort(+(foo,bar),-lero)'
        parsed = {'name': 'sort', 'args': [('+', ('foo', 'bar')), ('-', 'lero')]}

        assert parser.parse(expr) == parsed
        assert unparser.unparse(parsed) == expr

    @pytest.mark.parametrize('func', ['select', 'values'])
    def test_query_functions(self, func):
        expr = '%s(username,password,(address,city))' % func
        parsed = {'name': func, 'args': ['username', 'password', ('address', 'city')]}

        assert parser.parse(expr) == parsed
        assert unparser.unparse(parsed) == expr

    @pytest.mark.parametrize('func', ['sum', 'mean', 'max', 'min', 'count'])
    def test_aggregate_functions(self, func):
        expr = '%s((a,b,c))' % func
        parsed = {'name': func, 'args': [('a', 'b', 'c')]}

        assert parser.parse(expr) == parsed
        assert unparser.unparse(parsed) == expr

    @pytest.mark.parametrize('func', ['distinct', 'first', 'one'])
    def test_result_functions(self, func):
        expr = '%s()' % func
        parsed = {'name': func, 'args': []}

        assert parser.parse(expr) == parsed
        assert unparser.unparse(parsed) == expr

    def test_limit_function(self):
        expr = 'limit(10,0)'
        parsed = {'name': 'limit', 'args': [10, 0]}

        assert parser.parse(expr) == parsed
        assert unparser.unparse(parsed) == expr

    def test_recurse_function(self):
        expr = 'recurse(lero)'
        parsed = {'name': 'recurse', 'args': ['lero']}

        assert parser.parse(expr) == parsed
        assert unparser.unparse(parsed) == expr

    @pytest.mark.parametrize('expr', ['foo=3&price=lt=10',
                                      'eq(foo,3)&lt(price,10)',
                                      'and(eq(foo,3),lt(price,10))',
                                      ])
    def test_equivalent_expressions(self, expr):
        parsed = parser.parse(expr)

        assert parsed == {'name': 'and', 'args': [{'name': 'eq', 'args': ['foo', 3]},
                                                  {'name': 'lt', 'args': ['price', 10]}]}

    def test_toplevel_and(self):
        parsed = parser.parse('eq(a, 1),eq(b, 2),eq(c, 3)')

        assert parsed == {'name': 'and', 'args': [{'name': 'eq', 'args': ['a', 1]},
                                                  {'name': 'eq', 'args': ['b', 2]},
                                                  {'name': 'eq', 'args': ['c', 3]},
                                                  ]}

    def test_parenthesis(self):
        parsed = parser.parse('(state=Florida|state=Alabama)&gender=female')

        import pdb; pdb.set_trace()

        assert parsed == {'name': 'and',
                          'args': [{'name': 'or',
                                    'args': [{'name': 'eq', 'args': ['state', 'Florida']},
                                             {'name': 'eq', 'args': ['state', 'Alabama']},
                                             ],
                                    },
                                   {'name': 'eq', 'args': ['gender', 'female']}]}
