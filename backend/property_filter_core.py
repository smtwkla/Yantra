"""The equipment list's property filter — pure rules (no DB, no Flask)
(docs/steps/S062-property-filter/1-brief.md § 5).

A filter is lines of *property, operator, value*, all of which (``match`` "all") or any of which
("any") a node must meet.  It travels as one JSON value, ``props``, in the screen's URL and the
API's query (§ 5.1).  Three steps, so the shell can load the properties named between them:

1. ``read_property_filter(raw)``: the JSON's shape (checks 1–3) and the property ids it names;
2. ``check_property_filter(parsed, properties, options)``: each line against its property
   (checks 4–6), giving the clean filter;
3. ``filter_condition(filter, like)``: one SQL condition and its parameters for the list's WHERE.

ISO 27001 A.8.28 (secure coding): every value from the request is an SQL parameter; the column
names and the operators' SQL come only from the fixed tables below (§ 5.4).
"""

import json

from properties_core import (
    CHOICE, CHOOSE_OPTION, CHOOSE_YES_NO, ENTER_NUMBER, ENTER_TEXT, GEO, GEO_COLUMNS, GEO_LEVEL, NUMBER, TEXT,
    TEXT_TOO_LONG, TEXT_VALUE_MAX, VALUE_COLUMNS, YES_NO, parse_value,
)

MAX_RULES = 10
MAX_PROPS_LENGTH = 4000    # characters of the raw value, so a URL stays a URL

MATCH_ALL = "all"
MATCH_ANY = "any"
MATCHES = (MATCH_ALL, MATCH_ANY)

# Messages (scope B, § 5.2); the value messages are properties_core's where one exists
UNREADABLE = "The property filter cannot be read. Clear it and make it again."
TOO_MANY_RULES = f"Use {MAX_RULES} conditions or fewer"
PROPERTY_NOT_IN_USE = "This property is no longer in use. Remove its condition."
CHOOSE_OPERATOR = "Choose an operator from the list"
ENTER_TWO_NUMBERS = "Enter two numbers"
SMALLER_FIRST = "Enter the smaller number first"
CHOOSE_AT_LEAST_ONE = "Choose at least one option"

HAS = "has"
NONE = "none"
BETWEEN = "between"
IN = "in"
NOT_IN = "not_in"
CONTAINS = "contains"

# The operators each data type takes, in the dialog's order (§ 5.2); has / none take no value.
# A Location takes only has / none: no search by distance (S061 out of scope).
_COMPARE = ("eq", "ne", "lt", "le", "gt", "ge")
OPERATORS = {
    NUMBER: (*_COMPARE, BETWEEN, HAS, NONE),
    CHOICE: (IN, NOT_IN, HAS, NONE),
    TEXT: (CONTAINS, "eq", HAS, NONE),
    YES_NO: ("eq", HAS, NONE),
    GEO: (HAS, NONE),
}

# The value column of each data type (properties_core.VALUE_COLUMNS has no Location: a location
# has two columns, and its latitude alone says whether a value exists, BS1-01)
_COLUMNS = {**VALUE_COLUMNS, GEO: GEO_COLUMNS[0]}

# An operator's SQL after the value expression; the placeholders are filled by the parameters only
_COMPARE_SQL = {"eq": "= %s", "ne": "<> %s", "lt": "< %s", "le": "<= %s", "gt": "> %s", "ge": ">= %s"}


def _is_whole_number(value):
    """A positive whole number; a boolean is not one here (True is an int in Python)."""
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


# ---------------------------------------------------------------------------
# 1. The shape (checks 1–3)
# ---------------------------------------------------------------------------

