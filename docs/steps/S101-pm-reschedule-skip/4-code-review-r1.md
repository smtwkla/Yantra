```
Step: S101 — Reschedule and skip a PM job
Doc: code-review r1
Author: code reviewer (Opus)
Date: 02-11-2026
```

# S101 — Code review, round 1

**Verdict: one `major` finding is open (CR1-01).** A plan save that changes an item reads the item's changes in
place of the plan's changes, so D4 (a schedule edit drops the reschedule) fails both ways. The rest of the step
follows the brief. All unit suites and the schema docs check are green.

## Tests run

- `YANTRA_TEST_RUN=s101cr1 tooling/run-tests.bat`: backend PASSED 5241 passed (151 s); frontend PASSED 458
  passed; tooling PASSED 239 passed (the line-width test included).
- `YANTRA_TEST_RUN=s101cr1 tooling\schema-docs.bat check`: exit 0, "Schema docs at migration v55: 4 passed".
  It ran after the unit suites, not beside them.
- Browser: none re-run. CR1-01 is a backend fault with no screen of its own, and its regression test is a
  backend test. The coder's runs are the right ones: the new spec alone, the targeted run (`pm-reschedule`,
  `pm-job`, `pm-jobs`, `pm-verify`, `pm-plans`, `screens`: 60 passed, 1 skipped) and the Normal whole suite once
  (419 passed, 15 skipped, 0 failed). The step changes no shared frontend file, so no WebKit run is due.

## Findings

### CR1-01 (major) — `backend/pm_plans.py:452-459`: the item loop overwrites `changes`, so D4 reads the wrong dict

**The problem.** `change_plan` computes `changes = plan_changes(locked, clean)` (line 447), then loops
`for item_id, changes in ops["update"]:` (line 452), which rebinds the same name to the last changed item's
fields. The call `settle_plan_job(..., keep_reschedule=not any(field in changes for field in SCHEDULE_FIELDS))`
(line 459) then tests the item's changes, not the plan's. `sync_items` puts an item in `ops["update"]` whenever
a field or its position differs. `PmPlanView.vue` sends `items` with every save (its field list, line 93), so a
save that edits the schedule and one item is an ordinary edit.

**Failure scenarios.**
1. *Reschedule kept after a schedule change.* An engineer moved a meter job to 1,300 h. Later he changes the
   plan's meter from run hours to strokes and, in the same save, fixes a typo in one item. `changes` is now
   `{"text": …}`, so `keep_reschedule` is True. The job keeps `rescheduled_meter` 1,300 against the strokes
   meter, with no `due_changed` line. This is the wrong-scale value D4 exists to prevent.
2. *Reschedule dropped with no schedule change.* An engineer changes only a reading item's meter (an item's
   `meter_equipment_id` / `meter_type_id`). These names are also in `METER_FIELDS`, and so in `SCHEDULE_FIELDS`.
   The reschedule is dropped, and the job's history says "The plan's schedule was changed, so the job's
   reschedule no longer applies." The schedule did not change.

The API tests did not catch it: `test_a_title_change_keeps_it_and_a_schedule_change_drops_it` and
`test_a_schedule_change_that_keeps_the_due_point_still_drops_it` save no items.

**Suggested fix.**
1. Compute the flag once, before the item loop, from the plan's changes (e.g.
   `schedule_changed = any(field in changes for field in SCHEDULE_FIELDS)` next to `update_row`), or rename the
   loop variable (`item_changes`). Doing both is clearest.
