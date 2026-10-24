"""Equipment properties — the pure rules (S035 § 5, § 8.1)."""

from decimal import Decimal

import pytest

from properties_core import (
    CHOOSE_ACTIVE_PROPERTIES, CHOOSE_A_PROPERTY, CHOOSE_DATA_TYPE, CHOOSE_OPTION, CHOOSE_YES_NO, DATA_TYPE_FIXED,
    DESCRIPTION_TOO_LONG, ENTER_LABEL, ENTER_NAME, ENTER_NUMBER, LABEL_TOO_LONG, NAME_TOO_LONG, NOT_ON_CLASS,
    NUMBER_TOO_BIG, ONLY_CHOICE_HAS_OPTIONS, OPTION_EXISTS, TEXT_TOO_LONG, TOO_MANY_DECIMALS, UNIT_FIXED,
    UNIT_ONLY_NUMBER, UNIT_TOO_LONG, VALUES_NOT_OBJECT, can_link, check_model_values, format_value, number_text,
    parse_property_ids, parse_value, parse_value_keys, property_changes, property_view, stored_value,
    validate_option, validate_property,
)


def _errors(data, creating=True):
    return [(e["field"], e["message"]) for e in validate_property(data, creating)[1]]


class TestProperty:

    def test_name_is_trimmed_and_collapsed(self):
        clean, errors = validate_property({"name": "  Power  –   design ", "data_type": "number"}, True)
        assert errors == [] and clean["name"] == "Power – design"

    @pytest.mark.parametrize("name, message", [
        ("", ENTER_NAME), ("   ", ENTER_NAME), (12, ENTER_NAME), (None, ENTER_NAME),
        ("x" * 81, NAME_TOO_LONG),
    ])
    def test_name_refusals(self, name, message):
        assert _errors({"name": name, "data_type": "text"}) == [("name", message)]

    def test_80_characters_pass(self):
        assert _errors({"name": "x" * 80, "data_type": "text"}) == []

    def test_create_needs_name_and_data_type(self):
        assert _errors({}) == [("name", ENTER_NAME), ("data_type", CHOOSE_DATA_TYPE)]
        assert _errors({"name": "Speed", "data_type": "float"}) == [("data_type", CHOOSE_DATA_TYPE)]

    def test_an_update_needs_nothing(self):
        assert validate_property({}, False) == ({}, [])

    def test_unit_and_description(self):
        clean, errors = validate_property({"name": "Speed", "data_type": "number", "unit": " rpm ",
                                           "description": "  "}, True)
        assert errors == [] and clean["unit"] == "rpm" and clean["description"] is None
        assert _errors({"name": "Speed", "data_type": "number", "unit": "x" * 21}) == [("unit", UNIT_TOO_LONG)]
        assert _errors({"name": "Speed", "data_type": "number", "unit": 5}) == [("unit", UNIT_TOO_LONG)]
        assert _errors({"name": "S", "data_type": "text", "description": "x" * 301}) == [
            ("description", DESCRIPTION_TOO_LONG)]

    def test_active_is_a_flag(self):
        assert validate_property({"active": False}, False) == ({"active": 0}, [])
        assert validate_property({"active": "no"}, False)[1][0]["field"] == "active"

    def test_options_on_create(self):
        clean, errors = validate_property({"name": "Drain", "data_type": "choice",
                                           "options": [" Internal ", "External"]}, True)
        assert errors == [] and clean["options"] == ["Internal", "External"]
        assert _errors({"name": "D", "data_type": "choice", "options": ["Internal", "internal"]}) == [
            ("options", OPTION_EXISTS)]
        assert _errors({"name": "D", "data_type": "choice", "options": [""]}) == [("options", ENTER_LABEL)]
        assert _errors({"name": "D", "data_type": "text", "options": ["A"]}) == [("options", ONLY_CHOICE_HAS_OPTIONS)]
        # An empty list on another type is no options at all
        assert _errors({"name": "D", "data_type": "text", "options": []}) == []


