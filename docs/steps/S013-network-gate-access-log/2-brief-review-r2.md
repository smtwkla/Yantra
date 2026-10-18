```
Step: S013 — Network gate, access log and job queue
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 17-10-2026
```

# S013 — Brief review, round 2

**Verdict: ready for the user's approval — no `blocker` or `major` finding is
open.** Every round-1 finding marked `Accepted` is reflected in the brief text
(checked section by section, § Earlier rounds below), and the revisions hold
together: the `TEST_USER_FACTORY` move works against `conftest.py`,
`auth_utils.py` and the existing tests as they are; the DB-down rules are
consistent with `app.py`, `auth_utils.py` and `db_helpers.py`; the worker's
connection, lock and `ensure_schema()` loop are sound. Four `minor` findings
remain, all gaps the coder would otherwise fill alone: the access-log hook's
behaviour during an outage *after* startup (BR2-01, the one that matters most —
`ensure_schema()` is sticky, so the accepted rule does not cover that case), the
claim/handler transaction boundary (BR2-02), the `db_down` fixture's reach
(BR2-03) and where the `auth_failed` detail comes from (BR2-04). Five nits.

Reviewed against: the brief as revised; `2-brief-review-r1.md`; `docs/Plan.MD`
§ 1, § 3, § 5, § 8; `docs/Maintenance-Philosophy.md`; `docs/Plant-Facts.md`;
`.claude/SMTW-WebApp-Base.md` § Internet Exposure, § DB Connection (timezone),
§ Local DB Migration (singleton lock), § Business Settings, § Background Worker /
Job Queue, § Testing; `.claude/CLAUDE-COMMON.md`; `.claude/CLAUDE.md`; the
working-tree code: `backend/app.py`, `auth_utils.py`, `access_core.py`,
`config_rbac.py`, `settings.py`, `local_db.py`, `db_helpers.py`,
`api_common.py`, `config.py`, `worker.py`, `tests/conftest.py`,
`tests/test_auth.py`, `tests/test_rbac.py`, `tests/test_settings_api.py`,
`tests/test_migration_v9.py`, `tests/test_masters_api.py` (the `db_down` use at
line 685); `tooling/build/nginx.conf`, `gunicorn.conf.py`,
`Dockerfile.backend`, `tooling/dev/docker-compose.dev.yml`,
`tooling/run-backend-tests.bat`; `frontend/src/api.js`, `stores/auth.js`,
`App.vue`, `views/SettingsView.vue`; Flask's `testing.py` and Werkzeug's
`test.py` (environ precedence); PyMySQL `connections.py` (`ping`/`connect`);
`docs/Keycloak.md`; S011 review r1 (BR1-01). One read-only `EXPLAIN` was run on
the dev MariaDB 11.4 container for BR2-07.

---

## Earlier rounds — Accepted answers verified in the text

| Finding | Where it now stands in the brief |
|---|---|
| BR1-01 | § 5.2 fallbacks (unreadable → defaults; `DBUnavailable` → cache, else `DEFAULT_INTERNAL_NETWORKS`, logged once per 30 s); § 5.3 "internal passes before any database read"; § 5.4 `ensure_schema()` first, sighting cached only after a successful insert; § 8 API › DB down. Present. See BR2-01 for the one case the rule still misses. |
| BR1-02 | § 3 `auth_utils.py` (factory inside `require_auth`), § 3 Tests (`test_client_class` with a default internal `X-Real-IP`, `test_role_matrix` updated), § 8 Gate (the hook-order test on `/api/masters/sites`), § 7 row. Present. |
| BR1-03 | § 4 (defaults `CURRENT_TIMESTAMP`, `NOW()` in SQL, `now_ist()` for the pure scheduler, worker on `get_local_db()`), § 7 row. Present. |
| BR1-04 | § 2: A.8.2 leads, A.8.20/A.8.22 supporting, A.8.15 "protected, append-only", CERT-In 180-day floor, A.8.16. Present. |
| BR1-05 | § 1.4, § 3 Frontend (no new route or guard; `networkDenied` flag; card in `App.vue`), § 7 row. Present. See BR2-08 for the template precedence. |
| BR1-06 | § 5.4 Outcome and detail (`require_perm_at` → `key@site:<id>`; business 403 → first 100 characters), § 5.3 and § 5.4 state the two Flask facts. Present. |
| BR1-07 | § 5.5 Connection and lock, Schema, SIGTERM; `LOCK_WORKER` in § 3 `local_db.py`. Present. See BR2-02 for the transaction boundary. |
| BR1-08 | § 5.6 pure `next_run`, `overdue`, badge and red failed count; § 1.9; § 8 Pure. Present. See BR2-09 for the two definitions of overdue. |
| BR1-09 | § 5.1 `is_internal` (IPv4-mapped unwrapped; loopback internal in code), § 8 Pure. Present. |
| BR1-10 | § 3 Tests (`_TABLES`, cache-clearing fixture, `require_network(dev_bypass=…)` tested directly). Present. |
| BR1-11 | § 5.4 `per_page`, `to` inclusive, `user` contains; § 4 truncation; § 5.2 PUT text, `strict=False`, change logged, guard message; § 5.6 1093 hint; § 3 `company_settings.py`. Present. See BR2-07 for the 1093 reason. |
| BR1-12 | § 3 Docs (Plan.MD § 3 row, CLAUDE.md departure, Keycloak.md `sid`), § 3 Tests (`TestPolicyStructure`). Present. |

