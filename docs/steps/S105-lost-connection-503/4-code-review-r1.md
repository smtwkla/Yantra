```
Step: S105 — A lost database connection answers 503, not 500
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 19-11-2026
```

# S105 — code review, round 1

**Verdict: no `blocker` or `major` finding is open. This round has no findings at all.** The change
builds the brief as cut on 19-11-2026, and nothing more. All unit suites are green on my own run.

Reviewed: `uv run --no-project python tooling/steps/step_snapshot.py diff S105` (6 files; the
working tree equals `refs/steps/S105`, checked with `--worktree`), the brief with its Review log,
and `3-impl-report.md`. I read these in full or around the hunks: `backend/api_common.py`,
`backend/app.py` (the hooks, the `DBUnavailable` handler and `auth_me`), `backend/db_helpers.py`,
`local_db.connection_lost` / `is_connection_lost` / `return_pooled_db`,
`access_control.internal_networks` and `_record`, `auth_utils.current_memberships` and its `except`
clauses, DBUtils' `PooledDB.cache` and `SteadyDBConnection._reset`, and the `TestDatabaseDown`
class in `test_auth.py`.

## Tests

- **`tooling/run-tests.bat`**, `YANTRA_TEST_RUN=s105cr1`: **ALL SUITES PASSED.** The line-width
  check is green. Backend: 5391 passed (134 s). Frontend: 472 passed (8 s). Tooling: 247 passed (2 s).
  The counts match the coder's run.
- **Build check:** not needed, because no frontend file changed.
- **Browser tests:** none. No screen and no API shape changed. The 503 body and the
  `db_unavailable` body are the ones the screens already handle (brief § 5).
- **Red, then green:** the impl report records the baseline run with the three new red cases (500,
  500 and 503) and test 3 green, as the brief expects. It then records the green run.

## Findings

None.

## Nits

None.

## Checked and found consistent

- **The handler (brief § 1.1).** `register_error_handlers` maps `pymysql.err.InterfaceError` to
  `_database_lost` (`api_common.py:124`). Flask picks the handler by the exception's MRO
  (`InterfaceError → Error → MySQLError → Exception`), so the new entry wins over the `Exception`
  catch-all. It does not touch `OperationalError` or `IntegrityError`. The body is exactly
  `{"error": DB_LOST_TEXT}`, with no cause in it (S064 UX-13). The log line is one ERROR with no
  traceback, and its detail is `connection closed` for an `InterfaceError` and `%s` of the error
  for an `OperationalError`. The 2013 line's text is unchanged.
- **DRY.** `_operational_error`'s lost branch now returns `_database_lost(exc)`, so the 2013 path
  and the closed-socket path share the log line and the 503. `log_connection_lost` is public only
  because `auth_me` calls it, as D3 says. The pre-existing `app._db_unavailable` handler returns the
  same 503 text. That overlap is older than this step, and the brief's cut leaves it alone.
- **`/api/auth/me` (brief § 1.2).** The code catches `(DBUnavailable, pymysql.MySQLError)`
  (`app.py:163`). A `MySQLError` that `connection_lost(None, exc)` does not call a loss is re-raised
  with a bare `raise`, so a deadlock, a lock wait or an SQL fault reaches the app's handlers as
  before. An `IntegrityError` also keeps its 409 or re-raise path. A loss is logged, and
  `DBUnavailable` is still not logged. Both then send the old outage body, which holds the token's
  permissions only, `sites` and `person_id` null, and `db_unavailable: true`. The body grants no
  more than S011 § 5.2 allows (ISO 27001 A.5.15). This is tested for IT admin (`compute_permissions`)
  and for `maintenance_team` (`[]`).
- **The hooks around `auth_me` during an outage.** These paths do not undo the 200:
  - `require_network` reads the ranges through `internal_networks`. Its `except` already covers
    `pymysql.MySQLError`, so a closed socket there gives the cached or default list, not an error.
  - The access-log hook catches every exception and backs off.
  - The teardown `close_db` returns the dead connection to the pool, where DBUtils' `_reset`
    suppresses the failed rollback. The checkout ping replaces the connection once the server
    answers.
- **Fail-closed.** No `except` in `auth_utils` catches a database error (lines 115, 174, 178 and
  291 catch JSON, JWT and login-server errors only). A loss during the permission read on any other
  route is therefore the 503, never a grant.
- **The `get_db` comment (§ 1.3)** now describes what DBUtils really does. The extra last sentence
  ("An error here means no new connection could be made") is true for `get_pooled_db`'s own
  connect, and the impl report states it under *Decisions taken*.
- **Tests (§ 5).** All three tests are there, with the names and stubs the brief gives:
  - test 1 checks the 503 body, exactly one `api_common` line with `GET /api/version` and
    `connection closed`, and `exc_info` None;
  - test 2 runs both cases (`InterfaceError`, 2013), checks the log detail and checks both roles;
  - test 3 pins the 1213 deadlock as `SERVER_ERROR`.
  No existing test was edited. The tests the brief lists as staying green (`test_errors.py`,
  `TestDatabaseDown`'s `db_down` tests, `test_access_control_api.py`, the `pm_templates`
  `InterfaceError` stub, `test_worker.py::TestConnectionLost`) pass in the full run.
- **Scope.** Everything in the brief's *Out of scope* list stays out: `describe_error`,
  `access_control`'s log text, a real-loss fixture, the `pm_templates` and `connection_lost`
  docstrings (the half out-of-date parenthesis was left as KLA decided at gate A), the frontend,
  retries and migrations. The three small choices in *Decisions taken* (the comment's last
  sentence, the one-line count in test 1, test 2's second request in the same test) are inside the
  brief and are reported.
- **Docs pass.** The `.claude/CLAUDE.md` *DB may not exist* line matches brief § 3 word for word.
  No other doc is due: no migration, so the schema docs check is not needed; no Plan.MD module
  behaviour, no secret, no role and no device check changes.
- **Architecture.** No *Architecture* entry is configured, so there is no doc to check against.
  The change adds no module, boundary or pattern. The handler lives in `api_common`, beside its
  siblings.
- **Track.** This is a full-track step, so no light-track criterion applies.
- **Use on the floor.** There is no screen change. The users now see the existing plain 503 text
  ("Yantra can't reach its database. Try again in a few minutes.") in place of "Something went
  wrong — try again". The readings sheet stops at the first unsaved row on a 503. IT admin gets the
  app shell and *Settings › Database*.
- **Line width** is green: `app.py`'s re-wrapped docstring passes.

**Left for the user's manual browser check:** nothing. The brief has no manual check and no
real-device check, and the impl report's `## Manual checks` says so.

## Feedback

- idea: the waiting time for a background `run-tests.bat` cost about 3 minutes of polling. The
  task-output file stays empty until the backend suite ends, because of the `| tail` in the spawn
  prompt's command. A small waiter script on the output file worked. Adding a line to the code
  reviewer's file on how to block until the run's summary appears would save the guesswork
  (`scratch/backend-tests-s105cr1.log` was also empty until the end).
