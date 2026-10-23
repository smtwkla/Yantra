"""Tickets — pure rules (S017 § 8, S018 § 8; no DB)."""

from datetime import date, datetime, timedelta
from decimal import Decimal

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
from tickets_core import (  # S019
    MACHINE_STOPPED_NEEDED, PLANNED_DATE_MAX_DAYS, PLANNED_DATE_NEEDED, PLANNED_DATE_PAST, PLANNED_DATE_TOO_FAR,
    REMARK_NEEDED, WAITING_REASON_NEEDED, WAITING_REASONS, is_overdue, machine_stopped_needed, planned_date_error,
)
from tickets_core import (  # S028
    EVENT_TIME_TOO_OLD_LONG, LONG_BACKDATE_DAYS, MAX_BACKDATE_DAYS, backdate_days, too_old_message,
)
from tickets_core import NOTE_EVENT, NOTE_NEEDED, ORDERED_EVENTS, validate_note  # S027
from tickets_core import (  # S020
    PART_DESCRIPTION_NEEDED, PART_KIND_NEEDED, PART_KINDS, PART_MAKER_NEEDED, PART_NODE_NEEDED, PART_QUANTITY_DECIMALS,
    PART_QUANTITY_NEEDED, PART_QUANTITY_TOO_BIG, PART_UNIT_NEEDED, PART_UNITS, PARTS_HINT_ACTION_CODES, validate_part,
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
        assert OPEN_STATES == ("raised", "acknowledged", "scheduled", "in_progress", "back_in_service")
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
        assert event_time_error(NOW, NOW, 7) is None

    def test_four_minutes_ahead_is_accepted(self):
        assert event_time_error(NOW + timedelta(minutes=4), NOW, 7) is None

    def test_six_minutes_ahead_is_refused(self):
        assert event_time_error(NOW + timedelta(minutes=6), NOW, 7) == EVENT_TIME_FUTURE

    def test_seven_days_back_is_accepted(self):
        assert event_time_error(NOW - timedelta(days=7), NOW, 7) is None

    def test_eight_days_back_is_refused(self):
        assert event_time_error(NOW - timedelta(days=8), NOW, 7) == EVENT_TIME_TOO_OLD
        assert "7 days" in EVENT_TIME_TOO_OLD

    def test_long_limit_accepts_1095_days_and_refuses_1096(self):
        assert event_time_error(NOW - timedelta(days=1095), NOW, 1095) is None
        assert event_time_error(NOW - timedelta(days=1096), NOW, 1095) == EVENT_TIME_TOO_OLD_LONG
        assert "3 years" in EVENT_TIME_TOO_OLD_LONG

    def test_not_before_refuses_an_earlier_time(self):
        last = NOW - timedelta(hours=1)
        assert event_time_error(NOW - timedelta(hours=2), NOW, 7, not_before=last) == EVENT_TIME_BEFORE_LAST
        assert event_time_error(last, NOW, 7, not_before=last) is None
        assert event_time_error(NOW, NOW, 7, not_before=last) is None


class TestValidateRaise:

    BODY = {"equipment_id": 5, "intensity": "critical"}

    @pytest.mark.parametrize("intensity", INTENSITIES)
    def test_each_intensity(self, intensity):
        clean, errors = validate_raise({**self.BODY, "intensity": intensity}, NOW, 7)
        assert errors == []
        assert clean == {"equipment_id": 5, "intensity": intensity, "failure_mode_id": None,
                         "reported_by_id": None, "repeat_of_id": None, "description": None, "occurred_at": NOW,
                         "restore": None}

    @pytest.mark.parametrize("intensity", [None, "", "breakdown", "CRITICAL", 1])
    def test_missing_or_unknown_intensity(self, intensity):
        body = {"equipment_id": 5} if intensity is None else {**self.BODY, "intensity": intensity}
        assert _fields(validate_raise(body, NOW, 7)[1]) == ["intensity"]

    @pytest.mark.parametrize("equipment_id", [None, 0, -1, "5", True, 1.5])
    def test_missing_or_bad_equipment_id(self, equipment_id):
        body = {"intensity": "critical"} if equipment_id is None else {**self.BODY, "equipment_id": equipment_id}
        assert _fields(validate_raise(body, NOW, 7)[1]) == ["equipment_id"]

    def test_description_is_trimmed_and_empty_is_none(self):
        assert validate_raise({**self.BODY, "description": "  oil leak  "}, NOW, 7)[0]["description"] == "oil leak"
        assert validate_raise({**self.BODY, "description": "   "}, NOW, 7)[0]["description"] is None

    def test_description_too_long(self):
        assert validate_raise({**self.BODY, "description": "x" * DESCRIPTION_MAX}, NOW, 7)[1] == []
        assert _fields(validate_raise({**self.BODY, "description": "x" * (DESCRIPTION_MAX + 1)}, NOW, 7)[1]) == [
            "description"]

    def test_description_must_be_text(self):
        assert _fields(validate_raise({**self.BODY, "description": 12}, NOW, 7)[1]) == ["description"]

    @pytest.mark.parametrize("field", ["failure_mode_id", "reported_by_id", "repeat_of_id"])
    def test_optional_ids(self, field):
        assert validate_raise({**self.BODY, field: 9}, NOW, 7)[0][field] == 9
        assert validate_raise({**self.BODY, field: None}, NOW, 7)[0][field] is None
        for bad in ("9", 0, True):
            assert _fields(validate_raise({**self.BODY, field: bad}, NOW, 7)[1]) == [field]

    def test_occurred_at_given(self):
        clean, errors = validate_raise({**self.BODY, "occurred_at": "2026-10-18T09:15"}, NOW, 7)
        assert errors == [] and clean["occurred_at"] == datetime(2026, 10, 18, 9, 15)

    @pytest.mark.parametrize("text, message", [
        ("2026-10-20T14:05:00+05:30", EVENT_TIME_FORMAT),
        ("2026-10-20T15:00", EVENT_TIME_FUTURE),
        ("2026-10-10T10:00", EVENT_TIME_TOO_OLD),
    ])
    def test_occurred_at_refused(self, text, message):
        _, errors = validate_raise({**self.BODY, "occurred_at": text}, NOW, 7)
        assert errors == [{"field": "occurred_at", "message": message}]


class TestValidateRaiseRestore:
    """S018 A1: the *Already fixed* block is the restore move's body, its refusals named restore.*"""

    BODY = {"equipment_id": 5, "intensity": "critical"}

    def test_the_block_is_the_moves_body(self):
        block = {"person_id": 4, "occurred_at": "2026-10-20T11:00", "started_at": "2026-10-20T10:30"}
        clean, errors = validate_raise({**self.BODY, "restore": block}, NOW, 7)
        assert errors == []
        assert clean["restore"] == validate_move("restore", block)[0] == {
            "occurred_at": datetime(2026, 10, 20, 11, 0), "remark": None, "person_id": 4,
            "started_at": datetime(2026, 10, 20, 10, 30), "machine_stopped": None}

    def test_only_the_person_is_required(self):
        clean, errors = validate_raise({**self.BODY, "restore": {"person_id": 4}}, NOW, 7)
        assert errors == [] and clean["restore"]["occurred_at"] is None and clean["restore"]["started_at"] is None

    def test_refusals_are_prefixed(self):
        _, errors = validate_raise({**self.BODY, "restore": {}}, NOW, 7)
        assert errors == [{"field": "restore.person_id", "message": PERSON_NEEDED}]
        _, errors = validate_raise({**self.BODY, "restore": {"person_id": "4", "occurred_at": "noon",
                                                            "started_at": "10:30"}}, NOW, 7)
        assert _fields(errors) == ["restore.occurred_at", "restore.person_id", "restore.started_at"]

    def test_the_raises_own_occurred_at_keeps_its_name(self):
        _, errors = validate_raise({**self.BODY, "occurred_at": "noon", "restore": {"person_id": 4}}, NOW, 7)
        assert _fields(errors) == ["occurred_at"]

    @pytest.mark.parametrize("block", ["yes", 1, True, [4]])
    def test_not_an_object(self, block):
        assert _fields(validate_raise({**self.BODY, "restore": block}, NOW, 7)[1]) == ["restore"]


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
        ("raised", ENGINEER, ["acknowledge", "start", "restore", "schedule", "not-a-fault"]),
        ("acknowledged", ENGINEER, ["start", "restore", "schedule", "not-a-fault"]),
        ("scheduled", ENGINEER, ["start", "restore", "reschedule", "not-a-fault"]),
        ("in_progress", ENGINEER, ["restore", "schedule", "not-a-fault"]),
        ("back_in_service", ENGINEER, ["send-back", "close"]),
        ("closed", ENGINEER, []),
        ("raised", WORKER, ["acknowledge", "start", "restore"]),
        ("acknowledged", WORKER, ["start", "restore"]),
        # S019 U1: a technician schedules from in progress only ("work stops, waiting")
        ("scheduled", WORKER, ["start", "restore"]),
        ("in_progress", WORKER, ["restore", "schedule"]),
        ("back_in_service", WORKER, []),
        ("raised", OPERATOR, ["restore"]),
        ("acknowledged", OPERATOR, ["restore"]),
        ("scheduled", OPERATOR, ["restore"]),
        ("in_progress", OPERATOR, ["restore"]),
        ("back_in_service", OPERATOR, []),
        ("raised", set(), []),
        ("raised", {"ticket:close"}, ["not-a-fault"]),
    ])
    def test_state_by_keys(self, state, keys, expected):
        assert allowed_moves(state, keys) == expected

    @pytest.mark.parametrize("keys, expected", [
        (ENGINEER, ["close"]),
        (WORKER, []),
    ])
    def test_no_send_back_once_a_repeat_exists(self, keys, expected):
        """S025 § 5.2: the failure came back on the repeat ticket; close stays."""
        assert allowed_moves("back_in_service", keys, has_repeat=True) == expected

    def test_the_table(self):
        assert {name: (m.from_states, m.to_state, m.key) for name, m in MOVES.items()} == {
            "acknowledge": (("raised",), "acknowledged", "ticket:work"),
            "start": (("raised", "acknowledged", "scheduled"), "in_progress", "ticket:work"),
            "restore": (("raised", "acknowledged", "scheduled", "in_progress"), "back_in_service", "ticket:restore"),
            "schedule": (("raised", "acknowledged", "in_progress"), "scheduled", "ticket:assign"),
            "reschedule": (("scheduled",), "scheduled", "ticket:assign"),
            "send-back": (("back_in_service",), "in_progress", "ticket:close"),
            "close": (("back_in_service",), "closed", "ticket:close"),
            "not-a-fault": (("raised", "acknowledged", "scheduled", "in_progress"), "closed", "ticket:close"),
        }
        # S019 U1: one Schedule move, whose key depends on where it starts from
        schedule = MOVES["schedule"]
        assert [schedule.key_at(s) for s in schedule.from_states] == ["ticket:assign", "ticket:assign", "ticket:work"]
        assert schedule.keys == {"ticket:assign", "ticket:work"}
        assert MOVES["start"].keys == {"ticket:work"}


