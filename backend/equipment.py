"""Equipment register — the equipment tree API
(docs/steps/S002-equipment-register/1-brief.md; types and notes: S004; models: S012;
QR labels and the by-code lookup: S014 — read-only, no locks).

Thin shell: equipment_core holds the rules (validation, codes, level table,
paths, tracked changes, the class and type taken from the model); this module checks
unit access, locks, issues codes, stores and writes the event history.

LOCK ORDER — one global order for every write in this module; each step is taken
only when the write needs it:

    (1) the node's own equipment row
    (2) the target parent equipment row
    (3) the unit row
    (4) the equipment model row (only when a write newly picks it)
    (5) the class row (the model's; its code is the prefix on create)
    (6) the serial_counters row

The type is no longer locked here: it comes from the model, whose type never changes
(S012 § 5.5); its name for the event comes from the plain re-read.

- Every lock is a single-row ``SELECT <decision columns> FROM <table> WHERE id = %s
  FOR UPDATE``, never taken through the join fragment (MariaDB has no FOR UPDATE OF,
  so a join would also lock ancestors and two opposite re-parents would deadlock).
- Every refusal about a row (scrapped, level rule, active, class prefix) is decided
  from the row its locking read returned.  Under REPEATABLE READ a locking read sees
  the latest committed row even after a lock wait; a plain read may show the
  snapshot from before the wait.  Plain reads (the fragment) serve only access
  checks and display values.
- Ancestors are never locked.  The scrap check locks the subtree top-down, the
  reverse of the order above: the one accepted deadlock (brief § 6 Locking).
- masters.py locks units, sites, manufacturers, models, classes, equipment types, people,
  memberships and person_units but never equipment, and takes manufacturer → model →
  class → type, the order here; this module never locks sites, manufacturers, types,
  people, memberships or person_units (it reads memberships and person_units plain, for
  the site checks, S011) and locks units/models/classes only after any equipment rows.
  So no lock cycle spans the two modules.  masters.py's own
  site-role writes lock person → their membership and person_units rows → units, and
  the membership insert then takes the site's row through its FK: unit → site, the
  order update_unit uses.
- Every write checks its key at the record's site (S011 § 5.4) inside the three choke
  points below (load_node_for_user, _load_target_node, _lock_target_unit), after their
  own refusals, so no write route can skip it.
- documents.py (S006, S008, S012, S017) takes exactly one owner lock per write, briefly: the
  node (1) through LOCK_EQUIPMENT and load_node_for_user, a model row (4) or a ticket row
  (7, below), never two; then it touches only equipment_documents rows, which nothing else
  locks.  So it adds no lock cycle.
- tickets.py (S017) raises a ticket under (1) the node raised on → (6) the serial counter
  (scope TK:YYYY-MM) → (7) the ticket row.  Ticket rows come last everywhere: nothing that
  holds one then takes an equipment, unit or counter lock.  The ticket insert takes shared
  locks through its foreign keys (machine, unit, person, failure mode), which gives two
  accepted deadlocks, as the scrap check's (S017 § 5.4): scrapping a machine (machine, then
  its parts) against a raise on one of its parts (the part, then the machine's FK lock); and
  a person's site-row edit (person, then units) against a raise naming that person (unit,
  then person).  InnoDB rolls one side back (1213).  The scrap path counts open tickets on
  the node and its parts while they are locked (_check_no_open_tickets), so a raise and a
  scrap of the same node serialise on (1).
"""

from datetime import datetime, timedelta, timezone

from flask import Blueprint, g, jsonify, request

from api_common import (
    DEFAULT_PER_PAGE, MAX_PAGE, MAX_PER_PAGE, UNIQUE_KEY_ERRORS, ApiError, actor, clean_body, enum_arg, int_arg,
    like_pattern,
)
import asset_list_core
from asset_list_core import build_asset_list
from auth_utils import permissions_at_site, require_perm, require_perm_at, user_unit_ids
from db_helpers import count, get_db, insert_row, next_counter, row_to_dict, rows_to_list, transaction, update_row
from equipment_core import (
    CRITICALITIES, LEVELS, SCRAPPED, STATUSES, check_parent, derive_from_model, effective_criticality,
    format_equipment_code, full_path, tracked_changes, validate_equipment,
)
from labels_core import MAX_LABELS_PER_REQUEST, TOO_MANY_LABELS, expand_selection, label_url, parse_code, qr_svg
from masters_core import model_label
from settings import label_base_url
from tickets_core import CLOSED

