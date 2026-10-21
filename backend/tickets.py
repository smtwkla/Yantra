"""Tickets — raise and see (docs/steps/S017-raise-tickets/1-brief.md) and work them to the end
(docs/steps/S018-work-tickets/1-brief.md): moves, re-grade, edit, assignment, labour, repeat.

Thin shell: tickets_core holds the rules (intensity, the event-time window, the serial, the
description rule, machine and component from the node, the moves table, the send-back and
re-grade rules, labour and close validation, the times); this module checks access, locks,
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
Working a ticket (S018 § 5.3) — a move, re-grade, edit, assignment or labour change — locks
(7) only; nothing else locked.  Codes, people and the earlier ticket of a repeat are read plain.
A raise with *Already fixed* (A1) applies the restore move to its own new row inside the raise's
transaction: no further lock, and a refusal rolls the whole raise back, serial included.

The ticket insert takes shared locks through its foreign keys on the machine's equipment
row, the unit, the person and the failure mode.  Two deadlocks follow, accepted (§ 5.4,
§ 7 decision 12; InnoDB rolls one side back with 1213, a rare 500):
- scrapping a machine (machine, then its parts FOR UPDATE) against a raise on one of its parts
  (the part, then the machine's shared FK lock);
- a person's site-row edit (person, then units) against a raise naming that person (the FK
  checks take unit, then person).
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
from auth_utils import check_perm, current_person_id, permissions_at_site, require_perm, require_perm_at
from config_rbac import ASSIGNABLE_ROLES
from db_helpers import count, get_db, insert_row, next_counter, row_to_dict, rows_to_list, transaction, update_row
from equipment import IST, accessible_unit_ids, load_node_for_user
from equipment_core import SCRAPPED
from tickets_core import (
    ACTION_NEEDED, ASSIGN_KEY, ASSIGNED_EVENT, AUTO_ASSIGN_MOVES, EVENT_LABELS,
    CAUSE_NEEDED, CLOSED, EDITED_EVENT, IN_PROGRESS, INTENSITY_FILTERS, MACHINE_LEVEL, MOVES, OPEN_STATES,
    ORDERED_EVENTS, RAISED, REGRADE_STATES, REGRADED_EVENT, REPEAT_WINDOW_DAYS,
    RAISE_SCREEN_LABELS, RESTORE_FIELD_PREFIX, RESTORE_KEY,
    STARTED_EVENT, STATE_FILTERS, UNASSIGNED_EVENT, WORK_KEY, allowed_moves, description_error, edit_lines,
    format_ticket_serial, is_breakdown, is_repeat_candidate, latest_restoration, machine_and_component, regrade_options,
    send_back_intensity, serial_scope, started_at_error, ticket_times, trade_error, validate_assignee,
    validate_close, validate_edit, validate_event_time, validate_labour, validate_move, validate_raise,
    validate_regrade, validate_regrade_body,
)

tickets_bp = Blueprint("tickets", __name__)

UNIQUE_KEY_ERRORS.update({
    "uq_tickets_serial": (None, "Serial collision — retry"),
})

READ_KEY = "ticket:read"
RAISE_KEY = "ticket:raise"

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
    " ma.label AS ma_label, rt.id AS rt_id, rt.serial AS rt_serial"
)


def _now():
    """The IST wall clock, naive, as every DATETIME is stored (base § Timezone policy)."""
    return datetime.now(IST).replace(tzinfo=None)


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


def _ticket_out(row):
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
    """The ticket's events, oldest first, as stored (datetimes, for ticket_times)."""
    cur.execute("SELECT e.event, e.from_state, e.to_state, e.occurred_at, e.intensity, e.remark, e.created_at,"
                " e.created_by, p.id AS person_id, p.name AS person_name FROM ticket_events e"
                " LEFT JOIN people p ON p.id = e.person_id WHERE e.ticket_id = %s"
                " ORDER BY e.occurred_at, e.id", (ticket_id,))
    return cur.fetchall()


