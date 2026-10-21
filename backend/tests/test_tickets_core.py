"""Tickets — pure rules (S017 § 8, S018 § 8; no DB)."""

from datetime import date, datetime, timedelta

import pytest

from tickets_core import (
    ACTION_NEEDED, ALREADY_BREAKDOWN, ALREADY_DEFECT, CAUSE_NEEDED, DESCRIPTION_MAX, DESCRIPTION_NEEDED,
    DESCRIPTION_NEEDED_OTHER, EVENT_TIME_BEFORE_LAST, EVENT_TIME_FORMAT, EVENT_TIME_FUTURE, EVENT_TIME_TOO_OLD,
    INTENSITIES, INTENSITY_FILTERS, LABOUR_BEFORE_CLOSE, LABOUR_DATE_EARLY, LABOUR_DATE_FORMAT, LABOUR_DATE_FUTURE,
    LOWERING_NEEDS_REMARK, MODE_NEEDED, MOVES, NOTHING_TO_CHANGE, OPEN_STATES, PERSON_NEEDED, REMARK_MAX,
    REPEAT_WINDOW_DAYS, STARTED_AFTER_RESTORE, STARTED_ALREADY, STATES, TRADE_NEEDED, allowed_moves,
    description_error, edit_lines, event_time_error, format_ticket_serial, is_breakdown, is_repeat_candidate, latest_restoration,
    machine_and_component, parse_event_time, regrade_options, send_back_intensity, serial_scope, started_at_error,
    ticket_times, trade_error, validate_close, validate_edit, validate_event_time, validate_labour, validate_move,
    validate_raise, validate_regrade,
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
                         "reported_by_id": None, "repeat_of_id": None, "description": None, "occurred_at": NOW,
                         "restore": None}

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

    @pytest.mark.parametrize("field", ["failure_mode_id", "reported_by_id", "repeat_of_id"])
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


class TestValidateRaiseRestore:
    """S018 A1: the *Already fixed* block is the restore move's body, its refusals named restore.*"""

    BODY = {"equipment_id": 5, "intensity": "critical"}

    def test_the_block_is_the_moves_body(self):
        block = {"person_id": 4, "occurred_at": "2026-10-20T11:00", "started_at": "2026-10-20T10:30"}
        clean, errors = validate_raise({**self.BODY, "restore": block}, NOW)
        assert errors == []
        assert clean["restore"] == validate_move("restore", block)[0] == {
            "occurred_at": datetime(2026, 10, 20, 11, 0), "remark": None, "person_id": 4,
            "started_at": datetime(2026, 10, 20, 10, 30)}

    def test_only_the_person_is_required(self):
        clean, errors = validate_raise({**self.BODY, "restore": {"person_id": 4}}, NOW)
        assert errors == [] and clean["restore"]["occurred_at"] is None and clean["restore"]["started_at"] is None

    def test_refusals_are_prefixed(self):
        _, errors = validate_raise({**self.BODY, "restore": {}}, NOW)
        assert errors == [{"field": "restore.person_id", "message": PERSON_NEEDED}]
        _, errors = validate_raise({**self.BODY, "restore": {"person_id": "4", "occurred_at": "noon",
                                                            "started_at": "10:30"}}, NOW)
        assert _fields(errors) == ["restore.occurred_at", "restore.person_id", "restore.started_at"]

    def test_the_raises_own_occurred_at_keeps_its_name(self):
        _, errors = validate_raise({**self.BODY, "occurred_at": "noon", "restore": {"person_id": 4}}, NOW)
        assert _fields(errors) == ["occurred_at"]

    @pytest.mark.parametrize("block", ["yes", 1, True, [4]])
    def test_not_an_object(self, block):
        assert _fields(validate_raise({**self.BODY, "restore": block}, NOW)[1]) == ["restore"]


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


# ---------------------------------------------------------------------------
# Working the ticket (S018 § 8)
# ---------------------------------------------------------------------------

WORKER = {"ticket:read", "ticket:raise", "ticket:restore", "ticket:work"}
OPERATOR = {"ticket:read", "ticket:raise", "ticket:restore"}
ENGINEER = WORKER | {"ticket:assign", "ticket:close"}


