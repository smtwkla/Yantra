"""PM work — the pure rules of doing one PM job (docs/steps/S098-pm-job-phone/1-brief.md § 5.1; R03.4).  No DB, no
clock, no Flask.

A technician starts a due job (its template's active items are copied into results: ``result_rows``), fills each item
(``validate_result``, ``result_changes``) and marks the job done when every item is filled (``unfilled_count``).
``state_error`` says which action a job's state allows; ``job_time_error`` keeps *Started* and *Done* inside the
readings' window, since a reading item logs its meter reading at the job's start time (D5, D6).

S099 (docs/steps/S099-pm-verify/1-brief.md § 5.1; R03.5): an engineer verifies a done job that waits for
verification (``awaits_verification``), or sends it back to in progress with a remark (``verify_error``,
``verify_remark``, ``SEND_BACK_CHANGES``); the second *Done* is at or after the latest send-back
(``done_time_error``).

S101 (docs/steps/S101-pm-reschedule-skip/1-brief.md § 5.2; R03.9): an engineer moves a due job to a new due date or
meter value (``reschedule_override``), or skips it (``SKIP_CHANGES``), always with a reason (``move_reason``); only a
due job (``move_error``).  ``reschedule_summary`` gives the page's "Moved from" from the timeline.

A bad input is a shell bug, never user input: it raises ``ValueError`` / ``TypeError`` naming it (S095 D8).
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

from meters_core import GAUGE, READING_BACKDATE_DAYS, limit_state, parse_number, validate_reading
from pm_jobs_core import CANCELLED, CREATED, DONE, DUE_CHANGED, DUE_STATE, IN_PROGRESS, JOB_STATES, SKIPPED, VERIFIED
from pm_schedule_core import BOTH, CALENDAR, METER
from pm_templates_core import CHECK, READING, STORED_DECIMALS, TASK, interval_number
from tickets_core import EVENT_TIME_FUTURE, FUTURE_SKEW, LABOUR_DATE_FORMAT, planned_date_error

WORK_KEY = "pm_job:work"
OK, NOT_OK, NA, DONE_OUTCOME, NOT_DONE = "ok", "not_ok", "na", "done", "not_done"
OUTCOMES = (OK, NOT_OK, NA, DONE_OUTCOME, NOT_DONE)          # the ENUM's order
OUTCOMES_BY_TYPE = {CHECK: (OK, NOT_OK, NA), TASK: (DONE_OUTCOME, NOT_DONE), READING: (NA,)}
REMARK_MAX = 500
START, FILL, PERFORMER, MARK_DONE = "start", "fill", "performer", "done"   # the actions state_error judges
ACTIONS = (START, FILL, PERFORMER, MARK_DONE)
STARTED_EVENT, PERFORMER_EVENT, DONE_EVENT = "started", "performer_changed", "done"

START_FIRST = "Start the job first."
ALREADY_STARTED = "This job has been started. Reload the page."
JOB_DONE = "This job is done and cannot be changed."
JOB_CANCELLED = "This job was cancelled."
JOB_SKIPPED = "This job was skipped."   # S101: every action on a skipped job
NO_ITEMS = "This plan's template has no items. Ask an engineer to add items to the template."
PERFORMED_BY_NEEDED = "Choose who did the work."
TIME_TOO_OLD = f"Enter a time up to {READING_BACKDATE_DAYS} days back."
CHOOSE_OUTCOME = {CHECK: "Choose OK, Not OK or NA.", TASK: "Choose Done or Not done.",
                  READING: "Enter the reading, or tap NA."}
VALUE_OR_NA = "Enter the reading or tap NA, not both."
REMARK_NEEDED = {NOT_OK: "Say what is wrong.", NOT_DONE: "Say why it was not done.",
                 NA: "Say why there is no reading."}
REMARK_TOO_LONG = f"Remark must be at most {REMARK_MAX} characters"
REMARK_NOT_TEXT = "Remark must be text"

# S099: verify and send back (§ 5.1)
VERIFY_KEY = "pm_job:verify"
VERIFIED_EVENT, SENT_BACK_EVENT = "verified", "sent_back"
SEND_BACK_CHANGES = {"state": IN_PROGRESS, "done_at": None, "done_meter": None, "timeliness": None,
                     "needs_verification": None}          # chk_pm_jobs_done, chk_pm_jobs_verification
NOT_DONE_YET = "This job is not done yet. It can be verified once it is marked done."
ALREADY_VERIFIED = "This job is verified. It cannot be changed."
NO_VERIFICATION = "This job needs no verification. It is final."
SEND_BACK_REMARK = "Say what must be done again."
SCRAPPED_NO_SEND_BACK = "This machine is scrapped. The job cannot be sent back."   # the page's line

# The result columns a job copies from its template's item at Start (§ 4.1; S104: the reading kind, and the meter
# resolved on the machine), and the ones the work fills
COPIED_FIELDS = ("position", "item_type", "text", "help_text", "photo", "reading_kind", "unit", "min_value",
                 "max_value", "meter_equipment_id", "meter_type_id")
RESULT_FIELDS = ("outcome", "value", "limit_state", "remark", "reading_id", "filled_at", "filled_by")
# What a save compares (result_changes); "is_reset" is the linked reading's mark, not a result column
_COMPARED = ("outcome", "value", "limit_state", "remark")

_STATE_ERRORS = {
    DUE_STATE: {START: None, FILL: START_FIRST, PERFORMER: START_FIRST, MARK_DONE: START_FIRST},
    IN_PROGRESS: {START: ALREADY_STARTED, FILL: None, PERFORMER: None, MARK_DONE: None},
    DONE: dict.fromkeys(ACTIONS, JOB_DONE),
    VERIFIED: dict.fromkeys(ACTIONS, JOB_DONE),
    CANCELLED: dict.fromkeys(ACTIONS, JOB_CANCELLED),
    SKIPPED: dict.fromkeys(ACTIONS, JOB_SKIPPED),
}


def _when(moment):
    return moment.strftime("%d-%m-%Y %H:%M")


def _moment(value, key):
    if not isinstance(value, datetime):
        raise TypeError(f"{key} must be a datetime, not {type(value).__name__}")
    return value


def _number(value, key):
    """``value`` as a Decimal or None; ``int`` is exact and allowed, ``bool`` and ``float`` are not."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (Decimal, int)):
        raise TypeError(f"{key} must be a Decimal or an int, not {type(value).__name__}")
    return Decimal(value)


