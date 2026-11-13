```
Step: S098 — Do the PM job on the phone
Doc: code-review
Round: 1
Author: Code reviewer (Opus)
Date: 02-11-2026
Verdict: no blocker or major finding open; 1 minor, 4 nits
```

# S098 — code review, round 1 (the backend)

**Verdict: no blocker or major finding is open.** This round covers the backend only:
snapshot round 1 (`refs/step-rounds/S098-1`), the diff `git diff refs/steps/S097
refs/step-rounds/S098-1 -- backend docs .claude`. The screens, the frontend tests and the browser
tests follow in round 2, and this review judges none of them. One minor finding: a reading item
whose meter is gone since *Start* keeps its old link, so a later *NA* breaks a CHECK and answers
500.

**Tests (my run, `YANTRA_TEST_RUN=s098cr1`):** `tooling/run-backend-tests.bat
tests/test_pm_work_core.py tests/test_pm_work_api.py tests/test_migration_v53.py
tests/test_pm_jobs_api.py tests/test_pm_jobs_core.py tests/test_pm_generate.py
tests/test_readings_api.py tests/test_meters_api.py`: **PASSED, 360 passed in 41 s**. Before the
run I checked that the working tree's backend files match the snapshot (`pm_work.py`,
`pm_work_core.py`, `pm_jobs.py`, `pm_jobs_core.py` are byte-equal apart from line endings). I made
no browser run and no schema docs check: the orchestrator asked for neither, and no finding needs
one. The coder's whole backend run (5082 passed) and the tooling run (239 passed) are recorded in
the report § 6.

## Findings

### CR1-01 (minor) — a meter gone since *Start* keeps the result's old reading link; a later *NA* answers 500

`backend/pm_work.py:330-332` (`_log_reading`), with `backend/pm_work.py:386-393` (`save_result`)
and the CHECK `chk_pm_job_results_reading` (`backend/local_db.py`, v53).

**Problem.** When the item's meter is no longer in force, `_log_reading` returns the result's
current `reading_id` unchanged. The brief's § 5.5 step 1 says exactly that ("`reading_id` stays as
it is"). But the result's value may change in the same save, and two faults follow:

1. **NA breaks a CHECK.** `chk_pm_job_results_reading` holds `reading_id IS NULL OR (value IS NOT
   NULL AND …)`. An *NA* save sets `value` NULL and keeps `reading_id`. MariaDB refuses the UPDATE
   with 4025. PyMySQL raises it as an `OperationalError`, and `api_common._operational_error`
   answers a plain 500.
2. **A changed value keeps a stale link.** The result keeps naming the old reading, which stays
   active with the old value. `logged` stays true. After a reload the page says the value is also
   logged on the meter, and the meter history holds a different value. D4 exists to stop the job
   and the meter from disagreeing.

**Failure scenario.**
1. A technician saves 1,270 on a *Run hours* item. The reading is logged, and `reading_id` = R.
2. An engineer removes the meter from the node, or from the model.
3. The technician sees the meter glass is misted and taps *NA* with a remark.
4. The save answers 500 "something went wrong", and the item cannot be set to *NA*. The other
   path: he types 1,275 instead. Then the job shows 1,275, "logged", and the meter keeps 1,270.

The test `test_a_meter_removed_after_start_keeps_the_value_on_the_job` removes the meter before
the first save, so `reading_id` is still NULL and neither case is reached.

**Suggested fix.** In `_log_reading`, remove the job's own `pm` reading (step 3) **before** the
meter-in-force check. `remove_reading_row` needs only the node and the meter type, not a meter in
force. Then, when the meter is gone, return `(None, not_logged(…))`: the result lets go of the
reading, as it does for a `manual` one. Add one API test: a value logged, the meter removed, then
*NA*. It must answer 200, with `reading_id` NULL and the old reading removed; also a changed value
with `logged` false. This changes the brief's § 5.5 step 1 wording ("`reading_id` stays as it is"),
so record it as a stated decision of the fix round.

