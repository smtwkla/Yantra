```
Step: S013 — Network gate, access log and job queue
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 17-10-2026
```

# S013 — Brief review, round 1

**Verdict: not ready — two `major` findings are open** (BR1-01, BR1-02). No
blocker. The design is sound and follows the user's two decisions of 17-10-2026:
the deny list is the right answer to role inheritance and the S011 union, the
DB-held "due since today's time" scheduler is simpler and more robust than
APScheduler for one daily task, and the migration is idempotent. The majors are
both about what happens *around* the new hooks rather than inside them: what the
gate and the access-log hook do while the database is down (the brief's own
"DB may not exist" rule, and S011 BR1-01 again), and the before-request order
against the test harness, which as written leaves `g.user` unset when the gate
runs in tests and breaks existing tests that use the raw `client` fixture.

Reviewed against: the brief; `docs/Plan.MD`; `docs/Maintenance-Philosophy.md`;
`docs/Plant-Facts.md`; `.claude/SMTW-WebApp-Base.md` § Internet Exposure, § DB
Connection (timezone), § Local DB Migration (singleton lock), § Business
Settings, § Background Worker / Job Queue, § Testing; `.claude/CLAUDE-COMMON.md`;
`.claude/CLAUDE.md`; the working-tree code: `backend/app.py`, `auth_utils.py`,
`access_core.py`, `config_rbac.py`, `settings.py`, `local_db.py`,
`db_helpers.py`, `api_common.py`, `config.py`, `worker.py`,
`tests/conftest.py`, `tests/test_auth.py`, `tests/test_rbac.py`,
`tests/test_settings_api.py`, `tests/test_migration_v9.py`;
`tooling/build/nginx.conf`, `gunicorn.conf.py`, `Dockerfile.backend`;
`frontend/src/api.js`, `stores/auth.js`, `App.vue`, `router/index.js`,
`views/NoAccessView.vue`, `views/SettingsView.vue`; S011 brief and review r1
(BR1-01); `docs/review/2026-10-16-smtw-review.md`.

---

## Major

### BR1-01 — `major` — The two hooks' behaviour while the database is down is underspecified, and one reading of it locks IT admin out exactly when they need Settings › Database

**Problem.** The brief settles one DB-down case (§ 5.3: memberships unknown →
token roles only) but leaves three others to the coder, and each has a wrong
answer that is easy to pick:

1. **The internal ranges come from `app_settings`** (§ 3, § 5.2), read through a
   5-minute cache. On a fresh process with the DB down (a restart during an
   outage, or the fresh-deploy case of CLAUDE.md "DB may not exist") the cache is
   cold and the read raises `DBUnavailable`. § 5.2 covers an *unreadable stored
   value* (→ defaults) but not an *unreachable store*. If the coder follows § 1.1
   "can't be classified → external, fail closed", IT admin from the plant is
   refused on every route, including `/api/auth/me` and
   `/api/settings/db-status` — the two routes S011 BR1-01 made DB-free so IT
   admin can see that the database is down. The gate would undo that.
2. **The access-log hook borrows "its own short DB connection from the pool"**
   (§ 5.4). `local_db.get_pooled_db()` opens a new connection when none is
   cached; with the server unreachable that blocks for `connect_timeout` (5 s)
   and raises. Wrapped in try/except it does not break the request — but every
   request, including the two above, would wait 5 s before answering. `get_db()`
   avoids this by asking `ensure_schema()` first, which answers from memory for
   30 s after a failed attempt. The hook must do the same.
3. **A failed write and the sighting cache.** If the cache records the sighting
   before the write succeeds, a sighting during a short outage is lost for ten
   minutes; if after, every request retries the write during the outage (cheap
   once (2) is fixed, and the right choice for an audit trail). The brief does
   not say which.

Related: for an **internal** address the gate should decide before any DB read
(no membership query needed: internal always passes). The brief implies it but
does not say it, and it is what keeps the IT-admin-from-the-plant path
DB-free.

**Why it matters.** "The app must start and serve while the DB is unreachable"
is a repo rule (CLAUDE.md), and the one person who must reach Settings during an
outage is the one role the gate restricts. ISO 27001 A.8.15 also asks that
logging failures not take the service down; a 5 s stall per request is a soft
version of that.

