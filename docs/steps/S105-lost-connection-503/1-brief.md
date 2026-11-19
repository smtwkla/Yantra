```
Step: S105 — A lost database connection answers 503, not 500
Doc: brief
Author: Brief writer (Opus)
Date: 14-11-2026 (revised 15-11-2026 for review rounds 1 and 2)
Track: full (chosen by KLA 14-11-2026; the writer proposed light)
Baseline: 9cde498 + uncommitted edits to .claude/CLAUDE.md and backend/tests/conftest.py (not a step)
Status: Gate A — waiting for KLA (brief review r1, r2 done; Q3 open)
```

# S105 — A lost database connection answers 503, not 500

**The point.** When the database server goes down, or stays down after a connection is lost, most
requests answer a plain **500** ("Something went wrong — try again") instead of the repo's **503**
("Yantra can't reach its database. Try again in a few minutes."). The cause is PyMySQL's
closed-socket `InterfaceError(0, "")`. `api_common` has no handler for it, so it falls to
`_unexpected_error`. The fix adds one error handler, makes `local_db.describe_error` name the real
cause behind that error, keeps `/api/auth/me`'s designed outage answer for a lost connection too
(KLA, 15-11-2026), and adds a shared test fixture that loses the connection for real (a `KILL` from
a second connection).

Source: KLA's feedback triage of 14-11-2026, from S104's code reviews r5 and r6, § Feedback
(`docs/steps/S104-pm-templates-one-path/4-code-review-r5.md`, `4-code-review-r6.md`).

## 0. The fault, confirmed

Two read-only probes against the dev DB (`scratch/s105_lost_connection_probe.py`, log
`scratch/s105-probe.log`; `scratch/s105_fixture_probe.py`) borrowed a connection from a real
`PooledDB` (`local_db.init_pool`), killed it with `KILL CONNECTION <id>` from a second connection,
and sent the result through `db_helpers.transaction` and the app's own `register_error_handlers`.
"Server stays down" means DBUtils' reconnect was refused.

| Case | What reaches the caller | `describe_error` today | Flask answers today |
|---|---|---|---|
| A. Killed mid-transaction, server up (the reconnect works) | `OperationalError(2013, 'Lost connection to MySQL server during query')` | `Lost connection … (error 2013)` | **503** |
| B. Killed mid-transaction, server stays down | `InterfaceError(0, '')`, `__context__` = the 2013 | `' (error 0)'` | **500** |
| C. An idle pooled connection died while the server is down; the next request reads | `InterfaceError(0, '')`, no `__context__` | `' (error 0)'` | **500** |
| D. Same as C; the request's first statement is `transaction()`'s `conn.begin()` | `InterfaceError(0, '')` from `db_helpers.py:48` | `' (error 0)'` | **500** |

Why, with evidence:
- **B.** Inside a transaction, DBUtils' cursor does not retry. It tries to reopen the connection, and
  when that fails it re-raises the 2013 (`backend/.venv/Lib/site-packages/dbutils/steady_db.py:728-828`,
  `tough_method`). `db_helpers.transaction` then calls `conn.rollback()` (`db_helpers.py:51-53`).
  PyMySQL has already closed the socket, so its rollback raises `InterfaceError(0, "")`
  (`backend/.venv/Lib/site-packages/pymysql/connections.py:875`, `_execute_command`). DBUtils' `rollback` tries to reopen, fails, and
  re-raises that error (`backend/.venv/Lib/site-packages/dbutils/steady_db.py:532-545`). The 2013 survives only as its `__context__`.
  In case A the cursor's reopen succeeds, so the rollback runs on the new connection and the 2013
  reaches `_operational_error`.
- **C, D.** The pool pings a cached connection at checkout (`ping=1`, `local_db.py:1701`). When the
  ping fails and the reconnect fails too, `_ping_check` swallows both errors and returns `False`
  (`backend/.venv/Lib/site-packages/dbutils/steady_db.py:409-450`), and `PooledDB.connection()` hands out the dead connection without an
  error (`backend/.venv/Lib/site-packages/dbutils/pooled_db.py:371-379`). Only a brand-new connection (an empty idle cache) raises,
  as `OperationalError` 2003 → `get_db` → `DBUnavailable` → 503 (`db_helpers.py:27-32`). So the
  comment at `db_helpers.py:28-29` ("an error means the server itself cannot be reached") is wrong
  for a cached connection. After any traffic the idle cache is never empty, so while the server is
  down, nearly every request gets C or D.
- **Every `InterfaceError` from PyMySQL is a closed socket.** PyMySQL 1.2.3 raises it in one place
  only, `backend/.venv/Lib/site-packages/pymysql/connections.py:875` (`grep InterfaceError backend/.venv/Lib/site-packages/pymysql/*.py`). The
  wrapper's other errors are DBUtils' own classes, not `pymysql.MySQLError`.
