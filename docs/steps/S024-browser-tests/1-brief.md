```
Step: S024 — Browser tests (Playwright)
Doc: brief
Author: Planner (Opus)
Date: 21-10-2026 (revised 21-10-2026 after brief-reviews r1, r2 and r3)
Track: full
Baseline: 6c58b7a + uncommitted S018 (r3); stale check at coding: ae3841f and later, no file in § 3 changed
Status: Gate B — code review r2 clean; awaiting the user's checks and commit (approved 21-10-2026 by KLA; A1, A2 approved 21-10-2026)
```

# S024 — Browser tests (Playwright)

The user has no time to run every step's manual checks by hand (21-10-2026):
"we either must ask my it-admin to do it or use playwright". The test suite
today never opens a screen: backend tests call the API, frontend tests call
pure helpers. Twice this week a screen compiled, passed every test and then
would not open (S017's blank raise screen, S018 CR1-01's dialogs), and only a
person in a browser could have found it.

S024 adds **browser tests**: a real browser engine drives the real screens
against a real backend and a throw-away database, as each role, at phone and
desktop size. Most manual checks become automated tests; the few that need a
real phone or a printer go to a named person (the IT admin), not necessarily
the user.

**Track: full.** A new dev dependency (`@playwright/test` and its browsers), a
test harness that sets who the user is per request (auth-adjacent, dev only),
a new database, and a change to the step workflow's manual-check rule.

**Coded after S018 is committed** (BR1-09): its flow tests are written against
S018's settled screens, and the "re-introduce the bug" demonstration (§ 8)
reverts with `git checkout` on committed files.

## 1. What will be built

1. **An e2e stack, started by one command** (`tooling/run-e2e-tests.bat`):
   - a **throw-away database** `vel_yantra_e2e` on the dev MariaDB (port 3307),
     dropped and rebuilt by the migrations at every run, so a run never
     depends on what was left behind; the bat creates the database and its
     grant itself on first use (§ 3, BR1-07);
   - the **backend** on `127.0.0.1:5002`, in dev mode with the test-identity
     header switched on (§ 5.1), its own `DATA_DIR` (`scratch/e2e-data/`,
     emptied with the database at each run);
   - **Vite** on port 5177 (`--strictPort`), proxying `/api` to
     `http://127.0.0.1:5002` (the dev servers on 5001 / 5176 keep running
     untouched);
   - **seed data** loaded through the API at the start of a run (§ 5.2).
2. **Who the browser is**: each test opens the app as a named seed person —
   `asPerson(page, "technician")` — by sending the existing test headers
   (`X-Test-Role`, `X-Test-User`) on every request from that browser
   context, and **checks who it is** before going on: `/api/auth/me`
   returns that person's username and the top bar shows their name
   (BR1-01). A request that loses its headers is refused, never promoted to
   admin (§ 5.1). No login screen, no Keycloak, no change to production auth.
3. **Three browser set-ups** in every run:
   - **phone, Chromium** (`devices["Pixel 7"]`: size and touch);
   - **phone, WebKit** (`devices["iPhone 14"]`; WebKit is Safari's engine,
     though not iOS Safari itself — § 7);
   - **desktop, Chromium** (1366 × 768).
