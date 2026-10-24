"""A node's meters — its model's meters plus its own (docs/steps/S038-meters-on-models-equipment/
1-brief.md § 1.2, § 1.3, § 5) — and their readings (docs/steps/S039-meter-reading-entry/
1-brief.md § 5, § 6).

Thin shell: meters_core holds the rules (limits, which meters a node has, the wording); this
module checks access and the scrapped rule, locks, stores and writes the history line.  The
model's meters are edited in Masters (masters.py); here a node adds its own meters, overrides
a model meter's limits, and removes its own meters.

Rows (node_meters, v30): one per node and meter type.  ``own = 1`` is a meter added on this
node; ``own = 0`` an override of the model meter's limits, kept only while it differs from
the model (an override equal to the model is deleted).  ``own`` never changes after insert,
so a later model change gives back the machine's own meter (BR1-04).  Remove sets an own
row inactive with no limits, so it can never act as a stale override (BR2-02).

Readings (meter_readings, v32): one row per reading, never deleted; a removal sets
removed_at / removed_by, and every read and rule but the history's *Show removed* leaves it out.
A Yes / No reading is stored as 1 / 0; reading_out gives the API's "yes" / "no" back, and
meters_core.validate_reading turns the words into numbers: the mapping lives there only (BR3-04).

Locks (equipment.py's LOCK ORDER): (1) the node, through load_node_for_user, which checks
equipment:edit at the node's site; the scrapped refusal is decided from that locked row →
(4b) the meter type → the node_meters row, by its unique key FOR UPDATE.  The model's meters
are read plainly: they change only under the model's lock, and a race shows a stale list
until reload (§ 7 decision 6).  The model id comes from the locked node row (BR1-17).
A reading write: (1), then plain reads; the node lock is the first statement (S039 § 5.3).
Logging checks reading:log at the node's site; the link rows, the meter type, the neighbour
readings and the same-minute row are then read plainly, so two writers on one node serialise
on (1) and the second sees the first one's row (its snapshot starts after the lock).  No
locking range read: gap locks on ix_meter_readings_meter_time could deadlock two inserts.  A
removal checks equipment:edit (IT admin removes, but does not log), then locks the reading row.
"""

from datetime import datetime

from flask import Blueprint, jsonify, request

from api_common import MAX_PAGE, MAX_PER_PAGE, UNIQUE_KEY_ERRORS, ApiError, actor, clean_body, int_arg
from auth_utils import has_perm_at, require_perm
from db_helpers import count, get_db, insert_row, row_to_dict, transaction, update_row
from equipment import IST, SCRAPPED_MESSAGE, load_node_for_user, write_events
from equipment_core import SCRAPPED
from masters import checked_limits, lock_meter_type, read_model_meters
from masters_core import model_label
from meters_core import (
    ACTION_REMOVE, ACTION_USE_MODEL, COUNTER, GAUGE, NO_LIMITS, PICK_A_METER, YES_NO, answer_state, answer_word,
    counter_error, effective_meters, format_number, in_force_pair, limit_state, may_remove, meter_type_of,
    parse_change_action, parse_meter_type_id, parse_reading_request, reset_removal_error, same_limits, to_minute,
    tracked_meter_change, validate_reading,
)

meters_bp = Blueprint("meters", __name__)

ALREADY_ON_NODE = "This machine already has this meter"
NO_LONGER_ON_MODEL = "This meter is no longer on the model. Reload the page."
NOT_ON_NODE = "This machine does not have this meter. Reload the page."
SAME_MINUTE = "A reading at this time exists. Pick another time, or remove that reading first."
ALREADY_REMOVED = "This reading was removed"

# The history dialog's page (§ 6): a meter has a few hundred readings a year
HISTORY_PER_PAGE = 30

UNIQUE_KEY_ERRORS.update({
    "uq_node_meters": ("meter_type_id", ALREADY_ON_NODE),
})

_NODE_METER_SELECT = (
    "SELECT nm.id, nm.own, nm.min_value, nm.max_value, nm.active,"
    " t.id AS t_id, t.name AS t_name, t.unit AS t_unit, t.kind AS t_kind, t.decimals AS t_decimals,"
    " t.expected_answer AS t_expected_answer"
    " FROM node_meters nm JOIN meter_types t ON t.id = nm.meter_type_id"
)