- **Flask routes it to `Exception`.** `InterfaceError`'s MRO is `InterfaceError → Error → MySQLError
  → Exception`, not `OperationalError` (probe output). So `_unexpected_error` answers it
  (`api_common.py:87-91`), with a traceback in the log and the 500 text on the screen.

What the user sees today with the server down:
- **Readings sheet:** it stops at the first unsaved row only on 502–504 (`isUnavailable`,
  `frontend/src/utils/meterLabels.js:183-185`; `ReadingsSheet.vue:263`). On a 500 it tries every
  row against the dead database, and each row shows "Something went wrong — try again".
- **Every other screen:** it shows "Something went wrong — try again" (`throwIfFailed` in
  `frontend/src/api.js` sends the body's `error`). That text asks for an immediate retry. The 503
  text tells the user to wait.
- **A page load (BR1-01).** `/api/auth/me` is built to answer while the database is down: its
  `except DBUnavailable` branch sends the token's permissions with `db_unavailable: true`, "so IT
  admin can still reach Settings › Database" (`app.auth_me`, `backend/app.py:131-164`;
  `test_auth.py::TestDatabaseDown`). In cases C and D `get_db` raises nothing, and the first
  statement (`current_person_id`, through `current_memberships` or the `get_db().cursor()` below
  it) raises the `InterfaceError`, which that branch does not catch. The answer is a 500, so
  `loadProfile` (`frontend/src/stores/auth.js:78-97`) sets `authError` and `App.vue` shows the
  full-page error card (`App.vue:73`). Nobody gets the app shell, and IT admin cannot open
  *Settings › Database*.

## 1. What will be built, and out of scope

**Built:**
1. **Every closed-socket error answers the database 503.** `api_common` registers a handler for
   `pymysql.err.InterfaceError`. It answers `{"error": DB_LOST_TEXT}` with status 503, the same body
   as `_operational_error`'s lost-connection branch and `app._db_unavailable`. It logs one line at
   ERROR through the new public `api_common.log_connection_lost(exc)`:
   `Database connection lost on <METHOD> <path>: <describe_error(exc)>`. The log has no
   traceback (D2). `_operational_error`'s lost-connection branch calls the same function, so the
   two log lines match (today it logs `%s` of the exception, i.e. `(2013, 'Lost connection …')`).
2. **`describe_error` names the cause behind a closed socket.** For an `InterfaceError`:
   - when its `__context__` is a `pymysql.MySQLError` that is not itself an `InterfaceError`, it
     returns that context's description by today's rule: with two or more `args`,
     `"<args[1]> (error <args[0]>)"` (e.g. `Lost connection to MySQL server during query (error
     2013)`); with fewer, `str(context)` (so a one-argument `MySQLError` gives its own text);
   - otherwise it returns the new constant `local_db.CONNECTION_CLOSED_TEXT` =
     `"Database connection closed (error 0)"` (case C/D: DBUtils swallowed the ping's error, so no
     cause is left to name).
   It looks one level deep only (D3). For every other exception the result is unchanged. Every
   caller benefits at once: `pm_templates.settle_template_plans` (`pm_templates.py:204`, the
   `DBUnavailable` message that `app._db_unavailable` logs), the worker's main loop
   (`worker.py:197`), `ensure_schema` (`local_db.py:1792`), `db_status` (`local_db.py:1834`,
   `:1852`) and the schema docs tool (`tooling/schema/schema_docs.py:95-131`).
3. **`/api/auth/me` keeps its outage answer for a lost connection** (KLA, 15-11-2026, D7).
   `app.auth_me`'s `except DBUnavailable:` becomes one clause,
   `except (DBUnavailable, pymysql.MySQLError) as exc:`:
   - a `pymysql.MySQLError` that `local_db.connection_lost(None, exc)` does not call a loss is
     re-raised with a bare `raise` (a deadlock, a lock wait or an SQL fault stays the 500 of
     `_operational_error` / `_unexpected_error`);
   - a loss (an `InterfaceError`, or an `OperationalError` with a lost code) is logged by
     `api_common.log_connection_lost(exc)` (the line of item 1);
   - then, for a loss and for `DBUnavailable` alike, the body of today's branch:
     `role=display_role(user["roles"], [])`, `permissions=user["permissions"]` (the token's),
     `sites=None`, `person_id=None`, `db_unavailable=True`, status 200. `DBUnavailable` is not
     logged here, as today (`get_db` logs nothing; `app._db_unavailable`, which would log it, is
     not reached, because `auth_me`'s clause catches it first).
   `connection_lost(None, …)` decides from the error alone (`getattr(None, "open", True)` is
   `True`; `local_db.py:1645-1661`), as for the pool's wrapper, which has no `open`. Both halves
   of a loss are tested: the `InterfaceError` by a real `KILL` (test 9), the `OperationalError`
   2013 by a stub (test 12; BR2-01). The 2013 reaches `auth_me` for real when a connection that
   was alive at checkout is lost between two statements with the server down: `auth_me` uses no
   transaction, so DBUtils retries on a new cursor, fails to reopen, and re-raises the 2013 with
   no `__context__` (`backend/.venv/Lib/site-packages/dbutils/steady_db.py:755-828`; the
   reviewer's probe `scratch/s105_br2_probe.py`). Today that 2013 is the 503 of
   `_operational_error`; after the step it is the 200.
4. **`access_control`'s two outage warnings name the cause** (BR1-04): `internal_networks`
   (`access_control.py:118`) and the access-log write in `_record` (`access_control.py:235`) log
   `describe_error(exc)` in place of `%s` of the exception. Only an exception that is not a
   `pymysql.MySQLError` reads as today (`describe_error` returns `str(exc)`). A `MySQLError` with
   two `args` changes from the tuple form, e.g. `(2003, "Can't connect …")`, to the
   `<message> (error <code>)` form of every other line, e.g. `Can't connect … (error 2003)`; the
   closed socket's `(0, '')` becomes `Database connection closed (error 0)` (or its cause, § 1.2).
   No test asserts the old form (§ 5). Their behaviour (the fallback list, the 30 s back-off) is unchanged.
5. **A shared fixture that loses the connection for real:** `lost_connection` in
   `backend/tests/conftest.py`, next to `db_down` (§ 3 gives its contract). The tests in § 5 use
   it: the request's own connection is killed with `KILL CONNECTION`, and the server "stays down"
   because new connections are refused.
6. **Comments that are now wrong are corrected:** `db_helpers.get_db` (`db_helpers.py:28-29`),
   `_operational_error`'s docstring (`api_common.py:95-97`), the sentence in
   `settle_template_plans`' docstring that says the app answers neither error as a 503
   (`pm_templates.py:188-189`), and `auth_me`'s docstring ("answers while the database is down"
   now also covers a lost connection).

