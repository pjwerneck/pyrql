# -*- coding: utf-8 -*-

from pyrql.parser import parser

import pytest


def test_single_argument_call():
    parsed = parser.parse('lero(foo)')
    assert parsed == {'name': 'lero', 'args': ['foo']}


def test_multiple_arguments_call():
    parsed = parser.parse('lero(foo, bar)')
    assert parsed == {'name': 'lero', 'args': ['foo', 'bar']}


def test_nested_call():
    parsed = parser.parse('and(lero(1), lero(2))')
    assert parsed == {'name': 'and', 'args': [{'name': 'lero', 'args': [1]},
                                              {'name': 'lero', 'args': [2]}]}


def test_deep_nested_call():
    parsed = parser.parse('or(lero(0), and(lero(1), lero(2)))')
    assert parsed == {'name': 'or',
                      'args': [{'name': 'lero', 'args': [0]},
                               {'name': 'and', 'args': [{'name': 'lero', 'args': [1]},
                                                        {'name': 'lero', 'args': [2]}]}]}


def test_arg_array():
    parsed = parser.parse('lero((1, 2, 3))')
    assert parsed == {'name': 'lero', 'args': [(1, 2, 3)]}


@pytest.mark.skip()
def test_persvr_example():
    parsed = parser.parse("(foo=3|foo=bar)&price=lt=10")

    assert parsed == {'name': 'and',
                      'args': [{'name': "or",
                                'args': [{'name': "eq",
                                          'args': ["foo", 3]},
                                         {'name': "eq",
                                          'args': ["foo", "bar"]}
                                         ]},
                               {'name': "lt",
                                'args': ["price", 10]
                                }]}
