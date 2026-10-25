"""An equipment item's own property values (docs/steps/S044-property-overrides/1-brief.md § 5, § 6).

One item may differ from its model: a motor rewound to 5.5 kW, a pump with a larger impeller.
Its own value of a property of its class wins over the model's on that item only (ISO 14224:
the nameplate data are attributes of the equipment unit; the model is the default).  Each set,
change and clear writes one ``property`` line in the item's history.

Thin shell: properties_core holds the rules (check_values, item_changes, item_events); this
module checks access and the scrapped rule, locks, stores and writes the history.  It imports
from equipment.py and properties.py and is imported by neither (properties.py importing
equipment.py would be a cycle: equipment.py imports properties.py for the card).

Keys: the read needs equipment:read at the node's site; the write equipment:edit there (as a
node's own meters, S038), not the model keepers' union, so an engineer of another site never
edits this site's machine.

LOCK ORDER of the write (equipment.py's order, step (1), then properties.py's (2) and (3)):

    (1) the node's equipment row (load_node_for_user, FOR UPDATE)
    (2) the property_definitions rows named, ascending, FOR UPDATE
    (3) the class_properties rows of the node's class for those ids and their property_options
        rows, LOCK IN SHARE MODE; then the model's model_property_values rows for those ids,
        LOCK IN SHARE MODE, so the "(model)" side of the history is the value committed now
    (4) the equipment_property_values rows (insert, update or delete by key), then the
        equipment_events inserts

No cycle:
- properties.py's other writes lock a class or a model, then properties and options, and never
  equipment.  This write takes equipment first, then properties; no path takes a property row
  and then an equipment row.
- update_property holds a property row (2), then share-reads both value tables.  A write here
  waiting on that property row holds only the node (1), which update_property never needs.
- A model's values save takes the model, then (2), then its value rows; this write never takes
  the model, so its share read of those rows (3) waits at most for that save to commit.
- Removing a property from a class takes the class row, then deletes the link; this write
  share-locks the link but never takes the class row.  A remove that comes first makes this
  write refuse "This property is not on the class"; one that comes second waits for the link's
  share lock.
- The node's class and model come from its locked row: a node edit (equipment.py (1)) waits on
  the same row, so the class the links are read for is the committed one.
- The item's own rows are read plainly after (1): every writer of them holds (1), and the
  transaction's snapshot starts at load_node_for_user's plain read, after the lock.
- The GET and the equipment detail read plainly.
"""

from flask import Blueprint, jsonify

from api_common import ApiError
from auth_utils import require_perm
from db_helpers import get_db, transaction
from equipment import SCRAPPED_MESSAGE, load_node_for_user, write_events
from equipment_core import SCRAPPED
from properties import (
    checked_changes, item_values, linked_properties, lock_value_properties, model_values, option_labels,
    options_by_property, values_from_body, write_values,
)
from properties_core import item_changes, item_events, property_view, stored_value, value_display

item_properties_bp = Blueprint("item_properties", __name__)


def _item_properties(cur, node):
    """The dialog's rows (§ 5.5), by name: each active property of the node's class with the
    item's own value (or None), the model's value as text (or None) and, for a choice, its
    active options plus the stored inactive one."""
    properties = linked_properties(cur, node["class_id"])
    by_id = {prop["id"]: prop for prop in properties}
    options = options_by_property(cur, list(by_id))
    has_model = node["model_id"] is not None
    from_model = model_values(cur, node["model_id"]) if has_model else {}
    own = item_values(cur, node["id"])
    items = []
    # The model's rows give the order and the model's display; the own value is added to each
    for row in property_view(properties, from_model, option_labels(options)):
        prop = by_id[row["property_id"]]
        stored = own.get(prop["id"])
        stored_option = stored["option_id"] if stored else None
        items.append({
            "property_id": prop["id"],
            "name": prop["name"],
            "data_type": prop["data_type"],
            "unit": prop["unit"],
            "options": [o for o in options[prop["id"]] if o["active"] or o["id"] == stored_option],
            "value": stored_value(prop["data_type"], stored),
            "model_display": row["display"],
            "has_model": has_model,
        })
    return {"items": items}


@item_properties_bp.route("/equipment/<int:node_id>/properties")
@require_perm("equipment:read")
def list_item_properties(node_id):
    """Readable on a scrapped item too: the record stays as it was."""
    with get_db().cursor() as cur:
        _, node = load_node_for_user(cur, node_id, for_update=False, key="equipment:read")
        return jsonify(_item_properties(cur, node))


@item_properties_bp.route("/equipment/<int:node_id>/properties", methods=["PUT"])
@require_perm("equipment:edit")
def set_item_properties(node_id):
    """Set or clear the item's own values named in ``values``; the others stay.  "" or null
    clears (the row falls back to the model's value).  The first refusal by property name
    answers and nothing is saved.  Only real changes are written and logged (item_changes)."""
    values, property_ids = values_from_body()
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        # (1); 404; 403 unless equipment:edit at the node's site
        locked, node = load_node_for_user(cur, node_id, for_update=True, key="equipment:edit")
        if locked["lifecycle"] == SCRAPPED:
            raise ApiError(SCRAPPED_MESSAGE, 409)
        if property_ids:
            properties, options = lock_value_properties(cur, locked["class_id"], property_ids)   # (2), (3)
            has_model = locked["model_id"] is not None
            from_model = (model_values(cur, locked["model_id"], list(properties), " LOCK IN SHARE MODE")
                          if has_model else {})   # (3)
            stored = item_values(cur, node_id)
            changes = item_changes(checked_changes(values, properties, options, stored), stored)
            write_values(cur, "equipment_property_values", "equipment_id", node_id, changes)   # (4)
            labels = option_labels(options)
            model_displays = {pid: value_display(prop, from_model.get(pid), labels)
                              for pid, prop in properties.items()}
            write_events(cur, node_id, item_events(properties, changes, stored, model_displays, labels, has_model))
    with conn.cursor() as cur:
        # node was read after the lock (1), so its class and model are the locked row's
        return jsonify(_item_properties(cur, node))
