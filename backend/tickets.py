"""Tickets — raise and see (docs/steps/S017-raise-tickets/1-brief.md).  Working the ticket is
S018.

Thin shell: tickets_core holds the rules (intensity, the event-time window, the serial, the
description rule, machine and component from the node); this module checks access, locks,
issues the serial and stores the ticket with its first event.

ACCESS — one predicate for the list, the detail and the ticket's photos (§ 5.3): a ticket is
visible when its own unit (the machine's unit at raise) or its machine's current unit is among
the units where the user holds ticket:read.  So a moved machine's tickets show on its
equipment page wherever it stands, and the old unit's team keeps them.  Outside it: 404.
"The ticket's site" in every write check is the site of tickets.unit_id.

LOCK ORDER (equipment.py's numbers): (1) the node raised on → (6) the serial counter →
(7) the ticket row.  Ticket rows are locked only here and by documents.py (the ticket owner,
through the functions below), always last; nothing that holds a ticket lock then takes an
equipment, unit or counter lock.  Ancestors of the node are read plain, never locked.

The ticket insert takes shared locks through its foreign keys on the machine's equipment
row, the unit, the person and the failure mode.  Two deadlocks follow, accepted (§ 5.4,
§ 7 decision 12; InnoDB rolls one side back with 1213, a rare 500):
- scrapping a machine (machine, then its parts FOR UPDATE) against a raise on one of its parts
  (the part, then the machine's shared FK lock);
- a person's site-row edit (person, then units) against a raise naming that person (the FK
  checks take unit, then person).
A mode's code change (masters.py) locks the mode row FOR UPDATE, then counts its tickets with
a shared-lock read: a raise holding the mode's FK lock commits first and is counted, a later
one queues behind the mode lock, so "code frozen once used" is race-free.  A deactivation is not, and
need not be: an inactive mode stays on tickets that already use it.

Import direction: documents.py imports the ticket owner's read and lock functions from here;
this module never imports documents.py.
"""

from datetime import datetime

from flask import Blueprint, jsonify, request

from api_common import (
    DEFAULT_PER_PAGE, MAX_PAGE, MAX_PER_PAGE, UNIQUE_KEY_ERRORS, ApiError, actor, clean_body, enum_arg, int_arg,
    like_pattern,
)
from auth_utils import has_perm_at, require_perm, require_perm_at
from db_helpers import count, get_db, insert_row, next_counter, row_to_dict, rows_to_list, transaction
from equipment import IST, accessible_unit_ids, load_node_for_user
from equipment_core import SCRAPPED
from tickets_core import (
    CLOSED, INTENSITY_FILTERS, MACHINE_LEVEL, OPEN_STATES, RAISED, STATE_FILTERS, description_error, format_ticket_serial,
    is_breakdown, machine_and_component, serial_scope, validate_raise,
)

tickets_bp = Blueprint("tickets", __name__)

UNIQUE_KEY_ERRORS.update({
    "uq_tickets_serial": (None, "Serial collision — retry"),
})

READ_KEY = "ticket:read"
RAISE_KEY = "ticket:raise"

SCRAPPED_NO_TICKETS = "Scrapped equipment takes no tickets"
TICKET_CLOSED = "This ticket is closed"

