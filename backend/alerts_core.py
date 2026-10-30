"""Alerts — pure rules, the same for every channel (docs/steps/S021-alerts-push/1-brief.md § 1.4,
§ 5.1–5.3, § 10 A1; no DB, no clock, no Flask).  Push is the channel today (push_core); S023's
Telegram would read the same facts and texts.

An alert is a message about a record.  About a ticket: a new breakdown, a new defect, *down
again*, an escalation of a breakdown nobody acknowledged in time, *assigned to you*, or (S032)
*ticket closed*.  About an improvement (S074, R05.5): *countermeasure for you*, *countermeasure
overdue* and *ready to verify*.  Each record has its own kinds, rules and texts here and its own
alert task (task_handlers); the channels, the push fan-out and the recipient query are shared
(S074 D1), so PM (R03.7) adds its kinds the same way.  It answers ISO 55001 § 7.4 / ISO 9001
§ 7.4 (what is communicated, when, to whom and how): the audience and channel tables below are
that decision, and you_get shows each person their part of it.
"""

from collections import namedtuple
from datetime import timedelta

from access_core import compute_permissions
from config_rbac import ASSIGNABLE_ROLES
from equipment_core import effective_criticality
from improvements_core import ACTION_OPEN, EDIT_KEY, IMPROVEMENT_OPEN_STATES, READ_KEY, VERIFY_KEY, WATCHING, watch_until
from tickets_core import (
    BREAKDOWN_INTENSITY, CLOSED as CLOSED_STATE, DOWN_STATES, MAX_BACKDATE_DAYS, OPEN_STATES, RAISED, SENT_BACK_EVENT,
)

BREAKDOWN = "breakdown"
DEFECT = "defect"
ESCALATION = "escalation"
ASSIGNED = "assigned"      # A1: Job assigned to you
CLOSED = "closed"          # S032: Ticket closed, by email
TICKET_KINDS = (BREAKDOWN, DEFECT, ESCALATION, ASSIGNED, CLOSED)
# S074: about an improvement.  The codes differ from S072's display state ready_to_verify, so a
# grep for one never finds the other.
ACTION_GIVEN = "action_given"        # Countermeasure for you
ACTION_OVERDUE = "action_overdue"    # Countermeasure overdue
VERIFY_READY = "verify_ready"        # Ready to verify
IMPROVEMENT_KINDS = (ACTION_GIVEN, ACTION_OVERDUE, VERIFY_READY)
KINDS = TICKET_KINDS + IMPROVEMENT_KINDS

ENGINEER = "maint_engineer"
SUPERVISOR = "maint_supervisor"
MANAGER = "maint_manager"

# Who gets each kind, at the ticket's site and unit (§ 5.2).  Roles are matched exactly, not
# through ROLE_INCLUDES: a manager holds the engineer's permissions, but "engineers quietly"
# means engineers (§ 7 decision 6).  ASSIGNED has no audience: it goes to the one assignee.
AUDIENCE = {
    BREAKDOWN: (ENGINEER, SUPERVISOR, MANAGER),
    DEFECT: (ENGINEER,),
    ESCALATION: (ENGINEER, MANAGER),
    CLOSED: (MANAGER,),    # S032 § 5.2: the close-out review is the manager's
}

# How each kind travels (S032 § 5.1).  ticket_alert fans out per channel; a channel not set up on
# the server is skipped there.  Adding email to another kind is one entry here (and its text).
PUSH = "push"
EMAIL = "email"
CHANNELS = {
    BREAKDOWN: (PUSH,),
    DEFECT: (PUSH,),
    ESCALATION: (PUSH,),
    ASSIGNED: (PUSH,),
    CLOSED: (EMAIL,),
    # S074 (Q5.1 a): push only.  Email later is an entry here, a text per kind and the email
    # branch of improvement_alert (D9).
    ACTION_GIVEN: (PUSH,),
    ACTION_OVERDUE: (PUSH,),
    VERIFY_READY: (PUSH,),
}

