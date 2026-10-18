```
Step: S013 — Network gate, access log and job queue
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 18-10-2026
```

# S013 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** 0 blocker, 0 major, 2 minor, 2 nit.

Reviewed: the working-tree diff on top of c2c45d2 (S012 committed in 3e338b4), read with
`git diff -w --ignore-cr-at-eol`, plus the new untracked files read in full. Checked against
the approved brief (gate A: only `it_admin` is internal-only; the gate reads token roles only)
and `3-impl-report.md`. Docs the planner edited (Plan.MD, CLAUDE.md, Keycloak.md, etc.) and the
unrelated `equipmentLabels.js` change are out of scope.

## Tests run

- `tooling/run-tests.bat`: backend **1163 passed** (157.9 s), frontend **51 passed** (9 files).
  Green.
- `npx vite build` in `frontend/`: built cleanly (154 modules), no warnings.

## Findings

### CR1-01 — minor — `backend/worker.py:132`, `backend/task_queue.py:74`

**Problem.** `run_one` treats every `pymysql.err.OperationalError` as "the connection is
gone". It re-raises without `mark_failed`, and `main()` then closes the connection, which also
drops the lock. But PyMySQL raises `OperationalError` for more than a lost connection. In
`pymysql/err.py`, `ER.LOCK_DEADLOCK` (1213) is mapped to `OperationalError`, and an unmapped
server error ≥ 1000, such as lock wait timeout (1205), falls back to `OperationalError`. On
those errors the connection is fine, and brief § 5.5 (3) asks for "rollback, then
`mark_failed`". The report's "Decisions taken" doesn't list this.

The task is then left `running` with no `last_error` until `locked_until` passes.
`requeue_stale` sets it back to `pending` without checking `attempts` against
`max_attempts`, and `claim_next` doesn't check either. So a task that fails this way every
time, or one that kills the worker process (an OOM, a container kill mid-task), is retried
every `TASK_LOCK_MINUTES` for ever. That breaks the § 5.5 goal "a failing task can't retry
for ever", and the failed count never shows it.

**Scenario.** A future handler does an `UPDATE` that deadlocks with a request every run. The
worker logs "database error; reconnecting next loop", drops and re-takes its lock, and the
task cycles `running` → `pending` → `running` every 10 minutes indefinitely. Its `attempts`
grows past `max_attempts`, `last_error` stays empty, and `failed_count` stays 0. (The purge
alone is unlikely to hit this, because its range sits far below the rows being inserted.)

**Fix.**
1. Re-raise only for a real connection loss, for example when `self.conn.open` is false or
   the error code is in the client range (2006, 2013, …). Let other `OperationalError`s go
   through the normal `mark_failed` path.
2. Make `requeue_stale` set a stale task to `failed`, with
   `last_error = 'worker lost the task'` and `completed_at = NOW()`, when
   `attempts >= max_attempts`. Otherwise set it back to `pending` as now.
3. Add a test for each change.

### CR1-02 — minor — `backend/worker.py:171-176`

**Problem.** `main()` catches only `pymysql.MySQLError`. Any other exception raised by
`run_once` outside the per-task `try` ends the worker process. Examples:
- a `TypeError` in `mark_failed` when the row has vanished (`row` is None);
- a bug in `due_tasks` or the schedule (a malformed `"HH:MM"`);
- `json.loads` in `claim_next`.

Brief § 5.5 says an unknown task or a bad payload "fails that task (logged), never the
worker", and the base pattern says the worker keeps running. Whether the container restarts
the process depends on the devops compose's restart policy, which this repo can't check.

**Scenario.** A later step adds `("daily_summary", "7:30 ")` to `SCHEDULE`. `_at()` raises
`ValueError` on every loop, the worker exits at once, and if the compose has no
`restart: unless-stopped` the queue stops until someone notices the Overdue badge.

**Fix.** In `main()`, add a second
`except Exception: logger.exception("Worker loop failed; retrying next loop"); worker.close()`
after the `MySQLError` branch. The loop then logs the error, never hides it, and carries on.
Add a test that makes `run_once` raise a `ValueError` and checks that the loop goes on.

### CR1-03 — nit — `backend/worker.py:48-50`, `:116`

The scheduler decides "due" from the Python clock (`now_ist()`), but compares it with
`created_at`, which the database's `NOW()` stamps. If the worker host's clock runs δ ahead of
the DB server's clock, a loop in the first δ after 02:30 enqueues the task, and the row's
`created_at` falls just before 02:30. The next loop then finds nothing "since today's time"
and enqueues it again. That is harmless for the idempotent purge, and NTP keeps δ to
milliseconds. This follows the brief as written (§ 4: the worker passes `now_ist()`).

