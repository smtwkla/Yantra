"""Alerts — pure rules, the same for every channel (docs/steps/S021-alerts-push/1-brief.md § 1.4,
§ 5.1–5.3, § 10 A1; no DB, no clock, no Flask).  Push is the channel today (push_core); S023's
Telegram would read the same facts and texts.

An alert is a message about a ticket: a new breakdown, a new defect, *down again*, an
escalation of a breakdown nobody acknowledged in time, *assigned to you*, or (S032) *ticket
closed*.  It answers ISO 55001 § 7.4 / ISO 9001 § 7.4 (what is communicated, when, to whom and
how): the audience and channel tables below are that decision, and you_get shows each person
their part of it.
"""

from collections import namedtuple
from datetime import timedelta

from config_rbac import ASSIGNABLE_ROLES
from equipment_core import effective_criticality
from tickets_core import (
    BREAKDOWN_INTENSITY, CLOSED as CLOSED_STATE, DOWN_STATES, MAX_BACKDATE_DAYS, OPEN_STATES, RAISED, SENT_BACK_EVENT,
)

BREAKDOWN = "breakdown"
DEFECT = "defect"
ESCALATION = "escalation"
ASSIGNED = "assigned"      # A1: Job assigned to you
CLOSED = "closed"          # S032: Ticket closed, by email
KINDS = (BREAKDOWN, DEFECT, ESCALATION, ASSIGNED, CLOSED)

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
}

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
    SMTW.MCC2", followed by "Closed tickets at SMTW, by email" when the role gets *ticket closed*
    (S032); then "Jobs assigned to you" once for an assignable role.  Empty: nothing to get (a
    technician before A1, IT admin, a storekeeper)."""
    lines = []
    for membership in sorted(memberships, key=lambda m: m["site_code"]):
        if membership["all_units"]:
            place = membership["site_code"]
        else:
            place = ", ".join(f"{membership['site_code']}.{code}" for code in sorted(membership["unit_codes"]))
        if not place:
            continue
        line = _what_line(membership["role"], place)
        if line:
            lines.append(line)
        if membership["role"] in AUDIENCE[CLOSED]:
            lines.append(f"Closed tickets at {place}, by email")
    if any(m["role"] in ASSIGNABLE_ROLES for m in memberships):
        lines.append("Jobs assigned to you")
    return lines
