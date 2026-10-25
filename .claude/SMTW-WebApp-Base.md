# SMTW-WebApp-Base.md

Reference architecture for SMTW **Flask + Vue.js web apps** — stack, layout, and patterns proven in production. Synced
from `smtw-common` into every repo, so it is always the current standard; older repos may predate parts of it. Does not
apply to non-web repos (firmware, scripts, data tools).

- **Rules** live in `CLAUDE-COMMON.md` and win on conflict. This file covers *how* to implement.
- A repo's `CLAUDE.md` may record deliberate deviations from this file (e.g. "no RBAC — single user").
- **Maintained in `smtw-common`**: add learnings here as they come up, in any project, then push and sync.

---

## Stack

| Layer          | Choice                      | Notes                                                        |
|----------------|-----------------------------|--------------------------------------------------------------|
| Backend        | Flask                       | Blueprints per module                                        |
| Frontend       | Vue.js 3 + Vite + Bootstrap | Composition API                                              |
| Primary DB     | MariaDB                     | PyMySQL, `%s` placeholders (PostgreSQL variant noted inline) |
| External DB    | MS SQL (read-only source)   | pymssql, raw SQL (if applicable)                             |
| Auth           | Keycloak                    | OIDC + PKCE, token as Bearer header                          |
| JWT            | PyJWT (`pyjwt[crypto]`)     | Not python-jose — unmaintained                               |
| Job queue      | DB-backed `task_queue`      | Default; Redis only when latency/throughput demand it        |
| Scheduling     | APScheduler → `task_queue`  | Cron specs in Python; jobs enqueue rather than run inline    |
| Notifications  | Telegram Bot API            | Group-routed, sent via `task_queue`                          |
| Object Storage | MinIO (S3-compatible)       | Only for large media / multi-server; otherwise `data/`       |
| Dependency mgr | uv                          | Replaces pip + requirements.txt                              |
| Process mgr    | Gunicorn + separate worker  | Behind Nginx; the worker is its own process, not in Gunicorn |
| Containers     | Docker Compose              | One compose file per environment                             |

Choosing between the DB-backed queue and Redis: see § Background Worker / Job Queue Pattern.

---

## Project Layout

```
project/
├── backend/
│   ├── .venv/                  # Managed by uv (gitignored)
│   ├── app.py                  # Flask app entry point + blueprint registration + startup recovery
│   ├── config.py               # Loads secrets_*.py + env overrides, validates at startup — the only importer of secrets
│   ├── auth_utils.py           # Keycloak token validation + RBAC helpers: require_perm, has_perm, compute_permissions
│   ├── config_rbac.py          # RBAC policy: ROLES + PERMISSIONS dict
│   ├── company_settings.py     # Business config — checked in, not secrets
│   ├── local_db.py             # Owned DB: migration engine + connection pool + singleton lock
│   ├── db_helpers.py           # Shared DB utilities (row_to_dict, Decimal/datetime serialisation, etc.)
│   ├── storage.py              # MinIO/S3 helpers (bucket management, presigned URLs)
│   ├── <module>.py             # One Blueprint per feature module (thin — dispatch only)
│   ├── <module>_state.py       # Event-sourced modules: pure state projections
│   ├── <module>_recording.py   # Event-sourced modules: validation + write path
│   ├── task_queue.py           # DB-backed queue ops: enqueue, claim_next, mark_done, mark_failed
│   ├── task_handlers.py        # Dispatch table: task_type → handler(payload, conn)
│   ├── scheduled_tasks.py      # Cron registry: task_type + cron expression
│   ├── worker.py               # Separate process: APScheduler + task_queue drainer
│   ├── telegram_notifier.py    # send_alert(group_key, html) — enqueues via task_queue
│   ├── secrets_*.py            # Credentials — gitignored, hook-blocked
│   ├── example_secrets_*.py    # Templates — checked in, documents all required fields
│   ├── pyproject.toml            # Dependencies + project metadata (managed by uv)
│   ├── data/                   # File uploads — gitignored, organised per tenant
│   └── tests/
│       ├── conftest.py         # App fixture + role-specific test clients
│       └── test_*.py
├── frontend/
│   ├── src/
│   │   ├── stores/auth.js      # Keycloak init + reactive auth state (authenticated, userName, userPermissions)
│   │   ├── stores/<domain>.js  # Cached domain data: ensure<Domain>() fetches once per session
│   │   ├── api.js              # Fetch wrapper — injects Bearer token + tenant param
│   │   ├── components/layout/
│   │   │   └── AppSidebar.vue  # Permission-filtered nav
│   │   ├── components/<module>/ # Per-module components
│   │   └── views/              # One view per module
│   └── package.json
├── docs/
│   ├── Schema.md               # DB setup (dev/prod) + annotated schema — update as understanding grows
│   ├── schema.sql              # Full DDL — exported, never hand-edited
│   ├── <Area>-Domain.md        # Domain knowledge (terms, process, constraints)
│   └── Module-*.md             # One doc per major module: business rules, permissions, flows
├── tooling/
│   ├── dev/
│   │   ├── docker-compose.dev.yml     # Dev DB + other services
│   │   ├── replicate_prod_to_local.py # Prod → local copy for realistic test data (see § Dev Data Tooling)
│   │   └── prod_readonly.py           # Read-only prod SQL runner
│   ├── run-backend-tests.bat    # Wrappers Claude Code runs (CLAUDE-COMMON § Wrapper scripts)
│   ├── run-frontend-build.bat
│   ├── run-prod-query.bat
│   ├── common/
│   │   ├── .env-common          # GitHub PAT for sync (gitignored)
│   │   ├── release.env          # Release config: TEST_CMD, BUILD_SCRIPT, DEPLOY_SCRIPT (gitignored)
│   │   ├── sync_common.py       # Syncs shared files from smtw-common repo
│   │   ├── bump_ver.py          # Semantic version bumper (reads/writes VERSION file)
│   │   └── release.py           # Pre-release pipeline: test → bump → commit+tag → build → deploy
│   ├── build/                   # Dockerfiles + build scripts
│   └── probe.py                 # Quick DB inspection: probe.py TABLE [FIELD=VALUE]
├── VERSION                      # Current version (e.g. 0.3.12), managed by bump_ver.py
├── scratch/                     # Temp files, gitignored — screenshots, exports
└── .claude/
    ├── CLAUDE.md               # Project-specific Claude instructions (imports CLAUDE-COMMON.md)
    ├── CLAUDE-COMMON.md        # Shared conventions (synced from smtw-common)
    ├── SMTW-WebApp-Base.md     # This reference architecture (synced from smtw-common)
    └── skills/                 # Shared skills (synced) + project-specific ones (e.g. read-prod-data)
```

---

## Keycloak Token Validation Pattern

`auth_utils.py` validates the Bearer token against Keycloak's JWKS endpoint, using PyJWT.

### Token decode flow

1. Extract the Bearer token from the `Authorization` header.
2. Use `jwt.PyJWKClient` to fetch the signing key from the JWKS endpoint.
3. Decode with `algorithms=["RS256"]` and `verify_aud=False` — Keycloak sets `aud="account"`, not the client_id.
4. Check the `azp` (authorized party) claim matches the expected `client_id` — this replaces the audience check.
5. On decode failure, evict the cached JWKS client and retry once (handles signing-key rotation).
6. Extract roles from both `realm_access.roles` and `resource_access.<client_id>.roles`.

### Internal URL for the JWKS fetch (`_make_internal_url`)

The backend fetches the signing keys server-to-server. In production Keycloak sits behind a reverse proxy whose HTTPS
cert covers the public domain only; the backend on the same LAN can reach Keycloak by IP, but HTTPS to the IP fails the
cert check. So rewrite the public URL to the LAN IP on Keycloak's plain-HTTP port 8080 — for the JWKS fetch only:

```
https://sso.example.com/realms/<Realm>  →  http://<keycloak-lan-ip>:8080/realms/<Realm>
```

- `KEYCLOAK_HOST_IP` comes from `secrets_app.py` (via `config.py`). Empty = use the public URL (dev).
- Issuer validation still uses the public `realm_url` — only the JWKS fetch uses the internal URL.
- `require_auth(realm_url, client_id, internal_realm_url, dev_bypass=...)` is a factory returning a `before_request`
  handler.

### Admin realm roles

`ADMIN_REALM_ROLES` (e.g. `{"admin", "mspv-apps-admin"}`) maps Keycloak realm roles to the app-level `admin` role.
`mspv-apps-admin` is the org-wide admin role in Keycloak — a user holding it gets full admin access in every app
without being listed in `config_rbac.py` (the admin bypass lives in code — see RBAC Pattern).

### Dev auth bypass

`DEV_AUTH_BYPASS=1` skips Keycloak in local dev: `require_auth` synthesises a `g.user` with a default role (typically
`admin`). Guard it hard — `config.py` must refuse to start if the bypass is set outside a dev environment, rather than
relying on nobody setting it in production.

---

## RBAC Pattern

