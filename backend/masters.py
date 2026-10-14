"""Masters module — sites, units, equipment classes, users' unit access
(docs/steps/S001-basic-masters/1-brief.md).

Thin shell: masters_core validates input, this module fetches, checks the
rules that need the database, and stores.  Pooled connections are autocommit,
so anything that checks and then writes runs in transaction() with the parent
row locked first.
"""

import logging

from flask import Blueprint, jsonify, request

from api_common import UNIQUE_KEY_ERRORS, ApiError, actor, clean_body
from auth_utils import require_perm
from db_helpers import count, fetch_one, get_db, insert_row, rows_to_list, transaction, update_row
from masters_core import (
    validate_equipment_class, validate_site, validate_unit, validate_unit_ids, validate_username,
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

_USER_UNITS_SELECT = (
    "SELECT uu.username, u.id, CONCAT(s.code, '.', u.code) AS full_code, u.name, u.active "
    "FROM user_units uu JOIN units u ON u.id = uu.unit_id JOIN sites s ON s.id = u.site_id"
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

def _site_filter():
    raw = request.args.get("site_id")
    if raw is None:
        return None
    if not raw.isdigit():
        raise ApiError("site_id must be a number", 400, "site_id")
    return int(raw)


@masters_bp.route("/units")
@require_perm("masters:read")
def list_units():
    conditions, params = [], []
    if not _include_inactive():
        conditions.append("u.active = 1")
    site_id = _site_filter()
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
    return (count(cur, "SELECT COUNT(*) AS n FROM user_units WHERE unit_id = %s", (unit_id,))
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
# Users' unit access
# ---------------------------------------------------------------------------

def _unit_summary(row):
    return {"id": row["id"], "full_code": row["full_code"], "name": row["name"], "active": row["active"]}


def _user_units(cur, username):
    cur.execute(f"{_USER_UNITS_SELECT} WHERE uu.username = %s ORDER BY full_code", (username,))
    return [_unit_summary(r) for r in cur.fetchall()]


@masters_bp.route("/user-units")
@require_perm("masters:read_senior")
def list_user_units():
    by_user = {}
    with get_db().cursor() as cur:
        cur.execute(f"{_USER_UNITS_SELECT} ORDER BY uu.username, full_code")
        for row in cur.fetchall():
            by_user.setdefault(row["username"], []).append(_unit_summary(row))
    items = [{"username": name, "units": units} for name, units in by_user.items()]
    return jsonify({"items": items, "total": len(items)})


@masters_bp.route("/user-units/<username>", methods=["PUT"])
@require_perm("masters:edit")
def replace_user_units(username):
    """Replace the user's whole unit set atomically; a change is logged as the access trail."""
    username, errors = validate_username(username)
    if not errors:
        body = request.get_json(silent=True)
        unit_ids, errors = validate_unit_ids(body.get("unit_ids") if isinstance(body, dict) else None)
    if errors:
        raise ApiError(errors[0]["message"], 400, errors[0]["field"])

    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        # Lock the user's rows first so a concurrent replace for the same user waits and
        # then sees current data; otherwise both diff against stale sets and the log is wrong.
        cur.execute("SELECT unit_id FROM user_units WHERE username = %s FOR UPDATE", (username,))
        before = _user_units(cur, username)
        held = {u["id"] for u in before}
        _check_grantable(cur, unit_ids, held)
        # Diff rather than delete-all/insert-all, so units that stay keep their original granted_at/by
        for unit_id in held - set(unit_ids):
            cur.execute("DELETE FROM user_units WHERE username = %s AND unit_id = %s", (username, unit_id))
        for unit_id in unit_ids:
            if unit_id not in held:
                cur.execute("INSERT INTO user_units (username, unit_id, granted_by) VALUES (%s, %s, %s)",
                            (username, unit_id, actor()))
    with conn.cursor() as cur:
        after = _user_units(cur, username)
    if {u["id"] for u in before} != {u["id"] for u in after}:
        logger.info("user_units changed: actor=%s user=%s before=[%s] after=[%s]", actor(), username,
                    ",".join(u["full_code"] for u in before), ",".join(u["full_code"] for u in after))
    return jsonify({"username": username, "units": after})


def _check_grantable(cur, unit_ids, held):
    """Every id must be a unit; an inactive unit may be kept but not newly granted."""
    if not unit_ids:
        return
    placeholders = ", ".join(["%s"] * len(unit_ids))
    cur.execute(f"SELECT id, active FROM units WHERE id IN ({placeholders}) FOR UPDATE", unit_ids)
    active_by_id = {r["id"]: r["active"] for r in cur.fetchall()}
    for unit_id in unit_ids:
        if unit_id not in active_by_id:
            raise ApiError(f"Unknown unit {unit_id}", 400, "unit_ids")
        if not active_by_id[unit_id] and unit_id not in held:
            raise ApiError(f"Unit {unit_id} is inactive and cannot be newly granted", 400, "unit_ids")
