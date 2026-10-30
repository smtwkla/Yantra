```
Step: S085 — Contract renewal
Doc: brief
Author: Orchestrator's drafter (Opus)
Date: 30-10-2026
Track: full
Baseline: d216f48 + uncommitted R02 docs (S080 being coded); S079–S084 coded before S085 (staleness check before coding)
Status: Approved 30-10-2026 (gate A delegated by KLA for tonight's R02 steps; review r1: 0 blocker, 0 major, 3 minor; BR1-01 and BR1-02 flagged for KLA at gate B)
From: R02.4
```

# S085 — Contract renewal

## 1. What will be built

S080–S084 give Yantra the contract, its machines and prices, its card, its documents and its
reminders. **R02.4 is the renewal:** one action on the contract page makes the next contract with
the same terms and machines, and keeps the chain from year to year (D6, "a new record linked to the
old one"; Plan.MD § 2 item 9).

1. ***Renew contract*** on the contract page (`/contracts/:id`, from S081) opens the contract dialog
   filled from the old contract: type, vendor, title, contract number, coverage, PM visits, response
   time, the *Only the vendor may repair* tick, the call-out number, the notes. **From** is the day
   after the old **To**; **To** keeps the old period's length (§ 5.2). The **cost note and every price
   start empty** (§ 5.4). The dialog says which machines are copied and which are not (§ 5.3).
2. **Saving** (`POST /api/contracts/<id>/renew`) creates the new contract at the old one's site with
   `renewal_of_id` = the old contract, copies its machine lines **without prices**, and writes each
   machine's history line (`contract_added`, S081 § 5.3). The old contract, its prices, cost note and
   documents stay as they were. The page then opens the new contract.
3. **The chain on the page:** the new contract shows "Renews: Atlas Copco AMC 2026–27 · 01-04-2026 to
   31-03-2027", the old one "Renewed by: Atlas Copco AMC 2027–28 · 01-04-2027 to 31-03-2028", each a
   link.
4. **One renewal per contract:** migration **v47** makes `renewal_of_id` unique (§ 4, E2).
5. **Refusals:** an inactive contract, an already renewed one, an inactive site, an inactive vendor.
6. **Reminders** (S084): once renewed, the old contract gets no more reminders; the new one gets its
   own at its own end (§ 5.6).

**After S085:** the engineer renews the Atlas Copco AMC in one dialog before 31-03-2027; the 2027–28
contract covers the same compressors, the managers enter this year's prices, and both years stay
comparable (D6).

### Out of scope

- Copying documents (they stay on the old contract, E6), prices or the cost note (§ 5.4).
- Making the old contract read-only after its renewal or end (§ 9 Q1).
- *Edit* of the terms on the contract page (S081 B9; § 9 Q4): the renewal is edited in Masters ›
  Contracts, as every contract.
- A "Renewed" badge or column in Masters › Contracts; breakdown calls across the chain (R02.6, S086);
  the vendor report across years (R02.8).

## 2. Standards and practice

- **ISO 55001 § 8.3, outsourcing** (Plan.MD § 2 cites it; the clause number in the 2024 edition *to
  verify*). In plain words: work given to an outside firm stays the plant's responsibility; the plant
  controls it and keeps the evidence. A renewal is a new decision to outsource for one more period,
  so it is a new record with its own terms, machines and cost, linked to the period before.
- **ISO 9001:2015 § 8.4, control of externally provided processes and services** (sub-clause 8.4.3,
  information for external providers, *to verify*). In plain words: state in each agreement what is
  required, and check the provider's work against it. Each year's terms stay on their own record, so
  the plant compares what was agreed each year with what the vendor did (R02.8).
- **ISO 9001:2015 § 7.5.3, control of documented information.** In plain words: keep records
  retrievable and protect them from unintended change. The renewal never changes the old contract,
  its prices, cost note or documents; the chain links make each year reachable from the next; each
  copied machine gets a history line with who and when. **Departure (recorded):** the old contract is
  not made read-only (§ 9 Q1).
- **ISO/IEC 27001:2022 A.5.15, access control.** In plain words: each person sees only what the work
  needs, and the server enforces it. The call-out number and the cost note follow their keys (S080
  § 5.4); nobody writes a price through a renewal (§ 5.4).

## 3. Where

S080–S084 are coded before S085; in their files this brief anchors by name (README § Anchors by
name). Names marked **(from S0NN)** do not exist at the baseline. S080 is being coded now: names from
its working-tree code are marked **(from S080, as coded)**; the staleness review checks all of them.
- (from S080, as coded): `backend/contracts.py` with `contracts_bp`, `_SiteFlags`, `_contract_out(row,
  flags, today)` (it deletes `renewal_of_id` from the answer), `_answer(cur, contract_id)`,
  `_drop_gated(clean, site_id)`, `_check_rules(clean, stored)`, `create_contract`, `change_contract`,
  `READ_BASIC`, `READ_CALLOUT`, `EDIT`, its LOCK ORDER note; `backend/contracts_core.py` with
  `validate_contract(body, creating)` (`REQUIRED` holds `site_id`), `DATE_MAX`, `SITE_INACTIVE`;
  `masters.check_active_vendor(cur, vendor_id)` (S079, public for S080); `test_contracts_api.py`,
  `test_contracts_core.py`, `test_migration_v43.py`.
- (from S080): `frontend/src/views/masters/ContractsPanel.vue`, `frontend/src/utils/contractLabels.js`
  (`contractBody(form, site)`), `frontend/e2e/contracts.spec.js` and its in-spec helpers,
  `frontend/tests/contractLabels.test.js`.
- (from S081): `contract_equipment`; `/contracts/:id(\\d+)` and `frontend/src/views/ContractView.vue`;
  `_machine_lines(cur, contract, flags)` and the detail's `machines` (`lifecycle`, `site_code`,
  `at_contract_site`); `contracts_core.event_text(contract)`; `test_contract_equipment_api.py`; the
  contracts.py bullet of equipment.py's LOCK ORDER.
