```
Step: S080 — Contract register
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 30-10-2026
```

# S080 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** The step builds what the brief and its staleness
answers ask. There is one `minor` finding (an empty-state text that can be false) and two nits.

Read in full: `backend/contracts.py`, `backend/contracts_core.py`, `ContractsPanel.vue`,
`contractLabels.js`, `contracts.spec.js`, `test_contracts_api.py`; the hunks of `local_db.py`,
`config_rbac.py`, `masters.py`, `masters_core.py`, `equipment.py`, `app.py`, `conftest.py`,
`test_rbac.py`, `MastersView.vue`, `docs/Plan.MD`, `.claude/CLAUDE.md`, `docs/schema/notes.json`;
the test lists of `test_contracts_core.py`, `test_migration_v43.py` and `contractLabels.test.js`; the
helpers they call (`masters_core._validate`, `_collapsed`, `api_common.clean_body`, `enum_arg`,
`int_arg`, `auth_utils.require_perm_at`, `useMasterForm.js`, the vendors store).

## Tests run by the reviewer

- **All unit suites** (`YANTRA_TEST_RUN=s080cr1 tooling\run-tests.bat`): PASSED — backend 4241 passed (205 s), frontend 384 passed, tooling 231 passed.
- **Build** (`npx vite build` in `frontend/`): built, exit 0; only the old chunk-size warning.
- **Schema docs** (`YANTRA_TEST_RUN=s080cr1 tooling\schema-docs.bat check`): exit 0, "Schema docs at migration v43: 4 passed".
- **Browser:** none re-run. No finding of mine needs one. The coder's runs are the right ones: the
  new spec alone (9 passed), the targeted run of § 8.4 (`contracts.spec.js`, `masters.spec.js`,
  `screens.spec.js`: 63 passed, 1 existing skip), and the whole suite at Normal once (328 passed;
  the 2 failures are the known `changelog.spec.js:14` on `desktop-chromium`, outside this step).
  No shared file changed, so no extra WebKit run is due.

## Minor

### CR1-01 (minor) — "No contracts yet." shows when the site has only ended contracts

`frontend/src/views/masters/ContractsPanel.vue:157-158` (with `filtersAtDefault`, `:39-41`).

- **Problem.** In the default view (Status *Not ended*) an empty list shows "No contracts yet. Add
  the first one with *Add contract*." The default view hides ended contracts. So the text is false
  whenever the site has contracts and all of them have ended. The impl report lists the choice
  (§ 4, *The empty state*); the reason is that the API cannot tell "none" from "only ended ones".
  The text is still scope B that states a wrong fact.
- **Failure scenario.** SMTW's three AMCs all ended on 31-03. On 01-04 the manager opens Masters ›
  Contracts. The screen says "No contracts yet. Add the first one with Add contract." and, under it,
  "Ended contracts: choose Ended in Status." The two lines contradict each other. The engineer
  may think the register was lost, or enter the ended contracts again as new ones.
- **Suggested fix.** In the default view, say only what is true: "No contracts in force or
  starting later." (plus the hint "Add one with *Add contract*." for a user with `can_add`). The
  existing line "Ended contracts: choose Ended in Status." already points to the rest. No API change
  is needed.

## Nits

- **CR1-02** (nit) `backend/contracts_core.py:43-50`: `date.fromisoformat` (Python 3.11+) also takes
  `20270331` and ISO week dates such as `2027-W13-3`, so the brief's "`YYYY-MM-DD` only" (§ 5.1, A6)
  is wider in code than in the report's assumption (§ 5, which names only the compact form); add a
  10-character check in `_date_parser`, or name both forms in the report.
- **CR1-03** (nit) `frontend/src/views/masters/ContractsPanel.vue:73`: five filters each start a
  `reload`, and an earlier, slower answer can land after a later one and show the wrong filter's rows;
  keep a request counter and drop an answer that is not the latest.

## Checked and found consistent

- **Migration v43** (`backend/local_db.py`): the brief's § 4.1 table word for word, appended after
  v42; one statement, `CREATE TABLE IF NOT EXISTS`; no `_PRECONDITIONS` entry is needed (a new
  table). `test_migration_v43.py` covers § 8.1: fresh database, a v42 database with a site and a
  vendor, each CHECK refused (4025) and its boundaries passing, the unknown vendor (1452), the
  repeated contract number, the re-run.
- **Schema docs:** `notes.json` has the `contracts` line in area *Equipment* with the reason
  (BS1-05) and the area note; `schema.json` and `schema-data.js` are regenerated; the check exits 0
  at v43 (above).
- **Validation (§ 5.1)** in the pure core: every required field absent on a `POST` gets its own
  "Enter …" / "Choose …" text through the `None` default; nothing required on a `PUT`; `active`
  dropped on a `POST`; `renewal_of_id` ignored; the parsers reused through the four public aliases
  and S079's `phone_parser` (D9, D11). The vendor id's long text for a missing or malformed id and
  S079's two texts through `masters.check_active_vendor` for an unknown or inactive one follow
  BS1-01; the report states the choice (§ 4).