equipment_bp = Blueprint("equipment", __name__)

UNIQUE_KEY_ERRORS.update({
    "uq_equipment_code": (None, "Code collision — retry"),
})

IST = timezone(timedelta(hours=5, minutes=30))

# The root equipment's grade at every depth.  A CASE that picks the root row rather
# than a COALESCE over the levels: if an equipment's grade were ever NULL, a COALESCE
# would fall through to a component unit's grade and hide the error.
_ROOT_CRITICALITY = (
    "CASE WHEN gp.id IS NOT NULL THEN gp.criticality "
    "WHEN p.id IS NOT NULL THEN p.criticality ELSE e.criticality END"
)

# The one place a node's unit is resolved: a part's unit is its root equipment's,
# at most two steps up.  For plain reads only — never with FOR UPDATE.
NODE_JOINS = (
    " LEFT JOIN equipment p ON p.id = e.parent_id"
    " LEFT JOIN equipment gp ON gp.id = p.parent_id"
    " JOIN units u ON u.id = COALESCE(gp.unit_id, p.unit_id, e.unit_id)"
    " JOIN sites s ON s.id = u.site_id"
    " JOIN equipment_classes c ON c.id = e.class_id"
    " LEFT JOIN equipment_types t ON t.id = e.type_id"
    # Inner joins, as the class: every node has a model (S012, BR3-04)
    " JOIN equipment_models m ON m.id = e.model_id"
    " JOIN manufacturers mf ON mf.id = m.manufacturer_id"
)
_NODE_FROM = " FROM equipment e" + NODE_JOINS

_NODE_COLUMNS = (
    "SELECT e.id, e.code, e.level, e.parent_id, e.class_id, e.type_id, e.model_id, e.name,"
    " e.serial_no, e.year, e.criticality, e.status, e.notes, e.created_at, e.created_by, e.updated_at,"
    " e.updated_by, c.code AS class_code, t.name AS type_name,"
    " m.designation AS model_designation, mf.name AS manufacturer_name, u.id AS root_unit_id,"
    " s.id AS site_id, s.code AS site_code, u.code AS unit_code,"
    " p.code AS p_code, p.level AS p_level, p.name AS p_name,"
    " gp.id AS gp_id, gp.code AS gp_code, gp.level AS gp_level, gp.name AS gp_name,"
    f" {_ROOT_CRITICALITY} AS root_criticality"
)

# Direct children that are still in use
_PART_COUNT = (
    "(SELECT COUNT(*) FROM equipment ch WHERE ch.parent_id = e.id AND ch.status <> 'scrapped') AS part_count"
)

# Locking reads: each returns the columns its decisions need (BR3-01)
LOCK_EQUIPMENT = ("SELECT id, level, status, parent_id, unit_id, class_id, type_id, model_id FROM equipment "
                  "WHERE id = %s FOR UPDATE")
_LOCK_UNIT = "SELECT id, code, active, site_id FROM units WHERE id = %s FOR UPDATE"
_LOCK_MODEL = "SELECT id, class_id, type_id, designation, active FROM equipment_models WHERE id = %s FOR UPDATE"
_LOCK_CLASS = "SELECT id, code, active FROM equipment_classes WHERE id = %s FOR UPDATE"


# ---------------------------------------------------------------------------
# Reading and shaping nodes
# ---------------------------------------------------------------------------

def _read_node(cur, node_id):
    """Plain read of one node through the fragment; None when it does not exist."""
    cur.execute(f"{_NODE_COLUMNS}{_NODE_FROM} WHERE e.id = %s", (node_id,))
    return cur.fetchone()


SAVED_BUT_UNREADABLE = "Saved, but the record could not be read back — reload the page"


def _reread(cur, node_id, message="This record changed while saving — try again", field=None):
    """Plain read of a node this request has just locked or written; 409 when the read finds
    no row.  Inside a write, REPEATABLE READ answers plain reads from the snapshot taken at
    the transaction's first plain read.  A unit, class or parent committed by another
    request after that snapshot is invisible to it, so the fragment's joins find nothing:
    a race the user can retry, not a server error."""
    node = _read_node(cur, node_id)
    if node is None:
        raise ApiError(message, 409, field)
    return node


