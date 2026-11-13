"""PM work — doing one PM job (docs/steps/S098-pm-job-phone/1-brief.md; R03.4): the job page, *Start*, one item's
result, the performer and *Mark job done*.  S099 (docs/steps/S099-pm-verify/1-brief.md; R03.5): *Verify job* and
*Send back* of a done job that waits for verification; Mark done copies the plan's needs_verification onto the job.
S101 (docs/steps/S101-pm-reschedule-skip/1-brief.md; R03.9): *Reschedule job* and *Skip job* of a due job, by a
pm_job:verify holder at the site, always with a reason.

Thin shell: pm_work_core holds the rules (the copy at Start, an item's result, the state table, the time window);
this module locks, reads, stores, writes the job's timeline line and answers the job page.  A reading item that
names a meter logs its value through meters.py's shared path (meters.lock_node, meter_in_force, write_reading), so
there is no second insert path of meter_readings (CLAUDE.md § SMTW-Review, *Meter readings (S039)*).

ACCESS (§ 5.2).  The page: pm_job:read, the job's node's current root unit among accessible_unit_ids(cur,
"pm_job:read"), else 404.  The writes: require_perm("pm_job:work"), then load_node_for_user(…, key="pm_job:work"):
404 by equipment:read's units, then 403 without pm_job:work at the node's site.  Every pm_job:work holder holds
pm_job:read (test_pm_job_work_key).  Any holder at the site works any job there (D3).  S099: verify and send back
the same way with pm_job:verify (require_perm, then load_node_for_user's 404 and 403 at the site), then the job's
state (verify_error); every holder holds pm_job:read (test_pm_job_verify_key).

LOCK ORDER (equipment.py's numbers; § 5.7).  The database runs REPEATABLE READ: a locking read sees the latest
committed row and does not start the snapshot; the first plain read does.  Pool connections are autocommit, so a
read before ``transaction(conn)`` is its own snapshot and ends with it.  The rule: every write takes the plan (6e),
then the job (6f), then any node lock, before any plain read of its transaction.  The job's plan_id and equipment_id
never change, nor do a result's item_type, meter_equipment_id and meter_type_id (copied at Start), so each route
reads them before the transaction, plainly (the pre-read; 404 when missing).
- Start: (6e) LOCK_PLAN → (6f) the job FOR UPDATE (its state) → (1) the job's node LOCK IN SHARE MODE (SHARE_NODE;
  scrapped from it) → plain: the access check, person_at_site, the plan with its template and the template's active
  items (S104: written only under the template's (6g), never locked here; a save racing a Start gives either list,
  both valid at that moment, D10), the meters in force on the node and its ancestors → the result inserts (shared
  foreign-key locks: the job, held; the template item; the meter's node; the meter type), the job update (with the
  template's name, D8), the event insert (the performer's people row, shared) → commit.
- An item: (6e) → (6f) → for a result that names a meter, (1) the meter's node FOR UPDATE through meters.lock_node
  (the node or an ancestor; its own plain access read follows at once and starts the snapshot) → plain: the job's
  node access, the result row (written only under (6f)), the meter type, then the meter in force, the old reading,
  the same minute, the neighbours (meters.write_reading) → the old reading's update (only a reading of source pm the
  job logged), the reading insert, the result update → commit.
  A save the job's state refuses (done, cancelled) answers after (6f) with the plain access check and takes
  no node lock (CR1-02).
- The performer: (6e) → (6f) → plain (access, person_at_site) → the job update and the event → commit.
- Mark done: (6e) → (6f) → (1) the job's node LOCK IN SHARE MODE (its lifecycle for settle_plan_job) → plain
  (access, the job's latest sent_back line (written only under (6f), so current), the results, the readings for
  done_meter) → the job update (with the plan's needs_verification, from the locked plan row), the event, then
  pm_jobs.settle_plan_job (plain reads, then for a new job (6) the PM: counter and the inserts) → commit.
- Verify (S099 § 5.6): (6e) → (6f) (the state and needs_verification from it) → SELECT NOW() → plain (access,
  current_person_id) → the job update and the verified event (shared foreign-key locks: the job, held; the
  verifier's people row) → commit.
- Send back (S099 § 5.6): (6e) → (6f) → (1) the job's node LOCK IN SHARE MODE (scrapped from it) → plain (access,
  current_person_id, the plan's open job: every writer of a plan's job rows holds (6e) first) → for an open job
  still due, its UPDATE to cancelled (its row exclusive, its uq_pm_jobs_open_plan entry removed) and its cancelled
  event (pm_jobs.cancel_job) → this job's UPDATE back to in_progress (the unique check meets only the entry removed
  just before) and the sent_back event → commit.  This is the one exception to "(6f) one job per transaction": the
  second job row of the same plan is written by a plain UPDATE under the same (6e), never with a second FOR UPDATE.
  A rollback undoes the open job's cancel with the send-back.
- Reschedule (S101 § 5.6): (6e) → (6f) → (1) the job's node LOCK IN SHARE MODE (scrapped from it) → SELECT NOW() →
  plain (access, the plan's last base job, the readings, the meter type, current_person_id) → the job's UPDATE (its
  row, held) → the rescheduled event (shared foreign-key locks: the job, held; the person's people row) → commit.
  No (6), no second job.
- Skip (S101 § 5.6): (6e) → (6f) → (1) shared → SELECT NOW() → plain (access, the readings for done_meter,
  current_person_id) → the job's UPDATE to skipped (its uq_pm_jobs_open_plan entry removed) → the skipped event →
  pm_jobs.settle_plan_job (plain reads; it sees the skip as the last base; for a new job (6) the PM: counter and the
  inserts) → commit.  The sequence of Mark done; a rollback undoes the skip and the new job together.
- The job page: plain, no lock.
No deadlock cycle:
- (6e) then (6f): every PM write that touches a job takes its plan first (S097's run and plan save, which update a
  job only while it is due, and every route here).  No path holds a job and waits on its plan.
- The node after (6e)/(6f): the node writers (equipment.py, meters.py's readings and meter writes, the scrap) hold
  the node and never wait on a plan or a job row, so a PM write waits behind them and finishes.  Two PM writes on
  jobs of different plans whose meters share a node queue on that node.  A plan save or the run holds a node shared
  and waits on nothing held here (they take their own plan only).
- The scrap and Start: the scrap holds the node and its parts FOR UPDATE and counts started jobs plainly
  (equipment._check_no_started_pm_jobs); Start waits on the node's shared lock behind it, then reads scrapped from
  its locked row: 409.  The accepted case (as pm_plans.py's): Start holds a part (1) shared and its result insert
  takes the machine's row shared through the meter foreign key, while a scrap of the machine holds the machine and
  waits for the part: InnoDB rolls one back (1213, a plain 500); a retry gives the right answer.
- meter_readings rows: only meters.remove_reading and this path update a reading, both under the reading's node (1)
  exclusive, so they serialise there.
- (6) the PM: counter is taken only inside settle_plan_job, last before its inserts.  Mark done holds (6e), (6f),
  the node shared, then (6); a run on another plan never waits on Mark done's plan or job.
- S099: two writes on one plan's jobs (verify, send back, the routes above, S097's run and plan save) queue on
  (6e); the second reads the first's committed job (a verify after a send-back: 409 NOT_DONE_YET; a send-back after
  a verify: 409 ALREADY_VERIFIED).  The open job's other writers (Start, an item, Mark done, the run's refresh and
  cancel) hold the same (6e) first, so none holds the open job's row while send back writes it.  The node is taken
  shared after (6e) and (6f), as Start; the scrap counts started jobs plainly after its node locks, so it either
  sees the sent-back job in progress (409) or makes send back read scrapped (409).  Send back's unique-key check
  may make another plan's job insert into a nearby gap of uq_pm_jobs_open_plan wait until this commit; that
  transaction holds nothing this route needs, so it is a wait, not a cycle.
- S101: reschedule and skip queue on (6e) with every other writer of the plan's jobs; the second reads the first's
  committed job after its locks (a skip after a skip, or a reschedule after a skip: 409 JOB_SKIPPED; a skip after a
  Start: 409 STARTED_NO_MOVE).  The node is taken shared, as Start and Mark done.  One job per transaction holds:
  the skip's new job is inserted by settle_plan_job, not locked.
"""

