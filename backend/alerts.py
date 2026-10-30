"""Alerts — the thin shell around alerts_core (docs/steps/S021-alerts-push/1-brief.md § 3, § 5.2,
§ 5.3, § 10 A1; S032 § 5.1–5.5: *ticket closed* by email).

Request side: tickets.py calls enqueue_alert inside the ticket's own transaction, after the
event that causes the alert is written, so the task rows commit or roll back with the ticket.
They are enqueued always, whether or not push is set up (§ 7 decision 10): the task finds the
channels, so the ticket path has no `if` for them, and every alert leaves its task_queue row.

Worker side: task_handlers reads the ticket's facts, the recipients and their devices (or, for
email, their addresses and the closed ticket's facts) through the functions below.  Plain reads, except the escalation's ticket lock, which is the
handler's.

Improvements (S074, R05.5).  Request side: improvements.py's countermeasure add and change of
owner call enqueue_improvement_alert in the route's transaction (*Countermeasure for you*).
Worker side: the daily improvement_alert_scan finds the overdue countermeasures and the ended
watches, and improvement_alert sends one alert to the people who may open the improvement
(people_at_unit, the recipient query shared with the tickets).  The scan's locks, in the global
order (equipment.py: (6b) then (6c)): one plain read of the candidates (scan_candidates, only to
narrow the work), then per improvement in id order its row FOR UPDATE and its candidate
countermeasures FOR UPDATE in id order (lock_for_scan); the decision comes from the locked rows,
and the marker UPDATEs are on rows already held.  Several (6b) rows are held at once, always in
id order; every route holds at most one (6b) while it waits, so no cycle.  improvement_alert
reads plain, as ticket_alert.  This module never imports improvements.py (improvements.py
imports it, as tickets.py does).
"""

from datetime import timedelta

from access_core import roles_holding
from alerts_core import (
    ACTION_GIVEN, ACTION_OVERDUE, AUDIENCE, IMPROVEMENT_AUDIENCE_KEY, PAYLOAD_DATE, PAYLOAD_TIME, display_name,
    escalation_minutes, excluded_people, first_name, improvement_facts, ticket_facts,
)
from db_helpers import marks
from improvements_core import ACTION_OPEN, IMPROVEMENT_OPEN_STATES, WATCHING
from settings import escalation_minutes as escalation_settings, label_base_url
from task_queue import enqueue
from tickets_core import latest_restoration, ticket_times

TICKET_ALERT = "ticket_alert"
TICKET_ESCALATE = "ticket_escalate"
IMPROVEMENT_ALERT = "improvement_alert"
IMPROVEMENT_SCAN = "improvement_alert_scan"
PUSH_SEND = "push_send"
# A send is internal and idempotent, so it may retry (base pattern); a push resent after a
# timeout shows twice at worst
PUSH_SEND_ATTEMPTS = 3
EMAIL_SEND = "email_send"
# The same reasoning (S032 § 5.5): an email resent after a lost answer arrives twice at worst
EMAIL_SEND_ATTEMPTS = 3


# ---------------------------------------------------------------------------
# Request side — in the ticket's transaction
# ---------------------------------------------------------------------------

def enqueue_ticket_alert(cur, ticket_id, kind, event_id, exclude_person_ids, minutes=None, person_id=None):
    """One ticket_alert task (§ 5.1).  ``event_id`` is the event that caused it (the text says
    *Down again* and its time from it); ``minutes`` comes with an escalation, ``person_id`` (the
    assignee) with *assigned*."""
    payload = {"ticket_id": ticket_id, "kind": kind, "event_id": event_id,
               "exclude_person_ids": list(exclude_person_ids)}
    if minutes is not None:
        payload["minutes"] = minutes
    if person_id is not None:
        payload["person_id"] = person_id
    return enqueue(cur, TICKET_ALERT, payload)


def enqueue_escalation(cur, ticket_id, trigger_event_id, minutes, now):
    """The escalation check, due ``minutes`` after the breakdown was recorded in Yantra (``now``,
    IST, as the session's NOW()) — not after the typed event time (§ 7 decision 5)."""
    return enqueue(cur, TICKET_ESCALATE, {"ticket_id": ticket_id, "trigger_event_id": trigger_event_id,
                                          "minutes": minutes},
                   scheduled_for=now + timedelta(minutes=minutes))


