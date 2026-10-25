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

The reading register (S050, docs/steps/S050-reading-register/1-brief.md § 5, § 6): one node's
active readings as a table, a row per minute and a column per meter; a plain read under
equipment:read, paged by minute.

Meter readings on the ticket (S052, docs/steps/S052-ticket-meters/1-brief.md § 5, § 6): each meter
in force on the ticket's machine and the nodes down to its part, with the reading as it stood at the
ticket's time and the marked readings of the week before; a plain read under ticket:read.
"""

from datetime import datetime

from flask import Blueprint, jsonify, request

from api_common import MAX_PAGE, MAX_PER_PAGE, UNIQUE_KEY_ERRORS, ApiError, actor, clean_body, int_arg
from auth_utils import has_perm_at, require_perm
from db_helpers import count, get_db, insert_row, row_to_dict, rows_to_list, transaction, update_row
from equipment import IST, SCRAPPED_MESSAGE, accessible_unit_ids, load_node_for_user, node_path, write_events
from equipment_core import SCRAPPED
from masters import checked_limits, lock_meter_type, read_model_meters, read_models_meters
from masters_core import model_label
from meters_core import (
    ACTION_REMOVE, ACTION_USE_MODEL, COUNTER, GAUGE, MARK_WINDOW_DAYS, NO_LIMITS, PICK_A_METER, YES_NO, answer_state,
    answer_word, counter_error, effective_meters, format_number, in_force_pair, limit_state, mark_window, may_remove,
    meter_type_of, parse_change_action, parse_meter_type_id, parse_meter_type_ids, parse_reading_request,
    readings_at_ticket, register_columns, register_rows, reset_removal_error, same_limits, shown_meter_ids, to_minute,
    tracked_meter_change, validate_reading,
)
from tickets import read_ticket
from tickets_core import machine_and_component

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
    "SELECT nm.id, nm.equipment_id, nm.own, nm.min_value, nm.max_value, nm.active,"
    " t.id AS t_id, t.name AS t_name, t.unit AS t_unit, t.kind AS t_kind, t.decimals AS t_decimals,"
    " t.expected_answer AS t_expected_answer"
    " FROM node_meters nm JOIN meter_types t ON t.id = nm.meter_type_id"
)


def _nodes_rows(cur, node_ids):
    """The node_meters rows of several nodes in one query -> {node_id: [row, ...]}."""
    out = {node_id: [] for node_id in node_ids}
    if not out:
        return out
    cur.execute(f"{_NODE_METER_SELECT} WHERE nm.equipment_id IN ({_marks(out)})", list(out))
    for row in cur.fetchall():
        out[row["equipment_id"]].append({
            "id": row["id"], "own": row["own"], "meter_type": meter_type_of(row), "min_value": row["min_value"],
            "max_value": row["max_value"], "active": row["active"]})
    return out


def _node_rows(cur, node_id):
    return _nodes_rows(cur, [node_id])[node_id]


def _meters_of(cur, node_id, model_id):
    """The node's meters (meters_core.effective_meters); a node without a model (S033) has
    only its own."""
    model_meters = read_model_meters(cur, model_id) if model_id is not None else []
    return effective_meters(model_meters, _node_rows(cur, node_id))


def _meters_out(cur, node_id, model_id):
    """The node's meters as the card shows them: each with ``last``, its newest active reading
    ``{value, taken_at, limit_state}``, or None before any reading (§ 6)."""
    meters = _meters_of(cur, node_id, model_id)
    _add_last(meters, _last_readings(cur, [node_id]), node_id)
    return meters


def _add_last(meters, last, node_id):
    """Put ``last`` on each of the node's meters, from ``_last_readings``' {(node, type): row}."""
    for meter in meters:
        row = last.get((node_id, meter["meter_type"]["id"]))
        meter["last"] = None if row is None else {
            key: reading_out(row, meter["meter_type"]["kind"])[key] for key in ("value", "taken_at", "limit_state")}


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


def _last_readings(cur, node_ids, until=None):
    """The newest active reading of each meter of the nodes → {(node_id, meter_type_id): row};
    newest by (taken_at, id), the history's order.  One query for any number of nodes.

    ``until`` (a naive IST datetime; S052 § 3) limits it to the readings taken at or before that
    time.  The bound is on the outer row *and* the NOT EXISTS neighbour: a later reading must not
    count as the newer one, or it would hide every earlier reading (S052 BR1-02).  Without
    ``until`` the query is the S039 card's and the S040 sheet's as before."""
    if not node_ids:
        return {}
    outer_bound, neighbour_bound, params = "", "", list(node_ids)
    if until is not None:
        outer_bound, neighbour_bound = " AND r.taken_at <= %s", " AND n.taken_at <= %s"
        params = [*node_ids, until, until]
    cur.execute(
        "SELECT r.equipment_id, r.meter_type_id, r.value, r.taken_at, r.is_reset, r.limit_state"
        " FROM meter_readings r"
        f" WHERE r.equipment_id IN ({_marks(node_ids)}) AND r.removed_at IS NULL{outer_bound} AND NOT EXISTS ("
        "  SELECT 1 FROM meter_readings n WHERE n.equipment_id = r.equipment_id"
        f"  AND n.meter_type_id = r.meter_type_id AND n.removed_at IS NULL{neighbour_bound}"
        "  AND (n.taken_at > r.taken_at OR (n.taken_at = r.taken_at AND n.id > r.id)))", params)
    return {(row["equipment_id"], row["meter_type_id"]): row for row in cur.fetchall()}


def _mark_counts(cur, node_ids, since, until):
    """The number of active marked readings (a gauge High / Low, a Yes / No Not OK) of each meter
    of the nodes taken in (``since``, ``until``] → {(node_id, meter_type_id): count} (S052 § 5.1
    step 6).  A counter and an amount store no limit_state, so they never appear."""
    if not node_ids:
        return {}
    cur.execute(
        "SELECT equipment_id, meter_type_id, COUNT(*) AS n FROM meter_readings"
        f" WHERE equipment_id IN ({_marks(node_ids)}) AND removed_at IS NULL AND limit_state IS NOT NULL"
        " AND taken_at > %s AND taken_at <= %s GROUP BY equipment_id, meter_type_id", [*node_ids, since, until])
    return {(row["equipment_id"], row["meter_type_id"]): row["n"] for row in cur.fetchall()}


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


# ---------------------------------------------------------------------------
# The end-of-day sheet (S040)
# ---------------------------------------------------------------------------

PICK_A_SITE = "Pick a site"


def _sheet_site_id():
    raw = request.args.get("site_id")
    if raw is None or not (raw.isascii() and raw.isdigit()) or int(raw) < 1:
        raise ApiError(PICK_A_SITE, 400, "site_id")
    return int(raw)


def _sheet_units(cur, site_id):
    """The site and its active units where the user logs readings -> (site, units); 404 when the
    site is unknown, inactive or has no such unit (admin too: its set is None, so ``active`` is
    checked here, BR1-17)."""
    cur.execute("SELECT id, code, name FROM sites WHERE id = %s AND active = 1", (site_id,))
    site = cur.fetchone()
    allowed = accessible_unit_ids(cur, "reading:log")
    if site is None or allowed == set():
        raise ApiError("Not found", 404)
    cur.execute("SELECT id, code, name FROM units WHERE site_id = %s AND active = 1 ORDER BY code", (site_id,))
    units = [u for u in cur.fetchall() if allowed is None or u["id"] in allowed]
    if not units:
        raise ApiError("Not found", 404)
    return site, units


def _marks(ids):
    return ", ".join(["%s"] * len(ids))


def _sheet_nodes(cur, unit_ids):
    """The machines of the units and their parts (two levels), scrapped ones left out, by code ->
    ([machine rows], {parent_id: [part rows]}); a scrapped part's own parts go with it."""
    def rows(column, ids):
        if not ids:
            return []
        cur.execute("SELECT id, code, name, level, parent_id, unit_id, model_id, lifecycle FROM equipment"
                    f" WHERE {column} IN ({_marks(ids)}) AND lifecycle <> %s ORDER BY code", (*ids, SCRAPPED))
        return cur.fetchall()

    machines = rows("unit_id", unit_ids)
    children = rows("parent_id", [m["id"] for m in machines])
    grandchildren = rows("parent_id", [c["id"] for c in children])
    parts = {}
    for part in [*children, *grandchildren]:
        parts.setdefault(part["parent_id"], []).append(part)
    return machines, parts


