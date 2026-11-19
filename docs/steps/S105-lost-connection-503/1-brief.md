```
Step: S105 — A lost database connection answers 503, not 500
Doc: brief
Author: Brief writer (Opus)
Date: 14-11-2026 (revised 15-11-2026 for review rounds 1 and 2; revised 19-11-2026: cut to a small step, KLA)
Track: full (chosen by KLA 14-11-2026; the writer proposed light)
Baseline: 0d64228 (stale check 19-11-2026: no file of § 3 changed since review r2's 6696283)
Status: Gate B — waiting for KLA (code review r1: no findings)
```

# S105 — A lost database connection answers 503, not 500

**The point.** When the database server goes down after the app has served requests, most
requests answer a plain **500** ("Something went wrong — try again") instead of the repo's **503**
("Yantra can't reach its database. Try again in a few minutes."), and a page load shows the
full-page error card instead of the app shell. The cause is PyMySQL's closed-socket
`InterfaceError(0, "")`, which `api_common` does not handle. The step adds one error handler,
keeps `/api/auth/me`'s outage answer for a lost connection (KLA, 15-11-2026), and corrects one
wrong comment. Database outages are rare, so the step stays small (KLA, 19-11-2026).

Source: KLA's feedback triage of 14-11-2026, from S104's code reviews r5 and r6, § Feedback
(`docs/steps/S104-pm-templates-one-path/4-code-review-r5.md`, `4-code-review-r6.md`).

## 0. The fault, confirmed

Two read-only probes against the dev DB (`scratch/s105_lost_connection_probe.py`, log
`scratch/s105-probe.log`; `scratch/s105_fixture_probe.py`; and the reviewer's
`scratch/s105_br2_probe.py`) killed a pooled connection with `KILL CONNECTION` and refused the
reconnect ("server stays down"), then sent the result through the app's own error handlers.

| Case | What reaches the caller | Answer today |
|---|---|---|
| A. Killed mid-transaction, server up | `OperationalError(2013, …)` | **503** |
| B. Killed mid-transaction, server stays down | `InterfaceError(0, '')` from the rollback | **500** |
| C. An idle pooled connection died while the server is down | `InterfaceError(0, '')` at the first statement | **500** |
| D. Same as C, first statement `transaction()`'s `conn.begin()` | `InterfaceError(0, '')` (`db_helpers.py:48`) | **500** |

