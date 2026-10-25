"""meters_core (S038 § 5.1, § 5.2, § 5.5): limits validation, a node's meters, the wording; the
reading rules (S039 § 5.1, § 5.2)."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from meters_core import (
    ACTION_LIMITS, ACTION_REMOVE, ACTION_USE_MODEL, NO_LIMITS, SOURCE_MODEL, SOURCE_NODE, answer_state,
    answer_word, counter_error, effective_meters, format_number, grouped_number, in_force_pair, limit_state,
    limits_text, may_remove, override_of, parse_change_action, parse_meter_type_id, parse_reading_request,
    parse_meter_type_ids, parse_taken_at, reading_text, reading_time_error, register_columns, register_rows,
    reset_removal_error, same_limits, shown_meter_ids, to_minute, tracked_meter_change, validate_limits,
    validate_reading,
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


# ---------------------------------------------------------------------------
# Readings (S039 § 5.1, § 5.2)
# ---------------------------------------------------------------------------

NOW = datetime(2026, 10, 24, 18, 0)


def _reading(value, kind="counter", decimals=1, reset=False, note=None):
    return validate_reading(value, kind, decimals, reset, note)


def _reading_error(value, **kw):
    errors = _reading(value, **kw)[1]
    assert len(errors) == 1, errors
    return errors[0]["field"], errors[0]["message"]


class TestValidateReading:
    def test_a_counter_reading_is_a_decimal_and_the_note_is_trimmed(self):
        clean, errors = _reading("12345.6", note="  after the shift ")
        assert errors == []
        assert clean == {"value": D("12345.6"), "is_reset": False, "note": "after the shift"}
        assert _reading(42, decimals=0)[0]["value"] == D(42)

    def test_an_empty_note_is_none(self):
        assert _reading("1", note="   ")[0]["note"] is None

    @pytest.mark.parametrize("value", [None, "", "   "])
    def test_a_missing_value(self, value):
        assert _reading_error(value) == ("value", "Enter the reading")

    @pytest.mark.parametrize("value, decimals, message", [
        ("abc", 1, "Enter a number with up to 1 decimal"),
        (True, 2, "Enter a number with up to 2 decimals"),
        (12.5, 3, "Enter a number with up to 3 decimals"),
        ("1.5", 0, "Enter a whole number"),
        ("1.25", 1, "Enter a number with up to 1 decimal"),     # more decimals than the type's (BR1-11)
        ("1e3", 1, "Enter a number with up to 1 decimal"),
    ])
    def test_not_a_number_of_the_types_decimals(self, value, decimals, message):
        assert _reading_error(value, decimals=decimals) == ("value", message)

    def test_beyond_the_column(self):
        assert _reading_error("100000000000", decimals=0) == ("value", "Enter a smaller number")
        assert _reading("99999999999.999", decimals=3)[1] == []

    def test_below_zero(self):
        assert _reading_error("-1") == ("value", "A counter cannot be below zero")
        assert _reading_error("-1", kind="amount", decimals=0) == ("value", "An amount cannot be below zero")
        assert _reading("-5.5", kind="gauge")[1] == []                 # a gauge may read below zero
        assert _reading("0")[1] == []

    def test_only_a_counter_is_reset(self):
        assert _reading("5", reset=True)[0]["is_reset"] is True
        for kind in ("gauge", "amount"):
            assert _reading_error("5", kind=kind, reset=True) == ("is_reset", "Only a counter can be reset")
        assert _reading_error("yes", kind="yes_no", decimals=0, reset=True) == (
            "is_reset", "Only a counter can be reset")

    @pytest.mark.parametrize("reset", [None, "true", 1])
    def test_reset_must_be_a_bool(self, reset):
        assert _reading_error("5", reset=reset) == ("is_reset", "Meter reset must be true or false")

    def test_the_note(self):
        assert _reading("5", note="x" * 200)[1] == []
        assert _reading_error("5", note="x" * 201) == ("note", "Note must be at most 200 characters")
        assert _reading_error("5", note=5) == ("note", "Note must be text")

    def test_an_amount_has_no_order_and_no_reset(self):
        assert _reading("420", kind="amount", decimals=0) == ({"value": D(420), "is_reset": False, "note": None}, [])

    def test_a_yes_no_answer_is_stored_as_1_or_0(self):
        """BR3-04: the word ↔ number mapping; no number rule fires on a Yes / No meter (BR3-05)."""
        assert _reading("yes", kind="yes_no", decimals=0)[0]["value"] == D(1)
        assert _reading("no", kind="yes_no", decimals=0)[0]["value"] == D(0)
        assert (answer_word(D(1)), answer_word(D("0.000"))) == ("yes", "no")

    @pytest.mark.parametrize("value", ["maybe", 1, True, "1", "Yes", None, ""])
    def test_a_yes_no_meter_takes_only_the_words(self, value):
        assert _reading_error(value, kind="yes_no", decimals=0) == ("value", "Pick Yes or No")


class TestReadingTime:
    def test_seven_days_back_exactly_is_allowed_and_a_minute_more_is_not(self):
        assert reading_time_error(NOW - timedelta(days=7), NOW) is None
        assert reading_time_error(NOW - timedelta(days=7, minutes=1), NOW) == "When was it read? Up to 7 days back"

    def test_five_minutes_ahead_is_allowed_and_six_are_not(self):
        assert reading_time_error(NOW + timedelta(minutes=5), NOW) is None
        assert reading_time_error(NOW + timedelta(minutes=6), NOW) == "That time is in the future"

    def test_absent_is_now(self):
        assert parse_taken_at(None, NOW) == (NOW, None)

    def test_a_time_is_kept_to_its_minute(self):
        assert parse_taken_at("2026-10-24T17:30:45", NOW) == (datetime(2026, 10, 24, 17, 30), None)
        assert parse_taken_at("2026-10-24 17:30", NOW) == (datetime(2026, 10, 24, 17, 30), None)

    @pytest.mark.parametrize("raw", ["24-10-2026 17:30", "2026-10-24T17:30Z", "", 5])
    def test_a_wrong_format(self, raw):
        assert parse_taken_at(raw, NOW) == (None, "Enter the time as YYYY-MM-DD HH:MM")

    def test_too_old_and_in_the_future(self):
        assert parse_taken_at("2026-10-16T18:00", NOW) == (None, "When was it read? Up to 7 days back")
        assert parse_taken_at("2026-10-24T19:00", NOW) == (None, "That time is in the future")

    def test_to_minute(self):
        assert to_minute(datetime(2026, 10, 24, 18, 0, 59, 999)) == NOW

    def test_the_request_names_a_meter_and_a_time(self):
        assert parse_reading_request({"meter_type_id": 3}, NOW) == ({"meter_type_id": 3, "taken_at": NOW}, [])
        clean, errors = parse_reading_request({"meter_type_id": "3", "taken_at": "2026-10-24T19:00"}, NOW)
        assert errors == [{"field": "meter_type_id", "message": "Pick a meter"},
                          {"field": "taken_at", "message": "That time is in the future"}]


def _at(value, hour, day=23, reset=False):
    return {"value": D(value), "taken_at": datetime(2026, 10, day, hour, 0), "is_reset": reset}


class TestCounterOrder:
    def test_between_its_neighbours_and_equal_values_pass(self):
        assert counter_error(D("150"), False, _at("100", 8), _at("200", 18), HOURS) is None
        assert counter_error(D("100"), False, _at("100", 8), _at("100", 18), HOURS) is None

    def test_no_neighbours(self):
        assert counter_error(D("5"), False, None, None, HOURS) is None

    def test_lower_than_the_one_before(self):
        assert counter_error(D("12000"), False, _at("12345.6", 18), None, HOURS) == (
            "value", "Lower than the reading of 23-10-2026 18:00 (12,345.6 h). Check the value, or tick Meter reset"
                     " if the meter was reset.", "counter_lower")

    def test_higher_than_the_one_after(self):
        assert counter_error(D("12400"), False, None, _at("12350", 8, day=24), HOURS) == (
            "value", "Higher than the later reading of 24-10-2026 08:00 (12,350.0 h). Check the value and the time.",
            None)

    def test_both_neighbours_the_earlier_one_is_named_first(self):
        assert counter_error(D("50"), False, _at("100", 8), _at("40", 18), HOURS)[2] == "counter_lower"

    def test_a_reset_lower_than_the_one_before_passes(self):
        assert counter_error(D("3"), True, _at("12345.6", 8), None, HOURS) is None

    def test_a_reset_equal_to_the_one_before_passes(self):
        """BR2-13: a replaced meter that reads 0 after a reading of 0."""
        assert counter_error(D("0"), True, _at("0", 8), None, HOURS) is None

    def test_a_reset_higher_than_the_one_before_is_refused(self):
        assert counter_error(D("200"), True, _at("100", 8), None, HOURS) == (
            "is_reset", "A reset reads lower than the reading before it. Untick Meter reset.", None)

    def test_a_reset_with_no_earlier_reading_passes(self):
        assert counter_error(D("500"), True, None, None, HOURS) is None

    def test_a_reset_with_a_later_reading_must_not_be_above_it(self):
        """BR1-18: a reset is still checked against the one after."""
        assert counter_error(D("3"), True, _at("100", 8), _at("10", 18), HOURS) is None
        assert counter_error(D("30"), True, _at("100", 8), _at("10", 18), HOURS)[0] == "value"

    def test_a_later_reset_does_not_bound_the_value(self):
        """BR1-18: the reading after is a reset, so it may read lower."""
        assert counter_error(D("150"), False, _at("100", 8), _at("2", 18, reset=True), HOURS) is None


class TestLimitsAndAnswers:
    @pytest.mark.parametrize("value, low, high, state", [
        ("5", "10", None, "low"),
        ("65", None, "60", "high"),
        ("65", "10", "60", "high"),
        ("5", "10", "60", "low"),
        ("30", "10", "60", None),
        ("60", "10", "60", None),            # equal to a limit is inside
        ("10", "10", "60", None),
        ("1000", None, None, None),
    ])
    def test_limit_state(self, value, low, high, state):
        assert limit_state(D(value), low, high) == state

    @pytest.mark.parametrize("answer, expected, state", [
        ("yes", "yes", None), ("no", "yes", "not_ok"), ("no", "no", None), ("yes", "no", "not_ok"),
    ])
    def test_answer_state(self, answer, expected, state):
        assert answer_state(answer, expected) == state


class TestRemoval:
    def test_may_remove_needs_equipment_edit_and_an_active_reading(self):
        active, removed = {"removed_at": None}, {"removed_at": datetime(2026, 10, 24, 9, 0)}
        assert may_remove(active, can_edit=True) is True
        assert may_remove(active, can_edit=False) is False
        assert may_remove(removed, can_edit=True) is False

    def test_a_reset_with_a_later_reading_cannot_be_removed(self):
        assert reset_removal_error({"is_reset": 1}, has_later=True) == (
            "This reading marks a meter reset. Remove the later readings first.")
        assert reset_removal_error({"is_reset": 1}, has_later=False) is None
        assert reset_removal_error({"is_reset": 0}, has_later=True) is None


class TestReadingWords:
    @pytest.mark.parametrize("value, decimals, text", [
        ("12345.6", 1, "12,345.6"), ("12350", 1, "12,350.0"), ("1234567.8", 1, "12,34,567.8"),
        ("420", 0, "420"), ("-1234.5", 1, "-1,234.5"), ("0", 2, "0.00"),
    ])
    def test_indian_grouping_with_the_types_decimals(self, value, decimals, text):
        assert grouped_number(D(value), decimals) == text

    def test_reading_text(self):
        assert reading_text(D("12345.6"), HOURS) == "12,345.6 h"
        assert reading_text(D("420"), SHIFT) == "420 pcs"
        assert reading_text(D("0"), OIL_OK) == "No"


# ---------------------------------------------------------------------------
# The reading register (S050 § 5.1, § 5.2, § 5.5)
# ---------------------------------------------------------------------------

def _in_force(meter_type, low=None, high=None):
    return {"meter_type": meter_type, "min_value": low, "max_value": high}


def _column(meter_type, in_force=True):
    return {"meter_type": meter_type, "in_force": in_force, "min_value": None, "max_value": None}


def _row(reading_id, meter_type, value, minute, limit_state=None, is_reset=0):
    return {"id": reading_id, "meter_type_id": meter_type["id"], "value": D(value),
            "taken_at": datetime(2026, 10, 23, 18, minute), "is_reset": is_reset, "limit_state": limit_state}


class TestRegisterColumns:
    def test_the_meters_in_force_in_their_order(self):
        columns = register_columns([_in_force(OIL, "10", "60"), _in_force(HOURS)], [OIL])
        assert [(c["meter_type"]["id"], c["in_force"]) for c in columns] == [(6, True), (1, True)]
        assert (columns[0]["min_value"], columns[0]["max_value"]) == ("10", "60")

    def test_a_type_read_but_no_longer_on_the_node_comes_after_by_name(self):
        columns = register_columns([_in_force(HOURS)], [SHIFT, HOURS, FUEL])
        assert [(c["meter_type"]["name"], c["in_force"]) for c in columns] == [
            ("Run hours", True), ("Fuel level", False), ("Shift production", False)]
        assert columns[1]["min_value"] is None and columns[1]["max_value"] is None

    def test_a_type_without_an_active_reading_and_not_in_force_is_no_column(self):
        # read_types holds only types with an active reading: one with removed readings only is absent
        assert register_columns([], []) == []
        assert [c["meter_type"]["id"] for c in register_columns([_in_force(HOURS)], [])] == [1]


class TestShownMeterIds:
    COLUMNS = [_column(OIL), _column(HOURS), _column(SHIFT, in_force=False)]

    def test_all_when_none_is_asked(self):
        assert shown_meter_ids(self.COLUMNS, None) == [6, 1, 8]

    def test_the_asked_columns_in_column_order(self):
        assert shown_meter_ids(self.COLUMNS, [8, 6]) == [6, 8]

    def test_an_id_that_is_no_column_is_ignored(self):
        assert shown_meter_ids(self.COLUMNS, [1, 99]) == [1]

    def test_only_stale_ids_show_all(self):
        assert shown_meter_ids(self.COLUMNS, [99]) == [6, 1, 8]

    def test_no_columns(self):
        assert shown_meter_ids([], [3]) == []


class TestRegisterRows:
    COLUMNS = [_column(OIL), _column(HOURS), _column(OIL_OK)]

    def test_one_row_per_minute_newest_first_a_cell_per_meter(self):
        readings = [
            _row(1, HOURS, "100.0", 0), _row(2, OIL, "55.0", 0), _row(3, OIL_OK, "1", 0),
            _row(4, HOURS, "108.5", 30), _row(5, OIL, "62.0", 30, limit_state="high"),
            _row(6, HOURS, "0", 45, is_reset=1),
        ]
        rows = register_rows(readings, self.COLUMNS)
        assert [r["taken_at"].minute for r in rows] == [45, 30, 0]
        assert rows[0]["cells"] == {1: {"id": 6, "value": "0", "limit_state": None, "is_reset": True}}
        assert rows[1]["cells"][6] == {"id": 5, "value": "62", "limit_state": "high", "is_reset": False}
        assert rows[1]["cells"][1]["value"] == "108.5"
        assert set(rows[2]["cells"]) == {1, 6, 9}

    def test_a_yes_no_value_comes_back_as_its_word(self):
        rows = register_rows([_row(1, OIL_OK, "1", 0), _row(2, OIL_OK, "0", 5, limit_state="not_ok")], self.COLUMNS)
        assert [r["cells"][9]["value"] for r in rows] == ["no", "yes"]
        assert rows[0]["cells"][9]["limit_state"] == "not_ok"

    def test_no_readings_no_rows(self):
        assert register_rows([], self.COLUMNS) == []

    def test_two_readings_of_one_meter_at_one_minute_the_higher_id_wins(self):
        rows = register_rows([_row(9, HOURS, "120", 0), _row(4, HOURS, "110", 0)], self.COLUMNS)
        assert len(rows) == 1 and rows[0]["cells"][1]["id"] == 9 and rows[0]["cells"][1]["value"] == "120"

    def test_a_reading_of_a_meter_that_is_no_column_is_left_out(self):
        assert register_rows([_row(1, SHIFT, "400", 0)], self.COLUMNS) == []


class TestParseMeterTypeIds:
    @pytest.mark.parametrize("raw", [None, "", "  "])
    def test_absent_or_empty_is_all(self, raw):
        assert parse_meter_type_ids(raw) == (None, [])

    @pytest.mark.parametrize("raw, ids", [("3,7", [3, 7]), ("3,3", [3]), (" 3 , 7 ", [3, 7]), ("7,3,7", [7, 3])])
    def test_a_comma_list(self, raw, ids):
        assert parse_meter_type_ids(raw) == (ids, [])

    @pytest.mark.parametrize("raw", ["3,x", "3,", "0", "-1", "x", "3.5", "٣"])
    def test_a_malformed_list_is_refused(self, raw):
        assert parse_meter_type_ids(raw) == (None, [{"field": "meter_type_ids", "message": "Pick a meter"}])
