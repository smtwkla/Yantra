```
Step: S098 — Do the PM job on the phone
Doc: impl-report
Author: Coder (Opus)
Date: 02-11-2026
```

# S098 — implementation report

**Status of this report:** both rounds are done. Round 1 (the backend) is below; round 2 (the screens, the
frontend and browser tests, the code review r1 fixes, the full runs) follows it, under `## Round 2 — screens`.
The `## Manual checks` and `## Docs updated` sections cover the whole step.

## Round 1 — backend

**Result:** the backend of R03.4 is built as briefed. The `meters.py` split came first, and the readings tests
ran green on it before `pm_work.py` existed (275 passed). Then migration v53, the pure core `pm_work_core.py`
with its tests, the shell `pm_work.py` (the job page, *Start*, an item, the performer, *Mark job done*), the S097
changes (the *Done* tab, *in progress* on *Due*, *Assigned to me* with the performer), the scrap refusal, the key
`pm_job:work`, and the backend tests. The whole backend suite and the tooling suite are green (numbers in § 6).
No departure from the brief changes behaviour; the small choices are in § 4.

BACKEND ROUND DONE.

## 1. What was built (round 1)

- **`backend/meters.py`, the shared reading path (§ 5.5).** `_lock_node` is now the public `lock_node`.
  `log_reading`'s body is split into three public functions: `meter_in_force`, `reading_at_minute` and
  `write_reading` (the value, the same-minute rule, the counter's neighbours, the meter's own limit state, the
  insert with its `source`, the re-read). `remove_reading`'s last part is `remove_reading_row`. `log_reading` and
  `remove_reading` call them and answer exactly as before.
- **Migration v53** (`backend/local_db.py`): § 4.1 as written, three statements (two `ALTER TABLE pm_jobs`, one
  `CREATE TABLE pm_job_results`). No `_PRECONDITIONS` entry.
- **`backend/pm_work_core.py`** (new, pure): the constants and messages of § 5.1 and `result_rows`,
  `validate_result`, `result_changes`, `is_filled`, `unfilled_count`, `state_error`, `job_time_error`,
  `done_meter_counted`, with the message builders `not_all_filled`, `done_before_start`, `same_minute_pm`,
  `not_logged`, `finish_jobs_first`.