def _item_grades(cur, ticket_id):
    """The machine's and the component's own criticality grades, read plain."""
    cur.execute("SELECT m.criticality AS machine_grade, c.criticality AS component_grade FROM tickets t"
                " JOIN equipment m ON m.id = t.equipment_id LEFT JOIN equipment c ON c.id = t.component_id"
                " WHERE t.id = %s", (ticket_id,))
    return cur.fetchone()


def enqueue_alert(cur, ticket_id, alert, event_id, actor_person_id, reported_by_id, now, person_id=None):
    """What a ticket change enqueues: ``alert`` is alerts_core's decision (an Alert, or None for
    nothing).  The left-out people follow § 5.2; an escalation is queued at the minutes for the
    item's grade, read now, so a setting changed later does not move it."""
    if alert is None:
        return
    enqueue_ticket_alert(cur, ticket_id, alert.kind, event_id,
                         excluded_people(alert.kind, actor_person_id, reported_by_id), person_id=person_id)
    if alert.escalate:
        grades = _item_grades(cur, ticket_id)
        minutes = escalation_minutes(grades["component_grade"], grades["machine_grade"], escalation_settings(cur))
        enqueue_escalation(cur, ticket_id, event_id, minutes, now)


def enqueue_improvement_alert(cur, kind, improvement_id, **fields):
    """One improvement_alert task (S074 § 5.3), in the caller's transaction (the route's or the
    scan's), so it commits or rolls back with the change that caused it.  ``fields``: action_id,
    person_id and given_by (*Countermeasure for you*); action_id and due_date, a date
    (*overdue*); watch_until, a datetime (*ready to verify*).  The dates travel as text; the
    payload carries person ids and a login, never an address."""
    payload = {"kind": kind, "improvement_id": improvement_id, **fields}
    if "due_date" in payload:
        payload["due_date"] = payload["due_date"].strftime(PAYLOAD_DATE)
    if "watch_until" in payload:
        payload["watch_until"] = payload["watch_until"].strftime(PAYLOAD_TIME)
    return enqueue(cur, IMPROVEMENT_ALERT, payload)


def enqueue_email(cur, person_id, subject, body):
    """One email_send task (S032 § 5.5): the person's id, never the address, which the task reads
    when it sends (A.5.34: the queue keeps done rows 90 days; a corrected address is used)."""
    return enqueue(cur, EMAIL_SEND, {"person_id": person_id, "subject": subject, "body": body},
                   max_attempts=EMAIL_SEND_ATTEMPTS)


# ---------------------------------------------------------------------------
# Worker side
# ---------------------------------------------------------------------------

_ALERT_TICKET = (
    "SELECT t.id, t.serial, t.state, t.intensity, t.description, t.occurred_at, t.created_by, t.unit_id,"
    " u.code AS unit_code, s.id AS site_id, s.code AS site_code, m.code AS machine_code, m.name AS machine_name,"
    " c.code AS component_code, f.label AS symptom, rp.name AS reported_by_name, rc.name AS raiser_name"
    " FROM tickets t JOIN units u ON u.id = t.unit_id JOIN sites s ON s.id = u.site_id"
    " JOIN equipment m ON m.id = t.equipment_id LEFT JOIN equipment c ON c.id = t.component_id"
    " LEFT JOIN failure_modes f ON f.id = t.failure_mode_id LEFT JOIN people rp ON rp.id = t.reported_by_id"
    " LEFT JOIN people rc ON rc.username = t.created_by"
    " WHERE t.id = %s"
)


def read_alert_ticket(cur, ticket_id, event_id):
    """The ticket, its unit, site and causing event, read once -> ``(row, ticket_facts)``, or None
    when the ticket or the event (of that ticket) does not exist."""
    cur.execute(_ALERT_TICKET, (ticket_id,))
    row = cur.fetchone()
    if row is None:
        return None
    cur.execute("SELECT e.event, e.occurred_at, e.remark, e.created_by, ap.name AS actor_name FROM ticket_events e"
                " LEFT JOIN people ap ON ap.username = e.created_by WHERE e.id = %s AND e.ticket_id = %s",
                (event_id, ticket_id))
    event = cur.fetchone()
    if event is None:
        return None
    name = display_name(row["reported_by_name"], row["raiser_name"], row["created_by"])
    actor = first_name(event["actor_name"] or event["created_by"])
    return row, ticket_facts(row, event, name, actor, label_base_url(cur))