What the user sees after the step, with the server down: every screen shows the 503 text; the
readings sheet stops at the first unsaved row; a page load gets the app shell, where IT admin
reaches *Settings › Database*. A person whose rights come from the database (operators,
technicians, engineers, managers) gets the database branch of `NoAccessView.vue`, unchanged since
S011: an icon and "The database is unavailable — try again shortly.", with no button. That screen
stays until the page is reloaded, also after the database is back (`dbUnavailable` is set once in
`loadProfile`, `frontend/src/stores/auth.js`), and the installed app (`"display": "standalone"` in
`frontend/public/manifest.webmanifest`) has no reload button. This is no regression: today the
same person gets the full-page error card with only *Sign out*. The gap is named under *Out of
scope*, and § 6 Q3 asks KLA whether to close it here (BR2-02).

**Rules** (nothing left to the coder):
- The 503 body is exactly `{"error": DB_LOST_TEXT}`. It never carries the cause or the error code
  (S064 UX-13: the cause goes to the log only).
- A request that loses its connection during the permission read gets the 503, never a grant.
  Today the `InterfaceError` is a 500, after the step a 503: both refuse. Nothing in `auth_utils`
  catches it (`require_auth` reads no database; `current_memberships` and `current_person_id` let
  it through), so fail-closed is unchanged. Test 10 checks this.
- `/api/auth/me` on a loss grants only what the token grants, exactly as on `DBUnavailable`
  (S011 § 5.2): a `maintenance_team` login gets `permissions: []`, IT admin
  `compute_permissions(["it_admin"])`. No membership, site or person is read or sent. Test 9
  checks both for the `InterfaceError`, test 12 IT admin's for the 2013.
- `db_helpers.transaction` is not changed. The server rolls back an uncommitted transaction when its
  connection drops, so nothing is half-written. Test 3 checks this: its row is written inside the
  transaction before the connection is lost.
- `_operational_error`'s rule for other codes is unchanged: 1213 (deadlock), 1205 (lock wait) and
  any non-loss code stay the plain 500. In `auth_me` too (test 11).
- `local_db.connection_lost`'s code is unchanged (its docstring adds `app.auth_me` to its users,
  § 3). It already counts an `InterfaceError` as a loss (S104 CR5-01).

**Out of scope:**
- No retry of the request and no `Retry-After` header. The 503s answer as they do today.
- The worker's handling (`worker.py:133-145`). It already treats a closed connection as a loss.
  Only its log line improves, through `describe_error`.
- No frontend change (the `db_unavailable` view exists), no migration, no RBAC change, no new
  dependency.
- **The outage screen's *Try again*** (BR2-02; KLA's choice in § 6 Q3, and this text follows its
  recommended option (a)). `NoAccessView.vue`'s database branch has no button, so a floor user
  must reload the page by hand (pull-to-refresh on Android, close and reopen the app on an
  iPhone). Its text, "The database is unavailable — try again shortly.", is a second wording of
  `DB_LOST_TEXT` ("Yantra can't reach its database. Try again in a few minutes.", S064 UX-13).
  The orchestrator queues a small frontend step: a *Try again* button on that branch that reloads
  the page, and the 503's wording there.

## 2. Standards and practice