_TICKET_FROM = (
    " FROM tickets t"
    " JOIN equipment m ON m.id = t.equipment_id"
    " JOIN equipment_classes mc ON mc.id = m.class_id"
    " LEFT JOIN equipment c ON c.id = t.component_id"
    " JOIN units u ON u.id = t.unit_id"
    " JOIN sites s ON s.id = u.site_id"
    " LEFT JOIN failure_modes f ON f.id = t.failure_mode_id"
    " LEFT JOIN people rp ON rp.id = t.reported_by_id"
)
_TICKET_COLUMNS = (
    "SELECT t.id, t.serial, t.state, t.intensity, t.occurred_at, t.created_at, t.created_by, t.description,"
    " t.unit_id, u.code AS unit_code, s.id AS site_id, s.code AS site_code,"
    " m.id AS m_id, m.code AS m_code, m.name AS m_name, mc.code AS m_class_code,"
    " c.id AS c_id, c.code AS c_code, c.name AS c_name,"
    " f.id AS f_id, f.code AS f_code, f.label AS f_label, rp.id AS rp_id, rp.name AS rp_name"
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
        "failure_mode": ({"id": plain["f_id"], "code": plain["f_code"], "label": plain["f_label"]}
                         if plain["f_id"] is not None else None),
        "description": plain["description"],
        "reported_by": {"id": plain["rp_id"], "name": plain["rp_name"]} if plain["rp_id"] is not None else None,
    }


def read_ticket(cur, ticket_id, _key=None):
    """Plain read of one ticket through the access predicate; 404 when missing or not
    visible, as equipment answers.  Also documents.py's ticket owner ``read``."""
    visible = _visible_condition(cur)
    if visible is None:
        raise ApiError("Not found", 404)
    condition, params = visible
    cur.execute(f"{_TICKET_COLUMNS}{_TICKET_FROM} WHERE t.id = %s AND {condition}", [ticket_id, *params])
    row = cur.fetchone()
    if row is None:
        raise ApiError("Not found", 404)
    return row


def _events(cur, ticket_id):
    cur.execute("SELECT e.event, e.from_state, e.to_state, e.occurred_at, e.intensity, e.remark, e.created_at,"
                " e.created_by, p.id AS person_id, p.name AS person_name FROM ticket_events e"
                " LEFT JOIN people p ON p.id = e.person_id WHERE e.ticket_id = %s"
                " ORDER BY e.occurred_at, e.id", (ticket_id,))
    events = []
    for row in rows_to_list(cur.fetchall()):
        person_id, person_name = row.pop("person_id"), row.pop("person_name")
        row["person"] = {"id": person_id, "name": person_name} if person_id is not None else None
        events.append(row)
    return events


def _detail(cur, row):
    return {**_ticket_out(row), "events": _events(cur, row["id"]),
            "can_add_photos": row["state"] != CLOSED and has_perm_at(RAISE_KEY, row["site_id"])}


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


def _lock_ticket(cur, ticket_id, key):
    """Lock the ticket row (7), then 404 (predicate) and 403 (``key`` at the ticket's site).
    The unit never changes, so the plain read for access is as good as the locked row."""
    cur.execute("SELECT id, state FROM tickets WHERE id = %s FOR UPDATE", (ticket_id,))
    locked = cur.fetchone()
    if locked is None:
        raise ApiError("Not found", 404)
    row = read_ticket(cur, ticket_id)
    require_perm_at(key, row["site_id"])
    return locked


def lock_ticket_for_change(cur, ticket_id, key):
    """In the write transaction: 404, 403, and a closed ticket 409, decided from the locked
    row (upload, title edit, remove and restore alike)."""
    if _lock_ticket(cur, ticket_id, key)["state"] == CLOSED:
        raise ApiError(TICKET_CLOSED, 409)


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
        items = [_ticket_out(row) for row in cur.fetchall()]
    return jsonify({"items": items, "total": total, "page": page, "per_page": per_page})


@tickets_bp.route("/<int:ticket_id>")
@require_perm(READ_KEY)
def get_ticket(ticket_id):
    with get_db().cursor() as cur:
        return jsonify(_detail(cur, read_ticket(cur, ticket_id)))


# ---------------------------------------------------------------------------
# The raise screen's pickers — the node's machine, checked as the raise is
# ---------------------------------------------------------------------------

def _required_node_arg():
    node_id = int_arg("equipment_id", None, minimum=1)
    if node_id is None:
        raise ApiError("equipment_id is required", 400, "equipment_id")
    return node_id


