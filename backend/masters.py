"""Masters module — sites, units, equipment classes and types, trades, the Team register of
people and their roles per site (docs/steps/S001-basic-masters/1-brief.md; equipment types:
S004; trades and Team: S010 A1; site roles: S011 A1).

Thin shell: masters_core validates input, this module fetches, checks the
rules that need the database, and stores.  Pooled connections are autocommit,
so anything that checks and then writes runs in transaction() with the parent
row locked first.

Equipment types lock class → type, the order equipment.py uses (class (4), type (5)).
People lock person → trades → the person's memberships and person_units rows → units; the
membership insert then takes its site row through the FK (unit → site, as update_unit).
"""

import logging

from flask import Blueprint, jsonify, request

from api_common import UNIQUE_KEY_ERRORS, ApiError, actor, clean_body
from auth_utils import has_perm, has_perm_at, require_perm, require_perm_at
from db_helpers import count, fetch_one, get_db, insert_row, rows_to_list, transaction, update_row
from masters_core import (
    no_login_role_error, normalise_username, technician_only, validate_equipment_class, validate_equipment_type,
    validate_person, validate_site, validate_site_row, validate_site_rows, validate_trade, validate_unit,
)

logger = logging.getLogger(__name__)

masters_bp = Blueprint("masters", __name__)

# Named UNIQUE indexes (migration v2) -> the field to flag and a plain message
UNIQUE_KEY_ERRORS.update({
    "uq_sites_code": ("code", "A site with this code already exists"),
    "uq_units_site_code": ("code", "A unit with this code already exists at this site"),
    "uq_units_warehouse": ("oneerp_warehouse", "This OneERP warehouse is already mapped to another unit"),
    "uq_equipment_classes_code": ("code", "An equipment class with this code already exists"),
    "uq_sites_default": ("is_default", "Another site was made the default at the same time; reload and try again"),
    # Migration v5 (S004)
    "uq_equipment_types_class_name": ("name", "A type with this name already exists in this class"),
    # Migration v7 (S010, amendment A1)
    "uq_trades_name": ("name", "A trade with this name exists"),
    "uq_people_username": ("username", "Another person already has this login (it may be an inactive one)"),
})

# is_default is 1 / NULL in the table; the API shows it as a boolean (see _site_out)
_SITE_SELECT = (
    "SELECT id, code, name, address, active, (is_default IS NOT NULL) AS is_default, "
    "created_at, created_by, updated_at, updated_by FROM sites"
)

_UNIT_SELECT = (
    "SELECT u.*, s.code AS site_code, CONCAT(s.code, '.', u.code) AS full_code "
    "FROM units u JOIN sites s ON s.id = u.site_id"
)

_TYPE_SELECT = (
    "SELECT t.*, c.code AS class_code FROM equipment_types t JOIN equipment_classes c ON c.id = t.class_id"
)

_PERSON_UNITS_SELECT = (
    "SELECT pu.person_id, u.id, u.site_id, s.code AS site_code, s.active AS site_active,"
    " CONCAT(s.code, '.', u.code) AS full_code, u.name, u.active "
    "FROM person_units pu JOIN units u ON u.id = pu.unit_id JOIN sites s ON s.id = u.site_id"
)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _include_inactive():
    return request.args.get("include_inactive") == "1"


def _lock_row(cur, table, record_id):
    """SELECT … FOR UPDATE the record.  A concurrent insert of a child row needs the
    parent's lock through the foreign key, so it waits until we commit."""
    cur.execute(f"SELECT * FROM {table} WHERE id = %s FOR UPDATE", (record_id,))
    row = cur.fetchone()
    if row is None:
        raise ApiError("Not found", 404)
    return row


def _int_filter(name):
    """An optional ?name=<id> list filter; anything but digits is a 400."""
    raw = request.args.get(name)
    if raw is None:
        return None
    # isascii: str.isdigit() also accepts digits such as '²' that int() rejects
    if not (raw.isascii() and raw.isdigit()):
        raise ApiError(f"{name} must be a number", 400, name)
    return int(raw)


def _site_out(row):
    row["is_default"] = bool(row["is_default"])
    return row


def _list_response(cur, sql, params=(), convert=lambda row: row):
    cur.execute(sql, params)
    items = [convert(row) for row in rows_to_list(cur.fetchall())]
    return jsonify({"items": items, "total": len(items)})


def _fetch_site(cur, site_id):
    return _site_out(fetch_one(cur, f"{_SITE_SELECT} WHERE id = %s", (site_id,)))


def _clear_default_site(cur, except_id=None):
    """Make no site the default (except_id is the one about to become it)."""
    cur.execute(
        "UPDATE sites SET is_default = NULL, updated_at = NOW(), updated_by = %s "
        "WHERE is_default = 1 AND id <> %s", (actor(), except_id or 0))