def _node_rows(cur, node_id):
    cur.execute(f"{_NODE_METER_SELECT} WHERE nm.equipment_id = %s", (node_id,))
    return [{"id": row["id"], "own": row["own"], "meter_type": meter_type_of(row), "min_value": row["min_value"],
             "max_value": row["max_value"], "active": row["active"]} for row in cur.fetchall()]


def _meters_of(cur, node_id, model_id):
    """The node's meters (meters_core.effective_meters); a node without a model (S033) has
    only its own."""
    model_meters = read_model_meters(cur, model_id) if model_id is not None else []
    return effective_meters(model_meters, _node_rows(cur, node_id))


def _meters_out(cur, node_id, model_id):
    """The node's meters as the card shows them: each with ``last``, its newest active reading
    ``{value, taken_at, limit_state}``, or None before any reading (§ 6)."""
    meters = _meters_of(cur, node_id, model_id)
    last = _last_readings(cur, node_id)
    for meter in meters:
        row = last.get(meter["meter_type"]["id"])
        meter["last"] = None if row is None else {
            key: reading_out(row, meter["meter_type"]["kind"])[key] for key in ("value", "taken_at", "limit_state")}
    return meters


def _model_meter(cur, model_id, meter_type_id):
    """The model's active meter of this type (plain read), or None."""
    if model_id is None:
        return None
    return next((m for m in read_model_meters(cur, model_id) if m["meter_type"]["id"] == meter_type_id), None)


def _lock_node(cur, node_id, key):
    """(1): 404 outside the user's units, 403 without ``key`` at the node's site (equipment:edit
    for a meter write or a reading's removal, reading:log for a reading), 409 when scrapped
    (from the locked row)."""
    locked, node = load_node_for_user(cur, node_id, for_update=True, key=key)
    if locked["lifecycle"] == SCRAPPED:
        raise ApiError(SCRAPPED_MESSAGE, 409)
    return locked, node


def _lock_node_meter(cur, node_id, meter_type_id):
    cur.execute("SELECT id, own, min_value, max_value, active FROM node_meters"
                " WHERE equipment_id = %s AND meter_type_id = %s FOR UPDATE", (node_id, meter_type_id))
    return cur.fetchone()


def _is_own_meter(row):
    return row is not None and row["own"] and row["active"]


@meters_bp.route("/equipment/<int:node_id>/meters")
@require_perm("equipment:read")
def list_node_meters(node_id):
    with get_db().cursor() as cur:
        _, node = load_node_for_user(cur, node_id, for_update=False, key="equipment:read")
        return jsonify(_meters_out(cur, node_id, node["model_id"]))


