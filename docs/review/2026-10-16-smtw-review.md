# Yantra audit — whole repo, read against `docs/steps/*`

```
Doc: codebase audit (/smtw-review)
Author: Claude (Opus)
Date: 16-10-2026
Scope: backend, frontend, tooling; all step briefs S001–S010, Plan.MD, domain docs, SMTW-WebApp-Base.md
```

I read the whole codebase against all ten step briefs, `Plan.MD`, the domain docs and
`SMTW-WebApp-Base.md`. The full suite passed at audit time: 697 backend and 36 frontend tests.
Findings [2] and [6] were checked by running them.

**S009 was dropped by the user after the audit (16-10-2026).** The audit was made on the working
tree, which still held S009's uncommitted code; file and line references are to that tree. Finding
[1] is rewritten for the drop.

The business rules from S001–S008 are built faithfully. Nothing critical was found. Most findings
are about the edges: auth behaviour, process leaks and documentation structure.

## HIGH

**[1]. Working tree — S009 is dropped, but its uncommitted code is still in the working tree**
- **Problem:** the tree still carries S009: migration v7 in `backend/local_db.py` (owner columns
  and `chk_equipment_documents_owner` on `equipment_documents`), the owner table in
  `backend/documents.py`, `file_store.py`'s owner folders, the tests, and the frontend move to
  `components/documents/`. Committed by accident, v7 would reach production as an applied
  migration that can't be taken back (migrations are append-only). Had S009 shipped without its
  amendment A1, removed class/type documents could never have been restored or erased.
- **Fix:**
  - revert the S009 changes in the working tree (keep or move the step files as you prefer);
  - the dev and test DBs have applied v7: reset them with `tooling/dev/dev-db-reset.bat` (they
    are disposable);
  - mark S009 `Dropped` in `docs/steps/README.md`, and drop the queued row "Class and type
    documents on the removed-documents screen";
  - S010's brief says "Depends on S009 committed" and "migration v8": update it to v7 and drop
    the dependency.

## MEDIUM

**[2]. `backend/auth_utils.py:87-97, 55` — Token retry turns forged tokens into repeated key fetches**
- **Problem:** on any decode failure the code discards the cached key client and builds a new
  one, which defeats PyJWT's built-in 30 s cooldown. Measured:
  - a forged token with an unknown key id costs 2–3 synchronous key-list fetches from Keycloak;
  - every expired genuine token costs one needless fetch.
- **Why it matters:** each fetch can block for up to 30 s (the default timeout). With 3 sync
  workers and a public front proxy, a handful of unauthenticated requests can stall the backend.
- **Fix:** drop the manual evict-and-retry (PyJWT already refreshes once on an unknown key id,
  with a cooldown); pass `timeout=5` to `PyJWKClient`; update step 5 of the base doc's token
  decode flow in `smtw-common`, which prescribes the pattern.

**[3]. `frontend/src/stores/auth.js:36-43` — A failed token refresh redirects away and loses typed input**
- **Problem:** `getToken()` calls `keycloak.login()` on any `updateToken` failure, including a
  network blip on mobile data and a background thumbnail fetch. The full-page redirect discards
  whatever is typed in an open dialog — against the base rule "Never lose typed input", with
  phones on mobile data as the main use case (Plan § 1).
- **Fix:** on failure, throw an error the dialog shows ("Connection problem — try again") and
  keep the input; show a "Sign in again" banner and redirect only when the user taps it.

**[4]. `docs/` — No module or schema docs; current rules are scattered across the step files**
- **Problem:** to know today's documents rules you read S006 and S008, plus review logs and
  impl-report departures ("the report wins over the brief"). There is no `Module-*.md`,
  `Schema.md` or `schema.sql`, which the base layout expects.
- **Fix:** write `docs/Module-Masters.md`, `Module-Equipment.md`, `Module-Documents.md` and
  `Schema.md`, and export `schema.sql` from the dev DB; add "module doc updated" to the Done gate
  in `docs/steps/README.md` (the `update-docs` skill fits this).

**[5]. S006 CR1-04/05/07/08 — Deferred findings with no target step are still open**
- **Problem:** `docs/steps/README.md` says a deferral names the step it goes to; these name none,
  so they were dropped. Still in the code:
  - the scrapped message is duplicated (`documents.py` `SCRAPPED_MESSAGE` and `equipment.py:476`);
  - `TITLE_MAX` is copied in the upload and title dialogs;
  - the settings range 1–100 is mirrored in `SettingsView.vue:39-40`;
  - a photo just over the cap says "Photo too large (50 megapixels)" (`documents_core.py` `_megapixels`);
  - title edit and `/thumb` by a user from another unit are untested (`test_documents_api.py`
    `test_another_units_node_is_404`);
  - any oversized body gets the file-upload 413 message (`api_common.py:56-60`).
