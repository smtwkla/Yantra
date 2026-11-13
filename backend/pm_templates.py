"""PM templates — the API (docs/steps/S104-pm-templates-one-path/1-brief.md § 5.1, § 5.2, § 5.6, § 6; R03.18).

The work of a PM plan is written once, on a template in *Masters › PM templates*: its name, who does it, whether an
engineer verifies each job, its trigger (a calendar interval, a meter type, or whichever comes first) and its items.
A machine gets the template through a link (pm_plans.py's *Attach*), and each machine's plan row holds only its own
facts.  A template change reaches every machine at its next job (TPM: improve the standard once; ISO 55001 § 8.2: one
recorded change); a job already started keeps the items it started with (S098).

Thin shell: pm_templates_core holds the rules (the fields, the merged trigger, the items and their sync, the words);
this module checks the keys, locks, reads the meter types the rules need and stores the result.  Nothing is
deleted: a template is deactivated, a removed item is set inactive (ISO 9001 § 7.5.3).

ACCESS (§ 5.8).  Read with equipment:read (held anywhere): a template is a site-less master, the plant's standard.
Written with pm_plan:edit held at any site (has_perm, the union; R03 Q18.4 a), as procedure:edit is for a class
lesson (S075); ``can_add`` / ``can_edit`` in the answers carry the same rule.  IT admin reads, writes nothing.

LOCK ORDER (equipment.py's numbers; § 5.9).  The template row is (6g): taken FOR UPDATE only by a template save,
first in its transaction, and LOCK IN SHARE MODE by pm_plans.py's *Attach*.
- Create: plain reads (the meter types) → the pm_templates insert (uq_pm_templates_name is the guard: two creates of
  one name wait on the unique entry and the second gets 1062 → 409) → the item inserts (shared foreign-key locks on
  the template, held, and the meter types) → commit.  A new template has no plans, so nothing is settled.
- Change (also {active} alone): (6g) the template FOR UPDATE, the first statement (404) → plain reads: the meter
  types, the active items (every item write holds (6g), so this read sees the newest committed rows) → update_row,
  the item inserts, updates and deactivations → commit.  Then § 5.6: each plan of the template, in id order, in its
  own transaction through pm_jobs.settle_one ((6e) → (1) shared → plain reads, where the template read sees the
  committed change → the job write), the daily run's function, with the engineer as the actor (BR1-03).
- The item check and the reads: plain, no lock.
No deadlock cycle: holding (6g) exclusive, a save waits only on the shared foreign-key locks of the meter types
(masters.py's meter-type writes never wait on a template row, so it is one-way: a lower number after (6g), as (6)
after (6e) is stated).  It never waits on a plan, a job, a node or a counter, and it settles plans only after its
commit, so no transaction holds (6g) and (6e) together.  *Attach* holds the node (1) shared, then (6g) shared;
nothing that holds (6g) exclusive waits on a node.  A job write reads the template plainly after its (6e) and (6f)
(S104 D10), never locking it.
"""

import logging

from flask import Blueprint, jsonify

import pm_jobs
from api_common import UNIQUE_KEY_ERRORS, ApiError, actor, clean_body
from auth_utils import has_perm, require_perm
from db_helpers import get_db, insert_row, marks, row_to_dict, transaction, update_row
from local_db import DBUnavailable, connection_lost, describe_error
from meters_core import format_number
from pm_templates_core import (
    DUPLICATE_NAME, ITEM_FIELDS, SCHEDULE_FIELDS, TEMPLATE_FIELDS, item_limits_text, sent_meter_type_ids,
    sync_items, template_changes, template_rules_error, trigger_text, validate_item, validate_items,
    validate_template,
)

logger = logging.getLogger(__name__)

pm_templates_bp = Blueprint("pm_templates", __name__)

EDIT_KEY = "pm_plan:edit"
READ_KEY = "equipment:read"

UNIQUE_KEY_ERRORS.update({
    "uq_pm_templates_name": ("name", DUPLICATE_NAME),
})

