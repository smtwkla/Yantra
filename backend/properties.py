"""Equipment properties — the property master, its options, the class links and the models'
values (docs/steps/S043-equipment-properties/1-brief.md § 5, § 6).  Read by everyone
(masters:read); kept by equipment:edit, the keepers of classes and models (U3), checked as the
union over the user's sites like the other masters, since a property is the same at every site.

Thin shell: properties_core holds the rules; this module fetches, locks and stores.

LOCK ORDER — one order for every write here, each step taken only when the write needs it:

    (1) the equipment_classes row, or the equipment_models row
    (2) the property_definitions row(s), by id, ascending
    (3) the property_options row

- Edit a property: (2).  The "options or values exist" checks are locking reads, so an option
  or value saved at the same moment is seen or waits: its insert takes a shared lock on the
  property row through the FK, which the edit holds exclusively.
- Add or edit an option: (2), then (3) for an edit (the option's property, fixed, read plainly).
- Add properties to a class: (1) the class, then (2) each property, ascending, FOR UPDATE; a
  choice's active options are read LOCK IN SHARE MODE; then INSERT IGNORE the links.
- Remove a property from a class: (1) the class, then delete the link.
- Set a model's values: (1) the model (its class never changes, S012), then (2) the properties
  named, ascending, then a locking read of their class links and (3) their options; upsert or
  delete the value rows.
- masters.py takes manufacturer → model → class → type and equipment.py model (4) → class (5);
  no route here locks a manufacturer, a type or equipment, and none takes a class and a model
  together, so no lock cycle spans the modules.  The tables of (2) and (3) are new (v31):
  nothing else locks them.
- S038's meters: equipment.py's order has (4b) the meter type and (5a) the type, and masters.py
  records a model's meters as model → meter type → model_meters.  No route here locks a meter
  type or a model_meters row, and a model's meters and its property values both take the model
  row first, so S038 joins no cycle.
"""

from flask import Blueprint, jsonify, request

from api_common import UNIQUE_KEY_ERRORS, ApiError, actor, clean_body
from auth_utils import require_perm
from db_helpers import count, fetch_one, get_db, insert_row, rows_to_list, transaction, update_row
from properties_core import (
    CHOICE, CHOOSE_ACTIVE_PROPERTIES, ONLY_CHOICE_HAS_OPTIONS, can_link, check_model_values, parse_property_ids,
    parse_value_keys, property_changes, property_view, validate_option, validate_property,
)

properties_bp = Blueprint("properties", __name__)

# Named UNIQUE indexes (migration v31) -> the field to flag and a plain message (BR1-05)
UNIQUE_KEY_ERRORS.update({
    "uq_property_definitions_name": ("name", "A property with this name exists"),
    "uq_property_options_label": ("label", "An option with this label exists"),
})

_PROPERTY_SELECT = (
    "SELECT p.*,"
    " (SELECT COUNT(*) FROM class_properties cp WHERE cp.property_id = p.id) AS class_count,"
    " (SELECT COUNT(*) FROM model_property_values v WHERE v.property_id = p.id) AS value_count"
    " FROM property_definitions p"
)
_OPTION_COLUMNS = "id, property_id, label, active"
_VALUE_COLUMNS = "property_id, value_number, value_text, value_bool, option_id"


def _body():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ApiError("Request body must be a JSON object", 400)
    return body


def _options_by_property(cur, property_ids, lock=""):
    """``{property_id: [{id, label, active}]}`` in the order they were made; ``lock`` a locking clause."""
    if not property_ids:
        return {}
    cur.execute(f"SELECT {_OPTION_COLUMNS} FROM property_options"
                f" WHERE property_id IN ({', '.join(['%s'] * len(property_ids))}) ORDER BY id{lock}",
                list(property_ids))
    options = {pid: [] for pid in property_ids}
    for row in cur.fetchall():
        options[row["property_id"]].append({"id": row["id"], "label": row["label"], "active": row["active"]})
    return options


def _property_out(cur, property_id):
    record = fetch_one(cur, f"{_PROPERTY_SELECT} WHERE p.id = %s", (property_id,))
    record["options"] = _options_by_property(cur, [property_id])[property_id]
    return record


# ---------------------------------------------------------------------------
# The property master (§ 6.1)
# ---------------------------------------------------------------------------

