```
Step: S098 — Do the PM job on the phone
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 01-11-2026
Track: full
Baseline: refs/steps/S097 (8294764; c9cd091 + S095, S096, S097), checked by staleness review s1
Status: Done — folded into S104 (KLA 13-11-2026, gate B 2a: its code is reworked and committed with S104; its own snapshot dropped); was: Held 02-11-2026 by KLA (one path: PM templates linked to class, model or machine; R03 re-plan; 5b nothing adopted until the rework is done); was: Gate B 02-11-2026 (code review r1 (backend): 1 minor, 4 nits, fixed in round 2; r2 (screens and fixes): 3 minor, 4 nits, fixed in fix round 1 — CR2-02 changes the offline message's words, for KLA; verify review r3: no finding; device checks pending: rows 64–66 of device-checks.md); approved 02-11-2026 (gate A delegated by KLA for tonight's PM steps: "Do those steps … stop only for real show stoppers"; review r1: 0 blocker, 0 major, 6 minor, 15 nits, all accepted; one step at 30 files, two snapshot rounds; the decisions of § 9 flagged for KLA at gate B)
From: R03.4
```

# S098 — Do the PM job on the phone

## 1. What will be built

R03.4 of `docs/roadmap/R03-pm.md`, the first usable slice of PM. **A technician opens a PM job,
starts it, fills it item by item on the phone and marks it done.** S095 decides when a job is due
(`backend/pm_schedule_core.py`), S096 stores the plans (`pm_plans`, `pm_plan_items`, v51), S097
makes the jobs and lists them (`pm_jobs`, `pm_job_events`, v52, the *PM* list). S098 lets people do
them.

1. **The record** (migration **v53**, § 4): a new table `pm_job_results`, one row per item of the
   job, **copied from the plan's active items at *Start***. A job not yet started shows the plan's
   items as they are now, so it follows plan edits; a started job keeps its own copy, so a later
   plan edit never rewrites what the job recorded (Plan § 4.3a, "never rewrites history"). `pm_jobs`
   gains two columns: `performed_by_id` and `started_at`.
2. **The job page** (`/pm/jobs/<id>`, mock-up `docs/roadmap/R03-mockups/03-pm-job.html`): the job's
   header (serial, state, standing, machine, plan, due point), *Performed by* and *Started*, one
   item per row, the count "3 of 7 filled", *Mark job done*, and the job's history.
   - *Check*: three large buttons *OK* / *Not OK* / *NA*.
   - *Task*: two large buttons *Done* / *Not done*.
   - *Reading*: a number with its unit; *High* or *Low* shows as it is typed, from the item's
     limits; *NA* when no reading can be taken.
   - *Not OK*, *Not done* and a reading's *NA* need a remark (§ 5.4).
3. **Each item is saved as it is filled** (one `PUT` per item, idempotent). A network drop loses at
   most the one item whose save failed, and that item says so.
4. **Start** (§ 5.3): *Performed by* (anyone with a membership at the site, default me) and
   *Started* (the S051 time field with its *Now* tick, up to 7 days back). This is how work is
   **recorded on behalf** (Plan § 4.3, decided 18-10-2026). Start copies the items in one
   transaction under the plan's and the job's locks.
5. **A reading item that names a meter** also writes a `meter_readings` row with source `pm`,
   through the same locked code path as `meters.log_reading`, refactored into shared functions
   (§ 5.5; CLAUDE.md § SMTW-Review, *Meter readings (S039)*: the node lock before any plain read,
   both neighbours checked). There is no second insert path. A refused counter value shows on the
   item, with the *Meter reset* tick the readings screens offer.
6. **Mark job done** (§ 5.6): allowed when every item is filled. The *Done* time is the S051 time
   field again. The job stores `done_at`, `done_meter` and `timeliness` (S095 N1; S097 declared the
   columns) and reaches state `done`. Every job ends at `done` here, also one whose plan
   `needs_verification`: R03.5 adds `verified` and *Send back*.
7. **The PM list** (S097's `PmJobsView.vue`): a row opens the job page (it opened the plan page,
   S097 D11); a started job shows *In progress* and sits on *Due*; a *Done* tab (S097 D10 left it to
   R03.4).
8. **Me › Open work** (Plan § 6): "PM jobs (n)" above the tickets, as the countermeasures are
   (S071): my due, overdue and in-progress PM jobs.
9. **One new key** `pm_job:work`: the technician, so the engineer and the manager; in
   `SITE_SCOPED`, checked at the job's node's site. R03.12 widens it to the operator.
10. **Scrapping a machine waits for its started PM jobs** (§ 5.8), as it waits for open tickets
    (`equipment._check_no_open_tickets`): a scrapped record is read-only, so a started job on it
    could never be finished.

**After S098:** PM works end to end on the pilot presses, without the engineer's sign-off.

### Out of scope

- Verify and send back, the *To verify* tab, `pm_job:verify` (R03.5). A done job cannot be edited
  until R03.5's *Send back*.
- Photos on job items (R03.6). The item's photo setting is copied into the result (`photo`) but
  shown nowhere and enforced nowhere (D12).
- A ticket from a Not OK item or an out-of-limit reading (R03.10); labour and parts (R03.11).
- Alerts (R03.7); reschedule and skip (R03.9); a cancel of a started job (no path in S098).
- CIL, operators working jobs, *CIL today* (R03.12); routes (R03.15).
- A link from the equipment page's PM card straight to the job page: the card's plan row is
  already one link (S096 § 5.8); only its badge changes (§ 5.10).
- Changing *Started* after *Start* (D6), and clearing a filled item (D7).

## 2. Standards and practice

- **TPM — planned maintenance pillar.** In plain words: the team decides in advance what each
  machine needs and when, does it, and learns from the results. S095–S097 are "decides" and "comes
  due"; S098 is "does it", with a result per item that the engineer (R03.5) and the compliance
  report (R03.14) read.
- **EN 13306 — maintenance terms** (term numbers *to verify*). In plain words: a *maintenance task*
  is work done; an *inspection* checks conformity and repairs nothing. S098 follows S096's split:
  a *Task* answers *Done* / *Not done*; a *Check* (inspection) answers *OK* / *Not OK* / *NA*; a
  *Reading* is a measurement judged against limits (the condition-based part).
- **ISO 14224 — maintenance data** (clause *to verify*). In plain words: record each maintenance
  event against the item, with who did it and when, and the measured values. The job keeps who
  performed it (a person, also one without a login), when it started and finished, and each
  reading; a reading of a meter goes into the meter's own history too, at the level the plan names
  (Plan § 4.3, *Which meter a plan uses*).
- **ISO 9001:2015 § 7.5.3 — control of documented information.** In plain words: records are kept,
  protected from change, and show who did what and when. A job's items are copied at *Start* and
  never follow later plan edits; each result keeps who filled it and when; the job's history
  holds *Started*, *Performed by changed* and *Done*; a done job cannot be changed (until R03.5's
  send back, which is itself recorded).