def node_path(node):
    codes = [c for c in (node["gp_code"], node["p_code"], node["code"]) if c]
    return full_path(node["site_code"], node["unit_code"], codes)


def _summary(node):
    """The list row.  unit_id and unit are the root equipment's, for parts too."""
    return {
        "id": node["id"],
        "code": node["code"],
        "level": node["level"],
        "name": node["name"],
        "class_id": node["class_id"],
        "class_code": node["class_code"],
        "type_id": node["type_id"],
        "type_name": node["type_name"],
        "model_id": node["model_id"],
        "model_designation": node["model_designation"],
        "manufacturer_name": node["manufacturer_name"],
        "model_label": model_label(node["manufacturer_name"], node["model_designation"]),
        "unit_id": node["root_unit_id"],
        "unit": f"{node['site_code']}.{node['unit_code']}",
        "full_path": node_path(node),
        "effective_criticality": effective_criticality(node["criticality"], node["root_criticality"]),
        "status": node["status"],
    }


def _ancestors(node):
    """Root first: the grandparent (if any), then the parent."""
    rows = []
    if node["gp_id"] is not None:
        rows.append({"id": node["gp_id"], "code": node["gp_code"], "level": node["gp_level"],
                     "name": node["gp_name"]})
    if node["parent_id"] is not None:
        rows.append({"id": node["parent_id"], "code": node["p_code"], "level": node["p_level"],
                     "name": node["p_name"]})
    return rows


def _child_rows(cur, where, params, root_grade):
    cur.execute(
        "SELECT ch.id, ch.parent_id, ch.code, ch.level, ch.name, ch.criticality, ch.status,"
        " c.code AS class_code FROM equipment ch JOIN equipment_classes c ON c.id = ch.class_id"
        f" WHERE {where} ORDER BY ch.code", params)
    return [{**row, "effective_criticality": effective_criticality(row["criticality"], root_grade)}
            for row in cur.fetchall()]


def _children(cur, node):
    """The subtree, two levels at most, scrapped nodes included."""
    root_grade = node["root_criticality"]
    children = _child_rows(cur, "ch.parent_id = %s", (node["id"],), root_grade)
    if not children:
        return []
    ids = [c["id"] for c in children]
    grandchildren = _child_rows(cur, f"ch.parent_id IN ({', '.join(['%s'] * len(ids))})", ids, root_grade)
    for child in children:
        child["children"] = [gc for gc in grandchildren if gc["parent_id"] == child["id"]]
    return children


def _detail(cur, node):
    out = _summary(node)
    plain = row_to_dict(node)
    for field in ("parent_id", "serial_no", "year", "criticality", "notes",
                  "created_at", "created_by", "updated_at", "updated_by"):
        out[field] = plain[field]
    out["root_criticality"] = node["root_criticality"]
    out["ancestors"] = _ancestors(node)
    out["children"] = _children(cur, node)
    cur.execute("SELECT id, event, old_value, new_value, created_at, created_by FROM equipment_events "
                "WHERE equipment_id = %s ORDER BY created_at DESC, id DESC", (node["id"],))
    out["events"] = rows_to_list(cur.fetchall())
    return out


# ---------------------------------------------------------------------------
# Unit access — only these helpers, the list, /my-units, the labels and documents.py's
# removed list touch accessible_unit_ids
# ---------------------------------------------------------------------------

def accessible_unit_ids(cur, key="equipment:read"):
    """The units where the user holds ``key`` (S011 § 5.3): None = every unit (admin, or a
    token role holding the key and equipment:read_all_units); otherwise a set of active unit
    ids — an empty set is no access at all, not an error.  Memberships are read through the
    request's connection, the one ``cur`` belongs to."""
    return user_unit_ids(key)


def _can_access(cur, unit_id):
    unit_ids = accessible_unit_ids(cur)
    return unit_ids is None or unit_id in unit_ids


