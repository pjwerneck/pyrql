# pyrql

[![Build Status](https://travis-ci.org/pjwerneck/pyrql.svg?branch=develop)](https://travis-ci.org/pjwerneck/pyrql)


## Overview

Resource Query Language (RQL) is a query language designed for use in URIs, with object-style data structures.

This library provides a Python parser that produces output identical to the [JavaScript Library](https://github.com/persvr/rql), and a query engine that can perform RQL queries on lists of dictionaries.

## Installing

```
pip install pyrql
```


## RQL Syntax

The RQL syntax is a compatible superset of the standard HTML form URL encoding. Simple queries can be written in standard HTML form URL encoding, but more complex queries can be written in a URL friendly query string, using a set of nested operators. For example, querying for a property `foo` with the value of `3` could be written as:

```
eq(foo,3)
```

Or in standard HTML form URL encoding:

```
foo=3
```

Both expressions result in the exact same parsed value:

```
{'name': 'eq', 'args': ['foo', 3]}
```


### Typed Values

The following types are available:

- string
- number
- boolean
- null
- epoch
- date
- datetime
- uuid
- decimal

Numbers, booleans and null are converted automatically to the corresponding Python types. Numbers are converted to float or integer accordingly:

```
>>> pyrql.parse('ten=10')
{'name': 'eq', 'args': ['ten', 10]}
>>> pyrql.parse('pi=3.14')
{'name': 'eq', 'args': ['pi', 3.14]}
>>> pyrql.parse('mil=1e6')
{'name': 'eq', 'args': ['mil', 1000000.0]}
```

Booleans and null are converted to booleans and None:

```
>>> pyrql.parse('a=true')
{'name': 'eq', 'args': ['a', True]}
>>> pyrql.parse('a=false')
{'name': 'eq', 'args': ['a', False]}
>>> pyrql.parse('a=null')
{'name': 'eq', 'args': ['a', None]}
```

Types can be used explicitly in the form `type:value`:

```
>>> pyrql.parse('a=string:1')
{'name': 'eq', 'args': ['a', '1']}

```

### URL encoding

The parser automatically unquotes strings with percent-encoding, but it also accepts characters that would require encoding if submitted on an URI.

```
>>> pyrql.parse('eq(foo,lero lero)')
{'name': 'eq', 'args': ['foo', 'lero lero']}
>>> pyrql.parse('eq(foo,lero%20lero)')
{'name': 'eq', 'args': ['foo', 'lero lero']}
```

If that's undesirable, you should verify the URL before calling the parser.


### Limitations

The pyrql parser doesn't implement a few redundant details of the RQL syntax, either because the standard isn't clear on what's allowed, or the functionality is already available in a clearer syntax.

The only operator allowed at the query top level is the AND operator, i.e. `&`. A toplevel `or` operation using the `|` operator must be enclosed in parenthesis.

```
>>> pyrql.parse('(a=1|b=2)')
{'args': [{'args': ['a', 1], 'name': 'eq'}, {'args': ['b', 2], 'name': 'eq'}], 'name': 'or'}
```

The slash syntax for arrays is not implemented yet and will result in a syntax error. The only valid array syntax is the comma delimited list inside parenthesis:

```
>>> pyrql.parse('(a,b)=1')
{'args': [('a', 'b'), 1], 'name': 'eq'}
```
## Query Engine

The main use case for the query engine is to allow API clients to perform server-side filtering on large responses on their own. It's an easy drop-in improvement when you want to provide simple querying capabilities on an existing API endpoint without exposing your storage, or reimplementing everything in a more complete querying solution like GraphQL.

The data is fed through the operators in the query from left to right, as a pipeline, where the results of each top-level operator are fed to the next. If you're familiar with MongoDB aggregation pipelines, the query engine follows a similar concept, where each step transforms the current state of the data before being fed to the next step.

The operators can be categorized in three types:

- Filtering operators, which filter the data, like comparison and membership operators.
- Transforming operators, which transform all the data at once, like `select`, `sort` and `aggregate`.
- Aggregation operators, which reduce all data to a single value, like `sum` and `min`.

See the reference below for all operators and the equivalent Python code.

### Example

For example, if you have a Flask API with an endpoint exposing tasks, like this:

```python
@app.route('/api/v1/tasks')
def get_user_tasks():
    tasks = [task.to_dict() for task in Task.get_all()]
    return jsonify(tasks)
```
Adding pyrql query support is straightforward:

```python
from pyrql import Query
from urllib.parse import unquote

@app.route('/api/v1/tasks')
def get_user_tasks():
    tasks = [task.to_dict() for task in Task.get_all()]

    query_string = unquote(request.query_string.decode(request.charset))
    query = Query(tasks).query(query_string)

    return jsonify(query.all())
```

And now the endpoint supports the RQL syntax. For sake of example, let's consider a typical tasks response is similar to the following:

```json
[
    {
    "status": "PENDING",
    "name": "Update mobile app",
    "due_date": "2022-02-01T15:00:00",
    "completed_date": null,
    "tags": ["development", "easy"],
    "assigned_to": null,
    "hours_budgeted": 4,
    "hours_spent": 0
    },
    {
    "status": "COMPLETED",
    "name": "Design new frontend",
    "due_date": "2022-01-28T14:00:00",
    "completed_date": "2022-01-27T12:17:00"
    "tags": ["design", "medium"],
    "assigned_to": "Bill",
    "hours_budgeted": 8,
    "hours_spent": 6
    },
    ...
]
```

If an API client wants to retrieve only tasks in the `PENDING` status, the simple equality comparison is supported with standard query strings:

```http
GET /api/v1/asks?state=PENDING
```
Or with the RQL syntax:

```http
GET /api/v1/tasks?eq(state,PENDING)
```

Let's say the client wants tasks in the `PENDING` state which contain the `easy` tag:

```http
GET /api/v1/tasks?eq(state,PENDING)&contains(tags,easy)
```

It can also perform simple aggregations, like adding up all hours spent by completed tasks, for each assigned user:

```http
GET /api/v1/tasks?eq(state,COMPLETED)&ne(assigned_user,null)&aggregate(assigned_to,sum(hours_spent))
```

### Reference Table


| RQL                                  | Python equivalent                                      | Obs.                                   |
| ------------------------------------ |:------------------------------------------------------ |:-------------------------------------- |
| FILTERING                            |                                                        |                                        |
| `eq(key,value)`                      | `[row for row in data if row[key] == value] `          |                                        |
| `ne(key,value)`                      | `[row for row in data if row[key] != value]`           |                                        |
| `lt(key,value)`                      | `[row for row in data if row[key] < value]`            |                                        |
| `le(key,value)`                      | `[row for row in data if row[key] <= value]`           |                                        |
| `gt(key,value)`                      | `[row for row in data if row[key] > value]`            |                                        |
| `ge(key,value)`                      | `[row for row in data if row[key] >= value]`           |                                        |
| `in(key,value)`                      | `[row for row in data if row[key] in value]`           |                                        |
| `out(key,value)`                     | `[row for row in data if row[key] not in value]`       |                                        |
| `contains(key,value)`                | `[row for row in data if value in row[key]]`           |                                        |
| `excludes(key,value)`                | `[row for row in data if value not in row[key]]`       |                                        |
| `and(expr1,expr2,...)`               | `[row for row in data if expr1 and expr2]`             |                                        |
| `or(expr1,expr2,...)`                | `[row for row in data if expr1 or expr2]`              |                                        |
| TRANSFORMING                         |                                                        |                                        |
|                                      |                                                        |                                        |
| `select(a,b,c,...)`                  | `[{a: row[a], b: row[b], c: row[c]} for row in data]`  |                                        |
| `values(a)`                          | `[row[a] for row in data]`                             |                                        |
| `limit(count,start?)`                | `data[start:count]`                                    |                                        |
| `sort(key)`                          | `sorted(data, key=lambda row: row[key])`               |                                        |
| `sort(-key)`                         | `sorted(data, key=lambda row: row[key], reverse=True)` |                                        |
| `distinct()`                         | `list(set(data))`                                      | Unlike `set`, RQL preserves order.     |
| `first()`                            | `data[0]`                                              |                                        |
| `one()`                              | `data[0]`                                              | Raises RQLQueryError if len(data) != 1 |
| `aggregate(key,agg1(a),agg2(b),...)` | See below                                              |                                        |
| AGGREGATION                          |                                                        |                                        |
| `sum(key)`                           | `sum([row[key] for row in data])`                      |                                        |
| `mean(key)`                          | `statistics.mean([row[key] for row in data])`          |                                        |
| `max(key)`                           | `max([row[key] for row in data])`                      |                                        |
| `min(key)`                           | `min([row[key] for row in data])`                      |                                        |
| `count()`                            | `len(data)`                                            |                                        |


The `aggregate` operator can't be summarized in a readable one-liner. It accepts a key, and any number of aggregation operators. All the data is grouped by the key value, aggregated by each aggregation operator, and a new list is built with the results and key value.
