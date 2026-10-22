"""Alerts — the thin shell around alerts_core (docs/steps/S021-alerts-push/1-brief.md § 3, § 5.2,
§ 5.3, § 10 A1).

Request side: tickets.py calls enqueue_alert inside the ticket's own transaction, after the
event that causes the alert is written, so the task rows commit or roll back with the ticket.
They are enqueued always, whether or not push is set up (§ 7 decision 10): the task finds the
channels, so the ticket path has no `if` for them, and every alert leaves its task_queue row.

Worker side: task_handlers reads the ticket's facts, the recipients and their devices through
the functions below.  Plain reads, except the escalation's ticket lock, which is the
handler's.
"""

from datetime import timedelta

from alerts_core import AUDIENCE, display_name, escalation_minutes, excluded_people, first_name, ticket_facts
from settings import escalation_minutes as escalation_settings, label_base_url
from task_queue import enqueue

TICKET_ALERT = "ticket_alert"
TICKET_ESCALATE = "ticket_escalate"
PUSH_SEND = "push_send"
# A send is internal and idempotent, so it may retry (base pattern); a push resent after a
# timeout shows twice at worst
PUSH_SEND_ATTEMPTS = 3


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


def recipients(cur, ticket, kind, exclude_person_ids):
    """§ 5.2: the active people with a membership at the ticket's site whose role is in the
    kind's audience (exactly), covering the ticket's unit (all units, or a person_units row),
    less the left-out ones -> their ids.  The join to push_subscriptions that follows already
    needs a login."""
    roles = AUDIENCE[kind]
    sql = ("SELECT p.id FROM people p JOIN memberships ms ON ms.person_id = p.id AND ms.site_id = %s"
           f" WHERE p.active = 1 AND ms.role IN ({', '.join(['%s'] * len(roles))})"
           " AND (ms.all_units = 1 OR EXISTS (SELECT 1 FROM person_units pu WHERE pu.person_id = p.id"
           " AND pu.unit_id = %s))")
    params = [ticket["site_id"], *roles, ticket["unit_id"]]
    if exclude_person_ids:
        sql += f" AND p.id NOT IN ({', '.join(['%s'] * len(exclude_person_ids))})"
        params.extend(exclude_person_ids)
    cur.execute(f"{sql} ORDER BY p.id", params)
    return [row["id"] for row in cur.fetchall()]


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

