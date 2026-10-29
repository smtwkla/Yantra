"""Improvements — the record where the team analyses one problem that tickets showed, so it does
not happen again (TPM focused improvement; docs/steps/S067-improvement-record/1-brief.md).  This
step: start one from a ticket, its detail, edit, add and remove tickets, the list and the lead
choices.  The screens are S068's.  S069 adds the analysis: the why-why chain (improvement_whys)
and the root cause with the contributing causes (columns of improvements).

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
- Reads (list, detail, leads; the ticket detail in tickets.py): plain, no lock.
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
  here locks a ticket, and no masters write locks an improvement or a why.
The cause freeze is race-free as the tickets' (tickets.py LOCK ORDER): a root-cause write that
holds the cause's shared lock commits before the code change gets its exclusive lock, and the
count sees it; a later one waits behind the cause's lock and then sees the new code, which is
allowed (the code changed before its first use).

Import direction: this module imports read_ticket, improvement_links, person_at_site and
people_at_site from tickets.py; tickets.py never imports this module (only improvements_core).
"""

from datetime import datetime

from flask import Blueprint, jsonify

from api_common import (
    DEFAULT_PER_PAGE, MAX_PAGE, MAX_PER_PAGE, UNIQUE_KEY_ERRORS, ApiError, actor, clean_body, enum_arg, int_arg,
)
from auth_utils import permissions_at_site, require_perm, require_perm_at
from db_helpers import count, get_db, insert_row, next_counter, row_to_dict, transaction, update_row
from equipment import IST, unit_access_condition
from improvements_core import (
    ALREADY_OPEN_RACE, CAUSE_ACTIVE, EDIT_KEY, IMPROVEMENT_CLOSED, IMPROVEMENT_OPEN_STATES, LEAD_AT_SITE, NOT_A_FAULT,
    READ_KEY, SERIAL_PREFIX, TICKET_FROM_LIST, TICKET_OTHER_SITE, WHYS_FULL, WHYS_MAX, is_open, link_error, loss,
    may_lead, position_error, removal_error, renumber, reorder, start_error, validate_improvement, validate_link,
    validate_root_cause, validate_why,
)
from tickets import code_ref, improvement_links, people_at_site, person_at_site, read_ticket
from tickets_core import format_serial, is_breakdown, serial_scope, ticket_times

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
)
# The list builds its items field by field, so the root-cause columns add nothing to it (S069 § 6)
_IMPROVEMENT_COLUMNS = (
    "SELECT i.id, i.serial, i.state, i.title, i.problem, i.created_at, i.created_by, i.updated_at, i.updated_by,"
    " i.unit_id, u.code AS unit_code, s.id AS site_id, s.code AS site_code,"
    " m.id AS m_id, m.code AS m_code, m.name AS m_name,"
    " l.id AS lead_id, l.name AS lead_name, l.active AS lead_active, cp.name AS created_by_name,"
    " i.root_cause, i.contributing_causes, rc.id AS rc_id, rc.code AS rc_code, rc.label AS rc_label,"
    " rc.cause_group AS rc_group, rc.active AS rc_active"
)