@properties_bp.route("/properties")
@require_perm("masters:read")
def list_properties():
    where = "" if request.args.get("include_inactive") == "1" else " WHERE p.active = 1"
    with get_db().cursor() as cur:
        cur.execute(f"{_PROPERTY_SELECT}{where} ORDER BY p.name")
        items = rows_to_list(cur.fetchall())
        options = _options_by_property(cur, [item["id"] for item in items])
        for item in items:
            item["options"] = options[item["id"]]
        return jsonify({"items": items})


def _refuse(refusal):
    field, message, status = refusal
    raise ApiError(message, status, field)


@properties_bp.route("/properties", methods=["POST"])
@require_perm("equipment:edit")
def create_property():
    clean = clean_body(validate_property, creating=True)
    changes, refusal = property_changes(None, clean)
    if refusal:
        _refuse(refusal)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        property_id = insert_row(cur, "property_definitions", changes, actor())
        for label in clean.get("options", []):
            insert_row(cur, "property_options", {"property_id": property_id, "label": label}, actor())
    with conn.cursor() as cur:
        return jsonify(_property_out(cur, property_id)), 201


def _lock_property(cur, property_id):
    cur.execute("SELECT id, name, data_type, unit, active FROM property_definitions WHERE id = %s FOR UPDATE",
                (property_id,))   # (2)
    row = cur.fetchone()
    if row is None:
        raise ApiError("Not found", 404)
    return row