# (6g): the template row, every column (the merged rules and template_changes compare with it)
LOCK_TEMPLATE = "SELECT * FROM pm_templates WHERE id = %s FOR UPDATE"

_METER_TYPE_COLUMNS = "mt.name AS t_name, mt.unit AS t_unit, mt.kind AS t_kind, mt.decimals AS t_decimals"
# BR1-14: one count of machines, the template's plan rows with linked = 1 (a plan that does not apply counts)
_PLAN_COUNT = "(SELECT COUNT(*) FROM pm_plans pl WHERE pl.template_id = tp.id AND pl.linked = 1)"
_TEMPLATE_SELECT = (
    f"SELECT tp.*, {_METER_TYPE_COLUMNS}, cp.name AS created_by_name, up.name AS updated_by_name,"
    " (SELECT COUNT(*) FROM pm_template_items i WHERE i.template_id = tp.id AND i.active = 1) AS item_count,"
    f" {_PLAN_COUNT} AS plan_count"
    " FROM pm_templates tp LEFT JOIN meter_types mt ON mt.id = tp.meter_type_id"
    " LEFT JOIN people cp ON cp.username = tp.created_by"
    " LEFT JOIN people up ON up.username = tp.updated_by"
)
_ITEM_SELECT = (
    f"SELECT i.*, {_METER_TYPE_COLUMNS} FROM pm_template_items i LEFT JOIN meter_types mt ON mt.id = i.meter_type_id"
    " WHERE i.template_id = %s AND i.active = 1 ORDER BY i.position, i.id"
)
# § 5.6: the plans a template save settles: linked, or with an open job (an unlinked plan's leftover due job)
_TEMPLATE_PLANS = ("SELECT pl.id FROM pm_plans pl WHERE pl.template_id = %s AND (pl.linked = 1 OR EXISTS"
                   " (SELECT 1 FROM pm_jobs j WHERE j.open_plan_id = pl.id)) ORDER BY pl.id")

# A template before the body: the columns a create does not send take their defaults (the CHECKs' null-ness)
_NEW_TEMPLATE = {field: None for field in TEMPLATE_FIELDS}


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------

def item_out(item, meter_type):
    """One template item as the page shows it (§ 6)."""
    return {
        "id": item["id"], "position": item.get("position"), "item_type": item["item_type"], "text": item["text"],
        "help_text": item["help_text"], "photo": item["photo"], "reading_kind": item["reading_kind"],
        "unit": item["unit"], "min_value": format_number(item["min_value"]),
        "max_value": format_number(item["max_value"]), "meter_type": meter_type,
        "limits_text": item_limits_text(item, meter_type),
    }


def template_items(cur, template_id):
    """The template's active items as the page shows them, in their order."""
    cur.execute(_ITEM_SELECT, (template_id,))
    return [item_out(row, pm_jobs.meter_type_out(row)) for row in cur.fetchall()]


def _summary_out(row):
    return {"id": row["id"], "name": row["name"], "trigger_text": trigger_text(row, pm_jobs.meter_type_out(row)),
            "item_count": row["item_count"], "plan_count": row["plan_count"], "active": bool(row["active"])}


def _detail(cur, template_id):
    cur.execute(f"{_TEMPLATE_SELECT} WHERE tp.id = %s", (template_id,))
    row = cur.fetchone()
    if row is None:
        raise ApiError("Not found", 404)
    plain = row_to_dict(row)
    return {
        "id": row["id"], "name": row["name"], "performer": row["performer"],
        "needs_verification": bool(row["needs_verification"]), "trigger_kind": row["trigger_kind"],
        "calendar_every": row["calendar_every"], "calendar_unit": row["calendar_unit"],
        "meter_type": pm_jobs.meter_type_out(row), "meter_every": format_number(row["meter_every"]),
        "trigger_text": trigger_text(row, pm_jobs.meter_type_out(row)), "active": bool(row["active"]),
        "items": template_items(cur, template_id), "plan_count": row["plan_count"],
        "created_at": plain["created_at"], "created_by_name": plain["created_by_name"] or plain["created_by"],
        "updated_at": plain["updated_at"],
        "updated_by_name": (plain["updated_by_name"] or plain["updated_by"]) if plain["updated_by"] else None,
        "can_edit": has_perm(EDIT_KEY),
    }


