"""Tickets — raise and see (docs/steps/S017-raise-tickets/1-brief.md) and work them to the end
(docs/steps/S018-work-tickets/1-brief.md): moves, re-grade, edit, assignment, labour, repeat;
the parts used (docs/steps/S020-parts-used/1-brief.md); work notes
(docs/steps/S027-work-notes/1-brief.md); the Me page's two reads, ``raised=me`` on the list and
``GET /activity`` (docs/steps/S031-me-page/1-brief.md).

Thin shell: tickets_core holds the rules (intensity, the event-time window, the serial, the
description rule, machine and component from the node, the moves table, the send-back and
re-grade rules, labour, parts and close validation, the times); this module checks access, locks,
reads the rows the rules need and stores the result.

ACCESS — one predicate for the list, the detail and the ticket's photos (§ 5.3): a ticket is
visible when its own unit (the machine's unit at raise) or its machine's current unit is among
the units where the user holds ticket:read.  So a moved machine's tickets show on its
equipment page wherever it stands, and the old unit's team keeps them.  Outside it: 404.
"The ticket's site" in every write check is the site of tickets.unit_id.

PEOPLE — who may be named (S018 § 5.8): the person on back in service and on a labour row is
any active person with a membership at the ticket's site; an assignee must hold one of
config_rbac.ASSIGNABLE_ROLES there.  The role is read from memberships, never from the
user's token, so IT admin (a token role) is never assigned.

LOCK ORDER (equipment.py's numbers): (1) the node raised on → (6) the serial counter →
(7) the ticket row.  Ticket rows are locked only here and by documents.py (the ticket owner,
through the functions below), always last; nothing that holds a ticket lock then takes an
equipment, unit or counter lock.  Ancestors of the node are read plain, never locked.
Working a ticket (S018 § 5.3) — a move (S019's schedule, change plan and the start from
scheduled included), re-grade, edit, assignment, labour or parts change (S020), a new work
note (S027) — locks (7) explicitly, and nothing else explicitly.  A note's correction (S027
§ 5.2) locks (7), then the note's event row FOR UPDATE; only the correction locks an event row,
and nothing locks one first, so this adds no lock-order edge.  Its ticket_note_edits insert
takes the event row's FK lock, already held.  Codes and people are read plain.  A change of tickets.state also
rewrites the entries of ix_tickets_unit_state, ix_tickets_equipment_state and
ix_tickets_component_state, the indexes of the unit, machine and component foreign keys, so
InnoDB re-checks those keys and takes shared locks on the unit, machine and (when set)
component rows (S025 CR1-02; S019 § 5.6 adds no lock and no lock-order edge).  Three reads
take a shared lock, each the one a foreign key of the same write takes anyway, so none
adds a lock-order edge (S025 § 1.5, § 1.6; S020 § 5.2):
- the edit reads the new component's row LOCK IN SHARE MODE (its parent plain) and decides
  "not scrapped" from it: a scrap holds that row FOR UPDATE, so the two serialise;
- a raise with repeat_of_id re-reads the earlier ticket LOCK IN SHARE MODE after its insert:
  a send-back holds that row FOR UPDATE, so the two cannot both succeed: when the send-back
  commits first, the raise is refused (and when the raise commits first, the send-back
  refuses a ticket that has a repeat).  When they overlap, they can deadlock instead (below);
- a parts add, and a parts edit whose node changes, read that node's row LOCK IN SHARE MODE
  (the machine itself or a part below it; its parent plain) and decide "not scrapped" from it,
  through the helper the edit uses: a scrap holds that row FOR UPDATE, so the two serialise.
  An edit that keeps the node reads nothing more (the line is history, S020 BR1-03).
A raise with *Already fixed* (A1) applies the restore move to its own new row inside the raise's
transaction: no further lock, and a refusal rolls the whole raise back, serial included.
The alerts (S021 § 5.3) are task_queue rows written in the same transaction (alerts.py); the
grade an escalation reads is a plain read.  The worker's ticket_escalate locks (7) too, alone
and last, and takes nothing after it; its other reads are plain: no new lock-order edge.

The ticket insert takes shared locks through its foreign keys on the machine's equipment
row, the component's, the unit, the person, the failure mode and the earlier ticket of a
repeat.  Four deadlocks follow, accepted (§ 5.4, § 7 decision 12, S025 CR1-02; InnoDB rolls
one side back with 1213, a rare JSON 500, and a retry gives the right answer):
- scrapping a machine (machine, then its parts FOR UPDATE) against a raise on one of its parts
  (the part, then the machine's shared FK lock);
- a person's site-row edit (person, then units) against a raise naming that person (the FK
  checks take unit, then person);
- a raise of a repeat (the machine (1), then the earlier ticket's shared lock) against a
  send-back of that earlier ticket (the ticket FOR UPDATE, then the machine's shared FK lock
  at its state change).  A parts write on the earlier ticket has the same shape (S020 § 5.2):
  the ticket FOR UPDATE, then the shared lock on the node the line is fitted to, which the
  raise holds as (1) when the repeat is raised on that node;
- a unit edit (the unit FOR UPDATE, then its tickets counted LOCK IN SHARE MODE, masters.py)
  against any move of a ticket in that unit (the ticket, then the unit's shared FK lock at
  its state change).  The moves include schedule and the start from scheduled (S019 § 5.6);
  change plan keeps the state, so its index entries and foreign-key checks do not change.
A failure code's code change (masters.py) locks the code row FOR UPDATE, then counts its
tickets with a shared-lock read: a ticket write holding the code's FK lock commits first and is
counted, a later one queues behind the code's lock, so "code frozen once used" is race-free
(modes S017, causes and actions S018 § 5.6).  A deactivation is not, and need not be: an
inactive code stays on tickets that already use it.

Import direction: documents.py imports the ticket owner's read and lock functions from here;
this module never imports documents.py.
"""

from datetime import datetime

from flask import Blueprint, jsonify, request

from api_common import (
    DEFAULT_PER_PAGE, MAX_PAGE, MAX_PER_PAGE, UNIQUE_KEY_ERRORS, ApiError, actor, clean_body, enum_arg, int_arg,
    like_pattern,
)
from auth_utils import check_perm, current_person_id, has_perm, has_perm_at, permissions_at_site, require_perm, require_perm_at
import alerts
from alerts_core import ASSIGNED_ALERT, close_alert, raise_alert, regrade_alert, send_back_alert
from config_rbac import ASSIGNABLE_ROLES
from db_helpers import count, get_db, insert_row, next_counter, row_to_dict, rows_to_list, transaction, update_row
from equipment import IST, accessible_unit_ids, load_node_for_user
from equipment_core import SCRAPPED
from tickets_core import (
    ACTION_NEEDED, ASSIGN_KEY, ASSIGNED_EVENT, AUTO_ASSIGN_MOVES, EDIT_NOTES_KEY, EVENT_LABELS, MACHINE_STOPPED_MOVES,
    MACHINE_STOPPED_NEEDED, NOTE_EVENT, NOTHING_TO_CHANGE, PART_NODE_NEEDED, PARTS_HINT_ACTION_CODES, PARTS_NOT_A_FAULT,
    CAUSE_NEEDED, CLOSED, EDITED_EVENT, IN_PROGRESS, INTENSITY_FILTERS, MACHINE_LEVEL, MOVES, OPEN_STATES,
    ORDERED_EVENTS, PLAN_FILTERS, RAISED, REGRADE_STATES, REGRADED_EVENT, REPEAT_WINDOW_DAYS,
    RAISE_SCREEN_LABELS, RESTORE_FIELD_PREFIX, RESTORE_KEY, SCHEDULED,
    STARTED_EVENT, STATE_FILTERS, UNASSIGNED_EVENT, WORK_KEY, allowed_moves, description_error, edit_lines,
    format_ticket_serial, is_breakdown, is_overdue, is_repeat_candidate, latest_restoration, machine_and_component,
    machine_stopped_needed, planned_date_error, regrade_options,
    send_back_error, send_back_intensity, serial_scope, started_at_error, ticket_times, trade_error, validate_assignee,
    backdate_days, validate_close, validate_edit, validate_event_time, validate_labour, validate_move, validate_raise,
    validate_note, validate_part, validate_regrade, validate_regrade_body,
)

tickets_bp = Blueprint("tickets", __name__)

UNIQUE_KEY_ERRORS.update({
    "uq_tickets_serial": (None, "Serial collision — retry"),
})

READ_KEY = "ticket:read"
RAISE_KEY = "ticket:raise"
BACKDATE_KEY = "ticket:backdate"   # S028: times older than 7 days; held by admin only

SCRAPPED_NO_TICKETS = "Scrapped equipment takes no tickets"
TICKET_CLOSED = "This ticket is closed"
TICKET_CHANGED = "This ticket changed — reload"
PERSON_AT_SITE = "Choose a person from this site"
ASSIGNEE_AT_SITE = "Choose a technician, engineer or manager at this site"
COMPONENT_OF_MACHINE = "Choose a component of this machine"
TRADE_FROM_LIST = "Choose a trade from the list"
REPEAT_UNKNOWN = "Choose the earlier ticket"
REPEAT_OTHER_MACHINE = "The earlier ticket is on another machine"
REPEAT_NOT_RESTORED = "That ticket can't be repeated: it is not back in service"
REPEAT_NOT_RECENT = (f"Not a repeat: the earlier ticket was not back in service within {REPEAT_WINDOW_DAYS} days"
                     " before this one")