def load_node_for_user(cur, node_id, for_update, key=None):
    """The node being read or written → ``(locked_row or None, node)``.  A missing node and
    one outside the user's units are the same 404, so nothing is revealed.  ``key`` (required
    for a write) is then checked at the node's site: 403 (S011 § 5.4)."""
    assert key is not None or not for_update, "a write must name the key it checks at the node's site"
    locked = None
    if for_update:
        cur.execute(LOCK_EQUIPMENT, (node_id,))   # (1)
        locked = cur.fetchone()
        if locked is None:
            raise ApiError("Not found", 404)
    node = _read_node(cur, node_id)
    if node is None or not _can_access(cur, node["root_unit_id"]):
        raise ApiError("Not found", 404)
    if key is not None:
        require_perm_at(key, node["site_id"])
    return locked, node


def _load_target_node(cur, node_id, child_level, key):
    """Lock the target parent of a create or re-parent (2), then refuse in this order:
    unknown 400 → outside the user's units 403 → scrapped 409 → wrong level 400 → ``key``
    not held at the parent's site 403."""
    cur.execute(LOCK_EQUIPMENT, (node_id,))
    locked = cur.fetchone()
    if locked is None:
        raise ApiError("Unknown parent", 400, "parent_id")
    # The locking read sees the parent; the plain read may not, when another request
    # committed it after this transaction's snapshot (see _reread).
    target = _reread(cur, node_id, "The parent changed while saving — try again", "parent_id")
    if not _can_access(cur, target["root_unit_id"]):
        raise ApiError("You have no access to the parent's unit", 403, "parent_id")
    if locked["status"] == SCRAPPED:
        raise ApiError("The parent is scrapped", 409, "parent_id")
    message = check_parent(child_level, locked["level"])
    if message:
        raise ApiError(message, 400, "parent_id")
    require_perm_at(key, target["site_id"], "parent_id")
    return locked


def _lock_target_unit(cur, unit_id, key):
    """Lock the unit equipment is created in or moved to (3).  A unit's existence and
    state are public (the masters list shows every unit), so inactive comes before access;
    ``key`` at the unit's site comes last (403)."""
    cur.execute(_LOCK_UNIT, (unit_id,))
    unit = cur.fetchone()
    if unit is None:
        raise ApiError("Unknown unit", 400, "unit_id")
    if not unit["active"]:
        raise ApiError("The unit is inactive", 409, "unit_id")
    if not _can_access(cur, unit_id):
        raise ApiError("You have no access to this unit", 403, "unit_id")
    require_perm_at(key, unit["site_id"], "unit_id")
    return unit


def _lock_model(cur, model_id, stored_model_id):
    """Lock the model a create or update newly picks (4) and take the class and type from it
    (S012 § 5.3): unknown 400, inactive 409.  Returns ``(model, class_id, type_id)``."""
    cur.execute(_LOCK_MODEL, (model_id,))
    model = cur.fetchone()
    if model is None:
        raise ApiError("Unknown model", 400, "model_id")
    class_id, type_id, message = derive_from_model(stored_model_id, model)
    if message:
        raise ApiError(message, 409, "model_id")
    return model, class_id, type_id


def _lock_class(cur, class_id):
    """Lock the class of a newly picked model (5); its code is the prefix on create, read
    here.  Through the API an active model always has an active class (masters.py refuses
    to deactivate a class with active models), so "inactive" is defence in depth."""
    cur.execute(_LOCK_CLASS, (class_id,))
    equipment_class = cur.fetchone()
    if equipment_class is None:
        raise ApiError("Unknown class", 400, "class_id")
    if not equipment_class["active"]:
        raise ApiError("The class is inactive", 409, "class_id")
    return equipment_class


def _pick_model(cur, clean, stored_model_id):
    """A write that picks a model: lock it (4) and its class (5), and put the class and the
    type into ``clean`` — both always, so a model without a type writes type_id NULL.
    Returns ``(model, class)`` for the event text."""
    model, class_id, type_id = _lock_model(cur, clean["model_id"], stored_model_id)
    equipment_class = _lock_class(cur, class_id)
    clean["class_id"], clean["type_id"] = class_id, type_id
    return model, equipment_class


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

def _next_code(cur, prefix):
    """Bump the per-prefix counter (6) in the caller's transaction: a failed create rolls the
    bump back, so failures leave no gaps."""
    return format_equipment_code(prefix, next_counter(cur, f"EQ:{prefix}"))