def read_property_filter(raw):
    """The raw ``props`` text -> ``(parsed, None)`` or ``(None, (field, message))``.

    ``parsed``: ``{match, rules, property_ids}``, the rules as sent and the sorted set of the
    property ids they name.  A missing or empty ``props`` is no filter: no rules, no ids."""
    if not raw:
        return {"match": MATCH_ALL, "rules": [], "property_ids": []}, None
    unreadable = (None, ("props", UNREADABLE))
    if len(raw) > MAX_PROPS_LENGTH:
        return unreadable
    try:
        data = json.loads(raw)
    except (ValueError, RecursionError):   # RecursionError: a deeply nested list, "[[[[…"
        return unreadable
    if not isinstance(data, dict):
        return unreadable
    match, rules = data.get("match", MATCH_ALL), data.get("rules")
    if match not in MATCHES or not isinstance(rules, list):
        return unreadable
    if len(rules) > MAX_RULES:
        return None, ("props", TOO_MANY_RULES)
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict) or not _is_whole_number(rule.get("property_id")):
            return None, (f"props.rules.{index}", UNREADABLE)
    return {"match": match, "rules": rules, "property_ids": sorted({rule["property_id"] for rule in rules})}, None


# ---------------------------------------------------------------------------
# 2. Each line against its property (checks 4–6)
# ---------------------------------------------------------------------------

def _number(raw):
    """A number as text by properties_core's rule -> ``(Decimal, None)`` or ``(None, message)``;
    blank is "Enter a number" here, since a filter line has no "clear"."""
    value, message = parse_value(NUMBER, raw)
    if message:
        return None, message
    if value is None:
        return None, ENTER_NUMBER
    return value, None


def _between(raw):
    if not isinstance(raw, list) or len(raw) != 2:
        return None, ENTER_TWO_NUMBERS
    ends = []
    for end in raw:
        value, message = _number(end)
        if message:
            return None, message
        ends.append(value)
    if ends[0] > ends[1]:
        return None, SMALLER_FIRST
    return tuple(ends), None


def _option_ids(raw, options):
    """A list of distinct option ids of this property, inactive ones too (values may hold them)."""
    if not isinstance(raw, list) or not raw:
        return None, CHOOSE_AT_LEAST_ONE
    known = {option["id"] for option in options}
    # any() stops at the first bad id, so "i not in known" never sees an unhashable value (a dict)
    if any(not _is_whole_number(i) or i not in known for i in raw) or len(set(raw)) != len(raw):
        return None, CHOOSE_OPTION
    return list(raw), None


def _text(raw):
    if not isinstance(raw, str) or not raw.strip():
        return None, ENTER_TEXT
    text = raw.strip()
    if len(text) > TEXT_VALUE_MAX:
        return None, TEXT_TOO_LONG
    return text, None


def _yes_no(raw):
    if not isinstance(raw, bool):
        return None, CHOOSE_YES_NO
    return int(raw), None


def _clean_value(data_type, op, raw, options):
    """The line's value for its operator -> ``(value, None)`` or ``(None, message)``."""
    if op in (HAS, NONE):
        return None, None          # a value sent is ignored
    if op == BETWEEN:
        return _between(raw)
    if data_type == NUMBER:
        return _number(raw)
    if data_type == CHOICE:
        return _option_ids(raw, options)
    if data_type == TEXT:
        return _text(raw)
    return _yes_no(raw)


def check_property_filter(parsed, properties, options):
    """``read_property_filter``'s ``parsed`` -> ``(filter, None)`` or ``(None, (field, message))``.

    ``properties``: ``{id: {id, name, data_type, unit, active, all_classes}}`` for the ids found;
    ``options``: ``{property_id: [{id, label, active}]}``.  Line by line, checks 4–6; the first
    refusal answers.  ``filter``: ``{match, rules: [{property_id, data_type, all_classes, op,
    value}]}``, each value clean (a Decimal, a pair of them, option ids, text, 1 or 0, or None)."""
    rules = []
    for index, rule in enumerate(parsed["rules"]):
        field = f"props.rules.{index}"
        prop = properties.get(rule["property_id"])
        if prop is None or not prop["active"]:
            return None, (f"{field}.property_id", PROPERTY_NOT_IN_USE)
        op = rule.get("op")
        if not isinstance(op, str) or op not in OPERATORS[prop["data_type"]]:
            return None, (f"{field}.op", CHOOSE_OPERATOR)
        value, message = _clean_value(prop["data_type"], op, rule.get("value"), options.get(prop["id"], ()))
        if message:
            return None, (f"{field}.value", message)
        rules.append({"property_id": prop["id"], "data_type": prop["data_type"],
                      "all_classes": bool(prop["all_classes"]), "op": op, "value": value})
    return {"match": parsed["match"], "rules": rules}, None


