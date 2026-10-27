"""Equipment properties — the pure rules (S043 § 5, § 8.1; an item's own values: S044 § 5, § 8.1;
Location, every-class and per-machine properties: S061 § 5, § 8.1)."""

from decimal import Decimal

import pytest

from properties_core import (
    CHOOSE_ACTIVE_PROPERTIES, CHOOSE_A_PROPERTY, CHOOSE_DATA_TYPE, CHOOSE_OPTION, CHOOSE_YES_NO, CHOOSE_YES_OR_NO,
    DATA_TYPE_FIXED, DESCRIPTION_TOO_LONG, ENTER_LABEL, ENTER_LOCATION, ENTER_NAME, ENTER_NUMBER, LABEL_TOO_LONG,
    LATITUDE_RANGE, LONGITUDE_RANGE, MOVING_HINT, NAME_TOO_LONG, NOT_ON_CLASS, NUMBER_TOO_BIG,
    ONLY_CHOICE_HAS_OPTIONS, OPTION_EXISTS, OWNER_ITEM, OWNER_MODEL, PER_ITEM_HAS_MODEL_VALUES, SET_ON_EACH_MACHINE,
    TEXT_TOO_LONG, TOO_MANY_DECIMALS, UNIT_FIXED, UNIT_ONLY_NUMBER, UNIT_TOO_LONG, VALUES_NOT_OBJECT, can_link,
    check_values, format_value, item_changes, item_events, map_url, moving_hint, number_text, on_level,
    parse_property_ids, parse_value, parse_value_keys, property_changes, property_view, stored_value,
    validate_option, validate_property, value_in_force,
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
            assert check_values({key: "1"}, props, {}, {}, owner=OWNER_MODEL) == (None, (f"values.{key}", NOT_ON_CLASS))

    def test_the_first_refusal_by_name_answers(self):
        props = {1: _prop(1, "Zeta"), 2: _prop(2, "alpha")}
        assert check_values({"1": "x", "2": "y"}, props, {}, {}, owner=OWNER_MODEL) == (None, ("values.2", ENTER_NUMBER))

    def test_an_unlinked_property_is_refused_in_its_name_s_place(self):
        """CR1-05: the order is by name, not by the body's key order; an unknown id (no name) first."""
        props = {1: _prop(1, "Zeta", linked=False), 2: _prop(2, "alpha")}
        assert check_values({"1": "1", "2": "y"}, props, {}, {}, owner=OWNER_MODEL) == (None, ("values.2", ENTER_NUMBER))
        props = {1: _prop(1, "alpha", active=0), 2: _prop(2, "Zeta")}
        assert check_values({"2": "y", "1": "1"}, props, {}, {}, owner=OWNER_MODEL) == (None, ("values.1", NOT_ON_CLASS))
        assert check_values({"2": "y", "9": "1", "7": "1"}, props, {}, {}, owner=OWNER_MODEL) == (
            None, ("values.7", NOT_ON_CLASS))

    def test_changes(self):
        props = {1: _prop(1, "Power"), 2: _prop(2, "Drain", "choice"), 3: _prop(3, "VSD", "yes_no")}
        changes, error = check_values({"1": "7.5", "2": 5, "3": ""}, props,
                                            {2: [{"id": 5, "active": 1}]}, {}, owner=OWNER_MODEL)
        assert error is None
        assert dict(changes) == {
            1: {"value_number": Decimal("7.5"), "value_text": None, "value_bool": None, "option_id": None,
               "value_lat": None, "value_lng": None},
            2: {"value_number": None, "value_text": None, "value_bool": None, "option_id": 5,
               "value_lat": None, "value_lng": None},
            3: None,
        }

    def test_clear_by_null_and_by_empty_text(self):
        """S044 § 8.1: an item's save clears its own value by "" or null, as the model's."""
        props = {1: _prop(1, "Power"), 2: _prop(2, "Frame", "text")}
        assert check_values({"1": None, "2": ""}, props, {}, {}, owner=OWNER_MODEL) == ([(2, None), (1, None)], None)

    def test_an_inactive_option_is_kept_when_unchanged(self):
        props = {2: _prop(2, "Drain", "choice")}
        options = {2: [{"id": 5, "active": 0}]}
        assert check_values({"2": 5}, props, options, {}, owner=OWNER_MODEL)[1] == ("values.2", CHOOSE_OPTION)
        assert check_values({"2": 5}, props, options, {2: {"option_id": 5}}, owner=OWNER_MODEL)[1] is None


class TestPropertyView:

    def test_rows_by_name_with_values(self):
        props = [
            {"id": 3, "name": "Generator rating", "data_type": "number", "unit": "kVA"},
            {"id": 1, "name": "drain", "data_type": "choice", "unit": None},
            {"id": 2, "name": "Frame size", "data_type": "text", "unit": None},
        ]
        values = {3: _columns(value_number=Decimal("62.5000")), 1: _columns(option_id=9)}
        common = {"per_item_only": False, "map_url": None}
        assert property_view(props, values, {9: "Internal"}) == [
            {"property_id": 1, "name": "drain", "data_type": "choice", "value": 9, "unit": None, "display": "Internal",
             "source": "model", **common},
            {"property_id": 2, "name": "Frame size", "data_type": "text", "value": None, "unit": None, "display": None,
             "source": None, **common},
            {"property_id": 3, "name": "Generator rating", "data_type": "number", "value": "62.5", "unit": "kVA",
             "display": "62.5 kVA", "source": "model", **common},
        ]

    def test_no_properties(self):
        assert property_view([], {}, {}) == []

    def test_no_model_shows_every_property_without_a_value(self):
        """A component-unit without a model (S033, BS1-01): the shell passes no values."""
        props = [{"id": 3, "name": "Generator rating", "data_type": "number", "unit": "kVA"}]
        assert property_view(props, {}, {}) == [
            {"property_id": 3, "name": "Generator rating", "data_type": "number", "per_item_only": False,
             "value": None, "unit": "kVA", "display": None, "source": None, "map_url": None}]


def test_option_label_rules():
    assert validate_option({"label": "  Packed   gland "}, True) == ({"label": "Packed gland"}, [])
    assert validate_option({}, True)[1] == [{"field": "label", "message": ENTER_LABEL}]
    assert validate_option({"label": "x" * 61}, True)[1] == [{"field": "label", "message": LABEL_TOO_LONG}]
    assert validate_option({"active": False}, False) == ({"active": 0}, [])


# ---------------------------------------------------------------------------
# An item's own values (S044 § 5.1, § 5.4, § 8.1)
# ---------------------------------------------------------------------------

def _columns(**value):
    """A value row / a change's columns: the four typed columns, one filled."""
    return {"value_number": None, "value_text": None, "value_bool": None, "option_id": None, "value_lat": None,
            "value_lng": None, **value}


class TestItemChanges:

    def test_a_clear_with_no_stored_row_is_dropped(self):
        assert item_changes([(1, None)], {}) == []

    def test_an_equal_value_is_dropped_per_data_type(self):
        stored = {1: _columns(value_number=Decimal("5.5000")), 2: _columns(value_text="IP55"),
                  3: _columns(value_bool=0), 4: _columns(option_id=9)}
        changes = [(1, _columns(value_number=Decimal("5.5"))), (2, _columns(value_text="IP55")),
                   (3, _columns(value_bool=0)), (4, _columns(option_id=9))]
        assert item_changes(changes, stored) == []

    def test_a_set_a_change_and_a_clear_are_kept(self):
        stored = {2: _columns(value_number=Decimal("7.5000")), 3: _columns(value_text="IP55"),
                  4: _columns(value_bool=1), 5: _columns(option_id=9)}
        changes = [(1, _columns(value_number=Decimal("5.5"))), (2, _columns(value_number=Decimal("5.5"))),
                   (3, _columns(value_text="ip55")), (4, _columns(value_bool=0)), (5, _columns(option_id=8)),
                   (6, None)]
        stored[6] = _columns(value_text="132M")
        assert item_changes(changes, stored) == changes


class TestPropertyViewWithItemValues:

    PROPS = [
        {"id": 1, "name": "Rated power", "data_type": "number", "unit": "kW"},
        {"id": 2, "name": "Shaft orientation", "data_type": "choice", "unit": None},
        {"id": 3, "name": "Frame size", "data_type": "text", "unit": None},
    ]

    def test_the_item_wins_then_the_model_then_none(self):
        model = {1: _columns(value_number=Decimal("7.5000")), 2: _columns(option_id=9)}
        item = {1: _columns(value_number=Decimal("5.5000"))}
        rows = property_view(self.PROPS, model, {9: "Horizontal"}, item)
        assert [(r["name"], r["value"], r["display"], r["source"]) for r in rows] == [
            ("Frame size", None, None, None),
            ("Rated power", "5.5", "5.5 kW", "item"),
            ("Shaft orientation", 9, "Horizontal", "model"),
        ]

    def test_a_model_less_item_shows_only_its_own(self):
        rows = property_view(self.PROPS, {}, {}, {3: _columns(value_text="132M")})
        assert [(r["display"], r["source"]) for r in rows] == [("132M", "item"), (None, None), (None, None)]

    def test_an_own_value_of_an_unlisted_property_is_not_shown(self):
        """A class change hides an own value of a property the new class lacks (S044 § 1.7)."""
        rows = property_view(self.PROPS[:1], {}, {}, {3: _columns(value_text="132M")})
        assert [r["property_id"] for r in rows] == [1]


class TestItemEvents:

    PROPS = {
        1: {"id": 1, "name": "Rated power", "data_type": "number", "unit": "kW"},
        2: {"id": 2, "name": "Shaft orientation", "data_type": "choice", "unit": None},
        3: {"id": 3, "name": "Ex-proof", "data_type": "yes_no", "unit": None},
    }
    LABELS = {9: "Horizontal", 8: "Vertical"}

    def _events(self, changes, before=None, model_displays=None, has_model=True):
        return item_events(self.PROPS, changes, before or {}, model_displays or {}, self.LABELS, has_model)

    def test_set_from_the_model_s_value_with_the_unit(self):
        assert self._events([(1, _columns(value_number=Decimal("5.5")))], model_displays={1: "7.5 kW"}) == [
            ("property", "Rated power: 7.5 kW (model)", "Rated power: 5.5 kW")]

    def test_set_from_a_model_with_no_value_and_an_option_label(self):
        assert self._events([(2, _columns(option_id=9))]) == [
            ("property", "Shaft orientation: no value (model)", "Shaft orientation: Horizontal")]

    def test_set_on_a_model_less_item(self):
        assert self._events([(3, _columns(value_bool=1))], has_model=False) == [
            ("property", "Ex-proof: no value", "Ex-proof: Yes")]

    def test_a_change(self):
        before = {2: _columns(option_id=9)}
        assert self._events([(2, _columns(option_id=8))], before=before) == [
            ("property", "Shaft orientation: Horizontal", "Shaft orientation: Vertical")]

    def test_a_clear_back_to_the_model_s_value(self):
        before = {1: _columns(value_number=Decimal("5.5000"))}
        assert self._events([(1, None)], before=before, model_displays={1: "7.5 kW"}) == [
            ("property", "Rated power: 5.5 kW", "Rated power: 7.5 kW (model)")]
        assert self._events([(1, None)], before=before, has_model=False) == [
            ("property", "Rated power: 5.5 kW", "Rated power: no value")]

    def test_one_event_per_change_by_name(self):
        changes = [(2, _columns(option_id=9)), (1, _columns(value_number=Decimal("5.5"))),
                   (3, _columns(value_bool=0))]
        assert [e[1].split(":")[0] for e in self._events(changes)] == ["Ex-proof", "Rated power",
                                                                        "Shaft orientation"]


# ---------------------------------------------------------------------------
# S061: Location, every-class and per-machine properties (§ 5, § 8.1)
# ---------------------------------------------------------------------------

def _geo(lat, lng):
    return _columns(value_lat=Decimal(lat), value_lng=Decimal(lng))


class TestLocation:

    @pytest.mark.parametrize("raw", ["11.016823, 76.955812", "11.016823,76.955812", "11.016823 76.955812",
                                     " 11.016823 ,  76.955812 "])
    def test_the_separators(self, raw):
        assert parse_value("geo", raw) == ((Decimal("11.016823"), Decimal("76.955812")), None)

    def test_more_than_6_decimals_are_rounded(self):
        assert parse_value("geo", "11.0000005, 76.0000004") == ((Decimal("11.000001"), Decimal("76.000000")), None)
        assert parse_value("geo", "11.0168234567, 76.9558123") == ((Decimal("11.016823"), Decimal("76.955812")), None)

    @pytest.mark.parametrize("raw", ["90, 180", "-90, -180", "0, 0", "-0.5, 0"])
    def test_the_ends_and_zero_are_accepted(self, raw):
        assert parse_value("geo", raw)[1] is None

    @pytest.mark.parametrize("raw, message", [
        ("90.000001, 76", LATITUDE_RANGE), ("-91, 76", LATITUDE_RANGE),
        ("11, -180.000001", LONGITUDE_RANGE), ("11, 181", LONGITUDE_RANGE),
        # S061 CR1-01: more digits than Decimal's 28-digit context holds after rounding
        ("1111111111111111111111111, 5", LATITUDE_RANGE), ("5, 1111111111111111111111111", LONGITUDE_RANGE),
        ("11.016823", ENTER_LOCATION), ("1, 2, 3", ENTER_LOCATION), ("north, east", ENTER_LOCATION),
        ("11.0N, 76.9E", ENTER_LOCATION), ("+11, 76", ENTER_LOCATION), ("1e1, 76", ENTER_LOCATION),
        (11.016823, ENTER_LOCATION), ([11, 76], ENTER_LOCATION), (True, ENTER_LOCATION),
    ])
    def test_refusals(self, raw, message):
        assert parse_value("geo", raw) == (None, message)

    @pytest.mark.parametrize("raw", [None, "", "   "])
    def test_blank_clears(self, raw):
        assert parse_value("geo", raw) == (None, None)

    def test_the_messages(self):
        assert ENTER_LOCATION == "Enter the location as latitude, longitude, for example 11.016823, 76.955812"
        assert LATITUDE_RANGE == "The latitude must be between -90 and 90"
        assert LONGITUDE_RANGE == "The longitude must be between -180 and 180"

    def test_stored_value_and_display_drop_trailing_zeros(self):
        row = _geo("11.016800", "76.955800")
        assert stored_value("geo", row) == "11.0168, 76.9558"
        assert format_value("geo", (Decimal("11.016823"), Decimal("-76.000000"))) == "11.016823, -76"
        assert stored_value("geo", _columns()) is None and stored_value("geo", None) is None
        assert format_value("geo", None) is None

    def test_map_url(self):
        assert map_url("geo", _geo("11.016823", "76.955812")) == (
            "https://www.google.com/maps/search/?api=1&query=11.016823,76.955812")
        assert map_url("geo", _geo("11.010000", "76.900000")).endswith("query=11.01,76.9")
        assert map_url("geo", None) is None and map_url("geo", _columns()) is None
        assert map_url("text", _columns(value_text="x")) is None

    def test_check_values_fills_both_columns_and_a_re_save_is_no_change(self):
        props = {4: _prop(4, "GPS location", "geo")}
        changes, error = check_values({"4": "11.016823, 76.955812"}, props, {}, {}, owner=OWNER_ITEM)
        assert error is None and changes == [(4, _geo("11.016823", "76.955812"))]
        # BR1-05: the same location against the stored DECIMALs writes nothing
        assert item_changes(changes, {4: _geo("11.016823", "76.955812")}) == []
        assert item_changes(changes, {4: _geo("11.016824", "76.955812")}) == changes

    def test_a_unit_on_a_location_is_refused(self):
        assert property_changes(None, {"data_type": "geo", "unit": "deg"}) == (None, ("unit", UNIT_ONLY_NUMBER, 400))
        assert validate_property({"name": "GPS", "data_type": "geo"}, True) == ({"name": "GPS", "data_type": "geo"}, [])


class TestFlags:

    @pytest.mark.parametrize("raw, stored", [(True, 1), (False, 0), (1, 1), (0, 0)])
    def test_accepted(self, raw, stored):
        assert validate_property({"all_classes": raw, "per_item_only": raw}, False) == (
            {"all_classes": stored, "per_item_only": stored}, [])

    @pytest.mark.parametrize("raw", ["yes", None, 2, "1"])
    def test_refused(self, raw):
        assert _errors({"all_classes": raw, "per_item_only": raw}, creating=False) == [
            ("all_classes", CHOOSE_YES_OR_NO), ("per_item_only", CHOOSE_YES_OR_NO)]

    def test_a_create_without_the_flags_sends_none(self):
        """The columns default to 0 (§ 5.1)."""
        assert property_changes(None, {"name": "P", "data_type": "text"}) == ({"name": "P", "data_type": "text"}, None)

    def test_turning_per_item_only_on_with_model_values_is_refused(self):
        stored = {"data_type": "geo", "unit": None, "per_item_only": 0}
        assert property_changes(stored, {"per_item_only": 1}, has_values=True, model_has_values=True) == (
            None, ("per_item_only", PER_ITEM_HAS_MODEL_VALUES, 409))
        assert property_changes(stored, {"per_item_only": 1}, has_values=True) == ({"per_item_only": 1}, None)

    def test_turning_it_off_or_keeping_it_on_is_allowed(self):
        stored = {"data_type": "geo", "unit": None, "per_item_only": 1}
        assert property_changes(stored, {"per_item_only": 0}, model_has_values=True) == ({"per_item_only": 0}, None)
        assert property_changes(stored, {"per_item_only": 1}, model_has_values=True) == ({"per_item_only": 1}, None)

    def test_all_classes_changes_at_any_time(self):
        stored = {"data_type": "text", "unit": None, "per_item_only": 0}
        assert property_changes(stored, {"all_classes": 1}, has_values=True, model_has_values=True) == (
            {"all_classes": 1}, None)

    def test_a_per_machine_property_is_refused_on_a_model_only(self):
        props = {4: {**_prop(4, "GPS location", "geo"), "per_item_only": 1}}
        assert check_values({"4": "11, 76"}, props, {}, {}, owner=OWNER_MODEL) == (
            None, ("values.4", SET_ON_EACH_MACHINE))
        assert check_values({"4": "11, 76"}, props, {}, {}, owner=OWNER_ITEM)[1] is None
        assert SET_ON_EACH_MACHINE == "Set this property on each machine, not on the model"

    def test_location_shows_only_on_top_level_equipment(self):
        props = [{"id": 1, "data_type": "geo"}, {"id": 2, "data_type": "number"}]
        assert on_level(props, "equipment") == props
        assert on_level(props, "component_unit") == [props[1]]
        assert on_level(props, "component") == [props[1]]


class TestValueInForceAndHint:

    PROPS = [
        {"id": 1, "name": "GPS location", "data_type": "geo", "unit": None, "per_item_only": 1},
        {"id": 2, "name": "Mobility", "data_type": "choice", "unit": None},
    ]
    LABELS = {7: "Fixed", 8: "Portable", 9: "Mobile", 10: "PORTABLE"}

    def _rows(self, mobility_option=None, gps=True, props=None):
        own = {1: _geo("11.016823", "76.955812")} if gps else {}
        if mobility_option is not None:
            own[2] = _columns(option_id=mobility_option)
        return property_view(props or self.PROPS, {}, self.LABELS, own)

    def test_portable_and_mobile_show_the_hint_fixed_does_not(self):
        assert moving_hint(self._rows(8)) == MOVING_HINT
        assert moving_hint(self._rows(9)) == MOVING_HINT
        assert moving_hint(self._rows(7)) is None
        assert MOVING_HINT == "This machine moves. The location may be out of date."

    def test_mobility_missing_or_without_a_value(self):
        assert moving_hint(self._rows(props=self.PROPS[:1])) is None
        assert moving_hint(self._rows(None)) is None

    def test_gps_without_a_value(self):
        assert moving_hint(self._rows(8, gps=False)) is None

    def test_names_in_other_case(self):
        props = [{**self.PROPS[0]}, {**self.PROPS[1], "name": "MOBILITY"}]
        assert moving_hint(self._rows(10, props=props)) == MOVING_HINT
        assert value_in_force(self._rows(8), "mobility")["display"] == "Portable"
        assert value_in_force(self._rows(None), "Mobility") is None
        assert value_in_force(self._rows(8), "Colour") is None

    def test_the_rows_carry_data_type_per_item_only_and_map_url(self):
        gps = self._rows(8)[0]
        assert (gps["data_type"], gps["per_item_only"], gps["display"], gps["map_url"]) == (
            "geo", True, "11.016823, 76.955812",
            "https://www.google.com/maps/search/?api=1&query=11.016823,76.955812")


def test_a_per_machine_property_s_history_has_no_model_mark():
    """§ 5.6: a per-machine property has no model value, so "no value" carries no "(model)"."""
    props = {1: {"id": 1, "name": "GPS location", "data_type": "geo", "unit": None, "per_item_only": 1}}
    changes = [(1, _geo("11.016823", "76.955812"))]
    assert item_events(props, changes, {}, {1: None}, {}, True) == [
        ("property", "GPS location: no value", "GPS location: 11.016823, 76.955812")]
    assert item_events(props, [(1, None)], {1: _geo("11.016823", "76.955812")}, {1: None}, {}, True) == [
        ("property", "GPS location: 11.016823, 76.955812", "GPS location: no value")]
