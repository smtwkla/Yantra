```
Step: S104 — PM templates: one path
Doc: code-review r6
Author: Code reviewer (Opus)
Date: 13-11-2026
```

# S104 — code review, round 6

**Verdict: no `blocker` or `major` finding is open.** Fix round 6 fixes both findings of round 5. CR5-01: a
database lost while a template's plans settle now ends the loop with BR1-12's 503. CR5-02: `schedule_changed` calls
`seed_matches`. The wider `connection_lost` changes nothing for its three other callers. Both new tests fail
without the fix, and the report records their red run. One nit: the 503's log line loses the real cause (CR6-01).

This round verifies fix round 6 only (`step_snapshot.py diff S104 --from-round 6`, 5 files, 42 lines added and 12
removed). Brief § 10 was not read (amendment A1 is being drafted there).

## Test runs (this review, `YANTRA_TEST_RUN=s104cr6`)

| Run | Result |
|---|---|
| `tooling\run-backend-tests.bat tests/test_worker.py tests/test_pm_templates_api.py tests/test_pm_plans_core.py tests/test_pm_plans_api.py tests/test_pm_generate.py tests/test_pm_alerts.py tests/test_pm_jobs_core.py` | **294 passed** (22.6 s); PASSED |
| All suites | not re-run. The round changes only backend code, and the coder's `tooling\run-tests.bat` is green (backend 5322, frontend 468, tooling 258; the line-width check passed). The files I ran are the changed test files plus every test file of a caller of `connection_lost`, `schedule_changed` and `seed_matches`. |
| Schema docs | not run: `local_db.py` changed only outside `_MIGRATIONS`. The coder's `check` exits 0. |
| Browser | not run: no screen and no API answer the screens rely on changed, apart from the 503 that `PmTemplateView.vue` already handles. No browser run is owed for this round. |

## Findings of earlier rounds

| ID | Status | Verified by |
|---|---|---|
| CR1-01 to CR1-14, CR2-01, CR2-02, CR3-01, CR3-02, CR4-01 to CR4-04 | Fixed (earlier rounds) | not re-checked |
| CR5-01 (minor) | **Fixed** | below |
| CR5-02 (minor) | **Fixed** | below |

**CR5-01, traced.**
- `local_db.connection_lost` (`local_db.py:1597-1613`) now returns True for `pymysql.err.InterfaceError`. The check
  comes after the `open` test and before the OperationalError code test. In the installed PyMySQL, the only place
  that raises `InterfaceError` is `_execute_command` when `self._sock is None` (`pymysql/connections.py:875`). So
  the error always means a closed socket, as the docstring says.
- `settle_template_plans` (`pm_templates.py:200-202`) raises `DBUnavailable(describe_error(exc)) from exc` on a
  loss. `app.py:64` answers that with the 503 and `DB_LOST_TEXT`, which the page shows as "The template may be
  saved. Reload the page to see it." The template's own transaction is committed before the loop
  (`pm_templates.py:263-284`), so the template stands, as BR1-12 says.
- The path I traced in round 5 now ends right: the rollback's `InterfaceError` reaches the loop, it counts as a
  loss, and the request answers 503 instead of logging every plan as failed and then giving a 500 from `_detail`.

**The other callers of `connection_lost`, checked one by one.**

| Caller | Connection | Effect of the wider rule |
|---|---|---|
| `worker.py:133-142` (`run_one`) | the worker's raw `get_local_db()` | None. The branch that calls `connection_lost` catches only `OperationalError`, so an `InterfaceError` never reaches it. It goes to the general branch, which tests `not self.conn.open` as before. |
| `pm_jobs.py:495-497` (`generate`, the task `pm_generate`) | the worker's raw connection, through `task_handlers.pm_generate` | None. An `InterfaceError` comes only from a closed socket. On a raw connection `open` is then already False, so the function returned True before the change too. `generate` has no caller outside the task handler. |
| `pm_jobs.py:577-579` (`alert_scan`, the task `pm_job_alert_scan`) | the worker's raw connection | None, for the same reason. |

The only new case is an `InterfaceError` on a raw connection that is still open. PyMySQL does not produce that
case. The unit test pins the answer as True, which is the safe side: the worker stops and the claim is requeued.