## Nits

- **CR1-02** (nit) `backend/pm_work.py:373`: `meters.lock_node` runs before `_work_access`. So a
  stale item `PUT` on a done job whose machine was scrapped later answers `SCRAPPED_MESSAGE`, not
  `JOB_DONE`. Both are 409. Either accept the difference and state it in the LOCK ORDER note, or
  take the lock with `for_update` but without its scrapped refusal on this path.
- **CR1-03** (nit) `backend/pm_jobs.py:110`, `:362`: `plan.item_count` in the list item counts the
  plan's active items now. For a started job this can differ from the job's own copied results
  (the test `test_a_plan_edit_leaves_a_started_job_as_it_is` makes 4 against 3). Round 2's row
  should not show it as the job's count for a started job. The job page's `item_count` is right.
- **CR1-04** (nit) `backend/pm_work.py:302`, `:416`, `:458`: D-c6 calls the private
  `pm_jobs._add_event` from another module. The brief allowed this only for `_now` (BR1-08, for the
  monkeypatch). Make it public (`add_event`), or name it in the brief's list of `pm_jobs` imports.
- **CR1-05** (nit) report § 4, last bullet: the core's tests were not shown red first, against the
  brief's § 8.2 "written first". The CLAUDE-COMMON rule ("write and green the core's unit tests
  before building the API") still holds: the core was green before the shell existed. The 66
  tests cover every row of § 5.4 and § 5.2, so I accept the departure as stated. No re-run is
  needed.

## The departures D-c1 … D-c10