This is the core access-control architecture. Apply it to every project with authenticated users.

### Files

**`config_rbac.py`** — single source of truth for the access policy.

- Defines `ROLES` tuple, ordered most → least privileged.
- Defines `PERMISSIONS` dict: maps `'module:action'` string → tuple of granted role names.
- Route code references only permission key strings — never role names directly.
- Order permission entries to match sidebar nav order (readability).

**`auth_utils.py`** — three functions consumed by route code:

- `compute_permissions(roles)` — returns union of permission keys across all roles; used to build
  `g.user['permissions']` on login.
- `has_perm(perm_key)` — boolean; checks `g.user` roles against `PERMISSIONS`; used for inline field masking inside a
  route.
- `require_perm(perm_key)` — decorator; gates an entire route; returns 403 if check fails.

### Multi-role support

Users may hold multiple roles simultaneously (e.g. both `supervisor` and `cashier`).

- `g.user["roles"]` — list of all matched roles for the user.
- `g.user["role"]` — primary role (most privileged, by ROLES tuple order).
- Permissions are the **union** of all roles' permissions — a user with two roles gets capabilities of both.
- `has_perm` and `require_perm` check against the full role set, not just the primary role.

### Permission key design rules

The rules — `module:action` format, `('*',)` wildcard, `admin` bypass in code, fail-closed, three-level read
hierarchy — are defined in `CLAUDE-COMMON.md` § RBAC Pattern. Example of the read hierarchy for an employee module:

- `employee:read_basic` — id, name, department
- `employee:read` — plus contact info, salary, dates
- `employee:read_senior` — plus Aadhaar, demographic reports

### How `require_perm` works

```
decorator logic (pseudocode):
  roles = g.user.roles
  if 'admin' in roles      → pass through
  if perm is ('*',)         → pass if any role is a known ROLE
  if any role in perm tuple → pass through
  else                      → return 403
```

`admin` in `roles` includes users mapped from Keycloak admin realm roles — see Keycloak Token Validation § Admin
realm roles.

### Applying permissions to routes

- `@require_perm(key)` goes immediately after `@app.route` / `@bp.route` — always.
- Use `has_perm(key)` inside a route to conditionally mask individual fields rather than blocking the entire response.
- The `/api/auth/me` endpoint returns `role`, `roles`, and `permissions` list to the frontend. Permissions are computed
  server-side from the roles — the frontend never derives them itself.

### Frontend auth pattern

`stores/auth.js` holds reactive refs: `authenticated`, `userName`, `userRole`, `userPermissions`.

Init sequence:

1. Fetch Keycloak config from `/api/auth/config`.
2. Init Keycloak with `login-required` and PKCE.
3. On success, call `/api/auth/me` with the Bearer token.
4. Store `role` and `permissions` from the response into the reactive refs.

The frontend never parses the Keycloak token for role or permissions — it always comes from `/api/auth/me`.

### Sidebar visibility

Each nav item declares the minimum permission required to show it.

- Single perm: item visible if `userPermissions` includes that key.
- Multiple perms (OR): item visible if `userPermissions` includes **any** of the keys. Use this when a module serves two
  different user groups (e.g. overtime module serves both `overtime:read` and `petty_sales:read` users).

Rule: use the **lowest permission** a user needs to see meaningful content in that module. Not the highest.

---

## Internet Exposure Pattern

When an app is reachable from outside the LAN (e.g. supervisors on mobile data), three pieces work together: the
backend must see the **real client IP**, a **network gate** keeps internal-only roles off the internet, and an **access
log** records who reached the API from where. Reference: VelKilnMaster `access_control.py`, `access_log.py`,
`tooling/build/nginx.conf`.

### Real client IP behind proxies

Behind the usual chain **front reverse proxy → app's nginx container → backend**, every request arrives from a proxy
address unless each hop passes the real one on.

**The trap (VelKilnMaster, Sept 2026):** the app's nginx set `X-Real-IP $remote_addr` — but `$remote_addr` was the
front proxy (10.24.0.18), so every client looked internal and the network gate silently let the internet in. Nothing
failed; it just never refused anyone.

**Fix — in the app's nginx**, accept `X-Forwarded-For` only from the front proxy's range:

```nginx
set_real_ip_from 10.24.0.0/23;      # front proxy range — the only hop allowed to vouch for the client
real_ip_header   X-Forwarded-For;
real_ip_recursive on;               # skip trusted hops from the right; first untrusted address = client

location /api/ {
    proxy_set_header X-Real-IP       $remote_addr;   # now the real client
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

- **Backend reads `X-Real-IP` only.** The first entry of `X-Forwarded-For` is whatever the client sent — trivially
  forged. `set_real_ip_from` + `real_ip_recursive` is what makes the address trustworthy; a client outside the trusted
  range cannot spoof it.
- `set_real_ip_from` must match the front proxy's actual range — keep it in step with the network zone config.
- Parse with `ipaddress`; on failure log it and treat the client as **external** (fail closed).
- **Verify after every deploy that touches proxies**: the access log must show real, varied client addresses, not the
  proxy's. A gate that never refuses looks exactly like a gate that works.

### Network gate by role

`access_control.py` exports `require_access()`, a `before_request` factory registered **after** `require_auth` (it
needs `g.user`):

- Permission `access:wan` in `config_rbac.py` lists the roles allowed from anywhere; everyone else must come from an
  internal network. Route code never sees this — it is a gate, like auth.
- Internal ranges are a comma-separated CIDR list in the `app_settings` table (`internal_networks`), editable in
  Settings without a deploy, cached in-process for 5 min.
- **The ranges mirror the front proxy's zone lists** (office, app zone, VPN pools, remote sites such as SSVT): a
  range left out makes those users external, and an internal-only role on the VPN is refused. Check the list against
  the devops repo's `zone-*.list` files when it is first set and whenever a zone is added.
- Admin bypasses; public paths (`/api/auth/config`, `/api/version`) and the dev auth bypass skip the gate.
- Refusal: 403 with a message saying an internal connection is required, plus a log warning naming user, role and IP.
- Granting `access:wan` to a role is a business decision (who may work from outside) — record the date and reason in
  a comment next to the grant.

### Access log

Answers "who reached the API, from where, and were they let in?" — without a row per request.

- **One row per sighting, not per request**: the first time a Keycloak session (`sid` claim) is seen from an IP, again
  when it moves to another IP (Wi-Fi → mobile data), and once per distinct refusal.
- **Outcomes**: `ok`, `auth_failed`, `denied_network`, `denied_perm`. Each gate marks its own refusal on `g`
  (`g.access_outcome`, `g.access_detail` — the failure reason or permission key); a bare 401/403 status is only the
  fallback. Validation 4xx and 5xx on an authenticated request still count as `ok` — the user did reach the API.
- **`after_request` hook**, registered before the other `after_request` hooks so Flask runs it last and sees the final
  status. Wrapped in try/except — a logging failure must never break the request.
- **One row per sighting per day, enforced by the database** (rule revised 18-10-2026 after 23 days of VelKilnMaster
  production data). The sighting key is `(outcome, session or username, IP, detail)`; the row carries
  `sighting_day` (the IST date) and `sighting_hash` (SHA-1 of the key), with a **unique index on
  `(sighting_hash, sighting_day)`**. The hook inserts with `INSERT IGNORE` (MariaDB) or `ON CONFLICT DO NOTHING`
  (PostgreSQL) and treats a rejected insert as "already seen". A small in-process cache in front of it only saves
  the insert attempt for repeats within 10 min; it is not the rule.
  - *Why the database and not the cache:* with three Gunicorn workers, each holding its own cache, three parallel
    requests from one phone at page load gave three identical rows at the same second, and the 10-minute window
    gave an active user a fresh row every 10 minutes — about 400 rows a day, 9,500 in 23 days, for twelve users.
    The question the log answers, "which addresses did each session come from", was buried under repeats.
  - The unique key is race-free across workers and survives restarts; a session seen again from the same address
    the next day gets a new row, which is the intended record. The table stays append-only (no updates).
  - **VelKilnMaster (Sept 2026) still has the cache-only dedupe** and is to be brought in line with this rule.
- **Columns**: `ts`, `username`, `role`, `session_id`, `client_ip`, `is_internal`, `outcome`, `method`, `path`, `sighting_day`, `sighting_hash` (the unique pair above),
  `user_agent`, `detail`; indexes on `ts DESC` and `(username, ts DESC)`. `ts` follows the timezone policy
  (`TIMESTAMP`/`DATETIME`, IST).
- **Retention**: a scheduled worker task deletes rows older than `ACCESS_LOG_RETENTION_DAYS` (`company_settings.py`).
- **Viewer**: Settings › Access log, paginated, filters for user, date range, external-only and denials-only; permission
  `access_log:view` for the people who own the security question (manager, IT).
- **Reading it** (what VelKilnMaster's log showed): "denials only" is mostly internet scanners probing `/api/.env`,
  `/api/.git-credentials` and the like, each a 401 — the login gate holding, and worth a glance now and then. A
  `denied_perm` that repeats for one role on one path every few minutes is a **frontend bug**: a page polls an
  endpoint that role cannot see, and the UI swallows the 403. Fix the UI; don't widen the permission.
- Classification and dedupe are pure (`classify_outcome`, `SightingCache` with an injectable clock) and unit-tested.

---

## Multi-Tenancy Pattern

When a single deployment serves multiple companies/tenants:

- The active tenant is selected in the UI (topbar dropdown) and stored client-side.
- Every API request carries the tenant identifier as a query parameter (e.g. `?company=ACME`).
- `@app.before_request` reads this parameter, validates it, and sets up the tenant context for the request.
- All DB connections, file paths, and local DB references use the tenant identifier to scope data.
- File storage is organised as `data/<TENANT>/` — never mix tenant data in a flat directory.
- Local (owned) DBs are named `<appname>_<TENANT>` — one DB per tenant, same schema.
- The tenant list is fetched from a central source (e.g. a config file or master DB) at startup.
- `g.company` (or equivalent) carries the active tenant through the request lifetime.

---

## Flask Blueprint Pattern

- One `.py` file per feature module, each exporting a Blueprint.
- All blueprints registered in `app.py` at startup.
- Auth middleware (`@app.before_request`) validates the Bearer token, maps to role, populates `g.user` with `username`,
  `name`, `role`, `roles`, `permissions`.
- Every non-trivial route has `@require_perm` — no unguarded routes except `/api/auth/config`, `/api/auth/me` and
  `/api/version`.
- Keep blueprints **thin**: route dispatch only. Business logic lives in pure functions (CLAUDE-COMMON § Pure core,
  thin shell) — for event-sourced modules, `<module>_recording.py` and `<module>_state.py`.

---

## DB Connection Pattern

### Per-request connection from a pool, cached on `g`

```python
def get_db():
    if "db" not in g:
        g.db = get_pooled_db()
    return g.db

