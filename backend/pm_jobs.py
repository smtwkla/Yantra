"""PM jobs — the shell (docs/steps/S097-pm-jobs-due/1-brief.md; R03.3).  A plan's job appears by itself when the
plan comes into its *Upcoming* window, and the team sees it on the PM list and the equipment page's PM card.

Thin shell: pm_schedule_core says when a plan is due and how a job stands; pm_jobs_core says what to do with the
plan's one open job (make, refresh, cancel) and holds the list's rules.  This module reads the inputs (the plan, its
last done job, its meter's readings), stores the job and its timeline line, and answers the list.

Who writes a job: only ``settle_plan_job``, called by the daily run (``generate``, the worker's task pm_generate,
05:00 IST, one transaction per plan), by pm_plans.py's writes (sync_node's make, relink and unlink, the plan
settings, in their transaction) and, through ``settle_one``, by a template save after its commit (S104 § 5.6).  A job
is never deleted: a stopped plan (its template deactivated, the template removed from the machine, a meter it needs
missing; S104 § 5.4) or a scrapped machine cancels its open, not started job with a timeline line (D7).  The
standing (*Not yet due*, *Upcoming*, *Due*, *Overdue*) is never stored: it is judged live from the copies of the due
point on the job and the meter's latest reading (D4).

S104 (docs/steps/S104-pm-templates-one-path/1-brief.md): the work lives on the plan's template, read through the plan
row (PLAN_SELECT); the template names meter types, and ``plan_resolutions`` matches each on the machine's own meters
in force, else on its meter link in use (S104 A1: a part's link to its parent's or grandparent's meter, set on the
part's Meters card; nothing walks up the tree without one), live, never stored on the plan.  A job copies the
trigger meter its due point was computed on (meter_equipment_id, meter_type_id), so the list, the alert scan, Mark
done and the reschedule read one column, and a done job's done_meter counts as the next base only on that same
meter (BR1-01).

ACCESS (§ 5.8).  pm_job:read (site-scoped): the list at the units where it is held (the job's node's current root
unit; D9), every unit for IT admin and admin; the card's ``schedule`` with the key at the node's site.

LOCK ORDER (equipment.py's numbers; § 5.7).  The database runs REPEATABLE READ: a locking read does not start the
snapshot, the first plain read does.  The rule: every write of a pm_jobs or pm_job_events row holds its plan's row
(6e) first, then the node (1) shared, then, for a new job, (6) the PM:YYYY-MM serial counter.  So the plan lock
serialises everything about one plan's jobs, the open job is read plainly after it, and uq_pm_jobs_open_plan is the
backstop (a 1062 there is a bug, a 500).
- The daily run, per plan, one transaction: (6e) SELECT … FOR UPDATE, the first statement → (1) the node LOCK IN
  SHARE MODE → SELECT NOW(), then plain reads (the snapshot starts here, after both locks): the plan, the open job,
  the last done job, the readings, the node's site and the assignee → CREATE: (6) the counter (exclusive until the
  commit), the job and event inserts (shared foreign-key locks on the plan and the node, held, and the person);
  REFRESH / CANCEL: the job row's UPDATE and the event insert → commit.
- pm_plans.py's writes: sync_node's make ((1) shared → the plan insert), relink / unlink and the plan settings
  ((6e) → (1) shared → the plan row's UPDATE) call settle_plan_job last in their transaction: plain reads (the plan
  with its template, the meters in force on the node and its ancestors) → (6) the counter (CREATE only) → the job
  insert or update and the event.  A template save calls settle_one per plan after its own commit (never holding
  the template row (6g) while it takes (6e)).
- (6) after (6e) and (1) is a departure from the number order (elsewhere the lower number comes first, e.g.
  improvements.py takes (6) before (6b)): the PM: counter row is taken by nothing else (only a job create, always
  last before its inserts, always under (6e)), and a plan transaction that only refreshes or cancels must not bump
  it, so it cannot come first.  It adds no cycle with the TK:, IM: or OPL counters.  A counter that other modules
  also take may not copy this order.
No deadlock cycle:
- Two writers of one plan (the run and a save, or two saves) both take (6e) first: the second waits, then reads the
  first's committed job (its snapshot starts after the lock), so two open jobs for one plan cannot be made.
- The run holds one plan (6e) and the counter (6) at a time and commits before it locks the next plan, so it never
  waits on a save's plan while it holds the counter (one transaction for the whole run would: D6).
- The open job is never read with a locking read: SELECT … WHERE open_plan_id = %s FOR UPDATE on a plan with no job
  would take a gap lock on uq_pm_jobs_open_plan, and a run's insert into that gap would wait on a save that waits on
  the run's counter.  No module reads a job FOR UPDATE by open_plan_id.
- The node (1) is taken shared; its writers (equipment.py, meters.py, the scrap) hold it exclusive and never wait on
  a plan, a job or the PM counter.  The scrap's top-down subtree lock is the accepted case pm_plans.py names.
- The person and the meter readings are read plainly; their writers never wait on PM rows.  A reading committed
  during the run counts in the next run or plan save (R03 Q3.2 a: daily).
- R03.4 onwards: a job write (start, an item, done) takes its plan (6e) first, then the job.  A path that locks a
  job and then waits on its plan deadlocks with the run.
- S098 (pm_work.py): start, an item, the performer and done take (6e), then (6f) the job FOR UPDATE, then a node
  (Start and done the job's node shared, an item with a meter the meter's node FOR UPDATE), before any plain read;
  done then calls settle_plan_job, which takes (6) last for a new job.  settle_plan_job leaves an in_progress job
  alone (decide), so the run and a plan save never write a started job.  pm_work.py's note gives the check.
- S099 (pm_work.py): send back calls cancel_job on the plan's open, not started job under the same (6e), by a plain
  UPDATE after (6f) the sent-back job; no second FOR UPDATE.  Verify writes only its own job.
- S101 (pm_work.py): reschedule and skip take (6e), then (6f) the due job, then the node shared, before any plain
  read.  Reschedule writes only its own job (its due copies and rescheduled_on / rescheduled_meter, no (6)); skip
  writes its own job, then calls settle_plan_job (for a new job (6) last), as Mark done.  The run and a plan save
  read the open job's reschedule columns plainly after (6e), which every writer of them holds first.
- S102: the daily ``pm_job_alert_scan`` (``alert_scan``) takes (6e) then (6f), one job per transaction, and writes
  only the job's four alert columns and a ``task_queue`` row; no node or counter.  After both locks: SELECT NOW(),
  then plain reads (the node's lifecycle, the plan meter's latest reading).  The candidates are one plain read
  before, committed, so each job's transaction starts fresh.  Every path that waits behind it waits only on (6e) or
  (6f), and the scan never waits on a node, a counter or a person: no cycle.
"""

