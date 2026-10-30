```
Step: S082 — Under contract on the machine
Doc: brief-review s1
Author: Brief reviewer (Fable)
Date: 30-10-2026
```

Reviewed against: d216f48 + uncommitted S079, S080, S081

# S082 — Staleness review s1

**Verdict: no `blocker` or `major` is open.** The brief's design holds against S079, S080 and S081 as coded; two `minor` findings and five nits fix wording and names only. The facts file `scratch/brief-facts-S082.md` was made before the three steps were coded, so it says "no such file" for every contract name; I checked those names in the code directly.

**What I compared.** The brief's statements about the code of S079–S081 (the names the orchestrator listed) against the working tree now: `backend/contracts.py`, `backend/contracts_core.py`, `backend/equipment.py`, `backend/auth_utils.py`, `backend/local_db.py` (v44), `backend/tests/conftest.py`, `backend/tests/test_contract_equipment_api.py`, `frontend/src/utils/contractLabels.js`, `frontend/src/views/ContractView.vue`, `frontend/src/views/EquipmentDetailView.vue`, `frontend/src/views/equipment/LessonsCard.vue`, `frontend/src/views/EquipmentView.vue`, `frontend/src/utils/assetList.js`, `frontend/src/router/index.js`, `frontend/e2e/contracts.spec.js`, and the impl reports of S080 and S081. S081's fix round in progress changes only the *Save price* label (`ContractMachineDialog.vue` and one spec line) and renames its test module's `engineer` override to `site_engineer`; S082 relies on neither.

## Findings

### BS1-01 — minor — § 5.1: the alias `ce` is already taken in S080's select fragment

**Problem.** § 5.1 says the card query is "S080's contract select fragment (the one its list and `_fetch_contract` use …) joined to `contract_equipment ce`". As coded (S081 § 4, the sums departure), the fragment is `_CONTRACT_SELECT`, used by `list_contracts` and `_contract_row` (there is no `_fetch_contract`), and it already ends with a grouped `LEFT JOIN (SELECT contract_id, COUNT(*) …, SUM(price) AS price_total FROM contract_equipment GROUP BY contract_id) ce ON ce.contract_id = c.id`. A second `JOIN contract_equipment ce` is a duplicate alias: MariaDB refuses the statement.

**Why it matters.** The coder who follows the brief's text gets an SQL error on the first test run and has to pick an alias alone. The row shape also changed: every row of the fragment now carries `machine_count`, `priced_count` and `price_total`; `_contract_out` deletes the last two only without `can_read_cost`, so the cut to § 5.2's keys is what keeps them out of the card for the manager, and § 5.2 should say so.

**Options.**
- (a) **Recommended.** In § 5.1 name the fragment `_CONTRACT_SELECT` (used by `list_contracts` and `_contract_row`) and join the lines as `JOIN contract_equipment cl ON cl.contract_id = c.id` with `cl.equipment_id IN (…)`; each row carries `cl.equipment_id`. In § 5.2 add: "the row also carries `machine_count`, `priced_count` and `price_total` (S081); the cut to the keys above leaves them out for every reader."
- (b) A separate select for the card, without the sums subquery. One more copy of the join to `sites` and `vendors`; rejected (DRY, and B2 wants the row shape `_contract_out` expects).

### BS1-02 — minor — § 8.2: "the engineer" of the card API tests cannot be the conftest `engineer` fixture

**Problem.** § 8.2 says "a technician of the site … ; the engineer: `callout_number` present" and lists `user_at_sites` among the fixtures without saying which client each role is. The conftest `engineer` fixture is `role_client("maint_engineer")`, an X-Test-Role identity with a wildcard membership whose `all_units` is false, so it holds no unit (S081 impl report § 4 and its feedback). The card route goes through `load_node_for_user`, which answers 404 for a node outside the user's units, so every card test with that fixture fails with 404. S081's test module now names its own `site_engineer` from `user_at_sites` for the same reason.