- (from S083): `contracts.lock_contract_for_change`, not used (it reads `id, site_id` only and checks
  `contract:read_senior`).
- (from S084): v46 (`first_reminder_for`, `second_reminder_for`); `alerts.contract_renewed(cur,
  contract_id)`; the scan's lock sentences in contracts.py, equipment.py and alerts.py;
  `backend/tests/test_contract_alerts.py`.

### Backend

- `backend/local_db.py`: migration **v47** at the end of `_MIGRATIONS` (§ 4.1); no `_PRECONDITIONS`
  entry.
- `backend/contracts_core.py`: `validate_renewal(body, creating)`, `renewal_period(from_date,
  to_date)`, `renewal_lines(machines)`, the private `_add_months(day, months)`, the messages of § 5.5.
- `backend/contracts.py`: the route `renew_contract` (§ 6); the private `_renewal_links(cur, row)` and
  `_renewal_offer(row, machines, flags, site_active)` (§ 6.1); `UNIQUE_KEY_ERRORS` gains
  `uq_contracts_renewal_of`; the LOCK ORDER note (§ 5.8). Imports `SCRAPPED`
  (`backend/equipment_core.py:19`) and `write_events` (`backend/equipment.py`).
- `backend/equipment.py`, `backend/alerts.py`: docstrings only (§ 5.8).

### Frontend

- `frontend/src/views/contracts/ContractFields.vue` (new): S080's dialog fields, moved out of
  `ContractsPanel.vue` unchanged, plus a renew mode (§ 5.7).
- `frontend/src/views/masters/ContractsPanel.vue`: its dialog renders `ContractFields`; no change of
  behaviour.
- `frontend/src/views/contracts/ContractRenewDialog.vue` (new): `FormModal.vue` through `useFormModal`
  (§ 5.7).
- `frontend/src/views/ContractView.vue`: the button, the chain lines, the dialog, the reload on a new
  `:id` (§ 5.7).
- `frontend/src/utils/contractLabels.js`: `renewalForm(contract)`, `renewalNotice(renewal, canReadCost)`,
  `chainText(link)`.

### Tests

- `backend/tests/test_migration_v47.py` (new), on the pattern of `test_migration_v43.py` (`V46` =
  `range(20, 47)`, `V47` = `range(20, 48)`; `_keys`, `_foreign_keys` from `test_migration_v36.py`).
- `backend/tests/test_contracts_core.py`, `backend/tests/test_contract_renewal_api.py` (new) (§ 8.2).
- `backend/tests/test_contracts_api.py`, `test_contract_equipment_api.py`, `test_contract_alerts.py`
  (§ 8.3).
- `frontend/tests/contractLabels.test.js`; `frontend/e2e/contracts.spec.js` (§ 8.4).

### Docs (housekeeping, by the coder)

- `docs/schema/notes.json`: in the `contracts` line, "`renewal_of_id` (→ `contracts`, always NULL until
  R02.4)" becomes "`renewal_of_id` (→ `contracts`, the contract this one renews; one renewal per
  contract, S085)", and the index `ix_contracts_renewal_of` becomes `uq_contracts_renewal_of`
  (unique) (BR1-08); then `tooling\schema-docs.bat write`, read `git diff docs/schema/`; `check` exits 0.
  `docs/schema/schema.json` and `docs/schema/schema-data.js` are generated.
- `docs/Plan.MD` § 2 item 9: "Renewal makes a new record linked to the old one" gains "(one per
  contract), with its terms and machines; prices and the cost note start empty, documents stay on the
  old contract (S085)".
- `.claude/CLAUDE.md` § SMTW-Review: the point of § 8.6.
- `docs/steps/device-checks.md`: no row (§ 8.5).

**File count:** 16 code and test files (5 backend, 5 frontend, 6 test files), 3 docs. One concern.

## 4. Data model

### 4.1 Migration v47

```sql
-- One renewal per contract (S085, R02.4).  A renewal set inactive keeps its place; it is set active
-- again to renew with it.  The unique key serves fk_contracts_renewal_of and S084's renewed check,
-- so the plain key goes.  Two statements, each safe to run twice: a half-applied v47 re-runs.
ALTER TABLE contracts ADD UNIQUE KEY IF NOT EXISTS uq_contracts_renewal_of (renewal_of_id);
ALTER TABLE contracts DROP INDEX IF EXISTS ix_contracts_renewal_of;
```

- **Order:** the unique key first, so `fk_contracts_renewal_of` always has an index on its column;
  InnoDB then lets the plain key go (an FK may use any index that starts with its column; *to verify*
  by `test_a_fresh_database_gets_v47`).
- **NULLs:** a unique key allows many NULLs; every contract that renews nothing passes.
- **No precondition:** nothing writes `renewal_of_id` before S085 (S080's `validate_contract` ignores
  it), so no two rows share a value; and production holds no contract before v46 (S084 § 9 A1).
- **Kept test databases:** an S084 test that inserted two renewals of one contract (`db_rows`) leaves
  rows v47 refuses (1062). § 8.3 changes such a test; if a kept worker database refuses v47 once, the
  coder drops the test databases by `.claude/CLAUDE.md`'s two-step procedure, never during a run.
- **Rollback:** a release before v47 reads `renewal_of_id` only in S084's renewed check, which works
  with either key.
- S084's comments that name `ix_contracts_renewal_of` are updated (`git grep ix_contracts_renewal_of`).

### 4.2 What is computed, never stored

The proposed period, the machines to copy and to skip, `can_renew`, the chain links (§ 6.1).

## 5. Rules

### 5.1 Who may renew

- **Key:** `contract:edit` at the old contract's site (engineers, managers, IT admin; admin by the
  bypass; S080 § 5.5). A renewal creates a contract there, so it takes the create key. No new key.
- **The route:** `require_perm(EDIT)` (403 when held nowhere); `contract:read_basic` not held at the
  site → 404 "Not found"; `require_perm_at(EDIT, site)` → 403 "You can't do this at SMTW". A request
  with no identity gets 401 from `require_auth` before any route, never admin.
