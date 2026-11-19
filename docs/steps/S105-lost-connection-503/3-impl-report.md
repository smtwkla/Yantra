```
Step: S105 — A lost database connection answers 503, not 500
Doc: impl report
Author: Coder (Opus)
Date: 19-11-2026
```

# S105 — implementation report

**Outcome.** The whole brief is built, nothing more: PyMySQL's closed-socket `InterfaceError` now
answers the database 503 on every route, `/api/auth/me` answers a lost connection with its outage
body (the token's permissions, `db_unavailable: true`), and the wrong comment in `db_helpers.get_db`
is corrected. Five code and test files and one doc changed; three new tests (four cases), red on
the baseline and green now; all unit suites green (`YANTRA_TEST_RUN=s105c1`, numbers below).

## What was built

1. **A closed socket answers the database 503** (brief § 1.1). `api_common` registers a handler for
   `pymysql.err.InterfaceError`. It answers `{"error": DB_LOST_TEXT}` with status 503 and logs one
   ERROR line with no traceback: `Database connection lost on <METHOD> <path>: connection closed`.
2. **`/api/auth/me` keeps its outage answer for a lost connection** (§ 1.2). A lost connection on
   its first statement (an `InterfaceError`, or an `OperationalError` with a lost code such as 2013)
   gives the same 200 body as `DBUnavailable`: the token's permissions, `sites` and `person_id` null,
   `db_unavailable` true. The loss is logged with the shared line. Any other database error (a
   deadlock 1213, a lock wait 1205, an SQL fault) is re-raised and stays the 500.
3. **The `get_db` comment** (§ 1.3) now says that the checkout ping replaces a dead cached
   connection only when the server answers, and that otherwise DBUtils hands out the dead
   connection, whose first statement raises `InterfaceError`, answered with the same 503.

## How it works

- `api_common.log_connection_lost(exc)` (new, public) writes the one log line. Its detail is
  `connection closed` for an `InterfaceError` (whose own text is the empty `(0, '')`), and the
  exception itself for an `OperationalError`, as before (`(2013, 'Lost connection …')`).
- `api_common._database_lost(exc)` (new, private) calls it and returns the 503. It is the
  registered handler for `InterfaceError`, and `_operational_error`'s lost branch now returns it,
  so the 2013 path and the closed-socket path share the same two lines. Flask picks the handler by
  the exception's class (MRO): `InterfaceError` is not an `OperationalError`, so it reached the
  catch-all `_unexpected_error` before (a 500 with a traceback).
- `app.auth_me` catches `(DBUnavailable, pymysql.MySQLError)`. For a `MySQLError` it asks
  `local_db.connection_lost(None, exc)`, which decides from the error alone (`None` has no `open`
  attribute, so the first test there passes); not a loss: bare `raise`, so the app's handlers
  answer it as before. A loss is logged with `log_connection_lost`. Then, for a loss and for
  `DBUnavailable` alike, the existing outage body. `DBUnavailable` is still not logged here.
- Fail-closed is unchanged: nothing in `auth_utils` catches a `MySQLError`, so a loss during the
  permission read on any other route reaches the new handler and is a 503, never a grant.

## Files touched

| File | Change |
|---|---|
| `backend/api_common.py` | New `log_connection_lost` and `_database_lost`; `_operational_error`'s lost branch uses `_database_lost` and its docstring drops "the pool's ping passed"; `register_error_handlers` adds the `InterfaceError` handler beside the `OperationalError` one. |
| `backend/app.py` | `import pymysql`; `log_connection_lost` and `connection_lost` added to the imports; `auth_me`'s except clause of § 1.2; its docstring says "or its connection is lost (S105)" (the paragraph re-wrapped to keep lines under 120). |
| `backend/db_helpers.py` | The comment in `get_db` (comment only). |
| `backend/tests/test_errors.py` | Test 1, `test_a_closed_connection_is_the_same_503`. |
| `backend/tests/test_auth.py` | Tests 2 (two cases) and 3 in `TestDatabaseDown`; imports `pymysql`, `app as app_module`, `SERVER_ERROR` and `server_error` from `tests.conftest`. |
| `.claude/CLAUDE.md` | The docs-pass line of § 3 (see *Docs updated*). |

Workflow files: the brief's `Status` and its row in `docs/steps/INDEX.md`.

## Decisions taken

- **The `get_db` comment's last sentence.** Besides what § 1.3 asks, the comment keeps a short
  statement of what the `except` below it means: "An error here means no new connection could be
  made." The old comment's second half said this for every case; it is now true only for the
  pool's own connect, so the sentence says that. Comment only.
- **Test 1 checks exactly one matching log line** (`len(lines) == 1`), a little stricter than the
  brief's "expect a record": it also shows the handler logs once, not twice.
- **Test 2's second request** (the `maintenance_team` token) runs inside the same test after the IT
  admin request, under the same monkeypatch, rather than as a separate test: the brief lists both
  as parts of test 2.
- No departure from the brief.

## Not done, deferred or assumed

- Everything in the brief's *Out of scope* stays out (no `describe_error` change, no
  `access_control` log change, no real-loss fixture, no `pm_templates` or `connection_lost`
  docstring edits, no frontend change, no retry).
