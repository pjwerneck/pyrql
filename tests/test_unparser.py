# -*- coding: utf-8 -*-

import pytest

from pyrql import unparse


@pytest.mark.parametrize("func", ["eq", "lt", "le", "gt", "ge", "ne"])
def test_cmp_functions(func):
    parsed = {"name": func, "args": ["a", 1]}
    assert unparse(parsed) == "%s(a,1)" % func

    parsed = {"name": func, "args": [("a", "b", "c"), 1]}
    assert unparse(parsed) == "%s((a,b,c),1)" % func