- **The button** shows only when `can_renew` (§ 6.1), so no tap ends in a 403, or in a 409 the page
  could foresee. No disabled control.
- **Identity:** no field changes who can log in or what they see. The site is the old one and is
  fixed (S080 D6), so the same people read the renewal.

### 5.2 The proposed period

`renewal_period(from_date, to_date)` → `(new_from, new_to)` as `date`s, or `(None, None)`:

- `new_from = to_date + 1 day`.
- **Whole months:** when `new_from.day == from_date.day`, the old period is `n` whole months (`n` = the
  months from `from_date` to `new_from`, at least 1): `new_to = _add_months(new_from, n) − 1 day`.
  `_add_months` keeps the day, or takes the month's last day when the month is shorter.
- **Otherwise** the same number of days: `new_to = new_from + (to_date − from_date)`.
- **Past `DATE_MAX`** (2099-12-31, S080): `(None, None)`; the dialog's dates are empty and the save
  asks for them.
- **Examples** (a scratch copy of the rule, run 30-10-2026): 01-04-2026 to 31-03-2027 → 01-04-2027 to
  31-03-2028; 15-01-2026 to 14-07-2026 → 15-07-2026 to 14-01-2027; 01-03-2027 to 29-02-2028 →
  01-03-2028 to 28-02-2029; 01-04-2024 to 31-03-2029 → 01-04-2029 to 31-03-2034; 10-04-2026 to
  31-03-2027 (not whole) → 01-04-2027 to 21-03-2028; 05-05-2026 to 05-05-2026 → 06-05-2026 to
  06-05-2026; 01-01-2099 to 31-12-2099 → none.
- **A proposal only.** The route checks the dates sent with S080's rules. **No refusal of an overlap**
  with the old contract (E9): S081's overlap warning shows it on both pages.

### 5.3 The machines copied

`renewal_lines(machines)` → `(copied, skipped)` over lines with `equipment_id`, `code`, `lifecycle`,
`at_contract_site`, `site_code`:

- **Copied:** a line whose node is not scrapped (`lifecycle != SCRAPPED`) and is at the contract's
  site (`at_contract_site`): S081 § 5.2's rules 3 and 4 for an add.
- **Skipped:** `{equipment_id, code, reason}`, `reason` "scrapped" or "now at BRICKS" (`site_code`);
  "scrapped" wins when both hold.
- **Unit access is not asked** (a departure from S081 § 5.2 rule 2): the lines are terms that every
  `contract:read_basic` holder at the site reads (S081 B7), so the renewal copies the scope as it is.
- Each copied line: `contract_id` the new contract, `equipment_id`, **`price` NULL**, `created_by` the
  renewer; then `write_events(cur, equipment_id, [("contract_added", None, event_text(new))])`, so the
  history says "Added to contract: Atlas Copco AMC 2027–28 (AMC, 01-04-2027 to 31-03-2028)".
- **The route decides from locked node rows** (§ 5.8 step 8). The dialog's notice comes from the
  detail; a node scrapped in between is skipped, and the answer's `skipped` names it.

### 5.4 The fields of the new contract

The body is the dialog's form. The route calls `clean_body(validate_renewal, creating=True)`;
`validate_renewal(body, creating)` takes `creating` only for `clean_body`'s call shape, ignores it and
always validates as a create (a renewal is one). It removes `site_id` from the body, calls
`validate_contract(body, True)`, and drops the `site_id` error ("Choose a site.") from its errors: the
route sets the site. `active` and `renewal_of_id` sent are
ignored, as on S080's `POST`.

| Field | Value |
|---|---|
| `site_id` | the old contract's |
| `vendor_id`, `contract_type`, `title`, `contract_number`, the five ticks, `breakdown_calls_per_year`, `covered_text`, `not_covered_text`, `pm_visits_per_year`, `response_hours`, `notes`, `from_date`, `to_date` | from the body (the dialog fills them from the old contract and § 5.2) |
| `callout_number` | holder of `contract:read` at the site: from the body (may be changed or cleared). **Non-holder (IT admin): the old contract's value, set by the route** after `_drop_gated` |
| `cost_note` | holder of `contract:read_senior`: from the body; the dialog starts it **empty**. Non-holder: NULL (`_drop_gated`) |
| every line's `price` | NULL, for every renewer |
| `renewal_of_id` | the old contract's id |
| `active`; `first_reminder_for`, `second_reminder_for` (S084) | 1; NULL, NULL |
| `created_by` | the renewer; `updated_*` NULL |

- **Why the call-out number is copied for IT admin.** It is the vendor's breakdown line, not a fact of
  one period. Without the copy, a renewal by IT admin would drop it, and S082's card would show "Call
  the engineer" until an engineer types it again. IT admin still never sees it: the answer leaves the
  key out (S080 § 5.4).
- **Why no price and no cost note are copied** (the price-copy decision). D8 makes a price the
  vendor's price "for the contract period", and R02.4 says "prices empty (managers fill them)". A
  copied price would show last year's figure as this year's cost, and R02.8's cost per machine-year
  would be wrong without anyone typing it. A non-holder never writes a price (S081 B3); a server-side
  copy for them would write money they cannot see. The cost note is the same kind of fact (D5).
  **Rejected:** (a) copy prices for a `contract:read_senior` renewer only (a manager's renewal and an
  engineer's would differ, and a stale price looks entered); (b) refuse a renewal by a non-holder (the
  engineers renew most contracts); (c) copy them server-side for everyone (a stale cost nobody entered).

### 5.5 Refusals (in the route's order, § 5.8)

