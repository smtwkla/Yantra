```
Step: S013 — Network gate, access log and job queue
Doc: impl-report
Author: Coder (Opus)
Date: 18-10-2026
```

# S013 — Implementation report

Built on top of commit 3e338b4 (S012 committed), as migration **v10**.

## 1. What was built

- **Network gate.** IT admin (`INTERNAL_ONLY_ROLES = ("it_admin",)`) is refused with 403
  `{"error", "code": "network_denied", "ip"}` on every API route, `/api/auth/me` included,
  when the request comes from outside the plant's ranges. Every other role works from
  anywhere, the manager included. Admin, public paths, `OPTIONS` and the dev bypass skip
  the gate. The gate reads token roles only and makes no database read.
- **Client address.** The address comes from `X-Real-IP` only. Missing or unparsable counts
  as external. IPv4-mapped IPv6 is unwrapped, and loopback is always internal. In dev the
  socket address is used when the header is missing and `FLASK_DEBUG` is set.
- **Settings › Network.** The internal ranges as CIDR text:
  - read with `settings:read`, edited with `settings:edit`;
  - each entry is checked and host bits are dropped;
  - an empty list is refused;
  - a list that would block the saver's own address is refused, except for admin;
  - the change is logged with the actor and old → new.
  The card also shows "Your address: … — internal/external".
- **Access log.** One `access_log` row per sighting: a session or user first seen from an
  address, or a distinct refusal. The outcome is `ok`, `auth_failed`, `denied_network` or
  `denied_perm`, with a fixed detail. The viewer is in Settings (`access_log:view`, manager
  and IT admin): paginated, newest first, with filters for user, from/to, external only and
  refusals only.
- **Job queue.** The `task_queue` table, `task_queue.py` (enqueue, claim, done/failed,
  stale requeue) and `task_handlers.py`. `worker.py` no longer idles: it drains the queue
  under a singleton lock.
- **Daily scheduler.** `scheduled_tasks.py` has one task, `purge_access_log`, daily at
  02:30 IST. It deletes access-log rows older than 365 days in batches, then done queue rows
  older than 90 days, keeping the last row per type.
- **Settings › Background tasks.** For each scheduled task: last run with its status, next
  run, and the badge "Overdue — is the worker running?". The count of failed tasks shows in
  red when it is above 0.
- **Frontend refusal card.** A full-page card with the message, "The server saw your address
  as …" and Sign out. It shows on the first call and mid-session, because `api.js` sets the
  auth store's `networkDenied` on any `network_denied` response.

## 2. How it works

**Request path** (`app.py`). The `before_request` order is `require_auth` →
`require_network` → the slow-request timer. The access-log `after_request` hook is
registered first, above `CORS(app)`. Flask runs `after_request` hooks in reverse, so this
one runs last and sees the final status, including error-handler and 500 responses.

**Classification** (`network_core.py`, pure). `access_control.client_network()` works out
`(ip, internal)` once per request and keeps it on `g`. The ranges come from
`internal_networks()`:
- a 5-minute cache per process;
- read through the request's `get_db()`;
- on `DBUnavailable` or a MySQL error: the last cached list, else
  `DEFAULT_INTERNAL_NETWORKS` (the RFC 1918 ranges), with a 30-second retry back-off and one
  warning per back-off;
- a stored value that can't be parsed: logged, and the defaults are used.

So an IT admin on the plant network gets past the gate, and `/api/auth/me` and
Settings › Database still answer, while the DB is down.

**Gate** (`access_control.require_network`). Once `g.user` is set, the gate refuses the
request when `gate_refuses(user.roles, internal)` is true, that is when the address is
external and a token role is in `INTERNAL_ONLY_ROLES`. It sets
`g.access_outcome = "denied_network"` and logs a warning naming the user, the roles and the
address.

**Outcome marks** (`auth_utils.py`):
- `validate_keycloak_token` sets `g.access_detail` to `no_token`, `invalid_token`,
  `wrong_client` or `no_role`, and still returns `None`;
- `require_auth` marks `auth_failed`;
- `require_perm` marks `denied_perm` with the key;
- `require_perm_at` marks `denied_perm` with `key@site:<id>`.

`classify_outcome` uses a mark when there is one. Otherwise 401 → `auth_failed`, 403 →
`denied_perm` with the first 100 characters of the message, and anything else → `ok`.
`g.user` gains `session_id`, the token's `sid` claim.