import logging
from datetime import datetime, time

import alerts

from flask import Blueprint, jsonify

from alerts_core import PM_JOB_DUE, PM_JOB_OVERDUE, pm_alert_due, pm_markers
from api_common import DEFAULT_PER_PAGE, MAX_PAGE, MAX_PER_PAGE, enum_arg, int_arg
from auth_utils import current_person_id, has_perm_at, require_perm
from db_helpers import count, get_db, insert_row, marks, next_counter, row_to_dict, transaction, update_row
from equipment import NODE_JOINS, accessible_unit_ids, meters_on_paths, types_by_node
from equipment_core import SCRAPPED
from local_db import connection_lost
from meters import first_reading_after, last_readings, readings_across_reset
from meters_core import format_number
from pm_jobs_core import (
    ASSIGNEE_CHANGED, BASE_STATES, CANCEL, CANCELLED, CANCELLED_EVENT, CREATE, CREATED, DONE, DUE_CHANGED, DUE_STATE,
    IN_PROGRESS, JOB_BASE, OPEN_STATES, READ_KEY, REFRESH, RESCHEDULE_DROPPED, RUN_ACTOR, SEED_BASE, SERIAL_PREFIX,
    SKIPPED, TAB_DONE, TAB_DUE, TAB_TO_VERIFY, TABS, VERIFIED, assignable_id, days_past, decide, due_copies,
    job_changes, job_override, job_standing, list_order, meter_base_source, meter_offset, pm_serial, seed_matches,
    tab_of,
)
from pm_links_core import IN_FORCE_SQL, METER_READING, applies, needed_meters, resolve_meters, stop_remark
from pm_schedule_core import BEFORE_USE, BOTH, DUE, METER, NOT_YET, OVERDUE, UPCOMING, job_state, next_due
from pm_templates_core import MAINTENANCE
from pm_work_core import SENT_BACK_EVENT, SKIPPED_EVENT, VERIFIED_EVENT, awaits_verification, self_verified
from tickets import person_at_site
from tickets_core import serial_scope

logger = logging.getLogger(__name__)

pm_jobs_bp = Blueprint("pm_jobs", __name__)

# (6e): the plan row alone, every column; pm_plans.py's writes take the same statement.  S104: the template's
# columns are read plainly after it (PLAN_SELECT); the template row (6g) is never locked by a job write.
LOCK_PLAN = "SELECT * FROM pm_plans WHERE id = %s FOR UPDATE"
# (6f): the job row, always right after its plan (6e); pm_work.py's routes and the alert scan (S102)
LOCK_JOB = "SELECT * FROM pm_jobs WHERE id = %s FOR UPDATE"
# (1), shared: the node's lifecycle (scrapped) is decided from this row; pm_plans.py shares it
SHARE_NODE = "SELECT id, lifecycle FROM equipment WHERE id = %s LOCK IN SHARE MODE"
# S104 § 5.7: the plan row with its template's columns under S096's names (title, performer, needs_verification,
# the trigger), so pm_schedule_core.next_due, schedule_inputs and decide take the same dict as before; plus the
# template's active flag and the node's code (the stop remark's words).  pm_plans.py builds the card's select from
# the same two parts (CR1-06), so a column added here reaches both.
PLAN_COLUMNS = (
    "pl.*, tp.name AS title, tp.performer, tp.needs_verification, tp.trigger_kind, tp.calendar_every,"
    " tp.calendar_unit, tp.meter_type_id, tp.meter_every, tp.active AS template_active, pe.code AS node_code"
)
PLAN_FROM = (
    " FROM pm_plans pl JOIN pm_templates tp ON tp.id = pl.template_id JOIN equipment pe ON pe.id = pl.equipment_id"
)
PLAN_SELECT = "SELECT " + PLAN_COLUMNS + PLAN_FROM
# IN_FORCE_SQL (a plan in force, S104 § 4.2) lives in pm_links_core since A1: equipment.py's LINK_PLANS_SQL uses it

_OPEN_IN = ", ".join(f"'{state}'" for state in OPEN_STATES)
_BASE_IN = ", ".join(f"'{state}'" for state in BASE_STATES)
_END_OF_DAY = time(23, 59, 59)

# A job with what the list shows: its plan and template, the job's own copy of the trigger meter (type and node;
# S104 § 5.3), the assignee's and the performer's names, the node, its current root unit and site
# (equipment.NODE_JOINS: e, p, gp, u, s, c, t, m are taken there, so the template is tp, the meter type mt and the
# meter's node mn) and the template's active item count.  The list, the card and the job page (pm_work.py) share
# it.  pl_title is the job's copy of the template's name from Start, else the template's name now (D8).
_JOB_JOINS = (
    " FROM pm_jobs j JOIN pm_plans pl ON pl.id = j.plan_id JOIN pm_templates tp ON tp.id = pl.template_id"
    " JOIN equipment e ON e.id = j.equipment_id" + NODE_JOINS +
    " LEFT JOIN equipment mn ON mn.id = j.meter_equipment_id"
    " LEFT JOIN meter_types mt ON mt.id = j.meter_type_id"
    " LEFT JOIN people a ON a.id = j.assignee_id"
    " LEFT JOIN people pb ON pb.id = j.performed_by_id"
)
JOB_FROM = (
    "SELECT j.*, COALESCE(j.title, tp.name) AS pl_title, tp.performer AS pl_performer, pl.template_id,"
    " mn.code AS meter_code, mt.name AS t_name, mt.unit AS t_unit, mt.kind AS t_kind, mt.decimals AS t_decimals,"
    f" {IN_FORCE_SQL} AS pl_active, tp.needs_verification AS pl_needs_verification,"
    " tp.trigger_kind AS pl_trigger_kind,"
    " a.name AS a_name, pb.name AS pb_name, e.code AS e_code, e.name AS e_name, e.lifecycle AS e_lifecycle,"
    " u.id AS unit_id, u.code AS unit_code, s.id AS site_id, s.code AS site_code,"
    " (SELECT COUNT(*) FROM pm_template_items i WHERE i.template_id = tp.id AND i.active = 1) AS item_count,"
    " (SELECT COUNT(*) FROM pm_job_results r WHERE r.job_id = j.id) AS result_count" + _JOB_JOINS
)
# The open jobs (the list's Due and Upcoming tabs, the card)
_JOB_SELECT = JOB_FROM + f" WHERE j.state IN ({_OPEN_IN})"
# S099 § 5.7: the jobs waiting for verification (To verify, the oldest done first), and the finished ones (Done,
# S098 § 6.3, narrowed: verified, or done and final; COALESCE keeps the jobs done before S099, whose copy is NULL;
# S101 D5: and the skipped ones, by their skip time)
_WAITING_WHERE = f" WHERE j.state = '{DONE}' AND j.needs_verification = 1"
_DONE_WHERE = (f" WHERE (j.state = '{VERIFIED}' OR j.state = '{SKIPPED}'"
               f" OR (j.state = '{DONE}' AND COALESCE(j.needs_verification, 0) = 0))")
