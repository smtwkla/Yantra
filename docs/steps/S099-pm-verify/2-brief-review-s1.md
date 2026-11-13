```
Step: S099 — Verify and send back a PM job
Doc: brief-review s1
Author: brief-reviewer (Fable 5.1)
Date: 02-11-2026
```

Reviewed against: c9cd091 + uncommitted S095, S096, S097, S098 (the working tree equals
`refs/steps/S098`, 5b340d0, for every file checked; S098's code review round 2 runs beside this
review, so a small fix may still land after it).

# S099 — Staleness review s1

**Verdict: no blocker or major finding. Two minor findings and seven nits.** The design of the
approved brief still works on the coded S097 and S098: every column, CHECK, constant, route, lock
statement, answer field, component and test the brief relies on exists as it says, with the
mismatches below. All are wording and file-list fixes to the brief; none changes a decision of § 7
or § 9.

The facts file `scratch/brief-facts-S099.md` was made before S097 and S098 were coded (it says
`backend/pm_work.py` and `PmJobView.vue` do not exist), so every name below was checked in the code
directly, not from it.

The one question asked: does each statement of the brief about S095–S098's code still hold? Checked
in § 3, § 4, § 5.1–5.8, § 6, § 8.1–8.4 and § 9 A1: `pm_work.py` (the routes, `_pre_read`,
`_lock_job`, `_share_node`, `_work_access`, `_event_time`, `job_detail`, `_events`, `mark_done`,
the LOCK ORDER note), `pm_work_core.py` (the constants, `validate_result`, `_remark`,
`state_error`, `job_time_error`, `done_before_start`), `pm_jobs.py` (`LOCK_PLAN`, `SHARE_NODE`,
`JOB_FROM`, `_DONE_SELECT`, `_DONE_COUNT`, `add_event`, `_cancel`, `settle_plan_job`, `_now`,
`jobs_out`, `job_item`, `_counts`, `list_jobs`), `pm_jobs_core.py` (the states, `TABS`, `tab_of`,
`list_order`), `config_rbac.py`, `local_db.py` v52 and v53, `equipment.py`'s LOCK ORDER,
`db_helpers.update_row`, `api_common.enum_arg`, `improvements._closed`, `tickets_core.MOVES`,
`pmLabels.js`, `PmJobView.vue`, `PmJobRow.vue`, `PmJobsView.vue`, `PmJobDoneDialog.vue`,
`MeView.vue`, the router, `pm-job.spec.js`, `pm-jobs.spec.js`, `me.spec.js`, `screens.spec.js`,
`e2e/support/meters.js` and `people.js`, `test_pm_jobs_api.py`, `test_pm_work_api.py`,
`test_pm_work_core.py`, `test_rbac.py`, `test_modules.py`, `pmLabels.test.js`, `notes.json` and
Plan.MD's *Needs-verification* bullet.

## Findings

### BS1-01 — minor — `pmLabels.js` holds the tab list, the URL query and the count line; the brief does not name them

**Problem.** § 3 *Frontend* lists `pmLabels.js`'s changes as `PM_EVENT_LABELS`, `jobBadges` and the
three new helpers. S097's code keeps three more things there that a fourth tab needs:
`PM_TABS = ["due", "upcoming", "done"]` (`PmJobsView.vue` falls back to *Due* for any other `tab`),
`jobsQuery(query)` (sets `tab` only for `upcoming` and `done`, and `page` only for `done`) and
`countText(tab, counts, total)` (S098 D-c12: the third argument is the *Done* tab's paged `total`;
no `to_verify` branch). Without them `/pm?tab=to_verify` opens *Due*, the API is asked for *Due*,
and the count line is empty. `pmLabels.test.js` tests `jobsQuery` and `countText` (lines 190–216),
so those tests change too; § 8.3 lists only the new helpers.

**Why it matters.** The coder names every changed line (§ 8.3); a file-list gap here is found late,
at the browser run.