class TestValidateMove:

    def test_acknowledge_needs_nothing(self):
        assert validate_move("acknowledge", {}) == ({"occurred_at": None, "remark": None}, [])

    def test_time_and_remark(self):
        clean, errors = validate_move("start", {"occurred_at": "2026-10-20T10:05", "remark": "  on it "})
        assert errors == [] and clean == {"occurred_at": datetime(2026, 10, 20, 10, 5), "remark": "on it",
                                          "machine_stopped": None}

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
        message = validate_event_time(datetime(2026, 10, 20, 10, 0), self.LAST, NOW, 7)
        assert message == "Must be at or after Acknowledged, 20-10-2026 10:04"

    def test_equal_to_the_last_event_is_accepted(self):
        assert validate_event_time(datetime(2026, 10, 20, 10, 4), self.LAST, NOW, 7) is None

    def test_future_and_back_dating_limits(self):
        assert validate_event_time(NOW + timedelta(minutes=6), self.LAST, NOW, 7) == EVENT_TIME_FUTURE
        old = ("raised", NOW - timedelta(days=10))
        assert validate_event_time(NOW - timedelta(days=8), old, NOW, 7) == EVENT_TIME_TOO_OLD
        assert validate_event_time(NOW - timedelta(days=7), old, NOW, 7) is None


