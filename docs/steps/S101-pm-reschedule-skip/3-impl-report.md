```
Step: S101 — Reschedule and skip a PM job
Doc: impl report
Author: coder (Opus)
Date: 02-11-2026
```

# S101 — Implementation report

**Result:** an engineer (any holder of `pm_job:verify` at the job's site) can move a due PM job to a new
date or meter value, or skip it, always with a reason. Migration v55 stores the move on the job, so the
daily run and a plan save keep it. All unit suites, the targeted browser run and the Normal whole suite are
green (numbers in § Tests). No departure from the brief's design. Four small forced choices are listed in
§ 4; the one to read is D-2 (the "Moved from" line in the job's first minute).

## 1. What was built

- **Migration v55**: `pm_jobs.rescheduled_on DATE NULL` and `rescheduled_meter DECIMAL(14,3) NULL` after
  `meter_offset`, and the CHECK `chk_pm_jobs_rescheduled` (a set value equals `due_on` / `due_meter`). No
  `_PRECONDITIONS` entry: every existing row gets NULL.
- **Reschedule job** (`POST /api/pm/jobs/<id>/reschedule`, `{due_on?, due_meter?, remark}`): a due job only
  (any standing). The new value replaces the computed one for that trigger; the windows stay the computed
  interval's. A `rescheduled` timeline line holds the new due point, the reason and the person.
- **Skip job** (`POST /api/pm/jobs/<id>/skip`, `{remark}`): a due job only. The job becomes `skipped` with
  `done_at` the skip minute and `done_meter` the meter value then; `timeliness` stays NULL. A `skipped` line
  holds the reason and the person. `skipped` is now a base state, so the plan's next job counts from the
  skip; the route settles the plan at once (a daily plan gets its next job at once).
- **The daily run and a plan save keep a move.** A change of the plan's schedule fields
  (`SCHEDULE_FIELDS`) drops it, with a `due_changed` line that says so ("The plan's schedule was changed, so
  the job's reschedule no longer applies.").
- **Skip gets its own text** "This job was skipped." in every refusal of S098's and S099's state tables.
- **The job page**: the card *Reschedule or skip* with **Skip job** and **Reschedule job** for a holder of
  `pm_job:verify` on a due job; "Moved from 08-11-2026." under the due line; "Skipped … by …: <reason>" on a
  skipped job; the history shows "Rescheduled to <due point>" and *Skipped* with their reasons.
- **The PM list**: badge *Rescheduled* on a moved due or started job; skipped jobs on the *Done* tab with
  *Skipped*, "Skipped <date>" and "by <name>"; the count line says "10 done · 2 skipped"; the empty text
  "No PM jobs are done or skipped yet."

## 2. How it works

**Core (pure).**
- `pm_jobs_core.job_override(job, trigger_kind)` reads the job's two reschedule columns and keeps only the
  ones the plan's kind still has (calendar for `calendar`/`both`, meter for `meter`/`both`, none for
  `before_use`).
- `due_copies(due, offset, override=None)` now also returns `rescheduled_on` and `rescheduled_meter` (the
  meter rounded to 3 places like the other meter columns). `due_from_job` sets `rescheduled` from them.
- `pm_work_core.reschedule_override(...)` judges the body in the brief's order: parse (date format, no
  calendar, no meter, the number), *moved* (a value equal to the job's own is no move), nothing moved, the
  bounds (the ticket's planned-date rule for the date; for the meter, above the counted reading and at most
  one interval past it), then builds next_due's override (the moved value, else the job's earlier move of
  that trigger). `move_error` allows only `due`. `move_reason` requires the reason. `reschedule_summary`
  gives the page's count of moves and the due point the job was first moved from.

**Shell.**
- `pm_jobs.schedule_inputs(cur, plan, now, override=None)` passes the override to `next_due`.
- `settle_plan_job(..., *, keep_reschedule=True)` reads the open job's override (`job_override`) unless
  `keep_reschedule` is False, and `_refresh` compares the override columns too. When they change (only a
  drop can change them there), it writes the `due_changed` line with `RESCHEDULE_DROPPED`, also when the
  due point stays.
- `pm_plans.change_plan` passes `keep_reschedule=not any(field in changes for field in SCHEDULE_FIELDS)`.
- The two routes in `pm_work.py` take (6e) the plan, (6f) the job, (1) the node shared, then the access
  check (404 / 403 with `pm_job:verify`), `move_error` (409), scrapped (409). Reschedule then refuses a
  `before_use` plan (defensive, BR1-03), reads the reading and offset once without the override, judges the
  body, recomputes with the override, writes the job's changed columns and the `rescheduled` line. Skip
  judges the reason, writes the job (state, `done_at`, `done_meter`) and the `skipped` line, and calls
  `settle_plan_job`, as *Mark job done* does.
- `job_detail` adds `can_skip` (the key at the site, state `due`, not scrapped), `can_reschedule` (the same,
  and the plan not `before_use`, from the new `JOB_FROM` column `pl_trigger_kind`) and `reschedule`.
  `job_item` adds `rescheduled` and `skipped`; `add_sign_off` fills `skipped` from the `skipped` line (one
  query, as the verify and send-back lines). The *Done* tab's SQL includes `skipped`, and its answer has
  `total_skipped` (one more count with the same filters).

**Frontend.** Two FormModal dialogs in S099's pattern (`blank()` reads the job at each open; `closed` hands
the saved job to the page; a 409 reloads it). `pmLabels.js` gains `movedFromText`, `jobSkippedText`, the
two event labels, the two badges and the fourth argument of `countText`.