- **CLAUDE-COMMON *Idle connections*** (the repo's own rule): "Detect a dead connection on first use
  (`OperationalError`/`InterfaceError` or equivalent) and reconnect, rather than returning a 500".
  Today the 503 rule covers only the `OperationalError` half. This step adds the `InterfaceError`
  half. The reconnect itself already works: the pool's checkout ping reopens the connection once the
  server answers (probe case C, then "server back": `SELECT 1` succeeds). Test 4 pins it.
- **HTTP semantics, RFC 9110 § 15.6.1 and § 15.6.4.** A 500 means an unexpected condition in the
  server. A 503 means the server cannot handle the request now and probably can after a delay. A
  database outage is the second case. The screens act on the difference (the readings sheet stops;
  the PM template page says "The template may be saved").
- **ISO/IEC 27001:2022 Annex A 8.15 *Logging*.** Logs must record exceptions and faults in a form a
  person can use. Today the log lines say ` (error 0)` or `(0, '')` and hide the real fault (a 2013
  lost connection, or a closed socket). After the fix they name it: the request line, the worker's
  and `ensure_schema`'s lines, and `access_control`'s two warnings. The 503 body still gives no
  internal detail to the user (CLAUDE-COMMON scope B: no internal codes on screen).
- **ISO/IEC 27001:2022 Annex A 5.15 *Access control*.** Access follows the rules set for it. The
  outage answer of `/api/auth/me` grants only the token's own permissions, never a database grant
  it could not read (§ 1 Rules; tests 9, 10 and 12).
- **Maintenance standards** (TPM, ISO 14224, EN 13306, ISO 55000, SMRP): not touched.

## 3. Where

| File | Change |
|---|---|
| `backend/api_common.py` | New public `log_connection_lost(exc)`: the ERROR line of § 1.1 with `describe_error(exc)`. New `_database_lost(exc)`: calls it, answers `{"error": DB_LOST_TEXT}`, 503. `_operational_error` calls `_database_lost` for a lost code. `register_error_handlers` adds `app.register_error_handler(pymysql.err.InterfaceError, _database_lost)` beside the `OperationalError` line. Import `describe_error` from `local_db`; `api_common` already imports `is_connection_lost` from there (`api_common.py:19`), so no new dependency direction. The docstring of `_operational_error` loses "the pool's ping passed" and names both errors. |
| `backend/local_db.py` | `CONNECTION_CLOSED_TEXT` constant; `describe_error` rule of § 1.2 (outside the exempt `_MIGRATIONS` block, so the 120-character limit applies). `connection_lost`'s docstring: add `app.auth_me` (S105) to the list of its users ("Shared by the worker and pm_generate's per-plan loop … and a template save's loop"); docstring only. |
| `backend/app.py` | `auth_me`'s except clause of § 1.3; `import pymysql`; `connection_lost` from `local_db` (already imported from there: `DBUnavailable`, `ensure_schema`, `init_pool`) and `log_connection_lost` from `api_common` (already imported: `DB_LOST_TEXT`, `register_error_handlers`). The docstring's outage sentence names both. |
| `backend/access_control.py` | The two warnings of § 1.4 (`:118`, `:235`) log `describe_error(exc)`; `describe_error` added to the existing `local_db` import (`access_control.py:24`). |
| `backend/db_helpers.py` | The comment in `get_db` (`:28-29`): the checkout ping replaces a dead cached connection only when the server answers. When it does not, DBUtils hands out the dead connection without an error, and its first statement raises PyMySQL's `InterfaceError`, which `api_common` answers with the same 503 (S105). Comment only. |
| `backend/pm_templates.py` | Docstring of `settle_template_plans` (`:188-189`): drop "neither of which the app answers as a 503". The loop still has to tell a loss from one plan's fault itself, because it catches `Exception`. Docstring only; the code stays. |
| `backend/tests/conftest.py` | The `lost_connection` fixture (contract below). |
| `backend/tests/test_errors.py` | Tests 1–7 (§ 5). |
| `backend/tests/test_pm_templates_api.py` | Test 8 (§ 5), beside `test_a_lost_connection_while_settling_answers_503_and_the_template_stands`, which stays. |
| `backend/tests/test_auth.py` | Tests 9–12 (§ 5), in `TestDatabaseDown`. |
| *Docs (housekeeping, by the coder)*: `.claude/CLAUDE.md` | § Yantra Specifics, *DB may not exist*: add "a connection lost mid-request (an `OperationalError` with a lost code, or PyMySQL's closed-socket `InterfaceError`, which DBUtils hands out when the server stays down) answers the same 503 (`api_common`, S105); `/api/auth/me` answers its `db_unavailable` body for a lost connection as for `DBUnavailable` (S105); a test loses a connection for real with the `lost_connection` fixture". § SMTW-Review: the point proposed in § 4 D6. |

Eleven files. None of them is synced from smtw-common (`grep -l "synced from"` finds none of them).

**The `lost_connection` fixture** (function scope; depends on `monkeypatch`):
1. **Set-up.** Keep the real `pymysql.connect`. Replace `pymysql.connect` (the module attribute)
   with a wrapper. While "down", the wrapper raises
   `pymysql.err.OperationalError(2003, "Can't connect to MySQL server (test: server down)")`.
   While "up", it calls the real function and records the new connection's `thread_id()`. Then
   build a fresh pool: `monkeypatch.setattr(local_db, "_pool", None)`, then
   `local_db.init_pool(config.DB_CONFIG)`. The swap must come first. DBUtils binds `creator.connect`
   when it makes each connection (`backend/.venv/Lib/site-packages/dbutils/steady_db.py:205`, `self._creator = creator.connect`), so only a
   pool built after the swap has its reconnects refused (checked: `scratch/s105_fixture_probe.py`,
   cases A–C). The swap also covers `local_db.get_local_db` (it calls `pymysql.connect`), so
   `db_rows` is refused while down. A test calls `server_back()` before it reads rows.
2. **`kill_request(down=True)`**, called inside a request (from a test view or a wrapped function).
   It reads the request's connection id through `flask.g.db`
   (`SELECT CONNECTION_ID() AS id`) and kills it (step 5). With `down=True` it then sets "down".
3. **`server_down()`**, called by the test between requests. It kills every connection the wrapper
   recorded that is still alive (step 5), then sets "down": the server has stopped for everyone.
   Killing them all matters. The access-log hook takes a second pooled connection after each
   request (`access_control.py:183`), so the idle cache holds more than one connection, and a live
   one would be checked out and would answer. "Every recorded connection" includes a dedicated one
   that a test or another fixture opened through `pymysql.connect` after `lost_connection` was set
   up (e.g. `get_local_db`): the wrapper records every connect. The fixture's docstring says so.
4. **`server_back()`** sets "up". The next checkout's ping fails on the dead connection, the
   reconnect succeeds, and the pool hands out a fresh connection.
5. **The kill.** With no id to kill, return at once (`WHERE ID IN ()` is a syntax error, and
   `server_down()` can find every recorded connection closed). Otherwise open the killer connection
   with the kept real `pymysql.connect` and
   `local_db._connect_kwargs(config.DB_CONFIG, 5)`, so the wrapper does not record it. Run
   `KILL CONNECTION %s` for each id. Ignore error 1094 (unknown thread id: the connection already
   closed itself) and no other code. Then poll
   `SELECT COUNT(*) AS n FROM information_schema.PROCESSLIST WHERE ID IN (…)` every 0.1 s, at most
   5 s. If the ids are still there after 5 s, fail the test with a message that names them. In the
   probe the kill had landed by the first poll (`wait polls: 0`); the poll keeps the test
   deterministic if it ever lands later. Close the killer connection.
6. **Teardown:** `server_back()`, then close the fixture's pool (`PooledDB.close()`,
   `backend/.venv/Lib/site-packages/dbutils/pooled_db.py:411`). `monkeypatch` then restores `local_db._pool` and `pymysql.connect`.
   The kill touches only connection ids this process's wrapper made, so other pytest-xdist workers
   (their own databases, their own connections) are never touched.

## 4. Design decisions

- **D1 — Answer `InterfaceError` at the app's error handlers.** One handler covers cases B, C and D,
  and any route, with or without `transaction()`.
  - *Rejected:* changing `transaction()` to re-raise the body's error when the rollback fails. That
    fixes case B only; C and D raise before or outside the rollback.
  - *Rejected:* a liveness check in `get_db` that raises `DBUnavailable`. It needs a second round
    trip per request (the pool has already pinged), or a reach into DBUtils' private `_con` to read
    PyMySQL's `open`. Case B would still need the handler.
  - *Rejected:* a stronger DBUtils `ping` setting (e.g. ping on every cursor). The reconnect still
    fails silently while the server is down (`_ping_check`, `backend/.venv/Lib/site-packages/dbutils/steady_db.py:441-449`), so the dead
    connection is still used.
