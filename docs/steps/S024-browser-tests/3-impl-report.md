```
Step: S024 — Browser tests (Playwright)
Doc: impl-report
Author: Coder (Opus)
Date: 21-10-2026
```

# S024 — Implementation report

Built on 28d3be3 (S018 committed as ae3841f). While I worked, other files changed in
the working tree that are not S024's and that I did not touch:
`.claude/SMTW-WebApp-Base.md`, `.claude/skills/smtw-review/SKILL.md`,
`tooling/common/material_icon.py`, `tooling/common/sync_common.py`,
`docs/review/2026-10-21-smtw-review.md` (the user's smtw-common sync and review).

## Questions for the user

All four answered. KLA, 21-10-2026: "yes to all three" (Questions 1–3 → A2 approved) and
A1 approved (Question 4). The original questions are kept in the brief's amendments A1
and A2; what was done is in "Amendments A1 and A2" below. The marks they described
(`test.fail`, `test.fixme`, the WebKit branch of `expectFieldMessage`) are gone.

## 1. What was built

- **An e2e stack started by one command**, `tooling/run-e2e-tests.bat`: it checks the
  dev DB container, creates `vel_yantra_e2e` and its grant if missing, installs Chromium
  and WebKit (a no-op when present), runs Playwright and prints the start and finish
  time and where the report is.
- **A backend for the browser** (`tooling/e2e/e2e_backend.py`) on `127.0.0.1:5002`
  against `vel_yantra_e2e`, dropped and rebuilt at every run, with its own data folder
  (`scratch/e2e-data/`, emptied at every run). Who the user is comes from the existing
  test headers; a request that lost them gets no access, never admin.
- **Vite on 5177** proxying `/api` to it, so the dev servers on 5001/5176 keep running.
- **A seed** (`tooling/e2e/seed_e2e.py`) loaded through the API: sites SMTW and BRICKS
  with their units, classes, trades, manufacturers and models from the dev seed; the
  nine people of brief § 5.2 with their real memberships; four machines (one with a
  gearbox, one scrapped).
- **Three browser set-ups** every run: Pixel 7 (Chromium), iPhone 14 (WebKit), desktop
  Chromium 1366 × 768.
- **The tests** (45 per set-up, 135 per run), in `frontend/e2e/`:
  - `screens.spec.js`: every route of `router/index.js` for each role that can reach
    it (heading, content, no console error); a header-less browser lands on "no access
    yet" with no permissions;
  - `tickets-raise.spec.js`: S017 raise paths, photo step, unit limits, back-dating,
    a person without a login; S018 A1 *Already fixed* with and without a start time;
  - `tickets-work.spec.js`: S018's technician, supervisor, engineer, raise-again,
    send back, *Machine stopped*, not a fault, assign / edit / change severity;
  - `masters.spec.js`: S016 failure codes;
  - `equipment.spec.js`: S012 manufacturer and model, S003 add / move / status, S006
    document upload and title;
  - `asset-list.spec.js`: S015;
  - `labels.spec.js`: S014 sheets, list ticks, `/e/<code>`.
  - Every dialog a flow opens is checked with `expectDialogFits` (Save and Cancel inside
    the screen, the dialog no taller than it).
  - Screenshots and a trace on failure, an HTML report, under `scratch/e2e-report/`.
- **The workflow change**: README § Manual checks and § Gates 4, the `/step` skill and
  the three agents now split checks into *Automated* and *On a real device*, with
  `[auto]` lines, the named person (today IT Admin), the round trip and
  `docs/steps/device-checks.md`.
- **`docs/steps/device-checks.md`**: the after-deploy section (Keycloak login, QR label
  on mobile data with Android and iPhone) and seven open rows for S014, S015, S017 and
  S018.
- **`.claude/CLAUDE.md`**: a bullet on the e2e stack, and the section
  `## Additional review points (smtw-review)` with the browser-test point.
- **S014–S018's own reports** carry their `[auto]` lines and their device rows (written
  from the passing runs below).