## 3. Files touched

Backend (7)
- `backend/local_db.py`: migration v55.
- `backend/pm_jobs_core.py`: `BASE_STATES` gains `SKIPPED`; `RESCHEDULE_DROPPED`; `job_override`; the
  override in `due_copies` and `due_from_job`.
- `backend/pm_jobs.py`: `schedule_inputs` override; `settle_plan_job` `keep_reschedule`; `_refresh` writes
  the drop's line; `JOB_FROM` gains `pl_trigger_kind`; `job_item` `rescheduled`, `skipped`;
  `_SIGN_OFF_EVENTS`, `add_sign_off` the `skipped` line; `_DONE_WHERE` gains `skipped`; `total_skipped`; the
  LOCK ORDER note.
- `backend/pm_work_core.py`: the constants, messages and functions of § 5.2; `JOB_SKIPPED` in both state
  tables.
- `backend/pm_work.py`: the two routes, `_move_access`, `_move_reason`; `job_detail` gains `can_skip`,
  `can_reschedule`, `reschedule`; the LOCK ORDER note.
- `backend/pm_plans_core.py`: `SCHEDULE_FIELDS`.
- `backend/pm_plans.py`: `change_plan` passes `keep_reschedule`.

Backend tests (5)
- `backend/tests/test_migration_v55.py` (new): the columns, the CHECK both ways, v54 → v55 with a due, a
  done and a skipped job, the re-run.
- `backend/tests/test_pm_jobs_core.py`: the three changed tests; `job_override`, the override in the copies,
  `due_from_job`'s `rescheduled`.
- `backend/tests/test_pm_work_core.py`: the two changed tests; the S101 texts, `move_error`, `move_reason`,
  `reschedule_override` (moves, refusals, order, bad input), `reschedule_summary`.
- `backend/tests/test_pm_reschedule_api.py` (new): § 8.2.
- `backend/tests/test_pm_jobs_api.py`: the list item's exact shape gains `rescheduled`, `skipped` (D-1).

Frontend (8)
- `frontend/src/views/PmJobView.vue`: the card, the moved-from line, the skipped line, the history's
  "Rescheduled to …", the two dialogs; `cancelled` is `state === "cancelled"` only.
- `frontend/src/views/pm/PmJobRescheduleDialog.vue` (new).
- `frontend/src/views/pm/PmJobSkipDialog.vue` (new).
- `frontend/src/components/PmJobRow.vue`: the skipped row.
- `frontend/src/views/PmJobsView.vue`: `total_skipped` to `countText`; the Done tab's empty text.
- `frontend/src/utils/pmLabels.js`: the labels, badges and helpers.
- `frontend/tests/pmLabels.test.js`: the new cases.
- `frontend/e2e/pm-reschedule.spec.js` (new): the three automated checks.

