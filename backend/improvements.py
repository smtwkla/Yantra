"""Improvements — the record where the team analyses one problem that tickets showed, so it does
not happen again (TPM focused improvement; docs/steps/S067-improvement-record/1-brief.md).  This
step: start one from a ticket, its detail, edit, add and remove tickets, the list and the lead
choices.  The screens are S068's.  S069 adds the analysis: the why-why chain (improvement_whys)
and the root cause with the contributing causes (columns of improvements).  S070 adds the
countermeasures (improvement_actions; ISO 9001 § 10.2.1 c): add, change, cancel, mark done, the
user's own open ones, the owner choices, and the documents store's fourth owner (read_action and
its lock functions, imported by documents.py).  Who marks one done is decided by data: its owner,
or an improvement:edit holder at the site (as Plan § 3's pm_job:work); no new key.  S072 adds the
working states (analysing → actions open → watching, moved by _settle_state from the data, D2),
Ready to verify computed from the clock (D1), the watch and its figures, notes, the verified close
(effective; not effective, which starts a follow-up), the drop, and the timeline
(improvement_events): EVERY write of this module writes its line in the same transaction as the
change, after it, under (6b) (D8).  A closed or dropped improvement is read-only (409).

Thin shell: improvements_core holds the rules (the states, the fields, start, link and remove,
who may lead, the loss); this module checks access, locks, reads the rows the rules need and
stores the result.  The linked tickets are never written: closed is final (Plan § 4.2); their
symptom, cause and downtime are read from the tickets, never copied (ISO 14224, EN 13306).

ACCESS (§ 5.7) — the predicate mirrors the tickets' (equipment.unit_access_condition): an
improvement is visible when its unit, or its machine's current unit, is among the units where
the user holds improvement:read.  Outside it: 404.  "The improvement's site" is its unit's site,
fixed: the unit is the first ticket's, and a ticket's unit never changes.  Every write checks
improvement:edit at that site after the 404 (403); a start checks it at the ticket's site.  The
linked tickets go in full to every reader of the improvement (D8).

LOCK ORDER (equipment.py's numbers; § 5.4).  The database runs REPEATABLE READ: a locking read
sees the newest committed row, a plain read the snapshot of the transaction's first plain read.
Every decision below comes from a locking read, or from a plain read made after the lock that
guards it is held.
- Start: (6) the serial counter (scope IM:YYYY-MM; only starts take IM rows, so two starts
  serialise here, and its SELECT is the transaction's first plain read) → (7) the ticket row
  LOCK IN SHARE MODE (state, not_a_fault: the start rule is decided from it; a send-back holds
  the ticket FOR UPDATE, so the two serialise) → plain reads (the ticket predicate 404, the key
  403, the open links 409, the lead 400) → the improvements insert (shared FK locks on the unit,
  the machine and the lead's person) → the improvement_tickets insert.  A refused start rolls
  back, the counter bump included, so no number is lost.
- Add ticket: (6b) the improvement row FOR UPDATE → (7) the ticket row LOCK IN SHARE MODE → plain
  reads (the transaction's first) → the link insert.
- Remove ticket: (6b) FOR UPDATE → plain reads (the links and their tickets' machine) → delete
  the link row.  The links read is safe: every link write takes (6b) first.  A ticket's
  equipment_id changes only through the ticket edit, which changes the component, never the
  machine.
- Edit: (6b) FOR UPDATE → plain reads (the lead only when it changes) → the update (a new lead
  takes a shared lock on that person).
- Add, edit, remove a why (S069 § 5.4): (6b) FOR UPDATE → plain reads (the transaction's first:
  the predicate 404, the key 403, the open state 409, the why 404, the whys by position) → the
  insert, update or delete, then the position updates the core returned.  Why rows are never
  locked on their own: every write of improvement_whys takes (6b) first, so two writers never
  interleave and the positions stay 1..n.
- Set root cause (S069): (6b) FOR UPDATE → plain reads (the cause's active flag only when the
  cause changes) → the update; a new root_cause_id takes a shared lock on that failure_causes
  row through the foreign key.  That is the one new edge: (6b) → a failure cause, shared.
- Countermeasures (S070 § 5.6).  Add: (6b) FOR UPDATE → plain reads (the transaction's first:
  the predicate 404, the key 403, the open state 409, the count 409, the owner 400, the problem's
  time and the due date 400) → the insert (shared FK locks on the improvement, held, and the
  owner's people row).  Change, mark done, cancel: (6b) FOR UPDATE → (6c) the countermeasure row
  FOR UPDATE (_lock_action; 404) → plain reads (the predicate 404, the key or the owner rule 403,
  the open state 409, the countermeasure's state from (6c) 409, then the owner, the due date or
  the done time 400) → the update (a new owner takes a shared lock on that person).  The
  problem's time (the earliest linked ticket) is read under (6b), so the links cannot change.
- A countermeasure's document (documents.py, its one owner lock): a plain read of the row's
  improvement_id (it never changes; 404) → (6b) FOR UPDATE → (6c) FOR UPDATE → plain reads (the
  predicate 404, the right 403, the open state and not cancelled 409, from the locked rows) →
  the equipment_documents statement (an insert share-locks the countermeasure, held).
- S072: every route above adds, at its end and still under its locks, its timeline line and,
  for the root cause and the countermeasure add, change, done and cancel, _settle_state (a plain
  read of the countermeasures' kind, state and done_at, safe because every countermeasure write
  takes (6b) first, then an UPDATE of the held improvement row).  Event rows are only inserted,
  never locked or updated; an insert takes shared foreign-key locks on the improvement (held),
  on the ticket when ticket_id is set ((7) shared, after (6b): Remove ticket gains the edge Add
  ticket already had) and on the countermeasure when action_id is set (held (6c), or inserted
  in the same transaction).  The edit also refuses a closed improvement now.
- Add note (S072): (6b) FOR UPDATE → plain reads (the predicate 404, improvement:note at the
  site 403, open 409) → the note line.
- Close as effective (S072): (6b) FOR UPDATE → plain reads (the predicate 404,
  improvement:verify at the site 403, close_error from the locked row and the clock 409) → the
  row closed (no updated_*) → its links' open_link NULL (S067 D4) → the line.
- Not effective (S072): (6) the serial counter, IM:YYYY-MM, before (6b) as the global order
  says, its SELECT the first plain read → (6b) the old improvement FOR UPDATE → plain reads (404,
  403, close_error 409, from the locked row) → the old links by a locking read (FOR UPDATE: the
  counter's SELECT fixed the snapshot, so a plain read would miss a link written while the route
  waited for (6b); every link write takes (6b) first, and _close updates these same rows, so no
  new edge) → the old row closed, its links' open_link NULL, its line →
  the follow-up's insert (shared FK locks on the unit, the machine, the lead and the old
  improvement, held) → one link per old ticket ((7) shared each; the old links freed
  uq_improvement_tickets_open in this transaction) → the follow-up's lines.  A refusal rolls
  back, the counter bump included.
- Drop (S072): (6b) FOR UPDATE → plain reads (404, improvement:edit 403, open 409) → the open
  countermeasures (6c) FOR UPDATE in one statement by id order, each cancelled with its line →
  the row dropped, its links' open_link NULL, the line.
- The alerts (S074): the countermeasure add and change of owner queue *Countermeasure for you*
  under their locks above (a task_queue insert: no foreign key, no new lock).  The daily scan
  (task_handlers.improvement_alert_scan, alerts.lock_for_scan) runs in the worker: one plain read
  of the candidates, then per improvement in id order (6b) FOR UPDATE and its candidate
  countermeasures (6c) FOR UPDATE in id order, deciding from the locked rows; it updates only
  rows it holds (the markers overdue_alert_for and ready_alert_for, no updated_*) and inserts
  only into task_queue.  It holds several (6b) rows at once, always in id order; every route
  here holds at most one (6b) while it waits (Not effective inserts a new improvement row, which
  takes no lock on a row the scan holds), so no cycle.  A deadlock all the same (1213) rolls the
  scan back and the queue retries it.
- Reads (list, detail, leads, mine, owners; the ticket detail in tickets.py): plain, no lock.
  S075: the detail reads each countermeasure's lesson (procedures) and its machine's current unit
  plainly; lesson_source is one plain read.  No route here locks or writes a procedures row.
  procedures.py links a lesson by taking a countermeasure (6c) LOCK IN SHARE MODE after its own
  (6) or (6d), never (6b) and never exclusive; every writer here takes (6b) then (6c) exclusive
  and never waits on a procedures row or the OPL counter, so no cycle (procedures.py LOCK ORDER).
One open link per ticket is race-free: two writers linking one ticket both hold its shared
lock, may both pass the plain check, and then meet on uq_improvement_tickets_open; the second
insert waits for the first transaction and fails with a duplicate key (UNIQUE_KEY_ERRORS: 409).
No new deadlock cycle:
- ticket writes (tickets.py) lock (7) FOR UPDATE and then take only shared locks on the unit,
  the machine and the component, never an improvement row.  A start or an add holds only a
  shared ticket lock while it waits for anything, so either it waits for the ticket write or
  the ticket write waits for it, never both.  A unit edit holds the unit FOR UPDATE and counts
  its tickets LOCK IN SHARE MODE (shared with shared: it does not wait for a start); a scrap
  holds the machine FOR UPDATE and counts open tickets with a plain read (no ticket lock); a
  raise of a repeat holds the machine (1) and takes the earlier ticket shared (shared with
  shared);
- accepted, as tickets.py's "a person's site-row edit against a raise naming that person": a
  person's site-row edit (masters.py: the person FOR UPDATE, then memberships, person_units,
  units) against a start naming that person as lead (the ticket, then the unit's and the
  person's shared FK locks).  InnoDB rolls one side back (1213), a rare JSON 500, and a retry
  gives the right answer;
- (6) only starts take IM: rows; a ticket raise takes its own TK: row;
- (6b) → (7): an add takes the improvement, then the ticket.  Nothing takes a ticket and then
  an improvement row: ticket writes never touch improvements, and a start inserts its own new
  row;
- (6b) → a failure cause, shared (S069): the one path that holds a cause exclusive and then
  waits on improvements is the code change in masters.py (the cause FOR UPDATE, then its
  improvements counted LOCK IN SHARE MODE).  It waits only on rows whose committed root_cause_id
  is that cause.  A root-cause write waits for a cause's shared lock only when it changes its
  root_cause_id to that cause (InnoDB checks a foreign key only when the column changes), and
  its row's committed entry then names the old cause: the code change of cause C never waits
  on a writer that waits for C.  A write that keeps its cause takes no cause lock.  No route
  here locks a ticket, and no masters write locks an improvement or a why;
- (6b) → (6c) (S070): every countermeasure writer takes its improvement first; nothing takes a
  countermeasure and then an improvement (the documents path reads improvement_id with a plain
  read before (6b)).  (6c) → equipment_documents rows: nothing else locks those.  No route here
  takes a ticket lock with a countermeasure.  An add or a change of owner share-locks only the
  improvement (held) and the owner's people row, never a unit; masters.py's person edit (person
  → memberships → person_units → units) never waits on an improvement or a countermeasure row,
  so it makes no cycle.  S069's cause freeze locks no countermeasure.
- S072 adds no lock level.  (6) → (6b) on Not effective: nothing holds an improvement row and
  then takes a counter (a start holds (6) and takes (7) shared and its own new row only); two
  Not effective on one improvement serialise on (6) in the same month, else on (6b), and the
  second finds it closed.  (6b) → (7) shared: as Add ticket; ticket writes never touch
  improvement rows.  (6b) → (6c): the drop takes its countermeasures by id order, every other
  writer takes one after (6b), so no two paths hold (6c) rows in opposite orders.  The
  follow-up's insert takes the unit's and the lead's shared FK locks, as a start: the same
  accepted deadlock with a person's site-row edit (1213, a rare JSON 500, a retry).  No route of
  S072 changes root_cause_id, so S069's cause freeze is untouched.
The cause freeze is race-free as the tickets' (tickets.py LOCK ORDER): a root-cause write that
holds the cause's shared lock commits before the code change gets its exclusive lock, and the
count sees it; a later one waits behind the cause's lock and then sees the new code, which is
allowed (the code changed before its first use).

Import direction: this module imports read_ticket, improvement_links, person_at_site and
people_at_site from tickets.py; tickets.py never imports this module (only improvements_core).
It imports alerts (S074), as tickets.py does; alerts never imports this module.  procedures.py
(S075) imports lesson_source from this module; this module never imports procedures.py: it reads
the procedures table by SQL only (each countermeasure's lesson, plain) and the rule of *Write
lesson* from procedures_core.
"""