_SKIPPED_AND = f" AND j.state = '{SKIPPED}'"   # the Done tab's total_skipped (S101, BR1-01)
_PAGED_TABS = {TAB_TO_VERIFY: (_WAITING_WHERE, "j.done_at ASC, j.id ASC"),
               TAB_DONE: (_DONE_WHERE, "j.done_at DESC, j.id DESC")}
_COUNT_FROM = "SELECT COUNT(*) AS n" + _JOB_JOINS
# One query each for a page of jobs (§ 6.3): the findings of their results, and their verify and send-back lines
_FINDINGS = ("SELECT job_id, SUM(outcome = 'not_ok') AS not_ok, SUM(outcome = 'not_done') AS not_done,"
             " SUM(limit_state IS NOT NULL) AS out_of_limits FROM pm_job_results WHERE job_id IN ({ids})"
             " GROUP BY job_id")
_SIGN_OFF_EVENTS = (
    "SELECT ev.job_id, ev.event, ev.occurred_at, ev.person_id, ev.remark, ev.created_by, p.name AS person_name,"
    " cp.name AS cp_name FROM pm_job_events ev"
    " LEFT JOIN people p ON p.id = ev.person_id"
    " LEFT JOIN people cp ON cp.username = ev.created_by"
    f" WHERE ev.job_id IN ({{ids}}) AND ev.event IN ('{VERIFIED_EVENT}', '{SENT_BACK_EVENT}', '{SKIPPED_EVENT}')"
    " ORDER BY ev.occurred_at, ev.id"
)


def job_row(cur, job_id):
    """One job with what the list shows (``JOB_FROM``), plain -> the row, or None: the job page and the alert task."""
    cur.execute(JOB_FROM + " WHERE j.id = %s", (job_id,))
    return cur.fetchone()


def _now(cur):
    """The session's clock (IST, as the queue and created_at), naive.  One function, so a test can fix the clock.
    It reads no table, so it does not start the transaction's snapshot."""
    cur.execute("SELECT NOW() AS now")
    return cur.fetchone()["now"]


# ---------------------------------------------------------------------------
# The template and the meter match (S104 § 5.3, § 5.7)
# ---------------------------------------------------------------------------

def plan_row(cur, plan_id):
    """The plan with its template (PLAN_SELECT), plain -> the row, or None."""
    cur.execute(PLAN_SELECT + " WHERE pl.id = %s", (plan_id,))
    return cur.fetchone()


def _meter_items(cur, template_ids):
    """The active *Meter reading* items of the templates, in position order -> ``{template_id: [row, …]}``."""
    out = {template_id: [] for template_id in template_ids}
    if not out:
        return out
    cur.execute("SELECT template_id, item_type, reading_kind, meter_type_id FROM pm_template_items"
                f" WHERE template_id IN ({marks(out)}) AND active = 1 AND reading_kind = '{METER_READING}'"
                " ORDER BY template_id, position, id", list(out))
    for row in cur.fetchall():
        out[row["template_id"]].append(row)
    return out


def meter_types_by_id(cur, type_ids):
    """``{id: {id, name, unit, kind, decimals}}`` of the meter types, one query."""
    ids = sorted({type_id for type_id in type_ids if type_id is not None})
    if not ids:
        return {}
    cur.execute(f"SELECT id, name, unit, kind, decimals FROM meter_types WHERE id IN ({marks(ids)})", ids)
    return {row["id"]: row for row in cur.fetchall()}


def has_meter_trigger(plan):
    return plan["trigger_kind"] in (METER, BOTH)


def plan_resolutions(cur, plans):
    """Each plan's meter match and why it makes no job (§ 5.3, § 5.4), for any number of PLAN_SELECT rows in a fixed
    number of queries (the card's one pass; the settle with one plan) -> ``{plan_id: {needs, resolved, missing,
    stop, trigger}}`` plus the shared ``codes``, ``meters`` and ``meter_types`` under the key None.  ``trigger`` is
    the trigger meter ``(node_id, meter_type_id)`` it resolves to, or None (no meter trigger, or no such meter)."""
    found = meters_on_paths(cur, sorted({plan["equipment_id"] for plan in plans}))
    types = types_by_node(found["meters"])
    items = _meter_items(cur, sorted({plan["template_id"] for plan in plans}))
    out = {}
    for plan in plans:
        needs = needed_meters(plan, items[plan["template_id"]])
        resolved = resolve_meters(needs, plan["equipment_id"], types, found["links"].get(plan["equipment_id"], {}))
        out[plan["id"]] = {"needs": needs, "resolved": resolved, "missing": applies(needs, resolved)}
    meter_types = meter_types_by_id(cur, [type_id for each in out.values() for type_id in each["needs"]])
    for plan in plans:
        each = out[plan["id"]]
        names = [meter_types[type_id]["name"] for type_id in each["missing"]]
        each["stop"] = stop_remark(bool(plan["template_active"]), bool(plan["linked"]), bool(plan["not_for_machine"]),
                                   names, plan["node_code"], plan["not_for_reason"])
        node_id = each["resolved"].get(plan["meter_type_id"]) if has_meter_trigger(plan) else None
        each["trigger"] = None if node_id is None else (node_id, plan["meter_type_id"])
    out[None] = {"codes": found["codes"], "meters": found["meters"], "meter_types": meter_types}
    return out