class TestBackdateWindow:
    """S028: how far back an entered time may lie."""

    def test_holder_of_the_key_gets_the_long_limit_always(self):
        assert backdate_days(datetime(2026, 11, 30, 23, 59), True) == LONG_BACKDATE_DAYS == 1095
        assert backdate_days(datetime(2026, 12, 1, 0, 0), True) == LONG_BACKDATE_DAYS

    def test_everyone_gets_the_long_limit_until_the_last_day_of_the_window(self):
        assert backdate_days(datetime(2026, 11, 30, 23, 59), False) == LONG_BACKDATE_DAYS

    def test_after_the_window_others_get_seven_days(self):
        assert backdate_days(datetime(2026, 12, 1, 0, 0), False) == MAX_BACKDATE_DAYS == 7

    def test_too_old_message_follows_the_limit(self):
        assert too_old_message(7) == EVENT_TIME_TOO_OLD
        assert too_old_message(1095) == EVENT_TIME_TOO_OLD_LONG
        assert "3 years" in too_old_message(1095)

    def test_too_old_message_refuses_any_other_limit(self):
        with pytest.raises(AssertionError):
            too_old_message(30)


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


# ---------------------------------------------------------------------------
# Deferred work (S019 § 8)
# ---------------------------------------------------------------------------