**Access-log hook** (`make_access_log_hook`). Public paths, `OPTIONS` and the dev bypass are
not logged. For everything else the hook builds the key
`(outcome, session_id or username, ip, detail)` and stops if:
- the `SightingCache` has seen the key in the last 10 minutes; or
- the hook's own 30-second back-off is running; or
- `ensure_schema()` reports the DB down.

Otherwise it inserts on its own pooled connection (autocommit), so a rolled-back request
still logs. Text is truncated to the column widths. The key is remembered only after a
successful insert. A failed insert starts the 30-second back-off with one warning. Any
exception in the hook is logged and never reaches the response.

**Test harness.** In TESTING mode with `X-Test-Role`, `require_auth` calls
`app.config["TEST_USER_FACTORY"](role, X-Test-User)`. Without a factory it returns 401. The
conftest:
- sets the factory and drops its own injector;
- makes the test client default to `X-Real-IP: 10.0.0.5`;
- turns off the dev `remote_addr` fallback;
- clears the sighting and range caches around every test;
- empties `access_log` and `task_queue` at session start.

**Queue and worker** (`task_queue.py`, `task_handlers.py`, `worker.py`). Each loop, every
5 seconds:
1. `ensure_schema()`; nothing more until it succeeds.
2. Ping the one dedicated `get_local_db()` connection; if it is dead, open a new one.
3. Confirm the lock with `IS_USED_LOCK(name) = CONNECTION_ID()`, else
   `GET_LOCK(name, 0)`. A new session has a new id, so after a reconnect the lock is taken
   again before any work. "Waiting for the worker lock" is logged at most once a minute.
4. `requeue_stale`.
5. Enqueue due scheduled tasks: `due_tasks` over `MAX(created_at)` per type, with the
   naive IST clock.
6. `run_one()` until nothing is due.

Each task takes three transactions:
1. **Claim** (`FOR UPDATE SKIP LOCKED`, then `running`, `attempts + 1`,
   `locked_until = NOW() + 10 min`), committed on its own.
2. **Handler and `mark_done`**, committed together.
3. **On an exception:** rollback, then `mark_failed` in its own transaction. While
   `attempts < max_attempts` the task goes back to `pending` at `NOW() + 5 min × attempts`;
   otherwise it is `failed`.

SIGTERM sets the stop flag. The loop ends after the current transaction, and the purge
checks `should_stop()` between batches.

**Tasks endpoint.** It uses the database's `NOW()` and returns, per `SCHEDULE` entry, the
latest row's status and time, `next_run` and `overdue` (more than 5 minutes past
`next_run`), plus `failed_count`.

## 3. Files touched

New (backend):
- `backend/company_settings.py`: named constants (retention, sighting window, cache, lock,
  backoff, poll, batch size).
- `backend/network_core.py`: pure core. `parse_networks`, `format_networks`, `parse_ip`,
  `is_internal`, `gate_refuses`, `classify_outcome`, `truncate`, `SightingCache`,
  `DEFAULT_INTERNAL_NETWORKS`.
- `backend/access_control.py`: shell. Client address, range loader and cache, `require_network`, access-log hook.
- `backend/scheduled_tasks.py`: `SCHEDULE` and the pure `due_tasks`, `next_run`, `is_overdue`.
- `backend/task_queue.py`: `enqueue`, `claim_next`, `mark_done`, `mark_failed`, `requeue_stale`, `last_enqueued`.
- `backend/task_handlers.py`: `HANDLERS`, `purge_access_log`, `run_task`, `BadTask`.

Changed (backend):
- `backend/local_db.py`: migration v10 (`access_log`, `task_queue`, the `internal_networks`
  default) and `LOCK_WORKER`.
- `backend/config_rbac.py`: `INTERNAL_ONLY_ROLES` with the date and reason;
  `access_log:view` (manager, IT admin; global).
- `backend/auth_utils.py`: `session_id` on `g.user`; failure codes; the outcome marks in
  `require_auth`, `require_perm` and `require_perm_at`; the test factory called inside
  `require_auth`; `logged_role()`.