| Case | Answer | Message (scope B) |
|---|---|---|
| a field of the body (S080 § 5.1, the period, the breakdown calls) | 400 | S080's messages, beside the field |
| contract missing, or `contract:read_basic` not held at its site | 404 | "Not found" |
| `contract:edit` not held at its site | 403 | "You can't do this at SMTW" |
| the old contract inactive | 409 | "This contract is inactive. Set it active in Masters › Contracts, then renew it." |
| its site inactive | 409 | "SMTW is inactive. Set it active in Masters › Sites, then renew the contract." |
| it has a renewal (active or not) | 409 | "This contract is already renewed: Atlas Copco AMC 2027–28. Open that contract to change it." |
| the vendor missing, or inactive | 400 `vendor_id` | `masters.check_active_vendor`'s: "That vendor no longer exists. Reload and try again." / "Vendor Atlas Copco is inactive. Choose another vendor or reactivate it." |
| two renewals at one instant (the unique key) | 409 | `UNIQUE_KEY_ERRORS["uq_contracts_renewal_of"] = (None, "This contract is already renewed. Reload the page to see the renewal.")` |

- The 409s carry no field; the dialog shows them at its top (`modalError`, `useFormModal`).
- **The vendor's message:** the roadmap wrote "Atlas Copco is inactive. Make it active in Masters ›
  Vendors, or choose another vendor."; the renewal reuses S079's check and text, as S080's create and
  change do, so the app says one thing for one refusal (CLAUDE-COMMON § Writing style B). A recorded
  wording departure.
- **Another vendor may be chosen** in the dialog (S080 D6 lets a contract's vendor change).
- **An ended or upcoming contract may be renewed** (late or early); only *inactive* (entered by
  mistake) is refused.
- **A renewal set inactive** keeps its link: the old contract stays renewed for the unique key, *Renew*
  stays hidden, and the old page shows "Renewed by: … (inactive)" and, for an editor, the way out
  (§ 5.7). To renew after all, the user sets that renewal active again and edits it (§ 9 Q2).

### 5.6 Reminders (S084)

- S084's rule stays: a contract is **renewed** when an **active** contract has `renewal_of_id` = it
  (`alerts.contract_renewed`, S084 § 5.2); after v47 at most one row can match.
- **Saved renewal:** the next scan skips the old contract; a `contract_alert` already queued for it
  sends nothing (S084 re-reads `renewed` in the task).
- **The new contract** starts with both markers NULL: its own reminders come 60 and 15 days before its
  own To date.
- **Renewal set inactive:** the old contract is no longer renewed; the next scan sends the reminder due
  and not yet sent for its To date (S084 § 5.1). Its page says where the renewal is (§ 5.7).
- No change to `alerts.py`'s code; only the docstring sentence of § 5.8.

### 5.7 The screens

**The contract page** (`ContractView.vue`):
- **Chain lines**, under "Atlas Copco · SMTW", each only when present: "Renews: [Atlas Copco AMC
  2026–27] · 01-04-2026 to 31-03-2027" (`renewal_of`) and "Renewed by: [Atlas Copco AMC 2027–28] ·
  01-04-2027 to 31-03-2028" (`renewed_by`), " (inactive)" after an inactive one; the title is a
  `router-link` to `/contracts/<id>`; `chainText(link)` builds the text after it.
- **The way out of an inactive renewal** (BR1-02): under "Renewed by: … (inactive)", only when the
  detail's `can_edit` (from S080), one small line (`form-text`): "To renew this contract again, set
  that renewal active in Masters › Contracts and change its terms." A reader without `can_edit` sees
  only the chain line.
- **Button** `"Renew contract"` (`btn btn-outline-primary btn-sm`, icon `fa-solid fa-rotate-right`) in
  the header row beside the badges, only when `can_renew`; on a phone the row wraps.
- **Reload on a new `:id`**: a chain link or a renewal opens another contract on the same route, so
  the page loads on a change of `route.params.id` (a `watch`), not only on mount.

**`ContractFields.vue`** (new): S080 § 5.7's fields 1–13, moved from `ContractsPanel.vue` as they are.
`const form = defineModel("form", { type: Object, required: true })` (`MeterFormFields.vue` uses
`defineModel`; one object here, for 17 fields); props `fieldError` (function), `mode` (`"create"`,
`"edit"`, `"renew"`), `sites`, `siteCode`, `vendors`, `storedVendor` (`{id, name, active}` or
`null`), `canReadCallout`, `canReadCost`, `idPrefix`. `ActiveToggle` (item 14) stays in the panel.
**`siteCode`** (BR1-03): the read-only site text on edit and renew comes from this prop, not from
`sites`: the panel passes `chosenSite?.code`, the renew dialog `contract.site_code`. **The empty
form:** S080's `EMPTY` constant in `ContractsPanel.vue` moves to `contractLabels.js` as
`EMPTY_CONTRACT_FORM`, imported by the panel's `blank` / `fromRecord` and by `renewalForm` (one copy).
In **renew** mode:
- **Site:** `siteCode` as read-only text (as on edit).
- **Vendor:** the active vendors; an inactive old vendor is the first option, "Atlas Copco
  (inactive)", selected, with the line "Vendor Atlas Copco is inactive. Choose another vendor or
  reactivate it." under the field (`form-text text-warning-emphasis`).
- **Title:** help "Change the years in the title, e.g. Atlas Copco AMC 2027–28."
- **Cost note** (only with `canReadCost`): empty; help "Enter this period's cost note. Last period's
  note stays on the old contract."

**`ContractRenewDialog.vue`** (new), prop `contract` (the detail), emits `renewed`:
- **Call contract** (settings: *Self-check, repo items* (13)): `useFormModal({ path:
  `/api/contracts/${props.contract.id}/renew`, blank, fromRecord: blank, afterSave, toBody, label:
  (c) => c.title })`. `useFormModal` calls `blank()` once with no seed at set-up (`const form =
  ref(blank())`), so `blank(seed)` returns `renewalForm(seed)` with a seed and `EMPTY_CONTRACT_FORM`
  without. The page calls `openCreate(contract)`: `editingId` stays `null`, so `save()` posts to
  `path`.
- **The vendors** (BR1-03): the dialog calls `ensureVendors()` (`frontend/src/stores/masters.js`, from
  S079: `/api/masters/vendors?include_inactive=1`, `masters:read`, held by every role) when it opens,
  and offers the active ones; `storedVendor` is built from the detail's `vendor_id`, `vendor_name`,
  `vendor_active`.
