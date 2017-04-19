# -*- coding: utf-8 -*-

import pyparsing as pp
from pyparsing import pyparsing_common as common


def make_keyword(kwd_str, kwd_value):
    return pp.Keyword(kwd_str).setParseAction(pp.replaceWith(kwd_value))


def _or_call(expr, loc, toks):
    return {'name': 'or', 'args': [toks[0], toks[1]]}


def _and_call(expr, loc, toks):
    if len(toks) == 1:
        return toks[0]
    else:
        return {'name': 'and', 'args': [toks[0], toks[1]]}


def _eq_call(expr, loc, toks):
    return {'name': 'eq', 'args': [toks[0], toks[1]]}


def _fiql_call(expr, loc, toks):
    return {'name': toks[1], 'args': [toks[0], toks[2]]}


def _simple_call(expr, loc, toks):
    return {'name': toks.name, 'args': list(toks.get('args', []))}


def _sort_call(expr, loc, toks):
    return {'name': 'sort', 'args': toks.args.asList()}


def _array(expr, loc, toks):
    return tuple(toks)


def _calls(expr, loc, toks):
    #import pdb; pdb.set_trace()
    calls = [x for x in toks]

    if len(calls) == 1:
        return calls[0]

    else:
        return {'name': 'and', 'args': calls}


TRUE = make_keyword('true', True)
FALSE = make_keyword('false', False)
NULL = make_keyword('null', None)

# functions that require specific grammar and can't use generic SIMPLE_CALL
SORT = make_keyword('sort', None).suppress()

# grammar
PLUS = pp.Literal('+')
MINUS = pp.Literal('-')
EQUALS = pp.Literal('=').suppress()
AND = pp.Literal('&').suppress()
OR = pp.Literal('|').suppress()
DOT = pp.Literal('.')
LPAR = pp.Literal('(').suppress()
RPAR = pp.Literal(')').suppress()
COMMA = pp.Literal(',')
COLON = pp.Literal(':').suppress()

STRING = pp.Word(pp.alphanums + '_*:+-')
NUMBER = common.number

IDENT = common.identifier.setResultsName('name')

CONV_STRING = (pp.Literal('string').suppress() + COLON + STRING)
CONV_NUMBER = (pp.Literal('number').suppress() + COLON + NUMBER)
CONV_DATE = (pp.Literal('date').suppress() + COLON + common.iso8601_date)\
    .setParseAction(common.convertToDate())
# add boolean, epoch and date

CONV = (CONV_DATE | CONV_STRING | CONV_NUMBER)

VALUE = (CONV | NUMBER | TRUE | FALSE | NULL | STRING)

ARRAY = (LPAR + pp.delimitedList(VALUE) + RPAR).setParseAction(_array) | VALUE

EQ_EXPR = (IDENT + EQUALS + ARRAY).setParseAction(_eq_call)
FIQL_EXPR = (IDENT + EQUALS + IDENT + EQUALS + ARRAY).setParseAction(_fiql_call)

CALL = pp.Forward()

ARG = pp.Forward()


OR_EXPR = (ARG + OR + ARG).setParseAction(_or_call)
AND_EXPR = (ARG + AND + ARG).setParseAction(_and_call)

ARGLIST = pp.delimitedList(ARG).setResultsName('args')

ARGARRAY = LPAR + ARGLIST + RPAR

ARG <<= (CALL | ARRAY | ARGARRAY)

SIMPLE_CALL = (IDENT + LPAR + pp.Optional(ARGLIST) + RPAR).setParseAction(_simple_call)

SORT_ARG = ((MINUS | PLUS) + ARRAY).setParseAction(lambda e, l, t: tuple(t))
SORT_ARGLIST = pp.delimitedList(SORT_ARG).setResultsName('args')
SORT_CALL = (SORT + LPAR + SORT_ARGLIST + RPAR).setParseAction(_sort_call)

CALL <<= (SORT_CALL | SIMPLE_CALL | FIQL_EXPR | EQ_EXPR)

AND_CALL = (CALL + AND + CALL).setParseAction(_and_call)
OR_CALL = (CALL + OR + CALL).setParseAction(_or_call)

OPCALL = (AND_CALL | OR_CALL | CALL)

OPCALLS = (pp.Optional(LPAR) + pp.delimitedList(OPCALL) + pp.Optional(RPAR)).setParseAction(_calls)

CALLS = (pp.Optional(LPAR) + pp.delimitedList(OPCALLS) + pp.Optional(RPAR)).setParseAction(_calls)

TOPLEVEL = CALLS


class Parser:

    def parse(self, expr):
        result = TOPLEVEL.parseString(expr)

        return result[0]


parser = Parser()