def not_all_filled(unfilled, total):
    return f"Fill every item first: {unfilled} of {total} are not filled."


def done_before_start(started_at):
    return f"Done must be at or after Started, {_when(started_at)}."


def same_minute_pm(taken_at):
    """A different reading of the meter at the job's start time (§ 5.5 step 4)."""
    return (f"The meter already has a different reading at this job's start time ({_when(taken_at)})."
            " Ask an engineer to check the meter's readings.")


def cannot_start(missing):
    """S104 § 5.7: *Start* of a job whose Meter reading item names a meter type the machine no longer has;
    ``missing`` is pm_links_core.missing_text's "no Brake air gap meter on EOT03"."""
    return f"This job cannot start: {missing}. Ask an engineer."


def not_logged(meter_name):
    """The answer's ``meter_note`` when the item's meter is gone since Start (§ 5.5 step 1, D9)."""
    return f"Saved on the job only: this machine no longer has the meter {meter_name}."


def finish_jobs_first(in_progress_count):
    """The scrap's refusal while PM jobs on the node are started (§ 5.8), the shape of
    tickets_core.close_tickets_first."""
    return f"Finish its PM jobs first ({in_progress_count} in progress)"


def result_rows(items):
    """The template's active items, in ``position`` order, each with its meter resolved on the machine by the shell
    (S104 § 5.7: ``meter_equipment_id`` the node whose meter it logs, ``min_value`` / ``max_value`` that meter's
    limits in force for a meter reading) -> the pm_job_results rows to insert (without job_id): every copied column
    as it is, ``template_item_id`` the item's id, every result column None (§ 5.3)."""
    rows = []
    for item in items:
        row = {"template_item_id": item["id"], **{field: item[field] for field in COPIED_FIELDS}}
        row.update(dict.fromkeys(RESULT_FIELDS))
        rows.append(row)
    return rows


