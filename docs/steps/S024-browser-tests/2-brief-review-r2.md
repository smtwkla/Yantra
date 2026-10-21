```
Step: S024 — Browser tests (Playwright)
Doc: brief-review r2
Author: Brief reviewer (Fable)
Date: 21-10-2026
```

Reviewed against: 6c58b7a + uncommitted S018 (the working tree also carries uncommitted edits to `docs/steps/README.md`, `.claude/skills/step/SKILL.md` and the S017 docs)

**Verdict: one `major` finding open (BR2-01); no blocker.** Every round-1
finding marked *Accepted* is in the brief text, not only in the log (§ Round 1
below). The revision's mechanics check out against the code: the launcher's
order of operations, `DEV_STUB_ROLE = "nobody"`, the `harness_user` change,
the bat's compose call and the seed people all hold. The one major is a false
claim about a file: `.claude/skills/smtw-review/SKILL.md` **is synced** from
smtw-common, so the edit the brief plans there would be overwritten at the
next sync; the user decides where the `/smtw-review` hook lives.

## Round 1 — Accepted findings verified in the text

| Finding | Where it now stands in the brief | Verified |
|---|---|---|
| BR1-01 | § 1.2 identity check; § 5.1 "No silent admin"; § 8 "A lost header is refused"; § 3 no `auth_utils.py` change | yes |
| BR1-02 | § 1.6 columns account / network / where; § 1.5 round trip; § 7.10 and § 9 Q6 test machine | yes |
| BR1-03 | § 1.4 names the dialogs; `dialogs.spec.js` gone from § 3; later steps call `expectDialogFits` | yes |
| BR1-04 | § 3 `seed_dev.py` refactor: `call(method, path, body=None, *, base_url, headers=None)`, `BASE_URL` into `main()` | yes |
| BR1-05 | § 3 `vite.config.js` `test.exclude`; § 8 "`npm test` stays green" | yes |
| BR1-06 | § 3 `backend/tests/harness.py`, `.dockerignore` keeps it out | yes |
| BR1-07 | § 3 launcher steps 1–5, `use_reloader=False`, `reuseExistingServer: false`, `--strictPort`, `127.0.0.1`, data folder emptied; § 3 bat creates the DB as root | yes |
| BR1-08 | § 3 new test in `test_access_control_api.py` with `TESTING` off; § 5.1; § 8 | yes |
| BR1-09 | header "Coded after S018 is committed"; § 1.5 later coders append; § 3 "The older steps' reports" | yes |
| BR1-10 | § 3 `support/console.js` allow-list of two sources; § 5.3 | yes |
| BR1-11 | § 5.2 people table; `harness_user(…, name=None)`; ids by code in a `beforeAll` | yes |
| BR1-12 | § 3 coder / code-reviewer run with the maximum timeout or in the background; § 8 duration; § 9 Q2 | yes |
| BR1-13 | § 8 second manual check **important**, read by the IT admin | yes |
| BR1-14 | Out of scope: network gate and access log | yes |
| BR1-15 | § 2 Cohn named; traceability under ISO 9001 § 8.3.4 | yes |

BR1-02's log line says "the name stays out until given"; the name is now
given (user answer Q4) and written in § 1.6 and § 9 — consistent.

## Findings

### BR2-01 — major — `.claude/skills/smtw-review/SKILL.md` is synced from smtw-common; a local edit is overwritten

**Problem.** § 3 says of the smtw-review skill: "The file is this repo's own
(not synced), so the change is local." It is synced:
`tooling/common/sync_common.py` lists `(".claude/skills", ".claude/skills")`
under `DIRS`, and `sync_dir()` writes every file found in smtw-common's
`.claude/skills/` over the local copy (`dest_path.write_text(content)`), no
exclusions. `smtw-review/SKILL.md` came in with the `init` commit (the sync)
and is generic (it reads `docs/Module-*.md` and `docs/Schema.md`, which Yantra
has none of). So the coder's edit lands, and the next `sync_common.py` run
removes it silently. (`step/` is not affected: it exists only here.)

**Why it matters.** The user decided (Q1) that `/smtw-review` runs the suite;
the brief's vehicle for that decision disappears on the next sync, and nobody
would notice until an audit skipped the browser tests. The decision stands;
*where* it is written must change, and that is the user's call because one
option is a change in another repo.

