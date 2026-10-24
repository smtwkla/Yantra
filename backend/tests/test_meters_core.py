"""meters_core (S038 § 5.1, § 5.2, § 5.5): limits validation, a node's meters, the wording."""

from decimal import Decimal

import pytest

from meters_core import (
    ACTION_LIMITS, ACTION_REMOVE, ACTION_USE_MODEL, NO_LIMITS, SOURCE_MODEL, SOURCE_NODE, effective_meters,
    format_number, in_force_pair, limits_text, override_of, parse_change_action, parse_meter_type_id,
    same_limits, tracked_meter_change, validate_limits,
)

D = Decimal
OIL = {"id": 6, "name": "Oil temperature", "unit": "°C", "kind": "gauge", "decimals": 1, "expected_answer": None}
FUEL = {"id": 7, "name": "Fuel level", "unit": "%", "kind": "gauge", "decimals": 0, "expected_answer": None}
HOURS = {"id": 1, "name": "Run hours", "unit": "h", "kind": "counter", "decimals": 1, "expected_answer": None}
SHIFT = {"id": 8, "name": "Shift production", "unit": "pcs", "kind": "amount", "decimals": 0, "expected_answer": None}
OIL_OK = {"id": 9, "name": "Oil level above min", "unit": None, "kind": "yes_no", "decimals": 0,
          "expected_answer": "yes"}


def _errors(body, kind="gauge", decimals=1, stored=NO_LIMITS):
    return validate_limits(body, kind, decimals, stored)[1]


def _message(body, **kw):
    errors = _errors(body, **kw)
    assert len(errors) == 1, errors
    return errors[0]["field"], errors[0]["message"]


class TestValidateLimits:
    def test_decimal_strings_and_integers_are_accepted_as_decimals(self):
        pair, errors = validate_limits({"min_value": "10", "max_value": "62.5"}, "gauge", 1, NO_LIMITS)
        assert errors == [] and pair == (D("10"), D("62.5"))
        pair, errors = validate_limits({"min_value": -5, "max_value": 60}, "gauge", 0, NO_LIMITS)
        assert errors == [] and pair == (D("-5"), D("60"))

    def test_trailing_zeros_are_not_decimals(self):
        pair, errors = validate_limits({"max_value": "62.50"}, "gauge", 1, NO_LIMITS)
        assert errors == [] and pair == (None, D("62.5"))

    @pytest.mark.parametrize("value", [True, False, 62.5, "abc", "1e3", "", " ", "NaN", "62.", ".5", [1], {}])
    def test_not_a_decimal_number_is_refused(self, value):
        assert _message({"min_value": value}) == ("min_value", "Enter a number with up to 1 decimal")

    def test_too_many_decimals_names_the_type_s_decimals(self):
        assert _message({"max_value": "62.55"}) == ("max_value", "Enter a number with up to 1 decimal")
        assert _message({"max_value": "1.2345"}, decimals=3) == ("max_value", "Enter a number with up to 3 decimals")

    def test_a_0_decimal_type_asks_for_a_whole_number(self):
        assert _message({"min_value": "2.5"}, decimals=0) == ("min_value", "Enter a whole number")
        assert _message({"min_value": 2.0}, decimals=0) == ("min_value", "Enter a whole number")

    def test_a_number_beyond_the_column_is_refused(self):
        assert _message({"max_value": "100000000000"}, decimals=0) == ("max_value", "Enter a smaller number")
        assert _message({"min_value": "-100000000000"}, decimals=0) == ("min_value", "Enter a smaller number")
        assert _errors({"max_value": "99999999999.999"}, decimals=3) == []

    def test_min_above_max_is_refused_on_max(self):
        assert _message({"min_value": "60", "max_value": "10"}) == ("max_value", "Min must not be above Max")

    def test_min_equal_to_max_passes(self):
        assert _errors({"min_value": "10", "max_value": "10"}) == []

    def test_an_absent_field_keeps_the_stored_value_and_null_clears_it(self):
        stored = (D("10"), D("60"))
        assert validate_limits({"max_value": "55"}, "gauge", 1, stored) == ((D("10"), D("55")), [])
        assert validate_limits({"min_value": None}, "gauge", 1, stored) == ((None, D("60")), [])
        assert validate_limits({}, "gauge", 1, stored) == (stored, [])

    def test_a_one_sided_update_is_checked_against_the_stored_other_side(self):
        assert _message({"min_value": "70"}, stored=(D("10"), D("60"))) == ("max_value", "Min must not be above Max")

    def test_each_start_point(self):
        # a row's own pair, the model's (a first override), NULLs (a create)
        assert validate_limits({"max_value": "50"}, "gauge", 1, (D("20"), D("55")))[0] == (D("20"), D("50"))
        assert validate_limits({"max_value": "50"}, "gauge", 1, (D("10"), D("60")))[0] == (D("10"), D("50"))
        assert validate_limits({"max_value": "50"}, "gauge", 1, NO_LIMITS)[0] == (None, D("50"))

    @pytest.mark.parametrize("kind, message", [
        ("counter", "A counter has no limits"),
        ("amount", "An amount per period has no limits"),
        ("yes_no", "A Yes / No meter has no limits"),
    ])
    def test_a_limit_on_a_non_gauge_is_refused(self, kind, message):
        assert _message({"max_value": "5"}, kind=kind) == ("max_value", message)
        assert _message({"min_value": 5}, kind=kind) == ("min_value", message)

    def test_the_kind_check_comes_before_the_number_check(self):
        assert _message({"min_value": "abc"}, kind="counter") == ("min_value", "A counter has no limits")

    @pytest.mark.parametrize("kind", ["counter", "amount", "yes_no"])
    def test_an_explicit_null_on_a_non_gauge_passes(self, kind):
        assert validate_limits({"min_value": None, "max_value": None}, kind, 0, NO_LIMITS) == (NO_LIMITS, [])