from decimal import Decimal

from flask import Blueprint, jsonify

import meters
import pm_jobs
from api_common import ApiError, actor, clean_body
from auth_utils import current_person_id, has_perm_at, require_perm
from db_helpers import get_db, insert_row, marks, row_to_dict, transaction, update_row
from equipment import SCRAPPED_MESSAGE, accessible_unit_ids, load_node_for_user
from equipment_core import SCRAPPED
from meters_core import format_number, to_minute
from pm_jobs_core import (
    DONE, DUE_STATE, IN_PROGRESS, OPEN_STATES, SKIPPED, VERIFIED, due_copies, due_from_job, job_changes,
)
from pm_links_core import METER_READING, missing_text
from pm_schedule_core import BEFORE_USE, timeliness
from pm_templates_core import item_limits_text, meter_label
from pm_work_core import (
    BEFORE_USE_NO_MOVE, DONE_EVENT, FILL, MARK_DONE, NO_ITEMS, PERFORMED_BY_NEEDED, PERFORMER, PERFORMER_EVENT,
    RESCHEDULED_EVENT, SEND_BACK_CHANGES, SENT_BACK_EVENT, SKIP_CHANGES, SKIPPED_EVENT, START, STARTED_EVENT,
    VERIFIED_EVENT, VERIFY_KEY, WORK_KEY, cannot_start, done_meter_counted, done_time_error, is_filled, move_error,
    move_reason,
    not_all_filled, not_logged, open_job_cancelled, open_job_started, reschedule_override, reschedule_summary,
    result_changes, result_rows, same_minute_pm, self_verified, state_error, unfilled_count, validate_result,
    verify_error, verify_remark,
)
from tickets import PERSON_AT_SITE, person_at_site
from tickets_core import EVENT_TIME_FORMAT, parse_event_time

pm_work_bp = Blueprint("pm_work", __name__)

READ_KEY = pm_jobs.READ_KEY
PM_SOURCE = "pm"   # meter_readings.source of a reading a job's item logged

