"""One-point lessons — the API (docs/steps/S075-one-point-lessons/1-brief.md; R05.6, the first half;
the screens are S077).  A lesson is one title, one short text and a few photos about one point,
written on a machine (any node of the register) and, when ticked, shown on every machine of its
class (TPM one-point lesson and yokoten).  It is the first kind of the Procedures master (Plan
§ 4.3a).  This module writes and reads lessons, links one to the countermeasure of kind Lesson it
was written for (procedures.action_id; the countermeasure is never written, D8), and gives the
documents store its fifth owner: read_procedure, read_procedure_for_change and
lock_procedure_for_change, imported by documents.py (this module never imports documents.py).

Thin shell: procedures_core holds the rules (the fields, the link, the flags); this module checks
access, locks, reads the rows the rules need and stores the result.  Nothing is deleted: a retired
lesson keeps its row, its photos and its serial (ISO 9001 § 7.5.3).

ACCESS (§ 5.5, § 5.7).  Read with equipment:read: a machine lesson when its machine is inside the
user's units (404 outside, as the node itself); a class lesson by every holder of equipment:read
at any site (as model documents, S012 § 2).  Written with procedure:edit (site-scoped, D4): a
create, and the tick or untick of the class, at the machine's site; a change of a machine lesson
at the machine's site (404 outside the units, then 403); a change of a class lesson with the key
held at any site.  Which rule applies is decided by the locked row's class_id.

LOCK ORDER (equipment.py's numbers; § 5.6).  The database runs REPEATABLE READ: a locking read
sees the newest committed row, a plain read the snapshot of the transaction's first plain read.
Every decision below comes from a locking read, or from a plain read made after the lock that
guards it is held; access checks are plain reads.  Per write this module takes EITHER (6) the OPL
serial counter (a create only) OR (6d) one procedures row FOR UPDATE (a change, or a lesson
document's owner lock), never both and never two procedures rows; then only shared locks.
- Create: plain reads first (the transaction's first: the machine through load_node_for_user,
  404 outside the units, 403 without procedure:edit at its site; its class_id for the tick) →
  (6) next_counter(OPL): only lesson creates take this row, so two creates serialise here, and a
  refused create rolls the bump back (no gap) → with action_id: lesson_source (plain: the
  improvement's predicate 400, its machine 400) → (6c) the countermeasure LOCK IN SHARE MODE
  (kind and state 409) → the lesson already linked to it (a plain read on the snapshot taken by
  the first read, so it only gives the 409 message with the serial; it is no guard) → the
  procedures insert (shared foreign-key locks on the machine (1), the class (5) and the
  countermeasure (6c); uq_procedures_action is the guard: a double tap waits on (6), misses the
  first lesson in the snapshot and meets the key, 409 without the serial) → the detail, read in
  the transaction.
- Change: (6d) the procedures row FOR UPDATE (404) → plain reads (the rights of § 5.5 from the
  locked class_id; when the tick changes, the machine's site and class through NODE_JOINS and the
  key at that site 403; when action_id is set on an unlinked lesson, the link checks as on a
  create with (6c) shared) → update_row of the changed fields (a new class or countermeasure takes
  its shared foreign-key lock).
- A lesson's document (documents.py, its one owner lock): (6d) FOR UPDATE (404) → plain reads (the
  read right 404, the write or purge right 403, decided by the locked class_id) → the
  equipment_documents statement (an insert share-locks the procedures row, held).
- Reads (the list, the detail; the improvement detail's lesson in improvements.py): plain, no lock.
No new deadlock cycle:
- (6) OPL: only lesson creates take it, holding nothing exclusive before it; whoever holds a
  machine, a class or a countermeasure exclusive never waits on an OPL row.
- (6d): only this module and the documents path lock a procedures row, one at a time, first in
  their transaction.  No other module locks or updates procedures rows (improvements.py reads them
  plainly), so no path holds another lock and then waits on (6d).
- The machine (1) and the class (5): taken shared through the foreign keys, after (6) or (6d).  A
  node write (equipment.py) and a class write (masters.py) hold them exclusive and never wait on a
  procedures row or the OPL counter; InnoDB checks a child's foreign key only when the column
  changes, and updates of equipment and equipment_classes never change id.
- (6c): taken shared after (6) or (6d), without (6b).  improvements.py's writers (and the S074
  scan) take (6b) then (6c) exclusive and never wait on (6d) or OPL, so a lesson write waiting on
  (6c) waits behind them and nothing waits on it.  Two lesson writes on one countermeasure share
  the lock and meet on uq_procedures_action.  (S074 D4 rejected a scan that took (6c) before
  (6b): that write then took the improvement too; this one never does.)
- equipment_documents rows follow (6d); nothing else locks them.
"""

