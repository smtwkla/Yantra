```
Step: S085 — Contract renewal
Doc: brief-review r1
Author: Brief reviewer (Fable)
Date: 30-10-2026
From: R02.4
```

Reviewed against: d216f48 + uncommitted S079, S080 (partial: `contracts.py`, `contracts_core.py`, `ContractsPanel.vue`, `contractLabels.js` and their tests are in the working tree; S081–S084 are approved briefs only)

# S085 — Brief review, round 1

**Verdict: no `blocker` or `major` finding. Three `minor` findings, two of them decisions for KLA (Q1 and Q2), and six nits.** The brief can go to gate A once the Review log answers them; KLA's two decisions are marked below.

Facts file used: `scratch/brief-facts-S085.md`. Every S080 name the brief marks "as coded" exists with the signature the brief gives; every S081–S084 name matches the approved brief it comes from (details under *Checked and found consistent*).

## Findings

### BR1-01 — minor — Q1 departs from the roadmap's "read-only once ended": KLA's own decision

**Problem.** R02.4 (approved at gate R) says "The old contract stays as it was, read-only once ended." The brief recommends Q1 (a): the old contract stays editable, and records the departure (§ 2, § 9 Q1). Gate A is delegated tonight, so this departure would pass without KLA seeing it.

**Why it matters.** It changes a gate-R sentence. The recommendation is, however, already the approved state: S080 § 5.1 ("An ended contract may be changed (a correction)") and S081 § 5.2 rule 1 (an ended contract takes adds) were approved on 30-10-2026, and S080 only said "R02.4 *may* make a renewed one read-only". Option (b) would touch S080's `PUT`, S081's three line routes and S083's document routes, with a way out for a real correction.

**Options.** (a) Keep editable, as the brief recommends; the orchestrator records in R02's log and Plan.MD § 2 item 9 that "read-only once ended" is dropped (ISO 9001 § 7.5.3 protects against *unintended* change; who/when columns record a correction) — **recommended**. (b) Read-only once renewed (not once ended): a 409 in S080's `PUT`, S081's writes and S083's writes when `renewed_by` exists, with "set the renewal inactive to correct the old contract" as the way out; a new step or an amendment to S080/S081/S083. **Mark for KLA at gate A or gate B:** the brief's text is right either way; only the decision is KLA's.

### BR1-02 — minor — An inactive renewal is a dead end on the old contract's page; and the split-quote case of S080 A4 is not answered: KLA's own decision (Q2)

**Problem.** With v47 (one renewal ever, E2), a renewal set inactive keeps its place: *Renew contract* stays hidden on the old page, which shows only "Renewed by: … (inactive)" (§ 5.5, § 5.7). Meanwhile S084 treats the old contract as not renewed and sends "Renew it or let it end" again (§ 5.6), but the engineer who opens the page cannot renew. The way out (show inactive in Masters › Contracts, reactivate the renewal, change its terms) is in § 5.5 and Q2 of the brief, not on the screen. Second, S080 A4 asked R02.4 to decide the split-quote case (D7: a mixed quote is two contracts; next year one contract may become two). E2 rejects "several renewals" in general but does not name that case or its workaround.

**Why it matters.** Use on the floor: a wrong renewal is the one case where the renewal flow is used twice, and the page gives no next step. A brief that leaves a flow's recovery off the screen is friction the coder cannot fix alone. The split case is a decision KLA asked for in S080 A4.

**Options.** (a) Keep v47 and show the way out: under "Renewed by: … (inactive)", for `can_edit` only, the line "To renew this contract again, set that renewal active in Masters › Contracts and change its terms." (scope B); and state in E2 that a contract split at renewal is one renewal plus a new contract whose notes name the old one — **recommended**. (b) Q2 (b): at most one *active* renewal, no unique key; `Renew` allowed when every renewal is inactive; a check in S080's `PUT` on reactivation across two contract rows (the brief's rejected design). **Mark for KLA:** (a) is inside D6; (b) changes the data model. The orchestrator may take (a) under the delegation and flag it at gate B.

### BR1-03 — minor — The renew dialog's vendor list, site code and empty form are not placed

**Problem.** § 5.7 says `ContractFields` in renew mode offers "the active vendors" with the inactive old vendor first, shows the site code as read-only text, and `renewalForm(contract)` builds "S080's form fields from the detail". Three sources are missing: (1) where `ContractRenewDialog.vue` gets the vendors (`ContractsPanel.vue` uses `ensureVendors()` from `frontend/src/stores/masters.js`; `ContractView.vue` is not a Masters view and loads nothing from that store today); (2) where the site code comes from in renew mode (the panel's edit mode reads `chosenSite?.code` from the list's `sites`, which the page does not have; the detail has `site_code`); (3) where S080's `EMPTY` form object lives once `renewalForm` in `contractLabels.js` needs it (today a `const` inside `ContractsPanel.vue`).