# The edit's timeline lines, in this order (§ 1 Edit)
_EDIT_LABELS = {"component": "Component", "failure_mode": "Symptom", "description": "Description"}

_TICKET_FROM = (
    " FROM tickets t"
    " JOIN equipment m ON m.id = t.equipment_id"
    " JOIN equipment_classes mc ON mc.id = m.class_id"
    " LEFT JOIN equipment c ON c.id = t.component_id"
    " JOIN units u ON u.id = t.unit_id"
    " JOIN sites s ON s.id = u.site_id"
    " LEFT JOIN failure_modes f ON f.id = t.failure_mode_id"
    " LEFT JOIN people rp ON rp.id = t.reported_by_id"
    " LEFT JOIN failure_causes fc ON fc.id = t.cause_id"
    " LEFT JOIN maintenance_actions ma ON ma.id = t.action_id"
    " LEFT JOIN tickets rt ON rt.id = t.repeat_of_id"
)
_TICKET_COLUMNS = (
    "SELECT t.id, t.serial, t.state, t.intensity, t.occurred_at, t.created_at, t.created_by, t.description,"
    " t.not_a_fault, t.unit_id, u.code AS unit_code, s.id AS site_id, s.code AS site_code,"
    " m.id AS m_id, m.code AS m_code, m.name AS m_name, m.class_id AS m_class_id, mc.code AS m_class_code,"
    " c.id AS c_id, c.code AS c_code, c.name AS c_name,"
    " f.id AS f_id, f.code AS f_code, f.label AS f_label, rp.id AS rp_id, rp.name AS rp_name,"
    " fc.id AS fc_id, fc.code AS fc_code, fc.label AS fc_label, ma.id AS ma_id, ma.code AS ma_code,"
    " ma.label AS ma_label, rt.id AS rt_id, rt.serial AS rt_serial, t.planned_date, t.waiting_reason"
)


def _now():
    """The IST wall clock, naive, as every DATETIME is stored (base § Timezone policy)."""
    return datetime.now(IST).replace(tzinfo=None)


def _max_back_days(now):
    """How far back this user may enter a time today (S028)."""
    return backdate_days(now, has_perm(BACKDATE_KEY))


def _today():
    """The IST date of now: the planned date's rules and *overdue* (S019 § 5.1, § 5.5)."""
    return _now().date()


# ---------------------------------------------------------------------------
# Access and shaping
# ---------------------------------------------------------------------------

def _visible_condition(cur):
    """The access predicate (§ 5.3) as ``(sql, params)`` over ``t`` and ``m``; None when the
    user may see no ticket at all (an empty IN () would be an SQL error)."""
    unit_ids = accessible_unit_ids(cur, READ_KEY)
    if unit_ids is None:
        return "1 = 1", []
    if not unit_ids:
        return None
    ids = sorted(unit_ids)
    placeholders = ", ".join(["%s"] * len(ids))
    return f"(t.unit_id IN ({placeholders}) OR m.unit_id IN ({placeholders}))", ids + ids


def _code_ref(row, prefix):
    """``{id, code, label}`` of a joined code (mode, cause, action), or None."""
    if row[f"{prefix}_id"] is None:
        return None
    return {"id": row[f"{prefix}_id"], "code": row[f"{prefix}_code"], "label": row[f"{prefix}_label"]}


def _ticket_out(row, today):
    """The ticket as the list and the detail show it; ``today`` (IST) decides *overdue*."""
    plain = row_to_dict(row)
    return {
        "id": plain["id"],
        "serial": plain["serial"],
        "state": plain["state"],
        "intensity": plain["intensity"],
        "is_breakdown": is_breakdown(plain["intensity"]),
        "occurred_at": plain["occurred_at"],
        "created_at": plain["created_at"],
        "created_by": plain["created_by"],
        "machine": {"id": plain["m_id"], "code": plain["m_code"], "name": plain["m_name"],
                    "class_code": plain["m_class_code"]},
        "component": ({"id": plain["c_id"], "code": plain["c_code"], "name": plain["c_name"]}
                      if plain["c_id"] is not None else None),
        "unit": {"id": plain["unit_id"], "code": plain["unit_code"], "site_code": plain["site_code"]},
        "failure_mode": _code_ref(plain, "f"),
        "description": plain["description"],
        "reported_by": {"id": plain["rp_id"], "name": plain["rp_name"]} if plain["rp_id"] is not None else None,
        "cause": _code_ref(plain, "fc"),
        "action": _code_ref(plain, "ma"),
        "not_a_fault": bool(plain["not_a_fault"]),
        "repeat_of": {"id": plain["rt_id"], "serial": plain["rt_serial"]} if plain["rt_id"] is not None else None,
        # S019: the current plan, set only while scheduled
        "planned_date": plain["planned_date"],
        "waiting_reason": plain["waiting_reason"],
        "overdue": is_overdue(row["state"], row["planned_date"], today),
    }


def _find_ticket(cur, ticket_id):
    """Plain read of one ticket through the access predicate -> the row, or None."""
    visible = _visible_condition(cur)
    if visible is None:
        return None
    condition, params = visible
    cur.execute(f"{_TICKET_COLUMNS}{_TICKET_FROM} WHERE t.id = %s AND {condition}", [ticket_id, *params])
    return cur.fetchone()


def read_ticket(cur, ticket_id, _key=None):
    """Plain read of one ticket through the access predicate; 404 when missing or not
    visible, as equipment answers.  Also documents.py's ticket owner ``read``."""
    row = _find_ticket(cur, ticket_id)
    if row is None:
        raise ApiError("Not found", 404)
    return row


def _event_rows(cur, ticket_id):
    """The ticket's events, oldest first, as stored (datetimes, for ticket_times).  ``id`` names
    a note for its correction; ``updated_*`` is set on a corrected note only (S027)."""
    cur.execute("SELECT e.id, e.event, e.from_state, e.to_state, e.occurred_at, e.intensity, e.remark, e.created_at,"
                " e.created_by, e.updated_at, e.updated_by, e.planned_date, e.waiting_reason, e.machine_stopped,"
                " p.id AS person_id, p.name AS person_name FROM ticket_events e"
                " LEFT JOIN people p ON p.id = e.person_id WHERE e.ticket_id = %s"
                " ORDER BY e.occurred_at, e.id", (ticket_id,))
    return cur.fetchall()


def _note_edits(cur, ticket_id):
    """The earlier texts of the ticket's notes, in one query (S027 § 3) -> ``{event_id: [{remark,
    replaced_at, replaced_by}, …]}``, newest first.  The detail path only: the repeat checks read
    _event_rows and need none of it (BR1-11)."""
    cur.execute("SELECT ne.event_id, ne.remark, ne.replaced_at, ne.replaced_by FROM ticket_note_edits ne"
                " JOIN ticket_events e ON e.id = ne.event_id WHERE e.ticket_id = %s ORDER BY ne.id DESC",
                (ticket_id,))
    edits = {}
    for row in rows_to_list(cur.fetchall()):
        edits.setdefault(row.pop("event_id"), []).append(row)
    return edits


def _events_out(rows, note_edits):
    """The timeline as the page shows it; each note carries ``earlier`` (empty when never
    corrected)."""
    events = []
    for row in rows_to_list(rows):
        person_id, person_name = row.pop("person_id"), row.pop("person_name")
        row["person"] = {"id": person_id, "name": person_name} if person_id is not None else None
        if row["machine_stopped"] is not None:
            row["machine_stopped"] = bool(row["machine_stopped"])
        if row["event"] == NOTE_EVENT:
            row["earlier"] = note_edits.get(row["id"], [])
        events.append(row)
    return events


def _assignees(cur, ticket_ids):
    """``{ticket_id: [{id, name}, ...]}`` in the order they were assigned; every id present."""
    result = {ticket_id: [] for ticket_id in ticket_ids}
    if ticket_ids:
        cur.execute("SELECT a.ticket_id, p.id, p.name FROM ticket_assignees a JOIN people p ON p.id = a.person_id"
                    f" WHERE a.ticket_id IN ({', '.join(['%s'] * len(ticket_ids))})"
                    " ORDER BY a.assigned_at, p.name, p.id", list(ticket_ids))
        for row in cur.fetchall():
            result[row["ticket_id"]].append({"id": row["id"], "name": row["name"]})
    return result


def _labour(cur, ticket_id):
    cur.execute("SELECT l.id, l.work_date, l.minutes, l.created_at, l.created_by, p.id AS person_id,"
                " p.name AS person_name, tr.id AS trade_id, tr.name AS trade_name FROM ticket_labour l"
                " JOIN people p ON p.id = l.person_id LEFT JOIN trades tr ON tr.id = l.trade_id"
                " WHERE l.ticket_id = %s ORDER BY l.work_date, l.id", (ticket_id,))
    rows = []
    for row in rows_to_list(cur.fetchall()):
        rows.append({
            "id": row["id"], "work_date": row["work_date"], "minutes": row["minutes"],
            "person": {"id": row["person_id"], "name": row["person_name"]},
            "trade": {"id": row["trade_id"], "name": row["trade_name"]} if row["trade_id"] is not None else None,
            "created_at": row["created_at"], "created_by": row["created_by"],
        })
    return rows