- **Fix:** add them to the README's Queued table under a tidy-up step, as S005 did.

**[6]. `backend/api_common.py:63-66` — Errors outside the handled cases come back as HTML, not JSON**
- **Problem (verified):** an unhandled exception gives Flask's HTML 500 page; an unknown `/api/*`
  path an HTML 404; a wrong method an HTML 405. The UI then shows "INTERNAL SERVER ERROR".
  Accepted-rare deadlocks surface this way. The base convention is `{"error": "Internal error"}`, 500.
- **Fix:** register a handler turning `HTTPException` into `{error}` with its own status, and any
  other exception into a logged `{error: "Internal error"}` 500.

## LOW

7. **`backend/masters.py:78-86` — `_int_filter` duplicates `api_common.int_arg` with different rules**
   (accepts `0`, different message). Use `int_arg(name, None, minimum=1)`.
8. **`frontend/tests/navigation.test.js:4-11` — Role fixtures have drifted from `test_rbac.py`.**
   MANAGER and IT_ADMIN lack `equipment:purge_documents` (S008), though the comment says "kept
   equal". Add it; better, generate one fixture both tests read.
9. **`backend/app.py:36`, `backend/pyproject.toml:9` — `flask-cors` is dead weight.** Vite proxies
   `/api` in dev and nginx in prod, so every call is same-origin. Remove `CORS(...)` and the dependency.
10. **`backend/pyproject.toml:14` — `python-dotenv` ships in the production image but only tooling
    uses it.** Remove it from the backend dependencies.
11. **`backend/auth_utils.py:59-65` — The token's issuer (`iss`) is not checked**, though the base
    says issuer validation uses the public realm URL. Pass `issuer=realm_url` and add one test.
12. **`backend/config.py:76-78` — The guard refusing `DEV_AUTH_BYPASS` outside dev has no test.**
    Add a subprocess test that it raises without `FLASK_DEBUG=1`.
13. **`backend/auth_utils.py:177-179` — A test-only auth skip (`TESTING` + `X-Test-Role`) lives in
    production code.** Safe while nothing sets `TESTING`, but fragile. Move the injection into `conftest.py`.
14. **`backend/app.py:55-57` — The 503 body shows every role the DB error, host/IP included.** Log
    the detail; return "Database unavailable — try again shortly".
15. **`tooling/build/nginx.conf:23-26` — `/assets/`'s own `add_header` drops the server-level
    security headers** (no `nosniff` on JS/CSS); no Content-Security-Policy. Repeat the three
    headers there, as `/` does; consider a CSP.
16. **`nginx.conf:29-40` vs `gunicorn.conf.py:6` — nginx gives up after 60 s, gunicorn allows 120 s.**
    A slow NFS write returns 504 but still commits; a retry duplicates the upload. Set
    `proxy_read_timeout 125s` in `/api/`.
17. **`tooling/build/build.bat:71-77, 80-82` — `docker push` failures aren't checked;** the script
    still says "Build complete" and the release goes on to deploy. It also wipes `scratch\*`. Add
    `if errorlevel 1 exit /b 1` after each push; drop the cleanup.
18. **`Dockerfile.backend:1,7-8,16`, `Dockerfile.frontend:12` — Build hygiene.** The `apt-get` layer
    installs nothing but runs `apt-get update` every build; `uv` and base images are unpinned. Drop
    the empty layer; pin the versions.
19. **`backend/app.py:149-151`, `vite.config.js:17` — The dev backend binds `0.0.0.0` with debug on
    and `DEV_AUTH_BYPASS`,** exposing an admin API and the Werkzeug debugger to the LAN. Bind the
    backend to `127.0.0.1`; Vite's proxy still reaches it.
20. **`backend/documents.py` restore/purge log lines — IST times printed without offset inside
    UTC-stamped lines.** Add `+05:30`.
21. **Small items:**
    - `api.js:17-25` documents a `code` field the API never sends;
    - `AppSidebar.vue:46-55` uses an Options-API block for the version;
    - `AppBottomNav.vue:28-35` has `<a role="button">` without `href`/`tabindex` (not keyboard-reachable);
    - `EquipmentDetailView.vue:143-144` shows "Updated · " for a never-edited record;
    - `masters_core.py:77-82` says "Site is required" for a malformed id;
    - the documents list `{items, upload_max_mb}` has no `total`.