def plan_meters_out(plan, resolution, shared):
    """The meters a plan uses on its machine, as the card and the plan page show them (§ 5.10, A1.6.7) ->
    ``[{meter_type, equipment: {id, code} or None, from_link}]`` in the template's order; ``equipment`` None for a
    type the machine lacks; ``from_link`` when the meter is a node above's, through the machine's meter link."""
    out = []
    for type_id in resolution["needs"]:
        node_id = resolution["resolved"][type_id]
        meter_type = shared["meter_types"][type_id]
        out.append({
            "meter_type": {key: meter_type[key] for key in ("id", "name", "unit", "kind", "decimals")},
            "equipment": None if node_id is None else {"id": node_id, "code": shared["codes"][node_id]},
            "from_link": node_id is not None and node_id != plan["equipment_id"],
        })
    return out


# ---------------------------------------------------------------------------
# The schedule of one plan (S097 § 5.3, § 5.4; S104 § 5.3: the meter base follows the meter)
# ---------------------------------------------------------------------------

def _last_base_job(cur, plan_id):
    cur.execute("SELECT done_at, done_meter, meter_equipment_id, meter_type_id FROM pm_jobs"
                f" WHERE plan_id = %s AND state IN ({_BASE_IN}) ORDER BY done_at DESC, id DESC LIMIT 1", (plan_id,))
    return cur.fetchone()


def _meter_base(cur, plan, last, meter):
    """§ 5.3 step 2 on the meter the trigger resolves to now -> ``(value, taken_at, start_meter)``; value None: no
    base.  pm_jobs_core.meter_base_source says whether the last base job's done_meter, the seed, or the meter's own
    readings give it (BR1-01); the readings case is the latest reading of this meter at or before the base time, else
    the first after it (S095 D9)."""
    source = meter_base_source(last, plan, meter)
    if source == JOB_BASE:
        return last["done_meter"], last["done_at"], None
    if last is not None:
        start = last["done_at"]
    else:
        # The session runs at +05:30 (local_db's init_command), so linked_at is IST
        start = datetime.combine(plan["last_done_on"], _END_OF_DAY) if plan["last_done_on"] else plan["linked_at"]
        if source == SEED_BASE:
            return plan["last_done_meter"], start, None
    reading = last_readings(cur, [meter[0]], until=start).get(tuple(meter))
    if reading is None:
        reading = first_reading_after(cur, meter[0], meter[1], start)
    if reading is None:
        return None, None, None
    return reading["value"], reading["taken_at"], reading["value"]


def schedule_inputs(cur, plan, now, override=None, meter=None):
    """The plan's next due point and its standing now (plain reads, after the plan's lock on a write) ->
    ``{due, standing, reading, offset, override}``.  ``plan`` is a PLAN_SELECT row; ``meter`` the trigger meter
    ``(node_id, meter_type_id)`` it resolves to now (plan_resolutions' ``trigger``; a job's own copy for the
    reschedule), None without one: the meter readings are read there, never on the job's node.  ``override`` (S101:
    the job's reschedule, next_due's ``{due_on, due_meter}``, or None) replaces the computed values; it is returned
    as given.  A plan with no base job and no seed counts from ``linked_at``, its (re)link (BR1-05)."""
    meter = None if meter is None else tuple(meter)
    last = _last_base_job(cur, plan["id"])
    start_meter, reading, offset, base_value = None, None, 0, None
    if has_meter_trigger(plan) and meter is not None:
        base_value, base_time, start_meter = _meter_base(cur, plan, last, meter)
        reading = last_readings(cur, [meter[0]]).get(meter)
        if base_value is not None:
            offset = meter_offset(base_value, readings_across_reset(cur, meter[0], meter[1], base_time))
    last_job = None if last is None else {"done_on": last["done_at"].date(), "done_meter": base_value}
    seed = plan["last_done_meter"] if seed_matches(plan, meter) else None
    due = next_due(dict(plan, created_on=plan["linked_at"].date(), last_done_meter=seed), last_job, start_meter,
                   override)
    reading_value = None if reading is None else reading["value"] + offset
    return {"due": due, "standing": job_state(due, reading_value, now.date()),
            "reading": reading, "offset": offset, "override": override}


# ---------------------------------------------------------------------------
# Settling one plan's job (§ 5.5)
# ---------------------------------------------------------------------------

def add_event(cur, job_id, event, now, actor, **fields):
    insert_row(cur, "pm_job_events", {"job_id": job_id, "event": event, "occurred_at": now, **fields}, actor)


def _job_assignee(cur, plan):
    """The plan's assignee when still assignable at the node's current site (§ 5.2, D12), else None.  S104 § 5.5: an
    operator template's plan uses none, whatever its row stores (the stored one is used again if the template goes
    back to maintenance)."""
    if plan["assignee_id"] is None or plan["performer"] != MAINTENANCE:
        return None
    cur.execute(f"SELECT s.id AS site_id FROM equipment e{NODE_JOINS} WHERE e.id = %s", (plan["equipment_id"],))
    site = cur.fetchone()
    person = None if site is None else person_at_site(cur, plan["assignee_id"], site["site_id"])
    return assignable_id(plan["assignee_id"], person)


def _meter_copy(trigger):
    """S104 § 5.3, D5: the trigger meter the due point was computed on, copied onto the job with the due copies."""
    return {"meter_equipment_id": trigger and trigger[0], "meter_type_id": trigger and trigger[1]}


def _create(cur, plan, inputs, assignee_id, now, actor, trigger):
    number = next_counter(cur, serial_scope(now.year, now.month, SERIAL_PREFIX))   # (6)
    copies = due_copies(inputs["due"], inputs["offset"])
    job_id = insert_row(cur, "pm_jobs", {
        "serial": pm_serial(now.year, now.month, number), "plan_id": plan["id"],
        "equipment_id": plan["equipment_id"], "created_why": inputs["standing"].trigger, **copies,
        **_meter_copy(trigger), "assignee_id": assignee_id,
    }, actor)
    add_event(cur, job_id, CREATED, now, actor, to_state=DUE_STATE, due_on=copies["due_on"],
               due_meter=copies["due_meter"])