from datetime import datetime, timedelta

from flask import Blueprint, jsonify

from alerts import enqueue_improvement_alert
from alerts_core import ACTION_GIVEN, given_alert
from api_common import (
    DEFAULT_PER_PAGE, MAX_PAGE, MAX_PER_PAGE, UNIQUE_KEY_ERRORS, ApiError, actor, clean_body, enum_arg, int_arg,
)
from auth_utils import current_person_id, has_perm_at, permissions_at_site, require_perm, require_perm_at
from db_helpers import count, marks, get_db, insert_row, next_counter, row_to_dict, transaction, update_row
from equipment import IST, NODE_JOINS, accessible_unit_ids, unit_access_condition
from improvements_core import (
    ACTION_ADDED, ACTION_CANCELLED, ACTION_CANCELLED_EVENT, ACTION_CHANGED, ACTION_DONE, ACTION_DONE_EVENT,
    ACTION_EDIT_LABELS, ACTION_KIND_LABELS, ACTION_OPEN, ACTIONS_FULL, ACTIONS_MAX, ALREADY_OPEN_RACE, CAUSE_ACTIVE,
    CLOSED_EFFECTIVE, CLOSED_NOT_EFFECTIVE, DROPPED, EDIT_KEY, EDIT_LABELS, EDITED, IMPROVEMENT_CLOSED,
    IMPROVEMENT_OPEN_STATES, LEAD_AT_SITE, NOT_A_FAULT, NOTE, NOTE_KEY, OWNER_AT_SITE, OWNER_OR_EDITOR, READ_KEY,
    READY_TO_VERIFY, ROOT_CAUSE_CHANGED, ROOT_CAUSE_SET, SERIAL_PREFIX, STARTED, STATE_CHANGED, TICKET_FROM_LIST,
    TICKET_LINKED, TICKET_OTHER_SITE, TICKET_REMOVED, VERIFY_KEY, WATCHING, WHY_ADDED, WHY_CHANGED, WHY_REMOVED,
    WHYS_FULL, WHYS_MAX, action_counts, action_flags, action_line, action_state_error, close_error, display_state,
    done_time_error, dropped_reason, due_date_error, is_open, link_error, loss, may_lead, overdue_days,
    position_error, removal_error, renumber, reorder, root_cause_line, start_error, validate_action,
    validate_cancel, validate_close, validate_done, validate_improvement, validate_link, validate_note,
    validate_root_cause, validate_why, watch_days_text, watch_figures, watch_start, watch_until, why_line,
    with_watch_ended, working_state,
)
from procedures_core import EDIT_KEY as LESSON_EDIT_KEY, may_write_lesson
from tickets import code_ref, improvement_links, people_at_site, person_at_site, read_ticket
from tickets_core import edit_lines, format_serial, is_breakdown, serial_scope, ticket_times

improvements_bp = Blueprint("improvements", __name__)

UNIQUE_KEY_ERRORS.update({
    "uq_improvement_tickets_open": ("ticket_id", ALREADY_OPEN_RACE),
})

STATE_FILTERS = ("open", "closed")

_IMPROVEMENT_FROM = (
    " FROM improvements i"
    " JOIN equipment m ON m.id = i.equipment_id"
    " JOIN units u ON u.id = i.unit_id"
    " JOIN sites s ON s.id = u.site_id"
    " JOIN people l ON l.id = i.lead_id"
    " LEFT JOIN people cp ON cp.username = i.created_by"
    " LEFT JOIN failure_causes rc ON rc.id = i.root_cause_id"
    # S072: who closed it, and the improvement it follows and the one that followed it (at most
    # one each: uq_improvements_follow_up), so the joins never add a row
    " LEFT JOIN people clp ON clp.username = i.closed_by"
    " LEFT JOIN improvements fo ON fo.id = i.follow_up_of_id"
    " LEFT JOIN improvements fu ON fu.follow_up_of_id = i.id"
)
# The list builds its items field by field, so the root-cause and close columns add nothing to
# it (S069 § 6); it reads watch_from and watch_days for the display state (S072 § 5.2)
_IMPROVEMENT_COLUMNS = (
    "SELECT i.id, i.serial, i.state, i.title, i.problem, i.created_at, i.created_by, i.updated_at, i.updated_by,"
    " i.unit_id, u.code AS unit_code, s.id AS site_id, s.code AS site_code,"
    " m.id AS m_id, m.code AS m_code, m.name AS m_name,"
    " l.id AS lead_id, l.name AS lead_name, l.active AS lead_active, cp.name AS created_by_name,"
    " i.root_cause, i.contributing_causes, rc.id AS rc_id, rc.code AS rc_code, rc.label AS rc_label,"
    " rc.cause_group AS rc_group, rc.active AS rc_active,"
    " i.watch_days, i.watch_from, i.closed_at, i.closed_by, i.close_remark, clp.id AS closed_by_person_id,"
    " clp.name AS closed_by_name, fo.id AS fo_id, fo.serial AS fo_serial, fu.id AS fu_id, fu.serial AS fu_serial"
)

# (6b): the improvement's decision columns, and the values an edit compares with
_LOCK_IMPROVEMENT = ("SELECT id, serial, state, unit_id, equipment_id, title, problem, lead_id,"
                     " root_cause, root_cause_id, contributing_causes, watch_days, watch_from FROM improvements"
                     " WHERE id = %s FOR UPDATE")
# (7), shared: the start and add rules are decided from this row
_SHARE_TICKET = "SELECT id, state, not_a_fault, unit_id, equipment_id FROM tickets WHERE id = %s LOCK IN SHARE MODE"

_LINKED_TICKETS = (
    "SELECT it.improvement_id, t.id, t.serial, t.state, t.intensity, t.occurred_at, t.not_a_fault,"
    " m.id AS m_id, m.code AS m_code, m.name AS m_name, f.id AS f_id, f.code AS f_code, f.label AS f_label,"
    " fc.id AS fc_id, fc.code AS fc_code, fc.label AS fc_label"
    " FROM improvement_tickets it JOIN tickets t ON t.id = it.ticket_id"
    " JOIN equipment m ON m.id = t.equipment_id"
    " LEFT JOIN failure_modes f ON f.id = t.failure_mode_id"
    " LEFT JOIN failure_causes fc ON fc.id = t.cause_id"
)


def _now():
    """The IST wall clock, naive, as every DATETIME is stored (as tickets.py)."""
    return datetime.now(IST).replace(tzinfo=None)


def _today():
    """The IST date of now: the due date's range and *overdue* (S070 § 5.3, § 5.4)."""
    return _now().date()


def _stamp():
    """Now to the second: a timeline line's time and the close's (DATETIME has no fraction)."""
    return _now().replace(microsecond=0)


# ---------------------------------------------------------------------------
# The timeline and the working state (S072 § 5.1, § 5.6)
# ---------------------------------------------------------------------------

def _add_event(cur, improvement_id, event, occurred_at, from_state=None, to_state=None, ticket_id=None,
               action_id=None, remark=None, earlier=None):
    """Write one timeline line, in the write's transaction, after the change it records (D8;
    as tickets._add_event).  Event rows are only inserted, never locked or updated."""
    insert_row(cur, "improvement_events", {
        "improvement_id": improvement_id, "event": event, "occurred_at": occurred_at, "from_state": from_state,
        "to_state": to_state, "ticket_id": ticket_id, "action_id": action_id, "remark": remark, "earlier": earlier,
    }, actor())


def _names(cur, person_ids):
    """People's names for an edit line, in one plain read -> ``{id: name}``."""
    ids = sorted({person_id for person_id in person_ids if person_id is not None})
    if not ids:
        return {}
    cur.execute(f"SELECT id, name FROM people WHERE id IN ({marks(ids)})", ids)
    return {row["id"]: row["name"] for row in cur.fetchall()}