Accepted earlier and not re-raised: S001 CR1-09 (v3 migration not re-run safe) and CR2-01 (a
mid-day DB restart gives 500, not 503; first-time unit grants can deadlock); S002's scrap vs
re-parent deadlock; S003 CR1-03 and CR1-08; S007's Android Back dropping an open dialog.

## Base conformance

**RBAC:** every route carries `@require_perm` (listed programmatically); the keys match
`config_rbac.py` and Plan § 3.

**Missing:**
- `Module-*.md`, `Schema.md`, `schema.sql` (see [4]) — about 1–2 days.
- Prod data tooling: `replicate_prod_to_local.py`, `prod_readonly.py`, `run-prod-query.bat`, the
  `read-prod-data` skill — about half a day, from VelKilnMaster; worth it now that production
  holds real data.
- JSON error handlers (see [6]) — about an hour.
- Sortable columns on the equipment list (Table / List Pattern) — small effort, low value.

**Outdated:**
- Token validation: no issuer check [11]; the evict-and-retry does harm [2] (the base doc itself
  should change).
- `/assets/` security headers [15].

**Skipped (not applicable or recorded as deliberate):** multi-tenancy; MinIO (Plan § 1);
Telegram, external integrations, approval workflow, phase completion, event-sourcing (phase 3
onward); print views; network gate, access log, `task_queue`/scheduler and PWA shell (recorded in
`.claude/CLAUDE.md` as phase-1 gaps).

## Hindsight review

1. **Domain fit.** `Plan.MD`, `Maintenance-Philosophy.md` and `Plant-Facts.md` are accurate and
   kept up step by step. With S009 dropped, Plan § 4.1 and § 5 still describe documents on classes
   and types — revert those lines. Two gaps will hit phase 3–4:
   - **AMC vendors** (Plant-Facts § 4) are nowhere in Plan's data model. Breakdowns on contract
     equipment need "who do we call, and what response time was promised". EN 13269, the European
     guideline on maintenance contracts, lists what a contract should define (scope, response
     times) — the fields Yantra would need. S010's contract-firm records could link to it.
   - **Position vs item.** ISO 14224 and SAP PM separate a *functional location* (the position,
     e.g. "VBM001's main drive") from the *equipment* (the physical motor fitted there). Yantra's
     nodes are physical items, so PM plans and tickets on a motor would travel with it when it is
     swapped. Decide in the phase-4 brief whether plans attach to the item or to its parent.
2. **Architecture.** S002's write transactions run in REPEATABLE READ (the database default, in
   which a plain read keeps seeing data as of the transaction's first read). That led to "decide
   only from locked rows" and the `_reread` / `_written_state` patches with their 409 "changed
   while saving" paths, at a cost of three brief rounds and two code rounds. Phase 3's ticket state
   machine will meet the same problem. Decide before the breakdowns step whether to keep this
   discipline (documented in a module doc) or run write transactions in READ COMMITTED, where a read
   after a lock sees what others have committed (S002 CR1-01 suggested this, scoped to one transaction).
3. **Technical debt, by cost of delay:**
   1. Revert the dropped S009 [1].
   2. The phase-1 foundation: task queue, worker, scheduler, PWA shell — phase 3's notifications and
      escalation depend on them.
   3. An access log on the internet-exposed app, plus fix [2]. ISO 27001 A.8.15/A.8.16 (logging and
      monitoring) ask for this record; every day without it is audit history that can't be recovered.
   4. Module docs [4]; the cost grows with every step.
   5. Token-refresh behaviour [3], before phones are used for data entry.
   6. Orphaned nits [5] and JSON errors [6].
   7. A job to reconcile orphan files and a retention rule for removed documents (both need the worker).
   8. Unpinned images [18].
4. **If starting again:**
   - Build the Plan § 8 phase-1 foundation before phase-2 features.
   - Use READ COMMITTED write transactions from S002.
   - Keep module docs as the living source of truth, with briefs as change records.
   - Keep the rest: pure core and thin shell, URL-query filters, `my-units`, the form guard, and
     reviews on risky steps.

## Summary

**Health:** good. Business logic matches the briefs, RBAC is complete and tested, and timezone
handling, the pool and migrations follow the base. S010 is in brief review with two `major`
findings open (BR1-01, BR1-02) and depends on S009 as written.

**Top 3 priorities:**
1. Revert S009 from the working tree and update README, Plan and S010 [1].
2. Auth hardening ([2], [3]) and the access log.
3. The phase-1 foundation and module docs before breakdowns start.

**Recurring patterns:**
- Deferred items without a home step get lost.
- Constants are duplicated between backend and frontend.
- Template behaviour carried over unexamined: the JWKS retry, `flask-cors`, unchecked pushes in
  `build.bat`, HTML error pages.
