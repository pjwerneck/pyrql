# -*- coding: utf-8 -*-

import operator
import statistics
from collections import defaultdict
from copy import copy
from copy import deepcopy
from urllib.parse import unquote

from .exceptions import RQLQueryError
from .parser import Parser


class NodeMeta(type):
    nodes = {}

    def __init__(cls, name, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        if not (name.endswith("Node") or name.startswith("_")):
            NodeMeta.nodes[getattr(cls, "name", name.lower())] = cls


class Node(metaclass=NodeMeta):
    def __init__(self, *args):
        self.args = args

    @classmethod
    def get_subnode(cls, name):
        try:
            return NodeMeta.nodes[name]
        except KeyError:
            raise RQLQueryError("Invalid query function: %s" % name)


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


class _Filter(RowNode):
    name = None

    def __init__(self, key, value):
        self.key = Key(key)
        self.value = value
        self.op = getattr(operator, self.name)

    def __call__(self, row):
        if isinstance(self.value, Key):
            value = self.value(row)
        else:
            value = self.value

        return self.op(self.key(row), value)


class EqualTo(_Filter):
    name = "eq"


class NotEqualTo(_Filter):
    name = "ne"


class LessThan(_Filter):
    name = "lt"


class LessOrEqual(_Filter):
    name = "le"


class GreaterThan(_Filter):
    name = "gt"


class GreaterOrEqual(_Filter):
    name = "ge"


class And(RowNode):
    def __call__(self, row):
        return all([f(row) for f in self.args if f is not None])


class Or(RowNode):
    def __call__(self, row):
        return any([f(row) for f in self.args if f is not None])


class In(RowNode):
    def __call__(self, row):
        key, value = self.args
        key = Key(key)
        return operator.contains(value, key(row))


class Out(RowNode):
    def __call__(self, row):
        key, value = self.args
        key = Key(key)
        return operator.not_(operator.contains(value, key(row)))


class Contains(RowNode):
    def __call__(self, row):
        key, value = self.args
        key = Key(key)
        return operator.contains(key(row), value)


class Excludes(RowNode):
    def __call__(self, row):
        key, value = self.args
        key = Key(key)
        return operator.not_(operator.contains(key(row), value))


class AggregateNode(DataNode):
    def __init__(self, key):
        self.key = Key(key)

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
        keys = [Key(arg) for arg in self.args]
        return [{str(key): key(row) for key in keys} for row in data]


class Values(DataNode):
    def __init__(self, *args):
        if len(args) > 1:
            raise RQLQueryError("values() must have a single key argument")
        self.key = Key(args[0])

    def __call__(self, data):
        return [self.key(row) for row in data]


class Aggregate(DataNode):
    def __init__(self, key, *aggrs):
        self.key = Key(key)
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
    def __init__(self, *args):
        if len(args) > 1:
            raise RQLQueryError("unwind() must have a single key argument")
        self.key = Key(args[0])

    def __call__(self, data):
        data = [{**row, str(self.key): item} for row in data for item in self.key(row)]
        return data


class Limit(DataNode):
    def __call__(self, data):
        limit, offset = self.args

        if offset:
            data = data[offset:]

        if limit and limit != float("inf"):
            data = data[:limit]

        return data


class Index(DataNode):
    def __call__(self, data):
        return data[self.args[0]]


class Slice(DataNode):
    def __call__(self, data):
        return data[slice(*self.args)]


class First(DataNode):
    def __call__(self, data):
        return data[:1]


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
    def __init__(self, *args):
        self.args = [("+", v) if isinstance(v, str) else v for v in args]

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

    def query(self, expr, ignore_top_eq=None):
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

            # if we were asked to ignore any top level eq nodes,
            # remove them
            if ignore_top_eq:
                new.rql_parsed["args"] = [
                    arg
                    for arg in new.rql_parsed["args"]
                    if not (arg["name"] == "eq" and arg["args"][0] in ignore_top_eq)
                ]

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
                raise RQLQueryError(f"{exc.__class__.__name__} executing node {node}: {exc}")

        # if there's a default limit and no limit clause was added,
        # add one and feed the data through it
        if self._default_limit and self._limit_clause is None:
            data = Limit(self._default_limit, 0).feed(data)

        return data

    def _apply(self, token):
        if not isinstance(token, dict):
            return token

        name = token["name"]
        node_class = Node.get_subnode(name)

        args = [self._apply(arg) for arg in token["args"]]
        kwargs = {}

        # if node is Limit, apply limit constraints
        if node_class == Limit:
            limit = min(args[0] or float("inf"), self._max_limit or float("inf"))
            try:
                offset = args[1]
            except IndexError:
                offset = 0
            args = (limit, offset)

            self._limit_clause = True

        node = node_class(*args, **kwargs)

        return node
