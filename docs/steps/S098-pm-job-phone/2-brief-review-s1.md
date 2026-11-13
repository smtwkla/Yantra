```
Step: S098 — Do the PM job on the phone
Doc: brief-review s1
Author: brief-reviewer (Fable 5.1)
Date: 02-11-2026
```

Reviewed against: c9cd091 + uncommitted S095, S096, S097 (the working tree equals `refs/steps/S097`,
4e4821c, for every file checked, the S097 fix round included: `pmLabels.js` already has `dueValueText`)

# S098 — Staleness review s1

**Verdict: no blocker or major finding. The brief's design holds against the coded S095–S097.** One
minor finding (the *Done* tab's rows cannot go through `jobs_out` as it is) and nine nits, all wording,
names and anchors. The coder can start once the Review log answers them.

**Scope of this round:** only the question of `docs/steps/README.md` § Stale brief check: does each
statement of the brief about S095–S097's code still hold? I checked § 3 (every S095, S096 and S097 name),
§ 4.1 (against v51 and v52), § 5.1 (the imported names and texts), § 5.3–§ 5.7 (the signatures, the
lock statements, the LOCK ORDER notes as coded), § 5.9–§ 5.11 (the S097 screens and helpers), § 6.2–§ 6.3
(the answer shapes), § 8.3 (the S097 tests the step changes) and § 9 A1–A3. I did not re-review the rest.

**Facts file:** `scratch/brief-facts-S098.md` is from 00:25 on 02-11-2026, before `pm_jobs.py`,
`pm_jobs_core.py`, `PmJobsView.vue` and `pm-jobs.spec.js` existed (it lists them as "no such file"),
so every S097 name was checked in the working tree, not from it. The S095 and S096 entries in it hold.

## Findings

### BS1-01 — minor — § 3, § 6.3: `jobs_out` and `_JOB_SELECT` serve open jobs only; the *Done* tab needs its own path

- **What the code is:** `pm_jobs._JOB_SELECT` (`backend/pm_jobs.py:91-103`) ends in
  `WHERE j.state IN ('due','in_progress')`. `jobs_out(cur, rows, today)` (`pm_jobs.py:316-347`) judges
  every row's standing live (`job_state(due_from_job(row), …)`, a `Due` that needs the job's windows) and
  sorts with `list_order`, which raises `ValueError` on a missing standing. `plan_schedules` (`:392-424`)
  builds the card's `open_job` from the same items.
- **What the brief says:** § 3 "`jobs_out` gains `performed_by`, `started_at`, `done_at`, `timeliness`",
  § 6.3 "For *Done*: the jobs in `BASE_STATES` … `ORDER BY done_at DESC, id DESC`, paged", § 6.2
  "`standing` … null for a done, cancelled or skipped job". Read together they imply `jobs_out` builds the
  done rows too. As coded it cannot: the select excludes them, the judging loop needs the standing, and
  the sort is by standing, not by `done_at`.
- **Why it matters:** the coder has to design the split alone (a parameter on `jobs_out`, a second select,
  a second builder), and the choice touches the card's `open_job` and the list's `counts`.
- **Options:**
  - (a) **Recommended.** Keep `_JOB_SELECT` and `jobs_out` for open jobs as they are. Add in `pm_jobs.py`
    a `_DONE_SELECT` (the same joins, `WHERE j.state IN ('done','verified')`, the `ORDER BY` and
    `LIMIT … OFFSET` of § 6.3, plus `COUNT(*)` for `total`) and move the item dict of `jobs_out` into one
    function `_job_item(row, standing, reading)` that both loops call; the done loop passes
    `standing=None, reading=None`, so the item shape of § 6.2 stays one copy. `counts` keeps coming from
    one open-jobs query (`_counts`, with `in_progress` added, and `_EMPTY` too), so the tab counts do not
    depend on the page.
  - (b) One `jobs_out(cur, rows, today, judged=True)` with a flag that skips the standing and the sort.
    Fewer names, but a flag that changes what a function does is the pattern CLAUDE-COMMON asks to avoid.
- **The fix to the brief:** § 3 (`pm_jobs.py`) and § 6.3 name the done path as in (a).

## Nits