- **A fresh path per contract:** `path` is fixed at set-up, so the page renders the dialog with
  `v-if="contract?.can_renew"` and `:key="contract.id"`.
- `toBody(form)` = `contractBody(form, { can_read_callout: contract.can_read_callout, can_read_cost:
  contract.can_read_cost })`: a gated field is sent only with its flag; the server ignores `site_id`.
- `afterSave(detail)` keeps the answer; FormModal's `closed` event then emits `renewed` once (the S077
  pattern, `frontend/src/views/equipment/LessonDialog.vue` `onClosed`); the page does
  `router.push({ name: "contract", params: { id: detail.id } })`, so the route never changes under an
  open backdrop.
- **Title** "Renew contract — Atlas Copco AMC 2026–27"; save label `"Renew contract"`.
- **Notice** at the top (`alert alert-info py-2`), `renewalNotice(contract.renewal, contract.can_read_cost)`: "The new contract
  starts the day after this one ends. 2 machines are copied: CMP001, CMP002. Prices start empty: the
  managers of SMTW enter them on the new contract. Documents stay on this contract." With
  `can_read_cost` the price sentence reads "Prices start empty: enter them on the new contract."
  (BR1-09); `renewalNotice(renewal, canReadCost)` takes the flag. With skipped
  lines: "Not copied: CMP004 (scrapped), CMP005 (now at BRICKS)." With none: "This contract has no
  machines; the new one starts with none."
- `renewalForm(contract)` (pure): S080's form fields from the detail; `from_date` / `to_date` from
  `contract.renewal` (`""` when `null`); `cost_note` `""`; `callout_number` the detail's or `""` when
  the key is absent; `site_id` the old one (read-only, ignored by the server).
- **The one-tap path:** *Renew contract* → change the years in the title → *Renew contract*.
- **Disabled controls:** none. **Destructive:** none (a wrong renewal is edited or set inactive in
  Masters › Contracts). On a phone: one column, as S080's dialog.

### 5.8 Locks (`POST /api/contracts/<id>/renew`)

The database runs REPEATABLE READ. The body is validated first (`clean_body`, pure, no lock). Then
one `transaction`, whose first statement is the old contract's lock, so every plain read after it
sees the rows as they were when the lock was granted:

1. `SELECT * FROM contracts WHERE id = %s FOR UPDATE` (the **old** contract) → 404 when missing.
2. Plain: `contract:read_basic` at its site → 404; `require_perm_at(EDIT, site)` → 403; `active` from
   the locked row → 409.
3. `SELECT id, code, active FROM sites WHERE id = %s LOCK IN SHARE MODE` → `active = 0`: 409.
4. Plain: `SELECT id, title FROM contracts WHERE renewal_of_id = %s` → a row: 409 naming it. Every
   renewal of this contract locks it first (step 1), so one committed before the lock was granted is
   seen; the unique key backs it.
5. `_drop_gated(clean, site)`; the call-out number of § 5.4; `_check_rules(clean, {})`.
6. `masters.check_active_vendor(cur, vendor_id)`: the vendor LOCK IN SHARE MODE → 400.
7. `insert_row(cur, "contracts", …, actor())`: shared FK locks on the site, the vendor (held) and the
   old contract (held exclusive). The new row is this transaction's own, invisible to others until the
   commit.
8. Plain: the old contract's lines with their nodes (`_machine_lines`, which orders by `code`); the
   route sorts them by `equipment_id` before the loop (BR1-05). They
   cannot change meanwhile: every line write locks the old contract first (S081 § 5.5). Per line:
   `SELECT id, lifecycle FROM equipment WHERE id = %s LOCK IN SHARE MODE` (node (1), shared);
   `renewal_lines` on the locked `lifecycle` and the plain site; for a copied line `insert_row(cur,
   "contract_equipment", …)` (shared FK locks, held) and `write_events`.