class TestWaitingReasons:

    def test_the_six_codes_and_their_delay_kinds(self):
        """The frontend's WAITING_REASON_LABELS asserts the same six codes (ticketLabels.test.js)."""
        assert {code: kind for code, (_label, kind) in WAITING_REASONS.items()} == {
            "parts": "logistic", "vendor": "logistic", "expert": "logistic",
            "slot": "administrative", "approval": "administrative", "other": None,
        }


class TestValidatePlanMoves:

    def test_schedule_needs_a_date_and_a_reason(self):
        _, errors = validate_move("schedule", {})
        assert errors == [{"field": "planned_date", "message": PLANNED_DATE_NEEDED},
                          {"field": "waiting_reason", "message": WAITING_REASON_NEEDED}]

    def test_schedule_parsed(self):
        clean, errors = validate_move("schedule", {"planned_date": "2026-10-25", "waiting_reason": "parts"})
        assert errors == []
        assert (clean["planned_date"], clean["waiting_reason"], clean["remark"]) == (date(2026, 10, 25), "parts", None)

    @pytest.mark.parametrize("planned_date", ["25-10-2026", "2026-13-01", 20261025, ""])
    def test_a_bad_date(self, planned_date):
        _, errors = validate_move("schedule", {"planned_date": planned_date, "waiting_reason": "parts"})
        assert errors == [{"field": "planned_date", "message": LABOUR_DATE_FORMAT}]

    def test_an_unknown_reason(self):
        _, errors = validate_move("schedule", {"planned_date": "2026-10-25", "waiting_reason": "workshop"})
        assert errors == [{"field": "waiting_reason", "message": WAITING_REASON_NEEDED}]

    @pytest.mark.parametrize("reason", [["parts"], {"a": 1}])
    def test_a_list_or_object_reason(self, reason):
        _, errors = validate_move("schedule", {"planned_date": "2026-10-25", "waiting_reason": reason})
        assert errors == [{"field": "waiting_reason", "message": WAITING_REASON_NEEDED}]

    def test_other_needs_a_remark(self):
        body = {"planned_date": "2026-10-25", "waiting_reason": "other"}
        assert validate_move("schedule", body)[1] == [{"field": "remark", "message": REMARK_NEEDED}]
        assert validate_move("schedule", {**body, "remark": "   "})[1] == [{"field": "remark", "message": REMARK_NEEDED}]
        assert validate_move("schedule", {**body, "remark": "Crane booked by civil"})[1] == []

    def test_change_plan_needs_a_remark_once(self):
        body = {"planned_date": "2026-10-25", "waiting_reason": "other"}
        assert validate_move("reschedule", body)[1] == [{"field": "remark", "message": REMARK_NEEDED}]
        assert validate_move("reschedule", {**body, "waiting_reason": "slot", "remark": "Parts late"})[1] == []

    @pytest.mark.parametrize("move", ["start", "restore"])
    def test_machine_stopped_is_a_boolean(self, move):
        body = {"person_id": 4} if move == "restore" else {}
        assert validate_move(move, body)[0]["machine_stopped"] is None
        assert validate_move(move, {**body, "machine_stopped": True})[0]["machine_stopped"] is True
        assert validate_move(move, {**body, "machine_stopped": "yes"})[1] == [
            {"field": "machine_stopped", "message": MACHINE_STOPPED_NEEDED}]