class TestPropertyChanges:

    NUMBER_KW = {"data_type": "number", "unit": "kW"}
    TEXT = {"data_type": "text", "unit": None}

    def test_a_unit_on_a_new_choice_is_refused(self):
        assert property_changes(None, {"data_type": "choice", "unit": "kW"}) == (
            None, ("unit", UNIT_ONLY_NUMBER, 400))
        assert property_changes(None, {"data_type": "choice", "unit": None}) == (
            {"data_type": "choice", "unit": None}, None)

    def test_the_options_list_is_not_a_column(self):
        assert property_changes(None, {"data_type": "choice", "options": ["A"]}) == ({"data_type": "choice"}, None)

    def test_a_unit_on_a_stored_text_is_refused(self):
        assert property_changes(self.TEXT, {"unit": "kW"}) == (None, ("unit", UNIT_ONLY_NUMBER, 400))

    def test_number_to_text_clears_the_unit(self):
        assert property_changes(self.NUMBER_KW, {"data_type": "text"}) == ({"data_type": "text", "unit": None}, None)

    def test_type_and_unit_change_freely_without_options_or_values(self):
        assert property_changes(self.TEXT, {"data_type": "number", "unit": "bar"}) == (
            {"data_type": "number", "unit": "bar"}, None)
        assert property_changes(self.NUMBER_KW, {"unit": "W"}) == ({"unit": "W"}, None)

    def test_the_data_type_is_fixed_by_an_option_or_a_value(self):
        choice = {"data_type": "choice", "unit": None}
        assert property_changes(choice, {"data_type": "text"}, has_options=True) == (
            None, ("data_type", DATA_TYPE_FIXED, 409))
        assert property_changes(self.NUMBER_KW, {"data_type": "text"}, has_values=True) == (
            None, ("data_type", DATA_TYPE_FIXED, 409))

    def test_the_unit_is_fixed_by_a_value(self):
        assert property_changes(self.NUMBER_KW, {"unit": "W"}, has_values=True) == (
            None, ("unit", UNIT_FIXED, 409))
        assert property_changes(self.NUMBER_KW, {"unit": None}, has_values=True) == (
            None, ("unit", UNIT_FIXED, 409))

    def test_sending_the_same_type_and_unit_is_no_change(self):
        assert property_changes(self.NUMBER_KW, {"data_type": "number", "unit": "kW", "name": "P"},
                                has_options=True, has_values=True) == ({"name": "P"}, None)


class TestParseValue:

    @pytest.mark.parametrize("raw, expected", [
        ("62.5", Decimal("62.5")), (62.5, Decimal("62.5")), ("-40", Decimal("-40")), (" 7 ", Decimal("7")),
        (1440, Decimal("1440")), ("0.0045", Decimal("0.0045")), ("62.5000", Decimal("62.5000")),
        ("999999999999.9999", Decimal("999999999999.9999")),
    ])
    def test_numbers_accepted(self, raw, expected):
        assert parse_value("number", raw) == (expected, None)

    @pytest.mark.parametrize("raw, message", [
        ("1e3", ENTER_NUMBER), ("+5", ENTER_NUMBER), ("1 000", ENTER_NUMBER), ("1,000", ENTER_NUMBER),
        ("1.", ENTER_NUMBER), (".5", ENTER_NUMBER), ("abc", ENTER_NUMBER), ("NaN", ENTER_NUMBER),
        (True, ENTER_NUMBER), (float("nan"), ENTER_NUMBER), (float("inf"), ENTER_NUMBER), ([1], ENTER_NUMBER),
        ("٣", ENTER_NUMBER),
        ("0.00001", TOO_MANY_DECIMALS), (0.00001, TOO_MANY_DECIMALS),
        (10 ** 12, NUMBER_TOO_BIG), ("-1000000000000", NUMBER_TOO_BIG), (1e16, NUMBER_TOO_BIG),
    ])
    def test_numbers_refused(self, raw, message):
        assert parse_value("number", raw) == (None, message)

    @pytest.mark.parametrize("data_type", ["number", "text", "yes_no", "choice"])
    @pytest.mark.parametrize("raw", [None, "", "   "])
    def test_blank_clears(self, data_type, raw):
        assert parse_value(data_type, raw) == (None, None)

    def test_text(self):
        assert parse_value("text", "  IP55 ") == ("IP55", None)
        assert parse_value("text", "x" * 100) == ("x" * 100, None)
        assert parse_value("text", "x" * 101) == (None, TEXT_TOO_LONG)
        assert parse_value("text", 55)[1] is not None

    def test_yes_no(self):
        assert parse_value("yes_no", True) == (1, None)
        assert parse_value("yes_no", False) == (0, None)
        assert parse_value("yes_no", "yes") == (None, CHOOSE_YES_NO)
        assert parse_value("yes_no", 1) == (None, CHOOSE_YES_NO)

    def test_choice(self):
        options = [{"id": 5, "active": 1}, {"id": 6, "active": 0}]
        assert parse_value("choice", 5, options) == (5, None)
        assert parse_value("choice", 6, options) == (None, CHOOSE_OPTION)         # inactive, newly picked
        assert parse_value("choice", 6, options, stored_option_id=6) == (6, None)  # inactive, unchanged
        assert parse_value("choice", 7, options) == (None, CHOOSE_OPTION)         # another property's
        assert parse_value("choice", "5", options) == (None, CHOOSE_OPTION)
        assert parse_value("choice", True, [{"id": 1, "active": 1}]) == (None, CHOOSE_OPTION)