- `backend/app.py`: hook order (access log above CORS, gate after auth); `network` in `/api/auth/me`.
- `backend/settings.py`: `GET/PUT /api/settings/network`, `GET /api/settings/access-log`, `GET /api/settings/tasks`.
- `backend/api_common.py`: `date_arg()` (DD-MM-YYYY or YYYY-MM-DD).
- `backend/worker.py`: the idle loop replaced by the drain loop (`Worker` class).

Tests:
- New: `test_network_core.py` and `test_scheduled_tasks.py` (pure); `test_access_control_api.py`,
  `test_access_log_api.py`, `test_task_queue.py`, `test_worker.py`, `test_migration_v10.py`.
- `tests/conftest.py`: `TEST_USER_FACTORY`, `InternalClient`, fallback off, cache-reset
  fixture, `_TABLES`; `RoleClient` copies the caller's headers dict (see § 4).
- `tests/test_auth.py`: `db_down` also patches `access_control.ensure_schema`; new
  `TestAccessLogMarks` (failure codes, `sid`, a real-token IT admin gated, `session_id`
  logged).
- `tests/test_rbac.py`: `access_log:view` in the role matrix; `INTERNAL_ONLY_ROLES` policy
  checks.

Frontend:
- `frontend/src/api.js`: keeps `ip` from the error body; sets `networkDenied` on `network_denied`.
- `frontend/src/stores/auth.js`: `networkDenied = ref(null)`.
- `frontend/src/App.vue`: the full-page network card, checked before `authenticated` and `authError`.
- `frontend/src/views/SettingsView.vue`: Network and Background tasks cards; shows `AccessLog` with `access_log:view`.
- `frontend/src/views/settings/AccessLog.vue` (new): the access-log list.

Docs:
- `docs/steps/S013-network-gate-access-log/1-brief.md` and `docs/steps/README.md`: status only.
- This report.

## 4. Decisions taken

Departures from the brief's wording:
1. **The purge commits per batch inside the handler.** § 5.5 says a handler commits
   nothing, but § 5.6 asks for one transaction per purge batch. The purge calls
   `conn.commit()` after each batch, the stated exception in `task_handlers.py`'s
   docstring. When it stops on `should_stop()`, the task is marked done; the next day's run
   continues, as § 5.6 says.
2. **IST in the worker is a fixed `timezone(+05:30)`, not `ZoneInfo("Asia/Kolkata")`.**
   ZoneInfo needs the `tzdata` package on Windows (the import failed in tests), and the
   brief allows no new dependency. India has no daylight saving; `equipment.py` already
   does the same.
3. **No `ping(reconnect=True)`.** PyMySQL 2.2 deprecates the `reconnect` argument (it
   warned in the tests), and CLAUDE-COMMON forbids deprecated APIs. The worker calls
   `ping()`; on failure it closes the connection and opens a new `get_local_db()` one. The
   effect is the same: a fresh session re-runs the IST `init_command`, and the lock is
   taken again.

Small choices the brief left open:
4. **Lock check:** `IS_USED_LOCK(name) = CONNECTION_ID()` first, `GET_LOCK(name, 0)` only
   when not held. This avoids stacking recursive `GET_LOCK` counts every loop.
5. **`Worker(lock_name=…)` parameter.** It defaults to `LOCK_WORKER`; the tests use
   `yantra_worker_test`, because lock names are server-wide and a dev worker on the same
   MariaDB holds `yantra_worker`.
6. **Bad tasks fail at once.** An unknown task type or a bad payload (`BadTask`) is set to
   `failed` on the first attempt, without retry; retrying can't fix it. Other exceptions
   retry as specified.
7. **`mark_failed`** sets `completed_at` on the final failure and keeps `last_error` up to
   2000 characters.
8. **API shapes:**
   - `GET /api/settings/network` returns `networks` as a list of strings; `PUT` takes text.
   - `/api/settings/tasks` returns `{tasks: [{task_type, daily_at, last_run, last_status,
     next_run, overdue}], failed_count}`. `daily_at` was added for the card. `last_run` is
     the latest row's `completed_at`, else its `created_at`. "Now" is the database's
     `NOW()`.
9. **Constants:** `OVERDUE_MINUTES = 5` lives in `scheduled_tasks.py` with the overdue
   rule; the brief's named constants are in `company_settings.py`.
10. **`denied_network` rows** have `detail` NULL; the role column already names the role.
11. **Ranges loader:** read through the request's `get_db()`. A database failure starts a
    30-second retry back-off for the loader (§ 5.2 asks for at most one warning per 30 s).