class TestPlannedDate:
    TODAY = date(2026, 10, 22)

    def test_yesterday_is_refused(self):
        assert planned_date_error(self.TODAY - timedelta(days=1), self.TODAY) == PLANNED_DATE_PAST

    def test_today_is_accepted(self):
        assert planned_date_error(self.TODAY, self.TODAY) is None

    def test_365_days_accepted_366_refused(self):
        assert PLANNED_DATE_MAX_DAYS == 365
        assert planned_date_error(self.TODAY + timedelta(days=365), self.TODAY) is None
        assert planned_date_error(self.TODAY + timedelta(days=366), self.TODAY) == PLANNED_DATE_TOO_FAR

    def test_overdue_after_the_day_only(self):
        planned = date(2026, 10, 25)
        assert is_overdue("scheduled", planned, date(2026, 10, 24)) is False
        assert is_overdue("scheduled", planned, date(2026, 10, 25)) is False
        assert is_overdue("scheduled", planned, date(2026, 10, 26)) is True
        assert is_overdue("in_progress", planned, date(2026, 10, 26)) is False
        assert is_overdue("raised", None, date(2026, 10, 26)) is False


class TestMachineStoppedNeeded:

    @pytest.mark.parametrize("from_state, intensity, expected", [
        ("scheduled", "degraded", True),
        ("scheduled", "initial", True),
        ("scheduled", "critical", False),
        ("acknowledged", "degraded", False),
        ("raised", "initial", False),
    ])
    def test_rule(self, from_state, intensity, expected):
        assert machine_stopped_needed(from_state, intensity) is expected


def _plan(event, minute, reason=None, intensity=None):
    return {**_ev(event, minute, intensity), "waiting_reason": reason}


def _start(minute, stopped=None):
    return {**_ev("started", minute), "machine_stopped": stopped}


def _all(events, now_minute):
    return ticket_times(events, datetime(2026, 10, 20, 10, 0) + timedelta(minutes=now_minute))