**Why it matters.** S081's coder lost about 5 minutes and one run on exactly this; the brief's test plan rests on the fixtures as coded.

**Options.**
- (a) **Recommended.** In § 8.2 state: "the technician, the engineer and the manager are `user_at_sites([(site, role, "all")])` clients at the test's site (the X-Test-Role `engineer` fixture holds no unit and gets 404 from `load_node_for_user`; S081 § 4)". The equipment-list tests in `test_equipment_api.py` use the same clients for the `contract` filter.
- (b) Leave it to the coder. Rejected: a known trap with a one-line fix.

## Nits

- **BS1-03** (nit) § 3, § 5.2: `_contract_out` is `_contract_out(row, flags, today)` since S081 (`today` from `contracts._today()`, `flags` from `_SiteFlags().at(site_id)`); the brief writes `_contract_out(row, flags)`. Update both places; the card route passes `_today()` once and uses it for `card_items` too.
- **BS1-04** (nit) § 3 Backend: `_sites_holding`'s callers are `list_contracts` (the list and its `sites`) and `_detail`, which hands the site ids to `_overlaps(cur, contract, lines, site_ids)`; `_overlaps` itself makes no call. Name `_detail` instead of `_overlaps`.
- **BS1-05** (nit) § 5.4 API: `enum_arg` refuses any value not in the tuple, an empty one included (`?contract=` → 400), so "empty or absent = no filter" does not hold; the screen never sends an empty value (`listUrl` skips falsy keys). Write "absent = no filter; any other value, empty included, → 400, as `tickets`". (Not a staleness point.)
- **BS1-06** (nit) § 3 Frontend: the *Tickets* select's `TICKET_FILTER_CHOICES` lives in `utils/ticketLabels.js`, not in `equipmentFilters.js`; by that pattern `CONTRACT_FILTER_CHOICES` belongs in `contractLabels.js`, tested in `contractLabels.test.js`, which drops `equipmentFilters.js` and its test from § 3 (one file fewer). A judgement for the orchestrator; either place works. (Not a staleness point.)
- **BS1-07** (nit) § 3 Docs, § 8.6: the SMTW-Review point is headed *Contract fields by key (S080)*; S081 extended its text, not its heading. Write "(S080)" or "the point S081 extended".

## Checked and found consistent

