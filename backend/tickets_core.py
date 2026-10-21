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

INTENSITIES = ("critical", "degraded", "initial")
BREAKDOWN_INTENSITY = "critical"

# The full S018 set (S017 § 7 decision 7), in workflow order
STATES = ("raised", "acknowledged", "in_progress", "back_in_service", "closed")
RAISED = "raised"
ACKNOWLEDGED = "acknowledged"
IN_PROGRESS = "in_progress"
BACK_IN_SERVICE = "back_in_service"
CLOSED = "closed"
OPEN_STATES = tuple(state for state in STATES if state != CLOSED)

# The list's filters: a group or one intensity
INTENSITY_FILTERS = {
    "breakdown": (BREAKDOWN_INTENSITY,),
    "defect": tuple(i for i in INTENSITIES if i != BREAKDOWN_INTENSITY),
    **{intensity: (intensity,) for intensity in INTENSITIES},
}
STATE_FILTERS = ("open", "closed", "all")

# Phone clocks drift a few minutes; a late entry at the end of a shift is normal, but older
# history (notebooks) is out of scope and would distort this month's figures (§ 7 decision 9)
FUTURE_SKEW = timedelta(minutes=5)
MAX_BACKDATE_DAYS = 7

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


def event_time_error(event_time, now, not_before=None):
    """The window an entered event time must fall in -> the message, or None: at most
    FUTURE_SKEW ahead of ``now``, at most MAX_BACKDATE_DAYS back, and not before
    ``not_before`` (S018: the ticket's last event)."""
    if event_time > now + FUTURE_SKEW:
        return EVENT_TIME_FUTURE
    if event_time < now - timedelta(days=MAX_BACKDATE_DAYS):
        return EVENT_TIME_TOO_OLD
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


def validate_raise(body, now):
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
        message = message or event_time_error(occurred_at, now)
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

# The events that move the ticket's state or intensity: the times are computed from these, so
# they must stay in order (§ 5.1).  Edits and assignments are stamped with the time they were
# recorded and take no part in the order rule.
ORDERED_EVENTS = (RAISED, ACKNOWLEDGED_EVENT, STARTED_EVENT, BACK_IN_SERVICE_EVENT, SENT_BACK_EVENT, CLOSED_EVENT,
                  NOT_A_FAULT_EVENT, REGRADED_EVENT)

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
}

REMARK_MAX = 1000                       # ticket_events.remark
REPEAT_WINDOW_DAYS = 7                  # user decision 6
LABOUR_MINUTES_MAX = 24 * 60            # chk_ticket_labour_minutes

# Severity order, for "raising" and "lowering" a grade
_INTENSITY_RANK = {"initial": 1, "degraded": 2, "critical": 3}
LOWER_THAN_BREAKDOWN = "degraded"       # a send-back with the machine running (§ 1)

# Re-grade: any open state before back in service (Plan.MD § 4.2)
REGRADE_STATES = (RAISED, ACKNOWLEDGED, IN_PROGRESS)
# "Not fixed — raise again" is offered on a ticket that was back in service (§ 5.5)
REPEAT_FROM_STATES = (BACK_IN_SERVICE, CLOSED)
# Downtime runs while the machine is critical in these states (§ 5.4)
_DOWN_STATES = (RAISED, ACKNOWLEDGED, IN_PROGRESS)

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


@dataclass(frozen=True)
class Move:
    from_states: tuple      # the states it may start from
    to_state: str
    key: str                # the permission, checked at the ticket's site
    event: str              # the ticket_events.event it writes
    requires: tuple = ()    # body fields that must be given (§ 5.2)


# The moves of § 1, in the order the page shows them: the chain first, then the significant ones
MOVES = {
    "acknowledge": Move((RAISED,), ACKNOWLEDGED, WORK_KEY, ACKNOWLEDGED_EVENT),
    "start": Move((RAISED, ACKNOWLEDGED), IN_PROGRESS, WORK_KEY, STARTED_EVENT),
    "restore": Move((RAISED, ACKNOWLEDGED, IN_PROGRESS), BACK_IN_SERVICE, RESTORE_KEY, BACK_IN_SERVICE_EVENT,
                    ("person_id",)),
    "send-back": Move((BACK_IN_SERVICE,), IN_PROGRESS, CLOSE_KEY, SENT_BACK_EVENT, ("machine_down", "remark")),
    "close": Move((BACK_IN_SERVICE,), CLOSED, CLOSE_KEY, CLOSED_EVENT, ("cause_id", "action_id")),
    "not-a-fault": Move((RAISED, ACKNOWLEDGED), CLOSED, CLOSE_KEY, NOT_A_FAULT_EVENT, ("cause_id", "remark")),
}

# The moves that add the user's own person as an assignee (§ 5.8)
AUTO_ASSIGN_MOVES = ("acknowledge", "start")

_REQUIRED_MESSAGES = {
    "person_id": PERSON_NEEDED,
    "remark": REMARK_NEEDED,
    "machine_down": MACHINE_DOWN_NEEDED,
    "cause_id": CAUSE_NEEDED,
    "action_id": ACTION_NEEDED,
}