class TestTicketTimesS019:

    def test_planned_stop_on_a_scheduled_defect(self):
        events = [_ev("raised", 0, "degraded"), _plan("scheduled", 10, "slot"), _start(100, stopped=1),
                  _ev("back_in_service", 290)]
        times = _all(events, 400)
        assert times["planned_downtime_minutes"] == 190
        assert times["downtime_minutes"] == 0
        assert times["waiting_minutes"] is None and times["waiting_by_reason"] is None
        assert times["response_minutes"] == 10 and times["repair_minutes"] == 190

    def test_not_stopped_has_no_planned_stop(self):
        events = [_ev("raised", 0, "degraded"), _plan("scheduled", 10, "slot"), _start(100, stopped=0),
                  _ev("back_in_service", 290)]
        assert _all(events, 400)["planned_downtime_minutes"] is None

    def test_breakdown_waiting_for_parts(self):
        """Started, scheduled for parts, started again, back in service: the waiting is out of
        repair, inside the downtime, and all logistic (parts)."""
        events = [_ev("raised", 0, "critical"), _ev("started", 10), _plan("scheduled", 40, "parts"),
                  _ev("started", 1000), _ev("back_in_service", 1060)]
        times = _all(events, 2000)
        assert times["repair_minutes"] == 30 + 60
        assert times["downtime_minutes"] == 1060
        assert times["waiting_minutes"] == 960
        assert times["waiting_by_reason"] == {"parts": 960}
        assert times["planned_downtime_minutes"] is None

    def test_the_reason_in_force_splits_the_waiting(self):
        events = [_ev("raised", 0, "critical"), _plan("scheduled", 10, "parts"), _plan("rescheduled", 110, "slot"),
                  _plan("rescheduled", 140, "other"), _ev("started", 200), _ev("back_in_service", 260)]
        times = _all(events, 300)
        assert times["waiting_by_reason"] == {"parts": 100, "slot": 30, "other": 60}
        assert times["waiting_minutes"] == 190
        assert times["response_minutes"] == 10

    def test_a_scheduled_defect_raised_to_critical_waits_from_the_regrade(self):
        events = [_ev("raised", 0, "degraded"), _plan("scheduled", 10, "parts"), _ev("regraded", 70, "critical"),
                  _ev("started", 100), _ev("back_in_service", 130)]
        times = _all(events, 200)
        assert times["waiting_minutes"] == 30 and times["waiting_by_reason"] == {"parts": 30}
        assert times["downtime_minutes"] == 60

    def test_a_planned_stop_ends_when_it_turns_critical(self):
        events = [_ev("raised", 0, "degraded"), _plan("scheduled", 10, "slot"), _start(100, stopped=1),
                  _ev("regraded", 150, "critical"), _ev("back_in_service", 200)]
        times = _all(events, 300)
        assert times["planned_downtime_minutes"] == 50
        assert times["downtime_minutes"] == 50

    def test_an_open_scheduled_breakdown_counts_to_now(self):
        events = [_ev("raised", 0, "critical"), _plan("scheduled", 20, "vendor")]
        times = _all(events, 500)
        assert times["response_minutes"] == 20
        assert times["downtime_minutes"] == 500
        assert times["waiting_minutes"] == 480 and times["waiting_by_reason"] == {"vendor": 480}
        assert times["repair_minutes"] is None

    def test_back_in_service_from_scheduled_without_a_start_makes_repair_unknown(self):
        """BR2-07: the last stretch of work is unknown, so the total is unknown."""
        events = [_ev("raised", 0, "critical"), _ev("started", 10), _plan("scheduled", 130, "parts"),
                  _ev("back_in_service", 300)]
        assert _all(events, 400)["repair_minutes"] is None

    def test_never_critical_while_scheduled_has_no_waiting(self):
        events = [_ev("raised", 0, "critical"), _ev("regraded", 5, "degraded"), _plan("scheduled", 10, "parts"),
                  _ev("started", 100), _ev("back_in_service", 130)]
        times = _all(events, 200)
        assert times["waiting_minutes"] is None and times["waiting_by_reason"] is None

    def test_an_open_planned_stop_counts_to_now(self):
        events = [_ev("raised", 0, "initial"), _plan("scheduled", 10, "slot"), _start(100, stopped=1)]
        assert _all(events, 160)["planned_downtime_minutes"] == 60

    def test_not_a_fault_from_scheduled_is_all_none(self):
        events = [_ev("raised", 0, "critical"), _plan("scheduled", 10, "parts"), _ev("closed_not_a_fault", 50)]
        assert set(_all(events, 100).values()) == {None}

    def test_s018_tickets_keep_their_figures_and_gain_empty_new_ones(self):
        events = [_ev("raised", 0, "critical"), _ev("acknowledged", 5), _ev("started", 15),
                  _ev("back_in_service", 75), _ev("closed", 200)]
        assert _all(events, 300) == {
            "response_minutes": 5, "repair_minutes": 60, "downtime_minutes": 75,
            "waiting_minutes": None, "waiting_by_reason": None, "planned_downtime_minutes": None,
        }


# ---------------------------------------------------------------------------
# S020 — parts used
# ---------------------------------------------------------------------------

