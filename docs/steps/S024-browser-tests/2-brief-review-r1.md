```
Step: S024 — Browser tests (Playwright)
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 21-10-2026
```

Reviewed against: 6c58b7a + uncommitted S018 (the working tree also carries uncommitted edits to `docs/steps/README.md` and `.claude/skills/step/SKILL.md`)

**Verdict: three `major` findings open (BR1-01 to BR1-03); no blocker.** The
approach is right and the auth claims check out against the code (§ Checked
below). The majors are: the e2e server's silent fall-back to the admin stub when
a request has no test header; the IT admin's checklist as written cannot be
carried out as the IT admin (network gate, production data, no account per
check); and "every dialog fits a phone" names neither the ~30 dialogs nor the
data state each needs.

## Findings

### BR1-01 — major — A request without the test header runs as admin, silently

**Problem.** The launcher runs with `DEV_AUTH_BYPASS=1` so the browser skips
Keycloak (`auth.js` `initAuth`: `config.devBypass` → `loadProfile()` with no
token). In `require_auth` the `X-Test-Role` branch comes first, but any request
*without* the header falls through to `_get_dev_stub_user()`, which is
`DEV_STUB_ROLE` from `secrets_app.py` — `"admin"` by default (`config.py`
line 80). So if a browser context, a popup, a `page.request` call or the seed
ever lacks the headers, it acts as admin: every screen opens, every button
shows, and a test "as operator" passes for the wrong reason. The seed in § 3
(`seed_dev.py`'s `call()`) sends no headers at all today and would "work" only
through this hole.

**Why it matters.** The brief's central claim (§ 1.2, § 7.3) is that every role
acts as itself with real memberships. An admin fall-back is exactly the
wildcard the brief says it rejects, reached by accident.

**Options.**
1. The launcher sets the stub to no access before the first request
   (`config.DEV_STUB_ROLE = "nobody"` in-process; `_get_dev_stub_user` reads
   it lazily and gives a user with no roles and no memberships), so a request
   that lost its headers is refused (403 / "no access yet" page), never
   promoted. The seed and every helper then *must* send the headers.
2. Additionally, `asRole(page, person)` asserts who is acting after the first
   load: `/api/auth/me` (via `page.request`) returns `username ===
   person.username`, and the screen shows that person. One cheap check per
   context that makes a lost header a loud failure.

**Recommendation.** Both. Record the no-access stub in § 5.1 as part of the
"test-only door" rule.

### BR1-02 — major — The real-device checklist cannot be done by the IT admin as written

**Problem.** § 1.6 and § 8 hand the real-device checks to the IT admin, but:
- **Network gate.** `it_admin` is refused off the plant network (S013,
  `INTERNAL_ONLY_ROLES`). S014's "scan with Android and iPhone on mobile
  data" and every "on a phone as a technician / supervisor / engineer" check
  of S017/S018 is done on mobile data by the people they name. As
  `it_admin` the scan shows the "plant network only" card (S014's own report
  says so). The checklist does not say which account each check needs.
- **Role.** `it_admin` does hold `ticket:work` / `ticket:close`
  (`config_rbac.py` 112–115), so the S018 dialogs open for him on the plant
  Wi-Fi; but "as a supervisor, pick the technician by typing" and the
  operator's *Machine stopped* need those roles, which `it_admin` is not.
- **Where.** Nothing says whether the checks run on production or the dev
  server. On production, S017/S018 checks raise and close real tickets:
  downtime, repeat-failure links and the month's `TK-` serials are KPI data
  (ISO 14224 records; SMRP availability). A non-developer must be told where
  to do it and on which machine, or be given a marked test node.
- **The round trip.** "to tick and date" a Markdown file in the repo is not
  something a non-developer does. How the list reaches him (printed, chat), how
  his result comes back, and who writes `— by <name>, DD-MM-YYYY` into the
  step's impl report (the user, via the planner) is unstated.

**Why it matters.** The brief's own rule: a flow the person cannot carry out as
described is `major`. Today the IT admin would open the list, try the first
scan on his phone and hit the network card.

**Options.**
1. Each row of `device-checks.md` names **account**, **network** and
   **where**: e.g. "a `maintenance_team` login with a Technician row at SMTW
   (ask KLA for the test login), on mobile data, on the dev server at
   `http://<dev-pc>:5176`" or "on production, on the test machine `<code>`
   (label marked TEST), and tell KLA so the test tickets are closed as *Not a
   fault*". The IT-admin-only rows (print, measure, greased label) need no
   login.
2. Define the round trip in README § Manual checks: the user gives the list
   to the named person; the result comes back to the user, who tells the
   planner; the planner writes `[x] … — by <name>, DD-MM-YYYY`. The file is
   the master list, not the ticking medium.
3. Keep the IT admin's name out of the repo file until open question 4 is
   answered; "the named person" with the name in the status line is enough.

**Recommendation.** 1 and 2; the brief's § 1.6 gains the three columns
(account, network, where) and § 8's "Real device" list gets the same.

### BR1-03 — major — "Dialogs fit a phone" and "the dialogs opened from each screen" are unscoped

**Problem.** The code has about thirty dialogs: 21 `<FormModal>` uses (every
masters panel's add/edit, document title and upload, ticket raise/edit), plus
`AssignDialog`, `EditTicketDialog`, `MoveDialog`, `RegradeDialog`,
`EquipmentFormModal` (×2), `EquipmentMoveModal`, `EquipmentStatusModal`. Each
needs a data state to open (an in-progress ticket for *Close*, a ticket with
labour for *Remove labour*, a node with a document for *Title*), a role, and a
locator. The brief says "every dialog" twice (§ 1.4) and names none; the coder
would choose the list and the states alone, which is the size of the step.

**Why it matters.** Unscoped, this is either a week of fixtures or a token
sample; either way the user cannot judge what was approved.

**Options.**
1. List the dialogs in § 8 (the grep above is the list) with the state and
   role each needs, and keep "every dialog".
2. Scope it: one shared assertion `expectDialogFits(page)` (Save and Cancel
   `boundingBox()` inside the viewport, body scrollable) called **inside the
   flow tests** on every dialog they open anyway (S017 raise, S018 acknowledge
   / start / back in service / close / send back / regrade / assign / labour,
   S016 add/edit, S012 model, equipment add/move/status), plus the masters
   Add dialogs opened from seed state. New dialogs are covered by the rule
   that each step's flow test calls it. `dialogs.spec.js` then goes; the
   check lives where the data already is.

**Recommendation.** 2 — it is the thin top layer § 7.8 asks for. `FormModal`
already uses `modal-dialog-scrollable` with a fixed footer, so the assertion
is mostly a regression guard for dialogs that bypass `FormModal`.

### BR1-04 — minor — `seed_dev.py` cannot be imported as it is

**Problem.** § 3 says the e2e seed reuses `seed_dev.py`'s `call()` and its
lists "import, not copy". But `call()` reads a module-level `BASE_URL` taken
from **`sys.argv[1]` at import** (default `http://localhost:5001` — the user's
dev backend), and sends no headers (it relies on the dev stub). Imported from
`seed_e2e.py`, it would post the seed into the dev database, or (with BR1-01)
be refused.

**Fix.** A small refactor of `seed_dev.py`, named in § 3: `call(method, path,
body=None, *, base_url, headers=None)` (or a tiny `Api(base_url, headers)`
class with `.call`), `main()` passing its own; `dev-seed.bat` unchanged in
behaviour; the lists (`SITES`, `UNITS`, `CLASSES`, `MANUFACTURERS`, `MODELS`,
`TRADES`) imported, `PEOPLE` and `EQUIPMENT` defined by the e2e seed (see
BR1-11). Note `seed_dev.py` is a script in `tooling/dev/`, so `seed_e2e.py`
needs `tooling/dev` on `sys.path` or the shared part moves to a module both
import.

### BR1-05 — minor — Vitest will pick up `frontend/e2e/*.spec.js` and go red

**Problem.** `vite.config.js` sets `test: { environment: "jsdom" }` with no
`include`/`exclude`, so Vitest's default glob (`**/*.{test,spec}.?(c|m)[jt]s`)
matches `e2e/screens.spec.js` and friends; `npm test`
(`tooling/run-frontend-tests.bat`, and so `run-tests.bat` and the release
`TEST_CMD`) would fail on Playwright's `test` import.

**Fix.** `test.exclude: [...configDefaults.exclude, "e2e/**"]` in
`vite.config.js` (from `vitest/config`), named in § 3; and § 8 adds "`npm
test` stays green".

### BR1-06 — minor — `harness_user` belongs under `backend/tests/`, not in the app package

**Problem.** § 3 moves `harness_user` to `backend/test_identity.py`.
`.dockerignore` excludes `backend/tests/` but the Dockerfile copies
`backend/` wholesale, so a test-only identity factory would ship in the
production image (inert — `TESTING` is never set there — but a layering
smell: `auth_utils` already carries the dev stub, which is the one dev-only
identity the app owns; a second one, for the harness, is test code).

**Options.**
1. `backend/tests/harness.py` with `harness_user` (no pytest import);
   `conftest.py` imports it (`from tests.harness import harness_user`, as it
   already imports `tests.access_helpers`); the launcher puts `backend/` on
   `sys.path` and imports `tests.harness`. Importing `conftest` itself is not
   an option: it mutates the DB name to `vel_yantra_test`, pops
   `DEV_AUTH_BYPASS` and sets `DATA_DIR` at import.
2. Keep the brief's placement and add `backend/test_identity.py` to
   `.dockerignore`.

**Recommendation.** 1. DRY is met either way; 1 keeps the app package free of
harness code.

### BR1-07 — minor — Launcher and config mechanics the coder must get right

The brief is right that `config.py` picks the DB from `secrets_app.DB_NAME`
and `DATA_DIR` from the env; the details below decide whether the stack works
and should be in § 3 / § 5.1 so the coder doesn't rediscover them:
- **Order of operations.** `FLASK_DEBUG=1`, `DEV_AUTH_BYPASS=1` and
  `DATA_DIR` (absolute, not `scratch/e2e-data` relative to whatever cwd
  Playwright uses) must be in `os.environ` **before `import config`**
  (`config.py` raises without `FLASK_DEBUG`); `config.DB_CONFIG["database"] =
  "vel_yantra_e2e"` **before `import app`**, because `app.py` calls
  `init_pool(DB_CONFIG)` and `ensure_schema(DB_CONFIG)` at import — the same
  trick `conftest.py` uses.
- **Drop and create before `import app`**, on a plain `pymysql` connection
  with no database selected. `GRANT ALL ON vel_yantra_e2e.*` includes CREATE
  and DROP on that one database, so the app user suffices once the grant
  exists.
- **No reloader.** `app.run(host="127.0.0.1", port=5002, debug=True)` starts
  Werkzeug's reloader, which re-runs the launcher in a child process: the
  drop/create runs twice and Playwright's `webServer` sees two processes.
  Use `use_reloader=False` (debug=False is fine too; `IS_DEV` comes from the
  env var, not from `app.run`).
- **Playwright `webServer`.** `reuseExistingServer: false` for both entries
  (a reused backend has not been reset); Vite started with `--port 5177
  --strictPort` (without `strictPort` Vite silently moves to 5178 when 5177
  is busy and the `url` wait times out); the proxy target
  `http://127.0.0.1:5002`, not `localhost` — Node 17+ may resolve `localhost`
  to `::1`, and the brief binds the backend to `127.0.0.1` only. The backend
  command runs in the backend's uv environment (`uv run --project backend
  python tooling/e2e/e2e_backend.py` or equivalent).
- **Data folder.** Wipe `scratch/e2e-data/` with the database at each run
  (photos from the last run otherwise pile up), and say so in § 8's "no
  leftovers".
- **The e2e database's creation** (open question 3): the bat can create it
  itself — `docker compose -f tooling/dev/docker-compose.dev.yml exec -T
  mariadb mariadb -uroot -pdev-root-password -e "CREATE DATABASE IF NOT EXISTS
  vel_yantra_e2e …; GRANT …"` (the root password is in the compose file, dev
  only). Then no manual step and no `dev-db-reset.bat`. `init-test-db.sql`
  still gains the lines for a fresh container. Recommend this as the answer
  to OQ3.

### BR1-08 — minor — The "production app answers 401 to X-Test-Role" test does not exist as claimed

**Problem.** § 5.1 says a test "exists in pytest since S013" that the app
without `TESTING` refuses a header-only request. What exists is
`test_no_test_user_factory_is_401` (`test_access_control_api.py` 115): the
**factory** removed, `TESTING` still on. The suite never runs with `TESTING`
off — the `app` fixture sets it on the module-level app and never resets it.

**Fix.** Either reword § 5.1 to the test that exists, or add the five-line
test (monkeypatch `app.config["TESTING"] = False`, header only → 401 via the
Keycloak path's `no_token`). Recommend adding it: it is the guard the brief
leans on.

### BR1-09 — minor — Workflow change: three gaps against README § Manual checks and the skill

1. **The older steps.** § 8 copies S014–S018's pending checks into S024's
   report. But S015–S018 sit at "manual checks pending" in the index; the
   brief should say that a passing S024 run marks each covered check `[auto]
   … — S024 e2e/<file>::<test>` **in that step's own impl report**, and
   that the user then sets those statuses (`Done`, or still pending the
   device rows). Otherwise they stay pending with their evidence in another
   step's file.
2. **Keeping `device-checks.md` alive.** The brief writes it once from
   S014–S018. The ongoing rule — each step's coder appends its real-device
   checks; a ticked row stays as the record (name, date) rather than being
   deleted; the planner moves the tick into the impl report (BR1-02 option
   2) — belongs in README § Manual checks and `coder.md`, and the brief's
   § 1.5 should state it.
3. **Sequencing with S018.** S018 is uncommitted and in code review; S024's
   flow tests target it. Say in § 9 that S024 is coded after S018 is
   committed (or at least after its review closes), so the tests are written
   against settled screens. The "re-introduce the two bugs" demonstration in
   § 8 also cannot use `git checkout -- <file>` to revert while S018 is
   uncommitted in those same files; after the S018 commit it can.

Also: the SKILL.md gate-B text and README § Gates 4 both say "ticked by the
user or explicitly skipped by them"; both need the `[auto]` and named-person
wording, and the brief lists both files — consistent. The `[auto]` marker as a
third state beside `[x]` / `[skipped]` is fine.

### BR1-10 — minor — `watchConsole` needs a stated allow-list

`auth.js` logs `console.warn("Auth bypass: DEV_AUTH_BYPASS enabled on
backend.")` on **every** page load under the bypass; Vite's dev client logs
`[vite] connected`; Vue dev-mode warnings are what the test is for. A
`watchConsole` that fails on "any console error or Vue warning" fails every
test unless the auth-bypass line (and Vite's own messages) are allowed. Name
the allow-list in § 3 (`support/people.js`), and keep it to those two
sources so a new warning is still caught.

### BR1-11 — minor — The seed people, their units, and how tests find the seed

- **The PEOPLE table.** S018's flows depend on who holds which units: the
  technician must hold the machine's unit for auto-assign; the supervisor's
  picker lists technicians at the site; the operator's "not at your units"
  needs a unit he lacks; the manager needs a BRICKS membership for § 5.2's
  "nobody but the manager". Write the table in § 5.2 as `seed_dev.py` does
  (`name, login, [(site, role, units | "all")]`), so the tests and the user
  can read it.
- **Display names.** `harness_user` names every user `Test maintenance_team`
  (`name = f"Test {role_name}"`), so the top bar — the "who is acting" check
  for shared logins — shows the same text for all six people, and a test
  asserting "Recording as <name>" would see it. The launcher's factory should
  pass a name from the seed (e.g. the person's name by username), or the
  harness take an optional name.
- **Ids.** Tests need ids for `/equipment/:id`, `/tickets/:id`, `/e/<code>`.
  Simplest: look them up by code through the API with the admin headers in a
  `beforeAll` (`page.request` / `request.newContext` with the same
  `extraHTTPHeaders`); say so, rather than a seed file the tests parse.

### BR1-12 — minor — Run time is a hard limit for the agents, not an assumption

Assumption 2 ("under 10 minutes") is also the Bash tool's maximum foreground
timeout (600 s) for the coder and code-reviewer subagents the brief tells to
run `tooling/run-e2e-tests.bat`. Three projects × every screen × every role
with one worker can approach it. Put in § 3's agent changes: run the bat with
the maximum timeout or in the background and read the result file; and in
§ 8 record the first run's duration, so OQ1 is decided on a number.

### BR1-13 — nit — Mark the checklist's readability check **important**

§ 8's second manual check (the IT admin can follow `device-checks.md`
without help) is the one deliverable aimed at a non-developer and the one
only a person can judge; it should be **important**, read by the IT admin
himself, not by the user.

### BR1-14 — nit — Say what the bypass switches off

Under `DEV_AUTH_BYPASS=1` both `require_network` and the access-log hook are
skipped (`access_control._skipped`). So the e2e stack never exercises the
network gate, the "plant network only" card, or writes a row to
`access_log` — Settings › Access log opens empty. Add to Out of scope with
the S013 line, so nobody later writes an e2e test for them and wonders.

### BR1-15 — nit — Standards wording

ISO 9001 § 8.3.4, ISO 27001:2022 A.8.29 / A.8.31 and ISO 9241-11 are cited
correctly and explained. Two small additions for the learner: the test
pyramid is Mike Cohn's (*Succeeding with Agile*, 2009), and a test's name
stating the requirement it verifies is the "traceability" ISO 9001 § 8.3.4
records are about. No maintenance standard applies to this step itself; the
brief rightly does not force one.

## Checked and found consistent

- **`require_auth` header path** (`auth_utils.py` 224–234): honoured only
  when `app.config["TESTING"]` and a `TEST_USER_FACTORY` are set; checked
  before the dev-bypass branch, so with both on, the header wins. No change
  to `auth_utils.py` is needed, as § 3 says. Production never sets either.
- **`harness_user("maintenance_team", "e2e_x")`** → `make_user(…,
  ["maintenance_team"])` with `memberships=None` → `current_memberships()`
  reads `memberships` by `current_person_id`, which resolves `people.username
  = normalise_username(g.user["username"])` (stripped, lower-cased) and
  `active = 1`. The person acts with their DB role at their site and their
  own Team record, as § 5.2 claims; `person_id` reaches the frontend via
  `/api/auth/me`.
- **Frontend bypass**: `/api/auth/config` returns `devBypass:
  DEV_AUTH_BYPASS`; `initAuth` then skips Keycloak and calls `/api/auth/me`
  with no token; `api.js` sends no `Authorization` when `getToken()` is null.
  Playwright's `extraHTTPHeaders` on the context applies to the page's
  `fetch()` calls, and through the Vite proxy the calls are same-origin, so
  no CORS preflight and `CORS_ORIGINS` needs no change.
- **DB and data selection**: `config.DB_CONFIG` built from `secrets_app`
  (dev default `127.0.0.1:3307`, user `vel_yantra_master`); `DATA_DIR` from
  the env with `abspath`; `conftest.py` shows the in-place mutation pattern
  the launcher can copy.
- **Ports**: 5001/5176 are hard-coded in `app.py` `__main__` and
  `vite.config.js`; the launcher's own `app.run` and `vite --port` override
  them without touching the dev run configs.
- **`vel_yantra_test`** is cleaned per session by `_clean_tables`, so a
  separate `vel_yantra_e2e` is the right call (§ 7.4).
- **npm**: `npx npm@11 install` per CLAUDE.md; **S022**: only
  `package-lock.json` changes, so `sbom/frontend.cdx.json` is the one SBOM to
  regenerate and commit; `uv.lock` untouched (the launcher uses `pymysql`
  and the stdlib).
- **`.gitignore`** already covers `scratch/`; Playwright's `outputDir` and
  the HTML reporter's `outputFolder` can both be pointed there.
- **Workflow files**: README § Manual checks / § Gates 4, SKILL.md gate B
  and the three agents are the complete set that states the tick rule; the
  brief names all of them.
- **Track full** is right: new dev dependency, auth-adjacent harness, a new
  database, and a workflow rule change.
- **Playwright facts**: WebKit runs on Windows; `devices["Pixel 7"]` and
  `devices["iPhone 14"]` exist; `workers: 1` serialises files and projects
  against the one database.