from flask import Blueprint, jsonify

from api_common import MAX_PER_PAGE, UNIQUE_KEY_ERRORS, ApiError, actor, clean_body, int_arg
from auth_utils import has_perm, has_perm_at, require_perm, require_perm_at
from db_helpers import count, get_db, insert_row, marks, next_counter, row_to_dict, transaction, update_row
from equipment import NODE_JOINS, accessible_unit_ids, load_node_for_user
from improvements import lesson_source
from procedures_core import (
    ACTION_NEEDED, EDIT_KEY, KIND_ONE_POINT_LESSON, LINK_RACE, READ_KEY, SERIAL_SCOPE, already_has_lesson,
    format_lesson_serial, lesson_flags, lesson_link_error, lesson_machine_message, link_kept_error, validate_lesson,
)

procedures_bp = Blueprint("procedures", __name__)

UNIQUE_KEY_ERRORS.update({
    "uq_procedures_action": ("action_id", LINK_RACE),
})

# (6d): the lesson's decision columns, and the values a change compares with
_LOCK_PROCEDURE = ("SELECT id, equipment_id, class_id, action_id, active, title, body FROM procedures"
                   " WHERE id = %s FOR UPDATE")
# (6c), shared: the link rule is decided from this row
_SHARE_ACTION = "SELECT id, improvement_id, kind, state FROM improvement_actions WHERE id = %s LOCK IN SHARE MODE"

# One lesson with its machine (code, name, current unit and site, class now) through NODE_JOINS, the
# class it is shown for (lc) and its writers' names.  e.class_id is the machine's class at read
# time, which the tick stores (§ 5.1).
_LESSON_SELECT = (
    "SELECT pr.id, pr.serial, pr.kind, pr.equipment_id, pr.class_id, pr.title, pr.body, pr.action_id, pr.active,"
    " pr.created_at, pr.created_by, pr.updated_at, pr.updated_by, e.code AS m_code, e.name AS m_name,"
    " e.class_id AS machine_class_id, u.id AS unit_id, s.id AS site_id, lc.code AS class_code,"
    " lc.name AS class_name, cp.name AS created_by_name, up.name AS updated_by_name"
    " FROM procedures pr JOIN equipment e ON e.id = pr.equipment_id" + NODE_JOINS +
    " LEFT JOIN equipment_classes lc ON lc.id = pr.class_id"
    " LEFT JOIN people cp ON cp.username = pr.created_by"
    " LEFT JOIN people up ON up.username = pr.updated_by"
)

_LIST_COLUMNS = (
    "SELECT pr.id, pr.serial, pr.title, pr.equipment_id, pr.class_id, pr.active, lc.code AS class_code,"
    " lc.name AS class_name FROM procedures pr LEFT JOIN equipment_classes lc ON lc.id = pr.class_id"
)


# ---------------------------------------------------------------------------
# Reads and access
# ---------------------------------------------------------------------------

def _lesson_row(cur, procedure_id):
    """Plain read of one lesson with its machine; 404 when there is none."""
    cur.execute(f"{_LESSON_SELECT} WHERE pr.id = %s", (procedure_id,))
    row = cur.fetchone()
    if row is None:
        raise ApiError("Not found", 404)
    return row


def _machine_visible(cur, row):
    """The lesson's machine is inside the units where the user holds equipment:read (S011 § 5.3;
    the unit is the root equipment's, through NODE_JOINS, as load_node_for_user decides)."""
    unit_ids = accessible_unit_ids(cur)
    return unit_ids is None or row["unit_id"] in unit_ids