def allowed_moves(state, held_keys):
    """The moves the user may make now on a ticket in ``state``, holding ``held_keys`` at the
    ticket's site -> their names, in MOVES order.  The page shows exactly these buttons."""
    return [name for name, move in MOVES.items() if state in move.from_states and move.key in held_keys]


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


def _event_fields(body):
    """What every move and re-grade takes: the event time (None = the server's clock) and a remark."""
    clean, errors = {}, []
    _optional_time(body, "occurred_at", clean, errors)
    _optional_text(body, "remark", REMARK_MAX, clean, errors)
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
    Not a fault needs nothing beyond its required cause and remark."""
    move = MOVES[name]
    clean, errors = _event_fields(body)
    if name == "restore":
        _optional_id(body, "person_id", "Choose a person from the list", clean, errors)
        _optional_time(body, "started_at", clean, errors)
    elif name == "send-back":
        machine_down = body.get("machine_down")
        if machine_down is None or isinstance(machine_down, bool):
            clean["machine_down"] = machine_down
        else:
            errors.append({"field": "machine_down", "message": MACHINE_DOWN_NEEDED})
    elif name in ("close", "not-a-fault"):
        _optional_id(body, "cause_id", CAUSE_NEEDED, clean, errors)
        if name == "close":
            _optional_id(body, "action_id", ACTION_NEEDED, clean, errors)
            _optional_id(body, "failure_mode_id", MODE_NEEDED, clean, errors)
    failed = {error["field"] for error in errors}
    for field in move.requires:
        if field not in failed and clean.get(field) is None:
            errors.append({"field": field, "message": _REQUIRED_MESSAGES[field]})
    return clean, errors


def _when(value):
    return value.strftime("%d-%m-%Y %H:%M")


# What the raise screen calls its raise time, for refusals on the *Already fixed* times (CR3-01):
# the user sees "When did it happen?", not "Raised"
RAISE_SCREEN_LABELS = {**EVENT_LABELS, RAISED: "the time it happened"}


def validate_event_time(event_time, last_event, now, labels=EVENT_LABELS):
    """S017's window for an entered time (event_time_error), with the ticket's last ordered
    event ``(event, occurred_at)`` as the lower bound; the refusal names that event (as
    ``labels`` words it) and its time -> the message, or None."""
    last_name, last_time = last_event
    message = event_time_error(event_time, now, not_before=last_time)
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

    raw = body.get("work_date")
    work_date = None
    if isinstance(raw, str):
        try:
            work_date = date.fromisoformat(raw.strip())
        except ValueError:
            work_date = None
    if work_date is None:
        errors.append({"field": "work_date", "message": LABOUR_DATE_FORMAT})
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


def ticket_times(events, now):
    """The ticket's figures from its events, oldest first (``event``, ``occurred_at``,
    ``intensity``), against ``now`` -> ``{response_minutes, repair_minutes, downtime_minutes}``
    (§ 5.4).  Each is None when unknown; all three are None on a ticket closed as not a fault.
    - response: raised -> the first acknowledged or started;
    - repair (EN 13306 active corrective maintenance time): the time in progress, from each
      started or sent_back to the next back in service (an open one to ``now``); None when a
      back in service had no start before it, or work never started;
    - downtime (EN 13306 time to restoration): the time while critical and not yet back in
      service, an open ticket to ``now``."""
    if any(e["event"] == NOT_A_FAULT_EVENT for e in events):
        return {"response_minutes": None, "repair_minutes": None, "downtime_minutes": None}

    raised_at = response = None
    repair, repair_known, repair_seen = timedelta(0), True, False
    downtime = timedelta(0)
    state = intensity = repair_from = down_from = None

    for event in events:
        name, at = event["event"], event["occurred_at"]
        if name not in ORDERED_EVENTS:
            continue
        if down_from is not None:
            downtime += max(timedelta(0), at - down_from)
            down_from = None
        if event.get("intensity"):
            intensity = event["intensity"]
        if name == RAISED:
            state, raised_at = RAISED, at
        elif name == ACKNOWLEDGED_EVENT:
            state = ACKNOWLEDGED
        elif name in (STARTED_EVENT, SENT_BACK_EVENT):
            state, repair_from, repair_seen = IN_PROGRESS, at, True
        elif name == BACK_IN_SERVICE_EVENT:
            state = BACK_IN_SERVICE
            if repair_from is None:
                repair_known = False
            else:
                repair += max(timedelta(0), at - repair_from)
                repair_from = None
        elif name == CLOSED_EVENT:
            state = CLOSED
        if response is None and raised_at is not None and name in (ACKNOWLEDGED_EVENT, STARTED_EVENT):
            response = at - raised_at
        if state in _DOWN_STATES and intensity == BREAKDOWN_INTENSITY:
            down_from = at

    if down_from is not None:
        downtime += max(timedelta(0), now - down_from)
    if repair_from is not None:
        repair += max(timedelta(0), now - repair_from)
    return {
        "response_minutes": None if response is None else _minutes(response),
        "repair_minutes": _minutes(repair) if repair_known and repair_seen else None,
        "downtime_minutes": _minutes(downtime),
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