**Options.** (a) § 3 *Frontend*, `pmLabels.js`: add "`PM_TABS` gains `to_verify`; `jobsQuery` sends
`tab=to_verify` and its `page`; `countText('to_verify', counts, total)` → '3 to verify' (from
`total`, the paged count, as *Done*; `counts.to_verify` is the tab label's)". § 8.3
`pmLabels.test.js`: add the `jobsQuery` and `countText` cases. **Recommended.** (b) Leave it to the
coder (it is the same file; but the brief's own rule is that every changed line is named).

### BS1-02 — minor — the floor goes through `_event_time`, not a bare `job_time_error` call

**Problem.** § 5.5 says `done_time_error(done_at, now, started_at, sent_back_at)` "replaces S098's
`job_time_error(done_at, now, not_before=started_at)`". In the code Mark done has no such call:
it calls `_event_time(body.get("done_at"), now, "done_at", not_before=job["started_at"])`
(`pm_work.py:458`), and `_event_time(raw, now, field, not_before=None)` (`:255`) parses the time
(null → now to the minute; `EVENT_TIME_FORMAT` 400), rounds it to the minute, then calls
`job_time_error(moment, now, not_before)`. Start calls the same helper without `not_before`.
`done_time_error` as § 5.1 defines it calls `job_time_error` first itself, so a second call after
`_event_time` would judge the window twice.

**Why it matters.** The coder must choose where the floor goes; the brief should say.

**Options.** (a) `_event_time` gains `sent_back_at=None` and calls
`done_time_error(moment, now, not_before, sent_back_at)` in place of `job_time_error` (Start passes
neither, so its behaviour is the same: `done_time_error` with both None is `job_time_error`). Mark
done passes `sent_back_at` from the plain read § 5.5 names. **Recommended**: one place judges a
time, as now. (b) Keep `_event_time` as it is and let Mark done call `done_time_error` after it
with the `moment` it returns; `done_time_error` then must not call `job_time_error` (change § 5.1's
row). More code, and two helpers to keep in step.

## Nits

- **BS1-03** (nit) § 3 (S098's list), § 5.1 (`done_time_error`'s row), § 8.2: `DONE_BEFORE_START`
  is not a constant. The code has the function `done_before_start(started_at)` → "Done must be at or
  after Started, 28-10-2026 10:00." (`pm_work_core.py:84`), the shape the brief's own
  `done_before_send_back(sent_back_at)` copies. Name it so in the three places.
- **BS1-04** (nit) § 3 *Backend* (`pm_jobs.py`), § 8.3: S097's CANCEL write is already out of
  `settle_plan_job`, as the private `_cancel(cur, job, remark, now, actor)` (`pm_jobs.py:218`; the
  signature the brief gives `cancel_job`; it writes `from_state=DUE_STATE`, right for send back,
  which cancels a `due` job only). S099 renames it public (`cancel_job`), as S098 CR1-04 did
  `add_event`; `settle_plan_job`'s branch changes to the new name. Say "rename", not "take out";
  § 8.3's "`cancel_job`'s extraction keeps `settle_plan_job`'s behaviour" then reads "the rename".
  Name `pm_jobs.add_event(cur, job_id, event, now, actor, **fields)` as the event writer of § 5.3
  step 4 and § 5.4 steps 3 and 5. Add one line to `pm_jobs.py`'s LOCK ORDER note (its last bullet
  is S098's): send back (`pm_work.py`) calls `cancel_job` on the plan's open job under the same (6e).
- **BS1-05** (nit) § 3 *Backend*, § 5.1 (`clean_remark`'s row), § 8.3: the remark rules are already
  a helper, `_remark(raw, outcome)` (`pm_work_core.py:116`), which looks the outcome up in
  `REMARK_NEEDED` — a dict by outcome (`{not_ok, not_done, na}`), not one text. S099 renames it
  `clean_remark(value, needed_message)` and turns its second argument into the message:
  `validate_result` passes `None` for a check's NA (its rule at `:165` stays) and
  `REMARK_NEEDED.get(outcome)` otherwise. `test_pm_work_core.py` tests the remark rules through
  `validate_result` only (lines 85–104), so they stay green as § 8.3 says.
- **BS1-06** (nit) § 8.3 `test_pm_jobs_api.py`: S098 left one *Done*-tab test, not two:
  `test_the_done_tab_newest_first_and_paged` (`:165`, two plans by `create(…)` with the default
  verification, both done by API, `total` 2, `per_page=1` page 2). It is the one whose plans need
  `needs_verification: false`. And `pm-jobs.spec.js` has no *Done*-tab test (S098 added only
  "a started job shows In progress on the Due tab", `:176`), so the BR1-12 sentence resolves to
  "no change in `pm-jobs.spec.js`"; `pm-job.spec.js:117` is the one line (`page.goto("/pm?tab=done")`
  then the row by serial), as § 8.3 says.
- **BS1-07** (nit) § 5.6, last paragraph: `equipment.py` carries the (6f) line twice: the short one
  at `:30` ("(6f) the PM job row (pm_jobs, S098): always right after its plan (6e)", the text the
  brief quotes) and the S098 paragraph at `:95` ("S098: start, an item, the performer and done take
  (6e), then (6f), then a node …"). Add the S099 exception to both, or say which.
- **BS1-08** (nit, a wording judgement for KLA) `PmJobDoneDialog.vue:69`: S098's consequence line
  reads "The job can no longer be changed." After S099 a job of a plan that needs verification can
  come back by send back, and § 5.5 says "Nothing else in Mark done changes". Either keep the line
  (the technician cannot change it; the engineer can send it back) or, when
  `job.plan.needs_verification` is true (the page has it), read "The job can no longer be changed.
  An engineer checks it." — one line in S098's dialog, no test change.
- **BS1-09** (nit) § 5.7, the *To verify* row: `PmJobRow.vue:21` shows a done row's right text as
  `Done ${formatDate(job.done_at)}` — the date only, "Done 27-10-2026". The brief's row reads
  "Done 27-10-2026 11:05" (with the time) while "a final done row is S098's row". Say whether the
  *To verify* row alone gets the time (a queue is read by time; recommended), or both rows.

## Checked and found consistent

- **v52, v53** (`local_db.py:1348`, `:1419`): `pm_jobs` has `timeliness ENUM NULL` then the generated
  `open_plan_id` with `uq_pm_jobs_open_plan`; `ix_pm_jobs_state (state, due_on)`; `chk_pm_jobs_done`
  = `(state NOT IN ('done','verified') OR done_at IS NOT NULL) AND (done_at IS NULL OR state IN
  ('done','verified','skipped')) AND (done_meter IS NULL OR done_at IS NOT NULL) AND (timeliness IS
  NULL OR state IN ('done','verified'))`, so `SEND_BACK_CHANGES` must clear all three, as § 5.1
  does; `chk_pm_jobs_started` as § 8.1's rows assume; `pm_job_results` with `outcome` and
  `limit_state`; `ADD COLUMN IF NOT EXISTS` / `ADD CONSTRAINT IF NOT EXISTS` is v53's pattern;
  `LATEST_VERSION = _MIGRATIONS[-1][0]`, so `test_modules.py` needs no edit.
- **`pm_work_core.py`**: `JOB_DONE` "This job is done and cannot be changed." (`done`, `verified`),
  `JOB_CANCELLED` "This job was cancelled." (`cancelled`, `skipped`), `REMARK_MAX` 500,
  `REMARK_TOO_LONG`, `REMARK_NOT_TEXT`, `TIME_TOO_OLD`, `DONE_EVENT`, `NOT_OK`, `NOT_DONE`;
  `state_error(state, action)` allows `in_progress` for fill, performer and done;
  `job_time_error(moment, now, not_before=None)`; the `TypeError` / `ValueError` rule.
- **`pm_work.py`**: `pm_work_bp` at `/api/pm`; `GET /jobs/<id>` (404 by `pm_job:read`'s units),
  `POST /jobs/<id>/done`; the pre-read (`plan_id`, `equipment_id`; 404); `_lock_job` = `LOCK_PLAN`
  (`SELECT * FROM pm_plans … FOR UPDATE`, so the locked plan row carries `needs_verification`) then
  `_LOCK_JOB`; `_share_node` = `SHARE_NODE` (`SELECT id, lifecycle … LOCK IN SHARE MODE`);
  `_work_access` = `load_node_for_user(cur, node_id, for_update=False, key=…)` (404 by
  `equipment:read`'s units through `_can_access`, then 403 at the site) then the state's 409 — the
  order § 5.2 gives; Mark done's order (6e) → (6f) → (1) shared → `NOW()` → plain, the job update
  `{state, done_at, done_meter, timeliness}` by `update_row`, the `done` event with
  `person_id=job["performed_by_id"]`, then `settle_plan_job`; `job_detail` builds on
  `pm_jobs.job_item` / `jobs_out`, sends `plan.needs_verification`, `can_start`, `can_work`,
  `events` with `person: {id, name}` and `created_by_name`; CR1-02's state check before the node
  lock on an item save (S099's verify and send back take the node shared after (6f) as Start does,
  with `verify_error` judged before the scrapped refusal, so the answers of § 5.2's order hold).
- **`pm_jobs.py`**: `_now` (`SELECT NOW()`, no table); `_last_base_job` `ORDER BY done_at DESC, id
  DESC` over `BASE_STATES` (§ 5.4's "latest done time"); `settle_plan_job` reads the open job
  plainly by `state IN (OPEN_STATES)` and leaves an `in_progress` job alone; `JOB_FROM` selects
  `j.*` (the new column arrives by itself) with `pl_needs_verification`, `site_id`, `unit_id`,
  `e_lifecycle`; `_DONE_WHERE` = `state IN ('done','verified')`, `ORDER BY j.done_at DESC, j.id
  DESC`, `_DONE_COUNT`, the answer `{items, counts, total, page, per_page}` and `_EMPTY` (which
  gains `to_verify: 0`); `_counts` over the open jobs; `assigned=me` = assignee or performer;
  `enum_arg("tab", TABS)` → "tab must be one of: …" (the text § 6.3 gives);
  `plan_schedules`'s `next_due`.
- **`pm_jobs_core.py`**: `DUE_STATE`, `IN_PROGRESS`, `DONE`, `VERIFIED`, `SKIPPED`, `CANCELLED`,
  `OPEN_STATES`, `BASE_STATES`, `CANCELLED_EVENT`, `TAB_DUE`, `TAB_UPCOMING`, `TAB_DONE`, `TABS`;
  `tab_of` and `list_order` take open jobs only (the new tab does not go through them, as *Done*).
- **RBAC**: `"pm_job:work": ("maint_technician",)` at `config_rbac.py:181` with its S098 comment
  (the style § 5.2's comment follows); `SITE_SCOPED` ends with `pm_job:read`, `pm_job:work`;
  `test_rbac.py`: `test_pm_job_work_key` (`:140`, the model for `test_pm_job_verify_key`), the
  matrix's comment lines `:266–268`, the engineer's and manager's rows.
- **Helpers**: `update_row(cur, table, record_id, clean, actor)`; `insert_row`; `has_perm_at(key,
  site_id)`; `current_person_id(cur)`; `clean_body`; `improvements._closed`'s `by_lead`
  (`closed_by_person_id == lead_id`, `:652`); `tickets_core.MOVES["send-back"]` →
  `IN_PROGRESS`, `SENT_BACK_EVENT`, a required remark.
- **Frontend**: the route `pm-job` at `/pm/jobs/:id`; `PmJobView.vue` has the header badges by
  `jobBadges`, the `pm-times` card "Performed by … · Started … · Done …", the read-only items, the
  History card (`PM_EVENT_LABELS[e.event]`, `e.person.name`, `recordedByText`, `e.remark`),
  `userPersonId`, and the done dialog through FormModal's `closed` event (the S077 rule and the
  call contract § 5.8 copies); `PmJobRow.vue` serves the list and *Me* › *Open work*
  (`MeView.vue:188`, `tab=due&assigned=me`), with `jobBadges` (*In progress* `text-bg-primary`;
  *Done* `text-bg-success` plus *On time* / *Late* for `done` and `verified`); `PmJobsView.vue`:
  `TABS` with static labels, `PagerBar` on *Done* at 50, `EMPTY_TEXTS` by tab and "No PM jobs
  match these filters.", the tab links by `.nav-tabs` role link; `TIMELINESS_LABELS`.
- **Browser tests**: `pm-job.spec.js` S098 test at `:88` ends with `/pm?tab=done` and the row by
  serial (`:117–118`); its other tests stop at `done` or before; `jobOf(machine, tab = "due")`
  is called with the default only; `screens.spec.js:73` finds *PM* by the *Due* link;
  `me.spec.js:207` lists a started job; `meterMachine(testInfo, tag, { unit })`, `apiAs(key)`,
  `personId(key)`, `expectDialogFits`, `expectNoSidewaysScroll` exist.
- **Docs**: `notes.json`'s `pm_jobs` line ends with the S098 sentences the brief's addition
  follows; Plan.MD `:763` still reads "**Needs-verification flag per plan** (*Proposed*,
  17-10-2026)".

## Feedback

- waste: the facts file `scratch/brief-facts-S099.md` was built before S097 and S098 were coded
  (it lists `pm_work.py`, `PmJobView.vue`, `pm-job.spec.js` as "no such file"), so none of its
  file, route or name lines could be used; every check went to the code (about 10 minutes of
  reads that a fresh `tooling/step-brief-facts.bat S099` run would have cut).
- idea: for a staleness review, the orchestrator runs `step-brief-facts.bat` again after the
  earlier steps are coded, and says so in the spawn prompt; the "planned in S0NN — re-check"
  marks then disappear by themselves.
