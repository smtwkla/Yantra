```
Step: S097 — PM jobs come due
Doc: impl-report
Author: Coder (Opus)
Date: 02-11-2026
```

# S097 — implementation report

**Status of this report:** both rounds are done. Round 1 (the backend) is below; round 2 (the screens, the
frontend and browser tests, the fixes of code review r1, the full runs) follows it, under `## Round 2 — screens`.
The `## Manual checks` and `## Docs updated` sections cover the whole step.

## Round 1 — backend

**Result:** the backend of R03.3 is built as briefed: migration v52 (`pm_jobs`, `pm_job_events`), the pure core
`pm_jobs_core.py` (tests written first and shown red), the shell `pm_jobs.py` with `GET /api/pm/jobs`, the daily
task `pm_generate` at 05:00 IST, the S096 save hook, the card's `schedule`, the `meters.py` reads and the key
`pm_job:read`. The backend suite and the tooling suite are green (numbers in § Tests, round 1). No departure from
the brief changes behaviour; the small choices are in § 4.

BACKEND ROUND DONE.

## 1. What was built (round 1)

- **Migration v52** (`backend/local_db.py`): the two tables exactly as § 4.1. No precondition (new tables only).
- **`backend/pm_jobs_core.py`** (new, pure): the constants of § 5.1 and `decide`, `due_copies`, `due_from_job`,
  `job_changes`, `meter_offset`, `days_past`, `tab_of`, `list_order`, `pm_serial`, `assignable_id`.
- **`backend/pm_jobs.py`** (new): the blueprint `pm_jobs_bp` with `GET /api/pm/jobs`; `schedule_inputs`,
  `settle_plan_job`, `generate`, `jobs_out`, `plan_schedules`, `_now`; the LOCK ORDER note of § 5.7.
- **The daily run**: `task_handlers.pm_generate` and its `HANDLERS` entry; `("pm_generate", "05:00")` second in
  `scheduled_tasks.SCHEDULE`.
- **The plan save** (`backend/pm_plans.py`): the create and the change route call
  `pm_jobs.settle_plan_job(cur, plan_id, node["lifecycle"], pm_jobs._now(cur), actor())` last in their
  transaction; the card list's items carry `schedule` (active: `plan_schedules`; inactive: null).
- **`backend/meters.py`**: `_last_readings` is now the public `last_readings` (three callers, all in
  `meters.py`; no change of behaviour); new `first_reading_after` and `readings_across_reset`.
- **`backend/config_rbac.py`**: `"pm_job:read": ("maint_operator", "it_admin")` with the brief's comment; in
  `SITE_SCOPED`.
- **`backend/app.py`**: the blueprint at `/api/pm`, after `pm_plans_bp`.

## 2. How it works (round 1)