def _part(**overrides):
    """The short way of § 8: a description, a number with the default kind, quantity 1."""
    return {"description": "Deep-groove ball bearing", "part_number": "6205-2RS", "number_kind": "generic",
            "quantity": "1", "node_id": 7, **overrides}


def _part_errors(**overrides):
    _, errors = validate_part(_part(**overrides))
    return [(e["field"], e["message"]) for e in errors]


class TestValidatePart:

    def test_the_short_way(self):
        clean, errors = validate_part(_part())
        assert errors == []
        assert clean == {"description": "Deep-groove ball bearing", "part_number": "6205-2RS", "maker": None,
                         "number_kind": "generic", "quantity": Decimal("1.00"), "qty_unit": "nos", "node_id": 7}

    def test_text_is_trimmed_and_empty_is_null(self):
        clean, errors = validate_part(_part(description="  Seal kit  ", part_number="  ", maker=" SKF "))
        assert errors == []
        assert (clean["description"], clean["part_number"], clean["number_kind"], clean["maker"]) == (
            "Seal kit", None, None, "SKF")

    @pytest.mark.parametrize("description", [None, "", "   "])
    def test_description_is_required(self, description):
        assert _part_errors(description=description) == [("description", PART_DESCRIPTION_NEEDED)]

    @pytest.mark.parametrize("field, maximum", [("description", 200), ("part_number", 60), ("maker", 100)])
    def test_a_text_longer_than_its_column(self, field, maximum):
        assert _part_errors(**{field: "x" * maximum}) == []
        assert _part_errors(**{field: "x" * (maximum + 1)}) == [(field, f"Too long (max {maximum})")]

    def test_a_kind_without_a_number_is_dropped(self):
        clean, errors = validate_part(_part(part_number=None, number_kind="maker"))
        assert errors == [] and clean["number_kind"] is None

    @pytest.mark.parametrize("kind", [None, "", "brand"])
    def test_a_number_needs_its_kind(self, kind):
        assert _part_errors(number_kind=kind) == [("number_kind", PART_KIND_NEEDED)]

    def test_a_makers_number_needs_the_maker(self):
        assert _part_errors(number_kind="maker") == [("maker", PART_MAKER_NEEDED)]
        assert _part_errors(number_kind="maker", maker="  ") == [("maker", PART_MAKER_NEEDED)]
        assert _part_errors(number_kind="maker", maker="Rexroth") == []

    def test_a_maker_with_no_number_is_allowed(self):
        """"Servo 68" by Indian Oil: a description and a maker, no number."""
        clean, errors = validate_part(_part(description="Servo 68", part_number=None, number_kind=None,
                                            maker="Indian Oil", quantity="5", qty_unit="L"))
        assert errors == []
        assert (clean["maker"], clean["number_kind"], clean["qty_unit"]) == ("Indian Oil", None, "L")

    @pytest.mark.parametrize("sent, stored", [
        ("2", Decimal("2.00")), (" 1.5 ", Decimal("1.50")), ("0.01", Decimal("0.01")), ("9999.99", Decimal("9999.99")),
        (3, Decimal("3.00")),
        (1.1, Decimal("1.10")),          # a JSON number: through str, never Decimal(float)
        ("1e2", Decimal("100.00")),      # judged on the value
        ("1.500", Decimal("1.50")),
    ])
    def test_quantities_accepted(self, sent, stored):
        clean, errors = validate_part(_part(quantity=sent))
        assert errors == []
        assert clean["quantity"] == stored and str(clean["quantity"]) == str(stored)

    @pytest.mark.parametrize("sent", [None, "", "abc", "1,5", "0", "-1", 0, -2.5, True, False, "NaN", "Infinity",
                                      "-inf", float("nan"), float("inf"), [1], {"q": 1}])
    def test_quantities_refused(self, sent):
        assert _part_errors(quantity=sent) == [("quantity", PART_QUANTITY_NEEDED)]

    @pytest.mark.parametrize("sent", ["1.505", 1.505, "0.001"])
    def test_more_than_two_decimals_is_refused_not_rounded(self, sent):
        assert _part_errors(quantity=sent) == [("quantity", PART_QUANTITY_DECIMALS)]

    @pytest.mark.parametrize("sent", ["10000", "9999.991", "1e100", 10000])
    def test_above_the_maximum(self, sent):
        assert _part_errors(quantity=sent) == [("quantity", PART_QUANTITY_TOO_BIG)]
        assert PART_QUANTITY_TOO_BIG == "At most 9999.99"

    def test_the_unit(self):
        for unit in PART_UNITS:
            assert validate_part(_part(qty_unit=unit))[0]["qty_unit"] == unit
        assert validate_part(_part())[0]["qty_unit"] == "nos"
        for unit in ("", "mtr", "NOS", 5):
            assert _part_errors(qty_unit=unit) == [("qty_unit", PART_UNIT_NEEDED)]

    @pytest.mark.parametrize("node_id", [None, 0, -1, "7", True, 1.0])
    def test_the_node_is_an_id(self, node_id):
        assert _part_errors(node_id=node_id) == [("node_id", PART_NODE_NEEDED)]

    def test_errors_come_in_field_order(self):
        _, errors = validate_part({})
        assert _fields(errors) == ["description", "quantity", "node_id"]

    def test_the_lists(self):
        assert PART_UNITS == ("nos", "set", "m", "L", "kg")
        assert PART_KINDS == ("maker", "generic")
        assert PARTS_HINT_ACTION_CODES == ("1", "3", "10")


