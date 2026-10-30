```
Step: S081 — Machines on the contract
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 30-10-2026
```

# S081 — Code review, round 1

**Verdict: no `blocker` or `major` finding is open.** The step builds what the brief and its staleness
answers (BS1-01 to BS1-06) ask, the price gate holds on every path, and all suites are green. There are
4 nits and no minor findings.

Read: the brief with its Review log, the impl report, the step's diff from `refs/steps/S080`
(`step_snapshot.py diff S081`, 24 files), and in full `backend/contracts.py`,
`backend/tests/test_contract_equipment_api.py`, `backend/tests/test_migration_v44.py`,
`frontend/src/views/ContractView.vue` and `frontend/src/views/contracts/ContractMachineDialog.vue`.

## Test runs (run name `s081cr1`)

- **Unit suites** (`tooling\run-tests.bat`): backend 4323 passed, frontend 391 passed, tooling 231
  passed; ALL SUITES PASSED.
- **Build** (`npx vite build` in `frontend/`): built; only the usual chunk-size warning.
- **Schema docs** (`tooling\schema-docs.bat check`): PASSED, 4 passed, at migration v44.
- **Browser tests:** not re-run. No finding of mine needs a browser run. The coder's runs are the right
  ones and are recorded with their counts:
  - the new tests alone: 7 passed;
  - the targeted run (`contracts`, `masters`, `tickets-raise`, `readings`, `screens`): 136 passed,
    1 skipped;
  - the whole suite at Normal, once, because the router is shared code: 336 passed, 15 skipped and
    2 failed. Both failures are the known `changelog.spec.js:14` on `desktop-chromium`, which is not
    this step's.

  `tickets-raise.spec.js` and `readings.spec.js` cover the two existing users of the changed
  `EquipmentPicker.vue`. No change to `api.js` or `e2e/support/`, so no extra WebKit run is due.

## Findings

No `blocker`, `major` or `minor` finding.

## Nits

- **CR1-01** (nit) `backend/tests/test_contract_equipment_api.py:310`: `test_overlaps` checks neither
  rule at the edge of § 5.6. Add a second AMC at a site the reader does not hold (its line on a node
  moved there), which must not show. Add one whose `to_date` equals this contract's `from_date`, which
  must show, so the inclusive comparison is pinned.
- **CR1-02** (nit) `backend/tests/test_contract_equipment_api.py:39`: the module's `engineer` fixture
  shadows conftest's `engineer` with a different person (a site engineer with all units). Name it
  `site_engineer`, so a reader does not take it for the X-Test-Role engineer.
- **CR1-03** (nit) `frontend/src/views/contracts/ContractMachineDialog.vue:71`: *Edit price* saves with
  `FormModal`'s default "Save". Use "Save price", so the button names its result (CLAUDE-COMMON
  § Writing style B), as *Add machine* already does.
- **CR1-04** (nit) `backend/tests/conftest.py:186`: `"contracts","procedures"` lacks the space after
  the comma.

## Checked and found consistent

- **Migration v44** (`backend/local_db.py`): it is § 4.1 word for word. The ENUM is v33's list plus the
  two kinds at the end; no migration between v33 and v43 changes it. It needs no `_PRECONDITIONS`
  entry. `test_migration_v44.py` covers a fresh database, a v43 database with every old event kind,
  the CHECK, the unique key, both foreign keys and a re-run.
- **`test_migration_v9.py`**: the edit is right. `test_the_shape_holds` pins the *current*
  `equipment_events.event` ENUM, and its comment already records v30's and v33's widenings. Adding the
  two kinds with "since v44 (S081)" follows that pattern. The report lists the file and why it changed.
- **Core** (`contracts_core.py`): `parse_price` refuses a float, a boolean, a minus sign, a comma, the
  rupee sign, three decimals and non-ASCII digits (`[0-9]`, not `\d`). `validate_line` requires the
  machine on a `POST` and drops it on a `PUT`. `event_text` holds no price and fits the 200-character
  column. `LINE_GATED_FIELDS` goes through S080's single `_drop_gated` (BS1-02).
