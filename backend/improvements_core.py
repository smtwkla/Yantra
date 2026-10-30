"""Improvements — pure rules (docs/steps/S067-improvement-record/1-brief.md § 5; no DB).

An improvement is the record where the team analyses one problem that tickets showed, so it
does not happen again (TPM focused improvement; ISO 9001 § 10.2.1 b).  This module holds the
states, the field validation, the start, link and remove rules, who may lead, and the loss.
S069 and S070 add the why-why chain, the root cause and the countermeasures; S072 the working
states, the watch and its figures, the closes and the timeline's lines.
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
# S072 § 5.8: who decides whether the fix worked, and who adds a note to the timeline
VERIFY_KEY = "improvement:verify"
NOTE_KEY = "improvement:note"

SERIAL_PREFIX = "IM"

# The states (S067 D3; S072 § 5.1, R05.4).  The first three move by themselves when the data
# changes (working_state); the closes are decisions.  These are the stored values (the ENUM).
ANALYSING = "analysing"
ACTIONS_OPEN = "actions_open"
WATCHING = "watching"
CLOSED_EFFECTIVE = "closed_effective"
CLOSED_NOT_EFFECTIVE = "closed_not_effective"
DROPPED = "dropped"
STATES = (ANALYSING, ACTIONS_OPEN, WATCHING, CLOSED_EFFECTIVE, CLOSED_NOT_EFFECTIVE, DROPPED)
# Computed from the clock, never stored (S072 D1): a watching improvement whose watch has ended
READY_TO_VERIFY = "ready_to_verify"
# "Open" is asked of the STORED state only (BR1-03): is_open(READY_TO_VERIFY) is False, so no
# caller passes the display state to is_open; the detail and the ticket page compute is_open
# from the row before they show the display state.
IMPROVEMENT_OPEN_STATES = (ANALYSING, ACTIONS_OPEN, WATCHING)
CLOSED_STATES = (CLOSED_EFFECTIVE, CLOSED_NOT_EFFECTIVE, DROPPED)

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


# Public names for procedures_core (S075 D10): one copy of the id and text rules, and no import of
# a private name.  The private names stay, so this module's own code is unchanged.
is_id = _is_id
text_field = _text


def validate_improvement(body, creating):
    """The start (``creating``) or edit body -> ``(clean, errors)`` for clean_body (§ 5.2).  On a
    start every field is required; on an edit an absent field stays as it is (not in ``clean``),
    and ``lead_id`` may not be null.  ``ticket_id`` is taken only on a start, ``watch_days``
    (S072 § 5.3) only on an edit; unknown fields are ignored."""
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
    if not creating and "watch_days" in body:
        days = body["watch_days"]
        if isinstance(days, int) and not isinstance(days, bool) and WATCH_DAYS_MIN <= days <= WATCH_DAYS_MAX:
            clean["watch_days"] = days
        else:
            errors.append({"field": "watch_days", "message": WATCH_DAYS_RANGE})
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


# ---------------------------------------------------------------------------
# The states, the watch, the close and the timeline (S072 § 5; ISO 9001 § 10.2.1 d, § 7.5.3)
# ---------------------------------------------------------------------------

# The kinds that act on the linked machines (S070 § 2): only these end and start the watch (D3).
# A Lesson or a Spread changes nothing on the machines the watch counts.
WATCH_KINDS = ("correction", "corrective", "preventive", "design_out")

# Q4.1 a: 90 days by default (dust builds up over months), set per improvement
WATCH_DAYS_DEFAULT = 90
WATCH_DAYS_MIN = 30
WATCH_DAYS_MAX = 365
WATCH_DAYS_RANGE = f"Choose a watch of {WATCH_DAYS_MIN} to {WATCH_DAYS_MAX} days"

CLOSE_TEXT_MAX = 1000
VERIFY_NOT_YET = "Verify once every countermeasure is done and the watch has ended"
NOTE_NEEDED = "Write the note"
NOTE_TOO_LONG = f"Note: up to {CLOSE_TEXT_MAX} characters"
NOTE_NOT_TEXT = "Note must be text"
# The close bodies' one text field -> (needed, too long, not text) (§ 5.3)
_CLOSE_MESSAGES = {
    "remark": ("Say why it did not work", f"Remark: up to {CLOSE_TEXT_MAX} characters", "Remark must be text"),
    "reason": ("Say why it is dropped", f"Reason: up to {CLOSE_TEXT_MAX} characters", "Reason must be text"),
}
DROPPED_WITH = "Dropped with the improvement: "

# The timeline's events (§ 5.6), the names improvement_events.event holds
STARTED = "started"
EDITED = "edited"
TICKET_LINKED = "ticket_linked"
TICKET_REMOVED = "ticket_removed"
WHY_ADDED = "why_added"
WHY_CHANGED = "why_changed"
WHY_REMOVED = "why_removed"
ROOT_CAUSE_SET = "root_cause_set"
ROOT_CAUSE_CHANGED = "root_cause_changed"
ACTION_ADDED = "action_added"
ACTION_CHANGED = "action_changed"
ACTION_DONE_EVENT = "action_done"
ACTION_CANCELLED_EVENT = "action_cancelled"
STATE_CHANGED = "state_changed"
NOTE = "note"
# The close events carry the state's name; watch_ended is computed, never stored (D1)
WATCH_ENDED = "watch_ended"

# The six kind words of S070 § 2, for the timeline's lines (the frontend's ACTION_KINDS keeps
# the same words, as WAITING_REASONS and its copy)
ACTION_KIND_LABELS = {
    "correction": "Correction", "corrective": "Corrective", "preventive": "Preventive",
    "design_out": "Design-out", "lesson": "Lesson", "spread": "Spread",
}
# The fields of an edit line, in their order (tickets_core.edit_lines' labels)
EDIT_LABELS = {"title": "Title", "problem": "Problem", "lead": "Lead", "watch": "Watch"}
ACTION_EDIT_LABELS = {"kind": "Kind", "text": "What will be done", "owner": "Owner", "due": "Due"}


def watch_ends(until):
    return f"The watch ends on {until:%d-%m-%Y}. Verify after it."


def watch_days_text(days):
    return f"{days} days"


def working_state(stored_state, root_cause_set, actions):
    """The working state the data earns (§ 5.1, D2), never chosen by a button.  ``actions``: the
    improvement's countermeasures, each with ``kind``, ``state`` and ``done_at``.
    1. no root cause -> Analysing (Q2.2 a: the root cause comes before Watching);
    2. watching, and no countermeasure of a WATCH_KINDS kind open -> stays Watching (a Lesson or
       Spread added during the watch does not end it, D3);
    3. none open and at least one done -> Watching;
    4. else Actions open (also when every one was cancelled: nothing was done to watch)."""
    if not root_cause_set:
        return ANALYSING
    open_kinds = [a["kind"] for a in actions if a["state"] == ACTION_OPEN]
    if stored_state == WATCHING and not any(kind in WATCH_KINDS for kind in open_kinds):
        return WATCHING
    if not open_kinds and any(a["state"] == ACTION_DONE for a in actions):
        return WATCHING
    return ACTIONS_OPEN


def watch_start(actions):
    """When the watch starts (§ 5.1, D3, D4): the latest done_at of the done countermeasures of a
    WATCH_KINDS kind; when none of those is done (only lessons or spreads), the latest done_at of
    any done one; None when nothing is done."""
    done = [a for a in actions if a["state"] == ACTION_DONE]
    times = [a["done_at"] for a in done if a["kind"] in WATCH_KINDS] or [a["done_at"] for a in done]
    return max(times) if times else None


def watch_until(watch_from, watch_days):
    """The watch's end, a datetime (§ 5.2): done 20-11-2026 15:30 + 90 days -> 18-02-2027 15:30."""
    return watch_from + timedelta(days=watch_days)