# S074 § 5.6, D6: an improvement alert goes to the holders of the key it is about, at the
# improvement's site and covering its unit, so nobody gets an alert about a page that would
# refuse them (ISO 27001 A.8.3).  Unlike AUDIENCE, by key, not by exact role: the manager verifies
# too.  ACTION_GIVEN and ACTION_OVERDUE keep only the owner (and the lead) among the holders.
IMPROVEMENT_AUDIENCE_KEY = {ACTION_GIVEN: READ_KEY, ACTION_OVERDUE: READ_KEY, VERIFY_READY: VERIFY_KEY}

# When a drained alert is still worth sending (BR2-04): a worker an hour late does not wake the
# supervisor for a machine already back in service
_SEND_STATES = {BREAKDOWN: DOWN_STATES, DEFECT: DOWN_STATES, ESCALATION: OPEN_STATES, ASSIGNED: OPEN_STATES,
                # S032 § 5.3: only while still closed (a closed ticket stays closed today; this
                # guards a future reopen)
                CLOSED: (CLOSED_STATE,)}

# Escalation per criticality grade (§ 1.5; Maintenance-Philosophy § 9).  Equipment must have a
# grade (new equipment starts at C), so an ungraded item is a leftover and counts as C.
GRADES = ("A", "B", "C")
UNGRADED_AS = "C"

DESCRIPTION_CUT = 80
REMARK_CUT = 80
TICKET_PATH = "/tickets/{id}"
IMPROVEMENT_PATH = "/tickets/improvements/{id}"
# How an improvement alert's payload carries its dates (S074 § 5.3): text, as JSON has no date
PAYLOAD_DATE = "%Y-%m-%d"
PAYLOAD_TIME = "%Y-%m-%d %H:%M:%S"

TEST_TITLE = "Yantra test"
TEST_BODY = "Notifications work on this device."
TEST_PATH = "/notifications"
TEST_TAG = "test"

# What a ticket change enqueues: an alert of ``kind``, and whether its escalation is queued too
Alert = namedtuple("Alert", "kind escalate")


def raise_alert(intensity, age):
    """§ 5.3: a breakdown alerts and escalates; a defect (degraded or initial) alerts quietly.
    A raise with *Already fixed* calls nothing (the caller's rule, S018 A1).  S028 § 4.6: a raise
    entered for a time more than MAX_BACKDATE_DAYS back (``age`` = now - occurred_at, a timedelta)
    is history, not news: nothing."""
    if age > timedelta(days=MAX_BACKDATE_DAYS):
        return None
    if intensity == BREAKDOWN_INTENSITY:
        return Alert(BREAKDOWN, True)
    return Alert(DEFECT, False)


def regrade_alert(state, new_intensity):
    """*Machine stopped*: a breakdown alert; it escalates only while still raised — once someone
    owns the ticket (acknowledged, scheduled, in progress) it does not (BR1-04).  Any other
    regrade sends nothing."""
    if new_intensity != BREAKDOWN_INTENSITY:
        return None
    return Alert(BREAKDOWN, state == RAISED)


def send_back_alert(machine_down):
    """*Down again*: the move's answer decides, not the event's intensity (BR2-01); no
    escalation, someone is already working on it (BR1-05)."""
    return Alert(BREAKDOWN, False) if machine_down else None


ASSIGNED_ALERT = Alert(ASSIGNED, False)


def close_alert(age):
    """S032 § 1.3: *Close* and *Not a fault* send *Ticket closed*, never escalated.  A close dated
    more than MAX_BACKDATE_DAYS back (``age`` = now - occurred_at) is back-entered history (S028),
    as for raise_alert: nothing."""
    if age > timedelta(days=MAX_BACKDATE_DAYS):
        return None
    return Alert(CLOSED, False)


def excluded_people(kind, actor_person_id, reported_by_id):
    """§ 5.2: the person whose action set the alert off is left out (the closer, for *ticket
    closed*, S032 § 5.2); for a breakdown or a defect the ticket's reported-by person too.  An
    escalation leaves nobody out."""
    if kind == ESCALATION:
        return []
    ids = {actor_person_id}
    if kind in (BREAKDOWN, DEFECT):
        ids.add(reported_by_id)
    return sorted(i for i in ids if i is not None)


