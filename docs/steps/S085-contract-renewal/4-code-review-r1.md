```
Step: S085 — Contract renewal
Doc: code-review r1
Author: Code reviewer (Opus)
Date: 31-10-2026
```

# S085 — code review, round 1

**Verdict: no `blocker` or `major` finding is open.** One `minor` finding and two nits. The route, the lock order,
migration v47, the permissions and the screens follow the brief. All unit suites are green, and the schema-docs
check exits 0.

## Tests run

- `YANTRA_TEST_RUN=s085cr1 tooling/run-tests.bat`: backend 4497 passed (321 s), frontend 402 passed, tooling 231
  passed; ALL SUITES PASSED.
- `YANTRA_TEST_RUN=s085cr1 tooling/schema-docs.bat check`: PASSED at migration v47 (4 passed), exit 0.
- `npx vite build` (into `scratch/`, then removed): built; only the old chunk-size warning.
- Browser: none re-run. No finding of mine needs a run. The coder's runs are the right ones (§ 8.4): the new tests
  alone, then the targeted run `e2e/contracts.spec.js e2e/masters.spec.js e2e/screens.spec.js` (89 passed,
  1 skipped), and the whole suite at Normal once (355 passed, 15 skipped, 2 failed). The 2 failures are the
  known S048 changelog fault (`e2e/changelog.spec.js:14`), outside this step. No shared frontend file changed, so
  no extra WebKit run is due.

## Findings

### CR1-01 (minor) — a failed vendor load leaves *Renew contract* dead, with no message

- **Where:** `frontend/src/views/contracts/ContractRenewDialog.vue:55-59` (`open()`), called from
  `frontend/src/views/ContractView.vue:150` (`@click="renewDialog.open()"`).
- **Problem:** `open()` awaits `ensureVendors()` before `openCreate`. When the vendor list fails to load, the
  promise rejects, nobody catches it, and the dialog never opens. The page shows nothing.
- **Failure scenario:** the database is down for a moment (503) or the phone's network drops when the engineer
  taps *Renew contract* for the first time in the session. Nothing happens. The engineer taps again and again, and
  the browser console holds an unhandled rejection. This breaks the floor rule that every failure shows one plain
  line that says what to do.
- **Fix:** follow `RootCauseDialog.vue` `open()`: open the dialog first (`openCreate(props.contract)`), then load
  the vendors in a `try`/`catch`, and on failure show one line in the dialog, e.g. "The list of vendors could not
  be loaded. Close the dialog and try again." Another way: catch in `ContractView` and set `actionError`. Add a
  unit or browser check only if it is cheap; a code fix is enough here.

## Nits

- **CR1-02** (nit) `frontend/src/utils/contractLabels.js:125-126`: when every line is skipped, the notice reads
  "No machines are copied. Not copied: CMP004 (scrapped), …". The two sentences say the same thing twice; one
  sentence, e.g. "No machine is copied: CMP004 (scrapped), CMP005 (now at BRICKS).", is shorter for the floor.