def _machine_class_id(cur, node):
    """The class of the node's machine: the node's own, or its machine's (a plain read)."""
    machine_id, component_id = machine_and_component(node)
    if component_id is None:
        return node["class_id"]
    cur.execute("SELECT class_id FROM equipment WHERE id = %s", (machine_id,))
    return cur.fetchone()["class_id"]


@tickets_bp.route("/modes")
@require_perm(RAISE_KEY)
def list_modes():
    """The symptoms a ticket on this node offers: the active modes of its machine's class,
    then the active General ones, each by label (S016 § 5.2).  The machine's, even for a
    component: the operator does not know the component's class."""
    node_id = _required_node_arg()
    with get_db().cursor() as cur:
        _, node = load_node_for_user(cur, node_id, for_update=False, key=RAISE_KEY)
        class_id = _machine_class_id(cur, node)
        cur.execute("SELECT id, code, label, description, class_id FROM failure_modes"
                    " WHERE active = 1 AND (class_id = %s OR class_id IS NULL)"
                    " ORDER BY class_id IS NULL, label", (class_id,))
        items = cur.fetchall()
    return jsonify({"items": items})


def _people_at_site(cur, site_id):
    """Active people with a membership at the site, by name, with their active trades
    ``[{id, name}]`` and their role there: the one people picker (reported by here; S018's
    assignees and labour).  Site first, so S018 can anchor it on a ticket's site."""
    cur.execute("SELECT p.id, p.name, ms.role FROM people p JOIN memberships ms ON ms.person_id = p.id"
                " WHERE ms.site_id = %s AND p.active = 1 ORDER BY p.name, p.id", (site_id,))
    people = [{**row, "trades": []} for row in cur.fetchall()]
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
    """People who can be named on a ticket on this node: at the node's current site.  Names
    only, and only where the user may raise (ISO 27001 A.5.15)."""
    node_id = _required_node_arg()
    with get_db().cursor() as cur:
        _, node = load_node_for_user(cur, node_id, for_update=False, key=RAISE_KEY)
        return jsonify({"items": _people_at_site(cur, node["site_id"])})


# ---------------------------------------------------------------------------
# Raise
# ---------------------------------------------------------------------------

def _check_mode(cur, mode_id, machine_class_id):
    """The picked symptom: active, and General or of the machine's class -> its code."""
    cur.execute("SELECT code, class_id, active FROM failure_modes WHERE id = %s", (mode_id,))
    mode = cur.fetchone()
    if (mode is None or not mode["active"]
            or (mode["class_id"] is not None and mode["class_id"] != machine_class_id)):
        raise ApiError("Choose a symptom from the list", 400, "failure_mode_id")
    return mode["code"]


def _check_reporter(cur, person_id, site_id):
    """Reported by: an active person with a membership at the ticket's site (operators
    without a login included, user decision 5)."""
    cur.execute("SELECT p.id FROM people p JOIN memberships ms ON ms.person_id = p.id"
                " WHERE p.id = %s AND p.active = 1 AND ms.site_id = %s", (person_id, site_id))
    if cur.fetchone() is None:
        raise ApiError("Choose a person from this site", 400, "reported_by_id")


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
            mode_code = _check_mode(cur, clean["failure_mode_id"], machine["class_id"])
        message = description_error(clean["description"], mode_code)
        if message:
            raise ApiError(message, 400, "description")
        if clean["reported_by_id"] is not None:
            _check_reporter(cur, clean["reported_by_id"], node["site_id"])

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
            "occurred_at": clean["occurred_at"],
        }, actor())
        insert_row(cur, "ticket_events", {
            "ticket_id": ticket_id,
            "event": RAISED,
            "to_state": RAISED,
            "occurred_at": clean["occurred_at"],
            "intensity": clean["intensity"],
        }, actor())
        # Read inside the transaction, as documents.py does: nothing after the commit can
        # turn this answer into an error
        detail = _detail(cur, read_ticket(cur, ticket_id))
    return jsonify(detail), 201