# (6f): the job row, always right after its plan (6e); one copy in pm_jobs.py (S102's scan takes it too)
_LOCK_JOB = pm_jobs.LOCK_JOB

_METER_TYPE_COLUMNS = "t.name AS t_name, t.unit AS t_unit, t.kind AS t_kind, t.decimals AS t_decimals"
# S104: the template's active items now (a job not started yet shows them; Start copies them), and a started job's
# results
_TEMPLATE_ITEMS = (
    f"SELECT i.*, {_METER_TYPE_COLUMNS} FROM pm_template_items i"
    " LEFT JOIN meter_types t ON t.id = i.meter_type_id"
    " WHERE i.template_id = %s AND i.active = 1 ORDER BY i.position, i.id"
)
_RESULTS = (
    f"SELECT r.*, me.code AS meter_code, {_METER_TYPE_COLUMNS},"
    " rd.removed_at IS NULL AND rd.id IS NOT NULL AS logged, fp.name AS filled_by_name"
    " FROM pm_job_results r"
    " LEFT JOIN equipment me ON me.id = r.meter_equipment_id"
    " LEFT JOIN meter_types t ON t.id = r.meter_type_id"
    " LEFT JOIN meter_readings rd ON rd.id = r.reading_id"
    " LEFT JOIN people fp ON fp.username = r.filled_by"
)
_EVENTS = (
    "SELECT ev.*, p.name AS person_name, cp.name AS cp_name FROM pm_job_events ev"
    " LEFT JOIN people p ON p.id = ev.person_id"
    " LEFT JOIN people cp ON cp.username = ev.created_by"
    " WHERE ev.job_id = %s ORDER BY ev.occurred_at, ev.id"
)


# ---------------------------------------------------------------------------
# The job page (§ 6.2)
# ---------------------------------------------------------------------------

def _meter_of(row):
    meter_type = pm_jobs.meter_type_out(row)   # the meter type's shape, one copy (BS1-03)
    if meter_type is None:
        return None
    return {"equipment_id": row["meter_equipment_id"], "code": row["meter_code"], "meter_type": meter_type}


def _item_out(row, is_result):
    """A template item resolved on the machine (``is_result`` False: a job not started; _resolved_items) or a result
    as the page shows it."""
    meter = _meter_of(row)
    result = row if is_result else {}
    return {
        "id": row["id"] if is_result else None,
        "template_item_id": row["template_item_id"] if is_result else row["id"],
        "position": row["position"], "item_type": row["item_type"], "text": row["text"],
        "help_text": row["help_text"], "reading_kind": row["reading_kind"], "unit": row["unit"], "meter": meter,
        "min_value": format_number(row["min_value"]), "max_value": format_number(row["max_value"]),
        "limits_text": item_limits_text(row, meter and meter["meter_type"], meter and meter["code"]),
        "outcome": result.get("outcome"), "value": format_number(result.get("value")),
        "limit_state": result.get("limit_state"), "remark": result.get("remark"),
        "logged": bool(result.get("logged")),
        "filled_at": row_to_dict({"at": result.get("filled_at")})["at"],
        "filled_by_name": result.get("filled_by_name") or result.get("filled_by"),
    }


def _results(cur, job_id):
    cur.execute(_RESULTS + " WHERE r.job_id = %s ORDER BY r.position", (job_id,))
    return cur.fetchall()


def _resolved_items(cur, plan):
    """The template's active items with each *Meter reading* item's meter resolved on the plan's machine (S104
    § 5.3: the node whose meter it logs, and that meter's limits in force, D6) -> ``(items, missing type names)``.
    One resolution for every item (pm_jobs.plan_resolutions): one meter per type on a node, its own or a linked one
    (S104 A1.6.2), so a type named twice resolves to the same node."""
    cur.execute(_TEMPLATE_ITEMS, (plan["template_id"],))
    rows = cur.fetchall()
    resolutions = pm_jobs.plan_resolutions(cur, [plan])
    resolution, shared = resolutions[plan["id"]], resolutions[None]
    items, missing = [], []
    for row in rows:
        item = dict(row, meter_equipment_id=None, meter_code=None)
        if row["reading_kind"] == METER_READING:
            node_id = resolution["resolved"].get(row["meter_type_id"])
            if node_id is None:
                if row["t_name"] not in missing:
                    missing.append(row["t_name"])
            else:
                meter = next(m for m in shared["meters"][node_id] if m["meter_type"]["id"] == row["meter_type_id"])
                limits = [None if meter[key] is None else Decimal(meter[key]) for key in ("min_value", "max_value")]
                item.update(meter_equipment_id=node_id, meter_code=shared["codes"][node_id],
                            min_value=limits[0], max_value=limits[1])
        items.append(item)
    return items, missing


def _items(cur, job):
    """§ 6.2: a due job shows the template's active items now, resolved on the machine; a cancelled or skipped job
    that never started none; else the job's results."""
    if job["state"] == DUE_STATE:
        items, _ = _resolved_items(cur, pm_jobs.plan_row(cur, job["plan_id"]))
        return [_item_out(row, is_result=False) for row in items]
    return [_item_out(row, is_result=True) for row in _results(cur, job["id"])]