class TestFormat:

    def test_numbers(self):
        assert format_value("number", Decimal("62.5000"), "kVA") == "62.5 kVA"
        assert format_value("number", Decimal("3"), None) == "3"
        assert format_value("number", Decimal("3.0000"), "") == "3"
        assert format_value("number", Decimal("100.0000"), "kW") == "100 kW"
        assert format_value("number", Decimal("-40.0000"), "°C") == "-40 °C"
        assert number_text(Decimal("0.0000")) == "0" and number_text(Decimal("-0")) == "0"
        assert number_text(Decimal("1200000.0000")) == "1200000"

    def test_other_types(self):
        assert format_value("yes_no", 1) == "Yes" and format_value("yes_no", 0) == "No"
        assert format_value("choice", 5, option_label="Internal") == "Internal"
        assert format_value("text", "IP55") == "IP55"
        assert format_value("number", None, "kW") is None

    def test_stored_value(self):
        assert stored_value("number", {"value_number": Decimal("62.5000")}) == "62.5"
        assert stored_value("yes_no", {"value_bool": 0}) is False
        assert stored_value("choice", {"option_id": 5}) == 5
        assert stored_value("text", None) is None


class TestLinks:

    def test_property_ids(self):
        assert parse_property_ids([3, 1, 3]) == ([1, 3], None)
        for raw in ([], None, "1", [0], [True], ["1"], [1.0]):
            assert parse_property_ids(raw) == (None, CHOOSE_A_PROPERTY)

    def test_can_link(self):
        assert can_link({"active": 1, "data_type": "number"}, 0)
        assert not can_link({"active": 0, "data_type": "number"}, 0)
        assert not can_link({"active": 1, "data_type": "choice"}, 0)
        assert can_link({"active": 1, "data_type": "choice"}, 1)
        assert CHOOSE_ACTIVE_PROPERTIES == "Choose active properties"


def _prop(pid, name, data_type="number", active=1, linked=True):
    return {"id": pid, "name": name, "data_type": data_type, "active": active, "linked": linked}


class TestModelValues:

    def test_keys(self):
        assert parse_value_keys({"12": 1, "3": None}) == ([3, 12], None)
        assert parse_value_keys({}) == ([], None)
        assert parse_value_keys([]) == (None, ("values", VALUES_NOT_OBJECT))
        for key in ("abc", "12.0", "-1", "0", " 1"):
            assert parse_value_keys({key: 1}) == (None, (f"values.{key}", NOT_ON_CLASS))

    def test_unknown_inactive_or_unlinked_is_refused(self):
        props = {1: _prop(1, "A", active=0), 2: _prop(2, "B", linked=False)}
        for key in ("1", "2", "9"):
            assert check_model_values({key: "1"}, props, {}, {}) == (None, (f"values.{key}", NOT_ON_CLASS))

    def test_the_first_refusal_by_name_answers(self):
        props = {1: _prop(1, "Zeta"), 2: _prop(2, "alpha")}
        assert check_model_values({"1": "x", "2": "y"}, props, {}, {}) == (None, ("values.2", ENTER_NUMBER))

    def test_changes(self):
        props = {1: _prop(1, "Power"), 2: _prop(2, "Drain", "choice"), 3: _prop(3, "VSD", "yes_no")}
        changes, error = check_model_values({"1": "7.5", "2": 5, "3": ""}, props,
                                            {2: [{"id": 5, "active": 1}]}, {})
        assert error is None
        assert dict(changes) == {
            1: {"value_number": Decimal("7.5"), "value_text": None, "value_bool": None, "option_id": None},
            2: {"value_number": None, "value_text": None, "value_bool": None, "option_id": 5},
            3: None,
        }

    def test_an_inactive_option_is_kept_when_unchanged(self):
        props = {2: _prop(2, "Drain", "choice")}
        options = {2: [{"id": 5, "active": 0}]}
        assert check_model_values({"2": 5}, props, options, {})[1] == ("values.2", CHOOSE_OPTION)
        assert check_model_values({"2": 5}, props, options, {2: {"option_id": 5}})[1] is None


class TestPropertyView:

    def test_rows_by_name_with_values(self):
        props = [
            {"id": 3, "name": "Generator rating", "data_type": "number", "unit": "kVA"},
            {"id": 1, "name": "drain", "data_type": "choice", "unit": None},
            {"id": 2, "name": "Frame size", "data_type": "text", "unit": None},
        ]
        values = {3: {"value_number": Decimal("62.5000"), "value_text": None, "value_bool": None, "option_id": None},
                  1: {"value_number": None, "value_text": None, "value_bool": None, "option_id": 9}}
        assert property_view(props, values, {9: "Internal"}) == [
            {"property_id": 1, "name": "drain", "value": 9, "unit": None, "display": "Internal", "source": "model"},
            {"property_id": 2, "name": "Frame size", "value": None, "unit": None, "display": None, "source": None},
            {"property_id": 3, "name": "Generator rating", "value": "62.5", "unit": "kVA", "display": "62.5 kVA",
             "source": "model"},
        ]

    def test_no_properties(self):
        assert property_view([], {}, {}) == []


def test_option_label_rules():
    assert validate_option({"label": "  Packed   gland "}, True) == ({"label": "Packed gland"}, [])
    assert validate_option({}, True)[1] == [{"field": "label", "message": ENTER_LABEL}]
    assert validate_option({"label": "x" * 61}, True)[1] == [{"field": "label", "message": LABEL_TOO_LONG}]
    assert validate_option({"active": False}, False) == ({"active": 0}, [])