- **Assumption** (brief § 6): production uses the same DBUtils 3.2.0 and PyMySQL 1.2.3 as
  `backend/uv.lock`. Test 1 pins today's mapping of `InterfaceError` to the 503.
- The parenthesis in `pm_templates.settle_template_plans` ("neither of which the app answers as a
  503") is now half out of date, as the brief says; left as it is (gate A answer, KLA 19-11-2026).

## Tests

**Red first.** On the baseline code, with the new tests in place
(`tooling\run-backend-tests.bat tests/test_errors.py tests/test_auth.py`): 3 failed, 70 passed.
- test 1: `assert (500, {'error': 'Something went wrong — try again'}) == (503, {...})`;
- test 2, `InterfaceError` case: `assert 500 == 200`;
- test 2, 2013 case: `assert 503 == 200`;
- test 3 passed, as the brief expects (it guards the re-raise).

**Green.** The brief's run line (`tests/test_errors.py tests/test_auth.py
tests/test_access_control_api.py tests/test_pm_templates_api.py`): 135 passed.

**Full run** (`tooling/run-tests.bat`, `YANTRA_TEST_RUN=s105c1`): ALL SUITES PASSED. Backend 5391
passed (154 s), frontend 472 passed (7 s), tooling 247 passed (2 s), line-width check green.

The first full run stopped at the line-width check (`backend/app.py:138`, 126 characters, the
`auth_me` docstring); the line was re-wrapped and the run repeated. A last re-flow of that same
docstring paragraph (no code) was saved while the second run was starting, so the brief's run line
(135 passed) and the tooling suite with the line-width check (247 passed) were run once more on the
final text, both green.

**Browser tests:** none (no frontend change; brief § 5).

## Manual checks

None (brief § 5: no manual check, no real-device check).

## Docs updated

- `.claude/CLAUDE.md` § Yantra Specifics, *DB may not exist*: the line of brief § 3 added after
  "`/api/health` reports `schema_ready`" ("a connection lost mid-request … answers the same 503
  (`api_common`), and `/api/auth/me` its `db_unavailable` body (S105)").
- No other doc: no migration (no schema docs), no module behaviour in `docs/Plan.MD`, no secret, no
  role, no device check.

## Feedback

- hindrance: a pytest `-k "a or b"` expression cannot pass through `cmd //c
  "tooling\run-backend-tests.bat …"`: cmd split it at the spaces and the run selected nothing
  ("no tests ran", exit 5); running the two whole files instead cost one extra run of a few seconds
  (`scratch/backend-tests-s105c1.log`). A line in *Unit tests* ("no spaced `-k` expression through
  `cmd //c`; name the test ids") would save it.