def _settle_state(cur, improvement_id, locked, root_cause_set):
    """Give the improvement the working state its data earns (§ 5.1, D2), under (6b), after the
    route's own write.  The countermeasures are a plain read: every countermeasure write takes
    (6b) first.  Writes state and watch_from with a plain UPDATE (no updated_*, D16) and a
    state_changed line when the state moves; an improvement that is not open is never settled."""
    if not is_open(locked["state"]):
        return
    cur.execute("SELECT kind, state, done_at FROM improvement_actions WHERE improvement_id = %s", (improvement_id,))
    actions = cur.fetchall()
    state = working_state(locked["state"], root_cause_set, actions)
    watch_from = watch_start(actions) if state == WATCHING else None
    if state == locked["state"] and watch_from == locked["watch_from"]:
        return
    cur.execute("UPDATE improvements SET state = %s, watch_from = %s WHERE id = %s", (state, watch_from, improvement_id))
    if state != locked["state"]:
        now = _stamp()
        _add_event(cur, improvement_id, STATE_CHANGED, now,
                   from_state=display_state(locked["state"], locked["watch_from"], locked["watch_days"], now),
                   to_state=state)


# ---------------------------------------------------------------------------
# Access and reads
# ---------------------------------------------------------------------------

def _visible_condition(cur):
    return unit_access_condition(cur, READ_KEY, "i.unit_id", "m.unit_id")


def _read_improvement(cur, improvement_id):
    """Plain read of one improvement through the access predicate; 404 when missing or not visible."""
    visible = _visible_condition(cur)
    if visible is not None:
        condition, params = visible
        cur.execute(f"{_IMPROVEMENT_COLUMNS}{_IMPROVEMENT_FROM} WHERE i.id = %s AND {condition}",
                    [improvement_id, *params])
        row = cur.fetchone()
        if row is not None:
            return row
    raise ApiError("Not found", 404)


def lesson_source(cur, action_id):
    """For procedures.py (S075 § 5.9): the countermeasure's improvement as ``{id, serial, title,
    equipment_id, machine_code, site_id}`` when the user may open it (this module's predicate),
    else None — a countermeasure that does not exist too.  One plain read; never raises, so a
    lesson's page shows no source line to a reader without improvement:read there, and a create
    turns None into its own 400."""
    visible = _visible_condition(cur)
    if visible is None:
        return None
    condition, params = visible
    cur.execute("SELECT i.id, i.serial, i.title, i.equipment_id, m.code AS machine_code, u.site_id"
                " FROM improvement_actions a JOIN improvements i ON i.id = a.improvement_id"
                " JOIN equipment m ON m.id = i.equipment_id JOIN units u ON u.id = i.unit_id"
                f" WHERE a.id = %s AND {condition}", [action_id, *params])
    return cur.fetchone()


def _check_improvement(cur, improvement_id):
    """A write's plain checks after its locks: the predicate (404), then improvement:edit at the
    improvement's site (403) -> the row."""
    row = _read_improvement(cur, improvement_id)
    require_perm_at(EDIT_KEY, row["site_id"])
    return row


def _lock_improvement(cur, improvement_id):
    """(6b) -> the locked row; 404 when there is none."""
    cur.execute(_LOCK_IMPROVEMENT, (improvement_id,))
    locked = cur.fetchone()
    if locked is None:
        raise ApiError("Not found", 404)
    return locked


def _require_open(locked):
    if not is_open(locked["state"]):
        raise ApiError(IMPROVEMENT_CLOSED, 409)


def _check_lead(cur, lead_id, site_id):
    """§ 5.6: an active person with a membership at the site whose role there may lead."""
    person = person_at_site(cur, lead_id, site_id)
    if person is None or not may_lead(person["role"]):
        raise ApiError(LEAD_AT_SITE, 400, "lead_id")


def _events_by_ticket(cur, ticket_ids):
    """The events ticket_times needs, of every ticket in one query, oldest first ->
    ``{ticket_id: [event, …]}``."""
    events = {ticket_id: [] for ticket_id in ticket_ids}
    if ticket_ids:
        cur.execute("SELECT ticket_id, event, occurred_at, intensity, waiting_reason, machine_stopped"
                    f" FROM ticket_events WHERE ticket_id IN ({marks(ticket_ids)}) ORDER BY occurred_at, id",
                    list(ticket_ids))
        for row in cur.fetchall():
            events[row["ticket_id"]].append(row)
    return events


def _linked_tickets(cur, improvement_ids, now):
    """The tickets of the improvements, each with its downtime as the ticket page computes it
    (an open breakdown to ``now``), newest first -> ``{improvement_id: [ticket, …]}``.  Two
    queries for any number of improvements (no N+1)."""
    result = {improvement_id: [] for improvement_id in improvement_ids}
    if not improvement_ids:
        return result
    cur.execute(f"{_LINKED_TICKETS} WHERE it.improvement_id IN ({marks(improvement_ids)})"
                " ORDER BY t.occurred_at DESC, t.id DESC", list(improvement_ids))
    rows = cur.fetchall()
    events = _events_by_ticket(cur, sorted({row["id"] for row in rows}))
    for row in rows:
        plain = row_to_dict(row)
        result[row["improvement_id"]].append({
            "id": plain["id"],
            "serial": plain["serial"],
            "state": plain["state"],
            "intensity": plain["intensity"],
            "is_breakdown": is_breakdown(plain["intensity"]),
            "occurred_at": plain["occurred_at"],
            "not_a_fault": bool(plain["not_a_fault"]),
            "machine": {"id": plain["m_id"], "code": plain["m_code"], "name": plain["m_name"]},
            "failure_mode": code_ref(plain, "f"),
            "cause": code_ref(plain, "fc"),
            "downtime_minutes": ticket_times(events[row["id"]], now)["downtime_minutes"],
        })
    return result


def _whys(cur, improvement_id):
    """The why-why chain by position, each with its writer's and changer's name (the person
    whose login it is, or the login itself, as created_by_name)."""
    cur.execute("SELECT w.id, w.position, w.question, w.answer, w.evidence, w.created_at, w.created_by,"
                " w.updated_at, w.updated_by, cp.name AS created_by_name, up.name AS updated_by_name"
                " FROM improvement_whys w"
                " LEFT JOIN people cp ON cp.username = w.created_by"
                " LEFT JOIN people up ON up.username = w.updated_by"
                " WHERE w.improvement_id = %s ORDER BY w.position, w.id", (improvement_id,))
    whys = []
    for row in cur.fetchall():
        plain = row_to_dict(row)
        whys.append({
            "id": plain["id"], "position": plain["position"], "question": plain["question"],
            "answer": plain["answer"], "evidence": plain["evidence"],
            "created_at": plain["created_at"], "created_by_name": plain["created_by_name"] or plain["created_by"],
            "updated_at": plain["updated_at"],
            "updated_by_name": (plain["updated_by_name"] or plain["updated_by"]) if plain["updated_by"] else None,
        })
    return whys


_ACTION_COLUMNS = (
    "SELECT a.id, a.kind, a.text, a.owner_id, a.due_date, a.state, a.done_text, a.done_at, a.done_by,"
    " a.cancel_reason, a.cancelled_at, a.cancelled_by, a.created_at, a.created_by, a.updated_at,"
    " o.name AS owner_name, o.active AS owner_active, o.username IS NOT NULL AS owner_has_login,"
    " cp.name AS created_by_name, dp.name AS done_by_name, xp.name AS cancelled_by_name"
    " FROM improvement_actions a JOIN people o ON o.id = a.owner_id"
    " LEFT JOIN people cp ON cp.username = a.created_by"
    " LEFT JOIN people dp ON dp.username = a.done_by"
    " LEFT JOIN people xp ON xp.username = a.cancelled_by"
)


def _problem_at(cur, improvement_id):
    """When the problem happened: the earliest linked ticket's occurred_at (S070 § 5.3), the
    floor of a countermeasure's due date and done time.  Links change only under (6b)."""
    cur.execute("SELECT MIN(t.occurred_at) AS at FROM improvement_tickets it JOIN tickets t ON t.id = it.ticket_id"
                " WHERE it.improvement_id = %s", (improvement_id,))
    return cur.fetchone()["at"]


def _by_name(plain, column):
    """Who a login column names: the person whose login it is, else the login; None when empty."""
    return (plain[f"{column}_name"] or plain[column]) if plain[column] else None


def _site_members(cur, person_ids, site_id):
    """Which of these people are active members of the site today (who may own a countermeasure,
    § 5.3), in one query."""
    if not person_ids:
        return set()
    cur.execute("SELECT DISTINCT p.id FROM people p JOIN memberships ms ON ms.person_id = p.id"
                f" WHERE p.active = 1 AND ms.site_id = %s AND p.id IN ({marks(person_ids)})", [site_id, *person_ids])
    return {row["id"] for row in cur.fetchall()}


def _action_documents(cur, action_ids):
    """The documents not removed of these countermeasures, newest first, in one query ->
    ``{action_id: [{id, kind, title, has_thumb}, …]}``."""
    result = {action_id: [] for action_id in action_ids}
    if action_ids:
        cur.execute("SELECT id, action_id, kind, title, has_thumb FROM equipment_documents"
                    f" WHERE action_id IN ({marks(action_ids)}) AND removed_at IS NULL"
                    " ORDER BY created_at DESC, id DESC", list(action_ids))
        for row in cur.fetchall():
            result[row["action_id"]].append({"id": row["id"], "kind": row["kind"], "title": row["title"],
                                             "has_thumb": bool(row["has_thumb"])})
    return result


def _action_lessons(cur, action_ids):
    """The lesson written for each of these countermeasures (S075 § 6.4; at most one each,
    uq_procedures_action), in one query -> ``{action_id: {id, serial, title, active}}``."""
    if not action_ids:
        return {}
    cur.execute(f"SELECT id, serial, title, active, action_id FROM procedures WHERE action_id IN ({marks(action_ids)})",
                list(action_ids))
    return {row["action_id"]: {"id": row["id"], "serial": row["serial"], "title": row["title"],
                               "active": bool(row["active"])} for row in cur.fetchall()}


