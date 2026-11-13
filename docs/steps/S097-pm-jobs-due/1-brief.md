```
Step: S097 — PM jobs come due
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 01-11-2026
Track: full
Baseline: refs/steps/S096 (1c9881f; c9cd091 + S095, S096), stale-brief check by the orchestrator 02-11-2026: the brief review r1 read S096's coded backend; S096's fix round changed only `PmPlanView.vue` and tests; S096 code review notes an item-only save does not stamp the plan's `updated_at`
Status: Done — folded into S104 (KLA 13-11-2026, gate B 2a: its code is reworked and committed with S104; its own snapshot dropped); was: Held 02-11-2026 by KLA (one path: PM templates linked to class, model or machine; R03 re-plan; 5b nothing adopted until the rework is done); was: Gate B 02-11-2026 (code review r1 (backend): 1 minor, 3 nits, fixed in round 2; r2 (screens and fixes): 1 minor, 2 nits, fixed in fix round 1; verify review r3: no finding; checks: 10 auto, no device check); approved 02-11-2026 (gate A delegated by KLA for tonight's PM steps: "Do those steps … stop only for real show stoppers"; review r1: 0 blocker, 0 major, 4 minor, 7 nits, all accepted; one step at 28 files, two snapshot rounds; the decisions of § 9 flagged for KLA at gate B)
From: R03.3
```

# S097 — PM jobs come due

## 1. What will be built

R03.3 of `docs/roadmap/R03-pm.md`. **A plan's job appears by itself when it comes due, and the team
sees it.** S095 decides *when* (`backend/pm_schedule_core.py`); S096 stores the plans
(`pm_plans`, v51). S097 makes the jobs, keeps one open job per plan, and shows them.

1. **The record** (migration **v52**, § 4): `pm_jobs` (one row per occurrence of a plan, against
   the plan's node: ISO 14224's one record per item per event) and `pm_job_events` (its timeline,
   as `ticket_events`). Serial `PM-YYYY-MM-NNN`, numbered in the IST month of creation. The state
   column is declared for the whole life of Plan § 4.3 now (`due`, `in_progress`, `done`,
   `verified`, `skipped`, `cancelled`), so R03.4, R03.5 and R03.9 need no ENUM change (D2). S097
   writes only `due` and `cancelled`.
2. **When a job is made** (D1): when the plan enters its *Upcoming* window (S095: 7 days or 10 %
   of the interval before the due date, the shorter; 10 % of N before the due meter value), or later.
   The job then stays open until it is done (R03.4), skipped (R03.9) or cancelled (below). **At
   most one open job per plan** (Q3.1 a), held by the plan's row lock and a unique key (D3).
3. **The daily run** `pm_generate` (worker, 05:00 IST, `scheduled_tasks.SCHEDULE`): for each plan,
   one transaction: make the job that has come into its window, refresh the open job's due point
   when the plan or the readings moved it, cancel the open job of a deactivated plan or a scrapped
   machine (§ 5.5, § 5.6). Meter plans use the readings entered by then, so the evening sheet's readings
   make the job next morning (Q3.2 a).
4. **The plan save** (S096's `POST` and `PUT /api/pm/plans…`) does the same for its plan, in the
   same transaction: a plan saved inside its window gets its job at once; deactivating a plan
   cancels its open job (D5).
5. **The job's standing is judged live** (D4): *Not yet due*, *Upcoming*, *Due* or *Overdue*
   (S095 `job_state`, D4 of S095: *Due* through the on-time window, *Overdue* after it), from the
   due point stored on the job and the meter's latest reading. So a reading typed at 10:00 turns an
   upcoming job *Due* at once; only a new job waits for the morning.
6. **The PM list** (`/pm`, a nav item **PM** after *Tickets*; mock-up
   `docs/roadmap/R03-mockups/02-pm-jobs.html`): tabs *Due* and *Upcoming*; filters *All my units*
   and *Assigned to me*. Each row: the badge, the serial, the due date and the days past it, or the
   due meter value; the machine, the plan and its item count; the unit, the meter now and the
   assignee. A row opens the plan page until R03.4 adds the job page (D11).
7. **The equipment page's PM card** (S096's `PmPlansCard.vue`): each plan row gains one line: its
   open job (badge, serial, due) or, without one, "Next due 02-12-2026 or at 3,250 h".
8. **One new key** `pm_job:read`: the operator and up (so the supervisor and the maintenance
   ladder) and IT admin, who reads only (Q2.2 a); not the storekeeper. In `SITE_SCOPED`, checked at
   the node's current unit.

**After S097:** a technician sees his PM jobs on the phone; nobody fills them yet (R03.4).

### Out of scope

- Doing the job: *Start*, the items, *Mark job done*, `pm_job_results`, `pm_job:work`, *Me* ›
  *Open work* (R03.4). The *Done* tab comes with R03.4, which makes the first done job (D10).
- Verify and send back (R03.5); photos (R03.6); alerts *PM job due* and *PM job overdue* (R03.7);
  reschedule and skip (R03.9, which adds the override columns); compliance (R03.14); CIL and
  before-use jobs (R03.12, R03.13: a `before_use` plan makes no job here).
- A job page and the job's timeline on screen: the events are written now (ISO 9001 § 7.5.3) and
  shown on R03.4's job page.
- A forecast of future jobs: the floating rule knows only the next one (Q3.1 a, option c rejected).
- *Status: PM due* on the equipment list (roadmap § Out).

## 2. Standards and practice

- **TPM — planned maintenance pillar.** In plain words: the maintenance team decides in advance
  what each machine needs and when, and the work then comes to it by itself. S096 is the
  "decides"; S097 is "comes by itself": nobody has to remember the gearbox oil at 5,000 h.
- **EN 13306 — maintenance terms** (term numbers *to verify*). In plain words: *scheduled
  maintenance* is carried out to a timetable; *predetermined maintenance* at set intervals of time
  or use. S097 makes the timetable visible: one job per plan, due at its date or meter value, with
  EN 13306's word *due*.
- **ISO 14224 — maintenance data** (clause *to verify*). In plain words: record each maintenance
  event against the item it was done on. A job names its plan's node (`pm_jobs.equipment_id`), one
  job per occurrence, even when the plan's meter is on the machine above (Plan § 4.3, *Which meter
  a plan uses*).
- **ISO 9001:2015 § 7.5.3 — control of records.** In plain words: records show who did what and
  when, and are not lost or changed. A job is never deleted: a job no longer wanted is *cancelled*,
  with a timeline line saying why; every creation and change of the due point or the assignee is a
  line (§ 5.5).
- **SMRP — PM compliance** (metric number *to verify*). In plain words: of the PM jobs due in a
  period, the share done on time. S097 stores each job's due point and windows, so R03.14 can count
  against the point the job was due at; the list shows the days past due, so a job inside its grace
  still reads *Due* but is not mistaken for one due today (S095 D4, consequence 1).
- **ISO/IEC 27001:2022 A.5.15 — access control.** In plain words: each person sees only what the
  work needs. `pm_job:read` at the user's units; IT admin reads all units and changes nothing
  (Q2.2 a); the storekeeper has no PM.

## 3. Where

S097 builds on two steps not committed at the time of writing. It relies on these names, which the
staleness check must confirm before coding:

- **S095** (`docs/steps/S095-pm-schedule-core/1-brief.md`): `pm_schedule_core.next_due(plan,
  last_job=None, start_meter=None, override=None)`, `job_state(due, reading_value, today)`, the
  dataclasses `Due` (`due_on`, `due_meter`, `grace_days`, `upcoming_days`, `meter_window`,
  `rescheduled`, `before_use`) and `Standing` (`state`, `trigger`, `no_reading`), the constants
  `CALENDAR`, `METER`, `BEFORE_USE`, `NOT_YET`, `UPCOMING`, `DUE`, `OVERDUE`; the plan key
  `trigger_kind` and `created_on` (S095 § 5.1, BR1-01; S096 § 9 A6: the row goes as it is, with
  `created_on` the IST date of `created_at`); the § 5.2 rule
  "the meter value at a time T"; § 9 N1 and A3 (this brief § 5.3, § 5.4).
- **S096** (`docs/steps/S096-pm-plans/1-brief.md`): migration v51 and the `pm_plans` columns `id`,
  `equipment_id`, `title`, `performer`, `assignee_id`, `trigger_kind`, `calendar_every`,
  `calendar_unit`, `meter_equipment_id`, `meter_type_id`, `meter_every`, `last_done_on`,
  `last_done_meter`, `active`, `created_at`; `pm_plan_items.plan_id` and `active`;
  `backend/pm_plans.py` with `pm_plans_bp` at `/api/pm`, the create and change routes and their
  lock sequences (§ 5.7: "(6e) the PM plan row"), the card list's builder `_summary_out`;
  `meters.meters_with_last`; `frontend/src/views/equipment/PmPlansCard.vue`,
  `frontend/src/utils/pmLabels.js`, `frontend/tests/pmLabels.test.js`,
  `frontend/e2e/pm-plans.spec.js`; the plan page route `pm-plan` (`/equipment/pm/<id>`).

### Backend

- `backend/local_db.py`: migration **v52** at the end of `_MIGRATIONS`, after S096's v51 (§ 4.1).
  No `_PRECONDITIONS` entry (two new tables; no existing row changes).
- `backend/pm_jobs_core.py` (new, pure; § 5.1): the constants, `decide`, `due_copies`,
  `due_from_job`, `job_changes`, `meter_offset`, `days_past`, `tab_of`, `list_order`,
  `pm_serial`, `assignable_id`. Imports: `pm_schedule_core` (the dataclass `Due` and the constants
  above), `tickets_core.format_serial` and `serial_scope` (pure to pure, public names),
  `config_rbac.ASSIGNABLE_ROLES` (a constant). No DB, no clock, no Flask.