def _write_events(cur, equipment_id, changes):
    for event, old, new in changes:
        cur.execute("INSERT INTO equipment_events (equipment_id, event, old_value, new_value, created_by) "
                    "VALUES (%s, %s, %s, %s, %s)", (equipment_id, event, old, new, actor()))


def _check_parts_scrapped(cur, node_id):
    """Scrapping needs every child and grandchild scrapped — decided from locking reads, so
    a part cannot be revived or slipped in while we decide.  Returns the locked parts' ids."""
    cur.execute("SELECT id, status FROM equipment WHERE parent_id = %s FOR UPDATE", (node_id,))
    parts = cur.fetchall()
    if parts:
        ids = [p["id"] for p in parts]
        cur.execute(f"SELECT id, status FROM equipment WHERE parent_id IN ({', '.join(['%s'] * len(ids))}) "
                    "FOR UPDATE", ids)
        parts = [*parts, *cur.fetchall()]
    if any(p["status"] != SCRAPPED for p in parts):
        raise ApiError("Scrap or move its parts first", 409, "status")
    return [p["id"] for p in parts]


def _check_no_open_tickets(cur, node_ids):
    """Scrapping waits until the tickets on the node and its parts are closed (S017 § 5.8,
    user decision 6): a scrapped record is read-only, so an open ticket on it could never be
    closed.  Counted while the node and its parts are locked; a raise locks its node first,
    so whichever gets the node first wins (S017 § 5.8).  A plain count is enough: this
    transaction's snapshot is taken by load_node_for_user's plain read, after the node's lock
    was granted, so a raise committed before that grant is seen."""
    placeholders = ", ".join(["%s"] * len(node_ids))
    sql = (f"SELECT COUNT(*) AS n FROM tickets WHERE state <> %s"
           f" AND (equipment_id IN ({placeholders}) OR component_id IN ({placeholders}))")
    if count(cur, sql, [CLOSED, *node_ids, *node_ids]):
        raise ApiError("Close its tickets first", 409, "status")


def _tracked_state(node):
    return {**node, "full_path": node_path(node),
            "model_label": model_label(node["manufacturer_name"], node["model_designation"])}


def _written_state(cur, node_id, unit=None, equipment_class=None, equipment_model=None):
    """The node as this write left it, for the event text.  The plain re-read may show a
    unit or class code, or a model designation, from before a change committed while this
    write waited for its lock; the locking reads of the target unit, class and model (when
    this write took them) have the current values, so those win.  The manufacturer name and
    the type name come from the re-read: a rename committed during the wait may show the
    old name in the event, a display-only residual (as S002 accepted for site codes)."""
    node = _reread(cur, node_id)
    if unit is not None:
        node = {**node, "unit_code": unit["code"]}
    if equipment_class is not None:
        node = {**node, "class_code": equipment_class["code"]}
    if equipment_model is not None:
        node = {**node, "model_designation": equipment_model["designation"]}
    return _tracked_state(node)


def _this_year():
    return datetime.now(IST).year


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

def _list_filters():
    """The conditions and parameters of the filters the list and the printed asset list share
    (site, unit, class, type, status, criticality, scrapped), read from the request.  One
    place decides what a filter means, so the print can never disagree with the list."""
    conditions, params = [], []
    for name, column in (("site_id", "u.site_id"), ("unit_id", "u.id"), ("class_id", "e.class_id"),
                         ("type_id", "e.type_id")):
        value = int_arg(name, None, minimum=1)
        if value is not None:
            conditions.append(f"{column} = %s")
            params.append(value)
    status = enum_arg("status", STATUSES)
    if status:
        conditions.append("e.status = %s")
        params.append(status)
    criticality = enum_arg("criticality", CRITICALITIES)
    if criticality:
        conditions.append(f"COALESCE(e.criticality, {_ROOT_CRITICALITY}) = %s")
        params.append(criticality)
    if request.args.get("include_scrapped") != "1":
        conditions.append("e.status <> 'scrapped'")
    return conditions, params