def clean_remark(value, needed_message):
    """-> ``(remark, None)`` or ``(None, message)``: trimmed, empty or absent is None; not text, or over REMARK_MAX,
    refused; None with ``needed_message`` set is that message (S099 BS1-05: S098's ``_remark``, renamed, so an item's
    remark and the verify remark share one rule)."""
    if value is not None and not isinstance(value, str):
        return None, REMARK_NOT_TEXT
    remark = value.strip() if isinstance(value, str) else None
    if remark is not None and len(remark) > REMARK_MAX:
        return None, REMARK_TOO_LONG
    remark = remark or None
    if remark is None and needed_message:
        return None, needed_message
    return remark, None


def _given(value):
    return value is not None and not (isinstance(value, str) and value.strip() == "")


def validate_result(body, result, meter_type):
    """One item's body against its stored result (§ 5.4) -> ``(clean, None)`` or ``(None, (field, message))``.

    ``body`` holds ``outcome``, ``value``, ``remark``, ``is_reset`` (each optional); ``result`` the pm_job_results
    row (``item_type`` and the copied limits); ``meter_type`` ``{kind, decimals}`` when the item names a meter, else
    None.  ``clean`` holds ``outcome``, ``value`` (a Decimal or None), ``limit_state``, ``remark`` and ``is_reset``
    (False for anything but a reading's value)."""
    if not isinstance(body, dict):
        raise TypeError(f"body must be a dict, not {type(body).__name__}")
    item_type = result["item_type"]
    if item_type not in OUTCOMES_BY_TYPE:
        raise ValueError(f"item_type must be one of {tuple(OUTCOMES_BY_TYPE)}, not {item_type!r}")
    outcome, raw_value = body.get("outcome"), body.get("value")
    value, is_reset, state = None, False, None
    if item_type == READING:
        if outcome is not None and outcome != NA:
            return None, ("outcome", CHOOSE_OUTCOME[READING])
        if outcome == NA and _given(raw_value):
            return None, ("value", VALUE_OR_NA)
        if outcome is None and not _given(raw_value):
            return None, ("outcome", CHOOSE_OUTCOME[READING])
        if outcome is None:
            kind, decimals = (meter_type["kind"], meter_type["decimals"]) if meter_type else (GAUGE, STORED_DECIMALS)
            reading, errors = validate_reading(raw_value, kind, decimals, body.get("is_reset", False), None)
            if errors:
                return None, (errors[0]["field"], errors[0]["message"])
            value, is_reset = reading["value"], reading["is_reset"]
            state = limit_state(value, result["min_value"], result["max_value"])
    elif outcome not in OUTCOMES_BY_TYPE[item_type] or raw_value is not None:
        return None, ("outcome", CHOOSE_OUTCOME[item_type])
    # A check's NA needs no remark: only a reading's NA says why no value was taken
    needed = None if outcome == NA and item_type != READING else REMARK_NEEDED.get(outcome)
    remark, message = clean_remark(body.get("remark"), needed)
    if message:
        return None, ("remark", message)
    return {"outcome": outcome, "value": value, "limit_state": state, "remark": remark, "is_reset": is_reset}, None