- **D2 — One log line, no traceback.** An `InterfaceError` from PyMySQL 1.2.3 is always a closed
  socket (`backend/.venv/Lib/site-packages/pymysql/connections.py:875`, the only raise), never a fault in Yantra's code. This matches the
  2013's line today. `pm_templates` keeps its own traceback line for its loop (S104 CR6-01).
  - *Rejected:* logging it through `logger.exception`, as `_unexpected_error` does. While the server
    is down every request would write a traceback, and none of them would say more than the
    one-line cause.
  - *Assumption* (tied to the library version): a later PyMySQL could raise `InterfaceError` for
    something else. Test 6 pins today's mapping, and tests 2–4 pin the real error.
- **D3 — `describe_error` looks one level into `__context__`.** Every known caller gets the swap
  from exactly one level: DBUtils' rollback raises the `InterfaceError` while it handles the 2013.
  When nothing usable is there, the fixed text says what is known: the connection was closed.
  - *Rejected:* following the whole `__context__` chain. No caller needs it, and a loop would need a
    guard.
  - *Rejected:* returning `str(exc.__context__)`. That gives the tuple form `(2013, '…')`, not the
    `message (error code)` form every other line uses.
- **D4 — The test's "server down" is a refused `pymysql.connect`; the loss itself is a real
  `KILL`.** The error that reaches the code is the one PyMySQL and DBUtils really produce, which is
  what the S104 review asked for. Only the reconnect is refused, which is what a stopped server
  does.
  - *Rejected:* stopping the dev DB container. Parallel test workers and other sessions share it,
    and it is a service change.
  - *Rejected:* patching DBUtils' private `SteadyDBConnection._create`. The first probe did that;
    a fixture should not depend on it.
  - *Rejected:* raising the exception from a stub (as `test_errors.py::failing_version` and
    `TestConnectionLost` do) for the tests of *which error arrives*. A stub shows only what the
    handler does with the error. Tests of what a handler does with a given error (tests 5, 6, 11)
    still raise it from a stub.
- **D5 — The fixture lives in `conftest.py`.** This is the repo's place for shared fixtures:
  `db_down` is there, "shared by the auth, network-gate and properties tests".
- **D6 — Proposed `/smtw-review` point** (`.claude/CLAUDE.md` § SMTW-Review): "**Lost connection
  (S105):** a database that is down or lost answers the 503 on every route — `DBUnavailable`
  (`app._db_unavailable`), an `OperationalError` with a lost code, and PyMySQL's closed-socket
  `InterfaceError`, which DBUtils hands out when the server stays down
  (`api_common.register_error_handlers`) — except `/api/auth/me`, which answers 200 with
  `db_unavailable: true` and the token's permissions only, for all three (`app.auth_me`, through
  `local_db.connection_lost`). A route that catches `DBUnavailable` to degrade must catch a lost
  connection too. A test of *which error arrives* uses the `lost_connection` fixture (a real
  `KILL`); a test of what a handler does with a given error may raise it."
- **D7 — `/api/auth/me` treats a lost connection as `DBUnavailable`** (KLA's decision, 15-11-2026,
  review finding BR1-01 option (a)). The route is the one place that catches `DBUnavailable` to
  degrade rather than refuse (`grep "except.*DBUnavailable" backend/*.py`: `app.py`, and
  `access_control.py` and `local_db.ensure_schema`, which both catch `pymysql.MySQLError` too).
  `local_db.connection_lost` already holds the rule of what a loss is, so no new rule is written.
  - *Rejected (b):* make `get_db` raise `DBUnavailable` for a dead connection, so every
    `except DBUnavailable` works. The cost of D1's second rejection; `auth_me` is the only caller
    that needs it.
  - *Rejected (c):* leave it out with a queued step. The outage mode (IT admin reaching *Settings ›
    Database*) would stay broken in the usual outage until then.

No architecture doc is configured (no *Architecture* entry in `.claude/CLAUDE.md` § Step workflow),
so there is no departure to state.

## 5. Tests and acceptance

Write the failing tests first. Tests 2, 3, 4, 6, 7, 9 and 10 fail on today's code (500, or
` (error 0)` / `(0, '')` in the log); test 12 fails on it too (503, not the 200). Test 1 passes today; it guards case A. Test 5 has no
database. Test 8 passes on status today and fails on its log assertion. Test 11 passes today; it
guards the re-raise of § 1.3.

`DB_TEXT` below is `api_common.DB_LOST_TEXT` (`test_errors.py` has it as `DB_TEXT`; `test_auth.py`
imports `DB_LOST_TEXT` from `api_common`).

In `backend/tests/test_errors.py`:
1. **`test_a_connection_killed_mid_transaction_with_the_server_up_is_503`.** Replace the
   `/api/version` view (`monkeypatch.setitem(app.view_functions, "version", view)`, as
   `failing_version` does). The view runs `conn = get_db()`, then
   `with transaction(conn), conn.cursor() as cur:` `SELECT 1`, then
   `lost_connection.kill_request(down=False)`, then `SELECT 1`. Expect
   `(503, {"error": DB_TEXT})`.
2. **`test_a_connection_lost_mid_transaction_while_the_server_stays_down_is_503`.** As test 1 with
   `kill_request()` (down). Expect `(503, {"error": DB_TEXT})`. Expect a log record from
   `api_common` whose message contains `GET /api/version` and `(error 2013)`, and no `api_common`
   record that contains ` (error 0)` (the access-log hook may log its own warning; it is not checked). Expect the response body not to contain `2013`.