def _check_rights(cur, row, class_id, key):
    """§ 5.5 and § 5.7 by ``class_id`` (the locked one on a write): a machine lesson needs its
    machine inside the user's units (404), then ``key``, when given, at the machine's site (403);
    a class lesson needs nothing more, because the route's require_perm (or documents.py's
    _owner_key) has checked the key held at any site."""
    if class_id is not None:
        return
    if not _machine_visible(cur, row):
        raise ApiError("Not found", 404)
    if key is not None:
        require_perm_at(key, row["site_id"])


def _lock_procedure(cur, procedure_id):
    """(6d) -> the locked row; 404 when there is none."""
    cur.execute(_LOCK_PROCEDURE, (procedure_id,))
    locked = cur.fetchone()
    if locked is None:
        raise ApiError("Not found", 404)
    return locked


def _documents(cur, procedure_id):
    """The lesson's documents not removed, oldest first: the order the writer added the photos is
    the lesson's order (§ 6.3).  The documents route's own list stays newest first."""
    cur.execute("SELECT id, kind, title, has_thumb FROM equipment_documents"
                " WHERE procedure_id = %s AND removed_at IS NULL ORDER BY created_at, id", (procedure_id,))
    return [{"id": r["id"], "kind": r["kind"], "title": r["title"], "has_thumb": bool(r["has_thumb"])}
            for r in cur.fetchall()]


def _class_ref(row):
    return {"id": row["class_id"], "code": row["class_code"], "name": row["class_name"]} if row["class_id"] else None


def _source(cur, row):
    """"From improvement IM-…" (§ 5.9), only for a reader who may open that improvement."""
    if row["action_id"] is None:
        return None
    improvement = lesson_source(cur, row["action_id"])
    if improvement is None:
        return None
    return {"improvement": {"id": improvement["id"], "serial": improvement["serial"], "title": improvement["title"]},
            "action_id": row["action_id"]}


def _detail(cur, row):
    """One lesson as its page shows it (§ 6.3).  ``machine`` is null for a class lesson whose
    machine is outside the reader's units: the class line names it instead."""
    plain = row_to_dict(row)
    for_class = row["class_id"] is not None
    machine_shown = not for_class or _machine_visible(cur, row)
    return {
        "id": plain["id"],
        "serial": plain["serial"],
        "kind": plain["kind"],
        "title": plain["title"],
        "body": plain["body"],
        "active": bool(plain["active"]),
        "for_class": for_class,
        "class": _class_ref(plain),
        "machine": {"id": plain["equipment_id"], "code": plain["m_code"], "name": plain["m_name"]}
        if machine_shown else None,
        "created_at": plain["created_at"],
        "created_by_name": plain["created_by_name"] or plain["created_by"],
        "updated_at": plain["updated_at"],
        "updated_by_name": (plain["updated_by_name"] or plain["updated_by"]) if plain["updated_by"] else None,
        "source": _source(cur, row),
        "documents": _documents(cur, row["id"]),
        **lesson_flags(for_class, has_perm_at(EDIT_KEY, row["site_id"]), has_perm(EDIT_KEY)),
    }


def _detail_response(cur, procedure_id):
    """The detail, read inside the write's transaction (one answer, one page copy, S068 BR1-09)."""
    return _detail(cur, _lesson_row(cur, procedure_id))


def _covers(cur, procedure_ids):
    """Each lesson's oldest photo not removed, in one query (no N+1) ->
    ``{procedure_id: {doc_id, has_thumb}}``."""
    if not procedure_ids:
        return {}
    cur.execute("SELECT d.procedure_id, d.id, d.has_thumb FROM equipment_documents d JOIN ("
                "SELECT MIN(id) AS id FROM equipment_documents"
                f" WHERE procedure_id IN ({marks(procedure_ids)}) AND kind = 'photo' AND removed_at IS NULL"
                " GROUP BY procedure_id) f ON f.id = d.id", list(procedure_ids))
    return {r["procedure_id"]: {"doc_id": r["id"], "has_thumb": bool(r["has_thumb"])} for r in cur.fetchall()}