- **`backend/pm_work.py`** (new): the blueprint `pm_work_bp` at `/api/pm` with the five routes of § 6, the LOCK
  ORDER note of § 5.7, and `job_detail` (the job page's answer).
- **`backend/pm_jobs.py`** (S097's): the *Done* tab (paged, `total`), `assigned=me` = assignee or performer,
  `tab_of(state, standing)`, `list_order` with the job's state, `counts.in_progress`, the items' new fields
  (`performed_by`, `started_at`, `done_at`, `timeliness`), the card's `open_job.state`, and the S098 lines of
  its LOCK ORDER note.
- **`backend/pm_jobs_core.py`** (S097's): `TAB_DONE`, `TABS` of three, `tab_of(state, standing_state)`,
  `list_order` putting the started jobs first.
- **`backend/equipment.py`**: `_check_no_started_pm_jobs` beside `_check_no_open_tickets`, called with the same
  ids in `update_equipment`; the LOCK ORDER list gains "(6f) the PM job row" and the S098 bullet.
- **`backend/config_rbac.py`**: `"pm_job:work": ("maint_technician",)` with the brief's comment; the key joins
  `SITE_SCOPED`.
- **`backend/app.py`**: `pm_work_bp` registered after `pm_jobs_bp`.

## 2. How it works

**The pre-read and the locks.** Every write route first reads, outside its transaction, the job's `plan_id` and
`equipment_id` (and, for an item, the result's `meter_equipment_id`); these never change, so the read is safe and
gives the 404. The pool's connections are autocommit, so this read is its own snapshot and ends at once. The
transaction then takes `pm_jobs.LOCK_PLAN` (6e), then `SELECT * FROM pm_jobs WHERE id = %s FOR UPDATE` (6f), then
the node: `pm_jobs.SHARE_NODE` (shared) at *Start* and *Mark job done*, `meters.lock_node` (FOR UPDATE) on the
meter's node for an item that names a meter. Only then come the plain reads (the access check, the person, the
items, the readings), so the reading's neighbour checks see the newest rows.

**The checks' order on a write:** `require_perm("pm_job:work")` (403 held nowhere) → the pre-read (404) → the
locks → `load_node_for_user(…, key="pm_job:work")` (404 outside the units, 403 without the key at the site) →
`state_error` (409) → the body (400) → the refusals of the data (409: scrapped, no items, not all filled, the
same minute).

**Start.** The performer must be an integer ≥ 1 (not a boolean) of an active person with a membership at the
node's site (`tickets.person_at_site`); *Started* is now (to the minute) or a time from `parse_event_time`,
within `job_time_error`'s window. A node scrapped since the job was made answers 409 `SCRAPPED_MESSAGE` from the
locked row. The plan's active items are copied by `result_rows`, one insert each; the job becomes
`in_progress` with `performed_by_id` and `started_at`; the event `started` has `occurred_at` = *Started*.

**An item.** `validate_result` judges the body against the result's copied type and limits (and the meter type
when the item names a meter): the outcome by type, the value through `meters_core.validate_reading`, the remark
rules, the `limit_state` from the copied limits. `result_changes` compares with the stored row (and the sent reset
mark with the linked reading's): nothing changed writes nothing. For an item with a meter whose outcome, value or
reset mark changed, `_log_reading` runs § 5.5: the meter in force (none: the value stays on the job only, with
`meter_note`); the old reading removed through `remove_reading_row` only when its `source` is `pm` and it is
active; *NA* stops there; a reading at the same minute is linked when it has the same value and mark, else 409
`SAME_MINUTE_PM`; else `write_reading(…, source="pm")` at the job's *Started* time. A refused counter value raises
inside the transaction, so nothing is saved (D4). The result's `UPDATE` stamps `filled_at` and `filled_by`. The
answer is the item, the job's `filled_count` and `item_count`, and `meter_note`.

**The performer.** No `performed_by_id` in the body, or the same person: no write. Another person: the update and
the event `performer_changed`.

**Mark job done.** *Done* is now or a time in the window, not before *Started*. Any unfilled item → 409 "Fill
every item first: n of m are not filled.". `done_meter` is the plan's meter reading at or before *Done*, else the
first after it, else none; `timeliness` is `pm_schedule_core.timeliness` over the job's own copies
(`due_from_job`) with the counted value (`done_meter_counted`, the job's offset). One `UPDATE` sets `done`,
`done_at`, `done_meter`, `timeliness`; the event `done`; then `pm_jobs.settle_plan_job` makes the next job at
once only if it is already in its *Upcoming* window.

**The job page** (`GET /api/pm/jobs/<id>`): the header is the list's own item (`pm_jobs.job_item`, judged live
through `pm_jobs.jobs_out` for an open job), plus `equipment.lifecycle`, the plan's `active` and
`needs_verification`, `done_meter`, the items (the plan's active items for a due job, `id` null; else the
results), `filled_count`, `item_count`, the events with the person's and the recorder's names, `can_start` and
`can_work`. The 404 is by the node's root unit among `accessible_unit_ids(cur, "pm_job:read")`.

**The PM list.** `tab=done` reads `_DONE_SELECT` (the same joins as the open select, `state IN ('done',
'verified')`), newest `done_at` first, paged, with a `COUNT(*)` for `total`; its items go through the same
`job_item` with no standing. `counts` always comes from the open jobs; the started ones are counted apart in
`in_progress` (see § 4, D-c2).

**The scrap.** `_check_no_started_pm_jobs` counts `in_progress` jobs on the node and its parts (plain, under the
node locks the scrap holds) → 409 "Finish its PM jobs first (1 in progress)" on `lifecycle`.

## 3. Files touched (round 1)

| File | Change |
|---|---|
| `backend/meters.py` | `lock_node` public; `meter_in_force`, `reading_at_minute`, `write_reading`, `remove_reading_row` split out of the two routes; docstring names the PM path |
| `backend/local_db.py` | migration v53 |
| `backend/pm_work_core.py` | new: the pure rules |
| `backend/pm_work.py` | new: the five routes, the LOCK ORDER note, `job_detail` |
| `backend/pm_jobs.py` | `JOB_FROM` (public, + performer and four page columns), `_DONE_SELECT`, `_DONE_COUNT`, `job_item` (public), the *Done* tab, `assigned=me` with the performer, `counts.in_progress`, `open_job.state`, the LOCK ORDER lines |
| `backend/pm_jobs_core.py` | `TAB_DONE`, `TABS`, `tab_of(state, standing)`, `list_order` |
| `backend/equipment.py` | `_check_no_started_pm_jobs`, its call, the LOCK ORDER (6f) line and S098 bullet; `db_helpers` import wrapped (line width) |
| `backend/config_rbac.py` | `pm_job:work`, `SITE_SCOPED` |
| `backend/app.py` | `pm_work_bp` registered |
| `backend/tests/test_pm_work_core.py` | new: 66 tests of the core |
| `backend/tests/test_pm_work_api.py` | new: 33 tests (page, start, items, readings with the lock test, performer, clock, done, the plan's rules for a started job, the database down) |
| `backend/tests/test_migration_v53.py` | new: the fresh build, the ENUMs, the CHECKs, the unique key, a v52 database migrating, a re-run |
| `backend/tests/test_pm_jobs_api.py` | the changed lines of § 7 below; new class `TestStartedAndDone` (3 tests) |
| `backend/tests/test_pm_jobs_core.py` | `test_tab_of` with the state; new `test_tab_of_a_started_job_is_due_whatever_its_standing`, `test_list_order_puts_the_started_jobs_first`; `test_list_order`'s items gain `state`; `TABS` of three |
| `backend/tests/test_pm_generate.py` | `insert_job` takes `performed_by` (a started row needs `started_at` and `performed_by_id`); `test_a_started_job_is_left` passes the technician; `overdue`, `upcoming`, `_today` moved here from `test_pm_jobs_api.py` |
| `backend/tests/test_rbac.py` | `test_role_matrix` rows and comment; new `test_pm_job_work_key` |
| `backend/tests/test_equipment_api.py` | new `test_scrapping_with_a_started_pm_job_is_409` |
| `backend/tests/conftest.py` | `pm_job_results` first in `_TABLES` (the line wrapped) |
| `docs/schema/notes.json`, `schema.json`, `schema-data.js` | § Docs updated |
| `docs/Plan.MD`, `.claude/CLAUDE.md` | § Docs updated |

## 4. Decisions taken

- **D-c1. `pm_jobs.JOB_FROM` and `pm_jobs.job_item` are public**, not the brief's `_job_item`. `pm_work.py`
  builds the job page's header from the same item (one copy of the shape, CLAUDE-COMMON *DRY*), and it may use
  only public names of `pm_jobs` beyond the brief's `_now`. `job_item` takes a fourth argument `today` (the open
  item's `days_past`); for a done job (`standing` None) `days_past` is None. `JOB_FROM` gains five columns for
  the page: `pb.name` (the performer), `e.lifecycle`, `s.id AS site_id`, `pl.active`, `pl.needs_verification`.
- **D-c2. The standing counts leave the started jobs out.** `counts.overdue`, `due` and `upcoming` count the
  jobs not started; `in_progress` counts the started ones. So "4 due · 1 overdue · 2 in progress" adds up to the
  *Due* tab's rows, and a started job that would read *Upcoming* is not counted on the *Upcoming* tab, where it
  is not listed. The brief said only "`counts` gains `in_progress`". **Flag for the reviewer.**
- **D-c3. `remove_reading_row(cur, node_id, reading, field=None)`** takes an optional field, so the PM path's
  `RESET_HAS_LATER` lands on `value` (§ 5.5 step 3); the readings route passes none, as before.
- **D-c4. `reading_at_minute` returns the row** (with `source`), where `log_reading` counted; `write_reading`
  uses it as a count. The PM path needs the value, the mark and the id to link.
- **D-c5. `write_reading` takes the raw value** (`body["value"]`) and validates it again with the meter's rules.
  `meters_core.parse_number` refuses a `Decimal`, so the PM path passes the value as it came in the body, which
  `validate_result` has already judged with the same rules.
- **D-c6. Events through `pm_jobs._add_event`**, called through the module as `_now` is (no second insert helper).
- **D-c7. A check's *NA* needs no remark**; only a reading's *NA* does (§ 5.4's table). The core passes NA to the
  remark rule for a reading only.
- **D-c8. The result `UPDATE` is written in `pm_work.py`**, not with `db_helpers.update_row`: `pm_job_results`
  has no `updated_at` / `updated_by` (§ 4.1), which `update_row` stamps.
- **D-c9. `overdue`, `upcoming` and `_today` moved to `test_pm_generate.py`** (the shared test helpers), so
  `test_pm_jobs_api.py` can import `start`, `fill`, `done` from `test_pm_work_api.py` without an import cycle.
- **D-c10. The scrap test is in `test_equipment_api.py` on the machine itself.** A part is always scrapped
  before its machine, so a part's started job is refused at the part; the count over the parts is kept as the
  brief says (same ids as the tickets' check).
- **The core's tests were written after the core, not before.** The brief asked for them red first; I wrote
  `pm_work_core.py` first and the 66 tests then passed at the first run. No red run was shown. Stated, not hidden.

## 5. Not done, deferred or assumed (round 1)

- Round 2: the screens, the frontend tests, the browser tests, the device-check rows, Plan.MD § 2 (8) and § 6.
- `job_detail`'s `filled_count` counts the results with an outcome or a value (`is_filled`); a due job reads 0.
- A linked reading removed later by an engineer on the Meters card: the result keeps its `reading_id`
  (`logged` false); the same value saved again is no change, so it is not logged again. Assumed rare; no rule in
  the brief.

## 6. Tests (round 1)

- The readings split alone, before `pm_work.py` existed: `tests/test_readings_api.py tests/test_meters_api.py
  tests/test_meters_core.py` — **275 passed**.
- The core: `tests/test_pm_work_core.py` — **66 passed**.
- The touched suites together (`test_pm_work_api`, `test_pm_work_core`, `test_pm_jobs_api`, `test_pm_generate`,
  `test_pm_jobs_core`, `test_migration_v53`, `v52`, `v51`, `test_rbac`, `test_equipment_api`,
  `test_pm_plans_api`) — **629 passed**.
- Tooling suite (`tooling/run-tooling-tests.bat`, the line-width check) — **239 passed**.
- `tooling\schema-docs.bat write` — **4 passed** (at migration v53).
- The whole backend suite (`YANTRA_TEST_RUN=s098c1 tooling\run-backend-tests.bat`) — **5082 passed** in 145 s (the known
  `test_search_words_in_any_order` passed too in this run).

## 7. Changed lines of S097's tests

- `test_pm_jobs_api.py::TestList::test_the_operator_sees_the_overdue_job`: the item gains `"performed_by": None,
  "started_at": None, "done_at": None, "timeliness": None`.
- `…::test_the_upcoming_tab_and_the_counts`: `counts` gains `"in_progress": 0`.
- `…::test_an_unknown_tab_is_refused`: `tab=nonsense`, the text "tab must be one of: due, upcoming, done".
- `…::TestCard::test_the_open_job_and_the_next_due`: `open_job` gains `"state": "due"`.
- `test_pm_generate.py::TestCancel::test_a_started_job_is_left`: the inserted row has a performer and a start.

## Round 2 — screens

**Result:** the screens of R03.4 are built as briefed: the job page, the *Mark job done* dialog, one job row
shared by the PM list and *Me*, the PM list's *Done* tab and *In progress* badge, the PM card's *In progress*
badge, and *Me* › *Open work*'s PM jobs. The code review r1's five findings are answered below. Every unit suite,
the build check, the targeted and the Normal browser runs are green, and `tooling\schema-docs.bat check` exits 0
(numbers in § R2.5).

### R2.1 What was built

- **The job page** (`frontend/src/views/PmJobView.vue`, route `pm-job`, `/pm/jobs/<id>`, title "PM job"): the
  header (the badges of `jobBadges`, the serial as the heading, the machine and the plan as links, the unit and the
  due point with its days past); for a due job the card *Start job* (*Performed by*, *Started* with its *Now* tick,
  *Start job*) and the plan's items read-only under "These are the plan's items now. Start the job to fill them."
  (no card and "These are the plan's items now." for a reader; "This machine is scrapped. The job cannot be
  started." for a scrapped machine); for a started job *Performed by* (a change saves at once, "Saved"),
  *Started*, "3 of 7 filled", each item (check *OK* / *Not OK* / *NA*, task *Done* / *Not done*, reading a
  number with its unit, *Save*, *NA*, *High* / *Low* as it is typed, the *Meter reset* tick after a
  `counter_lower` refusal, the remark field for *Not OK*, *Not done* and a reading's *NA*, "Saving…", "Saved",
  the refusal or "Not saved: … Tap again." under the item, "Also logged as a … reading of …" or the
  `meter_note`), then *Mark job done* (disabled with "Fill all n items first. Your entries are saved as you go.");
  for a done job the card "Performed by … · Started … · Done …" and each result as text with "Filled by …";
  *History* in every state ("by the daily PM run" for the run's lines). A 404 shows "PM job not found, or not at
  your units." with *Back to PM*; another failure "PM job could not be loaded: …" with *Retry*.
- **The dialog** (`frontend/src/views/pm/PmJobDoneDialog.vue`): *Done* (EventFields, `pm-done`), the line
  "Started … · n of n filled", the consequence "The job can no longer be changed.", the button *Mark job done*.
- **One row** (`frontend/src/components/PmJobRow.vue`), class `job-row` and `data-equipment` kept: badges, serial,
  the due point or "Done <date>", the machine, the plan and item count, a small line (a started job: "In progress
  · <performer>"; a done one: "by <performer>").
- **The PM list** (`PmJobsView.vue`): tabs *Due*, *Upcoming*, *Done*; *Done* paged with `PagerBar` (page in the
  URL); the count line through `countText` ("… · 2 in progress", "12 done"); "No PM jobs are done yet.".
- **The PM card** (`PmPlansCard.vue`): the open job's badges through `jobBadges` (*In progress* first).
- **Me** (`MeView.vue`): "PM jobs (n)" with the rows above the countermeasures, page 1 of *Open work*, for a
  `pm_job:read` holder with a Team record; *Tickets* heading when either section above has rows.
- **Labels** (`pmLabels.js`): `RESULT_LABELS`, `RESULT_BADGES`, `OUTCOME_BUTTONS`, `REMARK_PROMPTS`,
  `TIMELINESS_LABELS`, `LIMIT_FLAG_LABELS`, `PM_EVENT_LABELS`, `RUN_ACTOR`, `PM_TABS`, `recordedByText`,
  `jobBadges`, `limitFlag`, `notSavedText`, `filledText`, `resultBody`, `resultText`, `readingUnit`;
  `countText(tab, counts, total)`, `jobsQuery` with the Done tab and its page.

### R2.2 Files touched (round 2)

| File | Change |
|---|---|
| `frontend/src/views/PmJobView.vue` | new: the job page |
| `frontend/src/views/pm/PmJobDoneDialog.vue` | new: *Mark job done* |
| `frontend/src/components/PmJobRow.vue` | new: one job row (taken out of `PmJobsView.vue`) |
| `frontend/src/router/index.js` | the `pm-job` route |
| `frontend/src/views/PmJobsView.vue` | *Done* tab, pager, rows through `PmJobRow`, the count line |
| `frontend/src/views/equipment/PmPlansCard.vue` | `jobBadges` on the open job |
| `frontend/src/views/MeView.vue` | the "PM jobs (n)" section |
| `frontend/src/utils/pmLabels.js` | the helpers of R2.1 |
| `frontend/tests/pmLabels.test.js` | the new helpers' tests (8 `describe` blocks) |
| `frontend/e2e/pm-job.spec.js` | new: 10 tests (§ 8.4) |
| `frontend/e2e/pm-jobs.spec.js` | the changed S097 test (the row opens the job page) and one S098 test |
| `frontend/e2e/me.spec.js` | one S098 test |
| `frontend/e2e/screens.spec.js` | the job page in `screens()`; the set-up plan gains `last_done_on` 40 days back |
| `backend/pm_work.py`, `backend/pm_jobs.py` | the code review r1 fixes (below) |
| `backend/tests/test_pm_work_api.py`, `backend/tests/test_pm_jobs_api.py` | three tests for those fixes |
| `docs/steps/device-checks.md`, `docs/Plan.MD` | § Docs updated |

Changed lines of S097's `pm-jobs.spec.js` (`S097: a plan saved past due shows its job as Overdue on the PM
list`): the last three lines (`row.click()`, the URL `/equipment/pm/<plan.id>`, the heading "S097 overdue
plan") became `jobOf(machine, plan)`, `row.click()`, the URL `/pm/jobs/<job.id>` and the job's serial as the
heading; a helper `jobOf` was added. Its title and every other test are unchanged.

### R2.3 Decisions taken (round 2)

- **D-c11. The started job's own count on the row** (CR1-03, below): `plan.item_count` of a started or done job is
  its result count, so the row's "· n items" is the job's.
- **D-c12. `countText(tab, counts, total)`** takes the Done tab's `total` as a third argument (the brief:
  "`countText` gains the *Done* tab"), since `counts` holds only the open jobs.
- **D-c13. The Me test asserts "PM jobs (n)" by pattern, not "PM jobs (1)".** Other specs in the same lane assign
  PM jobs to the seed technician, so a fixed count would depend on the lane's order. The test finds its own row by
  the machine.
- **D-c14. The page's own item state** (the typed value, the open remark, "Saved", the refusal) lives in one
  reactive map by result id in `PmJobView.vue`; the item row is not a separate component. One page uses it; a
  component would add props and events for no second use.
- **D-c15. "Not saved: <message>. Tap again."** drops the message's last full stop (`notSavedText`), so the
  network text reads "Not saved: No connection. Check Wi-Fi or mobile data and try again. Tap again.". The brief's
  words, with "try again" and "Tap again" side by side: **flag for KLA** (scope B: two retries in one line).
- **D-c16. *Mark job done* hands the job over on FormModal's `closed`**, as the brief's S077 rule says.
- **D-c17. A save the state refuses opens nothing on the page**: a 409 shows its message under the item; the page
  does not reload by itself. *Start job*'s 409 without a field (started by another person) reloads the job.
- **D-c18. Browser tests that expect a 400 name it** with `consoleWatch.allowFailedRequest`, and the network-drop
  test names Chromium's `ERR_INTERNET_DISCONNECTED` with `allowBrowserError` (S024 conventions).

### Code review r1 fixes

| Finding | Answer |
|---|---|
| CR1-01 (minor) | **Fixed.** `_log_reading` now removes the job's own `pm` reading **before** the meter-in-force check, and a gone meter returns `(None, not_logged(…))`: the result lets go of its link. **Stated decision:** this changes § 5.5 step 1's "`reading_id` stays as it is" to "the job's own reading is removed and the link let go", so an *NA* keeps `chk_pm_job_results_reading` and a new value is never shown as logged (D4). New test `test_pm_work_api.py::TestMeterReadings::test_a_meter_removed_after_a_logged_value_lets_go_of_the_reading` (a value logged, the meter removed, then *NA*, then a new value). Fails without the fix: `assert 500 == 200` (4025 on `chk_pm_job_results_reading`); passes with it. |
| CR1-02 (nit) | **Fixed.** `save_result` judges the job's state right after (6f): a refused state runs the plain access check (404 / 403) and answers the state's 409, before any node lock. So a late save on a done job whose machine was scrapped since answers `JOB_DONE`. The LOCK ORDER note says so. New test `…::test_a_late_save_on_a_done_job_of_a_scrapped_machine_says_done`. Fails without the fix: the message was the scrapped refusal, not "This job is done and cannot be changed."; passes with it. |
| CR1-03 (nit) | **Fixed, by the job's own count.** `pm_jobs.JOB_FROM` gains `result_count` (the job's `pm_job_results`), and `job_item` sends it as `plan.item_count` for a started or done job (the plan's active items for a due job). Chosen over hiding the count: the row keeps one shape for every state. New test `test_pm_jobs_api.py::TestStartedAndDone::test_a_started_job_counts_its_own_items`. Fails without the fix: `assert 3 == 2`; passes with it. |
| CR1-04 (nit) | **Fixed.** `pm_jobs._add_event` is now the public `add_event`; `pm_jobs.py` and `pm_work.py` call it. |
| CR1-05 (nit) | Nothing to do (accepted by the review). |

### R2.4 Not done, deferred or assumed (round 2)

- The browser tests check the 48 px buttons on the Android phone (`@device`: at least 44 px, the brief's number);
  the gloved thumb and the keypad are device checks (rows 65, 66).
- The Me test does not check the count 1 (D-c13).

### R2.5 Tests (round 2)

- New browser spec alone (`E2E_LANES=1`, `e2e/pm-job.spec.js --project=phone-chromium -g S098`): first run 10
  failed (the route's `\\d+` lost a backslash: every job page was "Page not found"); after the fix 5 failed
  (one test waited for *Not done* to read pressed before its remark; four met their own expected 400s and the
  offline error in the console watch); after those, **10 passed**.
- Code review r1: the three new backend tests red without the fixes, green with them (table above).
- Targeted (Normal: `pm-job`, `pm-jobs`, `me`, `pm-plans`, `readings`, `screens`): **113 passed, 1 skipped**, 98 s.
- All unit suites once (`YANTRA_TEST_RUN=s098c1 tooling\run-tests.bat`): backend **5085 passed**, frontend
  **447 passed**, tooling **239 passed**.
- Build check (`npx vite build` in `frontend/`): built; the old chunk-size warning only.
- Whole browser suite at Normal (`tooling\run-e2e-tests.bat`), once: **408 passed, 1 failed, 15 skipped**, 252 s (6 lanes). The one failure is `labels.spec.js:57` "labels printed from the equipment list's ticks" on `desktop-chromium`: the seed extruder EXT001 was on page 2 of the equipment list (72 machines, 50 per page; the CMP machines other specs of lane 1 made sort before EXT). S098's machines are class HP and sort after it, so it is the lane's order, not this step. Re-run alone (`tooling\run-e2e-tests.bat e2e/labels.spec.js`): **6 passed**. Not fixed here (outside the step); **flag for the orchestrator**: a third order-dependent test beside the two known ones.
- `tooling\schema-docs.bat check`: exit 0, **4 passed** at migration v53.

## Manual checks

- [auto] a technician starts a due job, fills each item and marks it done — `frontend/e2e/pm-job.spec.js`::S098: a technician starts a due job, fills each item and marks it done
- [auto] each item is saved as it is filled; a reload keeps them — `frontend/e2e/pm-job.spec.js`::S098: each item is saved as it is filled; a reload keeps them
- [auto] a reading out of its limits shows High as it is typed — `frontend/e2e/pm-job.spec.js`::S098: a reading out of its limits shows High as it is typed
- [auto] Not OK needs a remark and shows on a red row — `frontend/e2e/pm-job.spec.js`::S098: Not OK needs a remark and shows on a red row
- [auto] a reading that logs a meter is refused on the item when the counter is lower — `frontend/e2e/pm-job.spec.js`::S098: a reading that logs a meter is refused on the item when the counter is lower
- [auto] recorded on behalf: another person and a start two days back — `frontend/e2e/pm-job.spec.js`::S098: recorded on behalf: another person and a start two days back
- [auto] a started job keeps its items when the plan changes — `frontend/e2e/pm-job.spec.js`::S098: a started job keeps its items when the plan changes
- [auto] a save during a network drop says Not saved and keeps the tap; it saves on the next tap — `frontend/e2e/pm-job.spec.js`::S098: a save during a network drop says Not saved and keeps the tap; it saves on the next tap
- [auto] IT admin and the operator read the job and have no Start job — `frontend/e2e/pm-job.spec.js`::S098: IT admin and the operator read the job and have no Start job
- [auto] the job page fits a phone with large item buttons — `frontend/e2e/pm-job.spec.js`::S098: the job page fits a phone with large item buttons
- [auto] Me › Open work lists my started PM job above the tickets — `frontend/e2e/me.spec.js`::S098: Me › Open work lists my started PM job above the tickets
- [auto] a started job shows In progress on the Due tab — `frontend/e2e/pm-jobs.spec.js`::S098: a started job shows In progress on the Due tab
- [auto] the job page opens for every pm_job:read role — `frontend/e2e/screens.spec.js` (the `/pm/jobs/<id>` entry of `screens()`)

On a real device (rows of `docs/steps/device-checks.md`):

- [ ] **important** A gloved thumb: with a work glove, OK, Not OK, NA and Done each hit the button meant (row 65).
- A real Wi-Fi drop on the plant Wi-Fi: "Not saved … Tap again.", then "Saved" back in range (row 64).
- The number keypad on the iPhone and Android: the decimal keypad shows and *Save* is not hidden (row 66).

## Docs updated

- `docs/schema/notes.json`: `pm_job_results` moved from `planned` to `tables` (area *Preventive maintenance*,
  whose note gains "job results (S098)"); the `pm_jobs` line names `performed_by_id`, `started_at`, the CHECK and
  S098's states; the `meter_readings` line: `source` `pm` since S098 and the result's `reading_id`. Then
  `tooling\schema-docs.bat write`; `git diff docs/schema/` read: `pm_job_results` with its keys, foreign keys and
  CHECKs, `pm_jobs`' two columns, key, foreign key and `chk_pm_jobs_started`, migration 53. `check` at the end:
  see R2.5.
- `docs/Plan.MD`: § 3 a `pm_job:work` paragraph with the stated departure; § 4.3 *PM job* a *Built (S098)*
  paragraph; § 2 (8) and § 6 (*Me*): the PM jobs in *Open work*, CIL jobs in R03.12.
- `.claude/CLAUDE.md`: § Step workflow *Self-check* (2) names `pm_work.py`; § SMTW-Review: *Meter readings (S039)*
  names the PM path, and the new point *PM job results (S098)*.
- `docs/steps/device-checks.md`: rows 64–66 (§ 8.5).
- `docs/Keycloak.md`: none, because no Keycloak role, client or claim changes.

## Shared docs

None: not in a worktree. The brief's status and its row in `docs/steps/INDEX.md` are set to *In code review*.

## Feedback

### Round 1

- waste: the brief asked for the core's tests red first, and I wrote the core first out of habit; a red run after
  the fact would have been theatre (`test_pm_work_core.py`, 0 min lost, one rule missed).
- hindrance: `awk length` in Git Bash counts bytes, so a line with "›" or "–" reads too long; only the tooling
  suite's line-width test is a true check (1 false lead, `backend/meters.py:218`).
- idea: `test_pm_jobs_api.py` and `test_pm_work_api.py` share plan builders; a small `tests/pm_helpers.py` (as
  `migration_helpers.py`) would stop helpers moving between test modules to avoid import cycles (D-c9).

### Round 2

- waste: a route regex written through a Python script lost one backslash (`"\\d+"` became `"\d+"`, which JS reads
  as `d+`), so the first browser run of the new spec failed 10 of 10 on "Page not found" (one run, 4 min). Editing
  JS through a script's string literals doubles the escaping problem; the Edit tool would not have.
- hindrance: the console watch fails a test on its own expected 400 or offline error until the test names it; the
  convention lives only in `e2e/support/console.js`'s header (one run, 4 of the 5 failures).
- idea: a check in the targeted run that each new `router/index.js` path actually matches a sample URL (a vitest
  over the routes) would catch a broken pattern in a second instead of a browser run.
- waste: patching this report by script failed four times on quoting and on a cut point (`## Docs updated` also
  appears in the status line); writing the section with the Edit tool would have been one call (about 6 min).

## Fix rounds

### Round 1 (code review r2)

All seven findings fixed. Run name `s098f1`.

| ID | Answer |
|---|---|
| CR2-01 | **Fixed.** `PmJobView.vue`: the "Also logged as …" line shows only when `item.logged` is true or the last save in this visit sent a `meter_note`. The test `S098: a reading that logs a meter is refused …` now asserts the row has no "Also logged" before the 1,270 save. Fails without the fix: `expect(row).not.toContainText("Also logged")`, received text ends "…Also logged as a Run hours reading of HP001."; passes with it. |
| CR2-02 | **Fixed.** `notSavedText(message)` returns `` `Not saved. ${message}` `` (the `meterLabels.NOT_SAVED` shape). Texts now: "Not saved. No connection. Check Wi-Fi or mobile data and try again." and "Not saved. Yantra is not answering. Try again in a minute." Updated: the `notSavedText` unit test, the `PmJobView.vue` header comment, the doc comment, `pm-job.spec.js` (the network-drop test now asserts "Not saved. No connection." on the item and on the performer line), and row 64 of `docs/steps/device-checks.md`. **This changes the brief's words in § 5.10, § 5.12 and § 8.5, decided by the orchestrator, for KLA at gate B. The brief is not edited.** Unit test fails without the fix: expected "Not saved. No connection. …", received "Not saved: No connection. … Tap again."; passes with it. |
| CR2-03 | **Fixed.** `changePerformer`'s `catch` sets `event.target.value` back to the saved performer. The network-drop test now changes *Performed by* offline, asserts the "Not saved. No connection." line and that the select shows the saved person again. **Red not possible:** with the reset removed this test still passes, because Vue re-patches the select's `:value` when `performer.saving` flips the `disabled` attribute. The reset stays as a guard that does not depend on that re-render; the test is a regression check only. |
| CR2-04 | **Fixed.** `resultText` uses `formatReading(item.value, item.meter.meter_type)` for an item with a meter ("1,270 h"), and the raw value with `item.unit` for a free reading. Unit test changed to expect "1,270 h"; fails without the fix: received "1270 h"; passes with it. |
| CR2-05 | **Fixed.** `PmJobsView.vue`: `DONE_PAGE_SIZE` removed; `PagerBar` gets `answer.per_page`. No test (the pager spec in `pm-jobs.spec.js` still passes). |
| CR2-06 | **Fixed.** `me.spec.js` S098 test reads the number in "PM jobs (n)" and asserts `.job-row` count equals it, and that the PM heading's top is above the *Tickets* heading's. |
| CR2-07 | **Fixed.** `PmJobView.vue` `load()` treats a 403 like a 404: "PM job not found, or not at your units." with *Back to PM*. No test added: the storekeeper path has no existing spec fixture and the change is one condition. |

**Tests (round 1):**

- `tooling/run-frontend-tests.bat tests/pmLabels.test.js`: 34 passed.
- `npx vite build` in `frontend/`: built in 4.7 s (old chunk-size warning only).
- Targeted browser run `e2e/pm-job.spec.js e2e/pm-jobs.spec.js e2e/me.spec.js e2e/screens.spec.js` (Normal): all lanes exit 0, 49 passed, 1 skipped.
- Full suites not re-run: the round changes only frontend files and one docs row.

**Docs updated:** `docs/steps/device-checks.md` (row 64 wording). Others: none, because no module, rule, schema, role or secret changed.

### Feedback

- none