def _events(cur, job_id, performer_id):
    """The timeline (§ 6.2); a verified line says whether its verifier is the job's *Performed by* (S099 D5)."""
    cur.execute(_EVENTS, (job_id,))
    out = []
    for row in cur.fetchall():
        plain = row_to_dict(row)
        out.append({
            "event": row["event"], "occurred_at": plain["occurred_at"], "from_state": row["from_state"],
            "to_state": row["to_state"],
            "person": None if row["person_id"] is None else {"id": row["person_id"], "name": row["person_name"]},
            "due_on": plain["due_on"], "due_meter": format_number(row["due_meter"]), "remark": row["remark"],
            # The login when no person matches; pm_generate stays as it is (the page words it)
            "created_by_name": row["cp_name"] or row["created_by"],
            "self_verified": (self_verified(row["person_id"], performer_id)
                              if row["event"] == VERIFIED_EVENT else None),
        })
    return out


def _open_job(cur, plan_id):
    """The plan's open job (at most one, uq_pm_jobs_open_plan), plainly: after (6e) on a write (§ 5.4 step 3)."""
    cur.execute(f"SELECT id, serial, state FROM pm_jobs WHERE plan_id = %s AND state IN ({marks(OPEN_STATES)})",
                (plan_id, *OPEN_STATES))
    return cur.fetchone()


def _job_row(cur, job_id):
    return pm_jobs.job_row(cur, job_id)


def job_detail(cur, job_id):
    """The job page's answer (§ 6.2), plain reads.  The header is the list's item (pm_jobs.job_item, one copy): an
    open job judged live (pm_jobs.jobs_out), a closed one with no standing."""
    row = _job_row(cur, job_id)
    now = pm_jobs._now(cur)
    if row["state"] in (DUE_STATE, IN_PROGRESS):
        (out,) = pm_jobs.jobs_out(cur, [row], now.date())
    else:
        out = pm_jobs.job_item(row, None, None, now.date())
    items = _items(cur, row)
    may_work = has_perm_at(WORK_KEY, row["site_id"])
    out["equipment"]["lifecycle"] = row["e_lifecycle"]
    out["plan"].update(active=bool(row["pl_active"]), needs_verification=bool(row["pl_needs_verification"]))
    pm_jobs.add_sign_off(cur, [out], with_findings=True)      # S099: findings, verification, sent_back
    # S099 § 6.2: the plan's open job beside a job waiting for verification, and who may verify or send back
    open_job = _open_job(cur, row["plan_id"]) if out["awaits_verification"] else None
    may_verify = has_perm_at(VERIFY_KEY, row["site_id"])
    can_verify = out["awaits_verification"] and may_verify
    # S101 § 6.2: a due job on a machine not scrapped may be skipped; moved too unless its plan is before-use
    can_skip = may_verify and row["state"] == DUE_STATE and row["e_lifecycle"] != SCRAPPED
    events = _events(cur, job_id, row["performed_by_id"])
    out.update(
        done_meter=format_number(row["done_meter"]), items=items,
        filled_count=sum(1 for item in items if item["id"] is not None and is_filled(item)),
        item_count=len(items), events=events,
        can_skip=can_skip, can_reschedule=can_skip and row["pl_trigger_kind"] != BEFORE_USE,
        reschedule=reschedule_summary(events),
        can_start=may_work and row["state"] == DUE_STATE and row["e_lifecycle"] != SCRAPPED,
        can_work=may_work and row["state"] == IN_PROGRESS,
        open_job=open_job, can_verify=can_verify,
        can_send_back=(can_verify and row["e_lifecycle"] != SCRAPPED
                       and (open_job is None or open_job["state"] == DUE_STATE)),
    )
    return out


@pm_work_bp.route("/jobs/<int:job_id>")
@require_perm(READ_KEY)
def get_job(job_id):
    with get_db().cursor() as cur:
        row = _job_row(cur, job_id)
        unit_ids = None if row is None else accessible_unit_ids(cur, READ_KEY)
        if row is None or (unit_ids is not None and row["unit_id"] not in unit_ids):
            raise ApiError("Not found", 404)
        return jsonify(job_detail(cur, job_id))


# ---------------------------------------------------------------------------
# The writes' common steps
# ---------------------------------------------------------------------------

def _body():
    """The JSON object (clean_body's 400 otherwise); the fields are judged route by route, unknown ones ignored."""
    return clean_body(lambda body, _creating: (body, []), creating=False)


def _pre_read(cur, job_id):
    """The job's plan_id and equipment_id, which never change, read before the transaction (§ 5.7): 404."""
    cur.execute("SELECT plan_id, equipment_id FROM pm_jobs WHERE id = %s", (job_id,))
    ids = cur.fetchone()
    if ids is None:
        raise ApiError("Not found", 404)
    return ids


def _lock_job(cur, job_id, ids):
    """(6e) the plan, then (6f) the job -> (plan row, job row)."""
    cur.execute(pm_jobs.LOCK_PLAN, (ids["plan_id"],))
    plan = cur.fetchone()
    cur.execute(_LOCK_JOB, (job_id,))
    return plan, cur.fetchone()


def _share_node(cur, node_id):
    cur.execute(pm_jobs.SHARE_NODE, (node_id,))   # (1) shared
    return cur.fetchone()