## 2. How it works

- **Start-up.** Playwright's `webServer` starts the backend launcher and Vite, never
  reusing a running one. The launcher, in order: puts `backend/` on the path; sets
  `FLASK_DEBUG=1`, `DEV_AUTH_BYPASS=1` and an absolute `DATA_DIR` before `import config`
  (config refuses the bypass without debug); sets `DB_CONFIG["database"] =
  "vel_yantra_e2e"` and `DEV_STUB_ROLE = "nobody"`; checks the guard
  (`check_target`: host `localhost`/`127.0.0.1`, name ending in `_e2e`) on what is now
  set; drops and creates the database on a plain `pymysql` connection with none
  selected (utf8mb4, utf8mb4_unicode_ci); empties the data folder; only then
  `import app` (which runs the migrations); sets `TESTING` and a `TEST_USER_FACTORY`;
  and runs Flask without the reloader (a reloader would re-run the drop in a child).
  Its log goes to `scratch/e2e-backend.log`. Then `globalSetup` runs the seed.
- **Identity.** `asPerson(page, "technician")` sets the browser context's headers to
  `X-Test-Role: maintenance_team`, `X-Test-User: e2e_technician` (IT admin:
  `X-Test-Role: it_admin`), opens the page, and checks that `/api/auth/me` answered with
  `e2e_technician` and that the top bar shows the person's name. The factory builds the
  user with `harness_user` (now in `backend/tests/harness.py`, shared with pytest), the
  name from the seed and memberships read from the database, as in production. A
  request without the headers falls to the dev stub, which is "nobody".