12. **New helpers:**
    - `api_common.date_arg()` for `from`/`to`;
    - `auth_utils.logged_role()` for the log's role column, using no query;
    - `network_core.parse_ip()`, shared by `is_internal` and the hook's warning on an
      unparsable address.
13. **The unparsable-address warning** is logged once per written sighting, from the hook.
14. **Test harness fix:** `RoleClient` used to `.update()` the caller's `headers` dict in
    place, which leaked `X-Test-Role` into a module-level constant across tests. It now
    builds a new dict. This changes test code only.
15. **Wording:** the network card adds "Connect to the plant network (Wi-Fi or VPN) and
    reload the page". The Network card's help line covers one range per line, the VPN pool,
    who is restricted, the 5-minute spread, and the guard's limit.

## 5. Not done, deferred or assumed

- **The worker container now needs `secrets_app.py` and DB access.** The old idle worker
  imported nothing; the new one imports `config`. The devops compose
  (`smtw_erp_devops/erp_server/yantra/compose.yml.j2`) must mount or render
  `secrets_app.py` into the worker container as it does for the backend. I could not check
  that template from this repo. **Verify before the release.**
- **MariaDB ≥ 10.6** for `SKIP LOCKED` (brief § 9.4): checked at the release.
- **`sid` claim.** When a token has no `sid`, the sighting key falls back to the username,
  so the log still works, with coarser sessions. `docs/Keycloak.md` (planner) covers it.
- **No frontend unit tests added.** The brief lists none; the network card and the Settings
  cards are covered by the manual checks.
- **Dev.** With the PyCharm "Backend" config (`DEV_AUTH_BYPASS=1`) the gate and the log are
  skipped by design. Without the bypass, the dev server's `remote_addr` (127.0.0.1 through
  the Vite proxy) counts as internal.
- Nothing else from the brief is left out. Docs listed under "Docs (at approval)" were done
  by the planner and not touched.

## Tests run

- `tooling/run-tests.bat`: backend **1163 passed**, frontend **51 passed** (9 files). No
  warnings after the `ping` change.
- `npx vite build` in `frontend/`: built cleanly.

## Manual checks