def _work_access(cur, node_id, state, action):
    """404 outside the user's units, 403 without pm_job:work at the node's site, 409 for the job's state -> node."""
    _, node = load_node_for_user(cur, node_id, for_update=False, key=WORK_KEY)
    refusal = state_error(state, action)
    if refusal:
        raise ApiError(*refusal)
    return node


def _performer(cur, raw, site_id):
    """``performed_by_id``: an integer ≥ 1 (not a boolean) of an active person with a membership at the site."""
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 1:
        raise ApiError(PERFORMED_BY_NEEDED, 400, "performed_by_id")
    if person_at_site(cur, raw, site_id) is None:
        raise ApiError(PERSON_AT_SITE, 400, "performed_by_id")
    return raw


def _event_time(raw, now, field, not_before=None, sent_back_at=None):
    """*Started* or *Done*: null or absent is now (to the minute); else YYYY-MM-DDTHH:MM, to the minute, in the
    window, not before ``not_before`` (*Started*) nor ``sent_back_at`` (S099: the latest send-back): one place
    judges a time (done_time_error, S099 BS1-02)."""
    if raw is None:
        return to_minute(now)
    moment, message = parse_event_time(raw)
    if message:
        raise ApiError(EVENT_TIME_FORMAT, 400, field)
    moment = to_minute(moment)
    message = done_time_error(moment, now, not_before, sent_back_at)
    if message:
        raise ApiError(message, 400, field)
    return moment


def _answer(conn, job_id):
    with conn.cursor() as cur:
        return jsonify(job_detail(cur, job_id))


# ---------------------------------------------------------------------------
# Start (§ 5.3)
# ---------------------------------------------------------------------------

@pm_work_bp.route("/jobs/<int:job_id>/start", methods=["POST"])
@require_perm(WORK_KEY)
def start_job(job_id):
    body = _body()
    conn = get_db()
    with conn.cursor() as cur:
        ids = _pre_read(cur, job_id)
    with transaction(conn), conn.cursor() as cur:
        _, job = _lock_job(cur, job_id, ids)                      # (6e), (6f)
        locked_node = _share_node(cur, ids["equipment_id"])       # (1) shared
        now = pm_jobs._now(cur)
        node = _work_access(cur, ids["equipment_id"], job["state"], START)
        performer_id = _performer(cur, body.get("performed_by_id"), node["site_id"])
        started_at = _event_time(body.get("started_at"), now, "started_at")
        if locked_node["lifecycle"] == SCRAPPED:
            raise ApiError(SCRAPPED_MESSAGE, 409)
        # S104 § 5.7: the template's active items and name, read plainly after the locks; each Meter reading item's
        # meter resolved on the machine now (a type gone since the settle: 409; the next settle cancels the job)
        plan = pm_jobs.plan_row(cur, ids["plan_id"])
        items, missing = _resolved_items(cur, plan)
        if not items:
            raise ApiError(NO_ITEMS, 409)   # defensive: a template keeps at least one active item
        if missing:
            raise ApiError(cannot_start(missing_text(missing, plan["node_code"])), 409)
        for row in result_rows(items):
            insert_row(cur, "pm_job_results", {"job_id": job_id, **row}, actor())
        # D8: the job keeps the template's name from Start, so a later rename leaves the record as it was
        update_row(cur, "pm_jobs", job_id, {"state": IN_PROGRESS, "performed_by_id": performer_id,
                                            "started_at": started_at, "title": plan["title"]}, actor())
        pm_jobs.add_event(cur, job_id, STARTED_EVENT, started_at, actor(), from_state=DUE_STATE,
                           to_state=IN_PROGRESS, person_id=performer_id)
    return _answer(conn, job_id)


# ---------------------------------------------------------------------------
# One item (§ 5.4, § 5.5)
# ---------------------------------------------------------------------------

def _meter_type(cur, meter_type_id):
    cur.execute("SELECT id, name, unit, kind, decimals FROM meter_types WHERE id = %s", (meter_type_id,))
    return cur.fetchone()


def _linked_reading(cur, reading_id):
    if reading_id is None:
        return None
    cur.execute("SELECT id, meter_type_id, value, is_reset, source, removed_at FROM meter_readings WHERE id = %s",
                (reading_id,))
    return cur.fetchone()


def _log_reading(cur, result, clean, raw_value, meter_lock, meter_type, linked, started_at):
    """§ 5.5 steps 1–6 for a result that names a meter -> ``(reading_id, meter_note)``: the reading the result names
    after the save, and the note when the meter is gone since Start (the value is then kept on the job only).
    ``meter_lock`` is meters.lock_node's (locked row, node): the model id from the locked row (S039 BR1-17).

    The job's own reading is removed before the meter-in-force check (CR1-01, a stated change of § 5.5 step 1):
    removing needs only the node and the meter type, and a result whose meter is gone lets go of its link, so the
    job never names a reading of another value (D4) and an NA keeps chk_pm_job_results_reading."""
    node_id = result["meter_equipment_id"]
    locked, node = meter_lock
    if linked is not None and linked["source"] == PM_SOURCE and linked["removed_at"] is None:
        # The job owns the reading it logged (D8); removed first, so the new one does not meet it at the minute
        meters.remove_reading_row(cur, node_id, linked, field="value")
    meter = meters.meter_in_force(cur, node_id, locked["model_id"], result["meter_type_id"])
    if meter is None:
        return None, not_logged(meter_label(node["code"], meter_type))
    if clean["value"] is None:
        return None, None   # NA logs nothing
    same = meters.reading_at_minute(cur, node_id, result["meter_type_id"], started_at)
    if same is not None:
        if same["value"] == clean["value"] and bool(same["is_reset"]) == clean["is_reset"]:
            return same["id"], None   # typed on the readings sheet too: the result names it
        raise ApiError(same_minute_pm(started_at), 409, "value")
    row = meters.write_reading(cur, node_id, meter, {"value": raw_value, "is_reset": clean["is_reset"], "note": None},
                               started_at, PM_SOURCE)
    return row["id"], None