- **BS1-02** (nit) § 5.7: the lock statements are spelled out; the code has them as `pm_jobs.LOCK_PLAN`
  (`SELECT * FROM pm_plans WHERE id = %s FOR UPDATE`) and `pm_jobs.SHARE_NODE` (`SELECT id, lifecycle FROM
  equipment WHERE id = %s LOCK IN SHARE MODE`), and `pm_plans.py:87-88` already takes them from `pm_jobs`
  (S097 impl § 4). Name the two constants in § 3's `pm_work.py` imports and § 5.7, so `pm_work.py` reuses
  them.
- **BS1-03** (nit) § 6.2: the item's `meter.meter_type` `{id, name, unit, kind, decimals}` is the shape of
  `pm_jobs.meter_type_out(row)` (`pm_jobs.py:289-295`, the one copy after S097 CR1-04; `pm_plans.py` uses
  it). Name it in § 3's imports and § 6.2 instead of a new dict.
- **BS1-04** (nit) § 3, the S097 names: add `pmLabels.countText(tab, counts)` (§ 5.9 changes the count
  line, which it builds; `PmJobsView.vue:56`) and `nextDueText`; `pm_jobs_core.VERIFIED`, `SKIPPED`,
  `CANCELLED`, `JOB_STATES` (§ 5.2's table names those states) and `RUN_ACTOR` (`"pm_generate"`: § 5.10's
  "by the daily PM run" is `created_by == RUN_ACTOR`); the two call sites the § 5.9 changes touch:
  `list_jobs` calls `tab_of(item["standing"]["state"])` (`pm_jobs.py:388`) and `jobs_out` builds
  `list_order`'s item from the standing only (`pm_jobs.py:328`), so both get the job's `state`, and the
  items of `test_pm_jobs_core.test_list_order` (`:270`) gain one.
