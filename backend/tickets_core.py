"""Tickets — pure rules (docs/steps/S017-raise-tickets/1-brief.md; no DB, no clock, no Flask).

A ticket is the work request of EN 13460 (S018 turns it into the work order): one record per
problem found on equipment, a breakdown or a defect by its intensity (Plan.MD § 4.2).  The
intensity is ISO 14224's failure impact: critical (the item stopped: a breakdown, EN 13306's
failure), degraded (a partial failure) or initial (ISO's incipient: early signs).

Every function takes plain data; the caller passes ``now`` (IST, naive) so nothing here reads
the clock.
"""

import re
from datetime import datetime, timedelta

INTENSITIES = ("critical", "degraded", "initial")
BREAKDOWN_INTENSITY = "critical"

# The full S018 set (S017 § 7 decision 7), in workflow order; S017 writes only "raised"
STATES = ("raised", "acknowledged", "in_progress", "back_in_service", "closed")
RAISED = "raised"
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
    field: equipment_id, intensity, failure_mode_id, reported_by_id (None when not given),
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

    return clean, errors


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
