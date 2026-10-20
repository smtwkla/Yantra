"""Tickets — pure rules (S017 § 8, no DB)."""

from datetime import datetime, timedelta

import pytest

from tickets_core import (
    DESCRIPTION_MAX, DESCRIPTION_NEEDED, DESCRIPTION_NEEDED_OTHER, EVENT_TIME_BEFORE_LAST, EVENT_TIME_FORMAT,
    EVENT_TIME_FUTURE, EVENT_TIME_TOO_OLD, INTENSITIES, INTENSITY_FILTERS, OPEN_STATES, STATES, description_error,
    event_time_error, format_ticket_serial, is_breakdown, machine_and_component, parse_event_time, serial_scope,
    validate_raise,
)

NOW = datetime(2026, 10, 20, 14, 30, 0)


def _fields(errors):
    return [e["field"] for e in errors]


class TestSerial:

    @pytest.mark.parametrize("number, serial", [
        (1, "TK-2026-10-001"), (999, "TK-2026-10-999"), (1000, "TK-2026-10-1000"),
    ])
    def test_three_digits_growing_to_four(self, number, serial):
        assert format_ticket_serial(2026, 10, number) == serial

    def test_month_is_zero_padded(self):
        assert format_ticket_serial(2027, 1, 7) == "TK-2027-01-007"

    def test_scope(self):
        assert serial_scope(2026, 10) == "TK:2026-10"
        assert serial_scope(2027, 3) == "TK:2027-03"


class TestStates:

    def test_open_states_are_every_state_but_closed(self):
        assert OPEN_STATES == ("raised", "acknowledged", "in_progress", "back_in_service")
        assert set(STATES) - set(OPEN_STATES) == {"closed"}

    def test_intensity_filters(self):
        assert INTENSITY_FILTERS["breakdown"] == ("critical",)
        assert INTENSITY_FILTERS["defect"] == ("degraded", "initial")
        assert INTENSITY_FILTERS["initial"] == ("initial",)

    def test_is_breakdown(self):
        assert is_breakdown("critical")
        assert not is_breakdown("degraded") and not is_breakdown("initial")


class TestParseEventTime:

    @pytest.mark.parametrize("text, expected", [
        ("2026-10-20T14:05", datetime(2026, 10, 20, 14, 5)),
        ("2026-10-20 14:05", datetime(2026, 10, 20, 14, 5)),
        ("2026-10-20T14:05:30", datetime(2026, 10, 20, 14, 5, 30)),
        ("2026-10-20 14:05:30", datetime(2026, 10, 20, 14, 5, 30)),
        (" 2026-10-20T14:05 ", datetime(2026, 10, 20, 14, 5)),
    ])
    def test_local_times_are_read(self, text, expected):
        assert parse_event_time(text) == (expected, None)

    @pytest.mark.parametrize("text", [
        "2026-10-20T14:05:00Z", "2026-10-20T14:05+05:30", "2026-10-20T14:05:00+00:00",   # offsets
        "20-10-2026 14:05", "2026-10-20", "yesterday", "", "2026-13-01T10:00", "2026-02-30T10:00",
        "2026-10-20T25:00", None, 12345,
    ])
    def test_offsets_and_garbage_are_refused(self, text):
        assert parse_event_time(text) == (None, EVENT_TIME_FORMAT)


class TestEventTimeWindow:

    def test_now_is_accepted(self):
        assert event_time_error(NOW, NOW) is None

    def test_four_minutes_ahead_is_accepted(self):
        assert event_time_error(NOW + timedelta(minutes=4), NOW) is None

    def test_six_minutes_ahead_is_refused(self):
        assert event_time_error(NOW + timedelta(minutes=6), NOW) == EVENT_TIME_FUTURE

    def test_seven_days_back_is_accepted(self):
        assert event_time_error(NOW - timedelta(days=7), NOW) is None

    def test_eight_days_back_is_refused(self):
        assert event_time_error(NOW - timedelta(days=8), NOW) == EVENT_TIME_TOO_OLD
        assert "7 days" in EVENT_TIME_TOO_OLD

    def test_not_before_refuses_an_earlier_time(self):
        last = NOW - timedelta(hours=1)
        assert event_time_error(NOW - timedelta(hours=2), NOW, not_before=last) == EVENT_TIME_BEFORE_LAST
        assert event_time_error(last, NOW, not_before=last) is None
        assert event_time_error(NOW, NOW, not_before=last) is None