@meters_bp.route("/readings/sheet")
@require_perm("reading:log")
def readings_sheet():
    """Every meter in force at one site, grouped by unit (S040 § 5.1, § 6): the units where the
    user logs, their machines (and parts) that have meters, each meter with its last reading.  A
    few queries for the whole site, none per node."""
    site_id = _sheet_site_id()
    with get_db().cursor() as cur:
        site, units = _sheet_units(cur, site_id)
        machines, parts = _sheet_nodes(cur, [u["id"] for u in units])
        nodes = [*machines, *(p for group in parts.values() for p in group)]
        models = read_models_meters(cur, sorted({n["model_id"] for n in nodes if n["model_id"] is not None}))
        node_rows = _nodes_rows(cur, [n["id"] for n in nodes])
        last = _last_readings(cur, [n["id"] for n in nodes])

    def meters_of(node):
        meters = effective_meters(models.get(node["model_id"], []), node_rows[node["id"]])
        _add_last(meters, last, node["id"])
        return meters

    out_units = []
    for unit in units:
        out_machines = []
        for machine in (m for m in machines if m["unit_id"] == unit["id"]):
            part_rows = []
            for child in parts.get(machine["id"], []):
                part_rows.append(child)
                part_rows.extend(parts.get(child["id"], []))
            out_parts = [{"id": p["id"], "code": p["code"], "name": p["name"], "level": p["level"],
                          "meters": part_meters} for p in part_rows if (part_meters := meters_of(p))]
            own = meters_of(machine)
            if own or out_parts:
                out_machines.append({"id": machine["id"], "code": machine["code"], "name": machine["name"],
                                     "lifecycle": machine["lifecycle"], "meters": own, "parts": out_parts})
        if out_machines:
            out_units.append({"id": unit["id"], "code": unit["code"], "name": unit["name"], "machines": out_machines})
    return jsonify({"site": site, "units": out_units})


