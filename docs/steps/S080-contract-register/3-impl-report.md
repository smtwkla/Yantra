```
Step: S080 — Contract register
Doc: impl-report
Author: Coder (Opus)
Date: 30-10-2026
```

# S080 — Contract register: implementation report

The step is built as the brief and its staleness answers say. Unit suites, the build, the schema docs
check, the new spec alone and the targeted browser run are green. The whole browser suite at Normal
failed only in the known `changelog.spec.js:14` test, which is outside this step (§ 6). Departures are small, and all are in § 4: the vendor's id refusal text, the empty-state rule,
and one e2e test that picks the vendor before its empty save.

## 1. What was built

- **A register of vendor contracts.** Migration v43 adds the table `contracts`. It has one site, a
  vendor from `vendors` (S079), a type, a title, the vendor's contract number, From and To, the
  coverage ticks, calls per year, *Covered* / *Not covered*, PM visits per year, response time, *Only
  the vendor may repair*, call-out number, cost note, notes, `renewal_of_id` (always NULL), active,
  and who and when. Foreign keys and CHECKs are the brief's § 4.1, word for word.
- **The API `/api/contracts`**: list (filters site, type, status, vendor, *include_inactive*), detail,
  create, change. A contract is never deleted; `active` false hides it from the default list.
- **The status from the dates**, never stored: *Starts on DD-MM-YYYY*, *In force*, *Ends in N days*
  (60-day window), *Ends today*, *Ended*.
- **Four site-scoped keys**: `contract:read_basic` (every role), `contract:read` (engineer, so
  manager), `contract:read_senior` (manager), `contract:edit` (engineer, so manager, and IT admin).
- **The gated fields.** The call-out number reaches only holders of `contract:read` at the contract's
  site, and the cost note only holders of `contract:read_senior`. A reader without the key gets no
  key in the answer (absent, not null). A writer without it has the field ignored, so the stored
  value stays.
- **Masters › Contracts**, the last tab after *Team*: filters, the table, *Add contract*, and one
  dialog with *Deactivate* / *Reactivate*.

## 2. How it works

- **`contracts_core.py` (pure).** `validate_contract(body, creating)` uses masters_core's rules
  through four new public aliases (`collapsed`, `flag_parser`, `validate_fields`, `id_parser`), plus
  `optional_text_parser` and S079's `phone_parser("Call-out number")`. On a POST it drops `active`
  and gives every absent required field `None`. So each field's own parser says "Enter a title.",
  "Choose a site." and so on. Unticking *Breakdown calls* with no number in the body adds
  `breakdown_calls_per_year: None`, which clears a stored number. `period_error`,
  `breakdown_calls_error`, `contract_status`, `status_bounds` (a list of `(column, operator, date)`
  that the shell turns into SQL with the dates as parameters) and `newest_end_first` hold the other
  rules. `_iso_date` is the stated copy of `improvements_core._iso_date`, with the bounds
  2000-01-01 to 2099-12-31 added.
