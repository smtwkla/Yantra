"""The equipment list's property filter — the pure rules (S062 § 5.2, § 5.4, § 8.1)."""

import json
from decimal import Decimal

import pytest

from api_common import like_pattern
from properties_core import (
    CHOOSE_OPTION, CHOOSE_YES_NO, ENTER_NUMBER, ENTER_TEXT, NUMBER_TOO_BIG, TEXT_TOO_LONG, TOO_MANY_DECIMALS,
)
from property_filter_core import (
    CHOOSE_AT_LEAST_ONE, CHOOSE_OPERATOR, ENTER_TWO_NUMBERS, MAX_PROPS_LENGTH, MAX_RULES, OPERATORS,
    PROPERTY_NOT_IN_USE, SMALLER_FIRST, TOO_MANY_RULES, UNREADABLE, check_property_filter, filter_condition,
    read_property_filter,
)

POWER, MOBILITY, FRAME, EXPROOF, GPS, OLD = 12, 15, 17, 18, 19, 20
FIXED, MOBILE, PORTABLE, RETIRED = 31, 32, 33, 34

PROPERTIES = {
    POWER: {"id": POWER, "name": "Rated power", "data_type": "number", "unit": "kW", "active": 1, "all_classes": 0},
    MOBILITY: {"id": MOBILITY, "name": "Mobility", "data_type": "choice", "unit": None, "active": 1,
               "all_classes": 0},
    FRAME: {"id": FRAME, "name": "Frame size", "data_type": "text", "unit": None, "active": 1, "all_classes": 0},
    EXPROOF: {"id": EXPROOF, "name": "Ex-proof", "data_type": "yes_no", "unit": None, "active": 1,
              "all_classes": 1},
    GPS: {"id": GPS, "name": "GPS location", "data_type": "geo", "unit": None, "active": 1, "all_classes": 1},
    OLD: {"id": OLD, "name": "Old", "data_type": "number", "unit": None, "active": 0, "all_classes": 0},
}
OPTIONS = {MOBILITY: [{"id": FIXED, "label": "Fixed", "active": 1}, {"id": MOBILE, "label": "Mobile", "active": 1},
                      {"id": PORTABLE, "label": "Portable", "active": 1},
                      {"id": RETIRED, "label": "Towed", "active": 0}]}


def _raw(rules, match=None):
    data = {"rules": rules} if match is None else {"match": match, "rules": rules}
    return json.dumps(data)


def _read(rules, match=None):
    return read_property_filter(_raw(rules, match))


def _check(rules, match=None):
    parsed, refusal = _read(rules, match)
    assert refusal is None
    return check_property_filter(parsed, PROPERTIES, OPTIONS)


def _rule(property_id, op, value=None):
    rule = {"property_id": property_id, "op": op}
    if value is not None:
        rule["value"] = value
    return rule


def _condition(rules, match=None):
    checked, refusal = _check(rules, match)
    assert refusal is None
    return filter_condition(checked, like_pattern)


class TestRead:

    @pytest.mark.parametrize("raw", [
        "not json", "[1, 2]", '"text"', "{}", '{"rules": {}}', '{"match": "some", "rules": []}',
        '{"match": null, "rules": []}', "[" * 1500 + "]" * 1500,
    ])
    def test_a_value_that_cannot_be_read_is_refused_on_props(self, raw):
        assert read_property_filter(raw) == (None, ("props", UNREADABLE))

    def test_a_props_longer_than_the_limit_is_refused(self):
        raw = _raw([_rule(POWER, "has")] + [{"property_id": POWER, "op": "has", "pad": "x" * MAX_PROPS_LENGTH}])
        assert len(raw) > MAX_PROPS_LENGTH
        assert read_property_filter(raw) == (None, ("props", UNREADABLE))

    def test_eleven_rules_are_refused(self):
        assert _read([_rule(POWER, "has")] * (MAX_RULES + 1)) == (None, ("props", TOO_MANY_RULES))

    def test_ten_rules_pass(self):
        parsed, refusal = _read([_rule(POWER, "has")] * MAX_RULES)
        assert refusal is None and len(parsed["rules"]) == MAX_RULES

    @pytest.mark.parametrize("rule", [
        "power", None, {"op": "has"}, {"property_id": 0}, {"property_id": -3}, {"property_id": "12"},
        {"property_id": 12.0}, {"property_id": True},
    ])
    def test_a_rule_without_a_whole_property_id_is_refused_on_its_line(self, rule):
        assert _read([_rule(POWER, "has"), rule]) == (None, ("props.rules.1", UNREADABLE))

    def test_missing_or_empty_props_is_no_filter(self):
        for raw in (None, ""):
            assert read_property_filter(raw) == ({"match": "all", "rules": [], "property_ids": []}, None)

    def test_match_defaults_to_all_and_property_ids_is_the_sorted_set(self):
        parsed, refusal = _read([_rule(MOBILITY, "has"), _rule(POWER, "gt", "5"), _rule(POWER, "lt", "9")])
        assert refusal is None
        assert parsed["match"] == "all" and parsed["property_ids"] == [POWER, MOBILITY]

    def test_any_is_kept(self):
        assert _read([], "any")[0]["match"] == "any"


