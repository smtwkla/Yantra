"""pm_work_core (S098 § 5.1, § 8.2): the pure rules of doing one PM job.  No database."""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

import pm_work_core as core
from meters_core import COUNTER, GAUGE, ONLY_A_COUNTER_RESETS, RESET_NOT_BOOL
from pm_jobs_core import CANCELLED, DONE, DUE_STATE, IN_PROGRESS, JOB_STATES, SKIPPED, VERIFIED
from pm_schedule_core import BEFORE_USE, BOTH, CALENDAR, METER
from pm_templates_core import CHECK, READING, TASK
from tickets_core import EVENT_TIME_FUTURE, LABOUR_DATE_FORMAT, PLANNED_DATE_PAST, PLANNED_DATE_TOO_FAR

NOW = datetime(2026, 10, 27, 9, 10)


def _item(item_id, position, item_type=CHECK, **fields):
    """A template item as the shell hands it to result_rows (S104): its meter already resolved on the machine."""
    return {"id": item_id, "position": position, "item_type": item_type, "text": f"Item {position}",
            "help_text": None, "photo": "optional", "reading_kind": None, "unit": None, "min_value": None,
            "max_value": None, "meter_equipment_id": None, "meter_type_id": None, **fields}


def _result(item_type=CHECK, **fields):
    return {"item_type": item_type, "min_value": None, "max_value": None, "outcome": None, "value": None,
            "limit_state": None, "remark": None, **fields}


# ---------------------------------------------------------------------------
# result_rows
# ---------------------------------------------------------------------------

def test_result_rows_copy_every_column_and_keep_the_order():
    items = [_item(11, 1), _item(12, 2, READING, reading_kind="measurement", unit="°C", min_value=Decimal(30),
                                 max_value=Decimal(60), help_text="At the power pack", photo="required"),
             _item(13, 3, READING, reading_kind="meter", meter_equipment_id=5, meter_type_id=7)]
    rows = core.result_rows(items)
    assert [row["template_item_id"] for row in rows] == [11, 12, 13]
    assert rows[1] == {
        "template_item_id": 12, "position": 2, "item_type": READING, "text": "Item 2",
        "help_text": "At the power pack", "photo": "required", "reading_kind": "measurement", "unit": "°C",
        "min_value": Decimal(30), "max_value": Decimal(60), "meter_equipment_id": None, "meter_type_id": None,
        "outcome": None, "value": None, "limit_state": None, "remark": None, "reading_id": None, "filled_at": None,
        "filled_by": None}
    assert (rows[2]["reading_kind"], rows[2]["meter_equipment_id"], rows[2]["meter_type_id"]) == ("meter", 5, 7)
    assert core.result_rows([]) == []


# ---------------------------------------------------------------------------
# validate_result
# ---------------------------------------------------------------------------

def _clean(outcome=None, value=None, limit_state=None, remark=None, is_reset=False):
    return {"outcome": outcome, "value": value, "limit_state": limit_state, "remark": remark, "is_reset": is_reset}


@pytest.mark.parametrize("item_type, outcome", [
    (CHECK, "ok"), (CHECK, "na"), (TASK, "done"),
])
def test_an_outcome_of_its_type_passes(item_type, outcome):
    assert core.validate_result({"outcome": outcome}, _result(item_type), None) == (_clean(outcome), None)


@pytest.mark.parametrize("item_type, body", [
    (CHECK, {}), (CHECK, {"outcome": "done"}), (CHECK, {"outcome": "nonsense"}), (CHECK, {"outcome": "ok", "value": 3}),
    (TASK, {}), (TASK, {"outcome": "ok"}), (TASK, {"outcome": "na"}), (TASK, {"outcome": "done", "value": "3"}),
    (READING, {}), (READING, {"outcome": "ok"}), (READING, {"value": ""}), (READING, {"outcome": "done", "value": 3}),
])
def test_another_outcome_or_none_is_refused(item_type, body):
    assert core.validate_result(body, _result(item_type), None) == (None, ("outcome", core.CHOOSE_OUTCOME[item_type]))


def test_the_three_choose_texts():
    assert core.CHOOSE_OUTCOME == {CHECK: "Choose OK, Not OK or NA.", TASK: "Choose Done or Not done.",
                                   READING: "Enter the reading, or tap NA."}