def _parts(cur, ticket_id):
    """The parts lines (S020), in the order entered, each with the node it was fitted to.  The
    quantity goes out as a string ("1.50"), so no float rounding on the way."""
    cur.execute("SELECT p.id, p.description, p.part_number, p.number_kind, p.maker, p.quantity, p.qty_unit,"
                " p.created_at, p.created_by, n.id AS node_id, n.code AS node_code, n.name AS node_name"
                " FROM ticket_parts p JOIN equipment n ON n.id = p.node_id WHERE p.ticket_id = %s ORDER BY p.id",
                (ticket_id,))
    return [{
        "id": row["id"], "description": row["description"], "part_number": row["part_number"],
        "number_kind": row["number_kind"], "maker": row["maker"], "quantity": str(row["quantity"]),
        "qty_unit": row["qty_unit"], "node": {"id": row["node_id"], "code": row["node_code"], "name": row["node_name"]},
        "created_at": row["created_at"], "created_by": row["created_by"],
    } for row in rows_to_list(cur.fetchall())]


def _parts_hint_actions(cur):
    """The ids of the actions whose close shows "No parts recorded" (S020 § 1.6), active or
    not: a retired code keeps its hint while old tickets still carry it."""
    placeholders = ", ".join(["%s"] * len(PARTS_HINT_ACTION_CODES))
    cur.execute(f"SELECT id FROM maintenance_actions WHERE code IN ({placeholders}) ORDER BY id",
                PARTS_HINT_ACTION_CODES)
    return [row["id"] for row in cur.fetchall()]


def _repeats(cur, ticket_id):
    """The later tickets raised as repeats of this one, the visible ones (§ 5.5: a query, not
    a stored list)."""
    visible = _visible_condition(cur)
    if visible is None:
        return []
    condition, params = visible
    cur.execute("SELECT t.id, t.serial, t.state, t.occurred_at FROM tickets t JOIN equipment m ON m.id = t.equipment_id"
                f" WHERE t.repeat_of_id = %s AND {condition} ORDER BY t.occurred_at, t.id", [ticket_id, *params])
    return rows_to_list(cur.fetchall())


def _latest_repeat_serial(cur, ticket_id):
    """The serial of the latest ticket raised as a repeat of this one, or None — unfiltered:
    a repeat the user cannot see still forbids the send-back (S025 § 5.2)."""
    cur.execute("SELECT serial FROM tickets WHERE repeat_of_id = %s ORDER BY occurred_at DESC, id DESC LIMIT 1",
                (ticket_id,))
    row = cur.fetchone()
    return row["serial"] if row else None


def _person_at_site(cur, person_id, site_id):
    """An active person with a membership at the site -> ``{id, name, role}``, or None.  The
    role is the person's at that site (memberships), never the user's token."""
    cur.execute("SELECT p.id, p.name, ms.role FROM people p JOIN memberships ms ON ms.person_id = p.id"
                " WHERE p.id = %s AND p.active = 1 AND ms.site_id = %s", (person_id, site_id))
    return cur.fetchone()


def _own_person_at_site(cur, site_id):
    """The user's own person at the site (§ 5.2, § 5.8), or None: no Team record, or no
    membership there (IT admin is a token role)."""
    person_id = current_person_id(cur)
    return None if person_id is None else _person_at_site(cur, person_id, site_id)


def _person_ref(person):
    return {"id": person["id"], "name": person["name"]} if person else None


def _moves(cur, row, keys):
    """allowed_moves for this user, with what each dialog shows: the restore move's
    ``default_person`` (the user's own person, when he holds ticket:work and may be named at the
    site, BR4-03) and acknowledge / start's ``recording_as`` (the person the move will
    auto-assign, BR4-04).  Start and restore carry ``asks_machine_stopped`` (S019 § 6): the
    server will require the answer — on restore, once a start time is given."""
    names = allowed_moves(row["state"], keys, has_repeat=_latest_repeat_serial(cur, row["id"]) is not None)
    own = _own_person_at_site(cur, row["site_id"]) if names else None
    moves = []
    for name in names:
        entry = {"name": name}
        if name == "restore":
            entry["default_person"] = _person_ref(own) if WORK_KEY in keys else None
        elif name in AUTO_ASSIGN_MOVES:
            entry["recording_as"] = _person_ref(own) if own and own["role"] in ASSIGNABLE_ROLES else None
        if name in MACHINE_STOPPED_MOVES:
            entry["asks_machine_stopped"] = machine_stopped_needed(row["state"], row["intensity"])
        if name == "close":
            entry["parts_hint_actions"] = _parts_hint_actions(cur)
        moves.append(entry)
    return moves


def _detail(cur, row):
    """The ticket page's data: the ticket, its timeline and figures, assignees, labour, repeats,
    and what this user may do here — every control from the keys at the ticket's site (§ 7
    decision 13)."""
    ticket_id, state = row["id"], row["state"]
    keys = set(permissions_at_site(row["site_id"]))
    events = _event_rows(cur, ticket_id)
    now = _now()
    is_open = state != CLOSED
    can_regrade = state in REGRADE_STATES and RAISE_KEY in keys
    return {
        **_ticket_out(row, now.date()),
        "events": _events_out(events, _note_edits(cur, ticket_id)),
        "times": ticket_times(events, now),
        "assignees": _assignees(cur, [ticket_id])[ticket_id],
        "labour": _labour(cur, ticket_id),
        "parts": _parts(cur, ticket_id),
        "repeats": _repeats(cur, ticket_id),
        "moves": _moves(cur, row, keys),
        "permissions": sorted(keys),
        "regrade_to": regrade_options(row["intensity"], WORK_KEY in keys) if can_regrade else [],
        "can_add_photos": is_open and RAISE_KEY in keys,
        "can_add_documents": is_open and WORK_KEY in keys,
        # Shown against now; the raise checks the new ticket's own time (§ 5.5)
        "can_raise_repeat": (RAISE_KEY in keys
                             and is_repeat_candidate(latest_restoration(state, row["not_a_fault"], events), now)),
    }


# ---------------------------------------------------------------------------
# The ticket as a documents owner (documents.OWNERS["ticket"], § 5.5): 404 → 403 → 409
# ---------------------------------------------------------------------------

def read_ticket_for_change(cur, ticket_id, key):
    """A write's early refusals from a plain read, so a refused upload reads and writes no
    file: not visible 404, ``key`` not held at the ticket's site 403, closed 409.  The
    decisions that count are lock_ticket_for_change's."""
    row = read_ticket(cur, ticket_id)
    require_perm_at(key, row["site_id"])
    if row["state"] == CLOSED:
        raise ApiError(TICKET_CLOSED, 409)
    return row


# The plan too (S019 BR2-04): Change plan's "Nothing to change" is decided from the locked row
_LOCK_TICKET = ("SELECT id, state, intensity, failure_mode_id, equipment_id, component_id, description,"
                " occurred_at, not_a_fault, planned_date, waiting_reason FROM tickets WHERE id = %s FOR UPDATE")


def _lock_ticket(cur, ticket_id, key):
    """Lock the ticket row (7), then 404 (predicate) and 403 (the key at the ticket's site) ->
    the ticket's row, its state, intensity, mode, machine, component, description and plan
    from the locked read (every refusal is decided from those, S018 § 5.3).  The unit never
    changes, so the plain read for access is as good as the locked row.  ``key`` is a
    permission key, or a function of the locked state that returns one (a move whose key
    depends on where it starts from: Move.key_at, S019 U1) or a set of keys, any one of which
    is enough (a stale move: the state is outside the move's from-states, so no per-state key
    applies and _apply_move answers 409, S019 CR1-01)."""
    cur.execute(_LOCK_TICKET, (ticket_id,))
    locked = cur.fetchone()
    if locked is None:
        raise ApiError("Not found", 404)
    row = read_ticket(cur, ticket_id)
    needed = key(locked["state"]) if callable(key) else key
    if isinstance(needed, str):
        require_perm_at(needed, row["site_id"])
    elif not any(has_perm_at(k, row["site_id"]) for k in needed):
        require_perm_at(sorted(needed)[0], row["site_id"])
    return {**row, **locked}


def _lock_open_ticket(cur, ticket_id, key):
    """_lock_ticket, and a closed ticket 409: closed is final and read-only."""
    ticket = _lock_ticket(cur, ticket_id, key)
    if ticket["state"] == CLOSED:
        raise ApiError(TICKET_CLOSED, 409)
    return ticket


def lock_ticket_for_change(cur, ticket_id, key):
    """In the write transaction: 404, 403, and a closed ticket 409, decided from the locked
    row (upload, title edit, remove and restore alike)."""
    _lock_open_ticket(cur, ticket_id, key)


def lock_ticket_for_purge(cur, ticket_id, key):
    """As lock_ticket_for_change without the closed check: erasing a file is disposition of
    information, not a change to the ticket (S008 § 5.3)."""
    _lock_ticket(cur, ticket_id, key)


# ---------------------------------------------------------------------------
# List and detail
# ---------------------------------------------------------------------------

def _equipment_filter(cur, node_id):
    """``equipment_id``: a machine -> its tickets; a component-unit or component -> the
    tickets raised on that node itself (§ 6).  None when there is no such node."""
    cur.execute("SELECT level FROM equipment WHERE id = %s", (node_id,))
    node = cur.fetchone()
    if node is None:
        return None
    column = "t.equipment_id" if node["level"] == MACHINE_LEVEL else "t.component_id"
    return f"{column} = %s"


