```
Step: S013 — Network gate, access log and job queue
Doc: brief
Author: Planner (Opus)
Date: 17-10-2026 (revised 17-10-2026 after brief-reviews r1 and r2; 18-10-2026 at gate A)
Track: full
Status: In code review (approved 18-10-2026 by KLA)
```

# S013 — Network gate, access log and job queue

Yantra is reachable from the internet, because shop-floor phones use mobile data
(Plan.MD § 1, 11-10-2026). Today anyone with a valid login can reach the API from
anywhere, and nothing records who came in from where. Phase 1 of Plan.MD lists
three missing pieces: the **network gate**, the **access log** and the **job
queue** (CLAUDE.md "Not yet built").

This step builds:
- **a network gate:** IT admin may use Yantra only from the plant network;
  every other role, the manager included, still works from anywhere;
- **an access log:** one row each time a login session is seen from a new
  address, or refused, with a viewer in Settings;
- **a minimal job queue and scheduler:** the worker drains a `task_queue` table
  and runs daily tasks; the first task deletes old access-log rows.

**Depends on:** S012 (migration v9). This step is migration **v10**.

User decisions while planning (17-10-2026):
1. **Internal-only role: IT admin only** (changed at gate A, 18-10-2026: the
   manager must be able to work from a phone on mobile data). All other roles
   keep access from anywhere (Plan.MD § 1 still holds for them).
2. **Retention by a job queue built in this step,** not deferred and not done in
   the request path.

Already in place (not rebuilt): Nginx takes the client address only from the
front proxy's range and passes it as `X-Real-IP` (`tooling/build/nginx.conf`,
base pattern § Real client IP).

## 1. What will be built

1. **Client address and classification.** The backend reads the client address
   from `X-Real-IP` only, and classifies it as **internal** when it falls inside
   one of the plant's network ranges (or is the server's own loopback), else
   **external**. An address that can't be parsed counts as external (fail
   closed).
2. **Settings › Network:** the list of internal ranges (CIDR, e.g.
   `10.24.0.0/16`), editable by `settings:edit` (IT admin) without a deploy. The
   card also shows "Your address: 203.0.113.7 — external" so the person editing
   can see what the server sees.
3. **The network gate.** A request from an external address is refused with
   403 "Yantra can be used from the plant network only for your role" when the
   user holds **IT admin** (from the token). Everyone else passes, the manager
   included. Admin, public paths and the dev bypass skip the gate.
4. **The frontend** shows that 403 as a full-page card — the message, "The server
   saw your address as …", and Sign out — both on the first call and when a
   refusal arrives mid-session (an IT admin who walks from Wi-Fi onto mobile
   data).
5. **The access log.** One row per *sighting*: the first time a login session is
   seen from an address, again when it moves to another address (Wi-Fi → mobile
   data), and once per distinct refusal. Outcomes: `ok`, `auth_failed`,
   `denied_network`, `denied_perm`.
6. **Settings › Access log:** a paginated list, newest first, with filters: user,
   date range, external only, refusals only. Permission `access_log:view`
   (manager, IT admin).
7. **The job queue.** A `task_queue` table, `enqueue()` for the backend, and the
   worker (`worker.py`) that claims and runs due tasks, with retries for
   internal tasks.
8. **The scheduler.** The worker enqueues daily tasks at a set IST time. One
   task now: **delete access-log rows older than 365 days**, daily at 02:30 IST.
9. **Settings › Background tasks:** one line per scheduled task — last run,
   result, next run, and an **Overdue** badge when the next run is in the past —
   and the count of failed tasks, so a dead worker is visible.

**Out of scope:**
- notifications (Telegram, web push, email), PM triggers, the daily summary:
  later tasks on this queue;
- a screen to retry or cancel tasks (the failed count only);
- restricting roles per site or per unit by network (the gate is per user);
- the PWA shell (still in CLAUDE.md "Not yet built");
- a second worker or worker failover (one worker, by lock);
- alerts when the worker stops (the Overdue badge shows it).

## 2. Standards and practice

- **ISO 27001:2022 A.8.2 (privileged access rights)** is the control the gate
  implements (BR1-04). It asks that privileged access be restricted and managed:
  identified privileged accounts, used only for privileged work, and bound to
  conditions such as place or device. IT admin (logins, masters, network
  settings) is the privileged account here; "only from the plant network" is the
  condition. If its password leaks, an attacker on the internet still can't use
  it. The manager is privileged too (restore and erase documents, whole sites),
  but must work from the floor on mobile data (gate A, 18-10-2026); the access
  log (A.8.15) and Keycloak's login (A.8.5) cover that account instead.
  - **A.8.20 (networks security) and A.8.22 (segregation of networks)** support
    it: the plant network is the trusted zone the gate relies on.
  - Everyday roles stay reachable from mobile data, because the shop floor needs
    them (a business decision, 11-10-2026).
- **ISO 27001:2022 A.8.15 (logging).** Record who accessed the system, from
  where, and refused attempts; **protect the log** and keep it for a stated
  period.
  - *Protected:* the log is append-only by design — no route updates or deletes
    rows, no foreign key cascades into it, the viewer is read-only, and only the
    scheduled purge deletes, by age. The code review checks this.
  - *Retention: 365 days.* The standard asks for a stated period, not a number.
    For reference, India's CERT-In directions (April 2022) require ICT logs to be
    kept for at least **180 days**; 365 clears that and covers an annual review.
  - One row per sighting, not per request, keeps the log readable.
- **ISO 27001:2022 A.8.16 (monitoring)** names failed logins and access from
  unusual places among the things to watch: the `auth_failed` rows, the external
  sightings and the "refusals only" filter serve that.