**Why it matters.** Each is a small decision the coder would take alone, and (3) is a copy of a 6-line constant if it is not moved (CLAUDE-COMMON § DRY).

**Options.** (a) State: the dialog calls `ensureVendors()` on open (`/api/masters/vendors?include_inactive=1`, `masters:read`, held by every role) and builds `storedVendor` from the detail's `vendor_id`, `vendor_name`, `vendor_active`; `ContractFields` takes a prop `siteCode` (the panel passes `chosenSite?.code`, the dialog `contract.site_code`) instead of deriving it from `sites`; `EMPTY` moves to `contractLabels.js` as `EMPTY_CONTRACT_FORM`, imported by the panel's `blank`/`fromRecord` and by `renewalForm` — **recommended**. (b) Let the page fetch the vendors and pass them as a prop; the rest as (a).

## Nits

- **BR1-04** (nit) § 8.2 `test_renew_needs_edit_at_the_site`: "operator at A → 403 naming A" cannot happen: an operator holds `contract:edit` nowhere, so `require_perm(EDIT)` answers the plain 403 before the route. The case that reaches "You can't do this at SMTW" is an engineer of site B who is operator at A. Fix the case.
- **BR1-05** (nit) § 5.8 step 8: `_machine_lines` (S081 § 6.1) orders by `code`; the node locks must be taken in `equipment_id` order. Say that the route sorts the lines by `equipment_id` before step 8's loop (or reads `equipment_id, lifecycle` itself and leaves `_machine_lines` to the answer).
- **BR1-06** (nit) § 3, § 5.4: `validate_renewal(body, creating)` has a `creating` argument that is always `True` (a renewal is a create); `clean_body(validator, creating)` passes it anyway. Say `validate_renewal(body, creating)` ignores `creating` and always validates as a create, or let the route call `clean_body(validate_renewal, creating=True)` and say so, so the coder does not wonder what `creating=False` means.
- **BR1-07** (nit) § 5.2: a contract that starts on a leap day, 29-02-2024 to 28-02-2025, is "not whole months" (`new_from` 01-03-2025, day 1 ≠ 29) and renews to 01-03-2025 → **01-03-2026**, one day longer than a year. Add it to `test_renewal_period_not_whole_months` as the stated behaviour, or treat "`from_date` is the last day of its month and `new_from` is a first" as whole months. Either; say which.
- **BR1-08** (nit) § 3 Docs: the `contracts` line of `docs/schema/notes.json` today says "`renewal_of_id` (→ `contracts`, always NULL until R02.4)" and "Indexes … `ix_contracts_renewal_of`". Both change (S085 fills it; the index becomes `uq_contracts_renewal_of`), not only the added clause.
- **BR1-09** (nit) § 5.7 notice: "Prices start empty: the managers of SMTW enter them on the new contract." reads oddly to the manager who is renewing. With `can_read_cost`: "Prices start empty: enter them on the new contract."; without: as written.

## Checked and found consistent

