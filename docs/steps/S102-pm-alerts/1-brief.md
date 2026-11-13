```
Step: S102 — PM alerts: job due, job overdue
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 02-11-2026
Track: full
Baseline: refs/steps/S101 (2ec75b6; c9cd091 + S095–S101), checked by staleness review s1
Status: Done — folded into S104 (KLA 13-11-2026, gate B 2a: its code is reworked and committed with S104; its own snapshot dropped); was: Held 02-11-2026 by KLA (one path: PM templates linked to class, model or machine; R03 re-plan; 5b nothing adopted until the rework is done); was: Gate B 02-11-2026 (code review r1: 3 nits, fixed (CR1-01 by the orchestrator, CR1-02 and CR1-03 in fix round 1: a test and a docstring, so no new review); device checks pending: rows 67 and 68 of device-checks.md); staleness s1: 0 blocker, 0 major, 1 minor, 4 nits, accepted; was approved 02-11-2026 (gate A delegated by KLA for tonight's PM steps: "Do those steps … stop only for real show stoppers"; review r1: 0 blocker, 0 major, 1 minor, 8 nits, all accepted; Q1–Q4 of § 9 flagged for KLA at gate B)
From: R03.7
```

# S102 — PM alerts: job due, job overdue

## 1. What will be built

S097 makes a plan's PM job at the start of its *Upcoming* window; the PM list judges it *Due* and
then *Overdue* live (S095 D4). Nobody is told: the technician must open the list. **R03.7 adds two
push alerts per due point** (Plan.MD § 4.7; gate R Q7.1 (a)):

1. **PM job due**, to the job's **assignee**, the morning the job turns *Due* (by date, or by a
   meter reading that reached the due value).
2. **PM job overdue**, once, the morning the job turns *Overdue* (past its on-time window), to the
   **assignee** and to the unit's holders of `pm_job:verify` (its **engineers** and managers), who
   can act on it (R03.9: reschedule or skip).

- A **contractor assignee** (a technician row, no login) has no device, so gets nothing; the
  engineers still get *overdue*. A job with **no assignee**: *due* reaches nobody; *overdue* the
  engineers.