@meters_bp.route("/equipment/<int:node_id>/meters", methods=["POST"])
@require_perm("equipment:edit")
def add_node_meter(node_id):
    """Add an own meter: an active type not already in force on the node (§ 5.3)."""
    meter_type_id = clean_body(lambda body, _creating: parse_meter_type_id(body), creating=True)
    body = request.get_json(silent=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        locked, _ = _lock_node(cur, node_id, "equipment:edit")                # (1)
        meter_type = lock_meter_type(cur, meter_type_id, adding=True)         # (4b)
        row = _lock_node_meter(cur, node_id, meter_type_id)
        if _model_meter(cur, locked["model_id"], meter_type_id) is not None or _is_own_meter(row):
            raise ApiError(ALREADY_ON_NODE, 409, "meter_type_id")
        low, high = checked_limits(body, meter_type, NO_LIMITS)
        values = {"min_value": low, "max_value": high, "active": 1}
        if row is not None and row["own"]:
            update_row(cur, "node_meters", row["id"], values, actor())       # a removed own meter comes back
        else:
            if row is not None:
                # An override of a type no longer on the model: the own meter takes its place
                cur.execute("DELETE FROM node_meters WHERE id = %s", (row["id"],))
            insert_row(cur, "node_meters",
                       {"equipment_id": node_id, "meter_type_id": meter_type_id, "own": 1, **values}, actor())
        write_events(cur, node_id, [("meter_added", None, meter_type["name"])])
    with conn.cursor() as cur:
        return jsonify(_meters_out(cur, node_id, locked["model_id"])), 201


@meters_bp.route("/equipment/<int:node_id>/meters/<int:meter_type_id>", methods=["PUT"])
@require_perm("equipment:edit")
def change_node_meter(node_id, meter_type_id):
    """Set limits (an override of a model meter, or an own gauge's), use the model's limits
    again, or remove an own meter (``active: false``)."""
    action = clean_body(lambda body, _creating: parse_change_action(body, allow_use_model=True), creating=False)
    body = request.get_json(silent=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        locked, node = _lock_node(cur, node_id, "equipment:edit")             # (1)
        meter_type = lock_meter_type(cur, meter_type_id, adding=False)        # (4b)
        row = _lock_node_meter(cur, node_id, meter_type_id)
        model_meter = _model_meter(cur, locked["model_id"], meter_type_id)
        if action == ACTION_REMOVE:
            events = _remove(cur, node, meter_type, model_meter, row)
        else:
            events = _set_limits(cur, node_id, body, action == ACTION_USE_MODEL, meter_type, model_meter, row)
        write_events(cur, node_id, events)
    with conn.cursor() as cur:
        return jsonify(_meters_out(cur, node_id, locked["model_id"]))


def _remove(cur, node, meter_type, model_meter, row):
    """An own meter → inactive with no limits; a model meter cannot be removed on one node."""
    if model_meter is not None:
        label = model_label(node["manufacturer_name"], node["model_designation"])
        raise ApiError(f"Comes from the model {label}. Remove it in Masters › Models, or change this machine's model.",
                       409)
    if not _is_own_meter(row):
        raise ApiError("Not found", 404)
    update_row(cur, "node_meters", row["id"], {"active": 0, "min_value": None, "max_value": None}, actor())
    return [("meter_removed", meter_type["name"], None)]


def _set_limits(cur, node_id, body, use_model, meter_type, model_meter, row):
    """The limits in force after the write; the history line shows both sides in force.  A
    limits write never changes ``active`` (BR2-02)."""
    before = in_force_pair(model_meter, row)
    if model_meter is None:
        if use_model or not _is_own_meter(row):
            raise ApiError(NO_LONGER_ON_MODEL, 409)
        after = checked_limits(body, meter_type, before)
        update_row(cur, "node_meters", row["id"], {"min_value": after[0], "max_value": after[1]}, actor())
        return tracked_meter_change(meter_type, before, after)

    model_pair = (model_meter["min_value"], model_meter["max_value"])
    after = model_pair if use_model else checked_limits(body, meter_type, before)
    if same_limits(after, model_pair):
        # No override (BR1-03): an own = 0 row goes; an own = 1 row (the model gained the type
        # later) stays with no limits, so a later model change gives back the machine's meter
        if row is not None and row["own"]:
            update_row(cur, "node_meters", row["id"], {"min_value": None, "max_value": None}, actor())
        elif row is not None:
            cur.execute("DELETE FROM node_meters WHERE id = %s", (row["id"],))
    elif row is not None:
        update_row(cur, "node_meters", row["id"], {"min_value": after[0], "max_value": after[1]}, actor())
    else:
        insert_row(cur, "node_meters", {"equipment_id": node_id, "meter_type_id": meter_type["id"], "own": 0,
                                        "min_value": after[0], "max_value": after[1]}, actor())
    return tracked_meter_change(meter_type, before, after)


# ---------------------------------------------------------------------------
# Readings (S039)
# ---------------------------------------------------------------------------

_READING_COLUMNS = ("id, meter_type_id, value, taken_at, is_reset, limit_state, note, created_at, created_by,"
                    " removed_at, removed_by")
# One meter of one node, active readings only
_ACTIVE = "equipment_id = %s AND meter_type_id = %s AND removed_at IS NULL"
_READING_FIELDS = ("id", "value", "taken_at", "is_reset", "limit_state", "note", "created_by", "created_at",
                   "removed_at", "removed_by")


def _now_minute():
    """The IST wall clock to the minute, naive, as every DATETIME is stored."""
    return to_minute(datetime.now(IST).replace(tzinfo=None))


def reading_out(row, kind):
    """A reading row as the API sends it: a Yes / No meter's stored 1 / 0 back as "yes" / "no"
    (BR3-04), any other value without trailing zeros, the times as the rest of the API."""
    out = row_to_dict({field: row[field] for field in _READING_FIELDS if field in row})
    out["value"] = answer_word(row["value"]) if kind == YES_NO else format_number(row["value"])
    out["is_reset"] = bool(row["is_reset"])
    return out


def _last_readings(cur, node_id):
    """The newest active reading of each of the node's meters → {meter_type_id: row}; newest by
    (taken_at, id), the history's order."""
    cur.execute(
        "SELECT r.meter_type_id, r.value, r.taken_at, r.is_reset, r.limit_state FROM meter_readings r"
        " WHERE r.equipment_id = %s AND r.removed_at IS NULL AND NOT EXISTS ("
        "  SELECT 1 FROM meter_readings n WHERE n.equipment_id = r.equipment_id"
        "  AND n.meter_type_id = r.meter_type_id AND n.removed_at IS NULL"
        "  AND (n.taken_at > r.taken_at OR (n.taken_at = r.taken_at AND n.id > r.id)))", (node_id,))
    return {row["meter_type_id"]: row for row in cur.fetchall()}


def _newest_active_id(cur, node_id, meter_type_id):
    """The id of the meter's newest active reading, or None.  Every other active reading has an
    active later one, so this one query decides the reset rule for a whole history page (BR2-11)."""
    cur.execute(f"SELECT id FROM meter_readings WHERE {_ACTIVE} ORDER BY taken_at DESC, id DESC LIMIT 1",
                (node_id, meter_type_id))
    row = cur.fetchone()
    return row["id"] if row else None


def _neighbour(cur, node_id, meter_type_id, taken_at, later):
    """The nearest active reading before (or after) ``taken_at`` (plain read, after (1))."""
    sign, order = (">", "ASC") if later else ("<", "DESC")
    cur.execute(f"SELECT value, taken_at, is_reset FROM meter_readings WHERE {_ACTIVE} AND taken_at {sign} %s"
                f" ORDER BY taken_at {order}, id {order} LIMIT 1", (node_id, meter_type_id, taken_at))
    return cur.fetchone()


def _limit_state(meter, value):
    """What is stored as limit_state (§ 5.2.5): a gauge against the limits in force, a Yes / No
    answer against the type's expected one; NULL for a counter and an amount."""
    kind = meter["meter_type"]["kind"]
    if kind == GAUGE:
        return limit_state(value, meter["min_value"], meter["max_value"])
    if kind == YES_NO:
        return answer_state(answer_word(value), meter["meter_type"]["expected_answer"])
    return None


@meters_bp.route("/equipment/<int:node_id>/readings")
@require_perm("equipment:read")
def list_readings(node_id):
    """One meter's history, newest first, in the house paging shape (§ 6, BR2-03)."""
    if request.args.get("meter_type_id") is None:
        raise ApiError(PICK_A_METER, 400, "meter_type_id")
    meter_type_id = int_arg("meter_type_id", None, 1)
    page = int_arg("page", 1, 1, MAX_PAGE)
    per_page = int_arg("per_page", HISTORY_PER_PAGE, 1, MAX_PER_PAGE)
    wants_removed = int_arg("include_removed", 0, 0, 1) == 1
    with get_db().cursor() as cur:
        _, node = load_node_for_user(cur, node_id, for_update=False, key="equipment:read")
        cur.execute("SELECT kind FROM meter_types WHERE id = %s", (meter_type_id,))
        meter_type = cur.fetchone()
        if meter_type is None:
            raise ApiError(PICK_A_METER, 400, "meter_type_id")
        # Removed readings are for equipment:edit holders only (§ 5.4); anyone else's ask is ignored
        can_edit = has_perm_at("equipment:edit", node["site_id"])
        where = ("equipment_id = %s AND meter_type_id = %s" if wants_removed and can_edit else _ACTIVE)
        params = (node_id, meter_type_id)
        total = count(cur, f"SELECT COUNT(*) AS n FROM meter_readings WHERE {where}", params)
        cur.execute(f"SELECT {_READING_COLUMNS} FROM meter_readings WHERE {where}"
                    " ORDER BY taken_at DESC, id DESC LIMIT %s OFFSET %s", (*params, per_page, (page - 1) * per_page))
        rows = cur.fetchall()
        newest = _newest_active_id(cur, node_id, meter_type_id)
    # Remove is offered where it would succeed: on a scrapped node every write is refused
    may_edit = can_edit and node["lifecycle"] != SCRAPPED
    items = [{**reading_out(row, meter_type["kind"]),
              "can_remove": may_remove(row, may_edit) and reset_removal_error(row, row["id"] != newest) is None}
             for row in rows]
    return jsonify({"items": items, "total": total, "page": page, "per_page": per_page})


@meters_bp.route("/equipment/<int:node_id>/readings", methods=["POST"])
@require_perm("reading:log")
def log_reading(node_id):
    """Log one reading (§ 5.1, § 5.2): the rules of its meter's kind, then insert."""
    now = _now_minute()
    clean = clean_body(lambda body, _creating: parse_reading_request(body, now), creating=True)
    body = request.get_json(silent=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        locked, _ = _lock_node(cur, node_id, "reading:log")                  # (1), the first statement
        meter = next((m for m in _meters_of(cur, node_id, locked["model_id"])
                      if m["meter_type"]["id"] == clean["meter_type_id"]), None)
        if meter is None:
            raise ApiError(NOT_ON_NODE, 409, "meter_type_id")
        meter_type = meter["meter_type"]
        reading, errors = validate_reading(body.get("value"), meter_type["kind"], meter_type["decimals"],
                                           body.get("is_reset", False), body.get("note"))
        if errors:
            raise ApiError(errors[0]["message"], 400, errors[0]["field"])
        taken_at = clean["taken_at"]
        key = (node_id, meter_type["id"])
        if count(cur, f"SELECT COUNT(*) AS n FROM meter_readings WHERE {_ACTIVE} AND taken_at = %s",
                 (*key, taken_at)):
            raise ApiError(SAME_MINUTE, 409, "taken_at")
        if meter_type["kind"] == COUNTER:
            refusal = counter_error(reading["value"], reading["is_reset"],
                                    _neighbour(cur, *key, taken_at, later=False),
                                    _neighbour(cur, *key, taken_at, later=True), meter_type)
            if refusal:
                field, message, code = refusal
                raise ApiError(message, 400, field, code)
        reading_id = insert_row(cur, "meter_readings", {
            "equipment_id": node_id, "meter_type_id": meter_type["id"], "value": reading["value"],
            "taken_at": taken_at, "is_reset": reading["is_reset"], "limit_state": _limit_state(meter, reading["value"]),
            "note": reading["note"],
        }, actor())
        cur.execute(f"SELECT {_READING_COLUMNS} FROM meter_readings WHERE id = %s", (reading_id,))
        row = cur.fetchone()
    return jsonify(reading_out(row, meter_type["kind"])), 201


@meters_bp.route("/equipment/<int:node_id>/readings/<int:reading_id>", methods=["DELETE"])
@require_perm("equipment:edit")
def remove_reading(node_id, reading_id):
    """Remove a wrong reading (§ 1.4, § 5.2.6): it is hidden, with who and when kept."""
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        _lock_node(cur, node_id, "equipment:edit")                           # (1); 404; 403; 409 scrapped
        cur.execute(f"SELECT {_READING_COLUMNS} FROM meter_readings WHERE id = %s AND equipment_id = %s FOR UPDATE",
                    (reading_id, node_id))
        reading = cur.fetchone()
        if reading is None:
            raise ApiError("Not found", 404)
        if not may_remove(reading, can_edit=True):
            raise ApiError(ALREADY_REMOVED, 409)
        message = reset_removal_error(reading, _newest_active_id(cur, node_id, reading["meter_type_id"]) != reading_id)
        if message:
            raise ApiError(message, 409)
        cur.execute("UPDATE meter_readings SET removed_at = NOW(), removed_by = %s WHERE id = %s",
                    (actor(), reading_id))
    return "", 204
