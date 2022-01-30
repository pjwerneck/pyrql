# -*- coding: utf-8 -*-

from datetime import datetime
from decimal import Decimal
from uuid import UUID

import pyparsing as pp
from dateutil.parser import parse as dateparse
from pyparsing import pyparsing_common as common
from six.moves import urllib

from .exceptions import RQLSyntaxError

# autoconvert:
# numbers
# booleans
# null

# converters:
# number
# epoch
# date
# datetime
# boolean
# string
# uuid
# decimal


def _sort_call(expr, loc, toks):
    return {"name": "sort", "args": toks.args.asList()}


def _array(expr, loc, toks):
    return tuple(toks)


def _unquote(expr, loc, toks):
    return urllib.parse.unquote(toks[0])


def _call_operator(expr, loc, toks):
    return toks.asDict()


def _comparison(expr, loc, toks):
    if len(toks) == 2:
        return {"name": "eq", "args": toks.asList()}

    else:
        op = toks.pop(1)
        return {"name": op, "args": toks.asList()}


def _or(expr, loc, toks):
    if len(toks) == 1:
        return toks[0]
    else:
        return {"name": "or", "args": toks.asList()}


def _and(expr, loc, toks):
    if len(toks) == 1:
        return toks[0]
    else:
        return {"name": "and", "args": toks.asList()}


def _group(expr, loc, toks):
    return toks[0]


def _date(expr, loc, toks):
    return dateparse(toks[0]).date()


def _datetime(expr, loc, toks):
    return dateparse(toks[0])


def _epoch(expr, loc, toks):
    return datetime.utcfromtimestamp(toks[0])


def _decimal(expr, loc, toks):
    return Decimal(toks[0])


def _uuid(expr, loc, toks):
    return UUID(hex=toks[0])


TRUE = pp.Keyword("true").setParseAction(pp.replaceWith(True))
FALSE = pp.Keyword("false").setParseAction(pp.replaceWith(False))
NULL = pp.Keyword("null").setParseAction(pp.replaceWith(None))

# let's treat sort as a keyword to better handle the +- prefix syntax
SORT = pp.Keyword("sort").suppress()

# keywords for typed values
K_NUMBER = pp.Keyword("number").suppress()
K_STRING = pp.Keyword("string").suppress()
K_DATE = pp.Keyword("date").suppress()
K_DATETIME = pp.Keyword("datetime").suppress()
K_BOOL = pp.Keyword("boolean").suppress()
K_EPOCH = pp.Keyword("epoch").suppress()
K_UUID = pp.Keyword("uuid").suppress()
K_DECIMAL = pp.Keyword("decimal").suppress()

# grammar
PLUS = pp.Literal("+")
MINUS = pp.Literal("-")
EQUALS = pp.Literal("=").suppress()
LPAR = pp.Literal("(").suppress()
RPAR = pp.Literal(")").suppress()
COLON = pp.Literal(":").suppress()

# reserved characters that are not part of the RQL grammar
RESERVED = pp.Word("@!*+$", exact=1)

UNRESERVED = pp.Word(pp.pyparsing_unicode.alphanums + "-:._~ ", exact=1)
PCT_ENCODED = pp.Combine(pp.Literal("%") + pp.Word(pp.hexnums, exact=2)).setParseAction(_unquote)
NCHAR = UNRESERVED | PCT_ENCODED | RESERVED

STRING = pp.Combine(pp.OneOrMore(NCHAR))

NAME = common.identifier

NUMBER = common.number

TYPED_STRING = K_STRING + COLON + STRING
TYPED_NUMBER = K_NUMBER + COLON + common.number
TYPED_DATE = (K_DATE + COLON + common.iso8601_date).setParseAction(_date)
TYPED_DATETIME = (K_DATETIME + COLON + common.iso8601_datetime).setParseAction(_datetime)
TYPED_BOOL = K_BOOL + COLON + (TRUE | FALSE)
TYPED_EPOCH = (K_EPOCH + COLON + common.number).setParseAction(_epoch)
TYPED_UUID = (K_UUID + COLON + STRING).setParseAction(_uuid)
TYPED_DECIMAL = (K_DECIMAL + COLON + STRING).setParseAction(_decimal)

TYPED_VALUE = (
    TYPED_DECIMAL | TYPED_UUID | TYPED_EPOCH | TYPED_DATETIME | TYPED_DATE | TYPED_NUMBER | TYPED_BOOL | TYPED_STRING
)

ARRAY = pp.Forward()

# using ^ instead of | between NUMBER and STRING to avoid ambiguity
# when parsing strings starting with numbers
VALUE = TYPED_VALUE | ARRAY | TRUE | FALSE | NULL | (NUMBER ^ STRING)

PAR_ARRAY = (LPAR + pp.delimitedList(VALUE) + RPAR).setParseAction(_array)

ARRAY <<= PAR_ARRAY

CALL_OPERATOR = pp.Forward()

ARGUMENT = CALL_OPERATOR | VALUE

SORT_ARG = ((MINUS | PLUS) + VALUE).setParseAction(lambda e, l, t: tuple(t))
SORT_ARGARRAY = pp.delimitedList(SORT_ARG).setResultsName("args")
SORT_CALL = (SORT + LPAR + SORT_ARGARRAY + RPAR).setParseAction(_sort_call)

FUNC_CALL = (
    NAME.setResultsName("name")
    + LPAR
    + pp.Group(pp.Optional(pp.delimitedList(ARGUMENT))).setResultsName("args")
    + RPAR
).setParseAction(_call_operator)

CALL_OPERATOR <<= SORT_CALL | FUNC_CALL

COMPARISON = (VALUE + EQUALS + pp.Optional(NAME + EQUALS) + VALUE).setParseAction(_comparison)

OPERATOR = pp.Forward()

OR = pp.delimitedList(OPERATOR, delim=pp.Literal("|")).setParseAction(_or)
AND = pp.delimitedList(OPERATOR, delim=pp.Literal("&")).setParseAction(_and)


GROUP = (LPAR + (OR | AND) + RPAR).setParseAction(_group)

OPERATOR <<= GROUP | COMPARISON | CALL_OPERATOR

QUERY = pp.delimitedList(AND).setParseAction(_and)


class Parser:
    def parse(self, expr):
        try:
            result = QUERY.parseString(expr, parseAll=True)
        except pp.ParseException as exc:
            raise RQLSyntaxError(*exc.args)

        return result[0]
