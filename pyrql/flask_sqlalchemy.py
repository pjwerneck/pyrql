# -*- coding: utf-8 -*-

import operator
from functools import reduce

from sqlalchemy import and_
from sqlalchemy import or_, not_
from sqlalchemy.inspection import inspect
7
from .parser import parser, RQLSyntaxError
from .unparser import unparser

from werkzeug.exceptions import BadRequest
from urllib.parse import unquote

from copy import deepcopy


class RQLQueryMixIn:

    def rql(self, request):
        expr = request.query_string

        if not expr:
            self.rql_parsed = None
            self.rql_expr = None
            return self

        if type(expr) is bytes:
            expr = expr.decode(request.charset)

        self.rql_expr = expr = unquote(expr)

        if len(self._entities) > 1:
            raise NotImplementedError("query must have a single entity for now")

        try:
            self.rql_parsed = root = parser.parse(expr)
        except RQLSyntaxError as exc:
            raise BadRequest("RQL Syntax error: %s" % exc.args)

        self._rql_select_clause = None
        self._rql_where_clause = None
        self._rql_order_by_clause = None
        self._rql_limit_clause = None
        self._rql_offset_clause = None
        self._rql_joins = []

        self._rql_walk(root)

        query = self

        for other in self._rql_joins:
            query = query.join(other)

        if self._rql_where_clause is not None:
            query = query.filter(self._rql_where_clause)

        if self._rql_order_by_clause is not None:
            query = query.order_by(*self._rql_order_by_clause)

        if self._rql_limit_clause is not None:
            query = query.limit(self._rql_limit_clause)

        if self._rql_offset_clause is not None:
            query = query.offset(self._rql_offset_clause)


        return query

    def rql_expr_replace(self, replacement):
        parsed = deepcopy(self.rql_parsed)

        replaced = self._rql_traverse_and_replace(parsed, replacement['name'], replacement['args'])

        if not replaced:
            parsed = {'name': 'and', 'args': [replacement, parsed]}

        return unparser.unparse(parsed)

    def _rql_traverse_and_replace(self, root, name, args):
        if root['name'] == name:
            root['args'] = args
            return True

        else:
            for arg in root['args']:
                if isinstance(arg, dict):
                    if self._rql_traverse_and_replace(arg, name, args):
                        return True

        return False

    def _rql_walk(self, node):
        self._rql_where_clause = self._rql_apply(node)

    def _rql_apply(self, node):
        if isinstance(node, dict):
            name = node['name']
            args = node['args']

            if name in {'eq', 'ne', 'lt', 'le', 'gt', 'ge'}:
                return self._rql_cmp(args, getattr(operator, name))

            try:
                method = getattr(self, '_rql_' + name)
            except AttributeError:
                raise BadRequest("Invalid query function: %s" % name)

            return method(args)

        elif isinstance(node, list):
            raise NotImplementedError

        elif isinstance(node, tuple):
            raise NotImplementedError

        return node

    def _rql_attr(self, attr):
        model = self._entities[0].type
        if isinstance(attr, str):
            try:
                return getattr(model, attr)
            except AttributeError:
                raise BadRequest("Invalid query attribute: %s" % attr)

        elif isinstance(attr, tuple) and len(attr) == 2:
            relationships = inspect(model).relationships.keys()

            if attr[0] in relationships:
                rel = getattr(model, attr[0])
                submodel = rel.mapper.class_

                column = getattr(submodel, attr[1])
                self._rql_joins.append(rel)

                return column

        raise NotImplementedError

    def _rql_value(self, value):
        return value

    def _rql_cmp(self, args, op):
        attr, value = args

        attr = self._rql_attr(attr)
        value = self._rql_value(value)

        return op(attr, value)

    def _rql_and(self, args):
        args = [self._rql_apply(node) for node in args]
        args = [a for a in args if a is not None]
        if args:
            return reduce(and_, args)

    def _rql_or(self, args):
        args = [self._rql_apply(node) for node in args]
        args = [a for a in args if a is not None]
        if args:
            return reduce(or_, args)

    def _rql_in(self, args):
        attr, value = args

        attr = self._rql_attr(attr)
        value = self._rql_value(value)

        return attr.in_(value)

    def _rql_out(self, args):
        attr, value = args

        attr = self._rql_attr(attr)
        value = self._rql_value(value)

        return not_(attr.in_(value))

    def _rql_like(self, args):
        attr, value = args

        attr = self._rql_attr(attr)
        value = self._rql_value(value)
        value = value.replace('*', '%')

        return attr.like(value)

    def _rql_limit(self, args):
        args = [self._rql_value(v) for v in args]

        if len(args) == 1:
            self._rql_limit_clause = args[0]

        elif len(args) == 2:
            self._rql_limit_clause = args[0]
            self._rql_offset_clause = args[1]

    def _rql_sort(self, args):
        args = [('+', v) if isinstance(v, str) else v for v in args]
        args = [(p, self._rql_attr(v)) for (p, v) in args]

        attrs = [attr.desc() if p == '-' else attr for (p, attr) in args]

        self._rql_order_by_clause = attrs
