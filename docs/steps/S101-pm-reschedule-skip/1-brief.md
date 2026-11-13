```
Step: S101 — Reschedule and skip a PM job
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 02-11-2026
Track: full
Baseline: refs/steps/S100 (c9cd091 + S095–S100, uncommitted)
Status: Done — folded into S104 (KLA 13-11-2026, gate B 2a: its code is reworked and committed with S104; its own snapshot dropped); was: Held 02-11-2026 by KLA (one path: PM templates linked to class, model or machine; R03 re-plan; 5b nothing adopted until the rework is done); was: Gate B 02-11-2026 (code review r1: 1 major (CR1-01, a reused variable kept or dropped a reschedule on the wrong edit), 1 nit, fixed in fix round 1; r2: no finding; no device check); approved 02-11-2026 (gate A delegated by KLA for tonight's PM steps: "Do those steps … stop only for real show stoppers"; review r1: 0 blocker, 0 major, 3 minor, 11 nits, all accepted; Q1–Q7 of § 9 flagged for KLA at gate B; the brief was written against the coded S095–S100, so no staleness review)
From: R03.9
```

# S101 — Reschedule and skip a PM job

## 1. What will be built

R03.9 of `docs/roadmap/R03-pm.md`. **An engineer moves a due PM job to a new date or meter
value, or skips it, always with a reason** (Plan § 4.3 *Rescheduling*; Maintenance-Philosophy
*Rescheduling*: "Skipping without a reason is not allowed"). It follows the roadmap's answers:
Q9.1 (a) a rescheduled job is on time against the new date, and reschedules are counted; Q9.2 (a)
a skipped job counts as not done, and the next job counts from the skip; Q3.3 (a) a job nobody
does stays overdue until it is done or skipped.

