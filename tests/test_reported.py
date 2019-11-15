# -*- coding: utf-8 -*-


from pyrql import parse


CMP_OPS = ["eq", "lt", "le", "gt", "ge", "ne"]


class TestReportedErrors:
    def test_like_with_string_parameter(self):
        expr = "like(name,*new jack city*)"
        rep = {"name": "like", "args": ["name", "*new jack city*"]}

        pd = parse(expr)
        assert pd == rep

    def test_like_with_string_encoded_parameter(self):
        expr = "like(name,*new%20jack%20city*)"
        rep = {"name": "like", "args": ["name", "*new jack city*"]}

        pd = parse(expr)
        assert pd == rep

    def test_string_starting_with_number(self):
        expr = "uuid=27f1db1c029e4a428961b85433de25fd"
        rep = {"name": "eq", "args": ["uuid", "27f1db1c029e4a428961b85433de25fd"]}

        pd = parse(expr)
        assert pd == rep
