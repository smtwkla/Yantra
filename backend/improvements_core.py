"""Improvements — pure rules (docs/steps/S067-improvement-record/1-brief.md § 5; no DB).

An improvement is the record where the team analyses one problem that tickets showed, so it
does not happen again (TPM focused improvement; ISO 9001 § 10.2.1 b).  This module holds the
states, the field validation, the start, link and remove rules, who may lead, and the loss.
improvements.py (the shell) feeds them the rows it has locked or read.
"""

from datetime import date, timedelta

from access_core import compute_permissions
from tickets_core import (
    BACK_IN_SERVICE, CLOSED, EVENT_TIME_FUTURE, FUTURE_SKEW, LABOUR_DATE_FORMAT, PLANNED_DATE_MAX_DAYS,
    PLANNED_DATE_TOO_FAR, is_breakdown, parse_event_time,
)

READ_KEY = "improvement:read"
EDIT_KEY = "improvement:edit"

SERIAL_PREFIX = "IM"

# The states (D3): only Analysing in S067; R05.4 appends its states, here and to the ENUM.
ANALYSING = "analysing"
STATES = (ANALYSING,)
# "Open" is asked in one place, so R05.4 only widens this tuple
IMPROVEMENT_OPEN_STATES = (ANALYSING,)

# Q1.1 a: a ticket starts an improvement once the machine is back in service, or after its close
START_FROM_STATES = (BACK_IN_SERVICE, CLOSED)

TITLE_MAX = 120
PROBLEM_MAX = 2000

TICKET_NEEDED = "Choose a ticket"
TITLE_NEEDED = "Enter a title"
TITLE_TOO_LONG = f"Title: up to {TITLE_MAX} characters"
TITLE_NOT_TEXT = "Title must be text"
PROBLEM_NEEDED = "Describe the problem"
PROBLEM_TOO_LONG = f"Problem: up to {PROBLEM_MAX} characters"
PROBLEM_NOT_TEXT = "Problem must be text"
LEAD_NEEDED = "Choose a lead"
LEAD_AT_SITE = "Choose an engineer or manager of this site"

START_STATE = "Start an improvement when the ticket is back in service or closed"
NOT_A_FAULT = "This ticket was closed as not a fault. There is nothing to analyse."
TICKET_OTHER_SITE = "Choose a ticket from this site"
TICKET_FROM_LIST = "Choose a ticket from the list"
ALREADY_HERE = "This ticket is already in this improvement"
ALREADY_OPEN_RACE = "This ticket is already in an open improvement. Reload the page."
IMPROVEMENT_CLOSED = "This improvement is closed"


# The why-why chain and the root cause (S069 § 5.2, § 5.3; TPM why-why, ISO 14224 failure cause)
WHYS_MAX = 20
QUESTION_MAX = 300
ANSWER_MAX = 1000
EVIDENCE_MAX = 500
ROOT_CAUSE_MAX = 500
CONTRIBUTING_MAX = 2000

QUESTION_NEEDED = "Enter the question"
QUESTION_TOO_LONG = f"Question: up to {QUESTION_MAX} characters"
QUESTION_NOT_TEXT = "Question must be text"
ANSWER_NEEDED = "Enter the answer"
ANSWER_TOO_LONG = f"Answer: up to {ANSWER_MAX} characters"
ANSWER_NOT_TEXT = "Answer must be text"
EVIDENCE_TOO_LONG = f"Evidence: up to {EVIDENCE_MAX} characters"
EVIDENCE_NOT_TEXT = "Evidence must be text"
WHYS_FULL = f"An analysis holds up to {WHYS_MAX} whys. Change a why instead."
POSITION_NOT_NUMBER = "Choose a place in the chain"
ROOT_CAUSE_NEEDED = "Enter the root cause"
ROOT_CAUSE_TOO_LONG = f"Root cause: up to {ROOT_CAUSE_MAX} characters"
ROOT_CAUSE_NOT_TEXT = "Root cause must be text"
CAUSE_NEEDED = "Choose the cause"
CAUSE_ACTIVE = "Choose an active cause from the list"
CONTRIBUTING_TOO_LONG = f"Other causes: up to {CONTRIBUTING_MAX} characters"
CONTRIBUTING_NOT_TEXT = "Other causes must be text"