def test_a_reading_with_a_value_and_na_is_refused():
    body = {"outcome": "na", "value": "12", "remark": "Gauge broken"}
    assert core.validate_result(body, _result(READING), None) == (None, ("value", core.VALUE_OR_NA))


@pytest.mark.parametrize("item_type, outcome, message", [
    (CHECK, "not_ok", "Say what is wrong."), (TASK, "not_done", "Say why it was not done."),
    (READING, "na", "Say why there is no reading."),
])
def test_a_remark_is_needed_for_not_ok_not_done_and_a_reading_s_na(item_type, outcome, message):
    for remark in (None, "", "   "):
        assert core.validate_result({"outcome": outcome, "remark": remark}, _result(item_type), None) == (
            None, ("remark", message))
    clean, error = core.validate_result({"outcome": outcome, "remark": "  Oil seeping  "}, _result(item_type), None)
    assert error is None and clean == _clean(outcome, remark="Oil seeping")


def test_a_remark_is_accepted_with_ok_and_a_check_s_na_needs_none():
    assert core.validate_result({"outcome": "ok", "remark": "Fine"}, _result(), None) == (_clean("ok", remark="Fine"),
                                                                                          None)
    assert core.validate_result({"outcome": "ok", "remark": "  "}, _result(), None) == (_clean("ok"), None)


def test_a_remark_must_be_text_of_at_most_500():
    assert core.validate_result({"outcome": "ok", "remark": 5}, _result(), None) == (None, ("remark",
                                                                                            "Remark must be text"))
    assert core.validate_result({"outcome": "ok", "remark": "x" * 501}, _result(), None) == (
        None, ("remark", "Remark must be at most 500 characters"))
    assert core.validate_result({"outcome": "ok", "remark": "x" * 500}, _result(), None)[1] is None


def test_a_free_reading_value_may_be_negative_and_has_three_decimals():
    clean, error = core.validate_result({"value": "-12.125"}, _result(READING), None)
    assert error is None and clean == _clean(value=Decimal("-12.125"))
    assert core.validate_result({"value": "1.0005"}, _result(READING), None) == (
        None, ("value", "Enter a number with up to 3 decimals"))
    assert core.validate_result({"value": "abc"}, _result(READING), None)[1][0] == "value"


def test_a_meter_reading_takes_the_meter_type_s_rules():
    one_decimal = {"kind": GAUGE, "decimals": 1}
    assert core.validate_result({"value": "48.5"}, _result(READING), one_decimal)[0]["value"] == Decimal("48.5")
    assert core.validate_result({"value": "48.55"}, _result(READING), one_decimal) == (
        None, ("value", "Enter a number with up to 1 decimal"))
    counter = {"kind": COUNTER, "decimals": 0}
    assert core.validate_result({"value": "-1"}, _result(READING), counter) == (
        None, ("value", "A counter cannot be below zero"))
    clean, error = core.validate_result({"value": "10", "is_reset": True}, _result(READING), counter)
    assert error is None and clean["is_reset"] is True


def test_the_reset_mark_through_validate_reading():
    gauge = {"kind": GAUGE, "decimals": 0}
    assert core.validate_result({"value": "10", "is_reset": True}, _result(READING), gauge) == (
        None, ("is_reset", ONLY_A_COUNTER_RESETS))
    assert core.validate_result({"value": "10", "is_reset": True}, _result(READING), None) == (
        None, ("is_reset", ONLY_A_COUNTER_RESETS))
    assert core.validate_result({"value": "10", "is_reset": "yes"}, _result(READING), {"kind": COUNTER,
                                                                                    "decimals": 0}) == (
        None, ("is_reset", RESET_NOT_BOOL))


@pytest.mark.parametrize("value, state", [
    ("212", "high"), ("29.9", "low"), ("45", None), ("30", None), ("60", None),
])
def test_limit_state_from_the_result_s_copied_limits(value, state):
    result = _result(READING, min_value=Decimal(30), max_value=Decimal(60))
    assert core.validate_result({"value": value}, result, None)[0]["limit_state"] == state


