```
Step: S081 — Machines on the contract
Doc: brief-review s1
Author: Brief reviewer (Fable)
Date: 30-10-2026
```

Reviewed against: d216f48 + uncommitted S079, S080

# S081 — Staleness review s1

**Verdict: no `blocker` or `major` is open.** The brief was written against S079's and S080's briefs; both
are now coded (`refs/steps/S079` = 73f0bc5, `refs/steps/S080` = 31484e6, both uncommitted). Every
design statement and every decision KLA's delegation approved still holds. Two names the brief cites from
S080 differ from the code (one signature, one function that does not exist), and S080 coded a gating
helper the brief should reuse. Both are `minor`: the brief's wording changes, the design does not.

The one question asked: does each statement of the brief about S079/S080's code still hold? I read the
brief's § 3, § 4.1, § 5.4, § 5.5, § 5.7, § 5.8, § 6, § 8 and A1 against `backend/contracts.py`,
`backend/contracts_core.py`, `backend/config_rbac.py`, `backend/local_db.py` (v42, v43, the latest
`MODIFY event`), `backend/equipment.py` (the LOCK ORDER bullet, `NODE_JOINS`, `accessible_unit_ids`,
`write_events`, the list's `site_id` filter), `backend/masters.py` (`check_active_vendor`),
`backend/api_common.py`, `backend/db_helpers.py`, `backend/auth_utils.py` (`require_perm_at`),
`backend/tests/conftest.py`, `backend/tests/test_contracts_api.py`, `backend/tests/test_rbac.py`,
`backend/tests/test_migration_v41.py` / `_v43.py`, `frontend/src/views/masters/ContractsPanel.vue`,
`frontend/src/utils/contractLabels.js`, `frontend/src/components/EquipmentPicker.vue`,
`frontend/src/composables/useFormModal.js`, `frontend/e2e/contracts.spec.js`, `tooling/e2e/seed_e2e.py`,
`docs/Plan.MD`, `.claude/CLAUDE.md`, and S080's impl report. No facts file was given for this round; the
one in `scratch/brief-facts-S081.md` is from round 1 (before S080 was coded: it reports `contracts.py`
as "no such file"), so I checked the S079/S080 names in the code directly.

## Findings

### BS1-01 — minor — `_contract_out` has three arguments and `_fetch_contract` does not exist

**Problem.** § 3 and A1 cite S080's `_contract_out(row, flags)` and `_fetch_contract`. The code
(`backend/contracts.py`) has:
- `_contract_out(row, flags, today)` — the third argument is today's IST date, for `contract_status`;
- no `_fetch_contract`. The joined read is `_contract_row(cur, contract_id)` (`_CONTRACT_SELECT` with
  the site code and the vendor's name and `active`), and a write's answer is `_answer(cur, contract_id)`,
  which calls `_contract_row` then `_contract_out(row, _SiteFlags().at(site_id), _today())`.

**Why it matters.** The coder would look for a function that is not there, and § 6.1's detail (the
machines, the total) has two call sites to extend, not one: `get_contract` and `_answer` (the answer of
S080's `PUT` and of S081's three line writes). The brief's "each write answers with the contract detail
(§ 6.1)" is right, and `_answer` is the place.

**Options.**
- (a) **Recommended.** In § 3 and A1 write `_contract_out(row, flags, today)`, `_contract_row(cur,
  contract_id)` and `_answer(cur, contract_id)`; in § 6.1 say the machines, `machine_count`,
  `price_total` and `priced_count` are added in one place both `get_contract` and `_answer` call (e.g.
  `_detail(cur, row, flags)`), so S080's `PUT` answer also carries them.
- (b) Leave the names and let the coder find them. Costs a search and risks a detail built in one of the
  two call sites only.

### BS1-02 — minor — S080 coded one gating mechanism; the brief's price drop should use it, not a parallel `if`

**Problem.** § 5.4 says the add route "drops `price` from the clean fields when the user lacks
`contract:read_senior` at the contract's site, as S080 drops `cost_note`", without naming how. S080 coded
the drop as one mechanism: `contracts_core.GATED_FIELDS = {"callout_number": "contract:read",
"cost_note": "contract:read_senior"}` and `contracts._drop_gated(clean, site_id)`, which deletes each
field of `GATED_FIELDS` the writer may not read. S080's impl report § 4 says "`_drop_gated` uses it, and
so will R02.2's prices", and `.claude/CLAUDE.md` § SMTW-Review *Contract fields by key* names
`_drop_gated` as the one write-side rule.

**Why it matters.** A second `if not has_perm_at(READ_COST, site): del clean["price"]` beside
`_drop_gated` is the planned duplicate the review rules call `minor`, and the SMTW-Review point would
then name a helper the price does not go through.

**Options.**
- (a) **Recommended.** § 3 (`contracts_core.py`): add `LINE_GATED_FIELDS = {"price":
  "contract:read_senior"}`; § 3 (`contracts.py`): `_drop_gated(clean, site_id, fields=GATED_FIELDS)`
  gains the `fields` argument, and the add route calls `_drop_gated(clean, site_id, LINE_GATED_FIELDS)`.
  § 8.6's SMTW-Review text names `_drop_gated` for the line's price as well.
- (b) Add `"price"` to `GATED_FIELDS` itself. Simpler, but `validate_contract` never yields `price`, so the
  contract writes would carry a dead entry, and the dict's docstring ("the fields only some readers see")
  would mix a contract field with a line field.
- (c) Leave it to the coder: a parallel check is the likely outcome.

## Nits

- **BS1-03** (nit) § 3 `backend/contracts.py`, § 5.5: contracts.py's own docstring needs more than the
  LOCK ORDER paragraph rewritten. Its first paragraph ends "The machines covered and their prices are
  R02.2's."; its ACCESS paragraph names only `callout_number` and `cost_note`; its no-cycle list says "no
  other module touches contracts" and "only this module's PUT locks it". Add to § 3: the docstring's first
  paragraph, the ACCESS paragraph (the price and the total) and the no-cycle list are rewritten too.
- **BS1-04** (nit) § 8.3, first bullet: no S080 test compares a whole contract item to a fixed key set.
  `test_contracts_api.py` checks only absent keys (`"cost_note" not in item`, lines 86, 104, 313) and a
  subset of the sent fields (line 168). Say so: S080's API tests stay green; nothing to update there.
- **BS1-05** (nit) § 8.1: the nearest pattern is now `test_migration_v43.py` (`range(20, 44)`, the same
  shape as v41's). Either name is fine; naming v43 saves the coder a comparison.
- **BS1-06** (nit) § 3, S080 line: the panel's dialog state is `useMasterForm` with a module constant
  `EMPTY` (`ContractsPanel.vue:80`), not `useFormModal`. S081's new dialog uses `useFormModal` directly,
  as § 5.7 says; that is right (`useFormModal` has `afterSave`, `useMasterForm` reloads a list). No
  change needed in § 5.7; one clause in § 3 ("the panel's own form goes through `useMasterForm`") stops
  the coder from copying the panel's wiring into the dialog.

## Checked and found consistent

- **Keys and `SITE_SCOPED`** (`backend/config_rbac.py`): the four `contract:*` keys exist with the
  brief's holders (`read_basic` every role; `read` engineer; `read_senior` manager; `edit` engineer and
  IT admin); all four are in `SITE_SCOPED`; `test_rbac.py::test_contract_keys` pins them. § 8.3's "no
  new key" holds.
- **Migrations**: v42 (vendors) and v43 (contracts) are the last entries of `_MIGRATIONS`, so **v44 is
  next**; `LATEST_VERSION = _MIGRATIONS[-1][0]`, so `test_modules.py` needs no edit. v43's DDL has every
  column § 5.7's Terms card names (`contract_number`, `covered_text`, `not_covered_text`,
  `pm_visits_per_year`, `response_hours`, `only_vendor_repairs`, `callout_number`, `cost_note`, `notes`,
  `renewal_of_id`, `active`), `title VARCHAR(100)` (§ 5.3's "at most 137" holds), and `contracts (id)` for
  the brief's foreign key.
- **The ENUM list** § 4.1: the latest `MODIFY event` is v33's (`local_db.py:1030`), and its list is the
  brief's twelve kinds word for word; no later migration changed it. `equipment_events.new_value` is
  `VARCHAR(200)`.
- **`_sites_holding(cur, key)`** exists in `contracts.py` and returns site rows (`id, code, name,
  active`) ordered by code; `_SiteFlags.at(site_id)` gives exactly `can_edit`, `can_read_callout`,
  `can_read_cost`; `_contract_out` merges them into every item, so the page gets `can_edit` and
  `can_read_cost` from the detail. The list answer's `sites` carry `can_read_cost` (§ 5.8).
- **`contracts_core`**: `CONTRACT_TYPES = ("warranty", "amc", "cmc", "on_call")` (the brief's
  `TYPE_SHORT` keys match); `contract_status(from_date, to_date, today)` as cited; `GATED_FIELDS` exists
  (BS1-02).
- **Lock pattern**: S080's `change_contract` takes `SELECT * FROM contracts WHERE id = %s FOR UPDATE`
  first, then `has_perm_at(READ_BASIC)` → 404, `require_perm_at(EDIT)` → 403, exactly § 5.5's steps 1–2.
  `require_perm_at` answers "You can't do this at {code}" (§ 5.4's text). `check_active_vendor(cur,
  vendor_id)` takes the vendor `LOCK IN SHARE MODE`, as the brief's equipment.py bullet says.
- **equipment.py's S080 bullet** reads "contracts.py (S080) locks at most one contracts row FOR UPDATE
  (PUT), first in its transaction, then the vendor row LOCK IN SHARE MODE when the vendor changes; a
  create takes the site and the vendor LOCK IN SHARE MODE. It locks no equipment, unit, ticket,
  improvement or procedures row …". § 5.5's replacement text supersedes it correctly (the node is now
  taken shared). `.claude/CLAUDE.md` self-check (2) already lists `contracts.py` among the lock notes.
- **equipment.py helpers**: `NODE_JOINS` joins `units u ON u.id = COALESCE(gp.unit_id, p.unit_id,
  e.unit_id)` then `sites s` (§ 5.2 rule 4's text is exact); `accessible_unit_ids(cur, key="equipment:read")`
  returns `None` for every unit (§ 6.1's `can_open`); `write_events(cur, equipment_id, changes)` takes
  `(event, old, new)` triples and stamps `actor()` (§ 5.3); the equipment list filters by `site_id`
  (`equipment.py:591`), so the picker's `site_id` needs no backend change.
- **`insert_row(cur, table, clean, actor)`** and **`update_row(cur, table, record_id, clean, actor)`**
  (`db_helpers.py`) match § 5.5; `row_to_dict` leaves a `Decimal` for Flask to serialise as a string
  (§ 6.1). `UNIQUE_KEY_ERRORS` is a module dict filled at import (§ 4.1).
- **`conftest.py`**: `make_site`, `make_unit`, `make_vendor(**fields)`, `make_equipment(parent=…)`,
  `user_at_sites`, `uniq`, `db_rows`, `db_down` all exist; `_TABLES` starts with `"contracts"`, so
  `contract_equipment` goes in front of it (§ 3).
- **`ContractsPanel.vue`**: the title cell is `<div class="fw-semibold">{{ c.title }}</div>`, with the
  phone line under it; the columns from `md` are Type, Vendor, Site, From, To, so *Cost before GST* fits
  the same `d-none d-md-table-cell` pattern (§ 5.8). The empty text is now CR1-01's "No contracts in force
  or starting later." (S081 does not cite the old text).
- **`contractLabels.js`** exports `contractTypeLabel`, `statusBadgeClass` (cited) and `contractBody(form,
  site)`; none of § 3's new names (`formatRupees`, `coverageLines`, `responseText`, `overlapText`,
  `lineBody`) collides.
- **`useFormModal({ path, blank, fromRecord, afterSave, toBody = (form) => form, label })`** returns
  `editingId`; `toBody(form.value)` is called with one argument; `afterSave(result)` runs after
  `modal.close()`; the `PUT` path is `${path}/${editingId.value}`. § 5.7's wiring (BR1-01) holds as
  written.
- **`EquipmentPicker.vue`**: no props today; `emit('pick', e.id)`; empty text "No equipment found at your
  units."; the search sends `level=all&q=&per_page=20`. § 5.7's picker changes are additive as stated.
- **`contracts.spec.js`** helpers: `day`, `shown`, `callAs`, `vendorByApi`, `siteId`, `contractByApi(vendor,
  title, fields, key)`, `openContracts(page, key)`, `row`, `fillNewContract`. The e2e seed has sites
  `SMTW` and `BRICKS` (a `BRICKS.FILTER` unit with a node), `engineer` at SMTW only and `manager` at both,
  so § 8.4's tests (another site's machine, the manager-only cost) have their fixtures.
- **Docs**: `docs/Plan.MD:48` is § 2 item 9 (the price per machine and the overlap warning are there);
  § 3 has the contract keys' paragraph; `.claude/CLAUDE.md` § SMTW-Review has *Contract fields by key
  (S080)* for § 8.6 to extend.

## Feedback

- waste: the facts file in `scratch/brief-facts-S081.md` is round 1's, made before S080 was coded, so it
  says "no such file" for every S080 file; a staleness round would save a dozen greps if the orchestrator
  re-ran `tooling/step-brief-facts.bat S081` first (about 5 min of reads here)
- idea: `step_snapshot.py diff S079 --stat` lists S080's files too (`contracts.py`, `ContractsPanel.vue`,
  …), so the two snapshots' file lists cannot be told apart from the tool alone; a `--only` that stops at
  the next step's snapshot would give each step its own list
