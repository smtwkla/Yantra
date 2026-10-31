```
Step: S085 — Contract renewal
Doc: impl-report
Author: Coder (Opus)
Date: 31-10-2026
```

# S085 — implementation report

**Result: *Renew contract* is built as the brief says: migration v47, the renew route, the chain and the offer in
the detail, the shared `ContractFields.vue`, the renew dialog and the chain lines on the contract page.** All unit
suites, the schema-docs check, the targeted browser run and the whole suite at Normal are green, apart from the two
known S048 changelog tests (§ Tests). BR1-01 (Q1) and BR1-02 (Q2) are coded with the options the brief records as
taken: the old contract stays editable, and v47 allows one renewal per contract, with the way-out line for editors.
No shared frontend file (`FormModal.vue`, `useFormModal.js`, `api.js`, the router, the auth store, `e2e/support/`)
changed.

## 1. What was built

- **Migration v47** makes `contracts.renewal_of_id` unique (`uq_contracts_renewal_of`) and drops the plain
  `ix_contracts_renewal_of`.
- **`POST /api/contracts/<id>/renew`** (`contract:edit` at the old contract's site) creates the new contract at
  the old site with `renewal_of_id` = the old one. It copies the old contract's in-service machines of the site
  without prices and writes each machine's `contract_added` history line. The answer is the new contract's detail
  plus `skipped`.
- **The detail** (`GET /api/contracts/<id>` and every write answer) gains `renewal_of`, `renewed_by`, `can_renew`
  and, when `can_renew`, `renewal` (the proposed dates, the machines copied and skipped).
- **The contract page** shows *Renew contract* when `can_renew`, the chain lines "Renews: …" and "Renewed by: …"
  (each title a link, " (inactive)" after an inactive one), and, for an editor under an inactive renewal, the line
  "To renew this contract again, set that renewal active in Masters › Contracts and change its terms."
- **The renew dialog** holds the contract fields filled from the old contract, the proposed dates, an empty cost
  note, and a notice of what is copied. After the save the page opens the new contract.
- **`ContractFields.vue`**: S080's dialog fields, moved out of `ContractsPanel.vue`, used by both dialogs.

## 2. How it works

**The proposed period** (`contracts_core.renewal_period`). The new From is the day after the old To. When the new
From has the old From's day of the month, the old period was whole months, and the new one keeps that count of
months (`_add_months` takes the month's last day when the month is shorter). Otherwise the new one keeps the same
number of days. A To past 31-12-2099 gives no dates; the dialog's dates are then empty.

**The machines** (`contracts_core.renewal_lines`). A line is copied when its node is not scrapped and is still at
the contract's site. Otherwise it is skipped with the reason "scrapped" (which wins) or "now at <site>". The
renewer's units are not asked.

**The body** (`contracts_core.validate_renewal`). It removes `site_id`, validates as a create with S080's
`validate_contract`, and drops the "Choose a site." error. `active` and `renewal_of_id` are ignored.

**The route** (`contracts.renew_contract`), in one transaction:
1. `_lock_contract` locks the old contract FOR UPDATE (404, 403); an inactive one is a 409.
2. The site LOCK IN SHARE MODE; an inactive site is a 409.
3. A plain read for a contract with `renewal_of_id` = the old one; one found is a 409 naming it.
4. `_drop_gated` removes the gated fields the renewer may not read. A renewer without `contract:read` (IT admin)
   gets the old call-out number, set by the route. The cost note comes only from a `contract:read_senior` holder's
   body. `_check_rules` checks the period and the calls.
5. `check_active_vendor` (400 `vendor_id`, S079's texts).
6. The insert: the body's fields, the old site, `renewal_of_id`; `active` and the reminder markers take their
   defaults.
7. The old contract's lines (`_machine_lines`), sorted by `equipment_id`; each node LOCK IN SHARE MODE, then
   `renewal_lines` on the locked `lifecycle`; each copied line inserted with no price, and its history line.
8. The answer: `_answer` on the new contract plus `skipped`.

Two renewals at one instant meet the unique key: `UNIQUE_KEY_ERRORS["uq_contracts_renewal_of"]` gives the 409
"This contract is already renewed. Reload the page to see the renewal."

**The detail** (`contracts._detail`). `_renewal_links` reads the two links plainly. `can_renew` is true when the
reader holds `contract:edit` at the site, the contract and its site are active, and there is no renewal.
`_renewal_offer` builds `renewal` from the core functions over the lines `_detail` already read. The site's
`active` comes as `site_active` in `_CONTRACT_COLUMNS`; `_contract_out` drops it from every answer.

**The dialog** (`ContractRenewDialog.vue`). It uses `useFormModal` with the renew path. `blank(seed)` returns
`renewalForm(seed)` with a seed, an empty form without. `open()` loads the vendors (`ensureVendors`) and calls
`openCreate(contract)`. `toBody` is `contractBody` with the detail's flags. `afterSave` keeps the answer; FormModal's
`closed` event then emits `renewed`, and the page does `router.push` to the new contract (the S077 pattern). The
page renders the dialog with `v-if="contract.can_renew"` and `:key="contract.id"`.

## 3. Files touched

Backend:
- `backend/local_db.py`: migration v47.
- `backend/contracts_core.py`: `validate_renewal`, `renewal_period`, `_add_months`, `renewal_lines`, the texts
  `RENEW_INACTIVE`, `RENEWAL_RACE`, `SKIP_SCRAPPED`, `renew_site_inactive`, `already_renewed`; imports `SCRAPPED`
  from `equipment_core`.
- `backend/contracts.py`: the route `renew_contract`; `_renewal_links`, `_link_out`, `_LINK_SELECT`,
  `_renewal_offer`; the gains in `_detail`; `s.active AS site_active` in `_CONTRACT_COLUMNS`, dropped in
  `_contract_out`; `UNIQUE_KEY_ERRORS` entry; the module docstring and the LOCK ORDER note (§ 5.8).
- `backend/equipment.py`: the contracts.py bullet of LOCK ORDER (docstring only).
- `backend/alerts.py`: the S084 sentence and the gap-lock sentence now name `uq_contracts_renewal_of` (docstring
  only).

Frontend:
- `frontend/src/views/contracts/ContractFields.vue` (new): the fields, with the `create`, `edit` and `renew` modes.
- `frontend/src/views/contracts/ContractRenewDialog.vue` (new): the renew dialog.
- `frontend/src/views/masters/ContractsPanel.vue`: renders `ContractFields`; `EMPTY` moved out; `fromRecord` is
  `contractForm`; `vendorOptions` became `storedVendor`.
- `frontend/src/views/ContractView.vue`: the button, the chain lines, the way-out line, the dialog.
- `frontend/src/utils/contractLabels.js`: `EMPTY_CONTRACT_FORM`, `contractForm`, `renewalForm`, `renewalNotice`,
  `chainText`.

Tests:
- `backend/tests/test_migration_v47.py` (new): 5 tests.
- `backend/tests/test_contracts_core.py`: `TestRenewal`, 7 tests (12 cases).
- `backend/tests/test_contract_renewal_api.py` (new): 28 tests.
- `frontend/tests/contractLabels.test.js`: 5 tests for the S085 helpers.
- `frontend/e2e/contracts.spec.js`: 6 S085 tests.

Docs: § Docs updated.

## 4. Decisions taken

- **`_renewal_offer(row, lines)`**, not `(row, machines, flags, site_active)`: `_detail` decides `can_renew`
  inline from the flags and `row["site_active"]` (the column the brief adds), so the offer only builds `renewal`.
  Same behaviour.
- **`_link_out`** sends a link's `active` as a boolean (`true`/`false`), as § 8.2's test reads it; the contract's
  own `active` stays as S080 sends it.
- **`contractForm(contract)`** in `contractLabels.js`: the panel's `fromRecord` loop, moved there so
  `renewalForm` reuses it (DRY); the panel's `fromRecord` is now `contractForm`. Same behaviour.
- **The route reads all lines, then locks the nodes in id order, then calls `renewal_lines` once, then inserts.**
  The brief describes it per line; the locks are the same (nodes shared in id order, before any line insert), and
  one call to the pure function is simpler.
- **`event_text(clean)`** for the history line: the body's validated title, type and dates, so no read of the new
  row.
- **`ContractFields` `storedVendor`**: the panel passes, on edit, the vendor list's row of the form's vendor; the
  fields list it first when inactive. The renew dialog passes the old contract's vendor from the detail. The
  panel's behaviour is unchanged.
- **The inactive-vendor line** under the Vendor field hides while the field shows the save's refusal: both carry
  S079's text, and one copy is enough on screen. The brief does not say whether both show at once; this is no
  departure from its wording.
- **The notice** leaves out the price sentence when no machine is copied (nothing to price), and says "No machines
  are copied." when every line is skipped (the brief gives no text for that case). `renewalNotice` takes the site
  code as a third argument, for "the managers of SMTW".
- **The renew dialog's field ids** start with `renew-` (`idPrefix`), so they never repeat a Masters id.
- **The button** sits at the end of the badges' row (`ms-auto`); on a phone the row wraps.

## 5. Not done, deferred or assumed

- **Re-check of BS1-06 and BS1-07 after S084's fix round:** `TestRenewed._renewal` still makes one renewal per
  test; no S084 test inserts two renewals of one contract, so no kept test database refused v47 (the targeted and
  full runs applied it). `alerts._RENEWED` is unchanged (an active renewal only), shared by `contract_renewed` and
  the scan. `ends_words` moved into `alerts_core.contract_facts` and plays no part in S085.
- **`ix_contracts_renewal_of` mentions:** `alerts.py` and `docs/schema/notes.json` updated; `local_db.py` v43 and
  `test_migration_v43.py` keep the old name on purpose (an applied migration and its test).
- **The residual deadlock** of § 5.8 (a renewal and a move or scrap of two covered nodes at one instant) is
  accepted, as the brief says, and written in contracts.py's LOCK ORDER note. No test makes it.
- **Standards *to verify*** (ISO 55001:2024's clause for outsourcing; ISO 9001 § 8.4.3) stay as the brief left
  them.
- Q1 and Q2 are coded as taken (BR1-01, BR1-02); KLA decides at gate B. The orchestrator records the dropped
  "read-only once ended" in R02's log (I did not edit the roadmap).

## Manual checks

Automated (from passing runs):

- [auto] **important** The engineer renews a contract; the new contract opens with its terms and machines, and the
  chain shows on both pages — `frontend/e2e/contracts.spec.js`::`S085: the engineer renews a contract; the new
  contract opens with its terms and machines, and the chain shows on both pages`
- [auto] **important** The manager renews a priced contract; the new contract shows No prices entered yet —
  `frontend/e2e/contracts.spec.js`::`S085: the manager renews a priced contract; the new contract shows No prices
  entered yet`
- [auto] **important** An inactive vendor is refused on renewal beside the Vendor field —
  `frontend/e2e/contracts.spec.js`::`S085: an inactive vendor is refused on renewal beside the Vendor field`
- [auto] A scrapped machine is named in the notice and not copied — `frontend/e2e/contracts.spec.js`::`S085: a
  scrapped machine is named in the notice and not copied`
- [auto] A renewal set inactive shows the way out to the engineer, and no Renew contract button —
  `frontend/e2e/contracts.spec.js`::`S085: a renewal set inactive shows the way out to the engineer, and no Renew
  contract button`
- [auto] The operator sees the chain but no Renew contract button — `frontend/e2e/contracts.spec.js`::`S085: the
  operator sees the chain but no Renew contract button`

On a real device: none (§ 8.5). No row added to `docs/steps/device-checks.md`.

## Tests

Run name `YANTRA_TEST_RUN=s085c1`.

- **While coding** (targeted): `test_migration_v47.py` + `test_migration_v46.py` 8 passed; `test_contracts_core.py`
  94 passed; `test_contract_renewal_api.py` 28 passed; the neighbours (`test_contracts_api.py`,
  `test_contract_equipment_api.py`, `test_contract_alerts.py`, `test_contract_card_api.py`, `test_modules.py`,
  `test_migration_v43.py` … `v46`, `test_rbac.py`) 211 passed; `contractLabels.test.js` 24 passed.
- **All unit suites** (`tooling/run-tests.bat`, once at the end): backend 4497 passed, frontend 402 passed, tooling
  231 passed; ALL SUITES PASSED.
- **Build check** `npx vite build`: built; only the old chunk-size warning.
- **Schema docs**: `tooling\schema-docs.bat write`, then `check`: PASSED, at migration v47.
- **Browser, the new tests alone** (`E2E_LANES=1`, `--project=phone-chromium -g S085`): first run 5 passed,
  1 failed (my test lacked `consoleWatch.allowFailedRequest` for the expected 400); fixed; then 6 passed.
- **Browser, targeted** (`e2e/contracts.spec.js e2e/masters.spec.js e2e/screens.spec.js`, Normal; the screens and
  APIs changed plus the always-added spec): 89 passed, 1 skipped, in 198 s.
- **Browser, the whole suite at Normal** (`tooling/run-e2e-tests.bat`, once): 355 passed, 15 skipped, 2 failed, in
  453 s. The 2 failures are the known fault outside this step: `e2e/changelog.spec.js:14` (S048, it_admin and admin
  open the change log, desktop-chromium; the empty 0.1.14 section in `CHANGELOG.md`). Left as they are.

## Docs updated

- `docs/schema/notes.json`: the `contracts` line names `renewal_of_id` as "the contract this one renews; one
  renewal per contract, S085" and the index `uq_contracts_renewal_of` (unique, v47).
- `docs/schema/schema.json`, `docs/schema/schema-data.js`: generated by `tooling\schema-docs.bat write` (v47:
  `uq_contracts_renewal_of`, unique, in place of `ix_contracts_renewal_of`); `check` exits 0.
- `docs/Plan.MD` § 2 item 9: "Renewal makes a new record linked to the old one (one per contract), with its terms
  and machines; prices and the cost note start empty, documents stay on the old contract (S085)."
- `.claude/CLAUDE.md` § SMTW-Review: the point *Contract renewal (S085)* of § 8.6, after *Contract reminders
  (S084)*. § Docs to keep current needs no change (no new dev command, port, secret or invariant beyond the review
  point).
- `docs/steps/device-checks.md`: none, because the step has no real-device check (§ 8.5).
- `docs/Maintenance-Philosophy.md`, `docs/Plant-Facts.md`, `backend/example_secrets_app.py`, `docs/Keycloak.md`:
  none, because the step settles no new maintenance rule, learns no plant fact, and adds no secret, role or claim.

## Feedback

- hindrance: the README's Shell rule 1 (no heredoc) and the Edit tool's "read the file first" made each small
  multi-file change a scratch Python script plus a CRLF/LF guard (`scratch/s085_edit1.py` … `edit8.py`, 8 scripts);
  one Python `write_text` silently turned LF into CRLF on Windows, caught only by `file` (about 3 min).
- waste: two Edit calls failed with "File has been modified since read" or "not read yet" on files I had just read
  through Bash `sed`/`grep` (`local_db.py`, `test_contracts_core.py`, `contracts.py`), each a re-read round trip.
- idea: the brief's § 3 lists the helpers' signatures (`_renewal_offer(row, machines, flags, site_active)`); a
  brief could name only the behaviour of private helpers and leave the signature to the coder, so a simpler shape
  is not a reported departure.

## Fix rounds

### Round 1

- **CR1-01** (minor) — Fixed. `ContractRenewDialog.vue` `open()` now opens the dialog first (`openCreate`), then
  loads the vendors in a `try`/`catch`; on failure `loadError` shows at the top of the dialog (joined with
  `modalError` as `topError`, as `RootCauseDialog.vue` does): "The list of vendors could not be loaded. Close the
  dialog and try again." New browser test `S085: when the vendors cannot be loaded, the renew dialog opens and says
  so` (`e2e/contracts.spec.js`; the vendors request is fulfilled with 503 through `page.route`, with
  `consoleWatch.allowFailedRequest`). Fails without the fix: the dialog never opens (`toBeVisible` and the 503
  console error); passes with it.
- **CR1-02** (nit) — Fixed. `renewalNotice` now says "No machine is copied: CMP004 (scrapped), CMP005 (now at
  BRICKS)." when every machine is skipped, and keeps "Not copied: …" only when some machines are copied. Unit test
  in `contractLabels.test.js` updated.
- **CR1-03** (nit) — Fixed. The comment on the node-lock loop in `contracts.py` now says "in id order, before any
  line insert".
- Also, S084 CR2-01 (nit): `status_label` dropped from `alerts_core.contract_facts` (recorded in S084's report,
  Round 2).

Tests: `tooling/run-frontend-tests.bat tests/contractLabels.test.js` 24 passed; backend `tests/test_alerts_core.py
tests/test_email_core.py tests/test_contract_alerts.py tests/test_contract_renewal_api.py` 246 passed;
`npx vite build` built (chunk-size warning only); `tooling/run-e2e-tests.bat e2e/contracts.spec.js
e2e/screens.spec.js` 54 passed, 1 skipped (Normal, targeted).

Docs updated: none, because only a dialog's load path, one notice sentence, a comment and an unused key changed;
no migration, key, secret or new rule.

#### Feedback

- hindrance: Python `open(p, "w")` on Windows wrote CRLF into LF files; found only by counting bytes (`git diff`
  looked normal because of autocrlf), then fixed with a binary rewrite (about 3 min).
