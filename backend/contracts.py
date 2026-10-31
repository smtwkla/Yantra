"""Vendor contracts — the API (docs/steps/S080-contract-register/1-brief.md; R02.1).  One record per vendor
contract, company-wide (S087: a contract has no site; its sites are its machines' sites, derived on every read
through contracts_core.LINE_SITE_JOINS): its vendor (the vendors master, S079), type, period, what is covered,
the PM visits agreed, the response time, the call-out number, the *Only the vendor may repair* tick and a cost note.
The status comes from the dates (contracts_core.contract_status), never stored.  Never deleted: one entered by mistake
is set inactive (ISO 9001 § 7.5).  The machines covered and their prices (contract_equipment, S081, R02.2; docs/steps/
S081-contract-equipment/1-brief.md): one line per node of any site, any level, with an optional price
before GST; the total is their sum, never stored.  Each add and remove writes a line in the machine's history
(equipment_events), never with the price.  The renewal (S085, R02.4; docs/steps/S085-contract-renewal/1-brief.md):
a new contract with renewal_of_id the old one (one renewal per contract, v47), its terms from the dialog, the old
contract's machines not scrapped copied without prices, wherever they stand; the old contract, its prices,
cost note and documents stay as they were.  The renewal is made only here (renew_contract), under the old contract's
lock.  The breakdown calls (S086, R02.6; docs/steps/S086-contract-breakdown-calls/1-brief.md): the tickets on a
covered node or its parts, happened in the period, that a Team record linked to the contract's vendor is assigned to
or logs labour on (the current link counts, Q9.5 a), with their downtime and the wait on the vendor from
tickets_core.ticket_times (through contracts_core.call_figures); derived on every read, nothing stored.

Thin shell: contracts_core holds the rules; this module checks access, locks, reads and stores.

ACCESS (S080 § 5.4, § 5.5; S081 § 5.4; S087 § 5.1).  Four global keys, checked by the union (has_perm, check_perm,
require_perm): a contract has no site (S087).  Unit rows play no part in reading it (D8); a machine line's link
follows the reader's units (can_open), the line itself does not (B7).  contract:read_basic reads the terms and
the machines; contract:read adds callout_number; contract:read_senior adds cost_note, each line's price and the
contract's price_total and priced_count; contract:edit adds and changes contracts and lines.  Every answer goes
through _contract_out (and _machine_lines for the lines), which leaves a gated field out (absent, not null) for a
reader without its key, and every write drops a gated field the writer may not read (_drop_gated with
GATED_FIELDS or LINE_GATED_FIELDS), so their save leaves it as it was (ISO 27001 A.5.15).  A price change has no
other field: it needs contract:read_senior too, else 403 (S081 B3).  The Under contract card (S082,
/for-equipment/<node_id>) reads the node through load_node_for_user (404 outside the reader's units), keeps every
contract found, and cuts _contract_out's answer to _CARD_KEYS: never a
price, a total or a cost note, for any reader.  The contract's documents and photos (S083, documents.py's
OWNERS["contract"] calling read_contract, read_contract_for_change and lock_contract_for_change below) are read
with contract:read_senior (D5: a quote or a signed contract shows the price), written with contract:edit and
contract:read_senior, restored and erased with equipment:purge_documents (held at any site) and
contract:read_senior; the flags can_read_documents and can_edit_documents say so to the page.  The breakdown
calls (S086 § 5.5, /<id>/calls) need contract:read_basic (403) and ticket:read somewhere (403);
each row passes the ticket predicate (unit_access_condition over ticket:read, as tickets._visible_condition), so the
card never lists a ticket the reader could not open and sends no count of the others; "N of M calls used" comes only
when the reader holds ticket:read at every active unit of each site of the contract's machines (complete, S087
§ 5.7).  No contract field beyond the vendor's name and the sites' codes.

LOCK ORDER (S080 § 5.6, S081 § 5.5).  The database runs REPEATABLE READ; each write decides from its locking reads,
and access checks are plain reads.  Per write this module takes at most one exclusive contract lock and one
exclusive line lock, then only shared locks; the contract lock is the first statement of every write on an
existing contract, so every plain read comes after it.
- Create: contract:edit by the decorator, before the transaction (403) → the vendor LOCK IN SHARE MODE
  (masters.check_active_vendor: missing or inactive 400) → the insert (its shared foreign-key lock on the vendor,
  already held) → the answer, read in the transaction.  No site lock (S087).
- Change: the contracts row FOR UPDATE, first (404) → plain access checks (404, 403) and the rules on the merged
  values → the vendor LOCK IN SHARE MODE only when vendor_id changes → update_row (a new vendor's shared
  foreign-key lock, already held) → the answer.
- Add a machine: the contracts row FOR UPDATE (404) → plain: read_basic 404, contract:edit 403, active 409 (from
  the locked row), the price dropped without contract:read_senior → the node (1) LOCK IN SHARE MODE (missing
  400; scrapped 409, from this row) → plain: the node's units (400) → the insert
  (shared foreign-key locks on the contract, held exclusive, and the node, held shared; uq_contract_equipment
  409) → the history line (equipment_events, inserted) → the answer.
- Change a price: the contracts row FOR UPDATE (404) → plain: 404, contract:edit 403, contract:read_senior 403 →
  the contract_equipment row FOR UPDATE (404) → update_row → the answer.
- Remove a machine: the contracts row FOR UPDATE (404) → plain: 404, contract:edit 403 → the contract_equipment
  row FOR UPDATE (404) → the delete → the history line (a shared foreign-key lock on the node) → the answer.
- Renew (S085 § 5.8): the old contracts row FOR UPDATE, first (_lock_contract: 404, contract:edit 403) → plain:
  active 409 (from the locked row) → plain: a contract whose renewal_of_id is the old one 409 (every renewal locks the
  old contract first, so one committed before the lock was granted is seen; uq_contracts_renewal_of, v47, backs
  it) → _drop_gated, the call-out number, the rules → the
  vendor LOCK IN SHARE MODE (400) → the insert of the new contract (shared foreign-key locks on the vendor, held,
  and the old contract, held exclusive; the new row is this transaction's own, which no other
  transaction sees, locks or waits on before the commit) → plain: the old contract's lines, sorted by
  equipment_id; per line the node (1) LOCK IN SHARE MODE, in id order → per copied line the insert (shared
  foreign-key locks, held) and the history line → the answer.  It never waits on a second existing contract row.
- Documents (S083): documents.py locks the contract row FOR UPDATE through lock_contract_for_change, first in its
  transaction, then touches only equipment_documents rows (plain: 404, the write or purge key 403,
  contract:read_senior 403).
- Reads: plain, no lock; the sites of a contract (site_codes, LINE_SITES_SQL) too.  The breakdown calls (S086 § 5.8)
  too: plain reads on autocommit connections, each query its own snapshot, nothing written.
No deadlock cycle:
- The contract row: only this module's functions lock it, always first in their transaction (the PUT, the three
  line writes, and documents.py's writes through lock_contract_for_change); nothing holds another lock and then
  waits on it.  The reminder scan (S084) is the one path that holds several, in id order: the daily
  contract_reminder_scan (alerts.lock_contract_for_scan) locks several contract rows FOR UPDATE in id order, then
  writes only their reminder columns and task_queue rows; every route holds at most one existing contract row
  (the renewal also inserts one), taken first, so no cycle.  The renewal (S085), after the old contract, waits
  only on the vendor and nodes (1), which no holder of a contract row holds exclusive.
- The contract_equipment row: only this module locks it, after its contract; no other module reads it with a lock.
- The node (1): taken shared only, after the contract.  equipment.py's writes (move, scrap, edit), meters.py,
  item_properties.py, documents.py and tickets.py's raise hold (1) exclusive and never wait on a contract or a
  line row, so an add waiting on (1) waits behind a writer that finishes.  documents.py's node path holds (1)
  exclusive and waits on no contract row; its contract path (S083) holds the contract row and no (1).  A scrap waiting
  for an add's shared lock gets it after the add commits; a scrapped node keeps its line.  The renewal holds several
  nodes shared, in id order.  A residual, accepted (S085 § 5.8): a move holds the node (1) then its target parent (2),
  and a scrap locks a subtree top-down (equipment.py's "one accepted deadlock"); a renewal holding one covered node
  shared and waiting for another, at the same instant as such a move or scrap of those two nodes, can meet a cycle.
  MariaDB rolls one back (1213, the plain 500 of api_common._operational_error); the renewal leaves nothing, and
  the engineer taps again.
- Two renewals of one contract serialise on the old contract's row; the second meets the renewal check (409).
- equipment_events rows are inserted, never locked by anyone.
- The vendor row: masters.py's vendor update locks only its own row and waits on nothing after it; a person write
  takes the person, then the vendor shared.  Neither waits on a contract lock a contract write holds, so a
  contract write waiting on the vendor waits behind a writer that finishes.  No contract write locks a site row
  (S087).
- Two contract writes: creates share the vendor lock; two writes on one contract serialise on its row;
  two adds of one node to two contracts share the node's lock.
"""