def _result_answer(conn, job_id, result_id, meter_note):
    with conn.cursor() as cur:
        rows = _results(cur, job_id)
    item = next(_item_out(row, is_result=True) for row in rows if row["id"] == result_id)
    return jsonify({"item": item, "filled_count": len(rows) - unfilled_count(rows), "item_count": len(rows),
                    "meter_note": meter_note})


@pm_work_bp.route("/jobs/<int:job_id>/results/<int:result_id>", methods=["PUT"])
@require_perm(WORK_KEY)
def save_result(job_id, result_id):
    body = _body()
    conn = get_db()
    with conn.cursor() as cur:
        ids = _pre_read(cur, job_id)
        cur.execute("SELECT meter_equipment_id FROM pm_job_results WHERE id = %s AND job_id = %s",
                    (result_id, job_id))
        copied = cur.fetchone()   # copied at Start, never updated
        if copied is None:
            raise ApiError("Not found", 404)
    meter_note = None
    with transaction(conn), conn.cursor() as cur:
        _, job = _lock_job(cur, job_id, ids)                                  # (6e), (6f)
        if state_error(job["state"], FILL) is not None:
            # Nothing will be written: 404 / 403, else the state's 409, before any node lock, so a late save on a
            # done job whose machine was scrapped since answers JOB_DONE, not the scrapped refusal (CR1-02)
            _work_access(cur, ids["equipment_id"], job["state"], FILL)
        meter_lock = None
        if copied["meter_equipment_id"] is not None:
            meter_lock = meters.lock_node(cur, copied["meter_equipment_id"], WORK_KEY)   # (1)
        now = pm_jobs._now(cur)
        _work_access(cur, ids["equipment_id"], job["state"], FILL)
        cur.execute("SELECT * FROM pm_job_results WHERE id = %s", (result_id,))
        result = cur.fetchone()
        meter_type = None if result["meter_type_id"] is None else _meter_type(cur, result["meter_type_id"])
        clean, error = validate_result(body, result, meter_type)
        if error:
            raise ApiError(error[1], 400, error[0])
        linked = _linked_reading(cur, result["reading_id"])
        changes = result_changes(result, clean, None if linked is None else linked["is_reset"])
        if changes:
            update = {column: value for column, value in changes.items() if column != "is_reset"}
            if meter_type is not None and ({"outcome", "value", "is_reset"} & changes.keys()):
                reading_id, meter_note = _log_reading(cur, result, clean, body.get("value"), meter_lock,
                                                      meter_type, linked, job["started_at"])
                if reading_id != result["reading_id"]:
                    update["reading_id"] = reading_id
            update.update(filled_at=now, filled_by=actor())
            cur.execute(f"UPDATE pm_job_results SET {', '.join(f'{column} = %s' for column in update)}"
                        " WHERE id = %s", (*update.values(), result_id))
    return _result_answer(conn, job_id, result_id, meter_note)


# ---------------------------------------------------------------------------
# The performer (§ 6.1)
# ---------------------------------------------------------------------------

@pm_work_bp.route("/jobs/<int:job_id>", methods=["PUT"])
@require_perm(WORK_KEY)
def change_performer(job_id):
    body = _body()
    conn = get_db()
    with conn.cursor() as cur:
        ids = _pre_read(cur, job_id)
    with transaction(conn), conn.cursor() as cur:
        _, job = _lock_job(cur, job_id, ids)                      # (6e), (6f)
        now = pm_jobs._now(cur)
        node = _work_access(cur, ids["equipment_id"], job["state"], PERFORMER)
        if "performed_by_id" in body:
            performer_id = _performer(cur, body["performed_by_id"], node["site_id"])
            if performer_id != job["performed_by_id"]:
                update_row(cur, "pm_jobs", job_id, {"performed_by_id": performer_id}, actor())
                pm_jobs.add_event(cur, job_id, PERFORMER_EVENT, now, actor(), person_id=performer_id)
    return _answer(conn, job_id)


# ---------------------------------------------------------------------------
# Mark job done (§ 5.6)
# ---------------------------------------------------------------------------

def _done_meter(cur, job, done_at):
    """S095 § 5.2's meter value at T = done_at on the job's own copy of its trigger meter (S104 § 5.3): the latest
    reading at or before it, else the first after it, else None (raw: the next job's base, S097 § 5.3)."""
    if job["meter_equipment_id"] is None:
        return None
    meter = (job["meter_equipment_id"], job["meter_type_id"])
    reading = meters.last_readings(cur, [meter[0]], until=done_at).get(meter)
    if reading is None:
        reading = meters.first_reading_after(cur, meter[0], meter[1], done_at)
    return None if reading is None else reading["value"]