Step docs: `docs/steps/S101-pm-reschedule-skip/1-brief.md` (Status), `docs/steps/INDEX.md` (Status), this
report.

## 4. Decisions taken

- **D-1 (forced, outside the brief's file list):** `test_pm_jobs_api.py::TestList::test_the_operator_sees_the_overdue_job`
  compares the whole list item, so it gains `"rescheduled": False, "skipped": None`. The file count is 20,
  not 19.
- **D-2 (a rule detail):** the created line's time carries the save's seconds, and a move's time is the
  minute (`to_minute`, as verify). A move in the job's first minute therefore sorts before the created
  line, and "the last computed line before the first move" would be none. `reschedule_summary` then takes
  the first computed line (the created line). Tested in the core and met by the API tests (a move right
  after the save).
- **D-3 (wording):** the meter values in `meter_not_above` and `meter_too_far` use
  `pm_plans_core.interval_number` (the house's grouping, "9,900 h"), not `meters_core.format_number`
  ("9900"), so the texts read as the brief's examples and as the page's due point.
- **D-4 (wording):** `jobSkippedText` adds no full stop after the reason ("Skipped 05-11-2026 14:20 by
  Priya: Machine idle all month"), the same as S099's `sentBackText`; the reason is shown as typed.
- **Helpers:** `pm_work._move_access` and `_move_reason` (one copy for both routes, beside S099's
  `_verify_access` and `_sign_off_remark`, whose state rule differs). `pm_jobs._SKIPPED_AND` holds the
  `total_skipped` condition. No new layer, flag or key.
- **The skip's next job** is settled with the skip's minute as `now` (the brief's `now`); *Mark job done*
  passes the unrounded time. The day is the same, so the result is the same.

## 5. Not done, deferred, assumed

- Nothing of the brief is left out.
- Assumed (A3): the tree is `refs/steps/S100` plus this step; no other step coded meanwhile.
- The reschedule recomputes all copies from the plan; if the meter was reset since the last run, the
  offset and windows on the job are brought up to date by the same write (as a run would do). Noted, not a
  change of rule.
- S102 (alerts) can read the moved point in `due_on` / `due_meter`; no other `pm_jobs` column changes.

## Manual checks

- [auto] An engineer reschedules a due job; the page and the list show the move — `frontend/e2e/pm-reschedule.spec.js`::`S101: an engineer reschedules a due job, and the page and the list show the move`
- [auto] An engineer skips a due job; it shows as Skipped on the Done tab — `frontend/e2e/pm-reschedule.spec.js`::`S101: an engineer skips a due job, and it shows as Skipped on the Done tab`
- [auto] The technician sees no Reschedule job or Skip job — `frontend/e2e/pm-reschedule.spec.js`::`S101: the technician sees no Reschedule job or Skip job`

On a real device: none (brief § 8.5); no row added to `docs/steps/device-checks.md`.

## Tests

Run name `s101c1`.

- Core red first: `test_pm_jobs_core.py` (ImportError on `job_override`) and `test_pm_work_core.py` (8
  collection errors) failed before the code, then passed (259 tests together).
- Targeted backend while coding: the PM modules, migrations v52–v55 and `test_rbac.py`: 384 passed, after
  D-1's shape fix; `test_pm_reschedule_api.py` 22 passed.
- **Full unit suites** (`tooling/run-tests.bat`, once): backend PASSED 5241 passed (165 s); frontend
  PASSED 458 passed; tooling PASSED 239 passed (the line-width test included).
- `npx vite build`: clean (only the known chunk-size note).
- Browser, the new spec alone (`E2E_LANES=1`, `phone-chromium`, `-g S101`): 3 passed.
- Browser, targeted (`pm-reschedule`, `pm-job`, `pm-jobs`, `pm-verify`, `pm-plans`, `screens`): 60 passed,
  1 skipped (a skip that was there before).
- **Browser whole suite at Normal** (once): 434 tests, 419 passed, 15 skipped, 0 failed (223 s).
- `tooling\schema-docs.bat check`: exit 0 (4 passed, migration v55).

## Docs updated

- `docs/schema/notes.json`: the `pm_jobs` line gains `rescheduled_on`, `rescheduled_meter` and the skipped
  job's columns; the `pm_job_events` line gains `rescheduled`, `skipped` and the drop's `due_changed` line.
- `docs/schema/schema.json`, `docs/schema/schema-data.js`: regenerated by `tooling\schema-docs.bat write`
  (migration 55; the two columns and `chk_pm_jobs_rescheduled`); diff read against `refs/steps/S100`.
- `docs/Plan.MD` § 4.3: *Rescheduling* is "Built, S101" with D1–D6 in one paragraph and D3's departure
  (earlier moves allowed); the PM job's state diagram gains `skipped` from `due`.
- `docs/Maintenance-Philosophy.md`: *Rescheduling* loses "(**Proposed**)" and gains the "Built (S101)"
  sentence.
- `.claude/CLAUDE.md` § SMTW-Review: the point *PM reschedule and skip (S101)* (brief § 8.6), word for word.
- `docs/steps/device-checks.md`: none, because the step has no real-device check. `docs/Keycloak.md`: none,
  because no role, client or claim changed.

## Feedback

- hindrance: `tooling\run-backend-tests.bat` with a missing test file (`tests/test_role_matrix.py`, the
  name CLAUDE.md's self-check item (5) and brief § 8.3 use; the test lives in `test_rbac.py`) printed only
  "no tests ran", not which file was missing (1 run, 1 min).
- idea: brief § 8.3 could list every test that compares the whole list item or page answer
  (`test_pm_jobs_api.py::TestList::test_the_operator_sees_the_overdue_job`), so a new field's forced test
  change is planned and not a surprise.
- waste: a background run ended with no notification arriving between turns, so I waited with an
  `until` loop on the summary file (no time lost, one extra call).

## Fix rounds

### Round 1

- **CR1-01 (major): Fixed.** In `change_plan` (`backend/pm_plans.py`) the plan-level flag
  `schedule_changed = any(field in changes for field in SCHEDULE_FIELDS)` is now computed from the plan's own
  `changes` before the item loop, and the loop variable is `item_changes`. `settle_plan_job` gets
  `keep_reschedule=not schedule_changed`. No other place in `pm_plans.py` reads `changes` after the loop (checked
  with grep: lines 448-450 only).
  Two new tests in `backend/tests/test_pm_reschedule_api.py::TestReschedule`:
  - `test_a_schedule_change_saved_with_an_item_edit_still_drops_it` (`calendar_every` plus an item text edit in one
    save: the reschedule is dropped, with the `due_changed` / `RESCHEDULE_DROPPED` line).
  - `test_an_item_only_edit_keeps_it_also_a_reading_items_meter` (an item text edit plus a reading item's meter
    change, no schedule change: the reschedule stays, no new line).
  Red without the fix: the first fails with `assert datetime.date(2026, 11, 12) is None` (reschedule kept); the
  second fails with `AttributeError: 'NoneType' object has no attribute 'isoformat'` (reschedule dropped). Both
  were run before the fix was written. Green with it: both pass.
- **CR1-02 (nit): Fixed.** `frontend/e2e/pm-reschedule.spec.js` skip test now asserts
  `toContainText(/\b[1-9]\d* skipped\b/)` on `pm-counts`.
- Runs (`YANTRA_TEST_RUN=s101f1`): `tooling/run-backend-tests.bat tests/test_pm_reschedule_api.py
  tests/test_pm_plans_api.py tests/test_pm_generate.py`: 89 passed. `tooling/run-e2e-tests.bat
  e2e/pm-reschedule.spec.js e2e/pm-plans.spec.js`: 15 passed. Python lines at most 120. No migration or doc is
  touched, so no docs update is due.

### Feedback

- none