@tickets_bp.route("/", strict_slashes=False)
@require_perm(READ_KEY)
def list_tickets():
    page = int_arg("page", 1, minimum=1, maximum=MAX_PAGE)
    per_page = int_arg("per_page", DEFAULT_PER_PAGE, minimum=1, maximum=MAX_PER_PAGE)
    state = enum_arg("state", STATE_FILTERS) or "open"
    intensity = enum_arg("intensity", tuple(INTENSITY_FILTERS))
    assigned = enum_arg("assigned", ("me",))
    raised = enum_arg("raised", ("me",))
    site_id = int_arg("site_id", None, minimum=1)
    unit_id = int_arg("unit_id", None, minimum=1)
    equipment_id = int_arg("equipment_id", None, minimum=1)
    q = (request.args.get("q") or "").strip()

    empty = {"items": [], "total": 0, "page": page, "per_page": per_page}
    today = _today()
    with get_db().cursor() as cur:
        visible = _visible_condition(cur)
        if visible is None:
            return jsonify(empty)
        conditions, params = [visible[0]], list(visible[1])
        if state == "open":
            conditions.append(f"t.state IN ({', '.join(['%s'] * len(OPEN_STATES))})")
            params.extend(OPEN_STATES)
        elif state == "closed":
            conditions.append("t.state = %s")
            params.append(CLOSED)
        elif state in PLAN_FILTERS:
            conditions.append("t.state = %s")
            params.append(SCHEDULED)
            if state == "overdue":
                # tickets_core.is_overdue in SQL (S019 § 5.5)
                conditions.append("t.planned_date < %s")
                params.append(today)
        if intensity:
            values = INTENSITY_FILTERS[intensity]
            conditions.append(f"t.intensity IN ({', '.join(['%s'] * len(values))})")
            params.extend(values)
        if assigned:
            # Assigned to me (S018 § 1): a user with no Team record is assigned nothing
            person_id = current_person_id(cur)
            if person_id is None:
                return jsonify(empty)
            conditions.append("EXISTS (SELECT 1 FROM ticket_assignees a WHERE a.ticket_id = t.id"
                              " AND a.person_id = %s)")
            params.append(person_id)
        if raised:
            # Raised by me (S031 § 5.2): I pressed Raise, or someone raised it naming me the reporter
            person_id = current_person_id(cur)
            if person_id is None:
                conditions.append("t.created_by = %s")
                params.append(actor())
            else:
                conditions.append("(t.created_by = %s OR t.reported_by_id = %s)")
                params.extend([actor(), person_id])
        if site_id is not None:
            conditions.append("s.id = %s")
            params.append(site_id)
        if unit_id is not None:
            conditions.append("t.unit_id = %s")
            params.append(unit_id)
        if equipment_id is not None:
            condition = _equipment_filter(cur, equipment_id)
            if condition is None:
                return jsonify(empty)
            conditions.append(condition)
            params.append(equipment_id)
        if q:
            conditions.append("(t.serial LIKE %s OR t.description LIKE %s)")
            params.extend([like_pattern(q)] * 2)
        # Open: what is down and waiting longest leads (the ENUM's order puts critical first);
        # within an intensity the scheduled rows come after the ones someone can act on now
        # (S019 § 1.6, BR1-04).  Scheduled and overdue: what is due next, the most overdue
        # first.  Closed and all: newest first (§ 5.3).  In SQL, because the list is paginated.
        if state == "open":
            order = f"t.intensity, t.state = '{SCHEDULED}', t.occurred_at, t.id"
        elif state in PLAN_FILTERS:
            order = "t.planned_date, t.id"
        else:
            order = "t.occurred_at DESC, t.id DESC"
        where = " AND ".join(conditions)
        total = count(cur, f"SELECT COUNT(*) AS n{_TICKET_FROM} WHERE {where}", params)
        cur.execute(f"{_TICKET_COLUMNS}{_TICKET_FROM} WHERE {where} ORDER BY {order} LIMIT %s OFFSET %s",
                    [*params, per_page, (page - 1) * per_page])
        rows = cur.fetchall()
        assignees = _assignees(cur, [row["id"] for row in rows])
        items = [{**_ticket_out(row, today), "assignees": assignees[row["id"]]} for row in rows]
    return jsonify({"items": items, "total": total, "page": page, "per_page": per_page})


@tickets_bp.route("/activity")
@require_perm(READ_KEY)
def list_activity():
    """My activity (S031 § 5.2): the timeline lines I recorded (``created_by`` is my login) on
    tickets I may see, newest recorded first.  ``/<int:ticket_id>`` matches digits only, so the
    two routes do not collide."""
    page = int_arg("page", 1, minimum=1, maximum=MAX_PAGE)
    per_page = int_arg("per_page", DEFAULT_PER_PAGE, minimum=1, maximum=MAX_PER_PAGE)
    with get_db().cursor() as cur:
        visible = _visible_condition(cur)
        if visible is None:
            return jsonify({"items": [], "total": 0, "page": page, "per_page": per_page})
        from_where = (" FROM ticket_events e JOIN tickets t ON t.id = e.ticket_id"
                      " JOIN equipment m ON m.id = t.equipment_id"
                      " LEFT JOIN people p ON p.id = e.person_id"
                      f" WHERE e.created_by = %s AND {visible[0]}")
        params = [actor(), *visible[1]]
        total = count(cur, f"SELECT COUNT(*) AS n{from_where}", params)
        cur.execute("SELECT e.id, e.event, e.occurred_at, e.created_at, e.intensity, e.remark, e.planned_date,"
                    " e.waiting_reason, p.id AS person_id, p.name AS person_name, t.id AS ticket_id, t.serial,"
                    " t.intensity AS ticket_intensity, t.state AS ticket_state,"
                    " m.id AS m_id, m.code AS m_code, m.name AS m_name"
                    f"{from_where}"
                    " ORDER BY e.created_at DESC, e.id DESC LIMIT %s OFFSET %s",
                    [*params, per_page, (page - 1) * per_page])
        items = []
        for row in rows_to_list(cur.fetchall()):
            items.append({
                "id": row["id"], "event": row["event"], "occurred_at": row["occurred_at"],
                "created_at": row["created_at"], "intensity": row["intensity"], "remark": row["remark"],
                "planned_date": row["planned_date"], "waiting_reason": row["waiting_reason"],
                "person": ({"id": row["person_id"], "name": row["person_name"]}
                           if row["person_id"] is not None else None),
                "ticket": {"id": row["ticket_id"], "serial": row["serial"], "intensity": row["ticket_intensity"],
                           "state": row["ticket_state"],
                           "machine": {"id": row["m_id"], "code": row["m_code"], "name": row["m_name"]}},
            })
    return jsonify({"items": items, "total": total, "page": page, "per_page": per_page})


@tickets_bp.route("/<int:ticket_id>")
@require_perm(READ_KEY)
def get_ticket(ticket_id):
    with get_db().cursor() as cur:
        return jsonify(_detail(cur, read_ticket(cur, ticket_id)))


# ---------------------------------------------------------------------------
# The pickers — anchored on the node raised on (the raise screen) or on a ticket (S018)
# ---------------------------------------------------------------------------

def _machine_class_id(cur, node):
    """The class of the node's machine: the node's own, or its machine's (a plain read)."""
    machine_id, component_id = machine_and_component(node)
    if component_id is None:
        return node["class_id"]
    cur.execute("SELECT class_id FROM equipment WHERE id = %s", (machine_id,))
    return cur.fetchone()["class_id"]


def _picker_anchor(cur):
    """``?ticket_id=`` (S018: the ticket by the access predicate, 404; ticket:read at the
    ticket's site, 403) or ``?equipment_id=`` (S017: the node, checked as the raise is) ->
    ``(site_id, the machine's class_id)``.  One of them is required."""
    ticket_id = int_arg("ticket_id", None, minimum=1)
    if ticket_id is not None:
        row = read_ticket(cur, ticket_id)
        require_perm_at(READ_KEY, row["site_id"])
        return row["site_id"], row["m_class_id"]
    node_id = int_arg("equipment_id", None, minimum=1)
    if node_id is None:
        raise ApiError("equipment_id or ticket_id is required", 400, "equipment_id")
    _, node = load_node_for_user(cur, node_id, for_update=False, key=RAISE_KEY)
    return node["site_id"], _machine_class_id(cur, node)


@tickets_bp.route("/modes")
@require_perm(RAISE_KEY)
def list_modes():
    """The symptoms a ticket offers: the active modes of its machine's class, then the active
    General ones, each by label (S016 § 5.2).  The machine's, even for a component: the
    operator does not know the component's class.  On a ticket, its machine's class now, so the
    close and edit dialogs work after the machine moved (S018 BS1-08)."""
    with get_db().cursor() as cur:
        _, class_id = _picker_anchor(cur)
        cur.execute("SELECT id, code, label, description, class_id FROM failure_modes"
                    " WHERE active = 1 AND (class_id = %s OR class_id IS NULL)"
                    " ORDER BY class_id IS NULL, label", (class_id,))
        items = cur.fetchall()
    return jsonify({"items": items})