def should_send(kind, state):
    return state in _SEND_STATES[kind]


def should_escalate(state, intensity, latest_critical_event_id, trigger_event_id):
    """§ 5.1: still raised, still critical, and the latest event that made it critical is the
    one that queued this escalation — so critical, down, critical again escalates once, from
    the last time (BR1-12)."""
    return state == RAISED and intensity == BREAKDOWN_INTENSITY and latest_critical_event_id == trigger_event_id


def escalation_minutes(component_grade, machine_grade, minutes_by_grade):
    """The minutes for the ticket's item: the component's own grade when it has one, else the
    machine's (decided 16-10-2026: a safety door graded A escalates first)."""
    grade = effective_criticality(component_grade, machine_grade) or UNGRADED_AS
    return minutes_by_grade[grade]


def first_name(name):
    words = (name or "").split()
    return words[0] if words else ""


def display_name(reported_by_name, raiser_team_name, raiser_login):
    """The name after "raised by" (BR2-11): the ticket's reported-by person, else the raiser's
    Team name, else the raiser's login — as a first name."""
    for name in (reported_by_name, raiser_team_name, raiser_login):
        if name and name.strip():
            return first_name(name)
    return ""


def _cut(text, limit):
    return text[:limit] if text else text


def ticket_facts(ticket, event, name, actor_name, base_url):
    """The one dict every alert text is built from (§ 5.1, BR2-11).  ``ticket``: id, serial,
    site_code, unit_code, machine_code, machine_name, component_code, intensity, state, symptom
    (the mode's label or None), description, occurred_at.  ``event``: the causing event's
    event, occurred_at, remark.  ``name``: display_name's; ``actor_name``: the first name of who
    made the causing event (the assigner, A1).  ``base_url``: the label link address, so S023's
    group message has a full link with no second read (BR3-02)."""
    path = TICKET_PATH.format(id=ticket["id"])
    return {
        "ticket_id": ticket["id"],
        "serial": ticket["serial"],
        "site_code": ticket["site_code"],
        "unit_code": ticket["unit_code"],
        "machine_code": ticket["machine_code"],
        "machine_name": ticket["machine_name"],
        "component_code": ticket["component_code"],
        "intensity": ticket["intensity"],
        "state": ticket["state"],
        "symptom": ticket["symptom"],
        "description": _cut(ticket["description"], DESCRIPTION_CUT),
        "occurred_at": ticket["occurred_at"],
        "name": name,
        "actor_name": actor_name,
        "event_type": event["event"],
        "event_at": event["occurred_at"],
        "event_remark": _cut(event["remark"], REMARK_CUT),
        "path": path,
        "url": f"{base_url}{path}",
    }


def alert_text(kind, facts, minutes=None):
    """-> ``(title, body)``, e.g. ("Breakdown · SMTW.MCC2 · VBM001",
    "TK-2026-10-012 · Not building pressure — raised by Ravi").  The body names the symptom,
    else the start of the description."""
    place = f"{facts['site_code']}.{facts['unit_code']} · {facts['machine_code']}"
    what = facts["symptom"] or facts["description"]
    lead = f"{facts['serial']} · {what}" if what else facts["serial"]
    raised_by = f"raised by {facts['name']}" if facts["name"] else "raised"
    if kind == ASSIGNED:
        title, tail = f"Assigned to you · {place}", f"by {facts['actor_name']}" if facts["actor_name"] else None
    elif kind == ESCALATION:
        title, tail = f"Not acknowledged after {minutes} min · {place}", raised_by
    elif kind == DEFECT:
        title, tail = f"Defect · {place}", raised_by
    elif facts["event_type"] == SENT_BACK_EVENT:
        title, tail = f"Down again · {place}", f"sent back at {facts['event_at'].strftime('%H:%M')}"
    else:
        title, tail = f"Breakdown · {place}", raised_by
    return title, f"{lead} — {tail}" if tail else lead


def is_quiet(kind):
    """A defect comes without sound and without escalation (user decision 2)."""
    return kind == DEFECT