class TestCheck:

    def test_an_unknown_and_an_inactive_property_are_refused(self):
        assert _check([_rule(99, "has")]) == (None, ("props.rules.0.property_id", PROPERTY_NOT_IN_USE))
        assert _check([_rule(POWER, "has"), _rule(OLD, "has")]) == (
            None, ("props.rules.1.property_id", PROPERTY_NOT_IN_USE))

    @pytest.mark.parametrize("property_id, op", [
        (POWER, "contains"), (MOBILITY, "eq"), (FRAME, "gt"), (EXPROOF, "ne"), (GPS, "eq"), (POWER, None),
        (POWER, ["gt"]), (POWER, "GT"),
    ])
    def test_an_operator_not_of_the_data_type_is_refused(self, property_id, op):
        assert _check([{"property_id": property_id, "op": op, "value": "1"}]) == (
            None, ("props.rules.0.op", CHOOSE_OPERATOR))

    @pytest.mark.parametrize("rule, message", [
        (_rule(POWER, "gt", "7,5"), ENTER_NUMBER),
        (_rule(POWER, "gt", "  "), ENTER_NUMBER),
        ({"property_id": POWER, "op": "gt"}, ENTER_NUMBER),
        (_rule(POWER, "gt", True), ENTER_NUMBER),
        (_rule(POWER, "eq", "5.12345"), TOO_MANY_DECIMALS),
        (_rule(POWER, "eq", "1000000000000"), NUMBER_TOO_BIG),
        (_rule(POWER, "between", "5"), ENTER_TWO_NUMBERS),
        (_rule(POWER, "between", ["5"]), ENTER_TWO_NUMBERS),
        (_rule(POWER, "between", ["5", "6", "7"]), ENTER_TWO_NUMBERS),
        (_rule(POWER, "between", ["5", ""]), ENTER_NUMBER),
        (_rule(POWER, "between", ["10", "5"]), SMALLER_FIRST),
        (_rule(MOBILITY, "in", []), CHOOSE_AT_LEAST_ONE),
        (_rule(MOBILITY, "in", FIXED), CHOOSE_AT_LEAST_ONE),
        (_rule(MOBILITY, "in", [FIXED, 999]), CHOOSE_OPTION),
        (_rule(MOBILITY, "in", [True]), CHOOSE_OPTION),
        (_rule(MOBILITY, "not_in", [FIXED, FIXED]), CHOOSE_OPTION),
        (_rule(MOBILITY, "in", [str(FIXED)]), CHOOSE_OPTION),
        (_rule(FRAME, "contains", "   "), ENTER_TEXT),
        (_rule(FRAME, "eq", 5), ENTER_TEXT),
        (_rule(FRAME, "eq", "x" * 101), TEXT_TOO_LONG),
        (_rule(EXPROOF, "eq", "true"), CHOOSE_YES_NO),
        (_rule(EXPROOF, "eq", 1), CHOOSE_YES_NO),
    ])
    def test_a_bad_value_is_refused_on_its_line(self, rule, message):
        assert _check([_rule(FRAME, "has"), rule]) == (None, ("props.rules.1.value", message))

    def test_an_option_of_another_property_is_refused(self):
        options = {**OPTIONS, FRAME: [{"id": 77, "label": "x", "active": 1}]}
        parsed, _ = _read([_rule(MOBILITY, "in", [77])])
        assert check_property_filter(parsed, PROPERTIES, options) == (None, ("props.rules.0.value", CHOOSE_OPTION))

    def test_the_first_refusal_answers_line_by_line(self):
        assert _check([_rule(POWER, "gt", "x"), _rule(OLD, "has")]) == (None, ("props.rules.0.value", ENTER_NUMBER))

    def test_clean_values(self):
        checked, refusal = _check([
            _rule(POWER, "gt", " 7.5 "), _rule(POWER, "between", ["5", "5"]), _rule(MOBILITY, "in", [RETIRED, FIXED]),
            _rule(FRAME, "contains", "  IE3 "), _rule(EXPROOF, "eq", False), _rule(GPS, "has", "ignored"),
        ], "any")
        assert refusal is None
        assert checked["match"] == "any"
        assert [(r["op"], r["value"]) for r in checked["rules"]] == [
            ("gt", Decimal("7.5")), ("between", (Decimal("5"), Decimal("5"))), ("in", [RETIRED, FIXED]),
            ("contains", "IE3"), ("eq", 0), ("has", None),
        ]
        assert [r["all_classes"] for r in checked["rules"]] == [False, False, False, False, True, True]

    def test_no_rules_give_no_condition(self):
        checked, refusal = _check([])
        assert refusal is None and filter_condition(checked, like_pattern) == (None, [])


