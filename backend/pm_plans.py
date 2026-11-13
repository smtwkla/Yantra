"""PM plans on a machine — the API (docs/steps/S104-pm-templates-one-path/1-brief.md § 5.4, § 5.5, § 6; R03.18;
S096 before it).  Since S104 a machine gets a PM plan only through a PM template linked to it: the work (items,
trigger, performer, verification) is the template's (pm_templates.py), and the machine's plan row holds only its own
facts: who the jobs are assigned to, *Last done* before Yantra, and whether the template still reaches it
(``linked``).  This module serves the equipment page's PM card, the plan page, *Attach PM template* (one machine; R03.19
adds class, type and model links), the plan settings and *Remove from this machine*, and keeps the plan rows in step
with the links (``sync_node``).  Each write settles the plan's one open job (pm_jobs.settle_plan_job, S097).

Thin shell: pm_links_core says which templates reach a node and what to do with its plan rows; pm_plans_core holds the
plan row's rules; pm_jobs resolves the meters a template needs on the machine (§ 5.3).  Nothing is deleted: a link is
set inactive, a plan row unlinked, so attaching again brings the same row back with its assignee, seed and jobs
(R03 Q19.1 a; ISO 9001 § 7.5.3).

ACCESS (§ 5.8).  Read with equipment:read: the node through load_node_for_user, 404 outside the user's units (a
missing plan is the same 404).  Written with pm_plan:edit (site-scoped): at the node's current site, 403 naming the
site; a scrapped node is read-only (409).  The answers' can_add / can_edit / can_remove carry the same rule.

LOCK ORDER (equipment.py's numbers; § 5.9).  The database runs REPEATABLE READ: a locking read sees the newest
committed row, a plain read the snapshot of the transaction's first plain read.  Per transaction this module takes at
most one exclusive row lock of its own (the plan (6e) or a link row), then only shared locks.
- Attach: (1) the node LOCK IN SHARE MODE, the first statement (404) → (6g) the template LOCK IN SHARE MODE (404;
  its ``active`` decides the 409) → plain reads: access (404 / 403), scrapped from the locked node (409), the active
  link → the link insert (uq_pm_template_links_open is the guard: 1062 → 409 "already attached") → commit.  Then
  sync_node.  The template's shared lock makes a concurrent deactivation either wait for the attach (its
  after-commit settle then sees the new plan) or commit first (the attach then sees it inactive).
- Remove: (6e) the plan FOR UPDATE (404) → (1) the node shared → plain: access, scrapped, the link → the link's
  UPDATE (its own row by id; nothing else locks a link) → commit → sync_node.
- sync_node: the node's links and plans read plainly (their own snapshot, committed), then one transaction per plan:
  make: (1) shared → the pm_plans insert (shared foreign-key locks on the node and the template;
  uq_pm_plans_template is the guard) → settle_plan_job; on its 1062 the make is rolled back and the row, read
  plainly, takes the relink path (BR1-02).  Relink / unlink: (6e) → (1) shared → plain → the linked (and, on a
  relink, linked_at) UPDATE → settle_plan_job.  Each is the S097 daily run's shape.
- Plan settings: (6e) → (1) shared → plain: access, scrapped, the plan with its template (PLAN_SELECT), the meter
  match, the assignee → update_row → settle_plan_job.
- The reads and the attach preview: plain, no lock.
settle_plan_job takes (6) the PM: counter last, for a new job only (pm_jobs.py's note).  No deadlock cycle: (6e) is
taken first or right after (1) shared by an attach-free path; nothing holds a plan and then waits on a template
(the template save settles its plans only after its commit), and the node writers never wait on a plan or a
template.  The scrap's top-down subtree lock against a plan write holding a part shared is the accepted case
S096 named (InnoDB rolls one back, 1213).
"""

import pymysql
from flask import Blueprint, jsonify

import pm_jobs
from api_common import MAX_PER_PAGE, ApiError, actor, clean_body, int_arg
from auth_utils import has_perm_at, require_perm
from config_rbac import ASSIGNABLE_ROLES
from db_helpers import get_db, insert_row, marks, row_to_dict, transaction, update_row
from equipment import SCRAPPED_MESSAGE, load_node_for_user, node_path
from equipment_core import SCRAPPED
from meters_core import format_number
from pm_jobs_core import seed_matches
from pm_links_core import EQUIPMENT, missing_text, plan_actions, reaching_templates
from pm_plans_core import (
    plan_changes, plan_settings_error, schedule_changed, validate_attach, validate_plan_settings,
)
from pm_templates import template_items
from pm_templates_core import trigger_text
from tickets import ASSIGNEE_AT_SITE, person_at_site

