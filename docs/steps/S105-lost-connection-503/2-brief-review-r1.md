```
Step: S105 — A lost database connection answers 503, not 500
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 14-11-2026
```

Reviewed against: 9cde498 + uncommitted non-step edits (`.claude/CLAUDE.md`: the *Test services* entry; `backend/tests/conftest.py`: the `admin` fixture's docstring)

**Verdict: one major finding is open (BR1-01); no blocker.** The fault, its cause and the handler design (D1)
hold against the code and the libraries. The gap is one route: `/api/auth/me` is built to answer 200 while the
database is down, and the brief's 503 does not give it that answer in the outage the brief describes. Four
findings in all: 1 major, 3 minor, plus 7 nits. The facts file was given and matches the draft. I re-ran
`scratch/s105_fixture_probe.py` six times against the dev DB: the same result each time (the 2013 behind the
`InterfaceError`, `wait polls: 0`, the reconnect after "server back").

## Findings

### BR1-01 (major) — `/api/auth/me` answers 503 in the outage, not its designed 200 with `db_unavailable`

**The problem.** `app.auth_me` answers while the database is down: it catches `DBUnavailable` and sends the
token's permissions with `db_unavailable: true` (`backend/app.py`, `except DBUnavailable:`), "so IT admin can still
reach Settings › Database". `test_auth.py::TestDatabaseDown` pins this with `db_down`, which makes `get_db`
raise `DBUnavailable`.

In the outage of § 0, cases C and D, `get_db` raises nothing. It hands out the dead connection, and the first
statement of `auth_me` (`current_memberships` → `current_person_id`) raises the `InterfaceError`. `except
DBUnavailable` does not catch it. Today the answer is a 500; after this brief it is a 503. In both, the frontend
(`stores/auth.js`, `loadProfile`) sets `authError`, and `App.vue` shows the full-page error card. Nobody gets the
app shell, and IT admin cannot open *Settings › Database*, which is the one screen made for this moment
(`settings.get_db_status`: "Always 200 — an unreachable database is a status to show").

The brief looked at this path only for security (§ 1 Rules: "Nothing in `auth_utils` catches it, so fail-closed
is unchanged"). That statement is right. The catch that matters is in `app.py`, not `auth_utils`.

**Why it matters.** § 0 says that "while the server is down, nearly every request gets C or D". So the designed
outage mode works only before the first traffic or when the idle cache is empty; in the usual outage it does not.
S105 does not make this worse (a 503 text is better than the 500 text). But S105 is the step that finds the
cause, has the fixture to test it, and then writes into `.claude/CLAUDE.md` and the `/smtw-review` point (D6)
that a lost database "answers the 503 on every route". That sentence is wrong for `/api/auth/me` (200 by
design), and a later audit would read the gap as closed.

**Options.**
- **(a) Fix it in this step (recommended).** `auth_me` treats a lost connection as it treats `DBUnavailable`: a
  second `except pymysql.MySQLError as exc:` that re-raises unless `local_db.connection_lost(None, exc)`, then
  the same degraded body. `connection_lost` already holds the rule (an `InterfaceError`, or an `OperationalError`
  with a lost code), so no new rule is written. One test in `test_auth.py::TestDatabaseDown` with
  `lost_connection`: a warm-up request, `server_down()`, then IT admin's `/api/auth/me` is 200 with
  `db_unavailable: true` and the token's permissions; a `maintenance_team` login gets `permissions: []`. Cost:
  two more files (`app.py`, `test_auth.py`), about ten lines of code. § 1.1, the `.claude/CLAUDE.md` sentence
  and D6 then say: every route answers the 503, except `/api/auth/me`, which answers its `db_unavailable` body
  for all three errors.
- **(b) Make `get_db` raise `DBUnavailable` for a dead connection** (the alternative D1 rejected). Every `except
  DBUnavailable` then works, and the comment in `get_db` stays true. It costs a second ping per request or a
  reach into DBUtils' private `_con`, and case B still needs the handler. Not recommended: `auth_me` is the only
  place that catches `DBUnavailable` to degrade (`grep "except.*DBUnavailable" backend/*.py`:
  `app.py`, and `access_control.py` and `local_db.ensure_schema`, which both catch `pymysql.MySQLError` too).
- **(c) Leave it out.** State it under *Out of scope* with a queued step, and correct the two doc sentences so
  they do not claim "every route". KLA should choose this knowingly: the outage mode stays broken until that
  step.

If Q1's optional check is run, add one action to it: reload the page while the database is down. That is where
this shows.

### BR1-02 (minor) — Test 3 does not check the rule it is named for

**The problem.** § 1 Rules: "The server rolls back an uncommitted transaction when its connection drops, so
nothing is half-written. Test 3 checks this." In test 3 the wrapper kills the connection **before** it calls
the real `insert_row`. The INSERT never reaches the server, so "no `sites` row with that code" is true whatever
the server does with an open transaction.

**Why it matters.** The rule is the reason `transaction()` stays unchanged. A test that cannot fail does not
support it.

**Options.**
- **(a) Write first, then lose the connection (recommended).** The wrapper calls the real `insert_row` (the row
  is in the open transaction), then `kill_request()`, then runs one more statement on the same cursor
  (`cur.execute("SELECT 1")`). That statement raises the 2013 inside the transaction, the rollback raises the
  `InterfaceError`, and the answer is the 503 through the new handler. "No `sites` row" is then a real check.
  The extra statement is needed: without it the loss shows at `conn.commit()`, as a 2013, which is a 503 today
  and does not use this step's path.
- (b) Keep the test as it is and take "Test 3 checks this" out of the rule. The rule then rests on MariaDB's
  documented behaviour only.

### BR1-03 (minor) — The fail-closed rule has no test; tests 3 and 4 read no permission from the database

**The problem.** § 1 Rules: "A request that loses its connection during authentication or the permission read
also gets the 503, never a grant." No test in § 5 exercises a permission read on a lost connection. Tests 3 and
4 use `admin`, which is `role_client("it_admin")` (the uncommitted docstring in `conftest.py` says so): its
`masters:edit` and `masters:read` come from the token, with no query. Test 5's engineer has a fixed wildcard
membership from the harness.

**Why it matters.** This is the security rule of the step (settings, *Self-check* item 3; ISO 27001 A.5.15). A
later change that catches the error in the permission path would not turn any test red.

**Options.**
- **(a) One test beside `test_auth.py::TestDatabaseDown::test_a_check_that_needs_memberships_is_503`
  (recommended):** the same request (`GET /api/masters/sites` with a `maintenance_team` Bearer token, whose
  memberships come from the database), after a warm-up request and `lost_connection.server_down()`. Expect
  `(503, {"error": DB_TEXT})`.
- (b) State in § 1 that the rule is not tested, and why.

### BR1-04 (minor) — Q2 names one of two log lines that print `(0, '')` through an outage

**The problem.** Q2 asks whether `access_control.internal_networks` (`access_control.py:118`) should use
`describe_error`. The access-log write has the same text one screen below: `_record` logs "Access log: could
not write (%s); writes paused for %d s" with `%s` of the exception (`access_control.py:235`). In case C/D
`_insert` gets a dead pooled connection too, so this line also prints `(0, '')`.

**Why it matters.** These two lines repeat every 30 s per process while the database is down
(`DB_BACKOFF_SECONDS`). § 2 gives ISO 27001 A.8.15 as the reason for the step: a log line must name the fault.
KLA cannot answer Q2 well when it shows half of the case.

**Options.**
- **(a) Include both lines (recommended):** `describe_error(exc)` in the two calls. `access_control` already
  imports from `local_db`, and `describe_error` returns `str(exc)` for any other exception, so the lines read
  as today for every other fault. No behaviour changes. One file more (`access_control.py`).
- (b) Leave both out, and name both in *Out of scope*.

Either way, Q2 should name both lines.

## Nits

- **BR1-05** (nit) § 0, § 5: `api.js:45` is the fallback for a body that is not JSON (`notJsonBody`). The body's
  `error` is read in `throwIfFailed`. Cite that function by name in both places.
- **BR1-06** (nit) § 1.2: say that the context's description follows today's rule (two arguments give
  `"<message> (error <code>)"`, anything else `str(exc)`), so a one-argument `MySQLError` in `__context__` is
  not left to the coder.
- **BR1-07** (nit) § 3, fixture step 5: say what the kill does with no id (return at once). `WHERE ID IN ()` is
  a syntax error, and `server_down()` can be called when every recorded connection is closed.
- **BR1-08** (nit) § 3, fixture step 3: add that `server_down()` also kills a dedicated connection a test or
  another fixture opened after `lost_connection` was set up (the wrapper records every `pymysql.connect`). The
  fixture's docstring should say it.
- **BR1-09** (nit) § 4 D6: "A test of a lost connection kills it for real … rather than raising a stubbed
  exception" contradicts test 7 and the four stub tests § 5 keeps. Write: "A test of *which error arrives* uses
  the `lost_connection` fixture; a test of what a handler does with a given error may raise it." Also name
  `app._db_unavailable`: the `DBUnavailable` handler is not in `api_common.register_error_handlers`.
- **BR1-10** (nit) § 5: list the tests in number order (test 5 comes after 6 and 7), or renumber.
- **BR1-11** (nit) § 6 Q1: "the probe already showed the same exceptions" is not exact. The probes killed one
  connection and refused the reconnect; neither stopped the server. The claim still holds by the code: PyMySQL
  turns MariaDB's shutdown packet into the same 2013 and closes the socket (`connections.py`, `_read_packet`,
  "MariaDB sends error packet with seqno==0 when shutdown"). Give that as the reason.

## Checked and found consistent

- **The four cases of § 0.** Read in DBUtils 3.2.0 and PyMySQL 1.2.3 (`backend/uv.lock`), and seen in the
  probe log: `tough_method` re-raises the 2013 inside a transaction when the reopen fails; `rollback` re-raises
  PyMySQL's `InterfaceError`; `_ping_check` swallows the failed ping and the failed reopen; `PooledDB.connection`
  hands out the connection without reading the ping's result.
- **`InterfaceError` is raised in one place** (`connections.py:875`). Request code uses only pooled
  connections (`g.db`, the access log's `_insert`), where use after close raises DBUtils' own class. So D2's
  "never a fault in Yantra's code" holds for what reaches the handler today.
- **Every `file:line` in the brief** shows the text the brief says (facts file, *Cited lines*, and my reading).
- **Who else catches these errors.** `get_db` (`OperationalError` at checkout only), `internal_networks`
  (`MySQLError`: falls back, by design), the three `connection_lost` callers, the worker. None but `auth_me`
  (BR1-01) depends on `DBUnavailable` for a dead connection.
- **Existing tests.** No test asserts the old log text or a 500 for an `InterfaceError`. The five tests the
  brief lists stay green: the stubbed `InterfaceError(0, "")` in `TestSettle` has no context, so it logs
  `CONNECTION_CLOSED_TEXT` and still answers 503.
- **The tests fail first as the brief says.** An `InterfaceError` reaches `_unexpected_error` today (500), also
  with `TESTING` on, because the `Exception` handler is registered.
- **The fixture.** The swap must come before the pool is built (`steady_db.py:205`). The kill touches only this
  process's connection ids, so parallel workers are safe. One user owns all test connections, so `KILL` and
  `PROCESSLIST` need no extra grant. Teardown order is right: the fixture's own teardown runs before
  `monkeypatch` restores the pool. Three verbs for five tests is not too much.
- **Test 4 with IT admin.** The network list is cached by the first GET, the second GET's first statement is the
  route's, and the access-log hook's own failure is caught. The 503 and the 200 after `server_back()` follow.
- **Test 5.** The wrapper on `pm_jobs.settle_plan_job` is reached through `settle_one`'s transaction on `g.db`;
  the loop stops at the first plan; `app._db_unavailable` then logs the new `describe_error` text.
- **The access log** records a 500 and a 503 alike (`classify_outcome`: `ok`), so nothing changes there.
- **The screens.** No frontend change is needed. The Readings sheet now stops at the first row. *PM template*
  now says "The template may be saved. Reload the page to see it." also when nothing was saved; the text says
  "may", so it stays true.
- **Standards.** CLAUDE-COMMON *Idle connections* is quoted correctly. RFC 9110 § 15.6.1 (500: an unexpected
  condition) and § 15.6.4 (503: cannot handle the request now, likely to recover) are the right sections. ISO
  27001:2022 A.8.15 (keep logs that record faults in a usable form) fits the `describe_error` change. The
  maintenance standards are not touched.
- **Plan and architecture.** `docs/Plan.MD` holds no rule on a database outage, so nothing contradicts it. No
  *Architecture* entry exists in the settings, as the brief says.
- **Structure.** The rule stays in one place per layer: `local_db` (what a loss is, how to describe it),
  `api_common` (the answer). No new module, flag or abstraction.

## Feedback

- hindrance: the facts file does not look up `DBUnavailable`, though the brief names it in backticks on six lines;
  it appears only inside cited lines (`scratch/brief-facts-S105.md`, *Code names*). The finding that matters
  (BR1-01) came from a grep for who catches it.
- idea: for an exception class a brief cites, the facts run could list the `except` sites of that class and of
  its parents (`git grep -n "except.*<Name>"`). A brief that remaps an exception is judged by who catches it.
- rule: the spawn prompt's general notes say "Do NOT Write report/summary/findings/analysis .md files", and the
  agent file says to write `2-brief-review-rN.md`. The agent file won, but the two lines contradict each other.
