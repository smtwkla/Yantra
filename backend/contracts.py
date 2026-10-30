"""Vendor contracts — the API (docs/steps/S080-contract-register/1-brief.md; R02.1).  One record per vendor
contract at one site: its vendor (the vendors master, S079), type, period, what is covered, the PM visits agreed,
the response time, the call-out number, the *Only the vendor may repair* tick and a cost note.  The status comes
from the dates (contracts_core.contract_status), never stored.  Never deleted: one entered by mistake is set
inactive (ISO 9001 § 7.5).  The machines covered and their prices (contract_equipment, S081, R02.2; docs/steps/
S081-contract-equipment/1-brief.md): one line per node of the contract's site, any level, with an optional price
before GST; the total is their sum, never stored.  Each add and remove writes a line in the machine's history
(equipment_events), never with the price.

Thin shell: contracts_core holds the rules; this module checks access, locks, reads and stores.

ACCESS (S080 § 5.4, § 5.5; S081 § 5.4).  Four site-scoped keys, checked at the contract's site (has_perm_at).  A
contract belongs to a site, not a unit, so unit rows play no part in reading it (D8); a machine line's link
follows the reader's units (can_open), the line itself does not (B7).  contract:read_basic reads the terms and
the machines; contract:read adds callout_number; contract:read_senior adds cost_note, each line's price and the
contract's price_total and priced_count; contract:edit adds and changes contracts and lines.  Every answer goes
through _contract_out (and _machine_lines for the lines), which leaves a gated field out (absent, not null) for a
reader without its key, and every write drops a gated field the writer may not read (_drop_gated with
GATED_FIELDS or LINE_GATED_FIELDS), so their save leaves it as it was (ISO 27001 A.5.15).  A price change has no
other field: it needs contract:read_senior too, else 403 (S081 B3).

LOCK ORDER (S080 § 5.6, S081 § 5.5).  The database runs REPEATABLE READ; each write decides from its locking reads,
and access checks are plain reads.  Per write this module takes at most one exclusive contract lock and one
exclusive line lock, then only shared locks; the contract lock is the first statement of every write on an
existing contract, so every plain read comes after it.
- Create: the site LOCK IN SHARE MODE (missing or inactive 400) → contract:edit at the site (plain, 403) → the
  vendor LOCK IN SHARE MODE (masters.check_active_vendor: missing or inactive 400) → the insert (its shared
  foreign-key locks on the site and the vendor, already held) → the answer, read in the transaction.
- Change: the contracts row FOR UPDATE, first (404) → plain access checks (404, 403) and the rules on the merged
  values → the vendor LOCK IN SHARE MODE only when vendor_id changes → update_row (a new vendor's shared
  foreign-key lock, already held) → the answer.
- Add a machine: the contracts row FOR UPDATE (404) → plain: read_basic 404, contract:edit 403, active 409 (from
  the locked row), the price dropped without contract:read_senior → the node (1) LOCK IN SHARE MODE (missing
  400; scrapped 409, from this row) → plain: the node's site and units through NODE_JOINS (400) → the insert
  (shared foreign-key locks on the contract, held exclusive, and the node, held shared; uq_contract_equipment
  409) → the history line (equipment_events, inserted) → the answer.
- Change a price: the contracts row FOR UPDATE (404) → plain: 404, contract:edit 403, contract:read_senior 403 →
  the contract_equipment row FOR UPDATE (404) → update_row → the answer.
- Remove a machine: the contracts row FOR UPDATE (404) → plain: 404, contract:edit 403 → the contract_equipment
  row FOR UPDATE (404) → the delete → the history line (a shared foreign-key lock on the node) → the answer.
- Reads: plain, no lock.
No deadlock cycle:
- The contract row: only this module locks it, always first in its transaction (the PUT and the three line
  writes); nothing holds another lock and then waits on it.
- The contract_equipment row: only this module locks it, after its contract; no other module reads it with a lock.
- The node (1): taken shared only, after the contract.  equipment.py's writes (move, scrap, edit), meters.py,
  item_properties.py, documents.py and tickets.py's raise hold (1) exclusive and never wait on a contract or a
  line row, so an add waiting on (1) waits behind a writer that finishes.  A scrap waiting for an add's shared
  lock gets it after the add commits; a scrapped node keeps its line.
- equipment_events rows are inserted, never locked by anyone.
- The vendor row: masters.py's vendor update locks only its own row and waits on nothing after it; a person write
  takes the person, then the vendor shared.  Neither waits on a contract or site lock a contract write holds, so a
  contract write waiting on the vendor waits behind a writer that finishes.
- The site row: masters.py's site update locks site rows (_clear_default_site a second one), never a vendor or a
  contract row; it may wait for a create's shared lock, never the reverse.  People writes take the site through
  the membership foreign key, shared, which is compatible.
- Two contract writes: creates share the site and vendor locks; two writes on one contract serialise on its row;
  two adds of one node to two contracts share the node's lock.
"""