pm_plans_bp = Blueprint("pm_plans", __name__)

EDIT_KEY = "pm_plan:edit"
READ_KEY = "equipment:read"
ER_DUP_ENTRY = 1062

TEMPLATE_INACTIVE = "This template is inactive. Reactivate it in Masters › PM templates first."
ALREADY_ATTACHED = "This template is already attached to this machine."
NO_LINK_HERE = "This plan does not come from a link to this machine."


# (6e) and (1) shared: the daily run (pm_jobs.generate) takes the same two statements (S097)
_LOCK_PLAN = pm_jobs.LOCK_PLAN
_SHARE_NODE = pm_jobs.SHARE_NODE
# (6g) shared: Attach (§ 5.9 step 3)
_SHARE_TEMPLATE = "SELECT id, active FROM pm_templates WHERE id = %s LOCK IN SHARE MODE"

# A plan with its template (pm_jobs.PLAN_COLUMNS and PLAN_FROM, so plan_resolutions reads the same row; CR1-06), the
# template's trigger meter type, its active item count, the assignee (with their role at the site given as the one
# parameter) and its writers' names.  The card and the detail share it.
_PLAN_SELECT = (
    "SELECT " + pm_jobs.PLAN_COLUMNS + ", mt.name AS t_name, mt.unit AS t_unit, mt.kind AS t_kind,"
    " mt.decimals AS t_decimals, a.name AS a_name, ms.role AS a_role,"
    " cp.name AS created_by_name, up.name AS updated_by_name,"
    " (SELECT COUNT(*) FROM pm_template_items i WHERE i.template_id = tp.id AND i.active = 1) AS item_count"
    + pm_jobs.PLAN_FROM +
    " LEFT JOIN meter_types mt ON mt.id = tp.meter_type_id"
    " LEFT JOIN people a ON a.id = pl.assignee_id"
    " LEFT JOIN memberships ms ON ms.person_id = pl.assignee_id AND ms.site_id = %s"
    " LEFT JOIN people cp ON cp.username = pl.created_by"
    " LEFT JOIN people up ON up.username = pl.updated_by"
)


def _can_write(node):
    return has_perm_at(EDIT_KEY, node["site_id"]) and node["lifecycle"] != SCRAPPED


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------

def _assignee_out(row):
    if row["assignee_id"] is None:
        return None
    return {"id": row["assignee_id"], "name": row["a_name"], "role": row["a_role"]}


# Where a plan comes from (§ 5.10).  S104 has one source, the link to the machine itself; R03.19 adds the class,
# type and model links ("Reaches this machine from: Class …")
_SOURCE = {"kind": EQUIPMENT, "label": "This machine"}


def _common_out(row, resolution, shared):
    meter_type = pm_jobs.meter_type_out(row)
    return {
        "id": row["id"], "template": {"id": row["template_id"], "name": row["title"],
                                      "active": bool(row["template_active"])},
        "title": row["title"], "source": dict(_SOURCE), "performer": row["performer"],
        "assignee": _assignee_out(row), "trigger_text": trigger_text(row, meter_type),
        "item_count": row["item_count"], "linked": bool(row["linked"]),
        "meters": pm_jobs.plan_meters_out(row, resolution, shared),
        "applies": not resolution["missing"],
        "missing_text": (missing_text([shared["meter_types"][t]["name"] for t in resolution["missing"]],
                                      row["node_code"]) if resolution["missing"] else None),
        "stop_remark": resolution["stop"],
    }


def _summary_out(row, node_id, resolution, shared, schedule):
    """A plan as the card lists it (§ 6)."""
    return {**_common_out(row, resolution, shared), "equipment": {"id": row["equipment_id"], "code": row["node_code"]},
            "own": row["equipment_id"] == node_id, "schedule": schedule}