def test_no_limits_no_limit_state_and_na_has_none():
    assert core.validate_result({"value": "212"}, _result(READING), None)[0]["limit_state"] is None
    result = _result(READING, min_value=Decimal(30), max_value=Decimal(60))
    assert core.validate_result({"outcome": "na", "remark": "No gauge"}, result, None)[0] == _clean(
        "na", remark="No gauge")


def test_validate_result_bad_input_is_a_shell_bug():
    with pytest.raises(TypeError):
        core.validate_result(["ok"], _result(), None)
    with pytest.raises(ValueError):
        core.validate_result({}, _result("photo"), None)


# ---------------------------------------------------------------------------
# result_changes, is_filled, unfilled_count
# ---------------------------------------------------------------------------

def test_result_changes_nothing_changed_is_empty():
    stored = _result(READING, value=Decimal("212.000"), limit_state="high")
    assert core.result_changes(stored, _clean(value=Decimal("212"), limit_state="high")) == {}
    assert core.result_changes(stored, _clean(value=Decimal("212"), limit_state="high"), linked_reset=False) == {}


def test_result_changes_each_field_alone():
    stored = _result(CHECK, outcome="not_ok", remark="Leak")
    assert core.result_changes(stored, _clean("ok")) == {"outcome": "ok", "remark": None}
    assert core.result_changes(stored, _clean("not_ok", remark="Big leak")) == {"remark": "Big leak"}
    reading = _result(READING, value=Decimal(1270))
    assert core.result_changes(reading, _clean(value=Decimal(1275))) == {"value": Decimal(1275)}
    assert core.result_changes(reading, _clean(value=Decimal(1270), limit_state="high")) == {"limit_state": "high"}
    assert core.result_changes(reading, _clean("na", remark="Broken")) == {"outcome": "na", "value": None,
                                                                         "remark": "Broken"}


def test_result_changes_the_same_value_with_another_reset_mark_is_a_change():
    reading = _result(READING, value=Decimal(10))
    assert core.result_changes(reading, _clean(value=Decimal(10), is_reset=True), linked_reset=False) == {
        "is_reset": True}
    assert core.result_changes(reading, _clean(value=Decimal(10), is_reset=True), linked_reset=1) == {}
    assert core.result_changes(reading, _clean(value=Decimal(10), is_reset=True)) == {}


def test_is_filled_and_unfilled_count():
    results = [_result(), _result(outcome="ok"), _result(READING, value=Decimal(0)), _result(READING, outcome="na")]
    assert [core.is_filled(r) for r in results] == [False, True, True, True]
    assert core.unfilled_count(results) == 1
    assert core.unfilled_count([]) == 0


# ---------------------------------------------------------------------------
# state_error
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("state, action, message", [
    (DUE_STATE, core.START, None), (DUE_STATE, core.FILL, core.START_FIRST),
    (DUE_STATE, core.PERFORMER, core.START_FIRST), (DUE_STATE, core.MARK_DONE, core.START_FIRST),
    (IN_PROGRESS, core.START, core.ALREADY_STARTED), (IN_PROGRESS, core.FILL, None),
    (IN_PROGRESS, core.PERFORMER, None), (IN_PROGRESS, core.MARK_DONE, None),
    *[(state, action, core.JOB_DONE) for state in (DONE, VERIFIED) for action in core.ACTIONS],
    *[(CANCELLED, action, core.JOB_CANCELLED) for action in core.ACTIONS],
    *[(SKIPPED, action, core.JOB_SKIPPED) for action in core.ACTIONS],     # S101: the skip's own text
])
def test_state_error(state, action, message):
    assert core.state_error(state, action) == (None if message is None else (message, 409))


def test_state_error_texts_and_bad_input():
    assert core.START_FIRST == "Start the job first."
    assert core.ALREADY_STARTED == "This job has been started. Reload the page."
    assert core.JOB_DONE == "This job is done and cannot be changed."
    assert core.JOB_CANCELLED == "This job was cancelled."
    with pytest.raises(ValueError):
        core.state_error("open", core.START)
    with pytest.raises(ValueError):
        core.state_error(DUE_STATE, "clear")


# ---------------------------------------------------------------------------
# job_time_error, done_meter_counted, the texts
# ---------------------------------------------------------------------------

