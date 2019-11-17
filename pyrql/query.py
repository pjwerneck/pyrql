# -*- coding: utf-8 -*-


import datetime
import operator
from collections import namedtuple, OrderedDict
from copy import deepcopy
from urllib.parse import unquote

from .exceptions import RQLQueryError
from .exceptions import RQLSyntaxError
from .parser import Parser


class Filter:
    def __init__(self, op, args):
        self.op = getattr(operator, op)
        self.key = args[0]
        self.value = args[1]

        self.row = None

    def __call__(self, row):
        self.row = row
        return self

    def __bool__(self):
        return self.op(self.row[self.key], self.value)


class And:
    def __init__(self, *args):
        self.args = args

    def __call__(self, row):
        self.row = row
        return self

    def __bool__(self):
        return all([f(self.row) for f in self.args if f is not None])


class Or:
    def __init__(self, *args):
        self.args = args

    def __call__(self, row):
        self.row = row
        return self

    def __bool__(self):
        return any([f(self.row) for f in self.args if f is not None])


class In:
    def __init__(self, attr, value):
        self.attr = attr
        self.value = value

    def __call__(self, row):
        self.row = row
        return self

    def __bool__(self):
        return operator.contains(self.value, self.row[self.attr])


class NotIn:
    def __init__(self, attr, value):
        self.attr = attr
        self.value = value

    def __call__(self, row):
        self.row = row
        return self

    def __bool__(self):
        return operator.not_(operator.contains(self.value, self.row[self.attr]))


class Contains:
    def __init__(self, attr, value):
        self.attr = attr
        self.value = value

    def __call__(self, row):
        self.row = row
        return self

    def __bool__(self):
        return operator.contains(self.row[self.attr], self.value)


class Excludes:
    def __init__(self, attr, value):
        self.attr = attr
        self.value = value

    def __call__(self, row):
        self.row = row
        return self

    def __bool__(self):
        return operator.not_(operator.contains(self.row[self.attr], self.value))


class Min:
    def __init__(self, attr):
        self.attr = attr

    def __call__(self, data):
        return min([row[self.attr] for row in data])


class Max:
    def __init__(self, attr):
        self.attr = attr

    def __call__(self, data):
        return max([row[self.attr] for row in data])


class Sum:
    def __init__(self, attr):
        self.attr = attr

    def __call__(self, data):
        return sum([row[self.attr] for row in data])


class Mean:
    def __init__(self, attr):
        self.attr = attr

    def __call__(self, data):
        return sum([row[self.attr] for row in data]) / len(data)


class Select:
    def __init__(self, attrs):
        self.attrs = attrs

    def __call__(self, data):
        # apply the select clause
        return [{k: row[k] for k in self.attrs} for row in data]


class Values:
    def __init__(self, attrs):
        self.attrs = attrs

    def __call__(self, data):
        return [row[self.attrs] for row in data]


class Aggregate:
    def __init__(self, group_by, attrs):
        self.group_by = group_by[0]
        self.attrs = attrs

    def __call__(self, data):

        groups = OrderedDict()
        for row in data:
            try:
                groups[row[self.group_by]].append(row)
            except KeyError:
                groups[row[self.group_by]] = [row]

        out = []

        for group_key, rows in groups.items():
            outrow = {}
            for attr in self.attrs:
                if isinstance(attr, str):
                    outrow[attr] = rows[0][attr]
                else:
                    outrow[attr.attr] = attr(rows)

            out.append(outrow)

        return out






        import pdb; pdb.set_trace()





def Count(data):
    return len(data)


def One(data):
    if len(data) > 1:
        raise ValueError("Multiple results found for 'one'")

    if len(data) == 0:
        raise ValueError("No results found for 'one'")

    return data


