```
Step: S085 — Contract renewal
Doc: brief-review s1
Author: Brief reviewer (Fable)
Date: 31-10-2026
```

Reviewed against: d216f48 + uncommitted S079, S080, S081, S082, S083, S084

# S085 — staleness review s1

**Verdict: no blocker or major finding. The brief's design and KLA's two gate-B decisions (BR1-01, BR1-02)
still hold against the code of S079–S084. Two minor findings name helpers that now exist and that the brief
plans around; five nits update wording.** Facts file read: `scratch/brief-facts-S085.md` (re-run today). S084
is in code review: BS1-06 and BS1-07 depend on its names as coded now (`alerts._RENEWED`,
`alerts.contract_renewed`, `TestRenewed._renewal`).

## Minor

### BS1-01 — minor — § 5.8 steps 1–2 and § 3 plan inline what `_lock_contract` now does

- **Problem.** S081 added `contracts._lock_contract(cur, contract_id, key=EDIT)` (`backend/contracts.py:446`):
  `SELECT * FROM contracts WHERE id = %s FOR UPDATE`, 404 when missing or `contract:read_basic` not held at the
  site, `require_perm_at(key, site)` 403, and it returns the locked row. That is exactly § 5.8 steps 1–2. The
  brief does not name it; § 3 lists only `lock_contract_for_change` from S083 as "not used".
- **Why it matters.** A coder that follows § 5.8 as written writes the same three statements a fourth time
  (the three line writes and `lock_contract_for_change` already call `_lock_contract`). CLAUDE-COMMON § DRY.
- **Fix (recommended).** § 3, in the S081 bullet: add `_lock_contract(cur, contract_id, key=EDIT)`. § 5.8: steps
  1–2 become "`locked = _lock_contract(cur, contract_id)` (the old contract FOR UPDATE, first; 404, 403), then
  `active` from the locked row → 409". No design change.

### BS1-02 — minor — the detail is built in `_detail`, and the columns live in `_CONTRACT_COLUMNS`