def _refresh(cur, job, inputs, assignee_id, now, actor, trigger):
    """Rewrite the copies that differ -> True when anything was written.  A timeline line for the due point and for
    the assignee only (the windows, the offset and the meter copy are copies of inputs, not the due point).  S101:
    the reschedule columns change here only when the reschedule is dropped (D4), so their change writes the
    due_changed line too, with RESCHEDULE_DROPPED, also when the due point stays the same."""
    copies = {**due_copies(inputs["due"], inputs["offset"], inputs["override"]), **_meter_copy(trigger)}
    changes = job_changes(job, copies, assignee_id)
    if not changes:
        return False
    update_row(cur, "pm_jobs", job["id"], changes, actor)
    dropped = "rescheduled_on" in changes or "rescheduled_meter" in changes
    if dropped or "due_on" in changes or "due_meter" in changes:
        add_event(cur, job["id"], DUE_CHANGED, now, actor, due_on=copies["due_on"], due_meter=copies["due_meter"],
                  remark=RESCHEDULE_DROPPED if dropped else None)
    if "assignee_id" in changes:
        add_event(cur, job["id"], ASSIGNEE_CHANGED, now, actor, person_id=assignee_id)
    return True


def cancel_job(cur, job, remark, now, actor):
    """Cancel a due job with its timeline line (``from_state`` due): the run, a plan save and S099's send back."""
    update_row(cur, "pm_jobs", job["id"], {"state": CANCELLED}, actor)
    add_event(cur, job["id"], CANCELLED_EVENT, now, actor, from_state=DUE_STATE, to_state=CANCELLED,
               remark=remark)


def settle_plan_job(cur, plan_id, node_lifecycle, now, actor, *, keep_reschedule=True):
    """Make, refresh or cancel the plan's open job (§ 5.5) -> the action taken (CREATE, REFRESH, CANCEL), or None
    when nothing was written (no job to make, or an open job whose copies did not change; CR1-02).  Runs with the
    plan's row held (6e) or newly inserted in the caller's transaction, and the node held shared; the template is
    read plainly (PLAN_SELECT, S104 § 5.7).  S104 § 5.4: the plan's stop remark (template deactivated, unlinked, not
    for this machine, a meter missing) cancels a due job with it and makes none; the trigger meter is resolved on the
    machine now (§ 5.3) and copied onto the job.  S101: a refresh keeps the due job's reschedule (job_override),
    unless ``keep_reschedule`` is False (a save that changed the schedule, D4); a new job never has one."""
    plan = plan_row(cur, plan_id)
    cur.execute(f"SELECT * FROM pm_jobs WHERE plan_id = %s AND state IN ({_OPEN_IN})", (plan_id,))
    job = cur.fetchone()
    resolution = plan_resolutions(cur, [plan])[plan_id]
    stop, scrapped = resolution["stop"], node_lifecycle == SCRAPPED
    before_use = plan["trigger_kind"] == BEFORE_USE
    open_state = None if job is None else job["state"]
    inputs = None
    if stop is None and not scrapped and not before_use and open_state != IN_PROGRESS:
        override = None if job is None or not keep_reschedule else job_override(job, plan["trigger_kind"])
        inputs = schedule_inputs(cur, plan, now, override, resolution["trigger"])
    decision = decide(stop, before_use, scrapped, open_state, inputs and inputs["standing"].state)
    if decision is None:
        return None
    action, remark = decision
    if action == CANCEL:
        cancel_job(cur, job, remark, now, actor)
    elif action == CREATE:
        _create(cur, plan, inputs, _job_assignee(cur, plan), now, actor, resolution["trigger"])
    elif not _refresh(cur, job, inputs, _job_assignee(cur, plan), now, actor, resolution["trigger"]):
        return None
    return action


# ---------------------------------------------------------------------------
# The daily run (§ 5.6)
# ---------------------------------------------------------------------------

def settle_one(conn, plan_id, actor, *, keep_reschedule=True):
    """One plan in its own transaction (D6) -> the action taken, or None (nothing to do, or the plan is gone).  The
    daily run passes RUN_ACTOR; S104 § 5.6: a template save passes its engineer (BR1-03), with ``keep_reschedule``
    False when the save changed the schedule."""
    with transaction(conn), conn.cursor() as cur:
        cur.execute(LOCK_PLAN, (plan_id,))   # (6e), the first statement
        plan = cur.fetchone()
        if plan is None:
            return None
        cur.execute(SHARE_NODE, (plan["equipment_id"],))   # (1) shared
        node = cur.fetchone()
        return settle_plan_job(cur, plan_id, node["lifecycle"], _now(cur), actor, keep_reschedule=keep_reschedule)


def generate(conn, should_stop):
    """Settle every plan that may need it, one transaction per plan (§ 5.6) -> ``{created, refreshed, cancelled,
    failed: [plan ids], stopped}``.  The caller (task_handlers.pm_generate) starts inside the worker's transaction:
    the candidates' read opened its snapshot, and the commit after it ends it, so each plan's transaction starts
    fresh.  A plan that fails is rolled back alone and the run goes on; a lost connection is raised at once.
    ``should_stop()`` is checked between plans: ``stopped`` True leaves the rest for the retry."""
    with conn.cursor() as cur:
        # The plans in force (S104 § 5.7), and any plan with a due job, so a stopped plan's leftover job is cancelled
        cur.execute(f"SELECT pl.id FROM pm_plans pl JOIN pm_templates tp ON tp.id = pl.template_id"
                    f" WHERE {IN_FORCE_SQL} UNION SELECT plan_id FROM pm_jobs WHERE state = '{DUE_STATE}' ORDER BY 1")
        plan_ids = [row["id"] for row in cur.fetchall()]
    conn.commit()
    result = {CREATE: 0, REFRESH: 0, CANCEL: 0}
    failed = []
    for index, plan_id in enumerate(plan_ids):
        if index and should_stop():
            return {"created": result[CREATE], "refreshed": result[REFRESH], "cancelled": result[CANCEL],
                    "failed": failed, "stopped": True}
        try:
            action = settle_one(conn, plan_id, RUN_ACTOR)
        except Exception as exc:   # noqa: BLE001 — one plan's fault must not stop the others
            if connection_lost(conn, exc):   # the worker's own test (local_db): re-raised at once
                raise
            logger.exception("pm_generate: plan %s failed", plan_id)
            failed.append(plan_id)
            continue
        if action is not None:
            result[action] += 1
    return {"created": result[CREATE], "refreshed": result[REFRESH], "cancelled": result[CANCEL],
            "failed": failed, "stopped": False}