class TestValidateRaise:

    BODY = {"equipment_id": 5, "intensity": "critical"}

    @pytest.mark.parametrize("intensity", INTENSITIES)
    def test_each_intensity(self, intensity):
        clean, errors = validate_raise({**self.BODY, "intensity": intensity}, NOW)
        assert errors == []
        assert clean == {"equipment_id": 5, "intensity": intensity, "failure_mode_id": None,
                         "reported_by_id": None, "description": None, "occurred_at": NOW}

    @pytest.mark.parametrize("intensity", [None, "", "breakdown", "CRITICAL", 1])
    def test_missing_or_unknown_intensity(self, intensity):
        body = {"equipment_id": 5} if intensity is None else {**self.BODY, "intensity": intensity}
        assert _fields(validate_raise(body, NOW)[1]) == ["intensity"]

    @pytest.mark.parametrize("equipment_id", [None, 0, -1, "5", True, 1.5])
    def test_missing_or_bad_equipment_id(self, equipment_id):
        body = {"intensity": "critical"} if equipment_id is None else {**self.BODY, "equipment_id": equipment_id}
        assert _fields(validate_raise(body, NOW)[1]) == ["equipment_id"]

    def test_description_is_trimmed_and_empty_is_none(self):
        assert validate_raise({**self.BODY, "description": "  oil leak  "}, NOW)[0]["description"] == "oil leak"
        assert validate_raise({**self.BODY, "description": "   "}, NOW)[0]["description"] is None

    def test_description_too_long(self):
        assert validate_raise({**self.BODY, "description": "x" * DESCRIPTION_MAX}, NOW)[1] == []
        assert _fields(validate_raise({**self.BODY, "description": "x" * (DESCRIPTION_MAX + 1)}, NOW)[1]) == [
            "description"]

    def test_description_must_be_text(self):
        assert _fields(validate_raise({**self.BODY, "description": 12}, NOW)[1]) == ["description"]

    @pytest.mark.parametrize("field", ["failure_mode_id", "reported_by_id"])
    def test_optional_ids(self, field):
        assert validate_raise({**self.BODY, field: 9}, NOW)[0][field] == 9
        assert validate_raise({**self.BODY, field: None}, NOW)[0][field] is None
        for bad in ("9", 0, True):
            assert _fields(validate_raise({**self.BODY, field: bad}, NOW)[1]) == [field]

    def test_occurred_at_given(self):
        clean, errors = validate_raise({**self.BODY, "occurred_at": "2026-10-18T09:15"}, NOW)
        assert errors == [] and clean["occurred_at"] == datetime(2026, 10, 18, 9, 15)

    @pytest.mark.parametrize("text, message", [
        ("2026-10-20T14:05:00+05:30", EVENT_TIME_FORMAT),
        ("2026-10-20T15:00", EVENT_TIME_FUTURE),
        ("2026-10-10T10:00", EVENT_TIME_TOO_OLD),
    ])
    def test_occurred_at_refused(self, text, message):
        _, errors = validate_raise({**self.BODY, "occurred_at": text}, NOW)
        assert errors == [{"field": "occurred_at", "message": message}]


class TestDescriptionError:

    def test_required_with_no_mode(self):
        assert description_error(None, None) == DESCRIPTION_NEEDED

    def test_required_with_other(self):
        assert description_error(None, "OTH") == DESCRIPTION_NEEDED_OTHER

    def test_optional_with_another_mode(self):
        assert description_error(None, "NOI") is None

    def test_given(self):
        assert description_error("leaks at the seal", None) is None
        assert description_error("leaks at the seal", "OTH") is None


class TestMachineAndComponent:

    def test_a_machine(self):
        assert machine_and_component({"id": 10, "level": "equipment", "parent_id": None, "gp_id": None}) == (10, None)

    def test_a_component_unit_under_a_machine(self):
        node = {"id": 11, "level": "component_unit", "parent_id": 10, "gp_id": None}
        assert machine_and_component(node) == (10, 11)

    def test_a_component_under_a_component_unit(self):
        node = {"id": 12, "level": "component", "parent_id": 11, "gp_id": 10}
        assert machine_and_component(node) == (10, 12)

    def test_a_component_straight_under_a_machine(self):
        node = {"id": 13, "level": "component", "parent_id": 10, "gp_id": None}
        assert machine_and_component(node) == (10, 13)