class TestAllowedMoves:

    @pytest.mark.parametrize("state, keys, expected", [
        ("raised", ENGINEER, ["acknowledge", "start", "restore", "not-a-fault"]),
        ("acknowledged", ENGINEER, ["start", "restore", "not-a-fault"]),
        ("in_progress", ENGINEER, ["restore"]),
        ("back_in_service", ENGINEER, ["send-back", "close"]),
        ("closed", ENGINEER, []),
        ("raised", WORKER, ["acknowledge", "start", "restore"]),
        ("in_progress", WORKER, ["restore"]),
        ("back_in_service", WORKER, []),
        ("raised", OPERATOR, ["restore"]),
        ("acknowledged", OPERATOR, ["restore"]),
        ("in_progress", OPERATOR, ["restore"]),
        ("back_in_service", OPERATOR, []),
        ("raised", set(), []),
        ("raised", {"ticket:close"}, ["not-a-fault"]),
    ])
    def test_state_by_keys(self, state, keys, expected):
        assert allowed_moves(state, keys) == expected

    def test_the_table(self):
        assert {name: (m.from_states, m.to_state, m.key) for name, m in MOVES.items()} == {
            "acknowledge": (("raised",), "acknowledged", "ticket:work"),
            "start": (("raised", "acknowledged"), "in_progress", "ticket:work"),
            "restore": (("raised", "acknowledged", "in_progress"), "back_in_service", "ticket:restore"),
            "send-back": (("back_in_service",), "in_progress", "ticket:close"),
            "close": (("back_in_service",), "closed", "ticket:close"),
            "not-a-fault": (("raised", "acknowledged"), "closed", "ticket:close"),
        }


class TestValidateMove:

    def test_acknowledge_needs_nothing(self):
        assert validate_move("acknowledge", {}) == ({"occurred_at": None, "remark": None}, [])

    def test_time_and_remark(self):
        clean, errors = validate_move("start", {"occurred_at": "2026-10-20T10:05", "remark": "  on it "})
        assert errors == [] and clean == {"occurred_at": datetime(2026, 10, 20, 10, 5), "remark": "on it"}

    def test_bad_time_and_long_remark(self):
        _, errors = validate_move("start", {"occurred_at": "10:05", "remark": "x" * (REMARK_MAX + 1)})
        assert _fields(errors) == ["occurred_at", "remark"]

    def test_restore_needs_a_person(self):
        _, errors = validate_move("restore", {})
        assert errors == [{"field": "person_id", "message": PERSON_NEEDED}]
        clean, errors = validate_move("restore", {"person_id": 4, "started_at": "2026-10-19T23:40"})
        assert errors == [] and clean["person_id"] == 4 and clean["started_at"] == datetime(2026, 10, 19, 23, 40)
        assert _fields(validate_move("restore", {"person_id": "4"})[1]) == ["person_id"]

    def test_send_back_needs_machine_down_and_remark(self):
        assert _fields(validate_move("send-back", {})[1]) == ["machine_down", "remark"]
        assert _fields(validate_move("send-back", {"machine_down": "yes", "remark": "x"})[1]) == ["machine_down"]
        clean, errors = validate_move("send-back", {"machine_down": False, "remark": "leaks still"})
        assert errors == [] and clean["machine_down"] is False

    def test_close_needs_cause_and_action(self):
        _, errors = validate_move("close", {})
        assert errors == [{"field": "cause_id", "message": CAUSE_NEEDED}, {"field": "action_id", "message": ACTION_NEEDED}]
        clean, errors = validate_move("close", {"cause_id": 1, "action_id": 2, "failure_mode_id": 3})
        assert errors == [] and (clean["cause_id"], clean["action_id"], clean["failure_mode_id"]) == (1, 2, 3)

    def test_not_a_fault_needs_cause_and_remark(self):
        assert _fields(validate_move("not-a-fault", {})[1]) == ["cause_id", "remark"]
        assert _fields(validate_move("not-a-fault", {"cause_id": 1, "remark": "   "})[1]) == ["remark"]
        assert validate_move("not-a-fault", {"cause_id": 1, "remark": "Operator error"})[1] == []