def result_changes(stored, clean, linked_reset=None):
    """The columns of ``stored`` (a pm_job_results row) that ``clean`` (validate_result's) changes -> ``{column:
    value}``, plus ``"is_reset"`` when ``linked_reset`` (the linked reading's mark, when the result names one) differs
    from the sent mark; ``{}`` when nothing changed, so a retry writes nothing (BR1-03).  Decimals compare by value."""
    changes = {column: clean[column] for column in _COMPARED if stored[column] != clean[column]}
    if linked_reset is not None and bool(linked_reset) != clean["is_reset"]:
        changes["is_reset"] = clean["is_reset"]
    return changes


def is_filled(result):
    return result["outcome"] is not None or result["value"] is not None


def unfilled_count(results):
    return sum(1 for result in results if not is_filled(result))


def state_error(state, action):
    """What a job in ``state`` refuses for ``action`` (§ 5.2's table) -> ``(message, 409)`` or None."""
    if state not in JOB_STATES:
        raise ValueError(f"state must be one of {JOB_STATES}, not {state!r}")
    if action not in ACTIONS:
        raise ValueError(f"action must be one of {ACTIONS}, not {action!r}")
    message = _STATE_ERRORS[state][action]
    return None if message is None else (message, 409)


def job_time_error(moment, now):
    """*Started* or *Done* (naive IST datetimes) against ``now`` -> the message, or None: at most FUTURE_SKEW ahead,
    at most READING_BACKDATE_DAYS back (exactly 7 days is allowed).  The floors (*Started*, a send-back) are
    ``done_time_error``'s."""
    _moment(moment, "moment")
    _moment(now, "now")
    if moment > now + FUTURE_SKEW:
        return EVENT_TIME_FUTURE
    if moment < now - timedelta(days=READING_BACKDATE_DAYS):
        return TIME_TOO_OLD
    return None


def done_meter_counted(done_meter, offset):
    """The meter value at Done counted across resets: ``done_meter + offset`` (§ 5.6), None without a value."""
    done_meter = _number(done_meter, "done_meter")
    offset = _number(offset, "offset")
    if offset is None:
        raise TypeError("offset must be a Decimal or an int, not NoneType")
    return None if done_meter is None else done_meter + offset


# ---------------------------------------------------------------------------
# S099: verify and send back (§ 5.1)
# ---------------------------------------------------------------------------

_VERIFY_STATE_ERRORS = {VERIFIED: ALREADY_VERIFIED, DUE_STATE: NOT_DONE_YET, IN_PROGRESS: NOT_DONE_YET,
                        CANCELLED: JOB_CANCELLED, SKIPPED: JOB_SKIPPED}


def _needs(value):
    """The job's ``needs_verification`` column: 0, 1 or None; ``bool`` is a shell bug (the column is an int)."""
    if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
        raise TypeError(f"needs_verification must be an int or None, not {type(value).__name__}")
    if value not in (None, 0, 1):
        raise ValueError(f"needs_verification must be 0, 1 or None, not {value!r}")
    return value


def awaits_verification(state, needs_verification):
    """A done job whose copied setting is 1 waits on *To verify* (§ 4.2)."""
    return state == DONE and _needs(needs_verification) == 1


def verify_error(state, needs_verification):
    """What a job refuses for verify and for send back (§ 5.1's table) -> ``(message, 409)`` or None."""
    if state not in JOB_STATES:
        raise ValueError(f"state must be one of {JOB_STATES}, not {state!r}")
    if awaits_verification(state, needs_verification):
        return None
    return _VERIFY_STATE_ERRORS.get(state, NO_VERIFICATION), 409


def verify_remark(body, needed):
    """The verify (``needed`` False) or send-back (True) remark of ``body`` -> ``(remark, None)`` or
    ``(None, ("remark", message))``."""
    remark, message = clean_remark(body.get("remark"), SEND_BACK_REMARK if needed else None)
    return (None, ("remark", message)) if message else (remark, None)


def done_before_send_back(sent_back_at):
    return f"Done must be at or after it was sent back, {_when(sent_back_at)}."