- `backend/pm_jobs.py` (new): the blueprint `pm_jobs_bp` (§ 6), the LOCK ORDER note (§ 5.7), and
  the shell functions `schedule_inputs`, `settle_plan_job`, `generate`, `plan_schedules`,
  `jobs_out` (§ 5.3–5.6, § 6). Imports: `pm_schedule_core`, `pm_jobs_core`; `require_perm`,
  `has_perm_at`, `current_person_id` (`backend/auth_utils.py`); `ApiError`, `enum_arg`, `int_arg`
  (`backend/api_common.py`); `get_db`, `insert_row`, `update_row`, `next_counter`, `transaction`, `marks`,
  `row_to_dict` (`backend/db_helpers.py`); `NODE_JOINS`, `accessible_unit_ids`
  (`backend/equipment.py`); `SCRAPPED` (`backend/equipment_core.py`); `last_readings`,
  `first_reading_after`, `readings_across_reset` (`backend/meters.py`, below); `person_at_site`
  (`backend/tickets.py`); `is_connection_lost` (`backend/local_db.py`). It never imports
  `pm_plans.py` (`pm_plans.py` imports it).
- `backend/pm_plans.py` (S096's): (a) in the create and the change route, inside their
  `transaction`, after the item writes and before the answer: `pm_jobs.settle_plan_job(cur,
  plan_id, node_lifecycle, now, actor())` (§ 5.5, D5); (b) the card list's items gain `schedule`
  from `pm_jobs.plan_schedules` (§ 6.3); (c) its LOCK ORDER note gains the S097 lines (§ 5.7).
- `backend/meters.py`: rename `_last_readings` to the public `last_readings` (all callers are in
  `meters.py`: the node's meters, `readings_sheet` through S096's `meters_with_last`, and the
  register; no change of behaviour). Two new public reads (§ 5.3): `first_reading_after(cur,
  equipment_id, meter_type_id, after)` and `readings_across_reset(cur, equipment_id,
  meter_type_id, after)`.
- `backend/config_rbac.py`: `"pm_job:read": ("maint_operator", "it_admin")` after S096's
  `pm_plan:edit`, with a comment (§ 5.8); the key joins `SITE_SCOPED`.
- `backend/scheduled_tasks.py`: `("pm_generate", "05:00")` second in `SCHEDULE`, after the purge,
  with a comment (D13).
- `backend/task_handlers.py`: the handler `pm_generate` (§ 5.6) and its `HANDLERS` entry; the
  module docstring names the third commit exception (one transaction per plan, D6).
- `backend/app.py`: `app.register_blueprint(pm_jobs_bp, url_prefix="/api/pm")`, after S096's
  `pm_plans_bp` line.
- `backend/equipment.py`: docstring only. Its LOCK ORDER note's S096 bullet "(6e) the PM plan row"
  gains the job rows and the PM serial counter (§ 5.7).

### Tests

- `backend/tests/test_migration_v52.py` (new; § 8.1), with the helpers of
  `backend/tests/migration_helpers.py` (`_recreate`, `_migrate`, `_run`, `_schema`).
- `backend/tests/test_pm_jobs_core.py` (new; § 8.2), written and green before the shell.
- `backend/tests/test_pm_generate.py` (new; § 8.2): the daily run.
- `backend/tests/test_pm_jobs_api.py` (new; § 8.2): the list, the card's `schedule`, the plan save.
- `backend/tests/test_rbac.py`: `test_role_matrix` rows and a new `test_pm_job_keys` (§ 8.3).
- `backend/tests/conftest.py`: `pm_job_events` and `pm_jobs` join `_TABLES`, first in the tuple
  (before S096's `pm_plan_items`, `pm_plans`).
- `backend/tests/test_scheduled_tasks.py`: `test_the_improvement_alerts_at_eight_after_the_purge`
  lists the new entry (§ 8.3).

### Frontend

- `frontend/src/views/PmJobsView.vue` (new): the PM list (§ 5.9).
- `frontend/src/router/index.js`: the route `{ path: "/pm", name: "pm", component: PmJobsView,
  meta: { title: "PM" } }`, after the improvements routes. A shared file (settings: *Shared
  code*): the whole browser suite runs again at the end.
- `frontend/src/stores/navigation.js`: `{ name: "pm", path: "/pm", icon: "fa-solid
  fa-calendar-check", label: "PM", perm: "pm_job:read" }` after `tickets`.
- `frontend/src/utils/pmLabels.js` (S096's): `STANDING_LABELS`, `STANDING_BADGES`,
  `dueText(dueOn, dueMeter, meterType)`, `daysPastText(days)`, `meterNowText(meter)`,
  `assigneeText(job)`, `jobsQuery(query)` (§ 5.9).
- `frontend/src/views/equipment/PmPlansCard.vue` (S096's): the schedule line per active plan
  (§ 5.10).
- `frontend/src/views/SettingsView.vue`: `TASK_LABELS` gains `pm_generate: "Create the PM jobs that
  are due or coming up"`.
- `frontend/tests/pmLabels.test.js` (S096's): the new helpers.
- `frontend/tests/navigation.test.js`: the role lists and two tests (§ 8.3).
- `frontend/e2e/pm-jobs.spec.js` (new; § 8.4). Its set-up helpers stay in the spec file, so
  `frontend/e2e/support/` is unchanged.
- `frontend/e2e/screens.spec.js`: the `/pm` screen and the bottom bar test (§ 8.3, § 8.4).

### Docs (housekeeping, by the coder)

- `docs/schema/notes.json`: `pm_jobs` and `pm_job_events` move from `planned` to `tables` in S096's
  area *Preventive maintenance* (the area's note gains "jobs (S097)"); `serial_counters`' line
  "later `PM-`" becomes "`PM-` PM job serials per month (S097)"; then `tooling\schema-docs.bat
  write`, read `git diff docs/schema/`, and `check` exits 0. `docs/schema/schema.json` and
  `docs/schema/schema-data.js` are generated. The generated column `open_plan_id` is new to the
  schema tool: the coder checks that `schema.json` shows it (*to verify* by the run).
- `docs/Plan.MD` § 4.3: a *Built (S097)* paragraph under *PM job* (when a job is made, one open job
  per plan, the daily run at 05:00, the save, cancellation, the reset rule, the list and the card;
  D1, D7, D8 as decisions). § 3: one paragraph for `pm_job:read`. § 6: the nav order *Me*,
  *Equipment*, *Tickets*, *PM*, *Readings*, *Masters*, *Settings* (the *Readings* bullet says
  "fourth"; it becomes fifth for the holders of `pm_job:read`).
- `.claude/CLAUDE.md`: § Step workflow, *Self-check, repo items* (2): `pm_jobs.py` joins the list
  of LOCK ORDER notes; § SMTW-Review gains the point of § 8.6.
- `docs/Keycloak.md`: no change. `docs/steps/device-checks.md`: no row (§ 8.5).

**File count:** 28 code and test files: backend 10, backend tests 7, frontend 11. Over the size
rule's 25 (§ 9, *Size*): kept as one step, coded and handed back in two snapshot rounds, backend
first (17 files), screens second (11 files).

## 4. Data model

### 4.1 Migration v52

```sql
-- PM jobs (S097, R03.3): one occurrence of a plan, made when the plan enters its Upcoming window
-- (pm_schedule_core), against the plan's node (ISO 14224: one record per item per event).  The
-- state covers the whole life (Plan § 4.3): due -> in_progress -> done -> verified, skipped
-- (R03.9), cancelled (its plan deactivated or its machine scrapped while not started).
-- due_on .. meter_window are copies of pm_schedule_core.Due, refreshed by the daily run and the
-- plan save while the job is due; meter_offset carries the meter's usage across a counter reset.
-- done_at, done_meter, timeliness are written at Mark done (R03.4) and are the record.
-- open_plan_id: the plan while the job is open, else NULL; its unique key keeps one open job per
-- plan (MariaDB has no partial index).  Never deleted.
CREATE TABLE IF NOT EXISTS pm_jobs (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    serial          VARCHAR(16) NOT NULL,
    plan_id         INT NOT NULL,
    equipment_id    INT NOT NULL,
    state           ENUM('due','in_progress','done','verified','skipped','cancelled') NOT NULL DEFAULT 'due',
    created_why     ENUM('calendar','meter') NOT NULL,
    due_on          DATE NULL,
    due_meter       DECIMAL(14,3) NULL,
    grace_days      SMALLINT NULL,
    upcoming_days   SMALLINT NULL,
    meter_window    DECIMAL(14,3) NULL,
    meter_offset    DECIMAL(14,3) NOT NULL DEFAULT 0,
    assignee_id     INT NULL,
    done_at         DATETIME NULL,
    done_meter      DECIMAL(14,3) NULL,
    timeliness      ENUM('on_time','late') NULL,
    open_plan_id    INT AS (CASE WHEN state IN ('due','in_progress') THEN plan_id END) PERSISTENT,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by      VARCHAR(100) NOT NULL,
    updated_at      DATETIME NULL,
    updated_by      VARCHAR(100) NULL,
    CONSTRAINT uq_pm_jobs_serial UNIQUE (serial),
    CONSTRAINT uq_pm_jobs_open_plan UNIQUE (open_plan_id),
    INDEX ix_pm_jobs_plan (plan_id, state, done_at),
    INDEX ix_pm_jobs_state (state, due_on),
    INDEX ix_pm_jobs_assignee (assignee_id, state),
    CONSTRAINT fk_pm_jobs_plan FOREIGN KEY (plan_id) REFERENCES pm_plans (id),
    CONSTRAINT fk_pm_jobs_equipment FOREIGN KEY (equipment_id) REFERENCES equipment (id),
    CONSTRAINT fk_pm_jobs_assignee FOREIGN KEY (assignee_id) REFERENCES people (id),
    CONSTRAINT chk_pm_jobs_windows CHECK (
        (due_on IS NULL) = (grace_days IS NULL) AND (grace_days IS NULL) = (upcoming_days IS NULL)
        AND (due_on IS NOT NULL OR meter_window IS NOT NULL)
        AND (due_meter IS NULL OR meter_window IS NOT NULL)
        AND meter_offset >= 0),
    CONSTRAINT chk_pm_jobs_done CHECK (
        (state NOT IN ('done','verified') OR done_at IS NOT NULL)
        AND (done_at IS NULL OR state IN ('done','verified','skipped'))
        AND (done_meter IS NULL OR done_at IS NOT NULL)
        AND (timeliness IS NULL OR state IN ('done','verified')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- The job's timeline (as ticket_events): created, due_changed (the new due point in due_on /
-- due_meter; the line before holds the old one), assignee_changed (person_id the new assignee, NULL
-- = no one), cancelled (remark: why).  R03.4 onwards add their events.  created_by is the user, or
-- pm_generate for the daily run.
CREATE TABLE IF NOT EXISTS pm_job_events (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    job_id          INT NOT NULL,
    event           VARCHAR(30) NOT NULL,
    from_state      VARCHAR(20) NULL,
    to_state        VARCHAR(20) NULL,
    occurred_at     DATETIME NOT NULL,
    person_id       INT NULL,
    due_on          DATE NULL,
    due_meter       DECIMAL(14,3) NULL,
    remark          VARCHAR(1000) NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by      VARCHAR(100) NOT NULL,
    INDEX ix_pm_job_events_job (job_id, occurred_at, id),
    CONSTRAINT fk_pm_job_events_job FOREIGN KEY (job_id) REFERENCES pm_jobs (id),
    CONSTRAINT fk_pm_job_events_person FOREIGN KEY (person_id) REFERENCES people (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

- **The generated column works on the dev DB** (fact, run 01-11-2026 on the `yantra-dev` container,
  MariaDB 11.4.13, a `TEMPORARY` table in one session, nothing kept; script
  `scratch/s097-gencol-check.sql`): two `done` rows and a `cancelled` row of plan 1 read
  `open_plan_id` NULL and pass with one `due` row; a second `due` row of plan 1 is refused with
  1062 on the unique key.
- **The ENUMs equal the core's constants.** `state` lists `pm_jobs_core.JOB_STATES`, `created_why`
  `(pm_schedule_core.CALENDAR, pm_schedule_core.METER)`, `timeliness` `(ON_TIME, LATE)` of S095;
  the generated column's list equals `pm_jobs_core.OPEN_STATES`. A test reads the column types from
  `information_schema.COLUMNS` and compares (§ 8.1).
- **Why `done_at`, `done_meter` and `timeliness` now** (D14): the next job counts from the last
  done job (S095 § 5.2), so the shell's base query reads them from the start, and S095 N1 asks a
  done job to keep its final due point and judgement. `chk_pm_jobs_done` allows `done_at` on a
  `skipped` job, because R03.9's skip is a base for the next job (Q9.2 a: "the next job counts
  from the skip"); R03.9 decides whether it writes it.
- **No unit column** (D9): a job follows its node; its unit is the node's current unit (the
  `equipment.NODE_JOINS` root unit), as the plan's access is.
- **Serial:** `VARCHAR(16)`, as `tickets.serial`; "PM-2026-11-001" is 14 characters and grows past
  999 as ticket serials do (`tickets_core.format_serial`).
- **Foreign keys:** no `ON DELETE` (RESTRICT, as every key in the schema). The generated column
  has no foreign key.
- **Re-run safety:** `CREATE TABLE IF NOT EXISTS`, two statements; a run stopped between them
  completes on the next start. **No precondition:** new tables only. Rollback: release v0.1.15
  (v50) and S096's release (v51) never read them.
- **Existing plans** (entered after S096, before S097's release) get their jobs at the first
  `pm_generate` run: after the deploy the worker finds the task never enqueued and runs it at once
  (`scheduled_tasks.due_tasks`).

### 4.2 What is computed, never stored

- The standing (*Not yet due*, *Upcoming*, *Due*, *Overdue*), its trigger, *No reading yet*, the
  days past, the tab; the next due point of a plan with no open job (the card).
- The meter's latest reading and its value counted across a reset (`latest + meter_offset`).
- Names, codes, units, the item count (joins).

## 5. Rules

### 5.1 The pure core (`backend/pm_jobs_core.py`)

```python
DUE_STATE, IN_PROGRESS, DONE, VERIFIED, SKIPPED, CANCELLED = (
    "due", "in_progress", "done", "verified", "skipped", "cancelled")
JOB_STATES = (DUE_STATE, IN_PROGRESS, DONE, VERIFIED, SKIPPED, CANCELLED)   # the ENUM's order
OPEN_STATES = (DUE_STATE, IN_PROGRESS)    # open_plan_id is set; one per plan
BASE_STATES = (DONE, VERIFIED)            # the next job counts from the latest of these; R03.9 may add SKIPPED
CREATE_STANDINGS = (UPCOMING, DUE, OVERDUE)   # S095's states that make a job
SERIAL_PREFIX = "PM"
RUN_ACTOR = "pm_generate"                 # created_by of the daily run's rows
CREATED, DUE_CHANGED, ASSIGNEE_CHANGED, CANCELLED_EVENT = "created", "due_changed", "assignee_changed", "cancelled"
PLAN_INACTIVE_REMARK = "The plan was deactivated."
NODE_SCRAPPED_REMARK = "The equipment was scrapped."
TAB_DUE, TAB_UPCOMING = "due", "upcoming"
TABS = (TAB_DUE, TAB_UPCOMING)
CREATE, REFRESH, CANCEL = "create", "refresh", "cancel"
```

| Function | Input → output | Rule |
|---|---|---|
| `decide(plan_active, before_use, node_scrapped, open_state, standing_state)` | → `(action, remark)` or `None` | the table of § 5.5 |
| `due_copies(due, offset)` | S095 `Due`, `Decimal` → `{due_on, due_meter, grace_days, upcoming_days, meter_window, meter_offset}` | the job's stored copies |
| `due_from_job(job)` | a `pm_jobs` row → `Due` | the copies back as a `Due`, `rescheduled` False, `before_use` False (R03.9 sets `rescheduled` from its columns) |
| `job_changes(job, copies, assignee_id)` | → `{column: new value}` | only the columns that differ |
| `meter_offset(base_value, readings)` | `Decimal` or None, `[{value, is_reset}]` in time order → `Decimal` | § 5.4 |
| `days_past(due_on, today)` | `date` or None, `date` → `int` or None | `(today - due_on).days` when ≥ 1, else None |
| `tab_of(standing_state)` | → `TAB_DUE` for DUE and OVERDUE, `TAB_UPCOMING` for NOT_YET and UPCOMING | |
| `list_order(item)` | a list item → sort key | OVERDUE, DUE, UPCOMING, NOT_YET; then `due_on` ascending, a job without `due_on` after those with one; then `serial` |
| `pm_serial(year, month, number)` | → "PM-2026-11-001" | `format_serial(SERIAL_PREFIX, …)` |
| `assignable_id(assignee_id, person)` | the plan's assignee id, `person_at_site`'s row or None → id or None | the id when the person is found and `person["role"]` is in `ASSIGNABLE_ROLES`; else None |

Type rules: dates are `date` (never `datetime`), meter values `Decimal`; `decide`'s states are the
constants above or None. A wrong input raises `ValueError` naming it (a shell bug, as S095 D8).

### 5.2 Which plans and jobs

- **A job is made only for an active plan** whose node is not scrapped and whose `trigger_kind` is
  not `before_use` (S096 refuses `before_use` until R03.13; the core would give *Not yet* anyway).
- **A machine out of use** (lifecycle not `scrapped`) keeps making jobs: a stored machine may need
  its preservation work. The engineer deactivates the plan, or skips the job once R03.9 exists.
- **The job's node** is the plan's `equipment_id` (fixed after create, S096 § 5.1).
- **The assignee** is the plan's `assignee_id` when `tickets.person_at_site(cur, id, site)` at the
  node's current site finds the person with a role in `ASSIGNABLE_ROLES` (`assignable_id`), else
  None: a person who left the site or was deactivated leaves the job unassigned (S096 § 9 A4, D12).
  An operator plan has no assignee (S096's `chk_pm_plans_assignee`); its job reads "Operator".
- **The job's assignee follows the plan's** while the job is `due` (every refresh copies it again).
  R03.4 decides whether a started job keeps its own.

### 5.3 The schedule inputs (`pm_jobs.schedule_inputs(cur, plan, now)`)

Plain reads, after the plan's lock (§ 5.7). `plan` is the `pm_plans` row; the core gets
`dict(plan, created_on=plan["created_at"].date())` (the session runs at +05:30, so `created_at` is
IST, `backend/local_db.py` `init_command`).

1. **The last base job:** `SELECT done_at, done_meter FROM pm_jobs WHERE plan_id = %s AND state IN
   (BASE_STATES) ORDER BY done_at DESC, id DESC LIMIT 1` → `last_job = {done_on:
   done_at.date(), done_meter}` or None. None for every plan until R03.4 marks a job done.
2. **The base meter value and its time** (S095 § 5.2, with its time added for § 5.4), only for a
   plan with a meter trigger (`meter_type_id` set):

   | Case | Base value | Base time |
   |---|---|---|
   | A last base job | its `done_meter` (may be None: no base, S095 T3) | its `done_at` |
   | No job; `last_done_meter` set | `last_done_meter` | T (below) |
   | No job, no seed value; a reading at or before T | that reading's `value` (`start_meter`) | its `taken_at` |
   | No job, no seed value, none at or before T; one after T | the earliest one's `value` (`start_meter`, S095 D9) | its `taken_at` |
   | None of these | None (`start_meter` None: "No reading yet") | — |

   T is 23:59:59 of `last_done_on` when the plan has a seed date, else the plan's `created_at`. The
   reading "at or before T" is `last_readings(cur, [meter_equipment_id], until=T)` for the plan's
   `meter_type_id`; "after T" is `first_reading_after(cur, meter_equipment_id, meter_type_id, T)`
   (`taken_at > T`, active, earliest by `(taken_at, id)`).
3. **The latest reading:** `last_readings(cur, [meter_equipment_id])` for the plan's type → the
   reading `{value, taken_at}` or None.
4. **The offset:** `meter_offset(base_value, readings_across_reset(cur, meter_equipment_id,
   meter_type_id, base_time))` (§ 5.4); 0 when the base value is None.
5. **The core:** `due = next_due(plan_input, last_job, start_meter)`; `reading_value = latest +
   offset` (None without a latest reading); `standing = job_state(due, reading_value, today)`, with
   `today = now.date()`.

`schedule_inputs` returns `{due, standing, reading, offset}`. The meters are read on
`meter_equipment_id` (the node or an ancestor, S096 D5), never on the job's node.

### 5.4 A counter reset after the base (S095 § 9 A3)

A counter reset (Plan § 4.5) makes the latest value lower than the base. Read as it is, a meter plan
would read *Not yet* until the new counter passed the old due value again: a job could be missed
for thousands of hours. **S097 carries the usage across the reset** (D8):

- `readings_across_reset(cur, equipment_id, meter_type_id, after)` returns the active readings of
  the meter taken after `after`, in `(taken_at, id)` order, as `[{value, is_reset}]`, **only when
  one of them is a reset** (one query, with an `EXISTS` on `is_reset = 1`); else `[]`.
- `meter_offset(base_value, readings)`: `offset = 0`, `before = base_value`; for each reading: a
  reset adds `before` to the offset; then `before = value`. The value passed to the core is
  `latest + offset`.
- Worked: base 1,000 h; readings 1,100, 1,200, a reset at 50, then 80 → offset 1,200, counted value
  1,280 (200 h before the reset, 80 after it, counted from 0). Two resets: 1,000; 1,200; reset 10;
  300; reset 5; 40 → offset 1,500, counted 1,540.
- Without a reset after the base the offset is 0 and the core sees the latest value, exactly as
  S095 § 5.4 reads. A seed above the readings (S096 § 9 A3) is not corrected.
- The offset is stored on the job (`meter_offset`) at create and refresh, so the list adds it to the
  latest reading without reading the history again. A reset typed during the day counts on the
  list from the next run or plan save.
- A reset counts from 0: a new meter that starts at 12 h counts those 12 h as used, so the job comes
  due early, never late.

### 5.5 Settling one plan's job (`pm_jobs.settle_plan_job(cur, plan_id, node_lifecycle, now, actor)`)

One function for the daily run and the plan save (DRY). It runs with the plan's row held (§ 5.7)
and reads the open job plainly: `SELECT * FROM pm_jobs WHERE plan_id = %s AND state IN
(OPEN_STATES)` (at most one row, `uq_pm_jobs_open_plan`). Then `decide`:

| Plan | Node | Open job | The plan's standing (§ 5.3) | Action |
|---|---|---|---|---|
| any | any | `in_progress` | — | none (R03.4 decides) |
| inactive | any | `due` | — | `CANCEL`, `PLAN_INACTIVE_REMARK` |
| active | scrapped | `due` | — | `CANCEL`, `NODE_SCRAPPED_REMARK` |
| inactive, or node scrapped | | none | — | none |
| active, `before_use` | not scrapped | none or `due` | — | none (R03.13; S096 refuses the kind) |
| active | not scrapped | none | NOT_YET | none |
| active | not scrapped | none | UPCOMING, DUE or OVERDUE | `CREATE` |
| active | not scrapped | `due` | any | `REFRESH` |

- **CREATE:** `next_counter(cur, serial_scope(now.year, now.month, SERIAL_PREFIX))` (scope
  "PM:2026-11"), then `insert_row(cur, "pm_jobs", {serial: pm_serial(…), plan_id, equipment_id,
  created_why: standing.trigger, **due_copies(due, offset), assignee_id}, actor)` and the event
  `created` (`to_state` `due`, `occurred_at` `now`, `due_on`, `due_meter`). `standing.trigger` is
  CALENDAR or METER whenever the state is not NOT_YET (S095 § 5.4).
- **REFRESH:** `job_changes(job, due_copies(due, offset), assignee_id)`; empty → nothing written.
  Else `update_row(cur, "pm_jobs", job_id, changes, actor)`, and the events: `due_changed` when
  `due_on` or `due_meter` changed (the new values), `assignee_changed` when `assignee_id` changed
  (`person_id` the new one or NULL). A change of the windows or the offset alone writes no event
  (they are copies of inputs, not the due point). A refreshed job whose standing is now NOT_YET
  (a plan edit pushed it back) stays open and shows as *Not yet due* under *Upcoming* (D17).
- **CANCEL:** `update_row` with `state` `cancelled` (so `open_plan_id` becomes NULL), and the event
  `cancelled` (`from_state` `due`, `to_state` `cancelled`, the remark). A plan made active again
  gets a new job (new serial) when it next comes into its window.
- **Answer:** the action taken (`CREATE`, `REFRESH`, `CANCEL` or None), for the run's log and the
  tests.
- **`now`** is the session's `SELECT NOW()` (IST, as the queue and `created_at`), read by
  `pm_jobs._now(cur)` (one function, so a test can fix the clock): once per plan transaction (the
  run) or once per request (the save and the list). It reads no table, so it does not start the
  snapshot.
- A refused save (400, 409) is refused before this call, so it makes no job. A failure after it
  rolls the job, its event and the serial counter back with the plan (no gap in the series).

### 5.6 The daily run (`pm_generate`)

`task_handlers.pm_generate(conn, payload, should_stop)` → `pm_jobs.generate(conn, should_stop)`:

1. `_expect_no_payload("pm_generate", payload)`.
2. **Candidates**, one plain read: `SELECT id FROM pm_plans WHERE active = 1 UNION SELECT plan_id
   FROM pm_jobs WHERE state = 'due' ORDER BY 1` (the active plans, and any plan with a `due` job, so
   an inactive plan's leftover job is cancelled). **Then `conn.commit()`** (BR1-01). The handler
   starts inside the worker's transaction (`worker.Worker.run_one` wraps `run_task` in `with
   transaction(self.conn)`), so this read opened that transaction's snapshot; the explicit commit
   ends it, as `purge_access_log` commits per batch, and the loop relies on no implicit commit.
3. **Per plan, in id order, one `transaction(conn)`** (D6, `db_helpers.transaction`: `BEGIN`, commit
   or roll back): lock (§ 5.7), `settle_plan_job(cur, id, lifecycle, now, RUN_ACTOR)`, commit. A plan
   gone or not found by its lock is skipped. After the last plan the connection is back in autocommit
   (`get_local_db`: `"autocommit": True`), so the worker's `mark_done` commits by itself and its outer
   commit has nothing left; on a raise the worker's rollback has nothing uncommitted to undo.
4. **A plan that fails** (an exception other than a lost connection) is rolled back alone, logged
   with `logger.exception("pm_generate: plan %s failed", plan_id)`, and the run goes on. At the end,
   if any failed, the handler raises `RuntimeError("pm_generate: plans … failed")`: the task retries
   with the back-off (`DEFAULT_MAX_ATTEMPTS` 3, `backend/task_queue.py`), and the plans already
   settled are found settled again (idempotent). After the last attempt the task is *Failed* on
   the Settings › *Background tasks* card. A lost connection is re-raised at once, as the worker
   expects: a `pymysql.err.OperationalError` whose code `local_db.is_connection_lost(code)` names,
   or a closed connection (`conn.open` false), the test of `worker.Worker._connection_lost`.
5. **`should_stop()`** is checked between plans: when set, the handler raises `RetryLater("pm_generate
   stopped; the rest runs on restart", 60)`, so the plans not yet settled are settled when the
   worker comes back, not tomorrow.
6. The log line: `pm_generate: N created, N refreshed, N cancelled, N failed`.
7. **What is stored:** on success, the jobs and events, plan by plan, then `mark_done`. On a retry:
   the plans settled so far stay committed. Nothing else is stored (no marker: an open job is the
   marker).

**This is the third commit exception** of `task_handlers.py`'s docstring, beside the purge's batches
and `push_send`'s failure record: the per-plan commit keeps each plan's locks short and makes a
deadlock with a plan save impossible (§ 5.7).

**The worker stopped:** no new jobs. The open jobs' standings still move on the list (D4), and the
*Background tasks* card shows *pm_generate* overdue (`scheduled_tasks.is_overdue`), as the roadmap's
R03.3 note asks.

### 5.7 Locks

The database runs REPEATABLE READ; a locking read does not start the snapshot, the first plain read
does. **The rule:** every write of a `pm_jobs` or `pm_job_events` row holds its plan's row (6e)
first. So the plan lock serialises everything about one plan's jobs, the open job can be read
plainly after it, and `uq_pm_jobs_open_plan` is the backstop (a 1062 there is a bug, a 500).

**The daily run, per plan** (one transaction):

1. `SELECT * FROM pm_plans WHERE id = %s FOR UPDATE` — (6e) exclusive, the first statement.
2. `SELECT id, lifecycle FROM equipment WHERE id = %s LOCK IN SHARE MODE` with the plan's
   `equipment_id` — (1) shared (S096's order: (6e), then (1)).
3. `SELECT NOW()`, then plain (the snapshot starts here, after both locks): the open job, the last
   base job, the readings (§ 5.3), the node's site (for the assignee) and `person_at_site`.
4. CREATE: `next_counter` — (6) the `PM:YYYY-MM` serial counter row, exclusive until the commit;
   `insert_row` of the job (shared foreign-key locks: the plan (held), the node (held), the person)
   and of its event (the new job, the person). REFRESH / CANCEL: `UPDATE pm_jobs … WHERE id` (the
   job's row, exclusive) and the event insert.
5. Commit.

**The plan save** (S096's routes, one transaction each), with S097's call at the end:

- *Create:* (1) the node `LOCK IN SHARE MODE` → plain reads → insert of the plan (the new row,
  exclusive) and its items → `settle_plan_job`: plain reads → (6) the counter → the job and event
  inserts.
- *Change:* (6e) the plan `FOR UPDATE` → (1) the node shared → plain reads → the plan and item
  writes → `settle_plan_job`: plain reads → (6) the counter (CREATE only) → the job update or
  inserts.

**No deadlock cycle:**

- Two writers of one plan (the run and a save, or two saves) both take (6e) first: the second waits
  and then reads the first's committed job (its snapshot starts after the lock). So two jobs for one
  plan cannot both be made; the unique key would refuse the second anyway.
- The run holds one plan (6e) and the counter (6) at a time, then commits. A save holds one plan
  (its own) and waits for the counter at most; the run never waits on a save's plan while it holds
  the counter, because it commits before it locks the next plan. (With one transaction for the whole
  run, the run would hold the counter and wait on plan 57's row while a save of plan 57 waited on
  the counter: a cycle. D6 removes it.)
- The open job is never read with a locking read: `SELECT … WHERE open_plan_id = %s FOR UPDATE` on a
  plan with no job would take a gap lock on `uq_pm_jobs_open_plan`, and a run's insert into that gap
  would wait on a save that waits on the run's counter. Plain reads under (6e) are enough.
- The node (1) is taken shared; its writers (equipment.py, meters.py, the scrap) hold it exclusive
  and never wait on a plan, a job or the PM counter. The scrap's top-down subtree lock is the
  accepted case S096 § 5.7 names.
- The person and the meter readings are read plainly; their writers never wait on PM rows. A
  reading committed during the run counts in the next run or plan save (Q3.2 a: daily).
- **(6) after (6e) and (1) is a departure from the number order** (BR1-04; elsewhere the lower
  number comes first, e.g. `improvements.py` takes (6) before (6b)). The reason: the `PM:` counter
  row is taken by nothing else (only S097's job creates, always last before the inserts, always
  under (6e)), and a plan transaction that only refreshes or cancels must not bump it, so it cannot
  come first. It adds no cycle with the ticket (`TK:`), improvement (`IM:`) or lesson (`OPL`)
  counters. A counter that other modules also take may not copy this order.
- **For R03.4 onwards:** a job write (start, an item, done) takes its plan (6e) first, then the job.
  A path that locks a job and then waits on its plan deadlocks with the run.

The coder writes this into `pm_jobs.py`'s LOCK ORDER note, and adds to S096's "(6e)" bullet in
`equipment.py`'s note: "S097: every pm_jobs and pm_job_events write holds its plan (6e) first, then
the node (1) shared, then, for a new job, (6) the PM:YYYY-MM counter. (6) after (6e) and (1) is a
departure from the number order: the PM: counter row is taken by nothing else, and a plan
transaction that only refreshes must not bump it. The daily run (pm_generate) takes one plan per
transaction and commits before the next; no module reads a job FOR UPDATE by open_plan_id."
`pm_jobs.py`'s own note carries the same departure sentence.

### 5.8 Permissions

| Key | Holders | Where |
|---|---|---|
| `pm_job:read` (new) | `("maint_operator", "it_admin")`: so the supervisor, technician, engineer and manager; not the storekeeper | `SITE_SCOPED`; the list through `accessible_unit_ids(cur, "pm_job:read")` over the node's current root unit; the card through `has_perm_at("pm_job:read", site)` |

Comment in `config_rbac.py`: "PM jobs (S097, R03.3): read by the operator and up, as tickets, so the
floor sees the planned work at its units; and by IT admin, who reads PM only (R03 Q2.2 a). Not the
storekeeper. Doing a job is pm_job:work (R03.4)."

| Route / screen | Key | Then |
|---|---|---|
| `GET /api/pm/jobs` | `require_perm("pm_job:read")`: 403 when held nowhere | the rows of the units where it is held; IT admin (with `equipment:read_all_units`) and admin: every unit (`accessible_unit_ids` None) |
| The card's `schedule` (`GET /api/pm/plans?equipment_id=`) | the route's `equipment:read` (S096) | `schedule` is null for a reader without `pm_job:read` at the node's site |
| The plan save | `pm_plan:edit` (S096) | the job follows the save; no extra key |
| The nav item *PM* | `pm_job:read` | `canOpenRoute("pm", …)` guards a typed `/pm` |

- **Who sees what:** operator, supervisor, technician, engineer, manager: the list at their units
  and the card's line; IT admin: every unit, nothing to change; storekeeper: no *PM* item, no line
  on the card (he still reads the plans, S096 D3).
- **Identity:** no field changes who can log in or what anyone sees. The assignee is answered as
  `{id, name}`; no login, no email. *Assigned to me* uses `current_person_id`: a user with no Team
  record matches nothing, and the screen hides the tick for him (`userPersonId`).

### 5.9 The PM list (`PmJobsView.vue`)

- **Route** `/pm` (title "PM"), the nav item *PM* after *Tickets* (sidebar and bottom bar, from
  `navItems`). A manager's bottom bar then has seven items on a phone (§ 8.3: the S040 test checks
  they fit).
- **Query in the URL** (as `TicketsView.vue`): `tab` (`upcoming`; *Due* is the default, left out),
  `unit_id`, `assigned=me`. Back returns to the same list.
- **Header:** the tabs *Due* and *Upcoming* (`nav nav-tabs`, links); under them one row of filters,
  wrapping on a phone: the select *Unit* (`aria-label="Unit"`, first option "All my units", then
  `filterableUnits(units, myUnits)` by `full_code`, as the tickets list) and, for a user with a Team
  record, the tick *Assigned to me*.
- **Count line** above the rows, from the answer's `counts`: on *Due* "4 due · 1 overdue" (BR1-05:
  `counts.due` counts the DUE standing only and `counts.overdue` the OVERDUE one, so the two parts
  add up to the *Due* tab's rows; a zero part left out; none: no line); on *Upcoming* "3 upcoming"
  (`counts.upcoming`: NOT_YET and UPCOMING).
- **A row** (`list-group-item`, a link to `/equipment/pm/<plan id>`, the whole row the target, at
  least 44 px high):
  1. the badge (`STANDING_LABELS`: *Overdue* `text-bg-danger`, *Due* `text-bg-warning`, *Upcoming*
     `text-bg-info`, *Not yet due* `text-bg-light border`), the serial in small text, and, right,
     `dueText`: "24-10-2026", "at 5,000 h", or "24-10-2026 or at 3,250 h", then `daysPastText` when
     the job is past its due date: " · 1 day ago", " · 3 days ago" (BR1-06: the badge is the
     judgement, *Due* inside the grace, *Overdue* after it; the words only count the days);
  2. in bold: "HP003 — Hydraulic press 3" (the job's node);
  3. "Monthly hydraulic check · 7 items";
  4. small: the unit's full code ("SMTW.MCC2"), then for a plan with a meter `meterNowText`: "Run
     hours now 5,006.5 h", "Run hours now 120 h · 5,120 h counted across a reset" (offset > 0), or
     "Run hours: no reading yet"; then `assigneeText`: the name, "No one yet", or "Operator" for an
     operator plan. Joined with " · ".
- **Numbers and dates:** `formatReading(value, meter_type)` (`frontend/src/utils/meterLabels.js`)
  and `formatDate` (`frontend/src/utils/datetime.js`): Indian grouping, DD-MM-YYYY.
- **Order:** the server's (`list_order`): on *Due* the overdue first, then the oldest due date.
- **States:** loading "Loading…"; a load error "PM jobs could not be loaded: <message>" with
  *Retry*; no units `NO_UNITS_TEXT`; empty *Due* "No PM jobs are due." (with a filter set: "No PM
  jobs match these filters."); empty *Upcoming* "No PM jobs are coming up." (same filter text).
- **No pager:** one open job per active plan bounds the list (tens of rows at the pilot, a few
  hundred later; the answer is built in one pass).
- **The one-tap path:** a technician taps *PM*; his units' due jobs are there, the overdue first.

### 5.10 The PM card's line (`PmPlansCard.vue`)

Under each **active** plan row's existing lines, when its `schedule` is not null:

- **An open job:** the badge, then "PM-2026-11-004 · 29-11-2026 · 3 days ago" (`dueText`,
  `daysPastText`), and for a meter plan `meterNowText`.
- **No open job:** "Next due 02-12-2026 or at 3,250 h" (`dueText` of `next_due`); a `both` plan
  whose meter has no base: "Next due 02-12-2026 · Run hours: no reading yet"; a meter-only plan with
  no base: "Next due when Run hours has a reading".
- Inactive plans show no line. `schedule` null (the storekeeper, or a reader without the key at the
  site): no line.

### 5.11 The database down

`GET /api/pm/jobs` and the plan save go through `get_db()`: 503 while the database is down or
missing (§ Yantra Specifics, *DB may not exist*); the list shows its load error with *Retry*. The
worker waits for `ensure_schema()` before it runs any task, so `pm_generate` runs once the database
is back and finds the day's work (the task is enqueued once, `due_tasks`).

## 6. API

### 6.1 `GET /api/pm/jobs`

| Query | Rule |
|---|---|
| `tab` | `enum_arg("tab", TABS)`, default `due`; another value: 400 "tab must be one of: due, upcoming" |
| `unit_id` | `int_arg("unit_id", None, minimum=1)`; a unit outside the user's units gives no rows |
| `assigned` | `enum_arg("assigned", ("me",))`; no Team record: no rows |

- **Rows:** the jobs in `OPEN_STATES` whose node's root unit (`equipment.NODE_JOINS`'s `u`) is
  among `accessible_unit_ids(cur, "pm_job:read")` (None: every unit; an empty set: the empty
  answer), with the filters; joined with the plan, its meter type, the assignee's name, the node,
  its unit and site, and the plan's active item count. Then one `last_readings` query over the
  plans' meter nodes; for each row `standing = job_state(due_from_job(row), latest + meter_offset,
  today)`; the rows of the asked tab, in `list_order`. `jobs_out(cur, rows, today)` builds the items
  (shared with the card's `open_job`).
- **Answer** 200 `{items, counts: {overdue, due, upcoming}}` (`counts` over both tabs: `overdue`
  the OVERDUE standing, `due` the DUE standing only, `upcoming` NOT_YET and UPCOMING; BR1-05). An
  item:

```
{id, serial, state, standing: {state, trigger, no_reading}, due_on, due_meter, days_past, created_why,
 equipment: {id, code, name}, plan: {id, title, item_count, performer},
 unit: {id, full_code}, site_code, assignee: {id, name} | null,
 meter: {equipment_id, code, meter_type: {id, name, unit, kind, decimals}, value_now, taken_at,
         value_counted, offset} | null,
 created_at}
```

- Numbers as strings through `meters_core.format_number`, dates `YYYY-MM-DD`, times as `row_to_dict`
  gives them. `unit.full_code` is the site's code, a dot and the unit's code ("SMTW.MCC2"), as the
  unit choices show it. `meter` is null for a plan without a meter trigger; `value_now` null when
  the meter has no reading; `value_counted` = `value_now` + `offset`.
- 401 without identity (before any route), 403 without the key anywhere, 503 with the database
  down.

### 6.2 The plan save

`POST /api/pm/plans` and `PUT /api/pm/plans/<id>` (S096) keep their answers. The job is made,
refreshed or cancelled inside them (§ 5.5); the screen sees it on the card after the save.

### 6.3 The card list's `schedule`

`GET /api/pm/plans?equipment_id=` (S096 § 6.2): each **active** item gains `schedule`, from
`pm_jobs.plan_schedules(cur, plans, site_id, now)`: null without `pm_job:read` at the node's site;
else `{open_job: {id, serial, standing, due_on, due_meter, days_past} | null, next_due: {due_on,
due_meter, no_reading} | null, meter: {…as § 6.1} | null}`. `next_due` is set only when there is no
open job (`schedule_inputs`, § 5.3). Queries: the open jobs of the listed plans in one query, the
latest readings in one; `schedule_inputs` per plan without an open job (a node has a few plans).
Inactive items get `schedule` null.

## 7. Design decisions

- **D1. A job is made when its plan enters the *Upcoming* window, and its standing is judged
  live.** Q3.1 a says "one open job per plan, shown as *Upcoming* a little before due": the job
  exists while it is upcoming, gets its serial then, and the *Upcoming* tab is a list of jobs, the
  same row as *Due*. S095's `job_state` gives the four states from the job's `Due`, so no state
  needs storing. Rejected: (a) jobs made only at the due point, with *Upcoming* listing plans
  without a job (two kinds of row, no serial to name a job before it is due, and a second query
  that judges every plan on every list request); (b) a job for every future occurrence (Q3.1 c,
  against the floating rule).
- **D2. The state ENUM holds the whole life now: `due`, `in_progress`, `done`, `verified`,
  `skipped`, `cancelled`.** Plan § 4.3's states, R03.9's skip and S097's cancel; an ENUM change
  later is a migration that rebuilds the table. `due` means "open, not started" (Plan § 4.3's
  first state), whatever the live standing. Rejected: only `due` and `cancelled` now (three later
  migrations of the ENUM); `open` instead of `due` (Plan's word is *due*).
- **D3. One open job per plan: the plan's row lock, and a unique key on a generated column.**
  `open_plan_id` is the plan while the job is `due` or `in_progress`, else NULL; NULLs repeat, so
  closed jobs never clash (checked on MariaDB 11.4, § 4.1). The lock makes the second writer see the
  first's job; the key stops a bug. Rejected: the lock alone (a future path that forgets it makes
  two jobs silently); a separate "open job" table (a second row to keep in step).
- **D4. The job stores its `Due` as copies, refreshed by the run and the save; the list judges
  from them.** S095 N1: "due_on and due_meter on pm_jobs are copies … rewritten when the
  recomputed values differ". With the windows and the reset offset stored too, the list needs one
  query and one readings query, and a job turns *Due* or *Overdue* on time even while the worker is
  stopped. Rejected: recomputing every input per list request (the base job, the seed's reading at
  T and the reset scan per row: N+1 queries); storing the standing (frozen when the worker stops,
  and a reading typed at 10:00 would show only next morning).
- **D5. The plan save settles its plan's job in the same transaction.** The roadmap: "saving a plan
  whose job is already due creates it at once". The same rule as the run (upcoming, due or overdue),
  so a plan saved inside its window does not wait for the morning, a deactivation cancels at once,
  and an edit that moves the due point moves the open job. One transaction: the plan and its job
  never disagree, and a refused save makes no job. Rejected: only "already due" (a plan saved two
  days before due would show its job only the next morning, unlike the same plan saved yesterday);
  a separate request after the save (a plan saved without its job if the second fails).
- **D6. The daily run commits per plan.** One transaction per plan keeps each lock short and avoids
  the run-versus-save deadlock of § 5.7; a failed plan does not hold back the others. Idempotent:
  a settled plan is found settled. The third commit exception of `task_handlers.py`. Rejected: one
  transaction for the run (as `contract_reminder_scan`): it would hold the PM counter while it waits
  on a plan that a save holds while it waits on the counter.
- **D7. A deactivated plan or a scrapped machine cancels its open, not started job** (state
  `cancelled`, with a timeline line). S096: "a stopped plan makes no jobs"; a due job of a stopped
  plan would otherwise stay *Overdue* for ever on the list (Q3.3's "until done or skipped" assumes
  a live plan). Kept as a record, never deleted. A started job (R03.4) is left to R03.4. Rejected:
  leave it open (the engineer cannot skip until R03.9, and the list fills with dead work); delete it
  (ISO 9001 § 7.5.3).
- **D8. Usage is carried across a counter reset** (§ 5.4). The simplest rule that cannot miss a job:
  a reset counts from 0, so the job comes due early, never late. Rejected: reading the latest value
  as it is (a meter-only plan would read *Not yet* for the whole old interval again: unsafe); a flag
  "Counter reset, check the plan" (a person must act, and nobody sees a flag on a job not yet made).
- **D9. A job's access and unit filter follow its node's current unit; no unit is stored.** A PM job
  is planned work on a machine; when the machine moves, its work moves with it, as its plans do
  (S096 reads plans through `load_node_for_user`). Rejected: a stored unit as tickets have (a ticket
  records where a fault happened; a job not yet done happened nowhere).
- **D10. Tabs *Due* and *Upcoming*; *Done* comes with R03.4.** Nobody can mark a job done before
  R03.4; an always-empty tab confuses the floor. Rejected: the mock-up's three tabs now.
- **D11. A row opens the plan page** (`/equipment/pm/<plan id>`) until R03.4's job page. The
  technician sees what the job will hold (its items). Rejected: rows that open nothing.
- **D12. The job's assignee is the plan's, checked at the node's site, and follows the plan while
  the job is due.** S096 A4 left a departed assignee to R03.3: the job is unassigned ("No one
  yet"), with a timeline line. Rejected: copying the id unchecked (a job assigned to a leaver).
- **D13. The run at 05:00 IST.** Before the morning shift, after the evening sheet's readings and
  the 02:30 purge; earlier than the 08:00 alert scans, so R03.7's alerts can follow the jobs made
  that morning. Rejected: 08:00 with the alerts (the morning shift would start without its jobs).
- **D14. `done_at`, `done_meter` and `timeliness` are columns now**, written by R03.4. The base query
  (§ 5.3) needs them, and S095 N1 asks a done job to keep its judgement. R03.4's migration then adds
  only its own table. Rejected: R03.4 adds them (S097's base query would read nothing).
- **D15. The meter reads live in `meters.py`.** `_last_readings` becomes public `last_readings` (one
  copy of the "latest active reading" rule, used by the card, the sheet and now PM);
  `first_reading_after` and `readings_across_reset` sit beside it. Rejected: PM's own queries on
  `meter_readings` (a second copy of the removed-reading and order rules).
- **D16. The card's job line is behind `pm_job:read` at the node's site.** The plans are read with
  `equipment:read` (S096 D3); the jobs are the new key's. Rejected: showing the job to every plan
  reader (the storekeeper would read jobs the list refuses him).
- **D17. A job pushed back by a plan edit stays open as *Not yet due*.** Rare (an interval made
  longer), and cancelling would burn a serial and a line for an edit. It shows under *Upcoming*.
  Rejected: cancelling it.

## 8. Tests and acceptance

### 8.1 Migration (`backend/tests/test_migration_v52.py`)

- A fresh database: both tables, `uq_pm_jobs_serial`, `uq_pm_jobs_open_plan`, the three indexes and
  the foreign keys `fk_pm_jobs_plan`, `fk_pm_jobs_equipment`, `fk_pm_jobs_assignee`,
  `fk_pm_job_events_job`, `fk_pm_job_events_person`.
- A v51 database with a plan (a node, a person) migrates to v52; the plan is kept.
- The ENUMs: `state` equals `pm_jobs_core.JOB_STATES`, `created_why` `(CALENDAR, METER)`,
  `timeliness` `(ON_TIME, LATE)` (`information_schema.COLUMNS.COLUMN_TYPE`); the generated
  column's expression names exactly `OPEN_STATES`: the test pulls the quoted values out of
  `GENERATION_EXPRESSION` (MariaDB stores it normalised: backticked names, lower-case `case when …
  in (…)`) and compares the tuple, not the string (BR1-07).
- One open job per plan: a second `due` job of a plan → 1062; `due` then `cancelled` then `due`
  passes; two `done` and one `due` pass; an `in_progress` and a `due` → 1062.
- The CHECKs refuse (4025): `due_on` without `grace_days`; neither `due_on` nor `meter_window`;
  `due_meter` without `meter_window`; `meter_offset` −1; `done` without `done_at`; `done_at` on a
  `due` job; `timeliness` on a `due` job; `done_meter` without `done_at`. They pass: a calendar job,
  a meter job with `due_meter` NULL and `meter_window` set, `skipped` with `done_at`.
- A duplicate serial → 1062. A re-run of v52 changes nothing (`_schema()` equal).

### 8.2 Backend

**Core** (`test_pm_jobs_core.py`, no database, written first):
- `decide`: every row of § 5.5's table, plus an inactive plan on a scrapped node with a `due` job
  (the plan's remark wins), and an active `before_use` plan with a `due` job (`None`: its `Due` has
  no field to copy).
- `due_copies` / `due_from_job`: round trip for a calendar, a meter and a `both` `Due`; `job_changes`:
  nothing changed → `{}`, each column alone, the assignee to None.
- `meter_offset`: no reset → 0; § 5.4's two worked examples; a reset as the first reading after the
  base (adds the base); base None → 0.
- `days_past`: due today → None; yesterday → 1; due_on None → None. `tab_of` each state.
  `list_order` over a mixed set (overdue, due, a meter job without `due_on`, upcoming, not yet).
  `pm_serial(2026, 11, 1)` → "PM-2026-11-001"; 1000 → "PM-2026-11-1000". `assignable_id`: a
  technician, an engineer, a manager → the id; an operator, a supervisor, None → None.
- A `datetime` where a `date` is expected, or a `float` meter value → `TypeError` / `ValueError`
  naming it.

**The daily run** (`test_pm_generate.py`; each test its own site, unit, model, machine, meter type
and plans, by `make_*` and plans inserted through `POST /api/pm/plans` as an engineer, or straight
rows where a state cannot be reached by the API; `now` fixed by monkeypatching `pm_jobs._now`):
- A monthly plan whose seed makes it due: one job, serial `PM-YYYY-MM-NNN` of the IST month, state
  `due`, `created_why` `calendar`, the copies equal `next_due`'s, the plan's assignee, a `created`
  line by `pm_generate`.
- A plan two months from due: no job. A plan 2 days before due (monthly: upcoming 3): a job.
- Run twice: still one job (idempotent); no second line.
- A meter plan: a reading past the due value → a job, `created_why` `meter`; below the window → none.
- D9 through the run: a meter plan with no reading has a calendar job (`both`) with `due_meter`
  NULL; after the first reading the next run sets `due_meter` and writes `due_changed`.
- A reset after the base (§ 5.4's first example): the job is made at the counted value, and
  `meter_offset` is 1,200.
- An inactive plan with a `due` job (row inserted): cancelled with `PLAN_INACTIVE_REMARK`; a
  scrapped node: cancelled with `NODE_SCRAPPED_REMARK`; an `in_progress` job (row inserted): left.
- An assignee who left the site: the job's `assignee_id` becomes NULL with `assignee_changed`.
- A plan whose settle raises (monkeypatched for one plan id): the other plans are settled and
  committed; the handler raises `RuntimeError`; the run again settles nothing twice.
- `should_stop` true after the first plan: `RetryLater` raised; the first plan's job is committed.
- A payload → `BadTask`. Through the worker (as `test_contract_alerts.py`'s `SCHEDULE` monkeypatch):
  the task is enqueued at its time, runs, and the job exists.
- The serial counter (BR1-02: `serial_counters` is emptied once per session, not per test): each
  test that asserts a serial fixes `pm_jobs._now` to a month of its own (a far year, e.g. 2091-03,
  one per test), so its first job is `PM-2091-03-001` whatever ran before; two jobs in that month
  number 1 and 2; a job in the next fixed month restarts at 1.

**The list and the save** (`test_pm_jobs_api.py`):
- `GET /api/pm/jobs`: an operator at the unit sees the due job (200, the item shape of § 6.1,
  `standing.state` `overdue`, `days_past`); a technician at another site's unit does not; the
  storekeeper 403; IT admin sees jobs of every unit; `unit_id` filters; `assigned=me` for the
  assignee and not for another technician; a user with no Team record and `assigned=me` → empty;
  `tab=upcoming` lists an upcoming job and a NOT_YET one; `tab=done` → 400; `counts` over both tabs.
- **Live standing:** an upcoming meter job turns `due` on the list after a reading is logged through
  `POST /api/equipment/<id>/readings`, with no run.
- `meter.value_counted` adds `meter_offset`.
- **The save:** `POST` of a plan due by its seed → 201 and one job with a `created` line by the
  engineer; `POST` of a plan far from due → no job; `PUT {active: false}` → the job `cancelled`
  with its line; `PUT {active: true}` → a new job with a new serial; `PUT` of a shorter interval →
  `due_on` changes with `due_changed`; `PUT` of the assignee → the job's assignee with
  `assignee_changed`; a `PUT` that changes nothing writes no job line; a refused `POST` (409
  duplicate title) makes no job and takes no serial: with `pm_jobs._now` fixed to
  a month of its own (as the run's tests), the next job made in that month is `…-001`; the API tests
  read the same `_now` (the save and the list call it).
- **The card:** `GET /api/pm/plans?equipment_id=` as a technician: `schedule.open_job` for the plan
  with a job, `schedule.next_due` for one without; as the storekeeper: `schedule` null; inactive
  plans: null.
- **The database down** (`db_down`, `backend/tests/conftest.py`): `GET /api/pm/jobs` → 503.

### 8.3 Existing tests that change or run again

- `backend/tests/test_rbac.py`: `test_role_matrix` — `pm_job:read` joins the rows of the operator,
  technician, supervisor, engineer, manager and IT admin, not the storekeeper; the comment above the
  rows gains "S097: pm_job:read to the operator (so the supervisor and the ladder) and IT admin; not
  the storekeeper". New `test_pm_job_keys`: the holders of `pm_job:read` are exactly those six roles
  (`compute_permissions` over `ROLES`) and it is in `SITE_SCOPED`. `test_site_scoped_keys_exist`
  and `test_every_role_gets_wildcard_permissions` stay green.
- `backend/tests/test_scheduled_tasks.py`: `test_the_improvement_alerts_at_eight_after_the_purge`
  asserts `[("purge_access_log", "02:30"), ("pm_generate", "05:00"), ("improvement_alert_scan",
  "08:00"), ("contract_reminder_scan", "08:00")]` (docstring: "S097: the PM run at 05:00, second").
  `test_the_schedule_has_the_purge` stays.
- `backend/tests/test_worker.py`: `TestTasksCard` reads `tasks[0]` (the purge, still first): green.
- `backend/tests/test_modules.py` (`LATEST_VERSION`): green at 52. `test_migration_v50.py` (S096
  filters its migrations to `<= 50`, S096 BR1-01) and `test_migration_v51.py` (S096's): green (to
  verify by the run; a v51 test that builds `_MIGRATIONS` whole gains v52 and must still pass).
  `backend/tests/test_migration_squash_v41.py` (`test_production_s_v41_gets_v50` asserts
  the versions of the later migrations, `[*range(20, 42), *[m[0] for m in CURRENT if m[0] > 41]]`, in
  the working tree since S096 BR1-01): green with v52 (BR1-11). `test_schema_docs_shell.py`: green once
  `tooling\schema-docs.bat write` has run.
- `tooling/tests/test_line_width.py`: every new and changed `.py` line at most 120 characters (the
  migration text is exempt, but kept within it anyway).
- `backend/tests/test_pm_plans_api.py` (S096's): the card list's items gain `schedule`; a test that
  compares an item whole changes; the save tests may now make jobs (a plan with a seed past due);
  the coder names every changed line in the impl report.
- `backend/tests/test_readings_api.py`, `test_meters_api.py`: run again after the `last_readings`
  rename; green.
- `backend/tests/test_auth.py`: `/api/auth/me`'s `permissions` equal `compute_permissions`: green.
- `frontend/tests/navigation.test.js`: `OPERATOR`, `ENGINEER`, `MANAGER`, `IT_ADMIN` gain
  `"pm_job:read"` (`SUPERVISOR` is `OPERATOR`; `STOREKEEPER` not); "maint_operator sees Me,
  Equipment, Tickets and Readings…" expects `["me", "equipment", "tickets", "pm", "readings"]` and
  its title names PM; "Me is first for every role with ticket:read…" expects `"pm"` after
  `"tickets"`; "Readings follows Tickets for every equipment:read holder…" becomes "Readings
  follows PM for every holder of pm_job:read (S050, S097)" (`indexOf("readings") ===
  indexOf("pm") + 1`); new: "PM follows Tickets for every holder of pm_job:read; the storekeeper
  has no PM (S097)" (`canOpenRoute("pm", STOREKEEPER)` false).
- `frontend/e2e/screens.spec.js`: `S040: the manager's bottom bar shows all six items without
  sideways scroll` becomes `S040, S097: the manager's bottom bar shows all seven items without
  sideways scroll`, expecting `["Me", "Equipment", "Tickets", "PM", "Readings", "Masters",
  "Settings"]` (`"PM"` new). Seven items of `flex: 1` at 0.75rem fit 390 px (assumption: the
  longest label "Equipment" is about 60 px; the test checks it on both phones).
- `frontend/e2e/floor.spec.js` (`S064: the bottom bar is reached by Tab…`, it looks for
  `"Tickets"`), `frontend/e2e/me.spec.js` (the first nav item is *Me*): unchanged, green.
- `frontend/e2e/pm-plans.spec.js` (S096's): its card assertions (`"2 items"`, the trigger text)
  stay true; a plan saved with a past seed now also shows a job line. The coder checks each
  assertion that reads the card's whole text and names any changed line.
- `frontend/e2e/settings.spec.js`: the Background tasks tests read their own lines: green.

### 8.4 Automated (e2e, `frontend/e2e/pm-jobs.spec.js`)

Set-up by API in the spec: each test makes its own machine with `meterMachine(testInfo, tag, {
unit: "SMTW.MCC2", modelMeters: [["Run hours", {}]] })` (`frontend/e2e/support/meters.js`) and its
plan by `POST /api/pm/plans` as the engineer (`apiAs`), with the technician as assignee
(`personId("technician")`, `frontend/e2e/support/people.js`). Dates by `istDay` and `shownDay`
(`frontend/e2e/support/tickets.js`). Day intervals keep the arithmetic plain: every 10 days, last
done 20 days ago → due 10 days ago, grace 1 → *Overdue*; last done 10 days ago → *Due* today; last
done 9 days ago → due tomorrow, upcoming 1 → *Upcoming*. Each test finds its own row by the
machine's code (the lane's database holds other tests' jobs). Untagged unless marked.

- **important** `S097: a plan saved past due shows its job as Overdue on the PM list` — as the
  technician, the nav item `"PM"`; on *Due* the row of the machine shows `"Overdue"`, a serial
  starting "PM-", the due date `shownDay(istDay(-10))` and "10 days ago", the plan's title with
  "1 item", "SMTW.MCC2" and the technician's name. A tap opens the plan page (its title as the
  heading).
- **important** `S097: a job inside its window shows under Upcoming, not under Due` — the
  *Upcoming* tab shows the row with `"Upcoming"`; the *Due* tab does not list it.
- **important** `S097: the equipment page's PM card shows the open job and the next due date` — a
  plan with a job: its card row shows `"Due"` and the serial; a second plan far from due shows "Next
  due" and its date.
- **important** `S097: deactivating the plan takes its job off the PM list` — the engineer opens the
  plan page, `"Deactivate"`, *Yes*; the technician's list has no row for the machine.
- `S097: a meter plan comes due when the reading passes its due value` — the operator logs 1,260 h
  by API **first**, then the engineer saves the plan (no daily run happens in a browser test: the
  save makes the job; BR1-08); a plan every 250 h, last done at 1,000 h: the row reads "at 1,250 h" and "Run hours now
  1,260 h" with `"Due"`.
- `S097: Assigned to me shows only my jobs` — two machines, one plan with the technician and one
  with "No one yet"; with *Assigned to me* ticked only the first row shows; the URL keeps
  `assigned=me` after a reload.
- `S097: IT admin reads the PM list and has no Assigned to me` — IT admin sees the row; no tick.
- `S097: the PM list fits a phone with no sideways scroll` (`@device`) — `expectNoSidewaysScroll`
  with three rows; the filters wrap.

`frontend/e2e/screens.spec.js` (its `screens()` list): `{ path: "/pm", title: "PM", shows: (page) =>
page.locator(".nav-tabs").getByRole("link", { name: "Due" }) }` for the `pm_job:read` roles
(`TICKET_ROLES`: every role but the storekeeper). The tabs are `nav nav-tabs` links, as on `MeView.vue`
and `ReadingsView.vue` (BR1-09).

**Runs** (settings: *Browser tests*): targeted `tooling/run-e2e-tests.bat e2e/pm-jobs.spec.js
e2e/pm-plans.spec.js e2e/equipment.spec.js e2e/screens.spec.js`, and the whole suite at Normal once
at the end (the router and the nav are shared). No change to `api.js` or `e2e/support/`, so the
*Shared code* WebKit run is not due; but **once**, for the seven-item bottom bar on the 390 px iPhone
(BR1-03): `tooling/run-e2e-tests.bat e2e/screens.spec.js --project=phone-webkit -g "S040"` (Docker
Desktop running; the repo's tooling starts the WebKit container), its result in the impl report.

### 8.5 On a real device

None. The list, the tabs and the card line are browser screens a browser engine judges (fit, no
sideways scroll, the seven-item bottom bar on both phone projects at the Full level). The worker
runs in the backend tests.

### 8.6 Acceptance and the SMTW-Review point

- All unit suites green; `tooling\schema-docs.bat check` exits 0; the targeted and the Normal browser
  runs green.
- By screen: S096's acceptance plan on a press at SMTW ("Monthly hydraulic check", every 1 month or
  250 h, last done 02-10-2026 at 1,840 h) saved on 01-11-2026 gets its job at the save: due
  02-11-2026 (31 days, grace 3, upcoming 3), so *Upcoming* on 01-11, *Due* from 02-11, *Overdue* from
  06-11-2026, unless the press reaches 2,090 h first; the technician sees it under *PM* › *Due*, the card
  shows it; IT admin reads both and changes nothing.
- **§ SMTW-Review point** (for `.claude/CLAUDE.md`): "**PM jobs (S097):** a plan has at most one open
  job (`due` or `in_progress`), held by the plan row (6e), which every pm_jobs and pm_job_events
  write takes first, and by `uq_pm_jobs_open_plan` on the generated `open_plan_id`. Jobs are made,
  refreshed and cancelled only by `pm_jobs.settle_plan_job`, from the daily `pm_generate` (05:00 IST,
  one transaction per plan) and the plan save; the due point and windows on the job are copies of
  `pm_schedule_core.next_due`, and the standing is judged live by `job_state`, never stored. A job
  is never deleted: a deactivated plan or a scrapped machine cancels its open, not started job with
  a timeline line. A path that writes a job without the plan lock, reads the open job `FOR UPDATE`
  by `open_plan_id`, or stores the standing breaks R03.3–R03.9."

## 9. Open questions and assumptions

All choices below were **decided by the orchestrator under KLA's go-ahead of 01-11-2026 ("Start
work on PM module … Do those steps … stop only for real show stoppers"), to confirm at gate B.**

- **Q1. When is a job made?** Decided: when its plan enters the *Upcoming* window (D1). (b) At the
  due point, with *Upcoming* as a list of plans.
- **Q2. The state ENUM for the whole life now** (D2), with `cancelled` added to Plan § 4.3's
  states. Taken as recommended.
- **Q3. The plan save makes the job when the plan is upcoming, not only when already due** (D5): a
  small widening of the roadmap's "already due", so the save and the run follow one rule.
- **Q4. Deactivating a plan cancels its open, not started job** (D7). A new rule; Plan.MD records
  it. Taken as recommended.
- **Q5. A counter reset carries the usage** (D8, S095 A3). Taken as recommended.
- **Q6. The run at 05:00 IST** (D13). KLA may name the shift start; moving it is one line.
- **Q7. No *Done* tab until R03.4** (D10); **rows open the plan page** (D11). Taken as recommended.
- **Q8. A machine out of use keeps making jobs** (§ 5.2). Taken as recommended.
- **A1. S095 and S096 as briefed.** Their names in § 3 hold when S097 is coded; the staleness review
  fixes this brief if they changed. In particular S096's route lock order ((6e) before (1)) and its
  card list builder.
- **A2. The handler begins inside the worker's transaction and ends it** (BR1-01): the explicit
  `conn.commit()` after the candidates read (§ 5.6 step 2); the per-plan transactions follow, and
  the worker connection is autocommit outside them (`backend/local_db.py` `get_local_db`: `"autocommit":
  True`), so each plan's `transaction(conn)` starts with no snapshot held from the candidates read.
- **A3. Seven nav items fit the phones' bottom bar** (§ 8.3): to verify by the S040 test on
  `phone-chromium` (Pixel 7) in the Normal run, and on `phone-webkit` (iPhone 14, 390 px) by the one
  targeted WebKit run of § 8.4 (BR1-03).
- **A4. The schema tool shows a generated column** (§ 3 Docs): to verify by `tooling\schema-docs.bat
  write`.
- **Notes for later steps** (not built here): R03.4 takes the plan (6e) before any job write,
  writes `done_at`, `done_meter` and `timeliness`, and decides what a started job does on a plan
  edit or deactivation; R03.5 decides whether a successor job may exist while a job waits for
  verification (`done` is not open), and its send-back to `in_progress` must clear `done_at`,
  `done_meter` and `timeliness` (`chk_pm_jobs_done`; the timeline keeps the first done) (BR1-10); R03.7 needs its own marker for *PM job due*, since a job is
  made while upcoming; R03.9 adds the override columns (then `due_from_job` sets `rescheduled`) and
  decides whether a skip writes `done_at`.
- **Size:** 28 code and test files, past the rule's 25, and about 1,000 lines (past 600; S096 is 1,060). Two tables
  (a record and its lines, one concern), one new screen and one card line. **Proposed cut** if the
  orchestrator wants it: S097a backend and task (migration, core, shell, the save hook, the run, the
  card's `schedule` field; 17 files), S097b screens (nav, list, card line, specs; 11 files).
  **Decided (orchestrator, 02-11-2026): one step**, as the reviewer advised: the screens are thin,
  and the list API's shape is exercised end to end only by them. The coder hands back in **two
  snapshot rounds**: first the backend (core tests first, then migration, shell, the run, the save
  hook, the card's `schedule`, and their tests), then the screens (nav, list, card line, label
  helpers, specs); the code reviewer reads the diff in that order, so no review sitting is bigger
  than S096's.
- **Standards *to verify*:** EN 13306 term numbers; ISO 14224's clause; SMRP's metric number.
- **No defining question for KLA.**

## 10. Amendments

None.

## Review log

### Round 1 — `2-brief-review-r1.md`, answered 02-11-2026

Sections changed: § 3 (the file count: one step, two snapshot rounds), § 5.6 (step 2: the explicit
commit; step 3: how the per-plan transactions end the worker's), § 5.7 (the (6)-after-(6e)
departure, in both LOCK ORDER notes), § 5.9 (the count line, "days ago"), § 5.10 ("days ago"),
§ 6.1 (`counts`), § 8.1 (the generation expression), § 8.2 (the serial tests), § 8.3 (the squash
test), § 8.4 (the meter test's order, the screens locator, the WebKit run, "10 days ago"), § 9 (A2,
A3, the later-step notes, *Size*).

| Finding | Answer |
|---|---|
| BR1-01 minor | Accepted (b): an explicit `conn.commit()` after the candidates read, as `purge_access_log`; § 5.6 and A2 say the handler starts inside the worker's transaction (`run_one`'s `with transaction(self.conn)`) and ends it there, then one `transaction(conn)` per plan; after the last plan the connection is autocommit again, so `mark_done` commits by itself. |
| BR1-02 minor | Accepted (a): each test that asserts a serial fixes `pm_jobs._now` to a month of its own (a far year), the run's tests and the API tests alike (the save and the list read the same `_now`); the "no serial taken" test asserts `…-001` in its own month. § 8.2. |
| BR1-03 minor | Accepted (a): one targeted run `tooling/run-e2e-tests.bat e2e/screens.spec.js --project=phone-webkit -g "S040"` in the step, its result in the impl report (§ 8.4 *Runs*, A3). |
| BR1-04 minor | Accepted (a): both LOCK ORDER notes (`equipment.py`'s bullet and `pm_jobs.py`'s note) name (6) after (6e) and (1) as a departure from the number order, with the reason: the `PM:` counter row is taken by nothing else, and a refresh-only transaction must not bump it; a counter other modules take may not copy it (§ 5.7). |
| BR1-05…BR1-11 nits | Accepted: BR1-05 `counts.due` is the DUE standing only, so "4 due · 1 overdue" adds up to the tab's rows (§ 5.9, § 6.1); BR1-06 " · 3 days ago" (the badge is the judgement; § 5.9, § 5.10, § 8.4); BR1-07 the migration test compares the quoted values of `GENERATION_EXPRESSION` as a tuple (§ 8.1); BR1-08 the reading is logged before the plan is saved (§ 8.4); BR1-09 `screens.spec.js` finds the "Due" link in `.nav-tabs` (§ 8.4); BR1-10 R03.5's send-back must clear `done_at`, `done_meter`, `timeliness` (§ 9 notes); BR1-11 the squash test already computes the later versions: the hedge is gone (§ 8.3). |

**Size (the orchestrator's question):** one step, as the reviewer advised; the coder hands back in
two snapshot rounds, backend first, then the screens, and the code review reads it in that order
(§ 9 *Size*).
