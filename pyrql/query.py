# -*- coding: utf-8 -*-

import datetime
import operator
import statistics
from collections import defaultdict
from copy import copy
from copy import deepcopy
from urllib.parse import unquote

from .exceptions import RQLQueryError
from .parser import Parser


class Node:
    def __init__(self, *args):
        self.args = args

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, self.args)


class RowNode(Node):
    def feed(self, data):
        return [row for row in data if self(row)]


class DataNode(Node):
    def feed(self, data):
        return self(data)


class Key(Node):
    def __init__(self, *args):
        self.args = []
        for arg in args:
            self.args.extend(arg.split("."))

    def __call__(self, row):
        value = row
        for key in self.args:
            value = value.get(key)

        return value

    def __str__(self):
        return ".".join(self.args)


class Filter(RowNode):
    def __init__(self, opname, key, value):
        self.opname = opname
        self.key = key
        self.value = value

        self.op = getattr(operator, opname)

    def __call__(self, row):
        if isinstance(self.value, Key):
            value = self.value(row)
        else:
            value = self.value

        return self.op(self.key(row), value)


class And(RowNode):
    def __call__(self, row):
        return all([f(row) for f in self.args if f is not None])


class Or(RowNode):
    def __call__(self, row):
        return any([f(row) for f in self.args if f is not None])


class In(RowNode):
    def __call__(self, row):
        key, value = self.args
        return operator.contains(value, key(row))


class NotIn(RowNode):
    def __call__(self, row):
        key, value = self.args
        return operator.not_(operator.contains(value, key(row)))


class Contains(RowNode):
    def __call__(self, row):
        key, value = self.args
        return operator.contains(key(row), value)


class Excludes(RowNode):
    def __call__(self, row):
        key, value = self.args
        return operator.not_(operator.contains(key(row), value))


class AggregateNode(DataNode):
    def __init__(self, key):
        self.key = key

    def __str__(self):
        return str(self.key)


class Min(AggregateNode):
    def __call__(self, data):
        return min([self.key(row) for row in data])


class Max(AggregateNode):
    def __call__(self, data):
        return max([self.key(row) for row in data])


class Sum(AggregateNode):
    def __call__(self, data):
        return sum([self.key(row) for row in data])


class Mean(AggregateNode):
    def __call__(self, data):
        return statistics.mean([self.key(row) for row in data])


class Select(DataNode):
    def __call__(self, data):
        return [{str(k): k(row) for k in self.args} for row in data]


class Values(DataNode):
    def __init__(self, key):
        self.key = key

    def __call__(self, data):
        return [self.key(row) for row in data]


class Aggregate(DataNode):
    def __init__(self, key, aggrs):
        self.key = key
        self.aggrs = aggrs

    def __call__(self, data):
        groups = defaultdict(list)
        for row in data:
            groups[self.key(row)].append(row)

        data = [
            {str(self.key): value, **{str(aggr): aggr(rows) for aggr in self.aggrs}}
            for (value, rows) in groups.items()
        ]
        return data


class Unwind(DataNode):
    def __init__(self, key):
        self.key = key

    def __call__(self, data):
        data = [{**row, str(self.key): item} for row in data for item in self.key(row)]
        return data


class Limit(DataNode):
    def __call__(self, data):
        limit, offset = self.args

        if offset:
            data = data[offset:]

        if limit:
            data = data[:limit]

        return data


class Count(DataNode):
    def __call__(self, data):
        return len(data)

    def __str__(self):
        return "count"


class Distinct(DataNode):
    def __call__(self, data):
        new_data = []

        for row in data:
            if row not in new_data:
                new_data.append(row)
        return new_data


class Sort(DataNode):
    def __call__(self, data):
        # sort least significant first
        if self.args:
            for prefix, key in reversed(self.args):
                data.sort(key=operator.itemgetter(key), reverse=prefix == "-")
        else:
            data.sort()

        return data


class One(DataNode):
    def __call__(self, data):
        if len(data) > 1:
            raise RQLQueryError("Multiple results found for 'one'")

        if len(data) == 0:
            raise RQLQueryError("No results found for 'one'")

        return data