# ---------------------------------------------------------------------------
# The PM alerts' daily scan (S102 § 5.4)
# ---------------------------------------------------------------------------

# Only narrows the work: every job it leaves out is one pm_alert_due answers None for (overdue sent for this due
# point; no meter due value and the date still ahead; neither).  A job whose *due* was sent stays a candidate
# through its window (BR1-03).
_ALERT_CANDIDATES = (
    f"SELECT id, plan_id FROM pm_jobs WHERE state = '{DUE_STATE}'"
    " AND NOT ((overdue_alert_on IS NOT NULL OR overdue_alert_meter IS NOT NULL)"
    " AND overdue_alert_on <=> due_on AND overdue_alert_meter <=> due_meter)"
    " AND (due_meter IS NOT NULL OR due_on <= %s) ORDER BY plan_id"
)


def _mark_alerted(cur, job, kind):
    """The kind's markers (alerts_core.pm_markers) on the job held (6f).  No updated_*: an alert is not a change of
    the job (as S074's and S084's markers)."""
    columns = pm_markers(kind, job)
    sets = ", ".join(f"{column} = %s" for column in columns)
    cur.execute(f"UPDATE pm_jobs SET {sets} WHERE id = %s", (*columns.values(), job["id"]))


def _alert_one(conn, job_id, plan_id):
    """One job in its own transaction (D9) -> the kind queued, or None.  (6e) the plan first, (6f) the job, then the
    clock and the plain reads (LOCK ORDER above); the decision comes from the locked rows.  S104: the meter is the
    job's own copy (§ 5.3), and the plan counts as active only while it is in force and its template applies (no
    stop remark, § 5.4), read plainly after the locks."""
    with transaction(conn), conn.cursor() as cur:
        cur.execute(LOCK_PLAN, (plan_id,))   # (6e), the first statement
        if cur.fetchone() is None:
            return None
        cur.execute(LOCK_JOB, (job_id,))     # (6f)
        job = cur.fetchone()
        if job is None:
            return None
        today = _now(cur).date()
        cur.execute("SELECT lifecycle FROM equipment WHERE id = %s", (job["equipment_id"],))
        lifecycle = cur.fetchone()["lifecycle"]
        value = None
        if job["meter_equipment_id"] is not None:
            meter = (job["meter_equipment_id"], job["meter_type_id"])
            reading = last_readings(cur, [meter[0]]).get(meter)
            value = None if reading is None else reading["value"]
        standing = job_standing(job, value, today)
        in_force = plan_resolutions(cur, [plan_row(cur, plan_id)])[plan_id]["stop"] is None
        kind = pm_alert_due(job, standing.state, in_force, lifecycle == SCRAPPED)
        if kind is not None:
            _mark_alerted(cur, job, kind)
            alerts.enqueue_pm_alert(cur, kind, job_id)
        return kind


def alert_scan(conn, should_stop):
    """Queue *PM job due* and *PM job overdue* once per due point (S102 § 5.4), one transaction per job ->
    ``{due, overdue, failed: [job ids], stopped}``.  Started inside the worker's transaction, as ``generate``: the
    candidates' read opens its snapshot and the commit after it ends it.  A job that fails is rolled back alone (no
    marker, no task) and the run goes on; a lost connection is raised at once.  The markers are written even when
    push is off (D6)."""
    with conn.cursor() as cur:
        cur.execute(_ALERT_CANDIDATES, (_now(cur).date(),))
        candidates = [(row["id"], row["plan_id"]) for row in cur.fetchall()]
    conn.commit()
    sent = {PM_JOB_DUE: 0, PM_JOB_OVERDUE: 0}
    failed = []
    for index, (job_id, plan_id) in enumerate(candidates):
        if index and should_stop():
            return {"due": sent[PM_JOB_DUE], "overdue": sent[PM_JOB_OVERDUE], "failed": failed, "stopped": True}
        try:
            kind = _alert_one(conn, job_id, plan_id)
        except Exception as exc:   # noqa: BLE001 — one job's fault must not stop the others
            if connection_lost(conn, exc):
                raise
            logger.exception("pm_job_alert_scan: job %s failed", job_id)
            failed.append(job_id)
            continue
        if kind is not None:
            sent[kind] += 1
    return {"due": sent[PM_JOB_DUE], "overdue": sent[PM_JOB_OVERDUE], "failed": failed, "stopped": False}


# ---------------------------------------------------------------------------
# The list and the card (§ 6)
# ---------------------------------------------------------------------------

def meter_type_out(row):
    """The ``meter_type`` of a joined row (meter_type_id and the t_ columns), or None without a meter.  One copy: the
    template and plan pages (pm_templates.py, pm_plans.py) and the job page (pm_work.py) use it too (CR1-06)."""
    if row["meter_type_id"] is None:
        return None
    return {"id": row["meter_type_id"], "name": row["t_name"], "unit": row["t_unit"], "kind": row["t_kind"],
            "decimals": row["t_decimals"]}


def _meter_out(row, reading, offset):
    """The plan's meter with its value now and counted across a reset (§ 6.1), or None without a meter trigger.
    ``row`` carries meter_equipment_id, meter_type_id, meter_code and the t_ columns."""
    if row["meter_type_id"] is None:
        return None
    value = None if reading is None else reading["value"]
    return {
        "equipment_id": row["meter_equipment_id"], "code": row["meter_code"],
        "meter_type": meter_type_out(row),
        "value_now": format_number(value), "taken_at": None if reading is None else row_to_dict(reading)["taken_at"],
        "value_counted": None if value is None else format_number(value + offset), "offset": format_number(offset),
    }