Important:
- [x] (covered by backend API tests, `test_access_control_api.py`; accepted by KLA, 21-10-2026) From the plant network as IT admin: Yantra works. From a phone on mobile data as the same IT admin: the "plant network only" card with the address. As a manager on mobile data: Yantra works. Over the VPN as IT admin: Yantra works (the VPN pool is internal).
- [x] (covered by backend API tests, `test_access_control_api.py`; accepted by KLA, 21-10-2026) Settings › Network shows "Your address: … — internal" from the plant; a list that would exclude it is refused.
- [ ] Settings › Access log shows real, varied client addresses (not the proxy's 10.24.x.x), including the phone's external one and the refusal. From a phone on mobile data, the log shows the carrier's address, not 10.24.0.18, and Settings › Network says "external" — before the gate is trusted (A1).
- [ ] **Production, at the release:** MariaDB ≥ 10.6 (Settings › Database); after deploying, the worker container log shows "worker started" and the lock taken; next morning, Settings › Background tasks shows the 02:30 purge as done and no Overdue badge.

Also (plain):
- Stop the worker container for a minute and start it again: the Background tasks line still shows the last run; nothing runs twice.
- An IT admin on Wi-Fi who switches to mobile data mid-session sees the card on the next action.

## Fix rounds

### Round 1

Tests: `tooling/run-tests.bat` backend **1168 passed** (+5), frontend **51 passed**.

- **CR1-01 — Fixed.**
  - `worker.py` `run_one` now re-raises an `OperationalError` only on a real connection loss
    (`_connection_lost`: connection closed, a client-side code >= 2000, or server codes 1053 /
    1927). Deadlock 1213 and lock wait timeout 1205 go through rollback + `mark_failed`, so
    `last_error` is set and attempts count. The failure handling is one helper, `_task_failed`.
  - `task_queue.requeue_stale` first sets expired `running` tasks with
    `attempts >= max_attempts` to `failed` (`completed_at = NOW()`, `last_error = 'worker lost
    the task; attempts used up'`), then the rest to `pending`. It returns the total touched; the
    worker's log line now says "set back to pending or failed".
  - Tests: `test_a_stale_claim_with_attempts_used_up_fails`, `test_a_deadlock_or_lock_timeout_is_a_task_failure`
    (1213 and 1205), `test_a_lost_connection_is_re_raised`.
  - Decision: the connection-loss test is by code (2xxx plus 1053/1927) or a closed connection,
    the reviewer's suggestion; the two server codes are my addition (shutdown, killed session).
- **CR1-02 — Fixed.** `main()` also catches `Exception`, logs it with `logger.exception`, closes
  the connection (a clean reconnect next loop), waits the usual poll interval and carries on.
  Test: `TestMainLoop.test_an_unexpected_error_does_not_end_the_worker` (first `run_once` raises
  `ValueError`, the second is reached).
- **CR1-03, CR1-04 — not addressed**, as the user asked (nits).

### Round 2

Tests: `tooling/run-tests.bat` backend **1170 passed** (+2), frontend **51 passed**.

- **CR2-01 — Fixed.** `worker.py` `_connection_lost` now treats only client codes
  `2000 <= code < 3000` (`CLIENT_ERROR_CODES`) plus 1053 / 1927 as a lost connection, so a
  server code such as 4025 `ER_CONSTRAINT_FAILED` goes through rollback + `mark_failed`.
  Test: `test_a_server_constraint_error_is_a_task_failure` (4025 -> `pending`, `last_error` has 4025).
- **CR2-02 — Fixed.** New `_log_lost` logs the lost-connection case with `exc_info`, so the chain
  shows the original error. `run_one` also catches the case where the rollback itself raised on a
  closed connection (the generic branch, `not self.conn.open`): it logs the original cause via
  `__context__` and re-raises. Test: `test_a_failed_rollback_logs_the_original_cause`.
- **CR2-03 — Fixed.** `task_queue.py` module docstring: stale tasks become pending, or failed when
  their attempts are used up.
- CR1-03, CR1-04 — still not addressed, as the user asked.

## Amendment A1 — One row per sighting per day, enforced by the database

Tests: `uv run pytest -q` in `backend/` (the same suite as `tooling/run-backend-tests.bat`)
**1283 passed** in 183 s. Frontend not changed, so no frontend run or `vite build`.

### What was built

- The access log now keeps **one row per sighting key per IST calendar day**, held by a unique
  key in the database, so the three Gunicorn workers (each with its own cache) can no longer
  write the same sighting three times, and an active user no longer gets a new row every
  10 minutes. The key is unchanged: `(outcome, session_id or username, client_ip, detail)`.
- The viewer is unchanged.

### How it works

- **Pure core** (`network_core.sighting_hash(outcome, who, ip, detail)`): joins the four parts
  with `\x1f` (a missing part is written as an empty string) and returns the SHA-1 hex, 40
  characters. Unlike Python's `hash()` it is the same in every process, so every worker
  computes the same value for the same sighting.
- **Table** (`access_log`, migration v10 edited in place as A1 says): two new columns,
  `sighting_day DATE NOT NULL` and `sighting_hash CHAR(40) NOT NULL`, and
  `UNIQUE KEY ux_access_log_sighting (sighting_hash, sighting_day)`.
- **Hook** (`access_control._record` / `_insert`): on a cache miss the row gets
  `sighting_hash(*key)` and is written with `INSERT IGNORE … CURDATE() …`. `CURDATE()` runs in
  the same session time zone (`+05:30`) as the `ts` default, so the day is `ts`'s IST date.
  `_insert` returns `cur.rowcount`: 1 when written, 0 when the unique key already holds that
  sighting for today (another worker, or an earlier process). Either way the key is then
  remembered in the process's `SightingCache`, so a repeat within 10 minutes makes no insert
  attempt. A failed connect or insert still backs off 30 s and is not remembered (unchanged).
- **Cache** (`SightingCache`): code unchanged; the docstring now says its only role is to save
  the insert attempt for repeats within the window, the one-row rule being the database's.

### Files touched

- `backend/network_core.py` — `sighting_hash()`, `_KEY_SEPARATOR`, `hashlib` import;
  `SightingCache` docstring.
- `backend/local_db.py` — migration v10: the two columns, the unique key, a comment line.
- `backend/access_control.py` — `_insert` uses `INSERT IGNORE` with `sighting_day` /
  `sighting_hash` and returns the row count; `_record` adds the hash and remembers on either
  result; module docstring says "per day".
- `backend/tests/test_network_core.py` — `TestSightingHash`: a pinned expected value (stable
  across runs), `None` and `""` alike per part, each part changes the hash, parts do not run
  together (`"ab","c"` vs `"a","bc"`).
- `backend/tests/test_access_log_api.py` — `test_one_row_per_day_across_workers` (cache cleared
  between two requests → one row; checks `sighting_day` = date of `ts` and the stored hash),
  `test_another_key_is_another_row` (another address; another outcome and detail, a
  `denied_perm` on the log viewer), `test_another_detail_is_another_row` (`no_token` vs
  `invalid_token`), `test_a_rejected_insert_is_remembered` (counts `_insert` calls: one ignored
  insert returning 0, no third attempt, one row); the viewer's seeding helper fills the two new
  columns.
- `backend/tests/test_worker.py` — the purge test's row helper fills the two new columns.
- `backend/tests/test_migration_v10.py` — asserts the two columns and the unique key's columns
  and order.
- `docs/steps/S013-network-gate-access-log/1-brief.md`, `docs/steps/README.md` — status only.

### Decisions taken

- **The hash is computed from the untruncated key**, the same tuple the cache uses, not from
  the truncated column values. Only a detail over 255 characters could differ, and the hash
  then still tells two such details apart.
- **Test rows written directly** (viewer seed, purge test) use `SHA1(UUID())` as the hash, so
  they never collide with each other or with hook rows.
- **The "address missing or not an address" warning** is now logged only when the row was
  actually written (`written` is 1), so a second worker that finds the row already there does
  not repeat it. This is the one use of `_insert`'s return value in the shell.
- **Migration test extended** (not listed under A1's *Where*): it checks the new columns and
  the unique key, since v10 was edited in place and the existing test pins its shape.
- `INSERT IGNORE` (as the brief says) also turns other insert errors into warnings, e.g. an
  over-long value. Every text column is already truncated before the insert and `outcome` is
  always one of the enum values, so nothing else can be ignored in practice.

### Not done, deferred or assumed

- **Dev and test databases:** I did not run `tooling/dev/dev-db-reset.bat` (interactive, and
  it would wipe all dev data). Instead, in both `vel_yantra_master` and `vel_yantra_test`, I
  dropped `access_log` (0 rows in each) and deleted `db_version` row 10, then ran `init_db`:
  v10 re-ran and created the new table; `task_queue` and the `internal_networks` setting were
  kept (`IF NOT EXISTS` / `INSERT IGNORE`). Any other dev DB that already has v10 (another
  machine) needs the same, or a reset.
- **Brief docs:** the tightened wording of manual check 3 (§ 8) and the superseded text of
  § 4 / § 5.4 are the planner's (A1 *Where*); not touched. `SMTW-WebApp-Base.md` not touched.
- Accepted by A1: a session active across midnight IST gets a second row.

### Manual checks

A1 adds none of its own; it tightens important check 3 above, which now carries the A1 wording (see the brief, § 8 and A1).

Also (plain):
- Open Yantra on a phone and move through a few pages over more than 10 minutes: the Access log shows one row for that session and address today, not one per worker or per 10 minutes.

### Fix round after code review r4

- **CR4-01 Fixed.** `_record` in `backend/access_control.py` now checks `outcome not in OUTCOMES` (imported from `network_core`) before the sighting cache and the insert; an unknown outcome is logged at error level, naming it, and the write is skipped without raising. Test `test_an_unknown_outcome_is_logged_not_written` (in `backend/tests/test_access_log_api.py`) forces an unknown outcome and checks no row and the log line (`caplog`).
- **CR4-02 Fixed.** Test `test_a_missing_address_is_warned_once` (same file) sends `X-Real-IP: ""` twice: the "missing or not an address" warning appears once, with the written row, and not again on the deduped repeat; one row.
- **CR4-04 Fixed.** The run of spaces in `test_none_and_empty_hash_alike` (`backend/tests/test_network_core.py`) is replaced by a parenthesised, line-broken assert.

Files touched: `backend/access_control.py`, `backend/tests/test_access_log_api.py`, `backend/tests/test_network_core.py`.