- **Merged rules on a `PUT`:** the period with the message beside the date that was sent; the calls
  number refused with the merged tick off; the tick off with no number clears the stored number
  (in the core, so the CHECK never trips); the site kept (`SITE_KEPT`), the same site no change; the
  vendor checked only when it changes, so a contract with an inactive vendor still saves.
- **Status (§ 5.3):** `contract_status` and `status_bounds` agree kind for kind; the inclusive
  period; the 60-day window; the order ascending, descending for `ended`; the bounds are code
  constants and the dates are SQL parameters. No SQL is built from client text.
- **Access (§ 5.4, § 5.5):** four keys with the brief's holders, all in `SITE_SCOPED`;
  `test_role_matrix` and the new `test_contract_keys` match. Every route has `require_perm`; the list
  holds only the sites of `_sites_holding(cur, "contract:read_basic")` and an unheld `site_id` gives
  an empty list; the detail and the `PUT` answer 404 outside the reader's sites and 403 naming the
  site for a reader without `contract:edit`; the `POST` takes `require_perm_at` at the body's site.
  The actor comes from `actor()`, never from the body. Every answer goes through `_contract_out`
  (the gated keys absent, not `null`); every write goes through `_drop_gated` at the contract's site
  (the body's site on a `POST`, the locked row's on a `PUT`). The tests prove the engineer's `PUT`
  keeps the manager's cost note and IT admin's `PUT` keeps the call-out number.
- **Locks (§ 5.6):** create: site `LOCK IN SHARE MODE`, the access check, the vendor `LOCK IN SHARE
  MODE` (S079's helper), the insert; change: the contract `FOR UPDATE` first, plain access checks,
  the vendor shared only when it changes. The LOCK ORDER note in `contracts.py` and the bullet in
  `equipment.py` match the code. No lock cycle with S079's vendor and person writes.
- **Database down:** every route reaches `get_db()`; `TestDatabaseDown` proves 503 for the list and
  the create.
- **Pure core, thin shell:** the rules (fields, period, calls, status, filter bounds, the gated-field
  map) live in `contracts_core.py`; the routes only check access, lock, read and store. The frontend
  only labels and shapes the body (`contractBody`); no business rule in the Vue file.
- **Reuse:** `_iso_date` is the stated copy of D9; nothing else repeats an existing helper.
  `check_active_vendor` is S079's helper made public, as BS1-01 asked.
- **The screen (§ 5.7):** the *Contracts* section last, after *Team*, with `contract:read_basic`;
  the filters; the table with the phone line "type · vendor · site code" (BR1-05) and the hidden
  columns below `md`; the badges; the count line, the cap line and the *Ended* hint; the dialog's
  fields in order, the site read-only on edit, the stored inactive vendor first on edit, the gated
  fields shown by the chosen site's flags, *Managers only*, the help texts; `ActiveToggle` with its
  own confirmation; `blank()` preselects the one `can_add` site and takes no seed.
- **Use on the floor:** the dialog is `FormModal` (scrollable body, fixed footer); *Deactivate*
  confirms first and sits apart in the footer; no button ends in a 403 (`can_add`, `can_edit`);
  every backend message the user can see is one short line saying what to do; the list has no fixed
  widths and passes the `@device` no-sideways-scroll test. Masters is an office screen for engineers,
  managers and IT admin, so the `btn-sm` buttons follow the other Masters panels.
- **Tests:** the core, API and migration tests cover § 8.2 and § 8.1, failure modes included. The
  nine e2e tests match § 8.4 and assert what the user sees (the field message, the badge text, the
  row's vendor, the "(inactive)" mark, the hidden columns); each flow test calls `expectDialogFits`
  on the dialogs it opens; only the phone-layout test carries `@device`, as the rule asks. The
  changed first test (vendor picked before the empty save) is listed in the report's § 4.
- **Docs pass:** `docs/Plan.MD` § 3 has the four key rows and the paragraph; `.claude/CLAUDE.md` has
  `contracts.py` in self-check item (2) and the § SMTW-Review point of § 8.6 (naming `_drop_gated`);
  `docs/Keycloak.md`, `example_secrets_app.py` and `device-checks.md` need no change. The report's
  `## Docs updated` lists them all.
- **Scope and track:** nothing beyond the brief; the departures are in the report's § 4. Full
  track, as a migration and new keys require.
- **Manual checks:** the report's `## Manual checks` carries every check of § 8.4 as `[auto]` with its
  test, the four important ones marked; § 8.5 has no real-device check, so no row in
  `docs/steps/device-checks.md`.

## Manual browser checks for the user

None required. The brief has no real-device check (§ 8.5), and every screen check is automated.
Optional, at gate B: open Masters › Contracts as the manager and add a contract with a cost note,
then open it as the engineer and see no cost note.

## Feedback

- hindrance: `git diff refs/steps/S079` as the orchestrator named it lists S080's new untracked files
  as deleted S079 files (the stat showed `VendorsPanel.vue` and `test_vendors_api.py` as removed);
  the snapshot tool's `diff S080` was the right command (1 extra call)
- waste: the unit run and the schema docs check both rebuild a database; I ran them in parallel to
  save time, and each still took several minutes (about 6 min of waiting)