def message(kind, facts, minutes=None):
    """The alert as a channel sends it: the text, the path the tap opens, a tag per ticket (the
    escalation replaces the breakdown's alert instead of stacking a second one), quiet or not."""
    title, body = alert_text(kind, facts, minutes)
    return {"title": title, "body": body, "path": facts["path"], "tag": f"ticket-{facts['ticket_id']}",
            "quiet": is_quiet(kind)}


def message_for_test():
    return {"title": TEST_TITLE, "body": TEST_BODY, "path": TEST_PATH, "tag": TEST_TAG, "quiet": False}


# ---------------------------------------------------------------------------
# Improvements (S074, R05.5; ISO 9001 § 10.2.1 c and d)
# ---------------------------------------------------------------------------

def given_alert(owner_id, actor_person_id, old_owner_id=None):
    """*Countermeasure for you* on an add (``old_owner_id`` None) or a change of owner (§ 5.1, D5):
    not when the owner gave it to themselves, nor when the owner did not change.  An actor with
    no Team record (admin) is None, so the owner is always told."""
    return owner_id != actor_person_id and owner_id != old_owner_id


def overdue_alert_due(action_state, due_date, alerted_for, improvement_state, today):
    """*Countermeasure overdue* is due (§ 5.1): the improvement's stored state is open, the
    countermeasure is open and past its due date, and this due date was not alerted yet.  ``!=``,
    not ``<``: a due date moved either way, and past, alerts again (BR1-01)."""
    return (improvement_state in IMPROVEMENT_OPEN_STATES and action_state == ACTION_OPEN and due_date < today
            and alerted_for != due_date)


def ready_alert_due(state, watch_from, watch_days, alerted_for, now):
    """*Ready to verify* is due (§ 5.1): the stored state is watching, the watch has ended, and
    this watch end was not alerted yet (once per watch end, BR1-01).  The stored state, never
    the display state ready_to_verify (S072 BR1-03)."""
    if state != WATCHING or watch_from is None:
        return False
    end = watch_until(watch_from, watch_days)
    return now >= end and alerted_for != end


def should_send_improvement(kind, improvement_state, watch_end, action, expected):
    """Is the queued alert still true when the task runs (§ 5.3's change table)?  ``action``: the
    countermeasure as it is now (``state``, ``owner_id``, ``due_date``), None for VERIFY_READY;
    ``watch_end``: watch_until of the row now, None before the watch; ``expected``: the payload's
    ``person_id``, ``due_date`` (a date) or ``watch_until`` (a datetime)."""
    if kind == VERIFY_READY:
        return improvement_state == WATCHING and watch_end is not None and watch_end == expected["watch_until"]
    if improvement_state not in IMPROVEMENT_OPEN_STATES or action["state"] != ACTION_OPEN:
        return False
    if kind == ACTION_GIVEN:
        return action["owner_id"] == expected["person_id"]
    return action["due_date"] == expected["due_date"]


def improvement_facts(improvement, action, giver_name, base_url):
    """The one dict every improvement alert text is built from (§ 5.4), as ticket_facts.
    ``improvement``: id, serial, title, site_code, unit_code, machine_code, watch_from,
    watch_days; ``action``: id, text, due_date, owner_name, or None; ``giver_name``: who gave the
    countermeasure (a first name, or None)."""
    path = IMPROVEMENT_PATH.format(id=improvement["id"])
    watch_from = improvement["watch_from"]
    return {
        "improvement_id": improvement["id"],
        "serial": improvement["serial"],
        "title": _cut(improvement["title"], DESCRIPTION_CUT),
        "site_code": improvement["site_code"],
        "unit_code": improvement["unit_code"],
        "machine_code": improvement["machine_code"],
        "action_id": action["id"] if action else None,
        "action_text": _cut(action["text"], DESCRIPTION_CUT) if action else None,
        "due_date": action["due_date"] if action else None,
        "owner_name": first_name(action["owner_name"]) if action else None,
        "giver_name": giver_name,
        "watch_until": watch_until(watch_from, improvement["watch_days"]) if watch_from else None,
        "path": path,
        "url": f"{base_url}{path}",
    }


