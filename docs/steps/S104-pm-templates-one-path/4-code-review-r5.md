```
Step: S104 — PM templates: one path
Doc: code-review r5
Author: Code reviewer (Opus)
Date: 13-11-2026
```

# S104 — code review, round 5

**Verdict: no `blocker` or `major` finding is open.** CR1-01 (the owed database, schema docs and browser runs)
closes: the runs are done and green, and my own unit-suite run and schema docs check agree. Fix round 4's four
findings (CR4-01 to CR4-04) are fixed. Fix round 5's code fix (`local_db.connection_lost` on a pooled connection)
ends the 500 on a template save where one plan fails, and leaves the worker's path as it was. It does not give the
503 of BR1-12 when the database really goes away during the settle (CR5-01, minor). The new pure rule
`schedule_changed` copies the seed comparison of `pm_jobs_core.seed_matches` instead of calling it (CR5-02, minor).

This round verifies fix rounds 4 and 5 only (`step_snapshot.py diff S104 --from-round 4`, 17 files). Brief § 10 was
not read (amendment A1 is being drafted there).

## Test runs (this review, `YANTRA_TEST_RUN=s104cr5`)

| Run | Result |
|---|---|
| `tooling\run-tests.bat` (background, nothing beside it) | line width passed; backend **5320 passed** (197 s), frontend **468 passed**, tooling **258 passed**; ALL SUITES: PASSED |
| `tooling\schema-docs.bat check` (after the suites, alone) | 4 passed, **exit 0** (`docs/schema/` at migration v57) |
| Browser | not re-run: none of my findings needs a browser run. I read the coder's lane logs (below). |

## Findings of earlier rounds

| ID | Status | Verified by |
|---|---|---|
| CR1-01 (blocker) | **Fixed (closed)** | The impl report's round 5 table lists every owed run with its counts. My unit and schema runs give the same counts. The one whole-suite failure is in `scratch/e2e-lanes/lane1.log:90`: the console guard caught `net::ERR_ADDRESS_IN_USE` loading `/src/router/index.js` from lane 1's Vite (port 5181), a Windows socket fault, not the app. That lane's other 66 tests passed, and the re-run of `contracts.spec.js` on `phone-chromium` passed 49. `contracts.spec.js` is not a spec of this step. The WebKit run of `screens.spec.js` (9 passed) covers the new shared `e2e/support/pm.js`. |
| CR1-02 to CR1-14, CR2-01, CR2-02, CR3-01, CR3-02 | Fixed (earlier rounds) | not re-checked. CR2-01's behaviour stands as KLA decided on 13-11-2026 (brief § 9 item 6). |
| CR4-01 (minor) | **Fixed** | below |
| CR4-02 (minor) | **Fixed** | `PmPlanView.vue` `clearSeed` no longer empties the meter field. The browser test types 900, clears, and expects 900 in the field (`pm-plans.spec.js:184-189`), green in the coder's runs. |
| CR4-03 (nit) | **Fixed** | `pmLabels.js` `lastDoneHint`: the "If you do not know the meter reading" sentence shows only when `plan.template.meter_type` is set. That is the same value the page uses to show the meter field (`triggerMeter`, `PmPlanView.vue:54, 272`). Two unit cases pin both texts. |
| CR4-04 (nit) | **Fixed** | One term, "old meter value", in the button, the question and the hint. |

**CR4-01, traced through the code:**
- `change_plan` (`pm_plans.py:448`) now calls `schedule_changed(locked, changes, resolution["trigger"])`. `locked`
  is the row read under the plan lock before `update_row`, so the stored seed columns are the old ones, also after
  `changes.update(seed_meter_…)`.
- The rule matches the button. The button shows only while `_seed_note` shows, which is when
  `seed_matches(row, trigger)` is false. For a clear, `schedule_changed` gives False in the same cases: the seed is
  of another meter, or no meter resolves. A clear of the seed the plan uses (sent by a client other than the
  page), a new value, and any date change still drop the move (S101 D4).
- The question "Clear the old meter value? The old value is removed. The next due does not move." is now true for
  every case where the button shows. The seed of another meter is never the base (`meter_base_source`), and the
  clear does not send `last_done_on`.
- Tests. `TestScheduleChanged` has five core cases, with a red result (import error) before the rule. The API test
  `test_clearing_the_unused_seed_keeps_the_open_job_s_reschedule` (`test_pm_plans_api.py:184`) tells the fix apart
  from the old code. Without it, `keep_reschedule=False` makes `settle_plan_job` pass no override
  (`pm_jobs.py:442`), so `rescheduled_on` would be None. It is green in round 5 and in my run. Its red result was
  not possible in round 4 (the database was down), and the report says so.