- **SMRP — PM compliance** (metric number *to verify*). In plain words: of the PM jobs due in a
  period, the share done on time. At *Mark job done* the job stores its judgement (`timeliness`,
  S095's 10 % window) against the due point it carried, so R03.14 counts stored results and a later
  plan edit cannot change them (S095 N1).
- **ISO/IEC 27001:2022 A.5.15 — access control.** In plain words: each person may do only what the
  work needs. `pm_job:work` at the job's site; IT admin reads PM and works no job (R03 Q2.2 a).
- **Departure, stated:** Plan § 3 grants `pm_job:work` to the operator and the supervisor. S098
  grants it to the technician (and up) only, as the roadmap's R03.4 says; R03.12 widens it, with
  the data rule "an operator works CIL jobs at his units" (Plan § 3).

## 3. Where

S098 builds on three steps not committed when this brief was written. The staleness check confirms
these names before coding (§ 9 A1):

- **S095** (`docs/steps/S095-pm-schedule-core/1-brief.md`): `pm_schedule_core.timeliness(due,
  done_on, done_meter)`, the constants `ON_TIME`, `LATE`; § 5.2's rule
  "the meter value at a time T"; § 9 N1 ("at *Mark job done* the shell stores the job's final
  `due_on`, `due_meter` and `timeliness`").
- **S096** (`docs/steps/S096-pm-plans/1-brief.md`): `pm_plan_items` columns `id`, `plan_id`,
  `position`, `item_type`, `text`, `help_text`, `photo`, `unit`, `min_value`, `max_value`,
  `meter_equipment_id`, `meter_type_id`, `active`; `pm_plans` columns `id`, `equipment_id`,
  `title`, `needs_verification`, `meter_equipment_id`, `meter_type_id`, `active`;
  `pm_plans_core.TASK`, `CHECK`, `READING`, `ITEM_TYPES`, `PHOTO_SETTINGS`, `STORED_DECIMALS`,
  `item_limits_text(item, meter_type=None, meter_code=None)`; the lock rule "(6e) the PM plan row,
  first in its transaction"; § 9 A6 (the item's limits judge the job's value; the meter reading keeps
  the meter's own limit state); `frontend/src/utils/pmLabels.js` (its `personLabel(person)`:
  "Kannan (Technician)", "Ravi (Technician) · Atlas Copco"), `frontend/tests/pmLabels.test.js`,
  `frontend/src/views/equipment/PmPlansCard.vue`, `frontend/src/views/PmPlanView.vue` (the route
  `pm-plan`, `/equipment/pm/<id>`). S096 is coded: these names are checked against the working tree
  (02-11-2026).
- **S097** (`docs/steps/S097-pm-jobs-due/1-brief.md`, coded; checked against the code by staleness
  review s1): migration v52; `pm_jobs` columns `id`, `serial`, `plan_id`, `equipment_id`, `state`,
  `created_why` (`ENUM('calendar','meter') NOT NULL`), `due_on`, `due_meter`, `grace_days`,
  `upcoming_days`, `meter_window`, `meter_offset`, `assignee_id`, `done_at`, `done_meter`,
  `timeliness`, `open_plan_id` (a generated PERSISTENT column: the plan while the state is `due` or
  `in_progress`; never written), `created_at`, `created_by`, `updated_at`, `updated_by`; the CHECK
  `chk_pm_jobs_done`; `pm_job_events` columns `id`, `job_id`, `event`, `from_state`, `to_state`,
  `occurred_at`, `person_id`, `due_on`, `due_meter`, `remark`, `created_at`, `created_by`;
  `pm_jobs_core.DUE_STATE`, `IN_PROGRESS`, `DONE`, `VERIFIED`, `SKIPPED`, `CANCELLED`, `JOB_STATES`,
  `OPEN_STATES`, `BASE_STATES`, `RUN_ACTOR` (`"pm_generate"`), `TABS`, `TAB_DUE`, `TAB_UPCOMING`,
  `decide`, `due_from_job`, `tab_of(standing_state)`, `list_order(item)`; `pm_jobs.py` with
  `pm_jobs_bp`, `LOCK_PLAN`, `SHARE_NODE`, `_JOB_SELECT` (open jobs only), `meter_type_out(row)`,
  `settle_plan_job(cur, plan_id, node_lifecycle, now, actor)`, `jobs_out(cur, rows, today)`,
  `_counts`, `_EMPTY`, `_now(cur)`, `plan_schedules`, `list_jobs`; `meters.last_readings` (public),
  `meters.first_reading_after`; the route `GET /api/pm/jobs` (§ 6.1 there);
  `frontend/src/views/PmJobsView.vue` (its rows `.job-row` with `data-equipment`);
  `STANDING_LABELS`, `STANDING_BADGES`, `dueText`, `daysPastText`, `meterNowText`, `assigneeText`,
  `jobsQuery`, `countText(tab, counts)`, `nextDueText` in `pmLabels.js`;
  `frontend/e2e/pm-jobs.spec.js`; the route `pm` (`/pm`). S097 § 5.7's rule, in `pm_jobs.py`'s LOCK
  ORDER note: "a job write (start, an item, done) takes its plan (6e) first, then the job".

### Backend

- `backend/local_db.py`: migration **v53** at the end of `_MIGRATIONS`, after S097's v52 (§ 4.1).
  No `_PRECONDITIONS` entry (§ 4.1, *Existing rows*).
- `backend/pm_work_core.py` (new, pure; § 5.1): the constants and messages, `result_rows`,
  `validate_result`, `result_changes`, `is_filled`, `unfilled_count`, `state_error`,
  `job_time_error`, `done_meter_counted`. Imports: `pm_jobs_core` (the state constants),
  `pm_plans_core.TASK`, `CHECK`, `READING`, `STORED_DECIMALS`; `meters_core.validate_reading`,
  `limit_state`, `GAUGE`, `format_number`, `READING_BACKDATE_DAYS`; `tickets_core.FUTURE_SKEW`,
  `EVENT_TIME_FUTURE` (pure to pure, public names; BR1-04, BR1-05). No DB, no clock, no Flask.
- `backend/pm_work.py` (new): the blueprint `pm_work_bp` (§ 6: the job page, start, an item, the
  performer, done), its LOCK ORDER note (§ 5.7), and `job_detail`. Imports: `pm_work_core`,
  `pm_jobs_core`, `pm_schedule_core.timeliness`; `import pm_jobs` and its `LOCK_PLAN`,
  `SHARE_NODE` (the two lock statements, reused as `pm_plans.py` does; BS1-02), `meter_type_out`
  (the meter type's answer shape, BS1-03), `settle_plan_job`, `jobs_out` and `_now`, always called through the module (`pm_jobs._now(cur)`), so a test that
  monkeypatches `pm_jobs._now` (S097 § 8.2) fixes the clock here too (BR1-08);
  `meters.lock_node`, `meter_in_force`, `write_reading`, `reading_at_minute`,
  `remove_reading_row`, `last_readings`, `first_reading_after`; `require_perm`, `require_perm_at`,
  `has_perm_at`, `current_person_id` (`backend/auth_utils.py`); `ApiError`, `actor`, `clean_body`
  (`backend/api_common.py`); `get_db`, `insert_row`, `update_row`, `transaction`, `row_to_dict`
  (`backend/db_helpers.py`); `load_node_for_user`, `accessible_unit_ids`, `SCRAPPED_MESSAGE`
  (`backend/equipment.py`); `SCRAPPED` (`backend/equipment_core.py`); `person_at_site`,
  `PERSON_AT_SITE` (`backend/tickets.py:371`, `backend/tickets.py:140`). It never imports
  `pm_plans.py`.
- `backend/pm_jobs.py` (S097's): `GET /api/pm/jobs` gains the tab `done` (paged, § 6.3) and widens
  `assigned=me` to "assignee or performer" (§ 6.3). `_JOB_SELECT` and `jobs_out` keep serving open
  jobs only (BS1-01): a new `_DONE_SELECT` (the same joins, `WHERE j.state IN ('done','verified')`,
  `ORDER BY j.done_at DESC, j.id DESC`, `LIMIT … OFFSET`, and a `COUNT(*)` for `total`) feeds the
  *Done* tab, and the item dict of `jobs_out` moves into one function `_job_item(row, standing,
  reading)` that both loops call (the done loop passes `standing=None, reading=None`), so § 6.2's item
  shape stays one copy. The items gain `state`, `performed_by`, `started_at`, `done_at`,
  `timeliness`; `counts` keeps coming from the open jobs (`_counts`, and `_EMPTY`), with
  `in_progress` added, so the tab counts never depend on the page. The two call sites of § 5.9:
  `list_jobs` calls `tab_of(item["state"], item["standing"]["state"])`, and `jobs_out` builds
  `list_order`'s item with the job's `state`. `settle_plan_job` is **unchanged**: its
  table already leaves an `in_progress` job alone (S097 § 5.5, first row); S098 adds tests that
  prove it (§ 8.2). Its LOCK ORDER note gains the S098 lines (§ 5.7).
- `backend/pm_jobs_core.py` (S097's): `TAB_DONE = "done"`, `TABS = (TAB_DUE, TAB_UPCOMING,
  TAB_DONE)`; `tab_of(state, standing_state)` (a started job is on *Due*, § 5.9); `list_order`
  puts the started jobs first (§ 5.9).
- `backend/meters.py`: `_lock_node` becomes the public `lock_node` (one name for the meter writes,
  the readings and PM; BR1-07), and `log_reading`'s body is split into three more public functions
  it then calls (§ 5.5): `meter_in_force`, `reading_at_minute`, `write_reading`; and
  `remove_reading`'s update into `remove_reading_row`. No change of behaviour for the readings
  routes. Its module docstring names the PM path.
- `backend/equipment.py`: the scrap check `_check_no_started_pm_jobs` beside
  `_check_no_open_tickets` (§ 5.8), called in `update_equipment` where the ticket check is
  called; the LOCK ORDER note gains "(6f) the PM job row" and the S098 bullet (§ 5.7).
- `backend/config_rbac.py`: `"pm_job:work": ("maint_technician",)` after S097's `pm_job:read`,
  with a comment (§ 5.2); the key joins `SITE_SCOPED`.
- `backend/app.py`: `app.register_blueprint(pm_work_bp, url_prefix="/api/pm")` after S097's
  `pm_jobs_bp` line.

### Tests

- `backend/tests/test_migration_v53.py` (new; § 8.1), with `backend/tests/migration_helpers.py`.
- `backend/tests/test_pm_work_core.py` (new; § 8.2), written and green before the shell.
- `backend/tests/test_pm_work_api.py` (new; § 8.2): the job page, start, items, readings, done,
  the performer, the plan-edit and run rules for a started job.
- `backend/tests/test_pm_jobs_api.py` (S097's): the *Done* tab, `assigned=me` with the performer,
  `counts.in_progress` (§ 8.3).
- `backend/tests/test_pm_jobs_core.py` (S097's): `tab_of` and `list_order` (§ 8.3).
- `backend/tests/test_equipment_api.py`: a scrap with a started PM job (§ 8.3).
- `backend/tests/test_rbac.py`: `test_role_matrix` rows and a new `test_pm_job_work_key` (§ 8.3).
- `backend/tests/conftest.py`: `pm_job_results` joins `_TABLES`, first in the tuple (before S097's
  `pm_job_events`).

### Frontend

- `frontend/src/views/PmJobView.vue` (new): the job page (§ 5.10).
- `frontend/src/views/pm/PmJobDoneDialog.vue` (new): *Mark job done* (§ 5.10).
- `frontend/src/components/PmJobRow.vue` (new): one job row, taken out of S097's `PmJobsView.vue`
  so the PM list and *Me* show the same row (CLAUDE-COMMON *DRY*).
- `frontend/src/router/index.js`: `{ path: "/pm/jobs/:id(\\d+)", name: "pm-job", component:
  PmJobView, meta: { title: "PM job" } }` after S097's `pm` route; under `/pm/` so the *PM* nav item
  stays lit. A shared file (settings: *Shared code*): the whole browser suite runs again.
- `frontend/src/views/PmJobsView.vue` (S097's): the *Done* tab, rows through `PmJobRow.vue`, the
  count line with *in progress* (§ 5.9).
- `frontend/src/views/equipment/PmPlansCard.vue` (S096's, S097's line): an open job in progress shows
  the badge *In progress* (§ 5.10).
- `frontend/src/views/MeView.vue`: the "PM jobs (n)" section (§ 5.11).
- `frontend/src/utils/pmLabels.js` (S096's): `RESULT_LABELS`, `jobBadges(job)`, `limitFlag(raw,
  min, max)`, `filledText(filled, total)`, `resultBody(item, choice)`, `TIMELINESS_LABELS`,
  `PM_EVENT_LABELS` (§ 5.10).
- `frontend/tests/pmLabels.test.js` (S096's): the new helpers.
- `frontend/e2e/pm-job.spec.js` (new; § 8.4). Set-up helpers in the spec file; `frontend/e2e/
  support/` is unchanged.
- `frontend/e2e/pm-jobs.spec.js` (S097's): the row opens the job page; the *Done* tab (§ 8.3).
- `frontend/e2e/me.spec.js`: one test (§ 8.4).
- `frontend/e2e/screens.spec.js`: the job page (§ 8.4).

### Docs (housekeeping, by the coder)

- `docs/schema/notes.json`: `pm_job_results` moves from `planned` to `tables` in the area
  *Preventive maintenance* (the area's note gains "job results (S098)"); the `pm_jobs` line gains
  `performed_by_id` and `started_at`; the `meter_readings` line's "A link to a PM job's result row
  comes with PM (phase 4)" becomes "`source` `pm`: logged by a PM job's reading item; the result row
  names it (`pm_job_results.reading_id`, S098)". Then `tooling\schema-docs.bat write`, read
  `git diff docs/schema/`, and `check` exits 0. `schema.json` and `schema-data.js` are generated.
- `docs/Plan.MD` § 4.3, under *PM job*: a *Built (S098)* paragraph (start, the copy, items saved
  one by one, recorded on behalf, the reading to the meter, done, the state `done` for every job
  until R03.5; D1–D12 as decisions). § 3: one paragraph for `pm_job:work` and the departure of § 2.
  § 6: the *Me* bullet's "PM jobs due and CIL jobs join *Open work* in phase 4 (R03.4)" becomes
  "PM jobs due, overdue and in progress sit above the tickets in *Open work* (S098); CIL jobs join in
  R03.12"; the § 2 *Me* item (8) the same.
- `.claude/CLAUDE.md`: § Step workflow, *Self-check, repo items* (2): `pm_work.py` joins the LOCK
  ORDER notes; § SMTW-Review: the *Meter readings (S039)* point names the PM path, and the new point
  of § 8.6.
- `docs/steps/device-checks.md`: the rows of § 8.5.
- `docs/Keycloak.md`: no change (no Keycloak role changes).

**File count:** 30 code and test files: backend 9 (`local_db.py`, `pm_work_core.py`, `pm_work.py`,
`pm_jobs.py`, `pm_jobs_core.py`, `meters.py`, `equipment.py`, `config_rbac.py`, `app.py`), backend
tests 8, frontend 13. Over the size rule's 25 (§ 9, *Size*).

## 4. Data model

### 4.1 Migration v53

```sql
-- PM jobs (S098, R03.4): who performed the job (any person with a membership at the site, also one
-- without a login: recorded on behalf, Plan § 4.3) and when it started.  Both set at Start; a job in
-- progress or done has both.  done_at is S097's column, written at Mark done.
ALTER TABLE pm_jobs
    ADD COLUMN IF NOT EXISTS performed_by_id INT NULL AFTER assignee_id,
    ADD COLUMN IF NOT EXISTS started_at DATETIME NULL AFTER performed_by_id,
    ADD KEY IF NOT EXISTS ix_pm_jobs_performer (performed_by_id, state),
    ADD CONSTRAINT fk_pm_jobs_performer
        FOREIGN KEY IF NOT EXISTS (performed_by_id) REFERENCES people (id);
ALTER TABLE pm_jobs ADD CONSTRAINT IF NOT EXISTS chk_pm_jobs_started CHECK (
    (state NOT IN ('in_progress','done','verified') OR (started_at IS NOT NULL AND performed_by_id IS NOT NULL))
    AND (started_at IS NOT NULL OR performed_by_id IS NULL)
    AND (done_at IS NULL OR started_at IS NULL OR done_at >= started_at));

-- The items of a started job (S098): a copy of the plan's active items at Start (Plan § 4.3a: a
-- plan edit never rewrites a job's record), and the result of each.  A check answers ok / not_ok /
-- na, a task done / not_done; a reading holds a value (judged by the copied limits: limit_state) or
-- na.  A reading that names a meter logs its value as a meter reading (source pm); reading_id names
-- it.  Rows are never deleted; a result is changed only while the job is in progress.
CREATE TABLE IF NOT EXISTS pm_job_results (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    job_id              INT NOT NULL,
    plan_item_id        INT NOT NULL,
    position            SMALLINT NOT NULL,
    item_type           ENUM('task','check','reading') NOT NULL,
    text                VARCHAR(200) NOT NULL,
    help_text           VARCHAR(500) NULL,
    photo               ENUM('none','optional','required') NOT NULL,
    unit                VARCHAR(20) NULL,
    min_value           DECIMAL(14,3) NULL,
    max_value           DECIMAL(14,3) NULL,
    meter_equipment_id  INT NULL,
    meter_type_id       INT NULL,
    outcome             ENUM('ok','not_ok','na','done','not_done') NULL,
    value               DECIMAL(14,3) NULL,
    limit_state         ENUM('low','high') NULL,
    remark              VARCHAR(500) NULL,
    reading_id          INT NULL,
    filled_at           DATETIME NULL,
    filled_by           VARCHAR(100) NULL,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by          VARCHAR(100) NOT NULL,
    CONSTRAINT uq_pm_job_results_item UNIQUE (job_id, plan_item_id),
    CONSTRAINT uq_pm_job_results_position UNIQUE (job_id, position),
    CONSTRAINT fk_pm_job_results_job FOREIGN KEY (job_id) REFERENCES pm_jobs (id),
    CONSTRAINT fk_pm_job_results_item FOREIGN KEY (plan_item_id) REFERENCES pm_plan_items (id),
    CONSTRAINT fk_pm_job_results_meter_equipment FOREIGN KEY (meter_equipment_id) REFERENCES equipment (id),
    CONSTRAINT fk_pm_job_results_meter_type FOREIGN KEY (meter_type_id) REFERENCES meter_types (id),
    CONSTRAINT fk_pm_job_results_reading FOREIGN KEY (reading_id) REFERENCES meter_readings (id),
    CONSTRAINT chk_pm_job_results_outcome CHECK (
        (item_type = 'check' AND (outcome IS NULL OR outcome IN ('ok','not_ok','na')) AND value IS NULL)
        OR (item_type = 'task' AND (outcome IS NULL OR outcome IN ('done','not_done')) AND value IS NULL)
        OR (item_type = 'reading' AND (outcome IS NULL OR outcome = 'na') AND (outcome IS NULL OR value IS NULL))),
    CONSTRAINT chk_pm_job_results_reading CHECK (
        (limit_state IS NULL OR value IS NOT NULL)
        AND (reading_id IS NULL OR (value IS NOT NULL AND meter_type_id IS NOT NULL))
        AND ((meter_equipment_id IS NOT NULL) = (meter_type_id IS NOT NULL))),
    CONSTRAINT chk_pm_job_results_filled CHECK (
        (filled_at IS NULL) = (outcome IS NULL AND value IS NULL)
        AND (filled_at IS NULL) = (filled_by IS NULL))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

- **The copy** (`result_rows`, § 5.3) takes every column S096 gives an item, as it is: `unit` NULL
  for a reading with a meter (the meter type's unit is joined), the limits the item's own (S096 § 9
  A6). `plan_item_id` keeps the link, so R03.17's reference photo and a later trend per item find
  the item; S096 never deletes an item row (S096 D4), so the foreign key always holds.
- **The ENUMs equal the cores' constants.** `item_type` lists `pm_plans_core.ITEM_TYPES`, `photo`
  `pm_plans_core.PHOTO_SETTINGS`, `outcome` `pm_work_core.OUTCOMES`, `limit_state`
  `(meters_core.LOW, meters_core.HIGH)`. A test reads `information_schema.COLUMNS` and compares
  (§ 8.1).
- **Filled** is `outcome IS NOT NULL OR value IS NOT NULL` (`pm_work_core.is_filled`); the CHECK
  ties `filled_at` / `filled_by` to it, so an unfilled row has neither.
- **No `updated_at` / `updated_by`:** `filled_at` / `filled_by` are stamped on every change of a
  result, so they say who filled it last. The first filling is not kept apart (D7).
- **`reading_id`** names the meter reading the item logged. When the item's value changes, the old
  reading is removed (its `removed_at`, `removed_by`) and the new one named (§ 5.5). A removed
  reading stays a row, so the foreign key holds.
- **`text` VARCHAR(200), `help_text` VARCHAR(500), `unit` VARCHAR(20)** equal S096's columns, so the
  copy never truncates. `remark` VARCHAR(500): one or two sentences on the floor.
- **Existing rows** (fact from S097 § 1: S097 writes only the states `due` and `cancelled`): every
  `pm_jobs` row then has `started_at` and `performed_by_id` NULL and `done_at` NULL, so
  `chk_pm_jobs_started` holds for them; the migration test builds a v52 database with a due and a
  cancelled job and migrates it (§ 8.1). So no `_PRECONDITIONS` entry: no existing row is changed and
  none can break the new CHECK.
- **Beside v52's CHECK** (BS1-05): `chk_pm_jobs_done` (S097) wants `done_at` on `done` / `verified`,
  allows `done_at` only on `done`, `verified`, `skipped`, `done_meter` only with `done_at`, and
  `timeliness` only on `done` / `verified`. § 5.6 step 4's one `UPDATE` (state `done` with
  `done_at`, `done_meter`, `timeliness`, and `started_at` already set) satisfies both CHECKs. Start's
  `UPDATE` (state `in_progress` with `started_at` and `performed_by_id`, no `done_at`) too.
  `open_plan_id` is generated and never written: it follows `state`. The migration test's v52 rows
  set `created_why` (`NOT NULL`).
- **Re-run safety:** `ADD COLUMN IF NOT EXISTS`, `ADD KEY IF NOT EXISTS`, `FOREIGN KEY IF NOT EXISTS`
  (the v50 pattern for `people.vendor_id`), `ADD CONSTRAINT IF NOT EXISTS`, `CREATE TABLE IF NOT
  EXISTS`; three statements; a run stopped between them completes on the next start.
- **Foreign keys:** no `ON DELETE` (RESTRICT), as every key in the schema. Rollback: the release of
  S097 (v52) never reads the new columns or the table.

### 4.2 What is computed, never stored

- The standing of a started job (S097: `job_state` from its stored copies, live); a done job shows
  its stored `timeliness` instead.
- *High* / *Low* while typing (the page); the stored `limit_state` is the server's.
- The filled count, *can_start*, *can_work*, the names (joins), `limits_text`
  (`pm_plans_core.item_limits_text` over the copied columns).

## 5. Rules

### 5.1 The pure core (`backend/pm_work_core.py`)

```python
WORK_KEY = "pm_job:work"
OK, NOT_OK, NA, DONE_OUTCOME, NOT_DONE = "ok", "not_ok", "na", "done", "not_done"
OUTCOMES = (OK, NOT_OK, NA, DONE_OUTCOME, NOT_DONE)          # the ENUM's order
OUTCOMES_BY_TYPE = {CHECK: (OK, NOT_OK, NA), TASK: (DONE_OUTCOME, NOT_DONE), READING: (NA,)}
REMARK_MAX = 500
# A reading without a meter is parsed at pm_plans_core.STORED_DECIMALS (DECIMAL(14,3)), imported (BR1-05)
START, FILL, PERFORMER, MARK_DONE = "start", "fill", "performer", "done"   # the actions state_error judges
STARTED_EVENT, PERFORMER_EVENT, DONE_EVENT = "started", "performer_changed", "done"
```

**Messages** (CLAUDE-COMMON writing style B):

| Constant | Text | Field / status |
|---|---|---|
| `START_FIRST` | "Start the job first." | 409 |
| `ALREADY_STARTED` | "This job has been started. Reload the page." | 409 |
| `JOB_DONE` | "This job is done and cannot be changed." | 409 |
| `JOB_CANCELLED` | "This job was cancelled." (state `cancelled`; also `skipped` until R03.9 gives the skip its own text, BR1-16) | 409 |
| `NO_ITEMS` | "This plan has no items. Ask an engineer to add items to the plan." A defensive 409, unreachable today: S096 keeps at least one active item on every plan (BR1-10) | 409 |
| `NOT_ALL_FILLED` | "Fill every item first: 3 of 7 are not filled." (`not_all_filled(n, total)`) | 409 |
| `PERFORMED_BY_NEEDED` | "Choose who did the work." (not `PERFORMER_NEEDED`: `pm_plans_core` has that name for the plan's performer, BR1-05) | 400 `performed_by_id` |
| `PERSON_AT_SITE` | "Choose a person from this site" (`tickets.PERSON_AT_SITE`) | 400 `performed_by_id` |
| `TIME_TOO_OLD` | "Enter a time up to 7 days back." | 400 `started_at` / `done_at` |
| `EVENT_TIME_FUTURE` | "That time is in the future" (`tickets_core`) | 400 |
| `DONE_BEFORE_START` | "Done must be at or after Started, 27-10-2026 09:10." | 400 `done_at` |
| `CHOOSE_OUTCOME` | per type: "Choose OK, Not OK or NA." / "Choose Done or Not done." / "Enter the reading, or tap NA." | 400 `outcome` |
| `VALUE_OR_NA` | "Enter the reading or tap NA, not both." | 400 `value` |
| `REMARK_NEEDED` | Not OK: "Say what is wrong."; Not done: "Say why it was not done."; a reading's NA: "Say why there is no reading." | 400 `remark` |
| `REMARK_TOO_LONG` | "Remark must be at most 500 characters" | 400 `remark` |
| `REMARK_NOT_TEXT` | "Remark must be text" | 400 `remark` |
| `NOT_LOGGED` | "Saved on the job only: this machine no longer has the meter <name>." (the answer's `meter_note`, § 5.5) | — |
| `SAME_MINUTE_PM` | "The meter already has a different reading at this job's start time (27-10-2026 09:10). Ask an engineer to check the meter's readings." | 409 `value` |

| Function | Input → output | Rule |
|---|---|---|
| `result_rows(items)` | the plan's active item rows in `position` order → insert dicts | copies `plan_item_id` (the item's `id`), `position`, `item_type`, `text`, `help_text`, `photo`, `unit`, `min_value`, `max_value`, `meter_equipment_id`, `meter_type_id`; every result column None |
| `validate_result(body, result, meter_type)` | the body, the stored result, the meter type `{kind, decimals}` or None → `(clean, None)` or `(None, (field, message))` | § 5.4 |
| `result_changes(stored, clean, linked_reset=None)` | the stored result, the clean body, the linked reading's `is_reset` (when `reading_id` is set; passed by the shell) → `{column: value}` of the columns that differ, plus `"is_reset"` when the sent mark differs from `linked_reset` | `{}` when nothing changed (idempotent; BR1-03) |
| `is_filled(result)` | → bool | `outcome` or `value` set |
| `unfilled_count(results)` | → int | |
| `state_error(state, action)` | a job state, one of the four actions → `(message, 409)` or None | § 5.2's table |
| `job_time_error(moment, now, not_before=None)` | naive IST datetimes → message or None | its own three comparisons, in order (BR1-04): `moment > now + FUTURE_SKEW` → `EVENT_TIME_FUTURE`; `moment < now - timedelta(days=READING_BACKDATE_DAYS)` → `TIME_TOO_OLD` (exactly 7 days is allowed); `not_before` set and `moment < not_before` → `DONE_BEFORE_START` with that time |
| `done_meter_counted(done_meter, offset)` | `Decimal` or None, `Decimal` → `Decimal` or None | `done_meter + offset` (§ 5.6) |

Type rules as S095 D8: a wrong input type raises `TypeError` / `ValueError` naming it (a shell
bug). The window is the readings' window for every role, admin included: the constant
`meters_core.READING_BACKDATE_DAYS` (7 days; S039 decision 8) itself, not the tickets' 7, so the two
can never drift apart (BR1-04). A PM reading is logged at the job's start time (§ 5.5), so the start
window must not exceed the readings' window. S028's backlog window (`backdate_days`) does not apply
(D5).

### 5.2 Who may do what, and when

| Key | Holders | Where |
|---|---|---|
| `pm_job:work` (new) | `("maint_technician",)`, so the engineer and the manager; not the operator or the supervisor yet (R03.12), not the storekeeper, not IT admin (R03 Q2.2 a) | `SITE_SCOPED`; checked at the site of the job's node's current unit (S097 D9) |
| `pm_job:read` (S097) | operator and up, IT admin | the job page: the node's root unit among `accessible_unit_ids(cur, "pm_job:read")`, else 404 |

Comment in `config_rbac.py`: "Doing a PM job (S098, R03.4): start it, fill its items, mark it done.
The technician, so the engineer and the manager; any holder at the job's site may work any job
there, assigned to him or not, as tickets (ticket:work).  Not IT admin, who reads PM only (R03 Q2.2
a).  Plan § 3 grants it to the operator too: R03.12 widens it, with the rule that an operator works
CIL jobs at his units."

**State × action** (`state_error`):

| State | Start | An item / the performer | Mark done |
|---|---|---|---|
| `due` | allowed | an item: 404 (no result row yet: the pre-read of § 5.7 finds none, BR1-01); the performer: `START_FIRST` | `START_FIRST` |
| `in_progress` | `ALREADY_STARTED` | allowed | allowed (if all filled) |
| `done`, `verified` | `JOB_DONE` | `JOB_DONE` | `JOB_DONE` |
| `cancelled`, `skipped` | `JOB_CANCELLED` | `JOB_CANCELLED` | `JOB_CANCELLED` |

`state_error(DUE_STATE, FILL)` still answers `START_FIRST` in the core (R03.5's send back keeps the
rows, so the cell may become live); it is tested in the core only.

- **Any `pm_job:work` holder at the site works any job there** (D3), assigned to him or not, also
  a job another person started: as `ticket:work`. The job keeps its assignee; *Performed by* says
  who did the work.
- **The checks' order on every write:** 401 (no identity, before any route) → 403 `require_perm`
  (the key held nowhere) → 404 (the job missing, or its node outside the user's units:
  `load_node_for_user`'s check, by `equipment:read`'s units, BR1-19) → 403
  `require_perm_at("pm_job:work", site)` → 409 `state_error` → 400 the body → 409 the item
  refusals. Every `pm_job:work` holder holds `pm_job:read` (the technician includes the operator;
  `test_pm_job_work_key` pins it), so a worker never meets a 404 for a job his unit has.
- **Identity:** no field changes who can log in or what anyone sees. *Performed by* names a person
  by id; only the name is answered (no login, no email). A user with no Team record may still start
  a job, naming another person as performer; *Me* shows him no PM jobs (§ 5.11).

### 5.3 Start (`POST /api/pm/jobs/<id>/start`)

Body `{performed_by_id, started_at}`:

- `performed_by_id`: required, an integer ≥ 1, not a boolean (`PERFORMED_BY_NEEDED`); then
  `tickets.person_at_site(cur, id, site)` at the node's site must find the person (any role: an
  operator or a contractor without a login is the case of *recorded on behalf*), else 400
  `PERSON_AT_SITE`. The page sends the user's own person (`userPersonId`) by default.
- `started_at`: `null` or absent = the server's `now` (to the minute, `meters_core.to_minute`, as
  readings and ticket times); else `tickets_core.parse_event_time` (400 `EVENT_TIME_FORMAT`), to the
  minute, then `job_time_error(started_at, now)`. A start before the job's `created_at` is allowed
  (a job made this morning, the work done two days ago and recorded on behalf); the history then
  shows *Started* before *Created*, as the ticket timeline shows a back-dated event (BR1-14).
- Unknown fields are ignored (`clean_body`).

The transaction (§ 5.7 has the locks): the state from the locked job row (`state_error(…, START)`);
the node's `lifecycle` from its locked row: `scrapped` → 409 `SCRAPPED_MESSAGE` (S097 cancels a due
job of a scrapped node only in the next run or plan save, so one can still be listed); the plan's
active items (`SELECT … FROM pm_plan_items WHERE plan_id = %s AND active = 1 ORDER BY position,
id`); none → 409 `NO_ITEMS`; then:

1. `insert_row(cur, "pm_job_results", row, actor())` for each of `result_rows(items)`, in order.
2. `update_row(cur, "pm_jobs", job_id, {state: IN_PROGRESS, performed_by_id, started_at}, actor())`
   (`open_plan_id` stays the plan: `in_progress` is open).
3. The event `started`: `from_state` `due`, `to_state` `in_progress`, `occurred_at` `started_at`,
   `person_id` the performer.

The answer is the job page's (§ 6.2). The due point and windows on the job stay as they are from
here on: S097 refreshes only a `due` job (D2).

**A double tap** on *Start job*: the second request waits on the plan lock, then reads the job
`in_progress` → 409 `ALREADY_STARTED`; the page reloads the job and shows it started.

### 5.4 One item (`PUT /api/pm/jobs/<id>/results/<result_id>`)

Body `{outcome, value, remark, is_reset}`, every field optional; the page sends all four for the
item's type. `validate_result(body, result, meter_type)`, in this order:

| Item type | Allowed | Rules |
|---|---|---|
| `check` | `outcome` in `(ok, not_ok, na)`; `value` null | another outcome or none → `CHOOSE_OUTCOME`; a value → `CHOOSE_OUTCOME` |
| `task` | `outcome` in `(done, not_done)`; `value` null | likewise |
| `reading` | `value` (a number), or `outcome` `na` with no value | both → `VALUE_OR_NA`; neither → `CHOOSE_OUTCOME` ("Enter the reading, or tap NA."); another outcome → `CHOOSE_OUTCOME` |

- **The value** of a reading: `meters_core.validate_reading(value, kind, decimals, is_reset, None)`
  with the meter type's kind and decimals when the item names a meter, else `GAUGE` and
  `pm_plans_core.STORED_DECIMALS` (a free value may be negative, a temperature). Its texts as they
  are ("Enter a number with up to 1 decimal", "A counter cannot be below zero"; field `value`).
- **`is_reset`**: optional, default false. `validate_reading` judges it with the same call, in its
  own words and on `is_reset`: not a boolean → "Meter reset must be true or false"
  (`RESET_NOT_BOOL`); true on a gauge or a free value → "Only a counter can be reset"
  (`ONLY_A_COUNTER_RESETS`). No PM text of its own (BR1-05).
- **The remark:** trimmed, empty → None; not text → `REMARK_NOT_TEXT`; over 500 →
  `REMARK_TOO_LONG`. Required for `not_ok`, `not_done` and a reading's `na` (`REMARK_NEEDED`). The
  API accepts a remark with any outcome (one rule, no extra refusal), but **the page sends
  `remark: null`** on a tap of *OK*, *Done* or a check's *NA* and on a reading's *Save* (BR1-02):
  the remark belongs to the answer it explains, so a row first saved *Not OK* and then corrected to
  *OK* loses its fault text.
- **`limit_state`** = `meters_core.limit_state(value, min_value, max_value)` over the **result's
  copied limits** (S096 § 9 A6), `None` for `na`; `not_ok` never (that is a Yes / No meter's word).
- **Idempotent:** `result_changes(stored, clean, linked_reset)` over `outcome`, `value`,
  `limit_state`, `remark`, and the sent `is_reset` against the linked reading's `is_reset` (read by
  the shell when `reading_id` is set; BR1-03); empty → nothing written, no meter reading, the answer as it stands (a retry after a lost
  answer is harmless). Else `UPDATE pm_job_results SET … , filled_at = now, filled_by = actor()`.
- **A result is never emptied** (D7): the page has no *Clear*; a wrong tap is changed by another
  tap.
- **The answer** (200): the result as § 6.2's item, and the job's `filled_count` and `item_count`,
  so the page moves "3 of 7 filled" and *Mark job done* without a reload; `meter_note` when the value
  was kept on the job only (§ 5.5).

### 5.5 A reading that names a meter (the shared path)

`meters.log_reading` is split into public functions that both callers use (CLAUDE-COMMON *DRY*;
CLAUDE.md § SMTW-Review, *Meter readings (S039)*):

| Function | What it does | Today's code it takes |
|---|---|---|
| `lock_node(cur, node_id, key)` | (1) the node FOR UPDATE through `load_node_for_user(…, for_update=True, key=key)`; 404, 403 at its site, 409 scrapped | `_lock_node`, renamed: one public name for the meter writes, the readings and PM (BR1-07) |
| `meter_in_force(cur, node_id, model_id, meter_type_id)` | the node's meter of that type in force (`_meters_of`), or None | `log_reading`'s `next(…)` |
| `reading_at_minute(cur, node_id, meter_type_id, taken_at)` | the active reading at that minute, or None | `log_reading`'s same-minute `count` |
| `write_reading(cur, node_id, meter, raw, taken_at, source)` | `validate_reading` (400), the same-minute rule (409 `SAME_MINUTE`), for a counter `counter_error` against `_neighbour` before and after (400 with its code), `_limit_state` (the meter's own limits), `insert_row` with `source`, the re-read row → `row` | the rest of `log_reading`'s body |
| `remove_reading_row(cur, node_id, reading)` | `reset_removal_error` (409 `RESET_HAS_LATER`), then the `removed_at` / `removed_by` update | `remove_reading`'s last part |

`log_reading` then reads: `lock_node(cur, node_id, "reading:log")` (the first statement, as
now), `meter_in_force` or 409 `NOT_ON_NODE`, `write_reading(…, source="manual")`. `remove_reading`
keeps its own 404 / `ALREADY_REMOVED` checks and calls `remove_reading_row`. The readings routes
answer exactly as before (`test_readings_api.py`, `test_meters_api.py` run unchanged).

**The PM item save, for a result with a meter and a value** (after the locks of § 5.7):

1. `meter = meter_in_force(cur, meter_equipment_id, locked_meter_node["model_id"], meter_type_id)`.
   None (the meter was removed from the model or the node since *Start*): the value is saved on the
   result only, `reading_id` stays as it is, and the answer carries `meter_note` (`NOT_LOGGED`).
   The job can still be finished (D9).
2. **The time** of the reading is the job's `started_at` (D6): the moment the technician was at the
   machine, so a job recorded on behalf two days later puts its reading two days back, between the
   right neighbours. The 7-day window is the start's (§ 5.3), not checked again (a job may stay open
   longer).
3. **The old reading:** when the result has a `reading_id` and the value or the reset mark changes
   (or the result becomes `na`), the old reading is read; **only when its `source` is `pm`** (the job
   logged it) and it is active, it is removed through `remove_reading_row` (a reset with later
   readings: 409 `RESET_HAS_LATER` on `value`, and nothing changes). The job owns the reading it
   logged, so `pm_job:work` removes it here, not `equipment:edit` (D8). Removed first, so the new one
   does not meet it at the same minute. A linked reading of another source (step 4: the operator's,
   `manual`) is never removed: the result lets go of it (`reading_id` NULL) and step 4 then meets it
   (BR1-03).
4. **The same minute:** `reading_at_minute` finds an active reading at `started_at`: with the same
   value and the same reset mark, the result names it (`reading_id`) and nothing is inserted (the
   technician also typed it on the evening sheet); with another value or mark: 409 `SAME_MINUTE_PM`
   on `value` (an engineer sorts it out on the Meters card).
5. `write_reading(cur, meter_equipment_id, meter, {value, is_reset, note: None}, started_at, "pm")`:
   a refused counter value raises its `ApiError` (field `value`, code `counter_lower` for a value
   lower than the reading before), the transaction rolls back, **the result is not saved**, and
   the page shows the refusal on the item (D4). With `counter_lower` the item offers the tick
   *Meter reset* (as the S040 sheet does on that code, `frontend/src/views/readings/ReadingsSheet.vue`); ticked and saved again, it sends `is_reset: true`.
6. The result's `reading_id` = the new reading's id, in the same `UPDATE` as the value.

A reading item with a meter answered `na` logs nothing (and removes its earlier `pm` reading, step 3).
A result without a meter logs nothing.

### 5.6 Mark job done (`POST /api/pm/jobs/<id>/done`)

Body `{done_at}`: `null` or absent = now (to the minute); else `parse_event_time`, to the minute,
`job_time_error(done_at, now, not_before=started_at)`. Then (the locks of § 5.7):

1. `state_error(state, MARK_DONE)`; `unfilled_count(results)` > 0 → 409 `not_all_filled(n, total)`.
2. **`done_meter`**, only when the plan has a meter trigger (`meter_type_id` set on the locked plan
   row): S095 § 5.2's rule at T = `done_at` on the plan's meter (`meter_equipment_id`,
   `meter_type_id`): `last_readings(cur, [meter_equipment_id], until=done_at)` for the type, else
   `first_reading_after(cur, meter_equipment_id, meter_type_id, done_at)`, else None. The raw value
   is stored: it is the next job's base (S097 § 5.3, the base value with its time `done_at`).
3. **`timeliness`** = `pm_schedule_core.timeliness(due_from_job(job), done_at.date(),
   done_meter_counted(done_meter, job["meter_offset"]))`: the due point and windows are the job's
   own copies (frozen at *Start*, D2), and the counted meter value adds the job's stored reset offset,
   as the list does (S097 § 5.4). That offset is frozen at *Start* too: a counter reset between
   *Start* and *Done* leaves it low, so a late job may read *On time* by meter. Rare; accepted and
   stated in Plan.MD's paragraph beside the changed-meter case (BR1-13).
4. `update_row(cur, "pm_jobs", job_id, {state: DONE, done_at, done_meter, timeliness}, actor())`:
   `open_plan_id` becomes NULL, so the plan has no open job.
5. The event `done`: `from_state` `in_progress`, `to_state` `done`, `occurred_at` `done_at`,
   `person_id` the performer.
6. `pm_jobs.settle_plan_job(cur, plan_id, node_lifecycle, now, actor())` (S097 § 5.5): the plan's
   next job is made at once if it already falls in its *Upcoming* window (rare: a job done very
   late), else by the daily run. The same rule as every plan save (S097 D5).

- **`needs_verification`** is not read: the job reaches `done` either way (D10).
- The answer is the job page's (§ 6.2), now read-only.
- **The plan's meter changed while the job was open** (an engineer's edit): `done_meter` reads the
  plan's meter now, which the next job counts from (right); `timeliness` then compares it with a
  `due_meter` of the old meter. Rare, accepted, stated in Plan.MD's paragraph.

### 5.7 Locks

The database runs REPEATABLE READ: a locking read sees the latest committed row and does not start
the snapshot; the first plain read does. Pool connections are autocommit (`db_helpers.transaction`'s
docstring), so a read before `transaction(conn)` is its own snapshot and ends with it. **S098's
rule:** every write route takes the plan (6e), then the job (6f), then any node lock, **before any
plain read** of its transaction (S097 § 5.7: "a job write takes its plan (6e) first, then the job").
So the reading's neighbour checks run on a snapshot that starts after the node lock, as in
`log_reading` (S039 § 5.3).

**The pre-read.** The routes name a job id, and the plan is locked before the job. The job's
`plan_id` and `equipment_id` never change (S097 § 5.2), nor do a result's copied `item_type`,
`meter_equipment_id` and `meter_type_id` (copied at *Start*, never updated). So each route reads them
**before** the transaction, plainly: `SELECT plan_id, equipment_id FROM pm_jobs WHERE id = %s` (and,
for an item, `SELECT item_type, meter_equipment_id, meter_type_id FROM pm_job_results WHERE id = %s
AND job_id = %s`); missing → 404. The precedent is `improvements._lock_action_for_documents` ("a
plain read of its improvement_id (it never changes; 404) → (6b) FOR UPDATE"); S098 puts the read
outside the transaction because a reading needs a fresh snapshot after its node lock.

**(6f) the PM job row**, new in `equipment.py`'s list after (6e): `SELECT * FROM pm_jobs WHERE id =
%s FOR UPDATE`, always right after its plan (6e), one job per transaction. The plan lock and the
node's shared lock are S097's statements `pm_jobs.LOCK_PLAN` and `pm_jobs.SHARE_NODE`, reused (BS1-02);
the job lock is a new `pm_work.py` constant.

**Start** (one `transaction`):

1. `SELECT * FROM pm_plans WHERE id = %s FOR UPDATE` (`LOCK_PLAN`) — (6e), exclusive.
2. `SELECT * FROM pm_jobs WHERE id = %s FOR UPDATE` — (6f), exclusive; the state from it.
3. `SELECT id, lifecycle FROM equipment WHERE id = %s LOCK IN SHARE MODE` (`SHARE_NODE`) with the job's
   `equipment_id` — (1) shared; the scrapped refusal from it (S097's order: (6e), then (1)).
4. Plain (the snapshot starts here): the access check (`load_node_for_user(cur, node_id,
   for_update=False, key="pm_job:work")`: its 404 is by `equipment:read`'s units (`_can_access`),
   and the route is safe because `require_perm("pm_job:work")` ran first and every holder holds
   `pm_job:read`; only `GET /api/pm/jobs/<id>` applies `accessible_unit_ids(cur, "pm_job:read")`,
   BR1-19), `person_at_site`, the
   plan's active items (every item write holds (6e), S096 § 5.7, so the read sees the newest).
5. The result inserts: shared foreign-key locks on the job (held), the plan item, the meter's node
   (the node or an ancestor) and the meter type. The job update and the event insert (the job, held;
   the performer's people row, shared).
6. Commit.

**An item** (one `transaction`):

1. (6e) the plan FOR UPDATE. 2. (6f) the job FOR UPDATE; the state from it.
3. For every save of a result that names a meter (a value or `na`; known from the pre-read, so
   also when only its old reading must be removed): `lock_node(cur, meter_equipment_id,
   "pm_job:work")` — (1) the meter's node FOR UPDATE (the node or an ancestor; the node the reading
   is on, as `log_reading` locks it). Its own plain access read follows at once and starts the
   snapshot.
4. Plain: the job's node access and `pm_job:work` at its site (when the meter is on an ancestor, the
   same root unit and site, S096 § 5.5); the result row (written only under (6f)); the meter type;
   then § 5.5: the meter in force, the old reading, the same minute, the neighbours.
5. Writes: the old reading's update (its row, exclusive), the reading insert (shared foreign-key
   locks: the node, held; the meter type), the result update (its row, exclusive; the new reading,
   held).
6. Commit.

**The performer** (`PUT /api/pm/jobs/<id>`): (6e) → (6f) → plain (access, `person_at_site`) → the
job update and the event insert (the people row, shared) → commit.

**Mark done:** (6e) → (6f) → (1) the job's node LOCK IN SHARE MODE (its `lifecycle` for
`settle_plan_job`) → plain (access, the results, the readings for `done_meter`) → the job update,
the event, then `settle_plan_job` (S097 § 5.7: plain reads, then for a new job (6) the `PM:` counter
and the inserts) → commit.

**The job page and the lists:** plain, no lock.

**No deadlock cycle** (against the LOCK ORDER notes of `equipment.py`, `meters.py`, `pm_plans.py`,
`pm_jobs.py`):

- *(6e) then (6f):* every PM write that touches a job takes its plan first: S097's run and plan save
  (they update a job only while it is `due`), and every S098 route. Two writers of one plan queue on
  (6e); no path holds a job and waits on its plan.
- *The node after (6e)/(6f):* S098's routes take a node lock (shared at Start and done, exclusive at
  an item) only after their plan and job. The node writers (`equipment.py`, `meters.py`'s
  `log_reading` and the meter writes, the scrap) hold the node and never wait on a plan or a job row,
  so a PM write waits behind them and finishes. Two PM writes on jobs of different plans whose
  meters share a node queue on that node; neither holds what the other waits for. A plan save or the
  run (S097) holds a node shared and waits on nothing S098 holds (they take their own plan only).
- *The scrap and Start:* the scrap holds the node and its parts FOR UPDATE and counts started jobs
  plainly (§ 5.8); Start waits on the node's shared lock behind it, then reads `scrapped` from its
  locked row → 409. **One accepted case**, as S096 § 5.7 states it for plans: Start holds a part (1)
  shared and its result insert then takes the machine's row shared through the meter foreign key,
  while a scrap of the machine holds the machine and waits for the part: InnoDB rolls one back
  (1213, a plain 500); a retry gives the right answer.
- *`meter_readings` rows:* the old reading's update locks that row; only `remove_reading` and this
  path update a reading, both under the reading's node (1) exclusive, so they serialise there.
- *(6) the `PM:` counter* is taken only inside `settle_plan_job`, last before its inserts (S097).
  Mark done holds (6e), (6f), the node shared, then (6): a run on another plan holds that plan, its
  node shared and maybe (6), and never waits on Mark done's plan or job.

The coder writes this into `pm_work.py`'s LOCK ORDER note, adds "(6f) the PM job row (pm_jobs,
S098): always right after its plan (6e)" to `equipment.py`'s list, and adds to its (6e) bullet:
"S098: start, an item, the performer and done take (6e), then (6f), then a node: Start and done its
node LOCK IN SHARE MODE, an item with a meter the meter's node FOR UPDATE through
meters.lock_node; all before any plain read; the job's plan_id is read before the
transaction (it never changes)." `meters.py`'s docstring gains: "A PM job's reading item (S098)
takes the same path: (6e), (6f), then (1) the meter's node, before any plain read; write_reading
does the checks and the insert for both callers."

### 5.8 Scrapping a machine with a started PM job

`equipment._check_no_started_pm_jobs(cur, node_ids)`, called next to `_check_no_open_tickets` with
the same `node_ids` (the node and its parts, locked): `SELECT COUNT(*) AS n FROM pm_jobs WHERE state
= 'in_progress' AND equipment_id IN (…)`; > 0 → 409 "Finish its PM jobs first (1 in progress)" on
`lifecycle` (`pm_work_core.finish_jobs_first(n)`, the shape of `tickets_core.close_tickets_first`).
A plain count is enough for the reason `_check_no_open_tickets`'s docstring gives: the snapshot
starts after the node's lock, and Start takes the node lock (shared) before it writes. A `due` job
does not block: S097 cancels it (`NODE_SCRAPPED_REMARK`) in the next run or plan save.

### 5.9 The PM list (S097's, changed)

- **Tabs:** *Due*, *Upcoming*, *Done* (`TABS`). `tab_of(state, standing_state)`: `in_progress` →
  `TAB_DUE` whatever the standing (work begun belongs to now); else S097's rule (DUE and OVERDUE →
  *Due*; NOT_YET and UPCOMING → *Upcoming*).
- **Order on *Due*** (`list_order`): the started jobs first, then S097's order (OVERDUE, DUE, then
  the due date, then the serial).
- **A row** (`PmJobRow.vue`, the S097 row as it is, keeping its class `job-row` and its `data-equipment` attribute, which `pm-jobs.spec.js` finds rows by; BS1-08) opens `/pm/jobs/<id>`. A started job shows the
  badge *In progress* (`text-bg-primary`) before its standing badge, and the small line names the
  performer: "In progress · Kannan". A done job (the *Done* tab) shows *Done* (`text-bg-success`)
  and *On time* (`text-bg-light border`) or *Late* (`text-bg-danger`), the done date ("Done
  29-10-2026"), the machine, the plan and "by Kannan".
- **The count line:** on *Due* "4 due · 1 overdue · 2 in progress" (a zero part left out); on *Done*
  "12 done" (the total). Both through `pmLabels.countText(tab, counts)`, which gains the *in progress* part and the *Done* tab (BS1-04).
- ***Done* tab:** the house pager (`PagerBar.vue`, as `TicketsView.vue`), newest first; the filters
  *Unit* and *Assigned to me* apply. Empty: "No PM jobs are done yet." (with a filter: S097's "No PM
  jobs match these filters.").
- ***Assigned to me*** now means "assigned to me, or performed by me": a job I started for another
  assignee is mine to finish (D11).

### 5.10 The job page (`PmJobView.vue`)

Route `/pm/jobs/<id>` (`pm-job`, title "PM job"). Load `GET /api/pm/jobs/<id>`; for `can_start` or
`can_work` also `GET /api/tickets/people?equipment_id=<node>` (`tickets.list_people`,
`backend/tickets.py:789`, under `require_perm("ticket:raise")`; `?equipment_id=` goes through
`_picker_anchor` → `load_node_for_user(…, key="ticket:raise")`; its people come from
`people_at_site` (`backend/tickets.py:753`) with `role` and `vendor_name`, which `personLabel` reads;
BS1-06; every `pm_job:work` holder holds `ticket:raise`). A 404: "PM job not found, or not at your units." with *Back to PM*.

**Header** (mock-up 03): the badges (`jobBadges(job)`: *In progress* / *Done* with *On time* or
*Late* / the S097 standing badge with `daysPastText`), the serial as the heading (`h1`, `h4`
class), then "HP003 — Hydraulic press 3" (a link to the equipment page), then "Monthly hydraulic
check · SMTW.MCC2 · due 24-10-2026 or at 2,090 h" (`dueText`; the plan's title links to the plan
page).

**Before *Start*** (state `due`, `can_start`): a card *Start job*:
1. **Performed by** — a select of the site's people by name, through S096's
   `pmLabels.personLabel` ("Kannan (Technician)", "Ravi (Technician) · Atlas Copco", "Ramesh
   (Operator)"), my own person first selected when I am in the
   list, else none selected and the help "Choose who did the work.".
2. **Started** — `frontend/src/views/tickets/EventFields.vue` with `withRemark: false`, `timeLabel: "Started"`, `idPrefix: "pm-start"` (required, BS1-07): *Now* ticked;
   unticked, a time up to 7 days back (the field's own "n days ago" hint).
3. *Start job* (`btn-primary`, full width on a phone, at least 48 px high). While it runs:
   "Starting…", disabled. A refusal shows beside its field.
Under the card, the items as they are on the plan now, read-only, under the line "These are the
plan's items now. Start the job to fill them." For `can_start` false (a reader, or IT admin) the
card is left out and the line reads "These are the plan's items now." A due job whose machine was
scrapped after the job was made (`equipment.lifecycle` `scrapped`; S097 cancels it in the next run
or plan save): no card, and the line "This machine is scrapped. The job cannot be started." (BR1-09).

**In progress** (`can_work`): a card with **Performed by** (the same select; a change saves at once
through `PUT /api/pm/jobs/<id>`, a small "Saved" after it) and **Started** as text ("27-10-2026
09:10"). Then the count "3 of 7 filled" (`filledText`), then the items, then *Mark job done*.

**An item row** (`list-group-item`), with its number and text in bold, the limits after it in small
text (`limits_text`: "30–60 °C", "· logs Oil temperature · HP003"), the help text under it in small
text:
- **Check:** `btn-group w-100` of *OK* (`btn-outline-success`, `btn-success` when chosen), *Not OK*
  (danger), *NA* (secondary), each `tap-target`, at least 48 px high, `aria-pressed` on the chosen
  one. A tap on *OK* or *NA* saves at once. A tap on *Not OK* opens the remark field under the
  buttons (label "What is wrong?") with *Save* beside it; *Save* sends `not_ok` with the remark. A
  saved *Not OK* row has a light red background (`list-group-item-danger`) and shows its remark.
- **Task:** *Done* / *Not done* the same way; *Not done* asks "Why was it not done?".
- **Reading:** a number input (`inputmode="decimal"`, the unit after it as `input-group-text`, the
  meter type's unit or the item's), *Save* beside it, and *NA* under it (asks "Why is there no
  reading?"). While typing, `limitFlag(raw, min, max)` shows *High* or *Low* (`text-bg-danger`) beside
  the label and outlines the input red; a value inside the limits shows nothing. Enter or *Save*
  saves. A saved value out of limits keeps the badge and the red row. Under an item with a meter:
  "Also logged as an Oil temperature reading of HP003." (the mock-up's line); after a `meter_note`
  that note instead.
- **Saving state per item:** while a save runs, the tapped control shows "Saving…" and the row's
  controls are disabled; then a small "Saved" with a check icon. A refusal (400, 409) shows its
  message under the item in red (`invalid-feedback d-block`), the typed value kept; with the code
  `counter_lower` the tick *Meter reset* appears under the input. **A failed save with no answer**
  (`err.status` 0, `api.js`'s network case, or 5xx): "Not saved: <message>. Tap again." under the item;
  the buttons show the last saved choice, the input keeps what was typed. So a network drop costs at
  most the item being saved, and the row says which one.
- The page holds no unsaved state other than a typed, unsaved value or remark: leaving the page
  loses only that (no route-leave guard, as S096 § 9 A5).

**Mark job done:** a full-width `btn-success` (48 px) after the items, not fixed to the screen (D13).
Disabled while any item is unfilled, with the reason under it: "Fill all 7 items first. Your
entries are saved as you go." (the mock-up's line; `filledText`). Enabled, a tap opens
`PmJobDoneDialog.vue` (`FormModal.vue` through `useFormModal`, title *Mark job done*): one field,
**Done** (`EventFields.vue`, `timeLabel: "Done"`, `withRemark: false`, `idPrefix: "pm-done"`, *Now* ticked), the line
"Started 27-10-2026 09:10 · 7 of 7 filled", under the *Done* field the consequence "The job can
no longer be changed." (style B: a confirmation states it; R03.5's send back is not built; BR1-17),
and the save button *Mark job done*. Call contract
(settings: *Self-check, repo items* (13)): `useFormModal({ path: "/api/pm/jobs/<id>/done", blank:
() => ({ done_at: null }), toBody: (form) => ({ done_at: form.done_at }), afterSave, label: () =>
serial })`; `blank()` takes no seed and `openCreate()` is called without one; the dialog's save
calls `send(() => apiPost(path, toBody(form)))`. `afterSave` emits `done(job)`; the page shows the
answer (FormModal's `closed` event hands the record over after the fade, the S077 rule). A refusal
(`done_at`) shows beside the field; `not_all_filled` (another person's change) closes nothing and
shows above the field.

**Done** (read-only for everyone): the header badges *Done* and *On time* / *Late*; a card
"Performed by Kannan · Started 27-10-2026 09:10 · Done 27-10-2026 11:05"; each item with its result
as text: a badge *OK* (`text-bg-success`), *Not OK* (`text-bg-danger`), *NA* (`text-bg-secondary`),
*Done*, *Not done*, or the value with its unit and *High* / *Low*; the remark under it; "Filled by
Kannan, 27-10-2026 09:40" in small text.

**History** (every state): a card *History* with the job's events, oldest first (`PM_EVENT_LABELS`):
"Created", "Due point changed", "Assignee changed", "Cancelled", "Started", "Performed by changed",
"Done" (S097's and S098's events), each with its time, the person where it names one, and who
recorded it ("by Priya"), as the ticket timeline's lines. A line recorded by the daily run reads "by
the daily PM run" (`created_by` equals `pm_jobs_core.RUN_ACTOR`, BS1-04).

**Read-only states:** a reader without `pm_job:work` at the site sees every state as text, no
buttons; IT admin the same. A cancelled job: the badge *Cancelled* and its remark, no items list
when it was never started (the plan's items are not shown for a cancelled job).

**The equipment page's PM card** (`PmPlansCard.vue`, S097 § 5.10): an open job whose `state` is
`in_progress` shows *In progress* before its standing badge (`jobBadges`). S097's `schedule.open_job`
gains `state` (§ 6.3).

### 5.11 Me › Open work

- For a holder of `pm_job:read` with a Team record, on page 1 of *Open work*, above the
  countermeasures: `GET /api/pm/jobs?tab=due&assigned=me` (the started jobs, then the overdue and
  due ones, assigned to me or performed by me). Heading "PM jobs (n)" (`data-testid="me-pm-jobs"`),
  then the rows (`PmJobRow.vue`), then the countermeasures and the tickets as today; the *Tickets*
  heading shows when either section above has rows.
- Upcoming jobs stay on the *PM* list only: *Open work* is what to do now.
- No rows: no section (the tickets' empty text stays as it is). A failed PM read fails the page's
  load as the other reads do (one `Promise.all`), with *Retry*.
- The order of sections: PM jobs first, because a due PM job has a date; the countermeasures and
  tickets keep theirs (D11).

### 5.12 The database down

Every new route goes through `get_db()`: 503 while the database is down or missing (§ Yantra
Specifics, *DB may not exist*). The job page shows "PM job could not be loaded: <message>" with
*Retry*; an item save shows "Not saved: … Tap again." No background task, no alert, no file.

## 6. API

All under `pm_work_bp` at `/api/pm`, ids `<int:…>`.

| Route | Key (decorator) | Body | Answer |
|---|---|---|---|
| `GET /api/pm/jobs/<id>` | `pm_job:read` | — | 200 the job (§ 6.2); 404 |
| `POST /api/pm/jobs/<id>/start` | `pm_job:work` | `{performed_by_id, started_at}` | 200 the job; 400, 403, 404, 409 |
| `PUT /api/pm/jobs/<id>/results/<result_id>` | `pm_job:work` | `{outcome, value, remark, is_reset}` | 200 `{item, filled_count, item_count, meter_note}`; 400, 403, 404, 409 |
| `PUT /api/pm/jobs/<id>` | `pm_job:work` | `{performed_by_id}` | 200 the job; 400, 403, 404, 409 |
| `POST /api/pm/jobs/<id>/done` | `pm_job:work` | `{done_at}` | 200 the job; 400, 403, 404, 409 |
| `GET /api/pm/jobs?tab=done` (S097's route) | `pm_job:read` | `page`, `per_page`, `unit_id`, `assigned` | 200 § 6.3 |

### 6.1 Common rules

- 401 without identity (before any route); 403 without the key anywhere (`require_perm`); 404 for a
  missing job and for one outside the user's `pm_job:read` units (the same answer, nothing
  revealed); a result id of another job: 404.
- A body that is not an object: `clean_body`'s 400. Times `YYYY-MM-DDTHH:MM`, IST, no offset
  (`parse_event_time`).
- `PUT /api/pm/jobs/<id>` with no `performed_by_id`, or the same person: no write, 200 the job.
  Another person: the update and the event `performer_changed` (`person_id` the new one). A
  `performed_by_id` that is not an integer ≥ 1 (a boolean, a text, `null`, 0): 400
  `PERFORMED_BY_NEEDED` on `performed_by_id`, as at *Start* (BR1-15); a person not at the site: 400
  `PERSON_AT_SITE`.

### 6.2 The job

```
{id, serial, state, standing: {state, trigger, no_reading} | null, due_on, due_meter, days_past,
 equipment: {id, code, name, lifecycle}, plan: {id, title, active, needs_verification},
 unit: {id, full_code}, site_code, assignee: {id, name} | null,
 performed_by: {id, name} | null, started_at, done_at, done_meter, timeliness,
 meter: {…as S097 § 6.1} | null,
 items: [{id | null, plan_item_id, position, item_type, text, help_text, unit,
          meter: {equipment_id, code, meter_type: {id, name, unit, kind, decimals}} | null,
          min_value, max_value, limits_text,
          outcome, value, limit_state, remark, logged, filled_at, filled_by_name}],
 filled_count, item_count,
 events: [{event, occurred_at, from_state, to_state, person: {id, name} | null, due_on, due_meter,
           remark, created_by_name}],
 can_start, can_work, created_at}
```

- `standing` is S097's live judgement for an open job (`job_state` over `due_from_job` and the
  meter's latest reading plus `meter_offset`), null for a done, cancelled or skipped job.
- `items`: for a `due` job, the plan's active items now (`id` null, every result field null); for a
  `cancelled` or `skipped` job that never started, `[]`; else the job's results by `position`.
  `logged` is true when `reading_id` is set and that reading is active. `photo` is not answered (D12).
- `can_start` = `has_perm_at("pm_job:work", site)`, state `due` and the node not scrapped (BR1-09);
  `can_work` = the key and state `in_progress`. `equipment` carries `lifecycle` too, for the
  scrapped line.
- An item's and the job's `meter.meter_type` is built by `pm_jobs.meter_type_out(row)`, the one copy
  of that shape (BS1-03).
- Numbers as strings through `meters_core.format_number`; dates `YYYY-MM-DD`, times as `row_to_dict`
  gives them. Names of `filled_by` and `created_by` through `people.username`, the login when no person
  matches (S096 § 6.1's rule); `pm_generate` stays as it is (the page words it).

### 6.3 S097's list and card, changed

- `GET /api/pm/jobs`: `tab` takes `done` (`enum_arg` over the new `TABS`); the 400 text becomes
  "tab must be one of: due, upcoming, done". For *Due* and *Upcoming* as S097, with `tab_of(state,
  standing)`, through `_JOB_SELECT` and `jobs_out` (open jobs only). For *Done*: `_DONE_SELECT`,
  the jobs in `BASE_STATES` (`done`, `verified`) at the user's units, the same filters, `ORDER BY
  done_at DESC, id DESC`, paged by `page` (`int_arg("page", 1, 1, MAX_PAGE)`) and `per_page`
  (`int_arg("per_page", DEFAULT_PER_PAGE, 1, MAX_PER_PAGE)`), with a `COUNT(*)` for `total`; each row
  through `_job_item(row, None, None)` (no standing, no sort; BS1-01); answer `{items, counts, total,
  page, per_page}`, `counts` from the open jobs as on the other tabs.
- `assigned=me`: `(j.assignee_id = %s OR j.performed_by_id = %s)` with `current_person_id`.
- Each item gains `performed_by: {id, name} | null`, `started_at`, `done_at`, `timeliness`;
  `counts` gains `in_progress` (open jobs in that state).
- The card's `schedule.open_job` gains `state`.

## 7. Design decisions

- **D1. Results are copied at *Start*, not at creation.** The roadmap's rule: a job not started
  follows plan edits (the engineer may still correct an item); a started one keeps its copy (Plan
  § 4.3a). Rejected: copying at creation (a plan fix made before anyone started would miss the job
  already listed); no copy, results pointing at plan items (a plan edit would rewrite a done job's
  text, against ISO 9001 § 7.5.3).
- **D2. A started job's due point, windows and assignee are frozen.** S097 refreshes only a `due`
  job (its `decide` leaves `in_progress` alone); S098 keeps it so and tests it. The job is judged
  at *Mark done* against the point it carried when work began; a plan edit after that is the next
  job's rhythm. A plan deactivated while a job is in progress leaves the job open, to be finished:
  the work began and its record should be complete. Rejected: cancelling a started job on
  deactivation (results thrown away); refreshing its due point (the judgement would move under the
  technician).
- **D3. Any `pm_job:work` holder at the site works any job**, as `ticket:work`; *Performed by*
  records who did it. Rejected: only the assignee or the performer (a job stalls when the assignee is
  away; the plant has few technicians).
- **D4. A refused meter value saves nothing.** The item and its meter reading are one transaction:
  if the counter check refuses the value, the result is not saved and the item shows the refusal.
  S039's rule exists so a wrong counter value never enters the history; a PM value the meter refuses
  is the same typo. The *Meter reset* tick covers a real reset; a wrong earlier reading is removed by
  an engineer on the Meters card (the refusal names its time). Rejected: saving the value on the job
  with the error shown (the job and the meter would disagree, and the next job's base, `done_meter`,
  would read a different value than the job shows).
- **D5. *Started* and *Done* up to 7 days back for everyone, admin included.** The readings' window
  (S039 decision 8): the reading is logged at *Started*. Rejected: S028's `backdate_days` (3 years
  while the backlog window is open, until 30-11-2026: a PM reading three years back would enter the
  meter history unchecked by the readings' own window).
- **D6. The reading's time is the job's *Started* time, and *Started* is fixed at *Start*.** One time
  per visit, which a job recorded on behalf two days later gets right; the counter is checked between
  the right neighbours. Fixed, so the readings already logged and the job never disagree. Rejected:
  the time of each item's save (a back-dated job would log today's time); an editable *Started*
  (its logged readings would keep the old time).
- **D7. A filled item can be changed while the job is in progress, never emptied.** A wrong tap is
  fixed by another tap; *Mark job done* needs every item filled anyway. Rejected: a *Clear* button
  (one more control on a crowded phone row, no use case).
- **D8. The job replaces its own meter reading** when its value changes, by removing it (kept as a
  removed row, who and when) and logging the new one, under `pm_job:work`. The reading belongs to
  the job: only a reading of source `pm` is removed; a linked reading someone else logged is never
  touched (BR1-03). Rejected: refusing a change once logged (a technician who mistyped would need an
  engineer); leaving two readings (the history would hold both).
- **D9. A meter gone since *Start* keeps the value on the job only**, with the note on the item.
  The job can be finished; the plan still names a meter the engineer must fix. Rejected: refusing
  (a job that can never be finished).
- **D10. Every job ends at `done` in S098, `needs_verification` or not.** R03.5 adds `verified`, the
  *To verify* tab and *Send back*; a done job then waits there. `done` is a base state (S097
  `BASE_STATES`), so the next job counts from it now. Rejected: holding jobs that need verification
  at `done` without a next job until R03.5 (the plan would stall for weeks).
- **D11. *Open work* shows my due, overdue and started PM jobs; "mine" is the assignee or the
  performer.** A job I started for someone else is mine to finish. Upcoming jobs are on the *PM*
  list. Rejected: assignee only (a started job vanishes from the person doing it); upcoming jobs too
  (the page fills with next week's work).
- **D12. The photo setting is copied, not shown.** R03.6 builds photos; a "photo needed" line now
  would ask for something nobody can do. The column is copied so R03.6 needs no migration of the
  results. Rejected: showing the setting (confusing); not copying it (R03.6 would read the plan's
  current setting for a started job).
- **D13. *Mark job done* sits after the items, not fixed to the screen.** The phones' bottom nav is
  fixed already; a second fixed bar covers the last item on a short phone and differs between
  WebKit and Chromium. The count "3 of 7 filled" at the top says how far it is. Rejected: the
  mock-up's fixed bar.
- **D14. A new module `pm_work.py` beside S097's `pm_jobs.py`.** S097's module makes and lists jobs
  (with the daily run); S098's does the work on one job. Both are blueprints at `/api/pm`;
  `pm_work.py` imports `pm_jobs.py`, never the other way. Rejected: one module (S097's would pass
  1,000 lines).
- **D15. Scrapping waits for started PM jobs**, as for open tickets (S017 user decision 6). A
  scrapped record is read-only, so a started job on it could never be finished. Rejected: cancelling
  the started job at the scrap (work done would be marked cancelled); letting the job finish on a
  scrapped node (the one exception to "scrapped is read-only").

## 8. Tests and acceptance

### 8.1 Migration (`backend/tests/test_migration_v53.py`)

- A fresh database: `pm_job_results` with `uq_pm_job_results_item`, `uq_pm_job_results_position` and
  its five foreign keys; `pm_jobs` with `performed_by_id`, `started_at`, `ix_pm_jobs_performer`,
  `fk_pm_jobs_performer`, `chk_pm_jobs_started`.
- A v52 database with a plan, a `due` job and a `cancelled` job migrates to v53; both jobs are
  kept, with the new columns NULL.
- The ENUMs: `item_type` equals `pm_plans_core.ITEM_TYPES`, `photo` `PHOTO_SETTINGS`, `outcome`
  `pm_work_core.OUTCOMES`, `limit_state` `(LOW, HIGH)` (`information_schema.COLUMNS.COLUMN_TYPE`).
- The CHECKs refuse (4025): an `in_progress` job without `started_at`; a `performed_by_id` without
  `started_at`; `done_at` before `started_at`; a check result with a value; a task with `ok`; a
  reading with `na` and a value; `limit_state` without a value; `reading_id` without a meter;
  `filled_at` on an empty result; `outcome` without `filled_at`. They pass: a check `ok` filled, a
  reading value with `high`, a reading `na`.
- A second result of one plan item on one job → 1062. A re-run of v53 changes nothing (`_schema()`
  equal).

### 8.2 Backend

**Core** (`test_pm_work_core.py`, no database, written first):
- `result_rows`: every copied column, results None; the order kept.
- `validate_result`: each row of § 5.4's table, both ways; the remark rules (needed for `not_ok`,
  `not_done`, a reading's `na`; accepted with `ok`; empty → None; 501 characters; not text); a
  reading value through `validate_reading` (decimals of a 1-decimal meter, a negative free value, a
  negative counter value refused); `is_reset` on a gauge → "Only a counter can be reset" on
  `is_reset`, not a boolean → "Meter reset must be true or false" (`validate_reading`'s texts);
  `limit_state` high, low, inside, a limit equal (inside), no limits.
- `result_changes`: nothing changed → `{}`; each field alone; the same value with `is_reset` true
  against a linked reading whose `is_reset` is false → a change. `is_filled`, `unfilled_count`.
- `state_error`: every cell of § 5.2's table, `(DUE_STATE, FILL)` → `START_FIRST` included.
- `job_time_error`: now; 7 days back exactly (allowed); 7 days and 1 minute (`TIME_TOO_OLD`); 6
  minutes ahead (`EVENT_TIME_FUTURE`); `not_before` equal (allowed) and one minute before
  (`DONE_BEFORE_START` with the time "27-10-2026 09:10").
- `done_meter_counted`: None → None; 1,280 + 1,200 → 2,480. `finish_jobs_first(1)`.

**The API** (`test_pm_work_api.py`; each test its own site, unit, machine, meter type and plan, the
plan through `POST /api/pm/plans` as an engineer with a past seed so S097 makes the job at the save;
people by `user_at_sites`):
- **The page:** a technician at the unit reads a `due` job (200, the plan's items with `id` null,
  `can_start` true); an operator reads it (`can_start` false); IT admin reads it (`can_start`
  false); a technician of another site: 404; the storekeeper: 403; a missing id: 404.
- **Start:** as the technician, performer himself, `started_at` null → 200, state `in_progress`,
  `started_at` the minute, one result per active item in order, an inactive item left out, the
  event `started`; the plan's assignee unchanged. Recorded on behalf: performer an operator without
  a login at the site, `started_at` 2 days back → 200 and both stored. Refusals: no performer
  (`PERFORMED_BY_NEEDED`); a person of another site (`PERSON_AT_SITE`); 8 days back (`TIME_TOO_OLD`);
  10 minutes ahead; a second Start (`ALREADY_STARTED`); IT admin and the operator → 403 (key not
  held); a node scrapped after the job was made (row updated in the test) → 409 `SCRAPPED_MESSAGE`.
- **Items:** a check `ok` → 200, `filled_count` 1, `filled_by` the user; the same body again → 200
  and no change of `filled_at` (idempotent); `not_ok` without a remark → 400 `remark`; with one →
  200; a task `not_done` likewise; a reading 212 with max 200 → `limit_state` `high`; `na` without a
  remark → 400; a value on a check → 400 `outcome`; a result id of another job → 404; a `PUT` on a
  `due` job with any result id → 404 (no result row yet, BR1-01); on a done job → 409 `JOB_DONE`;
  by an operator → 403. `START_FIRST` through the API: the performer `PUT` and *Mark done* on a
  `due` job → 409 "Start the job first.".
- **Readings** (a counter meter *Run hours* on the machine with a reading 1,260 at `started_at` − 1
  hour, by API): a reading item of that meter with 1,270 → 200, a `meter_readings` row with source
  `pm`, `taken_at` = `started_at`, `logged` true; the readings list of the meter shows it; 1,200 → 400
  `value` with code `counter_lower`, the result **not** saved and no reading written; 1,200 with
  `is_reset` true → 200 and a reset reading; a change from 1,270 to 1,275 → the 1,270 reading removed
  (`removed_by` the user) and 1,275 logged; then `na` with a remark → the 1,275 reading removed; a
  gauge item of *Oil temperature* with item limits 30–60 and meter limits 20–80: 70 → the result
  `high`, the meter reading's `limit_state` NULL (inside the meter's own limits, S096 A6); the same
  minute with the same value already logged by the operator → linked, no second row; then a change
  of the value → the operator's `manual` reading is **not** removed and the save is 409
  `SAME_MINUTE_PM` (BR1-03); a same-minute reading with another value → 409 `SAME_MINUTE_PM`; the
  meter removed from the node after *Start* → 200 with `meter_note`, no reading. **The lock and the
  snapshot**, modelled on `test_readings_api.py`'s
  `test_two_writers_on_one_node_serialise_and_the_second_sees_the_first` (BR1-18): a second
  connection holds the machine's row `FOR UPDATE`, inserts a Run hours reading of 1,300 one minute
  before `started_at`, and commits; the PM save of 1,280, sent meanwhile, waits for
  the lock and is then refused `counter_lower` against the 1,300 it could not have seen without
  the lock and the fresh snapshot.
- **Performer:** a change → 200 and the event `performer_changed`; the same person → no event;
  `performed_by_id` `true`, `"7"` or `null` → 400 `PERFORMED_BY_NEEDED`; a person of another site →
  400 `PERSON_AT_SITE`.
- **The clock:** `pm_jobs._now` monkeypatched in a test fixes the time of *Start* and *Done* too
  (`pm_work.py` calls it through the module, BR1-08).
- **Done:** with one item unfilled → 409 "Fill every item first: 1 of 3 are not filled."; all filled →
  200, `done`, `done_at` now, `open_plan_id` NULL, the event `done`; `done_at` before `started_at` →
  400 `DONE_BEFORE_START`; a meter plan: `done_meter` the reading at or before `done_at` (the PM
  reading of 1,270), `timeliness` `on_time` inside the window and `late` past it (S095's figures); a
  second Done → 409 `JOB_DONE`; the plan's next job: none at once (a monthly plan just done);
  the daily run later makes it from `done_at` (S097's `generate` called in the test with `_now`
  fixed 28 days on).
- **A started job and S097** (D2): after *Start*, a plan `PUT` that changes the interval, the
  assignee and the items leaves the job's `due_on`, `assignee_id` and results unchanged and writes
  no job event; `PUT {active: false}` leaves it `in_progress` (not cancelled), and it can be marked
  done; `pm_generate` run twice leaves it as it is.
- **The database down** (`db_down`): `GET /api/pm/jobs/<id>` and `POST …/start` → 503.

### 8.3 Existing tests that change or run again

- `backend/tests/test_rbac.py`: `test_role_matrix` — `pm_job:work` joins the rows of the technician,
  engineer and manager; not the operator, supervisor, storekeeper or IT admin; the comment above the
  rows gains "S098: pm_job:work to the technician (so the engineer and manager); R03.12 widens it to
  the operator". New `test_pm_job_work_key`: its holders are exactly those three roles
  (`compute_permissions` over `ROLES`), it is in `SITE_SCOPED`, and every holder also holds
  `pm_job:read`.
- `backend/tests/test_pm_jobs_api.py` (S097's): `tab=done` → 400 becomes 200 with the done job of a
  test; `tab=nonsense` → 400 "tab must be one of: due, upcoming, done"; an in-progress upcoming job is
  on *Due*; `assigned=me` finds a job I perform for another assignee; `counts.in_progress`; the
  *Done* tab's paging (`per_page=1`, two done jobs → `total` 2, one item). The coder names every
  changed line.
- `backend/tests/test_pm_jobs_core.py` (S097's): `tab_of` takes `(state, standing)`: every
  standing with `due`, and `in_progress` with each standing → `TAB_DUE` (`test_tab_of` calls
  `tab_of(state)` today); `list_order` puts a started job before an overdue one, and the items of
  `test_list_order` gain a `state` (BS1-04).
- `backend/tests/test_pm_generate.py` (S097's): its "an `in_progress` job (row inserted): left" stays
  green unchanged (S098's rows now need `started_at` and `performed_by_id` by `chk_pm_jobs_started`:
  the coder adds both to that inserted row).
- `backend/tests/test_equipment_api.py`: new `test_scrapping_with_a_started_pm_job_is_409` beside
  `test_scrapping_with_live_parts_is_409`; a `due` job does not block.
- `backend/tests/test_readings_api.py`, `test_meters_api.py`: unchanged, green after the refactor of
  § 5.5 (the readings answers do not change).
- `backend/tests/conftest.py`: `_TABLES` gains `pm_job_results` first.
- `backend/tests/test_modules.py` (`LATEST_VERSION`), `test_migration_squash_v41.py` (the later
  versions, S096 BR1-01), `test_migration_v51.py`, `test_migration_v52.py`: green at 53. The
  migration tests filter `_MIGRATIONS` to their own version (`test_migration_v51.py`'s
  `V51 = [m … if m[0] <= 51]`), so S097's v52 tests never meet `chk_pm_jobs_started` (BR1-20);
  `test_pm_generate.py` (above) runs at the latest version and needs the two columns.
- `test_schema_docs_shell.py`: green once `tooling\schema-docs.bat write` has run.
- `tooling/tests/test_line_width.py`: every new and changed `.py` line at most 120 characters.
- `frontend/tests/pmLabels.test.js`: `limitFlag` ("212" over 200 → "high"; "29.9" under 30 → "low";
  "" → null; "abc" → null; no limits → null; equal → null), `filledText(3, 7)` → "3 of 7 filled",
  `jobBadges` for in progress, done on time, done late, due overdue; `resultBody` for each type.
- `frontend/e2e/pm-jobs.spec.js` (S097's): `S097: a plan saved past due shows its job as Overdue on
  the PM list` — its last three lines (`row.click()`, the URL `/equipment/pm/<plan.id>`, the heading
  "S097 overdue plan") become: the URL `/pm/jobs/<job id>` and the job's serial as the heading
  (BS1-08); its title stays. Its row locator `.job-row[data-equipment="<code>"]` keeps working,
  since `PmJobRow.vue` keeps the class and the attribute. Every test that reads the
  *Due* tab's rows stays true (a due job is unchanged). The coder names each changed line.
- `frontend/e2e/me.spec.js`: the S031 and S071 tests stay green (the PM section shows only with PM
  jobs; their users have none). `S031: the three tabs fit the screen width` unchanged.
- `frontend/e2e/pm-plans.spec.js` (S096's), `equipment.spec.js`: green (the card's badge changes only
  for a started job).

### 8.4 Automated (e2e)

**`frontend/e2e/pm-job.spec.js`** (new). Set-up by API in the spec: each test makes its machine with
`meterMachine(testInfo, tag, { unit: "SMTW.MCC2", modelMeters: [["Run hours", {}], ["Oil
temperature", { min_value: "20", max_value: "80" }]] })` (`frontend/e2e/support/meters.js`), a plan by
`POST /api/pm/plans` as the engineer (`apiAs`) with three items (a Check "No oil leaks at the
cylinder seals", a Task "Grease the main bearing", a Reading "Power-pack oil temperature" 30–60 °C
without a meter unless the test says), every 10 days, last done 20 days ago (so S097 makes the job
at the save, *Overdue*), the technician as assignee (`personId("technician")`). Readings by
`logByApi`. Each test finds its own job by the machine's code. Untagged unless marked.

- **important** `S098: a technician starts a due job, fills each item and marks it done` — as the
  technician: *PM*, the row, the job page shows `"Start job"` and the plan's three items read-only;
  *Start job* with *Performed by* preset to the technician and *Now*; `"0 of 3 filled"`; *OK* on
  the check, *Done* on the task, 48.5 and *Save* on the reading; `"3 of 3 filled"`; *Mark job done*
  → the dialog (`expectDialogFits`), *Mark job done* → the badges `"Done"` and `"Late"` (due 10 days
  ago, grace 1), the history lines `"Started"` and `"Done"`; the *PM* list's *Done* tab lists the
  serial.
- **important** `S098: each item is saved as it is filled; a reload keeps them` — start, fill two
  items, reload: both still chosen, `"2 of 3 filled"`, *Mark job done* disabled with `"Fill all 3
  items first. Your entries are saved as you go."`.
- **important** `S098: a reading out of its limits shows High as it is typed` — type 62 in the
  30–60 item: `"High"` shows before *Save*; saved, the row keeps `"High"`; 45 removes it.
- **important** `S098: Not OK needs a remark and shows on a red row` — *Not OK*, *Save* with an
  empty remark → `"Say what is wrong."` beside the field; typed "Oil seeping at the left rod seal",
  saved; after a reload the row shows the remark.
- **important** `S098: a reading that logs a meter is refused on the item when the counter is
  lower` — a plan whose reading item logs *Run hours · <machine>*; the operator logged 1,260 h an hour
  before by API; the job started with *Now*; 1,200 → the refusal `"Lower than the reading of"` under
  the item and the tick `"Meter reset"`; the count stays `"0 of 1 filled"`; 1,270 → saved, the line
  `"Also logged as a Run hours reading of"`; the equipment page's Meters card shows the latest
  reading "1,270 h".
- **important** `S098: recorded on behalf: another person and a start two days back` — *Performed
  by* the seeded operator without a phone (the person named "Ramesh (operator, no phone)" in
  `tooling/e2e/seed_e2e.py`; the option found by "Ramesh"), *Now* unticked, a time two days back;
  *Start job*; the card reads that name and the time; *Mark job done* with a *Done* time before
  *Started* → `"Done must be at or after Started"` beside the field (`expectDialogFits`).
- **important** `S098: a started job keeps its items when the plan changes` — start the job; the
  engineer adds a fourth item by API (`PUT /api/pm/plans/<id>`); the job page still shows `"0 of 3
  filled"`; a new job of another plan, not started, shows the plan's items as they are.
- **important** `S098: a save during a network drop says Not saved and keeps the tap; it saves on the
  next tap` (BR1-06) — start, fill one item; `page.context().setOffline(true)`; tap *OK* on the
  next: `"Not saved"` under it and the row unfilled (`"1 of 3 filled"`); `setOffline(false)`; tap
  *OK* again: `"Saved"`, `"2 of 3 filled"`; a reload shows both items filled.
- `S098: IT admin and the operator read the job and have no Start job` — both see the items and no
  `"Start job"`.
- `S098: the job page fits a phone with large item buttons` (`@device`) — an in-progress job:
  `expectNoSidewaysScroll`; each of *OK*, *Not OK*, *NA* is at least 44 px high; the three fit one
  row.

**`frontend/e2e/me.spec.js`:**
- **important** `S098: Me › Open work lists my started PM job above the tickets` — the technician
  starts a job by API; *Me*: the heading `"PM jobs (1)"`, the row with `"In progress"`; a tap opens
  the job page.

**`frontend/e2e/pm-jobs.spec.js`** (S097's): the changed test above, and
- `S098: a started job shows In progress on the Due tab` — started by API while *Upcoming* (last done 9
  days ago): it shows on *Due* with `"In progress"`, not on *Upcoming*.

**`frontend/e2e/screens.spec.js`** (its `screens()` list): `{ path: "/pm/jobs/<id>", title: "PM job",
shows: (page) => page.getByRole("heading", { name: job.serial }), who: TICKET_ROLES }` (the
`pm_job:read` roles: every role but the storekeeper, S097). Its set-up already saves "Screens test:
monthly check" as the engineer (a monthly calendar plan with no `last_done_on`, so no job today):
the set-up adds `last_done_on` 40 days back to that plan's body, so the save makes its job (one plan,
one job, `pmPlan` unchanged), and the job is read from `GET /api/pm/jobs` by the machine (BS1-09).

**Runs** (settings: *Browser tests*): targeted `tooling/run-e2e-tests.bat e2e/pm-job.spec.js
e2e/pm-jobs.spec.js e2e/me.spec.js e2e/pm-plans.spec.js e2e/readings.spec.js e2e/screens.spec.js`;
the whole suite at Normal once at the end (the router is shared). No change to `api.js` or
`e2e/support/`, so no extra WebKit run.

### 8.5 On a real device

Rows for `docs/steps/device-checks.md`; by IT Admin, on production on the TEST machine after the
release, on a pilot press at SMTW or SSVT (Q0.2 a), with a technician's account:

- *A real Wi-Fi drop* (a plain note; the browser test above covers the rule, BR1-06). On an Android
  phone on the plant Wi-Fi, start a job and fill two items. Walk to a dead spot, tap an item: it
  reads "Not saved … Tap again." and keeps the tap. Back in range, tap again: "Saved". Reload: every
  item filled before the drop is there.
- **important** *A gloved thumb.* With a work glove, tap *OK*, *Not OK*, *NA* on three items and *Done*
  on a task: each tap hits the button meant, never its neighbour.
- *The number keypad.* On the iPhone, tap a reading's input: the decimal keypad shows, and *Save* is
  not hidden behind it (scroll if needed). On Android the same.

### 8.6 Acceptance and the SMTW-Review point

- All unit suites green; `tooling\schema-docs.bat check` exits 0; the targeted and the Normal browser
  runs green.
- By screen, on the S096 acceptance plan ("Monthly hydraulic check" on a press at SMTW, due 02-11-2026
  or at 2,090 h): the technician opens *PM*, taps the job, starts it, fills the seven items (the
  power-pack temperature 48.5 °C, the run hours read into the press's meter), marks it done; the job
  reads *Done*, *On time*; the run hours reading is in the press meter's history and the item says
  *Also logged* (the history shows no source; BR1-11); *Me* shows the job
  while it is in progress; IT admin reads it and changes nothing.
- **§ SMTW-Review points** (for `.claude/CLAUDE.md`):
  - *Meter readings (S039)* gains: "A PM job's reading item (S098) uses the same path:
    `meters.lock_node`, `meter_in_force`, `write_reading` (the checks and the insert, one
    copy), after its plan (6e) and job (6f) locks and before any plain read; its time is the job's
    *Started* time."
  - New: "**PM job results (S098):** a job's items are copied from the plan's active items at *Start*
    (`pm_job_results`), and nothing changes them afterwards but the job's own item saves while it is
    `in_progress`; a plan edit or deactivation never touches a started job (S097's `settle_plan_job`
    leaves `in_progress` alone), and a done job is read-only until R03.5's send back. Every write of
    `pm_work.py` takes the plan (6e), then the job (6f), then a node, before any plain read (the job's
    `plan_id` is read before the transaction). A refused meter value saves nothing on the job.
    *Mark job done* stores `done_at`, `done_meter` and `timeliness` (`pm_schedule_core.timeliness`
    over the job's own copies). A path that rewrites a started job's results from the plan, writes a
    PM reading outside `write_reading`, or reads plainly before its node lock breaks R03.4–R03.5."

## 9. Open questions and assumptions

All choices below were **decided by the orchestrator under KLA's go-ahead of 01-11-2026 ("Start
work on PM module … Do those steps … stop only for real show stoppers"), to confirm at gate B.**

- **Q1. Copy at *Start*; a started job keeps its items, due point and assignee** (D1, D2). As the
  roadmap says.
- **Q2. A started job of a deactivated plan stays open and can be finished** (D2). New rule.
- **Q3. Any technician at the site may work any job** (D3), as tickets.
- **Q4. A refused meter value saves nothing; the item shows the refusal** (D4).
- **Q5. *Started* and *Done* up to 7 days back for everyone, admin too** (D5): a departure from
  S028's backlog window for tickets.
- **Q6. The reading's time is *Started*; *Started* is fixed** (D6).
- **Q7. Not OK, Not done and a reading's NA need a remark** (§ 5.4). A small departure from the
  mock-up, where the remark is shown but not said to be required.
- **Q8. Every job ends at `done`, also one that needs verification** (D10); R03.5 adds `verified`.
- **Q9. *Open work*: due, overdue and started; mine = assignee or performer** (D11).
- **Q10. Scrapping waits for started PM jobs** (D15).
- **Q11. *Mark job done* after the items, not a fixed bar** (D13): a departure from the mock-up.
- **A1. S095, S096 and S097 as briefed.** S097 is in brief review tonight; its names in § 3 must hold
  when S098 is coded, and the staleness review fixes this brief if they changed (in particular
  `settle_plan_job`'s signature, `decide`'s `in_progress` row, `tab_of`, `jobs_out`, the list's
  answer shape and its `assigned=me`).
- **A2. The read before the transaction is safe** (§ 5.7): pool connections are autocommit
  (`backend/db_helpers.py`, `transaction`'s docstring; `backend/local_db.py` `"autocommit": True`), so
  that read is its own snapshot; the columns it reads never change.
- **A3. `chk_pm_jobs_started` holds for S097's rows** (§ 4.1): S097 writes only `due` and
  `cancelled`. If S097 ships first and writes another state, its rows are checked by the migration
  test against a v52 database.
- **A4. The network case of `api.js`** (`err.status` 0, `NO_CONNECTION_TEXT`) is what an item shows on
  a drop; checked in the code (`frontend/src/api.js`, `send`) and by the browser test with
  `setOffline` (§ 8.4, BR1-06).
- **A5. A started job in a unit deactivated later** is reachable by nobody (`accessible_unit_ids`
  lists active units; S025 § 5.3 refuses a deactivation on open tickets only). Not S098's to build:
  noted for R03.9, whose skip (or a deactivation check like § 5.8's) is the way out (BR1-21).
- **Notes for later steps:** R03.5 sends a job back to `in_progress` (the results become writable
  again) and adds `verified`; R03.6 shows the copied `photo` and blocks *Mark job done* on a required
  photo; R03.10 offers a ticket for each `not_ok` and each result with `limit_state` set; R03.11 adds
  labour; R03.12 widens `pm_job:work` and adds the performer rule by plan.
- **Size: one step, two snapshot rounds** (decided with the review, BR1 *Size*). 30 code and test
  files, past the rule's 25, and about 1,250 lines; one table and two columns, one new page, one
  dialog, two small changes (the list, *Me*). The *Me* cut would save five thin files and lose the
  one path by which a technician finds the job he started (D11), so it is not taken.
  - **Round 1, the backend:** first the `meters.py` split (§ 5.5), with `test_readings_api.py` and
    `test_meters_api.py` run green before `pm_work.py` exists, so a refactor fault is never mixed
    with a new-route fault; then the core and its tests, the migration, `pm_work.py`, the S097
    changes, `equipment.py`, `config_rbac.py`, and their tests.
  - **Round 2, the screens:** the 13 frontend files and the browser runs.
- **Standards *to verify*:** EN 13306 term numbers; ISO 14224's clause; SMRP's metric number.
- **No defining question for KLA.**

## 10. Amendments

None.

## Review log

### Round 1 — `2-brief-review-r1.md`, answered 02-11-2026

Sections changed: § 3 (the S096 names checked against the code, `personLabel`, `STORED_DECIMALS`;
`pm_work_core` imports; `pm_jobs._now` through the module; `lock_node`), § 4.1 (the reading CHECK),
§ 5.1 (messages, `result_changes`, `job_time_error`, the window constant), § 5.2 (the state table,
the 404 order), § 5.3 (a start before *Created*), § 5.4 (`is_reset`, the remark sent as null,
idempotence with the reset mark), § 5.5 (`lock_node`, only a `pm` reading removed, the same minute
with the mark), § 5.6 (the frozen offset), § 5.7 (Start step 4's access check), § 5.10 (the
scrapped line, `personLabel`, the dialog's consequence line), § 6.1, § 6.2, D8, § 8.2, § 8.3, § 8.4
(the offline test), § 8.5, § 8.6, § 9 (A4, A5, Size).

| Finding | Answer |
|---|---|
| BR1-01 minor | Accepted (a). § 5.2: an item on a `due` job is 404 (no result row; the pre-read stays); `state_error(DUE_STATE, FILL)` stays in the core and is tested there; § 8.2 tests `START_FIRST` through the performer `PUT` and *Mark done*, and a `PUT` of an item on a `due` job as 404. |
| BR1-02 minor | Accepted (a). § 5.4: the page sends `remark: null` on *OK*, *Done*, a check's *NA* and a reading's *Save*; the API still accepts a remark with any outcome. |
| BR1-03 minor | Accepted (a). § 5.5 step 3 removes only a reading of source `pm`; a linked `manual` reading is let go and step 4 then answers `SAME_MINUTE_PM`; `result_changes` compares the sent `is_reset` with the linked reading's (§ 5.1, § 5.4); D8 and § 8.2 follow. |
| BR1-04 minor | Accepted (a). `job_time_error` makes its own three comparisons with `meters_core.READING_BACKDATE_DAYS` and `tickets_core.FUTURE_SKEW`; no text replacement, no tickets constant (§ 3, § 5.1). |
| BR1-05 minor | Accepted (a). `pm_plans_core.STORED_DECIMALS` imported; `RESET_ONLY_COUNTER` dropped, `validate_reading`'s `ONLY_A_COUNTER_RESETS` and `RESET_NOT_BOOL` used (§ 5.4, § 8.2); the start message renamed `PERFORMED_BY_NEEDED`. |
| BR1-06 minor | Accepted (a). § 8.4: the important test `S098: a save during a network drop says Not saved and keeps the tap; it saves on the next tap` with `setOffline`; § 8.5 keeps the real Wi-Fi as a plain note; § 9 A4. |
| BR1-07…BR1-21 nits | All accepted. 07: `_lock_node` becomes the public `lock_node`, one name. 08: `pm_work.py` calls `pm_jobs._now(cur)` through the module, and a test shows it. 09: `can_start` false on a scrapped node; `equipment.lifecycle` answered; the line "This machine is scrapped. The job cannot be started.". 10: `NO_ITEMS` kept as a defensive 409, said unreachable. 11: § 8.6 reworded (no source on the history). 12: the CHECK reads `(outcome IS NULL OR value IS NULL)`. 13: the frozen offset stated in § 5.6 and Plan.MD's paragraph. 14: a start before *Created* allowed and said (§ 5.3). 15: `PERFORMED_BY_NEEDED` on a bad `performed_by_id` in the `PUT` (§ 6.1, § 8.2). 16: `JOB_CANCELLED` "This job was cancelled."; R03.9 gives the skip its own text. 17: the dialog's line "The job can no longer be changed.". 18: the lock test modelled on `test_two_writers_on_one_node_serialise_and_the_second_sees_the_first`. 19: Start's access check said to be `equipment:read`'s, the route safe through `require_perm("pm_job:work")`. 20: the v52 hedge dropped. 21: § 9 A5, noted for R03.9. |
| Size | One step, two snapshot rounds: backend first, the `meters.py` split landed with the readings tests green before `pm_work.py`; then the screens (§ 9 Size). |

### Staleness s1 — `2-brief-review-s1.md`, answered 02-11-2026

Checked against `refs/steps/S097` (S095–S097 coded). Sections changed: header (`Baseline:`), § 3
(the S097 names as coded; `pm_work.py` imports; the `pm_jobs.py` done path and call sites), § 4.1
(beside `chk_pm_jobs_done`, the generated `open_plan_id`, `created_why`), § 5.7 (`LOCK_PLAN`,
`SHARE_NODE`), § 5.9 (`PmJobRow.vue` keeps `job-row` and `data-equipment`; `countText`), § 5.10
(`tickets.list_people` and `EventFields.vue` anchors, `idPrefix`, `RUN_ACTOR`), § 6.2
(`meter_type_out`), § 6.3 (`_DONE_SELECT`, `_job_item`), § 8.3 (`test_tab_of`, `test_list_order`,
the `pm-jobs.spec.js` lines), § 8.4 (the screens set-up).

| Finding | Answer |
|---|---|
| BS1-01 minor | Accepted (a). `_JOB_SELECT` and `jobs_out` stay for open jobs; a new `_DONE_SELECT` (the same joins, `done` / `verified`, `ORDER BY done_at DESC, id DESC`, paged, `COUNT(*)` for `total`) feeds the *Done* tab; the item dict moves into `_job_item(row, standing, reading)`, called by both loops (the done loop with `None, None`); `counts` keeps coming from the open jobs (`_counts`, `_EMPTY`), with `in_progress` added. § 3 and § 6.3. |
| BS1-02…BS1-10 nits | All accepted. 02: `pm_jobs.LOCK_PLAN` and `SHARE_NODE` reused, named in § 3 and § 5.7. 03: `pm_jobs.meter_type_out` builds the meter type in § 6.2. 04: § 3 names `countText`, `nextDueText`, `VERIFIED`, `SKIPPED`, `CANCELLED`, `JOB_STATES`, `RUN_ACTOR`, and the two call sites (`list_jobs`' `tab_of`, `jobs_out`'s `list_order` item) that get the job's `state`; § 5.9 `countText`, § 5.10 `RUN_ACTOR`, § 8.3 `test_list_order`. 05: § 3 lists v52's `created_why`, `created_by`, `updated_*`, the generated `open_plan_id` (never written), `pm_job_events`' `id`, `due_on`, `due_meter`, `created_at`; § 4.1 shows both CHECKs met by § 5.6's and Start's `UPDATE`, and the v52 rows set `created_why`. 06: `tickets.list_people` at `backend/tickets.py:789`, its key, `_picker_anchor` and `people_at_site`. 07: `frontend/src/views/tickets/EventFields.vue`, with the required `idPrefix` (`pm-start`, `pm-done`). 08: the spec's three lines named; `PmJobRow.vue` keeps `job-row` and `data-equipment`. 09: the screens set-up adds `last_done_on` 40 days back to its existing plan. 10: the facts file re-run after S097's code (`scratch/brief-facts-S098.md`, 02-11-2026): every S097 name resolves; the only names not found are S098's new ones. |