def _standing_out(standing):
    return {"state": standing.state, "trigger": standing.trigger, "no_reading": standing.no_reading}


def jobs_out(cur, rows, today):
    """Open-job rows of ``_JOB_SELECT`` as the list sends them (§ 6.1), in ``list_order``: one readings query over
    the plans' meter nodes; each standing judged live from the job's copies and the latest reading plus the job's
    offset (D4)."""
    meter_nodes = sorted({row["meter_equipment_id"] for row in rows if row["meter_equipment_id"] is not None})
    latest = last_readings(cur, meter_nodes)
    judged = []
    for row in rows:
        reading = latest.get((row["meter_equipment_id"], row["meter_type_id"]))
        standing = job_standing(row, None if reading is None else reading["value"], today)
        judged.append((row, standing, reading))
    judged.sort(key=lambda each: list_order({"state": each[0]["state"], "standing": {"state": each[1].state},
                                             "due_on": each[0]["due_on"], "serial": each[0]["serial"]}))
    return [job_item(row, standing, reading, today) for row, standing, reading in judged]


def _person(person_id, name):
    return None if person_id is None else {"id": person_id, "name": name}


def job_item(row, standing, reading, today):
    """One job row of ``JOB_FROM`` as the list sends it (§ 6.1; S098 § 6.3).  ``standing`` (pm_schedule_core's) and
    ``reading`` (the plan's meter's latest) for an open job; None for a done one, which has no standing and no
    days past.  The one copy of the item's shape: the open list, the Done tab and the job page build on it."""
    plain = row_to_dict(row)
    return {
        "id": row["id"], "serial": row["serial"], "state": row["state"],
        "standing": None if standing is None else _standing_out(standing), "due_on": plain["due_on"],
        "due_meter": format_number(row["due_meter"]),
        "days_past": None if standing is None else days_past(row["due_on"], today),
        "created_why": row["created_why"],
        "equipment": {"id": row["equipment_id"], "code": row["e_code"], "name": row["e_name"]},
        # A started job counts its own copied items (CR1-03): a plan edit since Start changes only the plan's count
        "plan": {"id": row["plan_id"], "title": row["pl_title"],
                 "item_count": row["result_count"] if row["started_at"] else row["item_count"],
                 "performer": row["pl_performer"], "template_id": row["template_id"]},
        "unit": {"id": row["unit_id"], "full_code": f"{row['site_code']}.{row['unit_code']}"},
        "site_code": row["site_code"],
        "assignee": _person(row["assignee_id"], row["a_name"]),
        "performed_by": _person(row["performed_by_id"], row["pb_name"]),
        "started_at": plain["started_at"], "done_at": plain["done_at"], "timeliness": row["timeliness"],
        "meter": _meter_out(row, reading, row["meter_offset"]),
        "created_at": plain["created_at"],
        # S099 § 6.3: the job's own copy of the plan's setting (None: not done, or done before S099)
        "needs_verification": None if row["needs_verification"] is None else bool(row["needs_verification"]),
        "awaits_verification": awaits_verification(row["state"], row["needs_verification"]),
        # S101 § 4.2: moved by an engineer (the reschedule columns, kept on a closed job as the record)
        "rescheduled": row["rescheduled_on"] is not None or row["rescheduled_meter"] is not None,
        # Filled by add_sign_off for a page of items (one query each); None until then
        "findings": None, "verification": None, "sent_back": None, "skipped": None,
    }


def _findings_out(row):
    """A job's findings (§ 4.2): the counts of its results Not OK, Not done and out of limits; all 0 without
    results (a job never started)."""
    return {key: int(row[key] or 0) if row else 0 for key in ("not_ok", "not_done", "out_of_limits")}


def sign_off_out(event, performer_id):
    """A ``verified``, ``sent_back`` or ``skipped`` (S101) line of _SIGN_OFF_EVENTS as the page and the list send it
    (§ 6.2, § 6.3): who by name only (the person, else the login's person, else the login; S098 § 6.2), when, the
    remark; a verified line also says whether the verifier is the job's *Performed by* (D5)."""
    out = {"at": row_to_dict(event)["occurred_at"],
           "by_name": event["person_name"] or event["cp_name"] or event["created_by"], "remark": event["remark"]}
    if event["event"] == VERIFIED_EVENT:
        out["self_verified"] = self_verified(event["person_id"], performer_id)
    return out


def add_sign_off(cur, items, with_findings):
    """Fill ``findings`` (when ``with_findings``), ``verification`` (a verified job's line), ``sent_back`` (the
    latest send-back of a job in progress) and ``skipped`` (a skipped job's line, S101) on ``items`` (job_item's), in
    place: one query each, none per row."""
    if not items:
        return items
    ids = [item["id"] for item in items]
    if with_findings:
        cur.execute(_FINDINGS.format(ids=marks(ids)), ids)
        found = {row["job_id"]: row for row in cur.fetchall()}
        for item in items:
            item["findings"] = _findings_out(found.get(item["id"]))
    cur.execute(_SIGN_OFF_EVENTS.format(ids=marks(ids)), ids)
    latest = {(row["job_id"], row["event"]): row for row in cur.fetchall()}   # time order: the last one stays
    for item in items:
        performer = item["performed_by"] and item["performed_by"]["id"]
        verified = latest.get((item["id"], VERIFIED_EVENT))
        sent_back = latest.get((item["id"], SENT_BACK_EVENT))
        item["verification"] = sign_off_out(verified, performer) if verified and item["state"] == VERIFIED else None
        item["sent_back"] = sign_off_out(sent_back, performer) if sent_back and item["state"] == IN_PROGRESS else None
        skipped = latest.get((item["id"], SKIPPED_EVENT))
        item["skipped"] = sign_off_out(skipped, performer) if skipped and item["state"] == SKIPPED else None
    return items


def _counts(items, to_verify):
    """The tab counts over the open jobs: the started ones apart (S098 § 5.9), the others by standing, so the parts
    of a tab add up to its rows; and the jobs waiting for verification (S099, counted by its own query)."""
    started = [item for item in items if item["state"] == IN_PROGRESS]
    states = [item["standing"]["state"] for item in items if item["state"] != IN_PROGRESS]
    return {"overdue": states.count(OVERDUE), "due": states.count(DUE),
            "upcoming": states.count(UPCOMING) + states.count(NOT_YET), "in_progress": len(started),
            "to_verify": to_verify}