class Query:

    _rql_max_limit = None
    _rql_default_limit = None
    _rql_auto_scalar = False

    def query(self, expr, data):
        if not expr:
            self.rql_parsed = None
            self.rql_expr = ""

        else:
            self.rql_expr = expr = unquote(expr)
            self.rql_parsed = Parser().parse(expr)

        data = deepcopy(data)

        self._rql_select_stack = []
        self._rql_where_clause = None
        self._rql_sort_clause = None
        self._rql_limit_stack = []
        self._rql_offset_stack = []
        self._rql_select_clause = []
        self._rql_values_clause = None
        self._rql_scalar_clause = None
        self._rql_where_clause = None
        self._rql_order_by_clause = None
        self._rql_one_clause = None
        self._rql_distinct_clause = None
        self._rql_group_by_clause = None
        self._rql_joins = []

        self._rql_walk(self.rql_parsed)

        # first, let's filter the data
        if self._rql_where_clause is not None:
            data = [row for row in data if bool(self._rql_where_clause.__call__(row))]

        if self._rql_scalar_clause:
            data = self._rql_scalar_clause(data)

        # then order the data
        if self._rql_sort_clause is not None:
            # sort by the least significant first.
            for op in reversed(self._rql_sort_clause):
                data.sort(**op)

        # apply distinct clause
        if self._rql_distinct_clause:
            new_data = []
            for row in data:
                if row not in new_data:
                    new_data.append(row)
            data = new_data

        # apply any offset
        if self._rql_offset_stack:
            offset = self._rql_offset_stack[-1]
            data = data[offset:]

        # then apply any limit
        if self._rql_limit_stack:
            limit = self._rql_limit_stack[-1]
            data = data[:limit]

        return data

    def _rql_walk(self, node):
        if node:
            self._rql_where_clause = self._rql_apply(node)

    def _rql_apply(self, node):
        if isinstance(node, dict):
            name = node["name"]
            args = node["args"]

            if name in {"eq", "ne", "lt", "le", "gt", "ge"}:
                return self._rql_cmp(name, args)

            try:
                method = getattr(self, "_rql_" + name)
            except AttributeError:
                raise RQLQueryError("Invalid query function: %s" % name)

            return method(args)

        elif isinstance(node, list):
            raise NotImplementedError

        elif isinstance(node, tuple):
            raise NotImplementedError

        return node

    def _rql_cmp(self, name, args):
        attr, value = args

        attr = self._rql_attr(attr)
        value = self._rql_value(value, attr)

        return Filter(name, (attr, value))

    def _rql_value(self, value, attr=None):
        if isinstance(value, dict):
            value = self._rql_apply(value)

        return value

    def _rql_attr(self, attr):
        if isinstance(attr, str):
            return attr

        elif isinstance(attr, tuple):
            raise NotImplementedError

        raise NotImplementedError

    def _rql_and(self, args):
        args = [self._rql_apply(a) for a in args]

        return And(*args)

    def _rql_or(self, args):
        args = [self._rql_apply(a) for a in args]

        return Or(*args)

    def _rql_in(self, args):
        attr, value = args

        attr = self._rql_attr(attr)
        value = self._rql_value(value, attr)

        return In(attr, value)

    def _rql_out(self, args):
        attr, value = args

        attr = self._rql_attr(attr)
        value = self._rql_value(value, attr)

        return NotIn(attr, value)

    def _rql_limit(self, args):
        args = [self._rql_value(v) for v in args]

        self._rql_limit_stack.append(min(args[0], self._rql_max_limit or float("inf")))

        if len(args) == 2:
            self._rql_offset_stack.append(args[1])

    def _rql_sort(self, args):
        clause = []

        args = [("+", v) if isinstance(v, str) else v for v in args]

        for prefix, attr in args:
            clause.append({"key": operator.itemgetter(attr), "reverse": prefix == "-"})

        self._rql_sort_clause = clause

    def _rql_contains(self, args):
        attr, value = args
        attr = self._rql_attr(attr)
        value = self._rql_value(value, attr)

        return Contains(attr, value)

    def _rql_excludes(self, args):
        attr, value = args
        attr = self._rql_attr(attr)
        value = self._rql_value(value, attr)

        return Excludes(attr, value)

    def _rql_select(self, args):
        attrs = [self._rql_attr(attr) for attr in args]
        self._rql_scalar_clause = Select(attrs)

    def _rql_values(self, args):
        (attr,) = args
        attr = self._rql_attr(attr)
        self._rql_scalar_clause = Values(attr)

    def _rql_distinct(self, args):
        self._rql_distinct_clause = True

    def _rql_count(self, args):
        self._rql_scalar_clause = Count

    def _rql_min(self, args):
        self._rql_scalar_clause = Min(args[0])

    def _rql_max(self, args):
        self._rql_scalar_clause = Max(args[0])

    def _rql_sum(self, args):
        self._rql_scalar_clause = Sum(args[0])

    def _rql_mean(self, args):
        self._rql_scalar_clause = Mean(args[0])

    def _rql_first(self, args):
        self._rql_limit_stack.append(1)

    def _rql_one(self, args):
        self._rql_scalar_clause = One

    def _rql_time(self, args):
        return datetime.time(*args)

    def _rql_date(self, args):
        return datetime.date(*args)

    def _rql_dt(self, args):
        return datetime.datetime(*args)

    def _rql_aggregate(self, args):
        funcs = {'sum': Sum, 'min': Min, 'max': Max, 'mean': Mean, 'count': Count}

        attrs = []
        aggrs = []

        for x in args:
            if isinstance(x, dict):
                agg_func = funcs[x["name"]]
                agg_attr = self._rql_attr(x["args"][0])

                aggrs.append(agg_func(agg_attr))

            else:
                attrs.append(self._rql_attr(x))

        self._rql_scalar_clause = Aggregate(attrs, attrs + aggrs)