def improvement_text(kind, facts):
    """-> ``(title, body)``, e.g. ("Countermeasure for you · SMTW.MCC2 · HP003",
    "IM-2026-10-001 · Clean the panel contactors — due 08-11-2026, from Ravi").  Dates DD-MM-YYYY."""
    place = f"{facts['site_code']}.{facts['unit_code']} · {facts['machine_code']}"
    if kind == VERIFY_READY:
        return (f"Ready to verify · {place}",
                f"{facts['serial']} · {facts['title']} — the watch ended on {facts['watch_until']:%d-%m-%Y}. "
                "Check if the fix worked.")
    lead = f"{facts['serial']} · {facts['action_text']}"
    due = f"{facts['due_date']:%d-%m-%Y}"
    if kind == ACTION_GIVEN:
        tail = f"due {due}, from {facts['giver_name']}" if facts["giver_name"] else f"due {due}"
        return f"Countermeasure for you · {place}", f"{lead} — {tail}"
    # The overdue body names the owner: the lead reads the same text
    return f"Countermeasure overdue · {place}", f"{lead} — was due {due}, owner {facts['owner_name']}"


def improvement_message(kind, facts):
    """The alert as a channel sends it (§ 5.4): quiet for all three (D7: planned work, no machine
    down), a tag per countermeasure (the overdue alert replaces the given one on the phone) or
    per improvement."""
    title, body = improvement_text(kind, facts)
    tag = (f"improvement-{facts['improvement_id']}" if kind == VERIFY_READY
           else f"improvement-action-{facts['action_id']}")
    return {"title": title, "body": body, "path": facts["path"], "tag": tag, "quiet": True}


def _what_line(role, place):
    """One membership's line, built from AUDIENCE so the page and the fan-out cannot disagree."""
    kinds = [label for kind, label in ((BREAKDOWN, "Breakdowns"), (DEFECT, "defects")) if role in AUDIENCE[kind]]
    if not kinds:
        return None
    what = " and ".join(kinds)
    what = what[0].upper() + what[1:]
    line = f"{what} at {place}"
    return f"{line}, escalations" if role in AUDIENCE[ESCALATION] else line


def you_get(memberships):
    """*What you will get* (BR2-06, A1) from the person's memberships: ``[{site_code, role,
    all_units, unit_codes}]``.  One line per membership whose role is in a push audience, e.g.
    "Breakdowns and defects at SMTW, escalations" (all units) or "Breakdowns at SMTW.MCC1,
    SMTW.MCC2", then "Improvements ready to verify at SMTW" when the role holds improvement:verify
    (S074), then "Closed tickets at SMTW, by email" when the role gets *ticket closed* (S032);
    then "Jobs assigned to you" once for an assignable role; then, once each, the countermeasure
    lines (S074 § 5.8) when a membership with a place holds improvement:read (the owner's alerts)
    or improvement:edit (who may lead gets the overdue alerts of the improvements they lead).
    The improvement lines follow config_rbac through compute_permissions.  Empty: nothing to get
    (IT admin, a storekeeper)."""
    lines = []
    keys_with_place = set()
    for membership in sorted(memberships, key=lambda m: m["site_code"]):
        if membership["all_units"]:
            place = membership["site_code"]
        else:
            place = ", ".join(f"{membership['site_code']}.{code}" for code in sorted(membership["unit_codes"]))
        if not place:
            continue
        keys = compute_permissions([membership["role"]])
        keys_with_place.update(keys)
        line = _what_line(membership["role"], place)
        if line:
            lines.append(line)
        if VERIFY_KEY in keys:
            lines.append(f"Improvements ready to verify at {place}")
        if membership["role"] in AUDIENCE[CLOSED]:
            lines.append(f"Closed tickets at {place}, by email")
    if any(m["role"] in ASSIGNABLE_ROLES for m in memberships):
        lines.append("Jobs assigned to you")
    if READ_KEY in keys_with_place:
        lines.append("Countermeasures given to you, and when they are overdue")
    if EDIT_KEY in keys_with_place:
        lines.append("Overdue countermeasures of improvements you lead")
    return lines