@app.teardown_appcontext
def _close_db(exc):
    conn = g.pop("db", None)
    if conn is not None:
        return_pooled_db(conn)
```

- One connection per request, borrowed from a pool and returned in teardown — never leaked, never stored in module
  globals or reused across requests.
- Pool: PyMySQL has no built-in pool — use a small pool helper (e.g. DBUtils `PooledDB`); psycopg2 has
  `psycopg2.pool.SimpleConnectionPool`. Size `maxconn >= gunicorn workers + worker process + a few`; start at 10 on a
  single server and raise only on observed exhaustion (the slow-request logger shows it).
- Pooled connections die after long idle periods — detect and reconnect on first use (CLAUDE-COMMON § Idle connections).
- Several databases (e.g. owned DB + read-only ingest DB) → **separate pools**, one per config.
- Background threads and the worker process hold their own dedicated connections, not pool ones.
- Cursors: `with conn.cursor() as cur:`. MS SQL (pymssql): `conn.cursor(as_dict=True)`, always in try/finally.
- Rows are plain dicts (PyMySQL `DictCursor`, psycopg2 `RealDictCursor`) — no ORM objects. **`cur.fetchone()[0]`
  fails** on a dict cursor; always use the column name: `cur.fetchone()["version"]`.
- Cache other expensive per-request computations on `g` too (e.g. `g.zones_cache`) — cleared automatically at request
  end.

### Timezone policy

**All datetime values in the database are IST (naive). Servers and containers stay UTC.**

| Layer                    | Timezone   | Mechanism                                               |
|--------------------------|------------|---------------------------------------------------------|
| Server OS / Docker host  | UTC        | Default, untouched                                      |
| Docker containers        | UTC        | No `TZ` env — keeps logs aligned with host              |
| MariaDB server (global)  | UTC        | Default, untouched                                      |
| MariaDB sessions (app)   | **IST**    | `init_command="SET time_zone = '+05:30'"` on every conn |
| DB column type           | `DATETIME` | Naive — stores literal value, no auto-conversion        |
| DB stored values         | **IST**    | `NOW()`, `CURRENT_TIMESTAMP` use session TZ → IST       |
| API responses            | IST+offset | `row_to_dict()` appends `+05:30` to datetime strings    |
| Frontend display         | As-is      | `DD-MM-YYYY HH:MM`, no conversion, no TZ suffix         |
| Python/container logging | UTC        | From host clock — logs ≠ business data                  |
| Redis / in-process delays| Unix epoch | `time.time()` — timezone-agnostic                       |

**The boundary:** IST lives inside the DB and everything downstream (API, frontend). UTC lives outside (server OS,
container logs, epochs). The session setting in `local_db.py` (applied to every pool connection) is the single point
where the switch happens.

**Do NOT set `TZ` on Docker containers** — it splits log timezones between host (UTC) and container (IST), making
incident correlation painful. All users are in one timezone; there is no need for multi-TZ support.

**Why `DATETIME` not `TIMESTAMP`**: `DATETIME` stores the literal value without conversion. Since all app connections
set the session to IST, all stored values are consistently IST. MariaDB `TIMESTAMP` auto-converts to/from UTC on
storage — unnecessary complexity when every connection agrees on timezone.

**Known gap**: adminer, pgAdmin and manual SQL connections don't get the session setting — they see UTC. Not a data
risk; the IT incharge knows to account for the +05:30 offset when browsing.

**PostgreSQL / TimescaleDB variant** — same policy, different mechanism:

- Session: `SET timezone = 'Asia/Kolkata'` on every pool connection (or `options='-c timezone=Asia/Kolkata'` in the
  psycopg2 connect call) — the equivalent of MariaDB's `init_command`.
- Column type: `TIMESTAMP` (without time zone), not `TIMESTAMPTZ` — same reason as `DATETIME` over MariaDB `TIMESTAMP`:
  store the literal IST value, no conversion, when every connection agrees on the timezone.

---

## Local DB Migration Pattern

- `local_db.py` owns the migration engine and the connection pool.
- `_MIGRATIONS` is an ordered list of `(version, description, [sql_statements])` tuples.
- Each entry is a list of individual SQL strings (not a single semicolon-separated string).
- `init_db(config)` is called at startup and applies any pending migrations automatically.
- Never edit or delete old migration entries — always append new ones.
- Use `ADD COLUMN IF NOT EXISTS` and `CREATE TABLE IF NOT EXISTS` for defensive migrations that may be applied to
  databases in varying states.
- For multi-tenant: each tenant gets its own database, named with a consistent prefix (e.g. `appname_TENANTID`).
- Tests use a separate prefix (e.g. `appname_test_`) and drop test DBs on exit.

### Singleton via DB lock

Gunicorn workers boot concurrently, so every worker calls `init_db`. Guard it with a DB-level named lock so only one
runs migrations while the others wait:

```python
# MariaDB: GET_LOCK(name, timeout) blocks up to `timeout` seconds; returns 1 when acquired
cur.execute("SELECT GET_LOCK('appname_migrations', 60) AS got")
if cur.fetchone()["got"] == 1:
    try:
        _apply_migrations(conn)
    finally:
        cur.execute("SELECT RELEASE_LOCK('appname_migrations')")