2. Add two API tests to `test_pm_reschedule_api.py`, each red before the fix (the *Red, then green* rule):
   - one save that changes `calendar_every` and the text of the plan's item drops the reschedule, with the
     `RESCHEDULE_DROPPED` line;
   - one save that changes only an item (its text, or a reading item's meter) keeps the reschedule and writes
     no line.

## Nits

- **CR1-02** (nit) `frontend/e2e/pm-reschedule.spec.js:86`: `toContainText("skipped")` also passes on the empty
  text "No PM jobs are done or skipped yet."; assert the count part instead, e.g. `toHaveText(/\b\d+ skipped$/)`.

## The coder's decisions

- **D-1** (the list item's exact shape in `test_pm_jobs_api.py`): accepted. The new fields force it, and the
  report lists the extra file.
- **D-2** (`reschedule_summary` falls back to the first computed line): accepted. `now = to_minute(...)` is the
  brief's rule (§ 5.3), so a move in the job's first minute sorts before the created line, and the fallback gives
  the right "Moved from". A side effect remains: in that minute the *History* card lists *Rescheduled* or
  *Skipped* above *Created*, as S099's minute-rounded lines already do. That is not a finding.
- **D-3** (`interval_number` in the two meter messages): accepted. The brief's own examples read "9,900 h", and
  the page's due point uses the same grouping. The departure from the brief's `format_number` is listed.
- **D-4** (no full stop after the skip's reason): accepted. It matches S099's `sentBackText` and shows the
  reason as typed.

## Manual checks

The impl report's `## Manual checks` carries the three automated checks of § 8.4 as `[auto]`, each with its test
in `frontend/e2e/pm-reschedule.spec.js`, and the coder's whole-suite run passed them. The brief has no real-device
check (§ 8.5), and `docs/steps/device-checks.md` correctly has no new row.

**For the user's manual browser check** (optional; no device-only check): on a phone, open a due PM job as an
engineer and check the following:
- the two buttons of *Reschedule or skip* fit in one row;
- the phone's own date picker opens from *New due date*.

## Checked and found consistent

- **Migration v55** (`backend/local_db.py`): appended after v54. It uses `ADD COLUMN IF NOT EXISTS` and
  `ADD CONSTRAINT IF NOT EXISTS`, and needs no precondition (every row gets NULL). The CHECK
  `(x IS NULL OR x <=> due_…)` refuses a set value against a NULL due point (`<=>` gives 0, not NULL), which the
  plain `=` would let pass. `test_migration_v55.py` covers the columns, the types, both ways of the CHECK with
  the meter-only job (BR1-10), a v54 database with a due, a done and a skipped job, and the re-run.
- **Schema docs:** `notes.json` names both columns and the two events. `schema.json` and `schema-data.js` are
  regenerated at migration 55, and `check` exits 0.
- **The override through S095's core:** `next_due(..., override)` takes the moved value and keeps the computed
  windows (S095 D5). `job_override` keeps only the triggers the plan's kind still has, and `due_copies` rounds
  `rescheduled_meter` as the other meter columns, so `job_changes` compares like with like. A rescheduled
  open job stays `REFRESH` in `decide` at every standing, so a job moved far ahead is not cancelled.
- **`settle_plan_job(..., *, keep_reschedule=True)`:** keyword-only. The run's positional call and
  `test_pm_generate.py`'s wrapper are unchanged. `_refresh` writes `due_changed` with `RESCHEDULE_DROPPED` when
  only the override columns change (tested). The fault in its caller is CR1-01.
- **The skip as the next job's base:** `SKIPPED` is in `BASE_STATES`. `done_at` is the skip's minute and
  `done_meter` comes from `_done_meter`. `timeliness` and `needs_verification` stay NULL, which
  `chk_pm_jobs_done` and `chk_pm_jobs_verification` require. The daily, monthly and meter cases are tested
  (next job at once, a month from the skip, 1,480 h).
- **The bounds (D3) and their refusals:** the date uses `tickets_core.planned_date_error` (one copy). The meter
  must be above the counted reading and at most one interval past it. Equal values are no move. The order is
  parse, moved, nothing moved, bounds, then the reason. Each message is one plain line, says what to do, and
  shows beside its field (`fieldError` on `due_on`, `due_meter`, `remark`).
- **Locks:** both routes take (6e) the plan, then (6f) the job, then (1) the node shared, then `SELECT NOW()`,
  then plain reads. The skip's `settle_plan_job` takes the PM counter (6) last, as *Mark job done* does. The
  LOCK ORDER notes of `pm_work.py` and `pm_jobs.py` carry both sequences. The lock test holds the plan row on a
  second connection and shows the skip waits.
- **`pm_job:verify` scoping:** `require_perm(VERIFY_KEY)` (403 for the technician and IT admin), then
  `load_node_for_user(..., key=VERIFY_KEY)` (404 outside the units, 403 without the key at the site). The key is
  in `SITE_SCOPED`. `can_skip` and `can_reschedule` use `has_perm_at(VERIFY_KEY, site)`. The manager inherits
  the key (tested). No actor comes from the client. All SQL is parameterised; the only f-strings hold
  constants.
- **What the reschedule writes:** only `pm_jobs` columns that `due_copies` produces (the due point, the windows,
  the offset and the two override columns). The assignee is passed unchanged. The moved point is in `due_on` /
  `due_meter`, as S102 § 5.2 reads it, and the CHECK enforces that.
- **The answer and the list:** `job_item` gains `rescheduled` and `skipped`, and `add_sign_off` fills `skipped`
  with one query for the page. `_DONE_WHERE` includes `skipped`, by `done_at` newest first. `total_skipped`
  uses the same filters and is 0 in the empty answer (tested with the unit filter and on *To verify*).
- **Frontend:** both dialogs use FormModal and `useFormModal` (S099's pattern): `blank()` reads the job at each
  open, `closed` hands the saved job to the page, and a 409 reloads it. Titles equal the save labels. The skip
  dialog states its consequence and "You cannot undo this.". *Skip job* is `btn-outline-danger`, on the left,
  apart from *Reschedule job*. Both dialogs call `expectDialogFits` in their flow tests. The tests are untagged,
  which is right for logic tests. `countText` leaves out a zero part. The technician's page has no card (tested).
- **Scope:** everything in the brief is built, and nothing beyond it. The coder's four decisions are listed in
  the report.
- **Docs pass:** `Plan.MD` § 4.3 (Built, D1–D6, D3's departure, `skipped` in the state diagram),
  `Maintenance-Philosophy.md` *Rescheduling*, and the `.claude/CLAUDE.md` § SMTW-Review point word for word.
  `device-checks.md`, `Keycloak.md` and `example_secrets_app.py` need no change.
- **Tests:** the core tests cover each function's rules and bad input. The API tests cover § 8.2's list: moves,
  run and save, on time, every refusal, before-use, the skip, *Done*, the lock, the identity and the database
  down (503).

## Feedback

- idea: CR1-01 is a reused local name (`changes`) that brief review, coding and 5241 green tests all passed. The
  brief prescribed "`changes = plan_changes(locked, clean)` (computed once, as now)" without seeing the item loop
  below that reuses the name. A brief that names a new local variable in an existing function could check that
  the function does not use the name already (`backend/pm_plans.py:447/452`).