from datetime import datetime

from flask import Blueprint, jsonify, request

from api_common import MAX_PER_PAGE, UNIQUE_KEY_ERRORS, ApiError, actor, clean_body, enum_arg, int_arg
from auth_utils import has_perm_at, require_perm, require_perm_at
from contracts_core import (
    CONTRACT_TYPES, DEFAULT_STATUS, GATED_FIELDS, LINE_GATED_FIELDS, SITE_INACTIVE, SITE_KEPT, STATUS_FILTERS,
    breakdown_calls_error, contract_status, event_text, newest_end_first, period_error, status_bounds,
    validate_contract, validate_line,
)
from db_helpers import count, get_db, insert_row, marks, row_to_dict, transaction, update_row
from equipment import IST, NODE_JOINS, accessible_unit_ids, node_path, write_events
from equipment_core import SCRAPPED
from masters import check_active_vendor

contracts_bp = Blueprint("contracts", __name__)

READ_BASIC = "contract:read_basic"
READ_CALLOUT = "contract:read"
READ_COST = "contract:read_senior"
EDIT = "contract:edit"

UNIQUE_KEY_ERRORS.update({
    "uq_contract_equipment": ("equipment_id", "This machine is already on the contract."),
})

# The machine lines' sums (S081 § 4.2): computed on every read, never stored.  price_total stays NULL while no
# line has a price.
_CONTRACT_SELECT = (
    "SELECT c.*, s.code AS site_code, v.name AS vendor_name, v.active AS vendor_active,"
    " COALESCE(ce.machine_count, 0) AS machine_count, COALESCE(ce.priced_count, 0) AS priced_count,"
    " ce.price_total FROM contracts c"
    " JOIN sites s ON s.id = c.site_id JOIN vendors v ON v.id = c.vendor_id"
    " LEFT JOIN (SELECT contract_id, COUNT(*) AS machine_count, COUNT(price) AS priced_count,"
    " SUM(price) AS price_total FROM contract_equipment GROUP BY contract_id) ce ON ce.contract_id = c.id"
)

INACTIVE_NO_ADD = "This contract is inactive. Set it active in Masters › Contracts, then add machines."
CHOOSE_MACHINE = "Choose a machine."
SCRAPPED_NO_ADD = "A scrapped machine cannot be added to a contract."
LINE_MISSING = "This machine is not on the contract."


def _today():
    return datetime.now(IST).date()


class _SiteFlags:
    """has_perm_at per site, computed once per site in the request (§ 6.2)."""

    def __init__(self):
        self._flags = {}

    def at(self, site_id):
        if site_id not in self._flags:
            self._flags[site_id] = {
                "can_edit": has_perm_at(EDIT, site_id),
                "can_read_callout": has_perm_at(READ_CALLOUT, site_id),
                "can_read_cost": has_perm_at(READ_COST, site_id),
            }
        return self._flags[site_id]


def _sites_holding(cur, key):
    """The sites where the user holds ``key`` (plain read), ordered by code, as _SiteViewer.grantable_site_ids
    decides per site."""
    cur.execute("SELECT id, code, name, active FROM sites ORDER BY code")
    return [row for row in cur.fetchall() if has_perm_at(key, row["id"])]


def _contract_out(row, flags, today):
    """The one answer builder (§ 5.4, § 6.1): a gated field is left out for a reader without its key, and
    renewal_of_id is not sent (R02.4)."""
    item = row_to_dict(row)
    del item["renewal_of_id"]
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
    " e.code, e.name, e.level, e.lifecycle, u.id AS root_unit_id, s.id AS site_id, s.code AS site_code,"
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
            "at_contract_site": row["site_id"] == contract["site_id"],
            "can_open": unit_ids is None or row["root_unit_id"] in unit_ids,
            **row_to_dict({key: row[key] for key in _LINE_STAMPS}),
        }
        if not flags["can_read_cost"]:
            del line["price"]
        lines.append(line)
    return lines