class TestValidateEventTime:

    LAST = ("acknowledged", datetime(2026, 10, 20, 10, 4))

    def test_before_the_last_event_names_it(self):
        message = validate_event_time(datetime(2026, 10, 20, 10, 0), self.LAST, NOW)
        assert message == "Must be at or after Acknowledged, 20-10-2026 10:04"

    def test_equal_to_the_last_event_is_accepted(self):
        assert validate_event_time(datetime(2026, 10, 20, 10, 4), self.LAST, NOW) is None

    def test_future_and_back_dating_limits(self):
        assert validate_event_time(NOW + timedelta(minutes=6), self.LAST, NOW) == EVENT_TIME_FUTURE
        old = ("raised", NOW - timedelta(days=10))
        assert validate_event_time(NOW - timedelta(days=8), old, NOW) == EVENT_TIME_TOO_OLD
        assert validate_event_time(NOW - timedelta(days=7), old, NOW) is None


class TestStartedAt:

    RESTORED = datetime(2026, 10, 21, 0, 30)

    def test_the_evening_before_is_accepted(self):
        assert started_at_error(datetime(2026, 10, 20, 23, 40), "acknowledged", self.RESTORED) is None

    def test_after_the_restoration_is_refused(self):
        assert started_at_error(datetime(2026, 10, 21, 0, 31), "raised", self.RESTORED) == STARTED_AFTER_RESTORE

    def test_not_when_work_has_started(self):
        assert started_at_error(datetime(2026, 10, 20, 23, 40), "in_progress", self.RESTORED) == STARTED_ALREADY


class TestSendBackIntensity:

    @pytest.mark.parametrize("current, machine_down, expected", [
        ("degraded", True, "critical"),
        ("initial", True, "critical"),
        ("critical", True, None),
        ("critical", False, "degraded"),
        ("degraded", False, None),
        ("initial", False, None),
    ])
    def test_rule(self, current, machine_down, expected):
        assert send_back_intensity(current, machine_down) == expected


class TestRegrade:

    def test_options(self):
        assert regrade_options("critical", lowering_allowed=False) == []
        assert regrade_options("initial", lowering_allowed=False) == ["critical", "degraded"]
        assert regrade_options("degraded", lowering_allowed=True) == ["critical", "initial"]
        assert regrade_options("critical", lowering_allowed=True) == ["degraded", "initial"]

    def test_same_intensity_is_refused(self):
        assert validate_regrade("critical", "critical", True, None) == (400, "intensity", ALREADY_BREAKDOWN)
        assert validate_regrade("degraded", "degraded", True, None) == (400, "intensity", ALREADY_DEFECT)

    def test_unknown_intensity_is_refused(self):
        assert validate_regrade("degraded", "breakdown", True, None)[:2] == (400, "intensity")

    def test_raising_needs_nothing(self):
        assert validate_regrade("degraded", "critical", False, None) is None
        assert validate_regrade("initial", "degraded", False, None) is None

    def test_lowering_needs_work_and_a_remark(self):
        assert validate_regrade("critical", "degraded", False, "runs")[0] == 403
        assert validate_regrade("critical", "degraded", True, None) == (400, "remark", LOWERING_NEEDS_REMARK)
        assert validate_regrade("critical", "initial", True, "runs again after a reset") is None


class TestValidateClose:

    def test_symptom_needed_when_the_ticket_has_none(self):
        assert validate_close(None, {"failure_mode_id": None}, 1) == (400, "failure_mode_id", MODE_NEEDED)
        assert validate_close(None, {"failure_mode_id": 5}, 1) is None
        assert validate_close(7, {"failure_mode_id": None}, 1) is None

    def test_no_labour_is_409(self):
        assert validate_close(7, {"failure_mode_id": None}, 0) == (409, None, LABOUR_BEFORE_CLOSE)

    def test_other_without_description_is_the_s017_rule(self):
        assert description_error(None, "OTH") == DESCRIPTION_NEEDED_OTHER