1. **Reschedule job** (`POST /api/pm/jobs/<id>/reschedule`): on a job in state `due` (any
   standing: *Upcoming*, *Due*, *Overdue*), a new due date and/or a new due meter value, and a
   required reason. The new value replaces the computed one for that trigger (S095's `override`);
   the on-time window stays the computed interval's (S095 D5). The job stores its reschedule in two
   new columns (migration **v55**, § 4), so the daily run and a plan save keep it. A timeline line
   `rescheduled` holds the new due point, the reason and who.
2. **Skip job** (`POST /api/pm/jobs/<id>/skip`): on a job in state `due`, a required reason. The job
   becomes `skipped`, with `done_at` the skip time and `done_meter` the meter value then (S095
   § 5.2's rule). It counts as not done (`timeliness` stays NULL). The plan's next job counts from
   the skip: `skipped` joins `pm_jobs_core.BASE_STATES`, and the route settles the plan at once, as
   *Mark job done* does. A timeline line `skipped` holds the reason and who.
3. **Who:** holders of `pm_job:verify` at the job's site (S099's key: the engineer and the
   manager). Not the technician, not IT admin.
4. **A plan edit and a reschedule.** The daily run and a plan save keep a job's reschedule, except
   that a change of the plan's schedule fields drops it (D4), with a `due_changed` line that says
   so.
5. **The job page** (`PmJobView.vue`): for a `pm_job:verify` holder on a due job, a card
   *Reschedule or skip* with **Skip job** and **Reschedule job**, each opening its dialog (phone
   first). A rescheduled job says "Moved from 08-11-2026." under its due line. A skipped job shows
   *Skipped*, who and the reason. The *History* card gains the lines *Rescheduled* (with the new due
   point) and *Skipped*.
6. **The PM list** (`PmJobRow.vue`): a due or started job that was rescheduled shows a
   *Rescheduled* badge; skipped jobs appear on the *Done* tab with a *Skipped* badge, newest first,
   and the tab's count line says "10 done · 2 skipped" (BR1-01).
7. **The counts for R03.14** are queryable with no new table: reschedules are the `rescheduled`
   events (one per move), rescheduled jobs have `rescheduled_on` or `rescheduled_meter` set, and
   skipped jobs have state `skipped` (§ 4.2).

**After S101:** the engineer can deal with every due job: do it, move it, or skip it (R03 Q3.3).

### Out of scope

- Reschedule or skip of a started job (D1): it is finished with *Not done* answers and marked done.
- Undoing a skip, or removing a reschedule (a new reschedule to the plan's date is the way back).
- The compliance report (R03.14) and its counts on screen; alerts (R03.7, S102).
- The equipment page's PM card: it shows the job's effective due point already; no badge there.
- Back-dating a skip (it is recorded at the moment it is made, D6).
- S098 § 9 A5 (a started job in a unit deactivated later): a skip does not reach it (it is
  started, and nobody holds the unit), so it stays a note for a later step.

## 2. Standards and practice

- **SMRP — metric 5.1.4 *Preventive Maintenance Compliance*, and PM rescheduled** (numbers *to
  verify*). In plain words: the
  share of PM jobs done on time, with the moved jobs counted apart, so a plant cannot look
  compliant by moving dates. Yantra judges a moved job against its new date (Q9.1 a) and keeps one
  timeline line per move, so R03.14 can show the number of reschedules beside the figure.
- **EN 13306 — scheduled (predetermined) maintenance** (term numbers *to verify*). In plain words:
  preventive work done to a timetable or a set amount of use. A reschedule is a recorded change of
  that timetable for one job; a skip is a planned job left out on purpose, recorded as not done.
  (EN 13306's *deferred* maintenance is about corrective work, so it is not used here; BR1-04.)
- **TPM — planned maintenance pillar.** In plain words: the team plans the work and does it as
  planned; a change to the plan is a decision with a reason, not a silent slip. Only the engineer
  moves or skips a job.
- **ISO 9001:2015 § 7.5.3 — control of documented information.** In plain words: records are kept,
  protected from change, and show who did what and when. Each move and each skip is a timeline line
  with who, when, the reason and the new due point; a skipped job keeps its due point and never
  becomes done.
- **ISO/IEC 27001:2022 A.5.15 — access control.** In plain words: each person may do only what the
  work needs. The routes check `pm_job:verify` at the job's site; IT admin reads PM only (R03 Q2.2 a).

## 3. Where

S101 builds on S095–S099, coded tonight and not committed (snapshots up to `refs/steps/S100`, all
in the working tree). The `file:line` anchors are to that tree; no other step is coding.

### Backend

- `backend/local_db.py`: migration **v55** after S099's v54 (§ 4.1). No `_PRECONDITIONS` entry.
- `backend/pm_jobs_core.py`: `BASE_STATES` gains `SKIPPED` (`pm_jobs_core.py:24`); new
  `job_override(job, trigger_kind)`; `due_copies(due, offset, override=None)` copies the override
  into `rescheduled_on`, `rescheduled_meter`; `due_from_job` sets `rescheduled` from them
  (`pm_jobs_core.py:120`, whose docstring already says "R03.9 sets it from its columns"); the remark
  `RESCHEDULE_DROPPED` (§ 5.1).
- `backend/pm_jobs.py`: `schedule_inputs(cur, plan, now, override=None)` passes it to `next_due`
  and returns it; `settle_plan_job(cur, plan_id, node_lifecycle, now, actor, *,
  keep_reschedule=True)` reads the open job's override (§ 5.4; keyword-only, so the run's positional
  call and `test_pm_generate.py`'s `TestRun::test_a_failing_plan_does_not_stop_the_others`, which
  wraps it as `settle(cur, plan_id, *args)`, are unchanged); `_refresh` writes the override columns and the
  `due_changed` remark; `JOB_FROM` gains `pl.trigger_kind AS pl_trigger_kind`; `job_item` gains
  `rescheduled` and `skipped`; `_SIGN_OFF_EVENTS` and `add_sign_off` gain the `skipped` line;
  `_DONE_WHERE` gains `skipped`; the LOCK ORDER note gains the S101 lines (§ 5.6).
- `backend/pm_work_core.py`: the constants, messages and pure functions of § 5.2; `SKIPPED` gets
  its own text `JOB_SKIPPED` in `_STATE_ERRORS` and `_VERIFY_STATE_ERRORS` (S098 BR1-16: "R03.9
  gives the skip its own text").
- `backend/pm_work.py`: the routes *reschedule* and *skip* (§ 6); `job_detail` gains `can_reschedule`,
  `can_skip`, `reschedule` (§ 6.2); the LOCK ORDER note gains the two routes (§ 5.6).
- `backend/pm_plans_core.py`: `SCHEDULE_FIELDS` (§ 5.4).
- `backend/pm_plans.py`: `change_plan` passes `keep_reschedule` to `settle_plan_job` (§ 5.4).

### Tests

- `backend/tests/test_migration_v55.py` (new; § 8.1), with `backend/tests/migration_helpers.py`.
- `backend/tests/test_pm_jobs_core.py`: `job_override`, the override in `due_copies` and
  `due_from_job`; three existing tests change (§ 8.3).
- `backend/tests/test_pm_work_core.py`: the functions of § 5.2; two existing tests change (§ 8.3).
- `backend/tests/test_pm_reschedule_api.py` (new; § 8.2), with S099's helpers.

### Frontend

- `frontend/src/views/PmJobView.vue`: the card, the moved-from line, the skipped line, the history
  lines (§ 5.7).
- `frontend/src/views/pm/PmJobRescheduleDialog.vue` (new) (§ 5.7).
- `frontend/src/views/pm/PmJobSkipDialog.vue` (new) (§ 5.7).
- `frontend/src/components/PmJobRow.vue`: the skipped row (§ 5.8).
- `frontend/src/views/PmJobsView.vue`: passes `answer.total_skipped` to `countText`; the *Done*
  tab's empty text becomes "No PM jobs are done or skipped yet." (§ 5.5, BR1-01).
- `frontend/src/utils/pmLabels.js`: `PM_EVENT_LABELS` gains `rescheduled`, `skipped`; `jobBadges`
  gains *Rescheduled* and *Skipped*; new `movedFromText(reschedule, meterType)` and
  `jobSkippedText(skipped)` (not `skippedText`, a name `contractLabels.js` already uses, BR1-08);
  `countText(tab, counts, total, totalSkipped = 0)` (§ 5.5).
- `frontend/tests/pmLabels.test.js`: the new helpers; the `jobBadges` and `countText("done", …)`
  cases (§ 8.3).
- `frontend/e2e/pm-reschedule.spec.js` (new; § 8.4). `frontend/e2e/support/` is unchanged.

No router, nav, `api.js`, `FormModal.vue` or `useFormModal.js` change; no new key.

### Docs (housekeeping, by the coder)

- `docs/schema/notes.json`: the `pm_jobs` line gains "`rescheduled_on`, `rescheduled_meter`: the
  engineer's reschedule of the due date and meter value (S101)"; the `pm_job_events` line gains the
  events `rescheduled` and `skipped`. Then `tooling\schema-docs.bat write`, read `git diff
  docs/schema/`; `check` exits 0. `schema.json` and `schema-data.js` are generated.
- `docs/Plan.MD` § 4.3: the *Rescheduling* bullet loses "(*Proposed*, 16-10-2026)" and says
  "Built (S101)", with D1–D6 in one paragraph and the departure of D3 (moving earlier is allowed);
  the PM job's state diagram (`due ──► in progress ──► done ──► verified`) gains `skipped` from
  `due` (BR1-14).
- `docs/Maintenance-Philosophy.md`: *Rescheduling* loses "(**Proposed**, 16-10-2026)"; one sentence:
  "Built (S101): the engineer moves a due job later or earlier, or skips it; a reason is required
  for both; a skip counts as not done and the next job counts from it."
- `.claude/CLAUDE.md` § SMTW-Review: the point of § 8.6.
- `docs/steps/device-checks.md`: no row (§ 8.5). `docs/Keycloak.md`: no change.

**File count:** 19 code and test files: backend 7, backend tests 4, frontend 8.

## 4. Data model

### 4.1 Migration v55

```sql
-- PM jobs (S101, R03.9): the engineer's reschedule of an open job.  rescheduled_on replaces the
-- computed due date and rescheduled_meter the computed due meter value (pm_schedule_core.next_due's
-- override; the windows stay the computed interval's).  NULL: not moved.  While set, due_on (or
-- due_meter) equals it: the daily run and a plan save pass it to next_due, so the copy keeps it.  A
-- change of the plan's schedule clears it.  Kept on a done or skipped job as the record that it was
-- moved; the moves themselves are the job's 'rescheduled' events.  A skipped job (R03.9) has
-- done_at (the skip time) and done_meter, which v52's chk_pm_jobs_done already allows.  Existing
-- rows get NULL, which the CHECK allows: no precondition.  <=>, as v54: a CHECK passes on NULL.
ALTER TABLE pm_jobs
    ADD COLUMN IF NOT EXISTS rescheduled_on DATE NULL AFTER meter_offset,
    ADD COLUMN IF NOT EXISTS rescheduled_meter DECIMAL(14,3) NULL AFTER rescheduled_on;
ALTER TABLE pm_jobs ADD CONSTRAINT IF NOT EXISTS chk_pm_jobs_rescheduled CHECK (
    (rescheduled_on IS NULL OR rescheduled_on <=> due_on)
    AND (rescheduled_meter IS NULL OR rescheduled_meter <=> due_meter));
```

- **Why columns, not events only** (D2): the daily run refreshes a due job's copies from the plan
  (`pm_jobs._refresh`, `pm_jobs.py:223`). Without a stored override, the next run would put the
  computed date back. S097 § 9 already says "R03.9 adds the override columns". The roadmap's
  "Migrations: none" is a departure, recorded here.
- **Existing rows** (fact: `pm_jobs` (v52) is unreleased, as S102 § 9 A1 says): dev and test rows
  get NULL and pass the CHECK. No row is updated.
- **No event change:** `pm_job_events.event` is `VARCHAR(30)` (`local_db.py`, v52), and the event
  row has `due_on`, `due_meter`, `person_id` and `remark` for the new lines. **No state change:**
  `pm_jobs.state` already has `skipped` (v52).
- **Re-run safety:** `ADD COLUMN IF NOT EXISTS`, `ADD CONSTRAINT IF NOT EXISTS` (v54's pattern).
  Rollback: S099's release never reads the columns.
- **S102 (alerts, approved)** numbers its migration v56, after this one. S101 keeps the moved due
  point in `due_on` / `due_meter` (the CHECK above), which is what S102 § 5.2 reads.

### 4.2 What is computed, never stored

- **Rescheduled** = `rescheduled_on IS NOT NULL OR rescheduled_meter IS NOT NULL`
  (`due_from_job`, `job_item`).
- **The number of moves** of a job = its `rescheduled` events; **moved from** = the due point of the
  job's last `created` or `due_changed` line before its first `rescheduled` line
  (`pm_work_core.reschedule_summary`). R03.14 counts the events per plan and month; no counter
  column (one source of the truth).

## 5. Rules

### 5.1 `pm_jobs_core` (pure)

```python
BASE_STATES = (DONE, VERIFIED, SKIPPED)   # the next job counts from the latest of these (Q9.2 a)
RESCHEDULE_DROPPED = "The plan's schedule was changed, so the job's reschedule no longer applies."
```

| Function | In → out | Rule |
|---|---|---|
| `job_override(job, trigger_kind)` | a `pm_jobs` row, the plan's kind → `{"due_on", "due_meter"}` or None | `rescheduled_on` kept only when the kind is `calendar` or `both`, `rescheduled_meter` only when `meter` or `both` (`pm_schedule_core` constants); None when neither is kept; `before_use` → None |
| `due_copies(due, offset, override=None)` | adds `rescheduled_on`, `rescheduled_meter` | the override's `due_on` and `due_meter` (the meter rounded as the other meter columns, `_column_scale`), None without one; the rest unchanged |
| `due_from_job(job)` | `rescheduled` | True when either column is set |

### 5.2 `pm_work_core` (pure)

```python
RESCHEDULED_EVENT, SKIPPED_EVENT = "rescheduled", "skipped"
SKIP_CHANGES = {"state": SKIPPED}   # with done_at and done_meter from the shell
```

**Messages** (CLAUDE-COMMON writing style B):

| Name | Text | Status, field |
|---|---|---|
| `JOB_SKIPPED` | "This job was skipped." | 409 (state `skipped`, every action of `state_error` and `verify_error`) |
| `STARTED_NO_MOVE` | "This job has been started. Finish it and mark it done." | 409 |
| `BEFORE_USE_NO_MOVE` | "This plan is now done before each use, so the job has no due point to move. Skip the job instead." | 409 |
| `MOVE_REASON` | "Say why the job is moved." | 400 `remark` |
| `SKIP_REASON` | "Say why the job is skipped." | 400 `remark` |
| `NOTHING_MOVED` | "Change the due date or the meter value." | 400 `due_on` (`due_meter` on a meter-only plan) |
| `NO_CALENDAR` | "This plan has no due date. Enter a meter value." | 400 `due_on` |
| `NO_METER` | "This plan has no meter. Enter a due date." | 400 `due_meter` |
| `NO_READING_YET` | "The meter has no reading yet, so a due value cannot be set. Log a reading first." | 400 `due_meter` |
| `meter_not_above(value_text)` | "Enter a value above the latest reading, 9,900 h." | 400 `due_meter` |
| `meter_too_far(value_text)` | "Enter a value up to 10,150 h: one interval after the latest reading." | 400 `due_meter` |
| `tickets_core.LABOUR_DATE_FORMAT`, `PLANNED_DATE_PAST`, `PLANNED_DATE_TOO_FAR` | S019's ("Enter the date as YYYY-MM-DD", "The date cannot be before today", "Choose a date within a year") | 400 `due_on` |
| `REMARK_NOT_TEXT`, `REMARK_TOO_LONG` | S098's | 400 `remark` |

The value texts are `meters_core.format_number` and the meter type's unit, as the page shows them.

| Function | In → out | Rule |
|---|---|---|
| `move_error(state)` | → `(message, 409)` or None | `due` → None; `in_progress` → `STARTED_NO_MOVE`; `done`, `verified` → `JOB_DONE`; `cancelled` → `JOB_CANCELLED`; `skipped` → `JOB_SKIPPED`; an unknown state → `ValueError`. For both routes. |
| `move_reason(body, skip)` | → `(remark, None)` or `(None, ("remark", message))` | `clean_remark(body.get("remark"), SKIP_REASON if skip else MOVE_REASON)` |
| `reschedule_override(body, trigger_kind, job, today, reading_counted, meter_every, meter_type)` | → `(override, None)` or `(None, (field, message))` | below |
| `reschedule_summary(events)` | the page's event dicts in time order → `{"count", "was_due_on", "was_due_meter"}` or None | § 4.2; None without a `rescheduled` line; `was_*` from the last `created` / `due_changed` line before the first `rescheduled` |

**`reschedule_override`** (`job` holds `due_on`, `due_meter`, `rescheduled_on`, `rescheduled_meter`;
`reading_counted` is the latest active reading plus the job's offset, or None; `meter_type` holds
`unit` and `decimals`, None without a meter trigger), in this order, the first refusal wins:

1. **Parse.** `due_on`: absent, null or `""` is *not given*; a string `YYYY-MM-DD` (the date input
   sends it; `date.fromisoformat` after `strip`, as `tickets_core._optional_date`) is a date; any
   other value → `LABOUR_DATE_FORMAT`. `due_meter`: absent, null or `""` is *not given*; else
   `meters_core.parse_number(raw, meter_type decimals)` (an int or a string; its `ValueError` text);
   given on a plan with no meter trigger → `NO_METER`. A `due_on` given on a plan with no calendar
   trigger → `NO_CALENDAR`.
2. **Moved.** A given value is *moved* when it differs from the job's current value (`due_on`;
   `due_meter` by value, 3.0 = 3). A value equal to it is not a move.
3. **Nothing moved** → `NOTHING_MOVED`.
4. **Bounds, for a moved value only.** Date: `tickets_core.planned_date_error(new, today)` (not
   before today, at most 365 days ahead; D3). Meter: `reading_counted` None → `NO_READING_YET`;
   `new <= reading_counted` → `meter_not_above`; `new > reading_counted + meter_every` →
   `meter_too_far`.
5. **The override**: for each trigger, the moved value, else the job's stored `rescheduled_*` for
   it (an earlier move stays), else None. Returns `{"due_on", "due_meter"}`.

The reason is judged after the values (`move_reason`), so a form with two faults shows the value's
first. A `bool`, `float` or `datetime` passed by the shell raises (S095 D8).

### 5.3 The two routes, step by step

**Both routes, the locks.** `require_perm("pm_job:verify")` and S098's pre-read
(`pm_work._pre_read`: 404) come first. Then, in one transaction: (6e) the plan and (6f) the job
(`pm_work._lock_job`), (1) the node shared (`pm_work._share_node`), and `now =
to_minute(pm_jobs._now(cur))`.

**Both routes, the checks**, in this order:
1. `load_node_for_user(cur, node_id, for_update=False, key="pm_job:verify")`: 404 outside the
   units, 403 without the key at the node's site.
2. `move_error(job["state"])`: 409.
3. A scrapped node: 409 `equipment.SCRAPPED_MESSAGE`.

**Reschedule:**
1. `plan["trigger_kind"] == "before_use"` → 409 `BEFORE_USE_NO_MOVE`. **Defensive** (BR1-03):
   `pm_plans_core._parse_trigger_kind` refuses `before_use` until R03.13, so only a plan changed in
   the database reaches it; `next_due` would raise on an override for such a plan. Its API test
   makes the row straight (§ 8.2).
2. `current = pm_jobs.schedule_inputs(cur, plan, now)` (no override: the reading and the offset do
   not depend on it, BR1-05). `reading_counted = reading value + offset`, or None.
3. The meter type (`pm_work._meter_type(cur, plan["meter_type_id"])`, None without a meter).
4. `reschedule_override(...)` (400 with its field), then `move_reason(body, skip=False)` (400).
5. `inputs = pm_jobs.schedule_inputs(cur, plan, now, override)` (the same snapshot: the same
   reading); `copies = due_copies(inputs["due"], inputs["offset"], override)`; `changes =
   job_changes(job, copies, job["assignee_id"])`; `update_row(cur, "pm_jobs", …)`.
6. The event: `add_event(cur, job_id, RESCHEDULED_EVENT, now, actor(), due_on=copies["due_on"],
   due_meter=copies["due_meter"], person_id=current_person_id(cur), remark=reason)`. No state
   change, so no `from_state` / `to_state`.
7. The answer: `job_detail` (§ 6.2).

**Skip:**
1. `move_reason(body, skip=True)` (400).
2. `done_meter = pm_work._done_meter(cur, plan, now)` (S095 § 5.2's rule at the skip time).
3. `update_row(cur, "pm_jobs", job_id, {**SKIP_CHANGES, "done_at": now, "done_meter": done_meter})`;
   `timeliness` and `needs_verification` stay NULL (`chk_pm_jobs_done`, `chk_pm_jobs_verification`).
   The generated `open_plan_id` becomes NULL.
4. The event: `add_event(cur, job_id, SKIPPED_EVENT, now, actor(), from_state="due",
   to_state="skipped", person_id=current_person_id(cur), remark=reason)`.
5. `pm_jobs.settle_plan_job(cur, plan_id, locked_node["lifecycle"], now, actor())`: the next job
   counts from the skip (`_last_base_job` now finds it) and is made at once when it is already in
   its *Upcoming* window (a daily plan: tomorrow is due, so a job appears; a monthly one: none yet).
6. The answer: `job_detail`.

A skip cancels nothing else: the plan has one open job (this one), and a done job waiting for
verification keeps waiting (S099). If that job is sent back later, S099's send back cancels the
plan's open job made after the skip, as for any open job.

### 5.4 The daily run and the plan save keep a reschedule

- `settle_plan_job` reads the open job (as now), then, for a refresh, `override = None if not
  keep_reschedule else job_override(job, plan["trigger_kind"])` and `schedule_inputs(cur, plan,
  now, override)`. `_refresh` compares `due_copies(due, offset, override)` (the override columns
  included) with the job; when `rescheduled_on` or `rescheduled_meter` changes, the `due_changed`
  line is written (also when the due point stays the same) with `remark=RESCHEDULE_DROPPED`.
- A plan whose kind loses a trigger drops that trigger's reschedule (`job_override`).
- **A change of the plan's schedule drops the reschedule** (D4): `pm_plans_core.SCHEDULE_FIELDS =
  ("trigger_kind", *CALENDAR_FIELDS, *METER_FIELDS, "last_done_on", "last_done_meter")`;
  `change_plan` passes `keep_reschedule=not any(field in changes for field in SCHEDULE_FIELDS)`,
  where `changes = plan_changes(locked, clean)` (computed once, as now for `update_row`). A change
  of the title, assignee, items or verification keeps it.
- A new job (CREATE) never has an override. A before-use plan's leftover due job is not refreshed
  (`decide`), so its columns stay; it can be skipped.

### 5.5 Mark done and the list

- *Mark job done* is unchanged: `timeliness(due_from_job(job), …)` reads the job's copies, whose
  `due_on` is the new date, so a moved job is on time against it (Q9.1 a; S095's table E20).
- `_DONE_WHERE` becomes `(j.state = 'verified' OR j.state = 'skipped' OR (j.state = 'done' AND
  COALESCE(j.needs_verification, 0) = 0))`: the *Done* tab lists skipped jobs by `done_at`, newest
  first (D5).
- **The count line** (BR1-01): the *Done* tab's answer gains `total_skipped`, one more `count` over
  `_COUNT_FROM + _DONE_WHERE + " AND j.state = 'skipped'"` with the same filters (0 in the empty
  answer); `total` still counts every row of the tab. `countText("done", counts, total,
  totalSkipped)` says "10 done · 2 skipped": the done part is `total - totalSkipped`, and a part at
  0 is left out (as the *Due* tab's line), so "2 skipped" alone and "10 done" alone are possible.
  Other tabs ignore the fourth argument. The empty text: "No PM jobs are done or skipped yet."

### 5.6 Locks

The rule of `pm_work.py`'s LOCK ORDER note holds: the plan (6e), then the job (6f), then the node,
before any plain read; (6) the PM counter only inside `settle_plan_job`, last.

- **Reschedule:** (6e) `pm_jobs.LOCK_PLAN` → (6f) `_LOCK_JOB` → (1) `pm_jobs.SHARE_NODE` → `SELECT
  NOW()` (no table) → plain: `load_node_for_user`'s access reads, `_last_base_job`, the readings
  (`last_readings`, `readings_across_reset`, `first_reading_after`), the meter type,
  `current_person_id` → the job's `UPDATE` (its row, held) → the event `INSERT` (shared foreign-key
  locks: the job, held; the person's `people` row) → commit. No (6), no second job.
- **Skip:** (6e) → (6f) → (1) shared → `SELECT NOW()` → plain: access, `_done_meter`'s readings,
  `current_person_id` → the job's `UPDATE` (state `skipped`; its `uq_pm_jobs_open_plan` entry
  removed) → the event `INSERT` → `settle_plan_job`: plain reads (it sees its own update: no open
  job; the skip as the last base), for a new job (6) the `PM:` counter, the job and event inserts
  (shared foreign-key locks on the plan and node, held, and the assignee) → commit. The same
  sequence as *Mark job done*. A rollback undoes the skip and the new job together.
- **The plan save and the run:** unchanged sequences; they read the job's override columns plainly
  after (6e), which every writer of them holds first.
- **No deadlock cycle:** every writer of a plan's job rows takes (6e) first (the run, a plan save,
  S098's and S099's routes, these two), so a reschedule and a skip of one job, or either beside the
  run, queue on (6e); the second reads the first's committed row after its locks (a skip after a
  skip: 409 `JOB_SKIPPED`; a reschedule after a skip: 409 `JOB_SKIPPED`; a skip after a start: 409
  `STARTED_NO_MOVE`). The node is taken shared, as Start and Mark done; the scrap holds the node
  exclusive and never waits on a plan or a job. The counter (6) after (6e) is S097's accepted order.
- The LOCK ORDER notes of `pm_work.py` and `pm_jobs.py` gain these two lines; `equipment.py`'s
  (6e)/(6f) lines need no change (one job per transaction holds: the skip's new job is inserted, not
  locked, as in Mark done).

### 5.7 The job page (`PmJobView.vue`) and the dialogs

- **Under the due line** (header): when `job.rescheduled && job.reschedule` (a reschedule dropped by
  a schedule edit, D4, shows no line: the due point is the plan's again, and the history tells the
  rest; BR1-02), a small line `movedFromText`: one move →
  "Moved from 08-11-2026." (or "from 10,040 h", or both joined by " or ", as `dueText`); more →
  "Moved 2 times, first from 08-11-2026.".
- **The card *Reschedule or skip*** (`data-testid="pm-move"`), for `can_reschedule || can_skip`,
  after the item list and before *History* (the place of S099's *Verify* card; *Start job* stays
  first for the work). Text: "Not the right time for this job? Move it to a new date or meter value,
  or skip it. Both need a reason." Two buttons in one row, `big-button flex-fill`: **"Skip job"**
  (`btn-outline-danger`, left) and **"Reschedule job"** (`btn-outline-primary`). "Reschedule job" is
  hidden when `can_reschedule` is false (a before-use plan).
- **`PmJobRescheduleDialog.vue`** (FormModal + `useFormModal`, S099's pattern; title "Reschedule
  job", the save label, BR1-06). Call contract:
  `blank()` takes no seed and reads the job at each open: `{due_on: job.due_on, due_meter:
  job.due_meter, remark: ""}`; `openCreate()` without a seed; the save sends `{due_on, due_meter,
  remark}` through `send` (the empty date or value sent as null); `afterSave` keeps the answer and
  `closed` hands it to the page as `saved(job)` (the S077 rule); a 409 emits `stale` on close and
  the page reloads. Content:
  - facts: "PM-2026-11-004 · due 08-11-2026 · Overdue 3 days" (`dueText`, `daysPastText`);
  - **"New due date"** (`<input type="date">`, id `pm-move-date`), shown when `job.due_on` is set;
  - **"New due value (h)"** (`inputmode="decimal"`, id `pm-move-meter`, the unit from
    `job.meter.meter_type`), shown when `job.meter` is set; under it "Now 9,900 h."
    (`job.meter.value_counted`);
  - **"Why is the job moved?"** (textarea, required, 500);
  - the consequence: "The job is on time if it is done by the new due date or meter value. The move
    is counted in the PM report." (the grace after it is the computed interval's, S095 D5; BR1-07);
  - save label "Reschedule job". Each refusal shows beside its field (`fieldError`, the form keys are
    the API's fields).
- **`PmJobSkipDialog.vue`**, the same pattern (title "Skip job"), `blank()` → `{remark: ""}`: facts
  as above; the
  consequence "The job is closed as skipped and counts as not done. The next job counts from today.
  You cannot undo this." (writing style B: a confirmation states the consequence); **"Why is the job
  skipped?"** (required); save label "Skip job".
- **A skipped job**: badge *Skipped*; the line `jobSkippedText(job.skipped)` → "Skipped 05-11-2026
  14:20 by Priya: <reason>." in place of the cancelled remark (the `cancelled` computed becomes
  `state === "cancelled"` only).
- **History**: a `rescheduled` line shows "to <dueText of its due_on, due_meter>" after its label,
  then the reason as the remark; a `skipped` line its reason.
- **Use on the floor:** the engineer acts at his desk or at the machine; one tap opens each dialog,
  two fields at most and a reason; the date is the phone's own date picker (as the ticket's planned
  date, S019). The technician never sees the card, so the floor's page is unchanged.

### 5.8 The list row (`PmJobRow.vue`)

- `jobBadges`: a `due` or `in_progress` job with `rescheduled` gets *Rescheduled*
  (`text-bg-light border`) after its other badges; a `skipped` job gets *Skipped*
  (`text-bg-secondary`), no longer *Cancelled*.
- A skipped row: right text "Skipped 05-11-2026" (`formatDate(done_at)`); small line the unit and
  "by <skipped.by_name>".

## 6. API

### 6.1 Common rules

As S099 § 6.1: a JSON object body (`clean_body`'s 400 otherwise), unknown fields ignored; the
answer is the job page's (`job_detail`). The database down → 503 (`DBUnavailable`).

### 6.2 The job (S098 § 6.2, S099; gains)

| Field | Value |
|---|---|
| `rescheduled` | bool (§ 4.2), also on the list's items |
| `skipped` | for a skipped job `{at, by_name, remark}` (`sign_off_out` of its `skipped` line), else null; also on the list's items (`add_sign_off`) |
| `reschedule` | `reschedule_summary(events)`: `{count, was_due_on, was_due_meter}` or null |
| `can_reschedule` | `pm_job:verify` at the site, state `due`, the node not scrapped, the plan not `before_use` |
| `can_skip` | `pm_job:verify` at the site, state `due`, the node not scrapped |
| `events[]` | gains the lines `rescheduled` (`due_on`, `due_meter`, `person`, `remark`) and `skipped` (`from_state`, `to_state`, `person`, `remark`) |

### 6.3 The routes

| Route | Body | Answers |
|---|---|---|
| `POST /api/pm/jobs/<id>/reschedule` | `{due_on?, due_meter?, remark}` | 200 the job; 400 with `field`; 403; 404; 409 (state, scrapped, before use) |
| `POST /api/pm/jobs/<id>/skip` | `{remark}` | 200 the job; 400 `remark`; 403; 404; 409 (state, scrapped) |
| `GET /api/pm/jobs?tab=done` (S098's) | — | gains `total_skipped` (§ 5.5) |

## 7. Design decisions

- **D1. Due jobs only; a started job is finished.** Both routes take state `due` (any standing,
  also *Upcoming*: an engineer may move a job before it is due). A started job is finished: its
  items take *Not done* or *NA* with a remark, and it is marked done, so the record shows what was
  done (ISO 9001 § 7.5.3). Rejected: skipping a started job (its results would hang on a job that
  never finished, and the technician's answers would be lost from the base).
- **D2. Two override columns, the moves as events** (migration v55). The run must keep the move,
  so it lives on the row it already reads; the count is the events, so it is never out of step.
  Rejected: the override read from the latest `rescheduled` event (one more query per plan in the
  run, and the job's due point hidden in its history); a `reschedule_count` column (a second copy of
  the events).
- **D3. A move may be earlier or later; the bounds are a typo guard.** Earlier is allowed (a
  planned shutdown next week: do it before), a small departure from Maintenance-Philosophy's "push
  … to a later date". A move can still flatter compliance: an overdue job moved to today and done
  today counts on time (Q9.1 a); the count of moves beside the figure shows it (BR1-12). Date: not before today, within a year (the
  ticket's planned-date rule, `tickets_core.planned_date_error`, one copy). Meter: above the latest
  counted reading and at most one interval past it. Rejected: a date bound of one interval (a
  weekly job could not move past a month's shutdown); no meter bound (a typed extra zero moves a
  job by years).
- **D4. A schedule edit of the plan drops the reschedule; other edits keep it.** The engineer who
  edits the rhythm sets the new rhythm (S095 § 9 N1), and a meter value meant for another meter
  would be wrong. The `due_changed` line says why. Rejected: keep it always (a wrong-scale meter
  value after a meter change); drop it on every plan save (a title fix would undo a decision).
- **D5. Skipped jobs on the *Done* tab.** The tab is the list of closed jobs; a *Skipped* badge and
  no *On time* / *Late* badge show it is not done. Rejected: a fifth tab (crowds the phone's tab
  row, S099's `@device` test); not listing them (the skip would be visible nowhere until R03.14).
  The count line says "10 done · 2 skipped" (`total_skipped`, BR1-01), so a skip is never counted
  as done. Rejected: "12 done" for the tab's rows (a wrong figure); "12 closed" (*closed* is the
  tickets' word).
- **D6. A skip is recorded now, with the meter value now.** The skip is a decision, not work, so
  it has no back-dated time; `done_at` is the minute of the skip and `done_meter` S095 § 5.2's
  value at it, so the next job counts from the skip (Q9.2 a) by date and by meter. Rejected: the
  skip keeps the due date as base (the next job would fall due at once on an overdue plan).
- **D7. The key is `pm_job:verify`** (the roadmap's choice: the engineer, so the manager). Rejected:
  a new key (one more role row for the same people).

## 8. Tests and acceptance

### 8.1 Migration (`backend/tests/test_migration_v55.py`)

- A v54 database with a `due`, a `done` and a `skipped` job (with `done_at`) migrates; the columns
  are NULL; the types read from `information_schema.COLUMNS` are `date` and `decimal(14,3)`.
- The CHECK refuses `rescheduled_on` different from `due_on`, `rescheduled_on` set with `due_on`
  NULL, and `rescheduled_meter` different from `due_meter`; it allows equal values. The case with
  `due_on` NULL needs a meter-only job (`due_on`, `grace_days`, `upcoming_days` NULL; `due_meter`
  and `meter_window` set; `created_why = 'meter'`), which `test_migration_v53._job` does not make by
  default: the test passes those columns (BR1-10).
- A second run of the migration's statements changes nothing.

### 8.2 Backend (`backend/tests/test_pm_reschedule_api.py`, new)

Helpers from `tests.test_pm_verify_api` and `tests.test_pm_work_api` (`plan_with`, `start`, `fill`,
`done`, `job_row`, `refusal`, the `tech` fixture), `tests.test_pm_generate` (`generate`, `alone`,
`fix_now`, `events_of`, `jobs_of`). Each test makes its own machine and plan (S099's pattern).

- **Reschedule, calendar:** a due job moved 10 days later → `due_on`, `rescheduled_on` equal the new
  date, `grace_days` unchanged; the `rescheduled` line holds the date, the reason, the engineer's
  person; `rescheduled` true on the page and the list; `reschedule` count 1 and `was_due_on` the old
  date. A second move → count 2, `was_due_on` still the first.
- **Reschedule, meter and both:** a meter plan moved to a value → `due_meter`; a `both` plan moving
  only the date keeps the meter computed; then moving the meter keeps the earlier date move.
- **The run keeps it:** after a move, `generate` writes nothing for the plan (no `due_changed`).
- **A plan edit:** a title change keeps it; a `calendar_every` change drops it, with a
  `due_changed` line whose remark is `RESCHEDULE_DROPPED`.
- **On time against the new date:** a job moved later and done after the old window but within
  the new one → `timeliness` `on_time`.
- **Refusals (400, with field):** each message of § 5.2 once: no reason, a date in the past, more
  than 365 days, a bad date string, a date on a meter-only plan, a meter value on a calendar plan,
  a meter value not above the reading, past one interval, with no reading, nothing moved, a reason
  over 500.
- **Refusals (409/403/404):** a started job, a done one, a skipped one, a scrapped machine; the
  technician 403; IT admin 403; an engineer of another site 404.
- **The before-use guard** (BR1-03): a calendar plan saved past due (its job made), then the test
  writes the plan straight: `UPDATE pm_plans SET trigger_kind = 'before_use', calendar_every = NULL,
  calendar_unit = NULL, last_done_on = NULL WHERE id = %s` (v51's `chk_pm_plans_calendar` and
  `chk_pm_plans_seed` allow it: a before-use plan has no interval and no seed date). The reschedule
  → 409 `BEFORE_USE_NO_MOVE`, `can_reschedule` false; the skip → 200.
- **Skip:** state `skipped`, `done_at` the minute, `done_meter` the reading at it, `timeliness` and
  `needs_verification` NULL; the `skipped` line (from `due` to `skipped`, the reason, the person);
  the *Done* tab's `total_skipped` counts it, with the unit filter too;
  a daily plan gets its next job at once, due the day after the skip; a monthly plan none, and its
  card's next due is the skip date plus a month; the *Done* tab lists the skipped job with its
  `skipped` line; a skip then a skip → 409 `JOB_SKIPPED`; a skip of a started job → 409
  `STARTED_NO_MOVE`; Start on a skipped job → 409 `JOB_SKIPPED`.
- **The lock:** the skip waits for the plan lock (BR1-09): a test holds the plan row `FOR UPDATE`
  on a second connection, starts the skip in a thread, and the skip answers only after the release
  (modelled on S099's `test_verify_waits_for_the_plan_lock`); then a reschedule of the skipped job
  answers 409 `JOB_SKIPPED`.
- **Identity:** a login with no person (`current_person_id` None) writes the line with
  `person_id` NULL; `created_by` holds the login, and the page names it (S098 § 6.2's rule).

### 8.3 Existing tests that change or run again

- `backend/tests/test_pm_jobs_core.py`: `test_the_constants` (`BASE_STATES` gains `SKIPPED`);
  `test_the_copies_go_back_to_the_same_due` and
  `test_the_copies_take_the_column_s_three_decimals` (the copies and the stored row gain
  `rescheduled_on`, `rescheduled_meter`).
- `backend/tests/test_pm_work_core.py`: `test_state_error` and `test_verify_error` (`SKIPPED` →
  `JOB_SKIPPED`).
- `frontend/tests/pmLabels.test.js`: it has no `skipped` case today; new cases for `jobBadges`
  (*Skipped*, *Rescheduled*), `countText("done", …)` ("10 done · 2 skipped", "2 skipped",
  "10 done"), `movedFromText` and `jobSkippedText`. Its existing `countText` cases are unchanged.
- Run again: `test_pm_generate.py`, `test_pm_jobs_api.py`, `test_pm_work_api.py`,
  `test_pm_verify_api.py`, `test_pm_plans_api.py`, `test_migration_v52.py`–`test_migration_v54.py`,
  `test_role_matrix` (no key change).

### 8.4 Automated (e2e, `frontend/e2e/pm-reschedule.spec.js`, new)

Set-up by API, S099's `jobFor` copied into the spec (a calendar plan every 10 days, last done 20
days ago, so the save makes the job); each test finds its own row by machine.

- `S101: an engineer reschedules a due job, and the page and the list show the move` — the card
  `pm-move`, "Reschedule job", `expectDialogFits`; save with no reason → `expectFieldMessage` "Say
  why the job is moved."; a date 5 days ahead (`istDay(5)`) and a reason → "Moved from …" under the
  due line, *History* shows *Rescheduled*; the PM list's row shows *Rescheduled*.
- `S101: an engineer skips a due job, and it shows as Skipped on the Done tab` — "Skip job",
  `expectDialogFits`, the consequence text, a reason → badge *Skipped*, the skipped line with the
  reason; the *Done* tab's row shows *Skipped*, and its count line names "skipped".
- `S101: the technician sees no Reschedule job or Skip job` — the technician on the same job: no
  `pm-move` card; *Start job* is there.

Untagged (logic tests; the dialog fit is checked on the Android phone in the flow). Targeted run:
`tooling/run-e2e-tests.bat e2e/pm-reschedule.spec.js e2e/pm-job.spec.js e2e/pm-jobs.spec.js
e2e/pm-verify.spec.js e2e/screens.spec.js`.

### 8.5 On a real device

None. The date picker is the phone's own, as the ticket's planned date (S019); the browser tests
cover the dialogs on the Android phone.

### 8.6 Acceptance and the SMTW-Review point

- Every test of § 8.1–8.4 green; `tooling/run-tests.bat` green; `npx vite build` clean;
  `tooling\schema-docs.bat check` exit 0.
- **SMTW-Review point** (`.claude/CLAUDE.md`): "**PM reschedule and skip (S101):** only a `due` job
  is moved or skipped, by a `pm_job:verify` holder at its site, with a reason, under the plan (6e)
  and job (6f) locks, and each writes its timeline line (`rescheduled`, `skipped`) in the same
  transaction. The move lives in `rescheduled_on` / `rescheduled_meter`, which `settle_plan_job`
  passes to `next_due` and a schedule edit of the plan clears; the count of moves is the events. A
  skip writes `done_at` and `done_meter` and is a base for the next job (`BASE_STATES`), never
  `timeliness`. A path that rewrites `due_on` without the override, or skips without a reason,
  breaks R03.9 and R03.14."

## 9. Open questions and assumptions

All decided by the orchestrator under KLA's go-ahead for tonight's PM steps, **to confirm at
gate B**:

- **Q1 (D1)** due jobs only; a started job is finished, not skipped.
- **Q2 (D2)** migration v55 (two columns), a departure from the roadmap's "Migrations: none".
- **Q3 (D3)** a move may be earlier (a departure from Maintenance-Philosophy's "later"); the bounds:
  today to a year ahead, the meter above the latest reading and at most one interval past it.
- **Q4 (D4)** a schedule edit of the plan drops the reschedule.
- **Q5 (D5)** skipped jobs on the *Done* tab; its count line says "10 done · 2 skipped".
- **Q6 (D6)** a skip is recorded now (no back-dating) and counts from now, by date and meter.
- **Q7** the list shows a *Rescheduled* badge only; "moved from" is on the job page.

Assumptions:

- **A1** `pm_job:verify` stays the engineer's (S099); the manager inherits it.
- **A2** S102 (alerts, approved) keeps v56 after this step's v55, and reads the moved due point in
  `due_on` / `due_meter` (fact, confirmed by review r1's cross-check).
- **A3** the facts of § 3 are the working tree at `refs/steps/S100`; nothing else codes tonight.

## 10. Amendments

None.

## Review log

### Round 1 — `2-brief-review-r1.md`, answered 02-11-2026

| Finding | Answer |
|---|---|
| BR1-01 (minor) the *Done* count calls skips "done" | Accepted (a): the *Done* answer gains `total_skipped`; `countText` says "10 done · 2 skipped", a part at 0 left out; the empty text "No PM jobs are done or skipped yet."; `PmJobsView.vue` joins *Where* (19 files). § 1, § 3, § 5.5, § 6.3, D5, § 8.2–8.4, Q5. |
| BR1-02 (minor) "Moved from" after a dropped reschedule | Accepted (a): the line shows only when `job.rescheduled && job.reschedule`; `reschedule` stays the count. § 5.7. |
| BR1-03 (minor) the before-use refusal is not reachable by API | Accepted (a): the guard stays, said defensive (`_parse_trigger_kind` refuses `before_use` until R03.13); its test writes the plan row straight (the `UPDATE` with `last_done_on = NULL` too, for `chk_pm_plans_seed`), then reschedule 409 and skip 200. § 5.3, § 8.2. |
| BR1-04…BR1-14 (nits) | All accepted. 04: EN 13306 *scheduled (predetermined)* maintenance, SMRP 5.1.4 (to verify). 05: step 2 calls `schedule_inputs` without an override. 06: dialog titles = save labels. 07: "by the new due date or meter value". 08: `jobSkippedText`, not `skippedText` (taken in `contractLabels.js`). 09: the lock bullet names the skip. 10: the meter-only job for the CHECK case. 11: "`pm_jobs` (v52) is unreleased", as S102. 12: D3 says a move can flatter compliance and the count shows it. 13: § 5.3 split into the locks and the checks. 14: Plan.MD's state diagram gains `skipped`. |