@equipment_bp.route("/", strict_slashes=False)
@require_perm("equipment:read")
def list_equipment():
    page = int_arg("page", 1, minimum=1, maximum=MAX_PAGE)
    per_page = int_arg("per_page", DEFAULT_PER_PAGE, minimum=1, maximum=MAX_PER_PAGE)
    conditions, params = _list_filters()
    level = enum_arg("level", (*LEVELS, "all")) or "equipment"
    if level != "all":
        conditions.append("e.level = %s")
        params.append(level)
    q = (request.args.get("q") or "").strip()
    if q:
        # The type name too, so "closed" finds closed-execution pumps whatever their names say;
        # and the model label (manufacturer and designation, S012), so "GA37", "Atlas" and
        # "Atlas Copco GA37" all find it
        conditions.append("(e.code LIKE %s OR e.name LIKE %s OR e.notes LIKE %s OR t.name LIKE %s"
                          " OR CONCAT(mf.name, ' ', m.designation) LIKE %s)")
        params.extend([like_pattern(q)] * 5)

    empty = {"items": [], "total": 0, "page": page, "per_page": per_page}
    with get_db().cursor() as cur:
        unit_ids = accessible_unit_ids(cur)
        if unit_ids is not None:
            if not unit_ids:
                return jsonify(empty)
            conditions.append(f"u.id IN ({', '.join(['%s'] * len(unit_ids))})")
            params.extend(sorted(unit_ids))
        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        total = count(cur, f"SELECT COUNT(*) AS n{_NODE_FROM}{where}", params)
        cur.execute(f"{_NODE_COLUMNS}, {_PART_COUNT}{_NODE_FROM}{where} ORDER BY e.code LIMIT %s OFFSET %s",
                    [*params, per_page, (page - 1) * per_page])
        items = [{**_summary(row), "part_count": row["part_count"]} for row in cur.fetchall()]
    return jsonify({"items": items, "total": total, "page": page, "per_page": per_page})


# ---------------------------------------------------------------------------
# One node, create, change
# ---------------------------------------------------------------------------

@equipment_bp.route("/my-units")
@require_perm("equipment:read")
def my_units():
    """The units the screens may offer this user.  all_units true = every unit (unit_ids is
    then empty); otherwise the user's active units.  edit_unit_ids: where equipment:edit is
    held (null = every unit), for the write pickers.  Lets the pickers avoid choices the
    write endpoints would refuse with 403."""
    with get_db().cursor() as cur:
        unit_ids = accessible_unit_ids(cur)
        edit_ids = accessible_unit_ids(cur, "equipment:edit")
    return jsonify({
        "all_units": unit_ids is None,
        "unit_ids": [] if unit_ids is None else sorted(unit_ids),
        "edit_unit_ids": None if edit_ids is None else sorted(edit_ids),
    })


@equipment_bp.route("/<int:node_id>")
@require_perm("equipment:read")
def get_equipment(node_id):
    with get_db().cursor() as cur:
        _, node = load_node_for_user(cur, node_id, for_update=False)
        # The user's keys at this node's site, so the screen's buttons follow the site (S011)
        return jsonify({**_detail(cur, node), "permissions": permissions_at_site(node["site_id"])})


# ---------------------------------------------------------------------------
# QR labels (S014) — read-only: the lookup behind /e/<code>, and the label sheets
# ---------------------------------------------------------------------------

@equipment_bp.route("/by-code/<code>")
@require_perm("equipment:read")
def get_equipment_by_code(code):
    """The id behind a label's code.  Not a code, unknown, or outside the user's units: the
    same 404, so a label reveals nothing about a unit the user may not see."""
    code = parse_code(code)
    if code is None:
        raise ApiError("Not found", 404)
    with get_db().cursor() as cur:
        cur.execute("SELECT id FROM equipment WHERE code = %s", (code,))
        row = cur.fetchone()
        if row is None:
            raise ApiError("Not found", 404)
        _, node = load_node_for_user(cur, row["id"], for_update=False)
    return jsonify({"id": node["id"]})