9. The answer: `_answer` on the new contract (S081's detail) plus `skipped`, read in the transaction.

**Two contract rows, in which order:** the old one first (step 1); the new one exists only as this
transaction's insert (step 7), which no other transaction can see, lock or wait on before the commit.
So the route never waits for a second **existing** contract row.

**No deadlock cycle**, checked against `backend/equipment.py` LOCK ORDER and the notes of S080 (create:
site and vendor shared; `PUT`: the contract first), S081 (line writes: the contract first, then a line
row or node (1) shared), S083 (documents: the contract first, then only `equipment_documents`) and
S084 (the scan: several contracts in id order, then only markers and `task_queue`):
- *The old contract:* every other holder takes it first, or in id order (the scan), and waits after
  it only on rows the renewal never holds exclusive. The renewal, after step 1, waits only on the site,
  the vendor and nodes, which none of them holds exclusive. So each waits behind a writer that finishes.
- *The site and the vendor (shared):* masters.py's site update and S079's vendor update lock their own
  row and wait on no contract.
- *The nodes (shared, in id order):* equipment.py's writers never wait on a contract or a line. **A
  residual, accepted:** a move holds the node (1) then the target parent (2), and a scrap locks a
  subtree top-down (equipment.py's "one accepted deadlock"); a renewal holding one covered node shared
  and waiting for another, at the same instant as such a move or scrap of those two nodes, can meet a
  cycle. MariaDB rolls one back (1213, the plain 500 of `_operational_error`, `backend/api_common.py`);
  the renewal leaves nothing, and the engineer taps again. The FK inserts take the same shared locks
  anyway; the explicit read lets "scrapped" be decided from a locking read.
- *Two renewals of one contract* serialise on step 1; the second meets step 4.

The coder writes this into contracts.py's LOCK ORDER note and adds to equipment.py's contracts.py
bullet: "The renewal (S085) locks the old contract FOR UPDATE first, then the site, the vendor and the
covered nodes (1) LOCK IN SHARE MODE, the nodes in id order; it inserts the new contract and its lines,
so it never waits on a second existing contract row." In the S084 sentence of the three docstrings,
"every route holds at most one contract row" becomes "every route holds at most one existing contract
row (the renewal also inserts one)".

### 5.9 The database down

The route and the detail go through `get_db()`: 503 (§ Yantra Specifics, *DB may not exist*). No
background task is added.

## 6. API

| Route | Decorator | Body | Answer |
|---|---|---|---|
| `POST /api/contracts/<int:contract_id>/renew` | `contract:edit` | S080 § 5.1's fields; `site_id`, `active`, `renewal_of_id` ignored | 201, the new contract's detail plus `skipped`; 400, 403, 404, 409 |
| `GET /api/contracts/<id>` (S080, S081; extended) | `contract:read_basic` | — | 200, § 6.1 |

`skipped`: `[{equipment_id, code, reason}]` (§ 5.3). The list `GET /api/contracts` is unchanged.

### 6.1 The detail gains

- `renewal_of`: `{id, title, from_date, to_date, active}` of the contract it renews, or `null`.
- `renewed_by`: the same for its renewal (at most one), or `null`.
- `can_renew`: the user holds `contract:edit` at the site, the contract and its site are active, and
  `renewed_by` is `null`. The site's `active` comes with the detail's row (`_CONTRACT_SELECT` gains
  `s.active AS site_active`; `_contract_out` drops it from the answer).
- `renewal` (only when `can_renew`): `{from_date, to_date, machines: [{equipment_id, code}], skipped:
  [{equipment_id, code, reason}]}`, from `renewal_period` (`null` dates past 2099) and `renewal_lines`
  over the detail's `machines`.
- Both links are contracts of the same site (the renewal copies the site; a site never changes), so a
  reader of one may read the other. `_renewal_links` reads them plainly: `SELECT id, title, from_date,
  to_date, active FROM contracts WHERE id = %s` and `… WHERE renewal_of_id = %s`.
- None of the four carries a price, the cost note or the call-out number.

## 7. Design decisions

- **E1. A create from a filled dialog, not a server-side copy of the row.** A vendor's new quote often
  changes the terms; the user sees and changes them before saving, and S080's validation is reused.
  Rejected: a one-tap copy, then an edit (the first write stores a contract that may be wrong).
- **E2. One renewal per contract, by a unique key (v47).** The chain stays a line, the old page names
  one successor, S084's check has one row to read. Rejected: several renewals with at most one active
  (a check across two contract rows in S080's `PUT` on reactivation, in an order that can meet S084's
  scan); no rule (two renewals, each with the old machines). **A contract split at renewal** (S080
  A4; D7's mixed quote, next year as two contracts) is one renewal plus a new contract, added in
  Masters › Contracts, whose notes name the old contract.
- **E3. The old length, in whole months when it was whole months** (§ 5.2). An AMC of 01-04 to 31-03
  renews to the next 01-04 to 31-03, leap years included; the roadmap's "one year later" is its
  one-year case. Rejected: the same number of days (a leap year shifts the end); always one year (a
  six-month contract would double).
- **E4. Prices and the cost note start empty; the call-out number is copied, by the route for a
  non-holder** (§ 5.4). Money belongs to a period; the call-out number to the vendor.
- **E5. In-service lines at the site are copied, whatever the renewer's units; scrapped and moved
  nodes are skipped and named** (§ 5.3). Rejected: copy every line (a scrapped machine paid again; a
  moved one breaks S081's site rule); a pick list in the dialog (*Remove* on the new page does it).
- **E6. Documents stay on the old contract.** They are that period's paper; the new signed contract is
  uploaded on the new one (S083). Rejected: copy them (two records of one file; the old quote's
  prices on the new contract).
- **E7. `ContractFields.vue` is extracted from S080's panel** (S081 B9 left this to R02.4). One copy of
  the fields serves add, edit and renew. Rejected: a second dialog with its own fields.
- **E8. The old contract first, then the nodes in id order** (§ 5.8): the first-lock rule of every
  contracts.py write. Rejected: no explicit node lock ("scrapped" from a plain read).
- **E9. No overlap refusal.** S081's warning shows a renewal that starts before the old one ends; a
  refusal would block an early renewal with new terms. Rejected: refuse `from_date <=` the old
  `to_date` (S080's `PUT` would need the same rule on both contracts).
- **E10. `validate_renewal` wraps `validate_contract`** and drops only the site's error. One field
  rule for create and renewal. Rejected: reading the old site before `clean_body` (a read outside the
  transaction, to fill a field the user never sends).

## 8. Tests and acceptance

### 8.1 Migration (`backend/tests/test_migration_v47.py`)

- `test_a_fresh_database_gets_v47`: `_keys("contracts")` has `uq_contracts_renewal_of` (unique), not
  `ix_contracts_renewal_of`; `_foreign_keys("contracts")` still has `fk_contracts_renewal_of`.
- `test_a_v46_database_keeps_its_contracts`: a v46 database with a site, a vendor and two contracts,
  one renewing the other (SQL), migrates; the rows are kept.
- `test_a_second_renewal_of_one_contract_is_refused`: a third with the same `renewal_of_id` → 1062.
- `test_many_contracts_renew_nothing`: three with `renewal_of_id` NULL pass.
- `test_a_rerun_changes_nothing`: `_schema()` equal after v47 runs again.

### 8.2 Backend

**Core** (`backend/tests/test_contracts_core.py`):
- `test_renewal_period_whole_months`: the 1-year, 6-month, leap-year and 5-year examples of § 5.2.
- `test_renewal_period_not_whole_months`: 10-04-2026 to 31-03-2027 → 01-04-2027 to 21-03-2028; a
  one-day contract → the next day; a leap-day start, 29-02-2024 to 28-02-2025, is not whole months
  (`new_from` 01-03-2025, day 1 ≠ 29) → 01-03-2025 to 01-03-2026, one day longer than a year: the
  stated behaviour (BR1-07); the dialog shows it, and the user may change it.
- `test_renewal_period_past_2099`: 2099 → `(None, None)`; 01-01-2098 to 31-12-2098 → 2099.
- `test_add_months_keeps_the_month_end`: 31-01-2027 + 1 → 28-02-2027; 31-01-2028 + 1 → 29-02-2028.
- `test_renewal_lines`: in service and standby at the site → copied; scrapped → "scrapped"; another
  site → "now at BRICKS"; both → "scrapped"; an empty list.
- `test_validate_renewal`: no `site_id` → no error and no `site_id` in `clean`; a `site_id` sent →
  dropped; a missing title → "Enter a title."; `active` and `renewal_of_id` ignored.

**API** (`backend/tests/test_contract_renewal_api.py`), each test with its own site, unit, vendor,
contract and machines (`make_site`, `make_unit`, `make_vendor`, `make_equipment`, `user_at_sites`,
`uniq`, `db_rows`; contracts and lines through S080's and S081's routes; the kept worker database
gives the starting state):
- `test_engineer_renews_a_contract`: 201; the new row has the body's terms and dates, the old site,
  `renewal_of_id`, `active` 1, both markers NULL, `created_by`; the old row unchanged (every column).
- `test_renewal_copies_the_machines_without_prices`: a manager-priced contract with two lines,
  renewed by the engineer: two new lines, `price` NULL; two `contract_added` events with the new
  `event_text`; the old lines keep their prices.
- `test_manager_renewal_copies_no_price`: the manager renews; NULL prices; `price_total` NULL.
- `test_renewal_skips_scrapped_and_moved_machines`: one node scrapped, one moved to another site
  (as admin); `skipped` names both; no line or event for them on the new contract.
- `test_renewal_copies_lines_outside_the_renewers_units`.
- `test_cost_note_comes_from_the_body_only`: the manager sends one → stored; the engineer sends one →
  NULL; the old note never copied.
- `test_it_admin_renewal_copies_the_callout_number`: no `callout_number` sent → the old number in the
  row (`db_rows`); no `callout_number` key in the answer.
- `test_engineer_may_change_the_callout_number`: `""` → NULL; another number → stored.
- `test_an_inactive_vendor_is_refused`: 400 `vendor_id`, `check_active_vendor`'s text; another active
  vendor → 201.
- `test_an_inactive_contract_is_refused`, `test_an_inactive_site_is_refused` (the site set inactive
  through Masters' site route; *to verify* that it allows one with contracts, else `db_rows`): 409.
- `test_a_second_renewal_is_refused`: 409 naming the renewal; also after it is set inactive.
- `test_the_body_is_checked`: To before From → 400 `to_date`; no title → 400 `title`; another site's
  `site_id` → 201 at the old site; another `renewal_of_id` → the path's id.
- `test_renew_needs_edit_at_the_site`: operator, technician, supervisor, storekeeper → 403; an
  engineer of site B with no role at A → 404; an engineer of site B who is operator at A → 403 naming
  A (BR1-04); a missing id → 404.
- `test_detail_shows_the_chain`: `renewed_by` and `renewal_of` name each other; `active` false after
  the renewal is set inactive; both `null` on a plain contract.
- `test_detail_offers_the_renewal`: the engineer's `can_renew` true, `renewal` with § 5.2's dates, the
  machines and the skipped; the operator's `can_renew` false, no `renewal` key; false after a
  renewal, on an inactive contract, on an inactive site.
- `test_a_renewed_contract_is_not_reminded`: `alerts.contract_renewed(cur, old_id)` true after the
  route; false after the renewal is set inactive.
- `test_the_unique_key_message`: `UNIQUE_KEY_ERRORS["uq_contracts_renewal_of"]` is § 5.5's pair.
- `test_renew_with_the_database_down` (`db_down`): 503.

### 8.3 Existing tests that break or run again

- `backend/tests/test_contracts_api.py`, `test_contract_equipment_api.py`: a test that compares a whole
  detail to a fixed key set gains `renewal_of`, `renewed_by`, `can_renew` and, for an editor,
  `renewal`.
- `backend/tests/test_contract_alerts.py` (S084): its *Renewed* tests insert renewals through
  `db_rows`; a test with an active and an inactive renewal of **one** contract uses two contracts (or
  flips `active` on one row).
- `test_migration_v43.py` … `test_migration_v46.py`: each slices its own range; green
  (`test_a_fresh_database_gets_v43` still finds `ix_contracts_renewal_of` at v43).
- `backend/tests/test_modules.py` (`LATEST_VERSION` 47), `test_schema_docs_shell.py`: green once
  `tooling\schema-docs.bat write` has run.
- `test_rbac.py` `test_role_matrix`, `conftest.py` `_TABLES`: no new key, no new table; unchanged.
- **Browser:** S080's tests in `contracts.spec.js` open the moved dialog (`"Add contract"`,
  `"Call-out number"`, `"Cost note"`, `"Managers only"`, `"Deactivate"`); the labels stay, and the
  targeted run shows the move broke nothing. No shared file (`FormModal.vue`, `useFormModal.js`,
  `api.js`, the router, the auth store, `e2e/support/`) changes.

### 8.4 Automated (e2e, `frontend/e2e/contracts.spec.js`)

Set-up by API with S080's and S081's in-spec helpers (a vendor and a contract per test; machines as
`createEquipment` does); the old contract from 300 days ago to 65 days ahead. Every flow test calls
`expectDialogFits` on the dialog it opens; refusals with `expectFieldMessage`. Untagged.

- **important** `S085: the engineer renews a contract; the new contract opens with its terms and
  machines, and the chain shows on both pages` — `"Renew contract"`; the dialog shows the old title,
  the vendor, the proposed dates and "2 machines are copied"; the title changed; saved; the new page
  shows the new title, both machines and "Renews:" with the old title; that link opens the old page:
  "Renewed by:", no `"Renew contract"`.
- **important** `S085: the manager renews a priced contract; the new contract shows No prices entered
  yet` — the old page keeps its total; the dialog's *Cost note* is empty.
- **important** `S085: an inactive vendor is refused on renewal beside the Vendor field` — "(inactive)"
  and the warning line; the save's refusal beside *Vendor*; another vendor → saved.
- `S085: a scrapped machine is named in the notice and not copied`.
- `S085: a renewal set inactive shows the way out to the engineer, and no Renew contract button` — a
  renewal by API, set inactive by API; the old page shows "Renewed by:" with "(inactive)", the line
  "To renew this contract again, set that renewal active in Masters › Contracts and change its terms."
  and no `"Renew contract"`; the operator sees the chain line without that line.
- `S085: the operator sees the chain but no Renew contract button`.

**Runs** (settings: *Browser tests*): targeted `tooling/run-e2e-tests.bat e2e/contracts.spec.js
e2e/masters.spec.js e2e/screens.spec.js`; the whole suite at Normal once at the end. No extra WebKit
run.

### 8.5 On a real device

None: a button, a dialog and a page, which a browser engine judges.

### 8.6 Acceptance and the SMTW-Review point

- All unit suites green; `tooling\schema-docs.bat check` exits 0; the targeted and Normal runs green.
- By screen: "Atlas Copco AMC 2026–27" (01-04-2026 to 31-03-2027; two compressors at ₹9,809 and
  ₹28,028) renewed by the engineer as "Atlas Copco AMC 2027–28", 01-04-2027 to 31-03-2028: the new
  page lists both compressors with no prices; the old keeps "Total: ₹37,837 before GST" for the
  manager; each compressor's history shows "Added to contract: Atlas Copco AMC 2027–28 …".
- **§ SMTW-Review point** (for `.claude/CLAUDE.md`): "**Contract renewal (S085):** a renewal is a new
  contract with `renewal_of_id` = the old one, unique (v47), made only by `contracts.renew_contract`
  under the old contract's lock. It copies the terms and the in-service machines of the site, never a
  price, the cost note or a document, and never changes the old contract. A path that copies prices,
  or writes `renewal_of_id` elsewhere, breaks D8 or the chain."

## 9. Open questions and assumptions

- **Q1. Is the old contract read-only once renewed or ended?** The roadmap says "read-only once ended".
  - **(a) No; it stays editable as every contract — recommended.** S080 § 5.1 lets an ended contract
    be corrected, and each write records who and when (ISO 9001 § 7.5.3 asks for protection from
    *unintended* change, not a ban on corrections).
  - (b) Read-only: S080's `PUT`, S081's three line routes and S083's document routes each refuse it
    (code of three steps), and a real correction needs a way out.
  - **Taken as recommended (a) by the orchestrator under the delegation of 30-10-2026; flagged for
    KLA at gate B** (BR1-01). The orchestrator records the dropped "read-only once ended" in R02's log
    and Plan.MD § 2 item 9 at gate B; the coder does not edit the roadmap.
- **Q2. One renewal per contract, ever, or at most one active?**
  - **(a) A unique key (v47) — recommended.** A wrong renewal is edited, or set inactive and later
    active again; nothing makes two.
  - (b) At most one active: no key, a check across two contract rows in S080's `PUT` on reactivation
    (E2), and the old page names one of several.
  - **Taken as recommended (a) by the orchestrator under the delegation of 30-10-2026; flagged for
    KLA at gate B** (BR1-02): v47 kept, the way-out line for editors (§ 5.7), the split case in E2.
- **Q3. The cost note: empty (recommended) or copied for managers?** (a) Empty, as the prices (E4).
  (b) Copied for `contract:read_senior` renewers: a non-holder's renewal still has none, so two
  renewals of one contract would differ.
- **Q4. *Edit* on the contract page?** Small once `ContractFields.vue` exists, and the user lands on
  the new page after a renewal. Not in R02.4; left out; proposed as a follow-up. Not defining.
- **A1. The S080–S084 names** are as § 3 states; the staleness review checks `_contract_out`,
  `_answer`, `_drop_gated`, `_check_rules`, `check_active_vendor`, `_machine_lines`, `contractBody`,
  the dialog in `ContractsPanel.vue`, `ContractView.vue`'s load, the LOCK ORDER notes of S080–S084,
  `alerts.contract_renewed`, and the migration number (v47 after S084's v46).
- **A2. v47 ships with v42–v46** (S084 A1); no row could break the key anyway (§ 4.1).
- **A3. The title is copied as it is**, with help to change the years; no rule rewrites it.
- **Roadmap corrections** (for R02's log): R02.4's "Migrations: none" is now v47 (E2); "To = one year
  later" is the one-year case of E3; "read-only once ended" is Q1; the vendor message reuses S079's
  (§ 5.5); the roadmap is silent on the cost note, the call-out number, scrapped or moved machines and
  documents (§ 5.3, § 5.4, E6).
- **Standards *to verify*:** ISO 55001:2024's clause number for outsourcing; ISO 9001 § 8.4.3.
- **No defining question:** Q1–Q3 have a recommended answer inside D6 and R02.4.

## 10. Amendments

None.

## Review log

### Round 1 — `2-brief-review-r1.md` (Fable), answered 30-10-2026

| Finding | Answer |
|---|---|
| BR1-01 minor | Accepted: Q1 (a) taken as recommended under the delegation, flagged for KLA at gate B; the orchestrator records it in R02's log and Plan.MD at gate B. § 9 Q1. |
| BR1-02 minor | Accepted (a): v47 kept, taken as recommended under the delegation and flagged for KLA at gate B; the editors' way-out line under "Renewed by: … (inactive)" and its browser test; the split quote at renewal in E2. § 5.5, § 5.7, E2, § 8.4, § 9 Q2. |
| BR1-03 minor | Accepted (a): `ensureVendors()` on open and `storedVendor` from the detail; the `siteCode` prop; `EMPTY_CONTRACT_FORM` in `contractLabels.js`. § 5.7. |
| BR1-04…BR1-09 nits | Accepted: BR1-04 the 403 case (§ 8.2); BR1-05 lines sorted by `equipment_id` (§ 5.8); BR1-06 `creating` ignored (§ 5.4); BR1-07 the leap-day start stated as not whole months (§ 8.2); BR1-08 the `notes.json` line and index (§ 3); BR1-09 the manager's notice text (§ 5.7). |
