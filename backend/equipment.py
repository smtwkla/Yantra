"""Equipment register — the equipment tree API
(docs/steps/S002-equipment-register/1-brief.md; types and notes: S004).

Thin shell: equipment_core holds the rules (validation, codes, level table,
paths, tracked changes); this module checks unit access, locks, issues codes,
stores and writes the event history.

LOCK ORDER — one global order for every write in this module; each step is taken
only when the write needs it:

    (1) the node's own equipment row
    (2) the target parent equipment row
    (3) the unit row
    (4) the class row
    (5) the equipment type row
    (6) the serial_counters row

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
- masters.py locks units, sites, classes, equipment types and user_units but never
  equipment, and takes a class before a type, as here; this module never locks sites
  or user_units and locks units/classes/types only after any equipment rows.  So no
  lock cycle spans the two modules.
- documents.py (S006) takes lock (1) only, briefly, through LOCK_EQUIPMENT and
  load_node_for_user, and then touches equipment_documents rows, which nothing else
  locks; so it adds no lock cycle.
"""

from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request

from api_common import UNIQUE_KEY_ERRORS, ApiError, actor, clean_body
from auth_utils import has_perm, require_perm
from db_helpers import count, get_db, insert_row, row_to_dict, rows_to_list, transaction, update_row
from equipment_core import (
    CRITICALITIES, LEVELS, SCRAPPED, STATUSES, check_parent, check_type_class, effective_criticality,
    format_equipment_code, full_path, tracked_changes, validate_equipment,
)

equipment_bp = Blueprint("equipment", __name__)

UNIQUE_KEY_ERRORS.update({
    "uq_equipment_code": (None, "Code collision — retry"),
})

IST = timezone(timedelta(hours=5, minutes=30))

DEFAULT_PER_PAGE = 50
MAX_PER_PAGE = 200
# Far past any real register (MAX_PAGE x MAX_PER_PAGE = 20 million rows), and it keeps
# the OFFSET a number MariaDB accepts: an unbounded page overflows it (error 1064).
MAX_PAGE = 100_000

# The root equipment's grade at every depth.  A CASE that picks the root row rather
# than a COALESCE over the levels: if an equipment's grade were ever NULL, a COALESCE
# would fall through to a component unit's grade and hide the error.
_ROOT_CRITICALITY = (
    "CASE WHEN gp.id IS NOT NULL THEN gp.criticality "
    "WHEN p.id IS NOT NULL THEN p.criticality ELSE e.criticality END"
)

# The one place a node's unit is resolved: a part's unit is its root equipment's,
# at most two steps up.  For plain reads only — never with FOR UPDATE.
_NODE_FROM = (
    " FROM equipment e"
    " LEFT JOIN equipment p ON p.id = e.parent_id"
    " LEFT JOIN equipment gp ON gp.id = p.parent_id"
    " JOIN units u ON u.id = COALESCE(gp.unit_id, p.unit_id, e.unit_id)"
    " JOIN sites s ON s.id = u.site_id"
    " JOIN equipment_classes c ON c.id = e.class_id"
    " LEFT JOIN equipment_types t ON t.id = e.type_id"
)

_NODE_COLUMNS = (
    "SELECT e.id, e.code, e.level, e.parent_id, e.class_id, e.type_id, e.name, e.make, e.model,"
    " e.serial_no, e.year, e.criticality, e.status, e.notes, e.created_at, e.created_by, e.updated_at,"
    " e.updated_by, c.code AS class_code, t.name AS type_name, u.id AS root_unit_id, s.code AS site_code, u.code AS unit_code,"
    " p.code AS p_code, p.level AS p_level, p.name AS p_name,"
    " gp.id AS gp_id, gp.code AS gp_code, gp.level AS gp_level, gp.name AS gp_name,"
    f" {_ROOT_CRITICALITY} AS root_criticality"
)

# Direct children that are still in use
_PART_COUNT = (
    "(SELECT COUNT(*) FROM equipment ch WHERE ch.parent_id = e.id AND ch.status <> 'scrapped') AS part_count"
)

# Locking reads: each returns the columns its decisions need (BR3-01)
LOCK_EQUIPMENT = ("SELECT id, level, status, parent_id, unit_id, class_id, type_id FROM equipment "
                  "WHERE id = %s FOR UPDATE")
