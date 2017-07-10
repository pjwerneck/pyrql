# -*- coding: utf-8 -*-

from pyrql.exceptions import RQLSyntaxError
from pyrql.parser import Parser
from pyrql.unparser import Unparser


__title__ = 'pyrql'
__version__ = '0.4.1'
__author__ = 'Pedro Werneck'
__license__ = 'MIT'


parse = Parser().parse

unparse = Unparser().unparse


__all__ = ['parse', 'unparse', 'RQLSyntaxError']