`GET /api/settings/tasks` already reads `SELECT NOW()`. Doing the same in
`enqueue_scheduled` would remove the skew, and with it the need for the worker's own IST
constant (see CR1-04). Optional; it would need a one-line note in the report as a departure.

### CR1-04 — nit — `backend/worker.py:42`, `backend/equipment.py:71`

`IST = timezone(timedelta(hours=5, minutes=30))` is now defined in two modules (DRY). The
departure itself is reported (decision 2) and sound: India has no daylight saving, and
`ZoneInfo` needs `tzdata` on Windows. Move the constant to one shared place, for example
`company_settings.py` or a small `timeutil`, and import it in both modules.

## Coder's stated departures

1. **The purge commits per batch inside the handler: accepted.** § 5.5 ("the handler commits
   nothing") and § 5.6 ("one transaction per batch") conflict, and the coder chose § 5.6 and
   reported it.
   - What it means: the connection is autocommit, so after the first `conn.commit()` the
     worker's `transaction()` no longer wraps the rest. The `task_queue` clean-up and
     `mark_done` each autocommit, and the final `commit()` does nothing.
   - That is safe only because the purge is idempotent. The docstring of `task_handlers.py`
     states it as the one exception.
   - Worth recording for later handlers: a handler that commits gives up the
     "work + `mark_done` atomic" guarantee.
2. **A fixed +05:30 offset instead of `ZoneInfo`: accepted.** It is correct for Asia/Kolkata,
   it matches `equipment.py`, and it adds no dependency. See CR1-04 for the duplicate constant.
3. **Reconnecting instead of `ping(reconnect=True)`: accepted.** I checked it in the installed
   PyMySQL: `connections.py` emits a `DeprecationWarning` for `reconnect` ("Create a new
   connection if you want to reconnect"), so CLAUDE-COMMON's no-deprecated-API rule requires
   the change.
   - `connect()` pings. On any `MySQLError` (this includes `err.Error("Already closed")`) it
     closes the connection and opens a fresh `get_local_db()` one, which re-runs the IST
     `init_command`.
   - `holds_lock()` then sees a new `CONNECTION_ID()` and takes the lock again before any
     work. `test_retaken_after_a_dropped_connection` covers this by killing the session.

The other "Decisions taken" (4–15) stay within the brief or fill gaps it left open. None
changes the design.

## Checked and found consistent

**Gate (gate A).**
- `INTERNAL_ONLY_ROLES = ("it_admin",)`, with the date and reason in a comment.
  `gate_refuses` uses token roles only, and the gate reads no memberships.
- Admin, public paths, `OPTIONS` and the dev bypass skip the gate. External manager, engineer,
  operator and admin pass; external IT admin gets 403 `network_denied` with `ip`, on
  `/api/auth/me` too.
- A real-token IT admin is gated as well (`test_a_real_token_it_admin_is_gated`).
- `X-Forwarded-For` is never read. An empty or unparsable address counts as external.
  IPv4-mapped addresses are unwrapped, and loopback is internal in code.
- The `remote_addr` fallback needs `FLASK_DEBUG=1`, and the tests turn it off.

**Hook order.**
- `before_request`: `require_auth` → `require_network` → timer.
- The access-log `after_request` hook is registered above `CORS(app)` and above
  `_log_slow_request`, so it runs last. Flask also runs it on error-handler and 500
  responses.
- The test harness now sets `g.user` inside `require_auth` through `TEST_USER_FACTORY`. With
  no factory the request gets 401, which is tested.

**DB down.**
- The gate decides from the cached ranges, falling back to `DEFAULT_INTERNAL_NETWORKS`. The
  ranges loader has its own 30-second back-off.
- `/api/auth/me` answers 200 for an internal IT admin with `db_unavailable` and `network`.
- The access-log hook skips writes while `ensure_schema` reports the DB down, and backs off
  30 s after a failed connect or insert (tested with `get_pooled_db` patched).
- A sighting is cached only after a successful insert, so it is written once the DB is back
  (tested). The `db_down` fixtures patch both `ensure_schema` references (BR2-03).
- Gunicorn uses `sync` workers, so the hook's second pooled connection can't exhaust the pool.

**Access log is append-only.**
- The only write paths are `_insert` (an INSERT) and the purge (a DELETE by age, in batches).
- The table has no foreign keys (tested in `test_migration_v10`), and the viewer route is GET
  only. `test_the_log_has_no_write_routes` asserts that no write method exists on the
  access-log path.

**Outcomes.**
- Each failing return of `validate_keycloak_token` sets one of four fixed codes, never the
  JWT library's message.
- `require_perm` marks the key; `require_perm_at` marks `key@site:<id>`.
- A business 403 gives its message, cut to 100 characters. A 400 or 500 counts as `ok`.
- The sighting key is `(outcome, sid or username, ip, detail)`, with a 10-minute window and
  pruning at 10 000 entries. `path`, `user_agent` and `detail` are cut to the column widths.
- No route catches `ApiError`, so a mark from `require_perm_at` can't leak onto a 200.

**Network setting.**
- Entries may be separated by commas or newlines. Host bits are dropped, a bad entry is named
  in the error, and an empty list is refused.
- The lock-out guard checks the saver's own address, and admin is exempt.
- The save runs `SELECT … FOR UPDATE`, then logs the actor and old → new. A save clears this
  process's cache at once. A corrupt stored value gives the defaults, with a warning.
- Every query is parameterised. The `IN (…)` and `WHERE` text is built from code constants
  only.

**Queue and worker.**
- Three transactions per task: the claim (`FOR UPDATE SKIP LOCKED`, committed), the handler
  together with `mark_done`, and `mark_failed` after a rollback, working from the committed
  `attempts`.
- The retry backoff is 5 min × attempts. `BadTask` fails at once.
- `requeue_stale` runs on every loop. `enqueue` uses the caller's cursor, and a rollback
  leaves no task (tested).
- `GET_LOCK(…, 0)` runs on a dedicated `get_local_db()` connection, after an
  `IS_USED_LOCK = CONNECTION_ID()` check. The "waiting" line is logged at most once a minute.
- The worker calls `ensure_schema()` until it succeeds. SIGTERM sets the stop flag, and the
  purge checks `should_stop()` between batches (tested).

**Scheduler.**
- `due_tasks` and `next_run` are pure and tested: down over 02:30, a day change, and
  "already enqueued today".
- The overdue rule is "more than 5 minutes past `next_run`", one definition, tested through
  the endpoint.
- The purge keeps the last row per type through a derived table, and keeps `failed` rows
  (tested).

**Migration v10.**
- It is appended, and v1 to v9 are untouched. `CREATE … IF NOT EXISTS` and
  `INSERT IGNORE` keep an existing `internal_networks` value (tested).
- `LOCK_WORKER` sits next to `LOCK_MIGRATIONS`.

**RBAC.**
- `access_log:view` is granted to `maint_manager` and `it_admin`, global, and is not in
  `SITE_SCOPED`. `test_role_matrix` is updated.
- `TestPolicyStructure` checks that `INTERNAL_ONLY_ROLES` ⊆ `ROLES`, ⊆ `TOKEN_ROLES`, and has
  no `admin`.

**Frontend.**
- `api.js` sets `networkDenied` on any `network_denied` response, across `request`,
  `apiUpload` and `apiGetBlob`.
- `loadProfile` goes through `apiGet`, so the first call sets it too.
- `App.vue` checks `networkDenied` before `authenticated` and `authError`.
- The Settings cards (Network, Background tasks) and `AccessLog.vue` (filters, a pager, and
  `YYYY-MM-DD` accepted by `date_arg`) only display data. No business logic runs in the
  browser.

**Pure core / thin shell.** `network_core.py` and `scheduled_tasks.py` have no Flask, no
database and no clock. `SightingCache` takes the clock as a parameter.

**Scope.** Everything in § 1 and § 3 is built, and nothing beyond it, apart from the small
helpers reported in decision 12.

**Manual checks.** The impl report's `## Manual checks` carries all four **important** checks
of brief § 8 as unticked boxes, plus the two plain ones.

**Track.** Full, as the brief says.

## For the user's manual check

- The four **important** checks in the impl report's `## Manual checks`:
  - IT admin from the plant, from mobile data and over the VPN; a manager on mobile data;
  - Settings › Network shows your address, and the lock-out guard refuses a bad list;
  - real, varied client addresses in the access log, which also checks the Nginx
    `set_real_ip_from 10.24.0.0/23` assumption: if every row shows 10.24.x.x, the gate is
    open to everyone;
  - production: MariaDB ≥ 10.6, worker started with the lock taken, and the 02:30 purge done
    next morning.
- **Recommended addition** (from the report's § 5, not a finding): before the release, check
  that the devops compose gives the **worker container** `secrets_app.py` and DB access.
  The new worker imports `config` at start and will not run without them. A restart policy
  on that container also limits CR1-02.
- Plain: stop the worker for a minute and start it again, and nothing runs twice; switching
  Wi-Fi to mobile data mid-session as IT admin shows the card on the next action.