def display_state(state, watch_from, watch_days, now):
    """The state an answer shows (§ 5.2, D1): Ready to verify once a watching improvement's watch
    has ended, else the stored state.  Never passed to is_open (BR1-03)."""
    if state == WATCHING and watch_from is not None and now >= watch_until(watch_from, watch_days):
        return READY_TO_VERIFY
    return state


def close_error(shown_state, until):
    """May the improvement be closed as effective or not effective now (§ 5.1's table)?
    ``shown_state`` is the display state; ``until`` the watch's end (None before the watch).
    -> None, or the refusal (a 409).  The two closes refuse the same cells."""
    if shown_state == READY_TO_VERIFY:
        return None
    if shown_state in CLOSED_STATES:
        return IMPROVEMENT_CLOSED
    if shown_state == WATCHING:
        return watch_ends(until)
    return VERIFY_NOT_YET


def validate_close(body, needed, field):
    """A close body's one text (§ 5.3): ``field`` is ``remark`` (the closes) or ``reason`` (the
    drop).  ``needed``: required, 1..CLOSE_TEXT_MAX after trim; else optional, absent, null or
    empty -> None.  -> ``(clean, errors)``; unknown fields are ignored."""
    needed_message, too_long, not_text = _CLOSE_MESSAGES[field]
    clean, errors = {}, []
    if needed:
        if body.get(field) is not None:
            _text(body, field, CLOSE_TEXT_MAX, needed_message, too_long, not_text, clean, errors)
        else:
            errors.append({"field": field, "message": needed_message})
    else:
        clean[field] = None
        if field in body:
            _optional_text(body, field, CLOSE_TEXT_MAX, too_long, not_text, clean, errors)
    return clean, errors