def _events_out(rows):
    events = []
    for row in rows_to_list(rows):
        person_id, person_name = row.pop("person_id"), row.pop("person_name")
        row["person"] = {"id": person_id, "name": person_name} if person_id is not None else None
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
    auto-assign, BR4-04)."""
    names = allowed_moves(row["state"], keys)
    own = _own_person_at_site(cur, row["site_id"]) if names else None
    moves = []
    for name in names:
        entry = {"name": name}
        if name == "restore":
            entry["default_person"] = _person_ref(own) if WORK_KEY in keys else None
        elif name in AUTO_ASSIGN_MOVES:
            entry["recording_as"] = _person_ref(own) if own and own["role"] in ASSIGNABLE_ROLES else None
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
        **_ticket_out(row),
        "events": _events_out(events),
        "times": ticket_times(events, now),
        "assignees": _assignees(cur, [ticket_id])[ticket_id],
        "labour": _labour(cur, ticket_id),
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


_LOCK_TICKET = ("SELECT id, state, intensity, failure_mode_id, equipment_id, component_id, description,"
                " occurred_at, not_a_fault FROM tickets WHERE id = %s FOR UPDATE")


def _lock_ticket(cur, ticket_id, key):
    """Lock the ticket row (7), then 404 (predicate) and 403 (``key`` at the ticket's site) ->
    the ticket's row, its state, intensity, mode, machine, component and description from the
    locked read (every refusal is decided from those, S018 § 5.3).  The unit never changes, so
    the plain read for access is as good as the locked row."""
    cur.execute(_LOCK_TICKET, (ticket_id,))
    locked = cur.fetchone()
    if locked is None:
        raise ApiError("Not found", 404)
    row = read_ticket(cur, ticket_id)
    require_perm_at(key, row["site_id"])
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
    site_id = int_arg("site_id", None, minimum=1)
    unit_id = int_arg("unit_id", None, minimum=1)
    equipment_id = int_arg("equipment_id", None, minimum=1)
    q = (request.args.get("q") or "").strip()

    empty = {"items": [], "total": 0, "page": page, "per_page": per_page}
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
        # closed and all: newest first (§ 5.3).  In SQL, because the list is paginated.
        order = ("t.intensity, t.occurred_at, t.id" if state == "open" else "t.occurred_at DESC, t.id DESC")
        where = " AND ".join(conditions)
        total = count(cur, f"SELECT COUNT(*) AS n{_TICKET_FROM} WHERE {where}", params)
        cur.execute(f"{_TICKET_COLUMNS}{_TICKET_FROM} WHERE {where} ORDER BY {order} LIMIT %s OFFSET %s",
                    [*params, per_page, (page - 1) * per_page])
        rows = cur.fetchall()
        assignees = _assignees(cur, [row["id"] for row in rows])
        items = [{**_ticket_out(row), "assignees": assignees[row["id"]]} for row in rows]
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


# ---------------------------------------------------------------------------
# Raise
# ---------------------------------------------------------------------------

@tickets_bp.route("/", methods=["POST"], strict_slashes=False)
@require_perm(RAISE_KEY)
def raise_ticket():
    now = _now()
    clean = clean_body(lambda body, _creating: validate_raise(body, now), creating=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        # (1) the node; 404 outside the user's units; 403 unless ticket:raise at its site
        locked, node = load_node_for_user(cur, clean["equipment_id"], for_update=True, key=RAISE_KEY)
        if locked["status"] == SCRAPPED:
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
            cur.execute("SELECT id, status, unit_id, class_id FROM equipment WHERE id = %s", (machine_id,))
            machine = cur.fetchone()
            if machine["status"] == SCRAPPED:
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
        _add_event(cur, ticket_id, RAISED, clean["occurred_at"], to_state=RAISED, intensity=clean["intensity"])
        if clean["restore"] is not None:
            # A1, *Already fixed*: the restore move's own code on the new row (no lock needed: the
            # row is this transaction's own); a refusal rolls the whole raise back
            _apply_move(cur, read_ticket(cur, ticket_id), "restore", clean["restore"], now, RESTORE_FIELD_PREFIX)
        # Read inside the transaction, as documents.py does: nothing after the commit can
        # turn this answer into an error
        detail = _detail(cur, read_ticket(cur, ticket_id))
    return jsonify(detail), 201


# ---------------------------------------------------------------------------
# Working the ticket (S018) — every write: lock (7) → 404 → 403 at the ticket's site → 409
# ---------------------------------------------------------------------------

def _add_event(cur, ticket_id, event, occurred_at, from_state=None, to_state=None, intensity=None, person_id=None,
               remark=None):
    insert_row(cur, "ticket_events", {
        "ticket_id": ticket_id, "event": event, "from_state": from_state, "to_state": to_state,
        "occurred_at": occurred_at, "intensity": intensity, "person_id": person_id, "remark": remark,
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
    message = validate_event_time(entered, last, now, labels)
    if message:
        raise ApiError(message, 400, field)
    return entered


def _ticket_response(cur, ticket_id):
    """The detail, read inside the write's transaction (as the raise)."""
    return _detail(cur, read_ticket(cur, ticket_id))


def _assign(cur, ticket_id, person_id, occurred_at):
    """Add an assignee with its *assigned* line; already assigned -> no change (False)."""
    cur.execute("SELECT 1 FROM ticket_assignees WHERE ticket_id = %s AND person_id = %s", (ticket_id, person_id))
    if cur.fetchone():
        return False
    cur.execute("INSERT INTO ticket_assignees (ticket_id, person_id, assigned_by) VALUES (%s, %s, %s)",
                (ticket_id, person_id, actor()))
    _add_event(cur, ticket_id, ASSIGNED_EVENT, occurred_at, person_id=person_id)
    return True


def _auto_assign(cur, ticket, occurred_at):
    """Acknowledge / start by a user whose own person is assignable at the ticket's site adds
    him, as a manual assignment would (§ 5.8); anyone else is simply not added."""
    own = _own_person_at_site(cur, ticket["site_id"])
    if own and own["role"] in ASSIGNABLE_ROLES:
        _assign(cur, ticket["id"], own["id"], occurred_at)


def _restore(cur, ticket, clean, occurred_at, last, now, prefix):
    """Back in service: the named person (anyone at the site), and the start time after the
    fact, written as a *started* event before it with the same person -> the event's fields.
    ``prefix`` names the refusals (``restore.`` from the raise, A1)."""
    person = _check_person(cur, clean["person_id"], ticket["site_id"], f"{prefix}person_id")
    from_state = ticket["state"]
    if clean["started_at"] is not None:
        started_at = _event_time(clean["started_at"], last, now, f"{prefix}started_at")
        message = started_at_error(started_at, from_state, occurred_at)
        if message:
            raise ApiError(message, 400, f"{prefix}started_at")
        _add_event(cur, ticket["id"], STARTED_EVENT, started_at, from_state, IN_PROGRESS, person_id=person["id"])
        from_state = IN_PROGRESS
    return {"from_state": from_state, "person_id": person["id"]}, {}


def _send_back(_cur, ticket, clean, *_args):
    """Send back: the intensity follows "machine down again?" (decision 4), on the sent_back event."""
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


def _not_a_fault(cur, _ticket, clean, *_args):
    """Not a fault: the cause says why it was raised; the flag keeps it out of failure counts."""
    _check_active_code(cur, "failure_causes", clean["cause_id"], "cause_id", CAUSE_NEEDED)
    return {}, {"cause_id": clean["cause_id"], "not_a_fault": 1}


# Per move: (cur, ticket, clean, occurred_at, last, now, prefix) -> (event fields, ticket changes)
_MOVE_STEPS = {
    "restore": _restore,
    "send-back": _send_back,
    "close": _close,
    "not-a-fault": _not_a_fault,
}


@tickets_bp.route("/<int:ticket_id>/moves/<move>", methods=["POST"])
def make_move(ticket_id, move):
    """One route for every move (§ 7 decision 1): the key, the from-states and the required
    fields come from tickets_core.MOVES; a stale page offering a move gets 409."""
    spec = MOVES.get(move)
    if spec is None:
        raise ApiError("Not found", 404)
    check_perm(spec.key)
    clean = clean_body(lambda body, _creating: validate_move(move, body), creating=False)
    now = _now()
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        ticket = _lock_open_ticket(cur, ticket_id, spec.key)
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
    _add_event(cur, ticket_id, spec.event, occurred_at, to_state=spec.to_state, remark=clean["remark"], **event)
    update_row(cur, "tickets", ticket_id, {"state": spec.to_state, **changes}, actor())
    if move in AUTO_ASSIGN_MOVES:
        _auto_assign(cur, ticket, occurred_at)


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
        _add_event(cur, ticket_id, REGRADED_EVENT, occurred_at, intensity=clean["intensity"], remark=clean["remark"])
        update_row(cur, "tickets", ticket_id, {"intensity": clean["intensity"]}, actor())
        detail = _ticket_response(cur, ticket_id)
    return jsonify(detail)


def _check_component(cur, component_id, machine_id):
    """A node below the ticket's machine (two levels), not scrapped -> its row; 400 otherwise."""
    cur.execute("SELECT e.id, e.code, e.name, e.level, e.status, e.parent_id, p.parent_id AS gp_id"
                " FROM equipment e LEFT JOIN equipment p ON p.id = e.parent_id WHERE e.id = %s", (component_id,))
    node = cur.fetchone()
    if (node is None or node["level"] == MACHINE_LEVEL or node["status"] == SCRAPPED
            or machine_and_component(node)[0] != machine_id):
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
    closed; assigning him again changes nothing (two taps on a phone)."""
    clean = clean_body(lambda body, _creating: validate_assignee(body), creating=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        ticket = _lock_open_ticket(cur, ticket_id, ASSIGN_KEY)
        person = _person_at_site(cur, clean["person_id"], ticket["site_id"])
        if person is None or person["role"] not in ASSIGNABLE_ROLES:
            raise ApiError(ASSIGNEE_AT_SITE, 400, "person_id")
        _assign(cur, ticket_id, person["id"], _now())
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