- **CR1-03** (nit) `backend/contracts.py:633`: the comment "node (1) shared, in id order" sits on the loop that
  locks; add "before any line insert" so the reason for the separate loop (the impl report's decision) stays in
  the code.

## Checked and found consistent

- **Lock order (§ 5.8).** `renew_contract` runs `clean_body` outside the transaction, then: `_lock_contract` (old
  contract FOR UPDATE, 404 without `contract:read_basic`, 403 without `contract:edit` at the site) → `active` 409
  from the locked row → the site `LOCK IN SHARE MODE` (409) → the plain renewal read (409 naming it) →
  `_drop_gated`, the call-out copy, `_check_rules` → `check_active_vendor` (vendor shared, 400) → the insert → the
  lines, sorted by `equipment_id`, each node `LOCK IN SHARE MODE` before any line insert → the line inserts and
  history lines → `_answer`. The pool is autocommit and `transaction()` calls `begin()`, so the first plain read
  (inside `_lock_contract`'s permission checks) comes after the old contract's lock; the plain renewal read
  therefore sees any renewal committed before the lock. No cycle with S081's line writes (contract first, then a
  line or node shared), S083's documents path (contract first, then only `equipment_documents`), S084's scan
  (contracts in id order, plain `contract_renewed`, so no gap lock on `uq_contracts_renewal_of`), or
  equipment.py's writers (node exclusive, never wait on a contract). The residual move/scrap deadlock is the one
  the brief accepts, and contracts.py's LOCK ORDER note records it. The notes in contracts.py, equipment.py and
  alerts.py say "at most one existing contract row (the renewal also inserts one)".
- **Migration v47.** The unique key comes before the plain key is dropped, so `fk_contracts_renewal_of` always has
  an index; both statements use `IF [NOT] EXISTS`, so a half-applied v47 re-runs. No `_PRECONDITIONS` entry is
  needed: the last release (v0.1.14) is at v41, so production has no `contracts` table; v42–v47 ship together. The
  upgrade test (`test_migration_v47.py`) covers the fresh database, a v46 database with a renewal, the 1062 on a
  second renewal, many NULLs and a re-run. v43 and its test keep the old index name, as an applied migration must.
- **Refusals (§ 5.5).** The order and the texts match: 400 body → 404 → 403 → 409 inactive → 409 site inactive →
  409 already renewed (also when the renewal is inactive) → 400 `vendor_id` with S079's texts. The unique-key
  backstop maps to a 409 with no field (`api_common._integrity_error`), which `useFormModal` shows at the top.
- **Permissions and gated fields.** The route is `require_perm(EDIT)` plus `require_perm_at(EDIT, site)` through
  `_lock_contract`; the actor comes from `actor()`. `_drop_gated` removes a call-out number without
  `contract:read` and a cost note without `contract:read_senior`; IT admin's renewal gets the old call-out number
  from the locked row, and the answer leaves it out. No line price is ever written. Every answer goes through
  `_detail` → `_contract_out`, which also drops the new `site_active`. The list and the card read
  `_CONTRACT_COLUMNS` and go through `_contract_out` too, so `site_active` never leaks. All SQL uses parameters.
- **The detail (§ 6.1).** `renewal_of`, `renewed_by`, `can_renew` and `renewal` are built in `_detail`, so the
  GET and every write answer carry them (`test_a_write_answer_carries_the_chain`). `can_renew` needs
  `contract:edit` at the site, an active contract and site, and no renewal (active or not).
- **Machines (§ 5.3).** Scrapped wins over "now at <site>"; units are not asked; each copied line has a NULL price
  and a `contract_added` line with the new contract's `event_text`. `at_contract_site` comes from a plain read, as
  in S081's `_check_node` and as the brief states.
- **Period (§ 5.2).** `renewal_period` and `_add_months` give every example of the brief, the leap-day start and
  the 2099 bound.
- **Reminders (§ 5.6).** `alerts._RENEWED` is unchanged; `test_a_renewed_contract_is_not_reminded` shows the old
  contract is renewed after the route and not renewed once the renewal is inactive.
- **Screens.** `ContractFields.vue` holds S080's fields unchanged, with the `contract` id prefix by default, so the
  Masters dialog's ids and labels stay the same; `storedVendor` gives the same option list as the old
  `vendorOptions`. `EMPTY_CONTRACT_FORM` and `contractForm` are the one copy. `ContractRenewDialog.vue` uses
  `useFormModal` as § 5.7 says (`blank(seed)`, `openCreate(contract)`, `afterSave`, then FormModal's `closed` emits
  `renewed`); the page renders it with `v-if="contract.can_renew"` and `:key="contract.id"`. FormModal keeps the
  footer fixed. The chain lines, the way-out line for editors and the button match the brief's texts.
- **Decisions taken.** Each one in the impl report is reported and keeps the brief's behaviour. The two texts the
  brief gave no words for are plain: the price sentence is left out when no machine is copied, and "No machines are
  copied." covers the all-skipped case (wording nit CR1-02).
- **Tests.** The core, API and migration tests cover § 8.1 and § 8.2, with the failure modes (403/404 by site,
  inactive contract, site and vendor, missing vendor, second renewal, body errors, the database down). The six
  browser tests assert what the user sees and call `expectDialogFits` on every dialog they open; none is tagged,
  which is right for logic tests. The impl report's `## Manual checks` carries the three important checks as
  `[auto]` with their tests; § 8.5 has no real-device check.
- **Docs pass.** `notes.json` names `renewal_of_id` and `uq_contracts_renewal_of`; `schema.json` and
  `schema-data.js` are generated, and `check` exits 0. Plan.MD § 2 item 9 and the `.claude/CLAUDE.md` § SMTW-Review
  point match § 3 and § 8.6. No other listed doc is made wrong.
- **Track.** Full, as the step needs (a migration, locks, permissions).

## Manual browser checks for the user

None from this step: every important check is `[auto]`, and § 8.5 lists no real-device check. KLA decides BR1-01
(Q1, the old contract stays editable) and BR1-02 (Q2, one renewal per contract) at gate B.

## Feedback

- hindrance: the backend suite took 321 s, while `.claude/CLAUDE.md` § Dev commands says "the full suite about
  40 s"; I planned my waits on the doc's figure (`scratch/backend-tests-s085cr1.log`, the schema-docs check ran at
  the same time).
- idea: the orchestrator's spawn prompt named the lock paths and the precondition question to confirm; that
  saved reading S080–S084 in full. Keep that habit for steps on top of an unreviewed base.