from datetime import datetime, time, timedelta

from flask import Blueprint, jsonify, request

from api_common import MAX_PER_PAGE, UNIQUE_KEY_ERRORS, ApiError, actor, clean_body, enum_arg, int_arg
from auth_utils import check_perm, has_perm, require_perm
from config_rbac import ASSIGNABLE_ROLES
from contracts_core import (
    CARD_ENDED_DAYS, CONTRACT_TYPES, DEFAULT_STATUS, GATED_FIELDS, LINE_GATED_FIELDS, LINE_SITE_JOINS, LINE_SITES_SQL,
    RENEW_INACTIVE, RENEWAL_RACE, STATUS_FILTERS, already_renewed, breakdown_calls_error, call_figures, calls_total,
    calls_used, card_items, contract_status, event_text, newest_end_first, period_error, renewal_lines,
    renewal_period, status_bounds, validate_contract, validate_line, vendor_warning,
)
from db_helpers import count, get_db, insert_row, marks, row_to_dict, transaction, update_row
from equipment import (
    IST, NODE_JOINS, accessible_unit_ids, load_node_for_user, node_path, unit_access_condition, write_events,
)
from equipment_core import SCRAPPED
from masters import check_active_vendor
from tickets import READ_KEY as TICKET_READ, events_by_ticket
from tickets_core import MACHINE_LEVEL, is_breakdown, is_overdue

contracts_bp = Blueprint("contracts", __name__)

READ_BASIC = "contract:read_basic"
READ_CALLOUT = "contract:read"
READ_COST = "contract:read_senior"
EDIT = "contract:edit"

UNIQUE_KEY_ERRORS.update({
    "uq_contract_equipment": ("equipment_id", "This machine is already on the contract."),
    "uq_contracts_renewal_of": (None, RENEWAL_RACE),   # S085 § 5.5: two renewals at one instant
})

# The machine lines' sums (S081 § 4.2) and the contract's sites (S087 § 5.2, the lines' current sites, by code; a
# site code holds no comma, masters_core.SITE_CODE_RE): computed on every read, never stored.  price_total stays
# NULL while no line has a price; site_codes while there is no line.
_CONTRACT_COLUMNS = (
    "SELECT c.*, v.name AS vendor_name, v.active AS vendor_active,"
    " COALESCE(ce.machine_count, 0) AS machine_count, COALESCE(ce.priced_count, 0) AS priced_count,"
    " ce.price_total, cs.site_codes"
)
_CONTRACT_FROM = (
    " FROM contracts c"
    " JOIN vendors v ON v.id = c.vendor_id"
    " LEFT JOIN (SELECT contract_id, COUNT(*) AS machine_count, COUNT(price) AS priced_count,"
    " SUM(price) AS price_total FROM contract_equipment GROUP BY contract_id) ce ON ce.contract_id = c.id"
    " LEFT JOIN (SELECT ce.contract_id, GROUP_CONCAT(DISTINCT s.code ORDER BY s.code SEPARATOR ',') AS site_codes"
    " FROM contract_equipment ce" + LINE_SITE_JOINS + " GROUP BY ce.contract_id) cs ON cs.contract_id = c.id"
)
_CONTRACT_SELECT = _CONTRACT_COLUMNS + _CONTRACT_FROM

