"""Tickets — pure rules (docs/steps/S017-raise-tickets/1-brief.md, docs/steps/S018-work-tickets/1-brief.md;
no DB, no clock, no Flask).

A ticket is the work request of EN 13460, and with S018's moves, labour and close the work order: one record per
problem found on equipment, a breakdown or a defect by its intensity (Plan.MD § 4.2).  The
intensity is ISO 14224's failure impact: critical (the item stopped: a breakdown, EN 13306's
failure), degraded (a partial failure) or initial (ISO's incipient: early signs).

Every function takes plain data; the caller passes ``now`` (IST, naive) so nothing here reads
the clock.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

INTENSITIES = ("critical", "degraded", "initial")
BREAKDOWN_INTENSITY = "critical"

# The S018 set (S017 § 7 decision 7) and S019's scheduled, in workflow order.  Scheduled is
# EN 13306's deferred corrective maintenance: work held, with a planned date and a waiting
# reason (S019 § 1.1).  The tickets.state ENUM lists it last (S019 § 7 decision 9); only this
# tuple's order is the workflow's.
STATES = ("raised", "acknowledged", "scheduled", "in_progress", "back_in_service", "closed")
RAISED = "raised"
ACKNOWLEDGED = "acknowledged"
SCHEDULED = "scheduled"
IN_PROGRESS = "in_progress"
BACK_IN_SERVICE = "back_in_service"
CLOSED = "closed"
OPEN_STATES = tuple(state for state in STATES if state != CLOSED)


def close_tickets_first(open_count):
    """The refusal when open tickets hold a record: scrapping a node (S017 § 5.8) and
    deactivating a unit (S025 § 5.3) say the same."""
    return f"Close its tickets first ({open_count} open)"

# The list's filters: a group or one intensity
INTENSITY_FILTERS = {
    "breakdown": (BREAKDOWN_INTENSITY,),
    "defect": tuple(i for i in INTENSITIES if i != BREAKDOWN_INTENSITY),
    **{intensity: (intensity,) for intensity in INTENSITIES},
}
# Scheduled and overdue (S019 § 1.6): the planner's view, ordered by planned date
STATE_FILTERS = ("open", "closed", "all", "scheduled", "overdue")
PLAN_FILTERS = ("scheduled", "overdue")

# Phone clocks drift a few minutes; a late entry at the end of a shift is normal, but older
# history (notebooks) is out of scope and would distort this month's figures (§ 7 decision 9)
FUTURE_SKEW = timedelta(minutes=5)
MAX_BACKDATE_DAYS = 7
# S028: admin always, and everyone while the backlog window is open, may enter times this far
# back.  A leap day short of three calendar years, on purpose: one subtraction, like the 7 days.
LONG_BACKDATE_YEARS = 3
LONG_BACKDATE_DAYS = LONG_BACKDATE_YEARS * 365
# S028: the last IST day (inclusive) on which everyone may enter the plant's notebook backlog
BACKLOG_UNTIL = date(2026, 11, 30)

DESCRIPTION_MAX = 1000

# The failure mode that says nothing by itself (S016 seed): a description is then needed
OTHER_MODE_CODE = "OTH"

# The level of the tree a ticket's machine is at (equipment_core.LEVELS[0])
MACHINE_LEVEL = "equipment"

# Local time only: what <input type="datetime-local"> sends, T or a space, seconds optional.
# No offset or Z, so a phone set to another time zone can never shift the time (§ 5.1).
_EVENT_TIME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})(:\d{2})?$")

EVENT_TIME_FORMAT = "Enter the time as YYYY-MM-DD HH:MM"
EVENT_TIME_FUTURE = "That time is in the future"
EVENT_TIME_TOO_OLD = f"When did it happen? Up to {MAX_BACKDATE_DAYS} days back"
EVENT_TIME_TOO_OLD_LONG = f"When did it happen? Up to {LONG_BACKDATE_YEARS} years back"
EVENT_TIME_BEFORE_LAST = "That time is before the last entry on this ticket"
DESCRIPTION_NEEDED = "Description is needed when no symptom is picked"
DESCRIPTION_NEEDED_OTHER = "Describe the problem when the symptom is Other"


def format_ticket_serial(year, month, number):
    """2026, 10, 1 -> TK-2026-10-001; past 999 the number simply grows (the equipment-code rule)."""
    return f"TK-{year:04d}-{month:02d}-{str(number).zfill(3)}"


def serial_scope(year, month):
    """The serial_counters row of one month: TK:2026-10."""
    return f"TK:{year:04d}-{month:02d}"


def parse_event_time(text):
    """``YYYY-MM-DDTHH:MM[:SS]`` (T or a space) -> ``(naive datetime, None)``, or
    ``(None, message)`` for anything else, an offset or Z included."""
    if not isinstance(text, str):
        return None, EVENT_TIME_FORMAT
    match = _EVENT_TIME_RE.match(text.strip())
    if not match:
        return None, EVENT_TIME_FORMAT
    date_part, minutes_part, seconds_part = match.groups()
    try:
        value = datetime.strptime(f"{date_part} {minutes_part}{seconds_part or ':00'}", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None, EVENT_TIME_FORMAT
    return value, None


def backdate_days(now, may_backdate):
    """How many days back an entered time may lie (S028): LONG_BACKDATE_DAYS for a holder of
    ticket:backdate, and for everyone while now's date is on or before BACKLOG_UNTIL;
    otherwise MAX_BACKDATE_DAYS.  BACKLOG_UNTIL is read at call time, so a test can move it."""
    if may_backdate or now.date() <= BACKLOG_UNTIL:
        return LONG_BACKDATE_DAYS
    return MAX_BACKDATE_DAYS


def too_old_message(max_back_days):
    """The refusal for a time older than the limit; the message follows the limit, not the role."""
    assert max_back_days in (MAX_BACKDATE_DAYS, LONG_BACKDATE_DAYS), max_back_days
    return EVENT_TIME_TOO_OLD_LONG if max_back_days == LONG_BACKDATE_DAYS else EVENT_TIME_TOO_OLD


def event_time_error(event_time, now, max_back_days, not_before=None):
    """The window an entered event time must fall in -> the message, or None: at most
    FUTURE_SKEW ahead of ``now``, at most ``max_back_days`` back (backdate_days), and not before
    ``not_before`` (S018: the ticket's last event)."""
    if event_time > now + FUTURE_SKEW:
        return EVENT_TIME_FUTURE
    if event_time < now - timedelta(days=max_back_days):
        return too_old_message(max_back_days)
    if not_before is not None and event_time < not_before:
        return EVENT_TIME_BEFORE_LAST
    return None


def _is_id(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _optional_id(body, field, message, clean, errors):
    value = body.get(field)
    if value is None:
        clean[field] = None
    elif _is_id(value):
        clean[field] = value
    else:
        errors.append({"field": field, "message": message})


def validate_raise(body, now, max_back_days):
    """The raise body -> ``(clean, errors)``, before the transaction.  ``clean`` holds every
    field: equipment_id, intensity, failure_mode_id, reported_by_id, repeat_of_id (None when not given),
    description (trimmed, None when empty) and occurred_at (``now`` when not given).  The
    rules that need rows (the mode, the person, the description with the mode) are the
    caller's, in the transaction."""
    clean, errors = {}, []

    if _is_id(body.get("equipment_id")):
        clean["equipment_id"] = body["equipment_id"]
    else:
        errors.append({"field": "equipment_id", "message": "Choose the equipment"})

    intensity = body.get("intensity")
    if intensity in INTENSITIES:
        clean["intensity"] = intensity
    else:
        errors.append({"field": "intensity", "message": "Choose how bad it is"})

    _optional_id(body, "failure_mode_id", "Choose a symptom from the list", clean, errors)
    _optional_id(body, "reported_by_id", "Choose a person from the list", clean, errors)
    _optional_id(body, "repeat_of_id", "Choose the earlier ticket", clean, errors)   # S018 § 5.5

    description = body.get("description")
    if description is None:
        clean["description"] = None
    elif not isinstance(description, str):
        errors.append({"field": "description", "message": "Description must be text"})
    else:
        description = description.strip()
        if len(description) > DESCRIPTION_MAX:
            errors.append({"field": "description", "message": f"Description is too long (max {DESCRIPTION_MAX})"})
        else:
            clean["description"] = description or None

    raw_time = body.get("occurred_at")
    if raw_time is None:
        clean["occurred_at"] = now
    else:
        occurred_at, message = parse_event_time(raw_time)
        message = message or event_time_error(occurred_at, now, max_back_days)
        if message:
            errors.append({"field": "occurred_at", "message": message})
        else:
            clean["occurred_at"] = occurred_at

    _restore_block(body, clean, errors)
    return clean, errors


# S018 A1, *Already fixed*: the raise body's optional back-in-service block, and the prefix that
# names its refusals so they land beside its own fields, not the raise's (BS2-02)
RESTORE_BLOCK = "restore"
RESTORE_FIELD_PREFIX = f"{RESTORE_BLOCK}."
RESTORE_BLOCK_NOT_OBJECT = "Back in service must be an object"


def _restore_block(body, clean, errors):
    """The ``restore`` block is the restore move's body, parsed by validate_move itself;
    ``clean["restore"]`` is None when not given.  The order of its times against the raise is
    the move's own check, in the transaction (tickets._apply_move)."""
    block = body.get(RESTORE_BLOCK)
    clean[RESTORE_BLOCK] = None
    if block is None:
        return
    if not isinstance(block, dict):
        errors.append({"field": RESTORE_BLOCK, "message": RESTORE_BLOCK_NOT_OBJECT})
        return
    restore, restore_errors = validate_move("restore", block)
    errors.extend({"field": f"{RESTORE_FIELD_PREFIX}{e['field']}", "message": e["message"]} for e in restore_errors)
    if not restore_errors:
        clean[RESTORE_BLOCK] = restore


def description_error(description, mode_code):
    """The description is required when no symptom is picked (``mode_code`` None) or the
    symptom is Other -> the message, or None."""
    if description:
        return None
    if mode_code is None:
        return DESCRIPTION_NEEDED
    if mode_code == OTHER_MODE_CODE:
        return DESCRIPTION_NEEDED_OTHER
    return None


def machine_and_component(node):
    """A node's ``level``, ``id``, ``parent_id`` and ``gp_id`` -> ``(machine_id, component_id)``.
    The tree is at most three levels: a machine is its own machine with no component; a
    component-unit's parent is the machine; a component's machine is its grandparent when it
    sits under a component-unit, else its parent (S017 § 5.2)."""
    if node["level"] == MACHINE_LEVEL:
        return node["id"], None
    if node["gp_id"] is not None:
        return node["gp_id"], node["id"]
    return node["parent_id"], node["id"]


def is_breakdown(intensity):
    return intensity == BREAKDOWN_INTENSITY


# ---------------------------------------------------------------------------
# Working the ticket (S018)
# ---------------------------------------------------------------------------

WORK_KEY = "ticket:work"
RESTORE_KEY = "ticket:restore"
ASSIGN_KEY = "ticket:assign"
CLOSE_KEY = "ticket:close"
EDIT_NOTES_KEY = "ticket:edit_notes"    # S027: correct a work note

# Event names (S018 § 4.3); RAISED is also the state's name
ACKNOWLEDGED_EVENT = "acknowledged"
STARTED_EVENT = "started"
BACK_IN_SERVICE_EVENT = "back_in_service"
SENT_BACK_EVENT = "sent_back"
CLOSED_EVENT = "closed"
NOT_A_FAULT_EVENT = "closed_not_a_fault"
REGRADED_EVENT = "regraded"
EDITED_EVENT = "edited"
ASSIGNED_EVENT = "assigned"
UNASSIGNED_EVENT = "unassigned"
SCHEDULED_EVENT = "scheduled"           # S019: the plan set
RESCHEDULED_EVENT = "rescheduled"       # S019: Change plan
# S027: a work note, what was found and tried.  Not in ORDERED_EVENTS: it moves neither the
# state nor the intensity, so it sets no lower bound for a later move's time and ticket_times
# skips it.
NOTE_EVENT = "note"

# The events that move the ticket's state or intensity: the times are computed from these, so
# they must stay in order (§ 5.1).  Edits and assignments are stamped with the time they were
# recorded and take no part in the order rule.  Rescheduled changes the waiting reason the
# waiting time is split by (S019 § 5.4), so it is ordered too.
ORDERED_EVENTS = (RAISED, ACKNOWLEDGED_EVENT, STARTED_EVENT, BACK_IN_SERVICE_EVENT, SENT_BACK_EVENT, CLOSED_EVENT,
                  NOT_A_FAULT_EVENT, REGRADED_EVENT, SCHEDULED_EVENT, RESCHEDULED_EVENT)

# How a refused time names the last event (§ 5.1)
EVENT_LABELS = {
    RAISED: "Raised",
    ACKNOWLEDGED_EVENT: "Acknowledged",
    STARTED_EVENT: "Started",
    BACK_IN_SERVICE_EVENT: "Back in service",
    SENT_BACK_EVENT: "Sent back",
    CLOSED_EVENT: "Closed",
    NOT_A_FAULT_EVENT: "Closed as not a fault",
    REGRADED_EVENT: "Severity changed",
    SCHEDULED_EVENT: "On hold",
    RESCHEDULED_EVENT: "Plan changed",
}

# S019 § 1.4: why a scheduled ticket waits -> (label, EN 13306 delay kind).  Logistic delay is
# the wait for maintenance resources (spares, specialists, test equipment, information,
# travel); administrative delay the wait for administrative reasons (a decision, a permit, a
# budget, production releasing the machine).  ``other`` is in neither total: the reports show
# it as its own line.  A fixed list, so the split stays comparable (§ 7 decision 3); the
# frontend's WAITING_REASON_LABELS copies it, and both test suites assert the six codes.
LOGISTIC_DELAY = "logistic"
ADMINISTRATIVE_DELAY = "administrative"
WAITING_REASONS = {
    "parts": ("Waiting for parts", LOGISTIC_DELAY),
    "vendor": ("At or waiting for a vendor, garage or maker", LOGISTIC_DELAY),
    "expert": ("Waiting for an expert", LOGISTIC_DELAY),
    "slot": ("Waiting for a production slot or shutdown", ADMINISTRATIVE_DELAY),
    "approval": ("Waiting for a decision or approval", ADMINISTRATIVE_DELAY),
    "other": ("Other (remark required)", None),
}
OTHER_REASON = "other"
PLANNED_DATE_MAX_DAYS = 365             # § 9 Q4

REMARK_MAX = 1000                       # ticket_events.remark
REPEAT_WINDOW_DAYS = 7                  # user decision 6
LABOUR_MINUTES_MAX = 24 * 60            # chk_ticket_labour_minutes

# Severity order, for "raising" and "lowering" a grade
_INTENSITY_RANK = {"initial": 1, "degraded": 2, "critical": 3}
LOWER_THAN_BREAKDOWN = "degraded"       # a send-back with the machine running (§ 1)

# Re-grade: any open state before back in service (Plan.MD § 4.2; scheduled too, S019 § 5.3)
REGRADE_STATES = (RAISED, ACKNOWLEDGED, SCHEDULED, IN_PROGRESS)
# "Not fixed — raise again" is offered on a ticket that was back in service (§ 5.5)
REPEAT_FROM_STATES = (BACK_IN_SERVICE, CLOSED)
# Downtime runs while the machine is critical in these states (§ 5.4; a stopped machine
# waiting in scheduled is down, S019 § 1.5)
DOWN_STATES = (RAISED, ACKNOWLEDGED, SCHEDULED, IN_PROGRESS)

# Messages the page or the tests match
PERSON_NEEDED = "Who did the work? Pick a name"
REMARK_NEEDED = "Add a remark"
MACHINE_DOWN_NEEDED = "Is the machine down again? Choose Yes or No"
CAUSE_NEEDED = "Choose the cause"
ACTION_NEEDED = "Choose the action taken"
MODE_NEEDED = "Choose the symptom"
LABOUR_BEFORE_CLOSE = "Add the labour before closing"
LOWERING_NEEDS_REMARK = "Say why the machine runs"
LOWERING_NOT_ALLOWED = "Only maintenance can lower the severity"
STARTED_AFTER_RESTORE = "Work cannot start after the machine was back in service"
STARTED_ALREADY = "Work has already started on this ticket"
ALREADY_BREAKDOWN = "Already a breakdown"
ALREADY_DEFECT = "Already a defect"
INTENSITY_NEEDED = "Choose how bad it is"
LABOUR_MINUTES = f"Time spent must be between 1 minute and {LABOUR_MINUTES_MAX // 60} hours"
LABOUR_DATE_FORMAT = "Enter the date as YYYY-MM-DD"
LABOUR_DATE_FUTURE = "That date is in the future"
LABOUR_DATE_EARLY = "That date is before the ticket's event"
TRADE_NEEDED = "Choose the trade worked"
NOTHING_TO_CHANGE = "Nothing to change"
NOTE_NEEDED = "Enter a note"
# S019 § 5.1–5.3
PLANNED_DATE_NEEDED = "Choose a date"
PLANNED_DATE_PAST = "The date cannot be before today"
PLANNED_DATE_TOO_FAR = "Choose a date within a year"
WAITING_REASON_NEEDED = "Choose why it waits"
MACHINE_STOPPED_NEEDED = "Choose Yes or No"


@dataclass(frozen=True)
class Move:
    from_states: tuple      # the states it may start from
    to_state: str
    key: str                # the permission, checked at the ticket's site
    event: str              # the ticket_events.event it writes
    requires: tuple = ()    # body fields that must be given (§ 5.2)
    # ((state, key), ...): from these states the move takes another key than ``key`` (S019 U1:
    # Schedule from in progress is the technician's "work stops, waiting"; from raised or
    # acknowledged it commits a slot, the engineer's)
    state_keys: tuple = ()

    def key_at(self, state):
        """The permission this move takes from ``state``."""
        return dict(self.state_keys).get(state, self.key)

    @property
    def keys(self):
        """Every permission the move takes from some state (the route's early 403)."""
        return {self.key, *(key for _state, key in self.state_keys)}


# The moves of § 1, in the order the page shows them: the chain first, then the plan (S019),
# then the significant ones
MOVES = {
    "acknowledge": Move((RAISED,), ACKNOWLEDGED, WORK_KEY, ACKNOWLEDGED_EVENT),
    "start": Move((RAISED, ACKNOWLEDGED, SCHEDULED), IN_PROGRESS, WORK_KEY, STARTED_EVENT),
    "restore": Move((RAISED, ACKNOWLEDGED, SCHEDULED, IN_PROGRESS), BACK_IN_SERVICE, RESTORE_KEY,
                    BACK_IN_SERVICE_EVENT, ("person_id",)),
    "schedule": Move((RAISED, ACKNOWLEDGED, IN_PROGRESS), SCHEDULED, ASSIGN_KEY, SCHEDULED_EVENT,
                     ("planned_date", "waiting_reason"), state_keys=((IN_PROGRESS, WORK_KEY),)),
    "reschedule": Move((SCHEDULED,), SCHEDULED, ASSIGN_KEY, RESCHEDULED_EVENT,
                       ("planned_date", "waiting_reason", "remark")),
    "send-back": Move((BACK_IN_SERVICE,), IN_PROGRESS, CLOSE_KEY, SENT_BACK_EVENT, ("machine_down", "remark")),
    "close": Move((BACK_IN_SERVICE,), CLOSED, CLOSE_KEY, CLOSED_EVENT, ("cause_id", "action_id")),
    # Also from in progress (S025 U4): Start pressed on arrival, nothing found
    "not-a-fault": Move((RAISED, ACKNOWLEDGED, SCHEDULED, IN_PROGRESS), CLOSED, CLOSE_KEY, NOT_A_FAULT_EVENT,
                        ("cause_id", "remark")),
}

# The moves that add the user's own person as an assignee (§ 5.8); scheduling is planning, not
# taking the work (S019 § 5.1)
AUTO_ASSIGN_MOVES = ("acknowledge", "start")
# The moves that set the plan (S019): their body carries planned_date and waiting_reason
PLAN_MOVES = ("schedule", "reschedule")
# The moves that may ask "was the machine stopped for this work?" (S019 § 5.3)
MACHINE_STOPPED_MOVES = ("start", "restore")

_REQUIRED_MESSAGES = {
    "person_id": PERSON_NEEDED,
    "remark": REMARK_NEEDED,
    "machine_down": MACHINE_DOWN_NEEDED,
    "cause_id": CAUSE_NEEDED,
    "action_id": ACTION_NEEDED,
    "planned_date": PLANNED_DATE_NEEDED,
    "waiting_reason": WAITING_REASON_NEEDED,
}


def allowed_moves(state, held_keys, has_repeat=False):
    """The moves the user may make now on a ticket in ``state``, holding ``held_keys`` at the
    ticket's site -> their names, in MOVES order.  The page shows exactly these buttons.
    ``has_repeat``: another ticket was raised as a repeat of this one, so no send-back."""
    return [name for name, move in MOVES.items()
            if state in move.from_states and move.key_at(state) in held_keys
            and not (name == "send-back" and send_back_error(has_repeat))]


def send_back_error(has_repeat, repeat_serial=None):
    """A ticket that came back as a repeat cannot be sent back (S025 § 5.2): the failure that
    came back is on the repeat ticket, and sending this one back would count the same stop
    twice.  -> the refusal, or None.  Closing it stays allowed: its repair did happen."""
    if not has_repeat:
        return None
    if repeat_serial:
        return f"This ticket came back as {repeat_serial}; work on that one"
    return "This ticket came back as a repeat; work on that one"


def _optional_text(body, field, maximum, clean, errors):
    value = body.get(field)
    if value is None:
        clean[field] = None
    elif not isinstance(value, str):
        errors.append({"field": field, "message": "Must be text"})
    else:
        value = value.strip()
        if len(value) > maximum:
            errors.append({"field": field, "message": f"Too long (max {maximum})"})
        else:
            clean[field] = value or None


def _optional_time(body, field, clean, errors):
    """A local time as the dialog sends it, or None; the window is checked later, against the
    ticket's last event."""
    raw = body.get(field)
    if raw is None:
        clean[field] = None
        return
    value, message = parse_event_time(raw)
    if message:
        errors.append({"field": field, "message": message})
    else:
        clean[field] = value


def _optional_date(body, field, message, clean, errors):
    """A ``YYYY-MM-DD`` date, or None when not given; anything else is ``message`` on ``field``
    (labour's work date, S019's planned date, BR1-16)."""
    raw = body.get(field)
    if raw is None:
        clean[field] = None
        return
    try:
        clean[field] = date.fromisoformat(raw.strip()) if isinstance(raw, str) else None
    except ValueError:
        clean[field] = None
    if clean[field] is None:
        errors.append({"field": field, "message": message})


def _optional_bool(body, field, message, clean, errors):
    value = body.get(field)
    if value is None or isinstance(value, bool):
        clean[field] = value
    else:
        errors.append({"field": field, "message": message})


def _event_fields(body):
    """What every move and re-grade takes: the event time (None = the server's clock) and a remark."""
    clean, errors = {}, []
    _optional_time(body, "occurred_at", clean, errors)
    _optional_text(body, "remark", REMARK_MAX, clean, errors)
    return clean, errors


def validate_note(body):
    """A work note's body (S027 § 3) -> ``(clean, errors)``: ``remark`` required, text, trimmed
    (line breaks inside kept), at most REMARK_MAX characters.  The same checks and messages as a
    move's remark, then the required check."""
    clean, errors = {}, []
    _optional_text(body, "remark", REMARK_MAX, clean, errors)
    if not errors and clean["remark"] is None:
        errors.append({"field": "remark", "message": NOTE_NEEDED})
    return clean, errors


def validate_regrade_body(body):
    """The re-grade body -> ``(clean, errors)``: occurred_at, remark and the intensity as sent
    (validate_regrade judges it against the ticket)."""
    clean, errors = _event_fields(body)
    clean["intensity"] = body.get("intensity")
    return clean, errors


def validate_move(name, body):
    """A move's body -> ``(clean, errors)``, before the transaction.  ``clean`` holds
    occurred_at and remark (None when not given) and the move's own fields; a field in
    ``MOVES[name].requires`` that is missing is an error with the message the page shows.
    Not a fault needs nothing beyond its required cause and remark.  A plan move with the
    reason *Other* needs a remark (S019 § 5.1, BR2-05: a body rule, so a 400 here); the rules
    that need the date of today or the ticket (planned_date_error, "Nothing to change",
    machine_stopped_needed) are the caller's."""
    move = MOVES[name]
    clean, errors = _event_fields(body)
    if name in MACHINE_STOPPED_MOVES:
        _optional_bool(body, "machine_stopped", MACHINE_STOPPED_NEEDED, clean, errors)
    if name == "restore":
        _optional_id(body, "person_id", "Choose a person from the list", clean, errors)
        _optional_time(body, "started_at", clean, errors)
    elif name == "send-back":
        _optional_bool(body, "machine_down", MACHINE_DOWN_NEEDED, clean, errors)
    elif name in ("close", "not-a-fault"):
        _optional_id(body, "cause_id", CAUSE_NEEDED, clean, errors)
        if name == "close":
            _optional_id(body, "action_id", ACTION_NEEDED, clean, errors)
            _optional_id(body, "failure_mode_id", MODE_NEEDED, clean, errors)
    elif name in PLAN_MOVES:
        _optional_date(body, "planned_date", LABOUR_DATE_FORMAT, clean, errors)
        reason = body.get("waiting_reason")
        if reason is None or (isinstance(reason, str) and reason in WAITING_REASONS):
            clean["waiting_reason"] = reason
        else:
            errors.append({"field": "waiting_reason", "message": WAITING_REASON_NEEDED})
    failed = {error["field"] for error in errors}
    for field in move.requires:
        if field not in failed and clean.get(field) is None:
            errors.append({"field": field, "message": _REQUIRED_MESSAGES[field]})
            failed.add(field)
    if (name in PLAN_MOVES and clean.get("waiting_reason") == OTHER_REASON and clean.get("remark") is None
            and "remark" not in failed):
        errors.append({"field": "remark", "message": REMARK_NEEDED})
    return clean, errors


def planned_date_error(planned, today):
    """S019 § 5.1: the planned date is today or later (the IST date of now; the event's time
    plays no part, BR1-05) and at most PLANNED_DATE_MAX_DAYS after today -> the message, or None."""
    if planned < today:
        return PLANNED_DATE_PAST
    if planned > today + timedelta(days=PLANNED_DATE_MAX_DAYS):
        return PLANNED_DATE_TOO_FAR
    return None


def machine_stopped_needed(from_state, intensity):
    """Whether Start (and Back in service with a start time) asks "was the machine stopped for
    this work?" (S019 § 5.3): only from scheduled, on a ticket that is not critical.  A
    critical ticket's machine is already down; work never planned is reactive (§ 7 decision 5)."""
    return from_state == SCHEDULED and not is_breakdown(intensity)


def is_overdue(state, planned_date, today):
    """S019 § 5.5: scheduled, and the planned date is before today.  Never on the date itself."""
    return state == SCHEDULED and planned_date is not None and planned_date < today


def _when(value):
    return value.strftime("%d-%m-%Y %H:%M")


# What the raise screen calls its raise time, for refusals on the *Already fixed* times (CR3-01):
# the user sees "When did it happen?", not "Raised"
RAISE_SCREEN_LABELS = {**EVENT_LABELS, RAISED: "the time it happened"}


def validate_event_time(event_time, last_event, now, max_back_days, labels=EVENT_LABELS):
    """S017's window for an entered time (event_time_error), with the ticket's last ordered
    event ``(event, occurred_at)`` as the lower bound; the refusal names that event (as
    ``labels`` words it) and its time -> the message, or None."""
    last_name, last_time = last_event
    message = event_time_error(event_time, now, max_back_days, not_before=last_time)
    if message == EVENT_TIME_BEFORE_LAST:
        return f"Must be at or after {labels.get(last_name, last_name)}, {_when(last_time)}"
    return message


def started_at_error(started_at, state, restored_at):
    """Back in service after the fact (§ 1): a start time may be given only while work has not
    started, and not after the restoration -> the message, or None.  The lower bound (the last
    event) is validate_event_time's."""
    if state == IN_PROGRESS:
        return STARTED_ALREADY
    if started_at > restored_at:
        return STARTED_AFTER_RESTORE
    return None


def send_back_intensity(current, machine_down):
    """The intensity a send-back sets (§ 1, decision 4) -> the new one, or None for no change:
    down again makes it critical; running lowers only a critical one, to degraded."""
    if machine_down:
        return None if current == BREAKDOWN_INTENSITY else BREAKDOWN_INTENSITY
    return LOWER_THAN_BREAKDOWN if current == BREAKDOWN_INTENSITY else None


def is_lowering(current, new):
    return _INTENSITY_RANK[new] < _INTENSITY_RANK[current]


def regrade_options(current, lowering_allowed):
    """The intensities this user may set now on an open ticket: higher ones always, lower ones
    with ticket:work (§ 1) -> a list in INTENSITIES order (the detail's ``regrade_to``)."""
    return [i for i in INTENSITIES if i != current and (lowering_allowed or not is_lowering(current, i))]


def validate_regrade(current, new, lowering_allowed, remark):
    """A re-grade -> ``(status, field, message)`` for the first refusal, or None (§ 5.2):
    an unknown or the same intensity 400; lowering without ticket:work 403, without a remark
    400."""
    if new not in INTENSITIES:
        return 400, "intensity", INTENSITY_NEEDED
    if new == current:
        return 400, "intensity", ALREADY_BREAKDOWN if is_breakdown(current) else ALREADY_DEFECT
    if is_lowering(current, new):
        if not lowering_allowed:
            return 403, "intensity", LOWERING_NOT_ALLOWED
        if not remark:
            return 400, "remark", LOWERING_NEEDS_REMARK
    return None


def validate_close(ticket_mode_id, clean, labour_count):
    """The close's rules that need the ticket -> ``(status, field, message)``, or None: the
    symptom when the ticket has none (400), at least one labour row (409).  The description
    rule needs the mode's code and stays the caller's (description_error)."""
    if ticket_mode_id is None and clean.get("failure_mode_id") is None:
        return 400, "failure_mode_id", MODE_NEEDED
    if labour_count < 1:
        return 409, None, LABOUR_BEFORE_CLOSE
    return None


def validate_labour(body, today, earliest):
    """A labour row's body -> ``(clean, errors)``: person, trade (optional here; trade_error says
    when it is needed), work_date not after ``today`` nor before ``earliest`` (the date of the
    ticket's event), minutes 1–1440."""
    clean, errors = {}, []
    if _is_id(body.get("person_id")):
        clean["person_id"] = body["person_id"]
    else:
        errors.append({"field": "person_id", "message": PERSON_NEEDED})
    _optional_id(body, "trade_id", TRADE_NEEDED, clean, errors)

    dates = {}
    _optional_date(body, "work_date", LABOUR_DATE_FORMAT, dates, errors)
    work_date = dates["work_date"]
    if body.get("work_date") is None:
        # Required here; a missing date reads as the format message, as before S019
        errors.append({"field": "work_date", "message": LABOUR_DATE_FORMAT})
    elif work_date is None:
        pass    # refused by _optional_date
    elif work_date > today:
        errors.append({"field": "work_date", "message": LABOUR_DATE_FUTURE})
    elif work_date < earliest:
        errors.append({"field": "work_date", "message": LABOUR_DATE_EARLY})
    else:
        clean["work_date"] = work_date

    minutes = body.get("minutes")
    if _is_id(minutes) and minutes <= LABOUR_MINUTES_MAX:
        clean["minutes"] = minutes
    else:
        errors.append({"field": "minutes", "message": LABOUR_MINUTES})
    return clean, errors


def validate_assignee(body):
    """The assign body -> ``(clean, errors)``: the person's id (the role check is the caller's)."""
    if _is_id(body.get("person_id")):
        return {"person_id": body["person_id"]}, []
    return {}, [{"field": "person_id", "message": "Choose a person from the list"}]


def trade_error(trade_id, person_has_trades):
    """The trade worked is required when the person holds a trade (ISO 14224 man-hours per
    discipline, decision 10); any active trade is accepted -> the message, or None."""
    if trade_id is None and person_has_trades:
        return TRADE_NEEDED
    return None


def validate_edit(body):
    """The edit body -> ``(clean, errors)``: only the fields present (component_id,
    failure_mode_id: an id or null; description: text or null).  The rules that need rows are
    the caller's."""
    clean, errors = {}, []
    for field, message in (("component_id", "Choose a component from the list"),
                           ("failure_mode_id", "Choose a symptom from the list")):
        if field in body:
            _optional_id(body, field, message, clean, errors)
    if "description" in body:
        _optional_text(body, "description", DESCRIPTION_MAX, clean, errors)
    if not clean and not errors:
        errors.append({"field": None, "message": NOTHING_TO_CHANGE})
    return clean, errors


def edit_lines(old, new, labels):
    """The timeline remark of an edit: one ``Label: old → new`` line per field that changed
    (``labels`` gives the fields and their order); an empty value shows as "—"."""
    lines = []
    for field, label in labels.items():
        if field in new and new[field] != old.get(field):
            lines.append(f"{label}: {old.get(field) or '—'} → {new[field] or '—'}")
    return "\n".join(lines)


def _minutes(delta):
    """A timedelta as whole minutes, never negative (the last event may lie up to FUTURE_SKEW
    after ``now``, BR1-14)."""
    return max(0, int(delta.total_seconds() // 60))


_TIMES_KEYS = ("response_minutes", "repair_minutes", "downtime_minutes", "waiting_minutes", "waiting_by_reason",
               "planned_downtime_minutes")
# The events that count as the first response (S019 § 7 decision 8: scheduling is a response)
_RESPONSE_EVENTS = (ACKNOWLEDGED_EVENT, STARTED_EVENT, SCHEDULED_EVENT)
# Where each ordered event leaves the state; regraded and rescheduled leave it as it is
_STATE_AFTER = {
    RAISED: RAISED, ACKNOWLEDGED_EVENT: ACKNOWLEDGED, SCHEDULED_EVENT: SCHEDULED, STARTED_EVENT: IN_PROGRESS,
    SENT_BACK_EVENT: IN_PROGRESS, BACK_IN_SERVICE_EVENT: BACK_IN_SERVICE, CLOSED_EVENT: CLOSED,
}


def ticket_times(events, now):
    """The ticket's figures from its events, oldest first (``event``, ``occurred_at``,
    ``intensity``; S019's ``waiting_reason`` and ``machine_stopped`` where set), against
    ``now`` -> the six keys of _TIMES_KEYS (S018 § 5.4, S019 § 5.4).  Each is None when
    unknown; all are None on a ticket closed as not a fault.
    - response: raised -> the first acknowledged, started or scheduled;
    - repair (EN 13306 active corrective maintenance time): the time in progress (a scheduled
      event ends a stretch, a started one opens the next); None when a back in service had no
      start right before it, or work never started;
    - downtime (EN 13306 time to restoration): the time while critical and not yet back in
      service, scheduled included, an open ticket to ``now``;
    - waiting (EN 13306 logistic and administrative delay): the time in scheduled while
      critical, in total and per waiting reason in force (the last scheduled / rescheduled
      event's); both None when the ticket was never critical while scheduled — a defect waiting
      for its slot is backlog, not delay.  Part of the downtime, never added to it;
    - planned downtime: from a started event marked machine_stopped to the next back in
      service, scheduled event or change to critical; None when there is no such start.

    The events cut the time into stretches; each stretch counts by the state, intensity and
    reason that held during it, clamped at zero (S018 BR1-14), and the last one runs to ``now``."""
    if any(e["event"] == NOT_A_FAULT_EVENT for e in events):
        return dict.fromkeys(_TIMES_KEYS)

    raised_at = response = None
    repair, repair_known, repair_seen = timedelta(0), True, False
    downtime = waiting = planned = timedelta(0)
    by_reason, waiting_seen, planned_seen = {}, False, False
    state = intensity = reason = since = None
    planned_stop = False    # the current in-progress stretch is a planned stop

    def count_stretch(until):
        nonlocal repair, downtime, waiting, planned, waiting_seen
        if since is None:
            return
        length = max(timedelta(0), until - since)
        critical = intensity == BREAKDOWN_INTENSITY
        if state == IN_PROGRESS:
            repair += length
            if planned_stop:
                planned += length
        if critical and state in DOWN_STATES:
            downtime += length
        if critical and state == SCHEDULED:
            waiting += length
            by_reason[reason] = by_reason.get(reason, timedelta(0)) + length
            waiting_seen = True

    for event in events:
        name, at = event["event"], event["occurred_at"]
        if name not in ORDERED_EVENTS:
            continue
        count_stretch(at)
        since = at
        if name == BACK_IN_SERVICE_EVENT and state != IN_PROGRESS:
            repair_known = False
        if name in (STARTED_EVENT, SENT_BACK_EVENT):
            repair_seen = True
        if name == RAISED:
            raised_at = at
        state = _STATE_AFTER.get(name, state)
        if event.get("intensity"):
            intensity = event["intensity"]
        if name in (SCHEDULED_EVENT, RESCHEDULED_EVENT):
            reason = event.get("waiting_reason")
        if name == STARTED_EVENT and event.get("machine_stopped"):
            planned_stop = planned_seen = True
        elif name in (BACK_IN_SERVICE_EVENT, SCHEDULED_EVENT) or intensity == BREAKDOWN_INTENSITY:
            planned_stop = False
        if response is None and raised_at is not None and name in _RESPONSE_EVENTS:
            response = at - raised_at
    if state != CLOSED:
        count_stretch(now)

    return {
        "response_minutes": None if response is None else _minutes(response),
        "repair_minutes": _minutes(repair) if repair_known and repair_seen else None,
        "downtime_minutes": _minutes(downtime),
        "waiting_minutes": _minutes(waiting) if waiting_seen else None,
        "waiting_by_reason": {code: _minutes(t) for code, t in by_reason.items()} if waiting_seen else None,
        "planned_downtime_minutes": _minutes(planned) if planned_seen else None,
    }


def latest_restoration(state, not_a_fault, events):
    """The time a ticket can be repeated from (§ 5.5): its latest back in service, but only
    while it stands back in service or closed, and not as a not-a-fault.  A ticket sent back
    is being worked again, so it is None.  ``events``: rows with ``event`` and ``occurred_at``."""
    if state not in REPEAT_FROM_STATES or not_a_fault:
        return None
    times = [e["occurred_at"] for e in events if e["event"] == BACK_IN_SERVICE_EVENT]
    return max(times) if times else None


def is_repeat_candidate(back_in_service_at, new_occurred_at):
    """Whether a new ticket may be a repeat of one restored at ``back_in_service_at`` (its
    latest back in service, § 5.5): 0 <= new - restoration <= REPEAT_WINDOW_DAYS.  None (never
    restored, or closed as not a fault) is never a candidate."""
    if back_in_service_at is None:
        return False
    return timedelta(0) <= new_occurred_at - back_in_service_at <= timedelta(days=REPEAT_WINDOW_DAYS)


# ---------------------------------------------------------------------------
# Parts used (S020): a line of what was fitted, on the ticket's machine or a component of it
# ---------------------------------------------------------------------------

PART_UNITS = ("nos", "set", "m", "L", "kg")    # checked here, not by an ENUM: a unit is added without a migration
DEFAULT_PART_UNIT = "nos"
MAKER_NUMBER = "maker"                          # from the maker's drawing or quote: maps to one OneERP item later
GENERIC_NUMBER = "generic"                      # a standard designation (6205-2RS): any brand
PART_KINDS = (MAKER_NUMBER, GENERIC_NUMBER)
PART_DESCRIPTION_MAX = 200                      # ticket_parts.description
PART_NUMBER_MAX = 60                            # ticket_parts.part_number
PART_MAKER_MAX = 100                            # ticket_parts.maker
PART_QUANTITY_MAX = Decimal("9999.99")          # DECIMAL(6,2)
_PART_QUANTITY_STEP = Decimal("0.01")
# The close dialog's hint "No parts recorded" (§ 1.6): ISO 14224 Table B.5's Replace, Modify and
# Overhaul, by code; Repair stays out, since most repairs fit nothing numbered (§ 9 Q6)
PARTS_HINT_ACTION_CODES = ("1", "3", "10")

PART_DESCRIPTION_NEEDED = "Describe the part"
PART_KIND_NEEDED = "Choose where the number comes from"
PART_MAKER_NEEDED = "Name the maker of this part number"
PART_QUANTITY_NEEDED = "Enter a quantity, e.g. 2 or 1.5"
PART_QUANTITY_DECIMALS = "At most two decimals"
PART_QUANTITY_TOO_BIG = f"At most {PART_QUANTITY_MAX}"
PART_UNIT_NEEDED = "Choose a unit"
PART_NODE_NEEDED = "Choose the machine or one of its parts"
# Fitting a part is a maintenance action on a failure (ISO 14224): a not-a-fault ticket cannot carry one
PARTS_NOT_A_FAULT = "Parts are recorded, so it was a fault — remove them first"


def part_quantity(value):
    """A quantity as the dialog sends it (the string typed) or as an API client may (a JSON
    number) -> ``(Decimal, None)`` or ``(None, message)``.  Converted through ``str``, never
    ``Decimal(float)``, whose binary expansion would make 1.1 fail the two-decimal rule; a bool
    is refused, as ``_is_id`` does; NaN and infinity are refused; "at most two decimals" is
    judged on the value, so "1e2" is 100 and 1.5 stays 1.50 (S020 § 5.1, BR2-01)."""
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return None, PART_QUANTITY_NEEDED
    try:
        quantity = Decimal(value.strip() if isinstance(value, str) else str(value))
    except InvalidOperation:
        return None, PART_QUANTITY_NEEDED
    if not quantity.is_finite() or quantity <= 0:
        return None, PART_QUANTITY_NEEDED
    # Before quantize: a huge value cannot be quantized to 0.01 in the default context
    if quantity > PART_QUANTITY_MAX:
        return None, PART_QUANTITY_TOO_BIG
    rounded = quantity.quantize(_PART_QUANTITY_STEP)
    if rounded != quantity:
        return None, PART_QUANTITY_DECIMALS
    return rounded, None


def validate_part(body):
    """A parts line's body -> ``(clean, errors)`` (S020 § 1.3, § 5.1): description required;
    part number optional, its kind required with it and dropped without it; the maker required
    for a maker's number; quantity; unit (``nos`` when not given); the node's id.  Whether the
    node is the ticket's machine or below it, and not scrapped, is the caller's (it needs the
    row, read locked)."""
    clean, errors = {}, []
    _optional_text(body, "description", PART_DESCRIPTION_MAX, clean, errors)
    if clean.get("description", "") is None:
        errors.append({"field": "description", "message": PART_DESCRIPTION_NEEDED})
    _optional_text(body, "part_number", PART_NUMBER_MAX, clean, errors)
    _optional_text(body, "maker", PART_MAKER_MAX, clean, errors)

    kind = body.get("number_kind")
    if clean.get("part_number") is None:
        clean["number_kind"] = None             # a kind sent without a number is dropped
    elif kind in PART_KINDS:
        clean["number_kind"] = kind
    else:
        errors.append({"field": "number_kind", "message": PART_KIND_NEEDED})
    if clean.get("number_kind") == MAKER_NUMBER and "maker" in clean and clean["maker"] is None:
        errors.append({"field": "maker", "message": PART_MAKER_NEEDED})

    quantity, message = part_quantity(body.get("quantity"))
    if message:
        errors.append({"field": "quantity", "message": message})
    else:
        clean["quantity"] = quantity

    unit = body.get("qty_unit")
    if unit is None:
        clean["qty_unit"] = DEFAULT_PART_UNIT
    elif unit in PART_UNITS:
        clean["qty_unit"] = unit
    else:
        errors.append({"field": "qty_unit", "message": PART_UNIT_NEEDED})

    if _is_id(body.get("node_id")):
        clean["node_id"] = body["node_id"]
    else:
        errors.append({"field": "node_id", "message": PART_NODE_NEEDED})
    return clean, errors