**The new tests fail without the fix.**
- `test_worker.py:146-149`. Before the fix, both asserts give False: `Pooled` has no `open`, and `Raw(True)` is
  open, and an `InterfaceError` is not an `OperationalError`. The report's run 1 shows them red.
- `test_pm_templates_api.py:186-203` tells apart both halves of the fix:
  - without the `connection_lost` change, the loop counts both plans as failed and answers 200 with
    `plans_failed: 2`. Both `status_code == 503` and `len(calls) == 1` fail. The report's run 1 shows this red;
  - with the `connection_lost` change but a bare `raise`, the `InterfaceError` reaches Flask with no handler for it,
    and the answer is a 500. `status_code == 503` fails.
  
  The test also reads `calendar_every` from the database, so it checks that the template stands after the 503.
- The red run came before the fix was written. That is the coder's *Red, then green* rule.

**CR5-02.** `pm_plans_core.schedule_changed` (`pm_plans_core.py:144-154`) ends with
`return not cleared or seed_matches(stored, trigger)`. `seed_matches` is imported from `pm_jobs_core`, and
`pm_jobs_core` imports only `config_rbac`, `pm_schedule_core` and `tickets_core`, so there is no import cycle.
One behaviour differs from the old copy, and the new behaviour is the right one. `seed_matches` also asks for a
stored `last_done_meter`. So a clear of a value that is already null is no schedule change: nothing moves. This
case does not happen anyway, because `plan_changes` sends no unchanged field. `stored` is the plan row read with
`SELECT *` under the plan lock (`pm_plans.py:448`), so `seed_matches`' key lookups find their columns. The five
`TestScheduleChanged` cases are green in my run.

## Nits

- **CR6-01** (nit) `backend/pm_templates.py:202`: the 503's log line names only `describe_error(InterfaceError(0,
  ""))`, which is " (error 0)". `app.py:67` logs the message with no traceback, so the real cause (the 2013 in the
  `InterfaceError`'s `__context__`) appears nowhere in the log. Before this round, the 500's traceback showed it.
  The worker's `_log_lost` (`worker.py:144-149`) exists for exactly this. Log the loss with `exc_info=exc` before
  the `raise`, or describe `exc.__context__` when `exc` is an `InterfaceError`.

## Checked and found consistent

- **Scope.** The round changes only what CR5-01 and CR5-02 asked for. *Decisions taken in round 6* gives the reason
  for each of the two choices: one shared helper, and `DBUnavailable` raised in the request path, not in
  `local_db`.
- **Docs.** None are due. `connection_lost` is an internal helper that no doc describes, and no route, permission,
  screen, rule or schema changed. `docs/schema/` is unchanged.
- **Line width.** The new docstring lines are within 120 characters. The coder's tooling suite passed the check.
- **Teardown after the 503.** `close_db` returns the dead wrapper to the pool as on any other route with a lost
  connection. The pool pings on checkout (`db_helpers.py:28-30`), so the next request gets a live connection.
  Nothing new here.
- **Manual checks.** Unchanged by this round. The 503 needs no manual check: the API test proves it, and the
  page's handling of a 503 did not change.

**Files re-read:** `backend/local_db.py:1575-1615, 1752-1756`, `backend/pm_templates.py:185-290`,
`backend/pm_plans_core.py:140-155`, `backend/pm_jobs_core.py:13-18, 128-145`, `backend/pm_jobs.py:475-505,
560-585`, `backend/worker.py:110-160`, `backend/app.py:55-70`, `backend/db_helpers.py:1-60`,
`backend/tests/test_worker.py:125-150`, the round 6 diff of `backend/tests/test_pm_templates_api.py`, PyMySQL's
`InterfaceError` raise sites (`pymysql/connections.py`, by search), and the impl report's *Fix round 6*.

## Still to check by hand in a browser

Nothing new. No check of this step needs a real device.

## Feedback

- idea: `describe_error` gives " (error 0)" for PyMySQL's closed-socket `InterfaceError`, which hides the cause in
  every log that uses it. A `describe_error` that falls back to `exc.__context__` for an `InterfaceError` would help
  each caller at once (`local_db.py:1752`, `pm_templates.py:202`, `worker.py:144`).
- none else.