- **Problem.** Since S082 (its BS1-01) the detail has one builder, `_detail(cur, row, flags, today)`
  (`backend/contracts.py:252`), called by `get_contract` and by `_answer` (every write's answer). The brief's § 6.1
  gains (`renewal_of`, `renewed_by`, `can_renew`, `renewal`) are described as an extension of
  `GET /api/contracts/<id>` and of "`_answer` on the new contract (S081's detail)"; `_detail` is never named. Also
  `_CONTRACT_SELECT` is now `_CONTRACT_COLUMNS + _CONTRACT_FROM` (`contracts.py:105–116`), and `_CARD_SELECT`
  (S082) reuses `_CONTRACT_COLUMNS`; § 6.1 says "`_CONTRACT_SELECT` gains `s.active AS site_active`".
- **Why it matters.** A coder that adds the four keys in `get_contract` leaves the renewal's own 201 answer and
  every line write's answer without them, and the page's `can_renew` would go stale after an *Add machine*. The
  `site_active` column must go into `_CONTRACT_COLUMNS` so the list, the card and the detail all carry it, and
  `_contract_out` must drop it on every path (it does today for `renewal_of_id` and the markers; the brief says
  so).
- **Fix (recommended).** § 3 (S081/S082 bullet): add `_detail(cur, row, flags, today)` and `_CONTRACT_COLUMNS`.
  § 6.1: "`_detail` calls `_renewal_links` and `_renewal_offer`, so the GET and every write's answer carry them;
  `_CONTRACT_COLUMNS` gains `s.active AS site_active`, which `_contract_out` deletes". `_renewal_offer` needs the
  flags' `can_edit` (`_SiteFlags.at` gives it) and the lines `_detail` already read. No design change.

## Nits

- **BS1-03** (nit) § 3 Frontend and § 5.7 "Reload on a new `:id`": `ContractView.vue:70` already has
  `watch(() => route.params.id, load, { immediate: true })` and `load()` clears the old contract on an id change
  (lines 45–68). Drop the reload from the Where list; the page's changes are the button, the chain lines and the
  dialog. The `:key="contract.id"` pattern the brief follows is at line 234.
- **BS1-04** (nit) § 3 Backend: `SCRAPPED` and `write_events` are already imported in `contracts.py` (lines 88–89,
  S081); "Imports …" becomes "uses the imported …".
- **BS1-05** (nit) § 3 (from S083): `lock_contract_for_change` does not "read `id, site_id` only"; it calls
  `_lock_contract` (`SELECT *` FOR UPDATE, 404, `key` 403) and then `require_perm_at(READ_COST, …)`
  (`contracts.py:576–581`). The `id, site_id` plain reads are `read_contract` and `read_contract_for_change`. The
  conclusion (not used: it demands `contract:read_senior`) holds; fix the reason.
- **BS1-06** (nit; depends on S084 as coded) § 4.1 "Kept test databases" and § 8.3 `test_contract_alerts.py`:
  S084's `TestRenewed` (`backend/tests/test_contract_alerts.py:212–234`) makes one renewal per test on its own
  `contract(60)` through `_renewal(…, active)`; no test inserts two renewals of one contract, so no kept worker
  database holds rows v47 refuses and no S084 test changes. Both bullets become "none found; the S084 tests set
  `renewal_of_id` through `db_rows` after S080's `POST`, which S085 still ignores, so they stay green". Likewise
  § 8.3's first bullet: no test in `test_contracts_api.py` or `test_contract_equipment_api.py` compares a whole
  detail to a fixed key set (`test_contract_card_api.py:100` compares the card item, cut to `_CARD_KEYS`, which
  the gains do not touch).
- **BS1-07** (nit; depends on S084 as coded) § 5.6 and § 4.1: S084's rule is the SQL fragment `alerts._RENEWED`
  (`alerts.py:431`, `EXISTS (… r.renewal_of_id = {id} AND r.active = 1)`), shared by `contract_renewed(cur,
  contract_id)` (line 472) and `read_alert_contract`; the task re-checks it through
  `alerts_core.should_send_contract`. Name `_RENEWED` beside `contract_renewed` in § 3 and § 5.6. The
  `ix_contracts_renewal_of` mentions to update after v47 are: the `alerts.py` docstring (lines 35–37, the gap-lock
  sentence) and `docs/schema/notes.json` (the brief has it); `local_db.py` v43 and `test_migration_v43.py` keep the
  old name on purpose.

## BR1-01 and BR1-02 (KLA's decisions at gate B)

The code changes neither decision's options:
- **Q1 (read-only once renewed or ended):** S080's `PUT`, S081's three line routes and S083's document routes
  refuse nothing by state (`change_price` and `remove_machine` say "Allowed on an inactive contract (BR1-03)";
  `documents.py:41–42` "an ended or inactive contract takes and loses documents"). Option (a) is the code as it is;
  option (b) would still touch the three steps' routes.
- **Q2 (one renewal ever, by a unique key):** `_RENEWED` counts only an **active** renewal, and S080's `PUT` lets a
  renewal go inactive and active again with no check across rows. So (a) v47 plus the way-out line is consistent
  with S084 as coded; (b) would still need the cross-row check in `PUT`.

## Checked and found consistent

- Migration number: `_MIGRATIONS` ends at v46 (`local_db.py:1523`), `LATEST_VERSION` = 46; **v47 is next**. v43
  defines `KEY ix_contracts_renewal_of (renewal_of_id)` and `fk_contracts_renewal_of` (`local_db.py:1457–1460`);
  `test_migration_v46.py` slices `range(20, 46)` / `range(20, 47)`, the pattern § 8.1 copies; `_keys` and
  `_foreign_keys` are in `test_migration_v36.py:32–40` with the shapes the brief expects.
- `contracts.py`: `_SiteFlags.at(site_id)` (`can_edit`, `can_read_callout`, `can_read_cost`, the two document
  flags); `_contract_out(row, flags, today)` deletes `renewal_of_id`, `first_reminder_for`, `second_reminder_for`
  and the gated fields; `_contract_row`, `_answer(cur, contract_id)`, `_drop_gated(clean, site_id, fields)`,
  `_check_rules(clean, stored)`, `_machine_lines(cur, contract, flags)` (orders by `e.code`; gives `lifecycle`,
  `site_code`, `at_contract_site`); `READ_BASIC`, `READ_CALLOUT`, `READ_COST`, `EDIT`; `UNIQUE_KEY_ERRORS.update`
  with `(field or None, message)` (`api_common.py:25–26`, so `(None, "…")` is the documented shape);
  `create_contract` / `change_contract` as § 5.8 describes them.
- `contracts_core.py`: `validate_contract(body, creating)` pops `active` on a create, `setdefault`s each of
  `REQUIRED` (holds `site_id`) to None, ignores unknown fields (`renewal_of_id`); the site's message is
  `_choose_text("Site")` = "Choose a site." (`masters_core.py:140–148`); `DATE_MAX` = 2099-12-31;
  `SITE_INACTIVE`; `event_text(contract)`; `SCRAPPED = "scrapped"` (`equipment_core.py:19`).
- `masters.check_active_vendor(cur, vendor_id)` (`masters.py:1301`): LOCK IN SHARE MODE, the two texts § 5.5
  quotes, 400 `vendor_id`.
- Permissions: `contract:edit` = `maint_engineer`, `it_admin`; `maint_manager` includes `maint_engineer`
  (`config_rbac.ROLE_INCLUDES`), so "engineers, managers, IT admin" holds; all four keys in `SITE_SCOPED`;
  `auth_utils.sites_holding(cur, key)` and `require_perm_at(key, site_id, field=None)` as cited. No new key.
- LOCK ORDER notes: `contracts.py:29–74`, `equipment.py:69–78` and `alerts.py:20–38` all carry S084's sentence
  "every route holds at most one contract row, taken first, so no cycle", the one § 5.8 rewrites;
  `documents.py:52–60` (the contract row through `lock_contract_for_change`, then only `equipment_documents`)
  needs no change. S080 create: site and vendor shared, no contract lock; S081: the contract first, then a line
  FOR UPDATE or the node (1) shared; S083: the contract first; S084 scan: `lock_contract_for_scan` in id order,
  `contract_renewed` plain by design (the gap-lock reason).
- § SMTW-Review: *Contract fields by key (S080)* with R02.2's lines, and *Contract reminders (S084)* are in
  `.claude/CLAUDE.md`; § 8.6's point fits beside them.
- Frontend: `ContractsPanel.vue` holds `EMPTY` (line 84), the dialog's fields 1–13 with the ids
  `contract-*`, `chosenSite` (line 117) and `chosenSite?.code` on edit (line 248), `vendorOptions` with the
  stored inactive vendor first, `toBody: (f) => contractBody(f, chosenSite.value)`, `ActiveToggle` in the footer;
  `contractLabels.contractBody(form, site)` sends `callout_number` / `cost_note` only with the site's flags;
  `stores/masters.ensureVendors({ refresh })`; `ContractMachineDialog.vue` is the `useFormModal` pattern with a
  fixed `path` per contract and the parent's `:key`; `useFormModal` calls `blank()` once at set-up and
  `blank(seed)` in `openCreate(seed)`, `editingId` null → POST; `FormModal` emits `closed` after the fade
  (line 125) and `LessonDialog.onClosed` is the hand-off pattern; `MeterFormFields.vue` uses `defineModel`;
  the route `name: "contract"`, path `/contracts/:id(\d+)`.
- Browser tests: `contracts.spec.js` has `contractByApi(vendor, title, fields, key)`, `vendorByApi`, `siteId`,
  `callAs`, `day(offset)`, `shown(iso)`, `openContracts`, imports `createEquipment` from `equipment.spec.js`,
  `expectDialogFits` and `expectFieldMessage`; the seed persons `engineer`, `manager`, `operator`, `it_admin`,
  `admin`. The labels § 8.3 names are in the spec's lines the facts file lists. Untagged tests, a targeted run
  with `contracts.spec.js`, `masters.spec.js` and `screens.spec.js`: the settings' convention.
- Docs: `notes.json`'s `contracts` line has "`renewal_of_id` (→ `contracts`, always NULL until R02.4)" and ends
  "`ix_contracts_renewal_of`"; Plan.MD § 2 item 9 has "Renewal makes a new record linked to the old one."; both
  as § 3 quotes them.

## Feedback

- waste: the facts file (385 lines) spends about 200 lines on column names the brief uses as table fields
  (`site_id`, `from_date`, `equipment_id`, `created_by`, `to_date`, …: "defined at none found", 12–53 files
  each); the lines that decided anything were the *not found* list and the eight contracts.py names
  (`scratch/brief-facts-S085.md:110–235`).
- idea: in staleness mode the facts run could mark each cited name with "new since `Baseline:`" (from
  `git diff <baseline> --stat` plus the untracked files), so the reviewer opens only those; this run read
  `contracts.py` whole (581 lines) to find the three helpers S081–S082 added (`_lock_contract`, `_detail`,
  `_CONTRACT_COLUMNS`), which the brief could not have named.
