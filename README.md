# pyrql

[![Build Status](https://travis-ci.org/pjwerneck/pyrql.svg?branch=develop)](https://travis-ci.org/pjwerneck/pyrql)

Resource Query Language (RQL) is a query language designed for use in URIs, with object-style data structures. This library is a Python parser that produces output identical to the JavaScript Library available at [https://github.com/persvr/rql](https://github.com/persvr/rql).


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

Types can be explicitly specified using a colon:

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

The slash syntax for arrays is not implemented and will result in a syntax error. The only valid array syntax is the comma delimited list inside parenthesis:

```
>>> pyrql.parse('(a,b)=1')
{'args': [('a', 'b'), 1], 'name': 'eq'}
```