@properties_bp.route("/properties/<int:property_id>", methods=["PUT"])
@require_perm("equipment:edit")
def update_property(property_id):
    """Edit any field.  The data type is fixed once the property has an option or a value, the
    unit once it has a value (§ 5.1); a type leaving *number* drops its unit in the same write."""
    clean = clean_body(validate_property, creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        stored = _lock_property(cur, property_id)
        has_options = bool(count(cur, "SELECT COUNT(*) AS n FROM property_options WHERE property_id = %s"
                                      " LOCK IN SHARE MODE", (property_id,)))
        cur.execute("SELECT 1 FROM model_property_values WHERE property_id = %s LIMIT 1 LOCK IN SHARE MODE",
                    (property_id,))
        has_values = cur.fetchone() is not None
        changes, refusal = property_changes(stored, clean, has_options, has_values)
        if refusal:
            _refuse(refusal)
        update_row(cur, "property_definitions", property_id, changes, actor())
    with conn.cursor() as cur:
        return jsonify(_property_out(cur, property_id))


def _option_out(cur, option_id):
    return fetch_one(cur, f"SELECT {_OPTION_COLUMNS} FROM property_options WHERE id = %s", (option_id,))


@properties_bp.route("/properties/<int:property_id>/options", methods=["POST"])
@require_perm("equipment:edit")
def create_option(property_id):
    clean = clean_body(validate_option, creating=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        if _lock_property(cur, property_id)["data_type"] != CHOICE:
            raise ApiError(ONLY_CHOICE_HAS_OPTIONS, 400, "label")
        option_id = insert_row(cur, "property_options", {**clean, "property_id": property_id}, actor())
    with conn.cursor() as cur:
        return jsonify(_option_out(cur, option_id)), 201


@properties_bp.route("/property-options/<int:option_id>", methods=["PUT"])
@require_perm("equipment:edit")
def update_option(option_id):
    """Rename (every value shows the new label) or (de)activate.  An inactive option cannot be
    newly picked; a stored value keeps it (§ 5.4).  No delete."""
    clean = clean_body(validate_option, creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        # A plain read of the property is safe (an option's property never changes) and lets
        # the property be locked first: the (2) → (3) order
        stored = fetch_one(cur, "SELECT property_id FROM property_options WHERE id = %s", (option_id,))
        if stored is None:
            raise ApiError("Not found", 404)
        _lock_property(cur, stored["property_id"])
        cur.execute("SELECT id FROM property_options WHERE id = %s FOR UPDATE", (option_id,))   # (3)
        update_row(cur, "property_options", option_id, clean, actor())
    with conn.cursor() as cur:
        return jsonify(_option_out(cur, option_id))


# ---------------------------------------------------------------------------
# Class links (§ 6.2, U6): add several at once, remove one
# ---------------------------------------------------------------------------

def _lock_class(cur, class_id):
    cur.execute("SELECT id FROM equipment_classes WHERE id = %s FOR UPDATE", (class_id,))   # (1)
    if cur.fetchone() is None:
        raise ApiError("Not found", 404)


def _class_properties(cur, class_id):
    cur.execute("SELECT p.id AS property_id, p.name, p.data_type, p.unit, p.active FROM class_properties cp"
                " JOIN property_definitions p ON p.id = cp.property_id WHERE cp.class_id = %s ORDER BY p.name",
                (class_id,))
    return {"items": cur.fetchall()}


@properties_bp.route("/equipment-classes/<int:class_id>/properties")
@require_perm("masters:read")
def list_class_properties(class_id):
    """The class's properties by name, inactive ones included (the table marks them)."""
    with get_db().cursor() as cur:
        if fetch_one(cur, "SELECT id FROM equipment_classes WHERE id = %s", (class_id,)) is None:
            raise ApiError("Not found", 404)
        return jsonify(_class_properties(cur, class_id))


@properties_bp.route("/equipment-classes/<int:class_id>/properties", methods=["POST"])
@require_perm("equipment:edit")
def add_class_properties(class_id):
    """Add the properties named; one already on the class is skipped.  Each must be active, and
    a choice must have an active option (§ 5.1).  An inactive class may get them, as an inactive
    model keeps its values (BR1-08)."""
    property_ids, message = parse_property_ids(_body().get("property_ids"))
    if message:
        raise ApiError(message, 400, "property_ids")
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        _lock_class(cur, class_id)
        placeholders = ", ".join(["%s"] * len(property_ids))
        cur.execute(f"SELECT id, data_type, active FROM property_definitions WHERE id IN ({placeholders})"
                    " ORDER BY id FOR UPDATE", property_ids)   # (2), ascending
        found = cur.fetchall()
        options = _options_by_property(cur, property_ids, " LOCK IN SHARE MODE")
        if len(found) != len(property_ids) or not all(
                can_link(prop, sum(1 for o in options[prop["id"]] if o["active"])) for prop in found):
            raise ApiError(CHOOSE_ACTIVE_PROPERTIES, 400, "property_ids")
        cur.executemany("INSERT IGNORE INTO class_properties (class_id, property_id, created_by) VALUES (%s, %s, %s)",
                        [(class_id, pid, actor()) for pid in property_ids])
    with conn.cursor() as cur:
        return jsonify(_class_properties(cur, class_id))


@properties_bp.route("/equipment-classes/<int:class_id>/properties/<int:property_id>", methods=["DELETE"])
@require_perm("equipment:edit")
def remove_class_property(class_id, property_id):
    """Remove the link only: the models' values stay, shown again when it is added back (§ 5.4)."""
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        _lock_class(cur, class_id)
        cur.execute("DELETE FROM class_properties WHERE class_id = %s AND property_id = %s", (class_id, property_id))
        if cur.rowcount == 0:
            raise ApiError("Not found", 404)
    with conn.cursor() as cur:
        return jsonify(_class_properties(cur, class_id))


# ---------------------------------------------------------------------------
# A model's values (§ 5.3) and the equipment page's card (§ 6.3)
# ---------------------------------------------------------------------------

def _linked_properties(cur, class_id):
    """The active properties of the class, by name."""
    cur.execute("SELECT p.id, p.name, p.data_type, p.unit FROM class_properties cp"
                " JOIN property_definitions p ON p.id = cp.property_id"
                " WHERE cp.class_id = %s AND p.active = 1 ORDER BY p.name", (class_id,))
    return cur.fetchall()


def _model_values(cur, model_id):
    cur.execute(f"SELECT {_VALUE_COLUMNS} FROM model_property_values WHERE model_id = %s", (model_id,))
    return {row["property_id"]: row for row in cur.fetchall()}


def _card_rows(cur, class_id, model_id):
    """The linked active properties with the model's values -> (properties, values, options, view rows)."""
    properties = _linked_properties(cur, class_id)
    # A component-unit may have no model (S033): its rows show no value (BS1-01)
    values = _model_values(cur, model_id) if model_id is not None else {}
    options = _options_by_property(cur, [p["id"] for p in properties])
    labels = {o["id"]: o["label"] for opts in options.values() for o in opts}
    return properties, values, options, property_view(properties, values, labels)


def equipment_properties(cur, class_id, model_id):
    """The Properties card of an equipment item (§ 6.3): its class's active properties with its
    model's values, ``source`` "model" or None (S044 adds "item").  ``model_id`` None (a
    component-unit without a model, S033): every row has no value."""
    return _card_rows(cur, class_id, model_id)[3]


def _model_properties(cur, model_id, class_id):
    """The model dialog's rows: the card's, plus each property's data type and, for a choice,
    its active options and the stored one if inactive."""
    properties, values, options, rows = _card_rows(cur, class_id, model_id)
    by_id = {prop["id"]: prop for prop in properties}
    items = []
    for row in rows:
        prop = by_id[row["property_id"]]
        stored = values.get(prop["id"])
        stored_option = stored["option_id"] if stored else None
        items.append({
            "property_id": prop["id"],
            "name": prop["name"],
            "data_type": prop["data_type"],
            "unit": prop["unit"],
            "options": [o for o in options[prop["id"]] if o["active"] or o["id"] == stored_option],
            "value": row["value"],
            "display": row["display"],
        })
    return {"items": items}


def _model_class(cur, model_id, lock=""):
    cur.execute(f"SELECT id, class_id FROM equipment_models WHERE id = %s{lock}", (model_id,))
    model = cur.fetchone()
    if model is None:
        raise ApiError("Not found", 404)
    return model["class_id"]


@properties_bp.route("/equipment-models/<int:model_id>/properties")
@require_perm("masters:read")
def list_model_properties(model_id):
    with get_db().cursor() as cur:
        return jsonify(_model_properties(cur, model_id, _model_class(cur, model_id)))


@properties_bp.route("/equipment-models/<int:model_id>/properties", methods=["PUT"])
@require_perm("equipment:edit")
def set_model_properties(model_id):
    """Set or clear the values named in ``values``; the others stay.  The first refusal by
    property name answers and nothing is saved (§ 5.3).  An inactive model may be edited: its
    data stays right for the equipment that uses it."""
    values = _body().get("values")
    property_ids, refusal = parse_value_keys(values)
    if refusal:
        raise ApiError(refusal[1], 400, refusal[0])
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        class_id = _model_class(cur, model_id, " FOR UPDATE")   # (1)
        if property_ids:
            placeholders = ", ".join(["%s"] * len(property_ids))
            cur.execute(f"SELECT id, name, data_type, active FROM property_definitions WHERE id IN ({placeholders})"
                        " ORDER BY id FOR UPDATE", property_ids)   # (2), ascending
            found = {row["id"]: row for row in cur.fetchall()}
            cur.execute(f"SELECT property_id FROM class_properties WHERE class_id = %s"
                        f" AND property_id IN ({placeholders}) LOCK IN SHARE MODE", [class_id, *property_ids])
            linked = {row["property_id"] for row in cur.fetchall()}
            properties = {pid: {**row, "linked": pid in linked} for pid, row in found.items()}
            options = _options_by_property(cur, list(found), " LOCK IN SHARE MODE")   # (3)
            changes, refusal = check_model_values(values, properties, options, _model_values(cur, model_id))
            if refusal:
                raise ApiError(refusal[1], 400, refusal[0])
            for property_id, columns in changes:
                if columns is None:
                    cur.execute("DELETE FROM model_property_values WHERE model_id = %s AND property_id = %s",
                                (model_id, property_id))
                    continue
                cur.execute(
                    "INSERT INTO model_property_values (model_id, property_id, value_number, value_text, value_bool,"
                    " option_id, updated_at, updated_by) VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s)"
                    " ON DUPLICATE KEY UPDATE value_number = VALUES(value_number), value_text = VALUES(value_text),"
                    " value_bool = VALUES(value_bool), option_id = VALUES(option_id), updated_at = NOW(),"
                    " updated_by = VALUES(updated_by)",
                    (model_id, property_id, columns["value_number"], columns["value_text"], columns["value_bool"],
                     columns["option_id"], actor()))
    with conn.cursor() as cur:
        return jsonify(_model_properties(cur, model_id, class_id))
