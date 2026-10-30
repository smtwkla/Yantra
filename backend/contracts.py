"""Vendor contracts — the API (docs/steps/S080-contract-register/1-brief.md; R02.1).  One record per vendor
contract at one site: its vendor (the vendors master, S079), type, period, what is covered, the PM visits agreed,
the response time, the call-out number, the *Only the vendor may repair* tick and a cost note.  The status comes
from the dates (contracts_core.contract_status), never stored.  Never deleted: one entered by mistake is set
inactive (ISO 9001 § 7.5).  The machines covered and their prices are R02.2's.

Thin shell: contracts_core holds the rules; this module checks access, locks, reads and stores.

ACCESS (§ 5.4, § 5.5).  Four site-scoped keys, checked at the contract's site (has_perm_at).  A contract belongs
to a site, not a unit, so unit rows play no part (D8).  contract:read_basic reads the terms; contract:read adds
callout_number, contract:read_senior adds cost_note; contract:edit adds and changes.  Every answer goes through
_contract_out, which leaves a gated field out (absent, not null) for a reader without its key, and every write
drops a gated field the writer may not read (_drop_gated), so their save leaves it as it was (ISO 27001 A.5.15).

LOCK ORDER (§ 5.6).  The database runs REPEATABLE READ; each write decides from its locking reads, and access
checks are plain reads.  Per write this module takes at most one exclusive row lock, the contract's own, then only
shared locks.
- Create: the site LOCK IN SHARE MODE (missing or inactive 400) → contract:edit at the site (plain, 403) → the
  vendor LOCK IN SHARE MODE (masters.check_active_vendor: missing or inactive 400) → the insert (its shared
  foreign-key locks on the site and the vendor, already held) → the answer, read in the transaction.
- Change: the contracts row FOR UPDATE, first (404) → plain access checks (404, 403) and the rules on the merged
  values → the vendor LOCK IN SHARE MODE only when vendor_id changes → update_row (a new vendor's shared
  foreign-key lock, already held) → the answer.
- Reads: plain, no lock.
No deadlock cycle:
- The contract row: only this module's PUT locks it, first in its transaction; no other module touches contracts.
- The vendor row: masters.py's vendor update locks only its own row and waits on nothing after it; a person write
  takes the person, then the vendor shared.  Neither waits on a contract or site lock a contract write holds, so a
  contract write waiting on the vendor waits behind a writer that finishes.
- The site row: masters.py's site update locks site rows (_clear_default_site a second one), never a vendor or a
  contract row; it may wait for a create's shared lock, never the reverse.  People writes take the site through
  the membership foreign key, shared, which is compatible.
- Two contract writes: creates share the site and vendor locks; two PUTs on one contract serialise on its row.
"""

from datetime import datetime

from flask import Blueprint, jsonify, request

from api_common import MAX_PER_PAGE, ApiError, actor, clean_body, enum_arg, int_arg
from auth_utils import has_perm_at, require_perm, require_perm_at
from contracts_core import (
    CONTRACT_TYPES, DEFAULT_STATUS, GATED_FIELDS, SITE_INACTIVE, SITE_KEPT, STATUS_FILTERS, breakdown_calls_error,
    contract_status, newest_end_first, period_error, status_bounds, validate_contract,
)
from db_helpers import count, get_db, insert_row, marks, row_to_dict, transaction, update_row
from equipment import IST
from masters import check_active_vendor

contracts_bp = Blueprint("contracts", __name__)

READ_BASIC = "contract:read_basic"
READ_CALLOUT = "contract:read"
READ_COST = "contract:read_senior"
EDIT = "contract:edit"

_CONTRACT_SELECT = (
    "SELECT c.*, s.code AS site_code, v.name AS vendor_name, v.active AS vendor_active FROM contracts c"
    " JOIN sites s ON s.id = c.site_id JOIN vendors v ON v.id = c.vendor_id"
)


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
    return item


def _contract_row(cur, contract_id):
    cur.execute(f"{_CONTRACT_SELECT} WHERE c.id = %s", (contract_id,))
    return cur.fetchone()


def _answer(cur, contract_id):
    """The answer of a write, read inside its transaction."""
    row = _contract_row(cur, contract_id)
    return _contract_out(row, _SiteFlags().at(row["site_id"]), _today())


def _drop_gated(clean, site_id):
    """A gated field the writer may not read is ignored (§ 5.4): their save leaves the stored value as it was."""
    for field, key in GATED_FIELDS.items():
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
        return jsonify(_contract_out(row, _SiteFlags().at(row["site_id"]), _today()))


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