def people_at_unit(cur, site_id, unit_ids, roles, only_ids=None, exclude_ids=(), with_email=False):
    """The recipient query every alert shares (S074 D1, § 5.6): the active people with a membership
    at ``site_id`` whose role is in ``roles``, covering one of ``unit_ids`` (all units of the
    site, or a person_units row), only among ``only_ids`` when given, less ``exclude_ids`` -> their
    ids in id order.  The join to push_subscriptions that follows already needs a login;
    ``with_email`` keeps only those with an address (S032 § 5.2)."""
    if not roles or not unit_ids or (only_ids is not None and not only_ids):
        return []
    sql = ("SELECT p.id FROM people p JOIN memberships ms ON ms.person_id = p.id AND ms.site_id = %s"
           f" WHERE p.active = 1 AND ms.role IN ({marks(roles)})"
           " AND (ms.all_units = 1 OR EXISTS (SELECT 1 FROM person_units pu WHERE pu.person_id = p.id"
           f" AND pu.unit_id IN ({marks(unit_ids)})))")
    params = [site_id, *roles, *unit_ids]
    if with_email:
        sql += " AND p.email IS NOT NULL"
    if only_ids is not None:
        sql += f" AND p.id IN ({marks(only_ids)})"
        params.extend(only_ids)
    if exclude_ids:
        sql += f" AND p.id NOT IN ({marks(exclude_ids)})"
        params.extend(exclude_ids)
    cur.execute(f"{sql} ORDER BY p.id", params)
    return [row["id"] for row in cur.fetchall()]


def recipients(cur, ticket, kind, exclude_person_ids, with_email=False):
    """§ 5.2: the people at the ticket's site whose role is in the kind's audience (exactly),
    covering the ticket's unit, less the left-out ones -> their ids (people_at_unit)."""
    return people_at_unit(cur, ticket["site_id"], [ticket["unit_id"]], AUDIENCE[kind],
                          exclude_ids=exclude_person_ids, with_email=with_email)


def recipients_with_email(cur, ticket, kind, exclude_person_ids):
    """The email channel's recipients (S032 § 5.1): recipients() with an address."""
    return recipients(cur, ticket, kind, exclude_person_ids, with_email=True)


def assignee(cur, ticket_id, person_id, exclude_person_ids):
    """A1: the one assigned person, while still assigned and active and not the actor -> [id] or []."""
    if person_id in exclude_person_ids:
        return []
    cur.execute("SELECT p.id FROM ticket_assignees a JOIN people p ON p.id = a.person_id"
                " WHERE a.ticket_id = %s AND a.person_id = %s AND p.active = 1", (ticket_id, person_id))
    return [row["id"] for row in cur.fetchall()]


def subscription_ids(cur, person_ids):
    """Every device of these people, in id order."""
    if not person_ids:
        return []
    cur.execute(f"SELECT id FROM push_subscriptions WHERE person_id IN ({', '.join(['%s'] * len(person_ids))})"
                " ORDER BY id", list(person_ids))
    return [row["id"] for row in cur.fetchall()]


def latest_critical_event_id(cur, ticket_id):
    """The latest event that made the ticket critical (BR1-12): raised, regraded or sent_back with
    intensity critical, latest by id — the order they were recorded, whatever time was typed."""
    cur.execute("SELECT id FROM ticket_events WHERE ticket_id = %s AND intensity = 'critical'"
                " ORDER BY id DESC LIMIT 1", (ticket_id,))
    row = cur.fetchone()
    return row["id"] if row else None


def person_memberships(cur, person_id):
    """The person's memberships as alerts_core.you_get reads them: ``[{site_code, role,
    all_units, unit_codes}]`` (active units only)."""
    cur.execute("SELECT ms.site_id, s.code AS site_code, ms.role, ms.all_units FROM memberships ms"
                " JOIN sites s ON s.id = ms.site_id WHERE ms.person_id = %s ORDER BY s.code", (person_id,))
    memberships = [{"site_id": row["site_id"], "site_code": row["site_code"], "role": row["role"],
                    "all_units": bool(row["all_units"]), "unit_codes": []} for row in cur.fetchall()]
    if memberships:
        by_site = {m["site_id"]: m for m in memberships}
        cur.execute("SELECT u.site_id, u.code FROM person_units pu JOIN units u ON u.id = pu.unit_id"
                    " WHERE pu.person_id = %s AND u.active = 1 ORDER BY u.code", (person_id,))
        for row in cur.fetchall():
            if row["site_id"] in by_site:
                by_site[row["site_id"]]["unit_codes"].append(row["code"])
    return memberships