def _seed_shown(row, resolution):
    """S104 A1.6.3: the stored *Last done* meter value is answered only while the plan's trigger resolves to the
    meter it was entered for (pm_jobs_core.seed_matches); otherwise it stays stored, hidden and unused (AD6), and the
    page shows an empty field."""
    return format_number(row["last_done_meter"]) if seed_matches(row, resolution["trigger"]) else None


def _plan_out(cur, row, node, resolution, shared):
    """One plan as its page shows it (§ 6)."""
    plain = row_to_dict(row)
    meter_type = pm_jobs.meter_type_out(row)
    out = _common_out(row, resolution, shared)
    out["template"].update(
        performer=row["performer"], needs_verification=bool(row["needs_verification"]),
        trigger_text=out["trigger_text"], meter_type=meter_type, items=template_items(cur, row["template_id"]),
        item_count=row["item_count"])
    can_edit = _can_write(node)
    return {
        **out,
        "equipment": {"id": node["id"], "code": node["code"], "name": node["name"], "level": node["level"],
                      "full_path": node_path(node), "site_code": node["site_code"]},
        "last_done_on": plain["last_done_on"], "last_done_meter": _seed_shown(row, resolution),
        "created_at": plain["created_at"], "created_by_name": plain["created_by_name"] or plain["created_by"],
        "updated_at": plain["updated_at"],
        "updated_by_name": (plain["updated_by_name"] or plain["updated_by"]) if plain["updated_by"] else None,
        "can_edit": can_edit and bool(row["linked"]),
        "can_remove": can_edit and bool(row["linked"]),
    }


def _plan_row(cur, plan_id, site_id):
    cur.execute(f"{_PLAN_SELECT} WHERE pl.id = %s", (site_id, plan_id))
    return cur.fetchone()


def _detail(cur, plan_id, node):
    row = _plan_row(cur, plan_id, node["site_id"])
    resolutions = pm_jobs.plan_resolutions(cur, [row])
    return _plan_out(cur, row, node, resolutions[plan_id], resolutions[None])


def _plan_node(cur, plan_id, key=READ_KEY):
    """A plan's node under ``key`` -> ``(plan row, node)``; 404 for a missing plan and for one outside the user's
    units (the same answer, so nothing is revealed)."""
    cur.execute("SELECT id, equipment_id FROM pm_plans WHERE id = %s", (plan_id,))
    plan = cur.fetchone()
    if plan is None:
        raise ApiError("Not found", 404)
    _, node = load_node_for_user(cur, plan["equipment_id"], for_update=False, key=key)
    return plan, node


def _subtree_ids(cur, node_id):
    """The node and its parts, two levels down (the tree has three levels, Plan § 4.1)."""
    ids, level = [node_id], [node_id]
    for _ in range(2):
        cur.execute(f"SELECT id FROM equipment WHERE parent_id IN ({marks(level)})", level)
        level = [row["id"] for row in cur.fetchall()]
        if not level:
            break
        ids.extend(level)
    return ids


def _equipment_id_arg():
    equipment_id = int_arg("equipment_id", None, minimum=1)
    if equipment_id is None:
        raise ApiError("equipment_id is required", 400, "equipment_id")
    return equipment_id


@pm_plans_bp.route("/plans", strict_slashes=False)
@require_perm(READ_KEY)
def list_plans():
    """The PM card (§ 6): the linked plans of the node and its parts in ``items``, the unlinked ones in ``unlinked``
    (for every reader: a plan removed from the machine is history), own plans first, each group by template name.
    The meters of every plan are resolved in one pass over the nodes and their ancestors (§ 5.3): no query per plan."""
    equipment_id = _equipment_id_arg()
    with get_db().cursor() as cur:
        _, node = load_node_for_user(cur, equipment_id, for_update=False, key=READ_KEY)
        ids = _subtree_ids(cur, node["id"])
        cur.execute(f"{_PLAN_SELECT} WHERE pl.equipment_id IN ({marks(ids)})"
                    " ORDER BY pl.equipment_id = %s DESC, tp.name, pl.id LIMIT %s",
                    (node["site_id"], *ids, node["id"], MAX_PER_PAGE))
        rows = cur.fetchall()
        resolutions = pm_jobs.plan_resolutions(cur, rows)
        schedules = pm_jobs.plan_schedules(cur, rows, resolutions, node["site_id"], pm_jobs._now(cur))
        out = [_summary_out(row, node["id"], resolutions[row["id"]], resolutions[None], schedules[row["id"]])
               for row in rows]
        return jsonify({"items": [plan for plan in out if plan["linked"]],
                        "unlinked": [plan for plan in out if not plan["linked"]],
                        "can_add": _can_write(node)})