# ---------------------------------------------------------------------------
# The reading register (S050)
# ---------------------------------------------------------------------------

def _read_meter_types(cur, node_id):
    """The meter types with at least one active reading on the node (§ 5.1.2), in or out of force."""
    cur.execute(
        "SELECT t.id AS t_id, t.name AS t_name, t.unit AS t_unit, t.kind AS t_kind, t.decimals AS t_decimals,"
        " t.expected_answer AS t_expected_answer FROM meter_types t WHERE t.id IN ("
        "  SELECT meter_type_id FROM meter_readings WHERE equipment_id = %s AND removed_at IS NULL)", (node_id,))
    return [meter_type_of(row) for row in cur.fetchall()]


@meters_bp.route("/equipment/<int:node_id>/readings/register")
@require_perm("equipment:read")
def readings_register(node_id):
    """Every active reading of one node as a table (S050 § 5, § 6): a row per minute, newest first,
    a column per meter.  Paged by minute: the count, the page's minutes, then their readings — a
    fixed handful of queries, none per meter or per row (§ 5.3)."""
    wanted, errors = parse_meter_type_ids(request.args.get("meter_type_ids"))
    if errors:
        raise ApiError(errors[0]["message"], 400, errors[0]["field"])
    page = int_arg("page", 1, 1, MAX_PAGE)
    per_page = int_arg("per_page", HISTORY_PER_PAGE, 1, MAX_PER_PAGE)
    with get_db().cursor() as cur:
        _, node = load_node_for_user(cur, node_id, for_update=False, key="equipment:read")
        columns = register_columns(_meters_of(cur, node_id, node["model_id"]), _read_meter_types(cur, node_id))
        shown = shown_meter_ids(columns, wanted)
        total, readings = 0, []
        if shown:
            where = f"equipment_id = %s AND removed_at IS NULL AND meter_type_id IN ({_marks(shown)})"
            params = (node_id, *shown)
            total = count(cur, f"SELECT COUNT(DISTINCT taken_at) AS n FROM meter_readings WHERE {where}", params)
            cur.execute(f"SELECT DISTINCT taken_at FROM meter_readings WHERE {where}"
                        " ORDER BY taken_at DESC LIMIT %s OFFSET %s", (*params, per_page, (page - 1) * per_page))
            minutes = [row["taken_at"] for row in cur.fetchall()]
            if minutes:
                cur.execute("SELECT id, meter_type_id, value, taken_at, is_reset, limit_state FROM meter_readings"
                            f" WHERE {where} AND taken_at IN ({_marks(minutes)})", (*params, *minutes))
                readings = cur.fetchall()
    return jsonify({
        "node": {"id": node["id"], "code": node["code"], "name": node["name"], "level": node["level"],
                 "full_path": node_path(node)},
        "columns": columns, "shown": shown, "rows": rows_to_list(register_rows(readings, columns)),
        "total": total, "page": page, "per_page": per_page,
    })