# ---------------------------------------------------------------------------
# 3. The SQL (§ 5.4)
# ---------------------------------------------------------------------------

def _applies(rule):
    """Where the node shows the property (S061 § 5.3) -> ``(conditions, params)``: linked to its
    class or on every class; a Location only on top-level equipment.  The same rule lives in
    properties.linked_properties, properties_core.on_level and properties.lock_value_properties:
    a change to one is made in all four."""
    conditions, params = [], []
    if not rule["all_classes"]:
        conditions.append("EXISTS (SELECT 1 FROM class_properties cp WHERE cp.class_id = e.class_id"
                          " AND cp.property_id = %s)")
        params.append(rule["property_id"])
    if rule["data_type"] == GEO:
        conditions.append("e.level = %s")
        params.append(GEO_LEVEL)
    return conditions, params


def _value_in_force(rule):
    """The value in force (S044 § 5.5): the item's own row first, then its model's.  A value row
    holds its one value in its type's column, so COALESCE over the two gives "own row wins"; a
    node without a model (S033) has only its own."""
    column = _COLUMNS[rule["data_type"]]
    sql = (f"COALESCE((SELECT iv.{column} FROM equipment_property_values iv WHERE iv.equipment_id = e.id"
           f" AND iv.property_id = %s), (SELECT mv.{column} FROM model_property_values mv"
           f" WHERE mv.model_id = e.model_id AND mv.property_id = %s))")
    return sql, [rule["property_id"], rule["property_id"]]


def _comparison(rule, like):
    """The operator's SQL after the value and its parameters."""
    op, value = rule["op"], rule["value"]
    if op == HAS:
        return "IS NOT NULL", []
    if op == NONE:
        return "IS NULL", []
    if op == BETWEEN:
        return "BETWEEN %s AND %s", list(value)
    if op in (IN, NOT_IN):
        keyword = "IN" if op == IN else "NOT IN"
        return f"{keyword} ({', '.join(['%s'] * len(value))})", list(value)
    if op == CONTAINS:
        return "LIKE %s", [like(value)]
    return _COMPARE_SQL[op], [value]


def filter_condition(filter_, like):
    """The checked filter -> ``(sql, params)``: one condition for the whole filter, the lines
    joined by AND (``match`` "all") or OR ("any"); ``(None, [])`` for no lines.  ``like`` turns a
    text into its LIKE pattern (api_common.like_pattern, passed in so this module imports no
    Flask).  A node meets a line only where it shows the property (D3), so "has no value" lists
    the gaps of the classes that have the property, and "not equal to" leaves out a node with no
    value (D4, SQL's rule for NULL)."""
    if not filter_["rules"]:
        return None, []
    parts, params = [], []
    for rule in filter_["rules"]:
        conditions, rule_params = _applies(rule)
        value_sql, value_params = _value_in_force(rule)
        compare_sql, compare_params = _comparison(rule, like)
        conditions.append(f"{value_sql} {compare_sql}")
        parts.append(f"({' AND '.join(conditions)})")
        params.extend([*rule_params, *value_params, *compare_params])
    joiner = " AND " if filter_["match"] == MATCH_ALL else " OR "
    return f"({joiner.join(parts)})", params