def _validate_labels_request(body, _creating):
    """ids: a non-empty list of distinct positive integers (not booleans), at most
    MAX_LABELS_PER_REQUEST; with_parts: a boolean, default false."""
    ids, with_parts = body.get("ids"), body.get("with_parts", False)
    if (not isinstance(ids, list) or not ids
            or any(isinstance(i, bool) or not isinstance(i, int) or i < 1 for i in ids)
            or len(set(ids)) != len(ids)):
        return {}, [{"field": "ids", "message": "Choose the equipment to print (a list of distinct ids)"}]
    if len(ids) > MAX_LABELS_PER_REQUEST:
        return {}, [{"field": "ids", "message": TOO_MANY_LABELS}]
    if not isinstance(with_parts, bool):
        return {}, [{"field": "with_parts", "message": "Must be true or false"}]
    return {"ids": ids, "with_parts": with_parts}, []


_LABELS_NOT_FOUND = "Some of the selected equipment was not found or is not at your units"


@equipment_bp.route("/labels", methods=["POST"])
@require_perm("equipment:read")
def equipment_labels():
    """The labels for the selected nodes (and, with_parts, their parts), in print order.
    One query over the three levels; any selected node missing or outside the user's units
    → 404 for the whole request, naming none (as the equipment page answers)."""
    clean = clean_body(_validate_labels_request, creating=False)
    ids, with_parts = clean["ids"], clean["with_parts"]
    in_ids = f"({', '.join(['%s'] * len(ids))})"
    with get_db().cursor() as cur:
        unit_ids = accessible_unit_ids(cur)
        if unit_ids is not None and not unit_ids:
            raise ApiError(_LABELS_NOT_FOUND, 404)   # no units: an empty IN () would be an SQL error
        if with_parts:
            # The tree is at most three levels: equipment, component-unit, component
            where, params = f"(e.id IN {in_ids} OR e.parent_id IN {in_ids} OR p.parent_id IN {in_ids})", ids * 3
        else:
            where, params = f"e.id IN {in_ids}", list(ids)
        if unit_ids is not None:
            where += f" AND u.id IN ({', '.join(['%s'] * len(unit_ids))})"
            params += sorted(unit_ids)
        cur.execute(f"SELECT e.id, e.parent_id, e.code, e.name, e.status, s.code AS site_code{_NODE_FROM}"
                    f" WHERE {where}", params)
        rows = cur.fetchall()
        base_url = label_base_url(cur)
    found = {row["id"] for row in rows}
    if any(node_id not in found for node_id in ids):
        raise ApiError(_LABELS_NOT_FOUND, 404)
    ordered, message = expand_selection(ids, rows, with_parts)
    if message:
        raise ApiError(message, 400, "ids")
    labels = []
    for row in ordered:
        url = label_url(base_url, row["code"])
        labels.append({"id": row["id"], "code": row["code"], "name": row["name"], "site_code": row["site_code"],
                       "url": url, "qr_svg": qr_svg(url)})
    return jsonify({"labels": labels})


# ---------------------------------------------------------------------------
# Printable asset list (S015) — read-only
# ---------------------------------------------------------------------------



def _asset_list_row(node):
    """The printed row: the list's summary plus what the sheet needs to tell machines apart."""
    return {**_summary(node), "parent_id": node["parent_id"], "serial_no": node["serial_no"], "year": node["year"]}


@equipment_bp.route("/asset-list")
@require_perm("equipment:read")
def asset_list():
    """The machines the filters choose, grouped by unit, with their parts when with_parts=1.
    Filters choose machines; parts come only with their machine, whatever their own class
    (S015 § 4).  Unit access is applied as in the list."""
    conditions, params = _list_filters()
    with_parts = request.args.get("with_parts") == "1"
    conditions.append("e.level = 'equipment'")
    printed = {"printed_at": datetime.now(IST).isoformat(timespec="seconds"),
               "printed_by": g.user.get("name") or actor()}
    with get_db().cursor() as cur:
        unit_ids = accessible_unit_ids(cur)
        if unit_ids is not None:
            if not unit_ids:
                return jsonify({"units": [], "total_rows": 0, **printed})   # an empty IN () is an SQL error
            conditions.append(f"u.id IN ({', '.join(['%s'] * len(unit_ids))})")
            params.extend(sorted(unit_ids))
        # The cap is read through the module so a test that patches it reaches both checks
        cap = asset_list_core.MAX_ASSET_LIST_ROWS
        cur.execute(f"{_NODE_COLUMNS}, s.name AS site_name, u.name AS unit_name{_NODE_FROM}"
                    f" WHERE {' AND '.join(conditions)} ORDER BY e.code LIMIT %s", [*params, cap + 1])
        machine_nodes = cur.fetchall()
        if len(machine_nodes) > cap:
            raise ApiError(asset_list_core.TOO_MANY_ROWS, 400)
        if not machine_nodes:
            return jsonify({"units": [], "total_rows": 0, **printed})
        machines = [{**_asset_list_row(n), "site_code": n["site_code"], "site_name": n["site_name"],
                     "unit_code": n["unit_code"], "unit_name": n["unit_name"]} for n in machine_nodes]
        parts = []
        if with_parts:
            in_ids = f"({', '.join(['%s'] * len(machines))})"
            ids = [m["id"] for m in machines]
            # The tree is at most three levels: component units (parent = machine) and
            # components (grandparent = machine)
            cur.execute(f"{_NODE_COLUMNS}{_NODE_FROM} WHERE e.parent_id IN {in_ids} OR p.parent_id IN {in_ids}",
                        ids * 2)
            parts = [_asset_list_row(n) for n in cur.fetchall()]
    result, message = build_asset_list(machines, parts, request.args.get("include_scrapped") == "1")
    if message:
        raise ApiError(message, 400)
    return jsonify({**result, **printed})