class Query:
    def __init__(self, data, default_limit=None, max_limit=None):
        self.data = data

        self._default_limit = default_limit
        self._max_limit = max_limit
        self._limit_clause = None

        self.rql_parsed = None
        self.rql_expr = ""

        self.pipeline = []

    def query(self, expr):
        if not expr:
            return self

        new = copy(self)

        new.rql_expr = expr = unquote(expr)
        new.rql_parsed = Parser().parse(expr)

        # if there's a query, build the pipeline
        if new.rql_parsed:
            # if top-level node is not an 'and', make it so
            if new.rql_parsed["name"] != "and":
                new.rql_parsed = {"name": "and", "args": [new.rql_parsed]}

            try:
                new.pipeline.extend(new._apply(new.rql_parsed).args)
            except RQLQueryError:
                raise
            except Exception as exc:
                raise RQLQueryError(f"{exc.__class__.__name__} preparing pipeline: {exc.args}")

        return new

    def all(self):
        # deepcopy data so we can transform it at will
        data = deepcopy(self.data)

        # execute the pipeline
        for node in self.pipeline:
            try:
                data = node.feed(data)
            except RQLQueryError:
                raise
            except Exception as exc:
                raise RQLQueryError(f"{exc.__class__.__name__} executing node {node}: {exc.args}")

        # if there's a default limit and no limit clause was added,
        # feed it
        if self._default_limit and self._limit_clause is None:
            data = Limit(self._default_limit, 0).feed(data)

        return data

    def _apply(self, node):
        name = node["name"]
        args = node["args"]

        try:
            method = getattr(self, "_rql_" + name)
        except AttributeError:
            raise RQLQueryError("Invalid query function: %s" % name)

        return method(args)

    def _rql_eq(self, args):
        return self._rql_cmp("eq", args)

    def _rql_ne(self, args):
        return self._rql_cmp("ne", args)

    def _rql_lt(self, args):
        return self._rql_cmp("lt", args)

    def _rql_le(self, args):
        return self._rql_cmp("le", args)

    def _rql_gt(self, args):
        return self._rql_cmp("gt", args)

    def _rql_ge(self, args):
        return self._rql_cmp("ge", args)

    def _rql_cmp(self, name, args):
        strkey, value = args
        key = self._rql_key(strkey)
        value = self._rql_value(value)
        return Filter(name, key, value)

    def _rql_value(self, value):
        if isinstance(value, dict):
            value = self._apply(value)

        return value

    def _rql_key(self, args):
        if isinstance(args, str):
            return Key(args)
        else:
            return Key(*args)

    def _rql_and(self, args):
        args = [self._apply(a) for a in args]
        return And(*args)

    def _rql_or(self, args):
        args = [self._apply(a) for a in args]
        return Or(*args)

    def _rql_in(self, args):
        keystr, value = args

        key = self._rql_key(keystr)
        value = self._rql_value(value)

        return In(key, value)

    def _rql_out(self, args):
        keystr, value = args

        key = self._rql_key(keystr)
        value = self._rql_value(value)

        return NotIn(key, value)

    def _rql_limit(self, args):
        args = [self._rql_value(v) for v in args]

        limit = min(args[0] or float("inf"), self._max_limit or float("inf"))

        try:
            offset = args[1]
        except IndexError:
            offset = 0

        self._limit_clause = Limit(limit if limit != float("inf") else None, offset)
        return self._limit_clause

    def _rql_sort(self, args):
        args = [("+", v) if isinstance(v, str) else v for v in args]
        return Sort(*args)

    def _rql_contains(self, args):
        keystr, value = args
        key = self._rql_key(keystr)
        value = self._rql_value(value)

        return Contains(key, value)

    def _rql_excludes(self, args):
        keystr, value = args
        key = self._rql_key(keystr)
        value = self._rql_value(value)

        return Excludes(key, value)

    def _rql_select(self, args):
        keys = [self._rql_key(keystr) for keystr in args]
        return Select(*keys)

    def _rql_values(self, args):
        key = self._rql_key(args)
        return Values(key)

    def _rql_distinct(self, args):
        return Distinct()

    def _rql_count(self, args):
        return Count()

    def _rql_min(self, args):
        return Min(self._rql_key(args))

    def _rql_max(self, args):
        return Max(self._rql_key(args))

    def _rql_sum(self, args):
        return Sum(self._rql_key(args))

    def _rql_mean(self, args):
        return Mean(self._rql_key(args))

    def _rql_first(self, args):
        return Limit(1, 0)

    def _rql_one(self, args):
        return One()

    def _rql_time(self, args):
        return datetime.time(*args)

    def _rql_date(self, args):
        return datetime.date(*args)

    def _rql_dt(self, args):
        return datetime.datetime(*args)

    def _rql_aggregate(self, args):
        funcs = {"sum": Sum, "min": Min, "max": Max, "mean": Mean, "count": Count}

        group_by = self._rql_key(args[0])
        fields = args[1:]

        aggrs = []

        for f in fields:
            agg_func = funcs[f["name"]]
            agg_key = self._rql_key(*f["args"]) if f["args"] else None

            aggrs.append(agg_func(agg_key))

        return Aggregate(group_by, aggrs)

    def _rql_unwind(self, args):
        key = self._rql_key(args[0])
        return Unwind(key)