4. **The first tests:**
   - **Every screen opens**, for each role that can reach it: no console
     error or Vue warning (§ 5.3), no blank page, the screen's heading shows.
     This is the test that would have caught both of this week's blank
     screens. It covers every route in `router/index.js` (with an id taken
     from the seed for `/equipment/:id`, `/tickets/:id`, `/e/:code`).
   - **Dialogs fit a phone** — one shared assertion `expectDialogFits(page)`:
     the dialog's Save and Cancel lie inside the viewport (`boundingBox()`)
     and the dialog is no taller than the viewport (a long one scrolls inside;
     BR2-07). It is called **inside the flow tests on every
     dialog they open anyway** — S017 raise; S018 acknowledge, start, back in
     service, close, not a fault, send back, change severity, edit, assign,
     labour; S016 failure mode / cause / action add and edit; S012
     manufacturer and model; equipment add, move, status; document upload
     and title — not by a separate file that opens all ~30 dialogs from
     scratch (BR1-03). Each later step's flow tests call it on the dialogs
     that step adds.
   - **S017 and S018 flows**, in place of their manual checks (§ 8 maps each):
     raise a ticket (from an equipment page and from the Tickets list);
     technician acknowledge → start → back in service with the times shown;
     supervisor back in service with the technician picked by typing and a
     start time; engineer close blocked until labour, then closed and
     read-only; send back with the machine down; operator *Machine stopped*;
     *Not fixed — raise again* linking both tickets; A1 *Already fixed* with
     and without a start time.
   - **Earlier committed steps' checks that a browser can do**: S015 (the
     asset list renders per unit, options change it), S016 (the failure-code
     masters add / edit / freeze), S014 (the labels page lays out 15
     labels per sheet element and 16 labels make two sheet elements: DOM
     assertions, since print emulation does not paginate; `/e/<code>` opens
     the equipment page) (BR2-04). What only paper or a camera can show stays with a
     person (§ 8).
   - **Screenshots and a trace on failure** (Playwright's own), kept under
     `scratch/e2e-report/`, so a red run shows what the browser saw.
5. **The step workflow changes** (README § Manual checks and § Gates, the
   `/step` skill, the three agents):
   - a brief's manual checks are split into **Automated** — each becomes an
     e2e test the coder writes with the step — and **On a real device** — the
     few a browser engine cannot judge (§ 7);
   - an automated check is marked in the impl report as
     `- [auto] <check> — <test file>::<test name>` once the e2e run passes;
     only a passing run may write it;
   - a real-device check is done by the user **or a person the user names**
     (the IT admin). The round trip (BR1-02): the user hands the person the
     rows from `docs/steps/device-checks.md` (printed or by chat); the person
     reports back to the user; the user tells the planner; the planner writes
     `- [x] <check> — by <name>, DD-MM-YYYY` into the step's impl report and
     marks the row done in `device-checks.md`. The file is the master list,
     not something the person edits;
   - the coder of every later step appends that step's real-device checks to
     `device-checks.md`; a done row stays as the record (who, when) (BR1-09);
   - the user still decides at gate B which checks are which, and can skip
     any;
   - the coder and the code reviewer run the e2e tests whenever the frontend
     or an API the screens use changed, and report the real result;
   - a step is `Done` when committed and every important check is `[auto]`,
     ticked for the user or the named person, or skipped by the user.
6. **A real-device checklist**, `docs/steps/device-checks.md`: the open
   real-device checks of every committed step, one row each, in plain words,
   with five columns a non-developer can follow without help (BR1-02):
   - **What to do and what you should see**;
   - **Account**: on a **production** row, which login, e.g. "a test login
     with the Technician role at SMTW (ask KLA)"; on a **dev-server** row and
     a print or measure row, "none" (the dev server runs with the login
     switched off, BR3-02). Not the IT admin account where the check is about
     another role, and never the IT admin account on mobile data (it is
     refused off the plant network, S013);
   - **Network**: company Wi-Fi, home network or mobile data. The dev server
     runs on KLA's laptop and IT Admin can reach it only while the laptop is
     on the company or home network; a mobile-data row is always a
     production row;
   - **Done**: who and when (`IT Admin, DD-MM-YYYY`), written by the planner
     (BR2-06);
   - **Where**: either the **dev server** on KLA's laptop
     (`http://<laptop>:5176`, when it is on the company or home network) or
     **production on the test machine** (below); a row says which, or "either"
     when both work, so IT Admin can do it whichever is at hand (user,
     21-10-2026). No check raises tickets on a real machine, so the KPIs stay
     clean (ISO 14224 records, SMRP availability).
   Two checks can only run on production, because they test the deployment,
   not a step's code: a real login through Keycloak (the dev server runs with
   the login switched off) and a QR label scanned on mobile data (the label's
   link is the production address). They form a short **after deploy** section
   at the top of `device-checks.md`, done once per release. Production rows
   use a **test machine named "TEST" in
   `SMTW.MCC2`** (real logins hold that unit), with its label marked TEST; its
   code, given at creation, is written into the rows once created; its
   tickets are closed as *Not a fault* after the check (BR2-05).
   The named person is **IT Admin** (open question 4).

### Out of scope

- Running the e2e tests in `run-tests.bat` or in the release pipeline
  (decided: no, open question 1).
- A CI server: there is none; runs are local.
- Visual comparison of screenshots against stored images (fragile; later if
  ever).
- Load or performance testing (~50 users; CLAUDE-COMMON).
- Keycloak login itself: the e2e stack never talks to Keycloak; the login
  path stays a real-device check.
- **The network gate and the access log** (S013): with `DEV_AUTH_BYPASS=1`
  both hooks are skipped (`access_control._skipped`), so the e2e stack never
  shows the "plant network only" card and Settings › Access log stays empty.
  They keep their API tests (BR1-14).
- The S010–S013 and S022 manual checks: S010–S013 are older admin screens
  covered by "every screen opens"; S022 is a command-line tool, not a screen.
- Automating checks that need a camera, a printer, a ruler or a real iOS
  keyboard.

## 2. Standards and practice

- **ISO 9001 § 8.3.4 (design and development controls)** asks for
  verification that the output meets the input requirements, with records of
  it. Today that verification is a person clicking through a checklist,
  recorded as a tick; an automated test is the same verification, repeatable
  on every change and recorded by its name and result. A test named after the
  requirement it checks gives **traceability** — from the brief's check to
  the test to its result — which is what § 8.3.4's records are about. Since
  ISO 9001 certification is a future goal, that is the kind of record an
  auditor looks for.
- **ISO/IEC 27001:2022 Annex A 8.29 (security testing in development and
  acceptance)** and **A 8.31 (separation of development, test and production
  environments)**: the e2e stack has its own database, data folder and ports,
  never touches the dev data and cannot reach production; the identity header
  works only in a dev-mode process that also refuses to start otherwise, and
  a request without it gets no access (§ 5.1).
- **The test pyramid** (Mike Cohn, *Succeeding with Agile*, 2009): many fast
  unit tests at the base (Yantra has ~1 800), fewer API tests, and a thin
  layer of slow end-to-end tests at the top that prove the pieces work
  together. S024 builds that top layer and keeps it thin: one test per flow,
  not one per field rule (the field rules stay in the API tests).
- **Usability (ISO 9241-11)** defines usability as effectiveness, efficiency
  and satisfaction for given users in a given context. A browser can check
  effectiveness (the flow completes, the buttons are reachable on a phone);
  satisfaction and "would a gloved thumb hit it" still need a person, which
  is why the real-device list stays.