def _sent_back_at(cur, job_id):
    """The job's latest send-back (S099 § 5.5, BR1-02), or None: the floor of a second *Done*."""
    cur.execute("SELECT MAX(occurred_at) AS at FROM pm_job_events WHERE job_id = %s AND event = %s",
                (job_id, SENT_BACK_EVENT))
    return cur.fetchone()["at"]


@pm_work_bp.route("/jobs/<int:job_id>/done", methods=["POST"])
@require_perm(WORK_KEY)
def mark_done(job_id):
    body = _body()
    conn = get_db()
    with conn.cursor() as cur:
        ids = _pre_read(cur, job_id)
    with transaction(conn), conn.cursor() as cur:
        _, job = _lock_job(cur, job_id, ids)                      # (6e), (6f)
        locked_node = _share_node(cur, ids["equipment_id"])       # (1) shared
        now = pm_jobs._now(cur)
        _work_access(cur, ids["equipment_id"], job["state"], MARK_DONE)
        done_at = _event_time(body.get("done_at"), now, "done_at", not_before=job["started_at"],
                              sent_back_at=_sent_back_at(cur, job_id))
        cur.execute("SELECT outcome, value FROM pm_job_results WHERE job_id = %s", (job_id,))
        results = cur.fetchall()
        unfilled = unfilled_count(results)
        if unfilled:
            raise ApiError(not_all_filled(unfilled, len(results)), 409)
        done_meter = _done_meter(cur, job, done_at)
        judged = timeliness(due_from_job(job), done_at.date(), done_meter_counted(done_meter, job["meter_offset"]))
        # S099: the setting is copied onto the job now; S104 D10: from the template, read plainly after (6e)
        needs_verification = pm_jobs.plan_row(cur, ids["plan_id"])["needs_verification"]
        update_row(cur, "pm_jobs", job_id,
                   {"state": DONE, "done_at": done_at, "done_meter": done_meter, "timeliness": judged,
                    "needs_verification": needs_verification}, actor())
        pm_jobs.add_event(cur, job_id, DONE_EVENT, done_at, actor(), from_state=IN_PROGRESS, to_state=DONE,
                           person_id=job["performed_by_id"])
        pm_jobs.settle_plan_job(cur, ids["plan_id"], locked_node["lifecycle"], now, actor())
    return _answer(conn, job_id)


# ---------------------------------------------------------------------------
# Verify job and send back (S099 § 5.3, § 5.4)
# ---------------------------------------------------------------------------

def _verify_access(cur, node_id, job):
    """404 outside the user's units, 403 without pm_job:verify at the node's site, then the job's 409."""
    load_node_for_user(cur, node_id, for_update=False, key=VERIFY_KEY)
    refusal = verify_error(job["state"], job["needs_verification"])
    if refusal:
        raise ApiError(*refusal)


def _sign_off_remark(body, needed):
    remark, error = verify_remark(body, needed)
    if error:
        raise ApiError(error[1], 400, error[0])
    return remark


@pm_work_bp.route("/jobs/<int:job_id>/verify", methods=["POST"])
@require_perm(VERIFY_KEY)
def verify_job(job_id):
    body = _body()
    conn = get_db()
    with conn.cursor() as cur:
        ids = _pre_read(cur, job_id)
    with transaction(conn), conn.cursor() as cur:
        _, job = _lock_job(cur, job_id, ids)                      # (6e), (6f)
        # To the minute, as every time of the job, so the timeline's order is the order of the minutes (D9)
        now = to_minute(pm_jobs._now(cur))
        _verify_access(cur, ids["equipment_id"], job)
        remark = _sign_off_remark(body, needed=False)
        # done_at, done_meter, timeliness and needs_verification stay: the next job's base does not move
        update_row(cur, "pm_jobs", job_id, {"state": VERIFIED}, actor())
        pm_jobs.add_event(cur, job_id, VERIFIED_EVENT, now, actor(), from_state=DONE, to_state=VERIFIED,
                          person_id=current_person_id(cur), remark=remark)
    return _answer(conn, job_id)


@pm_work_bp.route("/jobs/<int:job_id>/send-back", methods=["POST"])
@require_perm(VERIFY_KEY)
def send_back_job(job_id):
    body = _body()
    conn = get_db()
    with conn.cursor() as cur:
        ids = _pre_read(cur, job_id)
    with transaction(conn), conn.cursor() as cur:
        _, job = _lock_job(cur, job_id, ids)                      # (6e), (6f)
        locked_node = _share_node(cur, ids["equipment_id"])       # (1) shared
        now = to_minute(pm_jobs._now(cur))
        _verify_access(cur, ids["equipment_id"], job)
        if locked_node["lifecycle"] == SCRAPPED:
            raise ApiError(SCRAPPED_MESSAGE, 409)   # a job in progress on a scrapped machine could never finish
        remark = _sign_off_remark(body, needed=True)
        person_id = current_person_id(cur)
        open_job = _open_job(cur, ids["plan_id"])   # plain: every writer of the plan's jobs holds (6e) first
        if open_job is not None and open_job["state"] == IN_PROGRESS:
            raise ApiError(open_job_started(open_job["serial"]), 409)
        if open_job is not None:
            # The plan holds one open job only (uq_pm_jobs_open_plan): the one made from a done time that no
            # longer stands is cancelled; the run makes it again from the latest done time (D3)
            pm_jobs.cancel_job(cur, open_job, open_job_cancelled(job["serial"]), now, actor())
        update_row(cur, "pm_jobs", job_id, SEND_BACK_CHANGES, actor())
        pm_jobs.add_event(cur, job_id, SENT_BACK_EVENT, now, actor(), from_state=DONE, to_state=IN_PROGRESS,
                          person_id=person_id, remark=remark)
    return _answer(conn, job_id)