def done_time_error(moment, now, started_at, sent_back_at):
    """*Done* (naive IST datetimes) -> the message or None (BR1-02): the window first (job_time_error), then not
    before the latest send-back, else not before *Started*.  A sent-back job's *Started* is earlier than its
    send-back, so the send-back is the floor that matters."""
    message = job_time_error(moment, now)
    if message:
        return message
    if sent_back_at is not None and moment < _moment(sent_back_at, "sent_back_at"):
        return done_before_send_back(sent_back_at)
    if started_at is not None and moment < _moment(started_at, "started_at"):
        return done_before_start(started_at)
    return None


def self_verified(verifier_person_id, performer_id):
    """The verifier is the job's *Performed by* (D5): both set and equal."""
    return verifier_person_id is not None and verifier_person_id == performer_id


def open_job_started(serial):
    return (f"The plan's open job {serial} has been started, so this job cannot be sent back. Verify this job, or"
            " raise a ticket for what is wrong.")


def open_job_cancelled(serial):
    """The open job's ``cancelled`` remark; ``serial`` is the sent-back job's."""
    return (f"{serial} was sent back, so the plan's open job is cancelled. The next job is made again from the latest"
            " done time.")


# ---------------------------------------------------------------------------
# S101: reschedule and skip (§ 5.2)
# ---------------------------------------------------------------------------

RESCHEDULED_EVENT, SKIPPED_EVENT = "rescheduled", "skipped"
SKIP_CHANGES = {"state": SKIPPED}   # with done_at and done_meter from the shell (S095 § 5.2, D6)
STARTED_NO_MOVE = "This job has been started. Finish it and mark it done."
BEFORE_USE_NO_MOVE = ("This plan is now done before each use, so the job has no due point to move. Skip the job"
                      " instead.")
MOVE_REASON = "Say why the job is moved."
SKIP_REASON = "Say why the job is skipped."
NOTHING_MOVED = "Change the due date or the meter value."
NO_CALENDAR = "This plan has no due date. Enter a meter value."
NO_METER = "This plan has no meter. Enter a due date."
NO_READING_YET = "The meter has no reading yet, so a due value cannot be set. Log a reading first."

_MOVE_ERRORS = {DUE_STATE: None, IN_PROGRESS: STARTED_NO_MOVE, DONE: JOB_DONE, VERIFIED: JOB_DONE,
                CANCELLED: JOB_CANCELLED, SKIPPED: JOB_SKIPPED}
_MOVABLE_KINDS = (CALENDAR, METER, BOTH)
# The timeline lines that hold a computed due point
_DUE_LINES = (CREATED, DUE_CHANGED)


def meter_not_above(value_text):
    return f"Enter a value above the latest reading, {value_text}."


def meter_too_far(value_text):
    return f"Enter a value up to {value_text}: one interval after the latest reading."


def move_error(state):
    """What a job in ``state`` refuses for reschedule and skip (D1: a due job only) -> ``(message, 409)`` or None."""
    if state not in _MOVE_ERRORS:
        raise ValueError(f"state must be one of {JOB_STATES}, not {state!r}")
    message = _MOVE_ERRORS[state]
    return None if message is None else (message, 409)


def move_reason(body, skip):
    """The reason a reschedule (``skip`` False) or a skip needs -> ``(remark, None)`` or ``(None, ("remark",
    message))``."""
    remark, message = clean_remark(body.get("remark"), SKIP_REASON if skip else MOVE_REASON)
    return (None, ("remark", message)) if message else (remark, None)


def _value_text(value, meter_type):
    """A meter value as the page shows a due point: "9,900 h" (the places it has, Indian grouping)."""
    return f"{interval_number(value, meter_type['decimals'])} {meter_type['unit'] or ''}".strip()


def _new_date(raw):
    """A ``YYYY-MM-DD`` string (the date input's) -> ``(date, None)`` or ``(None, LABOUR_DATE_FORMAT)``."""
    if isinstance(raw, str):
        try:
            return date.fromisoformat(raw.strip()), None
        except ValueError:
            pass
    return None, LABOUR_DATE_FORMAT