class TestParse:
    @pytest.mark.parametrize("body", [{}, {"meter_type_id": None}, {"meter_type_id": "6"},
                                      {"meter_type_id": True}, {"meter_type_id": 0}, {"meter_type_id": 1.0}])
    def test_meter_type_id_must_be_an_id(self, body):
        assert parse_meter_type_id(body) == (None, [{"field": "meter_type_id", "message": "Pick a meter type"}])

    def test_meter_type_id(self):
        assert parse_meter_type_id({"meter_type_id": 6}) == (6, [])

    def test_actions(self):
        assert parse_change_action({"active": False}, True) == (ACTION_REMOVE, [])
        assert parse_change_action({"use_model_limits": True}, True) == (ACTION_USE_MODEL, [])
        assert parse_change_action({"min_value": "1"}, True) == (ACTION_LIMITS, [])
        assert parse_change_action({}, False) == (ACTION_LIMITS, [])

    @pytest.mark.parametrize("body, allow, field", [
        ({"active": True}, True, "active"),
        ({"active": 0}, True, "active"),
        ({"active": False, "max_value": "5"}, True, "active"),
        ({"use_model_limits": False}, True, "use_model_limits"),
        ({"use_model_limits": True}, False, "use_model_limits"),
        ({"use_model_limits": True, "min_value": None}, True, "use_model_limits"),
    ])
    def test_refused_actions(self, body, allow, field):
        action, errors = parse_change_action(body, allow)
        assert action is None and errors[0]["field"] == field


class TestWording:
    @pytest.mark.parametrize("pair, text", [
        ((D("10.000"), D("60.000")), "Limits: 10–60 °C"),
        ((None, D("60")), "Limits: up to 60 °C"),
        ((D("10"), None), "Limits: from 10 °C"),
        ((D("-5.5"), D("62.5")), "Limits: -5.5–62.5 °C"),
        (NO_LIMITS, "No limits"),
    ])
    def test_the_gauge_wordings(self, pair, text):
        assert limits_text(OIL, pair) == text

    @pytest.mark.parametrize("meter_type", [HOURS, SHIFT, OIL_OK])
    def test_a_non_gauge_has_no_limits_line(self, meter_type):
        assert limits_text(meter_type, NO_LIMITS) is None

    def test_format_number(self):
        assert [format_number(v) for v in (D("10.000"), D("62.500"), D("100"), D("0.000"), D("-0.000"), None)] == \
            ["10", "62.5", "100", "0", "0", None]

    def test_setting_an_override_shows_both_sides_in_force(self):
        assert tracked_meter_change(OIL, (D("10"), D("60")), (None, D("55"))) == [
            ("meter_limits", "Oil temperature: 10–60 °C", "Oil temperature: up to 55 °C")]

    def test_clearing_an_override_writes_the_reverse(self):
        assert tracked_meter_change(OIL, (None, D("55")), (D("10"), D("60"))) == [
            ("meter_limits", "Oil temperature: up to 55 °C", "Oil temperature: 10–60 °C")]

    def test_no_limits_reads_no_limits_and_an_unchanged_pair_writes_nothing(self):
        assert tracked_meter_change(OIL, NO_LIMITS, (D("1"), None)) == [
            ("meter_limits", "Oil temperature: no limits", "Oil temperature: from 1 °C")]
        assert tracked_meter_change(OIL, (D("10.000"), None), (D("10"), None)) == []

    def test_same_limits(self):
        assert same_limits((D("10.000"), None), (D("10"), None))
        assert not same_limits((D("10"), None), (None, D("10")))


def _model(meter_type, low=None, high=None, active=1):
    return {"meter_type": meter_type, "min_value": low, "max_value": high, "active": active}