APPLIES = ("EXISTS (SELECT 1 FROM class_properties cp WHERE cp.class_id = e.class_id AND cp.property_id = %s)")


def _value(column):
    return (f"COALESCE((SELECT iv.{column} FROM equipment_property_values iv WHERE iv.equipment_id = e.id"
            f" AND iv.property_id = %s), (SELECT mv.{column} FROM model_property_values mv"
            f" WHERE mv.model_id = e.model_id AND mv.property_id = %s))")


class TestCondition:

    @pytest.mark.parametrize("op, value, sql, params", [
        ("eq", "7.5", "= %s", [Decimal("7.5")]),
        ("ne", "7.5", "<> %s", [Decimal("7.5")]),
        ("lt", "7.5", "< %s", [Decimal("7.5")]),
        ("le", "7.5", "<= %s", [Decimal("7.5")]),
        ("gt", "7.5", "> %s", [Decimal("7.5")]),
        ("ge", "7.5", ">= %s", [Decimal("7.5")]),
        ("between", ["5", "10"], "BETWEEN %s AND %s", [Decimal("5"), Decimal("10")]),
        ("has", None, "IS NOT NULL", []),
        ("none", None, "IS NULL", []),
    ])
    def test_number_operators(self, op, value, sql, params):
        assert _condition([_rule(POWER, op, value)]) == (
            f"(({APPLIES} AND {_value('value_number')} {sql}))", [POWER, POWER, POWER, *params])

    def test_choice_text_and_yes_no(self):
        assert _condition([_rule(MOBILITY, "in", [MOBILE, PORTABLE])]) == (
            f"(({APPLIES} AND {_value('option_id')} IN (%s, %s)))", [MOBILITY, MOBILITY, MOBILITY, MOBILE, PORTABLE])
        assert _condition([_rule(MOBILITY, "not_in", [FIXED])]) == (
            f"(({APPLIES} AND {_value('option_id')} NOT IN (%s)))", [MOBILITY, MOBILITY, MOBILITY, FIXED])
        assert _condition([_rule(FRAME, "contains", "5%_\\")]) == (
            f"(({APPLIES} AND {_value('value_text')} LIKE %s))", [FRAME, FRAME, FRAME, "%5\\%\\_\\\\%"])
        assert _condition([_rule(FRAME, "eq", "132M")]) == (
            f"(({APPLIES} AND {_value('value_text')} = %s))", [FRAME, FRAME, FRAME, "132M"])

    def test_an_every_class_property_has_no_class_link_condition(self):
        assert _condition([_rule(EXPROOF, "eq", True)]) == (f"(({_value('value_bool')} = %s))", [EXPROOF, EXPROOF, 1])

    def test_a_location_is_on_top_level_equipment_only(self):
        assert _condition([_rule(GPS, "none")]) == (
            f"((e.level = %s AND {_value('value_lat')} IS NULL))", ["equipment", GPS, GPS])

    def test_all_joins_with_and_any_with_or(self):
        rules = [_rule(POWER, "has"), _rule(FRAME, "has")]
        sql_all, _ = _condition(rules)
        sql_any, _ = _condition(rules, "any")
        line = f"({APPLIES} AND {_value('value_number')} IS NOT NULL)"
        assert sql_all.startswith(f"({line} AND (")
        assert sql_any.startswith(f"({line} OR (")

    def test_request_text_is_only_in_the_parameters(self):
        attack = "x' OR 1=1 --"
        sql, params = _condition([_rule(FRAME, "eq", attack), _rule(FRAME, "contains", attack)])
        assert "OR 1=1" not in sql and "'" not in sql
        assert params[3] == attack and params[7] == like_pattern(attack)

    def test_every_operator_has_as_many_placeholders_as_parameters(self):
        values = {"between": ["1", "2"], "in": [FIXED, MOBILE], "not_in": [PORTABLE], "contains": "a",
                  "eq": {"text": "a", "yes_no": True}, "has": None, "none": None}
        rules = []
        for prop in PROPERTIES.values():
            if not prop["active"]:
                continue
            for op in OPERATORS[prop["data_type"]]:
                value = values.get(op, "3")
                if isinstance(value, dict):
                    value = value.get(prop["data_type"], "3")
                rules.append(_rule(prop["id"], op, value))
        for start in range(0, len(rules), MAX_RULES):
            chunk = rules[start:start + MAX_RULES]
            sql, params = _condition(chunk, "any")
            assert sql.count("%s") == len(params), chunk
