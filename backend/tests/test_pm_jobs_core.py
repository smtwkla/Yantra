"""PM jobs core — the pure rules of the job a plan makes (docs/steps/S097-pm-jobs-due/1-brief.md § 5.1, § 8.2;
R03.3): what the daily run and the plan save do with a plan's open job, the copies of the due point a job stores,
the usage carried across a counter reset, the list's tab and order, the serial and the assignee.  No database."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from config_rbac import ASSIGNABLE_ROLES
from pm_jobs_core import (
    BASE_STATES, CANCEL, CANCELLED, CREATE, CREATE_STANDINGS, DONE, DUE_STATE, IN_PROGRESS, JOB_BASE, JOB_STATES,
    NODE_SCRAPPED_REMARK, OPEN_STATES, READ_KEY, READING_BASE, REFRESH, SEED_BASE, SKIPPED, TAB_DONE, TAB_DUE,
    TAB_TO_VERIFY, TAB_UPCOMING, TABS, TEMPLATE_INACTIVE_REMARK, UNLINKED_REMARK, VERIFIED, assignable_id, days_past,
    decide, does_not_apply_remark, due_copies, due_from_job, job_changes, job_override, job_standing, list_order,
    meter_base_source, meter_offset, not_for_machine_remark, pm_serial, seed_matches, tab_of,
)
from pm_schedule_core import BEFORE_USE, BOTH, CALENDAR, DUE, METER, NOT_YET, OVERDUE, UPCOMING, Due

STANDINGS = (NOT_YET, UPCOMING, DUE, OVERDUE)


def test_the_constants():
    assert JOB_STATES == ("due", "in_progress", "done", "verified", "skipped", "cancelled")
    assert OPEN_STATES == (DUE_STATE, IN_PROGRESS)
    assert BASE_STATES == (DONE, VERIFIED, SKIPPED)   # S101: the next job counts from a skip too (R03 Q9.2 a)
    assert CREATE_STANDINGS == (UPCOMING, DUE, OVERDUE)
    # S098: the Done tab; S099: To verify between Upcoming and Done
    assert TABS == (TAB_DUE, TAB_UPCOMING, TAB_TO_VERIFY, TAB_DONE) == ("due", "upcoming", "to_verify", "done")
    assert SKIPPED in JOB_STATES and CANCELLED in JOB_STATES
    assert READ_KEY == "pm_job:read"   # S102: one copy, for pm_jobs.py, pm_work.py and alerts_core


# ---------------------------------------------------------------------------
# decide: § 5.5's table, row by row
# ---------------------------------------------------------------------------

def _decide(stop=None, before_use=False, scrapped=False, open_state=None, standing=NOT_YET):
    return decide(stop, before_use, scrapped, open_state, standing)


# S104 § 5.4: the plan's stop remark replaces S097's plan_active; any remark stops it the same way
STOPS = [TEMPLATE_INACTIVE_REMARK, UNLINKED_REMARK, does_not_apply_remark("no Run hours meter on HP003")]


@pytest.mark.parametrize("stop", [None, *STOPS])
@pytest.mark.parametrize("scrapped", [True, False])
@pytest.mark.parametrize("standing", [None, *STANDINGS])
def test_a_started_job_is_left_to_r03_4(stop, scrapped, standing):
    assert _decide(stop=stop, scrapped=scrapped, open_state=IN_PROGRESS, standing=standing) is None


@pytest.mark.parametrize("stop", STOPS)
def test_a_stopped_plan_cancels_its_due_job_with_its_remark(stop):
    assert _decide(stop=stop, open_state=DUE_STATE, standing=None) == (CANCEL, stop)


def test_a_scrapped_node_cancels_the_due_job_of_a_plan_in_force():
    assert _decide(scrapped=True, open_state=DUE_STATE, standing=None) == (CANCEL, NODE_SCRAPPED_REMARK)


def test_a_stopped_plan_on_a_scrapped_node_gives_the_plan_s_remark():
    assert _decide(stop=UNLINKED_REMARK, scrapped=True, open_state=DUE_STATE) == (CANCEL, UNLINKED_REMARK)


@pytest.mark.parametrize("stop, scrapped", [(TEMPLATE_INACTIVE_REMARK, False), (None, True), (UNLINKED_REMARK, True)])
@pytest.mark.parametrize("standing", [None, *STANDINGS])
def test_a_stopped_plan_or_a_scrapped_node_without_a_job_does_nothing(stop, scrapped, standing):
    assert _decide(stop=stop, scrapped=scrapped, standing=standing) is None


def test_the_remarks():
    assert not_for_machine_remark("Hand-greased") == "Not for this machine: Hand-greased"
    assert does_not_apply_remark("no Run hours meter on HP003") == "Does not apply: no Run hours meter on HP003."


@pytest.mark.parametrize("open_state", [None, DUE_STATE])
def test_a_before_use_plan_makes_no_job(open_state):
    assert _decide(before_use=True, open_state=open_state, standing=NOT_YET) is None
    assert _decide(before_use=True, open_state=open_state, standing=None) is None


def test_a_plan_not_yet_in_its_window_makes_no_job():
    assert _decide(standing=NOT_YET) is None


@pytest.mark.parametrize("standing", [UPCOMING, DUE, OVERDUE])
def test_a_plan_in_its_window_or_past_it_makes_a_job(standing):
    assert _decide(standing=standing) == (CREATE, None)


@pytest.mark.parametrize("standing", STANDINGS)
def test_an_active_plan_refreshes_its_due_job_at_any_standing(standing):
    assert _decide(open_state=DUE_STATE, standing=standing) == (REFRESH, None)


def test_decide_needs_the_standing_to_create():
    with pytest.raises(ValueError, match="standing_state"):
        _decide(standing=None)


@pytest.mark.parametrize("state", [DONE, CANCELLED, "open"])
def test_decide_refuses_a_state_that_is_not_open(state):
    with pytest.raises(ValueError, match="open_state"):
        _decide(open_state=state)


def test_decide_refuses_an_unknown_standing():
    with pytest.raises(ValueError, match="standing_state"):
        _decide(standing="late")


@pytest.mark.parametrize("field", ["before_use", "node_scrapped"])
def test_decide_refuses_a_flag_that_is_not_a_bool(field):
    flags = {"before_use": False, "node_scrapped": False}
    flags[field] = 1
    with pytest.raises(TypeError, match=field):
        decide(None, flags["before_use"], flags["node_scrapped"], None, UPCOMING)


@pytest.mark.parametrize("stop", [True, False, "", 1])
def test_decide_refuses_a_stop_that_is_not_a_remark(stop):
    with pytest.raises(TypeError, match="stop"):
        decide(stop, False, False, None, UPCOMING)


# ---------------------------------------------------------------------------
# The copies of the due point
# ---------------------------------------------------------------------------

CALENDAR_DUE = Due(date(2026, 11, 2), None, 3, 3, None, rescheduled=False, before_use=False)
METER_DUE = Due(None, Decimal("5000"), None, None, Decimal("25"), rescheduled=False, before_use=False)
BOTH_DUE = Due(date(2026, 12, 2), Decimal("3250"), 3, 3, Decimal("25"), rescheduled=False, before_use=False)


@pytest.mark.parametrize("due", [CALENDAR_DUE, METER_DUE, BOTH_DUE])
def test_the_copies_go_back_to_the_same_due(due):
    copies = due_copies(due, Decimal("0"))
    assert copies == {"due_on": due.due_on, "due_meter": due.due_meter, "grace_days": due.grace_days,
                      "upcoming_days": due.upcoming_days, "meter_window": due.meter_window,
                      "meter_offset": Decimal("0"), "rescheduled_on": None, "rescheduled_meter": None}
    assert due_from_job({**copies, "id": 7, "serial": "PM-2026-11-001"}) == due


def test_the_copies_take_the_column_s_three_decimals():
    """CR1-01: 10 % of a 3-decimal meter_every has 4 decimals; the copy is rounded as DECIMAL(14,3) stores it, so a
    job that stores the rounded value is not refreshed again."""
    due = Due(None, Decimal("2500.0005"), None, None, Decimal("25.0005"), rescheduled=False, before_use=False)
    copies = due_copies(due, Decimal("0.0005"))
    assert (copies["due_meter"], copies["meter_window"], copies["meter_offset"]) == (
        Decimal("2500.001"), Decimal("25.001"), Decimal("0.001"))
    stored = {"id": 1, "assignee_id": None, "due_on": None, "due_meter": Decimal("2500.001"), "grace_days": None,
              "upcoming_days": None, "meter_window": Decimal("25.001"), "meter_offset": Decimal("0.001"),
              "rescheduled_on": None, "rescheduled_meter": None}
    assert job_changes(stored, copies, None) == {}


# S102 § 5.3: the standing, one copy for the list and the alert scan

def _meter_job(offset):
    """A meter job due at 1500, window 50 (the reschedule columns None, as a pm_jobs row carries them, BS1-01)."""
    return {"due_on": None, "due_meter": Decimal("1500.000"), "grace_days": None, "upcoming_days": None,
            "meter_window": Decimal("50.000"), "meter_offset": offset, "rescheduled_on": None,
            "rescheduled_meter": None}


def test_job_standing_adds_the_offset():
    """A reading of 1490 with an offset of 20 counts as 1510: *Due*; without the offset it would be *Upcoming*."""
    standing = job_standing(_meter_job(Decimal("20.000")), Decimal("1490"), date(2026, 11, 20))
    assert (standing.state, standing.trigger) == (DUE, METER)
    assert job_standing(_meter_job(Decimal("0.000")), Decimal("1490"), date(2026, 11, 20)).state == UPCOMING


def test_job_standing_with_no_reading():
    standing = job_standing(_meter_job(Decimal("20.000")), None, date(2026, 11, 20))
    assert (standing.state, standing.no_reading) == (NOT_YET, True)


# S101: the reschedule (§ 5.1)

MOVED = Due(date(2026, 12, 12), Decimal("3300"), 3, 3, Decimal("25"), rescheduled=True, before_use=False)


def test_the_copies_carry_the_override():
    override = {"due_on": date(2026, 12, 12), "due_meter": Decimal("3300.0004")}
    copies = due_copies(MOVED, Decimal("0"), override)
    assert (copies["due_on"], copies["rescheduled_on"]) == (date(2026, 12, 12), date(2026, 12, 12))
    # Rounded as the other meter columns, so the stored row equals the copy (and chk_pm_jobs_rescheduled holds)
    assert copies["rescheduled_meter"] == Decimal("3300.000")
    one = due_copies(MOVED, Decimal("0"), {"due_on": date(2026, 12, 12), "due_meter": None})
    assert (one["rescheduled_on"], one["rescheduled_meter"]) == (date(2026, 12, 12), None)


def test_due_from_job_reads_the_reschedule():
    copies = due_copies(MOVED, Decimal("0"), {"due_on": date(2026, 12, 12), "due_meter": None})
    assert due_from_job(copies).rescheduled is True
    assert due_from_job({**copies, "rescheduled_on": None, "rescheduled_meter": Decimal("3300")}).rescheduled is True
    assert due_from_job({**copies, "rescheduled_on": None}).rescheduled is False


def _moved_job(on=date(2026, 12, 12), meter=Decimal("3300")):
    return {"rescheduled_on": on, "rescheduled_meter": meter}


@pytest.mark.parametrize("kind, expected", [
    (CALENDAR, {"due_on": date(2026, 12, 12), "due_meter": None}),
    (METER, {"due_on": None, "due_meter": Decimal("3300")}),
    (BOTH, {"due_on": date(2026, 12, 12), "due_meter": Decimal("3300")}),
    (BEFORE_USE, None),
])
def test_job_override_keeps_the_plan_s_triggers_only(kind, expected):
    assert job_override(_moved_job(), kind) == expected


def test_job_override_is_none_without_a_move():
    assert job_override(_moved_job(None, None), BOTH) is None
    assert job_override(_moved_job(meter=None), METER) is None      # the date move of a plan that lost its calendar
    assert job_override(_moved_job(on=None), CALENDAR) is None


def test_job_override_refuses_an_unknown_kind():
    with pytest.raises(ValueError, match="trigger_kind"):
        job_override(_moved_job(), "weekly")


def test_the_copies_carry_the_offset():
    assert due_copies(METER_DUE, Decimal("1200"))["meter_offset"] == Decimal("1200")


def test_due_copies_refuses_a_float_offset_and_a_negative_one():
    with pytest.raises(TypeError, match="offset"):
        due_copies(METER_DUE, 1.5)
    with pytest.raises(ValueError, match="offset"):
        due_copies(METER_DUE, Decimal("-1"))


def test_due_copies_refuses_a_before_use_due():
    with pytest.raises(ValueError, match="before_use"):
        due_copies(Due(None, None, None, None, None, rescheduled=False, before_use=True), Decimal("0"))


def test_due_from_job_refuses_a_datetime():
    job = {**due_copies(CALENDAR_DUE, Decimal("0")), "due_on": datetime(2026, 11, 2, 0, 0)}
    with pytest.raises(TypeError, match="due_on"):
        due_from_job(job)


def _job(due=BOTH_DUE, offset=Decimal("0"), assignee_id=5):
    """A pm_jobs row as the database gives it: the DECIMAL(14,3) columns carry three places."""
    copies = due_copies(due, offset)
    row = {key: (value.quantize(Decimal("0.001")) if isinstance(value, Decimal) else value)
           for key, value in copies.items()}
    return {"id": 1, "serial": "PM-2026-11-001", "state": DUE_STATE, "assignee_id": assignee_id, **row}


def test_job_changes_nothing_changed():
    assert job_changes(_job(), due_copies(BOTH_DUE, Decimal("0")), 5) == {}


@pytest.mark.parametrize("column, value", [
    ("due_on", date(2026, 12, 9)), ("due_meter", Decimal("3300")), ("grace_days", 4), ("upcoming_days", 4),
    ("meter_window", Decimal("30")), ("meter_offset", Decimal("120")),
])
def test_job_changes_each_column_alone(column, value):
    copies = {**due_copies(BOTH_DUE, Decimal("0")), column: value}
    assert job_changes(_job(), copies, 5) == {column: value}


def test_job_changes_the_assignee_to_none():
    assert job_changes(_job(), due_copies(BOTH_DUE, Decimal("0")), None) == {"assignee_id": None}


def test_job_changes_the_meter_due_point_from_none():
    """A `both` plan whose meter had no base value (S095 D9) gets one after the first reading."""
    no_base = Due(BOTH_DUE.due_on, None, 3, 3, Decimal("25"), rescheduled=False, before_use=False)
    assert job_changes(_job(no_base), due_copies(BOTH_DUE, Decimal("0")), 5) == {"due_meter": Decimal("3250")}


# ---------------------------------------------------------------------------
# The usage carried across a counter reset (§ 5.4)
# ---------------------------------------------------------------------------

def _r(value, reset=False):
    return {"value": Decimal(value), "is_reset": reset}


def test_no_reset_gives_no_offset():
    assert meter_offset(Decimal("1000"), [_r("1100"), _r("1200")]) == 0
    assert meter_offset(Decimal("1000"), []) == 0


def test_the_first_worked_example():
    """Base 1,000 h; 1,100, 1,200, a reset at 50, then 80: offset 1,200, counted 1,280."""
    offset = meter_offset(Decimal("1000"), [_r("1100"), _r("1200"), _r("50", True), _r("80")])
    assert offset == Decimal("1200")
    assert Decimal("80") + offset == Decimal("1280")


def test_the_second_worked_example():
    """Two resets: 1,000; 1,200; reset 10; 300; reset 5; 40: offset 1,500, counted 1,540."""
    offset = meter_offset(Decimal("1000"), [_r("1200"), _r("10", True), _r("300"), _r("5", True), _r("40")])
    assert offset == Decimal("1500")
    assert Decimal("40") + offset == Decimal("1540")


def test_a_reset_first_after_the_base_adds_the_base():
    assert meter_offset(Decimal("1000"), [_r("20", True), _r("60")]) == Decimal("1000")


def test_no_base_gives_no_offset():
    assert meter_offset(None, [_r("20", True), _r("60")]) == 0


def test_meter_offset_refuses_a_float():
    with pytest.raises(TypeError, match="value"):
        meter_offset(Decimal("1000"), [{"value": 50.0, "is_reset": True}])
    with pytest.raises(TypeError, match="base_value"):
        meter_offset(1000.0, [])


# ---------------------------------------------------------------------------
# The list: days past, tab, order
# ---------------------------------------------------------------------------

TODAY = date(2026, 11, 10)


def test_days_past():
    assert days_past(TODAY, TODAY) is None
    assert days_past(date(2026, 11, 9), TODAY) == 1
    assert days_past(date(2026, 11, 7), TODAY) == 3
    assert days_past(date(2026, 11, 12), TODAY) is None
    assert days_past(None, TODAY) is None


def test_days_past_refuses_a_datetime():
    with pytest.raises(TypeError, match="today"):
        days_past(TODAY, datetime(2026, 11, 10, 9, 0))
    with pytest.raises(TypeError, match="due_on"):
        days_past(datetime(2026, 11, 10, 9, 0), TODAY)


@pytest.mark.parametrize("state, tab", [(OVERDUE, TAB_DUE), (DUE, TAB_DUE), (UPCOMING, TAB_UPCOMING),
                                        (NOT_YET, TAB_UPCOMING)])
def test_tab_of(state, tab):
    assert tab_of(DUE_STATE, state) == tab


@pytest.mark.parametrize("standing", [OVERDUE, DUE, UPCOMING, NOT_YET])
def test_tab_of_a_started_job_is_due_whatever_its_standing(standing):
    """S098 § 5.9: work begun belongs to now."""
    assert tab_of(IN_PROGRESS, standing) == TAB_DUE


def test_tab_of_refuses_an_unknown_state():
    with pytest.raises(ValueError, match="standing_state"):
        tab_of(DUE_STATE, "late")
    with pytest.raises(ValueError, match="state must be one of"):
        tab_of(DONE, DUE)


def _item(serial, state, due_on, job_state=DUE_STATE):
    return {"serial": serial, "state": job_state, "standing": {"state": state}, "due_on": due_on}


def test_list_order_puts_the_started_jobs_first():
    """S098 § 5.9: a started job before an overdue one."""
    items = [_item("PM-2026-11-001", OVERDUE, date(2026, 10, 20)),
             _item("PM-2026-11-009", NOT_YET, date(2026, 12, 1), IN_PROGRESS),
             _item("PM-2026-11-008", DUE, date(2026, 11, 9), IN_PROGRESS)]
    assert [item["serial"] for item in sorted(items, key=list_order)] == [
        "PM-2026-11-008", "PM-2026-11-009", "PM-2026-11-001"]


def test_list_order():
    items = [
        _item("PM-2026-11-006", NOT_YET, date(2026, 12, 1)),
        _item("PM-2026-11-005", UPCOMING, date(2026, 11, 12)),
        _item("PM-2026-11-004", DUE, None),
        _item("PM-2026-11-003", DUE, date(2026, 11, 9)),
        _item("PM-2026-11-007", DUE, date(2026, 11, 9)),
        _item("PM-2026-11-002", OVERDUE, date(2026, 11, 1)),
        _item("PM-2026-11-001", OVERDUE, date(2026, 10, 20)),
    ]
    assert [item["serial"] for item in sorted(items, key=list_order)] == [
        "PM-2026-11-001", "PM-2026-11-002", "PM-2026-11-003", "PM-2026-11-007", "PM-2026-11-004",
        "PM-2026-11-005", "PM-2026-11-006",
    ]


# ---------------------------------------------------------------------------
# Serial and assignee
# ---------------------------------------------------------------------------

def test_pm_serial():
    assert pm_serial(2026, 11, 1) == "PM-2026-11-001"
    assert pm_serial(2026, 11, 1000) == "PM-2026-11-1000"


@pytest.mark.parametrize("role", ASSIGNABLE_ROLES)
def test_an_assignable_person_keeps_the_job(role):
    assert assignable_id(9, {"id": 9, "name": "Ravi", "role": role}) == 9


@pytest.mark.parametrize("role", ["maint_operator", "maint_supervisor", "maint_storekeeper"])
def test_a_person_without_an_assignable_role_leaves_the_job_unassigned(role):
    assert assignable_id(9, {"id": 9, "name": "Ravi", "role": role}) is None


def test_a_person_not_found_or_no_assignee_leaves_the_job_unassigned():
    assert assignable_id(9, None) is None
    assert assignable_id(None, None) is None


# ---------------------------------------------------------------------------
# The meter base follows the meter (S104 § 5.3, BR1-01)
# ---------------------------------------------------------------------------

PRESS_HOURS = (4, 7)     # (node id, meter type id): the parent's Run hours
PART_HOURS = (5, 7)      # the part's own Run hours, added later
OIL_TEMP = (4, 8)


def _last(meter):
    """A base job's copied meter, as ``_last_base_job`` reads it."""
    return {"meter_equipment_id": meter and meter[0], "meter_type_id": meter and meter[1]}