- **The price gate** (§ 5.4):
  - `_contract_out` drops `price_total` and `priced_count`, and `_machine_lines` drops `price`; the keys
    are absent, not null.
  - The list carries the gated sums through the same `_contract_out`. The reported extra
    `machine_count` on list items is ungated by design.
  - `POST` drops the price for a non-holder. `PUT` answers 403 by `require_perm_at(READ_COST)` before
    any read of the line (B3).
  - No history line carries a price, and a price change writes none.
  - The API tests cover the engineer, IT admin and the manager on each path.
- **Permissions:** every route has `require_perm(EDIT)` or `require_perm(READ_BASIC)` and then the
  site check: 404 without `read_basic` at the site, 403 without `edit` there. The actor comes from
  `actor()`. All SQL uses parameters; the f-strings add only code constants, `NODE_JOINS` and `marks()`.
- **The node rules** (§ 5.2): the inactive contract (409, add only), a missing node or one outside the
  reader's units (400), a scrapped node from the locked row (409), another site (400, naming the
  contract's site) and a duplicate (409 through `UNIQUE_KEY_ERRORS`) are each tested.
- **Locks** (§ 5.5): every write takes the contract `FOR UPDATE` first, then the line `FOR UPDATE` or
  the node `LOCK IN SHARE MODE`. Only contracts.py locks these rows, and it takes nothing else
  exclusive, so there is no cycle. Both the equipment.py bullet and the docstring of contracts.py say
  this.
  - One window is not new: the plain `NODE_JOINS` read in `_check_node` uses the snapshot of the first
    plain read after the contract lock. A move committed between that read and the node lock can still
    pass as the old site. The line then shows "Now at …", the display residual that § 5.2 accepts.
- **Overlaps** (§ 5.6): one query matches the same node, the parent, the grandparent, a child or a
  grandchild, and only at the reader's `read_basic` sites. It skips an inactive contract on either
  side. The test covers each case the brief lists, on both contracts.
- **Database down:** `db_down` gives 503 on the add and on the detail.
- **Frontend:**
  - The page shows every state of § 5.7: loading, the 404 text with its link, a load error with
    *Retry*, the empty list with or without the hint, "Now at", the lifecycle badge, the overlaps, the
    price and the total for senior holders only.
  - *Remove* asks in its row, as `MetersCard.vue` does, and the confirm button is styled danger.
  - The dialog uses `FormModal` through `useFormModal`, with `toBody` built on `lineBody` (BR1-01).
    The picker is kept to the contract's site with the brief's empty text. Save is disabled with
    "Choose a machine" until a machine is picked.
  - The page and the dialog hold no business rule.
  - `btn-sm` follows `MetersCard.vue`; the page is an engineer's and manager's screen, not a floor
    screen.
- **Browser tests:** the 7 tests of § 8.4 assert what the user sees: the row, the history line, "₹9,809",
  the total line, no price for the engineer, the overlap text, the column and the link. Each flow test
  calls `expectDialogFits` on every dialog it opens. Only the phone-fit test is tagged `@device`, as
  the rule asks.
- **Manual checks:** all seven checks are `[auto]` with their test, the two important ones marked. The
  brief has no real-device check (§ 8.5).
- **Docs pass:** `notes.json` has the new table and the two event kinds, and the generated files are
  current (the check passes). `Plan.MD` § 3 and `.claude/CLAUDE.md` § SMTW-Review have § 8.6's text
  with BS1-02's `_drop_gated`. `device-checks.md` correctly gets no row.
- **Scope:** everything in § 3 is built. Nothing out of scope is built: no card, no filter, no
  placeholder cards, no *Edit* of the terms. The departures are in "Decisions taken".

## Manual browser check for the user

None required. Every check is automated and passed in the coder's runs. At gate B the user may look at
the B3, Q3, Q5 and Q6 choices, which the brief flags for KLA.

## Feedback

- none