def _lock_site_for_unit(cur, site_id):
    """Lock the site a unit sits under: it must exist (400) and be active (409)."""
    cur.execute("SELECT * FROM sites WHERE id = %s FOR UPDATE", (site_id,))
    site = cur.fetchone()
    if site is None:
        raise ApiError("Unknown site", 400, "site_id")
    if not site["active"]:
        raise ApiError("The site is inactive; reactivate it first", 409, "site_id")


# ---------------------------------------------------------------------------
# Sites
# ---------------------------------------------------------------------------

@masters_bp.route("/sites")
@require_perm("masters:read")
def list_sites():
    where = "" if _include_inactive() else " WHERE active = 1"
    with get_db().cursor() as cur:
        return _list_response(cur, f"{_SITE_SELECT}{where} ORDER BY code", convert=_site_out)


def _as_column_value(clean):
    """is_default is stored as 1 or NULL, never 0 (see migration v3)."""
    if "is_default" in clean:
        clean["is_default"] = 1 if clean["is_default"] else None


@masters_bp.route("/sites", methods=["POST"])
@require_perm("masters:edit")
def create_site():
    clean = clean_body(validate_site, creating=True)
    making_default = bool(clean.get("is_default"))
    if making_default and clean.get("active") == 0:
        raise ApiError("An inactive site cannot be the default", 409, "is_default")
    _as_column_value(clean)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        if making_default:
            _clear_default_site(cur)
        site_id = insert_row(cur, "sites", clean, actor())
    with conn.cursor() as cur:
        return jsonify(_fetch_site(cur, site_id)), 201