_LOCK_UNIT = "SELECT id, code, active FROM units WHERE id = %s FOR UPDATE"
_LOCK_CLASS = "SELECT id, code, active FROM equipment_classes WHERE id = %s FOR UPDATE"
_LOCK_TYPE = "SELECT id, class_id, name, active FROM equipment_types WHERE id = %s FOR UPDATE"


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


def _path(node):
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
        "unit_id": node["root_unit_id"],
        "unit": f"{node['site_code']}.{node['unit_code']}",
        "full_path": _path(node),
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
    for field in ("parent_id", "make", "model", "serial_no", "year", "criticality", "notes",
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
# Unit access — only these helpers, the list and /my-units touch _accessible_unit_ids
# ---------------------------------------------------------------------------

def _accessible_unit_ids(cur):
    """None = every unit (equipment:read_all_units; admin bypasses has_perm).  Otherwise the
    user's active units — an empty set is no access at all, not an error."""
    if has_perm("equipment:read_all_units"):
        return None
    cur.execute("SELECT uu.unit_id FROM user_units uu JOIN units u ON u.id = uu.unit_id "
                "WHERE uu.username = %s AND u.active = 1", (actor().lower(),))
    return {row["unit_id"] for row in cur.fetchall()}


def _can_access(cur, unit_id):
    unit_ids = _accessible_unit_ids(cur)
    return unit_ids is None or unit_id in unit_ids


def load_node_for_user(cur, node_id, for_update):
    """The node being read or written → ``(locked_row or None, node)``.  A missing node and
    one outside the user's units are the same 404, so nothing is revealed."""
    locked = None
    if for_update:
        cur.execute(LOCK_EQUIPMENT, (node_id,))   # (1)
        locked = cur.fetchone()
        if locked is None:
            raise ApiError("Not found", 404)
    node = _read_node(cur, node_id)
    if node is None or not _can_access(cur, node["root_unit_id"]):
        raise ApiError("Not found", 404)
    return locked, node


def _load_target_node(cur, node_id, child_level):
    """Lock the target parent of a create or re-parent (2), then refuse in this order:
    unknown 400 → outside the user's units 403 → scrapped 409 → wrong level 400."""
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
    return locked


def _lock_target_unit(cur, unit_id):
    """Lock the unit equipment is created in or moved to (3).  A unit's existence and
    state are public (the masters list shows every unit), so inactive comes before access."""
    cur.execute(_LOCK_UNIT, (unit_id,))
    unit = cur.fetchone()
    if unit is None:
        raise ApiError("Unknown unit", 400, "unit_id")
    if not unit["active"]:
        raise ApiError("The unit is inactive", 409, "unit_id")
    if not _can_access(cur, unit_id):
        raise ApiError("You have no access to this unit", 403, "unit_id")
    return unit


def _lock_class(cur, class_id):
    """Lock the class of a create or reclassify (4); its code is the prefix, read here."""
    cur.execute(_LOCK_CLASS, (class_id,))
    equipment_class = cur.fetchone()
    if equipment_class is None:
        raise ApiError("Unknown class", 400, "class_id")
    if not equipment_class["active"]:
        raise ApiError("The class is inactive", 409, "class_id")
    return equipment_class


def _lock_type(cur, type_id, node_class_id, newly_chosen):
    """Lock the type a write gives the node (5); every decision comes from this row.  The
    active check applies only when this write chooses the type; a type kept from before is
    checked for its class only (and keeping a type without a class change takes no lock at all)."""
    cur.execute(_LOCK_TYPE, (type_id,))
    equipment_type = cur.fetchone()
    if equipment_type is None:
        raise ApiError("Unknown type", 400, "type_id")
    message = check_type_class(equipment_type["class_id"], node_class_id)
    if message:
        raise ApiError(message, 400, "type_id")
    if newly_chosen and not equipment_type["active"]:
        raise ApiError("The type is inactive", 409, "type_id")
    return equipment_type


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

def _next_code(cur, prefix):
    """Bump the per-prefix counter (6) and read it back on the same connection, inside the
    caller's transaction: a failed create rolls the bump back, so failures leave no gaps."""
    scope = f"EQ:{prefix}"
    cur.execute("INSERT INTO serial_counters (scope, last_value) VALUES (%s, 1) "
                "ON DUPLICATE KEY UPDATE last_value = last_value + 1", (scope,))
    cur.execute("SELECT last_value FROM serial_counters WHERE scope = %s", (scope,))
    return format_equipment_code(prefix, cur.fetchone()["last_value"])


def _check_type_on_update(cur, locked, clean, sent_type):
    """The type a PUT leaves the node with must belong to its class, and a class change
    needs a type decision: the type is never cleared silently (S004 § 5.2).  Decided from
    the locked node and type rows; returns the locked type when one was taken, else None."""
    class_changes = "class_id" in clean
    if class_changes and locked["type_id"] is not None and not sent_type:
        raise ApiError("Pick a type of the new class, or none", 400, "type_id")
    resulting_type = clean.get("type_id", locked["type_id"])
    if resulting_type is None or not ("type_id" in clean or class_changes):
        return None
    new_class = clean.get("class_id", locked["class_id"])
    return _lock_type(cur, resulting_type, new_class, newly_chosen="type_id" in clean)


def _write_events(cur, equipment_id, changes):
    for event, old, new in changes:
        cur.execute("INSERT INTO equipment_events (equipment_id, event, old_value, new_value, created_by) "
                    "VALUES (%s, %s, %s, %s, %s)", (equipment_id, event, old, new, actor()))


def _check_parts_scrapped(cur, node_id):
    """Scrapping needs every child and grandchild scrapped — decided from locking reads, so
    a part cannot be revived or slipped in while we decide."""
    cur.execute("SELECT id, status FROM equipment WHERE parent_id = %s FOR UPDATE", (node_id,))
    parts = cur.fetchall()
    if parts:
        ids = [p["id"] for p in parts]
        cur.execute(f"SELECT id, status FROM equipment WHERE parent_id IN ({', '.join(['%s'] * len(ids))}) "
                    "FOR UPDATE", ids)
        parts = [*parts, *cur.fetchall()]
    if any(p["status"] != SCRAPPED for p in parts):
        raise ApiError("Scrap or move its parts first", 409, "status")


def _tracked_state(node):
    return {**node, "full_path": _path(node)}


def _written_state(cur, node_id, unit=None, equipment_class=None, equipment_type=None):
    """The node as this write left it, for the event text.  The plain re-read may show a
    unit or class code, or a type name, from before a change committed while this write
    waited for its lock (or miss a type created since: the type join is a LEFT JOIN); the
    locking reads of the target unit, class and type (when this write took them) have the
    current values, so those win."""
    node = _reread(cur, node_id)
    if unit is not None:
        node = {**node, "unit_code": unit["code"]}
    if equipment_class is not None:
        node = {**node, "class_code": equipment_class["code"]}
    if equipment_type is not None:
        node = {**node, "type_name": equipment_type["name"]}
    return _tracked_state(node)


def _this_year():
    return datetime.now(IST).year


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

def _int_arg(name, default, minimum, maximum=None):
    raw = request.args.get(name)
    if raw is None:
        return default
    # isascii: str.isdigit() also accepts digits such as '²' that int() rejects
    if not (raw.isascii() and raw.isdigit()) or int(raw) < minimum or (maximum is not None and int(raw) > maximum):
        bounds = f"between {minimum} and {maximum}" if maximum is not None else f"at least {minimum}"
        raise ApiError(f"{name} must be a whole number {bounds}", 400, name)
    return int(raw)


def _enum_arg(name, allowed):
    raw = request.args.get(name)
    if raw is not None and raw not in allowed:
        raise ApiError(f"{name} must be one of: {', '.join(allowed)}", 400, name)
    return raw


def _like_pattern(text):
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


@equipment_bp.route("/", strict_slashes=False)
@require_perm("equipment:read")
def list_equipment():
    page = _int_arg("page", 1, minimum=1, maximum=MAX_PAGE)
    per_page = _int_arg("per_page", DEFAULT_PER_PAGE, minimum=1, maximum=MAX_PER_PAGE)
    conditions, params = [], []
    for name, column in (("site_id", "u.site_id"), ("unit_id", "u.id"), ("class_id", "e.class_id"),
                         ("type_id", "e.type_id")):
        value = _int_arg(name, None, minimum=1)
        if value is not None:
            conditions.append(f"{column} = %s")
            params.append(value)
    status = _enum_arg("status", STATUSES)
    if status:
        conditions.append("e.status = %s")
        params.append(status)
    criticality = _enum_arg("criticality", CRITICALITIES)
    if criticality:
        conditions.append(f"COALESCE(e.criticality, {_ROOT_CRITICALITY}) = %s")
        params.append(criticality)
    level = _enum_arg("level", (*LEVELS, "all")) or "equipment"
    if level != "all":
        conditions.append("e.level = %s")
        params.append(level)
    q = (request.args.get("q") or "").strip()
    if q:
        # The type name too, so "closed" finds closed-execution pumps whatever their names say
        conditions.append("(e.code LIKE %s OR e.name LIKE %s OR e.notes LIKE %s OR t.name LIKE %s)")
        params.extend([_like_pattern(q)] * 4)
    if request.args.get("include_scrapped") != "1":
        conditions.append("e.status <> 'scrapped'")

    empty = {"items": [], "total": 0, "page": page, "per_page": per_page}
    with get_db().cursor() as cur:
        unit_ids = _accessible_unit_ids(cur)
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
    then empty); otherwise the user's active units.  Lets the pickers avoid choices the
    write endpoints would refuse with 403."""
    with get_db().cursor() as cur:
        unit_ids = _accessible_unit_ids(cur)
    return jsonify({"all_units": unit_ids is None, "unit_ids": [] if unit_ids is None else sorted(unit_ids)})


@equipment_bp.route("/<int:node_id>")
@require_perm("equipment:read")
def get_equipment(node_id):
    with get_db().cursor() as cur:
        _, node = load_node_for_user(cur, node_id, for_update=False)
        return jsonify(_detail(cur, node))


@equipment_bp.route("/", methods=["POST"], strict_slashes=False)
@require_perm("equipment:edit")
def create_equipment():
    this_year = _this_year()
    clean = clean_body(lambda body, creating: validate_equipment(body, creating, this_year), creating=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        unit = None
        if clean["level"] == "equipment":
            unit = _lock_target_unit(cur, clean["unit_id"])              # (3)
        else:
            _load_target_node(cur, clean["parent_id"], clean["level"])   # (2)
        equipment_class = _lock_class(cur, clean["class_id"])            # (4)
        equipment_type = None
        if "type_id" in clean:   # a null type_id was dropped by the validator
            equipment_type = _lock_type(cur, clean["type_id"], clean["class_id"], newly_chosen=True)  # (5)
        code = _next_code(cur, equipment_class["code"])                  # (6)
        node_id = insert_row(cur, "equipment", {"code": code, **clean}, actor())
        created = _written_state(cur, node_id, unit, equipment_class, equipment_type)
        _write_events(cur, node_id, [("created", None, created["full_path"])])
    with conn.cursor() as cur:
        # Committed already: a retry would duplicate the record, so the message says reload
        return jsonify(_detail(cur, _reread(cur, node_id, SAVED_BUT_UNREADABLE))), 201


@equipment_bp.route("/<int:node_id>", methods=["PUT"])
@require_perm("equipment:edit")
def update_equipment(node_id):
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        locked, node = load_node_for_user(cur, node_id, for_update=True)   # (1); 404
        if locked["status"] == SCRAPPED:
            raise ApiError("This record is scrapped and cannot be changed", 409)
        this_year = _this_year()
        stored = {"code": node["code"], "level": locked["level"]}
        clean = clean_body(lambda body, creating: validate_equipment(body, creating, this_year, stored),
                           creating=False)
        sent_type = "type_id" in clean   # as sent, before unchanged fields are dropped
        # Sending back the current parent, unit, class or type is not a move or a reclassification
        for field in ("parent_id", "unit_id", "class_id", "type_id"):
            if field in clean and clean[field] == locked[field]:
                del clean[field]
        unit = equipment_class = None
        if "parent_id" in clean:
            _load_target_node(cur, clean["parent_id"], locked["level"])   # (2)
        if "unit_id" in clean:
            unit = _lock_target_unit(cur, clean["unit_id"])               # (3)
        if "class_id" in clean:
            equipment_class = _lock_class(cur, clean["class_id"])         # (4)
        equipment_type = _check_type_on_update(cur, locked, clean, sent_type)   # (5)
        if clean.get("status") == SCRAPPED:
            _check_parts_scrapped(cur, node_id)
        before = _tracked_state(node)
        update_row(cur, "equipment", node_id, clean, actor())
        after = _written_state(cur, node_id, unit, equipment_class, equipment_type)
        _write_events(cur, node_id, tracked_changes(before, after))
    with conn.cursor() as cur:
        # Committed already: "try again" would mislead, so the message says reload
        return jsonify(_detail(cur, _reread(cur, node_id, SAVED_BUT_UNREADABLE)))
