```
Step: S082 — Under contract on the machine
Doc: impl report
Author: Coder (Opus), resumed run
Date: 31-10-2026
```

# S082 — implementation report

**S082 is built and green, except two browser failures outside the step.** The unit suites are green: backend
4355, frontend 397, tooling 231. The schema docs check and the build pass. The whole browser suite at Normal has
2 failures, both in `changelog.spec.js` (S048). They come from the empty `0.1.14` section that release v0.1.14
wrote into the committed `CHANGELOG.md`; S082 changes neither file (§ 5).

## 1. What was built

1. **The *Under contract* card** on the equipment page, after *Lessons* and before *Open tickets*, on every
   width. One item per contract in force on the node, its parent or its grandparent, and per contract ended
   in the last 90 days: the headline ("Under AMC with Atlas Copco until 31-03-2027"; ended: "AMC with Atlas
   Copco ended on 31-03-2026."), an *Ends in N days* badge, the ancestor that brings it ("Through CMP001 —
   Screw compressor 1, this part's machine."), the response time, the coverage lines, the call line and
   *Open contract*. The D9 warning "Do not repair. Call the engineer; the vendor repairs this machine." stands
   first, in `alert-warning`, on a contract not ended with the tick.
2. **The route** `GET /api/contracts/for-equipment/<node_id>` behind `contract:read_basic`.
3. **The equipment list's *Contract* filter**: *Any contract status / Under contract / Not under contract*,
   API `?contract=under|not_under`.
4. **`auth_utils.sites_holding(cur, key)`**: S080's `contracts._sites_holding`, moved, public, unchanged.

## 2. How it works

- **Route** (`contracts.contracts_for_equipment`): reads the node with `load_node_for_user(cur, node_id,
  for_update=False)` (404 outside the reader's units). One plain read: `_CARD_SELECT` (S080's contract
  columns and joins, plus `contract_equipment cl` and `cl.equipment_id`) with `cl.equipment_id IN (node,
  parent, grandparent)`, `c.active = 1`, `c.from_date <= today` and `c.to_date >= today − 90`.
  `contracts_core.card_items(rows, node, today)` (pure) keeps one row per contract, the line nearest the node,
  and orders them: not ended by `to_date, id`; then ended, the latest end first, then `id`. The shell keeps a
  contract only where `has_perm_at("contract:read_basic", site)` (once per site), builds it through
  `_contract_out` and keeps only `_CARD_KEYS`, plus `contract_id` and `via`. So no price, total, priced count,
  machine count or cost note goes out, for any reader; the call-out number goes out only where
  `_contract_out` keeps it (`contract:read` at the contract's site).
- **Filter** (`equipment.list_equipment`, beside the `tickets` filter, not in `_list_filters`, so the printed
  asset list ignores it): `enum_arg("contract", COVERAGE_FILTERS)`; the sites from
  `sites_holding(cur, "contract:read_basic")`; the condition from the pure
  `contracts_core.covered_sql(coverage, site_ids, today)`: an `EXISTS` (or `NOT EXISTS`) over
  `contract_equipment` and `contracts` with `ce.equipment_id IN (e.id, e.parent_id, p.parent_id)`,
  active, in force today, at those sites; `0 = 1` / `1 = 1` with no site. `equipment.py` imports
  `contracts_core` (pure) only, never `contracts.py`.
- **Card** (`UnderContractCard.vue`, `props: { node }`): fetches only when `node.permissions` holds
  `contract:read_basic`; shows nothing with no item, except "No contract on this machine." for a
  `contract:edit` holder at the node's site; an error shows "Contracts could not be loaded: <message>". The
  texts come from pure helpers in `contractLabels.js`: `cardHeadline`, `showsDoNotRepair`, `viaText`,
  `callLine` (`{text, number}` or `null`), `telHref`. An ended item is `text-secondary`, with no warning and no
  call line.
- **List screen** (`EquipmentView.vue`): a select `aria-label="Contract"` after *Tickets*, shown with
  `contract:read_basic` in `userPermissions`; `contract` joins `FILTER_KEYS` (the phone's *Filters (n)*) and
  `listUrl`, both skipped for a user without the key, through one helper `keyApplies(key)` that also holds the
  existing `tickets` rule.

## 3. Files touched

| File | Change |
|---|---|
| `backend/auth_utils.py` | `sites_holding(cur, key)`, moved from `contracts.py`. |
| `backend/contracts.py` | `_sites_holding` removed, callers use `sites_holding`; `_CONTRACT_SELECT` split into `_CONTRACT_COLUMNS` + `_CONTRACT_FROM` (same text); `_CARD_SELECT`, `_CARD_KEYS`, `_via`, the route `contracts_for_equipment`; module docstring. |
| `backend/contracts_core.py` | `CARD_ENDED_DAYS`, `COVERAGE_FILTERS`, `card_items`, `covered_sql`. |
| `backend/equipment.py` | the `contract` filter in `list_equipment`; imports. |
| `backend/tests/test_contracts_core.py` | `TestCardItems`, `TestCoveredSql`. |
| `backend/tests/test_contract_card_api.py` | new: the card route. |
| `backend/tests/test_equipment_api.py` | `TestContractFilter`. |
| `frontend/src/views/equipment/UnderContractCard.vue` | new: the card. |
| `frontend/src/views/EquipmentDetailView.vue` | the card after *Lessons*; docstring and the order comment. |
| `frontend/src/views/EquipmentView.vue` | the *Contract* select, `FILTER_KEYS`, `listUrl`, `keyApplies`. |
| `frontend/src/utils/contractLabels.js` | `CONTRACT_FILTER_CHOICES`, the three texts, `showsDoNotRepair`, `cardHeadline`, `viaText`, `callLine`, `telHref`. |
| `frontend/tests/contractLabels.test.js` | the S082 cases. |
| `frontend/e2e/contracts.spec.js` | eight S082 tests and their helpers. |
| `docs/Plan.MD`, `.claude/CLAUDE.md`, `docs/steps/device-checks.md` | docs pass (below). |
| `docs/steps/S082-under-contract-card/1-brief.md`, `docs/steps/INDEX.md` | Status. |

13 code and test files, 3 docs. The brief planned 15 code files: `equipmentFilters.js` and its test are not
touched, because BS1-06 moved `CONTRACT_FILTER_CHOICES` to `contractLabels.js`.

## 4. Decisions taken

- **Kept from the stopped coder's work, after review against the brief:** all of it, with one whitespace slip
  fixed (`empty ={` in `list_equipment`). Its route, core functions and tests match § 5.1–§ 5.6 and the
  staleness answers (BS1-01: `_CONTRACT_SELECT` with `cl` for the lines).
- **`via` carries `level`** besides `{id, code, name}` (§ 5.2 names three keys). The grandparent is always a
  machine, but the parent may be a component-unit (on a component's card), and "this part's machine" would then
  be wrong. `viaText` writes "this part's component-unit." for that case. The brief gives only the machine
  wording; the component-unit wording is mine.
- **`_CONTRACT_SELECT` split** into columns and joins, so `_CARD_SELECT` adds `cl.equipment_id` and the join
  without a near-copy of the select. `_CONTRACT_SELECT`'s text is unchanged.
- **`callLine` returns `null`** where the brief says the line is "left out" (ended; a reader without the number
  under the D9 warning), so the rule is in the pure helper and tested, not in the template.
- **The card's texts as exported constants** (`DO_NOT_REPAIR`, `ASK_THE_ENGINEER`, `NO_CALLOUT_NUMBER`), so
  the unit test pins the wording once.
- **`keyApplies(key)`** in `EquipmentView.vue` replaces the two inline `tickets` checks; `listUrl` now loops
  over `[...FILTER_KEYS, "q", "props"]` (the same keys as before, plus `contract`), so the counted keys and the
  sent keys cannot drift apart.
- **The card's root is the card itself** (`order-0` on it), not a wrapper `div` as `LessonsCard` has: the
  Lessons card needs a wrapper for its dialog; this card has none.
- **Departures flagged by the brief for KLA at gate B** (not mine): the card before *Open tickets* (Q2 b); the
  wording "To call the vendor, ask the engineer."; the call-out number as a `tel:` link (departs from S079
  D12's text-only phone).

## 5. Not done, deferred or assumed

- **A fault outside S082, not fixed (needs a decision).** `S048: it_admin opens the change log from the
  version in the sidebar` and the same test for `admin` (`frontend/e2e/changelog.spec.js:14`, desktop-chromium)
  fail. Release v0.1.14 (e77d635) wrote an empty `## 0.1.14` section, so the dialog shows "No notes were written
  for this version." Then `dialog.getByText("This version")` matches that line and the badge, and the strict
  locator fails. The fault is in HEAD, so a pre-flight or release run fails on it too. A fix is one word,
  `getByText("This version", { exact: true })`. Recommendation: fix it in the fix lane (its own step), or here
  if the orchestrator allows it. I left it alone because it is outside S082's scope.
- Out of scope as the brief says: a part's contract on its machine's card (Q4), upcoming contracts on the card,
  the printed asset list, a list column or badge.

## Manual checks

- [auto] **Important.** The technician sees the card with Do not repair and no number; the engineer sees the call-out number as a call link — `frontend/e2e/contracts.spec.js::S082: a technician sees the Under contract card with Do not repair and no number; the engineer sees the call-out number as a call link`
- [auto] **Important.** The card comes before Open tickets (and below Lessons) — `frontend/e2e/contracts.spec.js::S082: the Under contract card comes before Open tickets`
- [auto] **Important.** A machine's contract shows on its part's card, naming the machine — `frontend/e2e/contracts.spec.js::S082: a contract on a machine shows on its part's card, naming the machine`
- [auto] An ended contract shows as ended, with no warning — `frontend/e2e/contracts.spec.js::S082: an ended contract shows on the card as ended, with no warning`
- [auto] The empty card for the engineer, no card for the operator — `frontend/e2e/contracts.spec.js::S082: the engineer sees No contract on this machine; the operator sees no card`
- [auto] A removed machine loses the card — `frontend/e2e/contracts.spec.js::S082: a machine removed from its contract loses the card`
- [auto] **Important.** The list's Contract filter — `frontend/e2e/contracts.spec.js::S082: Under contract and Not under contract filter the equipment list`
- [auto] The card fits a phone (`@device`; phone-chromium and desktop-chromium at Normal) — `frontend/e2e/contracts.spec.js::S082: the Under contract card with its warning fits a phone with no sideways scroll`
- [ ] **Important.** On a phone, the yellow "Do not repair" warning is readable at arm's length in the shop's
  light — `docs/steps/device-checks.md` row 59 (dev server, set-up by KLA in the row; for IT Admin).

## Tests run

Run name `YANTRA_TEST_RUN=s082c1`.

- Targeted backend, while coding: `test_contracts_core.py test_contract_card_api.py test_equipment_api.py
  test_contracts_api.py test_contract_equipment_api.py` — PASSED, 375 passed (S080's and S081's modules green
  after the `sites_holding` move, § 8.3).
- Frontend unit while coding: `tests/contractLabels.test.js` — 19 passed.
- **All suites**, `tooling/run-tests.bat`, once at the end: backend PASSED, 4355 passed (384 s); frontend
  PASSED, 397 passed; tooling PASSED, 231 passed; ALL SUITES: PASSED.
- Build: `npx vite build` in `frontend/` — built, only the known chunk-size warning.
- Schema docs: `tooling/schema-docs.bat check` — exit 0, "Schema docs at migration v44: 4 passed".
- Browser, the new tests alone (`E2E_LANES=1`, `e2e/contracts.spec.js --project=phone-chromium -g S082`):
  8 passed, on the first run.
- Browser, targeted at Normal (`e2e/contracts.spec.js e2e/equipment.spec.js e2e/lessons.spec.js
  e2e/screens.spec.js`, the brief's § 8.4 set: the changed screens, plus the specs whose order and filter-row
  tests § 8.3 names): 112 passed, 2 skipped, in 113 s.
- Browser, **whole suite at Normal** (`tooling/run-e2e-tests.bat`, once): 345 passed, 15 skipped, **2 failed**,
  in 224 s. The two failures are the S048 changelog tests on desktop-chromium (§ 5). Every S082, equipment,
  lessons and screens test passed. Not run again: no code changed after it.

## Docs updated

- `docs/Plan.MD` § 4.1: the bullet *Under contract on the machine* (the card, its place, its texts, the filter).
- `.claude/CLAUDE.md` § SMTW-Review, *Contract fields by key (S080)*: the S082 sentence (the card route through
  `_contract_out` and `_CARD_KEYS`; the filter at `sites_holding(cur, "contract:read_basic")`).
- `docs/steps/device-checks.md`: row 59.
- `docs/schema/`: none, because S082 has no migration; `tooling/schema-docs.bat check` exits 0.
- `docs/Keycloak.md`, `backend/example_secrets_app.py`, `docs/Maintenance-Philosophy.md`, `docs/Plant-Facts.md`:
  none, because no role, client, secret, rule or plant fact changed.

## Fix round 1

Run name `YANTRA_TEST_RUN=s082c2`.

- **CR1-01 (minor) — Fixed.** The call-out `tel:` link in `UnderContractCard.vue` now has `d-inline-block tap-target`, as *Open contract* has, so its `min-height: 44px` applies. The first S082 test in `frontend/e2e/contracts.spec.js` now asserts the link's `boundingBox().height` is at least 44. Fails without the fix: `Expected: >= 44, Received: 21` (phone-chromium, the test alone); passes with it.
- **CR1-02 (nit) — Fixed.** `isEnded` in `frontend/src/utils/contractLabels.js` is now exported; the card takes `ended` from it, and `v-if="r.call && !r.ended"` is `v-if="r.call"` (`callLine` already returns `null` for an ended item).

Tests: frontend unit 397 passed; `npx vite build` built (only the known chunk-size warning); browser targeted `contracts.spec.js` + `screens.spec.js`: 44 passed, 1 skipped (all three projects of the Normal level). No whole-suite run, by the fix-round rule.

Docs updated: none, because the change is a CSS class, one export and a test assertion; no behaviour, key, schema or text changed.

### Feedback (fix round 1)

- none

## Feedback

- hindrance: after the reboot Docker Desktop was not running, so the resumed run stopped and handed back for the
  user to start it (one hand-back and a wait; `run-backend-tests.bat` printed "Is the dev DB up?").
  idea: a resume prompt after a reboot could confirm "Docker Desktop and the dev DB are up" before spawning.
- hindrance: the whole browser suite is red on HEAD because of a test outside the step (`changelog.spec.js`,
  after release v0.1.14's empty section), so a step's Normal run cannot be fully green (2 failures in a 224 s run).
- hindrance: `tooling\schema-docs.bat check` (194 s for "4 passed") and `run-tests.bat` passed the Bash tool's
  3-minute mark and were moved to the background, which split the result reading over several turns.
