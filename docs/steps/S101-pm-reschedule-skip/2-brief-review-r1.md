```
Step: S101 — Reschedule and skip a PM job
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 02-11-2026
```

Reviewed against: c9cd091 + uncommitted S095, S096, S097, S098, S099, S100

# S101 — Brief review, round 1

**Verdict: no `blocker` or `major` finding is open.** Three `minor` findings (one is the Q5
judgement call) and a list of nits. The facts file `scratch/brief-facts-S101.md` was given and
used; every name it lists as "not found" is one the brief says is new, and every claim about an
existing name checked against the working tree holds. Full track, so further rounds may follow.

## The S102 cross-check (asked by the orchestrator)

**S101 does what S102 § 5.2 assumes; neither brief must change its design.** Fact, from the
brief and the code:

- A reschedule writes the moved point into `due_on` / `due_meter`: § 5.3 step 5 builds `copies`
  from `next_due(..., override)`, and `next_due` puts the override into `due_on` / `due_meter`
  (`backend/pm_schedule_core.py:196`, `:203`); `job_changes` then writes them with
  `rescheduled_on` / `rescheduled_meter` in one `UPDATE`.
- Every refresh keeps it: `settle_plan_job(..., keep_reschedule=True)` passes `job_override(job,
  kind)` to `schedule_inputs`, so `_refresh`'s copies hold the moved point again (§ 5.4). The
  CHECK `rescheduled_on <=> due_on` (v55) refuses any write that leaves `due_on` behind.
- S101 names no S102 marker column: `job_changes` writes only the keys of `due_copies` plus
  `assignee_id`; S102's `_mark_alerted` is a raw `UPDATE` of its four columns only.

What to update, wording only: S102 § 9 A2 can be closed ("S101 keeps the due point in
`due_on` / `due_meter`"); S102 § 8.1's `V54` slice becomes `V55` (`m[0] <= 55`), as its own note
foresees; S102's staleness check before coding should read S101's two new routes in `pm_work.py`
(they call `_lock_job` and `job_detail`, which S102 keeps as wrappers, so no conflict).

## Findings

### BR1-01 — minor — § 5.5, D5, Q5: the *Done* tab's count line calls skipped jobs "done"

**Problem.** `_DONE_WHERE` gains `skipped`, and `countText("done", …, total)` keeps "12 done"
(`frontend/src/utils/pmLabels.js:282`), so the line counts skipped jobs as done while their rows
carry *Skipped* and the brief's own D5 says a skipped job "is not done". The empty text "No PM
jobs are done yet." has the same gap.

**Why it matters.** Writing style B: one word for one thing. An engineer reading "12 done" for
the month, two of them skipped, reads a wrong figure; R03.14 will then show a different number.

**Options.**
- (a) **Recommended.** The *Done* tab's answer gains `total_skipped` (one more `COUNT` on
  `_DONE_WHERE AND j.state = 'skipped'`, with the same filters), and `countText` says
  "10 done · 2 skipped" (the skipped part left out at zero), as the *Due* tab's line is built.
  One extra query on a paged tab; `countText`'s test gains a case.