def _people_at_site(cur, site_id):
    """Active people with a membership at the site, by name, with their active trades
    ``[{id, name}]``, their role there and whether that role may be assigned (§ 5.8): the one
    people picker (reported by, the back-in-service person, labour, assignees)."""
    cur.execute("SELECT p.id, p.name, ms.role FROM people p JOIN memberships ms ON ms.person_id = p.id"
                " WHERE ms.site_id = %s AND p.active = 1 ORDER BY p.name, p.id", (site_id,))
    people = [{**row, "assignable": row["role"] in ASSIGNABLE_ROLES, "trades": []} for row in cur.fetchall()]
    if people:
        by_id = {person["id"]: person for person in people}
        cur.execute("SELECT pt.person_id, t.id, t.name FROM person_trades pt JOIN trades t ON t.id = pt.trade_id"
                    f" WHERE t.active = 1 AND pt.person_id IN ({', '.join(['%s'] * len(by_id))}) ORDER BY t.name",
                    list(by_id))
        for row in cur.fetchall():
            by_id[row["person_id"]]["trades"].append({"id": row["id"], "name": row["name"]})
    return people


@tickets_bp.route("/people")
@require_perm(RAISE_KEY)
def list_people():
    """People who can be named on a ticket: at the node's current site (raise), or at the
    ticket's site (S018).  Names only, and only where the user may raise or read tickets
    (ISO 27001 A.5.15)."""
    with get_db().cursor() as cur:
        site_id, _ = _picker_anchor(cur)
        return jsonify({"items": _people_at_site(cur, site_id)})


# ---------------------------------------------------------------------------
# Checks shared by raise and work
# ---------------------------------------------------------------------------

def _check_mode(cur, mode_id, machine_class_id, field="failure_mode_id"):
    """The picked symptom: active, and General or of the machine's class -> its row (code, label)."""
    cur.execute("SELECT id, code, label, class_id, active FROM failure_modes WHERE id = %s", (mode_id,))
    mode = cur.fetchone()
    if (mode is None or not mode["active"]
            or (mode["class_id"] is not None and mode["class_id"] != machine_class_id)):
        raise ApiError("Choose a symptom from the list", 400, field)
    return mode


def _check_person(cur, person_id, site_id, field):
    """An active person with a membership at the site (operators without a login included,
    S017 user decision 5; S018 § 5.8) -> ``{id, name, role}``; 400 on ``field`` otherwise."""
    person = _person_at_site(cur, person_id, site_id)
    if person is None:
        raise ApiError(PERSON_AT_SITE, 400, field)
    return person


def _check_active_code(cur, table, code_id, field, message):
    """A cause or action picked at close: it exists and is active.  ``table`` is a code constant."""
    cur.execute(f"SELECT active FROM {table} WHERE id = %s", (code_id,))
    row = cur.fetchone()
    if row is None or not row["active"]:
        raise ApiError(message, 400, field)


def _check_repeat(cur, repeat_of_id, machine_id, occurred_at):
    """§ 5.5: the earlier ticket is readable, on the same machine, stands back in service or closed (not as
    a not-a-fault), and its latest back in service
    lies at most REPEAT_WINDOW_DAYS before the new ticket's time and not after it.  Read plain:
    the new ticket points at it, nothing on it changes."""
    earlier = _find_ticket(cur, repeat_of_id)
    if earlier is None:
        raise ApiError(REPEAT_UNKNOWN, 400, "repeat_of_id")
    if earlier["m_id"] != machine_id:
        raise ApiError(REPEAT_OTHER_MACHINE, 400, "repeat_of_id")
    restored_at = latest_restoration(earlier["state"], earlier["not_a_fault"], _event_rows(cur, repeat_of_id))
    if restored_at is None:
        raise ApiError(REPEAT_NOT_RESTORED, 400, "repeat_of_id")
    if not is_repeat_candidate(restored_at, occurred_at):
        raise ApiError(REPEAT_NOT_RECENT, 400, "repeat_of_id")


def _recheck_repeat(cur, repeat_of_id):
    """After the insert: the earlier ticket's state read again under the shared lock its
    foreign key already holds (S025 § 5.2).  A send-back committed since _check_repeat's
    plain read is seen here, and the raise is refused and rolled back."""
    cur.execute("SELECT state, not_a_fault FROM tickets WHERE id = %s LOCK IN SHARE MODE", (repeat_of_id,))
    earlier = cur.fetchone()
    if latest_restoration(earlier["state"], earlier["not_a_fault"], _event_rows(cur, repeat_of_id)) is None:
        raise ApiError(REPEAT_NOT_RESTORED, 400, "repeat_of_id")


# ---------------------------------------------------------------------------
# Raise
# ---------------------------------------------------------------------------

