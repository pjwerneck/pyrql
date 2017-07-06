# -*- coding: utf-8 -*-


from pyrql import parse


CMP_OPS = ['eq', 'lt', 'le', 'gt', 'ge', 'ne']


class TestReportedErrors:

    def test_like_with_string_parameter(self):
        expr = 'like(name,*new jack city*)'
        rep = {'name': 'like', 'args': ['name', '*new jack city*']}

        pd = parse(expr)
        assert pd == rep

    def test_like_with_string_encoded_parameter(self):
        expr = 'like(name,*new%20jack%20city*)'
        rep = {'name': 'like', 'args': ['name', '*new jack city*']}

        pd = parse(expr)
        assert pd == rep
