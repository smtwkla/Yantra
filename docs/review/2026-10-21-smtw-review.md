# Yantra audit — whole repo, read against `docs/steps/*`

```
Doc: codebase audit (/smtw-review)
Author: Claude (Opus), with six read-only reviewers
Date: 21-10-2026
Scope: backend, frontend, tooling; step briefs S001–S018, S022; Plan.MD, domain docs, SMTW-WebApp-Base.md; the previous audit (16-10-2026)
Code: HEAD 28d3be3 (S018 committed as ae3841f); S024 (browser tests) in progress, its files excluded
```

The audit was split in six areas, each read in full by its own reviewer: equipment and
documents; masters, Team and failure codes; tickets; authentication, RBAC and security;
infrastructure and cross-cutting; base conformance. The main findings were re-checked in the code
before this report.

**Tests were not run in this audit**: S024's coder was using the test database at the same time.
The last full run (S018 code review r5, 21-10-2026) was green: backend 1823, frontend 93,
dependency-audit 42; `vite build` clean. S024's browser tests do not exist yet, and Yantra's
`CLAUDE.md` has no `## SMTW-Review` section yet (S024 A1 adds it).

**Overall:** the business rules of S001–S018 are built faithfully; RBAC is complete (94 URL
rules, none ungated, every key in the policy, every site-scoped write checked at the record's
site); SQL is parameterised; file handling is safe; timezone handling is consistent. The serious
findings are about **the next release** and **integrity at the seams between modules** that the
step reviews, each looking at one step, could not see.

## CRITICAL

None.

## HIGH

**[1]. `backend/local_db.py:289-292, 322-327` — The next release applies migrations v6–v13 at once; v9 fails on any production equipment row, and the app then serves 503 everywhere**
- **Problem:** the newest release tag is `v0.1.3` (migrations v1–v5); `VERSION` is `0.1.3`. The
  next release applies v6–v13 (S006–S018) in one go. v9 adds `equipment.model_id INT NOT NULL`
  with a foreign key: on a table with rows, the column fills with 0 and the FK fails (1452). The
  comment above v9 says so and relies on "production had no equipment when v9 was written".
  Nothing checks that today.