# Countermeasures (S070 § 5; ISO 9001 § 10.2.1 c).  The six kinds (Q3.1 a): Correction fixes this
# failure now; Corrective removes its cause here; Preventive adds regular work (EN 13306);
# Design-out changes the machine (TPM maintenance prevention); Lesson teaches the team (TPM
# one-point lesson); Spread applies the fix to the similar machines (TPM yokoten).
ACTION_KINDS = ("correction", "corrective", "preventive", "design_out", "lesson", "spread")
ACTION_OPEN = "open"
ACTION_DONE = "done"
ACTION_CANCELLED = "cancelled"
# Done and cancelled are final (D5)
ACTION_STATES = (ACTION_OPEN, ACTION_DONE, ACTION_CANCELLED)

ACTIONS_MAX = 30
ACTION_TEXT_MAX = 500
DONE_TEXT_MAX = 1000
CANCEL_REASON_MAX = 500

KIND_NEEDED = "Choose the kind"
ACTION_TEXT_NEEDED = "Enter what will be done"
ACTION_TEXT_TOO_LONG = f"What will be done: up to {ACTION_TEXT_MAX} characters"
ACTION_TEXT_NOT_TEXT = "What will be done must be text"
OWNER_NEEDED = "Choose the owner"
OWNER_AT_SITE = "Choose a person of this site"
DONE_TEXT_NEEDED = "Say what you did"
DONE_TEXT_TOO_LONG = f"What you did: up to {DONE_TEXT_MAX} characters"
DONE_TEXT_NOT_TEXT = "What you did must be text"
REASON_NEEDED = "Say why it is cancelled"
REASON_TOO_LONG = f"Reason: up to {CANCEL_REASON_MAX} characters"
REASON_NOT_TEXT = "Reason must be text"
ACTIONS_FULL = f"An improvement holds up to {ACTIONS_MAX} countermeasures. Change an open one instead."
OWNER_OR_EDITOR = "Only the owner, or an engineer or manager of this site, can do this"
ONLY_OPEN_CHANGES = "Only an open countermeasure can be changed"
ALREADY_DONE = "This countermeasure is already done"
WAS_CANCELLED = "This countermeasure was cancelled"
DONE_NOT_CANCELLED = "A done countermeasure cannot be cancelled"
ALREADY_CANCELLED = "This countermeasure is already cancelled"

# What a countermeasure in each state refuses, per operation (§ 5.5): None = allowed
_STATE_REFUSALS = {
    "change": {ACTION_DONE: ONLY_OPEN_CHANGES, ACTION_CANCELLED: ONLY_OPEN_CHANGES},
    "done": {ACTION_DONE: ALREADY_DONE, ACTION_CANCELLED: WAS_CANCELLED},
    "cancel": {ACTION_DONE: DONE_NOT_CANCELLED, ACTION_CANCELLED: ALREADY_CANCELLED},
    "photo": {ACTION_CANCELLED: WAS_CANCELLED},
}


def already_in(ticket_serial, improvement_serial):
    return f"{ticket_serial} is already in {improvement_serial}"


def keeps_a_ticket(machine_code):
    return f"An improvement keeps a ticket of {machine_code}."