Why:
- **C, D (the usual outage).** The pool pings a cached connection at checkout (`ping=1`,
  `local_db.py:1701`). When the ping and the reconnect both fail, `_ping_check` swallows the errors
  (`backend/.venv/Lib/site-packages/dbutils/steady_db.py:409-450`) and `PooledDB.connection()` hands
  out the dead connection (`backend/.venv/Lib/site-packages/dbutils/pooled_db.py:371-379`). So the
  comment in `db_helpers.get_db` (`db_helpers.py:28-29`, "an error means the server itself cannot
  be reached") is wrong for a cached connection.
- **B.** DBUtils re-raises the 2013 when its reopen fails; `db_helpers.transaction`'s rollback then
  meets the closed socket, and PyMySQL raises `InterfaceError(0, "")`
  (`backend/.venv/Lib/site-packages/pymysql/connections.py:875`).
- **Every `InterfaceError` from PyMySQL 1.2.3 is a closed socket**: `connections.py:875` is its only
  raise. Its MRO is `InterfaceError → Error → MySQLError → Exception` (checked), not
  `OperationalError`, so `_unexpected_error` (`api_common.py:87`) answers it: a 500 with a
  traceback in the log.
- **A 2013 can also reach `/api/auth/me`** (no transaction there): a connection lost between two
  statements with the server down; DBUtils fails to reopen and re-raises the 2013
  (`steady_db.py:755-828`, the reviewer's probe). Today that is the 503 of `_operational_error`.

What the user sees today with the server down:
- **Readings sheet:** it stops at the first unsaved row only on 502–504 (`isUnavailable`,
  `frontend/src/utils/meterLabels.js:183-185`). On a 500 it tries every row, and each row shows
  "Something went wrong — try again".
- **Every other screen** shows "Something went wrong — try again", which asks for an immediate retry.
- **A page load.** `app.auth_me` (`backend/app.py:132`) answers `db_unavailable: true` with the
  token's permissions on `DBUnavailable` (`except DBUnavailable`, `app.py:161`), "so IT admin can
  still reach Settings › Database". In cases C and D the `InterfaceError` comes from its first
  statement and is not caught: a 500, and `App.vue` shows the full-page error card. IT admin cannot
  open *Settings › Database*.

## 1. What will be built, and out of scope

**Built:**
1. **A closed socket answers the database 503.** `api_common.register_error_handlers` registers a
   handler for `pymysql.err.InterfaceError`. It answers `{"error": DB_LOST_TEXT}`, 503, and logs one
   ERROR line with no traceback: `Database connection lost on <METHOD> <path>: connection closed`.
   It reuses `_operational_error`'s lost branch: that branch's two lines (the log line and the 503)
   move into a private `_database_lost(exc)`, which both handlers use. The line's detail is
   `connection closed` for an `InterfaceError` and, as today, `%s` of the exception for an
   `OperationalError` (`(2013, 'Lost connection …')`). The log line itself is the new public
   `api_common.log_connection_lost(exc)`, because `app.auth_me` writes it too (item 2).
2. **`/api/auth/me` keeps its outage answer for a lost connection** (KLA, 15-11-2026, BR1-01
   option (a)). `except DBUnavailable:` becomes `except (DBUnavailable, pymysql.MySQLError) as exc:`:
   - a `pymysql.MySQLError` that `local_db.connection_lost(None, exc)` does not call a loss is
     re-raised with a bare `raise` (a deadlock, a lock wait, an SQL fault stay the 500);
   - a loss (`InterfaceError`, or `OperationalError` with a lost code) is logged with
     `api_common.log_connection_lost(exc)`;
   - then, for a loss and for `DBUnavailable` alike, today's body: `role=display_role(user["roles"],
     [])`, `permissions=user["permissions"]` (the token's), `sites=None`, `person_id=None`,
     `db_unavailable=True`, status 200. `DBUnavailable` is still not logged here, as today.

   `connection_lost(None, …)` decides from the error alone (`getattr(None, "open", True)` is
   `True`; `local_db.py:1645-1661`). Checked with `uv run python`: `InterfaceError(0, '')` → True,
   `OperationalError(2013, …)` → True, `OperationalError(1213, …)` → False,
   `IntegrityError(1062, …)` → False. `DBUnavailable` is a plain `Exception`, not a `MySQLError`.
3. **The wrong comment in `db_helpers.get_db`** (`db_helpers.py:28-29`) says what happens: the
   checkout ping replaces a dead cached connection only when the server answers; when it does not,
   DBUtils hands out the dead connection, and its first statement raises PyMySQL's `InterfaceError`,
   which `api_common` answers with the same 503 (S105). Comment only.

What the user sees after the step, with the server down: every screen shows the 503 text; the
readings sheet stops at the first unsaved row; a page load gets the app shell, where IT admin
reaches *Settings › Database*. A person whose rights come from the database gets the database
branch of `NoAccessView.vue`, unchanged since S011 ("The database is unavailable — try again
shortly.", no button; it stays until the page is reloaded). That is no regression: today the same
person gets the full-page error card.

**Rules:**
- The 503 body is exactly `{"error": DB_LOST_TEXT}`; it never carries the cause (S064 UX-13).
- A request that loses its connection during the permission read gets the 503, never a grant.
  Nothing in `auth_utils` catches a `MySQLError` (its `except` clauses, `auth_utils.py:115`, `:174`,
  `:178`, `:291`, catch only JSON, JWT and login-server errors), so fail-closed is unchanged.
- `/api/auth/me` on a loss grants only what the token grants, as on `DBUnavailable` (S011 § 5.2):
  `maintenance_team` gets `permissions: []`, IT admin `compute_permissions(["it_admin"])`.
- `_operational_error`'s rule for other codes is unchanged: 1213, 1205 and any non-loss code stay
  the 500, in `auth_me` too.
- `db_helpers.transaction` and `local_db.connection_lost` are not changed. The server rolls back an
  uncommitted transaction when its connection drops, so nothing is half-written.

**Out of scope** (each: outages are rare; KLA 19-11-2026):
- `describe_error` looking into `__context__`, and a `CONNECTION_CLOSED_TEXT` constant (old D3). The
  log line says `connection closed`; a 2013 behind it shows in the worker's and `pm_templates`'
  own tracebacks.
- `access_control`'s two outage warnings (`access_control.py:118`, `:235`) keep their `%s` text
  (old § 1.4; KLA reversed the BR1-04 answer).
- A `lost_connection` fixture with a real `KILL` and polling (old D4, D5). § 0's probes already show
  which error arrives for real; the tests raise it from a stub.
- The docstring edits in `pm_templates.settle_template_plans` (`pm_templates.py:188-189`) and
  `local_db.connection_lost`, and a `/smtw-review` point (old D6). After the step the parenthesis
  "neither of which the app answers as a 503" in `settle_template_plans` is half out of date (an
  `InterfaceError` now is a 503); the code it describes stays right, because the loop catches
  `Exception` and must still tell a loss apart.
- A manual check on KLA's laptop (old Q1).
- A *Try again* button on `NoAccessView.vue`'s database branch (old Q3, settled as option (c)):
  not in this step, nothing queued.
- No retry, no `Retry-After`, no worker change (`worker.py:133-145` already treats a closed
  connection as a loss), no frontend change, no migration, no RBAC change, no new dependency.

## 2. Standards and practice

- **CLAUDE-COMMON *Idle connections***: "Detect a dead connection on first use
  (`OperationalError`/`InterfaceError` or equivalent) and reconnect, rather than returning a 500".
  Today only the `OperationalError` half answers the 503; the step adds the `InterfaceError` half.
  The reconnect already works: the checkout ping reopens once the server answers (probe case C,
  then "server back").
- **HTTP, RFC 9110 § 15.6.4** (503): the server cannot handle the request now and probably can
  after a delay. A database outage is that, not an unexpected fault (500, § 15.6.1); the readings
  sheet acts on the difference.
- **ISO/IEC 27001:2022 Annex A 5.15 *Access control***: access follows the rules set for it. The
  outage answer of `/api/auth/me` grants only the token's own permissions (tests 2 and 3).
- Maintenance standards (TPM, ISO 14224, EN 13306, ISO 55000, SMRP): not touched.

## 3. Where

| File | Change |
|---|---|
| `backend/api_common.py` | New public `log_connection_lost(exc)`: `logger.error("Database connection lost on %s %s: %s", request.method, request.path, detail)`, detail `"connection closed"` for a `pymysql.err.InterfaceError`, else `exc`. New private `_database_lost(exc)`: calls it, returns `jsonify({"error": DB_LOST_TEXT}), 503`. `_operational_error`'s lost branch returns `_database_lost(exc)`; its docstring drops "the pool's ping passed". `register_error_handlers` adds `app.register_error_handler(pymysql.err.InterfaceError, _database_lost)` beside the `OperationalError` line (`api_common.py:111`). `pymysql` is already imported. |
| `backend/app.py` | `auth_me`'s except clause of § 1.2; `import pymysql`; `connection_lost` added to the `local_db` import (`app.py:21`) and `log_connection_lost` to the `api_common` import (`app.py:10`). The docstring's "answers while the database is down" adds "or its connection is lost". |
| `backend/db_helpers.py` | The comment of § 1.3 (`:28-29`). Comment only. |
| `backend/tests/test_errors.py` | Test 1. |
| `backend/tests/test_auth.py` | Tests 2 and 3, in `TestDatabaseDown`. |
| *Docs (housekeeping, by the coder)*: `.claude/CLAUDE.md` | § Yantra Specifics, *DB may not exist*: add "; a connection lost mid-request (an `OperationalError` with a lost code, or PyMySQL's closed-socket `InterfaceError`, which DBUtils hands out while the server stays down) answers the same 503 (`api_common`), and `/api/auth/me` its `db_unavailable` body (S105)". |

Six files (five code and test files, one doc). None is synced from smtw-common.

## 4. Design decisions

- **D1 — Answer `InterfaceError` at the app's error handlers.** One handler covers cases B, C and D
  on every route, with or without `transaction()`.
  - *Rejected:* a liveness check in `get_db` that raises `DBUnavailable`. It costs a second round
    trip per request (the pool has already pinged) or a reach into DBUtils' private `_con`, and
    case B would still need the handler.
- **D2 — One log line, no traceback.** An `InterfaceError` from PyMySQL 1.2.3 is always a closed
  socket, never a fault in Yantra's code, and a traceback per request during an outage would say
  nothing more. The 2013's line is the same today.
  - *Assumption* (tied to the library version): a later PyMySQL could raise `InterfaceError` for
    something else; test 1 pins today's mapping.
- **D3 — `/api/auth/me` treats a lost connection as `DBUnavailable`** (KLA, 15-11-2026, BR1-01
  option (a)). `local_db.connection_lost` already holds the rule of what a loss is, so no new rule is
  written. `auth_me` logs the loss with the shared line, so a caught error is never silent
  (CLAUDE-COMMON *Error handling*); that is why `log_connection_lost` is public.
  - *Rejected:* no log line in `auth_me`. The degraded answer would hide the cause of that request.

No architecture doc is configured (no *Architecture* entry in `.claude/CLAUDE.md` § Step workflow),
so there is no departure to state.

## 5. Tests and acceptance

Write the failing tests first. Test 1 and both cases of test 2 fail on today's code (500, 500 and
503); test 3 passes today and guards the re-raise. All three raise the error from a stub; no
database loss is needed. `DB_TEXT` is `test_errors.py`'s copy of `DB_LOST_TEXT`.

In `backend/tests/test_errors.py`:
1. **`test_a_closed_connection_is_the_same_503`.** `failing_version(pymysql.err.InterfaceError(0, ""))`
   (the existing fixture, `test_errors.py:14`). With `caplog` at ERROR, `client.get("/api/version")`
   gives `(503, {"error": DB_TEXT})`. Expect an `api_common` record whose message contains
   `GET /api/version` and `connection closed`, with `exc_info` None (no traceback).

In `backend/tests/test_auth.py`, class `TestDatabaseDown` (Bearer tokens through
`_bearer(_token(…))`, as its three tests do; `import app as app_module`):
2. **`test_a_lost_connection_gives_the_token_permissions`**, parametrized over
   `pymysql.err.InterfaceError(0, "")` (detail `connection closed`) and
   `pymysql.err.OperationalError(2013, "Lost connection to MySQL server during query")` (detail
   `2013`). Monkeypatch `app_module.current_memberships` (the name `auth_me` calls,
   `app.py:12-14`) to raise the error. With `caplog` at ERROR:
   - IT admin's `/api/auth/me` gives 200 with `db_unavailable` True, `sites` None, `person_id`
     None, `role` `"it_admin"` and `permissions == auth_utils.compute_permissions(["it_admin"])`; an
     `api_common` record contains `GET /api/auth/me` and the detail;
   - a `maintenance_team` token's `/api/auth/me` gives 200 with `permissions == []` and
     `db_unavailable` True.
3. **`test_another_database_error_in_auth_me_is_not_hidden`.** The same monkeypatch, raising
   `pymysql.err.OperationalError(1213, "Deadlock found when trying to get lock")`. IT admin's
   `/api/auth/me` gives `server_error(res) == SERVER_ERROR` (`tests.conftest`, as
   `test_a_deadlock_is_the_500` checks), not a `db_unavailable` body.

**Existing tests that stay green unchanged:** `test_errors.py` (`test_a_lost_connection_is_503`,
`test_a_deadlock_is_the_500`, `test_db_unavailable_is_the_same_503_without_the_cause`);
`test_auth.py::TestDatabaseDown`'s three `db_down` tests and `test_access_control_api.py::TestDatabaseDown::test_internal_it_admin_still_reaches_me` (the `DBUnavailable` half of the clause; the other `/api/auth/me` callers in the tests reach no error path);
`test_pm_templates_api.py`'s `InterfaceError` stub test (`:195-203`; the loop turns it into
`DBUnavailable` before any handler); `test_worker.py::TestConnectionLost`. `grep "Database
connection lost" backend/tests` finds no assertion on the 2013 line's text, which is unchanged.
Always-check tests (`test_role_matrix`, `conftest.py` `_TABLES`, `db_down`, the migration tests):
not touched (no key, no table, no migration).

**Runs.** While coding, from the repo root:
`YANTRA_TEST_RUN=s105c1 cmd //c "tooling\\run-backend-tests.bat tests/test_errors.py tests/test_auth.py tests/test_access_control_api.py tests/test_pm_templates_api.py"`.
Once at the end: `tooling/run-tests.bat` (it includes the line-width check).
**Browser tests: none.** No frontend file changes; the 503 body and the `db_unavailable` body are
the ones the screens already handle (`throwIfFailed` in `frontend/src/api.js`,
`meterLabels.isUnavailable`, `NoAccessView.vue`).

**Manual checks:** none. **On a real device:** none.

## 6. Open questions and assumptions

- **Assumption:** production uses the same DBUtils (3.2.0) and PyMySQL (1.2.3) as `backend/uv.lock`,
  so the cases in § 0 hold there.
- **Note for smtw-common (not fixed here):** `SMTW-WebApp-Base.md` § DB Connection Pattern › *The
  app runs while the database is missing or down* names only the "unavailable" error; a DBUtils pool
  that stays down hands out PyMySQL's `InterfaceError` instead, so other apps on the pattern may
  answer it as a 500.
- **Gate A answers (KLA, 19-11-2026):** the brief approved as cut; the half out-of-date
  parenthesis in `pm_templates.settle_template_plans` (`pm_templates.py:188-189`) is left as it is.

## 7. Amendments

None.

## Review log

| Finding | Severity | Answer |
|---|---|---|
| BR1-01 | major | Accepted (KLA's decision, 15-11-2026, option (a)). `app.auth_me` catches `(DBUnavailable, pymysql.MySQLError)`; a `MySQLError` that `local_db.connection_lost(None, exc)` does not call a loss is re-raised; a loss is logged by the new `api_common.log_connection_lost` and answers the same `db_unavailable` body (§ 1.2, D3). Tests 2 and 3 in `test_auth.py::TestDatabaseDown`. § 0 names the page-load symptom; the `.claude/CLAUDE.md` line (§ 3) names `/api/auth/me`. |
| BR1-02 | minor | Accepted, option (a), in round 1. Void since 19-11-2026: the test it changed (a real `KILL` inside `create_site`) is cut with the fixture. |
| BR1-03 | minor | Accepted, option (a), in round 1. Void since 19-11-2026: the `server_down()` test is cut with the fixture; the rule (a loss during the permission read is the 503, never a grant) stays in § 1 Rules, with its evidence from `auth_utils`. |
| BR1-04 | minor | Accepted, option (a), in round 1. Void since 19-11-2026: KLA reversed it; `access_control`'s warnings are out of scope (§ 1). |
| BR1-05…BR1-11 | nit | Accepted, all seven, in round 1. 05 (`throwIfFailed` named) stands. 06 (`describe_error`'s context rule), 07 and 08 (the fixture's kill), 09 (the `/smtw-review` point), 10 (test numbering) and 11 (Q1's reason) are void since 19-11-2026: what they changed is cut. |
| BR2-01 | minor | Accepted, option (a). The 2013 half of `auth_me`'s loss is the second case of test 2 (it was test 12). |
| BR2-02 | minor | Settled by KLA 19-11-2026 as option (c): the *Try again* button is not in this step and nothing is queued (§ 1 *Out of scope*). |
| BR2-03…BR2-06 | nit | Accepted, all four, in round 2. 04 (`DBUnavailable` not logged in `auth_me`, as today) stands in § 1.2. 03 (`access_control`'s new log form), 05 (`connection_lost`'s docstring) and 06 (the `access_control` tests in the run list) are void since 19-11-2026: what they changed is cut. |
| KLA 19-11-2026 | — | Cut to a small step ("database outages are rare; we don't need too fancy code to handle it"). Kept: the `InterfaceError` handler, `auth_me`'s outage answer for a loss, the `get_db` comment, the `.claude/CLAUDE.md` line. Cut: `describe_error`'s `__context__` rule and `CONNECTION_CLOSED_TEXT`, `access_control`'s log lines, the `lost_connection` fixture and its eight real-loss tests, the `pm_templates` and `connection_lost` docstring edits, the `/smtw-review` point, Q1's laptop check; Q3 settled as (c). Twelve tests became three (stub-raised); eleven files became six. Answers made void: BR1-02, BR1-03, BR1-04, BR1-06…BR1-11, BR2-03, BR2-05, BR2-06. The full r2 brief is kept as `scratch/S105-brief-r2-full.md`. |

## Feedback

- idea: the brief writer's probe needed `YANTRA_TESTING=1` to import `config` without a
  `secrets_app.py` (first run failed with `RuntimeError: secrets_app.py not found`); one line in
  *Test services* saying how to run a scratch probe against the dev DB would save a run.
- hindrance: the facts run marks a correct `file:line` as "`<name>` moved?" whenever the same
  paragraph names a function defined elsewhere (`scratch/brief-facts-S105.md`, the *Cited lines*
  for `db_helpers.py:28-29`, `local_db.py:1792`, `pm_templates.py:204`); checking each by hand
  took a few minutes. Matching a name only to the cite next to it would cut the noise.
- rule: self-check item 4 (identity paths) asks about editable fields, not about a route that
  degrades instead of refusing; the round-1 major (BR1-01, `/api/auth/me`'s `except DBUnavailable`)
  was such a route. An item "for an exception the step remaps, grep its `except` sites and their
  parents' (`git grep -n "except.*<Name>"`)" would have caught it before review.
- rule (round 2): when a step changes which screen a user lands on (here `/api/auth/me`'s answer
  sends floor users to `NoAccessView.vue`), self-check item 13 (screens) does not say to read that
  screen, because the step does not edit it. BR2-02 came from it. One line in item 13, "a screen
  the change newly sends users to counts as a screen of the step", would catch it before review.
- hindrance: the Bash tool failed a quoted heredoc that held a Python edit script with many
  apostrophes and backticks ("unexpected EOF while looking for matching `''"); writing the script
  to the scratchpad with Write and running it worked.
- waste (19-11-2026): the brief grew to 553 lines and eleven files for a rare fault before anyone
  asked how much handling an outage deserves; a line in the spawn prompt or the self-check
  ("size the handling to how often the fault happens; ask the user when the real-world fix is
  bigger than the fault") would have saved two review rounds of fixture detail.