@masters_bp.route("/sites/<int:site_id>", methods=["PUT"])
@require_perm("masters:edit")
def update_site(site_id):
    clean = clean_body(validate_site, creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        site = _lock_row(cur, "sites", site_id)
        if clean.get("code", site["code"]) != site["code"]:
            if count(cur, "SELECT COUNT(*) AS n FROM units WHERE site_id = %s", (site_id,)):
                raise ApiError("Code is in use and cannot be changed", 409, "code")
        will_be_default = bool(clean["is_default"]) if "is_default" in clean else bool(site["is_default"])
        will_be_active = bool(clean["active"]) if "active" in clean else bool(site["active"])
        if clean.get("active") == 0:
            if site["is_default"]:
                raise ApiError("This is the default site; untick Default first", 409, "active")
            if count(cur, "SELECT COUNT(*) AS n FROM units WHERE site_id = %s AND active = 1", (site_id,)):
                raise ApiError("The site has active units; deactivate them first", 409, "active")
        if will_be_default and not will_be_active:
            raise ApiError("An inactive site cannot be the default", 409, "is_default")
        if will_be_default and not site["is_default"]:
            _clear_default_site(cur, except_id=site_id)
        _as_column_value(clean)
        update_row(cur, "sites", site_id, clean, actor())
    with conn.cursor() as cur:
        return jsonify(_fetch_site(cur, site_id))


# ---------------------------------------------------------------------------
# Units
# ---------------------------------------------------------------------------

@masters_bp.route("/units")
@require_perm("masters:read")
def list_units():
    conditions, params = [], []
    if not _include_inactive():
        conditions.append("u.active = 1")
    site_id = _int_filter("site_id")
    if site_id is not None:
        conditions.append("u.site_id = %s")
        params.append(site_id)
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    with get_db().cursor() as cur:
        return _list_response(cur, f"{_UNIT_SELECT}{where} ORDER BY s.code, u.code", params)


def _unit_is_referenced(cur, unit_id):
    """Access rows or any equipment — scrapped included, it still carries the unit in its
    history — freeze the unit's code and site.  Only equipment rows hold a unit_id; parts
    follow their equipment."""
    return (count(cur, "SELECT COUNT(*) AS n FROM person_units WHERE unit_id = %s", (unit_id,))
            or count(cur, "SELECT COUNT(*) AS n FROM equipment WHERE unit_id = %s", (unit_id,)))


@masters_bp.route("/units", methods=["POST"])
@require_perm("masters:edit")
def create_unit():
    clean = clean_body(validate_unit, creating=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        _lock_site_for_unit(cur, clean["site_id"])
        unit_id = insert_row(cur, "units", clean, actor())
    with conn.cursor() as cur:
        return jsonify(fetch_one(cur, f"{_UNIT_SELECT} WHERE u.id = %s", (unit_id,))), 201


@masters_bp.route("/units/<int:unit_id>", methods=["PUT"])
@require_perm("masters:edit")
def update_unit(unit_id):
    clean = clean_body(validate_unit, creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        unit = _lock_row(cur, "units", unit_id)
        code_changes = clean.get("code", unit["code"]) != unit["code"]
        site_changes = clean.get("site_id", unit["site_id"]) != unit["site_id"]
        if code_changes or site_changes:
            if _unit_is_referenced(cur, unit_id):
                if code_changes:
                    raise ApiError("Code is in use and cannot be changed", 409, "code")
                raise ApiError("Unit is in use and cannot be moved to another site", 409, "site_id")
        # Laid-up (out_of_use) equipment still stands in the unit, so it blocks too (S002 § 10.2)
        if clean.get("active") == 0 and count(
                cur, "SELECT COUNT(*) AS n FROM equipment WHERE unit_id = %s AND status <> 'scrapped'",
                (unit_id,)):
            raise ApiError("The unit holds equipment that is not scrapped; move or scrap it first",
                           409, "active")
        if site_changes or clean.get("active") == 1:
            _lock_site_for_unit(cur, clean.get("site_id", unit["site_id"]))
        update_row(cur, "units", unit_id, clean, actor())
    with conn.cursor() as cur:
        return jsonify(fetch_one(cur, f"{_UNIT_SELECT} WHERE u.id = %s", (unit_id,)))


# ---------------------------------------------------------------------------
# Equipment classes
# ---------------------------------------------------------------------------

@masters_bp.route("/equipment-classes")
@require_perm("masters:read")
def list_equipment_classes():
    where = "" if _include_inactive() else "WHERE active = 1 "
    with get_db().cursor() as cur:
        return _list_response(cur, f"SELECT * FROM equipment_classes {where}ORDER BY code")


@masters_bp.route("/equipment-classes", methods=["POST"])
@require_perm("equipment:edit")
def create_equipment_class():
    clean = clean_body(validate_equipment_class, creating=True)
    with get_db().cursor() as cur:
        class_id = insert_row(cur, "equipment_classes", clean, actor())
        return jsonify(fetch_one(cur, "SELECT * FROM equipment_classes WHERE id = %s", (class_id,))), 201


@masters_bp.route("/equipment-classes/<int:class_id>", methods=["PUT"])
@require_perm("equipment:edit")
def update_equipment_class(class_id):
    clean = clean_body(validate_equipment_class, creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        record = _lock_row(cur, "equipment_classes", class_id)
        # Every equipment code is built from the class prefix, scrapped equipment included
        if clean.get("code", record["code"]) != record["code"] and count(
                cur, "SELECT COUNT(*) AS n FROM equipment WHERE class_id = %s", (class_id,)):
            raise ApiError("Code is in use and cannot be changed", 409, "code")
        update_row(cur, "equipment_classes", class_id, clean, actor())
    with conn.cursor() as cur:
        return jsonify(fetch_one(cur, "SELECT * FROM equipment_classes WHERE id = %s", (class_id,)))


# ---------------------------------------------------------------------------
# Equipment types — per class (ISO 14224); the class is fixed after create
# ---------------------------------------------------------------------------

def _lock_class_for_type(cur, class_id, field):
    """Lock the class a type is created or reactivated under: it must exist (400) and be
    active (409).  ``field`` is class_id on create, active on reactivation."""
    cur.execute("SELECT id, active FROM equipment_classes WHERE id = %s FOR UPDATE", (class_id,))
    equipment_class = cur.fetchone()
    if equipment_class is None:
        raise ApiError("Unknown class", 400, field)
    if not equipment_class["active"]:
        raise ApiError("The class is inactive", 409, field)


def _fetch_type(cur, type_id):
    return fetch_one(cur, f"{_TYPE_SELECT} WHERE t.id = %s", (type_id,))


@masters_bp.route("/equipment-types")
@require_perm("masters:read")
def list_equipment_types():
    conditions, params = [], []
    if not _include_inactive():
        conditions.append("t.active = 1")
    class_id = _int_filter("class_id")
    if class_id is not None:
        conditions.append("t.class_id = %s")
        params.append(class_id)
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    with get_db().cursor() as cur:
        return _list_response(cur, f"{_TYPE_SELECT}{where} ORDER BY c.code, t.name", params)


@masters_bp.route("/equipment-types", methods=["POST"])
@require_perm("equipment:edit")
def create_equipment_type():
    clean = clean_body(validate_equipment_type, creating=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        _lock_class_for_type(cur, clean["class_id"], "class_id")
        type_id = insert_row(cur, "equipment_types", clean, actor())
    with conn.cursor() as cur:
        return jsonify(_fetch_type(cur, type_id)), 201


@masters_bp.route("/equipment-types/<int:type_id>", methods=["PUT"])
@require_perm("equipment:edit")
def update_equipment_type(type_id):
    """Rename, deactivate or reactivate.  Deactivating needs no "in use" check: equipment
    keeps the type, it just can't be newly chosen."""
    clean = clean_body(validate_equipment_type, creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        # A plain read of the class is safe (a type's class never changes) and lets the
        # reactivation lock the class before the type: the class → type order
        stored = fetch_one(cur, "SELECT class_id FROM equipment_types WHERE id = %s", (type_id,))
        if stored is None:
            raise ApiError("Not found", 404)
        if clean.get("active") == 1:
            _lock_class_for_type(cur, stored["class_id"], "active")
        record = _lock_row(cur, "equipment_types", type_id)
        if "class_id" in clean:
            if clean["class_id"] != record["class_id"]:
                raise ApiError("Class cannot be changed", 400, "class_id")
            del clean["class_id"]
        update_row(cur, "equipment_types", type_id, clean, actor())
    with conn.cursor() as cur:
        return jsonify(_fetch_type(cur, type_id))


# ---------------------------------------------------------------------------
# Grants of a set of rows (trades of a person, units of a site row)
# ---------------------------------------------------------------------------

def _check_grantable(cur, table, ids, held, field, label):
    """Every id must be a row of ``table`` (locked); an inactive one may be kept but not newly
    granted.  ``table`` is a code constant, never client input.  Returns the locked rows by id."""
    if not ids:
        return {}
    placeholders = ", ".join(["%s"] * len(ids))
    cur.execute(f"SELECT * FROM {table} WHERE id IN ({placeholders}) FOR UPDATE", ids)
    rows_by_id = {r["id"]: r for r in cur.fetchall()}
    for record_id in ids:
        if record_id not in rows_by_id:
            raise ApiError(f"Unknown {label} {record_id}", 400, field)
        if not rows_by_id[record_id]["active"] and record_id not in held:
            raise ApiError(f"{label.capitalize()} {record_id} is inactive and cannot be newly granted", 400, field)
    return rows_by_id


# ---------------------------------------------------------------------------
# Trades (S010) — kinds of maintenance work (ISO 14224 maintenance resources: "discipline")
# ---------------------------------------------------------------------------

@masters_bp.route("/trades")
@require_perm("masters:read")
def list_trades():
    where = "" if _include_inactive() else "WHERE active = 1 "
    with get_db().cursor() as cur:
        return _list_response(cur, f"SELECT * FROM trades {where}ORDER BY name")


@masters_bp.route("/trades", methods=["POST"])
@require_perm("people:edit")
def create_trade():
    clean = clean_body(validate_trade, creating=True)
    with get_db().cursor() as cur:
        trade_id = insert_row(cur, "trades", clean, actor())
        return jsonify(fetch_one(cur, "SELECT * FROM trades WHERE id = %s", (trade_id,))), 201


@masters_bp.route("/trades/<int:trade_id>", methods=["PUT"])
@require_perm("people:edit")
def update_trade(trade_id):
    clean = clean_body(validate_trade, creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        _lock_row(cur, "trades", trade_id)
        update_row(cur, "trades", trade_id, clean, actor())
    with conn.cursor() as cur:
        return jsonify(fetch_one(cur, "SELECT * FROM trades WHERE id = %s", (trade_id,)))


# ---------------------------------------------------------------------------
# Team (S010 A1) — a register of people (or contractor firms), with their trades and an
# optional Yantra login.  people:edit maintains the register; the login, and the active
# flag of a person who has one, are IT admin's (masters:edit): a login turns the
# person's site roles into access (ISO 27001 A.5.3, A.8.2).
# Lock order person -> trades -> site rows -> units; only the trade PUT locks a trade row alone.
# ---------------------------------------------------------------------------

def _attach_trades(cur, items):
    """Add ``trades`` ([{id, name, active}] by name, inactive included) to each item, in one query."""
    for item in items:
        item["trades"] = []
    if not items:
        return items
    by_id = {item["id"]: item for item in items}
    placeholders = ", ".join(["%s"] * len(by_id))
    cur.execute(
        "SELECT pt.person_id, t.id, t.name, t.active FROM person_trades pt "
        f"JOIN trades t ON t.id = pt.trade_id WHERE pt.person_id IN ({placeholders}) ORDER BY t.name",
        list(by_id))
    for row in cur.fetchall():
        by_id[row["person_id"]]["trades"].append(
            {"id": row["id"], "name": row["name"], "active": bool(row["active"])})
    return items


def _is_own(person):
    """The person whose stored login is the actor's own (S011 A1 rule 4), case-insensitively."""
    return person["username"] is not None and person["username"] == normalise_username(actor())


class _SiteViewer:
    """What the acting user may see and change of people's site rows (S011 A1 rule 5, gate
    A).  IT admin (masters:read_senior / masters:edit) sees and changes every row; an
    engineer (people:edit) sees every row of a person without a login and, of a person with
    one, the rows at the sites where they hold people:assign_technicians, and may change a
    Technician row (or add one) only there.  Nobody changes their own person's rows."""

    def __init__(self, cur):
        self.senior = has_perm("masters:read_senior")
        self.editor = has_perm("people:edit")
        self.it_admin = has_perm("masters:edit")
        self._assigns_at = {}
        self._active_site_ids = None
        self._cur = cur

    def assigns_at(self, site_id):
        if site_id not in self._assigns_at:
            self._assigns_at[site_id] = has_perm_at("people:assign_technicians", site_id)
        return self._assigns_at[site_id]

    def sees(self, person, row):
        if self.senior or (self.editor and person["username"] is None):
            return True
        return self.editor and self.assigns_at(row["site_id"])

    def editable(self, person, row):
        if _is_own(person):
            return False
        return self.it_admin or (self.assigns_at(row["site_id"]) and technician_only(row["role"], None))

    def assignable_site_ids(self, person, present_site_ids):
        """Active sites where this viewer may add a row for the person (a Technician row, for
        an engineer; any role, for IT admin)."""
        if _is_own(person):
            return []
        if self._active_site_ids is None:
            self._cur.execute("SELECT id FROM sites WHERE active = 1 ORDER BY code")
            self._active_site_ids = [r["id"] for r in self._cur.fetchall()]
        return [site_id for site_id in self._active_site_ids
                if site_id not in present_site_ids and (self.it_admin or self.assigns_at(site_id))]


def _unit_summary(row):
    return {"id": row["id"], "full_code": row["full_code"], "name": row["name"], "active": row["active"]}


def _site_rows(cur, person_ids):
    """person_id -> {site_id: {site_id, site_code, active, role, all_units, units}}, by plain
    reads.  Unit rows at a site without a membership (moved from user_units by migration v8)
    make a row with role None, so they are visible and the first save replaces them."""
    rows = {person_id: {} for person_id in person_ids}
    if not person_ids:
        return rows
    placeholders = ", ".join(["%s"] * len(person_ids))
    cur.execute("SELECT m.person_id, m.site_id, s.code AS site_code, s.active, m.role, m.all_units "
                f"FROM memberships m JOIN sites s ON s.id = m.site_id WHERE m.person_id IN ({placeholders})",
                list(person_ids))
    for r in cur.fetchall():
        rows[r["person_id"]][r["site_id"]] = {
            "site_id": r["site_id"], "site_code": r["site_code"], "active": bool(r["active"]),
            "role": r["role"], "all_units": bool(r["all_units"]), "units": []}
    cur.execute(f"{_PERSON_UNITS_SELECT} WHERE pu.person_id IN ({placeholders}) ORDER BY full_code",
                list(person_ids))
    for r in cur.fetchall():
        row = rows[r["person_id"]].setdefault(r["site_id"], {
            "site_id": r["site_id"], "site_code": r["site_code"], "active": bool(r["site_active"]),
            "role": None, "all_units": False, "units": []})
        row["units"].append(_unit_summary(r))
    return rows


def _people_out(cur, rows):
    """Rows with their trades and, for those who may see them, their site rows.  Editors
    (people:edit) learn whether a person has a login; the login itself goes only to those who
    maintain it, IT admin (A.5.15, A.5.34).  Site rows: _SiteViewer."""
    items = _attach_trades(cur, rows_to_list(rows))
    viewer = _SiteViewer(cur)
    site_rows = _site_rows(cur, [item["id"] for item in items]) if viewer.editor else {}
    for item in items:
        if viewer.editor:
            person_rows = site_rows[item["id"]]
            visible = [row for row in person_rows.values() if viewer.sees(item, row)]
            item["sites"] = [{**row, "editable": viewer.editable(item, row)}
                             for row in sorted(visible, key=lambda r: r["site_code"])]
            item["assignable_site_ids"] = viewer.assignable_site_ids(item, set(person_rows))
            item["has_login"] = item["username"] is not None
        if not viewer.senior:
            del item["username"]
    return items


def _fetch_person(cur, person_id):
    cur.execute("SELECT * FROM people WHERE id = %s", (person_id,))
    return _people_out(cur, [cur.fetchone()])[0]


def _check_login_change(clean):
    """Setting, changing or clearing a login is IT admin's, and nobody sets their own:
    otherwise IT admin could give roles to a person, then take that person's login."""
    if "username" not in clean:
        return
    if not has_perm("masters:edit"):
        raise ApiError("Only IT admin can set the login", 403, "username")
    if clean["username"] is not None and clean["username"] == normalise_username(actor()):
        raise ApiError("You can't give yourself a login", 403, "username")


def _login_save_sites(clean, login_changes):
    """The ``sites`` of a login save (S011 A1 rule 1): a POST or PUT that sets, changes or
    clears the login must carry the person's whole set of sites, written in the same
    transaction, so what IT admin sees and sends is exactly what is granted.  ``sites`` goes
    only with ``username`` (IT admin's); an engineer saves site rows one by one.
    -> the validated rows, or None when not sent."""
    body = request.get_json(silent=True)   # a dict: clean_body has checked it
    if "sites" not in body:
        if login_changes:
            raise ApiError("A login change must carry the person's sites", 400, "sites")
        return None
    if "username" not in clean:
        raise ApiError("Sites are saved one site at a time, except with a login change", 400, "sites")
    rows, errors = validate_site_rows(body["sites"])
    if errors:
        raise ApiError(errors[0]["message"], 400, errors[0]["field"])
    return rows


@masters_bp.route("/people")
@require_perm("masters:read")
def list_people():
    where = "" if _include_inactive() else "WHERE active = 1 "
    with get_db().cursor() as cur:
        cur.execute(f"SELECT * FROM people {where}ORDER BY name, id")
        items = _people_out(cur, cur.fetchall())
    return jsonify({"items": items, "total": len(items)})


def _held_trade_ids(cur, person_id):
    cur.execute("SELECT trade_id FROM person_trades WHERE person_id = %s", (person_id,))
    return {r["trade_id"] for r in cur.fetchall()}


@masters_bp.route("/people", methods=["POST"])
@require_perm("people:edit")
def create_person():
    clean = clean_body(validate_person, creating=True)
    _check_login_change(clean)
    sites = _login_save_sites(clean, login_changes=clean.get("username") is not None)
    trade_ids = clean.pop("trade_ids", [])
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        _check_grantable(cur, "trades", trade_ids, set(), "trade_ids", "trade")
        person_id = insert_row(cur, "people", clean, actor())
        for trade_id in trade_ids:
            cur.execute("INSERT INTO person_trades (person_id, trade_id, granted_by) VALUES (%s, %s, %s)",
                        (person_id, trade_id, actor()))
        if sites is not None:
            _replace_site_rows(cur, person_id, clean.get("username"), sites)
    with conn.cursor() as cur:
        person = _fetch_person(cur, person_id)
    if sites is not None:
        _log_login_save(person_id, None, {}, clean.get("username"), person)
    return jsonify(person), 201


@masters_bp.route("/people/<int:person_id>", methods=["PUT"])
@require_perm("people:edit")
def update_person(person_id):
    """Absent fields stay as they are, so Deactivate (``{active}``) keeps the trades and login."""
    clean = clean_body(validate_person, creating=False)
    _check_login_change(clean)
    trade_ids = clean.pop("trade_ids", None)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        person = _lock_row(cur, "people", person_id)
        login_changes = "username" in clean and clean["username"] != person["username"]
        sites = _login_save_sites(clean, login_changes)
        # Nobody changes their own access: their login, active flag or sites (S011 A1 rule 4)
        if _is_own(person):
            for field, changes in (("username", login_changes), ("active", "active" in clean),
                                   ("sites", sites is not None)):
                if changes:
                    raise ApiError("You can't change your own access", 403, field)
        # Checked on the locked row: deactivating a person with a login revokes access, and
        # reactivating restores it, so it is IT admin's like the login itself (A1 rule 1)
        if "active" in clean and person["username"] is not None and not has_perm("masters:edit"):
            raise ApiError("Only IT admin can activate or deactivate a person with a login", 403, "active")
        trades_changed = False
        if trade_ids is not None:
            held = _held_trade_ids(cur, person_id)
            _check_grantable(cur, "trades", trade_ids, held, "trade_ids", "trade")
            # Diff rather than replace, so kept trades keep their original granted_at/by
            for trade_id in held - set(trade_ids):
                cur.execute("DELETE FROM person_trades WHERE person_id = %s AND trade_id = %s",
                            (person_id, trade_id))
            for trade_id in trade_ids:
                if trade_id not in held:
                    cur.execute("INSERT INTO person_trades (person_id, trade_id, granted_by) VALUES (%s, %s, %s)",
                                (person_id, trade_id, actor()))
            trades_changed = held != set(trade_ids)
        if sites is not None:
            before_rows = _site_rows(cur, [person_id])[person_id]   # for the log: what is replaced
            _replace_site_rows(cur, person_id, clean.get("username", person["username"]), sites)
        if clean:
            update_row(cur, "people", person_id, clean, actor())
        elif trades_changed:
            # update_row does nothing for an empty change, but "who/when on every change" holds
            cur.execute("UPDATE people SET updated_at = NOW(), updated_by = %s WHERE id = %s",
                        (actor(), person_id))
    with conn.cursor() as cur:
        out = _fetch_person(cur, person_id)
    if sites is not None:   # every replacement of the rows is logged, whether or not the login changed
        _log_login_save(person_id, person["username"], before_rows, clean.get("username", person["username"]), out)
    return jsonify(out)


# ---------------------------------------------------------------------------
# Site roles of a person (S011 A1): a role per site, with all the site's units or chosen
# ones.  For a person with an active login these rows are their Yantra access.  IT admin
# (masters:edit) sets any role; an engineer (people:assign_technicians at the site) adds,
# changes or removes Technician rows at that site only (gate A).  Refusals: 400 (body,
# unknown site, units, the no-login rule) before 403 (own person, the engineer's limits).
# ---------------------------------------------------------------------------

def _lock_site_rows(cur, person_id):
    """(2) Lock the person's membership and person_units rows -> site_id -> {role,
    all_units, unit_ids}.  Locking reads are single-table; each held unit's site comes from a
    plain read, safe because a unit with person_units rows cannot change site
    (_unit_is_referenced).  A site with unit rows only (legacy) has role None."""
    cur.execute("SELECT site_id, role, all_units FROM memberships WHERE person_id = %s FOR UPDATE", (person_id,))
    stored = {r["site_id"]: {"role": r["role"], "all_units": bool(r["all_units"]), "unit_ids": set()}
              for r in cur.fetchall()}
    cur.execute("SELECT unit_id FROM person_units WHERE person_id = %s FOR UPDATE", (person_id,))
    unit_ids = [r["unit_id"] for r in cur.fetchall()]
    if unit_ids:
        cur.execute(f"SELECT id, site_id FROM units WHERE id IN ({', '.join(['%s'] * len(unit_ids))})", unit_ids)
        for r in cur.fetchall():
            row = stored.setdefault(r["site_id"], {"role": None, "all_units": False, "unit_ids": set()})
            row["unit_ids"].add(r["id"])
    return stored


def _check_site_row(cur, site_id, clean, stored, field):
    """The 400s that need the database for one row: the site exists; an inactive site, or an
    inactive unit, may be kept on an existing row but not newly granted; every unit is the
    site's.  Locks the units (3)."""
    cur.execute("SELECT id, code, active FROM sites WHERE id = %s", (site_id,))
    site = cur.fetchone()
    if site is None:
        raise ApiError("Unknown site", 400, field)
    if not site["active"] and stored is None:
        raise ApiError(f"Site {site['code']} is inactive and cannot be newly granted", 400, field)
    held = stored["unit_ids"] if stored else set()
    for unit in _check_grantable(cur, "units", clean["unit_ids"], held, "unit_ids", "unit").values():
        if unit["site_id"] != site_id:
            raise ApiError(f"Unit {unit['code']} is not at site {site['code']}", 400, "unit_ids")


def _check_site_write(person, site_id, stored_role, new_role):
    """The 403s of a site-row write, on the locked person row: never one's own person; IT
    admin (masters:edit) any role; otherwise people:assign_technicians at that site, and a
    Technician row (or none) before and after."""
    if _is_own(person):
        raise ApiError("You can't change your own access", 403, "sites")
    if has_perm("masters:edit"):
        return
    require_perm_at("people:assign_technicians", site_id, "sites")
    if not technician_only(stored_role, new_role):
        raise ApiError("Only IT admin can set this role", 403, "role")


def _write_site_row(cur, person_id, site_id, clean, stored):
    """(after every check) Insert or update the membership and diff the units, so what stays
    keeps its granted_at/by.  All units clears the site's unit rows."""
    if stored is None or stored["role"] is None:
        cur.execute("INSERT INTO memberships (person_id, site_id, role, all_units, granted_by) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (person_id, site_id, clean["role"], int(clean["all_units"]), actor()))
    elif (stored["role"], stored["all_units"]) != (clean["role"], clean["all_units"]):
        cur.execute("UPDATE memberships SET role = %s, all_units = %s, updated_at = NOW(), updated_by = %s "
                    "WHERE person_id = %s AND site_id = %s",
                    (clean["role"], int(clean["all_units"]), actor(), person_id, site_id))
    held = stored["unit_ids"] if stored else set()
    wanted = set() if clean["all_units"] else set(clean["unit_ids"])
    for unit_id in held - wanted:
        cur.execute("DELETE FROM person_units WHERE person_id = %s AND unit_id = %s", (person_id, unit_id))
    for unit_id in clean["unit_ids"]:
        if unit_id not in held and unit_id in wanted:
            cur.execute("INSERT INTO person_units (person_id, unit_id, granted_by) VALUES (%s, %s, %s)",
                        (person_id, unit_id, actor()))


def _delete_site_row(cur, person_id, site_id, stored):
    cur.execute("DELETE FROM memberships WHERE person_id = %s AND site_id = %s", (person_id, site_id))
    for unit_id in stored["unit_ids"]:
        cur.execute("DELETE FROM person_units WHERE person_id = %s AND unit_id = %s", (person_id, unit_id))


def _replace_site_rows(cur, person_id, username, rows):
    """A login save's whole set (S011 A1 rule 1), after the person row is locked: every check
    of every row first, then the writes.  The caller has checked masters:edit (the login)."""
    stored = _lock_site_rows(cur, person_id)                                 # (2)
    if username is None:
        message = no_login_role_error([row["role"] for row in rows])
        if message:
            raise ApiError(message, 400, "role")
    for row in rows:
        _check_site_row(cur, row["site_id"], row, stored.get(row["site_id"]), "sites")   # (3)
    for site_id in set(stored) - {row["site_id"] for row in rows}:
        _delete_site_row(cur, person_id, site_id, stored[site_id])
    for row in rows:
        _write_site_row(cur, person_id, row["site_id"], row, stored.get(row["site_id"]))


def _describe(row):
    """A site row for the log: SITE:role:all or SITE:role:UNIT,UNIT ('-' for a legacy row)."""
    if row is None:
        return "-"
    units = "all" if row["all_units"] else ",".join(u["full_code"].split(".", 1)[1] for u in row["units"])
    return f"{row['site_code']}:{row['role'] or '-'}:{units}"


def _describe_rows(rows):
    return ";".join(_describe(rows[site_id]) for site_id in sorted(rows, key=lambda s: rows[s]["site_code"]))


def _log_login_save(person_id, old_login, old_rows, login, person_out):
    """One INFO line for a login save, with both sides (ISO 27001 A.8.15): actor, person,
    login before->after, and the site rows before (read in the transaction) and after."""
    with get_db().cursor() as cur:
        rows = _site_rows(cur, [person_id])[person_id]
    logger.info("login saved: actor=%s person=%s '%s' login=%s->%s before=[%s] after=[%s]",
                actor(), person_id, person_out["name"], old_login or "-", login or "-",
                _describe_rows(old_rows), _describe_rows(rows))


def _site_row_response(conn, person_id, before, after):
    """After the commit: log the change (actor, person, site, before, after) when there is
    one, and answer with the person, filtered like GET /people."""
    if _describe(before) != _describe(after):
        logger.info("site role changed: actor=%s person=%s site=%s before=[%s] after=[%s]",
                    actor(), person_id, (after or before)["site_code"], _describe(before), _describe(after))
    with conn.cursor() as cur:
        return jsonify(_fetch_person(cur, person_id))


@masters_bp.route("/people/<int:person_id>/sites/<int:site_id>", methods=["PUT"])
@require_perm("people:assign_technicians")
def put_person_site(person_id, site_id):
    """Add or change the person's row at one site: ``{role, all_units, unit_ids}``."""
    clean, errors = validate_site_row(request.get_json(silent=True))
    if errors:
        raise ApiError(errors[0]["message"], 400, errors[0]["field"])
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        person = _lock_row(cur, "people", person_id)                          # (1); 404
        stored = _lock_site_rows(cur, person_id).get(site_id)                 # (2)
        _check_site_row(cur, site_id, clean, stored, "site_id")              # (3); 400
        no_login_message = no_login_role_error([clean["role"]]) if person["username"] is None else None
        if no_login_message:
            raise ApiError(no_login_message, 400, "role")
        _check_site_write(person, site_id, stored["role"] if stored else None, clean["role"])   # 403
        before = _site_rows(cur, [person_id])[person_id].get(site_id)
        _write_site_row(cur, person_id, site_id, clean, stored)
        after = _site_rows(cur, [person_id])[person_id].get(site_id)
    return _site_row_response(conn, person_id, before, after)


@masters_bp.route("/people/<int:person_id>/sites/<int:site_id>", methods=["DELETE"])
@require_perm("people:assign_technicians")
def delete_person_site(person_id, site_id):
    """Remove the person's row at one site (its role and its units)."""
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        person = _lock_row(cur, "people", person_id)                          # (1); 404
        stored = _lock_site_rows(cur, person_id).get(site_id)                 # (2)
        if stored is None:
            raise ApiError("Not found", 404)
        _check_site_write(person, site_id, stored["role"], None)              # 403
        before = _site_rows(cur, [person_id])[person_id].get(site_id)
        _delete_site_row(cur, person_id, site_id, stored)
    return _site_row_response(conn, person_id, before, None)