No maintenance standard applies to this step itself.

## 3. Where

### Frontend (`frontend/`)
- `package.json`: dev dependency `@playwright/test` (pinned); script
  `"e2e": "playwright test"`. Changed with `npx npm@11 install` (CLAUDE.md).
- `vite.config.js`:
  - the proxy target reads `YANTRA_API_URL` (default `http://localhost:5001`,
    unchanged for dev); the e2e config sets `http://127.0.0.1:5002` (Node may
    resolve `localhost` to `::1`, and the backend binds IPv4 only, BR1-07);
  - `test.exclude: [...configDefaults.exclude, "e2e/**"]`, so Vitest does not
    pick up the Playwright specs and `npm test` stays green (BR1-05).
- `playwright.config.js` (new): the three projects (§ 1.3); `workers: 1`;
  two `webServer` entries, both `reuseExistingServer: false` (a reused
  backend has not been reset):
  - backend: `uv run --project ../backend python ../tooling/e2e/e2e_backend.py`,
    waiting on `http://127.0.0.1:5002/api/health`;
  - Vite: `vite --port 5177 --strictPort` with `YANTRA_API_URL` set, waiting
    on `http://127.0.0.1:5177`;
  `globalSetup` = the seed; `outputDir` and the HTML report under
  `../scratch/e2e-report/`, traces and screenshots on failure.
- `e2e/` (new):
  - `setup/global-setup.js` — runs `tooling/e2e/seed_e2e.py` against 5002;
  - `support/people.js` — `asPerson(page, key)`: one browser context per
    seed person with `extraHTTPHeaders` `{X-Test-Role: "maintenance_team",
    X-Test-User: <login>}` (token role `it_admin` for the IT admin), then the
    identity check of § 1.2; `seedIds(playwright)` — looks up ids by code
    through the API with the admin headers, on its own
    `playwright.request.newContext({ baseURL, extraHTTPHeaders })` in a
    `beforeAll` (the `request` fixture is per test and not available there,
    BR3-04) (BR1-11);
  - `support/console.js` — `watchConsole(page)`: fails the test on any
    `console.error`, any `console.warn` that is a Vue warning (`[Vue warn]`),
    and any uncaught page error; the allow-list is exactly two sources —
    `auth.js`'s "Auth bypass: DEV_AUTH_BYPASS enabled on backend." line and
    Vite's own `[vite]` client messages — so any new warning still fails
    (BR1-10);
  - `support/dialogs.js` — `expectDialogFits(page)` (§ 1.4);
  - `screens.spec.js` — every route opens, per role;
  - `tickets-raise.spec.js`, `tickets-work.spec.js` — S017/S018/A1 flows;
  - `masters.spec.js`, `equipment.spec.js`, `asset-list.spec.js`,
    `labels.spec.js` — S016, S012/equipment dialogs, S015, S014.

### Backend
- `backend/tests/harness.py` (new; moved out of `tests/conftest.py`):
  `harness_user(role, username, name=None)` — the existing X-Test-Role
  factory, with no pytest import, so the pytest suite and the e2e server
  share one definition (DRY). The optional `name` lets the e2e factory give
  each person their seed name, so the top bar shows who is acting rather than
  "Test maintenance_team" for everyone (BR1-11). `conftest.py` imports it
  (`from tests.harness import harness_user`, as it already imports
  `tests.access_helpers`); its behaviour is unchanged. It stays under
  `backend/tests/`, which `.dockerignore` keeps out of the production image
  (BR1-06).
- `tooling/e2e/e2e_backend.py` (new): starts the Flask app for e2e. Order
  matters (BR1-07):
  1. put `backend/` on `sys.path`; set `FLASK_DEBUG=1`, `DEV_AUTH_BYPASS=1`
     (so the frontend skips Keycloak, as in dev) and an absolute `DATA_DIR`
     in `os.environ`
     **before `import config`** (`config.py` refuses the bypass without
     `FLASK_DEBUG`);
  2. `import config`; set `config.DB_CONFIG["database"] = "vel_yantra_e2e"`
     and `config.DEV_STUB_ROLE = "nobody"` (§ 5.1); then check the guard
     (§ 5.1) on the host and the name now set, before anything is dropped
     (BR3-03);
  3. on a plain `pymysql` connection with no database selected, `DROP
     DATABASE IF EXISTS` / `CREATE DATABASE vel_yantra_e2e` with the charset
     and collation of `init-test-db.sql` (utf8mb4, utf8mb4_unicode_ci); empty
     `DATA_DIR`;
  4. **then** `import app` (it opens the pool and runs the migrations at
     import, as `conftest.py` relies on); set `app.config["TESTING"] = True`
     and `TEST_USER_FACTORY` to a factory that calls `harness_user` with the
     username defaulted to `e2e_<role>` when `X-Test-User` is missing (as
     `conftest.py`'s factory does: `created_by` is `NOT NULL`, so a `None`
     username would make the first seed write a 500, BR2-02), and the display
     name from `seed_e2e.PEOPLE` by login, else the username;
  5. `app.run(host="127.0.0.1", port=5002, use_reloader=False)` — no
     reloader, which would re-run the launcher (and the drop) in a child
     process.
  Runs in the backend's uv environment (`pymysql` and the app's own imports;
  `uv.lock` unchanged).