def _seeded(value, meter):
    """A plan row with a *Last done* meter value and the meter it was entered for."""
    return {"last_done_meter": value, "seed_meter_equipment_id": meter and meter[0],
            "seed_meter_type_id": meter and meter[1]}


class TestSeedMatches:

    def test_the_seed_of_this_meter(self):
        assert seed_matches(_seeded(Decimal("1840"), PRESS_HOURS), PRESS_HOURS) is True

    def test_the_same_type_on_another_node_is_another_meter(self):
        assert seed_matches(_seeded(Decimal("1840"), PRESS_HOURS), PART_HOURS) is False

    def test_the_same_node_with_another_type_is_another_meter(self):
        assert seed_matches(_seeded(Decimal("1840"), PRESS_HOURS), OIL_TEMP) is False

    def test_no_value_no_meter_or_no_stored_meter_matches_nothing(self):
        assert seed_matches(_seeded(None, PRESS_HOURS), PRESS_HOURS) is False
        assert seed_matches(_seeded(Decimal("1840"), PRESS_HOURS), None) is False
        assert seed_matches(_seeded(Decimal("1840"), None), PRESS_HOURS) is False

    def test_a_list_pair_is_a_meter_too(self):
        assert seed_matches(_seeded(Decimal("1840"), PRESS_HOURS), list(PRESS_HOURS)) is True