- **ISO 27001:2022 A.8.5 (secure authentication)** is unchanged: Keycloak stays
  the login gate. The network gate adds a second condition for IT admin.
- **Base pattern (SMTW-WebApp-Base § Internet exposure, § Job queue)** is
  followed, with two departures stated in § 7: the gate lists the roles that are
  **refused** from outside, not the roles allowed; and the scheduler is a small
  built-in daily schedule, not APScheduler.

## 3. Where

### Backend
- **Migration v10** in `backend/local_db.py` (§ 4): tables `access_log` and
  `task_queue`; the default `internal_networks` row in `app_settings`;
  `LOCK_WORKER = "yantra_worker"` next to `LOCK_MIGRATIONS` (base: one place for
  lock names).
- **`backend/network_core.py`** (new, pure): `parse_networks(text)` (CIDR list →
  networks, or errors), `is_internal(ip_text, networks)`, `gate_refuses(roles,
  internal)`, `classify_outcome(status, g_outcome)`, `SightingCache` (injectable
  clock).
- **`backend/access_control.py`** (new, shell): reads `X-Real-IP`, loads the
  internal networks (§ 5.2), `require_network(dev_bypass=…)` (a before-request
  factory, as `require_auth`), and the access-log `after_request` hook.
- **`backend/config_rbac.py`:** `INTERNAL_ONLY_ROLES = ("it_admin",)`, with the
  date and reason as a comment; new key
  `access_log:view` (`maint_manager`, `it_admin`; global, not site-scoped).