# The card's rows (S082 § 5.1, BS1-01): every contract with a line on one of the nodes, each row once per line
# (cl.equipment_id; ``ce`` is the sums' alias above).  The caller adds the node ids and the dates.
_CARD_SELECT = (
    f"{_CONTRACT_COLUMNS}, cl.equipment_id{_CONTRACT_FROM}"
    " JOIN contract_equipment cl ON cl.contract_id = c.id"
)

# The card's item (S082 § 5.2): the keys kept from _contract_out's answer; never a price, a total or a cost note
_CARD_KEYS = ("title", "contract_type", "vendor_name", "from_date", "to_date", "status", "response_hours",
              "covers_labour", "covers_parts", "covers_consumables", "covers_breakdown_calls",
              "breakdown_calls_per_year", "only_vendor_repairs", "can_read_callout", "callout_number")

INACTIVE_NO_ADD = "This contract is inactive. Set it active in Masters › Contracts, then add machines."
CHOOSE_MACHINE = "Choose a machine."
SCRAPPED_NO_ADD = "A scrapped machine cannot be added to a contract."
LINE_MISSING = "This machine is not on the contract."


def _today():
    return datetime.now(IST).date()


def _flags():
    """The reader's contract flags (§ 6.2), the same for every contract since the keys are global (S087 § 5.1):
    computed once per request by the route and passed on."""
    can_edit, can_read_cost = has_perm(EDIT), has_perm(READ_COST)
    return {
        "can_edit": can_edit,
        "can_read_callout": has_perm(READ_CALLOUT),
        "can_read_cost": can_read_cost,
        # The contract's documents (S083 § 6.1): read with read_senior, written with edit and read_senior
        "can_read_documents": can_read_cost,
        "can_edit_documents": can_read_cost and can_edit,
    }


def _contract_out(row, flags, today):
    """The one answer builder (§ 5.4, § 6.1): a gated field is left out for a reader without its key, and
    renewal_of_id is not sent (R02.4)."""
    item = row_to_dict(row)
    del item["renewal_of_id"]
    # The reminder markers are the daily scan's (S084), not the contract's
    del item["first_reminder_for"]
    del item["second_reminder_for"]
    item["site_codes"] = row["site_codes"].split(",") if row["site_codes"] else []
    item["status"] = contract_status(row["from_date"], row["to_date"], today)
    item.update(flags)
    if not flags["can_read_callout"]:
        del item["callout_number"]
    if not flags["can_read_cost"]:
        del item["cost_note"]
        del item["price_total"]
        del item["priced_count"]
    return item


def _contract_row(cur, contract_id):
    cur.execute(f"{_CONTRACT_SELECT} WHERE c.id = %s", (contract_id,))
    return cur.fetchone()


# A line's node, as the contract page shows it (S081 § 6.1): plain reads, never with a lock
_LINE_SELECT = (
    "SELECT ce.equipment_id, ce.price, ce.created_at, ce.created_by, ce.updated_at, ce.updated_by,"
    " e.code, e.name, e.level, e.lifecycle, u.id AS root_unit_id, s.code AS site_code,"
    " u.code AS unit_code, p.code AS p_code, gp.code AS gp_code"
    " FROM contract_equipment ce JOIN equipment e ON e.id = ce.equipment_id" + NODE_JOINS
)

# The other contracts' lines that overlap a line of this one (S081 § 5.6): another active contract of the same
# type whose period meets this one's, with a line on the same node, an ancestor of it (x.parent_id,
# xp.parent_id) or a part of it (o.parent_id, op.parent_id); the tree has at most three levels (S002).
_OVERLAP_SELECT = (
    "SELECT ce.equipment_id, c2.id AS contract_id, c2.title, c2.contract_type, c2.from_date, c2.to_date,"
    " o.id AS on_id, o.code AS on_code"
    " FROM contract_equipment ce"
    " JOIN equipment x ON x.id = ce.equipment_id"
    " LEFT JOIN equipment xp ON xp.id = x.parent_id"
    " JOIN contracts c2 ON c2.id <> ce.contract_id"
    " JOIN contract_equipment ce2 ON ce2.contract_id = c2.id"
    " JOIN equipment o ON o.id = ce2.equipment_id"
    " LEFT JOIN equipment op ON op.id = o.parent_id"
    " WHERE ce.contract_id = %s AND c2.active = 1 AND c2.contract_type = %s"
    " AND c2.from_date <= %s AND c2.to_date >= %s"
    " AND (o.id = x.id OR o.id = x.parent_id OR o.id = xp.parent_id OR o.parent_id = x.id OR op.parent_id = x.id)"
)

_LINE_STAMPS = ("price", "created_at", "created_by", "updated_at", "updated_by")


def _machine_lines(cur, contract, flags):
    """The contract's machine lines by code (§ 6.1).  Every line is listed to a read_basic holder; only the link
    (can_open) follows the reader's units (B7).  The price is left out without can_read_cost."""
    cur.execute(f"{_LINE_SELECT} WHERE ce.contract_id = %s ORDER BY e.code", (contract["id"],))
    rows = cur.fetchall()
    unit_ids = accessible_unit_ids(cur)
    lines = []
    for row in rows:
        line = {
            "equipment_id": row["equipment_id"], "code": row["code"], "name": row["name"], "level": row["level"],
            "lifecycle": row["lifecycle"], "full_path": node_path(row), "site_code": row["site_code"],
            "can_open": unit_ids is None or row["root_unit_id"] in unit_ids,
            **row_to_dict({key: row[key] for key in _LINE_STAMPS}),
        }
        if not flags["can_read_cost"]:
            del line["price"]
        lines.append(line)
    return lines


