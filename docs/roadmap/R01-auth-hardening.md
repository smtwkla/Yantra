```
Roadmap: R01 — Auth hardening
Doc: roadmap
Author: Roadmapper (Opus)
Date: 25-10-2026
Status: Approved (KLA, 26-10-2026, gate R)
```

# R01 — Auth hardening

**The point:** ten audit findings from 21-10-2026 are still open in today's code, and none of
them is fixed by S025–S056. This roadmap cuts them into **six steps and one manual check**. The
first useful result is the token checks (R01.2) and the input kept on a failed sign-in (R01.3),
which can be coded in parallel. KLA answered **nine questions** (26-10-2026, § Decisions): all at the recommendation except
Q7.1, log lines only, which makes R01.7 small and drops its table.

## The feature

The audit of 21-10-2026 (`docs/review/2026-10-21-smtw-review.md`) listed security findings that
had moved through two audits without a home step. S025 § 1.8 queued them as **Auth hardening**:
audit [7], [8], [11], [12], [16]–[20] and the auth test gaps of [28]. KLA chose it as the next
work after the ticket and meter modules, before the PM engine.

**Why now (fact):** Yantra is open to the internet so that shop-floor phones on mobile data can
reach it (Plan.MD § 1, "Access from outside"). Every role except IT admin works from outside the
plant. So a weakness in the sign-in, the file cache, the error text or the access trail can be
used from anywhere, not only from the plant network.

**What it is not:** no new module and no change to the maintenance rules. No new data: Q7.1
chose log lines over an access-change table.

## What exists

Each finding checked against the code at HEAD `82997ee` (25-10-2026).