- `tooling/dev/seed_dev.py` (refactor, BR1-04): `call(method, path, body=None,
  *, base_url, headers=None)` (the module-level `BASE_URL` read from
  `sys.argv` at import moves into `main()`); `dev-seed.bat` behaves as
  before. The shared lists (`SITES`, `UNITS`, `CLASSES`, `TRADES`,
  `MANUFACTURERS`, `MODELS`) are imported by the e2e seed.
- `tooling/e2e/seed_e2e.py` (new): the seed (§ 5.2), through the API with
  the admin headers (`X-Test-Role: admin`); puts `tooling/dev` on `sys.path`
  to import `seed_dev`; defines its own people and equipment.
- `backend/tests/test_access_control_api.py`: one new test — with
  `app.config["TESTING"]` off, a request carrying only `X-Test-Role` is 401
  (the Keycloak path's no-token refusal). The existing test covers the
  missing factory with `TESTING` on; this one covers the guard § 5.1 leans on
  (BR1-08).
- No change to `auth_utils.py`: the header path exists (S013 BR1-02), and
  `_get_dev_stub_user` reads `DEV_STUB_ROLE` lazily, so the launcher's
  in-process setting takes effect.

### Tooling and dev DB
- `tooling/run-e2e-tests.bat` (new):
  1. checks the dev DB container is up;
  2. creates `vel_yantra_e2e` and its grant if missing, as root through the
     compose file — `docker compose -f tooling/dev/docker-compose.dev.yml
     exec -T mariadb mariadb -uroot -p<dev root password> -e "CREATE DATABASE
     IF NOT EXISTS vel_yantra_e2e …; GRANT ALL ON vel_yantra_e2e.* TO …"`
     (the dev root password is in the compose file; dev only) — so no manual
     step and no `dev-db-reset.bat`;
  3. runs `npx playwright install chromium webkit` every time (a no-op when
     they are there; it fetches the right ones after a Playwright update);
  4. runs `npx playwright test` in `frontend/`, prints the run time and where
     the report is.
  Exit codes as Playwright's (0 green, 1 a failure).
- `tooling/dev/init-test-db.sql`: also creates `vel_yantra_e2e` and grants
  it, for a fresh container.
- `sbom/frontend.cdx.json`: regenerated (CLAUDE.md: commit `sbom/` with every
  dependency change); `tooling/run-deps-audit.bat` run once.
- `.gitignore`: `scratch/` already covers the report and data folders.

### Workflow docs
- `docs/steps/README.md` § Manual checks and § Gates 4 (worded generically:
  "the named person, today IT Admin", BR2-08): the rule of § 1.5
  (`[auto]`, the named person, the round trip, `device-checks.md` kept alive,
  the `Done` rule).
- `.claude/skills/step/SKILL.md`: gate B shows `[auto]` checks as passed
  tests and real-device ones as the checklist; the `Done` rule; the brief
  template's two kinds of check.
- `.claude/agents/coder.md`: write an e2e test for each *Automated* check of
  the brief; append the *On a real device* checks to `device-checks.md`; run
  `tooling/run-e2e-tests.bat` **with the maximum Bash timeout (600 000 ms) or
  in the background, reading the result when it finishes** (BR1-12); mark
  `[auto]` only from a passing run.
- `.claude/agents/code-reviewer.md`: run the e2e tests the same way; check
  each *Automated* check has a test that really asserts it (§ 5.4), and that
  flow tests call `expectDialogFits` on the dialogs they open.
- `.claude/agents/brief-reviewer.md`: a brief splits its checks into
  Automated and On a real device; a check put on the device list that a
  browser could do is `minor`; a device row without account, network and
  where is `minor`.
- `docs/steps/device-checks.md` (new): § 1.6.
- `.claude/CLAUDE.md`: one bullet — the e2e stack, its ports, its command,
  and when it runs: when a step changes screens, when the user asks, from
  `/smtw-review`; never in `run-tests.bat` or the release (user, 21-10-2026).
- **`/smtw-review` runs the suite** (user, Q1): `.claude/skills/` is
  **synced** from smtw-common (`tooling/common/sync_common.py` overwrites it),
  so S024 does **not** edit Yantra's copy; the edit would vanish at the next
  sync (BR2-01). Instead (user, 21-10-2026): the user adds to smtw-common's
  `smtw-review` skill an instruction to read a section of the project's
  `CLAUDE.md` holding **additional review points**, so each repo plugs its
  own checks into the audit. S024 adds that section to Yantra's
  `.claude/CLAUDE.md`, under the heading **`## Additional review points
  (smtw-review)`**, with one point: run `tooling/run-e2e-tests.bat` in the
  background, report the result and every failing test with the screen and
  the step it checks. The heading is the plug-in point the user's skill
  change looks for, so it is written exactly as here. The smtw-common change
  itself is the user's, outside S024.

### The older steps' reports (BR1-09)
A passing S024 run writes each covered check of S014–S018 as
`- [auto] <check> — S024 e2e/<file>::<test>` **in that step's own
`3-impl-report.md`**, and its real-device rows into `device-checks.md`. The
user then sets those steps' statuses (`Done`, or still pending the device
rows).

## 4. Data model

No migration. A new **database** `vel_yantra_e2e`, built by the existing
migrations at each run and thrown away.

## 5. Rules

### 5.1 The identity header stays a test-only door