@pm_plans_bp.route("/plans/<int:plan_id>")
@require_perm(READ_KEY)
def get_plan(plan_id):
    with get_db().cursor() as cur:
        _, node = _plan_node(cur, plan_id)
        return jsonify(_detail(cur, plan_id, node))


def _template_as_plan(template, node):
    """A template not yet attached, in PLAN_SELECT's shape for plan_resolutions (the attach preview)."""
    return {**template, "id": 0, "template_id": template["id"], "title": template["name"],
            "template_active": template["active"], "equipment_id": node["id"], "node_code": node["code"],
            "linked": 1, "not_for_machine": 0, "not_for_reason": None}


@pm_plans_bp.route("/plans/attach-preview")
@require_perm(EDIT_KEY)
def attach_preview():
    """The attach dialog's line (§ 5.10, § 9 item 3): the meters the template would use on this machine, or why it
    does not apply here.  The same resolution as the plan page (pm_jobs.plan_resolutions)."""
    equipment_id = _equipment_id_arg()
    template_id = int_arg("template_id", None, minimum=1)
    if template_id is None:
        raise ApiError("template_id is required", 400, "template_id")
    with get_db().cursor() as cur:
        _, node = load_node_for_user(cur, equipment_id, for_update=False, key=EDIT_KEY)
        cur.execute("SELECT * FROM pm_templates WHERE id = %s", (template_id,))
        template = cur.fetchone()
        if template is None:
            raise ApiError("Not found", 404)
        plan = _template_as_plan(template, node)
        resolutions = pm_jobs.plan_resolutions(cur, [plan])
        resolution, shared = resolutions[0], resolutions[None]
        missing = [shared["meter_types"][t]["name"] for t in resolution["missing"]]
        return jsonify({"meters": pm_jobs.plan_meters_out(plan, resolution, shared), "applies": not missing,
                        "missing": missing_text(missing, node["code"]) if missing else None})


# ---------------------------------------------------------------------------
# Keeping the plan rows in step with the links (§ 5.4)
# ---------------------------------------------------------------------------

def _set_linked(conn, plan_id, linked, who):
    """Relink or unlink one plan row in its own transaction: (6e) → (1) shared → the linked UPDATE (and linked_at on
    a relink, BR1-05: the schedule then counts from now when it has no base job and no seed) → the settle."""
    with transaction(conn), conn.cursor() as cur:
        cur.execute(_LOCK_PLAN, (plan_id,))   # (6e)
        plan = cur.fetchone()
        cur.execute(_SHARE_NODE, (plan["equipment_id"],))   # (1) shared
        node = cur.fetchone()
        now = pm_jobs._now(cur)
        if bool(plan["linked"]) != bool(linked):
            changes = {"linked": int(linked), **({"linked_at": now} if linked else {})}
            update_row(cur, "pm_plans", plan_id, changes, who)
        pm_jobs.settle_plan_job(cur, plan_id, node["lifecycle"], now, who)


def _make_plan(conn, node_id, template_id, who):
    """A new plan row (§ 5.4): no assignee (R03 answer 4a), no Last done, linked now.  A 1062 on
    uq_pm_plans_template means another request made it: the make is rolled back and that row takes the relink path,
    (6e) first (BR1-02)."""
    try:
        with transaction(conn), conn.cursor() as cur:
            cur.execute(_SHARE_NODE, (node_id,))   # (1) shared
            node = cur.fetchone()
            now = pm_jobs._now(cur)
            plan_id = insert_row(cur, "pm_plans", {"equipment_id": node_id, "template_id": template_id, "linked": 1,
                                                   "linked_at": now}, who)
            pm_jobs.settle_plan_job(cur, plan_id, node["lifecycle"], now, who)
        return
    except pymysql.err.IntegrityError as exc:
        if exc.args[0] != ER_DUP_ENTRY:
            raise
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM pm_plans WHERE equipment_id = %s AND template_id = %s", (node_id, template_id))
        plan_id = cur.fetchone()["id"]
    conn.commit()
    _set_linked(conn, plan_id, True, who)