def reschedule_override(body, trigger_kind, job, today, reading_counted, meter_every, meter_type):
    """The reschedule's body against the job (§ 5.2) -> ``(override, None)`` or ``(None, (field, message))``.

    ``job`` holds ``due_on``, ``due_meter``, ``rescheduled_on``, ``rescheduled_meter``; ``today`` the IST date;
    ``reading_counted`` the latest active reading plus the job's offset, or None; ``meter_every`` the plan's interval
    and ``meter_type`` ``{unit, decimals}``, both None without a meter trigger.  ``override`` is next_due's: the moved
    value of each trigger, else the job's earlier move of it, else None."""
    if trigger_kind not in _MOVABLE_KINDS:
        raise ValueError(f"trigger_kind must be one of {_MOVABLE_KINDS}, not {trigger_kind!r}")
    if type(today) is not date:
        raise TypeError(f"today must be a date, not {type(today).__name__}")
    reading_counted = _number(reading_counted, "reading_counted")
    has_calendar, has_meter = trigger_kind in (CALENDAR, BOTH), trigger_kind in (METER, BOTH)

    new_on = new_meter = None
    if _given(body.get("due_on")):
        if not has_calendar:
            return None, ("due_on", NO_CALENDAR)
        new_on, message = _new_date(body["due_on"])
        if message:
            return None, ("due_on", message)
    if _given(body.get("due_meter")):
        if not has_meter:
            return None, ("due_meter", NO_METER)
        try:
            new_meter = parse_number(body["due_meter"], meter_type["decimals"])
        except ValueError as exc:
            return None, ("due_meter", str(exc))

    # A value equal to the job's own is no move (Decimals by value: 10000.0 = 10000)
    moved_on = new_on if new_on is not None and new_on != job["due_on"] else None
    moved_meter = new_meter if new_meter is not None and new_meter != job["due_meter"] else None
    if moved_on is None and moved_meter is None:
        return None, ("due_on" if has_calendar else "due_meter", NOTHING_MOVED)

    # The bounds are a typo guard (D3): a date from today to a year ahead, a value up to one interval past the meter
    if moved_on is not None:
        message = planned_date_error(moved_on, today)
        if message:
            return None, ("due_on", message)
    if moved_meter is not None:
        if reading_counted is None:
            return None, ("due_meter", NO_READING_YET)
        if moved_meter <= reading_counted:
            return None, ("due_meter", meter_not_above(_value_text(reading_counted, meter_type)))
        furthest = reading_counted + _number(meter_every, "meter_every")
        if moved_meter > furthest:
            return None, ("due_meter", meter_too_far(_value_text(furthest, meter_type)))

    due_on = moved_on if moved_on is not None else (job["rescheduled_on"] if has_calendar else None)
    due_meter = moved_meter if moved_meter is not None else (job["rescheduled_meter"] if has_meter else None)
    return {"due_on": due_on, "due_meter": due_meter}, None


def reschedule_summary(events):
    """The page's timeline lines (in time order) -> ``{count, was_due_on, was_due_meter}``, or None when the job was
    never moved (§ 4.2): the number of moves, and the due point of the last computed line (created, due_changed)
    before the first move.  The created line holds the save's seconds and a move only its minute, so a move in the
    job's first minute sorts before the created line: then the first computed line is the one moved from."""
    moves = [index for index, line in enumerate(events) if line["event"] == RESCHEDULED_EVENT]
    if not moves:
        return None
    computed = [line for line in events[:moves[0]] if line["event"] in _DUE_LINES]
    if not computed:
        computed = [line for line in events if line["event"] in _DUE_LINES][:1]
    was = computed[-1] if computed else {"due_on": None, "due_meter": None}
    return {"count": len(moves), "was_due_on": was["due_on"], "was_due_meter": was["due_meter"]}
