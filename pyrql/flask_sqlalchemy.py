# -*- coding: utf-8 -*-

import operator
from functools import reduce

from sqlalchemy import and_
from sqlalchemy import or_, not_

from .parser import parser, RQLSyntaxError

from werkzeug.exceptions import BadRequest


class RQLQueryMixIn:

    def rql(self, expr):
        if not expr:
            return self

        if len(self._entities) > 1:
            raise NotImplementedError("query must have a single entity for now")

        try:
            root = parser.parse(expr)
        except RQLSyntaxError as exc:
            raise BadRequest("RQL Syntax error: %s" % exc.args)

        self._rql_select_clause = None
        self._rql_where_clause = None
        self._rql_order_by_clause = None
        self._rql_limit_clause = None
        self._rql_offset_clause = None

        self._rql_walk(root)

        query = self

        if self._rql_where_clause is not None:
            query = query.filter(self._rql_where_clause)

        if self._rql_limit_clause is not None:
            query = query.limit(self._rql_limit_clause)

        if self._rql_offset_clause is not None:
            query = query.offset(self._rql_offset_clause)

        if self._rql_order_by_clause is not None:
            query = query.order_by(*self._rql_order_by_clause)

        return query

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
                raise NotImplementedError(name)

            return method(args)

        elif isinstance(node, list):
            raise NotImplementedError

        elif isinstance(node, tuple):
            raise NotImplementedError

        return node

    def _rql_attr(self, attr):
        if isinstance(attr, str):
            model = self._entities[0].type
            try:
                column = getattr(model, attr)
            except AttributeError as exc:
                raise BadRequest("Invalid query attribute: %s" % attr)

        return column

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
        expr = reduce(and_, args)

        return expr

    def _rql_or(self, args):
        args = [self._rql_apply(node) for node in args]
        args = [a for a in args if a is not None]
        expr = reduce(or_, args)

        return expr

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

    def _rql_count(self, args):
        self._rql_count_clause = True
