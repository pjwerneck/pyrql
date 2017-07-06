# -*- coding: utf-8 -*-

from pyrql.exceptions import RQLSyntaxError
from pyrql.parser import Parser
from pyrql.unparser import Unparser


parse = Parser().parse

unparse = Unparser().unparse


__all__ = ['parse', 'unparse', 'RQLSyntaxError']