| Finding | State today | Evidence |
|---|---|---|
| [7] key list evict-and-retry | **Open** | `backend/auth_utils.py:73-78` makes `PyJWKClient(jwks_uri)` with no timeout; `:130-141` drops the cached client and decodes again on **any** decode failure, so every bad token costs a key fetch. A Keycloak outage gives 401, which `frontend/src/stores/auth.js:80-82` shows as "Your account is not in the maintenance team". |
| [8] typed input lost on a failed refresh; no leave guard | **Open, and wider** | `auth.js:46-59`: `getToken()` calls `keycloak.login()` on any refresh failure. No `onBeforeRouteLeave` or `beforeunload` anywhere in `frontend/src` (grep empty). Two full-page forms are unguarded: `RaiseTicketView.vue` and, since S040, `views/readings/ReadingsSheet.vue` (a whole site's meter readings on one screen). Dialogs are guarded (`useFormModal.js` `dirty`, `FormModal.vue:32, 55`). |
| [11] access-change trail incomplete and forgeable | **Open** | `backend/masters.py:1195-1196` checks who may (de)activate a person with a login, but no log line follows; only the login save (`:1341`) and a site-role change (`:1350`) log. `masters_core.py:51-57` strips only the ends of a name, so a line break stays inside it. `app.py:24` logs with a plain format and no filter, so `\r\n` from a path or a name reaches the log raw. |
| [12] network gate unverified; too easy to switch off | **Open** (code and production check) | `tooling/build/nginx.conf:10` trusts the whole `10.24.0.0/23` as proxies. `backend/network_core.py:31-44` accepts any range, `0.0.0.0/0` included. S013's real-address check is still unticked (`docs/steps/S013-network-gate-access-log/3-impl-report.md:262`). |
| [16] token checks thin | **Open** | `auth_utils.py:81-87`: only `verify_exp`; no issuer, no required claims, `leeway` 0, no `typ` check. |
| [17] files cached an hour | **Open** | `backend/documents.py:83` `CACHE_MAX_AGE_S = 3600`; `:365-370` sends `private, max-age=3600` with no `Vary: Authorization`. |
| [18] the 503 body shows the DB error | **Open** | `app.py:66-68` answers `f"Database unavailable: {exc}"`. `settings.py:106-113` with `local_db.py:1276-1294` gives host, port and the raw error to every `settings:read` holder, managers included (`config_rbac.py:151`), from the internet. |
| [19] nginx headers and timeouts | **Open in this repo; partly covered at the front proxy** | In this repo: `nginx.conf:23-26` (`/assets/`) re-declares `add_header`, so the three security headers drop there; no CSP; no `proxy_read_timeout`, so nginx's 60 s default cuts requests that gunicorn allows for 120 s (`tooling/build/gunicorn.conf.py:6`). At the front proxy (devops repo, read only): `smtw_erp_devops/nginx/src/conf.d/security-headers.conf:4-19` adds HSTS, `nosniff`, `X-Frame-Options`, `Referrer-Policy` and `Permissions-Policy` to every response; `proxy-params.conf:7` sets 300 s. So production's `/assets/` responses get the headers at the edge (to verify live, R01.1). |
| [20] dev servers listen on the LAN | **Open** | `app.py:210` `host="0.0.0.0"`; `frontend/vite.config.js:31` `host: "0.0.0.0"`. Vite's `fs.allow` (`:34`) already keeps the repo's files off it. The e2e stacks bind `127.0.0.1` already (`frontend/playwright.config.js:76`). |
| [28] auth test gaps | **Partly done** | Done: `X-Test-Role` ignored with `TESTING` off (`backend/tests/test_access_control_api.py:113-118`, S024 BR1-08); no factory gives 401 (`:108-110`). Open: the `DEV_AUTH_BYPASS` refusal (`config.py:76-78`) has no test; no test of issuer, algorithm pinning or a key-list fetch failure (`test_auth.py` covers expiry, signature, client, missing header); no test walks every route as a role with no access (only `test_access_log_api.py:286` reads `url_map`, for one prefix). |
| [9] JSON error handlers | **Done in S025** (not in this roadmap) | `backend/api_common.py:85-101`. |

**Found while reading (fact, new):** the front proxy limits a request to **50 MB**
(`smtw_erp_devops/nginx/src/sites-available/vel-yantra.mspv.app.conf:11`), but Settings allows
an upload limit up to **100 MB** (`backend/config.py:128`) and Yantra's own nginx takes 101 MB
(`nginx.conf:39`). An upload between 50 and 100 MB gets nginx's HTML 413 from the front, not
Yantra's message. See Q5.3.

**What no item rebuilds:** the network gate and access log (S013), the JSON error handlers and
`DB_LOST_TEXT` (S025), the dialog guard (`FormModal.vue`, `useFormModal.js`, S007), the
permission-checked file routes (S006), and the token flow's role mapping (S011).

## Standards

The maintenance standards (TPM, ISO 14224, EN 13306, ISO 55000, SMRP KPIs) do not apply here:
this roadmap changes how the app protects itself, not maintenance work. The standards are
security ones.

**How the numbers are marked.** ISO/IEC 27001:2022 Annex A controls that earlier Yantra steps
already cite are given plain. Controls new to Yantra are marked *to verify*. OWASP ASVS chapter
numbers are from ASVS 5.0 (May 2025) as I know it, and are all *to verify* against the published
text; no requirement numbers are given.

| Standard | What it says, in plain words | How R01 follows it | Items |
|---|---|---|---|
| **OWASP ASVS 5.0, V9 Self-contained Tokens** (to verify) | A server that accepts a signed token checks who issued it, that it has not expired, what kind of token it is, and that the signing method is one it expects. | R01.2 checks the issuer, requires `exp`, `iat` and `iss`, checks `typ`, and keeps RS256 the only method. | R01.2 |
| **RFC 8725, JSON Web Token Best Current Practices** (section numbers to verify) | The same rules from the IETF: pin the algorithms, validate the issuer, use explicit typing. | As above. | R01.2 |
| **OWASP ASVS 5.0, V7 Session Management** (to verify) | A session that ends or fails is handled so the user knows and the app does not act on a stale sign-in. | R01.3 tells the user that the sign-in ended and offers *Sign in again*, instead of a silent redirect. | R01.3 |
| **OWASP ASVS 5.0, V8 Authorization** (to verify) | Every function checks access on the server, and this is tested. | R01.6 walks every API route as a role with no access. | R01.6 |
| **OWASP ASVS 5.0, V3 Web Frontend Security** (to verify) | The browser is told how to treat the app's pages: no sniffing of content types, no framing by other sites, and a content security policy (CSP) that names where scripts and calls may come from. | R01.5 sends the headers on every response and adds a CSP. | R01.5 |
| **OWASP ASVS 5.0, V13 Configuration** (to verify) | Debug and development features are not reachable by others. | R01.5 binds the dev servers to the laptop itself. | R01.5 |
| **OWASP ASVS 5.0, V14 Data Protection** (to verify) | Sensitive data is not kept in caches where another user can read it. | R01.4 marks files `no-cache`, so the browser asks the server (and its access check) every time. | R01.4 |
| **OWASP ASVS 5.0, V16 Security Logging and Error Handling** (to verify) | Error messages tell the user what to do and hide internal detail; log lines cannot be forged with user input; security events are logged. | R01.4 hides the DB error; R01.7 escapes line breaks in logs and logs every access change. | R01.4, R01.7 |
| **RFC 9111, HTTP Caching** (fact) | `private` lets the browser store a response; `no-cache` makes it check with the server before each use; the ETag then answers 304 cheaply. | R01.4 uses `private, no-cache`. | R01.4 |
| **ISO/IEC 27001:2022 A.8.5 Secure authentication** (to verify) | Sign-in is done by a sound method, and its failures are handled safely. | R01.2, R01.3. | R01.2, R01.3 |
| **ISO 27001 A.5.18 Access rights** | Access is given, changed and taken away by a recorded process, and reviewed. | R01.7 records every change to a person's access. | R01.7 |
| **ISO 27001 A.8.15 Logging** | Logs record activities and are protected from tampering. | R01.7 stops forged lines and logs every access change. Loki will keep the lines outside the container (KLA's plan, Q7.1). | R01.7 |
| **ISO 27001 A.8.20 Networks security** | Networks and the devices on them are managed and controlled. | R01.1 verifies the gate in production; R01.5 narrows the trusted proxy and refuses ranges that would switch the gate off. | R01.1, R01.5 |
| **ISO 27001 A.8.9 Configuration management** | Security settings of hardware, software and networks are set, recorded and kept. | R01.5's headers live in the image's `nginx.conf`, in git. | R01.5 |
| **ISO 27001 A.8.12 Data leakage prevention** (to verify) | Measures stop data from leaking to people who should not see it. | R01.4 (file cache, DB detail). | R01.4 |
| **ISO 27001 A.8.31 Separation of development, test and production environments** (to verify) | Development systems are kept apart, so a dev shortcut cannot reach real users or data. | R01.5 keeps the dev server, which skips sign-in, off the LAN. | R01.5 |
| **ISO 27001 A.8.29 Security testing in development and acceptance** (to verify) | Security functions are tested before release. | R01.2's token tests and R01.6's route walk. | R01.2, R01.6 |
| **ISO 9001:2015 § 7.5.3 Control of documented information** (to verify) | Records are protected from loss and unintended change. ISO 9001 is a future goal for the plant. | Not met by R01: Q7.1 chose log lines; the lasting record is Loki's, outside this repo. | R01.7 |

**Base doc (SMTW-WebApp-Base.md) to correct upstream:** its token flow step 5 says "on decode
failure, evict the cached JWKS client and retry once" (`.claude/SMTW-WebApp-Base.md:116`). That is
the cause of [7]. Its "never lose typed input" rule (`:1187`) covers dialogs only. The base doc is
synced from smtw-common, so R01.2 and R01.3 each give the corrected text in their impl report, and
KLA applies it in smtw-common (as S025 item 9 did).

## Showcase

None (KLA, 25-10-2026: no deck for this roadmap). The items that change text on screen give that
text below (CLAUDE-COMMON scope B).

## Items

| Item | Goal | Size | Track | Depends on | Status |
|---|---|---|---|---|---|
| R01.1 | Check the network gate and the headers in production (manual, KLA) | S | manual check, no step | — | partly done: checks 1, 3, 5 pass; 2, 4, 6 open |
| R01.2 | Token checks: no evict-and-retry, a timeout, issuer and claims checked, a login-server outage reads as such | S | full | — | → S059, 26-10-2026 |
| R01.3 | Keep typed input: a failed sign-in renewal keeps the screen; a leave guard on the two full-page forms | M | full | — | open |
| R01.4 | What the server sends: files not served from cache, no DB detail in errors or to managers | S | full | — | open |
| R01.5 | Web server and network: headers on every response, a CSP, timeouts, a narrower trusted proxy, a range check, dev servers off the LAN | M | full | R01.1 | open |
| R01.6 | Route walk: every API route tried as a role with no access | S–M | full | — | open |
| R01.7 | Access-change trail: forged log lines stopped, every access change logged (log lines only, Q7.1 a) | S | full | R01.4 | open |

### R01.1 — Check the network gate and the headers in production (manual)

- **Goal:** prove that the gate sees real client addresses in production, before anything else
  in R01 relies on it. Closes S013's open check (impl report line 262) and audit [12]'s
  "unverified in production".
- **Why manual:** Claude is read-only on production, and the check needs a phone on mobile data.
  It is not a step; the orchestrator adds these as rows of `docs/steps/device-checks.md` for KLA
  (or the person KLA names).
- **The checks** (all read-only, on production):
  1. From a phone on **mobile data**, as a manager, open Settings › Network. It says "Your
     address: … — external", and the address is the carrier's, not `10.24.0.18` or `10.24.0.100`.
  2. Settings › Access log shows that phone's carrier address, and other varied addresses, not the
     proxy's `10.24.x.x`.
  3. From the **plant Wi-Fi**, Settings › Network says "internal".
  4. As IT admin on mobile data: the "plant network only" card.
  5. From any PC: `curl -sI https://vel-yantra.mspv.app/` and `curl -sI` on one file under
     `/assets/`. Both show `Strict-Transport-Security`, `X-Content-Type-Options`,
     `X-Frame-Options` and `Referrer-Policy` (the front proxy adds them).
  6. On the front proxy VM, `ip -4 -br addr`: note the address it connects to Yantra from.
     `vm-register/vm_register.yml:39-40` says only `10.24.0.18` is bound there (to verify). R01.5
     narrows `set_real_ip_from` to it.
- **Results:**
  - Checks 1 and 3 pass (KLA, 26-10-2026, on a mobile phone): Settings › Network says
    "external" on mobile data and "internal" on the plant Wi-Fi.
  - Check 5 passes (Claude, 26-10-2026, `curl -sI` from KLA's laptop). Both the page and
    `/assets/index-BY_RE93o.js` carry HSTS, `X-Content-Type-Options`, `X-Frame-Options`,
    `Referrer-Policy` and `Permissions-Policy`, all from the front proxy. The page also carries
    Yantra's own three, so they appear twice. That is harmless, and R01.5 can drop the copies
    the front proxy already sends. The front proxy sends `Permissions-Policy: camera=()`, so a
    page cannot use the camera. Yantra has no in-page camera today (no `getUserMedia` in
    `frontend/src`). A later in-app QR scanner needs that header changed in the devops repo.
  - Checks 2, 4 and 6 are open.
- **After it:** KLA knows whether a host on the app LAN can fake an address today, and R01.5 has
  the address to trust.
- **Migrations:** none. **Leaves for later:** the code fixes of [12] (R01.5).

### R01.2 — Token checks

- **Goal:** a bad token costs no key fetch, a slow Keycloak cannot hold a worker for 30 s, and a
  token from the wrong issuer or of the wrong kind is refused. Audit [7], [16], and the token
  tests of [28].
- **What changes (backend only):**
  - `auth_utils.py`: drop the evict-and-retry. PyJWT's `PyJWKClient` already fetches the key list
    again when a token names an unknown key id, so key rotation still works (fact: PyJWT 2.15.1 in
    `uv.lock`; the coder confirms the refetch in its source). Create the client with
    `timeout=5`.
  - A failure to fetch the key list (`PyJWKClientConnectionError`) answers **503**, not 401, and
    the access log records it with its own code.
  - `jwt.decode` with `issuer` = the public realm URL, `leeway=30`, `require=["exp", "iat",
    "iss"]`; then `typ` must be `Bearer` (Keycloak's access-token type; the brief confirms it
    from a real token's claims).
  - Tests: wrong issuer, missing `exp`, `typ` not `Bearer`, an `HS256` token signed with the
    public key (algorithm pinning), a key-list fetch failure (503), a token 20 s in the future
    (passes with the leeway); the `DEV_AUTH_BYPASS` refusal without `FLASK_DEBUG`.
- **Text on screen (scope B):** the 503 body is "Sign-in cannot be checked right now. The login
  server does not answer. Try again in a minute." R01.3 shows it on the start screen instead of
  "Your account is not in the maintenance team".
- **After it:** a burst of junk tokens from the internet no longer reaches Keycloak; a Keycloak
  outage says so.
- **Migrations:** none. **Leaves for later:** the corrected base-doc text goes to smtw-common
  (impl report).

### R01.3 — Keep typed input

- **Goal:** typed input survives a failed sign-in renewal and an accidental leave. Audit [8].
- **What changes (frontend only):**
  - `getToken()` no longer redirects to the login page. It tells two cases apart: the renewal
    failed but the session is still valid (a network drop: the refresh token has not expired), or
    the session has ended (the refresh token has expired). In both, the request fails with an
    error the screen shows, and the screen keeps its input.
  - When the session has ended, a bar at the top of the app offers *Sign in again*. It goes to
    the login page and discards the input, without the leave guard's prompt (KLA, 25-10-2026:
    the case is rare).
  - A shared leave guard (one composable, used by both screens): moving to another page in the
    app shows an in-app "Discard your changes?" dialog with the modals' words; closing or
    reloading the tab shows the browser's own prompt (its text cannot be changed). It applies to
    **Raise ticket** and the **Readings sheet** (Q3.2).
  - `loadProfile` shows a 503's own message (R01.2's text, or the DB message), and keeps the
    "not in the maintenance team" text for a 401 only.
  - Tests: a unit test of `auth.js` (none today, audit [28]); browser tests of the leave guard on
    both screens and of a failed renewal on a dialog.
- **Text on screen (scope B):**
  - Network drop: "Not sent. The connection to the login server dropped. Your input is kept.
    Check the network, then try again."
  - Session ended (bar): "Your sign-in has ended. Sign in again to go on." Button: *Sign in
    again*.
  - Session ended (on the request): "Not sent. Your sign-in has ended. Sign in again, then try
    again."
  - Leave guard: "Discard your changes?" / "What you typed on this screen is not saved." Buttons:
    *Keep editing*, *Discard*.
- **After it:** a technician raising a ticket on mobile data loses nothing to a network drop, and
  is warned before leaving a half-filled form.
- **Note (fact):** the auth store, `api.js` and the router are shared frontend files (CLAUDE.md
  § Step workflow, *Shared code*), so the coder runs the whole browser suite once at the end.
- **Migrations:** none. **Leaves for later:** keeping a draft across a full sign-in (Q3.1 option b);
  the leave guard on Settings (Q3.2 option b); the base-doc text to smtw-common.

### R01.4 — What the server sends

- **Goal:** nothing is served from a browser cache without the access check, and no user sees
  database internals. Audit [17], [18].
- **What changes (backend, one Settings card):**
  - `documents.py`: files and thumbnails go out with `Cache-Control: private, no-cache`; the ETag
    still makes a repeat view a 304, so phones re-download nothing that did not change.
  - `app.py`: the `DBUnavailable` handler logs the detail and answers the plain
    `DB_LOST_TEXT` ("Database unavailable — try again shortly"), the same words as S025's
    lost-connection 503.
  - `GET /api/settings/db-status`: host, port and the error text only for `settings:edit`
    holders (IT admin, who is held to the plant network); a manager sees reachable yes or no and
    the schema version (Q4.1). The S025 precondition message stays visible to IT admin there.
  - Tests for each.
- **Text on screen (scope B):** a manager's Settings › Database card says "Ask IT admin for the
  details." where the detail would be.
- **After it:** a shared kiosk phone cannot show the next user a drawing they may not open; an
  outage shows no host name to the internet.
- **Migrations:** none. **Leaves for later:** none.

### R01.5 — Web server and network

- **Goal:** every response carries the security headers and a CSP; long requests are not cut at
  60 s; only the front proxy may set the client address; a typo cannot switch off the gate; the
  dev servers are not on the LAN. Audit [12] (code), [19], [20].
- **What changes in this repo:**
  - `tooling/build/nginx.conf` (built into the frontend image):
    - the headers once at server level, repeated in `/assets/` (nginx drops inherited
      `add_header` when a block sets its own);
    - a CSP (Q5.1), starting from the audit's: `default-src 'self'; connect-src 'self'
      https://sso.mspv.app; img-src 'self' blob: data:; object-src 'none'; frame-ancestors
      'self'`. The brief checks what keycloak-js, the service worker, Bootstrap and the PDF and
      photo views load;
    - `proxy_read_timeout 130s` on `/api/`, above gunicorn's 120 s;
    - `set_real_ip_from` the front proxy's address only (from R01.1 step 6).
  - `network_core.parse_networks`: refuse an IPv4 range shorter than /8 and an IPv6 range
    shorter than /7 (so the whole private block `fc00::/7` is still allowed; the brief settles
    the IPv6 limit). Message (scope B): "'0.0.0.0/0' is too wide. Enter a range of /8 or
    narrower, such as 10.24.0.0/16."
  - Dev servers (Q5.2): the backend's `app.run` on `127.0.0.1`; Vite on `127.0.0.1` by default,
    with a separate run config for device checks on the LAN.
- **What changes in the devops repo (`smtw_erp_devops`, KLA runs it):** only for Q5.3 (upload
  size): `nginx/src/sites-available/vel-yantra.mspv.app.conf:11` `client_max_body_size` to
  `101M`, deployed with `nginx/deploy-nginx.yml`. HSTS is already set there
  (`security-headers.conf:4`). The CSP lives in this repo's `nginx.conf`, not at the front,
  because it names Yantra's own sources. The brief gives KLA the exact line.
- **Release:** the headers and the CSP take effect only with a new frontend image. The step's
  manual checks run after its release: login, a token renewal after 5 minutes, a photo upload, a
  PDF view, a test notification, and `curl -sI` for the headers.
- **After it:** the app's own pages are protected even if the front proxy's config changes, and a
  wrong range in Settings › Network is refused.
- **Migrations:** none. **Leaves for later:** a CSP report endpoint (not proposed).

### R01.6 — Route walk

- **Goal:** prove that every API route refuses a user with no access. Audit [28]: 25 of 90 gated
  rules check their key inside the route (`check_perm`), so a decorator scan cannot prove it.
- **Decided by KLA, 25-10-2026: test plus a required declaration** (fail-closed, OWASP ASVS V8
  deny by default, to verify). Every route declares how its access is checked: `@require_perm(key)`
  as today; a new marker for the routes that check inside (`check_perm`, `require_perm_at`), e.g.
  `@perm_checked_in_route("<reason>")`, with a check after the request that a helper really ran
  (a 2xx without one is an error); and `@public("<reason>")` for the open routes. A route with no
  declaration is refused with 403 at runtime, and a test lists it. Small app change in
  `auth_utils.py` and a marker on about 25 routes; the brief names the marker names and where
  the "a helper ran" check lives (production as well as tests). Size stays S–M; no longer
  tests only.
- **What changes (the walk test):** one test reads `app.url_map`, fills each rule's arguments with a
  real id, and calls it as the login-only role (`maintenance_team`, which grants nothing). Every
  answer must be 401, 403 or 404, never 2xx. The public paths (`PUBLIC_PATHS`) and
  `GET /api/auth/me` (answered for any login) are the listed exceptions, each with its reason. A
  new route without a filled id makes the test fail, so each new route is a decision.
- **Optional (Q6.1):** a test that every token role is either in `INTERNAL_ONLY_ROLES` or in a list
  of roles allowed from outside with a dated reason (audit hindsight 2, "the deny-list gate
  fails open").
- **After it:** a route that forgets its check fails the tests.
- **Migrations:** none. **Leaves for later:** if the walk finds a route that answers 2xx, the fix
  is its own step (the test marks it as expected to fail with the fault named).

### R01.7 — Access-change trail

- **Goal:** the record of who changed whose access is complete and cannot be forged. Audit [11].
- **What changes:**
  - A logging filter that escapes `\r` and `\n` in every log line, in the app and the worker.
  - Names (`parse_name`, used for people, sites, units and equipment) no longer keep line breaks
    or other control characters: inner whitespace collapses to one space, as manufacturer names
    already do (`masters_core.py:64-71`).
  - A log line for every change of `active` on a person with a login: actor, person, before,
    after.
  - Each access-change line has one fixed shape, so Loki can find it by a label or a plain
    filter: `access_change actor=<person id> person=<person id> field=<active|login|site role>
    before=<value> after=<value>`. The coder fixes the exact field names in the brief; values are
    escaped like every other line.
- **Q7.1 (KLA, 26-10-2026): log lines only.** No table and no screen. KLA will configure Loki to
  ship the container logs, so the lines outlive the container's log rotation. The Loki setup is
  outside this repo (devops, KLA).
- **After it:** KLA can answer "who gave this person access, and when" from Loki for an ISO 27001
  access review, as long as Loki keeps the lines.
- **Migrations:** none.
- **Leaves for later:** the `access_changes` table and its Settings tab (Q7.1 b), if Loki's
  retention proves too short; a periodic access-review report (ISO 27001 A.5.18 "reviewed"); trades are
  not access and stay out.

## Order

1. **R01.1 first (now, 15 minutes, no code).** It closes a check open since 18-10-2026 and tells
   whether a host on the app LAN could fake its address today. R01.5 needs its answer.
2. **R01.2 and R01.3 next, in parallel.** They are the two risks the floor and the internet
   meet first: unauthenticated requests that reach Keycloak, and lost input on phones. R01.2 is
   backend only, R01.3 frontend only; they share no file (the 503 text works whichever lands
   first).
3. **R01.4.** Small, and it shares no file with R01.3, so it can also run beside R01.3.
4. **R01.5** after R01.1. Its effect waits for a release anyway (new frontend image), so it fits
   just before the next release.
5. **R01.6** after R01.2 (both change `auth_utils.py`). Since KLA's decision it also marks
   routes in `documents.py`, `equipment.py`, `masters.py` and `tickets.py`, so it runs beside
   R01.3 only, not beside R01.4 or R01.7.
6. **R01.7 last.** Q7.1 is answered (log lines only), and it shares `app.py` and `masters.py` with R01.4.

**Parallel pairs** (no shared files, at most one migration; step skill § Parallel steps):
- R01.2 ∥ R01.3 (backend vs frontend).
- R01.3 ∥ R01.4 (R01.4 touches only the Settings view in the frontend).
- R01.6 ∥ R01.3 (R01.6 ∥ R01.5 dropped: R01.6 now changes app code, KLA 25-10-2026).

**Not in parallel:** R01.4 and R01.5 (both change `app.py`); R01.4 and R01.7 (`app.py`, the
Settings view); R01.2 and R01.6 run best one after the other, because both change the auth tests
(no shared file, but a finding in one changes the other).

**Effort (estimate):** about two days of step time with reviews, against the queue's "about a
day". The difference: the readings sheet (S040) added a second full-page form to guard. Q7.1's
log-lines answer took about half a day off the first estimate.

## Decisions for the user

**Answers (KLA, 26-10-2026, on the answer sheet
https://claude.ai/artifact/7JKrBjU9VzZPEGpCytbCR2):**

| Question | Answer | Note |
|---|---|---|
| Q3.1 | a | A network drop keeps the typing; after a real end of session, *Sign in again* discards it (25-10-2026). |
| Q3.2 | a | Only Raise ticket and the Readings sheet. |
| Q4.1 | a | IT admin only. |
| Q5.1 | a | Enforce the CSP in the release; check right after the deploy. |
| Q5.2 | a | 127.0.0.1, plus a "Frontend (LAN)" run config. |
| Q5.3 | a | Front proxy to 101 MB. KLA asked for a text for the devops team (below). |
| Q6.1 | a | Yes, the every-role test. |
| Q7.1 | **a** (not the recommendation) | Log lines only: "we will configure loki to ship logs". |
| Q7.2 | — | Not asked: it applies only to Q7.1 b or c. |

Also decided: R01.2 accepted as written; R01.6's declaration design (25-10-2026).

**Text for the devops team (Q5.3):**

> Yantra: raise the upload limit at the front proxy. In
> `smtw_erp_devops/nginx/src/sites-available/vel-yantra.mspv.app.conf`, line 11, change
> `client_max_body_size 50M;` to `client_max_body_size 101M;`, then reload nginx on the front
> proxy. Why: Yantra's Settings allow uploads up to 100 MB, and Yantra's own nginx already
> accepts 101 MB. Today a file between 50 and 100 MB gets the front proxy's "413 Request Entity
> Too Large" page instead of Yantra's message. 101 MB leaves room for the form fields around a
> 100 MB file. Check: upload a 60 MB PDF to a machine's documents in Yantra; it saves. No other
> site changes.

Questions are numbered by their item: Q3.2 is the second question of R01.3, and its options
are answered as "3.2 a", "3.2 b" (renumbered 26-10-2026 at KLA's request; the old numbers
were D2→Q3.1, D3→Q3.2, D6→Q4.1, D4→Q5.1, D5.1→Q5.2, D5.2→Q5.3, D7→Q6.1, D1.1→Q7.1,
D1.2→Q7.2).

**Q3.1. What happens when the sign-in cannot be renewed?** Waits: R01.3.
- **(a) Keep the screen, show the message, offer *Sign in again* — recommended.** Simple. A
  network drop loses nothing. After a real end of session, *Sign in again* discards the input
  (see KLA's answer below).
- **KLA, 25-10-2026:** a network drop keeps the input (no sign-in needed; try again). A session
  that has really ended is rare: *Sign in again* goes to the login page and the input is
  discarded, with no leave-guard prompt and no "copy your text" step.
- **(b) As (a), and also keep the draft of Raise ticket and the Readings sheet in the browser
  across the sign-in.** Nothing is lost even then. More code and tests, and a draft stays on a
  shared phone until it is sent or discarded.
- **(c) As today:** go to the login page at once. The input is lost.

**Q3.2. Which screens get the leave guard?** Waits: R01.3.
- **(a) Raise ticket and the Readings sheet — recommended.** The two screens where real work is
  typed on a phone.
- **(b) Also Settings.** Its inputs are IT admin's set-once values, at a desk; low value.

**Q4.1. Who sees the database details in Settings › Database?** Waits: R01.4.
- **(a) IT admin only (`settings:edit`); a manager sees reachable yes or no and the schema
  version — recommended.** IT admin works only from the plant network, so the details never reach
  the internet. No new permission key.
- (b) Managers too, but only from the plant network. Needs the network check in the route.
- (c) As today.

**Q5.1. Turn on the CSP at once, or watch it first?** Waits: R01.5.
- **(a) Enforce it in the release, with a check right after the deploy — recommended.** The
  browser tests do not use Keycloak, so only production proves the sign-in under the CSP. A
  failure shows at once on login, and the way back is to redeploy the previous version.
- **(b) Report-only for one release, enforce in the next.** Nothing can break, but the reports
  are seen only in a browser's developer tools (no report endpoint is proposed), and it takes two
  releases.
- **(c) No CSP now.** Only the header fixes; the CSP waits.

**Q5.2. Where do the dev servers on KLA's laptop listen?** Waits: R01.5.
- **(a) Both on 127.0.0.1; a separate run config, "Frontend (LAN)", for the device checks that
  run on the dev server — recommended.** The dev server skips sign-in, so it is open to the LAN
  only while KLA runs a device check.
- (b) 127.0.0.1 only; dev-server device checks move to production.
- (c) As today: an admin API without sign-in on the LAN at port 5176.

**Q5.3. How to fix the upload size above 50 MB?** Waits: R01.5.
- **(a) Raise the front proxy's limit to 101 MB (one line in the devops repo; KLA deploys it)
  — recommended.** Settings stays the one place that sets the limit, and a refusal shows
  Yantra's message.
- (b) Lower Settings' maximum to 50 MB. No devops change; a large manual must be split.

**Q6.1. Add the "every token role is a decision" test to R01.6?** Waits: R01.6.
- **(a) Yes — recommended.** One small test; a future Keycloak role must be named internal-only
  or allowed from outside with a reason, so the deny-list gate cannot fail open by accident.
- (b) No; it stays an audit hindsight point.

**Q7.1. How complete must the access-change trail be?** Waits: R01.7.
- **(a) Log lines only.** No migration, about 1 hour. The trail lives in the container logs; how
  long they are kept is not known from this repo (risk below).
- **(b) An append-only table and a read-only list in Settings › Access log — recommended.** The
  record survives log rotation and can be shown in an ISO 27001 access review. One migration and
  one tab; about half a day.
- **(c) The table without a screen.** Same record; IT reads it in the database. Saves about an
  hour, but KLA cannot see it.

**Q7.2. With Q7.1 (b) or (c): how long are the rows kept?** Waits: R01.7.
- **(a) Forever — recommended.** A few rows a month; the full history stays.
- (b) Purge after 365 days, like the access log (Plan.MD § 1).

**Not asked again:** Plan.MD § 1 already settles that every role except IT admin works from
outside, that the VPN counts as internal, and that admin bypasses the gate. R01 departs from none
of it.

## Out of the roadmap and risks

**Out (fact):**
- Audit [13], [14], [21]–[27] and the other test gaps of [28]: the queued *Tidy-up*.
- Audit [15]: the queued *Module and schema docs*.
- Two-factor login (OTP) for the admin account: a Keycloak setting for KLA (`docs/Keycloak.md`
  line 82), not code. It is worth doing before R01.5's CSP release, since admin bypasses the gate.
- The audit's hindsight points other than Q6.1 (a global masters key, `team.py`, READ COMMITTED).
- Malware scanning of uploads: its own queued item (ISO 27001 A.8.7).
- Any edit of the devops repo by an agent: the one line of Q5.3 is given as text for KLA.

**Risks:**
- **The CSP can break sign-in in production only** (assumption: keycloak-js may load from or
  call `sso.mspv.app` in ways the dev bypass and the browser tests never exercise). Covered by
  Q5.1's check after the deploy and the rollback by redeploy.
- **The access trail is only as long as Loki keeps it** (Q7.1 a). KLA will configure Loki to
  ship the logs (devops, outside this repo); its retention sets how far back an access review can
  look. Until Loki runs, the container's log rotation sets it.
- **The front proxy's address is not confirmed** (`vm_register.yml` says "owner unconfirmed" for
  `10.24.0.100`). R01.1 step 6 confirms it before R01.5 narrows `set_real_ip_from`; a wrong
  address would make every client look like the proxy, so the gate would treat everyone as
  internal or external together.
- **The front proxy's `Permissions-Policy` blocks the camera API** (`camera=()`,
  `security-headers.conf:19`). Yantra uses file inputs only today (fact: no `getUserMedia` in
  `frontend/src`), so nothing breaks. A future in-app QR scanner would need `camera=(self)` there.
- **PyJWT's own refetch on an unknown key id** is what keeps key rotation working once the
  retry is gone (R01.2). The coder confirms it in the library's source before removing the
  retry.
- **The route walk may find a real gap.** Then R01.6 grows a fix, or a new step is needed.

## Slides — none (KLA, 25-10-2026: no deck for this roadmap)

## Log

- 25-10-2026 — First version (Draft): seven items from audit [7], [8], [11], [12], [16]–[20] and
  the auth gaps of [28], checked against HEAD `82997ee`; [9] found done in S025; the 50 MB front
  proxy limit found in the devops repo; seven decisions for KLA.
- 25-10-2026 — KLA asked for an explainer deck after all: a private slide deck (one slide per item
  and per question; D1 and D5 split into D1.1/D1.2 and D5.1/D5.2 so each answer has one number),
  https://claude.ai/artifact/QZXkNEQvXWJCXxKsDG6Qte. The roadmap file stays the record.
- 26-10-2026 — R01.1: checks 1 and 3 pass (KLA, phone), check 5 passes (curl); checks 2, 4 and 6
  are open. Found: the front proxy's `Permissions-Policy: camera=()` blocks any later in-page
  camera.
- 26-10-2026 — KLA: R01.2 (token checks) accepted as written; it has no question.
- 26-10-2026 — Questions renumbered by item (Q3.1 … Q7.2, mapping in § Decisions), at KLA's
  request: the deck must name each question and label each option. The log lines above keep
  the old D numbers.
- 26-10-2026 — Gate R: KLA answered on the answer sheet. All at the recommendation except Q7.1
  (a, log lines only; Loki will ship the logs). R01.7 shrinks to size S with no migration;
  effort about two days. Status Approved.

## Feedback

- `hindrance` — The roadmapper's agent file requires a showcase, mock-ups and slides for every
  roadmap; KLA's "no deck" had to come in the task text. A `Deck: none` line in the header,
  allowed by `docs/roadmap/README.md`, would make the exception part of the convention.
- `rule` — Two findings changed only after reading the devops repo (`smtw_erp_devops/nginx/src/`:
  HSTS already set, a 50 MB limit the app does not know). The audit read only
  `tooling/build/nginx.conf`. Proposal: CLAUDE.md § SMTW-Review names the front proxy's Yantra
  files as part of the audit.
- `idea` — Re-checking eleven findings against new code took most of this run. A status column
  per finding in the queued row (open, partly, done, with the step) would let the next roadmapper
  start from it.
- `waste` — `grep -rn` over `backend` without excluding `.venv` returned library lines first; the
  `Grep` tool with a glob on `backend/*.py` would have been cleaner.