| ID | Judgement |
|---|---|
| D-c1 `JOB_FROM`, `job_item` public | Accepted. One copy of the item shape for the list, the *Done* tab and the page (DRY); `days_past` None for a done job is right. |
| D-c2 the counts leave the started jobs out | **Accepted, and flag it for KLA at gate B.** The brief said only "`counts` gains `in_progress`". The coder's reading makes "n due · n overdue · n in progress" add up to the *Due* tab's rows, and no started job counts twice. The consequence to state: `counts.overdue` no longer counts a started job that is past its due point. Today only `pmLabels.countText` reads the counts, and no badge or report counts overdue jobs from this answer. R03.14's compliance report must count from the stored rows, not from these tab counts. |
| D-c3 `remove_reading_row(…, field=None)` | Accepted. The readings route passes no field, as before (`test_readings_api.py` green). |
| D-c4 `reading_at_minute` returns the row | Accepted. `write_reading` still refuses the same minute on `taken_at` (SAME_MINUTE), as before. |
| D-c5 `write_reading` takes the raw value | Accepted. The value is checked twice by the same `validate_reading` rules; the second check cannot refuse what the first passed. |
| D-c6 events through `pm_jobs._add_event` | Accepted in substance; the name is CR1-04. |
| D-c7 a check's *NA* needs no remark | Accepted: it is the brief's own rule (§ 1 item 2, § 5.4's table, § 8.2), not a departure. |
| D-c8 the result `UPDATE` written in `pm_work.py` | Accepted. `pm_job_results` has no `updated_at` / `updated_by`, which `update_row` stamps. The column names come from code constants (`_COMPARED`, `reading_id`, `filled_at`, `filled_by`), never from the client. |
| D-c9 test helpers moved to `test_pm_generate.py` | Accepted; the coder's idea of a `tests/pm_helpers.py` is worth a later step. |
| D-c10 the scrap test on the machine | Accepted. A part is scrapped before its machine, so the count over the parts is kept, with the same ids as the tickets' check. |

## The points the orchestrator named

- **`meters.log_reading` split (S039).** `log_reading` still takes `lock_node(…, "reading:log")`
  as its first statement, then `meter_in_force`, then `write_reading(…, "manual")`. The insert now
  names `source` explicitly; before, it took the column's default `'manual'`. So the stored row is
  the same, and the answer is the same `reading_out`. `write_reading` is the only `INSERT INTO
  meter_readings` in the backend; the PM path calls it. Both neighbours are checked in
  `write_reading` (`counter_error` with `_neighbour` before and after), unchanged. The PM path
  takes (6e), (6f), then the meter's node FOR UPDATE through `lock_node`, before any plain read
  (`_now` reads no table). `test_the_save_waits_for_the_node_lock_and_sees_the_reading_before_it`
  proves the wait and the fresh snapshot. `remove_reading` keeps its 404 and `ALREADY_REMOVED`
  checks and calls `remove_reading_row`. `test_readings_api.py` and `test_meters_api.py` ran
  unchanged and green.
- **Lock sequences.** Start: (6e) → (6f) → the node shared → plain reads. An item: (6e) → (6f) →
  the meter's node FOR UPDATE (only for a result with a meter) → plain reads. The performer: (6e) →
  (6f) → plain reads. Done: (6e) → (6f) → the node shared → plain reads → `settle_plan_job`, which
  takes (6) last. These match the LOCK ORDER notes of `pm_work.py`, `equipment.py` ((6f) added)
  and `pm_jobs.py`, and S097's "plan first, then job". I found no path that holds a job or a node
  and then waits on a plan. The pre-read runs on an autocommit connection before `transaction()`
  (`db_helpers.transaction` calls `conn.begin()`; `local_db` sets `autocommit: True`), so it is its
  own snapshot.
- **Migration v53.** It matches § 4.1 statement for statement: the three statements and every
  `IF NOT EXISTS`. The CHECKs hold for S097's existing rows (due and cancelled, the new columns
  NULL), so no `_PRECONDITIONS` entry is needed, and the v52-to-v53 test proves it.
  `chk_pm_jobs_started` and v52's `chk_pm_jobs_done` both hold for Start's UPDATE and Done's
  UPDATE. `meter_readings.source` already lists `pm` (v32's ENUM). The ENUM test compares
  `information_schema` with the cores' constants.
- **`pm_job:work` scoping.** `("maint_technician",)`, in `SITE_SCOPED`. Every write has
  `require_perm(WORK_KEY)` (the union), then `load_node_for_user(…, key=WORK_KEY)`, which gives 404
  outside the units and 403 without the key at the node's site. `can_start` and `can_work` use
  `has_perm_at` at the job's node's current site. IT admin and the operator get 403, and the tests
  show it.
- **Start's copy.** `result_rows` copies every S096 column, `photo` included, from the active items
  in `position, id` order under (6e). The unique keys `(job_id, plan_item_id)` and
  `(job_id, position)` back it. A double tap waits on (6e), then reads `in_progress` and answers
  409 `ALREADY_STARTED`. A node scrapped since the job was made answers 409 from the locked row.
- **The per-item save.** `result_changes` returns `{}` for a repeated body, so nothing is written
  and nothing is logged. A remark-only change logs no reading. The job removes a reading only when
  its `source` is `pm` and it is active. A same-minute reading with the same value and reset mark
  is linked; with another value or mark the save is refused with 409 `SAME_MINUTE_PM` on `value`.
  A refused counter value raises inside the transaction, which rolls back the earlier removal too
  (D4). The open fault is CR1-01.
- **Mark done.** The state check comes first, then the unfilled count. `done_meter` is
  `last_readings(…, until=done_at)` (at or before), else `first_reading_after`, else None, on the
  locked plan's meter. `timeliness` is `pm_schedule_core.timeliness(due_from_job(job), …)` over the
  locked job's own due point, with the stored `meter_offset`; it is `NOT NULL DEFAULT 0`, so
  `done_meter_counted` never meets None. The stored due point is the job's (S095 N1). After the
  update, `settle_plan_job` runs on the plan; it sees the job's new state, as its own write.
- **The 7-day window.** `TIME_TOO_OLD` and `job_time_error` use
  `meters_core.READING_BACKDATE_DAYS` itself, for *Started* and *Done*, admin included.
- **Remarks.** They are needed for `not_ok`, `not_done` and a reading's `na`, trimmed, and at most
  500 characters; a remark that is not text is refused.
- **Scrap refusal.** `_check_no_started_pm_jobs` counts `in_progress` jobs on the node and its
  parts, with the same ids and under the same locks as `_check_no_open_tickets`. It is the only
  scrap path (`update_equipment`).
- **S097 changes.** `settle_plan_job` is unchanged: `decide` returns None for `in_progress`, and
  the plan-edit, deactivation and two-run tests prove it. The *Done* tab uses `_DONE_SELECT` with
  the same joins and filters, `BASE_STATES`, `done_at DESC, id DESC`, paged, with a `COUNT(*)`
  total. `counts` always comes from the open jobs (D-c2). `assigned=me` is
  `(assignee OR performer)`. `tab_of` and `list_order` put started jobs on *Due*, first.

## Docs pass

The `## Docs updated` section of round 1 matches the diff:

- `docs/schema/notes.json`: `pm_job_results` moved from `planned` to `tables`, and the area note
  and the `pm_jobs` and `meter_readings` lines are updated. `schema.json` and `schema-data.js` are
  regenerated and name migration 53.
- `docs/Plan.MD`: § 3 has the `pm_job:work` paragraph with the departure; § 4.3 has *Built
  (S098)*.
- `.claude/CLAUDE.md`: *Self-check* (2) names `pm_work.py`; § SMTW-Review gains *Meter readings*
  with the PM path, and the new point *PM job results (S098)*.

Plan.MD § 2 (8) and § 6, and `docs/steps/device-checks.md`, are stated as round 2's work. That is
correct, because they describe the screens. `docs/Keycloak.md` needs no change. I ran no schema
docs check: the orchestrator excluded it for this round, and the gate B check covers it.

## Manual checks

This is the backend round, so there is nothing new for the user's manual browser check. The
report says `## Manual checks` comes with round 2; round 2's review checks that it carries every
important check of the brief.

## Checked and found consistent

- No actor is taken from the client. `actor()` comes from the token. `performed_by_id` is a person
  chosen by design (recorded on behalf) and checked with `person_at_site` at the node's site.
- No SQL is built from client strings. The dynamic `UPDATE` and `IN (…)` parts use code constants
  and `marks()`.
- The database down: every route goes through `get_db()`, and `test_the_database_down` gets 503
  for GET and Start. No exception is swallowed.
- The pure core imports only pure modules (`meters_core`, `pm_jobs_core`, `pm_plans_core`,
  `tickets_core`). It has no DB, no clock and no Flask, and it raises `TypeError` / `ValueError`
  on shell bugs. `equipment.py` imports only pure cores for its check, so there is no cycle.
- The import direction: `pm_work.py` imports `pm_jobs` and `meters`; nothing imports `pm_work`
  except `app.py`.
- The tests cover the brief's § 8.1–§ 8.3 lists, including the failure modes: the refusals per
  field, the state table, the lock test, the clock fix, and the plan and run rules for a started
  job.
- The screen text in the backend messages follows style B: what is wrong and what to do. It keeps
  the house shapes of `close_tickets_first` and `PERSON_AT_SITE`.
- `Track: full`, as the step needs (a migration, a new key, a shared reading path).

## Feedback

- hindrance: `git diff --stat refs/step-rounds/S098-1 -- backend`, my check that the working
  tree's backend matches the snapshot, lists the step's untracked new files as 6,493 deleted
  lines. I compared four files with `git show … | diff` instead. A `step_snapshot.py` mode
  "working tree against round N" would answer this in one call (1 extra command, 2 min).
- idea: the orchestrator's spawn prompt names the exact diff and the test files, which saved a
  `--stat` pass and a full-suite run. Make that the template for split-round reviews (this run).