def read_closed_facts(cur, ticket_id, event_id):
    """The facts of the closed-ticket email (S032 § 5.3), read plain -> the dict
    email_core.closed_email takes, or None when the ticket or the event does not exist.

    The times come from tickets_core.ticket_times, the function the ticket page uses, so the
    figures match the page.  A closed ticket's figures end at its close, so the closing event's
    time stands for "now".  Every parts line is read; closed_email shows the first ten."""
    found = read_alert_ticket(cur, ticket_id, event_id)
    if found is None:
        return None
    ticket, facts = found
    cur.execute("SELECT c.name AS component_name, t.not_a_fault, fc.label AS cause, ma.label AS action"
                " FROM tickets t LEFT JOIN equipment c ON c.id = t.component_id"
                " LEFT JOIN failure_causes fc ON fc.id = t.cause_id LEFT JOIN maintenance_actions ma ON ma.id = t.action_id"
                " WHERE t.id = %s", (ticket_id,))
    extra = cur.fetchone()
    cur.execute("SELECT id, event, occurred_at, intensity, remark, waiting_reason, machine_stopped FROM ticket_events"
                " WHERE ticket_id = %s ORDER BY occurred_at, id", (ticket_id,))
    events = cur.fetchall()
    closing = next(e for e in events if e["id"] == event_id)
    cur.execute("SELECT COALESCE(SUM(minutes), 0) AS minutes, COUNT(DISTINCT person_id) AS people FROM ticket_labour"
                " WHERE ticket_id = %s", (ticket_id,))
    labour = cur.fetchone()
    cur.execute("SELECT description, quantity, qty_unit FROM ticket_parts WHERE ticket_id = %s ORDER BY id",
                (ticket_id,))
    parts = list(cur.fetchall())
    not_a_fault = bool(extra["not_a_fault"])
    return {
        "serial": ticket["serial"], "site_code": ticket["site_code"], "unit_code": ticket["unit_code"],
        "machine_code": ticket["machine_code"], "machine_name": ticket["machine_name"],
        "component_code": ticket["component_code"], "component_name": extra["component_name"],
        "intensity": ticket["intensity"], "not_a_fault": not_a_fault, "symptom": ticket["symptom"],
        "description": ticket["description"], "raised_at": ticket["occurred_at"], "raised_by": facts["name"],
        "back_in_service_at": latest_restoration(ticket["state"], not_a_fault, events),
        "times": ticket_times(events, closing["occurred_at"]),
        "cause": extra["cause"], "action": extra["action"],
        "labour_minutes": int(labour["minutes"]), "labour_people": labour["people"], "parts": parts,
        "closed_at": closing["occurred_at"], "closed_by": facts["actor_name"], "remark": closing["remark"],
        "url": facts["url"],
    }


# ---------------------------------------------------------------------------
# Improvements (S074) — worker side
# ---------------------------------------------------------------------------

_ALERT_IMPROVEMENT = (
    "SELECT i.id, i.serial, i.title, i.state, i.watch_from, i.watch_days, i.lead_id, i.unit_id,"
    " u.code AS unit_code, s.id AS site_id, s.code AS site_code, m.code AS machine_code,"
    " m.unit_id AS machine_unit_id"
    " FROM improvements i JOIN units u ON u.id = i.unit_id JOIN sites s ON s.id = u.site_id"
    " JOIN equipment m ON m.id = i.equipment_id WHERE i.id = %s"
)
_ALERT_ACTION = (
    "SELECT a.id, a.text, a.state, a.owner_id, a.due_date, p.name AS owner_name FROM improvement_actions a"
    " JOIN people p ON p.id = a.owner_id WHERE a.id = %s AND a.improvement_id = %s"
)


def read_alert_improvement(cur, improvement_id, action_id=None, given_by=None):
    """The improvement, its site, unit and machine, and its countermeasure when ``action_id`` is
    given, read plain -> ``(row, action, improvement_facts)``; None when the improvement, or the
    countermeasure of that improvement, does not exist.  ``given_by``: the login that gave the
    countermeasure; the text names that person's first name, else the login."""
    cur.execute(_ALERT_IMPROVEMENT, (improvement_id,))
    row = cur.fetchone()
    if row is None:
        return None
    action = None
    if action_id is not None:
        cur.execute(_ALERT_ACTION, (action_id, improvement_id))
        action = cur.fetchone()
        if action is None:
            return None
    giver = None
    if given_by:
        cur.execute("SELECT name FROM people WHERE username = %s", (given_by,))
        person = cur.fetchone()
        giver = first_name(person["name"] if person else given_by)
    return row, action, improvement_facts(row, action, giver, label_base_url(cur))


