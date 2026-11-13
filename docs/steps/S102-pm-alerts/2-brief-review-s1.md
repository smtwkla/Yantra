```
Step: S102 — PM alerts: job due, job overdue
Doc: brief-review s1
Author: Brief reviewer (Fable)
Date: 02-11-2026
```

Reviewed against: c9cd091 + uncommitted S095, S096, S097, S098, S099, S100, S101 (snapshot `refs/steps/S101` = 2ec75b6; the working tree equals it in every backend file the brief names: `pm_jobs.py`, `pm_jobs_core.py`, `pm_work.py`, `pm_work_core.py`, `pm_plans.py`, `local_db.py`, `equipment.py`, `alerts_core.py`, `alerts.py`, `task_handlers.py`, `scheduled_tasks.py`)

**Verdict: no blocker or major finding is open.** Staleness mode, one question only: does each statement of the brief about the code still hold after S101? The design holds as approved. One `minor` (a KeyError the coder would otherwise resolve alone) and four nits (wording and test lists). No facts file was given for this round; I read the S100→S101 diff and the files as they stand.

S101's code review r1 runs now. If its fix round changes `pm_work._lock_job`, `pm_jobs.JOB_FROM`, `pm_jobs_core.due_from_job`, `job_changes` or migration v55, those five names are the only ones to re-check; nothing else in this brief depends on S101's code.

## What S101 changed that the brief touches

Fact, from `git diff refs/steps/S100 refs/steps/S101`:

- v55: `pm_jobs.rescheduled_on DATE NULL AFTER meter_offset`, `rescheduled_meter DECIMAL(14,3) NULL AFTER rescheduled_on`, and `chk_pm_jobs_rescheduled` (each, when set, `<=>` its due column). Column order now: … `meter_offset`, `rescheduled_on`, `rescheduled_meter`, `assignee_id`, `done_at`, `done_meter`, `timeliness`, `needs_verification`, `open_plan_id`, …
- `pm_jobs_core`: `BASE_STATES = (DONE, VERIFIED, SKIPPED)`; `due_copies(due, offset, override=None)` adds `rescheduled_on` / `rescheduled_meter` to the copies; `due_from_job(job)` reads `job["rescheduled_on"]` and `job["rescheduled_meter"]` for `Due.rescheduled`; new `job_override`, `RESCHEDULE_DROPPED`.
- `pm_jobs`: `settle_plan_job(…, *, keep_reschedule=True)`; `schedule_inputs(cur, plan, now, override=None)`; `_refresh` writes a `due_changed` line also when only the reschedule is dropped; `JOB_FROM` gains `pl.trigger_kind AS pl_trigger_kind`; `job_item` gains `rescheduled` and `skipped`; `jobs_out` unchanged.
- `pm_work`: two routes, `POST /jobs/<id>/reschedule` and `POST /jobs/<id>/skip`, both through `_lock_job` (`LOCK_PLAN` then `_LOCK_JOB`, unchanged) and `_answer` → `job_detail` → `_job_row`; `job_detail` adds `can_skip`, `can_reschedule`, `reschedule`.
- `pm_plans.change_plan` passes `keep_reschedule=not any(field in changes for field in SCHEDULE_FIELDS)`.
- The LOCK ORDER notes of `pm_jobs.py` and `pm_work.py` each gain an S101 bullet; `.claude/CLAUDE.md` § SMTW-Review gains *PM reschedule and skip (S101)*.

## Findings

### BS1-01 — minor — § 5.3 and § 8.1: `job_standing`'s job must carry the two reschedule columns

**Problem.** § 5.3 defines `job_standing(job, latest_value, today)` as `job_state(due_from_job(job), …)`. Since S101, `due_from_job` reads `job["rescheduled_on"]` and `job["rescheduled_meter"]` (`backend/pm_jobs_core.py`, `due_from_job`). § 8.1's unit test ("a meter job at reading 1490, offset 20, due 1500, window 50 → *Due*") builds its job as a dict; without those two keys the call raises `KeyError`.

**Why it matters.** The coder meets the error and must choose alone: add the keys to the test dicts, or make `due_from_job` tolerant (`job.get`), which would hide a missing column on a real row. The scan itself is safe: its job comes from `LOCK_JOB` (`SELECT *`), which has every column.

**Options.**
- (a) **Recommended.** § 5.3 says the job is a full `pm_jobs` row (it has `rescheduled_on` and `rescheduled_meter` since S101); § 8.1's test dicts carry both keys as `None`, as `test_the_copies_take_the_column_s_three_decimals` in `backend/tests/test_pm_jobs_core.py` does. `due_from_job` stays strict.
- (b) `due_from_job` uses `job.get(...)` for the two columns. Rejected: a strict read is what catches a query that forgot a column.

### Nits