def _may_create_lesson(cur, machine_id):
    """The lesson create's own checks (S075 § 5.5, § 5.7) on the improvement's machine as it is
    now: its current unit among the user's units, and procedure:edit at that unit's site.  The
    improvement's site is fixed at its first ticket's unit, but the machine may have moved since
    (BR1-03).  One plain read through NODE_JOINS."""
    cur.execute(f"SELECT u.id AS unit_id, s.id AS site_id FROM equipment e{NODE_JOINS} WHERE e.id = %s",
                (machine_id,))
    machine = cur.fetchone()
    if machine is None:
        return False
    unit_ids = accessible_unit_ids(cur)
    return (unit_ids is None or machine["unit_id"] in unit_ids) and has_perm_at(LESSON_EDIT_KEY, machine["site_id"])


def _actions(cur, improvement_id, site_id, improvement_open, machine_id):
    """The countermeasures in the order they were added (§ 6), each with its owner's standing
    today, its overdue days and what the user may do on it (action_flags), and since S075 its
    lesson and can_write_lesson.  Four queries for any number (the rows, the owners'
    memberships, the documents, the lessons), and one more for the machine's current unit when
    a Lesson countermeasure could take a lesson."""
    cur.execute(f"{_ACTION_COLUMNS} WHERE a.improvement_id = %s ORDER BY a.id", (improvement_id,))
    rows = cur.fetchall()
    if not rows:
        return []
    members = _site_members(cur, sorted({row["owner_id"] for row in rows}), site_id)
    documents = _action_documents(cur, [row["id"] for row in rows])
    lessons = _action_lessons(cur, [row["id"] for row in rows])
    may_create = any(may_write_lesson(row["kind"], row["state"], row["id"] in lessons, True) for row in rows) and (
        _may_create_lesson(cur, machine_id))
    today = _today()
    may_edit = has_perm_at(EDIT_KEY, site_id)
    person_id = current_person_id(cur)
    actions = []
    for row in rows:
        plain = row_to_dict(row)
        actions.append({
            "id": plain["id"], "kind": plain["kind"], "text": plain["text"],
            "owner": {"id": plain["owner_id"], "name": plain["owner_name"], "active": bool(plain["owner_active"]),
                      "has_login": bool(plain["owner_has_login"]), "may_own": plain["owner_id"] in members},
            "due_date": plain["due_date"], "state": plain["state"],
            "overdue_days": overdue_days(row["state"], row["due_date"], today),
            "done_text": plain["done_text"], "done_at": plain["done_at"], "done_by_name": _by_name(plain, "done_by"),
            "cancel_reason": plain["cancel_reason"], "cancelled_at": plain["cancelled_at"],
            "cancelled_by_name": _by_name(plain, "cancelled_by"),
            "created_at": plain["created_at"], "created_by_name": _by_name(plain, "created_by"),
            "updated_at": plain["updated_at"],
            **action_flags(improvement_open, row["state"], may_edit,
                           person_id is not None and person_id == row["owner_id"]),
            "documents": documents[row["id"]],
            "lesson": lessons.get(row["id"]),
            "can_write_lesson": may_write_lesson(row["kind"], row["state"], row["id"] in lessons, may_create),
        })
    return actions


def _root_cause(plain):
    """The root cause as the page shows it, or None (text and cause are both set or neither)."""
    if plain["root_cause"] is None:
        return None
    return {"text": plain["root_cause"],
            "cause": {**code_ref(plain, "rc"), "cause_group": plain["rc_group"], "active": bool(plain["rc_active"])}}


def _machine(row):
    return {"id": row["m_id"], "code": row["m_code"], "name": row["m_name"]}


def _unit(row):
    return {"id": row["unit_id"], "code": row["unit_code"], "site_id": row["site_id"], "site_code": row["site_code"]}


def _ref(plain, prefix):
    return {"id": plain[f"{prefix}_id"], "serial": plain[f"{prefix}_serial"]} if plain[f"{prefix}_id"] else None


# The watch's tickets (§ 5.4): the machines' tickets from watch_days before the watch to the end,
# not-a-fault left out (there was no failure), served by ix_tickets_equipment_state
_WATCH_TICKETS = (
    "SELECT t.id, t.serial, t.occurred_at, t.intensity, t.failure_mode_id, m.code AS m_code,"
    " f.code AS f_code, f.label AS f_label"
    " FROM tickets t JOIN equipment m ON m.id = t.equipment_id LEFT JOIN failure_modes f ON f.id = t.failure_mode_id"
)


def _figures(cur, row, tickets, end):
    """The watch's figures (§ 5.4) on the linked tickets' machines and symptoms, to ``end``.
    Every reader sees them, also tickets of a unit the reader cannot open (serial, time, machine
    and symptom only, as S067 D8)."""
    machines = sorted({(t["machine"]["id"], t["machine"]["code"]) for t in tickets}, key=lambda m: m[1])
    symptoms = {t["failure_mode"]["id"]: t["failure_mode"] for t in tickets if t["failure_mode"]}
    watch_from, days = row["watch_from"], row["watch_days"]
    machine_ids = [machine_id for machine_id, _ in machines]
    rows = []
    if machine_ids:
        cur.execute(f"{_WATCH_TICKETS} WHERE t.equipment_id IN ({marks(machine_ids)}) AND t.not_a_fault = 0"
                    " AND t.occurred_at >= %s AND t.occurred_at < %s ORDER BY t.occurred_at, t.id",
                    [*machine_ids, watch_from - timedelta(days=days), end])
        rows = cur.fetchall()
    events = _events_by_ticket(cur, [r["id"] for r in rows])
    watch_tickets = [{
        "id": r["id"], "serial": r["serial"], "occurred_at": r["occurred_at"], "intensity": r["intensity"],
        "failure_mode_id": r["failure_mode_id"], "machine_code": r["m_code"],
        "symptom": ({"id": r["failure_mode_id"], "code": r["f_code"], "label": r["f_label"]}
                    if r["failure_mode_id"] else None),
        "downtime_minutes": ticket_times(events[r["id"]], end)["downtime_minutes"],
    } for r in rows]
    figures = watch_figures(watch_tickets, set(symptoms), watch_from, days, end)
    return {
        "machines": [{"id": machine_id, "code": code} for machine_id, code in machines],
        "symptoms": sorted(symptoms.values(), key=lambda s: s["code"]),
        **figures,
        "repeats": [row_to_dict(repeat) for repeat in figures["repeats"]],
    }


def _watch(cur, row, tickets, now):
    """``{days, from, until, ended, figures}`` (§ 6); figures from the watch's start, to now for
    an open improvement and to the close for a closed or dropped one (BR1-14)."""
    watch_from = row["watch_from"]
    if watch_from is None:
        return {"days": row["watch_days"], "from": None, "until": None, "ended": False, "figures": None}
    until = watch_until(watch_from, row["watch_days"])
    end = now if is_open(row["state"]) else row["closed_at"]
    return {"days": row["watch_days"], **row_to_dict({"from": watch_from, "until": until}), "ended": now >= until,
            "figures": _figures(cur, row, tickets, end)}


_TIMELINE = (
    "SELECT e.id, e.event, e.occurred_at, e.created_by, p.name AS by_name, e.from_state, e.to_state, e.ticket_id,"
    " t.serial AS t_serial, e.action_id, a.kind AS a_kind, a.text AS a_text, e.remark, e.earlier"
    " FROM improvement_events e LEFT JOIN people p ON p.username = e.created_by"
    " LEFT JOIN tickets t ON t.id = e.ticket_id LEFT JOIN improvement_actions a ON a.id = e.action_id"
    " WHERE e.improvement_id = %s ORDER BY e.occurred_at DESC, e.id DESC"
)


def _timeline(cur, row, shown_state):
    """The timeline, newest first (§ 5.6), one query, with the computed *Watch ended* line once
    the watch has ended (ready to verify, or closed effective or not effective)."""
    cur.execute(_TIMELINE, (row["id"],))
    lines = [{
        "id": r["id"], "event": r["event"], "occurred_at": r["occurred_at"], "by_name": r["by_name"] or r["created_by"],
        "from_state": r["from_state"], "to_state": r["to_state"],
        "ticket": {"id": r["ticket_id"], "serial": r["t_serial"]} if r["ticket_id"] else None,
        "action": {"id": r["action_id"], "kind": r["a_kind"], "text": r["a_text"]} if r["action_id"] else None,
        "remark": r["remark"], "earlier": r["earlier"],
    } for r in cur.fetchall()]
    ended = shown_state == READY_TO_VERIFY or row["state"] in (CLOSED_EFFECTIVE, CLOSED_NOT_EFFECTIVE)
    until = watch_until(row["watch_from"], row["watch_days"]) if row["watch_from"] else None
    return [row_to_dict(line) for line in with_watch_ended(lines, ended and until is not None, until)]


def _closed(plain, row):
    """``{at, by_name, by_lead, remark}`` of a closed or dropped improvement, else None.  by_lead:
    the person whose login closed it is the lead (ISO 27001 A.5.3's recorded departure); admin,
    with no Team record, never is."""
    if row["closed_at"] is None:
        return None
    return {"at": plain["closed_at"], "by_name": plain["closed_by_name"] or plain["closed_by"],
            "by_lead": row["closed_by_person_id"] is not None and row["closed_by_person_id"] == row["lead_id"],
            "remark": plain["close_remark"]}


