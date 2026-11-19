```
Step: S105 — A lost database connection answers 503, not 500
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 15-11-2026
```

Reviewed against: 6696283 + uncommitted non-step edit (`backend/tests/conftest.py`: the `admin` fixture's docstring)

**Verdict: no blocker or major finding is open.** BR1-01 (major) is closed: `/api/auth/me` keeps its designed
200 with `db_unavailable: true` on a lost connection (§ 1.3, D7, tests 9 and 11), and the design holds against
the code. All eleven round-1 answers are in the brief's text, not only in the Review log. This round adds two
minor findings and four nits; none changes the design KLA decided.

What I re-read (the text changed since `scratch/S105-brief-r1.md`, and the code it now relies on): § 0 (the
`throwIfFailed` cite, the "A page load" bullet); § 1 items 1–6, the "what the user sees after" paragraph, Rules,
Out of scope; § 2 (A.8.15, A.5.15); § 3 (the table, the file count, fixture steps 3 and 5); § 4 D1, D2, D4, D6,
D7; § 5 all; § 6 Q1, Q2; the Review log. Code read for it: `app.auth_me`, `auth_utils` (`require_auth`,
`current_memberships`, `current_person_id`, `has_perm`, `logged_role`), `access_control` (the gate,
`internal_networks`, `_record`, `_insert`), `local_db.connection_lost` and `describe_error`,
`db_helpers.transaction`, DBUtils' `tough_method` and `_reset`, `test_auth.py::TestDatabaseDown`, the
`conftest.py` fixtures the new tests use, `NoAccessView.vue`, `App.vue`, `stores/auth.js`.

The facts file was given and matches the draft. The two commits since round 1's baseline (9cde498 → 6696283)
touch none of the brief's code files; in `.claude/CLAUDE.md` the *DB may not exist* bullet and § SMTW-Review
are as the brief assumes. One read-only probe of my own: `scratch/s105_br2_probe.py` (BR2-01).

## Findings

### BR2-01 (minor) — The `OperationalError` half of the `/api/auth/me` rule has no test

**The problem.** § 1.3 says a loss is "an `InterfaceError`, or an `OperationalError` with a lost code", and
both get the degraded 200. Test 9 loses the connection before the request (case C), so it sends only the
`InterfaceError`. Test 11 sends a code that is not a loss (1213). No test sends a lost code through `auth_me`.

That half is a real change of behaviour, and it is reachable. Today a 2013 raised in `auth_me` passes
`except DBUnavailable` and is the 503 of `_operational_error`; after the step it is the 200. The probe shows
when it arrives: `auth_me` uses no transaction, and outside a transaction a connection that is alive at
checkout and lost between two statements, with the server down, raises
`OperationalError(2013, 'Lost connection to MySQL server during query')` with no `__context__`. DBUtils retries
on a new cursor, fails to reopen, and re-raises the first error (`steady_db.py:755-828`).
`connection_lost(None, exc)` is `True` for it.

**Why it matters.** An `auth_me` that catches `(DBUnavailable, pymysql.err.InterfaceError)` passes all eleven
tests and leaves the full-page error card for this case. D7 is KLA's decision and covers both errors.

**Options.**
- **(a) Make test 11 two stubbed cases (recommended).** The same monkeypatch of `app.current_memberships`:
  `OperationalError(2013, "Lost connection to MySQL server during query")` gives 200 with `db_unavailable`
  true, `permissions == auth_utils.compute_permissions(["it_admin"])`, and an `api_common` record containing
  `GET /api/auth/me` and `(error 2013)`; 1213 gives the 500 as now. No fixture is needed. The 2013 case fails
  on today's code (503), so it joins the list of tests written first.
- (b) Leave it, and say in § 1.3 that only the `InterfaceError` half is tested.

### BR2-02 (minor) — The outage screen that floor users now get offers no way to try again

**The problem.** After D7, a page load in the usual outage puts every person whose rights come from the
database (operators, technicians, engineers, managers) on `NoAccessView.vue`'s database branch: an icon and
"The database is unavailable — try again shortly." The screen has no button. `dbUnavailable` is set once in
`loadProfile` (`stores/auth.js`) and nothing reads `/api/auth/me` again, so the screen stays after the
database is back, until the page is reloaded. Yantra is installed as a standalone PWA
(`manifest.webmanifest`: `"display": "standalone"`), which has no reload button: on Android the user must
know pull-to-refresh, on an iPhone the user must close the app and open it again.

The text is also a second wording for one condition. Every other screen shows "Yantra can't reach its
database. Try again in a few minutes." in the same outage (`DB_LOST_TEXT`; S064 UX-13 made the two 503s one
text).