@tickets_bp.route("/", methods=["POST"], strict_slashes=False)
@require_perm(RAISE_KEY)
def raise_ticket():
    now = _now()
    max_back_days = _max_back_days(now)
    clean = clean_body(lambda body, _creating: validate_raise(body, now, max_back_days), creating=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        # (1) the node; 404 outside the user's units; 403 unless ticket:raise at its site
        locked, node = load_node_for_user(cur, clean["equipment_id"], for_update=True, key=RAISE_KEY)
        if locked["lifecycle"] == SCRAPPED:
            raise ApiError(SCRAPPED_NO_TICKETS, 409)
        if clean["restore"] is not None:
            # A1: back in service needs its own key at the node's site, checked before the insert
            require_perm_at(RESTORE_KEY, node["site_id"])
        machine_id, component_id = machine_and_component(node)
        if component_id is None:
            machine = locked
        else:
            # Ancestors are read plain, never locked.  Through the API a machine is scrapped
            # only after its parts, so this is defence in depth.
            cur.execute("SELECT id, lifecycle, unit_id, class_id FROM equipment WHERE id = %s", (machine_id,))
            machine = cur.fetchone()
            if machine["lifecycle"] == SCRAPPED:
                raise ApiError(SCRAPPED_NO_TICKETS, 409)

        mode_code = None
        if clean["failure_mode_id"] is not None:
            mode_code = _check_mode(cur, clean["failure_mode_id"], machine["class_id"])["code"]
        message = description_error(clean["description"], mode_code)
        if message:
            raise ApiError(message, 400, "description")
        if clean["reported_by_id"] is not None:
            _check_person(cur, clean["reported_by_id"], node["site_id"], "reported_by_id")
        if clean["repeat_of_id"] is not None:
            _check_repeat(cur, clean["repeat_of_id"], machine_id, clean["occurred_at"])

        # (6) the serial, from the IST raise date, in this transaction: a failed raise leaves no gap
        serial = format_ticket_serial(now.year, now.month, next_counter(cur, serial_scope(now.year, now.month)))
        ticket_id = insert_row(cur, "tickets", {
            "serial": serial,
            "equipment_id": machine_id,
            "component_id": component_id,
            "unit_id": machine["unit_id"],
            "intensity": clean["intensity"],
            "failure_mode_id": clean["failure_mode_id"],
            "description": clean["description"],
            "reported_by_id": clean["reported_by_id"],
            "repeat_of_id": clean["repeat_of_id"],
            "occurred_at": clean["occurred_at"],
        }, actor())
        raised_event_id = _add_event(cur, ticket_id, RAISED, clean["occurred_at"], to_state=RAISED,
                                     intensity=clean["intensity"])
        if clean["repeat_of_id"] is not None:
            _recheck_repeat(cur, clean["repeat_of_id"])
        if clean["restore"] is not None:
            # A1, *Already fixed*: the restore move's own code on the new row (no lock needed: the
            # row is this transaction's own); a refusal rolls the whole raise back
            _apply_move(cur, read_ticket(cur, ticket_id), "restore", clean["restore"], now, RESTORE_FIELD_PREFIX)
        else:
            # S021 § 5.3: a breakdown alerts and escalates, a defect alerts quietly; *Already fixed*
            # sends nothing (nothing needs a response).  After the refusals above, so a refused
            # raise rolls the task rows back with it (BS1-09).
            alerts.enqueue_alert(cur, ticket_id, raise_alert(clean["intensity"], now - clean["occurred_at"]), raised_event_id,
                                 current_person_id(cur), clean["reported_by_id"], now)
        # Read inside the transaction, as documents.py does: nothing after the commit can
        # turn this answer into an error
        detail = _detail(cur, read_ticket(cur, ticket_id))
    return jsonify(detail), 201


# ---------------------------------------------------------------------------
# Working the ticket (S018) — every write: lock (7) → 404 → 403 at the ticket's site → 409
# ---------------------------------------------------------------------------

def _add_event(cur, ticket_id, event, occurred_at, from_state=None, to_state=None, intensity=None, person_id=None,
               remark=None, planned_date=None, waiting_reason=None, machine_stopped=None):
    """Write one timeline line -> its id (an alert names the event that caused it, S021 BR1-12)."""
    return insert_row(cur, "ticket_events", {
        "ticket_id": ticket_id, "event": event, "from_state": from_state, "to_state": to_state,
        "occurred_at": occurred_at, "intensity": intensity, "person_id": person_id, "remark": remark,
        "planned_date": planned_date, "waiting_reason": waiting_reason, "machine_stopped": machine_stopped,
    }, actor())


def _last_ordered_event(cur, ticket_id):
    """The latest event that moved the state or the intensity -> ``(event, occurred_at)``; every
    ticket has its raised event."""
    cur.execute(f"SELECT event, occurred_at FROM ticket_events WHERE ticket_id = %s"
                f" AND event IN ({', '.join(['%s'] * len(ORDERED_EVENTS))}) ORDER BY occurred_at DESC, id DESC"
                " LIMIT 1", (ticket_id, *ORDERED_EVENTS))
    row = cur.fetchone()
    return row["event"], row["occurred_at"]


def _event_time(entered, last, now, field):
    """The time an ordered event is recorded at: the entered one, inside the window after the
    last event (400 naming it), or the server's clock (§ 5.1) — never before the last event,
    which may lie up to FUTURE_SKEW ahead of the clock."""
    if entered is None:
        return max(now, last[1])
    # The raise's own fixed-already times are shown beside the raise screen's fields, which have other names
    labels = RAISE_SCREEN_LABELS if field.startswith(RESTORE_FIELD_PREFIX) else EVENT_LABELS
    message = validate_event_time(entered, last, now, _max_back_days(now), labels)
    if message:
        raise ApiError(message, 400, field)
    return entered


def _ticket_response(cur, ticket_id):
    """The detail, read inside the write's transaction (as the raise)."""
    return _detail(cur, read_ticket(cur, ticket_id))


def _assign(cur, ticket_id, person_id, occurred_at):
    """Add an assignee with its *assigned* line -> the line's id; already assigned -> no change
    (None)."""
    cur.execute("SELECT 1 FROM ticket_assignees WHERE ticket_id = %s AND person_id = %s", (ticket_id, person_id))
    if cur.fetchone():
        return None
    cur.execute("INSERT INTO ticket_assignees (ticket_id, person_id, assigned_by) VALUES (%s, %s, %s)",
                (ticket_id, person_id, actor()))
    return _add_event(cur, ticket_id, ASSIGNED_EVENT, occurred_at, person_id=person_id)


def _auto_assign(cur, ticket, occurred_at):
    """Acknowledge / start by a user whose own person is assignable at the ticket's site adds
    him, as a manual assignment would (§ 5.8); anyone else is simply not added."""
    own = _own_person_at_site(cur, ticket["site_id"])
    if own and own["role"] in ASSIGNABLE_ROLES:
        _assign(cur, ticket["id"], own["id"], occurred_at)


def _machine_stopped(ticket, clean, prefix):
    """S019 § 5.3: "was the machine stopped for this work?" for the *started* event -> the
    answer, or None where it is not asked (a value sent is then ignored); 400 when asked and
    not answered."""
    if not machine_stopped_needed(ticket["state"], ticket["intensity"]):
        return None
    if clean["machine_stopped"] is None:
        raise ApiError(MACHINE_STOPPED_NEEDED, 400, f"{prefix}machine_stopped")
    return clean["machine_stopped"]


def _start(_cur, ticket, clean, _occurred_at, _last, _now, prefix):
    """Start: from scheduled on a ticket that is not critical, the stopped answer on the event."""
    return {"machine_stopped": _machine_stopped(ticket, clean, prefix)}, {}


def _restore(cur, ticket, clean, occurred_at, last, now, prefix):
    """Back in service: the named person (anyone at the site), and the start time after the
    fact, written as a *started* event before it with the same person (and, from scheduled on a
    defect, the stopped answer, S019 § 5.3) -> the event's fields.  ``prefix`` names the
    refusals (``restore.`` from the raise, A1)."""
    person = _check_person(cur, clean["person_id"], ticket["site_id"], f"{prefix}person_id")
    from_state = ticket["state"]
    if clean["started_at"] is not None:
        started_at = _event_time(clean["started_at"], last, now, f"{prefix}started_at")
        message = started_at_error(started_at, from_state, occurred_at)
        if message:
            raise ApiError(message, 400, f"{prefix}started_at")
        _add_event(cur, ticket["id"], STARTED_EVENT, started_at, from_state, IN_PROGRESS, person_id=person["id"],
                   machine_stopped=_machine_stopped(ticket, clean, prefix))
        from_state = IN_PROGRESS
    return {"from_state": from_state, "person_id": person["id"]}, {}


def _schedule(_cur, _ticket, clean, _occurred_at, _last, now, _prefix):
    """Schedule (S019 § 5.1): the planned date today or later, within a year (today is the IST
    date of now, never the event's time, BR1-05) -> the plan, on the event and the ticket."""
    message = planned_date_error(clean["planned_date"], now.date())
    if message:
        raise ApiError(message, 400, "planned_date")
    plan = {"planned_date": clean["planned_date"], "waiting_reason": clean["waiting_reason"]}
    return plan, dict(plan)


def _reschedule(cur, ticket, clean, occurred_at, last, now, prefix):
    """Change plan (S019 § 5.2): the date rule first — an overdue plan needs a new date, even
    when only the reason changes (BR2-07) — then the date or the reason must differ from the
    locked row's."""
    event, plan = _schedule(cur, ticket, clean, occurred_at, last, now, prefix)
    if (plan["planned_date"], plan["waiting_reason"]) == (ticket["planned_date"], ticket["waiting_reason"]):
        raise ApiError(NOTHING_TO_CHANGE, 400)
    return event, plan


def _send_back(cur, ticket, clean, *_args):
    """Send back: refused once the ticket came back as a repeat (S025 § 5.2, checked under the
    ticket's lock, so a raise of a repeat and a send-back cannot both succeed); the intensity
    follows "machine down again?" (decision 4), on the sent_back event."""
    repeat_serial = _latest_repeat_serial(cur, ticket["id"])
    message = send_back_error(repeat_serial is not None, repeat_serial)
    if message:
        raise ApiError(message, 409)
    new = send_back_intensity(ticket["intensity"], clean["machine_down"])
    if new is None:
        return {}, {}
    return {"intensity": new}, {"intensity": new}


def _close(cur, ticket, clean, occurred_at, *_args):
    """Close: symptom (the ticket's or a correction, the S016 class rule), labour, active cause
    and action, the description rule.  A changed symptom is an *edited* line before *closed*."""
    labour = count(cur, "SELECT COUNT(*) AS n FROM ticket_labour WHERE ticket_id = %s", (ticket["id"],))
    refusal = validate_close(ticket["failure_mode_id"], clean, labour)
    if refusal:
        status, field, message = refusal
        raise ApiError(message, status, field)
    _check_active_code(cur, "failure_causes", clean["cause_id"], "cause_id", CAUSE_NEEDED)
    _check_active_code(cur, "maintenance_actions", clean["action_id"], "action_id", ACTION_NEEDED)
    changes = {"cause_id": clean["cause_id"], "action_id": clean["action_id"]}
    mode_code = ticket["f_code"]
    new_mode_id = clean["failure_mode_id"]
    if new_mode_id is not None and new_mode_id != ticket["failure_mode_id"]:
        mode = _check_mode(cur, new_mode_id, ticket["m_class_id"])
        mode_code = mode["code"]
        changes["failure_mode_id"] = new_mode_id
        lines = edit_lines({"failure_mode": ticket["f_label"]}, {"failure_mode": mode["label"]}, _EDIT_LABELS)
        _add_event(cur, ticket["id"], EDITED_EVENT, occurred_at, remark=lines)
    message = description_error(ticket["description"], mode_code)
    if message:
        raise ApiError(message, 400, "description")
    return {}, changes


def _not_a_fault(cur, ticket, clean, *_args):
    """Not a fault: the cause says why it was raised; the flag keeps it out of failure counts.
    Refused while parts are recorded (S020 § 1.5): fitting a part is a maintenance action on a
    failure.  Counted under the ticket lock, which a parts add holds or waits for, so the two
    cannot both succeed."""
    if count(cur, "SELECT COUNT(*) AS n FROM ticket_parts WHERE ticket_id = %s", (ticket["id"],)):
        raise ApiError(PARTS_NOT_A_FAULT, 409)
    _check_active_code(cur, "failure_causes", clean["cause_id"], "cause_id", CAUSE_NEEDED)
    return {}, {"cause_id": clean["cause_id"], "not_a_fault": 1}


# Per move: (cur, ticket, clean, occurred_at, last, now, prefix) -> (event fields, ticket changes)
_MOVE_STEPS = {
    "start": _start,
    "restore": _restore,
    "schedule": _schedule,
    "reschedule": _reschedule,
    "send-back": _send_back,
    "close": _close,
    "not-a-fault": _not_a_fault,
}


@tickets_bp.route("/<int:ticket_id>/moves/<move>", methods=["POST"])
def make_move(ticket_id, move):
    """One route for every move (§ 7 decision 1): the key, the from-states and the required
    fields come from tickets_core.MOVES; a stale page offering a move gets 409.  A move whose key
    depends on its from-state (Schedule, S019 U1) is refused early only when the user holds
    none of its keys anywhere; the key that counts is the one for the locked state."""
    spec = MOVES.get(move)
    if spec is None:
        raise ApiError("Not found", 404)
    if not any(has_perm(key) for key in spec.keys):
        check_perm(spec.key)
    clean = clean_body(lambda body, _creating: validate_move(move, body), creating=False)
    now = _now()
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        ticket = _lock_open_ticket(cur, ticket_id, lambda state: spec.key_at(state) if state in spec.from_states else spec.keys)
        _apply_move(cur, ticket, move, clean, now)
        detail = _ticket_response(cur, ticket_id)
    return jsonify(detail)


def _apply_move(cur, ticket, move, clean, now, prefix=""):
    """One move on a ticket the caller holds (locked by make_move; just inserted, in its own
    transaction, by the raise's *Already fixed*, A1): the from-state check, the event time after
    the last ordered event, the move's own step, its event, the new state, and the auto-assign.
    ``prefix`` names the refusals on the move's fields (``restore.`` from the raise, BS2-02)."""
    spec = MOVES[move]
    if ticket["state"] not in spec.from_states:
        raise ApiError(TICKET_CHANGED, 409)
    ticket_id = ticket["id"]
    last = _last_ordered_event(cur, ticket_id)
    occurred_at = _event_time(clean["occurred_at"], last, now, f"{prefix}occurred_at")
    event, changes = {"from_state": ticket["state"]}, {}
    if move in _MOVE_STEPS:
        extra_event, changes = _MOVE_STEPS[move](cur, ticket, clean, occurred_at, last, now, prefix)
        event.update(extra_event)
    if ticket["state"] == SCHEDULED and spec.to_state != SCHEDULED:
        # The one place the plan is cleared (S019 BR1-08): every move that leaves scheduled,
        # now and later, so chk_tickets_plan stays a guard that never fires.  The events keep it.
        changes = {**changes, "planned_date": None, "waiting_reason": None}
    event_id = _add_event(cur, ticket_id, spec.event, occurred_at, to_state=spec.to_state, remark=clean["remark"],
                          **event)
    update_row(cur, "tickets", ticket_id, {"state": spec.to_state, **changes}, actor())
    if move in AUTO_ASSIGN_MOVES:
        _auto_assign(cur, ticket, occurred_at)
    if move == "send-back":
        # S021 § 5.3, BR3-04: *Down again* — the move's answer decides, whatever the intensity
        # was; after the event, so the alert names it
        alerts.enqueue_alert(cur, ticket_id, send_back_alert(clean["machine_down"]), event_id,
                             current_person_id(cur), ticket["rp_id"], now)
    if spec.to_state == CLOSED:
        # S032 § 1.3: Close and Not a fault — *ticket closed* to the site's managers, by email; the
        # closer is left out, the reporter is not; a close of back-entered history sends nothing
        alerts.enqueue_alert(cur, ticket_id, close_alert(now - occurred_at), event_id, current_person_id(cur), None,
                             now)


@tickets_bp.route("/<int:ticket_id>/regrade", methods=["POST"])
@require_perm(RAISE_KEY)
def regrade(ticket_id):
    """Change the intensity before back in service (Plan.MD § 4.2): raising by ticket:raise,
    lowering also needs ticket:work at the ticket's site and a remark (§ 7 decision 7).  The new
    intensity is on the regraded event, which the times read."""
    clean = clean_body(lambda body, _creating: validate_regrade_body(body), creating=False)
    now = _now()
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        ticket = _lock_open_ticket(cur, ticket_id, RAISE_KEY)
        if ticket["state"] not in REGRADE_STATES:
            raise ApiError(TICKET_CHANGED, 409)
        refusal = validate_regrade(ticket["intensity"], clean["intensity"],
                                   WORK_KEY in permissions_at_site(ticket["site_id"]), clean["remark"])
        if refusal:
            status, field, message = refusal
            raise ApiError(message, status, field)
        occurred_at = _event_time(clean["occurred_at"], _last_ordered_event(cur, ticket_id), now, "occurred_at")
        event_id = _add_event(cur, ticket_id, REGRADED_EVENT, occurred_at, intensity=clean["intensity"],
                              remark=clean["remark"])
        update_row(cur, "tickets", ticket_id, {"intensity": clean["intensity"]}, actor())
        # S021 § 5.3: *Machine stopped* alerts; it escalates only while still raised
        alerts.enqueue_alert(cur, ticket_id, regrade_alert(ticket["state"], clean["intensity"]), event_id,
                             current_person_id(cur), ticket["rp_id"], now)
        detail = _ticket_response(cur, ticket_id)
    return jsonify(detail)


def _locked_node_of_machine(cur, node_id, machine_id, machine_counts):
    """The node, when it is below the ticket's machine (two levels) — or the machine itself,
    when ``machine_counts`` — and not scrapped -> its row; None otherwise.  The node's row alone
    is read LOCK IN SHARE MODE — the lock the write's foreign key takes anyway — and "not
    scrapped" is decided from it, so a scrap of it at the same moment either commits first and
    is seen, or waits for this write and counts its ticket (S025 § 1.6).  The parent is read
    plain: a locking read through the join would lock it too.  Shared by the ticket edit's
    component and the parts line's node (S020 § 5.2); each caller raises its own refusal."""
    cur.execute("SELECT id, code, name, level, lifecycle, parent_id FROM equipment WHERE id = %s LOCK IN SHARE MODE",
                (node_id,))
    node = cur.fetchone()
    if node is None or node["lifecycle"] == SCRAPPED:
        return None
    if node["level"] == MACHINE_LEVEL:
        return node if machine_counts and node["id"] == machine_id else None
    node["gp_id"] = None
    if node["parent_id"] is not None:
        cur.execute("SELECT parent_id FROM equipment WHERE id = %s", (node["parent_id"],))
        node["gp_id"] = cur.fetchone()["parent_id"]
    return node if machine_and_component(node)[0] == machine_id else None


def _check_component(cur, component_id, machine_id):
    """A node below the ticket's machine (two levels), not scrapped -> its row; 400 otherwise."""
    node = _locked_node_of_machine(cur, component_id, machine_id, machine_counts=False)
    if node is None:
        raise ApiError(COMPONENT_OF_MACHINE, 400, "component_id")
    return node


def _node_label(code, name):
    return f"{code} {name}" if code else None


@tickets_bp.route("/<int:ticket_id>", methods=["PUT"])
@require_perm(WORK_KEY)
def edit_ticket(ticket_id):
    """Edit the component, symptom and description while open (§ 1 Edit); each change is a
    line on one *edited* event, old → new."""
    clean = clean_body(lambda body, _creating: validate_edit(body), creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        ticket = _lock_open_ticket(cur, ticket_id, WORK_KEY)
        old = {"component": _node_label(ticket["c_code"], ticket["c_name"]), "failure_mode": ticket["f_label"],
               "description": ticket["description"]}
        new, mode_code = {}, ticket["f_code"]
        if "component_id" in clean:
            component_id = clean["component_id"]
            node = _check_component(cur, component_id, ticket["equipment_id"]) if component_id else None
            new["component"] = _node_label(node["code"], node["name"]) if node else None
        if "failure_mode_id" in clean:
            mode = _check_mode(cur, clean["failure_mode_id"], ticket["m_class_id"]) if clean["failure_mode_id"] else None
            new["failure_mode"] = mode["label"] if mode else None
            mode_code = mode["code"] if mode else None
        if "description" in clean:
            new["description"] = clean["description"]
        message = description_error(new.get("description", ticket["description"]), mode_code)
        if message:
            raise ApiError(message, 400, "description")
        lines = edit_lines(old, new, _EDIT_LABELS)
        # Decide "changed" from the ids: two modes of different classes may share a label (CR1-06)
        if any(clean[field] != ticket[field] for field in clean):
            update_row(cur, "tickets", ticket_id, clean, actor())
        if lines:
            _add_event(cur, ticket_id, EDITED_EVENT, _now(), remark=lines)
        detail = _ticket_response(cur, ticket_id)
    return jsonify(detail)


@tickets_bp.route("/<int:ticket_id>/assignees", methods=["POST"])
@require_perm(ASSIGN_KEY)
def add_assignee(ticket_id):
    """Assign a technician, engineer or manager at the ticket's site, in any state before
    closed; assigning him again changes nothing (two taps on a phone) and alerts nobody.  A new
    assignee gets *Assigned to you* (S021 A1); acknowledge and start, which assign the actor
    himself (_auto_assign), alert nobody."""
    clean = clean_body(lambda body, _creating: validate_assignee(body), creating=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        ticket = _lock_open_ticket(cur, ticket_id, ASSIGN_KEY)
        person = _person_at_site(cur, clean["person_id"], ticket["site_id"])
        if person is None or person["role"] not in ASSIGNABLE_ROLES:
            raise ApiError(ASSIGNEE_AT_SITE, 400, "person_id")
        event_id = _assign(cur, ticket_id, person["id"], _now())
        if event_id is not None:
            alerts.enqueue_alert(cur, ticket_id, ASSIGNED_ALERT, event_id, current_person_id(cur), None, _now(),
                                 person_id=person["id"])
        detail = _ticket_response(cur, ticket_id)
    return jsonify(detail)


@tickets_bp.route("/<int:ticket_id>/assignees/<int:person_id>", methods=["DELETE"])
@require_perm(ASSIGN_KEY)
def remove_assignee(ticket_id, person_id):
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        _lock_open_ticket(cur, ticket_id, ASSIGN_KEY)
        cur.execute("DELETE FROM ticket_assignees WHERE ticket_id = %s AND person_id = %s", (ticket_id, person_id))
        if cur.rowcount == 0:
            raise ApiError("Not assigned", 404)
        _add_event(cur, ticket_id, UNASSIGNED_EVENT, _now(), person_id=person_id)
        detail = _ticket_response(cur, ticket_id)
    return jsonify(detail)


def _labour_body(cur, ticket):
    """The labour row's body, checked against the ticket (§ 1 Labour): the person anyone at the
    ticket's site, an active trade, required when the person holds one."""
    now = _now()
    clean = clean_body(lambda body, _creating: validate_labour(body, now.date(), ticket["occurred_at"].date()),
                       creating=True)
    _check_person(cur, clean["person_id"], ticket["site_id"], "person_id")
    if clean["trade_id"] is not None:
        cur.execute("SELECT active FROM trades WHERE id = %s", (clean["trade_id"],))
        trade = cur.fetchone()
        if trade is None or not trade["active"]:
            raise ApiError(TRADE_FROM_LIST, 400, "trade_id")
    has_trades = count(cur, "SELECT COUNT(*) AS n FROM person_trades pt JOIN trades t ON t.id = pt.trade_id"
                            " WHERE pt.person_id = %s AND t.active = 1", (clean["person_id"],)) > 0
    message = trade_error(clean["trade_id"], has_trades)
    if message:
        raise ApiError(message, 400, "trade_id")
    return clean


def _labour_row(cur, ticket_id, row_id):
    cur.execute("SELECT id FROM ticket_labour WHERE id = %s AND ticket_id = %s", (row_id, ticket_id))
    if cur.fetchone() is None:
        raise ApiError("Not found", 404)


@tickets_bp.route("/<int:ticket_id>/labour", methods=["POST"])
@require_perm(WORK_KEY)
def add_labour(ticket_id):
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        ticket = _lock_open_ticket(cur, ticket_id, WORK_KEY)
        insert_row(cur, "ticket_labour", {"ticket_id": ticket_id, **_labour_body(cur, ticket)}, actor())
        detail = _ticket_response(cur, ticket_id)
    return jsonify(detail), 201


@tickets_bp.route("/<int:ticket_id>/labour/<int:row_id>", methods=["PUT"])
@require_perm(WORK_KEY)
def update_labour(ticket_id, row_id):
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        ticket = _lock_open_ticket(cur, ticket_id, WORK_KEY)
        _labour_row(cur, ticket_id, row_id)
        update_row(cur, "ticket_labour", row_id, _labour_body(cur, ticket), actor())
        detail = _ticket_response(cur, ticket_id)
    return jsonify(detail)


@tickets_bp.route("/<int:ticket_id>/labour/<int:row_id>", methods=["DELETE"])
@require_perm(WORK_KEY)
def remove_labour(ticket_id, row_id):
    """A hard delete with no timeline line: the ticket is open and labour is not part of the
    failure's story (§ 4.2, BR1-16)."""
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        _lock_open_ticket(cur, ticket_id, WORK_KEY)
        _labour_row(cur, ticket_id, row_id)
        cur.execute("DELETE FROM ticket_labour WHERE id = %s", (row_id,))
        detail = _ticket_response(cur, ticket_id)
    return jsonify(detail)


# ---------------------------------------------------------------------------
# Work notes (S027): what was found and tried, a line on the timeline
# ---------------------------------------------------------------------------

@tickets_bp.route("/<int:ticket_id>/notes", methods=["POST"])
@require_perm(RESTORE_KEY)
def add_note(ticket_id):
    """S027 § 5.1: whoever may confirm the machine is back may write what they see, in any open
    state.  Stamped with the server's clock; it moves nothing (not an ordered event), so no
    order rule applies and the times stay as they were."""
    clean = clean_body(lambda body, _creating: validate_note(body), creating=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        _lock_open_ticket(cur, ticket_id, RESTORE_KEY)
        _add_event(cur, ticket_id, NOTE_EVENT, _now(), remark=clean["remark"])
        detail = _ticket_response(cur, ticket_id)
    return jsonify(detail), 201


@tickets_bp.route("/<int:ticket_id>/notes/<int:event_id>", methods=["PUT"])
@require_perm(EDIT_NOTES_KEY)
def edit_note(ticket_id, event_id):
    """Correct a note (S027 § 1.5, § 5.2): the ticket (7) FOR UPDATE (404 → 403 → 409), then
    the note's event row FOR UPDATE (a move's event or another ticket's note: 404).  The text
    it replaces goes to ticket_note_edits; the note keeps its time and place."""
    clean = clean_body(lambda body, _creating: validate_note(body), creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        _lock_open_ticket(cur, ticket_id, EDIT_NOTES_KEY)
        cur.execute("SELECT remark FROM ticket_events WHERE id = %s AND ticket_id = %s AND event = %s FOR UPDATE",
                    (event_id, ticket_id, NOTE_EVENT))
        note = cur.fetchone()
        if note is None:
            raise ApiError("Not found", 404)
        if note["remark"] == clean["remark"]:
            raise ApiError(NOTHING_TO_CHANGE, 400, "remark")
        # One clock value for both rows, so "Edited by …, <time>" and the earlier text's
        # "replaced at" show the same minute
        now, user = _now(), actor()
        cur.execute("INSERT INTO ticket_note_edits (event_id, remark, replaced_at, replaced_by) VALUES (%s, %s, %s, %s)",
                    (event_id, note["remark"], now, user))
        cur.execute("UPDATE ticket_events SET remark = %s, updated_at = %s, updated_by = %s WHERE id = %s",
                    (clean["remark"], now, user, event_id))
        detail = _ticket_response(cur, ticket_id)
    return jsonify(detail)


# ---------------------------------------------------------------------------
# Parts used (S020): lines of what was fitted, on the labour routes' pattern
# ---------------------------------------------------------------------------

# "Fitted here before" (§ 1.4, § 5.3): enough for the dialog's list, newest first
PART_SUGGESTIONS_MAX = 20


def _part_body(cur, ticket, current_node_id=None):
    """The parts line's body (S020 § 5.1), checked against the ticket.  The node is checked on
    an add, and on an edit only when it changes (§ 5.2 step 3, BR1-03): the machine itself or a
    part below it, not scrapped, decided from its row read LOCK IN SHARE MODE.  An unchanged
    node is history and may have been scrapped since."""
    clean = clean_body(lambda body, _creating: validate_part(body), creating=True)
    if (clean["node_id"] != current_node_id
            and _locked_node_of_machine(cur, clean["node_id"], ticket["equipment_id"], machine_counts=True) is None):
        raise ApiError(PART_NODE_NEEDED, 400, "node_id")
    return clean


def _part_row(cur, ticket_id, row_id):
    """A parts line of this ticket -> its node's id; 404 for a line of another ticket."""
    cur.execute("SELECT node_id FROM ticket_parts WHERE id = %s AND ticket_id = %s", (row_id, ticket_id))
    row = cur.fetchone()
    if row is None:
        raise ApiError("Not found", 404)
    return row["node_id"]


@tickets_bp.route("/<int:ticket_id>/parts", methods=["POST"])
@require_perm(WORK_KEY)
def add_part(ticket_id):
    """S020 § 5.2: the ticket (7) FOR UPDATE (404 → 403 → 409), the body (400), then the node
    in share mode — the order of the ticket edit (S025 § 1.6)."""
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        ticket = _lock_open_ticket(cur, ticket_id, WORK_KEY)
        insert_row(cur, "ticket_parts", {"ticket_id": ticket_id, **_part_body(cur, ticket)}, actor())
        detail = _ticket_response(cur, ticket_id)
    return jsonify(detail), 201


@tickets_bp.route("/<int:ticket_id>/parts/<int:row_id>", methods=["PUT"])
@require_perm(WORK_KEY)
def update_part(ticket_id, row_id):
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        ticket = _lock_open_ticket(cur, ticket_id, WORK_KEY)
        node_id = _part_row(cur, ticket_id, row_id)
        update_row(cur, "ticket_parts", row_id, _part_body(cur, ticket, node_id), actor())
        detail = _ticket_response(cur, ticket_id)
    return jsonify(detail)


@tickets_bp.route("/<int:ticket_id>/parts/<int:row_id>", methods=["DELETE"])
@require_perm(WORK_KEY)
def remove_part(ticket_id, row_id):
    """A hard delete with no timeline line, as labour (S020 § 5.2, § 7 decision 9): the ticket
    is open and the line carries its own audit columns."""
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        _lock_open_ticket(cur, ticket_id, WORK_KEY)
        _part_row(cur, ticket_id, row_id)
        cur.execute("DELETE FROM ticket_parts WHERE id = %s", (row_id,))
        detail = _ticket_response(cur, ticket_id)
    return jsonify(detail)


@tickets_bp.route("/<int:ticket_id>/part-suggestions")
@require_perm(WORK_KEY)
def part_suggestions(ticket_id):
    """"Fitted here before" (S020 § 1.4, § 5.3): the distinct lines already recorded on the
    ticket's machine and its parts (two levels), on any ticket, newest first.  Read by machine,
    not through the ticket access predicate (BR2-03, accepted): a suggestion carries no ticket
    and no site.  ticket:work at the ticket's site, as the parts writes."""
    with get_db().cursor() as cur:
        row = read_ticket(cur, ticket_id)
        require_perm_at(WORK_KEY, row["site_id"])
        machine_id = row["m_id"]
        cur.execute("SELECT p.part_number, p.number_kind, p.maker, p.description FROM ticket_parts p"
                    " JOIN equipment n ON n.id = p.node_id LEFT JOIN equipment np ON np.id = n.parent_id"
                    " WHERE n.id = %s OR n.parent_id = %s OR np.parent_id = %s"
                    " GROUP BY p.part_number, p.number_kind, p.maker, p.description"
                    " ORDER BY MAX(p.created_at) DESC, MAX(p.id) DESC LIMIT %s",
                    (machine_id, machine_id, machine_id, PART_SUGGESTIONS_MAX))
        items = cur.fetchall()
    return jsonify({"items": items, "total": len(items)})