def _detail(cur, row):
    """The improvement page's data (§ 6): the record, its tickets with each one's removable, the
    loss, the lead's standing today, the user's keys at the improvement's site, since S070 the
    countermeasures with their counts and the time the problem happened, and since S072 the
    display state, the watch, the close, the follow-ups, the timeline and the decision flags.
    is_open is the stored state's (BR1-03), taken before the display state replaces it."""
    now = _now()
    tickets = _linked_tickets(cur, [row["id"]], now)[row["id"]]
    open_now = is_open(row["state"])
    shown_state = display_state(row["state"], row["watch_from"], row["watch_days"], now)
    keys = set(permissions_at_site(row["site_id"]))
    machine = _machine(row)
    links = [{"id": t["id"], "equipment_id": t["machine"]["id"]} for t in tickets]
    for ticket, link in zip(tickets, links):
        ticket["removable"] = open_now and removal_error(link, links, machine) is None
    lead_now = person_at_site(cur, row["lead_id"], row["site_id"])
    actions = _actions(cur, row["id"], row["site_id"], open_now, row["m_id"])
    plain = row_to_dict(row)
    return {
        "id": plain["id"],
        "serial": plain["serial"],
        "state": shown_state,
        "is_open": open_now,
        "title": plain["title"],
        "problem": plain["problem"],
        "machine": machine,
        "unit": _unit(plain),
        "lead": {"id": plain["lead_id"], "name": plain["lead_name"], "active": bool(plain["lead_active"]),
                 "may_lead": lead_now is not None and may_lead(lead_now["role"])},
        "created_at": plain["created_at"],
        "created_by": plain["created_by"],
        "created_by_name": plain["created_by_name"] or plain["created_by"],
        "updated_at": plain["updated_at"],
        "updated_by": plain["updated_by"],
        "tickets": tickets,
        "loss": loss(tickets),
        "whys": _whys(cur, plain["id"]),
        "root_cause": _root_cause(plain),
        "contributing_causes": plain["contributing_causes"],
        "actions": actions,
        "action_counts": action_counts(actions),
        "problem_at": row_to_dict({"at": _problem_at(cur, row["id"])})["at"],
        "permissions": sorted(keys),
        "watch": _watch(cur, row, tickets, now),
        "closed": _closed(plain, row),
        "follow_up_of": _ref(plain, "fo"),
        "follow_up": _ref(plain, "fu"),
        "timeline": _timeline(cur, row, shown_state),
        # § 5.8: the screens follow these, so no control ends in a 403 or a 409 (S068 D6)
        "can_verify": shown_state == READY_TO_VERIFY and VERIFY_KEY in keys,
        "can_drop": open_now and EDIT_KEY in keys,
        "can_add_note": open_now and NOTE_KEY in keys,
        "can_edit_watch": open_now and EDIT_KEY in keys,
    }


def _detail_response(cur, improvement_id):
    """The detail, read inside the write's transaction (as the ticket raise)."""
    return _detail(cur, _read_improvement(cur, improvement_id))


# ---------------------------------------------------------------------------
# List, detail, leads
# ---------------------------------------------------------------------------

@improvements_bp.route("/", strict_slashes=False)
@require_perm(READ_KEY)
def list_improvements():
    page = int_arg("page", 1, minimum=1, maximum=MAX_PAGE)
    per_page = int_arg("per_page", DEFAULT_PER_PAGE, minimum=1, maximum=MAX_PER_PAGE)
    state = enum_arg("state", STATE_FILTERS) or "open"
    unit_id = int_arg("unit_id", None, minimum=1)
    with get_db().cursor() as cur:
        visible = _visible_condition(cur)
        if visible is None:
            return jsonify({"items": [], "total": 0, "page": page, "per_page": per_page})
        conditions, params = [visible[0]], list(visible[1])
        negate = "" if state == "open" else "NOT "
        conditions.append(f"i.state {negate}IN ({marks(IMPROVEMENT_OPEN_STATES)})")
        params.extend(IMPROVEMENT_OPEN_STATES)
        if unit_id is not None:
            conditions.append("i.unit_id = %s")
            params.append(unit_id)
        where = " AND ".join(conditions)
        total = count(cur, f"SELECT COUNT(*) AS n{_IMPROVEMENT_FROM} WHERE {where}", params)
        cur.execute(f"{_IMPROVEMENT_COLUMNS}{_IMPROVEMENT_FROM} WHERE {where} ORDER BY i.id DESC LIMIT %s OFFSET %s",
                    [*params, per_page, (page - 1) * per_page])
        rows = cur.fetchall()
        now = _now()
        linked = _linked_tickets(cur, [row["id"] for row in rows], now)
    items = []
    for row in rows:
        plain = row_to_dict(row)
        items.append({
            "id": plain["id"], "serial": plain["serial"],
            "state": display_state(row["state"], row["watch_from"], row["watch_days"], now), "title": plain["title"],
            "machine": _machine(plain), "unit": _unit(plain), "lead": {"id": plain["lead_id"], "name": plain["lead_name"]},
            "loss": loss(linked[row["id"]]), "created_at": plain["created_at"],
        })
    return jsonify({"items": items, "total": total, "page": page, "per_page": per_page})


@improvements_bp.route("/<int:improvement_id>")
@require_perm(READ_KEY)
def get_improvement(improvement_id):
    with get_db().cursor() as cur:
        return jsonify(_detail_response(cur, improvement_id))


@improvements_bp.route("/leads")
@require_perm(EDIT_KEY)
def list_leads():
    """Who may lead (§ 5.6) at the anchor's site: ``?ticket_id=`` (the start dialog; the ticket
    through its predicate, 404) or ``?improvement_id=`` (the edit dialog; the improvement's
    predicate, 404); then improvement:edit at that site (403), as tickets' _picker_anchor."""
    ticket_id = int_arg("ticket_id", None, minimum=1)
    improvement_id = int_arg("improvement_id", None, minimum=1)
    with get_db().cursor() as cur:
        if ticket_id is not None:
            site_id = read_ticket(cur, ticket_id)["site_id"]
        elif improvement_id is not None:
            site_id = _read_improvement(cur, improvement_id)["site_id"]
        else:
            raise ApiError("ticket_id or improvement_id is required", 400, "ticket_id")
        require_perm_at(EDIT_KEY, site_id)
        items = [{"id": p["id"], "name": p["name"]} for p in people_at_site(cur, site_id) if may_lead(p["role"])]
    return jsonify({"items": items})


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------

@improvements_bp.route("/", methods=["POST"], strict_slashes=False)
@require_perm(EDIT_KEY)
def start_improvement():
    clean = clean_body(validate_improvement, creating=True)
    now = _now()
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        # (6) the serial, from the IST start date: a refused start rolls the bump back
        number = next_counter(cur, serial_scope(now.year, now.month, SERIAL_PREFIX))
        cur.execute(_SHARE_TICKET, (clean["ticket_id"],))   # (7), shared
        locked = cur.fetchone()
        if locked is None:
            raise ApiError("Not found", 404)
        ticket = read_ticket(cur, clean["ticket_id"])    # 404, the ticket is the anchor
        require_perm_at(EDIT_KEY, ticket["site_id"])
        message = (start_error(locked["state"], locked["not_a_fault"])
                   or link_error(ticket["serial"], improvement_links(cur, ticket["id"])))
        if message:
            raise ApiError(message, 409, "ticket_id")
        _check_lead(cur, clean["lead_id"], ticket["site_id"])
        improvement_id = insert_row(cur, "improvements", {
            "serial": format_serial(SERIAL_PREFIX, now.year, now.month, number),
            "unit_id": locked["unit_id"],
            "equipment_id": locked["equipment_id"],
            "title": clean["title"],
            "problem": clean["problem"],
            "lead_id": clean["lead_id"],
        }, actor())
        _link_tickets(cur, improvement_id, [ticket["id"]], _stamp())
        detail = _detail_response(cur, improvement_id)
    return jsonify(detail), 201


def _link_tickets(cur, improvement_id, ticket_ids, now, remark=None):
    """A new improvement's links and its first lines, one shape on every path (BR1-05): started
    (no ticket; ``remark`` names the improvement a follow-up comes from), then one ticket_linked
    per ticket."""
    _add_event(cur, improvement_id, STARTED, now, remark=remark)
    for ticket_id in ticket_ids:
        insert_row(cur, "improvement_tickets", {"improvement_id": improvement_id, "ticket_id": ticket_id}, actor())
        _add_event(cur, improvement_id, TICKET_LINKED, now, ticket_id=ticket_id)