# PostgreSQL: pg_advisory_lock(<MIGRATION_LOCK_ID>) blocks; pg_advisory_unlock(<MIGRATION_LOCK_ID>) releases
```

Once the waiting workers get the lock they find no pending migrations and carry on. The same lock — held, with a
non-blocking try (`GET_LOCK(name, 0)` / `pg_try_advisory_lock`) — keeps any singleton to one instance: the APScheduler,
the queue drainer, background monitor threads. A connection-held lock is released automatically if its process dies.

### Advisory locks on pooled connections (PostgreSQL)

Session-level `pg_advisory_lock` is held by the **connection**, not the request. Pooled connections run in autocommit
and are reused, so a lock that isn't explicitly released survives into every later request on that connection.

**The incident (VelKilnMaster, June 2026):** a request-path lock was taken on key 2 but unlocked on key 1 (a no-op).
Key 2 stayed held forever; every later request needing it blocked, each holding a pooled connection. ~88 stuck
connections exhausted `max_connections` on a DB instance shared with other apps, and the midnight scheduled job failed
to enqueue.

- **Request path: prefer `pg_advisory_xact_lock(key)`** inside an explicit transaction — released automatically at
  commit/rollback, nothing to forget.
- If a session lock is unavoidable, acquire it **immediately before** `try:` and release it in `finally:`, using the
  same named constant for lock and unlock — never two literals.
- **Lock-ID registry**: define every key as a named constant in one place (e.g. `local_db.py`:
  `LOCK_MIGRATIONS = 1`, `LOCK_SENSOR_MONITOR = 8001`, `LOCK_WORKER = 8002`, …) so keys can't collide or drift.
- Singletons (scheduler, drainer, monitor thread) keep session locks on their **own dedicated connection** — that's
  the one case where holding a lock for the process lifetime is the point.
- **Diagnose**: query `pg_stat_activity` *as the app role* (a read-only user can't see other roles' rows) and look for
  `state = 'active'` with `wait_event = 'advisory'` piling up. Immediate relief: restart the backend (drops pooled
  connections) or `pg_terminate_backend` the stuck ones.

### Migration squashing

When the migration list grows long (20+), squash all migrations into a single v1 entry containing the full schema as
`CREATE TABLE IF NOT EXISTS` statements. This simplifies fresh installations. But do this only after explicit
confirmation,
as different instances of dev, staging, deploy need to be considered.
After squashing:

- Dev databases must be recreated (drop + recreate). Document this clearly.
- Incremental migrations (v2+) continue to use `ALTER TABLE`.
- Version numbers need not be contiguous (e.g. v1, v2, v3 … v13, v15 is fine if v14 was dropped during squash).

---

## API Response Conventions

Consistent response shapes across all endpoints:

- **Success, single object:** `jsonify(obj_dict)` — flat dict
- **Success, list:** `jsonify({'items': [...], 'total': N})` — always wrap lists, never return a bare array
- **Success, paginated list:** `jsonify({'items': [...], 'total': N, 'page': P, 'per_page': PP})`
- **Not found:** `jsonify({'error': 'descriptive message'}), 404`
- **Forbidden:** handled automatically by `require_perm` → `jsonify({'error': 'Forbidden...'}), 403`
- **Bad request:** `jsonify({'error': 'reason'}), 400`
- **Server error:** `jsonify({'error': 'Internal error'}), 500` — never leak stack traces to the client

Dates: always serialise to ISO 8601 string (`YYYY-MM-DD`) before returning — never return raw `datetime` objects.
Decimals: Flask's `jsonify` handles `Decimal` by serialising as string — this is safe and avoids floating-point
precision loss. The frontend should use `Number()` or `parseFloat()` when it needs to do arithmetic. Avoid `float()`
casts on the backend — they introduce imprecision. Note: raw `json.dumps` (without Flask) will crash on `Decimal`.

---

## Business Settings Pattern

Separate from secrets and env vars, `company_settings.py` holds business configuration that:

- Is checked into version control (not sensitive).
- Changes rarely (when external system configuration changes, not per deployment).
- Is imported directly by modules that need it.

Examples: ERP supplier groups, item groups, Tally company name, purchase ledger lists, payment limits, cash account
names. Keep it flat — simple constants, no classes or complex structures.

---

## Object Storage Pattern (MinIO / S3)

For file storage that exceeds simple on-disk needs (large media, multi-server deployments):

- Use MinIO (self-hosted, S3-compatible) with the `minio` Python client.
- **Bucket naming**: monthly rotation (e.g. `modulename-YYYYMM`) keeps bucket sizes manageable.
- **Object key pattern**: `{entity_id}/{timestamp}_{file_id}.{ext}` — groups files by entity.
- **Frontend access**: presigned URLs with a sensible expiry (e.g. 7 days). Never expose raw credentials.
- **Storage helper** (`storage.py`): `ensure_bucket()` creates the current month's bucket if missing;
  `get_presigned_url()` generates download URLs.
- Store the MinIO object path in the DB, not the presigned URL — URLs expire but paths are permanent.
- Dev port: avoid port 9000 if running Tally or other services that use it — use 9100 instead.

---

## Background Worker / Job Queue Pattern

For async and scheduled work (AI calls, external system sync, PDF generation, notifications, cron jobs). The worker is
always a **separate process** (`worker.py`), never inside Gunicorn.

### Choosing a queue

**Default: a DB-backed `task_queue` table.** One less service to run and monitor; work survives worker restarts
naturally; "what's pending?" is a plain SELECT; and a task can be enqueued in the same transaction as the business data
that caused it. That fits internal apps at this scale (CLAUDE-COMMON § Right-sized for internal apps).

**Redis** only when latency or throughput genuinely demand it — sub-second pickup or very high job volume.

### DB-backed queue (default)

Table (MariaDB; PostgreSQL: `SERIAL`, `JSONB`, `TIMESTAMP`, and a partial index `WHERE status = 'pending'`):

```sql
CREATE TABLE IF NOT EXISTS task_queue (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    task_type     VARCHAR(50) NOT NULL,
    payload       JSON,
    status        VARCHAR(20) NOT NULL DEFAULT 'pending',   -- pending | running | done | failed
    attempts      INT NOT NULL DEFAULT 0,
    max_attempts  INT NOT NULL DEFAULT 3,
    scheduled_for DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    locked_until  DATETIME NULL,
    last_error    TEXT,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at  DATETIME NULL,
    INDEX idx_task_queue_due (status, scheduled_for)
);
```

- **`task_queue.py`**:
  - `enqueue(task_type, payload, scheduled_for=None)` — INSERT, return the id. Pass the caller's connection to enqueue
    inside the business transaction.
  - `claim_next(conn, worker_id)` — `SELECT … WHERE status = 'pending' AND scheduled_for <= NOW() … LIMIT 1 FOR UPDATE
    SKIP LOCKED`, then set `status = 'running'` and `locked_until`. `SKIP LOCKED` needs MariaDB 10.6+ (PostgreSQL 9.5+).
    `locked_until` lets a task claimed by a crashed worker become claimable again.
  - `mark_done(conn, task_id)` / `mark_failed(conn, task_id, error, retry_delay)` — on failure, store `last_error`; if
    `attempts < max_attempts`, set back to `pending` with `scheduled_for = now + retry_delay`, else `failed`.
- **`task_handlers.py`** — dispatch table `task_type → handler(payload, conn)`. Handlers are plain functions that take a
  connection and commit nothing: the worker owns the transaction. Validate the payload first — log and fail malformed
  tasks, never crash the worker.
- **`worker.py`** — launched as `python worker.py`:
  1. Take the singleton lock (§ Local DB Migration Pattern › Singleton via DB lock) so only one worker instance drains
     the queue, even with several nodes.
  2. Start APScheduler. Scheduled jobs (`scheduled_tasks.py`: task_type + cron expression) **enqueue** a task at cron
     time rather than doing the work inline, so scheduled work gets the same retries and history as everything else.
  3. Drain loop: `claim_next` → dispatch → `mark_done` / `mark_failed` with retry backoff.
- **No separate cron-log table.** `task_queue` already records every scheduled run as a row — filter by `task_type` +
  `created_at` for history.

### Redis queue (when latency or throughput demand it)

#### Architecture

- **Queue module** (`<module>_queue.py`): defines constants (`QUEUE_KEY`, `STATUS_PREFIX`, `RETRY_KEY`, `MAX_RETRIES`,
  `RETRY_DELAY`) and `enqueue_*()` functions that LPUSH JSON job payloads to Redis.
- **Worker process** (`<module>_worker.py`): uses `BRPOP` on the queue key with a short timeout (e.g. 5s) to stay
  responsive to shutdown signals.
- **Job payload**: JSON dict with a `type` field to dispatch to the correct handler, plus required IDs. Always validate
  required fields before dispatching — log and skip malformed jobs instead of crashing.

#### BRPOP vs BLMOVE

Plain `BRPOP` is sufficient when the DB tracks sync state (the four columns below). If the worker crashes after popping
but before processing, the job is lost from Redis — but the DB still shows `synced = 0`, so the job is recoverable.
`BLMOVE` (atomic pop + push to a processing list) adds complexity without real benefit when the DB is the source of
truth. Reserve `BLMOVE` for queues where Redis is the *only* record of work to do.

#### Retry mechanism

- On failure, increment `attempt` counter in the job dict.
- If `attempt < MAX_RETRIES`: add to a Redis sorted set (score = `time.time() + RETRY_DELAY`).
- Worker main loop calls `_promote_retries()` each iteration — moves due jobs (score ≤ now) back to the main queue.
- After `MAX_RETRIES`: mark as permanently failed in the DB.

#### Worker heartbeat

- Set a Redis key with TTL (e.g. `worker:heartbeat` with 30s TTL) on each loop iteration.
- Health checks (admin diagnostics page) read this key to show worker status.

### Automatic retry: internal tasks only

Whichever queue: only auto-retry idempotent, system-internal tasks (e.g. AI report generation). Never auto-retry
external system syncs where humans may have created manual entries as a workaround — on the DB-backed queue, enqueue
those with `max_attempts = 1`. See below.

### Recovery: automatic vs manual

Choose the right recovery strategy based on whether the operation is **safely re-runnable**:

**Automatic recovery** (startup re-enqueue) — for tasks where the system can verify no duplicate exists:

- AI report generation: `LEFT JOIN weighment_ai_reports ... WHERE r.id IS NULL` — if no report row exists, it's safe
  to re-enqueue. No external side effects.
- Internal state updates: the system owns both sides and can check idempotency.

**Manual recovery** (admin tools only) — for external system syncs (e.g. Tally, ERP):

- The system **cannot know** if a human created a manual entry in the external system as a workaround while the sync
  was failing. Automatic re-enqueue risks duplicate vouchers/invoices that are invisible to the system.
- Instead: make failures highly visible (persist error to DB, show on transaction detail), and provide admin tools
  for IT incharge to review failures, enquire, and manually re-queue after confirming no manual entry was made.
- Never auto-recover these at startup — even rate-limited re-enqueue is wrong because the duplication risk is
  per-job, not per-volume.

### Job status tracking in DB

Add four columns to the entity table for each external system sync:

| Column           | Type       | Purpose                              |
|------------------|------------|--------------------------------------|
| `synced`         | TINYINT(1) | Whether sync completed successfully  |
| `voucher_number` | VARCHAR    | External reference returned on sync  |
| `synced_at`      | DATETIME   | Timestamp of successful sync         |
| `sync_error`     | TEXT       | Last error message (NULL on success) |

### Background monitoring daemon

For periodic checks lighter and more frequent than a scheduled task (e.g. a sensor poll every 15 s):

- Start a `threading.Thread(daemon=True)` in `app.py` after DB init, guarded by the singleton lock so only one gunicorn
  worker runs it.
- The thread owns its own DB connection — never shares one with request handlers.
- Use a `threading.Event` for graceful shutdown.
- Persist alert state in the DB so a restart doesn't re-fire pending alerts.

Anything less frequent or heavier belongs in the scheduler → `task_queue` instead.

---

## External System Integration Pattern

When integrating with external systems (ERPNext, Tally, etc.):

### Proxy pattern for legacy protocols

If the external system speaks a non-HTTP protocol or needs network isolation, put a small proxy in front:

- Go is a good choice for simple HTTP→protocol proxies (single binary, easy to deploy).
- Authenticate with a pre-shared key (`X-API-Key` header).
- Endpoints: `/health` (no auth, for monitoring), `/api/*` (authenticated passthrough).
- The proxy is dumb — no business logic. All parsing and validation happens in the Python worker.

### Approval-time field freezing

When a transaction must be synced to an external system after approval:

- Resolve and store all external references (ledger names, amounts, account IDs) at approval time, not at sync time.
- This prevents issues where master data changes between approval and sync.
- Store frozen values in dedicated columns (e.g. `tally_ledger_name`, `tally_invoice_total`).

### Auto-enqueue on status transition

- When the backend route changes an entity's status, enqueue the sync job in the same request.
- The worker picks it up asynchronously — the route returns immediately.
- Never make the user wait for external system calls in a synchronous request.

---

## Telegram Notification Pattern

Centralise in `telegram_notifier.py`:

- `TELEGRAM_GROUPS` dict in `company_settings.py`: `{"ops": {"name": ..., "description": ..., "chat_id": ...}}`. The
  bot token is a secret (`secrets_app.py`).
- `send_alert(group_key, html_message)` validates the group key and enqueues a `telegram_send` task. The Bot API call
  happens in the worker, so a slow or failed send never blocks a request.
- The handler retries on 5xx and respects `Retry-After`. Mark the task done only on a verified successful send.
- Put a `threading.Lock` around any in-process alert aggregation, so concurrent threads (e.g. a monitoring daemon) can't
  send duplicates.
- **Route by group, not by user**: one Telegram group per audience (engineers, supervisors, ops). Joining the group is
  the subscription — no user-management work in the app.

---

## Multi-Step Approval Workflow Pattern

For processes requiring multiple people to act sequentially (e.g. bank payment runs):

### Status design

```
draft → for_verification → verified → in_progress → complete
                              ↘ rejected (terminal)
```

- Each status transition is a separate API call with its own permission.
- Rejected is terminal — don't allow resubmission of the same entity. Force creation of a new one. This keeps the audit
  trail clean.
- Draft entities can be hard-deleted. Once submitted for verification, only status transitions are allowed.

### Permission mapping

Map each transition to a distinct permission:

| Transition              | Permission          | Role     |
|-------------------------|---------------------|----------|
| Create draft            | `create_bank_run`   | incharge |
| Submit for verification | `create_bank_run`   | incharge |
| Verify / Reject         | `verify_bank_run`   | approver |
| Execute                 | `execute_bank_run`  | incharge |
| Complete                | `complete_bank_run` | approver |

### Soft holds

When an entity is in an active workflow (draft through in_progress), its amounts are "soft-held" — reserved against
the parent entity's balance but not yet committed. Released on rejection or on completion when marked failed.

---

## Phase Completion Pattern

When an entity has independent sub-phases that can be done in any order:

- Use boolean flags (e.g. `gross_complete`, `tare_complete`) rather than a single status field.
- Each phase has its own "Done" button that locks the phase's fields and records who completed it.
- The entity can only advance to the next status when all required phases are complete.
- Backend auto-sets the supervisor/actor from `g.user["name"]` when a phase is completed — never trust the client.
- Auto-recalculate derived fields when dependencies change (e.g. `weighment_weight = gross - tare`).

---

## Event-Sourced Module Pattern

For domains where history matters (operation logs, audits, state machines):

- **The immutable event log is the source of truth.** Never UPDATE or DELETE events — add a `voided` flag and filter on
  it.
- **State projection** — `<module>_state.py` replays events to derive current status. Projections are pure functions
  (CLAUDE-COMMON § Pure core, thin shell), so they unit-test easily and can be cached per request on `g`.
- **Write path** — `<module>_recording.py` owns it: `record_event(...)` validates (business rules, blocking predecessors,
  state preconditions), inserts, then triggers downstream effects (counters, notifications).
- **Derived counters** (e.g. a per-entity round number that advances on a specific event) are bumped in exactly one
  place — never duplicated across call sites.

**Event traps** (optional): operators attach a one-shot reminder to `(entity, future_state, event_type)`. When a
matching event is recorded, send the notification and mark the trap fired — only if the send succeeded, so the next
matching event retries.

---

## Serial Number Generation

For human-readable sequential identifiers:

- Format: `YYYY-MM-DD-NNN` (e.g. `2026-03-06-001`) — date prefix + daily sequence; or `<CODE>-<seq>` when the serial
  belongs to a type (e.g. a mould code). For batch entities: `PREFIX-YYYY-MM-NNN` (e.g. `PR-2026-03-001`).
- Generate server-side from a **counter row locked `FOR UPDATE`**, not `MAX(serial) + 1`. Two concurrent requests both
  read the same `MAX` and collide — the UNIQUE index turns the race into a 500, it doesn't prevent it.
- The counter lives on the row that owns the sequence (`next_serial` on the type row; a `serial_counters(scope, day)`
  row for daily sequences, inserted on the first of the day with `ON CONFLICT DO NOTHING`). In one transaction:

  ```sql
  SELECT next_serial FROM mould_types WHERE id = %s FOR UPDATE;   -- concurrent allocators wait here
  UPDATE mould_types SET next_serial = next_serial + %s WHERE id = %s;
  -- insert the rows with serials first .. first + count - 1, then commit
  ```

  Allocating a block of `count` serials in one lock covers multi-row entries (e.g. N pieces from one mix).
- Never reuse a serial: voiding the entity keeps its number. The counter only moves forward — if it can be edited (e.g.
  seeding past numbers already in use before go-live), reject any value below the current one.
- Store as `VARCHAR(32)` with a UNIQUE index — a safety net, not the allocation mechanism.
- Reference: VelKilnMaster `casting.py` (piece serials).

---

## File Upload Pattern

- Uploaded files are stored on disk under `data/<TENANT>/<module>/` — or in MinIO for larger deployments.
- Validate file type (check magic bytes or extension whitelist) and enforce a size limit on every upload route.
- Store files with a system-generated name (e.g. `<empid>.jpg`) — never trust the client-supplied filename.
- Serve files through a dedicated authenticated route (e.g. `/api/photo/<id>`) that checks permissions — never expose
  the `data/` directory via static file serving.
- `data/` is gitignored; document the expected directory structure in CLAUDE.md.
- Max upload size should be configurable at runtime (store in `app_settings` table, not hardcoded).

---

## Secrets Pattern

- Credentials live in `secrets_*.py` files — gitignored and Claude Code hook-blocked.
- A corresponding `example_secrets_*.py` is checked in to document all required fields with placeholder values.
- Never name a secrets file `secrets.py` — that name conflicts with Python's stdlib `secrets` module.
- Claude Code hook blocks Read/Edit/Write on files matching `secrets_*.py`.
- Route all reads through `config.py` — modules import from `config`, never from `secrets_app` directly. One audit
  point, easy env-var overrides, and required fields validated at startup.

---

## Environment & Configuration

Three tiers of configuration, from most to least sensitive:

| Tier               | File / Source         | Git status  | Examples                                  |
|--------------------|-----------------------|-------------|-------------------------------------------|
| Secrets            | `secrets_*.py`        | gitignored  | DB passwords, API keys, SSO client secret |
| Business settings  | `company_settings.py` | checked in  | Supplier groups, ledger lists, limits     |
| Operational config | Environment variables | `.env` file | Debug flag, host, port, data directory    |

- `debug=True` in development only — never in production. Hardcoding it is a security risk.
- The Vite build injects the app version from the root `VERSION` file as `__APP_VERSION__` — display it in the sidebar
  footer for easy version identification.

---

## Observability

### Slow-request logger

Add from day one — negligible cost, and it pays off the first time gunicorn starts SIGKILLing workers or the pool runs
dry. Flags any request slower than `SLOW_REQUEST_MS` (env var, default 3000):

```python
@app.before_request
def _start_timer():
    g._req_start = time.monotonic()

@app.after_request
def _log_slow(response):
    elapsed_ms = int((time.monotonic() - g._req_start) * 1000)
    if elapsed_ms >= SLOW_REQUEST_MS:
        logger.warning("SLOW %d ms  %s %s  status=%s",
                       elapsed_ms, request.method, request.path, response.status_code)
    return response
```

---

## Versioning & Release

### Version source of truth

The `VERSION` file at the project root holds the current version (e.g. `0.3.12`). All tooling reads from and writes to
this file. Semantic versioning: `MAJOR.MINOR.PATCH`.

- PATCH: bug fixes, small adjustments
- MINOR: new features, backward-compatible
- MAJOR: breaking changes or large rewrites

The Vite build reads `VERSION` at build time and injects it as `__APP_VERSION__`. The `version` field in `package.json`
is not the app version.

### Stale bundle detection

Every SPA must tell an open tab when a newer build is deployed — a tab left open for days otherwise runs old JS against a new API, breaking silently. Reference implementation: VelKilnMaster commit `939a732`.

- **`index.html` must be served `Cache-Control: no-cache`** — it's the only file whose URL doesn't change between builds, so a stale copy pins the browser to the old (immutable, long-cached) hashed bundle. `no-cache` = revalidate, not "don't store"; the ETag keeps it a 304. In nginx, `add_header` stops inheriting once redefined in a `location`, so repeat the security headers there.
- **Root `VERSION` file is the single source of truth** — the bundler bakes it in at build time (Vite: `define: { __APP_VERSION__ }`); the backend serves it from a public, DB-free `GET /api/version` → `{"version": "..."}`. Read the file with a fallback to `"unknown"`, try both dev and container paths, and `COPY VERSION` into the backend image.
- **Endpoint must be unauthenticated** — a client on a stale bundle may have a broken token, and the check must still work.
- **Detection: a pure `isOutdated(ours, theirs)` function**, unit-tested with no network or DOM. Conservative — anything ambiguous (non-string, empty, `"unknown"`, missing local version) means "no update", since a false positive nags forever. Compare by inequality, not ordering: a rollback is still a bundle the client isn't running.
- **Poll cheaply**: on tab foregrounding (`visibilitychange`) plus a slow interval (~15 min) while visible; `cache: "no-store"`; fail silently when offline; latch the flag and stop polling once found.
- **Prompt, never auto-reload** — a dismissible toast with a Reload button. A surprise reload discards whatever the user was half-way through entering.
- **Test that the version isn't `"unknown"`** — that catches a missing `COPY VERSION` in CI rather than in production, where the feature would be silently dead.

### Release pipeline (`release.py`)

`tooling/common/release.py` automates the full release: clean-tree and branch checks, tests, version bump, release
commit + tag, build, deploy, and finally `git push --follow-tags`. Its module docstring is the reference for the
pipeline steps, flags (`-m`, `-M`, `-B`) and every `release.env` option (`TEST_CMD`, `POST_BUMP_SCRIPT`,
`BUILD_SCRIPT`, `DEPLOY_SCRIPT`, `GIT_PUSH`) — read it rather than relying on a copy here.

- Run it via `uv run tooling/common/release.py` — its PEP 723 inline metadata installs `python-dotenv` in an isolated
  environment, so no project venv is needed.
- Configure it in `tooling/common/release.env` (gitignored); every setting is optional.
- When it may run, and who triggers it: `CLAUDE-COMMON.md` § Release & deployment authorization.

### Version bumper (`bump_ver.py`)

`tooling/common/bump_ver.py` reads `VERSION`, increments the requested part, writes back. Can be used standalone:

```bash
python tooling/common/bump_ver.py -p   # 1.2.3 -> 1.2.4
python tooling/common/bump_ver.py -m   # 1.2.3 -> 1.3.0
python tooling/common/bump_ver.py -M   # 1.2.3 -> 2.0.0
```

Creates `VERSION` with `0.0.0` if it doesn't exist.

---

## Shared Tooling Sync

Shared files — Claude instructions (`CLAUDE-COMMON.md`, this file), skills, hooks, and release/ops tooling — live in
the private `smtwkla/smtw-common` repo and are synced into each project by `tooling/common/sync_common.py`.

### How it works

1. `sync_common.py` self-updates first — if the upstream version differs, it rewrites itself and re-executes.
2. It syncs every file in its `FILES` list and every directory in its `DIRS` list from `smtw-common`'s `main` branch.
   Those two lists are the authoritative inventory of what gets synced.
3. It warns if `.claude/CLAUDE.md` doesn't start with the banner that imports `CLAUDE-COMMON.md`, and prints the
   banner to paste.

Sync only adds and overwrites — a file removed from `smtw-common` stays in the project until deleted by hand.

### Setup

1. Create `tooling/common/.env-common` (gitignored) with a GitHub PAT that has read access to `smtwkla/smtw-common`:
   ```
   GITHUB_PAT=ghp_xxxxxxxxxxxxxxxxxxxx
   ```
2. Run: `python tooling/common/sync_common.py`

To share a new file, add it to `FILES` or `DIRS` in `sync_common.py` in `smtw-common`, push, then sync. From
`smtw-common`, `tooling/common/sync_all.py` runs the sync across all sibling repos in one go.

---

## Testing Pattern

Three layers — keep them separate:

**Layer 1 — Unit tests (no HTTP, no DB)**

- Test `config_rbac` structure: all keys have colons, all roles known, no admin in tuples, wildcards not mixed.
- Test `compute_permissions`: admin gets all keys, each role gets the expected subset, unknown role gets nothing.
- Test `has_perm`: admin always True, wildcard grants all known roles but not unknown roles, unknown perm key returns
  False for non-admin.
- Test `require_perm` decorator in isolation using a dummy function — no Flask test client needed.
- Test multi-role permission union: user with roles A + B gets permissions of both.

**Layer 2 — HTTP enforcement tests**

- Use role-specific test clients (fixtures in `conftest.py`).
- Verify restricted roles get 403 on key write routes — decorator fires before any DB query, so no DB mocking needed.
- Verify privileged roles are not blocked (response may fail for other reasons, but not 403).

**Layer 3 — Domain tests (against a test DB)**

- Seed data through the real write path (e.g. `record_event`), not raw INSERTs, so validation runs.
- Assert derived state through the projection functions.
- Truncate the test DB once per session (session-scoped `pytest_configure`), not per class — per-class resets were
  tried and weren't worth the complexity. If tests pollute each other, fix the test, not the fixture.

**Layer 4 — Frontend unit tests (Vitest)**

- Vitest (`npm test` → `vitest run`, `environment: "jsdom"` in `vite.config.js`), tests in `frontend/tests/*.test.js`,
  run via `tooling/run-frontend-tests.bat`.
- Test the **pure helpers** the frontend does keep: formatters (`utils/*.js`), nav filtering (`canSeeNavItem`), the
  stale-bundle `isOutdated`, client-side crypto twins. Plain data in, plain data out — no component mounting, no
  network.
- Logic that would need a component test to verify usually belongs in a pure helper (or the backend) instead.
- Where a frontend helper must interoperate with a backend algorithm (e.g. an encryption format), generate a test
  vector with the Python implementation (a `tooling/` script) into `frontend/tests/fixtures/` and test the JS side
  against it, so the two can't drift silently. Reference: VelKilnMaster `tooling/crypto/make_test_vector.py`.

Write `test_rbac.py` first, before any module tests. It validates the policy file itself and catches mistakes
immediately.

---

## Dev Data Tooling

### Replicate prod → local

`tooling/dev/replicate_prod_to_local.py` gives realistic local test data. Rules learned the hard way:

1. **Full-copy mode is lift-and-shift only** — copy rows verbatim, no "fix-up" steps. If prod has it, local has it.
2. **Cutoff mode** ("copy events up to date X") reproduces past states. Any trim or re-seed logic (e.g. rebuilding
   derived counters when events are filtered out) runs **only** in cutoff mode.
3. **Safety guards**: refuse unless the local host is `localhost`; refuse if prod and local point at the same host + DB;
   require interactive confirmation.
4. **FK-aware order**: copy an explicit list of parent tables first, then the rest.
5. **Skip list** for tables that shouldn't be copied (time-series hypertables, worker-local queue state, the migration
   version table).
6. **Reset sequences** after the copy so new inserts don't collide — PostgreSQL: `setval` each `SERIAL` to `MAX(id)`;
   MariaDB: `ALTER TABLE … AUTO_INCREMENT = MAX(id) + 1` where needed.
7. Read prod with a **read-only DB user**, never the app's write user.

### Read-only prod data

For investigating prod data without risk — DB-level access, complementing the `prod-vm` skill and `ccssh` (machine-level
access, CLAUDE-COMMON § Production access):

- A DB user with `SELECT` grants only on the app tables (reuse a read-only ingest user if the app already has one).
  Credentials in `secrets_app.py`.
- `tooling/dev/prod_readonly.py` — SQL runner with the IST session timezone, wrapped in `tooling/run-prod-query.bat`.
- A project skill `.claude/skills/read-prod-data/SKILL.md` describing the workflow, so Claude uses it when asked to
  "check prod".

---

## Frontend Design

### Overall Layout

The app shell is a fixed three-zone layout:

```
┌──────┬─────────────────────────────────┐
│      │           Topbar                │
│ Side │─────────────────────────────────│
│ bar  │                                 │
│      │         Main Content            │
│      │         (router-view)           │
└──────┴─────────────────────────────────┘
```

- **Sidebar**: fixed width, full height, icon-only nav links. Permission-filtered. Version number at the bottom.
- **Topbar**: fixed height. Holds company/tenant selector (left), page title or breadcrumb (centre), username + logout (
  right).
- **Main content**: scrollable. Fills remaining space. Each route renders into this area via `<router-view>`.

Dimensions live in CSS custom properties (e.g. `--sidebar-width`, `--topbar-height`) defined on `:root` — never
hardcoded in component styles.

### Navigation Hierarchy

The app uses three levels of navigation. The sidebar is level 1. Levels 2 and 3 live inside the content area.

```
┌──────┬──────────────────────────────────────┐
│      │              Topbar                  │
│ Side │──────────────────────────────────────│
│ bar  │  [icon] [icon] [icon]  ← Module toolbar  (level 2)
│  ↑   │──────────────────────────────────────│
│ L1   │  [icon] [icon]  ← Section toolbar    (level 3, sparingly)
│      │──────────────────────────────────────│
│      │           Content                    │
└──────┴──────────────────────────────────────┘
```

**Level 2 — Module Toolbar**

Almost every module has one. It is a horizontal icon bar just below the topbar, switching between the module's top-level
sections.

- Visually consistent with the sidebar: same icon style, same active/hover states.
- Each icon switches the active section within the module — local state, not a route change.
- Section icons are permission-filtered; if only one section is accessible, the toolbar is hidden.
- Don't use it as a substitute for sidebar entries — sections here are genuinely subordinate to the module.

**Level 3 — Section Toolbar**

Used sparingly, only when a specific section within a module has its own set of sub-views that would pollute the module
toolbar if added there. Rendered just below the module toolbar, scoped to the active section.

- Visually subordinate to the module toolbar — smaller icons, or a tab-strip style, to signal the hierarchy.
- Sections that don't have sub-views render nothing at level 3 — the space collapses cleanly.
- Apply the same permission-filtering logic as the module toolbar.

### CSS Architecture

- Use CSS custom properties for all theme values: colours, spacing, border radii, shadow levels.
- Define them globally in `src/assets/main.css` or an `App.vue` style block.
- Component styles are scoped (`<style scoped>`). Never use global selectors inside scoped styles except for `:root`
  overrides.
- Bootstrap provides the grid and utility classes. Override Bootstrap variables via CSS custom properties or a SCSS
  variables file — don't fight Bootstrap with `!important`.

### Sidebar Design Principles

- Icons only — no text labels. Tooltip on hover shows the label.
- Active state: distinct background tint + icon colour change.
- Hover state: subtle background change.
- All states use CSS custom properties so theming is a single-file change.
- Nav items are driven by data (array of `{ name, icon, label, perm }`) — not hardcoded markup.
- Items are filtered by `userPermissions` — never render then hide; exclude from the DOM entirely.
- The sidebar order defines perceived module priority — put the most-used modules at the top.

### Topbar Design Principles

- If relevant, Company selector is a styled `<select>` or custom dropdown — the most important control, always visible.
- Changing the company reloads the current view's data without a full page refresh.
- Username shown as plain text; logout as an icon button or small link, not a prominent button.
- No breadcrumbs deeper than one level — the app is flat (sidebar selects the module; the module manages its own
  sub-navigation).

### View Structure

Each view is a single `.vue` file for the module (e.g. `EmployeesView.vue`). Internal layout:

```
┌─────────────────────────────────────────┐
│  View header: title + primary actions   │  (e.g. filters, export button)
├─────────────────────────────────────────┤
│  Main content area                      │  (table, form, cards, charts)
├─────────────────────────────────────────┤
│  Pagination / summary                   │  (if applicable)
└─────────────────────────────────────────┘
```

- Keep views thin — complex logic goes in `api.js` or composables, not in the view's `<script setup>`.
- Use `ref` and `computed` from Vue's Composition API. Avoid `data()` / Options API.
- Loading state: show a spinner or skeleton while data is fetching. Don't leave the view blank.
- Error state: show a dismissible alert with a human-readable message. Log the full error to the console.
- Empty state: show a helpful message when the list is empty, not just a blank table.

### Status-Dependent Views

When an entity has a multi-step workflow, render different components per status rather than one mega-component with
v-if/v-else blocks everywhere:

- Parent view loads data and passes it to a status-specific child component.
- Example: `BankRunDraft.vue`, `BankRunForVerification.vue`, `BankRunExecution.vue`, `BankRunComplete.vue`.
- Each child owns its own layout, edit logic, and action buttons — no tangled conditionals.
- The parent handles data loading, status transitions, and routing back to the list.

### Mutually Exclusive Action Buttons

When a view has both "save current edits" and "advance to next status" actions:

- Show **Save** when the form is dirty (unsaved changes exist).
- Show **Advance** (e.g. "Submit for Verification") when the form is clean and all preconditions are met.
- Never show both simultaneously — it confuses users about what clicking will do.
- Place the primary action button on the right. Secondary/destructive actions (Delete, Reject) go on the left.

### Edit-Toggle Pattern

For inline editing of selections (e.g. choosing an ERP supplier):

- **Saved state**: show a read-only badge/display with a pencil icon to enter edit mode.
- **Editing state**: show the search/select input with Save and Cancel buttons.
- Clicking Save commits the change (API call); Cancel returns to saved state without changes.
- This avoids permanently showing form controls for fields that are set once and rarely changed.

### Group Edits Pattern

When an input applies to a group of records (e.g. marking all entries for a supplier as "success"):

- Show the input once at the group header level, not on every row.
- On save, fan out the group-level value to all child records in a single API call.
- This reduces cognitive load and prevents inconsistent states within a group.

### Table / List Pattern

- Always server-side paginate large datasets — never load everything then paginate in the browser.
- Pagination controls: previous/next with current page indicator. Show total record count.
- Sortable columns: clicking the header sorts; clicking again reverses. Show a sort indicator icon.
- Filters above the table. Applying a filter resets to page 1.
- Column widths: set explicitly so the table doesn't reflow when data changes.
- Action column (edit, view, delete) is right-aligned and always the last column.

### Form / Modal Pattern

- Use Bootstrap modals for create/edit forms on list views — avoids a separate route for simple forms.
- For complex forms, use a dedicated route/view.
- Disable the submit button while the request is in flight — prevent double-submit.
- Never leave a disabled submit button silent: tell the user **why** — bind a `saveDisabledReason` computed to the
  button's `title`, and/or show an inline hint under the problem field.
- Show validation errors inline next to the relevant field, not only at the top.
- On success: close modal, refresh the list, optionally show a toast notification.
- On failure: keep the modal open, show the error message.
- **Never lose typed input.** Form modals use `backdrop: 'static'`, so a click outside never closes them. Esc, ✕ and
  Cancel close at once when the form is unchanged; when it has changed, they first show an in-dialog
  "Discard your changes? Keep editing / Discard". Detect changes by comparing the form with a snapshot taken at open.
  No browser `confirm()`. Implement this once, in the shared form-modal component, not per dialog.
- **A refusal is always in view.** When a save is refused, by the form's own check or by the server, the dialog
  scrolls the first field with a message into view and puts the cursor in it. A refusal for a field that is not in
  the form shows at the top of the dialog, also scrolled into view. Why: a long dialog on a phone hides its lower
  fields, and a message there makes Save look dead (Yantra, 22-10-2026: *Time spent* empty below the fold). Implement
  this once, in the shared form logic that holds the error, not per dialog. A browser test checks that the message
  is on screen (Playwright `toBeInViewport()`), not only that it exists.

### Print / Export Views

- Print views use `@media print` CSS to hide controls and show print-friendly headers — no separate route needed for
  simple cases.
- For complex print layouts, use a separate Vue component at a dedicated route (e.g. `/print/report`).
- Triggered by a button that opens the print route in a new tab.

### Design Tone

- Internal business tool: clarity and density matter more than decoration.
- Prefer a dark sidebar against a light content area — clear spatial hierarchy.
- Use colour purposefully: primary action, warning, danger, success — not for decoration.
- Typography: one font family, two or three sizes maximum per view.
- Avoid animation except for micro-interactions (button active state, modal open/close).
- Timestamps: always IST, formatted `DD-MM-YYYY HH:MM`. No timezone suffix for single-timezone apps. The backend must
  ensure all datetimes are IST before serialisation (see Timezone handling under DB Connection Pattern).

---

## Frontend API Helper Pattern

`api.js` is the single point for all backend calls:

- Calls `getToken()` (which refreshes if near expiry) before every request.
- Appends the current tenant/company as a query parameter automatically.
- Exports thin wrappers: `apiGet`, `apiPost`, `apiPut`, `apiDelete`.

No view or component calls `fetch` directly.

**Cached domain stores** — for data that is expensive to fetch and rarely changes within a session (e.g. a plant
layout, master lists), `stores/<domain>.js` exports an `ensure<Domain>()` that fetches on first call and returns the
cached copy after. Views call it instead of each re-fetching the same payload.

---

## Pre-flight Before Every Release

Pre-flight runs in two stages. **Before the maintenance window**, `/pre-flight` (`tooling/common/preflight.py`, or a
run config that sets the Release run configs' `TEST_CMD`) runs the release's tests on HEAD; a green run stamps that
commit with a git note (`refs/notes/preflight`, not pushed), and a red run gives one bug report per failure and asks
what to do (fix the code, fix the test, mark as a known fault, investigate). **In the window**, `release.py` skips
`TEST_CMD` when HEAD carries a valid stamp (this exact commit, this machine, this `TEST_CMD`, at most 7 days old);
otherwise it runs the tests and aborts on failure before bumping or tagging, as before, and stamps a green run. The
release commit (only `VERSION` changed) carries the stamp, so a retry after a failed build or deploy does not test
again. A release started while a pre-flight runs aborts before anything changes. The repo's settings are a
`## Pre-flight` section in its `CLAUDE.md`: *Test command*, *Tests a clean copy of HEAD* (`yes` | `no`), *Failure
logs*, *Re-run failing tests*, *Known fault*.

To also gate on a clean frontend build, set `BUILD_SCRIPT` in `release.env` so the build step runs before deploy.

---

## `.claude/CLAUDE.md` for a New Project

Start it with the banner `sync_common.py` prints — it imports `CLAUDE-COMMON.md`. Minimum contents:

- Stack (backend, frontend, DB, auth)
- Dev commands (start backend, start frontend, run tests)
- Schema reference (where DDL lives, where the annotated guide is)
- Key domain conventions (encoding schemes, naming rules, multi-tenancy model)
- External integrations (ERP, accounting, AI services)
- Anything that overrides the Defaults in `CLAUDE-COMMON.md` (Invariants can't be overridden)
- Deliberate deviations from this file, so audits don't flag them as gaps

---

## Fresh Project Bootstrap Checklist

1. `uv init backend && uv add flask flask-cors pymysql pyjwt[crypto] apscheduler` (PostgreSQL: `psycopg2-binary`
   instead of `pymysql`).
2. `npm create vite@latest frontend -- --template vue`, then `npm i bootstrap @popperjs/core keycloak-js`.
3. Copy `sync_common.py` into `tooling/common/` and run it (see § Shared Tooling Sync) — that brings in
   `CLAUDE-COMMON.md`, this file, shared skills/hooks and release tooling.
4. Scaffold `.claude/CLAUDE.md` starting with the banner the sync prints (see § `.claude/CLAUDE.md` for a New Project).
5. `tooling/dev/docker-compose.dev.yml` with the dev DB.
6. `example_secrets_app.py` + `.gitignore` entry for `secrets_*.py`; `config.py` as the only importer of secrets.
7. Backend skeletons following this file: `config_rbac.py`, `auth_utils.py`, `local_db.py` (pool + migrations +
   singleton lock), `db_helpers.py`, `task_queue.py` + `worker.py`.
8. First migration: the auth-dependent tables + `task_queue`. Commit.
9. `test_rbac.py` before any module tests.
10. Slow-request logger and the public `GET /api/version` endpoint + stale-bundle check, from day one.
11. `.bat` wrappers in `tooling/` for test / build / prod-query.
12. A first release via `release.py -p` to prove the pipeline end to end before real features land.

---

## Common Pitfalls

| Pitfall                                                   | Fix                                                                                                                                                                                                                 |
|-----------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| DB connection leaks                                       | Per-request connection from the pool, returned in `teardown_appcontext` — never held across requests                                                                                                                |
| No `@` alias in Vite by default                           | Use relative imports in frontend (`../../stores/auth.js`) unless alias is explicitly configured                                                                                                                     |
| `secrets` is a Python stdlib module                       | Name files `secrets_db.py`, never `secrets.py`                                                                                                                                                                      |
| Wildcard mixed with roles                                 | `('*',)` must be alone — never `('*', 'other_role')`                                                                                                                                                                |
| Admin listed in PERMISSIONS tuples                        | Admin bypass is in code — listing it in tuples is misleading and tested against                                                                                                                                     |
| npm commands with absolute paths on Windows               | `cd frontend && npm run build`, not a full Windows path                                                                                                                                                             |
| Wrong DB placeholder style                                | PyMySQL and psycopg2 both use `%s`, not `?`                                                                                                                                                                         |
| Role/permission logic duplicated in frontend              | Frontend only stores what `/api/auth/me` returns — never derives permissions from the token                                                                                                                         |
| `debug=True` hardcoded                                    | Use an env var or config flag; production must run with debug off                                                                                                                                                   |
| Serving files from `data/` as static                      | Always route file serving through an authenticated endpoint                                                                                                                                                         |
| Returning bare JSON arrays                                | Always wrap lists: `jsonify({'items': [...]})` — bare arrays can break some clients                                                                                                                                 |
| `Decimal` from DB in JSON responses                       | Flask `jsonify` serialises `Decimal` as string — this is fine; frontend uses `Number()`/`parseFloat()`. Don't cast to `float()` (loses precision). Only a problem with raw `json.dumps` which crashes on `Decimal`. |
| Changing company not refreshing data                      | Watch the company reactive ref in each view and reload on change                                                                                                                                                    |
| `data.get("field")` returns None not ""                   | Use `(data.get("field") or "").strip()` when key may exist with null value                                                                                                                                          |
| Worker crashes on malformed jobs                          | Always validate required fields in job payload before dispatching — log and skip, never crash                                                                                                                       |
| Bulk re-enqueue floods external system                    | Make startup recovery manual (admin button) for high-volume queues; auto-enqueue only for safe ones                                                                                                                 |
| Multi-role users lose secondary permissions               | Union permissions from all roles, not just the primary role                                                                                                                                                         |
| Port conflicts with legacy systems                        | Check default ports of all services (e.g. Tally uses 9000, same as MinIO default)                                                                                                                                   |
| Keycloak LDAP sub-OU group sync                           | Users in sub-OUs may not auto-link to groups; workaround: manually join in Keycloak                                                                                                                                 |
| Timestamps wrong in adminer/pgAdmin/debug SQL             | Expected: server is UTC, only app sessions are IST. Manual connections show UTC — account for +05:30 offset                                                                                                         |
| Version shown differs from the release tag                | The root `VERSION` file is the only source — Vite and `/api/version` read it; `package.json`'s version is not the app version                                                                                       |
| `cur.fetchone()[0]` on a dict cursor                      | Rows are dicts — use the column name: `cur.fetchone()["colname"]`                                                                                                                                                   |
| Two workers run migrations concurrently                   | Singleton DB lock around `init_db` (§ Local DB Migration Pattern)                                                                                                                                                   |
| Two scheduler / monitor instances running                 | Same singleton lock around `start_scheduler` and monitor threads                                                                                                                                                    |
| Pool exhaustion → gunicorn SIGKILL                        | `maxconn >= gunicorn workers + worker process + buffer`; the slow-request logger shows it coming                                                                                                                    |
| Task marked done although the send failed                 | Mark done only on a verified successful send; otherwise let it retry                                                                                                                                                |
| Duplicate Telegram alerts from threads                    | `threading.Lock` around the in-process aggregation path                                                                                                                                                             |
| Scheduled-job history in a separate table                 | `task_queue` rows are the history — no extra audit-log table                                                                                                                                                        |
| `TZ` env set on a container                               | Don't — host stays UTC; the DB session setting is the only IST switch                                                                                                                                               |
| Replicate script "helpfully" fixes up rows                | Full copy is lift-and-shift; fix-up logic runs only in cutoff mode                                                                                                                                                  |
| Silent disabled Submit button                             | Bind a `saveDisabledReason` computed to `title`; add an inline hint                                                                                                                                                 |
| Direct `npm`/`uv` commands trip Claude permission prompts | Run the `tooling/*.bat` wrappers (CLAUDE-COMMON § Wrapper scripts)                                                                                                                                                  |