**Why it matters.** This is not a regression: today the same person gets the error card with "Something went
wrong — try again" and only *Sign out*. But § 1 ("What the user sees after the step") now makes this screen
the designed outage screen for the floor, and "try again" names an action the screen does not offer
(settings, *Use on the floor*: obvious what to do next; wording a low-literacy user would follow). The screen
dates from S011, when only the rare `DBUnavailable` case reached it.

**Options.** This is KLA's call.
- **(a) Keep S105 backend-only (recommended).** Name the gap under *Out of scope*, and ask the orchestrator
  to queue a small step: a *Try again* button on the database branch that reloads the page, and the 503's
  text there. S105 stays without a frontend change and without browser runs.
- (b) Add it to this step: the button (`window.location.reload()`) and `DB_LOST_TEXT`'s wording in
  `NoAccessView.vue`, plus one browser test that fulfils `/api/auth/me` with `db_unavailable: true` through
  `page.route` (with `serviceWorkers: "block"`). The step then has a frontend file and targeted browser runs,
  and "No frontend change" goes from § 1 and § 5.
- (c) Leave it unsaid. The screen works as it did for `DBUnavailable`.

## Nits

- **BR2-03** (nit) § 1.4: "for one with two `args` and no closed socket, the text is the same as today" is
  wrong. Today `%s` prints the tuple, `(2003, "Can't connect …")`; `describe_error` gives
  `Can't connect … (error 2003)`, which test 7 already expects. Write: a `MySQLError` with two arguments
  changes to the `<message> (error <code>)` form of every other line; only an exception that is not a
  `MySQLError` reads as today. Round 1's BR1-04 made the same inexact statement; no test asserts the old form.
- **BR2-04** (nit) § 1.3: "(as today: `get_db` or `ensure_schema` has logged its cause)" is not exact.
  `get_db` logs nothing; its `DBUnavailable` from a refused checkout is logged only by `app._db_unavailable`,
  which `auth_me`'s clause comes before. Write: "`DBUnavailable` is not logged here, as today."
- **BR2-05** (nit) § 3, the `local_db.py` row: `connection_lost`'s docstring lists who shares it ("Shared by
  the worker and pm_generate's per-plan loop … and a template save's loop"). Add `app.auth_me` (S105) to that
  list, docstring only; "`connection_lost` is unchanged" in § 1 Rules stays true for the code.
- **BR2-06** (nit) § 5 Runs: add `tests/test_access_control_api.py` to the while-coding command and to the
  "stay green" list. Its `TestDatabaseDown` runs `internal_networks`' changed warning (four tests, none
  asserts the text).

## Checked and found consistent

- **Round-1 answers in the text.** BR1-01: § 0, § 1.3, § 3 (`app.py`, the `.claude/CLAUDE.md` sentence), D6,
  D7, tests 9 and 11, Q1's reload. BR1-02: test 3 writes, kills, then runs `SELECT 1` on the same cursor.
  BR1-03: test 10, § 1 Rules, § 2 A.5.15. BR1-04: § 1.4, § 3, test 7, Q2. BR1-05 to BR1-11: each is in the
  section the Review log names.