def _node(meter_type, own, low=None, high=None, active=1):
    return {**_model(meter_type, low, high, active), "own": own}


def _by_name(meters):
    return {m["meter_type"]["name"]: m for m in meters}


class TestEffectiveMeters:
    def test_no_model_and_no_rows(self):
        assert effective_meters([], []) == []

    def test_model_meters_with_their_limits_ordered_by_name(self):
        meters = effective_meters([_model(OIL, D("10"), D("60")), _model(FUEL), _model(HOURS)], [])
        assert [m["meter_type"]["name"] for m in meters] == ["Fuel level", "Oil temperature", "Run hours"]
        oil = _by_name(meters)["Oil temperature"]
        assert oil == {"meter_type": OIL, "source": SOURCE_MODEL, "min_value": "10", "max_value": "60",
                       "model_min": "10", "model_max": "60", "overridden": False,
                       "limits_text": "Limits: 10–60 °C", "model_limits_text": "Limits: 10–60 °C"}
        assert _by_name(meters)["Run hours"]["limits_text"] is None

    def test_an_override_wins_over_the_model(self):
        oil = effective_meters([_model(OIL, D("10"), D("60"))], [_node(OIL, 0, None, D("55"))])[0]
        assert (oil["min_value"], oil["max_value"], oil["overridden"]) == (None, "55", True)
        assert (oil["model_min"], oil["model_max"]) == ("10", "60")
        assert oil["limits_text"] == "Limits: up to 55 °C" and oil["model_limits_text"] == "Limits: 10–60 °C"

    def test_an_override_with_no_limits_is_still_an_override(self):
        oil = effective_meters([_model(OIL, D("10"), D("60"))], [_node(OIL, 0)])[0]
        assert oil["overridden"] and oil["limits_text"] == "No limits"

    def test_a_stale_override_is_left_out(self):
        assert effective_meters([], [_node(OIL, 0, None, D("55"))]) == []
        # the model's meter removed (inactive): the override goes with it
        assert effective_meters([_model(OIL, D("10"), D("60"), active=0)], [_node(OIL, 0, None, D("55"))]) == []

    def test_an_own_meter(self):
        meters = effective_meters([_model(OIL)], [_node(HOURS, 1)])
        hours = _by_name(meters)["Run hours"]
        assert hours == {"meter_type": HOURS, "source": SOURCE_NODE, "min_value": None, "max_value": None,
                         "model_min": None, "model_max": None, "overridden": False, "limits_text": None,
                         "model_limits_text": None}

    def test_a_removed_own_meter_is_left_out(self):
        assert effective_meters([], [_node(FUEL, 1, active=0)]) == []

    def test_an_own_meter_the_model_gains_later_shows_once_as_the_model_s(self):
        meters = effective_meters([_model(OIL, D("10"), D("60"))], [_node(OIL, 1, D("20"), D("50"))])
        assert len(meters) == 1
        oil = meters[0]
        assert (oil["source"], oil["min_value"], oil["max_value"], oil["overridden"]) == (SOURCE_MODEL, "20", "50", True)

    def test_an_own_row_with_no_limits_under_a_model_meter_is_no_override(self):
        oil = effective_meters([_model(OIL, D("10"), D("60"))], [_node(OIL, 1)])[0]
        assert (oil["source"], oil["overridden"], oil["min_value"]) == (SOURCE_MODEL, False, "10")

    def test_an_inactive_own_row_still_holds_the_override_of_a_model_meter(self):
        oil = effective_meters([_model(OIL, D("10"), D("60"))], [_node(OIL, 1, None, D("50"), active=0)])[0]
        assert (oil["overridden"], oil["max_value"]) == (True, "50")

    def test_an_inactive_model_row_and_an_active_own_row_of_its_type_shows_the_own(self):
        meters = effective_meters([_model(OIL, D("10"), D("60"), active=0)], [_node(OIL, 1, None, D("50"))])
        assert [(m["source"], m["max_value"]) for m in meters] == [(SOURCE_NODE, "50")]


class TestInForce:
    def test_in_force_pair(self):
        model = _model(OIL, D("10"), D("60"))
        assert in_force_pair(model, None) == (D("10"), D("60"))
        assert in_force_pair(model, _node(OIL, 0, None, D("5"))) == (None, D("5"))
        assert in_force_pair(model, _node(OIL, 1)) == (D("10"), D("60"))
        assert in_force_pair(None, _node(OIL, 1, D("1"), None)) == (D("1"), None)
        assert in_force_pair(None, None) == NO_LIMITS

    def test_override_of(self):
        assert override_of(None) is None
        assert override_of(_node(OIL, 0)) == NO_LIMITS
        assert override_of(_node(OIL, 1)) is None
        assert override_of(_node(OIL, 1, D("1"), None, active=0)) == (D("1"), None)
