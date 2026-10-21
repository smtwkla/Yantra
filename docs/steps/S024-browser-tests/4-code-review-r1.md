```
Step: S024 — Browser tests (Playwright)
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 21-10-2026
```

# S024 — Code review, round 1

**Verdict: one `major` finding is open (CR1-01). No blocker. Every suite is green: the unit tests, the build, and the browser tests twice in a row.**

Scope: the whole uncommitted S024 implementation against `1-brief.md`, with the approved
amendments A1 (`## SMTW-Review` in CLAUDE.md) and A2 (three screen faults fixed), and
`3-impl-report.md`. I read the diff with `git diff -w --ignore-cr-at-eol` and read the new
files in full. Some other changes in the working tree belong to the planner or to the
user's sync, not to S024. These are the README index rows for S010–S014 and S019–S025, the
status lines of the S010–S014 briefs, `docs/Plan.MD`, `.claude/SMTW-WebApp-Base.md`,
`.claude/skills/smtw-review/SKILL.md` and `tooling/common/*`. I did not review them.

## Test results (run by me)

| Run | Result |
|---|---|
| `tooling/run-tests.bat` | exit 0. Backend **1835 passed** (230 s), vitest **93 passed** (12 files; `e2e/` not picked up), deps tests **42 passed** |
| `npx vite build` (frontend) | built in 3.6 s, with no new warning. The bundle holds Bootstrap's data-API (`[data-bs-toggle="dropdown"]` handler) and Popper. So in the production build, `import "bootstrap"` is not tree-shaken: bootstrap's `package.json` has no `sideEffects` field |
| `tooling/run-e2e-tests.bat`, run 1 | exit 0. **117 passed**, 0 skipped, 0 flaky, 4.4 min (12:18:57 to 12:23:22) |
| `tooling/run-e2e-tests.bat`, run 2 (straight after) | exit 0. **117 passed**, 0 skipped, 0 flaky, 5.9 min (12:28:04 to 12:34:03) |
| `scratch/e2e-backend.log` (run 2) | no traceback, no 500 |