def improvement_recipients(cur, kind, row, action):
    """S074 § 5.6: the holders of the kind's key (IMPROVEMENT_AUDIENCE_KEY) at the improvement's
    site covering one of the two units S067's access predicate accepts (the improvement's own and
    its machine's current one, improvements._visible_condition), so a recipient can open what the
    alert names.  *For you*: only the countermeasure's owner; *overdue*: only the owner and the
    lead (one person once); *ready to verify*: every holder.  Nobody is left out as the actor:
    the scan has none, and the given alert's actor was left out when it was queued."""
    if kind == ACTION_GIVEN:
        only = [action["owner_id"]]
    elif kind == ACTION_OVERDUE:
        only = sorted({action["owner_id"], row["lead_id"]})
    else:
        only = None
    units = sorted({row["unit_id"], row["machine_unit_id"]})
    return people_at_unit(cur, row["site_id"], units, roles_holding(IMPROVEMENT_AUDIENCE_KEY[kind]), only_ids=only)


def scan_candidates(cur, today, now):
    """The scan's one plain read per table (S074 § 5.2): the open countermeasures past their due
    date and not alerted for it, of open improvements, and the watching improvements whose watch
    has ended and was not alerted for that end -> ``{improvement_id: [action ids]}`` in id order
    (an improvement only ready has no action ids).  It only narrows the work: the decision comes
    from the locked rows."""
    states = list(IMPROVEMENT_OPEN_STATES)
    cur.execute("SELECT a.id, a.improvement_id FROM improvement_actions a JOIN improvements i ON i.id = a.improvement_id"
                " WHERE a.state = %s AND a.due_date < %s"
                " AND (a.overdue_alert_for IS NULL OR a.overdue_alert_for <> a.due_date)"
                f" AND i.state IN ({marks(states)}) ORDER BY a.improvement_id, a.id",
                (ACTION_OPEN, today, *states))
    candidates = {}
    for row in cur.fetchall():
        candidates.setdefault(row["improvement_id"], []).append(row["id"])
    cur.execute("SELECT id FROM improvements WHERE state = %s AND watch_from IS NOT NULL"
                " AND watch_from + INTERVAL watch_days DAY <= %s"
                " AND (ready_alert_for IS NULL OR ready_alert_for <> watch_from + INTERVAL watch_days DAY)",
                (WATCHING, now))
    for row in cur.fetchall():
        candidates.setdefault(row["id"], [])
    return dict(sorted(candidates.items()))


def lock_for_scan(cur, improvement_id, action_ids):
    """(6b) the improvement FOR UPDATE, then (6c) each candidate countermeasure FOR UPDATE in id
    order, one row per statement (equipment.py's rule) -> ``(improvement, [actions])``; the
    improvement None when it is gone (never: nothing is deleted), a gone countermeasure left
    out."""
    cur.execute("SELECT id, state, watch_from, watch_days, ready_alert_for, lead_id FROM improvements"
                " WHERE id = %s FOR UPDATE", (improvement_id,))
    improvement = cur.fetchone()
    if improvement is None:
        return None, []
    actions = []
    for action_id in sorted(action_ids):
        cur.execute("SELECT id, state, due_date, overdue_alert_for, owner_id FROM improvement_actions"
                    " WHERE id = %s AND improvement_id = %s FOR UPDATE", (action_id, improvement_id))
        action = cur.fetchone()
        if action is not None:
            actions.append(action)
    return improvement, actions


def mark_overdue_alerted(cur, action_id, due_date):
    """The overdue alert was queued for this due date (v40).  No updated_*: an alert is not a
    change of the record.  The row is held (6c)."""
    cur.execute("UPDATE improvement_actions SET overdue_alert_for = %s WHERE id = %s", (due_date, action_id))


def mark_ready_alerted(cur, improvement_id, watch_end):
    """The ready alert was queued for this watch end (v40); no updated_*.  The row is held (6b)."""
    cur.execute("UPDATE improvements SET ready_alert_for = %s WHERE id = %s", (watch_end, improvement_id))