def _lessons_of_node(cur, node, active):
    """The lessons § 5.1 shows on the node's page (its own and its class's), newest first, up to
    MAX_PER_PAGE, and the count of them -> ``(rows, total)``."""
    where = "(pr.equipment_id = %s OR pr.class_id = %s) AND pr.active = %s"
    params = [node["id"], node["class_id"], int(active)]
    total = count(cur, f"SELECT COUNT(*) AS n FROM procedures pr WHERE {where}", params)
    cur.execute(f"{_LIST_COLUMNS} WHERE {where} ORDER BY pr.id DESC LIMIT %s", [*params, MAX_PER_PAGE])
    return cur.fetchall(), total


def _list_items(rows, node_id, covers):
    return [{
        "id": r["id"], "serial": r["serial"], "title": r["title"], "for_class": r["class_id"] is not None,
        "class": _class_ref(r), "own": r["equipment_id"] == node_id, "active": bool(r["active"]),
        "cover": covers.get(r["id"]),
    } for r in rows]


# ---------------------------------------------------------------------------
# The documents store's fifth owner (§ 5.8; documents.OWNERS)
# ---------------------------------------------------------------------------

def read_procedure(cur, procedure_id, _key=None):
    """documents.py's ``read``: one lesson as *one lesson* is read (§ 5.7) -> its row; 404 when
    missing, or for a machine lesson when its machine is outside the user's units.  A class lesson
    is open to every holder of the read key at any site (_owner_key checked it)."""
    row = _lesson_row(cur, procedure_id)
    _check_rights(cur, row, row["class_id"], None)
    return row


def read_procedure_for_change(cur, procedure_id, key):
    """documents.py's ``read_for_change``: a write's early refusals from plain reads, so a refused
    upload reads and writes no file (S006 § 5.6).  By the stored target: a machine lesson 404, then
    ``key`` at the machine's site 403; a class lesson nothing beyond _owner_key's any-site check.
    No state rule: a retired lesson's photos may change (§ 5.4).  The decisions that count are
    lock_procedure_for_change's."""
    row = _lesson_row(cur, procedure_id)
    _check_rights(cur, row, row["class_id"], key)
    return row


def lock_procedure_for_change(cur, procedure_id, key):
    """documents.py's ``lock_for_change`` and ``lock_for_purge`` (upload, retitle, remove, restore,
    purge), in the write transaction: (6d) FOR UPDATE (404), then by the locked class_id — a
    machine lesson: its machine inside the user's units (404) and ``key`` (the write key, or the
    purge key on restore and purge) at the machine's site (403); a class lesson: nothing beyond
    _owner_key's any-site check.  No state rule, so restore and purge need no separate function."""
    locked = _lock_procedure(cur, procedure_id)
    _check_rights(cur, _lesson_row(cur, procedure_id), locked["class_id"], key)


# ---------------------------------------------------------------------------
# The link to a countermeasure (§ 5.3)
# ---------------------------------------------------------------------------

def _check_link(cur, action_id, equipment_id):
    """§ 5.3 in § 5.6's order: the countermeasure's improvement through its predicate (plain;
    None -> 400 on action_id: a body field naming a record the user cannot open) and the
    improvement's machine (400 on equipment_id); then (6c) shared, its kind and state (409); then
    the lesson already linked to it (plain read on the snapshot, 409 with the serial; only the
    message: uq_procedures_action is the guard, see LOCK ORDER)."""
    source = lesson_source(cur, action_id)
    if source is None:
        raise ApiError(ACTION_NEEDED, 400, "action_id")
    if equipment_id != source["equipment_id"]:
        raise ApiError(lesson_machine_message(source["machine_code"]), 400, "equipment_id")
    cur.execute(_SHARE_ACTION, (action_id,))   # (6c), shared
    action = cur.fetchone()
    message = lesson_link_error(action["kind"], action["state"])
    if message:
        raise ApiError(message, 409, "action_id")
    cur.execute("SELECT serial FROM procedures WHERE action_id = %s", (action_id,))
    linked = cur.fetchone()
    if linked is not None:
        raise ApiError(already_has_lesson(linked["serial"]), 409, "action_id")


# ---------------------------------------------------------------------------
# Routes (§ 6)
# ---------------------------------------------------------------------------