_EMPTY = {"items": [], "counts": {"overdue": 0, "due": 0, "upcoming": 0, "in_progress": 0, "to_verify": 0}}


@pm_jobs_bp.route("/jobs")
@require_perm(READ_KEY)
def list_jobs():
    """The PM list (§ 6.1): the open jobs at the user's units, judged live, on the asked tab; ``counts`` over the
    open jobs.  No pager on *Due* and *Upcoming*: one open job per active plan bounds the list.  *Done* (S098 § 6.3;
    S099: verified, or done and final), newest first, and *To verify* (S099 § 5.7: done and waiting), oldest done
    first, are paged, with ``total``; their counts are the open jobs' too.  ``counts.to_verify`` on every tab."""
    tab = enum_arg("tab", TABS) or TAB_DUE
    unit_id = int_arg("unit_id", None, minimum=1)
    assigned = enum_arg("assigned", ("me",))
    page = int_arg("page", 1, 1, MAX_PAGE)
    per_page = int_arg("per_page", DEFAULT_PER_PAGE, 1, MAX_PER_PAGE)
    empty = _EMPTY if tab not in _PAGED_TABS else {**_EMPTY, "total": 0, "page": page, "per_page": per_page}
    if tab == TAB_DONE:
        empty = {**empty, "total_skipped": 0}
    with get_db().cursor() as cur:
        unit_ids = accessible_unit_ids(cur, READ_KEY)
        if unit_ids is not None and not unit_ids:
            return jsonify(empty)
        where, params = [], []
        if unit_ids is not None:
            ids = sorted(unit_ids)
            where.append(f"u.id IN ({marks(ids)})")
            params.extend(ids)
        if unit_id is not None:
            where.append("u.id = %s")
            params.append(unit_id)
        if assigned:
            person_id = current_person_id(cur)
            if person_id is None:
                return jsonify(empty)
            # Mine: assigned to me, or performed by me (S098 D11: a job I started for another is mine to finish)
            where.append("(j.assignee_id = %s OR j.performed_by_id = %s)")
            params.extend([person_id, person_id])
        today = _now(cur).date()
        filters = "".join(f" AND {condition}" for condition in where)
        cur.execute(_JOB_SELECT + filters, params)
        items = jobs_out(cur, cur.fetchall(), today)
        counts = _counts(items, count(cur, _COUNT_FROM + _WAITING_WHERE + filters, params))
        if tab in _PAGED_TABS:
            tab_where, order = _PAGED_TABS[tab]
            total = count(cur, _COUNT_FROM + tab_where + filters, params)
            cur.execute(f"{JOB_FROM}{tab_where}{filters} ORDER BY {order} LIMIT %s OFFSET %s",
                        [*params, per_page, (page - 1) * per_page])
            finished = add_sign_off(cur, [job_item(row, None, None, today) for row in cur.fetchall()],
                                    with_findings=True)
            answer = {"items": finished, "counts": counts, "total": total, "page": page, "per_page": per_page}
            if tab == TAB_DONE:   # S101 (BR1-01): the count line says "10 done · 2 skipped"
                answer["total_skipped"] = count(cur, _COUNT_FROM + tab_where + _SKIPPED_AND + filters, params)
            return jsonify(answer)
        shown = [item for item in items if tab_of(item["state"], item["standing"]["state"]) == tab]
        add_sign_off(cur, shown, with_findings=False)
    return jsonify({"items": shown, "counts": counts})


def _trigger_meter_row(plan, resolution, shared):
    """The trigger meter a plan resolves to, in the joined row's shape _meter_out reads (S104 § 5.3)."""
    trigger = resolution["trigger"]
    if trigger is None:
        return {"meter_type_id": None}
    meter_type = shared["meter_types"][trigger[1]]
    return {"meter_equipment_id": trigger[0], "meter_type_id": trigger[1], "meter_code": shared["codes"][trigger[0]],
            "t_name": meter_type["name"], "t_unit": meter_type["unit"], "t_kind": meter_type["kind"],
            "t_decimals": meter_type["decimals"]}


def plan_schedules(cur, plans, resolutions, site_id, now):
    """The card's ``schedule`` of each plan (§ 6.3) -> ``{plan_id: schedule or None}``.  None for every plan without
    pm_job:read at the node's site, and for an unlinked plan.  ``plans`` are PLAN_SELECT rows and ``resolutions``
    their plan_resolutions (the card's one pass, S104 § 5.3).  The open jobs in one query (and one readings query);
    the next due point (schedule_inputs, on the resolved trigger meter) only for a plan in force that applies and has
    no open job; a plan that makes no job has neither (its stop remark says why)."""
    out = {plan["id"]: None for plan in plans}
    linked = [plan for plan in plans if plan["linked"]]
    if not linked or not has_perm_at(READ_KEY, site_id):
        return out
    ids = [plan["id"] for plan in linked]
    cur.execute(f"{_JOB_SELECT} AND j.plan_id IN ({marks(ids)})", ids)
    open_jobs = {item["plan"]["id"]: item for item in jobs_out(cur, cur.fetchall(), now.date())}
    for plan in linked:
        job = open_jobs.get(plan["id"])
        resolution = resolutions[plan["id"]]
        if job is not None:
            out[plan["id"]] = {
                "open_job": {key: job[key] for key in ("id", "serial", "state", "standing", "due_on", "due_meter",
                                                       "days_past")},
                "next_due": None, "meter": job["meter"],
            }
            continue
        if plan["trigger_kind"] == BEFORE_USE or resolution["stop"] is not None:
            out[plan["id"]] = {"open_job": None, "next_due": None, "meter": None}
            continue
        inputs = schedule_inputs(cur, plan, now, None, resolution["trigger"])
        due = inputs["due"]
        out[plan["id"]] = {
            "open_job": None,
            "next_due": {"due_on": due.due_on and due.due_on.isoformat(), "due_meter": format_number(due.due_meter),
                         "no_reading": inputs["standing"].no_reading},
            "meter": _meter_out(_trigger_meter_row(plan, resolution, resolutions[None]), inputs["reading"],
                                inputs["offset"]),
        }
    return out
