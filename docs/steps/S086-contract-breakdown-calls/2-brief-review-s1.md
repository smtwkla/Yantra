```
Step: S086 — Breakdown calls on the contract
Doc: brief-review s1
Author: Brief reviewer (Fable)
Date: 31-10-2026
```

Reviewed against: d216f48 + uncommitted S079, S080, S081, S082, S083, S084

# S086 — staleness review s1

**Verdict: no `blocker` or `major` finding is open.** The brief still holds against the code of
S079–S084 as it stands in the working tree and against S085 as its brief states it. One `minor`
finding (BS1-01: the "Do not repair" constant already exists, so the brief plans a duplicate and a
change to a file it need not touch) and five nits, all wording. The three decisions flagged for KLA
at gate B (BR1-03, Q2, C3) keep their options: none of S080–S085 adds a history of `parent_id`, a
hidden count, or a rule on *Not a fault*.

Facts file: `scratch/brief-facts-S086.md`, re-run today (`tooling/steps/brief_facts.py S086`). The
brief's Baseline names S080–S085 as "coded before S086"; S085 is not coded yet, so its names are
checked against `docs/steps/S085-contract-renewal/1-brief.md` (approved, staleness-checked s1).
S084 is in code review (`4-code-review-r1.md`: 0 blocker, 0 major, 0 minor, 3 nits on docstrings
and one test); none of its findings touches a name S086 relies on.

The one question, per statement: what changed since the baseline, what in the brief is now wrong,
and the fix.

## Findings

### BS1-01 — minor — § 1, § 3, § 5.6, § 8.2, § 8.3: `DO_NOT_REPAIR_TEXT` already exists as `DO_NOT_REPAIR`

**What changed.** S082 as coded put the D9 text into `frontend/src/utils/contractLabels.js` as the
exported constant `DO_NOT_REPAIR` (line 141, the same words), with `isEnded(item)` and
`showsDoNotRepair(item)` (not ended and `only_vendor_repairs`) beside it; `UnderContractCard.vue`
imports `DO_NOT_REPAIR` and `showsDoNotRepair`; `frontend/tests/contractLabels.test.js` tests
`showsDoNotRepair`. S082's spec asserts the text through its own in-spec constant (`contracts.spec.js`
line 405), not the app's.