def _overlaps(cur, contract, lines, site_ids):
    """``{equipment_id: [overlap, …]}`` for the lines of an active contract (§ 5.6), the other contract only at a
    site in ``site_ids`` (where the reader holds read_basic).  on_code is None when the other line is on the same
    node.  An inactive contract shows none, and an inactive other contract counts in none."""
    if not contract["active"] or not lines or not site_ids:
        return {}
    cur.execute(f"{_OVERLAP_SELECT} AND c2.site_id IN ({marks(site_ids)}) ORDER BY c2.from_date, c2.id, o.code",
                [contract["id"], contract["contract_type"], contract["to_date"], contract["from_date"], *site_ids])
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
    overlaps = _overlaps(cur, row, lines, [s["id"] for s in _sites_holding(cur, READ_BASIC)])
    for line in lines:
        line["overlaps"] = overlaps.get(line["equipment_id"], [])
    item["machines"] = lines
    return item


def _answer(cur, contract_id):
    """The answer of a write, read inside its transaction: the detail."""
    row = _contract_row(cur, contract_id)
    return _detail(cur, row, _SiteFlags().at(row["site_id"]), _today())


def _drop_gated(clean, site_id, fields=GATED_FIELDS):
    """A gated field the writer may not read is ignored (§ 5.4): their save leaves the stored value as it was.
    ``fields`` maps each gated field to its key: the contract's (GATED_FIELDS) or a line's (LINE_GATED_FIELDS)."""
    for field, key in fields.items():
        if field in clean and not has_perm_at(key, site_id):
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
    """The contracts of the sites where contract:read_basic is held, filtered (§ 5.3, § 6.2)."""
    site_id, vendor_id, contract_type, status, include_inactive = _list_filters()
    today = _today()
    flags = _SiteFlags()
    with get_db().cursor() as cur:
        sites = _sites_holding(cur, READ_BASIC)
        site_ids = [s["id"] for s in sites]
        if site_id is not None:
            site_ids = [s for s in site_ids if s == site_id]   # a site not held: an empty list, not a 403
        items, total = [], 0
        if site_ids:
            where, params = [f"c.site_id IN ({marks(site_ids)})"], list(site_ids)
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
            condition = " AND ".join(where)
            total = count(cur, f"SELECT COUNT(*) AS n FROM contracts c WHERE {condition}", params)
            direction = "DESC" if newest_end_first(status) else "ASC"
            cur.execute(f"{_CONTRACT_SELECT} WHERE {condition} ORDER BY c.to_date {direction}, c.id {direction}"
                        " LIMIT %s", [*params, MAX_PER_PAGE])
            items = [_contract_out(row, flags.at(row["site_id"]), today) for row in cur.fetchall()]
    return jsonify({
        "items": items,
        "total": total,
        "sites": [{**row_to_dict(s), "can_add": bool(s["active"]) and flags.at(s["id"])["can_edit"],
                   "can_read_callout": flags.at(s["id"])["can_read_callout"],
                   "can_read_cost": flags.at(s["id"])["can_read_cost"]} for s in sites],
    })


@contracts_bp.route("/<int:contract_id>")
@require_perm(READ_BASIC)
def get_contract(contract_id):
    with get_db().cursor() as cur:
        row = _contract_row(cur, contract_id)
        if row is None or not has_perm_at(READ_BASIC, row["site_id"]):
            raise ApiError("Not found", 404)   # existence is not shown outside the reader's sites
        return jsonify(_detail(cur, row, _SiteFlags().at(row["site_id"]), _today()))


@contracts_bp.route("/", methods=["POST"], strict_slashes=False)
@require_perm(EDIT)
def create_contract():
    """A contract at a site where the user holds contract:edit (§ 5.6 Create)."""
    clean = clean_body(validate_contract, creating=True)
    site_id = clean["site_id"]
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        cur.execute("SELECT id, active FROM sites WHERE id = %s LOCK IN SHARE MODE", (site_id,))
        site = cur.fetchone()
        if site is None:
            raise ApiError("Choose a site.", 400, "site_id")
        if not site["active"]:
            raise ApiError(SITE_INACTIVE, 400, "site_id")
        require_perm_at(EDIT, site_id, "site_id")
        _drop_gated(clean, site_id)
        _check_rules(clean, {})
        check_active_vendor(cur, clean["vendor_id"])
        contract_id = insert_row(cur, "contracts", clean, actor())
        answer = _answer(cur, contract_id)
    return jsonify(answer), 201