- `SCHEDULE_FIELDS` is gone from `pm_plans_core` with no other user. `pm_templates.py` keeps its own
  `SCHEDULE_FIELDS` (the template's fields), so nothing else changed.

## Fix round 5: the test faults

I checked that each of the 8 test fixes makes the test assert what it means to check. A fix that only loosens a
test so that it passes would be a fault here. I found none.

| # | Test | Verdict |
|---|---|---|
| 1, 2 | `test_migration_v57.py::test_the_tables_keys_and_foreign_keys` | Right. `LIKE %s` with `pm\_%` still matches only `pm_` tables. With both sides sorted in Python, the test still checks the exact set and count of the seven tables. The order of the rows never mattered to the test. |
| 3 | (the code fault, CR5-01 below) | — |
| 4 | `test_pm_generate.py::TestRun::test_a_failing_plan_does_not_stop_the_others` | Right. The stand-in now passes `keep_reschedule=` through to the real `settle_plan_job`, so the good plan settles and only the bad one fails, as the test means. |
| 5 | `test_pm_work_api.py::…::test_a_meter_removed_after_start_keeps_the_value_on_the_job` | Right. The new text is `meter_label`'s wording ("RDAA001's Test meter 0098"), which Decisions taken 5 states. The old test still had the S098 wording. |
| 6, 7 | `test_pm_alerts.py::TestRecipients` (due, overdue) | Right. The job's title is the template's name (S104 § 5.10), and `pm_helpers` numbers names (Decisions taken 15). The tests still pin the whole body: serial, title, dates and assignee. |
| 8, 9 | `pm-jobs.spec.js` (Overdue on the PM list; the PM card) | Right. Both use the name `planByApi` returns (`support/pm.js` adds the machine code), as `pm-plans.spec.js` does. The badge, the date and *Next due* assertions are unchanged. |

**Red, then green.** Fault 3 has its red result: the API test answered 500 before the fix (run 1b). The two
`TestConnectionLost` tests were written with the fix, and the report gives the reason. That is acceptable.

## Minor

### CR5-01 (minor) — on a request's pooled connection, a database that goes away during the settle still gives no 503

- **Where:** `backend/local_db.py:1604` (`connection_lost`), as called by `backend/pm_templates.py:200`
  (`settle_template_plans`); the test `backend/tests/test_worker.py:141`.
- **Problem:** the round 5 docstring says that on DBUtils' wrapper "the error alone decides (a 2xxx client code …
  is a loss)". On the real path the loop does not get the 2xxx error when the server is down. I traced this
  from the installed libraries' source (`dbutils/steady_db.py`, `pymysql/connections.py`):
  1. Inside `settle_one`'s `transaction(conn)`, an `execute` fails with `OperationalError(2013)`. PyMySQL then
     force-closes the socket. In a transaction, DBUtils' `tough_method` tries `con._create()`. With the server
     down, that fails, and it re-raises the 2013.
  2. `db_helpers.transaction` then calls `conn.rollback()`. PyMySQL raises `InterfaceError(0, "")` on the closed
     socket. DBUtils' `SteadyDBConnection.rollback` catches it, fails to reconnect, and re-raises the
     `InterfaceError`. So the exception that reaches the loop is the `InterfaceError`, and the 2013 is only its
     `__context__`.
  3. `connection_lost(wrapper, InterfaceError)`: `getattr(conn, "open", True)` is True on the wrapper, and an
     `InterfaceError` is not an `OperationalError`, so the answer is False. The loop counts the plan as failed and
     goes on. Each next plan fails at `conn.begin()` with the same `InterfaceError`.
  4. After the loop, `_detail` reads on the same dead wrapper. That raises `InterfaceError` too, and
     `api_common` has no handler for it, so it falls to `_unexpected_error`: a plain 500.

  The 503 path works only when DBUtils could reconnect in step 1, because then the rollback runs on the new
  connection and the 2013 reaches the loop. The new test models only that case: it calls the wrapper stub with a
  2013. The worker is not affected. Its raw PyMySQL connection has `open`, which is False after the force-close,
  so the worker and `pm_generate` stop at once as before.
- **Failure scenario:** an engineer saves a template that 12 machines use. The template commits, and then the
  database restarts for its nightly backup while the plans are settled. Twelve tracebacks are logged as "settling
  plan … failed", and the page shows the generic server error. BR1-12's line "The template may be saved. Reload
  the page to see it." (`PmTemplateView.vue:169`, shown only on a 503) is never shown. The engineer may think the
  change was lost and type it again. The data is safe: the template stands, a repeated PUT writes nothing, and
  the next daily run settles the plans. Only the answer and the logs are wrong, so this is minor.
- **Fix:**
  1. In `connection_lost`, count `pymysql.err.InterfaceError` as a loss. PyMySQL raises it only on a closed
     connection, and the worker's raw path already returns True there through `open`, so it changes nothing for
     the worker.
  2. In `settle_template_plans`, on a loss, raise `DBUnavailable` from the error, so the app's handler answers
     the 503 the page expects. A bare re-raise of the `InterfaceError` would still be a 500.
  3. Correct the docstring.
  4. Add a case to `TestConnectionLost`: the pooled stub with `InterfaceError(0, "")` is a loss.
  5. Add an API test in `test_pm_templates_api.py`: `settle_one` raises `InterfaceError(0, "")` for the first
     plan. The save answers 503, the template is changed in the database, and the loop stopped after the first
     plan.

### CR5-02 (minor) — `schedule_changed` repeats `seed_matches` instead of calling it

