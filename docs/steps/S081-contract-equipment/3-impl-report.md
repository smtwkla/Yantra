```
Step: S081 — Machines on the contract
Doc: impl-report
Author: Coder (Opus)
Date: 30-10-2026
```

# S081 — Machines on the contract: implementation report

The step is built as the brief and its staleness answers (BS1-01 to BS1-06) say. The unit suites, the build, the schema docs check, the new browser tests alone and the targeted
browser run are green. The whole browser suite at Normal failed only in the known `changelog.spec.js:14`
(both of its cases, it_admin and admin), which is not this step's (§ 6). Departures from the brief are
small; all are in § 4.

## 1. What was built

- **The machines a contract covers.** Migration v44 adds `contract_equipment`: one row per contract and
  equipment node, any level, with an optional `price DECIMAL(10,2)` before GST. The keys, foreign keys
  and CHECK are § 4.1's, word for word. The same migration adds `contract_added` and `contract_removed`
  at the end of the `equipment_events.event` ENUM (v33's list, unchanged since).
- **Three line routes** on `/api/contracts/<id>/equipment`: `POST` (add a machine), `PUT …/<equipment_id>`
  (change its price), `DELETE …/<equipment_id>` (remove it). Each answers with the contract's detail.
- **The detail and the list carry the machines' sums.** The detail (`GET /api/contracts/<id>` and the
  answer of every write, S080's `PUT` included) has `machines`, `machine_count`, and, for
  `contract:read_senior` holders only, `price_total` and `priced_count`. Each line has the node, its path,
  its site, `at_contract_site`, `can_open`, its overlaps, who and when, and `price` (gated).
- **The overlap warning** (§ 5.6): under each line, every other active contract of the same type whose
  period meets this one's, with a line on the same node, a node above it or a part of it.
- **The machine's history**: each add writes `contract_added`, each removal `contract_removed`, with
  "<title> (<type>, DD-MM-YYYY to DD-MM-YYYY)". Never the price.
- **The contract page** `/contracts/:id` (`ContractView.vue`): the header, the *Terms* card, the
  *Machines covered* card with *Add machine*, *Edit price* and *Remove* (asked in the row), the price per
  line and the total for managers.
- **The machine dialog** (`ContractMachineDialog.vue`): *Add machine* (the picker, kept to the contract's
  site, and the price for managers) and *Edit price* (the price alone).
- **Masters › Contracts**: each title opens the contract page; a *Cost before GST* column from the `md`
  width for users who hold `contract:read_senior` at some listed site.

## 2. How it works

- **Core (`contracts_core.py`, pure).**
  - `parse_price(raw)`: `None` or `""` (also only spaces) → `None`; an `int` ≥ 0, or a trimmed string
    matching `^[0-9]+(\.[0-9]{1,2})?$` → `Decimal`; above `PRICE_MAX` → "Price: at most 9,99,99,999.99.";
    anything else (a float, a boolean, a minus, a comma, "₹", three decimals) → "Enter the price in
    rupees, before GST, e.g. 9809 or 9809.50.".
  - `validate_line(body, creating)`: on a `POST` the machine is required (`id_parser("Machine")` gives
    "Choose a machine."); on a `PUT` a sent `equipment_id` is dropped. Built on S080's
    `validate_fields`.
  - `LINE_GATED_FIELDS = {"price": "contract:read_senior"}` (BS1-02), `TYPE_SHORT`, `event_text(contract)`.
- **Shell (`contracts.py`).**
  - `_CONTRACT_SELECT` now left-joins one grouped read of `contract_equipment` (count, priced count, sum).
    So the list and the detail both carry `machine_count`, `priced_count` and `price_total`;
    `_contract_out` deletes the last two (and `cost_note`) without `can_read_cost`.
  - `_detail(cur, row, flags, today)` is the one builder of § 6.1 (BS1-01). `get_contract` and `_answer`
    call it, so S080's `PUT` answer carries the machines too. It calls `_machine_lines` (one plain read
    through `NODE_JOINS`, by code; `node_path` for the path; `can_open` from `accessible_unit_ids`;
    `price` deleted without `can_read_cost`) and `_overlaps` (one plain read, below).
  - `_overlaps(cur, contract, lines, site_ids)`: nothing for an inactive contract or an empty list.
    Otherwise one query joins this contract's lines to the other active contracts of the same type
    whose period meets it, at the sites where the reader holds `contract:read_basic`
    (`_sites_holding`). A match is the same node, its parent, its grandparent, a child or a grandchild,
    through `parent_id` (three levels at most). `on_code` is `null` on the same node.
  - *Add* (`add_machine`): `validate_line` → `_lock_contract` (the contract `FOR UPDATE`, then
    `read_basic` 404 and `contract:edit` 403 at its site) → inactive 409 → `_drop_gated(clean, site,
    LINE_GATED_FIELDS)` → `_check_node` (the node `LOCK IN SHARE MODE`: missing 400; a plain read
    through `NODE_JOINS`: not in the user's units 400; scrapped, from the locked row, 409; another
    site 400 naming the contract's site) → `insert_row` (`uq_contract_equipment` → 409 "This machine is
    already on the contract.") → `write_events` → the detail, 201.
  - *Change a price* (`change_price`): `_lock_contract` → `require_perm_at(contract:read_senior)` 403 (B3)
    → `_drop_gated` → `_lock_line` (the line `FOR UPDATE`, 404 "This machine is not on the contract.") →
    `update_row` (nothing when no price was sent) → the detail. No history line.
  - *Remove* (`remove_machine`): `_lock_contract` → `_lock_line` → `DELETE` → `write_events`
    (`contract_removed`, the contract's text as the old value) → the detail.
  - An inactive contract takes price changes and removals (BR1-03); only the add refuses it.
  - The module docstring is rewritten whole (BS1-03): the first paragraph, ACCESS, the LOCK ORDER
    path by path and the no-cycle list. equipment.py's contracts.py bullet is § 5.5's text.
- **Frontend.**
  - `contractLabels.js`: `formatRupees` (`toLocaleString("en-IN")`, paise only when not whole),
    `coverageLines`, `responseText`, `overlapText` (type nouns "AMC", "CMC", "warranty", "on-call
    contract"; " (on CMP001)" before the stop), `lineBody(form, { creating, canReadCost })`.
  - `EquipmentPicker.vue`: optional `siteId` (adds `site_id` to the search) and `emptyText`; `pick` emits
    `(id, item)`. `RaiseTicketView.vue` and `ReadingsRegister.vue` pass neither and take only the id.
  - `ContractMachineDialog.vue`: `useFormModal` directly (BS1-06) with `toBody: (f) => lineBody(f, {
    creating: editingId.value === null, canReadCost })` (BR1-01). A pick stores the picker's item and
    shows "CODE — name" with *Change*; Save *Add machine* is disabled with "Choose a machine" until then.
    The page keys the dialog by the contract's id, so its path never names another contract.
  - `ContractView.vue`: loads `GET /api/contracts/<id>`; a 404 shows "Contract not found, or not at
    your sites." with a link to the equipment list. Every write's answer replaces the page's copy.
  - `equipmentLabels.describeEvent`: "Added to contract: …" and "Removed from contract: …".

## 3. Files touched

| File | Change |
|---|---|
| `backend/local_db.py` | Migration v44 |
| `backend/contracts_core.py` | `parse_price`, `validate_line`, `LINE_GATED_FIELDS`, `PRICE_MAX`, `TYPE_SHORT`, `event_text` |
| `backend/contracts.py` | Docstring rewritten; the sums in `_CONTRACT_SELECT`; `_contract_out` gates them; `_machine_lines`, `_overlaps`, `_detail`; `_drop_gated` gains `fields`; the three line routes; `uq_contract_equipment` in `UNIQUE_KEY_ERRORS` |
| `backend/equipment.py` | Docstring: the contracts.py LOCK ORDER bullet (§ 5.5) |
| `backend/tests/conftest.py` | `contract_equipment` first in `_TABLES` |
| `backend/tests/test_migration_v44.py` | New (6 tests) |
| `backend/tests/test_contracts_core.py` | The line, the price and the history text (S081 classes) |
| `backend/tests/test_contract_equipment_api.py` | New (35 tests) |
| `backend/tests/test_migration_v9.py` | The pinned event ENUM gains the two kinds |
| `frontend/src/views/ContractView.vue` | New: the contract page |
| `frontend/src/views/contracts/ContractMachineDialog.vue` | New: *Add machine* and *Edit price* |
| `frontend/src/router/index.js` | Route `/contracts/:id(\\d+)`, name `contract` |
| `frontend/src/components/EquipmentPicker.vue` | Props `siteId`, `emptyText`; `pick` emits the item too |
| `frontend/src/views/masters/ContractsPanel.vue` | Title link; *Cost before GST* column |
| `frontend/src/utils/contractLabels.js` | `formatRupees`, `coverageLines`, `responseText`, `overlapText`, `lineBody` |
| `frontend/src/utils/equipmentLabels.js` | Two `describeEvent` cases |
| `frontend/tests/contractLabels.test.js` | S081 tests (6) |
| `frontend/tests/equipmentLabels.test.js` | One test for the two kinds |
| `frontend/e2e/contracts.spec.js` | Seven S081 tests and their in-spec helpers |
| `docs/schema/notes.json`, `schema.json`, `schema-data.js` | The `contract_equipment` line, the two kinds on `equipment_events`; regenerated |
| `docs/Plan.MD` | § 3, the contract keys' paragraph |
| `.claude/CLAUDE.md` | § SMTW-Review, *Contract fields by key* |
| `docs/steps/S081-contract-equipment/1-brief.md`, `docs/steps/INDEX.md` | Status (S081's row only) |

Count: 19 code and test files (4 backend code, 5 backend tests, 7 frontend code, 3 frontend tests and
the spec), 5 docs (3 of them the schema docs). `backend/tests/test_contracts_api.py` needed no change (BS1-04).

## 4. Decisions taken

- **The sums are one grouped `LEFT JOIN` in `_CONTRACT_SELECT`**, not three correlated subqueries. So
  every list item also carries `machine_count` and, gated, `priced_count`; § 6 names only `price_total`
  on the list. Both go through `_contract_out`, so nothing new leaks; the panel reads only `price_total`.
- **`uq_contract_equipment` joins `UNIQUE_KEY_ERRORS` from `contracts.py`** (`UNIQUE_KEY_ERRORS.update`,
  as every module does), not by an edit of `api_common.py`.
- **The rule order of an add** follows § 5.2 and § 5.5: the node's shared lock (missing 400), then the
  plain read (outside the user's units 400), then scrapped 409 from the locked row, then the site 400.
  So an engineer of one site who names a node of another site where they hold no unit gets "Choose a
  machine.", not the site text. A user who sees both sites gets the site text.
- **`_check_node`, `_lock_contract` and `_lock_line`** are three small helpers in `contracts.py`, so the
  three routes share one contract lock path and one line lock path.
- **`load_node_for_user` is not reused** for the node: it locks `FOR UPDATE` (exclusive), and § 5.5 wants
  the node shared; its refusal is a 404, where § 5.2 wants 400 on `equipment_id`.
- **`_drop_gated` is also called by the price route**, after its 403 (BS1-02): a no-op there, but every
  line write goes through the one gating mechanism.
- **The overlap text** puts " (on CMP001)" before the final stop: "…, 01-04-2025 to 31-03-2026 (on
  CMP001)." The brief gives the sentence and the clause, not their join.
- **Save on *Edit price*** keeps `FormModal`'s default "Save"; *Add machine* uses "Add machine" (§ 5.7).
- **Empty list:** "Add the first one with Add machine." shows only when *Add machine* shows (can edit and
  the contract is active), so an inactive contract never points at a button that is not there.
- **A 404 page links "Open the equipment list"**, a verb-first link text for § 5.7's "a link to the
  equipment list".
- **The type badge in the header** is `text-bg-light border`, and *Inactive* `text-bg-secondary`; the
  brief names the badges, not their colours.
- **API tests use a site engineer** (`user_at_sites`, all units) instead of the `engineer` fixture: the
  X-Test-Role engineer holds no unit (its wildcard membership has `all_units` false), so every add was
  refused "Choose a machine.". The module overrides `engineer` with that site engineer.

## 5. Not done, deferred or assumed

- Out of scope as the brief says: the *Under contract* card, the list filter and
  `auth_utils.sites_holding` (S082); documents, renewal, reminders, breakdown calls, PM visits.
- **Assumed:** the machine dialog's price field label is "Price (₹, before GST)" without "(optional)";
  the help text says it is from the quote.
- **Known failure, not this step's:** see § 6 for `changelog.spec.js:14`.

## 6. Tests

Run name `YANTRA_TEST_RUN=s081c1`.

- **Unit suites, final full run** (`tooling\run-tests.bat`): backend 4323 passed, frontend 391 passed,
  tooling 231 passed; ALL SUITES PASSED. The first full run had 1 failure:
  `tests/test_migration_v9.py::test_the_shape_holds` pins the latest `equipment_events.event` ENUM; it
  now lists the two new kinds (one more test file touched). Then the full run again, green.
- **Build** (`npx vite build`): green; only the usual chunk-size warning.
- **Schema docs** (`tooling\schema-docs.bat check`): PASSED, exit 0, at migration v44.
- **New browser tests alone** (`E2E_LANES=1`, `e2e/contracts.spec.js --project=phone-chromium -g S081`):
  7 passed, first run.
- **Targeted browser run** (Normal with `e2e/contracts.spec.js e2e/masters.spec.js
  e2e/tickets-raise.spec.js e2e/readings.spec.js e2e/screens.spec.js`, § 8.4): 136 passed, 1 skipped (an
  existing skip), 0 failed. The specs are the changed screens (contracts, masters), the two other users of
  `EquipmentPicker.vue` (tickets-raise, readings) and `screens.spec.js`.
- **Whole suite at Normal** (`tooling\run-e2e-tests.bat`, once, because the router is shared code):
  336 passed, 15 skipped, 2 failed. The 2 failures are the known `changelog.spec.js:14` on
  `desktop-chromium` ("S048: it_admin …" and "S048: admin opens the change log …"): v0.1.14's empty
  CHANGELOG section makes `getByText('This version')` match two elements. Not this step's; not fixed.
- No change to `api.js` or `e2e/support/`, so no extra WebKit run.

## Manual checks

From the brief § 8.4 (all automated; § 8.5 has no real-device check):

- [auto] the engineer adds a machine to a contract; the page lists it and the machine's history shows the
  line (**important**) — `frontend/e2e/contracts.spec.js`::`S081: the engineer adds a machine to a contract; the page lists it and the machine's history shows the line`
- [auto] the manager enters a price per machine and sees the total; the engineer sees no price
  (**important**) — `frontend/e2e/contracts.spec.js`::`S081: the manager enters a price per machine and sees the total; the engineer sees no price`
- [auto] a machine of another site is not offered in Add machine — `frontend/e2e/contracts.spec.js`::`S081: a machine of another site is not offered in Add machine`
- [auto] Remove asks first; the machine leaves the contract page and its history shows the line — `frontend/e2e/contracts.spec.js`::`S081: Remove asks first; the machine leaves the contract page and its history shows the line`
- [auto] a second AMC on the same machine shows the overlap line on both contract pages — `frontend/e2e/contracts.spec.js`::`S081: a second AMC on the same machine shows the overlap line on both contract pages`
- [auto] Masters › Contracts shows Cost before GST to the manager only, and the title opens the contract
  page — `frontend/e2e/contracts.spec.js`::`S081: Masters › Contracts shows Cost before GST to the manager only, and the title opens the contract page`
- [auto] the contract page with its machines fits a phone with no sideways scroll (`@device`) — `frontend/e2e/contracts.spec.js`::`S081: the contract page with its machines fits a phone with no sideways scroll`

On a real device: none (§ 8.5).

## Docs updated

- `docs/schema/notes.json`: the `contract_equipment` line (area *Equipment*); the `equipment_events`
  line names `contract_added` and `contract_removed`. Then `tooling\schema-docs.bat write` regenerated
  `docs/schema/schema.json` and `docs/schema/schema-data.js`; `check` exits 0 (PASSED, 4 checks).
- `docs/Plan.MD` § 3, the contract keys' paragraph: the price per machine and the total follow
  `contract:read_senior`; an engineer or IT admin adds a machine without a price; a price change needs
  both keys (B3).
- `.claude/CLAUDE.md` § SMTW-Review, *Contract fields by key*: the price, the total and the priced count
  through `_contract_out`, `_machine_lines` and `_drop_gated` with `LINE_GATED_FIELDS`; the history never
  holds a price; a price change needs both keys (§ 8.6 with BS1-02).
- `docs/steps/device-checks.md`: no row (§ 8.5: none).

## Feedback

- waste: the X-Test-Role `engineer` fixture holds no unit (wildcard membership, `all_units` false), so 16
  of the new API tests failed with "Choose a machine." before I found it with a debug test (1 extra run,
  about 5 min; `backend/tests/conftest.py` `engineer`). A line in conftest's `engineer` docstring would save it.
- hindrance: two inline heredocs carrying JS/Python with quotes died with "unexpected EOF while looking for
  matching `''" (2 lost calls); README § Shell on Windows says so, and I had read it only after the first.
- rule: `test_migration_v9.py::test_the_shape_holds` pins the latest event ENUM, but § 8.3 of the brief
  ("existing tests that break") did not list it; the full run found it (1 extra full run, about 4 min).
  A brief that widens a pinned ENUM could grep the tests for the old list.

## Fix rounds

### Round 1

Answers to `4-code-review-r1.md` (0 blocker, 0 major, 0 minor, 4 nits). All four fixed. No code fault found.

- **CR1-01 Fixed.** Two tests added to `TestDetail` in `backend/tests/test_contract_equipment_api.py`:
  - `test_overlaps_at_a_site_the_reader_does_not_hold_stay_hidden`: the machine is moved to another site, its line is added on that site's AMC, and the machine moves back. The admin (holds both sites) sees the overlap; the site engineer (holds only the contract's site) sees none.
  - `test_a_period_that_only_touches_on_one_day_overlaps`: a contract ending on this contract's `from_date` shows; one ending the day before does not. This pins the inclusive comparison.
  Both pass on the unchanged code, so the code was right. Red run not done: no fault and no code change; these tests add coverage only.
- **CR1-02 Fixed.** The module's `engineer` fixture is now `site_engineer`, with its two uses in `parametrize` (`request.getfixturevalue`) renamed. conftest's `engineer` is no longer shadowed.
- **CR1-03 Fixed.** `ContractMachineDialog.vue`: the *Edit price* button says "Save price". `frontend/e2e/contracts.spec.js` line 306 now clicks "Save price". No other test asserts that button.
- **CR1-04 Fixed.** `backend/tests/conftest.py` `_TABLES`: `"contracts", "procedures"`.

**Tests** (run name `s081f1`): `test_contract_equipment_api.py` and `test_contracts_api.py` 70 passed. Full `tooling\run-tests.bat`: backend 4325 passed, frontend 391 passed, tooling 231 passed, ALL SUITES PASSED. Browser, targeted because CR1-03 changed a text a test asserts: `e2e/contracts.spec.js`, 18 passed (phone and desktop). No whole-suite run, as asked.

**Docs updated:** none, because the round changes a button label and tests only.

### Feedback

- none