def _overlaps(cur, contract, lines):
    """``{equipment_id: [overlap, …]}`` for the lines of an active contract (§ 5.6), every other contract (read_basic
    is global, S087 § 5.3).  on_code is None when the other line is on the same node.  An inactive contract shows
    none, and an inactive other contract counts in none."""
    if not contract["active"] or not lines:
        return {}
    cur.execute(f"{_OVERLAP_SELECT} ORDER BY c2.from_date, c2.id, o.code",
                [contract["id"], contract["contract_type"], contract["to_date"], contract["from_date"]])
    found = {}
    for row in cur.fetchall():
        found.setdefault(row["equipment_id"], []).append({
            "contract_id": row["contract_id"], "title": row["title"], "contract_type": row["contract_type"],
            "from_date": row["from_date"].isoformat(), "to_date": row["to_date"].isoformat(),
            "on_code": None if row["on_id"] == row["equipment_id"] else row["on_code"],
        })
    return found


def _detail(cur, row, flags, today):
    """The contract with its machines (S081 § 6.1): the one place the detail is built, for the GET and every
    write's answer (BS1-01)."""
    item = _contract_out(row, flags, today)
    lines = _machine_lines(cur, row, flags)
    overlaps = _overlaps(cur, row, lines)
    for line in lines:
        line["overlaps"] = overlaps.get(line["equipment_id"], [])
    item["machines"] = lines
    item.update(_renewal_links(cur, row))
    # S085 § 6.1: the button shows only when the renewal would pass the route's refusals
    item["can_renew"] = flags["can_edit"] and bool(row["active"]) and item["renewed_by"] is None
    if item["can_renew"]:
        item["renewal"] = _renewal_offer(row, lines)
    return item


_LINK_SELECT = "SELECT id, title, from_date, to_date, active FROM contracts"


def _link_out(link):
    if link is None:
        return None
    return {**row_to_dict(link), "active": bool(link["active"])}


def _renewal_links(cur, row):
    """The chain (S085 § 6.1): the contract this one renews and its renewal (at most one, v47), plain reads.  A
    reader of one may read the other: contract:read_basic is global (S087)."""
    renewal_of = None
    if row["renewal_of_id"] is not None:
        cur.execute(f"{_LINK_SELECT} WHERE id = %s", (row["renewal_of_id"],))
        renewal_of = cur.fetchone()
    cur.execute(f"{_LINK_SELECT} WHERE renewal_of_id = %s", (row["id"],))
    return {"renewal_of": _link_out(renewal_of), "renewed_by": _link_out(cur.fetchone())}


def _renewal_offer(row, lines):
    """What the renew dialog proposes (S085 § 5.2, § 5.3): the period and the machines copied and skipped.  The
    route decides again from its locked rows."""
    new_from, new_to = renewal_period(row["from_date"], row["to_date"])
    copied, skipped = renewal_lines(lines)
    return {"from_date": new_from.isoformat() if new_from else None,
            "to_date": new_to.isoformat() if new_to else None,
            "machines": copied, "skipped": skipped}


def _answer(cur, contract_id):
    """The answer of a write, read inside its transaction: the detail."""
    row = _contract_row(cur, contract_id)
    return _detail(cur, row, _flags(), _today())


def _drop_gated(clean, fields=GATED_FIELDS):
    """A gated field the writer may not read is ignored (§ 5.4): their save leaves the stored value as it was.
    ``fields`` maps each gated field to its key: the contract's (GATED_FIELDS) or a line's (LINE_GATED_FIELDS)."""
    for field, key in fields.items():
        if field in clean and not has_perm(key):
            del clean[field]


def _check_rules(clean, stored):
    """The period and breakdown calls on the merged values (``stored`` the locked row, or {} on a create)."""
    error = period_error(clean.get("from_date", stored.get("from_date")), clean.get("to_date", stored.get("to_date")),
                         "to_date" in clean)
    if error:
        raise ApiError(error[1], 400, error[0])
    message = breakdown_calls_error(clean.get("covers_breakdown_calls", stored.get("covers_breakdown_calls", 0)),
                                    clean.get("breakdown_calls_per_year"))
    if message:
        raise ApiError(message, 400, "breakdown_calls_per_year")


def _list_filters():
    """The query of § 6.2 -> (site_id, vendor_id, contract_type, status, include_inactive); a bad value is a 400.
    An empty status is the default."""
    site_id = int_arg("site_id", None, 1)
    vendor_id = int_arg("vendor_id", None, 1)
    contract_type = enum_arg("contract_type", CONTRACT_TYPES)
    status = enum_arg("status", STATUS_FILTERS) if request.args.get("status") else DEFAULT_STATUS
    return site_id, vendor_id, contract_type, status, request.args.get("include_inactive") == "1"


# ---------------------------------------------------------------------------
# Routes (§ 6)
# ---------------------------------------------------------------------------