class TestValidateLabour:

    TODAY = date(2026, 10, 20)
    EARLIEST = date(2026, 10, 18)
    BODY = {"person_id": 3, "work_date": "2026-10-20", "minutes": 85}

    def test_valid(self):
        clean, errors = validate_labour(self.BODY, self.TODAY, self.EARLIEST)
        assert errors == [] and clean == {"person_id": 3, "trade_id": None, "work_date": self.TODAY, "minutes": 85}

    @pytest.mark.parametrize("minutes", [0, 1441, -5, "60", 1.5, None, True])
    def test_minutes_out_of_range(self, minutes):
        assert _fields(validate_labour({**self.BODY, "minutes": minutes}, self.TODAY, self.EARLIEST)[1]) == ["minutes"]

    @pytest.mark.parametrize("minutes", [1, 1440])
    def test_minutes_bounds(self, minutes):
        assert validate_labour({**self.BODY, "minutes": minutes}, self.TODAY, self.EARLIEST)[1] == []

    @pytest.mark.parametrize("work_date, message", [
        ("2026-10-21", LABOUR_DATE_FUTURE), ("2026-10-17", LABOUR_DATE_EARLY), ("20-10-2026", LABOUR_DATE_FORMAT),
        (None, LABOUR_DATE_FORMAT),
    ])
    def test_date_limits(self, work_date, message):
        _, errors = validate_labour({**self.BODY, "work_date": work_date}, self.TODAY, self.EARLIEST)
        assert errors == [{"field": "work_date", "message": message}]

    def test_the_ticket_date_is_accepted(self):
        assert validate_labour({**self.BODY, "work_date": "2026-10-18"}, self.TODAY, self.EARLIEST)[1] == []

    def test_person_required(self):
        assert _fields(validate_labour({**self.BODY, "person_id": None}, self.TODAY, self.EARLIEST)[1]) == ["person_id"]

    def test_trade_required_when_the_person_has_trades(self):
        assert trade_error(None, person_has_trades=True) == TRADE_NEEDED
        assert trade_error(None, person_has_trades=False) is None
        assert trade_error(4, person_has_trades=True) is None


class TestEdit:

    def test_only_the_fields_given(self):
        assert validate_edit({"component_id": None}) == ({"component_id": None}, [])
        assert validate_edit({"description": "  Seal  "}) == ({"description": "Seal"}, [])

    def test_nothing_to_change(self):
        assert validate_edit({}) == ({}, [{"field": None, "message": NOTHING_TO_CHANGE}])

    def test_bad_ids(self):
        assert _fields(validate_edit({"failure_mode_id": "3"})[1]) == ["failure_mode_id"]

    def test_lines(self):
        labels = {"component": "Component", "failure_mode": "Symptom", "description": "Description"}
        old = {"component": None, "failure_mode": "Abnormal noise", "description": "Bang"}
        new = {"component": "P-01 Pump", "failure_mode": "Abnormal noise", "description": None}
        assert edit_lines(old, new, labels) == "Component: — → P-01 Pump\nDescription: Bang → —"
        assert edit_lines(old, dict(old), labels) == ""


def _ev(event, minute, intensity=None):
    """An event ``minute`` minutes after 10:00 on 20-10-2026."""
    return {"event": event, "occurred_at": datetime(2026, 10, 20, 10, 0) + timedelta(minutes=minute),
            "intensity": intensity}


def _times(events, now_minute):
    result = ticket_times(events, datetime(2026, 10, 20, 10, 0) + timedelta(minutes=now_minute))
    return result["response_minutes"], result["repair_minutes"], result["downtime_minutes"]