@pm_templates_bp.route("/templates", strict_slashes=False)
@require_perm(READ_KEY)
def list_templates():
    """*Masters › PM templates* (§ 6, BR1-19): the active templates in ``items``, the inactive ones in ``inactive``,
    each by name, in one request."""
    with get_db().cursor() as cur:
        cur.execute(f"{_TEMPLATE_SELECT} ORDER BY tp.name, tp.id")
        rows = cur.fetchall()
    return jsonify({"items": [_summary_out(row) for row in rows if row["active"]],
                    "inactive": [_summary_out(row) for row in rows if not row["active"]],
                    "can_add": has_perm(EDIT_KEY)})


@pm_templates_bp.route("/templates/<int:template_id>")
@require_perm(READ_KEY)
def get_template(template_id):
    with get_db().cursor() as cur:
        return jsonify(_detail(cur, template_id))


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------

def _meter_types(cur, ids):
    """The meter types the body names, plain (their writers never wait on a template)."""
    if not ids:
        return {}
    cur.execute(f"SELECT id, name, unit, kind, decimals FROM meter_types WHERE id IN ({marks(ids)})", list(ids))
    return {row["id"]: row for row in cur.fetchall()}


def _check_rules(merged, meter_types):
    error = template_rules_error(merged, meter_types.get(merged["meter_type_id"]))
    if error:
        raise ApiError(error[1], 400, error[0])


def _clean_items(raw, meter_types):
    items, error = validate_items(raw, meter_types)
    if error:
        raise ApiError(error[1], 400, error[0])
    return items


def _insert_item(cur, template_id, item):
    insert_row(cur, "pm_template_items", {"template_id": template_id, **item}, actor())


def settle_template_plans(conn, template_id, keep_reschedule):
    """§ 5.6: after the save's commit, each plan of the template in its own transaction (pm_jobs.settle_one, the
    daily run's function, with the engineer as the actor; BR1-03) -> ``(settled, failed)`` counts.  One plan's fault
    is logged and the others go on, as the daily run; the next morning's run settles it.  A lost connection ends the
    loop and raises DBUnavailable (a 503; the template stands, BR1-12; CR5-01: the pool's own error is an
    InterfaceError or an OperationalError, neither of which the app answers as a 503)."""
    with conn.cursor() as cur:
        cur.execute(_TEMPLATE_PLANS, (template_id,))
        plan_ids = [row["id"] for row in cur.fetchall()]
    conn.commit()   # ends the plain read's snapshot, so each plan's transaction starts fresh
    settled = failed = 0
    for plan_id in plan_ids:
        try:
            pm_jobs.settle_one(conn, plan_id, actor(), keep_reschedule=keep_reschedule)
        except Exception as exc:   # noqa: BLE001 — one plan's fault must not stop the others
            if connection_lost(conn, exc):
                # CR6-01: app.py logs the 503's message only; the cause (a 2013 behind PyMySQL's closed-socket
                # InterfaceError) is logged here with its traceback, as worker._log_lost does
                logger.error("PM template %s: the database connection was lost while settling plan %s",
                             template_id, plan_id, exc_info=exc)
                raise DBUnavailable(describe_error(exc)) from exc
            logger.exception("PM template %s: settling plan %s failed", template_id, plan_id)
            failed += 1
            continue
        settled += 1
    return settled, failed


