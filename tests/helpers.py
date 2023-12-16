import datetime
import decimal
import uuid
from typing import Any

from hypothesis import strategies as st
from hypothesis.extra.dateutil import timezones as st_timezones

CMP_OPS = ["eq", "lt", "le", "gt", "ge", "ne"]


def py2rql(value: Any) -> str:
    """Convert a Python value to a RQL literal."""
    if isinstance(value, (list, tuple)):
        return "(" + ",".join(map(py2rql, value)) + ")"

    if value is None:
        return "null"

    elif isinstance(value, bool):
        return str(value).lower()

    elif isinstance(value, decimal.Decimal):
        return "decimal:%s" % value

    elif isinstance(value, float):
        # repr(float) returns the shortest decimal representation
        # for the same binary float
        return repr(value)

    elif isinstance(value, uuid.UUID):
        return "uuid:%s" % value.hex

    elif isinstance(value, datetime.datetime):
        return "datetime:%s" % value.isoformat()

    elif isinstance(value, datetime.date):
        return "date:%s" % value.isoformat()

    return str(value)


rql_names = st.from_regex(r"^[a-zA-Z][a-zA-Z0-9_]+$", fullmatch=True)

rql_cmp_ops = st.sampled_from(CMP_OPS)

rql_member_ops = st.sampled_from(["in", "out", "contains", "excludes"])

py_strings = st.text(
    min_size=1,
    alphabet=st.characters(
        # rql reserved characters
        blacklist_characters=tuple("$@!*+-=:()"),
        whitelist_categories=("Ll", "Lu", "Nd"),
    ),
    # filter out numbers, strings that start with a number, and reserved words
).filter(lambda x: not (x.isdigit() or x[0].isdigit() or x in {"true", "false", "null"}))

rql_typed_strings = st.text(
    min_size=1,
    alphabet=st.characters(
        # rql reserved characters
        blacklist_characters=tuple("$@!*+-=:()"),
        whitelist_categories=("Ll", "Lu", "Nd"),
    ),
).map(lambda x: f"string:{x}")

py_numbers = st.one_of(st.integers(), st.floats(allow_infinity=False, allow_nan=False))

py_dates = st.dates()

# reject tz-aware datetimes that have a timezone offset with more than 5
# digits (not ISO 8601 compliant)
py_datetimes = st.datetimes(timezones=st_timezones()).filter(lambda x: len(x.strftime("%z")) <= 5)

py_naive_datetimes = st.datetimes()

py_booleans = st.booleans()

py_uuids = st.uuids()

py_decimals = st.decimals(allow_nan=False, allow_infinity=False)


py_values = st.one_of(
    st.none(),
    py_strings,
    py_numbers,
    py_dates,
    py_datetimes,
    py_naive_datetimes,
    py_booleans,
    py_uuids,
    py_decimals,
)

# epoch timestamps are always UTC, with microseconds removed
epoch_pairs = (
    st.datetimes(timezones=st_timezones())
    .map(lambda dt: dt.replace(microsecond=0).astimezone(datetime.timezone.utc))
    .map(lambda dt: (dt, f"epoch:{dt.timestamp()}"))
)

value_pairs = st.one_of(
    py_values.map(lambda x: (x, py2rql(x))),
    epoch_pairs,
)

array_values = st.lists(py_values, min_size=1).map(lambda x: tuple(x))

array_pairs = array_values.map(lambda x: (x, py2rql(x)))


py_single_attributes = st.from_regex(r"^[a-zA-Z][a-zA-Z0-9_]*$", fullmatch=True)

py_composite_attributes = st.lists(py_single_attributes, min_size=1).map(lambda x: tuple(x))

py_attributes = st.one_of(py_single_attributes, py_composite_attributes)

# pairs a parsed tuple of strings with a RQL string array
attribute_pairs = py_attributes.map(
    lambda x: (x, f"({','.join(x)})" if isinstance(x, tuple) else x)
)


# sort attributes are optionally prefixed with a + or - sign
py_sort_attributes = st.one_of(
    py_attributes,
    st.tuples(st.sampled_from(("+", "-")), py_attributes),
)


def map_sort_attr(x):
    # if it's not a tuple, use the same value
    if not isinstance(x, tuple):
        return (x, x)

    # if it's a tuple, it can have a + or - prefix
    if x[0] in "-+":
        prefix = x[0]
        v = x[1]

        # if the value is a tuple, it's a composite attribute
        if isinstance(v, tuple):
            v = f"({','.join(v)})"

        return (x, f"{prefix}{v}")

    # if it's a tuple but doesn't have a prefix, it's just a composite attribute
    return (x, f"({','.join(x)})")


sort_attribute_pairs = py_sort_attributes.map(map_sort_attr)