def sync_node(conn, node_id, who):
    """Make, relink and unlink the node's plan rows so they match the templates that reach it (§ 5.4) -> the
    actions taken.  Reads the node's links and plans plainly, then writes each plan in its own transaction.  Called
    by *Attach* and *Remove*; R03.19 adds its other callers (a class, type or model link, a node's move)."""
    with conn.cursor() as cur:
        cur.execute("SELECT id, class_id, type_id, model_id FROM equipment WHERE id = %s", (node_id,))
        node = cur.fetchone()
        cur.execute("SELECT template_id, target_kind, target_id, active FROM pm_template_links"
                    " WHERE target_kind = %s AND target_id = %s AND active = 1", (EQUIPMENT, node_id))
        links = cur.fetchall()
        cur.execute("SELECT id, template_id, linked FROM pm_plans WHERE equipment_id = %s", (node_id,))
        plans = cur.fetchall()
    conn.commit()   # ends the plain reads' snapshot, so each plan's transaction starts fresh
    actions = plan_actions(reaching_templates(node, links), plans)
    for template_id in actions["make"]:
        _make_plan(conn, node_id, template_id, who)
    for plan_id in actions["relink"]:
        _set_linked(conn, plan_id, True, who)
    for plan_id in actions["unlink"]:
        _set_linked(conn, plan_id, False, who)
    return actions


# ---------------------------------------------------------------------------
# Write checks
# ---------------------------------------------------------------------------

def _share_lock_node(cur, node_id):
    """(1) shared, then the plain access checks (404 / 403) and the scrapped refusal from the locked row (409)."""
    cur.execute(_SHARE_NODE, (node_id,))
    locked = cur.fetchone()
    if locked is None:
        raise ApiError("Not found", 404)
    _, node = load_node_for_user(cur, node_id, for_update=False, key=EDIT_KEY)
    if locked["lifecycle"] == SCRAPPED:
        raise ApiError(SCRAPPED_MESSAGE, 409)
    return node


def _check_assignee(cur, person_id, site_id):
    """S096 § 5.3, D7: an active person holding a Technician, Engineer or Manager role at the node's site."""
    person = person_at_site(cur, person_id, site_id)
    if person is None or person["role"] not in ASSIGNABLE_ROLES:
        raise ApiError(ASSIGNEE_AT_SITE, 400, "assignee_id")


def _active_link(cur, template_id, node_id):
    cur.execute("SELECT id FROM pm_template_links WHERE template_id = %s AND target_kind = %s AND equipment_id = %s"
                " AND active = 1", (template_id, EQUIPMENT, node_id))
    return cur.fetchone()


# ---------------------------------------------------------------------------
# Routes (§ 6)
# ---------------------------------------------------------------------------

@pm_plans_bp.route("/plans", methods=["POST"], strict_slashes=False)
@require_perm(EDIT_KEY)
def attach_template():
    """*Attach PM template* (§ 5.5): a link of the template to this machine, then its plan row (made, or the old one
    relinked with its history).  A template that does not apply may be attached; the answer says why it makes no
    job (D13)."""
    clean = clean_body(validate_attach, creating=True)
    conn = get_db()
    node_id, template_id = clean["equipment_id"], clean["template_id"]
    with transaction(conn), conn.cursor() as cur:
        cur.execute(_SHARE_NODE, (node_id,))   # (1) shared, the first statement
        locked = cur.fetchone()
        if locked is None:
            raise ApiError("Not found", 404)
        cur.execute(_SHARE_TEMPLATE, (template_id,))   # (6g) shared
        template = cur.fetchone()
        if template is None:
            raise ApiError("Not found", 404, "template_id")
        _, node = load_node_for_user(cur, node_id, for_update=False, key=EDIT_KEY)
        if locked["lifecycle"] == SCRAPPED:
            raise ApiError(SCRAPPED_MESSAGE, 409)
        if not template["active"]:
            raise ApiError(TEMPLATE_INACTIVE, 409, "template_id")
        if _active_link(cur, template_id, node_id) is not None:
            raise ApiError(ALREADY_ATTACHED, 409, "template_id")
        try:
            insert_row(cur, "pm_template_links", {"template_id": template_id, "target_kind": EQUIPMENT,
                                                  "equipment_id": node_id}, actor())
        except pymysql.err.IntegrityError as exc:
            if exc.args[0] == ER_DUP_ENTRY:   # a concurrent attach of the same pair (uq_pm_template_links_open)
                raise ApiError(ALREADY_ATTACHED, 409, "template_id") from exc
            raise
    sync_node(conn, node_id, actor())
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM pm_plans WHERE equipment_id = %s AND template_id = %s", (node_id, template_id))
        plan_id = cur.fetchone()["id"]
        return jsonify(_detail(cur, plan_id, node)), 201