@procedures_bp.route("/", strict_slashes=False)
@require_perm(READ_KEY)
def list_lessons():
    """A machine's lessons (§ 6.2): the active ones in ``items``, the retired ones in ``retired``
    only for a holder of procedure:edit at any site (they bring one back)."""
    equipment_id = int_arg("equipment_id", None, minimum=1)
    if equipment_id is None:
        raise ApiError("equipment_id is required", 400, "equipment_id")
    with get_db().cursor() as cur:
        _, node = load_node_for_user(cur, equipment_id, for_update=False)   # 404 outside the units
        rows, total = _lessons_of_node(cur, node, active=True)
        retired = _lessons_of_node(cur, node, active=False)[0] if has_perm(EDIT_KEY) else []
        covers = _covers(cur, [r["id"] for r in (*rows, *retired)])
        return jsonify({
            "items": _list_items(rows, node["id"], covers),
            "retired": _list_items(retired, node["id"], covers),
            "total": total,
            "can_add": has_perm_at(EDIT_KEY, node["site_id"]),
        })


@procedures_bp.route("/<int:procedure_id>")
@require_perm(READ_KEY)
def get_lesson(procedure_id):
    with get_db().cursor() as cur:
        return jsonify(_detail(cur, read_procedure(cur, procedure_id)))


@procedures_bp.route("/", methods=["POST"], strict_slashes=False)
@require_perm(EDIT_KEY)
def create_lesson():
    """A lesson on a machine (§ 5.1), for its class when ticked, linked to a countermeasure of kind
    Lesson when action_id is given (§ 5.3).  Needs procedure:edit at the machine's site."""
    clean = clean_body(validate_lesson, creating=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        # Plain, the transaction's first: 404 outside the units, 403 without the key at its site
        _, node = load_node_for_user(cur, clean["equipment_id"], for_update=False, key=EDIT_KEY)
        number = next_counter(cur, SERIAL_SCOPE)   # (6): a refused create rolls the bump back
        if clean["action_id"] is not None:
            _check_link(cur, clean["action_id"], node["id"])
        procedure_id = insert_row(cur, "procedures", {
            "serial": format_lesson_serial(number),
            "kind": KIND_ONE_POINT_LESSON,
            "equipment_id": node["id"],
            "class_id": node["class_id"] if clean["for_class"] else None,
            "title": clean["title"],
            "body": clean["body"],
            "action_id": clean["action_id"],
        }, actor())
        detail = _detail_response(cur, procedure_id)
    return jsonify(detail), 201


@procedures_bp.route("/<int:procedure_id>", methods=["PUT"])
@require_perm(EDIT_KEY)
def change_lesson(procedure_id):
    """Title, text, the class tick, retire or bring back (``active``), and a countermeasure link
    on a lesson that has none (§ 5.2–§ 5.5).  A field equal to the stored one is not written, and
    a change of nothing writes nothing (no updated_at)."""
    clean = clean_body(validate_lesson, creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        locked = _lock_procedure(cur, procedure_id)   # (6d)
        row = _lesson_row(cur, procedure_id)
        _check_rights(cur, row, locked["class_id"], EDIT_KEY)   # 404, 403 by the locked target
        changes = {field: clean[field] for field in ("title", "body") if field in clean and clean[field] != locked[field]}
        if "active" in clean and clean["active"] != bool(locked["active"]):
            changes["active"] = int(clean["active"])
        if "for_class" in clean and clean["for_class"] != (locked["class_id"] is not None):
            # Ticking or unticking needs the machine's site, whatever the stored target (§ 5.5)
            require_perm_at(EDIT_KEY, row["site_id"])
            changes["class_id"] = row["machine_class_id"] if clean["for_class"] else None
        if "action_id" in clean:
            message = link_kept_error(locked["action_id"], clean["action_id"])
            if message:
                raise ApiError(message, 409, "action_id")
            if locked["action_id"] is None and clean["action_id"] is not None:
                _check_link(cur, clean["action_id"], locked["equipment_id"])
                changes["action_id"] = clean["action_id"]
        update_row(cur, "procedures", procedure_id, changes, actor())
        detail = _detail_response(cur, procedure_id)
    return jsonify(detail)