- `contract_equipment` (v44): `contract_id`, `equipment_id`, `price`; `uq_contract_equipment`; `KEY ix_contract_equipment_equipment (equipment_id)`.
- `load_node_for_user(cur, node_id, for_update, key=None)` → `(None, node)` for a plain read; 404 for a missing node and one outside the user's units (`accessible_unit_ids`, default key `equipment:read`). The node row (`_NODE_COLUMNS`) carries `parent_id`, `p_code`, `p_name`, `gp_id`, `gp_code`, `gp_name`, `site_id`, so `via` needs no further query.
- `NODE_JOINS`: the parent alias is `p`, the grandparent `gp` through `p.parent_id`; `covered_sql`'s `IN (e.id, e.parent_id, p.parent_id)` fits `_NODE_FROM`.
- `list_equipment`: `tickets = enum_arg("tickets", tuple(_TICKET_FILTERS))` beside which the `contract` filter goes; `_list_filters(cur)` is the shared print set and has no `tickets`; `assetList.js` `FILTER_KEYS` has no `tickets`. `equipment.py` does not import `contracts.py`; `contracts.py` imports `IST`, `NODE_JOINS`, `accessible_unit_ids`, `node_path`, `write_events` from `equipment.py`, so the cycle B10 names is real.
- `EquipmentView.vue`: `FILTER_KEYS` (line 157) and `listUrl` (line 217) list `tickets`, skipped without `ticket:read` (`canSeeTickets`); the *Tickets* select has `aria-label="Tickets"` (line 371).
- `EquipmentDetailView.vue`: `LessonsCard` (its wrapper `order-0`), then the *Open tickets* card `order-0`, `DocumentsCards` `order-1 order-md-0`, the details row `order-2 order-md-0`; the docstring (lines 35–37) and the template comment (lines 238–239) name the order. The *Lessons* and `S064` order tests (`lessons.spec.js:258`, `equipment.spec.js:946`) hold with a card between *Lessons* and *Open tickets*; `equipment.spec.js:960` asserts `/^Filters \(2\)/` for a URL without `contract`.
- `LessonsCard.vue`: `props: { node }`, loads `/api/procedures?equipment_id=`, `watch(() => props.node.id, …, { immediate: true })`, error line "Lessons could not be loaded: {{ loadError }}", hidden with no rows unless `can_add`: the pattern B2 and § 5.3 copy.
- The node detail sends `permissions` from `permissions_at_site(node["site_id"])` (`equipment.py:696`).
- `contracts_core.contract_status(from_date, to_date, today)` → `{kind, label, days}`, kinds `upcoming`, `ended`, `ending`, `in_force`; `contractLabels.statusBadgeClass(kind)`; `coverageLines(contract)` → up to two lines with the brief's texts; `responseText(hours)` → "24 hours", "1 hour", `null`.
- `_SiteFlags().at(site_id)` → `{can_edit, can_read_callout, can_read_cost}`; `_contract_out` drops `renewal_of_id`, deletes `callout_number` without `can_read_callout`, and `cost_note`, `price_total`, `priced_count` without `can_read_cost`. `GATED_FIELDS`, `LINE_GATED_FIELDS` and `_drop_gated(clean, site_id, fields=GATED_FIELDS)` are write-side and untouched by S082.
- `_sites_holding(cur, key)`: `SELECT id, code, name, active FROM sites ORDER BY code`, kept where `has_perm_at(key, row["id"])`; `has_perm_at` asserts the key is in `SITE_SCOPED`; the four `contract:*` keys are in it (S080). No test references `_sites_holding`, so § 8.3 ("green, no change") holds for `test_contracts_api.py` and `test_contract_equipment_api.py`.
- `ContractView.vue` at `/contracts/:id(\d+)` (name `contract`, no nav item); a 404 shows "Contract not found, or not at your sites." with a link to the equipment list.
- `contracts.spec.js` helpers: `callAs`, `vendorByApi`, `siteId`, `contractByApi(vendor, title, fields, key)` (AMC at SMTW, `day(-30)` to `day(300)`), `machineByApi(name, unitCode = "SMTW.MCC1")` (a GA37), `lineByApi(contract, machine, price)`, `contractWithMachine(testInfo, { onIt, price })`, `day`, `shown`, `CALLOUT = "+91 00000 00000"`; it imports `card`, `saveDialog` and `expectNoSidewaysScroll`.
- conftest: `make_site`, `make_unit`, `make_vendor`, `make_equipment`, `user_at_sites`, `uniq`, `db_down` exist; `_TABLES` starts with `contract_equipment`, `contracts`. `test_improvements_api.py:654` patches `config_rbac.PERMISSIONS` with `monkeypatch.setitem`.
- LOCK ORDER: `contracts.py`'s note ends "Reads: plain, no lock"; `equipment.py`'s contracts bullet (lines 68–72) describes writes only. S082 adds reads, so § 5.7 "None" needs no note change.
- `docs/Plan.MD` § 4.1 *Equipment register* exists (line 257).

## Feedback

- hindrance: `git diff refs/steps/S081 -- backend frontend` against the working tree lists every untracked contract file as deleted (3818 lines), because untracked files are not in the diff; I compared file by file with `git show refs/steps/S081:<file> | diff -w - <file>` instead (1 run lost, 2 min).
- idea: `scratch/brief-facts-S082.md` predates the coding of S079–S081, so it says "no such file" for every contract name and listed nothing I could verify from it; before a staleness review the orchestrator could run `tooling/step-brief-facts.bat S0NN` again, so the facts file names where each dependency's code now is.
- idea: the staleness prompt did not say whether a facts file existed; I found it by `ls scratch/brief-facts-*`. The prompt could name it, or say it is stale.