@contracts_bp.route("/", strict_slashes=False)
@require_perm(READ_BASIC)
def list_contracts():
    """Every contract, filtered (§ 5.3, § 6.2; S087 § 5.10).  The Site filter keeps the contracts with a machine
    at that site (an unknown site: an empty list); ``sites`` lists every site for the filter; the flags are the
    reader's, the same for every contract."""
    site_id, vendor_id, contract_type, status, include_inactive = _list_filters()
    today = _today()
    flags = _flags()
    where, params = [], []
    if site_id is not None:
        where.append("EXISTS (SELECT 1 FROM contract_equipment ce" + LINE_SITE_JOINS
                     + " WHERE ce.contract_id = c.id AND s.id = %s)")
        params.append(site_id)
    if vendor_id is not None:
        where.append("c.vendor_id = %s")
        params.append(vendor_id)
    if contract_type is not None:
        where.append("c.contract_type = %s")
        params.append(contract_type)
    if not include_inactive:
        where.append("c.active = 1")
    for column, operator, value in status_bounds(status, today):
        where.append(f"c.{column} {operator} %s")   # column and operator are code constants
        params.append(value)
    condition = " AND ".join(where) or "1 = 1"
    direction = "DESC" if newest_end_first(status) else "ASC"
    with get_db().cursor() as cur:
        cur.execute("SELECT id, code, name, active FROM sites ORDER BY code")
        sites = [row_to_dict(s) for s in cur.fetchall()]
        total = count(cur, f"SELECT COUNT(*) AS n FROM contracts c WHERE {condition}", params)
        cur.execute(f"{_CONTRACT_SELECT} WHERE {condition} ORDER BY c.to_date {direction}, c.id {direction}"
                    " LIMIT %s", [*params, MAX_PER_PAGE])
        items = [_contract_out(row, flags, today) for row in cur.fetchall()]
    return jsonify({
        "items": items,
        "total": total,
        "sites": sites,
        "can_add": flags["can_edit"],
        "can_read_callout": flags["can_read_callout"],
        "can_read_cost": flags["can_read_cost"],
    })


@contracts_bp.route("/<int:contract_id>")
@require_perm(READ_BASIC)
def get_contract(contract_id):
    with get_db().cursor() as cur:
        row = _contract_row(cur, contract_id)
        if row is None:
            raise ApiError("Not found", 404)
        return jsonify(_detail(cur, row, _flags(), _today()))


def _via(node, via_id):
    """The ancestor whose line brought the contract to the node (S082 § 5.1), from the node row's columns; None on
    the node itself.  ``level`` lets the card name a machine or a component-unit."""
    if via_id is None:
        return None
    prefix = "p" if via_id == node["parent_id"] else "gp"
    return {"id": via_id, "code": node[f"{prefix}_code"], "name": node[f"{prefix}_name"],
            "level": node[f"{prefix}_level"]}


@contracts_bp.route("/for-equipment/<int:node_id>")
@require_perm(READ_BASIC)
def contracts_for_equipment(node_id):
    """The Under contract card (S082 § 5.1, § 5.2): the contracts in force on the node or its ancestors, and those
    ended in the last CARD_ENDED_DAYS, wherever their other machines stand (S087 § 5.4).  One plain read; the item
    goes through _contract_out, then keeps only _CARD_KEYS."""
    today = _today()
    flags = _flags()
    with get_db().cursor() as cur:
        _locked, node = load_node_for_user(cur, node_id, for_update=False)
        node_ids = [i for i in (node["id"], node["parent_id"], node["gp_id"]) if i is not None]
        cur.execute(f"{_CARD_SELECT} WHERE cl.equipment_id IN ({marks(node_ids)}) AND c.active = 1"
                    " AND c.from_date <= %s AND c.to_date >= %s",
                    [*node_ids, today, today - timedelta(days=CARD_ENDED_DAYS)])
        rows = cur.fetchall()
    items = []
    for found in card_items(rows, node, today):
        out = _contract_out(found["row"], flags, today)
        items.append({"contract_id": out["id"], **{key: out[key] for key in _CARD_KEYS if key in out},
                      "via": _via(node, found["via_id"])})
    return jsonify({"items": items})