- **One function writes jobs.** `settle_plan_job` reads the plan and its open job plainly (the caller holds the
  plan row, or has just inserted it), works out the plan's schedule only when a job may be made or refreshed,
  and asks `decide` (§ 5.5's table). CREATE takes the `PM:YYYY-MM` counter, inserts the job with the copies of
  S095's `Due` and the reset offset, and writes the `created` line. REFRESH writes only the columns that differ
  (`job_changes`), with a `due_changed` line when `due_on` or `due_meter` changed and an `assignee_changed` line
  when the assignee changed. CANCEL sets `cancelled` with the remark.
- **The schedule inputs** (`schedule_inputs`): the last done job (none until R03.4), the base meter value and
  its time by § 5.3's table (`last_readings(..., until=T)`, then `first_reading_after`), the latest reading, and
  the offset from `readings_across_reset` (empty unless a reset follows the base, one query). `next_due` and
  `job_state` then give the due point and the standing; the reading passed is `latest + offset`.
- **The daily run** (`generate`): reads the candidates (active plans, and plans with a `due` job), commits (it
  starts inside the worker's transaction, BR1-01), then settles each plan in its own `transaction(conn)`: (6e)
  the plan `FOR UPDATE`, (1) the node `LOCK IN SHARE MODE`, `SELECT NOW()`, then `settle_plan_job`. A plan that
  raises is rolled back alone and logged; a lost connection is re-raised. It returns the counts; the handler logs
  "pm_generate: N created, N refreshed, N cancelled, N failed", raises `RetryLater(…, 60)` after a stop and
  `RuntimeError("pm_generate: plans … failed")` when any plan failed.
- **The list** (`GET /api/pm/jobs`): one query over the open jobs at the user's units (`accessible_unit_ids(cur,
  "pm_job:read")` over the node's root unit), with the `unit_id` and `assigned=me` filters; `jobs_out` makes one
  `last_readings` query over the plans' meter nodes, judges each standing live from the job's copies and
  `latest + meter_offset`, sorts by `list_order` and builds the items of § 6.1. The answer holds the asked tab's
  items and `counts` over both tabs.
- **The card** (`plan_schedules`): null for every plan without `pm_job:read` at the node's site; else the open
  jobs of the listed plans in one query (through `jobs_out`), and `schedule_inputs` per plan without an open job.

## 3. Files touched (round 1)

| File | Change |
|---|---|
| `backend/local_db.py` | migration v52 |
| `backend/pm_jobs_core.py` | new, the pure core |
| `backend/pm_jobs.py` | new, the shell and `GET /api/pm/jobs` |
| `backend/pm_plans.py` | the save hook in both routes, `schedule` on the card's items, the lock statements from `pm_jobs`, docstring (S097 lines) |
| `backend/meters.py` | `last_readings` public; `first_reading_after`, `readings_across_reset` |
| `backend/config_rbac.py` | `pm_job:read`, in `SITE_SCOPED` |
| `backend/scheduled_tasks.py` | `pm_generate` at 05:00 |
| `backend/task_handlers.py` | the handler, its `HANDLERS` entry, the docstring's third commit exception |
| `backend/app.py` | the blueprint |
| `backend/equipment.py` | docstring: the (6e) entry and its bullet |
| `backend/tests/test_pm_jobs_core.py` | new, 95 tests |
| `backend/tests/test_pm_generate.py` | new, 16 tests (the run) and the helpers the API tests share |
| `backend/tests/test_pm_jobs_api.py` | new, 21 tests (the list, the save, the card, 503) |
| `backend/tests/test_migration_v52.py` | new, 20 tests |
| `backend/tests/test_rbac.py` | `pm_job:read` in six rows of `test_role_matrix`, the comment line, new `test_pm_job_keys` |
| `backend/tests/conftest.py` | `pm_job_events`, `pm_jobs` first in `_TABLES` |
| `backend/tests/test_scheduled_tasks.py` | the schedule with `pm_generate` second; the docstring line |

17 files, as the brief's backend count.

## 4. Decisions taken (round 1)

- **`pm_plans.py` takes its two lock statements from `pm_jobs`** (`LOCK_PLAN`, `SHARE_NODE`; S096 had them as
  private constants with the same text). The run needs the same two statements, and `pm_jobs` may not import
  `pm_plans`, so the one copy moved to `pm_jobs` (DRY). No change of behaviour.
- **`generate` returns its counts and `stopped`; the handler raises.** `RetryLater` is defined in
  `task_handlers.py`, which imports `pm_jobs`; raising it from `pm_jobs` would need the reverse import. The
  handler raises exactly as § 5.6 says. The retry delay is the constant `PM_STOPPED_RETRY_SECONDS = 60`.
- **`pm_plans.py` calls `pm_jobs._now(cur)`**, the brief's name, so the tests that fix the clock by
  monkeypatching `pm_jobs._now` fix the save and the list too.
- **The inactive card items get `schedule: null`** (the brief: "Inactive items get `schedule` null"), so every
  item of both lists has the key.
- **A `before_use` plan on the card** gets `{open_job: null, next_due: null, meter: null}` (S096 refuses the kind,
  so none exists; this only keeps `next_due` from failing on one).
- **`decide` raises `TypeError` for a flag that is not a bool** and `ValueError` for an unknown state (the
  brief's type rules, S095 D8).
- **Test helpers:** `test_pm_generate.py` holds the helpers the API tests import (`fix_now`, `jobs_of`,
  `events_of`, `set_plan`, `add_reading`, `daily`); no new helper module. A run test that counts serials first
  deactivates the plans of earlier tests and cancels their due jobs straight (`alone`), because the run settles
  every plan in the worker's database.
- **S096's review note** (an item-only save does not stamp the plan's `updated_at`): it does not matter to S097.
  S097 never reads `pm_plans.updated_at`; an item-only save still calls `settle_plan_job`, which finds the due
  point unchanged (items do not move it) and writes nothing.

## 5. Not done, deferred or assumed (round 1)

- The screens, the frontend tests, the browser tests and the full runs: round 2.
- `GET /api/pm/jobs` sends `plan.performer`, so the screen shows "Operator" for an operator plan (§ 5.9).
- **A4 verified:** `tooling\schema-docs.bat write` shows `open_plan_id` in `schema.json` as `int`, `UK`,
  `stored generated` (the expression itself is not shown; the table's note names it).

## Tests (round 1)

- **Red, then green (the core):** `tests/test_pm_jobs_core.py` was written before `pm_jobs_core.py` and run
  alone: `ImportError` (1 error). After the core: 95 passed.
- Targeted runs while coding, all green at the end: `test_pm_jobs_core.py` 95, `test_migration_v52.py` 20 (with
  `test_rbac.py` 85 together), `test_pm_generate.py` 16, `test_pm_jobs_api.py` 21; `test_pm_plans_api.py`,
  `test_scheduled_tasks.py`, `test_rbac.py`, `test_readings_api.py`, `test_meters_api.py`, `test_worker.py`,
  `test_migration_v50/51`, `test_migration_squash_v41.py`, `test_modules.py` green after the edits.
- **Backend suite** (`YANTRA_TEST_RUN=s097c1 tooling\run-backend-tests.bat`): 4954 passed in 112 s.
- **Tooling suite** (`tooling\run-tooling-tests.bat`, includes the line-width check): 239 passed. A first run
  found one 142-character docstring line of mine in `task_handlers.py`; wrapped, then green.
- **Schema docs:** `tooling\schema-docs.bat write`: 4 passed at v52; `check`: 4 passed, exit 0.
- `test_pm_plans_api.py` needed no change: no S096 test compares a card item whole, and its save tests use plans
  far from due or check fields a job does not touch.

## Round 2 — screens

**Result:** the screens of R03.3 are built as briefed: the PM list (`/pm`, nav item *PM* after *Tickets*), the
open job or the next due point on the equipment page's PM card, and the Settings label of `pm_generate`. The four
findings of code review r1 are fixed (below). All unit suites, the schema docs check, the targeted browser run,
the whole browser suite at Normal and the WebKit S040 run are green (numbers in § Tests, round 2). One wording
departure from the brief's examples: meter values show their meter type's decimals ("at 1,250.0 h"), see § 4.

### 1. What was built (round 2)

- **`frontend/src/views/PmJobsView.vue`** (new): the PM list of § 5.9. Tabs *Due* and *Upcoming* (`nav nav-tabs`
  router links, `tab=upcoming` in the URL, *Due* the default); the filters *Unit* ("All my units", then the
  user's units by full code) and *Assigned to me* (shown only with a Team record, `userPersonId`); the count line
  ("4 due · 1 overdue", "3 upcoming"); one row per job, a link to `/equipment/pm/<plan id>` of at least 44 px:
  the standing badge, the serial, the due text and the days past; the machine in bold; the plan with its item
  count; the unit, the meter now and the assignee. The states: "Loading…", the load error with *Retry*,
  `NO_UNITS_TEXT`, and the three empty texts of § 5.9.
- **`frontend/src/views/equipment/PmPlansCard.vue`**: under each active plan with a `schedule`, the open job's
  badge and "PM-2026-11-004 · 29-11-2026 · 3 days ago" (and the meter now for a meter plan), or the next-due line.
- **`frontend/src/utils/pmLabels.js`**: `STANDING_LABELS`, `STANDING_BADGES`, `dueText`, `daysPastText`,
  `meterNowText`, `assigneeText`, `jobsQuery` as the brief names them, and two more: `nextDueText` (the card's
  line without a job) and `countText` (the count line).
- **Nav and route:** `navigation.js` gains `pm` after `tickets` (`pm_job:read`); `router/index.js` gains `/pm`
  after the improvements routes (title "PM"); `canOpenRoute` guards a typed `/pm`.
- **`SettingsView.vue`**: `TASK_LABELS.pm_generate` = "Create the PM jobs that are due or coming up".

### 2. Code review r1 fixes

- **CR1-01 (minor) Fixed.** `pm_jobs_core.due_copies` rounds `due_meter`, `meter_window` and `meter_offset` to
  three places, half away from zero, as `DECIMAL(14,3)` stores them, so `job_changes` compares like with like.
  New core test `test_the_copies_take_the_column_s_three_decimals` (25.0005 copies as 25.001, and a job that
  stores 25.001 has no change). Fails without the fix: `assert (Decimal('2500.0005'), …) == (Decimal('2500.001'),
  …)`; passes with it.
- **CR1-02 (nit) Fixed.** `settle_plan_job` answers None when a refresh writes nothing (`_refresh` returns
  whether it wrote), so the run's "N refreshed" counts real writes. New test
  `test_pm_generate.py::TestRun::test_the_counts_name_only_real_writes` (two runs; the second counts 0 refreshed,
  and the job's `updated_at` stays NULL). Fails without the fix: `assert (0, 1, 0) == (0, 0, 0)`; passes with it.
- **CR1-03 (nit) Fixed.** One function `local_db.connection_lost(conn, exc)`: the connection is closed, or an
  `OperationalError` whose code `is_connection_lost` names. `worker.Worker._connection_lost` is removed and
  `run_one` calls it; `pm_jobs.generate` calls it in place of its own `_lost`. The worker calls it only in its
  `OperationalError` branch, so its behaviour is unchanged. No new test: `test_worker.py`'s lost-connection
  tests cover the worker's path, and they pass.
- **CR1-04 (nit) Fixed.** `pm_jobs.meter_type_out(row)` is the one copy of the meter-type shape; `pm_jobs._meter_out`
  and `pm_plans._meter_out` use it, and `pm_plans._meter_type` is removed (`pm_jobs` may not import `pm_plans`,
  so the copy lives in `pm_jobs`, as `LOCK_PLAN` does). No new test: a refactor with no change of behaviour,
  covered by `test_pm_plans_api.py` and `test_pm_jobs_api.py`.

### 3. Files touched (round 2)

| File | Change |
|---|---|
| `frontend/src/views/PmJobsView.vue` | new, the PM list |
| `frontend/src/views/equipment/PmPlansCard.vue` | the job line or the next-due line |
| `frontend/src/utils/pmLabels.js` | the PM job helpers |
| `frontend/src/stores/navigation.js` | the *PM* item |
| `frontend/src/router/index.js` | the `/pm` route |
| `frontend/src/views/SettingsView.vue` | the task's label |
| `frontend/tests/pmLabels.test.js` | the helpers' tests |
| `frontend/tests/navigation.test.js` | the role lists, two changed and one new test |
| `frontend/e2e/pm-jobs.spec.js` | new, 8 tests |
| `frontend/e2e/screens.spec.js` | the `/pm` screen; the S040 test with seven items |
| `backend/pm_jobs_core.py`, `backend/pm_jobs.py`, `backend/pm_plans.py`, `backend/local_db.py`, `backend/worker.py` | the CR1 fixes |
| `backend/tests/test_pm_jobs_core.py`, `backend/tests/test_pm_generate.py` | the CR1-01 and CR1-02 tests |

Frontend: 10 files, as the brief's 11 less `frontend/e2e/support/` (unchanged, as the brief says).

### 4. Decisions taken (round 2)

- **Meter values show their type's decimals:** "at 1,250.0 h", "Run hours now 1,260.0 h". The brief says to use
  `formatReading` (§ 5.9 *Numbers and dates*), which pads to the meter type's decimals (Run hours has 1); its
  examples ("at 5,000 h") show none. I followed the rule, so the list matches every other reading on the app's
  screens; the browser test asserts what the screen shows. If KLA wants targets without padding ("at 1,250 h"),
  it is one helper change in `dueText`.
- **Two extra helpers** in `pmLabels.js`, `nextDueText` and `countText`, so the card's line and the count line are
  tested in vitest, not built in the templates.
- **The unit filter offers the user's equipment units** (`filterableUnits(units, myUnits)`, as the tickets list).
  A unit where the user reads equipment but not PM jobs gives no rows; every role that reads equipment also
  holds `pm_job:read` except the storekeeper, who has no PM item.
- **The deactivate browser test** does not call `expectDialogFits` on the *Yes* confirmation, as S096's test of
  the same flow does not: it is not a form dialog with *Save* and *Cancel*.
- **`frontend/e2e/pm-plans.spec.js` needed no change:** every card assertion uses `toContainText` on its row, so
  the new job line does not break it (checked by the targeted run).

### 5. Not done, deferred or assumed (round 2)

- None beyond the brief's *Out of scope*. A3 (seven items fit the bottom bar) is checked on `phone-chromium` in
  the Normal run and on `phone-webkit` in the one WebKit run (§ Tests, round 2).

### Tests (round 2)

- **Frontend unit tests while coding:** `pmLabels.test.js` 26 passed; `navigation.test.js` 14 passed.
- **Build check:** `npx vite build` built clean (the chunk-size warning only).
- **The new browser tests alone** (`E2E_LANES=1`, `e2e/pm-jobs.spec.js --project=phone-chromium -g S097`): 8
  passed in 13.7 s.
- **Targeted run** (Normal: `e2e/pm-jobs.spec.js e2e/pm-plans.spec.js e2e/equipment.spec.js e2e/screens.spec.js`):
  91 passed, 2 skipped (the phone-only bottom-bar test on desktop), all lanes done in 94 s.
- **The CR1 fixes:** red then green as in § 2; then `test_pm_jobs_core.py test_pm_generate.py test_pm_jobs_api.py
  test_pm_plans_api.py test_worker.py test_contract_alerts.py test_alerts.py`: 288 passed.
- **All unit suites** (`YANTRA_TEST_RUN=s097c1 tooling\run-tests.bat`): ALL SUITES PASSED. Backend 4956
  passed (155 s), frontend 439 passed, tooling 239 passed.
- **Whole browser suite at Normal** (`tooling\run-e2e-tests.bat`): 395 passed, 15 skipped, **1 failed**, all
  lanes done in 200 s. The failure is outside S097: `e2e/improvements.spec.js:97` *S068: the Improvements tab
  lists the improvement, the Unit filter narrows, Closed is empty* expects "No closed improvements yet.", but an
  earlier test in the same lane (lane 5) had dropped an improvement, which lists under *Closed*:
  `improvement-register.spec.js:83` (S076, *the dropped improvement shows under Closed in the period*) (corrected
  in fix round 1; this report first named the spec's own S073 test). S097 changes no improvement code; the new spec moved tests between lanes, so this test now runs after a
  closing one. Re-run alone (`tooling\run-e2e-tests.bat e2e/improvements.spec.js`): 25 passed in 48.6 s. Every
  S097 test passed in the Normal run (`pm-jobs.spec.js`, `screens.spec.js` including `/pm` and the seven-item
  bar). **Not fixed here:** it is an order-dependent assumption in S068's test (it should look only for its own
  improvement under *Closed*, or not assert the empty state). I recommend a fix-lane step. I did not run the
  whole suite again: the failing test passes alone, and nothing of S097 changed after the run.
- **WebKit S040** (`tooling\run-e2e-tests.bat e2e/screens.spec.js --project=phone-webkit -g "S040"`): 1 passed
  (the seven items fit the 390 px iPhone; A3 confirmed on both phones).
- **Schema docs check** (`tooling\schema-docs.bat check`): 4 passed, exit 0.

## Manual checks

- [auto] **important** A plan saved past due shows its job as Overdue on the PM list —
  `frontend/e2e/pm-jobs.spec.js::S097: a plan saved past due shows its job as Overdue on the PM list`
- [auto] **important** A job inside its window shows under Upcoming, not under Due —
  `frontend/e2e/pm-jobs.spec.js::S097: a job inside its window shows under Upcoming, not under Due`
- [auto] **important** The equipment page's PM card shows the open job and the next due date —
  `frontend/e2e/pm-jobs.spec.js::S097: the equipment page's PM card shows the open job and the next due date`
- [auto] **important** Deactivating the plan takes its job off the PM list —
  `frontend/e2e/pm-jobs.spec.js::S097: deactivating the plan takes its job off the PM list`
- [auto] A meter plan comes due when the reading passes its due value —
  `frontend/e2e/pm-jobs.spec.js::S097: a meter plan comes due when the reading passes its due value`
- [auto] Assigned to me shows only my jobs — `frontend/e2e/pm-jobs.spec.js::S097: Assigned to me shows only my jobs`
- [auto] IT admin reads the PM list and has no Assigned to me —
  `frontend/e2e/pm-jobs.spec.js::S097: IT admin reads the PM list and has no Assigned to me`
- [auto] The PM list fits a phone with no sideways scroll (`@device`) —
  `frontend/e2e/pm-jobs.spec.js::S097: the PM list fits a phone with no sideways scroll`
- [auto] The `/pm` screen opens for every holder of `pm_job:read` — `frontend/e2e/screens.spec.js::every screen
  opens as <role>`
- [auto] The manager's bottom bar shows seven items without sideways scroll (both phones) —
  `frontend/e2e/screens.spec.js::S040, S097: the manager's bottom bar shows all seven items without sideways scroll`
- On a real device: none (brief § 8.5); no row added to `docs/steps/device-checks.md`.

## Docs updated

- `docs/schema/notes.json`: `pm_jobs` and `pm_job_events` moved from `planned` to `tables`; the area's note names
  jobs (S097); `serial_counters` names `PM-` (S097); `pm_plans` notes the cancel. Then `schema-docs.bat write`
  (`schema.json`, `schema-data.js` generated), `git diff docs/schema/` read.
- `docs/Plan.MD`: § 3 the `pm_job:read` row of the matrix and its paragraph; § 4.3 *Built (S097)* under *PM job*;
  § 6 the nav order with *PM*.
- `.claude/CLAUDE.md`: § Step workflow (2) names `pm_jobs.py`; § SMTW-Review the *PM jobs (S097)* point.
- `docs/Keycloak.md`, `docs/steps/device-checks.md`: no change (§ 3: no new role or claim; § 8.5: no
  real-device check).

## Feedback

- waste: a stray `uv run python -` with an empty heredoc opened an interactive Python and held the shell for
  2 minutes until stopped (my command, not a tool fault).
- hindrance: `db_rows` returns tuples, so `== []` on an empty result fails; three of the first six failures in
  `test_pm_generate.py` were that (1 run).
- idea: `tests/conftest.py` could offer a `technician_at(site)` fixture; S096's and S097's tests each build one
  with `make_person` and `give_site_role`.

### Feedback (round 2)

- hindrance: an inline `sed` with `\r\n` in its replacement wrote raw line breaks into a Python script, which
  then had to be repaired with Edit (my own break of README § Shell rule 1; 2 runs lost).
- hindrance: a new spec file moves tests between lanes, and an older test that assumes an empty list (S068's
  "No closed improvements yet.") then fails in the Normal run (1 re-run of `improvements.spec.js`, 1 min).
- idea: `step-check` could flag e2e assertions of a global empty state ("No … yet.") in specs that share the
  lane database, since each one fails as soon as the lane plan changes.

## Fix round 1

Answers `4-code-review-r2.md` (run name `s097f1`).

### Round 1 (code review r2)

- **CR2-01 (minor): Fixed.** `pmLabels.js` has one helper, `dueValueText`, used by `dueText` (so also
  `nextDueText`): the places the value has, at most the type's decimals, Indian grouping, with the unit
  ("at 1,250 h"). `formatReading` stays in `meterNowText` (readings). Tests updated: `pmLabels.test.js` lines 144,
  145, 178 and `pm-jobs.spec.js` 122. Fails without the fix: `dueText` tests expected "at 5,000 h", got
  "at 5,000.0 h" (2 failed, 24 passed); passes with it (26 passed).
- **CR2-02 (nit): Fixed.** `pm-jobs.spec.js` card test: the badge locator is scoped to `pm-open-job`.
- **CR2-03 (nit): Fixed.** The S068 cause in the round 2 Tests section now names
  `improvement-register.spec.js:83` (S076) earlier in lane 5.

### Tests (fix round 1)

- `tooling/run-frontend-tests.bat tests/pmLabels.test.js`: 26 passed.
- `npx vite build` in `frontend/`: built.
- `tooling/run-e2e-tests.bat e2e/pm-jobs.spec.js e2e/pm-plans.spec.js e2e/screens.spec.js`: 38 passed, 1 skipped
  (phone-only test on desktop), all lanes done in 82 s.

### Docs updated (fix round 1)

- none, because the change is wording of a number on a screen; Plan.MD § 4.3 gives no due-value format.

### Feedback (fix round 1)

- none