- **`contracts.py` (shell).**
  - *List:* reads the sites where `contract:read_basic` is held (`_sites_holding`). It counts and
    reads the matching rows of those sites, at most `MAX_PER_PAGE`. It answers `{items, total,
    sites}`, and each site carries `can_add`, `can_read_callout` and `can_read_cost`. A `site_id`
    the user does not hold gives an empty list.
  - *Flags:* `_SiteFlags` computes `has_perm_at` once per site in the request.
  - *Answers:* every answer goes through `_contract_out`. It drops `renewal_of_id`, adds the status
    and the flags, and deletes the gated keys the reader may not see.
  - *Create:* takes the site `LOCK IN SHARE MODE` (400 if missing or inactive), then checks
    `contract:edit` at the site (403 naming it), drops the gated fields (`_drop_gated`) and checks
    the period and the calls. Then `masters.check_active_vendor` (share lock, S079's two texts),
    then the insert, then the answer.
  - *Change:* locks the contract row `FOR UPDATE` first (404). It then checks `read_basic` at its
    site (404) and `contract:edit` (403), keeps the site (400 on a different one), drops the gated
    fields and checks the rules on the merged values. The vendor is checked only when it changes.
    Then `update_row` and the answer.
  - *Lock notes:* the LOCK ORDER note in the module docstring is § 5.6's text. `equipment.py` has a
    contracts.py bullet.
- **`masters.py`.** S079's `_check_new_vendor` is now public as `check_active_vendor` (BS1-01). Its
  one caller is renamed with it.
- **Frontend.**
  - `utils/contractLabels.js` holds the labels and `contractBody(form, site)`. That function turns
    empty texts into null, numbers into numbers, sets calls to null without the tick, and sends
    `callout_number` / `cost_note` only when the chosen site's flags allow them.
  - `ContractsPanel.vue` reloads on each filter change. Its `reload` also calls `ensureVendors`,
    with `refresh` on the first load only, because a save's `resetMasters()` empties the shared
    vendor cache.
  - The dialog's call-out number and cost note fields follow the flags of the site in `form.site_id`.
    On edit, a stored inactive vendor is the first option, "(inactive)".

## 3. Files touched

| File | Change |
|---|---|
| `backend/local_db.py` | Migration v43, `contracts` |
| `backend/contracts_core.py` | New: the pure rules |
| `backend/contracts.py` | New: blueprint, access, locks, `_contract_out` |
| `backend/app.py` | Registers `contracts_bp` at `/api/contracts` |
| `backend/config_rbac.py` | Four keys with their comment; all four in `SITE_SCOPED` |
| `backend/equipment.py` | Docstring: the contracts.py LOCK ORDER bullet |
| `backend/masters_core.py` | Four public aliases with a comment |
| `backend/masters.py` | `_check_new_vendor` → `check_active_vendor` (BS1-01), docstring line |
| `backend/tests/test_migration_v43.py` | New (7 tests) |
| `backend/tests/test_contracts_core.py` | New |
| `backend/tests/test_contracts_api.py` | New (33 tests) |
| `backend/tests/test_rbac.py` | Matrix rows, the S080 comment, `test_contract_keys` |
| `backend/tests/conftest.py` | `contracts` first in `_TABLES` |
| `frontend/src/views/masters/ContractsPanel.vue` | New: the tab |
| `frontend/src/views/MastersView.vue` | The *Contracts* section, last |
| `frontend/src/utils/contractLabels.js` | New |
| `frontend/tests/contractLabels.test.js` | New (7 tests) |
| `frontend/e2e/contracts.spec.js` | New (9 tests) |
| `docs/schema/notes.json`, `schema.json`, `schema-data.js` | The contracts line; regenerated |
| `docs/Plan.MD` | § 3: four key rows and one paragraph |
| `.claude/CLAUDE.md` | Self-check item (2): contracts.py's LOCK ORDER note; § SMTW-Review point |
| `docs/steps/S080-contract-register/1-brief.md`, `docs/steps/INDEX.md` | Status (S080's row only) |

## 4. Decisions taken

- **The `vendor_id` refusal text.** BS1-01 asks for both the parser `id_parser("Vendor")` and the long
  text "Choose a vendor. The list holds the active vendors of Masters › Vendors." for a missing
  vendor. `_parse_vendor_id` therefore runs `id_parser("Vendor")` and replaces its refusal with the
  long text. So a missing, null or non-id `vendor_id` gives the long text. An unknown or inactive
  vendor gives S079's two texts through `check_active_vendor`.
- **`period_error(from_date, to_date, to_sent)`** has a third argument, because the message depends
  on which date was sent (§ 5.1). The brief named only two.
- **The breakdown-calls clearing lives in `validate_contract`** (pure), not in the shell. It adds
  `breakdown_calls_per_year: None` when the tick is false and no number was sent.
  `breakdown_calls_error(ticked, calls)` then checks the merged tick.
- **`newest_end_first(status)`** in the core names the order rule of § 5.3. Ties are ordered by `id`
  in the same direction.
- **`GATED_FIELDS`** in the core maps each gated field to its key. `_drop_gated` uses it, and so
  will R02.2's prices.
- **Create checks the period and the calls after the access check**, as change does. So a user
  without the key gets the 403, not a 400.
- **The empty state.** "No contracts yet." (plus "Add the first one with *Add contract*." for a user
  with `can_add`) shows when the filters are at their defaults (Status *Not ended*) and the list is
  empty. Any other filter gives "No contracts match these filters." The API cannot tell "none at
  all" from "only ended ones" without a second count. So the hint "Ended contracts: choose Ended in
  Status." stays under it in the default view, also when empty.
- **A one-word "1 contract."** for a total of 1. The brief gives only "N contracts.".
- **The dialog is FormModal's standard width.** `FormModal.vue` is shared and has no size prop. Its
  "two columns from `md`" are Bootstrap `col-md-6` pairs inside it: Site / Type, Covered / Not
  covered, Calls per year. From / To and PM visits / Response time are always side by side
  (`col-6`), because each is a short input.
- **The e2e "empty save" test picks the vendor first.** The API reports only the first error, in
  field order, and `vendor_id` comes before `title`. On a fully empty form the message beside
  *Vendor* would show, not "Enter a title.". The test still saves an empty title and asserts "Enter
  a title." beside *Title*. *Departure in the test only.*
- **Dates in the e2e spec** are today in IST, computed in the test (`Date.now()` + 5:30).

## 5. Not done, deferred or assumed

- R02.2 to R02.8 as the brief's *Out of scope* says. There is no cost column (Q1 as recommended),
  and no read-only view of a contract for a reader who may not edit it (A2).
- **Assumption:** `date.fromisoformat` (Python 3.11+) also accepts the compact form `20270331`. The
  stated copy keeps that behaviour, as in improvements. The dialog always sends `YYYY-MM-DD`.
- No real-device checks (§ 8.5: none).

## 6. Tests

- **Backend:** while coding, the targeted files `test_migration_v43.py` (7 passed),
  `test_contracts_core.py` with `test_masters_core.py` (441 passed), `test_rbac.py` (64 passed) and
  `test_contracts_api.py` (33 passed).
- **Full unit run** (`YANTRA_TEST_RUN=s080c1 tooling\run-tests.bat`): backend PASSED, 4241 passed
  (197 s); frontend PASSED, 384 passed; tooling PASSED, 231 passed.
- **Build** (`npx vite build`): built; only the old chunk-size warning.
- **Schema docs** (`tooling\schema-docs.bat check`, run `s080c1`): PASSED, exit 0, at migration v43.
- **Browser:**
  - The new spec alone on `phone-chromium`, one lane: 9 passed. The first run had 2 failures in my
    own test code (`selectOption` with a RegExp label); the tests now pick the site by its id.
  - Targeted, § 8.4 (`e2e/contracts.spec.js e2e/masters.spec.js e2e/screens.spec.js`, Normal):
    63 passed, 1 skipped (an existing skip).
  - Whole suite at Normal (`tooling\run-e2e-tests.bat`, run once): 328 passed, 2 failed, 15 skipped
    (188 s). Both failures are the known one outside this step: `changelog.spec.js:14` on
    `desktop-chromium` (it_admin and admin; v0.1.14's empty CHANGELOG section). The other known
    failure, `improvements.spec.js:97` (lane-sharing), did not come back in this run. No S080 test
    and no masters test failed.

## Manual checks

- [auto] the engineer adds a contract and sees it In force (**important**) — `frontend/e2e/contracts.spec.js`::`S080: the engineer adds a contract and sees it In force in Masters › Contracts`
- [auto] a To date before the From date is refused beside the To field (**important**) — `frontend/e2e/contracts.spec.js`::`S080: a To date before the From date is refused beside the To field`
- [auto] the engineer sees the call-out number field and no cost note; the manager sees both (**important**) — `frontend/e2e/contracts.spec.js`::`S080: the engineer sees the call-out number field and no cost note; the manager sees both`
- [auto] IT admin adds a contract without the call-out number or the cost note — `frontend/e2e/contracts.spec.js`::`S080: IT admin adds a contract without the call-out number or the cost note`
- [auto] the status badges and the Status filter (**important**) — `frontend/e2e/contracts.spec.js`::`S080: the status badges and the Status filter`
- [auto] an inactive vendor is not offered, and its contract shows it as inactive — `frontend/e2e/contracts.spec.js`::`S080: an inactive vendor is not offered for a new contract, and its contract shows it as inactive`
- [auto] a deactivated contract leaves the list, and Show inactive brings it back — `frontend/e2e/contracts.spec.js`::`S080: a deactivated contract leaves the list, and Show inactive brings it back`
- [auto] the engineer does not see another site's contract; the manager sees Edit on both — `frontend/e2e/contracts.spec.js`::`S080: the engineer does not see another site's contract; the manager sees Edit on both`
- [auto] the Contracts list fits a phone with no sideways scroll (`@device`) — `frontend/e2e/contracts.spec.js`::`S080: the Contracts list fits a phone with no sideways scroll`

No real-device checks (§ 8.5), so no rows were added to `docs/steps/device-checks.md`.

## Docs updated

- `docs/schema/notes.json`: the `contracts` line (area *Equipment*, with the reason it is not beside
  `vendors`, BS1-05), and the area note "… and vendor contracts (S080)". Then `tooling\schema-docs.bat
  write` regenerated `schema.json` and `schema-data.js` (read in `git diff refs/steps/S079 --
  docs/schema/`), and `check` exits 0.
- `docs/Plan.MD` § 3: the four key rows in the matrix, and one paragraph on the keys and the field
  rule. § 2 item 9 needed no change: the coding did not depart from it.
- `.claude/CLAUDE.md`: § Step workflow *Self-check, repo items* (2) names `contracts.py`'s LOCK ORDER
  note; § SMTW-Review gains *Contract fields by key (S080)* (the brief's § 8.6 text, naming
  `_drop_gated`).
- `docs/Keycloak.md`, `backend/example_secrets_app.py`, `docs/steps/device-checks.md`: none, because
  no role, secret or real-device check changed.

## Feedback

- hindrance: a probe command left a bare `cat > /dev/null` waiting on stdin, and the Bash tool hung
  for its 2-minute timeout until I stopped it (1 call, 2 min)
- waste: my first lone browser run failed on my own `selectOption({ label: /regex/ })`, which
  Playwright does not accept for `selectOption` (1 extra run, 1 min)
- rule: BS1-01's answer asks for both "`id_parser("Vendor")`" and the long text "only for a missing
  `vendor_id`". The two contradict each other for a null id, so I chose (§ 4). A staleness answer
  that changes a message could quote the final text per case (BS1-01)
- idea: the brief's e2e check "an empty save shows Enter a title." cannot pass as written, because the
  API reports only the first error and `vendor_id` comes first. Brief reviewers could check an e2e
  refusal against the validator's field order (§ 8.4)

## Code review r1: CR1-01 to CR1-03, fixed by the orchestrator

- **CR1-01 (minor) — Fixed.** `frontend/src/views/masters/ContractsPanel.vue`: the empty default view now says "No contracts in force or starting later. Add one with *Add contract*." (true also when every contract has ended; the line "Ended contracts: choose Ended in Status." stays). The brief's § 5.7 text "No contracts yet…" is superseded by this.
- **CR1-02 (nit) — Fixed.** `backend/contracts_core.py` `_iso_date`: only the 10-character `YYYY-MM-DD` form is taken; `20270331`, week dates (`2027-W13-3`) and `2027-3-31` are refused. Test: three new cases in `test_contracts_core.py::…::test_dates_out_of_form_or_range_are_refused`.
- **CR1-03 (nit) — Fixed.** `ContractsPanel.vue` `reload`: a request counter; an answer (or error) that is not the latest request's is dropped.
- Checked: `tooling\run-backend-tests.bat tests/test_contracts_core.py tests/test_contracts_api.py` passed; `tooling\run-frontend-tests.bat` 384 passed; `npx vite build` green; `e2e/contracts.spec.js` on phone-chromium, one lane: 9 passed.