@equipment_bp.route("/", methods=["POST"], strict_slashes=False)
@require_perm("equipment:edit")
def create_equipment():
    this_year = _this_year()
    clean = clean_body(lambda body, creating: validate_equipment(body, creating, this_year), creating=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        unit = None
        if clean["level"] == "equipment":
            unit = _lock_target_unit(cur, clean["unit_id"], "equipment:edit")              # (3)
        else:
            _load_target_node(cur, clean["parent_id"], clean["level"], "equipment:edit")   # (2)
        equipment_model, equipment_class = _pick_model(cur, clean, None)   # (4), (5)
        code = _next_code(cur, equipment_class["code"])                  # (6)
        node_id = insert_row(cur, "equipment", {"code": code, **clean}, actor())
        created = _written_state(cur, node_id, unit, equipment_class, equipment_model)
        _write_events(cur, node_id, [("created", None, created["full_path"])])
    with conn.cursor() as cur:
        # Committed already: a retry would duplicate the record, so the message says reload
        return jsonify(_detail(cur, _reread(cur, node_id, SAVED_BUT_UNREADABLE))), 201


@equipment_bp.route("/<int:node_id>", methods=["PUT"])
@require_perm("equipment:edit")
def update_equipment(node_id):
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        # (1); 404; 403 unless equipment:edit at the node's current site (a move or
        # re-parent is checked at the target's site too, below)
        locked, node = load_node_for_user(cur, node_id, for_update=True, key="equipment:edit")
        if locked["status"] == SCRAPPED:
            raise ApiError("This record is scrapped and cannot be changed", 409)
        this_year = _this_year()
        stored = {"code": node["code"], "level": locked["level"]}
        clean = clean_body(lambda body, creating: validate_equipment(body, creating, this_year, stored),
                           creating=False)
        # Sending back the current parent, unit or model is not a move or a model change
        for field in ("parent_id", "unit_id", "model_id"):
            if field in clean and clean[field] == locked[field]:
                del clean[field]
        unit = equipment_model = equipment_class = None
        if "parent_id" in clean:
            _load_target_node(cur, clean["parent_id"], locked["level"], "equipment:edit")   # (2)
        if "unit_id" in clean:
            unit = _lock_target_unit(cur, clean["unit_id"], "equipment:edit")               # (3)
        if "model_id" in clean:
            # Another class is a reclassification: the code is kept (S002)
            equipment_model, equipment_class = _pick_model(cur, clean, locked["model_id"])   # (4), (5)
        if clean.get("status") == SCRAPPED:
            _check_no_open_tickets(cur, [node_id, *_check_parts_scrapped(cur, node_id)])
        before = _tracked_state(node)
        update_row(cur, "equipment", node_id, clean, actor())
        after = _written_state(cur, node_id, unit, equipment_class, equipment_model)
        _write_events(cur, node_id, tracked_changes(before, after))
    with conn.cursor() as cur:
        # Committed already: "try again" would mislead, so the message says reload
        return jsonify(_detail(cur, _reread(cur, node_id, SAVED_BUT_UNREADABLE)))