- `require_auth` already honours `X-Test-Role` / `X-Test-User` only when
  `app.config["TESTING"]` is true and a `TEST_USER_FACTORY` is set (S013
  BR1-02). Production never sets either. The new pytest test (§ 3) shows a
  header-only request is 401 with `TESTING` off.
- **No silent admin** (BR1-01): with `DEV_AUTH_BYPASS=1`, a request without
  the header would fall to the dev stub user, `DEV_STUB_ROLE` — `"admin"` by
  default. The launcher sets `config.DEV_STUB_ROLE = "nobody"` before the
  first request, so such a request gets a user with no role and no
  membership (the "no access yet" page, 403 on the API), never admin. The
  seed and every helper must send the headers; `asPerson` checks who it is
  (§ 1.2).
- The launcher runs with `FLASK_DEBUG=1`, so `config.py`'s existing guard
  ("DEV_AUTH_BYPASS only with FLASK_DEBUG=1") holds, and binds to
  `127.0.0.1` only.
- It refuses to start unless the database host is `localhost` / `127.0.0.1`
  and the database name ends in `_e2e`, so a mistyped setting can never drop
  the dev database or reach another server. The guard is a small function
  with its own pytest test (§ 8).

### 5.2 The seed

Sites `SMTW` and `BRICKS` with their units from `seed_dev.py`; classes,
trades, manufacturers and models from it too; the S016 failure codes come with
the migrations.

**People** (each with a login equal to the username, a Team record, and the
browser sending `X-Test-Role: maintenance_team`, `X-Test-User: <login>`):

| Key | Login | Name | Role, site, units | Trade |
|---|---|---|---|---|
| operator | `e2e_operator` | Muthu (operator) | operator, SMTW, `MCC2` | — |
| supervisor | `e2e_supervisor` | Selvi (supervisor) | supervisor, SMTW, `MCC1`, `MCC2` | — |
| technician | `e2e_technician` | Kannan (technician) | technician, SMTW, all units | Mechanical |
| technician2 | `e2e_technician2` | Ravi (technician) | technician, SMTW, all units | Electrical |
| engineer | `e2e_engineer` | Priya (engineer) | engineer, SMTW, all units | — |
| manager | `e2e_manager` | Arun (manager) | manager, SMTW and BRICKS, all units | — |
| storekeeper | `e2e_storekeeper` | Devi (storekeeper) | storekeeper, SMTW, all units | — |
| operator_nologin | (no login) | Ramesh (operator, no phone) | operator, SMTW, `MCC2` | — |
| it_admin | `e2e_it_admin` | IT admin | token role `it_admin` (`X-Test-Role: it_admin`) | — |

Ramesh has no login (S017: IT admin may give a phone-less person an Operator
row): he is picked, never acts, for S017's "supervisor raises naming him" and
S018 § 5.8's "the operator fixed it himself" (BR2-03).

So `harness_user` takes the **memberships from the database**, as in
production: each person acts with their real role at their real units and
their own Team record (`current_person_id`), which S018's defaults,
auto-assign and pickers depend on. A wildcard site role would hide exactly
the bugs a browser test is for. The operator lacks `MCC1` and `KILN`, for the
"not at your units" paths; only the manager and IT admin reach `BRICKS`.

**Equipment**: at `SMTW.MCC2`, a machine `MCC2-EXT` (class from the seed)
with a component `MCC2-EXT-GBX`, and a scrapped machine; at `SMTW.MCC1` one
machine; at `BRICKS.FILTER` one machine. Ids are looked up by code in the
tests (§ 3), not hard-coded.

Each test file creates the tickets it works on; no test depends on another
test's ticket. Tests run **one file at a time** against the one database
(`workers: 1`), so they cannot race.

### 5.3 The console

`watchConsole` (§ 3) fails a test on a console error, a Vue warning or an
uncaught error, with the allow-list of two sources. A test that needs a
refused request (a 403 page) asserts the message on the page; the browser's
own "Failed to load resource" line for that one request is matched by URL and
status, not by a wider allow-list.

### 5.4 What a passing test must assert

A test asserts what the user would see, not only that the page opened: the
state badge, the timeline line, the times card's values, the refusal message
beside its field. "Every screen opens" asserts the screen's heading and no
console error. A test that only navigates is not an automated check.

## 6. API

No new endpoint. The seed uses the existing masters, Team, membership,
equipment and settings APIs with the admin headers.

## 7. Design decisions

1. **Playwright** over Cypress and Selenium. Playwright drives Chromium and
   WebKit (Safari's engine) from one API, emulates phones (size, touch,
   user agent), runs headless on Windows, and its test runner, traces and
   screenshots come in one package maintained by Microsoft with monthly
   releases. *Rejected:* Cypress — no WebKit on Windows in practice, one tab
   only; Selenium — needs separate drivers and a test runner of our own.
2. **Identity by the existing test header**, not by a login. *Rejected:* a
   test Keycloak realm with real users — the tests would need network access
   to Keycloak, real passwords in the repo, and would test Keycloak rather
   than Yantra; the login flow stays a real-device check.
3. **Real memberships from the database** (`maintenance_team` + username),
   not the wildcard site role the pytest harness uses for API tests (§ 5.2).
4. **A throw-away database per run**, not the pytest database and not the dev
   database: pytest empties tables between tests and would collide with a
   browser run; the dev data is the user's (ISO 27001 A 8.31).
