"""Masters module — sites, units, equipment classes and types, manufacturers and equipment
models, trades, the Team register of people and their roles per site, failure codes
(docs/steps/S001-basic-masters/1-brief.md; equipment types: S004; trades and Team: S010 A1;
site roles: S011 A1; manufacturers and models: S012; failure modes, causes and maintenance
actions: S016; meter types: S037).

Thin shell: masters_core validates input, this module fetches, checks the
rules that need the database, and stores.  Pooled connections are autocommit,
so anything that checks and then writes runs in transaction() with the parent
row locked first.

Equipment types, and failure modes of a class, lock class → type (mode).  Manufacturers and
models lock manufacturer → model → class → type (S012 § 5.5), the order equipment.py also
follows (model (4), class (5)):
- model create: manufacturer → class → type → insert;
- model reactivate: manufacturer → model → class (the model's ids, which never change,
  read plainly first);
- model designation edit or deactivate: the model row alone;
- manufacturer deactivate: its row, then a plain count of its active models (a concurrent
  model reactivate waits on the manufacturer lock);
- class deactivate: its row, then a plain count of its active models (a concurrent model
  create or reactivate waits on the class lock).
People lock person → trades → the person's memberships and person_units rows → units; the
membership insert then takes its site row through the FK (unit → site, as update_unit).
Model meters (S038 § 5.4) lock model → meter type → the model_meters row: (4) → (4b) of
equipment.py's order; no model meter write takes a manufacturer, class or type.  A meter
type update locks the meter type alone, then counts its model_meters and node_meters rows
LOCK IN SHARE MODE (the freeze, S038 § 5.3): link rows are touched only by link writes,
which hold the meter type's lock first, so the share locks join no cycle.
Equipment categories (S063 § 5.3) come after the class: a class update locks its row, then the
category it moves into or is reactivated in; a class create locks only that category.  A
category deactivate locks its row, then makes a plain count of its active classes (a concurrent
class write that would put an active class in it waits on the category lock).  No category
write takes a class lock, so no cycle.
"""

import logging

from flask import Blueprint, jsonify, request

from api_common import UNIQUE_KEY_ERRORS, ApiError, actor, clean_body
from auth_utils import has_perm, has_perm_at, require_perm, require_perm_at
from db_helpers import count, fetch_one, get_db, insert_row, rows_to_list, transaction, update_row
from equipment_core import check_type_class
from meters_core import (
    ACTION_REMOVE, NO_LIMITS, format_number, limits_text, meter_type_of, parse_change_action, parse_meter_type_id,
    validate_limits,
)
from tickets_core import CLOSED, close_tickets_first
from masters_core import (
    CLASS_CATEGORY_INACTIVE, category_in_use, model_label, no_login_role_error, normalise_username, technician_only,
    validate_equipment_category, validate_equipment_class, validate_equipment_model, validate_equipment_type,
    validate_failure_cause, validate_failure_mode, validate_maintenance_action, validate_manufacturer, validate_person, validate_site, validate_site_row,
    validate_meter_type, validate_site_rows, validate_trade, validate_unit,
)

logger = logging.getLogger(__name__)

masters_bp = Blueprint("masters", __name__)