# ---------------------------------------------------------------------------
# Work notes (S027 § 8)
# ---------------------------------------------------------------------------

class TestValidateNote:

    @pytest.mark.parametrize("body", [{}, {"remark": None}, {"remark": ""}, {"remark": "  \n "}])
    def test_missing_or_blank_is_enter_a_note(self, body):
        assert validate_note(body)[1] == [{"field": "remark", "message": NOTE_NEEDED}]
        assert NOTE_NEEDED == "Enter a note"

    @pytest.mark.parametrize("value", [12, ["Belt loose"]])
    def test_not_text(self, value):
        assert validate_note({"remark": value})[1] == [{"field": "remark", "message": "Must be text"}]

    def test_the_length_limit(self):
        assert validate_note({"remark": "x" * REMARK_MAX}) == ({"remark": "x" * REMARK_MAX}, [])
        assert validate_note({"remark": "x" * (REMARK_MAX + 1)})[1] == [
            {"field": "remark", "message": "Too long (max 1000)"}]

    def test_trimmed_with_the_line_breaks_kept(self):
        text = "  Pressure not reached in Pilot line.\nReason not known yet \n"
        assert validate_note({"remark": text}) == (
            {"remark": "Pressure not reached in Pilot line.\nReason not known yet"}, [])


class TestTicketTimesWithNotes:

    @staticmethod
    def _with_notes(events):
        """A note one minute after every event: notes in every state."""
        out = []
        for event in events:
            out += [event, {"event": NOTE_EVENT, "occurred_at": event["occurred_at"] + timedelta(minutes=1),
                            "intensity": None}]
        return out

    @pytest.mark.parametrize("events, now_minute", [
        # Response, repair and downtime, with a send-back
        ([_ev("raised", 0, "critical"), _ev("acknowledged", 5), _ev("started", 15), _ev("back_in_service", 75),
          _ev("sent_back", 100), _ev("back_in_service", 130), _ev("closed", 200)], 300),
        # Waiting by reason on a breakdown
        ([_ev("raised", 0, "critical"), _ev("started", 10), _plan("scheduled", 40, "parts"),
          _plan("rescheduled", 400, "slot"), _ev("started", 1000), _ev("back_in_service", 1060)], 2000),
        # A planned stop on a scheduled defect
        ([_ev("raised", 0, "degraded"), _plan("scheduled", 10, "slot"), _start(100, stopped=1),
          _ev("back_in_service", 290)], 400),
        # Still open, counting to now
        ([_ev("raised", 0, "critical"), _ev("started", 10)], 70),
    ])
    def test_notes_change_no_figure(self, events, now_minute):
        assert NOTE_EVENT not in ORDERED_EVENTS
        assert _all(self._with_notes(events), now_minute) == _all(events, now_minute)