5. **Separate ports (5002 / 5177)**, so the e2e run works while the user's
   dev servers run.
6. **A separate command, not in `run-tests.bat` or the release** (decided by
   the user, open question 1): browser runs take minutes and need ~500 MB of
   browsers; the coder and reviewer run it when screens change, the user
   when they ask, and `/smtw-review` as part of its audit.
7. **WebKit emulation is not an iPhone.** It catches layout, script and
   Safari-engine faults, but not iOS Safari's keyboard laid over the page,
   the camera, or real touch precision. Those stay on the real-device list.
8. **Thin top layer**: one test per user flow and per screen; field-level
   rules stay in the API tests, so the browser suite stays fast and does not
   break on every wording change. Locators use roles and visible text
   (`getByRole('button', { name: 'Close ticket' })`), not CSS classes, so a
   restyle does not break them — and so a renamed button is noticed. The
   dialog-fit check rides on the flow tests (§ 1.4) rather than a test per
   dialog.
9. **The workflow change goes with this step**, not later: without it,
   automated checks would still wait for a person's tick.
10. **A test machine on production** (named TEST in `SMTW.MCC2`, label marked TEST) for the
    few checks that must run there, rather than real machines: their tickets
    would otherwise enter the breakdown history and the KPIs.

## 8. Tests and acceptance

### The suite itself
- `tooling/run-e2e-tests.bat` runs green on the three projects, **twice in a
  row** (no leftovers between runs: the database and `scratch/e2e-data/` are
  rebuilt). The report records the first run's duration (open question 2).
- **The suite catches the faults it is for** — shown once, then reverted with
  `git checkout` (S018 committed by then): re-introduce S017's watcher order
  bug in `RaiseTicketView.vue` and S018 CR1-01's `blank: (seed) => seed` in
  one dialog; each makes the run red with a console error named in the
  report.
- **A lost header is refused**: a context without the headers lands on the
  "no access yet" page, and `/api/auth/me` shows no permissions (§ 5.1).
- `npm test` stays green (Vitest ignores `e2e/`); pytest stays green after
  `harness_user` moves (`tooling/run-tests.bat`).
- pytest: the launcher's guard refuses `vel_yantra_test`, `vel_yantra_master`
  and a non-local host; the header-only request with `TESTING` off is 401.

### Mapping of existing manual checks
Each pending important check of S014–S018 becomes either `[auto] <test>` in
its own step's report (§ 3) or a row of `device-checks.md`. Expected split:
- **Automated:** S017's raise paths and photo-step flow (upload of a test
  image file); all of S018's technician, supervisor, engineer, raise-again
  and A1 checks; S015's render and options, including parts indented under their machine
  with the count line (BR3-01); S016's masters; S014's layout
  (15 labels per sheet element, two sheets for 16) and `/e/<code>`.
- **Real device:** S014 print at 100 % and measure 52 mm, scan with Android
  and iPhone cameras on mobile data, the greased label; S015's two paper
  checks (print at 100 %, the header repeats on page 2); S017 a photo from a
  real camera; S018 the iPhone keyboard over the close dialog; a real login
  through Keycloak once — each with account, network and where (§ 1.6).

### Manual checks
On a real device / by a person:
- **Important:** the user runs `tooling/run-e2e-tests.bat` once on their own
  machine: it creates the database, installs the browsers, goes green, and
  the report opens.
- **Important:** the IT admin reads `docs/steps/device-checks.md` and says
  whether he could follow each row without help (BR1-13).

### Acceptance
Green on the three projects, twice; the two re-introduced bugs turn it red;
a lost header is refused; the workflow docs and agents carry the new rule; the
older steps' reports carry their `[auto]` lines; the device checklist exists.

## 9. Open questions and assumptions

1. ~~E2E in the release test command?~~ **Decided by the user (21-10-2026):
   no** — "only after a step needs it, or when i request so. maybe
   smtw-review might trigger / use it too". The suite runs when a step
   changes screens (coder and code reviewer), when the user asks, and from
   `/smtw-review` (§ 3).
2. **Run time.** It must stay under the agents' 10-minute Bash limit or run in
   the background (§ 3). If a full run takes much longer, files run in
   parallel with one database each (a later change).
3. ~~The e2e database on an existing dev DB~~ — settled (BR1-07): the bat
   creates it as root through the compose file; `init-test-db.sql` gains it
   for a fresh container.
4. ~~Who is the named person?~~ **Decided (21-10-2026): "IT Admin"** — the
   name written in the README rule, `device-checks.md` and the ticks
   (`— by IT Admin, DD-MM-YYYY`).
5. **The browsers download** (~500 MB, Chromium and WebKit) into the user
   profile's Playwright cache, once.
6. **The production test machine**: a machine named TEST in `SMTW.MCC2`,
   created by the user in the equipment register before the device checks.
   Its tickets are closed as *Not a fault*.

## 10. Amendments

### A1 — A `SMTW-Review` section in CLAUDE.md

```
Requested by: KLA, 21-10-2026 ("add to S024 a: write to CLAUDE.md asking it to add a SMTW-Review section. it can make use of playwrite if needed")
Status: Approved 21-10-2026 by KLA
```

**Why.** The user's change to smtw-common's `smtw-review` skill makes the
audit read a section of each project's `CLAUDE.md` with that repo's own
review points. Yantra's section names what the audit should check here, and
lets it use the browser tests when they help.