@pm_templates_bp.route("/template-item-check", methods=["POST"])
@require_perm(EDIT_KEY)
def check_item():
    """One item judged by the template save's own rules, writing nothing (S096 D2): the dialog shows a refusal beside
    its field at once.  Body ``{item}``; the answer is the clean item in the page's shape (``id`` as sent)."""
    body = clean_body(lambda raw, _creating: (raw, []), creating=False)
    item = body.get("item")
    if not isinstance(item, dict):
        raise ApiError("item must be an object", 400, "item")
    with get_db().cursor() as cur:
        meter_types = _meter_types(cur, sent_meter_type_ids({"items": [item]}))
    clean, errors = validate_item(item, meter_types)
    if errors:
        raise ApiError(errors[0]["message"], 400, errors[0]["field"])
    meter_type = meter_types.get(clean["meter_type_id"]) if clean["meter_type_id"] else None
    return jsonify(item_out({**clean, "position": None}, meter_type and {
        key: meter_type[key] for key in ("id", "name", "unit", "kind", "decimals")}))


@pm_templates_bp.route("/templates", methods=["POST"], strict_slashes=False)
@require_perm(EDIT_KEY)
def create_template():
    """A template with its items (§ 5.1, § 5.2), in one transaction; pm_plan:edit held at any site."""
    clean = clean_body(validate_template, creating=True)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        meter_types = _meter_types(cur, sent_meter_type_ids(clean))
        merged = {**_NEW_TEMPLATE, **clean}
        _check_rules(merged, meter_types)
        items = _clean_items(clean["items"], meter_types)
        template_id = insert_row(cur, "pm_templates", {
            field: merged[field] for field in TEMPLATE_FIELDS if field != "active"}, actor())
        for position, item in enumerate(items, start=1):
            # A new template's items are all new: an id sent with one (a hand-made request) is not used
            _insert_item(cur, template_id, {**{field: item[field] for field in ITEM_FIELDS}, "position": position})
    with conn.cursor() as cur:
        detail = _detail(cur, template_id)
    return jsonify({**detail, "plans_settled": 0, "plans_failed": 0}), 201


@pm_templates_bp.route("/templates/<int:template_id>", methods=["PUT"])
@require_perm(EDIT_KEY)
def change_template(template_id):
    """Any subset of the template's fields; ``items`` replaces the list, synced by id; ``{active}`` alone deactivates
    or reactivates.  A field equal to the stored one is not written, and a change of nothing writes nothing.  After
    the commit, every plan of the template is settled (§ 5.6), also when nothing changed (a repeated PUT after a
    503 settles them again, BR1-12)."""
    clean = clean_body(validate_template, creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        cur.execute(LOCK_TEMPLATE, (template_id,))   # (6g), the first statement
        locked = cur.fetchone()
        if locked is None:
            raise ApiError("Not found", 404)
        merged = {**locked, **clean}
        meter_types = _meter_types(cur, sorted({*sent_meter_type_ids(clean), *(
            [merged["meter_type_id"]] if merged["meter_type_id"] is not None else [])}))
        _check_rules(merged, meter_types)
        ops = None
        if "items" in clean:
            items = _clean_items(clean["items"], meter_types)
            cur.execute("SELECT id, position, " + ", ".join(ITEM_FIELDS) + " FROM pm_template_items"
                        " WHERE template_id = %s AND active = 1 ORDER BY position, id", (template_id,))
            ops, message = sync_items(cur.fetchall(), items)
            if message:
                raise ApiError(message, 400, "items")
        changes = template_changes(locked, clean)
        schedule_changed = any(field in changes for field in SCHEDULE_FIELDS)
        update_row(cur, "pm_templates", template_id, changes, actor())
        if ops is not None:
            for item in ops["insert"]:
                _insert_item(cur, template_id, item)
            for item_id, item_changes in ops["update"]:
                update_row(cur, "pm_template_items", item_id, item_changes, actor())
            for item_id in ops["deactivate"]:
                update_row(cur, "pm_template_items", item_id, {"active": 0}, actor())
    # S101 D4: a change of the schedule drops the reschedule of every plan's open job; any other change keeps it
    settled, failed = settle_template_plans(conn, template_id, keep_reschedule=not schedule_changed)
    with conn.cursor() as cur:
        detail = _detail(cur, template_id)
    return jsonify({**detail, "plans_settled": settled, "plans_failed": failed})
