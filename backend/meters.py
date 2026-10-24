"""A node's meters — its model's meters plus its own (docs/steps/S038-meters-on-models-equipment/
1-brief.md § 1.2, § 1.3, § 5).

Thin shell: meters_core holds the rules (limits, which meters a node has, the wording); this
module checks access and the scrapped rule, locks, stores and writes the history line.  The
model's meters are edited in Masters (masters.py); here a node adds its own meters, overrides
a model meter's limits, and removes its own meters.

Rows (node_meters, v30): one per node and meter type.  ``own = 1`` is a meter added on this
node; ``own = 0`` an override of the model meter's limits, kept only while it differs from
the model (an override equal to the model is deleted).  ``own`` never changes after insert,
so a later model change gives back the machine's own meter (BR1-04).  Remove sets an own
row inactive with no limits, so it can never act as a stale override (BR2-02).

Locks (equipment.py's LOCK ORDER): (1) the node, through load_node_for_user, which checks
equipment:edit at the node's site; the scrapped refusal is decided from that locked row →
(4b) the meter type → the node_meters row, by its unique key FOR UPDATE.  The model's meters
are read plainly: they change only under the model's lock, and a race shows a stale list
until reload (§ 7 decision 6).  The model id comes from the locked node row (BR1-17).
"""

from flask import Blueprint, jsonify, request

from api_common import UNIQUE_KEY_ERRORS, ApiError, actor, clean_body
from auth_utils import require_perm
from db_helpers import get_db, insert_row, transaction, update_row
from equipment import SCRAPPED_MESSAGE, load_node_for_user, write_events
from equipment_core import SCRAPPED
from masters import checked_limits, lock_meter_type, read_model_meters
from masters_core import model_label
from meters_core import (
    ACTION_REMOVE, ACTION_USE_MODEL, NO_LIMITS, effective_meters, in_force_pair, meter_type_of,
    parse_change_action, parse_meter_type_id, same_limits, tracked_meter_change,
)

meters_bp = Blueprint("meters", __name__)

ALREADY_ON_NODE = "This machine already has this meter"
NO_LONGER_ON_MODEL = "This meter is no longer on the model. Reload the page."

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


def _model_meter(cur, model_id, meter_type_id):
    """The model's active meter of this type (plain read), or None."""
    if model_id is None:
        return None
    return next((m for m in read_model_meters(cur, model_id) if m["meter_type"]["id"] == meter_type_id), None)


def _lock_node(cur, node_id):
    """(1): 404 outside the user's units, 403 without equipment:edit at the node's site, 409 when
    scrapped (from the locked row)."""
    locked, node = load_node_for_user(cur, node_id, for_update=True, key="equipment:edit")
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
        return jsonify(_meters_of(cur, node_id, node["model_id"]))


@meters_bp.route("/equipment/<int:node_id>/meters", methods=["POST"])
@require_perm("equipment:edit")
def add_node_meter(node_id):
    """Add an own meter: an active type not already in force on the node (§ 5.3)."""
    meter_type_id = clean_body(lambda body, _creating: parse_meter_type_id(body), creating=True)
    body = request.get_json(silent=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        locked, _ = _lock_node(cur, node_id)                                  # (1)
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
        return jsonify(_meters_of(cur, node_id, locked["model_id"])), 201


@meters_bp.route("/equipment/<int:node_id>/meters/<int:meter_type_id>", methods=["PUT"])
@require_perm("equipment:edit")
def change_node_meter(node_id, meter_type_id):
    """Set limits (an override of a model meter, or an own gauge's), use the model's limits
    again, or remove an own meter (``active: false``)."""
    action = clean_body(lambda body, _creating: parse_change_action(body, allow_use_model=True), creating=False)
    body = request.get_json(silent=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        locked, node = _lock_node(cur, node_id)                               # (1)
        meter_type = lock_meter_type(cur, meter_type_id, adding=False)        # (4b)
        row = _lock_node_meter(cur, node_id, meter_type_id)
        model_meter = _model_meter(cur, locked["model_id"], meter_type_id)
        if action == ACTION_REMOVE:
            events = _remove(cur, node, meter_type, model_meter, row)
        else:
            events = _set_limits(cur, node_id, body, action == ACTION_USE_MODEL, meter_type, model_meter, row)
        write_events(cur, node_id, events)
    with conn.cursor() as cur:
        return jsonify(_meters_of(cur, node_id, locked["model_id"]))


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