**What changes** (replaces the `## Additional review points (smtw-review)`
section of § 3; the heading is the one the user's skill change looks for):

1. `.claude/CLAUDE.md` gains a section **`## SMTW-Review`**, read by
   `/smtw-review`, with Yantra's own points:
   - **Browser tests:** the audit may run `tooling/run-e2e-tests.bat`
     (Playwright) when it helps — to confirm a finding about a screen, a
     permission shown or hidden, or a flow — or in full to report the suite's
     state; in the background, as it takes minutes. Not required on every
     audit.
   - **Steps:** check each committed step's status against its impl report
     (checks `[auto]`, ticked, skipped or pending) and list steps that are
     committed but not `Done`.
   - **Device checks:** list the open rows of `docs/steps/device-checks.md`.
   - **Previous audit:** read the latest `docs/review/*-smtw-review.md` and
     report the status of each of its findings.
2. The section says how it grows: a step that adds something a later audit
   should check (a new invariant, a check that only a full run shows) adds a
   point to it; the planner proposes the point in the step's brief.

**Where.** `.claude/CLAUDE.md` only; § 3's "Additional review points" bullet
is replaced by this.

**Tests.** None (a doc change); the next `/smtw-review` reads it.

**Open points.** None.

### A2 — Fix the three screen faults the browser tests found

```
Requested by: KLA, 21-10-2026 (the coder's questions 1–3 in 3-impl-report.md; "yes to all three")
Status: Approved 21-10-2026 by KLA
```

**Why.** The suite's first runs found three faults in screens already
committed (impl report, Questions 1–3). They are marked in the specs
(`test.fail`, `test.fixme`) rather than hidden; this amendment fixes them and
removes the marks, so the suite is fully green with no known fault.

**What changes.**

1. **Field messages drawn in WebKit** (S016, S017, S018 screens). A message
   shown through Bootstrap's sibling rule (`.is-invalid ~ .invalid-feedback`)
   is laid out at 0 × 0 by WebKit when the field turns red in the same update.
   Every such message is rendered instead as `v-if="<error>"` with `class="invalid-feedback d-block"`,
   the form several dialogs already use: the raise screen, the ticket move
   dialogs, Masters › Failure codes, and any other screen that uses the sibling
   rule (the coder lists them in the report). `expectFieldMessage` then checks
   "visible" on every project; the WebKit branch and the `test.fail` go.
2. **Add equipment's race** (S003). After Save the app navigates to the new
   equipment page while the dialog is still closing, and `FormModal` disposes
   Bootstrap's modal mid-animation ("Cannot read properties of null (reading
   'style')"). `FormModal` disposes the modal only after Bootstrap's
   `hidden.bs.modal` (or the navigation waits for it — the coder picks the one
   that fixes every caller, and says which). The `test.fixme` goes.
3. **Bootstrap loaded once** (S014). `main.js` loads `bootstrap.bundle.min.js`
   and the components import `{ Modal } from "bootstrap"`, so two copies both
   handle `data-bs-toggle="dropdown"` and the *Print label* menu opens and
   closes on one click. Exactly one copy is loaded. **No new dependency**: if
   the only way needs one (e.g. `@popperjs/core` for the ES build's
   dropdowns), the coder stops and asks. The `test.fail` goes.

**Where.** The screens of point 1, `FormModal.vue` (and the equipment list if
the navigation changes), `main.js` and the components importing Bootstrap
(`FormModal.vue`, `PhotoViewer.vue`); the specs and helpers that carry the
marks.