---

## Minor

### BR2-01 — `minor` — The access-log hook still pays a connect timeout per request during an outage *after* startup, because `ensure_schema()` is sticky

**Problem.** § 5.4 says the hook "first asks `ensure_schema()` (answered from
memory for 30 s after a failed attempt) … It never opens a connection to a
server known to be down, so no request waits for a connect timeout." That holds
only while the schema has *never* come up. `local_db.ensure_schema` sets
`_schema_ready = True` once and returns `None` from then on (lines 455–457); it
is never reset. So in the common outage — the database goes away after the
process started — `ensure_schema()` says "fine", the hook calls
`get_pooled_db()`, the pool's checkout ping fails, DBUtils tries to reconnect,
and the hook waits the 5 s `connect_timeout` before its try/except catches the
error. Every request in that outage then costs the route's own 5 s (its
`get_db()` does the same) **plus** the hook's 5 s: `/api/auth/me` for IT admin
answers after ~10 s instead of ~5 s, and Settings › Database's `db-status`
(3 s connect) after ~8 s. Round 1 framed `get_db()`'s protection too broadly;
the brief took that framing over.

The brief's DB-down test will not catch this: the `db_down` fixture patches
`ensure_schema` to *return an error*, which is the never-up case, not the
sticky-ready case.

**Why it matters.** This is the acceptance of BR1-01 ("the access-log hook does
not slow or break the response"), and the person waiting is the IT admin trying
to read Settings › Database during the outage.

**Options.**
1. Give the hook its own back-off, on the `ensure_schema` model: a module-level
   "down until" moment; any connect or insert failure sets it to now +
   `_RETRY_INTERVAL_S` (30 s) and logs once; while it holds, the hook skips the
   write without touching the pool. The sighting stays uncached (§ 5.4 already
   says so), so the first request after the back-off writes it. Cost of an
   outage after startup: one connect timeout per process per 30 s, not one per
   request. Add the test: with `get_pooled_db` patched to raise, the second
   request within 30 s makes no connect attempt (a counter on the patch).
   **Recommended.**
2. Make the hook's connect timeout short (1 s) instead. Still one wait per
   request, and a second connect-timeout constant to keep. Not recommended.

### BR2-02 — `minor` — Claim and handler in one transaction would roll back `attempts + 1` on failure and retry for ever

**Problem.** § 5.5 says the claim sets `status = 'running'`, `attempts + 1`,
`locked_until`; then "a handler runs in one transaction and commits nothing
itself; the worker commits with `mark_done`. On an exception: rollback, store
`last_error`; `attempts < max_attempts` → `pending` again … else `failed`." It
does not say whether the claim's `UPDATE` is committed before the handler
starts. If the coder puts claim and handler in the same transaction (the
`FOR UPDATE SKIP LOCKED` read invites it), the rollback on failure also undoes
`attempts + 1`, `mark_failed` then compares the *old* `attempts` with
`max_attempts`, and a task that always fails is retried for ever at five-minute
steps — never reaching `failed`, never counted on the Background tasks card.
The brief's own test ("a failing handler retries with backoff and ends
`failed`") would fail, but only after the coder has guessed wrong.

**Options.**
1. State the boundary: **the claim is its own short transaction** (`begin`,
   `SELECT … FOR UPDATE SKIP LOCKED`, `UPDATE … running, attempts + 1,
   locked_until`, `commit`); **the handler's work is a second transaction**,
   committed by `mark_done` or rolled back on an exception; `mark_failed` is
   then a plain autocommit `UPDATE` on the committed `attempts`. The connection
   is `autocommit=True` (`local_db._connect_kwargs`), so each transaction is an
   explicit `conn.begin()` — `db_helpers.transaction(conn)` fits. The purge's
   batches are each their own transaction (§ 5.5 already says so). The
   `locked_until` reclaim then also works: a crash after the claim's commit
   leaves a `running` row that `requeue_stale` finds. **Recommended.**
2. One transaction, with `mark_failed` re-applying `attempts + 1` itself.
   Works, but `attempts` is then counted in two places. Not recommended.

### BR2-03 — `minor` — The `db_down` fixture reaches `db_helpers.ensure_schema` only; the hook's own reference must be patched too, or the DB-down hook test is vacuous

**Problem.** `tests/test_auth.py` `db_down` does
`monkeypatch.setattr(db_helpers, "ensure_schema", lambda _config: "Can't
connect (test)")`. That reaches `get_db()` (routes, `current_memberships()`,
the gate's membership fallback) and nothing else. The hook is in
`access_control.py` and calls `ensure_schema()` through whatever name it
imports — `from local_db import ensure_schema` is the natural one, and the
fixture does not touch it. Under `db_down` the hook would then see a ready
schema (the test DB is up) and write normally; the tests in § 8 API › DB down
("the access-log hook does not slow or break the response, and the sighting is
written after the DB is back") would pass without the hook ever being in the
DB-down path. The same applies to the ranges loader's `DBUnavailable` fallback
(§ 5.2) if it reads through its own connection rather than `get_db()`.

**Options.**
1. Say in § 3 Tests that `db_down` is extended to the hook's and the ranges
   loader's references (patch the function where each module looks it up —
   `access_control.ensure_schema` / `access_control.get_pooled_db` — or have
   both read the database through `db_helpers.get_db()`'s path so one patch
   covers all), and that the "written after the DB is back" test ends the
   fixture mid-test (`monkeypatch.undo()`) before the second request.
   **Recommended.** With BR2-01 option 1 the fixture also resets the hook's
   back-off moment.
2. Leave to the coder. The test would exist and pass; it just would not test
   the hook.

### BR2-04 — `minor` — `auth_failed` "detail: the reason" — `validate_keycloak_token` returns `None` with no reason to record

**Problem.** § 5.4 says `require_auth` marks `auth_failed` with "detail: the
reason". `validate_keycloak_token` (auth_utils.py 104–164) returns `None` from
five places — no Bearer header, signature or expiry failure (after the JWKS
retry), wrong `azp`, no recognised role — and logs the reason each time, but
hands nothing back; `require_auth` sees only `None`. The coder must either
change the function's contract (`test_auth._validate` asserts `is None` in six
tests) or set the detail inside the validator. The detail is also part of the
sighting key, so it must be a short fixed string, not the JWT library's message
(which can carry the token's `exp`, making every probe a new sighting).

**Options.**
1. The validator sets `g.access_detail` to one of a few fixed codes at each
   return — `no_token`, `invalid_token`, `wrong_client`, `no_role` — and keeps
   returning `None`; `require_auth` sets `g.access_outcome = "auth_failed"`.
   The `_validate` tests run in a `test_request_context`, so `g` is there;
   they are unchanged. State the four codes in § 5.4. **Recommended.**
2. `require_auth` records `detail = "token"` only. Simpler, but A.8.16 is
   served better by "expired token from this address" vs "no role".

---

## Nit

### BR2-05 — `nit` — Test harness details to pin down

- **Factory call shape.** `require_auth` calls `TEST_USER_FACTORY(role,
  username)`. Today the default username (`test_<role>`) and the `X-Test-User`
  header are conftest's business (`_inject_test_user`, line 67). Say that
  `require_auth` passes `request.headers.get("X-Test-User")` (possibly `None`)
  and the factory applies the default, so the harness convention stays in
  conftest; and that `TESTING` + `X-Test-Role` with **no factory configured**
  is a 401, not a crash and not a pass (fail closed).
- **The "missing `X-Real-IP` → external" API test** cannot be produced by
  leaving the header out: Flask's `FlaskClient._copy_environ` merges
  `{**self.environ_base, **other}`, so a per-call `environ_base={}` keeps the
  default. Either the client subclass takes a kwarg (`real_ip=None` → no
  default header) or the test sends `X-Real-IP: ""` (Werkzeug passes an empty
  header through; "missing or unparsable → external" covers it). Say which; the
  kwarg is the explicit one. Werkzeug applies `headers` after `environ_base`
  (`EnvironBuilder.get_environ`), so the *override* in gate tests works as
  written.
- **The `remote_addr` dev fallback (§ 5.1) must not fire in tests.** The test
  client's `REMOTE_ADDR` is `127.0.0.1` → loopback → internal, which would
  turn the "missing → external" test green for the wrong reason. Tests are run
  from PyCharm or `tooling/run-backend-tests.bat` with whatever the shell has;
  conftest pops `DEV_AUTH_BYPASS` but not `FLASK_DEBUG`. Either conftest pops
  `FLASK_DEBUG` the same way, or the address reader reads `config.IS_DEV` at
  call time (not `from config import IS_DEV`) so a test can monkeypatch it.

### BR2-06 — `nit` — "Registered before the other `after_request` hooks": `CORS(app)` registers one at app.py line 37

`flask_cors.CORS(app, …)` adds its `after_request` when it is called, before
`require_auth` is registered. For the access-log hook to be registered first
(and so run last) it must be added right after `app = Flask(__name__)`, above
`CORS(app)` — worth a line in § 3, or drop the "sees the final status"
rationale, since neither `flask_cors` nor `_log_slow_request` changes the
status and the order is then immaterial. Also note `access_control` is imported
in `app.py` after `app` exists (it needs no `app` at import, but the
registration does).

### BR2-07 — `nit` — The "error 1093" reason for the derived table is MySQL's, not MariaDB's; keep the derived table for the plan it gets

Checked on the dev container (MariaDB 11.4.13): `EXPLAIN DELETE FROM t WHERE k
NOT IN (SELECT MAX(k) FROM t GROUP BY …)` is **accepted** — MariaDB has allowed
the target table in a `DELETE` subquery since 10.3.1 (the KB page "DELETE ›
Same source and target table"). The hint was round 1's (BR1-11) and the brief
took it as stated; the reason should be corrected. The derived table is still
the right choice: the direct form plans as a `DEPENDENT SUBQUERY` (re-run per
row), the derived form materialises the `MAX(id)` list once. Say that instead.

### BR2-08 — `nit` — Frontend: which card wins

`App.vue` renders the shell on `v-if="authenticated"` first, the `authError`
card second. Mid-session `authenticated` is `true`, so the `networkDenied`
card must take precedence over the shell (`v-if="networkDenied"` first). On
the first call `loadProfile` also sets `authError` ("Could not load your
profile: …") for the same 403; harmless once the `networkDenied` card is first,
but say so, or have `loadProfile` skip `authError` when `networkDenied` is set.
Also: `api.js` importing `networkDenied` from `stores/auth.js` closes an import
cycle that already exists (`stores/auth` → `api`); fine at runtime since both
are used inside functions — a one-line comment saves the next reader a worry.

### BR2-09 — `nit` — Small wording and contract points

- **Overdue** is defined twice in § 5.6: `overdue = next_run < now` and "(more
  than one poll interval late)". Pick one — the plain `next_run < now` is fine
  (the five-second window after 02:30 is invisible in practice).
- **How the purge sees the stop flag.** `task_handlers` cannot import
  `worker._running` (worker imports the handlers). Pass a `should_stop`
  callable into the handler (`handler(payload, conn, should_stop)`) or keep the
  flag in `task_queue.py`. Say which.
- **First deploy after 02:30:** `due_tasks` will enqueue the purge at once
  (today's time passed, nothing enqueued) — correct and useful; say it, so the
  first day's "purge_access_log done" line at an odd hour is expected and the
  release manual check reads right.
- **`GET_LOCK` each loop doubles as the reconnect check:** MariaDB returns 1 at
  once when the same session already holds the lock, and takes it afresh after
  `ping(reconnect=True)` opened a new session. One sentence in § 5.5 saves the
  coder adding an `IS_USED_LOCK` check.

---

## Checked and found consistent

- **`TEST_USER_FACTORY` against the suite as it is.** `test_auth`'s
  `TestValidateToken` and `test_rbac`'s `ctx` fixture use
  `test_request_context` on a bare app, untouched by `require_auth`.
  `TestDatabaseDown.test_it_admin_gets_token_permissions` passes through the
  client's default internal address and § 5.3's "internal decides before any
  DB read". `test_masters_api.py:685` (`db_down` with a `role_client`) and
  `TestLoginOnly` are unaffected for the same reason. `require_perm` setting
  `g.access_outcome` works in the `ctx` fixture (a request context is active).
  Conftest can set `test_client_class` and the factory at import, before any
  `app.test_client()`.
- **Gate DB-down paths.** External `it_admin` is refused from the token alone;
  external `maintenance_team` → `current_memberships()` → `get_db()` →
  `DBUnavailable` → token roles only → passes; its routes answer 503,
  `/api/auth/me` 200 with `db_unavailable` (app.py 129–135). Internal anything
  → no query. Matches § 5.3.
- **Worker connection and lock.** PyMySQL `ping(reconnect=True)` calls
  `connect()`, which re-runs `init_command` (connections.py 724–726), so the
  IST session setting survives a reconnect. `ensure_schema()` takes
  `LOCK_MIGRATIONS` on its own short connection; `LOCK_WORKER` is a different
  name on the dedicated connection; MariaDB allows several named locks per
  session. `requeue_stale` on the same connection is right for one worker.
- **`after_request` facts.** Flask's `full_dispatch_request` finalises a
  response returned by a `before_request` hook through `process_response`, and
  `handle_exception` finalises the 500 with `from_error_handler=True`; so
  `auth_failed`, `denied_network`, 503 and 500 all reach the hook.
  `teardown_appcontext` (`close_db`) runs after `after_request`, so the hook's
  second pooled connection beside `g.db` is correct; the pool of 10 covers
  3 sync workers × 2.
- **Sighting cache and the hook's own connection** make a rolled-back request
  still log (§ 5.4), and `auth_failed` rows key on `(outcome, None, ip,
  detail)` — bounded under scanning, as in round 1.
- **Migration v10** idempotent; `test_migration_v10` follows the
  `test_migration_v9` pattern (remove the version row, `init_db` twice).
- **Docs listed in § 3 are the right ones:** Plan.MD § 1 still says "all
  roles get `access:wan`" (line 27) and § 3's matrix has no `access_log:view`
  row; `docs/Keycloak.md` does not mention `sid` today.
- **Permissions** (§ 5.7, § 6) match `config_rbac.py`; `access_log:view`
  global is right for a cross-site record; the Settings nav needs
  `settings:read`, which the manager has.
- **Default ranges vs the proxy.** The front-proxy range `10.24.0.0/23` in
  `nginx.conf` matches the base; the RFC 1918 defaults contain it, so manual
  check 3 (real, varied addresses) remains the check that catches the
  proxy-IP trap.
- **Standards** (§ 2) unchanged from round 1 and correctly cited; the
  maintenance standards (ISO 14224, EN 13306, ISO 55000, SMRP, TPM) have no
  bearing on this step.
- **Track: full** and the four **important** manual checks are right; the
  stop-and-restart and mid-session checks are rightly plain.
- **Open questions** 1 (admin from outside) and 2 (VPN) are the user's to
  answer at approval; the brief's recommendation on 1 stands.