def test_job_time_error():
    assert core.job_time_error(NOW, NOW) is None
    assert core.job_time_error(NOW - timedelta(days=7), NOW) is None
    assert core.job_time_error(NOW - timedelta(days=7, minutes=1), NOW) == "Enter a time up to 7 days back."
    assert core.job_time_error(NOW + timedelta(minutes=5), NOW) is None
    assert core.job_time_error(NOW + timedelta(minutes=6), NOW) == EVENT_TIME_FUTURE


def test_job_time_error_bad_input():
    with pytest.raises(TypeError):
        core.job_time_error(NOW.date(), NOW)


def test_done_meter_counted():
    assert core.done_meter_counted(None, Decimal(1200)) is None
    assert core.done_meter_counted(Decimal(1280), Decimal(1200)) == Decimal(2480)
    assert core.done_meter_counted(Decimal(1280), 0) == Decimal(1280)
    with pytest.raises(TypeError):
        core.done_meter_counted(1280.0, 0)
    with pytest.raises(TypeError):
        core.done_meter_counted(Decimal(1), None)


def test_the_texts():
    assert core.finish_jobs_first(1) == "Finish its PM jobs first (1 in progress)"
    assert core.not_all_filled(3, 7) == "Fill every item first: 3 of 7 are not filled."
    assert core.same_minute_pm(NOW) == ("The meter already has a different reading at this job's start time"
                                        " (27-10-2026 09:10). Ask an engineer to check the meter's readings.")
    assert core.not_logged("Oil temperature · HP003") == (
        "Saved on the job only: this machine no longer has the meter Oil temperature · HP003.")
    assert core.OUTCOMES == ("ok", "not_ok", "na", "done", "not_done")


# ---------------------------------------------------------------------------
# S099: verify and send back (§ 5.1)
# ---------------------------------------------------------------------------

SENT_BACK_AT = datetime(2026, 10, 28, 10, 0)


@pytest.mark.parametrize("state", core.JOB_STATES)
@pytest.mark.parametrize("needs", [0, 1, None])
def test_awaits_verification(state, needs):
    assert core.awaits_verification(state, needs) is (state == DONE and needs == 1)


@pytest.mark.parametrize("state, needs, message", [
    (VERIFIED, 1, core.ALREADY_VERIFIED),
    (DUE_STATE, None, core.NOT_DONE_YET), (IN_PROGRESS, None, core.NOT_DONE_YET),
    (CANCELLED, None, core.JOB_CANCELLED), (SKIPPED, None, core.JOB_SKIPPED),
    (DONE, 0, core.NO_VERIFICATION), (DONE, None, core.NO_VERIFICATION),
    (DONE, 1, None),
])
def test_verify_error(state, needs, message):
    assert core.verify_error(state, needs) == (None if message is None else (message, 409))


def test_verify_error_bad_input():
    with pytest.raises(ValueError):
        core.verify_error("open", 1)
    with pytest.raises(ValueError):
        core.verify_error(DONE, 2)
    with pytest.raises(TypeError):
        core.verify_error(DONE, True)


@pytest.mark.parametrize("body, needed, expected", [
    ({}, False, (None, None)),
    ({"remark": None}, False, (None, None)),
    ({"remark": ""}, False, (None, None)),
    ({"remark": "   "}, False, (None, None)),
    ({"remark": " x "}, False, ("x", None)),
    ({"remark": "a" * 500}, False, ("a" * 500, None)),
    ({"remark": "a" * 501}, False, (None, ("remark", core.REMARK_TOO_LONG))),
    ({"remark": 5}, False, (None, ("remark", core.REMARK_NOT_TEXT))),
    ({}, True, (None, ("remark", core.SEND_BACK_REMARK))),
    ({"remark": "  "}, True, (None, ("remark", core.SEND_BACK_REMARK))),
    ({"remark": "Re-tighten the left rod seal"}, True, ("Re-tighten the left rod seal", None)),
])
def test_verify_remark(body, needed, expected):
    assert core.verify_remark(body, needed) == expected