- **The console.** An automatic fixture (`support/test.js`) attaches `watchConsole` to
  every test's page and fails the test at its end on any `console.error`, any `[Vue
  warn]` warning or any uncaught page error. Only the auth store's bypass line and
  Vite's `[vite]` lines are allowed; a test that expects a refused request names it
  (`allowFailedRequest(url part, status)`).
- **Test data.** Each test makes the tickets it works on (through the API as the right
  person, then works them on the screens). The three set-ups share one database, so
  names a test creates carry the set-up's name; asserted counts are either about rows
  no other test adds (General modes: 14) or computed from the page (the asset list's
  count line against its rows).
- **Times.** Typed times are whole minutes in IST (`istLocal`), so response, repair and
  downtime come out exact: e.g. raised 120 min ago, acknowledged at −100, started at −90,
  back in service at −30 → 20 min, 1 h, 1 h 30 min.

## 3. Files touched

Frontend:
- `frontend/package.json`, `package-lock.json`: dev dependency `@playwright/test`
  1.64.1 (pinned), via `npx npm@11 install`.
- `frontend/vite.config.js`: proxy target from `YANTRA_API_URL` (default unchanged);
  Vitest excludes `e2e/**`.
- `frontend/playwright.config.js` (new): projects, `workers: 1`, the two web servers,
  global setup, report and outputs under `scratch/e2e-report/`, IST time zone.
- `frontend/e2e/setup/global-setup.js` (new): runs the seed.
- `frontend/e2e/support/stack.js` (new): the two addresses.
- `frontend/e2e/support/people.js` (new): `asPerson`, `headersFor`, `apiAs`, `seedIds`,
  `personId`.
- `frontend/e2e/support/console.js` (new): `watchConsole`.
- `frontend/e2e/support/test.js` (new): the `test` with the console fixture.
- `frontend/e2e/support/dialogs.js` (new): `expectDialogFits`, `expectNoSidewaysScroll`,
  `expectFieldMessage`.
- `frontend/e2e/support/tickets.js` (new): ticket helpers (times, API setup, dialogs,
  cards).
- `frontend/e2e/*.spec.js` (7 new) and `frontend/e2e/fixtures/test-photo.jpg`,
  `test-manual.pdf` (new; a 160 × 120 JPEG and a one-page PDF).

Backend:
- `backend/tests/harness.py` (new): `harness_user(role, username, name=None)`.
- `backend/tests/conftest.py`: imports it; the definition and three imports removed.
- `backend/tests/test_access_control_api.py`: `test_test_headers_outside_testing_are_401`.
- `backend/tests/test_e2e_launcher.py` (new): the guard's tests.

Tooling:
- `tooling/e2e/e2e_backend.py`, `tooling/e2e/seed_e2e.py` (new).
- `tooling/run-e2e-tests.bat` (new).
- `tooling/dev/seed_dev.py`: `call(..., *, base_url, headers=None)`; `BASE_URL` read in
  `main()`; the loops of `main()` moved into `create_masters`, `create_people`,
  `create_equipment` (shared with the e2e seed); `dev-seed.bat` behaves as before.
- `tooling/dev/init-test-db.sql`: also creates and grants `vel_yantra_e2e`.
- `sbom/frontend.cdx.json`: regenerated by `tooling/run-deps-audit.bat`.

Docs and workflow:
- `docs/steps/README.md`: § Manual checks rewritten; § Gates 4; S024's index row.
- `docs/steps/device-checks.md` (new).
- `.claude/skills/step/SKILL.md`: the brief's two kinds of check; gate B; the `Done` rule.
- `.claude/agents/coder.md`, `code-reviewer.md`, `brief-reviewer.md`: the new rules.
- `.claude/CLAUDE.md`: the e2e bullet and the review-points section.
- `docs/steps/S024-browser-tests/1-brief.md`: status only.
- `docs/steps/S014…S018/3-impl-report.md`: a "Browser tests (S024)" block under each
  `## Manual checks`.

## 4. Decisions taken

1. **One context per test, person switched by headers** (departure from § 3's "one
   browser context per seed person"). `asPerson(page, key)` sets the headers on the
   test's own context (`setExtraHTTPHeaders`) and reloads; calling it again switches
   person. A separately made `browser.newContext()` would not get the project's phone
   emulation, nor Playwright's trace and screenshot on failure. Same isolation in
   effect: one person at a time, checked each time.
2. **Equipment looked up by name, not code.** Codes are generated (S002), so the seed's
   machines are named (`E2E extruder`, …) and `seedIds()` returns `{id, code, …}` by
   name, through the API as admin.
3. **No Team record for IT admin.** She holds a token role, not a site role; the seed
   gives her none. That is also what lets a test show "Nobody will be assigned".
4. **`seed_dev.py` helpers.** The brief asked only for `call()` and the shared lists;
   the e2e seed needed the same create loops, so they moved into three functions rather
   than being copied.
5. **The guard's test lives in `backend/tests/test_e2e_launcher.py`**, importing the
   launcher from `tooling/e2e/` (its `main()` is guarded, so importing it starts
   nothing). It runs in `run-backend-tests.bat`.
6. **Seed run with `uv run --project ../backend python`**, the same interpreter as the
   backend.
7. **The raise screen is a page, not a dialog**, so `expectDialogFits` does not apply;
   its phone check is `expectNoSidewaysScroll` plus Save in view.
8. **`expectNoSidewaysScroll` measures against the viewport Playwright set**, not
   `clientWidth`: Playwright's WebKit on Windows scales its window by the display
   scaling (125 % gives 312 px for a 390 px iPhone), which made every page look 79 px too
   wide.
9. **Known faults marked, not hidden** (Questions 1–3): `test.fail` where the failure is
   steady (it turns red the day the fault is fixed, as a reminder to un-mark it),
   `test.fixme` where it is a race.
10. **IST in the browser** (`timezoneId: "Asia/Kolkata"`, `locale: "en-IN"`), as the
    plant's phones, since the server reads typed times as IST.
11. **Extra plain checks automated** where they cost one or two lines: back-dating,
    the open-ticket warning, *Recording as* / *Nobody will be assigned*, remove-labour
    asks first, the asset list's `@page` rule removed after leaving.

## 5. Not done, deferred, assumed

- The re-introduced-bug demonstration ran on the affected specs, not the whole suite
  (§ 8 below).
- Not automated (stay plain checks in their reports): S014 "tick across two pages …
  changing the filter clears the ticks" and "a long name is cut with …"; S017 "scrap
  with an open ticket", "remove a ticket photo; Settings › Removed documents"; S015
  "Printed by shows the name on production".
- S015's "a press shows its component-units *and components*": the seed has a machine
  with a component unit (depth 1) only, no component below it (depth 2).
- The TEST machine's code is a blank in `device-checks.md` until KLA creates it.
- The device rows give the dev server as `http://<KLA's laptop>:5176` and production as
  "ask KLA": I do not know either address.

## 6. Tests

- **Current state (after the gate B minors, 21-10-2026):** `tooling/run-e2e-tests.bat` **135 passed**
  (45 per set-up), 0 skipped, 0 failed. The older runs below are kept as history.
- `tooling/run-tests.bat`: backend **1835 passed** (168 s; including the 12 new guard
  cases and the 401 test), frontend vitest **93 passed** (12 files; `e2e/` not picked
  up), dependency-audit tests **42 passed**.
- `npx vite build`: built, only the existing chunk-size warning.
- `tooling/run-deps-audit.bat`: **exit 1**, from pillow 12.3.0 in the backend (7 high,
  2 moderate, fixed in 13.0.0) — not from this step; nothing reported for
  `@playwright/test`. `sbom/frontend.cdx.json` regenerated.
- **After A1/A2**: `tooling/run-tests.bat` backend 1835 passed, vitest 93 passed, deps
  tests 42 passed; `npx vite build` built. E2E: **117 passed, 0 skipped, 0 expected
  failures** on all three set-ups, 7.9 min (12:09–12:17). Superseded below by that run:
- **E2E, three set-ups (before A1/A2)** (`tooling/run-e2e-tests.bat`):
  - first run: 114 passed, 3 skipped (the fixme), **4.5 min** (07:15:03–07:19:34);
  - after the last code change, **twice in a row**: 114 passed, 3 skipped, exit 0, 4.5 min
    each (07:39:14–07:43:49 and 07:43:52–07:48:28; the database and data folder rebuilt
    each time);
  - "passed" counts the expected failures (4 per run: the WebKit message on 1 set-up,
    the label menu on 3); "skipped" is the Add equipment race on 3.
- **The suite catches the faults it is for** (each re-introduced, run, then reverted with
  `git checkout -- <file>`; `git status` showed `frontend/src` clean after each):
  - S017's watcher order (the `watch(nodeId, …, { immediate: true })` moved above
    `const form`) in `RaiseTicketView.vue`; `screens` + `tickets-raise`, three
    set-ups: **39 failed**, 9 passed, every failure with
    `uncaught error: Cannot access 'form' before initialization`;
  - S018 CR1-01's `blank: (seed) => seed` in `RegradeDialog.vue`; `screens` +
    `tickets-work`, desktop: **14 failed**, 2 passed, with
    `uncaught error: Cannot read properties of undefined (reading 'intensity')` and
    `[Vue warn]: Unhandled error during execution of render function`.
- **A lost header is refused**: `screens.spec.js` › "a request that lost its test
  headers gets no access, never admin" (empty permissions and roles, the "no access yet"
  page), in every run.

## Manual checks

Important:
- [ ] The user runs `tooling/run-e2e-tests.bat` once on their own machine: it creates
  the database, installs the browsers, goes green, and the report opens
  (`scratch/e2e-report/html/index.html`).
- [ ] IT Admin reads `docs/steps/device-checks.md` and says whether she could follow
  each row without help.

## Fix rounds

### Round 1

Only CR1-01 was asked for in this round. CR1-02 to CR1-07 were not touched.

- **CR1-01: Fixed.** `frontend/e2e/masters.spec.js` has two new tests, one for Causes and
  one for Actions: "engineer: a causes entry is added and edited" and "engineer: a actions
  entry is added and edited". Each test:
  1. opens *Add cause* / *Add action* and calls `expectDialogFits`;
  2. fills in a code and a label, and saves;
  3. opens that row's *Edit*, calls `expectDialogFits` again, changes the label, saves, and
     checks the row shows the new label.

  The code and label carry the project's suffix, as the mode test does, because the three
  set-ups share one database. For a cause the test also picks a cause group: the list
  is not filtered, so no group is pre-picked and the server refuses the save with 400
  (my first run failed on this on all three set-ups, and I added the group choice).
- **Tests after the fix:**
  - `tooling/run-tests.bat`: backend **1835 passed** (255 s), vitest **93 passed**, deps
    tests **42 passed**. No production code changed in this round.
  - `tooling/run-e2e-tests.bat`: **123 passed**, 0 skipped, 0 failed, 4.6 min, exit 0
    (117 before, plus 6 new: 2 tests on 3 set-ups).
  - In the run before the group choice was added, one other test also failed once:
    "not a fault: the remark is open and required..." on desktop Chromium (the suggested
    cause showed "—" instead of "5.1 ..."). It passed in the final run on all three
    set-ups. I did not find the cause; it may be a timing flake or an effect of the
    failed cause test, which had left a dialog open. I flag it as unexplained.

## Fix round — gate B minors

KLA asked (21-10-2026) for five open findings. CR1-05, CR1-06 and CR1-07 stay open by KLA's
choice. No production code changed.

- **CR1-02: Fixed.** The "Browser tests (S024)" blocks of S014, S015, S016, S017 and S018
  now cite the current run (135 passed, 0 skipped, 0 failed). S014 lists "the equipment page
  prints a node with its parts" as an `[auto]` line. The WebKit caveats are gone from S016,
  S017 and S018.
- **CR1-03: Fixed.** `docs/steps/device-checks.md` has row 8 (S016, S017, S018): on an
  iPhone, a refused Save on Raise ticket and on *Not a fault* shows its message beside the
  field. *Done* is empty.
- **CR1-04: Fixed.** `frontend/e2e/masters.spec.js` has four new tests, each run on the
  three set-ups: Units (as IT admin, who holds `masters:edit`), Equip Class, Equip Type and
  Trades (as engineer). Each one opens the section and checks that its table has a row. It
  opens the Add dialog and calls `expectDialogFits`. It saves the dialog empty and checks
  that the server's refusal shows beside a field (the text "Name is required" for Trades; any
  field message for the other three, as the first refused field is not the point of the test).
  The 400 response is allowed with `allowFailedRequest`.
- **CR2-01: Fixed.** The two tests now read "engineer: a cause is added and edited" and
  "engineer: an action is added and edited" (each kind carries its noun with the article).
- **CR2-02: Fixed.** § 1 says "45 per set-up, 135 per run"; § 6 starts with the current
  count.

- **Tests:**
  - `tooling/run-tests.bat`: exit 0. Backend **1835 passed** (238 s), vitest **93 passed**
    (12 files), deps tests **42 passed**.
  - `tooling/run-e2e-tests.bat` (full, in the background): **135 passed**, 0 skipped, 0
    failed, 0 flaky, 5.1 min, exit 0 (123 before, plus 12 new: 4 tests on 3 set-ups).
  - `npx vite build` not run: nothing under `frontend/src` changed.
  - After the CR2-01 rename, `masters` alone: 30 passed in three runs out of four. In the first
    of the four, 29 passed and one test was listed as flaky ("engineer: the pre-filled lists
    are there; a press mode is added…", iPhone 14 WebKit; it passed on retry). I did not
    find the cause. It did not come back in the next three runs.

## Amendments A1 and A2 (approved 21-10-2026 by KLA)

### A1 — `## SMTW-Review` in `.claude/CLAUDE.md`

The section `## Additional review points (smtw-review)` is replaced by `## SMTW-Review`.
It keeps the earlier browser-test text (command, background run, spec-to-step map,
marked tests) inside its *Browser tests* point, now saying the audit may run the suite
when it helps and not on every audit. New points: *Steps* (status against impl report;
list committed steps not `Done`), *Device checks* (open rows of
`docs/steps/device-checks.md`), *Previous audit* (status of each finding of the latest
`docs/review/*-smtw-review.md`), and *How this section grows*. The section is last in
the file, as the earlier one was.

### A2 — three screen faults fixed

1. **Field messages (WebKit).** 58 messages in 21 files were `<div class="invalid-feedback">{{ x }}</div>`
   (the sibling rule); each is now `<div v-if="x" class="invalid-feedback d-block">{{ x }}</div>`
   (inner quotes single in the `v-if`). Files: DocumentTitleModal, DocumentUploadModal,
   EquipmentFormModal, EquipmentMoveModal, EquipmentStatusModal, the ten Masters panels
   (EquipmentClasses, EquipmentTypes, FailureCauses, FailureModes, MaintenanceActions,
   Manufacturers, Models, People, Sites, Trades, Units), RaiseTicketView, EditTicketDialog,
   EventFields (one was already converted), LabourPanel, MoveDialog. No message uses the
   sibling rule any more (`grep invalid-feedback` finds none without `v-if`). The WebKit
   branch of `expectFieldMessage` and the `test.fail` in `tickets-raise.spec.js` are gone;
   it checks "visible" on every project.
2. **Add equipment's race.** Fixed in `FormModal.vue`, so it covers every caller (all
   dialogs share it): the component tracks `visible` (set in `open()`, cleared on
   Bootstrap's `hidden.bs.modal`). On unmount a dialog that is not visible is disposed
   at once as before; one that is still shown or fading out is closed (`hideNow`) and
   **disposed only on `hidden.bs.modal`** (once). The navigation is untouched.
   `test.fixme` removed from `equipment.spec.js`.
3. **Bootstrap once.** Kept the **ES build** (`import { Modal } from "bootstrap"` in
   FormModal and PhotoViewer, unchanged); `main.js` now does `import "bootstrap"` (which
   registers the data-API, so `data-bs-toggle` dropdowns still work) instead of
   `bootstrap.bundle.min.js`; the second copy is gone. The ES build needs
   `@popperjs/core`, which is bootstrap's **peer dependency, already installed and
   already in `package-lock.json`** (the components' ES import already pulled it in): no
   package added, `package.json` and the lock untouched by this. `test.fail` removed
   from `labels.spec.js`.

Also: the unused `test` import in `e2e/support/dialogs.js` removed.

**Files (A2):** the 21 `.vue` files above, `frontend/src/components/FormModal.vue`,
`frontend/src/main.js`, `frontend/e2e/equipment.spec.js`, `labels.spec.js`,
`tickets-raise.spec.js`, `support/dialogs.js`. **A1:** `.claude/CLAUDE.md`.

**Decisions.** (a) FormModal-side fix chosen over waiting for navigation: one place, all
callers. (b) ES build kept over the UMD bundle: the components import from it and need
no change; popper is already present as the peer. (c) `v-if` on the message also means
an empty message is no longer in the DOM (nothing relied on it; vitest and e2e green).

**Not done / to verify.** The race was intermittent: the Add equipment test passed in
this run (all three set-ups) but one pass is not proof; a second run is cheap. The
real-iPhone field-message row in `device-checks.md` stays (Playwright's WebKit is not
Safari).