**Options.**
1. State the four rules in § 5.2–5.4: (a) the gate decides *internal* from the
   address alone, before any DB read; (b) the ranges loader catches
   `DBUnavailable`: last cached list if any, else the built-in defaults (the same
   `DEFAULT_INTERNAL_NETWORKS` constant the migration inserts), logged once per
   30 s like `ensure_schema`; (c) the access-log hook calls `ensure_schema()`
   first and skips the write (log at WARNING, once per 30 s) when it returns an
   error — never opens a connection to a server known to be down; (d) the
   sighting is cached only after a successful INSERT. Add the tests: gate from an
   internal address with `db_down` → 200 on `/api/auth/me`; external IT admin
   with `db_down` → 403; the hook with `db_down` does not slow or break the
   response. **Recommended.**
2. Keep the gate DB-free altogether: ranges from `company_settings.py`, not
   `app_settings`. Simpler, but loses "editable without a deploy", which the
   brief and the base pattern want. Not recommended.

---

### BR1-02 — `major` — Before-request order against the test harness: the gate would run before `g.user` is set in tests, and the raw `client` fixture breaks existing tests

**Problem.** Flask runs `before_request` functions in registration order.
`app.py` registers `require_auth` at import (line 44); `tests/conftest.py`
registers `_inject_test_user` when *it* is imported, i.e. after `app`, so it
runs after everything `app.py` registered. `require_auth`'s TESTING branch
returns `None` when `X-Test-Role` is present and leaves `g.user` to the
conftest hook (auth_utils.py line 214–216). The brief registers the gate "after
`require_auth`" in `app.py` — so in tests the order is `require_auth` → gate →
`_inject_test_user`, and the gate sees no `g.user`. The coder then has to
choose alone: crash, treat as anonymous (pass), or re-order hooks by hand. If
it passes, every gate test written with `role_client` passes vacuously.

Two existing tests break in any case:

- `test_auth.TestDatabaseDown.test_it_admin_gets_token_permissions` uses the
  **raw `client` fixture** with a Bearer token and no `X-Real-IP`. § 5.1 says
  missing header → external; the user is `it_admin` → 403 `network_denied`,
  not the 200 asserted. § 3 says "conftest sets an internal address by default"
  but not how; `RoleClient` can add a header, the raw `client` cannot, and
  `test_auth` needs the raw client to send real tokens.
- `test_rbac.TestComputePermissions.test_role_matrix` lists the exact key set
  for `maint_manager` and `it_admin`; adding `access_log:view` fails both rows.
  Trivial, but the brief says existing tests are unaffected.

**Why it matters.** A gate that is never exercised by the suite is the base
pattern's own warning ("a gate that never refuses looks exactly like a gate that
works"). And the brief's acceptance is "`run-tests.bat` green".

**Options.**
1. Move the harness injection *into* `require_auth`'s TESTING branch: conftest
   sets `flask_app.config["TEST_USER_FACTORY"] = harness_user` and
   `require_auth` calls it (`g.user = factory(role, username)`) instead of
   returning early. Then `g.user` exists for every later hook, in tests as in
   production, and the registration order in `app.py` (`require_auth` → gate →
   timer) is the only order. For the address: set
   `flask_app.test_client_class` to a `FlaskClient` subclass whose `open()`
   defaults `environ_base={"HTTP_X_REAL_IP": "10.0.0.5"}` — this covers the raw
   `client`, `RoleClient` and every fixture at once; gate tests pass
   `headers={"X-Real-IP": "203.0.113.7"}` to override. Update
   `test_role_matrix`. **Recommended.**
2. Keep the conftest hook and have the gate tolerate a missing `g.user` (pass),
   with conftest re-ordering `flask_app.before_request_funcs[None]` to put the
   injector right after `require_auth`. Works, but it is a hidden coupling to
   Flask internals and a gate that silently passes anonymous requests is the
   wrong default. Not recommended.

Also name in § 8 the one test that checks the order itself: a `role_client`
manager with an external `X-Real-IP` gets 403 on `/api/masters/sites` (so a
regression to "gate before user" fails loudly).

---

## Minor

### BR1-03 — `minor` — "Not by `CURRENT_TIMESTAMP` (the server runs UTC)" is wrong, and introduces a second timestamp convention