- **Where:** `backend/pm_plans_core.py:153-154`.
- **Problem:** the rule exists so that "the button shows" and "the due does not move" agree. The note is decided by
  `pm_jobs_core.seed_matches` (`pm_plans._seed_note`). The base is decided by `meter_base_source`, which also
  uses `seed_matches`. `schedule_changed` writes the same comparison out a second time, a third copy beside
  `plan_changes`. CR4-01's fix proposed `seed_matches`, and *Decisions taken* (round 4) does not say why it was not
  used. Today the copies agree: a clear is a change only when the stored value is not null, which is
  `seed_matches`' first condition.
- **Failure scenario:** a later step changes when a seed counts, for example a legacy seed with no meter ids that
  counts for the plan's own meter, and edits `seed_matches` only. The note then hides, but a clear still keeps the
  move; or the note shows, and a clear of a seed that is the base keeps a move whose base just changed.
- **Fix:** `return not cleared or seed_matches(stored, trigger)`, with `seed_matches` imported from
  `pm_jobs_core` into `pm_plans_core`. This is pure core to pure core, and there is no import cycle:
  `pm_jobs_core` imports neither plan module. The five core tests stay as they are.

## Checked and found consistent

- **The worker's own connection path.** `worker.py:92` opens `get_local_db()`, a raw `pymysql.connect`, whose
  `open` property exists, so `getattr` returns the real value. `pm_generate` and `pm_job_alert_scan`
  (`pm_jobs.py:496, 578`) run on that connection through the task handlers. For them `connection_lost` behaves
  exactly as before round 5.
- **The wrapper.** PooledDB's `connection()` gives a `PooledDedicatedDBConnection` whose `__getattr__` asks the
  `SteadyDBConnection`. That object has no `open` and raises `AttributeError`, so the `getattr` default applies.
  This matches the round 5 traceback. The wrapper's `_con` is None only after `close()` at teardown, never inside
  the loop.
- **Fault 3's main effect is fixed.** A plan that fails for a non-connection reason now gives `plans_failed: 1`
  and the saved template (`TestSettle::test_one_plan_failing_leaves_the_template_saved`, green), not a 500.
- **`PmPlanView.vue` after CR4-02.** With a typed value kept, the page stays dirty, so Cancel asks. After the clear,
  `plan.seed_note` is null, so `planSettingsBody` sends the field, and *Save plan* ties it to the meter in use now.
- **Line width:** the tooling suite's check passed over the changed Python files.
- **Docs.** Round 4 names none as due, which is right: no route, permission or flow changed, and the question text
  is in the code. Round 5 regenerated `schema.json` and `schema-data.js`; `check` exits 0 in my run. The impl
  report's *Runs owed* and *Manual checks* are current. Every `[auto]` check now has a passing run behind it, and
  the real-device list is empty, as brief § 8.5 says.
- **Manual checks:** the reviewer's plan-page watch of rounds 2–4 is now `[auto]`, from the browser test and the two
  API tests, all green.

**Files re-read:** `backend/local_db.py:1585-1660`, `backend/db_helpers.py:1-70`, `backend/api_common.py:79-115`,
`backend/pm_templates.py:185-290`, `backend/pm_plans.py:74-161, 405-460`, `backend/pm_plans_core.py` (whole),
`backend/pm_jobs_core.py:128-145`, `backend/pm_jobs.py:425-472, 480-500, 565-600`, `backend/worker.py`
(connection lines), `backend/.venv/…/dbutils/steady_db.py` (`begin`, `rollback`, `_fatal_check`, `tough_method`),
`backend/.venv/…/pymysql/connections.py` (`open`, `begin`, `rollback`, `_execute_command`),
`frontend/src/views/PmPlanView.vue` (the clear and the meter field), `frontend/src/views/PmTemplateView.vue:160-170`,
`frontend/src/utils/pmLabels.js:225-335`, the round 4–5 diff of every test file, `scratch/e2e-lanes/lane1.log`, and
the impl report's *Runs owed*, *Manual checks* and *Fix rounds › Round 4, Round 5*.

## Still to check by hand in a browser

Nothing new. The plan page's unused-seed flow is now covered by the browser test and the API tests. No check of
this step needs a real device. After CR5-01's fix the 503 text needs no manual check: the API test proves the 503,
and the page's handling of a 503 is unchanged.

## Feedback

- idea: a test of a lost connection that stubs the error at the loop (as `TestConnectionLost` does) shows only what
  the helper does with that error, not which error arrives. Here DBUtils' `rollback` swaps the 2013 for an
  `InterfaceError`. A shared test helper that kills the request connection for real (`KILL CONNECTION_ID()` from a
  second connection) would show it (`tests/test_worker.py:141`, `pm_templates.py:200`).
- rule: the same swap seems to affect every route that runs `db_helpers.transaction` when the server stays down: the
  rollback's `InterfaceError` reaches Flask as a plain 500, not `_operational_error`'s 503. This is outside S104, so
  it is not a finding here. It is a candidate point for `/smtw-review` or a fix-lane step
  (`db_helpers.py:42-55`, `api_common.py:95-104`).