def _is_id(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


def _text(body, field, maximum, needed, too_long, not_text, clean, errors):
    """A required text when present: trimmed, 1..maximum characters."""
    value = body[field]
    if not isinstance(value, str):
        errors.append({"field": field, "message": not_text})
        return
    value = value.strip()
    if not value:
        errors.append({"field": field, "message": needed})
    elif len(value) > maximum:
        errors.append({"field": field, "message": too_long})
    else:
        clean[field] = value


def validate_improvement(body, creating):
    """The start (``creating``) or edit body -> ``(clean, errors)`` for clean_body (§ 5.2).  On a
    start every field is required; on an edit an absent field stays as it is (not in ``clean``),
    and ``lead_id`` may not be null.  ``ticket_id`` is taken only on a start; unknown fields are
    ignored."""
    clean, errors = {}, []
    if creating:
        if _is_id(body.get("ticket_id")):
            clean["ticket_id"] = body["ticket_id"]
        else:
            errors.append({"field": "ticket_id", "message": TICKET_NEEDED})
    for field, maximum, needed, too_long, not_text in (
            ("title", TITLE_MAX, TITLE_NEEDED, TITLE_TOO_LONG, TITLE_NOT_TEXT),
            ("problem", PROBLEM_MAX, PROBLEM_NEEDED, PROBLEM_TOO_LONG, PROBLEM_NOT_TEXT)):
        if field in body and body[field] is not None:
            _text(body, field, maximum, needed, too_long, not_text, clean, errors)
        elif creating or field in body:
            errors.append({"field": field, "message": needed})
    if "lead_id" in body or creating:
        if _is_id(body.get("lead_id")):
            clean["lead_id"] = body["lead_id"]
        else:
            errors.append({"field": "lead_id", "message": LEAD_NEEDED})
    return clean, errors


def validate_link(body, _creating=True):
    """The add-ticket body ``{ticket_id}`` -> ``(clean, errors)`` for clean_body."""
    if _is_id(body.get("ticket_id")):
        return {"ticket_id": body["ticket_id"]}, []
    return {}, [{"field": "ticket_id", "message": TICKET_NEEDED}]


def _optional_text(body, field, maximum, too_long, not_text, clean, errors):
    """An optional text when present: ``null`` or empty after trim -> None (stored as NULL)."""
    value = body[field]
    if value is None:
        clean[field] = None
    elif not isinstance(value, str):
        errors.append({"field": field, "message": not_text})
    elif not value.strip():
        clean[field] = None
    elif len(value.strip()) > maximum:
        errors.append({"field": field, "message": too_long})
    else:
        clean[field] = value.strip()


def validate_why(body, creating):
    """The add (``creating``) or edit body of a why -> ``(clean, errors)`` for clean_body (S069
    § 5.2).  On an add, question and answer are required and ``position`` is not taken; on an
    edit an absent field stays as it is, and ``position`` is type-checked here (its range needs
    the chain's length: position_error).  An absent evidence on an add is None."""
    clean, errors = {}, []
    for field, maximum, needed, too_long, not_text in (
            ("question", QUESTION_MAX, QUESTION_NEEDED, QUESTION_TOO_LONG, QUESTION_NOT_TEXT),
            ("answer", ANSWER_MAX, ANSWER_NEEDED, ANSWER_TOO_LONG, ANSWER_NOT_TEXT)):
        if field in body and body[field] is not None:
            _text(body, field, maximum, needed, too_long, not_text, clean, errors)
        elif creating or field in body:
            errors.append({"field": field, "message": needed})
    if "evidence" in body:
        _optional_text(body, "evidence", EVIDENCE_MAX, EVIDENCE_TOO_LONG, EVIDENCE_NOT_TEXT, clean, errors)
    elif creating:
        clean["evidence"] = None
    if not creating and "position" in body:
        position = body["position"]
        if isinstance(position, int) and not isinstance(position, bool):
            clean["position"] = position
        else:
            errors.append({"field": "position", "message": POSITION_NOT_NUMBER})
    return clean, errors


def position_error(n, position):
    """A place in a chain of ``n`` whys: None, or the refusal (a 400 on ``position``)."""
    if 1 <= position <= n:
        return None
    return f"Choose a place from 1 to {n}"


def renumber(whys):
    """``whys``: ``(id, position)`` pairs in chain order -> the pairs whose position must change
    so the positions are 1..n with no gap (after a removal: the lines after it move up)."""
    return [(why_id, place) for place, (why_id, old) in enumerate(whys, start=1) if place != old]


def reorder(whys, why_id, new_position):
    """``whys``: the chain's ``(id, position)`` pairs by position.  Move ``why_id`` to
    ``new_position`` (1..n, checked by position_error); the lines between shift by one -> the
    pairs that change, the moved why's included; none when it stays at its place."""
    moved = next(pair for pair in whys if pair[0] == why_id)
    order = [pair for pair in whys if pair[0] != why_id]
    order.insert(new_position - 1, moved)
    return renumber(order)


def validate_root_cause(body, _creating=True):
    """The root-cause body -> ``(clean, errors)`` for clean_body (S069 § 5.2).  ``root_cause``
    and ``root_cause_id`` are always required together (D4: never cleared); an absent
    ``contributing_causes`` stays as it is.  Whether the cause exists and is active is the
    shell's check."""
    clean, errors = {}, []
    if body.get("root_cause") is not None:
        _text(body, "root_cause", ROOT_CAUSE_MAX, ROOT_CAUSE_NEEDED, ROOT_CAUSE_TOO_LONG, ROOT_CAUSE_NOT_TEXT,
              clean, errors)
    else:
        errors.append({"field": "root_cause", "message": ROOT_CAUSE_NEEDED})
    if _is_id(body.get("root_cause_id")):
        clean["root_cause_id"] = body["root_cause_id"]
    else:
        errors.append({"field": "root_cause_id", "message": CAUSE_NEEDED})
    if "contributing_causes" in body:
        _optional_text(body, "contributing_causes", CONTRIBUTING_MAX, CONTRIBUTING_TOO_LONG, CONTRIBUTING_NOT_TEXT,
                       clean, errors)
    return clean, errors


def is_open(state):
    return state in IMPROVEMENT_OPEN_STATES


def start_error(state, not_a_fault):
    """May this ticket start an improvement (§ 5.3)?  None, or the refusal (a 409)."""
    if not_a_fault:
        return NOT_A_FAULT
    if state not in START_FROM_STATES:
        return START_STATE
    return None


def link_error(ticket_serial, links, improvement_id=None):
    """One open improvement per ticket (Q1.4 a).  ``links``: the ticket's improvement links,
    each ``{improvement_id, serial, open_link}``.  ``improvement_id`` is the improvement the
    ticket is being added to (None on a start).  None, or the refusal (a 409)."""
    if improvement_id is not None and any(link["improvement_id"] == improvement_id for link in links):
        return ALREADY_HERE
    for link in links:
        if link["open_link"]:
            return already_in(ticket_serial, link["serial"])
    return None


def removal_error(ticket, links, machine):
    """May this ticket leave the improvement (§ 5.3, BR1-02 a)?  The improvement keeps at least
    one ticket of its own machine.  ``ticket`` and each of ``links`` (the improvement's linked
    tickets, this one included) carry ``id`` and ``equipment_id``; ``machine`` is the
    improvement's ``{id, code}``.  None, or the refusal (a 409)."""
    if ticket["equipment_id"] != machine["id"]:
        return None
    others = [link for link in links if link["id"] != ticket["id"] and link["equipment_id"] == machine["id"]]
    return None if others else keeps_a_ticket(machine["code"])


def may_lead(role):
    """A role at a site may lead an improvement there when it grants improvement:edit (D6): the
    rule follows config_rbac, never a role list of its own."""
    return EDIT_KEY in compute_permissions([role])


def loss(tickets):
    """The loss of an improvement's tickets, each with ``intensity`` and ``downtime_minutes``
    (None on a not-a-fault ticket) -> ``{tickets, breakdowns, downtime_minutes}``."""
    return {
        "tickets": len(tickets),
        "breakdowns": sum(1 for t in tickets if is_breakdown(t["intensity"])),
        "downtime_minutes": sum(t["downtime_minutes"] or 0 for t in tickets),
    }


# ---------------------------------------------------------------------------
# Countermeasures (S070 § 5)
# ---------------------------------------------------------------------------

def _required(body, field, creating):
    """A field a POST needs and a PUT may leave out, but never send as null: is it to be read?
    -> (read it, missing).  ``missing`` is True when it is required here and not given."""
    if field in body and body[field] is not None:
        return True, False
    return False, creating or field in body


def validate_action(body, creating):
    """The add (``creating``) or change body of a countermeasure -> ``(clean, errors)`` for
    clean_body (§ 5.2).  On an add every field is required; on a change an absent field stays as
    it is and none may be null.  Whether the owner may own it (the shell's person_at_site) and
    the due date's range (due_date_error) are checked after.  Unknown fields, the state and the
    done and cancel fields are ignored."""
    clean, errors = {}, []
    read, missing = _required(body, "kind", creating)
    if read and body["kind"] in ACTION_KINDS:
        clean["kind"] = body["kind"]
    elif read or missing:
        errors.append({"field": "kind", "message": KIND_NEEDED})
    read, missing = _required(body, "text", creating)
    if read:
        _text(body, "text", ACTION_TEXT_MAX, ACTION_TEXT_NEEDED, ACTION_TEXT_TOO_LONG, ACTION_TEXT_NOT_TEXT,
              clean, errors)
    elif missing:
        errors.append({"field": "text", "message": ACTION_TEXT_NEEDED})
    read, missing = _required(body, "owner_id", creating)
    if read and _is_id(body["owner_id"]):
        clean["owner_id"] = body["owner_id"]
    elif read or missing:
        errors.append({"field": "owner_id", "message": OWNER_NEEDED})
    read, missing = _required(body, "due_date", creating)
    due = _iso_date(body["due_date"]) if read else None
    if due is not None:
        clean["due_date"] = due
    elif read or missing:
        errors.append({"field": "due_date", "message": LABOUR_DATE_FORMAT})
    return clean, errors


def _iso_date(value):
    """``YYYY-MM-DD`` (trimmed) -> the date, or None for anything else."""
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def validate_done(body, _creating=True):
    """The mark-done body -> ``(clean, errors)`` (§ 5.2).  ``done_at`` absent or null is None:
    the S051 *Now* tick sends nothing and the server's clock decides."""
    clean, errors = {}, []
    if body.get("done_text") is not None:
        _text(body, "done_text", DONE_TEXT_MAX, DONE_TEXT_NEEDED, DONE_TEXT_TOO_LONG, DONE_TEXT_NOT_TEXT,
              clean, errors)
    else:
        errors.append({"field": "done_text", "message": DONE_TEXT_NEEDED})
    clean["done_at"] = None
    if body.get("done_at") is not None:
        value, message = parse_event_time(body["done_at"])
        if message:
            errors.append({"field": "done_at", "message": message})
        else:
            clean["done_at"] = value
    return clean, errors


def validate_cancel(body, _creating=True):
    """The cancel body ``{reason}`` -> ``(clean, errors)`` (§ 5.2)."""
    clean, errors = {}, []
    if body.get("reason") is not None:
        _text(body, "reason", CANCEL_REASON_MAX, REASON_NEEDED, REASON_TOO_LONG, REASON_NOT_TEXT, clean, errors)
    else:
        errors.append({"field": "reason", "message": REASON_NEEDED})
    return clean, errors


def due_date_error(due, problem_date, today):
    """§ 5.3, D7: from the day the problem happened (the earliest linked ticket's date; None
    sets no floor) to today + PLANNED_DATE_MAX_DAYS.  A date in the past is allowed: a
    correction already done is recorded with its true dates.  -> the message, or None."""
    if problem_date is not None and due < problem_date:
        return f"Choose a date from {problem_date:%d-%m-%Y}, the day the problem happened"
    if due > today + timedelta(days=PLANNED_DATE_MAX_DAYS):
        return PLANNED_DATE_TOO_FAR
    return None


def done_time_error(done_at, now, problem_at):
    """§ 5.3, D6: not more than FUTURE_SKEW ahead of now, and not before the problem happened
    (the earliest linked ticket's time; None sets no floor).  No 7-day limit.  -> the message,
    or None.  The floor is the minute shown in the message: a ticket raised with *Now* stores
    seconds, and a done time typed in that same minute must pass."""
    if done_at > now + FUTURE_SKEW:
        return EVENT_TIME_FUTURE
    if problem_at is not None and done_at < problem_at.replace(second=0, microsecond=0):
        return f"Not before the problem happened, {problem_at:%d-%m-%Y %H:%M}"
    return None


def action_state_error(operation, state):
    """May ``operation`` (change, done, cancel, photo) act on a countermeasure in ``state``
    (§ 5.5)?  None, or the refusal (a 409)."""
    return _STATE_REFUSALS[operation].get(state)


def overdue_days(state, due_date, today):
    """§ 5.4: the days an open countermeasure is past its due date; 0 when due today or later,
    done or cancelled.  Computed, never stored."""
    if state != ACTION_OPEN:
        return 0
    return max((today - due_date).days, 0)


def action_counts(actions):
    """``actions``, each with ``state`` and ``overdue_days`` -> ``{open, done, cancelled,
    overdue}`` (S071's "2 of 6 done"; R05.4's *Watching* reads ``open``)."""
    counts = dict.fromkeys(ACTION_STATES, 0)
    for action in actions:
        counts[action["state"]] += 1
    counts["overdue"] = sum(1 for action in actions if action["overdue_days"] > 0)
    return counts


def action_flags(improvement_open, state, may_edit, is_owner):
    """What the user may do on one countermeasure (§ 5.7), so no control ends in a 403 or a 409.
    ``may_edit``: improvement:edit at the improvement's site; ``is_owner``: the user's own Team
    record owns it."""
    may_act = may_edit or is_owner
    return {
        "can_change": improvement_open and state == ACTION_OPEN and may_edit,
        "can_mark_done": improvement_open and state == ACTION_OPEN and may_act,
        "can_add_photo": improvement_open and state != ACTION_CANCELLED and may_act,
    }