**Problem.** § 4 says times are written by the app "not by `CURRENT_TIMESTAMP`
(the server runs UTC)". Every connection Yantra opens — pool and
`get_local_db()` alike — runs `SET time_zone = '+05:30'`
(`local_db._connect_kwargs`), so `NOW()` and `DEFAULT CURRENT_TIMESTAMP`
already yield IST. That is the base's timezone policy ("the session setting in
`local_db.py` is the single point where the switch happens") and it is how
every table from v1 to v9 gets its `created_at`. The new tables would be the
only ones without a default, and `ts`/`created_at` would be the only columns
filled from Python's clock.

**Why it matters.** Two conventions for the same thing is what the base's
policy exists to avoid; the stated reason would also mislead the next step.
The pure scheduler does need `now_ist` as a parameter (no `datetime.now()` in
the core — correct), so a Python `now_ist()` helper is still needed there.

**Options.**
1. Correct the reasoning; give `ts`, `created_at` and `scheduled_for`
   `DEFAULT CURRENT_TIMESTAMP` like the other tables and use `NOW()` in SQL;
   keep one `now_ist()` helper (`datetime.now(ZoneInfo("Asia/Kolkata"))`,
   naive) for the scheduler's clock and for the worker's comparisons, and say
   that the two agree because of the session setting. State that the worker
   connects with `get_local_db()` (so it gets the `init_command`). **Recommended.**
2. Keep app-written times, with the reason corrected ("one clock for the pure
   core and the tables"). Acceptable, but then say why the other tables differ.

### BR1-04 — `minor` — Standards: the gate's exact control is A.8.2; add the "protected" half of A.8.15 and the Indian retention floor

**Problem.** The citations are correct in substance, but the mapping of the
gate to A.8.20 / A.8.22 is the loose one. In ISO 27001:2022 Annex A
(ISO 27002:2022 gives the guidance):

- **A.8.20 Networks security** — networks and network devices are secured,
  managed and controlled. **A.8.22 Segregation of networks** — groups of
  services, users and systems are kept in separate network zones. Both are
  about the *network* as infrastructure (firewalls, zones). The gate uses the
  network zone as evidence, but what it does is restrict *accounts*.
- **A.8.2 Privileged access rights** — "the allocation and use of privileged
  access rights shall be restricted and managed": privileged accounts are
  identified, granted to fewer people, used only for privileged work, and may
  be bound to conditions (place, device, time). IT admin and the manager are
  exactly the privileged accounts here; "only from the plant network" is such a
  condition. This is the control an auditor would look for.
- **A.8.15 Logging** also says logs are *protected* against tampering and
  deletion, and that a *retention period* is set. The design already satisfies
  it (no update route; no FK that cascades; only the scheduled purge deletes;
  `access_log:view` is read-only) — say so in one line, so the property is
  deliberate and the code reviewer checks it.
- **A.8.16 Monitoring** names failed logins and access from unusual locations
  among the things to watch — the `auth_failed` and external sightings fit.
- Retention: no ISO number, as the brief says. For reference, India's **CERT-In
  directions of April 2022** require ICT system logs to be kept for **180
  days**; 365 clears it. Worth one line, since the owner will be asked about
  retention one day.

**Options.**
1. In § 2: lead the gate paragraph with A.8.2 (privileged access rights, the
   condition being the network), keep A.8.20 / A.8.22 as the supporting
   controls, add the "protected, append-only" line under A.8.15 and the CERT-In
   floor under retention. **Recommended.**
2. Leave as is. The claims are not wrong, only imprecise.

### BR1-05 — `minor` — The denied page: the frontend already has the first-call case; specify the mid-session case instead of a new view and router guard

**Problem.** § 1.4 and § 3 add `NetworkDeniedView.vue` plus "403 handling in
the API helper / router guard, as `NoAccessView` (S011)". But `NoAccessView` is
not reached by a router guard — `App.vue` renders it in place of
`<router-view>` when permissions are empty. And `stores/auth.loadProfile()`
already turns any non-401 failure of `/api/auth/me` into `authError`, which
`App.vue` shows as a full-page card with the message and **Sign out** (App.vue
lines 46–56). The first-call refusal (§ 5.3 last bullet) therefore already
shows the backend's message; what is missing is only the address (the API
helper keeps `code` and `field` from the body, not `ip`).

What the brief does not cover is the **mid-session** refusal: a manager who
opens Yantra on Wi-Fi and walks out onto mobile data. Every later call fails
with 403 `network_denied`, and each view shows it as an ordinary error. The
brief should say what happens.