class TestMeterBaseSource:

    def test_a_base_job_of_this_meter_gives_its_done_meter(self):
        assert meter_base_source(_last(PRESS_HOURS), _seeded(None, None), PRESS_HOURS) == JOB_BASE

    def test_a_base_job_of_another_meter_is_not_the_base(self):
        # the part gained its own hour meter after a job counted on the press's: read the part's own readings
        assert meter_base_source(_last(PRESS_HOURS), _seeded(None, None), PART_HOURS) == READING_BASE
        assert meter_base_source(_last(PRESS_HOURS), _seeded(None, None), OIL_TEMP) == READING_BASE

    def test_a_job_with_no_copied_meter_is_not_the_base_of_any_meter(self):
        assert meter_base_source(_last(None), _seeded(None, None), PART_HOURS) == READING_BASE

    def test_a_base_job_decides_even_when_a_seed_matches(self):
        seed = _seeded(Decimal("1840"), PART_HOURS)
        assert meter_base_source(_last(PRESS_HOURS), seed, PART_HOURS) == READING_BASE
        assert meter_base_source(_last(PART_HOURS), seed, PART_HOURS) == JOB_BASE

    def test_without_a_job_a_seed_of_this_meter_is_the_base(self):
        assert meter_base_source(None, _seeded(Decimal("1840"), PRESS_HOURS), PRESS_HOURS) == SEED_BASE

    def test_without_a_job_a_seed_of_another_meter_is_not_used(self):
        assert meter_base_source(None, _seeded(Decimal("1840"), PRESS_HOURS), PART_HOURS) == READING_BASE

    def test_without_a_job_or_a_seed_the_readings_decide(self):
        assert meter_base_source(None, _seeded(None, None), PRESS_HOURS) == READING_BASE