- **BS1-02** (nit) § 5.2 "What S101 must do", § 9 A2 and "A staleness check is due", § 4.1 "the staleness check confirms it": S101 is coded, so write these as verified facts. `pm_work.reschedule_job` writes `update_row(cur, "pm_jobs", job_id, job_changes(job, due_copies(inputs["due"], inputs["offset"], override), job["assignee_id"]), actor())`: the due copies and the two reschedule columns, never the four markers (`job_changes` compares only the keys of `copies` plus `assignee_id`). `skip_job` writes `SKIP_CHANGES` (`state = 'skipped'`), `done_at` and `done_meter`, then `settle_plan_job`. v55 is S101's (the two columns and `chk_pm_jobs_rescheduled`); v56 stands, and `AFTER needs_verification` places the four markers between `needs_verification` and `open_plan_id`.
- **BS1-03** (nit) § 5.2 table: add two rows S101 made real. (1) A plan save that changes a schedule field (`pm_plans_core.SCHEDULE_FIELDS`) calls `settle_plan_job(…, keep_reschedule=False)`, so `_refresh` drops the reschedule and `due_on` / `due_meter` go back to the computed point (the `due_changed` line with `RESCHEDULE_DROPPED`): the markers hold the rescheduled point, so both alerts re-arm for the computed one; a save that keeps the reschedule moves no due point, so nothing. (2) A skip settles the plan's next job in the same transaction (`skip_job` → `settle_plan_job`); the new job has NULL markers and alerts at its own due point. Both follow the rule as written ("only `due_on` and `due_meter` compare"); the rows only make the coder's test list complete.
- **BS1-04** (nit) § 8.3 "Run whole": add `backend/tests/test_pm_reschedule_api.py` (S101's routes go through `_lock_job`, `_LOCK_JOB` and `_job_row`, which S102 moves). `backend/tests/test_pm_jobs_api.py` `TestList` now compares the whole item, with `rescheduled` and `skipped` (S101 D-1); S102 adds no item field, so it stays green as the brief says.
- **BS1-05** (nit) § 5.6 step 2, `JOB_FROM`'s columns: add `pl_trigger_kind` (S101). The sentence "`trigger_kind` is not read" (BR1-06) stays true as a choice: the row now carries it, and `pm_job_facts` still follows the values.

## Checked and found consistent

- `pm_work.py`: `_LOCK_JOB = "SELECT * FROM pm_jobs WHERE id = %s FOR UPDATE"` (line 122), `_job_row` (line 218: `pm_jobs.JOB_FROM + " WHERE j.id = %s"`), `_lock_job` (line 288), `job_detail` (line 223) are as the brief describes; S101's two routes call `_lock_job` and `_answer`, so § 3's move (`_LOCK_JOB = pm_jobs.LOCK_JOB`, `_job_row` → `pm_jobs.job_row`) serves them with no further change.
- `pm_jobs.jobs_out` (line 366) still has exactly the two lines § 5.3 names (`value = None if reading is None else reading["value"] + row["meter_offset"]`, `standing = job_state(due_from_job(row), value, today)`), keyed on `(meter_equipment_id, meter_type_id)` from `last_readings(cur, node_ids, until=None)`; `job_standing` extracts them one to one.
- `pm_jobs.READ_KEY` (line 89), `LOCK_PLAN` (line 92), `_now` (line 147), `plan_schedules` (line 530), `job_item` (line 387: field by field, the four markers never in it; S101 added `rescheduled` and `skipped`, not the markers).
- `pm_jobs_core.DUE_STATE`, `BASE_STATES` with `SKIPPED`: § 5.1's first row (`state != DUE_STATE` → `None`) already covers a skipped job; `BASE_STATES` is not read by S102.
- `pm_work_core.VERIFY_KEY = "pm_job:verify"` (line 56); `pm_schedule_core.job_state`, `DUE`, `OVERDUE`; `meters_core.format_number`.
- v56 `AFTER needs_verification`: valid, the markers land before `open_plan_id`; `_mark_alerted` touches no column of `chk_pm_jobs_rescheduled` or `chk_pm_jobs_windows`.
- `backend/tests/test_migration_v55.py` follows the pattern the brief names for v56 (`V54` / `V55` slices, `_recreate`, `_migrate`, `_run` of `migration_helpers`, `_job` of `test_migration_v53.py`); `test_migration_v52.py`–`v55.py` each slice their own range, so v56 breaks none.
- § 5.5 locks: reschedule takes (6e), (6f), then the node shared, before any plain read; skip the same, then `settle_plan_job` ((6) last for a new job). Neither waits on a row the scan holds beyond (6e)/(6f) in the same order; no cycle. The S102 bullet goes after the S101 bullet in both LOCK ORDER notes.
- § 5.2 and § 9's SMTW-Review point agree with S101's own point in `.claude/CLAUDE.md` ("a path that rewrites `due_on` without the override … breaks R03.9"): S102 writes no due column.
- `backend/tests/test_pm_generate.py` helpers § 8.2 names (`fix_now`, `set_plan`, `alone`, `insert_job(db_rows, plan, state, serial, performed_by)`, `add_reading`, `daily`, `overdue`, `upcoming`, `generate`, `technician`) exist unchanged.
- `docs/schema/notes.json`: the `pm_jobs` entry is still one line (S101 lengthened it); the brief's addition fits.
- `docs/Plan.MD`: S101 changed only the *Rescheduling* bullet and the state diagram, not § 4.7's alert row.

## Feedback

- hindrance: `git diff refs/steps/S101 -- backend` shows every untracked PM file as deleted (the snapshot has them, the index does not), so the "is the working tree still S101?" check needed `git show refs/steps/S101:<file> | diff -q - <file>` per file instead of one diff (1 run lost, 2 min).
- idea: when a staleness review follows a snapshotted step, the orchestrator could state in the prompt whether the working tree equals the snapshot (one line from `tooling/step-snapshot.bat`), so the reviewer does not re-check it file by file.