@pm_plans_bp.route("/plans/<int:plan_id>", methods=["PUT"])
@require_perm(EDIT_KEY)
def change_plan(plan_id):
    """The machine's own settings (§ 5.5): ``assignee_id``, ``last_done_on``, ``last_done_meter``, any subset; any
    other field is refused by name (D12).  A field equal to the stored one is not written, except a *Last done* meter
    value whose seed was entered for another meter than the plan uses now (plan_changes, CR1-05)."""
    clean = clean_body(validate_plan_settings, creating=False)
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        cur.execute(_LOCK_PLAN, (plan_id,))   # (6e)
        locked = cur.fetchone()
        if locked is None:
            raise ApiError("Not found", 404)
        node = _share_lock_node(cur, locked["equipment_id"])   # (1) shared, then 404 / 403 / 409
        plan = pm_jobs.plan_row(cur, plan_id)
        resolution = pm_jobs.plan_resolutions(cur, [plan])[plan_id]
        trigger_type = None
        if pm_jobs.has_meter_trigger(plan):
            trigger_type = pm_jobs.meter_types_by_id(cur, [plan["meter_type_id"]]).get(plan["meter_type_id"])
        if clean.get("assignee_id") is not None:
            _check_assignee(cur, clean["assignee_id"], node["site_id"])
        # Only what changes is judged: a page that sends back a stored value the machine can no longer use (a seed
        # of a meter since removed) is not refused for it
        changes = plan_changes(locked, clean, resolution["trigger"])
        error = plan_settings_error(changes, plan, trigger_type, resolution["trigger"] is not None,
                                    pm_jobs._now(cur).date())
        if error:
            raise ApiError(error[1], 400, error[0])
        if "last_done_meter" in changes:
            # BR1-01: the seed carries the meter it was entered for; null clears all three
            trigger = resolution["trigger"] if changes["last_done_meter"] is not None else (None, None)
            changes.update(seed_meter_equipment_id=trigger[0], seed_meter_type_id=trigger[1])
        keep_reschedule = not schedule_changed(locked, changes, resolution["trigger"])
        update_row(cur, "pm_plans", plan_id, changes, actor())
        # S101 D4: a change of Last done drops the open job's reschedule; an assignee change, or the clear of a seed
        # the plan does not use (CR4-01), keeps it
        pm_jobs.settle_plan_job(cur, plan_id, node["lifecycle"], pm_jobs._now(cur), actor(),
                                keep_reschedule=keep_reschedule)
        detail = _detail(cur, plan_id, node)
    return jsonify(detail)


@pm_plans_bp.route("/plans/<int:plan_id>/remove", methods=["POST"])
@require_perm(EDIT_KEY)
def remove_plan(plan_id):
    """*Remove from this machine* (§ 5.5): the template's link to this machine is set inactive, then sync_node
    unlinks the plan and cancels its open, not started job ("The template was removed from this machine.").  A
    started job is left to finish.  The plan and its history stay."""
    conn = get_db()
    with transaction(conn), conn.cursor() as cur:
        cur.execute(_LOCK_PLAN, (plan_id,))   # (6e)
        locked = cur.fetchone()
        if locked is None:
            raise ApiError("Not found", 404)
        node = _share_lock_node(cur, locked["equipment_id"])   # (1) shared, then 404 / 403 / 409
        link = _active_link(cur, locked["template_id"], locked["equipment_id"])
        if link is None:
            raise ApiError(NO_LINK_HERE, 409)
        cur.execute("UPDATE pm_template_links SET active = 0, removed_at = NOW(), removed_by = %s WHERE id = %s",
                    (actor(), link["id"]))
    sync_node(conn, locked["equipment_id"], actor())
    with conn.cursor() as cur:
        return jsonify(_detail(cur, plan_id, node))