def test_clean_remark_with_and_without_a_needed_message():
    assert core.clean_remark(None, None) == (None, None)
    assert core.clean_remark(" ok ", None) == ("ok", None)
    assert core.clean_remark("", "Say what is wrong.") == (None, "Say what is wrong.")
    assert core.clean_remark("Leak", "Say what is wrong.") == ("Leak", None)
    assert core.clean_remark(["x"], None) == (None, core.REMARK_NOT_TEXT)


def test_done_time_error():
    started = SENT_BACK_AT - timedelta(days=1)
    now = SENT_BACK_AT + timedelta(days=3)
    assert core.done_time_error(SENT_BACK_AT, now, started, SENT_BACK_AT) is None
    assert core.done_time_error(SENT_BACK_AT - timedelta(minutes=1), now, started, SENT_BACK_AT) == (
        "Done must be at or after it was sent back, 28-10-2026 10:00.")
    assert core.done_time_error(started - timedelta(minutes=1), now, started, None) == (
        core.done_before_start(started))
    assert core.done_time_error(NOW, NOW, None, None) is None
    assert core.done_time_error(NOW + timedelta(minutes=6), NOW, None, None) == EVENT_TIME_FUTURE
    assert core.done_time_error(now - timedelta(days=8), now, None, None) == core.TIME_TOO_OLD
    # The window comes first: 8 days back is too old even before the send-back
    assert core.done_time_error(now - timedelta(days=8), now, started, SENT_BACK_AT) == core.TIME_TOO_OLD


def test_done_time_error_bad_input():
    with pytest.raises(TypeError):
        core.done_time_error(NOW, NOW, None, "2026-10-28")
    with pytest.raises(TypeError):
        core.done_time_error(NOW, NOW, "2026-10-27", None)


@pytest.mark.parametrize("verifier, performer, expected", [
    (7, 7, True), (7, 8, False), (None, 7, False), (7, None, False), (None, None, False),
])
def test_self_verified(verifier, performer, expected):
    assert core.self_verified(verifier, performer) is expected


def test_the_s099_texts():
    assert core.VERIFY_KEY == "pm_job:verify"
    assert (core.VERIFIED_EVENT, core.SENT_BACK_EVENT) == ("verified", "sent_back")
    assert core.SEND_BACK_CHANGES == {"state": IN_PROGRESS, "done_at": None, "done_meter": None,
                                      "timeliness": None, "needs_verification": None}
    assert core.NOT_DONE_YET == "This job is not done yet. It can be verified once it is marked done."
    assert core.ALREADY_VERIFIED == "This job is verified. It cannot be changed."
    assert core.NO_VERIFICATION == "This job needs no verification. It is final."
    assert core.SEND_BACK_REMARK == "Say what must be done again."
    assert core.SCRAPPED_NO_SEND_BACK == "This machine is scrapped. The job cannot be sent back."
    assert core.open_job_started("PM-2026-11-004") == (
        "The plan's open job PM-2026-11-004 has been started, so this job cannot be sent back. Verify this job, or"
        " raise a ticket for what is wrong.")
    assert core.open_job_cancelled("PM-2026-10-014") == (
        "PM-2026-10-014 was sent back, so the plan's open job is cancelled. The next job is made again from the"
        " latest done time.")
    assert core.done_before_send_back(SENT_BACK_AT) == "Done must be at or after it was sent back, 28-10-2026 10:00."


# ---------------------------------------------------------------------------
# S101: reschedule and skip (§ 5.2)
# ---------------------------------------------------------------------------

TODAY = date(2026, 11, 2)
HOURS = {"unit": "h", "decimals": 1}


def test_the_s101_texts():
    assert (core.RESCHEDULED_EVENT, core.SKIPPED_EVENT) == ("rescheduled", "skipped")
    assert core.SKIP_CHANGES == {"state": SKIPPED}
    assert core.JOB_SKIPPED == "This job was skipped."
    assert core.STARTED_NO_MOVE == "This job has been started. Finish it and mark it done."
    assert core.BEFORE_USE_NO_MOVE == ("This plan is now done before each use, so the job has no due point to move."
                                       " Skip the job instead.")
    assert core.MOVE_REASON == "Say why the job is moved."
    assert core.SKIP_REASON == "Say why the job is skipped."
    assert core.NOTHING_MOVED == "Change the due date or the meter value."
    assert core.NO_CALENDAR == "This plan has no due date. Enter a meter value."
    assert core.NO_METER == "This plan has no meter. Enter a due date."
    assert core.NO_READING_YET == "The meter has no reading yet, so a due value cannot be set. Log a reading first."
    assert core.meter_not_above("9,900 h") == "Enter a value above the latest reading, 9,900 h."
    assert core.meter_too_far("10,150 h") == "Enter a value up to 10,150 h: one interval after the latest reading."