- Only people who may open the job get an alert (`pm_job:read` at the job's site, covering the
  node's current root unit, S097 D9). The tap opens `/pm/jobs/<id>` (S098).
- Quiet push (no sound, Urgency low), kept 24 hours, as S074 and S084. Both kinds share a tag
  per job, so *overdue* replaces *due* on the phone.
- A daily task **`pm_job_alert_scan`** at **08:00 IST** (after S097's `pm_generate` at 05:00)
  queues one **`pm_job_alert`** per alert due. Four columns on `pm_jobs` (migration **v56**) keep
  the due point each alert was sent for, so a changed due point (a plan edit, R03.9's reschedule)
  sends them again with no route clearing anything.
- None for a started job, a done job (also *To verify*), a skipped or cancelled job, a job of an
  inactive plan or of a scrapped machine.
- ***What you will get*** (`alerts_core.you_get`) gains two lines; **Settings › Background tasks**
  lists the new task.

**After S102:** on 20-11-2026 at 08:00 Ravi's phone shows *PM job due · SMTW.MCC2 · HP003*,
"PM-2026-11-004 · Monthly press check — due on 20-11-2026, on time until 23-11-2026." On
24-11-2026, still not started, Ravi and the SMTW.MCC2 engineers get *PM job overdue · SMTW.MCC2 ·
HP003*, "PM-2026-11-004 · Monthly press check — was due on 20-11-2026, assigned to Ravi."

### Out of scope

- Alerts on *Waiting for verification* and *Sent back* (S099's note), on *Upcoming*, or a repeat
  while a job stays overdue; the daily summary email (Plan § 4.7, phase 5); Telegram (parked).
- A started job left unfinished (no alert, D5); a before-use plan (no due point, R03.13).
- Reschedule and skip (S101, coded): S102 relies on what S101 writes (§ 5.2).
- An alert when the assignee changes (BR1-01): the job is in the new assignee's *Me › Open work* at
  once; an *assigned to you* PM kind is a later step (§ 5.2, § 9 Q4).
- Any change to the PM list, the job page, the card or the service worker (it caches nothing and
  never will, § Yantra Specifics, *Notifications*).

## 2. Standards and practice

- **TPM, planned maintenance pillar.** In plain words: planned work is done when it was planned,
  not when someone remembers. The *due* alert tells the person who does it on the day; the
  *overdue* alert tells the people who can move the work when the plan slips.
- **EN 13306, scheduled maintenance** (preventive maintenance carried out to a time schedule or a
  number of units of use; clause number *to verify*). Both triggers count: a job due by meter
  reading alerts like a job due by date.
- **SMRP, PM compliance** (metric number *to verify*). In plain words: the share of PM jobs done
  within their window. The *overdue* alert fires when the job leaves the window, the moment it
  starts to count late (S095 D4), so the alert and the compliance figure use one rule.
- **ISO 55001 § 7.4 / ISO 9001 § 7.4, communication.** In plain words: decide what is told, when,
  to whom and how. `alerts_core`'s tables are that decision; *What you will get* shows each person
  theirs.
- **ISO/IEC 27001:2022 A.8.3** (*to verify*) **and A.5.34.** In plain words: each person sees only
  what the job needs. An alert reaches only people who may open the job; a payload carries ids,
  never an address.

## 3. Where

S095–S099 are coded tonight, not committed (snapshots up to `refs/steps/S100`); this brief anchors
by name in the files they add or change (`backend/pm_jobs.py`, `backend/pm_jobs_core.py`,
`backend/pm_work.py`, `backend/pm_schedule_core.py`, `backend/task_handlers.py`,
`backend/scheduled_tasks.py`, `backend/local_db.py`). The alert files are cited by line.

### Backend

- `backend/alerts_core.py` (pure, § 5): `PM_JOB_DUE = "pm_job_due"`, `PM_JOB_OVERDUE =
  "pm_job_overdue"`, `PM_KINDS`; `KINDS` (`backend/alerts_core.py:45`) becomes `TICKET_KINDS +
  IMPROVEMENT_KINDS + CONTRACT_KINDS + PM_KINDS`; `CHANNELS` (`:65`) gains both kinds as
  `(PUSH,)`; `PM_PATH = "/pm/jobs/{id}"` after `CONTRACT_PATH` (`:116`); `due_point_alerted`,
  `pm_alert_due`, `should_send_pm`, `pm_job_facts`, `pm_job_text`, `pm_job_message`; `you_get`
  (`:466`) gains § 5.7's lines; the docstring names the fourth record. It imports `READ_KEY` from
  `pm_jobs_core` as `PM_READ_KEY` (the name `READ_KEY` is already `improvements_core`'s here),
  `VERIFY_KEY` from `pm_work_core` as `PM_VERIFY_KEY`, `DUE_STATE` from `pm_jobs_core`, `DUE` and
  `OVERDUE` from `pm_schedule_core`, `format_number` from `meters_core`.
- `backend/alerts.py` (shell): `PM_JOB_ALERT = "pm_job_alert"`, `PM_JOB_SCAN =
  "pm_job_alert_scan"` beside `CONTRACT_SCAN` (`backend/alerts.py:62`); `enqueue_pm_alert`;
  `pm_job_recipients` on `people_at_unit` (`:174`), unchanged; the docstring: the PM paragraph
  (§ 5.5). It never imports `pm_jobs.py`.
- `backend/pm_jobs_core.py` (pure): `READ_KEY = "pm_job:read"` (one copy; `pm_jobs.READ_KEY`
  becomes `READ_KEY` imported from here); `job_standing(job, latest_value, today)` (§ 5.3).
- `backend/pm_jobs.py` (shell): `import alerts` and calls `alerts.enqueue_pm_alert` (so a test's
  monkeypatch of `alerts.enqueue_pm_alert` reaches the scan, BR1-04); `jobs_out` calls `job_standing` (same answer, one copy);
  `LOCK_JOB = "SELECT * FROM pm_jobs WHERE id = %s FOR UPDATE"` and `job_row(cur, job_id)` (the
  `JOB_FROM` row, plain) move here from `pm_work.py`; `alert_scan(conn, should_stop)`,
  `_alert_one`, `_mark_alerted`, `_ALERT_CANDIDATES` (§ 5.4); the LOCK ORDER note (§ 5.5).
- `backend/pm_work.py`: `_LOCK_JOB = pm_jobs.LOCK_JOB` (as `pm_plans.py` takes
  `pm_jobs.LOCK_PLAN`); `_job_row` calls `pm_jobs.job_row`; no other change.
- `backend/task_handlers.py`: `pm_job_alert` and `pm_job_alert_scan`; `HANDLERS` gains both;
  the docstring names the scan as the fourth commit exception (beside `pm_generate`).
  `_push_to_people` as it is.
- `backend/scheduled_tasks.py`: `SCHEDULE` gains `("pm_job_alert_scan", "08:00")` last, with a
  comment.
- `backend/push_core.py`: `PM_TTL_SECONDS = IMPROVEMENT_TTL_SECONDS` after `CONTRACT_TTL_SECONDS`
  (`backend/push_core.py:46`), with D7's reason.
- `backend/local_db.py`: migration **v56** (§ 4.1); no `_PRECONDITIONS` entry.
- `backend/equipment.py`: docstring only, the (6e) / (6f) LOCK ORDER bullets (§ 5.5).

**Import direction:** `alerts_core` imports the pure `pm_jobs_core`, `pm_work_core`,
`pm_schedule_core`, `meters_core` (pure → pure; none of them imports `alerts_core`). `pm_jobs.py`
imports `alerts` and `alerts_core` (it already imports `tickets`, which imports `alerts`).
`alerts.py` cannot import `pm_jobs.py` or `meters.py` (`meters` → `tickets` → `alerts`, a cycle),
so the scan and the job read live in `pm_jobs.py`, the recipients in `alerts.py`.

### Frontend

- `frontend/src/views/SettingsView.vue` — `TASK_LABELS` (`frontend/src/views/SettingsView.vue:208`)
  gains `pm_job_alert_scan: "Send the PM alerts: jobs due today and jobs overdue"` (BR1-08).

### Tests

- `backend/tests/test_alerts_core.py` — the new rules, texts, `you_get` (§ 8.1, § 8.3).
- `backend/tests/test_pm_jobs_core.py` — `job_standing`, `READ_KEY` (§ 8.1).
- `backend/tests/test_pm_alerts.py` (new) — the scan, the handler, the worker path (§ 8.2).
- `backend/tests/test_scheduled_tasks.py` — the new entry (§ 8.3).
- `backend/tests/test_push_api.py` — the engineer's `you_get` (§ 8.3).
- `backend/tests/test_migration_v56.py` (new), on the pattern of `test_migration_v54.py` (§ 8.1).
- `frontend/e2e/notifications.spec.js` — the *What you will get* lines (§ 8.4).
- `frontend/e2e/settings.spec.js` — the Background tasks line (§ 8.4).

### Docs (housekeeping, by the coder)

- `docs/schema/notes.json`: the `pm_jobs` line gains "the due point each alert was sent for
  (S102)"; then `tooling\schema-docs.bat write`, read `git diff docs/schema/`, and `check` exits 0.
  `docs/schema/schema.json` and `docs/schema/schema-data.js` are generated.
- `docs/Plan.MD` § 4.7: the row *PM job due / overdue* becomes § 5.6's recipients (Telegram
  column empty, the departure of Q7.1 named), and one bullet like *Contract reminders*.
- `.claude/CLAUDE.md` § Yantra Specifics, *Notifications (S021)*: the PM kinds, the scan and the
  markers; § SMTW-Review: the point of § 9.
- `docs/steps/device-checks.md`: two rows (§ 8.5).

**File count:** 19 code and test files (11 code: 10 backend, 1 frontend; 8 tests), 4 docs. One
concern. No split.

## 4. Data model

### 4.1 Migration v56

```sql
-- PM alerts (S102, R03.7): the due point (date and meter value, as due_on and due_meter) each alert
-- was queued for, so the daily scan sends each once per due point.  Both NULL = never sent.  A changed
-- due point (a plan edit, a reschedule) sends them again.
ALTER TABLE pm_jobs
    ADD COLUMN IF NOT EXISTS due_alert_on DATE NULL AFTER needs_verification,
    ADD COLUMN IF NOT EXISTS due_alert_meter DECIMAL(14,3) NULL AFTER due_alert_on,
    ADD COLUMN IF NOT EXISTS overdue_alert_on DATE NULL AFTER due_alert_meter,
    ADD COLUMN IF NOT EXISTS overdue_alert_meter DECIMAL(14,3) NULL AFTER overdue_alert_on;
```

- **The number.** S099 takes v54 (`backend/local_db.py`, "PM jobs: whether a done PM job waits for
  verification"). S101 takes v55 (coded: `rescheduled_on`, `rescheduled_meter`,
  `chk_pm_jobs_rescheduled`), so S102 takes **v56** (checked, staleness s1). `AFTER
  needs_verification` places the four markers between `needs_verification` and `open_plan_id`.
- **The value is the due point alerted for**, not a flag (S074 D3, S084 D3): the same types as
  `due_on` and `due_meter` (`backend/local_db.py`, v52's `pm_jobs`). A due point changed later
  differs from the markers, so the alerts due for the new point are sent again (§ 5.2).
- **No CHECK, no index:** tens of jobs, read once a day through `ix_pm_jobs_state`.
- **No `_PRECONDITIONS` entry:** four nullable columns; production holds no PM job (`pm_jobs` is new
  in v52, never released; § 9 A1).
- **Re-run safety:** `ADD COLUMN IF NOT EXISTS`. **Rollback:** a release before v56 never reads the
  columns and has no scan.
- **No answer shows them:** `pm_jobs.job_item` builds its dict field by field, and the list, the
  card (`pm_jobs.plan_schedules`) and the job page (`pm_work.job_detail`) build on it, so the
  markers never reach the browser (fact: `backend/pm_jobs.py`, `job_item`).
- **A departure from the roadmap** (R03.7: "Migrations: none"; S097's note already said "R03.7 needs
  its own marker for *PM job due*"): D3.

### 4.2 What is computed, never stored

- The standing (*Not yet*, *Upcoming*, *Due*, *Overdue*): live from the job's copies and the plan
  meter's latest reading plus `meter_offset`, as the list (`pm_jobs.jobs_out`, S097 D4).
- Recipients, their devices, every text: read when the alert task runs.

## 5. Rules

### 5.1 When an alert is due

`alerts_core.due_point_alerted(marker_on, marker_meter, due_on, due_meter)` → True when the marker
is set (`marker_on` or `marker_meter` is not None) and equals the due point (`marker_on == due_on`
and `marker_meter == due_meter`; `Decimal` compares by value, `1500.000 == 1500`).

`alerts_core.pm_alert_due(job, standing_state, plan_active, node_scrapped)` → `PM_JOB_OVERDUE`,
`PM_JOB_DUE` or `None`. `job`: a `pm_jobs` row (`state`, `due_on`, `due_meter` and the four
markers). In order, the first that holds:

| Case | Result |
|---|---|
| `job["state"] != DUE_STATE` (started, done, verified, skipped, cancelled) | `None` |
| `plan_active` false, or `node_scrapped` true (the next `pm_generate` cancels the job) | `None` |
| `standing_state == OVERDUE` | `PM_JOB_OVERDUE` unless the overdue marker is alerted for the due point, else `None` |
| `standing_state == DUE` | `PM_JOB_DUE` unless the due marker is alerted for the due point, else `None` |
| otherwise (*Not yet*, *Upcoming*) | `None` |

- **At most one per run.** A job found already *Overdue* (made late, the worker down, a meter
  that jumped past the window) gets only *overdue*, and the shell writes **both** markers (§ 5.4
  step 6), so a standing that falls back to *Due* (a meter reading deactivated) sends no late *due*.
- **The moment of *overdue*** is the standing *Overdue*: after the on-time window (grace), as the
  screen shows it (D2). A weekly job: 2 days after due; monthly: 4; yearly: 37
  (the morning after the window: grace 1, 3 and 36 days, BR1-07).
- **The moment of *due*** is the standing *Due*: the due date, or the first morning after a
  reading reached `due_meter`. Not at *Upcoming* (the list shows it; one alert per stage is
  enough).
- **The trigger:** `job_standing` already takes the furthest of the date and the meter (S095 D2),
  so a meter-due job alerts like a date-due one.

### 5.2 A changed due point re-arms the alerts

The markers hold the due point; nothing clears them. When `due_on` or `due_meter` changes, both
markers differ, so each alert is due again when its standing comes:

| Change after an alert was sent | Result |
|---|---|
| A plan edit moves the due point (`pm_jobs._refresh`, a `due_changed` line) | both alerts again at their new moments |
| R03.9's reschedule (S101) writes a new `due_on` / `due_meter` | the same |
| The windows or `meter_offset` change, the due point not | nothing (only `due_on` and `due_meter` compare) |
| The job starts, is done, skipped or cancelled | nothing (state) |
| A plan save that changes a schedule field (`pm_plans_core.SCHEDULE_FIELDS`) drops a reschedule (`settle_plan_job(…, keep_reschedule=False)`, a `due_changed` line with `RESCHEDULE_DROPPED`) | `due_on` / `due_meter` go back to the computed point: both alerts re-arm for it; a save that keeps the reschedule moves no due point: nothing (BS1-03) |
| A skip (`pm_work.skip_job`) settles the plan's next job in the same transaction | the skipped job: nothing; the new job has NULL markers and alerts at its own due point (BS1-03) |
| The assignee changes (`pm_jobs._refresh`, an `assignee_changed` line) | nothing: the job is in the new assignee's *Me › Open work*; an *assigned to you* PM kind is a later step (BR1-01, § 9 Q4) |
| A *both* plan's `due_meter` goes from NULL (no reading yet) to a value after *due* by date | *due* once more (accepted, § 9 A3) |

**What S101 does** (verified in its code, staleness s1, BS1-02): `pm_work.reschedule_job` writes
`update_row(cur, "pm_jobs", job_id, job_changes(job, due_copies(inputs["due"], inputs["offset"],
override), job["assignee_id"]), actor())`: the due copies (`due_on` / `due_meter`) and the two
reschedule columns, never the four markers (`job_changes` compares only the keys of the copies and
`assignee_id`). `skip_job` writes `SKIP_CHANGES` (`state = 'skipped'`), `done_at` and `done_meter`,
then `settle_plan_job`: no alert for the skipped job. Any later path that moves a due point writes
`due_on` / `due_meter` and never the markers (§ 9's SMTW-Review point).

### 5.3 The standing, one copy

`pm_jobs_core.job_standing(job, latest_value, today)`, where `job` is a full `pm_jobs` row (since
S101 it carries `rescheduled_on` and `rescheduled_meter`, which `due_from_job` reads strictly; BS1-01),
= `job_state(due_from_job(job), None if
latest_value is None else latest_value + job["meter_offset"], today)`. `pm_jobs.jobs_out` calls it
in place of its two lines (`value = …`, `standing = job_state(…)`), so the list and the scan cannot
disagree. `latest_value` is the plan meter's latest active reading's `value`, or None.

### 5.4 The daily scan (`pm_job_alert_scan`)

- **When:** daily at **08:00 IST**, after `contract_reminder_scan` at the same time and three hours
  after `pm_generate` (S097 D13). The worker's `enqueue_scheduled` enqueues it once a day, and once
  on return after a worker down over the time (`scheduled_tasks.due_tasks`).
- **No payload** (`_expect_no_payload`): BadTask otherwise.
- **The handler** (`task_handlers.pm_job_alert_scan`) calls `pm_jobs.alert_scan(conn, should_stop)`
  and acts on its result as `pm_generate` does: `stopped` → `RetryLater(…,
  PM_STOPPED_RETRY_SECONDS)`; `failed` → `RuntimeError` naming the job ids (retry with the
  back-off). Log: "pm_job_alert_scan: N due, M overdue, K failed".
- **`pm_jobs.alert_scan`, one transaction per job** (as `generate`, S097 D6, because (6e) is
  "one at a time, first in its transaction", `backend/equipment.py` LOCK ORDER):
  1. **Candidates, one plain read** (`_ALERT_CANDIDATES`), in the worker's transaction, then
     `conn.commit()` (the snapshot ends; each job's transaction starts fresh):
     `SELECT id, plan_id FROM pm_jobs WHERE state = 'due' AND NOT ((overdue_alert_on IS NOT NULL
     OR overdue_alert_meter IS NOT NULL) AND overdue_alert_on <=> due_on AND overdue_alert_meter
     <=> due_meter) AND (due_meter IS NOT NULL OR due_on <= %s) ORDER BY plan_id`, the parameter
     `today` from `_now(cur)`. It only narrows the work: every job it leaves out is one
     `pm_alert_due` answers `None` for (overdue sent for this point; or no meter due value and the
     date still ahead; or neither a date nor a meter value). A job whose *due* was sent stays a
     candidate through its window and is locked and answered `None` each morning: deliberate, one
     query over tens of jobs (BR1-03).
  2. **Per candidate, in plan id order** (`_alert_one(conn, job_id, plan_id)`), in
     `transaction(conn)`:
     1. (6e) `LOCK_PLAN` (the job's `plan_id` never changes, S098); gone → skip.
     2. (6f) `LOCK_JOB` → the job row; gone → skip.
     3. `_now(cur)`; `today = now.date()`.
     4. Plain: the node's lifecycle (`SELECT lifecycle FROM equipment WHERE id = %s`, the job's
        `equipment_id`); the plan meter's latest reading (`meters.last_readings(cur,
        [plan["meter_equipment_id"]])`, only when `plan["meter_type_id"]` is set).
     5. `standing = job_standing(job, value, today)`; `kind = pm_alert_due(job, standing.state,
        bool(plan["active"]), lifecycle == SCRAPPED)`. Decided from the locked plan and job rows;
        only the reading and the lifecycle are plain.
     6. When `kind`: `_mark_alerted(cur, job, kind)`: `UPDATE pm_jobs SET due_alert_on = %s,
        due_alert_meter = %s WHERE id = %s` for *due*; for *overdue* the same with the two overdue
        columns too (all four set to the job's `due_on`, `due_meter`). No `updated_*`: an alert is
        not a change of the job (as S074's and S084's markers). Then
        `alerts.enqueue_pm_alert(cur, kind, job_id)`.
  3. `should_stop()` between jobs; a job's exception other than a lost connection
     (`local_db.connection_lost`) is logged and the job counted in `failed`; the run goes on.
     Returns `{due, overdue, failed: [job ids], stopped}`.
- **What a run stores:** per job, the markers and its `pm_job_alert` task in one commit; then
  `mark_done` in the worker's transaction. A failed job rolls back alone (no marker, no task), and
  the task retries (`DEFAULT_MAX_ATTEMPTS` 3, `backend/task_queue.py`): the jobs already marked are
  no candidates, so nothing doubles. After three failures the task is `failed` (Settings ›
  Background tasks); tomorrow's run finds the same unmarked jobs. A stop: `RetryLater` 60 s, the
  rest then. Push off, or nobody to tell: the markers are written all the same (D6).
- **Why `_now(cur)`:** `pm_jobs._now` reads the session clock (IST) and is what tests fix
  (`fix_now` in `backend/tests/test_pm_generate.py`).

### 5.5 Locks

The database runs REPEATABLE READ. Per job, in `alert_scan`'s own transaction:

1. (6e) the plan row `FOR UPDATE`, the first statement.
2. (6f) the job row `FOR UPDATE`.
3. `SELECT NOW()` (no table), then plain: the node's lifecycle, the readings (the snapshot starts
   here, after both locks).
4. The marker `UPDATE` on the job held; the `task_queue` insert (no foreign key) → commit.

**The alert task** (`pm_job_alert`): plain reads only. **The routes:** unchanged.

**No deadlock cycle**, checked against `backend/equipment.py` (6e) / (6f) and the notes of
`backend/pm_jobs.py` and `backend/pm_work.py`:

- The scan follows the PM rule as it stands: the plan first, then its one job, one plan per
  transaction, before any plain read. Every PM path that touches a job takes its plan first, so no
  path holds a job and waits on its plan.
- The scan takes no node, counter, meter, reading or person lock; the paths it waits behind (a
  plan save, `pm_generate`, Start, an item, Mark done, verify, send back, S101's routes) wait only
  on those, never on a row the scan holds, and finish.
- A deadlock all the same (1213) rolls that job back; it counts in `failed`, and the retry
  finds it again.

The coder adds to `pm_jobs.py`'s LOCK ORDER note and to `equipment.py`'s (6e) bullet: "S102: the
daily `pm_job_alert_scan` (`pm_jobs.alert_scan`) takes (6e) then (6f), one job per transaction, and
writes only the job's four alert columns and a `task_queue` row; no node or counter." `alerts.py`'s
docstring gains a short PM paragraph: the scan lives in `pm_jobs.py`, `pm_job_alert` reads plain.

### 5.6 The alert task (`pm_job_alert`), its recipients and texts

**Enqueued** by `alerts.enqueue_pm_alert(cur, kind, job_id)` in the scan's per-job transaction:
payload `{kind, job_id}`. No due point (the marker holds it), no person id, no address.

**The handler**, in the worker's transaction, plain reads only:

1. Validate: `job_id` by `_ids`, `kind` in `PM_KINDS`; else BadTask (failed at once).
2. `row = pm_jobs.job_row(cur, job_id)` (`JOB_FROM`: `j.*`, `pl_title`, `pl_active`, `a_name`,
   `e_code`, `e_lifecycle`, `pl_trigger_kind` (S101; not read, BR1-06), `unit_id`, `unit_code`, `site_id`, `site_code`, `t_unit`); None →
   BadTask.
3. `should_send_pm(kind, row)` (pure): `state == DUE_STATE`, the plan active, the node not
   scrapped, and the kind's marker still alerted for the job's due point now (a due point changed
   since the scan: the next scan decides). False → log "pm_job_alert <kind> for <serial>: not sent,
   no longer true (…)" and return (done). The standing is not judged again (no readings query in
   the handler): a *due* task run late, on a job already *Overdue*, still sends *due*; the same
   morning's scan sends *overdue*, which replaces it on the phone (one tag). Accepted (BR1-02).
4. `push_sender.enabled()` false → log "push is not set up, no channel", return.
5. `facts = pm_job_facts(row, label_base_url(cur))`; `people = alerts.pm_job_recipients(cur, kind,
   row)`; `_push_to_people(cur, people, pm_job_message(kind, facts), PM_TTL_SECONDS)`.
6. Log "pm_job_alert <kind> for <serial>: n people, m devices".

**What it stores:** on success the `push_send` rows and `done`, one commit (a retry never doubles
them); on an exception a rollback and a retry, failed after 3. `push_send` is unchanged.

**Recipients** (`alerts.pm_job_recipients(cur, kind, row)`), at `row["site_id"]` covering
`[row["unit_id"]]` (the node's current root unit, the list's predicate, S097 D9):

| Kind | Who | Query |
|---|---|---|
| *due* | the assignee only | `people_at_unit(cur, site, [unit], roles_holding(PM_READ_KEY), only_ids=[assignee_id])`; `[]` without an assignee |
| *overdue* | the assignee, and the holders of `pm_job:verify` (engineer; the manager through `ROLE_INCLUDES`) | the *due* query, plus `people_at_unit(cur, site, [unit], roles_holding(PM_VERIFY_KEY))`; ids merged, sorted, each once |

- **By key, not by exact role** (S074 D6): `pm_job:verify` holders are who can sign off, and R03.9
  gives them reschedule and skip, so *overdue* reaches who can act. Every one of them holds
  `pm_job:read` (S099 A3), so the tap never ends in a 404.
- **The assignee must still be able to open the job:** `only_ids` inside the `pm_job:read` query leaves
  out an assignee who left the site, lost the unit or is inactive.
- **No login:** a contractor (or any person without a login) has no `push_subscriptions` row, so
  `subscription_ids` finds no device: skipped, and the log counts the person with 0 devices.
- **A login with no site role** (admin, IT admin) is never a recipient; a person who also holds a
  site role gets the alerts of that role (BR1-05). **Nobody is left out as the actor:** the scan
  has none.

**The facts** (`pm_job_facts(row, base_url)`): `job_id`, `serial`, `title` (`pl_title` cut to
`DESCRIPTION_CUT`, 80), `site_code`, `unit_code`, `machine_code` (`e_code`: the job's node, a
machine or a part), `due_on`, `due_meter`, `meter_unit` (`t_unit`), `grace_days`, `meter_window`,
`assignee_name` (`first_name(a_name)`, or None), `path` (`PM_PATH`), `url`.

**Push text** (`pm_job_text(kind, facts)` → `(title, body)`; writing style B; dates DD-MM-YYYY;
meter values through `format_number` and the meter type's unit):

| | *PM job due* | *PM job overdue* |
|---|---|---|
| Title | `PM job due · SMTW.MCC2 · HP003` | `PM job overdue · SMTW.MCC2 · HP003` |
| Body | `PM-2026-11-004 · Monthly press check — due on 20-11-2026, on time until 23-11-2026.` | `PM-2026-11-004 · Monthly press check — was due on 20-11-2026, assigned to Ravi.` |

- **The due words follow the values, not the plan's kind** (BR1-06): "on 20-11-2026" when `due_on`
  is set, "at 1500 h" when `due_meter` is set, "on 20-11-2026 or at 1500 h" when both are. A
  *both* plan with no reading yet (`due_meter` NULL) reads as a date-only job; `trigger_kind` is
  not read. **On time until:** `due_on + grace_days` → "23-11-2026"; `due_meter +
  meter_window` → "1650 h"; both → "23-11-2026 or 1650 h".
- *Overdue* without an assignee: "…, not assigned." The engineers read who has it; the assignee
  reads his own name, as S074's overdue text names the owner.
- `pm_job_message(kind, facts)` → `{title, body, path: "/pm/jobs/12", tag: "pm-job-12", quiet:
  True}`. `sw.js` opens any same-origin path, so it needs no change.
- **What a reader may see:** every recipient holds `pm_job:read` at the unit, so the serial, the
  plan title, the machine code and the assignee's first name are theirs to read. No result, remark
  or reading of the job is in the text.

### 5.7 What you will get

`you_get(memberships)` (`backend/alerts_core.py:466`), for memberships with a place only (after
the `if not place: continue`, because `people_at_unit` needs a unit):

- when the role holds `pm_job:verify`: `"Overdue PM jobs at <place>"`, after the membership's
  *Improvements ready to verify* line;
- once, when a membership with a place has a role in `ASSIGNABLE_ROLES`: `"PM jobs assigned to
  you, when due and when overdue"`, after *Jobs assigned to you*.

Examples: an engineer at SMTW (all units): "Breakdowns and defects at SMTW, escalations",
"Improvements ready to verify at SMTW", "Overdue PM jobs at SMTW", "Contracts ending for machines
at SMTW", "Jobs assigned to you", "PM jobs assigned to you, when due and when overdue", then the
two countermeasure lines. A technician: "Jobs assigned to you", "PM jobs assigned to you, when due
and when overdue", the owner line. A manager without units: unchanged (no PM line). Operator,
supervisor, storekeeper: unchanged. **The dot** (`showDot`) changes for nobody: every role that
gains a line had one.

### 5.8 The database down

- The scan and the alert task run in the worker, which reconnects on its own (S013). A scan due
  while the database was down runs once when it is back (`due_tasks`); the live standing finds the
  same jobs, and the markers stop doubles.
- No route changes, so no request path is affected; the reading path (`meters.log_reading`, the
  S040 sheet, S098's items) gets no push work (as R03 Q3.2 kept job creation out of it).
- Push not set up: the task logs and ends; the markers stay written, so turning push on later
  sends no backlog (D6).

## 6. API

No new route and no changed answer, except:

- `GET /api/push/config` (`backend/push.py`): `you_get` gains § 5.7's lines.
- `GET /api/settings/tasks` (`backend/settings.py`): lists `pm_job_alert_scan` after
  `contract_reminder_scan`.

## 7. Design decisions

- **D1. Two kinds, push only, their own task** (S074 D1: each record its own alert task), sharing
  `CHANNELS`, `_push_to_people` and `people_at_unit`. Rejected: one kind with a stage field (a kind
  is an event; the audiences differ).
- **D2. *Overdue* fires when the standing turns *Overdue*, after the on-time window** (S095 D4,
  BR1-02's choice left to R03.7). The phone and the PM list then say the same word, and the alert
  marks the moment the job starts to count late (SMRP). Cost: a yearly job's engineers hear 37
  days after the due date; the assignee heard on the due day. Rejected: at the due point, with
  "due" in the text (two alerts the same morning, and an *overdue* alert on a job the screen calls
  *Due*). **Decided by the orchestrator under KLA's go-ahead, to confirm at gate B** (§ 9 Q1).
- **D3. "Once" by four marker columns holding the due point alerted for (v56)**, a departure from
  R03.7's "Migrations: none". A moved due point re-arms the alerts with no route clearing anything,
  so S101 and plan edits need no alert code (§ 5.2). Kept past the queue's 90-day purge. The same
  types as `due_on` / `due_meter`, so the compare is exact. Rejected: two flag columns cleared by
  every route that moves a due point (S101 and `_refresh` must remember; a forgotten path loses
  alerts); a key string such as "2026-11-20|1500" (two types in one text column); the task queue
  as the memory (purged).
- **D4. A separate scan at 08:00, not inside `pm_generate` at 05:00.** A job turns *Due* by date
  or by a reading typed on the evening sheet; one morning look finds both, at the hour of every
  other daily alert (S074, S084), when the shift has started. `pm_generate` keeps one concern and
  its plan-save path stays free of push work. Rejected: in `settle_plan_job` (a plan save would
  then queue pushes, and a 05:00 alert waits on a phone through the night); on the reading save
  (the locked reading path would gain push work, against R03 Q3.2 (a)).
- **D5. No alert for a started job.** Someone is on it (S098: a started job belongs to *Due*
  whatever its standing). A job left half done is R03.14's overdue list. Rejected: *overdue* for a
  started job too (it alerts the person who is doing it). **Decided by the orchestrator under
  KLA's go-ahead, to confirm at gate B** (§ 9 Q2).
- **D6. The markers are written even when push is off or nobody would get it.** "Once" is about
  the event: switching push on later must not send old alerts (S074 D8, S084 D7).
- **D7. Quiet, kept 24 hours** (`PM_TTL_SECONDS`, its own name, as S084 D6). No machine is down;
  planned work. A phone off for an hour must still get a once-only alert.
- **D8. *Due* to the assignee only; *overdue* also to `pm_job:verify` holders** (Q7.1 (a), a
  departure from Plan § 4.7's Telegram column while Telegram is parked). The engineers get no
  *due* for jobs nobody can be reached about (no assignee, a contractor): every job comes due, and
  that would be daily noise; they hear at *overdue*. **The manager gets *overdue* too**, by key
  (D6 of S074): to confirm at gate B (§ 9 Q3).
- **D9. One transaction per job** (as `pm_generate`, S097 D6). The PM rule takes "(6e) one at a
  time"; holding several plan rows would add a new lock pattern. It also means each job decides
  from fresh rows: no plain read made before its locks.

## 8. Tests and acceptance

### 8.1 Pure core and migration

`backend/tests/test_alerts_core.py` (new classes; `TODAY` fixed, a monthly job due on `TODAY`,
grace 3):

- `due_point_alerted`: both markers None → False; equal date → True; equal date, another meter →
  False; meter `Decimal("1500.000")` against `Decimal("1500")` → True; a set marker against a
  moved date → False.
- `pm_alert_due`: *Due*, never sent → `PM_JOB_DUE`; *Due*, due sent for this point → None; due
  sent for an older date → `PM_JOB_DUE`; *Overdue*, nothing sent → `PM_JOB_OVERDUE`; *Overdue*,
  overdue sent → None; *Upcoming* and *Not yet* → None; state `in_progress`, `done`, `verified`,
  `skipped`, `cancelled` at *Overdue* → None; plan inactive → None; node scrapped → None.
- `should_send_pm`: as queued → True; started, plan inactive, node scrapped, due point moved since
  → False each.
- `pm_job_text` / `pm_job_message`: § 5.6's two texts exactly; a meter job ("at 1500 h", "on time
  until 1650 h"); a *both* job ("on 20-11-2026 or at 1500 h"); *overdue* without an assignee ("not
  assigned"); a 100-character title cut at 80; path `/pm/jobs/12`, tag `pm-job-12` for both
  kinds (so *overdue* replaces *due*, BR1-09), quiet True.
- `TestChannels`: `test_every_kind_has_channels_and_the_improvement_kinds_are_push_only` asserts
  `KINDS == TICKET_KINDS + IMPROVEMENT_KINDS + CONTRACT_KINDS + PM_KINDS`; new:
  `CHANNELS[PM_JOB_DUE] == CHANNELS[PM_JOB_OVERDUE] == ("push",)`, `PM_KINDS == (PM_JOB_DUE,
  PM_JOB_OVERDUE)`.

`backend/tests/test_pm_jobs_core.py`: `job_standing` gives `job_state`'s answer with the offset
added (a meter job at reading 1490, offset 20, due 1500, window 50 → *Due*; the test dicts carry
`rescheduled_on` and `rescheduled_meter` as None, as `test_the_copies_take_the_column_s_three_decimals`
does, BS1-01); a None reading →
`no_reading` for a meter job; `READ_KEY == "pm_job:read"`.

`backend/tests/test_migration_v56.py` (new; `V55 = [m for m in local_db._MIGRATIONS if m[0] <=
55]` (S101's v55), `V56` likewise, with `_recreate`, `_migrate`, `_run` of `backend/tests/migration_helpers.py`
and `_job` of `backend/tests/test_migration_v53.py`, as `test_migration_v54.py`): a fresh database
has the four columns, nullable, in order after `needs_verification`, types `date` / `decimal(14,3)`;
a v55 database with a due job keeps it, all four NULL; a re-run changes nothing.

### 8.2 Shell (`backend/tests/test_pm_alerts.py`, new)

Fixtures and helpers from `backend/tests/test_pm_generate.py` (`fix_now`, `set_plan`, `alone`,
`insert_job`, `add_reading`, `daily`, `overdue`, `upcoming`, `generate`, `technician`) and
`backend/tests/test_pm_plans_api.py` (`create`, `engineer_a`, `press`, `site`, `hours`); devices
by `add_device` and the `run` helper of `backend/tests/test_alerts.py`. Each plan is saved through
`POST /api/pm/plans` as the engineer, with the technician as assignee. **The scan reads every due
job of the worker's database**, so each test calls `alone(db_rows, plan_id)` first (as S097's
tests). `add_device(person)` inserts a `push_subscriptions` row for any person (no login needed);
a person without one stands for a contractor, who cannot sign in and so has no device.

- **Due by date:** a plan saved *Upcoming*, `fix_now` to the due date → one `pm_job_alert`
  payload `{kind: "pm_job_due", job_id}`, `due_alert_on` = `due_on`, overdue columns NULL,
  `updated_at` unchanged; a second run → none. `fix_now` past the grace → one *overdue*, all four
  markers set; a third run → none.
- **Due by meter:** a meter plan; a reading below `due_meter` → none; a reading at `due_meter`
  → one *due*; a reading past `due_meter + meter_window` → *overdue*.
- **Straight to overdue:** a plan saved `overdue(...)` → only *overdue*, and both due columns set.
- **Re-arm:** after *due*, `set_plan` moves the seed and a save refreshes the job to a later due
  date → none now; `fix_now` to the new date → *due* again.
- **No alert:** a started job (`insert_job(..., performed_by=…)`) at *Overdue*; a done job; a
  cancelled job; a plan set inactive straight (`set_plan(active=0)`, the job still due); a
  scrapped node (`scrap` of `backend/tests/documents_helpers.py`).
- **All or nothing per job:** `alerts.enqueue_pm_alert` monkeypatched to raise for one of two
  jobs → the run raises `RuntimeError` naming that job; the other job's marker and task stay; the
  failed job has neither.
- **Handler, recipients:** *due* → one `push_send` for the assignee's device (Urgency `low`, `ttl`
  86400, path `/pm/jobs/<id>`, § 5.6's title); the engineer gets none. *overdue* → the assignee
  and the engineer and the manager of the unit; an engineer of another unit, a supervisor, an
  operator get none. No assignee → *due* sends nothing; *overdue* only the engineers. A contractor
  assignee (no username, no device) → *overdue* reaches the engineers. An assignee who no longer
  covers the unit → left out.
- **Handler, no longer true:** started, plan inactive, node scrapped, due point moved after the
  scan → done, no `push_send`. **Push off** (`push_off`): no rows, and the scan still writes the
  markers.
- **Through the worker:** `Worker.run_once` with `SCHEDULE` patched to `[("pm_job_alert_scan",
  "00:00")]` (as `backend/tests/test_worker.py`), `push_sender.send` faked (`fake_send` of
  `backend/tests/test_alerts.py`): every row `done`, the fake called with the text.
- **Bad tasks:** the scan with a payload; `pm_job_alert` with an unknown kind, no `job_id`, a
  missing job → BadTask.

### 8.3 Existing tests that break or run again

- `backend/tests/test_alerts_core.py` `TestYouGet`: `test_engineer_all_units`,
  `test_manager_at_two_sites`, `test_manager_at_one_unit`, `test_technician_gets_assigned_jobs`
  gain § 5.7's lines in place. `test_supervisor_at_two_units`,
  `test_a_manager_without_units_gets_the_contract_lines`, `test_engineer_gets_no_email_line`,
  `test_operator_gets_the_countermeasure_line`, `test_nothing_for_other_roles`,
  `test_no_memberships_it_admin`, `test_a_membership_without_units` stay green.
- `backend/tests/test_alerts_core.py` `TestChannels`: the `KINDS` assertion (§ 8.1).
- `backend/tests/test_scheduled_tasks.py` `test_the_improvement_alerts_at_eight_after_the_purge`
  (`SCHEDULE ==` four entries) gains the fifth; `test_the_schedule_has_the_purge` stays green.
- `backend/tests/test_push_api.py` `test_push_on_with_the_public_key_and_what_you_get`: the
  engineer's list gains `f"Overdue PM jobs at {site['code']}"` after the verify line and "PM jobs
  assigned to you, when due and when overdue" after "Jobs assigned to you".
- Run whole, as they pin what the refactors touch: `backend/tests/test_pm_jobs_api.py` (the list
  through `jobs_out`; `TestList` compares the whole item, and S102 adds no field), `backend/tests/test_pm_work_api.py`, `backend/tests/test_pm_verify_api.py`
  and `backend/tests/test_pm_reschedule_api.py` (`LOCK_JOB`, `job_row`; BS1-04), `backend/tests/test_pm_generate.py`, `backend/tests/test_pm_jobs_core.py`.
- Unchanged: `backend/tests/test_rbac.py` `test_role_matrix` (no new key); `backend/tests/conftest.py`
  `_TABLES` (no new table); `backend/tests/test_migration_v52.py`, `test_migration_v53.py`,
  `test_migration_v54.py` (each slices its own range); `backend/tests/test_worker.py`
  `TestTasksCard` (`tasks[0]` stays `purge_access_log`).

### 8.4 Automated (e2e)

- `frontend/e2e/notifications.spec.js` "S021 A1: What you will get — …": the engineer's card also
  contains "Overdue PM jobs at SMTW" and "PM jobs assigned to you, when due and when overdue"
  (`// S102`); the technician's exact list becomes `["Jobs assigned to you", "PM jobs assigned to
  you, when due and when overdue", "Countermeasures given to you, and when they are overdue"]`.
- `frontend/e2e/settings.spec.js`, new test "S102: Background tasks lists the PM alerts at 08:00"
  (IT admin): the card shows "Send the PM alerts: jobs due today and jobs overdue — daily at 08:00".
  The S084 test stays green.
- Targeted run: `tooling/run-e2e-tests.bat e2e/notifications.spec.js e2e/settings.spec.js
  e2e/screens.spec.js`; the whole suite at Normal once at the end. `npx vite build` in `frontend/`.

### 8.5 On a real device (`docs/steps/device-checks.md`)

Push needs HTTPS and the VAPID keys, so both rows run on **production, the TEST machine at
SMTW.MCC2**, after the deploy. *Network*: "Company Wi-Fi, or mobile data with the phones
charging" (quiet push, Urgency low). The engineer test login writes one PM plan on the TEST
machine: title "TEST PM alert check", every **1 week** (on-time window 1 day), one check item,
**Last done 6 days ago**, assignee the **technician test login**. The engineer deactivates the plan
after row 2.

1. **Important.** The technician's phone has notifications on (steps 1 and 4 of *Phone set-up for
   notifications (S021)*). **After 08:00 the next day** (the due date) it shows **PM job due ·
   SMTW.MCC2 · <TEST machine code>**, without sound; the body names "TEST PM alert check" and
   "on time until" the next day's date. A tap opens the job page. The engineer's phone shows
   nothing. *Account:* Engineer test login (writes the plan); Technician test login (the phone).
2. **Important.** Nobody starts the job. **After 08:00 two days after the due date**, the
   technician's and the engineer's phones show **PM job overdue · SMTW.MCC2 · …**, "was due on
   <date>, assigned to <the technician's first name>". On the technician's phone it **replaces**
   the *due* alert. *Account:* both test logins, phones with notifications on.

### 8.6 Acceptance

- All unit suites green; the targeted browser runs and the whole suite at Normal green once.
- `tooling\schema-docs.bat check` exits 0.
- By the worker (§ 8.2): each alert reaches the right devices once per due point, never for a
  started, done, skipped or cancelled job, and again after the due point moves.

## 9. Open questions and assumptions

All four are **decided by the orchestrator under KLA's go-ahead, to confirm at gate B**; none
blocks coding (each is one constant or one line to change later).

- **Q1. When *overdue* fires** (D2).
  - **(a) When the standing turns *Overdue*, after the on-time window — recommended.** Phone and
    screen agree; the alert marks the late count. A yearly job waits 37 days.
  - (b) The morning after the due date, with the text "was due …, still on time until …". Earlier
    for long intervals; the alert then says *overdue* on a job the list calls *Due*.
- **Q2. A started job** (D5).
  - **(a) No alert — recommended.** Someone is on it.
  - (b) *Overdue* for a started job too: it reaches the engineers when a job is left half done.
- **Q3. The manager in *overdue*** (D8).
  - **(a) By key: every `pm_job:verify` holder, so engineers and managers — recommended.** The
    manager can reschedule or skip as well (R03.9), as S074 sends *ready to verify* to both.
  - (b) Engineers only (exact role, as `AUDIENCE`): fewer alerts for a manager of many units.
- **Q4. A change of assignee after *due* was sent** (BR1-01; § 5.2).
  - **(a) No alert; the job is in the new assignee's *Me › Open work* — recommended.** The markers
    stay keyed on the due point; no route code.
  - (b) Re-arm *due* on an assignee change: a fifth marker column, or `_refresh` clearing the due
    marker (the "forgotten path" design D3 rejects).
  - (c) A third kind *PM job assigned to you* from `_refresh` and the plan save: push work on the
    plan-save path D4 keeps free; not asked for by the roadmap.
- **A1.** v51–v56 ship in one release, so production holds no PM job before v56; the first
  morning after the release alerts the jobs then due, once each.
- **A2. Verified** against S101's brief § 4.1 and § 5.3 (BR1-09): its reschedule writes the
  override into `rescheduled_on` / `rescheduled_meter` and the job's `due_on` / `due_meter`
  (`due_copies` → `job_changes` → `update_row`, a v55 CHECK keeps them equal), a skip sets
  `state = 'skipped'`, and neither names the four markers. Checked again in S101's code at staleness s1 (§ 5.2,
  BS1-02).
- **A3.** A *both* plan whose meter gets its first reading after the date made the job *Due*
  sends *due* once more (§ 5.2): rare, harmless, and simpler than a compare per trigger.
- **Staleness s1 done** against `refs/steps/S101`: the migration number (v55 is S101's, v56
  stands), `JOB_FROM`'s columns, `pm_work.py`'s `_LOCK_JOB` and `_job_row`, `jobs_out`, the PM
  LOCK ORDER notes and S101's reschedule columns (BS1-01 … BS1-05).
- **Proposed point for § SMTW-Review** (`.claude/CLAUDE.md`): "PM alerts (S102): the daily
  `pm_job_alert_scan` (`pm_jobs.alert_scan`) sends *PM job due* and *PM job overdue* once per due
  point through the four `pm_jobs` columns `due_alert_on` / `due_alert_meter` and
  `overdue_alert_on` / `overdue_alert_meter`, never for a job not in state `due`, of an inactive
  plan or a scrapped node; it takes (6e) then (6f), one job per transaction. A path that moves a
  job's due point must write `due_on` / `due_meter` (so the alerts re-arm) and never the markers.
  An alert goes only to people with `pm_job:read` covering the job's unit: *due* to the assignee,
  *overdue* also to the `pm_job:verify` holders."
- **Roadmap corrections** (for the orchestrator to note in R03's log): R03.7's "Migrations: none"
  (D3); R03.7 also changes `pm_jobs.py`, `pm_work.py` and `push_core.py`, and adds a migration, so
  it conflicts with S101 in `local_db.py`.
- **No defining question.** Gate R answered Q7.1 (a); the choices above are inside it.

## 10. Amendments

None.

## Review log

### Round 1 — `2-brief-review-r1.md`, answered 02-11-2026

Sections changed: § 1 (out of scope), § 3 (pm_jobs.py, Frontend), § 5.1, § 5.2, § 5.4, § 5.6,
§ 8.1, § 8.4, § 9 (Q4, A2, staleness).

| Finding | Answer |
|---|---|
| BR1-01 minor | Accepted (a): no alert on an assignee change; § 5.2's table and § 1's out of scope say so; § 9 Q4 lists it for KLA at gate B. |
| BR1-02 … BR1-09 nits | Accepted, as recommended: the late *due* task is the accepted case (§ 5.6 step 3); the candidates keep a job whose *due* was sent, stated (§ 5.4); `pm_jobs.py` does `import alerts` (§ 3); the admin / IT admin wording (§ 5.6); the due words follow the values (§ 5.6); the window arithmetic (§ 5.1); the task label "jobs due today and jobs overdue" (§ 3, § 8.4); one tag for both kinds asserted (§ 8.1), A2 verified against S101's brief (§ 9). |

### Staleness s1 — `2-brief-review-s1.md`, answered 02-11-2026

Sections changed: header (Baseline), § 4.1, § 5.2, § 5.3, § 5.6, § 8.1, § 8.3, § 9 (A2, staleness).

| Finding | Answer |
|---|---|
| BS1-01 minor | Accepted (a): § 5.3 says `job` is a full `pm_jobs` row with `rescheduled_on` / `rescheduled_meter`; § 8.1's test dicts carry both as None; `due_from_job` stays strict. |
| BS1-02 … BS1-05 nits | Accepted, as recommended: S101's reschedule and skip written as verified facts, v56 confirmed with the column order (§ 4.1, § 5.2, § 9 A2); the two § 5.2 rows (a save that drops a reschedule, a skip's next job); `test_pm_reschedule_api.py` in *Run whole*, `TestList` stays green (§ 8.3); `pl_trigger_kind` in `JOB_FROM`'s columns, not read (§ 5.6). |