# ---------------------------------------------------------------------------
# Reschedule job and skip job (S101 § 5.3)
# ---------------------------------------------------------------------------

def _move_access(cur, node_id, job, locked_node):
    """404 outside the user's units, 403 without pm_job:verify at the node's site, the job's 409 (a due job only,
    D1), then 409 for a scrapped machine."""
    load_node_for_user(cur, node_id, for_update=False, key=VERIFY_KEY)
    refusal = move_error(job["state"])
    if refusal:
        raise ApiError(*refusal)
    if locked_node["lifecycle"] == SCRAPPED:
        raise ApiError(SCRAPPED_MESSAGE, 409)


def _move_reason(body, skip):
    remark, error = move_reason(body, skip)
    if error:
        raise ApiError(error[1], 400, error[0])
    return remark


@pm_work_bp.route("/jobs/<int:job_id>/reschedule", methods=["POST"])
@require_perm(VERIFY_KEY)
def reschedule_job(job_id):
    body = _body()
    conn = get_db()
    with conn.cursor() as cur:
        ids = _pre_read(cur, job_id)
    with transaction(conn), conn.cursor() as cur:
        _, job = _lock_job(cur, job_id, ids)                      # (6e), (6f)
        locked_node = _share_node(cur, ids["equipment_id"])       # (1) shared
        now = to_minute(pm_jobs._now(cur))
        _move_access(cur, ids["equipment_id"], job, locked_node)
        plan = pm_jobs.plan_row(cur, ids["plan_id"])   # S104: with its template's trigger, plainly after the locks
        if plan["trigger_kind"] == BEFORE_USE:
            # Defensive (BR1-03): the template routes refuse before_use until R03.13; next_due takes no override
            raise ApiError(BEFORE_USE_NO_MOVE, 409)
        # S104 § 5.3: on the job's own copy of the trigger meter
        meter = None if job["meter_equipment_id"] is None else (job["meter_equipment_id"], job["meter_type_id"])
        # The reading and the offset do not depend on the override (BR1-05)
        current = pm_jobs.schedule_inputs(cur, plan, now, None, meter)
        reading = current["reading"]
        counted = None if reading is None else reading["value"] + current["offset"]
        meter_type = None if plan["meter_type_id"] is None else _meter_type(cur, plan["meter_type_id"])
        override, error = reschedule_override(body, plan["trigger_kind"], job, now.date(), counted,
                                              plan["meter_every"], meter_type)
        if error:
            raise ApiError(error[1], 400, error[0])
        reason = _move_reason(body, skip=False)
        inputs = pm_jobs.schedule_inputs(cur, plan, now, override, meter)   # the same snapshot: the same reading
        copies = due_copies(inputs["due"], inputs["offset"], override)
        update_row(cur, "pm_jobs", job_id, job_changes(job, copies, job["assignee_id"]), actor())
        pm_jobs.add_event(cur, job_id, RESCHEDULED_EVENT, now, actor(), due_on=copies["due_on"],
                          due_meter=copies["due_meter"], person_id=current_person_id(cur), remark=reason)
    return _answer(conn, job_id)


@pm_work_bp.route("/jobs/<int:job_id>/skip", methods=["POST"])
@require_perm(VERIFY_KEY)
def skip_job(job_id):
    body = _body()
    conn = get_db()
    with conn.cursor() as cur:
        ids = _pre_read(cur, job_id)
    with transaction(conn), conn.cursor() as cur:
        _, job = _lock_job(cur, job_id, ids)                      # (6e), (6f)
        locked_node = _share_node(cur, ids["equipment_id"])       # (1) shared
        now = to_minute(pm_jobs._now(cur))
        _move_access(cur, ids["equipment_id"], job, locked_node)
        reason = _move_reason(body, skip=True)
        # D6: recorded now, with the meter value now, so the next job counts from the skip by date and by meter;
        # timeliness and needs_verification stay NULL (a skip is not done)
        update_row(cur, "pm_jobs", job_id,
                   {**SKIP_CHANGES, "done_at": now, "done_meter": _done_meter(cur, job, now)}, actor())
        pm_jobs.add_event(cur, job_id, SKIPPED_EVENT, now, actor(), from_state=DUE_STATE, to_state=SKIPPED,
                          person_id=current_person_id(cur), remark=reason)
        pm_jobs.settle_plan_job(cur, ids["plan_id"], locked_node["lifecycle"], now, actor())
    return _answer(conn, job_id)