**Tests.** The full e2e run is green on all three projects with no
`test.fail` or `test.fixme` left for these faults; vitest and the backend
suite stay green. The device row for field messages on a real iPhone stays
(Playwright's WebKit is not Safari).

**Open points.** None.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 21-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BR1-01 a lost header runs as admin | major | **Accepted** (both options): the launcher sets `DEV_STUB_ROLE = "nobody"` in-process; `asPerson` checks `/api/auth/me` and the top bar; a test shows a header-less context is refused (§ 1.2, § 3, § 5.1, § 8) |
| BR1-02 the device checklist cannot be done as the IT admin | major | **Accepted** (1 and 2): rows carry account, network and where; production checks use a test machine; the round trip through the user and the planner is in § 1.5; the name stays out until given (§ 1.6, § 9 Q4, Q6) |
| BR1-03 "every dialog" unscoped | major | **Accepted** (option 2): one `expectDialogFits` called inside the flow tests on the dialogs they open, named in § 1.4; `dialogs.spec.js` dropped; later steps call it on their dialogs |
| BR1-04 `seed_dev.py` not importable | minor | **Accepted**: `call()` takes `base_url` and `headers`; `BASE_URL` moves into `main()`; the e2e seed imports the shared lists (§ 3) |
| BR1-05 Vitest picks up `e2e/` | minor | **Accepted**: `test.exclude` in `vite.config.js`; `npm test` stays green in § 8 |
| BR1-06 `harness_user` in the app package | minor | **Accepted** (option 1): `backend/tests/harness.py`, kept out of the image (§ 3) |
| BR1-07 launcher and config mechanics | minor | **Accepted**: the order of operations, drop/create on a plain connection, `use_reloader=False`, `reuseExistingServer: false`, `--strictPort`, `127.0.0.1`, `uv run`, the data folder emptied, the bat creating the DB as root (§ 1.1, § 3; Q3 settled) |
| BR1-08 the 401 test does not exist as claimed | minor | **Accepted**: a new pytest test with `TESTING` off (§ 3, § 5.1, § 8) |
| BR1-09 workflow gaps: older steps, keeping the list alive, sequencing | minor | **Accepted**: `[auto]` lines go into each older step's own report; every later coder appends device rows; S024 is coded after S018 is committed (header, § 1.5, § 3) |
| BR1-10 `watchConsole` allow-list | minor | **Accepted**: exactly the auth-bypass line and Vite's `[vite]` messages (§ 3, § 5.3) |
| BR1-11 seed people, names, ids | minor | **Accepted**: the people table in § 5.2; `harness_user` takes an optional name so the top bar shows who is acting; ids looked up by code in a `beforeAll` |
| BR1-12 the 10-minute limit for agents | minor | **Accepted**: agents run the bat with the maximum timeout or in the background; the first run's duration is recorded (§ 3, § 8, § 9 Q2) |
| BR1-13 checklist readability check important | nit | **Accepted**: important, read by the IT admin himself (§ 8) |
| BR1-14 what the bypass switches off | nit | **Accepted**: network gate and access log added to Out of scope |
| BR1-15 standards wording | nit | **Accepted**: Cohn named; traceability under ISO 9001 § 8.3.4 (§ 2) |

### User answers, 21-10-2026 (before round 2)

- Q1: not in the release test command; run when a step needs it, on request,
  and from `/smtw-review` → § 3 (Yantra's CLAUDE.md; the synced skill is not
  edited, BR2-01), § 7.6, Out of scope.
- Q4: the named person is "IT Admin" → § 1.6, § 9.

### Round 2 — `2-brief-review-r2.md` (Fable), answered 21-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BR2-01 the smtw-review skill is synced | major | **Accepted** (recommended route; the user decides at gate A): S024 does not edit Yantra's synced copy; Yantra's `CLAUDE.md` carries the instruction (read in the audit's Phase 1, used under Phase 3 *Tests*); the generic lines for smtw-common come ready to paste in the impl report (§ 3) |
| BR2-02 missing `X-Test-User` gives a `None` username and a 500 | minor | **Accepted**: the launcher's factory defaults the username to `e2e_<role>` and takes the name from the seed (§ 3) |
| BR2-03 no person without a login | minor | **Accepted**: Ramesh, operator with no login, at SMTW/MCC2 (§ 5.2) |
| BR2-04 S015's paper checks; print emulation does not paginate | minor | **Accepted**: DOM assertions on sheet elements; S015's three paper checks on the device list (§ 1.4, § 8) |
| BR2-05 `SMTW.TEST` reads as a unit | minor | **Accepted**: a machine named TEST in `SMTW.MCC2`, its code written into the rows once created (§ 1.6, § 7.10, § 9 Q6) |
| BR2-06 Done column | nit | **Accepted** (§ 1.6) |
| BR2-07 "its body scrolls" | nit | **Accepted**: buttons inside the viewport, dialog no taller than it (§ 1.4) |
| BR2-08 sys.path, charset, install every run, generic README | nit | **Accepted** (§ 3) |
| BR2-09 S014's IT-admin-on-mobile-data row | nit | **Accepted**: left off the device list; it is S013's expected refusal, covered by its API tests, and contradicts the Account rule |

### Round 3 — `2-brief-review-r3.md` (Fable), answered 21-10-2026

| Finding | Severity | Answer |
|---|---|---|
| BR3-01 S015's parts check is a screen check | minor | **Accepted**: automated in `asset-list.spec.js`; two paper checks on the device list (§ 8) |
| BR3-02 no login on the dev server | minor | **Accepted**: Account "none" on dev-server rows; a mobile-data row is a production row (§ 1.6) |
| BR3-03 leftovers; guard order | nit | **Accepted**: header date, the user-answers line, Q2 for the run time; the guard runs on the name the launcher has set (§ 3) |
| BR3-04 `request` fixture in `beforeAll` | nit | **Accepted**: `playwright.request.newContext` (§ 3) |

### User change, 21-10-2026 (at gate A)

"i will add instruction to the smtw-review skill to look at a section on
CLAUDE.md of the project for a section that contains instructions on
additional review points. that way, each repo could plug in into the
smtw-review" → § 3: Yantra's `CLAUDE.md` gains `## Additional review points
(smtw-review)` with the browser-test point; no paste-ready lines for
smtw-common (the user writes that change).

### User answer, 21-10-2026 (at gate A)

"The IT admin might be able to access the dev instance that is running on my
laptops to do some tests if required. that applies if my computer is plugged
in to the company / home network. She can also be asked to use a TEST machine
on PROD for the checks too." → § 1.6: each device row runs on the dev server
on KLA's laptop (company or home network) or on production on the TEST
machine, or either; the two deployment checks (Keycloak login, a label on
mobile data) are an *after deploy* section done once per release; the TEST
machine stays (Q6).

### Gate A, 21-10-2026 — approved by KLA

"brief approved", after the answers on the smtw-review plug-in point (user's skill change; Yantra's `## Additional review points (smtw-review)` section) and on where IT Admin does the device checks (dev on KLA's laptop or production on the TEST machine; after-deploy section).