With the coder's own post-A2 run, A2's Add-equipment fix (S003, "engineer adds equipment
from the list; its page opens") has now passed on all three set-ups in **three runs in a
row**, 9 of 9. No `test.fail`, `test.fixme`, `test.skip` or `.only` is left in
`frontend/e2e/`.

**Popper and `npm ci`** (A2 point 3, as asked):
- The committed lock (HEAD) already has `node_modules/@popperjs/core` 2.11.8 with
  `"peer": true`, as bootstrap 5.3.8's `peerDependencies` (`^2.11.8`). The working-tree
  lock leaves it as it is.
- I ran `npm ci --ignore-scripts` on a copy of `package.json` and `package-lock.json` in a
  scratch folder (npm 10.9.2). It added 108 packages, and `npm ls` shows
  `bootstrap@5.3.8 └── @popperjs/core@2.11.8`.
- `tooling/build/Dockerfile.frontend` runs a plain `npm ci`: no `--legacy-peer-deps`, no
  `--omit=peer`, no `--omit=dev`, and the repo has no `.npmrc`. npm 7 and later install
  peers by default, so the image's build stage gets Popper.
- This is not a new reliance. Before A2, `FormModal` and `PhotoViewer` already imported
  `{ Modal } from "bootstrap"`, which resolves to `bootstrap.esm.js`, which imports
  `@popperjs/core`.
- `vite.config.js` now imports `vitest/config`. `vitest` is a devDependency, and the
  Dockerfile's `npm ci` installs devDependencies, so `npm run build` in the image still
  resolves it.

## Findings

### CR1-01 — `major` — The cause and action dialogs of S016 are never opened or checked to fit, and the report does not say so

- **Where:** `frontend/e2e/masters.spec.js:21-90`; brief § 1.4.
- **Problem:** brief § 1.4 lists the dialogs that `expectDialogFits` must check inside the
  flow tests, including "S016 failure mode / cause / action add and edit".
  `masters.spec.js` opens only the **mode** dialogs: *Add mode* at line 31 and a mode's
  *Edit* at line 64. No test opens *Add cause* (`FailureCausesPanel.vue:75`), *Add
  action* (`MaintenanceActionsPanel.vue:54`) or their edit dialogs. They are only shown as
  rows (lines 42-45 and 82-88).
- **Not reported:** the impl report's "Decisions taken" and "Not done" do not mention this.
  An unreported departure from the brief is at least `major` under the review rules. Its
  practical weight is small.
- **Failure scenario:** A2 rewrote the field messages in both panels: 3 in
  `FailureCausesPanel.vue` and 3 in `MaintenanceActionsPanel.vue`. A typo in one of the
  new `v-if` expressions, or a dialog whose footer slides off a phone, would ship without
  a red test. Both are things the suite was built to catch.
- **Fix:** in `masters.spec.js`, as an engineer on *Causes*, click *Add cause*, call
  `expectDialogFits`, fill in a cause and save it. The label needs the project's suffix,
  as the mode test does. Then open its *Edit* and call `expectDialogFits` again. Do the
  same on *Actions*. This is about 20 lines, written like the mode test. Or, if the
  planner agrees to drop them, record the departure in the report's Decisions.

### CR1-02 — `minor` — The reports of S014, S016, S017 and S018 still show the state before A2

- **Where:**
  - `docs/steps/S014-qr-labels/3-impl-report.md:245, 250`;
  - `docs/steps/S015-asset-list/3-impl-report.md:121`;
  - `docs/steps/S016-failure-codes/3-impl-report.md:181, 186`;
  - `docs/steps/S017-raise-tickets/3-impl-report.md:276, 283`;
  - `docs/steps/S018-work-tickets/3-impl-report.md:326, 336, 712`.
- **Problem:** each "Browser tests (S024)" block was written from the runs before A2. Each
  cites "114 passed, 3 skipped, twice in a row". The S014 block lists "the equipment page
  prints a node with its parts" as **Not passing**, marked expected-to-fail. S016, S017 and
  S018 say the field messages are not drawn on WebKit. Since A2, all of these pass on all
  three set-ups, and the marks are gone (S024 report § A2; confirmed by my two runs).
- **Failure scenario:** at gate B the planner shows these blocks for S014–S018. The user
  then sees a passing S014 check as failing, and the WebKit caveats on checks that now pass
  everywhere. That could hold S014 back from `Done` for no reason, or send IT Admin to
  re-check something already automated.
- **Fix:**
  - point the header line of each block at the post-A2 runs (117 passed, 0 skipped, twice);
  - turn S014 line 250 into an `- [auto] … — S024 e2e/labels.spec.js::the equipment page
    prints a node's label with its parts` line;
  - remove the WebKit caveats from S016:186, S017:283 and S018:336.

### CR1-03 — `minor` — The iPhone field-message device row that A2 "keeps" does not exist

- **Where:** `docs/steps/S024-browser-tests/3-impl-report.md:297-299`;
  `docs/steps/device-checks.md` (rows 1–7, D1–D3); brief A2 *Tests*.
- **Problem:** A2's *Tests* says "The device row for field messages on a real iPhone
  stays". The report repeats that "the real-iPhone field-message row in `device-checks.md`
  stays". No row in `device-checks.md` is about field messages. Rows 6 and 7 are about the
  keyboard over the Close dialog.
- **Failure scenario:** the WebKit fault behind A2 point 1 (a message laid out at 0 × 0)
  was found only in Playwright's WebKit. No one is asked to confirm on a real iPhone that
  a refused Save now shows its message beside the field. That gap is exactly what A2 meant
  to keep covered.
- **Fix:** add a row such as: "S016/S017/S018 — On an **iPhone**: Raise ticket, choose
  *Running, reduced*, leave the description empty, press Save. The red message 'Describe
  the problem, or pick a symptom' shows under the field. Then on a ticket, *Not a fault* →
  Save with no remark → 'Add a remark' shows under the remark. Account: none (dev server).
  Network: company Wi-Fi or home network. Where: dev server." Or change the report and the
  A2 note if the planner decides that no row is needed.

### CR1-04 — `minor` — Four Masters sections are never shown by any browser test

- **Where:** `frontend/e2e/screens.spec.js:56`; brief § 1.4 and § 1 *Out of scope*.
- **Problem:** "every screen opens" visits `/masters` and checks its *Sites* button.
  Masters is one route with nine sections (`MastersView.vue:22-32`), and only the active
  one is rendered. In the whole suite:
  - *Sites* is rendered by default;
  - *Team* by `tickets-raise.spec.js`;
  - *Manufacturers* and *Models* by `equipment.spec.js`;
  - *Failure codes* by `masters.spec.js`.

  **Units, Equip Class, Equip Type and Trades are never rendered**, yet the brief's *Out of
  scope* says the S010–S013 admin screens are "covered by every screen opens". A2 also
  edited the field messages in all four of those panels.
- **Failure scenario:** a render error in `UnitsPanel.vue` (say, a wrong name in one of
  the new `v-if` expressions that throws on render) gives a blank Units section and a
  console error. The suite stays green. This is the S017 "blank screen" kind of fault the
  suite exists to catch.
- **Fix:** in the `/masters` entry of `screens.spec.js` (or one more step after it), click
  every visible button of the Masters toolbar in turn and assert that its panel shows
  (e.g. its table or its *Add* button for roles that have one). The console fixture
  already fails the test on any error.

### CR1-05 — `minor` — `PhotoViewer` still disposes its modal while it is shown

- **Where:** `frontend/src/components/documents/PhotoViewer.vue:91-93`.
- **Problem:** A2 fixed the dispose-mid-animation race in `FormModal` only, as A2 asked:
  "every caller" of FormModal. `PhotoViewer`, the other Bootstrap modal (and one A2's
  *Where* names), still calls `modal?.dispose()` at once on unmount.
- **Failure scenario** (likely, not reproduced): a technician opens a ticket photo and
  presses Android's **Back**, a natural way to "close" a full-screen photo. The router
  leaves the ticket page and `PhotoViewer` unmounts while shown. Bootstrap's `dispose()`
  removes the backdrop but not `body.modal-open` and its padding. The next page then
  cannot scroll until a reload. If Back comes during the fade, it is the same "reading
  'style'" error A2 fixed in FormModal.
- **Fix:** the same unmount rule as FormModal (hide, then dispose on `hidden.bs.modal`).
  Ideally it should be one small shared helper that both components call, rather than a
  second copy. Pre-existing and outside S024's approved scope, so `Deferred` to a step
  (or S025) is an acceptable answer. A device row "Android Back with a photo open" would
  confirm it.

### CR1-06 — `nit` — FormModal: an unmount during the *opening* animation still leaves the backdrop

- **Where:** `frontend/src/components/FormModal.vue:100-118`.
- **Problem:** if the component unmounts within about 300 ms of `open()`, while Bootstrap
  is still showing the dialog, `hideNow()` calls `modal.hide()`. Bootstrap ignores a hide
  while `_isTransitioning`. So `hidden.bs.modal` never fires, the instance is never
  disposed, and the backdrop and `body.modal-open` stay on the next page.
- **Not a regression:** before A2 this case broke too (a dispose during the show
  callback). A person would have to open a dialog and press Back within a fraction of a
  second.
- **Fix (optional):** if `visible` but not yet shown, listen for `shown.bs.modal` once and
  hide then. Or note it in the comment.

### CR1-07 — `nit` — `_empty_data_dir` hides the reason when the data folder cannot be removed

- **Where:** `tooling/e2e/e2e_backend.py:62-64`.
- **Problem:** `shutil.rmtree(DATA_DIR, ignore_errors=True)` is followed by
  `os.makedirs(DATA_DIR)`.
- **Failure scenario:** on Windows, a file still held open (say, by a backend left over
  from an aborted run) makes `rmtree` fail silently. `makedirs` then raises
  `FileExistsError`, which says nothing about the locked file. The run fails at start-up
  with a misleading line in `scratch/e2e-backend.log`.
- **Fix:** `if os.path.exists(DATA_DIR): shutil.rmtree(DATA_DIR)` (no `ignore_errors`),
  then `os.makedirs(DATA_DIR)`. The real error, naming the file, then reaches the log.
  This also follows "never silently swallow exceptions".

## Earlier rounds

None. This is round 1.

## Manual checks

- The impl report's `## Manual checks` carries both **important** checks of brief § 8 as
  unticked boxes: the user's own e2e run, and IT Admin reading `device-checks.md`.
- `device-checks.md` carries the brief's real-device split:
  - S014: 52 mm, the greased label, and the Android and iPhone scans (D2, D3);
  - S015: the two paper checks;
  - S017: a camera photo;
  - S018: the keyboard over Close, on Android and on iPhone;
  - the Keycloak login (D1).

  Each row has its account, network and where.
- **Missing:** the iPhone field-message row (CR1-03).

Still for the user's or IT Admin's **manual check**:
- [ ] The user runs `tooling/run-e2e-tests.bat` once on their own machine and opens
  `scratch/e2e-report/html/index.html`.
- [ ] IT Admin reads `docs/steps/device-checks.md` and says whether each row can be
  followed without help.
- After this step: the rows of `device-checks.md` (D1–D3, 1–7, and the row CR1-03 adds).
- In the browser, once: on the equipment page, *Print label* opens its menu on one click
  and *This node and all its parts* opens the labels tab. This one is automated; the
  manual click is worth doing because A2 changed how Bootstrap is loaded app-wide. Do it
  on the **built** app (production or `vite preview`), since the e2e runs use the Vite dev
  server.

## Checked and found consistent

- **Brief § 1.1 / § 3, the stack.**
  - Order of start-up in the launcher (`e2e_backend.py`):
    1. `FLASK_DEBUG`, `DEV_AUTH_BYPASS` and `DATA_DIR` are set before `import config`;
    2. `DB_CONFIG["database"]` and `DEV_STUB_ROLE = "nobody"` are set, then the guard runs
       on what is now set;
    3. drop and create run on a plain `pymysql` connection with no database selected,
       utf8mb4 / utf8mb4_unicode_ci;
    4. then `import app`, `TESTING` and the factory;
    5. `use_reloader=False`, bound to `127.0.0.1`.
  - `config.DB_CONFIG` is read only when the pool opens, during `import app`, so the
    override takes effect.
  - `DEV_STUB_ROLE` is read lazily (`auth_utils.py:195`).
  - The DDL holds only the guarded constant name; no request data reaches it.
- **Playwright config:** `workers: 1`, `reuseExistingServer: false`, `--strictPort`,
  `YANTRA_API_URL` → `127.0.0.1:5002`, report, traces and screenshots under
  `scratch/e2e-report/`.
- **Vite:** the proxy default for dev is unchanged; Vitest excludes `e2e/**`.
- **The bat** checks the container, creates the database and its grant as root through
  the compose file, runs `playwright install chromium webkit` on every run, and exits with
  Playwright's exit code.
- **`init-test-db.sql`** creates `vel_yantra_e2e` and its grant for a fresh container.
- **§ 5.1, the identity header stays a test-only door.**
  - `harness_user` moved to `backend/tests/harness.py` with no pytest import, and
    `conftest.py` behaves the same.
  - `backend/tests/` stays out of the image (`.dockerignore`).
  - The new `test_test_headers_outside_testing_are_401` proves that a header-only request
    with `TESTING` off is 401.
  - The guard's pytest cases (`test_e2e_launcher.py`) refuse `vel_yantra_test`,
    `vel_yantra_master`, `_e2e_old`, an empty or `None` name, and a remote, empty or
    `None` host.
  - A header-less browser lands on "You have no access yet" with empty permissions and
    roles (`screens.spec.js:75`).
  - `asPerson` checks `/api/auth/me` and the top bar before going on.
  - The factory defaults the username to `e2e_<role>` (BR2-02).
  - No production code path changed in the backend.
- **§ 5.2, the seed.**
  - The nine people with their real site roles and units, including Ramesh with no login,
    and IT Admin as a token role with no Team record (Decision 3).
  - The four machines, with the gearbox and the scrapped one.
  - The seed refuses a non-admin identity and a non-empty database.
  - The `seed_dev.py` refactor keeps `dev-seed.bat`'s behaviour. `BASE_URL` moved into
    `main()`. The three `create_*` helpers are shared rather than copied (Decision 4,
    reported).
- **§ 5.3, the console.** It is an automatic fixture on every test. The allow-list is
  exactly the auth-bypass line and `[vite]`. Refused requests are allowed only by URL and
  status (`allowFailedRequest`).
- **§ 5.4 and the automated checks.**
  - Each flow asserts what the user sees: the state badge, timeline lines, exact values in
    the Times card (20 min / 1 h / 1 h 30 min; 20 / 30 / 50 min for A1), field messages,
    "Recording as", "Nobody will be assigned", the read-only ticket after Close, sheet and
    label counts, the asset list's count line against its rows, and the parts' indent.
  - Every S017, S018 and A1 flow of § 1.4 is there.
  - `expectDialogFits` runs on every dialog the flows open: S017/S018 actions through
    `openAction`, labour, assign, edit, the S012 manufacturer and model, the equipment
    add, move and status dialogs, document upload and title, the Team add and edit, and
    the failure mode add and edit. The exception is CR1-01.
- **Decisions taken 1–11** are reported, and none of them changes what the user approved.
  Decision 1 (one context per test, switched by headers) keeps the device emulation and
  the trace, and `asPerson` re-checks identity on each switch.
- **A1.** `.claude/CLAUDE.md` has `## SMTW-Review` with *Browser tests*, *Steps*, *Device
  checks*, *Previous audit* and *How this section grows*, plus the S024 bullet under Yantra
  Specifics. The old "Additional review points" heading is gone.
- **A2 point 1.**
  - `grep invalid-feedback` in `frontend/src` finds 72 messages, all with `v-if`, none on
    the sibling rule. The four I read in full (RaiseTicketView, EquipmentFormModal,
    SitesPanel, EventFields) are converted correctly.
  - A message now shows whenever its error is set, even where the `is-invalid` binding
    differs. That is an improvement, and the report states it as Decision (c).
  - `expectFieldMessage` has no WebKit branch.
- **A2 point 2.** In `FormModal`, a dialog that is visible or closing is disposed only on
  `hidden.bs.modal`. A dialog that is not shown is disposed at once. The listeners are
  removed with it. The comment says why. Green in three runs in a row.
- **A2 point 3.** `main.js` imports `"bootstrap"` (the ES build) once, and the bundle no
  longer holds a second copy. The data-API dropdown works, both in the e2e run and in the
  production bundle. No new dependency (see Popper above).
- **Workflow docs.**
  - `docs/steps/README.md` § Manual checks and § Gates 4 carry the rules: `[auto]`, the
    named person (today IT Admin), the round trip, and `Done`.
  - The `/step` skill (gate B, the brief template, `Done`) and the three agents carry the
    same rules.
  - `.claude/skills/smtw-review/` is not edited by S024 (BR2-01).
- **Dependencies.**
  - `@playwright/test` is pinned at 1.64.1 as a devDependency, and the lock adds only
    `playwright` and `playwright-core`.
  - `sbom/frontend.cdx.json` is regenerated and lists them.
  - The report states that the audit's exit 1 comes from pillow in the backend, not from
    this step.
- **Security.** No route was added or changed. No actor comes from the client outside the
  test-only header path. No SQL is built from request data.
- **Track.** Full, as the brief says.