- **Failure scenario:** one machine was typed into production since v0.1.3 (phase 2 is "load the
  equipment list"). After the deploy, v6–v8 apply, v9 fails and is retried every 30 s; `get_db()`
  raises `DBUnavailable`, so every DB route answers 503. The post-deploy check reads
  `/api/version`, which does not touch the DB, so `deploy.py` reports success and `release.py`
  pushes the tag.
- **Rollback:** after v9 the v0.1.3 image cannot run (it selects `e.make, e.model`, which v9
  drops). Rollback means a database restore, and no step takes a backup before a deploy.
- **Fix:**
  1. Now: read production's schema version (Settings › Database) and the equipment count.
  2. Add an engine-level precondition before v9: refuse with a clear message if `equipment` has
     rows, applying nothing (v9's text is not edited).
  3. Dump the database before every deploy (`deploy.py` or the playbook).
  4. Report schema readiness on a public endpoint (e.g. `/api/health` with the `ensure_schema`
     state) and make `deploy.py` check it.
  5. Release now, then every one or two steps.

**[2]. `backend/masters.py:245-250, 272-284` — Units used only by tickets are not frozen, and can be deactivated with open tickets**
- **Problem:** `_unit_is_referenced` counts `person_units` and `equipment` only; its docstring
  "Only equipment rows hold a unit_id" is stale since v12. `tickets.unit_id` is the place of the
  failure (S017 § 5.3) and the site every ticket write is checked at.
- **Failure scenarios:**
  - a machine with tickets moves from `SMTW.FWMILL` to `SMTW.MCC1`; FWMILL now has no equipment
    and no `person_units`, so IT admin can move FWMILL to another site: every old ticket now
    reads that site, SMTW's engineers get 403 on its moves, and the record says the failure
    happened elsewhere (S001 § 5: frozen once used);
  - the emptied unit is deactivated while a ticket is open: inactive units drop out of access
    (`auth_utils.py:329-334`), so the team that should close it gets 404.
- **Fix:** count `tickets` in `_unit_is_referenced` (`LOCK IN SHARE MODE`, as
  `_check_code_frozen`); refuse deactivation while the unit has tickets not closed; tests; fix
  the docstring and Plan § 4.1.
- Found independently by two reviewers. VERIFIED.

**[3]. `backend/tickets.py:719-724`, `tickets_core.py:309` — A ticket already raised again as a repeat can still be sent back; the same stop then counts twice**
- **Problem:** S018 CR1-02 made *raise again* refuse a ticket that was sent back; the mirror rule
  is missing. `_send_back` and the page (`TicketDetailView.vue:194-209`) ignore `repeats`.
- **Failure scenario:** TK-014 back in service at 10:00; the press stops at 10:30 and the operator
  raises TK-020 as a repeat; at 11:00 the engineer sends TK-014 back with "machine down again:
  yes". Both tickets are open and critical, and `ticket_times` counts downtime on both for the
  same stop — MTTR, availability and the repeat count (ISO 9001 § 10.2) are all wrong.
- **Fix:** 409 on send-back while a ticket has `repeat_of_id = id`; hide *Send back* while
  `repeats` is not empty; in the raise, re-read the earlier ticket's state `LOCK IN SHARE MODE`
  after the insert (the FK already takes that lock), so whichever commits first wins. Tests.
- VERIFIED.

## MEDIUM

**[4]. `backend/tickets.py:831-839` with `equipment.py:383-394` — A scrap and a ticket edit at the same moment can leave an open ticket on a scrapped component**
- `_check_component` checks "not scrapped" with a plain read in the edit's snapshot; the scrap
  counts open tickets in its own. Interleaved, both pass (S017 decision 6 forbids the result).
  The lock notes (`tickets.py:24-30`, `equipment.py:58-60`) also miss two FK locks (the edit's
  shared lock on the component; a repeat raise's shared lock on the earlier ticket).
- **Fix:** read the component `LOCK IN SHARE MODE` and decide from that row (the FK takes the same
  lock, so no new lock-order edge); correct the lock notes.
- Found by two reviewers. PLAUSIBLE (follows from InnoDB's FK locking; not reproduced).

**[5]. `backend/tickets_core.py:306, 311` — *Not a fault* is refused once anyone pressed *Start* (user's call)**
- Start is allowed straight from raised (the technician presses it on arrival), but not-a-fault
  only from raised or acknowledged. "Went, looked, nothing wrong" after Start must end as a close
  with an action and labour, so it counts as a failure in MTBF and MTTR. Whether a ticket is
  excluded from the KPIs then depends on a button press, not on what was found.
- **Fix:** allow not-a-fault from in progress, or record the rule as a decision. VERIFIED.

**[6]. `frontend/src/views/tickets/RegradeDialog.vue:24, 41, 78-95` — *Machine stopped* shows nothing when refused**
- In "stopped" mode the intensity field is not rendered, but its error is filtered out of the
  top message. Two operators tapping *Machine stopped* on the same defect: the second gets 400
  "Already a breakdown" on `intensity`, nothing shows, Save seems to do nothing.
- **Fix:** show the error, and reload the ticket. VERIFIED.

**[7]. `backend/auth_utils.py:73-78, 130-141` — The key-list evict-and-retry still amplifies unauthenticated requests (previous [2], open)**
- Any decode failure drops the cached key client and fetches again, bypassing PyJWT's cooldown,
  with a 30 s default timeout on 3 sync workers. A Keycloak outage reads to the user as "Your
  account is not in the maintenance team" (`stores/auth.js:80-82`).
- **Fix:** drop the retry, `PyJWKClient(uri, timeout=5)`, map a fetch failure to 503; correct
  step 5 of the base doc's token flow upstream. VERIFIED.

**[8]. `frontend/src/stores/auth.js:46-59`, `RaiseTicketView.vue` — Typed input is lost on a failed token refresh, and the raise screen has no leave guard (previous [3], open)**
- `getToken()` calls `keycloak.login()` on any refresh failure — a mobile-data blip discards an
  open dialog's input. The raise screen is a full-page form with no `onBeforeRouteLeave` /
  `beforeunload` guard. Both break the base rule "never lose typed input", now that tickets are
  raised from phones.
- **Fix:** surface the error and offer "Sign in again"; add a leave guard to full-page forms.
  VERIFIED.

**[9]. `backend/api_common.py:64-67`, `db_helpers.py:27-32` — No JSON error handlers; a DB that dies mid-request gives an HTML 500 (previous [6], open)**
- Unknown `/api/*` paths, wrong methods and unhandled exceptions return Flask's HTML pages. A DB
  that dies while the pool holds idle connections passes checkout and raises `OperationalError`
  on the first `execute`, which nothing maps to 503 (S001 CR2-01, accepted then, now cheap).
- **Fix:** handlers for `HTTPException` → `{error}` with its status, other exceptions → logged
  `{error: "Internal error"}` 500, `OperationalError` 2xxx → 503. VERIFIED.

**[10]. `tooling/build/build.bat:49, 57, 72-77` — Push failures are ignored, and a version tag can be overwritten (previous [17], open and wider)**
- The four `docker push` calls are unchecked, so a failed push can still let the release deploy a
  tag the registry lacks. Run by hand, `build.bat` builds the working tree and re-pushes
  `:0.1.3` with S006–S018 code — a deploy then rolls out v6–v13 under the old version number. It
  also still wipes `scratch\*` (the dependency report and S024's logs live there).
- **Fix:** `if errorlevel 1 exit /b 1` after each push; refuse unless the tree is clean and HEAD
  is at `v%VERSION%`; refuse to overwrite an existing tag; stop wiping `scratch\`. VERIFIED.

**[11]. `backend/masters.py:969-999, 1117-1126`, `masters_core.py:51-61`, `auth_utils.py:242`, `app.py:22` — The access-change trail can be incomplete and forged**
- (De)activating a person with a login changes their access but writes no log line (only site
  changes log), so "who restored the leaver's access" is lost (ISO 27001 A.5.18, A.8.15).
- A person's name may contain a line break (`parse_name` strips only the ends); the `login saved`
  line embeds it, so an engineer can plant a fake line in the trail. An unauthenticated `%0A` in
  the path and an attacker-chosen key id reach log lines raw the same way.
- **Fix:** log every `active` change on a person with a login; collapse whitespace in names (as
  manufacturers do); a logging filter that escapes `\r\n` (or `%r`). Later: an append-only
  `access_changes` table (hindsight 3). VERIFIED.

**[12]. `tooling/build/nginx.conf:10`, `backend/network_core.py:39`, `settings.py:204-219` — The network gate is unverified in production and easy to switch off by mistake**
- The code is right (only `X-Real-IP`, set by nginx after `real_ip`; spoofing tested), but S013's
  manual checks are unticked, and `set_real_ip_from` trusts the whole `10.24.0.0/23`, so any host
  there can forge the client address. Any range is accepted as internal: `0.0.0.0/0`, or a typo
  like `10.24.0.0/1` (`strict=False` makes it `0.0.0.0/1`), silently disables the gate.
- **Fix:** do the S013 checks (a device-checks row); narrow `set_real_ip_from` to the front proxy;
  refuse ranges broader than /8 (and the IPv6 equivalent). VERIFIED in code; production PLAUSIBLE.

**[13]. DRY — near-copies and backend rules repeated in the frontend**
- `masters.py` (1,167 lines): plain list routes copied five times (296, 399, 658, 682, 727);
  filter blocks four times (230, 342, 468, 557); three create and one update routes re-implement
  `_create_plain_master` / `_update_plain_master`; `_lock_site_for_unit` ≈ `_lock_active_parent`;
  `_parse_trade_ids` ≈ `validate_unit_ids` (S010 CR1-02, deferred with no step).
- The queued "shared unit-access helper" has grown to six copies (`equipment.py:472, 565, 617`,
  `documents.py:501` ×2, `tickets.py:129`); `', '.join(['%s'] * n)` is hand-built 15 times.
- Frontend copies: `siteRoles.js` re-implements the role rules (`no_login_role_error`,
  technician-only) though S011 A1 says the frontend computes no RBAC; `CAUSE_GROUPS`,
  `EMPLOYMENT`, `TITLE_MAX` (×3), `MB` (×3), `MAX_LABELS`, the upload range 1–100; the S006
  deferred items (previous [5]) all still open and spread to `RaiseTicketView.vue`.
- **Fix:** one tidy-up step: `_list_plain` / `_list_filtered`, `unit_scope()` and
  `in_placeholders()` helpers, server-sent `role_choices` and limits, one `SCRAPPED_MESSAGE`.
  VERIFIED.

**[14]. `frontend/tests/navigation.test.js:8-22` — Role fixtures have drifted further (previous [8], worse)**
- The comment says "kept equal to test_rbac.py"; 5 of 6 roles now differ (engineer, manager and
  IT admin lack `failure_codes:edit`, the four S018 `ticket:*` keys and `access_log:view`; the
  operator lacks `ticket:restore`).
- **Fix:** generate one fixture from `config_rbac.py` that both suites read (base Testing
  Layer 4). VERIFIED.

**[15]. `docs/` — No module or schema docs; the current rules are spread over ~9 superseding texts per area (previous [4], open and larger)**
- There is still no `Module-*.md`, `Schema.md` or `schema.sql`. Team alone is defined by S010 A1,
  S011 A1, its gate answers and S017 § 5.9; documents by S006, S008, S012, S017, S018 and three
  impl-report departures. One consequence found here: the criticality badges were re-coloured
  blue by an unrecorded change (finding [24]).
- **Fix:** `Module-Masters.md`, `Module-Equipment.md`, `Module-Documents.md`,
  `Module-Tickets.md`, `Schema.md`; export `schema.sql` (`mariadb-dump --no-data`) at each step's
  Done gate; add "module doc updated" to the gate. About 2 days.

## LOW

16. **`backend/auth_utils.py:85-87, 151-162` — Token checks are thin (previous [11], open).** No
    issuer check; `exp`/`iat` not required; `leeway=0`, so clock skew between Keycloak and the app
    can fail the first `/auth/me` after login; `typ` not checked. **Fix:** `issuer=realm_url`,
    `leeway=30`, `require=["exp","iat","iss"]`, check `typ`.
17. **`backend/documents.py:83, 363-368` — Permission-checked files are cached an hour.** `private,
    max-age=3600` without `Vary: Authorization`: on a shared kiosk the next user can be served a
    cached file without the access check. **Fix:** `private, no-cache` (the ETag still gives 304).
18. **`backend/app.py:64-66` — The 503 body shows the DB error to every user (previous [14],
    open);** `/api/settings/db-status` also shows host, port and error to managers from the
    internet. **Fix:** log the detail, return a plain message.
19. **`tooling/build/nginx.conf:17-40` — Headers and timeouts (previous [15], [16], open).**
    `/assets/` drops `nosniff`, `X-Frame-Options`, `Referrer-Policy`; no CSP (all assets are
    self-hosted, so `default-src 'self'; connect-src 'self' https://sso.mspv.app; img-src 'self'
    blob: data:; object-src 'none'; frame-ancestors 'self'` fits); no `proxy_read_timeout` above
    gunicorn's 120 s. Check HSTS at the front proxy.
20. **`backend/app.py:179-181`, `frontend/vite.config.js:17` — Dev servers listen on the LAN
    (previous [19], open).** With the run config's `DEV_AUTH_BYPASS=1`, Vite's `0.0.0.0` plus its
    `/api` proxy also exposes an admin API on port 5176. **Fix:** both on 127.0.0.1 by default.
21. **`backend/worker.py:52-54, 84-125`, `local_db.py:24-26` — Worker robustness.** "Due" compares
    the container's clock with a DB-stamped `MAX(created_at)` (a skew can enqueue twice — harmless
    for the purge, not for S021 alerts or phase-4 PM generation); a dead worker session can hold
    the singleton lock for hours (no `wait_timeout`/`read_timeout`); lock names are server-wide,
    so a second Yantra database on the same MariaDB gets no worker. **Fix:** `SELECT NOW()` for the
    schedule, session timeouts on the worker connection, lock names from `DB_NAME`.
22. **`tooling/run-tests.bat` — The frontend build is not a release gate.** It first runs inside
    `docker build`, after the release commit and tag. **Fix:** call `run-frontend-build.bat`.
23. **Dependencies.** `flask-cors` (previous [9]) and `python-dotenv` (previous [10]) still in
    `pyproject.toml`; production CORS allows `http://localhost:5176`. `qrcode` has had no release
    for 537 days (`segno` is the maintained alternative). No deprecated APIs found, but pytest does
    not turn `DeprecationWarning` into errors. Base images and `uv` unpinned; an empty `apt-get`
    layer; `.venv` and `.ruff_cache` missing from `.dockerignore` (previous [18]).
24. **Equipment and documents, small.** `status=scrapped` lists are empty unless
    `include_scrapped=1` too, and the fix-up is copied in two frontend places (`equipment.py:446`);
    criticality badges are shades of blue, against S003 § 5.4 (red, amber, grey) and unrecorded —
    grade A looks like *Standby* on the same row (`equipmentLabels.js:37-42`); the move dialog's
    parent search offers parents at sites where the user cannot edit (403 on save); a never-edited
    node shows "Updated · "; IST times without offset in UTC log lines (previous [20]); stale
    comments (`equipment.py:45, 242`, `documents.py:136`, `RemovedDocuments.vue:11`); a scrap plus
    model change in one PUT can deadlock with a part create (API only).
25. **Tickets, small.** The close can be refused on `description` but the close dialog has no
    description field; `repeats` lists tickets later closed as not a fault; the repeat button can
    disagree with the server (site of the old ticket vs the node's, a moved component, a
    deactivated symptom pre-filled); a labour row whose person left the site can only be deleted,
    losing the man-hours (accept the row's existing person on PUT); `tickets.py` (972 lines) mixes
    ten concerns and the page-control rules (271-314) cannot be tested without the DB.
26. **Masters, small.** `DELETE /people/<id>/sites/<site>` answers 404 before 403, so an engineer
    can learn whether a hidden site row exists; lists return `created_by`/`updated_by` logins to
    every role, though S010 A1 masks `people.username`; `_int_filter` still accepts 0 (previous
    [7]); "Site is required" for a malformed id (previous [21]); the login lookup compares under
    the case- and accent-insensitive collation while the own-person rule compares exactly
    (`COLLATE utf8mb4_bin`); dead `upper=` parameter; IT admin's own record offers *Deactivate*,
    always refused.
27. **API shapes.** No `total` on the documents list, `GET /api/tickets/people`, two ticket lists
    (`tickets.py:499, 527`); `POST /labels` returns `{labels}`. Record as departures or align.
28. **Test gaps.**
    - No test runs the production upgrade path (a v5 schema with v0.1.3-shaped rows → v13) — the
      gap that hides [1]; v1–v7 have no migration tests.
    - No test walks every route as a role with no access (25 of 90 gated rules check their key
      inside the route, so a decorator scan cannot prove coverage).
    - No test that `X-Test-Role` is ignored with `TESTING` off; no test of the `DEV_AUTH_BYPASS`
      refusal (previous [12]); none for issuer, algorithm pinning or a key-list fetch failure.
    - The TK serial's IST month boundary is not pinned (a slip to UTC passes except 00:00–05:30
      on the 1st); the threaded snapshot test changes only the locked column.
    - Frontend: `auth.js`, `equipment.js` (`pickableUnits`), `withoutExtension` untested; no
      component or browser tests (~8,100 untested lines of views, components and composables —
      S024 is adding browser tests).

Accepted earlier and not re-raised: S001 CR1-09 and CR2-01 (except as part of [9]); S002's scrap
vs re-parent deadlock; S003 CR1-03, CR1-08; S007's Android Back; S018 CR5-01 (left by the user);
S018 § 5.1's ordered-events rule (decided by the user).

## Previous audit (16-10-2026) — status

| Item | Status |
|---|---|
| [1] S009 in the working tree | **Done** (dropped, code kept as a patch) |
| [2] JWKS evict-and-retry | Open → [7] |
| [3] Token refresh redirect | Open → [8] |
| [4] Module and schema docs | Open, larger → [15] |
| [5] S006 deferred items | Open, spread → [13] |
| [6] JSON error handlers | Open → [9] |
| [7] `_int_filter` | Open → [26] |
| [8] Role fixtures | Open, worse → [14] |
| [9] flask-cors, [10] python-dotenv | Open → [23] |
| [11] Issuer check | Open → [16] |
| [12] DEV_AUTH_BYPASS guard test | Open → [28] |
| [13] Test header in production code | Kept on purpose (fails closed without a factory; S024 builds on it); a `TESTING`-off test is missing → [28] |
| [14] 503 detail | Open → [18] |
| [15] `/assets/` headers, [16] nginx timeout | Open → [19] |
| [17] build.bat | Open, wider → [10] |
| [18] Build hygiene | Open → [23] |
| [19] Dev server on 0.0.0.0 | Open, Vite too → [20] |
| [20] IST log offsets | Open → [24] |
| [21] Small items | `api.js` `code` note no longer applies (S013 sends `code`); the rest open → [24], [26], [27] |

**None of the nine security items moved in seven steps, and none was queued** — the previous
audit's recurring pattern ("deferred items without a home step get lost") repeated.

## Base conformance

The base doc was re-synced from smtw-common today (uncommitted in the working tree, with the new
`smtw-review` skill and `sync_common.py`); its only change is the access-log rule that came from
Yantra's own S013 A1, which Yantra meets.

**Conforms:** stack; RBAC (with the S011 deviation recorded); frontend auth and sidebar; internet
exposure (X-Real-IP, deny-list gate, access log with DB dedupe, retention); blueprints and pure
cores; DB connection code; migrations (13 append-only versions — `git log -p` shows no removed
line, and the v7/v10 in-place edits predate their first commit); business settings; secrets;
env/config; observability (slow-request logger); worker and queue; serial numbers (`TK-YYYY-MM-NNN`
from a counter row); file upload; versioning and stale-bundle detection; shared tooling sync;
testing layers 1–4; layout, navigation, CSS, sidebar, topbar, view structure, form/modal, print
views.

**Missing:**
1. Module and schema docs — [15]; about 2 days.
2. JSON error handlers — [9]; about 1 hour.
3. Prod data tooling (`replicate_prod_to_local.py`, `prod_readonly.py`, `run-prod-query.bat`, the
   `read-prod-data` skill, a read-only DB user) — half a day to a day from VelKilnMaster; less
   urgent while production holds little data.
4. "Never lose typed input" outside modals — [8]; half a day.
5. Sortable columns and explicit widths on the equipment list — 2–3 hours, low value.

**Outdated:**
1. Token validation — [7], [16]; about 2 hours, and the base's step 5 itself needs correcting.
2. `/assets/` security headers, no CSP — [19]; 10 minutes (half a day for a CSP).
3. Cross-language fixtures — [14]; 1–2 hours.
4. Settings view against the navigation-hierarchy and edit-toggle patterns (seven stacked cards,
   always-open inputs for set-once values, five copied load/save blocks) — half a day, low–medium.
5. Timezone policy in the deploy: `TZ: Asia/Kolkata` on the containers
   (`smtw_erp_devops/erp_server/yantra/compose.yml.j2:22, 41`) puts logs in IST against the base's
   "logs stay UTC"; the same line is in other apps' composes — decide upstream which rule stands.
6. Unrecorded variant: `check_perm` inside the route on the document and move routes — record it
   in `CLAUDE.md` and add the route-walk test of [28].

**Skipped (not applicable or recorded as deliberate):** multi-tenancy; MinIO; APScheduler,
deny-list gate and site roles (recorded); PWA shell (recorded gap); external integrations,
approval workflow, phase completion, monitoring daemon, sync-status columns; Redis; migration
squashing; event sourcing (tickets store their state, with an append-only timeline — by design);
Telegram (due with S021).

**Repo ahead of the base — worth upstreaming to smtw-common:** the S022 dependency check
(`tooling/deps/`, `sbom/`, OSV, exit codes); the step workflow (`docs/steps/README.md`, `/step`,
three agents, stale brief check, tracks); starting without a database (`ensure_schema` retry,
`DBUnavailable` → 503, `/auth/me` from the token); the DB-queue scheduler deciding "due" from its
own history, poison-task caps and the "Overdue — is the worker running?" card; site-scoped RBAC
(`SITE_SCOPED`, `has_perm_at`, pure `access_core`, `ROLE_INCLUDES`) and `check_perm`; moves and
permissions sent by the server for the record's site; atomic upload writes (`os.replace`) with
type checked by content; the one-statement serial counter; list state in the URL query with a
`loadSeq` guard. Base text to correct: token step 5, an explicit issuer check, drop `flask-cors`
from the bootstrap list, "never lose typed input" for full-page forms and token refresh, the
TZ-on-containers rule.

## Hindsight review

1. **Domain fit.** `Plan.MD`, `Maintenance-Philosophy.md` and `Plant-Facts.md` are accurate and
   kept up step by step; the code handles nothing they don't describe. Three domain points will
   cost more the longer they wait:
   - **Position vs item** (ISO 14224's functional location): S017 already had to rule that a
     re-parented component keeps the ticket's machine; PM plans on physical items would travel
     with a swapped motor. Decide in the PM brief.
   - **Document kind mixes file format with purpose** (photo / document / drawing): Plan § 4.1's
     kind pick-list and missing-drawings list will have to untangle it across three owners;
     cheapest now — format from the bytes, category as its own field.
   - **KPIs need intervals, not totals:** `ticket_times` returns totals per ticket, so a
     three-week stop cannot be split by month, two critical tickets on one machine count one stop
     twice ([3] creates exactly that), and "breakdown" means the *current* intensity, so a
     breakdown later lowered drops out of MTTR. Return (start, end) intervals and a
     `was_breakdown` flag from the events before the KPI step.
2. **Architecture.**
   - **The REPEATABLE READ discipline is unwritten.** Every write relies on "lock first, first
     plain read after it", explained only in docstrings that already miss two FK locks. Two of
     this audit's findings ([3]'s raise side, [4]) are this class. Before phase 3–4 add writes,
     either use locking reads (`FOR SHARE`) for every cross-table rule check, or run write
     transactions in READ COMMITTED — and write the rule and one lock table in a module doc.
   - **Two sources of truth for a ticket:** the row's `state`/`intensity` drive the moves,
     `ticket_times` rebuilds state from the events, and nothing checks they agree. The queued
     "correct an event time" and S019's scheduled state will each touch one side. A pure
     `project(events)` asserted equal to the row in the API tests closes it. `edited` events keep
     only label text, so the operator's symptom vs the engineer's can never be measured — store ids.
   - **Repair time after a send-back** counts waiting as hands-on (EN 13306 calls it logistic
     delay); S019's waiting split needs a work-stopped / resumed event pair, which touches
     `MOVES`, the state ENUM and `ticket_times` together.
   - **Site-scoped keys double as global keys** (`equipment:edit` on manufacturers and models,
     `equipment:purge_documents` on model documents): an engineer at one plant edits masters for
     all plants. A separate global key (e.g. `equipment_masters:edit`) would make "site-scoped"
     mean what it says.
   - **The deny-list gate fails open** for any future token role; admin bypasses it while IT
     admin, who now holds every key, is kept inside; the security reads (`settings:read`,
     `access_log:view`) are manager keys usable from mobile data. A test that every token role is
     either internal-only or allowed with a dated reason makes each new role a decision. Enforce
     OTP on admin (Keycloak.md § 3.1).
   - **Team is an access-control subsystem inside the code-list masters** (~450 of masters.py's
     lines, its own lock order, visibility rules tested only through the API). A `team.py` plus a
     pure `team_core.py` would make the access rules reviewable on their own.
3. **Technical debt, by cost of delay:**
   1. **Release cadence and the v9 guard** [1], [10] — every machine typed into production makes
      the next release riskier; rollback is a restore with no backup step.
   2. **Integrity at the module seams** [2], [3], [4] — wrong history and double downtime, before
      the floor uses tickets.
   3. **An auth-hardening step** — [7], [8], [9], [11], [12], [16]–[20]; about a day; internet
      exposure grew with every step since S013.
   4. **"Referenced by" is a hand-kept list** — S017 added `fk_tickets_unit` and nobody revisited
      the unit freeze ([2]); PM jobs, readings and rounds will add more FKs. Check the freeze and
      deactivate rules against `information_schema` foreign keys in a test.
   5. **Module and schema docs** [15] — the cost grows with every step.
   6. **The tidy-up** [13], [14] — and the queued unit-access helper, now six copies.
   7. **The orphan-file sweep and a retention rule for removed documents** — unblocked since the
      worker exists (S013); also each new document owner grows the removed list by hand (a UNION
      branch, a builder, a `v-if`) — let each `Owner` supply its branch.
4. **If starting again:**
   - Release every one or two steps, with a backup and a schema-ready check in the deploy.
   - Module docs as the living source of truth from S001, briefs as change records.
   - READ COMMITTED (or locking reads everywhere) for write transactions, written down once.
   - Browser tests from the first screen (S024 now), so "checks pending" never piles up — nine
     committed steps are not `Done` today.
   - Keep: pure core and thin shell, the server sending moves and permissions per record, URL
     query state, the step workflow with its reviews, the S022 dependency check.

## Summary

**Health: good.** Business logic matches the briefs; RBAC is complete and tested; SQL, files,
timezone and migrations follow the base. The risk is concentrated in **the next release** (v9 on a
production that may already hold equipment, no backup, a deploy check that cannot see a DB
failure) and in **seams between modules** (units vs tickets, send-back vs repeats, scrap vs ticket
edit) that the per-step reviews could not see.

**Top 3 priorities:**
1. **Before the next release:** read production's schema version and equipment count; add the v9
   precondition, a pre-deploy backup and a schema-ready check; fix `build.bat` [1], [10].
2. **Ticket integrity:** freeze units used by tickets and block deactivation with open tickets;
   refuse send-back after a repeat; lock the component check [2], [3], [4].
3. **Give the open items a home:** queue an auth-hardening step and a tidy-up step in the README,
   and write the module docs [7]–[9], [11]–[15].

**Recurring patterns:**
- **Deferred items without a home step get lost** — for the second audit running (all nine
  security items, S006's and S010's deferrals, the queued helper "due with S017").
- **Rules live in more than one place** — backend rules re-derived in the frontend, constants
  copied, the current rule spread over superseding briefs.
- **Implicit invariants** — lock order and snapshot discipline in docstrings, "referenced by" and
  the removed list kept by hand, fixtures "kept equal" by comment.