@pytest.mark.parametrize("state, message", [
    (DUE_STATE, None), (IN_PROGRESS, core.STARTED_NO_MOVE), (DONE, core.JOB_DONE), (VERIFIED, core.JOB_DONE),
    (CANCELLED, core.JOB_CANCELLED), (SKIPPED, core.JOB_SKIPPED),
])
def test_move_error(state, message):
    assert core.move_error(state) == (None if message is None else (message, 409))


def test_move_error_covers_every_state_and_refuses_an_unknown_one():
    assert set(JOB_STATES) == {DUE_STATE, IN_PROGRESS, DONE, VERIFIED, CANCELLED, SKIPPED}
    with pytest.raises(ValueError):
        core.move_error("open")


@pytest.mark.parametrize("body, skip, expected", [
    ({}, False, (None, ("remark", core.MOVE_REASON))),
    ({"remark": "  "}, False, (None, ("remark", core.MOVE_REASON))),
    ({}, True, (None, ("remark", core.SKIP_REASON))),
    ({"remark": " Shutdown next week "}, False, ("Shutdown next week", None)),
    ({"remark": "Machine sold"}, True, ("Machine sold", None)),
    ({"remark": "a" * 501}, True, (None, ("remark", core.REMARK_TOO_LONG))),
    ({"remark": 5}, False, (None, ("remark", core.REMARK_NOT_TEXT))),
])
def test_move_reason(body, skip, expected):
    assert core.move_reason(body, skip) == expected


def _job(due_on=TODAY, due_meter=None, rescheduled_on=None, rescheduled_meter=None):
    return {"due_on": due_on, "due_meter": due_meter, "rescheduled_on": rescheduled_on,
            "rescheduled_meter": rescheduled_meter}


def _move(body, kind=CALENDAR, job=None, reading=None, every=None, meter_type=None):
    if kind != CALENDAR and job is None:
        job = _job(due_on=None if kind == METER else TODAY, due_meter=Decimal("10000"))
    if kind != CALENDAR:
        reading = Decimal("9900") if reading is None else reading
        every = Decimal("250") if every is None else every
        meter_type = meter_type or HOURS
    return core.reschedule_override(body, kind, job or _job(), TODAY, reading, every, meter_type)


def test_a_calendar_move():
    assert _move({"due_on": "2026-11-12"}) == ({"due_on": date(2026, 11, 12), "due_meter": None}, None)
    assert _move({"due_on": " 2026-11-12 ", "due_meter": None}) == (
        {"due_on": date(2026, 11, 12), "due_meter": None}, None)
    # Earlier is allowed (D3): today is the floor
    assert _move({"due_on": "2026-11-02"}, job=_job(due_on=date(2026, 11, 9)))[0]["due_on"] == TODAY


def test_a_meter_move():
    assert _move({"due_meter": "10100"}, METER) == ({"due_on": None, "due_meter": Decimal("10100")}, None)
    assert _move({"due_meter": 10150, "due_on": ""}, METER)[0]["due_meter"] == Decimal("10150")   # one interval on


def test_a_both_plan_keeps_the_earlier_move_of_the_other_trigger():
    moved = _job(due_on=date(2026, 11, 20), due_meter=Decimal("10000"), rescheduled_on=date(2026, 11, 20))
    assert _move({"due_on": "2026-11-20", "due_meter": "10050"}, BOTH, job=moved) == (
        {"due_on": date(2026, 11, 20), "due_meter": Decimal("10050")}, None)
    assert _move({"due_on": "2026-11-25"}, BOTH)[0] == {"due_on": date(2026, 11, 25), "due_meter": None}