def validate_note(body, _creating=True):
    """The note body ``{remark}`` (§ 5.3, § 5.5): required, trimmed at its ends (line breaks
    inside kept), 1..CLOSE_TEXT_MAX."""
    clean, errors = {}, []
    if body.get("remark") is not None:
        _text(body, "remark", CLOSE_TEXT_MAX, NOTE_NEEDED, NOTE_TOO_LONG, NOTE_NOT_TEXT, clean, errors)
    else:
        errors.append({"field": "remark", "message": NOTE_NEEDED})
    return clean, errors


def dropped_reason(reason):
    """A countermeasure's cancel reason when its improvement is dropped (D10), cut to the cancel
    reason's bound."""
    return f"{DROPPED_WITH}{reason}"[:CANCEL_REASON_MAX]


def _window(rows, days, symptom_ids):
    breakdowns = [t for t in rows if is_breakdown(t["intensity"])]
    return {
        "days": days,
        "breakdowns": len(breakdowns),
        "symptom_breakdowns": (sum(1 for t in breakdowns if t["failure_mode_id"] in symptom_ids)
                               if symptom_ids else None),
        "downtime_minutes": sum(t["downtime_minutes"] or 0 for t in rows),
    }


def watch_figures(tickets, symptom_ids, watch_from, watch_days, end):
    """The watch's facts (§ 5.4, D4, D5; ISO 9001 § 10.2.1 d): the machines' tickets in the
    ``watch_days`` before ``watch_from`` against the days after it, to ``end`` (now, or the close)
    or the watch's end, whichever is first; and the repeats.  ``tickets``: the machines' tickets
    (not-a-fault already left out), each with ``id``, ``serial``, ``occurred_at``, ``intensity``,
    ``failure_mode_id``, ``machine_code``, ``symptom`` and ``downtime_minutes``; ``symptom_ids``
    the linked tickets' symptoms (failure modes, ISO 14224).  A ticket counts on the side of its
    occurred_at, its downtime in full.  Repeats: every ticket with one of the symptoms from
    ``watch_from`` to ``end``, any intensity (a degraded return is still a return), ``in_watch``
    False once past the watch's end.  -> ``{before, after, repeats}``."""
    until = watch_until(watch_from, watch_days)
    after_end = min(end, until)
    begin = watch_from - timedelta(days=watch_days)
    before = [t for t in tickets if begin <= t["occurred_at"] < watch_from]
    after = [t for t in tickets if watch_from <= t["occurred_at"] < after_end]
    repeats = [{
        "id": t["id"], "serial": t["serial"], "occurred_at": t["occurred_at"], "intensity": t["intensity"],
        "machine_code": t["machine_code"], "symptom": t["symptom"], "in_watch": t["occurred_at"] < until,
    } for t in tickets
        if symptom_ids and t["failure_mode_id"] in symptom_ids and watch_from <= t["occurred_at"] < end]
    return {
        "before": _window(before, watch_days, symptom_ids),
        "after": _window(after, max((after_end - watch_from).days, 0), symptom_ids),
        "repeats": repeats,
    }


def why_line(position, question, answer, evidence):
    """A why as one timeline line: "3. Why …? Because: … Evidence: …" (the evidence only when
    set; v39's backfill writes the same shape)."""
    parts = [f"{position}.", question, f"Because: {answer}"]
    if evidence:
        parts.append(f"Evidence: {evidence}")
    return " ".join(parts)


def root_cause_line(cause_code, cause_label, text, contributing):
    """The root cause as a timeline line: "4.2 Management error: <text>", and a second line
    "Other causes: …" when set."""
    line = f"{cause_code} {cause_label}: {text}"
    return f"{line}\nOther causes: {contributing}" if contributing else line


def role_word(role):
    """A site role as one plain word for a line: maint_technician -> technician."""
    return role.removeprefix("maint_").replace("_", " ")


def action_line(kind, text, owner_name, owner_role, due):
    """A new countermeasure as a timeline line: "Corrective: <text>. Owner Kannan (technician),
    due 08-11-2026."  ``owner_role`` None leaves the bracket out."""
    owner = f"{owner_name} ({role_word(owner_role)})" if owner_role else owner_name
    return f"{ACTION_KIND_LABELS[kind]}: {text}. Owner {owner}, due {due:%d-%m-%Y}."


def with_watch_ended(lines, show, until):
    """The timeline, newest first, with the computed *Watch ended* line in its place by time
    (§ 5.6, D1) when ``show`` (the display state is Ready to verify, or the improvement was closed
    effective or not effective).  ``lines`` carry ``occurred_at`` as datetimes."""
    if not show:
        return lines
    ended = {"id": None, "event": WATCH_ENDED, "occurred_at": until, "by_name": None, "from_state": None,
             "to_state": None, "ticket": None, "action": None, "remark": None, "earlier": None}
    place = next((i for i, line in enumerate(lines) if line["occurred_at"] <= until), len(lines))
    return [*lines[:place], ended, *lines[place:]]