- **S080 names as coded** (`backend/contracts.py`, `backend/contracts_core.py`, working tree): `contracts_bp`, `_SiteFlags.at(site_id)` → `{can_edit, can_read_callout, can_read_cost}`, `_contract_out(row, flags, today)` (deletes `renewal_of_id`), `_answer(cur, contract_id)`, `_drop_gated(clean, site_id)`, `_check_rules(clean, stored)`, `create_contract`, `change_contract`, `READ_BASIC`, `READ_CALLOUT`, `EDIT`, the LOCK ORDER note; `validate_contract(body, creating)` (ignores unknown fields, `renewal_of_id` included; pops `active` on a create; `REQUIRED` holds `site_id`), `DATE_MAX` = 2099-12-31, `SITE_INACTIVE`; `masters.check_active_vendor(cur, vendor_id)` with exactly the two texts of § 5.5; `contractBody(form, site)` sends `callout_number` / `cost_note` only with the site's flags; `clean_body` raises the first of a list of `{field, message}`, so dropping the `site_id` entry works (E10).
- **S081–S084 names** against their approved briefs: `_machine_lines(cur, contract, flags)`, the detail's `machines` with `lifecycle`, `site_code`, `at_contract_site`, `event_text(contract)`, `write_events` and `contract_added` (S081 § 5.3, § 6.1); `lock_contract_for_change` reads `id, site_id` and checks `read_senior` (S083 § 5.1), rightly not reused; v46 `first_reminder_for`, `second_reminder_for`, `alerts.contract_renewed` = an **active** row with `renewal_of_id` (S084 § 5.2), the scan in id order and the "at most one contract row" sentence (S084 § 5.5); v47 follows v46 (S083 v45, S084 v46).
- **Migration v47**: MariaDB 11.4 (`tooling/dev/docker-compose.dev.yml`) accepts `ADD UNIQUE KEY IF NOT EXISTS` and `DROP INDEX IF EXISTS`; the unique key first keeps an index under `fk_contracts_renewal_of`; many NULLs pass; no precondition (nothing writes the column before S085; S084 A1); the kept-worker-database hedge is right (`conftest.py` empties `_TABLES` once per session, after the migrations run, so S084's two-renewal rows from an earlier run could meet v47); `test_a_fresh_database_gets_v43` keeps finding `ix_contracts_renewal_of` (it migrates `range(20, 44)`); `test_modules.py` reads `LATEST_VERSION`.
- **S084 interplay**: a saved renewal (active) stops the old contract's reminders; the new contract starts with NULL markers; a renewal set inactive re-arms the old contract; the unique key serves `contract_renewed`'s query; the comments naming `ix_contracts_renewal_of` are updated.
- **Lock order** (§ 5.8): old contract X → site S → vendor S → insert → nodes S in id order → inserts and events. Checked against `equipment.py` LOCK ORDER, S080 (create: site, vendor S; `PUT`: contract first), S081 (contract first, then node (1) S or a line row), S083 (contract first, then documents), S084 (contracts X in id order, then markers and `task_queue`), `masters.py` (site and vendor updates lock their own row, wait on no contract). The route never waits for a second existing contract row; the only cycle is the one the brief accepts (a move's (1) → (2) or a scrap's top-down subtree against the renewal's shared node locks, rolled back by 1213, nothing written). The plain renewal check (step 4) is sound: the snapshot is taken after the lock is granted, and every renewal of one contract locks it first.
- **D5, D8, D10 and S081 B3**: no price is copied for any renewer (D8 "for the contract period"; R02.4 "prices empty"); the cost note starts empty (D5, Q3); the call-out number follows `contract:read` and is copied by the route for a non-holder, never shown to them (D10, S080 § 5.4); no 403 and no silent price write, so B3's rule is not met and not broken. `renewal_of`, `renewed_by`, `renewal` carry no gated field.
- **Permissions**: `contract:edit` at the site (`config_rbac.py:166`: `maint_engineer`, `it_admin`; `maint_manager` implies `maint_engineer`, line 83); 404 for `read_basic` not held, 403 at the site; the button follows `can_renew`.
- **Frontend pattern**: `useFormModal` calls `blank()` once at set-up and `blank(seed)` in `openCreate(seed)`; `editingId` null → `apiPost(path)`; `FormModal` emits `closed` after the fade (S077 `LessonDialog.vue` `onClosed`); `watch(() => route.params.id, load, { immediate: true })` is the pattern of `EquipmentDetailView.vue:151`; `MeterFormFields.vue` uses `defineModel`.
- **Standards**: ISO 55001 § 8.3, ISO 9001 § 8.4 and § 7.5.3, ISO 27001 A.5.15 named and explained in plain words; the one departure (Q1) recorded.
- **Track full** (a migration, locks); **manual checks**: none on a device, right (a button, a dialog, a page); the five browser tests assert what the user sees; the three important ones are marked.
- **Scope B texts**: the 409 and 400 messages, the button, the title, the help lines read as one line each saying what is wrong and what to do; the vendor refusal reuses S079's text (one message for one refusal).

## Feedback

- waste: the brief cites S080–S084 by section (`S081 § 5.2 rule 2`, `S084 § 5.5`), so checking it meant reading about 400 lines across four 600–800-line briefs; a facts-file section that prints the cited sections of other steps' briefs (as *Cited lines* does for code) would have saved about 10 minutes.
- rule: the brief's header already carries a filled `Baseline:` line ("d216f48 + uncommitted R02 docs (S080 being coded) …"), while `docs/steps/README.md` § Stale brief check says the orchestrator copies the review's `Reviewed against:` there at approval; one of the two should say which text stands before approval.
- idea: `brief_facts.py` lists `defineModel`, `idPrefix`, `afterSave` as "defined at none found" though it lists their uses; a line "a Vue macro / a keyword argument, not a definition" would stop the reader checking them.