**Options.**
1. No new route or guard. `api.js` keeps `ip` from the body; `stores/auth.js`
   gains `networkDenied = ref(null)` (`{message, ip}`), set by `api.js` whenever
   a response carries `code === "network_denied"` (first call or later);
   `App.vue` shows the existing full-page card (message, "The server saw your
   address as …", Sign out) when it is set — one small component or the card
   inline. The user signs out or moves back onto Wi-Fi and reloads.
   **Recommended** (smaller than the brief, and it covers both cases).
2. Keep the new view and add a router guard. More code, and a guard cannot
   react to a 403 that arrives mid-session anyway.

### BR1-06 — `minor` — Which 403s count as `denied_perm`: `require_perm_at` and the business 403s are not covered

**Problem.** § 3 says `require_auth` and `require_perm` mark
`g.access_outcome`; § 5.4 makes a bare 403 fall back to `denied_perm`. The
backend has other 403s: `require_perm_at` (auth_utils.py line 370, the S011
site check — a permission refusal in every sense), and business refusals raised
as `ApiError(..., 403)` ("You can't change your own access", "Only IT admin can
set the login", "You have no access to this unit", masters.py / equipment.py).
Under the fallback all become `denied_perm` with `detail = NULL`. That is
defensible for an audit trail (the user was refused), but the viewer's
"refusals only" filter will then show a manager's own-access guard next to
real permission denials, with nothing to tell them apart.

**Options.**
1. `require_perm_at` marks `g.access_outcome = "denied_perm"` and
   `g.access_detail = f"{key}@site:{site_id}"`, like `require_perm`; the
   business 403s stay on the fallback with `detail = "<first 100 chars of the
   error>"` so the row says why. State this in § 5.4. **Recommended.**
2. Only gate-marked refusals count; a bare 403 is `ok`. Cleaner rows, but it
   hides refusals, which A.8.16 asks to see. Not recommended.

Also confirm in § 5.4 two Flask facts the design relies on (both true, both
worth a sentence so the coder does not test for them): `preprocess_request`
stops at the first hook that returns a response, so the gate never runs on a
401; `after_request` runs on error-handler responses and on the 500 path too
(`from_error_handler=True`), so `auth_failed`, 503 and 500 are all seen.

### BR1-07 — `minor` — Worker: lock timeout, which connection does the work, where the lock name lives, who migrates

**Problem.** § 5.5 says the lock is held on a dedicated connection and
re-taken after a reconnect, but leaves open: (a) `GET_LOCK(name, timeout)` —
with what timeout, and what does "a second worker waits" look like (the base
says singletons use a *non-blocking* try); (b) whether the task work runs on
the same dedicated connection or on a second one — the worker must never use
the pool or `db_helpers.get_db()` (Flask `g`); (c) the lock name — the base's
lock-ID registry rule puts every lock constant in one place, next to
`LOCK_MIGRATIONS` in `local_db.py`; (d) "doesn't touch the queue before the
schema is at v10" — does the worker call `ensure_schema()` (and so run
migrations under the migration lock, which is safe and makes the worker
container self-sufficient), or only read `db_version`?; (e) SIGTERM "finishes
the current task" — a purge batch loop can run for a while; the worker
container's `stop_grace_period` in the devops compose must allow it, or the
loop should check the stop flag between batches.

**Options.**
1. State: one dedicated `get_local_db()` connection for lock and work;
   `GET_LOCK(LOCK_WORKER, 0)` tried every loop, "waiting for the worker lock"
   logged once a minute while another holder exists; `LOCK_WORKER =
   "yantra_worker"` in `local_db.py`; the worker calls `ensure_schema()` each
   loop until it returns `None`; the purge checks the stop flag between batches
   and the handler contract allows that (a batch is a transaction, so stopping
   between batches loses nothing). **Recommended.**
2. Leave to the coder with "as the migration lock". Underspecified for a
   process that must survive overnight disconnects.

### BR1-08 — `minor` — Background tasks: define "overdue" and compute `next_run` in the pure module

**Problem.** § 1.9 and § 6 return `last_run, last_status, next_run` and say a
dead worker "is visible". It is visible only by arithmetic: if the worker died
on Monday, Tuesday's card shows `last_run` Monday 02:30 and `next_run` Tuesday
02:30 — in the past — and the reader must notice. `next_run` is also not
defined (today's time if not yet enqueued today, else tomorrow's) and § 3 lists
only `due_tasks` as pure.

**Options.**
1. `scheduled_tasks.py` also exports pure `next_run(entry, last_enqueued,
   now_ist)`; the endpoint adds `overdue: bool` (= `next_run < now`), and the
   card shows an "Overdue — is the worker running?" badge and the failed count
   in red when > 0. Tests for `next_run` beside `due_tasks`. **Recommended.**
2. Leave as is; the user reads the dates.

### BR1-09 — `minor` — Loopback and IPv4-mapped addresses: dev lock-out, and a classification hole

**Problem.** The defaults are the three RFC 1918 ranges. `127.0.0.1` and `::1`
are in none of them. In dev without the auth bypass (real Keycloak at
localhost, `FLASK_DEBUG=1`, § 5.1's `remote_addr` fallback), a manager or IT
admin is *external* and refused; and the lock-out guard (§ 5.2) refuses every
save by a non-admin whose address is `127.0.0.1`. Separately,
`ipaddress.ip_address("::ffff:10.24.0.5")` is an `IPv6Address` that is not
inside `10.0.0.0/8`, so a front proxy that ever passes IPv4-mapped addresses
would classify the whole plant as external (fail closed, but wrong).

**Options.**
1. In `is_internal`: unwrap `.ipv4_mapped` before matching; treat loopback as
   internal in code (only the server itself can present it — not a hole), and
   say so in § 5.1 rather than adding `127.0.0.0/8` to the editable list.
   Tests for both. **Recommended.**
2. Add `127.0.0.0/8,::1/128` to the default list. Works, but IT admin can
   remove it by mistake and a dev then cannot tell why.

### BR1-10 — `minor` — Test isolation for the two new tables and the per-process cache

**Problem.** `conftest._TABLES` empties the known tables once per session;
`access_log` and `task_queue` are not in the brief's list of conftest changes.
A `pending` row left by an aborted run would be claimed by the first
`claim_next` test; the "one `ok` row on a first request, none on the second"
test depends on `SightingCache` state across tests in the same process. And
"dev bypass unaffected" (§ 8) cannot be tested through the app: conftest pops
`DEV_AUTH_BYPASS` and `config.py` refuses it without `FLASK_DEBUG`.

**Options.**
1. Add both tables to `_TABLES`; a `sightings` fixture that clears the cache
   (or the tests use fresh usernames and addresses from `uniq`, like S011);
   `require_network(dev_bypass=...)` takes the flag as a factory argument like
   `require_auth`, and the dev-bypass test calls the handler directly in a
   `test_request_context`. **Recommended.**
2. Leave to the coder.

---

## Nit

### BR1-11 — `nit` — API and data details to pin down

- `GET /api/settings/access-log` returns `page_size`; the existing lists
  (`equipment.py` 445, `documents.py` 489) and the base convention say
  `per_page`, with `api_common.int_arg` and `DEFAULT_PER_PAGE`. Use the same.
- `to` is inclusive (end of that IST day: `ts < to + 1 day`); `user` is exact
  or "contains" (`like_pattern` exists) — say which.
- `path` and `user_agent` are `VARCHAR(255)`; a long scanner URL or UA makes
  the INSERT fail in strict mode and the row is lost. Truncate before writing.
- `PUT /api/settings/network {networks}` — a string as typed (textarea,
  comma or newline separated) or a list? Say which; the stored form is the
  comma-separated text. `ip_network(..., strict=False)` so `10.24.0.5/16` is
  accepted and normalised, or name the host-bits error — either, but say.
- "Keeps at least the last row per task type": `DELETE … WHERE id NOT IN
  (SELECT MAX(id) FROM task_queue GROUP BY task_type)` is MariaDB error 1093
  (same table in a subquery); wrap the subquery in a derived table. A hint for
  the coder.
- Constants: `DONE_TASK_RETENTION_DAYS = 90`, the 10-minute sighting window,
  the 5-minute ranges cache, `locked_until` 10 min and the 5 min × attempts
  backoff all belong in `company_settings.py` or as named module constants,
  not literals (CLAUDE-COMMON: no magic numbers).
- The `PUT` of the ranges is itself an A.8.15 event; log actor and old → new
  like `put_app_settings` does (settings.py line 96–98), under `FOR UPDATE`.
- The lock-out guard protects the saver only, not the manager at a site on a
  different range (SSVT?). Acceptable; say it, and let the 400 message hint
  "check every site's range before saving".

### BR1-12 — `nit` — Docs and policy tests

- Plan.MD § 3 permission matrix: add the `access_log:view` row (manager,
  it_admin); § 3's listed doc updates name § 1, § 5, § 8 only.
- `.claude/CLAUDE.md`: record the deny-list `INTERNAL_ONLY_ROLES` as a
  deliberate departure from the base's `access:wan`, as the S011 RBAC deviation
  is recorded (CLAUDE-COMMON precedence rule: a repo's CLAUDE.md records
  deviations from the base).
- `test_rbac.TestPolicyStructure`: `INTERNAL_ONLY_ROLES ⊆ ROLES` and
  "`admin` not in it", so the tuple is validated like `PERMISSIONS`.
- `docs/Keycloak.md`: one line that the `sid` claim is what the access log
  calls a session (the doc does not mention it today).

---

## Checked and found consistent

- **Nginx real IP** is in place as the brief says: `set_real_ip_from
  10.24.0.0/23`, `real_ip_header X-Forwarded-For`, `real_ip_recursive on`, and
  `X-Real-IP $remote_addr` to the backend (`tooling/build/nginx.conf`).
- **Deny list vs inheritance.** `ROLE_INCLUDES` never *adds* `maint_manager` to
  anyone, so checking held role names (token roles ∪ membership roles) against
  `INTERNAL_ONLY_ROLES` cannot be bypassed by inheritance; an `access:wan`
  allow list granted to engineers would indeed let managers through
  (`compute_permissions(["maint_manager"])` includes every engineer key). The
  departure is correctly stated in § 7. A membership with an invalid role is
  ignored by `valid_memberships` and grants nothing, so it also cannot be a
  manager.
- **"Manager at any site → internal-only everywhere"** is the user's decision
  and matches the stated reason (the account, not the site, is protected).
- **S011 BR1-01 reference** is accurate: `/api/auth/me` catches
  `DBUnavailable` and answers from the token (`app.py` 129–135);
  `current_memberships()` is lazy and `g`-cached; `require_auth` is DB-free.
- **Hook order.** `after_request` functions run in reverse registration order,
  so "register the access-log hook before the others" is right; `flask_cors`
  and `_log_slow_request` do not change the status code.
- **Migration v10** is idempotent (`CREATE TABLE IF NOT EXISTS`, `INSERT
  IGNORE`), and `INSERT IGNORE` is what makes "an existing value is not
  overwritten" true. `ENUM` for `outcome` matches `equipment_events.event`;
  adding a value later is a `MODIFY`, as v5 and v9 did.
- **`due_tasks`** holds across the cases in § 8: worker down over 02:30 → one
  run on return; restart after the run → `MAX(created_at)` ≥ today 02:30 → not
  due; before midnight → tomorrow's time not passed. Keeping the last row per
  type is harmless even when it is a `done` row older than 90 days.
- **Sighting key** bounds the log under internet scanning: `auth_failed` rows
  key on `(outcome, None, ip, detail)`, one per scanner address per reason per
  10 minutes, not one per probed path.
- **`SKIP LOCKED`** needs MariaDB ≥ 10.6; dev runs `mariadb:11.4`
  (`docker-compose.dev.yml`); the production check is an important manual
  check, as it should be.
- **Permissions table (§ 5.7)** matches `config_rbac.py`: `settings:read`
  (manager, IT admin), `settings:edit` (IT admin); `access_log:view` global is
  right for a cross-site record. The Settings nav item needs `settings:read`,
  which the manager has.
- **`company_settings.py`** for `ACCESS_LOG_RETENTION_DAYS` follows the base's
  Business Settings pattern.
- **Open question 1 (admin from outside)** gives both sides and a
  recommendation; it is the user's call. Open question 2 (VPN) is the right
  question for the default ranges.
- **Manual checks**: the four **important** ones are the ones only a person can
  do (a real phone on mobile data; the real-address check that catches the
  base's "proxy IP" trap; the production version and worker log). The
  stop-and-restart check is rightly plain.
- **Track: full** is right (migration, auth/security code, locking, new
  module design).
- **Maintenance standards** (ISO 14224, EN 13306, ISO 55000, SMRP, TPM) have no
  bearing on this step; none is cited, correctly.