- **BS1-05** (nit) § 3 and § 4.1, the v52 shape: `pm_jobs` also has `created_why ENUM('calendar','meter')
  NOT NULL` (the migration test's v52 rows of § 8.1 must set it), `created_by`, `updated_at`, `updated_by`,
  and `open_plan_id` is a generated PERSISTENT column (`CASE WHEN state IN ('due','in_progress') THEN
  plan_id END`): § 5.3 step 2 and § 5.6 step 4 read right, but say "generated, never written".
  `pm_job_events` also has `id`, `due_on`, `due_meter`, `created_at`. And v52's `chk_pm_jobs_done`
  (`done` / `verified` need `done_at`; `done_at` only in `done`, `verified`, `skipped`; `done_meter` needs
  `done_at`; `timeliness` only in `done` / `verified`) sits beside the new `chk_pm_jobs_started`: name it in
  § 4.1 so the one `UPDATE` of § 5.6 step 4 is seen to satisfy both.
- **BS1-06** (nit) § 5.10: `tickets.list_people` is at `backend/tickets.py:789` (not 787); its route is
  `GET /api/tickets/people` under `require_perm("ticket:raise")`, and `?equipment_id=` goes through
  `_picker_anchor` → `load_node_for_user(…, key="ticket:raise")`; the answer's people carry `role` and
  `vendor_name` (`people_at_site`, `:753`), which `personLabel` reads.
- **BS1-07** (nit) § 5.10: `EventFields.vue` lives at `frontend/src/views/tickets/EventFields.vue` (not
  `components/`); its `idPrefix` prop is required (`:36`), beside `withRemark` and `timeLabel`.
- **BS1-08** (nit) § 8.3, `pm-jobs.spec.js`: the test's "last sentence" is the S097 brief's; in the spec
  the change is lines 66-68 (`row.click()`, the URL `/equipment/pm/<plan.id>`, the heading "S097 overdue
  plan"). Its row locator is `.job-row[data-equipment="<code>"]` (`:47`), so § 3's `PmJobRow.vue` keeps
  the class `job-row` and the `data-equipment` attribute of `PmJobsView.vue:126-127`.
- **BS1-09** (nit) § 8.4, `screens.spec.js`: its set-up already saves "Screens test: monthly check" as the
  engineer (`:38-44`), a monthly calendar plan with no `last_done_on`, so no job exists today. Say that the
  set-up adds `last_done_on` 40 days back to that plan (one plan, one job, `pmPlan` unchanged) rather than
  a second plan.
- **BS1-10** (nit) § 1, § 3: the facts file is stale for S097 (above); the orchestrator may run
  `tooling/step-brief-facts.bat S098` again before the coder starts, so the coder's copy lists
  `pm_jobs.py`'s names and their users.

## Checked and found consistent

- **S095:** `pm_schedule_core.timeliness(due, done_on, done_meter)` (`:251`), `ON_TIME`, `LATE` (`:29`);
  `done_on` must be a `date` (`_date(…, required=True)`: § 5.6's `done_at.date()` is right); `done_meter`
  a `Decimal`, `int` or None (`_meter_value`).
- **S096:** v51's `pm_plans` and `pm_plan_items` columns as § 3 lists them; `pm_plans_core.TASK`, `CHECK`,
  `READING`, `ITEM_TYPES`, `PHOTO_SETTINGS`, `STORED_DECIMALS = 3`, `item_limits_text(item, meter_type=None,
  meter_code=None)`, `PERFORMER_NEEDED` ("Choose who does the jobs.", so the rename of BR1-05 stands),
  `ITEMS_NEEDED` (at least one item: `NO_ITEMS` unreachable, as § 5.1 says); `pm_plans.py`'s LOCK ORDER
  note: (6e) first, "every item write holds (6e)" (`:29`), "a removed item is set inactive" (`:9`), "R03.3's
  daily run and R03.4 must keep this: the plan first" (`:35`); `pmLabels.personLabel` (`:72-75`);
  `PmPlansCard.vue` reads `p.schedule.open_job.standing.state` (`:96-97`) — `state` can join `open_job`
  (`plan_schedules`, `:408`).
- **S097:** `settle_plan_job(cur, plan_id, node_lifecycle, now, actor)` (`:210`; CR1-02 made it answer
  None when nothing is written — the brief never reads the answer); it skips `schedule_inputs` and
  `decide` answers None for an `in_progress` job (`pm_jobs_core.py:90-91`), so "`settle_plan_job` is
  unchanged" holds; after Mark done it finds no open job, reads the done row through `_last_base_job`
  (same transaction) and may `CREATE` under (6) — § 5.6 step 6 as written. `pm_jobs._now(cur)` (`:106`,
  `SELECT NOW()`, no table: no snapshot). `jobs_out(cur, rows, today)`, `plan_schedules`, `pm_jobs_bp`,
  `GET /api/pm/jobs` with `enum_arg("tab", TABS)` (the 400 text is `f"{name} must be one of: …"`, so
  "tab must be one of: due, upcoming, done" follows) and `assigned` as `j.assignee_id = %s` (`:383`).
  `pm_jobs_core.DUE_STATE`, `IN_PROGRESS`, `DONE`, `OPEN_STATES`, `BASE_STATES`, `TABS`, `TAB_DUE`,
  `TAB_UPCOMING`, `decide`, `due_from_job`, `tab_of(standing_state)`, `list_order(item)`. S097 writes only
  `due` (`_create`) and `cancelled` (`_cancel`), so A3 and § 4.1 *Existing rows* hold. `pm_jobs.py`'s
  LOCK ORDER note ends with "a job write (start, an item, done) takes its plan (6e) first, then the job"
  (`:47-48`), and "no module reads a job FOR UPDATE by open_plan_id" (the brief's (6f) is by `id`).
  `equipment.py`'s list has (6e) with "its jobs' rows (pm_jobs.py, S097) only under it" (`:28-29`) and
  the (6e) bullet with the S097 lines (`:84-93`): § 5.7's additions fit. `.claude/CLAUDE.md`'s self-check
  (2) already names `pm_plans.py` and `pm_jobs.py`.
- **`meters.py`:** `_lock_node(cur, node_id, key)` (`:133`, 404 / 403 / 409 as § 5.5 says);
  `log_reading`'s body (`:398-436`) has the `next(…)` over `_meters_of`, the same-minute `count`,
  `counter_error` against `_neighbour` both ways, `_limit_state`, the `insert_row` (no `source` set
  today: the column's default is `manual`) and the re-read; `remove_reading` (`:439-460`) keeps 404 and
  `ALREADY_REMOVED`, then `reset_removal_error` and the update. `last_readings(cur, node_ids, until=None)`
  → `{(node, type): row}`; `first_reading_after(cur, equipment_id, meter_type_id, after)`;
  `meters_with_last`. `meter_readings.source` is `ENUM('manual','pm','move','iiot')` (schema, `:631`), so
  `source="pm"` needs no migration. `meters_core`: `validate_reading(value, kind, decimals, reset, note)`,
  `limit_state(value, low, high)`, `GAUGE`, `format_number`, `READING_BACKDATE_DAYS = 7`, `to_minute`,
  `LOW`, `HIGH`, `RESET_NOT_BOOL`, `ONLY_A_COUNTER_RESETS`, `COUNTER_LOWER = "counter_lower"`.
- **Other names § 3 cites:** `tickets_core.FUTURE_SKEW`, `EVENT_TIME_FUTURE`, `EVENT_TIME_FORMAT`,
  `parse_event_time`, `close_tickets_first`; `tickets.person_at_site` (`:371`), `PERSON_AT_SITE` (`:140`);
  `api_common.ApiError`, `actor`, `clean_body`, `int_arg`, `enum_arg`, `MAX_PAGE`, `DEFAULT_PER_PAGE`,
  `MAX_PER_PAGE`; `equipment.load_node_for_user(cur, node_id, for_update, key=None)` with `_can_access` on
  `equipment:read`'s units (BR1-19 holds), `accessible_unit_ids`, `SCRAPPED_MESSAGE`,
  `_check_no_open_tickets(cur, node_ids)` called in `update_equipment` (`:924`);
  `improvements._lock_action_for_documents`; `config_rbac`: `pm_job:read` `("maint_operator", "it_admin")`
  with the comment "Doing a job is pm_job:work (R03.4)" and in `SITE_SCOPED`; `ticket:raise` to the
  operator and up (every `pm_job:work` holder has it); `app.py` registers `pm_jobs_bp` at `/api/pm`
  (`:209`); the router's `pm` route (`/pm`) and `navigation.canOpenRoute` by path prefix, so
  `/pm/jobs/<id>` is behind `pm_job:read` as the nav item is; `conftest._TABLES` starts with
  `pm_job_events`; `test_pm_generate.py:234` inserts an `in_progress` row through `insert_job`;
  `test_pm_jobs_api.py:114-116` asserts `tab=done` → 400 "tab must be one of: due, upcoming";
  `test_pm_jobs_core.test_tab_of` calls `tab_of(state)`; `test_readings_api.py:212`
  `test_two_writers_on_one_node_serialise_and_the_second_sees_the_first`;
  `test_equipment_api.py:368` `test_scrapping_with_live_parts_is_409`; `test_migration_v51.py` and
  `_v52.py` filter `_MIGRATIONS` by version; `ReadingsSheet.vue:240` shows the reset tick on
  `counter_lower`; `api.js` sets `err.status = 0` with `NO_CONNECTION_TEXT`; `db_helpers.py:45` "Pool
  connections are autocommit"; `local_db.py` `"autocommit": True`; `seed_e2e.py:47` "Ramesh (operator, no
  phone)" at SMTW MCC2; `support/meters.js` `meterMachine(testInfo, tag, { unit, modelMeters, ownMeters })`
  and `logByApi`; `MeView.vue` loads with one `Promise.all` (`:111`) and has `me-countermeasures`;
  `PagerBar.vue`; `screens.spec.js` `TICKET_ROLES`; `docs/schema/notes.json` has `pm_job_results` under
  `planned` and the `meter_readings` sentence § 3 quotes; `docs/Plan.MD:987` has the *Me* sentence § 3
  quotes.

## Feedback

- waste: the facts file `scratch/brief-facts-S098.md` was made before S097's code existed, so every
  S097 name (about 40) was checked by hand with grep and sed instead of read from it (about 10 minutes).
  A staleness review needs a facts file made after the steps it checks against were coded; the step
  skill could re-run `step-brief-facts.bat` as part of the stale brief check.
- hindrance: `git diff refs/steps/S097 -- <file>` reports every untracked file as deleted (the diff is
  against the index, which does not hold them), so the per-file comparison with the snapshot needed
  `git show refs/steps/S097:<file>` into a temp file and `diff` (2 runs lost). A `tooling/step-snapshot.bat
  diff <file>` that compares the snapshot with the working tree would save this.
- idea: the Read tool refused the brief at 1,297 lines (41k tokens) and needed three reads; the brief
  reviewer's instructions could say "read a long brief by section (§ 3, § 5, § 8 first)".