- **`backend/auth_utils.py`:**
  - `g.user` gains `session_id` (the token's `sid` claim);
  - `require_auth`, `require_perm` and `require_perm_at` mark
    `g.access_outcome` and `g.access_detail` on a refusal (BR1-06);
  - **the test harness moves into `require_auth`** (BR1-02): in TESTING mode with
    `X-Test-Role`, `require_auth` calls `app.config["TEST_USER_FACTORY"](role,
    username)` and sets `g.user`, instead of returning early for a later conftest
    hook. So `g.user` exists for every later hook, in tests as in production.
- **`backend/app.py`:** before-request order `require_auth` → `require_network`
  → timer; the access-log hook registered **before** the other `after_request`
  hooks, including the one `CORS(app)` registers at its call (so the hook goes
  above that line). Flask runs `after_request` hooks in reverse, so it runs last
  and sees the final status (BR2-06).
- **`backend/settings.py`:** `GET/PUT /api/settings/network`, `GET
  /api/settings/access-log`, `GET /api/settings/tasks`.
- **`backend/task_queue.py`** (new): `enqueue(cur, task_type, payload,
  scheduled_for=None, max_attempts=3)`, `claim_next`, `mark_done`,
  `mark_failed`, `requeue_stale`.
- **`backend/task_handlers.py`** (new): `HANDLERS = {"purge_access_log": …}`.
- **`backend/scheduled_tasks.py`** (new): `SCHEDULE = [("purge_access_log",
  "02:30")]` (IST) and the pure `due_tasks(schedule, last_enqueued, now_ist)` and
  `next_run(entry, last_enqueued, now_ist)` (BR1-08).
- **`backend/worker.py`:** the idle loop becomes the drain loop (§ 5.5).
- **`backend/company_settings.py`** (new, per the base), named constants
  (BR1-11): `ACCESS_LOG_RETENTION_DAYS = 365`, `DONE_TASK_RETENTION_DAYS = 90`,
  `SIGHTING_WINDOW_MINUTES = 10`, `NETWORKS_CACHE_SECONDS = 300`,
  `TASK_LOCK_MINUTES = 10`, `TASK_RETRY_BACKOFF_MINUTES = 5`,
  `WORKER_POLL_SECONDS = 5`, `PURGE_BATCH_ROWS = 10_000`.

### Frontend (BR1-05: no new route or guard)
- **`frontend/src/api.js`:** keeps `ip` from an error body, and sets the auth
  store's `networkDenied` whenever a response carries `code ===
  "network_denied"`, on any call.
- **`frontend/src/stores/auth.js`:** `networkDenied = ref(null)` (`{message,
  ip}`).
- **`frontend/src/App.vue`:** shows the full-page card (message, "The server saw
  your address as …", Sign out) when `networkDenied` is set, in place of the
  page, as it does for `authError` and the S011 no-access case. The
  `networkDenied` card is checked **before** `v-if="authenticated"` and before
  `authError` (which `loadProfile` also sets on the same 403), so it wins
  (BR2-08). Reconnecting on Wi-Fi and reloading clears it.
- **`frontend/src/views/SettingsView.vue`:** cards *Network* and *Background
  tasks*; **`views/settings/AccessLog.vue`** (new) for the access-log list.

### Tests
- New: `test_network_core.py` (pure), `test_access_control_api.py`,
  `test_access_log_api.py`, `test_task_queue.py`, `test_scheduled_tasks.py`
  (pure), `test_worker.py`, `test_migration_v10.py`.
- **Harness** (BR1-02, BR1-10):
  - `conftest` sets `flask_app.config["TEST_USER_FACTORY"]` (the existing
    harness user builder) and drops its own before-request injector.
    `require_auth` calls `factory(role, request.headers.get("X-Test-User"))`; the
    factory applies the `test_<role>` default, so the harness convention stays in
    conftest. TESTING with `X-Test-Role` and **no factory** → 401 (fail closed;
    BR2-05);
  - `flask_app.test_client_class` becomes a `FlaskClient` subclass whose requests
    default to `X-Real-IP: 10.0.0.5` (internal), so the raw `client`,
    `RoleClient` and every fixture are unaffected; gate tests override it with an
    external address. The "missing address" test sends `X-Real-IP: ""` (Flask
    merges the default header back in, so it can't be left out; empty counts as
    unparsable → external). Conftest turns off the `FLASK_DEBUG` `remote_addr`
    fallback of § 5.1 (BR2-05);
  - **DB-down tests patch every `ensure_schema` reference** — the one in
    `db_helpers` (as `db_down` does today) and the ones the access-log hook and
    the ranges loader import — and the hook's back-off test patches
    `get_pooled_db` to raise, so these tests can't pass vacuously (BR2-03);
  - `conftest._TABLES` gains `access_log` and `task_queue`;
  - a fixture clears the per-process `SightingCache` and the networks cache;
  - the dev-bypass test calls `require_network(dev_bypass=True)`'s handler in a
    `test_request_context` (conftest refuses `DEV_AUTH_BYPASS`).
- **Changed existing tests:** `test_rbac.test_role_matrix` gains
  `access_log:view` for manager and IT admin; `test_rbac.TestPolicyStructure`
  checks `INTERNAL_ONLY_ROLES ⊆ ROLES` and no `admin` in it (BR1-12).
  `test_auth.TestDatabaseDown.test_it_admin_gets_token_permissions` stays green
  through the client's default internal address.

### Docs (at approval, by the planner)
- `docs/Plan.MD` § 1 (the access-from-outside row: IT admin internal-only),
  § 3 (`access_log:view` row), § 5 (tables), § 8 (phase 1 items done).
- `.claude/CLAUDE.md`: "Not yet built" (only the PWA shell left); a line on the
  worker; the deny-list `INTERNAL_ONLY_ROLES` recorded as a deliberate departure
  from the base's `access:wan` (BR1-12).
- `docs/Keycloak.md`: the `sid` claim is what the access log calls a session.

## 4. Data model (migration v10)

```sql
CREATE TABLE IF NOT EXISTS access_log (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    ts          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    username    VARCHAR(100) NULL,            -- NULL when the token was not valid
    role        VARCHAR(100) NULL,            -- the display role at that moment
    session_id  VARCHAR(100) NULL,
    client_ip   VARCHAR(45) NOT NULL,
    is_internal TINYINT(1) NOT NULL,
    outcome     ENUM('ok','auth_failed','denied_network','denied_perm') NOT NULL,
    method      VARCHAR(10) NOT NULL,
    path        VARCHAR(255) NOT NULL,
    user_agent  VARCHAR(255) NULL,
    detail      VARCHAR(255) NULL,            -- refusal reason or permission key
    sighting_day  DATE NOT NULL,              -- A1: the IST date of ts (CURDATE())
    sighting_hash CHAR(40) NOT NULL,          -- A1: SHA-1 of (outcome, who, ip, detail)
    INDEX ix_access_log_ts (ts),
    INDEX ix_access_log_user_ts (username, ts),
    UNIQUE KEY ux_access_log_sighting (sighting_hash, sighting_day)   -- A1: one row per sighting per day
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS task_queue (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    task_type     VARCHAR(50) NOT NULL,
    payload       JSON NULL,
    status        ENUM('pending','running','done','failed') NOT NULL DEFAULT 'pending',
    attempts      INT NOT NULL DEFAULT 0,
    max_attempts  INT NOT NULL DEFAULT 3,
    scheduled_for DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    locked_until  DATETIME NULL,
    last_error    TEXT NULL,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at  DATETIME NULL,
    INDEX ix_task_queue_due (status, scheduled_for),
    INDEX ix_task_queue_type_created (task_type, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT IGNORE INTO app_settings (setting_key, setting_value)
VALUES ('internal_networks', '10.0.0.0/8,172.16.0.0/12,192.168.0.0/16');
```

- **Times are IST through the session setting** (BR1-03). Every Yantra
  connection runs `SET time_zone = '+05:30'` (`local_db._connect_kwargs`), so
  `NOW()` and `DEFAULT CURRENT_TIMESTAMP` already give IST, as in every table
  from v1 to v9. SQL uses `NOW()`. The pure scheduler takes `now_ist` as a
  parameter; the worker passes `now_ist()` (`datetime.now(ZoneInfo(
  "Asia/Kolkata"))`, naive), which agrees with `NOW()` because of that session
  setting. The worker connects with `get_local_db()`, so it gets the setting.
- **Default internal ranges: the three private (RFC 1918) ranges**, the constant
  `DEFAULT_INTERNAL_NETWORKS` in `network_core.py`, used by the migration and by
  the fallbacks of § 5.2. Every plant address is inside them, and a phone on
  mobile data has a public address (or a carrier address in `100.64.0.0/10`,
  which is not in the list). IT admin can narrow the list later. This default
  keeps IT admin able to reach Settings on the first deploy.
- `client_ip` is 45 characters, room for an IPv6 address. `path`, `user_agent`
  and `detail` are truncated to 255 before writing (BR1-11), so a long scanner
  URL can't make the insert fail.
- **No foreign keys:** the log keeps its rows when people or logins change.

## 5. Rules

### 5.1 Client address
- From `X-Real-IP` only, never `X-Forwarded-For` (base pattern: its first entry
  is what the client sent). Missing or unparsable → a warning (once per
  sighting) and **external**.
- In dev (no Nginx) the address is `request.remote_addr` when `X-Real-IP` is
  missing **and** `FLASK_DEBUG` is set, so the dev server works on localhost. In
  production `X-Real-IP` is always set by Nginx.
- **`is_internal`** (BR1-09): an IPv4-mapped IPv6 address (`::ffff:10.24.0.5`) is
  unwrapped to its IPv4 form before matching; **loopback** (`127.0.0.0/8`,
  `::1`) is internal in code, not through the editable list — only the server
  itself can present it, and it keeps dev working when IT admin edits the list.

### 5.2 Internal networks setting
- Stored as comma-separated CIDR text in `app_settings`. The `PUT` body is
  `{"networks": "<text>"}` as typed in a textarea, comma- or newline-separated;
  entries are trimmed and normalised with `ip_network(…, strict=False)`, so
  `10.24.0.5/16` is saved as `10.24.0.0/16` (BR1-11).
- Saved only when every entry parses (400 on the field, naming the bad entry)
  and the list is not empty (400 "At least one range is needed").
- **Lock-out guard:** a `PUT` that would make the saving user's own address
  external is refused, 400 "This would block your own address (x.x.x.x) — check
  every site's range before saving", unless the user is admin. It protects the
  saver only, not an IT admin at a site on another range; the message says so.
- The change is logged with actor and old → new, under `SELECT … FOR UPDATE`, as
  `put_app_settings` does (A.8.15).
- Read through a 5-minute cache per process (base pattern); a save clears the
  saving process's cache at once. Other Gunicorn workers pick it up within 5
  minutes — stated in the card's help line.
- **Fallbacks** (BR1-01), so the gate never locks out the plant:
  - an unreadable stored value (hand-edited) → logged, and the defaults are used;
  - **the database unreachable** (`DBUnavailable`) → the last cached list if
    any, else `DEFAULT_INTERNAL_NETWORKS`; logged at most once per 30 s, as
    `ensure_schema` does.

### 5.3 The network gate
- Runs after `require_auth`, before the route (Flask stops at the first
  before-request hook that returns a response, so it never runs on a 401).
  Skips: public paths (`/api/auth/config`, `/api/version`, `/api/health`), admin,
  the dev auth bypass, `OPTIONS`.
- **An internal address passes before any database read** (BR1-01): no
  membership query is made. This keeps IT admin from the plant DB-free on
  `/api/auth/me` and `/api/settings/db-status` while the database is down (S011
  BR1-01).
- **External: refused when the user holds any role in `INTERNAL_ONLY_ROLES`**
  (today `it_admin`). The roles are taken **from the token only**: the gate
  never reads memberships, so it makes no database read at all. Should a site
  role ever be added to the list, the gate must read memberships too (and the
  DB-down rule of BR1-01 applies again).
- `/api/auth/me` still answers while the DB is down (S011 BR1-01), now with
  `network: {ip, internal}`.
- Refusal: 403 `{"error": "...", "code": "network_denied", "ip": "..."}`;
  `g.access_outcome = "denied_network"`; a warning log line naming user, roles
  and address.
- `/api/auth/me` is gated too, so the frontend learns of the refusal on its first
  call and shows the card (§ 3 Frontend).

### 5.4 Access log
- **`after_request` hook**, wrapped in try/except: a logging failure is logged
  and never breaks the request. It runs on error-handler and 500 responses too
  (Flask calls `after_request` there), so `auth_failed`, 503 and 500 are seen.
- **Its own connection, only when the database is up** (BR1-01, BR2-01): the hook
  first asks `ensure_schema()` (answered from memory for 30 s after a failed
  attempt, but only before the schema first came up), and then keeps **its own
  30-second back-off**: after a failed connect or insert it skips writes for 30 s
  per process, logging a warning at most once per back-off. So an outage *after*
  startup costs at most one connect timeout per 30 s per process, not one per
  request. When up, it borrows its own pooled connection, so a rolled-back
  request still logs.
- **Outcome and detail** (BR1-06):
  - `g.access_outcome` when a gate set it: `require_auth` → `auth_failed`
    (detail: one fixed code that `validate_keycloak_token` sets on
    `g.access_detail` at each failing return — `no_token`, `invalid_token`,
    `wrong_client`, `no_role` — never the JWT library's message, which would
    make every probe a new sighting; the function still returns `None`, so its
    tests are unchanged; BR2-04), `require_network` → `denied_network`, `require_perm`
    → `denied_perm` (detail: the key), `require_perm_at` → `denied_perm` (detail:
    `key@site:<id>`);
  - otherwise 401 → `auth_failed`, 403 → `denied_perm` with `detail` = the first
    100 characters of the error message (the business refusals, e.g. "You can't
    change your own access");
  - any other status on an authenticated request → `ok`;
  - public paths, `OPTIONS` and the dev bypass are not logged.
- **Sighting key:** `(outcome, session_id or username, client_ip, detail)`.
  **One row per key per IST calendar day, enforced by the database** (A1,
  18-10-2026): the row carries `sighting_day` and `sighting_hash`, the insert is
  `INSERT IGNORE`, and a rejected insert (`rowcount == 0`) means another worker
  or an earlier process wrote it today. `SightingCache` (one per process, pruned
  at 10 000 entries) only saves the insert attempt for repeats within 10 minutes;
  it is not the rule. **The key is cached only after a successful insert or a
  rejected one**, never after a failed connect or insert, so a sighting during a
  short outage is written once the DB is back (BR1-01). This replaces the
  earlier "duplicates across Gunicorn workers are accepted".
- **`auth_failed` rows** carry no username (the token was not valid); the
  address and path are kept.
- **Viewer** (BR1-11): `GET /api/settings/access-log?user=&from=&to=&external=1
  &denied=1&page=&per_page=` → `{items, total, page, per_page}`, newest first,
  `DEFAULT_PER_PAGE` and `int_arg` as the other lists. `user` matches "contains"
  (`like_pattern`); `from`/`to` are DD-MM-YYYY or YYYY-MM-DD, IST, `to`
  inclusive (`ts < to + 1 day`).

### 5.5 Job queue and worker
- **`enqueue`** takes the caller's cursor, so a task can be added in the same
  transaction as the data that caused it.
- **Claim:** `SELECT … WHERE status = 'pending' AND scheduled_for <= NOW() ORDER
  BY scheduled_for, id LIMIT 1 FOR UPDATE SKIP LOCKED`, then `status =
  'running'`, `attempts + 1`, `locked_until = NOW() + TASK_LOCK_MINUTES`.
  `SKIP LOCKED` needs MariaDB ≥ 10.6 (checked at release, § 8).
- **Stale claims:** a `running` task whose `locked_until` has passed (the worker
  died mid-task) is set back to `pending` (`requeue_stale`) at start and every
  loop.
- **Three transactions per task** (BR2-02): (1) the claim — select, `status =
  'running'`, `attempts + 1` — is committed on its own, so the attempt counts
  even if the handler fails; (2) the handler runs in a second transaction and
  commits nothing itself; the worker commits it together with `mark_done`; (3) on
  an exception: rollback of (2), then `mark_failed` in its own short transaction,
  working from the committed `attempts`. So a failing task can't retry for ever.
- **Done / failed:** on an exception the worker stores `last_error`; `attempts < max_attempts` → `pending` again, `scheduled_for =
  NOW() + TASK_RETRY_BACKOFF_MINUTES × attempts`; else `failed`. Only internal,
  idempotent tasks retry (base pattern); `purge_access_log` is one. An unknown
  task type or a bad payload fails that task (logged), never the worker.
- **Connection and lock** (BR1-07):
  - **one dedicated `get_local_db()` connection** for the lock and the work —
    never the pool or `db_helpers.get_db()` (Flask's `g`);
  - `GET_LOCK(LOCK_WORKER, 0)` (non-blocking, the base's singleton rule) tried
    each loop until held; "waiting for the worker lock" logged once a minute
    while another worker holds it;
  - the connection is pinged each loop (`ping(reconnect=True)`, which re-runs
    the IST `init_command`); after a reconnect the lock is taken again before
    any work (CLAUDE-COMMON: idle connections). `IS_USED_LOCK` / `GET_LOCK` each
    loop doubles as the check that the lock is still held (BR2-09).
- **Schema:** the worker calls `ensure_schema()` each loop until it returns no
  error, so it can run the migrations itself under the migration lock and never
  touches the queue before the schema is at v10. It starts while the DB is down
  (CLAUDE.md "DB may not exist"): it logs and retries every 30 s.
- **Loop:** every `WORKER_POLL_SECONDS` — requeue stale claims, enqueue due
  scheduled tasks, claim and run tasks until none is due.
- **SIGTERM:** the worker finishes the current transaction and exits. The purge
  checks the stop flag between batches (each batch is its own transaction, so
  stopping between them loses nothing; the next day's run continues).

### 5.6 Scheduler
- `SCHEDULE` lists `(task_type, "HH:MM")` in IST, daily.
- **Pure `due_tasks(schedule, last_enqueued, now_ist)`:** a task is due when
  today's time has passed and nothing of that type was enqueued since today's
  time. `last_enqueued` comes from `task_queue` (`MAX(created_at)` per type). So
  a worker that was down at 02:30 runs the task when it comes back, once, and a
  restart never runs it twice.
- **Pure `next_run(entry, last_enqueued, now_ist)`** (BR1-08): today's time when
  not yet enqueued since it, else tomorrow's. The tasks endpoint adds `overdue`:
  true when `next_run` is more than **five minutes** in the past (one definition;
  BR2-09); the card shows
  "Overdue — is the worker running?" and the failed count in red when above 0.
- **`purge_access_log`:**
  - `DELETE FROM access_log WHERE ts < NOW() − ACCESS_LOG_RETENTION_DAYS` in
    batches of `PURGE_BATCH_ROWS`, one transaction each, until none is left
    (checking the stop flag between batches); logs the count;
  - then deletes `done` queue rows older than `DONE_TASK_RETENTION_DAYS`,
    keeping the last row per task type so `due_tasks` keeps working. The "last
    row per type" ids are read through a derived table, so they are computed
    once, not per row (BR2-07: MariaDB 11.4 accepts the direct subquery; the
    derived table is for clarity and a single evaluation). `failed` rows are
    kept until handled.
  - The handler gets a `should_stop()` callable from the worker and checks it
    between batches (BR2-09).
- **First run after the first deploy:** if the worker first starts after 02:30,
  the purge runs at once (nothing was enqueued since today's time). Harmless:
  the log is empty then (BR2-09).

### 5.7 Who sees what

| Action | Permission |
|---|---|
| Read the internal networks | `settings:read` (manager, IT admin) |
| Change the internal networks | `settings:edit` (IT admin) |
| Read the access log | `access_log:view` (manager, IT admin) — new key |
| Read Background tasks | `settings:read` |

## 6. API

| Method & path | Permission |
|---|---|
| `GET /api/settings/network` → `{networks, your_ip, your_ip_internal}` | `settings:read` |
| `PUT /api/settings/network` `{networks: "<text>"}` | `settings:edit` |
| `GET /api/settings/access-log` (filters § 5.4) → `{items, total, page, per_page}` | `access_log:view` |
| `GET /api/settings/tasks` → per scheduled type `{task_type, last_run, last_status, next_run, overdue}`, plus `failed_count` | `settings:read` |
| Every route | 403 `network_denied` from outside for the internal-only roles (§ 5.3) |
| `GET /api/auth/me` | as now, plus `network: {ip, internal}` |

## 7. Design decisions

| Decision | Reason | Rejected alternative |
|---|---|---|
| IT admin internal-only | User decision 1 (gate A); the privileged account for logins, masters and network settings (A.8.2), with no need to work from outside | Manager internal-only too (rejected at gate A: managers work from the floor on mobile data); nobody restricted |
| A deny list `INTERNAL_ONLY_ROLES`, not the base's `access:wan` allow list | A person can hold IT admin and a site role; an allow list granting the site roles would let that account through; the deny list says "any of these roles → internal only" | `access:wan` with intersection logic over roles |
| Gate reads token roles only | IT admin comes from the token; no DB read in the gate, so it works the same while the DB is down | Reading memberships (only needed if a site role becomes internal-only) |
| Internal decided before any DB read; ranges fall back to cache/defaults when the DB is down | IT admin must reach Settings › Database during an outage (S011 BR1-01; CLAUDE.md "DB may not exist") | Fail closed on an unreachable store (locks IT admin out exactly then) |
| Default internal ranges: the RFC 1918 private ranges; loopback internal in code | Safe first deploy; mobile data is public or carrier-grade NAT; dev keeps working | Empty list (locks IT admin out); loopback in the editable list |
| Lock-out guard on saving the ranges | A typo can't shut IT admin out; admin can still recover | No guard (recovery by SQL) |
| Test harness user set inside `require_auth` | Every later hook sees `g.user` in tests as in production; gate tests can't pass vacuously (BR1-02) | Re-ordering Flask's hook list from conftest |
| Mid-session refusal through an auth-store flag, no new route | One card covers the first call and later calls (BR1-05) | A new view plus a router guard |
| Job queue in this step | User decision 2; notifications and PM need it next | Retention deferred; delete in the request path |
| Built-in daily schedule, not APScheduler | One daily task; no new dependency; "due since today's time" in the DB survives restarts, where an in-memory scheduler misses a run while the worker is down | APScheduler (the base pattern), revisited if schedules get richer than daily |
| One worker via non-blocking `GET_LOCK` on a dedicated connection | Simple and safe; matches the base's singleton rule | Several workers with `SKIP LOCKED` only |
| Retention 365 days | A.8.15 asks for a stated period; above CERT-In's 180 days; covers an annual review; rows are few | 90 or 180 days; keep forever |
| Background tasks line with an Overdue badge | A dead worker is otherwise invisible until something isn't done | No status; an alert channel (later, with notifications) |
| IST through the session time zone, `NOW()` in SQL | The convention of every table v1–v9 (BR1-03) | App-written timestamps (a second convention) |

## 8. Tests and acceptance

### Pure
- `parse_networks`: IPv4, IPv6, spaces, newlines, host bits normalised, empty, a
  bad entry named in the error.
- `is_internal`: inside / outside / unparsable (→ external) / IPv6 / IPv4-mapped
  IPv6 / loopback v4 and v6.
- `gate_refuses`: it_admin, it_admin plus a site role, manager only, engineer
  only, no roles; internal always passes.
- `classify_outcome`: gate marks win; 401/403 fallbacks with detail; 4xx/5xx
  with a user → `ok`.
- `SightingCache`: first sighting written, repeat suppressed, after 10 min written
  again, new address written, not cached when the insert failed, pruning.
- `due_tasks` and `next_run`: before the time; after the time and not yet
  enqueued; already enqueued today; worker down over the time (runs once on
  return); day change; overdue.

### API
- **Gate:** external IT admin → 403 `network_denied` on a normal route and on
  `/api/auth/me`; **a `role_client` IT admin with an external `X-Real-IP` → 403 on
  `/api/masters/sites`** (checks the hook order, BR1-02); external manager → 200;
  external engineer → 200; internal IT admin → 200; external admin → 200;
  public paths from outside → 200; a missing `X-Real-IP` → external; dev bypass
  (handler called directly) passes.
- **DB down** (BR1-01): internal IT admin → 200 on `/api/auth/me` with
  `db_unavailable`; external IT admin → 403; the access-log hook does not slow or
  break the response, and the sighting is written after the DB is back.
- **Network setting:** read; save; a bad CIDR → 400 naming it; empty → 400; host
  bits normalised; a list excluding the saver's own address → 400 (admin →
  200); a corrupt stored value → defaults used; the change is logged.
- **Access log:** one `ok` row on a first request, none on the second from the
  same address, a new row from a new address; `denied_network`, `denied_perm`
  (from `require_perm`, `require_perm_at` and a business 403, each with its
  detail), `auth_failed` rows; a long path truncated; filters (`to` inclusive)
  and paging; `access_log:view` → 403 for an engineer.
- **Queue:** enqueue inside a transaction that rolls back → no task; claim →
  running; done; a failing handler retries with backoff and ends `failed`; a
  stale `running` task is requeued; an unknown task type fails without crashing
  the worker.
- **Worker:** the lock is not taken twice (a second connection's `GET_LOCK(…, 0)`
  returns 0); after a dropped connection the lock is re-taken before work; the
  stop flag ends the purge between batches.
- **Purge:** rows older than 365 days deleted, newer kept; done queue rows older
  than 90 days deleted, the last per type kept; failed rows kept.
- **Migration v10:** tables and the default setting created; re-run changes
  nothing; an existing `internal_networks` value is not overwritten.

### Manual checks (important, for the impl report)
- [ ] From the plant network as IT admin: Yantra works. From a phone on mobile
  data as the same IT admin: the "plant network only" card with the address.
  As a manager on mobile data: Yantra works. Over the VPN as IT admin: Yantra
  works (the VPN pool is internal).
- [ ] Settings › Network shows "Your address: … — internal" from the plant;
  a list that would exclude it is refused.
- [ ] Settings › Access log shows real, varied client addresses (not the
  proxy's 10.24.x.x), including the phone's external one and the refusal.
  From a phone on mobile data, the log shows the carrier's address, not
  10.24.0.18, and Settings › Network says "external" — before the gate is
  trusted (A1: VelKilnMaster's log showed the proxy address for half a day).
- [ ] **Production, at the release:** MariaDB ≥ 10.6 (Settings › Database);
  after deploying, the worker container log shows "worker started" and the lock
  taken; next morning, Settings › Background tasks shows the 02:30 purge as done
  and no Overdue badge.

Also (plain):
- Stop the worker container for a minute and start it again: the Background
  tasks line still shows the last run; nothing runs twice.
- An IT admin on Wi-Fi who switches to mobile data mid-session sees the card on
  the next action.

### Acceptance
- `tooling/run-tests.bat` green and the frontend build clean.
- IT admin on mobile data is refused; a manager on mobile data is not; both
  show in the access log with real addresses.

## 9. Open questions and assumptions

1. **Decided (18-10-2026) — admin from anywhere.** The Keycloak admin
   (`mspv-apps-admin`) bypasses the gate (base pattern), so the owner can fix a
   wrong network list from anywhere. Protect the admin account with Keycloak's
   two-factor login.
2. **Decided (18-10-2026) — VPN.** The owner connects occasionally through the
   VPN; that traffic arrives from the VPN subnet. The VPN pool counts as
   internal: it must be inside the internal ranges (a private range is, by the
   defaults); otherwise IT admin adds it in Settings › Network. Checked by
   manual check 1.
3. **Assumption:** the front proxy range `10.24.0.0/23` in `nginx.conf` is still
   correct (verified by manual check 3).
4. **Assumption:** production MariaDB is ≥ 10.6 (S012 needs ≥ 10.5); checked at
   the release.
5. **Assumption:** the devops compose gives the worker container a stop grace
   period of at least 10 s (Docker's default); the purge stops between batches
   anyway.

## 10. Amendments

### A1 — One row per sighting per day, enforced by the database

```
Requested by: KLA, 18-10-2026
Status: Approved 18-10-2026 by KLA (user: "make the S013 amend A1"); baseline: the working tree of 18-10-2026 (S013 code in review r3, uncommitted on 3e338b4)
```

**Why.** VelKilnMaster runs the same access-log design (three sync Gunicorn
workers, an in-process `SightingCache`, a 10-minute window) and 23 days of its
production log (26-09 to 18-10-2026) show that "one row per sighting" is not
what happens: 9,489 rows for twelve users, about 400 a day. Two causes, both
designed in: each worker has its own cache, so three parallel requests from one
phone at page load give three identical rows at the same second; and the
10-minute window gives an active user a fresh row every 10 minutes. The log's
question, "which addresses did each session come from", is buried under repeats.
The same data confirmed the two other points the brief already covers (below).
The base pattern (`SMTW-WebApp-Base.md` § Access log) is revised the same day so
the VelKilnMaster team can fix their code from it.

**What changes** (supersedes the sighting-key paragraph of § 5.4 and the
`access_log` table of § 4):

1. **Rule:** one row per sighting key per IST calendar day, enforced by the
   database, not by the cache. The sighting key stays
   `(outcome, session_id or username, client_ip, detail)`.
2. **Table** (`access_log`, still migration v10 — v10 is not applied anywhere
   but the disposable dev and test databases, so it is edited, not followed by
   a v11):
   - `sighting_day DATE NOT NULL` — the IST date of `ts`, set by the hook from
     the same clock as `ts` (`CURDATE()` in the insert, the session time zone);
   - `sighting_hash CHAR(40) NOT NULL` — SHA-1 hex of the key, the four parts
     joined by `\x1f`, `None` written as an empty part;
   - `UNIQUE KEY ux_access_log_sighting (sighting_hash, sighting_day)`.
3. **Hook** (`access_control._record`): on a cache miss it runs
   `INSERT IGNORE …`; `cur.rowcount == 0` means another worker, or an earlier
   process, wrote the sighting today; either way the key is then remembered in
   the cache. The pool's connections are autocommit (§ 5.4), so the row is kept
   whatever the request did.
4. **Cache** (`SightingCache`): unchanged in code; its role shrinks to saving
   the insert attempt for repeats within `SIGHTING_WINDOW_MINUTES` (10). The
   docstring and the base pattern say so.
5. **Pure core** (`network_core.py`): `sighting_hash(outcome, who, ip, detail)`,
   pure and tested: stable across processes; a missing part and an empty one
   hash alike, since the key already treats a missing detail as `""`.
6. **Viewer:** unchanged. Rows per day are now one per session per address per
   outcome, so the list reads as intended.

**Confirmed, no change** (from the same production data):

- **Real client address** — the base pattern's trap (every row carrying the
  front proxy 10.24.0.18, so an internet scanner was logged as *internal*) was
  visible in VelKilnMaster's log for the first half-day of 26-09-2026. Manual
  check 3 (§ 8) already covers it; its wording is tightened: *from a phone on
  mobile data, the Access log shows the carrier's address, not 10.24.0.18, and
  Settings › Network says "external" — before the gate is trusted.*
- **Internal ranges** — VelKilnMaster's production list omits the VPN pools
  and SSVT, so those users count as external. Yantra's defaults are the RFC 1918
  ranges (§ 7), which include both; § 9.2 already decides the VPN is internal.
  Manual check 1 names the VPN pool and SSVT's range explicitly when run.

**Where**

- `backend/local_db.py` — v10: the two columns and the unique key.
- `backend/network_core.py` — `sighting_hash()`; `SightingCache` docstring.
- `backend/access_control.py` — `_insert` returns `cur.rowcount`; `_record`
  computes the hash, uses `INSERT IGNORE`, remembers on either result.
- `backend/tests/test_network_core.py` — `sighting_hash` stable and
  distinct per part.
- `backend/tests/test_access_log_api.py` — two requests with the same key on
  the same day, the cache cleared between them (as a second worker would be),
  give **one** row; a different address, outcome or detail gives a second; a
  rejected insert is remembered (no third attempt).
- `docs/steps/S013-network-gate-access-log/1-brief.md` § 4, § 5.4 — this
  amendment supersedes them; `.claude/SMTW-WebApp-Base.md` — synced from
  smtw-common after the base is updated there (done 18-10-2026 in smtw-common).

**Open points**

- `sighting_day` on the IST calendar day: a session active across midnight
  gets a second row. Accepted; it is the simplest "per day" there is.
- The hash is SHA-1 for its fixed 40 characters, not for security; the key is
  not secret.

## Gate A — 18-10-2026 (KLA)

Approved with one change: **only IT admin is internal-only**; the manager works
from anywhere, including mobile data. Admin keeps working from anywhere. VPN
traffic comes from the VPN subnet, treated as internal (§ 9). The brief text
above is updated to match.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 17-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BR1-01 DB-down behaviour of the hooks | major | **Accepted** (option 1): internal decided before any DB read (§ 5.3); ranges fall back to the last cache or `DEFAULT_INTERNAL_NETWORKS` on `DBUnavailable` (§ 5.2); the hook asks `ensure_schema()` and skips when the DB is down; the sighting cached only after a successful insert (§ 5.4); tests (§ 8) |
| BR1-02 hook order vs the test harness | major | **Accepted** (option 1): `TEST_USER_FACTORY` called inside `require_auth`; a test client class defaulting `X-Real-IP` to an internal address; `test_role_matrix` updated; the hook-order test named (§ 3, § 8) |
| BR1-03 IST timestamps | minor | **Accepted** (option 1): `DEFAULT CURRENT_TIMESTAMP` and `NOW()`, the session time zone; `now_ist()` only for the pure scheduler; worker on `get_local_db()` (§ 4) |
| BR1-04 standards | minor | **Accepted** (option 1): A.8.2 leads; A.8.20/A.8.22 supporting; A.8.15 "protected, append-only"; CERT-In 180-day floor (§ 2) |
| BR1-05 the denied page | minor | **Accepted** (option 1): an auth-store flag set by `api.js` on any `network_denied`; `App.vue` shows the card; no new route or guard (§ 3) |
| BR1-06 which 403s are `denied_perm` | minor | **Accepted** (option 1): `require_perm_at` marks with `key@site:<id>`; business 403s fall back with the message as detail; the two Flask facts stated (§ 5.3, § 5.4) |
| BR1-07 worker lock and connection | minor | **Accepted** (option 1): one dedicated `get_local_db()` connection; non-blocking `GET_LOCK`; `LOCK_WORKER` in `local_db.py`; the worker runs `ensure_schema()`; stop flag between purge batches (§ 5.5) |
| BR1-08 overdue and `next_run` | minor | **Accepted** (option 1): pure `next_run`; `overdue` in the endpoint; badge and red failed count (§ 5.6) |
| BR1-09 loopback and IPv4-mapped | minor | **Accepted** (option 1): unwrap IPv4-mapped; loopback internal in code (§ 5.1) |
| BR1-10 test isolation | minor | **Accepted** (option 1): `_TABLES`; cache-clearing fixture; `require_network(dev_bypass=…)` factory tested directly (§ 3) |
| BR1-11 API and data details | nit | **Accepted**: `per_page`; `to` inclusive, `user` contains; truncation; PUT body as text with `strict=False`; the 1093 hint; named constants in `company_settings.py`; the change logged; the guard's limit in its message |
| BR1-12 docs and policy tests | nit | **Accepted**: Plan.MD § 3 row; CLAUDE.md records the deny-list departure; `TestPolicyStructure` checks `INTERNAL_ONLY_ROLES`; Keycloak.md `sid` line |

### Round 2 — `2-brief-review-r2.md` (Fable), answered 17-10-2026

No blocker or major finding; the loop ends here.

| Finding | Severity | Answer |
|---|---|---|
| BR2-01 outage after startup | minor | **Accepted**: the hook keeps its own 30-s back-off after a failed connect or insert; test with `get_pooled_db` patched (§ 5.4, § 3 Tests) |
| BR2-02 claim and handler in one transaction | minor | **Accepted**: three transactions — claim committed, handler, `mark_failed` on the committed attempts (§ 5.5) |
| BR2-03 `db_down` patches one reference | minor | **Accepted**: every `ensure_schema` reference patched; back-off test patches `get_pooled_db` (§ 3 Tests) |
| BR2-04 `auth_failed` detail | minor | **Accepted** (option 1): four fixed codes set on `g.access_detail` in the validator (§ 5.4) |
| BR2-05 harness details | nit | **Accepted**: factory signature and default in conftest; no factory → 401; `X-Real-IP: ""` for the missing-address test; `remote_addr` fallback off in tests (§ 3 Tests) |
| BR2-06 CORS `after_request` | nit | **Accepted**: the hook registered above `CORS(app)` (§ 3) |
| BR2-07 error 1093 reason | nit | **Accepted**: reason corrected; derived table kept (§ 5.6) |
| BR2-08 App.vue precedence | nit | **Accepted**: `networkDenied` before `authenticated` and `authError` (§ 3 Frontend) |
| BR2-09 small points | nit | **Accepted**: one overdue definition (5 min); `should_stop()` passed to handlers; first deploy after 02:30 runs at once; `GET_LOCK` each loop checks the lock (§ 5.5, § 5.6) |
