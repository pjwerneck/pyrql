# -*- coding: utf-8 -*-


import ply.lex as lex
import ply.yacc as yacc

from .exceptions import RQLSyntaxError


RESERVED = {
    # 'aggregate': 'AGGREGATE',
    # 'and': 'AND',
    # 'contains': 'CONTAINS',
    # 'count': 'COUNT',
    # 'distinct': 'DISTINCT',
    # 'eq': 'EQ',
    # 'excludes': 'EXCLUDES',
    # 'first': 'FIRST',
    # 'ge': 'GE',
    # 'gt': 'GT',
    # 'in': 'IN',
    # 'le': 'LE',
    # 'limit': 'LIMIT',
    # 'lt': 'LT',
    # 'max': 'MAX',
    # 'mean': 'MEAN',
    # 'min': 'MIN',
    # 'ne': 'NE',
    # 'one': 'ONE',
    # 'or': 'OR',
    # 'out': 'OUT',
    # 'recurse': 'RECURSE',
    # 'rel': 'REL',
    # 'select': 'SELECT',
    'sort': 'SORT',
    # 'sum': 'SUM',
    # 'values': 'VALUES'
    'true': 'BOOL_TRUE',
    'false': 'BOOL_FALSE',
    'null': 'NULL',
    }

tokens = (
    'NAME',
    'LPAREN',
    'RPAREN',
    'ICONST',
    'FCONST',
    # 'SCONST',

    # delimiters
    # 'DOT',
    'COMMA',

    # operators
    'PLUS',
    'MINUS',

    # 'DIV',
    'EQUALS',
    'AND',
    'OR',

    ) + tuple(RESERVED.values())


precedence = (
    ('left', 'OR'),
    ('left', 'AND'),
    )

# t_DOT = r'\.'
t_COMMA = r','


# operators
t_PLUS = r'\+'
t_MINUS = r'-'
# t_DIV = r'/'
t_EQUALS = r'='
t_AND = r'&'
t_OR = r'\|'

t_ignore = ' \t'

t_BOOL_TRUE = r'true'
t_BOOL_FALSE = r'false'
t_NULL = r'null'


def t_NAME(t):
    r'[a-zA-Z_\*][a-zA-Z0-9 _\*:]*'
    t.type = RESERVED.get(t.value, "NAME")
    return t


def t_FCONST(t):
    r'((\d+)(\.\d+)(e(\+|-)?(\d+))? | (\d+)e(\+|-)?(\d+))([lL]|[fF])?'
    t.value = float(t.value)
    return t


def t_ICONST(t):
    r'\d+([uU]|[lL]|[uU][lL]|[lL][uU])?'
    t.value = int(t.value)
    return t


def t_SCONST(t):
    r'(\\.)+?'
    t.value = t.value
    return t


def t_LPAREN(t):
    r'\('
    try:
        t.lexer.paren_count += 1
    except AttributeError:
        t.lexer.paren_count = 1
    return t


def t_RPAREN(t):
    r'\)'
    t.lexer.paren_count -= 1
    return t


def t_error(t):
    raise RQLSyntaxError("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)


def p_toplevel(t):
    """
    toplevel : calls

    """
    if len(t[1]) == 1:
        t[0] = t[1][0]

    else:
        t[0] = {'name': 'and', 'args': t[1]}


def p_calls(t):
    """
    calls : call COMMA calls
          | call
    """
    if len(t) == 2:
        t[0] = [t[1]]

    else:
        t[0] = [t[1]] + t[3]


def p_op_eq(t):
    """
    call : NAME EQUALS const
    """
    t[0] = {'name': 'eq', 'args': [t[1], t[3]]}


def p_fiql_ops(t):
    """
    call : NAME EQUALS NAME EQUALS const
    """
    t[0] = {'name': t[3], 'args': [t[1], t[5]]}


def p_op_and(t):
    """
    call : arg AND arg
    """
    t[0] = {'name': 'and', 'args': [t[1], t[3]]}


def p_op_or(t):
    """
    call : arg OR arg
    """
    t[0] = {'name': 'or', 'args': [t[1], t[3]]}


def p_generic_call(t):
    """
    call : NAME LPAREN arglist RPAREN
         | NAME LPAREN RPAREN
    """
    if len(t) == 4:
        t[0] = {'name': t[1], 'args': []}
    else:
        t[0] = {'name': t[1], 'args': t[3]}


def p_sort_call(t):
    """
    call : SORT LPAREN sort_arglist RPAREN

    """
    t[0] = {'name': 'sort', 'args': t[3]}


def p_argarray(t):
    """
    arg : LPAREN arglist RPAREN

    """
    t[0] = tuple(t[2])


def p_paren_arg(t):
    """
    arg : LPAREN arg RPAREN
    """
    t[0] = t[2]


def p_arglist(t):
    """
    arglist : arg COMMA arglist
            | arg
    """
    if len(t) == 2:
        t[0] = [t[1]]
    else:
        t[0] = [t[1]] + t[3]


def p_sort_arglist(t):
    """
    sort_arglist : sort_arg COMMA sort_arglist
                 | sort_arg
    """
    if len(t) == 2:
        t[0] = [t[1]]
    else:
        t[0] = [t[1]] + t[3]


def p_sort_arg(t):
    """
    sort_arg : sort_prefix arg
             | arg
    """
    if len(t) == 2:
        t[0] = t[1]

    else:
        t[0] = (t[1], t[2])


def p_sort_prefix(t):
    """
    sort_prefix : PLUS
                | MINUS
    """
    t[0] = t[1]


def p_arg(t):
    """
    arg : const
        | call
    """

    t[0] = t[1]


def p_true(t):
    """
    const : BOOL_TRUE

    """
    t[0] = True


def p_false(t):
    """
    const : BOOL_FALSE

    """
    t[0] = False


def p_null(t):
    """
    const : NULL

    """
    t[0] = None


def p_const(t):
    """
    const : NAME
          | ICONST
          | FCONST
    """
    t[0] = t[1]


def p_error(p):
    raise RQLSyntaxError("Syntax error at '%s'" % p.value)


lex.lex()

parser = yacc.yacc()