# Named UNIQUE indexes (migration v2) -> the field to flag and a plain message
UNIQUE_KEY_ERRORS.update({
    "uq_sites_code": ("code", "A site with this code already exists"),
    "uq_units_site_code": ("code", "A unit with this code already exists at this site"),
    "uq_units_warehouse": ("oneerp_warehouse", "This OneERP warehouse is already mapped to another unit"),
    "uq_equipment_classes_code": ("code", "An equipment class with this code already exists"),
    # Migration v35 (S063)
    "uq_equipment_categories_name": ("name", "A category with this name already exists"),
    "uq_sites_default": ("is_default", "Another site was made the default at the same time; reload and try again"),
    # Migration v5 (S004)
    "uq_equipment_types_class_name": ("name", "A type with this name already exists in this class"),
    # Migration v7 (S010, amendment A1)
    "uq_trades_name": ("name", "A trade with this name exists"),
    # Migration v29 (S037)
    "uq_meter_types_name": ("name", "A meter type with this name exists"),
    # Migration v30 (S038)
    "uq_model_meters": ("meter_type_id", "This model already has this meter"),
    "uq_people_username": ("username", "Another person already has this login (it may be an inactive one)"),
    # Migration v9 (S012)
    "uq_manufacturers_name": ("name", "A manufacturer with this name exists"),
    "uq_equipment_models_maker_designation": ("designation",
                                              "This manufacturer already has a model with this designation"),
    # Migration v11 (S016)
    "uq_failure_modes_code": ("code", "A failure mode with this code exists"),
    "uq_failure_causes_code": ("code", "A failure cause with this code exists"),
    "uq_failure_causes_label": ("label", "A failure cause with this label exists"),
    "uq_maintenance_actions_code": ("code", "A maintenance action with this code exists"),
    "uq_maintenance_actions_label": ("label", "A maintenance action with this label exists"),
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

# A class with its category's name (S063 § 5.2); category_name is NULL with no category
_CLASS_SELECT = (
    "SELECT c.*, cat.name AS category_name FROM equipment_classes c"
    " LEFT JOIN equipment_categories cat ON cat.id = c.category_id"
)

# class_count: the active classes in the category, the number that blocks deactivation (S063 D8)
_CATEGORY_SELECT = (
    "SELECT cat.*, (SELECT COUNT(*) FROM equipment_classes c WHERE c.category_id = cat.id AND c.active = 1)"
    " AS class_count FROM equipment_categories cat"
)

_TYPE_SELECT = (
    "SELECT t.*, c.code AS class_code FROM equipment_types t JOIN equipment_classes c ON c.id = t.class_id"
)

_MODEL_SELECT = (
    "SELECT m.*, mf.name AS manufacturer_name, c.code AS class_code, c.name AS class_name, t.name AS type_name "
    "FROM equipment_models m JOIN manufacturers mf ON mf.id = m.manufacturer_id "
    "JOIN equipment_classes c ON c.id = m.class_id LEFT JOIN equipment_types t ON t.id = m.type_id"
)

# class_code is NULL for a General mode (every class)
_FAILURE_MODE_SELECT = (
    "SELECT f.*, c.code AS class_code FROM failure_modes f LEFT JOIN equipment_classes c ON c.id = f.class_id"
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
    """Access rows, any equipment — scrapped included, it still carries the unit in its
    history — or any ticket, open or closed (S025 § 5.3), freeze the unit's code and site.  Of
    the equipment only machine rows hold a unit_id; parts follow their machine.  A ticket's
    unit_id is the place of the failure and the site its writes are checked at (S017 § 5.3).
    The ticket count is a locking read under the unit's lock, as _check_code_frozen: a raise
    holding the unit's FK lock commits first and is counted."""
    return (count(cur, "SELECT COUNT(*) AS n FROM person_units WHERE unit_id = %s", (unit_id,))
            or count(cur, "SELECT COUNT(*) AS n FROM equipment WHERE unit_id = %s", (unit_id,))
            or count(cur, "SELECT COUNT(*) AS n FROM tickets WHERE unit_id = %s LOCK IN SHARE MODE", (unit_id,)))


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
        # A ticket not closed keeps its unit active: inactive units drop out of access, so the
        # team could no longer close it (S025 § 5.3).  First, so the count is what the user sees.
        if clean.get("active") == 0:
            open_tickets = count(cur, "SELECT COUNT(*) AS n FROM tickets WHERE unit_id = %s AND state <> %s"
                                      " LOCK IN SHARE MODE", (unit_id, CLOSED))
            if open_tickets:
                raise ApiError(close_tickets_first(open_tickets), 409, "active")
        # Laid-up (out_of_use) equipment still stands in the unit, so it blocks too (S002 § 10.2)
        if clean.get("active") == 0 and count(
                cur, "SELECT COUNT(*) AS n FROM equipment WHERE unit_id = %s AND lifecycle <> 'scrapped'",
                (unit_id,)):
            raise ApiError("The unit holds equipment that is not scrapped; move or scrap it first",
                           409, "active")
        if site_changes or clean.get("active") == 1:
            _lock_site_for_unit(cur, clean.get("site_id", unit["site_id"]))
        update_row(cur, "units", unit_id, clean, actor())
    with conn.cursor() as cur:
        return jsonify(fetch_one(cur, f"{_UNIT_SELECT} WHERE u.id = %s", (unit_id,)))


# ---------------------------------------------------------------------------
# Equipment categories (S063) — a group of equipment classes (ISO 14224 Annex A); a name only
# ---------------------------------------------------------------------------

@masters_bp.route("/equipment-categories")
@require_perm("masters:read")
def list_equipment_categories():
    where = "" if _include_inactive() else " WHERE cat.active = 1"
    with get_db().cursor() as cur:
        return _list_response(cur, f"{_CATEGORY_SELECT}{where} ORDER BY cat.name")


def _fetch_category(cur, category_id):
    return fetch_one(cur, f"{_CATEGORY_SELECT} WHERE cat.id = %s", (category_id,))


@masters_bp.route("/equipment-categories", methods=["POST"])
@require_perm("equipment:edit")
def create_equipment_category():
    clean = clean_body(validate_equipment_category, creating=True)
    with get_db().cursor() as cur:
        category_id = insert_row(cur, "equipment_categories", clean, actor())
        return jsonify(_fetch_category(cur, category_id)), 201


@masters_bp.route("/equipment-categories/<int:category_id>", methods=["PUT"])
@require_perm("equipment:edit")
def update_equipment_category(category_id):
    """Rename, deactivate or reactivate.  Deactivating is refused while an active class is in
    the category (S063 § 5.1); inactive classes may keep it."""
    clean = clean_body(validate_equipment_category, creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        _lock_row(cur, "equipment_categories", category_id)
        if clean.get("active") == 0:
            # The transaction's first plain read: its snapshot starts after the lock is held
            active_classes = count(cur, "SELECT COUNT(*) AS n FROM equipment_classes"
                                        " WHERE category_id = %s AND active = 1", (category_id,))
            if active_classes:
                raise ApiError(category_in_use(active_classes), 409, "active")
        update_row(cur, "equipment_categories", category_id, clean, actor())
    with conn.cursor() as cur:
        return jsonify(_fetch_category(cur, category_id))


# ---------------------------------------------------------------------------
# Equipment classes
# ---------------------------------------------------------------------------

def _fetch_class(cur, class_id):
    return fetch_one(cur, f"{_CLASS_SELECT} WHERE c.id = %s", (class_id,))


@masters_bp.route("/equipment-classes")
@require_perm("masters:read")
def list_equipment_classes():
    where = "" if _include_inactive() else " WHERE c.active = 1"
    with get_db().cursor() as cur:
        return _list_response(cur, f"{_CLASS_SELECT}{where} ORDER BY c.code")


@masters_bp.route("/equipment-classes", methods=["POST"])
@require_perm("equipment:edit")
def create_equipment_class():
    clean = clean_body(validate_equipment_class, creating=True)
    conn = get_db()
    # A transaction, so the category's lock holds until the insert commits (S063 § 5.3)
    with transaction(conn), conn.cursor() as cur:
        if clean.get("category_id") is not None:
            _lock_active_parent(cur, "equipment_categories", clean["category_id"], "category_id", "category")
        class_id = insert_row(cur, "equipment_classes", clean, actor())
    with conn.cursor() as cur:
        return jsonify(_fetch_class(cur, class_id)), 201


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
        # Otherwise the class could be inactive while its models still put new equipment in it
        # (S012 § 5.2); a concurrent model create or reactivate waits on this class lock
        if clean.get("active") == 0 and count(
                cur, "SELECT COUNT(*) AS n FROM equipment_models WHERE class_id = %s AND active = 1", (class_id,)):
            raise ApiError("Deactivate this class's models first", 409, "active")
        _lock_category_of_class(cur, clean, record)
        update_row(cur, "equipment_classes", class_id, clean, actor())
    with conn.cursor() as cur:
        return jsonify(_fetch_class(cur, class_id))


def _lock_category_of_class(cur, clean, record):
    """Lock the category a class save moves the class into, or reactivates it in (S063 § 5.2):
    it must exist (400) and be active (409).  A save that keeps the category of an active
    class, or leaves the class inactive in its category, does not read it."""
    new_category = clean.get("category_id")
    if new_category is not None and new_category != record["category_id"]:
        _lock_active_parent(cur, "equipment_categories", new_category, "category_id", "category")
        return
    reactivating = clean.get("active") == 1 and not record["active"]
    kept_category = clean.get("category_id", record["category_id"])
    if reactivating and kept_category is not None:
        # The stored category exists (the foreign key); its refusal says what to do (KLA, CR1-03)
        cur.execute("SELECT active FROM equipment_categories WHERE id = %s FOR UPDATE", (kept_category,))
        if not cur.fetchone()["active"]:
            raise ApiError(CLASS_CATEGORY_INACTIVE, 409, "active")


# ---------------------------------------------------------------------------
# Equipment types — per class (ISO 14224); the class is fixed after create
# ---------------------------------------------------------------------------

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
        _lock_active_parent(cur, "equipment_classes", clean["class_id"], "class_id", "class")
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
            _lock_active_parent(cur, "equipment_classes", stored["class_id"], "active", "class")
        record = _lock_row(cur, "equipment_types", type_id)
        if "class_id" in clean:
            if clean["class_id"] != record["class_id"]:
                raise ApiError("Class cannot be changed", 400, "class_id")
            del clean["class_id"]
        update_row(cur, "equipment_types", type_id, clean, actor())
    with conn.cursor() as cur:
        return jsonify(_fetch_type(cur, type_id))


# ---------------------------------------------------------------------------
# Manufacturers and equipment models (S012) — ISO 14224's manufacturer's name and model
# designation.  A model belongs to one class and at most one type of it, fixed after create.
# ---------------------------------------------------------------------------

@masters_bp.route("/manufacturers")
@require_perm("masters:read")
def list_manufacturers():
    where = "" if _include_inactive() else "WHERE active = 1 "
    with get_db().cursor() as cur:
        return _list_response(cur, f"SELECT * FROM manufacturers {where}ORDER BY name")


@masters_bp.route("/manufacturers", methods=["POST"])
@require_perm("equipment:edit")
def create_manufacturer():
    clean = clean_body(validate_manufacturer, creating=True)
    with get_db().cursor() as cur:
        manufacturer_id = insert_row(cur, "manufacturers", clean, actor())
        return jsonify(fetch_one(cur, "SELECT * FROM manufacturers WHERE id = %s", (manufacturer_id,))), 201


@masters_bp.route("/manufacturers/<int:manufacturer_id>", methods=["PUT"])
@require_perm("equipment:edit")
def update_manufacturer(manufacturer_id):
    """Rename (a typo: models and equipment show the new name at once), deactivate or
    reactivate.  Deactivating needs its models deactivated first, as a site its units."""
    clean = clean_body(validate_manufacturer, creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        _lock_row(cur, "manufacturers", manufacturer_id)
        if clean.get("active") == 0 and count(
                cur, "SELECT COUNT(*) AS n FROM equipment_models WHERE manufacturer_id = %s AND active = 1",
                (manufacturer_id,)):
            raise ApiError("The manufacturer has active models; deactivate them first", 409, "active")
        update_row(cur, "manufacturers", manufacturer_id, clean, actor())
    with conn.cursor() as cur:
        return jsonify(fetch_one(cur, "SELECT * FROM manufacturers WHERE id = %s", (manufacturer_id,)))


def _model_out(row):
    row["label"] = model_label(row["manufacturer_name"], row["designation"])
    return row


def _fetch_model(cur, model_id):
    return _model_out(fetch_one(cur, f"{_MODEL_SELECT} WHERE m.id = %s", (model_id,)))


def _lock_active_parent(cur, table, record_id, field, label):
    """Lock the manufacturer or class a model is created or reactivated under, or the category
    a class is put in or reactivated in (S063): it must exist (400 Unknown …) and be active
    (409).  ``table`` is a code constant, never client input; ``field`` is the id field on
    create, active on reactivation."""
    cur.execute(f"SELECT id, active FROM {table} WHERE id = %s FOR UPDATE", (record_id,))
    row = cur.fetchone()
    if row is None:
        raise ApiError(f"Unknown {label}", 400, field)
    if not row["active"]:
        raise ApiError(f"The {label} is inactive", 409, field)


def lock_type_of_class(cur, type_id, class_id):
    """Lock the type a write newly picks for a record of ``class_id``: a new model's type, or
    a model-less component unit's (equipment.py, S033 § 5.2).  A type of that class (400,
    S004), active (409)."""
    cur.execute("SELECT id, class_id, active FROM equipment_types WHERE id = %s FOR UPDATE", (type_id,))
    equipment_type = cur.fetchone()
    if equipment_type is None:
        raise ApiError("Unknown type", 400, "type_id")
    message = check_type_class(equipment_type["class_id"], class_id)
    if message:
        raise ApiError(message, 400, "type_id")
    if not equipment_type["active"]:
        raise ApiError("The type is inactive", 409, "type_id")


@masters_bp.route("/equipment-models")
@require_perm("masters:read")
def list_equipment_models():
    conditions, params = [], []
    if not _include_inactive():
        conditions.append("m.active = 1")
    for name in ("class_id", "manufacturer_id"):
        value = _int_filter(name)
        if value is not None:
            conditions.append(f"m.{name} = %s")
            params.append(value)
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    with get_db().cursor() as cur:
        return _list_response(cur, f"{_MODEL_SELECT}{where} ORDER BY mf.name, m.designation", params,
                              convert=_model_out)


@masters_bp.route("/equipment-models", methods=["POST"])
@require_perm("equipment:edit")
def create_equipment_model():
    clean = clean_body(validate_equipment_model, creating=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        _lock_active_parent(cur, "manufacturers", clean["manufacturer_id"], "manufacturer_id", "manufacturer")
        _lock_active_parent(cur, "equipment_classes", clean["class_id"], "class_id", "class")
        if clean.get("type_id") is not None:
            lock_type_of_class(cur, clean["type_id"], clean["class_id"])
        model_id = insert_row(cur, "equipment_models", clean, actor())
    with conn.cursor() as cur:
        return jsonify(_fetch_model(cur, model_id)), 201


@masters_bp.route("/equipment-models/<int:model_id>", methods=["PUT"])
@require_perm("equipment:edit")
def update_equipment_model(model_id):
    """Edit the designation (a typo), deactivate or reactivate.  The manufacturer, class and
    type are fixed: a wrong model is deactivated and a new one created (S012 § 5.2).  An
    inactive model stays on its equipment; it just can't be newly picked."""
    clean = clean_body(validate_equipment_model, creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        # A plain read of the fixed ids is safe (they never change) and lets the reactivation
        # lock the manufacturer before the model: the manufacturer → model → class order
        stored = fetch_one(cur, "SELECT manufacturer_id, class_id, type_id FROM equipment_models WHERE id = %s",
                           (model_id,))
        if stored is None:
            raise ApiError("Not found", 404)
        for field, label in (("manufacturer_id", "Manufacturer"), ("class_id", "Class"), ("type_id", "Type")):
            if field in clean:
                if clean[field] != stored[field]:
                    raise ApiError(f"{label} cannot be changed", 400, field)
                del clean[field]
        reactivating = clean.get("active") == 1
        if reactivating:
            _lock_active_parent(cur, "manufacturers", stored["manufacturer_id"], "active", "manufacturer")
        _lock_row(cur, "equipment_models", model_id)
        if reactivating:
            _lock_active_parent(cur, "equipment_classes", stored["class_id"], "active", "class")
        update_row(cur, "equipment_models", model_id, clean, actor())
    with conn.cursor() as cur:
        return jsonify(_fetch_model(cur, model_id))


# ---------------------------------------------------------------------------
# Failure codes (S016) — ISO 14224 § 9 and Annex B: failure modes (what is seen: the
# operator's symptom), failure causes (in ISO's five groups) and maintenance actions.
# Read by everyone, kept by failure_codes:edit.  A failure mode's code is frozen once a ticket
# uses it (S017 § 5.7, S016 § 5.4); S018 does the same for causes and actions.  A cause's code is
# frozen also once an improvement's root cause uses it (S069 § 5.5).
# ---------------------------------------------------------------------------

def _fetch_failure_mode(cur, mode_id):
    return fetch_one(cur, f"{_FAILURE_MODE_SELECT} WHERE f.id = %s", (mode_id,))


def _check_mode_label(cur, label, class_id, mode_id=None):
    """A mode's label is unique within what one picker shows (S016 § 5.1): a class mode's
    against its class and the General ones; a General mode's against every mode.  Inactive
    rows count, so a reactivation can't bring a duplicate back.  Plain ``=``: the column's
    case-insensitive collation applies.  Not an index (the scope crosses the NULL class), so
    two saves at the same moment could both pass: accepted (§ 7 decision 8)."""
    scope = "" if class_id is None else " AND (f.class_id = %s OR f.class_id IS NULL)"
    params = [label, mode_id or 0] + ([] if class_id is None else [class_id])
    cur.execute(f"{_FAILURE_MODE_SELECT} WHERE f.label = %s AND f.id <> %s{scope} LIMIT 1", params)
    clash = cur.fetchone()
    if clash is not None:
        where = f"of class {clash['class_code']}" if clash["class_code"] else "General"
        raise ApiError(f"A failure mode with this label exists ({clash['code']}, {where})", 409, "label")


@masters_bp.route("/failure-modes")
@require_perm("masters:read")
def list_failure_modes():
    """``class_id=N`` -> the modes of class N plus the General ones, by label: the list a
    ticket on equipment of class N offers (S017).  Without it every mode: General first, then
    by class code, then by label."""
    conditions, params = [], []
    if not _include_inactive():
        conditions.append("f.active = 1")
    class_id = _int_filter("class_id")
    if class_id is not None:
        conditions.append("(f.class_id = %s OR f.class_id IS NULL)")
        params.append(class_id)
        order = "f.label"
    else:
        order = "f.class_id IS NOT NULL, c.code, f.label"
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    with get_db().cursor() as cur:
        return _list_response(cur, f"{_FAILURE_MODE_SELECT}{where} ORDER BY {order}", params)


@masters_bp.route("/failure-modes", methods=["POST"])
@require_perm("failure_codes:edit")
def create_failure_mode():
    clean = clean_body(validate_failure_mode, creating=True)
    class_id = clean.get("class_id")
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        if class_id is not None:
            _lock_active_parent(cur, "equipment_classes", class_id, "class_id", "class")
        _check_mode_label(cur, clean["label"], class_id)
        mode_id = insert_row(cur, "failure_modes", clean, actor())
    with conn.cursor() as cur:
        return jsonify(_fetch_failure_mode(cur, mode_id)), 201


@masters_bp.route("/failure-modes/<int:mode_id>", methods=["PUT"])
@require_perm("failure_codes:edit")
def update_failure_mode(mode_id):
    """Edit code, label, description; deactivate or reactivate.  The class is fixed (S016
    § 5.2): a mode made under the wrong class is deactivated and made again, so tickets that
    use it are never re-labelled.  The code is frozen once a ticket uses the mode (S017 § 5.7):
    decided under the mode's lock, which a ticket insert's foreign-key check waits for, so the
    count cannot miss a ticket.  Deactivating needs no check."""
    clean = clean_body(validate_failure_mode, creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        # A plain read of the class is safe (it never changes) and lets the reactivation lock
        # the class before the mode: the class → mode order, as for types
        stored = fetch_one(cur, "SELECT class_id FROM failure_modes WHERE id = %s", (mode_id,))
        if stored is None:
            raise ApiError("Not found", 404)
        if "class_id" in clean:
            if clean["class_id"] != stored["class_id"]:
                raise ApiError("Class cannot be changed", 400, "class_id")
            del clean["class_id"]
        if clean.get("active") == 1 and stored["class_id"] is not None:
            _lock_active_parent(cur, "equipment_classes", stored["class_id"], "active", "class")
        locked = _lock_row(cur, "failure_modes", mode_id)
        _check_code_frozen(cur, clean, locked, "failure_mode_id")
        if "label" in clean:
            _check_mode_label(cur, clean["label"], stored["class_id"], mode_id)
        update_row(cur, "failure_modes", mode_id, clean, actor())
    with conn.cursor() as cur:
        return jsonify(_fetch_failure_mode(cur, mode_id))


def _check_code_frozen(cur, clean, locked, ticket_column, root_cause_column=None):
    """A code change on a failure code a ticket uses -> 409 (S017 § 5.7, S018 § 5.6); with
    ``root_cause_column``, also on one an improvement's root cause uses (S069 § 5.5).  Under the
    record's lock (``locked``), and each count is a locking read: a plain snapshot taken before a
    ticket or root-cause write that held the record's FK lock had committed would miss it.  The
    column names are code constants, never client input."""
    if "code" not in clean or clean["code"] == locked["code"]:
        return
    if count(cur, f"SELECT COUNT(*) AS n FROM tickets WHERE {ticket_column} = %s LOCK IN SHARE MODE",
             (locked["id"],)):
        raise ApiError("This code is used by tickets and can no longer change", 409, "code")
    if root_cause_column is not None and count(
            cur, f"SELECT COUNT(*) AS n FROM improvements WHERE {root_cause_column} = %s LOCK IN SHARE MODE",
            (locked["id"],)):
        raise ApiError("This code is used by an improvement's root cause and can no longer change", 409, "code")


def _create_plain_master(table, validator):
    """POST of a master with no parent and no rule beyond its unique keys (a duplicate is the
    database's 409).  ``table`` is a code constant, never client input."""
    clean = clean_body(validator, creating=True)
    with get_db().cursor() as cur:
        record_id = insert_row(cur, table, clean, actor())
        return jsonify(fetch_one(cur, f"SELECT * FROM {table} WHERE id = %s", (record_id,))), 201


def _update_plain_master(table, record_id, validator, used_by, root_cause_column=None):
    """PUT of such a master: absent fields stay as they are; an unknown id is a 404.  The code
    is frozen once a ticket uses the record: ``used_by`` is the ticket column that points at it
    (S018 § 5.6); ``root_cause_column`` the improvements column, for a cause (S069 § 5.5); every
    other field stays editable."""
    clean = clean_body(validator, creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        locked = _lock_row(cur, table, record_id)
        _check_code_frozen(cur, clean, locked, used_by, root_cause_column)
        update_row(cur, table, record_id, clean, actor())
    with conn.cursor() as cur:
        return jsonify(fetch_one(cur, f"SELECT * FROM {table} WHERE id = %s", (record_id,)))


@masters_bp.route("/failure-causes")
@require_perm("masters:read")
def list_failure_causes():
    """By group, then code: the ENUM sorts in its declared order (design … misc), so a local
    cause stays in its ISO group."""
    where = "" if _include_inactive() else "WHERE active = 1 "
    with get_db().cursor() as cur:
        return _list_response(cur, f"SELECT * FROM failure_causes {where}ORDER BY cause_group, code")


@masters_bp.route("/failure-causes", methods=["POST"])
@require_perm("failure_codes:edit")
def create_failure_cause():
    return _create_plain_master("failure_causes", validate_failure_cause)


@masters_bp.route("/failure-causes/<int:cause_id>", methods=["PUT"])
@require_perm("failure_codes:edit")
def update_failure_cause(cause_id):
    """The group may change, also once in use: a reclassification for all history, as the
    ISO roll-up wants (S016 § 5.3); it reclassifies the root causes too.  The code is frozen once a
    ticket uses the cause (S018 § 5.6), or an improvement's root cause does (S069 § 5.5)."""
    return _update_plain_master("failure_causes", cause_id, validate_failure_cause, "cause_id", "root_cause_id")


@masters_bp.route("/maintenance-actions")
@require_perm("masters:read")
def list_maintenance_actions():
    """By code length, then code: ISO's 1 … 12 come in number order."""
    where = "" if _include_inactive() else "WHERE active = 1 "
    with get_db().cursor() as cur:
        return _list_response(cur, f"SELECT * FROM maintenance_actions {where}ORDER BY CHAR_LENGTH(code), code")


@masters_bp.route("/maintenance-actions", methods=["POST"])
@require_perm("failure_codes:edit")
def create_maintenance_action():
    return _create_plain_master("maintenance_actions", validate_maintenance_action)


@masters_bp.route("/maintenance-actions/<int:action_id>", methods=["PUT"])
@require_perm("failure_codes:edit")
def update_maintenance_action(action_id):
    return _update_plain_master("maintenance_actions", action_id, validate_maintenance_action, "action_id")


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
            raise ApiError(f"That {label} no longer exists. Reload and try again.", 400, field)
        row = rows_by_id[record_id]
        if not row["active"] and record_id not in held:
            # A unit by its code, a trade (no code) by its name; never the id (S064 UX-13 row 17)
            shown = row.get("code") or row["name"]
            raise ApiError(f"{label.capitalize()} {shown} is inactive. Untick it or reactivate it.", 400, field)
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
# Meter types (S037) — the catalogue of quantities a model or a machine can carry.  Edited with
# equipment:edit like models; a meter type is not at a site.  Update locks the row alone.
# ---------------------------------------------------------------------------

@masters_bp.route("/meter-types")
@require_perm("masters:read")
def list_meter_types():
    where = "" if _include_inactive() else "WHERE active = 1 "
    with get_db().cursor() as cur:
        return _list_response(cur, f"SELECT * FROM meter_types {where}ORDER BY name")


@masters_bp.route("/meter-types", methods=["POST"])
@require_perm("equipment:edit")
def create_meter_type():
    clean = clean_body(validate_meter_type, creating=True)
    with get_db().cursor() as cur:
        meter_type_id = insert_row(cur, "meter_types", clean, actor())
        return jsonify(fetch_one(cur, "SELECT * FROM meter_types WHERE id = %s", (meter_type_id,))), 201


@masters_bp.route("/meter-types/<int:meter_type_id>", methods=["PUT"])
@require_perm("equipment:edit")
def update_meter_type(meter_type_id):
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        stored = _lock_row(cur, "meter_types", meter_type_id)
        clean = clean_body(lambda data, creating: validate_meter_type(data, creating, stored), creating=False)
        _check_meter_type_frozen(cur, clean, stored)
        update_row(cur, "meter_types", meter_type_id, clean, actor())
    with conn.cursor() as cur:
        return jsonify(fetch_one(cur, "SELECT * FROM meter_types WHERE id = %s", (meter_type_id,)))


# What a meter type's readings mean: frozen once a model or a node uses the type (S038 § 1.5)
_FROZEN_WHEN_USED = ("kind", "unit", "decimals", "expected_answer")
METER_TYPE_IN_USE = ("This meter type is in use. Its kind, unit, decimals and expected answer cannot change. "
                     "Make a new meter type.")


def _check_meter_type_frozen(cur, clean, locked):
    """A change of kind, unit, decimals or expected answer on a meter type that any model meter
    or node meter uses, active or not -> 409.  A change is a value that differs from the stored
    one, as _check_code_frozen decides, so the edit dialog re-sending them passes.  Under the
    type's lock, and the counts are locking reads: a plain snapshot could miss a link committed
    while this request waited for the lock (S038 § 5.4)."""
    changed = [field for field in _FROZEN_WHEN_USED if field in clean and clean[field] != locked[field]]
    if not changed:
        return
    for table in ("model_meters", "node_meters"):
        if count(cur, f"SELECT COUNT(*) AS n FROM {table} WHERE meter_type_id = %s LOCK IN SHARE MODE",
                 (locked["id"],)):
            raise ApiError(METER_TYPE_IN_USE, 409, changed[0])


# ---------------------------------------------------------------------------
# Model meters (S038) — the meters every machine of a model carries, with a gauge's default
# limits.  Read with masters:read, edited with equipment:edit (as models).  Remove sets the
# row inactive, so readings (S039) keep their meaning; an add of a removed type brings the
# row back.  An inactive model may gain and lose meters: it stays on its machines (BR2-03).
# ---------------------------------------------------------------------------

_MODEL_METER_SELECT = (
    "SELECT mm.id, mm.model_id, mm.min_value, mm.max_value, mm.active,"
    " t.id AS t_id, t.name AS t_name, t.unit AS t_unit, t.kind AS t_kind, t.decimals AS t_decimals,"
    " t.expected_answer AS t_expected_answer"
    " FROM model_meters mm JOIN meter_types t ON t.id = mm.meter_type_id"
)


def _model_meter_row(row):
    return {"id": row["id"], "meter_type": meter_type_of(row), "min_value": row["min_value"],
            "max_value": row["max_value"], "active": row["active"]}


def read_models_meters(cur, model_ids, include_inactive=False):
    """Plain read of several models' meters in one query -> {model_id: [meter, ...]}, each list by
    meter type name, in the shape meters_core takes (S040: the readings sheet reads a whole site)."""
    out = {model_id: [] for model_id in model_ids}
    if not out:
        return out
    where = "" if include_inactive else " AND mm.active = 1"
    marks = ", ".join(["%s"] * len(out))
    cur.execute(f"{_MODEL_METER_SELECT} WHERE mm.model_id IN ({marks}){where} ORDER BY t.name, t.id", list(out))
    for row in cur.fetchall():
        out[row["model_id"]].append(_model_meter_row(row))
    return out


def read_model_meters(cur, model_id, include_inactive=False):
    """Plain read of a model's meters, by meter type name, in the shape meters_core takes."""
    return read_models_meters(cur, [model_id], include_inactive)[model_id]


def _model_meter_out(row):
    pair = (row["min_value"], row["max_value"])
    return {"id": row["id"], "meter_type": row["meter_type"], "min_value": format_number(pair[0]),
            "max_value": format_number(pair[1]), "limits_text": limits_text(row["meter_type"], pair),
            "active": row["active"]}


def _fetch_model_meter(cur, model_meter_id):
    cur.execute(f"{_MODEL_METER_SELECT} WHERE mm.id = %s", (model_meter_id,))
    return _model_meter_out(_model_meter_row(cur.fetchone()))


def lock_meter_type(cur, meter_type_id, adding):
    """Lock the meter type of a link write ((4b) of equipment.py's order).  An add needs a known
    (400) and active (409) type; a change of an existing link takes the type as it is: a
    deactivated type stays in force where it is linked (S037 § 1.1)."""
    cur.execute("SELECT id, name, unit, kind, decimals, expected_answer, active FROM meter_types"
                " WHERE id = %s FOR UPDATE", (meter_type_id,))
    meter_type = cur.fetchone()
    if meter_type is None:
        if adding:
            raise ApiError("Unknown meter type", 400, "meter_type_id")
        raise ApiError("Not found", 404)
    if adding and not meter_type["active"]:
        raise ApiError("This meter type is inactive. Pick another meter type.", 409, "meter_type_id")
    return meter_type


def checked_limits(body, meter_type, stored):
    """validate_limits for the locked meter type, its first error a 400."""
    pair, errors = validate_limits(body, meter_type["kind"], meter_type["decimals"], stored)
    if errors:
        raise ApiError(errors[0]["message"], 400, errors[0]["field"])
    return pair


@masters_bp.route("/equipment-models/<int:model_id>/meters")
@require_perm("masters:read")
def list_model_meters(model_id):
    with get_db().cursor() as cur:
        if fetch_one(cur, "SELECT id FROM equipment_models WHERE id = %s", (model_id,)) is None:
            raise ApiError("Not found", 404)
        return jsonify([_model_meter_out(row) for row in read_model_meters(cur, model_id, _include_inactive())])


@masters_bp.route("/equipment-models/<int:model_id>/meters", methods=["POST"])
@require_perm("equipment:edit")
def add_model_meter(model_id):
    """Add a meter type to a model, or bring a removed one back with the sent limits (BR1-18)."""
    meter_type_id = clean_body(lambda body, _creating: parse_meter_type_id(body), creating=True)
    body = request.get_json(silent=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        _lock_row(cur, "equipment_models", model_id)                       # (4); 404
        meter_type = lock_meter_type(cur, meter_type_id, adding=True)      # (4b)
        cur.execute("SELECT id, active FROM model_meters WHERE model_id = %s AND meter_type_id = %s FOR UPDATE",
                    (model_id, meter_type_id))
        existing = cur.fetchone()
        if existing is not None and existing["active"]:
            raise ApiError("This model already has this meter", 409, "meter_type_id")
        low, high = checked_limits(body, meter_type, NO_LIMITS)
        values = {"min_value": low, "max_value": high}
        if existing is not None:
            update_row(cur, "model_meters", existing["id"], {**values, "active": 1}, actor())
            model_meter_id = existing["id"]
        else:
            model_meter_id = insert_row(cur, "model_meters",
                                        {"model_id": model_id, "meter_type_id": meter_type_id, **values}, actor())
    with conn.cursor() as cur:
        return jsonify(_fetch_model_meter(cur, model_meter_id)), 201


@masters_bp.route("/model-meters/<int:model_meter_id>", methods=["PUT"])
@require_perm("equipment:edit")
def update_model_meter(model_meter_id):
    """Set a model meter's limits, or remove it (``active: false``).  A removed row is not
    found here: an add brings it back."""
    action = clean_body(lambda body, _creating: parse_change_action(body, allow_use_model=False), creating=False)
    body = request.get_json(silent=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        # The model and type ids never change, so a plain read lets the locks run model ->
        # meter type -> row
        ids = fetch_one(cur, "SELECT model_id, meter_type_id FROM model_meters WHERE id = %s", (model_meter_id,))
        if ids is None:
            raise ApiError("Not found", 404)
        _lock_row(cur, "equipment_models", ids["model_id"])                         # (4)
        meter_type = lock_meter_type(cur, ids["meter_type_id"], adding=False)       # (4b)
        row = _lock_row(cur, "model_meters", model_meter_id)
        if not row["active"]:
            raise ApiError("Not found", 404)
        if action == ACTION_REMOVE:
            update_row(cur, "model_meters", model_meter_id, {"active": 0}, actor())
        else:
            low, high = checked_limits(body, meter_type, (row["min_value"], row["max_value"]))
            update_row(cur, "model_meters", model_meter_id, {"min_value": low, "max_value": high}, actor())
    with conn.cursor() as cur:
        return jsonify(_fetch_model_meter(cur, model_meter_id))


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

    def grantable_site_ids(self):
        """Active sites where this viewer may add a row for someone (a Technician row, for an
        engineer; any role, for IT admin), before any person's own rows are taken out.  The
        people list sends it for the Add dialog, which has no person yet (S064 § 5.6 rule 1)."""
        if self._active_site_ids is None:
            self._cur.execute("SELECT id FROM sites WHERE active = 1 ORDER BY code")
            self._active_site_ids = [r["id"] for r in self._cur.fetchall()]
        return [site_id for site_id in self._active_site_ids if self.it_admin or self.assigns_at(site_id)]

    def assignable_site_ids(self, person, present_site_ids):
        """Active sites where this viewer may add a row for the person."""
        if _is_own(person):
            return []
        return [site_id for site_id in self.grantable_site_ids() if site_id not in present_site_ids]


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
    (people:edit) learn whether a person has a login; the login itself, and the email address
    copied from it (S032 § 1.6), go only to those who maintain it, IT admin (A.5.15, A.5.34).
    Site rows: _SiteViewer.  -> (items, the viewer)."""
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
            del item["email"]
    return items, viewer


def _fetch_person(cur, person_id):
    cur.execute("SELECT * FROM people WHERE id = %s", (person_id,))
    items, _viewer = _people_out(cur, [cur.fetchone()])
    return items[0]


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
        items, viewer = _people_out(cur, cur.fetchall())
        body = {"items": items, "total": len(items)}
        # The sites the Add dialog offers (S064 UX-14): only editors get site data, as each item
        if viewer.editor:
            body["assignable_site_ids"] = viewer.grantable_site_ids()
    return jsonify(body)


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
        raise ApiError(f"Site {site['code']} is inactive. Remove the row or reactivate the site.", 400, field)
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