- **§ 1.3 against `auth_me`.** Every database read of the route is inside the `try`. `client_network()`
  before it needs no catch: `internal_networks` catches `(DBUnavailable, pymysql.MySQLError)` itself. The
  clause re-raises what `connection_lost(None, exc)` does not call a loss, so a deadlock, a lock wait, an
  `IntegrityError` or an SQL fault answers as today. The degraded body takes `user["permissions"]` and
  `display_role(user["roles"], [])`: memberships already cached on `g` are not used, so the answer grants the
  token's keys only. `app.py` importing `pymysql`, `connection_lost` and `log_connection_lost` adds no new
  dependency direction.
- **D7's claim.** `auth_me` is the only `except DBUnavailable` that lacks `pymysql.MySQLError`
  (`access_control.py:116` and `local_db.py:1791` have both). No other route degrades on a database error.
- **IT admin reaches *Settings › Database*.** `settings:read` and `masters:read` come from the `it_admin`
  token (`has_perm` makes no query), and `db_status` uses its own connection and always answers 200.
- **Test 3.** `transaction()` commits outside its `try`, so a loss seen only at `commit()` is a 2013 and
  today's 503; step 3 of the wrapper is what sends the request through the rollback and the new handler.
- **Test 7.** The harness `it_admin` passes the gate from the internal test address. With the ranges cache
  cleared, `internal_networks` reads through a dead pooled connection: `InterfaceError(0, "")` with no
  context, so the line reads `Internal networks unreadable (Database connection closed (error 0))`.
  `logged_role` makes no query, so the hook's failure is in `_insert` and logs "could not write", not "could
  not record". `_fresh_access_caches` clears both states after the test.
- **Test 9.** The warm-up caches the ranges (300 s) and the sighting, so IT admin's second request reads the
  database first in `current_memberships`. That error has no context, so the log holds
  `CONNECTION_CLOSED_TEXT`. A `maintenance_team` token has `permissions == []`, as
  `test_login_only_user_gets_nothing` shows. Returning a dead connection to the pool is safe: DBUtils'
  `_reset` swallows the failed rollback.
- **Test 10.** `masters:read` is a wildcard key, but a `maintenance_team` token holds no key, so `has_perm`
  reads the memberships; that read raises the error, which nothing catches. It is the request of
  `test_a_check_that_needs_memberships_is_503`.
- **Test 11.** `auth_me` calls the name `current_memberships` of module `app`, so the monkeypatch reaches it.
  The 1213 goes through the bare `raise` to `_operational_error` and the plain 500. It passes today, and
  fails if the re-raise is left out.
- **Q1's lines.** `connections.py:785-790`, `:823-836`, `:845-849` and `:875` show the text the brief gives.
  With the dev bypass the stub user's memberships are fixed, and the loss shows at `current_person_id`
  inside the same `try`, as § 0 says.
- **Standards.** ISO 27001:2022 A.5.15 (access is given by the rules set for it, and nothing beyond them) is
  cited correctly for the degraded answer and test 10. A.8.15 now covers all the log lines the step changes.
- **Structure.** Eleven files, counted. The rule of what a loss is stays in `local_db`, the log line and the
  503 in `api_common`; `auth_me` only chooses between them. No new module, flag or abstraction. No
  architecture doc is configured.

## Feedback

- hindrance: the round-2 diff (`git diff --no-index -w` of the two brief copies) was 37 KB, so the Bash tool
  stored it in a file and it took a second read; a `--stat` first and the diff per section would have been
  enough.
- rule: the round-2 rule limits the review to the changed text "and what that change touches". It does not
  say whether an unchanged screen that the changed text newly relies on (`NoAccessView.vue`, BR2-02) is in
  scope below `major`. I took it as in scope; one sentence in the agent file would settle it.
- idea: the writer's probes covered a loss inside a transaction and a dead pooled connection, but not a loss
  outside a transaction; BR2-01 needed a third probe (`scratch/s105_br2_probe.py`, 5 minutes). A self-check
  line "for a route the step changes, probe the path that route really takes (with or without
  `transaction()`)" would have shown the 2013 before review.