@contracts_bp.route("/", methods=["POST"], strict_slashes=False)
@require_perm(EDIT)
def create_contract():
    """A contract, company-wide (§ 5.6 Create; S087 § 5.5): no site; a ``site_id`` sent is ignored."""
    clean = clean_body(validate_contract, creating=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        _drop_gated(clean)
        _check_rules(clean, {})
        check_active_vendor(cur, clean["vendor_id"])
        contract_id = insert_row(cur, "contracts", clean, actor())
        answer = _answer(cur, contract_id)
    return jsonify(answer), 201


@contracts_bp.route("/<int:contract_id>", methods=["PUT"])
@require_perm(EDIT)
def change_contract(contract_id):
    """Any subset of the fields (§ 5.6 Change).  Every field sent is written; the vendor may change to an active
    one.  A ``site_id`` sent is ignored (S087 § 5.5)."""
    clean = clean_body(validate_contract, creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        locked = _lock_contract(cur, contract_id)
        _drop_gated(clean)
        _check_rules(clean, locked)
        if clean.get("vendor_id", locked["vendor_id"]) != locked["vendor_id"]:
            check_active_vendor(cur, clean["vendor_id"])
        update_row(cur, "contracts", contract_id, clean, actor())
        answer = _answer(cur, contract_id)
    return jsonify(answer)


# ---------------------------------------------------------------------------
# The machines a contract covers (S081 § 5, § 6; LOCK ORDER above)
# ---------------------------------------------------------------------------

def _lock_contract(cur, contract_id, key=EDIT):
    """Every write's first statement on an existing contract: the contract FOR UPDATE, then read_basic (404) and
    ``key`` (403; contract:edit for the contract and line writes), both global (S087 § 5.1) -> the locked row.  The
    read_basic 404 cannot fire today (every role holds it); it stays as the fail-closed habit (S087 § 5.1)."""
    cur.execute("SELECT * FROM contracts WHERE id = %s FOR UPDATE", (contract_id,))
    locked = cur.fetchone()
    if locked is None or not has_perm(READ_BASIC):
        raise ApiError("Not found", 404)
    check_perm(key)
    return locked


def _lock_line(cur, contract_id, equipment_id):
    """The line FOR UPDATE, after its contract -> its id; 404 when the machine is not on the contract."""
    cur.execute("SELECT id FROM contract_equipment WHERE contract_id = %s AND equipment_id = %s FOR UPDATE",
                (contract_id, equipment_id))
    line = cur.fetchone()
    if line is None:
        raise ApiError(LINE_MISSING, 404)
    return line["id"]


def _check_node(cur, equipment_id):
    """The node an add names (§ 5.2 rules 2-3): its shared lock (1), then a plain read for its units.  Any site
    (S087 § 5.4), but inside the adder's units and not scrapped."""
    cur.execute("SELECT id, lifecycle FROM equipment WHERE id = %s LOCK IN SHARE MODE", (equipment_id,))   # (1)
    locked = cur.fetchone()
    if locked is None:
        raise ApiError(CHOOSE_MACHINE, 400, "equipment_id")
    cur.execute(f"SELECT u.id AS root_unit_id FROM equipment e{NODE_JOINS} WHERE e.id = %s", (equipment_id,))
    node = cur.fetchone()
    unit_ids = accessible_unit_ids(cur)
    if node is None or (unit_ids is not None and node["root_unit_id"] not in unit_ids):
        raise ApiError(CHOOSE_MACHINE, 400, "equipment_id")
    if locked["lifecycle"] == SCRAPPED:
        raise ApiError(SCRAPPED_NO_ADD, 409, "equipment_id")


@contracts_bp.route("/<int:contract_id>/equipment", methods=["POST"])
@require_perm(EDIT)
def add_machine(contract_id):
    """A node of any site inside the adder's units, any level (§ 5.2; S087 § 5.4).  The price is kept only for a
    contract:read_senior holder (§ 5.4)."""
    clean = clean_body(validate_line, creating=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        locked = _lock_contract(cur, contract_id)
        if not locked["active"]:
            raise ApiError(INACTIVE_NO_ADD, 409)
        _drop_gated(clean, LINE_GATED_FIELDS)
        _check_node(cur, clean["equipment_id"])
        insert_row(cur, "contract_equipment", {"contract_id": contract_id, **clean}, actor())
        write_events(cur, clean["equipment_id"], [("contract_added", None, event_text(locked))])
        answer = _answer(cur, contract_id)
    return jsonify(answer), 201


@contracts_bp.route("/<int:contract_id>/equipment/<int:equipment_id>", methods=["PUT"])
@require_perm(EDIT)
def change_price(contract_id, equipment_id):
    """A line's price (§ 5.4): only with contract:edit and contract:read_senior, else 403 (B3).  No
    history line: it would carry the price; the line's updated_at and updated_by record the change.  Allowed on an
    inactive contract (BR1-03)."""
    clean = clean_body(validate_line, creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        _lock_contract(cur, contract_id)
        check_perm(READ_COST)
        _drop_gated(clean, LINE_GATED_FIELDS)
        line_id = _lock_line(cur, contract_id, equipment_id)
        update_row(cur, "contract_equipment", line_id, clean, actor())
        answer = _answer(cur, contract_id)
    return jsonify(answer)


@contracts_bp.route("/<int:contract_id>/equipment/<int:equipment_id>", methods=["DELETE"])
@require_perm(EDIT)
def remove_machine(contract_id, equipment_id):
    """A line taken off (B5): deleted, with its price (§ 9 Q3); the machine's history keeps the add and the
    remove.  Allowed on an inactive contract (BR1-03)."""
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        locked = _lock_contract(cur, contract_id)
        line_id = _lock_line(cur, contract_id, equipment_id)
        cur.execute("DELETE FROM contract_equipment WHERE id = %s", (line_id,))
        write_events(cur, equipment_id, [("contract_removed", event_text(locked), None)])
        answer = _answer(cur, contract_id)
    return jsonify(answer)


# ---------------------------------------------------------------------------
# Renewal (S085 § 5, § 6; LOCK ORDER above)
# ---------------------------------------------------------------------------

@contracts_bp.route("/<int:contract_id>/renew", methods=["POST"])
@require_perm(EDIT)
def renew_contract(contract_id):
    """The next contract with the terms sent (the dialog fills them from the old one), renewal_of_id the old one;
    its machines not scrapped copied without prices, wherever they stand, each with a history line (§ 5.3, § 5.4;
    S087 § 5.5).  The old contract, its prices, cost note and documents are not changed."""
    clean = clean_body(validate_contract, creating=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        old = _lock_contract(cur, contract_id)
        if not old["active"]:
            raise ApiError(RENEW_INACTIVE, 409)
        # Every renewal locks the old contract first, so one committed before our lock is seen; v47's key backs it
        cur.execute("SELECT id, title FROM contracts WHERE renewal_of_id = %s", (contract_id,))
        renewal = cur.fetchone()
        if renewal is not None:
            raise ApiError(already_renewed(renewal["title"]), 409)
        _drop_gated(clean)
        if not has_perm(READ_CALLOUT):
            # The vendor's breakdown line, not a fact of one period: kept for a renewer who may not read it (§ 5.4)
            clean["callout_number"] = old["callout_number"]
        _check_rules(clean, {})
        check_active_vendor(cur, clean["vendor_id"])
        new_id = insert_row(cur, "contracts", {**clean, "renewal_of_id": contract_id}, actor())
        lines = sorted(_machine_lines(cur, old, _flags()), key=lambda line: line["equipment_id"])
        for line in lines:   # node (1) shared, in id order, before any line insert; "scrapped" from the locked row
            cur.execute("SELECT lifecycle FROM equipment WHERE id = %s LOCK IN SHARE MODE", (line["equipment_id"],))
            line["lifecycle"] = cur.fetchone()["lifecycle"]
        copied, skipped = renewal_lines(lines)
        added = event_text(clean)
        for machine in copied:
            insert_row(cur, "contract_equipment", {"contract_id": new_id, "equipment_id": machine["equipment_id"]},
                       actor())
            write_events(cur, machine["equipment_id"], [("contract_added", None, added)])
        answer = {**_answer(cur, new_id), "skipped": skipped}
    return jsonify(answer), 201


# ---------------------------------------------------------------------------
# Breakdown calls (S086 § 5, § 6): read-only, no lock
# ---------------------------------------------------------------------------

# A call's ticket: the machine at raise (t.equipment_id) and the part as it stands (t.component_id)
_CALL_SELECT = (
    "SELECT t.id, t.serial, t.state, t.intensity, t.occurred_at, t.not_a_fault, t.planned_date,"
    " m.id AS m_id, m.code AS m_code, m.name AS m_name, c.id AS c_id, c.code AS c_code, c.name AS c_name"
    " FROM tickets t JOIN equipment m ON m.id = t.equipment_id LEFT JOIN equipment c ON c.id = t.component_id"
)
# The ticket is on a line node (§ 5.1 rule 1): the machine, the part, or the part's current parent
_ON_A_LINE = ("EXISTS (SELECT 1 FROM contract_equipment ce WHERE ce.contract_id = %s"
              " AND ce.equipment_id IN (t.equipment_id, t.component_id, c.parent_id))")
# A Team record linked to the vendor now is an assignee or has a labour row (§ 5.1 rule 3)
_BY_THE_VENDOR = (
    "(EXISTS (SELECT 1 FROM ticket_assignees ta JOIN people pa ON pa.id = ta.person_id"
    " WHERE ta.ticket_id = t.id AND pa.vendor_id = %s)"
    " OR EXISTS (SELECT 1 FROM ticket_labour tl JOIN people pl ON pl.id = tl.person_id"
    " WHERE tl.ticket_id = t.id AND pl.vendor_id = %s))"
)


def _covered_nodes(cur, contract_id):
    """Query 1 (§ 5.1): the contract's lines -> ``(machines, parts)``: the machines the lines stand on (the root of
    each line's tree, as NODE_JOINS), and the part lines with their current children (a component-unit's
    components).  Both empty when the contract has no line."""
    cur.execute("SELECT ce.equipment_id, e.level, COALESCE(gp.id, p.id, e.id) AS machine_id"
                " FROM contract_equipment ce JOIN equipment e ON e.id = ce.equipment_id"
                " LEFT JOIN equipment p ON p.id = e.parent_id LEFT JOIN equipment gp ON gp.id = p.parent_id"
                " WHERE ce.contract_id = %s", (contract_id,))
    rows = cur.fetchall()
    machines = sorted({row["machine_id"] for row in rows})
    parts = sorted({row["equipment_id"] for row in rows if row["level"] != MACHINE_LEVEL})
    if parts:
        cur.execute(f"SELECT id FROM equipment WHERE parent_id IN ({marks(parts)})", parts)
        parts = sorted({*parts, *(row["id"] for row in cur.fetchall())})
    return machines, parts


def _call_rows(cur, contract):
    """Query 2 (§ 5.1): the contract's calls the reader may open, newest first.  A covered machine's tickets come by
    t.equipment_id; a covered part's by t.component_id, wherever the part stood when raised (BR1-03).  [] when the
    contract has no line or the reader holds ticket:read at no unit."""
    machines, parts = _covered_nodes(cur, contract["id"])
    visible = unit_access_condition(cur, TICKET_READ, "t.unit_id", "m.unit_id")
    if not machines or visible is None:
        return []
    on_nodes, node_params = f"t.equipment_id IN ({marks(machines)})", list(machines)
    if parts:
        on_nodes = f"({on_nodes} OR t.component_id IN ({marks(parts)}))"
        node_params += parts
    visible_sql, visible_params = visible
    start = datetime.combine(contract["from_date"], time.min)
    end = datetime.combine(contract["to_date"] + timedelta(days=1), time.min)   # both end days count
    cur.execute(f"{_CALL_SELECT} WHERE {on_nodes} AND t.occurred_at >= %s AND t.occurred_at < %s"
                f" AND {_ON_A_LINE} AND {_BY_THE_VENDOR} AND {visible_sql}"
                " ORDER BY t.occurred_at DESC, t.id DESC",
                [*node_params, start, end, contract["id"], contract["vendor_id"], contract["vendor_id"],
                 *visible_params])
    return cur.fetchall()


def _vendor_people(cur, ticket_ids, vendor_id):
    """Query 4 (§ 5.1): the vendor's people on each ticket, as assignee or on a labour row, each once, by name ->
    ``{ticket_id: [{id, name}, …]}``."""
    people = {ticket_id: [] for ticket_id in ticket_ids}
    if not ticket_ids:
        return people
    ids = marks(ticket_ids)
    cur.execute("SELECT DISTINCT w.ticket_id, p.id, p.name FROM"
                f" (SELECT ticket_id, person_id FROM ticket_assignees WHERE ticket_id IN ({ids})"
                f" UNION SELECT ticket_id, person_id FROM ticket_labour WHERE ticket_id IN ({ids})) w"
                " JOIN people p ON p.id = w.person_id WHERE p.vendor_id = %s ORDER BY w.ticket_id, p.name, p.id",
                [*ticket_ids, *ticket_ids, vendor_id])
    for row in cur.fetchall():
        people[row["ticket_id"]].append({"id": row["id"], "name": row["name"]})
    return people


def _vendor_reach(cur, vendor_id, sites):
    """§ 5.4, S087 § 5.7 -> ``(linked_count, {site code: assignable_count})``: the active Team records linked to the
    vendor, and per site of ``sites`` (the contract's line sites, ``{id, code}``) those of them whose role there may
    be assigned (ASSIGNABLE_ROLES)."""
    cur.execute("SELECT COUNT(*) AS linked FROM people WHERE vendor_id = %s AND active = 1", (vendor_id,))
    linked = cur.fetchone()["linked"]
    if not sites:
        return linked, {}
    roles = sorted(ASSIGNABLE_ROLES)
    site_ids = [site["id"] for site in sites]
    cur.execute("SELECT ms.site_id, COUNT(DISTINCT p.id) AS assignable FROM memberships ms"
                " JOIN people p ON p.id = ms.person_id AND p.vendor_id = %s AND p.active = 1"
                f" WHERE ms.site_id IN ({marks(site_ids)}) AND ms.role IN ({marks(roles)}) GROUP BY ms.site_id",
                [vendor_id, *site_ids, *roles])
    assignable = {row["site_id"]: row["assignable"] for row in cur.fetchall()}
    return linked, {site["code"]: assignable.get(site["id"], 0) for site in sites}


def _sees_covered_sites(cur, site_ids):
    """``complete`` (§ 5.5; S087 § 5.7, F4): the reader holds ticket:read at every active unit of every site of the
    contract's lines, so the listed calls are the contract's calls.  No line: no site, no calls, True."""
    unit_ids = accessible_unit_ids(cur, TICKET_READ)
    if unit_ids is None or not site_ids:
        return True
    cur.execute(f"SELECT id FROM units WHERE site_id IN ({marks(site_ids)}) AND active = 1", site_ids)
    return {row["id"] for row in cur.fetchall()} <= unit_ids


def _call_out(row, figures, people, today):
    plain = row_to_dict({**row, "back_in_service_at": figures["back_in_service_at"]})
    return {
        "id": plain["id"], "serial": plain["serial"], "state": plain["state"], "intensity": plain["intensity"],
        "is_breakdown": is_breakdown(plain["intensity"]),
        "overdue": is_overdue(row["state"], row["planned_date"], today),
        "not_a_fault": bool(plain["not_a_fault"]),
        "occurred_at": plain["occurred_at"], "back_in_service_at": plain["back_in_service_at"],
        "machine": {"id": plain["m_id"], "code": plain["m_code"], "name": plain["m_name"]},
        "component": ({"id": plain["c_id"], "code": plain["c_code"], "name": plain["c_name"]}
                      if plain["c_id"] is not None else None),
        "downtime_minutes": figures["downtime_minutes"],
        "vendor_waiting_minutes": figures["vendor_waiting_minutes"],
        "vendor_people": people,
    }


@contracts_bp.route("/<int:contract_id>/calls")
@require_perm(READ_BASIC)
@require_perm(TICKET_READ)
def contract_calls(contract_id):
    """The contract's breakdown calls (§ 5.1-§ 5.5, § 6): the tickets the reader may open, their figures, the
    total, the calls used (only for a reader of every unit of the lines' sites) and the vendor warning (an active
    contract not ended), with the sites where no linked person may be assigned.  Plain reads, no lock."""
    today = _today()
    now = datetime.now(IST).replace(tzinfo=None)
    with get_db().cursor() as cur:
        contract = _contract_row(cur, contract_id)
        if contract is None:
            raise ApiError("Not found", 404)
        cur.execute(LINE_SITES_SQL, (contract_id,))
        sites = cur.fetchall()
        rows = _call_rows(cur, contract)
        ids = [row["id"] for row in rows]
        events = events_by_ticket(cur, ids)
        people = _vendor_people(cur, ids, contract["vendor_id"])
        complete = _sees_covered_sites(cur, [site["id"] for site in sites])
        warning = None
        if contract["active"] and contract_status(contract["from_date"], contract["to_date"], today)["kind"] != "ended":
            warning = vendor_warning(*_vendor_reach(cur, contract["vendor_id"], sites))
    calls = [_call_out(row, call_figures(row["state"], bool(row["not_a_fault"]), events[row["id"]], now),
                       people[row["id"]], today) for row in rows]
    total = calls_total(calls)
    return jsonify({
        "calls": calls,
        "total": total,
        "complete": complete,
        "used": calls_used(total["count"], contract["breakdown_calls_per_year"], contract["from_date"],
                           contract["to_date"], complete),
        "warning": warning[0] if warning else None,
        "warning_sites": warning[1] if warning else [],
        "vendor_name": contract["vendor_name"],
        "site_codes": [site["code"] for site in sites],
    })


# ---------------------------------------------------------------------------
# The contract as a documents owner (S083 § 5.1; documents.py's OWNERS["contract"]).  Every document is behind
# contract:read_senior (D5; global since S087), on every route, also restore and purge.  No state rule (§ 5.3).
# ---------------------------------------------------------------------------

def _contract_access(row, key):
    """The plain reads' checks: missing or no read_basic 404, read_senior 403, then ``key`` 403 when given (all
    by the union, S087 § 5.9: equipment:purge_documents held at any site, as for a model's documents)."""
    if row is None or not has_perm(READ_BASIC):
        raise ApiError("Not found", 404)
    check_perm(READ_COST)
    if key is not None:
        check_perm(key)


def _contract_id_row(cur, contract_id):
    cur.execute("SELECT id FROM contracts WHERE id = %s", (contract_id,))
    return cur.fetchone()


def read_contract(cur, contract_id, _key=None):
    """documents.py's ``read`` (list, file, thumb): a plain read -> the row ``{id}``; 404 when missing, 403 without
    contract:read_senior."""
    row = _contract_id_row(cur, contract_id)
    _contract_access(row, None)
    return row


def read_contract_for_change(cur, contract_id, key):
    """documents.py's ``read_for_change``: a write's early refusals from a plain read (404, 403, and ``key`` 403),
    so a refused upload reads and writes no file (S006 § 5.6).  The decisions that count are
    lock_contract_for_change's."""
    row = _contract_id_row(cur, contract_id)
    _contract_access(row, key)
    return row


def lock_contract_for_change(cur, contract_id, key):
    """documents.py's ``lock_for_change`` and ``lock_for_purge`` (upload, retitle, remove, restore, purge), in the
    write transaction: the contract FOR UPDATE through _lock_contract (404, ``key`` 403), then contract:read_senior
    (403).  No state rule, so one function serves change and purge."""
    _lock_contract(cur, contract_id, key)
    check_perm(READ_COST)