@pytest.mark.parametrize("body, kind, expected", [
    ({"due_on": "12-11-2026"}, CALENDAR, ("due_on", LABOUR_DATE_FORMAT)),
    ({"due_on": 20261112}, CALENDAR, ("due_on", LABOUR_DATE_FORMAT)),
    ({"due_on": "2026-11-01"}, CALENDAR, ("due_on", PLANNED_DATE_PAST)),
    ({"due_on": "2027-11-03"}, CALENDAR, ("due_on", PLANNED_DATE_TOO_FAR)),
    ({"due_on": "2027-11-02"}, CALENDAR, None),                           # 365 days ahead is allowed
    ({"due_on": "2026-11-12"}, METER, ("due_on", core.NO_CALENDAR)),
    ({"due_meter": "10100"}, CALENDAR, ("due_meter", core.NO_METER)),
    ({"due_meter": "abc"}, METER, ("due_meter", "Enter a number with up to 1 decimal")),
    ({"due_meter": "9900"}, METER, ("due_meter", core.meter_not_above("9,900 h"))),
    ({"due_meter": "10150.1"}, METER, ("due_meter", core.meter_too_far("10,150 h"))),
    ({}, CALENDAR, ("due_on", core.NOTHING_MOVED)),
    ({"due_on": "2026-11-02"}, CALENDAR, ("due_on", core.NOTHING_MOVED)),   # the date it has
    ({}, METER, ("due_meter", core.NOTHING_MOVED)),
    ({"due_meter": "10000.0"}, METER, ("due_meter", core.NOTHING_MOVED)),   # 10000.0 = 10000
    ({"due_on": "2026-11-02", "due_meter": "10000"}, BOTH, ("due_on", core.NOTHING_MOVED)),
])
def test_the_refusals(body, kind, expected):
    assert _move(body, kind)[1] == expected


def test_no_reading_refuses_only_a_meter_move():
    job = _job(due_on=TODAY, due_meter=None)
    assert core.reschedule_override({"due_meter": "500"}, BOTH, job, TODAY, None, Decimal("250"), HOURS) == (
        None, ("due_meter", core.NO_READING_YET))
    assert core.reschedule_override({"due_on": "2026-11-09"}, BOTH, job, TODAY, None, Decimal("250"), HOURS) == (
        {"due_on": date(2026, 11, 9), "due_meter": None}, None)


def test_a_value_fault_comes_before_another_field_s():
    # The date's fault is shown first; the meter's after it is fixed
    assert _move({"due_on": "x", "due_meter": "abc"}, BOTH)[1] == ("due_on", LABOUR_DATE_FORMAT)


def test_reschedule_override_bad_input():
    with pytest.raises(ValueError):
        core.reschedule_override({}, BEFORE_USE, _job(), TODAY, None, None, None)
    with pytest.raises(TypeError):
        core.reschedule_override({"due_on": "2026-11-12"}, CALENDAR, _job(), datetime(2026, 11, 2), None, None,
                                 None)
    with pytest.raises(TypeError):
        _move({"due_meter": "10100"}, METER, reading=9900.0)


def _line(event, due_on=None, due_meter=None):
    return {"event": event, "due_on": due_on, "due_meter": due_meter}


def test_reschedule_summary():
    assert core.reschedule_summary([_line("created", "2026-11-08")]) is None
    assert core.reschedule_summary([]) is None
    events = [_line("created", "2026-11-01"), _line("due_changed", "2026-11-08", "10040"), _line("started"),
              _line("rescheduled", "2026-11-15"), _line("assignee_changed"), _line("rescheduled", "2026-11-20"),
              _line("due_changed", "2026-12-01")]
    assert core.reschedule_summary(events) == {"count": 2, "was_due_on": "2026-11-08", "was_due_meter": "10040"}
    assert core.reschedule_summary([_line("rescheduled", "2026-11-15")]) == {
        "count": 1, "was_due_on": None, "was_due_meter": None}


def test_reschedule_summary_of_a_move_in_the_job_s_first_minute():
    """The created line has seconds and the move only its minute, so the move sorts first."""
    events = [_line("rescheduled", "2026-11-15"), _line("created", "2026-11-08"), _line("due_changed", "2026-11-09")]
    assert core.reschedule_summary(events) == {"count": 1, "was_due_on": "2026-11-08", "was_due_meter": None}