- (b) Keep "12 done" (the brief's Q5) and accept the mismatch until R03.14.
- (c) Rename the line "12 closed": *closed* is the tickets' word and would mean a second thing.

### BR1-02 — minor — § 5.7, § 4.2: "Moved from …" stays on the page after D4 drops the move

**Problem.** The page shows `movedFromText` "when `job.reschedule`", and `reschedule_summary`
returns a count whenever a `rescheduled` line exists. After a schedule edit drops the override
(D4, `RESCHEDULE_DROPPED`), `rescheduled` is false and `due_on` is the computed date again, but
`reschedule` still holds `{count: 1, was_due_on: …}`, so the header says "Moved from 08-11-2026."
under a due line that is no longer moved.

**Why it matters.** The header misstates the record (ISO 9001 § 7.5.3 is the brief's own
standard here); the history already tells the full story.

**Options.**
- (a) **Recommended.** Show the line only when `job.rescheduled` is true (`v-if="job.rescheduled
  && job.reschedule"`); `reschedule` stays as the count for R03.14. The e2e test of § 8.4 is
  unchanged.
- (b) `reschedule_summary` also returns `dropped: true` when a `due_changed` line with
  `RESCHEDULE_DROPPED` follows the last `rescheduled` line, and the page words it ("Moved
  1 time; the plan's schedule changed since"). More code for a rare case.

### BR1-03 — minor — § 5.3, § 8.2: the before-use refusal cannot be reached through the API; say how its test makes the row

**Problem.** `BEFORE_USE_NO_MOVE` and the test "a before-use plan's leftover due job" need a plan
with `trigger_kind = 'before_use'`, but `validate_plan` refuses that kind
(`pm_plans_core.py:149`, `BEFORE_USE_NOT_YET`, "until R03.13"), so no API path makes one. The
brief does not say how the test gets the row.

**Why it matters.** The coder would either write a test that cannot pass or decide alone to write
the row straight.

**Options.**
- (a) **Recommended.** Keep the guard (it is cheap, and `next_due` raises on an override for a
  before-use plan) and state the set-up: a calendar plan saved past due, then a direct
  `UPDATE pm_plans SET trigger_kind = 'before_use', calendar_every = NULL, calendar_unit = NULL
  WHERE id = %s` (the coder checks v51's CHECK allows it), then the reschedule → 409, the skip →
  200.
- (b) Keep the guard as defensive, like `NO_ITEMS` ("defensive: S096 keeps at least one active
  item"), with no API test; a unit test of `can_reschedule`'s rule is enough.

## Nits

- **BR1-04** (nit) § 2: EN 13306 defines *deferred corrective maintenance* (a fault whose repair
  is put off by a rule); it has no "deferred maintenance" term for a preventive job. Cite the
  reschedule as a change of the *scheduled (predetermined) maintenance* plan instead, and SMRP's
  figure as metric 5.1.4 *Preventive Maintenance Compliance* (keep "to verify").
- **BR1-05** (nit) § 5.3 reschedule step 2: only `reading` and `offset` are used from this call,
  and neither depends on the override, so pass `override=None` there; step 5's call with the new
  override stays.
- **BR1-06** (nit) § 5.7: the dialogs' titles are not stated. S099's pattern: the title is the
  save label ("Reschedule job", "Skip job").
- **BR1-07** (nit) § 5.7: the reschedule consequence "on time if it is done by the new date" is
  wrong for a meter-only plan. "The job is on time if it is done by the new due date or meter
  value." (the window after it is the computed interval's, as D5 says).
- **BR1-08** (nit) § 3, § 5.7: `skippedText` already exists in
  `frontend/src/utils/contractLabels.js:126` with another meaning. Name the new helper
  `jobSkippedText` (or `skippedLine`), so one name means one thing across the utils.
- **BR1-09** (nit) § 8.2 "The lock": the bullet says the reschedule waits but describes the skip
  waiting; name it "the skip waits for the plan lock; then a reschedule of the skipped job → 409".
- **BR1-10** (nit) § 8.1: the case "`rescheduled_on` set with `due_on` NULL" needs a meter-only
  job (`due_on`, `grace_days`, `upcoming_days` NULL; `due_meter` and `meter_window` set;
  `created_why = 'meter'`), which `test_migration_v53._job` does not make by default; say so.
- **BR1-11** (nit) § 4.1 "production is at v41": the version does not matter; the point is that
  `pm_jobs` (v52) is unreleased, as S102 A1 says. Align the two briefs.
- **BR1-12** (nit) D3 "it cannot flatter compliance": an overdue job moved to today and done today
  counts on time, by Q9.1 (a); the count of moves shows it. Reword to say that.
- **BR1-13** (nit) § 5.3 "Both: …" is one sentence of about 70 words (style A); split it into the
  lock steps and the checks.
- **BR1-14** (nit) § 3 Docs: Plan.MD § 4.3's state diagram (`due ──► in progress ──► done ──►
  verified`) could gain `skipped` beside the text change the brief plans.

## Checked and found consistent

- **Migration v55** (§ 4.1): the two columns and the CHECK; `<=>` is needed (with `= `, a
  `rescheduled_on` set while `due_on` is NULL would pass); `ADD … IF NOT EXISTS` as v54; no
  precondition is right (nullable columns, `pm_jobs` unreleased). The departure from the
  roadmap's "Migrations: none" is recorded (D2, Q2). Column order after `meter_offset` does not
  clash with S102's `AFTER needs_verification`.
- **S095's override** (D5): `next_due` replaces only the value and keeps `grace`, `upcoming` and
  `meter_window` from the computed interval (`pm_schedule_core.py:191–206`); `timeliness` reads
  the job's copies, so a moved job is judged against the new date (Q9.1 a, S095 E20).
- **`settle_plan_job(..., keep_reschedule=)`, `_refresh`, D4**: keyword-only keeps
  `test_a_failing_plan_does_not_stop_the_others`'s `settle(cur, plan_id, *args)` wrapper working
  (`test_pm_generate.py:286`); `change_plan` computes `plan_changes` once (`pm_plans.py:448`);
  `SCHEDULE_FIELDS` from `CALENDAR_FIELDS`, `METER_FIELDS` plus the seed; `job_override` drops a
  trigger the plan lost; `due_copies` must round `rescheduled_meter` through `_column_scale` so
  the CHECK holds after MariaDB's own rounding (the brief says so).
- **The skip as a base** (D6): `BASE_STATES` gains `SKIPPED`, `_last_base_job` orders by
  `done_at`; `chk_pm_jobs_done` allows `done_at` and `done_meter` on `skipped` and forces
  `timeliness` NULL; `chk_pm_jobs_started` and `chk_pm_jobs_verification` pass with `started_at`
  and `needs_verification` NULL; `_done_meter` is Mark done's rule; a daily plan gets its next job
  at once (upcoming window 1 day), a monthly one not (`upcoming_days` 3).
- **Bounds** (D3): `planned_date_error` (today … +365, `PLANNED_DATE_MAX_DAYS`) and
  `parse_number` exist with the texts named; the meter bound is in the counted frame, the same
  as `due_meter` and the dialog's "Now … h" (`value_counted`).
- **Locks** (§ 5.6): (6e) `LOCK_PLAN` → (6f) `_LOCK_JOB` → (1) `SHARE_NODE` → `SELECT NOW()` →
  plain reads, as Verify and Send back; the skip's `settle_plan_job` takes (6) last, as Mark done;
  matches the LOCK ORDER notes of `pm_jobs.py`, `pm_work.py`, `pm_plans.py` and `equipment.py`
  (6e)/(6f). One job locked per transaction holds.
- **`pm_job:verify`**: in `SITE_SCOPED`; the engineer, the manager through `ROLE_INCLUDES`;
  `load_node_for_user(cur, node_id, for_update=False, key=…)` gives 404 outside the units
  (`equipment:read` is `*`, so the technician and IT admin get 403), as S099's tests show
  (`test_pm_verify_api.py:133–144`); `test_role_matrix` needs no change.
- **Job page and list**: `job_item`, `add_sign_off`, `_SIGN_OFF_EVENTS`, `sign_off_out`,
  `_events` and `jobBadges` are where the brief says; `PmJobVerifyDialog.vue` is the pattern the
  two dialogs copy (`blank()` without a seed, `afterSave` + `closed` → `saved`, 409 → `stale`);
  `PmPlansCard.vue`'s `open_job` has no `rescheduled` key, so no badge there, as § 1.6 says.
- **Use on the floor**: one tap to each dialog; at most two fields and a reason; the phone's own
  date picker; the skip is a dialog that states the consequence and needs a reason, never a
  single tap; the technician sees no card (hidden, not a 403). Texts follow style B.
- **Tests that change** (§ 8.3): `test_the_constants` (`BASE_STATES`),
  `test_the_copies_go_back_to_the_same_due` and `test_the_copies_take_the_column_s_three_decimals`
  (`job_changes` reads `job["rescheduled_*"]`), `test_state_error` and `test_verify_error`
  (`SKIPPED` → `JOB_SKIPPED`); `test_state_error_texts_and_bad_input` and `test_pm_verify_api.py`'s
  `JOB_CANCELLED` use (a cancelled job) are unchanged; `pmLabels.test.js` has no `skipped` case;
  no e2e spec names a skipped job. The targeted-run spec files exist.
- **File count** 18 and the standards named match the settings' list (TPM, SMRP, EN 13306,
  ISO 9001, ISO 27001).

## Feedback

- waste: read S102's brief whole (647 lines) for the cross-check when only § 5.2, § 8.1 and § 9 A2
  mattered; the orchestrator could name the sections it wants cross-checked
  (`docs/steps/S102-pm-alerts/1-brief.md`, about 10 minutes).
- idea: the facts file already shows a brief's "new" name that exists elsewhere (`skippedText` in
  `contractLabels.js`); a one-line mark such as "**name taken** in another module" in the
  *not found* list would make it stand out (`scratch/brief-facts-S101.md:138`).