class TestTicketTimes:

    def test_straight_path(self):
        events = [_ev("raised", 0, "critical"), _ev("acknowledged", 5), _ev("started", 15),
                  _ev("back_in_service", 75), _ev("closed", 200)]
        assert _times(events, 300) == (5, 60, 75)

    def test_start_from_raised(self):
        events = [_ev("raised", 0, "critical"), _ev("started", 10), _ev("back_in_service", 40)]
        assert _times(events, 100) == (10, 30, 40)

    def test_back_in_service_after_the_fact_without_a_start(self):
        events = [_ev("raised", 0, "critical"), _ev("acknowledged", 5), _ev("back_in_service", 50)]
        assert _times(events, 100) == (5, None, 50)

    def test_back_in_service_after_the_fact_with_a_start(self):
        events = [_ev("raised", 0, "critical"), _ev("started", 20), _ev("back_in_service", 50)]
        assert _times(events, 100) == (20, 30, 50)

    def test_send_back_with_the_machine_down(self):
        events = [_ev("raised", 0, "critical"), _ev("started", 10), _ev("back_in_service", 40),
                  _ev("sent_back", 100), _ev("back_in_service", 130)]
        # Downtime 0-40 and 100-130; repair 10-40 and 100-130
        assert _times(events, 200) == (10, 60, 70)

    def test_send_back_running_from_critical_stops_downtime(self):
        events = [_ev("raised", 0, "critical"), _ev("started", 10), _ev("back_in_service", 40),
                  _ev("sent_back", 100, "degraded"), _ev("back_in_service", 130)]
        assert _times(events, 200) == (10, 60, 40)

    def test_send_back_down_on_a_defect_starts_downtime(self):
        events = [_ev("raised", 0, "degraded"), _ev("started", 10), _ev("back_in_service", 40),
                  _ev("sent_back", 100, "critical"), _ev("back_in_service", 130)]
        assert _times(events, 200) == (10, 60, 30)

    def test_defect_regraded_critical(self):
        events = [_ev("raised", 0, "degraded"), _ev("acknowledged", 5), _ev("regraded", 30, "critical"),
                  _ev("started", 40), _ev("back_in_service", 90)]
        assert _times(events, 200) == (5, 50, 60)

    def test_lowered_from_critical(self):
        events = [_ev("raised", 0, "critical"), _ev("started", 10), _ev("regraded", 25, "degraded"),
                  _ev("back_in_service", 90)]
        assert _times(events, 200) == (10, 80, 25)

    def test_open_ticket_counts_to_now(self):
        events = [_ev("raised", 0, "critical"), _ev("started", 10)]
        assert _times(events, 70) == (10, 60, 70)
        assert _times([_ev("raised", 0, "critical")], 30) == (None, None, 30)

    def test_a_defect_has_no_downtime(self):
        assert _times([_ev("raised", 0, "initial"), _ev("started", 10)], 70) == (10, 60, 0)

    def test_last_event_after_now_is_clamped(self):
        events = [_ev("raised", 0, "critical"), _ev("started", 10)]
        assert _times(events, 8) == (10, 0, 10)

    def test_bookkeeping_events_are_ignored(self):
        events = [_ev("raised", 0, "critical"), _ev("assigned", 1), _ev("started", 10), _ev("edited", 12),
                  _ev("back_in_service", 40)]
        assert _times(events, 100) == (10, 30, 40)

    def test_not_a_fault_is_all_none(self):
        events = [_ev("raised", 0, "critical"), _ev("acknowledged", 5), _ev("closed_not_a_fault", 20)]
        assert _times(events, 100) == (None, None, None)


class TestRepeat:

    RESTORED = datetime(2026, 10, 10, 12, 0)

    def test_seven_days_accepted_eight_refused(self):
        assert is_repeat_candidate(self.RESTORED, self.RESTORED + timedelta(days=7))
        assert not is_repeat_candidate(self.RESTORED, self.RESTORED + timedelta(days=8))
        assert REPEAT_WINDOW_DAYS == 7

    def test_a_new_time_before_the_restoration_is_refused(self):
        assert not is_repeat_candidate(self.RESTORED, self.RESTORED - timedelta(minutes=1))
        assert is_repeat_candidate(self.RESTORED, self.RESTORED)

    def test_never_restored(self):
        assert not is_repeat_candidate(None, self.RESTORED)

    def test_latest_restoration_needs_a_restored_state(self):
        events = [{"event": "back_in_service", "occurred_at": self.RESTORED},
                  {"event": "back_in_service", "occurred_at": self.RESTORED + timedelta(days=1)}]
        later = self.RESTORED + timedelta(days=1)
        assert latest_restoration("back_in_service", False, events) == later
        assert latest_restoration("closed", False, events) == later
        assert latest_restoration("in_progress", False, events) is None
        assert latest_restoration("closed", True, events) is None
        assert latest_restoration("back_in_service", False, []) is None

    def test_the_latest_restoration_counts(self):
        """The caller passes the latest back in service: a repeat 9 days after the first but 2
        after the second is a candidate."""
        first, second = self.RESTORED, self.RESTORED + timedelta(days=7)
        new = self.RESTORED + timedelta(days=9)
        assert not is_repeat_candidate(first, new) and is_repeat_candidate(max(first, second), new)
