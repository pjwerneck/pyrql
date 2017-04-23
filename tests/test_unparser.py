# -*- coding: utf-8 -*-

from pyrql.parser import parser
from pyrql.unparser import unparser

import pytest


@pytest.mark.parametrize('func', ['eq', 'lt', 'le', 'gt', 'ge', 'ne'])
def test_cmp_functions(func):
    parsed = {'name': func, 'args': ['a', 1]}
    assert unparser.unparse(parsed) == '%s(a,1)' % func

    parsed = {'name': func, 'args': [('a', 'b', 'c'), 1]}
    assert unparser.unparse(parsed) == '%s((a,b,c),1)' % func