@improvements_bp.route("/<int:improvement_id>", methods=["PUT"])
@require_perm(EDIT_KEY)
def edit_improvement(improvement_id):
    """Title, problem, lead and, since S072, the watch's length (§ 5.2, S072 D14): a field equal
    to the stored one is not written, and an edit that changes nothing writes nothing, no line
    either.  The lead is checked only when it changes, so a lead who has since left the site
    stays until someone picks another (§ 5.6).  A closed improvement is read-only (S072: 409).
    A changed watch changes no stored state: the display state follows from the clock (D1)."""
    clean = clean_body(validate_improvement, creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        locked = _lock_improvement(cur, improvement_id)   # (6b)
        row = _check_improvement(cur, improvement_id)
        _require_open(locked)
        changes = {field: value for field, value in clean.items() if value != locked[field]}
        if "lead_id" in changes:
            _check_lead(cur, changes["lead_id"], row["site_id"])
        update_row(cur, "improvements", improvement_id, changes, actor())
        if changes:
            _add_event(cur, improvement_id, EDITED, _stamp(), remark=_edit_line(cur, locked, changes))
        detail = _detail_response(cur, improvement_id)
    return jsonify(detail)


def _edit_line(cur, locked, changes):
    """The edit's line (BR1-04): "Label: old → new" per changed field, in display values (the
    leads' names, "90 days"); the old values are in the line, so earlier stays NULL."""
    names = _names(cur, [locked["lead_id"], changes.get("lead_id")])
    old = {"title": locked["title"], "problem": locked["problem"], "lead": names.get(locked["lead_id"]),
           "watch": watch_days_text(locked["watch_days"])}
    new = {}
    for field, value in changes.items():
        if field == "lead_id":
            new["lead"] = names.get(value)
        elif field == "watch_days":
            new["watch"] = watch_days_text(value)
        else:
            new[field] = value
    return edit_lines(old, new, EDIT_LABELS)


@improvements_bp.route("/<int:improvement_id>/tickets", methods=["POST"])
@require_perm(EDIT_KEY)
def add_ticket(improvement_id):
    """A ticket of the improvement's site, in any state (Q1.1 a).  A ticket the user cannot see
    answers as an unknown one, so nothing tells that it exists (§ 5.3)."""
    ticket_id = clean_body(validate_link, creating=True)["ticket_id"]
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        locked = _lock_improvement(cur, improvement_id)   # (6b)
        cur.execute(_SHARE_TICKET, (ticket_id,))           # (7), shared
        locked_ticket = cur.fetchone()
        row = _check_improvement(cur, improvement_id)
        _require_open(locked)
        if locked_ticket is None:
            raise ApiError(TICKET_FROM_LIST, 400, "ticket_id")
        try:
            ticket = read_ticket(cur, ticket_id)
        except ApiError as hidden:
            raise ApiError(TICKET_FROM_LIST, 400, "ticket_id") from hidden
        if ticket["site_id"] != row["site_id"]:
            raise ApiError(TICKET_OTHER_SITE, 400, "ticket_id")
        if locked_ticket["not_a_fault"]:
            raise ApiError(NOT_A_FAULT, 409, "ticket_id")
        message = link_error(ticket["serial"], improvement_links(cur, ticket_id), improvement_id)
        if message:
            raise ApiError(message, 409, "ticket_id")
        insert_row(cur, "improvement_tickets", {"improvement_id": improvement_id, "ticket_id": ticket_id}, actor())
        _add_event(cur, improvement_id, TICKET_LINKED, _stamp(), ticket_id=ticket_id)
        detail = _detail_response(cur, improvement_id)
    return jsonify(detail), 201


@improvements_bp.route("/<int:improvement_id>/tickets/<int:ticket_id>", methods=["DELETE"])
@require_perm(EDIT_KEY)
def remove_ticket(improvement_id, ticket_id):
    """A wrongly added ticket taken off again (D9); the improvement keeps a ticket of its own
    machine (BR1-02).  The link row goes; the ticket row is not written."""
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        locked = _lock_improvement(cur, improvement_id)   # (6b)
        row = _check_improvement(cur, improvement_id)
        _require_open(locked)
        cur.execute("SELECT t.id, t.equipment_id FROM improvement_tickets it JOIN tickets t ON t.id = it.ticket_id"
                    " WHERE it.improvement_id = %s", (improvement_id,))
        links = cur.fetchall()
        ticket = next((link for link in links if link["id"] == ticket_id), None)
        if ticket is None:
            raise ApiError("Not found", 404)
        message = removal_error(ticket, links, _machine(row))
        if message:
            raise ApiError(message, 409)
        cur.execute("DELETE FROM improvement_tickets WHERE improvement_id = %s AND ticket_id = %s",
                    (improvement_id, ticket_id))
        # The line's foreign key takes the ticket's shared lock: (6b) -> (7) shared, as Add ticket
        _add_event(cur, improvement_id, TICKET_REMOVED, _stamp(), ticket_id=ticket_id)
        detail = _detail_response(cur, improvement_id)
    return jsonify(detail)


# ---------------------------------------------------------------------------
# The why-why chain and the root cause (S069; LOCK ORDER above)
# ---------------------------------------------------------------------------

def _lock_for_analysis(cur, improvement_id):
    """Every S069 write's start (§ 5.1): (6b), then the predicate 404, the key at the site 403
    and the open state 409 -> ``(the locked row, the visible row)``."""
    locked = _lock_improvement(cur, improvement_id)   # (6b)
    row = _check_improvement(cur, improvement_id)
    _require_open(locked)
    return locked, row


def _chain(cur, improvement_id):
    """The improvement's whys as ``(id, position)`` by position, read under (6b)."""
    cur.execute("SELECT id, position FROM improvement_whys WHERE improvement_id = %s ORDER BY position, id",
                (improvement_id,))
    return [(row["id"], row["position"]) for row in cur.fetchall()]


def _shift(cur, pairs):
    """Positions of lines that only shifted: no updated_* stamp (BR1-07)."""
    for why_id, position in pairs:
        cur.execute("UPDATE improvement_whys SET position = %s WHERE id = %s", (position, why_id))


def _read_why(cur, improvement_id, why_id):
    """The why of this improvement; a why of another improvement or an unknown one -> 404."""
    cur.execute("SELECT id, position, question, answer, evidence FROM improvement_whys"
                " WHERE id = %s AND improvement_id = %s", (why_id, improvement_id))
    why = cur.fetchone()
    if why is None:
        raise ApiError("Not found", 404)
    return why


@improvements_bp.route("/<int:improvement_id>/whys", methods=["POST"])
@require_perm(EDIT_KEY)
def add_why(improvement_id):
    """A why appended at the end of the chain, up to WHYS_MAX (§ 5.2, § 5.3)."""
    clean = clean_body(validate_why, creating=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        _lock_for_analysis(cur, improvement_id)
        n = len(_chain(cur, improvement_id))
        if n >= WHYS_MAX:
            raise ApiError(WHYS_FULL, 409)
        insert_row(cur, "improvement_whys", {"improvement_id": improvement_id, "position": n + 1, **clean}, actor())
        _add_event(cur, improvement_id, WHY_ADDED, _stamp(),
                   remark=why_line(n + 1, clean["question"], clean["answer"], clean["evidence"]))
        detail = _detail_response(cur, improvement_id)
    return jsonify(detail), 201


def _why_text(why):
    return why_line(why["position"], why["question"], why["answer"], why["evidence"])


@improvements_bp.route("/<int:improvement_id>/whys/<int:why_id>", methods=["PUT"])
@require_perm(EDIT_KEY)
def edit_why(improvement_id, why_id):
    """The text and the place in the chain (§ 5.3): a field equal to the stored one is not
    written, and an edit that changes nothing writes nothing.  The moved why is stamped
    updated_*; the lines that only shifted are not."""
    clean = clean_body(validate_why, creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        _lock_for_analysis(cur, improvement_id)
        why = _read_why(cur, improvement_id, why_id)
        changes = {field: value for field, value in clean.items() if field != "position" and value != why[field]}
        shifted = []
        if "position" in clean:
            chain = _chain(cur, improvement_id)
            message = position_error(len(chain), clean["position"])
            if message:
                raise ApiError(message, 400, "position")
            for pair_id, position in reorder(chain, why_id, clean["position"]):
                if pair_id == why_id:
                    changes["position"] = position
                else:
                    shifted.append((pair_id, position))
        update_row(cur, "improvement_whys", why_id, changes, actor())
        _shift(cur, shifted)
        if changes:   # the other whys' shifts write no line
            _add_event(cur, improvement_id, WHY_CHANGED, _stamp(), remark=_why_text({**why, **changes}),
                       earlier=_why_text(why))
        detail = _detail_response(cur, improvement_id)
    return jsonify(detail)


@improvements_bp.route("/<int:improvement_id>/whys/<int:why_id>", methods=["DELETE"])
@require_perm(EDIT_KEY)
def remove_why(improvement_id, why_id):
    """The row is deleted (S069 D6); the lines after it move up.  Since S072 the timeline keeps
    the removed why's text (why_removed, earlier)."""
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        _lock_for_analysis(cur, improvement_id)
        why = _read_why(cur, improvement_id, why_id)
        rest = [pair for pair in _chain(cur, improvement_id) if pair[0] != why_id]
        cur.execute("DELETE FROM improvement_whys WHERE id = %s", (why_id,))
        _shift(cur, renumber(rest))
        _add_event(cur, improvement_id, WHY_REMOVED, _stamp(), earlier=_why_text(why))
        detail = _detail_response(cur, improvement_id)
    return jsonify(detail)


@improvements_bp.route("/<int:improvement_id>/root-cause", methods=["PUT"])
@require_perm(EDIT_KEY)
def set_root_cause(improvement_id):
    """Set or change the root cause and the contributing causes (§ 5.2; never cleared, D4).
    The cause is checked only when it changes, so a root cause whose cause was deactivated
    later survives an edit of the text (a plain read, as tickets' _check_active_code).  The
    linked tickets are never written (Q2.3 a)."""
    clean = clean_body(validate_root_cause, creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        locked, row = _lock_for_analysis(cur, improvement_id)   # row: the old cause's code and label
        changes = {field: value for field, value in clean.items() if value != locked[field]}
        old_cause = (row["rc_code"], row["rc_label"])
        new_cause = old_cause
        if "root_cause_id" in changes:
            cur.execute("SELECT active, code, label FROM failure_causes WHERE id = %s", (changes["root_cause_id"],))
            cause = cur.fetchone()
            if cause is None or not cause["active"]:
                raise ApiError(CAUSE_ACTIVE, 400, "root_cause_id")
            new_cause = (cause["code"], cause["label"])
        update_row(cur, "improvements", improvement_id, changes, actor())
        if changes:
            merged = {**locked, **changes}
            first = locked["root_cause_id"] is None
            _add_event(cur, improvement_id, ROOT_CAUSE_SET if first else ROOT_CAUSE_CHANGED, _stamp(),
                       remark=root_cause_line(*new_cause, merged["root_cause"], merged["contributing_causes"]),
                       earlier=None if first else root_cause_line(*old_cause, locked["root_cause"],
                                                                   locked["contributing_causes"]))
        _settle_state(cur, improvement_id, locked, root_cause_set=True)
        detail = _detail_response(cur, improvement_id)
    return jsonify(detail)


# ---------------------------------------------------------------------------
# Countermeasures (S070; LOCK ORDER above)
# ---------------------------------------------------------------------------

# (6c): the countermeasure's decision columns, and the values a change compares with
_LOCK_ACTION = ("SELECT id, improvement_id, state, kind, text, owner_id, due_date FROM improvement_actions"
                " WHERE id = %s AND improvement_id = %s FOR UPDATE")


def _lock_action(cur, improvement_id, action_id):
    """(6c), after (6b) -> the locked row; a countermeasure of another improvement or an unknown
    one -> 404."""
    cur.execute(_LOCK_ACTION, (action_id, improvement_id))
    action = cur.fetchone()
    if action is None:
        raise ApiError("Not found", 404)
    return action


def _refuse_state(operation, action):
    """The countermeasure's own state (§ 5.5), from its locked row: 409."""
    message = action_state_error(operation, action["state"])
    if message:
        raise ApiError(message, 409)


def _require_owner_or_editor(cur, site_id, owner_id):
    """Owner by data (§ 5.7, as Plan § 3's pm_job:work): improvement:edit at the improvement's
    site, or the user's own Team record owns the countermeasure; else 403.  A user with no Team
    record (IT admin) owns nothing."""
    if has_perm_at(EDIT_KEY, site_id):
        return
    person_id = current_person_id(cur)
    if person_id is None or person_id != owner_id:
        raise ApiError(OWNER_OR_EDITOR, 403)


def _check_owner(cur, owner_id, site_id):
    """§ 5.3, D3: an active person with a membership at the site, any role, a login or not ->
    ``{id, name, role}`` (S072: the add's line names the owner and their role)."""
    person = person_at_site(cur, owner_id, site_id)
    if person is None:
        raise ApiError(OWNER_AT_SITE, 400, "owner_id")
    return person


def _check_due(cur, improvement_id, due):
    """§ 5.3, D7: from the day the problem happened to a year ahead."""
    problem_at = _problem_at(cur, improvement_id)
    message = due_date_error(due, problem_at.date() if problem_at else None, _today())
    if message:
        raise ApiError(message, 400, "due_date")


def _lock_for_actions(cur, improvement_id, action_id=None):
    """A countermeasure write's start (§ 5.6): (6b), then (6c) when ``action_id`` is given ->
    ``(locked improvement, locked countermeasure or None)``.  The checks come after, as plain
    reads, in the order § 5.1 gives."""
    locked = _lock_improvement(cur, improvement_id)   # (6b)
    action = _lock_action(cur, improvement_id, action_id) if action_id is not None else None   # (6c)
    return locked, action


@improvements_bp.route("/<int:improvement_id>/actions", methods=["POST"])
@require_perm(EDIT_KEY)
def add_action(improvement_id):
    """A countermeasure with its kind, text, owner and due date, up to ACTIONS_MAX (§ 5.2)."""
    clean = clean_body(validate_action, creating=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        locked, _ = _lock_for_actions(cur, improvement_id)
        row = _check_improvement(cur, improvement_id)   # 404, 403
        _require_open(locked)
        if count(cur, "SELECT COUNT(*) AS n FROM improvement_actions WHERE improvement_id = %s",
                 (improvement_id,)) >= ACTIONS_MAX:
            raise ApiError(ACTIONS_FULL, 409)
        owner = _check_owner(cur, clean["owner_id"], row["site_id"])
        _check_due(cur, improvement_id, clean["due_date"])
        action_id = insert_row(cur, "improvement_actions", {"improvement_id": improvement_id, **clean}, actor())
        _add_event(cur, improvement_id, ACTION_ADDED, _stamp(), action_id=action_id,
                   remark=action_line(clean["kind"], clean["text"], owner["name"], owner["role"], clean["due_date"]))
        # An open countermeasure of a WATCH_KINDS kind ends Watching (D3)
        _settle_state(cur, improvement_id, locked, root_cause_set=locked["root_cause_id"] is not None)
        _queue_given(cur, improvement_id, action_id, clean["owner_id"])
        detail = _detail_response(cur, improvement_id)
    return jsonify(detail), 201


def _queue_given(cur, improvement_id, action_id, owner_id, old_owner_id=None):
    """*Countermeasure for you* (S074 § 5.5, D5), in this transaction, so a refused write queues
    nothing: on an add, and on a change of owner, unless the owner gave it to themselves.  The
    task insert touches only task_queue: no new lock."""
    if given_alert(owner_id, current_person_id(cur), old_owner_id):
        enqueue_improvement_alert(cur, ACTION_GIVEN, improvement_id, action_id=action_id, person_id=owner_id,
                                  given_by=actor())


def _action_edit_line(cur, action, changes):
    """A countermeasure change's line: "Label: old → new" per changed field, the kind as its
    word, the owner as the name, the due date DD-MM-YYYY; earlier NULL (the old value is in it)."""
    names = _names(cur, [action["owner_id"], changes.get("owner_id")])

    def shown(values):
        out = {}
        if "kind" in values:
            out["kind"] = ACTION_KIND_LABELS[values["kind"]]
        if "text" in values:
            out["text"] = values["text"]
        if "owner_id" in values:
            out["owner"] = names.get(values["owner_id"])
        if "due_date" in values:
            out["due"] = f"{values['due_date']:%d-%m-%Y}"
        return out
    return edit_lines(shown(action), shown(changes), ACTION_EDIT_LABELS)


@improvements_bp.route("/<int:improvement_id>/actions/<int:action_id>", methods=["PUT"])
@require_perm(EDIT_KEY)
def edit_action(improvement_id, action_id):
    """Kind, text, owner and due date of an open countermeasure: a field equal to the stored one
    is not written, and a change of nothing writes nothing.  The owner and the due date are
    checked only when they change, so an owner who has since left the site stays until someone
    picks another (§ 5.3)."""
    clean = clean_body(validate_action, creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        locked, action = _lock_for_actions(cur, improvement_id, action_id)
        row = _check_improvement(cur, improvement_id)   # 404, 403
        _require_open(locked)
        _refuse_state("change", action)
        changes = {field: value for field, value in clean.items() if value != action[field]}
        if "owner_id" in changes:
            _check_owner(cur, changes["owner_id"], row["site_id"])
        if "due_date" in changes:
            _check_due(cur, improvement_id, changes["due_date"])
        update_row(cur, "improvement_actions", action_id, changes, actor())
        if changes:
            _add_event(cur, improvement_id, ACTION_CHANGED, _stamp(), action_id=action_id,
                       remark=_action_edit_line(cur, action, changes))
        # A kind changed into or out of WATCH_KINDS can end or keep the watch
        _settle_state(cur, improvement_id, locked, root_cause_set=locked["root_cause_id"] is not None)
        if "owner_id" in changes:
            _queue_given(cur, improvement_id, action_id, changes["owner_id"], action["owner_id"])
        detail = _detail_response(cur, improvement_id)
    return jsonify(detail)


@improvements_bp.route("/<int:improvement_id>/actions/<int:action_id>/done", methods=["POST"])
@require_perm(READ_KEY)
def mark_action_done(improvement_id, action_id):
    """What was done and when (§ 5.2), by the owner or an improvement:edit holder (§ 5.7).  No
    done_at is *Now*: the server's clock.  done_by is who recorded it; updated_* stay the last
    change of the plan (D8)."""
    clean = clean_body(validate_done, creating=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        locked, action = _lock_for_actions(cur, improvement_id, action_id)
        row = _read_improvement(cur, improvement_id)   # 404
        _require_owner_or_editor(cur, row["site_id"], action["owner_id"])
        _require_open(locked)
        _refuse_state("done", action)
        now = _stamp()
        done_at = clean["done_at"] or now
        message = done_time_error(done_at, now, _problem_at(cur, improvement_id))
        if message:
            raise ApiError(message, 400, "done_at")
        cur.execute("UPDATE improvement_actions SET state = %s, done_text = %s, done_at = %s, done_by = %s"
                    " WHERE id = %s", (ACTION_DONE, clean["done_text"], done_at, actor(), action_id))
        _add_event(cur, improvement_id, ACTION_DONE_EVENT, done_at, action_id=action_id, remark=clean["done_text"])
        # The last open one done starts the watch (§ 5.1)
        _settle_state(cur, improvement_id, locked, root_cause_set=locked["root_cause_id"] is not None)
        detail = _detail_response(cur, improvement_id)
    return jsonify(detail)


@improvements_bp.route("/<int:improvement_id>/actions/<int:action_id>/cancel", methods=["POST"])
@require_perm(EDIT_KEY)
def cancel_action(improvement_id, action_id):
    """An open countermeasure cancelled with a reason; the row stays (ISO 9001 § 7.5.3, D5)."""
    clean = clean_body(validate_cancel, creating=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        locked, action = _lock_for_actions(cur, improvement_id, action_id)
        _check_improvement(cur, improvement_id)   # 404, 403
        _require_open(locked)
        _refuse_state("cancel", action)
        _cancel(cur, improvement_id, action_id, clean["reason"], _stamp())
        # The last open one cancelled starts the watch, when one is done (§ 5.1)
        _settle_state(cur, improvement_id, locked, root_cause_set=locked["root_cause_id"] is not None)
        detail = _detail_response(cur, improvement_id)
    return jsonify(detail)


def _cancel(cur, improvement_id, action_id, reason, now):
    """Cancel one locked open countermeasure with its reason, and its line (S070; S072's drop)."""
    cur.execute("UPDATE improvement_actions SET state = %s, cancel_reason = %s, cancelled_at = %s,"
                " cancelled_by = %s WHERE id = %s", (ACTION_CANCELLED, reason, now, actor(), action_id))
    _add_event(cur, improvement_id, ACTION_CANCELLED_EVENT, now, action_id=action_id, remark=reason)


@improvements_bp.route("/actions/mine")
@require_perm(READ_KEY)
def my_actions():
    """The user's open countermeasures of open improvements inside the predicate, by due date
    (*Me › Open work*, D9).  A user with no Team record owns none."""
    with get_db().cursor() as cur:
        person_id = current_person_id(cur)
        visible = _visible_condition(cur)
        if person_id is None or visible is None:
            return jsonify({"items": [], "total": 0})
        where = (f"a.owner_id = %s AND a.state = %s AND i.state IN ({marks(IMPROVEMENT_OPEN_STATES)})"
                 f" AND {visible[0]}")
        params = [person_id, ACTION_OPEN, *IMPROVEMENT_OPEN_STATES, *visible[1]]
        from_ = (" FROM improvement_actions a JOIN improvements i ON i.id = a.improvement_id"
                 " JOIN equipment m ON m.id = i.equipment_id JOIN units u ON u.id = i.unit_id")
        total = count(cur, f"SELECT COUNT(*) AS n{from_} WHERE {where}", params)
        cur.execute("SELECT a.id, a.kind, a.text, a.due_date, a.state, i.id AS i_id, i.serial, i.title, i.state AS i_state,"
                    f" u.site_id, m.id AS m_id, m.code AS m_code, m.name AS m_name{from_} WHERE {where}"
                    " ORDER BY a.due_date, a.id LIMIT %s", [*params, MAX_PER_PAGE])
        rows = cur.fetchall()
    today = _today()
    items = []
    for row in rows:
        flags = action_flags(is_open(row["i_state"]), row["state"], has_perm_at(EDIT_KEY, row["site_id"]), True)
        items.append({
            "id": row["id"], "kind": row["kind"], "text": row["text"], "due_date": row["due_date"].isoformat(),
            "overdue_days": overdue_days(row["state"], row["due_date"], today),
            "can_mark_done": flags["can_mark_done"], "can_add_photo": flags["can_add_photo"],
            "improvement": {"id": row["i_id"], "serial": row["serial"], "title": row["title"], "machine": _machine(row)},
        })
    return jsonify({"items": items, "total": total})


@improvements_bp.route("/owners")
@require_perm(EDIT_KEY)
def list_owners():
    """Who may own a countermeasure (§ 5.3, D3): every active person of the improvement's site,
    any role, a login or not, by name."""
    improvement_id = int_arg("improvement_id", None, minimum=1)
    if improvement_id is None:
        raise ApiError("improvement_id is required", 400, "improvement_id")
    with get_db().cursor() as cur:
        site_id = _read_improvement(cur, improvement_id)["site_id"]
        require_perm_at(EDIT_KEY, site_id)
        items = [{"id": p["id"], "name": p["name"]} for p in people_at_site(cur, site_id)]
    return jsonify({"items": items})


# ---------------------------------------------------------------------------
# Notes, the verified close and the drop (S072 § 5.5, § 5.7; LOCK ORDER above)
# ---------------------------------------------------------------------------

@improvements_bp.route("/<int:improvement_id>/notes", methods=["POST"])
@require_perm(NOTE_KEY)
def add_note(improvement_id):
    """A note on the timeline by any reader at the site but IT admin (Q1.3 a, D6); open only
    (D12).  No correction of a note (§ 9 Q3)."""
    clean = clean_body(validate_note, creating=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        locked = _lock_improvement(cur, improvement_id)   # (6b)
        row = _read_improvement(cur, improvement_id)       # 404
        require_perm_at(NOTE_KEY, row["site_id"])           # 403
        _require_open(locked)                               # 409
        _add_event(cur, improvement_id, NOTE, _stamp(), remark=clean["remark"])
        detail = _detail_response(cur, improvement_id)
    return jsonify(detail), 201


def _lock_for_close(cur, improvement_id, key):
    """A close's or a drop's start: (6b), the predicate 404, ``key`` at the site 403 -> the
    locked row."""
    locked = _lock_improvement(cur, improvement_id)   # (6b)
    row = _read_improvement(cur, improvement_id)
    require_perm_at(key, row["site_id"])
    return locked


def _require_ready(locked, now):
    """§ 5.1: verify only after the watch (D11), from the locked row and the clock (D1): 409."""
    until = watch_until(locked["watch_from"], locked["watch_days"]) if locked["watch_from"] else None
    message = close_error(display_state(locked["state"], locked["watch_from"], locked["watch_days"], now), until)
    if message:
        raise ApiError(message, 409)


def _close(cur, improvement_id, state, now, remark):
    """The row closed (no updated_*, D16) and its links' open_link NULL, so its tickets may start
    or join another improvement (S067 D4)."""
    cur.execute("UPDATE improvements SET state = %s, closed_at = %s, closed_by = %s, close_remark = %s WHERE id = %s",
                (state, now, actor(), remark, improvement_id))
    cur.execute("UPDATE improvement_tickets SET open_link = NULL WHERE improvement_id = %s", (improvement_id,))


@improvements_bp.route("/<int:improvement_id>/verify/effective", methods=["POST"])
@require_perm(VERIFY_KEY)
def close_effective(improvement_id):
    """*Close: it worked* (ISO 9001 § 10.2.1 d): by an engineer or manager of the site, the lead
    too (Q4.2 a), once the watch has ended."""
    remark = clean_body(lambda body, _creating: validate_close(body, False, "remark"), creating=True)["remark"]
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        locked = _lock_for_close(cur, improvement_id, VERIFY_KEY)
        now = _stamp()
        _require_ready(locked, now)
        _close(cur, improvement_id, CLOSED_EFFECTIVE, now, remark)
        _add_event(cur, improvement_id, CLOSED_EFFECTIVE, now, from_state=READY_TO_VERIFY, to_state=CLOSED_EFFECTIVE,
                   remark=remark)
        detail = _detail_response(cur, improvement_id)
    return jsonify(detail)


@improvements_bp.route("/<int:improvement_id>/verify/not-effective", methods=["POST"])
@require_perm(VERIFY_KEY)
def close_not_effective(improvement_id):
    """*Did not work — analyse again* (Q1.4 a, D9): the old one closed with its remark, and a
    follow-up started with the old title, problem, lead, watch and tickets; nothing of the
    analysis is copied.  Answers the follow-up's detail, 201.  The counter (6) comes before (6b),
    as the global order says; a refusal rolls the bump back, so no number is lost."""
    remark = clean_body(lambda body, _creating: validate_close(body, True, "remark"), creating=True)["remark"]
    now = _stamp()
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        number = next_counter(cur, serial_scope(now.year, now.month, SERIAL_PREFIX))   # (6)
        locked = _lock_for_close(cur, improvement_id, VERIFY_KEY)                   # (6b)
        _require_ready(locked, now)
        # A locking read: the counter's SELECT fixed the snapshot before (6b) was held, so a plain
        # read would miss a link added or removed while this route waited (CR1-01).  _close
        # updates exactly these rows, so the lock adds no edge.
        cur.execute("SELECT ticket_id FROM improvement_tickets WHERE improvement_id = %s ORDER BY ticket_id"
                    " FOR UPDATE", (improvement_id,))
        ticket_ids = [r["ticket_id"] for r in cur.fetchall()]
        _close(cur, improvement_id, CLOSED_NOT_EFFECTIVE, now, remark)
        _add_event(cur, improvement_id, CLOSED_NOT_EFFECTIVE, now, from_state=READY_TO_VERIFY,
                   to_state=CLOSED_NOT_EFFECTIVE, remark=remark)
        follow_up_id = insert_row(cur, "improvements", {
            "serial": format_serial(SERIAL_PREFIX, now.year, now.month, number),
            "unit_id": locked["unit_id"],
            "equipment_id": locked["equipment_id"],
            "title": locked["title"],
            "problem": locked["problem"],
            "lead_id": locked["lead_id"],
            "watch_days": locked["watch_days"],
            "follow_up_of_id": improvement_id,
        }, actor())
        # _close freed uq_improvement_tickets_open in this transaction, so the links fit
        _link_tickets(cur, follow_up_id, ticket_ids, now, remark=f"Follow-up of {locked['serial']}")
        detail = _detail_response(cur, follow_up_id)
    return jsonify(detail), 201


@improvements_bp.route("/<int:improvement_id>/drop", methods=["POST"])
@require_perm(EDIT_KEY)
def drop_improvement(improvement_id):
    """*Drop* an open improvement with a reason (engineers and managers).  Its open
    countermeasures are cancelled with it, each with its line (D10), taken (6c) by id order."""
    reason = clean_body(lambda body, _creating: validate_close(body, True, "reason"), creating=True)["reason"]
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        locked = _lock_for_close(cur, improvement_id, EDIT_KEY)
        _require_open(locked)
        now = _stamp()
        cur.execute("SELECT id FROM improvement_actions WHERE improvement_id = %s AND state = %s ORDER BY id"
                    " FOR UPDATE", (improvement_id, ACTION_OPEN))   # (6c), by id
        for action in cur.fetchall():
            _cancel(cur, improvement_id, action["id"], dropped_reason(reason), now)
        _close(cur, improvement_id, DROPPED, now, reason)
        _add_event(cur, improvement_id, DROPPED, now,
                   from_state=display_state(locked["state"], locked["watch_from"], locked["watch_days"], now),
                   to_state=DROPPED, remark=reason)
        detail = _detail_response(cur, improvement_id)
    return jsonify(detail)


# ---------------------------------------------------------------------------
# The documents store's fourth owner: the countermeasure (S070 § 5.8; documents.OWNERS)
# ---------------------------------------------------------------------------

def _action_row(cur, action_id):
    """Plain read of a countermeasure's improvement_id, state and owner; 404 when missing."""
    cur.execute("SELECT id, improvement_id, state, owner_id FROM improvement_actions WHERE id = %s", (action_id,))
    action = cur.fetchone()
    if action is None:
        raise ApiError("Not found", 404)
    return action


def _document_rights(cur, key, site_id, owner_id):
    """documents.py passes the owner's key for the operation, so this branches on it: the write
    key improvement:read (D4) -> the owner or improvement:edit at the improvement's site (§ 5.7);
    the purge key (restore) -> that key at the site."""
    if key == READ_KEY:
        _require_owner_or_editor(cur, site_id, owner_id)
    else:
        require_perm_at(key, site_id)


def read_action(cur, action_id, _key=None):
    """documents.py's ``read``: the countermeasure through its improvement's predicate; 404 when
    missing or not visible -> the countermeasure's row with its improvement's site and state."""
    action = _action_row(cur, action_id)
    improvement = _read_improvement(cur, action["improvement_id"])
    return {**action, "site_id": improvement["site_id"], "improvement_state": improvement["state"]}


def read_action_for_change(cur, action_id, key):
    """documents.py's ``read_for_change``: a write's early refusals from plain reads, so a refused
    upload reads and writes no file.  ``key`` is improvement:read (upload) -> the owner or
    improvement:edit at the site, 403; then the improvement open and the countermeasure not
    cancelled, 409.  The decisions that count are lock_action_for_change's."""
    action = read_action(cur, action_id)
    _document_rights(cur, key, action["site_id"], action["owner_id"])
    if not is_open(action["improvement_state"]):
        raise ApiError(IMPROVEMENT_CLOSED, 409)
    _refuse_state("photo", action)
    return action


def _lock_action_for_documents(cur, action_id):
    """The one owner lock of a countermeasure's document (§ 5.6): a plain read of its
    improvement_id (it never changes; 404), then (6b) and (6c), then the predicate (404) ->
    ``(locked improvement, locked countermeasure, the improvement's visible row)``."""
    improvement_id = _action_row(cur, action_id)["improvement_id"]
    locked, action = _lock_for_actions(cur, improvement_id, action_id)
    return locked, action, _read_improvement(cur, improvement_id)


def lock_action_for_change(cur, action_id, key):
    """documents.py's ``lock_for_change`` (upload, retitle, remove, restore), in the write
    transaction: 404, then by ``key`` — improvement:read, the write key: the owner or
    improvement:edit at the site; the purge key (restore): that key at the site — 403, then the
    improvement open and the countermeasure not cancelled, 409, all from the locked rows."""
    locked, action, row = _lock_action_for_documents(cur, action_id)
    _document_rights(cur, key, row["site_id"], action["owner_id"])
    _require_open(locked)
    _refuse_state("photo", action)


def lock_action_for_purge(cur, action_id, key):
    """documents.py's ``lock_for_purge``: as lock_action_for_change with the purge key and no
    state check: erasing a file is disposition of information (S008 § 5.3)."""
    _, _, row = _lock_action_for_documents(cur, action_id)
    require_perm_at(key, row["site_id"])