**Options.**
1. **The generic line goes to smtw-common's copy** of the skill, worded as the
   brief already has it ("when the repo has `tooling/run-e2e-tests.bat`, run
   it … and report …"), as a ready-to-paste change the user makes in
   smtw-common (outside S024; listed under "not done / for the user" in the
   impl report). S024 does not touch the local file. Yantra's `CLAUDE.md`
   bullet (already in § 3) carries the repo-specific part; the audit reads
   `CLAUDE.md` in its Phase 1, so the bullet already reaches it.
2. **The `CLAUDE.md` bullet only**, worded as an instruction the audit acts on
   ("`/smtw-review` runs `tooling/run-e2e-tests.bat` as part of Phase 3 …"),
   and the skill left alone. Weaker: a generic skill is not told to look for
   it; it works only because the audit reads `CLAUDE.md`.
3. A sync exclusion — not viable: `sync_common.py` is itself synced
   (`SELF_SRC`), so an exclusion list added here is overwritten too.

**Recommendation.** 1, with 2's wording in the `CLAUDE.md` bullet as the
belt-and-braces. In § 3, replace the smtw-review entry with "no change in
this repo; the line for smtw-common's copy is given in the impl report"; in
§ 7.6 keep "from `/smtw-review`" and say how. Also name the phase it joins
(Phase 3 *Cross-cutting checks*, item 8 *Tests*), so whoever edits the
skill does not restructure it.

### BR2-02 — minor — The launcher's factory: default the username, and say where the name comes from

**Problem.** § 3 step 4 says the factory "calls `harness_user` with the seed
person's name", nothing more. Two things the coder would otherwise decide:
- **A request with `X-Test-Role` but no `X-Test-User`** — the seed's own
  admin requests, as § 3 describes them (`X-Test-Role: admin`) — reaches the
  factory with `username=None`. `conftest.py`'s factory defaults it
  (`username or f"test_{role_name}"`); a factory that does not would set
  `g.user["username"] = None`, and the first write fails: `actor()` returns
  `g.user["username"]` and every master's `created_by` is `VARCHAR(100) NOT
  NULL` (`local_db.py`), so the seed's first `POST /api/masters/sites` is a
  500. (`normalise_username(None)` returns `""`, so reads survive; writes do
  not.)
- **Where the name comes from.** The seed runs *after* the backend is up
  (`globalSetup`), so the factory cannot read a seed file at start-up unless
  it imports the list. Simplest: the launcher imports `PEOPLE` from
  `seed_e2e.py` (same folder, `tooling/e2e`) and maps login → name, falling
  back to the username; no query per request.

**Fix.** In § 3 step 4: the factory defaults the username as `conftest.py`
does (or the seed always sends `X-Test-User: e2e_admin`, which also makes the
seed's `created_by` readable), and takes the name from `seed_e2e.PEOPLE` by
login, else the username.

### BR2-03 — minor — The seed has no person without a login

**Problem.** The people table in § 5.2 gives everyone a login. Two flows the
brief says it automates need a phone-less person at `SMTW.MCC2`:
- S017's third important check: "As IT admin, give a person without a login
  an Operator row at a site; as a supervisor there, raise a ticket naming
  that person as *reported by*" (S017 § 8) — § 8 here maps "S017's raise
  paths" to automated;
- S018 § 5.8: the person named on back in service may be any person with a
  membership at the site, "operators included … a defect the operator fixed
  himself" — the TPM autonomous-maintenance case the supervisor's picker
  exists for.

Without the row, the coder either adds one in the test (fine, but then the
"ask KLA" seed table in the brief is not what runs) or skips the check.

**Fix.** Add a row to § 5.2: `Ramesh (operator, no login)` — no login, an
Operator row at `SMTW`, unit `MCC2`, set by the admin seed (only IT admin may
set an Operator row without a login, `NO_LOGIN_ROLES`; the seed's `PUT
/people/<id>/sites/<site_id>` path in `seed_dev.py` does exactly this). A
technician without a login is not needed: the two with logins cover
auto-assign and the picker.

### BR2-04 — minor — S015's print checks fall out of both lists; "2 pages in print emulation" is not observable

**Problem.** § 8's mapping sends "S015's render and options" to automated and
names no S015 row on the device list. S015's three **important** checks are
all paper checks (S015 § 8): one unit with checklist columns on the office
printer at 100 % with no column cut off; a two-page unit where the header
repeats on page 2 and the next unit starts a new page; parts indented with
the count line. The third can be asserted in the DOM; the first two cannot:
`page.emulateMedia({ media: "print" })` applies print CSS but does not
paginate, so neither "page 2" nor a cut-off column exists to assert. The same
applies to S014's "16 labels make 2 pages in print emulation" (§ 1.4, § 8):
only `page.pdf()` (headless Chromium, desktop project only) paginates, and
reading a page count out of the PDF needs a parser or a fragile regex.

**Options.**
1. Keep the DOM-level assertions (15 label cells per sheet element, two sheet
   elements for 16; the asset list's columns, indentation and count line) and
   put the paper facts (page 2's header, nothing cut off, 52 mm) on the device
   list as print rows — account "none", where "dev server", network "plant
   Wi-Fi" — done by the IT admin on the office printer.
2. `page.pdf()` in the desktop Chromium project and a page count — a
   dependency or a hand-rolled PDF read for one assertion.

**Recommendation.** 1. Reword § 1.4 and § 8 ("two sheets in the DOM", not
"2 pages in print emulation") and add the S015 and S014 print rows to the
expected device list.

### BR2-05 — minor — The production test machine: `SMTW.TEST` is a unit path, not a machine

**Problem.** § 1.6, § 7.10 and § 9 Q6 call the test machine `SMTW.TEST`. In
Yantra `SITE.UNIT` is the unit's full code (`seed_dev.py` `SMTW.MCC2`;
`equipment_core.full_path`), and a machine's own code is
`<class prefix><nnn>` given at creation (`format_equipment_code`: `EXT001`),
never typed. § 9 Q6 then places it "in unit `SMTW.MCC2` (or a unit of its
own)" — so the name says *unit*, the text says *machine in MCC2*. The person
following a device row needs the code that is on the label.

**Fix.** Say "a machine named **TEST** in `SMTW.MCC2`, created by the user in
Masters before the device checks; its code (`<prefix>nnn`) is written into
the rows of `device-checks.md` once known; the label marked TEST". Keep MCC2
rather than a unit of its own: the real technician and supervisor logins used
for the rows hold MCC2 already; a `TEST` unit would need every such login to
be given it first.

### BR2-06 — nit — `device-checks.md` needs a fifth column: done by whom, when

§ 1.6 lists four columns; § 1.5 says "a done row stays as the record (who,
when)". Add **Done** (`— by IT Admin, DD-MM-YYYY`, blank while open) so the
file carries the record it claims to.

### BR2-07 — nit — `expectDialogFits`: "its body scrolls" cannot be asserted on a short dialog

§ 1.4 defines the assertion as Save and Cancel inside the viewport
(`boundingBox()`) "and its body scrolls". A dialog shorter than the phone
screen has nothing to scroll. Define it as: the footer buttons' boxes lie
inside the viewport, and the dialog's own box is no taller than the viewport
(so a tall body must be the part that scrolls). `FormModal` already uses
`modal-dialog-scrollable`; the check guards the dialogs that bypass it.

### BR2-08 — nit — Small launcher and bat details

- `tooling/e2e/e2e_backend.py` lives outside `backend/`, so `backend/` goes on
  `sys.path` **before** `import config` (`config.py` imports `auth_utils`
  itself), and `tooling/e2e` for `seed_e2e` (BR2-02). § 3 said this in
  round 1 (BR1-06 option 1) and the revision dropped it.
- `CREATE DATABASE vel_yantra_e2e` in the launcher (step 3) and the bat
  should carry `CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci` as
  `init-test-db.sql` does, so the three databases match.
- Bat step 3 "installs the browsers on first use": `npx playwright install
  chromium webkit` is idempotent and returns at once when they are present;
  run it every time rather than detect "first use".
- The README rule (§ 3 "Workflow docs") can say "a person the user names —
  today the IT admin" rather than hard-code the title into the convention;
  the name belongs in the rows and the ticks (Q4), where the brief also puts
  it.

### BR2-09 — nit — One device row contradicts the Account rule

§ 1.6: "never the IT admin account on mobile data (it is refused off the
plant network)". S014's plain check "As IT admin on mobile data, a scanned
label shows the 'plant network only' card (expected)" is exactly that, on
purpose. If it goes on the list, word the row as the expected card; or drop
it (it is a plain check, and S013's API tests cover the gate).

## Checked and found consistent

- **`DEV_STUB_ROLE = "nobody"`** (`auth_utils._get_dev_stub_user`): the
  cache `_DEV_STUB_USER` is built on the first call, nothing calls it at
  import, so the launcher's in-process setting before the first request
  takes effect. `"nobody"` is neither a site role nor a token role →
  `make_user("dev", "Dev User", [], [])`: `permissions` empty, `memberships`
  a fixed empty list (`current_memberships()` returns it without a query).
  `require_perm` → `has_perm` → `global_permissions([], [])` empty → 403.
  `/api/auth/me` → `role` null, `permissions []`, `sites []`, `person_id`
  null (no person with login `dev`). Frontend: `loadProfile` sets
  `authenticated` true with an empty permission list → `App.vue`'s
  `noAccess` → `NoAccessView`, the nav empty. § 5.1 and § 8 hold. A context
  without headers would answer `username: "dev"`, so `asPerson`'s identity
  check fails loudly, as § 1.2 says.
- **Launcher order** (§ 3): `FLASK_DEBUG` / `DEV_AUTH_BYPASS` / `DATA_DIR`
  before `import config` (the bypass guard at `config.py` 77; `DATA_DIR`
  read with `abspath` at 90); `DB_CONFIG["database"]` mutated in place before
  `import app` (`app.py` 30–31 `init_pool` / `ensure_schema` at import);
  `app.run(host="127.0.0.1", port=5002, use_reloader=False)` leaves `IS_DEV`
  to the env var. `GRANT ALL ON vel_yantra_e2e.*` survives `DROP DATABASE`
  (MariaDB keeps `mysql.db` rows), so the app user's drop/create works every
  run once the bat has made the grant.
- **The bat's compose call**: service `mariadb`, image `mariadb:11.4` (the
  `mariadb` client is in it), `MARIADB_ROOT_PASSWORD: dev-root-password`,
  project `yantra-dev`; the grant to `'vel_yantra_master'@'%'` matches
  `init-test-db.sql`.
- **`harness_user(role, username, name=None)`**: only `conftest.py`'s
  `_test_user_factory` calls it, and no test asserts the `Test <role>` name
  (`grep` of `backend/tests/`); `name or f"Test {role_name}"` keeps the suite
  unchanged. `from tests.harness import harness_user` follows the existing
  `tests.access_helpers` import. `.dockerignore` excludes `backend/tests/`.
- **The seed people against S011 / S018**: IT admin creates each person with
  `username` + `sites` in one `POST /people` (`masters:edit`; the Operator row
  is IT admin's). Technician Kannan (`maint_technician`, all units of SMTW)
  qualifies for auto-assign on acknowledge / start (S018 § 5.8); the
  supervisor Selvi (`MCC1`, `MCC2`) holds `ticket:restore` but not
  `ticket:work`, so back in service asks her to name someone and the picker
  (people at SMTW) lists Kannan; the engineer holds `ticket:close` /
  `ticket:assign`; the operator Muthu (`MCC2` only) holds `ticket:raise` /
  `ticket:restore` at SMTW and lacks `MCC1` / `KILN` for the "not found"
  paths (S017 check 2); A1 *Already fixed* needs `ticket:work`, so the
  technician; only the manager (BRICKS all units) and IT admin (token,
  `equipment:read_all_units`) reach `BRICKS`; the storekeeper holds the `*`
  keys only (Equipment, Masters). An IT admin with a Team record is never
  auto-assigned or pre-filled (S018 § 5.7), as the table implies.
- **`seed_dev.py` refactor**: `call()` is the only user of `BASE_URL`;
  `main()` reads `sys.argv` itself; `dev-seed.bat` unchanged. The lists
  `SITES`, `UNITS`, `CLASSES`, `TRADES`, `MANUFACTURERS`, `MODELS` are plain
  module constants, importable once `tooling/dev` is on `sys.path`.
- **Vitest exclude**: `configDefaults` comes from `vitest/config`; `vitest`
  4.1 is a devDependency. **Playwright**: two `webServer` entries are
  supported; the web servers start before `globalSetup`, so the seed finds
  5002 up. `devices["Pixel 7"]` / `devices["iPhone 14"]` exist.
- **S018 CR1-01 and the S017 watcher bug** (§ 8's re-introduce demonstration)
  are real and committed/committable: `blank: (seed) => seed` in
  `MoveDialog` / `RegradeDialog` / `EditTicketDialog` / `LabourPanel`
  (S018 4-code-review-r1); `watch(nodeId, …, { immediate: true })` moved
  below the refs in 6c58b7a.
- **The user's answers**: Q1 in § 3 (`CLAUDE.md` bullet, coder and
  code-reviewer "whenever the frontend or an API the screens use changed"),
  § 7.6, Out of scope; Q4 "IT Admin" in § 1.6, § 9 and the Review log. The
  `/smtw-review` part is BR2-01.
- **Standards** (§ 2) unchanged from round 1 and still right: ISO 9001
  § 8.3.4 (design verification with records — a named, repeatable test is
  the record), ISO 27001 A.8.29 / A.8.31 (test environment separated from
  dev and production — own DB, data folder, ports, a dev-mode-only door),
  Cohn's test pyramid, ISO 9241-11.
- **Manual checks** (§ 8): the two important ones are the right two (the
  first green run on the user's machine; the IT admin reading the checklist);
  nothing plain is marked important.
- **Track full** still right (new dev dependency, auth-adjacent harness, a
  new database, workflow rule change).