@contracts_bp.route("/<int:contract_id>", methods=["PUT"])
@require_perm(EDIT)
def change_contract(contract_id):
    """Any subset of the fields (§ 5.6 Change).  Every field sent is written; the site is fixed, the vendor may
    change to an active one."""
    clean = clean_body(validate_contract, creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        cur.execute("SELECT * FROM contracts WHERE id = %s FOR UPDATE", (contract_id,))
        locked = cur.fetchone()
        if locked is None or not has_perm_at(READ_BASIC, locked["site_id"]):
            raise ApiError("Not found", 404)
        require_perm_at(EDIT, locked["site_id"])
        if "site_id" in clean:
            if clean.pop("site_id") != locked["site_id"]:
                raise ApiError(SITE_KEPT, 400, "site_id")
        _drop_gated(clean, locked["site_id"])
        _check_rules(clean, locked)
        if clean.get("vendor_id", locked["vendor_id"]) != locked["vendor_id"]:
            check_active_vendor(cur, clean["vendor_id"])
        update_row(cur, "contracts", contract_id, clean, actor())
        answer = _answer(cur, contract_id)
    return jsonify(answer)


# ---------------------------------------------------------------------------
# The machines a contract covers (S081 § 5, § 6; LOCK ORDER above)
# ---------------------------------------------------------------------------

def _lock_contract(cur, contract_id):
    """Every line write's first statement: the contract FOR UPDATE, then read_basic at its site (404) and
    contract:edit there (403) -> the locked row."""
    cur.execute("SELECT * FROM contracts WHERE id = %s FOR UPDATE", (contract_id,))
    locked = cur.fetchone()
    if locked is None or not has_perm_at(READ_BASIC, locked["site_id"]):
        raise ApiError("Not found", 404)
    require_perm_at(EDIT, locked["site_id"])
    return locked


def _lock_line(cur, contract_id, equipment_id):
    """The line FOR UPDATE, after its contract -> its id; 404 when the machine is not on the contract."""
    cur.execute("SELECT id FROM contract_equipment WHERE contract_id = %s AND equipment_id = %s FOR UPDATE",
                (contract_id, equipment_id))
    line = cur.fetchone()
    if line is None:
        raise ApiError(LINE_MISSING, 404)
    return line["id"]


def _check_node(cur, equipment_id, contract):
    """The node an add names (§ 5.2 rules 2-4): its shared lock (1), then plain reads for its units and site."""
    cur.execute("SELECT id, lifecycle FROM equipment WHERE id = %s LOCK IN SHARE MODE", (equipment_id,))   # (1)
    locked = cur.fetchone()
    if locked is None:
        raise ApiError(CHOOSE_MACHINE, 400, "equipment_id")
    cur.execute(f"SELECT u.id AS root_unit_id, s.id AS site_id FROM equipment e{NODE_JOINS} WHERE e.id = %s",
                (equipment_id,))
    node = cur.fetchone()
    unit_ids = accessible_unit_ids(cur)
    if node is None or (unit_ids is not None and node["root_unit_id"] not in unit_ids):
        raise ApiError(CHOOSE_MACHINE, 400, "equipment_id")
    if locked["lifecycle"] == SCRAPPED:
        raise ApiError(SCRAPPED_NO_ADD, 409, "equipment_id")
    if node["site_id"] != contract["site_id"]:
        cur.execute("SELECT code FROM sites WHERE id = %s", (contract["site_id"],))
        code = cur.fetchone()["code"]
        raise ApiError(f"Choose a machine of {code}, the contract's site.", 400, "equipment_id")


@contracts_bp.route("/<int:contract_id>/equipment", methods=["POST"])
@require_perm(EDIT)
def add_machine(contract_id):
    """A node of the contract's site, any level (§ 5.2).  The price is kept only for a contract:read_senior holder
    at the site (§ 5.4)."""
    clean = clean_body(validate_line, creating=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        locked = _lock_contract(cur, contract_id)
        if not locked["active"]:
            raise ApiError(INACTIVE_NO_ADD, 409)
        _drop_gated(clean, locked["site_id"], LINE_GATED_FIELDS)
        _check_node(cur, clean["equipment_id"], locked)
        insert_row(cur, "contract_equipment", {"contract_id": contract_id, **clean}, actor())
        write_events(cur, clean["equipment_id"], [("contract_added", None, event_text(locked))])
        answer = _answer(cur, contract_id)
    return jsonify(answer), 201


@contracts_bp.route("/<int:contract_id>/equipment/<int:equipment_id>", methods=["PUT"])
@require_perm(EDIT)
def change_price(contract_id, equipment_id):
    """A line's price (§ 5.4): only with contract:edit and contract:read_senior at the site, else 403 (B3).  No
    history line: it would carry the price; the line's updated_at and updated_by record the change.  Allowed on an
    inactive contract (BR1-03)."""
    clean = clean_body(validate_line, creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        locked = _lock_contract(cur, contract_id)
        require_perm_at(READ_COST, locked["site_id"])
        _drop_gated(clean, locked["site_id"], LINE_GATED_FIELDS)
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