**What is now wrong.** The brief was written while S082 was being coded and left it open ("Only when
S082 wrote the text inline; the coder checks"). It now plans a second constant and a change to a
file that needs none:
- § 3 Frontend: `contractLabels.js` gains `DO_NOT_REPAIR_TEXT`; `UnderContractCard.vue` "uses
  `DO_NOT_REPAIR_TEXT` instead of its own copy". The file count says "8 frontend code with
  `UnderContractCard.vue`".
- § 1 Out of scope: "beyond moving one text into a shared constant (§ 3)".
- § 5.6: "`DO_NOT_REPAIR_TEXT` = 'Do not repair. …'".
- § 8.2 Frontend unit: "`DO_NOT_REPAIR_TEXT`" in `contractLabels.test.js`.
- § 8.3 Browser: "S082's card test asserts the 'Do not repair' text, which moves to a constant with
  the same words".

**Why it matters.** A coder who follows § 3 adds `DO_NOT_REPAIR_TEXT` next to `DO_NOT_REPAIR` (a
planned duplicate, CLAUDE-COMMON DRY) and edits `UnderContractCard.vue` for nothing; the unit test
of § 8.2 would test a constant that should not exist.

**Fix (recommended).** Wording only:
- § 3 Frontend: `contractLabels.js` "(from S082): `DO_NOT_REPAIR`, `isEnded`, `showsDoNotRepair`,
  reused"; drop the `UnderContractCard.vue` bullet; file count 7 frontend code files, 17 in all.
- § 1 Out of scope: "Any change to S082's card route or its *Under contract* card."
- § 5.6: the warning shows when `showsDoNotRepair(item)` (S082's rule, one function), with the text
  `DO_NOT_REPAIR`; the items kept are those with `!isEnded(item)`.
- § 8.2: drop the `DO_NOT_REPAIR_TEXT` test; `ticketContractLine` tests stay.
- § 8.3: "S082's card tests assert the same text through the spec's own constant; the app's constant
  is unchanged; re-run."

## Nits

- **BS1-02** (nit) § 5.6: the card item's key is `contract_id`, not `id`
  (`contracts.contracts_for_equipment`: `{"contract_id": out["id"], …}`, and
  `UnderContractCard.vue` links `/contracts/${r.item.contract_id}`). Write the link as
  `/contracts/<item.contract_id>`.
- **BS1-03** (nit) § 3 Backend: `contracts.py` already imports `accessible_unit_ids` from
  `equipment.py` (line 88, with `IST`, `NODE_JOINS`, `load_node_for_user`, `node_path`,
  `write_events`); only `unit_access_condition` is new there. Also `IST` is at hand for `now`
  (§ 5.2), so no import from `tickets.py` beyond `events_by_ticket`.
- **BS1-04** (nit) § 3 Backend, BR1-11: the check still holds (`tickets.py` imports `alerts`,
  `alerts_core`, `config_rbac`, `equipment`, `equipment_core`, `improvements_core`, `tickets_core`;
  none imports `contracts.py`; `documents.py` imports both and nothing imports it). Add one clause:
  `equipment.py` (S082 B10) and `alerts_core.py` (S084) now import `contracts_core`, so
  `contracts_core`'s new import must stay `tickets_core` only (it has no project import), never
  `equipment` or `tickets`.
- **BS1-05** (nit) § 8.4 Team records: name the route: a site row is
  `PUT /api/masters/people/<id>/sites/<site_id>` with `{role, all_units, unit_ids}` (the
  `give_site_role` fixture's call); "the site-roles route" is not a name in the code.
- **BS1-06** (nit) § 5.8: the LOCK ORDER notes that name contracts now also live in `equipment.py`
  (the contracts.py bullet, S080–S084) and `alerts.py` (the S084 scan); S086 changes none of them.
  Add the two to the "unchanged" list, so the coder's self-check item (2) finds them.

## Where a finding depends on S085 or on S084's code review

- None of the findings depends on them. S085 (by its brief) adds `s.active AS site_active` to
  `_CONTRACT_COLUMNS` (dropped by `_contract_out`), four keys to the detail through `_detail`
  (`renewal_of`, `renewed_by`, `can_renew`, `renewal`), the route `renew_contract`, and on
  `ContractView.vue` the chain lines under the vendor line, `"Renew contract"` in the header row and
  `ContractRenewDialog` — nothing at the page's end, so the calls card stays last (§ 5.3). S085
  moves S080's dialog fields to `ContractFields.vue` and `EMPTY` to `contractLabels.js` as
  `EMPTY_CONTRACT_FORM`; no name collides with `callsTotalLine`, `callsUsedLine`,
  `ticketContractLine`. The coder re-reads `_CONTRACT_COLUMNS` and `_detail` after S085 is coded.
- S084's three nits (CR1-01 docstrings in `alerts.py` and `equipment.py`, CR1-02 `ends_words`,
  CR1-03 a test) change no name or shape S086 reads; `_contract_out` deleting
  `first_reminder_for` and `second_reminder_for` is as the brief's § 3 (from S084) implies.

## The gate-B decisions (BR1-03, Q2, C3): options unchanged

- **BR1-03** (a covered part's tickets wherever the part stood when raised): the code still reads
  the tree as it is now. S082's `card_items` and `covered_sql` use `e.parent_id` / `p.parent_id`
  with no history; `equipment_events` records `moved_parent` as text only. The widening and its
  residual stand as written.
- **Q2** (*Not a fault* counts as a call): no step since the baseline touches `not_a_fault` or
  `latest_restoration`; `tickets_core.py` is unchanged.
- **C3** (the used line only for a whole-site reader): `accessible_unit_ids(cur, key)` and
  `unit_access_condition` are unchanged; `equipment._ticket_light_column` still sends no ticket fact
  for a unit without `ticket:read`. The options are the same.

## Checked and found consistent

- `backend/contracts.py` as coded: `contracts_bp`, `READ_BASIC`, `_CONTRACT_SELECT` =
  `_CONTRACT_COLUMNS + _CONTRACT_FROM` (with `vendor_name`, `site_code`, `vendor_active`),
  `_contract_row(cur, contract_id)`, `_contract_out(row, flags, today)`, `_SiteFlags.at`,
  `_detail`, `_today()`, `get_contract`'s 404 rule (missing, or `READ_BASIC` not held at the row's
  site), `_lock_contract(cur, id, key=EDIT)` (not used by S086: reads only), the card route
  `/for-equipment/<int:node_id>` through `load_node_for_user(cur, node_id, for_update=False)` (404
  outside the reader's `equipment:read` units, as § 5.6 accepts), `_CARD_KEYS` (holds `status`,
  `response_hours`, `covers_breakdown_calls`, `only_vendor_repairs`, `vendor_name`,
  `contract_type`, `to_date`: all `ticketContractLine` and `cardHeadline` need), `CARD_ENDED_DAYS`
  = 90, and the docstring's "Reads: plain, no lock."
- `contracts_core.py`: `contract_status(from_date, to_date, today)` → `{kind, label, days}` with
  kinds `upcoming`, `in_force`, `ending`, `ended` (§ 5.4); it imports `masters_core` only; the
  breakdown-calls tick forces `breakdown_calls_per_year` NULL (`validate_contract`, § 5.3).
- `auth_utils.sites_holding(cur, key)` exists (S082); `has_perm_at`, `permissions_at_site`,
  `require_perm` as cited. `config_rbac`: `ticket:read` = `("maint_operator", "it_admin")`,
  `contract:read_basic` = `("*",)`, the four contract keys in `SITE_SCOPED`, `ASSIGNABLE_ROLES` =
  technician, engineer, manager; the storekeeper (`maint_storekeeper`) holds `*` keys and no
  `ticket:read` (§ 5.5, § 8.2's 403 test).
- `equipment.py`: `accessible_unit_ids(cur, key="equipment:read")` and
  `unit_access_condition(cur, key, unit_column, machine_unit_column)` → `(sql, params)` or `None`,
  as § 5.5's table states; `_ticket_light_column` as cited.
- `tickets.py`, `tickets_core.py`, `improvements.py`, `TicketDetailView.vue`, `PersonPicker.vue`,
  `ticketLabels.js`, `e2e/support/`, `tooling/e2e/seed_e2e.py` and `test_tickets_api.py` are
  unchanged since the baseline (`git diff --stat d216f48`): `people_at_site`, `_visible_condition`,
  `person_at_site`, `ASSIGNEE_AT_SITE`, `_now`, `_events_by_ticket` (two call sites, lines 403 and
  602), the docstring's "Import direction" paragraph, `ticket.permissions` (the page's `can(key)`),
  `ticket.component?.id ?? ticket.machine.id`, the plan line and the `action-bar` div, the seed
  operator with MCC2 only. Round 1's checks of them stand.
- `contractLabels.js`: `cardHeadline`, `responseText`, `coverageLines`, `callLine`, `isEnded`,
  `showsDoNotRepair`, `DO_NOT_REPAIR` (BS1-01). `ContractView.vue`: the Documents card
  (`DocumentsCards`, behind `can_read_documents`) comes after the machines card and is the last
  card; the page reloads on `route.params.id`. The `contract` route is named `contract`
  (`/contracts/:id(\d+)`).
- `contracts.spec.js` helpers the brief relies on: `callAs(key, method, path, data)`,
  `vendorByApi` (as the engineer), `contractByApi(vendor, title, fields, key)`,
  `machineByApi(name, unitCode)`, `partByApi`, `contractWithMachine`, `openNodeAs`; `raiseByApi`,
  `moveByApi`, `istLocal` in `e2e/support/tickets.js`; `expectDialogFits`,
  `expectNoSidewaysScroll` in `e2e/support/dialogs.js`.
- Fixtures: `make_vendor`, `make_site`, `make_unit`, `make_equipment`, `make_person`,
  `give_site_role`, `user_at_sites`, `user_with_units`, `make_ticket`, `uniq`, `db_down` exist;
  `_TABLES` already empties `contract_equipment`, `contracts` and `vendors`, so S086 adds no table.
- Migrations: v42 vendors, v43 contracts, v44 `contract_equipment`, v45 contract documents, v46
  reminder markers; S085 takes v47; S086 adds none, so no number to take. `ix_people_vendor`,
  `uq_contract_equipment`, `ix_tickets_equipment_state`, `ix_tickets_component_state`,
  `ix_ticket_labour_ticket`, `ix_ticket_events_ticket` are in `local_db.py`.
- § SMTW-Review: *Contract fields by key (S080)* reads as the brief cites it (every answer through
  `_contract_out`; R02.2's price rule; R02.3's documents); *Contract reminders (S084)* is there; S085
  adds *Contract renewal*; S086's point goes after it.
- The e2e `DO_NOT_REPAIR` and the S082 card tests keep the operator on MCC2 and never relink a seed
  person, as BR1-01 asks.

## Feedback

- idea: `brief_facts.py` marks the brief's own new names as "not found: `_call_rows` (planned in
  S080)" because the surrounding bullet carries "(from S080)"; the mark should attach to the step
  that the sentence says the name is *new in* (here S086), so a reviewer sees "new in this step"
  rather than a wrong source (`scratch/brief-facts-S086.md` § Code names, last two lines).