# (6b): the improvement's decision columns, and the values an edit compares with
_LOCK_IMPROVEMENT = ("SELECT id, state, unit_id, equipment_id, title, problem, lead_id,"
                     " root_cause, root_cause_id, contributing_causes FROM improvements"
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


def _in(values):
    return ", ".join(["%s"] * len(values))


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
                    f" FROM ticket_events WHERE ticket_id IN ({_in(ticket_ids)}) ORDER BY occurred_at, id",
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
    cur.execute(f"{_LINKED_TICKETS} WHERE it.improvement_id IN ({_in(improvement_ids)})"
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


def _detail(cur, row):
    """The improvement page's data (§ 6): the record, its tickets with each one's removable, the
    loss, the lead's standing today and the user's keys at the improvement's site."""
    tickets = _linked_tickets(cur, [row["id"]], _now())[row["id"]]
    open_now = is_open(row["state"])
    machine = _machine(row)
    links = [{"id": t["id"], "equipment_id": t["machine"]["id"]} for t in tickets]
    for ticket, link in zip(tickets, links):
        ticket["removable"] = open_now and removal_error(link, links, machine) is None
    lead_now = person_at_site(cur, row["lead_id"], row["site_id"])
    plain = row_to_dict(row)
    return {
        "id": plain["id"],
        "serial": plain["serial"],
        "state": plain["state"],
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
        "permissions": sorted(permissions_at_site(row["site_id"])),
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
        conditions.append(f"i.state {negate}IN ({_in(IMPROVEMENT_OPEN_STATES)})")
        params.extend(IMPROVEMENT_OPEN_STATES)
        if unit_id is not None:
            conditions.append("i.unit_id = %s")
            params.append(unit_id)
        where = " AND ".join(conditions)
        total = count(cur, f"SELECT COUNT(*) AS n{_IMPROVEMENT_FROM} WHERE {where}", params)
        cur.execute(f"{_IMPROVEMENT_COLUMNS}{_IMPROVEMENT_FROM} WHERE {where} ORDER BY i.id DESC LIMIT %s OFFSET %s",
                    [*params, per_page, (page - 1) * per_page])
        rows = cur.fetchall()
        linked = _linked_tickets(cur, [row["id"] for row in rows], _now())
    items = []
    for row in rows:
        plain = row_to_dict(row)
        items.append({
            "id": plain["id"], "serial": plain["serial"], "state": plain["state"], "title": plain["title"],
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
        insert_row(cur, "improvement_tickets", {"improvement_id": improvement_id, "ticket_id": ticket["id"]}, actor())
        detail = _detail_response(cur, improvement_id)
    return jsonify(detail), 201


@improvements_bp.route("/<int:improvement_id>", methods=["PUT"])
@require_perm(EDIT_KEY)
def edit_improvement(improvement_id):
    """Title, problem and lead (§ 5.2): a field equal to the stored one is not written, and an
    edit that changes nothing writes nothing.  The lead is checked only when it changes, so a
    lead who has since left the site stays until someone picks another (§ 5.6)."""
    clean = clean_body(validate_improvement, creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        locked = _lock_improvement(cur, improvement_id)   # (6b)
        row = _check_improvement(cur, improvement_id)
        changes = {field: value for field, value in clean.items() if value != locked[field]}
        if "lead_id" in changes:
            _check_lead(cur, changes["lead_id"], row["site_id"])
        update_row(cur, "improvements", improvement_id, changes, actor())
        detail = _detail_response(cur, improvement_id)
    return jsonify(detail)


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
        detail = _detail_response(cur, improvement_id)
    return jsonify(detail)


# ---------------------------------------------------------------------------
# The why-why chain and the root cause (S069; LOCK ORDER above)
# ---------------------------------------------------------------------------

def _lock_for_analysis(cur, improvement_id):
    """Every S069 write's start (§ 5.1): (6b), then the predicate 404, the key at the site 403
    and the open state 409 -> the locked row."""
    locked = _lock_improvement(cur, improvement_id)   # (6b)
    _check_improvement(cur, improvement_id)
    _require_open(locked)
    return locked


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
        detail = _detail_response(cur, improvement_id)
    return jsonify(detail), 201


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
        detail = _detail_response(cur, improvement_id)
    return jsonify(detail)


@improvements_bp.route("/<int:improvement_id>/whys/<int:why_id>", methods=["DELETE"])
@require_perm(EDIT_KEY)
def remove_why(improvement_id, why_id):
    """The row is deleted, no history in this step (D6); the lines after it move up."""
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        _lock_for_analysis(cur, improvement_id)
        _read_why(cur, improvement_id, why_id)
        rest = [pair for pair in _chain(cur, improvement_id) if pair[0] != why_id]
        cur.execute("DELETE FROM improvement_whys WHERE id = %s", (why_id,))
        _shift(cur, renumber(rest))
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
        locked = _lock_for_analysis(cur, improvement_id)
        changes = {field: value for field, value in clean.items() if value != locked[field]}
        if "root_cause_id" in changes:
            cur.execute("SELECT active FROM failure_causes WHERE id = %s", (changes["root_cause_id"],))
            cause = cur.fetchone()
            if cause is None or not cause["active"]:
                raise ApiError(CAUSE_ACTIVE, 400, "root_cause_id")
        update_row(cur, "improvements", improvement_id, changes, actor())
        detail = _detail_response(cur, improvement_id)
    return jsonify(detail)
