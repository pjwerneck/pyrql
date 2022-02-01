# -*- coding: utf-8 -*-

from pyrql.exceptions import RQLError
from pyrql.exceptions import RQLQueryError
from pyrql.exceptions import RQLSyntaxError
from pyrql.parser import Parser
from pyrql.query import Query
from pyrql.unparser import Unparser

__title__ = "pyrql"
__version__ = "0.7.5"
__author__ = "Pedro Werneck"
__license__ = "MIT"


parse = Parser().parse

unparse = Unparser().unparse

__all__ = ["parse", "unparse", "Query", "RQLError", "RQLQueryError", "RQLSyntaxError"]