3. **`test_a_real_route_answers_503_and_writes_nothing_when_the_connection_is_lost`.** Wrap
   `masters.insert_row` (monkeypatch the name in `masters`, as `test_masters_api.py:701` does): the
   wrapper (1) calls the real `insert_row(cur, table, clean, actor)`, so the row is in the open
   transaction of `create_site` (`masters.py:240-245`); (2) calls `lost_connection.kill_request()`;
   (3) runs `cur.execute("SELECT 1")` on the same cursor; (4) returns the id. Step 3 raises the 2013
   inside the transaction, the rollback raises the `InterfaceError`, and the answer comes through the
   new handler (without step 3 the loss shows at `conn.commit()` as a 2013, a 503 today, which does
   not use this step's path). Send
   `admin.post("/api/masters/sites", json={"code": uniq.site_code(), "name": "x"})`. Expect
   `(503, {"error": DB_TEXT})`. Then call `lost_connection.server_back()`. Expect no `sites` row
   with that code (`db_rows`): the server dropped the uncommitted INSERT with the session. Expect
   `admin.get("/api/masters/sites").status_code == 200`.
4. **`test_a_dead_pooled_connection_is_503_until_the_server_is_back`.** `admin.get` of
   `/api/masters/sites` gives 200 (this warms the pool). Call `lost_connection.server_down()`.
   The same GET gives `(503, {"error": DB_TEXT})`. Call `lost_connection.server_back()`. The same
   GET gives 200, with no app restart: the checkout ping reconnects (*Idle connections*).
5. **`TestDescribeError`**, plain unit tests with no database. Build each chained exception with
   `try: raise A` / `except A: raise B`, then catch B:
   - an `InterfaceError(0, "")` raised while handling
     `OperationalError(2013, "Lost connection to MySQL server during query")` →
     `"Lost connection to MySQL server during query (error 2013)"`;
   - an `InterfaceError(0, "")` raised while handling `OperationalError("gone")` (one argument) →
     `"gone"` (checked: `str()` of it is `'gone'`);
   - an `InterfaceError(0, "")` with no context → `CONNECTION_CLOSED_TEXT`;
   - an `InterfaceError(0, "")` raised while handling a `ValueError` → `CONNECTION_CLOSED_TEXT`;
   - an `InterfaceError(0, "")` raised while handling another `InterfaceError(0, "")` →
     `CONNECTION_CLOSED_TEXT` (one level, D3);
   - unchanged: `OperationalError(2003, "Can't connect")` → `"Can't connect (error 2003)"`, and
     `DBUnavailable("down")` → `"down"`.
6. **`test_an_interface_error_is_the_same_503`.** `failing_version(pymysql.err.InterfaceError(0, ""))`.
   Expect `(503, {"error": DB_TEXT})` and a log line containing `Database connection closed (error 0)`.
7. **`test_access_control_names_the_cause_when_the_connection_is_lost`.** `admin.get` of
   `/api/masters/sites` gives 200 (warms the pool and the ranges). Call
   `lost_connection.server_down()`, then `access_control.clear_networks_cache()` and
   `access_control.reset_access_log_state()` (so the gate reads the ranges again and the hook
   tries its write; the autouse `_fresh_access_caches` puts them back afterwards). With `caplog` at
   WARNING, the same GET gives 503. Expect an `access_control` record containing
   `Internal networks unreadable (Database connection closed (error 0))`, and one containing
   `Access log: could not write (` and `(error ` (its connection is a dead cached one, `error 0`,
   or a new one refused, `error 2003`, depending on the pool's idle cache). Expect no
   `access_control` record that contains `(0, '')`.

In `backend/tests/test_pm_templates_api.py`:
8. **`test_a_real_lost_connection_while_settling_answers_503_and_names_the_cause`.** Set up with
   `due_on_two` (two nodes). Wrap `pm_jobs.settle_plan_job`: the wrapper calls
   `lost_connection.kill_request()` (down), then the real function, so the loss falls inside
   `settle_one`'s transaction. Send `engineer_a.put(f"{TEMPLATES}/{template['id']}",
   json={"calendar_every": 35})`. Expect 503. Expect `app`'s `Database unavailable on PUT …` log
   record to contain `(error 2013)`, not ` (error 0)`. Then call `server_back()`. Expect the
   template's `calendar_every` to be 35 in `db_rows` (it was committed before the plans settle,
   S104 BR1-12).

In `backend/tests/test_auth.py`, class `TestDatabaseDown` (Bearer tokens through `_bearer(_token(…))`,
as its three tests do):
9. **`test_a_lost_connection_gives_the_token_permissions`.** Warm up:
   `client.get("/api/auth/me", headers=<it_admin>)` gives 200 with `db_unavailable` false. Call
   `lost_connection.server_down()`. With `caplog` at ERROR:
   - IT admin's `/api/auth/me` gives 200 with `db_unavailable` true, `sites` None, `person_id`
     None, `role` `"it_admin"` and `permissions == auth_utils.compute_permissions(["it_admin"])`;
     an `api_common` record contains `GET /api/auth/me` and `CONNECTION_CLOSED_TEXT` (case C);
   - a `maintenance_team` token's `/api/auth/me` gives 200 with `permissions == []` and
     `db_unavailable` true.
   Then `server_back()`: IT admin's `/api/auth/me` gives `db_unavailable` false again.
10. **`test_a_lost_connection_during_the_membership_read_is_503`.** Warm up with IT admin's
   `GET /api/masters/sites` (200). Call `lost_connection.server_down()`. The same GET with a
   `maintenance_team` token (whose memberships come from the database, `current_memberships`)
   gives `(503, {"error": DB_LOST_TEXT})`: the refusal of § 1 Rules, never a grant.
11. **`test_another_database_error_in_auth_me_is_not_hidden`.** Monkeypatch `current_memberships`
   in the module `app` (`import app as app_module`; the name `auth_me` calls,
   `backend/app.py:12-14`) to raise
   `pymysql.err.OperationalError(1213, "Deadlock found when trying to get lock")`. IT admin's
   `/api/auth/me` gives `server_error(res) == SERVER_ERROR` (`tests.conftest`, as
   `test_a_deadlock_is_the_500` checks), not a `db_unavailable` body. No database loss is needed; no `lost_connection`.
12. **`test_a_lost_code_in_auth_me_gives_the_token_permissions`** (BR2-01). The same monkeypatch as
   test 11, raising `pymysql.err.OperationalError(2013, "Lost connection to MySQL server during
   query")`. With `caplog` at ERROR, IT admin's `/api/auth/me` gives 200 with `db_unavailable`
   true, `sites` None, `person_id` None and
   `permissions == auth_utils.compute_permissions(["it_admin"])`; an `api_common` record contains
   `GET /api/auth/me` and `(error 2013)`. No `lost_connection`: the stub tests what `auth_me` does
   with the 2013 (D4); when it arrives for real is § 1.3's evidence.

**Existing tests that stay green unchanged** (checked by `grep InterfaceError backend/tests`, and by
`grep "Database connection lost"`, `grep "could not write"` and `grep "Internal networks unreadable"`
in the tests, which find no assertion on the old log text):
- `test_errors.py`: `test_a_lost_connection_is_503`, `test_a_deadlock_is_the_500`,
  `test_db_unavailable_is_the_same_503_without_the_cause`;
- `test_auth.py::TestDatabaseDown`: `test_it_admin_gets_token_permissions`,
  `test_login_only_user_gets_nothing`, `test_a_check_that_needs_memberships_is_503` (`db_down`:
  the `DBUnavailable` half of the new clause, unchanged);
- `test_access_log_api.py::TestDatabaseDown` (`test_skipped_while_down_and_written_once_back`,
  `test_a_failed_write_backs_off`): no assertion on the warning text;
- `test_access_control_api.py::TestDatabaseDown` (`test_internal_it_admin_still_reaches_me`,
  `test_external_it_admin_is_refused`, `test_ranges_fall_back_to_the_cache`,
  `test_ranges_fall_back_to_the_defaults`): they run `internal_networks`' changed warning, and none
  asserts its text (BR2-06);
- `test_worker.py::TestConnectionLost`;
- `test_task_queue.py::TestWorkerRuns::test_a_failed_rollback_logs_the_original_cause` (it raises
  `pymysql.err.Error`, not `InterfaceError`);
- `test_pm_templates_api.py::TestSettle::test_a_lost_connection_while_settling_answers_503_and_the_template_stands`;
- `test_migration_squash_v41.py` (`describe_error` of a `MigrationBlocked`, not a `MySQLError`).

Always-check tests: `test_rbac.py::TestComputePermissions::test_role_matrix`, `conftest.py`
`_TABLES`, `db_down` and the migration tests are not touched (no key, no table, no migration).

**Runs.** While coding:
`YANTRA_TEST_RUN=s105c1 cmd //c "tooling\\run-backend-tests.bat tests/test_errors.py tests/test_pm_templates_api.py tests/test_auth.py tests/test_access_log_api.py tests/test_access_control_api.py tests/test_worker.py tests/test_task_queue.py"`
from the repo root. Once at the end: `tooling/run-tests.bat` (it includes the line-width check).
**Browser tests: none.** No frontend file changes, and the 503 body and the `db_unavailable` body
are the ones the screens already handle (`throwIfFailed` in `api.js`, `meterLabels.isUnavailable`,
`PmTemplateView.vue:170`, `NoAccessView.vue`).

**Manual checks:** none required. The real `KILL` tests cover the behaviour. An optional check on
KLA's laptop is in § 6, Q1. It is not a device check: a browser engine is not the limit there.

## 6. Open questions and assumptions

- **Q1 (optional check, not a gate).** On the dev laptop with Backend and Frontend running: open
  *Masters › Sites*, run `tooling/dev/dev-db-down.bat`, then save a site. Expect the message
  "Yantra can't reach its database. Try again in a few minutes.", not "Something went wrong — try
  again". Then reload the page while the database is still down: expect the app shell (the top
  bar and the side menu), not the full-page error card; as IT admin, *Settings › Database* opens
  and shows the database unreachable. Run `tooling/dev/dev-db-up.bat` and reload: the page works
  with no backend restart. This shows that a stopped container behaves as the fixture's refused
  connect does. *Recommendation:* skip it unless KLA wants to see it. The probes killed one
  connection and refused the reconnect; neither stopped the server. The same errors follow from the
  code: when the server stops, PyMySQL turns the closed socket into a 2013 (`_read_bytes` and
  `_read_packet`, "MariaDB sends error packet with seqno==0 when shutdown") or a 2006 (`_write_bytes`)
  and calls `_force_close`, after which `_execute_command` raises the `InterfaceError(0, "")`
  (`backend/.venv/Lib/site-packages/pymysql/connections.py:785-790`, `:823-836`, `:845-849`, `:875`).
- **Q2 (settled in review round 1, BR1-04).** `access_control`'s two outage warnings
  (`internal_networks`, `access_control.py:118`; the access-log write, `:235`) now use
  `describe_error` (§ 1.4).
- **Q3 (for KLA at gate A; BR2-02): the outage screen offers no way to try again.** After D7, a
  page load in the usual outage puts every person whose rights come from the database on
  `NoAccessView.vue`'s database branch: "The database is unavailable — try again shortly.", no
  button, and it stays after the database is back until the page is reloaded (§ 1, "What the user
  sees after the step"). Not a regression (today: the error card with only *Sign out*), but the
  step makes it the designed outage screen for the floor, and "try again" names an action the
  screen does not offer. Options:
  - **(a) Keep S105 backend-only (recommended).** The gap is named under *Out of scope*, and the
    orchestrator queues a small step: a *Try again* button on the database branch that reloads the
    page, and `DB_LOST_TEXT`'s wording there. S105 stays with no frontend file and no browser run.
    The brief is written for this option.
  - (b) Add it to this step. It adds `frontend/src/views/NoAccessView.vue` (a *Try again* button
    that calls `window.location.reload()`, and the text "Yantra can't reach its database. Try
    again in a few minutes." in place of today's; the frontend has no copy of `DB_LOST_TEXT`, so
    the text is written in the view), and one browser test in a new
    `frontend/e2e/no-access.spec.js` (named after the screen; not `screens.spec.js`, where every
    test counts as `@device`): with file-level
    `test.use({ serviceWorkers: "block" })` (the repo's rule for a spec that uses `page.route`),
    fulfil `/api/auth/me` with `db_unavailable: true` and empty permissions, expect the text and
    the button, and that a tap loads `/api/auth/me` again. The step then has thirteen files, a
    frontend build check, targeted browser runs (`e2e/no-access.spec.js e2e/screens.spec.js`) and
    one run of the new spec on `--project=phone-webkit` (it uses `page.route`), and "No frontend
    change" and "Browser tests: none" leave § 1 and § 5.
  - (c) Leave it unsaid. The screen works as it did for `DBUnavailable` since S011, and nobody is
    asked to queue anything.
- **Base pattern gap (for smtw-common, not fixed here).** `SMTW-WebApp-Base.md` § DB Connection
  Pattern › *The app runs while the database is missing or down* asks for a `db_down` fixture and a
  503 test for every layer. That fixture makes `get_db` refuse. It never shows the closed-socket
  `InterfaceError` that a DBUtils pool hands out when the server stays down, so every app on the
  pattern may have this fault, including a degraded `/auth/me` that catches only the
  "unavailable" error. The base is synced, so the gap goes to smtw-common: name `InterfaceError`
  beside `DBUnavailable` there, and add a real-loss fixture to its *Tests* line.
- **Assumption:** production uses the same DBUtils (3.2.0) and PyMySQL (1.2.3) as `backend/uv.lock`,
  so the cases above hold there.

## 7. Amendments

None.

## Review log

| Finding | Severity | Answer |
|---|---|---|
| BR1-01 | major | Accepted (KLA's decision, 15-11-2026, option (a)). `app.auth_me` catches `(DBUnavailable, pymysql.MySQLError)`; a `MySQLError` that `local_db.connection_lost(None, exc)` does not call a loss is re-raised; a loss is logged by the new `api_common.log_connection_lost` and answers the same `db_unavailable` body (§ 1.3, D7). Tests 9 and 11 in `test_auth.py::TestDatabaseDown`. § 0 names the page-load symptom; the `.claude/CLAUDE.md` line (§ 3) and the `/smtw-review` point (D6) now except `/api/auth/me`. Q1 adds the reload. |
| BR1-02 | minor | Accepted, option (a). Test 3's wrapper writes first, then kills, then runs `SELECT 1` on the same cursor, so the INSERT is in the open transaction when the connection is lost and "no `sites` row" is a real check of the rule. |
| BR1-03 | minor | Accepted, option (a). Test 10 in `test_auth.py::TestDatabaseDown`: a `maintenance_team` token's `GET /api/masters/sites` after `server_down()` is the 503. § 1 Rules names it; § 2 adds ISO 27001 A.5.15. |
| BR1-04 | minor | Accepted, option (a). Both `access_control` warnings use `describe_error` (§ 1.4, § 3); test 7 checks both lines; Q2 is settled and removed from *Out of scope*. |
| BR1-05…BR1-11 | nit | Accepted, all seven. 05: `throwIfFailed` in `api.js` cited by name (§ 0, § 5). 06: § 1.2 states today's rule for the context, with a one-argument case in test 5. 07: the kill returns at once with no id (§ 3 step 5). 08: `server_down()` kills dedicated connections too, said in the docstring (§ 3 step 3). 09: D6 rewritten (which error arrives vs what a handler does; `app._db_unavailable` named), D4's stub rejection narrowed to match. 10: tests renumbered in order (old 6, 7, 5 are now 5, 6, 8; the new tests are 7 and 9–11). 11: Q1 gives PyMySQL's shutdown handling as the reason, with lines. |
| BR2-01 | minor | Accepted, option (a), as a separate test 12 (`test_a_lost_code_in_auth_me_gives_the_token_permissions`) rather than a second case inside test 11, so test 11 keeps its name and its "passes today" role and the existing references to it stay right. The stub raises `OperationalError(2013, …)` from `app.current_memberships`; the answer is the `db_unavailable` 200 with IT admin's token permissions and an `api_common` line with `GET /api/auth/me` and `(error 2013)`. It fails today (503), so it joins the tests written first. § 1.3 names both halves and when the 2013 really arrives (the reviewer's probe); § 1 Rules, § 2 A.5.15 and the `test_auth.py` row of § 3 name test 12. |
| BR2-02 | minor | Deferred — to the user (gate A). § 6 Q3 holds the three options, (a) recommended; the brief is written for (a): § 1 "What the user sees after the step" now says what the database branch of `NoAccessView.vue` shows (no button, stays until a reload), and *Out of scope* names the gap and the small step to queue. Q3 (b) lists what that option would add (`NoAccessView.vue`, a new `frontend/e2e/no-access.spec.js`, the runs). |
| BR2-03…BR2-06 | nit | Accepted, all four. 03: § 1.4 says only a non-`MySQLError` reads as today; a two-argument `MySQLError` changes to `<message> (error <code>)`. 04: § 1.3 says `DBUnavailable` is not logged here, as today (`get_db` logs nothing; `app._db_unavailable` is not reached). 05: § 3's `local_db.py` row adds `app.auth_me` to `connection_lost`'s docstring; § 1 Rules says the code is unchanged. 06: `tests/test_access_control_api.py` is in the while-coding command and its four `TestDatabaseDown` tests in the "stay green" list (§ 5). |

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