# ---------------------------------------------------------------------------
# Meter readings on the ticket (S052)
# ---------------------------------------------------------------------------

def _node_or_none(cur, node_id):
    """The node under equipment:read, or None when it answers 404 (outside the user's units)."""
    try:
        return load_node_for_user(cur, node_id, for_update=False, key="equipment:read")[1]
    except ApiError as exc:
        if exc.status != 404:
            raise
        return None


def _ticket_path(cur, ticket):
    """The ticket's machine, then each node down to its part (§ 5.1 steps 2–4), root first.

    Every node of the path is in the machine's unit (equipment.NODE_JOINS' root unit), so access
    is all-or-nothing.  A ticket is visible through its own unit or its machine's
    (tickets._visible_condition), so a reader may see a ticket whose machine is outside their
    units: the machine then answers 404 and the path is empty, the card hidden, the ticket page
    unaffected (§ 7 decision 6).  A 403 is not caught: it cannot happen while equipment:read is
    "*", and must surface if the key ever narrows.

    A part moved to another machine since the raise is left out with its ancestors: its meters now
    belong to that machine.  Its 404 means the same (it can only fail when it left the machine's
    unit)."""
    machine = _node_or_none(cur, ticket["m_id"])
    if machine is None:
        return []
    if ticket["c_id"] is None:
        return [machine]
    part = _node_or_none(cur, ticket["c_id"])
    if part is None or machine_and_component(part)[0] != machine["id"]:
        return [machine]
    path = [machine]
    if part["gp_id"] is not None:
        # The part sits under a component-unit, itself under the machine
        path.append(load_node_for_user(cur, part["parent_id"], for_update=False, key="equipment:read")[1])
    path.append(part)
    return path


@meters_bp.route("/tickets/<int:ticket_id>/meters")
@require_perm("ticket:read")
def ticket_meters(ticket_id):
    """The ticket card's meters (§ 5.1, § 6): per node of the path with a meter in force, each
    meter's newest active reading at or before the ticket's time and its marked readings in the
    window before.  Plain reads, no locks; two reading queries for all nodes, none per meter."""
    with get_db().cursor() as cur:
        ticket = read_ticket(cur, ticket_id)
        at = ticket["occurred_at"]
        nodes = []
        for node in _ticket_path(cur, ticket):
            meters = _meters_of(cur, node["id"], node["model_id"])
            if meters:
                nodes.append((node, meters))
        node_ids = [node["id"] for node, _ in nodes]
        last = _last_readings(cur, node_ids, until=at)
        counts = _mark_counts(cur, node_ids, mark_window(at), at)
    out = []
    for node, meters in nodes:
        at_readings = {}
        for meter in meters:
            key = (node["id"], meter["meter_type"]["id"])
            if key in last:
                at_readings[key] = reading_out(last[key], meter["meter_type"]["kind"])
        out.append({
            "node": {"id": node["id"], "code": node["code"], "name": node["name"], "level": node["level"]},
            "meters": readings_at_ticket(meters, at_readings, counts, node["id"]),
        })
    return jsonify({"at": row_to_dict({"at": at})["at"], "mark_window_days": MARK_WINDOW_DAYS, "nodes": out})
